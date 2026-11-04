"""Public signals requests carry explicit protocol claims only for the protocol operator kinds."""

import copy
import json
from pathlib import Path

from TrialLedger.layer2 import run

FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures"
)
SUPPORT = [{"id": "invented", "status": "known", "resolution": "resolved", "basis": ["user:invented"]}]


def _case(name: str, identity: str) -> dict:
    return next(c for c in json.loads((FIXTURES / name).read_text())["cases"] if c["id"] == identity)


def _request(kind: str, data: dict, claims: list | None = None) -> dict:
    signal = {"id": "s", "kind": kind, "data": data, "support": SUPPORT}
    if claims is not None:
        signal["claims"] = claims
    return {"operation": "signals", "signals": [signal]}


def test_explicit_schedule_claims_reach_the_operator_through_the_public_request():
    data = _case("schedule.json", "TIM-1")["data"]
    reply = run(_request("schedule_coverage", data, [{"id": "visit-feasible", "claim": "existence"}]))
    assert reply["code"] == "complete", reply
    signal = reply["result"]["signals"][0]
    assert signal["code"] == "satisfied"
    assert [row["id"] for row in signal["value"]["claims"]] == ["visit-feasible"]


def test_omitted_claims_compute_the_operator_defaults():
    data = _case("schedule.json", "TIM-1")["data"]
    signal = run(_request("schedule_coverage", data))["result"]["signals"][0]
    assert signal["code"] == "violated"
    assert [row["claim"] for row in signal["value"]["claims"]] == ["existence", "nominal", "full_window"]


def test_policy_termination_is_only_computed_when_claimed_publicly():
    case = _case("policy.json", "POL-5-acyclic-dead-end-is-not-termination")
    claimed = run(_request("finite_policy", case["data"], case["claims"]))["result"]["signals"][0]
    assert {row["claim"]: row["outcome"] for row in claimed["value"]["claims"]}[
        "termination"
    ] == "not_established"
    default = run(_request("finite_policy", case["data"]))["result"]["signals"][0]
    assert "termination" not in {row["claim"] for row in default["value"]["claims"]}


def test_binomial_claims_and_a_missing_role_stay_unadmitted_publicly():
    case = _case("binomial.json", "STA-4-missing-alignment-keeps-arithmetic")
    signal = run(_request("binomial_design", case["data"], []))["result"]["signals"][0]
    assert signal["code"] == "unresolved"
    assert signal["calculation_code"] == "computed"
    assert signal["admission"]["code"] == "binding_unresolved"
    assert signal["status"] == "known"
    assert signal["value"]["null_rejection_probability"] == "1/4"


def test_claims_on_an_existing_kind_are_refused_not_ignored():
    guide = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]
    request = copy.deepcopy(guide["signal_examples"]["decision_table"])
    request["signals"][0]["claims"] = []
    reply = run(request)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["unsupported_signal_claims"]


def test_a_non_object_claim_is_refused():
    data = _case("schedule.json", "TIM-1")["data"]
    reply = run(_request("schedule_coverage", data, ["existence"]))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["signal_claim_not_object"]


def test_malformed_operator_claims_are_translation_refusals():
    data = _case("schedule.json", "TIM-1")["data"]
    reply = run(_request("schedule_coverage", data, [{"id": "x", "claim": "coverage"}]))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["schedule_invalid_claims"]


ASSESSMENT = {"id": "assessment", "status": "known", "resolution": "resolved", "basis": ["user:invented"]}
COLLECTION = {"id": "collection", "status": "proposed", "resolution": "resolved", "basis": ["user:invented"]}
ROLES = {"permitted": ["assessment"], "nominal": ["assessment"], "available": ["collection"]}


def _rows(signal: dict) -> dict:
    return {row["claim"]: row for row in signal["claim_admission"]}


def _outside_window_request(role_support: dict | None) -> dict:
    data = dict(_case("schedule.json", "TIM-1")["data"], nominal="100")
    signal = {"id": "s", "kind": "schedule_coverage", "data": data, "support": [ASSESSMENT, COLLECTION]}
    if role_support is not None:
        signal["role_support"] = role_support
    return {"operation": "signals", "signals": [signal]}


def test_a_known_outside_window_finding_is_admitted_while_the_collection_plan_is_proposed():
    signal = run(_outside_window_request(ROLES))["result"]["signals"][0]
    rows = _rows(signal)
    assert rows["nominal"]["admission"] == "accepted"
    assert rows["nominal"]["effective_outcome"] == "outside_window"
    assert rows["nominal"]["support"] == ["assessment"]
    assert rows["existence"]["admission"] == "proposed_refused"
    assert rows["existence"]["effective_outcome"] == "unresolved"
    assert rows["full_window"]["admission"] == "proposed_refused"
    assert signal["code"] == "unresolved"
    assert signal["role_support"] == ROLES


def test_without_role_support_every_claim_is_gated_by_all_support():
    rows = _rows(run(_outside_window_request(None))["result"]["signals"][0])
    assert rows["nominal"]["admission"] == "proposed_refused"
    assert rows["nominal"]["effective_outcome"] == "unresolved"


def test_an_undecided_claim_is_undetermined_not_admitted_or_refused():
    data = _case("schedule.json", "TIM-3-unknown-availability")["data"]
    signal = {
        "id": "s",
        "kind": "schedule_coverage",
        "data": data,
        "support": [ASSESSMENT],
        "role_support": {"permitted": ["assessment"]},
    }
    rows = _rows(run({"operation": "signals", "signals": [signal]})["result"]["signals"][0])
    assert {row["admission"] for row in rows.values()} == {"undetermined"}
    assert {row["effective_outcome"] for row in rows.values()} == {"unresolved"}


def test_a_proposed_prohibition_no_longer_hides_known_policy_coverage():
    case = _case("policy.json", "POL-1-proposed-prohibition-keeps-raw-violation")
    claims = [{"id": c, "claim": c, "witness_limit": 1} for c in ("coverage", "prohibition")]
    signal = run(_request("finite_policy", case["data"], claims))["result"]["signals"][0]
    rows = _rows(signal)
    assert (rows["coverage"]["admission"], rows["coverage"]["effective_outcome"]) == ("accepted", "covered")
    assert (rows["prohibition"]["admission"], rows["prohibition"]["effective_outcome"]) == (
        "proposed_refused",
        "unresolved",
    )
    assert rows["prohibition"]["outcome"] == "violation"


def test_a_missing_binomial_role_leaves_each_claim_unadmitted():
    case = _case("binomial.json", "STA-4-missing-alignment-keeps-arithmetic")
    claims = [{"id": "alpha", "quantity": "null_rejection_probability", "comparison": "<=", "value": "1/4"}]
    rows = run(_request("binomial_design", case["data"], claims))["result"]["signals"][0]["claim_admission"]
    assert [(row["outcome"], row["admission"]) for row in rows] == [("satisfied", "binding_unresolved")]


def test_role_support_is_validated():
    base = _outside_window_request(ROLES)
    for roles, problem in (
        ({"window": ["assessment"]}, "unknown_signal_role"),
        ({"permitted": ["nobody"]}, "invalid_signal_role_support"),
        ({"permitted": []}, "invalid_signal_role_support"),
        ({}, "invalid_signal_role_support"),
    ):
        request = copy.deepcopy(base)
        request["signals"][0]["role_support"] = roles
        reply = run(request)
        assert (reply["code"], reply["problems"]) == ("refused", [problem])
    guide = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]
    request = copy.deepcopy(guide["signal_examples"]["decision_table"])
    request["signals"][0]["role_support"] = {"model": ["invented-inputs"]}
    assert run(request)["problems"] == ["unsupported_signal_role_support"]
