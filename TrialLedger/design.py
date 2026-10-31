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
from TrialLedger.banks import type_criterion
from TrialLedger.cells import cell_number_state, cell_text_state
from TrialLedger.coherence import RELATIONS, SETTINGS, resolve
from TrialLedger.criteria import itemize
from TrialLedger.profile import (
    SIGNAL_MIN_SPONSORS,
    SIGNAL_MIN_TRIALS,
    STANDARD_SHARE,
    element_key,
    frequency_rows,
    mechanism_rows,
    occupancy_rows,
)

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
    drugs = []
    for drug in rx.experimental_drugs(study):
        state, found, resolved_by = rx.drug_class(answers, names[drug])
        epc = sorted({c[1] for c in found if c[2] == "has_epc"})
        drugs.append((drug, state, epc, resolved_by))
    return {
        "nct": nct,
        "digest": warrants.study_digest(study),
        "sponsor": protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", ""),
        "status": protocol.get("statusModule", {}).get("overallStatus", ""),
        "itemize": code,
        "criteria": criteria,
        "coordinates": resolve(evidence),
        "elements": elements,
        "drugs": drugs,
    }


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
    names = [alias for study in studies for aliases in rx.drug_names(study).values() for alias in aliases]
    kwargs = {"get": get} if sleep is None else {"get": get, "sleep": sleep}
    answers = rx.load_or_lookup(folder, names, **kwargs)
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
    target = folder / DESIGN_NAME
    book.save(target)
    return target, sizes
