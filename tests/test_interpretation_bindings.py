"""Source bindings support an exact declared use, never an identity guessed from matching counts.

Positive: population membership/definition identity and scope admit an application, with original standing.
Negative: changed population, arm, time, edition, relation or identity cannot become a clinical refutation;
it remains an unresolved use. Proposed bindings remain conditional and do not mutate fixed evidence.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, replace

import pytest

from TrialLedger.layer2 import interpretation_bindings as b
from TrialLedger.layer2 import signals


def scope():
    return {"study": "study", "population": "ITT:A", "arm": "A", "time": "enrollment", "version": "v1"}


def declaration():
    return {
        "id": "population-binding",
        "kind": "population",
        "relation": "subset_of",
        "subjects": ["ITT", "EFS"],
        "scope": scope(),
        "sources": [{"ref": "registry", "version": "v1", "address": "/population", "digest": "sha256:held"}],
        "status": "known",
        "resolution": "resolved",
        "basis": ["source:explicit-subset-definition"],
    }


def population():
    return signals.Signal(
        "coverage",
        "population",
        {
            "universe": "ITT:A",
            "alignment": "confirmed",
            "total": 609,
            "parent_ref": "ITT",
            "subset_relation": "confirmed",
            "subset": {"ref": "EFS", "universe": "ITT:A", "lower": 607, "upper": 607},
        },
        (signals.Support("source", "known", "resolved", ("source:counts",)),),
        {},
    )


def use(signal="coverage"):
    return {"binding": "population-binding", "signal": signal, "scope": scope()}


def test_binding_parsers_and_real_signal_consumer_keep_inputs_and_provenance():
    raw, raw_use, signal = declaration(), use(), population()
    before = copy.deepcopy((raw, raw_use, signal))
    bindings = b.parse_bindings([raw], "study")
    uses = b.parse_uses([raw_use], bindings, {signal.id}, "study")
    rows = b.check_uses(bindings, uses, (signal,), "study")
    assert rows == [
        {
            "binding": "population-binding",
            "signal": "coverage",
            "code": "supported",
            "status": "known",
            "basis": ["source:explicit-subset-definition", "registry@v1#/population"],
            "blockers": [],
            "rule": "interpretation.binding-use:1",
        }
    ]
    assert signals.evaluate(signal)["value"]["counts"][2] == {"id": "outside", "lower": 2, "upper": 2}
    assert (raw, raw_use, signal) == before
    assert asdict(bindings[0])["sources"][0]["digest"] == "sha256:held"


def test_binding_standing_keeps_hypotheses_conditional_and_unknowns_open():
    assert b.binding_standing("known", "resolved") == "supported"
    assert b.binding_standing("interpolated", "resolved") == "conditional"
    assert b.binding_standing("proposed", "resolved") == "conditional"
    assert b.binding_standing("known", "unresolved") == "unresolved"
    assert b.binding_standing("known", "partially_resolved") == "unresolved"
    assert b.binding_standing("known", "conflicting") == "unresolved"
    assert b.binding_standing("invented", "resolved") == "unresolved"


def test_scope_compatibility_requires_each_declared_axis_and_the_current_study():
    assert b.scope_compatibility(scope(), scope(), "study") == "matched"
    assert b.scope_compatibility(scope(), {**scope(), "arm": "B"}, "study") == "scope_mismatch"
    assert b.scope_compatibility(scope(), {**scope(), "time": "week12"}, "study") == "scope_mismatch"
    assert b.scope_compatibility(scope(), {**scope(), "version": "v2"}, "study") == "scope_mismatch"
    assert b.scope_compatibility(scope(), scope(), "other") == "study_mismatch"
    assert b.scope_compatibility(scope(), {**scope(), "study": "other"}, "study") == "study_mismatch"
    assert b.scope_compatibility({}, scope(), "study") == "scope_incomplete"
    assert b.scope_compatibility(scope(), {}, "study") == "scope_incomplete"


@pytest.mark.parametrize("axis", ["study", "population", "arm", "time", "version"])
def test_use_scope_changes_remain_unresolved_without_erasing_the_partial_calculation(axis):
    raw_use = use()
    raw_use["scope"][axis] = "different"
    bindings = b.parse_bindings([declaration()], "study")
    uses = b.parse_uses([raw_use], bindings, {"coverage"}, "study")
    rows = b.check_uses(bindings, uses, (population(),), "study")
    assert rows[0]["code"] == "unresolved" and rows[0]["blockers"]
    assert signals.evaluate(population())["value"]["counts"][2]["lower"] == 2


@pytest.mark.parametrize("status,code", [("proposed", "conditional"), ("interpolated", "conditional")])
def test_use_never_promotes_the_standing_of_an_assumed_binding(status, code):
    raw = declaration()
    raw["status"] = status
    bindings = b.parse_bindings([raw], "study")
    uses = b.parse_uses([use()], bindings, {"coverage"}, "study")
    row = b.check_uses(bindings, uses, (population(),), "study")[0]
    assert row["code"] == code and row["status"] == status


def test_population_compatibility_matches_the_relation_and_exact_named_sets():
    data = population().data
    assert b.population_compatibility("subset_of", ["ITT", "EFS"], "ITT:A", "population", data) == "matched"
    assert b.population_compatibility("subset_of", ["EFS", "ITT"], "ITT:A", "population", data) == (
        "subjects_mismatch"
    )
    assert b.population_compatibility("same_universe", ["ITT", "EFS"], "ITT:A", "population", data) == (
        "operator_mismatch"
    )
    assert b.population_compatibility("subset_of", ["ITT", "EFS"], "ITT:B", "population", data) == (
        "population_mismatch"
    )
    assert b.population_compatibility("subset_of", ["ITT", "EFS"], "ITT:A", "population", {}) == (
        "population_mismatch"
    )
    assert (
        b.population_compatibility(
            "subset_of", ["ITT", "EFS"], "ITT:A", "population", {**data, "subset": None}
        )
        == "population_mismatch"
    )
    assert (
        b.population_compatibility(
            "subset_of", ["ITT", "EFS"], "ITT:A", "population", {**data, "subset_relation": "unknown"}
        )
        == "subset_not_declared"
    )


def test_overlap_and_partition_bind_only_explicit_complete_membership_relations():
    marginals = [{"ref": "EFS", "universe": "ITT:A"}, {"ref": "EFQ", "universe": "ITT:A"}]
    data = {"universe": "ITT:A", "marginals": marginals}
    assert b.population_compatibility("same_universe", ["EFS", "EFQ"], "ITT:A", "overlap", data) == "matched"
    assert b.population_compatibility("same_universe", ["EFQ", "EFS"], "ITT:A", "overlap", data) == "matched"
    assert b.population_compatibility("same_universe", ["EFS", "EFS"], "ITT:A", "overlap", data) == (
        "subjects_mismatch"
    )
    assert (
        b.population_compatibility(
            "same_universe", ["EFS", "EFQ"], "ITT:A", "overlap", {**data, "marginals": []}
        )
        == "subjects_mismatch"
    )
    parts = {"universe": "ITT:A", "parts": marginals, "disjoint": True, "exhaustive": True}
    assert (
        b.population_compatibility("partition_of", ["EFS", "EFQ"], "ITT:A", "partition", parts) == "matched"
    )
    assert (
        b.population_compatibility(
            "partition_of", ["EFS", "EFQ"], "ITT:A", "partition", {**parts, "disjoint": False}
        )
        == "partition_not_declared"
    )
    assert (
        b.population_compatibility(
            "partition_of", ["EFS", "EFQ"], "ITT:A", "partition", {**parts, "exhaustive": 1}
        )
        == "partition_not_declared"
    )


@pytest.mark.parametrize(
    "members",
    [None, {}, [], [None], [{"ref": "EFS", "universe": "ITT:B"}], [{"ref": []}], [{"universe": "ITT:A"}]],
)
def test_malformed_or_misaligned_population_members_cannot_admit_a_binding(members):
    assert (
        b.population_compatibility(
            "same_universe", ["EFS", "EFQ"], "ITT:A", "overlap", {"universe": "ITT:A", "marginals": members}
        )
        == "subjects_mismatch"
    )


def test_definition_compatibility_needs_the_adopted_rule_and_its_exact_edition():
    data = {"scope": "cohort:A", "adopted": ["change"], "rules": [{"id": "change", "version": "v1"}]}
    assert b.definition_compatibility(["change"], "cohort:A", "v1", "dependencies", data) == "matched"
    assert b.definition_compatibility(["change"], "cohort:A", "v1", "population", data) == "operator_mismatch"
    assert b.definition_compatibility(["change"], "cohort:B", "v1", "dependencies", data) == (
        "population_mismatch"
    )
    assert b.definition_compatibility([], "cohort:A", "v1", "dependencies", data) == "definition_not_adopted"
    assert b.definition_compatibility(["other"], "cohort:A", "v1", "dependencies", data) == (
        "definition_not_adopted"
    )
    assert b.definition_compatibility(["change"], "cohort:A", "v2", "dependencies", data) == (
        "definition_version_mismatch"
    )
    assert (
        b.definition_compatibility(["change"], "cohort:A", "v1", "dependencies", {**data, "adopted": None})
        == "definition_not_adopted"
    )
    assert (
        b.definition_compatibility(["change"], "cohort:A", "v1", "dependencies", {**data, "rules": None})
        == "definition_not_found"
    )
    assert (
        b.definition_compatibility(["change"], "cohort:A", "v1", "dependencies", {**data, "rules": []})
        == "definition_not_found"
    )


def test_definition_use_does_not_rewrite_observed_or_imputed_requirements():
    raw = declaration()
    raw.update(id="definition", kind="definition", relation="adopts", subjects=["change"])
    data = {
        "scope": "ITT:A",
        "adopted": ["change"],
        "rules": [
            {
                "id": "change",
                "version": "v1",
                "output": {"id": "change", "mode": "derived"},
                "alternatives": [
                    [{"id": "baseline", "mode": "observed"}, {"id": "week12", "mode": "observed"}]
                ],
                "when": [],
            }
        ],
        "available": [{"id": "baseline", "mode": "observed"}, {"id": "week12", "mode": "imputed"}],
    }
    before = copy.deepcopy(data)
    signal = replace(population(), kind="dependencies", data=data)
    bindings = b.parse_bindings([raw], "study")
    uses = b.parse_uses([{**use(), "binding": "definition"}], bindings, {signal.id}, "study")
    assert b.check_uses(bindings, uses, (signal,), "study")[0]["code"] == "supported"
    assert data == before and data["available"][1]["mode"] == "imputed"


@pytest.mark.parametrize(
    "mutation,problem",
    [
        (lambda r: r.update(extra=True), "unknown_fields"),
        (lambda r: r.pop("basis"), "missing_fields"),
        (lambda r: r.update(id=" "), "nonempty_text"),
        (lambda r: r.update(kind="guess"), "unsupported_kind"),
        (lambda r: r.update(relation="equal"), "unsupported_kind"),
        (lambda r: r.update(subjects=[]), "nonempty_list"),
        (lambda r: r.update(subjects=["ITT"]), "subject_arity"),
        (lambda r: r.update(basis=None), "list_required"),
        (lambda r: r.update(status=None), "invalid_status"),
        (lambda r: r.update(resolution=[]), "invalid_resolution"),
        (lambda r: r.update(scope={}), "missing_fields"),
        (lambda r: r["scope"].update(time=""), "nonempty_text"),
        (lambda r: r.update(sources=[]), "nonempty_list"),
        (lambda r: r.update(sources=[None]), "object_required"),
        (lambda r: r["sources"][0].update(digest=None), "nonempty_text"),
        (lambda r: r["sources"][0].update(truth=True), "unknown_fields"),
        (lambda r: r["sources"].append(copy.deepcopy(r["sources"][0])), "duplicate_source"),
        (lambda r: r.update(basis=["x"] * (b.MAX_ITEMS + 1)), "resource_bound"),
    ],
)
def test_binding_declarations_refuse_malformed_values_by_name(mutation, problem):
    raw = declaration()
    mutation(raw)
    with pytest.raises(ValueError, match=problem):
        b.parse_bindings([raw], "study")


def test_empty_declarations_are_empty_context_and_duplicate_identities_are_not_silent_overwrites():
    assert b.parse_bindings([], "study") == ()
    assert b.parse_uses([], (), set(), "study") == ()
    assert b.check_uses((), (), (), "study") == []
    with pytest.raises(ValueError, match="duplicate_binding_id"):
        b.parse_bindings([declaration(), declaration()], "study")
    with pytest.raises(ValueError, match="list_required"):
        b.parse_bindings(None, "study")
    with pytest.raises(ValueError, match="object_required"):
        b.parse_bindings([None], "study")
    with pytest.raises(ValueError, match="resource_bound"):
        b.parse_bindings([declaration()] * (b.MAX_ITEMS + 1), "study")


@pytest.mark.parametrize(
    "mutation,problem",
    [
        (lambda r: r.update(binding="unknown"), "unknown_binding"),
        (lambda r: r.update(signal="unknown"), "unknown_signal"),
        (lambda r: r.update(extra=True), "unknown_fields"),
        (lambda r: r.update(scope=None), "object_required"),
    ],
)
def test_binding_uses_refuse_unknown_targets_without_guessing(mutation, problem):
    raw = use()
    mutation(raw)
    bindings = b.parse_bindings([declaration()], "study")
    with pytest.raises(ValueError, match=problem):
        b.parse_uses([raw], bindings, {"coverage"}, "study")


def test_duplicate_uses_or_direct_library_unknown_targets_are_named_errors():
    bindings = b.parse_bindings([declaration()], "study")
    with pytest.raises(ValueError, match="duplicate_use"):
        b.parse_uses([use(), use()], bindings, {"coverage"}, "study")
    with pytest.raises(ValueError, match="unknown_target"):
        b.check_uses(bindings, (b.BindingUse("missing", "coverage", scope()),), (population(),), "study")
    with pytest.raises(ValueError, match="duplicate_target_identity"):
        b.check_uses(bindings, (), (population(), population()), "study")
