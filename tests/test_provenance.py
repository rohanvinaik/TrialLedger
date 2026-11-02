"""Retained symbolic rules and concept definitions keep their stated provenance."""

from TrialLedger.layer2.coherence import RELATIONS
from TrialLedger.layer2.expectations import FROZEN
from TrialLedger.layer2.provenance import (
    CONCEPT_AUTHORITIES,
    DEVELOPMENT_POPULATIONS,
    LICENCE_STATUSES,
    PROVENANCE,
    RULE_EXPOSURE,
)


def test_every_retained_rule_has_provenance():
    expected = {f"relation:{r.id}" for r in RELATIONS} | {f"expectation:{e.id}" for e in FROZEN}
    expected |= {"classes:rxclass", "representation:near_miss", "fragment:nsclc_legacy"}
    expected |= {
        f"threshold:{name}" for name in ("STANDARD_SHARE", "SIGNAL_MIN_TRIALS", "SIGNAL_MIN_SPONSORS")
    }
    assert expected <= set(PROVENANCE)
    assert not any(key.startswith(("bank:", "gate:", "pattern:")) for key in PROVENANCE)


def test_origins_and_authority_limits_remain_explicit():
    assert {origin.split(":")[0] for _, origin, _ in PROVENANCE.values()} <= {"external", "prior", "derived"}
    assert {licence for _, _, licence, _ in CONCEPT_AUTHORITIES.values()} <= set(LICENCE_STATUSES)
    assert CONCEPT_AUTHORITIES["local"][1] is None and CONCEPT_AUTHORITIES["ajcc"][1] is None
    assert CONCEPT_AUTHORITIES["snomedct"][2] == "licence_required"
    assert CONCEPT_AUTHORITIES["dsm"][2] == CONCEPT_AUTHORITIES["ajcc"][2] == "words_only"


def test_concept_development_exposure_never_becomes_confirmation():
    assert set(RULE_EXPOSURE) == {"fragment:nsclc_legacy"}
    assert set(RULE_EXPOSURE) <= set(PROVENANCE)
    for key, (populations, _frozen, confirmed_on) in RULE_EXPOSURE.items():
        assert populations and set(populations) <= set(DEVELOPMENT_POPULATIONS), key
        assert not set(confirmed_on) & set(populations), key
