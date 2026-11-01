"""The local-model transport: GSE's contract.

Positive: a pinned model answers a schema-constrained, temperature-0 request built from the canonical prompt;
the answer is cached under its identity, and a second ask is a cache hit with no call.
Negative: no model, no budget or an output budget that leaves no room is refused; an unpinned model, a changed
digest, a prompt over the context budget, a spent call budget, a malformed or truncated response are named
errors, never answers.
"""

import json

import pytest

from TrialLedger.questions import ATOM_CLAIM_OPTIONS, answer_schema, question
from TrialLedger.transport import (
    RUBRICS,
    LocalModel,
    TransportError,
    installed_digest,
    prompt_for,
    request_body,
    response_text,
)

DIGEST = "a" * 64
HELD = {"target": {"text": "* ECOG 0-1"}, "headings": [], "scoping": [], "stem": "", "siblings": []}
QUESTION = question("atom_claim", {"claim": "ecog 0|1"}, HELD, ATOM_CLAIM_OPTIONS)
SCHEMA = answer_schema(ATOM_CLAIM_OPTIONS)


class FakeOllama:
    def __init__(self, digests=(DIGEST,), response=None):
        self.digests = list(digests)
        self.posts = []
        self.response = response or {"response": json.dumps({"verdict": "supported", "quote": "ECOG 0-1"})}

    loaded = ()

    def __call__(self, method, url, body, timeout):
        if url.endswith("/api/ps"):
            return {"models": [{"name": name} for name in self.loaded]}
        if method == "GET":
            digest = self.digests[0] if len(self.digests) == 1 else self.digests.pop(0)
            return {"models": [{"name": "qwen", "digest": digest}]}
        self.posts.append(json.loads(body))
        return self.response


def model(tmp_path, http, **options):
    local = LocalModel("qwen", http, tmp_path / "answers.jsonl", budget=options.pop("budget", 5), **options)
    local.pin()
    return local


def test_a_pinned_model_answers_and_the_answer_is_cached(tmp_path):
    http = FakeOllama()
    local = model(tmp_path, http)
    text, identity, cached = local.ask(QUESTION, SCHEMA)
    assert json.loads(text) == {"verdict": "supported", "quote": "ECOG 0-1"} and not cached
    assert identity.startswith(f"qwen#{DIGEST}@")
    sent = http.posts[0]
    assert sent["format"] == SCHEMA and sent["options"]["temperature"] == 0 and sent["stream"] is False
    assert json.loads(sent["prompt"])["question"]["envelope"] == HELD
    again = model(tmp_path, FakeOllama())
    assert again.ask(QUESTION, SCHEMA) == (text, identity, True)
    assert again.calls == 0


def test_the_identity_is_per_question_kind(tmp_path, monkeypatch):
    """Positive: the atom-claim identity hashes only its own rubric, in the shape it had when it was the only
    kind (so an answer cached then is still a hit); another kind's rubric added or changed leaves it as it
    was. Negative: a change to its own rubric changes it, and two kinds never share an identity."""
    import hashlib

    from TrialLedger import transport

    local = model(tmp_path, FakeOllama())
    alone = transport.canonical(
        [transport.PROTOCOL_VERSION, {"atom_claim": RUBRICS["atom_claim"]}, local.options]
    )
    assert local.identity("atom_claim") == f"qwen#{DIGEST}@{hashlib.sha256(alone.encode()).hexdigest()[:16]}"
    before = local.identity("atom_claim")
    assert local.identity("outcome_endpoint") != before
    monkeypatch.setitem(transport.RUBRICS, "new_kind", "Another rubric.")
    monkeypatch.setitem(transport.RUBRICS, "outcome_endpoint", "A changed rubric.")
    assert local.identity("atom_claim") == before
    monkeypatch.setitem(transport.RUBRICS, "atom_claim", RUBRICS["atom_claim"] + " Changed.")
    assert local.identity("atom_claim") != before


def test_the_prompt_and_body_are_canonical():
    prompt = json.loads(prompt_for(QUESTION))
    assert prompt["operation"] == "atom_claim" and set(prompt["question"]) == {
        "target",
        "envelope",
        "options",
    }
    body = request_body("m", "p", {"type": "object"}, {"think": False, "num_ctx": 4096, "num_predict": 512})
    assert body["think"] is False and body["options"] == {
        "temperature": 0,
        "num_ctx": 4096,
        "num_predict": 512,
    }


def test_a_bad_configuration_is_refused(tmp_path):
    with pytest.raises(TransportError, match="model_required"):
        LocalModel(" ", FakeOllama(), tmp_path / "a", budget=1)
    with pytest.raises(TransportError, match="call_budget_required"):
        LocalModel("qwen", FakeOllama(), tmp_path / "a", budget=0)
    with pytest.raises(TransportError, match="invalid_output_budget"):
        LocalModel("qwen", FakeOllama(), tmp_path / "a", budget=1, num_ctx=2048, num_predict=1024)


def test_an_unpinned_or_changed_model_is_refused(tmp_path):
    unpinned = LocalModel("qwen", FakeOllama(), tmp_path / "a", budget=1)
    with pytest.raises(TransportError, match="model_not_pinned"):
        unpinned.ask(QUESTION, SCHEMA)
    changed = model(tmp_path, FakeOllama(digests=(DIGEST, "b" * 64, "b" * 64)))
    with pytest.raises(TransportError, match="model_changed"):
        changed.ask(QUESTION, SCHEMA)
    after = model(tmp_path / "x", FakeOllama(digests=(DIGEST, DIGEST, "b" * 64)))
    with pytest.raises(TransportError, match="model_changed"):
        after.ask(QUESTION, SCHEMA)
    assert not (tmp_path / "x" / "answers.jsonl").exists()


def test_budgets_and_bad_responses_are_named_errors(tmp_path):
    small = model(tmp_path / "s", FakeOllama(), num_ctx=2048, num_predict=512)
    big = question("atom_claim", {"claim": "x" * 4000}, HELD, ATOM_CLAIM_OPTIONS)
    with pytest.raises(TransportError, match="context_exceeded"):
        small.ask(big, SCHEMA)
    spent = model(tmp_path / "b", FakeOllama(), budget=1)
    spent.ask(QUESTION, SCHEMA)
    other = question("atom_claim", {"claim": "other"}, HELD, ATOM_CLAIM_OPTIONS)
    with pytest.raises(TransportError, match="call_budget_spent"):
        spent.ask(other, SCHEMA)
    cut = model(tmp_path / "c", FakeOllama(response={"response": "{", "done_reason": "length"}))
    with pytest.raises(TransportError, match="incomplete_output"):
        cut.ask(QUESTION, SCHEMA)


def test_response_and_tag_decisions():
    assert response_text({"response": "x"}) == ("ok", "x")
    assert response_text({"response": "x", "done_reason": "stop"}) == ("ok", "x")
    assert response_text({"response": "x", "done_reason": "length"}) == ("incomplete_output", "")
    assert response_text([]) == ("invalid_response", "")
    assert response_text({"response": 1}) == ("invalid_response", "")
    tags = {"models": [{"name": "qwen", "digest": DIGEST}, {"name": "other", "digest": DIGEST}]}
    assert installed_digest(tags, "qwen") == ("ok", DIGEST)
    assert installed_digest(tags, "missing") == ("model_not_found_or_ambiguous", "")
    twice = {"models": [{"name": "qwen", "digest": DIGEST}, {"name": "qwen", "digest": DIGEST}]}
    assert installed_digest(twice, "qwen") == ("model_not_found_or_ambiguous", "")
    assert installed_digest({"models": [{"name": "qwen", "digest": "A" * 64}]}, "qwen") == (
        "invalid_digest",
        "",
    )
    assert installed_digest({"models": [{"name": "qwen", "digest": "a" * 63}]}, "qwen") == (
        "invalid_digest",
        "",
    )
    assert installed_digest({"models": "x"}, "qwen") == ("invalid_tags", "")
    assert installed_digest([], "qwen") == ("invalid_tags", "")


def test_memory_is_released_and_never_shared(tmp_path):
    """Positive: release unloads the model at once; every request sets a short keep-alive. Negative: a pin is
    refused while another model is loaded."""
    http = FakeOllama()
    local = model(tmp_path, http)
    local.ask(QUESTION, SCHEMA)
    assert http.posts[0]["keep_alive"] == "2m"
    local.release()
    assert http.posts[-1] == {"model": "qwen", "keep_alive": 0}
    busy = FakeOllama()
    busy.loaded = ("other-model",)
    with pytest.raises(TransportError, match="another_model_loaded"):
        LocalModel("qwen", busy, tmp_path / "b", budget=1).pin()
    same = FakeOllama()
    same.loaded = ("qwen",)
    assert LocalModel("qwen", same, tmp_path / "c", budget=1).pin() == DIGEST
