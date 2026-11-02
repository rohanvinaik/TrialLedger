"""Evaluation definitions, declared before anything is measured (add-bank-coverage Decision 8; B2, B6, B7).

Three levels, audited apart and traced: a mention (a concept's words, an atom), a scoped assertion (the
assertion layer's constraint over atoms) and an eligibility evaluation. Every measure takes its level and
reads only the gold records and emitted claims of that level; matching and judging refuse a mixture of levels.
Recall is measured only against gold annotation of a sample (auditing emitted claims alone cannot see a
miss); without it, recall is `not_measured`.

A gold record quotes the source words its claim rests on, the quote being the text's own at the claim's span,
and keeps each annotator's read: the annotator, a verdict (ANNOTATOR_VERDICTS) and the words that annotator
quoted, with their span. Agreement is source-grounded when at least two annotators read it and every read's
quote is the text at its own span; otherwise it is model-review agreement, never reported as adjudication
(B6). "agreed" needs two annotators at least.

Matching is one-to-one and declared here (MATCHING_RULE). Every measure carries its numerator and
denominator, its number of trials, its per-trial counts (claims are clustered by trial) and, where labels are
unresolved, the bounds C/(C+W+U) and (C+U)/(C+W+U); a measure whose denominator is zero is `not_measured`,
never 0 or 1. B7's release thresholds are declared as data (THRESHOLDS), with the measure each one reads
(THRESHOLD_MEASURE), the smallest sample a verdict is given on (MINIMUM_DENOMINATOR) and the seeded cluster
bootstrap over trials that gives the lower bound a verdict reads (BOOTSTRAP).
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

LEVELS = ("mention", "scoped_assertion", "eligibility")
RESOLUTIONS = ("agreed", "adjudicated", "unresolved")
JUDGEMENTS = ("correct", "wrong", "missed", "spurious", "unresolved")
# What one annotator says of a gold claim: the words hold it, they do not, or the annotator cannot tell.
ANNOTATOR_VERDICTS = ("holds", "does_not_hold", "unsure")
AGREEMENT_KINDS = ("source_grounded", "model_review_agreement")
MATCHING_RULE = (
    "A gold claim and an emitted claim are candidates when they share level, trial, record version, unit and "
    "concept id and their half-open spans overlap by at least one character. Candidates are paired one to "
    "one, greedily, in the order: longer overlap first, then the smaller distance between their starts, then "
    "the gold claim's position, then the emitted claim's. A paired claim is never paired again. Claims of "
    "different levels are never matched together: a mixture is refused."
)
MEASURES = (
    "any_mention_coverage",
    "complete_representation_coverage",
    "recall",
    "precision",
    "parameter_accuracy",
    "abstention_rate",
    "miss_rate",
)
# B7, declared 2026-11-01 before measuring: lower-bound precision per error class, recall target for the
# general packages. Abstention is always preferred to a wrong reading: no threshold rewards emitting.
CONSEQUENTIAL_CLASSES = ("polarity", "modality", "subject", "qualifier")
THRESHOLDS: dict[str, dict[str, float]] = {
    "precision_lower_bound": {"consequential": 0.95, "other": 0.90},
    "recall_target": {"general_packages": 0.70},
}
# The measure each threshold reads; a verdict on any other measure is refused (wrong_measure).
THRESHOLD_MEASURE = {"precision_lower_bound": "precision", "recall_target": "recall"}
# The smallest sample a verdict is given on: judged items in the denominator and distinct trials among them.
# Claude's first setting (2026-11-01), prior, not yet ratified by the founder (tasks.md 1.5).
MINIMUM_DENOMINATOR: dict[str, dict[str, int]] = {
    "precision_lower_bound": {"items": 30, "trials": 5},
    "recall_target": {"items": 30, "trials": 5},
}
# The cluster bootstrap a verdict's lower bound comes from: `resamples` draws of the trials with replacement,
# from random.Random(seed); the bound is the `lower_rank`-th smallest resampled rate (nearest rank: 50 of 2000
# is the 2.5th percentile, the lower end of a two-sided 95% percentile interval). Claude's first setting
# (2026-11-01), prior, not yet ratified by the founder (tasks.md 1.5).
BOOTSTRAP: dict[str, str | int] = {
    "seed": "evaluation-bootstrap-2026-11-01",
    "resamples": 2000,
    "lower_rank": 50,
}


@dataclass(frozen=True)
class Claim:
    """One claim at one level: the system's (source "bank:<name>") or a gold annotator's ("gold")."""

    level: str
    nct_id: str
    record_version: str
    unit_id: str  # the criterion (or other unit) of the record the span is on
    start: int
    end: int
    concept_id: str
    values: tuple[str, ...]
    params: tuple[tuple[str, str], ...]
    source: str


@dataclass(frozen=True)
class Read:
    """One annotator's read of a gold claim: its verdict and the words it quoted, at their half-open span on
    the unit's text."""

    annotator: str
    verdict: str
    quote: str
    start: int
    end: int


@dataclass(frozen=True)
class GoldRecord:
    """The gold-annotation record: a claim, the source words at its span, each annotator's read, the kind of
    agreement the reads make (AGREEMENT_KINDS) and how the record was resolved (agreed by two annotators at
    least, adjudicated on the source, or left unresolved)."""

    claim: Claim
    quote: str
    reads: tuple[Read, ...]
    agreement: str
    resolution: str


@dataclass(frozen=True)
class Measure:
    name: str
    level: str
    numerator: int
    denominator: int
    trials: int
    lower: float | None  # C/(C+W+U), or the plain rate when nothing is unresolved
    upper: float | None  # (C+U)/(C+W+U)
    status: str  # measured or not_measured
    note: str
    # per trial, in trial order: (nct_id, hits C, misses W, unresolved U) of the denominator's items
    clusters: tuple[tuple[str, int, int, int], ...] = ()


def agreement_kind(text: str, reads: Iterable[Read]) -> str:
    """What an agreement between reads is, B6 (pure — pinned): source_grounded when at least two distinct
    annotators read the claim and every read's quote is exactly the text at its own span (0 <= start < end <=
    len(text) and text[start:end] == quote); otherwise model_review_agreement, which is never reported as
    adjudication. Words found elsewhere in the text, or the same annotator twice, do not ground it."""
    given = list(reads)
    annotators = {read.annotator for read in given if read.annotator}
    grounded = all(
        0 <= read.start < read.end <= len(text) and text[read.start : read.end] == read.quote
        for read in given
    )
    return "source_grounded" if len(annotators) >= 2 and grounded else "model_review_agreement"


def gold_problems(record: GoldRecord, text: str) -> tuple[str, ...]:
    """What makes a gold record unusable against its unit's text (pure — pinned).

    unknown_level; unversioned_record (no record version); span_out_of_bounds (not 0 <= start < end <=
    len(text)); quote_mismatch (the record's quote is not text[start:end] exactly, so the annotation is not
    grounded in the source); no_annotator (no read); unknown_verdict (a read's verdict outside
    ANNOTATOR_VERDICTS); unknown_resolution; agreed_without_two_annotators (resolution "agreed" with fewer
    than two distinct annotators); agreed_without_assent (resolution "agreed" while a read's verdict is not
    "holds"); misstated_agreement (the recorded agreement is not agreement_kind of the reads on this text).
    Each once, in that order. No problem: an empty tuple.
    """
    claim = record.claim
    found = []
    if claim.level not in LEVELS:
        found.append("unknown_level")
    if not claim.record_version:
        found.append("unversioned_record")
    inside = 0 <= claim.start < claim.end <= len(text)
    if not inside:
        found.append("span_out_of_bounds")
    if not inside or text[claim.start : claim.end] != record.quote:
        found.append("quote_mismatch")
    if not record.reads:
        found.append("no_annotator")
    if any(read.verdict not in ANNOTATOR_VERDICTS for read in record.reads):
        found.append("unknown_verdict")
    if record.resolution not in RESOLUTIONS:
        found.append("unknown_resolution")
    if record.resolution == "agreed":
        if len({read.annotator for read in record.reads if read.annotator}) < 2:
            found.append("agreed_without_two_annotators")
        if any(read.verdict != "holds" for read in record.reads):
            found.append("agreed_without_assent")
    if record.agreement != agreement_kind(text, record.reads):
        found.append("misstated_agreement")
    return tuple(found)


def _single_level(claims: Iterable[Claim]) -> None:
    levels = sorted({claim.level for claim in claims})
    if len(levels) > 1:
        raise ValueError(f"claims of different levels are never evaluated together: {levels}")


def _known_level(level: str) -> None:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r}; the levels are {LEVELS}")


def at_level(
    level: str, gold: list[GoldRecord] | None, emitted: list[Claim]
) -> tuple[list[GoldRecord], list[Claim]]:
    """The gold records and emitted claims of one level, each list in its given order (pure — pinned).
    Claims of every other level are left out; an absent gold sample is an empty list. A level outside LEVELS:
    ValueError, never an empty reading."""
    _known_level(level)
    return (
        [record for record in gold or [] if record.claim.level == level],
        [claim for claim in emitted if claim.level == level],
    )


def _key(claim: Claim) -> tuple[str, str, str, str, str]:
    return (claim.level, claim.nct_id, claim.record_version, claim.unit_id, claim.concept_id)


def match(gold: list[Claim], emitted: list[Claim]) -> list[tuple[int, int]]:
    """The one-to-one pairs (gold index, emitted index) of MATCHING_RULE, in pairing order (pure — pinned).

    Candidates share level, trial, record version, unit and concept and overlap by a character at least;
    the longest overlap pairs first, then the nearer starts, then the earlier gold and emitted positions; a
    claim paired once is never paired again. No candidate: an empty list. Claims of more than one level,
    gold and emitted together: ValueError (a measure reads one level, through at_level)."""
    _single_level([*gold, *emitted])
    candidates = sorted(
        (
            -(min(g.end, e.end) - max(g.start, e.start)),
            abs(g.start - e.start),
            gi,
            ei,
        )
        for gi, g in enumerate(gold)
        for ei, e in enumerate(emitted)
        if _key(g) == _key(e) and max(g.start, e.start) < min(g.end, e.end)
    )
    pairs: list[tuple[int, int]] = []
    used_gold: set[int] = set()
    used_emitted: set[int] = set()
    for _overlap, _distance, gi, ei in candidates:
        if gi not in used_gold and ei not in used_emitted:
            pairs.append((gi, ei))
            used_gold.add(gi)
            used_emitted.add(ei)
    return pairs


def judge(gold: list[GoldRecord], emitted: list[Claim]) -> tuple[list[str], list[str]]:
    """Each gold record's and each emitted claim's judgement after matching (pure — pinned).

    A paired gold record: unresolved when its resolution is, else correct when the emitted claim's values and
    params equal its own (params as a set), else wrong; its emitted claim gets the same judgement. An unpaired
    gold record: missed (unresolved when its resolution is). An unpaired emitted claim in a unit the gold
    sample annotated: spurious; in a unit it did not annotate: unresolved (no gold says either way). Claims of
    more than one level: ValueError."""
    claims = [record.claim for record in gold]
    pairs = match(claims, emitted)
    gold_judged = ["unresolved" if r.resolution == "unresolved" else "missed" for r in gold]
    annotated = {(c.level, c.nct_id, c.record_version, c.unit_id) for c in claims}
    emitted_judged = [
        "spurious" if (e.level, e.nct_id, e.record_version, e.unit_id) in annotated else "unresolved"
        for e in emitted
    ]
    for gi, ei in pairs:
        g, e = claims[gi], emitted[ei]
        same = g.values == e.values and set(g.params) == set(e.params)
        verdict = "unresolved" if gold[gi].resolution == "unresolved" else "correct" if same else "wrong"
        gold_judged[gi] = emitted_judged[ei] = verdict
    return gold_judged, emitted_judged


def bounds(correct: int, wrong: int, unresolved: int) -> tuple[float, float] | None:
    """The bounds of a rate with unresolved labels: (C/(C+W+U), (C+U)/(C+W+U)) (pure — pinned). Nothing
    labelled (C+W+U = 0): None, not measured, never 0 or 1."""
    total = correct + wrong + unresolved
    if total == 0:
        return None
    return correct / total, (correct + unresolved) / total


def rate(
    name: str,
    level: str,
    judged: Iterable[tuple[str, str]],
    hits: tuple[str, ...],
    misses: tuple[str, ...],
    note: str = "",
) -> Measure:
    """A rate over judged items `(nct_id, judgement)`, clustered by trial (pure — pinned).

    The numerator counts the items judged one of `hits`; the denominator the items judged one of `hits`,
    `misses` or unresolved (any other judgement is outside this measure); bounds treat unresolved items as
    possibly a hit; `trials` counts the distinct trials of the denominator's items and `clusters` gives each
    of them, in trial order, with its hits, misses and unresolved items. An empty denominator: not_measured
    with no bounds and no clusters."""
    items = [(nct, j) for nct, j in judged if j in hits or j in misses or j == "unresolved"]
    counts: dict[str, list[int]] = {}
    for nct, j in items:
        tally = counts.setdefault(nct, [0, 0, 0])
        tally[0 if j in hits else 2 if j == "unresolved" else 1] += 1
    correct = sum(tally[0] for tally in counts.values())
    unresolved = sum(tally[2] for tally in counts.values())
    found = bounds(correct, len(items) - correct - unresolved, unresolved)
    if found is None:
        return Measure(name, level, 0, 0, 0, None, None, "not_measured", note or "no item to measure")
    clusters = tuple((nct, counts[nct][0], counts[nct][1], counts[nct][2]) for nct in sorted(counts))
    return Measure(
        name, level, correct, len(items), len(counts), found[0], found[1], "measured", note, clusters
    )


def recall(level: str, gold: list[GoldRecord] | None, emitted: list[Claim]) -> Measure:
    """Recall against gold annotation of one level, or not_measured when no gold record of that level was
    annotated (pure — pinned): correct gold records over every gold record (correct, wrong, missed or
    unresolved), clustered by trial; gold and emitted claims of other levels are left out. An empty or
    absent gold sample: not_measured, whatever was emitted and audited. An unknown level: ValueError."""
    gold, emitted = at_level(level, gold, emitted)
    if not gold:
        return Measure("recall", level, 0, 0, 0, None, None, "not_measured", "no gold sample annotated")
    gold_judged, _ = judge(gold, emitted)
    judged = [(record.claim.nct_id, j) for record, j in zip(gold, gold_judged, strict=True)]
    return rate("recall", level, judged, ("correct",), ("wrong", "missed"))


def precision(level: str, emitted: list[Claim], verdicts: list[str]) -> Measure:
    """Precision of the emitted claims of one level from their verdicts, one per claim in order (from `judge`
    against gold, or from a source-grounded audit of the claims alone) (pure — pinned): correct over correct,
    wrong, spurious and unresolved, with the unresolved bounds, clustered by trial; claims of other levels
    and their verdicts are left out. No judged claim: not_measured. An unknown level: ValueError."""
    _known_level(level)
    judged = [
        (claim.nct_id, verdict)
        for claim, verdict in zip(emitted, verdicts, strict=True)
        if claim.level == level
    ]
    return rate("precision", level, judged, ("correct",), ("wrong", "spurious"))


def miss_rate(level: str, gold: list[GoldRecord], emitted: list[Claim]) -> Measure:
    """The share of one level's gold records no emitted claim of that level matched (pure — pinned): missed
    over every gold record, unresolved ones bounding it, clustered by trial. No gold of the level:
    not_measured. An unknown level: ValueError."""
    gold, emitted = at_level(level, gold, emitted)
    gold_judged, _ = judge(gold, emitted) if gold else ([], [])
    judged = [(record.claim.nct_id, j) for record, j in zip(gold, gold_judged, strict=True)]
    return rate("miss_rate", level, judged, ("missed",), ("correct", "wrong"), "" if gold else "no gold")


def unit_rates(
    level: str,
    units: list[tuple[str, str, str]],
    emitted: list[Claim],
    abstained: set[tuple[str, str, str]],
) -> tuple[Measure, Measure]:
    """Any-mention coverage and the abstention rate over units (pure — pinned).

    Units are `(nct_id, record_version, unit_id)`: the units with at least one emitted claim of the level
    (claims of other levels never cover a unit), and the units a bank abstained on at this level, each over
    every unit, clustered by trial. No unit: both not_measured. An unknown level: ValueError."""
    _, emitted = at_level(level, None, emitted)
    mentioned = {(c.nct_id, c.record_version, c.unit_id) for c in emitted}
    covered = [(u[0], "covered" if u in mentioned else "uncovered") for u in units]
    abstaining = [(u[0], "abstained" if u in abstained else "answered") for u in units]
    return (
        rate("any_mention_coverage", level, covered, ("covered",), ("uncovered",)),
        rate("abstention_rate", level, abstaining, ("abstained",), ("answered",)),
    )


def complete_representation(level: str, gold: list[GoldRecord], emitted: list[Claim]) -> Measure:
    """Complete-representation coverage over the units the gold sample annotated at one level
    (pure — pinned).

    A unit is complete when every gold record of it is judged correct and no emitted claim of the level in it
    is wrong or spurious; unresolved when it would be complete but for an unresolved record or claim; else
    incomplete. Complete over every annotated unit, with the unresolved bounds, clustered by trial; claims of
    other levels are left out. No gold of the level: not_measured. An unknown level: ValueError."""
    gold, emitted = at_level(level, gold, emitted)
    gold_judged, emitted_judged = judge(gold, emitted) if gold else ([], ["unresolved"] * len(emitted))
    units: dict[tuple[str, str, str], set[str]] = {}
    for record, judgement in zip(gold, gold_judged, strict=True):
        claim = record.claim
        units.setdefault((claim.nct_id, claim.record_version, claim.unit_id), set()).add(judgement)
    for claim, judgement in zip(emitted, emitted_judged, strict=True):
        unit = (claim.nct_id, claim.record_version, claim.unit_id)
        if unit in units:
            units[unit].add(judgement)
    judged = [
        (
            unit[0],
            "incomplete"
            if found & {"wrong", "missed", "spurious"}
            else "unresolved"
            if "unresolved" in found
            else "complete",
        )
        for unit, found in units.items()
    ]
    note = "" if gold else "no gold sample annotated"
    return rate("complete_representation_coverage", level, judged, ("complete",), ("incomplete",), note)


def parameter_accuracy(level: str, gold: list[GoldRecord], emitted: list[Claim]) -> dict[str, Measure]:
    """Accuracy of each parameter field over one level's matched, resolved pairs (pure — pinned): for each
    field a gold record states, the pairs whose emitted claim states the same value over the pairs whose gold
    states the field, clustered by trial; fields in name order; claims of other levels are left out. No
    resolved pair: an empty dict. An unknown level: ValueError."""
    gold, emitted = at_level(level, gold, emitted)
    claims = [record.claim for record in gold]
    judged: dict[str, list[tuple[str, str]]] = {}
    for gi, ei in match(claims, emitted):
        if gold[gi].resolution == "unresolved":
            continue
        stated = dict(emitted[ei].params)
        for field, value in claims[gi].params:
            verdict = "correct" if stated.get(field) == value else "wrong"
            judged.setdefault(field, []).append((claims[gi].nct_id, verdict))
    return {
        field: rate(f"parameter_accuracy:{field}", level, judged[field], ("correct",), ("wrong",))
        for field in sorted(judged)
    }


def clustered_lower_bound(
    clusters: tuple[tuple[str, int, int, int], ...], seed: str, resamples: int, lower_rank: int
) -> float | None:
    """The lower bound of a rate from a cluster bootstrap over trials (pure — pinned).

    Each of `resamples` draws picks len(clusters) trials uniformly with replacement, by
    random.Random(seed).randrange, and computes the pessimistic rate of the drawn trials: their hits over
    their hits, misses and unresolved items, C/(C+W+U), so an unresolved item counts as a miss. The bound is
    the `lower_rank`-th smallest of the drawn rates (nearest rank, counted from 1). The same clusters, seed,
    count and rank give the same bound on every run. No cluster, no draw, a rank outside 1..resamples, or a
    draw with no item: None, never a number."""
    if not clusters or resamples < 1 or not 1 <= lower_rank <= resamples:
        return None
    draw_from = random.Random(seed)
    rates: list[float] = []
    for _ in range(resamples):
        drawn = [clusters[draw_from.randrange(len(clusters))] for _ in clusters]
        total = sum(hits + misses + unresolved for _nct, hits, misses, unresolved in drawn)
        if total == 0:
            return None
        rates.append(sum(hits for _nct, hits, _misses, _unresolved in drawn) / total)
    return sorted(rates)[lower_rank - 1]


def precision_group(error_class: str) -> str:
    """The precision threshold group of an error class, B7 (pure — pinned): consequential for polarity,
    modality, subject and qualifier (CONSEQUENTIAL_CLASSES), other for any other class."""
    return "consequential" if error_class in CONSEQUENTIAL_CLASSES else "other"


def threshold_verdict(measure: Measure, threshold: str, group: str) -> str:
    """A measure against one of B7's declared thresholds (pure — pinned).

    unknown_threshold: `threshold` is not in THRESHOLDS or `group` is not one of its groups (precision's
    groups are precision_group's). wrong_measure: the measure is not the one the threshold reads
    (THRESHOLD_MEASURE: precision_lower_bound reads precision, recall_target reads recall). not_measured: the
    measure was not measured. insufficient_denominator: fewer judged items or fewer trials than
    MINIMUM_DENOMINATOR declares for the threshold. Otherwise the verdict reads clustered_lower_bound of the
    measure's per-trial counts under BOOTSTRAP (the 50th smallest of 2000 seeded cluster resamples of the
    pessimistic rate C/(C+W+U)), never the measure's own bounds: meets at or above the threshold's value,
    below under it, not_measured if no bound can be computed. Never met on a measure not measured."""
    values = THRESHOLDS.get(threshold)
    if values is None or group not in values:
        return "unknown_threshold"
    if measure.name != THRESHOLD_MEASURE[threshold]:
        return "wrong_measure"
    if measure.status != "measured":
        return "not_measured"
    minimum = MINIMUM_DENOMINATOR[threshold]
    if measure.denominator < minimum["items"] or measure.trials < minimum["trials"]:
        return "insufficient_denominator"
    lower = clustered_lower_bound(
        measure.clusters, str(BOOTSTRAP["seed"]), int(BOOTSTRAP["resamples"]), int(BOOTSTRAP["lower_rank"])
    )
    if lower is None:
        return "not_measured"
    return "meets" if lower >= values[group] else "below"
