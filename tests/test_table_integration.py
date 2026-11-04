"""Finite-table findings reach real consumers without promoting an unaccepted table."""

import json
from copy import deepcopy

import pytest

from scripts.trace_reasoning_consumers import invoke
from TrialLedger.layer2 import run
from TrialLedger.layer2.decision_tables import EXAMPLES


def payload():
    return {
        "operation": "signals",
        "signals": [
            {
                "id": "dose-actions",
                "kind": "decision_table",
                "data": deepcopy(EXAMPLES["decision_table"]),
                "support": [
                    {
                        "id": "table-reading",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["invented:explicit-table-not-clinical-evidence"],
                    }
                ],
            }
        ],
    }


def complete(request):
    response = run(request)
    assert response["code"] == "complete", response
    assert all(
        finding["completion"] != "unclassified" and finding["disposition"] != "unclassified"
        for finding in response["metadata"]["findings"]
    ), response
    return response


def test_table_is_discovered_and_preserves_inputs():
    request = payload()
    before = deepcopy(request)
    response = complete(request)
    assert request == before
    assert response["result"]["signals"][0]["code"] == "consistent"
    assert {row["kind"] for row in response["metadata"]["findings"]} >= {
        "table_domain",
        "table_coverage",
        "table_actions",
        "table_overlaps",
    }
    guide = run({"operation": "describe", "view": "signals", "detail": "full"})
    assert "decision_table" in guide["result"]["signal_kinds"]


def test_known_coverage_gap_survives_independent_unfinished_checks():
    request = payload()
    data = request["signals"][0]["data"]
    data["rows"][0]["when"] = data["domains"][0]["values"][0]
    data["limits"]["solver_calls"] = 2
    response = complete(request)
    findings = response["metadata"]["findings"]
    coverage = next(row for row in findings if row["kind"] == "table_coverage")
    assert coverage["logical_result"] == "gap"
    assert coverage["disposition"] == "conflict"
    assert coverage["completion"] == "complete"
    assert any(row["disposition"] == "not_computed" for row in findings)


@pytest.mark.parametrize("status", ["proposed", "interpolated"])
def test_outer_support_cannot_be_promoted_by_exact_table_arithmetic(status):
    request = payload()
    request["signals"][0]["support"][0]["status"] = status
    response = complete(request)
    assert all(row["standing"] == status for row in response["metadata"]["findings"])
    if status == "proposed":
        assert all(row["logical_result"] == "unresolved" for row in response["metadata"]["findings"])
        assert any(row.get("raw_result") == "covered" for row in response["metadata"]["findings"])
    else:
        assert all(row["disposition"] == "conditional" for row in response["metadata"]["findings"])


def test_same_action_overlap_is_descriptive():
    request = payload()
    data = request["signals"][0]["data"]
    data["rows"].append(
        {"id": "duplicate-one", "when": data["domains"][0]["values"][1], "action": "escalate"}
    )
    response = complete(request)
    assert response["result"]["signals"][0]["code"] == "consistent"
    assert any(
        row["kind"] == "table_overlaps" and row["disposition"] == "descriptive"
        for row in response["metadata"]["findings"]
    )


def test_equal_unresolved_aggregate_codes_do_not_hide_outer_refusal():
    request = payload()
    request["signals"][0]["data"]["limits"]["solver_calls"] = 2
    request["signals"][0]["support"][0]["status"] = "proposed"
    response = complete(request)
    signal = response["result"]["signals"][0]
    assert signal["code"] == signal["calculation_code"] == "unresolved"
    assert all(row["logical_result"] == "unresolved" for row in response["metadata"]["findings"])
    assert any(row.get("raw_result") == "covered" for row in response["metadata"]["findings"])


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_table_reaches_actual_public_transports(mode, tmp_path):
    request = payload()
    assert invoke(request, mode, tmp_path) == json.loads(json.dumps(complete(request)))
