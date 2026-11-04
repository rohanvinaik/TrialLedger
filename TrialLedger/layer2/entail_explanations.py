"""Scoped nonconstraining mentions and bounded proved conditions beside entailment.

Nothing here adds a premise or changes a decision. Candidate conditions come from
a bounded typed plan; every displayed condition retains its own solver warrant.
"""

from __future__ import annotations

import dataclasses
import json

from TrialLedger.layer2 import entail
from TrialLedger.layer2 import residual_requirements as residual
from TrialLedger.layer2.assertions import (
    PROPOSITIONS,
    Always,
    AnyOf,
    Not,
    Proposition,
    ScopedAssertion,
    canonical,
)

MAX_CONDITIONS = residual.MAX_CANDIDATES
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
    """Only a supported, feasible accepted profile receives residual requirements (pure — pinned).

    post: __return__ in ('not_open', 'unresolved', 'limited', 'impossible', 'eligible')
    post: __return__ != 'eligible' or (result in ('UNDETERMINED', 'ENTAILED') and intrinsic is True)
    """
    if result not in (entail.UNDETERMINED, entail.ENTAILED):
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
    return residual.opposite(value)


def condition_plan(
    assertions: tuple[ScopedAssertion, ...], query: object, context: entail.Context
) -> residual.Plan:
    """The same finite discovery plan governs output and work reservation."""
    return residual.candidate_plan(assertions, query, context)


def planned_conditions(
    assertions: tuple[ScopedAssertion, ...], query: object, context: entail.Context
) -> tuple:
    """Compatibility view of the bounded source/subformula candidates."""
    return tuple(seed.body for seed in condition_plan(assertions, query, context).seeds)


def _profile_truth(condition: Proposition, asked: tuple, bound: int, out: dict) -> str:
    compiled = residual.formula(condition)
    toward = entail._satisfiable([asked, compiled], bound)
    against = entail._satisfiable([asked, residual.formula(_opposite(condition))], bound)
    out["checks"]["profile_queries"] += 2
    code = residual.profile_truth_code(toward, against)
    if code in ("limited", "unresolved"):
        out["blockers"].append(
            "resource_bound:explanation_profile" if code == "limited" else "profile_inconsistent"
        )
    return code


def _remaining(plan: residual.Plan, truths: dict[str, str]) -> list[tuple[Proposition, bool]]:
    rows = {}
    for seed in plan.seeds:
        condition = residual.specialize(seed.body, truths)
        if isinstance(condition, bool) or residual.formula(condition)[0] == "const":
            continue
        key = residual.key(condition)
        rows.setdefault(key, (condition, seed.asserted and key == residual.key(seed.body)))
    return list(rows.values())


def _proved_requirement(
    assertions: tuple[ScopedAssertion, ...],
    query: Proposition,
    condition: Proposition,
    asserted: bool,
    context: entail.Context,
    bound: int,
    out: dict,
) -> None:
    global_decision = entail.decide(assertions, condition, context, bound)
    out["checks"]["decisions"] += 1
    if global_decision.result == entail.ENTAILED and not any(
        code not in BENIGN_BLOCKERS for code in global_decision.blockers
    ):
        relation, warrant = "required_by_criteria", global_decision
    elif asserted:
        out["blockers"].extend(code for code in global_decision.blockers if code not in BENIGN_BLOCKERS)
        return
    else:
        implication = entail.decide(assertions, AnyOf((Not(query), condition)), context, bound)
        out["checks"]["decisions"] += 1
        blockers = sorted(set((*global_decision.blockers, *implication.blockers)))
        code = condition_code(global_decision.result, implication.result, blockers)
        if code == "unresolved":
            out["blockers"].extend(blockers)
        if code != "necessary":
            return
        relation, warrant = "necessary_if_query", implication
    out["conditions"].append(
        {
            "relation": relation,
            "body": _plain(condition),
            "status": warrant.status,
            "warrant": dataclasses.asdict(warrant),
            "scope": dataclasses.asdict(context),
            "profile_check": {"code": "not_established_by_query", "basis": "query_alone"},
        }
    )


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
    """Return bounded proved residuals without changing the supplied decision."""
    if type(bound) is not int or not 1 <= bound <= entail.MAX_ASSIGNMENTS:
        raise ValueError("invalid_resource_bound:explanations")
    out = {
        "coverage": "bounded_candidate_discovery_not_complete_screening",
        "permissions": _permissions(assertions, query, context),
        "conditions": [],
        "blockers": [],
        "checks": {
            "code": "not_open",
            "decisions": 0,
            "intrinsic_queries": 0,
            "profile_queries": 0,
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
    plan = condition_plan(assertions, query, context)
    out["blockers"].extend(plan.blockers)
    truths = {residual.key(probe): _profile_truth(probe, formula, bound, out) for probe in plan.probes}
    remaining = _remaining(plan, truths)
    out["checks"].update(
        code="complete",
        planned=len(plan.seeds),
        profile_probes=len(plan.probes),
        planning_nodes=plan.visited_nodes,
    )
    for condition, asserted in remaining:
        key = residual.key(condition)
        code = truths.get(key)
        if code is None:
            code = _profile_truth(condition, formula, bound, out)
        if code != "open":
            continue
        _proved_requirement(assertions, query, condition, asserted, context, bound, out)
    out["blockers"] = sorted(set(out["blockers"]))
    if out["blockers"]:
        out["checks"]["code"] = "limited"
    return out
