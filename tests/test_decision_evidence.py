"""Location warrants copied wording, never eligibility or semantic absence."""

from copy import deepcopy

import pytest

from TrialLedger.layer2 import decision_evidence, session_state, source_evidence
from TrialLedger.layer2.service import run


def source():
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {"eligibilityCriteria": "Entry: adults.\nCrossover: ECOG 0–2."},
        }
    }
    return {"study": study, "snapshot": source_evidence.snapshot(study)}


def context(role="quote"):
    held = source()
    return {
        "id": "wording",
        "source": "comparator",
        "role": role,
        "anchor": {
            "id": "wording",
            "address": "/protocolSection/eligibilityModule/eligibilityCriteria",
            "digest": held["snapshot"]["digest"],
            "expected": held["study"]["protocolSection"]["eligibilityModule"]["eligibilityCriteria"],
        },
        "note": "My reading, not a computed entry rule.",
        "scope": "caller-selected crossover passage",
    }


@pytest.mark.parametrize(
    "role,expected",
    [
        ("quote", "source_quote"),
        ("reading", "caller_reading"),
        ("gap", "caller_gap"),
    ],
)
def test_context_role_has_its_own_origin(role, expected):
    assert decision_evidence.role_code(role) == expected


@pytest.mark.parametrize("value", [None, True, {}, [], "confirmed", "known"])
def test_role_cannot_authorize_a_clinical_fact(value):
    assert decision_evidence.role_code(value) == "invalid_context_role"


@pytest.mark.parametrize("role", ["quote", "reading", "gap"])
def test_located_wording_does_not_promote_note_or_scope(role):
    entries = [context(role)]
    saved = deepcopy(entries)
    result = decision_evidence.locate(entries, {"comparator": source()})[0]
    assert entries == saved
    assert result["source_value_standing"] == "known"
    assert result["anchor"]["value"] == entries[0]["anchor"]["expected"]
    assert result["note_standing"] == "proposed"
    assert result["note_origin"] == "caller_supplied_annotation"
    assert "context_only" in result["effect"]
    assert "no population" in result["scope_origin"]
    assert not {"assertion", "clinical_absence", "eligibility"} & result.keys()


@pytest.mark.parametrize("field,value", [("digest", "0" * 64), ("expected", "Adults only.")])
def test_changed_digest_or_value_never_becomes_located(field, value):
    item = context()
    item["anchor"][field] = value
    with pytest.raises(ValueError, match="stale"):
        decision_evidence.locate([item], {"comparator": source()})


def test_span_preserves_exact_source_and_refuses_different_reading():
    item = context("reading")
    item["anchor"]["span"] = {"start": 15, "end": 24, "text": "Crossover"}
    located = decision_evidence.locate([item], {"comparator": source()})[0]
    assert located["anchor"]["span"]["text"] == "Crossover"
    item["anchor"]["span"]["text"] = "Entry"
    with pytest.raises(ValueError, match="stale_span"):
        decision_evidence.locate([item], {"comparator": source()})


@pytest.mark.parametrize("entries", [None, False, {}, [context()] * 33])
def test_malformed_or_oversized_context_is_not_ignored(entries):
    with pytest.raises(ValueError):
        decision_evidence.locate(entries, {"comparator": source()})


def test_unknown_source_and_duplicate_identity_refuse():
    with pytest.raises(ValueError, match="unknown_source"):
        decision_evidence.locate([context()], {})
    with pytest.raises(ValueError, match="duplicate_id"):
        decision_evidence.locate([context(), context()], {"comparator": source()})


def test_legacy_session_identity_does_not_acquire_context_defaults():
    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    original = deepcopy(request["session"])
    prepared = session_state.prepare(original)
    assert prepared["session"] == original
    assert prepared["digest"] == session_state.digest(original)
    assert all(v == [] for v in prepared["decision_evidence"].values())
    assert all("evidence" not in v for v in original["decisions"])
