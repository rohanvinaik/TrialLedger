"""design.xlsx: a population reading (`reading.read_population`) laid out as sheets, each row with its
warrant.

`write_book` writes the workbook from a reading; `write_design` is `trialledger profile` over a written
folder: the folder's record is checked against its own digests (nothing is written for a record that does not
verify), drug classes are read from NLM RxClass (cached in classes.json), the population is read once and the
workbook written beside the pull, whose own files are never touched. The cross-trial layers computed only for
the sheets (the profile, mechanism signals, occupancy, conditional rarity) are computed here. Accuracy of the
typing is for the founder to judge on the Audit sheet, never scored against labels Claude wrote.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from TrialLedger import classes as rx
from TrialLedger import warrants
from TrialLedger.banks import type_criterion
from TrialLedger.cells import cell_number_state, cell_text_state
from TrialLedger.coherence import RELATIONS, SETTINGS, accepted_value, resolve, weakest
from TrialLedger.criteria import eligibility_coverage, itemize
from TrialLedger.expectations import (
    FROZEN,
    autoimmune_exclusion,
    conditional_rarity,
    deviation_status,
)
from TrialLedger.nearmiss import near_misses
from TrialLedger.profile import (
    SIGNAL_MIN_SPONSORS,
    SIGNAL_MIN_TRIALS,
    STANDARD_SHARE,
    element_key,
    element_silence,
    frequency_rows,
    full_criteria_tier,
    mechanism_rows,
    occupancy_rows,
)
from TrialLedger.provenance import PROVENANCE
from TrialLedger.reading import (
    axes_aliases,
    axes_as_looked_up,
    axes_not_looked_up,
    class_warrant,
    drug_aliases,
    drug_axes_view,
    near_miss_input,
    read_population,
    review_coordinates,
    review_flags,
    study_view,
)
from TrialLedger.review import flags_for

DESIGN_NAME = "design.xlsx"
# design-2 (add-scoped-reasoning 1.1): the strata, expectation cells, occupancy and results read the known
# setting only, near misses known and interpolated, and every rule that reads a coordinate commits to the
# relations table (each relation's kind among its fields)
VERSION = "design-2"
AUDIT_EVERY = 25  # every 25th typed criterion goes to the Audit sheet for the founder's review
# The statuses the strata, the expectation cells and the results grouping accept (add-scoped-reasoning,
# Decision 7): known only, read through coherence.accepted_value (_stratum); a trial whose known setting is
# not one value is in "setting unresolved". Occupancy also reads the known level only, but whole: it reads the
# known domain itself, since a trial whose known setting holds several values could fall in each of their
# cells, counted apart from the occupants, never as one.
STRATA_ACCEPTS = ("known",)


class DesignError(Exception):
    """Nothing is written: the folder holds no TrialLedger record ("not_a_record"), or its record does not
    verify against its own digests ("not_verified")."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _cell(value: Any) -> Any:
    """A value a cell holds exactly, or the reason it cannot, never a cut or rounded value."""
    if isinstance(value, str):
        state = cell_text_state(value)
        return value if state == "ok" else f"({state}: see studies.json)"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value if cell_number_state(value) == "ok" else f"({cell_number_state(value)})"
    return value


def _rule(name: str, *functions: Callable[..., Any], data: tuple[str, ...] = ()) -> str:
    """A sheet rule's warrant: its name, the design version, the code of the functions that decide its rows
    and the digests of the data tables they read (`data`: the relations, whose kinds decide each coordinate's
    levels)."""
    return warrants.rule(name, VERSION, "", warrants.code_digest(*functions), *data)


def _relations_digest(relations: tuple[Any, ...]) -> str:
    """The digest of a relations table as data: every field of every relation, in order, its kind and its
    approval among them, so a relation made strict, a default or a proposal changes every warrant that reads
    a coordinate."""
    return warrants.digest("relations", warrants.canonical([dataclasses.asdict(r) for r in relations]))


def _stratum(view: dict[str, Any]) -> str:
    """A trial's setting stratum: its setting when known (stated evidence and strict relations leave one
    value: STRATA_ACCEPTS through coherence.accepted_value), else "setting unresolved". A default's conclusion
    is interpolated and a proposal's narrowing proposed: neither is built on here."""
    setting, _status = accepted_value(view["coordinates"]["setting"], STRATA_ACCEPTS)
    return setting or "setting unresolved"


def _levels(row: dict[str, Any]) -> tuple[str, str]:
    """A coordinate's interpolated domain and each proposal's narrowing, as two cells: the interpolated values
    ("(conflict)" when none), and each proposal "<relation>: <values>" on its own."""
    interpolated = " | ".join(row["interpolated"]["domain"]) or "(conflict)"
    proposals = " ⏐ ".join(
        f"{p['relation']}: {' | '.join(p['domain']) or '(conflict)'}" for p in row["proposals"]
    )
    return interpolated, proposals


def _profile_trials(views: list[dict[str, Any]], by_setting: bool) -> list[tuple]:
    """Each view as the profile reads it: every trial, with whether its eligibility was typed and its
    eligibility content and coverage, so that its silence is counted as unresolved, never as absence."""
    rows = []
    for view in views:
        classes = sorted({c for _, state, epc, _ in view["drugs"] if state == "classified" for c in epc})
        unresolved = not view["drugs"] or any(state != "classified" for _, state, _, _ in view["drugs"])
        rows.append(
            (
                view["nct"],
                view["sponsor"],
                _stratum(view) if by_setting else "all trials",
                view["itemize"] == "itemized",
                view["elements"],
                classes,
                unresolved,
                view["coverage"]["content"],
                view["coverage"]["evidence"],
            )
        )
    return rows


def _axes_rows(axes: dict[str, Any]) -> list[list[Any]]:
    """One drug's axes as rows: each name with what RxNorm says it is and its role beside the own name, each
    ATC or structure class with its standing, each own-entry target with its crosswalk row, and its ATC
    classes for the aligned reading; every row with its request and retrieval."""
    rows = []
    for name, code, rxcui, parts, role, requests, release in axes["identities"]:
        value = f"{code} {rxcui}".strip() + (f" (ingredients {', '.join(parts)})" if parts else "")
        rows.append(
            [
                "name",
                name,
                value,
                role,
                rxcui,
                release,
                " | ".join(r for r, _ in requests),
                " | ".join(t for _, t in requests),
            ]
        )
    for name, axis, class_id, class_name, kind, standing, rxcui, subject, release, request, retrieved in axes[
        "assertions"
    ]:
        value = f"{axis}: {class_id} {class_name} ({kind})"
        rows.append(["class", name, value, standing, f"{rxcui} {subject}", release, request, retrieved])
    for target, atc, atc_name, relation, member, request, read in axes["alignment"]:
        value = f"ATC {atc} {atc_name}" if atc else "(no crosswalk row)"
        rows.append(
            ["target", target, value, relation + (" (member)" if member else ""), "", "", request, read]
        )
    basis, classes = axes["atc"]
    rows.append(["aligned ATC", "", " | ".join(classes) or "(unknown)", basis or "(none)", "", "", "", ""])
    return rows


def sheets(reading: dict[str, Any], answers: dict[str, Any]) -> dict[str, tuple[list[str], list[list]]]:
    """Every sheet of design.xlsx, laid out from a population reading, as (header, rows), each row ending in
    its warrant."""
    views = reading["views"]
    digests = {v["nct"]: v["digest"] for v in views}
    # every rule that reads a coordinate commits to the relations table and to the functions that decide a
    # coordinate's levels and a trial's stratum
    relations = _relations_digest(RELATIONS)
    strata = (resolve, accepted_value, _stratum)
    trials_rule = _rule(
        "trials", study_view, *strata, type_criterion, itemize, eligibility_coverage, data=(relations,)
    )
    axes_rule = _rule(
        "drug_axes",
        rx.drug_axes,
        rx.alias_role,
        rx.own_targets,
        rx.target_alignment,
        rx.drug_atc,
        drug_axes_view,
        axes_not_looked_up,
        axes_as_looked_up,
    )
    out: dict[str, tuple[list[str], list[list]]] = {}

    out["Trials"] = (
        [
            "NCT Number",
            "Lead Sponsor",
            "Status",
            "Itemized",
            "Eligibility Content",
            "Sectioning",
            "Inclusion Coverage",
            "Exclusion Coverage",
            "Coverage Markers",
            "Criteria",
            "Typed",
            "Untyped",
            "Setting (known)",
            "Setting (interpolated: default relations added)",
            "Setting (each proposal alone)",
            "Prior Advanced Lines (known)",
            "Selections (known)",
            "Experimental Drugs",
            "Warrant",
        ],
        [
            [
                v["nct"],
                v["sponsor"],
                v["status"],
                v["itemize"],
                v["coverage"]["content"],
                v["coverage"]["sectioning"],
                dict(v["coverage"]["evidence"])["inclusion"],
                dict(v["coverage"]["evidence"])["exclusion"],
                " ⏐ ".join(
                    f"{kind} [{scope}] piece {piece}, characters {start}-{end}: {said}"
                    for kind, scope, piece, start, end, said in v["coverage"]["markers"]
                ),
                len(v["criteria"]),
                sum(1 for c in v["criteria"] if c[3]),
                sum(1 for c in v["criteria"] if not c[3]),
                " | ".join(v["coordinates"]["setting"]["domain"]) or "(conflict)",
                *_levels(v["coordinates"]["setting"]),
                " | ".join(v["coordinates"]["prior_advanced_lines"]["domain"]) or "(conflict)",
                "; ".join(
                    f"{name[10:]}: {' | '.join(row['domain']) or '(conflict)'}"
                    for name, row in v["coordinates"].items()
                    if name.startswith("selection:") and row["state"] != "unnarrowed"
                ),
                "; ".join(f"{d} [{s}{': ' + ', '.join(e) if e else ''}]" for d, s, e, _ in v["drugs"]),
                warrants.computed(trials_rule, v["digest"]),
            ]
            for v in views
        ],
    )
    criteria_rows, residual_rows, audit_rows = [], [], []
    for v in views:
        for index, section, text, atoms in v["criteria"]:
            summary = "; ".join(f"{a[1]}={'|'.join(a[2])}{dict(a[3]) or ''}" for a in atoms)
            warrant = warrants.computed(trials_rule, v["digest"], warrants.literal(f"criterion {index}"))
            row = [v["nct"], index, section, text, summary, warrant]
            criteria_rows.append(row)
            if not atoms:
                residual_rows.append([v["nct"], index, section, text, "no_bank_matched", warrant])
            elif len(criteria_rows) % AUDIT_EVERY == 0:
                audit_rows.append([v["nct"], index, section, text, summary, "", "", warrant])
    out["Criteria"] = (["NCT Number", "Piece", "Section", "Criterion", "Atoms", "Warrant"], criteria_rows)
    out["Residual"] = (["NCT Number", "Piece", "Section", "Criterion", "Reason", "Warrant"], residual_rows)
    out["Audit"] = (
        [
            "NCT Number",
            "Piece",
            "Section",
            "Criterion",
            "Atoms",
            "Founder: correct? (yes/no)",
            "Founder: note",
            "Warrant",
        ],
        audit_rows,
    )
    out["Coordinates"] = (
        [
            "NCT Number",
            "Coordinate",
            "Known Domain",
            "Known State",
            "Interpolated Domain (default relations added)",
            "Interpolated State",
            "Each Proposal Alone (never built on)",
            "Removed By (status: values by criterion or relation)",
            "Warrant",
        ],
        [
            [
                v["nct"],
                name,
                " | ".join(row["domain"]),
                row["state"],
                _levels(row)[0],
                row["interpolated"]["state"],
                _levels(row)[1],
                "; ".join(
                    [f"known: {'|'.join(removed)} by {cause}" for _, removed, cause in row["causes"]]
                    + [
                        f"interpolated: {'|'.join(removed)} by {cause}"
                        for _, removed, cause in row["interpolated"]["causes"]
                    ]
                    + [
                        f"proposed: {'|'.join(removed)} by {cause}"
                        for p in row["proposals"]
                        for _, removed, cause in p["causes"]
                    ]
                ),
                warrants.computed(trials_rule, v["digest"]),
            ]
            for v in views
            for name, row in v["coordinates"].items()
            if row["state"] != "unnarrowed"
            or row["interpolated"]["state"] != "unnarrowed"
            or row["proposals"]
        ],
    )
    out["Outcomes"] = (
        ["NCT Number", "Type", "Measure", "Time Frame", "Endpoint Classes", "Time Points", "Warrant"],
        [
            [
                v["nct"],
                kind,
                measure,
                frame,
                " | ".join(classes),
                " | ".join(points),
                warrants.computed(trials_rule, v["digest"]),
            ]
            for v in views
            for kind, measure, frame, classes, points in v["outcomes"]
        ],
    )
    result_rows = []
    for v in views:
        stratum = _stratum(v)
        for title, classes, kind, unit, param, frame, group, klass, value, spread, low, high in v["results"]:
            for endpoint in classes or ["(no endpoint class)"]:
                result_rows.append(
                    [
                        endpoint,
                        stratum,
                        unit,
                        param,
                        v["nct"],
                        kind,
                        title,
                        frame,
                        group,
                        klass,
                        value,
                        spread,
                        low,
                        high,
                        warrants.computed(trials_rule, v["digest"]),
                    ]
                )
    result_rows.sort(key=lambda row: (row[0], row[1], row[2], row[3], row[4]))
    out["Results"] = (
        [
            "Endpoint Class",
            "Setting (known)",
            "Unit",
            "Measure Type",
            "NCT Number",
            "Outcome Type",
            "Title",
            "Time Frame",
            "Arm/Group",
            "Class or Category",
            "Value",
            "Spread",
            "Lower Limit",
            "Upper Limit",
            "Warrant",
        ],
        result_rows,
    )
    rows_exp = []
    for expectation in FROZEN:
        expectation_rule = _rule(
            expectation.id,
            autoimmune_exclusion,
            eligibility_coverage,
            conditional_rarity,
            *strata,
            data=(relations,),
        )
        observations = [(_stratum(v), v["observations"][expectation.id][0]) for v in views]
        for v in views:
            status, reason, cited, qualifiers = v["observations"][expectation.id]
            source, share, n, present_bits, absent_bits = conditional_rarity(
                observations, _stratum(v), expectation.support
            )
            bits = present_bits if status == "present" else absent_bits
            known = status in ("present", "explicitly_negated", "not_documented")
            rows_exp.append(
                [
                    expectation.id,
                    v["nct"],
                    status,
                    reason,
                    " ⏐ ".join(cited),
                    " ⏐ ".join(qualifiers),
                    _stratum(v),
                    source,
                    share,
                    n,
                    bits if known else None,
                    deviation_status(status, len(qualifiers), ""),
                    warrants.computed(expectation_rule, v["digest"]),
                ]
            )
    out["Expectations"] = (
        [
            "Expectation",
            "NCT Number",
            "Observation",
            "Reason",
            "Criteria Cited",
            "Qualifiers",
            "Cell (setting, known)",
            "Rarity Source",
            "Share Present in Cell",
            "Known in Cell",
            "Rarity of This Observation (bits)",
            "Deviation",
            "Warrant",
        ],
        rows_exp,
    )
    review_rule = _rule(
        "review",
        flags_for,
        eligibility_coverage,
        review_flags,
        review_coordinates,
        resolve,
        data=(relations,),
    )
    review_rows = []
    for v, flags in zip(views, reading["flags"], strict=True):
        for kind, element, why, priority, evidence, question, options in flags:
            review_rows.append(
                [
                    priority,
                    kind,
                    v["nct"],
                    element,
                    why,
                    " ⏐ ".join(evidence),
                    question,
                    " | ".join(options),
                    "",
                    "",
                    warrants.computed(review_rule, v["digest"]),
                ]
            )
    review_rows.sort(key=lambda row: (row[0], row[1], row[2]))
    out["Review Queue"] = (
        [
            "Priority",
            "Kind",
            "NCT Number",
            "Element",
            "Why Unresolved",
            "Evidence",
            "Question",
            "Answer Options",
            "Answer",
            "Answered By (expert or model)",
            "Warrant",
        ],
        review_rows,
    )
    comparable = [
        status
        for t, status in zip(reading["near_miss_trials"], reading["near_miss_status"], strict=True)
        if all(t[1].values())
    ]
    near_miss_rule = _rule(
        "near_miss", near_misses, near_miss_input, accepted_value, weakest, resolve, data=(relations,)
    )
    out["Near Misses"] = (
        [
            "NCT A",
            "NCT B",
            "The One Difference",
            "Value in A",
            "Value in B",
            "Sponsor A",
            "Sponsor B",
            "Start Year A",
            "Start Year B",
            "Predicates Agreeing",
            f"Representation (known for {comparable.count('known')} and interpolated for "
            f"{comparable.count('interpolated')} of {len(views)} trials; an unknown never matches)",
            "Rests On (the weakest status of the two settings: known or interpolated)",
            "Warrant",
        ],
        [
            [
                *pair,
                PROVENANCE["representation:near_miss"][2],
                status,
                warrants.computed(near_miss_rule, digests[pair[0]], digests[pair[1]]),
            ]
            for pair, status in zip(reading["pairs"], reading["pair_status"], strict=True)
        ],
    )
    out["Drug Axes"] = (
        [
            "NCT Number",
            "Drug",
            "Identity (own name)",
            "Reason",
            "Row",
            "Name or Target",
            "Value",
            "Standing, Role or Relation",
            "Asserted Of (RxNorm)",
            "RxNav Release",
            "Request",
            "Retrieved",
            "Warrant",
        ],
        [
            [
                v["nct"],
                axes["drug"],
                axes["identity"],
                axes["reason"],
                *row,
                warrants.computed(axes_rule, v["digest"]),
            ]
            for v in views
            for axes in v["drug_axes"]
            for row in _axes_rows(axes)
        ],
    )
    out["Rules"] = (
        ["Rule", "Kind", "Origin", "Source or Note", "Warrant"],
        [
            [key, kind, origin, note, warrants.literal(key)]
            for key, (kind, origin, note) in PROVENANCE.items()
        ],
    )
    out["Relations"] = (
        [
            "Relation",
            "Statement",
            "Basis",
            "Kind (strict: known; default: interpolated; proposal: shown alone, never built on)",
            "Approval",
            "Narrows",
            "To",
            "Warrant",
        ],
        [
            [
                r.id,
                r.statement,
                r.basis,
                r.kind,
                r.approval,
                r.narrows,
                " | ".join(r.allowed),
                _rule(r.id, resolve, data=(_relations_digest((r,)),)),
            ]
            for r in RELATIONS
        ],
    )
    classes_rows = []
    for name, answer in sorted(answers.items()):
        state, release, requests = class_warrant(answer)
        asked = " | ".join(f"{request} at {retrieved}" for request, retrieved in requests)
        held = release if state == "found" else f"({state})"
        for klass in answer["classes"] or [("", "", "", "")]:
            # the warrant commits to the row's answer: the class, and the requests and release it rests on
            warrant = warrants.literal(json.dumps([name, klass, state, release, requests]))
            classes_rows.append(
                [name, json.dumps(answer["codes"], sort_keys=True), *klass, asked, held, warrant]
            )
    out["Classes"] = (
        [
            "Name Asked",
            "Codes",
            "Class Id",
            "Class",
            "Relation",
            "Source",
            "Requests (each with its retrieval time)",
            "RxNav Release (not_recorded: cached before answers carried it)",
            "Warrant",
        ],
        classes_rows,
    )
    profile_rule = _rule(
        "profile",
        frequency_rows,
        element_key,
        element_silence,
        full_criteria_tier,
        eligibility_coverage,
        *strata,
        data=(relations,),
    )
    mechanism_rule = _rule(
        "mechanism", mechanism_rows, element_silence, eligibility_coverage, *strata, data=(relations,)
    )
    frequency, mechanism = [], []
    for by_setting in (False, True):
        trials = _profile_trials(views, by_setting)
        root = warrants.merkle_root([digests[t[0]] for t in trials])
        frequency += [[*row, warrants.computed(profile_rule, root)] for row in frequency_rows(trials)]
        mechanism += [[*row, warrants.computed(mechanism_rule, root)] for row in mechanism_rows(trials)]
    out["Profile"] = (
        [
            "Stratum",
            "Element",
            "Trials Stating (S)",
            "Absence Established (A): no ascertainment rule is declared, so 0 by construction",
            "Unresolved: Empty Eligibility",
            "Unresolved: No Rule Match (eligibility never typed)",
            "Unresolved: Abbreviated",
            "Unresolved: Unspecified",
            "Unresolved (U)",
            "Trials (N)",
            "Registry Statement Rate (S/N)",
            "Full-Criteria Lower Bound (S/N)",
            "Full-Criteria Upper Bound ((S+U)/N)",
            "Surprisal of the Statement Rate (bits)",
            "Sponsors",
            f'Standard Tier (≥ {STANDARD_SHARE:.0%}: met, not_met, unresolved; "" for a primary endpoint)',
            "Estimand",
            "Warrant",
        ],
        frequency,
    )
    out["Mechanism Signals"] = (
        [
            "Stratum",
            "Class (FDA EPC)",
            "Element",
            "In Class Stating",
            "In Class",
            "Others Stating",
            "Others",
            "Statement Rate in Class",
            "Statement Rate in Others",
            "Difference of Statement Rates",
            "Difference, Abbreviated Silences Least Favourable (others' counted as stating)",
            "Sponsors Stating",
            "Trials with Unresolved Class",
            "Silent in Class, Abbreviated",
            "Silent in Others, Abbreviated",
            "Status of the statement-rate comparison (proposed: holds with abbreviated silences read least "
            f"favourably, ≥{SIGNAL_MIN_TRIALS} trials, ≥{SIGNAL_MIN_SPONSORS} sponsors; below_support: holds "
            "so, less support; unresolved: abbreviated silences could reverse it)",
            "Warrant",
        ],
        mechanism,
    )
    occupancy_trials = [
        (
            v["nct"],
            v["coordinates"]["setting"]["domain"],
            tuple(sorted({c for _, s, e, _ in v["drugs"] if s == "classified" for c in e}))
            if v["drugs"] and all(s == "classified" for _, s, _, _ in v["drugs"])
            else (),
        )
        for v in views
    ]
    observed = sorted({c for _, _, classes in occupancy_trials for c in classes})
    cells = [(setting, klass) for setting in SETTINGS for klass in observed]
    root = warrants.merkle_root([v["digest"] for v in views])
    occupancy_rule = _rule("occupancy", occupancy_rows, resolve, data=(relations,))
    out["Occupancy"] = (
        [
            "Setting (known)",
            "Class (FDA EPC)",
            "Occupying Trials",
            "Trials That Could Fall Here",
            "State",
            "Warrant",
        ],
        [[*row, warrants.computed(occupancy_rule, root)] for row in occupancy_rows(cells, occupancy_trials)],
    )
    return out


ABOUT = [
    [
        "Review Queue",
        "What this symbolic reading could not cleanly resolve, each as a typed question with closed answer "
        "options and its evidence, for a domain expert or a model to answer: unresolved drug classes, "
        "coordinate conflicts, unresolved expectation observations, verified deviations and records that "
        "say their eligibility criteria are abbreviated. Nothing in it "
        "is resolved by TrialLedger; an answer is recorded with who gave it.",
    ],
    [
        "Outcomes / Results",
        "Every registered outcome with its endpoint classes and stated time points. Results: every posted "
        "measurement, grouped by endpoint class, setting, unit and measure type; only rows that share all "
        "four are comparable, and nothing is pooled or converted.",
    ],
    [
        "What this workbook is",
        "The coherence engine over the pull beside it: every criterion itemized and typed by "
        "deterministic rules, each trial's design coordinates resolved, and every typed element measured "
        "against "
        "this pull's population. No model read any trial.",
    ],
    [
        "Trials",
        "One row per study: how its eligibility was itemized and typed; what the text says about itself, "
        "kept apart (content empty or present; sectioned or not; for the inclusion and the exclusion "
        "criteria, whether the record says its list is abbreviated, says it is complete, or says nothing, "
        "each marker with its place and scope; no marker never means complete); its setting known, "
        "interpolated and as each proposal alone would narrow it (see Coordinates), and its "
        "experimental drugs with their RxClass state and FDA Established Pharmacologic Class.",
    ],
    [
        "Criteria / Residual",
        "Every criterion with the atoms typed from it; the Residual sheet lists every criterion "
        "no rule typed. Untyped is not absent: no count treats it as lacking anything.",
    ],
    ["Audit", "A sample of typed criteria for the founder's review. Typing accuracy is judged here, by him."],
    [
        "Coordinates",
        "Domains of still-possible values, at three statuses kept apart. Known: the record's own criteria "
        "and the strict relations (none yet, so the setting is rarely known). Interpolated: the default "
        "relations added, assumed until overruled. Each proposal alone: what one proposed relation would "
        "narrow the interpolated domain to, shown and never built on. Strata, expectation cells, occupancy "
        "and results read the known domain only; near misses read known and interpolated, each pair "
        "labelled. Conflict means the record's own criteria, or the relations, exclude every value; each "
        "cause is named with its status.",
    ],
    [
        "Relations",
        "Every relation, its basis, its kind and its approval, kept apart: a strict relation's conclusion is "
        "known, a default's interpolated, a proposal's shown alone and never built on. The four approved on "
        "2026-10-31 are defaults (each excludes a qualifying design); none is strict yet.",
    ],
    [
        "Classes",
        "Every RxClass answer, with class ids and sources; not_found, malformed and lookup_failed are "
        "named, never read as 'no class'. Each answer's requests, with their retrieval times, and the RxNav "
        "release it was read under; an answer cached before answers carried them says not_recorded.",
    ],
    [
        "Profile",
        "Each element over every trial of the stratum (N), as two estimands kept apart: the registry "
        "statement rate (S/N, the share of records that state it, a point) and, for an eligibility element,"
        " the full-criteria frequency, which records identify only as an interval from S/N to (S+U)/N, "
        "where U counts the silent trials whose silence does not establish absence, each kind named (empty "
        "eligibility; eligibility no rule typed; a record that says its list is abbreviated; one that says "
        "nothing of its coverage). No ascertainment rule is declared, so A is 0 by construction and the "
        "upper bound is 1 wherever a trial is silent. A primary endpoint is not eligibility: its row gives "
        "the statement rate only, and says so. The surprisal of the statement rate (how unexpected, not how"
        " important), the sponsors, and the standard tier (the empirical source of reusable protocol "
        "language, not a verdict on clinical value): met when the lower bound reaches it, not_met when the "
        "upper bound falls short, unresolved otherwise. Strata by setting use the known setting only (a "
        "trial whose known setting is not one value is in 'setting unresolved'); interpolated and proposed "
        "settings are never built on here.",
    ],
    [
        "Mechanism Signals",
        "A statement-rate comparison: elements stated more often by the typed trials of one drug class than "
        "by the rest of the stratum's typed trials (a trial whose text was never typed is in neither group). "
        "A record that says its list is abbreviated may hold an element it does not state, so the comparison "
        "is bounded: proposed only when it still holds with every such silence among the others counted as "
        "stating and every one in the class as lacking (the least favourable reading), unresolved when those "
        "silences could reverse it. Every row is a proposal for review, never an established mechanism link; "
        "sponsor templates and eras can produce the same pattern, so sponsors and unresolved-class trials "
        "are shown.",
    ],
    [
        "Occupancy",
        "Each setting and drug class: occupied, unknown (unresolved trials could fall here) or empty. "
        "A trial occupies a cell only by its known setting; one whose known setting holds several values "
        "could fall in each, counted apart. An empty cell is a lead for exploration, not proof of unmet "
        "need.",
    ],
    [
        "Expectations",
        "Each frozen expectation observed in every trial: present, explicitly negated, not documented, "
        "unresolved or not applicable, with the criteria cited, how rare the observation is in its cell, and "
        "its deviation status. An omission is never read as permission.",
    ],
    [
        "Near Misses",
        "Pairs of trials whose representation (one setting, known or interpolated; every experimental "
        "drug's class) is equal and that differ in exactly one predicate known for both. The header gives "
        "how many trials the representation is known and interpolated for; each pair says the weakest status "
        "it rests on. Shared sponsors and eras confound; an outcome difference between a pair is an "
        "association to investigate.",
    ],
    [
        "Drug Axes",
        "Each experimental drug's axes beside its FDA class, never merged with it: what RxNorm says its "
        "own name is (another name may confirm that concept, never supply one; an unresolved own name "
        "gives its reason), each ATC and chemical-structure class RxClass asserted with its standing "
        "(known only when asserted of the own name's concept: a brand or a salt does not inherit its "
        "ingredient's class), each target its own entry states with its crosswalk row (membership only "
        "where the relation entails it; a word naming another drug is no target), and its ATC classes for"
        " the aligned near-miss reading with their basis. Every row gives its RxNav request, retrieval "
        "time and release. The modality and cell extractions, the intervention MeSH, the aligned pairs "
        "and the structure relations are in the resolve JSON.",
    ],
    [
        "Rules",
        "Every bank, relation, expectation, representation and threshold, with where it came from: "
        "external (a cited source), prior (domain knowledge declared before measuring) or derived (written "
        "while reading a named population, which therefore cannot confirm it).",
    ],
    [
        "Warrant",
        "Each row's hash over the rule that derived it (the code that decides its rows, and the relations "
        "table, each relation's kind among its fields, wherever a coordinate is read) and the studies it "
        "rests on.",
    ],
]


def write_book(target: Path, reading: dict[str, Any], answers: dict[str, Any]) -> dict[str, int]:
    """Write design.xlsx at `target` from a population reading and the RxClass `answers`; the sheets'
    sizes."""
    book = Workbook()
    about = book.active
    about.title = "About"
    for row in ABOUT:
        about.append(row)
    sizes = {}
    for name, (header, rows) in sheets(reading, answers).items():
        sheet = book.create_sheet(name)
        sheet.append(header)
        for row in rows:
            sheet.append([_cell(value) for value in row])
        sizes[name] = len(rows)
    book.save(target)
    return sizes


def write_design(folder: Path, *, get=rx.http_get, sleep=None) -> tuple[Path, dict[str, int]]:
    """Write design.xlsx (and classes.json) into a TrialLedger folder; return the path and sheet sizes."""
    from TrialLedger.record import record_problems

    path = folder / "studies.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        studies = record["studies"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise DesignError("not_a_record", f"{path}: not a TrialLedger record ({error})") from error
    csv_path = folder / "studies.csv"
    problems = record_problems(record, csv_path.read_bytes() if csv_path.is_file() else None)
    if problems:
        raise DesignError("not_verified", "the record does not verify: " + "; ".join(problems[:5]))
    kwargs = {"get": get} if sleep is None else {"get": get, "sleep": sleep}
    answers = rx.load_or_lookup(folder, drug_aliases(studies), axes_aliases(studies), **kwargs)
    target = folder / DESIGN_NAME
    return target, write_book(target, read_population(studies, answers), answers)
