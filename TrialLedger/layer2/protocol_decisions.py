"""Protocol alternatives (C8): validation, candidate construction and pure classifications.

One responsibility per function. Execution of candidate checks stays in design_session's ordinary budgeted
child path; this module never runs an operator, reads files or decides a clinical choice.
"""

from __future__ import annotations

import copy
import json
from typing import Any

FIELDS = {"kind", "id", "question", "target", "coverage", "selected", "alternatives"}
ALTERNATIVE_FIELDS = {"id", "label", "replace_objects", "checks"}
MAX_ALTERNATIVES = 16
MAX_REPLACEMENTS = 16
CHECK_CODES = ("not_applicable", "violated", "repair_choice", "undetermined", "satisfied")
COMPATIBILITY = (
    "incompatible_under_declared_checks",
    "undetermined",
    "repair_choice_open_under_declared_checks",
    "compatible_under_declared_checks",
)
DISPOSITIONS = (
    "blocker",
    "repair_choice",
    "design_choice",
    "evidence_question",
    "settled_within_declared_alternatives",
    "no_compatible_alternative",
)
# Rohan, 2026-11-04: policy failures are conflicts (incompatible, blocking); schedule gaps and an unmet
# binomial target are the person's repair choice, in comparisons as in the clinical labels.
CONFLICT_OUTCOMES = frozenset({"gap", "competing", "violation", "not_established", "inconsistent_domain"})
REPAIR_OUTCOMES = frozenset(
    {"no_feasible_time", "no_permitted_time", "outside_window", "not_collected", "uncovered", "not_satisfied"}
)
FAILURE_OUTCOMES = CONFLICT_OUTCOMES | REPAIR_OUTCOMES
CONFLICT_CODES = frozenset({"conflict", "inconsistent", "violated"})


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _fail(code: str) -> ValueError:
    return ValueError("protocol_option_" + code)


def validate(raw: object, index: dict, target: dict) -> dict:
    """One protocol decision, validated against the admitted protocol index; returns a detached copy."""
    if type(raw) is not dict or set(raw) - (FIELDS | {"evidence"}) or FIELDS - set(raw):
        raise _fail("fields")
    item = copy.deepcopy(raw)
    if item["kind"] != "protocol_options":
        raise _fail("fields")
    if (
        type(item["id"]) is not str
        or not item["id"]
        or type(item["question"]) is not str
        or not item["question"]
    ):
        raise _fail("fields")
    if item["coverage"] != "declared_design":
        raise _fail("coverage")
    if _canonical(item["target"]) != _canonical(target):
        raise _fail("target_changed")
    alternatives = item["alternatives"]
    if type(alternatives) is not list or not 2 <= len(alternatives) <= MAX_ALTERNATIVES:
        raise _fail("count")
    required = {
        cid
        for cid, check in index["checks"].items()
        if check["required"] is True and _canonical(check["scope"]["target"]) == _canonical(target)
    }
    if not required:
        raise _fail("no_required_check")
    ids, optional_sets = set(), set()
    for alt in alternatives:
        if type(alt) is not dict or set(alt) != ALTERNATIVE_FIELDS:
            raise _fail("fields")
        if type(alt["id"]) is not str or not alt["id"] or alt["id"] in ids:
            raise _fail("fields")
        ids.add(alt["id"])
        if type(alt["label"]) is not str or not alt["label"]:
            raise _fail("fields")
        checks = alt["checks"]
        if type(checks) is not list or len(set(map(str, checks))) != len(checks):
            raise _fail("fields")
        if any(c not in index["checks"] for c in checks):
            raise _fail("unknown_check")
        if not required <= set(checks):
            raise _fail("missing_required_check")
        optional_sets.add(tuple(sorted(set(checks) - required)))
        replacements = alt["replace_objects"]
        if type(replacements) is not list or len(replacements) > MAX_REPLACEMENTS:
            raise _fail("fields")
        seen = set()
        for obj in replacements:
            if type(obj) is not dict or "id" not in obj or "kind" not in obj or "scope" not in obj:
                raise _fail("fields")
            if obj["id"] not in index["objects"] or obj["id"] in seen:
                raise _fail("unknown_object")
            seen.add(obj["id"])
            if obj["kind"] != index["kinds"][obj["id"]]:
                raise _fail("kind_changed")
            held = index["objects"][obj["id"]]["scope"]["target"]
            if type(obj["scope"]) is not dict or _canonical(obj["scope"].get("target")) != _canonical(held):
                raise _fail("target_changed")
    if len(optional_sets) != 1:
        raise _fail("context_mismatch")
    selected = item["selected"]
    if selected is not None:
        if type(selected) is not dict or set(selected) != {"alternative", "origin", "basis"}:
            raise _fail("selection")
        basis = selected["basis"]
        if selected["origin"] != "user" or selected["alternative"] not in ids:
            raise _fail("selection")
        if type(basis) is not list or not basis or any(type(b) is not str or not b for b in basis):
            raise _fail("selection")
    return item


def candidate(protocol: dict, replacements: list[dict]) -> dict:
    """The baseline protocol with the listed objects replaced simultaneously; the baseline is untouched."""
    out = copy.deepcopy(protocol)
    swap = {obj["id"]: copy.deepcopy(obj) for obj in replacements}
    out["objects"] = [swap.get(obj["id"], obj) for obj in out["objects"]]
    return out


def check_code(
    application: list[str], admitted_conflict: bool, admitted_repair: bool, unsettled: bool
) -> str:
    """One listed check's outcome inside a frame (pure).

    pre: all(isinstance(a, str) for a in application)
    post: __return__ in CHECK_CODES
    post: not admitted_conflict or __return__ in ("violated", "not_applicable")
    post: __return__ != "repair_choice" or (admitted_repair and not admitted_conflict)
    post: __return__ != "satisfied" or not (admitted_conflict or admitted_repair or unsettled)
    """
    if application and all(a == "not_applicable" for a in application):
        return "not_applicable"
    if admitted_conflict:
        return "violated"
    if unsettled:
        return "undetermined"
    if admitted_repair:
        return "repair_choice"
    return "satisfied"


def compatibility(required_codes: list[str]) -> str:
    """Aggregate only the required checks; optional context never decides (pure).

    pre: all(code in CHECK_CODES for code in required_codes)
    post: __return__ in COMPATIBILITY
    post: __return__ != "compatible_under_declared_checks" or "satisfied" in required_codes
    post: "violated" not in required_codes or __return__ == "incompatible_under_declared_checks"
    post: __return__ != "repair_choice_open_under_declared_checks" or "repair_choice" in required_codes
    """
    if "violated" in required_codes:
        return "incompatible_under_declared_checks"
    if "undetermined" in required_codes:
        return "undetermined"
    if "repair_choice" in required_codes:
        return "repair_choice_open_under_declared_checks"
    if "satisfied" not in required_codes:
        return "undetermined"
    return "compatible_under_declared_checks"


def disposition(rows: list[tuple[str, str]], selected: str | None) -> str:
    """Decision disposition from (compatibility, candidate digest) rows and the attributed selection (pure).

    `rows` are in alternative order; `selected` is the selected alternative's compatibility or None.

    pre: all(row[0] in COMPATIBILITY for row in rows)
    post: __return__ in DISPOSITIONS
    post: selected != "incompatible_under_declared_checks" or __return__ == "blocker"
    post: selected != "repair_choice_open_under_declared_checks" or __return__ == "repair_choice"
    """
    if selected == "incompatible_under_declared_checks":
        return "blocker"
    if selected == "repair_choice_open_under_declared_checks":
        return "repair_choice"
    compatible = [digest for code, digest in rows if code == "compatible_under_declared_checks"]
    if len(compatible) >= 2 and len(set(compatible)) >= 2:
        return "design_choice"
    if any(code == "undetermined" for code, _ in rows):
        return "evidence_question"
    if len(compatible) >= 1:
        return "settled_within_declared_alternatives"
    if any(code == "repair_choice_open_under_declared_checks" for code, _ in rows):
        return "repair_choice"
    return "no_compatible_alternative"


def classify(check: dict) -> str:
    """Read one executed check row (as built by design_session) into its check_code."""
    claims = [row for child in check["children"] for s in child["signals"] for row in s["claim_admission"]]
    applications = [row["application"] for row in claims]
    admitted = [
        row for row in claims if row["admission"] == "accepted" and row["application"] != "not_applicable"
    ]
    plain = [s for child in check["children"] for s in child["signals"] if not s["claim_admission"]]
    admitted_conflict = any(row["outcome"] in CONFLICT_OUTCOMES for row in admitted) or any(
        s["admission"]["code"] == "accepted" and s["calculation_code"] in CONFLICT_CODES for s in plain
    )
    admitted_repair = any(row["outcome"] in REPAIR_OUTCOMES for row in admitted)
    unsettled = (
        bool(check["unresolved"])
        or check["not_computed"] is not None
        or not check["children"]
        or any(child["refusal"] for child in check["children"])
        or any(s["code"] == "limit" for child in check["children"] for s in child["signals"])
        # A conditional claim is a checked conditional obligation (Rohan, 2026-11-04), not undetermined.
        or any(row["admission"] != "accepted" for row in claims if row["application"] != "not_applicable")
        or any(
            s["admission"]["code"] != "accepted" or s["code"] != s["calculation_code"] or s["blockers"]
            for s in plain
        )
    )
    return check_code(applications, admitted_conflict, admitted_repair, unsettled)


def assumed_entry_ids(assumed: set[str]) -> set[str]:
    """Support-entry ids a hypothetical frame may treat as accepted: only replaced objects' own entries."""
    return {f"object:{i}" for i in assumed} | {f"adoption:{i}" for i in assumed}


def frame_request(request: dict, assumed: set[str], frame_ref: str) -> dict:
    """Lift only assumed objects' own entries in a candidate frame; premise entries keep their standing."""
    out: dict[str, Any] = copy.deepcopy(request)
    lifted = assumed_entry_ids(assumed)
    for signal in out.get("signals", []):
        for entry in signal.get("support", []):
            if entry["id"] in lifted:
                entry.update(status="known", resolution="resolved", basis=[frame_ref])
    return out
