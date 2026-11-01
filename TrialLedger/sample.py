"""A live, stratified, declared sample of interventional trials (add-targeted-questions, Decision 9).

Strata are the registry's top-level condition categories, read from its derived condition MeSH (a label for
spread, never a fact about a trial: the derived MeSH is wrong for some records), plus the trials with no
condition MeSH at all. For each stratum the full NCT ID list is fetched live, from one snapshot; a seeded
simple random draw is taken within it from the discovery pool, never from the confirmation pool that a hash of
the NCT ID reserves; trials drawn in several strata are kept once, with every membership and their union
inclusion probability. Everything is kept: the queries, the pool sizes, the seed, the snapshot and the draw.
Each drawn trial is resolved later, one at a time.

The confirmation pool is three sequential batches (add-bank-coverage B8): `pool` names a trial's pool,
discovery or confirmation batch 0, 1 or 2 (SHA-256 mod 10 equal to 0, 1, 2), one batch per release, never
reused for a revised version. A confirmation sample is drawn from exactly one named batch (`draw_batch`),
only when `batch_request` allows it, and records the batch; `reserved` still means "in any confirmation
batch". A confirmation draw never takes a trial already inspected (Decision 9, B4): the inspected
populations (the NSCLC record, the pilot and discovery samples) are declared as kept files whose IDs
`inspected_ids` reads, `screen_inspected` removes them before the draw, and the sample keeps each list and
counts what it excluded.
It is allowed only for code clean at a named commit (TrialLedger/ and tests/, `code_state`, with a digest of
their source) and only for a batch the ledger of used batches has not already given to another commit.

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
import subprocess
from collections.abc import Callable
from pathlib import Path
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
# add-bank-coverage founder decision B8 (2026-11-01): the confirmation pool is three sequential 10% batches,
# sha256(NCT ID) mod 10 equal to 0, 1 and 2, one per release, never reused for a revised version.
DISCOVERY = "discovery"
CONFIRMATION_BATCHES = (0, 1, 2)
BATCH_POOL = "confirmation_{batch}"
NOT_A_CHECKOUT = "not a git checkout"  # what record.code_commit says when git cannot name the code's version


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


def pool(nct: str) -> str:
    """The pool an NCT ID belongs to (pure — pinned; add-bank-coverage B8): "confirmation_0",
    "confirmation_1" or "confirmation_2" when its SHA-256 mod 10 is 0, 1 or 2 (the three sequential
    confirmation batches, one per release), else "discovery". A trial is in a confirmation batch exactly when
    `reserved` holds, so the discovery pool is unchanged."""
    residue = int(hashlib.sha256(nct.encode("ascii")).hexdigest(), 16) % 10
    return BATCH_POOL.format(batch=residue) if residue in CONFIRMATION_BATCHES else DISCOVERY


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WATCHED = ("TrialLedger", "tests")  # the code a confirmation draw confirms: clean at its commit, digested


def git_query(root: Path, *args: str) -> str:
    """One git command run in `root`: its standard output. Raises OSError or CalledProcessError when git
    cannot answer (no git, not a checkout)."""
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout


def code_state(root: Path = PACKAGE_ROOT, git: Callable[..., str] | None = None) -> dict[str, Any]:
    """The version of the code a confirmation draw would confirm, read through `git` (default `git_query`):
    the commit HEAD names, every changed or untracked (not ignored) path under `WATCHED`, and the SHA-256 of
    the tracked files under `WATCHED` as sorted "path NUL sha256(bytes)" lines. The commit is "" when git
    cannot answer; a tracked file that cannot be read leaves the digest ""."""
    ask = git or git_query
    try:
        commit = ask(root, "rev-parse", "HEAD").strip()
        status = ask(root, "status", "--porcelain", "--untracked-files=all", "--", *WATCHED)
        tracked = sorted(name for name in ask(root, "ls-files", "-z", "--", *WATCHED).split("\0") if name)
    except (OSError, subprocess.CalledProcessError):
        return {"commit": "", "dirty": [], "source_digest": "", "watched": list(WATCHED)}
    digest = hashlib.sha256()
    try:
        for name in tracked:
            digest.update(f"{name}\0{hashlib.sha256((root / name).read_bytes()).hexdigest()}\n".encode())
    except OSError:
        digest = None
    return {
        "commit": commit,
        "dirty": [line[3:] for line in status.splitlines() if line.strip()],
        "source_digest": digest.hexdigest() if digest else "",
        "watched": list(WATCHED),
    }


def inspected_ids(document: Any) -> list[str]:
    """The NCT IDs a kept file of an inspected population lists (pure — pinned; Decision 9, B4), each once,
    sorted: a sample's drawn trials (`trials[].nct`), an audit's balance supplement (`supplements[].nct`) and
    a record's studies (`studies[].protocolSection.identificationModule.nctId`). Anything else lists nothing,
    so a file of none of these shapes gives no ID, never a guessed one."""
    if not isinstance(document, dict):
        return []
    found: set[str] = set()
    for key in ("trials", "supplements"):
        items = document.get(key)
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and isinstance(item.get("nct"), str) and item["nct"]:
                found.add(item["nct"])
    studies = document.get("studies")
    for study in studies if isinstance(studies, list) else []:
        protocol = study.get("protocolSection") if isinstance(study, dict) else None
        ident = protocol.get("identificationModule") if isinstance(protocol, dict) else None
        nct = ident.get("nctId") if isinstance(ident, dict) else None
        if isinstance(nct, str) and nct:
            found.add(nct)
    return sorted(found)


def ledger_batches(document: Any) -> dict[str, str] | None:
    """The used batches a ledger file declares (pure — pinned; add-bank-coverage B8): its `batches`, each a
    declared batch ("0", "1", "2") mapped to the non-empty code commit it confirmed; None when the file is not
    of that shape, so a malformed ledger is never read as one with no batch used."""
    if not isinstance(document, dict) or not isinstance(document.get("batches"), dict):
        return None
    batches = document["batches"]
    names = {str(b) for b in CONFIRMATION_BATCHES}
    if not all(key in names and isinstance(value, str) and value for key, value in batches.items()):
        return None
    return dict(batches)


def batch_request(
    batch: int, commit: str, dirty: list[str], inspected: list[int], used: dict[str, str] | None
) -> str:
    """Whether a confirmation draw from one named batch may be made (pure — pinned; add-bank-coverage B8,
    Decision 9, B4). `commit` and `dirty` are the code's (`code_state`), `inspected` the number of IDs in each
    declared list of inspected trials, `used` the ledger's batches (`ledger_batches`).
    "ok"                  — a declared batch, clean code at a named commit, every inspected list holding
                            IDs, and the batch unused or used for this same commit.
    "unknown_batch"       — not 0, 1 or 2: no other confirmation batch is declared.
    "no_code_version"     — git cannot name the code's commit.
    "uncommitted_changes" — TrialLedger/ or tests/ differs from the commit, so it names no code exactly.
    "no_inspected"        — no inspected population declared: nothing shows the draw excludes them.
    "inspected_empty"     — a declared inspected list holds no ID (unreadable, or not a sample or record).
    "ledger_unreadable"   — the ledger of used batches is missing or malformed.
    "batch_used"          — the ledger gives the batch to another commit: a batch never confirms twice.
    """
    if batch not in CONFIRMATION_BATCHES:
        return "unknown_batch"
    if not commit or commit == NOT_A_CHECKOUT:
        return "no_code_version"
    if dirty:
        return "uncommitted_changes"
    if not inspected:
        return "no_inspected"
    if not all(count > 0 for count in inspected):
        return "inspected_empty"
    if used is None:
        return "ledger_unreadable"
    if used.get(str(batch), commit) != commit:
        return "batch_used"
    return "ok"


def screen_inspected(ids: list[str], inspected: frozenset[str], batch: int) -> tuple[list[str], list[str]]:
    """One stratum's IDs with every inspected trial removed (pure — pinned; Decision 9, B4). Returns (the IDs
    not inspected, in their order; the distinct IDs of that confirmation batch removed, sorted): an inspected
    trial outside the batch could never be drawn, so it is not counted as excluded."""
    name = BATCH_POOL.format(batch=batch)
    kept = [nct for nct in ids if nct not in inspected]
    excluded = sorted({nct for nct in ids if nct in inspected and pool(nct) == name})
    return kept, excluded


def draw_batch(ids: list[str], n: int, seed: str, label: str, batch: int) -> tuple[list[str], int]:
    """A seeded simple random draw of `n` from one stratum's IDs in one confirmation batch (pure — pinned;
    add-bank-coverage B8).

    The pool is the stratum's distinct IDs whose `pool` is that batch, sorted, so the draw depends on the set
    of IDs, the seed, the label and the batch alone; never an ID of the discovery pool or of another batch.
    Returns (the drawn IDs in draw order, the pool size); fewer than `n` when the pool is smaller.
    """
    name = BATCH_POOL.format(batch=batch)
    members = sorted({nct for nct in ids if pool(nct) == name})
    rng = random.Random(f"{seed}:{name}:{label}")
    return rng.sample(members, min(max(n, 0), len(members))), len(members)


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
    batch: int | None = None,
    inspected: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """The whole sample, fetched live: every stratum's IDs, its draw, and each drawn trial's memberships and
    union inclusion probability. Every stratum is read from the same registry snapshot, or the sample fails.

    With `batch` (add-bank-coverage B8), every stratum is drawn from that one confirmation batch instead of
    the discovery pool, and the sample records the batch; its balance check declares no supplement, since a
    supplement is drawn from the discovery pool and would mix discovery trials into a confirmation sample.
    Every `inspected` ID is removed before a batch draw (`screen_inspected`); each stratum and the sample
    count the distinct batch trials so excluded.
    """
    strata, members, snapshots = [], {}, set()
    pools: dict[str, set[str]] = {}
    excluded: set[str] = set()
    drawn_from = DISCOVERY if batch is None else BATCH_POOL.format(batch=batch)
    for label in (*CATEGORIES, NO_MESH):
        query = stratum_query(label)
        ids, version, timestamp = query_ids({"filter.advanced": query}, progress=progress)
        snapshots.add((version, timestamp))
        stratum: dict[str, Any] = {"label": label, "query": query, "matched": len(ids)}
        if batch is None:
            drawn, size = draw(ids, per_stratum, seed, label)
        else:
            kept, removed = screen_inspected(ids, inspected, batch)
            drawn, size = draw_batch(kept, per_stratum, seed, label, batch)
            stratum["inspected_excluded"] = len(removed)
            excluded.update(removed)
        pools[label] = set(ids)
        strata.append(stratum | {"pool": size, "drawn": drawn})
        progress(f"{label}: {len(ids)} trials, {size} in the {drawn_from} pool, {len(drawn)} drawn")
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
        "confirmation_batches": {
            BATCH_POOL.format(batch=b): f"sha256(NCT ID) mod 10 == {b}" for b in CONFIRMATION_BATCHES
        },
        "drawn_from": drawn_from,
        "confirmation_batch": batch,
        "inspected_excluded": None if batch is None else len(excluded),
        "api_version": version,
        "data_timestamp": timestamp,
        "balance": balance_declaration(SUPPLEMENT_PER_CELL if batch is None else 0),
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


def balance_declaration(per_cell: int = SUPPLEMENT_PER_CELL) -> dict[str, Any]:
    """The balance check and its supplement (`per_cell` trials per empty cell; none for a confirmation
    sample), declared in the sample before any trial is resolved."""
    return {
        "axes": {axis: piece for axis, (piece, _enum) in AXES.items()},
        "cells": declared_cells(),
        "supplement_per_cell": per_cell,
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
