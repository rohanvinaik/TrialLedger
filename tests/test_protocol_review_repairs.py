"""Consumer-level repairs from the external review of 27ef4b7 (2026-11-04).

Each test reproduces a reviewed defect through the public operation and asserts the positive behaviour and
its MUST-NOT. The epistemic guarantees live between components, so unit tests of either side alone missed
them.
"""

import copy
import json
from pathlib import Path

from tests.test_protocol_session_replay import _session
from TrialLedger.layer2 import protocol_view, run

FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures"
)


def _claims(reply: dict) -> list[dict]:
    child = reply["result"]["protocol"]["checks"][0]["children"][0]
    return child["signals"][0]["claim_admission"]


def _with_proposed_premise(request: dict) -> dict:
    premise = copy.deepcopy(request["session"]["premises"][0])
    premise["id"] = premise["payload"]["id"] = "draft-reading"
    premise["payload"]["status"] = "proposed"
    request["session"]["premises"].append(premise)
    return request


# 1. Check-level support cannot be bypassed per claim.
def test_a_proposed_check_level_premise_refuses_every_claim_in_a_managed_session():
    request = _with_proposed_premise(_session("84", collection_status="known"))
    request["session"]["protocol"]["objects"][2]["support"] = ["adult"]
    request["session"]["protocol"]["checks"][0]["support"] = ["draft-reading"]
    reply = run(request)
    assert reply["code"] == "complete", reply["problems"]
    rows = _claims(reply)
    assert {row["admission"] for row in rows} == {"proposed_refused"}
    assert {row["effective_outcome"] for row in rows} == {"unresolved"}
    assert all("premise:draft-reading" in row["support"] for row in rows)


def test_without_check_level_support_the_same_claims_are_accepted():
    request = _session("84", collection_status="known")
    request["session"]["protocol"]["objects"][2]["support"] = ["adult"]
    assert {row["admission"] for row in _claims(run(request))} == {"accepted"}


def test_publicly_unbound_support_applies_to_every_claim():
    data = json.loads((FIXTURES / "schedule.json").read_text())["cases"][0]["data"]
    known = {"status": "known", "resolution": "resolved", "basis": ["user:invented"]}
    support = [
        {"id": "assessment", **known},
        {"id": "collection", **known},
        {"id": "check-reading", "status": "proposed", "resolution": "resolved", "basis": ["user:invented"]},
    ]
    roles = {"permitted": ["assessment"], "nominal": ["assessment"], "available": ["collection"]}
    signal = {"id": "s", "kind": "schedule_coverage", "data": data, "support": support, "role_support": roles}
    rows = run({"operation": "signals", "signals": [signal]})["result"]["signals"][0]["claim_admission"]
    assert {row["admission"] for row in rows} == {"proposed_refused"}


# 2. A hypothesis never supplies a fact.
def test_a_hypothesis_origin_object_with_known_standing_is_refused():
    request = _session("84", collection_status="known")
    for item in request["session"]["protocol"]["objects"]:
        item["origin"] = {"kind": "hypothesis", "ref": "user:what-if", "source": None, "analysis": None}
    reply = run(request)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_hypothesis_cannot_supply_fact"]


def test_a_proposed_hypothesis_object_is_admitted_but_never_applied():
    request = _session("84", collection_status="known")
    for item in request["session"]["protocol"]["objects"]:
        item["origin"] = {"kind": "hypothesis", "ref": "user:what-if", "source": None, "analysis": None}
        item["standing"]["status"] = "proposed"
    rows = _claims(run(request))
    assert {row["admission"] for row in rows} == {"proposed_refused"}
    assert {row["status"] for row in rows} == {"proposed"}


# 3. Operator-internal standing survives into every consumer.
def test_an_interpolated_prohibition_stays_interpolated_in_claim_rows_and_metadata():
    case = next(
        c
        for c in json.loads((FIXTURES / "policy.json").read_text())["cases"]
        if c["id"] == "POL-1-covered-but-unsafe"
    )
    data = copy.deepcopy(case["data"])
    data["prohibitions"][0]["rule"]["status"] = "interpolated"
    support = [{"id": "outer", "status": "known", "resolution": "resolved", "basis": ["user:invented"]}]
    claims = [{"id": "prohibition", "claim": "prohibition", "witness_limit": 1}]
    reply = run(
        {
            "operation": "signals",
            "signals": [
                {"id": "s", "kind": "finite_policy", "data": data, "support": support, "claims": claims}
            ],
        }
    )
    row = reply["result"]["signals"][0]["claim_admission"][0]
    assert (row["admission"], row["status"]) == ("accepted", "interpolated")
    assert row["determining_ids"] == ["no-low-dose-with-low-dose-signal"]
    finding = next(f for f in reply["metadata"]["findings"] if f["kind"] == "protocol_claim")
    assert finding["standing"] == "interpolated"
    assert finding["standing"] != "known"
    assert finding["disposition"] == "conflict"


# 4. The view consumes existing operators' structured findings.
def test_an_estimand_collection_mismatch_reaches_the_view_and_keeps_the_section_open():
    example = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]["signal_examples"]
    estimand = copy.deepcopy(example["estimand"]["signals"][0]["data"])
    for plan in estimand["collection_plan"]:
        plan["action"] = "stop"
    request = _session("84", collection_status="known")
    protocol = request["session"]["protocol"]
    template = copy.deepcopy(protocol["objects"][0])
    template.update(id="estimand", kind="estimand", depends_on=[], data=estimand)
    protocol["objects"].append(template)
    check = copy.deepcopy(protocol["checks"][0])
    check.update(id="estimand-check", kind="estimand", objects=["estimand"], claims=[])
    protocol["checks"] = [check]
    protocol["sections"] = [{"id": "endpoints", "state": "requested", "objects": ["estimand"], "basis": []}]
    reply = run(request)
    assert reply["code"] == "complete", reply["problems"]
    signal = reply["result"]["protocol"]["checks"][0]["children"][0]["signals"][0]
    assert signal["blockers"], "the estimand fixture must carry findings"
    view = protocol_view.view(reply["result"])
    endpoints = next(s for s in view["sections"] if s["id"] == "endpoints")
    assert endpoints["coverage"] == "open"
    texts = [item["text"] for item in view["open_items"] if item["kind"] == "signal_finding"]
    for blocker in signal["blockers"]:
        assert any(blocker in text for text in texts), blocker
    assert view["checks"][0]["findings"][0]["codes"] == signal["blockers"]
    assert "estimand_collection_plan_mismatch:week12" in signal["blockers"]
    assert any("estimand_collection_plan_mismatch:week12" in text for text in texts)
    assert endpoints["coverage"] != "specified"
