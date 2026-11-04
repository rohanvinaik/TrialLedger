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
    decisions, generated = _questions(raw["questions"], target, ids, defaults, len(analyses))
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
    if "definition_checks" in raw:
        from TrialLedger.layer2.definition_checks import prepare as prepare_definitions

        session["definition_checks"] = prepare_definitions(
            _definition_checks(raw["definition_checks"], defaults), by_analysis
        )
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
            },
            {"operation", "for", "criteria", "id", "target", "questions"},
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
