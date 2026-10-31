"""age_limits_ordered — the minimum age is at most the maximum age.

Positive: within a family that converts exactly, minimum ≤ maximum is consistent, and minimum > maximum a
conflict (2 Years exceeds 18 Months).
Negative: units with no exact conversion (months against days) are never judged; an absent limit, which may
mean "no limit", is never taken as one.
"""

import pytest

from TrialLedger.checks import age_limits_ordered


@pytest.mark.parametrize(
    "minimum, maximum, expected",
    [
        ("18 Years", "65 Years", "consistent"),
        ("18 Years", "18 Years", "consistent"),
        ("6 Months", "1 Year", "consistent"),
        ("28 Days", "4 Weeks", "consistent"),
        ("65 Years", "18 Years", "conflict"),
        ("2 Years", "18 Months", "conflict"),
        ("2 Weeks", "13 Days", "conflict"),
        ("1 Month", "30 Days", "not_checkable"),
        ("1 Year", "400 Days", "not_checkable"),
        (None, "65 Years", "not_checkable"),
        ("18 Years", None, "not_checkable"),
        ("eighteen", "65 Years", "not_checkable"),
    ],
)
def test_outcomes(minimum, maximum, expected):
    assert age_limits_ordered(minimum, maximum) == expected
