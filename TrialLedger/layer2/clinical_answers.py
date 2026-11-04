"""Clinical projections of existing effective findings, with canonical result addresses.

The metadata owner classifies admission and standing. This module selects readable
information and independent change axes; it never decides a clinical proposition.
"""

from __future__ import annotations

import json
from typing import cast

from TrialLedger.layer2 import result_semantics, source_evidence

VALUE_FIELDS = (
    "id",
    "label",
    "name",
    "count",
    "count_lower",
    "count_upper",
    "denominator",
    "max_exceptions",
    "bounds",
    "count_kind",
    "witness_threshold",
    "direction",
    "lower",
    "upper",
    "value",
    "values",
    "remaining",
    "members",
    "total",
    "counts",
    "unit",
    "period",
    "time_frame",
    "stating",
    "trials",
    "unresolved",
    "threshold",
    "tier",
    "description",
    "category",
    "group",
    "rarity",
    "bits",
    "pair",
    "difference",
    "years",
    "sponsors",
    "sign",
    "profile",
    "witness",
    "requests",
    "comparison",
    "required_premises",
    "occupied",
    "unknown",
    "empty",
    "known",
    "interpolated",
    "proposals",
    "effect",
    "removed",
)
SCOPE_FIELDS = ("target", "context", "cohort", "scope", "population", "universe", "study_ref", "time")
SUPPORT_FIELDS = (
    "proof",
    "basis",
    "rule",
    "warrant",
    "support",
    "binding_support",
    "application",
    "admission",
    "elimination_status",
    "feasibility_status",
    "guarantee",
    "assumptions",
    "exception_check",
    "decision",
)
ORIGIN_FIELDS = ("origin", "origin_refs", "criterion_ref")


def _copy(value: object) -> object:
    """Normalize tuples only; no clinical or numeric normalization."""
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _selected(root: dict, path: str) -> object:
    try:
        return source_evidence._selected(root, path)
    except (ValueError, KeyError, TypeError, IndexError):
        return None


def _ancestors(root: dict, path: str) -> list[dict]:
    """Actual containing objects, nearest first, using the shared exact pointer owner."""
    paths = [path]
    while paths[-1]:
        paths.append(paths[-1].rpartition("/")[0])
    return [v for p in paths if isinstance(v := _selected(root, p), dict)]


def _fields(row: dict, names: tuple[str, ...]) -> dict:
    return {name: _copy(row[name]) for name in names if name in row}


def _query(row: dict) -> object:
    value = row.get("query", row.get("body"))
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except ValueError:
            return value
        return decoded if isinstance(decoded, dict) else value
    return _copy(value)


def _proof_ids(value: object) -> set[str]:
    if isinstance(value, list | tuple):
        return set().union(*(_proof_ids(item) for item in value)) if value else set()
    if not isinstance(value, dict):
        return set()
    found = {
        ref
        for name in ("proof", "basis", "premises")
        for ref in (value[name] if isinstance(value.get(name), list | tuple) else ())
        if isinstance(ref, str)
    }
    for name in ("warrant", "decision", "alternatives", "distinctions", "support", "conditions", "rule"):
        found.update(_proof_ids(value.get(name)))
    return found


def _support_payload(value: object) -> object:
    """Keep typed support, excluding documentary attribution and the asked query."""
    if isinstance(value, list | tuple):
        return [_support_payload(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _support_payload(item)
            for key, item in value.items()
            if key not in (*ORIGIN_FIELDS, "query", "span", "evidence")
        }
    return value


def _premise_support(value: object, ids: set[str]) -> list[dict]:
    """Resolve exact deciding IDs into their current typed payload and standing."""
    if isinstance(value, list | tuple):
        return [row for item in value for row in _premise_support(item, ids)]
    if not isinstance(value, dict):
        return []
    if value.get("id") in ids:
        held = cast(dict, _support_payload(value))
        if "payload" in value:
            # These basis references name the exchange/source, not a different
            # logical premise. Payload rules and declared dependencies stay intact.
            for name in ("standing", "dependency_support"):
                if isinstance(held.get(name), dict):
                    held[name].pop("basis", None)
        return [{"premise": value["id"], "version": 1, "value": held}]
    return [
        row
        for name in ("assertions", "assumptions", "premises", "fixed", "effective_premises")
        for row in _premise_support(value.get(name), ids)
    ]


def _resolved_support(ancestors: list[dict], ids: set[str]) -> list[dict]:
    """Nearest complete premise representation wins; unrelated inputs stay out."""
    out = {}
    for ancestor in ancestors:
        # Effective session values include payload, standing and derivation dependencies.
        for name in ("effective_premises", "premises", "assertions", "assumptions", "fixed"):
            for row in _premise_support(ancestor.get(name), ids - out.keys()):
                out.setdefault(row["premise"], row)
    return [out[key] for key in sorted(out)]


def _premise_origins(value: object, ids: set[str]) -> list[dict]:
    rows = []
    if isinstance(value, list | tuple):
        for item in value:
            rows.extend(_premise_origins(item, ids))
    elif isinstance(value, dict):
        if value.get("id") in ids:
            held = _fields(value, ORIGIN_FIELDS)
            if held:
                rows.append({"premise": value["id"], **held})
        for name in ("assertions", "assumptions", "premises", "payload", "fixed", "effective_premises"):
            if name in value:
                rows.extend(_premise_origins(value[name], ids))
    return rows


def _origins(raw: dict, ancestors: list[dict], support: dict, permissions: list, conditions: list) -> list:
    rows = []
    explicit = _fields(raw, ORIGIN_FIELDS)
    if explicit:
        rows.append(explicit)
    ids = _proof_ids(raw) | _proof_ids(support)
    for condition in conditions:
        ids.update(_proof_ids(condition))
    ids.update(p["id"] for p in permissions if isinstance(p, dict) and "id" in p)
    for ancestor in ancestors:
        found = []
        for name in ("premises", "assertions", "assumptions", "fixed", "effective_premises"):
            found.extend(_premise_origins(ancestor.get(name), ids))
        if found:
            rows.extend(found)
            ids.difference_update(row["premise"] for row in found)
        if not ids:
            break
    for permission in permissions:
        if isinstance(permission, dict) and "criterion_ref" in permission:
            rows.append({"premise": permission["id"], "criterion_ref": permission["criterion_ref"]})
    unique = {json.dumps(row, sort_keys=True, ensure_ascii=False): row for row in rows}
    return [unique[key] for key in sorted(unique)]


def _scope(raw: dict, ancestors: list[dict]) -> dict:
    scope = {}
    for ancestor in ancestors:
        for key, value in _fields(ancestor, SCOPE_FIELDS).items():
            scope.setdefault(key, value)
    query = _query(raw)
    if query is not None:
        scope["query"] = query
    return scope


def _explanations(raw: dict, ancestors: list[dict]) -> dict:
    if isinstance(raw.get("explanations"), dict):
        return raw["explanations"]
    for ancestor in ancestors:
        if ancestor.get("decision") is raw and isinstance(ancestor.get("explanations"), dict):
            return ancestor["explanations"]
        if ancestor.get("query_decision") is raw and isinstance(ancestor.get("query_explanations"), dict):
            return ancestor["query_explanations"]
    return {}


def _decision_values(raw: dict) -> dict:
    selected = raw.get("selected")
    return {
        "id": raw.get("id"),
        "question": raw.get("question"),
        "selected": {"alternative": selected["alternative"]} if isinstance(selected, dict) else None,
        "alternatives": [
            _fields(option, ("id", "label", "query", "code")) for option in raw.get("alternatives", ())
        ],
        "distinctions": [_fields(check, ("alternatives", "code")) for check in raw.get("distinctions", ())],
    }


def _decision_support(raw: dict) -> dict:
    return {
        **_fields(
            raw, ("coverage", "coverage_limit", "determining_alternatives", "determining_distinctions")
        ),
        "alternatives": [
            _fields(option, ("id", "warrant", "feasibility_status")) for option in raw.get("alternatives", ())
        ],
        "distinctions": [
            {
                **_fields(check, ("alternatives", "code", "support_status")),
                "support": change_projection(
                    check["result"].get("operation", ""), check["result"].get("result")
                )["support"]
                if isinstance(check.get("result"), dict)
                else None,
            }
            for check in raw.get("distinctions", ())
        ],
    }


def _finding(root: dict, meta: dict) -> dict:
    path = meta["path"]
    selected = _selected(root, path)
    ancestors = _ancestors(root, path)
    raw = selected if isinstance(selected, dict) else ancestors[0] if ancestors else {}
    support = _fields(raw, SUPPORT_FIELDS)
    if meta.get("kind") == "session_decision":
        support = _decision_support(raw)
    elif "support_path" in meta:
        support["declared_support"] = _copy(_selected(root, meta["support_path"]))
    explanations = _explanations(raw, ancestors)
    permissions = explanations.get("permissions", [])
    values = _decision_values(raw) if meta.get("kind") == "session_decision" else _fields(raw, VALUE_FIELDS)
    if permissions:
        values["permissions"] = [
            _fields(p, ("id", "code", "body", "applicability", "scope")) for p in permissions
        ]
        support["permissions"] = [_fields(p, ("id", "status", "rule", "blockers")) for p in permissions]
    if explanations:
        support["explanation_blockers"] = _copy(explanations.get("blockers", []))
    if meta.get("completion") == "unclassified" or meta.get("kind") == "unclassified":
        values["unclassified"] = _copy(selected)
    return {
        "path": path,
        "kind": meta.get("kind", "unclassified"),
        "outcome": meta.get("logical_result", ""),
        "standing": meta.get("standing"),
        "completion": meta.get("completion", "unclassified"),
        "disposition": meta.get("disposition", "unclassified"),
        "scope": _scope(raw, ancestors),
        "values": values,
        "support": support,
        "origins": _origins(raw, ancestors, support, permissions, explanations.get("conditions", [])),
        "conditions": _copy(explanations.get("conditions", [])),
        "blockers": [row["code"] for row in meta.get("causes", ())],
        "canonical_ref": path,
    }


def project(operation: str, result: object, problems: tuple | list = ()) -> dict:
    """Project effective metadata findings, keeping unknown outcomes inspectable."""
    meta = result_semantics.metadata(operation, result, problems)
    root = {"result": result, "problems": problems}
    return {
        "version": 1,
        "operation": operation,
        "findings": [_finding(root, finding) for finding in meta["findings"]],
    }


def change_projection(operation: str, result: object) -> dict:
    """Independent typed question, wording, answer, support, origin and context axes.

    Caller wording never certifies clinical meaning. Deciding support versions are
    resolved only for actual warrant IDs; copied evidence context is not a premise.
    """
    axes = {name: [] for name in ("question", "wording", "answer", "support", "origin", "context")}
    root = {"result": result}
    for row in project(operation, result)["findings"]:
        identity = {"path": row["path"]}
        raw = _selected(root, row["path"])
        raw = raw if isinstance(raw, dict) else {}
        decision = row["kind"] == "session_decision"
        question = {"scope": row["scope"]}
        values = cast(dict, _copy(row["values"]))
        wording = {}
        if decision:
            question["alternatives"] = [
                _fields(option, ("id", "query")) for option in raw.get("alternatives", ())
            ]
            wording = {
                "question": raw.get("question"),
                "alternatives": [_fields(option, ("id", "label")) for option in raw.get("alternatives", ())],
            }
            values.pop("question", None)
            values["alternatives"] = [
                _fields(option, ("id", "code")) for option in raw.get("alternatives", ())
            ]
        axes["question"].append({**identity, **question})
        axes["wording"].append({**identity, **wording})
        axes["answer"].append(
            {
                **identity,
                "outcome": row["outcome"],
                "values": values,
                "conditions": [_fields(c, ("relation", "body", "scope")) for c in row["conditions"]],
            }
        )
        axes["support"].append(
            {
                **identity,
                "standing": row["standing"],
                "completion": row["completion"],
                "disposition": row["disposition"],
                "support": _support_payload(row["support"]),
                "premise_versions": _resolved_support(
                    _ancestors(root, row["path"]),
                    _proof_ids(row["support"])
                    | _proof_ids(row["conditions"])
                    | {p["id"] for p in row["values"].get("permissions", ()) if "id" in p},
                ),
                "blockers": row["blockers"],
                "conditions": [
                    _support_payload(_fields(c, ("status", "warrant"))) for c in row["conditions"]
                ],
            }
        )
        axes["origin"].append({**identity, "origins": row["origins"]})
        axes["context"].append({**identity, "evidence": _copy(raw.get("evidence", [])) if decision else []})
    return axes
