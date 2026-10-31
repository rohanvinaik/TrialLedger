"""results_flag_first_submit — hasResults is Present(ResultsFirstSubmitDate), as the registry defines it.

Positive: the flag agreeing with the date's presence is consistent; disagreeing, a conflict.
Negative: a flag that is absent or not a boolean (including the string "true") is never consistent.
"""

import pytest

from TrialLedger.checks import results_flag_first_submit


@pytest.mark.parametrize(
    "flag, present, expected",
    [
        (True, True, "consistent"),
        (False, False, "consistent"),
        (True, False, "conflict"),
        (False, True, "conflict"),
        (None, True, "not_checkable"),
        (None, False, "not_checkable"),
        ("true", True, "not_checkable"),
        (1, True, "not_checkable"),
    ],
)
def test_outcomes(flag, present, expected):
    assert results_flag_first_submit(flag, present) == expected
