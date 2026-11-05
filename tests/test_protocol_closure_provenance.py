"""A receipt retains adoption provenance across exactly the objects that gate its check.

These invented plans come from public discovery and preparation. A stale adoption withholds its own
application; retaining its original premise id never repairs or promotes that application.
"""

import copy
import json
import subprocess

from tests.test_protocol_mcp_lifecycle import CLI, ROOT, McpClient
from TrialLedger.layer2 import run


def plan() -> dict:
    card = run({"operation": "describe", "view": "protocol", "detail": "full"})
    prepared = run(copy.deepcopy(card["result"]["examples"]["estimand"]))
    assert prepared["code"] == "complete", prepared.get("problems")
    return prepared["result"]["request"]


def object_of(request: dict, identity: str) -> dict:
    return next(o for o in request["session"]["protocol"]["objects"] if o["id"] == identity)


def child_of(reply: dict, check: str = "estimand-check") -> dict:
    assert reply["code"] == "complete", reply.get("problems")
    declared = next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == check)
    return declared["children"][0]


def add_baseline(request: dict, *, stale: bool) -> str:
    baseline = copy.deepcopy(object_of(request, "score"))
    baseline["id"] = "baseline-score"
    baseline["version"] = "invented-v2" if stale else "invented-v1"
    premise_id = "adopt:baseline-score:invented-v1"
    baseline["support"] = [premise_id]
    request["session"]["protocol"]["objects"].append(baseline)
    score = object_of(request, "score")
    score["data"]["baseline"] = baseline["id"]
    score["depends_on"].append(baseline["id"])
    adopted = copy.deepcopy(request["session"]["premises"][0])
    adopted["id"] = premise_id
    adopted["payload"]["objects"] = [{"id": baseline["id"], "version": "invented-v1"}]
    request["session"]["premises"].append(adopted)
    return premise_id


def test_a_stale_linked_assessment_keeps_its_original_adoption_in_the_receipt():
    request = plan()
    assessment = object_of(request, "week12")
    original = assessment["support"][0]
    assessment["version"] = "invented-v2"

    child = child_of(run(request))

    assert original in child["receipt"]["premises"]
    assert "week12" in child["receipt"]["closure"]
    stale = "stale_adoption:week12:" + original
    support = {row["id"]: row for row in child["request"]["signals"][0]["support"]}
    assert support[stale]["resolution"] == "unresolved"
    assert "premise:" + original not in support
    assert child["signals"][0]["admission"]["code"] == "binding_unresolved"


def test_current_closure_premises_keep_their_first_consumed_order():
    request = plan()
    child = child_of(run(request))

    assert child["receipt"]["closure"] == ["week-policy", "week12-collection", "week12", "score"]
    assert child["receipt"]["premises"] == [
        "adopt:week-policy:invented-v1",
        "adopt:week12-collection:invented-v1",
        "adopt:week12:invented-v1",
        "adopt:score:invented-v1",
    ]
    assert child["signals"][0]["admission"]["code"] == "accepted"


def test_a_stale_nested_baseline_keeps_its_original_adoption_in_the_receipt():
    request = plan()
    original = add_baseline(request, stale=True)

    child = child_of(run(request))

    assert child["receipt"]["closure"][-1] == "baseline-score"
    assert child["receipt"]["premises"][-1] == original
    assert child["signals"][0]["admission"]["code"] == "binding_unresolved"
    stale = "stale_adoption:baseline-score:" + original
    assert stale in {row["id"] for row in child["receipt"]["role_support"]["estimand"]}


def test_a_shared_adoption_of_two_stale_linked_objects_is_retained_once_without_merging_applications():
    request = plan()
    original = "adopt:assessment-and-score:invented-v1"
    adopted = copy.deepcopy(request["session"]["premises"][0])
    adopted["id"] = original
    adopted["payload"]["objects"] = [
        {"id": "week12", "version": "invented-v1"},
        {"id": "score", "version": "invented-v1"},
    ]
    request["session"]["premises"].append(adopted)
    for identity in ("week12", "score"):
        item = object_of(request, identity)
        item["support"] = [original]
        item["version"] = "invented-v2"

    child = child_of(run(request))

    assert child["receipt"]["premises"].count(original) == 1
    support = {row["id"]: row for row in child["request"]["signals"][0]["support"]}
    for identity in ("week12", "score"):
        assert support[f"stale_adoption:{identity}:{original}"]["resolution"] == "unresolved"
    assert "premise:" + original not in support
    assert child["signals"][0]["admission"]["code"] == "binding_unresolved"


def test_an_unrelated_stale_object_never_enters_the_receipt_or_changes_the_child():
    request = plan()
    expected = child_of(run(copy.deepcopy(request)))
    unrelated = copy.deepcopy(object_of(request, "score"))
    unrelated["id"] = "unrelated-score"
    unrelated["version"] = "invented-v2"
    original = "adopt:unrelated-score:invented-v1"
    unrelated["support"] = [original]
    request["session"]["protocol"]["objects"].append(unrelated)
    adopted = copy.deepcopy(request["session"]["premises"][0])
    adopted["id"] = original
    adopted["payload"]["objects"] = [{"id": unrelated["id"], "version": "invented-v1"}]
    request["session"]["premises"].append(adopted)

    actual = child_of(run(request))

    assert original not in actual["receipt"]["premises"]
    assert unrelated["id"] not in actual["receipt"]["closure"]
    assert actual == expected


def test_a_stale_measurement_does_not_withhold_an_independent_assessment_schedule():
    request = plan()
    object_of(request, "score")["version"] = "invented-v2"
    card = run({"operation": "describe", "view": "protocol"})
    prepared = run(card["result"]["example"])
    schedule = copy.deepcopy(prepared["result"]["request"]["session"]["protocol"]["checks"][0])
    schedule["id"] = "independent-schedule"
    schedule["objects"] = ["week12", "week12-collection"]
    schedule["scope"] = copy.deepcopy(request["session"]["protocol"]["checks"][0]["scope"])
    request["session"]["protocol"]["checks"].append(schedule)

    reply = run(request)
    estimand = child_of(reply)
    independent = child_of(reply, "independent-schedule")

    assert "adopt:score:invented-v1" in estimand["receipt"]["premises"]
    assert estimand["signals"][0]["admission"]["code"] == "binding_unresolved"
    assert "score" not in independent["receipt"]["closure"]
    assert "adopt:score:invented-v1" not in independent["receipt"]["premises"]
    assert {row["admission"] for row in independent["signals"][0]["claim_admission"]} == {"accepted"}


def test_the_public_cli_and_initialized_mcp_retain_the_same_stale_closure_provenance(tmp_path):
    request = plan()
    object_of(request, "week12")["version"] = "invented-v2"
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    completed = subprocess.run(
        [CLI, "reason", "--request", str(path)], capture_output=True, text=True, cwd=ROOT, check=False
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    cli_reply = json.loads(completed.stdout)
    client = McpClient(tmp_path / "served")
    try:
        mcp_reply = client.call("reason", request=request)
    finally:
        client.close()

    cli_child, mcp_child = child_of(cli_reply), child_of(mcp_reply)
    assert "adopt:week12:invented-v1" in cli_child["receipt"]["premises"]
    assert cli_child == mcp_child
    assert cli_child["signals"][0]["admission"]["code"] == "binding_unresolved"
