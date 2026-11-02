"""Reporting review tasks checked against saved registry evidence and actual MCP responses.

Positive cases retain exact source spans, group-specific populations/denominators, reporting periods and
record addresses. Negative cases plant altered source words/offsets, missing denominator or workbook rows,
count inconsistencies and changed/refused MCP answers. No clinical-role or biomarker reading is expected.
"""

import copy
import json
import shutil
from pathlib import Path

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
    ]
    for result in results:
        assert result.task and any(w.startswith(NO_WORKBOOK) for w in whats(result.unresolved))
        assert result.findings == []


CRITERION_TEXT = BODIES["NCT01030536"]["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]


def with_criteria():
    record = copy.deepcopy(RECORD)
    original = BODIES["NCT01030536"]["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    start = original.index(CRITERION_TEXT)
    record["studies"][1]["criteria"] = [
        {
            "heading": "unsectioned",
            "number": 1,
            "text": CRITERION_TEXT,
            "source_start": start,
            "source_end": start + len(CRITERION_TEXT),
        }
    ]
    return record


def test_the_source_example_sections_are_exact_and_visible():
    result = reviewer.eligibility_across(run())
    assert result.evidence and result.findings == []
    for item in result.evidence:
        heading, text, start, end = item.value
        original = BODIES[item.nct]["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
        assert text == original[start:end]
        assert heading in {"unsectioned", "inclusion", "exclusion"}


def test_an_eligibility_section_is_compared_as_exact_source_text():
    result = reviewer.eligibility_across(run(with_criteria()), ["NCT01030536"])
    assert [(e.address, e.value[1]) for e in result.evidence] == [("/studies/1/criteria/0", CRITERION_TEXT)]
    assert result.findings == []


def test_a_criterion_missing_from_the_eligibility_sheet_is_found():
    sheets = {contract.ELIGIBILITY: ([contract.ADDRESS], [])}
    result = reviewer.eligibility_across(run(with_criteria(), sheets), ["NCT01030536"])
    assert [(f.address, f.value) for f in result.findings] == [
        ("/studies/1/criteria/0", contract.ELIGIBILITY)
    ]


def test_the_enrolled_and_analysed_populations_are_told_apart():
    result = reviewer.eligible_vs_enrolled(run())
    evidence = {(e.nct, e.what): e.value for e in result.evidence}
    assert evidence[("NCT01030536", "enrolled")] == [23, "ACTUAL"]
    assert evidence[("NCT01030536", "baseline denominator, BG000")] == ["7", "Participants"]
    assert any(
        u.nct == "NCT04852770" and u.what.startswith("no baseline characteristics posted")
        for u in result.unresolved
    )
    assert not any("the baseline analysed" in u.what for u in result.unresolved)


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
    missing_group = measure["denominators"][0]["counts"].pop()["group"]
    del measure["classes"][0]["categories"][0]["measurements"][0]["comment"]
    result = reviewer.result_population(run(record))
    assert {f"no denominator for group {missing_group}", "NA without the registry's reason"} <= set(
        whats(result.unresolved)
    )


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
    events = RECORD["studies"][1]["adverse_events"]
    event_addresses = [f"/studies/1/adverse_events/events/{i}" for i in range(len(events["events"]))]
    group_addresses = [f"/studies/1/adverse_events/groups/{i}" for i in range(len(events["groups"]))]
    sheets = {
        contract.SAFETY: ([contract.ADDRESS], [[a] for a in event_addresses[:-1]]),
        contract.GROUPS: ([contract.ADDRESS], [[a] for a in group_addresses[:-1]]),
    }
    result = reviewer.safety_in_period(run(sheets=sheets), ["NCT01030536"])
    assert {(f.address, f.value) for f in result.findings} == {
        (event_addresses[-1], contract.SAFETY),
        (group_addresses[-1], contract.GROUPS),
    }


def faithful(record):
    return lambda address: ("ok", copy.deepcopy(resolved_value(record, address)))


def test_a_record_tool_answering_each_address_with_the_records_value_passes():
    result = reviewer.address_answered(run(), faithful(RECORD), bound=1000)
    assert result.findings == [] and result.evidence
    assert "/studies/1/adverse_events/events/0" in {e.address for e in result.evidence}


def test_an_answer_off_the_record_or_refused_is_found():
    addresses = [
        "/studies/1/posted_outcomes/0/classes/0/categories/0/measurements/0",
        "/studies/1/adverse_events/events/0",
    ]
    sheets = {
        contract.POSTED: ([contract.ADDRESS], [[addresses[0]]]),
        contract.SAFETY: ([contract.ADDRESS], [[addresses[1]]]),
    }

    def off(address):
        if address == addresses[1]:
            return "refused", {"error": "outside_record"}
        value = copy.deepcopy(resolved_value(RECORD, address))
        value["value"] = "7"
        return "ok", value

    result = reviewer.address_answered(run(sheets=sheets), off)
    assert {f.what for f in result.findings} == {
        reviewer.FINDING_WORDS["not_answered"],
        reviewer.FINDING_WORDS["answered_differently"],
    }


def test_the_rows_asked_are_the_workbooks_when_there_is_one():
    sheets = {contract.SAFETY: ([contract.ADDRESS], [["/studies/1/adverse_events/events/0"]])}
    result = reviewer.address_answered(run(sheets=sheets), faithful(RECORD))
    assert [e.address for e in result.evidence] == ["/studies/1/adverse_events/events/0"]


def test_the_real_record_tool_answers_each_address(tmp_path):
    folder = tmp_path / "example"
    folder.mkdir()
    shutil.copy(EXAMPLES / "record.json", folder / reviewer.RECORD_NAME)
    result = reviewer.address_answered(run(), reviewer.mcp_ask(tmp_path, "example"))
    assert result.findings == [] and result.evidence


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


def test_altered_section_words_or_offsets_are_source_disagreements():
    record = with_criteria()
    record["studies"][1]["criteria"][0]["text"] = "A substituted clinical interpretation"
    assert reviewer.eligibility_across(run(record), ["NCT01030536"]).findings
    record = with_criteria()
    record["studies"][1]["criteria"][0]["source_start"] += 1
    assert reviewer.eligibility_across(run(record), ["NCT01030536"]).findings


def test_result_evidence_keeps_measure_and_class_denominators_separately():
    record = copy.deepcopy(RECORD)
    measure = record["studies"][1]["posted_outcomes"][0]
    measure["classes"][0]["denominators"] = [
        {"units": "Participants", "counts": [{"group": "OG000", "value": "5"}]}
    ]
    evidence = {item.address: item.value for item in reviewer.result_population(run(record)).evidence}
    base = "/studies/1/posted_outcomes/0"
    assert evidence[base + "/denominators/0/counts/0"] == ["7", "Participants"]
    assert evidence[base + "/classes/0/denominators/0/counts/0"] == ["5", "Participants"]


def test_baseline_measure_population_and_lower_denominators_remain_distinct():
    record = copy.deepcopy(RECORD)
    measure = record["studies"][1]["baseline"]["measures"][0]
    measure["population"] = "Participants with an age measurement"
    measure["denominators"] = [{"units": "Participants", "counts": [{"group": "BG000", "value": "5"}]}]
    measure["classes"][0]["denominators"] = [
        {"units": "Participants", "counts": [{"group": "BG000", "value": "3"}]}
    ]
    result = reviewer.eligible_vs_enrolled(run(record))
    evidence = {item.address: item.value for item in result.evidence}
    base = "/studies/1/baseline/measures/0"
    assert evidence[base + "/population"] == "Participants with an age measurement"
    assert evidence[base + "/denominators/0/counts/0"] == ["5", "Participants"]
    assert evidence[base + "/classes/0/denominators/0/counts/0"] == ["3", "Participants"]
    assert evidence["/studies/1/baseline/denominators/0/counts/0"] == ["7", "Participants"]
    assert not any("the baseline analysed" in item.what for item in result.unresolved)


def test_a_dropped_source_passage_cannot_hide_behind_the_full_eligibility_field():
    record = with_criteria()
    text = CRITERION_TEXT
    record["studies"][1]["criteria"] = [
        {"heading": "unsectioned", "number": 1, "text": text[:10], "source_start": 0, "source_end": 10},
        {
            "heading": "unsectioned",
            "number": 2,
            "text": text[20:],
            "source_start": 20,
            "source_end": len(text),
        },
    ]
    result = reviewer.eligibility_across(run(record), ["NCT01030536"])
    assert any(item.what == "source eligibility passages are not contiguous" for item in result.findings)
    record["studies"][1]["criteria"].pop()
    result = reviewer.eligibility_across(run(record), ["NCT01030536"])
    assert any(
        item.what == "source eligibility passages do not cover the original text" for item in result.findings
    )
