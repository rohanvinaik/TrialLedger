"""The independent preservation check (acceptance/preserve.py): registry value → record value → displayed
cell.

Written from the contract and its hand-checked examples (tests/fixtures/contract/examples), never from the
code that builds the record or the workbook; units A and C are held to it.

Positive: the contract's example record, an excerpt, agrees with the registry bodies it was cut from; the
walker's own record of every saved body agrees with the bodies completely; the Safety example's rows, the
contract's hand-checked cells, agree with the record of their two trials; a Posted results row written by hand
from the example's hand-checked values agrees with the example record.
Negative: each planted defect is caught by name: a measurement moved to another group (its value, or its group
ID), a denominator under the wrong group, an adverse-event total swapped between groups, a dropped nested
comment, a value rounded or retyped, a value invented, a held value written as not stated, an excerpt read as
complete; in the workbook, a wrong row address, a wrong trial, a changed count, a count where the trial has no
such group, a count written as text, a raw code, a rounded denominator, a missing row and a repeated one.
"""

import copy
import json
from pathlib import Path

import pytest

from acceptance import preserve
from acceptance.preserve import cell_findings, project_study, record_findings
from TrialLedger import contract

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"
EXAMPLES = FIXTURES / "examples"
BODIES = preserve.bodies_in([FIXTURES / "studies-ids-3.json", FIXTURES / "studies-osimertinib-subset.json"])
RECORD = json.loads((EXAMPLES / "record.json").read_text(encoding="utf-8"))
SAFETY = json.loads((EXAMPLES / "safety.json").read_text(encoding="utf-8"))
MEASURE = "/studies/1/posted_outcomes/0/classes/0/categories/0/measurements/0"


def codes(findings):
    return sorted({finding.code for finding in findings})


def excerpt():
    return copy.deepcopy(RECORD)


def projected(*ncts):
    return {"studies": [project_study(BODIES[nct]) for nct in ncts]}


def safety_record():
    """The record of the Safety example's two trials, cut to the two serious events each row shows."""
    record = projected(*SAFETY["trials"])
    for study in record["studies"]:
        study["adverse_events"]["events"] = study["adverse_events"]["events"][:2]
    return record


def safety_rows():
    return copy.deepcopy(SAFETY["rows"])


def safety_findings(rows, record=None, complete=True):
    return cell_findings(record or safety_record(), {contract.SAFETY: (SAFETY["columns"], rows)}, complete)


# ── registry → record: the examples and the walker's own record agree ───────────────────────────────────


def test_the_example_record_agrees_with_the_registry_as_an_excerpt():
    assert record_findings(BODIES, RECORD, complete=False) == []


def test_every_saved_body_agrees_with_the_walkers_own_record_completely():
    record = projected(*BODIES)
    assert record_findings(BODIES, record, complete=True) == []
    study = record["studies"][0]
    assert (
        study["baseline"]["measures"][0]["classes"][0]["categories"][0]["measurements"][0]["value"] == "63.4"
    )
    assert study["adverse_events"]["events"][0]["table"] == "serious"
    assert study["adverse_events"]["events"][7]["table"] == "other"


def test_the_example_is_not_a_complete_record():
    found = record_findings(BODIES, RECORD, complete=True)
    assert "dropped" in codes(found) and "study_missing" in codes(found)
    assert set(codes(found)) <= {"dropped", "study_missing"}


# ── registry → record: planted defects ──────────────────────────────────────────────────────────────────


def baseline_measurements(record):
    return record["studies"][1]["baseline"]["measures"][0]["classes"][0]["categories"][0]["measurements"]


def test_a_measurement_value_moved_to_another_group_is_misplaced():
    record = excerpt()
    first, second = baseline_measurements(record)
    first["value"], second["value"] = second["value"], first["value"]
    found = record_findings(BODIES, record, complete=False)
    assert codes(found) == ["misplaced"]
    assert {f.field for f in found} == {
        "studies[].baseline.measures[].classes[].categories[].measurements[].value"
    }


def test_a_measurement_whose_group_id_is_swapped_is_misplaced():
    record = excerpt()
    first, second = baseline_measurements(record)
    first["group"], second["group"] = second["group"], first["group"]
    assert "misplaced" in codes(record_findings(BODIES, record, complete=False))


def test_a_denominator_under_the_wrong_group_is_misplaced():
    record = excerpt()
    counts = record["studies"][1]["posted_outcomes"][0]["denominators"][0]["counts"]
    counts[0]["value"], counts[1]["value"] = counts[1]["value"], counts[0]["value"]
    assert codes(record_findings(BODIES, record, complete=False)) == ["misplaced"]


def test_adverse_event_totals_swapped_between_groups_are_misplaced():
    record = excerpt()
    first, second = record["studies"][1]["adverse_events"]["groups"]
    first["serious_affected"], second["serious_affected"] = (
        second["serious_affected"],
        first["serious_affected"],
    )
    assert codes(record_findings(BODIES, record, complete=False)) == ["misplaced"]


def test_a_dropped_nested_comment_is_caught_in_an_excerpt():
    record = excerpt()
    measurement = record["studies"][1]["posted_outcomes"][0]["classes"][0]["categories"][0]["measurements"][1]
    del measurement["comment"]
    found = record_findings(BODIES, record, complete=False)
    assert codes(found) == ["dropped"]
    assert found[0].expected == "Data was not reported as MTD was not reached in the specified arm group."


def test_a_dropped_nested_field_is_caught_in_a_complete_record():
    record = projected("NCT01030536")
    measures = record["studies"][0]["baseline"]["measures"][0]["classes"][0]["categories"][0]["measurements"]
    del measures[4]["comment"]
    del record["studies"][0]["adverse_events"]["events"][3]
    found = record_findings({"NCT01030536": BODIES["NCT01030536"]}, record, complete=True)
    assert "dropped" in codes(found)
    assert any(f.expected == "Data was not calculated" for f in found)


@pytest.mark.parametrize("rounded", ["63", 63.4, "63.40"])
def test_a_value_rounded_or_retyped_is_a_mismatch(rounded):
    record = excerpt()
    baseline_measurements(record)[0]["value"] = rounded
    assert codes(record_findings(BODIES, record, complete=False)) == ["mismatch"]


def test_a_count_retyped_is_a_mismatch():
    record = excerpt()
    record["studies"][1]["enrollment"]["count"] = "23"
    assert codes(record_findings(BODIES, record, complete=False)) == ["mismatch"]


def test_a_value_the_registry_does_not_hold_is_invented():
    record = excerpt()
    record["studies"][0]["acronym"] = "TBCT"
    assert codes(record_findings(BODIES, record, complete=False)) == ["invented"]


def test_a_held_value_written_as_not_stated_is_a_false_absence():
    record = excerpt()
    record["studies"][0]["why_stopped"] = {"status": "not_stated", "note": "not_reported"}
    assert codes(record_findings(BODIES, record, complete=False)) == ["false_absence"]


def test_a_list_reordered_is_a_mismatch():
    record = excerpt()
    record["studies"][1]["conditions"].reverse()
    assert codes(record_findings(BODIES, record, complete=False)) == ["mismatch"]


def test_a_study_without_its_body_is_named():
    found = record_findings({}, RECORD, complete=False)
    assert codes(found) == ["no_body"]


# ── record → cell: the Safety example ───────────────────────────────────────────────────────────────────


def test_the_safety_example_agrees_with_its_record():
    assert safety_findings(safety_rows()) == []


def test_a_wrong_row_address_is_caught():
    rows = safety_rows()
    rows[0][1] = "/studies/0/adverse_events/events/1"
    found = safety_findings(rows)
    assert {"not_shown", "number_differs", "row_repeated", "row_missing"} <= set(codes(found))


def test_an_address_that_resolves_nowhere_or_is_no_pointer_is_named():
    rows = safety_rows()
    rows[0][1] = "/studies/0/adverse_events/events/9"
    rows[1][1] = "studies/0/adverse_events/events/1"
    assert {"address_unresolved", "address_unreadable"} <= set(codes(safety_findings(rows)))


def test_a_row_at_another_grain_is_named():
    rows = safety_rows()
    rows[0][1] = "/studies/0/adverse_events/groups/0"
    assert "wrong_grain" in codes(safety_findings(rows, complete=False))


def test_a_wrong_trial_is_caught():
    rows = safety_rows()
    rows[2][0] = "NCT01030536"
    assert codes(safety_findings(rows)) == ["trial_differs"]


def test_a_changed_count_is_caught():
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("G3 affected")] = 0
    found = safety_findings(rows)
    assert codes(found) == ["number_differs"] and found[0].field == "Safety: G3 affected"


def test_a_count_where_the_trial_has_no_such_group_is_caught():
    rows = safety_rows()
    rows[2][SAFETY["columns"].index("G3 affected")] = 0
    assert codes(safety_findings(rows)) == ["not_blank"]


def test_a_count_written_as_text_is_retyped():
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("G1 at risk")] = "7"
    assert codes(safety_findings(rows)) == ["retyped"]


def test_a_count_the_registry_does_not_give_reads_not_reported():
    record = safety_record()
    del record["studies"][0]["adverse_events"]["events"][0]["counts"][0]["events"]
    assert codes(safety_findings(safety_rows(), record)) == ["not_shown"]
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("G1 events")] = preserve.NOT_REPORTED
    assert safety_findings(rows, record) == []


def test_a_raw_code_is_not_shown():
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("Assessment")] = "SYSTEMATIC_ASSESSMENT"
    rows[1][SAFETY["columns"].index("Table")] = "serious"
    assert codes(safety_findings(rows)) == ["not_shown"]


def test_an_unworded_absence_and_a_missing_row_are_caught():
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("Notes")] = None
    found = safety_findings(rows[:3])
    assert codes(found) == ["row_missing", "unexplained_blank"]


# ── record → cell: a Posted results row, written by hand from the example's hand-checked values ─────────


POSTED_ROW = {
    "Trial ID": "NCT01030536",
    contract.ADDRESS: MEASURE,
    "Outcome type": "Primary",
    "Measure": "Maximum Tolerated Dose (MTD)",
    "Measure description": "Not stated",
    "Analysis population": RECORD["studies"][1]["posted_outcomes"][0]["population"],
    "Reporting status": "Posted",
    "Time frame": "Day 1 to end of Cycle 1 (approximately 28 days)",
    "Class": "Not stated",
    "Category": "Not stated",
    "Group": "CAT-8015 20 Microgram Per Kilogram (mcg/kg) (OG000)",
    "Denominator": "7 Participants",
    "Parameter": "Number",
    "Value": "NA",
    "Spread or limits": "Not stated",
    "Unit": "mcg/Kg",
    "Comment": "Data was not reported as MTD was not reached in the specified arm group.",
}


def posted_findings(**changed):
    row = POSTED_ROW | changed
    headers = list(row)
    return cell_findings(RECORD, {contract.POSTED: (headers, [list(row.values())])}, complete=False)


def test_a_hand_written_posted_results_row_agrees_with_the_example():
    assert posted_findings() == []


@pytest.mark.parametrize(
    ("column", "cell", "code"),
    [
        ("Denominator", "6 Participants", "not_shown"),
        ("Value", "N/A", "not_shown"),
        ("Group", "CAT-8015 30 Microgram Per Kilogram (mcg/kg) (OG001)", "not_shown"),
        ("Parameter", "NUMBER", "not_shown"),
        ("Comment", None, "blank"),
        ("Measure description", "", "unexplained_blank"),
    ],
)
def test_a_posted_results_cell_off_its_record_is_caught(column, cell, code):
    found = posted_findings(**{column: cell})
    assert codes(found) == [code] and found[0].field == f"{contract.POSTED}: {column}"


def test_a_posted_row_addressing_the_other_group_shows_the_other_denominator():
    found = posted_findings(**{contract.ADDRESS: MEASURE[:-1] + "1"})
    assert {f.field for f in found} == {f"{contract.POSTED}: Group", f"{contract.POSTED}: Denominator"}


# ── the pure decisions, both signs ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ((True, "7", "value", "7", ["6"], True), "match"),
        ((True, "7", "value", "6", ["6"], True), "misplaced"),
        ((True, "7", "value", 7, ["6"], True), "mismatch"),
        ((True, 0, "value", False, [], True), "mismatch"),
        ((True, "7", "value_object", {"status": "not_stated"}, [], True), "false_absence"),
        ((True, "7", "absent", None, [], True), "dropped"),
        ((True, "7", "absent", None, [], False), "not_in_excerpt"),
        ((False, None, "value", "x", [], True), "invented"),
        ((False, None, "value_object", {"status": "not_stated"}, [], True), "silent"),
        ((False, None, "absent", None, [], True), "silent"),
    ],
)
def test_value_verdict(arguments, expected):
    assert preserve.value_verdict(*arguments) == expected


@pytest.mark.parametrize(
    ("pointer", "expected"),
    [
        ("", ("ok", [])),
        ("/studies/0/adverse_events", ("ok", ["studies", "0", "adverse_events"])),
        ("/a~1b/c~0d", ("ok", ["a/b", "c~d"])),
        ("studies/0", ("not_a_pointer", [])),
        ("/a~2", ("bad_escape", [])),
    ],
)
def test_pointer_steps(pointer, expected):
    assert preserve.pointer_steps(pointer) == expected


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        (("7 Participants", ["7", "Participants"], [], False, False), "shown"),
        (("17 Participants", ["7"], [], False, False), "not_shown"),
        (("63.40", ["63.4"], [], False, False), "not_shown"),
        ((None, [], [], False, True), "blank_by_construction"),
        ((0, [], [], False, True), "not_blank"),
        ((None, ["7"], [], False, False), "blank"),
        (("  ", [], [], True, False), "unexplained_blank"),
        ((7, [], [7], False, False), "shown"),
        ((7.0, [], [7], False, False), "number_differs"),
        (("7", [], [7], False, False), "retyped"),
        (("seven", [], [7], False, False), "number_differs"),
        ((63.4, ["63.4"], [], False, False), "retyped"),
        ((True, ["Yes"], [], False, False), "not_shown"),
        (("Not stated", [], [], True, False), "shown"),
    ],
)
def test_cell_verdict(arguments, expected):
    assert preserve.cell_verdict(*arguments) == expected


def test_shows_text_reads_numbers_whole():
    assert preserve.shows_text("63.4 (8.7)", "63.4") and preserve.shows_text("n = 7", "7")
    assert not preserve.shows_text("63.45", "63.4") and not preserve.shows_text("1.7", "7")
    assert preserve.shows_text("7.", "7") and not preserve.shows_text("7.5", "7")


# ── the shells: a workbook read back and a run's files ──────────────────────────────────────────────────


def write_safety_book(path, rows, split):
    from openpyxl import Workbook

    book = Workbook()
    first = book.active
    first.title = contract.SAFETY
    first.append(["Safety: one row per adverse-event term"])
    first.append(SAFETY["columns"])
    for row in rows[:split]:
        first.append(row)
    second = book.create_sheet(f"{contract.SAFETY} (2)")
    second.append(SAFETY["columns"])
    for row in rows[split:]:
        second.append(row)
    book.save(path)


def test_a_listing_continued_on_a_numbered_sheet_is_read_whole(tmp_path):
    book = tmp_path / "landscape.xlsx"
    write_safety_book(book, safety_rows(), 2)
    sheets = preserve.workbook_sheets(book)
    assert list(sheets) == [contract.SAFETY]
    headers, rows = sheets[contract.SAFETY]
    assert headers == SAFETY["columns"] and [list(row) for row in rows] == SAFETY["rows"]
    assert cell_findings(safety_record(), sheets, complete=True) == []


def test_a_run_is_checked_from_its_files(tmp_path):
    (tmp_path / "landscape.json").write_text(json.dumps(safety_record()), encoding="utf-8")
    rows = safety_rows()
    rows[3][SAFETY["columns"].index("G2 at risk")] = 135
    write_safety_book(tmp_path / "landscape.xlsx", rows, 3)
    bodies = {nct: BODIES[nct] for nct in SAFETY["trials"]}
    found = preserve.check_run(
        bodies, tmp_path / "landscape.json", tmp_path / "landscape.xlsx", complete=False
    )
    assert {f.code for f in found} >= {"number_differs", "sheet_missing"}
    assert [f.field for f in found if f.code == "number_differs"] == ["Safety: G2 at risk"]
