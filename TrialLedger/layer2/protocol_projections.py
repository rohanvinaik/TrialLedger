"""Named projections from validated protocol checks into existing public child requests (packet E).

A projector builds requests and receipts. It evaluates no operator, reads no prose or premise payload,
matches no label, and never widens, intersects or aligns a scope. Standing is carried as declared: an
object with no adoption support never becomes a known constraint. Unit behaviour only; nothing here is a
clinical finding.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping

MAX_SCOPE = 1024
STANDING_FIELDS = {"status", "resolution", "basis"}

UNPROJECTED = "definition_not_projected:0"

PROJECTIONS: dict[str, str] = {
    "schedule": "schedule_window_coverage:1",
    "finite_policy": "finite_policy_model:1",
    "binomial_design": "binomial_efficacy:1",
    "estimand": "estimand_declaration:1",
    "dependencies": "endpoint_dependencies:1",
    "temporal": "temporal_request:1",
    "decision_table": "decision_table_request:1",
    "external_method": "external_method_declaration:1",
}


def _fail(code: str) -> ValueError:
    return ValueError("projection_" + code)


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def scope_length_state(length: int) -> str:
    """Classify a canonical scope string length.

    pre: length >= 0
    post: __return__ in ("scope_ok", "scope_too_long")
    """
    return "scope_too_long" if length > MAX_SCOPE else "scope_ok"


def scope_equality_state(check_scope: str, object_scope: str) -> str:
    """Compare two canonical scope strings exactly; no widening or alignment.

    pre: isinstance(check_scope, str) and isinstance(object_scope, str)
    post: __return__ in ("scope_equal", "scope_mismatch")
    """
    return "scope_equal" if check_scope == object_scope else "scope_mismatch"


def adoption_state(support_count: int) -> str:
    """Classify whether an object declares adoption support.

    pre: support_count >= 0
    post: __return__ in ("adoption_declared", "adoption_absent")
    """
    return "adoption_declared" if support_count > 0 else "adoption_absent"


def binding_shape_state(bindings: list, name: str) -> str:
    """Classify a check's bindings against the single named binding shape.

    pre: isinstance(bindings, list) and isinstance(name, str)
    post: __return__ in ("binding_ok", "binding_shape")
    """
    if len(bindings) != 1 or not isinstance(bindings[0], dict):
        return "binding_shape"
    row = bindings[0]
    if set(row) != {"projection", "data"} or row["projection"] != name:
        return "binding_shape"
    return "binding_ok" if isinstance(row["data"], dict) else "binding_shape"


def _standing_of(premise_standing: Mapping[str, dict], premise: str) -> dict:
    row = premise_standing.get(premise) if isinstance(premise_standing, Mapping) else None
    if row is None:
        raise _fail("missing_premise_standing")
    if not isinstance(row, Mapping) or set(row) != STANDING_FIELDS:
        raise _fail("invalid_standing")
    return copy.deepcopy(dict(row))


def stale_adoption_id(obj_id: str, premise: str) -> str:
    """The support identity of one object's stale application of an adoption record."""
    return f"stale_adoption:{obj_id}:{premise}"


def _premise_entry(premise: str, premise_standing: Mapping[str, dict]) -> dict:
    return {"id": "premise:" + premise, **_standing_of(premise_standing, premise)}


def object_entries(obj: dict, premise_standing: Mapping[str, dict], stale: list | tuple = ()) -> list[dict]:
    """Support entries for one object: its own standing, each support premise, or the adoption gap."""
    standing = obj["standing"]
    entries = [
        {
            "id": "object:" + obj["id"],
            "status": standing["status"],
            "resolution": standing["resolution"],
            "basis": list(standing["basis"]),
        }
    ]
    for premise in obj["support"]:
        entry = _premise_entry(premise, premise_standing)
        if premise in stale:
            # A stale adoption (older version of this object) never admits the current version. Its
            # application is object-specific: one record may be current for another object, so the
            # stale application keeps its own identity and can never be merged into the current one.
            entry.update(
                id=stale_adoption_id(obj["id"], premise),
                resolution="unresolved",
                basis=[f"adoption_stale_version: re-adopt {obj['id']} at version {obj['version']}"],
            )
        entries.append(entry)
    if adoption_state(len(obj["support"])) == "adoption_absent":
        entries.append(
            {
                "id": "adoption:" + obj["id"],
                "status": standing["status"],
                "resolution": "unresolved",
                "basis": ["no adoption support declared for " + obj["id"]],
            }
        )
    return entries


def _unique(entries: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for entry in entries:
        if entry["id"] not in seen:
            seen.add(entry["id"])
            out.append(entry)
    return out


def _obj_entries(index: dict, ids: list[str], premise_standing: Mapping[str, dict]) -> list[dict]:
    rows: list[dict] = []
    for identity in ids:
        stale = index.get("stale_adoptions", {}).get(identity, [])
        rows += object_entries(index["objects"][identity], premise_standing, stale)
    return _unique(rows)


def _of_kind(index: dict, check: dict, kind: str) -> list[str]:
    return [i for i in check["objects"] if index["kinds"][i] == kind]


def _unresolved(code: str, objects: list[str], premises: list[str] | None = None) -> dict:
    return {"code": "projection_" + code, "objects": list(objects), "premises": list(premises or [])}


APPLICABILITY = "condition_applicability"


def reference_closure(index: dict, roots: list[str]) -> list[str]:
    """The roots, then every object they reference transitively, in first-reached order (pure, finite)."""
    seen: list[str] = []
    pending = list(roots)
    while pending:
        identity = pending.pop(0)
        if identity in seen or identity not in index.get("objects", {}):
            continue
        seen.append(identity)
        pending.extend(index.get("references", {}).get(identity, {}).get("objects", []))
    return seen


class _Build:
    """Accumulates one check's consumed objects and role support."""

    def __init__(self, index: dict, check: dict, premise_standing: Mapping[str, dict]):
        self.index = index
        self.check = check
        self.standing = premise_standing
        self.objects = list(check["objects"])
        self.roles: dict[str, list[dict]] = {}
        self.extra: list[dict] = []

    def gating(self, ids: list[str]) -> list[str]:
        """Objects whose standing, adoption and conditions gate a finding over `ids` (Rohan, 2026-11-05).

        An object listed on the check gates by itself. An object a projection reached through a link (for
        example the collection an estimand consumes) gates together with everything it references
        transitively (that collection's assessment and measurement). Objects merely named inside a listed
        object's data (a measurement baseline, the estimand a collection names) do not gate that check.
        """
        out: list[str] = []
        for identity in ids:
            out += (
                [identity] if identity in self.check["objects"] else reference_closure(self.index, [identity])
            )
        return list(dict.fromkeys(out))

    def consume(self, identity: str) -> None:
        if identity not in self.objects:
            self.objects.append(identity)

    def role(self, name: str, ids: list[str], premises: list[str] | None = None) -> None:
        rows = _obj_entries(self.index, self.gating(ids), self.standing)
        rows += [_premise_entry(p, self.standing) for p in premises or []]
        # Check-wide support is explicit in every role. It is never inferred from absence: a premise that
        # also backs one object must still reach every claim when the check declares it (external review).
        rows += [_premise_entry(p, self.standing) for p in self.check["support"]]
        self.roles[name] = _unique(rows)

    def support(self) -> list[dict]:
        rows = _obj_entries(self.index, self.gating(self.objects), self.standing)
        for entries in self.roles.values():
            rows += entries
        rows += [_premise_entry(p, self.standing) for p in self.check["support"]]
        return _unique(rows)

    def scope_issue(self, scope: str) -> dict | None:
        # The same gating closure as standing, adoption and conditions (Rohan, 2026-11-05).
        wrong = [
            i
            for i in self.gating(self.objects)
            if scope_equality_state(scope, canonical(self.index["objects"][i]["scope"])) == "scope_mismatch"
        ]
        return _unresolved("scope_mismatch", wrong) if wrong else None

    def conditions(self) -> list[dict]:
        """Every assessment condition in the reference closure of what this check consumes.

        A condition travels along references, not only with objects listed on the check: an estimand that
        consumes a linked collection is bound by that collection's conditional assessment (composition
        audit, 2026-11-05). The closure follows `references[id].objects` (object ids named inside data).
        """
        out = []
        for identity in self.gating(self.objects):
            obj = self.index["objects"][identity]
            if obj["kind"] == "assessment" and obj["data"]["condition"] is not None:
                out.append({"object": identity, "condition": copy.deepcopy(obj["data"]["condition"])})
        return out

    def receipt(self, name: str, version: str, request: dict, support: list[dict]) -> dict:
        stale = {
            stale_adoption_id(identity, premise): premise
            for identity in self.objects
            for premise in self.index.get("stale_adoptions", {}).get(identity, [])
        }
        # Provenance keeps the original premise id for both current and stale applications.
        premises = list(
            dict.fromkeys(
                e["id"][len("premise:") :] if e["id"].startswith("premise:") else stale[e["id"]]
                for e in support
                if e["id"].startswith("premise:") or e["id"] in stale
            )
        )
        return {
            "projection": name,
            "version": version,
            "check": self.check["id"],
            "objects": list(self.objects),
            # Every object whose standing, adoption and conditions gate this check.
            "closure": self.gating(self.objects),
            "premises": premises,
            "target": copy.deepcopy(self.check["scope"]["target"]),
            "scope": copy.deepcopy(self.check["scope"]),
            "bindings": copy.deepcopy(self.check["bindings"]),
            "role_support": copy.deepcopy(self.roles),
            "conditions": self.conditions(),
            "request_digest": hashlib.sha256(canonical(request).encode("utf-8")).hexdigest(),
        }

    def child(self, name: str, version: str, kind: str, data: dict, claims: object = None) -> dict:
        identity = self.check["id"] + ":" + name
        support = self.support()
        signal: dict = {"id": identity, "kind": kind, "data": data, "support": support}
        if claims is not None:
            signal["claims"] = copy.deepcopy(claims)
            signal["role_support"] = {role: [e["id"] for e in rows] for role, rows in self.roles.items()}
        request = {"operation": "signals", "signals": [signal]}
        return {"id": identity, "request": request, "receipt": self.receipt(name, version, request, support)}


def _result(check: dict, name: str, version: str, children=None, unresolved=None, not_computed=None) -> dict:
    return {
        "check": check["id"],
        "kind": check["kind"],
        "projection": name + ":" + version,
        "children": children or [],
        "unresolved": unresolved or [],
        "not_computed": not_computed,
    }


def _scope_string(build: _Build, needs_text: bool) -> tuple[str, dict | None]:
    scope = canonical(build.check["scope"])
    issue = build.scope_issue(scope)
    if issue is None and needs_text and scope_length_state(len(scope)) == "scope_too_long":
        issue = _unresolved("scope_too_long", build.objects)
    return scope, issue


def _project_schedule(build: _Build, name: str, version: str) -> dict:
    index, check = build.index, build.check
    (a_id,), (c_id,) = _of_kind(index, check, "assessment"), _of_kind(index, check, "collection")
    scope, issue = _scope_string(build, True)
    if issue:
        return _result(check, name, version, unresolved=[issue])
    a, c = index["objects"][a_id]["data"], index["objects"][c_id]["data"]
    build.role("permitted", [a_id])
    build.role("nominal", [a_id])
    build.role("available", [c_id])
    data = {
        "scope": scope,
        "anchor": a["anchor"],
        "unit": a["unit"],
        "nominal": copy.deepcopy(a["nominal"]),
        "permitted": copy.deepcopy(a["permitted"]),
        "available": copy.deepcopy(c["availability"]),
    }
    return _result(
        check, name, version, [build.child(name, version, "schedule_coverage", data, check["claims"])]
    )


def _project_policy(build: _Build, name: str, version: str) -> dict:
    index, check = build.index, build.check
    (p_id,) = _of_kind(index, check, "policy")
    policy = index["objects"][p_id]["data"]
    bound = [b["object"] for b in policy["bindings"] if b["object"] is not None]
    premises = [b["premise"] for b in policy["bindings"] if b["premise"] is not None]
    for identity in bound:
        build.consume(identity)
    _, issue = _scope_string(build, False)
    if issue:
        return _result(check, name, version, unresolved=[issue])
    build.role("model", [p_id, *bound], premises)
    data = copy.deepcopy(policy["model"])
    return _result(check, name, version, [build.child(name, version, "finite_policy", data, check["claims"])])


def _project_binomial(build: _Build, name: str, version: str) -> dict:
    index, check = build.index, build.check
    (e_id,), (ep_id,) = _of_kind(index, check, "efficacy"), _of_kind(index, check, "endpoint")
    scope, issue = _scope_string(build, True)
    if issue:
        return _result(check, name, version, unresolved=[issue])
    eff = index["objects"][e_id]
    premises = [row["premise"] for row in eff["data"]["assumptions"]]
    build.role("parameters", [e_id, ep_id])
    build.role("assumptions", [], premises)
    assumptions = [
        {
            "role": row["role"],
            "ref": "premise:" + row["premise"],
            "version": eff["version"],
            **_standing_of(build.standing, row["premise"]),
        }
        for row in eff["data"]["assumptions"]
    ]
    data = {"scope": scope, **copy.deepcopy(eff["data"]["parameters"]), "assumptions": assumptions}
    return _result(
        check, name, version, [build.child(name, version, "binomial_design", data, check["claims"])]
    )


def _project_estimand(build: _Build, name: str, version: str) -> dict:
    (est_id,) = _of_kind(build.index, build.check, "estimand")
    data = copy.deepcopy(build.index["objects"][est_id]["data"])
    # Collections that declare event_handling for this estimand supply its collection plan (declared once,
    # on the collection). A differing declaration is a named conflict, never a silent override.
    linked = [
        (oid, obj)
        for oid, obj in build.index["objects"].items()
        if obj["kind"] == "collection"
        and isinstance(obj["data"].get("event_handling"), dict)
        and obj["data"]["event_handling"]["estimand"] == est_id
    ]
    declared_in_data = {
        row["requirement"]: row["action"]
        for row in data.get("collection_plan", [])
        if isinstance(row, dict) and "requirement" in row
    }
    plan = {row["requirement"]: row for row in data.get("collection_plan", []) if isinstance(row, dict)}
    declared: dict[str, tuple[str, str]] = {}
    conflicts = []
    for oid, obj in linked:
        handling = obj["data"]["event_handling"]
        requirement, action = handling["requirement"], handling["action"]
        other_collection = declared.get(requirement)
        in_data = declared_in_data.get(requirement)
        if (other_collection and other_collection[1] != action) or (
            in_data is not None and in_data != action
        ):
            conflicts.append(oid)
            continue
        declared[requirement] = (oid, action)
        build.consume(oid)
        standing = obj["standing"]
        plan[requirement] = {
            "requirement": requirement,
            "action": action,
            "status": standing["status"],
            "resolution": standing["resolution"],
            "basis": list(standing["basis"]),
        }
    if conflicts:
        return _result(
            build.check,
            name,
            version,
            unresolved=[_unresolved("collection_plan_conflict", [est_id, *conflicts])],
        )
    if linked:
        data["collection_plan"] = [plan[key] for key in sorted(plan)]
    _, issue = _scope_string(build, False)
    if issue:
        return _result(build.check, name, version, unresolved=[issue])
    build.role("estimand", [est_id, *(oid for oid, _ in linked)])
    return _result(build.check, name, version, [build.child(name, version, "estimand", data)])


def _project_dependencies(build: _Build, name: str, version: str) -> dict:
    (ep_id,) = _of_kind(build.index, build.check, "endpoint")
    endpoint = build.index["objects"][ep_id]["data"]
    variable = endpoint["variable"]
    build.consume(variable)
    _, issue = _scope_string(build, False)
    if issue:
        return _result(build.check, name, version, unresolved=[issue])
    build.role("dependencies", [ep_id, variable])
    data = copy.deepcopy(endpoint["dependencies"])
    return _result(build.check, name, version, [build.child(name, version, "dependencies", data)])


def _project_binding(kind: str):
    def project(build: _Build, name: str, version: str) -> dict:
        check = build.check
        # The applicability binding is validated separately by the managed session (task 2.9); only the
        # operation binding counts here, so the two can coexist (external review).
        operation = [b for b in check["bindings"] if b.get("projection") != APPLICABILITY]
        if binding_shape_state(operation, name) != "binding_ok":
            return _result(check, name, version, unresolved=[_unresolved("binding_shape", check["objects"])])
        _, issue = _scope_string(build, False)
        if issue:
            return _result(check, name, version, unresolved=[issue])
        build.role("data", list(check["objects"]))
        data = copy.deepcopy(operation[0]["data"])
        return _result(check, name, version, [build.child(name, version, kind, data)])

    return project


def _project_external(build: _Build, name: str, version: str) -> dict:
    method = _of_kind(build.index, build.check, "external_method")
    if len(method) != 1:
        return _result(
            build.check, name, version, unresolved=[_unresolved("binding_shape", build.check["objects"])]
        )
    data = build.index["objects"][method[0]]["data"]
    note = {
        "method": method[0],
        "definition": copy.deepcopy(data["definition"]),
        "missing": list(data["missing"]),
        "inputs": copy.deepcopy(data["inputs"]),
    }
    return _result(build.check, name, version, not_computed=note)


def _project_definition(build: _Build, name: str, version: str) -> dict:
    return _result(build.check, name, version, unresolved=[_unresolved("slice_5", build.check["objects"])])


_PROJECTORS = {
    "schedule": _project_schedule,
    "finite_policy": _project_policy,
    "binomial_design": _project_binomial,
    "estimand": _project_estimand,
    "dependencies": _project_dependencies,
    "temporal": _project_binding("temporal"),
    "decision_table": _project_binding("decision_table"),
    "external_method": _project_external,
    "definition": _project_definition,
}


def project(index: dict, check_id: str, *, premise_standing: Mapping[str, dict]) -> dict:
    """Project one validated check into public child requests; never mutates its inputs."""
    if type(check_id) is not str or check_id not in index.get("checks", {}):
        raise _fail("unknown_check")
    check = index["checks"][check_id]
    projector = _PROJECTORS.get(check["kind"])
    if projector is None:
        raise _fail("unknown_kind")
    name, version = PROJECTIONS.get(check["kind"], UNPROJECTED).split(":")
    projected = projector(_Build(index, check, premise_standing), name, version)
    stale = index.get("stale_adoptions", {})
    consumed = [*check["objects"], *(o for c in projected["children"] for o in c["receipt"]["objects"])]
    for identity in dict.fromkeys(consumed):
        if stale.get(identity):
            projected["unresolved"].append(
                {"code": "adoption_stale_version", "objects": [identity], "premises": list(stale[identity])}
            )
    return projected
