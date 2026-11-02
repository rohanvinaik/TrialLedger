"""A trial's setting stratum rests on the known setting only (add-scoped-reasoning, Decision 7).

Positive: a setting stated evidence and strict relations leave as one value is the stratum.
Negative: a setting that only a default (interpolated) or a proposal narrows to one value is never a stratum;
it is "setting unresolved".
"""

from TrialLedger.design import _stratum


def view(known, interpolated, proposed=()):
    row = {"domain": known, "interpolated": {"domain": interpolated}}
    row["proposals"] = [{"relation": "p", "domain": proposed}] if proposed else []
    return {"coordinates": {"setting": row}}


def test_a_known_setting_is_the_stratum():
    assert _stratum(view(("adjuvant",), ("adjuvant",))) == "adjuvant"


def test_a_setting_only_a_default_or_a_proposal_narrows_is_unresolved():
    assert _stratum(view(("adjuvant", "maintenance"), ("maintenance",))) == "setting unresolved"
    assert _stratum(view(("adjuvant", "perioperative"), ("adjuvant", "perioperative"), ("adjuvant",))) == (
        "setting unresolved"
    )
