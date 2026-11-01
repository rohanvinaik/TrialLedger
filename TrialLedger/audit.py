"""The serial audit loop (add-targeted-questions): one sampled trial at a time, resolved live, its record
kept, its questions written before any answer, then each question asked of the local model, if one is named.

For each trial: `resolve`'s own path reads it live (one snapshot) and keeps the record; its reading is built
by `reading.read_population`; a source manifest accounts for every piece of its eligibility text (and confirms
that only whitespace lies between the pieces, naming any text no piece covers), every outcome and every
intervention; each typed atom becomes one `atom_claim` question with its envelope. Every manifest, question
and answer row says how its trial was drawn (`drawn_as`: "sample" or "supplement"), so a rate is never read
over the supplement by default. Questions go to questions.jsonl first, so a blind reference can be recorded
before any answer exists; then, with a model, each question is asked in turn and its validated answer goes to
answers.jsonl. After the sample, balance.json counts the audited trials by phase, intervention type and
primary purpose, names the gaps against the registry and lists the labelled supplement drawn for them. Nothing
here changes a reading."""

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
from TrialLedger.reading import effective_section, read_population
from TrialLedger.sample import (
    VERIFIED_FORMS,
    balance_rows,
    declared_cells,
    draw_supplements,
    holds_cell,
    trial_cells,
)
from TrialLedger.transport import LocalModel, TransportError


def text_coverage(
    text: str, pieces: list[tuple[str, str, int, int]]
) -> tuple[str, list[tuple[int, int]], list[tuple[int, int]]]:
    """Whether the eligibility pieces account for the whole text (pure — pinned).

    Every stretch the pieces leave (before the first, between two, after the last) must be whitespace only,
    so the pieces and the gaps in order reproduce the text. Returns (the code, the stretches of text no piece
    covers, the stretches read twice), each as (start, end); both lists are always complete, so an overlap
    never hides a hole.
      "covered"                   — they do; no spans.
      "overlapping"               — a piece starts before the previous one ends; no text is uncovered.
      "uncovered_text"            — some stretch holds text no piece covers; nothing overlaps.
      "overlapping_and_uncovered" — both.
    """
    holes: list[tuple[int, int]] = []
    overlaps: list[tuple[int, int]] = []
    at = 0
    for _kind, _section, start, end in pieces:
        if start < at:
            overlaps.append((start, min(at, end)))
        elif text[at:start].strip():
            holes.append((at, start))
        at = max(at, end)
    if text[at:].strip():
        holes.append((at, len(text)))
    if overlaps and holes:
        return "overlapping_and_uncovered", holes, overlaps
    if overlaps:
        return "overlapping", holes, overlaps
    if holes:
        return "uncovered_text", holes, overlaps
    return "covered", holes, overlaps


def trial_questions(
    study: dict[str, Any], view: dict[str, Any], drawn_as: str
) -> tuple[list[dict], list[dict]]:
    """One trial's audit questions and its source manifest, every row labelled with how the trial was drawn
    (`drawn_as`; outside the question's id and prompt).

    The manifest has one row per eligibility piece (heading, criterion, prose; with offsets and the count of
    atoms typed from it), one row confirming that the gaps between pieces are whitespace only
    (`text_coverage`), one per stretch of text no piece covers (`eligibility_gap`, always, even when pieces
    also overlap) and one per stretch read twice (`eligibility_overlap`), then one per registered outcome and
    per intervention, so a piece no question touches is still seen. Each atom of each criterion is one
    `atom_claim` question; a criterion whose envelope cannot be built within budget is a manifest row with
    that reason and no question.
    """
    protocol = study.get("protocolSection", {})
    nct = view["nct"]
    text = protocol.get("eligibilityModule", {}).get("eligibilityCriteria") or ""
    text = text if isinstance(text, str) else ""
    _code, pieces = itemize(text)
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
                claimed = effective_section(section, atom[3])
                target = {"nct": nct, "piece": index, "atom": number, "claim": atom_claim(atom, claimed)}
                target |= {"concept": atom[1], "values": list(atom[2]), "params": [list(p) for p in atom[3]]}
                target["section"] = claimed
                asked = question("atom_claim", target, held, ATOM_CLAIM_OPTIONS)
                questions.append(asked | {"drawn_as": drawn_as})
        manifest.append(row)
    coverage, holes, overlaps = text_coverage(text, pieces)
    manifest.append(
        {"nct": nct, "unit": "eligibility_text", "kind": "coverage", "length": len(text)}
        | {"pieces": len(pieces), "status": coverage}
    )
    for unit, kind, spans in (
        ("eligibility_gap", "uncovered_text", holes),
        ("eligibility_overlap", "overlapping", overlaps),
    ):
        manifest.extend(
            {"nct": nct, "unit": unit, "kind": kind, "start": start, "end": end}
            | {"text": text[start:end], "status": kind}
            for start, end in spans
        )
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
    return questions, [row | {"drawn_as": drawn_as} for row in manifest]


def answer_questions(model: LocalModel, questions: list[dict]) -> list[dict]:
    """Ask `model` each question in turn; each answer is validated, and a refusal or a failure is kept as its
    named code, never as a verdict. Each answer row carries its question's `drawn_as` ("" if it has none)."""
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
            | {"drawn_as": item.get("drawn_as", "")}
        )
    return rows


def _append(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _audit_trial(
    nct: str,
    drawn_as: str,
    out: Path,
    counts: dict[str, int],
    *,
    fetch: Callable[[str], tuple[list[dict], str, str]],
    classes_for: Callable[[list[dict]], dict[str, Any]],
    model: LocalModel | None,
    progress: Callable[[str], None],
) -> dict[str, list[str]]:
    """One trial through the loop: its record kept (or read back), its manifest and questions written, its
    questions asked if there is a model. Returns the balance cells its record holds."""
    kept = out / "records" / f"{nct}.json"
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
    questions, manifest = trial_questions(study, view, drawn_as)
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
    return trial_cells(study)


def run_audit(
    sample: dict[str, Any],
    out: Path,
    *,
    fetch: Callable[[str], tuple[list[dict], str, str]],
    classes_for: Callable[[list[dict]], dict[str, Any]],
    model: LocalModel | None = None,
    limit: int = 0,
    query_ids: Callable[..., tuple[list[str], str, str]] | None = None,
    progress: Callable[[str], None] = lambda message: None,
) -> dict[str, int]:
    """Audit a sample one trial at a time; returns counts. `fetch(nct)` reads one trial live (one snapshot),
    `classes_for(studies)` its RxClass answers; `model`, if given, answers each question in turn and is
    released at the end. A trial already in out/records is read from there, never fetched again.

    Then the balance table goes to balance.json beside the manifest: the audited trials counted by phase,
    intervention type and primary purpose from their records. When the whole sample was audited, the sample
    declares its supplement and `query_ids` can read the registry, each declared cell no drawn trial holds is
    checked against the registry and, if the frame holds some, a labelled supplement is drawn for it and
    audited in the same loop; otherwise those cells are named "not_checked". A cell the registry returns
    none for is "empty_in_registry" only when its query's forms are in `VERIFIED_FORMS`."""
    (out / "records").mkdir(parents=True, exist_ok=True)
    counts = {"trials": 0, "questions": 0, "answered": 0, "answer_errors": 0, "supplements": 0}
    trials = sample["trials"][:limit] if limit else sample["trials"]
    declaration = sample.get("balance")
    declared = declaration["cells"] if declaration else declared_cells()

    def one(nct: str, drawn_as: str) -> dict[str, list[str]]:
        return _audit_trial(
            nct, drawn_as, out, counts, fetch=fetch, classes_for=classes_for, model=model, progress=progress
        )

    registry: dict[str, int] = {}
    supplements: list[dict[str, Any]] = []
    snapshot: dict[str, str] = {}
    supplement_cells: list[dict[str, list[str]]] = []
    drawn: list[dict[str, list[str]]] = []
    try:
        drawn = [one(t["nct"], "sample") for t in trials]
        rows = balance_rows(drawn, [], declared, {}, VERIFIED_FORMS)
        if declaration and query_ids is not None and len(trials) == len(sample["trials"]):
            sampled = {t["nct"] for t in sample["trials"]}
            registry, supplements, snapshot = draw_supplements(
                rows, sample["seed"], declaration["supplement_per_cell"], sampled, query_ids, progress
            )
            held = {}
            for nct in dict.fromkeys(item["nct"] for item in supplements):
                held[nct] = one(nct, "supplement")
                supplement_cells.append(held[nct])
            for item in supplements:
                item["holds_cell"] = holds_cell(held[item["nct"]][item["axis"]], item["value"])
            counts["supplements"] = len(held)
    finally:
        if model is not None:
            model.release()
    table = {
        "audited": len(trials),
        "of": len(sample["trials"]),
        "declared": bool(declaration),
        "rows": balance_rows(drawn, supplement_cells, declared, registry, VERIFIED_FORMS),
        "verified_query_forms": VERIFIED_FORMS,
        "supplements": supplements,
        "supplement_snapshot": snapshot,
    }
    (out / "balance.json").write_text(json.dumps(table, indent=1, ensure_ascii=False), encoding="utf-8")
    return counts
