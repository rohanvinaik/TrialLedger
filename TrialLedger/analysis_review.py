"""Readable summaries of returned analyses, without an additional reasoning path.

Each summary names its exact retained result. Inclusion in a handoff neither binds
populations nor adopts a comparator result for a new design. Detailed findings and
the complete canonical response remain the authority for every displayed value.
"""

from __future__ import annotations

from copy import deepcopy

from TrialLedger.clinical_display import outcome, proposition

PRIORITY = {"reported_issue": 0, "open_check": 1, "reported_result": 2, "unclassified": 3}


def review_priority_code(code: str, states: list[str]) -> str:
    """Order returned issues before open and completed checks (pure — pinned).

    The order is presentation, never a clinical severity or admissibility score.
    post: __return__ in ('reported_issue', 'open_check', 'reported_result', 'unclassified')
    post: code != 'conflict' or __return__ == 'reported_issue'
    """
    if code in ("conflict", "INCONSISTENT") or any(
        state in ("gap", "conflicting_actions", "violation", "collection_plan_mismatch") for state in states
    ):
        return "reported_issue"
    if (
        code in ("unresolved", "refused", "UNDETERMINED", "OUT_OF_SCOPE", "UNSUPPORTED_QUERY")
        or "unresolved" in states
    ):
        return "open_check"
    if code in ("bounded", "consistent", "complete", "permitted_only", "ENTAILED", "REFUTED"):
        return "reported_result"
    return "unclassified"


def _detail(text: str, address: str, standing: object = None) -> dict:
    return {"text": text, "canonical_ref": address, "standing": standing}


def _interval(row: dict) -> str:
    lower, upper = row.get("lower"), row.get("upper")
    return str(lower) if lower == upper else f"{lower}–{upper}"


def _counts(value: dict, address: str, standing: object) -> list[dict]:
    """Copy returned intervals with their declared universe and total."""
    universe, total = value.get("universe", "Not stated"), value.get("total", "Not stated")
    return [
        _detail(
            f"{row.get('id')}: {_interval(row)}; declared universe: {universe}; total: {total}.",
            f"{address}/counts/{index}",
            standing,
        )
        for index, row in enumerate(value.get("counts", []))
    ]


def _table(value: dict, address: str, standing: object) -> tuple[str, list[dict], list[str]]:
    domain = (value.get("domain") or {}).get("state", "not_reported")
    coverage = (value.get("coverage") or {}).get("state", "not_computed")
    overlaps = [
        (index, row)
        for index, row in enumerate(value.get("overlaps", []))
        if row.get("state") != "disjoint" and not (row.get("state") == "overlap" and row.get("same_action"))
    ]
    prohibitions = value.get("prohibitions", [])
    states = [coverage]
    states.extend(
        "conflicting_actions" if row.get("state") == "overlap" else row.get("state", "")
        for _, row in overlaps
    )
    states.extend(row.get("state", "") for row in prohibitions)
    conflict_count = sum(row.get("state") == "overlap" for _, row in overlaps)
    violation_count = sum(row.get("state") == "violation" for row in prohibitions)
    prohibition_coverage = value.get("prohibition_coverage") or {}
    declared = prohibition_coverage.get("declared", len(prohibitions))
    unresolved = sum(row.get("state") == "unresolved" for row in prohibitions)
    safety = (
        f"{violation_count} violations among {declared} declared action prohibitions; "
        f"{unresolved} prohibition checks unresolved"
        if prohibitions
        else f"{declared} action prohibitions declared; "
        f"checks {prohibition_coverage.get('state', 'unresolved')}"
        if declared
        else "action prohibitions not declared; no safety property checked"
    )
    summary = (
        f"Domain: {domain}; Coverage: {coverage}; {conflict_count} different-action overlaps returned; "
        f"{safety}. "
        "Checks cover only the declared variables and constraints."
    )
    details = [
        _detail(
            "Coverage: " + coverage + "; completeness is conditional on the declared domain.",
            address + "/coverage",
            standing,
        )
    ]
    for index, declared_domain in enumerate(value.get("declared_domains", [])):
        ref = f"{address}/declared_domains/{index}"
        alternatives = [
            proposition(part, f"{ref}/values/{position}")["text"]
            for position, part in enumerate(declared_domain.get("values", []))
        ]
        details.append(
            _detail(
                f"Declared variable {declared_domain.get('id')}: " + "; ".join(alternatives),
                ref,
                standing,
            )
        )
    for index, row in overlaps:
        details.append(
            _detail(
                f"Rows {', '.join(row.get('rows', []))}: {row.get('state')}; "
                f"actions {', '.join(row.get('actions', []))}.",
                f"{address}/overlaps/{index}",
                standing,
            )
        )
    if not declared:
        details.append(
            _detail(
                "No action prohibitions were declared; coverage does not establish clinical safety.",
                address,
                standing,
            )
        )
    elif not prohibitions:
        details.append(
            _detail(
                f"{declared} action prohibitions were declared; their checks remain "
                f"{prohibition_coverage.get('state', 'unresolved')}. An empty result list is not clearance.",
                address + "/prohibition_coverage",
                standing,
            )
        )
    for index, row in enumerate(prohibitions):
        ref = f"{address}/prohibitions/{index}"
        condition = proposition(row.get("when"), ref + "/when")["text"]
        details.append(
            _detail(
                f"Prohibition {row.get('id')}: action {row.get('action')} when {condition}; "
                f"returned state: {row.get('state')}.",
                ref,
                standing,
            )
        )
    for index, row in enumerate(value.get("case_witnesses", [])):
        ref = f"{address}/case_witnesses/{index}"
        profile = proposition(row.get("profile"), ref + "/profile")["text"]
        details.append(
            _detail(
                f"Returned {row.get('kind')} case: {profile}; "
                f"rows: {', '.join(row.get('rows', [])) or 'none'}; "
                f"actions: {', '.join(row.get('actions', [])) or 'none'}.",
                ref,
                standing,
            )
        )
    witness_summary = value.get("witness_summary")
    if isinstance(witness_summary, dict):
        witness_text = (
            "Cases not computed: " + str(witness_summary.get("reason", "Not stated"))
            if witness_summary.get("state") == "not_computed"
            else f"Case enumeration: {witness_summary.get('state')}; "
            f"combinations examined {witness_summary.get('combinations_examined')} "
            f"of {witness_summary.get('combinations_total')}; "
            f"witnesses returned {witness_summary.get('witnesses_returned')}; "
            f"unexamined combinations {witness_summary.get('unexamined_combinations')}."
        )
        details.append(
            _detail(
                witness_text,
                address + "/witness_summary",
                standing,
            )
        )
    details.append(
        _detail(
            f"Termination: {value.get('termination', 'not_computed')}; "
            f"operating characteristics: {value.get('operating_characteristics', 'not_computed')}.",
            address,
            standing,
        )
    )
    return summary, details, states


def _stages(value: dict, address: str, standing: object) -> tuple[str, list[dict], list[str]]:
    transitions = value.get("transitions", [])
    details, states = [], []
    for index, row in enumerate(transitions):
        states.append(row.get("code", ""))
        source, target = row.get("source_stage", {}), row.get("target_stage", {})
        ref = f"{address}/transitions/{index}"
        details.append(
            _detail(
                f"{row.get('id')}: {row.get('source')} "
                f"({source.get('population')}; {source.get('total')} {source.get('unit')}; "
                f"{source.get('time')}) → {row.get('target')} "
                f"({target.get('population')}; {target.get('total')} {target.get('unit')}; "
                f"{target.get('time')}): {row.get('code')}. "
                "Count compatibility is conditional on the supplied relation, not individual membership. "
                f"Gate reference: {row.get('declaration', {}).get('gate_ref')}; "
                f"basis: {'; '.join(row.get('basis', [])) or 'Not stated'}.",
                ref,
                row.get("status"),
            )
        )
        calculation = row.get("population_result") or {}
        if isinstance(calculation.get("value"), dict):
            details.extend(_counts(calculation["value"], ref + "/population_result/value", row.get("status")))
    return (
        f"{len(transitions)} declared stage transitions checked. "
        "Population counts, assumptions and permitted transitions remain separate.",
        details,
        states,
    )


def _estimand(value: dict, address: str, standing: object) -> tuple[str, list[dict], list[str]]:
    rows = value.get("requirements", [])
    details, states = [], []
    for index, row in enumerate(rows):
        states.extend([row.get("collection_alignment", ""), row.get("actual_input", "")])
        declaration = row.get("declaration", {})
        details.append(
            _detail(
                f"{row.get('id')}: relevance {row.get('relevance')}; "
                f"collection plan {row.get('collection_alignment')} "
                f"(standing {row.get('collection_status')}); actual input {row.get('actual_input')} "
                f"(standing {row.get('actual_status')}). "
                f"Variable: {declaration.get('variable')}; window: {declaration.get('window')}.",
                f"{address}/requirements/{index}",
                row.get("relevance_status"),
            )
        )
    mismatches = sum(row.get("collection_alignment") == "collection_plan_mismatch" for row in rows)
    return (
        f"Definition: {value.get('definition_state')}; {mismatches} collection-plan mismatches "
        f"among {len(rows)} declared requirements. Actual input availability is checked separately; "
        "estimation is not computed.",
        details,
        states,
    )


def _dependencies(value: dict, address: str, standing: object) -> tuple[str, list[dict], list[str]]:
    rows = value.get("rules", [])
    details = [
        _detail(
            f"{row.get('id')} (version {row.get('version')}): {row.get('state')}; "
            f"output {row.get('output', {}).get('id')} "
            f"({row.get('output', {}).get('mode')}); "
            f"unavailable or unestablished inputs: {', '.join(row.get('missing', [])) or 'none reported'}. "
            "An unavailable or unestablished listed input need not block an available alternative.",
            f"{address}/rules/{index}",
            standing,
        )
        for index, row in enumerate(rows)
    ]
    return (
        f"{len(rows)} adopted dependency rules checked; "
        f"{sum(row.get('state') == 'blocked' for row in rows)} blocked and "
        f"{sum(row.get('state') == 'unresolved' for row in rows)} unresolved. "
        "Derived availability remains in its declared observed or modelled mode.",
        details,
        [row.get("state", "") for row in rows],
    )


def _signal(row: dict, address: str, owner: str) -> dict:
    raw_value = row.get("value")
    value = raw_value if isinstance(raw_value, dict) else {}
    kind, standing = row.get("kind", "Not stated"), row.get("status")
    value_ref = address + "/value"
    if kind == "decision_table":
        summary, details, states = _table(value, value_ref, standing)
    elif kind == "stages":
        summary, details, states = _stages(value, value_ref, standing)
    elif kind == "estimand":
        summary, details, states = _estimand(value, value_ref, standing)
    elif kind == "dependencies":
        summary, details, states = _dependencies(value, value_ref, standing)
    elif "counts" in value:
        details, states = _counts(value, value_ref, standing), []
        summary = "Returned bounds: " + "; ".join(
            f"{count.get('id')} {_interval(count)}" for count in value["counts"]
        )
        summary += f". Declared universe: {value.get('universe')}; total: {value.get('total')}."
    else:
        details, states = [], []
        summary = "Returned calculation retained; open the exact result for this signal's typed details."
    applied, calculated = row.get("code", ""), row.get("calculation_code", "")
    return {
        "analysis": owner + " / " + str(row.get("id")),
        "kind": kind,
        "code": applied,
        "calculation_code": calculated,
        "priority": review_priority_code(calculated, states),
        "standing": standing,
        "scope": value.get("scope", value.get("universe", value.get("study", "Not stated"))),
        "version": value.get("version", value.get("snapshot", "Not stated")),
        "summary": summary,
        "details": details,
        "blockers": deepcopy(row.get("blockers", [])),
        "basis": deepcopy(row.get("basis", [])),
        "rule": row.get("rule"),
        "admission": deepcopy(row.get("admission")),
        "canonical_ref": address,
    }


def _definition(row: dict, address: str, owner: str) -> dict:
    declaration = row.get("declaration", {})
    details = []
    for side in ("left", "right"):
        binding = declaration.get(side, {})
        ref = f"{address}/declaration/{side}"
        body = proposition(binding.get("body"), ref + "/body")["text"]
        details.append(
            _detail(
                f"{side.capitalize()} meaning: {body}; bound analysis: {binding.get('analysis')}; "
                f"bound address: {binding.get('address')}; resolution: {binding.get('resolution')}; "
                f"basis: {'; '.join(binding.get('basis', [])) or 'Not stated'}.",
                ref,
                binding.get("status"),
            )
        )
    code = row.get("code", "")
    return {
        "analysis": owner + " / definition " + str(row.get("id")),
        "kind": "definition_check",
        "code": code,
        "calculation_code": code,
        "priority": review_priority_code(code, []),
        "standing": row.get("status"),
        "scope": deepcopy(row.get("target", "Not stated")),
        "version": "Open exact declarations and warrants",
        "summary": f"Declared relationship: {row.get('relation')}; returned result: {code}. "
        "A conflict is relative to this explicit relationship, not proof that differently purposed "
        "thresholds must match.",
        "details": details,
        "blockers": deepcopy(row.get("blockers", [])),
        "basis": deepcopy(row.get("basis", [])),
        "rule": "Declared definition relationship; open exact checks for rule versions",
        "admission": None,
        "canonical_ref": address,
    }


def _logical(result: dict, address: str, owner: str, context: dict) -> dict:
    decision = result["decision"]
    code = decision.get("result", "")
    return {
        "analysis": owner,
        "kind": "entailment",
        "code": code,
        "calculation_code": code,
        "priority": review_priority_code(code, []),
        "standing": decision.get("status"),
        "scope": deepcopy(context) if context else "No cohort, arm or phase context supplied",
        "version": "Open exact premises and rule versions",
        "summary": outcome(code),
        "details": [
            _detail(
                "Represented question: "
                + proposition(decision.get("query"), address + "/decision/query")["text"],
                address + "/decision",
                decision.get("status"),
            )
        ],
        "blockers": deepcopy(decision.get("blockers", [])),
        "basis": deepcopy(decision.get("proof", [])),
        "rule": "Open exact deciding premises and their warrants",
        "admission": None,
        "canonical_ref": address + "/decision",
    }


def _envelope(response: dict, address: str, owner: str, context: dict | None = None) -> list[dict]:
    operation = response.get("operation", "Not stated")
    result = response.get("result")
    if operation == "design_session" and isinstance(result, dict):
        represented = {
            option.get("analysis")
            for decision in result.get("decisions", [])
            for option in decision.get("alternatives", [])
        }
        analyses = [
            summary
            for index, row in enumerate(result.get("analyses", []))
            if row.get("id") not in represented
            for summary in _envelope(
                row.get("result", {}),
                f"{address}/result/analyses/{index}/result",
                owner + " / " + str(row.get("id")),
                row.get("request", {}).get("context", {}),
            )
        ]
        return analyses + [
            _definition(row, f"{address}/result/definition_checks/{index}", owner)
            for index, row in enumerate(result.get("definition_checks", []))
        ]
    if operation == "signals" and isinstance(result, dict):
        return [
            _signal(row, f"{address}/result/signals/{index}", owner)
            for index, row in enumerate(result.get("signals", []))
        ]
    if operation == "entailment" and isinstance(result, dict) and isinstance(result.get("decision"), dict):
        return [_logical(result, address + "/result", owner, context or {})]
    return [
        {
            "analysis": owner,
            "kind": operation,
            "code": response.get("code", "Not stated"),
            "calculation_code": "Not summarized",
            "priority": review_priority_code(response.get("code", ""), []),
            "standing": None,
            "scope": "Open the exact analysis; inclusion does not bind its population to a decision.",
            "version": "Not stated",
            "summary": "Separate analysis retained. Its complete typed findings remain in Findings.",
            "details": [],
            "blockers": deepcopy(response.get("problems", [])),
            "basis": [],
            "rule": None,
            "admission": None,
            "canonical_ref": address,
        }
    ]


def summaries(payloads: list[tuple[str, dict]]) -> list[dict]:
    """Project each included or managed analysis once, preserving exact result ownership."""
    rows = []
    for index, (identity, payload) in enumerate(payloads):
        response = payload["response"]
        owner = "Main" if index == 0 else f"Included {index}"
        for row in _envelope(response, "/response", owner, payload.get("request", {}).get("context", {})):
            row["artifact"] = identity
            rows.append(row)
    return sorted(rows, key=lambda row: PRIORITY[row["priority"]])
