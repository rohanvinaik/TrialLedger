"""Public evidence-to-witness-to-consequence contracts, including negative-sign boundaries."""

import copy
import json

import pytest

from TrialLedger import cli
from TrialLedger.layer2 import bounds_guide, exception_guide, run, signals_guide


def answer(request):
    response = run(request)
    assert response["code"] == "complete", response
    assert all(row["completion"] != "unclassified" for row in response["metadata"]["findings"])
    assert all(row["disposition"] != "unclassified" for row in response["metadata"]["findings"])
    return response["result"]


def test_floor_conflict_blocks_dependent_elimination_and_keeps_conditional_warrants():
    request = exception_guide.example()
    before = copy.deepcopy(request)
    result = answer(request)
    check = result["exception_checks"][0]
    assert (check["lower"], check["upper"], check["status"]) == (1, 0, "interpolated")
    assert result["consequence"]["result"] == "CONFLICT"
    assert result["consequence"]["status"] == "interpolated"
    assert result["candidates"][0]["state"] == "unresolved"
    assert check["id"] == result["candidates"][0]["observations"][0]["exception_check"]
    assert "exception_bridge_conflict:score_2" in result["consequence"]["blockers"]
    assert request == before


def test_wrong_arm_attribution_conflict_must_not_weaken_independent_known_conflict():
    request = exception_guide.example()
    bridge = request["observations"][0]["bridge"]
    bridge["status"] = "known"
    first = request["exception_evidence"]["bindings"][0]
    first["status"] = "known"
    for target in ("entry_eligibility", "assessment_adherence"):
        binding = copy.deepcopy(first)
        binding.update(id=target, status="interpolated", possible_targets=[target])
        binding["scope"]["arm"] = "other"
        request["exception_evidence"]["bindings"].append(binding)
        bridge["exception_evidence"]["bindings"].append(target)
    result = answer(request)
    assert result["exception_checks"][0]["code"] == "conflict"
    assert result["exception_checks"][0]["status"] == "known"
    assert result["exception_checks"][0]["attributions"][1]["applicable"] is False
    assert result["consequence"]["status"] == "known"


def test_global_failure_must_not_be_located_in_a_profile_without_a_binding():
    request = exception_guide.example()
    witness = request["observations"][0]
    witness["bridge"]["exception_evidence"].update(extent="profile", profile=witness["body"])
    result = answer(request)
    assert result["exception_checks"][0]["lower"] == 0
    assert result["exception_checks"][0]["contributions"][0]["transfer"] == "no_local_floor"
    assert result["candidates"][0]["state"] == "ruled_out"
    assert result["consequence"]["status"] == "interpolated"


@pytest.mark.parametrize("cap,state", [(48, "ruled_out"), (49, "not_ruled_out"), (None, "unresolved")])
def test_threshold_and_unknown_ceiling_propagate_to_candidates(cap, state):
    request = exception_guide.example()
    request["observations"][0]["count"] = 49
    request["observations"][0]["bridge"]["max_exceptions"] = cap
    result = answer(request)
    candidate = result["candidates"][0]
    assert candidate["state"] == state
    assert candidate["observations"][0]["witness_threshold"]["maximum_exceptions_for_witness"] == 48
    assert result["exception_checks"][0]["upper"] == cap
    if cap is None:
        assert result["consequence"]["result"] == "UNDETERMINED"
        assert "exception_upper_unknown" in candidate["observations"][0]["decision"]["blockers"]


@pytest.mark.parametrize(
    "change,blocker",
    [
        ("proposed", "binding_proposed:entry-reading"),
        ("wrong_arm", "scope_mismatch:entry-reading"),
        ("broad", "missing_entry_attribution:entry-reading"),
    ],
)
def test_unwarranted_exception_application_keeps_counts_without_using_them(change, blocker):
    request = exception_guide.example()
    binding = request["exception_evidence"]["bindings"][0]
    if change == "proposed":
        binding["status"] = "proposed"
    elif change == "wrong_arm":
        binding["scope"]["arm"] = "other"
    else:
        binding["possible_targets"].append("assessment_adherence")
    result = answer(request)
    assert result["exception_checks"][0]["contributions"][0]["reported_lower"] == 1
    assert result["exception_checks"][0]["code"] == "unresolved"
    assert blocker in result["candidates"][0]["observations"][0]["decision"]["blockers"]
    assert result["consequence"]["result"] == "UNDETERMINED"


def test_rejection_budget_must_not_consume_entry_ineligibility_floor():
    request = exception_guide.example()
    request["observations"][0]["direction"] = "rejected"
    result = answer(request)
    check = result["exception_checks"][0]
    assert check["code"] == "unresolved" and check["lower"] is None
    assert check["positive_budget_check"]["lower"] == 1
    assert check["positive_budget_check"]["code"] == "conflict"
    assert result["consequence"]["result"] == "UNDETERMINED"
    assert all(c["state"] == "unresolved" for c in result["candidates"])


@pytest.mark.parametrize(
    "targets,status,cap,code,state",
    [
        (["treatment_adherence"], "known", 5, "consistent", "ruled_out"),
        (["treatment_adherence"], "known", 0, "consistent", "ruled_out"),
        (["entry_eligibility", "treatment_adherence"], "known", 5, "consistent", "ruled_out"),
        (["entry_eligibility"], "proposed", 5, "consistent", "ruled_out"),
        (["entry_eligibility", "treatment_adherence"], "known", 0, "unresolved", "unresolved"),
        (["entry_eligibility"], "proposed", 0, "unresolved", "unresolved"),
    ],
)
def test_only_material_attribution_uncertainty_can_block_an_independently_supplied_cap(
    targets, status, cap, code, state
):
    request = exception_guide.example()
    request["exception_evidence"]["bindings"][0].update(possible_targets=targets, status=status)
    request["observations"][0]["bridge"]["max_exceptions"] = cap
    result = answer(request)
    check = result["exception_checks"][0]
    assert check["code"] == code
    assert result["candidates"][0]["state"] == state
    assert check["lower"] == 0
    assert check["upper"] == cap  # supplied ceiling, never inferred from the count
    assert check["contributions"][0]["reported_lower"] == 1
    assert check["contributions"][0]["status"] == status
    if code == "consistent":
        assert check["blockers"] == []
        assert result["consequence"]["result"] == "ENTAILED"
        assert result["consequence"]["status"] == "interpolated"
    else:
        assert check["possible_floor_upper"] == 1
        assert check["interval_state"] == "attribution_dependent"


def test_proposed_bridge_exposes_conflict_if_adopted_without_admitting_it():
    request = exception_guide.example()
    request["observations"][0]["bridge"]["status"] = "proposed"
    result = answer(request)
    check = result["exception_checks"][0]
    assert check["code"] == "unresolved"
    assert check["conditional_lower"] == 1
    assert check["conditional_interval_state"] == "ceiling_conflict"
    assert result["consequence"]["result"] == "UNDETERMINED"


def test_retracting_conflicting_attribution_restores_only_its_warranted_consequences():
    request = exception_guide.example()
    binding = copy.deepcopy(request["exception_evidence"]["bindings"][0])
    binding.update(id="assessment", possible_targets=["assessment_adherence"])
    request["exception_evidence"]["bindings"].append(binding)
    ids = request["observations"][0]["bridge"]["exception_evidence"]["bindings"]
    ids.append("assessment")
    result = answer(request)
    assert result["exception_checks"][0]["code"] == "attribution_conflict"
    assert result["exception_checks"][0]["lower"] is None
    assert result["consequence"]["result"] == "CONFLICT"
    ids.remove("assessment")
    request["observations"][0]["bridge"]["max_exceptions"] = 1
    revised = answer(request)
    assert revised["exception_checks"][0]["code"] == "consistent"
    assert revised["candidates"][0]["state"] == "ruled_out"
    assert revised["consequence"]["status"] == "interpolated"


def population_request(parent=609, subset=590):
    request = signals_guide.example("population")
    signal = request["signals"][0]
    signal["data"].update(total=parent, universe="same-arm", parent_ref="parent")
    signal["data"]["subset"].update(ref="subset", universe="same-arm", lower=subset, upper=subset)
    scope = {
        "study": "invented:study",
        "version": "v1",
        "arm": "A",
        "time": "entry",
        "population": "same-arm",
    }
    request.update(
        study_ref="invented:study",
        bindings=[
            {
                "id": "population",
                "kind": "population",
                "relation": "subset_of",
                "subjects": ["parent", "subset"],
                "scope": scope.copy(),
                "sources": [{"ref": "invented:counts", "version": "v1", "address": "/counts"}],
                "status": "known",
                "resolution": "resolved",
                "basis": ["invented:accepted-scope-reading"],
            }
        ],
        binding_uses=[{"binding": "population", "signal": signal["id"], "scope": scope.copy()}],
    )
    return request


@pytest.mark.parametrize("parent,subset,code", [(609, 590, "bounded"), (590, 609, "conflict")])
def test_population_direction_uses_the_declared_relation(parent, subset, code):
    result = answer(population_request(parent, subset))
    assert result["signals"][0]["code"] == code
    assert result["binding_checks"][0]["code"] == "supported"


@pytest.mark.parametrize("change", ["arm", "version", "proposed"])
def test_wrong_population_scope_and_pending_reading_must_not_refute_clinical_design(change):
    request = population_request(590, 609)
    if change == "proposed":
        request["bindings"][0]["status"] = "proposed"
    else:
        request["binding_uses"][0]["scope"][change] = "other"
    result = answer(request)
    assert result["signals"][0]["calculation_code"] == "conflict"
    assert result["signals"][0]["code"] == "unresolved"
    assert result["binding_checks"][0]["blockers"]
    assert result["binding_premises"]["binding_uses"] == request["binding_uses"]


@pytest.mark.parametrize(
    "payload", [exception_guide.example(), population_request(), population_request(590, 609)]
)
def test_real_cli_mcp_parity(payload, tmp_path, capsys):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(payload))
    assert cli.main(["reason", "--request", str(path)]) == 0
    output = json.loads(capsys.readouterr().out)
    lines = [
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            }
        ).encode(),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "reason", "arguments": {"request": payload}},
            }
        ).encode(),
    ]
    written = []
    assert cli.main(["mcp", "--root", str(tmp_path)], mcp_streams=(lines, written.append)) == 0
    mcp = json.loads(json.loads(written[-1])["result"]["content"][0]["text"])
    mcp.pop("tool")
    assert mcp == output


def test_legacy_missing_or_null_ceiling_is_still_refused():
    request = bounds_guide.example()
    request["observations"][0]["bridge"]["max_exceptions"] = None
    assert run(request)["code"] == "refused"
