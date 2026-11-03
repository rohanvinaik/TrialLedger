"""Estimand channels keep their own admission and support through the public boundary."""

import json
from copy import deepcopy

import pytest

from scripts.trace_reasoning_consumers import invoke
from TrialLedger.layer2 import run
from TrialLedger.layer2.estimand_evidence import EXAMPLES


def payload():
    return {
        "operation": "signals",
        "signals": [
            {
                "id": "endpoint-inputs",
                "kind": "estimand",
                "data": deepcopy(EXAMPLES["estimand"]),
                "support": [
                    {
                        "id": "declared-inputs",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["invented:explicit-declarations-not-trial-evidence"],
                    }
                ],
            }
        ],
    }


def complete(request):
    response = run(request)
    assert response["code"] == "complete", response
    assert all(
        row["completion"] != "unclassified" and row["disposition"] != "unclassified"
        for row in response["metadata"]["findings"]
    ), response
    return response


def available(data, status="known"):
    rule = deepcopy(data["requirements"][0]["rule"])
    rule.update(ref="invented:actual-input:" + status, status=status)
    return {"requirement": "week12", "mode": "observed", "state": "available", "rule": rule}


def test_plan_mismatch_does_not_hide_independently_available_input():
    request = payload()
    data = request["signals"][0]["data"]
    data["data_state"] = [available(data)]
    response = complete(request)
    actual = next(row for row in response["metadata"]["findings"] if row["kind"] == "estimand_actual_input")
    assert actual["logical_result"] == "available"
    assert actual["standing"] == "known"
    assert actual["causes"] == []
    assert response["result"]["signals"][0]["value"]["estimation"] == "not_computed"


def test_pending_relevance_does_not_poison_independent_availability():
    request = payload()
    data = request["signals"][0]["data"]
    data["data_state"] = [available(data)]
    data["requirements"][0]["rule"]["status"] = "proposed"
    data["definitions"]["summary"]["status"] = "proposed"
    response = complete(request)
    actual = next(row for row in response["metadata"]["findings"] if row["kind"] == "estimand_actual_input")
    assert actual["logical_result"] == "available" and actual["standing"] == "known"
    assert actual["disposition"] == "settled" and actual["causes"] == []


def test_redundant_weaker_availability_support_preserves_known_fact():
    request = payload()
    data = request["signals"][0]["data"]
    data["data_state"] = [available(data), available(data, "interpolated")]
    data["data_state"][1]["state"] = "unknown"
    response = complete(request)
    actual = next(row for row in response["metadata"]["findings"] if row["kind"] == "estimand_actual_input")
    assert actual["standing"] == "known"


def test_irrelevant_collection_plan_does_not_need_confirmation():
    request = payload()
    data = request["signals"][0]["data"]
    data["requirements"][0]["relevance"] = "not_required_for_this_estimand"
    data["collection_plan"] = []
    response = complete(request)
    plan = next(
        row for row in response["metadata"]["findings"] if row["kind"] == "estimand_collection_alignment"
    )
    assert plan["logical_result"] == "aligned" and plan["standing"] == "known"


def test_outer_proposal_gates_locals_even_when_aggregate_was_already_unresolved():
    request = payload()
    data = request["signals"][0]["data"]
    data["data_state"] = [available(data)]
    request["signals"][0]["support"][0]["status"] = "proposed"
    response = complete(request)
    signal = response["result"]["signals"][0]
    assert signal["calculation_code"] == signal["code"] == "unresolved"
    assert signal["admission"]["code"] == "proposed_refused"
    assert all(row["logical_result"] == "unresolved" for row in response["metadata"]["findings"])
    assert any(row.get("raw_result") == "available" for row in response["metadata"]["findings"])


def test_empty_requirements_are_inspection():
    request = payload()
    request["signals"][0]["data"].update(requirements=[], collection_plan=[])
    assert complete(request)["metadata"]["kind"] == "inspection"


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_actual_transports_preserve_separate_requirement_channels(mode, tmp_path):
    request = payload()
    assert invoke(request, mode, tmp_path) == json.loads(json.dumps(complete(request)))
