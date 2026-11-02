"""Declared expectations: one predicate, its observation status per trial, its conditional rarity,
and the status of each deviation (openspec/changes/add-design-synthesis).

An expectation is declared, never discovered here: a predicate, the trials it applies to, the cell and
parent it is measured over, the support each needs, and its provenance. The caller supplies each
observation status and its warrant; this module does not read eligibility text:

  present            — the trial excludes it (an exclusion criterion names it; or an inclusion
                       criterion negates it or says its patients are excluded);
  explicitly_negated — the trial admits it (an inclusion criterion names it as eligible, or an
                       exclusion criterion says such patients are eligible);
  not_documented     — the whole text was read and nothing names it: never "admitted";
  unresolved         — it is named where its scope cannot be told (unsectioned text, or cohorts
                       that disagree);
  not_applicable     — the expectation does not apply to the trial (the caller decides, from its
                       experimental drugs' classes).

Rarity is conditional corpus rarity, −log2 of a frequency in a declared cell, not the derivational
significance of SIGNIFICANCE_WEIGHTING.md (that needs a space of admissible alternatives, a later
target). A deviation that is valid and unexplained stays a verified deviation; it is never noise.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

STATUSES = ("present", "explicitly_negated", "not_documented", "unresolved", "not_applicable")


@dataclass(frozen=True)
class Expectation:
    id: str
    statement: str
    applies_to: tuple[str, ...]  # experimental-drug classes (FDA EPC names, or "stated: <target>")
    cell: str  # the coordinate the cell is keyed by
    parent: str  # the parent cell: "all" (every applicable trial)
    support: int  # the fewest known observations a cell needs before it reports a rarity
    provenance: str


# Historical declared hypothesis, retained with its original development provenance. It is not a
# confirmed clinical rule and is not applied automatically by the public reasoning operation.
FROZEN = (
    Expectation(
        "checkpoint_blockers_exclude_autoimmune_disease",
        "A trial whose experimental drug blocks PD-1 or PD-L1 excludes patients with autoimmune disease.",
        (
            "Programmed Death Receptor-1 Blocking Antibody",
            "Programmed Death Ligand-1 Blocker",
            "stated: PD-1",
            "stated: PD-L1",
        ),
        "setting",
        "all",
        10,
        "prior: immune-related adverse events of checkpoint blockade (domain knowledge; the "
        "drugs' label warnings); surfaced as a mechanism signal on development data (487 Phase 3 "
        "NSCLC trials, 2026-10-31); frozen 2026-10-31 at the founder's word; confirmation needs "
        "a population no rule was written against",
    ),
)


def conditional_rarity(
    observations: list[tuple[str, str]], cell: str, support: int
) -> tuple[str, float | None, int, float | None, float | None]:
    """The share of "present" among known observations in a cell, with rarities (pure — pinned).

    `observations` are (cell key, status) for every applicable trial. Known statuses are present,
    explicitly_negated and not_documented; unresolved and not_applicable count nowhere. Returns
    (source, P(present), known count, bits of a present observation, bits of an absent one).
    Source is "cell" when the cell has at least `support` known observations, "parent" (every
    applicable trial) when only the parent has, and "abstain" (no share, no bits) when neither
    does. A share of 0 or 1 gives None for the observation that never occurred: an unobserved
    event has no finite rarity here.
    """
    known = [(key, status) for key, status in observations if status in STATUSES[:3]]
    in_cell = [status for key, status in known if key == cell]
    if len(in_cell) >= support:
        source, chosen = "cell", in_cell
    elif len(known) >= support:
        source, chosen = "parent", [status for _, status in known]
    else:
        return "abstain", None, len(in_cell), None, None
    share = sum(1 for status in chosen if status == "present") / len(chosen)
    present_bits = round(-math.log2(share), 3) if share > 0 else None
    absent_bits = round(-math.log2(1 - share), 3) if share < 1 else None
    return source, round(share, 4), len(chosen), present_bits, absent_bits


def deviation_status(status: str, qualifiers: int, audit: str) -> str:
    """How an observation stands against an expectation that its predicate is present
    (pure — pinned).

    audit "invalid" (the founder found the span does not say what was read) → invalid_extraction,
    whatever the status; not_applicable → not_applicable; unresolved → scope_unresolved; present →
    conforms; not_documented → omission (silence is not admission, and never shares its label);
    explicitly_negated with a condition recorded → explanation_supported; explicitly_negated
    otherwise → verified_deviation (valid, and unexplained until something explains it).
    """
    if audit == "invalid":
        return "invalid_extraction"
    if status == "not_applicable":
        return "not_applicable"
    if status == "unresolved":
        return "scope_unresolved"
    if status == "present":
        return "conforms"
    if status == "not_documented":
        return "omission"
    if status == "explicitly_negated" and qualifiers > 0:
        return "explanation_supported"
    return "verified_deviation"
