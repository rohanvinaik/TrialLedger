"""Intent: baseline witnesses constrain designs, then reach consequences without promoting support."""

from __future__ import annotations

import copy
import itertools
import json

import pytest

from TrialLedger.layer2 import run
from TrialLedger.layer2.bounds_guide import example
from TrialLedger.layer2.design_bounds import candidate_state, common_result, witness_support, witness_verdict


@pytest.mark.parametrize(
    "count,exceptions,expected",
    [(0, 0, "no_witness"), (126, 125, "witness"), (126, 126, "no_witness"), (126, 127, "no_witness")],
)
def test_positive_count_must_exceed_the_exception_allowance(count, exceptions, expected):
    assert witness_support(count, exceptions, "interpolated", "resolved") == expected


@pytest.mark.parametrize(
    "status,resolution,expected",
    [
        ("proposed", "resolved", "proposed_refused"),
        ("known", "unresolved", "binding_unresolved"),
        ("interpolated", "partially_resolved", "binding_unresolved"),
        ("known", "conflicting", "binding_unresolved"),
        ("known", "resolved", "witness"),
    ],
)
def test_unsettled_bridges_must_never_supply_witnesses(status, resolution, expected):
    assert witness_support(1, 0, status, resolution) == expected


@pytest.mark.parametrize(
    "support,result,blockers,expected",
    [
        ("witness", "REFUTED", [], "ruled_out"),
        ("no_witness", "REFUTED", [], "not_ruled_out"),
        ("proposed_refused", "REFUTED", [], "unresolved"),
        ("binding_unresolved", "REFUTED", [], "unresolved"),
        ("witness", "UNDETERMINED", ["resource_bound"], "unresolved"),
        ("witness", "REFUTED", ["proposed_refused:x"], "ruled_out"),
        ("witness", "UNDETERMINED", ["undecided_by_constraints"], "not_ruled_out"),
        ("witness", "UNDETERMINED", ["no_constraint_mentions_query"], "not_ruled_out"),
        ("witness", "ENTAILED", [], "not_ruled_out"),
        ("witness", "OUT_OF_SCOPE", [], "unresolved"),
        ("witness", "UNSUPPORTED_QUERY", [], "unresolved"),
        ("no_witness", "INCONSISTENT", [], "inconsistent"),
    ],
)
def test_only_supported_refutation_eliminates_a_design(support, result, blockers, expected):
    assert witness_verdict(support, result, blockers) == expected


def test_observations_constrain_independently_without_voting_or_order():
    assert candidate_state([]) == "not_ruled_out"
    assert candidate_state(["not_ruled_out"]) == "not_ruled_out"
    assert candidate_state(["unresolved"]) == "unresolved"
    for order in itertools.permutations(["ruled_out", "unresolved", "not_ruled_out"]):
        assert candidate_state(list(order)) == "ruled_out"
    assert candidate_state(["ruled_out", "inconsistent"]) == "inconsistent"


@pytest.mark.parametrize(
    "states,results,expected",
    [
        ([], [], "CONFLICT"),
        (["not_ruled_out"], [], "UNDETERMINED"),
        (["unresolved"], ["ENTAILED"], "UNDETERMINED"),
        (["not_ruled_out"], ["ENTAILED"], "ENTAILED"),
        (["not_ruled_out"], ["REFUTED"], "REFUTED"),
        (["not_ruled_out"], ["UNDETERMINED"], "UNDETERMINED"),
        (["not_ruled_out"] * 2, ["ENTAILED", "REFUTED"], "UNDETERMINED"),
        (["not_ruled_out"] * 2, ["ENTAILED", "UNDETERMINED"], "UNDETERMINED"),
    ],
)
def test_common_consequences_need_every_survivor(states, results, expected):
    assert common_result(states, results) == expected


def complete(request):
    reply = run(json.loads(json.dumps(request)))
    assert reply["code"] == "complete", reply
    return reply["result"]


def test_elimination_reaches_the_common_consequence_and_retains_its_weakest_status():
    request = example()
    before = copy.deepcopy(request)
    result = complete(request)
    assert result["remaining"] == ["at_most_2", "at_most_3"]
    assert result["consequence"]["result"] == "ENTAILED"
    assert result["consequence"]["status"] == "interpolated"
    assert result["premises"] == request == before
    first = result["candidates"][0]["observations"][0]
    assert first["decision"]["result"] == "REFUTED" and first["decision"]["proof"] == ("at_least_3",)
    assert set(first["basis"]) == {
        "invented:baseline-cell",
        "user:invented-assumption-of-aligned-eligibility-witnesses",
    }
    # Reinstating the candidate changes the common consequence; this catches disconnected witness logic.
    request["observations"][0]["bridge"]["max_exceptions"] = 12
    revised = complete(request)
    assert len(revised["remaining"]) == 3
    assert revised["consequence"]["result"] == "UNDETERMINED"
    assert complete(before) == result


def test_known_deductions_require_known_bridges_and_observations():
    request = example()
    request["observations"][0]["bridge"]["status"] = "known"
    assert complete(request)["consequence"]["status"] == "known"
    request["observations"][0]["status"] = "interpolated"
    assert complete(request)["consequence"]["status"] == "interpolated"


@pytest.mark.parametrize(
    "field,value", [("status", "proposed"), ("resolution", "unresolved"), ("resolution", "conflicting")]
)
def test_unaccepted_bridges_keep_candidates_and_block_the_derived_answer(field, value):
    request = example()
    request["observations"][0]["bridge"][field] = value
    result = complete(request)
    assert len(result["remaining"]) == 3 and result["consequence"]["result"] == "UNDETERMINED"


def test_zero_and_overlapping_marginals_cannot_manufacture_witnesses():
    request = example()
    observation = request["observations"][0]
    observation["bridge"]["max_exceptions"] = observation["count"]
    second = copy.deepcopy(observation)
    second["id"] = "overlapping-arm-or-marginal"
    request["observations"].append(second)
    assert len(complete(request)["remaining"]) == 3
    observation["count"] = second["count"] = 0
    assert len(complete(request)["remaining"]) == 3


def test_no_candidate_surviving_is_a_conflict_without_explosion():
    request = example()
    request["candidates"] = request["candidates"][:1]
    result = complete(request)
    assert result["remaining"] == []
    assert result["consequence"]["result"] == "CONFLICT"
    assert result["consequence"]["status"] == "interpolated"


def test_inconsistent_candidate_is_reported_with_its_own_proof_not_observation_status():
    request = example()
    candidate = request["candidates"][0]
    candidate["assertions"].append(request["candidates"][1]["assertions"][0])
    request["observations"][0]["status"] = "proposed"
    result = complete(request)
    assert result["candidates"][0]["state"] == "inconsistent"
    assert result["candidates"][0]["query_decision"]["result"] == "INCONSISTENT"


@pytest.mark.parametrize("change", ["scale", "unit", "time", "cohort", "qualified", "proposed", "bound"])
def test_measurement_scope_and_uncertainty_must_not_be_silently_erased(change):
    request = example()
    observation = request["observations"][0]
    if change == "scale":
        observation["body"]["predicate"]["key"] = "different_scale"
    elif change == "unit":
        observation["body"]["value"]["unit"] = "different_unit"
    elif change == "time":
        observation["body"]["time"] = {
            "class": "TemporalScope",
            "orientation": "at",
            "anchor": "randomization",
            "certainty": "explicit",
        }
    elif change == "cohort":
        request["candidates"][0]["assertions"][0]["cohort"] = {
            "class": "Scope",
            "kind": "cohort_ref",
            "ref": "A",
        }
        observation["context"] = {"cohort": "B"}
    elif change == "qualified":
        request["candidates"][0]["assertions"][0]["applicability"] = {
            "class": "Literal",
            "subject": {"class": "Subject", "kind": "participant"},
            "predicate": {"class": "Predicate", "kind": "condition_status", "key": "qualifier"},
            "value": {"class": "Value", "kind": "boolean"},
        }
    elif change == "proposed":
        request["candidates"][0]["assertions"][0]["status"] = "proposed"
    else:
        request["bound"] = 1
    result = complete(request)
    assert "at_least_3" in result["remaining"]
    assert result["consequence"]["result"] == "UNDETERMINED"


def test_unconstrained_candidate_remains_possible_and_exact_cutoff_is_not_recovered():
    request = example()
    request["candidates"].append({"id": "no_cutoff", "assertions": []})
    result = complete(request)
    assert result["remaining"] == ["at_most_2", "at_most_3", "no_cutoff"]
    assert result["consequence"]["result"] == "UNDETERMINED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("count", -1),
        ("count", True),
        ("count", "12"),
        ("count", 101),
        ("denominator", 0),
        ("status", []),
        ("basis", []),
        ("population", ""),
        ("context", []),
    ],
)
def test_invalid_observation_inputs_are_named_refusals(field, value):
    request = example()
    request["observations"][0][field] = value
    reply = run(request)
    assert reply["code"] == "refused" and reply["problems"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_exceptions", -1),
        ("max_exceptions", True),
        ("max_exceptions", 101),
        ("resolution", []),
        ("basis", []),
    ],
)
def test_invalid_bridge_inputs_are_named_refusals(field, value):
    request = example()
    request["observations"][0]["bridge"][field] = value
    assert run(request)["code"] == "refused"


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidates", []),
        ("observations", []),
        ("study_ref", ""),
        ("query", {"class": "Always"}),
        ("context", {"cohort": False}),
        ("bound", 0),
        ("bound", True),
    ],
)
def test_invalid_operation_inputs_are_named_refusals(field, value):
    request = example()
    request[field] = value
    assert run(request)["code"] == "refused"


def test_duplicate_ids_and_unknown_fields_are_not_silently_accepted():
    for field in ("observations", "candidates"):
        request = example()
        request[field].append(copy.deepcopy(request[field][0]))
        assert run(request)["code"] == "refused"
    request = example()
    request["observations"][0]["raw_eligibility_text"] = "WHO PS 0-2"
    assert run(request)["code"] == "refused"


def test_discovery_exposes_working_schema_categories_and_reusable_example():
    description = complete({"operation": "describe", "view": "design_bounds"})
    result = complete(description["example"])
    assert set(description["result_guide"]["fields"]) == set(result)
    assert set(description["answer_guide"]["design_bounds"]) == {
        "ruled_out",
        "not_ruled_out",
        "unresolved",
        "inconsistent",
        "CONFLICT",
        "ENTAILED",
        "REFUTED",
        "UNDETERMINED",
    }
    assert "design_bounds" in complete({"operation": "describe"})["discovery"]


def test_disjunctions_are_not_flattened_into_universal_requirements():
    request = example()
    first = request["candidates"][0]["assertions"][0]
    first["body"] = {"class": "AnyOf", "parts": [first["body"], request["query"]]}
    assert "at_least_3" in complete(request)["remaining"]


def test_unsupported_queries_and_total_work_limits_are_explicit():
    request = example()
    request["query"] = {"class": "Opaque", "ref": "unsettled:query"}
    result = complete(request)
    assert result["consequence"]["result"] == "UNDETERMINED"
    assert result["candidates"][1]["query_decision"]["result"] == "UNSUPPORTED_QUERY"
    request = example()
    request["candidates"] = [{"id": str(i), "assertions": []} for i in range(501)]
    reply = run(request)
    assert reply["code"] == "refused" and reply["problems"] == ["resource_bound:design_bounds"]


def test_unresolved_observation_status_never_becomes_a_registry_assertion():
    request = example()
    request["observations"][0]["status"] = "proposed"
    result = complete(request)
    assert "at_least_3" in result["remaining"]
    assert result["candidates"][0]["observations"][0]["support"] == "proposed_refused"
    assert result["premises"]["observations"][0]["status"] == "proposed"


def test_a_common_negative_consequence_preserves_elimination_support():
    request = example()
    request["query"] = {"class": "Not", "part": request["query"]}
    result = complete(request)
    assert result["consequence"]["result"] == "REFUTED"
    assert result["consequence"]["status"] == "interpolated"
