"""Replay explicit clinical design questions through existing reasoning owners.

This module keeps immutable ledgers and an auditable decision list. It neither reads clinical meaning
from text nor turns a historical comparator's protocol into a new-trial requirement.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from copy import deepcopy
from itertools import combinations
from typing import Any, cast

from TrialLedger.layer2 import admission, entail, signals, solver_work, source_evidence
from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import session_projections as projections
from TrialLedger.layer2 import session_state as state

ALTERNATIVE_CODES = frozenset(
    {
        "target_mismatch",
        "conflict",
        "computation_task",
        "translation_question",
        "infeasible",
        "feasible",
        "evidence_question",
    }
)

SESSION_WORK_CODES = (
    "within_budget",
    "resource_bound:session_solver_work",
    "resource_bound:session_analyses",
)

REVISION_INPUT_CODES = (
    "ready",
    "invalid_previous_response",
    "previous_result_session_mismatch",
    "result_mismatch",
    "invalid_session_revision_identity",
    "parent_mismatch",
)


class SessionBudgetError(ValueError):
    """A named resource refusal with the numeric reservation retained for public delivery."""

    def __init__(self, code: str, diagnostics: dict) -> None:
        super().__init__(code)
        self.diagnostics = deepcopy(diagnostics)


def revision_input_code(
    complete: bool,
    session_matches: bool,
    result_matches: bool,
    same_id: bool,
    new_revision: bool,
    parent_matches: bool,
) -> str:
    """Name the first failed public revision integrity check (pure).

    post: __return__ in REVISION_INPUT_CODES
    post: __return__ != 'ready' or (complete and session_matches and result_matches)
    post: __return__ != 'ready' or (same_id and new_revision and parent_matches)
    """
    if not complete:
        return "invalid_previous_response"
    if not session_matches:
        return "previous_result_session_mismatch"
    if not result_matches:
        return "result_mismatch"
    if not same_id or not new_revision:
        return "invalid_session_revision_identity"
    if not parent_matches:
        return "parent_mismatch"
    return "ready"


def prepare_revision(previous_request: object, previous_response: object, next_session: object) -> dict:
    """Prepare a public revision without interpreting or accepting any clinical field.

    The public result fingerprint covers exactly ``response['result']``. The caller's
    retained artifact establishes which prior bytes were supplied; this constructor
    checks their documentary consistency and never certifies source truth or consent.
    """
    # Only the prior session is consumed here. Its already-retained previous
    # replay is not another query and must not be charged to this copy's node cap.
    prior = state.obj(previous_request, {"operation", "session", "previous"}, "previous_request")
    prior_request = source_evidence._json_copy(
        {
            "operation": prior["operation"],
            "session": prior["session"],
            "previous": None,
        },
        "previous_request",
    )
    if prior_request["operation"] != "design_session":
        raise ValueError("unsupported_session_operation")
    if type(previous_response) is not dict:
        raise ValueError("invalid_previous_response")
    # Replay consumes the logical result, never presentation views or prior diff copies.
    # The artifact owner independently verifies and retains the complete envelope.
    prior_response = source_evidence._json_copy(
        {
            key: value
            for key, value in previous_response.items()
            if key in ("code", "operation", "result", "result_digest")
        },
        "previous_response",
    )
    old = state.prepare(prior_request["session"])
    following = source_evidence._json_copy(next_session, "next_session")
    if type(following) is not dict:
        raise ValueError("invalid_fields:session")
    supplied_parent = following.get("parent_digest")
    following.setdefault("parent_digest", None)
    next_prepared = state.prepare(following)
    result = prior_response.get("result")
    complete = (
        prior_response.get("code") == "complete"
        and prior_response.get("operation") == "design_session"
        and type(result) is dict
    )
    code = revision_input_code(
        complete,
        complete
        and result.get("session_digest") == old["digest"]
        and result.get("session_id") == old["session"]["id"]
        and result.get("revision") == old["session"]["revision"]
        and source_evidence.exact_json_equal(result.get("target"), old["session"]["target"]),
        complete
        and type(prior_response.get("result_digest")) is str
        and prior_response["result_digest"] == state.digest(result),
        next_prepared["session"]["id"] == old["session"]["id"],
        next_prepared["session"]["revision"] != old["session"]["revision"],
        supplied_parent is None or supplied_parent == old["digest"],
    )
    if code != "ready":
        raise ValueError(code)
    next_prepared["session"]["parent_digest"] = old["digest"]
    return {
        "operation": "design_session",
        "session": next_prepared["session"],
        "previous": {
            "session": old["session"],
            "result": result,
            "expected_result_digest": prior_response["result_digest"],
        },
    }


def alternative_code(result: str, blockers: list[str], accepted: bool, target_matches: bool) -> str:
    """Classify only a completed ordinary entailment's exact declared alternative (pure).

    post: __return__ in ALTERNATIVE_CODES
    post: target_matches or __return__ == 'target_mismatch'
    post: __return__ != 'feasible' or accepted
    post: __return__ != 'feasible' or result in ('ENTAILED', 'UNDETERMINED')
    """
    if not target_matches:
        return "target_mismatch"
    if result == "INCONSISTENT":
        return "conflict"
    if "resource_bound" in blockers:
        return "computation_task"
    if result == "UNSUPPORTED_QUERY" or any(
        v.startswith(("proposed_refused", "unresolved_", "opaque", "unspecified_boundary", "conflicting:"))
        for v in blockers
    ):
        return "translation_question"
    if result == "REFUTED" and accepted:
        return "infeasible"
    if result == "ENTAILED" and accepted and not blockers:
        return "feasible"
    if result == "UNDETERMINED" and accepted and blockers == ["undecided_by_constraints"]:
        return "feasible"
    return "evidence_question"


def _question(kind: str, alternatives: list[dict], selected: dict | None, distinguished: bool) -> str:
    codes = [v["code"] for v in alternatives]
    if "conflict" in codes or (
        selected is not None
        and next(v for v in alternatives if v["id"] == selected["alternative"])["code"] == "infeasible"
    ):
        return "blocker"
    if "translation_question" in codes or "target_mismatch" in codes:
        return "translation_question"
    if "computation_task" in codes:
        return "computation_task"
    if selected is not None:
        chosen = next(v for v in alternatives if v["id"] == selected["alternative"])
        return "chosen_by_person" if chosen["code"] == "feasible" else "chosen_with_open_checks"
    if codes and codes.count("infeasible") == len(codes):
        return "blocker"
    if codes.count("feasible") == 1 and codes.count("infeasible") == len(codes) - 1:
        return "settled_within_declared_alternatives"
    if kind == "historical":
        return "evidence_question"
    open_options = [option for option in alternatives if option["code"] not in ("feasible", "infeasible")]
    if open_options and all(
        option["code"] == "evidence_question"
        and (option.get("warrant") or {}).get("blockers") == ["no_constraint_mentions_query"]
        for option in open_options
    ):
        return "unrepresented_design_question"
    if codes.count("feasible") >= 2:
        return "design_choice" if distinguished else "options_not_distinguished"
    return "evidence_question"


def session_work_code(
    analyses: int, solver_work_reserved: int, max_analyses: int, max_solver_work: int
) -> str:
    """Classify actual local reasoning work; source JSON size is diagnostic only.

    pre: analyses >= 0
    pre: solver_work_reserved >= 0
    pre: max_analyses > 0
    pre: max_solver_work > 0
    post: __return__ in SESSION_WORK_CODES
    """
    if solver_work_reserved > max_solver_work:
        return "resource_bound:session_solver_work"
    if analyses > max_analyses:
        return "resource_bound:session_analyses"
    return "within_budget"


def _child(request: dict, execute: Callable[[object], dict], budget: dict, limits: dict) -> dict:
    """One common budget owner for named analyses and pairwise distinction checks."""
    budget["expanded_items"] += _nodes(request)
    reserved = _reserve(request)
    budget["solver_work_reserved"] += reserved
    budget["analyses"] += 1
    code = session_work_code(
        budget["analyses"],
        budget["solver_work_reserved"],
        limits["max_analyses"],
        limits["max_solver_work"],
    )
    if code != "within_budget":
        raise SessionBudgetError(
            code,
            {
                "code": code,
                "operation": request["operation"],
                "budget": deepcopy(budget),
                "limits": {key: limits[key] for key in ("max_analyses", "max_solver_work")},
                "request_reservation": reserved,
            },
        )
    result = json.loads(state.canonical(execute(deepcopy(request))))
    if type(result) is not dict or result.get("code") not in ("complete", "refused"):
        raise ValueError("invalid_child_result")
    return {
        "request": deepcopy(request),
        "result": result,
        "request_digest": state.digest(request),
        "result_digest": state.digest(result),
    }


def _distinctions(
    alternatives: list[dict],
    analyses: dict,
    values: dict,
    execute: Callable[[object], dict],
    budget: dict,
    limits: dict,
) -> list[dict]:
    """Ask the existing solver whether two individually feasible options differ under the same floor."""
    out = []
    feasible = [v for v in alternatives if v["code"] == "feasible"]
    for left, right in combinations(feasible, 2):
        requests = [analyses[v["analysis"]]["request"] for v in (left, right)]
        floors = [{k: v for k, v in request.items() if k != "query"} for request in requests]
        row = {
            "alternatives": [left["id"], right["id"]],
            "dependencies": ["analysis:" + left["analysis"], "analysis:" + right["analysis"]],
        }
        if not source_evidence.exact_json_equal(floors[0], floors[1]):
            out.append(
                {
                    **row,
                    "code": "incomparable_floors",
                    "request": None,
                    "result": None,
                    "support_status": None,
                    "origin_refs": [],
                }
            )
            continue
        q, r = (cast(a.Proposition, a.from_canonical(state.canonical(v["query"]))) for v in (left, right))
        xor = a.AnyOf((a.AllOf((q, a.Not(r))), a.AllOf((a.Not(q), r))))
        request = {**deepcopy(floors[0]), "query": json.loads(a.canonical(xor))}
        checked = _child(request, execute, budget, limits)
        result = checked["result"]
        code = "unresolved"
        support_status = None
        origins = []
        if result["code"] == "complete":
            decision = result["result"]["decision"]
            support_status = _feasibility_status(request, decision)
            origins = _origins(decision["proof"], values)
            accepted = support_status is not None
            if decision["result"] == "REFUTED" and accepted:
                code = "equivalent_under_floor"
            elif alternative_code(decision["result"], decision["blockers"], accepted, True) == "feasible":
                code = "distinguishable_under_floor"
        out.append({**row, **checked, "code": code, "support_status": support_status, "origin_refs": origins})
    return out


def _nodes(node: object) -> int:
    if isinstance(node, dict):
        return 1 + sum(_nodes(v) for v in node.values())
    if isinstance(node, list):
        return 1 + sum(_nodes(v) for v in node)
    return 1


def _nested_table_work(node: object) -> int:
    """Reserve every embedded table owner, including tables hidden in interpretation frames."""
    if isinstance(node, list):
        return sum(_nested_table_work(v) for v in node)
    if not isinstance(node, dict):
        return 0
    cost = 0
    if node.get("kind") == "decision_table" and isinstance(node.get("data"), dict):
        data = node["data"]
        limits = data.get("limits", {})
        bound, calls = limits.get("solver_bound"), limits.get("solver_calls")
        if (
            type(bound) is not int
            or not 1 <= bound <= 65536
            or type(calls) is not int
            or not 1 <= calls <= 256
        ):
            raise ValueError("invalid_resource_bound:session_table")
        from TrialLedger.layer2.decision_tables import work_reservation

        cost = work_reservation(data)
    elif node.get("kind") in signals.CLAIM_KINDS and isinstance(node.get("data"), dict):
        # Protocol operators publish their own conservative formulas (interface operators.md, C10);
        # a malformed declaration refuses here with the operator's named translation code.
        cost = signals.operator(node["kind"]).work_reservation(node["data"])
    return cost + sum(_nested_table_work(v) for v in node.values())


def _reserve(request: dict) -> int:
    """Reserve bounded satisfiability assignments, including proof minimization and nested tables.

    This is a conservative reservation in assignment/check units, not measured CPU time or solver calls.
    """
    operation = request["operation"]
    if operation == "evidence_requests":
        from TrialLedger.layer2 import evidence_requests

        bound = request.get("bound", evidence_requests.DEFAULT_BOUND)
        cap = request.get("limits", {}).get("max_decisions", evidence_requests.LIMITS["max_decisions"][0])
        if type(bound) is not int or not 1 <= bound <= 65536 or type(cap) is not int or cap < 1:
            raise ValueError("invalid_resource_bound:session_evidence_requests")
        n = max(
            (len(candidate.get("assertions", [])) for candidate in request.get("candidates", [])), default=0
        )
        return bound * cap * (12 * n + 32)
    bound = request.get("bound", 65536)
    if type(bound) is not int or not 1 <= bound <= 65536:
        raise ValueError("invalid_resource_bound:session_child")
    n = len(request.get("assertions", [])) + len(request.get("fixed", {}).get("assertions", []))
    queries = max(1, len(request.get("queries", [])))
    frames = request.get("interpretations", [])
    if frames:
        n += max(len(v.get("assumptions", [])) for v in frames)
    if operation == "source_assertions":
        n += 2
    calls = queries * (len(frames) + 1)
    candidates = request.get("candidates", [])
    if operation == "design_bounds":
        n = max((len(v.get("assertions", [])) for v in candidates), default=0)
        calls *= max(1, len(candidates)) * (len(request.get("observations", [])) + 1)
    base = (
        bound * (2 * n + 4) * calls
        if operation in ("entailment", "interpretations", "design_bounds", "source_assertions")
        else _nodes(request)
    )
    # Unsupported estimates retain the declared per-enumeration ceiling. These
    # call counts include proof minimization and the shared explanation plan.
    from TrialLedger.layer2.entail_explanations import MAX_CONDITIONS
    from TrialLedger.layer2.residual_requirements import MAX_PROFILE_PROBES

    ordinary = 2 * n + 4
    explained = ordinary * (2 * MAX_CONDITIONS + 1) + 1 + 2 * MAX_PROFILE_PROBES + 2 * MAX_CONDITIONS
    if operation == "entailment":
        base = bound * explained
    elif operation == "interpretations":
        base = bound * (ordinary * (2 * len(frames) + 1) + explained * queries * (len(frames) + 1))
    elif operation == "design_bounds":
        base = (
            bound * max(1, len(candidates)) * ((3 * n + 8) * len(request.get("observations", [])) + explained)
        )
    elif operation == "source_assertions":
        from TrialLedger.layer2 import source_assertions

        try:
            expanded = source_assertions.prepare(request)
        except ValueError:
            # The same pure preparation refuses before any solver call in service.
            pass
        else:
            base = sum(_reserve(child) for child in expanded["requests"])
    represented = solver_work.logical_reservation(request, bound)
    if represented is not None:
        base = represented
    # Parsing, raw validation and effective checks may visit the same table. Count every declared
    # query/frame/candidate use conservatively instead of assuming the wrapper calls it once.
    table_repeats = 3 * (queries + 1) * (len(frames) + 1) * (len(candidates) + 1)
    return base + _nested_table_work(request) * table_repeats


def _request(analysis: dict, prepared: dict, values: dict) -> tuple[dict, list[dict]]:
    request: dict[str, Any] = {"operation": analysis["operation"], **deepcopy(analysis["parameters"])}
    ledger = []
    seen = set()
    for use in analysis["uses"]:
        key = (use["premise"], use["slot"], use["projection"])
        if key in seen:
            raise ValueError("duplicate_projection_use")
        seen.add(key)
        slot = use["slot"]
        if use["projection"] == "source_study":
            held = prepared["sources"][use["premise"]]
            if "study" in request or "expected_digest" in request:
                raise ValueError("source_study_collision")
            if (
                analysis["target"]["kind"] != "historical"
                or analysis["target"]["scope"]["study"] != held["snapshot"]["study_ref"]
            ):
                raise ValueError("source_study_target_mismatch")
            request["study"] = deepcopy(held["study"])
            request["expected_digest"] = held["snapshot"]["digest"]
            ledger.append({**use, "source": deepcopy(held["snapshot"])})
            continue
        projected, detail = projections.project(use, analysis, values[use["premise"]], prepared, values)
        if slot in ("fixed_assertions", "fixed_signals"):
            field = "assertions" if slot == "fixed_assertions" else "signals"
            request.setdefault("fixed", {"assertions": [], "signals": []})[field].append(projected)
        else:
            request.setdefault(slot, []).append(projected)
        ledger.append({**use, "value": deepcopy(projected), "details": detail})
    for operation, field in (
        ("entailment", "assertions"),
        ("signals", "signals"),
        ("coordinates", "evidence"),
        ("corpus", "trials"),
    ):
        if analysis["operation"] == operation:
            request.setdefault(field, [])
    if analysis["operation"] == "interpretations":
        request.setdefault("fixed", {"assertions": [], "signals": []})
    return request, ledger


def _feasibility_status(request: dict, decision: dict) -> str | None:
    """Use actual accepted deciding support, preserving null for genuinely unfinished answers."""
    if decision["result"] in ("ENTAILED", "REFUTED", "INCONSISTENT"):
        status = decision["status"]
        return status if admission.admission_code(status, "resolved", True) == "accepted" else None
    if decision["result"] == "UNDETERMINED" and decision["blockers"] == ["undecided_by_constraints"]:
        by_id = {v["id"]: v for v in request["assertions"]}
        proof = decision["proof"]
        if proof and all(
            ref in by_id
            and admission.admission_code(by_id[ref]["status"], by_id[ref]["resolution"], True) == "accepted"
            for ref in proof
        ):
            return projections.weakest([by_id[ref] for ref in proof], list(proof))["status"]
    return None


def _accepted_decision(request: dict, decision: dict) -> bool:
    return _feasibility_status(request, decision) is not None


def _origins(proof: list[str], values: dict) -> list[dict]:
    """Actual deciding references are distinct from the complete replay-input origin ledger."""
    return [{"premise": ref, "origin": deepcopy(values[ref]["origin"])} for ref in proof if ref in values]


def _decision_support(
    code: str, alternatives: list[dict], distinctions: list[dict], selected: dict | None
) -> dict:
    """Retain a sufficient deciding warrant without unrelated pending alternatives weakening it."""
    by_id = {v["id"]: v for v in alternatives}
    groups = []
    if code == "design_choice":
        for i, check in enumerate(distinctions):
            if check["code"] == "distinguishable_under_floor":
                ids = check["alternatives"]
                statuses = [by_id[ref]["feasibility_status"] for ref in ids] + [check["support_status"]]
                groups.append((ids, [i], statuses))
    elif code == "settled_within_declared_alternatives":
        groups = [(list(by_id), [], [v["feasibility_status"] for v in alternatives])]
    elif code == "chosen_by_person":
        ref = cast(dict, selected)["alternative"]
        groups = [([ref], [], [by_id[ref]["feasibility_status"]])]
    elif code == "blocker":
        if alternatives and all(item["code"] == "infeasible" for item in alternatives):
            groups.append((list(by_id), [], [item["feasibility_status"] for item in alternatives]))
        for item in alternatives:
            if item["code"] == "conflict" or (
                selected is not None
                and item["id"] == selected["alternative"]
                and item["code"] == "infeasible"
            ):
                groups.append(([item["id"]], [], [item["feasibility_status"]]))
    valid = []
    for ids, checks, statuses in groups:
        if statuses and all(v is not None for v in statuses):
            status = "interpolated" if "interpolated" in statuses else "known"
            valid.append((status, ids, checks))
    if not valid:
        return {
            "standing": None,
            "determining_alternatives": [],
            "determining_distinctions": [],
            "origin_refs": [],
        }
    status, ids, checks = min(valid, key=lambda v: (v[0] != "known", v[1], v[2]))
    origins = []
    for ref in ids:
        for origin in by_id[ref]["origin_refs"]:
            if origin not in origins:
                origins.append(deepcopy(origin))
    for i in checks:
        for origin in distinctions[i]["origin_refs"]:
            if origin not in origins:
                origins.append(deepcopy(origin))
    return {
        "standing": status,
        "determining_alternatives": ids,
        "determining_distinctions": checks,
        "origin_refs": origins,
    }


def _decisions(
    prepared: dict, analyses: dict, values: dict, execute: Callable[[object], dict], budget: dict
) -> list[dict]:
    out = []
    for item in prepared["decisions"].values():
        state.target(item["target"])
        state.text(item["question"], "decision.question")
        if item["coverage"] not in ("represented_restriction", "declared_design"):
            raise ValueError("unsupported_decision_coverage")
        alternatives = []
        ids = set()
        for original in state.rows(item["alternatives"], "alternatives"):
            alternative = state.obj(original, {"id", "label", "analysis", "query"}, "alternative")
            identity = state.text(alternative["id"], "alternative.id")
            state.text(alternative["label"], "alternative.label")
            if identity in ids:
                raise ValueError("duplicate_alternative_id")
            ids.add(identity)
            if alternative["analysis"] not in analyses:
                raise ValueError("unknown_alternative_analysis")
            checked = analyses[alternative["analysis"]]
            request, result = checked["request"], checked["result"]
            matches = checked["target"] == item["target"]
            if request["operation"] != "entailment" or not source_evidence.exact_json_equal(
                alternative["query"], request["query"]
            ):
                raise ValueError("alternative_requires_exact_entailment_query")
            if result["code"] != "complete":
                code, deciding = "translation_question", None
            else:
                deciding = result["result"]["decision"]
                code = alternative_code(
                    deciding["result"], deciding["blockers"], _accepted_decision(request, deciding), matches
                )
            alternatives.append(
                {
                    **deepcopy(alternative),
                    "code": code,
                    "warrant": deepcopy(deciding),
                    "feasibility_status": _feasibility_status(request, deciding)
                    if deciding is not None
                    else None,
                    "origin_refs": _origins(deciding["proof"], values) if deciding is not None else [],
                    "analysis_result_digest": checked["result_digest"],
                }
            )
        if len(alternatives) < 2:
            raise ValueError("decision_requires_declared_alternatives")
        selected = item["selected"]
        if selected is not None:
            state.obj(selected, {"alternative", "origin", "basis"}, "selected")
            if selected["origin"] != "user" or selected["alternative"] not in ids:
                raise ValueError("invalid_user_selection")
            basis = state.rows(selected["basis"], "selected.basis")
            if not basis:
                raise ValueError("missing_selection_basis")
            for v in basis:
                state.text(v, "selected.basis")
        distinctions = _distinctions(
            alternatives, analyses, values, execute, budget, prepared["session"]["limits"]
        )
        distinguished = any(v["code"] == "distinguishable_under_floor" for v in distinctions)
        question_code = _question(item["target"]["kind"], alternatives, selected, distinguished)
        deciding_support = _decision_support(question_code, alternatives, distinctions, selected)
        input_ids = sorted(
            {
                use["premise"]
                for alternative in alternatives
                for use in prepared["analyses"][alternative["analysis"]]["uses"]
                if use["premise"] in values
            }
        )
        out.append(
            {
                **deepcopy(item),
                **deciding_support,
                "origin": {"kind": "user_choice", "basis": deepcopy(selected["basis"])}
                if selected is not None
                else {"kind": "computed", "refs": deepcopy(deciding_support["origin_refs"])},
                "input_origins": _origins(input_ids, values),
                **(
                    {"evidence": deepcopy(prepared["decision_evidence"][item["id"]])}
                    if "evidence" in item
                    else {}
                ),
                "alternatives": alternatives,
                "distinctions": distinctions,
                "open_alternatives": [
                    {"id": v["id"], "code": v["code"]}
                    for v in alternatives
                    if v["code"] not in ("feasible", "infeasible")
                ],
                "code": question_code,
                "coverage_limit": (
                    "Only caller-declared represented constructs; not complete clinical eligibility."
                ),
            }
        )
    priority = {
        "blocker": 0,
        "translation_question": 1,
        "computation_task": 2,
        "evidence_question": 3,
        "design_choice": 4,
        "settled_within_declared_alternatives": 5,
        "chosen_by_person": 6,
        "chosen_with_open_checks": 3,
        "options_not_distinguished": 3,
        "unrepresented_design_question": 3,
    }
    return sorted(out, key=lambda v: (priority[v["code"]], v["id"]))


APPLICABILITY_PREMISE_KINDS = ("assertion", "source_assertion", "derived_assertion")


def applicability_code(result: str, admitted: bool) -> str:
    """Whether a declared assessment condition applies in the check's scope (pure).

    Only an admitted proof decides; anything else leaves the claims conditional (C4).

    pre: isinstance(result, str)
    post: __return__ in ("applies", "does_not_apply", "undetermined")
    post: __return__ == "undetermined" or admitted
    post: __return__ != "applies" or result == "ENTAILED"
    post: __return__ != "does_not_apply" or result == "REFUTED"
    """
    if admitted and result == "ENTAILED":
        return "applies"
    if admitted and result == "REFUTED":
        return "does_not_apply"
    return "undetermined"


def _applicability_premises(declared: dict, prepared: dict) -> list[str] | None:
    """The explicitly declared premises that decide a check's conditions; None when none are declared."""
    rows = [b for b in declared["bindings"] if b.get("projection") == "condition_applicability"]
    if not rows:
        return None
    if len(rows) != 1 or set(rows[0]) != {"projection", "premises"}:
        raise ValueError("protocol_applicability_binding")
    premises = rows[0]["premises"]
    if (
        type(premises) is not list
        or not premises
        or len(set(map(str, premises))) != len(premises)
        or any(p not in prepared["premises"] for p in premises)
        or any(prepared["premises"][p]["kind"] not in APPLICABILITY_PREMISE_KINDS for p in premises)
    ):
        raise ValueError("protocol_applicability_binding")
    return list(premises)


def _applicability(
    conditions: list[dict], premises: list[str] | None, declared: dict, values: dict, run_child: Callable
) -> tuple[str, list[dict], str | None, list[str]]:
    """Decide each declared condition by ordinary budgeted entailment over the declared premises.

    Returns the application, the retained decisions, and, when a proof decided the application, its weakest
    standing and deciding premise references. These travel with every affected finding (external review).
    """
    if not conditions:
        return "unconditional", [], None, []
    if premises is None:
        return "conditional", [], None, []
    context = {k: v for k, v in declared["scope"]["context"].items() if v is not None}
    rows = []
    for item in conditions:
        request = {
            "operation": "entailment",
            "assertions": [deepcopy(values[p]["payload"]) for p in premises],
            "query": deepcopy(item["condition"]),
            **({"context": context} if context else {}),
        }
        result = run_child(request)
        decision = (result.get("result") or {}).get("decision") or {}
        admitted = (
            result.get("code") == "complete"
            and admission.admission_code(decision.get("status", "proposed"), "resolved", True) == "accepted"
        )
        rows.append(
            {
                "object": item["object"],
                "premises": list(premises),
                "request": request,
                "result": deepcopy(result),
                "request_digest": state.digest(request),
                "result_digest": state.digest(result),
                "code": applicability_code(decision.get("result", ""), admitted),
                "status": decision.get("status"),
                "proof": list(decision.get("proof") or []),
            }
        )
    codes = {row["code"] for row in rows}
    deciding = [row for row in rows if row["code"] == "does_not_apply"] if "does_not_apply" in codes else rows
    if "does_not_apply" not in codes and codes != {"applies"}:
        return "conditional", rows, None, []
    status = entail.weakest_status(tuple(row["status"] for row in deciding))
    refs = sorted({ref for row in deciding for ref in row["proof"]})
    return ("not_applicable" if "does_not_apply" in codes else "unconditional"), rows, status, refs


def _run_protocol_checks(
    prepared: dict,
    values: dict,
    execute: Callable[[object], dict],
    budget: dict,
    index: dict,
    check_ids: list[str],
    assumed: frozenset[str] = frozenset(),
    frame_ref: str | None = None,
) -> list[dict]:
    """Run declared protocol checks through their named projections and the ordinary budgeted child path.

    Projection supplies requests and receipts only; operators compute; the signal gate admits each claim from
    its own deciding support. Nothing here interprets a label or promotes standing (interface R1, C4). In a
    hypothetical candidate frame only replaced objects' own entries are assumed (C8); premises keep theirs.
    """
    from TrialLedger.layer2 import protocol_decisions, protocol_projections

    limits = prepared["session"]["limits"]
    standing = {
        key: {k: value["standing"][k] for k in ("status", "resolution", "basis")}
        for key, value in values.items()
    }
    checks = []
    for check_id in check_ids:
        projected = protocol_projections.project(index, check_id, premise_standing=standing)
        children = []
        declared = index["checks"][check_id]
        deciding = _applicability_premises(declared, prepared)
        for child in projected["children"]:
            application, applicability, applied_status, applied_refs = _applicability(
                child["receipt"].get("conditions", []),
                deciding,
                declared,
                values,
                lambda request: _child(request, execute, budget, limits)["result"],
            )
            executed = (
                protocol_decisions.frame_request(child["request"], set(assumed), frame_ref or "frame")
                if assumed
                else child["request"]
            )
            checked = _child(executed, execute, budget, limits)
            result = checked["result"]
            signals_out = (
                (result.get("result") or {}).get("signals", []) if result.get("code") == "complete" else []
            )
            children.append(
                {
                    "id": child["id"],
                    "receipt": deepcopy(child["receipt"]),
                    "request": executed,
                    "result": deepcopy(result),
                    "request_digest": state.digest(executed),
                    "result_digest": state.digest(result),
                    "signals": [
                        {
                            key: deepcopy(signal[key])
                            for key in (
                                "id",
                                "kind",
                                "code",
                                "calculation_code",
                                "status",
                                "admission",
                                "blockers",
                            )
                        }
                        | {
                            "claim_admission": [
                                # C4: a declared assessment condition is never applied unconditionally.
                                {
                                    **deepcopy(row),
                                    "application": application,
                                    "application_status": applied_status,
                                    "application_refs": list(applied_refs),
                                    # The finding is no stronger than its applicability proof; the
                                    # arithmetic keeps its own independent standing in "status".
                                    "finding_status": entail.weakest_status(
                                        tuple(v for v in (row.get("status"), applied_status) if v)
                                    )
                                    if row.get("status") or applied_status
                                    else None,
                                }
                                for row in signal.get("claim_admission", [])
                            ]
                        }
                        for signal in signals_out
                    ],
                    "conditions": deepcopy(child["receipt"].get("conditions", [])),
                    "applicability": applicability,
                    "refusal": None if result.get("code") == "complete" else list(result.get("problems", [])),
                }
            )
        declared = index["checks"][check_id]
        checks.append(
            {
                "id": check_id,
                "kind": declared["kind"],
                "required": declared["required"],
                "scope": deepcopy(declared["scope"]),
                "objects": list(declared["objects"]),
                "projection": projected["projection"],
                "children": children,
                "unresolved": deepcopy(projected["unresolved"]),
                "not_computed": deepcopy(projected["not_computed"]),
            }
        )
    return checks


def _frame_claim(claim: dict, lifted: set[str]) -> dict:
    """A claim inside a candidate frame; one resting on a local assumption is never reported as known (C8)."""
    row = {
        key: claim.get(key)
        for key in ("id", "claim", "outcome", "admission", "application", "finding_status")
    }
    assumed = sorted(set(claim.get("support") or []) & lifted)
    row["assumed"] = assumed
    if assumed:
        row["finding_status"] = "proposed"
    return row


def _protocol_decision_rows(
    prepared: dict, values: dict, execute: Callable[[object], dict], budget: dict
) -> list[dict]:
    """Evaluate every protocol alternative freshly on its own detached candidate (C8)."""
    from TrialLedger.layer2 import protocol_decisions

    out = []
    for item in prepared.get("protocol_decisions", []):
        alternatives = []
        for alternative, held in zip(item["alternatives"], item["candidates"], strict=True):
            assumed = frozenset(o["id"] for o in alternative["replace_objects"])
            frame = "hypothetical" if assumed else "fixed"
            checks = _run_protocol_checks(
                prepared,
                values,
                execute,
                budget,
                held["index"],
                list(alternative["checks"]),
                assumed,
                f"frame:{frame}:{item['id']}:{alternative['id']}",
            )
            lifted = protocol_decisions.assumed_entry_ids(set(assumed))
            rows, required = [], []
            for check in checks:
                code = protocol_decisions.classify(check)
                if check["required"]:
                    required.append(code)
                rows.append(
                    {
                        "id": check["id"],
                        "required": check["required"],
                        "check_code": code,
                        "conditional_claims": [
                            claim["id"]
                            for child in check["children"]
                            for signal in child["signals"]
                            for claim in signal["claim_admission"]
                            if claim.get("application") == "conditional"
                        ],
                        "claims": [
                            _frame_claim(claim, lifted)
                            for child in check["children"]
                            for signal in child["signals"]
                            for claim in signal["claim_admission"]
                        ],
                        "children": [
                            {
                                "request_digest": c["request_digest"],
                                "result_digest": c["result_digest"],
                                # The alternative's own computed schedule values (windows, feasible part,
                                # gap), retained so delivery can show them without recomputing.
                                "schedule": [
                                    deepcopy(signal["value"])
                                    for signal in (
                                        (c["result"].get("result") or {}).get("signals", [])
                                        if c["result"].get("code") == "complete"
                                        else []
                                    )
                                    if signal.get("kind") == "schedule_coverage"
                                ],
                            }
                            for c in check["children"]
                        ],
                    }
                )
            compatibility = protocol_decisions.compatibility(required)
            alternatives.append(
                {
                    "id": alternative["id"],
                    "label": alternative["label"],
                    "frame": frame,
                    "assumption_refs": sorted(assumed),
                    "unconditional_application": "admitted"
                    if frame == "fixed" and compatibility == "compatible_under_declared_checks"
                    else "withheld",
                    "compatibility": compatibility,
                    "conditional_checks": [row["id"] for row in rows if row["conditional_claims"]],
                    "checks": rows,
                    "candidate_digest": state.digest(held["raw"]),
                }
            )
        selected = item["selected"]
        chosen = next(
            (a["compatibility"] for a in alternatives if selected and a["id"] == selected["alternative"]),
            None,
        )
        out.append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "question": item["question"],
                "target": deepcopy(item["target"]),
                "coverage": item["coverage"],
                "selected": deepcopy(selected),
                "selection": deepcopy(selected),
                "alternatives": alternatives,
                "disposition": protocol_decisions.disposition(
                    [(a["compatibility"], a["candidate_digest"]) for a in alternatives], chosen
                ),
                **({"evidence": deepcopy(item["evidence"])} if "evidence" in item else {}),
            }
        )
    return out


def _protocol_checks(prepared: dict, values: dict, execute: Callable[[object], dict], budget: dict) -> dict:
    """The baseline protocol checks, then every protocol alternative on its detached candidate."""
    index = prepared["protocol"]
    checks = _run_protocol_checks(prepared, values, execute, budget, index, list(index["check_order"]))
    return {
        "schema_version": 1,
        "objects": [deepcopy(index["objects"][key]) for key in index["order"]],
        "sections": deepcopy(index["sections"]),
        "checks": checks,
        "decisions": _protocol_decision_rows(prepared, values, execute, budget),
        "limits_of_claim": [
            "Each check covers only its declared objects, claims and variables; not medical completeness.",
            "Projection receipts record consumed objects and premises; they do not establish meaning.",
            "Each claim is admitted on its own deciding support; the signal code is a conservative summary.",
        ],
    }


def replay(prepared: dict, execute: Callable[[object], dict], budget: dict) -> dict:
    """Execute every child afresh; full graph is replay dependence, not global support."""
    values, analyses, ledger = {}, {}, []
    limits = prepared["session"]["limits"]
    for node in prepared["order"]:
        kind, key = node.split(":", 1)
        if kind == "source":
            continue
        if kind == "premise":
            values[key] = projections.effective(prepared["premises"][key], prepared, values, analyses)
            continue
        analysis = prepared["analyses"][key]
        request, projected = _request(analysis, prepared, values)
        checked = _child(request, execute, budget, limits)
        result = checked["result"]
        analyses[key] = {
            "id": key,
            "target": deepcopy(analysis["target"]),
            "request": request,
            "result": deepcopy(result),
            "request_digest": state.digest(request),
            "result_digest": state.digest(result),
            "dependencies": list(prepared["graph"][node]),
        }
        ledger.append({"analysis": key, "projections": projected})
    from TrialLedger.layer2 import definition_checks

    # Protocol checks run before definition relations, so a relation can read their retained children.
    protocol_out = _protocol_checks(prepared, values, execute, budget) if "protocol" in prepared else None
    related_definitions = definition_checks.run(
        prepared["definition_checks"],
        analyses,
        lambda request: _child(request, execute, budget, limits),
        protocol=protocol_out,
        target=prepared["session"]["target"],
    )
    return {
        "schema_version": prepared["session"]["schema_version"],
        "session_id": prepared["session"]["id"],
        "revision": prepared["session"]["revision"],
        "session_digest": prepared["digest"],
        "target": deepcopy(prepared["session"]["target"]),
        "sources": [
            {
                "id": key,
                "snapshot": deepcopy(v["snapshot"]),
                "study": deepcopy(v["study"]),
                "compiled": deepcopy(v["compiled"]),
            }
            for key, v in prepared["sources"].items()
        ],
        "premises": deepcopy(list(prepared["premises"].values())),
        "effective_premises": list(values.values()),
        "dependency_graph": deepcopy(prepared["graph"]),
        "analyses": list(analyses.values()),
        "projection_ledger": ledger,
        "decisions": _decisions(prepared, analyses, values, execute, budget),
        **({"protocol": protocol_out} if protocol_out is not None else {}),
        **({"definition_checks": related_definitions} if "definition_checks" in prepared["session"] else {}),
        "limits": deepcopy(limits),
        "limit_semantics": {
            "max_expanded_items": "legacy_nonoperative; expanded_items is diagnostic only",
            "max_solver_work": "aggregate reservation across fresh previous and current analyses",
            "max_output_bytes": "complete serialized output; no truncation",
        },
        "limits_of_claim": [
            "Caller labels do not independently verify source truth or confirmation.",
            "Exact representation comparison is not clinical semantic equivalence.",
            "A represented restriction is not full patient eligibility.",
            "All analysis inputs are replay dependencies; only claimed support or actual deciding warrants "
            "weaken a finding.",
        ],
    }


def _diff(before: dict, after: dict) -> dict:
    out = {}
    fields = ["sources", "premises", "effective_premises", "analyses", "decisions"]
    if "definition_checks" in before or "definition_checks" in after:
        fields.append("definition_checks")
    for field in fields:
        old, new = ({v["id"]: v for v in snapshot.get(field, [])} for snapshot in (before, after))
        out[field] = [
            {
                "id": key,
                "code": state.change_code(
                    key in old, key in new, source_evidence.exact_json_equal(old.get(key), new.get(key))
                ),
                "before_digest": state.digest(old[key]) if key in old else None,
                "after_digest": state.digest(new[key]) if key in new else None,
            }
            for key in sorted(old.keys() | new.keys())
        ]
    return out


ANSWER_CHANGE_CODES = (
    "new",
    "withdrawn",
    "projection_unknown",
    "answer_changed",
    "support_changed",
    "origin_changed",
    "input_only",
    "unchanged",
)
REVISION_AXES = ("question", "wording", "answer", "support", "origin", "context", "requirements")
REVISION_CHANGE_CODES = ANSWER_CHANGE_CODES + (
    "question_changed",
    "wording_changed",
    "context_changed",
    "requirements_changed",
)


def answer_change_code(
    before: bool,
    after: bool,
    comparable: bool,
    answer_equal: bool,
    support_equal: bool,
    origin_equal: bool,
    input_equal: bool,
) -> str:
    """Name a change without collapsing its independently retained axes (pure).

    post: __return__ in ANSWER_CHANGE_CODES
    post: __return__ != 'unchanged' or (before and after and comparable)
    post: __return__ != 'unchanged' or (answer_equal and support_equal and origin_equal and input_equal)
    """
    if not before:
        return "new"
    if not after:
        return "withdrawn"
    if not comparable:
        return "projection_unknown"
    if not answer_equal:
        return "answer_changed"
    if not support_equal:
        return "support_changed"
    if not origin_equal:
        return "origin_changed"
    return "unchanged" if input_equal else "input_only"


def revision_change_code(
    before: bool,
    after: bool,
    comparable: bool,
    question_equal: bool,
    wording_equal: bool,
    answer_equal: bool,
    support_equal: bool,
    origin_equal: bool,
    context_equal: bool,
    input_equal: bool,
    requirements_equal: bool = True,
) -> str:
    """Name the primary revision axis while retaining every independent axis (pure).

    post: __return__ in REVISION_CHANGE_CODES
    post: __return__ != 'answer_changed' or (question_equal and not answer_equal)
    post: __return__ != 'unchanged' or (before and after and comparable and input_equal)
    """
    if not before:
        return "new"
    if not after:
        return "withdrawn"
    if not comparable:
        return "projection_unknown"
    if not question_equal:
        return "question_changed"
    if not answer_equal:
        return "answer_changed"
    if not requirements_equal:
        return "requirements_changed"
    if not support_equal:
        return "support_changed"
    if not context_equal:
        return "context_changed"
    if not wording_equal:
        return "wording_changed"
    if not origin_equal:
        return "origin_changed"
    return "unchanged" if input_equal else "input_only"


def _analysis_answer(row: dict, snapshot: dict) -> dict:
    """Use the shared clinical projection; source origins remain session-owned data."""
    from TrialLedger.layer2 import clinical_answers

    envelope = row["result"]
    if envelope.get("code") != "complete":
        return {"state": "not_comparable", "refusal": deepcopy(envelope.get("problems", []))}
    payload = deepcopy(envelope["result"])
    if type(payload) is not dict:
        return {"state": "not_comparable", "reason": "unsupported_result_shape"}
    # The projector resolves only IDs in actual deciding warrants against this
    # ledger. This copy supplies provenance, not an additional logical premise.
    payload["effective_premises"] = deepcopy(snapshot["effective_premises"])
    axes = clinical_answers.change_projection(row["request"]["operation"], payload)
    known = bool(axes["answer"]) and all(item.get("completion") != "unclassified" for item in axes["support"])
    if envelope.get("metadata", {}).get("kind") == "inspection" and not axes["answer"]:
        # An admission-only inspection asked no clinical question. Compare its
        # documentary context without inventing a missing clinical projection.
        known = True
        axes["context"] = {"inspection": deepcopy(envelope["result"])}
    axes["question"] = {
        "target": deepcopy(row["target"]),
        "request": {
            key: deepcopy(row["request"][key])
            for key in ("query", "queries", "context")
            if key in row["request"]
        },
        "findings": axes["question"],
    }
    return {"state": "comparable" if known else "not_comparable", **axes}


def _decision_answer(row: dict, snapshot: dict) -> dict:
    """Use the same session-decision projection as the clinical handoff."""
    from TrialLedger.layer2 import clinical_answers

    axes = clinical_answers.change_projection(
        "design_session",
        {
            "decisions": [deepcopy(row)],
            "effective_premises": deepcopy(snapshot["effective_premises"]),
        },
    )
    # Generated pairwise distinction checks are consequences, not newly asked
    # questions or new caller wording/context. Compare the declared decision here.
    axes["question"] = {
        "target": deepcopy(row["target"]),
        "alternatives": [
            {"id": option["id"], "query": deepcopy(option["query"])} for option in row["alternatives"]
        ],
    }
    axes["wording"] = {
        "question": row["question"],
        "alternatives": [{"id": option["id"], "label": option["label"]} for option in row["alternatives"]],
    }
    axes["context"] = deepcopy(row.get("evidence", []))
    # Every option uses its own actual analysis, including options whose clinical
    # verdict is already copied into this decision. Residuals must not depend on
    # whether a renderer happened to repeat them at decision level.
    analyses = {item["id"]: item for item in snapshot.get("analyses", [])}
    for option in row["alternatives"]:
        analysis = analyses.get(option.get("analysis"))
        if analysis is None or analysis["result"].get("code") != "complete":
            continue
        payload = deepcopy(analysis["result"]["result"])
        payload["effective_premises"] = deepcopy(snapshot.get("effective_premises", []))
        detail = clinical_answers.change_projection(analysis["request"]["operation"], payload)
        axes["requirements"].append({"option": option["id"], "requirements": detail["requirements"]})
        if any(item["conditions"] for item in detail["requirements"]):
            axes["support"].append(
                {
                    "option": option["id"],
                    "condition_support": [
                        {key: deepcopy(item[key]) for key in ("conditions", "premise_versions")}
                        for item in detail["support"]
                    ],
                }
            )
            axes["origin"].append({"option": option["id"], "condition_origins": deepcopy(detail["origin"])})
    return {"state": "comparable", **axes}


def _definition_answer(row: dict, snapshot: dict) -> dict:
    from TrialLedger.layer2 import clinical_answers

    axes = clinical_answers.change_projection("design_session", {"definition_checks": [row]})
    axes["question"] = {
        "target": deepcopy(row["target"]),
        "relation": row["relation"],
        "meanings": {key: deepcopy(row["declaration"][key]["body"]) for key in ("left", "right")},
    }
    axes["context"] = deepcopy(row["observed"])
    axes["origin"] = {
        "relation_basis": deepcopy(row["basis"]),
        "readings": {key: deepcopy(row["declaration"][key]["basis"]) for key in ("left", "right")},
    }
    return {"state": "comparable", **axes}


PROTOCOL_AXES = ("verdict", "requirements", "support", "origin", "scope_model", "wording", "input")


def protocol_axes(changed: dict) -> list[str]:
    """Name changed protocol axes; a digest change alone is only input (pure).

    pre: all(isinstance(v, bool) for v in changed.values())
    post: all(axis in PROTOCOL_AXES for axis in __return__)
    post: "input" not in __return__ or __return__ == ["input"]
    post: "verdict" in __return__ or not changed.get("verdict")
    """
    named = [axis for axis in PROTOCOL_AXES[:-1] if changed.get(axis)]
    if not named and changed.get("input"):
        return ["input"]
    return named


def _claims_of(check: dict) -> dict:
    return {
        row["id"]: row
        for child in check.get("children", [])
        for signal in child.get("signals", [])
        for row in signal.get("claim_admission", [])
    }


WARRANT_FIELDS = (
    "status",
    "finding_status",
    "application_status",
    "application_refs",
    "support",
    "determining_ids",
)


def _semantic_record(check: dict) -> dict:
    """Typed per-check record for revision: claim rows and every non-claim operator's computed result.

    Verdict, admission and warrant (arithmetic, applicability and finding standing, applicability proofs,
    deciding references, role support) stay separate axes; a request digest never stands in for them.
    """
    claims = _claims_of(check)
    plain = {
        (child.get("id"), signal.get("id")): signal
        for child in check.get("children", [])
        for signal in child.get("signals", [])
        if not signal.get("claim_admission")
    }
    return {
        "verdict": {
            **{("claim", k): (v.get("effective_outcome"), v.get("application")) for k, v in claims.items()},
            **{
                ("signal", k): (s.get("code"), s.get("calculation_code"), tuple(s.get("blockers") or ()))
                for k, s in plain.items()
            },
            ("projection",): (
                tuple(u.get("code") for u in check.get("unresolved") or ()),
                check.get("not_computed") is not None,
            ),
        },
        "requirements": {
            **{("claim", k): v.get("admission") for k, v in claims.items()},
            **{("signal", k): (s.get("admission") or {}).get("code") for k, s in plain.items()},
        },
        "warrant": {
            **{
                ("claim", k): tuple(json.dumps(v.get(f), sort_keys=True) for f in WARRANT_FIELDS)
                for k, v in claims.items()
            },
            ("roles",): json.dumps(
                [
                    s.get("role_support")
                    for ch in check.get("children", [])
                    for s in ch.get("request", {}).get("signals", [])
                ],
                sort_keys=True,
            ),
            ("applicability",): json.dumps(
                [
                    (a.get("code"), a.get("status"), a.get("proof"))
                    for ch in check.get("children", [])
                    for a in ch.get("applicability") or []
                ],
                sort_keys=True,
            ),
        },
    }


CHANGE_FIELDS = ("effective_outcome", "application", "admission", "finding_status", "application_status")


def _check_changes(left: dict, right: dict) -> list[dict]:
    """Per-claim and per-signal before/after for a protocol check (walkthrough finding: thin answer_diff)."""
    out = []
    lc, rc = _claims_of(left), _claims_of(right)
    for key in sorted(lc.keys() | rc.keys()):
        for field in CHANGE_FIELDS:
            before = lc.get(key, {}).get(field)
            after = rc.get(key, {}).get(field)
            if before != after:
                out.append({"claim": key, "field": field, "before": before, "after": after})
    signals = [
        {
            (child.get("id"), signal.get("id")): signal
            for child in check.get("children", [])
            for signal in child.get("signals", [])
            if not signal.get("claim_admission")
        }
        for check in (left, right)
    ]
    for key in sorted(signals[0].keys() | signals[1].keys(), key=str):
        for field in ("code", "calculation_code", "blockers"):
            before = signals[0].get(key, {}).get(field)
            after = signals[1].get(key, {}).get(field)
            if before != after:
                out.append({"signal": key[1], "field": field, "before": before, "after": after})
    return out


def _record_changed(left: dict, right: dict) -> bool:
    return left.keys() != right.keys() or any(left[k] != right[k] for k in left)


def _protocol_answer_diff(before: dict, after: dict) -> dict:
    """Protocol consequences per check and decision, beside (never instead of) the audit diff (C9, REV-1)."""
    objects = [{o["id"]: o for o in snapshot.get("objects", [])} for snapshot in (before, after)]

    def involved(check: dict, side: int, field: str) -> list:
        return [objects[side].get(i, {}).get(field) for i in check.get("objects", [])]

    out: dict = {"checks": [], "decisions": []}
    old, new = ({c["id"]: c for c in snapshot.get("checks", [])} for snapshot in (before, after))
    for key in sorted(old.keys() | new.keys()):
        left, right = old.get(key), new.get(key)
        if left is None or right is None:
            out["checks"].append(
                {
                    "id": key,
                    "change": state.change_code(left is not None, right is not None, False),
                    "axes": [],
                }
            )
            continue
        same = source_evidence.exact_json_equal
        lr, rr = _semantic_record(left), _semantic_record(right)
        verdict = _record_changed(lr["verdict"], rr["verdict"])
        changed = {
            "verdict": verdict,
            # Admission changed where the computed verdict did not (residual requirement).
            "requirements": any(
                lr["requirements"].get(k) != rr["requirements"].get(k)
                and lr["verdict"].get(k) == rr["verdict"].get(k)
                for k in lr["requirements"].keys() | rr["requirements"].keys()
            ),
            "support": _record_changed(lr["warrant"], rr["warrant"]),
            "origin": not same(involved(left, 0, "origin"), involved(right, 1, "origin")),
            "scope_model": not same(involved(left, 0, "scope"), involved(right, 1, "scope"))
            or not same(involved(left, 0, "version"), involved(right, 1, "version"))
            or not same(left.get("scope"), right.get("scope")),
            "input": [c.get("request_digest") for c in left.get("children", [])]
            != [c.get("request_digest") for c in right.get("children", [])],
        }
        axes = protocol_axes(changed)
        out["checks"].append(
            {
                "id": key,
                "code": state.change_code(True, True, not axes),
                "axes": axes,
                "changes": _check_changes(left, right),
            }
        )
    old, new = ({d["id"]: d for d in snapshot.get("decisions", [])} for snapshot in (before, after))
    for key in sorted(old.keys() | new.keys()):
        left, right = old.get(key), new.get(key)
        if left is None or right is None:
            out["decisions"].append(
                {
                    "id": key,
                    "change": state.change_code(left is not None, right is not None, False),
                    "axes": [],
                }
            )
            continue
        la, ra = ({a["id"]: a for a in d["alternatives"]} for d in (left, right))
        common = la.keys() & ra.keys()
        changed = {
            "verdict": left["disposition"] != right["disposition"]
            or la.keys() != ra.keys()
            or any(la[i]["compatibility"] != ra[i]["compatibility"] for i in common),
            "requirements": any(
                [(x["id"], x["admission"]) for c in la[i]["checks"] for x in c["claims"]]
                != [(x["id"], x["admission"]) for c in ra[i]["checks"] for x in c["claims"]]
                for i in common
            ),
            "wording": left["question"] != right["question"]
            or any(la[i]["label"] != ra[i]["label"] for i in common),
            "input": any(la[i]["candidate_digest"] != ra[i]["candidate_digest"] for i in common),
        }
        axes = protocol_axes(changed)
        out["decisions"].append({"id": key, "code": state.change_code(True, True, not axes), "axes": axes})
    return out


def _answer_diff(before: dict, after: dict) -> dict:
    """Clinical consequences alongside, never in place of, full canonical audit changes."""
    out = {}
    fields = ["analyses", "decisions"]
    if "definition_checks" in before or "definition_checks" in after:
        fields.append("definition_checks")
    for field in fields:
        old, new = (
            {v["id"]: (index, v) for index, v in enumerate(s.get(field, []))} for s in (before, after)
        )
        rows = []
        for key in sorted(old.keys() | new.keys()):
            projected = []
            for values, snapshot in ((old, before), (new, after)):
                row = values[key][1] if key in values else None
                projected.append(
                    None
                    if row is None
                    else _analysis_answer(row, snapshot)
                    if field == "analyses"
                    else _decision_answer(row, snapshot)
                    if field == "decisions"
                    else _definition_answer(row, snapshot)
                )
            left, right = projected
            comparable = (
                left is not None
                and right is not None
                and all(item["state"] == "comparable" for item in (left, right))
            )
            equal = {
                axis: comparable
                and left is not None
                and right is not None
                and source_evidence.exact_json_equal(left[axis], right[axis])
                for axis in REVISION_AXES
            }
            code = revision_change_code(
                key in old,
                key in new,
                comparable,
                *(equal[axis] for axis in REVISION_AXES if axis != "requirements"),
                source_evidence.exact_json_equal(
                    old.get(key, (None, None))[1], new.get(key, (None, None))[1]
                ),
                equal["requirements"],
            )
            active = new[key][1] if key in new else old[key][1]
            rows.append(
                {
                    "id": key,
                    "operation": active["request"]["operation"] if field == "analyses" else "design_session",
                    "code": code,
                    "changes": [axis for axis, same in equal.items() if comparable and not same],
                    "axes": {
                        axis: "unchanged" if same else "changed" if comparable else "not_comparable"
                        for axis, same in equal.items()
                    },
                    "before": left,
                    "after": right,
                    "before_path": f"/previous_fresh/{field}/{old[key][0]}" if key in old else None,
                    "after_path": f"/result/{field}/{new[key][0]}" if key in new else None,
                }
            )
        out[field] = rows
    if "protocol" in before or "protocol" in after:
        # Flat fields with {id, code, axes} rows, the established answer_diff row shape for every consumer.
        protocol = _protocol_answer_diff(before.get("protocol") or {}, after.get("protocol") or {})
        out["protocol_checks"] = protocol["checks"]
        out["protocol_decisions"] = protocol["decisions"]
    return out


def run(request: object, execute: Callable[[object], dict] | None = None) -> dict:
    """Run a closed session request; the public service owns envelope/refusal integration."""
    raw = state.obj(request, {"operation", "session", "previous"}, "session_request")
    # Fresh current/previous sessions and the supplied comparison result are
    # separately bounded JSON units. Summing their repeated retained sources
    # under one query-node cap rejects ordinary revisions without limiting solver work.
    held: dict[str, Any] = {
        "operation": source_evidence._json_copy(raw["operation"], "session_request"),
        "session": source_evidence._json_copy(raw["session"], "session_request"),
        "previous": None,
    }
    if raw["previous"] is not None:
        previous = state.obj(raw["previous"], {"session", "result", "expected_result_digest"}, "previous")
        held["previous"] = {
            key: source_evidence._json_copy(value, "previous_" + key) for key, value in previous.items()
        }
    if held["operation"] != "design_session":
        raise ValueError("unsupported_session_operation")
    current = state.prepare(held["session"])
    previous = held["previous"]
    old = None
    if previous is not None:
        state.obj(previous, {"session", "result", "expected_result_digest"}, "previous")
        if type(previous["result"]) is not dict:
            raise ValueError("invalid_previous_result")
        old = state.prepare(previous["session"])
        if old["session"]["schema_version"] != current["session"]["schema_version"]:
            # No implicit migration between representation versions (C2).
            raise ValueError("mixed_session_version_revision")
        if (
            old["session"]["id"] != current["session"]["id"]
            or old["session"]["revision"] == current["session"]["revision"]
        ):
            raise ValueError("invalid_session_revision_identity")
    code = state.revision_code(
        previous is not None,
        old is not None and current["session"]["parent_digest"] == old["digest"],
        previous is not None and state.digest(previous["result"]) == previous["expected_result_digest"],
    )
    if code not in ("initial", "replay"):
        raise ValueError(code)
    if old is None and current["session"]["parent_digest"] is not None:
        raise ValueError("initial_parent_must_be_null")
    if old is not None:
        # old is constructed only in the non-null previous branch above.
        assert previous is not None
        if previous["result"].get("session_digest") != old["digest"]:
            raise ValueError("previous_result_session_mismatch")
    if execute is None:
        from TrialLedger.layer2.service import run as execute
    budget = {"analyses": 0, "expanded_items": 0, "solver_work_reserved": 0}
    before = replay(old, execute, budget) if old is not None else None
    after = replay(current, execute, budget)
    output = {
        "code": "complete",
        "operation": "design_session",
        "result": after,
        "result_digest": state.digest(after),
        "previous_fresh": before,
        "diff": _diff(before, after) if before is not None else None,
        "answer_diff": _answer_diff(before, after) if before is not None else None,
        "work": budget,
        "problems": [],
    }
    if len(state.canonical(output).encode("utf-8")) > current["session"]["limits"]["max_output_bytes"]:
        raise ValueError("resource_bound:session_output_bytes")
    return output
