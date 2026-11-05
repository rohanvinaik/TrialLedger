"""Bounded finite-policy operator: exhaustive checks over a declared finite state/valuation model.

The operator reports coverage, exclusivity, prohibitions, invariants and, only when requested, graph
termination. It never interprets action descriptions, never deletes valuations to satisfy a prohibition,
assumes no fairness and supplies no implicit clock or state update. Reachable states are computed as a
fixpoint over states; node-to-node edges are never materialized. Coverage speaks only about the declared
variables.
"""

from __future__ import annotations

import copy
import itertools
import json
import math
from dataclasses import dataclass
from typing import Any

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import decision_tables as tables
from TrialLedger.layer2 import entail
from TrialLedger.layer2.signals import support_state

KIND = "finite_policy"
RULE = "policy.finite_reachable_states:1"
GUARANTEE = "exhaustive_over_declared_finite_model"
MAX_POLICY_WORK = 1_000_000
MAX_VALUATIONS = 4096
MAX_STATES = 32
MAX_ACTIONS = 64
MAX_TRANSITIONS = 128
MAX_RULES = 32
MAX_TEXT = 1024
MAX_WITNESSES = 64
CLAIMS = ("coverage", "exclusivity", "prohibition", "invariant", "termination")
DEFAULT_CLAIMS = CLAIMS[:4]
STATUSES = ("known", "interpolated", "proposed")
RESOLUTIONS = ("resolved", "partially_resolved", "unresolved", "conflicting")
LEVELS = ("participant", "cohort", "study")
FIELDS = (
    "scope",
    "version",
    "variables",
    "constraints",
    "states",
    "initial",
    "terminal",
    "actions",
    "transitions",
    "prohibitions",
    "invariants",
)
RESERVED = "policy_state"

INPUTS = {
    KIND: {
        "required": FIELDS,
        "optional": (),
        "fields": {
            "scope": "nonempty identity of the policy application and stage",
            "version": "nonempty policy version",
            "variables": "decision-table domains [{id, values:[equality Literal]}]; at most 8 variables of "
            "at most 32 values each, and at most 4096 valuations in their product",
            "constraints": "[{id, condition, rule}]: tagged propositions restricting feasible valuations",
            "states": "1 to 32 unique nonempty state names; declared order is the tie order",
            "initial": "nonempty unique subset of states",
            "terminal": "unique subset of states; a terminal state has no outgoing transition",
            "actions": "[{id, scope:{level: participant|cohort|study, ref}, description}]; wording unread",
            "transitions": "[{id, from, to, guard, actions}]; guard is a tagged proposition",
            "prohibitions": "[{id, state|null, condition, actions, rule}]: forbidden action selections",
            "invariants": "[{id, state|null, condition, actions: [], rule}]: required at every reached node. "
            "External variables are re-chosen at every step from the state's feasible valuations, so an "
            "invariant over them holds only if the constraints imply it; represent memory in states",
        },
        "reserved": "policy_state is an equality literal on the current state; callers never declare it",
        "claims": "nonempty [{id, claim, witness_limit 0..64}], claim in coverage|exclusivity|prohibition|"
        "invariant|termination, each at most once; evaluate() omits termination",
        "limits": "reservation S*V*(K+P+I)+V*T proposition evaluations; above 1,000,000 returns code limit",
    }
}


def claim_outcome(claim: str, violations: int, declared: int) -> str:
    """Classify one completed claim; no declared obligation is never safe.

    pre: claim in ('coverage', 'exclusivity', 'prohibition', 'invariant', 'termination')
    pre: violations >= 0
    pre: declared >= 0
    post: claim != 'coverage' or __return__ in ('covered', 'gap')
    post: claim != 'exclusivity' or __return__ in ('exclusive', 'competing')
    post: claim != 'prohibition' or __return__ in ('not_declared', 'clear', 'violation')
    post: claim != 'invariant' or __return__ in ('not_declared', 'holds', 'violation')
    post: claim != 'termination' or __return__ in ('all_paths_terminate', 'not_established')
    post: violations == 0 or __return__ in ('gap', 'competing', 'violation', 'not_established')
    post: declared > 0 or claim not in ('prohibition', 'invariant') or __return__ == 'not_declared'
    """
    if claim == "coverage":
        return "gap" if violations else "covered"
    if claim == "exclusivity":
        return "competing" if violations else "exclusive"
    if claim == "termination":
        return "not_established" if violations else "all_paths_terminate"
    if declared == 0:
        return "not_declared"
    if violations:
        return "violation"
    return "clear" if claim == "prohibition" else "holds"


def policy_code(inconsistent: bool, limited: bool, failed: bool) -> str:
    """Classify the whole result; an empty or unfinished model is never satisfied.

    pre: True
    post: __return__ in ('inconsistent_domain', 'limit', 'violated', 'satisfied')
    post: not inconsistent or __return__ == 'inconsistent_domain'
    post: inconsistent or not limited or __return__ == 'limit'
    post: __return__ != 'satisfied' or not (inconsistent or limited or failed)
    """
    if inconsistent:
        return "inconsistent_domain"
    if limited:
        return "limit"
    return "violated" if failed else "satisfied"


def rule_standing(statuses: list[str], resolutions: list[str]) -> str:
    """Name the standing of the rules behind a claim, from the existing support gate.

    pre: len(statuses) == len(resolutions)
    post: __return__ in ('known', 'interpolated', 'proposed_refused', 'binding_unresolved', 'no_rule_support')
    post: statuses or __return__ == 'no_rule_support'
    post: 'proposed' not in statuses or __return__ == 'proposed_refused' or not statuses
    """
    if not statuses:
        return "no_rule_support"
    gate = support_state(statuses, resolutions)
    if gate != "accepted":
        return gate
    return "interpolated" if "interpolated" in statuses else "known"


def envelope_status(statuses: list[str]) -> str | None:
    """Name the weakest declared status; nothing is relabelled proposed.

    pre: all(s in ('known', 'interpolated', 'proposed') for s in statuses)
    post: __return__ in (None, 'known', 'interpolated', 'proposed')
    post: bool(statuses) == (__return__ is not None)
    post: (__return__ == 'proposed') == ('proposed' in statuses)
    """
    if not statuses:
        return None
    if "proposed" in statuses:
        return "proposed"
    return "interpolated" if "interpolated" in statuses else "known"


def envelope_resolution(resolutions: list[str]) -> str | None:
    """Name the worst declared resolution: conflicting > unresolved > partially_resolved > resolved.

    pre: all(r in ('resolved', 'partially_resolved', 'unresolved', 'conflicting') for r in resolutions)
    post: __return__ in (None, 'resolved', 'partially_resolved', 'unresolved', 'conflicting')
    post: bool(resolutions) == (__return__ is not None)
    post: __return__ is None or __return__ in resolutions
    """
    for worst in ("conflicting", "unresolved", "partially_resolved", "resolved"):
        if worst in resolutions:
            return worst
    return None


@dataclass
class _Model:
    scope: str
    version: str
    variables: list
    choices: list
    constraints: list
    states: list
    initial: list
    terminal: set
    actions: list
    transitions: list
    prohibitions: list
    invariants: list
    valuation_count: int


def _text(raw: object, code: str = "policy_invalid_text") -> str:
    if not isinstance(raw, str) or not raw or len(raw) > MAX_TEXT:
        raise ValueError(code)
    return raw


def _list(raw: object, maximum: int, code: str = "policy_invalid_list") -> list:
    if not isinstance(raw, list) or len(raw) > maximum:
        raise ValueError(code)
    return raw


def _object(raw: object, fields: set[str], code: str) -> dict:
    if not isinstance(raw, dict) or set(raw) != fields:
        raise ValueError(code)
    return raw


def _reserved_key() -> str:
    literal = a.Literal(
        a.Subject("study_procedure", ""),
        a.Predicate("measurement", RESERVED),
        a.Value("enum", "eq", members=("state",)),
    )
    return next(iter(tables._keys(literal)))


RESERVED_KEY = _reserved_key()


def _literals(body: object):
    if isinstance(body, a.Literal):
        yield body
        yield from _literals(body.qualifiers)
    elif isinstance(body, a.AllOf | a.AnyOf):
        for part in body.parts:
            yield from _literals(part)
    elif isinstance(body, a.Not):
        yield from _literals(body.part)


def _formula(raw: object, declared: frozenset[str], states: list[str]) -> tuple:
    body = tables._proposition(raw)
    if tables._keys(body) - declared - {RESERVED_KEY}:
        raise ValueError("policy_undeclared_variable")
    for literal in _literals(body):
        if RESERVED_KEY in tables._keys(literal) and any(m not in states for m in literal.value.members):
            raise ValueError("policy_unknown_state")
    return entail.proposition_formula(body)[0]


def _rule(raw: object) -> tuple[str, str]:
    code = "policy_invalid_rule"
    row = _object(raw, {"ref", "version", "status", "resolution", "basis"}, code)
    _text(row["ref"], code)
    _text(row["version"], code)
    if row["status"] not in STATUSES or row["resolution"] not in RESOLUTIONS:
        raise ValueError(code)
    basis = row["basis"]
    if not isinstance(basis, list) or not 1 <= len(basis) <= 32:
        raise ValueError(code)
    if any(not isinstance(item, str) or not item for item in basis) or len(set(basis)) != len(basis):
        raise ValueError(code)
    return row["status"], row["resolution"]


def _state_subset(raw: object, states: list[str], code: str, nonempty: bool) -> list[str]:
    if not isinstance(raw, list) or len(raw) > len(states) or (nonempty and not raw):
        raise ValueError(code)
    if any(not isinstance(item, str) or item not in states for item in raw) or len(set(raw)) != len(raw):
        raise ValueError(code)
    return raw


def _unique_ids(rows: list[dict]) -> None:
    identities = [row["id"] for row in rows]
    if len(set(identities)) != len(identities):
        raise ValueError("policy_duplicate_id")


def _action_ids(raw: object, declared: list[str], nonempty: bool = True) -> list[str]:
    if not isinstance(raw, list) or len(raw) > MAX_ACTIONS or (nonempty and not raw):
        raise ValueError("policy_invalid_list")
    for item in raw:
        _text(item)
    if len(set(raw)) != len(raw):
        raise ValueError("policy_invalid_list")
    if any(item not in declared for item in raw):
        raise ValueError("policy_unknown_action")
    return raw


def _parse_actions(raw: object) -> list[dict]:
    rows = []
    for item in _list(raw, MAX_ACTIONS, "policy_invalid_action"):
        row = _object(item, {"id", "scope", "description"}, "policy_invalid_action")
        _text(row["id"], "policy_invalid_action")
        _text(row["description"], "policy_invalid_action")
        scope = _object(row["scope"], {"level", "ref"}, "policy_invalid_action")
        if scope["level"] not in LEVELS:
            raise ValueError("policy_invalid_action")
        _text(scope["ref"], "policy_invalid_action")
        rows.append(row)
    if not rows:
        raise ValueError("policy_invalid_action")
    _unique_ids(rows)
    return rows


def _parse_rows(raw: object, maximum: int, fields: set[str]) -> list[dict]:
    rows = []
    for item in _list(raw, maximum):
        row = _object(item, fields, "policy_invalid_list")
        _text(row["id"])
        rows.append(row)
    _unique_ids(rows)
    return rows


def _state_or_null(raw: object, states: list[str]) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw:
        raise ValueError("policy_invalid_text")
    if raw not in states:
        raise ValueError("policy_unknown_state")
    return raw


def _parse(data: object) -> _Model:
    data = _object(data, set(FIELDS), "policy_data_fields")
    scope, version = _text(data["scope"]), _text(data["version"])
    _list(data["variables"], MAX_VALUATIONS)
    _, declared = tables._domains(data["variables"])
    if RESERVED_KEY in declared or any(
        literal.predicate.key == RESERVED
        for domain in data["variables"]
        for raw in domain["values"]
        for literal in _literals(tables._proposition(raw))
    ):
        raise ValueError("policy_reserved_variable")
    choices = tables._domain_options(data["variables"])
    count = math.prod(len(options) for options in choices)
    if count > MAX_VALUATIONS:
        raise ValueError("policy_valuation_limit")
    states = _list(data["states"], MAX_STATES, "policy_invalid_states")
    if not states or any(not isinstance(s, str) or not s or len(s) > MAX_TEXT for s in states):
        raise ValueError("policy_invalid_states")
    if len(set(states)) != len(states):
        raise ValueError("policy_invalid_states")
    initial = _state_subset(data["initial"], states, "policy_invalid_initial", True)
    terminal = _state_subset(data["terminal"], states, "policy_invalid_terminal", False)
    actions = _parse_actions(data["actions"])
    action_ids = [row["id"] for row in actions]
    constraints = [
        (row, _formula(row["condition"], declared, states), _rule(row["rule"]))
        for row in _parse_rows(data["constraints"], MAX_RULES, {"id", "condition", "rule"})
    ]
    transitions = []
    for row in _parse_rows(data["transitions"], MAX_TRANSITIONS, {"id", "from", "to", "guard", "actions"}):
        source, target = _text(row["from"]), _text(row["to"])
        if source not in states or target not in states:
            raise ValueError("policy_unknown_state")
        if source in terminal:
            raise ValueError("policy_terminal_outgoing")
        ids = _action_ids(row["actions"], action_ids)
        transitions.append((row, _formula(row["guard"], declared, states), ids))
    prohibitions = []
    fields = {"id", "state", "condition", "actions", "rule"}
    for row in _parse_rows(data["prohibitions"], MAX_RULES, fields):
        state = _state_or_null(row["state"], states)
        ids = _action_ids(row["actions"], action_ids)
        prohibitions.append(
            (row, state, _formula(row["condition"], declared, states), ids, _rule(row["rule"]))
        )
    invariants = []
    for row in _parse_rows(data["invariants"], MAX_RULES, fields):
        state = _state_or_null(row["state"], states)
        if row["actions"] != []:
            raise ValueError("policy_invariant_actions")
        invariants.append((row, state, _formula(row["condition"], declared, states), _rule(row["rule"])))
    return _Model(
        scope,
        version,
        data["variables"],
        choices,
        constraints,
        states,
        initial,
        set(terminal),
        actions,
        transitions,
        prohibitions,
        invariants,
        count,
    )


def _claims(raw: object) -> list[dict]:
    if not isinstance(raw, list) or not raw or len(raw) > len(CLAIMS):
        raise ValueError("policy_invalid_claims")
    seen_claims, seen_ids = set(), set()
    for item in raw:
        row = _object(item, {"id", "claim", "witness_limit"}, "policy_invalid_claims")
        limit = row["witness_limit"]
        if not isinstance(row["id"], str) or not row["id"] or row["claim"] not in CLAIMS:
            raise ValueError("policy_invalid_claims")
        if type(limit) is not int or not 0 <= limit <= MAX_WITNESSES:
            raise ValueError("policy_invalid_claims")
        if row["claim"] in seen_claims or row["id"] in seen_ids:
            raise ValueError("policy_duplicate_claim")
        seen_claims.add(row["claim"])
        seen_ids.add(row["id"])
    return raw


def _reservation(model: _Model) -> int:
    states, valuations = len(model.states), model.valuation_count
    rules = len(model.constraints) + len(model.prohibitions) + len(model.invariants)
    return states * valuations * rules + valuations * len(model.transitions)


def work_reservation(data: dict) -> int:
    """Reserve S*V*(K+P+I) + V*T proposition evaluations; guards run only at their own from-state."""
    return _reservation(_parse(data))


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class _Run:
    """One exhaustive exploration; every proposition evaluation is counted."""

    def __init__(self, model: _Model):
        self.model = model
        self.used = 0
        self.guard_evaluations = 0
        names = model.states
        self.index = {name: i for i, name in enumerate(names)}
        self.valuations = list(itertools.product(*model.choices))
        self.env = [{key: value for _, key, value, _ in chosen} for chosen in self.valuations]
        self.rendered = [
            {identity: json.loads(a.canonical(literal)) for identity, _, _, literal in chosen}
            for chosen in self.valuations
        ]
        self.terminal = {self.index[name] for name in model.terminal}
        self.feasible: list[list[int]] = []
        self.dist: dict[int, int] = {}
        self.parent: dict[int, tuple[int, int]] = {}
        self.enabled: dict[int, list[tuple[int, tuple[int, ...]]]] = {}
        self.first_enable: dict[tuple[int, int], int] = {}
        self.edges: dict[int, list[tuple[int, int]]] = {}
        self.conflicts: list[tuple[int, int]] = []
        self.sources = [self.index[row["from"]] for row, _, _ in model.transitions]
        self.targets = [self.index[row["to"]] for row, _, _ in model.transitions]

    def holds(self, formula: tuple, state: int, valuation: int) -> bool:
        self.used += 1
        env = self.env[valuation]
        env[RESERVED_KEY] = self.model.states[state]
        return entail._holds(formula, env)

    def build_feasible(self) -> None:
        formulas = [formula for _, formula, _ in self.model.constraints]
        for state in range(len(self.model.states)):
            self.feasible.append(
                [v for v in range(len(self.valuations)) if all(self.holds(f, state, v) for f in formulas)]
            )

    def expand(self, state: int) -> None:
        rows = self.model.transitions
        own = [t for t in range(len(rows)) if self.sources[t] == state]
        self.enabled[state] = []
        for v in self.feasible[state]:
            found: tuple[int, ...] = ()
            if state not in self.terminal:
                found = tuple(t for t in own if self.guarded(rows[t][1], state, v))
            for t in found:
                self.first_enable.setdefault((state, t), v)
            self.enabled[state].append((v, found))
        self.edges[state] = []
        for t in own:
            if (state, t) not in self.first_enable:
                continue
            if self.feasible[self.targets[t]]:
                self.edges[state].append((t, self.targets[t]))
            else:
                self.conflicts.append((state, t))

    def guarded(self, formula: tuple, state: int, valuation: int) -> bool:
        self.guard_evaluations += 1
        return self.holds(formula, state, valuation)

    def explore(self) -> None:
        level = sorted(self.index[name] for name in self.model.initial if self.feasible[self.index[name]])
        self.dist = {state: 0 for state in level}
        depth = 0
        while level:
            discovered: set[int] = set()
            for state in level:
                self.expand(state)
                for t, target in self.edges[state]:
                    if target not in self.dist:
                        self.dist[target] = depth + 1
                        self.parent[target] = (state, t)
                        discovered.add(target)
            level, depth = sorted(discovered), depth + 1

    def step(self, state: int, valuation: int, transition: int | None) -> dict:
        row = None if transition is None else self.model.transitions[transition]
        return {
            "state": self.model.states[state],
            "valuation": self.rendered[valuation],
            "transition": None if row is None else row[0]["id"],
            "actions": [] if row is None else list(row[2]),
        }

    def trace(self, state: int, valuation: int, transition: int | None) -> list[dict]:
        chain, current = [], state
        while current in self.parent:
            previous, t = self.parent[current]
            chain.append((previous, t))
            current = previous
        steps = [self.step(p, self.first_enable[(p, t)], t) for p, t in reversed(chain)]
        return steps + [self.step(state, valuation, transition)]

    def nodes(self):
        for state in sorted(self.dist):
            for valuation, found in self.enabled[state]:
                yield state, valuation, found

    def cycle_states(self) -> list[int]:
        output = []
        for start in sorted(self.dist):
            pending = [target for _, target in self.edges[start]]
            seen: set[int] = set()
            while pending:
                current = pending.pop()
                if current == start:
                    output.append(start)
                    break
                if current not in seen:
                    seen.add(current)
                    pending.extend(target for _, target in self.edges[current])
        return output

    def violations(self) -> dict[str, list[tuple]]:
        model = self.model
        gaps, competing, prohibited, failed = [], [], [], []
        cache: dict[tuple, bool] = {}

        def holds(kind: str, number: int, formula: tuple, state: int, valuation: int) -> bool:
            key = (kind, number, state, valuation)
            if key not in cache:
                cache[key] = self.holds(formula, state, valuation)
            return cache[key]

        for state, valuation, found in self.nodes():
            name = model.states[state]
            order = (self.dist[state], state, valuation)
            if state not in self.terminal:
                if not found:
                    gaps.append((*order, None, {"kind": "gap", "state": name}))
                if len(found) > 1:
                    element = {
                        "kind": "competing",
                        "transitions": [model.transitions[t][0]["id"] for t in found],
                    }
                    competing.append((*order, found[0], element))
                for t in found:
                    for number, (row, scope, formula, forbidden, _) in enumerate(model.prohibitions):
                        if scope not in (None, name) or not set(model.transitions[t][2]) & set(forbidden):
                            continue
                        if holds("p", number, formula, state, valuation):
                            element = {
                                "kind": "prohibition",
                                "id": row["id"],
                                "transition": model.transitions[t][0]["id"],
                            }
                            prohibited.append((*order, t, number, element))
            for number, (row, scope, formula, _) in enumerate(model.invariants):
                if scope in (None, name) and not holds("i", number, formula, state, valuation):
                    failed.append((*order, None, number, {"kind": "invariant", "id": row["id"]}))
        return {
            "coverage": gaps,
            "exclusivity": competing,
            "prohibition": prohibited,
            "invariant": failed,
        }

    def termination(self, gaps: list[tuple]) -> tuple[list[str], dict[str, dict]]:
        reasons, witnesses = [], {}
        if gaps:
            first = gaps[0]
            reasons.append("dead_end")
            witnesses["dead_end"] = {"trace": self.trace(first[1], first[2], None), "element": first[-1]}
        cycles = self.cycle_states()
        if cycles:
            state = cycles[0]
            reasons.append("reachable_cycle")
            choice = next(t for t, target in self.edges[state] if self._reaches(target, state))
            witnesses["reachable_cycle"] = {
                "trace": self.trace(state, self.first_enable[(state, choice)], choice),
                "element": {"kind": "reachable_cycle", "state": self.model.states[state]},
            }
        if self.conflicts:
            first_conflict = self.conflict_rows()[0]
            reasons.append("transition_target_infeasible")
            witnesses["transition_target_infeasible"] = {
                "trace": first_conflict["trace"],
                "element": {
                    "kind": "transition_target_infeasible",
                    "transition": first_conflict["transition"],
                },
            }
        return sorted(reasons), witnesses

    def _reaches(self, source: int, goal: int) -> bool:
        pending, seen = [source], set()
        while pending:
            current = pending.pop()
            if current == goal:
                return True
            if current not in seen:
                seen.add(current)
                pending.extend(target for _, target in self.edges[current])
        return False

    def conflict_rows(self) -> list[dict]:
        rows = []
        for state, t in sorted(self.conflicts, key=lambda item: item[1]):
            transition = self.model.transitions[t][0]
            rows.append(
                {
                    "transition": transition["id"],
                    "from": transition["from"],
                    "to": transition["to"],
                    "trace": self.trace(state, self.first_enable[(state, t)], t),
                }
            )
        return rows


def _rules(model: _Model, claim: str) -> list[tuple[str, str, str]]:
    rules = [(row["id"], *standing) for row, _, standing in model.constraints]
    if claim == "prohibition":
        rules += [(item[0]["id"], *item[4]) for item in model.prohibitions]
    if claim == "invariant":
        rules += [(item[0]["id"], *item[3]) for item in model.invariants]
    return rules


def _all_rules(model: _Model) -> list[tuple[str, str, str]]:
    rules = [(row["id"], *standing) for row, _, standing in model.constraints]
    rules += [(item[0]["id"], *item[4]) for item in model.prohibitions]
    rules += [(item[0]["id"], *item[3]) for item in model.invariants]
    return rules


def _claim_row(
    model: _Model, claim: dict, outcome: str, found: int, witnesses: list[dict], reasons: list[str]
) -> dict:
    rules = _rules(model, claim["claim"])
    limit = claim["witness_limit"]
    return {
        "id": claim["id"],
        "claim": claim["claim"],
        "outcome": outcome,
        "violations_found": found,
        "witnesses": witnesses[:limit],
        "witness_limit": limit,
        "witnesses_omitted": found - len(witnesses[:limit]),
        "reasons": reasons,
        "standing": rule_standing([r[1] for r in rules], [r[2] for r in rules]),
        "determining_ids": _unique([r[0] for r in rules]),
    }


def _declared(model: _Model, claim: str) -> int:
    return {"prohibition": len(model.prohibitions), "invariant": len(model.invariants)}.get(claim, 1)


def _value(model: _Model, rows: list[dict], work: dict, extra: dict) -> dict:
    return {
        "scope": model.scope,
        "version": model.version,
        "declared_variables": copy.deepcopy(model.variables),
        "states": list(model.states),
        "initial": list(model.initial),
        "terminal": sorted(model.terminal, key=model.states.index),
        **extra,
        "claims": rows,
        "work": work,
        "guarantee": GUARANTEE,
        "fairness": "not_assumed",
        "operating_characteristics": "not_computed",
        "patient_outcomes": "not_modelled",
    }


def _envelope(model: _Model, code: str, value: dict, blockers: set[str]) -> dict:
    rules = _all_rules(model)
    return {
        "code": code,
        "value": value,
        "blockers": sorted(blockers),
        "rule": RULE,
        "support_status": envelope_status([r[1] for r in rules]),
        "determining_ids": _unique([r[0] for r in rules]),
        "support_resolution": envelope_resolution([r[2] for r in rules]),
    }


def _plain_claims(model: _Model, claims: list[dict], outcome: str) -> list[dict]:
    return [_claim_row(model, claim, outcome, 0, [], []) for claim in claims]


def validate(kind: str, data: dict, claims: list[dict]) -> None:
    """Admission-time input check: the named refusals check() would raise, without computing anything.

    Parses the data and the requested claims exactly as check() does, so a malformed declaration is refused
    before any work is reserved or any claim is evaluated (PAH cold audit: parameters refused only at run).
    """
    if kind != KIND:
        raise ValueError("unsupported_policy_kind")
    _parse(data)
    _claims(claims)


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Check the requested finite-policy claims exhaustively over the declared model."""
    if kind != KIND:
        raise ValueError("unsupported_policy_kind")
    model = _parse(data)
    requested = _claims(claims)
    reserved = _reservation(model)
    if reserved > MAX_POLICY_WORK:
        extra = {
            "feasibility": [],
            "reachability": {
                "initial_nodes": None,
                "reachable_states": None,
                "unreachable_states": None,
                "reachable_nodes": None,
                "guard_evaluations": None,
            },
            "transition_target_conflicts": None,
        }
        rows = _plain_claims(model, requested, "not_executed")
        value = _value(model, rows, {"reserved": reserved, "used": 0}, extra)
        return _envelope(model, policy_code(False, True, False), value, {"policy_work_limit"})
    run = _Run(model)
    run.build_feasible()
    feasibility = [
        {"state": name, "feasible_valuations": len(run.feasible[i])} for i, name in enumerate(model.states)
    ]
    initial_nodes = sum(len(run.feasible[run.index[name]]) for name in model.initial)
    if initial_nodes == 0:
        extra = {
            "feasibility": feasibility,
            "reachability": {
                "initial_nodes": 0,
                "reachable_states": [],
                "unreachable_states": list(model.states),
                "reachable_nodes": 0,
                "guard_evaluations": 0,
            },
            "transition_target_conflicts": [],
        }
        rows = _plain_claims(model, requested, "inconsistent_domain")
        value = _value(model, rows, {"reserved": reserved, "used": run.used}, extra)
        return _envelope(model, policy_code(True, False, False), value, {"policy_inconsistent_domain"})
    run.explore()
    found = run.violations()
    for items in found.values():
        items.sort(key=lambda item: item[:-1])
    rows, blockers = [], set()
    reachable = sorted(run.dist)
    for claim in requested:
        name = claim["claim"]
        if name == "termination":
            reasons, witnesses = run.termination(found["coverage"])
            items = [witnesses[reason] for reason in reasons]
            count = len(reasons)
        else:
            reasons = []
            items = [
                {"trace": run.trace(item[1], item[2], item[3]), "element": item[-1]}
                for item in found[name][: claim["witness_limit"]]
            ]
            count = len(found[name])
        outcome = claim_outcome(name, count, _declared(model, name))
        rows.append(_claim_row(model, claim, outcome, count, items, reasons))
        if outcome in ("gap", "competing", "violation", "not_established"):
            blockers.add("policy_" + outcome + ":" + claim["id"])
    conflicts = run.conflict_rows()
    blockers.update("policy_transition_target_infeasible:" + row["transition"] for row in conflicts)
    extra = {
        "feasibility": feasibility,
        "reachability": {
            "initial_nodes": initial_nodes,
            "reachable_states": [model.states[i] for i in reachable],
            "unreachable_states": [n for i, n in enumerate(model.states) if i not in run.dist],
            "reachable_nodes": sum(len(run.feasible[i]) for i in reachable),
            "guard_evaluations": run.guard_evaluations,
        },
        "transition_target_conflicts": conflicts,
    }
    failed = bool(blockers)
    value = _value(model, rows, {"reserved": reserved, "used": run.used}, extra)
    return _envelope(model, policy_code(False, False, failed), value, blockers)


def evaluate(kind: str, data: dict) -> dict:
    """Check coverage, exclusivity, prohibition and invariant; termination is never implicit."""
    claims: list[dict[str, Any]] = [
        {"id": name, "claim": name, "witness_limit": 64} for name in DEFAULT_CLAIMS
    ]
    return check(kind, data, claims)


def _example() -> dict:
    def literal(key: str, positive: bool = True) -> dict:
        return json.loads(
            a.canonical(
                a.Literal(
                    a.Subject("study_procedure"),
                    a.Predicate("measurement", key),
                    a.Value("boolean"),
                    polarity="positive" if positive else "negative",
                )
            )
        )

    def domain(key: str) -> dict:
        return {"id": key, "values": [literal(key), literal(key, False)]}

    def action(identity: str) -> dict:
        return {
            "id": identity,
            "scope": {"level": "cohort", "ref": "invented:stage-a"},
            "description": identity,
        }

    rule = {
        "ref": "invented:prohibition-rule",
        "version": "invented:1",
        "status": "known",
        "resolution": "resolved",
        "basis": ["invented:example choice"],
    }
    return {
        "scope": "invented:interim-rule:stage-a",
        "version": "invented:policy-v1",
        "variables": [domain("invented_efficacy_signal"), domain("invented_safety_signal")],
        "constraints": [],
        "states": ["interim", "decided"],
        "initial": ["interim"],
        "terminal": ["decided"],
        "actions": [action("invented_continue_arm"), action("invented_stop_arm")],
        "transitions": [
            {
                "id": "invented-continue",
                "from": "interim",
                "to": "decided",
                "guard": literal("invented_efficacy_signal"),
                "actions": ["invented_continue_arm"],
            },
            {
                "id": "invented-stop",
                "from": "interim",
                "to": "decided",
                "guard": literal("invented_efficacy_signal", False),
                "actions": ["invented_stop_arm"],
            },
        ],
        "prohibitions": [
            {
                "id": "invented-no-continue-with-safety-signal",
                "state": None,
                "condition": literal("invented_safety_signal"),
                "actions": ["invented_continue_arm"],
                "rule": rule,
            }
        ],
        "invariants": [],
    }


EXAMPLES = {KIND: _example()}
