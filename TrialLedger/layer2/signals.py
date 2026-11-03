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


def evaluate(signal: Signal, claims: list[dict] | None = None) -> dict:
    """Preserve mathematical output separately from whether its supplied premises may constrain a design."""
    module = operator(signal.kind)
    calculation = (
        module.evaluate(signal.kind, signal.data)
        if claims is None
        else module.check(signal.kind, signal.data, claims)
    )
    if not isinstance(calculation, dict) or set(calculation) != {"code", "value", "blockers", "rule"}:
        raise ValueError("invalid_signal_operator_result")
    state = support_state([p.status for p in signal.support], [p.resolution for p in signal.support])
    blockers = list(calculation["blockers"])
    if state != "accepted":
        blockers.append(state + ":" + signal.id)
    return {
        "id": signal.id,
        "kind": signal.kind,
        "code": calculation["code"] if state == "accepted" else "unresolved",
        "calculation_code": calculation["code"],
        "value": calculation["value"],
        "rule": calculation["rule"],
        "status": entail.weakest_status(tuple(p.status for p in signal.support)),
        "basis": [ref for p in signal.support for ref in p.basis],
        "support": [dataclasses.asdict(p) for p in signal.support],
        "blockers": blockers,
    }


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
