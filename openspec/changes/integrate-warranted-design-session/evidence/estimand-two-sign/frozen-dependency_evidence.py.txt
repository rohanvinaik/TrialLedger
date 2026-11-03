"""Typed prerequisite constraints for explicitly adopted measurement/calculation rules.

No text, label or guideline is interpreted here. A caller supplies scoped/versioned rules and the distinct
availability of observed, imputed and derived inputs. Absence stays unknown; adoption is explicit. Only a
derived output can be produced by a rule, so a calculation never manufactures an observed measurement.
"""

from __future__ import annotations

from typing import Any

LIMIT = 1000
MODES = ("observed", "imputed", "derived")
TRUTHS = ("true", "false", "unknown")
INPUTS = {
    "dependencies": {
        "required": ("scope", "version", "rules", "adopted", "available", "unavailable", "conditions"),
        "fields": {
            "scope": "nonempty reference binding all rules, inputs and conditions to one applicable scope",
            "version": "nonempty version of the declared dependency representation",
            "rules": "array of distinct {id,version,output,alternatives,when} rule objects",
            "adopted": "distinct ids of explicitly adopted rules; an unadopted rule imposes nothing",
            "available": "array of {id,mode} inputs; mode observed, imputed or derived",
            "unavailable": "array of explicitly unavailable {id,mode} inputs; missing is unknown",
            "conditions": "object of condition ids to true/false/unknown strings; missing ids are unknown",
        },
        "rule": {
            "id": "distinct nonempty rule id",
            "version": "nonempty source/definition version",
            "output": "{id,mode:derived}; calculations cannot create observed or imputed measurements",
            "alternatives": "nonempty OR of AND arrays of {id,mode} prerequisite objects",
            "when": "AND array of {id,is:true|false}; explicit [] is unconditional",
        },
        "claim": {
            "fields": ("available", "unavailable", "adopted", "conditions"),
            "meaning": "add facts jointly; conditions refine unknown, never overwrite dissent",
        },
    }
}
EXAMPLES = {
    "dependencies": {
        "scope": "invented:cohort-and-assessment-window",
        "version": "1",
        "rules": [
            {
                "id": "change",
                "version": "invented-definition-1",
                "output": {"id": "change", "mode": "derived"},
                "alternatives": [
                    [{"id": "baseline", "mode": "observed"}, {"id": "week12", "mode": "observed"}]
                ],
                "when": [],
            }
        ],
        "adopted": ["change"],
        "available": [{"id": "baseline", "mode": "observed"}],
        "unavailable": [],
        "conditions": {},
    }
}


def alternative_state(inputs: list[str]) -> str:
    """One AND alternative of typed prerequisite availability (pure — pinned)."""
    if "unavailable" in inputs:
        return "blocked"
    if "unknown" in inputs:
        return "unresolved"
    return "ready"


def guard_state(matches: list[str]) -> str:
    """An AND guard: false defeats unknown; unknown never silently activates it (pure — pinned)."""
    if "false" in matches:
        return "inactive"
    if "unknown" in matches:
        return "unresolved"
    return "active"


def prerequisite_state(guard: str, alternatives: list[str]) -> str:
    """An explicit guard and OR of prerequisite alternatives (pure — pinned)."""
    if guard == "inactive":
        return "inactive"
    if guard == "unresolved":
        return "unresolved"
    if "ready" in alternatives:
        return "ready"
    if alternatives and all(state == "blocked" for state in alternatives):
        return "blocked"
    return "unresolved"


def condition_join(current: str, incoming: str) -> str:
    """Refine a declared condition without choosing a conflicting source (pure — pinned)."""
    if current == "unknown":
        return incoming
    if incoming == "unknown" or incoming == current:
        return current
    return "conflict"


def _object(value: Any, fields: set[str], required: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"not_an_object:{where}")
    if set(value) - fields:
        raise ValueError(f"unknown_field:{where}")
    if required - set(value):
        raise ValueError(f"missing_field:{where}")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"not_text:{where}")
    return value


def _list(value: Any, where: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"not_a_list:{where}")
    if len(value) > LIMIT:
        raise ValueError(f"resource_bound:{where}")
    return value


def _measurement(value: Any) -> tuple[str, str]:
    item = _object(value, {"id", "mode"}, {"id", "mode"}, "measurement")
    mode = item["mode"]
    if not isinstance(mode, str) or mode not in MODES:
        raise ValueError("measurement_mode_outside_vocabulary")
    return _text(item["id"], "measurement:id"), mode


def _measurements(value: Any) -> set[tuple[str, str]]:
    held = [_measurement(raw) for raw in _list(value, "measurements")]
    if len(set(held)) != len(held):
        raise ValueError("duplicate_measurement")
    return set(held)


def _conditions(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or len(value) > LIMIT:
        raise ValueError("invalid_dependency_conditions")
    held = {}
    for identity, state in value.items():
        _text(identity, "condition:id")
        if not isinstance(state, str) or state not in TRUTHS:
            raise ValueError("condition_state_outside_vocabulary")
        held[identity] = state
    return held


def _rules(value: Any) -> dict[str, dict]:
    result = {}
    requirements = 0
    for raw in _list(value, "rules"):
        fields = {"id", "version", "output", "alternatives", "when"}
        item = _object(raw, fields, fields, "rule")
        identity = _text(item["id"], "rule:id")
        if identity in result:
            raise ValueError("duplicate_dependency_rule")
        version = _text(item["version"], "rule:version")
        output = _measurement(item["output"])
        if output[1] != "derived":
            raise ValueError("rule_output_not_derived")
        alternatives = [_measurements(group) for group in _list(item["alternatives"], "alternatives")]
        if not alternatives:
            raise ValueError("missing_dependency_alternative")
        when = []
        for raw_guard in _list(item["when"], "when"):
            guard = _object(raw_guard, {"id", "is"}, {"id", "is"}, "guard")
            condition = _text(guard["id"], "guard:id")
            expected = guard["is"]
            if not isinstance(expected, str) or expected not in TRUTHS[:2]:
                raise ValueError("guard_state_outside_vocabulary")
            when.append((condition, expected))
        if len({key for key, _ in when}) != len(when):
            raise ValueError("duplicate_dependency_guard")
        requirements += sum(len(group) for group in alternatives) + len(when)
        if requirements > LIMIT:
            raise ValueError("resource_bound:dependency_requirements")
        result[identity] = {"version": version, "output": output, "alternatives": alternatives, "when": when}
    return result


def _adopted(value: Any, rules: dict) -> set[str]:
    held = [_text(raw, "adopted:id") for raw in _list(value, "adopted")]
    if len(set(held)) != len(held):
        raise ValueError("duplicate_adopted_rule")
    if set(held) - rules.keys():
        raise ValueError("unknown_adopted_rule")
    return set(held)


def _input_state(item: tuple[str, str], available: set, unavailable: set) -> str:
    if item in available:
        return "available"
    return "unavailable" if item in unavailable else "unknown"


def _rule_reading(rule: dict, available: set, unavailable: set, conditions: dict) -> tuple[str, list[str]]:
    matches = [
        "unknown"
        if conditions.get(key, "unknown") == "unknown"
        else "true"
        if conditions[key] == expected
        else "false"
        for key, expected in rule["when"]
    ]
    alternatives = [
        alternative_state([_input_state(item, available, unavailable) for item in group])
        for group in rule["alternatives"]
    ]
    state = prerequisite_state(guard_state(matches), alternatives)
    missing = [
        f"{identity}:{mode}"
        for group in rule["alternatives"]
        for identity, mode in sorted(group)
        if (identity, mode) not in available
    ]
    return state, sorted(set(missing))


def _solve(
    rules: dict, adopted: set[str], available: set, unavailable: set, conditions: dict, conflicts: list[str]
) -> dict:
    available = set(available)
    for _ in range(len(adopted) + 1):
        before = len(available)
        for identity in sorted(adopted):
            rule = rules[identity]
            state, _ = _rule_reading(rule, available, unavailable, conditions)
            if state == "ready":
                available.add(rule["output"])
        if len(available) == before:
            break
    rows, blockers = [], list(conflicts)
    for identity, mode in sorted(available & unavailable):
        blockers.append(f"availability_conflict:{identity}:{mode}")
    for identity in sorted(adopted):
        rule = rules[identity]
        state, missing = _rule_reading(rule, available, unavailable, conditions)
        alternatives = [
            [
                {"id": key, "mode": mode, "state": _input_state((key, mode), available, unavailable)}
                for key, mode in sorted(group)
            ]
            for group in rule["alternatives"]
        ]
        guards = [
            {"id": key, "is": expected, "state": conditions.get(key, "unknown")}
            for key, expected in rule["when"]
        ]
        output_id, output_mode = rule["output"]
        rows.append(
            {
                "id": identity,
                "version": rule["version"],
                "state": state,
                "missing": missing,
                "output": {"id": output_id, "mode": output_mode},
                "alternatives": alternatives,
                "when": guards,
            }
        )
        if state in ("blocked", "unresolved"):
            blockers.append(f"dependency_{state}:{identity}")
    if conflicts or available & unavailable or any(row["state"] == "blocked" for row in rows):
        code = "conflict"
    elif any(row["state"] == "unresolved" for row in rows):
        code = "unresolved"
    else:
        code = "consistent"
    return {
        "code": code,
        "value": {
            "rules": rows,
            "available": [{"id": identity, "mode": mode} for identity, mode in sorted(available)],
            "witnesses": [],
        },
        "blockers": sorted(set(blockers)),
        "rule": "dependencies.explicit_prerequisites.v1",
    }


def _evaluate(data: dict, claims: list[dict]) -> dict:
    fields = set(INPUTS["dependencies"]["required"])
    value = _object(data, fields, fields, "dependencies")
    _text(value["scope"], "scope")
    _text(value["version"], "version")
    rules = _rules(value["rules"])
    adopted = _adopted(value["adopted"], rules)
    available, unavailable = _measurements(value["available"]), _measurements(value["unavailable"])
    conditions = _conditions(value["conditions"])
    conflicts = []
    conflicting_conditions = set()
    for raw in _list(claims, "claims"):
        claim = _object(raw, {"available", "unavailable", "adopted", "conditions"}, set(), "dependency_claim")
        if not claim:
            raise ValueError("empty_dependency_claim")
        available |= _measurements(claim.get("available", []))
        unavailable |= _measurements(claim.get("unavailable", []))
        adopted |= _adopted(claim.get("adopted", []), rules)
        for identity, incoming in _conditions(claim.get("conditions", {})).items():
            if identity in conflicting_conditions:
                continue
            current = conditions.get(identity, "unknown")
            joined = condition_join(current, incoming)
            if joined == "conflict":
                conflicts.append(f"condition_conflict:{identity}")
                conflicting_conditions.add(identity)
                conditions[identity] = "unknown"
            else:
                conditions[identity] = joined
    if max(len(available), len(unavailable), len(conditions)) > LIMIT:
        raise ValueError("resource_bound:dependency_facts")
    result = _solve(rules, adopted, available, unavailable, conditions, conflicts)
    result["value"].update({"scope": value["scope"], "version": value["version"]})
    return result


def evaluate(kind: str, data: dict) -> dict:
    """Evaluate explicitly adopted rules without I/O or inferred measurement roles."""
    if kind != "dependencies":
        raise ValueError("unsupported_dependency_kind")
    return _evaluate(data, [])


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Apply all candidate facts jointly; conflicting sources/claims never overwrite one another."""
    if kind != "dependencies":
        raise ValueError("unsupported_dependency_kind")
    return _evaluate(data, claims)
