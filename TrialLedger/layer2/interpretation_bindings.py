"""Source-bound population/definition applications inside isolated interpretation frames.

This module checks declared identities and scopes. It neither reads a source nor certifies
the caller's clinical reading. Unusable applications remain unresolved, not false designs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from TrialLedger.layer2 import assertions
from TrialLedger.layer2 import signals as evidence

MAX_ITEMS = 256
SCOPE_FIELDS = frozenset({"study", "population", "arm", "time", "version"})
BINDING_FIELDS = frozenset(
    {"id", "kind", "relation", "subjects", "scope", "sources", "status", "resolution", "basis"}
)
RELATIONS = {"population": ("subset_of", "same_universe", "partition_of"), "definition": ("adopts",)}


@dataclass(frozen=True)
class Binding:
    id: str
    kind: str
    relation: str
    subjects: tuple[str, ...]
    scope: dict[str, str]
    sources: tuple[dict, ...]
    status: str
    resolution: str
    basis: tuple[str, ...]


@dataclass(frozen=True)
class BindingUse:
    binding: str
    signal: str
    scope: dict[str, str]


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}:nonempty_text_required")
    return value


def _rows(value: object, where: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{where}:list_required")
    if len(value) > MAX_ITEMS:
        raise ValueError(f"{where}:resource_bound")
    return value


def _object(value: object, required: frozenset[str], optional: frozenset[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{where}:object_required")
    if set(value) - required - optional:
        raise ValueError(f"{where}:unknown_fields")
    if required - set(value):
        raise ValueError(f"{where}:missing_fields")
    return value


def _texts(value: object, where: str) -> tuple[str, ...]:
    rows = tuple(_text(item, where) for item in _rows(value, where))
    if not rows:
        raise ValueError(f"{where}:nonempty_list_required")
    return rows


def _scope(value: object, where: str) -> dict[str, str]:
    row = _object(value, SCOPE_FIELDS, frozenset(), where)
    return {key: _text(row[key], f"{where}.{key}") for key in sorted(SCOPE_FIELDS)}


def _sources(value: object) -> tuple[dict, ...]:
    out = []
    for raw in _rows(value, "binding.sources"):
        row = _object(raw, frozenset({"ref", "version", "address"}), frozenset({"digest"}), "binding.source")
        source = {key: _text(item, f"binding.source.{key}") for key, item in row.items()}
        if source in out:
            raise ValueError("binding.sources:duplicate_source")
        out.append(source)
    if not out:
        raise ValueError("binding.sources:nonempty_list_required")
    return tuple(out)


def parse_bindings(raw: object, study_ref: str) -> tuple[Binding, ...]:
    """Read strict binding declarations, retaining mismatched scopes for an unresolved use result."""
    _text(study_ref, "study_ref")
    out = []
    ids = set()
    for value in _rows(raw, "bindings"):
        row = _object(value, BINDING_FIELDS, frozenset(), "binding")
        identity = _text(row["id"], "binding.id")
        if identity in ids:
            raise ValueError("bindings:duplicate_binding_id")
        ids.add(identity)
        kind = _text(row["kind"], "binding.kind")
        relation = _text(row["relation"], "binding.relation")
        if kind not in RELATIONS or relation not in RELATIONS[kind]:
            raise ValueError("binding:unsupported_kind_or_relation")
        subjects = _texts(row["subjects"], "binding.subjects")
        if (relation == "subset_of" and len(subjects) != 2) or (relation == "adopts" and len(subjects) != 1):
            raise ValueError("binding:invalid_subject_arity")
        if relation == "same_universe" and len(subjects) < 2:
            raise ValueError("binding:invalid_subject_arity")
        if relation in ("same_universe", "partition_of") and len(set(subjects)) != len(subjects):
            raise ValueError("binding:duplicate_subject")
        status, resolution = row["status"], row["resolution"]
        if not isinstance(status, str) or status not in assertions.STATUSES:
            raise ValueError("binding:invalid_status")
        if not isinstance(resolution, str) or resolution not in assertions.RESOLUTIONS:
            raise ValueError("binding:invalid_resolution")
        out.append(
            Binding(
                identity,
                kind,
                relation,
                subjects,
                _scope(row["scope"], "binding.scope"),
                _sources(row["sources"]),
                status,
                resolution,
                _texts(row["basis"], "binding.basis"),
            )
        )
    return tuple(out)


def parse_uses(
    raw: object, bindings: tuple[Binding, ...], signal_ids: set[str], study_ref: str
) -> tuple[BindingUse, ...]:
    """A use names existing objects; disagreement in scope remains data for the use check."""
    _text(study_ref, "study_ref")
    known = {binding.id for binding in bindings}
    out = []
    pairs = set()
    for value in _rows(raw, "binding_uses"):
        row = _object(value, frozenset({"binding", "signal", "scope"}), frozenset(), "binding_use")
        binding = _text(row["binding"], "binding_use.binding")
        signal = _text(row["signal"], "binding_use.signal")
        if binding not in known:
            raise ValueError("binding_use:unknown_binding")
        if signal not in signal_ids:
            raise ValueError("binding_use:unknown_signal")
        if (binding, signal) in pairs:
            raise ValueError("binding_use:duplicate_use")
        pairs.add((binding, signal))
        out.append(BindingUse(binding, signal, _scope(row["scope"], "binding_use.scope")))
    return tuple(out)


def binding_standing(status: str, resolution: str) -> str:
    """Standing for a binding assumed only in its interpretation frame (pure — pinned).

    post: __return__ in ("supported", "conditional", "unresolved")
    post: __return__ != "supported" or (status == "known" and resolution == "resolved")
    """
    if resolution != "resolved" or status not in ("known", "interpolated", "proposed"):
        return "unresolved"
    return "supported" if status == "known" else "conditional"


def scope_compatibility(bound: dict, used: dict, study_ref: str) -> str:
    """Exact application scope, never a join by count or group title (pure — pinned)."""
    if set(bound) != SCOPE_FIELDS or set(used) != SCOPE_FIELDS:
        return "scope_incomplete"
    if bound["study"] != study_ref or used["study"] != study_ref:
        return "study_mismatch"
    if bound != used:
        return "scope_mismatch"
    return "matched"


def _member_refs(rows: object, universe: str) -> list[str] | None:
    if not isinstance(rows, list) or not rows:
        return None
    if any(not isinstance(row, dict) or row.get("universe") != universe for row in rows):
        return None
    refs = [row.get("ref") for row in rows]
    if any(not isinstance(ref, str) or not ref for ref in refs) or len(set(refs)) != len(refs):
        return None
    return refs


def population_compatibility(relation: str, subjects: list[str], universe: str, kind: str, data: dict) -> str:
    """Bind only the relation that the named population operator actually represents (pure — pinned)."""
    expected_kind = {"subset_of": "population", "same_universe": "overlap", "partition_of": "partition"}
    if expected_kind.get(relation) != kind:
        return "operator_mismatch"
    if data.get("universe") != universe:
        return "population_mismatch"
    if relation == "subset_of":
        subset = data.get("subset")
        if not isinstance(subset, dict) or subset.get("universe") != universe:
            return "population_mismatch"
        if subjects != [data.get("parent_ref"), subset.get("ref")]:
            return "subjects_mismatch"
        return "matched" if data.get("subset_relation") == "confirmed" else "subset_not_declared"
    if relation == "partition_of" and (
        data.get("disjoint") is not True or data.get("exhaustive") is not True
    ):
        return "partition_not_declared"
    refs = _member_refs(data.get("marginals" if relation == "same_universe" else "parts"), universe)
    if refs is None or len(subjects) != len(set(subjects)) or set(subjects) != set(refs):
        return "subjects_mismatch"
    return "matched"


def definition_compatibility(
    subjects: list[str], population: str, version: str, kind: str, data: dict
) -> str:
    """An adopted definition belongs to its exact rule edition and application scope (pure — pinned)."""
    if kind != "dependencies":
        return "operator_mismatch"
    if data.get("scope") != population:
        return "population_mismatch"
    adopted = data.get("adopted")
    if len(subjects) != 1 or not isinstance(adopted, list) or subjects[0] not in adopted:
        return "definition_not_adopted"
    rules = data.get("rules")
    if not isinstance(rules, list):
        return "definition_not_found"
    rows = [row for row in rules if isinstance(row, dict) and row.get("id") == subjects[0]]
    if len(rows) != 1:
        return "definition_not_found"
    return "matched" if rows[0].get("version") == version else "definition_version_mismatch"


def _use_problem(binding: Binding, use: BindingUse, signal: evidence.Signal, study_ref: str) -> str:
    scope = scope_compatibility(binding.scope, use.scope, study_ref)
    if scope != "matched":
        return scope
    if binding.kind == "population":
        return population_compatibility(
            binding.relation, list(binding.subjects), binding.scope["population"], signal.kind, signal.data
        )
    if binding.kind != "definition" or binding.relation != "adopts":
        return "operator_mismatch"
    return definition_compatibility(
        list(binding.subjects),
        binding.scope["population"],
        binding.scope["version"],
        signal.kind,
        signal.data,
    )


def check_uses(
    bindings: tuple[Binding, ...],
    uses: tuple[BindingUse, ...],
    signals: tuple[evidence.Signal, ...],
    study_ref: str,
) -> list[dict[str, Any]]:
    """Return application gates with their evidence; never modify bindings, uses or signals."""
    by_binding = {binding.id: binding for binding in bindings}
    by_signal = {signal.id: signal for signal in signals}
    if len(by_binding) != len(bindings) or len(by_signal) != len(signals):
        raise ValueError("binding_use:duplicate_target_identity")
    rows = []
    for use in uses:
        if use.binding not in by_binding or use.signal not in by_signal:
            raise ValueError("binding_use:unknown_target")
        binding = by_binding[use.binding]
        standing = binding_standing(binding.status, binding.resolution)
        problem = _use_problem(binding, use, by_signal[use.signal], study_ref)
        blockers = []
        if standing == "unresolved":
            blockers.append("binding_unresolved:" + binding.id)
        if problem != "matched":
            blockers.append(problem + ":" + binding.id)
        rows.append(
            {
                "binding": binding.id,
                "signal": use.signal,
                "code": "unresolved" if blockers else standing,
                "status": binding.status,
                "basis": [
                    *binding.basis,
                    *(f"{s['ref']}@{s['version']}#{s['address']}" for s in binding.sources),
                ],
                "blockers": blockers,
                "rule": "interpretation.binding-use:1",
            }
        )
    return rows
