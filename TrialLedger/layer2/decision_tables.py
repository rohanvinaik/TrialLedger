"""Finite declared decision tables, checked by the existing scoped entailment engine.

This operator checks the table's structure, never the clinical appropriateness of its actions.
Every equality domain is explicitly closed; no integers, units, time joins or rules are inferred.
"""

from __future__ import annotations

import dataclasses
import json
import math
from itertools import combinations, islice, product
from typing import cast

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail

MAX_DOMAINS = 8
MAX_VALUES = 32
MAX_ROWS = 32
MAX_CALLS = 256
MAX_WORK = 1 << 24
MAX_INPUT_NODES = 8192
MAX_INPUT_DEPTH = 32
MAX_CASES = 256
MAX_CASE_WITNESSES = 16
MAX_CASE_WORK = 16384
INPUTS = {
    "decision_table": {
        "required": ("scope", "version", "domains", "constraints", "actions", "rows", "limits"),
        "optional": ("prohibitions",),
        "fields": {
            "scope": "nonempty identity of one table application, population, event and protocol version",
            "version": "nonempty definition version",
            "domains": "distinct {id,values}: finite equality Literal alternatives for one exact variable",
            "constraints": "tagged propositions restricting feasible domain combinations; [] means none",
            "actions": "distinct nonempty action identities; labels do not establish clinical equivalence",
            "rows": "distinct {id,when,action}; when is an existing tagged proposition",
            "prohibitions": (
                "optional distinct {id,when,action}; conditions forbidding that action, "
                "using only declared variables"
            ),
            "limits": "{solver_bound,solver_calls}; bounded per-call and aggregate enumeration",
        },
        "claims": "unsupported: candidate claims cannot silently alter a declared decision table",
    }
}


def prohibition_state(result: str, blocked: bool) -> str:
    """Classify forbidden selection feasibility; an unfinished check is never safe (pure — pinned).

    pre: result in ('ENTAILED', 'REFUTED', 'UNDETERMINED', 'INCONSISTENT')
    post: __return__ in ('unresolved', 'domain_conflict', 'clear', 'violation')
    post: not blocked or __return__ == 'unresolved'
    post: __return__ != 'clear' or (not blocked and result == 'REFUTED')
    post: blocked or result not in ('ENTAILED', 'UNDETERMINED') or __return__ == 'violation'
    """
    if blocked:
        return "unresolved"
    if result == "INCONSISTENT":
        return "domain_conflict"
    return "clear" if result == "REFUTED" else "violation"


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


def _prohibitions(raw: object, actions: list[str], keys: frozenset[str]) -> list[tuple]:
    """Parse must-not declarations separately from feasible-domain constraints."""
    output, ids = [], set()
    for raw_row in _rows(raw, MAX_ROWS, "prohibitions"):
        row = _object(raw_row, {"id", "when", "action"}, "prohibition")
        identity, action = _text(row["id"], "prohibition"), _text(row["action"], "prohibition_action")
        if identity in ids:
            raise ValueError("table_duplicate_prohibition")
        ids.add(identity)
        if action not in actions:
            raise ValueError("table_unknown_prohibition_action")
        condition = _proposition(row["when"])
        if _keys(condition) - keys:
            raise ValueError("table_undeclared_prohibition_variable")
        output.append((identity, condition, action))
    return output


def _check_prohibitions(prohibitions: list[tuple], rows: list[tuple], checks: _Checks) -> list[dict]:
    output = []
    for identity, condition, action in prohibitions:
        selected = tuple(row[1] for row in rows if row[2] == action)
        if selected:
            body = a.AllOf((condition, _join(selected)))
            check = checks.check("overlap", body, [identity, *(row[0] for row in rows if row[2] == action)])
            decision = check["decision"]
            check["state"] = prohibition_state(
                decision["result"] if decision else entail.UNDETERMINED, bool(check["blockers"])
            )
        else:
            check = {
                "state": "clear",
                "blockers": [],
                "decision": None,
                "basis": [identity],
                "rule": "table.action_without_rows:1",
                "guarantee": "conditional_on_declared_table",
            }
        check.update(id=identity, action=action, when=json.loads(a.canonical(condition)))
        output.append(check)
    return output


def _domain_options(raw_domains: list[dict]) -> list[list[tuple]]:
    """Exact scalar representatives of closed equality declarations, retaining their full literal values."""
    output = []
    for domain in raw_domains:
        choices, seen = [], set()
        for raw in domain["values"]:
            # _domains has already established this exact equality-literal contract.
            literal = cast(a.Literal, _proposition(raw))
            key = next(iter(_keys(literal)))
            if literal.value.kind == "enum":
                value = literal.value.members[0]
            else:
                value = (
                    literal.polarity == "positive"
                    if literal.value.kind == "boolean"
                    else literal.value.number
                )
            if value not in seen:
                seen.add(value)
                choices.append((domain["id"], key, value, literal))
        output.append(choices)
    return output


def _case_issues(rows: list[tuple], prohibitions: list[tuple], assignment: dict) -> list[dict]:
    matched = [(identity, action) for identity, formula, action in rows if entail._holds(formula, assignment)]
    actions = sorted({action for _, action in matched})
    row_ids = [identity for identity, _ in matched]
    issues = []
    if not matched:
        issues.append(
            {"kind": "coverage_gap", "result_address": "/value/coverage", "rows": [], "actions": []}
        )
    elif len(actions) > 1:
        issues.append(
            {
                "kind": "conflicting_actions",
                "result_address": "/value/overlaps",
                "rows": row_ids,
                "actions": actions,
            }
        )
    for index, (identity, formula, action) in enumerate(prohibitions):
        if action in actions and entail._holds(formula, assignment):
            issues.append(
                {
                    "kind": "prohibition_violation",
                    "result_address": "/value/prohibitions/" + str(index),
                    "rows": [i for i, a in matched if a == action],
                    "actions": [action],
                    "prohibition": identity,
                }
            )
    return issues


def _case_witnesses(
    data: dict, rows: list[tuple], prohibitions: list[tuple], bound: int
) -> tuple[list, dict]:
    """Bound illustrations independently; a partial sample never weakens or completes the exact checks."""
    choices = _domain_options(data["domains"])
    constraints = [entail.proposition_formula(_proposition(raw))[0] for raw in data["constraints"]]
    compiled_rows = [
        (identity, entail.proposition_formula(body)[0], action) for identity, body, action in rows
    ]
    compiled_prohibitions = [
        (identity, entail.proposition_formula(body)[0], action) for identity, body, action in prohibitions
    ]
    formulas = [*constraints, *(r[1] for r in compiled_rows), *(r[1] for r in compiled_prohibitions)]
    unit_work = max(1, sum(_formula_work(formula) for formula in formulas))
    limit = min(bound, MAX_CASES, MAX_CASE_WORK // unit_work)
    total = math.prod(len(values) for values in choices)
    examined, feasible, found, output = 0, 0, 0, []
    for chosen in islice(product(*choices), limit):
        examined += 1
        assignment = {key: value for _, key, value, _ in chosen}
        if not all(entail._holds(formula, assignment) for formula in constraints):
            continue
        feasible += 1
        issues = _case_issues(compiled_rows, compiled_prohibitions, assignment)
        found += len(issues)
        for issue in issues:
            if len(output) < MAX_CASE_WITNESSES:
                issue.update(
                    scope=data["scope"],
                    version=data["version"],
                    profile=json.loads(a.canonical(_join(tuple(value for _, _, _, value in chosen), True))),
                    values=[
                        {"domain": identity, "value": json.loads(a.canonical(value))}
                        for identity, _, _, value in chosen
                    ],
                )
                output.append(issue)
    complete = examined == total and found == len(output)
    return output, {
        "state": "complete" if complete else "truncated",
        "combinations_total": total,
        "combinations_examined": examined,
        "feasible_profiles_examined": feasible,
        "witnesses_found": found,
        "witnesses_returned": len(output),
        "unexamined_combinations": total - examined,
        "omitted_witnesses": found - len(output) if examined == total else None,
        "enumeration_limit": limit,
        "output_limit": MAX_CASE_WITNESSES,
        "work": examined * unit_work,
        "guarantee": "illustrations_only_over_declared_domains",
    }


def _formula_work(formula: tuple) -> int:
    if formula[0] in ("const", "bool", "cmp", "enum"):
        return 1
    if formula[0] == "not":
        return 1 + _formula_work(formula[1])
    return 1 + sum(_formula_work(part) for part in formula[1])


def _table_inputs(data: dict) -> tuple:
    """One structural parser shared by reservation and execution; no solver runs here."""
    _bounded_input(data)
    fields = set(INPUTS["decision_table"]["required"])
    if isinstance(data, dict) and "prohibitions" in data:
        fields.add("prohibitions")
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
    prohibitions = _prohibitions(data.get("prohibitions", []), actions, keys)
    bound, call_limit = _limits(data["limits"])
    return scope, version, assertions, actions, rows, prohibitions, bound, call_limit


def work_reservation(data: dict) -> int:
    """Conservatively reserve the represented partition, proof checks and bounded illustrations.

    Every solver query and proof subset uses atoms from these declarations. Their union therefore bounds
    each enumeration, including numeric thresholds outside the listed equality-domain values. A partition
    exceeding the per-call bound enumerates nothing; its capped size remains conservative. At most 2n+4
    satisfiability checks cover one decide call, including disconnected consistency and proof minimization.
    This estimates assignment/check units, not time, and changes no execution or clinical bound.
    """
    from TrialLedger.layer2 import solver_work

    _, _, assertions, actions, rows, prohibitions, bound, calls = _table_inputs(data)
    bodies = [item.body for item in assertions] + [row[1] for row in (*rows, *prohibitions)]
    space = solver_work._partition_space([entail.proposition_formula(body)[0] for body in bodies], bound)
    requested = 2 + len(prohibitions) + len(rows) * (len(rows) - 1) // 2 + len(actions)
    executed = min(requested, calls, MAX_WORK // (bound * 3))
    return space * executed * (2 * len(assertions) + 4) + MAX_CASE_WORK


def _evaluate(data: dict) -> dict:
    scope, version, assertions, actions, rows, prohibitions, bound, call_limit = _table_inputs(data)
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
        "declared_domains": data["domains"],
        "prohibitions": [],
        "prohibition_coverage": {
            "state": "unresolved" if prohibitions else "not_declared",
            "declared": len(prohibitions),
            "guarantee": "conditional_on_declared_table",
        },
        "case_witnesses": [],
        "witness_summary": {"state": "not_computed", "reason": "domain_not_established_feasible"},
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
        output["prohibitions"] = _check_prohibitions(prohibitions, rows, checks)
        forbidden = any(row["state"] == "violation" for row in output["prohibitions"])
        for check in output["prohibitions"]:
            blockers.update(check["blockers"])
            incomplete |= check["state"] == "unresolved"
        if prohibitions and not any(row["state"] == "unresolved" for row in output["prohibitions"]):
            output["prohibition_coverage"]["state"] = "checked"
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
        code = table_state("feasible", coverage["state"] == "gap", ambiguous or forbidden, incomplete)
        if coverage["state"] == "gap":
            blockers.add("table_uncovered_case")
        if ambiguous:
            blockers.add("table_conflicting_actions")
        if forbidden:
            blockers.add("table_forbidden_action")
        output["case_witnesses"], output["witness_summary"] = _case_witnesses(data, rows, prohibitions, bound)
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
