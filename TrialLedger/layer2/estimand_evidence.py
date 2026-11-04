"""Explicit estimand relevance and collection/input alignment, without statistical inference.

Strategy names supply no data requirement. Each relevance rule binds a declared event, variable, window
and mode with attributed support. Plans, actual input states and structural nonexistence remain separate.
Only explicit adopted dependency rules can establish an input-rule conflict. No estimability, estimator
validity, treatment effect, operating characteristics or clinical appropriateness is computed here.
"""

from __future__ import annotations

from copy import deepcopy

from TrialLedger.layer2 import dependency_evidence
from TrialLedger.layer2.signals import support_state

LIMIT = 128
STATUSES = ("known", "interpolated", "proposed")
RESOLUTIONS = ("resolved", "partially_resolved", "unresolved", "conflicting")
STRATEGIES = (
    "treatment_policy",
    "hypothetical",
    "composite",
    "while_on_treatment",
    "principal_stratum",
    "unresolved",
)
RELEVANCE = ("required", "not_required_for_this_estimand", "unresolved")
DEFINITION_KEYS = {"treatment", "population", "variable", "intercurrent_events", "summary"}
REF_FIELDS = {"ref", "version", "status", "resolution", "basis"}
INPUTS = {
    "estimand": {
        "required": (
            "scope",
            "version",
            "id",
            "definitions",
            "events",
            "requirements",
            "collection_plan",
            "data_state",
            "dependencies",
        ),
        "fields": {
            "scope": "exact population/study/arm/time/edition identity, no inferred correspondence",
            "version": "nonempty declared representation version",
            "id": "nonempty estimand identity",
            "definitions": "exactly treatment/population/variable/intercurrent_events/summary standing refs",
            "events": "{id,event_ref,strategy,status,resolution,basis}; event_ref is a standing ref",
            "requirements": (
                "{id,event,variable,window,role,mode,relevance,rule}; rule is a standing ref; variable "
                "must equal definitions.variable.ref exactly. Component inputs (score, rescue date) "
                "belong in the explicitly attributed window/requirement definition, "
                "not a replacement variable."
            ),
            "collection_plan": "{requirement,action,status,resolution,basis}; action collect/stop/unknown",
            "data_state": "{requirement,mode,state,rule}; rule is a standing ref; facts retain exact modes",
            "dependencies": "null or exact existing dependency input; scope/version must match",
        },
        "standing_ref": "{ref,version,status,resolution,basis}; attributed declarations, not verified truth",
        "strategies": list(STRATEGIES),
        "relevance": list(RELEVANCE),
        "roles": ["observed_measurement", "event_ascertainment", "estimator_input"],
        "data_states": ["available", "unavailable", "unknown", "structurally_unavailable"],
        "claims": "unsupported: nonempty candidate claims refuse instead of inventing an elimination",
        "limits": {"events": LIMIT, "requirements": LIMIT, "facts": LIMIT * 2, "basis": 32},
        "outputs": {
            "actual_input": [
                "available",
                "missing_relevant",
                "not_required_for_this_estimand",
                "unresolved",
                "structurally_unavailable",
            ],
            "collection_alignment": ["aligned", "collection_plan_mismatch", "unresolved"],
            "estimation": "not_computed for every result",
        },
    }
}


def collection_alignment(relevance: str, action: str) -> str:
    """A stopped required collection is a plan mismatch, not impossible estimation (pure — pinned).

    pre: relevance in ("required", "not_required_for_this_estimand", "unresolved")
    pre: action in ("collect", "stop", "unknown")
    post: __return__ != "collection_plan_mismatch" or (relevance == "required" and action == "stop")
    post: __return__ != "aligned" or relevance != "unresolved"
    """
    if relevance == "not_required_for_this_estimand":
        return "aligned"
    if relevance == "unresolved" or action == "unknown":
        return "unresolved"
    if relevance == "required" and action == "stop":
        return "collection_plan_mismatch"
    return "aligned"


def actual_input(relevance: str, state: str) -> str:
    """Preserve nonexistence and available inputs; absence is missing only if relevant (pure — pinned).

    pre: relevance in ("required", "not_required_for_this_estimand", "unresolved")
    pre: state in ("available", "unavailable", "unknown", "structurally_unavailable")
    post: (__return__ == "available") == (state == "available")
    post: (__return__ == "structurally_unavailable") == (state == "structurally_unavailable")
    post: __return__ != "missing_relevant" or (relevance == "required" and state == "unavailable")
    """
    if state == "structurally_unavailable":
        return "structurally_unavailable"
    if state == "available":
        return "available"
    if relevance == "not_required_for_this_estimand":
        return "not_required_for_this_estimand"
    if relevance == "required" and state == "unavailable":
        return "missing_relevant"
    return "unresolved"


def _object(value: object, fields: set[str], where: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("estimand_fields_do_not_fit:" + where)
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("estimand_identity_required:" + where)
    return value


def _rows(value: object, limit: int, where: str) -> list:
    if not isinstance(value, list):
        raise ValueError("estimand_list_required:" + where)
    if len(value) > limit:
        raise ValueError("resource_bound:estimand_" + where)
    return value


def _standing(row: dict) -> None:
    if row["status"] not in STATUSES or row["resolution"] not in RESOLUTIONS:
        raise ValueError("estimand_invalid_standing")
    basis = [_text(item, "basis") for item in _rows(row["basis"], 32, "basis")]
    if not basis or len(set(basis)) != len(basis):
        raise ValueError("estimand_basis_empty_or_duplicate")


def _ref(raw: object) -> dict:
    row = _object(raw, REF_FIELDS, "reference")
    _text(row["ref"], "ref")
    _text(row["version"], "ref:version")
    _standing(row)
    return row


def _definitions(raw: object) -> dict:
    row = _object(raw, DEFINITION_KEYS, "definitions")
    return {key: _ref(value) for key, value in row.items()}


def _events(raw: object) -> dict[str, dict]:
    result = {}
    for value in _rows(raw, LIMIT, "events"):
        row = _object(value, {"id", "event_ref", "strategy", "status", "resolution", "basis"}, "event")
        identity = _text(row["id"], "event:id")
        if identity in result:
            raise ValueError("estimand_duplicate_event")
        _ref(row["event_ref"])
        _standing(row)
        if row["strategy"] not in STRATEGIES:
            raise ValueError("estimand_unsupported_strategy")
        result[identity] = row
    return result


def _requirements(raw: object, events: dict[str, dict], variable: str) -> dict[str, dict]:
    result = {}
    fields = {"id", "event", "variable", "window", "role", "mode", "relevance", "rule"}
    for value in _rows(raw, LIMIT, "requirements"):
        row = _object(value, fields, "requirement")
        identity = _text(row["id"], "requirement:id")
        if identity in result:
            raise ValueError("estimand_duplicate_requirement")
        _text(row["event"], "requirement:event")
        if row["event"] not in events:
            raise ValueError("estimand_unknown_event")
        if row["variable"] != variable:
            raise ValueError("estimand_variable_mismatch")
        _text(row["window"], "requirement:window")
        if row["role"] not in ("observed_measurement", "event_ascertainment", "estimator_input"):
            raise ValueError("estimand_unsupported_role")
        if row["mode"] not in dependency_evidence.MODES or row["relevance"] not in RELEVANCE:
            raise ValueError("estimand_unsupported_requirement")
        if row["role"] == "observed_measurement" and row["mode"] != "observed":
            raise ValueError("estimand_observed_mode_mismatch")
        _ref(row["rule"])
        result[identity] = row
    return result


def _plans(raw: object, requirements: dict[str, dict]) -> dict[str, dict]:
    result = {}
    for value in _rows(raw, LIMIT, "collection_plan"):
        row = _object(value, {"requirement", "action", "status", "resolution", "basis"}, "plan")
        _text(row["requirement"], "plan:requirement")
        if row["requirement"] not in requirements:
            raise ValueError("estimand_unknown_plan_requirement")
        if row["requirement"] in result:
            raise ValueError("estimand_duplicate_plan")
        if row["action"] not in ("collect", "stop", "unknown"):
            raise ValueError("estimand_unsupported_plan")
        _standing(row)
        result[row["requirement"]] = row
    return result


def _facts(raw: object, requirements: dict[str, dict]) -> list[dict]:
    result, identities = [], set()
    for value in _rows(raw, LIMIT * 2, "data_state"):
        row = _object(value, {"requirement", "mode", "state", "rule"}, "data_state")
        _text(row["requirement"], "data_state:requirement")
        if row["requirement"] not in requirements or row["mode"] not in dependency_evidence.MODES:
            raise ValueError("estimand_unknown_data_input")
        if row["state"] not in ("available", "unavailable", "unknown", "structurally_unavailable"):
            raise ValueError("estimand_unsupported_data_state")
        _ref(row["rule"])
        identity = (row["requirement"], row["mode"], row["state"])
        if identity in identities:
            raise ValueError("estimand_duplicate_data_state")
        identities.add(identity)
        result.append(row)
    return result


def _gate(refs: list[dict]) -> str:
    return support_state([row["status"] for row in refs], [row["resolution"] for row in refs])


def _support(refs: list[dict]) -> str | None:
    if _gate(refs) != "accepted":
        return None
    return "interpolated" if any(row["status"] == "interpolated" for row in refs) else "known"


def _local(requirement: dict, definitions: dict, events: dict, plans: dict, facts: list[dict]) -> dict:
    identity = requirement["id"]
    event = events[requirement["event"]]
    refs = [
        definitions["variable"],
        definitions["intercurrent_events"],
        event["event_ref"],
        event,
        requirement["rule"],
    ]
    gate = _gate(refs)
    relevance = requirement["relevance"] if gate == "accepted" else "unresolved"
    blockers = [] if gate == "accepted" else ["estimand_" + gate + ":" + identity]
    if relevance == "unresolved":
        blockers.append("estimand_relevance_unresolved:" + identity)
    relevance_blockers = list(blockers)
    plan = plans.get(identity)
    plan_refs = [*refs, plan] if plan is not None else refs
    plan_gate = _gate(plan_refs)
    action = plan["action"] if plan is not None and plan_gate == "accepted" else "unknown"
    alignment = collection_alignment(relevance, action)
    collection_blockers = list(relevance_blockers)
    if alignment != "aligned":
        collection_blockers.append("estimand_" + alignment + ":" + identity)
        if plan is not None and plan_gate != "accepted":
            collection_blockers.append("estimand_" + plan_gate + ":collection:" + identity)
    actual_blockers = []
    matching = [row for row in facts if row["requirement"] == identity and row["mode"] == requirement["mode"]]
    accepted = [row for row in matching if _gate([row["rule"]]) == "accepted"]
    states = {row["state"] for row in accepted} - {"unknown"}
    contradictory = "available" in states and bool(states & {"unavailable", "structurally_unavailable"})
    state = (
        "unknown"
        if contradictory or not states
        else "structurally_unavailable"
        if ("structurally_unavailable" in states)
        else next(iter(states))
    )
    actual_refs = [definitions["variable"], event["event_ref"], *(row["rule"] for row in accepted)]
    actual_gate = _gate(actual_refs) if accepted else "missing_support"
    input_code = actual_input(relevance, state if actual_gate == "accepted" else "unknown")
    if accepted and actual_gate != "accepted":
        actual_blockers.append("estimand_" + actual_gate + ":actual:" + identity)
    if contradictory:
        actual_blockers.append("estimand_availability_conflict:" + identity)
    if input_code in ("missing_relevant", "unresolved") or (
        input_code == "structurally_unavailable" and relevance == "required"
    ):
        actual_blockers.append("estimand_" + input_code + ":" + identity)
    if input_code not in ("available", "structurally_unavailable"):
        actual_blockers.extend(relevance_blockers)
    input_refs = actual_refs if accepted else []
    if state in ("available", "unavailable", "structurally_unavailable"):
        known = [row for row in accepted if row["state"] == state and row["rule"]["status"] == "known"]
        if known and all(ref["status"] == "known" for ref in actual_refs[:2]):
            input_refs = [*actual_refs[:2], *(row["rule"] for row in known)]
    if input_code in ("missing_relevant", "not_required_for_this_estimand"):
        input_refs = [*refs, *input_refs]
    return {
        "id": identity,
        "declaration": deepcopy(requirement),
        "event": deepcopy(event),
        "relevance": relevance,
        "relevance_status": _support(refs),
        "collection_alignment": alignment,
        "collection_status": (
            _support(refs)
            if relevance == "not_required_for_this_estimand"
            else _support(plan_refs)
            if plan is not None
            else None
        ),
        "collection_plan": deepcopy(plan),
        "actual_input": input_code,
        "actual_status": _support(input_refs),
        "recorded_state": state,
        "data_state": deepcopy(matching),
        "relevance_blockers": sorted(set(relevance_blockers)),
        "collection_blockers": sorted(set(collection_blockers)),
        "actual_blockers": sorted(set(actual_blockers)),
        "blockers": sorted(set(relevance_blockers + collection_blockers + actual_blockers)),
        "estimation": "not_computed",
    }


def _merged_request(base: dict, facts: list[dict]) -> dict:
    prepared = deepcopy(base)
    available = {(row["id"], row["mode"]) for row in base["available"]}
    unavailable = {(row["id"], row["mode"]) for row in base["unavailable"]}
    for row in facts:
        if row["state"] == "available":
            available.add((row["requirement"], row["mode"]))
        elif row["state"] in ("unavailable", "structurally_unavailable"):
            unavailable.add((row["requirement"], row["mode"]))
    prepared["available"] = [{"id": identity, "mode": mode} for identity, mode in sorted(available)]
    prepared["unavailable"] = [{"id": identity, "mode": mode} for identity, mode in sorted(unavailable)]
    return prepared


def _binding_refs(requirements: list[dict], definitions: dict, events: dict) -> list[dict]:
    refs = []
    for row in requirements:
        event = events[row["event"]]
        refs.extend(
            [
                definitions["variable"],
                definitions["intercurrent_events"],
                event["event_ref"],
                event,
                row["rule"],
            ]
        )
    return refs


def _dependency_check(identity: str, prepared: dict, facts: list[dict], refs: list[dict]) -> dict:
    accepted = [row for row in facts if _gate([row["rule"]]) == "accepted"]
    effective_request = _merged_request(prepared, accepted)
    effective = dependency_evidence.evaluate("dependencies", effective_request)
    gate = _gate(refs) if refs else "accepted"
    code = effective["code"] if gate == "accepted" else "unresolved"
    support = None
    deciding_refs = [*refs, *(row["rule"] for row in accepted)]
    if code != "unresolved":
        known_request = _merged_request(
            prepared, [row for row in accepted if row["rule"]["status"] == "known"]
        )
        known_result = dependency_evidence.evaluate("dependencies", known_request)
        if all(ref["status"] == "known" for ref in refs) and known_result["code"] == code:
            support = "known"
            deciding_refs = [row for row in deciding_refs if row["status"] == "known"]
            effective_request, effective = known_request, known_result
        else:
            support = _support(deciding_refs) if deciding_refs else "known"
    blockers = list(effective["blockers"])
    if gate != "accepted":
        blockers.append("estimand_" + gate + ":" + identity)
    return {
        "id": identity,
        "code": code,
        "status": support,
        "gate": gate,
        "request": effective_request,
        "result": effective,
        "blockers": sorted(set(blockers)),
        "deciding_refs": deepcopy(deciding_refs),
        "pending_facts": deepcopy([row for row in facts if _gate([row["rule"]]) != "accepted"]),
    }


def _dependency(data: dict, requirements: dict, facts: list[dict], definitions: dict, events: dict) -> dict:
    supplied = data["dependencies"]
    base = (
        {
            "scope": data["scope"],
            "version": data["version"],
            "rules": [],
            "adopted": [],
            "available": [],
            "unavailable": [],
            "conditions": {},
        }
        if supplied is None
        else deepcopy(supplied)
    )
    if (
        not isinstance(base, dict)
        or base.get("scope") != data["scope"]
        or base.get("version") != data["version"]
    ):
        raise ValueError("estimand_dependency_scope_mismatch")
    dependency_evidence.evaluate("dependencies", base)
    rules = {rule["id"]: rule for rule in base["rules"]}
    outputs = {rule["output"]["id"] for rule in base["rules"]}
    mentioned = {
        item["id"] for rule in base["rules"] for alternative in rule["alternatives"] for item in alternative
    } | {item["id"] for key in ("available", "unavailable") for item in base[key]}
    if mentioned - requirements.keys() - outputs:
        raise ValueError("estimand_unknown_dependency_input")
    raw_request = _merged_request(base, facts)
    raw_result = dependency_evidence.evaluate("dependencies", raw_request)
    checks = []
    inputs = {(row["requirement"], row["mode"]) for row in facts}
    inputs.update((row["id"], row["mode"]) for key in ("available", "unavailable") for row in base[key])
    for identity, mode in sorted(inputs):
        request = {
            **deepcopy(base),
            "adopted": [],
            "available": [row for row in base["available"] if (row["id"], row["mode"]) == (identity, mode)],
            "unavailable": [
                row for row in base["unavailable"] if (row["id"], row["mode"]) == (identity, mode)
            ],
        }
        local = [row for row in facts if (row["requirement"], row["mode"]) == (identity, mode)]
        refs = (
            _binding_refs([requirements[identity]], definitions, events) if identity in requirements else []
        )
        checks.append(_dependency_check("availability:" + identity + ":" + mode, request, local, refs))
    producers: dict[str, set[str]] = {}
    for key, rule in rules.items():
        producers.setdefault(rule["output"]["id"], set()).add(key)
    for identity in sorted(base["adopted"]):
        closure = {identity}
        for _ in range(len(rules)):
            needed = {item["id"] for key in closure for alt in rules[key]["alternatives"] for item in alt}
            expanded = closure | {
                key for item in needed for key in producers.get(item, set()) if key in base["adopted"]
            }
            if expanded == closure:
                break
            closure = expanded
        mentioned_here = {item["id"] for key in closure for alt in rules[key]["alternatives"] for item in alt}
        mentioned_here.update(rules[key]["output"]["id"] for key in closure)
        request = {
            **deepcopy(base),
            "adopted": sorted(closure),
            "available": [row for row in base["available"] if row["id"] in mentioned_here],
            "unavailable": [row for row in base["unavailable"] if row["id"] in mentioned_here],
        }
        local = [row for row in facts if row["requirement"] in mentioned_here]
        refs = _binding_refs(
            [requirements[key] for key in sorted(mentioned_here & requirements.keys())], definitions, events
        )
        checks.append(_dependency_check("adopted:" + identity, request, local, refs))
    return {"raw_request": raw_request, "raw_result": raw_result, "checks": checks}


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Check supplied relevance, collection and inputs separately, preserving exact dependency results."""
    if kind != "estimand":
        raise ValueError("unsupported_estimand_kind")
    if not isinstance(claims, list) or claims:
        raise ValueError("estimand_candidate_claims_unsupported")
    data = _object(data, set(INPUTS["estimand"]["required"]), "data")
    for field in ("scope", "version", "id"):
        _text(data[field], field)
    definitions = _definitions(data["definitions"])
    events = _events(data["events"])
    requirements = _requirements(data["requirements"], events, definitions["variable"]["ref"])
    plans = _plans(data["collection_plan"], requirements)
    facts = _facts(data["data_state"], requirements)
    rows = [_local(requirements[key], definitions, events, plans, facts) for key in sorted(requirements)]
    dependency = _dependency(data, requirements, facts, definitions, events)
    dependency_checks = dependency["checks"]
    conflicts = [row for row in dependency_checks if row["code"] == "conflict"]
    dependency_code = (
        "conflict"
        if conflicts
        else "unresolved"
        if any(row["code"] == "unresolved" for row in dependency_checks)
        else "consistent"
    )
    definition_checks = [
        {"attribute": key, "declaration": deepcopy(definitions[key]), "code": _gate([definitions[key]])}
        for key in sorted(definitions)
    ]
    event_checks = [
        {
            "id": key,
            "strategy": events[key]["strategy"],
            "code": _gate([events[key], events[key]["event_ref"]]),
        }
        for key in sorted(events)
    ]
    complete = all(row["code"] == "accepted" for row in definition_checks) and all(
        row["code"] == "accepted" and row["strategy"] != "unresolved" for row in event_checks
    )
    blockers = {blocker for row in rows for blocker in row["blockers"]}
    blockers.update(blocker for row in dependency_checks for blocker in row["blockers"])
    if not complete:
        blockers.add("estimand_definition_unresolved")
    if conflicts:
        code = "conflict"
        support = "known" if any(row["status"] == "known" for row in conflicts) else "interpolated"
        deciding = [row["id"] for row in conflicts if row["status"] == support]
    elif blockers or dependency_code == "unresolved":
        code, support, deciding = "unresolved", None, []
    else:
        code = "consistent"
        refs = [
            *definitions.values(),
            *events.values(),
            *(row["event_ref"] for row in events.values()),
            *(row["rule"] for row in requirements.values()),
            *plans.values(),
        ]
        refs.extend(row["rule"] for row in facts if _gate([row["rule"]]) == "accepted")
        support = _support(refs) if requirements else None
        deciding = sorted(requirements)
    return {
        "code": code,
        "support_status": support,
        "determining_ids": deciding,
        "value": {
            "scope": data["scope"],
            "version": data["version"],
            "id": data["id"],
            "definition_state": "complete" if complete else "unresolved",
            "definition_checks": definition_checks,
            "event_checks": event_checks,
            "events": deepcopy(data["events"]),
            "data_state": deepcopy(data["data_state"]),
            "requirements": rows,
            "dependency_request": dependency["raw_request"],
            "dependency_result": dependency["raw_result"],
            "dependency_code": dependency_code,
            "dependency_checks": dependency_checks,
            "estimation": "not_computed",
            "witnesses": [],
        },
        "blockers": sorted(blockers),
        "rule": "estimand.supplied_relevance:1",
    }


def evaluate(kind: str, data: dict) -> dict:
    """Check one declared estimand; no source reading or inferred statistical method."""
    return check(kind, data, [])


def _example() -> dict:
    def reference(name: str) -> dict:
        return {
            "ref": "invented:" + name,
            "version": "1",
            "status": "known",
            "resolution": "resolved",
            "basis": ["invented:declared-example-not-registry-evidence"],
        }

    definitions = {key: reference(key) for key in sorted(DEFINITION_KEYS)}
    return {
        "scope": "invented:HF:cohort-A:week12",
        "version": "1",
        "id": "invented:week12-policy",
        "definitions": definitions,
        "events": [
            {
                "id": "discontinuation",
                "event_ref": reference("treatment-discontinuation"),
                "strategy": "treatment_policy",
                "status": "known",
                "resolution": "resolved",
                "basis": ["invented:chosen-event-handling"],
            }
        ],
        "requirements": [
            {
                "id": "week12",
                "event": "discontinuation",
                "variable": definitions["variable"]["ref"],
                "window": "invented:week12-regardless-of-discontinuation",
                "role": "observed_measurement",
                "mode": "observed",
                "relevance": "required",
                "rule": reference("week12-relevance"),
            }
        ],
        "collection_plan": [
            {
                "requirement": "week12",
                "action": "stop",
                "status": "known",
                "resolution": "resolved",
                "basis": ["invented:stop-after-discontinuation"],
            }
        ],
        "data_state": [],
        "dependencies": None,
    }


EXAMPLES = {"estimand": _example()}
