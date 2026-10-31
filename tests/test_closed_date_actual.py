"""closed_date_actual — a completed or terminated study's completion dates are typed actual.

Positive: COMPLETED or TERMINATED with an ACTUAL date is consistent; with an ESTIMATED date, a conflict.
Negative: a missing status or date type is never consistent; a study that is not closed is never judged.
"""

import pytest

from TrialLedger.checks import closed_date_actual


@pytest.mark.parametrize(
    "status, date_type, expected",
    [
        ("COMPLETED", "ACTUAL", "consistent"),
        ("TERMINATED", "ACTUAL", "consistent"),
        ("COMPLETED", "ESTIMATED", "conflict"),
        ("TERMINATED", "ESTIMATED", "conflict"),
        ("COMPLETED", None, "not_checkable"),
        (None, "ACTUAL", "not_checkable"),
        (None, None, "not_checkable"),
        ("RECRUITING", "ESTIMATED", "not_applicable"),
        ("WITHDRAWN", "ESTIMATED", "not_applicable"),
        ("UNKNOWN", "ESTIMATED", "not_applicable"),
        ("ACTIVE_NOT_RECRUITING", None, "not_applicable"),
    ],
)
def test_outcomes(status, date_type, expected):
    assert closed_date_actual(status, date_type) == expected


def test_a_missing_type_is_never_a_pass():
    assert closed_date_actual("COMPLETED", None) != "consistent"


def test_an_open_study_is_never_in_conflict():
    for status in ("RECRUITING", "NOT_YET_RECRUITING", "SUSPENDED", "ENROLLING_BY_INVITATION"):
        assert closed_date_actual(status, "ESTIMATED") == "not_applicable"
