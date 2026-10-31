"""reasons_account — reasons for non-completion account for every participant not completed.

Positive: reasons summing to the number not completed are consistent; otherwise a conflict.
Negative: with no reasons there is nothing to judge; a reason or total that is not a whole number is never
consistent.
"""

import pytest

from TrialLedger.checks import reasons_account


@pytest.mark.parametrize(
    "not_completed, reasons, expected",
    [
        (5, [2, 3], "consistent"),
        (0, [0], "consistent"),
        (5, [2, 2], "conflict"),
        (3, [2, 2], "conflict"),
        (5, [], "not_applicable"),
        (None, [1], "not_checkable"),
        (5, [2, None], "not_checkable"),
        (5, [True, 4], "not_checkable"),
        (-1, [1], "not_checkable"),
    ],
)
def test_outcomes(not_completed, reasons, expected):
    assert reasons_account(not_completed, reasons) == expected
