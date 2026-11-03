"""Stage-local population checks; explicit progression never invents membership.

A documented_subset edge declares that every member of its target population belongs to its source
population. Counts test that relation's compatibility; passing the test does not establish the relation.
A permitted edge describes a possible pathway and supplies no subset or individual-membership warrant.
Graph resolution concerns the shared study/snapshot identity and gates every edge; edge resolution concerns
only its declared relation. gate_ref identifies a supplied transition condition; this operator retains that
reference but does not evaluate a clinical predicate or assert that any individual passed it.
"""

from __future__ import annotations

from copy import deepcopy

from TrialLedger.layer2 import numeric_evidence

MAX_STAGES = 32
MAX_TRANSITIONS = 128
MAX_CLAIMS = 256
STATUSES = ("known", "interpolated", "proposed")
RESOLUTIONS = ("resolved", "partially_resolved", "unresolved", "conflicting")
SCOPE_FIELDS = {
    "study",
    "snapshot",
    "source_population",
    "target_population",
    "source_arm",
    "target_arm",
    "source_time",
    "target_time",
    "unit",
}
INPUTS = {
    "stages": {
        "required": ("study", "snapshot", "resolution", "stages", "transitions"),
        "fields": {
            "study": "nonempty study identity",
            "snapshot": "nonempty supplied source snapshot identity; not protocol-edition proof",
            "resolution": "shared study/snapshot binding; unresolved gates every edge",
            "stages": "distinct {id,population,arm,time,unit,total}; total integer/null, unit exact",
            "transitions": (
                "{id,source,target,relation,scope,status,resolution,basis,gate_ref}; relation permitted "
                "or documented_subset. Scope names exact graph and endpoint identities. Each edge "
                "keeps independent support; no title/count matching or automatic membership."
            ),
        },
        "claims": "{transition,count,lower,upper}; count is source id, target id or outside",
        "limits": {"stages": MAX_STAGES, "transitions": MAX_TRANSITIONS, "claims": MAX_CLAIMS},
    }
}


def transition_gate(
    relation: str, status: str, resolution: str, scope_matches: bool, unit_matches: bool
) -> str:
    """Name the use of a validated stage relation without promoting its meaning (pure — pinned).

    pre: relation in ("permitted", "documented_subset")
    pre: status in ("known", "interpolated", "proposed")
    pre: resolution in ("resolved", "partially_resolved", "unresolved", "conflicting")
    post: (__return__ == "stage_scope_mismatch") == (not scope_matches)
    post: (__return__ == "stage_unit_mismatch") == (scope_matches and not unit_matches)
    post: (__return__ == "proposed_refused") == (scope_matches and unit_matches and status == "proposed")
    post: __return__ != "stage_binding_unresolved" or resolution != "resolved"
    post: __return__ not in ("permitted_only", "checkable") or resolution == "resolved"
    post: __return__ not in ("permitted_only", "checkable") or status != "proposed"
    post: __return__ not in ("permitted_only", "checkable") or (scope_matches and unit_matches)
    post: __return__ != "permitted_only" or relation == "permitted"
    post: __return__ != "checkable" or relation == "documented_subset"
    post: isinstance(__return__, str)
    """
    if not scope_matches:
        return "stage_scope_mismatch"
    if not unit_matches:
        return "stage_unit_mismatch"
    if status == "proposed":
        return "proposed_refused"
    if resolution != "resolved":
        return "stage_binding_unresolved"
    if relation == "permitted":
        return "permitted_only"
    return "checkable"


def stage_result_code(codes: list[str]) -> str:
    """An independent established conflict remains visible beside unresolved checks (pure — pinned).

    pre: all(code in ("conflict", "unresolved", "bounded", "permitted_only") for code in codes)
    post: (__return__ == "conflict") == ("conflict" in codes)
    post: (__return__ == "unresolved") == ("conflict" not in codes and "unresolved" in codes)
    post: (__return__ == "consistent") == ("conflict" not in codes and "unresolved" not in codes)
    """
    if "conflict" in codes:
        return "conflict"
    if "unresolved" in codes:
        return "unresolved"
    return "consistent"


def stage_support_status(code: str, statuses: list[str]) -> str:
    """Choose deciding edge support, preserving independent stronger conflict (pure — pinned).

    pre: code in ("consistent", "conflict", "unresolved")
    pre: all(status in ("known", "interpolated") for status in statuses)
    post: (__return__ == "no_support") == (code == "unresolved" or not statuses)
    post: __return__ not in ("known", "interpolated") or (statuses and code != "unresolved")
    post: __return__ != "known" or "known" in statuses
    post: __return__ != "interpolated" or "interpolated" in statuses
    """
    if code == "unresolved" or not statuses:
        return "no_support"
    if code == "conflict":
        return "known" if "known" in statuses else "interpolated"
    return "interpolated" if "interpolated" in statuses else "known"


def _object(value: object, fields: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError("stage_not_object:" + where)
    if set(value) != fields:
        raise ValueError("stage_fields_do_not_fit:" + where)
    return value


def _text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("stage_identity_required:" + where)
    return value


def _rows(value: object, limit: int, where: str) -> list:
    if not isinstance(value, list):
        raise ValueError("stage_list_required:" + where)
    if len(value) > limit:
        raise ValueError("resource_bound:stage_" + where)
    return value


def _count(value: object, where: str) -> None:
    if value is not None and (type(value) is not int or value < 0):
        raise ValueError("stage_count_required:" + where)
    if isinstance(value, int) and value.bit_length() > 2048:
        raise ValueError("resource_bound:stage_count")


def _stages(raw: object) -> dict[str, dict]:
    result = {}
    for value in _rows(raw, MAX_STAGES, "stages"):
        row = _object(value, {"id", "population", "arm", "time", "unit", "total"}, "stage")
        for field in ("id", "population", "arm", "time", "unit"):
            _text(row[field], "stage:" + field)
        _count(row["total"], "stage:total")
        if row["id"] == "outside" or row["id"] in result:
            raise ValueError("stage_duplicate_or_reserved_id")
        result[row["id"]] = row
    return result


def _transitions(raw: object, stages: dict[str, dict]) -> dict[str, dict]:
    result = {}
    fields = {"id", "source", "target", "relation", "scope", "status", "resolution", "basis", "gate_ref"}
    for value in _rows(raw, MAX_TRANSITIONS, "transitions"):
        row = _object(value, fields, "transition")
        for field in ("id", "source", "target", "gate_ref"):
            _text(row[field], "transition:" + field)
        if row["id"] in result:
            raise ValueError("stage_duplicate_transition")
        if row["source"] not in stages or row["target"] not in stages:
            raise ValueError("stage_unknown_endpoint")
        if row["source"] == row["target"]:
            raise ValueError("stage_self_transition")
        if row["relation"] not in ("permitted", "documented_subset"):
            raise ValueError("stage_unsupported_relation")
        if row["status"] not in STATUSES or row["resolution"] not in RESOLUTIONS:
            raise ValueError("stage_invalid_standing")
        basis = [_text(item, "basis") for item in _rows(row["basis"], MAX_CLAIMS, "basis")]
        if not basis or len(set(basis)) != len(basis):
            raise ValueError("stage_basis_empty_or_duplicate")
        scope = _object(row["scope"], SCOPE_FIELDS, "scope")
        for field in SCOPE_FIELDS:
            _text(scope[field], "scope:" + field)
        result[row["id"]] = row
    return result


def _claims(raw: object, transitions: dict[str, dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {identity: [] for identity in transitions}
    for value in _rows(raw, MAX_CLAIMS, "claims"):
        row = _object(value, {"transition", "count", "lower", "upper"}, "claim")
        identity = _text(row["transition"], "claim:transition")
        if identity not in transitions:
            raise ValueError("stage_unknown_transition_claim")
        edge = transitions[identity]
        if row["count"] not in (edge["source"], edge["target"], "outside"):
            raise ValueError("stage_unknown_count_claim")
        _count(row["lower"], "claim:lower")
        _count(row["upper"], "claim:upper")
        result[identity].append({key: row[key] for key in ("count", "lower", "upper")})
    return result


def _scope(data: dict, source: dict, target: dict) -> dict:
    return {
        "study": data["study"],
        "snapshot": data["snapshot"],
        "source_population": source["population"],
        "target_population": target["population"],
        "source_arm": source["arm"],
        "target_arm": target["arm"],
        "source_time": source["time"],
        "target_time": target["time"],
        "unit": source["unit"],
    }


def _edge(data: dict, edge: dict, stages: dict[str, dict], claims: list[dict]) -> dict:
    source, target = stages[edge["source"]], stages[edge["target"]]
    scope_matches = edge["scope"] == _scope(data, source, target)
    unit_matches = source["unit"] == target["unit"]
    resolution = edge["resolution"] if data["resolution"] == "resolved" else data["resolution"]
    gate = transition_gate(edge["relation"], edge["status"], resolution, scope_matches, unit_matches)
    request = calculation = None
    blockers = [] if gate in ("checkable", "permitted_only") else [gate + ":" + edge["id"]]
    if edge["relation"] == "documented_subset" and scope_matches and unit_matches:
        if source["total"] is None or target["total"] is None:
            blockers.append("stage_total_unknown:" + edge["id"])
        else:
            universe = "stage-parent:" + data["study"] + ":" + data["snapshot"] + ":" + source["id"]
            request = {
                "universe": universe,
                "alignment": "confirmed",
                "total": source["total"],
                "parent_ref": source["id"],
                "subset_relation": "confirmed",
                "subset": {
                    "ref": target["id"],
                    "universe": universe,
                    "lower": target["total"],
                    "upper": target["total"],
                },
            }
            calculation = numeric_evidence.check("population", request, claims)
    if edge["relation"] == "permitted" and claims:
        blockers.append("stage_subset_not_warranted:" + edge["id"])
    code = "unresolved"
    if not blockers and gate == "permitted_only":
        code = "permitted_only"
    elif not blockers and calculation is not None:
        code = calculation["code"]
    if calculation is not None and gate == "checkable" and not blockers:
        blockers.extend(calculation["blockers"])
    return {
        "id": edge["id"],
        "source": source["id"],
        "target": target["id"],
        "code": code,
        "status": edge["status"],
        "basis": list(edge["basis"]),
        "declaration": deepcopy(edge),
        "source_stage": deepcopy(source),
        "target_stage": deepcopy(target),
        "claims": deepcopy(claims),
        "population_request": request,
        "population_result": calculation,
        "blockers": blockers,
        "rule": "stages.explicit_subset:1",
        "guarantee": "count_compatibility_conditional_on_supplied_relation_not_individual_membership",
    }


def check(kind: str, data: dict, claims: list[dict]) -> dict:
    """Prepare independent existing population checks; never infer progression from matching counts."""
    if kind != "stages":
        raise ValueError("unsupported_stage_kind")
    data = _object(data, set(INPUTS["stages"]["required"]), "data")
    _text(data["study"], "study")
    _text(data["snapshot"], "snapshot")
    if data["resolution"] not in RESOLUTIONS:
        raise ValueError("stage_invalid_resolution")
    stages = _stages(data["stages"])
    transitions = _transitions(data["transitions"], stages)
    grouped = _claims(claims, transitions)
    rows = [_edge(data, transitions[key], stages, grouped[key]) for key in sorted(transitions)]
    active = [row for row in rows if not claims or grouped[row["id"]] or row["code"] == "conflict"]
    code = stage_result_code([row["code"] for row in active])
    deciding = [row for row in active if row["code"] == "conflict"] if code == "conflict" else active
    admitted = [row for row in deciding if row["code"] in ("conflict", "bounded", "permitted_only")]
    support = stage_support_status(code, [row["status"] for row in admitted])
    if code == "conflict":
        admitted = [row for row in admitted if row["status"] == support]
    return {
        "code": code,
        "support_status": None if support == "no_support" else support,
        "determining_ids": [row["id"] for row in admitted],
        "value": {
            "study": data["study"],
            "snapshot": data["snapshot"],
            "stages": [deepcopy(stages[key]) for key in sorted(stages)],
            "transitions": rows,
            "witnesses": [],
        },
        "blockers": sorted({blocker for row in active for blocker in row["blockers"]}),
        "rule": "stages.explicit_subset:1",
    }


def evaluate(kind: str, data: dict) -> dict:
    """Compute stage-edge checks with no candidate count restrictions."""
    return check(kind, data, [])


EXAMPLES = {
    "stages": {
        "study": "invented:runin-study",
        "snapshot": "invented:snapshot-v1",
        "resolution": "resolved",
        "stages": [
            {
                "id": "induction",
                "population": "induction-started",
                "arm": "all",
                "time": "entry",
                "unit": "person",
                "total": 498,
            },
            {
                "id": "maintenance",
                "population": "randomized-maintenance",
                "arm": "all",
                "time": "week16",
                "unit": "person",
                "total": 440,
            },
        ],
        "transitions": [
            {
                "id": "randomized-after-runin",
                "source": "induction",
                "target": "maintenance",
                "relation": "documented_subset",
                "scope": {
                    "study": "invented:runin-study",
                    "snapshot": "invented:snapshot-v1",
                    "source_population": "induction-started",
                    "target_population": "randomized-maintenance",
                    "source_arm": "all",
                    "target_arm": "all",
                    "source_time": "entry",
                    "target_time": "week16",
                    "unit": "person",
                },
                "status": "interpolated",
                "resolution": "resolved",
                "basis": ["invented:declared-person-lineage-not-registry-evidence"],
                "gate_ref": "invented:week16-response-gate-retained-not-evaluated",
            },
        ],
    }
}
