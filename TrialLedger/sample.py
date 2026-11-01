"""A live, stratified, declared sample of interventional trials (add-targeted-questions, Decision 9).

Strata are the registry's top-level condition categories, read from its derived condition MeSH (a label for
spread, never a fact about a trial: the derived MeSH is wrong for some records), plus the trials with no
condition MeSH at all. For each stratum the full NCT ID list is fetched live, from one snapshot; a seeded
simple random draw is taken within it from the discovery pool, never from the confirmation pool that a hash of
the NCT ID reserves; trials drawn in several strata are kept once, with every membership and their union
inclusion probability. Everything is kept: the queries, the pool sizes, the seed, the snapshot and the draw.
Each drawn trial is resolved later, one at a time.

The sample also declares its balance check: the drawn trials are counted by phase (each registry value,
combined phases kept as written), intervention type and primary purpose, read from each record when it is
resolved (the sample holds only IDs). A declared cell no drawn trial holds is checked against the registry
(its frame IDs fetched live); if the frame holds some, a seeded supplement is drawn for it and labelled, with
its own inclusion probability, never merged into the strata's. A cell the registry returns no trial for is
called empty only when its query's form has been tried live (`VERIFIED_FORMS`); otherwise it is
"query_unverified", since a search area the registry ignores would also return nothing."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable
from typing import Any

from TrialLedger.registry import enum_labels

BASE = "AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2010-01-01,2025-12-31]"
CATEGORIES = (
    "Neoplasms",
    "Cardiovascular Diseases",
    "Nervous System Diseases",
    "Infections",
    "Nutritional and Metabolic Diseases",
    "Respiratory Tract Diseases",
    "Digestive System Diseases",
    "Mental Disorders",
    "Musculoskeletal Diseases",
    "Skin and Connective Tissue Diseases",
    "Immune System Diseases",
    "Urogenital Diseases",
    "Female Urogenital Diseases and Pregnancy Complications",
    "Endocrine System Diseases",
    "Eye Diseases",
    "Hemic and Lymphatic Diseases",
    "Congenital, Hereditary, and Neonatal Diseases and Abnormalities",
)
NO_MESH = "no condition MeSH"
CONFIRMATION_SHARE = 3  # of 10: sha256(NCT ID) mod 10 below this is the confirmation pool, never drawn here


class SnapshotChanged(Exception):
    """The registry's data timestamp changed between queries that must come from one snapshot."""


def _condition(label: str) -> str:
    """One stratum's condition: no condition MeSH, or the category as a condition term or ancestor."""
    if label == NO_MESH:
        return "AREA[ConditionMeshTerm]MISSING"
    term = f'"{label}"'
    return f"(AREA[ConditionMeshTerm]{term} OR AREA[ConditionAncestorTerm]{term})"


def stratum_query(label: str) -> str:
    """The registry query of one stratum: the base filter and the category as a condition term or ancestor."""
    return f"{BASE} AND {_condition(label)}"


def reserved(nct: str) -> bool:
    """Whether an NCT ID belongs to the confirmation pool (pure — pinned): its SHA-256 mod 10 is below the
    declared share. Declared before any draw; no discovery wave draws from it."""
    return int(hashlib.sha256(nct.encode("ascii")).hexdigest(), 16) % 10 < CONFIRMATION_SHARE


def draw(ids: list[str], n: int, seed: str, label: str) -> tuple[list[str], int]:
    """A seeded simple random draw of `n` from one stratum's discovery pool (pure — pinned).

    The pool is the stratum's distinct IDs outside the confirmation pool, sorted, so the draw depends on the
    set of IDs, the seed and the label alone, never on the API's order. Returns (the drawn IDs in draw order,
    the pool size); fewer than `n` when the pool is smaller.
    """
    pool = sorted({nct for nct in ids if not reserved(nct)})
    rng = random.Random(f"{seed}:{label}")
    return rng.sample(pool, min(max(n, 0), len(pool))), len(pool)


def inclusion(memberships: list[str], sizes: dict[str, tuple[int, int]]) -> float:
    """A trial's probability of being drawn at least once (pure — pinned): 1 − Π (1 − n_h / N_h) over the
    strata it belongs to, where `sizes[h]` = (n_h drawn, N_h in the pool); a stratum with an empty pool
    contributes nothing."""
    miss = 1.0
    for label in memberships:
        drawn, pool = sizes[label]
        if pool > 0:
            miss *= 1 - min(drawn, pool) / pool
    return 1 - miss


def draw_sample(
    per_stratum: int,
    seed: str,
    query_ids: Callable[..., tuple[list[str], str, str]],
    progress: Callable[[str], None] = lambda message: None,
) -> dict[str, Any]:
    """The whole sample, fetched live: every stratum's IDs, its draw, and each drawn trial's memberships and
    union inclusion probability. Every stratum is read from the same registry snapshot, or the sample fails.
    """
    strata, members, snapshots = [], {}, set()
    pools: dict[str, set[str]] = {}
    for label in (*CATEGORIES, NO_MESH):
        query = stratum_query(label)
        ids, version, timestamp = query_ids({"filter.advanced": query}, progress=progress)
        snapshots.add((version, timestamp))
        drawn, pool = draw(ids, per_stratum, seed, label)
        pools[label] = set(ids)
        strata.append({"label": label, "query": query, "matched": len(ids), "pool": pool, "drawn": drawn})
        progress(f"{label}: {len(ids)} trials, {pool} in the discovery pool, {len(drawn)} drawn")
    if len(snapshots) != 1:
        raise SnapshotChanged(f"the registry changed while sampling: {sorted(snapshots)}")
    sizes = {s["label"]: (len(s["drawn"]), s["pool"]) for s in strata}
    for stratum in strata:
        for nct in stratum["drawn"]:
            members.setdefault(nct, [])
    for nct in members:
        members[nct] = [label for label in sizes if nct in pools[label]]
    version, timestamp = snapshots.pop()
    return {
        "seed": seed,
        "per_stratum": per_stratum,
        "confirmation_pool": f"sha256(NCT ID) mod 10 < {CONFIRMATION_SHARE}",
        "api_version": version,
        "data_timestamp": timestamp,
        "balance": balance_declaration(),
        "strata": strata,
        "trials": [
            {"nct": nct, "strata": labels, "inclusion_probability": inclusion(labels, sizes)}
            for nct, labels in members.items()
        ],
    }


# ── the balance table (Decision 9): phase, intervention type and primary purpose of the trials drawn ──────

NONE = "(none recorded)"
# Each axis: its search area (the metadata's `piece` for the field) and the enum its values come from.
AXES = {
    "phase": ("Phase", "Phase"),
    "intervention_type": ("InterventionType", "InterventionType"),
    "primary_purpose": ("DesignPrimaryPurpose", "PrimaryPurpose"),
}
# The metadata's rule for designModule.phases: "Pulldown menu in PRS can have combo of 2 phases, 1&2, or 2&3."
# A combined phase is its own cell, written as the API's CSV writes a phase list.
PHASE_COMBINATIONS = ("PHASE1|PHASE2", "PHASE2|PHASE3")
SUPPLEMENT_PER_CELL = 1
SUPPLEMENT_LABEL = "supplement {axis}={value}"
# The query forms a cell query is built from, each with the date it was tried live against the registry and
# returned trials (counts recorded in tests/live_query_forms.json). A zero-hit query whose forms are not all
# here is never read as an empty cell.
VERIFIED_FORMS = {
    "AREA[Phase]": "2026-11-01",
    "NOT AREA[Phase]": "2026-11-01",
    "AREA[InterventionType]": "2026-11-01",
    "AREA[DesignPrimaryPurpose]": "2026-11-01",
}


def declared_cells() -> dict[str, list[str]]:
    """Every registry value of each balance axis, from the vendored enums, and the two phase combinations the
    metadata's rule names: the cells a sample is checked against."""
    cells = {axis: list(enum_labels(enum)) for axis, (_piece, enum) in AXES.items()}
    cells["phase"] += list(PHASE_COMBINATIONS)
    return cells


def balance_declaration() -> dict[str, Any]:
    """The balance check and its supplement, declared in the sample before any trial is resolved."""
    return {
        "axes": {axis: piece for axis, (piece, _enum) in AXES.items()},
        "cells": declared_cells(),
        "supplement_per_cell": SUPPLEMENT_PER_CELL,
        "supplement_seed_label": SUPPLEMENT_LABEL,
        "rule": "for each declared cell no drawn trial holds, the frame's NCT IDs holding it are fetched "
        "live; if there are any, a seeded simple random draw of supplement_per_cell from their discovery "
        "pool, outside the sample, is a labelled supplement with its own inclusion probability",
    }


def trial_cells(study: dict[str, Any]) -> dict[str, list[str]]:
    """The balance cells one resolved record holds (pure — pinned).

    Phase: the record's phase list joined by "|" in its own order, so a combined phase stays as written
    ("PHASE1|PHASE2"), never split or reordered (`holds_cell` matches it to a declared cell in any order).
    Intervention type: each distinct type of its interventions, in order of first appearance. Primary purpose:
    the design's one value. A field the record does not fill is the cell NONE, never a guessed value.
    """
    protocol = study.get("protocolSection")
    protocol = protocol if isinstance(protocol, dict) else {}
    design = protocol.get("designModule")
    design = design if isinstance(design, dict) else {}
    listed = design.get("phases")
    phases = [p for p in (listed if isinstance(listed, list) else []) if isinstance(p, str) and p]
    info = design.get("designInfo")
    purpose = info.get("primaryPurpose") if isinstance(info, dict) else None
    arms = protocol.get("armsInterventionsModule")
    interventions = arms.get("interventions") if isinstance(arms, dict) else None
    types = [
        item["type"]
        for item in (interventions if isinstance(interventions, list) else [])
        if isinstance(item, dict) and isinstance(item.get("type"), str) and item["type"]
    ]
    return {
        "phase": ["|".join(phases) if phases else NONE],
        "intervention_type": list(dict.fromkeys(types)) or [NONE],
        "primary_purpose": [purpose if isinstance(purpose, str) and purpose else NONE],
    }


def holds_cell(held: list[str], value: str) -> bool:
    """Whether a record's values on one axis hold a cell (pure — pinned): a value equal to it as a set of its
    "|"-joined parts, so a record listing "PHASE2|PHASE1" holds the declared "PHASE1|PHASE2", while
    "PHASE2" alone never holds a combined cell nor a combined value a single one."""
    parts = set(value.split("|"))
    return any(set(item.split("|")) == parts for item in held)


def query_forms(axis: str, value: str) -> list[str]:
    """The query forms `cell_query` builds one cell's query from: the axis's search area and, for a phase cell
    that leaves some phase out, the exact-phase `NOT` form."""
    if axis != "phase":
        return [f"AREA[{AXES[axis][0]}]"]
    excluded = [p for p in enum_labels("Phase") if p not in value.split("|")]
    return ["AREA[Phase]"] + (["NOT AREA[Phase]"] if excluded else [])


def cell_status(drawn: int, supplemented: int, registry: int | None, verified: bool) -> str:
    """What one declared cell of the balance table says (pure — pinned).

    `drawn` and `supplemented` count the sampled and the supplement trials whose records hold the cell;
    `registry` is the number of the frame's trials the registry says hold it, or None when it was not asked;
    `verified` says whether every form of the cell's query was tried live and returned trials.
      "present"           — a drawn trial holds the cell.
      "gap_supplemented"  — no drawn trial does, the registry holds some, and a supplement trial does.
      "gap"               — no drawn trial does and the registry holds some: a gap no supplement filled.
      "empty_in_registry" — no drawn trial does, and the frame holds none by a verified query: not a gap.
      "query_unverified"  — no drawn trial does and the registry returned none, by a query whose form was
                            never tried live: silence, never read as absence.
      "not_checked"       — no drawn trial does and the registry was not asked (a partial audit, or a sample
                            that declared no supplement).
    """
    if drawn > 0:
        return "present"
    if registry is None:
        return "not_checked"
    if registry == 0:
        return "empty_in_registry" if verified else "query_unverified"
    return "gap_supplemented" if supplemented > 0 else "gap"


def balance_rows(
    drawn: list[dict[str, list[str]]],
    supplements: list[dict[str, list[str]]],
    declared: dict[str, list[str]],
    registry: dict[str, int],
    verified: dict[str, str],
) -> list[dict[str, Any]]:
    """The balance table (pure — pinned): one row per declared cell of each axis, in the registry's order,
    then each value a record holds that no declared cell matches (NONE among them), in order of first
    appearance, as first written.

    `drawn` and `supplements` are the cells of each sampled and each supplement trial; `registry` maps
    "axis=value" to the frame's count for the cells that were asked; `verified` is the declared list of query
    forms tried live (`VERIFIED_FORMS`). A record's value counts for a cell by `holds_cell`, so a combined
    phase listed in another order still counts. A row counts the trials holding the cell in each group, says
    whether the cell is a registry value, and carries its `cell_status`; a value no enum declares is never a
    gap ("undeclared").
    """
    rows = []
    for axis, values in declared.items():
        seen: list[str] = []
        for cells in drawn + supplements:
            for v in cells.get(axis, []):
                if not holds_cell([*values, *seen], v):
                    seen.append(v)
        for value in [*values, *seen]:
            in_drawn = sum(holds_cell(cells.get(axis, []), value) for cells in drawn)
            in_supplement = sum(holds_cell(cells.get(axis, []), value) for cells in supplements)
            known = value in values
            count = registry.get(f"{axis}={value}")
            checked = known and all(form in verified for form in query_forms(axis, value))
            status = cell_status(in_drawn, in_supplement, count, checked) if known else "undeclared"
            rows.append(
                {"axis": axis, "value": value, "registry_value": known, "drawn": in_drawn}
                | {"supplement": in_supplement, "registry_count": count, "status": status}
            )
    return rows


def frame_condition() -> str:
    """The strata together, as one condition: the sampled frame within the base filter."""
    return "(" + " OR ".join(_condition(label) for label in (*CATEGORIES, NO_MESH)) + ")"


def cell_query(axis: str, value: str) -> str:
    """The registry query for the frame's trials holding one cell. A phase cell is exact: it excludes every
    other phase, so "PHASE2" never matches a "PHASE1|PHASE2" record."""
    piece = AXES[axis][0]
    if axis != "phase":
        return f"{BASE} AND {frame_condition()} AND AREA[{piece}]{value}"
    held = value.split("|")
    terms = [f"AREA[Phase]{p}" for p in held]
    terms += [f"NOT AREA[Phase]{p}" for p in enum_labels("Phase") if p not in held]
    return f"{BASE} AND {frame_condition()} AND " + " AND ".join(terms)


def draw_supplements(
    rows: list[dict[str, Any]],
    seed: str,
    per_cell: int,
    sampled: set[str],
    query_ids: Callable[..., tuple[list[str], str, str]],
    progress: Callable[[str], None],
) -> tuple[dict[str, int], list[dict[str, Any]], dict[str, str]]:
    """For each declared cell no drawn trial holds: the frame's IDs holding it, fetched live, and a seeded
    draw of `per_cell` from their discovery pool outside the sample, each its own labelled draw. Returns (the
    registry's count per asked cell, the supplement draws, the snapshot); every cell is read from one
    snapshot, or this fails (`SnapshotChanged`). Each draw carries its own inclusion probability n/N and the
    trial's union probability over every supplement draw whose pool held it, as the strata's draws do."""
    registry: dict[str, int] = {}
    supplements, snapshots = [], set()
    pools: dict[str, set[str]] = {}
    sizes: dict[str, tuple[int, int]] = {}
    for row in rows:
        if row["status"] != "not_checked":
            continue
        cell = f"{row['axis']}={row['value']}"
        query = cell_query(row["axis"], row["value"])
        ids, version, timestamp = query_ids({"filter.advanced": query}, progress=progress)
        snapshots.add((version, timestamp))
        registry[cell] = len(set(ids))
        label = SUPPLEMENT_LABEL.format(axis=row["axis"], value=row["value"])
        outside = [nct for nct in ids if nct not in sampled]
        picked, pool = draw(outside, per_cell, seed, label)
        pools[label], sizes[label] = set(outside), (len(picked), pool)
        probability = inclusion([label], sizes)
        supplements.extend(
            {"nct": nct, "axis": row["axis"], "value": row["value"], "label": label, "query": query}
            | {"matched": registry[cell], "pool": pool, "inclusion_probability": probability}
            for nct in picked
        )
        progress(f"{cell}: none drawn, {registry[cell]} in the frame, {len(picked)} drawn as a supplement")
    for item in supplements:
        item["memberships"] = [label for label in sizes if item["nct"] in pools[label]]
        item["union_inclusion_probability"] = inclusion(item["memberships"], sizes)
    if len(snapshots) > 1:
        raise SnapshotChanged(f"the registry changed while supplementing: {sorted(snapshots)}")
    version, timestamp = snapshots.pop() if snapshots else ("", "")
    return registry, supplements, {"api_version": version, "data_timestamp": timestamp}
