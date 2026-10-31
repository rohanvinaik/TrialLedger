"""bounded — a participant count is at most the count that contains it.

Positive: count ≤ bound is consistent, including equality; count > bound is a conflict.
Negative: an absent, boolean, negative or textual count is never consistent and never a conflict.
"""

import pytest

from TrialLedger.checks import bounded


@pytest.mark.parametrize(
    "count, bound, expected",
    [
        (2, 3, "consistent"),
        (3, 3, "consistent"),
        (0, 0, "consistent"),
        (4, 3, "conflict"),
        (None, 3, "not_checkable"),
        (3, None, "not_checkable"),
        (True, 3, "not_checkable"),
        (3, True, "not_checkable"),
        (-1, 3, "not_checkable"),
        ("3", 4, "not_checkable"),
    ],
)
def test_outcomes(count, bound, expected):
    assert bounded(count, bound) == expected
