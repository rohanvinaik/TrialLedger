"""Source-supported partial evidence and its explicit consumers in candidate design reasoning.

Operators know counts, graphs or dependencies. This boundary retains support and never supplies a clinical
binding, an API result or a preferred design. Modules are fixed here, not loaded from caller code.
"""

from __future__ import annotations

import dataclasses
import importlib
from typing import Any

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail

MODULES = {
    **{kind: "numeric_evidence" for kind in ("overlap", "partition", "summary", "population")},
    **{kind: "graph_evidence" for kind in ("temporal", "regimen", "relations")},
    "dependencies": "dependency_evidence",
    "stages": "stage_evidence",
    "decision_table": "decision_tables",
    "estimand": "estimand_evidence",
    "schedule_coverage": "protocol_schedule",
    "finite_policy": "protocol_policies",
    "binomial_design": "protocol_statistics",
}
# Kinds whose explicit obligations travel as per-signal claims in the public request. Existing kinds keep
# their established claim semantics (candidate claims inside design_bounds/interpretations frames only).
CLAIM_KINDS = frozenset({"schedule_coverage", "finite_policy", "binomial_design"})
# Input roles a caller may bind to subsets of a claim-kind signal's support (interface R1). A claim row that
# names its deciding roles (`determined_by`) is gated only by those roles' support; an unbound role, or a row
# naming none, is gated by all of the signal's support.
ROLES = {
    "schedule_coverage": ("available", "nominal", "permitted"),
    "finite_policy": ("model",),
    "binomial_design": ("assumptions", "parameters"),
}


@dataclasses.dataclass(frozen=True)
class Support:
    id: str
    status: str
    resolution: str
    basis: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class Signal:
    id: str
    kind: str
    data: dict[str, Any]
    support: tuple[Support, ...]
    bindings: dict[str, a.Proposition]
    application_blockers: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ClaimSignal(Signal):
    """A protocol-kind signal with explicit claims and role-bound support.

    A separate class, so existing Signal serializations and v1 canonical results stay byte-identical.
    """

    claims: tuple[dict, ...] | None = None
    role_support: dict[str, tuple[str, ...]] | None = None


def operator(kind: str):
    if kind not in MODULES:
        raise ValueError("unsupported_signal_kind")
    return importlib.import_module("TrialLedger.layer2." + MODULES[kind])


def support_state(statuses: list[str], resolutions: list[str]) -> str:
    """An evidence source can constrain only with accepted, resolved support (pure — pinned).

    post: __return__ in ("missing_support", "proposed_refused", "binding_unresolved", "accepted")
    post: __return__ != "accepted" or bool(statuses)
    post: __return__ != "accepted" or len(statuses) == len(resolutions)
    post: __return__ != "accepted" or "proposed" not in statuses
    post: __return__ != "accepted" or all(value == "resolved" for value in resolutions)
    """
    if not statuses or len(statuses) != len(resolutions):
        return "missing_support"
    if "proposed" in statuses:
        return "proposed_refused"
    if any(value != "resolved" for value in resolutions):
        return "binding_unresolved"
    return "accepted"


CLAIM_ADMISSIONS = (
    "undetermined",
    "application_blocked",
    "missing_support",
    "proposed_refused",
    "binding_unresolved",
    "accepted",
)


def claim_admission_state(decided: bool, blocked: bool, inner: str, outer: str) -> str:
    """Admit one claim row from its own deciding support; never from another row's (pure).

    pre: inner in ("accepted", "none", "missing_support", "proposed_refused", "binding_unresolved")
    pre: outer in ("missing_support", "proposed_refused", "binding_unresolved", "accepted")
    post: __return__ in CLAIM_ADMISSIONS
    post: __return__ != "accepted" or (decided and not blocked and outer == "accepted")
    post: __return__ != "accepted" or inner in ("accepted", "none")
    post: decided or __return__ == "undetermined"
    """
    if not decided:
        return "undetermined"
    if blocked:
        return "application_blocked"
    if inner not in ("accepted", "none"):
        return inner
    return outer


def _claim_admissions(signal: Signal, calculation: dict) -> list[dict]:
    """Per-claim admission rows over the same gate; the whole-signal code remains the conservative summary.

    Role-bound support narrows only the support a role contributes. Support bound to no role (for example a
    check-level premise) applies to every claim, so it can never be bypassed per claim. Each row retains its
    own effective standing (outer and operator-internal) and determining references for every consumer.
    """
    value = calculation["value"]
    rows = value.get("claims") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        return []
    support = {p.id: p for p in signal.support}
    roles = getattr(signal, "role_support", None) or {}
    bound = {i for ids in roles.values() for i in ids}
    unbound = [i for i in support if i not in bound]
    envelope_status = calculation.get("support_status")
    envelope_resolution = calculation.get("support_resolution") or "resolved"
    envelope_ids = list(calculation.get("determining_ids") or [])
    output = []
    for row in rows:
        named = row.get("determined_by")
        decided = row.get("outcome") not in ("unresolved", "unknown_target", "not_executed", "limit")
        if isinstance(named, list) and named:
            ids = sorted({i for role in named for i in roles.get(role, tuple(support))} | set(unbound))
        else:
            ids = sorted(support)
        statuses = [support[i].status for i in ids]
        resolutions = [support[i].resolution for i in ids]
        inner = "none"
        standing = row.get("standing")
        determining = list(row.get("determining_ids") or [])
        if isinstance(standing, str):
            inner = (
                "accepted"
                if standing in ("known", "interpolated")
                else "none"
                if standing == "no_rule_support"
                else standing
            )
            if standing in ("known", "interpolated"):
                statuses.append(standing)
                resolutions.append("resolved")
            elif standing == "proposed_refused":
                statuses.append("proposed")
                resolutions.append("resolved")
        elif envelope_status is not None:
            statuses.append(envelope_status)
            resolutions.append(envelope_resolution)
            determining = envelope_ids
        state = claim_admission_state(
            decided, bool(signal.application_blockers), inner, support_state(statuses, resolutions)
        )
        output.append(
            {
                "id": row["id"],
                "claim": row.get("claim", row.get("quantity")),
                "outcome": row["outcome"],
                "support": ids,
                "status": entail.weakest_status(tuple(statuses)) if statuses else None,
                "determining_ids": determining,
                "admission": state,
                "effective_outcome": row["outcome"]
                if state in ("accepted", "undetermined")
                else "unresolved",
            }
        )
    return output


def evaluate(signal: Signal, claims: list[dict] | None = None) -> dict:
    """Preserve mathematical output separately from whether its supplied premises may constrain a design."""
    module = operator(signal.kind)
    calculation = (
        module.evaluate(signal.kind, signal.data)
        if claims is None
        else module.check(signal.kind, signal.data, claims)
    )
    fields = {"code", "value", "blockers", "rule"}
    extended = fields | {"support_status", "determining_ids"}
    # An operator may also report its internal support's resolution separately from its status, so that a
    # missing, unresolved or conflicting internal binding is refused as unresolved, never relabelled proposed.
    resolved_form = extended | {"support_resolution"}
    if not isinstance(calculation, dict) or set(calculation) not in (fields, extended, resolved_form):
        raise ValueError("invalid_signal_operator_result")
    status = entail.weakest_status(tuple(p.status for p in signal.support))
    inner = None
    inner_resolution = "resolved"
    if set(calculation) in (extended, resolved_form):
        inner = calculation["support_status"]
        ids = calculation["determining_ids"]
        if inner not in (None, "known", "interpolated", "proposed") or not isinstance(ids, list):
            raise ValueError("invalid_signal_operator_support")
        if set(calculation) == resolved_form:
            declared = calculation["support_resolution"]
            if (inner is None) != (declared is None) or (
                declared is not None and declared not in a.RESOLUTIONS
            ):
                raise ValueError("invalid_signal_operator_support")
            inner_resolution = declared or "resolved"
        if any(not isinstance(identity, str) or not identity for identity in ids) or len(set(ids)) != len(
            ids
        ):
            raise ValueError("invalid_signal_operator_support")
        if inner is not None:
            status = entail.weakest_status((status, inner))
    state = support_state(
        [p.status for p in signal.support] + ([inner] if inner is not None else []),
        [p.resolution for p in signal.support] + ([inner_resolution] if inner is not None else []),
    )
    blockers = list(calculation["blockers"]) + list(signal.application_blockers)
    if state != "accepted":
        blockers.append(state + ":" + signal.id)
    result = {
        "id": signal.id,
        "kind": signal.kind,
        "code": calculation["code"]
        if state == "accepted" and not signal.application_blockers
        else "unresolved",
        "calculation_code": calculation["code"],
        "value": calculation["value"],
        "rule": calculation["rule"],
        "status": status,
        "basis": [ref for p in signal.support for ref in p.basis],
        "support": [dataclasses.asdict(p) for p in signal.support],
        "admission": {"code": state, "application_blockers": list(signal.application_blockers)},
        "blockers": blockers,
    }
    if set(calculation) in (extended, resolved_form):
        result["operator_support"] = {
            "status": calculation["support_status"],
            "determining_ids": list(calculation["determining_ids"]),
        }
        if set(calculation) == resolved_form:
            result["operator_support"]["resolution"] = calculation["support_resolution"]
    if signal.kind in CLAIM_KINDS:
        result["claim_admission"] = _claim_admissions(signal, calculation)
        bound = getattr(signal, "role_support", None)
        if bound is not None:
            result["role_support"] = {role: list(ids) for role, ids in sorted(bound.items())}
    return result


def expression_body(
    expression: dict, bindings: dict[str, a.Proposition], unit: str | None = None
) -> a.Proposition:
    """Bind a derived mathematical witness to explicitly supplied participant predicates.

    This is structural substitution, never clinical recognition. A comparison changes only the numeric
    operand on the bound measurement; its subject, time, scale key and qualifiers survive unchanged.
    """
    kind = expression.get("kind")
    if kind == "comparison":
        ref = expression.get("ref")
        body = bindings.get(ref)
        if not isinstance(body, a.Literal) or body.polarity != "positive" or body.value.kind != "quantity":
            raise ValueError("summary_requires_positive_quantity_binding")
        if unit != body.value.unit:
            raise ValueError("summary_binding_unit_mismatch")
        return dataclasses.replace(
            body,
            value=a.Value(
                "quantity", expression["comparison"], number=expression["number"], unit=body.value.unit
            ),
        )
    refs = expression.get("refs")
    if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) for ref in refs):
        raise ValueError("invalid_witness_expression_refs")
    if len(set(refs)) != len(refs):
        raise ValueError("duplicate_witness_expression_ref")
    if any(ref not in bindings or not isinstance(bindings[ref], a.PROPOSITIONS) for ref in refs):
        raise ValueError("missing_signal_predicate_binding")
    parts = tuple(bindings[ref] for ref in refs)
    if kind == "all_of":
        return parts[0] if len(parts) == 1 else a.AllOf(parts)
    if kind == "none_of":
        return a.Not(parts[0] if len(parts) == 1 else a.AnyOf(parts))
    if kind == "difference" and len(parts) == 2:
        return a.AllOf((parts[0], a.Not(parts[1])))
    raise ValueError("unsupported_witness_expression")


def derived_witness(signal: Signal, result: dict, identity: str, population: str, denominator: int) -> dict:
    """Retain an interval as an interval and refuse a caller's attempt to substitute another population."""
    if signal.data.get("universe") != population or signal.data.get("total") != denominator:
        raise ValueError("derived_witness_population_mismatch")
    value = result["value"]
    rows = value.get("witnesses", []) if isinstance(value, dict) else []
    row = next((row for row in rows if row["id"] == identity), None)
    if row is None:
        if result["code"] in ("unresolved", "conflict"):
            return {
                "body": a.Opaque("unresolved-signal:" + signal.id),
                "lower": None,
                "upper": None,
                "blockers": list(result["blockers"]) or ["signal_conflict:" + signal.id],
                "expression": None,
            }
        raise ValueError("unknown_derived_witness")
    body = expression_body(row["expression"], signal.bindings, signal.data.get("unit"))
    blockers = list(result["blockers"]) if result["code"] not in ("bounded", "consistent") else []
    return {
        "body": body,
        "lower": row["lower"],
        "upper": row["upper"],
        "blockers": blockers,
        "expression": row["expression"],
    }
