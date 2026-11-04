"""Public investigation requests preserve hypothetical standing and bounded session handoffs."""

import json
from copy import deepcopy

import pytest

from scripts.trace_reasoning_consumers import invoke
from TrialLedger.layer2 import design_session_guide, evidence_requests_guide, run


def session_request():
    session = deepcopy(design_session_guide.EXAMPLE)
    request = evidence_requests_guide.example()
    candidates = request.pop("candidates")
    request.update(bound=32, limits={"max_decisions": 100})
    session["session"].update(
        premises=[
            {
                "id": candidate["id"],
                "kind": "candidate",
                "payload": candidate,
                "origin": {
                    "kind": "hypothesis",
                    "ref": "invented:candidate:" + candidate["id"],
                    "source": None,
                    "analysis": None,
                },
                "depends_on": [],
            }
            for candidate in candidates
        ],
        decisions=[],
    )
    session["session"]["analyses"] = [
        {
            "id": "seek-evidence",
            "operation": "evidence_requests",
            "target": session["session"]["target"],
            "parameters": {key: value for key, value in request.items() if key != "operation"},
            "uses": [
                {"premise": candidate["id"], "slot": "candidates", "projection": "identity"}
                for candidate in candidates
            ],
        }
    ]
    return session


def test_discovery_lists_exact_result_fields_and_hypothetical_rows():
    description = run({"operation": "describe", "view": "evidence_requests", "detail": "full"})["result"]
    request = description["example"]
    before = deepcopy(request)
    response = run(request)
    assert response["code"] == "complete", response
    assert request == before
    assert set(description["result_guide"]["fields"]) == set(response["result"])
    findings = response["metadata"]["findings"]
    assert all(row["completion"] != "unclassified" for row in findings)
    assert all(row["disposition"] != "unclassified" for row in findings)
    rows = [row for row in findings if row["kind"] == "hypothetical_evidence_request"]
    assert rows and all(row["hypothetical"] and row["disposition"] == "open" for row in rows)
    for row in response["result"]["requests"]:
        assert not set(row) & {"count", "bridge", "basis", "status"}


def test_row_budget_and_complete_envelope_budget_are_distinct():
    request = evidence_requests_guide.example()
    request["limits"] = {"max_bytes": 1}
    response = run(request)
    assert response["code"] == "complete", response
    assert response["result"]["requests"] == []
    assert response["result"]["output"]["omitted"] > 0
    assert response["result"]["search"]["state"] == "complete"
    request["limits"]["max_response_bytes"] = 1
    response = run(request)
    assert response["code"] == "refused"
    assert response["problems"] == ["resource_bound:evidence_requests:response_bytes"]


@pytest.mark.parametrize("bad", [2**53 + 1, float("nan"), float("inf")])
def test_unsupported_numeric_precision_never_changes_comparison_cells(bad):
    request = evidence_requests_guide.example()
    request["variables"][0]["domain"].update(minimum=bad, maximum=bad)
    response = run(request)
    assert response["code"] == "refused"
    assert response["problems"][0].endswith("exact_number_required") or response["problems"] == [
        "nonfinite_json:evidence_requests"
    ]


def test_session_projects_candidates_and_reserves_actual_witness_work():
    request = session_request()
    before = deepcopy(request)
    response = run(request)
    assert response["code"] == "complete", response
    assert request == before
    child = response["result"]["analyses"][0]
    assert child["result"] == run(child["request"])
    assert response["work"]["solver_work_reserved"] == 217600
    assert len(child["dependencies"]) == 2
    assert all(row["origin"]["kind"] == "hypothesis" for row in response["result"]["effective_premises"])
    request["session"]["limits"]["max_solver_work"] = 1
    refused = run(request)
    assert refused["code"] == "refused" and "resource_bound" in refused["problems"][0]


def test_session_refuses_raw_candidates_bypassing_the_projection_ledger():
    request = session_request()
    request["session"]["analyses"][0]["parameters"]["candidates"] = []
    response = run(request)
    assert response["code"] == "refused"
    assert response["problems"] == ["projected_slot_collision:seek-evidence"]


@pytest.mark.parametrize("mode", ["cli", "mcp"])
@pytest.mark.parametrize("submitted", [evidence_requests_guide.example(), session_request()])
def test_public_transports_preserve_complete_investigation_handoff(mode, submitted, tmp_path):
    response = run(submitted)
    assert response["code"] == "complete", response
    assert invoke(submitted, mode, tmp_path) == json.loads(json.dumps(response))
