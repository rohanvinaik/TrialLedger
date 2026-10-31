"""combine — one record-level outcome from a check's entries.

Positive: any conflict makes a conflict; otherwise any uncheckable entry makes the whole not checkable;
otherwise any consistent entry makes it consistent.
Negative: no entries, or only inapplicable ones, are never called consistent.
"""

import pytest

from TrialLedger.checks import combine


@pytest.mark.parametrize(
    "outcomes, expected",
    [
        (["conflict", "not_checkable", "consistent"], "conflict"),
        (["consistent", "conflict"], "conflict"),
        (["consistent", "not_checkable"], "not_checkable"),
        (["consistent", "consistent"], "consistent"),
        (["not_applicable", "consistent"], "consistent"),
        (["not_applicable"], "not_applicable"),
        ([], "not_applicable"),
    ],
)
def test_outcomes(outcomes, expected):
    assert combine(outcomes) == expected
