"""book_size_state — whether every common spreadsheet app opens a workbook of so many cells.

Positive: up to and including Google Sheets' cap of 10,000,000 cells, a workbook fits.
Negative: one cell more than the cap, or any number above it, is named as over Google Sheets' cap.
"""

import pytest

from TrialLedger.cells import GOOGLE_SHEETS_CELLS, book_size_state


def test_the_cap_is_google_sheets():
    assert GOOGLE_SHEETS_CELLS == 10_000_000


@pytest.mark.parametrize("cells", [0, 1, 2_178_689, GOOGLE_SHEETS_CELLS])
def test_a_workbook_up_to_the_cap_fits(cells):
    assert book_size_state(cells) == "fits"


@pytest.mark.parametrize("cells", [GOOGLE_SHEETS_CELLS + 1, 17_000_000])
def test_a_workbook_over_the_cap_is_named(cells):
    assert book_size_state(cells) == "over_google_sheets"
