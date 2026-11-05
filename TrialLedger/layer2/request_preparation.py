"""Explicit typed JSON conveniences; expansion is not interpretation or reasoning.

Compact atoms and named questions expand into the existing public request format. Every
applied default and supplied criterion origin is returned beside the executable request.
No solver, source reader, consent checker or clinical synonym recognizer is called here.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, cast

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import session_state, source_evidence
from TrialLedger.layer2.entail import MAX_ASSIGNMENTS

INPUTS: dict[str, dict[str, Any]] = {
    "prepare": {
        "required": ("for", "criteria"),
        "fields": {
            "for": "entailment or design_session; typed expansion only, no computation",
            "criteria": "named {id,modality,body,origin}; status defaults proposed, resolution unresolved",
            "query": "required for entailment: compact or canonical proposition",
            "context": "entailment context, or per-question context; omitted leaves cohort/phase/arm open",
            "bound": "entailment solver bound; default 65536, used only when expanded request is run",
            "id": "required for design_session: caller's session identity",
            "target": "required for design_session: existing explicit {kind,ref,scope} target",
            "revision": "design_session revision; default one",
            "sources": "existing source rows, including digest-bound study handles; copied unchanged",
            "questions": "design_session {id,question,options:[{id,label,query}],"
            "criteria?,context?,bound?,selected?,evidence?,coverage?,target?}",
            "analyses": "optional existing canonical additional analyses; no analysis is executed",
            "limits": "optional partial existing session limits; missing limits are disclosed defaults",
            "definition_checks": "optional canonical session definition-link declarations; copied unchanged",
            "protocol": "optional design_session protocol {objects,checks,sections}; makes schema_version "
            "2; shapes and a runnable example: describe view protocol",
        },
    },
    "compact_proposition": {
        "required": (),
        "fields": {
            "canonical": "existing tagged Literal/AllOf/AnyOf/Not/Opaque remains available",
            "compound": "exactly one of {all:[...]}, {any:[...]}, {not:...}; no inferred grouping",
            "literal": "{kind,predicate:{kind,key},subject?,polarity?,time?,qualifiers?,"
            "evidence?,...value fields}",
            "quantity_or_interval": "explicit comparison, number, unit, inclusivity; "
            "interval also requires upper",
            "enum_or_enum_set": "explicit comparison and members; enum and enum_set keep different meanings",
            "boolean": "no number or members; positive or negative polarity states whether it holds",
        },
    },
    "compact_criterion": {
        "required": ("id", "modality", "body", "origin"),
        "fields": {
            "id": "nonempty unique criterion id",
            "modality": "required, excluded, permitted, definitional, descriptive or unresolved; "
            "never guessed",
            "body": "compact or canonical proposition",
            "origin": "{kind,ref,source?,analysis?}; structured origin is retained, never authenticated",
            "status": "known, interpolated or proposed; omitted is proposed",
            "resolution": "resolved, partially_resolved, unresolved or conflicting; omitted is unresolved",
            "criterion_ref": "explicit source/adoption citation; defaults to caller origin.ref",
            "applicability": "compact/canonical condition; default Always",
            "cohort": "compact/canonical Scope; default all_participants",
            "rule": "existing Rule; default explicitly identifies caller declaration, not source deduction",
            "branch": "existing Branch; default unresolved",
            "span": "existing Span objects; default []",
        },
    },
}
PROTOCOL_DATA = {
    "standing_ref": "{ref,version,status,resolution,basis}: an attributed versioned reference, not "
    "verified truth",
    "measurement": "{definition:standing_ref, unit:string|null, mode:observed|imputed|derived, "
    "baseline:measurement id|null}",
    "endpoint": "{variable:measurement id, definition:standing_ref, estimand:estimand id|null, "
    "dependencies:null|the dependencies operator data (see operator_inputs)}",
    "estimand": "exactly the estimand operator data (see operator_inputs.estimand)",
    "assessment": "{measurement:measurement id, anchor:event id, unit:string, nominal:rational string|null, "
    "permitted:interval union|null, condition:proposition|null}",
    "collection": "{assessment:assessment id, mode:observed|imputed|derived, availability:interval "
    "union|null (null unknown, [] none planned), event_handling:null|{estimand:estimand object id, "
    "requirement:that estimand's requirement id, action:collect|stop}}",
    "efficacy": "{endpoint:endpoint id, method:binomial_design|external_method, parameters:"
    "{model,direction,n,critical_count,p0,p1}|external_method id, assumptions:[{role:fixed_n|iid_binary|"
    "alignment, premise:premise id}]}. Roles: fixed_n (the sample size is fixed in advance), iid_binary "
    "(independent, identically distributed binary responses) and alignment (the population, endpoint and "
    "analysis set correspond to the modelled Bernoulli response); all three are needed for application",
    "policy": "{model:the finite_policy operator data (see operator_inputs.finite_policy), bindings:"
    "[{variable:model variable id, object:object id|null, premise:premise id|null}] (exactly one non-null)}. "
    "External variables are re-chosen at every step from the feasible valuations: an invariant over them can "
    "only hold if it follows from the constraints for that state; keep memory in states",
    "external_method": "{definition:standing_ref, inputs:[{name,value:string|null,unit:string|null,"
    "ref:object or premise id|null}], missing:[input names]}",
    "interval_union": "[{lower,upper,lower_inclusive,upper_inclusive}]; rational strings or null (infinite, "
    "never inclusive)",
}
PROTOCOL_CHECKS = {
    "schedule": "objects: exactly one assessment and its collection; claims [{id,claim:existence|nominal|"
    "full_window}]",
    "finite_policy": "objects: exactly one policy; claims [{id,claim:coverage|exclusivity|prohibition|"
    "invariant|termination,witness_limit:0-64}]",
    "binomial_design": "objects: one binomial_design efficacy and its endpoint; claims [{id,quantity:"
    "null_rejection_probability|power,comparison:<=|>=,value}] or []",
    "estimand": "objects: exactly one estimand; claims []",
    "dependencies": "objects: one endpoint with non-null dependencies; claims []",
    "external_method": "objects: an external_method efficacy and its external_method, or the external_method "
    "alone; claims []",
    "temporal / decision_table": "bindings: exactly one {projection:temporal_request|decision_table_request, "
    "data:<that operator's data>}; objects optional",
    "condition_applicability binding": "{projection:condition_applicability, premises:[assertion premise "
    "ids]}; decides a declared assessment condition (otherwise findings stay conditional)",
}
PROTOCOL_DECISIONS = {
    "shape": "protocol.decisions: [{id, question, alternatives:[{id, label, replace?: [compact objects with "
    "existing ids, same kind], checks:[check ids]}], selected?: {alternative, origin:user, basis:[refs]}}]",
    "rules": "every alternative lists every required check; optional checks must be identical across "
    "alternatives; an empty replace is the baseline as declared; a replacement is a hypothetical frame "
    "(withheld from unconditional application, never reported as known)",
    "results": "result.protocol.decisions: per alternative compatible / repair_choice_open / undetermined / "
    "incompatible under the declared checks; disposition blocker (selected incompatible), repair_choice, "
    "design_choice, evidence_question, settled_within_declared_alternatives or no_compatible_alternative",
}
PROTOCOL_NOTES = {
    "ids": "references inside data (variable, estimand, assessment, endpoint, measurement) are protocol "
    "OBJECT ids, not an estimand's own data.id",
    "source_interpretation_origin": "origin {kind:source_interpretation, ref:<session source snapshot "
    "study_ref>#<RFC6901 pointer into that study>, source:<session source id>}",
    "external_method": "inputs and missing are disjoint by name; list every input you cannot supply in "
    "missing (a null-valued input is not treated as missing)",
    "event_handling": "declared once, on the collection: {estimand, requirement, action}. The estimand check "
    "takes that requirement's collection plan from the linked collection (with its standing); a differing "
    "action in the estimand's own data is a named collection_plan_conflict, never an override",
    "adoption": "support premises are the caller's attribution of adoption; the tool does not judge whether "
    "a premise is clinically about the object",
    "raw_vs_effective": "operator values keep raw outcomes; claim_admission.effective_outcome is what may be "
    "applied (unresolved when support is refused)",
    "retained_study": 'a source study handle is {"$retained_study": {run, nct, digest}}; all three are '
    "required, and validation is deferred to execution where the handle is hydrated",
}
PROTOCOL_ADMISSION = (
    "An object's own standing and its adoption support are conjunctive (C3): support premises record "
    "adoption, "
    "and the object's own standing (default proposed/unresolved) must also be declared known (or "
    "interpolated) and resolved before its findings are admitted. Check-wide support applies to every claim. "
    "Each check's operator inputs are parsed at admission without computing (for example 0 <= p0 < p1 <= 1, "
    "0 <= critical_count <= n + 1, and 1 to 16 binomial assumptions); a malformed input refuses "
    "preparation and the run alike as protocol_check_input:<check id>:<operator code>."
)
PROTOCOL_INPUTS = {
    "compact_protocol_object": {
        "required": ("id", "kind", "version", "origin", "data"),
        "fields": {
            "id": "unique protocol object id",
            "kind": "measurement, endpoint, estimand, assessment, collection, efficacy, policy or "
            "external_method",
            "version": "declared definition edition; never inferred from the draft revision",
            "origin": "{kind,ref,source?}; user_choice, hypothesis or source_interpretation; never defaulted",
            "data": "the kind's closed canonical payload (operator reference); an assessment condition "
            "may be a compact or canonical proposition",
            "standing": "{status,resolution,basis}; default proposed/unresolved/[origin.ref] (disclosed)",
            "support": "premise ids adopting this object; default [] (adoption stays unresolved)",
            "depends_on": "default: exactly the object ids named inside data (mechanical, disclosed)",
            "scope": "{target,context}; default the session target with an open cohort/phase/arm (disclosed)",
        },
    },
    "compact_protocol_check": {
        "required": ("id", "kind", "objects", "required"),
        "fields": {
            "id": "unique check id",
            "kind": "schedule, finite_policy, binomial_design, estimand, dependencies, temporal, "
            "decision_table, definition or external_method",
            "objects": "declared object ids this check consumes",
            "required": "explicit boolean; never defaulted (it decides which alternatives must include it)",
            "claims": "the check's explicit obligations (operator reference); required for schedule and "
            "finite_policy; default [] for others (disclosed)",
            "bindings": "named projection records, e.g. {projection:condition_applicability,premises:[...]}; "
            "default []",
            "support": "check-wide premise ids; default []",
            "scope": "default the session target with an open cohort/phase/arm (disclosed)",
        },
    },
    "compact_protocol_section": {
        "required": ("id", "state"),
        "fields": {
            "id": "population, eligibility, interventions, endpoints, assessments, efficacy, safety or "
            "exploratory",
            "state": "requested or not_applicable; omitted sections are not_requested",
            "objects": "relevant object ids; default []",
            "basis": "attributed references; required nonempty for not_applicable; default []",
        },
    },
}
LIMITS_OF_CLAIM = (
    "Typed structural expansion only: no clinical answer, source-truth check or person confirmation.",
    "Run the returned request through reason to compute its consequences and source admission.",
    "Defaults are explicit in the expansion and defaults list; "
    "revise any that do not match the intended meaning.",
    "Origins are caller declarations; status never becomes known or resolved merely through preparation.",
)


def compact_node_code(keys: list[str]) -> str:
    """Choose a declared syntax branch without interpreting a predicate (pure).

    post: __return__ in ('canonical', 'all', 'any', 'not', 'literal', 'invalid_compound', 'invalid_node')
    post: __return__ not in ('all', 'any', 'not') or len(keys) == 1
    """
    if "class" in keys:
        return "canonical"
    compounds = [key for key in keys if key in ("all", "any", "not")]
    if compounds:
        return compounds[0] if len(keys) == 1 else "invalid_compound"
    return "literal" if "kind" in keys else "invalid_node"


def _fields(value: object, allowed: set[str], required: set[str], where: str) -> dict:
    if type(value) is not dict:
        raise ValueError("not_an_object:" + where)
    if set(value) - allowed:
        raise ValueError("unknown_field:" + where)
    if required - set(value):
        raise ValueError("missing_field:" + where)
    return value


def _rows(value: object, maximum: int, where: str) -> list:
    if type(value) is not list:
        raise ValueError("not_a_list:" + where)
    if len(value) > maximum:
        raise ValueError("resource_bound:prepare:" + where)
    return value


def _text(value: object, where: str) -> str:
    if type(value) is not str or not value:
        raise ValueError("not_text:" + where)
    return value


def _pointer(path: str, key: str | int) -> str:
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _default(ledger: list, path: str, value: object) -> object:
    ledger.append({"path": path, "value": deepcopy(value)})
    return deepcopy(value)


def _take(raw: dict, key: str, value: object, path: str, defaults: list) -> object:
    return raw[key] if key in raw else _default(defaults, _pointer(path, key), value)


def _added_defaults(before: object, after: object, path: str, defaults: list) -> None:
    if isinstance(before, dict) and isinstance(after, dict):
        for key, value in after.items():
            child = _pointer(path, key)
            if key not in before:
                _default(defaults, child, value)
            else:
                _added_defaults(before[key], value, child, defaults)
    elif isinstance(before, list) and isinstance(after, list):
        for index, (left, right) in enumerate(zip(before, after, strict=True)):
            _added_defaults(left, right, _pointer(path, index), defaults)


def _model(raw: object, expected: type | tuple[type, ...], path: str, defaults: list) -> dict:
    if type(raw) is not dict:
        raise ValueError("model_object_required:" + path)
    held = a.from_canonical(json.dumps(raw, allow_nan=False))
    if not isinstance(held, expected):
        raise ValueError("wrong_model_class:" + path)
    expanded = json.loads(a.canonical(held))
    _added_defaults(raw, expanded, path, defaults)
    return expanded


def _typed(raw: object, cls: type, path: str, defaults: list) -> dict:
    if type(raw) is not dict:
        raise ValueError("model_object_required:" + path)
    return _model(raw if "class" in raw else {"class": cls.__name__, **raw}, cls, path, defaults)


def _scope(raw: object, path: str, defaults: list) -> dict:
    if type(raw) is not dict:
        raise ValueError("model_object_required:" + path)
    held = deepcopy(cast(dict, raw))
    if "parts" in held:
        held["parts"] = [
            _scope(part, _pointer(_pointer(path, "parts"), index), defaults)
            for index, part in enumerate(_rows(held["parts"], 128, path))
        ]
    return _typed(held, a.Scope, path, defaults)


def _literal(raw: dict, path: str, defaults: list) -> dict:
    common = {"kind", "predicate", "subject", "polarity", "time", "qualifiers", "evidence"}
    fields = {"comparison", "members", "number", "upper", "unit", "inclusivity"}
    kind = raw["kind"]
    required = {"kind", "predicate"}
    if kind in ("quantity", "interval"):
        required |= {"comparison", "number", "unit", "inclusivity"}
        if kind == "interval":
            required.add("upper")
    elif kind in ("enum", "enum_set", "entity_ref", "definition_ref"):
        required |= {"comparison", "members"}
    elif kind not in ("boolean", "unresolved"):
        raise ValueError("unsupported_compact_value_kind:" + path)
    _fields(raw, common | fields, required, path)
    predicate = _typed(raw["predicate"], a.Predicate, _pointer(path, "predicate"), defaults)
    value = _model(
        {"class": "Value", **{key: value for key, value in raw.items() if key in fields | {"kind"}}},
        a.Value,
        _pointer(path, "value"),
        defaults,
    )
    result = {
        "class": "Literal",
        "predicate": predicate,
        "value": value,
        "subject": _typed(
            _take(raw, "subject", {"kind": "participant", "referent": ""}, path, defaults),
            a.Subject,
            _pointer(path, "subject"),
            defaults,
        ),
    }
    for key in ("polarity", "time", "evidence"):
        if key in raw:
            result[key] = (
                _typed(raw[key], a.TemporalScope, _pointer(path, key), defaults)
                if key == "time" and raw[key] is not None
                else raw[key]
            )
    if "qualifiers" in raw:
        result["qualifiers"] = _condition(raw["qualifiers"], _pointer(path, "qualifiers"), defaults)
    return _model(result, a.Literal, path, defaults)


def proposition(raw: object, path: str, defaults: list) -> dict:
    if type(raw) is not dict:
        raise ValueError("model_object_required:" + path)
    held = cast(dict[str, Any], raw)
    code = compact_node_code(list(held))
    if code == "canonical":
        return _model(held, a.PROPOSITIONS, path, defaults)
    if code in ("invalid_compound", "invalid_node"):
        raise ValueError(code + ":" + path)
    if code == "literal":
        return _literal(held, path, defaults)
    if code == "not":
        return {"class": "Not", "part": proposition(held["not"], _pointer(path, "part"), defaults)}
    parts = [
        proposition(part, _pointer(_pointer(path, "parts"), index), defaults)
        for index, part in enumerate(_rows(held[code], 1000, path))
    ]
    return _model(
        {"class": "AllOf" if code == "all" else "AnyOf", "parts": parts}, a.PROPOSITIONS, path, defaults
    )


def _condition(raw: object, path: str, defaults: list) -> dict:
    if isinstance(raw, dict) and raw.get("class") == "Always":
        return _model(raw, a.Always, path, defaults)
    return _model(proposition(raw, path, defaults), a.CONDITIONS, path, defaults)


def _origin(raw: object, path: str, defaults: list) -> dict:
    held = _fields(raw, {"kind", "ref", "source", "analysis"}, {"kind", "ref"}, path)
    kind = held["kind"]
    if kind not in ("user_choice", "source_interpretation", "hypothesis"):
        raise ValueError("unsupported_origin:" + path)
    result = {"kind": kind, "ref": _text(held["ref"], path + "/ref")}
    for field in ("source", "analysis"):
        value = _take(held, field, None, path, defaults)
        if value is not None:
            _text(value, path + "/" + field)
        result[field] = value
    if kind == "source_interpretation" and result["source"] is None:
        raise ValueError("source_interpretation_requires_source")
    if kind in ("user_choice", "hypothesis") and result["source"] is not None:
        raise ValueError("choice_origin_is_not_source_fact")
    if result["analysis"] is not None:
        raise ValueError("derived_analysis_requires_derived_origin")
    return result


def _criterion(raw: object, index: int, defaults: list) -> tuple[dict, dict]:
    path = "/request/assertions/" + str(index)
    shape = INPUTS["compact_criterion"]
    held = _fields(raw, set(shape["fields"]), set(shape["required"]), "criteria/" + str(index))
    origin = _origin(held["origin"], "/origins/" + str(index) + "/origin", defaults)
    identity = _text(held["id"], path + "/id")
    assertion = {
        "class": "ScopedAssertion",
        "id": identity,
        "criterion_ref": _take(held, "criterion_ref", origin["ref"], path, defaults),
        "modality": held["modality"],
        "body": proposition(held["body"], path + "/body", defaults),
        "status": _take(held, "status", "proposed", path, defaults),
        "resolution": _take(held, "resolution", "unresolved", path, defaults),
        "rule": _typed(
            _take(
                held,
                "rule",
                {"id": "typed-request-declaration", "version": "1", "warrants": [origin["ref"]]},
                path,
                defaults,
            ),
            a.Rule,
            path + "/rule",
            defaults,
        ),
    }
    if "applicability" in held:
        assertion["applicability"] = _condition(held["applicability"], path + "/applicability", defaults)
    if "cohort" in held:
        assertion["cohort"] = _scope(held["cohort"], path + "/cohort", defaults)
    if "branch" in held:
        assertion["branch"] = _typed(held["branch"], a.Branch, path + "/branch", defaults)
    if "span" in held:
        assertion["span"] = [
            _typed(span, a.Span, path + "/span/" + str(i), defaults)
            for i, span in enumerate(_rows(held["span"], 1000, path + "/span"))
        ]
    return _model(assertion, a.ScopedAssertion, path, defaults), {"id": identity, "origin": origin}


def _context(raw: object, path: str, defaults: list) -> dict:
    held = _fields(raw, {"cohort", "phase", "arm"}, set(), path)
    context = {}
    for key in ("cohort", "phase", "arm"):
        value = _take(held, key, None, path, defaults)
        if value is not None:
            _text(value, path)
        context[key] = value
    return context


def _bound(raw: object) -> int:
    if type(raw) is not int or not 1 <= raw <= MAX_ASSIGNMENTS:
        raise ValueError("invalid_resource_bound:prepare")
    return raw


def _sources(raw: object) -> list:
    sources, ids = [], set()
    for source in _rows(raw, session_state.HARD_LIMITS["max_sources"], "sources"):
        held = _fields(
            source, {"id", "study", "expected_digest"}, {"id", "study", "expected_digest"}, "source"
        )
        identity = _text(held["id"], "source.id")
        if identity in ids:
            raise ValueError("duplicate_id:source:" + identity)
        ids.add(identity)
        if type(held["study"]) is not dict:
            raise ValueError("not_an_object:source.study")
        _text(held["expected_digest"], "source.expected_digest")
        sources.append(deepcopy(held))
    return sources


def _analyses(raw: object, ids: set[str], sources: set[str]) -> list:
    analyses, seen = [], set()
    for analysis in _rows(raw, session_state.HARD_LIMITS["max_analyses"], "analyses"):
        held = _fields(
            analysis,
            {"id", "operation", "target", "parameters", "uses"},
            {"id", "operation", "target", "parameters", "uses"},
            "analysis",
        )
        identity = _text(held["id"], "analysis.id")
        if identity in seen:
            raise ValueError("duplicate_id:analysis:" + identity)
        seen.add(identity)
        if held["operation"] not in session_state.OPERATIONS:
            raise ValueError("unsupported_analysis:" + identity)
        session_state.target(held["target"])
        if type(held["parameters"]) is not dict or set(held["parameters"]) & (
            session_state.SLOTS | {"operation", "fixed"}
        ):
            raise ValueError("projected_slot_collision:" + identity)
        for use in _rows(held["uses"], 1000, "uses"):
            _fields(use, {"premise", "slot", "projection"}, {"premise", "slot", "projection"}, "use")
            if use["premise"] not in ids | sources:
                raise ValueError("unknown_dependency:" + str(use["premise"]))
            if use["slot"] not in session_state.SLOTS:
                raise ValueError("unsupported_projection_slot")
            _text(use["projection"], "use.projection")
        analyses.append(deepcopy(held))
    return analyses


def _questions(raw: object, target: dict, ids: list[str], defaults: list, offset: int) -> tuple[list, list]:
    decisions, analyses, seen = [], [], set()
    for index, question in enumerate(_rows(raw, session_state.HARD_LIMITS["max_decisions"], "questions")):
        path = "/request/session/decisions/" + str(index)
        held = _fields(
            question,
            {
                "id",
                "question",
                "options",
                "criteria",
                "context",
                "bound",
                "selected",
                "evidence",
                "coverage",
                "target",
            },
            {"id", "question", "options"},
            "question",
        )
        identity = _text(held["id"], "question.id")
        if identity in seen:
            raise ValueError("duplicate_id:question:" + identity)
        seen.add(identity)
        uses = _rows(held.get("criteria", ids), 1000, "question.criteria")
        for ref in uses:
            _text(ref, "question.criteria")
        if len(set(uses)) != len(uses) or any(ref not in ids for ref in uses):
            raise ValueError("unknown_or_duplicate_question_criterion:" + identity)
        selected_target = deepcopy(_take(held, "target", target, path, defaults))
        session_state.target(selected_target)
        alternatives = []
        for option_index, option in enumerate(_rows(held["options"], 16, "options")):
            option = _fields(option, {"id", "label", "query"}, {"id", "label", "query"}, "option")
            option_id = _text(option["id"], "option.id")
            analysis_id = "question:" + identity + ":option:" + option_id
            query = proposition(
                option["query"], path + "/alternatives/" + str(option_index) + "/query", defaults
            )
            analysis_path = "/request/session/analyses/" + str(offset + len(analyses))
            context = _context(held.get("context", {}), analysis_path + "/parameters/context", defaults)
            bound = _bound(_take(held, "bound", MAX_ASSIGNMENTS, analysis_path + "/parameters", defaults))
            projected = [{"premise": ref, "slot": "assertions", "projection": "identity"} for ref in uses]
            if "criteria" not in held:
                _default(defaults, analysis_path + "/uses", projected)
            analyses.append(
                {
                    "id": analysis_id,
                    "operation": "entailment",
                    "target": deepcopy(selected_target),
                    "parameters": {"query": query, "context": context, "bound": bound},
                    "uses": projected,
                }
            )
            alternatives.append(
                {
                    "id": option_id,
                    "label": _text(option["label"], "option.label"),
                    "analysis": analysis_id,
                    "query": deepcopy(query),
                }
            )
        decision = {
            "id": identity,
            "question": _text(held["question"], "question.question"),
            "target": selected_target,
            "coverage": _take(held, "coverage", "represented_restriction", path, defaults),
            "alternatives": alternatives,
            "selected": _take(held, "selected", None, path, defaults),
        }
        if "evidence" in held:
            decision["evidence"] = deepcopy(held["evidence"])
        decisions.append(decision)
    return decisions, analyses


def _definition_checks(raw: object, defaults: list) -> list:
    checks = deepcopy(_rows(raw, 32, "definition_checks"))
    for index, check in enumerate(checks):
        if type(check) is not dict:
            raise ValueError("not_an_object:definition_check")
        for side in ("left", "right"):
            item = check.get(side)
            if type(item) is not dict or "body" not in item:
                raise ValueError("missing_field:definition_check." + side)
            path = "/request/session/definition_checks/" + str(index) + "/" + side + "/body"
            item["body"] = proposition(item["body"], path, defaults)
    return checks


# Object references inside closed protocol data, exactly as frozen in interface/ledger.md. Preparation uses
# them only to fill an omitted depends_on mechanically; protocol_objects re-validates every reference.
def _data_references(kind: str, data: dict, ids: set[str]) -> list[str]:
    found: list[object] = []
    if kind == "measurement":
        found = [data.get("baseline")]
    elif kind == "endpoint":
        found = [data.get("variable"), data.get("estimand")]
    elif kind == "assessment":
        found = [data.get("measurement")]
    elif kind == "collection":
        handling = data.get("event_handling")
        found = [data.get("assessment"), handling.get("estimand") if isinstance(handling, dict) else None]
    elif kind == "efficacy":
        found = [
            data.get("endpoint"),
            data.get("parameters") if data.get("method") == "external_method" else None,
        ]
    elif kind == "policy":
        found = [b.get("object") for b in data.get("bindings") or [] if isinstance(b, dict)]
    elif kind == "external_method":
        found = [i.get("ref") for i in data.get("inputs") or [] if isinstance(i, dict)]
    return list(dict.fromkeys(ref for ref in found if isinstance(ref, str) and ref in ids))


def _protocol_scope(raw: dict, target: dict, path: str, defaults: list) -> dict:
    open_context = {"cohort": None, "phase": None, "arm": None}
    return deepcopy(
        _take(raw, "scope", {"target": deepcopy(target), "context": open_context}, path, defaults)
    )


def _adoption_premise(raw: object, object_id: str, version: str) -> dict:
    """An explicit adoption record from a compact `adopted_by`; standing is never defaulted."""
    held = _fields(
        raw, {"ref", "status", "resolution"}, {"ref", "status", "resolution"}, "protocol.adopted_by"
    )
    return {
        "id": f"adopt:{object_id}:{version}",
        "kind": "adoption",
        "payload": {
            "objects": [{"id": object_id, "version": version}],
            "status": held["status"],
            "resolution": held["resolution"],
        },
        "origin": {
            "kind": "user_choice",
            "ref": _text(held["ref"], "adopted_by.ref"),
            "source": None,
            "analysis": None,
        },
        "depends_on": [],
    }


def _protocol_object(
    item: object, path: str, target: dict, ids: set, defaults: list, adoptions: list
) -> dict:
    """One compact protocol object with disclosed administrative defaults (also used for replacements)."""
    row = _fields(
        item,
        {
            "id",
            "kind",
            "version",
            "origin",
            "data",
            "standing",
            "support",
            "depends_on",
            "scope",
            "adopted_by",
        },
        {"id", "kind", "version", "origin", "data"},
        "protocol.object",
    )
    origin = _origin(row["origin"], path + "/origin", defaults)
    data = deepcopy(row["data"])
    if row["kind"] == "assessment" and isinstance(data, dict) and isinstance(data.get("condition"), dict):
        data["condition"] = proposition(data["condition"], path + "/data/condition", defaults)
    standing = {"status": "proposed", "resolution": "unresolved", "basis": [origin["ref"]]}
    support: list = []
    if "adopted_by" in row:
        adoption = _adoption_premise(row["adopted_by"], row["id"], row["version"])
        adoptions.append(adoption)
        # Defaults follow the explicit adoption (disclosed); own standing and support stay conjunctive (C3).
        standing = {
            "status": adoption["payload"]["status"],
            "resolution": adoption["payload"]["resolution"],
            "basis": [adoption["origin"]["ref"]],
        }
        support = [adoption["id"]]
    references = _data_references(row["kind"], data, ids) if isinstance(data, dict) else []
    return {
        "id": row["id"],
        "kind": row["kind"],
        "scope": _protocol_scope(row, target, path, defaults),
        "version": row["version"],
        "origin": origin,
        "standing": deepcopy(_take(row, "standing", standing, path, defaults)),
        "support": deepcopy(_take(row, "support", support, path, defaults)),
        "depends_on": deepcopy(_take(row, "depends_on", references, path, defaults)),
        "data": data,
    }


def _protocol_decisions(
    raw: object, target: dict, ids: set, defaults: list, offset: int, adoptions: list
) -> list[dict]:
    """Compact protocol alternatives (C8): {id,question,alternatives:[{id,label,replace?,checks}]}."""
    out = []
    for index, item in enumerate(_rows(raw, 128, "protocol.decisions")):
        # Disclosed defaults point where the values land: the expanded session's decisions list.
        path = f"/request/session/decisions/{offset + index}"
        row = _fields(
            item,
            {"id", "question", "alternatives", "selected"},
            {"id", "question", "alternatives"},
            "protocol.decision",
        )
        alternatives = []
        for number, alt in enumerate(_rows(row["alternatives"], 16, "protocol.decision.alternatives")):
            spot = f"{path}/alternatives/{number}"
            held = _fields(
                alt, {"id", "label", "replace", "checks"}, {"id", "label", "checks"}, "protocol.alternative"
            )
            replace = (
                held["replace"] if "replace" in held else _default(defaults, spot + "/replace_objects", [])
            )
            alternatives.append(
                {
                    "id": held["id"],
                    "label": held["label"],
                    "replace_objects": [
                        _protocol_object(obj, f"{spot}/replace_objects/{k}", target, ids, defaults, adoptions)
                        for k, obj in enumerate(_rows(replace, 16, "protocol.alternative.replace"))
                    ],
                    "checks": deepcopy(held["checks"]),
                }
            )
        out.append(
            {
                "kind": "protocol_options",
                "id": row["id"],
                "question": row["question"],
                "target": deepcopy(target),
                "coverage": "declared_design",
                "selected": deepcopy(_take(row, "selected", None, path, defaults)),
                "alternatives": alternatives,
            }
        )
    return out


def _protocol(raw: object, target: dict, defaults: list, decision_offset: int, adoptions: list) -> dict:
    """Mechanical expansion of a compact protocol; every administrative default is disclosed."""
    held = _fields(
        raw, {"objects", "checks", "sections", "decisions"}, {"objects", "checks", "sections"}, "protocol"
    )
    base = "/request/session/protocol"
    rows = _rows(held["objects"], 256, "protocol.objects")
    ids = {row.get("id") for row in rows if isinstance(row, dict)}
    objects = [
        _protocol_object(item, f"{base}/objects/{index}", target, ids, defaults, adoptions)
        for index, item in enumerate(rows)
    ]
    checks = []
    for index, item in enumerate(_rows(held["checks"], 128, "protocol.checks")):
        path = f"{base}/checks/{index}"
        row = _fields(
            item,
            {"id", "kind", "objects", "required", "claims", "bindings", "support", "scope"},
            {"id", "kind", "objects", "required"},
            "protocol.check",
        )
        if row["kind"] in ("schedule", "finite_policy") and "claims" not in row:
            raise ValueError("protocol_check_claims_required:" + str(row["id"]))
        checks.append(
            {
                "id": row["id"],
                "kind": row["kind"],
                "scope": _protocol_scope(row, target, path, defaults),
                "objects": deepcopy(row["objects"]),
                "bindings": deepcopy(_take(row, "bindings", [], path, defaults)),
                "claims": deepcopy(_take(row, "claims", [], path, defaults)),
                "required": row["required"],
                "support": deepcopy(_take(row, "support", [], path, defaults)),
            }
        )
    sections = []
    for index, item in enumerate(_rows(held["sections"], 8, "protocol.sections")):
        path = f"{base}/sections/{index}"
        row = _fields(item, {"id", "state", "objects", "basis"}, {"id", "state"}, "protocol.section")
        sections.append(
            {
                "id": row["id"],
                "state": row["state"],
                "objects": deepcopy(_take(row, "objects", [], path, defaults)),
                "basis": deepcopy(_take(row, "basis", [], path, defaults)),
            }
        )
    expanded = {"schema_version": 1, "objects": objects, "checks": checks, "sections": sections}
    if "decisions" in held:
        expanded["decisions"] = _protocol_decisions(
            held["decisions"], target, ids, defaults, decision_offset, adoptions
        )
    return expanded


RETAINED_STUDY_MARKER = "$retained_study"  # the transport's typed source handle (retained_sources.MARKER)


def _has_retained_handles(sources: list) -> bool:
    handles = [
        source["study"][RETAINED_STUDY_MARKER]
        for source in sources
        if isinstance(source.get("study"), dict) and RETAINED_STUDY_MARKER in source["study"]
    ]
    for handle in handles:
        # Structural only (no hydration here): the transport needs exactly run, nct and digest.
        if type(handle) is not dict or set(handle) != {"run", "nct", "digest"}:
            raise ValueError("invalid_source_marker")
        if not all(type(value) is str and value for value in handle.values()):
            raise ValueError("invalid_source_marker")
    return bool(handles)


def _session(raw: dict, criteria: list, origins: list, defaults: list) -> dict:
    session_state.target(raw["target"])
    target = deepcopy(raw["target"])
    path = "/request/session"
    sources = _sources(_take(raw, "sources", [], path, defaults))
    source_ids = {source["id"] for source in sources}
    for entry in origins:
        source = entry["origin"]["source"]
        if source is not None and source not in source_ids:
            raise ValueError("unknown_source:origin")
    ids = [criterion["id"] for criterion in criteria]
    analyses = _analyses(raw.get("analyses", []), set(ids), source_ids)
    if "questions" not in raw and "protocol" not in raw:
        # Version 1 preparation keeps its existing refusal exactly.
        raise ValueError("missing_field:prepare.design_session")
    # A protocol-only session has no questions; the default is disclosed where it lands (session decisions).
    questions = raw["questions"] if "questions" in raw else _default(defaults, path + "/decisions", [])
    decisions, generated = _questions(questions, target, ids, defaults, len(analyses))
    analyses.extend(generated)
    by_analysis = {}
    for analysis in analyses:
        if analysis["id"] in by_analysis:
            raise ValueError("duplicate_id:analysis:" + analysis["id"])
        by_analysis[analysis["id"]] = analysis
    session_state._decision_inputs({decision["id"]: decision for decision in decisions}, by_analysis)
    supplied_limits = _fields(raw.get("limits", {}), set(session_state.HARD_LIMITS), set(), "limits")
    limits = {}
    for key, ceiling in session_state.HARD_LIMITS.items():
        value = _take(supplied_limits, key, ceiling, path + "/limits", defaults)
        if type(value) is not int or not 1 <= value <= ceiling:
            raise ValueError("invalid_limit:" + key)
        limits[key] = value
    for name, items in (
        ("sources", sources),
        ("premises", criteria),
        ("analyses", analyses),
        ("decisions", decisions),
    ):
        if len(items) > limits["max_" + name]:
            raise ValueError("resource_bound:prepare:" + name)
    premises = [
        {
            "id": criterion["id"],
            "kind": "assertion",
            "payload": criterion,
            "origin": deepcopy(origin["origin"]),
            "depends_on": [],
        }
        for criterion, origin in zip(criteria, origins, strict=True)
    ]
    session = {
        "schema_version": 1,
        "id": _text(raw["id"], "id"),
        "revision": _text(_take(raw, "revision", "one", path, defaults), "revision"),
        "parent_digest": None,
        "target": target,
        "sources": sources,
        "premises": premises,
        "analyses": analyses,
        "decisions": decisions,
        "limits": limits,
    }
    if "protocol" in raw:
        session["schema_version"] = 2
        adoptions: list = []
        protocol = _protocol(raw["protocol"], target, defaults, len(session["decisions"]), adoptions)
        known = {premise["id"]: premise for premise in session["premises"]}
        for adoption in adoptions:
            held = known.get(adoption["id"])
            if held is not None:
                # The same object version adopted twice (e.g. a baseline and an identical replacement) is one
                # record; a different record under the same id is a conflicting adoption.
                if held != adoption:
                    raise ValueError("conflicting_adoption:" + adoption["id"])
                continue
            known[adoption["id"]] = adoption
            session["premises"].append(adoption)
        # Protocol alternatives are session decisions (C8); the protocol envelope itself stays exactly C2.
        session["decisions"].extend(protocol.pop("decisions", []))
        session["protocol"] = protocol
    if "definition_checks" in raw:
        from TrialLedger.layer2.definition_checks import prepare as prepare_definitions

        # Protocol operands name declared checks; each has the session target (definitions.md).
        declared = (
            {"checks": {check["id"]: {"scope": check["scope"]} for check in session["protocol"]["checks"]}}
            if "protocol" in session
            else None
        )
        session["definition_checks"] = prepare_definitions(
            _definition_checks(raw["definition_checks"], defaults), by_analysis, protocol=declared
        )
    # Validation only (no solver): a v2 expansion must already be an admissible session. Digest-bound
    # retained-study handles are hydrated by the transport at execution, so a session carrying them is
    # validated there instead; prepare() discloses that deferral (PAH cold audit).
    if "protocol" in session and not _has_retained_handles(sources):
        session_state.prepare(session)
    return {"operation": "design_session", "session": session, "previous": None}


def prepare(request: object) -> dict:
    """Return one runnable request and its construction record, without computing it."""
    held = source_evidence._json_copy(request, "prepare")
    shape = INPUTS["prepare"]
    raw = _fields(held, {"operation", *shape["fields"]}, {"operation", *shape["required"]}, "prepare")
    if raw["operation"] != "prepare":
        raise ValueError("unsupported_preparation_operation")
    mode = raw["for"]
    if mode not in ("entailment", "design_session"):
        raise ValueError("unsupported_preparation_target")
    if mode == "entailment":
        _fields(
            raw,
            {"operation", "for", "criteria", "query", "context", "bound"},
            {"operation", "for", "criteria", "query"},
            "prepare.entailment",
        )
    else:
        _fields(
            raw,
            {
                "operation",
                "for",
                "criteria",
                "id",
                "revision",
                "target",
                "sources",
                "questions",
                "analyses",
                "limits",
                "definition_checks",
                "protocol",
            },
            {"operation", "for", "criteria", "id", "target"},
            "prepare.design_session",
        )
    defaults, criteria, origins, ids = [], [], [], set()
    for index, criterion in enumerate(_rows(raw["criteria"], 1000, "criteria")):
        expanded, origin = _criterion(criterion, index, defaults)
        if expanded["id"] in ids:
            raise ValueError("duplicate_id:criterion:" + expanded["id"])
        ids.add(expanded["id"])
        criteria.append(expanded)
        origins.append(origin)
    if mode == "entailment":
        expanded = {
            "operation": "entailment",
            "assertions": criteria,
            "query": proposition(raw["query"], "/request/query", defaults),
            "context": _context(raw.get("context", {}), "/request/context", defaults),
            "bound": _bound(_take(raw, "bound", MAX_ASSIGNMENTS, "/request", defaults)),
        }
    else:
        expanded = _session(raw, criteria, origins, defaults)
    result = {
        "request": expanded,
        "defaults": defaults,
        "origins": origins,
        "limits_of_claim": list(LIMITS_OF_CLAIM),
    }
    session_out = expanded.get("session") if isinstance(expanded.get("session"), dict) else {}
    if "protocol" in session_out and _has_retained_handles(session_out.get("sources", [])):
        result["validation"] = "deferred_until_execution:retained_study"
    for entry in defaults:
        parts = entry["path"].split("/")
        if mode == "design_session" and parts[1:3] == ["request", "assertions"]:
            entry["path"] = "/".join(["", "request", "session", "premises", parts[3], "payload", *parts[4:]])
        entry["value"] = deepcopy(source_evidence._selected(result, entry["path"]))
    return result


def example() -> dict:
    atom = {
        "kind": "quantity",
        "predicate": {"kind": "demographic", "key": "age"},
        "comparison": "ge",
        "number": 18,
        "unit": "years",
        "inclusivity": "inclusive",
    }
    return {
        "operation": "prepare",
        "for": "entailment",
        "criteria": [
            {
                "id": "age",
                "modality": "required",
                "body": atom,
                "origin": {"kind": "user_choice", "ref": "invented:brief"},
                "status": "known",
                "resolution": "resolved",
            }
        ],
        "query": {**deepcopy(atom), "comparison": "eq", "number": 17},
    }


def session_example() -> dict:
    request = example()
    target = {
        "kind": "new_trial",
        "ref": "invented-draft",
        "scope": {
            "study": "invented-draft",
            "population": "adults",
            "arm": "all",
            "time": "entry",
            "version": "draft-1",
        },
    }
    return {
        "operation": "prepare",
        "for": "design_session",
        "id": "invented-session",
        "target": target,
        "criteria": request["criteria"],
        "questions": [
            {
                "id": "age-choice",
                "question": "Which represented ages fit?",
                "options": [
                    {"id": "seventeen", "label": "Age 17", "query": request["query"]},
                    {
                        "id": "eighteen",
                        "label": "Age 18",
                        "query": {**deepcopy(request["query"]), "number": 18},
                    },
                ],
            }
        ],
    }


def card(*, schema: bool = False) -> dict:
    result = {
        "detail": "schema" if schema else "card",
        "operation": "prepare",
        "question": "Prepare a small typed request without writing canonical boilerplate.",
        "procedure": "Use typed criteria/query or named questions/options, "
        "inspect returned request/defaults/origins, then run returned request through reason. "
        "No Python builder is needed.",
        "boundary": "No prose interpretation, computation, source certification or person confirmation; "
        "missing standing stays proposed/unresolved.",
        "input": deepcopy(INPUTS["prepare"]),
        "compact_shapes": deepcopy({key: value for key, value in INPUTS.items() if key != "prepare"}),
        "example_basis": "Invented teaching choices, not a real trial or human confirmation.",
        "example": example(),
        "session_example": session_example(),
        "next": "Inspect defaults and origins. Pass result.request as the next reason request, "
        "or retain this preparation with response_view compact then call reason with prepared:artifact.id. "
        "CLI: reason --prepared ID --store STORE. No copied canonical JSON or Python script is needed.",
        "discover": {
            "schema": {"operation": "describe", "view": "prepare", "detail": "schema"},
            "full": {"operation": "describe", "view": "prepare", "detail": "full"},
        },
    }
    if schema:
        fields = {key: {"description": text} for key, text in INPUTS["prepare"]["fields"].items()}
        result.update(
            request_schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {"operation": {"const": "prepare"}, **fields},
                "required": ["operation", *INPUTS["prepare"]["required"]],
                "description": "Structural schema only; preparation validates typed construction, "
                "execution validates its own admission and sources.",
            },
            input_shapes=deepcopy(INPUTS),
        )
    return result


def protocol_example() -> dict:
    """An invented week-12 visit, its collection plan and a required schedule check (teaching only)."""
    request = session_example()
    interval = {"lower": "77", "upper": "91", "lower_inclusive": True, "upper_inclusive": True}
    through_80 = {"lower": None, "upper": "80", "lower_inclusive": False, "upper_inclusive": True}
    origin = {"kind": "user_choice", "ref": "user:invented week-12 plan (teaching example)"}
    reference = {
        "ref": "invented:score definition",
        "version": "1",
        "status": "proposed",
        "resolution": "unresolved",
        "basis": ["user:invented week-12 plan (teaching example)"],
    }
    request["protocol"] = {
        "objects": [
            {
                "id": "score",
                "kind": "measurement",
                "version": "invented-v1",
                "origin": origin,
                "data": {"definition": reference, "unit": "points", "mode": "observed", "baseline": None},
            },
            {
                "id": "week12",
                "kind": "assessment",
                "version": "invented-v1",
                "origin": origin,
                "data": {
                    "measurement": "score",
                    "anchor": "randomization",
                    "unit": "day",
                    "nominal": "84",
                    "permitted": [interval],
                    "condition": None,
                },
            },
            {
                "id": "collection",
                "kind": "collection",
                "version": "invented-v1",
                "origin": origin,
                "data": {
                    "assessment": "week12",
                    "mode": "observed",
                    "availability": [through_80],
                    "event_handling": None,
                },
            },
        ],
        "checks": [
            {
                "id": "week12-schedule",
                "kind": "schedule",
                "objects": ["week12", "collection"],
                "required": True,
                "claims": [
                    {"id": "visit", "claim": "existence"},
                    {"id": "target", "claim": "nominal"},
                    {"id": "window", "claim": "full_window"},
                ],
            }
        ],
        "sections": [{"id": "assessments", "state": "requested", "objects": ["week12", "collection"]}],
    }
    return request


# ---------------------------------------------------------------------------------------------------------
# Focused runnable protocol examples, one per implemented family. Every value is invented teaching data.
# ---------------------------------------------------------------------------------------------------------
_INVENTED_ORIGIN = {"kind": "user_choice", "ref": "user:invented teaching plan (not a real trial)"}
_INVENTED_ADOPTION = {
    "ref": "user:invented adoption (teaching example)",
    "status": "known",
    "resolution": "resolved",
}
_INVENTED_VERSION = "invented-v1"


def _invented_reference(name: str) -> dict:
    return {
        "ref": "invented:" + name,
        "version": "1",
        "status": "known",
        "resolution": "resolved",
        "basis": ["user:invented teaching plan (not a real trial)"],
    }


def _invented_object(identity: str, kind: str, data: dict, adopted: bool = True) -> dict:
    row = {
        "id": identity,
        "kind": kind,
        "version": _INVENTED_VERSION,
        "origin": deepcopy(_INVENTED_ORIGIN),
        "data": data,
    }
    if adopted:
        row["adopted_by"] = deepcopy(_INVENTED_ADOPTION)
    return row


def _invented_session(protocol: dict, criteria: list | None = None) -> dict:
    """A protocol-only design_session preparation around invented objects."""
    request = session_example()
    del request["questions"]
    request["criteria"] = criteria or []
    request["protocol"] = protocol
    return request


def _invented_measurement(identity: str = "score", unit: str = "points") -> dict:
    return _invented_object(
        identity,
        "measurement",
        {
            "definition": _invented_reference(identity + " definition"),
            "unit": unit,
            "mode": "observed",
            "baseline": None,
        },
    )


def _invented_flag(key: str, positive: bool = True) -> dict:
    from TrialLedger.layer2 import assertions as assertion

    literal = assertion.Literal(
        assertion.Subject("study_procedure"),
        assertion.Predicate("measurement", key),
        assertion.Value("boolean", "eq"),
        polarity="positive" if positive else "negative",
    )
    return json.loads(assertion.canonical(literal))


def _invented_all(*parts: dict) -> dict:
    return {"class": "AllOf", "parts": list(parts)}


def _invented_not(part: dict) -> dict:
    return {"class": "Not", "part": part}


def _invented_action(name: str) -> dict:
    return {"id": name, "scope": {"level": "cohort", "ref": "invented:cohort"}, "description": name}


def policy_example() -> dict:
    """A dose policy whose continue rule ignores a safety signal, violating a declared prohibition."""
    signal, concern = _invented_flag("efficacy_signal"), _invented_flag("safety_concern")
    model = {
        "scope": "invented:dose-policy",
        "version": "invented-v1",
        "variables": [
            {"id": key, "values": [_invented_flag(key), _invented_flag(key, False)]}
            for key in ("efficacy_signal", "safety_concern")
        ],
        "constraints": [],
        "states": ["interim", "decided"],
        "initial": ["interim"],
        "terminal": ["decided"],
        "actions": [_invented_action("continue_dosing"), _invented_action("hold_dosing")],
        "transitions": [
            {
                "id": "continue",
                "from": "interim",
                "to": "decided",
                "guard": signal,
                "actions": ["continue_dosing"],
            },
            {
                "id": "hold",
                "from": "interim",
                "to": "decided",
                "guard": _invented_not(signal),
                "actions": ["hold_dosing"],
            },
        ],
        "prohibitions": [
            {
                "id": "no-continue-with-safety-concern",
                "state": None,
                "condition": concern,
                "actions": ["continue_dosing"],
                "rule": _invented_reference("safety prohibition"),
            }
        ],
        "invariants": [],
    }
    protocol = {
        "objects": [_invented_object("dose-policy", "policy", {"model": model, "bindings": []})],
        "checks": [
            {
                "id": "dose-policy-check",
                "kind": "finite_policy",
                "objects": ["dose-policy"],
                "required": True,
                "claims": [
                    {"id": "coverage", "claim": "coverage", "witness_limit": 8},
                    {"id": "prohibition", "claim": "prohibition", "witness_limit": 8},
                    {"id": "termination", "claim": "termination", "witness_limit": 8},
                ],
            }
        ],
        "sections": [{"id": "safety", "state": "requested", "objects": ["dose-policy"]}],
    }
    return _invented_session(protocol)


def _invented_efficacy_objects(method: str, parameters: object, assumptions: list) -> list:
    return [
        _invented_measurement("response", "responder"),
        _invented_object(
            "response-endpoint",
            "endpoint",
            {
                "variable": "response",
                "definition": _invented_reference("response endpoint"),
                "estimand": None,
                "dependencies": None,
            },
        ),
        _invented_object(
            "efficacy-design",
            "efficacy",
            {
                "endpoint": "response-endpoint",
                "method": method,
                "parameters": parameters,
                "assumptions": assumptions,
            },
        ),
    ]


def binomial_example() -> dict:
    """A single-arm exact fixed-n binomial design with all three declared assumption roles."""
    roles = ("fixed_n", "iid_binary", "alignment")
    criteria = [
        {
            "id": "assume-" + role,
            "modality": "descriptive",
            "body": _invented_flag("assumption_" + role),
            "origin": {"kind": "user_choice", "ref": "user:invented " + role + " assumption"},
            "status": "known",
            "resolution": "resolved",
        }
        for role in roles
    ]
    parameters = {
        "model": "fixed_n_iid_bernoulli",
        "direction": "greater",
        "n": 20,
        "critical_count": 7,
        "p0": "1/5",
        "p1": "2/5",
    }
    objects = _invented_efficacy_objects(
        "binomial_design", parameters, [{"role": role, "premise": "assume-" + role} for role in roles]
    )
    protocol = {
        "objects": objects,
        "checks": [
            {
                "id": "binomial-check",
                "kind": "binomial_design",
                "objects": ["efficacy-design", "response-endpoint"],
                "required": True,
                "claims": [
                    {
                        "id": "type-one",
                        "quantity": "null_rejection_probability",
                        "comparison": "<=",
                        "value": "1/10",
                    },
                    {"id": "power", "quantity": "power", "comparison": ">=", "value": "7/10"},
                ],
            }
        ],
        "sections": [{"id": "efficacy", "state": "requested", "objects": ["efficacy-design"]}],
    }
    return _invented_session(protocol, criteria)


def external_method_example() -> dict:
    """An external method with named missing inputs: it reads not_computed and is never evaluated here."""
    method = {
        "definition": _invented_reference("externally computed survival analysis"),
        "inputs": [
            {"name": "alpha", "value": "1/20", "unit": None, "ref": None},
            {"name": "hazard_ratio", "value": None, "unit": None, "ref": None},
        ],
        "missing": ["accrual_rate"],
    }
    objects = _invented_efficacy_objects("external_method", "outside-method", [])
    objects.append(_invented_object("outside-method", "external_method", method))
    protocol = {
        "objects": objects,
        "checks": [
            {
                "id": "outside-method-check",
                "kind": "external_method",
                "objects": ["efficacy-design", "outside-method"],
                "required": True,
            }
        ],
        "sections": [{"id": "efficacy", "state": "requested", "objects": ["efficacy-design"]}],
    }
    return _invented_session(protocol)


def estimand_example() -> dict:
    """An estimand linked once from its collection, plus an endpoint dependencies check."""
    estimand = {
        "scope": "invented:cohort-A:week12",
        "version": "1",
        "id": "invented:week12-policy",
        "definitions": {
            name: _invented_reference(name)
            for name in ("intercurrent_events", "population", "summary", "treatment", "variable")
        },
        "events": [
            {
                "id": "discontinuation",
                "event_ref": _invented_reference("treatment discontinuation"),
                "strategy": "treatment_policy",
                "status": "known",
                "resolution": "resolved",
                "basis": ["user:invented teaching plan (not a real trial)"],
            }
        ],
        "requirements": [
            {
                "id": "week12",
                "event": "discontinuation",
                "variable": "invented:variable",
                "window": "invented:week12-regardless-of-discontinuation",
                "role": "observed_measurement",
                "mode": "observed",
                "relevance": "required",
                "rule": _invented_reference("week12 relevance"),
            }
        ],
        "collection_plan": [],
        "data_state": [],
        "dependencies": None,
    }
    day_range = {"lower": "77", "upper": "91", "lower_inclusive": True, "upper_inclusive": True}
    measurement = lambda name: {"id": name, "mode": "observed"}  # noqa: E731
    dependencies = {
        "scope": "invented:cohort-A:change-score",
        "version": "1",
        "rules": [
            {
                "id": "change",
                "version": "invented-definition-1",
                "output": {"id": "change", "mode": "derived"},
                "alternatives": [[measurement("baseline"), measurement("week12")]],
                "when": [],
            }
        ],
        "adopted": ["change"],
        "available": [measurement("baseline"), measurement("week12")],
        "unavailable": [],
        "conditions": {},
    }
    protocol = {
        "objects": [
            _invented_measurement(),
            _invented_object(
                "week12",
                "assessment",
                {
                    "measurement": "score",
                    "anchor": "randomization",
                    "unit": "day",
                    "nominal": "84",
                    "permitted": [day_range],
                    "condition": None,
                },
            ),
            _invented_object("week-policy", "estimand", estimand),
            _invented_object(
                "week12-collection",
                "collection",
                {
                    "assessment": "week12",
                    "mode": "observed",
                    "availability": [day_range],
                    "event_handling": {
                        "estimand": "week-policy",
                        "requirement": "week12",
                        "action": "collect",
                    },
                },
            ),
            _invented_object(
                "change-endpoint",
                "endpoint",
                {
                    "variable": "score",
                    "definition": _invented_reference("change endpoint"),
                    "estimand": None,
                    "dependencies": dependencies,
                },
            ),
        ],
        "checks": [
            {"id": "estimand-check", "kind": "estimand", "objects": ["week-policy"], "required": True},
            {
                "id": "dependencies-check",
                "kind": "dependencies",
                "objects": ["change-endpoint"],
                "required": True,
            },
        ],
        "sections": [
            {"id": "endpoints", "state": "requested", "objects": ["week-policy", "change-endpoint"]}
        ],
    }
    return _invented_session(protocol)


def decisions_example() -> dict:
    """Two collection plans compared under one schedule check; the baseline plan is selected."""
    request = protocol_example()
    protocol = request["protocol"]
    for item in protocol["objects"]:
        item["adopted_by"] = deepcopy(_INVENTED_ADOPTION)
    longer = deepcopy(protocol["objects"][2])
    del longer["adopted_by"]
    longer["data"]["availability"] = [
        {"lower": None, "upper": "91", "lower_inclusive": False, "upper_inclusive": True}
    ]
    longer["support"] = ["adopt:collection:" + longer["version"]]
    protocol["decisions"] = [
        {
            "id": "collection-plan",
            "question": "How long should invented week-12 collection run?",
            "alternatives": [
                {"id": "as-drafted", "label": "Through day 80", "checks": ["week12-schedule"]},
                {
                    "id": "extend",
                    "label": "Through day 91",
                    "replace": [longer],
                    "checks": ["week12-schedule"],
                },
            ],
            "selected": {
                "alternative": "as-drafted",
                "origin": "user",
                "basis": ["user:invented selection (teaching example)"],
            },
        }
    ]
    return request


def definition_example() -> dict:
    """Two invented MADRS-style trigger readings: the stricter reading implies the earlier one."""
    from TrialLedger.layer2 import assertions as assertion

    def threshold(number: int) -> dict:
        value = assertion.Value("quantity", "ge", number=number, unit="score")
        literal = assertion.Literal(
            assertion.Subject("participant"), assertion.Predicate("measurement", "madrs"), value
        )
        return json.loads(assertion.canonical(literal))

    def policy(identity: str, guard: dict, action: str) -> dict:
        scores = [
            json.loads(
                assertion.canonical(
                    assertion.Literal(
                        assertion.Subject("participant"),
                        assertion.Predicate("measurement", "madrs"),
                        assertion.Value("quantity", "eq", number=number, unit="score"),
                    )
                )
            )
            for number in (18, 21, 23)
        ]
        return {
            "model": {
                "scope": "invented:" + identity,
                "version": "invented-v1",
                "variables": [{"id": "madrs", "values": scores}],
                "constraints": [],
                "states": ["monitoring", "decided"],
                "initial": ["monitoring"],
                "terminal": ["decided"],
                "actions": [_invented_action(action), _invented_action("keep_monitoring")],
                "transitions": [
                    {
                        "id": action,
                        "from": "monitoring",
                        "to": "decided",
                        "guard": guard,
                        "actions": [action],
                    },
                    {
                        "id": "not-" + action,
                        "from": "monitoring",
                        "to": "decided",
                        "guard": _invented_not(guard),
                        "actions": ["keep_monitoring"],
                    },
                ],
                "prohibitions": [],
                "invariants": [],
            },
            "bindings": [],
        }

    trigger, relapse = threshold(20), threshold(22)
    readings = {
        "trigger-check": ("trigger-rule", trigger, "retreat"),
        "relapse-check": ("relapse-rule", relapse, "record_relapse"),
    }
    protocol = {
        "objects": [
            _invented_object(obj, "policy", policy(obj, guard, action))
            for obj, guard, action in readings.values()
        ],
        "checks": [
            {
                "id": check,
                "kind": "finite_policy",
                "objects": [obj],
                "required": True,
                "claims": [{"id": "coverage", "claim": "coverage", "witness_limit": 8}],
            }
            for check, (obj, _guard, _action) in readings.items()
        ],
        "sections": [],
    }
    request = _invented_session(protocol)

    def operand(check: str, guard: dict) -> dict:
        return {
            "protocol_check": check,
            "child": 0,
            "address": "/request/signals/0/data/transitions/0/guard",
            "body": guard,
            "status": "known",
            "resolution": "resolved",
            "basis": ["user:invented " + check + " reading (teaching example)"],
        }

    request["definition_checks"] = [
        {
            "id": "relapse-implies-trigger",
            "relation": "implies",
            "left": operand("relapse-check", relapse),
            "right": operand("trigger-check", trigger),
            "status": "known",
            "resolution": "resolved",
            "basis": ["user:invented definition-relation declaration (teaching example)"],
        }
    ]
    return request


def protocol_examples() -> dict:
    """Family -> complete invented prepare request, each of which prepares and runs to complete."""
    return {
        "schedule": protocol_example(),
        "finite_policy": policy_example(),
        "binomial_design": binomial_example(),
        "external_method": external_method_example(),
        "estimand": estimand_example(),
        "decisions": decisions_example(),
        "definition_relation": definition_example(),
    }


PROTOCOL_BUILT = {
    "built": [
        "exact schedule window coverage (existence, nominal day, full permitted window)",
        "finite declared-variable policies: coverage, exclusivity, prohibition, invariant and termination "
        "claims with bounded witnesses",
        "exact fixed-n one-sided single-arm binomial design (null rejection probability and power)",
        "plan comparisons (protocol.decisions) over the declared checks",
        "definition relations (implies, equivalent, disjoint) over two attributed protocol-check readings",
    ],
    "not_built": [
        "adaptive, cluster or survival calculations (an external_method stays not computed, with its named "
        "missing inputs)",
        "optimisation or sample-size search",
        "protocol writing",
        "any judgement of clinical appropriateness, safety, validity or completeness",
    ],
    "policy_coverage": "coverage is over the declared variables and states only; an undeclared variable, "
    "safety signal or operating characteristic is not covered. External variables are re-chosen at every "
    "step. A covered policy is not a safe policy.",
}
PROTOCOL_FAMILIES = {
    "schedule": "week-12 visit: a feasible visit, an uncollected nominal day and an uncovered window part "
    "(unadopted, so findings stay unadmitted)",
    "finite_policy": "dose policy whose continue rule ignores a declared safety prohibition: a violation "
    "with bounded witnesses, plus coverage and termination",
    "binomial_design": "single-arm exact binomial with fixed_n, iid_binary and alignment declared as "
    "premises; exact probabilities against stated bounds",
    "external_method": "not_computed: declared with named missing inputs and never evaluated",
    "estimand": "estimand with its week-12 requirement linked once from the collection (event_handling), "
    "plus an endpoint dependencies check",
    "decisions": "two collection plans compared under one schedule check, baseline selected",
    "definition_relation": "two trigger readings over two finite-policy checks; the stricter implies the "
    "earlier",
}


def protocol_card(*, detail: str = "card") -> dict:
    """The protocol discovery card at three levels: card (default), schema and full."""
    result: dict[str, Any] = {
        "detail": detail,
        "operation": "prepare",
        "question": "Declare protocol objects, checks and sections for a version-2 design session.",
        "procedure": "Add a protocol {objects,checks,sections} to a design_session preparation; inspect "
        "defaults/origins (scope, standing, support and depends_on defaults are disclosed), then run the "
        "returned request. Read result.protocol: per-check children, per-claim admission and receipts.",
        "boundary": "No clinical value, claim, required flag, origin or adoption is defaulted; unspecified "
        "standing stays proposed/unresolved, so findings stay unadmitted until adoption support is declared.",
        "built_boundary": deepcopy(PROTOCOL_BUILT),
        "input_shapes": deepcopy(PROTOCOL_INPUTS),
        "object_data": deepcopy(PROTOCOL_DATA),
        "check_patterns": deepcopy(PROTOCOL_CHECKS),
        "admission": PROTOCOL_ADMISSION,
        "decisions": deepcopy(PROTOCOL_DECISIONS),
        "operator_inputs": {"operation": "describe", "view": "signals", "detail": "full"},
        "discover": {
            "schema": {"operation": "describe", "view": "protocol", "detail": "schema"},
            "full": {"operation": "describe", "view": "protocol", "detail": "full"},
        },
    }
    if detail != "schema":
        result["notes"] = deepcopy(PROTOCOL_NOTES)
        result["example_basis"] = "Invented teaching choices, not a real trial or human confirmation."
        result["example"] = protocol_example()
        result["example_families"] = deepcopy(PROTOCOL_FAMILIES)
        result["next"] = (
            "Run the example through prepare, then reason; the schedule check reports a feasible visit, "
            "an uncollected nominal day and an uncovered (80, 91] part of the window, all unadmitted "
            "until the objects are adopted. One focused runnable example per implemented family is "
            "returned under examples in detail full."
        )
    if detail == "full":
        result["examples"] = protocol_examples()
    return result
