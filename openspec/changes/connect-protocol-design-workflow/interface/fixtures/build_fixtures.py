"""Wave-0 fixture generator for packets B, C and D (interface v1). Run from the repo root:
    .venv/bin/python openspec/changes/connect-protocol-design-workflow/interface/fixtures/build_fixtures.py
Expected values are written by hand from contracts C5-C7, except binomial tails, which are computed here by an
independent closed-form sum (math.comb over Fractions) that shares no code with any production module."""

import json
import math
from decimal import ROUND_HALF_EVEN, Decimal
from fractions import Fraction
from pathlib import Path

from TrialLedger.layer2 import construction as c

HERE = Path(__file__).parent
X = c.expanded


def iv(lo, hi, li=True, ui=True):
    return {
        "lower": lo,
        "upper": hi,
        "lower_inclusive": li if lo is not None else False,
        "upper_inclusive": ui if hi is not None else False,
    }


def sdata(nominal, permitted, available, anchor="randomization", unit="day"):
    return {
        "scope": "draft:week-12-assessment",
        "anchor": anchor,
        "unit": unit,
        "nominal": nominal,
        "permitted": permitted,
        "available": available,
    }


ALLC = None  # evaluate(): all three claims, ids equal claim names


def row(outcome, determined_by, missing=(), feasible=None, uncovered=None):
    return {
        "outcome": outcome,
        "determined_by": sorted(determined_by),
        "missing": sorted(missing),
        "feasible": feasible,
        "uncovered": uncovered,
    }


AP, APN, ANP = ["available", "permitted"], ["available", "nominal", "permitted"], ["nominal", "permitted"]
W = [iv("77", "91")]
schedule_cases = [
    {
        "id": "TIM-1",
        "acceptance": ["TIM-1"],
        "data": sdata("84", W, [iv(None, "80")]),
        "claims": ALLC,
        "expect": {
            "code": "violated",
            "claims": {
                "existence": row("satisfied", AP, feasible=[iv("77", "80")]),
                "nominal": row("not_collected", APN),
                "full_window": row("uncovered", AP, uncovered=[iv("80", "91", False, True)]),
            },
        },
    },
    {
        "id": "TIM-2-open-boundary",
        "acceptance": ["TIM-2"],
        "data": sdata("84", W, [iv(None, "91", False, False)]),
        "claims": ALLC,
        "expect": {
            "code": "violated",
            "claims": {
                "existence": row("satisfied", AP, feasible=[iv("77", "91", True, False)]),
                "nominal": row("satisfied", APN),
                "full_window": row("uncovered", AP, uncovered=[iv("91", "91")]),
            },
        },
    },
    {
        "id": "TIM-3-unknown-availability",
        "acceptance": ["TIM-3"],
        "data": sdata("84", W, None),
        "claims": ALLC,
        "expect": {
            "code": "unresolved",
            "claims": {
                "existence": row("unresolved", [], ["available"]),
                "nominal": row("unresolved", [], ["available"]),
                "full_window": row("unresolved", [], ["available"]),
            },
        },
    },
    {
        "id": "TIM-3-explicitly-none",
        "acceptance": ["TIM-3"],
        "data": sdata("84", W, []),
        "claims": ALLC,
        "expect": {
            "code": "violated",
            "claims": {
                "existence": row("no_feasible_time", AP, feasible=[]),
                "nominal": row("not_collected", APN),
                "full_window": row("uncovered", AP, uncovered=[iv("77", "91")]),
            },
        },
    },
    {
        "id": "TIM-3-no-permitted-time",
        "acceptance": ["TIM-3"],
        "data": sdata("84", [], [iv(None, "80")]),
        "claims": ALLC,
        "expect": {
            "code": "violated",
            "claims": {
                "existence": row("no_permitted_time", ["permitted"], feasible=[]),
                "nominal": row("outside_window", ANP),
                "full_window": row("no_permitted_time", ["permitted"], uncovered=[]),
            },
        },
    },
    {
        "id": "TIM-4-no-nominal",
        "acceptance": ["TIM-4"],
        "data": sdata(None, W, [iv(None, "80")]),
        "claims": ALLC,
        "expect": {
            "code": "violated",
            "claims": {
                "existence": row("satisfied", AP, feasible=[iv("77", "80")]),
                "nominal": row("unknown_target", ["nominal"], ["nominal"]),
                "full_window": row("uncovered", AP, uncovered=[iv("80", "91", False, True)]),
            },
        },
    },
    {
        "id": "TIM-4-outside-window-survives-unknown-collection",
        "acceptance": ["TIM-4", "EPI-2"],
        "data": sdata("100", W, None),
        "claims": ALLC,
        "expect": {
            "code": "violated",
            "claims": {
                "existence": row("unresolved", [], ["available"]),
                "nominal": row("outside_window", ANP),
                "full_window": row("unresolved", [], ["available"]),
            },
        },
    },
    {
        "id": "TIM-6-repeated-visits",
        "acceptance": ["TIM-6"],
        "data": sdata("56", [iv("27", "29"), iv("55", "57"), iv("83", "85")], [iv("0", "56")]),
        "claims": ALLC,
        "expect": {
            "code": "violated",
            "claims": {
                "existence": row("satisfied", AP, feasible=[iv("27", "29"), iv("55", "56")]),
                "nominal": row("satisfied", APN),
                "full_window": row("uncovered", AP, uncovered=[iv("56", "57", False, True), iv("83", "85")]),
            },
        },
    },
    {
        "id": "rational-endpoints-and-canonical-output",
        "acceptance": ["TIM-2"],
        "data": sdata("2/4", [iv("1/3", "7/2", True, False)], [iv("0", "14/4")]),
        "claims": ALLC,
        "expect": {
            "code": "satisfied",
            "nominal": "1/2",
            "permitted": [iv("1/3", "7/2", True, False)],
            "available": [iv("0", "7/2")],
            "claims": {
                "existence": row("satisfied", AP, feasible=[iv("1/3", "7/2", True, False)]),
                "nominal": row("satisfied", APN),
                "full_window": row("satisfied", AP, uncovered=[]),
            },
        },
    },
    {
        "id": "touching-intervals-merge",
        "acceptance": ["TIM-2"],
        "data": sdata("2", [iv("2", "3"), iv("1", "2", True, False)], [iv("1", "3")]),
        "claims": ALLC,
        "expect": {
            "code": "satisfied",
            "permitted": [iv("1", "3")],
            "claims": {
                "existence": row("satisfied", AP, feasible=[iv("1", "3")]),
                "nominal": row("satisfied", APN),
                "full_window": row("satisfied", AP, uncovered=[]),
            },
        },
    },
    {
        "id": "punctured-window-never-filled",
        "acceptance": ["TIM-2"],
        "data": sdata("2", [iv("1", "2", True, False), iv("2", "3", False, True)], [iv("2", "2")]),
        "claims": ALLC,
        "expect": {
            "code": "violated",
            "permitted": [iv("1", "2", True, False), iv("2", "3", False, True)],
            "claims": {
                "existence": row("no_feasible_time", AP, feasible=[]),
                "nominal": row("outside_window", ANP),
                "full_window": row(
                    "uncovered", AP, uncovered=[iv("1", "2", True, False), iv("2", "3", False, True)]
                ),
            },
        },
    },
    {
        "id": "subset-of-claims",
        "acceptance": ["TIM-1"],
        "data": sdata("84", W, [iv(None, "80")]),
        "claims": [{"id": "visit-feasible", "claim": "existence"}],
        "expect": {
            "code": "satisfied",
            "claims": {"visit-feasible": row("satisfied", AP, feasible=[iv("77", "80")])},
        },
    },
]
bad_W = [iv("77", "91")]
schedule_malformed = [
    {
        "id": "float-bound",
        "data": sdata(
            "84", [{"lower": 77.0, "upper": "91", "lower_inclusive": True, "upper_inclusive": True}], None
        ),
        "claims": ALLC,
        "refusal": "schedule_invalid_rational",
    },
    {
        "id": "decimal-string",
        "data": sdata("84.5", bad_W, None),
        "claims": ALLC,
        "refusal": "schedule_invalid_rational",
    },
    {
        "id": "zero-denominator",
        "data": sdata("1/0", bad_W, None),
        "claims": ALLC,
        "refusal": "schedule_invalid_rational",
    },
    {
        "id": "whitespace",
        "data": sdata(" 84", bad_W, None),
        "claims": ALLC,
        "refusal": "schedule_invalid_rational",
    },
    {
        "id": "plus-sign",
        "data": sdata("+84", bad_W, None),
        "claims": ALLC,
        "refusal": "schedule_invalid_rational",
    },
    {
        "id": "int-not-string",
        "data": sdata(84, bad_W, None),
        "claims": ALLC,
        "refusal": "schedule_invalid_rational",
    },
    {
        "id": "bit-limit",
        "data": sdata(str(1 << 256), bad_W, None),
        "claims": ALLC,
        "refusal": "schedule_rational_bit_limit",
    },
    {
        "id": "reversed",
        "data": sdata("84", [iv("91", "77")], None),
        "claims": ALLC,
        "refusal": "schedule_empty_interval",
    },
    {
        "id": "open-singleton",
        "data": sdata("84", [iv("80", "80", True, False)], None),
        "claims": ALLC,
        "refusal": "schedule_empty_interval",
    },
    {
        "id": "inclusive-infinity",
        "data": sdata(
            "84", [{"lower": None, "upper": "80", "lower_inclusive": True, "upper_inclusive": True}], None
        ),
        "claims": ALLC,
        "refusal": "schedule_infinite_inclusive",
    },
    {
        "id": "bool-as-flag",
        "data": sdata(
            "84", [{"lower": "1", "upper": "2", "lower_inclusive": 1, "upper_inclusive": True}], None
        ),
        "claims": ALLC,
        "refusal": "schedule_invalid_interval",
    },
    {
        "id": "too-many-intervals",
        "data": sdata("84", [iv(str(2 * i), str(2 * i + 1)) for i in range(33)], None),
        "claims": ALLC,
        "refusal": "schedule_union_limit",
    },
    {
        "id": "union-not-list",
        "data": sdata("84", {"lower": "1"}, None),
        "claims": ALLC,
        "refusal": "schedule_invalid_union",
    },
    {
        "id": "extra-field",
        "data": {**sdata("84", bad_W, None), "window_label": "week 12"},
        "claims": ALLC,
        "refusal": "schedule_data_fields",
    },
    {
        "id": "missing-field",
        "data": {k: v for k, v in sdata("84", bad_W, None).items() if k != "available"},
        "claims": ALLC,
        "refusal": "schedule_data_fields",
    },
    {
        "id": "empty-anchor",
        "data": sdata("84", bad_W, None, anchor=""),
        "claims": ALLC,
        "refusal": "schedule_invalid_anchor",
    },
    {
        "id": "empty-claims",
        "data": sdata("84", bad_W, None),
        "claims": [],
        "refusal": "schedule_invalid_claims",
    },
    {
        "id": "unknown-claim",
        "data": sdata("84", bad_W, None),
        "claims": [{"id": "x", "claim": "coverage"}],
        "refusal": "schedule_invalid_claims",
    },
    {
        "id": "duplicate-claim",
        "data": sdata("84", bad_W, None),
        "claims": [{"id": "a", "claim": "nominal"}, {"id": "b", "claim": "nominal"}],
        "refusal": "schedule_duplicate_claim",
    },
]

# ---------------- finite_policy ----------------
SP = c.Subject(kind="study_procedure", referent="")


def blit(key, positive=True):
    return c.literal(
        subject=SP,
        predicate=c.Predicate(kind="measurement", key=key),
        value=c.Value(kind="boolean"),
        polarity="positive" if positive else "negative",
        time=None,
        qualifiers=c.Always(),
        evidence=(),
    )


def state_is(name):
    return c.literal(
        subject=SP,
        predicate=c.Predicate(kind="measurement", key="policy_state"),
        value=c.enum_value(members=(name,), comparison="eq"),
        polarity="positive",
        time=None,
        qualifiers=c.Always(),
        evidence=(),
    )


def var(identity, key):
    return {"id": identity, "values": [X(blit(key)), X(blit(key, False))]}


def evar(identity, key, members):
    return {
        "id": identity,
        "values": [
            X(
                c.literal(
                    subject=SP,
                    predicate=c.Predicate(kind="measurement", key=key),
                    value=c.enum_value(members=(m,), comparison="eq"),
                    polarity="positive",
                    time=None,
                    qualifiers=c.Always(),
                    evidence=(),
                )
            )
            for m in members
        ],
    }


def ref(name, status="known", resolution="resolved"):
    return {
        "ref": name,
        "version": "1",
        "status": status,
        "resolution": resolution,
        "basis": ["user:simulated policy choice (interface fixture)"],
    }


def act(identity, level="cohort"):
    return {
        "id": identity,
        "scope": {"level": level, "ref": "draft:stage-a"},
        "description": identity.replace("_", " "),
    }


def tr(identity, src, dst, guard, actions):
    return {"id": identity, "from": src, "to": dst, "guard": X(guard), "actions": actions}


def pdata(
    variables, states, initial, terminal, actions, transitions, prohibitions=(), invariants=(), constraints=()
):
    return {
        "scope": "draft:policy-fixture",
        "version": "interface-v1",
        "variables": variables,
        "constraints": list(constraints),
        "states": states,
        "initial": initial,
        "terminal": terminal,
        "actions": actions,
        "transitions": transitions,
        "prohibitions": list(prohibitions),
        "invariants": list(invariants),
    }


HE, LE, HS, LS = (
    blit(k)
    for k in (
        "high_dose_efficacy_superior",
        "low_dose_efficacy_superior",
        "high_dose_safety_concern",
        "low_dose_safety_concern",
    )
)


def N(p):
    return c.Not(part=p)


def AND(*p):
    return c.AllOf(parts=tuple(p))


def OR(*p):
    return c.AnyOf(parts=tuple(p))


x, y = blit("x"), blit("y")
TAUT = OR(x, N(x))
HIGH_OK = AND(HE, N(HS))
POL1_VARS = [
    var("high_eff", "high_dose_efficacy_superior"),
    var("low_eff", "low_dose_efficacy_superior"),
    var("high_safety", "high_dose_safety_concern"),
    var("low_safety", "low_dose_safety_concern"),
]
POL1_ACTIONS = [act("select_high_dose"), act("select_low_dose"), act("stop_for_futility")]
POL1_TR = [
    tr("t-high", "interim", "selected", HIGH_OK, ["select_high_dose"]),
    tr("t-low", "interim", "selected", AND(LE, N(HIGH_OK)), ["select_low_dose"]),
    tr("t-stop", "interim", "selected", AND(N(LE), N(HIGH_OK)), ["stop_for_futility"]),
]
POL1_PROH = [
    {
        "id": "no-low-dose-with-low-dose-signal",
        "state": None,
        "condition": X(LS),
        "actions": ["select_low_dose"],
        "rule": ref("user:low-dose safety prohibition"),
    }
]


def pol1(prohibitions=POL1_PROH):
    return pdata(
        POL1_VARS, ["interim", "selected"], ["interim"], ["selected"], POL1_ACTIONS, POL1_TR, prohibitions
    )


def claim(name, limit=64, identity=None):
    return {"id": identity or name, "claim": name, "witness_limit": limit}


def prow(outcome, found, witnesses, reasons=(), standing=None):
    out = {
        "outcome": outcome,
        "violations_found": found,
        "witnesses_returned": witnesses,
        "reasons": sorted(reasons),
    }
    if standing:
        out["standing"] = standing
    return out


XV = [var("x", "x")]
policy_cases = [
    {
        "id": "POL-1-covered-but-unsafe",
        "acceptance": ["POL-1"],
        "data": pol1(),
        "claims": None,
        "expect": {
            "code": "violated",
            "support_status": "known",
            "determining_ids": ["no-low-dose-with-low-dose-signal"],
            "reachability": {
                "reachable_states": ["interim", "selected"],
                "unreachable_states": [],
                "initial_nodes": 16,
                "reachable_nodes": 32,
            },
            "claims": {
                "coverage": prow("covered", 0, 0),
                "exclusivity": prow("exclusive", 0, 0),
                "prohibition": prow("violation", 3, 3, standing="known"),
                "invariant": prow("not_declared", 0, 0),
            },
        },
    },
    {
        "id": "POL-1-proposed-prohibition-keeps-raw-violation",
        "acceptance": ["POL-1", "EPI-1"],
        "data": pol1([{**POL1_PROH[0], "rule": ref("proposed reading", status="proposed")}]),
        "claims": [claim("prohibition")],
        "expect": {
            "code": "violated",
            "support_status": "proposed",
            "claims": {"prohibition": prow("violation", 3, 3, standing="proposed_refused")},
        },
    },
    {
        "id": "POL-6-witness-cap-zero",
        "acceptance": ["POL-6"],
        "data": pol1(),
        "claims": [claim("prohibition", 0)],
        "expect": {"code": "violated", "claims": {"prohibition": prow("violation", 3, 0)}},
    },
    {
        "id": "POL-2-inputs-vary-between-steps",
        "acceptance": ["POL-2"],
        "data": pdata(
            XV,
            ["a", "b", "c", "d", "z"],
            ["a"],
            ["b", "d"],
            [act("go"), act("stop"), act("wait"), act("switch")],
            [
                tr("a-c", "a", "c", x, ["go"]),
                tr("a-b", "a", "b", N(x), ["stop"]),
                tr("c-c", "c", "c", x, ["wait"]),
                tr("c-d", "c", "d", N(x), ["switch"]),
                tr("z-b", "z", "b", TAUT, ["stop"]),
            ],
        ),
        "claims": [claim("coverage"), claim("exclusivity"), claim("termination")],
        "expect": {
            "code": "violated",
            "support_status": None,
            "determining_ids": [],
            "reachability": {
                "reachable_states": ["a", "b", "c", "d"],
                "unreachable_states": ["z"],
                "initial_nodes": 2,
                "reachable_nodes": 8,
            },
            "claims": {
                "coverage": prow("covered", 0, 0),
                "exclusivity": prow("exclusive", 0, 0),
                "termination": prow("not_established", 1, 1, ["reachable_cycle"]),
            },
        },
    },
    {
        "id": "POL-3-same-actions-different-targets",
        "acceptance": ["POL-3"],
        "data": pdata(
            XV,
            ["s", "t1", "t2"],
            ["s"],
            ["t1", "t2"],
            [act("act"), act("other")],
            [
                tr("s-t1", "s", "t1", x, ["act"]),
                tr("s-t2", "s", "t2", x, ["act"]),
                tr("s-t1-not", "s", "t1", N(x), ["other"]),
            ],
        ),
        "claims": [claim("coverage"), claim("exclusivity")],
        "expect": {
            "code": "violated",
            "claims": {"coverage": prow("covered", 0, 0), "exclusivity": prow("competing", 1, 1)},
        },
    },
    {
        "id": "POL-3-identical-duplicate-rows-not-deduplicated",
        "acceptance": ["POL-3"],
        "data": pdata(
            XV,
            ["s", "t1"],
            ["s"],
            ["t1"],
            [act("act")],
            [tr("r1", "s", "t1", TAUT, ["act"]), tr("r2", "s", "t1", TAUT, ["act"])],
        ),
        "claims": [claim("exclusivity")],
        "expect": {"code": "violated", "claims": {"exclusivity": prow("competing", 2, 2)}},
    },
    {
        "id": "POL-4-terminal-exempt-from-coverage-not-invariants",
        "acceptance": ["POL-4"],
        "data": pdata(
            XV,
            ["s", "end"],
            ["s"],
            ["end"],
            [act("finish")],
            [tr("s-end", "s", "end", TAUT, ["finish"])],
            invariants=[
                {
                    "id": "x-at-end",
                    "state": "end",
                    "condition": X(x),
                    "actions": [],
                    "rule": ref("user:end-state requirement"),
                }
            ],
        ),
        "claims": [claim("coverage"), claim("invariant")],
        "expect": {
            "code": "violated",
            "claims": {
                "coverage": prow("covered", 0, 0),
                "invariant": prow("violation", 1, 1, standing="known"),
            },
        },
    },
    {
        "id": "POL-5-acyclic-dead-end-is-not-termination",
        "acceptance": ["POL-5"],
        "data": pdata(
            XV,
            ["s", "m", "end"],
            ["s"],
            ["end"],
            [act("go"), act("finish")],
            [tr("s-m", "s", "m", TAUT, ["go"]), tr("m-end", "m", "end", x, ["finish"])],
        ),
        "claims": [claim("coverage"), claim("termination")],
        "expect": {
            "code": "violated",
            "claims": {
                "coverage": prow("gap", 1, 1),
                "termination": prow("not_established", 1, 1, ["dead_end"]),
            },
        },
    },
    {
        "id": "POL-5-terminating-policy",
        "acceptance": ["POL-5"],
        "data": pdata(
            XV, ["s", "end"], ["s"], ["end"], [act("finish")], [tr("s-end", "s", "end", TAUT, ["finish"])]
        ),
        "claims": [claim("coverage"), claim("exclusivity"), claim("termination")],
        "expect": {
            "code": "satisfied",
            "claims": {
                "coverage": prow("covered", 0, 0),
                "exclusivity": prow("exclusive", 0, 0),
                "termination": prow("all_paths_terminate", 0, 0),
            },
        },
    },
    {
        "id": "POL-7-empty-feasible-initial-model",
        "acceptance": ["POL-7"],
        "data": pdata(
            XV,
            ["s", "end"],
            ["s"],
            ["end"],
            [act("finish")],
            [tr("s-end", "s", "end", TAUT, ["finish"])],
            constraints=[
                {"id": "contradiction", "condition": X(AND(x, N(x))), "rule": ref("user:constraint")}
            ],
        ),
        "claims": None,
        "expect": {
            "code": "inconsistent_domain",
            "claims": {
                k: prow("inconsistent_domain", 0, 0)
                for k in ("coverage", "exclusivity", "prohibition", "invariant")
            },
        },
    },
    {
        "id": "POL-7-transition-into-infeasible-target",
        "acceptance": ["POL-7"],
        "data": pdata(
            XV,
            ["s", "t", "end"],
            ["s"],
            ["end"],
            [act("go"), act("stop")],
            [
                tr("s-t", "s", "t", x, ["go"]),
                tr("s-end", "s", "end", N(x), ["stop"]),
                tr("t-end", "t", "end", TAUT, ["stop"]),
            ],
            constraints=[
                {"id": "t-needs-x", "condition": X(OR(N(state_is("t")), x)), "rule": ref("user:constraint")},
                {
                    "id": "t-needs-not-x",
                    "condition": X(OR(N(state_is("t")), N(x))),
                    "rule": ref("user:constraint"),
                },
            ],
        ),
        "claims": [claim("coverage"), claim("termination")],
        "expect": {
            "code": "violated",
            "transition_target_conflicts": ["s-t"],
            "reachability": {
                "reachable_states": ["s", "end"],
                "unreachable_states": ["t"],
                "initial_nodes": 2,
                "reachable_nodes": 4,
            },
            "claims": {
                "coverage": prow("covered", 0, 0),
                "termination": prow("not_established", 1, 1, ["transition_target_infeasible"]),
            },
        },
    },
]
p_ok = pdata(XV, ["s", "end"], ["s"], ["end"], [act("finish")], [tr("s-end", "s", "end", TAUT, ["finish"])])
policy_malformed = [
    {
        "id": "reserved-variable",
        "data": {**p_ok, "variables": [var("ps", "policy_state")]},
        "claims": None,
        "refusal": "policy_reserved_variable",
    },
    {
        "id": "undeclared-variable-in-guard",
        "data": {**p_ok, "transitions": [tr("s-end", "s", "end", y, ["finish"])]},
        "claims": None,
        "refusal": "policy_undeclared_variable",
    },
    {
        "id": "terminal-outgoing",
        "data": {
            **p_ok,
            "transitions": [
                tr("s-end", "s", "end", TAUT, ["finish"]),
                tr("end-s", "end", "s", TAUT, ["finish"]),
            ],
        },
        "claims": None,
        "refusal": "policy_terminal_outgoing",
    },
    {
        "id": "invariant-with-actions",
        "data": {
            **p_ok,
            "invariants": [
                {"id": "i", "state": None, "condition": X(x), "actions": ["finish"], "rule": ref("r")}
            ],
        },
        "claims": None,
        "refusal": "policy_invariant_actions",
    },
    {
        "id": "unknown-action",
        "data": {**p_ok, "transitions": [tr("s-end", "s", "end", TAUT, ["dose_escalate"])]},
        "claims": None,
        "refusal": "policy_unknown_action",
    },
    {
        "id": "unknown-state-in-transition",
        "data": {**p_ok, "transitions": [tr("s-q", "s", "q", TAUT, ["finish"])]},
        "claims": None,
        "refusal": "policy_unknown_state",
    },
    {
        "id": "unknown-state-literal",
        "data": {**p_ok, "transitions": [tr("s-end", "s", "end", state_is("q"), ["finish"])]},
        "claims": None,
        "refusal": "policy_unknown_state",
    },
    {
        "id": "no-initial",
        "data": {**p_ok, "initial": []},
        "claims": None,
        "refusal": "policy_invalid_initial",
    },
    {
        "id": "duplicate-transition-id",
        "data": {
            **p_ok,
            "transitions": [
                tr("s-end", "s", "end", x, ["finish"]),
                tr("s-end", "s", "end", N(x), ["finish"]),
            ],
        },
        "claims": None,
        "refusal": "policy_duplicate_id",
    },
    {
        "id": "bad-action-scope",
        "data": {
            **p_ok,
            "actions": [{"id": "finish", "scope": {"level": "site", "ref": "x"}, "description": "finish"}],
        },
        "claims": None,
        "refusal": "policy_invalid_action",
    },
    {
        "id": "proposed-rule-missing-basis",
        "data": {
            **p_ok,
            "invariants": [
                {
                    "id": "i",
                    "state": None,
                    "condition": X(x),
                    "actions": [],
                    "rule": {**ref("r"), "basis": []},
                }
            ],
        },
        "claims": None,
        "refusal": "policy_invalid_rule",
    },
    {
        "id": "extra-field",
        "data": {**p_ok, "priority": "row_order"},
        "claims": None,
        "refusal": "policy_data_fields",
    },
    {
        "id": "witness-limit-too-large",
        "data": p_ok,
        "claims": [claim("coverage", 65)],
        "refusal": "policy_invalid_claims",
    },
    {
        "id": "witness-limit-bool",
        "data": p_ok,
        "claims": [claim("coverage", True)],
        "refusal": "policy_invalid_claims",
    },
    {
        "id": "duplicate-claim",
        "data": p_ok,
        "claims": [claim("coverage", 1, "a"), claim("coverage", 1, "b")],
        "refusal": "policy_duplicate_claim",
    },
    {
        "id": "valuation-limit",
        "data": {**p_ok, "variables": [evar(f"v{i}", f"v{i}", ("a", "b", "c")) for i in range(8)]},
        "claims": None,
        "refusal": "policy_valuation_limit",
    },
]

# ---------------- binomial_design ----------------
ROLES = ("fixed_n", "iid_binary", "alignment")


def assumption(role, status="known"):
    return {
        "role": role,
        "ref": f"user:{role} assumption (interface fixture)",
        "version": "1",
        "status": status,
        "resolution": "resolved",
        "basis": ["user:simulated planning choice (interface fixture)"],
    }


def bdata(n, k, p0, p1, model="fixed_n_iid_bernoulli", direction="greater", assumptions=None):
    return {
        "scope": "draft:phase2-response",
        "model": model,
        "direction": direction,
        "n": n,
        "critical_count": k,
        "p0": p0,
        "p1": p1,
        "assumptions": assumptions if assumptions is not None else [assumption(r) for r in ROLES],
    }


def tail(n, k, p):
    p = Fraction(p)
    return sum((Fraction(math.comb(n, i)) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)), Fraction(0))


def canon(q):
    q = Fraction(q)
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


def disp(q):
    q = Fraction(q)
    return str(
        (Decimal(q.numerator) / Decimal(q.denominator)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    )


def bexp(n, k, p0, p1, code="computed", **extra):
    a, b = tail(n, k, p0), tail(n, k, p1)
    return {
        "code": code,
        "null_rejection_probability": canon(a),
        "power": canon(b),
        "display": {"null_rejection_probability": disp(a), "power": disp(b), "rounding": "half_even_4dp"},
        **extra,
    }


binomial_cases = [
    {
        "id": "STA-1-k2",
        "acceptance": ["STA-1"],
        "data": bdata(2, 2, "1/2", "3/4"),
        "claims": [],
        "expect": {
            **bexp(2, 2, "1/2", "3/4"),
            "support_status": "known",
            "application": {"code": "not_withheld_by_assumptions", "reasons": []},
        },
    },
    {
        "id": "STA-1-k1",
        "acceptance": ["STA-1"],
        "data": bdata(2, 1, "1/2", "3/4"),
        "claims": [],
        "expect": bexp(2, 1, "1/2", "3/4"),
    },
    {
        "id": "STA-2-k0-always-rejects",
        "acceptance": ["STA-2"],
        "data": bdata(3, 0, "0", "1"),
        "claims": [],
        "expect": bexp(3, 0, "0", "1"),
    },
    {
        "id": "STA-2-k-n-plus-1-never-rejects",
        "acceptance": ["STA-2"],
        "data": bdata(3, 4, "0", "1"),
        "claims": [],
        "expect": bexp(3, 4, "0", "1"),
    },
    {
        "id": "STA-2-p0-zero-p1-one",
        "acceptance": ["STA-2"],
        "data": bdata(3, 3, "0", "1"),
        "claims": [],
        "expect": bexp(3, 3, "0", "1"),
    },
    {
        "id": "n10-k7",
        "acceptance": ["STA-1"],
        "data": bdata(10, 7, "1/2", "7/10"),
        "claims": [],
        "expect": bexp(10, 7, "1/2", "7/10"),
    },
    {
        "id": "claims-alpha-bound-and-power",
        "acceptance": ["STA-1"],
        "data": bdata(2, 2, "1/2", "3/4"),
        "claims": [
            {"id": "alpha", "quantity": "null_rejection_probability", "comparison": "<=", "value": "1/4"},
            {"id": "power-target", "quantity": "power", "comparison": ">=", "value": "3/5"},
        ],
        "expect": {
            **bexp(2, 2, "1/2", "3/4", code="not_satisfied"),
            "claim_outcomes": {"alpha": "satisfied", "power-target": "not_satisfied"},
            "blockers_include": ["binomial_claim_not_satisfied:power-target"],
        },
    },
    {
        "id": "STA-3-survival-model-unsupported",
        "acceptance": ["STA-3"],
        "data": bdata(2, 2, "1/2", "3/4", model="exponential_time_to_event"),
        "claims": [],
        "expect": {
            "code": "unsupported_method",
            "computed": False,
            "blockers_include": ["binomial_unsupported_method"],
        },
    },
    {
        "id": "STA-3-less-direction-unsupported",
        "acceptance": ["STA-3"],
        "data": bdata(2, 2, "1/2", "3/4", direction="less"),
        "claims": [],
        "expect": {"code": "unsupported_method", "computed": False},
    },
    {
        "id": "STA-4-missing-alignment-keeps-arithmetic",
        "acceptance": ["STA-4"],
        "data": bdata(2, 2, "1/2", "3/4", assumptions=[assumption("fixed_n"), assumption("iid_binary")]),
        "claims": [],
        "expect": {
            **bexp(2, 2, "1/2", "3/4"),
            "assumption_coverage": {"fixed_n": "declared", "iid_binary": "declared", "alignment": "missing"},
            "blockers_include": ["binomial_assumption_missing:alignment"],
            "support_status": "proposed",
            "application": {"code": "withheld", "reasons": ["assumption_missing:alignment"]},
        },
    },
    {
        "id": "STA-4-proposed-alignment",
        "acceptance": ["STA-4", "EPI-1"],
        "data": bdata(
            2,
            2,
            "1/2",
            "3/4",
            assumptions=[
                assumption("fixed_n"),
                assumption("iid_binary"),
                assumption("alignment", "proposed"),
            ],
        ),
        "claims": [],
        "expect": {
            **bexp(2, 2, "1/2", "3/4"),
            "support_status": "proposed",
            "application": {
                "code": "withheld",
                "reasons": ["assumption_not_accepted:user:alignment assumption (interface fixture)"],
            },
        },
    },
]
b_ok = bdata(2, 2, "1/2", "3/4")
binomial_malformed = [
    {"id": "n-zero", "data": {**b_ok, "n": 0}, "claims": [], "refusal": "binomial_invalid_n"},
    {"id": "n-bool", "data": {**b_ok, "n": True}, "claims": [], "refusal": "binomial_invalid_n"},
    {"id": "n-ceiling", "data": {**b_ok, "n": 513}, "claims": [], "refusal": "binomial_n_ceiling"},
    {
        "id": "k-negative",
        "data": {**b_ok, "critical_count": -1},
        "claims": [],
        "refusal": "binomial_invalid_critical_count",
    },
    {
        "id": "k-too-large",
        "data": {**b_ok, "critical_count": 4},
        "claims": [],
        "refusal": "binomial_invalid_critical_count",
    },
    {
        "id": "p-equal",
        "data": {**b_ok, "p1": "1/2"},
        "claims": [],
        "refusal": "binomial_invalid_probabilities",
    },
    {
        "id": "p-reversed",
        "data": {**b_ok, "p0": "3/4", "p1": "1/2"},
        "claims": [],
        "refusal": "binomial_invalid_probabilities",
    },
    {
        "id": "p-above-one",
        "data": {**b_ok, "p1": "3/2"},
        "claims": [],
        "refusal": "binomial_invalid_probabilities",
    },
    {"id": "p-float", "data": {**b_ok, "p0": 0.5}, "claims": [], "refusal": "binomial_invalid_rational"},
    {"id": "p-decimal", "data": {**b_ok, "p0": "0.5"}, "claims": [], "refusal": "binomial_invalid_rational"},
    {
        "id": "p-bits",
        "data": {**b_ok, "p0": "1/" + str(1 << 256)},
        "claims": [],
        "refusal": "binomial_rational_bit_limit",
    },
    {
        "id": "no-assumptions",
        "data": {**b_ok, "assumptions": []},
        "claims": [],
        "refusal": "binomial_invalid_assumption",
    },
    {
        "id": "bad-role",
        "data": {**b_ok, "assumptions": [{**assumption("fixed_n"), "role": "normality"}]},
        "claims": [],
        "refusal": "binomial_invalid_assumption",
    },
    {
        "id": "duplicate-assumption",
        "data": {**b_ok, "assumptions": [assumption("fixed_n"), assumption("fixed_n")]},
        "claims": [],
        "refusal": "binomial_duplicate_assumption",
    },
    {"id": "extra-field", "data": {**b_ok, "alpha": "1/20"}, "claims": [], "refusal": "binomial_data_fields"},
    {
        "id": "claim-value-out-of-range",
        "data": b_ok,
        "claims": [{"id": "a", "quantity": "power", "comparison": ">=", "value": "2"}],
        "refusal": "binomial_invalid_claims",
    },
    {
        "id": "claim-strict-comparison",
        "data": b_ok,
        "claims": [{"id": "a", "quantity": "power", "comparison": ">", "value": "1/2"}],
        "refusal": "binomial_invalid_claims",
    },
    {
        "id": "duplicate-claim-id",
        "data": b_ok,
        "claims": [
            {"id": "a", "quantity": "power", "comparison": ">=", "value": "1/2"},
            {"id": "a", "quantity": "power", "comparison": "<=", "value": "1"},
        ],
        "refusal": "binomial_duplicate_claim",
    },
]

rationals = {
    "valid": {
        "0": "0",
        "-0": "0",
        "7": "7",
        "-7": "-7",
        "2/4": "1/2",
        "-6/4": "-3/2",
        "14/4": "7/2",
        "84/1": "84",
        str((1 << 256) - 1): str((1 << 256) - 1),
    },
    "invalid_syntax": [
        "",
        " 1",
        "1 ",
        "+1",
        "1.5",
        "1e3",
        "NaN",
        "inf",
        "1/0",
        "1/-2",
        "01",
        "1/02",
        "1//2",
        "--1",
        "½",
    ],
    "invalid_type": [1, 1.5, True, None, ["1"]],
    "over_bit_limit": [str(1 << 256), "1/" + str(1 << 256)],
}

for name, payload in {
    "schedule.json": {
        "interface_version": 1,
        "kind": "schedule_coverage",
        "cases": schedule_cases,
        "malformed": schedule_malformed,
    },
    "policy.json": {
        "interface_version": 1,
        "kind": "finite_policy",
        "cases": policy_cases,
        "malformed": policy_malformed,
    },
    "binomial.json": {
        "interface_version": 1,
        "kind": "binomial_design",
        "cases": binomial_cases,
        "malformed": binomial_malformed,
    },
    "rationals.json": {"interface_version": 1, **rationals},
}.items():
    (HERE / name).write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n")
    print(name, len(payload.get("cases", [])), "cases", len(payload.get("malformed", [])), "malformed")
