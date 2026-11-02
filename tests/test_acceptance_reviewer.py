"""The reviewer's tasks (acceptance/reviewer.py), exercised on the contract's examples.

Until the record (unit A), the workbook (unit C) and the record tool's address part (unit F) land, the tasks
run on tests/fixtures/contract/examples/record.json as a run folder's landscape.json, with no workbook, beside
the registry bodies it was cut from; the address task asks a stand-in record tool, and the real one is held to
the target as an expected failure until unit F 6.2.

Positive: each task names its destination, finds its evidence at the record's addresses (the eligibility
criteria and their roles, the enrolled and analysed populations, a result's population and denominator per
group, the adverse-event period, threshold and counts, each reading's words in the registry text), and names
what stays unresolved (no criteria itemized, no baseline posted, the baseline analysing fewer than enrolled,
no workbook to check the destination, no biomarker mention). A record tool that answers each address with the
record's value passes.
Negative: a reading whose words the registry does not hold, more affected than at risk, a criterion with no
reading, a group without a denominator, an "NA" without its reason, an answer that differs from the record's
value, a refused address, and a workbook missing the destination's rows, are each named.
"""

import copy
import json
import shutil
from pathlib import Path

import pytest

from acceptance import preserve, reviewer
from acceptance.reviewer import Run
from TrialLedger import contract

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"
EXAMPLES = FIXTURES / "examples"
BODIES = preserve.bodies_in([FIXTURES / "studies-ids-3.json", FIXTURES / "studies-osimertinib-subset.json"])
RECORD = json.loads((EXAMPLES / "record.json").read_text(encoding="utf-8"))
NO_WORKBOOK = "no workbook in the run folder"


def run(record=None, sheets=None, bodies=BODIES):
    return Run(copy.deepcopy(record or RECORD), sheets, bodies)


def whats(items):
    return [item.what for item in items]


def resolved_value(record, address):
    _code, tokens = preserve.pointer_steps(address)
    return preserve.resolve_pointer(record, tokens)[1]


def test_a_run_folder_is_read_as_its_record_and_workbook(tmp_path):
    shutil.copy(EXAMPLES / "record.json", tmp_path / reviewer.RECORD_NAME)
    loaded = reviewer.load_run(tmp_path, BODIES)
    assert loaded.record == RECORD and loaded.sheets is None and loaded.bodies is BODIES


def test_every_task_names_its_destination_and_says_no_workbook_was_checked():
    results = reviewer.review(run())
    assert [r.destination for r in results] == [
        (contract.ELIGIBILITY,),
        (contract.REVIEW, contract.BASELINE),
        (contract.POSTED,),
        (contract.SAFETY, contract.GROUPS),
        (contract.BIOMARKERS, contract.READINGS),
    ]
    for result in results:
        assert result.task and any(w.startswith(NO_WORKBOOK) for w in whats(result.unresolved))
        assert result.findings == []


# ── eligibility ─────────────────────────────────────────────────────────────────────────────────────────


CRITERION_TEXT = (
    "Written informed consent and Health Insurance Portability and Accountability Act (HIPAA) authorization"
)


def with_criteria(readings):
    record = copy.deepcopy(RECORD)
    role = {"status": "known", "rule": "criteria.criterion_role", "words": ["Inclusion Criteria:"]}
    role |= {"result": "inclusion", "note": ""}
    record["studies"][1]["criteria"] = [
        {
            "heading": "Inclusion Criteria",
            "number": "1",
            "text": CRITERION_TEXT,
            "role": role,
            "readings": readings,
        }
    ]
    return record


def test_the_example_has_no_itemized_criteria_and_says_so():
    result = reviewer.eligibility_across(run())
    assert result.evidence == []
    assert [(u.nct, u.address) for u in result.unresolved[1:]] == [
        ("NCT04852770", "/studies/0/criteria"),
        ("NCT01030536", "/studies/1/criteria"),
    ]


def test_a_criterion_is_compared_with_its_role_and_a_criterion_unread_is_named():
    result = reviewer.eligibility_across(run(with_criteria(None)), ["NCT01030536"])
    assert [(e.address, e.value[2]) for e in result.evidence] == [("/studies/1/criteria/0", CRITERION_TEXT)]
    assert "No reading produced" in whats(result.unresolved)


def test_a_criterion_missing_from_the_eligibility_sheet_is_found():
    sheets = {contract.ELIGIBILITY: ([contract.ADDRESS], [])}
    result = reviewer.eligibility_across(run(with_criteria(None), sheets), ["NCT01030536"])
    assert [(f.address, f.value) for f in result.findings] == [
        ("/studies/1/criteria/0", contract.ELIGIBILITY)
    ]


# ── eligible and enrolled ───────────────────────────────────────────────────────────────────────────────


def test_the_enrolled_and_analysed_populations_are_told_apart():
    result = reviewer.eligible_vs_enrolled(run())
    evidence = {(e.nct, e.what): e.value for e in result.evidence}
    assert evidence[("NCT01030536", "enrolled")] == [23, "ACTUAL"]
    assert evidence[("NCT01030536", "analysed, BG000")] == "7"
    assert ("NCT04852770", "no baseline characteristics posted") in {
        (u.nct, u.what) for u in result.unresolved
    }
    assert "the baseline analysed 13 of 23 enrolled" in whats(result.unresolved)


def test_a_complete_baseline_analysing_every_enrolled_participant_is_not_unresolved():
    record = {"studies": [preserve.project_study(BODIES["NCT01030536"])]}
    result = reviewer.eligible_vs_enrolled(run(record))
    assert not [u for u in result.unresolved if u.what.startswith("the baseline analysed")]


def test_an_enrollment_no_trial_review_row_shows_is_found():
    sheets = {contract.REVIEW: (["Trial ID", "Value"], [["NCT01030536", "123"]])}
    result = reviewer.eligible_vs_enrolled(run(sheets=sheets), ["NCT01030536"])
    assert "no Trial review row shows the enrollment" in whats(result.findings)
    sheets = {contract.REVIEW: (["Trial ID", "Value"], [["NCT01030536", "23 (actual)"]])}
    result = reviewer.eligible_vs_enrolled(run(sheets=sheets), ["NCT01030536"])
    assert "no Trial review row shows the enrollment" not in whats(result.findings)


# ── a result's population and denominator ───────────────────────────────────────────────────────────────


def test_a_results_population_and_each_groups_denominator_are_found():
    result = reviewer.result_population(run())
    assert ("NCT04852770", "no results posted") in {(u.nct, u.what) for u in result.unresolved}
    values = {e.address: e.value for e in result.evidence}
    measurement = "/studies/1/posted_outcomes/0/classes/0/categories/0/measurements/"
    assert values[measurement + "0"] == ["NA", ["7", "Participants"]]
    assert values[measurement + "1"] == ["NA", ["6", "Participants"]]
    assert values["/studies/1/posted_outcomes/0/population"].startswith("Evaluable Population for DLT")


def test_a_group_without_a_denominator_and_an_na_without_its_reason_are_unresolved():
    record = copy.deepcopy(RECORD)
    measure = record["studies"][1]["posted_outcomes"][0]
    measure["denominators"][0]["counts"].pop()
    del measure["classes"][0]["categories"][0]["measurements"][0]["comment"]
    result = reviewer.result_population(run(record))
    assert {"no denominator for group OG001", "NA without the registry's reason"} <= set(
        whats(result.unresolved)
    )


# ── safety within its period ────────────────────────────────────────────────────────────────────────────


def test_safety_is_read_within_its_period():
    result = reviewer.safety_in_period(run())
    values = {e.what: e.value for e in result.evidence}
    assert values["reporting period"] == "From Screening (Day -28) to Post Therapy Day 30"
    assert values["threshold for other events (%)"] == "5"
    assert values["G2: CAT-8015 30 Microgram Per Kilogram (mcg/kg)"][:2] == [3, 6]
    assert result.findings == []


def test_more_affected_than_at_risk_and_a_count_not_reported_are_named():
    record = copy.deepcopy(RECORD)
    events = record["studies"][1]["adverse_events"]
    events["groups"][0]["serious_affected"] = 9
    del events["events"][0]["counts"][1]["events"]
    del events["time_frame"]
    result = reviewer.safety_in_period(run(record))
    assert whats(result.findings) == [reviewer.FINDING_WORDS["affected_exceeds_at_risk"]]
    assert "G2 events: Not reported" in whats(result.unresolved)
    assert any(w.startswith("reporting period not stated") for w in whats(result.unresolved))


def test_a_safety_row_and_a_group_row_missing_from_the_workbook_are_found():
    sheets = {contract.SAFETY: ([contract.ADDRESS], [["/studies/1/adverse_events/events/0"]])}
    sheets[contract.GROUPS] = ([contract.ADDRESS], [["/studies/1/adverse_events/groups/0"]])
    result = reviewer.safety_in_period(run(sheets=sheets), ["NCT01030536"])
    assert [(f.address, f.value) for f in result.findings] == [
        ("/studies/1/adverse_events/groups/1", contract.GROUPS)
    ]


# ── readings traced to their words ──────────────────────────────────────────────────────────────────────


def test_every_reading_of_the_examples_is_traced_to_the_registrys_words():
    result = reviewer.biomarker_trace(run())
    traced = {(e.nct, e.address) for e in result.evidence}
    assert traced == {
        ("NCT04852770", "/studies/0/universe"),
        ("NCT01030536", "/studies/1/universe"),
        ("NCT01030536", "/studies/1/interventions/0/drug_class"),
    }
    assert ("NCT01030536", "/studies/1/coordinates/prior_advanced_lines") in {
        (u.nct, u.address) for u in result.unresolved
    }
    assert "no biomarker mention in the record" in whats(result.unresolved)
    assert result.findings == []


def test_a_biomarker_mention_is_traced_and_one_the_registry_does_not_hold_is_found():
    record = copy.deepcopy(RECORD)
    mention = {"status": "known", "rule": "banks.biomarker_status", "words": ["B-cell CLL"]}
    record["studies"][1]["biomarker_mentions"] = [mention | {"result": {}, "note": ""}]
    result = reviewer.biomarker_trace(run(record), ["NCT01030536"])
    assert "/studies/1/biomarker_mentions/0" in {e.address for e in result.evidence}
    record["studies"][1]["biomarker_mentions"][0]["words"] = ["EGFR exon 19 deletion"]
    result = reviewer.biomarker_trace(run(record), ["NCT01030536"])
    assert [(f.address, f.value) for f in result.findings] == [
        ("/studies/1/biomarker_mentions/0", ["EGFR exon 19 deletion"])
    ]


def test_a_reading_with_altered_words_is_found_and_one_without_a_body_is_unresolved():
    record = copy.deepcopy(RECORD)
    record["studies"][0]["universe"]["words"][0] = "Stress Disorder"
    result = reviewer.biomarker_trace(run(record))
    assert result.findings == []  # a word within a registry term is traced
    record["studies"][0]["universe"]["words"][0] = "Depressive Disorder"
    result = reviewer.biomarker_trace(run(record))
    assert [(f.nct, f.value) for f in result.findings] == [("NCT04852770", ["Depressive Disorder"])]
    result = reviewer.biomarker_trace(run(bodies={}))
    assert "registry body not given: readings not traced" in whats(result.unresolved)


def test_a_reading_with_no_readings_row_is_found():
    sheets = {
        contract.READINGS: ([contract.ADDRESS], [["/studies/0/universe"]]),
        contract.BIOMARKERS: ([], []),
    }
    result = reviewer.biomarker_trace(run(sheets=sheets), ["NCT04852770"])
    assert result.findings == []
    result = reviewer.biomarker_trace(run(sheets=sheets), ["NCT01030536"])
    assert {f.address for f in result.findings} == {
        "/studies/1/universe",
        "/studies/1/interventions/0/drug_class",
        "/studies/1/coordinates/prior_advanced_lines",
    }


@pytest.mark.parametrize(
    ("words", "texts", "expected"),
    [
        (["EGFR"], ["EGFR mutation"], ("traced", [])),
        ([], ["EGFR"], ("no_words", [])),
        (["EGFR", "ALK"], ["EGFR mutation"], ("untraced", ["ALK"])),
        (["egfr"], ["EGFR"], ("untraced", ["egfr"])),
        (["EGFR"], [], ("untraced", ["EGFR"])),
    ],
)
def test_words_traced(words, texts, expected):
    assert reviewer.words_traced(words, texts) == expected


# ── a row's address asked of the record tool ────────────────────────────────────────────────────────────


def faithful(record):
    return lambda address: ("ok", copy.deepcopy(resolved_value(record, address)))


def test_a_record_tool_answering_each_address_with_the_records_value_passes():
    result = reviewer.address_answered(run(), faithful(RECORD))
    assert result.findings == [] and len(result.evidence) == 17
    assert "/studies/1/adverse_events/events/0" in {e.address for e in result.evidence}


def test_an_answer_off_the_record_or_refused_is_found():
    def off(address):
        value = copy.deepcopy(resolved_value(RECORD, address))
        if address.endswith("measurements/0"):
            value["value"] = "7"
        if address.endswith("events/0"):
            return "refused", {"error": "outside_record"}
        return "ok", value

    result = reviewer.address_answered(run(), off)
    assert sorted(whats(result.findings)) == [
        reviewer.FINDING_WORDS["not_answered"],
        reviewer.FINDING_WORDS["answered_differently"],
        reviewer.FINDING_WORDS["answered_differently"],
    ]


def test_the_rows_asked_are_the_workbooks_when_there_is_one():
    sheets = {contract.SAFETY: ([contract.ADDRESS], [["/studies/1/adverse_events/events/0"]])}
    result = reviewer.address_answered(run(sheets=sheets), faithful(RECORD))
    assert [e.address for e in result.evidence] == ["/studies/1/adverse_events/events/0"]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="until unit F 6.2: the record tool's address part on a schema-3 record",
)
def test_the_real_record_tool_answers_each_address(tmp_path):
    folder = tmp_path / "example"
    folder.mkdir()
    shutil.copy(EXAMPLES / "record.json", folder / reviewer.RECORD_NAME)
    result = reviewer.address_answered(run(), reviewer.mcp_ask(tmp_path, "example"))
    assert result.findings == [] and result.evidence


def test_a_criterion_whose_readings_are_empty_is_named_with_its_text():
    result = reviewer.eligibility_across(run(with_criteria([])), ["NCT01030536"])
    unread = [u for u in result.unresolved if u.what == reviewer.NO_READING]
    assert [(u.address, u.value) for u in unread] == [("/studies/1/criteria/0", CRITERION_TEXT)]
    typed = [{"status": "known", "rule": "banks.type_criterion", "words": ["informed consent"], "result": {}}]
    result = reviewer.eligibility_across(run(with_criteria(typed)), ["NCT01030536"])
    assert reviewer.NO_READING not in whats(result.unresolved)


def with_key_criterion(text, role):
    record = with_criteria([])
    reading = {"categories": ["Prior therapy and line"], "at": "criteria/0", "readings": []}
    key = {"text": text, "role": role, "reading": reading, "rule": "landscape.key_criteria"}
    record["studies"][1]["key_criteria"] = [key]
    return record


def test_a_key_criterion_is_its_criterions_text_and_role():
    result = reviewer.eligibility_across(
        run(with_key_criterion(CRITERION_TEXT, "inclusion")), ["NCT01030536"]
    )
    assert result.findings == []
    for text, role in ((CRITERION_TEXT, "exclusion"), ("Written informed consent", "inclusion")):
        result = reviewer.eligibility_across(run(with_key_criterion(text, role)), ["NCT01030536"])
        assert [(f.address, f.what) for f in result.findings] == [
            ("/studies/1/key_criteria/0", reviewer.FINDING_WORDS["key_criterion_differs"])
        ]


def test_a_module_the_record_says_is_not_posted_is_unresolved_not_read():
    record = copy.deepcopy(RECORD)
    not_posted = {"status": "not_posted", "note": "no results posted"}
    record["studies"][1]["baseline"] = not_posted
    record["studies"][1]["adverse_events"] = not_posted
    enrolled = reviewer.eligible_vs_enrolled(run(record), ["NCT01030536"])
    safety = reviewer.safety_in_period(run(record), ["NCT01030536"])
    assert any(
        u.what.startswith("no baseline characteristics posted (not_posted") for u in enrolled.unresolved
    )
    assert any(u.what.startswith("no adverse events posted (not_posted") for u in safety.unresolved)
    assert not any(e.address.endswith("time_frame") for e in safety.evidence)
