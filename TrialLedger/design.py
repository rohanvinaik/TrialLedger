"""`trialledger profile`: the coherence engine over a written folder, written to design.xlsx beside the pull.

The shell composes the layers: the folder's record is checked against its own digests (nothing is written for
a record that does not verify); each study's eligibility is itemized and typed; each trial's coordinates are
resolved; drug classes are read from NLM RxClass (cached in classes.json); the profile is computed over the
folder's population; and every sheet is written with each row's warrant. The pull's own files are never
touched. Accuracy of the typing is for the founder to judge on the Audit sheet, never scored against labels
Claude wrote.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from TrialLedger import classes as rx
from TrialLedger import warrants
from TrialLedger.banks import endpoint_classes, stated_targets, time_points, type_criterion
from TrialLedger.cells import cell_number_state, cell_text_state
from TrialLedger.coherence import RELATIONS, SETTINGS, resolve
from TrialLedger.criteria import itemize
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
    frequency_rows,
    mechanism_rows,
    occupancy_rows,
)
from TrialLedger.provenance import PROVENANCE
from TrialLedger.review import flags_for

DESIGN_NAME = "design.xlsx"
VERSION = "design-1"
AUDIT_EVERY = 25  # every 25th typed criterion goes to the Audit sheet for the founder's review


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


def _rule(name: str, *functions: Callable[..., Any]) -> str:
    return warrants.rule(name, VERSION, "", warrants.code_digest(*functions))


def study_view(study: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    """One study as the design layers read it: criteria with atoms, evidence, coordinates, elements,
    classes."""
    protocol = study.get("protocolSection", {})
    nct = protocol.get("identificationModule", {}).get("nctId", "")
    text = protocol.get("eligibilityModule", {}).get("eligibilityCriteria") or ""
    code, pieces = itemize(text if isinstance(text, str) else "")
    readable = [(section, text[start:end]) for _kind, section, start, end in pieces]
    criteria, evidence, elements = [], [], []
    for index, (kind, section, start, end) in enumerate(pieces):
        if kind != "criterion":
            continue
        atoms = type_criterion(text[start:end])
        criteria.append((index, section, text[start:end], atoms))
        for _bank, concept, values, params, _s, _e in atoms:
            flipped = dict(params).get("text_polarity") == "excluded" and section == "inclusion"
            effective = "exclusion" if flipped else section
            evidence.append((effective, concept, values, dict(params).get("scope", ""), f"criterion {index}"))
            elements.append(element_key(effective, concept, values, params))
    names = rx.drug_names(study)
    arms_module = protocol.get("armsInterventionsModule", {})
    descriptions = {
        item.get("name"): " ".join(str(item.get(k) or "") for k in ("name", "description"))
        for item in arms_module.get("interventions", []) or []
        if isinstance(item, dict)
    }
    # An arm's description names its whole combination ("SCT-I10A plus docetaxel"), so an agent word in it
    # cannot be attributed to one drug: only the intervention's own entry is read.
    drugs = []
    for drug in rx.experimental_drugs(study):
        state, found, resolved_by = rx.drug_class(answers, names[drug])
        epc = sorted({c[1] for c in found if c[2] == "has_epc"})
        if state != "classified":
            stated = stated_targets(descriptions.get(drug, ""))
            if stated:
                state, epc, resolved_by = "stated_by_record", [f"stated: {s}" for s in stated], "description"
        drugs.append((drug, state, epc, resolved_by))
    outcomes = []
    for kind, key in (
        ("primary", "primaryOutcomes"),
        ("secondary", "secondaryOutcomes"),
        ("other", "otherOutcomes"),
    ):
        for outcome in protocol.get("outcomesModule", {}).get(key, []) or []:
            measure, frame = str(outcome.get("measure") or ""), str(outcome.get("timeFrame") or "")
            classes = endpoint_classes(measure)
            outcomes.append((kind, measure, frame, classes, time_points(frame)))
            if kind == "primary":
                elements.extend(f"primary:endpoint:{c}" for c in classes)
    results = []
    for measure in (study.get("resultsSection", {}).get("outcomeMeasuresModule", {}) or {}).get(
        "outcomeMeasures", []
    ) or []:
        groups = {g.get("id"): g.get("title") for g in measure.get("groups", []) or [] if isinstance(g, dict)}
        title = str(measure.get("title") or "")
        for klass in measure.get("classes", []) or []:
            for category in klass.get("categories", []) or []:
                for m in category.get("measurements", []) or []:
                    results.append(
                        (
                            title,
                            endpoint_classes(title),
                            str(measure.get("type") or ""),
                            str(measure.get("unitOfMeasure") or ""),
                            str(measure.get("paramType") or ""),
                            str(measure.get("timeFrame") or ""),
                            str(groups.get(m.get("groupId"), "")),
                            str(klass.get("title") or category.get("title") or ""),
                            str(m.get("value") or ""),
                            str(m.get("spread") or ""),
                            str(m.get("lowerLimit") or ""),
                            str(m.get("upperLimit") or ""),
                        )
                    )
    return {
        "nct": nct,
        "digest": warrants.study_digest(study),
        "sponsor": protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
        "start_year": str(protocol.get("statusModule", {}).get("startDateStruct", {}).get("date", ""))[:4],
        "status": protocol.get("statusModule", {}).get("overallStatus", ""),
        "itemize": code,
        "criteria": criteria,
        "coordinates": resolve(evidence),
        "elements": elements,
        "drugs": drugs,
        "outcomes": outcomes,
        "results": results,
        "observations": {
            expectation.id: _observe(expectation, readable, code, drugs) for expectation in FROZEN
        },
    }


def near_miss_input(view: dict[str, Any]) -> tuple[str, dict[str, str], dict[str, str], str, str]:
    """A study view as the near-miss decision reads it: its representation (setting when one value; its
    experimental drugs' classes when every one is classified), its design predicates (the ECOG values and
    histologies its inclusion criteria state, the checkpoint expectation when present or admitted), its lead
    sponsor and its start year. Anything not known is ""."""
    setting = view["coordinates"]["setting"]["with_proposed"]
    drugs = view["drugs"]
    classified = drugs and all(state == "classified" for _, state, _, _ in drugs)
    classes = " + ".join(sorted({c for _, _, epc, _ in drugs for c in epc})) if classified else ""
    ecog, histologies = "", set()
    for _index, section, _text, atoms in view["criteria"]:
        for _bank, concept, values, _params, _s, _e in atoms:
            if section == "inclusion" and concept == "ecog_ps" and not ecog:
                ecog = "|".join(values)
            if section == "inclusion" and concept == "histology":
                histologies |= set(values)
    status = next(iter(view["observations"].values()), ("", "", [], []))[0]
    return (
        view["nct"],
        {"setting": setting[0] if len(setting) == 1 else "", "classes": classes},
        {
            "ecog_ps": ecog,
            "histology": "|".join(sorted(histologies)),
            "autoimmune_exclusion": status if status in ("present", "explicitly_negated") else "",
        },
        view["sponsor"],
        view["start_year"],
    )


def review_flags(view: dict[str, Any], known_classes: list[str]) -> list[tuple]:
    """The review flags of one study view: what the symbolic reading leaves for an expert or a model."""
    from TrialLedger.coherence import COORDINATES

    return flags_for(
        [(drug, state) for drug, state, _, _ in view["drugs"]],
        {
            name: (list(row["domain"]), row["state"], [c[2] for c in row["causes"]])
            for name, row in view["coordinates"].items()
        },
        {name: list(values) for name, values in COORDINATES.items()},
        {eid: (s, r, c) for eid, (s, r, c, _) in view["observations"].items()},
        known_classes,
    )


def _observe(expectation, readable, code, drugs) -> tuple[str, str, list[str], list[str]]:
    """One trial's observation of a frozen expectation: (status, reason, cited texts, qualifiers)."""
    classes = {c for _, state, epc, _ in drugs if state in ("classified", "stated_by_record") for c in epc}
    if not classes & set(expectation.applies_to):
        return "not_applicable", "no experimental drug of the expectation's classes", [], []
    if code == "empty":
        return "unresolved", "no eligibility text", [], []
    status, reason, indices, qualifiers = autoimmune_exclusion(readable)
    return status, reason, [readable[i][1] for i in indices], qualifiers


def _stratum(view: dict[str, Any]) -> str:
    setting = view["coordinates"]["setting"]["with_proposed"]
    return setting[0] if len(setting) == 1 else "setting unresolved"


def _profile_trials(views: list[dict[str, Any]], by_setting: bool) -> list[tuple]:
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
            )
        )
    return rows


def sheets(views: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, tuple[list[str], list[list]]]:
    """Every sheet of design.xlsx as (header, rows), each row ending in its warrant."""
    digests = {v["nct"]: v["digest"] for v in views}
    trials_rule = _rule("trials", study_view, resolve, type_criterion, itemize)
    out: dict[str, tuple[list[str], list[list]]] = {}

    out["Trials"] = (
        [
            "NCT Number",
            "Lead Sponsor",
            "Status",
            "Itemized",
            "Criteria",
            "Typed",
            "Untyped",
            "Setting",
            "Setting with Proposed Relations",
            "Prior Advanced Lines",
            "Selections",
            "Experimental Drugs",
            "Warrant",
        ],
        [
            [
                v["nct"],
                v["sponsor"],
                v["status"],
                v["itemize"],
                len(v["criteria"]),
                sum(1 for c in v["criteria"] if c[3]),
                sum(1 for c in v["criteria"] if not c[3]),
                " | ".join(v["coordinates"]["setting"]["domain"]),
                " | ".join(v["coordinates"]["setting"]["with_proposed"]) or "(conflict)",
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
            "Domain",
            "State",
            "With Proposed Relations",
            "State with Proposed",
            "Removed By",
            "Warrant",
        ],
        [
            [
                v["nct"],
                name,
                " | ".join(row["domain"]),
                row["state"],
                " | ".join(row["with_proposed"]),
                row["proposed_state"],
                "; ".join(
                    f"{'|'.join(removed)} by {cause}"
                    for _, removed, cause in row["causes"] + row["proposed_causes"]
                ),
                warrants.computed(trials_rule, v["digest"]),
            ]
            for v in views
            for name, row in v["coordinates"].items()
            if row["state"] != "unnarrowed" or row["proposed_state"] != "unnarrowed"
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
            "Setting (with proposed relations)",
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
                    warrants.computed(
                        _rule(expectation.id, autoimmune_exclusion, conditional_rarity), v["digest"]
                    ),
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
            "Cell (setting, with proposed relations)",
            "Rarity Source",
            "Share Present in Cell",
            "Known in Cell",
            "Rarity of This Observation (bits)",
            "Deviation",
            "Warrant",
        ],
        rows_exp,
    )
    known_classes = sorted({c for v in views for _, s, e, _ in v["drugs"] if s == "classified" for c in e})
    review_rows = []
    for v in views:
        for kind, element, why, priority, evidence, question, options in review_flags(v, known_classes):
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
                    warrants.computed(_rule("review", flags_for), v["digest"]),
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
    nm_trials = [near_miss_input(v) for v in views]
    digests = {v["nct"]: v["digest"] for v in views}
    comparable = sum(all(t[1].values()) for t in nm_trials)
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
            f"Representation (known for {comparable} of {len(views)} trials; an unknown never matches)",
            "Warrant",
        ],
        [
            [
                *pair,
                "setting (one value) and experimental drug classes (all classified)",
                warrants.computed(_rule("near_miss", near_misses), digests[pair[0]], digests[pair[1]]),
            ]
            for pair in near_misses(nm_trials)
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
        ["Relation", "Statement", "Basis", "Approval", "Narrows", "To", "Warrant"],
        [
            [r.id, r.statement, r.basis, r.approval, r.narrows, " | ".join(r.allowed), _rule(r.id, resolve)]
            for r in RELATIONS
        ],
    )
    out["Classes"] = (
        ["Name Asked", "Codes", "Class Id", "Class", "Relation", "Source", "Warrant"],
        [
            [
                name,
                json.dumps(answer["codes"], sort_keys=True),
                *klass,
                warrants.literal(json.dumps([name, klass])),
            ]
            for name, answer in sorted(answers.items())
            for klass in (answer["classes"] or [("", "", "", "")])
        ],
    )
    profile_rule = _rule("profile", frequency_rows, element_key)
    frequency, mechanism = [], []
    for by_setting in (False, True):
        trials = _profile_trials(views, by_setting)
        root = warrants.merkle_root([digests[t[0]] for t in trials])
        frequency += [[*row, warrants.computed(profile_rule, root)] for row in frequency_rows(trials)]
        mechanism += [
            [*row, warrants.computed(_rule("mechanism", mechanism_rows), root)]
            for row in mechanism_rows(trials)
        ]
    out["Profile"] = (
        [
            "Stratum",
            "Element",
            "Trials Stating",
            "Trials Typed",
            "Frequency",
            "Surprisal (bits)",
            "Sponsors",
            f"Tier (standard ≥ {STANDARD_SHARE:.0%})",
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
            "Frequency in Class",
            "Frequency in Others",
            "Difference",
            "Sponsors Stating",
            "Trials with Unresolved Class",
            f"Status (proposed: ≥{SIGNAL_MIN_TRIALS} trials, ≥{SIGNAL_MIN_SPONSORS} sponsors)",
            "Warrant",
        ],
        mechanism,
    )
    occupancy_trials = [
        (
            v["nct"],
            v["coordinates"]["setting"]["with_proposed"],
            tuple(sorted({c for _, s, e, _ in v["drugs"] if s == "classified" for c in e}))
            if v["drugs"] and all(s == "classified" for _, s, _, _ in v["drugs"])
            else (),
        )
        for v in views
    ]
    observed = sorted({c for _, _, classes in occupancy_trials for c in classes})
    cells = [(setting, klass) for setting in SETTINGS for klass in observed]
    root = warrants.merkle_root([v["digest"] for v in views])
    out["Occupancy"] = (
        [
            "Setting (with proposed relations)",
            "Class (FDA EPC)",
            "Occupying Trials",
            "Trials That Could Fall Here",
            "State",
            "Warrant",
        ],
        [
            [*row, warrants.computed(_rule("occupancy", occupancy_rows), root)]
            for row in occupancy_rows(cells, occupancy_trials)
        ],
    )
    return out


ABOUT = [
    [
        "Review Queue",
        "What this symbolic reading could not cleanly resolve, each as a typed question with closed answer "
        "options and its evidence, for a domain expert or a model to answer: unresolved drug classes, "
        "coordinate conflicts, unresolved expectation observations and verified deviations. Nothing in it "
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
        "One row per study: how its eligibility was itemized and typed, its coordinates, and its "
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
        "Domains of still-possible values. 'Domain' uses approved relations only (none is approved "
        "yet); 'With Proposed Relations' shows what the proposed relations would add. Conflict means the "
        "record's "
        "own criteria, or the relations, exclude every value; each cause is named.",
    ],
    [
        "Relations",
        "Every relation, its basis and approval. All are proposed until the founder approves them by id.",
    ],
    [
        "Classes",
        "Every RxClass answer, with class ids and sources; not_found, malformed and lookup_failed are "
        "named, never read as 'no class'.",
    ],
    [
        "Profile",
        "Each element's frequency over the trials whose text was typed, its surprisal (how unexpected, "
        "not how important), its sponsors, and the standard tier (the empirical source of reusable protocol "
        "language, not a verdict on clinical value). Strata by setting rest on the proposed relations.",
    ],
    [
        "Mechanism Signals",
        "Elements more frequent among trials of one drug class than among the rest of the "
        "stratum. Every row is a proposal for review, never an established mechanism link; sponsor "
        "templates and "
        "eras can produce the same pattern, so sponsors and unresolved-class trials are shown.",
    ],
    [
        "Occupancy",
        "Each setting and drug class: occupied, unknown (unresolved trials could fall here) or empty. "
        "An empty cell is a lead for exploration, not proof of unmet need.",
    ],
    ["Warrant", "Each row's hash over the rule that derived it and the studies it rests on."],
]


def write_book(target: Path, studies: list[dict[str, Any]], answers: dict[str, Any]) -> dict[str, int]:
    """Analyse `studies` with the RxClass `answers` and write design.xlsx at `target`; the sheets' sizes."""
    views = [study_view(study, answers) for study in studies]
    book = Workbook()
    about = book.active
    about.title = "About"
    for row in ABOUT:
        about.append(row)
    sizes = {}
    for name, (header, rows) in sheets(views, answers).items():
        sheet = book.create_sheet(name)
        sheet.append(header)
        for row in rows:
            sheet.append([_cell(value) for value in row])
        sizes[name] = len(rows)
    book.save(target)
    return sizes


def drug_aliases(studies: list[dict[str, Any]]) -> list[str]:
    """Every drug or biological name and other name of the studies, for RxClass."""
    return [alias for study in studies for aliases in rx.drug_names(study).values() for alias in aliases]


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
    answers = rx.load_or_lookup(folder, drug_aliases(studies), **kwargs)
    target = folder / DESIGN_NAME
    return target, write_book(target, studies, answers)


def symbolic_output(studies: list[dict[str, Any]], answers: dict[str, Any]) -> list[dict[str, Any]]:
    """Each study's symbolic reading as plain data: typed criteria, coordinates, drugs, outcomes, near misses
    and expectation observations, each value with the record text it rests on. The JSON form of `resolve`."""
    views = [study_view(study, answers) for study in studies]
    known_classes = sorted({c for v in views for _, s, e, _ in v["drugs"] if s == "classified" for c in e})
    pairs = near_misses([near_miss_input(v) for v in views])
    output = []
    for view in views:
        output.append(
            {
                "nct": view["nct"],
                "digest": view["digest"],
                "lead_sponsor": view["sponsor"],
                "status": view["status"],
                "itemized": view["itemize"],
                "criteria": [
                    {
                        "piece": index,
                        "section": section,
                        "text": text,
                        "atoms": [
                            {
                                "bank": a[0],
                                "concept": a[1],
                                "values": list(a[2]),
                                "params": dict(a[3]),
                                "span": text[a[4] : a[5]],
                            }
                            for a in atoms
                        ],
                    }
                    for index, section, text, atoms in view["criteria"]
                ],
                "coordinates": {
                    name: {
                        "domain": list(row["domain"]),
                        "state": row["state"],
                        "with_proposed_relations": list(row["with_proposed"]),
                        "removed_by": [
                            [c[0], list(c[1]), c[2]] for c in row["causes"] + row["proposed_causes"]
                        ],
                    }
                    for name, row in view["coordinates"].items()
                },
                "experimental_drugs": [
                    {"name": d, "state": s, "classes": e, "resolved_by": r} for d, s, e, r in view["drugs"]
                ],
                "outcomes": [
                    {"type": k, "measure": m, "time_frame": f, "endpoint_classes": c, "time_points": p}
                    for k, m, f, c, p in view["outcomes"]
                ],
                "review": [
                    {
                        "kind": k,
                        "element": el,
                        "why": why,
                        "priority": int(pr),
                        "evidence": ev,
                        "question": q,
                        "options": opts,
                        "answer": None,
                    }
                    for k, el, why, pr, ev, q, opts in review_flags(view, known_classes)
                ],
                "near_misses": [
                    {
                        "other": p[1 - side],
                        "difference": p[2],
                        "value": p[3 + side],
                        "other_value": p[4 - side],
                        "other_sponsor": p[6 - side],
                        "other_start_year": p[8 - side],
                        "predicates_agreeing": p[9],
                    }
                    for p in pairs
                    for side in (0, 1)
                    if p[side] == view["nct"]
                ],
                "expectations": {
                    eid: {
                        "status": s,
                        "reason": r,
                        "cited": c,
                        "qualifiers": q,
                        "deviation": deviation_status(s, len(q), ""),
                    }
                    for eid, (s, r, c, q) in view["observations"].items()
                },
            }
        )
    return output
