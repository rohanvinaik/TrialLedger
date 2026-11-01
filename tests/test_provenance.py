"""Provenance — every rule, vocabulary and threshold says where it came from.

Positive: every bank, relation, frozen expectation, eligibility-coverage marker pattern and named threshold
has an entry with an origin of "external", "prior" or "derived"; the abbreviation pattern is derived from the
NSCLC development data and the completeness pattern is prior.
Negative: a bank, relation, expectation or marker pattern added without an entry fails here; no entry names an
origin outside the three; no marker pattern claims an external source.

Concept provenance apart from rule provenance (add-bank-coverage Decision 5, B4, B5).
Positive: B5's open authorities come first in the concept-authority table, open (or open under accepted
terms); every derived bank and the pilot's gate have an exposure record naming the populations they were
written against, every existing bank and the gate naming the pilot (its audit read every bank's atoms); every
exposure record is a rule with an origin, the seed fragment's derived from both populations.
Negative: no licence status outside the five; SNOMED CT is not usable without a licence; DSM and AJCC are
words only; no exposure names an unknown population or lacks an origin, and no rule is confirmed on a
population that informed it; no bank omits the pilot; no edition is invented (the local namespace has none,
and AJCC none: its 8th edition is named in bank:setting's note and two relations' origins, never pinned from
its source).
"""

from TrialLedger.banks import BANKS
from TrialLedger.coherence import RELATIONS
from TrialLedger.expectations import FROZEN
from TrialLedger.provenance import (
    CONCEPT_AUTHORITIES,
    DEVELOPMENT_POPULATIONS,
    LICENCE_STATUSES,
    PROVENANCE,
    RULE_EXPOSURE,
)


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


def test_the_open_authorities_come_first():
    open_ones = ("loinc", "ucum", "rxnorm", "rxclass", "mesh", "ncit", "hgnc", "hgvs", "icd10cm", "icd11")
    for authority in open_ones:
        assert CONCEPT_AUTHORITIES[authority][2] in ("open", "open_with_terms"), authority
    assert list(CONCEPT_AUTHORITIES)[: len(open_ones)] == list(open_ones)
    assert CONCEPT_AUTHORITIES["snomedct"][2] == "licence_required"
    assert CONCEPT_AUTHORITIES["dsm"][2] == CONCEPT_AUTHORITIES["ajcc"][2] == "words_only"
    assert {licence for _, _, licence, _ in CONCEPT_AUTHORITIES.values()} <= set(LICENCE_STATUSES)
    assert CONCEPT_AUTHORITIES["local"][1] is None and CONCEPT_AUTHORITIES["ajcc"][1] is None


def test_every_derived_rule_records_its_exposure():
    derived = {key for key, (_, origin, _) in PROVENANCE.items() if origin.startswith("derived")}
    banks_and_gates = {key for key in derived if key.startswith(("bank:", "gate:"))}
    assert banks_and_gates <= set(RULE_EXPOSURE)
    assert "fragment:nsclc_legacy" in RULE_EXPOSURE
    assert set(RULE_EXPOSURE) <= set(PROVENANCE)  # every exposure is of a rule with an origin
    assert PROVENANCE["fragment:nsclc_legacy"][1].startswith("derived")
    assert "pilot" in PROVENANCE["fragment:nsclc_legacy"][1]
    # the pilot's audit (2026-10-31/11-01) read every existing bank's atoms, the typing banks and the others
    banks = {f"bank:{bank}" for bank in BANKS} | {key for key in RULE_EXPOSURE if key.startswith("bank:")}
    assert {"bank:endpoints", "bank:stated_targets"} < banks
    for bank in banks:
        assert RULE_EXPOSURE[bank][0] == ("nsclc_phase3_2015_2024", "pilot_2026_10_31"), bank
    assert "11-01" in DEVELOPMENT_POPULATIONS["pilot_2026_10_31"]
    assert RULE_EXPOSURE["gate:mention_value"][0] == ("pilot_2026_10_31",)
    for key, (populations, _frozen, confirmed_on) in RULE_EXPOSURE.items():
        assert populations and set(populations) <= set(DEVELOPMENT_POPULATIONS), key
        assert not set(confirmed_on) & set(populations), key  # B4: what informed a rule never confirms it
