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
recurring criterion's examples presented as one text, a registry decimal shown with other decimals or in
another format, a value a number cannot hold (1e-400) written as one, a participant denominator changed to
eyes without its shown unit changing, a posted-outcome group's row with another description, a Group link
to the wrong group, an empty listing in other words, and a value in a cell the contract declares blank.
The words, forms and blanks are the contract's declared display policy; the comparisons are the checker's.
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


def safety_rows(record=None):
    record = record or safety_record()
    headers = SAFETY["columns"]
    rows = []

    def shown(name, value):
        want = preserve.expected(contract.FIELD_NAMES[name], value)
        return next(iter(want.texts or want.counts or want.words), preserve.NOT_REPORTED)

    count_field = "studies[].adverse_events.events[].counts[].group"

    def add(study_index, study, event_index, event, group_id, count, address):
        module = study["adverse_events"]
        matches = [group for group in module.get("groups", []) if group.get("id") == group_id]
        group = matches[0] if len(matches) == 1 else None
        row = {
            "Trial ID": study["nct"],
            contract.ADDRESS: address,
            "Table": shown("studies[].adverse_events.events[].table", event.get("table")),
            "Term": shown("studies[].adverse_events.events[].term", event.get("term")),
            "Group": (
                shown("studies[].adverse_events.groups[].title", group.get("title"))
                if group is not None
                else preserve.SAFETY_GROUP_TITLE_UNRESOLVED
            ),
            "Affected": (
                count.get("affected", preserve.NOT_REPORTED)
                if isinstance(count, dict)
                else preserve.NOT_REPORTED
            ),
            "At risk": (
                count.get("at_risk", preserve.NOT_REPORTED)
                if isinstance(count, dict)
                else preserve.NOT_REPORTED
            ),
            "Events": (
                count.get("events", preserve.NOT_REPORTED)
                if isinstance(count, dict)
                else preserve.NOT_REPORTED
            ),
            "Reporting period": shown("studies[].adverse_events.time_frame", module.get("time_frame")),
            "Organ system": shown(
                "studies[].adverse_events.events[].organ_system", event.get("organ_system")
            ),
            "Group description": (
                shown("studies[].adverse_events.groups[].description", group.get("description"))
                if group is not None
                else preserve.SAFETY_GROUP_DESCRIPTION_UNRESOLVED
            ),
            "Group ID": (
                "Not stated"
                if group_id is None and "/counts/" not in address
                else shown(
                    count_field if "/counts/" in address else "studies[].adverse_events.groups[].id",
                    group_id,
                )
            ),
            "Frequency threshold": shown(
                "studies[].adverse_events.frequency_threshold", module.get("frequency_threshold")
            ),
            "Vocabulary": shown("studies[].adverse_events.events[].vocabulary", event.get("vocabulary")),
            "Assessment": shown("studies[].adverse_events.events[].assessment", event.get("assessment")),
            "Notes": shown("studies[].adverse_events.events[].notes", event.get("notes")),
        }
        rows.append([row[header] for header in headers])

    for study_index, study in enumerate(record["studies"]):
        module = study["adverse_events"]
        for event_index, event in enumerate(module.get("events", [])):
            event_address = f"/studies/{study_index}/adverse_events/events/{event_index}"
            counts = event.get("counts", [])
            for count_index, count in enumerate(counts):
                group_id = count.get("group") if isinstance(count, dict) else None
                add(
                    study_index,
                    study,
                    event_index,
                    event,
                    group_id,
                    count,
                    f"{event_address}/counts/{count_index}",
                )
            seen = []
            for group in module.get("groups", []):
                group_id = group.get("id")
                if group_id in seen:
                    continue
                seen.append(group_id)
                if any(
                    (count.get("group") if isinstance(count, dict) else None) == group_id for count in counts
                ):
                    continue
                add(study_index, study, event_index, event, group_id, None, event_address)
            if not seen and not counts:
                add(study_index, study, event_index, event, None, None, event_address)
    return rows


def safety_findings(rows, record=None, complete=False):
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
    partial = excerpt()
    partial["studies"][0].pop("brief_title")
    found = record_findings(BODIES, partial, complete=True)
    assert "dropped" in codes(found) and "study_missing" in codes(found)
    assert set(codes(found)) <= {"dropped", "study_missing"}


# ── registry → record: planted defects ──────────────────────────────────────────────────────────────────


def baseline_measurements(record):
    return record["studies"][1]["baseline"]["measures"][0]["classes"][0]["categories"][0]["measurements"]


def test_a_measurement_value_moved_to_another_group_is_misplaced():
    record = excerpt()
    first, second = baseline_measurements(record)[:2]
    first["value"], second["value"] = second["value"], first["value"]
    found = record_findings(BODIES, record, complete=False)
    assert codes(found) == ["misplaced"]
    assert {f.field for f in found} == {
        "studies[].baseline.measures[].classes[].categories[].measurements[].value"
    }


def test_a_measurement_whose_group_id_is_swapped_is_misplaced():
    record = excerpt()
    first, second = baseline_measurements(record)[:2]
    first["group"], second["group"] = second["group"], first["group"]
    assert "misplaced" in codes(record_findings(BODIES, record, complete=False))


def test_a_denominator_under_the_wrong_group_is_misplaced():
    record = excerpt()
    counts = record["studies"][1]["posted_outcomes"][0]["denominators"][0]["counts"]
    counts[0]["value"], counts[1]["value"] = counts[1]["value"], counts[0]["value"]
    assert codes(record_findings(BODIES, record, complete=False)) == ["misplaced"]


def test_adverse_event_totals_swapped_between_groups_are_misplaced():
    record = excerpt()
    first, second = record["studies"][1]["adverse_events"]["groups"][:2]
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
    rows[0][1] = rows[0][1].rsplit("/", 1)[0] + "/1"
    found = safety_findings(rows)
    assert "not_shown" in codes(found)


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
    rows[10][0] = "NCT01030536"
    assert codes(safety_findings(rows)) == ["trial_differs"]


def test_a_changed_count_is_caught():
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("Affected")] = 99
    found = safety_findings(rows)
    assert codes(found) == ["number_differs"] and found[0].field == "Safety: Affected"


def test_an_orphan_count_id_is_retained_with_unresolved_group_context():
    rows = safety_rows()
    record = safety_record()
    selected = rows[2]
    count = preserve.resolve_pointer(record, selected[1].strip("/").split("/"))[1]
    count["group"] = "EG999"
    selected[SAFETY["columns"].index("Group ID")] = "EG999"
    selected[SAFETY["columns"].index("Group")] = preserve.SAFETY_GROUP_TITLE_UNRESOLVED
    selected[SAFETY["columns"].index("Group description")] = preserve.SAFETY_GROUP_DESCRIPTION_UNRESOLVED
    assert safety_findings(rows, record) == []


def test_safety_group_titles_are_checked_by_local_id_not_position_or_trial():
    record = safety_record()
    record["studies"][0]["adverse_events"]["groups"].reverse()
    rows = safety_rows(record)
    group_column = SAFETY["columns"].index("Group")
    rows[0][group_column], rows[10][group_column] = rows[10][group_column], rows[0][group_column]
    found = safety_findings(rows, record)
    assert any(f.field == "Safety: Group" and f.code == "not_shown" for f in found)


def test_a_declared_safety_group_without_a_count_stays_not_reported():
    record = safety_record()
    study = record["studies"][0]
    event = study["adverse_events"]["events"][0]
    omitted = event["counts"].pop(1)
    rows = safety_rows(record)
    pointer = "/studies/0/adverse_events/events/0"
    row = next(
        row
        for row in rows
        if row[SAFETY["columns"].index(contract.ADDRESS)] == pointer
        and row[SAFETY["columns"].index("Group ID")] == omitted["group"]
    )
    assert [row[SAFETY["columns"].index(name)] for name in ("Affected", "At risk", "Events")] == [
        preserve.NOT_REPORTED
    ] * 3
    assert safety_findings(rows, record, complete=True) == []


def test_safety_rejects_event_rows_for_fabricated_or_already_counted_groups():
    rows = safety_rows()
    base = rows[0].copy()
    pointer_column = SAFETY["columns"].index(contract.ADDRESS)
    group_column = SAFETY["columns"].index("Group ID")
    title_column = SAFETY["columns"].index("Group")
    description_column = SAFETY["columns"].index("Group description")
    count_columns = [SAFETY["columns"].index(name) for name in ("Affected", "At risk", "Events")]
    for group_id in ("EG999", "EG000"):
        row = base.copy()
        row[pointer_column] = row[pointer_column].rsplit("/counts/", 1)[0]
        row[group_column] = group_id
        row[title_column] = preserve.SAFETY_GROUP_TITLE_UNRESOLVED
        row[description_column] = preserve.SAFETY_GROUP_DESCRIPTION_UNRESOLVED
        for index in count_columns:
            row[index] = preserve.NOT_REPORTED
        rows.append(row)
    found = safety_findings(rows)
    assert [finding.code for finding in found] == ["wrong_grain", "wrong_grain"]


def test_duplicate_count_rows_and_an_event_without_groups_or_counts_are_preserved():
    record = safety_record()
    module = record["studies"][0]["adverse_events"]
    event = module["events"][0]
    event["counts"].append(copy.deepcopy(event["counts"][0]))
    module["groups"] = []
    module["events"].append({"table": "other", "term": "Term without group or count"})
    rows = safety_rows(record)
    duplicate_pointers = [
        row[SAFETY["columns"].index(contract.ADDRESS)]
        for row in rows
        if row[SAFETY["columns"].index(contract.ADDRESS)].startswith(
            "/studies/0/adverse_events/events/0/counts/"
        )
    ]
    assert duplicate_pointers[-1].endswith("/counts/5")
    event_only = next(
        row for row in rows if row[SAFETY["columns"].index("Term")] == "Term without group or count"
    )
    assert event_only[SAFETY["columns"].index(contract.ADDRESS)] == "/studies/0/adverse_events/events/2"
    assert event_only[SAFETY["columns"].index("Group ID")] == "Not stated"
    assert safety_findings(rows, record, complete=True) == []


def test_a_count_written_as_text_is_retyped():
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("At risk")] = str(rows[0][SAFETY["columns"].index("At risk")])
    assert codes(safety_findings(rows)) == ["retyped"]


def test_a_count_the_registry_does_not_give_reads_not_reported():
    record = safety_record()
    selected = safety_rows()[0]
    count = preserve.resolve_pointer(record, selected[1].strip("/").split("/"))[1]
    del count["events"]
    assert codes(safety_findings(safety_rows(), record)) == ["retyped"]
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("Events")] = preserve.NOT_REPORTED
    assert safety_findings(rows, record) == []


def test_a_raw_code_is_not_shown():
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("Assessment")] = "SYSTEMATIC_ASSESSMENT"
    rows[1][SAFETY["columns"].index("Table")] = "serious"
    assert codes(safety_findings(rows)) == ["not_shown"]


def test_an_unworded_absence_and_a_missing_row_are_caught():
    rows = safety_rows()
    rows[0][SAFETY["columns"].index("Notes")] = None
    found = safety_findings(rows[:3], complete=True)
    assert codes(found) == ["row_missing", "unexplained_blank"]


# ── record → cell: a Posted results row, written by hand from the example's hand-checked values ─────────


POSTED_ROW = {
    "Trial ID": "NCT01030536",
    contract.ADDRESS: MEASURE,
    "Outcome type": "Primary",
    "Measure": "Maximum Tolerated Dose (MTD)",
    "Measure description": BODIES["NCT01030536"]["resultsSection"]["outcomeMeasuresModule"][
        "outcomeMeasures"
    ][0]["description"],
    "Analysis population": RECORD["studies"][1]["posted_outcomes"][0]["population"],
    "Reporting status": "Posted",
    "Time frame": "Day 1 to end of Cycle 1 (approximately 28 days)",
    "Class": None,
    "Category": None,
    "Group": "CAT-8015 20 Microgram Per Kilogram (mcg/kg) (OG000)",
    contract.DENOMINATOR: preserve.Number(7, "0"),
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
        (contract.DENOMINATOR, preserve.Number(6, "0"), "number_differs"),
        (contract.DENOMINATOR, preserve.Number(7, "General"), "format_differs"),
        ("Class", "Not stated", "not_blank"),
        ("Value", "N/A", "not_shown"),
        ("Group", "CAT-8015 30 Microgram Per Kilogram (mcg/kg) (OG001)", "not_shown"),
        ("Parameter", "NUMBER", "not_shown"),
        ("Comment", None, "blank"),
        ("Measure description", "", "blank"),
    ],
)
def test_a_posted_results_cell_off_its_record_is_caught(column, cell, code):
    found = posted_findings(**{column: cell})
    assert codes(found) == [code] and found[0].field == f"{contract.POSTED}: {column}"


def test_a_posted_row_addressing_the_other_group_shows_the_other_denominator():
    found = posted_findings(**{contract.ADDRESS: MEASURE[:-1] + "1"})
    assert {f.field for f in found} == {
        f"{contract.POSTED}: Group",
        f"{contract.POSTED}: {contract.DENOMINATOR}",
    }


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
    "Outcome measures",
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
        rows.append([*cells, group["description"], None, totals])
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
    assert headers == SAFETY["columns"] and plain == safety_rows()
    assert rows[0][SAFETY["columns"].index("At risk")] == preserve.Number(7, "General")
    assert cell_findings(safety_record(), sheets, complete=True) == []


def test_a_run_is_checked_from_its_files(tmp_path):
    (tmp_path / "landscape.json").write_text(json.dumps(safety_record()), encoding="utf-8")
    rows = safety_rows()
    rows[3][SAFETY["columns"].index("At risk")] = 135
    write_safety_book(tmp_path / "landscape.xlsx", rows, 3)
    bodies = {nct: BODIES[nct] for nct in SAFETY["trials"]}
    found = preserve.check_run(
        bodies, tmp_path / "landscape.json", tmp_path / "landscape.xlsx", complete=False
    )
    assert {f.code for f in found} >= {"number_differs", "sheet_missing"}
    assert [f.field for f in found if f.code == "number_differs"] == ["Safety: At risk"]


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
        "Population": "Measure population: Not stated",
        "Class": "Age",
        "Category": None,
        "Group": "CAT-8015 20 Microgram Per Kilogram (mcg/kg) (BG000)",
        contract.DENOMINATOR: preserve.Number(7, "0"),
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
    assert baseline_findings(preserve.Number(63.4, "0.0")) == []
    assert baseline_findings("63.4") == []
    found = baseline_findings(preserve.Number(63.4, "0"))
    assert [(f.code, f.field) for f in found] == [("decimals_differ", "Baseline: Value")]
    assert codes(baseline_findings(preserve.Number(63.4, "General"))) == ["format_differs"]
    assert codes(baseline_findings(preserve.Number(63.0, "0.0"))) == ["number_differs"]


def test_a_value_a_cell_cannot_hold_exactly_must_be_text():
    record = excerpt()
    baseline_measurements(record)[0]["value"] = "1e-400"
    assert codes(baseline_findings(preserve.Number(0.0, "General"), record)) == ["number_differs"]
    assert baseline_findings("1e-400", record) == []


# ── a status's words: an absence, an unresolved value, a criterion with no reading ──────────────────────


def test_a_wrong_absence_label_is_caught():
    row = baseline_row(preserve.Number(63.4, "0.0")) | {"Population": "Not posted"}
    found = cell_findings(RECORD, {contract.BASELINE: (list(row), [list(row.values())])}, complete=False)
    assert [(f.code, f.field) for f in found] == [("wrong_words", f"{contract.BASELINE}: Population")]
    row["Population"] = "Invented statement"
    found = cell_findings(RECORD, {contract.BASELINE: (list(row), [list(row.values())])}, complete=False)
    assert codes(found) == ["wrong_words"]


# ── the Trial index and the Trial review ────────────────────────────────────────────────────────────────

# NCT04852770's index row, from the example's hand-checked values.
INDEX_ROW = {
    "Trial ID": "NCT04852770",
    "Acronym or short title": "Efficacy of TBCT, MBHP and PPT for PTSD During the Covid-19 Pandemics",
    "Sponsor": "Fundação Bahiana de Infectologia (Other)",
    "Phase": "Not applicable",
    "Status": "Terminated",
    "Conditions": "Posttraumatic Stress Disorder; Covid19",
    "Design": "Treatment; Randomized; masking Double",
    "Enrollment": preserve.Number(135, "General"),
    "Enrollment type": "Actual",
    "Start": "06-Apr-2020 (Actual)",
    "Primary endpoint": "Not stated",
    "Results posted": "Not stated",
    "Publications": "Not stated",
    "Countries": "Not stated",
    "Last update posted": "04-Apr-2025",
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
]
REVIEW_HEADERS = ["Trial ID", "Section", "Fact", "Value", "Basis"]


def one_study():
    # Deliberate excerpt for these hand-authored index/dossier rows; complete-record tests are separate.
    fields = {
        "nct",
        "brief_title",
        "acronym",
        "official_title",
        "overall_status",
        "why_stopped",
        "start_date",
        "last_update_posted",
        "lead_sponsor",
        "dmc",
        "phases",
        "primary_purpose",
        "allocation",
        "masking",
        "study_type",
        "enrollment",
        "conditions",
        "condition_mesh",
    }
    return {
        "studies": [
            {key: copy.deepcopy(value) for key, value in RECORD["studies"][0].items() if key in fields}
        ]
    }


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
        ("Enrollment", preserve.Number(153, "General"), "number_differs"),
        ("Enrollment type", "Anticipated", "not_shown"),
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
    rows = [*REVIEW_ROWS, ("Raw results state", str(RECORD["studies"][0]["results_posted"]), "Reading")]
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


# ── an empty listing's one line ─────────────────────────────────────────────────────────────────────────


def test_an_empty_listing_says_so_in_the_contracts_words():
    sheet = next(sheet for sheet in contract.SHEETS if sheet.name == contract.ANALYSES)
    headers = [column.header for column in sheet.columns]
    line = [contract.EMPTY_LISTING_WORDS[contract.ANALYSES]] + [None] * (len(headers) - 1)
    assert cell_findings(RECORD, {contract.ANALYSES: (headers, [line])}) == []
    other = ["No analyses here"] + [None] * (len(headers) - 1)
    assert codes(cell_findings(RECORD, {contract.ANALYSES: (headers, [other])})) == ["wrong_words"]
    record = excerpt()
    record["studies"][1]["posted_outcomes"][0]["analyses"] = [{"method": "Log Rank"}]
    found = cell_findings(record, {contract.ANALYSES: (headers, [line])})
    assert sorted(codes(found)) == ["address_unreadable", "row_missing"]


# ── posted-outcome groups: one Groups row per group, and the Posted results Group cell's link ───────────


def posted_groups_record():
    return {"studies": [project_study(BODIES["NCT01030536"])]}


def posted_group_row(record, g):
    group = record["studies"][0]["posted_outcomes"][0]["groups"][g]
    measures = [
        m["title"]
        for m in record["studies"][0]["posted_outcomes"]
        if any(
            other.get("title") == group["title"] and other.get("description") == group.get("description")
            for other in m.get("groups") or []
        )
    ]
    address = f"/studies/0/posted_outcomes/0/groups/{g}"
    return [
        "NCT01030536",
        address,
        "Posted results",
        group["id"],
        None,
        group["title"],
        group["description"],
        "\n".join(measures),
        None,
    ]


def posted_group_findings(rows, record=None):
    record = record or posted_groups_record()
    found = cell_findings(record, {contract.GROUPS: (GROUP_HEADERS, rows)}, complete=False)
    return [f for f in found if f.field.startswith(contract.GROUPS)]


def test_a_posted_outcome_group_row_shows_its_description_and_measures():
    record = posted_groups_record()
    assert posted_group_findings([posted_group_row(record, 0), posted_group_row(record, 1)], record) == []


def test_a_posted_outcome_group_row_whose_description_differs_is_caught():
    record = posted_groups_record()
    row = posted_group_row(record, 0)
    row[GROUP_HEADERS.index("Description")] = posted_group_row(record, 1)[GROUP_HEADERS.index("Description")]
    found = posted_group_findings([row], record)
    assert [(f.code, f.field) for f in found] == [("not_shown", f"{contract.GROUPS}: Description")]


def linked_posted_row(record, target_row):
    title = record["studies"][0]["posted_outcomes"][0]["groups"][0]["title"]
    cells = {
        "Trial ID": "NCT01030536",
        contract.ADDRESS: "/studies/0/posted_outcomes/0/classes/0/categories/0/measurements/0",
        "Group": preserve.Linked(title, contract.GROUPS, target_row),
    }
    return cells


def link_findings(target_row):
    record = posted_groups_record()
    groups = [posted_group_row(record, 0), posted_group_row(record, 1)]
    cells = linked_posted_row(record, target_row)
    sheets = {
        contract.GROUPS: (GROUP_HEADERS, groups),
        contract.POSTED: (list(cells), [list(cells.values())]),
    }
    found = cell_findings(record, sheets, complete=False)
    return [f for f in found if f.field == f"{contract.POSTED}: Group"]


def test_a_group_link_to_its_own_group_carries_its_id():
    assert link_findings(1) == []


def test_a_group_link_pointing_at_the_wrong_group_is_caught():
    assert codes(link_findings(2)) == ["wrong_link"]
    assert codes(link_findings(9)) == ["wrong_link"]


# ── a denominator in other units than participants ──────────────────────────────────────────────────────


def test_a_participant_denominator_changed_to_eyes_without_its_unit_shown_is_caught():
    record = excerpt()
    record["studies"][1]["posted_outcomes"][0]["denominators"][0]["units"] = "Eyes"
    cells = POSTED_ROW
    found = cell_findings(record, {contract.POSTED: (list(cells), [list(cells.values())])}, complete=False)
    assert [(f.code, f.field) for f in found] == [("not_shown", f"{contract.POSTED}: {contract.DENOMINATOR}")]
    shown = POSTED_ROW | {contract.DENOMINATOR: "7 Eyes"}
    found = cell_findings(record, {contract.POSTED: (list(shown), [list(shown.values())])}, complete=False)
    assert found == []


def baseline_group_row(record, g):
    group = record["studies"][0]["baseline"]["groups"][g]
    address = f"/studies/0/baseline/groups/{g}"
    return [
        "NCT01030536",
        address,
        "Baseline",
        group["id"],
        None,
        group["title"],
        group.get("description"),
        None,
        None,
    ]


def baseline_link_findings(target_row):
    """A Baseline row's Group cell linked to the given Groups row (1-based), the Groups sheet holding the
    trial's first two baseline groups."""
    record = posted_groups_record()
    groups = [baseline_group_row(record, 0), baseline_group_row(record, 1)]
    title = record["studies"][0]["baseline"]["groups"][0]["title"]
    cells = {
        "Trial ID": "NCT01030536",
        contract.ADDRESS: "/studies/0/baseline/measures/0/classes/0/categories/0/measurements/0",
        "Group": preserve.Linked(title, contract.GROUPS, target_row),
    }
    sheets = {
        contract.GROUPS: (GROUP_HEADERS, groups),
        contract.BASELINE: (list(cells), [list(cells.values())]),
    }
    found = cell_findings(record, sheets, complete=False)
    return [f for f in found if f.field == f"{contract.BASELINE}: Group"]


def test_a_baseline_group_link_to_its_own_group_carries_its_id():
    assert contract.BASELINE in contract.GROUP_LINKS and contract.FLOW in contract.GROUP_LINKS
    assert baseline_link_findings(1) == []


def test_a_baseline_group_link_to_the_wrong_group_is_caught():
    assert codes(baseline_link_findings(2)) == ["wrong_link"]
    assert codes(baseline_link_findings(9)) == ["wrong_link"]


def module_group_row(record, module, label, g):
    group = record["studies"][0][module]["groups"][g]
    address = f"/studies/0/{module}/groups/{g}"
    return [
        "NCT01030536",
        address,
        label,
        group["id"],
        None,
        group["title"],
        group.get("description"),
        None,
        None,
    ]


FLOW_COUNT = "/studies/0/participant_flow/periods/0/milestones/0/counts/0"
BASELINE_VALUE = "/studies/0/baseline/measures/0/classes/0/categories/0/measurements/0"


def linked_findings(sheet, address, title_of, groups, target):
    """A listing row's Group cell linked to `target`: (the sheet, the data row from 1) among `groups`."""
    record = posted_groups_record()
    cells = {
        "Trial ID": "NCT01030536",
        contract.ADDRESS: address,
        "Group": preserve.Linked(title_of(record), target[0], target[1]),
    }
    sheets = {contract.GROUPS: (GROUP_HEADERS, groups(record)), sheet: (list(cells), [list(cells.values())])}
    return [f for f in cell_findings(record, sheets, complete=False) if f.field == f"{sheet}: Group"]


def both_modules(record):
    return [
        module_group_row(record, "baseline", "Baseline", 0),
        module_group_row(record, "participant_flow", "Participant flow", 0),
    ]


def test_a_flow_group_link_to_its_own_group_carries_its_id():
    title = lambda record: record["studies"][0]["participant_flow"]["groups"][0]["title"]  # noqa: E731
    assert linked_findings(contract.FLOW, FLOW_COUNT, title, both_modules, (contract.GROUPS, 2)) == []


def test_a_group_link_to_the_same_titled_group_of_another_module_is_caught():
    record = posted_groups_record()
    baseline = record["studies"][0]["baseline"]["groups"][0]
    flow = record["studies"][0]["participant_flow"]["groups"][0]
    assert (baseline["title"], baseline.get("description")) == (flow["title"], flow.get("description"))
    title = lambda record: record["studies"][0]["baseline"]["groups"][0]["title"]  # noqa: E731
    found = linked_findings(contract.BASELINE, BASELINE_VALUE, title, both_modules, (contract.GROUPS, 2))
    assert codes(found) == ["wrong_link"]
    assert linked_findings(contract.BASELINE, BASELINE_VALUE, title, both_modules, (contract.GROUPS, 1)) == []


def test_a_group_link_to_a_missing_row_or_another_sheet_is_caught():
    title = lambda record: record["studies"][0]["baseline"]["groups"][0]["title"]  # noqa: E731
    for target in ((contract.GROUPS, 3), (contract.GROUPS, 0), (contract.SAFETY, 1)):
        found = linked_findings(contract.BASELINE, BASELINE_VALUE, title, both_modules, target)
        assert codes(found) == ["wrong_link"], target


def test_an_unlinked_baseline_group_cell_must_still_show_the_groups_id():
    record = posted_groups_record()
    title = record["studies"][0]["baseline"]["groups"][0]["title"]
    cells = {"Trial ID": "NCT01030536", contract.ADDRESS: BASELINE_VALUE, "Group": title}
    found = cell_findings(record, {contract.BASELINE: (list(cells), [list(cells.values())])}, complete=False)
    assert [(f.code, f.field) for f in found if f.field == f"{contract.BASELINE}: Group"] == [
        ("not_shown", f"{contract.BASELINE}: Group")
    ]


def scoped_baseline():
    record = excerpt()
    baseline = record["studies"][1]["baseline"]
    measure = baseline["measures"][0]
    klass = measure["classes"][0]
    for holder in (baseline, measure, klass):
        holder["denominators"] = [{"units": "Participants", "counts": [{"group": "BG000", "value": "7"}]}]
    baseline["population"] = "All treated participants"
    measure["population"] = "Evaluable participants"
    row = baseline_row(preserve.Number(63.4, "0.0"))
    row[contract.DENOMINATOR] = "Class denominator: 7; Measure denominator: 7; Module denominator: 7"
    row["Population"] = (
        "Measure population: Evaluable participants\nBaseline population: All treated participants"
    )
    return record, row


def scoped_baseline_findings(record, row):
    return cell_findings(record, {contract.BASELINE: (list(row), [list(row.values())])}, complete=False)


def test_all_denominator_and_population_scopes_are_shown_independently():
    record, row = scoped_baseline()
    assert scoped_baseline_findings(record, row) == []


def test_equal_denominators_do_not_excuse_dropped_scope_labels():
    record, row = scoped_baseline()
    row[contract.DENOMINATOR] = "7; 7; 7"
    findings = scoped_baseline_findings(record, row)
    assert (
        len([f for f in findings if f.field == f"{contract.BASELINE}: {contract.DENOMINATOR} (scope)"]) == 3
    )


def test_denominator_values_must_not_be_attached_to_another_scope():
    record, row = scoped_baseline()
    measure = record["studies"][1]["baseline"]["measures"][0]
    measure["denominators"][0]["counts"][0]["value"] = "5"
    measure["classes"][0]["denominators"][0]["counts"][0]["value"] = "3"
    row[contract.DENOMINATOR] = "Class denominator: 5; Measure denominator: 3; Module denominator: 7"
    findings = scoped_baseline_findings(record, row)
    assert {tuple(f.expected) for f in findings if f.field.endswith("(scope)")} == {
        ("Class", "3"),
        ("Measure", "5"),
    }


def test_population_values_must_not_lose_their_scope_labels():
    record, row = scoped_baseline()
    row["Population"] = "Evaluable participants; All treated participants"
    findings = scoped_baseline_findings(record, row)
    assert len([f for f in findings if f.field == f"{contract.BASELINE}: Population (scope)"]) == 2


def test_a_denominator_qualifier_must_keep_its_own_scope_even_without_counts():
    record, row = scoped_baseline()
    record["studies"][1]["baseline"]["measures"][0]["units_analyzed"] = "Eyes"
    row[contract.DENOMINATOR] += "; Measure units analyzed (other than participants): Eyes"
    assert scoped_baseline_findings(record, row) == []
    row[contract.DENOMINATOR] = row[contract.DENOMINATOR].replace(
        "Measure units analyzed", "Module units analyzed"
    )
    assert any(f.field.endswith("(scope)") for f in scoped_baseline_findings(record, row))


def test_multiline_dossier_fields_are_read_whole_and_paragraph_loss_is_caught():
    record = {"studies": [project_study(BODIES["NCT01030536"])]}
    arm = record["studies"][0]["arms"][0]
    arm["description"] = "First paragraph.\n\nSecond paragraph with a separate requirement."
    value = f"Arm: {arm['label']}\nArm description: {arm['description']}\n[End of field]"
    row = ["NCT01030536", "Arms", "Arm 1", value, "Registry"]
    findings = cell_findings(record, {contract.REVIEW: (REVIEW_HEADERS, [row])})
    assert not [f for f in findings if f.code != "fact_missing"]
    row[3] = f"Arm: {arm['label']}\nArm description: First paragraph.\n[End of field]"
    findings = cell_findings(record, {contract.REVIEW: (REVIEW_HEADERS, [row])})
    assert any(f.field == "Trial review: Arm 1: Arm description" and f.code == "not_shown" for f in findings)


def test_numeric_enrollment_must_not_return_as_text():
    found = index_findings(Enrollment="135")
    assert [(f.code, f.field) for f in found] == [("retyped", "Trial index: Enrollment")]


def test_placeholder_rows_are_only_the_deepest_empty_source_nodes():
    record = {
        "studies": [
            {
                "nct": "NCT09000001",
                "posted_outcomes": [{"title": "Empty measure", "classes": [{"categories": []}]}],
            }
        ]
    }
    sheet = next(s for s in contract.SHEETS if s.name == contract.POSTED)
    assert preserve.listing_nodes(record, sheet) == ["/studies/0/posted_outcomes/0/classes/0"]
    empty_class = record["studies"][0]["posted_outcomes"][0]["classes"][0]
    empty_class["categories"] = [{"measurements": [{"group": "OG000", "value": "7"}]}]
    assert preserve.listing_nodes(record, sheet) == [
        "/studies/0/posted_outcomes/0/classes/0/categories/0/measurements/0"
    ]


def test_a_placeholder_must_not_hide_an_existing_measurement():
    record = {
        "studies": [
            {
                "nct": "NCT09000001",
                "posted_outcomes": [
                    {"classes": [{"categories": [{"measurements": [{"group": "OG000", "value": "7"}]}]}]}
                ],
            }
        ]
    }
    sheet = next(s for s in contract.SHEETS if s.name == contract.POSTED)
    row = preserve.Row(
        contract.POSTED,
        1,
        {
            "Trial ID": "NCT09000001",
            contract.ADDRESS: "/studies/0/posted_outcomes/0/classes/0",
            "Value": "No measurements posted",
        },
    )
    findings, _address = preserve.row_findings(record, sheet, row)
    assert "wrong_grain" in codes(findings)


def test_missing_confidence_bound_is_written_in_words_while_missing_metadata_is_omitted():
    record = {
        "studies": [
            {"nct": "NCT09000001", "posted_outcomes": [{"analyses": [{"ci_percent": "95", "ci_lower": "2"}]}]}
        ]
    }
    row = {
        "Trial ID": "NCT09000001",
        contract.ADDRESS: "/studies/0/posted_outcomes/0/analyses/0",
        "Confidence interval": "95% CI 2 to Not stated",
    }
    sheets = {contract.ANALYSES: (list(row), [list(row.values())])}
    findings = cell_findings(record, sheets, complete=False)
    assert not [f for f in findings if f.field.startswith("Statistical analyses: Confidence interval")]
    sheets[contract.ANALYSES][1][0][-1] = "95% CI 2"
    findings = cell_findings(record, sheets, complete=False)
    assert any(f.field == "Statistical analyses: Confidence interval (scope)" for f in findings)


@pytest.mark.parametrize(
    "words,accepted",
    [
        ("Interventional — design not stated", True),
        ("Interventional — interventional design fields not applicable", False),
        ("Not applicable", False),
        ("Interventional — design not stated; randomized", False),
        ("Treatment; randomized; parallel assignment; double masked", False),
    ],
)
def test_silent_interventional_index_design_uses_exact_declared_policy(words, accepted):
    study = {"nct": "NCT90000001", "study_type": "INTERVENTIONAL"}
    for name in ("primary_purpose", "allocation", "intervention_model", "masking", "who_masked"):
        study[name] = {"status": "not_stated", "note": "not_reported"}
    design = next(
        c
        for sheet in contract.SHEETS
        if sheet.name == contract.INDEX
        for c in sheet.columns
        if c.header == "Design"
    )
    sheet = contract.Sheet(contract.INDEX, "studies[]", (design,))
    row = preserve.Row(contract.INDEX, 2, {"Trial ID": study["nct"], "Design": words})
    findings = preserve.index_findings({"studies": [study]}, sheet, [row])
    assert (findings == []) is accepted


@pytest.mark.parametrize(
    "field,value",
    [
        ("primary_purpose", "TREATMENT"),
        ("allocation", "RANDOMIZED"),
        ("intervention_model", "PARALLEL"),
        ("masking", "DOUBLE"),
        ("who_masked", ["PARTICIPANT"]),
    ],
)
def test_compact_silent_design_must_not_hide_any_supplied_design_field(field, value):
    study = {"nct": "NCT90000001", "study_type": "INTERVENTIONAL"}
    for name in ("primary_purpose", "allocation", "intervention_model", "masking", "who_masked"):
        study[name] = {"status": "not_stated", "note": "not_reported"}
    study[field] = value
    design = next(
        c
        for sheet in contract.SHEETS
        if sheet.name == contract.INDEX
        for c in sheet.columns
        if c.header == "Design"
    )
    sheet = contract.Sheet(contract.INDEX, "studies[]", (design,))
    row = preserve.Row(
        contract.INDEX, 2, {"Trial ID": study["nct"], "Design": "Interventional — design not stated"}
    )
    assert preserve.index_findings({"studies": [study]}, sheet, [row])


@pytest.mark.parametrize(
    "wrong",
    [
        "Class one [ID: id-one; relation: rel-one; source: source-one]",
        "Class one\nClass two",
        (
            "Class one [ID: id-two; relation: rel-one; source: source-one]\n"
            "Class two [ID: id-one; relation: rel-two; source: source-two]"
        ),
        (
            "Class one [ID: id-one; relation: rel-one; source: source-one] or "
            "Class two [ID: id-two; relation: rel-two; source: source-two]"
        ),
        (
            "Class one [ID: id-one; relation: rel-one; source: source-two]\n"
            "Class two [ID: id-two; relation: rel-two; source: source-one]"
        ),
    ],
)
def test_direct_class_display_must_keep_each_source_tuple_and_line(wrong):
    field = contract.FIELD_NAMES["studies[].interventions[].drug_class"]
    value = {
        "status": "known",
        "rule": field.source[0],
        "words": ["Source intervention"],
        "note": "",
        "result": {
            "state": "classified",
            "resolved_by": "Source intervention",
            "classes": [
                ["id-one", "Class one", "rel-one", "source-one"],
                ["id-two", "Class two", "rel-two", "source-two"],
            ],
        },
    }
    expected = preserve.expected(field, value)
    correct = (
        "Class one [ID: id-one; relation: rel-one; source: source-one]\n"
        "Class two [ID: id-two; relation: rel-two; source: source-two]"
    )
    assert preserve.judge(correct, expected, False) == "shown"
    assert preserve.judge(wrong, expected, False) != "shown"


@pytest.mark.parametrize(
    "status, state",
    (("unresolved", "classified"), ("unresolved", "conflict"), ("known", "conflict")),
)
def test_class_source_display_does_not_promote_unresolved_or_conflicting_payloads(status, state):
    field = contract.FIELD_NAMES["studies[].interventions[].drug_class"]
    value = {
        "status": status,
        "rule": field.source[0],
        "words": ["Source intervention"],
        "note": "identity unresolved",
        "result": {"state": state, "classes": [["id", "Source class", "relation", "source"]]},
    }
    wanted = preserve.expected(field, value)
    assert preserve.judge("Unresolved — identity unresolved", wanted, False) == "shown"
    assert (
        preserve.judge("Source class [ID: id; relation: relation; source: source]", wanted, False) != "shown"
    )


@pytest.mark.parametrize(
    "study_type,type_words", [("OBSERVATIONAL", "Observational"), ("EXPANDED_ACCESS", "Expanded access")]
)
def test_noninterventional_absence_notes_require_applicability_words(study_type, type_words):
    study = {
        "nct": "NCT90000001",
        "study_type": study_type,
        "who_masked": {"status": "not_stated", "note": "not_reported"},
    }
    for name in ("phases", "primary_purpose", "allocation", "intervention_model", "masking"):
        study[name] = {"status": "not_stated", "note": "not_applicable"}
    design = next(
        c
        for sheet in contract.SHEETS
        if sheet.name == contract.INDEX
        for c in sheet.columns
        if c.header == "Design"
    )
    phase = next(
        c
        for sheet in contract.SHEETS
        if sheet.name == contract.INDEX
        for c in sheet.columns
        if c.header == "Phase"
    )
    sheet = contract.Sheet(contract.INDEX, "studies[]", (design, phase))
    row = preserve.Row(
        contract.INDEX,
        2,
        {
            "Trial ID": study["nct"],
            "Design": f"{type_words} — interventional design fields not applicable",
            "Phase": "Not applicable",
        },
    )
    assert preserve.index_findings({"studies": [study]}, sheet, [row]) == []
    row.cells["Phase"] = "Not stated"
    assert preserve.index_findings({"studies": [study]}, sheet, [row])
    study["phases"] = ["PHASE3"]
    row.cells["Phase"] = "Not applicable"
    assert preserve.index_findings({"studies": [study]}, sheet, [row])


@pytest.mark.parametrize(
    "name,value",
    [
        ("primary_purpose", "TREATMENT"),
        ("allocation", "RANDOMIZED"),
        ("intervention_model", "PARALLEL"),
        ("masking", "NONE"),
        ("who_masked", ["PARTICIPANT"]),
    ],
)
def test_noninterventional_summary_cannot_hide_any_source_present_design_value(name, value):
    study = {"nct": "NCT90000001", "study_type": "OBSERVATIONAL"}
    for key in ("primary_purpose", "allocation", "intervention_model", "masking", "who_masked"):
        study[key] = {"status": "not_stated", "note": "not_applicable"}
    study[name] = value
    design = next(
        c
        for sheet in contract.SHEETS
        if sheet.name == contract.INDEX
        for c in sheet.columns
        if c.header == "Design"
    )
    sheet = contract.Sheet(contract.INDEX, "studies[]", (design,))
    row = preserve.Row(
        contract.INDEX,
        2,
        {"Trial ID": study["nct"], "Design": "Observational — interventional design fields not applicable"},
    )
    assert preserve.index_findings({"studies": [study]}, sheet, [row])


def test_date_shaped_prose_is_literal_while_typed_registry_dates_use_date_format():
    comment = contract.FIELD_NAMES["studies[].participant_flow.periods[].milestones[].comment"]
    typed = contract.FIELD_NAMES["studies[].start_date.date"]
    prose = preserve.expected(comment, "2016-12-27")
    date = preserve.expected(typed, "2016-12-27")
    assert preserve.judge("2016-12-27", prose, False) == "shown"
    assert preserve.judge("27-Dec-2016", prose, False) != "shown"
    assert preserve.judge("27-Dec-2016", date, False) == "shown"
    assert preserve.judge("30-Dec-2016", date, False) != "shown"


def test_grouped_enrollment_display_does_not_relax_the_integer_value():
    field = contract.FIELD_NAMES["studies[].enrollment.count"]
    want = preserve._values_expected(field, [1074])
    assert preserve.judge("1,074 (Actual)", want, False) == "shown"
    assert preserve.judge("1,075 (Actual)", want, False) != "shown"
    assert preserve.judge("11,074 (Actual)", want, False) != "shown"


@pytest.mark.parametrize("placeholder", [False, True])
@pytest.mark.parametrize(
    "wrong",
    [
        "Not stated",
        "Not applicable",
        "Standard Deviation",
        "Standard Deviation: 7",
        "Standard Deviation: Not stated; 7",
    ],
)
def test_known_dispersion_type_with_no_numeric_spread_is_not_erased_or_filled(placeholder, wrong):
    measurement = {"group": "G1", "value": "53"}
    measure = {
        "dispersion_type": "Standard Deviation",
        "classes": [] if placeholder else [{"categories": [{"measurements": [measurement]}]}],
    }
    record = {"studies": [{"nct": "NCT90000001", "posted_outcomes": [measure]}]}
    address = "/studies/0/posted_outcomes/0" + (
        "" if placeholder else "/classes/0/categories/0/measurements/0"
    )
    column = next(
        c
        for s in contract.SHEETS
        if s.name == contract.POSTED
        for c in s.columns
        if c.header == "Spread or limits"
    )
    sheet = contract.Sheet(contract.POSTED, "studies[].posted_outcomes[]", (column,))
    row = preserve.Row(
        contract.POSTED,
        2,
        {
            "Trial ID": "NCT90000001",
            contract.ADDRESS: address,
            "Spread or limits": "Standard Deviation: Not stated",
        },
    )
    assert preserve.row_findings(record, sheet, row)[0] == []
    row.cells["Spread or limits"] = wrong
    assert preserve.row_findings(record, sheet, row)[0]


def test_typed_anticipated_posting_month_is_formatted_but_identical_comment_is_literal():
    typed = contract.FIELD_NAMES["studies[].posted_outcomes[].anticipated_posting_date"]
    comment = contract.FIELD_NAMES["studies[].participant_flow.periods[].milestones[].comment"]
    want = preserve.expected(typed, "2028-06")
    assert preserve.judge("Not posted (anticipated Jun-2028)", want, False) == "shown"
    assert preserve.judge("Not posted (anticipated Jul-2028)", want, False) != "shown"
    assert preserve.judge("Jun-2028", preserve.expected(comment, "2028-06"), False) != "shown"
