"""recruiting_site_recruiting_study — a multi-site study with a recruiting site is itself recruiting.

Positive: two or more sites, one RECRUITING: the study RECRUITING is consistent, anything else a conflict.
Negative: a single site is never judged (the rule names multi-site studies); an overall status the registry
assigned (UNKNOWN, WITHHELD) is never judged against the responsible party's rule; an unreported site status
with no recruiting site reported is never taken as "not recruiting".
"""

import pytest

from TrialLedger.checks import recruiting_site_recruiting_study


@pytest.mark.parametrize(
    "overall, sites, expected",
    [
        ("RECRUITING", ["RECRUITING", "COMPLETED"], "consistent"),
        ("ACTIVE_NOT_RECRUITING", ["RECRUITING", "COMPLETED"], "conflict"),
        ("COMPLETED", ["RECRUITING", "RECRUITING"], "conflict"),
        ("COMPLETED", ["COMPLETED", "COMPLETED"], "not_applicable"),
        ("COMPLETED", ["COMPLETED", None], "not_checkable"),
        ("RECRUITING", ["RECRUITING"], "not_applicable"),
        ("COMPLETED", [], "not_applicable"),
        ("UNKNOWN", ["RECRUITING", "RECRUITING"], "not_checkable"),
        ("WITHHELD", ["RECRUITING", "RECRUITING"], "not_checkable"),
        (None, ["RECRUITING", "RECRUITING"], "not_checkable"),
    ],
)
def test_outcomes(overall, sites, expected):
    assert recruiting_site_recruiting_study(overall, sites) == expected
