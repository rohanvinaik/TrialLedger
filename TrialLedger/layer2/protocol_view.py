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
WITNESSED_OUTCOMES = frozenset({"gap", "competing", "violation", "not_established"})
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
# Plain words for the admission code of a refused claim. The exact code stays in the Admission column.
ADMISSION_WORDS = {
    "proposed_refused": "the deciding premise is still a proposal",
    "missing_support": "a premise this claim needs is not declared",
    "binding_unresolved": "a premise this claim needs is not fully resolved",
    "application_blocked": "the condition for applying this claim is blocked",
}
# Kind of finding for one claim or finding, from the view's own conflict/repair classification.
KIND_WORDS = {
    "conflict": "Conflict",
    "repair_choice": "Repair choice",
    "not_computed": "Not computed",
    "not_determined": "Not determined",
    "not_applied": "Not applied",
    "conditional": "Conditional",
    "not_applicable": "Not applicable",
    "finding": "Finding",
    "no_finding": "No finding",
}
KIND_ORDER = tuple(KIND_WORDS)
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


def literal_text(literal: Any) -> str:
    """One retained valuation literal in plain words: its key, polarity and (for quantities) value."""
    if not isinstance(literal, dict):
        return "an undeclared value"
    key = _get(literal, "predicate", "key")
    name = key if isinstance(key, str) and key else "a declared variable"
    value = literal.get("value") if isinstance(literal.get("value"), dict) else {}
    if value.get("kind") == "boolean":
        return name if literal.get("polarity") != "negative" else f"not {name}"
    number = value.get("number")
    if isinstance(number, int | float) and not isinstance(number, bool):
        unit = value.get("unit")
        text = f"{name} {value.get('comparison')} {number:g}" + (f" {unit}" if unit else "")
        return text if literal.get("polarity") != "negative" else f"not ({text})"
    return name


def witness_text(detail: dict) -> str:
    """A concise sentence for the first retained bounded witness trace; empty when none is retained.

    The trace is read as returned (state, valuation, transition, actions); nothing is recomputed.
    """
    witnesses = detail.get("witnesses")
    first = witnesses[0] if isinstance(witnesses, list) and witnesses else None
    trace = first.get("trace") if isinstance(first, dict) else None
    last = trace[-1] if isinstance(trace, list) and trace and isinstance(trace[-1], dict) else None
    if last is None:
        return ""
    valuation = last.get("valuation") if isinstance(last.get("valuation"), dict) else {}
    values = ", ".join(literal_text(valuation[key]) for key in sorted(valuation))
    where = f"in state {last.get('state')}" + (f" with {values}" if values else "")
    transition, actions = last.get("transition"), last.get("actions")
    if transition is None:
        outcome = "no declared rule applies"
    else:
        chosen = ", ".join(str(item) for item in actions) if isinstance(actions, list) and actions else "none"
        outcome = f"transition {transition} selects {chosen}"
    steps = f" after {len(trace) - 1} earlier step(s)" if len(trace) > 1 else ""
    return f"Example from the retained bounded trace: {where}{steps}, {outcome}."


def witness_wording(row: dict, child: dict) -> str | None:
    """The bounded witness sentence for an applied policy finding, else None (claim wording unchanged)."""
    if row.get("effective_outcome") not in WITNESSED_OUTCOMES or row.get("application") == "not_applicable":
        return None
    text = witness_text(_value_claim(child, row.get("id")))
    if not text:
        return None
    return CONDITIONAL_PREFIX + text if row.get("application") == "conditional" else text


def _template(row: dict, child: dict) -> str:
    claim, effective = row.get("claim"), row.get("effective_outcome")
    if effective == "unresolved" and row.get("admission") == "undetermined":
        # Not a refusal: the operator could not decide because a declared input is missing.
        return "Not determined: an input this claim needs is not declared."
    if effective == "unresolved":
        admission = str(row.get("admission"))
        return f"Not applied: {ADMISSION_WORDS.get(admission, 'the deciding support is ' + admission)}."
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
                        "witness_wording": witness_wording(row, child),
                        "kind_of_finding": claim_kind(row),
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
                "kind_of_finding": signal_kind(sig),
                "ref": _child_ref(index, j),
            }
            for j, sig in _plain_signals(check)
        ],
        "unresolved": copy.deepcopy(check.get("unresolved") or []),
        "not_computed": copy.deepcopy(check.get("not_computed")),
        "not_computed_items": not_computed_items(check),
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
    return "not stated (open)" if value is None else str(value)


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


def window_texts(value: dict) -> dict:
    """Permitted, availability, feasible and gap texts of one schedule_coverage `value` (shared builder)."""
    claims = {r.get("claim"): r for r in value.get("claims") or [] if isinstance(r, dict)}
    return {
        "permitted": interval_text(value.get("permitted")),
        "availability": interval_text(value.get("available")),
        "feasible": interval_text(claims["existence"].get("feasible"))
        if "existence" in claims
        else "not computed",
        "full_coverage_gap": interval_text(claims["full_window"].get("uncovered"))
        if "full_window" in claims
        else "not computed",
    }


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
        **window_texts(value),
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


# Plain words for the unresolved-projection and operator-finding codes. The exact code always stays beside.
UNRESOLVED_WORDS = {
    "projection_scope_mismatch": "the declared objects are for different scopes (for example collection and "
    "assessment), so nothing was computed",
    "projection_scope_too_long": "the declared scope is too long to project, so nothing was computed",
    "projection_collection_plan_conflict": "the declared collection plans conflict, so nothing was computed",
    "projection_binding_shape": "a declared object does not have the shape this check reads, so nothing was "
    "computed",
    "projection_slice_5": "this kind of check is not computed in this version",
    "adoption_stale_version": "an object was adopted at an older version than the one now declared",
    "session_work_limit": "not run: the session's configured work limit was reached before this check",
}
FINDING_CODE_WORDS = {
    "schedule_no_permitted_time": "the permitted window is empty",
    "schedule_no_feasible_time": "no permitted assessment time falls within planned collection",
    "schedule_outside_window": "the nominal target is outside the permitted window",
    "schedule_not_collected": "the nominal target is not within planned collection",
    "schedule_uncovered": "planned collection leaves part of the permitted window uncovered",
    "schedule_unresolved": "the schedule could not be settled from the declared inputs",
    "policy_gap": "a reachable declared situation has no rule",
    "policy_competing": "a reachable declared situation enables more than one rule",
    "policy_violation": "a declared prohibition is violated in a reachable declared situation",
    "policy_not_established": "the declared property is not established",
    "policy_transition_target_infeasible": "a declared transition target is not reachable",
    "policy_inconsistent_domain": "the declared domain is inconsistent",
    "policy_work_limit": "not computed within the declared work limit",
    "binomial_claim_not_satisfied": "a declared binomial design target is not met",
    "binomial_assumption_missing": "a declared assumption the method needs is missing",
    "binomial_unsupported_method": "the declared method is not supported",
    "binomial_bit_limit": "not computed within the declared size limit",
    "collection_plan_mismatch": "the collection plan does not meet a declared requirement",
}


def code_words(code: object) -> str:
    """Plain words for one operator finding code such as `schedule_uncovered:window`; the code stays beside.

    pre: True
    post: isinstance(__return__, str)
    post: str(code) in __return__
    """
    text = str(code)
    head, _, tail = text.partition(":")
    words = FINDING_CODE_WORDS.get(head) or UNRESOLVED_WORDS.get(head)
    if words is None:
        words = head.replace("_", " ")
    return f"{words} (claim {tail}; {text})" if tail and head in FINDING_CODE_WORDS else f"{words} ({text})"


def unresolved_words(entry: dict) -> str:
    """Plain words for one unresolved-projection entry; its objects and exact code stay in the text."""
    code = str(entry.get("code"))
    words = UNRESOLVED_WORDS.get(code, code.replace("_", " "))
    objects = ", ".join(str(o) for o in entry.get("objects") or [])
    if code == "session_work_limit":
        configured = entry.get("configured") or {}
        words += (
            f" ({entry.get('limit')}; this check reserves {entry.get('reserved')} after "
            f"{entry.get('already_reserved')} already reserved, against max_solver_work "
            f"{configured.get('max_solver_work')} and max_analyses {configured.get('max_analyses')})"
        )
    return f"{words}{' (objects: ' + objects + ')' if objects else ''} [{code}]"


def not_computed_items(check: dict) -> list[dict]:
    """One entry per reason a check was not computed: unresolved projection or external method (pure)."""
    out = [
        {
            "code": str(entry.get("code")),
            "text": f"No finding: {unresolved_words(entry)}. Resolve this before relying on the check.",
        }
        for entry in check.get("unresolved") or []
    ]
    declared = check.get("not_computed")
    if declared is not None:
        missing = ", ".join(str(m) for m in declared.get("missing") or []) or "none declared"
        out.append(
            {
                "code": "not_computed",
                "text": "No finding: computed outside this tool (external method); "
                f"missing inputs: {missing}.",
            }
        )
    return out


def claim_kind(row: dict) -> str:
    """Kind of finding for one claim row, from the same conflict/repair split the sections use (pure).

    pre: isinstance(row, dict)
    post: __return__ in KIND_WORDS
    """
    if row.get("application") == "not_applicable":
        return "not_applicable"
    if row.get("effective_outcome") == "not_executed":
        return "not_computed"
    if row.get("admission") != "accepted":
        return "not_determined" if row.get("admission") == "undetermined" else "not_applied"
    outcome = row.get("outcome")
    if outcome in CONFLICT_OUTCOMES:
        return "conflict"
    if outcome in REPAIR_OUTCOMES:
        return "repair_choice"
    if row.get("application") == "conditional":
        return "conditional"
    if row.get("effective_outcome") in UNSETTLED:
        return "not_applied"
    return "finding" if row.get("effective_outcome") in FAILURES else "no_finding"


def signal_kind(signal: dict) -> str:
    """Kind of finding for one operator finding with no claim rows (pure)."""
    if (signal.get("admission") or {}).get("code") != "accepted":
        return "not_applied"
    if signal.get("calculation_code") in CONFLICT_CODES:
        return "conflict"
    if any("collection_plan_mismatch" in code for code in signal_finding_codes(signal)):
        return "repair_choice"
    return "finding"


def reason_words(reason: str, consuming: list[dict], coverage: str) -> str:
    """Plain words for one section reason; `consuming` are view check rows. The code keeps its own column."""
    if coverage == "not_applicable":
        return f"Declared not applicable by the caller (caller's basis: {reason})"
    kind, _, rest = reason.partition(":")
    if reason == "no_objects_declared":
        return "The section is requested but no objects are declared for it"
    if reason == "no_check_declared":
        return "Objects are declared but no check consumes them"
    if kind == "not_computed":
        return f"Check {rest} was not computed (see its Protocol findings row)"
    check_id, _, tail = rest.partition(":")
    if kind == "unresolved":
        return f"Check {check_id}: {UNRESOLVED_WORDS.get(tail, tail.replace('_', ' '))}"
    if kind == "signal":
        return f"Check {check_id}: {code_words(tail)}"
    if kind == "claim_unresolved":
        for check in consuming:
            for row in check["claims"]:
                if check["id"] == check_id and row.get("id") == tail:
                    if row.get("admission") == "undetermined":
                        return (
                            f"Claim {tail} of check {check_id} is not determined: a declared input is missing"
                        )
                    word = ADMISSION_WORDS.get(str(row.get("admission")), "its support is not accepted")
                    return f"Claim {tail} of check {check_id} was not applied: {word}"
        return f"Claim {tail} of check {check_id} is not settled"
    return reason.replace("_", " ")


NOMINAL_WORDS = {
    "satisfied": "is inside the permitted window and within planned collection",
    "outside_window": "is outside the permitted window",
    "not_collected": "is inside the permitted window but outside planned collection",
    "unresolved": "has no applied finding (its deciding premise is a proposal or an input is missing)",
    "not_executed": "was not computed within the declared work limit",
}
NO_UNIT_TEXT = ("unknown", "not computed", "none", "not stated")


def interval_phrase(text: object, unit: object, anchor: object) -> str:
    """An interval or number with its unit and anchor, e.g. `[77, 91] days from randomization` (pure)."""
    shown = str(text)
    if shown in NO_UNIT_TEXT or shown.startswith("not "):
        return shown
    plural = "" if not unit else (f" {unit}s" if not str(unit).endswith("s") else f" {unit}")
    return f"{shown}{plural}" + (f" from {anchor}" if anchor else "")


def nominal_phrase(outcome: object, nominal: object, unit: object, anchor: object) -> str:
    """The nominal outcome in words with the raw code kept beside; no outcome is invented (pure)."""
    if outcome == "unknown_target":
        return "No nominal target is declared (unknown_target)"
    if str(outcome) in ("not computed", "None"):
        return "not computed"
    words = NOMINAL_WORDS.get(str(outcome), f"has outcome {outcome}")
    return f"Target {interval_phrase(nominal, unit, anchor)} {words} ({outcome})"


COMPATIBILITY_WORDS = {
    "compatible_under_declared_checks": "No conflict or repair choice found under the declared checks",
    "repair_choice_open_under_declared_checks": "A repair choice is open under the declared checks",
    "incompatible_under_declared_checks": "A conflict is found under the declared checks",
    "undetermined": "Not determined: a declared check is unsettled or was not computed",
}
DISPOSITION_WORDS = {
    "blocker": "The option you selected has a conflict under the declared checks",
    "repair_choice": "A repair choice is open: the option you selected, or every declared option, leaves a "
    "gap to repair",
    "design_choice": "Two or more declared options fit; choosing among them is your design decision",
    "evidence_question": "Not settled: a declared check needs more evidence or inputs",
    "settled_within_declared_alternatives": "Settled among the declared alternatives only",
    "no_compatible_alternative": "No declared option fits under the declared checks",
}


def application_phrase(frame: str, compatibility: str, application: str, assumptions: list[str]) -> str:
    """Why an alternative is or is not applied to the draft, in plain words (pure).

    pre: application in ("admitted", "withheld")
    post: isinstance(__return__, str)
    """
    if application == "admitted":
        return "Applied to the draft: it is the draft as written and no conflict or repair choice is found"
    if frame == "hypothetical":
        objects = ", ".join(assumptions) or "none named"
        return (
            "Not applied to the draft: a hypothetical alternative that assumes these objects are replaced: "
            f"{objects}"
        )
    return (
        "Not applied as a settled design: the draft as written has no clean result "
        f"({COMPATIBILITY_WORDS.get(compatibility, compatibility).lower()})"
    )


OUTCOME_WORDS = {
    "gap": "a reachable declared situation has no rule",
    "competing": "a reachable declared situation enables more than one rule",
    "violation": "a declared prohibition is violated",
    "not_established": "a declared property is not established",
    "inconsistent_domain": "the declared domain is inconsistent",
    "no_feasible_time": "no permitted assessment time falls within planned collection",
    "no_permitted_time": "the permitted window is empty",
    "outside_window": "the nominal target is outside the permitted window",
    "not_collected": "the nominal target is outside planned collection",
    "uncovered": "planned collection leaves part of the permitted window uncovered",
    "not_satisfied": "a declared bound is not met",
    "satisfied": "holds under the declared inputs",
    "unresolved": "no applied finding",
    "not_executed": "not computed within the work limit",
    "violated": "a declared check is violated",
    "conflict": "a conflict is found",
}
FIELD_WORDS = {
    "effective_outcome": "outcome",
    "application": "application",
    "admission": "admission",
    "finding_status": "standing",
    "application_status": "applicability standing",
    "code": "result code",
    "calculation_code": "calculated code",
    "blockers": "blockers",
}
AXIS_WORDS = {
    "verdict": "the computed outcome changed",
    "requirements": "remaining requirements changed",
    "support": "the deciding support changed",
    "origin": "the attributed origin changed",
    "scope_model": "the scope or an object version changed",
    "wording": "the caller wording changed",
    "input": "inputs changed; outcome, support and origin are the same",
}


def outcome_words(code: object) -> str:
    """Plain words for an outcome code, with the code kept beside it (pure)."""
    words = OUTCOME_WORDS.get(str(code))
    return f"{words} ({code})" if words else str(code)


def _changed_value(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, list | tuple):
        return "; ".join(str(v) for v in value) or "none"
    return outcome_words(value)


def change_lines(changes: list[dict]) -> tuple[list[str], list[str]]:
    """Before and after lines for the per-claim changes of one retained answer_diff row (pure)."""
    before, after = [], []
    for change in changes:
        if not isinstance(change, dict):
            continue
        subject = f"Claim {change['claim']}" if "claim" in change else f"Check finding {change.get('signal')}"
        field = FIELD_WORDS.get(str(change.get("field")), str(change.get("field")))
        before.append(f"{subject}, {field}: {_changed_value(change.get('before'))}")
        after.append(f"{subject}, {field}: {_changed_value(change.get('after'))}")
    return before, after


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


ADOPTION_CODES = ("not_adopted", "stale_version", "adopted_known", "adopted_interpolated", "adopted_proposed")


ADOPTION_WORDS = {
    "not_adopted": "No adoption record: nothing was declared as adopting this object",
    "stale_version": "Adopted at an older version than the one now declared; re-adoption is needed",
    "adopted_known": "Adopted as written (caller-attributed; known only if its premises hold)",
    "adopted_interpolated": "Adopted as written on an overridable working assumption (caller-attributed)",
    "adopted_proposed": "Adopted as a proposal only (caller-attributed; not yet accepted)",
}


def adoption_code(supported: bool, stale: bool, standing: str | None) -> str:
    """How one protocol object stands as adopted, from its declared records only (pure).

    post: __return__ in ADOPTION_CODES
    post: supported or __return__ == "not_adopted"
    """
    if not supported:
        return "not_adopted"
    if stale:
        return "stale_version"
    if standing in ("known", "interpolated", "proposed"):
        return "adopted_" + standing
    return "adopted_proposed"


def _adoption_rows(protocol: dict, result: dict, checks: list[dict]) -> list[dict]:
    """Who adopted each protocol object, at which version, with which standing (explicit records only)."""
    premises = {p.get("id"): p for p in result.get("effective_premises") or [] if isinstance(p, dict)}
    stale = {
        entry["objects"][0]: list(entry.get("premises") or [])
        for check in checks
        for entry in check.get("unresolved") or []
        if entry.get("code") == "adoption_stale_version" and entry.get("objects")
    }
    rows = []
    for obj in protocol.get("objects") or []:
        records = [premises.get(pid) or {"id": pid} for pid in obj.get("support") or []]
        standing = [(r.get("standing") or {}).get("status") for r in records]
        weakest = next((s for s in ("proposed", "interpolated", "known") if s in standing), None)
        rows.append(
            {
                "object": obj["id"],
                "kind": obj.get("kind"),
                "version": obj.get("version"),
                "adopted_by": [r["id"] for r in records],
                "adoption_origins": [
                    f"{(r.get('origin') or {}).get('kind')}: {(r.get('origin') or {}).get('ref')}"
                    for r in records
                ],
                "adoption": adoption_code(bool(records), obj["id"] in stale, weakest),
                "object_standing": (obj.get("standing") or {}).get("status"),
            }
        )
    return rows


def view(result: dict) -> dict:
    """The clinical protocol view of one v2 design_session result.

    pre: isinstance(result, dict)
    post: len(__return__) == 7
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
        "adoption": _adoption_rows(protocol, result, checks),
        "limits_of_claim": list(protocol.get("limits_of_claim") or []) + list(EXTRA_LIMITS),
    }
