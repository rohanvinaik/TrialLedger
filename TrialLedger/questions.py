"""Targeted questions: one specific question, closed options, a bounded source envelope.

Specified in openspec/changes/add-targeted-questions. The symbolic system decides which questions exist and
what each may see; a model only answers. A question's envelope is deterministic: the target piece of
eligibility text with its offsets, the section heading it sits under, the scoping lines between that heading
and it (a cohort line such as "Cohort B only:"), the stem it continues (a previous piece ending in a colon),
and its neighbours when an explicit "and"/"or" joins them. It never resolves those relationships; it hands
over the text that bears on them. An envelope over its budget is refused, never truncated. An answer is
validated deterministically: its verdict is one of the closed options and its quote lies verbatim in the
envelope (a location check, not entailment).
"""

from __future__ import annotations

import hashlib
import json
import re

ENVELOPE_BUDGET = 4000  # bytes of envelope text; a larger envelope is refused, never cut
ATOM_CLAIM_OPTIONS = (
    "supported",
    "wrong_value",
    "wrong_polarity_or_modality",
    "unsupported",
    "insufficient_context",
)
_JOIN_AT_END = re.compile(r"(?:\bor|\band|\band/or|;\s*or|;\s*and)\s*$", re.IGNORECASE)
_JOIN_AT_START = re.compile(r"^\W*(?:or|and|and/or)\b", re.IGNORECASE)

Piece = tuple[str, str, int, int]  # kind, section, start, end (criteria.itemize)


def envelope(text: str, pieces: list[Piece], index: int, budget: int = ENVELOPE_BUDGET) -> tuple[str, dict]:
    """The envelope of piece `index` of an itemized eligibility text (pure — pinned).

    Returns ("ok", envelope) or ("envelope_over_budget", {}) or ("not_a_criterion", {}). The envelope holds
    the target (text, start, end, section), the nearest heading before it, the scoping lines (prose pieces
    ending in a colon) between that heading and it, the stem (the piece just before it, when that piece ends
    in a colon), and the siblings (the criteria just before and after it, when an explicit "and"/"or" joins
    them).
    """
    kind, section, start, end = pieces[index]
    if kind != "criterion":
        return "not_a_criterion", {}
    target = text[start:end]
    heading_at = next((i for i in range(index - 1, -1, -1) if pieces[i][0] == "heading"), -1)
    headings = [text[pieces[heading_at][2] : pieces[heading_at][3]]] if heading_at >= 0 else []
    scoping = [
        text[s:e]
        for k, _sec, s, e in pieces[heading_at + 1 : index]
        if k == "prose" and text[s:e].rstrip().endswith(":")
    ]
    previous = pieces[index - 1] if index > 0 else None
    following = pieces[index + 1] if index + 1 < len(pieces) else None
    stem = ""
    if previous and previous[0] == "criterion" and text[previous[2] : previous[3]].rstrip().endswith(":"):
        stem = text[previous[2] : previous[3]]
    siblings = []
    if previous and previous[0] == "criterion" and not stem:
        before = text[previous[2] : previous[3]]
        if _JOIN_AT_END.search(before) or _JOIN_AT_START.search(target):
            siblings.append(before)
    if following and following[0] == "criterion":
        after = text[following[2] : following[3]]
        if _JOIN_AT_END.search(target) or _JOIN_AT_START.search(after):
            siblings.append(after)
    held = {
        "target": {"text": target, "start": start, "end": end, "section": section},
        "headings": headings,
        "scoping": scoping,
        "stem": stem,
        "siblings": siblings,
    }
    size = sum(len(part.encode("utf-8")) for part in [target, *headings, *scoping, stem, *siblings])
    if size > budget:
        return "envelope_over_budget", {}
    return "ok", held


def atom_claim(atom: tuple, section: str) -> str:
    """The claim one typed atom makes about its criterion, in words a reader checks against the text."""
    _bank, concept, values, params, _s, _e = atom
    detail = "; ".join(f"{name} {value}" for name, value in params)
    stated = f"{concept} = {' | '.join(values)}" + (f" ({detail})" if detail else "")
    if section == "exclusion":
        return f"This exclusion criterion excludes participants with: {stated}"
    if section == "inclusion":
        return f"This inclusion criterion requires participants to have: {stated}"
    return f"This criterion (no inclusion or exclusion heading) states: {stated}"


def question(kind: str, target: dict, held: dict, options: tuple[str, ...]) -> dict:
    """A question object with its id: a hash of everything the model will see."""
    body = {"kind": kind, "target": target, "envelope": held, "options": list(options)}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {"id": digest[:16], **body}


def answer_schema(options: tuple[str, ...]) -> dict:
    """The JSON schema an answer must satisfy: one closed verdict and the verbatim quote it rests on."""
    return {
        "type": "object",
        "properties": {"verdict": {"type": "string", "enum": list(options)}, "quote": {"type": "string"}},
        "required": ["verdict", "quote"],
        "additionalProperties": False,
    }


def validate_answer(raw: str, options: tuple[str, ...], held: dict) -> tuple[str, str, str]:
    """A model's raw answer, checked (pure — pinned).

    Returns (code, verdict, quote): ("ok", verdict, quote) when the answer is a JSON object with exactly a
    verdict among `options` and a quote; the quote must lie verbatim in the envelope's text unless the verdict
    is "insufficient_context" or "unsupported" (which may quote nothing). Otherwise a named audit error with
    empty verdict and quote: "malformed", "unknown_verdict", "quote_not_in_envelope".
    """
    try:
        answer = json.loads(raw)
    except (ValueError, TypeError):
        return "malformed", "", ""
    if not isinstance(answer, dict) or set(answer) != {"verdict", "quote"}:
        return "malformed", "", ""
    verdict, quote = answer["verdict"], answer["quote"]
    if not isinstance(verdict, str) or not isinstance(quote, str):
        return "malformed", "", ""
    if verdict not in options:
        return "unknown_verdict", "", ""
    texts = [held["target"]["text"], *held["headings"], *held["scoping"], held["stem"], *held["siblings"]]
    if quote.strip() and not any(quote.strip() in part for part in texts):
        return "quote_not_in_envelope", "", ""
    if not quote.strip() and verdict not in ("insufficient_context", "unsupported"):
        return "quote_not_in_envelope", "", ""
    return "ok", verdict, quote
