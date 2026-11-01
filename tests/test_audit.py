"""The serial audit loop.

Positive: each typed atom becomes one question with its own envelope; every eligibility piece, outcome and
intervention has a manifest row; questions are written before answers; with a model, each answer is validated
and written, the record is kept, and the model is released at the end.
Negative: an untyped criterion has no question but keeps its manifest row; a trial already kept is never
fetched again; a model failure is recorded as a named error, never as a verdict."""

import json

from records import ongoing_study

from TrialLedger.audit import run_audit, trial_questions
from TrialLedger.reading import read_population
from TrialLedger.transport import LocalModel

TEXT = (
    "Inclusion Criteria:\n\n* ECOG performance status 0-1\n* Signed informed consent\n\n"
    "Exclusion Criteria:\n\n* Active autoimmune disease\n"
)


def study(nct="NCT09000001"):
    s = ongoing_study()
    s["protocolSection"]["identificationModule"]["nctId"] = nct
    s["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = TEXT
    s["protocolSection"]["outcomesModule"] = {
        "primaryOutcomes": [{"measure": "Overall survival", "timeFrame": "Up to 24 months"}]
    }
    s["protocolSection"]["armsInterventionsModule"] = {
        "armGroups": [{"label": "A", "type": "EXPERIMENTAL", "interventionNames": ["Drug: XB-1"]}],
        "interventions": [{"type": "DRUG", "name": "XB-1", "description": "XB-1 is an anti-PD-1 antibody"}],
    }
    return s


def test_every_atom_is_one_question_and_every_piece_a_row():
    s = study()
    view = read_population([s], {})["views"][0]
    questions, manifest = trial_questions(s, view)
    atoms = sum(len(atoms) for _i, _s, _t, atoms in view["criteria"])
    assert len(questions) == atoms > 0
    assert {q["kind"] for q in questions} == {"atom_claim"}
    assert all(q["target"]["nct"] == "NCT09000001" for q in questions)
    eligibility = [row for row in manifest if row["unit"] == "eligibility"]
    assert [row["kind"] for row in eligibility] == [
        "heading",
        "criterion",
        "criterion",
        "heading",
        "criterion",
    ]
    consent = next(row for row in eligibility if row["start"] == TEXT.index("* Signed"))
    assert consent["status"] in ("untyped", "typed")
    assert not any(q["target"]["piece"] == consent["piece"] for q in questions) or consent["atoms"] > 0
    outcome = next(row for row in manifest if row["unit"] == "outcome")
    assert outcome["text"] == "Overall survival" and outcome["frame"] == "Up to 24 months"
    drug = next(row for row in manifest if row["unit"] == "intervention")
    assert drug["text"] == "XB-1" and drug["state"] == "stated_by_record"


class FakeOllama:
    def __init__(self, answer):
        self.answer = answer
        self.posts = []

    def __call__(self, method, url, body, timeout):
        if url.endswith("/api/ps"):
            return {"models": []}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "qwen3:8b", "digest": "a" * 64}]}
        self.posts.append(json.loads(body))
        return {"response": self.answer}


def test_the_loop_keeps_records_writes_questions_then_answers_and_releases(tmp_path):
    fetched = []

    def fetch(nct):
        fetched.append(nct)
        return [study(nct)], "2.0.5", "T"

    http = FakeOllama(json.dumps({"verdict": "insufficient_context", "quote": ""}))
    model = LocalModel("qwen3:8b", http, tmp_path / "cache.jsonl", budget=50)
    model.pin()
    sample = {"trials": [{"nct": "NCT09000001"}, {"nct": "NCT09000002"}]}
    counts = run_audit(sample, tmp_path / "out", fetch=fetch, classes_for=lambda s: {}, model=model)
    assert counts["trials"] == 2 and counts["questions"] == counts["answered"] > 0
    assert (tmp_path / "out" / "records" / "NCT09000001.json").is_file()
    answers = [json.loads(line) for line in (tmp_path / "out" / "answers.jsonl").read_text().splitlines()]
    assert {a["code"] for a in answers} == {"ok"} and {a["verdict"] for a in answers} == {
        "insufficient_context"
    }
    assert http.posts[-1] == {"model": "qwen3:8b", "keep_alive": 0}
    again = run_audit(sample, tmp_path / "out", fetch=fetch, classes_for=lambda s: {}, limit=1)
    assert fetched == ["NCT09000001", "NCT09000002"] and again["trials"] == 1


def test_a_bad_answer_is_a_named_error(tmp_path):
    http = FakeOllama(json.dumps({"verdict": "supported", "quote": "not in the envelope"}))
    model = LocalModel("qwen3:8b", http, tmp_path / "cache.jsonl", budget=1)
    model.pin()
    sample = {"trials": [{"nct": "NCT09000001"}]}
    counts = run_audit(
        sample,
        tmp_path / "out",
        fetch=lambda n: ([study(n)], "v", "t"),
        classes_for=lambda s: {},
        model=model,
    )
    codes = [
        json.loads(line)["code"] for line in (tmp_path / "out" / "answers.jsonl").read_text().splitlines()
    ]
    assert codes[0] == "quote_not_in_envelope" and "call_budget_spent" in codes
    assert counts["answer_errors"] == len(codes) and counts["answered"] == 0
