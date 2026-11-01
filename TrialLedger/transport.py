"""A local model behind the GSE call contract (add-targeted-questions, Decision 3).

The model is named explicitly, never chosen here; its installed digest is pinned from Ollama's `/api/tags` and
verified before and after every call, so an answer from a changed model is refused. The prompt is canonical
JSON (operation, rubric, question); the answer is constrained by a JSON schema in Ollama's `format`;
temperature 0; explicit context and output budgets; a prompt over budget is refused, never truncated; an
answer cut by the output limit is an error. Every answer is cached under a hash of the model identity, the
prompt and the schema: a cache hit is a saved answer, not a new observation. The identity is per question
kind (its rubric alone is hashed), so adding or changing one kind's rubric never invalidates another kind's
cached answers. Nothing here reads or produces a
TrialLedger reading.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "trialledger.targeted-question/1"
KEEP_ALIVE = "2m"  # a model left by a crashed run unloads itself; `release` unloads at once
RUBRICS = {
    "atom_claim": (
        "You check one claim against eligibility text. Use only the envelope: the target text, its "
        "section heading, scoping lines, stem and joined siblings. supported: the target states exactly "
        "the claim, with its values, its section's polarity and as a requirement. wrong_value: the target"
        " states this concept with different values. wrong_polarity_or_modality: the concept and values "
        "appear, but the text permits it, excludes it where the claim requires it (or the reverse), "
        "offers it as one alternative among others, or refers to past history rather than a current "
        "requirement. unsupported: the target does not state it. insufficient_context: the envelope does "
        "not hold enough to decide. Quote the shortest verbatim text from the envelope that decides your "
        "verdict; quote nothing only for unsupported or insufficient_context."
    ),
    "untyped_criterion": (
        "You name what one eligibility criterion states. Use only the envelope: the target text, its "
        "section heading, scoping lines, stem and joined siblings. The options are the concepts "
        "TrialLedger's banks type, named as concept or concept:instance (ecog_ps, age, biomarker:EGFR, "
        "lab:platelets, condition:hiv, prior_agent:PD-1, histology:squamous). Give one instance for each "
        "concept the target states, each with the shortest verbatim span of the target that states it; "
        "separate concepts are separate instances (EGFR or ALK is biomarker:EGFR and biomarker:ALK). "
        "out_of_taxonomy: a requirement of the target that no option names, with its verbatim span of the "
        "target. none: the target states no requirement at all. insufficient_context: the envelope does not "
        "hold enough to decide. none and insufficient_context stand alone. Name what the text states, "
        "whether it requires or excludes it."
    ),
    "outcome_endpoint": (
        "You check one claim about a registered outcome against its own measure title, the envelope's "
        "target. supported: the measure is an endpoint of the claimed class. wrong_value: the measure is an "
        "endpoint of a different class than the one claimed (disease-free where the claim says "
        "progression-free survival). unsupported: the measure does not name an endpoint of that class (the "
        "words appear in another sense or only as context). insufficient_context: the text does not hold "
        "enough to decide. Quote the shortest verbatim text from the envelope that decides your verdict; "
        "quote nothing only for unsupported or insufficient_context."
    ),
    "outcome_time_point": (
        "You check one claim about a registered outcome's time frame, the envelope's target, read with its "
        "measure (context). A claim says either that a time is the end of an observation window over which "
        "events are counted (up to N is always a window, not a scheduled measurement), or only that the time "
        "frame states a time point at N, with no role. supported: the time frame states the claimed time, as "
        "a window if the claim says window, as a time point (not only as the end of a window) if the claim "
        "says time point. wrong_value: it states a different time. wrong_role: only a window claimed where "
        "the time frame states that time as a time point, or a time point claimed where it states that time "
        "only as the end of a window. unsupported: the time frame does not state it. insufficient_context: "
        "the envelope does not hold enough to decide. Quote the shortest verbatim text from the envelope "
        "that decides your verdict; quote nothing only for unsupported or insufficient_context."
    ),
    "intervention_target": (
        "You check one claim about a drug intervention against its own registry entry: its description "
        "(the target) and its name (context). supported: the entry states that this intervention itself is "
        "a drug of the claimed class or acts on the claimed target. wrong_value: the entry states a "
        "different class or target for it. unsupported: the entry does not state it, or names the class "
        "only for something else (a prior therapy, a condition, a partner drug of a combination). "
        "insufficient_context: the entry does not hold enough to decide. Quote the shortest verbatim text "
        "from the envelope that decides your verdict; quote nothing only for unsupported or "
        "insufficient_context."
    ),
}

Http = Callable[[str, str, bytes | None, float], Any]  # method, url, body, timeout -> parsed JSON


class TransportError(Exception):
    """A named refusal or failure; never an answer."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def prompt_for(question: dict) -> str:
    """The canonical-JSON prompt for one question: the operation, its rubric and the question itself."""
    return canonical(
        {
            "protocol": PROTOCOL_VERSION,
            "operation": question["kind"],
            "rubric": RUBRICS[question["kind"]],
            "question": {k: question[k] for k in ("target", "envelope", "options")},
        }
    )


def request_body(model: str, prompt: str, schema: dict, options: dict) -> dict:
    """The Ollama `/api/generate` body: schema-constrained, temperature 0, explicit budgets, no stream."""
    return {
        "model": model,
        "prompt": prompt,
        "format": schema,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "think": options["think"],
        "options": {"temperature": 0, "num_ctx": options["num_ctx"], "num_predict": options["num_predict"]},
    }


def response_text(envelope: Any) -> tuple[str, str]:
    """The answer text of an Ollama envelope (pure — pinned).

    Returns ("ok", text), or ("invalid_response", "") when the envelope is not an object with a string
    `response`, or ("incomplete_output", "") when generation stopped at the output limit.
    """
    if not isinstance(envelope, dict) or not isinstance(envelope.get("response"), str):
        return "invalid_response", ""
    if envelope.get("done_reason") == "length":
        return "incomplete_output", ""
    return "ok", envelope["response"]


def installed_digest(tags: Any, model: str) -> tuple[str, str]:
    """The digest Ollama reports for exactly one installed `model` (pure — pinned).

    Returns ("ok", digest), ("invalid_tags", "") for a malformed listing, ("model_not_found_or_ambiguous", "")
    unless exactly one entry has that name, or ("invalid_digest", "") unless the digest is 64 lowercase hex.
    """
    if not isinstance(tags, dict) or not isinstance(tags.get("models"), list):
        return "invalid_tags", ""
    matches = [m for m in tags["models"] if isinstance(m, dict) and m.get("name") == model]
    if len(matches) != 1:
        return "model_not_found_or_ambiguous", ""
    digest = matches[0].get("digest")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        return "invalid_digest", ""
    return "ok", digest


class LocalModel:
    """One pinned local model, a call budget and an answer cache."""

    def __init__(
        self,
        model: str,
        http: Http,
        cache: Path,
        *,
        budget: int,
        base_url: str = "http://localhost:11434",
        timeout: float = 600.0,
        num_ctx: int = 16384,
        num_predict: int = 4096,
        think: bool = True,
    ) -> None:
        if not model.strip():
            raise TransportError("model_required")
        if budget <= 0:
            raise TransportError("call_budget_required")
        if num_predict + 1024 >= num_ctx:
            raise TransportError("invalid_output_budget")
        self.model, self.http, self.cache, self.budget = model, http, cache, budget
        self.base_url, self.timeout = base_url.rstrip("/"), timeout
        self.options = {"num_ctx": num_ctx, "num_predict": num_predict, "think": think}
        self.digest = ""
        self.calls = 0

    def _digest(self) -> str:
        code, digest = installed_digest(
            self.http("GET", f"{self.base_url}/api/tags", None, self.timeout), self.model
        )
        if code != "ok":
            raise TransportError(code)
        return digest

    def pin(self) -> str:
        """Pin the installed digest; a later change of the model under its tag refuses every answer. Refused
        while any other model is loaded, so two models never share the machine's memory."""
        running = self.http("GET", f"{self.base_url}/api/ps", None, self.timeout)
        others = [m.get("name") for m in (running or {}).get("models", []) if m.get("name") != self.model]
        if others:
            raise TransportError("another_model_loaded")
        digest = self._digest()
        if self.digest and digest != self.digest:
            raise TransportError("model_changed")
        self.digest = digest
        return digest

    def release(self) -> None:
        """Unload the model now (Ollama `keep_alive: 0`)."""
        body = canonical({"model": self.model, "keep_alive": 0}).encode("utf-8")
        self.http("POST", f"{self.base_url}/api/generate", body, self.timeout)

    def identity(self, kind: str) -> str:
        """The identity of this model asked one `kind` of question: the model, its digest and a digest of the
        protocol, that kind's rubric alone and the inference options. A rubric added or changed for another
        kind leaves it, and the answers cached under it, unchanged (design.md Decision 3); the one-entry
        rubric map has the shape the protocol digest had when `atom_claim` was the only kind, so an atom-claim
        answer cached then is still a hit."""
        if not self.digest:
            raise TransportError("model_not_pinned")
        hashed = canonical([PROTOCOL_VERSION, {kind: RUBRICS[kind]}, self.options])
        protocol = hashlib.sha256(hashed.encode()).hexdigest()[:16]
        return f"{self.model}#{self.digest}@{protocol}"

    def _cached(self) -> dict[str, str]:
        if not self.cache.is_file():
            return {}
        return {row["key"]: row["answer"] for row in map(json.loads, self.cache.read_text().splitlines())}

    def ask(self, question: dict, schema: dict) -> tuple[str, str, bool]:
        """The raw answer to one question: (answer text, identity, from the cache)."""
        prompt = prompt_for(question)
        identity = self.identity(question["kind"])
        key = hashlib.sha256(canonical([identity, prompt, schema]).encode()).hexdigest()
        saved = self._cached().get(key)
        if saved is not None:
            return saved, identity, True
        if len(prompt.encode("utf-8")) > self.options["num_ctx"] - self.options["num_predict"] - 1024:
            raise TransportError("context_exceeded")
        if self.calls >= self.budget:
            raise TransportError("call_budget_spent")
        if self._digest() != self.digest:
            raise TransportError("model_changed")
        body = canonical(request_body(self.model, prompt, schema, self.options)).encode("utf-8")
        self.calls += 1
        code, text = response_text(self.http("POST", f"{self.base_url}/api/generate", body, self.timeout))
        if code != "ok":
            raise TransportError(code)
        if self._digest() != self.digest:
            raise TransportError("model_changed")
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        with self.cache.open("a", encoding="utf-8") as out:
            out.write(
                canonical({"key": key, "identity": identity, "question": question["id"], "answer": text})
                + "\n"
            )
        return text, identity, False


def urllib_http(method: str, url: str, body: bytes | None, timeout: float) -> Any:
    """The real HTTP call, through the standard library (local Ollama only)."""
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    request = Request(url, data=body, method=method, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except TimeoutError as error:
        raise TransportError("model_timeout") from error
    except URLError as error:
        raise TransportError("model_connection_error") from error
    except ValueError as error:
        raise TransportError("invalid_response") from error
