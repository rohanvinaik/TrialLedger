"""A v2 managed session runs protocol checks through projection, the budgeted child path and claim gating."""

import copy

from TrialLedger.layer2 import run

ORIGIN = {"kind": "user_choice", "ref": "user:invented week-12 plan", "source": None, "analysis": None}


def _standing(status: str) -> dict:
    return {"status": status, "resolution": "resolved", "basis": ["user:invented week-12 plan"]}


def adoption_premise(
    identity: str, version: str, status: str = "known", resolution: str = "resolved"
) -> dict:
    """An explicit attributed adoption record naming exactly one object version (Rohan, 2026-11-04)."""
    return {
        "id": f"adopt:{identity}:{version}",
        "kind": "adoption",
        "payload": {
            "objects": [{"id": identity, "version": version}],
            "status": status,
            "resolution": resolution,
        },
        "origin": copy.deepcopy(ORIGIN),
        "depends_on": [],
    }


def new_edition(session: dict, identity: str, suffix: str = "revised") -> dict:
    """An instructed change to an adopted object: a new version, re-adopted at exactly that version.

    Content changed under an unchanged version is refused on every revision path, and an adoption belongs to
    one edition (Rohan, 2026-11-04). Each adoption record adopting the old version gets a matching record for
    the new version, with the same standing and origin; only this object's support is rebound.
    """
    item = next(o for o in session["protocol"]["objects"] if o["id"] == identity)
    old, new = item["version"], f"{item['version']}-{suffix}"
    item["version"] = new
    premises = {p["id"]: p for p in session["premises"]}
    support = []
    for ref in item["support"]:
        record = premises.get(ref)
        named = (record or {}).get("payload", {}).get("objects", []) if record else []
        if record and record.get("kind") == "adoption" and {"id": identity, "version": old} in named:
            fresh = copy.deepcopy(record)
            fresh["id"] = f"adopt:{identity}:{new}"
            fresh["payload"]["objects"] = [{"id": identity, "version": new}]
            if fresh["id"] not in premises:
                session["premises"].append(fresh)
                premises[fresh["id"]] = fresh
            support.append(fresh["id"])
        else:
            support.append(ref)
    item["support"] = support
    return item


def adopt(request: dict, identity: str, status: str = "known", resolution: str = "resolved") -> dict:
    """Adopt a protocol object by its own adoption premise, which becomes its only support."""
    session = request["session"]
    item = next(o for o in session["protocol"]["objects"] if o["id"] == identity)
    premise = adoption_premise(identity, item["version"], status, resolution)
    session["premises"] = [p for p in session["premises"] if p["id"] != premise["id"]] + [premise]
    item["support"] = [premise["id"]]
    return request


def _session(nominal: str, collection_status: str = "proposed") -> dict:
    request = copy.deepcopy(run({"operation": "describe", "view": "design_session"})["result"]["example"])
    session = request["session"]
    session["schema_version"] = 2
    scope = {
        "target": copy.deepcopy(session["target"]),
        "context": {"cohort": None, "phase": None, "arm": None},
    }

    adoptions = []

    def obj(identity, kind, data, depends_on, status="known", adopted=True):
        if adopted:
            adoptions.append(adoption_premise(identity, "invented-v1"))
        return {
            "id": identity,
            "kind": kind,
            "scope": copy.deepcopy(scope),
            "version": "invented-v1",
            "origin": copy.deepcopy(ORIGIN),
            "standing": _standing(status),
            "support": [f"adopt:{identity}:invented-v1"] if adopted else [],
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
                adopted=False,
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
    session["premises"] = session["premises"] + adoptions
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


def test_a_declared_assessment_condition_keeps_every_claim_conditional():
    request = _session("84", collection_status="known")
    condition = {
        "class": "Literal",
        "subject": {"class": "Subject", "kind": "participant", "referent": ""},
        "predicate": {"class": "Predicate", "kind": "treatment_history", "key": "discontinued_study_drug"},
        "value": {"class": "Value", "kind": "boolean"},
        "polarity": "positive",
        "time": None,
        "qualifiers": {"class": "Always"},
        "evidence": [],
    }
    request["session"]["protocol"]["objects"][1]["data"]["condition"] = condition
    child = run(request)["result"]["protocol"]["checks"][0]["children"][0]
    assert child["conditions"] and child["conditions"][0]["object"] == "week12"
    assert {row["application"] for row in child["signals"][0]["claim_admission"]} == {"conditional"}


def test_without_a_condition_claims_apply_unconditionally():
    child = run(_session("84"))["result"]["protocol"]["checks"][0]["children"][0]
    assert {row["application"] for row in child["signals"][0]["claim_admission"]} == {"unconditional"}


def _adult_body(request: dict) -> dict:
    return copy.deepcopy(request["session"]["premises"][0]["payload"]["body"])


def _with_condition(condition: dict, deciding: list | None) -> dict:
    request = _session("84", collection_status="known")
    adopt(request, "collection")
    request["session"]["protocol"]["objects"][1]["data"]["condition"] = condition
    if deciding is not None:
        request["session"]["protocol"]["checks"][0]["bindings"] = [
            {"projection": "condition_applicability", "premises": deciding}
        ]
    return request


def _applications(reply: dict) -> set:
    child = reply["result"]["protocol"]["checks"][0]["children"][0]
    return {row["application"] for row in child["signals"][0]["claim_admission"]}, child


def test_a_condition_entailed_by_the_declared_premises_applies_unconditionally():
    base = _session("84")
    applications, child = _applications(run(_with_condition(_adult_body(base), ["adult"])))
    assert applications == {"unconditional"}
    assert [row["code"] for row in child["applicability"]] == ["applies"]
    assert child["applicability"][0]["request"]["operation"] == "entailment"


def test_a_condition_refuted_by_the_declared_premises_is_not_applicable():
    base = _session("84")
    condition = {"class": "Not", "part": _adult_body(base)}
    applications, child = _applications(run(_with_condition(condition, ["adult"])))
    assert applications == {"not_applicable"}
    assert [row["code"] for row in child["applicability"]] == ["does_not_apply"]


def test_an_undecided_or_undeclared_condition_stays_conditional():
    other = {
        "class": "Literal",
        "subject": {"class": "Subject", "kind": "participant", "referent": ""},
        "predicate": {"class": "Predicate", "kind": "treatment_history", "key": "discontinued_study_drug"},
        "value": {"class": "Value", "kind": "boolean"},
        "polarity": "positive",
        "time": None,
        "qualifiers": {"class": "Always"},
        "evidence": [],
    }
    decided, child = _applications(run(_with_condition(other, ["adult"])))
    assert decided == {"conditional"} and child["applicability"][0]["code"] == "undetermined"
    undeclared, child = _applications(run(_with_condition(_adult_body(_session("84")), None)))
    assert undeclared == {"conditional"} and child["applicability"] == []


def test_an_invalid_applicability_binding_is_a_named_refusal():
    for premises in ([], ["nobody"], ["adult", "adult"]):
        reply = run(_with_condition(_adult_body(_session("84")), premises))
        assert reply["problems"] == ["protocol_applicability_binding"], premises
