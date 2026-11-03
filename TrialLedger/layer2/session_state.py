"""Closed, content-addressed session ledgers; no clinical interpretation or solver."""

from __future__ import annotations

import hashlib
import json
from typing import Any, cast

from TrialLedger.layer2 import source_assertions, source_evidence

SESSION_FIELDS = {
    "schema_version",
    "id",
    "revision",
    "parent_digest",
    "target",
    "sources",
    "premises",
    "analyses",
    "decisions",
    "limits",
}
KINDS = {
    "source_assertion",
    "assertion",
    "signal",
    "binding",
    "observation",
    "candidate",
    "corpus_trial",
    "coordinate_evidence",
    "derived_assertion",
}
OPERATIONS = {
    "entailment",
    "coordinates",
    "corpus",
    "design_bounds",
    "evidence_requests",
    "signals",
    "interpretations",
    "source_assertions",
}
SLOTS = {
    "assertions",
    "signals",
    "bindings",
    "observations",
    "candidates",
    "trials",
    "evidence",
    "fixed_assertions",
    "fixed_signals",
    "study",
}
HARD_LIMITS = {
    "max_analyses": 128,
    "max_premises": 1000,
    "max_sources": 64,
    "max_decisions": 128,
    "max_expanded_items": 10000,
    "max_solver_work": 10000000,
    "max_output_bytes": 16000000,
}


def canonical(value: object) -> str:
    """Canonical JSON of already finite, validated values."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: object) -> str:
    """Content identity, not a source-truth certificate."""
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def obj(value: object, fields: set[str], where: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("invalid_fields:" + where)
    return cast(dict[str, Any], value)


def text(value: object, where: str) -> str:
    if type(value) is not str or not value:
        raise ValueError("not_text:" + where)
    return value


def rows(value: object, where: str) -> list:
    if type(value) is not list:
        raise ValueError("not_list:" + where)
    return value


def target(value: object) -> dict:
    item = obj(value, {"kind", "ref", "scope"}, "target")
    if item["kind"] not in ("new_trial", "historical"):
        raise ValueError("unsupported_target_kind")
    text(item["ref"], "target.ref")
    scope = obj(item["scope"], {"study", "population", "arm", "time", "version"}, "target.scope")
    for key, val in scope.items():
        text(val, "target.scope." + key)
    return item


def revision_code(has_previous: bool, parent_matches: bool, result_matches: bool) -> str:
    """Name the revision's documentary gate, never a clinical outcome (pure).

    post: __return__ in ('initial', 'replay', 'parent_mismatch', 'result_mismatch')
    post: has_previous or __return__ == 'initial'
    post: __return__ != 'replay' or (has_previous and parent_matches and result_matches)
    """
    if not has_previous:
        return "initial"
    if not parent_matches:
        return "parent_mismatch"
    if not result_matches:
        return "result_mismatch"
    return "replay"


def change_code(before: bool, after: bool, equal: bool) -> str:
    """Classify one stable identifier after actual fresh replays (pure).

    post: __return__ in ('new', 'withdrawn', 'unchanged', 'changed', 'absent')
    post: before or not after or __return__ == 'new'
    post: after or not before or __return__ == 'withdrawn'
    """
    if not before:
        return "new" if after else "absent"
    if not after:
        return "withdrawn"
    return "unchanged" if equal else "changed"


def _index(items: list, fields: set[str], where: str) -> dict[str, dict]:
    out = {}
    for raw in items:
        item = obj(raw, fields, where)
        key = text(item["id"], where + ".id")
        if key in out:
            raise ValueError("duplicate_id:" + where + ":" + key)
        out[key] = item
    return out


def _ordered(graph: dict[str, list[str]]) -> list[str]:
    """Iteratively order the complete graph; flat chains do not consume Python call depth."""
    done: set[str] = set()
    active: set[str] = set()
    order = []
    for root in graph:
        stack = [(root, False)]
        while stack:
            key, leaving = stack.pop()
            if leaving:
                active.remove(key)
                done.add(key)
                order.append(key)
                continue
            if key in active:
                raise ValueError("dependency_cycle:" + key)
            if key in done:
                continue
            if key not in graph:
                raise ValueError("unknown_dependency:" + key)
            active.add(key)
            stack.append((key, True))
            stack.extend((child, False) for child in reversed(graph[key]))
    return order


def _origin(premise: dict, sources: dict, analyses: dict) -> None:
    origin = obj(premise["origin"], {"kind", "ref", "source", "analysis"}, "origin")
    text(origin["ref"], "origin.ref")
    if origin["kind"] not in ("source_rule", "source_interpretation", "user_choice", "hypothesis", "derived"):
        raise ValueError("unsupported_origin")
    if origin["source"] is not None and origin["source"] not in sources:
        raise ValueError("unknown_source:origin")
    if origin["analysis"] is not None and origin["analysis"] not in analyses:
        raise ValueError("unknown_analysis:origin")
    if origin["kind"] == "source_rule":
        if (
            premise["kind"] != "source_assertion"
            or origin["source"] is None
            or origin["analysis"] is not None
        ):
            raise ValueError("source_rule_requires_compiled_assertion")
    elif premise["kind"] == "source_assertion":
        raise ValueError("compiled_assertion_requires_source_rule")
    if origin["kind"] == "derived":
        payload = obj(premise["payload"], {"analysis", "query"}, "derived_assertion")
        if (
            premise["kind"] != "derived_assertion"
            or origin["analysis"] != payload["analysis"]
            or origin["source"] is not None
        ):
            raise ValueError("derived_origin_mismatch")
    elif premise["kind"] == "derived_assertion" or origin["analysis"] is not None:
        raise ValueError("derived_analysis_requires_derived_origin")
    if origin["kind"] == "source_interpretation":
        if origin["source"] is None:
            raise ValueError("source_interpretation_requires_source")
        held = sources[origin["source"]]
        prefix = held["snapshot"]["study_ref"] + "#"
        if not origin["ref"].startswith(prefix):
            raise ValueError("source_interpretation_digest_mismatch")
        source_evidence._selected(held["study"], origin["ref"][len(prefix) :])
        if premise["kind"] == "assertion" and premise["payload"].get("criterion_ref") != origin["ref"]:
            raise ValueError("source_interpretation_assertion_ref_mismatch")
    if origin["kind"] in ("user_choice", "hypothesis") and origin["source"] is not None:
        raise ValueError("choice_origin_is_not_source_fact")


def _decision_inputs(decisions: dict, analyses: dict) -> None:
    """Check question administration before any reasoning call; no clinical feasibility is inferred."""
    for item in decisions.values():
        target(item["target"])
        text(item["question"], "decision.question")
        if item["coverage"] not in ("represented_restriction", "declared_design"):
            raise ValueError("unsupported_decision_coverage")
        ids, queries = set(), set()
        alternatives = rows(item["alternatives"], "alternatives")
        if not 2 <= len(alternatives) <= 16:
            raise ValueError("decision_requires_declared_alternatives")
        for raw in alternatives:
            alt = obj(raw, {"id", "label", "analysis", "query"}, "alternative")
            identity = text(alt["id"], "alternative.id")
            text(alt["label"], "alternative.label")
            if identity in ids:
                raise ValueError("duplicate_alternative_id")
            ids.add(identity)
            written = canonical(alt["query"])
            if written in queries:
                raise ValueError("duplicate_alternative_query")
            queries.add(written)
            analysis = analyses.get(alt["analysis"])
            if analysis is None:
                raise ValueError("unknown_alternative_analysis")
            if analysis["operation"] != "entailment" or not source_evidence.exact_json_equal(
                analysis["parameters"].get("query"), alt["query"]
            ):
                raise ValueError("alternative_requires_exact_entailment_query")
        selected = item["selected"]
        if selected is not None:
            obj(selected, {"alternative", "origin", "basis"}, "selected")
            if selected["origin"] != "user" or selected["alternative"] not in ids:
                raise ValueError("invalid_user_selection")
            basis = rows(selected["basis"], "selected.basis")
            if not basis:
                raise ValueError("missing_selection_basis")
            for value in basis:
                text(value, "selected.basis")


def prepare(value: object) -> dict:
    """Detach and validate ledgers and complete replay dependencies before any child call."""
    held = source_evidence._json_copy(value, "design_session")
    session = obj(held, SESSION_FIELDS, "session")
    if type(session["schema_version"]) is not int or session["schema_version"] != 1:
        raise ValueError("unsupported_session_version")
    for key in ("id", "revision"):
        text(session[key], key)
    if session["parent_digest"] is not None:
        text(session["parent_digest"], "parent_digest")
    target(session["target"])
    limits = obj(session["limits"], set(HARD_LIMITS), "limits")
    for key, ceiling in HARD_LIMITS.items():
        if type(limits[key]) is not int or not 1 <= limits[key] <= ceiling:
            raise ValueError("invalid_limit:" + key)
    sources_raw = _index(rows(session["sources"], "sources"), {"id", "study", "expected_digest"}, "source")
    premises = _index(
        rows(session["premises"], "premises"), {"id", "kind", "payload", "origin", "depends_on"}, "premise"
    )
    analyses = _index(
        rows(session["analyses"], "analyses"), {"id", "operation", "target", "parameters", "uses"}, "analysis"
    )
    decisions = _index(
        rows(session["decisions"], "decisions"),
        {"id", "question", "target", "coverage", "alternatives", "selected"},
        "decision",
    )
    for name, entries in (
        ("sources", sources_raw),
        ("premises", premises),
        ("analyses", analyses),
        ("decisions", decisions),
    ):
        if len(entries) > limits["max_" + name]:
            raise ValueError("resource_bound:" + name)
    sources = {}
    for key, row in sources_raw.items():
        compiled = source_assertions.prepare(
            {
                "operation": "source_assertions",
                "study": row["study"],
                "expected_digest": row["expected_digest"],
            }
        )
        sources[key] = {**row, "snapshot": compiled["source"], "compiled": compiled}
    graph: dict[str, list[str]] = {"source:" + key: [] for key in sources}
    for key, premise in premises.items():
        if premise["kind"] not in KINDS or type(premise["payload"]) is not dict:
            raise ValueError("invalid_premise_kind_or_payload:" + key)
        deps = rows(premise["depends_on"], "depends_on")
        if len(deps) != len(set(text(v, "depends_on") for v in deps)):
            raise ValueError("duplicate_dependency:" + key)
        _origin(premise, sources, analyses)
        graph["premise:" + key] = ["premise:" + ref for ref in deps]
        if premise["origin"]["source"] is not None:
            graph["premise:" + key].append("source:" + premise["origin"]["source"])
        if premise["kind"] == "derived_assertion":
            graph["premise:" + key].append("analysis:" + premise["payload"]["analysis"])
        if premise["kind"] == "corpus_trial":
            payload = obj(
                premise["payload"], {"source", "stratum", "feature_uses", "metadata"}, "corpus_trial"
            )
            if payload["source"] not in sources:
                raise ValueError("unknown_source:corpus_trial")
            text(payload["stratum"], "corpus_trial.stratum")
            graph["premise:" + key].append("source:" + payload["source"])
            for use in rows(payload["feature_uses"], "feature_uses"):
                use = obj(use, {"premise", "projection"}, "feature_use")
                graph["premise:" + key].append("premise:" + text(use["premise"], "feature_use.premise"))
    for key, analysis in analyses.items():
        if analysis["operation"] not in OPERATIONS or type(analysis["parameters"]) is not dict:
            raise ValueError("unsupported_analysis:" + key)
        target(analysis["target"])
        if analysis["target"]["kind"] == "new_trial" and analysis["target"] != session["target"]:
            raise ValueError("new_trial_target_mismatch:" + key)
        if set(analysis["parameters"]) & (SLOTS | {"operation", "fixed"}):
            raise ValueError("projected_slot_collision:" + key)
        graph["analysis:" + key] = []
        for use in rows(analysis["uses"], "uses"):
            use = obj(use, {"premise", "slot", "projection"}, "use")
            if use["slot"] not in SLOTS:
                raise ValueError("unsupported_projection_slot")
            ref = text(use["premise"], "use.premise")
            if use["projection"] == "source_study":
                if (
                    ref not in sources
                    or use["slot"] != "study"
                    or analysis["operation"] != "source_assertions"
                ):
                    raise ValueError("invalid_source_study_projection")
                graph["analysis:" + key].append("source:" + ref)
            else:
                graph["analysis:" + key].append("premise:" + ref)
    _decision_inputs(decisions, analyses)
    order = _ordered(graph)
    return {
        "session": session,
        "digest": digest(session),
        "sources": sources,
        "premises": premises,
        "analyses": analyses,
        "decisions": decisions,
        "graph": graph,
        "order": order,
    }
