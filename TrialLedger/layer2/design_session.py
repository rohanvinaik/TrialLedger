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

from TrialLedger.layer2 import admission, source_evidence
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
    budget["solver_work_reserved"] += _reserve(request)
    budget["analyses"] += 1
    code = session_work_code(
        budget["analyses"],
        budget["solver_work_reserved"],
        limits["max_analyses"],
        limits["max_solver_work"],
    )
    if code != "within_budget":
        raise ValueError(code)
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
        n = len(data.get("domains", [])) + len(data.get("constraints", []))
        cost = bound * calls * (2 * n + 4)
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
    }
    return sorted(out, key=lambda v: (priority[v["code"]], v["id"]))


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
    return {
        "schema_version": 1,
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
    for field in ("sources", "premises", "effective_premises", "analyses", "decisions"):
        old, new = ({v["id"]: v for v in snapshot[field]} for snapshot in (before, after))
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


def run(request: object, execute: Callable[[object], dict] | None = None) -> dict:
    """Run a closed session request; the public service owns envelope/refusal integration."""
    held = source_evidence._json_copy(request, "session_request")
    state.obj(held, {"operation", "session", "previous"}, "session_request")
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
    if old is not None and previous["result"].get("session_digest") != old["digest"]:
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
        "previous_fresh": before,
        "diff": _diff(before, after) if before is not None else None,
        "work": budget,
        "problems": [],
    }
    if len(state.canonical(output).encode("utf-8")) > current["session"]["limits"]["max_output_bytes"]:
        raise ValueError("resource_bound:session_output_bytes")
    return output
