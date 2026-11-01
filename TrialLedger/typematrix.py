"""The supported-type matrix and its manifest (add-bank-coverage Decision 7, founder decision B1).

A trial's type is not its condition alone. The axes: condition category (the sample's strata, as condition
MeSH terms or ancestors), intervention type, primary purpose, phase (not applicable among them, combined
phases as written), allocation, intervention model, and the populations children, healthy volunteers and
pregnancy. Each axis's values come from the vendored registry enums or the sample's own declarations, never
copied. v1's universe (B1, 2026-11-01): every interventional study started 2010 to the present, all phases,
purposes and populations; observational studies and expanded access are declared unsupported, each a later
type. Pregnancy has no registry field: its coordinate is never read from text, and is `not_in_registry`.

The manifest says, for every declared value of every axis, whether it is supported, unsupported (with its
reason) or not yet measured; a value is supported only with measured results cited (an evaluation's id).
"""

from __future__ import annotations

from typing import Any

from TrialLedger.registry import enum_labels
from TrialLedger.sample import CATEGORIES, NO_MESH, NONE, declared_cells, trial_cells

NOT_IN_REGISTRY = "not_in_registry"
UNSUPPORTED: dict[str, str] = {
    "OBSERVATIONAL": "observational studies are unsupported in v1, a declared later type",
    "EXPANDED_ACCESS": "expanded access is unsupported in v1, a declared later type",
}
UNIVERSE: dict[str, Any] = {
    "declared": "founder decision B1, 2026-11-01",
    "study_type": "INTERVENTIONAL",
    "start_from": "2010-01",  # year and month, the precision every start date has
    "start_to": "present",  # open-ended: a run passes the present it is read at, never a clock
    "unsupported": UNSUPPORTED,
}
UNIVERSE_CODES = (
    "in_universe",
    "study_type_not_stated",
    "observational_unsupported",
    "expanded_access_unsupported",
    "unknown_study_type",
    "start_date_not_stated",
    "start_date_unreadable",
    "before_universe",
    "after_present",
)
_CELLS = declared_cells()
AXIS_VALUES: dict[str, tuple[str, ...]] = {
    "study_type": tuple(enum_labels("StudyType")),
    "condition_category": (*CATEGORIES, NO_MESH),
    "phase": tuple(_CELLS["phase"]),
    "intervention_type": tuple(_CELLS["intervention_type"]),
    "primary_purpose": tuple(_CELLS["primary_purpose"]),
    "allocation": tuple(enum_labels("DesignAllocation")),
    "intervention_model": tuple(enum_labels("InterventionalAssignment")),
    "children": ("yes", "no"),
    "healthy_volunteers": ("yes", "no"),
    "pregnancy": ("yes", "no"),
}
MANIFEST_STATUSES = ("supported", "unsupported", "unmeasured")
MANIFEST_FIELDS = ("axis", "value", "status", "reason", "evidence")


def _module(protocol: dict[str, Any], name: str) -> dict[str, Any]:
    found = protocol.get(name)
    return found if isinstance(found, dict) else {}


def study_coordinates(study: dict[str, Any]) -> dict[str, list[str]]:
    """The type-matrix coordinates one record holds, each axis a list of values (pure — pinned).

    Phase, intervention type and primary purpose as the balance cells read them (`sample.trial_cells`).
    Condition category: each declared category among the record's condition MeSH terms or ancestors
    (derivedSection.conditionBrowseModule), in declared order; none of them while terms exist: NONE; no terms
    at all: NO_MESH. Allocation and intervention model: the design's value. Children: "yes" when the
    standard age groups include CHILD, "no" when they are stated without it. Healthy volunteers: "yes" or "no"
    as the boolean states. Pregnancy: not_in_registry, always. A field the record does not fill is NONE.
    """
    protocol = study.get("protocolSection")
    protocol = protocol if isinstance(protocol, dict) else {}
    derived = study.get("derivedSection")
    browse = _module(derived if isinstance(derived, dict) else {}, "conditionBrowseModule")
    listed = [browse.get("meshes"), browse.get("ancestors")]
    terms = {
        item["term"]
        for items in listed
        if isinstance(items, list)
        for item in items
        if isinstance(item, dict) and isinstance(item.get("term"), str)
    }
    categories = [category for category in CATEGORIES if category in terms]
    info = _module(_module(protocol, "designModule"), "designInfo")
    eligibility = _module(protocol, "eligibilityModule")
    ages = eligibility.get("stdAges")
    healthy = eligibility.get("healthyVolunteers")
    allocation, model = info.get("allocation"), info.get("interventionModel")
    return {
        **trial_cells(study),
        "condition_category": categories or ([NONE] if terms else [NO_MESH]),
        "allocation": [allocation if isinstance(allocation, str) and allocation else NONE],
        "intervention_model": [model if isinstance(model, str) and model else NONE],
        "children": [("yes" if "CHILD" in ages else "no") if isinstance(ages, list) and ages else NONE],
        "healthy_volunteers": [("yes" if healthy else "no") if isinstance(healthy, bool) else NONE],
        "pregnancy": [NOT_IN_REGISTRY],
    }


def universe_status(study: dict[str, Any], present: str | None = None) -> str:
    """Whether a record is in v1's universe, or why not (pure — pinned).

    The study type first: not stated, OBSERVATIONAL, EXPANDED_ACCESS or another value than INTERVENTIONAL
    each has its code. Then the start date (statusModule.startDateStruct.date, "YYYY-MM" or "YYYY-MM-DD"):
    not stated, unreadable, before 2010-01 (before_universe), or later than `present` compared at the
    start's own precision (after_present; None: the universe is open-ended). Otherwise in_universe.
    """
    protocol = study.get("protocolSection")
    protocol = protocol if isinstance(protocol, dict) else {}
    study_type = _module(protocol, "designModule").get("studyType")
    if not isinstance(study_type, str) or not study_type:
        return "study_type_not_stated"
    if study_type == "OBSERVATIONAL":
        return "observational_unsupported"
    if study_type == "EXPANDED_ACCESS":
        return "expanded_access_unsupported"
    if study_type != UNIVERSE["study_type"]:
        return "unknown_study_type"
    date = _module(_module(protocol, "statusModule"), "startDateStruct").get("date")
    if not isinstance(date, str) or not date:
        return "start_date_not_stated"
    parts = date.split("-")
    if len(parts) not in (2, 3) or not all(part.isdigit() for part in parts) or len(parts[0]) != 4:
        return "start_date_unreadable"
    if date[:7] < UNIVERSE["start_from"]:
        return "before_universe"
    if present is not None and date > present[: len(date)]:
        return "after_present"
    return "in_universe"


def declared_manifest() -> dict[str, Any]:
    """The manifest before anything is measured: every declared value of every axis unmeasured, except the
    study types outside the universe, unsupported with their reasons."""
    rows = []
    for axis, values in AXIS_VALUES.items():
        for value in values:
            reason = UNSUPPORTED.get(value, "") if axis == "study_type" else ""
            status = "unsupported" if reason else "unmeasured"
            rows.append({"axis": axis, "value": value, "status": status, "reason": reason, "evidence": None})
    return {"universe": UNIVERSE, "rows": rows}


def manifest_problems(manifest: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    """What makes a supported/unsupported manifest unaccountable (pure — pinned).

    For each row, in order, as (code, axis, value): wrong_fields (its keys are not MANIFEST_FIELDS),
    unknown_axis, unknown_value, duplicate_row, unknown_status, supported_without_evidence (supported only
    with measured results cited), unsupported_without_reason. Then missing_row for every declared value of
    every axis no row states. A manifest without a rows list: one ("no_rows", "", ""). No problem: empty.
    """
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        return (("no_rows", "", ""),)
    found: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict) or tuple(row) != MANIFEST_FIELDS:
            found.append(("wrong_fields", str(row.get("axis", "")) if isinstance(row, dict) else "", ""))
            continue
        axis, value, status = str(row["axis"]), str(row["value"]), row["status"]
        if axis not in AXIS_VALUES:
            found.append(("unknown_axis", axis, value))
        elif value not in AXIS_VALUES[axis]:
            found.append(("unknown_value", axis, value))
        if (axis, value) in seen:
            found.append(("duplicate_row", axis, value))
        seen.add((axis, value))
        if status not in MANIFEST_STATUSES:
            found.append(("unknown_status", axis, value))
        if status == "supported" and not row["evidence"]:
            found.append(("supported_without_evidence", axis, value))
        if status == "unsupported" and not str(row["reason"] or "").strip():
            found.append(("unsupported_without_reason", axis, value))
    for axis, values in AXIS_VALUES.items():
        found.extend(("missing_row", axis, value) for value in values if (axis, value) not in seen)
    return tuple(found)
