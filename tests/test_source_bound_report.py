"""The ordinary report preserves source context and exposes approved checks without clinical inference."""

import copy

import pytest
from openpyxl import load_workbook
from records import ongoing_study, results_study
from rxnav_fake import FakeRxNav

from TrialLedger import checks, contract, landscape, readout
from TrialLedger.classes import _ask_rxnav


def report(studies, answers=None):
    manifest = landscape.landscape_manifest(studies, "v", "snapshot", "commit", {}, landscape.RULE_VERSIONS)
    return landscape.landscape_record(studies, {}, {}, manifest, answers)


def test_approved_checks_preserve_exact_inputs_and_never_rewrite_source():
    study = results_study()
    study["resultsSection"]["adverseEventsModule"]["seriousEvents"][0]["stats"][0]["numAffected"] = 100
    original = copy.deepcopy(study)
    reading = landscape.registry_check_reading(study)
    result = reading["result"]
    assert study == original
    assert reading["rule"] == "checks.run_checks" and reading["status"] == "known"
    assert [row["id"] for row in result["checks"]] == [c.id for c in checks.CHECKS if c.id in checks.APPROVED]
    rows = {row["id"]: row for row in result["checks"]}
    assert rows["ae_affected_within_at_risk"]["outcome"] == "conflict"
    assert result["inputs"]["resultsSection.adverseEventsModule"] == {
        "state": "stated",
        "value": original["resultsSection"]["adverseEventsModule"],
    }
    assert all(path in result["inputs"] for row in result["checks"] for path in row["source"])
    assert all(row["rule"] and row["basis"] for row in result["checks"])
    assert len(result["inputs"]) < sum(len(row["source"]) for row in result["checks"])


def test_check_inputs_keep_absent_null_false_and_malformed_parent_distinct():
    inputs = landscape.registry_check_inputs(
        {"hasResults": False, "a": None, "b": "malformed"},
        ["hasResults", "a", "missing", "b.child", "hasResults"],
    )
    assert inputs == {
        "hasResults": {"state": "stated", "value": False},
        "a": {"state": "stated", "value": None},
        "missing": {"state": "not_stated"},
        "b.child": {"state": "malformed_parent", "at": "b", "value": "malformed"},
    }


def test_an_uncheckable_record_never_reads_as_consistent():
    reading = landscape.registry_check_reading({})
    rows = {row["id"]: row for row in reading["result"]["checks"]}
    assert rows["age_limits_ordered"]["outcome"] == "not_checkable"
    words, _basis = readout.registry_check_summary(reading)
    assert "not checkable" in words


def test_results_submission_context_is_source_bound_and_visible_in_the_dossier():
    study = ongoing_study()
    status = study["protocolSection"]["statusModule"]
    status.update(resultsWaived=False, resultsFirstSubmitDate="2026-08-01", dispFirstSubmitDate="2026-07-01")
    record = report([study])
    held = record["studies"][0]
    assert held["results_waived"] is False
    assert held["results_first_submitted"] == "2026-08-01"
    assert held["disposition_first_submitted"] == "2026-07-01"
    assert held["estimated_results_first_submitted"] == "2026-09-01"
    assert landscape.schema_problems(record) == ()
    facts = {fact: value for _band, _listing, fact, value, _basis in readout.dossier_facts(held)}
    assert facts["Results submission waived"] == "No"
    assert "2026" in facts["Results submitted, not yet posted"]
    assert "Results delay disposition first submitted" in facts


@pytest.mark.parametrize("value", [True, "120", 120.0, None])
def test_the_record_validator_does_not_accept_a_noninteger_enrollment(value):
    record = report([results_study()])
    record["studies"][0]["enrollment"]["count"] = value
    assert ("wrong_type", "studies[0].enrollment.count") in landscape.schema_problems(record)


def test_valid_zero_false_and_numeric_result_strings_keep_their_source_types():
    study = results_study()
    study["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = 0
    record = report([study])
    assert landscape.schema_problems(record) == ()
    held = record["studies"][0]
    assert type(held["enrollment"]["count"]) is int and held["enrollment"]["count"] == 0
    assert held["population"]["healthy_volunteers"] is False
    assert held["posted_outcomes"][0]["classes"][0]["categories"][0]["measurements"][0]["value"] == "21"


def test_condition_mesh_identifiers_are_retained_without_indication_inference():
    record = report([results_study()])
    held = record["studies"][0]
    assert held["condition_mesh_ids"] == ["D000001"]
    assert held["condition_mesh_ancestor_ids"] == ["D000002"]
    assert not any("universe" in key or "setting" in key for key in held)
    assert not hasattr(contract, "NON_ONCOLOGY_TERMS") and not hasattr(contract, "PLACEBO_FORMS")


def test_drug_evidence_shows_canonical_names_and_conflicts_without_raw_json():
    fake = FakeRxNav(
        names={"Testamab": ["100"], "TM-1": ["200"]},
        concepts={"100": ("canonical A", "IN"), "200": ("canonical B", "IN")},
        classes={
            "100": [("E", "Class E", "EPC", "has_epc", "DAILYMED", "100")],
            "200": [("B", "Class B", "EPC", "has_epc", "DAILYMED", "200")],
        },
    )
    answers = _ask_rxnav(
        ["Testamab", "TM-1"],
        {"Testamab", "TM-1"},
        get=fake,
        sleep=lambda _: None,
        monotonic=lambda: 0.0,
        progress=lambda _: None,
    )
    record = report([results_study()], answers)
    reading = record["studies"][0]["interventions"][0]["drug_class"]
    assert reading["rule"] == contract.FIELD_NAMES["studies[].interventions[].drug_class"].source[0]
    assert reading["status"] == "unresolved" and reading["result"]["classes"] == []
    words, basis = readout.drug_class_words(reading)
    assert "canonical A" in words and "canonical B" in words and "conflicting concepts" in words
    assert "Source assertion" in words and "Class E" in words and "Class B" in words
    assert "'identities':" not in words and "{'" not in words
    assert basis == contract.STATUS_WORDS["unresolved"]


@pytest.mark.parametrize(
    "status, note, words, basis",
    (
        ("unresolved", "lookup unavailable", "Unresolved — lookup unavailable", "Unresolved"),
        ("not_stated", "not_reported", "Not stated", "Not stated"),
        ("not_posted", "not_posted", "Not posted", "Not posted"),
    ),
)
def test_outer_source_status_cannot_be_overruled_by_a_classified_payload(status, note, words, basis):
    value = {
        "status": status,
        "note": note,
        "rule": "classes.class_evidence",
        "words": ["Source name"],
        "result": {"state": "classified", "classes": [["C", "Source class", "has_epc", "DAILYMED"]]},
    }
    assert readout.drug_class_words(value) == (words, basis)


def test_an_unresolved_class_payload_names_its_classes_as_candidates():
    value = {
        "status": "unresolved",
        "note": "identity unresolved",
        "rule": "classes.class_evidence",
        "words": ["Source name"],
        "result": {"state": "unresolved", "classes": [["C", "Source class", "has_epc", "DAILYMED"]]},
    }
    words, basis = readout.drug_class_words(value)
    assert "Source class candidate: Source class" in words
    assert "attribution unresolved" in words
    assert "Classes attributed to the exact RxNorm concept" not in words
    assert basis == "Unresolved"


def test_registry_check_rows_have_exact_addresses_and_workbook_changes_are_detected(tmp_path):
    record = report([results_study(), ongoing_study()])
    plan = {name: (headers, rows) for name, headers, rows, _starts in readout.book_plan(record)}
    headers, rows = plan["Registry checks"]
    assert len(rows) == 2 * len(checks.APPROVED)
    assert rows[0][1][0] == "/studies/0/registry_checks/result/checks/0"
    assert rows[len(checks.APPROVED)][1][0] == "/studies/1/registry_checks/result/checks/0"
    assert "Outcome" in headers and "Rule basis" in headers
    path = tmp_path / "landscape.xlsx"
    readout.write_book(record, path)
    assert readout.book_problems(record, path) == []
    workbook = load_workbook(path)
    workbook["Registry checks"]["D2"] = "Changed outcome"
    workbook.save(path)
    workbook.close()
    assert readout.book_problems(record, path)


def test_check_diagnostics_render_literal_syntax_without_changing_scalar_information():
    assert readout.check_detail_words("phases=['PHASE1', 'PHASE2']") == "phases=PHASE1; PHASE2"
    assert (
        readout.check_detail_words("input={'minimum': 3, 'maximum': None}")
        == "input=minimum: 3; maximum: null"
    )
    assert readout.check_detail_words("counts=[0, False, 2]") == "counts=0; False; 2"
    assert readout.check_detail_words("group=G0; affected=8; atRisk=4") == "group=G0; affected=8; atRisk=4"
