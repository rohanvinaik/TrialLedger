"""Stage warrants reach every ordinary and hypothetical consumer without identity promotion."""

from copy import deepcopy

import pytest

from TrialLedger.layer2 import run
from TrialLedger.layer2.stage_evidence import EXAMPLES


def payload():
    return {
        "operation": "signals",
        "signals": [
            {
                "id": "pathway",
                "kind": "stages",
                "data": deepcopy(EXAMPLES["stages"]),
                "support": [
                    {
                        "id": "counts",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["invented:explicit-test-premise"],
                    }
                ],
            }
        ],
    }


def complete(request):
    response = run(request)
    assert response["code"] == "complete", response
    return response


def test_local_interpretation_standing_reaches_public_result():
    request = payload()
    before = deepcopy(request)
    response = complete(request)
    assert request == before
    row = response["result"]["signals"][0]
    assert row["status"] == "interpolated"
    assert row["operator_support"]["status"] == "interpolated"
    assert all(finding["standing"] == "interpolated" for finding in response["metadata"]["findings"])


def test_independent_known_edge_metadata_does_not_inherit_other_edge_uncertainty():
    request = payload()
    data = request["signals"][0]["data"]
    known = deepcopy(data["transitions"][0])
    known.update(id="known-relation", status="known")
    data["transitions"].append(known)
    response = complete(request)
    assert response["result"]["signals"][0]["status"] == "interpolated"
    rows = response["result"]["signals"][0]["value"]["transitions"]
    known_index = next(index for index, row in enumerate(rows) if row["id"] == known["id"])
    finding = next(
        row
        for row in response["metadata"]["findings"]
        if row["path"] == f"/result/signals/0/value/transitions/{known_index}"
    )
    assert finding["standing"] == "known"


@pytest.mark.parametrize("mode", ["proposed", "wrong_unit", "wrong_scope", "unknown_count"])
def test_pending_scope_or_meaning_never_becomes_a_clinical_conflict(mode):
    request = payload()
    data = request["signals"][0]["data"]
    data["stages"][1]["total"] = 499
    if mode == "proposed":
        data["transitions"][0]["status"] = "proposed"
    elif mode == "wrong_unit":
        data["stages"][1]["unit"] = "person-period"
    elif mode == "wrong_scope":
        data["transitions"][0]["scope"]["target_time"] = "another-event"
    else:
        data["stages"][0]["total"] = None
    response = complete(request)
    assert response["result"]["signals"][0]["code"] == "unresolved"
    assert all(
        row["disposition"] not in ("settled", "conflict", "unclassified")
        for row in response["metadata"]["findings"]
    )


def test_proposed_outer_support_gates_inner_metadata():
    request = payload()
    request["signals"][0]["support"][0]["status"] = "proposed"
    response = complete(request)
    findings = response["metadata"]["findings"]
    assert all(row["logical_result"] == "unresolved" for row in findings)
    assert findings[-1]["raw_result"] == "bounded"


def test_empty_stage_graph_is_inspection():
    request = payload()
    request["signals"][0]["data"].update(stages=[], transitions=[])
    response = complete(request)
    assert response["metadata"] == {"version": 1, "kind": "inspection", "findings": []}


def design_request():
    request = payload()
    request.update(
        operation="design_bounds",
        study_ref="invented:runin-study",
        observations=[],
        candidates=[
            {
                "id": "everyone-progressed",
                "assertions": [],
                "signal_claims": [
                    {
                        "signal": "pathway",
                        "claim": {
                            "transition": "randomized-after-runin",
                            "count": "outside",
                            "lower": 0,
                            "upper": 0,
                        },
                    }
                ],
            },
            {
                "id": "fifty-eight-outside",
                "assertions": [],
                "signal_claims": [
                    {
                        "signal": "pathway",
                        "claim": {
                            "transition": "randomized-after-runin",
                            "count": "outside",
                            "lower": 58,
                            "upper": 58,
                        },
                    }
                ],
            },
        ],
        query={
            "class": "Literal",
            "subject": {"class": "Subject", "kind": "participant"},
            "predicate": {"class": "Predicate", "kind": "demographic", "key": "unrepresented-profile"},
            "value": {"class": "Value", "kind": "boolean"},
        },
    )
    return request


def test_candidate_elimination_uses_local_relation_support():
    response = complete(design_request())
    candidates = {row["id"]: row for row in response["result"]["candidates"]}
    assert candidates["everyone-progressed"]["state"] == "ruled_out"
    assert candidates["everyone-progressed"]["elimination_status"] == "interpolated"
    assert candidates["fifty-eight-outside"]["state"] == "not_ruled_out"


def test_hypothetical_frame_cannot_overwrite_inner_interpolated_support():
    signal = payload()["signals"][0]
    response = complete(
        {
            "operation": "interpretations",
            "study_ref": "invented:runin-study",
            "fixed": {"assertions": [], "signals": []},
            "interpretations": [
                {
                    "id": "pathway-reading",
                    "label": "Invented pathway reading",
                    "origin": "assistant",
                    "basis": ["invented:declared-reading"],
                    "assumptions": [],
                    "signals": [signal],
                    "signal_claims": [],
                    "binding_uses": [],
                }
            ],
            "queries": [{"id": "unrepresented", "body": design_request()["query"]}],
        }
    )
    assert response["result"]["interpretations"][0]["signals"][0]["status"] == "interpolated"


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_stages_reach_actual_public_transports(mode, tmp_path):
    import json

    from scripts.trace_reasoning_consumers import invoke

    request = design_request()
    assert invoke(request, mode, tmp_path) == json.loads(json.dumps(complete(request)))
