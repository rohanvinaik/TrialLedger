"""A test-only stand-in for unit B's interface (universes.assign, universes.reading, coherence.resolve under
an assignment), until unit B lands on main: the record's tests pass `shim_domains` as landscape_record's
`domains`. It is no rule of TrialLedger's and nothing in production reads it.

It mimics B's shapes only: a study whose condition MeSH terms or ancestors hold Lymphoma or Leukemia is
haematologic, one holding Neoplasms solid; one with any other condition MeSH term general; one with none
unresolved. Its coordinates are coherence.resolve's, cut to the packs contract.UNIVERSES gives the universe
for a treatment trial, each row naming its packs.
"""

from __future__ import annotations

from typing import Any

from TrialLedger import coherence, contract, landscape

HEME = ("Lymphoma", "Leukemia")


def shim_assign(study: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(universes, the terms that decided them)."""
    browse = study.get("derivedSection", {}).get("conditionBrowseModule", {})
    terms = [held.get("term") for key in ("meshes", "ancestors") for held in browse.get(key, []) or []]
    heme = [term for term in terms if term in HEME]
    if heme:
        return ["oncology.heme"], heme
    if "Neoplasms" in terms:
        return ["oncology.solid"], ["Neoplasms"]
    meshes = [held.get("term") for held in browse.get("meshes", []) or []]
    return (["general"], meshes) if meshes else ([], [])


def shim_domains(study: dict[str, Any], view: dict[str, Any], _answers: Any) -> tuple[dict, dict]:
    universes, words = shim_assign(study)
    purpose = study["protocolSection"].get("designModule", {}).get("designInfo", {}).get("primaryPurpose")
    status = "known" if universes else "unresolved"
    reading = {
        "status": status,
        "rule": "universes.assign",
        "words": words,
        "result": {
            "universes": universes,
            "decided_by": "condition_mesh" if universes else "",
            "sources": [],
        },
        "note": "" if universes else "Scope unresolved — no source identifies a domain",
    }
    packs: dict[str, list[str]] = {}
    for universe in contract.UNIVERSES:
        if universe.name not in universes:
            continue
        for pack in universe.packs:
            needs_treatment = any(r.kind == "primary_purpose" for r in pack.requires)
            if needs_treatment and purpose != "TREATMENT":
                continue
            for coordinate in pack.coordinates:
                packs.setdefault(coordinate, []).append(f"{universe.name}/{pack.name}")
    resolved = coherence.resolve(landscape.criteria_evidence(view["criteria"]))
    return reading, {name: {**row, "packs": packs[name]} for name, row in resolved.items() if name in packs}
