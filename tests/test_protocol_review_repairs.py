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


# 1b. A premise backing one object and also declared check-wide reaches every claim (second review).
def _outside_window_with_collection_premise(check_wide: bool) -> dict:
    request = _with_proposed_premise(_session("100", collection_status="known"))
    request["session"]["protocol"]["objects"][2]["support"] = ["draft-reading"]
    if check_wide:
        request["session"]["protocol"]["checks"][0]["support"] = ["draft-reading"]
    return request


def _nominal(reply: dict) -> dict:
    return next(row for row in _claims(reply) if row["claim"] == "nominal")


def test_collection_only_proposed_support_leaves_the_known_outside_window_finding_admitted():
    reply = run(_outside_window_with_collection_premise(check_wide=False))
    nominal = _nominal(reply)
    assert (nominal["outcome"], nominal["admission"], nominal["status"]) == (
        "outside_window",
        "accepted",
        "known",
    )
    assert nominal["effective_outcome"] == "outside_window"
    assert "premise:draft-reading" not in nominal["support"]


def test_the_same_premise_declared_check_wide_withholds_that_finding():
    reply = run(_outside_window_with_collection_premise(check_wide=True))
    nominal = _nominal(reply)
    assert nominal["admission"] == "proposed_refused"
    assert nominal["effective_outcome"] == "unresolved"
    assert "premise:draft-reading" in nominal["support"]


def test_declaring_a_premise_check_wide_changes_the_child_request():
    def digest(reply):
        return reply["result"]["protocol"]["checks"][0]["children"][0]["request_digest"]

    assert digest(run(_outside_window_with_collection_premise(False))) != digest(
        run(_outside_window_with_collection_premise(True))
    )


# 5. Applicability carries its own weakest standing and deciding references (third review).
def _with_interpolated_deciding_premise(negate: bool) -> dict:
    from tests.test_protocol_session_replay import _with_condition

    base = _session("84")
    body = copy.deepcopy(base["session"]["premises"][0]["payload"]["body"])
    condition = {"class": "Not", "part": body} if negate else body
    request = _with_condition(condition, ["adult-interpolated"])
    premise = copy.deepcopy(request["session"]["premises"][0])
    premise["id"] = premise["payload"]["id"] = "adult-interpolated"
    premise["payload"]["status"] = "interpolated"
    request["session"]["premises"].append(premise)
    return request


def _first_claim(reply: dict) -> tuple[dict, dict]:
    child = reply["result"]["protocol"]["checks"][0]["children"][0]
    return child["signals"][0]["claim_admission"][0], protocol_view.view(reply["result"])["checks"][0][
        "claims"
    ][0]


def test_an_interpolated_applicability_proof_qualifies_the_unconditional_finding():
    row, clinical = _first_claim(run(_with_interpolated_deciding_premise(negate=False)))
    assert row["application"] == "unconditional"
    assert (row["status"], row["application_status"], row["finding_status"]) == (
        "known",
        "interpolated",
        "interpolated",
    )
    assert "adult-interpolated" in row["application_refs"]
    assert clinical["standing"] == "interpolated" and clinical["arithmetic_standing"] == "known"
    assert "adult-interpolated" in clinical["determining_ids"]
    assert clinical["wording"].endswith("Applicability rests on interpolated support.")


def test_an_interpolated_refutation_is_a_qualified_not_applicable():
    row, clinical = _first_claim(run(_with_interpolated_deciding_premise(negate=True)))
    assert (row["application"], row["application_status"]) == ("not_applicable", "interpolated")
    assert clinical["wording"] == (
        "Not applicable: the declared condition does not hold in this scope. "
        "Applicability rests on interpolated support."
    )
    assert clinical["standing"] == "interpolated"


def test_a_known_applicability_proof_adds_no_qualification():
    from tests.test_protocol_session_replay import _with_condition

    base = _session("84")
    request = _with_condition(copy.deepcopy(base["session"]["premises"][0]["payload"]["body"]), ["adult"])
    row, clinical = _first_claim(run(request))
    assert (row["application_status"], row["finding_status"]) == ("known", "known")
    assert "Applicability rests" not in clinical["wording"]


# 6. The applicability binding coexists with an operation binding (third review).
def _temporal_request(with_applicability: bool) -> dict:
    example = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]["signal_examples"]
    data = copy.deepcopy(example["temporal"]["signals"][0]["data"])
    request = _session("84", collection_status="known")
    check = copy.deepcopy(request["session"]["protocol"]["checks"][0])
    bindings = [{"projection": "temporal_request", "data": data}]
    if with_applicability:
        bindings.append({"projection": "condition_applicability", "premises": ["adult"]})
    check.update(id="timeline", kind="temporal", objects=[], claims=[], bindings=bindings)
    request["session"]["protocol"]["checks"] = [check]
    return request


def test_a_temporal_check_keeps_its_child_when_an_applicability_binding_is_added():
    for with_applicability in (False, True):
        check = run(_temporal_request(with_applicability))["result"]["protocol"]["checks"][0]
        assert len(check["children"]) == 1, with_applicability
        assert check["unresolved"] == [], with_applicability
