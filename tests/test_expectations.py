"""Expectations — observation status, conditional rarity and deviation status, with the falsifier set.

The falsifier (add-design-surprise 1.2): an explicit exclusion, a qualified exception, an omission,
unresolved text and conflicting cohort scopes, each read to its status; then the two properties the
design must keep: a valid unexplained exception survives as a verified deviation, and an omission is
never permission.

Positive: an exclusion naming autoimmune disease (or a named autoimmune disease) is present, its
exceptions kept; an inclusion that admits it is explicitly negated, its conditions kept; a negated or
"are excluded" inclusion is present; rarity is −log2 of the cell's share with the cell's size, falling
back to the parent and saying so.
Negative: an omission is never "admitted" (not_documented, a verified deviation, never explanation
supported); unsectioned text and disagreeing cohorts are never resolved; unresolved observations never
enter a count; a sparse cell never reports a rarity; a valid unexplained exception is never noise.
"""

import math

import pytest

from TrialLedger.expectations import (
    FROZEN,
    autoimmune_exclusion,
    conditional_rarity,
    deviation_status,
)

EXPLICIT = [
    ("exclusion", "* Active autoimmune disease that has required systemic treatment in the past 2 years")
]
QUALIFIED = [
    (
        "exclusion",
        "* Active or prior documented autoimmune disease, except vitiligo, type 1 diabetes or hypothyroidism "
        "on stable hormone replacement",
    )
]
OMISSION = [("inclusion", "* ECOG 0-1"), ("exclusion", "* Pregnancy")]
UNRESOLVED = [("unsectioned", "Patients with autoimmune disease")]
CONFLICTING = [
    ("exclusion", "* Cohort A: active autoimmune disease"),
    ("inclusion", "* Cohort B: patients with autoimmune disease are eligible"),
]
ADMITTED_IF = [
    ("inclusion", "* Patients with rheumatoid arthritis are eligible if controlled on stable therapy")
]
ADMITTED = [("inclusion", "* Patients with a history of autoimmune disease")]


@pytest.mark.parametrize(
    "pieces, status, reason",
    [
        (EXPLICIT, "present", "excluded"),
        (QUALIFIED, "present", "excluded"),
        (OMISSION, "not_documented", "not_named"),
        (UNRESOLVED, "unresolved", "unsectioned_mention"),
        (CONFLICTING, "unresolved", "conflicting_scopes"),
        (ADMITTED_IF, "explicitly_negated", "admitted"),
        (ADMITTED, "explicitly_negated", "admitted"),
        ([("inclusion", "* No history of autoimmune disease")], "present", "excluded"),
        ([("inclusion", "* Patients with lupus are excluded")], "present", "excluded"),
        ([("exclusion", "* Crohn's disease or ulcerative colitis")], "present", "excluded"),
    ],
)
def test_observation_status(pieces, status, reason):
    assert autoimmune_exclusion(pieces)[:2] == (status, reason)


def test_exceptions_and_conditions_are_kept_as_written():
    assert autoimmune_exclusion(QUALIFIED)[3] == [
        "except vitiligo, type 1 diabetes or hypothyroidism on stable hormone replacement"
    ]
    assert autoimmune_exclusion(ADMITTED_IF)[3] == ["if controlled on stable therapy"]


def test_an_omission_is_never_permission():
    status = autoimmune_exclusion(OMISSION)[0]
    assert status == "not_documented" and status != "explicitly_negated"
    assert deviation_status(status, 0, "") == "omission"


def test_an_abbreviated_record_says_less_by_its_silence():
    pieces = [("exclusion", "Key Exclusion Criteria:"), ("exclusion", "* Pregnancy")]
    assert autoimmune_exclusion(pieces)[:2] == ("unresolved", "abbreviated_criteria")
    note = [
        ("exclusion", "* Pregnancy"),
        ("exclusion", "Other protocol-defined exclusion criteria may apply"),
    ]
    assert autoimmune_exclusion(note)[:2] == ("unresolved", "abbreviated_criteria")


def test_a_valid_unexplained_exception_survives():
    status, _, _, qualifiers = autoimmune_exclusion(ADMITTED)
    assert deviation_status(status, len(qualifiers), "") == "verified_deviation"


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


@pytest.mark.parametrize(
    "text",
    [
        # real exclusion criteria (Phase 3 NSCLC, 2015-2024) whose permissive sentence is an exception
        "* Active autoimmune disease that has required systemic treatment in the past 2 years. Replacement "
        "therapy (eg, thyroxine, insulin, or physiologic corticosteroid) is allowed.",
        "12. Active or known or suspected autoimmune disease (subjects with Type 1 diabetes mellitus, "
        "hypothyroidism only requiring hormone replacement, or skin disorders (vitiligo, psoriasis, or "
        "alopecia) not requiring systemic treatment are permitted to enroll).",
    ],
)
def test_an_exclusion_with_a_permitted_exception_is_present(text):
    status, reason, cited, qualifiers = autoimmune_exclusion([("exclusion", text)])
    assert (status, reason, cited) == ("present", "excluded", [0])
    assert qualifiers and deviation_status(status, len(qualifiers), "") == "conforms"


def test_two_exclusions_never_conflict():
    pieces = [
        ("exclusion", "9. Active or prior documented inflammatory bowel disease (e.g. Crohn's disease)."),
        ("exclusion", "8. Active autoimmune disease. NOTE: Patients with vitiligo are eligible."),
    ]
    assert autoimmune_exclusion(pieces)[:2] == ("present", "excluded")


def test_a_negation_reaches_across_an_example_list():
    text = (
        "* Patients must not have significant gastrointestinal disorders with diarrhea as a major symptom "
        "(e.g., Crohn's disease, malabsorption, etc.)"
    )
    assert autoimmune_exclusion([("inclusion", text)])[:2] == ("present", "excluded")
