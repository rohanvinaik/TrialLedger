"""Known table denominators and collection counts survive adjacent source silence.

All studies below are invented structural fixtures. The risk fallback is the existing registry rule;
it neither creates a missing event observation nor transfers a population across modules.
"""

import copy
import json

import pytest
from openpyxl import load_workbook

from TrialLedger import landscape, readout

ABSENT = object()


def adverse_event_study(
    affected=5, event_at_risk=ABSENT, group_at_risk=10, table="serious", malformed_later_stats=False
):
    """Minimal source fixture with an optional malformed later event for aggregation tests."""
    count = {"groupId": "G1", "numAffected": affected}
    if event_at_risk is not ABSENT:
        count["numAtRisk"] = event_at_risk
    module = {
        "eventGroups": [{"id": "G1", "title": "Group 1", f"{table}NumAtRisk": group_at_risk}],
        "seriousEvents": [],
        "otherEvents": [],
    }
    module[f"{table}Events"] = [{"term": "Invented event", "notes": "Exact source note.", "stats": [count]}]
    if malformed_later_stats:
        module[f"{table}Events"].append({"term": "Malformed unrelated event", "stats": "not an array"})
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "designModule": {"studyType": "INTERVENTIONAL"},
            "statusModule": {"overallStatus": "RECRUITING", "resultsFirstSubmitDate": "2026-01-01"},
        },
        "hasResults": True,
        "resultsSection": {"adverseEventsModule": module},
    }


def report(study, validate=True):
    manifest = landscape.landscape_manifest(
        [study], "fixture", "snapshot", "test", {}, landscape.RULE_VERSIONS
    )
    result = landscape.landscape_record([study], {}, {}, manifest)
    result = json.loads(json.dumps(result))
    if validate:
        assert landscape.schema_problems(result) == ()
    return result


def safety(record):
    return readout.safety_rows(record["studies"][0], 0, 1)


def availability(record):
    return {
        fact: (value, basis)
        for fact, value, basis in readout.availability_rows(record["studies"][0], "Safety")
    }


@pytest.mark.parametrize("table", ["serious", "other"])
def test_missing_event_risk_uses_only_its_unique_table_group_with_visible_rule_and_source(table):
    source = adverse_event_study(table=table)
    original = copy.deepcopy(source)
    record = report(source)
    before = copy.deepcopy(record)
    [row] = safety(record)
    pointer = f"/studies/0/adverse_events/groups/0/{table}_at_risk"
    assert row[6][0] == 10
    assert row[6][3:5] == (pointer, "")
    assert row[6][5] == f"checks.at_risk: /studies/0/adverse_events/events/0/counts/0/at_risk; {pointer}"
    assert row[15][0].startswith("Exact source note.\n")
    assert f"{table} group total" in row[15][0]
    assert pointer in row[15][0] and "checks.at_risk" in row[15][0]
    assert source == original and record == before


@pytest.mark.parametrize("event_risk", [0, 3, 10])
def test_explicit_event_denominator_including_zero_wins_without_fallback_label(event_risk):
    [row] = safety(report(adverse_event_study(event_at_risk=event_risk)))
    assert row[6][0] == event_risk
    assert row[6][4] == ""
    assert row[15][0] == "Exact source note."


def test_explicit_blank_uses_the_existing_blank_denominator_rule():
    [row] = safety(report(adverse_event_study(event_at_risk=None)))
    assert row[6][0] == 10 and row[6][5].startswith("checks.at_risk: ")


@pytest.mark.parametrize("malformed", ["not a count", True, -1, [], {}])
def test_malformed_explicit_event_denominator_is_never_replaced_by_group_total(malformed):
    # Exercise this display boundary directly; typed report admission separately refuses malformed scalars.
    record = report(adverse_event_study())
    record["studies"][0]["adverse_events"]["events"][0]["counts"][0]["at_risk"] = malformed
    [row] = safety(record)
    assert row[6][0] != 10 and row[6][4] == ""
    assert row[15][0] == "Exact source note."


@pytest.mark.parametrize("group_risk", [None, "10", True, -1, [], {}])
def test_unusable_group_total_does_not_supply_a_denominator(group_risk):
    record = report(adverse_event_study())
    record["studies"][0]["adverse_events"]["groups"][0]["serious_at_risk"] = group_risk
    [row] = safety(record)
    assert row[6][0] == "Not reported" and row[6][4] == ""


def test_duplicate_group_identifier_never_selects_one_group_total():
    source = adverse_event_study()
    source["resultsSection"]["adverseEventsModule"]["eventGroups"].append(
        {"id": "G1", "title": "Other local group", "seriousNumAtRisk": 20}
    )
    [row] = safety(report(source))
    assert row[6][0] == "Not reported" and row[6][4] == ""
    assert "no unique" in row[4][0]


@pytest.mark.parametrize("group_id", [None, "", True, 7])
def test_missing_or_malformed_group_identity_cannot_supply_a_fallback_denominator(group_id):
    record = report(adverse_event_study())
    events = record["studies"][0]["adverse_events"]
    events["groups"][0]["id"] = group_id
    events["events"][0]["counts"][0]["group"] = group_id
    [row] = safety(record)
    assert row[6][0] == "Not reported" and row[6][4] == ""


def test_group_total_never_transfers_to_an_unmatched_count_or_an_absent_event_count_row():
    source = adverse_event_study()
    module = source["resultsSection"]["adverseEventsModule"]
    module["seriousEvents"][0]["stats"][0]["groupId"] = "other-module-G1"
    rows = safety(report(source))
    assert all(row[6][0] == "Not reported" and row[6][4] == "" for row in rows)
    module["seriousEvents"][0]["stats"] = []
    [row] = safety(report(source))
    assert row[5][0] == row[6][0] == "Not reported"


def test_unknown_event_table_cannot_choose_a_serious_or_other_denominator():
    record = report(adverse_event_study())
    record["studies"][0]["adverse_events"]["events"][0]["table"] = "unresolved"
    [row] = safety(record)
    assert row[6][0] == "Not reported" and row[6][4] == ""


def test_known_serious_count_survives_an_unreported_other_collection():
    source = adverse_event_study()
    del source["resultsSection"]["adverseEventsModule"]["otherEvents"]
    values = availability(report(source))
    assert values["Serious adverse-event terms"] == ("1 serious terms (Safety)", "Registry")
    assert values["Other adverse-event terms"] == ("Not stated", "Not stated")


def test_known_empty_other_collection_is_zero_listed_terms_beside_unknown_serious_collection():
    source = adverse_event_study()
    del source["resultsSection"]["adverseEventsModule"]["seriousEvents"]
    values = availability(report(source))
    assert values["Serious adverse-event terms"] == ("Not stated", "Not stated")
    assert values["Other adverse-event terms"] == ("0 other terms (Safety)", "Registry")


def test_malformed_other_collection_does_not_erase_known_serious_count_or_become_zero():
    source = adverse_event_study()
    source["resultsSection"]["adverseEventsModule"]["otherEvents"] = "not an array"
    values = availability(report(source))
    assert values["Serious adverse-event terms"] == ("1 serious terms (Safety)", "Registry")
    assert values["Other adverse-event terms"] == (
        "Unresolved — source collection is malformed",
        "Unresolved",
    )


def test_both_known_collections_keep_the_existing_combined_wording():
    values = availability(report(adverse_event_study()))
    assert values["Adverse-event terms"] == ("1 serious and 0 other terms (Safety)", "Registry")
    assert "Serious adverse-event terms" not in values and "Other adverse-event terms" not in values


def test_both_missing_collections_remain_unknown_together():
    source = adverse_event_study()
    module = source["resultsSection"]["adverseEventsModule"]
    del module["seriousEvents"], module["otherEvents"]
    assert availability(report(source))["Adverse events"] == ("Not stated", "Not stated")


def test_actual_workbook_emits_effective_risk_origin_and_separate_partial_collection_counts(tmp_path):
    source = adverse_event_study()
    del source["resultsSection"]["adverseEventsModule"]["otherEvents"]
    record = report(source)
    before = copy.deepcopy(record)
    path = tmp_path / "landscape.xlsx"
    readout.write_book(record, path)
    assert readout.book_problems(record, path) == []
    workbook = load_workbook(path, read_only=True)
    try:
        safety_rows = list(workbook["Safety"].iter_rows(values_only=True))
        headers = safety_rows[0]
        values = dict(zip(headers, safety_rows[1], strict=True))
        assert values["At risk"] == 10
        assert "serious group total" in values["Notes"]
        assert "/studies/0/adverse_events/groups/0/serious_at_risk" in values["Notes"]
        review = list(workbook["Trial review"].iter_rows(values_only=True))
        facts = {row[2]: (row[3], row[4]) for row in review[1:]}
        assert facts["Serious adverse-event terms"] == ("1 serious terms (Safety)", "Registry")
        assert facts["Other adverse-event terms"] == ("Not stated", "Not stated")
    finally:
        workbook.close()
    assert record == before
