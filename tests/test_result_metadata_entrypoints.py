"""Per-finding epistemic and operational state survives actual CLI/MCP handoffs."""

from __future__ import annotations

import copy

import pytest

from scripts.trace_reasoning_consumers import invoke
from TrialLedger.layer2.interpretations_guide import frame, premise, quantity
from TrialLedger.layer2.source_assertions_guide import example as source_example


def mixed_request():
    """Invented premises distinguish a fixed fact from two different unresolved readings."""
    adult = premise("adult", quantity("age", "ge", 18, "Years"))
    adult["status"] = "known"
    literals = [
        {
            "class": "Literal",
            "subject": {"class": "Subject", "kind": "participant"},
            "predicate": {"class": "Predicate", "kind": "exposure", "key": f"invented-{i}"},
            "value": {"class": "Value", "kind": "boolean"},
        }
        for i in range(8)
    ]
    unresolved = premise("unclear-PS", quantity("ECOG", "le", 2, "ECOG"))
    unresolved["resolution"] = "unresolved"
    return {
        "operation": "interpretations",
        "study_ref": "invented:metadata-intent-case",
        "fixed": {"assertions": [adult], "signals": []},
        "interpretations": [
            frame(
                "limited",
                "An invented conjunction beyond the chosen limit",
                [premise("large", {"class": "AllOf", "parts": literals})],
            ),
            frame("unresolved", "A reading whose PS restriction is unsettled", [unresolved]),
        ],
        "queries": [
            {"id": "adult", "body": quantity("age", "ge", 18, "Years")},
            {"id": "PS", "body": quantity("ECOG", "le", 2, "ECOG")},
        ],
        "bound": 10,
    }


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_mixed_results_keep_fixed_answers_and_both_open_causes(mode, tmp_path):
    request = mixed_request()
    before = copy.deepcopy(request)
    response = invoke(request, mode, tmp_path)
    assert request == before
    assert response["code"] == "complete"
    findings = {row["path"]: row for row in response["metadata"]["findings"]}
    fixed = findings["/result/fixed/queries/0"]
    assert fixed["logical_result"] == "ENTAILED"
    assert fixed["disposition"] == "settled"
    limited = findings["/result/interpretations/0"]
    assert limited["completion"] == "limited"
    assert limited["disposition"] == "not_computed"
    gated = findings["/result/interpretations/1/queries/0"]
    assert gated["logical_result"] == "UNDETERMINED"
    assert gated["raw_result"] == "ENTAILED"
    assert gated["disposition"] != "settled"
    assert {cause["kind"] for cause in gated["causes"]} == {"premise"}
    common = findings["/result/consequences/1"]
    assert {cause["kind"] for cause in common["causes"]} >= {"computation", "premise"}
    assert not any(row["disposition"] == "design_choice" for row in findings.values())


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_more_computation_changes_completion_without_claiming_new_evidence(mode, tmp_path):
    request = mixed_request()
    request = {
        "operation": "entailment",
        "assertions": request["fixed"]["assertions"],
        "query": request["queries"][0]["body"],
        "bound": 1,
    }
    limited = invoke(request, mode, tmp_path)
    request["bound"] = 100
    settled = invoke(request, mode, tmp_path)
    assert limited["metadata"]["findings"][0]["completion"] == "limited"
    assert settled["metadata"]["findings"][0]["completion"] == "complete"
    assert settled["result"]["decision"]["proof"] == ["adult"]
    assert settled["metadata"]["findings"][0]["disposition"] == "settled"


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_discovery_and_empty_source_inspection_do_not_certify_a_design(mode, tmp_path):
    discovery = invoke({"operation": "describe"}, mode, tmp_path)
    assert discovery["metadata"] == {"version": 1, "kind": "discovery", "findings": []}
    request = source_example()
    request["queries"] = []
    inspected = invoke(request, mode, tmp_path)
    assert inspected["metadata"] == {"version": 1, "kind": "inspection", "findings": []}
    assert inspected["result"]["analyses"] == []


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_source_metadata_points_to_the_actual_nested_effective_answer(mode, tmp_path):
    request = source_example()
    response = invoke(request, mode, tmp_path)
    metadata = response["metadata"]
    assert metadata["kind"] == "reasoning"
    assert metadata["findings"]
    for row in metadata["findings"]:
        assert row["path"].startswith("/result/analyses/")
        cursor = response
        for token in row["path"].split("/")[1:]:
            key = token.replace("~1", "/").replace("~0", "~")
            cursor = cursor[int(key)] if isinstance(cursor, list) else cursor[key]
        assert isinstance(cursor, dict)
