"""cell_text_state, cell_number_state and sheet_fits — what a spreadsheet can hold exactly.

Positive: ordinary text, tabs, line feeds, edge whitespace, "="-text, error-code text and every character
XML 1.0 allows are "ok" (the writer forces text to text); integers a double holds below 10**16, floats that
"%.16g" carries exactly, integral floats and booleans are held exactly, as openpyxl's own round trip
confirms; a sheet up to the row limit fits.
Negative: the characters XML 1.0 forbids (controls, U+FFFE, U+FFFF, lone surrogates), carriage returns and
text over the cell limit are never "ok", and a forbidden character outranks the other reasons; the limit
counts UTF-16 code units; integers no double holds, integers of 17 digits, floats needing 17 significant
digits, negative zero, NaN and infinities are never "ok"; a sheet one row over the limit does not fit.
"""

import math

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell

from TrialLedger.cells import CELL_LIMIT, ROW_LIMIT, cell_number_state, cell_text_state, sheet_fits


@pytest.mark.parametrize(
    "text",
    [
        "",
        "plain",
        "tab\there",
        "line\nfeed",
        "  edges  ",
        "=SUM(A1)",
        "#N/A",
        "x" * CELL_LIMIT,
        "é" * CELL_LIMIT,
        "퟿�",
        "😀 \U0010ffff",
    ],
)
def test_text_a_cell_holds_exactly(text):
    assert cell_text_state(text) == "ok"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("bell\x07", "forbidden_characters"),
        ("\x00", "forbidden_characters"),
        ("vertical\x0btab", "forbidden_characters"),
        ("form\x0cfeed", "forbidden_characters"),
        ("unit\x1fseparator", "forbidden_characters"),
        ("a￾b", "forbidden_characters"),
        ("a￿b", "forbidden_characters"),
        ("lone \ud800 surrogate", "forbidden_characters"),
        ("\udfff", "forbidden_characters"),
        ("a\r\nb", "carriage_return"),
        ("a\rb", "carriage_return"),
        ("x" * (CELL_LIMIT + 1), "too_long"),
        ("😀" * (CELL_LIMIT // 2 + 1), "too_long"),
    ],
)
def test_text_a_cell_cannot_hold_exactly(text, expected):
    assert cell_text_state(text) == expected


def test_forbidden_characters_outrank_the_other_reasons():
    assert cell_text_state("\x07\r" + "x" * CELL_LIMIT) == "forbidden_characters"
    assert cell_text_state("\ud800" + "x" * CELL_LIMIT) == "forbidden_characters"
    assert cell_text_state("\r" + "x" * CELL_LIMIT) == "carriage_return"


HELD = [0, 7, -7, 2**53, -(2**53), 2**53 + 2, 9999999999999998, True, False, 0.0, 0.1, -2.5, 2.0, 1e20, 1e-7]
HELD += [40.71427, 1 / 3, 1e300]
NOT_HELD = [2**53 + 1, -(2**53 + 1), 10**16, -(10**16), 10**20, -(10**20), 10**400, -(10**400)]
NOT_HELD += [9999999999999999, 123456789.12345679]
NOT_HELD += [0.1 + 0.2, -0.0, math.nan, math.inf, -math.inf, 1.7976931348623157e308]


@pytest.mark.parametrize("number", HELD)
def test_a_number_a_cell_holds_exactly(number):
    assert cell_number_state(number) == "ok"


@pytest.mark.parametrize("number", NOT_HELD)
def test_a_number_a_cell_cannot_hold_exactly(number):
    assert cell_number_state(number) == "not_exact"


def test_the_decision_is_openpyxls_own_round_trip(tmp_path):
    numbers = [n for n in HELD + NOT_HELD if not (isinstance(n, int) and abs(n) > 10**300)]
    book = Workbook(write_only=True)
    sheet = book.create_sheet("n")
    sheet.append([WriteOnlyCell(sheet, value=number) for number in numbers])
    book.save(tmp_path / "numbers.xlsx")
    book = load_workbook(tmp_path / "numbers.xlsx", read_only=True)
    back = list(next(book["n"].iter_rows(values_only=True)))
    book.close()
    for number, held in zip(numbers, back, strict=True):
        if isinstance(number, bool):
            exact = held is number
        elif isinstance(number, int):
            exact = type(held) is int and held == number
        else:
            exact = (
                isinstance(held, (int, float))
                and float(held) == number
                and math.copysign(1.0, float(held)) == math.copysign(1.0, number)
            )
        assert (cell_number_state(number) == "ok") == exact, (number, held)


def test_sheet_fits_up_to_the_row_limit():
    assert sheet_fits(0) == "fits"
    assert sheet_fits(ROW_LIMIT - 1) == "fits"
    assert sheet_fits(ROW_LIMIT) == "too_many_rows"
