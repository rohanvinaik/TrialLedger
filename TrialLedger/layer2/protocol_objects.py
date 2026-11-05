"""Typed v2 protocol objects, checks and sections: admission and a detached canonical index (C2, C3, C4, C10).

This module validates shape, references and origin rules only. It runs no solver, evaluates no claim and
combines no standing: an object's own status, its support and its coverage are the coordinator's later work.
It never infers scope, meaning or a relation from an id, label or heading. Every refusal is a translation
question (`ValueError("protocol_<code>")`), never a clinical finding.
"""

from __future__ import annotations

import copy
import heapq
import json
from collections.abc import Mapping
from typing import Any, cast

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail, protocol_numbers, source_evidence

SCHEMA_VERSION = 1
MAX_OBJECTS = 256
MAX_CHECKS = 128
MAX_TEXT = 256
MAX_BASIS = 32

ENVELOPE = {"schema_version", "objects", "checks", "sections"}
OBJECT_FIELDS = {"id", "kind", "scope", "version", "origin", "standing", "support", "depends_on", "data"}
CHECK_FIELDS = {"id", "kind", "scope", "objects", "bindings", "claims", "required", "support"}
SECTION_FIELDS = {"id", "state", "objects", "basis"}
KINDS = (
    "measurement",
    "endpoint",
    "estimand",
    "assessment",
    "collection",
    "efficacy",
    "policy",
    "external_method",
)
CHECK_KINDS = (
    "temporal",
    "schedule",
    "dependencies",
    "estimand",
    "definition",
    "decision_table",
    "finite_policy",
    "binomial_design",
    "external_method",
)
SECTIONS = (
    "population",
    "eligibility",
    "interventions",
    "endpoints",
    "assessments",
    "efficacy",
    "safety",
    "exploratory",
)
ORIGIN_KINDS = ("user_choice", "hypothesis", "source_interpretation")
STATUSES = ("known", "interpolated", "proposed")
RESOLUTIONS = ("resolved", "partially_resolved", "unresolved", "conflicting")
MODES = ("observed", "imputed", "derived")
ROLES = ("fixed_n", "iid_binary", "alignment")
METHODS = ("binomial_design", "external_method")

# Literal key lists copied from the operators; a coordinator test compares them with their owners.
R_DEP = ("scope", "version", "rules", "adopted", "available", "unavailable", "conditions")
R_EST = (
    "scope",
    "version",
    "id",
    "definitions",
    "events",
    "requirements",
    "collection_plan",
    "data_state",
    "dependencies",
)
R_POL = (
    "scope",
    "version",
    "variables",
    "constraints",
    "states",
    "initial",
    "terminal",
    "actions",
    "transitions",
    "prohibitions",
    "invariants",
)
BINOMIAL_FIELDS = {"model", "direction", "n", "critical_count", "p0", "p1"}

PATTERN_ROLES = (
    "assessment",
    "collection",
    "endpoint",
    "dependent_endpoint",
    "estimand",
    "policy",
    "binomial",
    "external_efficacy",
    "external_method",
)


def identity_state(value: object) -> str:
    """Classify an object, check or section identity by its own text only (pure — pinned).

    pre: True
    post: __return__ in ("ok", "invalid_id")
    post: __return__ != "ok" or (type(value) is str and 0 < len(value) <= 256)
    """
    if type(value) is str and 0 < len(value) <= MAX_TEXT:
        return "ok"
    return "invalid_id"


def ceiling_state(count: int, limit: int) -> str:
    """Classify a declared list length against its ceiling; on the ceiling is inside it (pure — pinned).

    pre: count >= 0 and limit > 0
    post: __return__ in ("ok", "over_limit")
    post: (__return__ == "ok") == (count <= limit)
    """
    return "ok" if count <= limit else "over_limit"


def binding_state(has_object: bool, has_premise: bool) -> str:
    """Classify a policy binding target: exactly one of an object id or a premise id (pure — pinned).

    pre: True
    post: __return__ in ("ok", "invalid_binding")
    post: (__return__ == "ok") == (has_object != has_premise)
    """
    return "ok" if has_object != has_premise else "invalid_binding"


def section_state(state: str, basis_size: int) -> str:
    """Classify a section's state against its basis: not_applicable needs a nonempty basis (pure — pinned).

    pre: basis_size >= 0
    post: __return__ in ("ok", "invalid_state", "not_applicable_basis")
    post: __return__ != "ok" or state in ("requested", "not_applicable")
    post: __return__ != "ok" or state == "requested" or basis_size > 0
    """
    if state not in ("requested", "not_applicable"):
        return "invalid_state"
    if state == "not_applicable" and basis_size == 0:
        return "not_applicable_basis"
    return "ok"


def check_pattern_state(kind: str, counts: Mapping[str, int], total: int, linked: bool) -> str:
    """Classify a check's declared objects against its kind's exact count pattern.

    `counts` holds the per-role tallies named in PATTERN_ROLES; `total` is every declared object; `linked`
    says the declared relation (collection to assessment, efficacy to endpoint or method) holds.

    pre: total >= 0
    post: __return__ in ("ok", "check_objects")
    post: kind not in ("temporal", "definition", "decision_table") or __return__ == "ok"
    """
    count = {role: counts.get(role, 0) for role in PATTERN_ROLES}
    if kind == "schedule":
        fits = count["assessment"] == 1 and count["collection"] == 1 and total == 2 and linked
    elif kind == "dependencies":
        fits = count["endpoint"] == 1 and count["dependent_endpoint"] == 1 and total == 1
    elif kind == "estimand":
        fits = count["estimand"] == 1 and total == 1
    elif kind == "finite_policy":
        fits = count["policy"] == 1 and total == 1
    elif kind == "binomial_design":
        fits = count["binomial"] == 1 and count["endpoint"] == 1 and total == 2 and linked
    elif kind == "external_method":
        pair = count["external_efficacy"] == 1 and count["external_method"] == 1 and total == 2 and linked
        alone = count["external_method"] == 1 and total == 1
        fits = pair or alone
    else:
        fits = True
    return "ok" if fits else "check_objects"


def _fail(code: str) -> ValueError:
    return ValueError("protocol_" + code)


def _object(raw: object, fields: set[str] | tuple[str, ...], code: str) -> dict:
    if type(raw) is not dict or set(raw) != set(fields):
        raise _fail(code)
    return cast(dict, raw)


def _text(raw: object, code: str) -> str:
    if type(raw) is not str or not raw:
        raise _fail(code)
    return raw


def _rows(raw: object, code: str = "not_list") -> list:
    if type(raw) is not list:
        raise _fail(code)
    return raw


def _unique_ids(raw: object, known: Mapping[str, Any], unknown: str, duplicate: str) -> list[str]:
    """A list of unique existing ids, in input order; a non-string cannot name anything."""
    result: list[str] = []
    for item in _rows(raw):
        if type(item) is not str or item not in known:
            raise _fail(unknown)
        if item in result:
            raise _fail(duplicate)
        result.append(item)
    return result


class _Frame:
    """Whole-graph facts the per-object passes read."""

    def __init__(self, target: dict, premises: Mapping[str, dict], sources: Mapping[str, dict]):
        self.target = _canonical(target)
        self.premises = premises
        self.sources = sources
        self.kinds: dict[str, str] = {}
        self.objects: dict[str, dict] = {}
        self.requirements: dict[str, set[str]] = {}
        self.deferred: list[tuple[str, str]] = []
        self.stale: dict[str, list[str]] = {}


def _canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        return "<not canonical json>"


def _scope(raw: object, frame: _Frame) -> None:
    scope = _object(raw, {"target", "context"}, "scope_fields")
    if _canonical(scope["target"]) != frame.target:
        raise _fail("scope_target")
    context = scope["context"]
    if type(context) is not dict or set(context) != {"cohort", "phase", "arm"}:
        raise _fail("scope_context")
    for value in context.values():
        if value is not None and (type(value) is not str or not value):
            raise _fail("scope_context")


def _standing_fields(raw: dict, code: str) -> None:
    if raw["status"] not in STATUSES or raw["resolution"] not in RESOLUTIONS:
        raise _fail(code)
    basis = raw["basis"]
    if type(basis) is not list or not 1 <= len(basis) <= MAX_BASIS:
        raise _fail(code)
    if any(type(item) is not str or not item for item in basis) or len(set(basis)) != len(basis):
        raise _fail(code)


def _standing(raw: object) -> None:
    _standing_fields(_object(raw, {"status", "resolution", "basis"}, "invalid_standing"), "invalid_standing")


def _standing_ref(raw: object) -> None:
    row = _object(raw, {"ref", "version", "status", "resolution", "basis"}, "invalid_reference")
    _text(row["ref"], "invalid_reference")
    _text(row["version"], "invalid_reference")
    _standing_fields(row, "invalid_reference")


def _origin(raw: object, frame: _Frame) -> None:
    origin = _object(raw, {"kind", "ref", "source", "analysis"}, "origin_fields")
    if origin["kind"] not in ORIGIN_KINDS:
        raise _fail("origin_kind")
    _text(origin["ref"], "origin_ref")
    if origin["analysis"] is not None:
        raise _fail("origin_analysis")
    if origin["kind"] != "source_interpretation":
        if origin["source"] is not None:
            raise _fail("origin_source")
        return
    source = origin["source"]
    if type(source) is not str or source not in frame.sources:
        raise _fail("unknown_source")
    held = frame.sources[source]
    prefix = held["snapshot"]["study_ref"] + "#"
    if not origin["ref"].startswith(prefix):
        raise _fail("origin_digest")
    try:
        source_evidence._selected(held["study"], origin["ref"][len(prefix) :])
    except Exception as error:
        raise _fail("origin_pointer") from error


def adoption_state(premise: Mapping[str, Any], object_id: str, version: str) -> str:
    """Whether a support premise is an adoption record naming this exact object version (pure).

    post: __return__ in ("adopts", "stale_version", "not_adoption", "other_object")
    """
    if premise.get("kind") != "adoption":
        return "not_adoption"
    objects = [o for o in (premise.get("payload") or {}).get("objects") or [] if isinstance(o, dict)]
    if any(o.get("id") == object_id and o.get("version") == version for o in objects):
        return "adopts"
    if any(o.get("id") == object_id for o in objects):
        return "stale_version"
    return "other_object"


# An adopted definition edition: everything but its attribution (origin, standing, adoption support) and the
# version label itself. Kind, scope, dependencies and data are governed content (Rohan, 2026-11-04).
EDITION_EXCLUDED = ("origin", "standing", "support", "version")


def edition_change_state(content_equal: bool, version_equal: bool) -> str:
    """Classify one object's revision by its governed content and version label (pure — pinned).

    post: __return__ in ("unchanged_edition", "new_edition", "content_changed_without_new_version")
    post: __return__ != "content_changed_without_new_version" or (version_equal and not content_equal)
    """
    if version_equal and not content_equal:
        return "content_changed_without_new_version"
    return "unchanged_edition" if version_equal else "new_edition"


def edition_conflicts(before: list, after: list) -> list[str]:
    """Object ids whose governed content changed while their version label stayed the same.

    Adoption records name an exact object id and version, so content changed under an old version would
    silently carry an adoption to content nobody adopted. Compared by id across two raw protocol object lists.
    """
    old = {o["id"]: o for o in before if isinstance(o, dict) and isinstance(o.get("id"), str)}
    out = []
    for item in after:
        if not isinstance(item, dict) or item.get("id") not in old:
            continue
        prior = old[item["id"]]
        content = [{k: v for k, v in o.items() if k not in EDITION_EXCLUDED} for o in (prior, item)]
        state = edition_change_state(
            _canonical(content[0]) == _canonical(content[1]), prior.get("version") == item.get("version")
        )
        if state == "content_changed_without_new_version":
            out.append(item["id"])
    return out


def origin_standing_state(origin_kind: str, status: str) -> str:
    """A hypothesis-origin object may only be proposed (pure — pinned).

    post: __return__ in ("ok", "hypothesis_cannot_supply_fact")
    post: __return__ == "ok" or (origin_kind == "hypothesis" and status != "proposed")
    """
    if origin_kind == "hypothesis" and status != "proposed":
        return "hypothesis_cannot_supply_fact"
    return "ok"


def _envelope(raw: object, frame: _Frame) -> dict:
    """The object's own envelope, without anything that needs the rest of the graph."""
    item = _object(raw, OBJECT_FIELDS, "object_fields")
    if identity_state(item["id"]) != "ok":
        raise _fail("invalid_id")
    if item["id"] in frame.objects:
        raise _fail("duplicate_object")
    if item["kind"] not in KINDS:
        raise _fail("unknown_kind")
    _scope(item["scope"], frame)
    if identity_state(item["version"]) != "ok":
        raise _fail("invalid_version")
    _origin(item["origin"], frame)
    _standing(item["standing"])
    if origin_standing_state(item["origin"]["kind"], item["standing"]["status"]) != "ok":
        # Mirrors the premise path (session_projections.effective): a hypothesis never supplies a fact.
        # Explicit hypothetical frames for unchosen alternatives are a separate path (C8).
        raise _fail("hypothesis_cannot_supply_fact")
    _unique_ids(item["support"], frame.premises, "unknown_premise", "duplicate_support")
    for premise_id in item["support"]:
        # Only an explicit adoption record naming this exact object version adopts it (Rohan, 2026-11-04).
        # A wrong premise (a criterion, another object's adoption) is a translation mistake and refuses; an
        # adoption of an older version of this object is stale: the object is treated as not yet adopted.
        state = adoption_state(frame.premises[premise_id], item["id"], item["version"])
        if state in ("not_adoption", "other_object"):
            raise _fail("adoption_mismatch")
        if state == "stale_version":
            frame.stale.setdefault(item["id"], []).append(premise_id)
    _rows(item["depends_on"])
    return item


def _reference(raw: object, kind: str, frame: _Frame, owner: str) -> str:
    """An existing object id of exactly this kind."""
    if type(raw) is not str or not raw:
        raise _fail("data_fields:" + owner)
    if raw not in frame.kinds:
        raise _fail("unknown_object")
    if frame.kinds[raw] != kind:
        raise _fail("reference_kind")
    return raw


def _nullable_reference(raw: object, kind: str, frame: _Frame, owner: str) -> list[str]:
    return [] if raw is None else [_reference(raw, kind, frame, owner)]


def _mode(raw: object, owner: str) -> None:
    if raw not in MODES:
        raise _fail("data_fields:" + owner)


def _measurement(data: dict, frame: _Frame) -> list[str]:
    _standing_ref(data["definition"])
    if data["unit"] is not None:
        _text(data["unit"], "data_fields:measurement")
    _mode(data["mode"], "measurement")
    return _nullable_reference(data["baseline"], "measurement", frame, "measurement")


def _endpoint(data: dict, frame: _Frame) -> list[str]:
    refs = [_reference(data["variable"], "measurement", frame, "endpoint")]
    _standing_ref(data["definition"])
    refs += _nullable_reference(data["estimand"], "estimand", frame, "endpoint")
    if data["dependencies"] is not None:
        _object(data["dependencies"], R_DEP, "data_fields:endpoint")
    return refs


def _estimand_requirements(data: dict) -> set[str]:
    identities: list[str] = []
    for row in _rows(data["requirements"], "data_fields:estimand"):
        if type(row) is not dict or "id" not in row:
            raise _fail("data_fields:estimand")
        identities.append(_text(row["id"], "data_fields:estimand"))
    if len(set(identities)) != len(identities):
        raise _fail("data_fields:estimand")
    return set(identities)


def _typed_proposition(raw: object) -> None:
    try:
        held = a.from_canonical(json.dumps(raw, allow_nan=False))
        if not isinstance(held, a.PROPOSITIONS):
            raise _fail("invalid_proposition")
        _, blockers = entail.proposition_formula(held)
    except Exception as error:
        raise _fail("invalid_proposition") from error
    if blockers:
        raise _fail("invalid_proposition")


def _assessment(data: dict, frame: _Frame) -> list[str]:
    refs = [_reference(data["measurement"], "measurement", frame, "assessment")]
    _text(data["anchor"], "data_fields:assessment")
    _text(data["unit"], "data_fields:assessment")
    if data["nominal"] is not None:
        protocol_numbers.rational(data["nominal"], "protocol")
    protocol_numbers.union(data["permitted"], "protocol")
    if data["condition"] is not None:
        _typed_proposition(data["condition"])
    return refs


def _collection(data: dict, frame: _Frame) -> list[str]:
    refs = [_reference(data["assessment"], "assessment", frame, "collection")]
    _mode(data["mode"], "collection")
    protocol_numbers.union(data["availability"], "protocol")
    handling = data["event_handling"]
    if handling is not None:
        # Declared once, on the collection (Rohan, 2026-11-04): the estimand check takes this requirement's
        # collection action from here; the action is never inferred from availability intervals.
        row = _object(handling, {"estimand", "requirement", "action"}, "data_fields:collection")
        refs.append(_reference(row["estimand"], "estimand", frame, "collection"))
        _text(row["requirement"], "data_fields:collection")
        if row["action"] not in ("collect", "stop"):
            raise _fail("data_fields:collection")
        frame.deferred.append((row["estimand"], row["requirement"]))
    return refs


def _strict_int(value: object) -> bool:
    return type(value) is int


def _efficacy(data: dict, frame: _Frame) -> list[str]:
    refs = [_reference(data["endpoint"], "endpoint", frame, "efficacy")]
    if data["method"] not in METHODS:
        raise _fail("data_fields:efficacy")
    parameters = data["parameters"]
    if data["method"] == "binomial_design":
        row = _object(parameters, BINOMIAL_FIELDS, "data_fields:efficacy")
        texts = (row["model"], row["direction"], row["p0"], row["p1"])
        if any(type(item) is not str or not item for item in texts):
            raise _fail("data_fields:efficacy")
        if not (_strict_int(row["n"]) and _strict_int(row["critical_count"])):
            raise _fail("data_fields:efficacy")
    else:
        refs.append(_reference(parameters, "external_method", frame, "efficacy"))
    seen: list[tuple[str, str]] = []
    for item in _rows(data["assumptions"], "data_fields:efficacy"):
        row = _object(item, {"role", "premise"}, "data_fields:efficacy")
        if row["role"] not in ROLES:
            raise _fail("data_fields:efficacy")
        if type(row["premise"]) is not str or row["premise"] not in frame.premises:
            raise _fail("unknown_premise")
        pair = (row["role"], row["premise"])
        if pair in seen:
            raise _fail("duplicate_support")
        seen.append(pair)
    return refs


def _policy(data: dict, frame: _Frame) -> list[str]:
    model = _object(data["model"], R_POL, "data_fields:policy")
    variables: set[str] = set()
    for row in _rows(model["variables"], "data_fields:policy"):
        if type(row) is not dict or "id" not in row:
            raise _fail("data_fields:policy")
        variables.add(_text(row["id"], "data_fields:policy"))
    refs: list[str] = []
    seen: list[dict] = []
    for item in _rows(data["bindings"], "data_fields:policy"):
        row = _object(item, {"variable", "object", "premise"}, "data_fields:policy")
        _text(row["variable"], "data_fields:policy")
        if row["variable"] not in variables:
            raise _fail("unknown_policy_variable")
        if binding_state(row["object"] is not None, row["premise"] is not None) != "ok":
            raise _fail("invalid_binding")
        if row["object"] is not None:
            if type(row["object"]) is not str or row["object"] not in frame.kinds:
                raise _fail("unknown_object")
            refs.append(row["object"])
        elif type(row["premise"]) is not str or row["premise"] not in frame.premises:
            raise _fail("unknown_premise")
        if row in seen:
            raise _fail("invalid_binding")
        seen.append(row)
    return refs


def _external_method(data: dict, frame: _Frame) -> list[str]:
    _standing_ref(data["definition"])
    refs: list[str] = []
    names: list[str] = []
    for item in _rows(data["inputs"], "data_fields:external_method"):
        row = _object(item, {"name", "value", "unit", "ref"}, "data_fields:external_method")
        names.append(_text(row["name"], "data_fields:external_method"))
        for key in ("value", "unit"):
            if row[key] is not None and type(row[key]) is not str:
                raise _fail("data_fields:external_method")
        ref = row["ref"]
        if ref is None:
            continue
        if type(ref) is not str:
            raise _fail("unknown_object")
        if ref in frame.kinds:
            refs.append(ref)
        elif ref not in frame.premises:
            raise _fail("unknown_object")
    if len(set(names)) != len(names):
        raise _fail("data_fields:external_method")
    missing = [
        _text(name, "data_fields:external_method")
        for name in _rows(data["missing"], "data_fields:external_method")
    ]
    if len(set(missing)) != len(missing) or set(missing) & set(names):
        raise _fail("external_missing")
    return refs


DATA_FIELDS = {
    "measurement": ("definition", "unit", "mode", "baseline"),
    "endpoint": ("variable", "definition", "estimand", "dependencies"),
    "estimand": R_EST,
    "assessment": ("measurement", "anchor", "unit", "nominal", "permitted", "condition"),
    "collection": ("assessment", "mode", "availability", "event_handling"),
    "efficacy": ("endpoint", "method", "parameters", "assumptions"),
    "policy": ("model", "bindings"),
    "external_method": ("definition", "inputs", "missing"),
}


def _data(identity: str, kind: str, data: object, frame: _Frame) -> list[str]:
    """Validate one closed payload and return the object ids it names, in encounter order."""
    row = _object(data, DATA_FIELDS[kind], "data_fields:" + kind)
    if kind == "estimand":
        frame.requirements[identity] = _estimand_requirements(row)
        return []
    handlers = {
        "measurement": _measurement,
        "endpoint": _endpoint,
        "assessment": _assessment,
        "efficacy": _efficacy,
        "policy": _policy,
        "external_method": _external_method,
    }
    if kind == "collection":
        return _collection(row, frame)
    return handlers[kind](row, frame)


def _order(graph: dict[str, list[str]], position: dict[str, int]) -> list[str]:
    """Dependencies first, ties in input order; anything left over lies on a cycle."""
    waiting = {key: len(set(parents)) for key, parents in graph.items()}
    children: dict[str, list[str]] = {key: [] for key in graph}
    for key, parents in graph.items():
        for parent in set(parents):
            children[parent].append(key)
    ready = [(position[key], key) for key, count in waiting.items() if count == 0]
    heapq.heapify(ready)
    result: list[str] = []
    while ready:
        _, key = heapq.heappop(ready)
        result.append(key)
        for child in children[key]:
            waiting[child] -= 1
            if waiting[child] == 0:
                heapq.heappush(ready, (position[child], child))
    if len(result) != len(graph):
        raise _fail("dependency_cycle")
    return result


def _check(raw: object, frame: _Frame, premises: Mapping[str, dict]) -> dict:
    item = _object(raw, CHECK_FIELDS, "check_fields")
    if identity_state(item["id"]) != "ok":
        raise _fail("invalid_id")
    if item["kind"] not in CHECK_KINDS:
        raise _fail("unknown_check_kind")
    _scope(item["scope"], frame)
    members = _unique_ids(item["objects"], frame.kinds, "unknown_object", "duplicate_dependency")
    for binding in _rows(item["bindings"]):
        if type(binding) is not dict:
            raise _fail("check_fields")
        _text(binding.get("projection"), "check_fields")
    _rows(item["claims"])
    if type(item["required"]) is not bool:
        raise _fail("invalid_required")
    _unique_ids(item["support"], premises, "unknown_premise", "duplicate_support")
    _pattern(item["kind"], members, frame)
    return item


def _pattern(kind: str, members: list[str], frame: _Frame) -> None:
    counts = dict.fromkeys(PATTERN_ROLES, 0)
    held = [frame.objects[identity] for identity in members]
    for obj in held:
        data = obj["data"]
        role = obj["kind"]
        if role == "endpoint" and data["dependencies"] is not None:
            counts["dependent_endpoint"] += 1
        if role == "efficacy":
            role = "binomial" if data["method"] == "binomial_design" else "external_efficacy"
        if role in counts:
            counts[role] += 1
    linked = _linked(kind, members, held)
    if check_pattern_state(kind, counts, len(held), linked) != "ok":
        raise _fail("check_objects:" + kind)


def _linked(kind: str, members: list[str], held: list[dict]) -> bool:
    by_kind: dict[str, list[dict]] = {}
    for obj in held:
        by_kind.setdefault(obj["kind"], []).append(obj)
    if (
        kind == "schedule"
        and len(by_kind.get("collection", [])) == 1
        and len(by_kind.get("assessment", [])) == 1
    ):
        return by_kind["collection"][0]["data"]["assessment"] == by_kind["assessment"][0]["id"]
    efficacy = by_kind.get("efficacy", [])
    if len(efficacy) != 1:
        return False
    data = efficacy[0]["data"]
    if kind == "binomial_design":
        endpoints = by_kind.get("endpoint", [])
        return len(endpoints) == 1 and data["endpoint"] == endpoints[0]["id"]
    if kind == "external_method":
        methods = by_kind.get("external_method", [])
        return len(methods) == 1 and data["parameters"] == methods[0]["id"]
    return False


def _section(raw: object, frame: _Frame, seen: dict) -> dict:
    item = _object(raw, SECTION_FIELDS, "section_fields")
    if item["id"] not in SECTIONS:
        raise _fail("unknown_section")
    if item["id"] in seen:
        raise _fail("duplicate_section")
    _unique_ids(item["objects"], frame.kinds, "unknown_object", "duplicate_dependency")
    basis = _rows(item["basis"], "section_fields")
    if any(type(entry) is not str or not entry for entry in basis) or len(set(basis)) != len(basis):
        raise _fail("section_fields")
    state = section_state(item["state"] if type(item["state"]) is str else "", len(basis))
    if state == "invalid_state":
        raise _fail("section_fields")
    if state == "not_applicable_basis":
        raise _fail("not_applicable_basis")
    return item


def validate_protocol(
    protocol: object,
    *,
    target: dict,
    premises: Mapping[str, dict],
    sources: Mapping[str, dict],
) -> dict:
    """Validate a v2 `session.protocol` and return a detached canonical index (never a clinical finding).

    Raises `ValueError("protocol_<code>")` for malformed or dangling declarations. The input is deep-copied
    and never mutated; the index shares nothing with it. No standing is combined and no claim is evaluated.
    """
    try:
        held = copy.deepcopy(protocol)
    except RecursionError as error:
        raise _fail("fields") from error
    if type(held) is not dict or set(held) != ENVELOPE:
        raise _fail("fields")
    held = cast(dict, held)
    if type(held["schema_version"]) is not int or held["schema_version"] != SCHEMA_VERSION:
        raise _fail("version")
    raw_objects, raw_checks, raw_sections = (_rows(held[key]) for key in ("objects", "checks", "sections"))
    if ceiling_state(len(raw_objects), MAX_OBJECTS) != "ok":
        raise _fail("object_limit")
    if ceiling_state(len(raw_checks), MAX_CHECKS) != "ok":
        raise _fail("check_limit")
    frame = _Frame(target, premises, sources)
    for raw in raw_objects:
        item = _envelope(raw, frame)
        frame.kinds[item["id"]] = item["kind"]
        frame.objects[item["id"]] = item
    position = {identity: index for index, identity in enumerate(frame.objects)}
    data_refs: dict[str, list[str]] = {}
    for identity, item in frame.objects.items():
        _unique_ids(item["depends_on"], frame.kinds, "unknown_object", "duplicate_dependency")
        refs = _data(identity, item["kind"], item["data"], frame)
        data_refs[identity] = list(dict.fromkeys(refs))
    for estimand, requirement in frame.deferred:
        if requirement not in frame.requirements[estimand]:
            raise _fail("unknown_requirement")
    graph = {
        identity: list(dict.fromkeys([*item["depends_on"], *data_refs[identity]]))
        for identity, item in frame.objects.items()
    }
    order = _order(graph, position)
    for identity, item in frame.objects.items():
        if not set(data_refs[identity]) <= set(item["depends_on"]):
            raise _fail("unlisted_reference")
    checks: dict[str, dict] = {}
    for raw in raw_checks:
        item = _check(raw, frame, premises)
        if item["id"] in checks:
            raise _fail("duplicate_check")
        checks[item["id"]] = item
    seen: dict[str, dict] = {}
    for raw in raw_sections:
        item = _section(raw, frame, seen)
        seen[item["id"]] = item
    sections = {
        name: (
            {"state": seen[name]["state"], "objects": seen[name]["objects"], "basis": seen[name]["basis"]}
            if name in seen
            else {"state": "not_requested", "objects": [], "basis": []}
        )
        for name in SECTIONS
    }
    dependents: dict[str, list[str]] = {identity: [] for identity in frame.objects}
    for identity, item in frame.objects.items():
        for parent in item["depends_on"]:
            dependents[parent].append(identity)
    references = {
        identity: {
            "objects": sorted(data_refs[identity]),
            "premises": list(item["support"]),
            "sources": [] if item["origin"]["source"] is None else [item["origin"]["source"]],
        }
        for identity, item in frame.objects.items()
    }
    index = {
        "schema_version": SCHEMA_VERSION,
        "objects": frame.objects,
        "kinds": frame.kinds,
        "order": order,
        "dependents": dependents,
        "references": references,
        "checks": checks,
        "check_order": list(checks),
        "stale_adoptions": {key: list(value) for key, value in frame.stale.items()},
        "sections": sections,
    }
    return copy.deepcopy(index)
