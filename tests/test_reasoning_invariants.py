"""Intent: independent information stays useful without promoting uncertain premises.

The all-example checks cover deterministic replay, source immutability and only
explicitly unordered inputs. The focused laws state their applicability below;
none assumes that a changed candidate family, denominator or default has the
monotonic semantics of adding a strict constraint.
"""

from __future__ import annotations

import copy
import itertools

import pytest

from tests.reasoning_invariant_cases import (
    OPERATIONS,
    assertion,
    encoded,
    example_cases,
    json_value,
    literal,
    permuted,
    runnable_objects,
    semantic_view,
)
from TrialLedger.layer2 import run

CASES = example_cases()
PARAMS = [pytest.param(label, payload, id=label) for label, payload in CASES]


def complete(payload):
    response = run(copy.deepcopy(payload))
    assert response["code"] == "complete", response
    return response


def guide(operation):
    return copy.deepcopy(complete({"operation": "describe", "view": operation})["result"]["example"])


def query_decisions(response):
    return {
        row["id"]: (row["result"], row["warrant"]["status"], sorted(row["warrant"]["blockers"]))
        for row in response["result"]["fixed"]["queries"]
    }


def test_inventory_covers_every_existing_operation_and_every_named_discovery_slot():
    assert {payload["operation"] for _, payload in CASES} == set(OPERATIONS)
    assert len({label for label, _ in CASES}) == len(CASES)
    # Discovery enumeration is checked against the whole returned guide in
    # example_cases. A new request-bearing slot cannot be silently omitted.
    assert any(label.startswith("examples/") for label, _ in CASES)
    assert all(
        any(label.startswith("describe/" + operation + "/") for label, _ in CASES) for operation in OPERATIONS
    )


def test_public_session_requests_are_atomic_and_include_the_focused_revision_slot():
    focus = complete({"operation": "describe", "view": "design_session"})["result"]
    current, revision = focus["example"], focus["revision_example"]
    declaration = current["session"]["analyses"][0]
    assert declaration["operation"] == "entailment"
    assert runnable_objects(declaration) == []
    assert (
        runnable_objects(
            {"operation": "design_session", "session": "session v1", "previous": "null or prior session"}
        )
        == []
    )
    assert runnable_objects(current) == [current]
    assert runnable_objects(revision) == [revision]
    assert any(
        label == "describe/design_session/revision_example" and payload == revision
        for label, payload in CASES
    )
    assert permuted(revision) == revision


@pytest.mark.parametrize(("label", "payload"), PARAMS)
def test_every_example_replays_without_mutating_its_premises(label, payload):
    original = copy.deepcopy(payload)
    first = run(payload)
    second = run(payload)
    assert payload == original, label
    assert json_value(first) == json_value(second), label
    assert first["code"] == "complete", (label, first["problems"])


@pytest.mark.parametrize(("label", "payload"), PARAMS)
def test_every_example_preserves_semantics_under_declared_unordered_permutation(label, payload):
    revised = permuted(payload)
    before, after = run(payload), run(revised)
    assert semantic_view(before) == semantic_view(after), label
    # Singleton/empty collections are the named identity-permutation case, not
    # evidence that a nontrivial reordering was exercised for that example.
    assert set(payload) == set(revised)


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        pytest.param(label, payload, id=label)
        for label, payload in CASES
        if payload["operation"] == "entailment"
    ],
)
def test_entailment_examples_keep_their_answer_under_consistent_independent_information(label, payload):
    revised = copy.deepcopy(payload)
    revised["assertions"].append(assertion("invariant-independent", literal("invariant:unrelated")))
    before, after = complete(payload), complete(revised)
    assert semantic_view(before) == semantic_view(after), label


@pytest.mark.parametrize("extra", ["independent", "tautology", "duplicate_support"])
def test_strict_completed_premise_addition_preserves_an_established_conclusion(extra):
    body = literal("invariant:age")
    payload = {"operation": "entailment", "assertions": [assertion("age", body)], "query": body}
    original = complete(payload)
    if extra == "independent":
        added = literal("invariant:unrelated")
    elif extra == "tautology":
        other = literal("invariant:other")
        added = {"class": "AnyOf", "parts": [other, {"class": "Not", "part": other}]}
    else:
        added = body
    payload["assertions"].append(assertion("extra", added))
    assert semantic_view(complete(payload)) == semantic_view(original)


def test_global_contradiction_is_an_explicit_exception_to_query_irrelevance():
    payload = {
        "operation": "entailment",
        "assertions": [assertion("age", literal("age"))],
        "query": literal("age"),
    }
    assert complete(payload)["result"]["decision"]["result"] == "ENTAILED"
    payload["assertions"] += [
        assertion("unrelated-low", literal("other", 0, "le")),
        assertion("unrelated-high", literal("other", 1, "ge")),
    ]
    assert complete(payload)["result"]["decision"]["result"] == "INCONSISTENT"


def test_global_work_limit_is_an_explicit_exception_to_query_irrelevance():
    payload = {
        "operation": "entailment",
        "assertions": [assertion("age", literal("age"))],
        "query": literal("age"),
        "bound": 9,
    }
    assert complete(payload)["result"]["decision"]["result"] == "ENTAILED"
    payload["assertions"] += [assertion("other-" + str(n), literal("other", n)) for n in range(6)]
    decision = complete(payload)["result"]["decision"]
    assert decision["result"] == "UNDETERMINED" and "resource_bound" in decision["blockers"]


def test_retraction_uses_fresh_premises_and_preserves_alternative_support():
    body, other = literal("age"), literal("other")
    premises = [assertion("age-a", body), assertion("age-b", body), assertion("other", other)]
    payload = {"operation": "entailment", "assertions": premises, "query": body}
    initial = complete(payload)
    assert initial["result"]["decision"]["result"] == "ENTAILED"
    # The minimal proof can name only one of age-a/age-b. Neither proof subset
    # is the complete dependency set for revisions of the submitted analysis.
    for removed in ("age-a", "age-b", "other"):
        revised = dict(payload, assertions=[p for p in premises if p["id"] != removed])
        assert complete(revised)["result"]["decision"]["result"] == "ENTAILED"
    no_age = dict(payload, assertions=[premises[-1]])
    assert complete(no_age)["result"]["decision"]["result"] == "UNDETERMINED"
    assert complete(payload) == initial


@pytest.mark.parametrize("status", ["known", "interpolated", "proposed"])
def test_entailment_weakening_support_never_promotes_a_conclusion(status):
    body = literal("age")
    response = complete(
        {"operation": "entailment", "assertions": [assertion("age", body, status)], "query": body}
    )
    decision = response["result"]["decision"]
    if status == "proposed":
        assert decision["result"] == "UNDETERMINED" and "proposed_refused:age" in decision["blockers"]
    else:
        assert decision["result"] == "ENTAILED" and decision["status"] == status


@pytest.mark.parametrize(
    "kind", list(run({"operation": "describe", "view": "signals"})["result"]["signal_examples"])
)
def test_each_signal_kind_retains_arithmetic_but_cannot_promote_weakened_support(kind):
    payload = copy.deepcopy(
        run({"operation": "describe", "view": "signals"})["result"]["signal_examples"][kind]
    )
    original = complete(payload)["result"]["signals"][0]
    for status in ("interpolated", "proposed"):
        revised = copy.deepcopy(payload)
        revised["signals"][0]["support"][0]["status"] = status
        row = complete(revised)["result"]["signals"][0]
        assert row["status"] == status
        assert row["calculation_code"] == original["calculation_code"]
        assert row["value"] == original["value"]
        if status == "proposed":
            assert row["code"] == "unresolved"


def test_independent_signal_addition_and_retraction_preserve_existing_calculations():
    examples = run({"operation": "describe", "view": "signals"})["result"]["signal_examples"]
    original = copy.deepcopy(examples["overlap"])
    before = semantic_view(complete(original))
    combined = copy.deepcopy(original)
    for kind in ("temporal", "regimen", "relations", "dependencies"):
        combined["signals"].append(copy.deepcopy(examples[kind]["signals"][0]))
    after = semantic_view(complete(combined))
    assert after[original["signals"][0]["id"]] == before[original["signals"][0]["id"]]
    assert semantic_view(complete(original)) == before


def test_design_elimination_is_local_to_its_support_and_candidate_family_is_explicit():
    payload = guide("design_bounds")
    before = semantic_view(complete(payload))
    unrelated = copy.deepcopy(
        run({"operation": "describe", "view": "signals"})["result"]["signal_examples"]["temporal"]["signals"][
            0
        ]
    )
    payload["signals"] = [unrelated]
    assert semantic_view(complete(payload)) == before
    payload["observations"][0]["bridge"]["status"] = "proposed"
    weaker = complete(payload)["result"]
    assert set(weaker["remaining"]) >= set(before["remaining"])
    assert all(
        row.get("elimination_status") != "known"
        for row in weaker["candidates"]
        if row["state"] == "ruled_out"
    )
    restored = guide("design_bounds")
    restored["candidates"].append({"id": "unrestricted-candidate", "assertions": []})
    assert complete(restored)["result"]["consequence"]["result"] == "UNDETERMINED"


@pytest.mark.parametrize(
    "targets,status",
    [
        (["treatment_adherence"], "known"),
        (["entry_eligibility", "treatment_adherence"], "known"),
        (["entry_eligibility"], "proposed"),
    ],
)
def test_attribution_ambiguity_compatible_under_every_reading_keeps_independent_eliminations(targets, status):
    description = run({"operation": "describe", "view": "design_bounds"})["result"]
    payload = copy.deepcopy(description["exception_example"])
    payload["observations"][0]["bridge"]["max_exceptions"] = 5
    baseline = copy.deepcopy(payload)
    del baseline["exception_evidence"]
    del baseline["observations"][0]["bridge"]["exception_evidence"]
    binding = payload["exception_evidence"]["bindings"][0]
    binding.update(possible_targets=targets, status=status)
    assert semantic_view(complete(payload)) == semantic_view(complete(baseline))


def test_interpretation_frames_preserve_independent_fixed_answer_on_local_retraction():
    payload = guide("interpretations")
    independent = assertion("invariant-fixed", literal("invariant:fixed"))
    payload["fixed"]["assertions"].append(independent)
    payload["queries"].append({"id": "invariant-fixed", "body": independent["body"]})
    before = query_decisions(complete(payload))
    revised = copy.deepcopy(payload)
    revised["interpretations"][0]["assumptions"] = []
    after = query_decisions(complete(revised))
    assert before == after
    assert after["invariant-fixed"][:2] == ("ENTAILED", "known")
    assert query_decisions(complete(payload)) == before


def test_coordinate_strict_narrowing_and_weakening_preserve_independent_dimensions():
    payload = guide("coordinates")
    biomarker = {
        "section": "inclusion",
        "concept": "biomarker:EGFR",
        "values": ["positive"],
        "scope": "",
        "ref": "invented:EGFR",
        "standing": {
            "status": "known",
            "resolution": "resolved",
            "basis": ["invented:explicit-test-premise"],
        },
    }
    payload["evidence"].append(biomarker)
    original = complete(payload)["result"]["coordinates"]
    for status in ("interpolated", "proposed"):
        revised = copy.deepcopy(payload)
        revised["evidence"][-1]["standing"]["status"] = status
        result = complete(revised)["result"]["coordinates"]
        assert set(result["selection:EGFR"]["domain"]) >= set(original["selection:EGFR"]["domain"])
        assert result["prior_advanced_lines"] == original["prior_advanced_lines"]
    for order in itertools.permutations(payload["evidence"]):
        revised = dict(payload, evidence=list(order))
        assert semantic_view(complete(revised)) == semantic_view(complete(payload))


def test_corpus_weakening_keeps_denominator_and_independent_feature_counts():
    payload: dict = {
        "operation": "corpus",
        "trials": [
            {
                "id": "invented-trial",
                "sponsor": "invented-sponsor",
                "stratum": "invented-cell",
                "typed": True,
                "elements": ["inclusion:age=adult", "inclusion:marker=positive"],
                "basis": ["invented:explicit-test-premise"],
                "standing": {
                    "status": "known",
                    "resolution": "resolved",
                    "basis": ["invented:explicit-test-premise"],
                },
            }
        ],
    }

    def rows(payload):
        return {row["element"]: row for row in complete(payload)["result"]["frequency"]}

    original = rows(payload)
    weakened = copy.deepcopy(payload)
    weakened["trials"][0]["feature_standings"] = {
        "elements": {
            "inclusion:marker=positive": {
                "status": "proposed",
                "resolution": "resolved",
                "basis": ["invented:unconfirmed-reading"],
            }
        }
    }
    revised = rows(weakened)
    assert revised["inclusion:age=adult"] == original["inclusion:age=adult"]
    marker = revised["inclusion:marker=positive"]
    assert marker["stating"] == 0 and marker["pending_stating"] == 1 and marker["trials"] == 1
    assert marker["lower"] <= original["inclusion:marker=positive"]["lower"]
    assert marker["upper"] >= original["inclusion:marker=positive"]["upper"]
    assert rows(payload) == original


def test_semantic_projection_preserves_bounds_and_does_not_sort_interval_endpoints():
    payload = guide("signals")
    original = complete(payload)
    changed = copy.deepcopy(original)
    value = changed["result"]["signals"][0]["value"]
    value["invariant-deliberately-changed-endpoints"] = [2, 1]
    assert semantic_view(changed) != semantic_view(original)
    assert encoded([2, 1]) != encoded([1, 2])


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        pytest.param(label, payload, id=label)
        for label, payload in CASES
        if payload["operation"] == "design_bounds"
    ],
)
def test_every_design_example_retains_candidate_consequences_with_duplicate_observation_support(
    label, payload
):
    revised = copy.deepcopy(payload)
    original_observation = revised["observations"][0]
    duplicate = copy.deepcopy(original_observation)
    duplicate["id"] = "invariant-duplicate-observation"
    revised["observations"].append(duplicate)
    before = semantic_view(complete(payload))
    after = semantic_view(complete(revised))
    assert before["remaining"] == after["remaining"], label
    assert before["consequence"]["result"] == after["consequence"]["result"], label
    assert before["consequence"]["status"] == after["consequence"]["status"], label
    original_blockers = before["consequence"]["blockers"] or []
    expected_blockers = set(original_blockers)
    for blocker in original_blockers:
        if blocker == "exception_bridge_conflict:" + original_observation["id"]:
            expected_blockers.add("exception_bridge_conflict:" + duplicate["id"])
    assert set(after["consequence"]["blockers"] or []) == expected_blockers, label
    assert {
        key: (row["state"], row["standing"], row["query"]) for key, row in before["candidates"].items()
    } == {key: (row["state"], row["standing"], row["query"]) for key, row in after["candidates"].items()}, (
        label
    )


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_invariant_examples_reach_real_entry_points_without_transport_promotion(operation, mode, tmp_path):
    from scripts.trace_reasoning_consumers import invoke

    payload = guide(operation)
    before = copy.deepcopy(payload)
    direct = complete(payload)
    transported = invoke(payload, mode, tmp_path)
    assert payload == before
    assert transported == json_value(direct)
    assert semantic_view(transported) == semantic_view(direct)
