"""Legacy Assignment shape backed by source-bound indication scope, never disease categories.

`assign` is pure: lookups are supplied by the run integrator. Internal pack keys retain their schema-3
spelling for coherence compatibility; `universes` is always empty and grants nothing. Historical lexical
category and purpose/drug-gating helpers have been retired.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from TrialLedger import contract
from TrialLedger.indications import LookupResult, MeshIdentity, resolve_indication

RULE = "universes.assign"
NSCLC = "D002289"
NSCLC_PACKS = (
    "oncology.solid/setting_and_line",
    "oncology.solid/gene_selection",
    "oncology.solid/nsclc_relations",
)


@dataclass(frozen=True)
class Assignment:
    """Compatibility shape: scope code and permitted packs, not a category assignment.

    The first eleven fields retain their positional order for existing consumers. `universes` is empty;
    `primary_purpose` is literal metadata, `target` is unused, and pack permission comes only from
    source-bound declared indication scope. Mixed indications never make a cohort assertion a
    trial-wide requirement.
    """

    case: str
    code: str
    universes: tuple[str, ...]
    decided_by: str
    primary_purpose: str
    sources: tuple[dict[str, Any], ...]
    packs: tuple[str, ...]
    words: str
    conditions: tuple[str, ...] = ()
    target: dict[str, str] | None = None
    applicability: tuple[dict[str, Any], ...] = ()
    indications: tuple[dict[str, Any], ...] = ()
    relationships: tuple[dict[str, str], ...] = ()
    source_scope: str = "indication"


def pack_scope(packs: tuple[str, ...]) -> tuple[dict[str, list[str]], tuple[str, ...]]:
    """The coherence coordinates the named packs compute, each with the packs that own it, and the relation
    ids they own, in contract.UNIVERSES order."""
    coordinates: dict[str, list[str]] = {}
    relations: dict[str, None] = {}
    for universe in contract.UNIVERSES:
        for pack in universe.packs:
            name = f"{universe.name}/{pack.name}"
            if name not in packs:
                continue
            for coordinate in pack.coordinates:
                coordinates.setdefault(coordinate, []).append(name)
            for relation in pack.relations:
                relations.setdefault(relation, None)
    return coordinates, tuple(relations)


def _module(study: dict[str, Any], path: str) -> dict[str, Any]:
    node: Any = study
    for key in path.split("."):
        node = node.get(key) if isinstance(node, dict) else None
    return node if isinstance(node, dict) else {}


def _source_identities(texts: list[str], lookups: dict[str, LookupResult]) -> tuple[MeshIdentity, ...]:
    """Only resolved, supplied identities; no lexical, ATC, ancestor or title-fragment guess."""
    return tuple(
        identity
        for text in texts
        for identity in lookups.get(text, LookupResult("not_looked_up")).identities
        if lookups.get(text, LookupResult("not_looked_up")).code == "resolved"
    )


def assign(
    study: dict[str, Any],
    drug_classes: dict[str, tuple[str, ...] | None] | None = None,
    *,
    lookups: dict[str, LookupResult] | None = None,
) -> Assignment:
    """Compatibility entry point; `drug_classes` is accepted but never interpreted.

    Whole literal title identities may serve as own disease assertions when their source lookup resolves;
    eligibility assertions are not read here. An unresolved lookup, including relay/no lookup, never assigns
    a default category. Derived MeSH terms remain secondary, even if they name an otherwise applicable pack.
    """
    held = lookups or {}
    protocol = _module(study, "protocolSection")
    condition_data = _module(protocol, "conditionsModule")
    raw_conditions = condition_data.get("conditions", [])
    malformed_conditions = not isinstance(raw_conditions, list) or any(
        not isinstance(text, str) for text in raw_conditions
    )
    conditions = (
        [text for text in raw_conditions if isinstance(text, str)] if isinstance(raw_conditions, list) else []
    )
    titles_module = _module(protocol, "identificationModule")
    titles = [
        titles_module[key]
        for key in ("briefTitle", "officialTitle")
        if isinstance(titles_module.get(key), str) and titles_module[key]
    ]
    browse = _module(study, "derivedSection.conditionBrowseModule")
    meshes = browse.get("meshes")
    mesh_terms = [
        entry["term"]
        for entry in (meshes if isinstance(meshes, list) else [])
        if isinstance(entry, dict) and isinstance(entry.get("term"), str)
    ]
    scope = resolve_indication(
        conditions, held, (NSCLC,), _source_identities(mesh_terms, held), _source_identities(titles, held)
    )
    code = "scope_unresolved" if malformed_conditions else scope["code"]
    labels = {
        "applicable": (
            "NSCLC rule packs apply to the established indication; "
            "criterion cohort and temporal scope remain separate"
        ),
        "inapplicable": "NSCLC rule packs do not apply to the established indication",
        "scope_unresolved": (
            "NSCLC rule applicability unresolved: "
            "the supplied sources do not establish the declared indication scope"
        ),
    }
    applicability = tuple(
        {
            "pack": pack,
            "status": code,
            "words": labels[code],
            "indications": [row["descriptor"] for row in scope["indications"]],
            "scope": "indication; not a trial-wide cohort assertion",
        }
        for pack in NSCLC_PACKS
    )
    used_names = list(dict.fromkeys([*conditions, *titles, *mesh_terms]))
    used_names += [
        name
        for name, answer in held.items()
        if name not in used_names and any(identity.descriptor == NSCLC for identity in answer.identities)
    ]
    sources = tuple(scope["sources"]) + (
        {
            "source": "mesh_lookups",
            "lookups": [{"text": name, **asdict(held[name])} for name in used_names if name in held],
        },
        {
            "source": "registry_conditions",
            "conditions": raw_conditions,
            "code": "malformed" if malformed_conditions else "read",
            "keywords": condition_data.get("keywords", []),
        },
        {
            "source": "registry_mesh",
            "meshes": browse.get("meshes", []),
            "ancestors": browse.get("ancestors", []),
            "browse_leaves": browse.get("browseLeaves", []),
        },
        {
            "source": "titles",
            "text": titles,
            "code": (
                "read_whole_names_only"
                if titles and all(title in held for title in titles)
                else "partly_looked_up"
                if any(title in held for title in titles)
                else "not_looked_up"
            ),
            "identities": [asdict(identity) for identity in _source_identities(titles, held)],
        },
        {"source": "eligibility_disease_assertions", "code": "not_yet_read"},
    )
    return Assignment(
        "unresolved" if code == "scope_unresolved" else "resolved",
        code,
        (),
        scope["decided_by"],
        str(_module(protocol, "designModule.designInfo").get("primaryPurpose") or ""),
        sources,
        NSCLC_PACKS if code == "applicable" else (),
        labels[code],
        tuple(conditions),
        None,
        applicability,
        tuple(scope["indications"]),
        tuple(scope["relationships"]),
    )


def reading(assignment: Assignment) -> dict[str, Any]:
    """Schema-3 legacy field with empty categories and explicit indication evidence/applicability."""
    return {
        "status": "unresolved" if assignment.code == "scope_unresolved" else "known",
        "rule": RULE,
        "words": list(assignment.conditions),
        "result": {
            "legacy": True,
            "universes": [],
            "decided_by": assignment.decided_by,
            "indications": [dict(row) for row in assignment.indications],
            "sources": [dict(row) for row in assignment.sources],
            "relationships": [dict(row) for row in assignment.relationships],
            "applicability": [dict(row) for row in assignment.applicability],
            "scope": assignment.source_scope,
        },
        "note": assignment.words,
    }
