"""Provenance — every rule, vocabulary and threshold says where it came from.

Positive: every bank, relation, frozen expectation and named threshold has an entry with an origin of
"external", "prior" or "derived".
Negative: a bank, relation or expectation added without an entry fails here; no entry names an origin outside
the three.
"""

from TrialLedger.banks import BANKS
from TrialLedger.coherence import RELATIONS
from TrialLedger.expectations import FROZEN
from TrialLedger.provenance import PROVENANCE


def test_every_rule_has_provenance():
    expected = {f"bank:{name}" for name in BANKS}
    expected |= {f"relation:{relation.id}" for relation in RELATIONS}
    expected |= {f"expectation:{expectation.id}" for expectation in FROZEN}
    expected |= {
        "bank:endpoints",
        "bank:stated_targets",
        "itemize",
        "classes:rxclass",
        "representation:near_miss",
    }
    expected |= {
        f"threshold:{name}" for name in ("STANDARD_SHARE", "SIGNAL_MIN_TRIALS", "SIGNAL_MIN_SPONSORS")
    }
    assert expected <= set(PROVENANCE)


def test_every_origin_is_one_of_three():
    assert {origin.split(":")[0] for _, origin, _ in PROVENANCE.values()} <= {"external", "prior", "derived"}
