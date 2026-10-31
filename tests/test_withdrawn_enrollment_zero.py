"""withdrawn_enrollment_zero — a withdrawn study enrolled nobody.

Positive: WITHDRAWN with ACTUAL enrollment 0 is consistent; above 0, a conflict.
Negative: an estimated count (a target) is never judged; a missing type or count is never consistent; a
boolean or negative count is not a count.
"""

import pytest

from TrialLedger.checks import withdrawn_enrollment_zero


@pytest.mark.parametrize(
    "status, enrollment_type, count, expected",
    [
        ("WITHDRAWN", "ACTUAL", 0, "consistent"),
        ("WITHDRAWN", "ACTUAL", 3, "conflict"),
        ("WITHDRAWN", "ESTIMATED", 50, "not_applicable"),
        ("WITHDRAWN", None, 0, "not_checkable"),
        ("WITHDRAWN", "ACTUAL", None, "not_checkable"),
        ("WITHDRAWN", "ACTUAL", True, "not_checkable"),
        ("WITHDRAWN", "ACTUAL", False, "not_checkable"),
        ("WITHDRAWN", "ACTUAL", -1, "not_checkable"),
        ("WITHDRAWN", "ACTUAL", "0", "not_checkable"),
        ("COMPLETED", "ACTUAL", 5, "not_applicable"),
        (None, "ACTUAL", 0, "not_checkable"),
    ],
)
def test_outcomes(status, enrollment_type, count, expected):
    assert withdrawn_enrollment_zero(status, enrollment_type, count) == expected


def test_a_target_is_never_a_conflict():
    assert withdrawn_enrollment_zero("WITHDRAWN", "ESTIMATED", 400) != "conflict"
