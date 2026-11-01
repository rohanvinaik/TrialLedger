"""The serial audit loop.

Positive: each typed atom becomes one question with its own envelope; every eligibility piece, outcome and
intervention has a manifest row, and a row confirms the gaps between the pieces; questions are written before
answers; with a model, each answer is validated and written, the record is kept, and the model is released at
the end; balance.json counts the audited trials, and a declared sample audited whole has each empty cell asked
of the registry and a labelled supplement drawn and audited for it; every manifest, question and answer row
says how its trial was drawn; a stretch of eligibility text no piece covers is a manifest row with its
offsets, its text and its trial's drawn_as.
Negative: an untyped criterion has no question but keeps its manifest row; a trial already kept is never
fetched again; a model failure is recorded as a named error, never as a verdict; a supplement whose record
does not hold its cell fills no gap; a partial audit or a sample that declared no supplement asks the
registry nothing and calls no cell a gap; a supplement's rows are never labelled as the sample's; the
eligibility_gap row is never missing when the pieces also overlap."""

import json

from records import ongoing_study

from TrialLedger import audit
from TrialLedger.audit import run_audit, trial_questions
from TrialLedger.reading import read_population
from TrialLedger.sample import balance_declaration
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
    questions, manifest = trial_questions(s, view, "sample")
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
    assert {a["drawn_as"] for a in answers} == {"sample"}
    asked = [json.loads(line) for line in (tmp_path / "out" / "questions.jsonl").read_text().splitlines()]
    assert {q["drawn_as"] for q in asked} == {"sample"}
    assert http.posts[-1] == {"model": "qwen3:8b", "keep_alive": 0}
    again = run_audit(sample, tmp_path / "out", fetch=fetch, classes_for=lambda s: {}, limit=1)
    assert fetched == ["NCT09000001", "NCT09000002"] and again["trials"] == 1


def test_the_manifest_confirms_the_gaps_between_pieces(tmp_path):
    s = study()
    view = read_population([s], {})["views"][0]
    _questions, manifest = trial_questions(s, view, "sample")
    [coverage] = [row for row in manifest if row["unit"] == "eligibility_text"]
    assert coverage["status"] == "covered" and coverage["length"] == len(TEXT) and coverage["pieces"] == 5
    assert not [row for row in manifest if row["unit"] == "eligibility_gap"]


def read_balance(out):
    return json.loads((out / "balance.json").read_text())


def test_the_balance_table_names_gaps_and_audits_a_labelled_supplement(tmp_path):
    """A declared sample, audited whole: the registry is asked about each empty cell; one cell's frame holds
    a trial, which is drawn as a supplement, audited, and fills the gap; a supplement whose record does not
    hold its cell is named and fills nothing."""
    supplement = study("NCT09000003")
    supplement["protocolSection"]["designModule"] = {
        "studyType": "INTERVENTIONAL",
        "phases": ["PHASE3", "PHASE2"],  # listed out of the declared order: still the PHASE2|PHASE3 cell
        "designInfo": {"primaryPurpose": "SCREENING"},
    }
    records = {"NCT09000001": study("NCT09000001"), "NCT09000003": supplement}

    def query_ids(query, progress):
        text = query["filter.advanced"]
        phase4 = "AREA[Phase]PHASE4 AND NOT AREA[Phase]NA" in text  # PHASE4 held, not excluded
        if "AREA[DesignPrimaryPurpose]SCREENING" in text or phase4:
            return ["NCT09000003", "NCT09000001"], "2.0.5", "T"
        return [], "2.0.5", "T"

    sample = {"seed": "s", "balance": balance_declaration(), "trials": [{"nct": "NCT09000001"}]}
    out = tmp_path / "out"
    counts = run_audit(
        sample,
        out,
        fetch=lambda n: ([records[n]], "2.0.5", "T"),
        classes_for=lambda s: {},
        query_ids=query_ids,
    )
    assert counts["trials"] == 2 and counts["supplements"] == 1
    table = read_balance(out)
    rows = {(r["axis"], r["value"]): r for r in table["rows"]}
    assert rows["primary_purpose", "SCREENING"]["status"] == "gap_supplemented"
    assert rows["phase", "PHASE4"]["status"] == "gap" and rows["phase", "PHASE4"]["registry_count"] == 2
    assert rows["phase", "PHASE2|PHASE3"]["supplement"] == 1
    assert rows["phase", "PHASE1"]["status"] == "empty_in_registry"
    assert rows["intervention_type", "DRUG"]["drawn"] == 1 == rows["intervention_type", "DRUG"]["supplement"]
    by_cell = {(s["axis"], s["value"]): s for s in table["supplements"]}
    assert by_cell["primary_purpose", "SCREENING"]["holds_cell"] is True
    assert by_cell["phase", "PHASE4"]["holds_cell"] is False
    assert by_cell["phase", "PHASE4"]["inclusion_probability"] == 1.0
    assert table["supplement_snapshot"] == {"api_version": "2.0.5", "data_timestamp": "T"}
    lines = (out / "manifest.jsonl").read_text().splitlines()
    drawn_as = {json.loads(line)["nct"]: json.loads(line)["drawn_as"] for line in lines}
    assert drawn_as == {"NCT09000001": "sample", "NCT09000003": "supplement"}
    lines = (out / "questions.jsonl").read_text().splitlines()
    asked = {json.loads(line)["target"]["nct"]: json.loads(line)["drawn_as"] for line in lines}
    assert asked == {"NCT09000001": "sample", "NCT09000003": "supplement"}
    assert table["verified_query_forms"]["NOT AREA[Phase]"] == "2026-11-01"


def test_a_partial_or_undeclared_audit_asks_no_registry(tmp_path):
    asked = []

    def query_ids(query, progress):
        asked.append(query)
        return [], "2.0.5", "T"

    def fetch(nct):
        return [study(nct)], "2.0.5", "T"

    declared = {"seed": "s", "balance": balance_declaration()}
    declared["trials"] = [{"nct": "NCT09000001"}, {"nct": "NCT09000004"}]
    run_audit(declared, tmp_path / "a", fetch=fetch, classes_for=lambda s: {}, query_ids=query_ids, limit=1)
    old = {"seed": "s", "trials": [{"nct": "NCT09000001"}]}
    run_audit(old, tmp_path / "b", fetch=fetch, classes_for=lambda s: {}, query_ids=query_ids)
    assert asked == []
    for name, audited in (("a", 1), ("b", 1)):
        table = read_balance(tmp_path / name)
        assert table["audited"] == audited and table["supplements"] == []
        statuses = {r["status"] for r in table["rows"] if r["registry_value"]}
        assert statuses == {"present", "not_checked"}
    assert read_balance(tmp_path / "a")["of"] == 2 and read_balance(tmp_path / "b")["declared"] is False


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


def test_an_uncovered_stretch_is_an_eligibility_gap_row(monkeypatch):
    """A piece the itemizer drops (forced here) leaves its text uncovered: trial_questions names it in one
    eligibility_gap row with its offsets, its exact text and the trial's drawn_as; with an overlap as well,
    both are named."""
    real = audit.itemize

    def dropping(text):
        code, pieces = real(text)
        return code, pieces[:2] + pieces[3:]

    monkeypatch.setattr(audit, "itemize", dropping)
    s = study()
    view = read_population([s], {})["views"][0]
    _questions, manifest = trial_questions(s, view, "supplement")
    [coverage] = [row for row in manifest if row["unit"] == "eligibility_text"]
    assert coverage["status"] == "uncovered_text"
    [gap] = [row for row in manifest if row["unit"] == "eligibility_gap"]
    consent = TEXT.index("* Signed informed consent")
    assert gap["start"] <= consent and gap["end"] >= consent + len("* Signed informed consent")
    assert (
        gap["text"] == TEXT[gap["start"] : gap["end"]] and gap["text"].strip() == "* Signed informed consent"
    )
    assert gap["drawn_as"] == "supplement" and gap["status"] == "uncovered_text"
    assert {row["drawn_as"] for row in manifest} == {"supplement"}

    def overlapping(text):
        code, pieces = real(text)
        kind, section, start, _end = pieces[0]
        return code, [(kind, section, start, pieces[1][2] + 2), pieces[1], *pieces[3:]]

    monkeypatch.setattr(audit, "itemize", overlapping)
    _questions, manifest = trial_questions(s, view, "sample")
    [gap] = [row for row in manifest if row["unit"] == "eligibility_gap"]
    [overlap] = [row for row in manifest if row["unit"] == "eligibility_overlap"]
    assert gap["text"].strip() == "* Signed informed consent"
    assert overlap["text"] == TEXT[overlap["start"] : overlap["end"]] == "* "
    [coverage] = [row for row in manifest if row["unit"] == "eligibility_text"]
    assert coverage["status"] == "overlapping_and_uncovered"
