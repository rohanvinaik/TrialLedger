"""Explicit consumer admission; provenance and a typed flag alone confer no standing."""

from __future__ import annotations

from typing import Any

from TrialLedger.layer2 import assertions as a


def read_standing(raw: Any, label: str) -> dict:
    """Validate an explicit standing, or preserve omitted support as pending."""
    if raw is None:
        return {"status": "proposed", "resolution": "unresolved", "basis": []}
    if not isinstance(raw, dict) or set(raw) != {"status", "resolution", "basis"}:
        raise ValueError("invalid_standing:" + label)
    if (
        not isinstance(raw["status"], str)
        or not isinstance(raw["resolution"], str)
        or raw["status"] not in a.STATUSES
        or raw["resolution"] not in a.RESOLUTIONS
    ):
        raise ValueError("invalid_standing_vocabulary:" + label)
    basis = raw["basis"]
    if isinstance(basis, list) and len(basis) > 1000:
        raise ValueError("resource_bound:standing_basis:" + label)
    if not isinstance(basis, list) or not basis or any(not isinstance(v, str) or not v for v in basis):
        raise ValueError("missing_standing_basis:" + label)
    return {"status": raw["status"], "resolution": raw["resolution"], "basis": list(basis)}


def admission_code(status: str, resolution: str, accepts_interpolated: bool = False) -> str:
    """Classify support without claiming to verify its source truth (pure).

    post: __return__ in ("accepted", "proposed_refused", "resolution_unresolved", "standing_not_accepted")
    post: __return__ != "accepted" or resolution == "resolved"
    post: __return__ != "accepted" or status == "known" or (accepts_interpolated and status == "interpolated")
    """
    if status == "proposed":
        return "proposed_refused"
    if resolution != "resolved":
        return "resolution_unresolved"
    if status == "known" or (accepts_interpolated and status == "interpolated"):
        return "accepted"
    return "standing_not_accepted"


def code(standing: dict, *, interpolated: bool = False) -> str:
    """Apply the named consumer policy to an already validated standing."""
    return admission_code(standing["status"], standing["resolution"], interpolated)
