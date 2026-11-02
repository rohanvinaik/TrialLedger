"""Long dossier display remains exact and readable; its independent check reads the written parts."""

import copy

import pytest
from openpyxl import load_workbook
from schema3_records import BODIES, record_of

from acceptance import preserve
from TrialLedger import contract, readout
from TrialLedger.cells import CELL_LIMIT

NCT = "NCT01030536"
FACT = contract.FIELD_NAMES["studies[].eligibility.text"].label
HEADERS = ["Trial ID", "Section", "Fact", "Value", "Basis"]


def report_with(text):
    body = copy.deepcopy(BODIES[NCT])
    body["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = text
    return record_of((NCT,), bodies={NCT: body})


@pytest.mark.parametrize(
    "text",
    (
        "Inclusion Criteria:\n" + "The source requirement remains exactly as written. " * 240,
        "X" * 12000,
        "First physical line.\n\nSecond physical line.\n" * 80,
        "患者 αβγ, café, naïve, 😀.\n" * 180,
        " \t\n\n" + " source words with spaces " * 240 + "\n \t ",
    ),
)
def test_long_dossier_parts_preserve_every_character_and_fit_readable_rows(text, tmp_path):
    record = report_with(text)
    before = copy.deepcopy(record)
    study = record["studies"][0]
    expected = next(value for _, _, fact, value, _ in readout.dossier_facts(study) if fact == FACT)
    path = tmp_path / "continued.xlsx"
    readout.write_book(record, path)
    book = load_workbook(path)
    review = book[contract.REVIEW]
    parts = [row for row in review.iter_rows(min_row=2) if row[2].value.startswith(FACT + " (part ")]
    assert len(parts) > 1
    assert "".join(row[3].value for row in parts) == expected
    for number, row in enumerate(parts, 1):
        assert row[0].value == NCT
        assert row[1].value == "Population and eligibility"
        assert row[2].value == contract.DOSSIER_PART_FORM.format(fact=FACT, part=number, count=len(parts))
        assert row[4].value == "Registry"
        assert row[3].alignment.wrap_text is True
        assert (
            review.row_dimensions[row[0].row].height <= contract.DOSSIER_LINES_PER_ROW * readout.LINE_POINTS
        )
        assert review.row_dimensions[row[0].row].height < contract.MAX_ROW_HEIGHT_POINTS
    assert [row[4].value for row in list(book[contract.ELIGIBILITY])[1:]] == [
        piece["text"] for piece in study["criteria"]
    ]
    index = book[contract.INDEX]
    target = index.cell(2, index.max_column).hyperlink.location.split("!")[1]
    assert review[target].value == NCT
    book.close()
    assert record == before
    assert readout.book_problems(record, path) == []
    assert preserve.cell_findings(record, preserve.workbook_sheets(path)) == []


@pytest.mark.parametrize("length, count", ((2400, 1), (2401, 2), (4800, 2), (4801, 3)))
def test_dossier_row_budget_boundary_uses_full_exact_slices(length, count):
    text = "x" * length
    parts = readout.dossier_value_parts(text)
    assert len(parts) == count
    assert "".join(parts) == text
    assert all(len(part) <= 2400 for part in parts)


@pytest.mark.parametrize(
    "value",
    (
        "x" * (CELL_LIMIT + 1),
        "😀" * (CELL_LIMIT // 2 + 1),
        "source\r\nline",
        "source\x07line",
    ),
)
def test_display_parts_do_not_bypass_an_existing_cell_refusal(value):
    assert readout.dossier_value_parts(value) == [value]
    shown = readout.written_safely([(readout.cell(value, "known"),)])
    assert shown[0][0][0].startswith("Unresolved — not written:")


def manual_parts():
    text = " \talpha\n\nβeta 😀 \nωmega  "
    record = {"studies": [{"nct": NCT, "eligibility": {"text": text}}]}
    values = [" \talpha\n", "\nβeta 😀 \n", "ωmega  \n[End of field]"]
    rows = [
        [NCT, "Population and eligibility", f"{FACT} (part {i} of 3)", value, "Registry"]
        for i, value in enumerate(values, 1)
    ]
    return record, rows


def independent_findings(record, rows):
    return preserve.cell_findings(record, {contract.REVIEW: (HEADERS, rows)})


def test_independent_dossier_check_joins_authored_parts_without_using_the_writer(monkeypatch):
    record, rows = manual_parts()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("The independent check must not call the writer")

    monkeypatch.setattr(readout, "dossier_value_parts", forbidden)
    monkeypatch.setattr(readout, "book_plan", forbidden)
    assert independent_findings(record, rows) == []


@pytest.mark.parametrize("case", ("missing", "reordered", "duplicated", "orphan", "whole_group"))
def test_independent_dossier_check_refuses_broken_part_sequences(case):
    record, rows = manual_parts()
    changed = {
        "missing": [rows[0], rows[2]],
        "reordered": [rows[1], rows[0], rows[2]],
        "duplicated": [rows[0], rows[1], rows[1], rows[2]],
        "orphan": [rows[1]],
        "whole_group": rows + rows,
    }[case]
    assert "continuation_invalid" in {f.code for f in independent_findings(record, changed)}


@pytest.mark.parametrize("column, replacement", ((0, "NCT00000001"), (1, "Other section"), (4, "Note")))
def test_independent_dossier_check_refuses_a_changed_part_context(column, replacement):
    record, rows = manual_parts()
    rows[1][column] = replacement
    assert "continuation_invalid" in {f.code for f in independent_findings(record, rows)}


@pytest.mark.parametrize("case", ("space_lost", "unicode_lost", "extra_prefix", "extra_suffix"))
def test_independent_dossier_check_compares_the_complete_exact_source(case):
    record, rows = manual_parts()
    if case == "space_lost":
        rows[0][3] = rows[0][3][1:]
    elif case == "unicode_lost":
        rows[1][3] = rows[1][3].replace("😀", "")
    elif case == "extra_prefix":
        rows[0][3] = rows[0][3] + rows[0][3]
    else:
        rows[-1][3] += "extra"
    assert "not_shown" in {f.code for f in independent_findings(record, rows)}


def test_independent_dossier_check_refuses_inconsistent_part_counts():
    record, rows = manual_parts()
    rows[1][2] = f"{FACT} (part 2 of 4)"
    assert "continuation_invalid" in {f.code for f in independent_findings(record, rows)}


def test_an_exact_whitespace_source_passage_is_not_a_missing_cell():
    text = " \t\n\n"
    assert preserve.cell_verdict(text, [text], [], [], False) == "shown"
    assert preserve.cell_verdict(None, [text], [], [], False) == "blank"
    assert preserve.cell_verdict(" ", [text], [], [], False) == "blank"
    assert preserve.cell_verdict(text, [], [], ["Not stated"], False) == "blank"


def test_a_long_numbered_dossier_element_is_reassembled_and_checked_as_its_source(tmp_path):
    body = copy.deepcopy(BODIES[NCT])
    text = "Literal arm paragraph.\n\nSecond paragraph with unchanged source spacing.  \n" * 30
    body["protocolSection"]["armsInterventionsModule"]["armGroups"][0]["description"] = text
    record = record_of((NCT,), bodies={NCT: body})
    path = tmp_path / "long-arm.xlsx"
    readout.write_book(record, path)
    sheets = preserve.workbook_sheets(path)
    assert preserve.cell_findings(record, sheets) == []
    rows = sheets[contract.REVIEW][1]
    parts = [row for row in rows if row[2].startswith("Arm 1 (part ")]
    assert len(parts) > 1
    parts[0][3] += parts[0][3]
    assert "not_shown" in {finding.code for finding in preserve.cell_findings(record, sheets)}
