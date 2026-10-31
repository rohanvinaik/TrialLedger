"""compare_formats — the JSON record and the spreadsheet must hold the same studies.

Positive: the same NCT IDs, in any order, are "same".
Negative: a study missing from either side, an extra one, or a different number of copies is never "same".
"""

from TrialLedger.ingest import compare_formats


def test_same_ids_in_the_same_order():
    assert compare_formats(["NCT00000001", "NCT00000002"], ["NCT00000001", "NCT00000002"]) == "same"


def test_same_ids_in_another_order():
    assert compare_formats(["NCT00000002", "NCT00000001"], ["NCT00000001", "NCT00000002"]) == "same"


def test_spreadsheet_rows_in_another_order_are_same():
    assert compare_formats(["NCT00000001", "NCT00000002"], ["NCT00000002", "NCT00000001"]) == "same"


def test_both_empty_is_same():
    assert compare_formats([], []) == "same"


def test_study_missing_from_the_spreadsheet():
    assert compare_formats(["NCT00000001", "NCT00000002"], ["NCT00000001"]) == "different"


def test_study_missing_from_the_record():
    assert compare_formats(["NCT00000001"], ["NCT00000001", "NCT00000002"]) == "different"


def test_different_study():
    assert compare_formats(["NCT00000001"], ["NCT00000009"]) == "different"


def test_different_number_of_copies():
    assert compare_formats(["NCT00000001", "NCT00000001"], ["NCT00000001"]) == "different"
