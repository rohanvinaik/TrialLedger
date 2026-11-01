"""The serial audit loop.

Positive: each typed atom becomes one atom-claim question with its own envelope; a criterion no bank typed
becomes one untyped-criterion question; each endpoint class and time point of an outcome is one question on
that outcome's own field; each target an experimental drug's own entry states is one question on that entry;
an RxClass assignment is checked against the kept RxClass answer and recorded, never asked; every eligibility
piece, outcome and intervention has a manifest row, and a row confirms the gaps between the pieces; questions
are written before answers; with a model, each answer is validated under its own kind's schema and written,
the record is kept, out_of_taxonomy answers are counted apart, and the model is released at the end;
balance.json counts the audited trials, and a declared sample audited whole has each empty cell asked of the
registry and a labelled supplement drawn and audited for it; every manifest, question and answer row says how
its trial was drawn; a stretch of eligibility text no piece covers is a manifest row with its offsets, its
text and its trial's drawn_as.
Negative: no question carries another unit's text; an RxClass assignment that differs from the answer kept
in the audit folder (read back from disk), or whose name has no kept answer, is recorded as such; a drug whose
lookup failed or was never answered is never recorded as unclassed; a kept answer is never rewritten; a trial
already kept is never fetched again; a model failure is recorded as a named error, never as a verdict; a
supplement whose record does not hold its cell fills no gap; a partial audit or a sample that declared no
supplement asks the registry nothing and calls no cell a gap; a supplement's rows are never labelled as the
sample's; the eligibility_gap row is never missing when the pieces also overlap."""

import json

from records import ongoing_study

from TrialLedger import audit
from TrialLedger.audit import keep_rxclass, run_audit, rxclass_absence, rxclass_check, trial_questions
from TrialLedger.reading import read_population
from TrialLedger.sample import balance_declaration
from TrialLedger.transport import LocalModel

# "History of active or past meningococcal disease" is a real criterion no bank types (NCT04382755).
TEXT = (
    "Inclusion Criteria:\n\n* ECOG performance status 0-1\n* Signed informed consent\n\n"
    "Exclusion Criteria:\n\n* Active autoimmune disease\n* History of active or past meningococcal disease\n"
)
PD1 = ["N0000191260", "Programmed Death Receptor-1 Blocking Antibody", "has_epc", "DAILYMED"]
ANSWERS = {"Testamab": {"codes": {"DAILYMED:has_epc": "found"}, "classes": [PD1]}}


def study(nct="NCT09000001"):
    s = ongoing_study()
    s["protocolSection"]["identificationModule"]["nctId"] = nct
    s["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = TEXT
    s["protocolSection"]["outcomesModule"] = {
        "primaryOutcomes": [{"measure": "Overall survival", "timeFrame": "Up to 24 months"}],
        # NCT04693377's secondary outcome, as registered
        "secondaryOutcomes": [{"measure": "Pain response", "timeFrame": "At 12 weeks post-treatment"}],
    }
    s["protocolSection"]["armsInterventionsModule"] = {
        "armGroups": [
            {"label": "A", "type": "EXPERIMENTAL", "interventionNames": ["Drug: XB-1", "Drug: Testamab"]}
        ],
        "interventions": [
            {"type": "DRUG", "name": "XB-1", "description": "XB-1 is an anti-PD-1 antibody"},
            {"type": "DRUG", "name": "Testamab"},
        ],
    }
    return s


def test_every_unit_has_its_kind_of_question_and_every_piece_a_row():
    s = study()
    view = read_population([s], ANSWERS)["views"][0]
    questions, manifest = trial_questions(s, view, ANSWERS, "sample")
    kinds = [q["kind"] for q in questions]
    atoms = sum(len(atoms) for _i, _s, _t, atoms in view["criteria"])
    assert kinds.count("atom_claim") == atoms > 0
    assert all(q["target"]["nct"] == "NCT09000001" for q in questions)
    eligibility = [row for row in manifest if row["unit"] == "eligibility"]
    assert [row["kind"] for row in eligibility] == [
        "heading",
        "criterion",
        "criterion",
        "heading",
        "criterion",
        "criterion",
    ]
    untyped = [q for q in questions if q["kind"] == "untyped_criterion"]
    assert len(untyped) == 1
    assert untyped[0]["envelope"]["target"]["text"] == "* History of active or past meningococcal disease"
    assert untyped[0]["envelope"]["headings"] == ["Exclusion Criteria:"]
    assert "out_of_taxonomy" in untyped[0]["options"] and "condition:hiv" in untyped[0]["options"]
    assert eligibility[-1]["status"] == "untyped" and eligibility[1]["instances"] == ["ecog_ps"]

    endpoint = next(q for q in questions if q["kind"] == "outcome_endpoint")
    assert endpoint["target"]["endpoint"] == "overall_survival"
    assert endpoint["envelope"]["target"]["text"] == "Overall survival"
    assert endpoint["envelope"]["target"]["field"] == "outcomesModule.primaryOutcomes[0].measure"
    points = {
        q["envelope"]["target"]["text"]: q["target"] for q in questions if q["kind"] == "outcome_time_point"
    }
    assert points["Up to 24 months"]["role"] == "window" and points["Up to 24 months"]["point"] == "24 month"
    assert points["At 12 weeks post-treatment"]["role"] == "unmarked"
    assert (
        points["At 12 weeks post-treatment"]["claim"] == "This time frame states a time point at 12 week(s)"
    )
    frame = next(q for q in questions if q["kind"] == "outcome_time_point")
    assert frame["envelope"]["context"] == [
        {"field": "outcomesModule.primaryOutcomes[0].measure", "text": "Overall survival"}
    ]
    outcomes = [row for row in manifest if row["unit"] == "outcome"]
    assert [row["status"] for row in outcomes] == ["asked", "asked"]
    assert outcomes[1]["classes"] == [] and outcomes[1]["questions"] == 1

    target = next(q for q in questions if q["kind"] == "intervention_target")
    assert target["target"]["stated"] == "PD-1" and target["target"]["drug"] == "XB-1"
    assert target["envelope"]["target"]["text"] == "XB-1 is an anti-PD-1 antibody"
    assert target["envelope"]["context"][0]["text"] == "XB-1"
    drugs = {row["text"]: row for row in manifest if row["unit"] == "intervention"}
    assert drugs["XB-1"]["status"] == "asked" and drugs["XB-1"]["state"] == "stated_by_record"
    assert (
        drugs["Testamab"]["status"] == "rxclass_checked"
        and drugs["Testamab"]["rxclass"] == "matches_artifact"
    )
    assert drugs["Testamab"]["artifact"] == [PD1]
    assert not any("Testamab" in json.dumps(q) for q in questions)
    for q in questions:
        assert "Overall survival" not in json.dumps(q["envelope"]) or q["kind"].startswith("outcome")


def test_an_rxclass_assignment_is_checked_against_the_kept_answer():
    assert rxclass_check(ANSWERS, "Testamab", [PD1[1]]) == ("matches_artifact", [PD1])
    assert rxclass_check(ANSWERS, "Testamab", ["Kinase Inhibitor"]) == ("differs_from_artifact", [PD1])
    assert rxclass_check(ANSWERS, "Testamab", []) == ("differs_from_artifact", [PD1])
    assert rxclass_check(ANSWERS, "TM-1", [PD1[1]]) == ("not_in_artifact", [])
    assert rxclass_check({"X": {"codes": {}}}, "X", []) == ("not_in_artifact", [])
    moa = ["N1", "PD-1 Receptor Antagonists", "has_moa", "MEDRT"]
    assert rxclass_check({"X": {"classes": [moa]}}, "X", []) == ("matches_artifact", [moa])


NOT_FOUND = {"codes": {"DAILYMED:has_epc": "not_found", "MEDRT:has_moa": "not_found"}, "classes": []}


def test_a_drug_no_class_resolves_is_never_asked_and_says_why():
    """Positive: a drug RxClass established as unclassed (every query not_found) is recorded so. Negative: a
    drug whose lookup failed or was never answered is recorded as not established, never as unclassed; neither
    is asked."""
    s = study()
    s["protocolSection"]["armsInterventionsModule"]["interventions"][0]["description"] = (
        "Intravenous infusion"
    )
    failed = {"codes": {"DAILYMED:has_epc": "lookup_failed", "MEDRT:has_moa": "not_found"}, "classes": []}
    answers = {"XB-1": NOT_FOUND, "Testamab": failed}
    view = read_population([s], answers)["views"][0]
    questions, manifest = trial_questions(s, view, answers, "sample")
    drugs = {row["text"]: row for row in manifest if row["unit"] == "intervention"}
    assert drugs["XB-1"]["status"] == drugs["XB-1"]["rxclass"] == "rxclass_unclassed"
    assert drugs["Testamab"]["status"] == "rxclass_not_established"
    assert not any(q["kind"] == "intervention_target" for q in questions)
    never = trial_questions(s, read_population([s], {})["views"][0], {}, "sample")[1]
    statuses = {row["text"]: row["status"] for row in never if row["unit"] == "intervention"}
    assert statuses == {"XB-1": "rxclass_not_established", "Testamab": "rxclass_not_established"}


def test_what_the_kept_answers_say_of_a_drug_with_no_class():
    """Positive: every alias not_found on every query is unclassed. Negative: a failure, a malformed body, an
    unanswered alias, no alias or empty codes is not established; a kept class the reading lacks differs."""
    malformed = {"codes": {"DAILYMED:has_epc": "malformed", "MEDRT:has_moa": "not_found"}, "classes": []}
    assert rxclass_absence({"a": NOT_FOUND, "b": NOT_FOUND}, ["a", "b"]) == "rxclass_unclassed"
    assert rxclass_absence({"a": NOT_FOUND}, ["a", "b"]) == "rxclass_not_established"
    assert rxclass_absence({"a": malformed}, ["a"]) == "rxclass_not_established"
    assert rxclass_absence({"a": {"codes": {}, "classes": []}}, ["a"]) == "rxclass_not_established"
    assert rxclass_absence({}, []) == "rxclass_not_established"
    assert rxclass_absence({"a": NOT_FOUND, "b": ANSWERS["Testamab"]}, ["a", "b"]) == "differs_from_artifact"


class FakeOllama:
    """Answers each kind in its own schema: insufficient context, or for an untyped criterion a requirement
    outside the taxonomy, quoted from the criterion."""

    def __init__(self, answer=None):
        self.answer = answer
        self.posts = []

    def __call__(self, method, url, body, timeout):
        if url.endswith("/api/ps"):
            return {"models": []}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "qwen3:8b", "digest": "a" * 64}]}
        posted = json.loads(body)
        self.posts.append(posted)
        if self.answer is not None:
            return {"response": self.answer}
        if json.loads(posted.get("prompt", "{}")).get("operation") == "untyped_criterion":
            instance = {"option": "out_of_taxonomy", "quote": "meningococcal disease"}
            return {"response": json.dumps({"instances": [instance]})}
        return {"response": json.dumps({"verdict": "insufficient_context", "quote": ""})}


def test_the_loop_keeps_records_writes_questions_then_answers_and_releases(tmp_path):
    fetched = []

    def fetch(nct):
        fetched.append(nct)
        return [study(nct)], "2.0.5", "T"

    http = FakeOllama()
    model = LocalModel("qwen3:8b", http, tmp_path / "cache.jsonl", budget=80)
    model.pin()
    sample = {"trials": [{"nct": "NCT09000001"}, {"nct": "NCT09000002"}]}
    counts = run_audit(sample, tmp_path / "out", fetch=fetch, classes_for=lambda s: ANSWERS, model=model)
    assert counts["trials"] == 2 and counts["questions"] == counts["answered"] > 0
    assert counts["out_of_taxonomy"] == 2 and counts["answer_errors"] == 0
    assert (tmp_path / "out" / "records" / "NCT09000001.json").is_file()
    answers = [json.loads(line) for line in (tmp_path / "out" / "answers.jsonl").read_text().splitlines()]
    assert {a["code"] for a in answers} == {"ok"}
    assert {a["verdict"] for a in answers} == {"insufficient_context", "out_of_taxonomy"}
    untyped = next(a for a in answers if a["kind"] == "untyped_criterion")
    assert untyped["instances"] == [["out_of_taxonomy", "meningococcal disease"]]
    assert {a["drawn_as"] for a in answers} == {"sample"}
    written = [json.loads(line) for line in (tmp_path / "out" / "questions.jsonl").read_text().splitlines()]
    assert [q["id"] for q in written] == [a["question"] for a in answers]
    assert {q["drawn_as"] for q in written} == {"sample"}
    assert http.posts[-1] == {"model": "qwen3:8b", "keep_alive": 0}
    again = run_audit(sample, tmp_path / "out", fetch=fetch, classes_for=lambda s: {}, limit=1)
    assert fetched == ["NCT09000001", "NCT09000002"] and again["trials"] == 1


def test_the_manifest_confirms_the_gaps_between_pieces(tmp_path):
    s = study()
    view = read_population([s], {})["views"][0]
    _questions, manifest = trial_questions(s, view, {}, "sample")
    [coverage] = [row for row in manifest if row["unit"] == "eligibility_text"]
    assert coverage["status"] == "covered" and coverage["length"] == len(TEXT) and coverage["pieces"] == 6
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
    _questions, manifest = trial_questions(s, view, {}, "supplement")
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
    _questions, manifest = trial_questions(s, view, {}, "sample")
    [gap] = [row for row in manifest if row["unit"] == "eligibility_gap"]
    [overlap] = [row for row in manifest if row["unit"] == "eligibility_overlap"]
    assert gap["text"].strip() == "* Signed informed consent"
    assert overlap["text"] == TEXT[overlap["start"] : overlap["end"]] == "* "
    [coverage] = [row for row in manifest if row["unit"] == "eligibility_text"]
    assert coverage["status"] == "overlapping_and_uncovered"


def test_a_malformed_untyped_answer_is_a_named_error(tmp_path):
    """Positive: an untyped criterion's answer is validated under its own schema. Negative: a claim-shaped
    answer to it is malformed, never a reading."""
    http = FakeOllama(json.dumps({"verdict": "supported", "quote": "meningococcal disease"}))
    model = LocalModel("qwen3:8b", http, tmp_path / "cache.jsonl", budget=80)
    model.pin()
    run_audit(
        {"trials": [{"nct": "NCT09000001"}]},
        tmp_path / "out",
        fetch=lambda n: ([study(n)], "v", "t"),
        classes_for=lambda s: {},
        model=model,
    )
    rows = [json.loads(line) for line in (tmp_path / "out" / "answers.jsonl").read_text().splitlines()]
    untyped = next(row for row in rows if row["kind"] == "untyped_criterion")
    assert untyped["code"] == "malformed" and untyped["verdict"] == "" and untyped["instances"] == []


def manifest_drugs(out):
    rows = [json.loads(line) for line in (out / "manifest.jsonl").read_text().splitlines()]
    return {row["text"]: row for row in rows if row["unit"] == "intervention"}


def test_the_rxclass_answers_used_are_kept_with_their_retrieval_times(tmp_path):
    """Positive: run_audit copies the answers for the trial's drug names into the audit folder, each with its
    retrieval time (None when the answer carried none), and the reading's classes match that kept copy.
    Negative: a name the trial does not use is not copied; a kept answer is never rewritten."""
    used = {"Testamab": {**ANSWERS["Testamab"], "retrieved": "2026-10-31T12:00:00+00:00"}, "XB-1": NOT_FOUND}
    answers = {**used, "Unused": NOT_FOUND}
    out = tmp_path / "out"
    run_audit(
        {"trials": [{"nct": "NCT09000001"}]},
        out,
        fetch=lambda n: ([study(n)], "v", "t"),
        classes_for=lambda s: answers,
    )
    kept = json.loads((out / "rxclass.json").read_text())
    assert set(kept["answers"]) == {"Testamab", "XB-1"}
    assert kept["answers"]["Testamab"]["retrieved"] == "2026-10-31T12:00:00+00:00"
    assert kept["answers"]["XB-1"]["retrieved"] is None
    assert kept["endpoint"].startswith("https://rxnav.nlm.nih.gov/")
    assert manifest_drugs(out)["Testamab"]["rxclass"] == "matches_artifact"
    changed = {"Testamab": {"codes": {}, "classes": [["N9", "Kinase Inhibitor", "has_epc", "DAILYMED"]]}}
    assert keep_rxclass(out / "rxclass.json", changed, ["Testamab"])["Testamab"]["classes"] == [PD1]


def test_a_reading_that_differs_from_the_kept_file_is_recorded(tmp_path):
    """Positive: an answer kept by an earlier run is what the check reads, from disk, so a reading built on a
    changed answer is recorded as differing from the artifact, the kept entry unchanged. Negative: it is never
    recorded as matching, and the kept file is not overwritten by the answer the reading used."""
    out = tmp_path / "out"
    out.mkdir()
    earlier = {
        "codes": {"DAILYMED:has_epc": "found"},
        "classes": [["N9", "Kinase Inhibitor", "has_epc", "DAILYMED"]],
    }
    seeded = {"answers": {"Testamab": {**earlier, "retrieved": "2026-01-01T00:00:00+00:00"}}}
    (out / "rxclass.json").write_text(json.dumps(seeded))
    run_audit(
        {"trials": [{"nct": "NCT09000001"}]},
        out,
        fetch=lambda n: ([study(n)], "v", "t"),
        classes_for=lambda s: ANSWERS,
    )
    testamab = manifest_drugs(out)["Testamab"]
    assert testamab["state"] == "classified" and testamab["classes"] == [PD1[1]]
    assert testamab["rxclass"] == "differs_from_artifact" and testamab["artifact"] == [earlier["classes"][0]]
    kept = json.loads((out / "rxclass.json").read_text())["answers"]
    assert kept["Testamab"]["classes"] == earlier["classes"]
    assert kept["Testamab"]["retrieved"] == "2026-01-01T00:00:00+00:00"
