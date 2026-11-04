"""Scoped nonconstraining mentions and bounded proved conditions beside entailment.

Nothing here adds a premise or changes a decision. Candidate conditions come from
typed applicability expressions already joined to the query by an admitted rule.
"""

from __future__ import annotations

import dataclasses
import json

from TrialLedger.layer2 import entail
from TrialLedger.layer2.assertions import (
    PROPOSITIONS,
    Always,
    AnyOf,
    Literal,
    Not,
    Proposition,
    ScopedAssertion,
    canonical,
)

MAX_CONDITIONS = 8
BENIGN_BLOCKERS = frozenset(("undecided_by_constraints", "no_constraint_mentions_query"))
PERMISSION_CODES = frozenset(
    (
        "unrelated",
        "withheld_permission",
        "out_of_scope",
        "related_permission",
        "conditional_permission",
        "explicit_permission",
    )
)


def permission_code(admission: str, scope: str, relation: str, conditional: bool) -> str:
    """Name a permission's actual coverage without turning a mention into permission (pure — pinned).

    post: __return__ in PERMISSION_CODES
    post: __return__ != 'explicit_permission' or admission == 'accepted'
    post: __return__ != 'explicit_permission' or scope == 'applicable'
    post: __return__ != 'explicit_permission' or relation == 'exact'
    post: __return__ != 'explicit_permission' or not conditional
    """
    if relation == "none":
        return "unrelated"
    if relation not in ("exact", "related") or type(conditional) is not bool:
        return "withheld_permission"
    if admission != "accepted":
        return "withheld_permission"
    if scope == "outside":
        return "out_of_scope"
    if scope != "applicable":
        return "withheld_permission"
    if relation != "exact":
        return "related_permission"
    return "conditional_permission" if conditional else "explicit_permission"


def explanation_gate(result: str, blockers: list[str], intrinsic: bool | None) -> str:
    """Only an open, supported, feasible query receives conditional consequences (pure — pinned).

    post: __return__ in ('not_open', 'unresolved', 'limited', 'impossible', 'eligible')
    post: __return__ != 'eligible' or (result == 'UNDETERMINED' and intrinsic is True)
    """
    if result != entail.UNDETERMINED:
        return "not_open"
    if any(code not in BENIGN_BLOCKERS for code in blockers):
        return "unresolved"
    if intrinsic is None:
        return "limited"
    if intrinsic is True:
        return "eligible"
    return "impossible" if intrinsic is False else "limited"


def condition_code(global_result: str, implication_result: str, blockers: list[str]) -> str:
    """Distinguish a necessary conditional fact from a global or unproved fact (pure — pinned).

    post: __return__ in ('unresolved', 'already_required', 'necessary', 'not_proved')
    post: __return__ != 'necessary' or (global_result == 'UNDETERMINED' and implication_result == 'ENTAILED')
    """
    if any(code not in BENIGN_BLOCKERS for code in blockers):
        return "unresolved"
    if global_result == entail.ENTAILED:
        return "already_required"
    if global_result == entail.UNDETERMINED and implication_result == entail.ENTAILED:
        return "necessary"
    return "not_proved"


def _plain(value: object) -> dict:
    return json.loads(canonical(value))


def _variables(formula: tuple) -> set[str]:
    return {key for _, key, _ in entail._atoms(formula)}


def _opposite(value: Proposition) -> Proposition:
    if isinstance(value, Not):
        return value.part
    if isinstance(value, Literal):
        return dataclasses.replace(value, polarity="negative" if value.polarity == "positive" else "positive")
    return Not(value)


def _candidates(assertions: tuple[ScopedAssertion, ...], query: object, context: entail.Context) -> tuple:
    if not isinstance(query, PROPOSITIONS):
        return ()
    asked, found = entail.proposition_formula(query)
    if found:
        return ()
    asked_variables = _variables(asked)
    candidates = {}
    for item in sorted(assertions, key=lambda item: item.id):
        code, _, blockers = entail.assertion_formula(item, context)
        body, body_blockers = entail.proposition_formula(item.body)
        if code != "constraint" or blockers or body_blockers or not (_variables(body) & asked_variables):
            continue
        if isinstance(item.applicability, Always):
            continue
        for condition in (item.applicability, _opposite(item.applicability)):
            formula, raised = entail.proposition_formula(condition)
            if raised or formula[0] == "const":
                continue
            candidates.setdefault(json.dumps(formula, sort_keys=True), condition)
    return tuple(candidates.values())


def planned_conditions(
    assertions: tuple[ScopedAssertion, ...], query: object, context: entail.Context
) -> tuple:
    """The exact bounded proof plan used by explain and session work reservation.

    Every candidate atom and threshold is already in an admitted rule whose body
    intersects the query. Adding an implication joins no new component or cells.
    """
    return _candidates(assertions, query, context)[:MAX_CONDITIONS]


def _permissions(assertions: tuple[ScopedAssertion, ...], query: object, context: entail.Context) -> list:
    if not isinstance(query, PROPOSITIONS):
        return []
    asked, found = entail.proposition_formula(query)
    if found:
        return []
    rows = []
    for item in sorted(assertions, key=lambda item: item.id):
        if item.modality != "permitted":
            continue
        body, body_blockers = entail.proposition_formula(item.body)
        relation = "exact" if body == asked else "related" if _variables(body) & _variables(asked) else "none"
        admission, _, raised = entail.assertion_formula(item, context)
        scope, scope_blockers = entail._scope_formula(item.cohort, context)
        _, application_blockers = entail.proposition_formula(item.applicability)
        accepted = (
            admission == "no_constraint" and not body_blockers and not raised and not application_blockers
        )
        scope_code = "applicable" if scope == entail.TRUE else "outside" if scope == entail.FALSE else "open"
        code = permission_code(
            "accepted" if accepted else "withheld",
            scope_code,
            relation,
            not isinstance(item.applicability, Always),
        )
        if code == "unrelated":
            continue
        rows.append(
            {
                "id": item.id,
                "code": code,
                "body": _plain(item.body),
                "applicability": _plain(item.applicability),
                "scope": _plain(item.cohort),
                "status": item.status,
                "criterion_ref": item.criterion_ref,
                "rule": _plain(item.rule),
                "blockers": sorted(set((*raised, *body_blockers, *scope_blockers, *application_blockers))),
            }
        )
    return rows


def explain(
    assertions: tuple[ScopedAssertion, ...],
    query: object,
    context: entail.Context,
    decision: entail.Decision,
    bound: int,
) -> dict:
    """Return additive explanations; at most sixteen decide calls and one intrinsic SAT call."""
    if type(bound) is not int or not 1 <= bound <= entail.MAX_ASSIGNMENTS:
        raise ValueError("invalid_resource_bound:explanations")
    out = {
        "permissions": _permissions(assertions, query, context),
        "conditions": [],
        "blockers": [],
        "checks": {
            "code": "not_open",
            "decisions": 0,
            "intrinsic_queries": 0,
            "planned": 0,
            "limit": MAX_CONDITIONS,
        },
    }
    initial = explanation_gate(decision.result, list(decision.blockers), True)
    if initial != "eligible" or not isinstance(query, PROPOSITIONS):
        out["checks"]["code"] = initial
        out["blockers"] = list(decision.blockers)
        return out
    formula, _ = entail.proposition_formula(query)
    intrinsic = entail._satisfiable([formula], bound)
    out["checks"]["intrinsic_queries"] = 1
    gate = explanation_gate(decision.result, list(decision.blockers), intrinsic)
    out["checks"]["code"] = gate
    if gate != "eligible":
        out["blockers"] = (
            ["resource_bound:explanation_profile"] if intrinsic is None else ["profile_inconsistent"]
        )
        return out
    candidates = _candidates(assertions, query, context)
    plan = planned_conditions(assertions, query, context)
    out["checks"].update(
        code="complete" if len(candidates) <= MAX_CONDITIONS else "limited", planned=len(plan)
    )
    if len(candidates) > MAX_CONDITIONS:
        out["blockers"].append("resource_bound:explanation_conditions")
    for condition in plan:
        unconditional = entail.decide(assertions, condition, context, bound)
        implication = entail.decide(assertions, AnyOf((Not(query), condition)), context, bound)
        out["checks"]["decisions"] += 2
        blockers = sorted(set((*unconditional.blockers, *implication.blockers)))
        code = condition_code(unconditional.result, implication.result, blockers)
        if code == "unresolved":
            out["blockers"].extend(blockers)
        if code != "necessary":
            continue
        out["conditions"].append(
            {
                "relation": "necessary_if_query",
                "body": _plain(condition),
                "status": implication.status,
                "warrant": dataclasses.asdict(implication),
                "scope": dataclasses.asdict(context),
            }
        )
    out["blockers"] = sorted(set(out["blockers"]))
    return out
