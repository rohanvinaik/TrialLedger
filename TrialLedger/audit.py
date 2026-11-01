"""The serial audit loop (add-targeted-questions): one sampled trial at a time, resolved live, its record
kept, its questions written before any answer, then each question asked of the local model, if one is named.

For each trial: `resolve`'s own path reads it live (one snapshot) and keeps the record; its reading is built
by `reading.read_population`; a source manifest accounts for every piece of its eligibility text, every
outcome and every intervention; each typed atom becomes one `atom_claim` question with its envelope. Questions
go to questions.jsonl first, so a blind reference can be recorded before any answer exists; then, with a
model, each question is asked in turn and its validated answer goes to answers.jsonl. Nothing here changes a
reading."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from TrialLedger import warrants
from TrialLedger.criteria import itemize
from TrialLedger.questions import (
    ATOM_CLAIM_OPTIONS,
    answer_schema,
    atom_claim,
    envelope,
    question,
    validate_answer,
)
from TrialLedger.reading import read_population
from TrialLedger.transport import LocalModel, TransportError


def trial_questions(study: dict[str, Any], view: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    """One trial's audit questions and its source manifest.

    The manifest has one row per eligibility piece (heading, criterion, prose; with offsets and the count of
    atoms typed from it), per registered outcome and per intervention, so a piece no question touches is still
    seen. Each atom of each criterion is one `atom_claim` question; a criterion whose envelope cannot be built
    within budget is a manifest row with that reason and no question.
    """
    protocol = study.get("protocolSection", {})
    nct = view["nct"]
    text = protocol.get("eligibilityModule", {}).get("eligibilityCriteria") or ""
    _code, pieces = itemize(text if isinstance(text, str) else "")
    atoms_at = {index: atoms for index, _section, _text, atoms in view["criteria"]}
    questions, manifest = [], []
    for index, (kind, section, start, end) in enumerate(pieces):
        atoms = atoms_at.get(index, [])
        row = {"nct": nct, "unit": "eligibility", "piece": index, "kind": kind, "section": section}
        row |= {
            "start": start,
            "end": end,
            "atoms": len(atoms),
            "status": "untyped" if not atoms else "typed",
        }
        if kind != "criterion":
            row["status"] = kind
        else:
            code, held = envelope(text, pieces, index)
            if code != "ok":
                row["status"] = code
            for number, atom in enumerate(atoms if code == "ok" else []):
                target = {"nct": nct, "piece": index, "atom": number, "claim": atom_claim(atom, section)}
                target |= {"concept": atom[1], "values": list(atom[2]), "params": [list(p) for p in atom[3]]}
                target["section"] = section
                questions.append(question("atom_claim", target, held, ATOM_CLAIM_OPTIONS))
        manifest.append(row)
    for number, (kind, measure, frame, classes, points) in enumerate(view["outcomes"]):
        manifest.append(
            {"nct": nct, "unit": "outcome", "piece": number, "kind": kind, "text": measure, "frame": frame}
            | {"classes": classes, "points": points, "status": "not_asked_this_wave"}
        )
    for number, (drug, state, classes, source) in enumerate(view["drugs"]):
        manifest.append(
            {"nct": nct, "unit": "intervention", "piece": number, "text": drug, "state": state}
            | {"classes": classes, "source": source, "status": "not_asked_this_wave"}
        )
    return questions, manifest


def answer_questions(model: LocalModel, questions: list[dict]) -> list[dict]:
    """Ask `model` each question in turn; each answer is validated, and a refusal or a failure is kept as its
    named code, never as a verdict."""
    schema = answer_schema(ATOM_CLAIM_OPTIONS)
    rows = []
    for item in questions:
        try:
            raw, identity, cached = model.ask(item, schema)
            code, verdict, quote = validate_answer(raw, ATOM_CLAIM_OPTIONS, item["envelope"])
        except TransportError as error:
            raw, identity, cached = "", "", False
            code, verdict, quote = error.code, "", ""
        rows.append(
            {"question": item["id"], "nct": item["target"].get("nct", ""), "code": code, "verdict": verdict}
            | {"quote": quote, "identity": identity, "cached": cached, "raw": raw}
        )
    return rows


def _append(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_audit(
    sample: dict[str, Any],
    out: Path,
    *,
    fetch: Callable[[str], tuple[list[dict], str, str]],
    classes_for: Callable[[list[dict]], dict[str, Any]],
    model: LocalModel | None = None,
    limit: int = 0,
    progress: Callable[[str], None] = lambda message: None,
) -> dict[str, int]:
    """Audit a sample one trial at a time; returns counts. `fetch(nct)` reads one trial live (one snapshot),
    `classes_for(studies)` its RxClass answers; `model`, if given, answers each question in turn and is
    released at the end. A trial already in out/records is read from there, never fetched again."""
    records = out / "records"
    records.mkdir(parents=True, exist_ok=True)
    counts = {"trials": 0, "questions": 0, "answered": 0, "answer_errors": 0}
    trials = sample["trials"][:limit] if limit else sample["trials"]
    try:
        for trial in trials:
            nct = trial["nct"]
            kept = records / f"{nct}.json"
            record: dict[str, Any]
            if kept.is_file():
                record = json.loads(kept.read_text(encoding="utf-8"))
            else:
                studies, version, timestamp = fetch(nct)
                record = {"study": studies[0], "api_version": version, "data_timestamp": timestamp}
                record["digest"] = warrants.study_digest(studies[0])
                kept.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            study: dict[str, Any] = record["study"]
            view = read_population([study], classes_for([study]))["views"][0]
            questions, manifest = trial_questions(study, view)
            _append(out / "manifest.jsonl", manifest)
            _append(out / "questions.jsonl", questions)
            counts["trials"] += 1
            counts["questions"] += len(questions)
            progress(f"{nct}: {len(questions)} questions, {len(manifest)} manifest rows")
            if model is not None:
                rows = answer_questions(model, questions)
                counts["answered"] += sum(1 for row in rows if row["code"] == "ok")
                counts["answer_errors"] += sum(1 for row in rows if row["code"] != "ok")
                _append(out / "answers.jsonl", rows)
    finally:
        if model is not None:
            model.release()
    return counts
