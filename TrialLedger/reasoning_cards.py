"""Small task cards over the existing reasoning contracts; full manuals stay on demand.

Cards contain navigation and wording guidance, never clinical premises. Schema view
publishes structural field contracts; owner validation still checks cross-field
constraints, identity, standing and resource limits.
"""

from __future__ import annotations

import dataclasses
from copy import deepcopy
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from TrialLedger.layer2 import assertions

TASKS = {
    "entailment": (
        "Does our draft require or rule out this patient profile?",
        (
            "Keep the decision, deciding premise ids, standing and blockers together. Check only the "
            "represented restrictions."
        ),
        (
            "Read explanations.permissions as scoped mentions, never requirements or overrides of "
            "exclusions. A proved necessary condition says what must hold IF the queried profile "
            "fits; it does not prove the whole profile fits."
        ),
    ),
    "coordinates": (
        "What treatment setting do these NSCLC criteria imply?",
        (
            "Use the explicit nsclc domain. Report explicit narrowing, overridable defaults, "
            "proposals and each input's actual effect separately."
        ),
        (
            "An accepted input can be inactive, redundant or have no consumer. A setting word alone "
            "does not establish progression or maintenance equivalence."
        ),
    ),
    "corpus": (
        "How common is this criterion among the trials we chose?",
        (
            "Agree the comparison set and represented features first. Report stating trials, "
            "denominator, silence range and support."
        ),
        (
            "Counts and a numerical tier describe this declared set; they do not establish a clinical"
            " standard, requirement or recommendation."
        ),
    ),
    "design_bounds": (
        "What do observed participants rule out about thin eligibility text?",
        (
            "Declare candidate designs, typed count witnesses and the eligibility bridge, including "
            "its maximum exceptions and standing."
        ),
        (
            "Keep count intervals, denominator, population, time and exception cap beside every "
            "elimination. Surviving the declared family does not recover the actual protocol; "
            "separate observations never sum automatically."
        ),
    ),
    "signals": (
        "Can partial tables or definitions bound something not reported directly?",
        (
            "Choose the relevant typed operator and retain sources, population/definition bindings, "
            "standing and any unresolved application."
        ),
        (
            "Equal totals or similar labels do not establish sameness. A permitted pathway does not "
            "establish actual progression. Raw arithmetic can stay visible while its design "
            "consequence is withheld."
        ),
    ),
    "interpretations": (
        "What would each reading allow, and what rules it out?",
        (
            "Keep accepted fixed premises separate from each rival frame. Report fixed answers, each "
            "frame's conditional consequences and the remaining distinction."
        ),
        (
            "Compatible means consistent with represented constraints, not true or preferred. "
            "Proposed premises may be explored inside their named frame; ordinary entailment still "
            "refuses them."
        ),
    ),
    "source_assertions": (
        "Use this retained NIH record without turning a reading into a fact.",
        (
            "Supply the complete raw study. Structured minimum/maximum age have direct rules; exact "
            "anchors locate other evidence and preserve proposed readings."
        ),
        (
            "An exact quotation establishes its source location, not its clinical meaning. Empty "
            "queries inspect admission only. Use returned study_ref and digest rather than "
            "constructing snapshot identity."
        ),
    ),
    "evidence_requests": (
        "What evidence would distinguish the surviving explanations?",
        (
            "Supply declared survivors, their selection basis and bounded dimensions. Read the "
            "accepted/rejected sign, attribution conditions and place to investigate."
        ),
        (
            "These are hypothetical investigation requests, never observed participants. A partial "
            "rejection needs an ineligible completion; it does not exclude every matching person."
        ),
    ),
    "design_session": (
        "Keep our evidence, choices and consequences together; what changes if we revise?",
        (
            "Use the source/premise ledger, named projections, analyses and decision alternatives. "
            "Preserve origins and coverage; replay both complete snapshots for a revision."
        ),
        (
            "Use answer_diff for independent answer/support/origin changes and diff for audit-object "
            "changes. A computation limit is a computation task, not evidence of absence or design "
            "freedom. Caller origin labels do not authenticate confirmation."
        ),
    ),
}

SHAPES = {
    "entailment": ("entailment", "context"),
    "coordinates": ("coordinates", "evidence", "standing"),
    "corpus": ("corpus", "trial", "coverage", "expectation", "standing"),
    "design_bounds": (
        "design_bounds",
        "candidate",
        "observation",
        "bridge",
        "derived_observation",
        "derivation",
        "context",
    ),
    "signals": ("signals", "signal", "support"),
    "interpretations": (
        "interpretations",
        "interpretation_floor",
        "interpretation",
        "interpretation_query",
        "interpretation_binding",
        "interpretation_binding_use",
        "context",
    ),
    "source_assertions": (
        "source_assertions",
        "source_anchor",
        "source_span",
        "source_template",
        "source_interpretation",
        "source_binding",
        "interpretation_query",
        "context",
    ),
}

CONTAINERS = {
    "assertions": "array",
    "query": "object",
    "context": "object",
    "bound": "integer",
    "domain": "string",
    "evidence": "array",
    "trials": "array",
    "cells": "array",
    "expectations": "array",
    "study_ref": "string",
    "candidates": "array",
    "observations": "array",
    "signals": "array",
    "exception_evidence": "object",
    "bindings": "array",
    "binding_uses": "array",
    "fixed": "object",
    "interpretations": "array",
    "queries": "array",
    "selected": ["string", "null"],
    "study": "object",
    "expected_digest": "string",
    "anchors": "array",
    "survivors": "array",
    "survival_basis": "array",
    "variables": "array",
    "signs": "array",
    "limits": "object",
    "session": "object",
    "previous": ["object", "null"],
}

MODEL_VOCABULARIES = {
    ("Evidence", "kind"): assertions.EVIDENCE_KINDS,
    ("Subject", "kind"): assertions.SUBJECT_KINDS,
    ("Predicate", "kind"): assertions.PREDICATE_KINDS,
    ("Value", "kind"): assertions.VALUE_KINDS,
    ("Value", "comparison"): assertions.COMPARISONS,
    ("Value", "inclusivity"): assertions.INCLUSIVITIES,
    ("TemporalScope", "orientation"): assertions.ORIENTATIONS,
    ("TemporalScope", "anchor"): assertions.ANCHOR_KINDS,
    ("TemporalScope", "inclusivity"): assertions.INCLUSIVITIES,
    ("TemporalScope", "certainty"): assertions.CERTAINTIES,
    ("Literal", "polarity"): assertions.POLARITIES,
    ("Scope", "kind"): assertions.SCOPE_KINDS,
    ("Branch", "node"): assertions.BRANCH_NODES,
    ("ScopedAssertion", "modality"): assertions.MODALITIES,
    ("ScopedAssertion", "status"): assertions.STATUSES,
    ("ScopedAssertion", "resolution"): assertions.RESOLUTIONS,
}


def _type_schema(annotation: object) -> dict[str, Any]:
    """Reflect the canonical model's declared containers without adding semantics."""
    origin, arguments = get_origin(annotation), get_args(annotation)
    if origin in (Union, UnionType):
        return {"anyOf": [_type_schema(part) for part in arguments]}
    if origin is tuple:
        return {"type": "array", "items": _type_schema(arguments[0])}
    if annotation is type(None):
        return {"type": "null"}
    primitives: dict[type, str] = {str: "string", int: "integer", float: "number", bool: "boolean"}
    if isinstance(annotation, type) and annotation in primitives:
        return {"type": primitives[annotation]}
    if isinstance(annotation, type) and annotation in assertions.CLASSES.values():
        return {"$ref": f"#/$defs/{annotation.__name__}"}
    raise TypeError(f"undocumented_model_annotation:{annotation}")


def _model_schemas() -> dict[str, Any]:
    definitions: dict[str, Any] = {}
    for name, cls in assertions.CLASSES.items():
        properties: dict[str, Any] = {"class": {"const": name}}
        required = ["class"]
        hints = get_type_hints(cls)
        for field in dataclasses.fields(cls):
            shape = _type_schema(hints[field.name])
            vocabulary = MODEL_VOCABULARIES.get((name, field.name))
            if vocabulary is not None:
                shape["enum"] = sorted(vocabulary)
            properties[field.name] = shape
            if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
                required.append(field.name)
        definitions[name] = {
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": required,
        }
    return definitions


def _contracts(view: str) -> dict[str, Any]:
    from TrialLedger.layer2 import design_session_guide, evidence_requests_guide, service

    if view == "design_session":
        return deepcopy(design_session_guide.INPUTS)
    if view == "evidence_requests":
        return {
            **deepcopy(evidence_requests_guide.INPUTS),
            **{key: deepcopy(service.INPUTS[key]) for key in ("candidate", "context")},
        }
    return {name: deepcopy(service.INPUTS[name]) for name in SHAPES[view]}


def _request_schema(view: str, contracts: dict[str, Any]) -> dict[str, Any]:
    shape = contracts[view]
    properties: dict[str, Any] = {"operation": {"const": view}}
    for key, description in shape["fields"].items():
        if key == "operation":
            continue
        properties[key] = {
            "description": str(description),
            **({"type": CONTAINERS[key]} if key in CONTAINERS else {}),
        }
    if view == "entailment":
        properties["assertions"]["items"] = {"$ref": "#/$defs/ScopedAssertion"}
        properties["query"] = {
            "anyOf": [{"$ref": f"#/$defs/{cls.__name__}"} for cls in assertions.PROPOSITIONS]
        }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"TrialLedger {view} structural request",
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": sorted({"operation", *shape["required"]}),
        "$defs": _model_schemas(),
        "description": (
            "Structural schema only. The operation owner additionally validates cross-field "
            "constraints, source identities, scope, standing, admission and resource limits. Named "
            "nested contracts are supplied beside this schema; schema acceptance is not proof of "
            "factual premises."
        ),
    }


def _example(view: str) -> dict[str, Any]:
    """Reuse only the requested owner's invented input; never compute example results."""
    from TrialLedger.layer2 import (
        bounds_guide,
        design_session_guide,
        evidence_requests_guide,
        interpretations_guide,
        service,
        signals_guide,
        source_assertions_guide,
    )

    factories = {
        "design_bounds": bounds_guide.example,
        "signals": signals_guide.example,
        "interpretations": interpretations_guide.example,
        "source_assertions": source_assertions_guide.example,
        "evidence_requests": evidence_requests_guide.example,
    }
    if view in factories:
        return factories[view]()
    if view == "design_session":
        return deepcopy(design_session_guide.EXAMPLE)
    return service._examples()[view]


def describe_card(view: str, *, schema: bool = False) -> dict[str, Any] | None:
    """Return one small task card or explicit structural schemas; never build the full manual."""
    if view == "prepare":
        from TrialLedger.layer2.request_preparation import card

        return card(schema=schema)
    if view == "overview":
        return {
            "detail": "card",
            "clinical_use": (
                "Gather the evidence, settle material readings, compute consequences, revise choices, "
                "deliver the decision list."
            ),
            "operations": [
                {
                    "operation": "prepare",
                    "kind": "preparation",
                    "question": "Expand compact typed input without computing a clinical answer.",
                },
                *[{"operation": name, "question": task[0]} for name, task in TASKS.items()],
            ],
            "discovery": {
                **{name: {"operation": "describe", "view": name} for name in TASKS},
                "prepare": {"operation": "describe", "view": "prepare"},
                "focused": {"operation": "describe", "view": "entailment"},
                "schema": {"operation": "describe", "view": "entailment", "detail": "schema"},
                "full": {"operation": "describe", "view": "full"},
                "delivery": {"operation": "describe", "view": "delivery"},
            },
            "boundaries": [
                (
                    "Source facts, accepted premises, overridable defaults and proposed readings "
                    "keep their origins."
                ),
                "Silence is not absence. Corpus counts describe and never decide.",
                "General prose compilation and complete protocol writing remain unintegrated.",
            ],
            "preparation": "Use describe view prepare for small typed criteria and questions; "
            "inspect its defaults/origins, then execute by retained preparation id without copying "
            "expanded JSON. No Python builder is needed.",
        }
    if view == "delivery":
        from TrialLedger.reasoning_mcp import TOOL_SCHEMAS
        from TrialLedger.retained_sources import SOURCE_CONTRACT

        tools: dict[str, Any] = deepcopy(TOOL_SCHEMAS)
        return {
            "detail": "schema" if schema else "card",
            "operation": "delivery",
            "workflow": [
                (
                    "For routine criteria/options, describe view prepare gives short typed input. "
                    "Retain a successful preparation, then call reason with prepared:ID and no request. "
                    "Its defaults/origins remain inspectable; preparation never confirms a reading."
                ),
                (
                    "reason with retain:true or response_view:compact retains the complete request and "
                    "response separately from source reports."
                ),
                (
                    "reason_result reads decisions, changes or exact addresses; follow every page/text "
                    "continuation needed."
                ),
                (
                    "reason_revise uses the artifact id plus an explicit next session or bounded replacement "
                    "edits with changed-premise origins; both snapshots are recomputed."
                ),
                (
                    "reason_export writes a separate review workbook, readable decision list, canonical "
                    "inputs and manifest; deliver its returned paths."
                ),
            ],
            "cli": [
                "reason --request compact-input.json --store STORE --compact",
                "reason --prepared PREPARATION_ID --store STORE --compact",
                "reason --request FILE --store STORE --compact",
                "reason-result --store STORE --id ID --part decisions",
                "reason-revise --store STORE --id ID --edits FILE --revision LABEL",
                "reason-export --store STORE --id ID --out FOLDER --source-record landscape.json",
            ],
            "tools": tools
            if schema
            else {
                name: {"required": spec["inputSchema"]["required"], "description": spec["description"]}
                for name, spec in tools.items()
            },
            "source_handles": {
                "contract": deepcopy(SOURCE_CONTRACT),
                "read": {"tool": "record", "run": "RUN", "part": "source", "nct": "NCT00000001"},
                "identity": "Use returned snapshot.digest and snapshot.study_ref. "
                "Address is optional and relative to the raw study; follow pages/text unchanged.",
            },
            "boundary": (
                "An artifact hash proves retained identity, not clinical truth or authenticated "
                "confirmation. Compact output has a complete retrievable canonical artifact; no source "
                "report is changed."
            ),
        }
    task = TASKS.get(view)
    if task is None:
        return None
    contracts = _contracts(view)
    card: dict[str, Any] = {
        "detail": "schema" if schema else "card",
        "operation": view,
        "question": task[0],
        "procedure": task[1],
        "boundary": task[2],
        "input": deepcopy(contracts[view]),
        "example_basis": "Invented teaching premises; not a report of an actual trial or human confirmation.",
        "example": _example(view),
        "discover": {
            "schema": {"operation": "describe", "view": view, "detail": "schema"},
            "full": {"operation": "describe", "view": view, "detail": "full"},
        },
    }
    if schema:
        card.update(request_schema=_request_schema(view, contracts), input_shapes=contracts)
    if view == "source_assertions":
        from TrialLedger.retained_sources import SOURCE_CONTRACT

        card["source_handles"] = deepcopy(SOURCE_CONTRACT)
    return card
