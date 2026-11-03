"""Authored positive and MUST-NOT intents: documentary floors never become clinical ceilings.

Exact source selections locate values; accepted meaning, same scope and the caller's
ceiling are separate premises. In particular, global deviations do not prove local ones.
"""

import copy
import dataclasses
import json

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2.exception_bounds import (
    apply,
    attribution_state,
    extent_transfer,
    interval_state,
    prepare,
)
from TrialLedger.layer2.source_evidence import snapshot


def profile(key="PS2"):
    return json.loads(
        a.canonical(
            a.Literal(
                a.Subject("participant"),
                a.Predicate("defined_term", key),
                a.Value("boolean", "eq"),
            )
        )
    )


@pytest.fixture
def evidence():
    study = {
        "protocolSection": {"identificationModule": {"nctId": "NCT00322452"}},
        "deviations": {
            "count": "1",
            "category": "protocol deviation",
            "denominator": "100",
        },
        "documentary_context": {"group": "local-G1", "period": "enrollment"},
    }
    identity = snapshot(study)
    scope = {
        "study": identity["study_ref"],
        "population": "randomized",
        "arm": "all",
        "time": "enrollment",
        "version": identity["digest"],
    }
    raw = {
        "sources": [{"id": "registry", "study": study, "digest": identity["digest"]}],
        "observations": [
            {
                "id": "reported",
                "source": "registry",
                "scope": copy.deepcopy(scope),
                "context": [
                    {"id": name, "address": "/documentary_context/" + name, "expected": value}
                    for name, value in study["documentary_context"].items()
                ],
                **{
                    key: {"address": "/deviations/" + key, "expected": value}
                    for key, value in study["deviations"].items()
                },
            }
        ],
        "bindings": [
            {
                "id": "meaning",
                "observation": "reported",
                "scope": copy.deepcopy(scope),
                "extent": "population",
                "possible_targets": ["entry_eligibility"],
                "profile": None,
                "status": "known",
                "resolution": "resolved",
                "basis": [
                    "Accepted: distinct randomized participants with eligibility deviations at enrollment."
                ],
                "rule": {"id": "person-confirmed-meaning", "version": "1"},
            }
        ],
    }
    reference = {
        "bindings": ["meaning"],
        "scope": copy.deepcopy(scope),
        "extent": "population",
        "profile": None,
    }
    return raw, reference, identity["study_ref"]


def test_interval_positive_lower_and_zero_ceiling_conflict():
    assert interval_state(1, 0, 100) == "ceiling_conflict"


def test_interval_must_not_make_unknown_ceiling_zero():
    assert interval_state(1, None, 100) == "unknown_ceiling"


def test_interval_structural_maximum_is_independent_of_informative_ceiling():
    assert interval_state(101, None, 100) == "structural_maximum_conflict"
    assert interval_state(101, 200, 100) == "structural_maximum_conflict"


def test_interval_boundary_is_consistent_and_must_not_conflict_on_equality():
    assert interval_state(1, 1, 100) == "consistent"
    assert interval_state(0, 0, 0) == "consistent"


def test_extent_population_floor_transfers_to_population():
    assert extent_transfer("population", "population", False) == "population_floor"


def test_extent_must_not_transfer_global_floor_into_profile():
    assert extent_transfer("population", "profile", True) == "no_local_floor"
    assert extent_transfer("population", "profile", False) == "no_local_floor"


def test_extent_profile_floor_transfers_to_same_profile_and_global():
    assert extent_transfer("profile", "profile", True) == "profile_floor"
    assert extent_transfer("profile", "population", False) == "population_floor"


def test_extent_must_not_transfer_between_different_profiles():
    assert extent_transfer("profile", "profile", False) == "profile_mismatch"


def test_known_global_floor_conflicts_with_global_zero_cap(evidence):
    raw, ref, study = evidence
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "conflict"
    assert result["check"]["lower"] == 1
    assert result["check"]["upper"] == 0
    assert result["check"]["structural_maximum"] == 100
    assert result["status"] == "known"


def test_global_floor_must_not_conflict_with_profile_zero_cap(evidence):
    raw, ref, study = evidence
    ref.update(extent="profile", profile=profile())
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "consistent"
    assert result["check"]["lower"] == 0
    assert result["check"]["contributions"][0]["transfer"] == "no_local_floor"
    assert result["blockers"] == []


def test_profile_floor_can_conflict_with_same_scope_global_cap(evidence):
    raw, ref, study = evidence
    raw["bindings"][0].update(extent="profile", profile=profile())
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "conflict"
    assert result["check"]["contributions"][0]["transfer"] == "population_floor"


def test_profile_floor_same_profile_is_useful(evidence):
    raw, ref, study = evidence
    raw["bindings"][0].update(extent="profile", profile=profile())
    ref.update(extent="profile", profile=profile())
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "conflict"


def test_different_profile_must_not_supply_a_local_floor(evidence):
    raw, ref, study = evidence
    raw["bindings"][0].update(extent="profile", profile=profile("PS3"))
    ref.update(extent="profile", profile=profile())
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "unresolved"
    assert result["check"]["lower"] == 0
    assert "profile_mismatch:meaning" in result["blockers"]


@pytest.mark.parametrize(
    "status,resolution,blocker",
    [
        ("proposed", "resolved", "binding_proposed"),
        ("known", "unresolved", "binding_unresolved"),
        ("interpolated", "conflicting", "binding_unresolved"),
    ],
)
def test_unaccepted_meaning_must_not_eliminate_but_keeps_conditional_arithmetic(
    evidence, status, resolution, blocker
):
    raw, ref, study = evidence
    raw["bindings"][0].update(status=status, resolution=resolution)
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "unresolved"
    assert result["check"]["lower"] == 0
    assert result["check"]["conditional_lower"] == 1
    assert blocker + ":meaning" in result["blockers"]


def test_interpolated_resolved_meaning_contributes_without_promotion(evidence):
    raw, ref, study = evidence
    raw["bindings"][0]["status"] = "interpolated"
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "conflict"
    assert result["status"] == "interpolated"


@pytest.mark.parametrize(
    "status,resolution,blocker",
    [
        ("proposed", "resolved", "bridge_proposed"),
        ("known", "unresolved", "bridge_unresolved"),
    ],
)
def test_bridge_admission_is_independent_of_documentary_location(evidence, status, resolution, blocker):
    raw, ref, study = evidence
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, status, resolution)
    assert result["check"]["code"] == "unresolved"
    assert blocker + ":meaning" in result["blockers"]


def test_multiple_floors_must_be_maximum_never_sum(evidence):
    raw, ref, study = evidence
    second = copy.deepcopy(raw["bindings"][0])
    second["id"] = "second-meaning"
    raw["bindings"].append(second)
    ref["bindings"].append("second-meaning")
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 1, "known", "resolved")
    assert result["check"]["code"] == "consistent"
    assert result["check"]["lower"] == 1
    assert len(result["check"]["contributions"]) == 2


def test_count_must_not_become_informative_upper_bound(evidence):
    raw, ref, study = evidence
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 80, "known", "resolved")
    assert result["check"]["upper"] == 80
    assert result["check"]["structural_maximum"] == 100
    assert result["effective_cap"] == 80


@pytest.mark.parametrize(
    "target,field,value",
    [
        ("observation", "arm", "other"),
        ("binding", "time", "followup"),
        ("reference", "version", "other"),
        ("observation", "study", "abstract-trial-label"),
    ],
)
def test_scope_mismatch_is_named_unresolved_not_clinical_refutation(evidence, target, field, value):
    raw, ref, study = evidence
    row = (
        raw["observations"][0]
        if target == "observation"
        else raw["bindings"][0]
        if target == "binding"
        else ref
    )
    row["scope"][field] = value
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "unresolved"
    assert result["check"]["lower"] == 0
    assert result["blockers"]


def test_wrong_top_study_identity_must_not_rename_real_record(evidence):
    raw, ref, _ = evidence
    result = apply(prepare(raw, "IPASS"), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "unresolved"
    assert "source_study_mismatch:meaning" in result["blockers"]


@pytest.mark.parametrize(
    "population,denominator,blocker",
    [
        ("safety", 100, "population_mismatch"),
        ("randomized", 99, "denominator_mismatch"),
    ],
)
def test_equal_names_or_counts_must_not_join_different_populations(
    evidence, population, denominator, blocker
):
    raw, ref, study = evidence
    result = apply(
        prepare(raw, study),
        ref,
        population,
        denominator,
        profile(),
        0,
        "known",
        "resolved",
    )
    assert result["check"]["code"] == "unresolved"
    assert blocker + ":meaning" in result["blockers"]


def test_source_values_and_meaning_evidence_are_retained_independently(evidence):
    raw, ref, study = evidence
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 1, "known", "resolved")
    contribution = result["check"]["contributions"][0]
    assert [row["value"] for row in contribution["located"]] == [
        "1",
        "protocol deviation",
        "100",
        "local-G1",
        "enrollment",
    ]
    assert all(row["code"] == "located" for row in contribution["located"])
    assert contribution["meaning_rule"] == raw["bindings"][0]["rule"]
    assert raw["bindings"][0]["basis"][0] in result["basis"]
    assert len(result["basis"]) == 6


def test_prepared_bundle_and_returned_values_must_not_alias_inputs(evidence):
    raw, ref, study = evidence
    bundle = prepare(raw, study)
    raw["bindings"][0]["basis"].append("later")
    raw["observations"][0]["scope"]["population"] = "changed"
    raw["sources"][0]["study"]["deviations"]["count"] = "99"
    first = apply(bundle, ref, "randomized", 100, profile(), 1, "known", "resolved")
    first["check"]["contributions"][0]["located"][0]["value"] = "changed"
    second = apply(bundle, ref, "randomized", 100, profile(), 1, "known", "resolved")
    assert second["check"]["lower"] == 1
    assert "later" not in second["basis"]
    assert second["check"]["contributions"][0]["located"][0]["value"] == "1"
    with pytest.raises(dataclasses.FrozenInstanceError):
        bundle.study_ref = "changed"


@pytest.mark.parametrize("role", ["count", "category", "denominator"])
def test_every_documentary_selection_must_match_exact_retained_value(evidence, role):
    raw, _, study = evidence
    raw["observations"][0][role]["expected"] = "stale"
    with pytest.raises(ValueError, match="stale_value"):
        prepare(raw, study)


def test_stale_supplied_digest_must_be_refused_before_meaning(evidence):
    raw, _, study = evidence
    raw["sources"][0]["digest"] = "0" * 64
    with pytest.raises(ValueError, match="stale_digest"):
        prepare(raw, study)


@pytest.mark.parametrize("target", ["raw", "source", "observation", "binding", "selection", "scope", "rule"])
def test_input_schema_must_be_closed(evidence, target):
    raw, _, study = evidence
    rows = {
        "raw": raw,
        "source": raw["sources"][0],
        "observation": raw["observations"][0],
        "binding": raw["bindings"][0],
        "selection": raw["observations"][0]["count"],
        "scope": raw["observations"][0]["scope"],
        "rule": raw["bindings"][0]["rule"],
    }
    rows[target]["invented"] = True
    with pytest.raises(ValueError):
        prepare(raw, study)


@pytest.mark.parametrize("value", [True, False, 1.5, None, "1.0", " 1", "1,000"])
def test_count_must_not_coerce_invalid_integer(evidence, value):
    raw, _, study = evidence
    raw["sources"][0]["study"]["deviations"]["count"] = value
    raw["sources"][0]["digest"] = snapshot(raw["sources"][0]["study"])["digest"]
    raw["observations"][0]["count"]["expected"] = value
    with pytest.raises(ValueError):
        prepare(raw, study)


def test_reference_profile_must_equal_observation_body(evidence):
    raw, ref, study = evidence
    ref.update(extent="profile", profile=profile("PS3"))
    with pytest.raises(ValueError, match="profile_body_mismatch"):
        apply(
            prepare(raw, study),
            ref,
            "randomized",
            100,
            profile(),
            0,
            "known",
            "resolved",
        )


def test_unknown_informative_ceiling_must_not_become_zero_or_known_population_upper(evidence):
    raw, ref, study = evidence
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), None, "known", "resolved")
    assert result["check"]["code"] == "unresolved"
    assert result["check"]["lower"] == 1
    assert result["check"]["upper"] is None
    assert result["check"]["structural_maximum"] == 100
    assert result["effective_cap"] == 100
    assert result["check"]["interval_state"] == "unknown_ceiling"
    assert result["blockers"] == ["exception_upper_unknown"]


def test_independent_accepted_conflict_is_not_erased_by_another_unresolved_binding(evidence):
    raw, ref, study = evidence
    other = copy.deepcopy(raw["bindings"][0])
    other.update(id="pending", status="proposed")
    raw["bindings"].append(other)
    ref["bindings"].append("pending")
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "conflict"
    assert result["check"]["lower"] == 1
    assert "binding_proposed:pending" in result["check"]["pending_blockers"]


def test_documentary_floor_above_selected_population_maximum_is_not_silently_discarded(evidence):
    raw, ref, study = evidence
    raw["sources"][0]["study"]["deviations"]["count"] = "101"
    identity = snapshot(raw["sources"][0]["study"])
    raw["sources"][0]["digest"] = identity["digest"]
    raw["observations"][0]["count"]["expected"] = "101"
    for row in (raw["observations"][0], raw["bindings"][0], ref):
        row["scope"].update(study=identity["study_ref"], version=identity["digest"])
    result = apply(
        prepare(raw, identity["study_ref"]), ref, "randomized", 100, profile(), None, "known", "resolved"
    )
    assert result["check"]["code"] == "conflict"
    assert result["check"]["interval_state"] == "structural_maximum_conflict"
    assert result["check"]["upper"] is None
    assert "exception_upper_unknown" in result["blockers"]


@pytest.mark.parametrize(
    "context",
    [
        [],
        [{"id": "count", "address": "/documentary_context/group", "expected": "local-G1"}],
        [{"id": "group", "address": "/documentary_context/group", "expected": "wrong"}],
        [{"id": "group", "address": "/documentary_context/group", "expected": "local-G1"}] * 2,
    ],
)
def test_documentary_context_must_be_exact_nonempty_and_unambiguous(evidence, context):
    raw, _, study = evidence
    raw["observations"][0]["context"] = context
    with pytest.raises(ValueError):
        prepare(raw, study)


def test_known_protocol_failure_is_preserved_but_must_not_become_eligibility_floor(evidence):
    raw, ref, study = evidence
    possible = [
        "entry_eligibility",
        "treatment_adherence",
        "assessment_adherence",
        "other_protocol_requirement",
    ]
    raw["bindings"][0]["possible_targets"] = possible
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "unresolved"
    assert result["check"]["lower"] == result["check"]["conditional_lower"] == 0
    assert "missing_entry_attribution:meaning" in result["blockers"]
    retained = result["check"]["contributions"][0]
    assert retained["count"] == retained["reported_lower"] == 1
    assert set(retained["possible_targets"]) == set(possible)
    assert retained["status"] == "known" and retained["resolution"] == "resolved"
    assert retained["scope"] == raw["bindings"][0]["scope"]
    assert retained["basis"][-1] == raw["bindings"][0]["basis"][0]
    assert retained["located"][1]["value"] == "protocol deviation"
    assert retained["floor"] == 0


def test_explicit_entry_eligibility_target_can_supply_accepted_floor(evidence):
    raw, ref, study = evidence
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["lower"] == result["check"]["conditional_lower"] == 1
    assert result["check"]["code"] == "conflict"
    assert result["check"]["contributions"][0]["possible_targets"] == ["entry_eligibility"]


def test_separate_proposed_eligibility_attribution_does_not_promote_broad_failure(evidence):
    raw, ref, study = evidence
    broad = raw["bindings"][0]
    broad["possible_targets"] = [
        "entry_eligibility",
        "treatment_adherence",
        "assessment_adherence",
        "other_protocol_requirement",
    ]
    attribution = copy.deepcopy(broad)
    attribution.update(id="eligibility-reading", possible_targets=["entry_eligibility"], status="proposed")
    raw["bindings"].append(attribution)
    ref["bindings"].append("eligibility-reading")
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["lower"] == 0
    assert result["check"]["conditional_lower"] == 1
    assert result["check"]["code"] == "unresolved"
    assert "missing_entry_attribution:meaning" in result["blockers"]
    assert "binding_proposed:eligibility-reading" in result["blockers"]
    assert [row["count"] for row in result["check"]["contributions"]] == [1, 1]
    assert result["check"]["contributions"][1]["conditional_possible_targets"] == ["entry_eligibility"]


@pytest.mark.parametrize("target", [None, "unattributed", "failure", 0, [], True])
def test_negative_target_must_be_explicit_closed_vocabulary(evidence, target):
    raw, _, study = evidence
    raw["bindings"][0]["possible_targets"] = target
    with pytest.raises(ValueError):
        prepare(raw, study)


def test_negative_target_must_not_be_defaulted_when_missing(evidence):
    raw, _, study = evidence
    del raw["bindings"][0]["possible_targets"]
    with pytest.raises(ValueError, match="fields"):
        prepare(raw, study)


def test_whole_evidence_packet_admits_exact_aggregate_byte_boundary(evidence, monkeypatch):
    from TrialLedger.layer2 import source_evidence

    raw, _, study = evidence
    # The source may be larger than the independent located-evidence output budget.
    raw["sources"][0]["study"]["unselected_protocol_text"] = "x" * 4096
    identity = snapshot(raw["sources"][0]["study"])
    raw["sources"][0]["digest"] = identity["digest"]
    for row in (raw["observations"][0], raw["bindings"][0]):
        row["scope"].update(study=identity["study_ref"], version=identity["digest"])
    size = len(json.dumps(raw, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    monkeypatch.setattr(source_evidence, "MAX_BYTES", size)
    bundle = prepare(raw, identity["study_ref"])
    assert bundle.observations[0].count == 1


def test_whole_packet_must_not_escape_aggregate_budget_through_small_individual_sources(
    evidence, monkeypatch
):
    from TrialLedger.layer2 import source_evidence

    raw, _, study = evidence
    size = len(json.dumps(raw, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    source_size = len(
        json.dumps(raw["sources"][0]["study"], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    assert source_size < size - 1
    monkeypatch.setattr(source_evidence, "MAX_BYTES", size - 1)
    with pytest.raises(ValueError, match="^resource_bound:bytes:template$"):
        prepare(raw, study)


def test_collection_limit_admits_its_boundary_and_must_not_mislabel_overflow(evidence, monkeypatch):
    from TrialLedger.layer2 import exception_bounds

    raw, _, study = evidence
    monkeypatch.setattr(exception_bounds, "MAX_ITEMS", 2)
    second = copy.deepcopy(raw["bindings"][0])
    second["id"] = "second"
    raw["bindings"].append(second)
    assert len(prepare(raw, study).bindings) == 2
    third = copy.deepcopy(second)
    third["id"] = "third"
    raw["bindings"].append(third)
    with pytest.raises(ValueError, match="^resource_bound:exception_bounds:bindings$"):
        prepare(raw, study)


@pytest.mark.parametrize("role", ["count", "denominator"])
@pytest.mark.parametrize("value", [True, False])
def test_boolean_documentary_quantities_must_not_become_zero_or_one(evidence, role, value):
    raw, _, study = evidence
    raw["sources"][0]["study"]["deviations"][role] = value
    raw["sources"][0]["digest"] = snapshot(raw["sources"][0]["study"])["digest"]
    raw["observations"][0][role]["expected"] = value
    with pytest.raises(ValueError, match="invalid_integer:source_marker"):
        prepare(raw, study)


def test_attribution_empty_intersection_is_conflict_must_not_mean_zero_failures():
    assert attribution_state(False, 0) == "attribution_conflict"


def test_attribution_single_entry_target_identifies_only_entry_eligibility():
    assert attribution_state(True, 1) == "entry_eligibility"


def test_attribution_entry_plus_other_possibility_must_not_identify_entry():
    assert attribution_state(True, 2) == "attribution_open"
    assert attribution_state(True, 4) == "attribution_open"


def test_attribution_non_entry_targets_must_not_become_entry_floor():
    assert attribution_state(False, 1) == "non_entry_failure"
    assert attribution_state(False, 3) == "non_entry_failure"


def test_same_failure_accepted_target_intersection_narrows_and_retraction_reopens(evidence):
    raw, ref, study = evidence
    original_source = copy.deepcopy(raw["sources"])
    raw["bindings"][0]["possible_targets"] = ["entry_eligibility", "treatment_adherence"]
    narrowing = copy.deepcopy(raw["bindings"][0])
    narrowing.update(id="narrow", possible_targets=["entry_eligibility", "assessment_adherence"])
    raw["bindings"].append(narrowing)
    ref["bindings"].append("narrow")
    narrowed = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert narrowed["check"]["code"] == "conflict"
    assert narrowed["check"]["lower"] == 1
    assert narrowed["status"] == "known"
    assert narrowed["check"]["attributions"][0]["possible_targets"] == ["entry_eligibility"]
    ref["bindings"].remove("narrow")
    reopened = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert reopened["check"]["code"] == "unresolved"
    assert reopened["check"]["lower"] == 0
    assert set(reopened["check"]["attributions"][0]["possible_targets"]) == {
        "entry_eligibility",
        "treatment_adherence",
    }
    assert reopened["check"]["contributions"][0]["reported_lower"] == 1
    assert raw["sources"] == original_source


def test_interpolated_narrowing_preserves_its_standing(evidence):
    raw, ref, study = evidence
    raw["bindings"][0]["possible_targets"] = ["entry_eligibility", "assessment_adherence"]
    narrower = copy.deepcopy(raw["bindings"][0])
    narrower.update(id="interpolated-entry", possible_targets=["entry_eligibility"], status="interpolated")
    raw["bindings"].append(narrower)
    ref["bindings"].append(narrower["id"])
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["lower"] == 1
    assert result["status"] == "interpolated"
    assert result["check"]["attributions"][0]["status"] == "interpolated"
    assert [row["status"] for row in result["check"]["contributions"]] == ["known", "interpolated"]


def test_known_singleton_proof_is_not_weakened_by_consistent_interpolation(evidence):
    raw, ref, study = evidence
    other = copy.deepcopy(raw["bindings"][0])
    other.update(
        id="broad-interpolation",
        possible_targets=["entry_eligibility", "other_protocol_requirement"],
        status="interpolated",
    )
    raw["bindings"].append(other)
    ref["bindings"].append(other["id"])
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["status"] == "known"
    assert result["check"]["lower"] == 1
    assert result["check"]["attributions"][0]["known_bindings"] == ["meaning"]
    assert result["check"]["contributions"][1]["status"] == "interpolated"


def test_interpolated_contradiction_must_not_be_discarded_by_known_proof_optimization(evidence):
    raw, ref, study = evidence
    other = copy.deepcopy(raw["bindings"][0])
    other.update(
        id="interpolated-assessment", possible_targets=["assessment_adherence"], status="interpolated"
    )
    raw["bindings"].append(other)
    ref["bindings"].append(other["id"])
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "attribution_conflict"
    assert result["check"]["lower"] is None
    assert result["check"]["conditional_lower"] is None
    assert result["status"] == "interpolated"
    assert result["check"]["independent_lower"] == 1
    assert result["check"]["independent_interval_state"] == "ceiling_conflict"
    assert result["check"]["attributions"][0]["possible_targets"] == []
    assert "attribution_conflict:meaning" in result["blockers"]
    assert result["effective_cap"] == 100


def test_empty_known_attribution_intersection_must_not_report_zero_or_eliminate(evidence):
    raw, ref, study = evidence
    other = copy.deepcopy(raw["bindings"][0])
    other.update(id="assessment", possible_targets=["assessment_adherence"])
    raw["bindings"].append(other)
    ref["bindings"].append(other["id"])
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "attribution_conflict"
    assert result["check"]["lower"] is None and result["check"]["conditional_lower"] is None
    assert result["resolution"] == "conflicting"
    assert result["status"] == "known"
    assert result["check"]["attributions"][0]["reported_lower"] == 1
    assert [row["count"] for row in result["check"]["contributions"]] == [1, 1]


def test_different_observed_failures_must_not_have_target_sets_intersected(evidence):
    raw, ref, study = evidence
    second = copy.deepcopy(raw["observations"][0])
    second["id"] = "independent-failure"
    raw["observations"].append(second)
    second_binding = copy.deepcopy(raw["bindings"][0])
    second_binding.update(
        id="different-failure-attribution",
        observation=second["id"],
        possible_targets=["assessment_adherence"],
    )
    raw["bindings"].append(second_binding)
    ref["bindings"].append(second_binding["id"])
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "conflict"
    assert result["check"]["lower"] == 1
    assert len(result["check"]["attributions"]) == 2
    assert all(group["possible_targets"] for group in result["check"]["attributions"])
    assert not any(code.startswith("attribution_conflict:") for code in result["blockers"])
    assert result["check"]["attributions"][1]["state"] == "non_entry_failure"


def test_profiles_of_one_partial_failure_must_not_be_conflated(evidence):
    raw, ref, study = evidence
    raw["bindings"][0].update(extent="profile", profile=profile("PS2"))
    other = copy.deepcopy(raw["bindings"][0])
    other.update(id="other-profile", profile=profile("PS3"), possible_targets=["treatment_adherence"])
    raw["bindings"].append(other)
    ref["bindings"].append(other["id"])
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert len(result["check"]["attributions"]) == 2
    assert result["check"]["code"] == "conflict"
    assert all(group["possible_targets"] for group in result["check"]["attributions"])


def test_proposed_rival_singletons_must_remain_separate_conditional_readings(evidence):
    raw, ref, study = evidence
    raw["bindings"][0]["possible_targets"] = [
        "entry_eligibility",
        "assessment_adherence",
        "treatment_adherence",
        "other_protocol_requirement",
    ]
    for identity, target in (
        ("entry-reading", "entry_eligibility"),
        ("treatment-reading", "treatment_adherence"),
    ):
        row = copy.deepcopy(raw["bindings"][0])
        row.update(id=identity, possible_targets=[target], status="proposed")
        raw["bindings"].append(row)
        ref["bindings"].append(identity)
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["code"] == "unresolved"
    assert result["check"]["lower"] == 0 and result["check"]["conditional_lower"] == 1
    assert len(result["check"]["attributions"][0]["possible_targets"]) == 4
    readings = result["check"]["contributions"][1:]
    assert [row["conditional_possible_targets"] for row in readings] == [
        ["entry_eligibility"],
        ["treatment_adherence"],
    ]
    assert [row["conditional_floor"] for row in readings] == [1, 0]


def test_other_protocol_residual_must_be_retained_without_eligibility_floor(evidence):
    raw, ref, study = evidence
    raw["bindings"][0]["possible_targets"] = ["other_protocol_requirement"]
    result = apply(prepare(raw, study), ref, "randomized", 100, profile(), 0, "known", "resolved")
    assert result["check"]["lower"] == result["check"]["conditional_lower"] == 0
    assert result["check"]["attributions"][0]["possible_targets"] == ["other_protocol_requirement"]
    assert result["check"]["contributions"][0]["reported_lower"] == 1
    assert result["check"]["code"] == "consistent"
    assert result["check"]["possible_floor_upper"] == 0
    assert result["blockers"] == []


def test_maintenance_recording_must_not_exclude_late_discovered_entry_violation(evidence):
    raw, ref, study = evidence
    raw["sources"][0]["study"]["documentary_context"]["period"] = "maintenance"
    identity = snapshot(raw["sources"][0]["study"])
    raw["sources"][0]["digest"] = identity["digest"]
    for row in (raw["observations"][0], raw["bindings"][0], ref):
        row["scope"].update(study=identity["study_ref"], version=identity["digest"])
    raw["observations"][0]["context"][1]["expected"] = "maintenance"
    raw["bindings"][0]["possible_targets"] = [
        "entry_eligibility",
        "treatment_adherence",
        "assessment_adherence",
        "other_protocol_requirement",
    ]
    broad = apply(
        prepare(raw, identity["study_ref"]), ref, "randomized", 100, profile(), 0, "known", "resolved"
    )
    assert "entry_eligibility" in broad["check"]["attributions"][0]["possible_targets"]
    narrowed = copy.deepcopy(raw["bindings"][0])
    narrowed.update(
        id="late-entry-discovery",
        possible_targets=["entry_eligibility"],
        basis=["Hypothetical evidence: a maintenance report identifies an entry violation discovered late."],
    )
    raw["bindings"].append(narrowed)
    ref["bindings"].append(narrowed["id"])
    result = apply(
        prepare(raw, identity["study_ref"]), ref, "randomized", 100, profile(), 0, "known", "resolved"
    )
    assert result["check"]["lower"] == 1
    assert result["check"]["code"] == "conflict"
    assert result["check"]["contributions"][0]["located"][-1]["value"] == "maintenance"


@pytest.mark.parametrize(
    "possible",
    [
        [],
        ["entry_eligibility", "entry_eligibility"],
        ["protocol_adherence"],
        ["entry_eligibility", "invented"],
    ],
)
def test_possible_target_sets_must_be_nonempty_unique_and_closed(evidence, possible):
    raw, _, study = evidence
    raw["bindings"][0]["possible_targets"] = possible
    with pytest.raises(ValueError):
        prepare(raw, study)
