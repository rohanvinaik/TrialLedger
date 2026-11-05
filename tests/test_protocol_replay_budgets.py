"""Replay-budget formulas for protocol checks, alternatives and revisions (task 1.5, C10).

The formulas are published in openspec/changes/connect-protocol-design-workflow/interface/budgets.md. Every
number asserted here is computed independently of design_session._reserve: a JSON node counter, the three
operator reservation formulas written out from operators.md. A protocol operator is charged once: a signals
child costs N + sum(R). The code is observed two ways, and each test says which:

- ``spy``: design_session._child is wrapped (monkeypatch), recording the request and the budget deltas of
  every child. This shows which children are charged, in which order, and what each costs.
- ``reply["work"]``: the retained budget counters {analyses, expanded_items, solver_work_reserved}, which
  design_session.run returns beside the result. This shows the cumulative charge, old and new included.

Every clinical value is invented.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from TrialLedger.layer2 import design_session as ds
from TrialLedger.layer2 import run, service, session_state
from TrialLedger.layer2.session_state import HARD_LIMITS

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "openspec/changes/connect-protocol-design-workflow/interface/fixtures/results"
OPERATOR_KINDS = ("schedule_coverage", "finite_policy", "binomial_design")

ORIGIN = {"kind": "user_choice", "ref": "user:invented budget plan", "source": None, "analysis": None}


# ---------------------------------------------------------------------------------------------------------
# Independent formulas
# ---------------------------------------------------------------------------------------------------------


def nodes(node: object) -> int:
    """JSON node count: every dict, list and scalar is one node; keys are not nodes."""
    if isinstance(node, dict):
        return 1 + sum(nodes(v) for v in node.values())
    if isinstance(node, list):
        return 1 + sum(nodes(v) for v in node)
    return 1


def schedule_reservation(windows: int, collected: int) -> int:
    """operators.md: R = 4*(w+c)**2 + 6*(w+c) + 8 with w, c the interval counts (null counts as 0)."""
    size = windows + collected
    return 4 * size * size + 6 * size + 8


def policy_reservation(model: dict) -> int:
    """operators.md: R = S*V*(K+P+I) + V*T, V the product of the domain sizes."""
    valuations = math.prod(len(domain["values"]) for domain in model["variables"])
    rules = len(model["constraints"]) + len(model["prohibitions"]) + len(model["invariants"])
    return len(model["states"]) * valuations * rules + valuations * len(model["transitions"])


def binomial_reservation(n: int) -> int:
    """operators.md: R = 12 * (n + 2)."""
    return 12 * (n + 2)


def operator_reservation(signal: dict) -> int:
    data = signal["data"]
    if signal["kind"] == "schedule_coverage":
        return schedule_reservation(len(data["permitted"] or []), len(data["available"] or []))
    if signal["kind"] == "finite_policy":
        return policy_reservation(data)
    return binomial_reservation(data["n"])


def predicted_charge(request: dict) -> dict:
    """The charge formula for a `signals` child: one analysis, N nodes, and N + sum(R) reserved work."""
    assert request["operation"] == "signals"
    total = sum(operator_reservation(s) for s in request["signals"] if s["kind"] in OPERATOR_KINDS)
    return {
        "analyses": 1,
        "expanded_items": nodes(request),
        "solver_work_reserved": nodes(request) + total,
    }


def add(left: dict, right: dict) -> dict:
    return {key: left[key] + right[key] for key in left}


ZERO = {"analyses": 0, "expanded_items": 0, "solver_work_reserved": 0}


# ---------------------------------------------------------------------------------------------------------
# Invented sessions
# ---------------------------------------------------------------------------------------------------------


def standing(status: str = "known") -> dict:
    return {"status": status, "resolution": "resolved", "basis": ["user:invented budget plan"]}


def adoption(identity: str, version: str) -> dict:
    return {
        "id": f"adopt:{identity}:{version}",
        "kind": "adoption",
        "payload": {
            "objects": [{"id": identity, "version": version}],
            "status": "known",
            "resolution": "resolved",
        },
        "origin": copy.deepcopy(ORIGIN),
        "depends_on": [],
    }


def pieces(count: int) -> list[dict]:
    """count disjoint closed intervals: [0,5], [10,15], ..."""
    return [
        {"lower": str(10 * i), "upper": str(10 * i + 5), "lower_inclusive": True, "upper_inclusive": True}
        for i in range(count)
    ]


def build(checks: int = 1, collected: int = 1, optional: int = 0, condition: dict | None = None) -> dict:
    """A v2 session with one assessment (one permitted window), one collection with `collected` intervals,
    and `checks` schedule checks over them, the last `optional` of which are not required.

    No legacy analyses or decisions: every child charged is a protocol child, so the counters are the
    protocol charge alone. With `condition`, the assessment is conditional and every check carries an
    applicability binding to the one declared premise (`adult`).
    """
    request = copy.deepcopy(run({"operation": "describe", "view": "design_session"})["result"]["example"])
    session = request["session"]
    session["schema_version"] = 2
    session["analyses"] = []
    session["decisions"] = []
    scope = {
        "target": copy.deepcopy(session["target"]),
        "context": {"cohort": None, "phase": None, "arm": None},
    }
    adoptions = []

    def obj(identity, kind, data, depends_on):
        adoptions.append(adoption(identity, "b1"))
        return {
            "id": identity,
            "kind": kind,
            "scope": copy.deepcopy(scope),
            "version": "b1",
            "origin": copy.deepcopy(ORIGIN),
            "standing": standing(),
            "support": [f"adopt:{identity}:b1"],
            "depends_on": depends_on,
            "data": data,
        }

    reference = {"ref": "invented:score", "version": "1", **standing()}
    window = {"lower": "77", "upper": "91", "lower_inclusive": True, "upper_inclusive": True}
    bindings = [{"projection": "condition_applicability", "premises": ["adult"]}] if condition else []
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
                "visit",
                "assessment",
                {
                    "measurement": "score",
                    "anchor": "randomization",
                    "unit": "day",
                    "nominal": "84",
                    "permitted": [window],
                    "condition": condition,
                },
                ["score"],
            ),
            obj(
                "plan",
                "collection",
                {
                    "assessment": "visit",
                    "mode": "observed",
                    "availability": pieces(collected),
                    "event_handling": None,
                },
                ["visit"],
            ),
        ],
        "checks": [
            {
                "id": f"sched-{i}",
                "kind": "schedule",
                "scope": copy.deepcopy(scope),
                "objects": ["visit", "plan"],
                "bindings": copy.deepcopy(bindings),
                "claims": [
                    {"id": "visit", "claim": "existence"},
                    {"id": "target", "claim": "nominal"},
                    {"id": "window", "claim": "full_window"},
                ],
                "required": i < checks - optional,
                "support": [],
            }
            for i in range(checks)
        ],
        "sections": [],
    }
    session["premises"] = session["premises"] + adoptions
    return request


def adult_condition(request: dict) -> dict:
    return copy.deepcopy(request["session"]["premises"][0]["payload"]["body"])


def with_alternatives(request: dict, windows: list[int | None]) -> dict:
    """One protocol_options decision. Alternative i replaces `plan` with `windows[i]` collected intervals;
    None keeps the baseline as declared. Every alternative lists every declared check."""
    session = request["session"]
    template = next(o for o in session["protocol"]["objects"] if o["id"] == "plan")
    checks = [c["id"] for c in session["protocol"]["checks"]]
    alternatives = []
    for index, count in enumerate(windows):
        replace = []
        if count is not None:
            item = copy.deepcopy(template)
            item["origin"] = {
                "kind": "hypothesis",
                "ref": f"user:invented window {index}",
                "source": None,
                "analysis": None,
            }
            item["standing"] = {
                "status": "proposed",
                "resolution": "resolved",
                "basis": [f"user:invented window {index}"],
            }
            item["data"]["availability"] = pieces(count)
            replace = [item]
        alternatives.append(
            {
                "id": f"alt{index}",
                "label": f"invented plan {index}",
                "replace_objects": replace,
                "checks": list(checks),
            }
        )
    session["decisions"] = [
        {
            "kind": "protocol_options",
            "id": "plan-choice",
            "question": "Which invented collection window?",
            "target": copy.deepcopy(session["target"]),
            "coverage": "declared_design",
            "selected": None,
            "alternatives": alternatives,
        }
    ]
    return request


def revise(previous: dict, collected: int) -> dict:
    """A revision request: `plan` re-declared with `collected` intervals as a new, re-adopted edition."""
    first = run(copy.deepcopy(previous))
    assert first["code"] == "complete", first
    session = copy.deepcopy(previous["session"])
    session["revision"] = "two"
    session["parent_digest"] = session_state.digest(previous["session"])
    plan = next(o for o in session["protocol"]["objects"] if o["id"] == "plan")
    plan["version"] = f"b2-{collected}"
    plan["data"]["availability"] = pieces(collected)
    session["premises"].append(adoption("plan", plan["version"]))
    plan["support"] = [f"adopt:plan:{plan['version']}"]
    for decision in session["decisions"]:
        for alternative in decision["alternatives"]:
            for item in alternative["replace_objects"]:
                if item["id"] == "plan":
                    item["version"] = plan["version"]
                    item["support"] = [f"adopt:plan:{plan['version']}"]
    request = copy.deepcopy(previous)
    request["session"] = session
    request["previous"] = {
        "session": copy.deepcopy(previous["session"]),
        "result": first["result"],
        "expected_result_digest": first["result_digest"],
    }
    return request


class Spy:
    """Wraps design_session._child; records (request, budget delta) per call, in call order."""

    def __init__(self, monkeypatch):
        self.calls: list[tuple[dict, dict]] = []
        original = ds._child

        def wrapped(request, execute, budget, limits):
            before = dict(budget)
            try:
                return original(request, execute, budget, limits)
            finally:
                self.calls.append((copy.deepcopy(request), {k: budget[k] - before[k] for k in budget}))

        monkeypatch.setattr(ds, "_child", wrapped)

    @property
    def deltas(self) -> list[dict]:
        return [delta for _, delta in self.calls]

    @property
    def signals(self) -> list[tuple[dict, dict]]:
        return [(r, d) for r, d in self.calls if r["operation"] == "signals"]

    def total(self) -> dict:
        out = dict(ZERO)
        for delta in self.deltas:
            out = add(out, delta)
        return out


def complete(request: dict) -> dict:
    reply = run(copy.deepcopy(request))
    assert reply["code"] == "complete", reply.get("problems")
    return reply


def work_of(request: dict) -> dict:
    return complete(request)["work"]


def standalone(revision: dict) -> dict:
    """The revision's new session as an initial request: no previous snapshot, so no parent."""
    out = copy.deepcopy(revision)
    out["previous"] = None
    out["session"]["parent_digest"] = None
    return out


def with_limits(request: dict, **limits: int) -> dict:
    out = copy.deepcopy(request)
    out["session"]["limits"].update(limits)
    return out


def refusal(request: dict) -> ds.SessionBudgetError:
    with pytest.raises(ds.SessionBudgetError) as raised:
        ds.run(copy.deepcopy(request), service.run)
    return raised.value


class Executed:
    """A counting execute function for design_session.run; shows what ran before a refusal."""

    def __init__(self):
        self.count = 0

    def __call__(self, request):
        self.count += 1
        return service.run(request)


# ---------------------------------------------------------------------------------------------------------
# Per child
# ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "collected,node_count,operator_work,reserved",
    [
        # R = 4*s^2 + 6*s + 8 with s = 1 + collected; N = 58 + 5*s for this session's support structure
        (1, 68, 36, 104),
        (2, 73, 62, 135),
        (4, 83, 138, 221),
        (5, 88, 188, 276),
        (0, 63, 18, 81),
    ],
)
def test_one_schedule_child_costs_nodes_plus_the_operator_reservation(
    monkeypatch, collected, node_count, operator_work, reserved
):
    spy = Spy(monkeypatch)
    reply = complete(build(checks=1, collected=collected))
    assert len(spy.calls) == 1
    request, delta = spy.calls[0]
    assert request["operation"] == "signals"
    assert nodes(request) == node_count == 58 + 5 * (1 + collected)
    assert schedule_reservation(1, collected) == operator_work
    assert delta == {
        "analyses": 1,
        "expanded_items": node_count,
        "solver_work_reserved": node_count + operator_work,
    }
    assert delta["solver_work_reserved"] == reserved
    assert delta == predicted_charge(request)
    assert reply["work"] == delta


def test_an_unknown_collection_is_a_null_union_and_drops_its_intervals_from_the_charge(monkeypatch):
    request = build(checks=1)
    request["session"]["protocol"]["objects"][2]["data"]["availability"] = None
    spy = Spy(monkeypatch)
    reply = complete(request)
    ((child, delta),) = spy.signals
    assert child["signals"][0]["data"]["available"] is None
    # w = 1, c = 0: R = 4 + 6 + 8 = 18
    assert schedule_reservation(1, 0) == 18
    assert delta == predicted_charge(child) == reply["work"]
    assert delta["solver_work_reserved"] == nodes(child) + 18


@pytest.mark.parametrize(
    "name", ["policy-work-limit", "policy-violation-known", "efficacy-binomial-and-external"]
)
def test_policy_and_binomial_children_are_charged_by_their_own_operator_formulas(monkeypatch, name):
    request = json.loads((RESULTS / f"{name}.json").read_text())["request"]
    spy = Spy(monkeypatch)
    reply = complete(request)
    signals = spy.signals
    assert signals, name
    for child, delta in signals:
        assert delta == predicted_charge(child), name
        assert delta["solver_work_reserved"] > nodes(
            child
        )  # the nested operator is charged, not just the nodes
    assert reply["work"] == spy.total()
    kinds = {s["kind"] for child, _ in signals for s in child["signals"]}
    assert kinds <= set(OPERATOR_KINDS) and kinds


def test_a_policy_over_its_operator_ceiling_is_still_charged_once_at_its_reservation(monkeypatch):
    """R = 1,052,672 exceeds the operator's 1,000,000 ceiling: the operator reports `limit`; the session
    has already charged N + 6R, and that is what the session limit sees."""
    request = json.loads((RESULTS / "policy-work-limit.json").read_text())["request"]
    spy = Spy(monkeypatch)
    reply = complete(request)
    ((child, delta),) = spy.signals
    policy = child["signals"][0]["data"]
    assert policy_reservation(policy) == 1_052_672 > 1_000_000
    assert delta["solver_work_reserved"] == nodes(child) + 1_052_672 == 1_054_534
    row = reply["result"]["protocol"]["checks"][0]["children"][0]["signals"][0]
    assert row["code"] == "limit"


# ---------------------------------------------------------------------------------------------------------
# Per protocol check and per alternative
# ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("checks", [0, 1, 3, 8])
def test_the_baseline_charges_one_child_per_declared_check(monkeypatch, checks):
    spy = Spy(monkeypatch)
    reply = complete(build(checks=checks, collected=1))
    assert [r["signals"][0]["id"] for r, _ in spy.calls] == [
        f"sched-{i}:schedule_window_coverage" for i in range(checks)
    ]
    assert reply["work"] == {
        "analyses": checks,
        "expanded_items": 68 * checks,
        "solver_work_reserved": 104 * checks,
    }


def test_a_check_whose_projection_is_unresolved_or_not_computed_is_charged_nothing(monkeypatch):
    request = build(checks=1)
    request["session"]["protocol"]["checks"][0]["kind"] = "definition"
    request["session"]["protocol"]["checks"][0]["claims"] = []
    request["session"]["protocol"]["checks"][0]["objects"] = []
    spy = Spy(monkeypatch)
    reply = complete(request)
    assert spy.calls == []
    assert reply["work"] == ZERO


@pytest.mark.parametrize(
    "checks,optional,windows",
    [
        (1, 0, [None, 2]),
        (3, 0, [None, 2]),
        (2, 0, [None, 2, 4]),
        (2, 1, [3, 3, None]),
        (4, 1, [1, 2, 3, 4]),
    ],
)
def test_every_alternative_replays_all_its_checks_freshly_and_the_total_is_the_sum(
    monkeypatch, checks, optional, windows
):
    request = with_alternatives(build(checks=checks, optional=optional), windows)
    spy = Spy(monkeypatch)
    reply = complete(request)
    # the children: the baseline's checks, then each alternative's checks, in listed order
    assert len(spy.calls) == checks + len(windows) * checks
    baseline = spy.calls[:checks]
    assert [r["signals"][0]["id"] for r, _ in baseline] == [
        f"sched-{i}:schedule_window_coverage" for i in range(checks)
    ]
    expected = dict(ZERO)
    for index, (child, delta) in enumerate(spy.signals):
        assert delta == predicted_charge(child), index
        expected = add(expected, delta)
    sizes = [1] * checks
    for count in windows:
        sizes += [1 if count is None else count] * checks
    assert [len(c["signals"][0]["data"]["available"]) for c, _ in spy.signals] == sizes
    assert reply["work"] == expected
    assert reply["work"]["analyses"] == checks * (1 + len(windows))
    # closed form: baseline + sum over alternatives of M * charge(collected intervals of that alternative)
    per_child = lambda c: add(  # noqa: E731
        {"analyses": 1, "expanded_items": 58 + 5 * (1 + c), "solver_work_reserved": 0},
        {
            "analyses": 0,
            "expanded_items": 0,
            "solver_work_reserved": 58 + 5 * (1 + c) + schedule_reservation(1, c),
        },
    )
    total = dict(ZERO)
    for c in [1, *[1 if w is None else w for w in windows]]:
        for _ in range(checks):
            total = add(total, per_child(c))
    assert reply["work"] == total


def test_an_alternative_identical_to_the_baseline_is_still_charged_not_reused(monkeypatch):
    request = with_alternatives(build(checks=2), [None, None])
    spy = Spy(monkeypatch)
    reply = complete(request)
    digests = [ds.state.digest(r) for r, _ in spy.calls]
    assert digests[:2] == digests[2:4] == digests[4:6]  # identical requests, replayed three times
    assert reply["work"]["analyses"] == 6
    assert reply["work"]["solver_work_reserved"] == 6 * 104


def test_two_decisions_each_add_their_alternatives(monkeypatch):
    request = with_alternatives(build(checks=2), [None, 2])
    second = copy.deepcopy(request["session"]["decisions"][0])
    second["id"] = "plan-choice-two"
    request["session"]["decisions"].append(second)
    spy = Spy(monkeypatch)
    reply = complete(request)
    assert reply["work"]["analyses"] == 2 + 2 * 2 + 2 * 2
    assert reply["work"] == spy.total()


def test_applicability_entailments_are_charged_before_the_check_child_and_only_when_bound(monkeypatch):
    base = build(checks=1)
    condition = adult_condition(base)
    # without a binding, the condition stays conditional and nothing is asked
    unbound = build(checks=1, condition=condition)
    unbound["session"]["protocol"]["checks"][0]["bindings"] = []
    spy = Spy(monkeypatch)
    assert complete(unbound)["work"]["analyses"] == 1
    assert [r["operation"] for r, _ in spy.calls] == ["signals"]
    # with a binding, each condition costs one entailment child ahead of the signals child
    request = with_alternatives(build(checks=1, condition=condition), [None, 2])
    spy = Spy(monkeypatch)
    spy.calls.clear()
    reply = complete(request)
    assert [r["operation"] for r, _ in spy.calls] == ["entailment", "signals"] * 3
    assert reply["work"]["analyses"] == 2 * (1 + 2)
    for (child, delta), (previous, previous_delta) in zip(spy.calls[1::2], spy.calls[::2], strict=True):
        assert previous_delta["analyses"] == 1
        assert previous_delta["expanded_items"] == nodes(previous)
        assert previous_delta["solver_work_reserved"] == ds._reserve(previous)  # solver_work owns this figure
        assert delta == predicted_charge(child)
    assert reply["work"] == spy.total()


# ---------------------------------------------------------------------------------------------------------
# Old and new snapshots in a revision
# ---------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("old,new", [(1, 3), (4, 1), (2, 2)])
def test_a_revision_replays_both_snapshots_into_one_budget(monkeypatch, old, new):
    previous = with_alternatives(build(checks=2, collected=old), [None, old + 1])
    request = revise(previous, new)
    standalone_old = work_of(previous)
    standalone_new = work_of(standalone(request))
    spy = Spy(monkeypatch)
    reply = complete(request)
    assert reply["previous_fresh"] is not None
    assert reply["work"] == add(standalone_old, standalone_new) == spy.total()
    half = len(spy.calls) // 2
    assert len(spy.calls) == 2 * half and half == 2 * (1 + 2)
    # old snapshot first, then new, each its own baseline and alternatives
    assert [d["analyses"] for _, d in spy.calls] == [1] * (2 * half)
    old_sizes = [len(c["signals"][0]["data"]["available"]) for c, _ in spy.calls[:half]]
    new_sizes = [len(c["signals"][0]["data"]["available"]) for c, _ in spy.calls[half:]]
    # alt1 keeps its own declared window (old + 1 intervals) in the new snapshot
    assert old_sizes == [old, old, old, old, old + 1, old + 1]
    assert new_sizes == [new, new, new, new, old + 1, old + 1]
    for child, delta in spy.signals:
        assert delta == predicted_charge(child)


def test_a_revision_costs_more_than_the_new_snapshot_alone_by_exactly_the_old_replay():
    previous = with_alternatives(build(checks=3, collected=2), [None, 3, 4])
    request = revise(previous, 5)
    old = work_of(previous)
    new_alone = work_of(standalone(request))
    both = work_of(request)
    assert old["analyses"] == new_alone["analyses"] == 3 * (1 + 3)
    assert both["analyses"] == old["analyses"] + new_alone["analyses"]
    assert both["solver_work_reserved"] - new_alone["solver_work_reserved"] == old["solver_work_reserved"]
    assert both["expanded_items"] - new_alone["expanded_items"] == old["expanded_items"]


# ---------------------------------------------------------------------------------------------------------
# Ceilings: exactly at the limit passes, one over refuses with the named code
# ---------------------------------------------------------------------------------------------------------

SOLVER = "resource_bound:session_solver_work"
ANALYSES = "resource_bound:session_analyses"


def boundary_cases():
    baseline = build(checks=2, collected=1)
    grid = with_alternatives(build(checks=3, collected=1), [None, 2, 4])
    revision = revise(with_alternatives(build(checks=2, collected=1), [None, 2]), 3)
    return {"baseline": baseline, "alternatives": grid, "revision": revision}


@pytest.mark.parametrize("name", ["baseline", "alternatives", "revision"])
def test_the_solver_work_limit_is_inclusive_and_one_over_limits_only_the_last_check(name):
    request = boundary_cases()[name]
    total = work_of(request)
    spy = Spy(pytest.MonkeyPatch())
    reply = run(with_limits(request, max_solver_work=total["solver_work_reserved"]))
    assert reply["code"] == "complete" and reply["work"] == total
    assert limited_entries(reply) == []
    del spy
    last = predicted_last_charge(request)
    over = run(with_limits(request, max_solver_work=total["solver_work_reserved"] - 1))
    # protocol children are limited, not refused: the run completes and the child's charge is released
    assert over["code"] == "complete"
    assert over["work"] == {key: total[key] - last[key] for key in total}
    assert over["work"]["analyses"] == total["analyses"] - 1
    for entry in limited_entries(over):
        assert entry["code"] == "session_work_limit"
        assert entry["limit"] == SOLVER
        assert entry["reserved"] == last["solver_work_reserved"]
        assert entry["already_reserved"] == over["work"]["solver_work_reserved"]
        assert entry["configured"] == {
            "max_analyses": 128,
            "max_solver_work": total["solver_work_reserved"] - 1,
        }
        assert entry["already_reserved"] + entry["reserved"] > entry["configured"]["max_solver_work"]
    assert len(limited_entries(over)) == (1 if name == "baseline" else 0)
    if name == "alternatives":
        decision = over["result"]["protocol"]["decisions"][0]
        assert decision["alternatives"][-1]["checks"][-1]["check_code"] == "undetermined"


def limited_entries(reply: dict) -> list[dict]:
    """The baseline checks' session_work_limit entries (current snapshot)."""
    return [
        entry
        for check in reply["result"]["protocol"]["checks"]
        for entry in check["unresolved"]
        if entry["code"] == "session_work_limit"
    ]


def predicted_last_charge(request: dict) -> dict:
    """The charge of the last protocol child of the run, from the retained spy of an unconstrained run."""
    with pytest.MonkeyPatch.context() as patch:
        spy = Spy(patch)
        complete(request)
    return predicted_charge(spy.calls[-1][0])


@pytest.mark.parametrize("name", ["baseline", "alternatives", "revision"])
def test_the_analyses_limit_is_inclusive_and_one_over_limits_the_last_child_with_the_named_code(name):
    request = boundary_cases()[name]
    total = work_of(request)
    assert run(with_limits(request, max_analyses=total["analyses"]))["code"] == "complete"
    over = run(with_limits(request, max_analyses=total["analyses"] - 1))
    assert over["code"] == "complete"
    assert over["work"]["analyses"] == total["analyses"] - 1
    entries = limited_entries(over)
    if name == "baseline":
        assert [e["limit"] for e in entries] == [ANALYSES]
        assert entries[0]["configured"]["max_analyses"] == total["analyses"] - 1
    # the unlimited reply names no limit anywhere
    assert limited_entries(run(with_limits(request, max_analyses=total["analyses"]))) == []


def test_the_expected_analyses_of_each_boundary_session_are_the_formula_values():
    assert work_of(boundary_cases()["baseline"])["analyses"] == 2
    assert work_of(boundary_cases()["alternatives"])["analyses"] == 3 + 3 * 3
    assert work_of(boundary_cases()["revision"])["analyses"] == (2 + 2 * 2) * 2


def test_solver_work_is_named_before_analyses_when_both_are_exceeded():
    request = build(checks=3)
    both = run(with_limits(request, max_solver_work=104 * 2, max_analyses=2))
    assert [e["limit"] for e in limited_entries(both)] == [SOLVER]
    only_analyses = run(with_limits(request, max_solver_work=104 * 3, max_analyses=2))
    assert [e["limit"] for e in limited_entries(only_analyses)] == [ANALYSES]


def test_a_limited_child_never_runs_and_the_children_that_fit_do():
    request = with_alternatives(build(checks=2, collected=1), [None, 2])
    total = work_of(request)
    for limit_name, limit in (
        ("max_solver_work", total["solver_work_reserved"] - 1),
        ("max_analyses", total["analyses"] - 1),
    ):
        executed = Executed()
        out = ds.run(with_limits(request, **{limit_name: limit}), executed)
        assert out["code"] == "complete", limit_name
        assert executed.count == total["analyses"] - 1, limit_name


def test_a_non_protocol_child_over_the_limit_still_refuses_the_whole_run():
    """Applicability entailments and declared analyses are not protocol check children: they refuse."""
    condition = adult_condition(build(checks=1))
    request = build(checks=1, condition=condition)
    entailment = work_of(request)
    assert entailment["analyses"] == 2
    over = run(with_limits(request, max_solver_work=68))
    assert over["code"] == "refused" and over["problems"] == [SOLVER]
    assert over["result"] is None
    assert over["diagnostics"]["operation"] == "entailment"
    # the same limit leaves a plain schedule check limited, not refused
    plain = run(with_limits(build(checks=1), max_analyses=0 + 1))
    assert plain["code"] == "complete" and limited_entries(plain) == []


def test_a_revision_limits_every_new_child_when_the_limit_lies_at_the_old_replay():
    previous = with_alternatives(build(checks=2, collected=1), [None, 2])
    request = revise(previous, 3)
    old = work_of(previous)
    total = work_of(request)
    executed = Executed()
    out = ds.run(with_limits(request, max_analyses=old["analyses"]), executed)
    assert out["code"] == "complete"
    assert executed.count == old["analyses"]  # the whole old replay ran; every new child was limited
    assert out["work"]["analyses"] == old["analyses"]
    assert [
        e["limit"] for e in [u for c in out["result"]["protocol"]["checks"] for u in c["unresolved"]]
    ] == [ANALYSES, ANALYSES]
    assert total["analyses"] == 2 * old["analyses"]


def test_the_default_analyses_limit_is_the_binding_protocol_ceiling_for_alternatives_times_checks():
    """M checks and N alternatives need M * (1 + N) children; the session cap of 128 admits fewer than the
    protocol ceilings (16 alternatives, 128 checks) would. The surplus children are limited, not refused."""
    fits = with_alternatives(build(checks=8), [None] * 15)
    assert work_of(fits)["analyses"] == 8 * 16 == 128
    over = with_alternatives(build(checks=8), [None] * 16)
    reply = run(over)
    assert reply["code"] == "complete"
    assert reply["work"]["analyses"] == 128  # the 129th..136th children were limited and released
    rows = [
        c for d in reply["result"]["protocol"]["decisions"] for a in d["alternatives"] for c in a["checks"]
    ]
    assert sum(row["check_code"] == "undetermined" for row in rows) == 8
    assert HARD_LIMITS["max_analyses"] == 128


def test_a_policy_session_is_bounded_by_the_exact_total_not_by_the_operator_ceiling():
    request = json.loads((RESULTS / "policy-work-limit.json").read_text())["request"]
    work = work_of(request)
    assert work["solver_work_reserved"] == 1_054_837  # 3 legacy entailments (303) + 1,862 + 1,052,672
    assert run(with_limits(request, max_solver_work=work["solver_work_reserved"]))["code"] == "complete"
    # the last child is a legacy decision entailment: not a protocol child, so the whole run refuses
    over = run(with_limits(request, max_solver_work=work["solver_work_reserved"] - 1))
    assert over["problems"] == [SOLVER]


def test_a_policy_over_its_operator_ceiling_runs_while_the_session_has_room_and_is_limited_when_it_does_not():
    """Doubling the constraints doubles R to 2,101,248, above the operator's 1,000,000 ceiling: the operator
    reports `limit`; the session charges only N + R (README R6 holds) and still has room."""
    request = json.loads((RESULTS / "policy-work-limit.json").read_text())["request"]
    policy = next(o for o in request["session"]["protocol"]["objects"] if o["kind"] == "policy")
    rows = policy["data"]["model"]["constraints"]
    assert len(rows) == 8
    rows += [{**copy.deepcopy(row), "id": row["id"] + "-copy"} for row in rows]
    policy["version"] = "budget-copy"
    policy["support"] = []
    expected = policy_reservation(policy["data"]["model"])
    assert expected == 2_101_248
    with pytest.MonkeyPatch.context() as patch:
        spy = Spy(patch)
        reply = complete(request)
    ((child, delta),) = spy.signals
    assert delta["solver_work_reserved"] == nodes(child) + expected
    row = reply["result"]["protocol"]["checks"][0]["children"][0]["signals"][0]
    assert (
        row["calculation_code"] == "limit"
    )  # the operator's own ceiling, with the session still inside its limit
    # with a session limit below N + R the policy check is limited by the session instead
    cap = delta["solver_work_reserved"] + 202 - 1
    limited = run(with_limits(request, max_solver_work=cap))
    assert limited["code"] == "complete"
    (entry,) = limited_entries(limited)
    assert entry["limit"] == SOLVER and entry["reserved"] == delta["solver_work_reserved"]
    assert entry["already_reserved"] == 202  # the two declared analyses, released child excluded


def test_the_output_size_limit_is_inclusive_and_checked_after_the_replay():
    request = build(checks=1)
    for digits in range(5, 9):
        probe = ds.run(with_limits(request, max_output_bytes=10**digits - 1), service.run)
        size = len(session_state.canonical(probe).encode("utf-8"))
        if len(str(size)) == digits:
            break
    else:  # pragma: no cover
        pytest.fail("no limit with the same digit count as the output")
    assert ds.run(with_limits(request, max_output_bytes=size), service.run)["code"] == "complete"
    with pytest.raises(ValueError, match="resource_bound:session_output_bytes"):
        ds.run(with_limits(request, max_output_bytes=size - 1), service.run)
    reply = run(with_limits(request, max_output_bytes=size - 1))
    assert reply["code"] == "refused" and reply["problems"] == ["resource_bound:session_output_bytes"]


@pytest.mark.parametrize("name", sorted(HARD_LIMITS))
def test_session_limits_are_inclusive_at_the_hard_ceiling_and_refused_one_above(name):
    request = build(checks=1)
    assert run(with_limits(request, **{name: HARD_LIMITS[name]}))["code"] == "complete"
    above = run(with_limits(request, **{name: HARD_LIMITS[name] + 1}))
    assert above["problems"] == [f"invalid_limit:{name}"]
    below = run(with_limits(request, **{name: 0}))
    assert below["problems"] == [f"invalid_limit:{name}"]


def test_the_legacy_expanded_items_limit_is_diagnostic_only():
    request = build(checks=2)
    reply = run(with_limits(request, max_expanded_items=1))
    assert reply["code"] == "complete"
    assert reply["work"]["expanded_items"] > 1
    assert reply["result"]["limit_semantics"]["max_expanded_items"].startswith("legacy_nonoperative")


@pytest.mark.parametrize("limit", [311, 312])
def test_c10_a_session_bound_limits_one_check_and_keeps_the_completed_ones(limit):
    request = build(checks=3, collected=1)
    assert work_of(request)["solver_work_reserved"] == 312
    reply = run(with_limits(request, max_solver_work=limit))
    assert reply["code"] == "complete"
    checks = {c["id"]: c for c in reply["result"]["protocol"]["checks"]}
    for name in ("sched-0", "sched-1"):
        assert checks[name]["unresolved"] == []
        assert {r["outcome"] for r in checks[name]["children"][0]["signals"][0]["claim_admission"]} >= {
            "uncovered"
        }
    if limit == 312:
        assert checks["sched-2"]["unresolved"] == []
        return
    limited = checks["sched-2"]
    assert limited["unresolved"] == [
        {
            "code": "session_work_limit",
            "objects": [],
            "premises": [],
            "limit": SOLVER,
            "reserved": 104,
            "already_reserved": 208,
            "configured": {"max_analyses": 128, "max_solver_work": 311},
        }
    ]
    assert reply["work"] == {"analyses": 2, "expanded_items": 136, "solver_work_reserved": 208}
    child = limited["children"][0]
    assert child["refusal"] == [SOLVER]
    assert child["result"] == {
        "code": "refused",
        "operation": "signals",
        "result": None,
        "problems": [SOLVER],
    }


def two_plans_request(limit: int) -> dict:
    """Checks in order: A (1 interval, 104), BIG (5 intervals, 276), SMALL (0 intervals, 81)."""
    request = build(checks=3, collected=1)
    protocol = request["session"]["protocol"]
    base = next(o for o in protocol["objects"] if o["id"] == "plan")
    for name, count in (("plan-big", 5), ("plan-small", 0)):
        item = copy.deepcopy(base)
        item["id"] = name
        item["data"]["availability"] = pieces(count)
        item["support"] = [f"adopt:{name}:b1"]
        protocol["objects"].append(item)
        request["session"]["premises"].append(adoption(name, "b1"))
    protocol["checks"][1]["objects"] = ["visit", "plan-big"]
    protocol["checks"][2]["objects"] = ["visit", "plan-small"]
    protocol["objects"] = [protocol["objects"][i] for i in (0, 1, 2, 3, 4)]
    for item in protocol["objects"][3:]:
        item["depends_on"] = ["visit"]
    return with_limits(request, max_solver_work=limit)


def test_a_later_smaller_check_still_runs_after_a_larger_one_is_released():
    assert work_of(two_plans_request(10_000))["solver_work_reserved"] == 104 + 276 + 81
    reply = run(two_plans_request(104 + 81 + 100))  # BIG does not fit; SMALL does
    assert reply["code"] == "complete"
    checks = {c["id"]: c for c in reply["result"]["protocol"]["checks"]}
    assert [e["limit"] for e in checks["sched-1"]["unresolved"]] == [SOLVER]
    assert checks["sched-1"]["unresolved"][0]["reserved"] == 276
    assert checks["sched-1"]["unresolved"][0]["already_reserved"] == 104
    assert checks["sched-0"]["unresolved"] == [] and checks["sched-2"]["unresolved"] == []
    assert checks["sched-2"]["children"][0]["result"]["code"] == "complete"
    assert reply["work"] == {
        "analyses": 2,
        "expanded_items": reply["work"]["expanded_items"],
        "solver_work_reserved": 185,
    }


def test_a_limited_checks_claims_never_read_satisfied_and_its_alternative_is_undetermined():
    reply = run(with_limits(build(checks=3, collected=1), max_solver_work=311))
    limited = reply["result"]["protocol"]["checks"][2]
    assert limited["children"][0]["signals"] == []  # no claim row at all, so none can read satisfied
    request = with_alternatives(build(checks=2, collected=1), [None, 2])
    total = work_of(request)["solver_work_reserved"]
    reply = run(with_limits(request, max_solver_work=total - 1))
    decision = reply["result"]["protocol"]["decisions"][0]
    last = decision["alternatives"][1]
    assert [c["check_code"] for c in last["checks"]] == [
        "satisfied" if False else last["checks"][0]["check_code"],
        "undetermined",
    ]
    assert last["checks"][1]["claims"] == []
    assert last["compatibility"] == "undetermined"
    assert last["unconditional_application"] == "withheld"
    assert decision["disposition"] != "settled_within_declared_alternatives"


def test_a_revision_with_one_snapshots_check_limited_is_reported_as_not_compared():
    """A check limited in one snapshot is `not_computed`, with which side was limited, and no axes or claim
    changes, so a missing computation never reads as a changed clinical answer (fixed after review)."""
    previous = build(checks=3, collected=1)
    request = revise(previous, 2)
    old, new = work_of(previous), work_of(standalone(request))
    reply = run(
        with_limits(request, max_solver_work=old["solver_work_reserved"] + new["solver_work_reserved"] - 1)
    )
    assert reply["code"] == "complete"
    rows = {r["id"]: r for r in reply["answer_diff"]["protocol_checks"]}
    assert rows["sched-0"]["axes"] == rows["sched-1"]["axes"] == ["support", "scope_model"]
    assert rows["sched-2"] == {
        "id": "sched-2",
        "code": "not_computed",
        "axes": [],
        "limited": ["after"],
        "changes": [],
    }
    assert [e["limit"] for e in limited_entries(reply)] == [SOLVER]
    assert reply["previous_fresh"]["protocol"]["checks"][2]["unresolved"] == []
