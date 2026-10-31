"""member — a cross-reference names something the same record defines.

Positive: an exact match is consistent; anything else is a conflict, even a case variant.
Negative: an absent reference is never consistent and never a conflict.
"""

import pytest

from TrialLedger.checks import member


@pytest.mark.parametrize(
    "value, defined, expected",
    [
        ("Drug: Aspirin", ["Drug: Aspirin", "Drug: Placebo"], "consistent"),
        ("Drug: Ibuprofen", ["Drug: Aspirin"], "conflict"),
        ("drug: aspirin", ["Drug: Aspirin"], "conflict"),
        ("EG000", [], "conflict"),
        (None, ["EG000"], "not_checkable"),
    ],
)
def test_outcomes(value, defined, expected):
    assert member(value, defined) == expected
