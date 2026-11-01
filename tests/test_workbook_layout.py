"""The workbooks laid out for a clinical reader: type, panes, filters, widths, wrapping and print setup.

Positive: on the review and record books written from the test records, every listing (continuation sheets
included) has its header row bold in Arial and ruled below, the header row and identifying column frozen, a
filter over every row, each column's width by its class and its cells top-aligned and wrapped as the class
says, landscape pages repeating the header row with a footer of the sheet's name and page number; a narrow
sheet is fitted to one page wide and a wide one printed over a defined print area repeating its identifying
column; About is first and laid out the same way; the Normal style, so every empty cell and whatever a reader
types, is Arial 10; a link is underlined; two writes of one record are identical part for part.
Negative: no cell is merged; no sheet holds a formula; a wide sheet is never scaled to fit; no warrant,
digest, NCT number, PMID, file name or group id is wider than its column, so none is broken or cut off; About,
which has no header row, is given no frozen header and no filter; a link is given no colour; the layout
changes no value, so each book certifies.
"""

import re
import zipfile

import pytest
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from records import ongoing_study, results_study

from TrialLedger import workbook
from TrialLedger.workbook import (
    ABOUT_CLASSES,
    BOOKS,
    FOOTER_LEFT,
    FOOTER_RIGHT,
    RECORD,
    REVIEW,
    WARRANT_HEADER,
    WIDTHS,
    WRAPS,
    certify,
    file_problems,
    print_fit,
    width_class,
    write_workbook,
)


def record(*studies):
    return {"provenance": {"data_timestamp": "2026-10-30T09:00:04"}, "studies": list(studies)}


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    folder = tmp_path_factory.mktemp("layout")
    data = record(results_study(), ongoing_study())
    for book in BOOKS:
        write_workbook(data, folder / book.name, book)
    return data, folder


def sheet_classes(book, name):
    sheet = next(sheet for sheet in book.sheets if name == sheet.name or name.startswith(f"{sheet.name} "))
    classes = [width_class(column.kind, column.source) for column in sheet.columns]
    return classes + ([width_class("warrant", WARRANT_HEADER)] if sheet.warranted else [])


def widths(sheet, count):
    held = {}
    for dimension in sheet.column_dimensions.values():
        for number in range(dimension.min, dimension.max + 1):
            held[number] = dimension.width
    return [held.get(number) for number in range(1, count + 1)]


def check_page(sheet, classes, listing):
    """What every worksheet, a listing or About, must show and print like."""
    assert widths(sheet, len(classes)) == [WIDTHS[code] for code in classes], sheet.title
    assert sheet.page_setup.orientation == "landscape", sheet.title
    assert (sheet.oddFooter.left.text, sheet.oddFooter.right.text) == (FOOTER_LEFT, FOOTER_RIGHT)
    assert not sheet.merged_cells.ranges, sheet.title
    column = get_column_letter(len(classes))
    if print_fit(sum(WIDTHS[code] for code in classes)) == "fit_width":
        assert sheet.sheet_properties.pageSetUpPr.fitToPage, sheet.title
        assert (sheet.page_setup.fitToWidth, sheet.page_setup.fitToHeight) == (1, 0), sheet.title
    else:
        assert not sheet.sheet_properties.pageSetUpPr or not sheet.sheet_properties.pageSetUpPr.fitToPage
        assert sheet.print_area == f"'{sheet.title}'!$A$1:${column}${sheet.max_row}", sheet.title
        assert sheet.print_title_cols == ("$A:$A" if listing else None), sheet.title
    for row in sheet.iter_rows(min_row=2 if listing else 1):
        for cell, code in zip(row, classes, strict=False):
            assert cell.data_type != "f", cell.coordinate
            assert cell.font.name == "Arial" and cell.font.sz == 10, cell.coordinate
            assert cell.alignment.vertical == "top", cell.coordinate
            assert bool(cell.alignment.wrap_text) == WRAPS[code], (sheet.title, cell.coordinate, code)
            assert cell.alignment.horizontal is None, cell.coordinate  # text left, numbers right


def check_listing(sheet, classes):
    assert sheet.freeze_panes == "B2", sheet.title
    assert sheet.auto_filter.ref == f"A1:{get_column_letter(len(classes))}{sheet.max_row}", sheet.title
    assert sheet.print_title_rows == "$1:$1", sheet.title
    for cell in next(sheet.iter_rows(max_row=1)):
        assert cell.font.b and cell.font.name == "Arial", cell.coordinate
        assert cell.border.bottom.style == "thin", cell.coordinate
        assert cell.alignment.wrap_text and cell.alignment.vertical == "top", cell.coordinate
    check_page(sheet, classes, listing=True)


def test_every_listing_is_laid_out_for_a_clinical_reader(written):
    _, folder = written
    for book in BOOKS:
        opened = load_workbook(folder / book.name)
        try:
            assert opened.sheetnames[0] == "About"
            for name in opened.sheetnames[1:]:
                check_listing(opened[name], sheet_classes(book, name))
        finally:
            opened.close()


def test_about_is_first_and_printed_but_has_no_header_to_freeze_or_filter(written):
    _, folder = written
    for book in BOOKS:
        opened = load_workbook(folder / book.name)
        try:
            about = opened["About"]
            assert about.freeze_panes is None and about.auto_filter.ref is None
            assert about.print_title_rows is None
            check_page(about, list(ABOUT_CLASSES), listing=False)
        finally:
            opened.close()


def test_the_technical_sheets_come_last(written):
    _, folder = written
    opened = load_workbook(folder / REVIEW.name, read_only=True)
    names = opened.sheetnames
    opened.close()
    assert names[-2:] == ["Checks", "Check Rules"]
    assert [sheet.name for sheet in RECORD.sheets] == ["Record"]


def test_a_narrow_sheet_fits_one_page_wide_and_a_wide_one_is_never_scaled(written):
    _, folder = written
    opened = load_workbook(folder / REVIEW.name)
    try:
        about, checks, studies = opened["About"], opened["Checks"], opened["Studies"]
        assert about.sheet_properties.pageSetUpPr.fitToPage
        assert not about.print_area
        assert not (studies.sheet_properties.pageSetUpPr and studies.sheet_properties.pageSetUpPr.fitToPage)
        assert studies.print_area == f"'Studies'!$A$1:$AX${studies.max_row}"
        assert studies.print_title_cols == "$A:$A"
        assert not (checks.sheet_properties.pageSetUpPr and checks.sheet_properties.pageSetUpPr.fitToPage)
        assert checks.print_area == f"'Checks'!$A$1:$E${checks.max_row}"
    finally:
        opened.close()


def test_no_identifier_or_warrant_is_broken_or_cut_off(written):
    _, folder = written
    seen = set()
    for book in BOOKS:
        opened = load_workbook(folder / book.name)
        try:
            for name in opened.sheetnames[1:]:
                classes = sheet_classes(book, name)
                headers = [cell.value for cell in next(opened[name].iter_rows(max_row=1))]
                for row in opened[name].iter_rows(min_row=2):
                    for cell, code, header in zip(row, classes, headers, strict=False):
                        if code in ("identifier", "warrant") and cell.value is not None:
                            seen.add(header)
                            assert len(str(cell.value)) <= WIDTHS[code], (name, cell.coordinate, code)
        finally:
            opened.close()
    assert not WRAPS["warrant"]
    assert {"NCT Number", "PMID", "File", "Group ID", "Record Digest", "Warrant"} <= seen


def test_an_empty_cell_reads_in_arial_10_and_a_link_is_underlined_without_colour(written):
    _, folder = written
    for book in BOOKS:
        with zipfile.ZipFile(folder / book.name) as package:
            styles = package.read("xl/styles.xml").decode()
        first_font = re.search(r"<font>(.*?)</font>", styles, re.S).group(1)
        assert '<name val="Arial"' in first_font and '<sz val="10"' in first_font, book.name
        assert "Calibri" not in styles, book.name
        assert re.search(r'<cellStyle name="Normal" xfId="0" builtinId="0"[^>]*/>', styles), book.name
        assert re.search(r'<cellStyleXfs count="1">\s*<xf numFmtId="0" fontId="0"', styles), book.name
    opened = load_workbook(folder / REVIEW.name)
    try:
        link, plain = opened["Studies"]["A2"], opened["Studies"]["B2"]
        assert link.hyperlink is not None and link.font.u == "single" and link.font.color is None
        assert plain.hyperlink is None and plain.font.u is None
    finally:
        opened.close()


def test_the_layout_changes_no_value(written):
    data, folder = written
    for book in BOOKS:
        assert certify(data, folder / book.name, book=book) == []
        assert file_problems(data, folder / book.name, book) == []


def test_two_writes_of_one_record_are_identical_part_for_part(tmp_path):
    data = record(results_study(), ongoing_study())
    for book in BOOKS:
        first, second = tmp_path / f"a-{book.name}", tmp_path / f"b-{book.name}"
        write_workbook(data, first, book)
        write_workbook(data, second, book)
        with zipfile.ZipFile(first) as one, zipfile.ZipFile(second) as two:
            assert one.namelist() == two.namelist()
            for name in one.namelist():
                if name != "docProps/core.xml":  # the write times openpyxl stamps
                    assert one.read(name) == two.read(name), (book.name, name)


def test_a_continuation_sheet_is_laid_out_like_the_first(tmp_path, monkeypatch):
    monkeypatch.setattr(
        workbook, "sheet_fits", lambda data_rows: "fits" if data_rows + 1 <= 40 else "too_many_rows"
    )
    data = record(results_study(), ongoing_study())
    path = tmp_path / RECORD.name
    write_workbook(data, path, RECORD)
    opened = load_workbook(path)
    try:
        parts = [name for name in opened.sheetnames if name != "About"]
        assert len(parts) > 1 and parts[1] == "Record 2"
        for name in parts:
            check_listing(opened[name], sheet_classes(RECORD, name))
    finally:
        opened.close()
