"""Canonical v2 design_session results for packet F, produced by the real public operation.

Run from the repo root: .venv/bin/python openspec/.../interface/fixtures/build_result_fixtures.py
All clinical content is invented; every choice is labelled simulated. Nothing here is hand-written output.
"""

import copy
import json
from pathlib import Path

from TrialLedger.layer2 import construction as c
from TrialLedger.layer2 import run

HERE = Path(__file__).parent / "results"
ORIGIN = {"kind": "user_choice", "ref": "user:simulated choice (fixture)", "source": None, "analysis": None}


def standing(status, resolution="resolved"):
    return {"status": status, "resolution": resolution, "basis": ["user:simulated choice (fixture)"]}


def base():
    request = copy.deepcopy(run({"operation": "describe", "view": "design_session"})["result"]["example"])
    request["session"]["schema_version"] = 2
    return request


def scope_of(session, cohort=None):
    return {
        "target": copy.deepcopy(session["target"]),
        "context": {"cohort": cohort, "phase": None, "arm": None},
    }


def obj(session, identity, kind, data, depends_on, status="known", support=("adult",), cohort=None):
    return {
        "id": identity,
        "kind": kind,
        "scope": scope_of(session, cohort),
        "version": "fixture-v1",
        "origin": copy.deepcopy(ORIGIN),
        "standing": standing(status),
        "support": list(support),
        "depends_on": depends_on,
        "data": data,
    }


def check(session, identity, kind, objects, claims, required=True, bindings=(), cohort=None):
    return {
        "id": identity,
        "kind": kind,
        "scope": scope_of(session, cohort),
        "objects": objects,
        "bindings": list(bindings),
        "claims": claims,
        "required": required,
        "support": [],
    }


def iv(lo, hi, li=True, ui=True):
    return {
        "lower": lo,
        "upper": hi,
        "lower_inclusive": li if lo is not None else False,
        "upper_inclusive": ui if hi is not None else False,
    }


REF = {"ref": "invented:score definition", "version": "1", **standing("known")}
SCHEDULE_CLAIMS = [
    {"id": "visit", "claim": "existence"},
    {"id": "target", "claim": "nominal"},
    {"id": "window", "claim": "full_window"},
]


def schedule_objects(session, nominal, collection_status="proposed", condition=None):
    return [
        obj(
            session,
            "score",
            "measurement",
            {"definition": REF, "unit": "points", "mode": "observed", "baseline": None},
            [],
        ),
        obj(
            session,
            "week12",
            "assessment",
            {
                "measurement": "score",
                "anchor": "randomization",
                "unit": "day",
                "nominal": nominal,
                "permitted": [iv("77", "91")],
                "condition": condition,
            },
            ["score"],
        ),
        obj(
            session,
            "collection",
            "collection",
            {
                "assessment": "week12",
                "mode": "observed",
                "availability": [iv(None, "80")],
                "event_handling": None,
            },
            ["week12"],
            status=collection_status,
            support=(),
        ),
    ]


def blit(key, positive=True):
    return c.literal(
        subject=c.Subject(kind="study_procedure", referent=""),
        predicate=c.Predicate(kind="measurement", key=key),
        value=c.Value(kind="boolean"),
        polarity="positive" if positive else "negative",
        time=None,
        qualifiers=c.Always(),
        evidence=(),
    )


def evar(key, n):
    return {
        "id": key,
        "values": [
            c.expanded(
                c.literal(
                    subject=c.Subject(kind="study_procedure", referent=""),
                    predicate=c.Predicate(kind="measurement", key=key),
                    value=c.enum_value(members=(f"v{i}",), comparison="eq"),
                    polarity="positive",
                    time=None,
                    qualifiers=c.Always(),
                    evidence=(),
                )
            )
            for i in range(n)
        ],
    }


def policy_model(prohibition_status="known", big=False):
    x = blit("low_dose_safety_signal")
    rule = {"ref": "user:simulated prohibition", "version": "1", **standing(prohibition_status)}
    variables = [
        {"id": "low_safety", "values": [c.expanded(x), c.expanded(blit("low_dose_safety_signal", False))]}
    ]
    states = ["interim", "selected"]
    constraints = []
    if big:
        variables = [evar(f"v{i}", 16) for i in range(3)]
        states = [f"s{i}" for i in range(32)]
        constraints = [{"id": f"k{i}", "condition": "TAUT", "rule": rule} for i in range(8)]
    first = c.literal(
        subject=c.Subject(kind="study_procedure", referent=""),
        predicate=c.Predicate(kind="measurement", key="v0"),
        value=c.enum_value(members=("v0",), comparison="eq"),
        polarity="positive",
        time=None,
        qualifiers=c.Always(),
        evidence=(),
    )
    taut = c.expanded(c.AnyOf(parts=(first, c.Not(part=first))))
    constraints = [{**k, "condition": taut} for k in constraints]
    return {
        "scope": "invented:stage-a-interim",
        "version": "fixture-v1",
        "variables": variables,
        "constraints": constraints,
        "states": states,
        "initial": [states[0]],
        "terminal": [states[1]],
        "actions": [
            {
                "id": "select_low_dose",
                "scope": {"level": "cohort", "ref": "invented:stage-a"},
                "description": "select low dose",
            }
        ],
        "transitions": [
            {
                "id": "t",
                "from": states[0],
                "to": states[1],
                "guard": c.expanded(c.AnyOf(parts=(x, c.Not(part=x)))) if not big else taut,
                "actions": ["select_low_dose"],
            }
        ],
        "prohibitions": []
        if big
        else [
            {
                "id": "no-low-with-signal",
                "state": None,
                "condition": c.expanded(x),
                "actions": ["select_low_dose"],
                "rule": rule,
            }
        ],
        "invariants": [],
    }


def write(name, request):
    reply = run(request)
    assert reply["code"] == "complete", (name, reply.get("problems"))
    (HERE / f"{name}.json").write_text(
        json.dumps({"request": request, "result": reply["result"]}, indent=1) + "\n"
    )
    print(name, "ok", len(json.dumps(reply["result"])))


def main():
    # 1. Schedule: refuted claims, a known outside-window target beside a proposed plan; open safety section.
    r = base()
    s = r["session"]
    s["protocol"] = {
        "schema_version": 1,
        "objects": schedule_objects(s, "100"),
        "checks": [check(s, "week12-schedule", "schedule", ["week12", "collection"], SCHEDULE_CLAIMS)],
        "sections": [
            {"id": "assessments", "state": "requested", "objects": ["week12", "collection"], "basis": []},
            {"id": "safety", "state": "requested", "objects": [], "basis": []},
            {
                "id": "exploratory",
                "state": "not_applicable",
                "objects": [],
                "basis": ["user:simulated choice (fixture)"],
            },
        ],
    }
    write("schedule-refuted-and-conditional", r)
    # 2. Conditional assessment (condition declared) and a scope mismatch that leaves a check unresolved.
    r = base()
    s = r["session"]
    cond = c.expanded(blit("discontinued_treatment"))
    objects = schedule_objects(s, "84", collection_status="known", condition=cond)
    objects[2]["scope"] = scope_of(s, cohort="post-discontinuation")
    s["protocol"] = {
        "schema_version": 1,
        "objects": objects,
        "checks": [check(s, "week12-schedule", "schedule", ["week12", "collection"], SCHEDULE_CLAIMS)],
        "sections": [
            {"id": "assessments", "state": "requested", "objects": ["week12", "collection"], "basis": []}
        ],
    }
    write("schedule-scope-mismatch-unresolved", r)
    # 2b. A projected conditional assessment: the condition is declared, so the result stays conditional.
    r = base()
    s = r["session"]
    objects = schedule_objects(s, "84", collection_status="known", condition=cond)
    objects[2]["support"] = ["adult"]
    s["protocol"] = {
        "schema_version": 1,
        "objects": objects,
        "checks": [check(s, "week12-schedule", "schedule", ["week12", "collection"], SCHEDULE_CLAIMS)],
        "sections": [
            {"id": "assessments", "state": "requested", "objects": ["week12", "collection"], "basis": []}
        ],
    }
    write("schedule-conditional-assessment", r)
    # 3. Policy: known violation and proposed prohibition; external method not computed.
    for name, status in (("policy-violation-known", "known"), ("policy-violation-proposed", "proposed")):
        r = base()
        s = r["session"]
        s["protocol"] = {
            "schema_version": 1,
            "objects": [
                obj(s, "interim-rule", "policy", {"model": policy_model(status), "bindings": []}, [])
            ],
            "checks": [
                check(
                    s,
                    "interim-safety",
                    "finite_policy",
                    ["interim-rule"],
                    [
                        {"id": c_, "claim": c_, "witness_limit": 4}
                        for c_ in ("coverage", "exclusivity", "prohibition", "termination")
                    ],
                )
            ],
            "sections": [{"id": "safety", "state": "requested", "objects": ["interim-rule"], "basis": []}],
        }
        write(name, r)
    # 4. Policy work limit (limited).
    r = base()
    s = r["session"]
    s["protocol"] = {
        "schema_version": 1,
        "objects": [obj(s, "big-rule", "policy", {"model": policy_model(big=True), "bindings": []}, [])],
        "checks": [
            check(
                s,
                "big-safety",
                "finite_policy",
                ["big-rule"],
                [{"id": "coverage", "claim": "coverage", "witness_limit": 1}],
            )
        ],
        "sections": [{"id": "safety", "state": "requested", "objects": ["big-rule"], "basis": []}],
    }
    write("policy-work-limit", r)
    # 5. Binomial: computed with a missing alignment role; external survival method not computed.
    r = base()
    s = r["session"]
    endpoint = obj(
        s,
        "response",
        "endpoint",
        {"variable": "score", "definition": REF, "estimand": None, "dependencies": None},
        ["score"],
    )
    eff = obj(
        s,
        "efficacy",
        "efficacy",
        {
            "endpoint": "response",
            "method": "binomial_design",
            "parameters": {
                "model": "fixed_n_iid_bernoulli",
                "direction": "greater",
                "n": 20,
                "critical_count": 9,
                "p0": "1/5",
                "p1": "2/5",
            },
            "assumptions": [
                {"role": "fixed_n", "premise": "adult"},
                {"role": "iid_binary", "premise": "adult"},
            ],
        },
        ["response"],
    )
    ext = obj(
        s,
        "survival",
        "external_method",
        {
            "definition": {"ref": "invented:log-rank", "version": "1", **standing("known")},
            "inputs": [{"name": "hazard_ratio", "value": "7/10", "unit": None, "ref": None}],
            "missing": ["accrual_rate", "dropout"],
        },
        [],
    )
    s["protocol"] = {
        "schema_version": 1,
        "objects": [schedule_objects(s, "84")[0], endpoint, eff, ext],
        "checks": [
            check(
                s,
                "efficacy-exact",
                "binomial_design",
                ["efficacy", "response"],
                [
                    {
                        "id": "alpha",
                        "quantity": "null_rejection_probability",
                        "comparison": "<=",
                        "value": "1/20",
                    },
                    {"id": "power", "quantity": "power", "comparison": ">=", "value": "4/5"},
                ],
            ),
            check(s, "survival-method", "external_method", ["survival"], []),
        ],
        "sections": [
            {"id": "efficacy", "state": "requested", "objects": ["efficacy", "survival"], "basis": []},
            {"id": "endpoints", "state": "requested", "objects": ["response"], "basis": []},
        ],
    }
    write("efficacy-binomial-and-external", r)
    # 6. A plan comparison: the selected plan leaves a window gap (repair choice); the alternative extends
    #    collection as a hypothetical replacement.
    r = base()
    s = r["session"]
    objects = schedule_objects(s, "84", collection_status="known")
    objects[2]["support"] = ["adult"]
    extended = copy.deepcopy(objects[2])
    extended["data"]["availability"] = [iv(None, "91")]
    s["protocol"] = {
        "schema_version": 1,
        "objects": objects,
        "checks": [check(s, "week12-schedule", "schedule", ["week12", "collection"], SCHEDULE_CLAIMS)],
        "sections": [
            {"id": "assessments", "state": "requested", "objects": ["week12", "collection"], "basis": []}
        ],
    }
    s["decisions"].append(
        {
            "kind": "protocol_options",
            "id": "collection-plan",
            "question": "How long should week-12 collection run?",
            "target": copy.deepcopy(s["target"]),
            "coverage": "declared_design",
            "selected": {
                "alternative": "as-drafted",
                "origin": "user",
                "basis": ["user:simulated choice (fixture)"],
            },
            "alternatives": [
                {
                    "id": "as-drafted",
                    "label": "Collect through day 80",
                    "replace_objects": [],
                    "checks": ["week12-schedule"],
                },
                {
                    "id": "extend",
                    "label": "Collect through day 91",
                    "replace_objects": [extended],
                    "checks": ["week12-schedule"],
                },
            ],
        }
    )
    write("decision-plan-comparison", r)


if __name__ == "__main__":
    main()
