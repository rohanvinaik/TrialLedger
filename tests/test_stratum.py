"""A trial's setting stratum rests on the known setting only.

Positive: a setting the record and the approved relations leave as one value is the stratum.
Negative: a setting that only a proposed relation narrows to one value is never a stratum; it is
"setting unresolved".
"""

from TrialLedger.design import _stratum


def view(domain, with_proposed):
    return {"coordinates": {"setting": {"domain": domain, "with_proposed": with_proposed}}}


def test_a_known_setting_is_the_stratum():
    assert _stratum(view(("adjuvant",), ("adjuvant",))) == "adjuvant"


def test_a_setting_only_a_proposed_relation_narrows_is_unresolved():
    assert _stratum(view(("adjuvant", "perioperative"), ("adjuvant",))) == "setting unresolved"
