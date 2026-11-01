"""Provenance — every rule, vocabulary and threshold says where it came from.

Positive: every bank, relation, frozen expectation, eligibility-coverage marker pattern and named threshold
has an entry with an origin of "external", "prior" or "derived"; the abbreviation pattern is derived from the
NSCLC development data and the completeness pattern is prior.
Negative: a bank, relation, expectation or marker pattern added without an entry fails here; no entry names an
origin outside the three; no marker pattern claims an external source.
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
        "pattern:eligibility_abbreviated",
        "pattern:eligibility_complete",
    }
    expected |= {
        f"threshold:{name}" for name in ("STANDARD_SHARE", "SIGNAL_MIN_TRIALS", "SIGNAL_MIN_SPONSORS")
    }
    assert expected <= set(PROVENANCE)


def test_the_coverage_marker_patterns_say_where_they_came_from():
    assert PROVENANCE["pattern:eligibility_abbreviated"][1].startswith(
        "derived: 487 interventional Phase 3 NSCLC"
    )
    assert PROVENANCE["pattern:eligibility_complete"][1].startswith("prior")
    # neither pattern is passed off as external or as confirmed by the population it was written against
    assert not any(
        PROVENANCE[key][1].startswith("external") for key in PROVENANCE if key.startswith("pattern:")
    )


def test_every_origin_is_one_of_three():
    assert {origin.split(":")[0] for _, origin, _ in PROVENANCE.values()} <= {"external", "prior", "derived"}
