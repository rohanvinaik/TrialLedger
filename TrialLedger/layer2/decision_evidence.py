"""Exact decision context; location warrants quotation, never its clinical interpretation."""

from __future__ import annotations

from copy import deepcopy

from TrialLedger.layer2 import source_evidence

MAX_CONTEXT = 32


def role_code(role: str) -> str:
    """Name context origins without turning a reading or gap into a source fact (pure).

    post: __return__ in ('source_quote', 'caller_reading', 'caller_gap', 'invalid_context_role')
    post: __return__ != 'source_quote' or role == 'quote'
    post: __return__ != 'caller_gap' or role == 'gap'
    """
    if type(role) is not str:
        return "invalid_context_role"
    return {"quote": "source_quote", "reading": "caller_reading", "gap": "caller_gap"}.get(
        role, "invalid_context_role"
    )


def locate(entries: object, sources: dict) -> list[dict]:
    """Verify complete explicit anchors; return context only, never solver assertions."""
    if type(entries) is not list:
        raise ValueError("not_list:decision.evidence")
    if len(entries) > MAX_CONTEXT:
        raise ValueError("resource_bound:decision.evidence")
    out, seen = [], set()
    required = {"id", "source", "anchor", "role"}
    for raw in entries:
        entry = source_evidence._object(raw, required | {"note", "scope"}, required, "decision.evidence")
        identity = source_evidence._text(entry["id"], "decision.evidence.id")
        if identity in seen:
            raise ValueError("duplicate_id:decision.evidence")
        seen.add(identity)
        source_id = source_evidence._text(entry["source"], "decision.evidence.source")
        if source_id not in sources:
            raise ValueError("unknown_source:decision.evidence")
        origin = role_code(entry["role"])
        if origin == "invalid_context_role":
            raise ValueError(origin)
        for field, maximum in (("note", 4096), ("scope", 1024)):
            value = entry.get(field, "")
            if type(value) is not str or len(value) > maximum:
                raise ValueError("invalid_text:decision.evidence." + field)
        held = sources[source_id]
        anchor = source_evidence.anchors(held["study"], held["snapshot"], [entry["anchor"]])[0]
        if anchor["id"] != identity:
            raise ValueError("identity_mismatch:decision.evidence.anchor")
        out.append(
            {
                "id": identity,
                "source_id": source_id,
                "role": entry["role"],
                "origin": origin,
                "source": deepcopy(held["snapshot"]),
                "anchor": anchor,
                "source_value_standing": "known",
                "note": entry.get("note", ""),
                "note_origin": "caller_supplied_annotation",
                "note_standing": "proposed",
                "declared_scope": entry.get("scope", ""),
                "scope_origin": "caller_declared; no population or applicability binding",
                "effect": "context_only; no assertion or semantic absence inferred",
            }
        )
    return out
