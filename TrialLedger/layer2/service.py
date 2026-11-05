"""One JSON boundary around the rescued symbolic operations.

All conclusions are conditional on explicitly supplied typed premises. Supplying JSON
does not make an agent's interpretation a registry fact. Raw registry records and free
text are refused here; source-to-assertion compilation is a separate, unfinished step.
"""

from __future__ import annotations

import dataclasses
import json
from copy import deepcopy
from typing import Any

from TrialLedger.capabilities import DISCOVERY_VIEWS, OPERATIONS
from TrialLedger.layer2 import (
    assertions,
    bounds_guide,
    coherence,
    coordinate_admission,
    corpus_admission,
    design_bounds,
    design_session,
    design_session_guide,
    entail,
    evidence_requests,
    evidence_requests_guide,
    exception_bounds,
    exception_guide,
    expectations,
    guide,
    interpretation_bindings,
    interpretations,
    interpretations_guide,
    nearmiss,
    profile,
    request_preparation,
    result_semantics,
    signal_binding_gate,
    signals,
    signals_guide,
    source_assertions,
    source_assertions_guide,
    translation_diagnostics,
)

MAX_ITEMS = 1000
BASIS = "Conditional on the supplied typed premises; their source meaning is not certified by this operation."
# The same closed field sets drive request validation and the agent-facing description.
INPUTS = {
    **exception_guide.INPUTS,
    **bounds_guide.INPUTS,
    **signals_guide.INPUTS,
    **interpretations_guide.INPUTS,
    **source_assertions_guide.INPUTS,
    "describe": {
        "required": (),
        "fields": {
            "view": "overview, prepare, entailment, coordinates, corpus, design_bounds, signals, "
            "interpretations, "
            "source_assertions, design_session, evidence_requests, delivery, worked_session or full",
            "detail": "card (default), schema or full; full/worked_session views retain their full guide",
        },
    },
    "entailment": {
        "required": ("assertions", "query"),
        "fields": {
            "assertions": "array of tagged ScopedAssertion objects",
            "query": "tagged Literal, AllOf, AnyOf, Not or Opaque object",
            "context": "context object; omitted means open cohort/phase/arm",
            "bound": f"integer from 1 to {entail.MAX_ASSIGNMENTS}; default {entail.MAX_ASSIGNMENTS}",
        },
    },
    "coordinates": {
        "required": ("domain", "evidence"),
        "fields": {"domain": "string: nsclc", "evidence": "array of evidence objects"},
    },
    "corpus": {
        "required": ("trials",),
        "fields": {
            "trials": "array of trial objects with distinct ids",
            "cells": "array of [setting string, class string] pairs; default []",
            "expectations": "array of expectation objects; default []",
        },
    },
    "context": {
        "required": (),
        "fields": {
            "cohort": "nonempty string or null",
            "phase": "nonempty string or null",
            "arm": "nonempty string or null",
        },
    },
    "evidence": {
        "required": ("section", "concept", "values", "scope", "ref"),
        "fields": {
            "section": "string from sections",
            "concept": "string from coordinate_values",
            "values": "array of that concept's allowed strings",
            "scope": "string from scopes",
            "ref": "nonempty premise/source reference string",
            "standing": "standing object; omitted support stays pending",
        },
    },
    "trial": {
        "required": ("id", "sponsor", "stratum", "elements", "basis"),
        "fields": {
            "id": "nonempty string",
            "sponsor": "nonempty string",
            "stratum": "nonempty declared comparison-set string",
            "elements": "array of typed element strings",
            "basis": "nonempty array of nonempty premise/source references",
            "classes": "array of class strings; default []",
            "class_unresolved": "boolean; default true",
            "typed": "boolean; default false; required true when eligibility elements are supplied",
            "eligibility_content": "string: present or empty; default present",
            "coverage": "coverage object; default {}",
            "representation": "object of nonempty keys to string values; default {}",
            "predicates": "object of nonempty keys to string values; default {}",
            "start_year": "string; default empty",
            "setting_domain": "array of setting strings; required nonempty if cells are requested",
            "standing": "standing object for the explicitly accepted representation; omitted means pending",
            "feature_standings": (
                "overrides: elements/representation/predicates map exact keys to standing; classes, "
                "setting_domain, typed, eligibility_content, coverage each take a standing"
            ),
        },
    },
    "coverage": {
        "required": (),
        "fields": {"inclusion": "string from coverage_states", "exclusion": "string from coverage_states"},
    },
    "expectation": {
        "required": ("id", "observations", "cell", "support", "basis"),
        "fields": {
            "id": "nonempty string",
            "observations": "array of [cell string, observation-state string] pairs",
            "cell": "nonempty string",
            "support": "positive integer",
            "basis": "nonempty array of nonempty premise/source references",
            "standing": "standing object; omitted observations stay pending",
            "observation_standings": "array of standing objects, one per observation; overrides standing",
        },
    },
    "standing": {
        "required": ("status", "resolution", "basis"),
        "fields": {
            "status": "known, interpolated or proposed",
            "resolution": "string from resolutions; only resolved can be admitted",
            "basis": "nonempty array of nonempty premise/source references",
        },
    },
}
SECTIONS = ("inclusion", "exclusion", "unsectioned")
SCOPES = ("advanced", "unspecified", "")
COVERAGE_STATES = ("abbreviation_stated", "completeness_stated", "unspecified")
COORDINATE_VALUES = {
    "setting": coherence.SETTINGS,
    "prior_lines": coherence.PRIOR_LINES,
    "stage": ("I", "II", "III", "IV"),
    "extent": ("metastatic", "recurrent", "advanced", "locally_advanced"),
    "resection": ("resected", "resectable"),
    "setting_word": (*coherence.SETTINGS, "consolidation"),
    "prior_agent": ("radiotherapy",),
    **{f"biomarker:{gene}": coherence.STATES for gene in coherence.SELECTED_GENES},
}
FREQUENCY_FIELDS = (
    "stratum",
    "element",
    "stating",
    "absence_established",
    "unresolved_empty",
    "unresolved_untyped",
    "unresolved_abbreviated",
    "unresolved_unspecified",
    "unresolved",
    "trials",
    "statement_rate",
    "lower",
    "upper",
    "surprisal_bits",
    "sponsors",
    "tier",
    "estimand",
)
ASSOCIATION_FIELDS = (
    "stratum",
    "class",
    "element",
    "inside_stating",
    "inside_trials",
    "outside_stating",
    "outside_trials",
    "inside_rate",
    "outside_rate",
    "difference",
    "least_favourable_difference",
    "sponsors",
    "unresolved_class_trials",
    "inside_abbreviated",
    "outside_abbreviated",
    "status",
)
PAIR_FIELDS = (
    "a",
    "b",
    "difference",
    "value_a",
    "value_b",
    "sponsor_a",
    "sponsor_b",
    "year_a",
    "year_b",
    "other_predicates_agreeing",
)


class RequestError(ValueError):
    """A named problem with the symbolic request, never a negative clinical finding."""


def _object(value: Any, allowed: set[str], required: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RequestError(f"not_an_object:{where}")
    if set(value) - allowed:
        raise RequestError(f"unknown_field:{where}")
    if required - set(value):
        raise RequestError(f"missing_field:{where}")
    return value


def _input(value: Any, shape: str, where: str) -> dict[str, Any]:
    description = INPUTS[shape]
    fields = set(description["fields"])
    if shape in OPERATIONS:
        fields.add("operation")
    return _object(value, fields, set(description["required"]), where)


def _text(value: Any, where: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value):
        raise RequestError(f"not_text:{where}")
    return value


def _list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise RequestError(f"not_a_list:{where}")
    if len(value) > MAX_ITEMS:
        raise RequestError(f"resource_bound:{where}")
    return value


def _texts(value: Any, where: str) -> list[str]:
    return [_text(item, where) for item in _list(value, where)]


def _model(value: Any) -> object:
    if not isinstance(value, dict):
        raise RequestError("model_object_required")
    return assertions.from_canonical(json.dumps(value, allow_nan=False))


def _entailment(request: dict[str, Any]) -> dict[str, Any]:
    from TrialLedger.layer2.entail_explanations import explain

    _input(request, "entailment", "request")
    given = _scoped_assertions(request["assertions"])
    context = _reason_context(request.get("context", {}))
    bound = _assignment_bound(request.get("bound", entail.MAX_ASSIGNMENTS))
    query = _model(request["query"])
    decision = entail.decide(given, query, context, bound)
    result = {"basis": BASIS, "decision": dataclasses.asdict(decision), "premises": request["assertions"]}
    result["explanations"] = explain(given, query, context, decision, bound)
    if "no_constraint_mentions_query" in decision.blockers and isinstance(query, assertions.PROPOSITIONS):
        result["translation_diagnostics"] = translation_diagnostics.diagnose(given, query)
    return result


def _reason_context(value: Any) -> entail.Context:
    context = _input(value, "context", "context")
    for key, item in context.items():
        if item is not None:
            _text(item, key)
    return entail.Context(**context)


def _assignment_bound(value: Any) -> int:
    if type(value) is not int or not 1 <= value <= entail.MAX_ASSIGNMENTS:
        raise RequestError("invalid_resource_bound")
    return value


def _bound_count(value: Any, maximum: int | None = None) -> int:
    if type(value) is not int or value < 0 or (maximum is not None and value > maximum):
        raise RequestError("invalid_participant_count")
    return value


def _bound_basis(value: Any) -> tuple[str, ...]:
    refs = _texts(value, "basis")
    if not refs:
        raise RequestError("missing_witness_basis")
    return tuple(refs)


def _prepared_signals(raw: Any) -> list[signals.Signal]:
    prepared = []
    for value in _list(raw, "signals"):
        row = _input(value, "signal", "signal")
        identity = _text(row["id"], "signal:id")
        kind = _text(row["kind"], "signal:kind")
        if kind not in signals.MODULES:
            raise RequestError("unsupported_signal_kind")
        if not isinstance(row["data"], dict):
            raise RequestError("signal_data_not_object")
        support = []
        for premise in _list(row["support"], "support"):
            item = _input(premise, "support", "support")
            status, resolution = _support_words(item["status"], item["resolution"])
            support.append(
                signals.Support(
                    _text(item["id"], "support:id"), status, resolution, _bound_basis(item["basis"])
                )
            )
        if not support or len({p.id for p in support}) != len(support):
            raise RequestError("missing_or_duplicate_signal_support")
        bindings = row.get("bindings", {})
        if not isinstance(bindings, dict) or len(bindings) > MAX_ITEMS:
            raise RequestError("invalid_signal_bindings")
        bound = {}
        for ref, payload in bindings.items():
            body = _model(payload)
            if not isinstance(body, assertions.PROPOSITIONS):
                raise RequestError("signal_binding_not_proposition")
            bound[_text(ref, "binding:ref")] = body
        claims = None
        if "claims" in row:
            if kind not in signals.CLAIM_KINDS:
                raise RequestError("unsupported_signal_claims")
            raw_claims = _list(row["claims"], "signal:claims")
            if any(not isinstance(item, dict) for item in raw_claims):
                raise RequestError("signal_claim_not_object")
            claims = tuple(deepcopy(item) for item in raw_claims)
        role_support = None
        if "role_support" in row:
            if kind not in signals.CLAIM_KINDS:
                raise RequestError("unsupported_signal_role_support")
            raw_roles = row["role_support"]
            if not isinstance(raw_roles, dict) or not raw_roles:
                raise RequestError("invalid_signal_role_support")
            known_ids = {p.id for p in support}
            role_support = {}
            for role, ids in raw_roles.items():
                if role not in signals.ROLES[kind]:
                    raise RequestError("unknown_signal_role")
                listed = _list(ids, "signal:role_support")
                if not listed or len(set(listed)) != len(listed) or any(i not in known_ids for i in listed):
                    raise RequestError("invalid_signal_role_support")
                role_support[role] = tuple(listed)
        if kind in signals.CLAIM_KINDS:
            prepared.append(
                signals.ClaimSignal(
                    identity,
                    kind,
                    row["data"],
                    tuple(support),
                    bound,
                    claims=claims,
                    role_support=role_support,
                )
            )
        else:
            prepared.append(signals.Signal(identity, kind, row["data"], tuple(support), bound))
    if len({signal.id for signal in prepared}) != len(prepared):
        raise RequestError("duplicate_signal_id")
    return prepared


def _support_words(status: Any, resolution: Any) -> tuple[str, str]:
    if not isinstance(status, str) or status not in assertions.STATUSES:
        raise RequestError("invalid_witness_status")
    if not isinstance(resolution, str) or resolution not in assertions.RESOLUTIONS:
        raise RequestError("invalid_bridge_resolution")
    return status, resolution


def _signals(request: dict[str, Any]) -> dict[str, Any]:
    _input(request, "signals", "request")
    prepared, bindings = _bound_signals(request)
    response = {
        "basis": BASIS,
        "premises": request["signals"],
        "signals": [
            signals.evaluate(
                signal,
                list(signal.claims)
                if isinstance(signal, signals.ClaimSignal) and signal.claims is not None
                else None,
            )
            for signal in prepared
        ],
        "limits": (
            "Typed, source-bound partial evidence; no clinical text interpretation or source mutation."
        ),
    }
    if "bindings" in request or "binding_uses" in request:
        response["binding_checks"] = bindings
        response["binding_premises"] = {
            key: request.get(key, []) for key in ("study_ref", "bindings", "binding_uses")
        }
    return response


def _bound_signals(request: dict) -> tuple[list[signals.Signal], list[dict]]:
    """Run the same declared application gates before all ordinary signal consumers."""
    prepared = _prepared_signals(request.get("signals", []))
    if "bindings" not in request and "binding_uses" not in request:
        return prepared, []
    study = _text(request.get("study_ref"), "binding:study_ref")
    gated, checks = signal_binding_gate.gate_signals(
        tuple(prepared), request.get("bindings", []), request.get("binding_uses", []), study
    )
    return list(gated), checks


def _bound_observation(
    value: Any,
    available: dict | None = None,
    calculated: dict | None = None,
    exceptions: exception_bounds.Bundle | None = None,
) -> design_bounds.Observation:
    derived = isinstance(value, dict) and "derivation" in value
    row = _input(value, "derived_observation" if derived else "observation", "observation")
    bridge = _input(row["bridge"], "bridge", "bridge")
    denominator = _bound_count(row["denominator"])
    if not denominator:
        raise RequestError("empty_witness_denominator")
    bridge_status, resolution = _support_words(bridge["status"], bridge["resolution"])
    direction = row.get("direction", "accepted")
    if direction not in ("accepted", "rejected"):
        raise RequestError("unsupported_witness_direction")
    blockers: tuple[str, ...] = ()
    derivation = None
    if derived:
        selection = _input(row["derivation"], "derivation", "derivation")
        ref = _text(selection["signal"], "derivation:signal")
        witness = _text(selection["witness"], "derivation:witness")
        if available is None or calculated is None or ref not in available or ref not in calculated:
            raise RequestError("unknown_derived_signal")
        source = available[ref]
        result = calculated[ref]
        projected = signals.derived_witness(source, result, witness, row["population"], denominator)
        body = projected["body"]
        count = projected["lower"] if projected["lower"] is not None else 0
        upper = projected["upper"]
        source_status = result["status"]
        source_basis = tuple(result["basis"])
        blockers = tuple(projected["blockers"])
        derivation = {
            "signal": ref,
            "witness": witness,
            "lower": projected["lower"],
            "upper": upper,
            "expression": projected["expression"],
            "rule": result["rule"],
        }
    else:
        source_status, _ = _support_words(row["status"], "resolved")
        source_basis = _bound_basis(row["basis"])
        body = _model(row["body"])
        if "count" in row:
            if "count_lower" in row or "count_upper" in row:
                raise RequestError("exact_and_interval_witness_count")
            count = _bound_count(row["count"], denominator)
            upper = None
        elif "count_lower" in row and "count_upper" in row:
            count = _bound_count(row["count_lower"], denominator)
            upper = _bound_count(row["count_upper"], denominator)
            if upper < count:
                raise RequestError("reversed_witness_count_interval")
        else:
            raise RequestError("witness_count_needed")
    if not isinstance(body, assertions.PROPOSITIONS):
        raise RequestError("witness_proposition_required")
    cap = bridge["max_exceptions"]
    check = None
    bridge_basis = _bound_basis(bridge["basis"])
    if "exception_evidence" in bridge:
        if exceptions is None:
            raise RequestError("missing_exception_evidence")
        if cap is not None:
            cap = _bound_count(cap, denominator)
        applied = _exception_application(
            exceptions, bridge["exception_evidence"], row, body, cap, bridge_status, resolution
        )
        check = applied["check"]
        bridge_status = applied["status"]
        resolution = applied["resolution"]
        blockers += tuple(applied["blockers"])
        bridge_basis += tuple(applied["basis"])
        cap = applied["effective_cap"]
    else:
        cap = _bound_count(cap, denominator)
    return design_bounds.Observation(
        _text(row["id"], "observation:id"),
        count,
        denominator,
        _text(row["population"], "population"),
        body,
        _reason_context(row["context"]),
        entail.weakest_status((source_status, bridge_status)),
        resolution,
        cap,
        source_basis + bridge_basis,
        upper,
        direction,
        blockers,
        derivation,
        check,
    )


def _exception_application(bundle, reference, row, body, cap, status, resolution) -> dict:
    """Keep the checked positive budget separate from a rejected witness's different predicate."""
    applied = exception_bounds.apply(
        bundle, reference, row["population"], row["denominator"], body, cap, status, resolution
    )
    check = applied["check"]
    if row.get("direction", "accepted") != "accepted":
        blocker = "exception_budget_predicate_mismatch:" + row["id"]
        check = {
            "code": "unresolved",
            "lower": None,
            "upper": cap,
            "structural_maximum": row["denominator"],
            "positive_budget_check": check,
            "blockers": [blocker],
            "basis": applied["basis"],
            "rule": "exception-budget-direction:1",
        }
        applied.update(check=check, resolution="unresolved", blockers=[blocker])
    elif check["code"] in ("conflict", "attribution_conflict"):
        blocker = "exception_bridge_conflict:" + row["id"]
        applied.update(resolution="conflicting", blockers=[*applied["blockers"], blocker])
        check["blockers"] = applied["blockers"].copy()
    check.update(id="exception:" + row["id"], observation=row["id"], status=applied["status"])
    return applied


def _scoped_assertions(raw: Any) -> tuple[assertions.ScopedAssertion, ...]:
    items = []
    for value in _list(raw, "assertions"):
        item = _model(value)
        if not isinstance(item, assertions.ScopedAssertion):
            raise RequestError("assertions_required")
        items.append(item)
    return tuple(items)


def _design_bounds(request: dict[str, Any]) -> dict[str, Any]:
    _input(request, "design_bounds", "request")
    study = _text(request["study_ref"], "study_ref")
    exceptions = (
        exception_bounds.prepare(request["exception_evidence"], study)
        if "exception_evidence" in request
        else None
    )
    candidates = []
    claims: dict[str, list[dict]] = {}
    prepared, binding_checks = _bound_signals(request)
    by_id = {signal.id: signal for signal in prepared}
    calculated = {signal.id: signals.evaluate(signal) for signal in prepared}
    for raw in _list(request["candidates"], "candidates"):
        row = _input(raw, "candidate", "candidate")
        items = _scoped_assertions(row["assertions"])
        candidates.append((_text(row["id"], "candidate:id"), items))
        checks = []
        for value in _list(row.get("signal_claims", []), "signal_claims"):
            check = _input(value, "signal_claim", "signal_claim")
            ref = _text(check["signal"], "signal_claim:signal")
            if ref not in by_id or not isinstance(check["claim"], dict):
                raise RequestError("invalid_candidate_signal_claim")
            checks.append(check)
        claims[row["id"]] = checks
    observations = [
        _bound_observation(raw, by_id, calculated, exceptions)
        for raw in _list(request["observations"], "observations")
    ]
    if not candidates or not (observations or prepared):
        raise RequestError("empty_design_bounds_inputs")
    for ids in ([identity for identity, _ in candidates], [o.id for o in observations]):
        if len(set(ids)) != len(ids):
            raise RequestError("duplicate_design_bounds_id")
    bound = _assignment_bound(request.get("bound", entail.MAX_ASSIGNMENTS))
    # Bound total repeated solver calls as well as each individual enumeration.
    if len(candidates) * (len(observations) + len(prepared) + 1) > MAX_ITEMS:
        raise RequestError("resource_bound:design_bounds")
    query = _model(request["query"])
    if not isinstance(query, assertions.PROPOSITIONS):
        raise RequestError("query_proposition_required")
    result = design_bounds.bound_designs(
        candidates,
        observations,
        query,
        _reason_context(request.get("context", {})),
        bound,
        signals=prepared,
        claims=claims,
        computed_signals=list(calculated.values()),
    )
    if "bindings" in request or "binding_uses" in request:
        result["binding_checks"] = binding_checks
    return {
        "basis": BASIS,
        "study_ref": study,
        "premises": request,
        **result,
        "limits": (
            "Declared candidate family only; source meaning and eligibility bridges are not certified. "
            "No automatic table interpretation or source mutation."
        ),
    }


def _interpretation(
    raw: Any,
    fixed: tuple[signals.Signal, ...],
    bindings: tuple[interpretation_bindings.Binding, ...],
    study_ref: str,
) -> interpretations.Interpretation:
    row = _input(raw, "interpretation", "interpretation")
    origin = _text(row["origin"], "interpretation:origin")
    if origin not in ("assistant", "user", "source"):
        raise RequestError("unsupported_interpretation_origin")
    local = tuple(_prepared_signals(row.get("signals", [])))
    signal_ids = [signal.id for signal in (*fixed, *local)]
    if len(set(signal_ids)) != len(signal_ids):
        raise RequestError("duplicate_interpretation_signal_id")
    claims = []
    for value in _list(row.get("signal_claims", []), "signal_claims"):
        claim = _input(value, "signal_claim", "signal_claim")
        if _text(claim["signal"], "signal_claim:signal") not in signal_ids:
            raise RequestError("unknown_interpretation_signal")
        if not isinstance(claim["claim"], dict):
            raise RequestError("signal_claim_not_object")
        claims.append(claim)
    uses = interpretation_bindings.parse_uses(
        row.get("binding_uses", []), bindings, set(signal_ids), study_ref
    )
    return interpretations.Interpretation(
        _text(row["id"], "interpretation:id"),
        _text(row["label"], "interpretation:label"),
        origin,
        _bound_basis(row["basis"]),
        _scoped_assertions(row.get("assumptions", [])),
        local,
        tuple(claims),
        uses,
    )


def _interpretations(request: dict[str, Any]) -> dict[str, Any]:
    """Translate explicit frames without admitting their assumptions to ordinary entailment."""
    _input(request, "interpretations", "request")
    study_ref = _text(request["study_ref"], "study_ref")
    floor = _input(request["fixed"], "interpretation_floor", "fixed")
    fixed_assertions = _scoped_assertions(floor.get("assertions", []))
    fixed_signals = tuple(_prepared_signals(floor.get("signals", [])))
    if any(item.status == "proposed" for item in fixed_assertions) or any(
        support.status == "proposed" for signal in fixed_signals for support in signal.support
    ):
        raise RequestError("proposed_material_requires_interpretation_frame")
    bindings = interpretation_bindings.parse_bindings(request.get("bindings", []), study_ref)
    frames = tuple(
        _interpretation(raw, fixed_signals, bindings, study_ref)
        for raw in _list(request["interpretations"], "interpretations")
    )
    queries = []
    for value in _list(request["queries"], "queries"):
        row = _input(value, "interpretation_query", "interpretation_query")
        body = _model(row["body"])
        if not isinstance(body, assertions.PROPOSITIONS):
            raise RequestError("query_proposition_required")
        queries.append(interpretations.Query(_text(row["id"], "query:id"), body))
    if not frames or not queries:
        raise RequestError("empty_interpretation_inputs")
    for identities in ([frame.id for frame in frames], [query.id for query in queries]):
        if len(set(identities)) != len(identities):
            raise RequestError("duplicate_interpretation_or_query_id")
    items = len(fixed_assertions) + len(fixed_signals) + len(bindings) + len(queries)
    items += sum(
        len(frame.assumptions) + len(frame.signals) + len(frame.signal_claims) + len(frame.binding_uses)
        for frame in frames
    )
    if items > MAX_ITEMS or len(queries) * (len(frames) + 1) > MAX_ITEMS:
        raise RequestError("resource_bound:interpretations")
    selected = request.get("selected")
    if selected is not None:
        _text(selected, "selected")
        if selected not in {frame.id for frame in frames}:
            raise RequestError("unknown_selected_interpretation")
    return interpretations.resolve(
        study_ref,
        fixed_assertions,
        fixed_signals,
        frames,
        tuple(queries),
        bindings,
        _reason_context(request.get("context", {})),
        _assignment_bound(request.get("bound", entail.MAX_ASSIGNMENTS)),
        selected,
    )


def _source_assertions(request: dict[str, Any]) -> dict[str, Any]:
    """Anchor retained evidence, then consume generated premises through the existing public operations."""
    _input(request, "source_assertions", "request")
    if "context" in request:
        _reason_context(request["context"])
    if "bound" in request:
        _assignment_bound(request["bound"])
    prepared = source_assertions.prepare(request)
    # Inspection validates the same representation as a queried request without running a synthetic query.
    fixed = tuple(_prepared_signals(prepared["fixed"]["signals"]))
    _scoped_assertions(prepared["fixed"]["assertions"])
    bindings = interpretation_bindings.parse_bindings(prepared["bindings"], prepared["source"]["study_ref"])
    for frame in prepared["interpretations"]:
        _interpretation(frame, fixed, bindings, prepared["source"]["study_ref"])
    analyses = []
    for child in prepared["requests"]:
        answer = run(child)
        if answer["code"] != "complete":
            raise RequestError("source_assertions:downstream:" + ";".join(answer["problems"]))
        analyses.append(answer)
    return prepared | {"analyses": analyses}


def _coordinates(request: dict[str, Any]) -> dict[str, Any]:
    _input(request, "coordinates", "request")
    if request["domain"] != "nsclc":
        raise RequestError("unsupported_domain")
    given = _list(request["evidence"], "evidence")
    evidence = []
    for index, raw in enumerate(given):
        item = _input(raw, "evidence", f"evidence:{index}")
        section, concept = item["section"], item["concept"]
        if section not in SECTIONS:
            raise RequestError(f"unsupported_section:{index}")
        if not isinstance(concept, str) or concept not in COORDINATE_VALUES:
            raise RequestError(f"unsupported_concept:{index}")
        values = _texts(item["values"], f"evidence:{index}:values")
        if not set(values) <= set(COORDINATE_VALUES[concept]):
            raise RequestError(f"unsupported_value:{index}")
        scope = _text(item["scope"], f"evidence:{index}:scope", empty=True)
        if scope not in SCOPES:
            raise RequestError(f"unsupported_scope:{index}")
        evidence.append((section, concept, tuple(values), scope, _text(item["ref"], f"evidence:{index}:ref")))
    admitted = coordinate_admission.resolve(given, evidence)
    return {
        "basis": BASIS,
        "domain": "nsclc",
        "premises": given,
        **admitted,
        "relations": [dataclasses.asdict(item) for item in coherence.RELATIONS],
    }


def _trial(raw: Any, index: int) -> dict[str, Any]:
    item = _input(raw, "trial", f"trial:{index}")
    overrides = item.get("feature_standings", {})
    if isinstance(overrides, dict):
        for key in corpus_admission.SCALARS:
            if key in overrides and key not in item:
                raise RequestError(f"missing_override_target:trial:{item['id']}:{key}")
    for key in ("id", "sponsor", "stratum"):
        _text(item[key], f"trial:{index}:{key}")
    _texts(item["basis"], f"trial:{index}:basis")
    if not item["basis"]:
        raise RequestError(f"missing_basis:{index}")
    item = dict(item)
    for key in ("elements", "classes", "setting_domain"):
        item[key] = _texts(item.get(key, []), f"trial:{index}:{key}")
    for key, default in (("typed", False), ("class_unresolved", True)):
        item[key] = item.get(key, default)
        if type(item[key]) is not bool:
            raise RequestError(f"not_boolean:trial:{index}:{key}")
    if (
        any(element.split(":", 1)[0] in profile.ELIGIBILITY_SECTIONS for element in item["elements"])
        and not item["typed"]
    ):
        raise RequestError(f"elements_without_typed_premises:{index}")
    if not item["class_unresolved"] and not item["classes"]:
        raise RequestError(f"classes_not_established:{index}")
    item["eligibility_content"] = item.get("eligibility_content", "present")
    if item["eligibility_content"] not in ("present", "empty"):
        raise RequestError(f"unsupported_content:{index}")
    item["coverage"] = _input(item.get("coverage", {}), "coverage", "coverage")
    if any(value not in COVERAGE_STATES for value in item["coverage"].values()):
        raise RequestError(f"unsupported_coverage:{index}")
    for key in ("representation", "predicates"):
        value = item.get(key, {})
        if not isinstance(value, dict) or not all(
            isinstance(k, str) and k and isinstance(v, str) for k, v in value.items()
        ):
            raise RequestError(f"not_text_mapping:{index}:{key}")
        item[key] = value
    item["start_year"] = _text(item.get("start_year", ""), f"trial:{index}:start_year", empty=True)
    return item


def _corpus(request: dict[str, Any]) -> dict[str, Any]:
    _input(request, "corpus", "request")
    given = _list(request["trials"], "trials")
    trials = [_trial(raw, index) for index, raw in enumerate(given)]
    ids = [item["id"] for item in trials]
    if len(set(ids)) != len(ids):
        raise RequestError("duplicate_trial_id")
    cells = []
    for raw in _list(request.get("cells", []), "cells"):
        held = _texts(raw, "cell")
        if len(held) != 2:
            raise RequestError("cell_needs_setting_and_class")
        cells.append((held[0], held[1]))
    prepared = corpus_admission.prepare(trials, cells)
    observations = []
    for raw in _list(request.get("expectations", []), "expectations"):
        item = _input(raw, "expectation", "expectation")
        _text(item["id"], "expectation:id")
        _text(item["cell"], "expectation:cell")
        if not _texts(item["basis"], "expectation:basis"):
            raise RequestError("missing_expectation_basis")
        if type(item["support"]) is not int or item["support"] < 1:
            raise RequestError("invalid_expectation_support")
        rows = []
        for row in _list(item["observations"], "observations"):
            pair = _texts(row, "observation")
            if len(pair) != 2 or pair[1] not in expectations.STATUSES:
                raise RequestError("invalid_observation")
            rows.append((pair[0], pair[1]))
        admitted = corpus_admission.expectations(item, rows)
        observations.append(
            {
                "id": item["id"],
                "basis": item["basis"],
                "rarity": expectations.conditional_rarity(
                    admitted["observations"], item["cell"], item["support"]
                ),
                "admission": admitted["admission"],
                "pending": admitted["pending"],
                "admitted_count": admitted["admitted_count"],
            }
        )
    return {
        "basis": BASIS,
        "premises": given,
        "admission": prepared["admission"],
        "pending": prepared["pending"],
        "frequency": [
            {
                **row,
                "description": {
                    "scope": "declared_comparison_set",
                    "stating": row["stating"],
                    "trials": row["trials"],
                    "threshold": profile.STANDARD_SHARE if row["tier"] else None,
                    "meaning": "descriptive frequency threshold; no clinical standard or recommendation",
                },
            }
            for row in prepared["frequency"]
        ],
        "associations": [
            dict(zip(ASSOCIATION_FIELDS, row, strict=True))
            for row in profile.mechanism_rows(prepared["association_trials"])
        ],
        "association_abstentions": prepared["association_abstentions"],
        "near_misses": [
            dict(zip(PAIR_FIELDS, row, strict=True)) for row in nearmiss.near_misses(prepared["pairs"])
        ],
        "near_miss_abstentions": prepared["near_miss_abstentions"],
        "occupancy": prepared["occupancy"],
        "expectations": observations,
        "limits": (
            "Known/resolved support admits factual corpus inputs; other readings remain pending. Standing"
            " is declared, not independently certified. Statement rates and proposed associations are not"
            " clinical importance, causation, or permission to reuse protocol language."
        ),
    }


def _examples() -> dict[str, dict[str, Any]]:
    """Executable typed examples, constructed through the existing validated object model."""
    female = assertions.Literal(
        assertions.Subject("participant"),
        assertions.Predicate("demographic", "eligible_sex"),
        assertions.Value("enum", members=("female",)),
    )
    premise = assertions.ScopedAssertion(
        "population",
        "user:example-brief",
        "required",
        female,
        rule=assertions.Rule("user-choice", "1", warrants=("user:example-brief",)),
        status="known",
        resolution="resolved",
    )
    male = dataclasses.replace(female, value=assertions.Value("enum", members=("male",)))
    return {
        "entailment": {
            "operation": "entailment",
            "assertions": [json.loads(assertions.canonical(premise))],
            "query": json.loads(assertions.canonical(male)),
        },
        "coordinates": {
            "operation": "coordinates",
            "domain": "nsclc",
            "evidence": [
                {
                    "section": "inclusion",
                    "concept": "prior_lines",
                    "values": ["0"],
                    "scope": "advanced",
                    "ref": "user:example-no-prior",
                    "standing": {
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["user:example-no-prior"],
                    },
                },
                {
                    "section": "inclusion",
                    "concept": "extent",
                    "values": ["advanced"],
                    "scope": "",
                    "ref": "user:example-advanced",
                    "standing": {
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["user:example-advanced"],
                    },
                },
            ],
        },
        "corpus": {
            "operation": "corpus",
            "trials": [
                {
                    "id": "example-a",
                    "sponsor": "example-sponsor-a",
                    "stratum": "user-declared-example-set",
                    "elements": ["inclusion:ecog_ps=0|1"],
                    "typed": True,
                    "basis": ["user:example-typed-premises"],
                    "standing": {
                        "status": "known",
                        "resolution": "resolved",
                        "basis": [("user:example-typed-premises")],
                    },
                },
                {
                    "id": "example-b",
                    "sponsor": "example-sponsor-b",
                    "stratum": "user-declared-example-set",
                    "elements": [],
                    "basis": ["user:example-typed-premises"],
                    "standing": {
                        "status": "known",
                        "resolution": "resolved",
                        "basis": [("user:example-typed-premises")],
                    },
                },
            ],
        },
    }


def _full_description() -> dict[str, Any]:
    """Describe this actual boundary, not a promise of the unfinished automated writer."""
    example_basis = ["user:invented-demonstration-premises-not-registry-facts"]
    comparison = {
        "operation": "corpus",
        "trials": [
            {
                "id": f"invented-class-a-{index}",
                "sponsor": f"invented-sponsor-{index}",
                "stratum": "invented-comparison-set",
                "elements": ["inclusion:example_requirement=yes"],
                "typed": True,
                "classes": ["invented-class-a"],
                "class_unresolved": False,
                "basis": example_basis,
                "standing": {"status": "known", "resolution": "resolved", "basis": example_basis},
            }
            for index in range(profile.SIGNAL_MIN_TRIALS)
        ]
        + [
            {
                "id": "invented-class-b",
                "sponsor": "invented-outside-sponsor",
                "stratum": "invented-comparison-set",
                "elements": ["inclusion:another_example_requirement=yes"],
                "typed": True,
                "classes": ["invented-class-b"],
                "class_unresolved": False,
                "basis": example_basis,
                "standing": {"status": "known", "resolution": "resolved", "basis": example_basis},
            }
        ],
    }
    matched = {
        "operation": "corpus",
        "trials": [
            {
                "id": f"invented-match-{index}",
                "sponsor": f"invented-sponsor-{index}",
                "stratum": "invented-comparison-set",
                "elements": [],
                "basis": example_basis,
                "standing": {"status": "known", "resolution": "resolved", "basis": example_basis},
                "representation": {"setting": "example-setting", "drug_class": "example-class"},
                "predicates": {"example_score_limit": value, "example_other_choice": "same"},
                "start_year": str(2020 + index),
            }
            for index, value in enumerate(("0|1", "0|2"))
        ],
    }
    occupancy = {
        "operation": "corpus",
        "trials": [
            {
                "id": "invented-definite",
                "sponsor": "invented-sponsor-a",
                "stratum": "invented-comparison-set",
                "elements": [],
                "basis": example_basis,
                "standing": {"status": "known", "resolution": "resolved", "basis": example_basis},
                "classes": ["invented-class"],
                "class_unresolved": False,
                "setting_domain": ["example-setting-a"],
            },
            {
                "id": "invented-possible",
                "sponsor": "invented-sponsor-b",
                "stratum": "invented-comparison-set",
                "elements": [],
                "basis": example_basis,
                "standing": {"status": "known", "resolution": "resolved", "basis": example_basis},
                "setting_domain": ["example-setting-a", "example-setting-b"],
            },
        ],
        "cells": [
            [setting, "invented-class"]
            for setting in ("example-setting-a", "example-setting-b", "example-setting-c")
        ],
    }
    rarity = {
        "operation": "corpus",
        "trials": [],
        "expectations": [
            {
                "id": "invented-declared-expectation",
                "observations": [
                    ["example-cell", "present"],
                    ["example-cell", "explicitly_negated"],
                    ["example-cell", "unresolved"],
                    ["example-cell", "not_applicable"],
                ],
                "cell": "example-cell",
                "support": 2,
                "basis": example_basis,
                "standing": {"status": "known", "resolution": "resolved", "basis": example_basis},
            }
        ],
    }
    model = {}
    for name, cls in assertions.CLASSES.items():
        fields = dataclasses.fields(cls)
        model[name] = {
            "fields": {field.name: str(field.type) for field in fields},
            "required": [
                field.name
                for field in fields
                if (field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING)
                or (cls is assertions.ScopedAssertion and field.name == "rule")
            ],
        }
    return {
        "basis": BASIS,
        "clinical_use": (
            "Work through a trial concept in conversation: what did the comparison trials document, what "
            "should we choose, and what happens if we change it? The assistant reads saved evidence, "
            "settles material interpretations with the person and prepares typed comparison features or "
            "design premises. These operations compute the supported counts, consequences, contradictions "
            "and open choices, retaining their basis. TrialLedger does not make the person's clinical "
            "decisions; it finds them: the assistant keeps a decision list (answer_guide.decision_list) of "
            "each choice with its evidence and computed consequences, reruns checks when choices change, and "
            "can save the list and request/result pairs separately from the source record. "
            "The person makes the clinical judgments. Automatic source-to-premise compilation and complete "
            "protocol generation remain unintegrated. Read the relevant operation guide; the worked session "
            "shows runnable examples of the translation and checking steps."
        ),
        "answer_guide": guide.answer_guide(),
        "question_vocabulary": deepcopy(guide.QUESTION_VOCABULARY),
        "worked_session": guide.worked_session(),
        "operation_field": {"type": "string", "required": True, "values": list(OPERATIONS)},
        "input_shapes": deepcopy(INPUTS),
        "limits": {
            "maximum_list_items": MAX_ITEMS,
            "maximum_corpus_features": corpus_admission.MAX_FEATURES,
            "maximum_assignments": entail.MAX_ASSIGNMENTS,
            "unknown_fields": "refused",
        },
        "vocabularies": {
            "sections": SECTIONS,
            "scopes": SCOPES,
            "coordinate_values": deepcopy(COORDINATE_VALUES),
            "coverage_states": COVERAGE_STATES,
            "observation_states": expectations.STATUSES,
            "modalities": sorted(assertions.MODALITIES),
            "polarities": sorted(assertions.POLARITIES),
            "statuses": sorted(assertions.STATUSES),
            "resolutions": sorted(assertions.RESOLUTIONS),
            "subject_kinds": sorted(assertions.SUBJECT_KINDS),
            "predicate_kinds": sorted(assertions.PREDICATE_KINDS),
            "value_kinds": sorted(assertions.VALUE_KINDS),
            "comparisons_by_value_kind": {
                kind: sorted(values) for kind, values in assertions.KIND_COMPARISONS.items()
            },
            "scope_kinds": sorted(assertions.SCOPE_KINDS),
            "evidence_kinds": sorted(assertions.EVIDENCE_KINDS),
            "orientations": sorted(assertions.ORIENTATIONS),
            "anchors": sorted(assertions.ANCHOR_KINDS),
            "inclusivities": sorted(assertions.INCLUSIVITIES),
            "certainties": sorted(assertions.CERTAINTIES),
            "branch_nodes": sorted(assertions.BRANCH_NODES),
        },
        "tagged_model": {
            "encoding": (
                "An object has a class tag from this table; JSON arrays become immutable tuples. "
                "Model defaults apply to omitted optional fields, then all values are validated. "
                "Quantities need finite numbers; intervals need ordered bounds; enumerations need "
                "members fitting the comparison. A boolean literal states that its predicate holds: give "
                "no members or number (otherwise boolean_with_operand); use polarity negative or Not for "
                "'does not hold'. Units are compared as written, never converted; time scopes match only "
                "when identical."
            ),
            "classes": model,
        },
        "premise_status": {
            "known": (
                "Given or deduced relative to explicitly supplied premises; "
                "this operation does not certify their source meaning."
            ),
            "interpolated": (
                "A default remains a default; a consequence cannot become stronger than its premises."
            ),
            "proposed": "A proposal is shown separately and is not an entailment premise.",
        },
        "availability": {
            "built": [
                "scoped entailment with proof/blockers",
                "explicit NSCLC coordinate closure",
                "typed corpus calculations",
            ],
            "designed_not_integrated": [
                "automatic source-to-assertion compilation",
                "complete brief-to-warranted-protocol workflow",
            ],
        },
        "use_cases": [
            {
                "question": (
                    "Does a proposed inclusion, exclusion or other design choice follow from the premises?"
                ),
                "operation": "entailment",
                "read": "decision.result, decision.status, decision.proof and decision.blockers",
                "meaning": (
                    "A conditional logical consequence, contradiction or unresolved question; not "
                    "automatic source interpretation."
                ),
            },
            {
                "question": (
                    "Which NSCLC setting, prior-treatment and gene-selection values remain possible?"
                ),
                "operation": "coordinates",
                "read": "coordinates: known domains, interpolated domains and each separate proposal",
                "meaning": (
                    "Only admitted known evidence narrows the known space; interpolated evidence, "
                    "defaults and proposals retain their own standing."
                ),
            },
            {
                "question": "How commonly do the selected comparable records state an element?",
                "operation": "corpus",
                "read": "frequency",
                "meaning": (
                    "Statement rates, eligibility silence bounds and corpus rarity, not clinical "
                    "importance or permission to reuse wording."
                ),
            },
            {
                "question": "Is an element stated more often within a declared drug class than outside it?",
                "operation": "corpus",
                "read": "associations",
                "meaning": (
                    "A proposed statement-rate association with support and unresolved counts, not a "
                    "causal or clinical rule."
                ),
            },
            {
                "question": (
                    "Which trials match on our declared comparison features but differ in one shared "
                    "known design choice?"
                ),
                "operation": "corpus",
                "read": "near_misses",
                "meaning": (
                    "One difference under the supplied representation; other missing or unshared "
                    "predicates are not proved equal."
                ),
            },
            {
                "question": (
                    "Is a declared setting/class cell occupied, possibly occupied or empty within this "
                    "supplied corpus?"
                ),
                "operation": "corpus",
                "read": "occupancy",
                "meaning": (
                    "Unknown membership prevents an empty verdict; empty does not establish infeasible or"
                    " underserved."
                ),
            },
            {
                "question": (
                    "How unusual is a present or non-present observation of an explicitly declared "
                    "expectation?"
                ),
                "operation": "corpus",
                "read": "expectations",
                "meaning": (
                    "Conditional corpus rarity with a cell/parent/abstain result; not derivational "
                    "significance or an explanation of a deviation."
                ),
            },
        ],
        "result_guides": {
            "envelope": {
                "code": (
                    "complete means the operation ran; refused means malformed or unsupported input, "
                    "never a negative clinical finding"
                ),
                "operation": "the requested operation",
                "result": "the operation result, or null on refusal",
                "problems": "named refusal reasons; empty on completion",
                "metadata": (
                    "additive per-finding completion, support and cause descriptions; not source truth"
                ),
            },
            "entailment": {
                "fields": {
                    "basis": BASIS,
                    "premises": "supplied tagged assertions, retained unchanged",
                    "decision": {
                        "result": list(entail.RESULTS),
                        "query": "canonical JSON string of the query; empty when it is not a proposition",
                        "status": (
                            "weakest supporting premise status for a conclusion/inconsistency; null otherwise"
                        ),
                        "proof": (
                            "assertion ids used, or considered for an undetermined query; not a "
                            "reconstructed source quote"
                        ),
                        "blockers": (
                            "named reasons, read together (answer_guide.entailment.blockers): "
                            "undecided_by_constraints, no_constraint_mentions_query, resource_bound, "
                            "query_not_proposition, and per item proposed_refused, unresolved_rule, "
                            "unresolved_assertion, conflicting, open_scope, unresolved_scope, "
                            "unresolved_literal, unspecified_boundary, opaque"
                        ),
                    },
                },
                "semantics": (
                    "Required A OR B does not entail A alone. An exclusion negates the whole body. "
                    "Applicability is not itself required. Permission/definition/description alone impose"
                    " no constraint. Cohort, arm, time, subject and units stay distinct; units are not "
                    "converted here. Inconsistency never licenses entailment by explosion."
                ),
            },
            "coordinates": {
                "fields": {
                    "basis": BASIS,
                    "domain": "nsclc only; the caller declares applicability",
                    "premises": "supplied evidence objects, retained unchanged",
                    "admission": (
                        "per-item standing, admission code and known/interpolated/pending destination"
                    ),
                    "effects": (
                        "per-input consumers and marginal domain changes, separately from admission: "
                        "no_consumer, inactive, redundant, withheld, narrowed or guarded; an explanation "
                        "of symbolic use, not clinical feasibility or unique causality"
                    ),
                    "coordinates": "setting, prior_advanced_lines and selection:<gene> for each gene",
                    "relations": (
                        "each actual rule's id, statement, basis, approval, kind, needs, lines_within, "
                        "narrows, allowed, needs_any and forbids"
                    ),
                },
                "coordinate_row": {
                    "domain": "known-level remaining values",
                    "state": "resolved, unnarrowed, unresolved or conflict (empty domain)",
                    "causes": "[coordinate, removed values, premise ref or relation id] rows",
                    "interpolated": (
                        "domain, state and additional causes after defaults; never replaces the known domain"
                    ),
                    "proposals": (
                        "each narrowing proposal separately: relation, domain, state, causes; never "
                        "combined or used as a premise"
                    ),
                },
                "semantics": (
                    "Inclusion retains and exclusion removes explicitly supplied setting, prior-line or "
                    "gene-selection values. Explicit setting is a finite restriction, distinct from "
                    "setting_word evidence; neither supplies progression or a clinical equivalence. "
                    "Other facts activate the listed NSCLC relations. Inspect effects even when an input "
                    "is admitted: acceptance alone establishes no narrowing. An active negative guard "
                    "can preserve alternatives; unmet antecedents instead make a rule inactive. Current "
                    "stored relations are defaults or proposals, not strict clinical deductions."
                ),
            },
            "corpus": {
                "fields": [
                    "basis",
                    "premises",
                    "admission",
                    "pending",
                    "association_abstentions",
                    "near_miss_abstentions",
                    "frequency",
                    "associations",
                    "near_misses",
                    "occupancy",
                    "expectations",
                    "limits",
                ],
                "frequency": {
                    "row_fields": (
                        *FREQUENCY_FIELDS,
                        "unresolved_pending",
                        "pending_stating",
                        "pending_statement_lower",
                        "pending_statement_upper",
                        "description",
                    ),
                    "meaning": (
                        "Within each declared stratum, stating/trials counts admitted known/resolved "
                        "inputs. pending_stating retains unadmitted readings; "
                        "pending_statement_lower/upper bound their effect on supplied statements, not "
                        "missing source text. Zero admitted counts have null surprisal. Eligibility "
                        "lower/upper bound full-criteria frequency; absence_established is currently "
                        "zero. Empty, untyped, abbreviated and unspecified silences remain unresolved. "
                        "Non-eligibility elements have no eligibility bounds or tier. Surprisal is "
                        "-log2(statement rate), not importance."
                    ),
                    "tier_threshold": profile.STANDARD_SHARE,
                    "tier": (
                        "met if the unrounded lower bound reaches the threshold, not_met if the upper is "
                        "below it, otherwise unresolved; this is a corpus setting, not clinical necessity"
                    ),
                    "description": (
                        "names the declared-set scope, stating/trials denominator and descriptive "
                        "threshold; even two of two is a description, not a clinical standard. Class "
                        "association has its own distinct support requirement."
                    ),
                },
                "associations": {
                    "row_fields": ASSOCIATION_FIELDS,
                    "meaning": (
                        "Pending relevant inputs withhold their stratum and are named in "
                        "association_abstentions. Within each stratum's typed, resolved-class trials, "
                        "compare inside/outside statement rates. Unresolved-class trials are counted "
                        "separately; abbreviated silences give the least-favourable difference. Only "
                        "positive or potentially positive comparisons are listed; no row is not proof of "
                        "no relation."
                    ),
                    "support": {
                        "stating_trials": profile.SIGNAL_MIN_TRIALS,
                        "distinct_sponsors": profile.SIGNAL_MIN_SPONSORS,
                    },
                    "status": (
                        "proposed when the least-favourable comparison holds with support; below_support "
                        "when it holds without support; unresolved when abbreviated silences could "
                        "reverse it"
                    ),
                },
                "near_misses": {
                    "row_fields": PAIR_FIELDS,
                    "meaning": (
                        "Pending declared representation/predicate fields withhold the trial and are "
                        "named in near_miss_abstentions. Representation must be nonempty, have identical "
                        "keys and known equal values. Exactly one shared known predicate differs; "
                        "other_predicates_agreeing counts the shared known equal predicates. Sponsor and "
                        "year accompany each pair. The representation, not stratum, determines matching; "
                        "no causal conclusion is made."
                    ),
                },
                "occupancy": {
                    "row_fields": ["setting", "class", "occupants", "possible", "state"],
                    "meaning": (
                        "Counts of definite and possible members for every requested cell: occupied with "
                        "a definite member, otherwise unknown with a possible member, otherwise empty. "
                        "This applies to the supplied corpus, not the whole registry."
                    ),
                },
                "expectations": {
                    "row_fields": ["id", "basis", "rarity", "admission", "pending", "admitted_count"],
                    "rarity_positions": [
                        "source",
                        "P(present)",
                        "known_count",
                        "present_bits",
                        "non_present_bits",
                    ],
                    "meaning": (
                        "Only known/resolved admitted observations enter. source is cell if its support "
                        "is met, otherwise parent over all supplied known observations, otherwise "
                        "abstain. present, explicitly_negated and not_documented count as known; "
                        "unresolved/not_applicable do not. Non-present here includes not_documented: it "
                        "is not proof of admission or clinical absence. A never-observed event has null "
                        "bits. Observation rows are supplied independently, not automatically derived "
                        "from trials."
                    ),
                },
                "input_notes": {
                    "stratum": (
                        "caller-declared comparable population, shared by frequency and associations; the"
                        " operation does not establish clinical comparability"
                    ),
                    "elements": (
                        "exact strings; inclusion:, exclusion:, permitted: and unsectioned: prefixes "
                        "select eligibility silence accounting; other prefixes get statement rates only"
                    ),
                    "typed_and_basis": (
                        "declare supplied representation/provenance; neither the flag nor a reference "
                        "certifies source meaning"
                    ),
                    "classes": (
                        "caller-supplied class memberships; class_unresolved=true excludes the trial from"
                        " inside/outside comparisons and preserves possible occupancy"
                    ),
                    "representation_and_predicates": (
                        "caller-declared exact feature values; empty values are unknown and missing "
                        "predicates are not assumed equal"
                    ),
                },
            },
        },
        "capability_examples": {
            "associations": {
                "premise_origin": "Invented typed demonstration, not clinical evidence or a class claim.",
                "request": comparison,
                "expect": (
                    "inclusion:example_requirement=yes has an invented-class-a association with status "
                    "proposed, inside rate 1 and outside rate 0"
                ),
            },
            "near_misses": {
                "premise_origin": "Invented comparison features and design choices, not trial facts.",
                "request": matched,
                "expect": (
                    "one pair differing in example_score_limit, with one other shared known predicate "
                    "agreeing"
                ),
            },
            "occupancy": {
                "premise_origin": "Invented membership domains, not a registry search or unmet-need claim.",
                "request": occupancy,
                "expect": "example-setting-a occupied, example-setting-b unknown, example-setting-c empty",
            },
            "expectations": {
                "premise_origin": (
                    "Invented declared observation statuses, not an automatically read clinical expectation."
                ),
                "request": rarity,
                "expect": (
                    "rarity [cell, 0.5, 2, 1.0, 1.0]; unresolved and not_applicable do not enter the "
                    "denominator"
                ),
            },
        },
        "developer_building_blocks": {
            "availability": (
                "Retained Python entrypoints, not additional reason/CLI/MCP operations. Their caller must"
                " supply the stated typed inputs. None is an automatic source-to-assertion compiler."
            ),
            "entries": [
                {
                    "purpose": "Construct, validate and serialize complete scoped premises",
                    "entrypoints": [
                        "TrialLedger.layer2.assertions.ScopedAssertion",
                        "TrialLedger.layer2.assertions.canonical",
                        "TrialLedger.layer2.assertions.from_canonical",
                        "TrialLedger.layer2.construction.quantity",
                        "TrialLedger.layer2.construction.enum_value",
                        "TrialLedger.layer2.construction.enum_set_value",
                        "TrialLedger.layer2.construction.literal",
                        "TrialLedger.layer2.construction.scoped_assertion",
                        "TrialLedger.layer2.construction.expanded",
                    ],
                    "precondition": (
                        "Preserve the proposition's referent, Boolean alternatives, modality, "
                        "applicability, cohort/time scope and actual provenance; serialization does not "
                        "certify them. Construction helpers require explicit scope and origin, default "
                        "to proposed standing, and expose canonical expanded inputs; they do not read prose."
                    ),
                },
                {
                    "purpose": (
                        "Read a literal number, comparator, unit, reference expression, duration, window "
                        "or interval"
                    ),
                    "entrypoints": [
                        f"TrialLedger.layer2.semantics.parsers.read_{kind}"
                        for kind in (
                            "number",
                            "comparator",
                            "unit",
                            "reference",
                            "duration",
                            "window",
                            "interval",
                        )
                    ],
                    "precondition": (
                        "Supply the original text and expression start offset. Returns "
                        "Parse(kind,status,readings,spans,end,note), retaining alternatives/abstention. A"
                        " local literal reading does not settle clinical attachment, force or scope."
                    ),
                },
                {
                    "purpose": "Validate evidence spans and versioned concept/predicate signatures",
                    "entrypoints": [
                        "TrialLedger.layer2.semantics.contracts.atom_problems",
                        "TrialLedger.layer2.semantics.contracts.result_problems",
                        "TrialLedger.layer2.semantics.loader.load_fragments",
                        "TrialLedger.layer2.semantics.loader.compile_registry",
                        "TrialLedger.layer2.predicates.predicate_registry",
                        "TrialLedger.layer2.predicates.atom_literal",
                    ],
                    "precondition": (
                        "Supply contract atoms plus original text, or declared fragments/mappings. "
                        "atom_literal(mapping,atom) returns a candidate literal, named mapping code and "
                        "unread operands; no clinical assertion is authorised. Local registries retain "
                        "authority, edition and historical exposure limits."
                    ),
                },
                {
                    "purpose": "Resolve a source-bound indication and declared rule-pack applicability",
                    "entrypoints": [
                        "TrialLedger.layer2.indications.MeshLookup",
                        "TrialLedger.layer2.indications.resolve_indication",
                        "TrialLedger.layer2.universes.assign",
                        "TrialLedger.layer2.universes.pack_scope",
                    ],
                    "precondition": (
                        "MeshLookup(cache,year=...).lookup(label) explicitly fetches/caches fixed-year "
                        "exact MeSH identities. "
                        "resolve_indication(conditions,lookups,declared_indications,registry_mesh,own_assertions)"
                        " and assign(study,lookups=...) consume supplied source identities. No "
                        "supplied/resolved lookup means unresolved, not an automatic category."
                    ),
                },
                {
                    "purpose": "Use declared closure tables and explicit status-consumption policies",
                    "entrypoints": [
                        "TrialLedger.layer2.coherence.resolve",
                        "TrialLedger.layer2.coherence.close",
                        "TrialLedger.layer2.coherence.accepted_value",
                        "TrialLedger.layer2.coherence.level_status",
                        "TrialLedger.layer2.coherence.weakest",
                    ],
                    "precondition": (
                        "Supply typed evidence and applicable Assignment/custom Relation tables. "
                        "accepted_value(row,accepts) permits known or known+interpolated, never "
                        "proposals. reason coordinates uses the existing NSCLC table; it does not accept "
                        "a new rule table."
                    ),
                },
                {
                    "purpose": "Configure typed corpus calculations and element identities directly",
                    "entrypoints": [
                        "TrialLedger.layer2.profile.element_key",
                        "TrialLedger.layer2.profile.frequency_rows",
                        "TrialLedger.layer2.profile.mechanism_rows",
                        "TrialLedger.layer2.profile.occupancy_rows",
                        "TrialLedger.layer2.nearmiss.near_misses",
                    ],
                    "precondition": (
                        "Supply the documented typed tuple shapes. Python frequency_rows accepts "
                        "standard_share; mechanism_rows accepts min_trials/min_sponsors. reason corpus "
                        "uses the module's declared defaults, not request-supplied clinical thresholds."
                    ),
                },
                {
                    "purpose": "Classify an already established observation's deviation status",
                    "entrypoints": [
                        "TrialLedger.layer2.expectations.deviation_status",
                        "TrialLedger.layer2.expectations.conditional_rarity",
                    ],
                    "precondition": (
                        "deviation_status(status,qualifiers,audit) requires a supplied documented "
                        "observation state, count of supported qualifiers and separate audit outcome. It "
                        "returns named invalid_audit/invalid_status/invalid_qualifiers for malformed "
                        "inputs, or "
                        "invalid_extraction/not_applicable/scope_unresolved/conforms/omission/explanation_supported/verified_deviation."
                        " It does not read text, discover expectations or explain an unexplained "
                        "deviation. Historical FROZEN expectation metadata is unconfirmed and is not "
                        "automatically applied by reason."
                    ),
                },
                {
                    "purpose": "Form bounded review questions from unresolved supplied findings",
                    "entrypoints": ["TrialLedger.layer2.review.flags_for"],
                    "precondition": (
                        "Supply drugs/classes, coordinate domains/causes, observation statuses, known "
                        "class choices and explicit abbreviation evidence. Returns kind, element, reason,"
                        " priority, evidence, question and options; it resolves nothing and does not "
                        "consume an answer."
                    ),
                },
                {
                    "purpose": "Evaluate source-grounded claims and record declared type coverage",
                    "entrypoints": [
                        "TrialLedger.layer2.evaluation.gold_problems",
                        "TrialLedger.layer2.evaluation.judge",
                        "TrialLedger.layer2.evaluation.recall",
                        "TrialLedger.layer2.evaluation.precision",
                        "TrialLedger.layer2.evaluation.unit_rates",
                        "TrialLedger.layer2.evaluation.complete_representation",
                        "TrialLedger.layer2.evaluation.parameter_accuracy",
                        "TrialLedger.layer2.evaluation.threshold_verdict",
                        "TrialLedger.layer2.typematrix.study_coordinates",
                        "TrialLedger.layer2.typematrix.declared_manifest",
                        "TrialLedger.layer2.typematrix.manifest_problems",
                    ],
                    "precondition": (
                        "Supply separate annotation levels, original text, versioned gold/emitted claims "
                        "and explicit review judgments. Missing denominators stay not_measured. "
                        "Threshold/coverage policy is developer data, not a clinical correctness warrant "
                        "or a limit on layer-one reporting across study types."
                    ),
                },
            ],
        },
        "examples": _examples(),
        "example_results": {
            "entailment": "REFUTED, proof population",
            "coordinates": "default advanced_first_line remains interpolated",
            "corpus": "statement rate 0.5; full-criteria interval [0.5, 1.0]",
        },
    }


def _describe(request: dict[str, Any]) -> dict[str, Any]:
    """Discover just the next operation, or explicitly request the complete reference guide."""
    _input(request, "describe", "request")
    view = request.get("view", "overview")
    views = DISCOVERY_VIEWS
    if not isinstance(view, str) or view not in views:
        raise RequestError("request.view:unsupported_view")
    detail = request.get("detail", "card")
    if not isinstance(detail, str) or detail not in ("card", "schema", "full"):
        raise RequestError("request.detail:unsupported_detail")
    if view == "prepare":
        from TrialLedger.layer2.request_preparation import card

        return card(schema=detail == "schema")
    if view == "protocol":
        from TrialLedger.layer2.request_preparation import protocol_card

        return protocol_card(detail=detail)
    if view not in ("full", "worked_session") and (detail != "full" or view == "delivery"):
        from TrialLedger.reasoning_cards import describe_card

        card = describe_card(view, schema=detail == "schema")
        if card is not None:
            return card
    full = _full_description()
    full["preparation"] = {
        "meaning": "Typed construction only, not a clinical reasoning operation. "
        "No Python builder is needed.",
        "discovery": {"operation": "describe", "view": "prepare"},
        "next": "Inspect request, defaults and origins, "
        "then run the returned request to compute consequences.",
    }
    full["input_shapes"]["prepare"] = deepcopy(request_preparation.INPUTS["prepare"])
    full["examples"]["prepare"] = request_preparation.example()
    full["example_results"]["prepare"] = "Typed construction only; no clinical answer computed."
    full["result_guides"]["prepare"] = {
        "fields": {
            "request": "Exact runnable expanded request; not computed yet.",
            "defaults": "Applied defaults with exact pointers and values in this preparation result.",
            "origins": "Complete supplied criterion origins; "
            "caller declarations, not authenticated confirmation.",
            "limits_of_claim": "Structural construction only; "
            "execute the expanded request to check consequences.",
        }
    }
    bounds_guide.extend(full)
    signals_guide.extend(full)
    interpretations_guide.extend(full)
    source_assertions_guide.extend(full)
    design_session_guide.extend(full)
    evidence_requests_guide.extend(full)
    full["result_guides"]["envelope"]["summary"] = "Short discovery or operation summary; no new premises."
    full["result_guides"]["reasoning_envelope"] = {
        **full["result_guides"]["envelope"],
        "clinical": "Operation-aware findings with canonical paths, scope, support and origin.",
        "result_digest": "SHA256 of canonical result only, returned on completion.",
        "result_digest_scope": "Excludes summary, presentation, artifact and other envelope metadata.",
    }
    full["result_guides"]["entailment"]["fields"]["explanations"] = {
        "permissions": "Scoped accepted or withheld mentions; permission never requires presence.",
        "conditions": "Solver-proved necessary conditions for an otherwise feasible query, with warrants.",
        "checks": "Bounded additional explanation checks, separate from the original decision.",
        "blockers": "Exact limits or unresolved explanation support; not a clinical negative.",
    }
    full["exception_example"] = exception_guide.example()
    full["response_metadata"] = {
        "location": "Every reason envelope has additive metadata; original clinical results remain intact.",
        "version": 1,
        "kinds": ["reasoning", "discovery", "inspection", "refusal"],
        "dispositions": sorted(result_semantics.DISPOSITIONS),
        "finding_fields": [
            "path",
            "kind",
            "logical_result",
            "standing",
            "completion",
            "causes",
            "disposition",
        ],
        "meaning": (
            "Each finding points to its actual result using a JSON pointer. Read the effective result and "
            "its warrant; raw_result/raw_path retain an ungated calculation when different. Completion "
            "and support are independent: a resource limit is unfinished computation, not missing evidence. "
            "Unknown reasoning causes remain unclassified. Refused requests are invalid translation "
            "tasks, unsupported operations, or computation-limited work; their exact codes remain. "
            "Completed corpus descriptions are descriptive, not clinical decisions. No metadata field "
            "establishes source truth or makes an "
            "open question a clinical choice. Discovery and empty source inspection have no clinical "
            "findings."
        ),
    }
    if view == "full":
        return full
    common = {key: full[key] for key in ("basis", "availability", "limits", "premise_status")}
    common["discovery"] = {name: {"operation": "describe", "view": name} for name in views}
    common["response_metadata"] = full["response_metadata"]
    if view == "overview":
        common["response_metadata"] = "Per-finding status; details in the focused describe guides."
        return common | {
            "clinical_use": (
                "TrialLedger does not make the person's clinical decisions; it finds them. Help the person "
                "explore what other trials documented, make each design choice precise, check its "
                "consequences and revise it, keeping a decision list of each choice with its evidence and "
                "computed consequences (decision_list below). You read the saved evidence and prepare "
                "agreed comparison features or premises; the operations compute over them. Read the focused "
                "guide, run the appropriate operation and explain the deciding basis and open choices. "
                "Update the premises and rerun when a choice changes; save the list and request/result "
                "pairs separately when file access permits. The person makes the clinical judgments. "
                "The source bridge compiles named structured fields and anchors hypothetical readings; "
                "general automatic text compilation and complete protocol generation remain unintegrated."
            ),
            "decision_list": full["answer_guide"]["decision_list"],
            "use_cases": [
                {key: case[key] for key in ("question", "operation")} for case in full["use_cases"]
            ],
            "input_shapes": {"describe": full["input_shapes"]["describe"]},
        }
    if view == "worked_session":
        return common | {"worked_session": full["worked_session"]}
    shapes = {
        "entailment": ("entailment", "context"),
        "coordinates": ("coordinates", "evidence", "standing"),
        "corpus": ("corpus", "trial", "coverage", "expectation", "standing"),
        "design_bounds": ("design_bounds", "candidate", "observation", "bridge", "context"),
        "signals": ("signals", "signal", "support"),
        "interpretations": (
            "interpretations",
            "interpretation_floor",
            "interpretation",
            "interpretation_query",
            "interpretation_binding",
            "interpretation_binding_use",
            "signal",
            "support",
            "context",
        ),
        "source_assertions": (
            *source_assertions_guide.INPUTS,
            "interpretation_query",
            "interpretation_binding_use",
            "signal",
            "support",
            "context",
        ),
        "design_session": tuple(design_session_guide.INPUTS),
        "evidence_requests": (*evidence_requests_guide.INPUTS, "candidate", "context"),
    }[view]
    vocabulary = {
        "entailment": tuple(
            key
            for key in full["vocabularies"]
            if key not in {"sections", "scopes", "coordinate_values", "coverage_states", "observation_states"}
        ),
        "coordinates": ("sections", "scopes", "coordinate_values", "statuses", "resolutions"),
        "corpus": ("coverage_states", "observation_states", "statuses", "resolutions"),
        "signals": ("statuses", "resolutions"),
        "interpretations": (
            "statuses",
            "resolutions",
            "modalities",
            "subject_kinds",
            "predicate_kinds",
            "value_kinds",
        ),
        "source_assertions": (
            "statuses",
            "resolutions",
            "modalities",
            "subject_kinds",
            "predicate_kinds",
            "value_kinds",
        ),
        "design_session": ("statuses", "resolutions"),
        "evidence_requests": ("statuses", "resolutions", "value_kinds"),
        "design_bounds": (
            "statuses",
            "resolutions",
            "modalities",
            "subject_kinds",
            "predicate_kinds",
            "value_kinds",
        ),
    }[view]
    result = common | {
        "operation": view,
        "input_shapes": {key: full["input_shapes"][key] for key in shapes},
        "vocabularies": {key: full["vocabularies"][key] for key in vocabulary},
        "result_guide": full["result_guides"][view],
        "answer_guide": {
            key: full["answer_guide"][key]
            for key in (
                "roles",
                "categories",
                "standing",
                view,
                "decision_list",
                "confirmation",
                "computation",
            )
        },
        "example": full["examples"][view],
        "example_result": full["example_results"][view],
    }
    if view in ("entailment", "design_bounds", "interpretations", "source_assertions", "evidence_requests"):
        result["tagged_model"] = full["tagged_model"]
    if view in ("signals", "design_bounds", "interpretations", "source_assertions"):
        result["operator_inputs"] = full["operator_inputs"]
        result["signal_kinds"] = full["signal_kinds"]
        result["signal_examples"] = full["signal_examples"]
    if view == "design_bounds":
        result["exception_example"] = full["exception_example"]
        for key in exception_guide.INPUTS:
            result["input_shapes"][key] = full["input_shapes"][key]
        for key in signals_guide.INPUTS:
            result["input_shapes"][key] = full["input_shapes"][key]
    if view in ("signals", "design_bounds"):
        result["binding_example"] = full["binding_example"]
        for key in ("interpretation_binding", "interpretation_binding_use"):
            result["input_shapes"][key] = full["input_shapes"][key]
    if view == "corpus":
        result["capability_examples"] = full["capability_examples"]
        result["answer_guide"]["notable"] = full["answer_guide"]["notable"]
    if view == "design_session":
        result["revision_example"] = deepcopy(design_session_guide.REVISION_EXAMPLE)
        result["tagged_model"] = full["tagged_model"]
    return result


def run(request: object) -> dict[str, Any]:
    """Run one existing symbolic operation, or return a named refusal for malformed/unsupported input."""
    from TrialLedger.clinical_delivery import augment

    operation = request.get("operation") if isinstance(request, dict) else None
    try:
        if not isinstance(request, dict):
            raise RequestError("request_not_an_object")
        if operation not in OPERATIONS:
            raise RequestError("unsupported_operation")
        if operation == "design_session":
            response = design_session.run(request, execute=run)
            response["metadata"] = result_semantics.metadata(operation, response["result"])
            return augment(response)
        function = {
            "describe": _describe,
            "prepare": request_preparation.prepare,
            "entailment": _entailment,
            "coordinates": _coordinates,
            "corpus": _corpus,
            "design_bounds": _design_bounds,
            "evidence_requests": evidence_requests.evaluate,
            "signals": _signals,
            "interpretations": _interpretations,
            "source_assertions": _source_assertions,
        }[operation]
        result = function(request)
        response = {
            "code": "complete",
            "operation": operation,
            "result": result,
            "problems": [],
            "metadata": result_semantics.metadata(operation, result),
        }
        if operation == "evidence_requests":
            maximum = request.get("limits", {}).get(
                "max_response_bytes", evidence_requests.LIMITS["max_response_bytes"][0]
            )
            encoded = json.dumps(
                response, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode()
            if len(encoded) > maximum:
                raise RequestError("resource_bound:evidence_requests:response_bytes")
        return augment(response)
    except (ValueError, TypeError, KeyError, RecursionError, OverflowError) as error:
        response = {
            "code": "refused",
            "operation": operation if isinstance(operation, str) else "",
            "result": None,
            "problems": [str(error)],
            "metadata": result_semantics.metadata(
                operation if isinstance(operation, str) else "", None, [str(error)]
            ),
        }
        if isinstance(error, design_session.SessionBudgetError):
            response["diagnostics"] = error.diagnostics
        return augment(response)
