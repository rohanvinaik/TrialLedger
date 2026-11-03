"""Intent: preserve useful hypothetical readings without promoting or leaking their premises.

An exact conditional consequence is different from identified source meaning. Scope, unresolved admission
and source conflicts must survive the route into a frame decision and the declared-family consequence.
"""

from __future__ import annotations

import copy
import dataclasses
import itertools

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail, signals
from TrialLedger.layer2 import interpretation_bindings as b
from TrialLedger.layer2 import interpretations as i


def flag(key="marker", negative=False):
    return a.Literal(
        a.Subject("participant"),
        a.Predicate("demographic", key),
        a.Value("boolean"),
        polarity="negative" if negative else "positive",
    )


def quantity(comparison, number, key="ECOG", unit="ECOG"):
    return a.Literal(
        a.Subject("participant"),
        a.Predicate("measurement", key),
        a.Value("quantity", comparison, number=number, unit=unit),
    )


def assertion(identity, body, status="proposed", **changes):
    return a.ScopedAssertion(
        identity,
        "invented:explicit-premise",
        "required",
        body,
        rule=a.Rule("invented-premise", "1", warrants=("invented:meaning-not-certified",)),
        status=status,
        resolution="resolved",
        **changes,
    )


def frame(identity="reading", assumptions=(), **changes):
    return i.Interpretation(
        identity, "Invented clinical reading", "assistant", ("invented:exploration",), assumptions, **changes
    )


def run(frames, fixed=(), fixed_signals=(), queries=None, **kwargs):
    return i.resolve(
        "invented:study",
        fixed,
        fixed_signals,
        tuple(frames),
        queries or (i.Query("question", flag()),),
        **kwargs,
    )


def population(status="known", resolution="resolved"):
    return signals.Signal(
        "coverage",
        "population",
        {
            "universe": "ITT",
            "alignment": "confirmed",
            "total": 200,
            "parent_ref": "randomized",
            "subset_relation": "confirmed",
            "subset": {"ref": "analysed", "universe": "ITT", "lower": 160, "upper": 160},
        },
        (signals.Support("count-and-reading", status, resolution, ("invented:source",)),),
        {},
    )


def binding(resolution="resolved", status="proposed"):
    scope = {"study": "invented:study", "population": "ITT", "arm": "A", "time": "analysis", "version": "1"}
    declared = b.Binding(
        "population-binding",
        "population",
        "subset_of",
        ("randomized", "analysed"),
        scope,
        ({"ref": "invented:registry", "version": "1", "address": "/population"},),
        status,
        resolution,
        ("invented:declared-cohort-correspondence",),
    )
    return declared, b.BindingUse(declared.id, "coverage", dict(scope))


def test_pure_states_preserve_each_distinct_remedy():
    assert i.compatibility_state(True, True, True, True) == "floor_conflict"
    assert i.compatibility_state(False, True, True, True) == "incoherent"
    assert i.compatibility_state(False, False, True, True) == "refuted"
    assert i.compatibility_state(False, False, False, True) == "unresolved"
    assert i.compatibility_state(False, False, False, False) == "compatible"
    assert i.selection_state(None, {}) == "none"
    assert i.selection_state("missing", {}) == "unknown_selection"
    assert i.selection_state("chosen", {"chosen": "compatible"}) == "selected"
    assert i.selection_state("chosen", {"chosen": "unresolved"}) == "unresolved"
    assert i.selection_state("chosen", {"chosen": "refuted"}) == "refused"
    assert i.selection_state("chosen", {"chosen": "incoherent"}) == "refused"
    assert i.selection_state("chosen", {"chosen": "floor_conflict"}) == "refused"


def test_competing_hypotheses_are_isolated_and_remain_proposed():
    yes = assertion("marker-required", flag())
    no = assertion("marker-excluded", flag(negative=True))
    inputs = (frame("yes", (yes,)), frame("no", (no,)))
    before = copy.deepcopy(inputs)
    result = run(inputs)
    assert result["remaining"] == ["yes", "no"]
    assert [row["state"] for row in result["interpretations"]] == ["compatible", "compatible"]
    assert [row["queries"][0]["result"] for row in result["interpretations"]] == ["ENTAILED", "REFUTED"]
    assert result["consequences"][0]["result"] == "UNDETERMINED"
    assert result["fixed"]["queries"][0]["result"] == "UNDETERMINED"
    assert result["interpretations"][0]["premises"]["assumptions"][0]["status"] == "proposed"
    assert result["interpretations"][0]["queries"][0]["warrant"]["status"] == "proposed"
    assert inputs == before
    assert entail.decide((yes,), flag()).result == "UNDETERMINED"
    assert entail.decide((yes,), flag()).blockers == (
        "no_constraint_mentions_query",
        "proposed_refused:marker-required",
    )


def test_fixed_refutation_and_intrinsic_incoherence_have_different_warrants():
    fixed = (assertion("fixed-maximum", quantity("le", 2), "known"),)
    result = run(
        [
            frame("outside-floor", (assertion("PS3", quantity("eq", 3)),)),
            frame("incoherent", (assertion("yes", flag()), assertion("no", flag(negative=True)))),
        ],
        fixed=fixed,
    )
    outside, incoherent = result["interpretations"]
    assert outside["state"] == "refuted" and incoherent["state"] == "incoherent"
    assert outside["warrant"]["fixed_premises"] == ["fixed-maximum"]
    assert outside["warrant"]["fixed_status"] == "known"
    assert set(outside["warrant"]["consistency"]["proof"]) == {"fixed-maximum", "PS3"}
    assert outside["queries"][0]["result"] == "UNDETERMINED"
    assert result["remaining"] == [] and result["consequences"][0]["result"] == "CONFLICT"


def test_interpolated_floor_refutation_retains_its_conditional_origin():
    result = run(
        [frame(assumptions=(assertion("PS3", quantity("eq", 3)),))],
        fixed=(assertion("interpolated-maximum", quantity("le", 2), "interpolated"),),
    )
    row = result["interpretations"][0]
    assert row["state"] == "refuted"
    assert row["warrant"]["fixed_status"] == "interpolated"
    assert row["warrant"]["guarantee"] == "conditional_on_fixed_and_interpretation_premises"


@pytest.mark.parametrize("resolution", ["unresolved", "partially_resolved", "conflicting"])
def test_unresolved_fixed_premise_cannot_refute_a_reading(resolution):
    fixed = dataclasses.replace(
        assertion("uncertain-maximum", quantity("le", 2), "known"), resolution=resolution
    )
    result = run([frame(assumptions=(assertion("PS3", quantity("eq", 3)),))], fixed=(fixed,))
    row = result["interpretations"][0]
    assert row["state"] == "unresolved"
    assert row["warrant"]["fixed_premises"] == []
    assert "premise_not_resolved:uncertain-maximum" in result["fixed"]["blockers"]


def test_open_fixed_scope_does_not_supply_an_unqualified_bound():
    fixed = assertion("cohort-A-only", quantity("le", 2), "known", cohort=a.Scope("cohort_ref", "A"))
    result = run([frame(assumptions=(assertion("PS3", quantity("eq", 3)),))], fixed=(fixed,))
    assert result["interpretations"][0]["state"] == "unresolved"
    result = run(
        [frame(assumptions=(assertion("PS3", quantity("eq", 3)),))],
        fixed=(fixed,),
        context=entail.Context(cohort="B"),
    )
    assert result["interpretations"][0]["state"] == "compatible"


def test_fixed_floor_contradiction_blocks_every_frame_without_explosion():
    result = run(
        [frame()], fixed=(assertion("yes", flag(), "known"), assertion("no", flag(negative=True), "known"))
    )
    assert result["interpretations"][0]["state"] == "floor_conflict"
    assert result["fixed"]["queries"][0]["result"] == "UNDETERMINED"
    assert result["consequences"][0]["result"] == "CONFLICT"


def test_unrelated_unknown_premise_retains_a_conditional_answer_and_independent_fixed_answer():
    unknown = dataclasses.replace(assertion("unknown", flag("other")), resolution="unresolved")
    result = run(
        [frame(assumptions=(assertion("marker", flag()), unknown))],
        fixed=(assertion("adult", quantity("ge", 18, "age", "Years"), "known"),),
        queries=(i.Query("marker", flag()), i.Query("adult", quantity("ge", 18, "age", "Years"))),
    )
    row = result["interpretations"][0]
    assert row["state"] == "unresolved"
    assert row["queries"][0]["result"] == "UNDETERMINED"
    assert row["queries"][0]["decision"]["result"] == "ENTAILED"
    assert result["consequences"][1]["result"] == "ENTAILED"
    assert result["consequences"][1]["basis"] == "fixed_floor"


def test_population_binding_is_consumed_and_revisions_recompute_the_refutation():
    declared, use = binding("unresolved")
    reading = frame(
        signal_claims=({"signal": "coverage", "claim": {"count": "outside", "lower": 0, "upper": 0}},),
        binding_uses=(use,),
    )
    result = run([reading], fixed_signals=(population(),), bindings=(declared,))
    row = result["interpretations"][0]
    assert row["state"] == "unresolved"
    assert row["signal_checks"][0]["code"] == "unresolved"
    assert row["signal_checks"][0]["calculation_code"] == "conflict"
    resolved = run(
        [reading],
        fixed_signals=(population(),),
        bindings=(dataclasses.replace(declared, resolution="resolved"),),
    )
    assert resolved["interpretations"][0]["state"] == "refuted"
    assert resolved["interpretations"][0]["bindings"][0]["code"] == "conditional"
    assert result["interpretations"][0]["state"] == "unresolved"


def test_unresolved_local_binding_preserves_its_exact_conditional_count():
    declared, use = binding("unresolved")
    result = run([frame(signals=(population("proposed"),), binding_uses=(use,))], bindings=(declared,))
    row = result["interpretations"][0]
    assert row["state"] == "unresolved"
    assert row["signals"][0]["value"]["counts"][-1] == {"id": "outside", "lower": 40, "upper": 40}
    assert row["signals"][0]["status"] == "proposed"
    assert row["premises"]["signals"][0]["support"][0]["status"] == "proposed"


@pytest.mark.parametrize("local", [False, True])
def test_binding_standing_reaches_every_dependent_calculation_without_mutation(local):
    declared, use = binding(status="proposed")
    source = population("known")
    reading = frame(signals=(source,) if local else (), binding_uses=(use,))
    before = copy.deepcopy((declared, source, reading))
    result = run([reading], fixed_signals=() if local else (source,), bindings=(declared,))
    row = result["interpretations"][0]["signals"][0]
    assert row["code"] == "bounded" and row["status"] == "proposed"
    assert row["unbound_status"] == "known"
    assert row["guarantee"] == "conditional_on_interpretation"
    assert row["binding_refs"] == row["assumed_bindings"] == [declared.id]
    assert declared.basis[0] in row["basis"]
    assert "invented:registry@1#/population" in row["binding_basis"]
    assert row["binding_support"][0]["status"] == "proposed"
    assert (declared, source, reading) == before


def test_unresolved_fixed_signal_cannot_refute_or_create_a_source_floor_conflict():
    unknown = population("proposed")
    result = run(
        [
            frame(
                signal_claims=({"signal": "coverage", "claim": {"count": "outside", "lower": 0, "upper": 0}},)
            )
        ],
        fixed_signals=(unknown,),
    )
    assert result["fixed"]["signals"][0]["code"] == "unresolved"
    assert result["interpretations"][0]["state"] == "unresolved"
    assert result["refuted"] == []


def test_completed_dependency_claim_governs_the_frame_while_unknown_baseline_remains_visible():
    source = signals.Signal(
        "definition",
        "dependencies",
        {
            "scope": "cohort",
            "version": "1",
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
            "adopted": ["change"],
            "available": [{"id": "baseline", "mode": "observed"}],
            "unavailable": [],
            "conditions": {},
        },
        (signals.Support("definition-source", "known", "resolved", ("invented:definition",)),),
        {},
    )
    scope = {"study": "invented:study", "population": "cohort", "arm": "A", "time": "week12", "version": "v1"}
    declared = b.Binding(
        "definition-binding",
        "definition",
        "adopts",
        ("change",),
        scope,
        ({"ref": "invented:protocol", "version": "v1", "address": "/endpoint"},),
        "known",
        "resolved",
        ("invented:adopted-definition",),
    )
    reading = frame(
        signal_claims=(
            {"signal": "definition", "claim": {"available": [{"id": "week12", "mode": "observed"}]}},
        ),
        binding_uses=(b.BindingUse(declared.id, "definition", scope),),
    )
    result = run([reading], fixed_signals=(source,), bindings=(declared,))
    row = result["interpretations"][0]
    assert row["state"] == "compatible"
    assert row["signals"][0]["code"] == "unresolved"
    assert row["signals"][0]["role"] == "baseline_context"
    assert row["signal_checks"][0]["code"] == "consistent"
    assert source.data["available"] == [{"id": "baseline", "mode": "observed"}]


def test_joint_claims_against_one_signal_are_conjoined():
    source = population()
    claims = (
        {"signal": "coverage", "claim": {"count": "outside", "lower": 30, "upper": 45}},
        {"signal": "coverage", "claim": {"count": "outside", "lower": 45, "upper": 50}},
    )
    result = run([frame(signal_claims=claims)], fixed_signals=(source,))
    assert result["interpretations"][0]["state"] == "refuted"
    assert len(result["interpretations"][0]["signal_checks"]) == 1
    assert len(result["interpretations"][0]["signal_checks"][0]["claims"]) == 2


def test_single_survivor_and_selection_never_promote_hypothesis_to_source_fact():
    result = run([frame("yes", (assertion("yes", flag()),))], selected="yes")
    assert result["selection"] == {"id": "yes", "state": "selected", "origin": "user_choice"}
    common = result["consequences"][0]
    assert common["result"] == "ENTAILED" and common["warrant"]["status"] == "proposed"
    assert common["warrant"]["guarantee"] == "conditional_on_declared_family_not_exhaustive"
    assert result["fixed"]["queries"][0]["result"] == "UNDETERMINED"
    refused = run(
        [frame("no", (assertion("no", flag(negative=True)),))],
        fixed=(assertion("yes", flag(), "known"),),
        selected="no",
    )
    assert refused["selection"]["state"] == "refused"
    assert refused["interpretations"][0]["state"] == "refuted"
    assert refused["consequences"][0]["result"] == "ENTAILED"  # independently established by the floor


def test_unsupported_query_and_resource_bound_have_no_false_refutation():
    result = run([frame()], queries=(i.Query("opaque", a.Opaque("unknown-subject")),))
    assert result["interpretations"][0]["queries"][0]["result"] == "UNSUPPORTED_QUERY"
    assert result["consequences"][0]["result"] == "UNSUPPORTED_QUERY"
    assert result["consequences"][0]["basis"] == "query_translation"
    hard = assertion("combination", a.AllOf((flag("a"), flag("b"), flag("c"))))
    result = run([frame(assumptions=(hard,))], bound=1)
    assert result["interpretations"][0]["state"] == "unresolved"
    assert "resource_bound" in result["interpretations"][0]["warrant"]["blockers"]


def test_finite_boolean_worlds_independently_check_frame_compatibility():
    worlds = list(itertools.product((False, True), repeat=2))
    bodies = [flag("p"), flag("p", True), a.AnyOf((flag("p"), flag("q"))), a.AllOf((flag("p"), flag("q")))]
    predicates = [lambda p, q: p, lambda p, q: not p, lambda p, q: p or q, lambda p, q: p and q]
    for fixed_index, local_index in itertools.product(range(4), repeat=2):
        intrinsic = any(predicates[local_index](*world) for world in worlds)
        together = any(
            predicates[fixed_index](*world) and predicates[local_index](*world) for world in worlds
        )
        expected = "incoherent" if not intrinsic else "compatible" if together else "refuted"
        result = run(
            [frame(assumptions=(assertion("local", bodies[local_index]),))],
            fixed=(assertion("fixed", bodies[fixed_index], "known"),),
        )
        assert result["interpretations"][0]["state"] == expected


def test_duplicate_identities_empty_families_and_unknown_selection_are_named_refusals():
    with pytest.raises(ValueError, match="empty_interpretation_inputs"):
        run([])
    with pytest.raises(ValueError, match="unknown_selected_interpretation"):
        run([frame()], selected="absent")
    with pytest.raises(ValueError, match="duplicate_interpretation_or_query_id"):
        run([frame(), frame()])
    with pytest.raises(ValueError, match="duplicate_interpretation_premise_id"):
        run([frame(assumptions=(assertion("same", flag()),))], fixed=(assertion("same", flag(), "known"),))
    with pytest.raises(ValueError, match="unknown_interpretation_signal_claim"):
        run([frame(signal_claims=({"signal": "absent", "claim": {}},))])
