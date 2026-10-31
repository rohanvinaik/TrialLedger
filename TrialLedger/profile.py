"""The information layer: every typed element measured against a declared population of comparable trials.

Four quantities are kept apart (the founder accepted this correction, 2026-10-31): logical state (each trial's
coordinate domains), frequency (an element's share of the trials whose eligibility text was itemized and
typed, so an untyped trial is never counted as lacking anything), association (an element's frequency among
trials whose experimental drug carries a class, against the rest of the stratum, with the number of distinct
lead sponsors behind it and the number of trials whose experimental class is unresolved), and relevance, which
belongs to each view. Surprisal, −log2 of a frequency, measures how unexpected an element is in the stratum,
not how important it is. A standard element (stated by at least STANDARD_SHARE of a stratum) is the empirical
source of reusable protocol language, not a verdict on its clinical value. An association is offered only as a
proposed relation, never as an established one; a design-space cell is occupied, unknown (unresolved trials
could fall in it) or empty, never empty while unknown.
"""

from __future__ import annotations

import math

STANDARD_SHARE = 0.9
SIGNAL_MIN_TRIALS = 5
SIGNAL_MIN_SPONSORS = 3

# One trial, as the profile reads it: (nct, lead sponsor, stratum, typed, elements, classes, class_unresolved)
Trial = tuple[str, str, str, bool, list[str], list[str], bool]


def element_key(
    section: str, concept: str, values: tuple[str, ...], params: tuple[tuple[str, str], ...]
) -> str:
    """The name under which an atom counts across trials (pure — pinned).

    A lab threshold counts by analyte ("inclusion:lab:platelets"), a prior agent by agent
    ("exclusion:prior_agent:PD-1"), a stage, extent or setting word by each value; anything else by its values
    together ("inclusion:ecog_ps=0|1", "inclusion:biomarker:EGFR=negative|unknown"), a PD-L1 percentage
    with its expression. The section is part of the name: requiring and excluding are different elements.
    """
    if concept in ("lab", "prior_agent", "stage", "extent", "setting_word", "resection"):
        return f"{section}:{concept}:{'|'.join(values)}"
    expression = dict(params).get("expression")
    suffix = f"@{expression}" if expression else ""
    return f"{section}:{concept}={'|'.join(values)}{suffix}"


def frequency_rows(trials: list[Trial], standard_share: float = STANDARD_SHARE) -> list[tuple]:
    """Every element's frequency in every stratum (pure — pinned).

    Rows (stratum, element, trials stating it, trials typed, frequency, surprisal in bits, distinct lead
    sponsors stating it, tier), sorted by stratum then descending count then element. The denominator is the
    stratum's typed trials; an element stated only by untyped trials is not counted. Tier is "standard" at a
    frequency of at least `standard_share`, else "". A stratum with no typed trial has no rows.
    """
    rows = []
    for stratum in sorted({t[2] for t in trials}):
        typed = [t for t in trials if t[2] == stratum and t[3]]
        if not typed:
            continue
        counts: dict[str, set[str]] = {}
        sponsors: dict[str, set[str]] = {}
        for nct, sponsor, _, _, elements, _, _ in typed:
            for element in set(elements):
                counts.setdefault(element, set()).add(nct)
                sponsors.setdefault(element, set()).add(sponsor)
        for element, stating in counts.items():
            share = len(stating) / len(typed)
            rows.append(
                (
                    stratum,
                    element,
                    len(stating),
                    len(typed),
                    round(share, 4),
                    round(-math.log2(share), 3),
                    len(sponsors[element]),
                    "standard" if share >= standard_share else "",
                )
            )
    return sorted(rows, key=lambda row: (row[0], -row[2], row[1]))


def mechanism_rows(
    trials: list[Trial], min_trials: int = SIGNAL_MIN_TRIALS, min_sponsors: int = SIGNAL_MIN_SPONSORS
) -> list[tuple]:
    """Each element's frequency within each experimental class against the rest of its stratum
    (pure — pinned).

    Over a stratum's typed trials, for each class C and element E: a = trials in C stating E, b = trials in C,
    c = trials not in C stating E, d = trials not in C; the frequencies a/b and c/d, their difference, the
    distinct lead sponsors among the a trials, and the stratum's trials whose experimental class is unresolved
    (they are in neither group's count, so they are named). Status: "proposed" when a ≥ min_trials, the
    sponsors ≥ min_sponsors and a/b > c/d; "below_support" otherwise when a/b > c/d; elements not more
    frequent in C are not listed. A class whose trials are the whole stratum has no comparison and no rows.
    """
    rows = []
    for stratum in sorted({t[2] for t in trials}):
        typed = [t for t in trials if t[2] == stratum and t[3]]
        unresolved = sum(1 for t in typed if t[6])
        known = [t for t in typed if not t[6]]
        for klass in sorted({c for t in known for c in t[5]}):
            inside = [t for t in known if klass in t[5]]
            outside = [t for t in known if klass not in t[5]]
            if not outside:
                continue
            for element in sorted({e for t in inside for e in t[4]}):
                stating = [t for t in inside if element in t[4]]
                a, b = len(stating), len(inside)
                c, d = sum(1 for t in outside if element in t[4]), len(outside)
                if a / b <= c / d:
                    continue
                sponsors = len({t[1] for t in stating})
                status = "proposed" if a >= min_trials and sponsors >= min_sponsors else "below_support"
                rows.append(
                    (
                        stratum,
                        klass,
                        element,
                        a,
                        b,
                        c,
                        d,
                        round(a / b, 4),
                        round(c / d, 4),
                        round(a / b - c / d, 4),
                        sponsors,
                        unresolved,
                        status,
                    )
                )
    return sorted(rows, key=lambda row: (row[0], row[12] != "proposed", -row[9], row[1], row[2]))


def occupancy_rows(
    cells: list[tuple[str, str]], trials: list[tuple[str, tuple[str, ...], tuple[str, ...]]]
) -> list[tuple]:
    """Each design-space cell's occupancy (pure — pinned).

    A cell is (setting, class); a trial is (nct, its setting domain, its experimental classes, empty when
    unresolved). A trial occupies a cell when its setting domain is that single setting and the class is one
    of its classes. It could fall in a cell when its setting domain holds the setting (and is not a single
    setting) or its classes are unresolved. Rows (setting, class, occupying trials, trials that could fall in
    it, state): "occupied" with any occupant, else "unknown" when some trial could fall in it, else "empty".
    """
    rows = []
    for setting, klass in cells:
        occupants = [n for n, domain, classes in trials if domain == (setting,) and klass in classes]
        possible = [
            n
            for n, domain, classes in trials
            if n not in occupants
            and setting in domain
            and (len(domain) > 1 or not classes)
            and (klass in classes or not classes)
        ]
        state = "occupied" if occupants else "unknown" if possible else "empty"
        rows.append((setting, klass, len(occupants), len(possible), state))
    return rows
