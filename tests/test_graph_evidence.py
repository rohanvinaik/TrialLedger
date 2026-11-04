"""Intent and finite reference checks for typed graph evidence, independent of clinical vocabulary."""

from __future__ import annotations

import copy
import itertools
import json

import pytest

from TrialLedger.layer2 import run
from TrialLedger.layer2.assertions import (
    Literal,
    Not,
    Predicate,
    Rule,
    ScopedAssertion,
    Subject,
    Value,
    canonical,
)
from TrialLedger.layer2.graph_evidence import (
    EXAMPLES,
    MAX_NODES,
    bound_tightness,
    check,
    evaluate,
    graph_disposition,
    membership_problem,
    relation_conflict,
)


def time_row(before, after, low=0, high=None, low_closed=True, high_closed=True):
    return {
        "before": before,
        "after": after,
        "lower": low,
        "upper": high,
        "lower_inclusive": low_closed,
        "upper_inclusive": high_closed,
    }


def temporal(events, constraints):
    return {
        "scope": "test:single-participant-course:v1",
        "unit": "day",
        "origin": events[0],
        "resolution": "resolved",
        "events": events,
        "constraints": constraints,
    }


def triple(subject, relation, target, polarity="positive"):
    return {"subject": subject, "relation": relation, "object": target, "polarity": polarity}


def relations(triples, disjoint=None):
    return {
        "scope": "test:one-indication-and-population",
        "version": "test:edition-1",
        "resolution": "resolved",
        "triples": triples,
        "disjoint": disjoint or [],
    }


@pytest.mark.parametrize(
    "left,left_strict,right,right_strict,expected",
    [
        ("0", False, "1", False, "tighter"),
        ("1", False, "0", False, "looser"),
        ("1/3", False, "2/6", False, "equal"),
        ("1/3", True, "2/6", False, "tighter"),
        ("1/3", False, "2/6", True, "looser"),
        ("-1/3", True, "0", False, "tighter"),
        ("0", True, "0", True, "equal"),
        ("1", True, "0", False, "looser"),
    ],
)
def test_upper_bounds_keep_numeric_and_strict_order(left, left_strict, right, right_strict, expected):
    assert bound_tightness(left, left_strict, right, right_strict) == expected


def test_temporal_closure_retains_exact_rational_and_open_endpoints():
    data = temporal(
        ["a", "b", "c"], [time_row("a", "b", "1/3", "2/3", False), time_row("b", "c", "1/3", "2/3")]
    )
    result = evaluate("temporal", data)
    assert result["code"] == "consistent"
    row = next(row for row in result["value"]["bounds"] if row["before"] == "a" and row["after"] == "c")
    assert row == time_row("a", "c", "2/3", "4/3", False)
    assert json.loads(json.dumps(result)) == result


@pytest.mark.parametrize(
    "constraint,expected",
    [
        (time_row("a", "a", 0, 0), "consistent"),
        (time_row("a", "a", 0, 0, False), "conflict"),
        (time_row("a", "b", 1, 0), "conflict"),
        (time_row("a", "b", 0, 0, False), "conflict"),
        (time_row("a", "b", -1, 0, False), "consistent"),
    ],
)
def test_temporal_self_and_empty_intervals_are_exact(constraint, expected):
    assert evaluate("temporal", temporal(["a", "b"], [constraint]))["code"] == expected


def test_before_means_positive_dense_time_not_an_invented_day_gap():
    data = temporal(["a", "b"], [time_row("a", "b", 0, "1/1000", False)])
    assert evaluate("temporal", data)["code"] == "consistent"


def test_candidate_time_claims_are_conjoined_before_deciding():
    data = temporal(["a", "b", "c"], [])
    one, two = time_row("a", "b", 0, None, False), time_row("b", "a", 0, None, False)
    assert check("temporal", data, [one])["code"] == "consistent"
    assert check("temporal", data, [two])["code"] == "consistent"
    assert check("temporal", data, [one, two])["code"] == "conflict"


def test_all_small_strict_order_graphs_match_an_independent_permutation_oracle():
    events = ["a", "b", "c"]
    edges = list(itertools.permutations(events, 2))
    for selected in itertools.product((False, True), repeat=len(edges)):
        held = [edge for edge, present in zip(edges, selected, strict=True) if present]
        feasible = any(
            all(order.index(a) < order.index(b) for a, b in held) for order in itertools.permutations(events)
        )
        data = temporal(events, [time_row(a, b, 0, None, False) for a, b in held])
        assert evaluate("temporal", data)["code"] == ("consistent" if feasible else "conflict"), held


def test_unbound_event_and_unsettled_timeline_do_not_eliminate_designs():
    data = temporal(["a"], [time_row("a", "unknown")])
    result = evaluate("temporal", data)
    assert result["code"] == "unresolved" and result["blockers"] == ["unbound_event:unknown"]
    data = temporal(["a"], [time_row("a", "a", 1, None)])
    data["resolution"] = "unresolved"
    assert evaluate("temporal", data)["code"] == "unresolved"


@pytest.mark.parametrize(
    "required,absent,complete,expected",
    [
        ([], [], [], "ok"),
        (["a"], [], [], "ok"),
        (["a"], ["b"], [], "ok"),
        (["a"], ["a"], [], "required_absent"),
        ([], ["a"], [["a"]], "required_absent"),
        ([], [], [["a"], ["b"]], "complete_sets_disagree"),
        (["b"], [], [["a"]], "required_outside_complete"),
        (["a"], [], [["a"], ["a"]], "ok"),
    ],
)
def test_membership_needs_a_warrant_for_absence(required, absent, complete, expected):
    assert membership_problem(required, absent, complete) == expected


def test_small_membership_constraints_match_possible_world_enumeration():
    universe = {"a", "b"}
    worlds = [set(items) for size in range(3) for items in itertools.combinations(universe, size)]
    for required, absent, first, second in itertools.product(
        worlds, worlds, [None, *worlds], [None, *worlds]
    ):
        exact = [members for members in (first, second) if members is not None]
        feasible = any(
            required <= world
            and not absent.intersection(world)
            and all(world == members for members in exact)
            for world in worlds
        )
        answer = membership_problem(list(required), list(absent), [list(members) for members in exact])
        assert (answer == "ok") == feasible, (required, absent, exact)


@pytest.mark.parametrize(
    "blockers,conflict,expected",
    [
        ([], False, "consistent"),
        ([], True, "conflict"),
        (["unresolved_binding"], False, "unresolved"),
        (["unresolved_binding"], True, "unresolved"),
    ],
)
def test_unsettled_binding_takes_precedence_over_a_graph_conflict(blockers, conflict, expected):
    assert graph_disposition(blockers, conflict) == expected


def test_regimen_closes_ingredients_only_for_complete_arm_and_product_membership():
    data = copy.deepcopy(EXAMPLES["regimen"])
    result = evaluate("regimen", data)
    assert result["code"] == "consistent"
    ingredients = result["value"]["arms"]["arm-A"]["ingredients"]
    assert ingredients["required"] == ["ingredient-A", "ingredient-B"] and ingredients["complete"]
    assert (
        check(
            "regimen", data, [{"arm": "arm-A", "ingredients": ["ingredient-A"], "ingredients_complete": True}]
        )["code"]
        == "conflict"
    )
    data["products"][0]["ingredients_complete"] = False
    assert not evaluate("regimen", data)["value"]["arms"]["arm-A"]["ingredients"]["complete"]
    assert (
        check(
            "regimen",
            data,
            [
                {
                    "arm": "arm-A",
                    "ingredients": ["ingredient-A", "ingredient-B", "C"],
                    "ingredients_complete": True,
                }
            ],
        )["code"]
        == "consistent"
    )


def test_regimen_claims_cannot_silently_replace_known_composition():
    data = copy.deepcopy(EXAMPLES["regimen"])
    claim = {"arm": "arm-A", "absent_ingredients": ["ingredient-B"]}
    assert check("regimen", data, [claim])["code"] == "conflict"
    data["arms"][0]["products_complete"] = False
    assert check("regimen", data, [claim])["code"] == "conflict"  # Positive membership suffices.


def test_exact_product_sets_are_combined_jointly():
    data = copy.deepcopy(EXAMPLES["regimen"])
    data["arms"][0]["products"] = []
    data["arms"][0]["products_complete"] = False
    data["products"].append({"id": "product-C", "ingredients": ["C"], "ingredients_complete": True})
    one = {"arm": "arm-A", "products": ["product-AB"], "products_complete": True}
    two = {"arm": "arm-A", "products": ["product-C"], "products_complete": True}
    assert check("regimen", data, [one])["code"] == "consistent"
    assert check("regimen", data, [two])["code"] == "consistent"
    assert check("regimen", data, [one, two])["code"] == "conflict"


def test_aggregate_and_observational_groups_never_become_assigned_arms():
    data = copy.deepcopy(EXAMPLES["regimen"])
    for role in ("aggregate", "observational"):
        data["arms"].append({"id": role, "role": role, "products": [], "products_complete": True})
    result = evaluate("regimen", data)
    assert list(result["value"]["arms"]) == ["arm-A"]
    assert check("regimen", data, [{"arm": "aggregate", "ingredients": []}])["code"] == "unresolved"


def test_unknown_products_and_unresolved_roles_are_not_absence():
    data = copy.deepcopy(EXAMPLES["regimen"])
    data["arms"][0]["products"] = ["unknown"]
    assert evaluate("regimen", data)["code"] == "unresolved"
    data = copy.deepcopy(EXAMPLES["regimen"])
    data["arms"][0]["role"] = "unresolved"
    assert evaluate("regimen", data)["code"] == "unresolved"


def test_unresolved_regimen_binding_blocks_a_conflicting_candidate_claim():
    data = copy.deepcopy(EXAMPLES["regimen"])
    data["resolution"] = "unresolved"
    assert (
        check("regimen", data, [{"arm": "arm-A", "absent_ingredients": ["ingredient-A"]}])["code"]
        == "unresolved"
    )


@pytest.mark.parametrize(
    "positive,negative,disjoint,expected",
    [
        ([], [], [], "ok"),
        ([["x", "instance_of", "A"]], [["x", "instance_of", "A"]], [], "positive_negative"),
        ([["x", "instance_of", "A"], ["x", "instance_of", "B"]], [], [["A", "B"]], "disjoint_membership"),
        ([["x", "is_a", "A"], ["x", "is_a", "B"]], [], [["A", "B"]], "ok"),
        ([["x", "associated", "A"], ["x", "has_ingredient", "B"]], [], [["A", "B"]], "ok"),
    ],
)
def test_relation_conflicts_preserve_relation_type_and_class_existence(
    positive, negative, disjoint, expected
):
    assert relation_conflict(positive, negative, disjoint) == expected


def test_relations_inherit_only_upward_and_preserve_explicit_negatives():
    data = relations(
        [
            triple("child", "is_a", "parent"),
            triple("parent", "is_a", "ancestor"),
            triple("person", "instance_of", "child"),
        ]
    )
    result = evaluate("relations", data)
    assert ["person", "instance_of", "ancestor"] in result["value"]["positive"]
    assert ["parent", "is_a", "child"] not in result["value"]["positive"]
    assert (
        check("relations", data, [triple("person", "instance_of", "ancestor", "negative")])["code"]
        == "conflict"
    )
    assert result["value"]["negative"] == []


def test_all_small_subtype_graphs_match_independent_path_enumeration():
    classes = ["a", "b", "c"]
    edges = list(itertools.permutations(classes, 2))
    for selected in itertools.product((False, True), repeat=len(edges)):
        held = {edge for edge, present in zip(edges, selected, strict=True) if present}
        reachable = {(node, node) for node in classes}
        for size in range(2, len(classes) + 1):
            for path in itertools.permutations(classes, size):
                if all(edge in held for edge in zip(path, path[1:], strict=False)):
                    reachable.add((path[0], path[-1]))
        rows = [triple(a, "is_a", b) for a, b in held]
        rows += [triple(node, "is_a", node) for node in classes]
        rows.append(triple("person", "instance_of", "a"))
        positive = evaluate("relations", relations(rows))["value"]["positive"]
        expected = {(a, "is_a", b) for a, b in reachable}
        expected.update(("person", "instance_of", b) for a, b in reachable if a == "a")
        assert {tuple(row) for row in positive} == expected, held


def test_association_and_ingredient_edges_do_not_inherit_clinical_membership():
    data = relations(
        [
            triple("drug", "associated", "child"),
            triple("child", "is_a", "parent"),
            triple("product", "has_ingredient", "drug"),
        ]
    )
    positives = evaluate("relations", data)["value"]["positive"]
    assert ["drug", "instance_of", "child"] not in positives
    assert ["drug", "associated", "parent"] not in positives
    assert ["product", "has_ingredient", "parent"] not in positives


def test_disjoint_classes_only_conflict_when_a_bound_instance_inhabits_both():
    data = relations([triple("X", "is_a", "A"), triple("X", "is_a", "B")], [["A", "B"]])
    assert evaluate("relations", data)["code"] == "consistent"
    assert check("relations", data, [triple("person", "instance_of", "X")])["code"] == "conflict"


def test_relation_claims_are_joint_and_source_inputs_are_not_mutated():
    data = relations([], [["A", "B"]])
    original = copy.deepcopy(data)
    one, two = triple("person", "instance_of", "A"), triple("person", "instance_of", "B")
    assert check("relations", data, [one])["code"] == "consistent"
    assert check("relations", data, [two])["code"] == "consistent"
    assert check("relations", data, [one, two])["code"] == "conflict"
    assert data == original


@pytest.mark.parametrize("kind", ["temporal", "regimen", "relations"])
def test_examples_are_serializable_and_unresolved_binding_is_explicit(kind):
    data = copy.deepcopy(EXAMPLES[kind])
    assert json.loads(json.dumps(evaluate(kind, data)))["code"] == "consistent"
    data["resolution"] = "partially_resolved"
    assert evaluate(kind, data)["code"] == "unresolved"


@pytest.mark.parametrize("kind", ["temporal", "regimen", "relations"])
@pytest.mark.parametrize("value", [None, [], "untyped", True])
def test_malformed_top_level_inputs_have_named_refusals(kind, value):
    with pytest.raises(ValueError):
        evaluate(kind, value)


@pytest.mark.parametrize("kind", ["temporal", "regimen", "relations"])
def test_unknown_fields_missing_fields_and_invalid_resolution_are_refused(kind):
    for key, value in (("unexpected", "x"), ("resolution", []), ("scope", "")):
        data = copy.deepcopy(EXAMPLES[kind])
        data[key] = value
        with pytest.raises(ValueError):
            evaluate(kind, data)
    data = copy.deepcopy(EXAMPLES[kind])
    del data["scope"]
    with pytest.raises(ValueError):
        evaluate(kind, data)


@pytest.mark.parametrize("number", [True, 1.0, "nan", "1/0", "1e1000000000", {}, []])
def test_temporal_numbers_are_finite_exact_and_typed(number):
    with pytest.raises(ValueError):
        evaluate("temporal", temporal(["a", "b"], [time_row("a", "b", number)]))


def test_resource_and_duplicate_identity_limits_are_named():
    with pytest.raises(ValueError, match="resource_bound"):
        evaluate("temporal", temporal([str(i) for i in range(MAX_NODES + 1)], []))
    with pytest.raises(ValueError, match="duplicate"):
        evaluate("temporal", temporal(["a", "a"], []))
    data = copy.deepcopy(EXAMPLES["regimen"])
    data["arms"].append(copy.deepcopy(data["arms"][0]))
    with pytest.raises(ValueError, match="duplicate_arm"):
        evaluate("regimen", data)
    data = relations([triple(str(i), "associated", str(i)) for i in range(MAX_NODES + 1)])
    with pytest.raises(ValueError, match="resource_bound"):
        evaluate("relations", data)
    with pytest.raises(ValueError, match="resource_bound"):
        evaluate("temporal", temporal(["a", "b"], [time_row("a", "b", "1" * 513)]))


def test_unsupported_relation_does_not_get_guessed_semantics():
    with pytest.raises(ValueError, match="unsupported_relation"):
        evaluate("relations", relations([triple("a", "treats", "b")]))
    with pytest.raises(ValueError, match="unsupported_graph_kind"):
        evaluate("unknown", {})


def public_graph_case(kind):
    if kind == "temporal":
        return temporal(["a", "b"], []), [
            time_row("a", "b", 0, None, False),
            time_row("b", "a", 0, None, False),
        ]
    if kind == "regimen":
        data = copy.deepcopy(EXAMPLES[kind])
        data["arms"][0].update(products=[], products_complete=False)
        data["products"].append({"id": "product-C", "ingredients": ["C"], "ingredients_complete": True})
        return data, [
            {"arm": "arm-A", "products": ["product-AB"], "products_complete": True},
            {"arm": "arm-A", "products": ["product-C"], "products_complete": True},
        ]
    return relations([], [["A", "B"]]), [
        triple("person", "instance_of", "A"),
        triple("person", "instance_of", "B"),
    ]


def public_signal(kind, data):
    return {
        "id": "invented-signal",
        "kind": kind,
        "data": data,
        "support": [
            {"id": "source", "status": "known", "resolution": "resolved", "basis": ["source:exact:v1"]},
            {
                "id": "binding",
                "status": "interpolated",
                "resolution": "resolved",
                "basis": ["user:accepted-explicit-binding:v1"],
            },
        ],
    }


def public_design(signal, claims):
    query = Literal(Subject("participant"), Predicate("condition_status", "invented-A"), Value("boolean"))
    candidates = []
    for identity, body in (("blocked", Not(query)), ("kept", query)):
        assertion = ScopedAssertion(
            identity,
            "user:invented-candidate:" + identity,
            "required",
            body,
            rule=Rule("invented-explicit-premise", "1"),
            status="known",
            resolution="resolved",
        )
        candidates.append({"id": identity, "assertions": [json.loads(canonical(assertion))]})
    candidates[0]["signal_claims"] = [{"signal": signal["id"], "claim": claim} for claim in claims]
    return {
        "operation": "design_bounds",
        "study_ref": "invented:study:version-1",
        "candidates": candidates,
        "observations": [],
        "signals": [signal],
        "query": json.loads(canonical(query)),
    }


@pytest.mark.parametrize("view", ["signals", "design_bounds"])
def test_public_discovery_supplies_runnable_graph_examples_and_claim_contracts(view):
    envelope = run({"operation": "describe", "view": view, "detail": "full"})
    assert envelope["code"] == "complete"
    discovery = envelope["result"]
    for kind in ("temporal", "regimen", "relations"):
        assert kind in discovery["signal_kinds"]
        assert discovery["operator_inputs"][kind]["claims"]
        assert discovery["operator_inputs"][kind]["limits"]
        result = run(discovery["signal_examples"][kind])
        assert result["code"] == "complete"
        assert result["result"]["signals"][0]["code"] == "consistent"


@pytest.mark.parametrize("kind", ["temporal", "regimen", "relations"])
def test_public_design_joint_claims_eliminate_and_retain_weakest_elimination_support(kind):
    data, claims = public_graph_case(kind)
    signal = public_signal(kind, data)
    request = public_design(signal, claims)
    original = copy.deepcopy(request)
    for claim in claims:
        one = run(public_design(signal, [claim]))
        assert one["code"] == "complete"
        assert one["result"]["candidates"][0]["state"] == "not_ruled_out"
    envelope = run(request)
    assert envelope["code"] == "complete"
    result = envelope["result"]
    assert result["remaining"] == ["kept"]
    assert result["consequence"]["result"] == "ENTAILED"
    assert result["consequence"]["status"] == "interpolated"
    blocked = result["candidates"][0]
    assert blocked["state"] == "ruled_out"
    assert len(blocked["signal_checks"]) == 1
    check = blocked["signal_checks"][0]
    assert check["code"] == check["calculation_code"] == "conflict"
    assert check["status"] == "interpolated"
    assert check["basis"] == ["source:exact:v1", "user:accepted-explicit-binding:v1"]
    assert json.loads(json.dumps(check["support"])) == signal["support"]
    assert result["signals"][0]["code"] == "consistent"
    assert request == original


@pytest.mark.parametrize("kind", ["temporal", "regimen", "relations"])
@pytest.mark.parametrize(
    "status,resolution,blocker",
    [("proposed", "resolved", "proposed_refused"), ("known", "unresolved", "binding_unresolved")],
)
def test_public_unsettled_support_does_not_eliminate_a_jointly_conflicting_candidate(
    kind, status, resolution, blocker
):
    data, claims = public_graph_case(kind)
    signal = public_signal(kind, data)
    signal["support"][1].update(status=status, resolution=resolution)
    envelope = run(public_design(signal, claims))
    assert envelope["code"] == "complete"
    result = envelope["result"]
    assert result["remaining"] == ["blocked", "kept"]
    assert result["consequence"]["result"] == "UNDETERMINED"
    blocked = result["candidates"][0]
    assert blocked["state"] == "unresolved"
    check = blocked["signal_checks"][0]
    assert (check["code"], check["calculation_code"]) == ("unresolved", "conflict")
    assert blocker + ":invented-signal" in check["blockers"]


@pytest.mark.parametrize("kind", ["temporal", "regimen", "relations"])
def test_public_unresolved_graph_binding_retains_the_candidate(kind):
    data, claims = public_graph_case(kind)
    data["resolution"] = "partially_resolved"
    envelope = run(public_design(public_signal(kind, data), claims))
    assert envelope["code"] == "complete"
    result = envelope["result"]
    assert result["remaining"] == ["blocked", "kept"]
    assert result["candidates"][0]["state"] == "unresolved"
    assert result["consequence"]["result"] == "UNDETERMINED"
    assert kind + "_binding:partially_resolved" in result["signals"][0]["blockers"]


@pytest.mark.parametrize("kind", ["temporal", "regimen", "relations"])
def test_public_source_conflict_blocks_the_family_without_claiming_protocol_impossibility(kind):
    data, claims = public_graph_case(kind)
    if kind == "temporal":
        data["constraints"] = claims
    elif kind == "regimen":
        data["arms"][0]["products"] = ["product-AB"]
        data["absent_products"] = [{"arm": "arm-A", "product": "product-AB"}]
    else:
        data["triples"] = claims
    signal = public_signal(kind, data)
    envelope = run(public_design(signal, []))
    assert envelope["code"] == "complete"
    result = envelope["result"]
    assert result["remaining"] == ["blocked", "kept"]
    assert all(row["state"] == "not_ruled_out" for row in result["candidates"])
    assert result["signals"][0]["code"] == "conflict"
    assert result["consequence"]["result"] == "CONFLICT"
    assert result["consequence"]["status"] == "interpolated"
    assert result["consequence"]["blockers"] == ["signal_conflict:invented-signal"]
    assert "not proof that every real protocol is impossible" in result["consequence"]["basis"]
