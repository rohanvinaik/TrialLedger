"""Invalid observation data never becomes an unexplained verified deviation."""

from __future__ import annotations

from enum import IntEnum

import pytest

from TrialLedger.layer2.expectations import STATUSES, deviation_status


@pytest.mark.parametrize(
    ("status", "qualifiers", "audit", "expected"),
    [
        ("explicitly_negated", 0, "", "verified_deviation"),
        ("explicitly_negated", 0, "valid", "verified_deviation"),
        ("explicitly_negated", 1, "valid", "explanation_supported"),
        ("not_documented", 0, "valid", "omission"),
        ("present", 0, "valid", "conforms"),
        ("unresolved", 0, "valid", "scope_unresolved"),
        ("not_applicable", 0, "valid", "not_applicable"),
        ("abc", 1, "abc", "invalid_audit"),
        ("abc", 1, "", "invalid_status"),
        ("explicitly_negated", -1, "valid", "invalid_qualifiers"),
        ("explicitly_negated", True, "valid", "invalid_qualifiers"),
        ("explicitly_negated", False, "valid", "invalid_qualifiers"),
        ("explicitly_negated", 0.0, "valid", "invalid_qualifiers"),
        ("explicitly_negated", "0", "valid", "invalid_qualifiers"),
        ("explicitly_negated", None, "valid", "invalid_qualifiers"),
        ("explicitly_negated", [], "valid", "invalid_qualifiers"),
        ([], 0, "valid", "invalid_status"),
        (None, 0, "valid", "invalid_status"),
        ("explicitly_negated", 0, [], "invalid_audit"),
        ("explicitly_negated", 0, None, "invalid_audit"),
    ],
)
def test_deviation_contract_returns_named_remedies(status, qualifiers, audit, expected):
    assert deviation_status(status, qualifiers, audit) == expected


@pytest.mark.parametrize("status", [*STATUSES, "unknown", None, []])
def test_invalid_audit_preserves_invalid_extraction_override(status):
    assert deviation_status(status, 0, "invalid") == "invalid_extraction"


class QualifierCount(IntEnum):
    NONE = 0


def test_exact_integer_qualifier_contract_refuses_int_enum():
    assert deviation_status("explicitly_negated", QualifierCount.NONE, "valid") == "invalid_qualifiers"


@pytest.mark.parametrize("status", STATUSES)
def test_malformed_qualifier_is_not_ignored_for_other_valid_statuses(status):
    assert deviation_status(status, -1, "valid") == "invalid_qualifiers"


@pytest.mark.parametrize("qualifiers", [-1, True, None, [], "0"])
def test_invalid_extraction_override_does_not_certify_malformed_observation(qualifiers):
    assert deviation_status("unknown", qualifiers, "invalid") == "invalid_extraction"
