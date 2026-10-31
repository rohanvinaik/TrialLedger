"""dates_ordered — a date that must come first does, reading partial dates as intervals.

Positive: certainly in order (equal days included) is consistent; certainly out of order is a conflict.
Negative: overlapping intervals (the same month, a day inside a month) are never judged either way; an
absent or unparseable date is never consistent.
"""

import pytest

from TrialLedger.checks import dates_ordered


@pytest.mark.parametrize(
    "earlier, later, expected",
    [
        ("2020-01-15", "2020-06-01", "consistent"),
        ("2020-05-01", "2020-05-01", "consistent"),
        ("2020-05", "2020-06", "consistent"),
        ("2020", "2021-01", "consistent"),
        ("2020-04-30", "2020-05", "consistent"),
        ("2020-06-01", "2020-01-15", "conflict"),
        ("2020-06", "2020-05-31", "conflict"),
        ("2021", "2020-12", "conflict"),
        ("2020-05", "2020-05", "not_checkable"),
        ("2020-05-31", "2020-05", "not_checkable"),
        ("2020", "2020-06-01", "not_checkable"),
        (None, "2020-05", "not_checkable"),
        ("2020-05", None, "not_checkable"),
        ("bad", "2020", "not_checkable"),
    ],
)
def test_outcomes(earlier, later, expected):
    assert dates_ordered(earlier, later) == expected
