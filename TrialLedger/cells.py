"""What a spreadsheet can hold exactly. The writer never truncates, cleans or reinterprets a value.

openpyxl (3.1.5, read 2026-10-31) silently cuts any string to 32,767 characters; raises on control characters
and writes the other characters XML 1.0 forbids (U+FFFE, U+FFFF) into a file it cannot read back; turns a
string starting with "=" into a formula and an error-code string into an error cell; writes a number as
"%.16g" (openpyxl.compat.strings.safe_string) and reads it back as an int when that text holds no ".", "e"
or "E", otherwise as a float (openpyxl.worksheet._reader._cast_number); and an xlsx read-back turns a
carriage return into a line feed (tested). The characters, lengths and numbers are answered here, by
refusing such a value a cell with a named reason; the type rewrites are answered in the writer, which
forces every text cell to text.
"""

from __future__ import annotations

import math
import re

CELL_LIMIT = 32767  # Excel's limit on characters in a cell; counted here in UTF-16 code units, the stricter
ROW_LIMIT = 1048576  # rows in a worksheet, the header row included
# Every character XML 1.0 does not allow (Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] |
# [#x10000-#x10FFFF]), lone surrogates included; openpyxl.cell.cell.ILLEGAL_CHARACTERS_RE is its C0 part.
FORBIDDEN_CHARACTERS = re.compile(r"[^\t\n\r\x20-퟿-�\U00010000-\U0010ffff]")
DIGITS_LIMIT = 10**16  # "%.16g" writes an integer this large in exponent form, which reads back as a float


def cell_text_state(text: str) -> str:
    """Whether a spreadsheet cell can hold `text` exactly (pure — pinned).

    The first that applies, in this order:
      "forbidden_characters" — the text holds a character the file format (XML 1.0) forbids: a control
                               character other than tab, line feed and carriage return, U+FFFE, U+FFFF,
                               or a lone surrogate.
      "carriage_return"      — the text holds a carriage return, which would come back as a line feed.
      "too_long"             — the text is longer than a cell holds (32,767 UTF-16 code units).
      "ok"                   — it can.
    """
    if FORBIDDEN_CHARACTERS.search(text):
        return "forbidden_characters"
    if "\r" in text:
        return "carriage_return"
    if len(text.encode("utf-16-le")) // 2 > CELL_LIMIT:
        return "too_long"
    return "ok"


def cell_number_state(number: int | float) -> str:
    """Whether a spreadsheet cell holds `number` exactly, as openpyxl writes and reads it (pure — pinned).

    A number is written as "%.16g" and read back as an int when that text holds no ".", "e" or "E" ("%.16g"
    writes no "E"), otherwise as a float. It is held exactly when what comes back is the same number: an
    integer the same integer, a float the same double with the same sign of zero. A boolean, an int to
    Python, is held exactly.
      "ok"        — it is held exactly.
      "not_exact" — it is not: an integer of 17 or more digits, or one no double holds exactly; a float
                    that needs 17 significant digits; negative zero; NaN; an infinity.
    """
    if isinstance(number, int):
        return "ok" if abs(number) < DIGITS_LIMIT and float(number) == number else "not_exact"
    if not math.isfinite(number):
        return "not_exact"
    written = "%.16g" % number  # noqa: UP031 — the writer's own expression (openpyxl safe_string)
    back = float(written) if "." in written or "e" in written else int(written)
    same_sign = math.copysign(1.0, back) == math.copysign(1.0, number)
    return "ok" if back == number and same_sign else "not_exact"


GOOGLE_SHEETS_CELLS = 10_000_000  # Google Sheets' cap on the cells of one spreadsheet


def book_size_state(cells: int) -> str:
    """Whether every common spreadsheet app opens a workbook of `cells` cells (pure — pinned).

    "fits"               — at most 10,000,000 cells, the most Google Sheets opens in one spreadsheet.
    "over_google_sheets" — more cells than that: Google Sheets refuses it.
    """
    return "fits" if cells <= GOOGLE_SHEETS_CELLS else "over_google_sheets"


def sheet_fits(data_rows: int) -> str:
    """Whether a sheet of `data_rows` rows, plus its header row, fits a worksheet (pure — pinned).

    "fits" or "too_many_rows".
    """
    return "fits" if data_rows + 1 <= ROW_LIMIT else "too_many_rows"
