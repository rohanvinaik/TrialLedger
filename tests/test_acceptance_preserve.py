"""The independent preservation check (acceptance/preserve.py): registry value → record value → displayed
cell.

Written from the contract and its hand-checked examples (tests/fixtures/contract/examples), never from the
code that builds the record or the workbook; units A and C are held to it.

Positive: the contract's example record, an excerpt, agrees with the registry bodies it was cut from; the
walker's own record of every saved body agrees with the bodies completely; the Safety example's rows, the
contract's hand-checked cells, agree with the record of their two trials; Posted results, Baseline,
Eligibility, Trial index and Trial review rows written by hand from the example's hand-checked values agree
with the example record; a registry decimal as a number cell of the right format agrees; an empty listing may
say so in one line.
Negative: each planted defect is caught by name: a measurement moved to another group (its value, or its group
ID), a denominator under the wrong group, an adverse-event total swapped between groups, a dropped nested
comment, a value rounded or retyped, a value invented, a held value written as not stated, an excerpt read as
complete; in the workbook, a wrong row address, a wrong trial, a changed count, a count where the trial has no
such group, a count written as text, a raw code, a rounded denominator, a missing row and a repeated one; a
wrong absence label (in a listing and in the dossier, value and basis), an omitted "No reading produced", a
wrong index fact, a wrong dossier fact, a dossier fact without its row, the record's JSON in a cell, a
recurring criterion's wordings presented as one representative text, a registry decimal shown with other
decimals, and a value a number cannot hold (1e-400) written as one.
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
    assert codes(safety_findings(safety_rows(), record)) == ["retyped"]
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
        (("7 Participants", ["7", "Participants"], [], [], False), "shown"),
        (("17 Participants", ["7"], [], [], False), "not_shown"),
        (("63.40", ["63.4"], [], [], False), "not_shown"),
        ((None, [], [], [], True), "blank_by_construction"),
        ((0, [], [], [], True), "not_blank"),
        ((None, ["7"], [], [], False), "blank"),
        ((None, [], [], ["Not stated"], False), "blank"),
        (("  ", [], [], [], False), "unexplained_blank"),
        ((7, [], [7], [], False), "shown"),
        ((7.0, [], [7], [], False), "number_differs"),
        (("7", [], [7], [], False), "retyped"),
        (("seven", [], [7], [], False), "number_differs"),
        ((63.4, ["63.4"], [], [], False), "shown"),
        ((63.4, ["63.4"], [], [], False, "0.00"), "decimals_differ"),
        ((66, ["66.0"], [], [], False), "decimals_differ"),
        ((66, ["66.0"], [], [], False, "0.0"), "shown"),
        ((0.0, ["1e-400"], [], [], False), "number_differs"),
        ((7, ["NA"], [], [], False), "retyped"),
        ((7, [], [], ["Not stated"], False), "retyped"),
        ((7, ["7", "Participants"], [], [], False), "not_shown"),
        ((True, ["Yes"], [], [], False), "not_shown"),
        (("Not stated", [], [], ["Not stated"], False), "shown"),
        (("Invented statement", [], [], ["Not stated"], False), "wrong_words"),
        (("Not posted", [], [], ["Not stated"], False), "wrong_words"),
        (("Not stated, probably none", [], [], ["Not stated"], False), "wrong_words"),
        (("Unresolved — the name is not in RxNorm", [], [], ["Unresolved"], False), "shown"),
        (("Completed", ["Completed"], [], ["Not stated"], False), "shown"),
        (("Any words", [], [], [], False), "shown"),
    ],
)
def test_cell_verdict(arguments, expected):
    assert preserve.cell_verdict(*arguments) == expected


def test_shows_text_reads_numbers_whole():
    assert preserve.shows_text("63.4 (8.7)", "63.4") and preserve.shows_text("n = 7", "7")
    assert not preserve.shows_text("63.45", "63.4") and not preserve.shows_text("1.7", "7")
    assert preserve.shows_text("7.", "7") and not preserve.shows_text("7.5", "7")


# ── record → cell: the Groups sheet's G1 ... Gn, from the Safety example's hand-checked names ───────────

GROUP_HEADERS = [
    "Trial ID",
    contract.ADDRESS,
    "Module",
    "Group ID",
    "Column",
    "Title",
    "Description",
    "Totals",
]
TOTALS = ("deaths_affected", "deaths_at_risk", "serious_affected", "serious_at_risk", "other_affected")


def group_rows():
    """One Groups row for each adverse-event group the Safety example names, its description and totals
    written from the record of its two trials."""
    record = safety_record()
    rows = []
    for named in SAFETY["group_columns"]:
        i = SAFETY["trials"].index(named["trial"])
        g = int(named["column"][1:]) - 1
        group = record["studies"][i]["adverse_events"]["groups"][g]
        totals = "; ".join(f"{key}: {group[key]}" for key in (*TOTALS, "other_at_risk") if key in group)
        address = f"/studies/{i}/adverse_events/groups/{g}"
        cells = [named["trial"], address, "Adverse events", named["group"], named["column"], named["title"]]
        rows.append([*cells, group["description"], totals])
    return rows


def groups_findings(rows):
    return cell_findings(safety_record(), {contract.GROUPS: (GROUP_HEADERS, rows)}, complete=False)


def test_the_groups_rows_name_each_adverse_event_groups_safety_columns():
    assert groups_findings(group_rows()) == []


def test_a_groups_row_naming_the_wrong_safety_column_or_no_module_is_caught():
    rows = group_rows()
    rows[0][GROUP_HEADERS.index("Column")] = "G2"
    rows[1][GROUP_HEADERS.index("Module")] = None
    rows[2][GROUP_HEADERS.index("Title")] = SAFETY["group_columns"][3]["title"]
    found = groups_findings(rows)
    assert sorted((f.code, f.field) for f in found) == [
        ("not_shown", "Groups: Column"),
        ("not_shown", "Groups: Title"),
        ("unexplained_blank", "Groups: Module"),
    ]


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
    plain = [[preserve._plain(cell) for cell in row] for row in rows]
    assert headers == SAFETY["columns"] and plain == SAFETY["rows"]
    assert rows[0][SAFETY["columns"].index("G1 at risk")] == preserve.Number(7, "General")
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


# ── numbers: a registry decimal written as a number cell ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "number_format", "expected"),
    [
        (66, "General", "66"),
        (66.0, "General", "66"),
        (63.4, "General", "63.4"),
        (66, "0.0", "66.0"),
        (0.125, "0.00", "0.12"),
        (1234.5, "#,##0.0", "1234.5"),
        (7, "0%", None),
        ("7", "General", None),
        (True, "General", None),
    ],
)
def test_displayed_number(value, number_format, expected):
    assert preserve.displayed_number(value, number_format) == expected


@pytest.mark.parametrize(
    ("text", "value", "number_format", "expected"),
    [
        ("63.4", 63.4, "General", "same"),
        ("66.0", 66, "0.0", "same"),
        ("66.0", 66, "General", "decimals_differ"),
        ("63.4", 63.39999, "0.0", "value_differs"),
        ("1e-400", 0.0, "General", "value_differs"),
        ("3.14159265358979323846", 3.141592653589793, "General", "value_differs"),
        ("NA", 7, "General", "not_a_number"),
        ("Infinity", float("inf"), "General", "not_a_number"),
        ("7", "7", "General", "not_a_number"),
    ],
)
def test_number_agrees(text, value, number_format, expected):
    assert preserve.number_agrees(text, value, number_format) == expected


def baseline_row(value_cell):
    """The Baseline row of NCT01030536's first group's age, from the example's hand-checked values."""
    return {
        "Trial ID": "NCT01030536",
        contract.ADDRESS: "/studies/1/baseline/measures/0/classes/0/categories/0/measurements/0",
        "Characteristic": "Age, Continuous",
        "Population": "Not stated",
        "Class": "Age",
        "Category": "Not stated",
        "Group": "CAT-8015 20 Microgram Per Kilogram (mcg/kg) (BG000)",
        "Denominator": "7 Participants",
        "Parameter": "Mean",
        "Value": value_cell,
        "Spread or limits": "Standard deviation 8.7",
        "Unit": "years",
        "Comment": "Not stated",
    }


def baseline_findings(value_cell, record=None):
    row = baseline_row(value_cell)
    sheets = {contract.BASELINE: (list(row), [list(row.values())])}
    return cell_findings(record or RECORD, sheets, complete=False)


def test_a_registry_decimal_as_a_number_cell_must_keep_its_value_and_decimals():
    assert baseline_findings(preserve.Number(63.4, "General")) == []
    assert baseline_findings("63.4") == []
    found = baseline_findings(preserve.Number(63.4, "0"))
    assert [(f.code, f.field) for f in found] == [("decimals_differ", "Baseline: Value")]
    assert codes(baseline_findings(preserve.Number(63.0, "0.0"))) == ["number_differs"]


def test_a_value_a_cell_cannot_hold_exactly_must_be_text():
    record = excerpt()
    baseline_measurements(record)[0]["value"] = "1e-400"
    assert codes(baseline_findings(preserve.Number(0.0, "General"), record)) == ["number_differs"]
    assert baseline_findings("1e-400", record) == []


# ── a status's words: an absence, an unresolved value, a criterion with no reading ──────────────────────


def test_a_wrong_absence_label_is_caught():
    found = posted_findings(Class="Not posted")
    assert [(f.code, f.field) for f in found] == [("wrong_words", f"{contract.POSTED}: Class")]
    assert codes(posted_findings(Category="Invented statement")) == ["wrong_words"]


ELIGIBILITY_HEADERS = [
    "Trial ID",
    contract.ADDRESS,
    "Heading",
    "Criterion number",
    "Role",
    "Criterion as written",
    "Readings",
]
CRITERION = (
    "* Written informed consent and Health Insurance Portability and Accountability Act (HIPAA) authorization"
)


def eligibility_record():
    record = excerpt()
    role = {
        "status": "known",
        "rule": "criteria.criterion_role",
        "words": [],
        "result": "inclusion",
        "note": "",
    }
    record["studies"][1]["criteria"] = [
        {"heading": "inclusion", "number": 1, "text": CRITERION, "role": role, "readings": []}
    ]
    return record


def eligibility_findings(readings_cell):
    row = ["NCT01030536", "/studies/1/criteria/0", "Inclusion", 1, "Inclusion", CRITERION, readings_cell]
    return cell_findings(eligibility_record(), {contract.ELIGIBILITY: (ELIGIBILITY_HEADERS, [row])})


def test_a_criterion_with_no_reading_reads_no_reading_produced():
    assert eligibility_findings("No reading produced") == []


@pytest.mark.parametrize(("cell", "code"), [(None, "blank"), ("None", "wrong_words"), ("", "blank")])
def test_an_omitted_no_reading_produced_is_caught(cell, code):
    found = eligibility_findings(cell)
    assert [(f.code, f.field) for f in found] == [(code, f"{contract.ELIGIBILITY}: Readings")]


# ── the Trial index and the Trial review ────────────────────────────────────────────────────────────────

# NCT04852770's index row, from the example's hand-checked values.
INDEX_ROW = {
    "Trial ID": "NCT04852770",
    "Acronym or short title": "Efficacy of TBCT, MBHP and PPT for PTSD During the Covid-19 Pandemics",
    "Sponsor": "Fundação Bahiana de Infectologia (Other)",
    "Phase": "Not applicable",
    "Status": "Terminated",
    "Conditions": "Posttraumatic Stress Disorder; Covid19",
    "Universe": "Outside oncology (condition MeSH terms)",
    "Design": "Treatment; Randomized; masking Double",
    "Enrollment": "135 (Actual)",
    "Start": "06-Apr-2020 (Actual)",
    "Primary endpoint": "Not stated",
    "Results posted": "Not posted",
    "Publications": "Not stated",
    "Countries": "Not stated",
    "Last update posted": "04-Apr-2025",
    "Treatment setting": "Not applicable",
    "Prior lines for advanced disease": "Not applicable",
    "Gene selection": "Not applicable",
    "Dossier": "Dossier",
}
REVIEW_ROWS = [
    ("Brief title", "Efficacy of TBCT, MBHP and PPT for PTSD During the Covid-19 Pandemics", "Registry"),
    ("Acronym", "Not stated", "Not stated"),
    ("Official title", RECORD["studies"][0]["official_title"], "Registry"),
    ("Overall status", "Terminated", "Registry"),
    ("Why stopped", "The study was interrupted due to the end of the pandemic.", "Registry"),
    ("Start date", "06-Apr-2020 (Actual)", "Registry"),
    ("Last update posted", "04-Apr-2025", "Registry"),
    ("Lead sponsor", "Fundação Bahiana de Infectologia (Other)", "Registry"),
    ("Data monitoring committee", "No", "Registry"),
    ("Phase", "Not applicable", "Registry"),
    ("Primary purpose", "Treatment", "Registry"),
    ("Allocation", "Randomized", "Registry"),
    ("Masking", "Double", "Registry"),
    ("Study type", "Interventional", "Registry"),
    ("Enrollment", "135 (Actual)", "Registry"),
    ("Conditions", "Posttraumatic Stress Disorder; Covid19", "Registry"),
    ("Condition MeSH terms", "Stress Disorders, Post-Traumatic; COVID-19", "Registry"),
    ("Universe", "General: no domain readings apply", "Reading"),
]
REVIEW_HEADERS = ["Trial ID", "Section", "Fact", "Value", "Basis"]


def one_study():
    return {"studies": [copy.deepcopy(RECORD["studies"][0])]}


def index_findings(**changed):
    row = INDEX_ROW | changed
    return cell_findings(one_study(), {contract.INDEX: (list(row), [list(row.values())])})


def review_findings(rows):
    cells = [["NCT04852770", "Section", fact, value, basis] for fact, value, basis in rows]
    return cell_findings(one_study(), {contract.REVIEW: (REVIEW_HEADERS, cells)})


def test_the_index_row_agrees_with_its_record():
    assert index_findings() == []


@pytest.mark.parametrize(
    ("column", "cell", "code"),
    [
        ("Enrollment", "153 (Actual)", "not_shown"),
        ("Enrollment", "135 (Anticipated)", "not_shown"),
        ("Start", "06-May-2020 (Actual)", "not_shown"),
        ("Status", "TERMINATED", "not_shown"),
        ("Publications", "None", "wrong_words"),
        ("Publications", "0", "wrong_words"),
        ("Sponsor", None, "blank"),
        ("Dossier", None, "unexplained_blank"),
    ],
)
def test_a_wrong_index_fact_is_caught(column, cell, code):
    found = index_findings(**{column: cell})
    assert [(f.code, f.field) for f in found] == [(code, f"{contract.INDEX}: {column}")]


def test_an_index_row_for_no_trial_and_a_trial_with_no_row_are_caught():
    found = index_findings(**{"Trial ID": "NCT00000000"})
    assert sorted(codes(found)) == ["row_missing", "trial_differs"]


def test_the_dossier_rows_agree_with_their_record():
    assert review_findings(REVIEW_ROWS) == []


def test_a_wrong_dossier_fact_is_caught():
    rows = list(REVIEW_ROWS)
    rows[0] = ("Brief title", "Efficacy of TBCT for PTSD", "Registry")
    rows[5] = ("Start date", "2020-04-16 (Actual)", "Registry")
    found = review_findings(rows)
    assert [(f.code, f.field) for f in found] == [
        ("not_shown", f"{contract.REVIEW}: Brief title"),
        ("not_shown", f"{contract.REVIEW}: Start date"),
    ]


def test_a_wrong_absence_label_in_the_dossier_is_caught():
    rows = list(REVIEW_ROWS)
    rows[1] = ("Acronym", "Not posted", "Not posted")
    found = review_findings(rows)
    assert [(f.code, f.field) for f in found] == [
        ("wrong_words", f"{contract.REVIEW}: Acronym"),
        ("wrong_words", f"{contract.REVIEW}: Acronym (basis)"),
    ]


def test_a_dossier_fact_the_registry_holds_without_its_row_is_caught():
    found = review_findings([row for row in REVIEW_ROWS if row[0] != "Why stopped"])
    assert [(f.code, f.field) for f in found] == [("fact_missing", f"{contract.REVIEW}: Why stopped")]


def test_a_raw_record_in_a_cell_is_caught():
    rows = [*REVIEW_ROWS, ("Universe", str(RECORD["studies"][0]["universe"]), "Reading")]
    assert codes(review_findings(rows)) == ["raw_record"]


def test_a_numbered_dossier_fact_is_read_line_by_line():
    record = {"studies": [project_study(BODIES["NCT01030536"])]}
    arm = record["studies"][0]["arms"][1]
    value = f"Arm: {arm['label']}\nArm type: Experimental\nArm description: {arm['description']}"
    rows = [["NCT01030536", "Arms and interventions", "Arm 2", value, "Registry"]]

    def found():
        every = cell_findings(record, {contract.REVIEW: (REVIEW_HEADERS, rows)})
        return [f for f in every if f.code != "fact_missing"]

    assert found() == []
    rows[0][2] = "Arm 3"
    assert {f.field for f in found()} == {
        f"{contract.REVIEW}: Arm 3: Arm",
        f"{contract.REVIEW}: Arm 3: Arm description",
    }


# ── the across-trial criteria listing (its grain read from the contract, whatever its name) ─────────────

CRITERIA_SHEET = next(
    sheet
    for sheet in contract.SHEETS
    if preserve.sheet_grains(sheet) and not preserve.sheet_grains(sheet)[0].startswith("studies")
)
CRITERIA_LIST = preserve.sheet_grains(CRITERIA_SHEET)[0].removesuffix("[]")
SHORT = "ECOG performance status 0-1"
LONG = "Eastern Cooperative Oncology Group (ECOG) performance status of 0 or 1 at screening"


def criteria_findings(wording_cell):
    entry = {
        "criterion": {"universe": "oncology.solid", "element": "inclusion:ecog_ps=0-1"},
        "role": "inclusion",
        "trials": 3,
        "of_trials": 4,
        "wording": [SHORT, LONG],
        "wording_from": ["NCT02151981 criterion 4", "NCT02296125 criterion 6"],
        "other_trials": ["NCT04487080"],
    }
    cells = {
        contract.ADDRESS: f"/{CRITERIA_LIST}/0",
        "Criterion": "Performance status (ECOG 0-1), solid tumour trials",
        "Role": "Inclusion",
        "Trials stating it": preserve.Number(3, "General"),
        "Of comparable trials": preserve.Number(4, "General"),
        "Representative wording": wording_cell,
        "Wording from": "NCT02151981 criterion 4; NCT02296125 criterion 6",
        "Other trials": "NCT04487080",
    }
    headers = [column.header for column in CRITERIA_SHEET.columns]
    sheets = {CRITERIA_SHEET.name: (headers, [[cells[h] for h in headers]])}
    return cell_findings({CRITERIA_LIST: [entry]}, sheets)


def test_the_recurring_criteria_row_shows_each_representative_wording():
    assert criteria_findings(f"{SHORT}\n{LONG}") == []


def test_wording_presented_as_one_representative_text_is_caught():
    found = criteria_findings(SHORT)
    assert [(f.code, f.field) for f in found] == [
        ("not_shown", f"{CRITERIA_SHEET.name}: Representative wording")
    ]


# ── an empty listing's one line ─────────────────────────────────────────────────────────────────────────


def test_an_empty_listing_may_say_so_in_one_line():
    sheet = next(sheet for sheet in contract.SHEETS if sheet.name == contract.ANALYSES)
    headers = [column.header for column in sheet.columns]
    line = ["None of these trials posted a statistical analysis"] + [None] * (len(headers) - 1)
    assert cell_findings(RECORD, {contract.ANALYSES: (headers, [line])}) == []
    record = excerpt()
    record["studies"][1]["posted_outcomes"][0]["analyses"] = [{"method": "Log Rank"}]
    found = cell_findings(record, {contract.ANALYSES: (headers, [line])})
    assert sorted(codes(found)) == ["address_unreadable", "row_missing"]
