"""Pure clinical protocol view over one canonical v2 design_session result (packet F).

The view arranges fields already present in the result and renders exact values as text. It runs no solver or
operator, reads no files, interprets no prose and supplies no premise. Wording is a fixed table keyed by claim
and effective outcome; no caller label enters a computed sentence.
"""

from __future__ import annotations

import copy
from fractions import Fraction
from typing import Any

from TrialLedger.layer2.protocol_numbers import render

SCHEMA_VERSION = 1
SECTION_IDS = (
    "population",
    "eligibility",
    "interventions",
    "endpoints",
    "assessments",
    "efficacy",
    "safety",
    "exploratory",
)
CONDITIONAL_PREFIX = "If the declared condition applies: "
EXTRA_LIMITS = (
    "Coverage and violations are over the declared variables, objects and claims only.",
    "Rendered decimals are rounded displays; exact rationals are canonical.",
)
# Effective outcomes that name an unapplied or unknown answer (open items, section "open").
UNSETTLED = ("unresolved", "unknown_target", "undetermined", "not_executed")
# Effective outcomes that name a found failure.
FAILURES = (
    "no_feasible_time",
    "no_permitted_time",
    "outside_window",
    "not_collected",
    "uncovered",
    "gap",
    "competing",
    "violation",
    "violated",
    "not_satisfied",
    "not_established",
    "open",
    "conflict",
)
STATIC_WORDING = {
    ("existence", "satisfied"): "At least one permitted assessment time falls within planned collection.",
    ("existence", "no_feasible_time"): "No permitted assessment time falls within planned collection.",
    ("existence", "no_permitted_time"): "The permitted window is empty, so no assessment is permitted.",
    ("full_window", "no_permitted_time"): "The permitted window is empty, so no assessment is permitted.",
    (
        "nominal",
        "satisfied",
    ): "The nominal target is inside the permitted window and within planned collection.",
    ("nominal", "outside_window"): "The nominal target is outside the permitted window.",
    (
        "nominal",
        "not_collected",
    ): "The nominal target is inside the permitted window but outside planned collection.",
    ("nominal", "unknown_target"): "No nominal target is declared.",
    ("full_window", "satisfied"): "Planned collection covers every permitted assessment time.",
    ("coverage", "covered"): "Every reachable declared situation has a rule.",
    ("exclusivity", "exclusive"): "No reachable declared situation enables more than one rule.",
    ("prohibition", "clear"): "No declared prohibition is violated in reachable declared situations.",
    ("prohibition", "not_declared"): "No prohibition is declared.",
    ("invariant", "holds"): "Every declared invariant holds in reachable declared situations.",
    ("invariant", "not_declared"): "No invariant is declared.",
    (
        "termination",
        "all_paths_terminate",
    ): "Every permitted path in the declared model reaches a terminal state.",
}
COUNT_WORDING = {
    ("coverage", "gap"): "{n} reachable declared situation(s) have no rule.",
    ("exclusivity", "competing"): "{n} reachable declared situation(s) enable more than one rule.",
    ("prohibition", "violation"): "{n} declared prohibition violation(s) in reachable declared situations.",
    ("invariant", "violation"): "{n} declared invariant failure(s).",
}
QUANTITIES = {"null_rejection_probability": "null rejection probability", "power": "power"}


def interval_text(raw: Any) -> str:
    """Render one interval-union value as exact text.

    pre: raw is None or isinstance(raw, list)
    post: isinstance(__return__, str)
    post: raw is not None or __return__ == "unknown"
    post: raw != [] or __return__ == "none"
    """
    if raw is None:
        return "unknown"
    if not raw:
        return "none"
    return " ∪ ".join(_one_interval(item) for item in raw)


def _one_interval(item: dict) -> str:
    lower, upper = item.get("lower"), item.get("upper")
    low = None if lower is None else render(Fraction(lower))
    high = None if upper is None else render(Fraction(upper))
    if low is not None and low == high and item.get("lower_inclusive") and item.get("upper_inclusive"):
        return "{" + low + "}"
    left = "[" if item.get("lower_inclusive") and low is not None else "("
    right = "]" if item.get("upper_inclusive") and high is not None else ")"
    return f"{left}{'-∞' if low is None else low}, {'+∞' if high is None else high}{right}"


def rational_text(raw: Any) -> str:
    """Render a canonical rational string, or "unknown" for null.

    pre: raw is None or isinstance(raw, str)
    post: isinstance(__return__, str)
    post: raw is not None or __return__ == "unknown"
    """
    return "unknown" if raw is None else render(Fraction(raw))


def _get(node: Any, *path: Any) -> Any:
    for step in path:
        try:
            node = node[step]
        except (KeyError, IndexError, TypeError):
            return None
    return node


def _signal_value(child: dict) -> dict:
    value = _get(child, "result", "result", "signals", 0, "value")
    return value if isinstance(value, dict) else {}


def _value_claim(child: dict, claim_id: object) -> dict:
    for row in _signal_value(child).get("claims") or []:
        if isinstance(row, dict) and row.get("id") == claim_id:
            return row
    return {}


def _decimal(value: dict, quantity: str) -> str | None:
    display = value.get("display")
    shown = display.get(quantity) if isinstance(display, dict) else None
    return shown if isinstance(shown, str) else None


def claim_wording(row: dict, child: dict) -> str:
    """Fixed wording for one claim row, chosen by (claim, effective_outcome).

    pre: isinstance(row, dict)
    post: isinstance(__return__, str)
    post: row.get("application") != "conditional" or __return__.startswith(CONDITIONAL_PREFIX)
    """
    suffix = (
        " Applicability rests on interpolated support."
        if row.get("application_status") == "interpolated"
        else ""
    )
    if row.get("application") == "not_applicable":
        return "Not applicable: the declared condition does not hold in this scope." + suffix
    text = _template(row, child)
    return (CONDITIONAL_PREFIX + text if row.get("application") == "conditional" else text) + suffix


def _template(row: dict, child: dict) -> str:
    claim, effective = row.get("claim"), row.get("effective_outcome")
    if effective == "unresolved" and row.get("admission") == "undetermined":
        # Not a refusal: the operator could not decide because a declared input is missing.
        return "Not determined: an input this claim needs is not declared."
    if effective == "unresolved":
        return f"Not applied: the deciding support is {row.get('admission')}."
    if effective == "not_executed":
        return "Not computed within the declared work limit."
    key: Any = (claim, effective)
    if key in STATIC_WORDING:
        return STATIC_WORDING[key]
    detail = _value_claim(child, row.get("id"))
    if key in COUNT_WORDING and isinstance(detail.get("violations_found"), int):
        return COUNT_WORDING[key].format(n=detail["violations_found"])
    if key == ("full_window", "uncovered"):
        gap = interval_text(detail.get("uncovered"))
        return f"Planned collection does not cover part of the permitted window: {gap}."
    if key == ("termination", "not_established") and isinstance(detail.get("reasons"), list):
        return (
            "Termination is not established in the declared model: "
            + ", ".join(str(reason) for reason in detail["reasons"])
            + "."
        )
    if claim in QUANTITIES and effective in ("satisfied", "not_satisfied") and "computed" in detail:
        return _bound_wording(claim, effective, detail, _signal_value(child))
    return f"Outcome: {effective}."


def _bound_wording(claim: str, effective: str, detail: dict, value: dict) -> str:
    computed = rational_text(detail["computed"])
    shown = _decimal(value, claim)
    if shown is not None:
        computed = f"{computed} ({shown})"
    verb = "meets" if effective == "satisfied" else "does not meet"
    bound = rational_text(detail.get("value"))
    comparison = detail.get("comparison")
    return f"The exact {QUANTITIES[claim]} {computed} {verb} the declared bound {comparison} {bound}."


def section_coverage(declared: Any, basis: Any, objects: Any, consuming: list[dict]) -> tuple[str, list[str]]:
    """Coverage code and reasons for one section; the first matching rule wins.

    pre: declared in ("requested", "not_applicable", "not_requested")
    post: __return__[0] in ("not_requested", "not_applicable", "open", "not_computed", "specified")
    post: declared != "not_requested" or __return__ == ("not_requested", [])
    post: __return__[0] != "specified" or __return__[1] == []
    """
    if declared == "not_requested":
        return "not_requested", []
    if declared == "not_applicable":
        return "not_applicable", list(basis)
    if not objects:
        return "open", ["no_objects_declared"]
    not_computed = [f"not_computed:{c['id']}" for c in consuming if _is_not_computed(c)]
    if not_computed:
        return "not_computed", not_computed
    reasons = [reason for c in consuming for reason in _open_reasons(c)]
    if reasons:
        return "open", reasons
    if not consuming:
        return "open", ["no_check_declared"]
    return "specified", []


def _signals(check: dict) -> list[dict]:
    return [s for child in check.get("children") or [] for s in child.get("signals") or []]


def _claim_rows(check: dict) -> list[tuple[dict, dict]]:
    return [
        (row, child)
        for child in check.get("children") or []
        for signal in child.get("signals") or []
        for row in signal.get("claim_admission") or []
    ]


def _is_not_computed(check: dict) -> bool:
    if check.get("not_computed") is not None:
        return True
    if any(s.get("code") == "limit" for s in _signals(check)):
        return True
    return any(
        "not_executed" in (row.get("outcome"), row.get("effective_outcome")) for row, _ in _claim_rows(check)
    )


def signal_finding_codes(signal: dict) -> list[str]:
    """Findings of an existing-operator signal with no claim rows, read from its own fields (pure).

    A signal is clean only when admitted, unchanged by the gate and without blockers; otherwise each
    blocker (or its code, when it names none) is retained verbatim. The view never reinterprets them.

    pre: isinstance(signal, dict)
    post: isinstance(__return__, list)
    post: all(isinstance(code, str) and code for code in __return__)
    """
    admission = (signal.get("admission") or {}).get("code")
    blockers = [str(b) for b in signal.get("blockers") or [] if b]
    clean = admission == "accepted" and signal.get("code") == signal.get("calculation_code") and not blockers
    if clean:
        return []
    return blockers or [f"code:{signal.get('code')}"]


def _plain_signals(check: dict) -> list[tuple[int, dict]]:
    return [
        (j, signal)
        for j, child in enumerate(check.get("children") or [])
        for signal in child.get("signals") or []
        if not signal.get("claim_admission")
    ]


def _open_reasons(check: dict) -> list[str]:
    out = [f"unresolved:{check['id']}:{entry.get('code')}" for entry in check.get("unresolved") or []]
    out += [
        f"signal:{check['id']}:{code}"
        for _, sig in _plain_signals(check)
        for code in signal_finding_codes(sig)
    ]
    rows = _claim_rows(check)
    out += [
        f"claim_unresolved:{check['id']}:{r.get('id')}"
        for r, _ in rows
        if r.get("effective_outcome") in UNSETTLED
    ]
    # A conditional claim is a checked conditional obligation, not an unchecked one: it does not open the
    # section. It stays visible as a claim_conditional open item and in its wording (corrected after review).
    return out


def _check_ref(index: int) -> str:
    return f"/protocol/checks/{index}"


def _child_ref(index: int, child_index: int) -> str:
    return f"/protocol/checks/{index}/children/{child_index}/result"


def _check_row(index: int, check: dict) -> dict:
    children = check.get("children") or []
    signals = _signals(check)
    first = signals[0] if signals else None
    claims = []
    for child in children:
        for signal in child.get("signals") or []:
            for row in signal.get("claim_admission") or []:
                claims.append(
                    {
                        "id": row.get("id"),
                        "claim": row.get("claim"),
                        "outcome": row.get("outcome"),
                        "effective_outcome": row.get("effective_outcome"),
                        "admission": row.get("admission"),
                        "application": row.get("application"),
                        "standing_support": copy.deepcopy(row.get("support")),
                        # The clinical finding is no stronger than its applicability proof; the arithmetic's
                        # own standing stays visible separately (external review).
                        "standing": row.get("finding_status") or row.get("status"),
                        "arithmetic_standing": row.get("status"),
                        "application_standing": row.get("application_status"),
                        "determining_ids": copy.deepcopy(row.get("determining_ids") or [])
                        + [
                            r
                            for r in row.get("application_refs") or []
                            if r not in (row.get("determining_ids") or [])
                        ],
                        "wording": claim_wording(row, child),
                    }
                )
    return {
        "id": check["id"],
        "kind": check["kind"],
        "required": check["required"],
        "projection": check.get("projection"),
        "summary": None
        if first is None
        else {
            "code": first.get("code"),
            "calculation_code": first.get("calculation_code"),
            "admission": copy.deepcopy(first.get("admission")),
        },
        "claims": claims,
        "findings": [
            {
                "signal": sig.get("id"),
                "kind": sig.get("kind"),
                "code": sig.get("code"),
                "calculation_code": sig.get("calculation_code"),
                "admission": (sig.get("admission") or {}).get("code"),
                "codes": signal_finding_codes(sig),
                "ref": _child_ref(index, j),
            }
            for j, sig in _plain_signals(check)
        ],
        "unresolved": copy.deepcopy(check.get("unresolved") or []),
        "not_computed": copy.deepcopy(check.get("not_computed")),
        "conditions": [copy.deepcopy(c) for child in children for c in child.get("conditions") or []],
        "refs": [
            {
                "result": _child_ref(index, j),
                "request_digest": child.get("request_digest"),
                "result_digest": child.get("result_digest"),
            }
            for j, child in enumerate(children)
        ],
    }


def _by_kind(protocol: dict, check: dict, kind: str) -> dict | None:
    wanted = set(check.get("objects") or [])
    for obj in protocol.get("objects") or []:
        if obj.get("id") in wanted and obj.get("kind") == kind:
            return obj
    return None


def _context(check: dict, key: str) -> str:
    value = _get(check, "scope", "context", key)
    return "all (open)" if value is None else str(value)


def _schedule_row(protocol: dict, index: int, check: dict, row: dict) -> dict:
    assessment = _by_kind(protocol, check, "assessment")
    collection = _by_kind(protocol, check, "collection")
    adata = (assessment or {}).get("data") or {}
    children = check.get("children") or []
    child = children[0] if children else None
    out = {
        "check": check["id"],
        "assessment": None if assessment is None else assessment["id"],
        "collection": None if collection is None else collection["id"],
        "cohort": _context(check, "cohort"),
        "arm": _context(check, "arm"),
        "phase": _context(check, "phase"),
        "measurement": adata.get("measurement"),
        "mode": ((collection or {}).get("data") or {}).get("mode"),
        "anchor": adata.get("anchor"),
        "unit": adata.get("unit"),
    }
    out.update(_schedule_numbers(child, [c.get("code") for c in check.get("unresolved") or []], row))
    stand, origin = {}, {}
    for obj in (assessment, collection):
        if obj is not None:
            stand[obj["kind"]] = _get(obj, "standing", "status")
            origin[obj["kind"]] = {"kind": _get(obj, "origin", "kind"), "ref": _get(obj, "origin", "ref")}
    out["standing"], out["origin"], out["refs"] = stand, origin, copy.deepcopy(row["refs"])
    return {key: out[key] for key in SCHEDULE_KEYS}


SCHEDULE_KEYS = (
    "check",
    "assessment",
    "collection",
    "cohort",
    "arm",
    "phase",
    "conditionality",
    "measurement",
    "mode",
    "anchor",
    "unit",
    "nominal",
    "permitted",
    "availability",
    "feasible",
    "full_coverage_gap",
    "nominal_outcome",
    "standing",
    "origin",
    "refs",
)


def _schedule_numbers(child: dict | None, codes: list, row: dict) -> dict:
    if child is None:
        text = "not computed"
        return {
            "conditionality": "not projected: " + ", ".join(str(c) for c in codes),
            "nominal": text,
            "permitted": text,
            "availability": text,
            "feasible": text,
            "full_coverage_gap": text,
            "nominal_outcome": text,
        }
    value = _signal_value(child)
    claims = {r.get("claim"): r for r in value.get("claims") or [] if isinstance(r, dict)}
    nominal_row = next((r for r in row["claims"] if r["claim"] == "nominal"), None)
    return {
        "conditionality": "conditional" if child.get("conditions") else "unconditional",
        "nominal": rational_text(value.get("nominal")) if "nominal" in claims else "not computed",
        "permitted": interval_text(value.get("permitted")),
        "availability": interval_text(value.get("available")),
        "feasible": interval_text(claims["existence"].get("feasible"))
        if "existence" in claims
        else "not computed",
        "full_coverage_gap": interval_text(claims["full_window"].get("uncovered"))
        if "full_window" in claims
        else "not computed",
        "nominal_outcome": "not computed" if nominal_row is None else nominal_row["effective_outcome"],
    }


# Section findings (Rohan, 2026-11-04): a separate label always shown beside C3 coverage, from admitted
# results only, by a fixed outcome table. Policy failures are conflicts; schedule gaps and unmet binomial
# targets are repair choices (the same split as the clinical metadata labels). No reasoning happens here.
CONFLICT_OUTCOMES = frozenset({"gap", "competing", "violation", "not_established", "inconsistent_domain"})
REPAIR_OUTCOMES = frozenset(
    {"no_feasible_time", "no_permitted_time", "outside_window", "not_collected", "uncovered", "not_satisfied"}
)
CONFLICT_CODES = frozenset({"conflict", "inconsistent", "violated"})
FINDINGS_TEXT = {
    "conflict_found": "Conflict found in the declared checks.",
    "repair_choice_open": "A repair choice is open in the declared checks.",
    "none_found_in_declared_checks": "No conflict or open repair choice found in the declared checks.",
    "not_checked": "Not fully checked (see coverage).",
}


def section_findings(coverage: str, conflicts: int, repairs: int) -> str:
    """One findings label beside coverage; a known problem always outranks coverage wording (pure).

    pre: conflicts >= 0 and repairs >= 0
    post: __return__ in FINDINGS_TEXT
    post: conflicts == 0 or __return__ == "conflict_found"
    post: __return__ != "none_found_in_declared_checks" or coverage == "specified"
    post: __return__ != "none_found_in_declared_checks" or conflicts == repairs == 0
    """
    if conflicts:
        return "conflict_found"
    if repairs:
        return "repair_choice_open"
    if coverage == "specified":
        return "none_found_in_declared_checks"
    return "not_checked"


def _section_detail(consuming: list[dict]) -> list[dict]:
    detail = []
    for check in consuming:
        for row, _ in _claim_rows(check):
            outcome = row.get("outcome")
            if row.get("admission") != "accepted" or row.get("application") == "not_applicable":
                continue
            if outcome in CONFLICT_OUTCOMES or outcome in REPAIR_OUTCOMES:
                detail.append(
                    {
                        "check": check["id"],
                        "claim": row.get("id"),
                        "outcome": outcome,
                        "kind": "conflict" if outcome in CONFLICT_OUTCOMES else "repair_choice",
                        "application": row.get("application"),
                    }
                )
        for _, signal in _plain_signals(check):
            if (signal.get("admission") or {}).get("code") != "accepted":
                continue
            codes = signal_finding_codes(signal)
            if signal.get("calculation_code") in CONFLICT_CODES:
                kind = "conflict"
            elif any("collection_plan_mismatch" in code for code in codes):
                kind = "repair_choice"
            else:
                continue
            detail.append(
                {
                    "check": check["id"],
                    "claim": None,
                    "outcome": signal.get("calculation_code"),
                    "kind": kind,
                    "application": "unconditional",
                }
            )
    return detail


def _section_rows(protocol: dict, check_rows: list[dict], checks: list[dict]) -> list[dict]:
    rows = []
    for sid in SECTION_IDS:
        declared = (protocol.get("sections") or {}).get(sid) or {
            "state": "not_requested",
            "objects": [],
            "basis": [],
        }
        objects = list(declared.get("objects") or [])
        consuming = [c for c in checks if set(c.get("objects") or []) & set(objects)]
        coverage, reasons = section_coverage(
            declared["state"], declared.get("basis") or [], objects, consuming
        )
        detail = _section_detail(consuming) if declared["state"] == "requested" else []
        findings = section_findings(
            coverage,
            sum(1 for d in detail if d["kind"] == "conflict"),
            sum(1 for d in detail if d["kind"] == "repair_choice"),
        )
        rows.append(
            {
                "id": sid,
                "declared": declared["state"],
                "coverage": coverage,
                "findings": findings,
                "findings_text": FINDINGS_TEXT[findings]
                if coverage not in ("not_requested", "not_applicable")
                else f"No checks: section {coverage.replace('_', ' ')}.",
                "findings_detail": detail,
                "reasons": reasons,
                "objects": objects,
                "checks": [c["id"] for c in consuming],
            }
        )
    return rows


def _open_items(check_rows: list[dict], checks: list[dict], sections: list[dict]) -> list[dict]:
    def item(kind: str, check: str | None, claim: str | None, text: str, ref: str) -> dict:
        return {"kind": kind, "check": check, "claim": claim, "text": text, "ref": ref}

    def claim_items(kind: str, wanted) -> list[dict]:
        out = []
        for i, row in enumerate(check_rows):
            refs = row["refs"]
            offset = 0
            for j, child in enumerate(checks[i].get("children") or []):
                for signal in child.get("signals") or []:
                    for _ in signal.get("claim_admission") or []:
                        view_row = row["claims"][offset]
                        offset += 1
                        if wanted(view_row):
                            out.append(
                                item(kind, row["id"], view_row["id"], view_row["wording"], refs[j]["result"])
                            )
        return out

    items = []
    for i, row in enumerate(check_rows):
        for entry in row["unresolved"]:
            items.append(
                item(
                    "unresolved_projection",
                    row["id"],
                    None,
                    f"Projection unresolved: {entry.get('code')}.",
                    _check_ref(i),
                )
            )
    for i, row in enumerate(check_rows):
        declared = row["not_computed"]
        if declared is not None:
            missing = ", ".join(str(m) for m in declared.get("missing") or []) or "none declared"
            items.append(
                item(
                    "not_computed",
                    row["id"],
                    None,
                    f"Not computed: external method; missing inputs: {missing}.",
                    _check_ref(i),
                )
            )
    for i, check in enumerate(checks):
        for j, signal in _plain_signals(check):
            for code in signal_finding_codes(signal):
                items.append(
                    item(
                        "signal_finding",
                        check_rows[i]["id"],
                        None,
                        f"Finding from the {signal.get('kind')} check: {code}.",
                        _child_ref(i, j),
                    )
                )
    items += claim_items("claim_unsettled", lambda r: r["effective_outcome"] in UNSETTLED)
    items += claim_items("claim_conditional", lambda r: r["application"] == "conditional")
    items += claim_items("claim_failure", lambda r: r["effective_outcome"] in FAILURES)
    for section in sections:
        if section["coverage"] in ("open", "not_computed"):
            items.append(
                item(
                    "section",
                    None,
                    None,
                    f"Section {section['id']} is {section['coverage']}.",
                    f"/protocol/sections/{section['id']}",
                )
            )
    return items


def view(result: dict) -> dict:
    """The clinical protocol view of one v2 design_session result.

    pre: isinstance(result, dict)
    post: len(__return__) == 6
    post: len(__return__["sections"]) == 8
    """
    protocol = result.get("protocol") if isinstance(result, dict) else None
    if not isinstance(protocol, dict):
        raise ValueError("view_not_protocol_result")
    checks = list(protocol.get("checks") or [])
    check_rows = [_check_row(i, c) for i, c in enumerate(checks)]
    sections = _section_rows(protocol, check_rows, checks)
    schedule = [
        _schedule_row(protocol, i, c, check_rows[i])
        for i, c in enumerate(checks)
        if c.get("kind") == "schedule"
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "sections": sections,
        "checks": check_rows,
        "schedule": schedule,
        "open_items": _open_items(check_rows, checks, sections),
        "limits_of_claim": list(protocol.get("limits_of_claim") or []) + list(EXTRA_LIMITS),
    }
