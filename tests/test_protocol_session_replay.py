"""A v2 managed session runs protocol checks through projection, the budgeted child path and claim gating."""

import copy

from TrialLedger.layer2 import run

ORIGIN = {"kind": "user_choice", "ref": "user:invented week-12 plan", "source": None, "analysis": None}


def _standing(status: str) -> dict:
    return {"status": status, "resolution": "resolved", "basis": ["user:invented week-12 plan"]}


def _session(nominal: str, collection_status: str = "proposed") -> dict:
    request = copy.deepcopy(run({"operation": "describe", "view": "design_session"})["result"]["example"])
    session = request["session"]
    session["schema_version"] = 2
    scope = {
        "target": copy.deepcopy(session["target"]),
        "context": {"cohort": None, "phase": None, "arm": None},
    }

    def obj(identity, kind, data, depends_on, status="known", support=("adult",)):
        return {
            "id": identity,
            "kind": kind,
            "scope": copy.deepcopy(scope),
            "version": "invented-v1",
            "origin": copy.deepcopy(ORIGIN),
            "standing": _standing(status),
            "support": list(support),
            "depends_on": depends_on,
            "data": data,
        }

    reference = {"ref": "invented:score", "version": "1", **_standing("known")}
    interval = {"lower": "77", "upper": "91", "lower_inclusive": True, "upper_inclusive": True}
    through_80 = {"lower": None, "upper": "80", "lower_inclusive": False, "upper_inclusive": True}
    session["protocol"] = {
        "schema_version": 1,
        "objects": [
            obj(
                "score",
                "measurement",
                {"definition": reference, "unit": "points", "mode": "observed", "baseline": None},
                [],
            ),
            obj(
                "week12",
                "assessment",
                {
                    "measurement": "score",
                    "anchor": "randomization",
                    "unit": "day",
                    "nominal": nominal,
                    "permitted": [interval],
                    "condition": None,
                },
                ["score"],
            ),
            obj(
                "collection",
                "collection",
                {
                    "assessment": "week12",
                    "mode": "observed",
                    "availability": [through_80],
                    "event_handling": None,
                },
                ["week12"],
                status=collection_status,
                support=(),
            ),
        ],
        "checks": [
            {
                "id": "week12-schedule",
                "kind": "schedule",
                "scope": copy.deepcopy(scope),
                "objects": ["week12", "collection"],
                "bindings": [],
                "claims": [
                    {"id": "visit", "claim": "existence"},
                    {"id": "target", "claim": "nominal"},
                    {"id": "window", "claim": "full_window"},
                ],
                "required": True,
                "support": [],
            }
        ],
        "sections": [
            {"id": "assessments", "state": "requested", "objects": ["week12", "collection"], "basis": []}
        ],
    }
    return request


def _admission(reply: dict) -> dict:
    check = reply["result"]["protocol"]["checks"][0]
    signal = check["children"][0]["signals"][0]
    return {row["claim"]: row for row in signal["claim_admission"]}, check


def test_a_known_outside_window_target_is_admitted_beside_a_proposed_collection_plan():
    reply = run(_session("100"))
    assert reply["code"] == "complete", reply
    rows, check = _admission(reply)
    assert (rows["nominal"]["outcome"], rows["nominal"]["admission"]) == ("outside_window", "accepted")
    assert rows["existence"]["admission"] == "proposed_refused"
    assert rows["full_window"]["effective_outcome"] == "unresolved"
    child = check["children"][0]
    assert child["receipt"]["projection"].startswith("schedule_window_coverage")
    assert child["request_digest"] == child["receipt"]["request_digest"]
    assert check["required"] is True and check["unresolved"] == []


def test_a_drafted_collection_plan_without_adoption_support_never_becomes_known():
    rows, _ = _admission(run(_session("84", collection_status="known")))
    assert rows["existence"]["outcome"] == "satisfied"
    assert rows["existence"]["admission"] == "binding_unresolved"
    assert rows["full_window"]["outcome"] == "uncovered"


def test_the_v2_result_retains_objects_sections_and_the_v1_ledger():
    reply = run(_session("84"))
    protocol = reply["result"]["protocol"]
    assert [o["id"] for o in protocol["objects"]] == ["score", "week12", "collection"]
    assert protocol["sections"]["assessments"]["state"] == "requested"
    assert protocol["sections"]["safety"]["state"] == "not_requested"
    assert reply["result"]["schema_version"] == 2
    assert reply["result"]["decisions"]


def test_the_protocol_child_is_charged_to_the_session_budget():
    with_checks = run(_session("84"))["work"]["solver_work_reserved"]
    request = _session("84")
    request["session"]["protocol"]["checks"] = []
    without = run(request)["work"]["solver_work_reserved"]
    assert with_checks > without
