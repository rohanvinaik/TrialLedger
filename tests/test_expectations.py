"""Conditional rarity and deviation logic on explicitly supplied observation states."""

import math

import pytest

from TrialLedger.layer2.expectations import FROZEN, conditional_rarity, deviation_status


@pytest.mark.parametrize(
    "status, qualifiers, audit, expected",
    [
        ("present", 0, "", "conforms"),
        ("present", 2, "invalid", "invalid_extraction"),
        ("explicitly_negated", 1, "", "explanation_supported"),
        ("explicitly_negated", 0, "", "verified_deviation"),
        ("not_documented", 0, "", "omission"),
        ("unresolved", 0, "", "scope_unresolved"),
        ("not_applicable", 0, "", "not_applicable"),
    ],
)
def test_deviation_status(status, qualifiers, audit, expected):
    assert deviation_status(status, qualifiers, audit) == expected


def test_rarity_in_a_supported_cell():
    observations = [("first_line", "present")] * 9 + [("first_line", "not_documented")] + [("x", "present")]
    source, share, n, present_bits, absent_bits = conditional_rarity(observations, "first_line", 10)
    assert (source, share, n) == ("cell", 0.9, 10)
    assert present_bits == round(-math.log2(0.9), 3) and absent_bits == round(-math.log2(0.1), 3)


def test_rarity_falls_back_to_the_parent_and_abstains_when_neither_is_supported():
    observations = [("a", "present")] * 3 + [("b", "present")] * 7 + [("b", "explicitly_negated")]
    assert conditional_rarity(observations, "a", 10)[:3] == ("parent", 0.9091, 11)
    assert conditional_rarity(observations[:5], "a", 10) == ("abstain", None, 3, None, None)


def test_unresolved_and_not_applicable_never_count():
    observations = [("c", "present")] * 10 + [("c", "unresolved")] * 5 + [("c", "not_applicable")] * 5
    assert conditional_rarity(observations, "c", 10)[:3] == ("cell", 1.0, 10)
    assert conditional_rarity(observations, "c", 10)[4] is None  # absence never observed: no finite rarity


def test_the_frozen_expectation_records_its_provenance():
    (expectation,) = FROZEN
    assert expectation.provenance.startswith("prior:")
    assert "Programmed Death Receptor-1 Blocking Antibody" in expectation.applies_to
