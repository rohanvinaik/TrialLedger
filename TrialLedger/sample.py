"""A live, stratified, declared sample of interventional trials (add-targeted-questions, Decision 9).

Strata are the registry's top-level condition categories, read from its derived condition MeSH (a label for
spread, never a fact about a trial: the derived MeSH is wrong for some records), plus the trials with no
condition MeSH at all. For each stratum the full NCT ID list is fetched live, from one snapshot; a seeded
simple random draw is taken within it from the discovery pool, never from the confirmation pool that a hash of
the NCT ID reserves; trials drawn in several strata are kept once, with every membership and their union
inclusion probability. Everything is kept: the queries, the pool sizes, the seed, the snapshot and the draw.
Each drawn trial is resolved later, one at a time."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable
from typing import Any

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


def stratum_query(label: str) -> str:
    """The registry query of one stratum: the base filter and the category as a condition term or ancestor."""
    if label == NO_MESH:
        return f"{BASE} AND AREA[ConditionMeshTerm]MISSING"
    term = f'"{label}"'
    return f"{BASE} AND (AREA[ConditionMeshTerm]{term} OR AREA[ConditionAncestorTerm]{term})"


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
        raise RuntimeError(f"the registry changed while sampling: {sorted(snapshots)}")
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
        "strata": strata,
        "trials": [
            {"nct": nct, "strata": labels, "inclusion_probability": inclusion(labels, sizes)}
            for nct, labels in members.items()
        ],
    }
