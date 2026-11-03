"""Finite declared decision tables, checked by the existing scoped entailment engine.

This operator checks the table's structure, never the clinical appropriateness of its actions.
Every equality domain is explicitly closed; no integers, units, time joins or rules are inferred.
"""

from __future__ import annotations

import dataclasses
import json
from itertools import combinations

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail

MAX_DOMAINS = 8
MAX_VALUES = 32
MAX_ROWS = 32
MAX_CALLS = 256
MAX_WORK = 1 << 24
MAX_INPUT_NODES = 8192
MAX_INPUT_DEPTH = 32
INPUTS = {
    "decision_table": {
        "required": ("scope", "version", "domains", "constraints", "actions", "rows", "limits"),
        "fields": {
            "scope": "nonempty identity of one table application, population, event and protocol version",
            "version": "nonempty definition version",
            "domains": "distinct {id,values}: finite equality Literal alternatives for one exact variable",
            "constraints": "tagged propositions restricting feasible domain combinations; [] means none",
            "actions": "distinct nonempty action identities; labels do not establish clinical equivalence",
            "rows": "distinct {id,when,action}; when is an existing tagged proposition",
            "limits": "{solver_bound,solver_calls}; bounded per-call and aggregate enumeration",
        },
        "claims": "unsupported: candidate claims cannot silently alter a declared decision table",
    }
}


def table_check_state(kind: str, result: str, blocked: bool) -> str:
    """Classify a completed solver check without treating an unfinished answer as false (pure).

    pre: kind in ('domain', 'coverage', 'overlap', 'action')
    pre: result in ('ENTAILED', 'REFUTED', 'UNDETERMINED', 'INCONSISTENT')
    post: kind != 'domain' or __return__ in ('unresolved', 'domain_conflict', 'feasible')
    post: kind != 'coverage' or __return__ in ('unresolved', 'domain_conflict', 'covered', 'gap')
    post: kind != 'overlap' or __return__ in ('unresolved', 'domain_conflict', 'disjoint', 'overlap')
    post: kind != 'action' or __return__ in ('unresolved', 'domain_conflict', 'reachable', 'unreachable')
    post: not blocked or __return__ == 'unresolved'
    post: blocked or result != 'INCONSISTENT' or __return__ == 'domain_conflict'
    """
    if blocked:
        return "unresolved"
    if result == "INCONSISTENT":
        return "domain_conflict"
    if kind == "domain":
        return "feasible"
    if kind == "coverage":
        return "covered" if result == "ENTAILED" else "gap"
    if kind == "overlap":
        return "disjoint" if result == "REFUTED" else "overlap"
    return "unreachable" if result == "REFUTED" else "reachable"


def table_state(domain: str, gap: bool, ambiguity: bool, incomplete: bool) -> str:
    """Retain a proved table conflict beside incomplete independent checks (pure).

    pre: domain in ('feasible', 'domain_conflict', 'unresolved')
    post: __return__ in ('conflict', 'unresolved', 'consistent')
    post: domain != 'domain_conflict' or __return__ == 'conflict'
    post: domain != 'unresolved' or __return__ == 'unresolved'
    post: domain != 'feasible' or not (gap or ambiguity) or __return__ == 'conflict'
    """
    if domain == "domain_conflict":
        return "conflict"
    if domain == "unresolved":
        return "unresolved"
    if gap or ambiguity:
        return "conflict"
    return "unresolved" if incomplete else "consistent"


def _object(raw: object, fields: set[str], where: str) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("table_not_object:" + where)
    if set(raw) != fields:
        raise ValueError("table_fields:" + where)
    return raw


def _text(raw: object, where: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise ValueError("table_identity_required:" + where)
    return raw


def _rows(raw: object, maximum: int, where: str) -> list:
    if not isinstance(raw, list):
        raise ValueError("table_list_required:" + where)
    if len(raw) > maximum:
        raise ValueError("resource_bound:table_" + where)
    return raw


def _bounded_input(raw: object) -> None:
    """Bound nested parsing independently of solver and row-count limits."""
    pending = [(raw, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > MAX_INPUT_NODES or depth > MAX_INPUT_DEPTH:
            raise ValueError("resource_bound:table_input")
        if isinstance(item, dict):
            if count + len(pending) + len(item) > MAX_INPUT_NODES:
                raise ValueError("resource_bound:table_input")
            pending.extend((value, depth + 1) for value in item.values())
        elif isinstance(item, list):
            if count + len(pending) + len(item) > MAX_INPUT_NODES:
                raise ValueError("resource_bound:table_input")
            pending.extend((value, depth + 1) for value in item)


def _proposition(raw: object) -> a.Proposition:
    try:
        held = a.from_canonical(json.dumps(raw, allow_nan=False))
    except (TypeError, OverflowError) as error:
        raise ValueError("table_invalid_proposition") from error
    if not isinstance(held, a.PROPOSITIONS):
        raise ValueError("table_not_proposition")
    _, blockers = entail.proposition_formula(held)
    if blockers:
        raise ValueError("table_unresolved_proposition")
    return held


def _keys(body: a.Proposition) -> frozenset[str]:
    formula, _ = entail.proposition_formula(body)
    return frozenset(key for _, key, _ in entail._atoms(formula))


def _join(parts: tuple[a.Proposition, ...], conjunction: bool = False) -> a.Proposition:
    if len(parts) == 1:
        return parts[0]
    return a.AllOf(parts) if conjunction else a.AnyOf(parts)


def _assertion(identity: str, body: a.Proposition) -> a.ScopedAssertion:
    return a.ScopedAssertion(
        identity,
        "table:declared-input",
        "required",
        body,
        rule=a.Rule("table.declared_input", "1", warrants=(identity,)),
        status="known",
        resolution="resolved",
    )


def _domains(raw: object) -> tuple[tuple[a.ScopedAssertion, ...], frozenset[str]]:
    assertions, keys, ids = [], set(), set()
    for raw_domain in _rows(raw, MAX_DOMAINS, "domains"):
        domain = _object(raw_domain, {"id", "values"}, "domain")
        identity = _text(domain["id"], "domain")
        if identity in ids:
            raise ValueError("table_duplicate_domain")
        ids.add(identity)
        values = tuple(_proposition(value) for value in _rows(domain["values"], MAX_VALUES, "values"))
        if not values:
            raise ValueError("table_empty_domain")
        held_keys = set()
        canonical = set()
        for value in values:
            if not isinstance(value, a.Literal) or not isinstance(value.qualifiers, a.Always):
                raise ValueError("table_domain_requires_literal_equality")
            if value.value.kind not in ("boolean", "quantity", "enum") or value.value.comparison != "eq":
                raise ValueError("table_domain_requires_literal_equality")
            if value.polarity != "positive" and value.value.kind != "boolean":
                raise ValueError("table_negative_domain_equality")
            held_keys.update(_keys(value))
            text = a.canonical(value)
            if text in canonical:
                raise ValueError("table_duplicate_domain_value")
            canonical.add(text)
        if len(held_keys) != 1 or keys.intersection(held_keys):
            raise ValueError("table_domain_variable_identity")
        keys.update(held_keys)
        assertions.append(_assertion("domain:" + identity, _join(values)))
    if not assertions:
        raise ValueError("table_empty_domains")
    return tuple(assertions), frozenset(keys)


def _limits(raw: object) -> tuple[int, int]:
    limits = _object(raw, {"solver_bound", "solver_calls"}, "limits")
    bound, calls = limits["solver_bound"], limits["solver_calls"]
    if type(bound) is not int or not 1 <= bound <= entail.MAX_ASSIGNMENTS:
        raise ValueError("table_invalid_solver_bound")
    if type(calls) is not int or not 1 <= calls <= MAX_CALLS:
        raise ValueError("table_invalid_solver_calls")
    return bound, calls


class _Checks:
    """One bounded owner of all calls; every skipped check remains explicit."""

    def __init__(self, assertions: tuple[a.ScopedAssertion, ...], bound: int, calls: int):
        self.assertions = assertions
        self.bound = bound
        self.calls = calls
        self.used = 0

    def check(self, kind: str, body: a.Proposition, refs: list[str]) -> dict:
        self.used += 1
        if self.used > self.calls or self.used * self.bound * 3 > MAX_WORK:
            return {
                "state": "unresolved",
                "blockers": ["resource_bound:table_checks"],
                "decision": None,
                "basis": refs,
            }
        decision = entail.decide(self.assertions, body, bound=self.bound)
        # Both sides being feasible is decisive for existence and exposes a coverage gap.
        # The raw solver explanation stays in decision; it is not an unfinished table check.
        blockers = sorted(set(decision.blockers) - {"undecided_by_constraints"})
        blocked = bool(blockers)
        return {
            "state": table_check_state(kind, decision.result, blocked),
            "blockers": blockers,
            "decision": dataclasses.asdict(decision),
            "basis": refs,
            "guarantee": "conditional_on_declared_table",
        }


def _evaluate(data: dict) -> dict:
    _bounded_input(data)
    fields = set(INPUTS["decision_table"]["required"])
    data = _object(data, fields, "decision_table")
    scope, version = _text(data["scope"], "scope"), _text(data["version"], "version")
    assertions, keys = _domains(data["domains"])
    constraints = tuple(_proposition(raw) for raw in _rows(data["constraints"], MAX_ROWS, "constraints"))
    if any(_keys(body) - keys for body in constraints):
        raise ValueError("table_undeclared_constraint_variable")
    assertions += tuple(_assertion("constraint:" + str(i), body) for i, body in enumerate(constraints))
    actions = [_text(raw, "action") for raw in _rows(data["actions"], MAX_ROWS, "actions")]
    if not actions or len(set(actions)) != len(actions):
        raise ValueError("table_actions_empty_or_duplicated")
    rows, row_ids = [], set()
    for raw in _rows(data["rows"], MAX_ROWS, "rows"):
        row = _object(raw, {"id", "when", "action"}, "row")
        identity, action = _text(row["id"], "row"), _text(row["action"], "action")
        if identity in row_ids:
            raise ValueError("table_duplicate_row")
        row_ids.add(identity)
        if action not in actions:
            raise ValueError("table_unknown_action")
        condition = _proposition(row["when"])
        if _keys(condition) - keys:
            raise ValueError("table_undeclared_guard_variable")
        rows.append((identity, condition, action))
    if not rows:
        raise ValueError("table_empty_rows")
    bound, call_limit = _limits(data["limits"])
    checks = _Checks(assertions, bound, call_limit)
    domain = checks.check("domain", assertions[0].body, [a.id for a in assertions])
    output = {
        "scope": scope,
        "version": version,
        "domain": domain,
        "coverage": None,
        "overlaps": [],
        "actions": [],
        "witnesses": [],
        "checks_requested": 1,
        "checks_executed": min(checks.used, call_limit),
        "termination": "not_computed_static_table",
        "operating_characteristics": "not_computed",
    }
    blockers = set(domain["blockers"])
    if domain["state"] != "feasible":
        code = table_state(domain["state"], False, False, True)
    else:
        refs = [row[0] for row in rows]
        coverage = checks.check("coverage", _join(tuple(row[1] for row in rows)), refs)
        coverage["uncovered_condition"] = json.loads(a.canonical(a.Not(_join(tuple(row[1] for row in rows)))))
        output["coverage"] = coverage
        blockers.update(coverage["blockers"])
        ambiguous, incomplete = False, coverage["state"] == "unresolved"
        for left, right in combinations(rows, 2):
            check = checks.check("overlap", a.AllOf((left[1], right[1])), [left[0], right[0]])
            check.update(
                rows=[left[0], right[0]], actions=[left[2], right[2]], same_action=left[2] == right[2]
            )
            output["overlaps"].append(check)
            blockers.update(check["blockers"])
            ambiguous |= check["state"] == "overlap" and not check["same_action"]
            incomplete |= check["state"] == "unresolved"
        for action in actions:
            parts = tuple(row[1] for row in rows if row[2] == action)
            action_check: dict
            if parts:
                action_check = checks.check(
                    "action", _join(parts), [row[0] for row in rows if row[2] == action]
                )
            else:
                action_check = {"state": "unreachable", "blockers": [], "decision": None, "basis": []}
            action_check["action"] = action
            output["actions"].append(action_check)
            blockers.update(action_check["blockers"])
            incomplete |= action_check["state"] == "unresolved"
        code = table_state("feasible", coverage["state"] == "gap", ambiguous, incomplete)
        if coverage["state"] == "gap":
            blockers.add("table_uncovered_case")
        if ambiguous:
            blockers.add("table_conflicting_actions")
        output["checks_requested"] = checks.used
        output["checks_executed"] = min(checks.used, call_limit, MAX_WORK // (bound * 3))
    return {"code": code, "value": output, "blockers": sorted(blockers), "rule": "table.finite_cases:1"}


def evaluate(kind: str, data: dict) -> dict:
    """Check one explicit finite table; source truth and support belong to the signal wrapper."""
    if kind != "decision_table":
        raise ValueError("unsupported_table_kind")
    return _evaluate(data)


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Refuse unsupported candidate table mutations rather than silently ignore them."""
    if not isinstance(claims, list):
        raise ValueError("table_claims_list_required")
    if claims:
        raise ValueError("unsupported_table_candidate_claim")
    return evaluate(kind, data)


def _example() -> dict:
    def literal(number: int) -> dict:
        return json.loads(
            a.canonical(
                a.Literal(
                    a.Subject("source_case"),
                    a.Predicate("measurement", "DLT"),
                    a.Value("quantity", number=number, unit="participant"),
                )
            )
        )

    return {
        "scope": "invented:phase1:expanded-cohort-six:DLT-window",
        "version": "invented:table-v1",
        "domains": [{"id": "DLT-count", "values": [literal(i) for i in range(7)]}],
        "constraints": [],
        "actions": ["escalate", "stop"],
        "rows": [
            {
                "id": "zero-or-one",
                "when": {"class": "AnyOf", "parts": [literal(0), literal(1)]},
                "action": "escalate",
            },
            {
                "id": "two-or-more",
                "when": {"class": "AnyOf", "parts": [literal(i) for i in range(2, 7)]},
                "action": "stop",
            },
        ],
        "limits": {"solver_bound": 4096, "solver_calls": 256},
    }


EXAMPLES = {"decision_table": _example()}
