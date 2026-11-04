"""Bounded typed candidate discovery, independent of the proofs that admit output.

No clinical vocabulary is recognized here. Accepted scoped assertions supply
whole logical clauses. Only facts proved from the query alone may specialize a
clause; criteria-derived facts never enter that specialization map.
"""

from __future__ import annotations

import dataclasses
import json

from TrialLedger.layer2 import entail
from TrialLedger.layer2.assertions import (
    PROPOSITIONS,
    AllOf,
    Always,
    AnyOf,
    Literal,
    Not,
    Proposition,
    ScopedAssertion,
)

MAX_CANDIDATES = 32
MAX_PROFILE_PROBES = 64
MAX_PLAN_NODES = 256


@dataclasses.dataclass(frozen=True)
class Seed:
    body: Proposition
    envelope: Proposition
    asserted: bool


@dataclasses.dataclass(frozen=True)
class Plan:
    seeds: tuple[Seed, ...]
    probes: tuple[Proposition, ...]
    blockers: tuple[str, ...]
    visited_nodes: int


def profile_truth_code(towards: bool | None, against: bool | None) -> str:
    """Classify two query-only SAT checks without promoting missing facts (pure).

    post: __return__ in ('established', 'refuted', 'open', 'limited', 'unresolved')
    post: __return__ != 'established' or (towards is True and against is False)
    post: __return__ != 'refuted' or (towards is False and against is True)
    """
    if towards is None or against is None:
        return "limited"
    if type(towards) is not bool or type(against) is not bool:
        return "unresolved"
    if towards is True and against is False:
        return "established"
    if towards is False and against is True:
        return "refuted"
    return "open" if towards and against else "unresolved"


def junction_code(operator: str, states: list[str]) -> str:
    """Keep conjunction and disjunction different while folding proved constants (pure).

    post: __return__ in ('true', 'false', 'single', 'compound', 'unresolved')
    """
    if operator not in ("and", "or") or any(value not in ("true", "false", "open") for value in states):
        return "unresolved"
    absorbing = "false" if operator == "and" else "true"
    if absorbing in states:
        return absorbing
    remaining = states.count("open")
    if remaining == 0:
        return "true" if operator == "and" else "false"
    return "single" if remaining == 1 else "compound"


def opposite(value: Proposition) -> Proposition:
    if isinstance(value, Not):
        return value.part
    if isinstance(value, Literal):
        return dataclasses.replace(value, polarity="negative" if value.polarity == "positive" else "positive")
    return Not(value)


def formula(value: Proposition) -> tuple:
    compiled, blockers = entail.proposition_formula(value)
    if blockers:
        raise ValueError("unresolved_requirement_candidate")
    return compiled


def key(value: Proposition) -> str:
    return json.dumps(formula(value), sort_keys=True)


def variables(value: Proposition) -> set[str]:
    return {name for _, name, _ in entail._atoms(formula(value))}


def _effect(item: ScopedAssertion) -> Proposition:
    body = item.body if item.modality == "required" else opposite(item.body)
    return body if isinstance(item.applicability, Always) else AnyOf((opposite(item.applicability), body))


def _roots(assertions: tuple[ScopedAssertion, ...], context: entail.Context) -> list[tuple[str, Proposition]]:
    roots = []
    for item in sorted(assertions, key=lambda item: item.id):
        code, _, blockers = entail.assertion_formula(item, context)
        if code == "constraint" and not blockers:
            body = _effect(item)
            if formula(body)[0] != "const":
                roots.append((item.id, body))
    return roots


def _nodes(value: Proposition) -> list[Proposition]:
    """One bounded preorder; a qualified literal stays one indivisible proposition."""
    out, pending = [], [value]
    while pending and len(out) <= MAX_PLAN_NODES:
        node = pending.pop()
        out.append(node)
        if isinstance(node, AllOf | AnyOf):
            pending.extend(reversed(node.parts))
        elif isinstance(node, Not):
            pending.append(node.part)
    return out


def candidate_plan(assertions: tuple[ScopedAssertion, ...], query: object, context: entail.Context) -> Plan:
    """Select source roots and connected subformulas; execute no solver here.

    Full source clauses are never shortened by a traversal bound. Their proper
    subformulas and query-only truth probes have independent finite caps.
    """
    if not isinstance(query, PROPOSITIONS):
        return Plan((), (), (), 0)
    asked, blockers = entail.proposition_formula(query)
    if blockers:
        return Plan((), (), (), 0)
    roots = _roots(assertions, context)
    groups = entail._components(
        [(entail.QUERY, {name for _, name, _ in entail._atoms(asked)})]
        + [(str(index), variables(body)) for index, (_, body) in enumerate(roots)]
    )
    connected = set(next(group for group in groups if entail.QUERY in group))
    ordered = sorted(enumerate(roots), key=lambda row: (str(row[0]) not in connected, row[1][0]))
    seeds, probes, descendants = {}, {}, []
    limits = set()
    visited = 0
    asked_variables = {name for _, name, _ in entail._atoms(asked)}
    for index, (_, body) in ordered:
        seeds.setdefault(key(body), Seed(body, body, True))
        if str(index) not in connected:
            continue
        nodes = _nodes(body)
        for node in nodes:
            visited += 1
            if visited > MAX_PLAN_NODES:
                limits.add("resource_bound:explanation_plan_nodes")
                break
            if formula(node)[0] == "const":
                continue
            if variables(node) & asked_variables:
                probes.setdefault(key(node), node)
            if key(node) != key(body):
                descendants.append(Seed(node, body, False))
    for seed in descendants:
        seeds.setdefault(key(seed.body), seed)
    if len(seeds) > MAX_CANDIDATES:
        limits.add("resource_bound:explanation_conditions")
    if len(probes) > MAX_PROFILE_PROBES:
        limits.add("resource_bound:explanation_profile_probes")
    return Plan(
        tuple(seeds.values())[:MAX_CANDIDATES],
        tuple(probes.values())[:MAX_PROFILE_PROBES],
        tuple(sorted(limits)),
        min(visited, MAX_PLAN_NODES),
    )


def _constant(value: Proposition | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    compiled = formula(value)
    return "true" if compiled == entail.TRUE else "false" if compiled == entail.FALSE else "open"


def specialize(value: Proposition, truths: dict[str, str]) -> Proposition | bool:
    """Fold only query-established values; no premise or clinical fact is added."""
    state = truths.get(key(value))
    if state in ("established", "refuted"):
        return state == "established"
    if isinstance(value, Not):
        part = specialize(value.part, truths)
        return not part if isinstance(part, bool) else opposite(part)
    if not isinstance(value, AllOf | AnyOf):
        return value
    parts = tuple(specialize(part, truths) for part in value.parts)
    states = [_constant(part) for part in parts]
    code = junction_code("and" if isinstance(value, AllOf) else "or", states)
    if code in ("true", "false"):
        return code == "true"
    kept = tuple(
        part
        for part, state in zip(parts, states, strict=True)
        if state == "open" and not isinstance(part, bool)
    )
    if code == "single":
        return kept[0]
    return type(value)(kept)
