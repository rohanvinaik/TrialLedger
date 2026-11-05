"""Closed, content-addressed session ledgers; no clinical interpretation or solver."""

from __future__ import annotations

import hashlib
import json
from typing import Any, cast

from TrialLedger.layer2 import decision_evidence, source_assertions, source_evidence

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
    "adoption",
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


def _adoption(premise: dict) -> None:
    """An explicit attributed record that the person adopted exact protocol object versions (2026-11-04)."""
    payload = obj(premise["payload"], {"objects", "status", "resolution"}, "adoption")
    if premise["origin"]["kind"] != "user_choice":
        raise ValueError("adoption_requires_user_choice")
    if payload["status"] not in ("known", "interpolated", "proposed") or payload["resolution"] not in (
        "resolved",
        "partially_resolved",
        "unresolved",
        "conflicting",
    ):
        raise ValueError("invalid_adoption_standing")
    adopted = rows(payload["objects"], "adoption.objects")
    if not adopted:
        raise ValueError("empty_adoption")
    seen = set()
    for item in adopted:
        row = obj(item, {"id", "version"}, "adoption.object")
        key = (text(row["id"], "adoption.object.id"), text(row["version"], "adoption.object.version"))
        if key in seen:
            raise ValueError("duplicate_adoption_object")
        seen.add(key)


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


def _decision_index(items: object) -> dict[str, dict]:
    """Accept optional context without inserting defaults into the caller's canonical session."""
    required = {"id", "question", "target", "coverage", "alternatives", "selected"}
    out = {}
    for item in rows(items, "decisions"):
        if type(item) is not dict or set(item) - (required | {"evidence"}) or required - set(item):
            raise ValueError("invalid_fields:decision")
        identity = text(item["id"], "decision.id")
        if identity in out:
            raise ValueError("duplicate_id:decision:" + identity)
        out[identity] = item
    return out


def _protocol_input_check(index: dict, premises: dict) -> None:
    """Refuse malformed protocol operator inputs at admission, before any work is reserved or computed.

    Each check is projected exactly as replay will project it, then each operator parses its own data and
    claims (`validate`, no solver). Premise standing affects only support rows, never operator data, so a
    placeholder standing that is never retained is used here. Bad parameters (for example p0 >= p1, or a
    critical count above n + 1) are refused by check id instead of halfway through a replay.
    """
    from TrialLedger.layer2 import protocol_projections, signals

    placeholder = {
        key: {"status": "proposed", "resolution": "unresolved", "basis": ["admission input check"]}
        for key in premises
    }
    for check_id in index["check_order"]:
        projected = protocol_projections.project(index, check_id, premise_standing=placeholder)
        for child in projected["children"]:
            request = child["request"]
            for signal in request.get("signals", []) if request.get("operation") == "signals" else []:
                if signal.get("kind") not in signals.CLAIM_KINDS:
                    continue
                try:
                    signals.operator(signal["kind"]).validate(
                        signal["kind"], signal["data"], signal.get("claims") or []
                    )
                except ValueError as error:
                    from TrialLedger.layer2 import refusal

                    # Repairable: point at the declared check (matched by value in the submitted request) and
                    # name the operator's input contract; the code is unchanged.
                    raise refusal.annotate(
                        ValueError(f"protocol_check_input:{check_id}:{error}"),
                        node=index["checks"][check_id],
                        rejected=str(error),
                        expected={
                            "requirement": f"the {signal['kind']} operator input contract",
                            "operator_code": str(error),
                        },
                        reference_view="protocol",
                    ) from error


def prepare(value: object) -> dict:
    """Detach and validate ledgers and complete replay dependencies before any child call."""
    held = source_evidence._json_copy(value, "design_session")
    if type(held) is not dict:
        raise ValueError("invalid_fields:session")
    version = held.get("schema_version")
    if type(version) is not int or version not in (1, 2):
        raise ValueError("unsupported_session_version")
    # Version 2 adds exactly one required ledger; version 1 is admitted exactly as before (CMP-1).
    required = SESSION_FIELDS | ({"protocol"} if version == 2 else set())
    if set(held) - (required | {"definition_checks"}) or required - set(held):
        raise ValueError("invalid_fields:session")
    session = held
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
    raw_decisions = rows(session["decisions"], "decisions")
    # Version 2 separates tagged protocol decisions; version 1 admission and its error codes are unchanged.
    protocol_raw = (
        [d for d in raw_decisions if type(d) is dict and "kind" in d]
        if session["schema_version"] == 2
        else []
    )
    decisions = _decision_index([d for d in raw_decisions if not any(d is p for p in protocol_raw)])
    for name, entries in (
        ("sources", sources_raw),
        ("premises", premises),
        ("analyses", analyses),
        ("decisions", [*decisions, *protocol_raw]),
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
        if premise["kind"] == "adoption":
            # Version 2 only; a v1 session keeps its exact previous refusal (CMP-1).
            if session["schema_version"] != 2:
                raise ValueError("invalid_premise_kind_or_payload:" + key)
            _adoption(premise)
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
    context = {
        key: decision_evidence.locate(item.get("evidence", []), sources) for key, item in decisions.items()
    }
    protocol = None
    if session["schema_version"] == 2:
        from TrialLedger.layer2 import protocol_objects

        protocol = protocol_objects.validate_protocol(
            session["protocol"], target=session["target"], premises=premises, sources=sources
        )
        _protocol_input_check(protocol, premises)
    protocol_decisions_out = []
    if protocol is not None:
        from TrialLedger.layer2 import protocol_decisions, protocol_objects

        for raw_decision in protocol_raw:
            item = protocol_decisions.validate(raw_decision, protocol, session["target"])
            if item["id"] in decisions or any(d["id"] == item["id"] for d in protocol_decisions_out):
                raise ValueError("duplicate_id:decision:" + item["id"])
            candidates = []
            for alternative in item["alternatives"]:
                raw_candidate = protocol_decisions.candidate(
                    session["protocol"], alternative["replace_objects"]
                )
                candidate_index = protocol_objects.validate_protocol(
                    raw_candidate, target=session["target"], premises=premises, sources=sources
                )
                _protocol_input_check(candidate_index, premises)
                candidates.append({"raw": raw_candidate, "index": candidate_index})
            protocol_decisions_out.append({**item, "candidates": candidates})
    from TrialLedger.layer2 import definition_checks

    # Protocol operands are validated against the admitted protocol index (v2 only; definitions.md).
    related_definitions = definition_checks.prepare(
        session.get("definition_checks", []), analyses, protocol=protocol
    )
    order = _ordered(graph)
    return {
        "session": session,
        "digest": digest(session),
        "sources": sources,
        "premises": premises,
        "analyses": analyses,
        "decisions": decisions,
        "decision_evidence": context,
        "definition_checks": related_definitions,
        "graph": graph,
        "order": order,
        **(
            {"protocol": protocol, "protocol_decisions": protocol_decisions_out}
            if protocol is not None
            else {}
        ),
    }
