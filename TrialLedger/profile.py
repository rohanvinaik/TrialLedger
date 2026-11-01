"""The information layer: every typed element measured against a declared population of comparable trials.

Four quantities are kept apart (the founder accepted this correction, 2026-10-31): logical state (each trial's
coordinate domains), frequency, association, and relevance, which belongs to each view.

Frequency is two named estimands, never one number (openspec/changes/add-scoped-reasoning, Decision 12): the
registry statement rate, S/N, the share of the stratum's records that state the element (a point: what records
say); and, for an eligibility element only, the full-criteria frequency, the share of the stratum's trials
whose full criteria hold it, which a registry record identifies only as an interval [S/N, (S+U)/N]. S states
it; A establishes its absence by a declared ascertainment rule; U is unresolved, because the record is silent
and its silence does not establish absence: its eligibility is empty, no bank typed any of it
(no_rule_match), the record says the element's section is abbreviated, or it says nothing of its coverage (no
marker never means complete). No ascertainment rule is declared, so A is 0 by construction and every silent
trial is in U: the upper bound is 1 wherever any trial is silent. A primary endpoint is not eligibility: it
has the statement rate only. Surprisal, −log2 of the statement rate, measures how unexpected a statement is
in the stratum, not how important it is. A standard element is the empirical source of reusable protocol
language, not a verdict on its clinical value, and its tier is three-valued: met when the lower bound reaches
STANDARD_SHARE, not met when the upper bound falls short of it, unresolved otherwise.

Association is a statement-rate comparison over typed trials: an element's statement rate among trials whose
experimental drug carries a class against the rest of the stratum's typed trials, with the distinct lead
sponsors behind it, the trials whose experimental class is unresolved, and the silent trials of each group
whose record says the element's section is abbreviated. It is proposed only when it holds at the least
favourable reading of those silences, unresolved when they could reverse it; a trial whose eligibility was
never typed is in neither group. An association is offered only as a proposed relation, never as an
established one; a design-space cell is occupied, unknown (unresolved trials could fall in it) or empty, never
empty while unknown.
"""

from __future__ import annotations

import math

from TrialLedger.criteria import SCOPES

STANDARD_SHARE = 0.9
SIGNAL_MIN_TRIALS = 5
SIGNAL_MIN_SPONSORS = 3
# The sections an eligibility element's key can begin with; any other element (a primary endpoint) is not one.
ELIGIBILITY_SECTIONS = ("inclusion", "exclusion", "permitted", "unsectioned")

# One trial, as the profile reads it: (nct, lead sponsor, stratum, typed, elements, classes, class_unresolved,
# eligibility content, coverage evidence per section), the last two as `criteria.eligibility_coverage` gives
# them; typed is whether its eligibility was itemized into criteria
Trial = tuple[str, str, str, bool, list[str], list[str], bool, str, tuple[tuple[str, str], ...]]


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


def element_silence(element: str, content: str, typed: bool, coverage: tuple[tuple[str, str], ...]) -> str:
    """Why a trial that does not state an element is silent about it (pure — pinned).

    The element's sections are read from its key: "inclusion:…" the inclusion criteria, "exclusion:…" the
    exclusions, "permitted:…" and "unsectioned:…" both (either could have stated it); any other element (a
    primary endpoint) is not an eligibility element. `content` and `coverage` are the trial's, as
    `criteria.eligibility_coverage` gives them; `typed` is whether any bank typed any of its eligibility (an
    eligibility element of the trial). Codes, the first that applies:
      not_eligibility — the element is not an eligibility element: its silence is outside this account;
      empty           — the trial's eligibility text is empty;
      no_rule_match   — the trial has eligibility text but no bank typed any of it (no list markers, or no
                        criterion any bank matched): its text was never read for the element;
      abbreviated     — the record says one of the element's sections is abbreviated;
      unspecified     — otherwise: the record says nothing that establishes absence (no ascertainment rule is
                        declared, so a completeness statement alone establishes nothing either).
    Every code but not_eligibility is unresolved; none is an absence.
    """
    section = element.split(":", 1)[0]
    if section not in ELIGIBILITY_SECTIONS:
        return "not_eligibility"
    scopes = (section,) if section in SCOPES else SCOPES
    if content == "empty":
        return "empty"
    if not typed:
        return "no_rule_match"
    if any(evidence == "abbreviation_stated" for scope, evidence in coverage if scope in scopes):
        return "abbreviated"
    return "unspecified"


def full_criteria_tier(stating: int, absent: int, unresolved: int, cohort: int, threshold: float) -> str:
    """The standard tier of an element over a stratum, from its identification interval (pure — pinned).

    `stating` (S), `absent` (A) and `unresolved` (U) partition the `cohort` (N). The interval is
    [S/N, (S+U)/N], compared unrounded: "met" when the lower bound reaches `threshold`; "not_met" when the
    upper bound falls short of it; "unresolved" otherwise, and for an empty cohort.
    """
    if cohort <= 0:
        return "unresolved"
    if stating / cohort >= threshold:
        return "met"
    if (stating + unresolved) / cohort < threshold:
        return "not_met"
    return "unresolved"


def frequency_rows(trials: list[Trial], standard_share: float = STANDARD_SHARE) -> list[tuple]:
    """Every element's statement rate, and an eligibility element's full-criteria interval, in every stratum
    (pure — pinned).

    Over each stratum's trials, all of them (N), typed or not, for each element some trial states: S trials
    state it, the statement rate is S/N and its surprisal is −log2 of that rate in bits. For an eligibility
    element, of the silent trials A have its absence established (none: no ascertainment rule is declared, so
    A is 0 by construction) and U are unresolved, counted by `element_silence` as empty, no_rule_match,
    abbreviated and unspecified (a trial no bank typed is in U, never counted as lacking the element); the
    full-criteria interval is [S/N, (S+U)/N] and the tier `full_criteria_tier`'s at `standard_share`. A
    primary endpoint is not an eligibility element: its row has the statement rate only, no A, U, interval or
    tier (None, and tier ""), and says so. Rows (stratum, element, S, A, U empty, U no_rule_match,
    U abbreviated, U unspecified, U, N, statement rate, lower bound, upper bound, surprisal, distinct lead
    sponsors stating it, tier, estimand), estimand "statement rate and full-criteria interval" or "statement
    rate only (not an eligibility element)", sorted by stratum then descending S then element.
    """
    rows = []
    for stratum in sorted({t[2] for t in trials}):
        cohort = [t for t in trials if t[2] == stratum]
        counts: dict[str, set[str]] = {}
        sponsors: dict[str, set[str]] = {}
        for nct, sponsor, _, _, elements, *_ in cohort:
            for element in set(elements):
                counts.setdefault(element, set()).add(nct)
                sponsors.setdefault(element, set()).add(sponsor)
        n = len(cohort)
        for element, stating in counts.items():
            s = len(stating)
            rate, surprisal = round(s / n, 4), round(-math.log2(s / n), 3)
            if element.split(":", 1)[0] not in ELIGIBILITY_SECTIONS:
                rows.append(
                    (stratum, element, s, *[None] * 6, n, rate, None, None, surprisal)
                    + (len(sponsors[element]), "", "statement rate only (not an eligibility element)")
                )
                continue
            silence = {"empty": 0, "no_rule_match": 0, "abbreviated": 0, "unspecified": 0}
            for nct, _, _, _, elements, _, _, content, coverage in cohort:
                if nct not in stating:
                    typed = any(e.split(":", 1)[0] in ELIGIBILITY_SECTIONS for e in elements)
                    silence[element_silence(element, content, typed, coverage)] += 1
            a, u = 0, sum(silence.values())
            rows.append(
                (
                    stratum,
                    element,
                    s,
                    a,
                    silence["empty"],
                    silence["no_rule_match"],
                    silence["abbreviated"],
                    silence["unspecified"],
                    u,
                    n,
                    rate,
                    rate,
                    round((s + u) / n, 4),
                    surprisal,
                    len(sponsors[element]),
                    full_criteria_tier(s, a, u, n, standard_share),
                    "statement rate and full-criteria interval",
                )
            )
    return sorted(rows, key=lambda row: (row[0], -row[2], row[1]))


def mechanism_rows(
    trials: list[Trial], min_trials: int = SIGNAL_MIN_TRIALS, min_sponsors: int = SIGNAL_MIN_SPONSORS
) -> list[tuple]:
    """Each element's statement rate within each experimental class against the rest of its stratum, a
    statement-rate comparison bounded against abbreviated silences (pure — pinned).

    Over a stratum's typed trials (an untyped trial's text was never read, and the comparison has no place to
    hold it, so it is in neither group), for each class C and element E that some trial in C states: a =
    trials in C stating E, b = trials in C, c = trials not in C stating E, d = trials not in C; the statement
    rates a/b and c/d and their difference; the silent trials in C and outside it whose record says E's
    section is abbreviated (`element_silence`), m and n; the difference at the least favourable reading of
    those silences, a/b − (c+n)/d (every abbreviated silence outside C counted as stating E, every one inside
    as lacking it); the distinct lead sponsors among the a trials; and the stratum's typed trials whose
    experimental class is unresolved (in neither group, so they are named). Status:
      proposed       — the comparison holds at the least favourable reading (a/b > (c+n)/d), a ≥ min_trials
                       and the sponsors ≥ min_sponsors;
      below_support  — it holds at the least favourable reading without that support;
      unresolved     — it fails at the least favourable reading but holds at the most favourable one
                       ((a+m)/b > c/d): abbreviated silences could reverse it, whatever its support;
    and elements for which it fails at both are not listed. A class whose trials are the whole stratum has
    no comparison and no rows. Rows (stratum, C, E, a, b, c, d, a/b, c/d, difference, least favourable
    difference, sponsors, unresolved-class trials, m, n, status).
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
                abbreviated_in, abbreviated_out = (
                    sum(
                        1
                        for t in group
                        if element not in t[4] and element_silence(element, t[7], t[3], t[8]) == "abbreviated"
                    )
                    for group in (inside, outside)
                )
                sponsors = len({t[1] for t in stating})
                if a / b > (c + abbreviated_out) / d:
                    status = "proposed" if a >= min_trials and sponsors >= min_sponsors else "below_support"
                elif (a + abbreviated_in) / b > c / d:
                    status = "unresolved"
                else:
                    continue
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
                        round(a / b - (c + abbreviated_out) / d, 4),
                        sponsors,
                        unresolved,
                        abbreviated_in,
                        abbreviated_out,
                        status,
                    )
                )
    return sorted(rows, key=lambda row: (row[0], row[15] != "proposed", -row[9], row[1], row[2]))


def occupancy_rows(
    cells: list[tuple[str, str]], trials: list[tuple[str, tuple[str, ...], tuple[str, ...]]]
) -> list[tuple]:
    """Each design-space cell's occupancy (pure — pinned).

    A cell is (setting, class); a trial is (nct, its setting domain, its experimental classes, empty when
    unresolved). A trial occupies a cell when its setting domain is that single setting and the class is one
    of its classes. It could fall in a cell when its setting domain holds the setting (and is not a single
    setting) or its classes are unresolved. Rows (setting, class, occupying trials, trials that could fall in
    it, state): "occupied" with any occupant, else "unknown" when some trial could fall in it, else "empty".
    Eligibility coverage needs no handling here: a setting domain is narrowed only by what a record states,
    so a record's silence (empty, abbreviated or unspecified) leaves its domain wide and the trial among
    those that could fall in a cell, never out of it.
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
