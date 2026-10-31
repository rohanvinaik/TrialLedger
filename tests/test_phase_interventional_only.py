"""phase_interventional_only — only interventional studies carry a phase.

Positive: an observational or expanded-access study with a phase other than NA is a conflict; with no
phases, or only NA, it is consistent (the rule is a prohibition, which an absent field satisfies).
Negative: an interventional study is never judged; a missing study type or phases that are not a list are
never consistent.
"""

import pytest

from TrialLedger.checks import phase_interventional_only


@pytest.mark.parametrize(
    "study_type, phases, expected",
    [
        ("OBSERVATIONAL", ["PHASE2"], "conflict"),
        ("OBSERVATIONAL", ["NA", "PHASE3"], "conflict"),
        ("EXPANDED_ACCESS", ["PHASE1"], "conflict"),
        ("OBSERVATIONAL", None, "consistent"),
        ("OBSERVATIONAL", [], "consistent"),
        ("OBSERVATIONAL", ["NA"], "consistent"),
        ("INTERVENTIONAL", ["PHASE2"], "not_applicable"),
        ("INTERVENTIONAL", None, "not_applicable"),
        (None, ["PHASE2"], "not_checkable"),
        ("OBSERVATIONAL", "PHASE2", "not_checkable"),
    ],
)
def test_outcomes(study_type, phases, expected):
    assert phase_interventional_only(study_type, phases) == expected
