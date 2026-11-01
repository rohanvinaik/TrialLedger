"""The serial audit loop (add-targeted-questions): one sampled trial at a time, resolved live, its record
kept, its questions written before any answer, then each question asked of the local model, if one is named.

For each trial: `resolve`'s own path reads it live (one snapshot) and keeps the record; its reading is built
by `reading.read_population`; a source manifest accounts for every piece of its eligibility text (and confirms
that only whitespace lies between the pieces, naming any text no piece covers), every outcome and every
intervention. The questions (design.md Decision 6), each one thing asked with its own bounded envelope: each
typed atom is one `atom_claim`; each criterion no bank typed is one `untyped_criterion`; each endpoint class
of an outcome is one `outcome_endpoint` on its measure; each time point of an outcome is one
`outcome_time_point` on its time frame, in the role the "up to N" rule gives it; each target an experimental
drug's own entry states is one `intervention_target`. An RxClass assignment is never a question: it is checked
against the RxClass answer kept in the audit folder (rxclass.json, written before the trial is read, each name
once, with its retrieval time) as read back from disk, and the result is a manifest field; a drug with no
RxClass class is recorded as unclassed by RxClass or as not established (a lookup failed or was never
answered). Every manifest, question and answer row says how its trial was drawn (`drawn_as`: "sample" or
"supplement"), so a rate is never read over the supplement by default. Questions go to questions.jsonl first,
so a blind reference can be recorded before any answer exists; then, with a model, each question is asked in
turn and its validated answer goes to answers.jsonl. After the sample, balance.json counts the audited trials
by phase, intervention type and primary purpose, names the gaps against the registry and lists the labelled
supplement drawn for them. Nothing here changes a reading."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from TrialLedger import classes as rx
from TrialLedger import warrants
from TrialLedger.criteria import itemize
from TrialLedger.questions import (
    ATOM_CLAIM_OPTIONS,
    FIELD_CLAIM_OPTIONS,
    TIME_POINT_OPTIONS,
    UNTYPED_OPTIONS,
    answer_schema,
    atom_claim,
    concept_instances,
    endpoint_claim,
    envelope,
    field_envelope,
    instances_schema,
    question,
    target_claim,
    time_point_claim,
    time_point_role,
    untyped_claim,
    untyped_reading,
    validate_answer,
    validate_instances,
)
from TrialLedger.reading import drug_aliases, effective_section, read_population
from TrialLedger.sample import (
    VERIFIED_FORMS,
    balance_rows,
    declared_cells,
    draw_supplements,
    holds_cell,
    trial_cells,
)
from TrialLedger.transport import LocalModel, TransportError

OUTCOME_LISTS = {"primary": "primaryOutcomes", "secondary": "secondaryOutcomes", "other": "otherOutcomes"}
KEPT_RXCLASS = "rxclass.json"  # the RxClass answers the audit used, kept in its folder


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


def rxclass_check(answers: dict[str, Any], alias: str, epc: list[str]) -> tuple[str, list[list[str]]]:
    """A classified intervention's classes checked against the kept RxClass answer (pure — pinned).

    `alias` is the name that resolved it and `epc` the established pharmacologic classes the reading gives it.
    Returns ("matches_artifact", kept) when the kept answer for `alias` lists classes and its has_epc class
    names are exactly `epc`; ("differs_from_artifact", kept) when they are not; ("not_in_artifact", []) when
    no answer with a class list is kept for `alias`. `kept` is that answer's classes, each (id, name,
    relation, source). Never a model question.
    """
    answer = answers.get(alias)
    if not isinstance(answer, dict) or not isinstance(answer.get("classes"), list):
        return "not_in_artifact", []
    kept = [[str(part) for part in item] for item in answer["classes"] if isinstance(item, (list, tuple))]
    names = sorted({item[1] for item in kept if len(item) == 4 and item[2] == "has_epc"})
    return ("matches_artifact" if names == sorted(epc) else "differs_from_artifact"), kept


def rxclass_absence(answers: dict[str, Any], aliases: list[str]) -> str:
    """What the kept RxClass answers say of a drug none of whose names they classify (pure — pinned).

    "differs_from_artifact" when a kept answer for one of its `aliases` lists a class (the reading was given
    none). "rxclass_unclassed" when every alias (at least one) has a kept answer with no class and every query
    of each answered not_found: RxClass established that it knows no class for the drug.
    "rxclass_not_established" otherwise: a lookup failed, a body was malformed, or a name was never answered,
    so the absence of a class is not established.
    """
    if any(isinstance(answers.get(alias), dict) and answers[alias].get("classes") for alias in aliases):
        return "differs_from_artifact"
    if not aliases:
        return "rxclass_not_established"
    for alias in aliases:
        answer = answers.get(alias)
        if not isinstance(answer, dict):
            return "rxclass_not_established"
        codes = answer.get("codes")
        if not isinstance(codes, dict) or not codes or set(codes.values()) != {"not_found"}:
            return "rxclass_not_established"
    return "rxclass_unclassed"


def keep_rxclass(path: Path, answers: dict[str, Any], names: list[str]) -> dict[str, Any]:
    """Copy into the audit folder's kept RxClass file the answers for `names` not yet kept there, each with
    its retrieval time (None for an answer cached before RxClass answers carried one); a kept answer is never
    rewritten. Returns the kept answers as read back from the file, so a check against them is a check against
    the artifact, not against the answers the reading was given."""
    kept = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    held = kept.setdefault("answers", {})
    new = {name: answers[name] for name in dict.fromkeys(names) if name in answers and name not in held}
    if new or not path.is_file():
        for name, answer in new.items():
            held[name] = {**answer, "retrieved": answer.get("retrieved")}
        kept["source"] = "NLM RxClass REST API, byDrugName; DAILYMED has_epc and MEDRT has_moa"
        kept["endpoint"] = rx.RXCLASS
        path.write_text(json.dumps(kept, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))["answers"]


def _eligibility(nct: str, text: str, view: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    _code, pieces = itemize(text)
    atoms_at = {index: atoms for index, _section, _text, atoms in view["criteria"]}
    questions, manifest = [], []
    for index, (kind, section, start, end) in enumerate(pieces):
        atoms = atoms_at.get(index, [])
        row: dict[str, Any] = {
            "nct": nct,
            "unit": "eligibility",
            "piece": index,
            "kind": kind,
            "section": section,
        }
        row |= {
            "start": start,
            "end": end,
            "atoms": len(atoms),
            "status": "untyped" if not atoms else "typed",
        }
        row["instances"] = [name for atom in atoms for name in concept_instances(atom[1], atom[2])]
        if kind != "criterion":
            row["status"] = kind
            manifest.append(row)
            continue
        code, held = envelope(text, pieces, index)
        if code != "ok":
            row["status"] = code
        elif not atoms:
            gap = {"nct": nct, "piece": index, "claim": untyped_claim(), "section": section}
            questions.append(question("untyped_criterion", gap, held, UNTYPED_OPTIONS))
        for number, atom in enumerate(atoms if code == "ok" else []):
            claimed = effective_section(section, atom[3])
            target: dict[str, Any] = {"nct": nct, "piece": index, "atom": number}
            target["claim"] = atom_claim(atom, claimed)
            target |= {"concept": atom[1], "values": list(atom[2]), "params": [list(p) for p in atom[3]]}
            target["section"] = claimed
            questions.append(question("atom_claim", target, held, ATOM_CLAIM_OPTIONS))
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
    return questions, manifest


def _outcomes(nct: str, view: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    questions, manifest = [], []
    within: dict[str, int] = {}
    for number, (kind, measure, frame, classes, points) in enumerate(view["outcomes"]):
        place = f"outcomesModule.{OUTCOME_LISTS[kind]}[{within.setdefault(kind, 0)}]"
        within[kind] += 1
        roles = [time_point_role(frame, p) for p in points]
        row: dict[str, Any] = {
            "nct": nct,
            "unit": "outcome",
            "piece": number,
            "kind": kind,
            "text": measure,
            "frame": frame,
        }
        row |= {"classes": classes, "points": points, "roles": roles}
        asked = []
        code, held = field_envelope(f"{place}.measure", measure, [])
        for endpoint in classes if code == "ok" else []:
            about = {"nct": nct, "unit": "outcome", "piece": number, "claim": endpoint_claim(endpoint)}
            about["endpoint"] = endpoint
            asked.append(question("outcome_endpoint", about, held, FIELD_CLAIM_OPTIONS))
        frame_code, frame_held = field_envelope(f"{place}.timeFrame", frame, [(f"{place}.measure", measure)])
        for point, role in zip(points, roles, strict=True) if frame_code == "ok" else []:
            timed = {"nct": nct, "unit": "outcome", "piece": number, "claim": time_point_claim(point, role)}
            timed |= {"point": point, "role": role}
            asked.append(question("outcome_time_point", timed, frame_held, TIME_POINT_OPTIONS))
        refused = [c for c in (code, frame_code) if c == "envelope_over_budget"]
        row["status"] = refused[0] if refused else "asked" if asked else "no_claim"
        row["questions"] = len(asked)
        questions.extend(asked)
        manifest.append(row)
    return questions, manifest


def _interventions(
    nct: str, study: dict[str, Any], view: dict[str, Any], answers: dict[str, Any]
) -> tuple[list[dict], list[dict]]:
    entries = (
        study.get("protocolSection", {}).get("armsInterventionsModule", {}).get("interventions", []) or []
    )
    # The last entry of a name, as the reading's own lookup of descriptions takes it.
    at = {item.get("name"): i for i, item in enumerate(entries) if isinstance(item, dict)}
    names = rx.drug_names(study)
    questions, manifest = [], []
    for number, (drug, state, classes, source) in enumerate(view["drugs"]):
        row: dict[str, Any] = {
            "nct": nct,
            "unit": "intervention",
            "piece": number,
            "text": drug,
            "state": state,
        }
        row |= {"classes": classes, "source": source, "questions": 0}
        if state == "classified":
            row["rxclass"], row["artifact"] = rxclass_check(answers, source, classes)
            row["status"] = "rxclass_checked"
            manifest.append(row)
            continue
        # No RxClass class: whether RxClass established that, or a lookup failed or was never answered.
        row["rxclass"] = rxclass_absence(answers, names.get(drug, []))
        if state == "stated_by_record" and drug in at:
            place = f"armsInterventionsModule.interventions[{at[drug]}]"
            description = str(entries[at[drug]].get("description") or "")
            # The reading read the name and description together; with no description, the name is the target.
            if description.strip():
                code, held = field_envelope(f"{place}.description", description, [(f"{place}.name", drug)])
            else:
                code, held = field_envelope(f"{place}.name", drug, [])
            stated = [c.removeprefix("stated: ") for c in classes] if code == "ok" else []
            for target_class in stated:
                target = {"nct": nct, "unit": "intervention", "piece": number, "drug": drug}
                target |= {"claim": target_claim(drug, target_class), "stated": target_class}
                questions.append(question("intervention_target", target, held, FIELD_CLAIM_OPTIONS))
            row["questions"] = len(stated)
            row["status"] = "asked" if stated else code
        else:
            row["status"] = row["rxclass"]
        manifest.append(row)
    return questions, manifest


def trial_questions(
    study: dict[str, Any], view: dict[str, Any], answers: dict[str, Any], drawn_as: str
) -> tuple[list[dict], list[dict]]:
    """One trial's audit questions and its source manifest, given the kept RxClass `answers` (the audit
    folder's copy, as read back from disk) that the reading's classes are checked against, every row labelled
    with how the trial was drawn (`drawn_as`; outside the question's id and prompt).

    The manifest has one row per eligibility piece (heading, criterion, prose; with offsets, the count of
    atoms typed from it and their concept instances), one row confirming that the gaps between pieces are
    whitespace only (`text_coverage`), one per stretch of text no piece covers (`eligibility_gap`, always,
    even when pieces also overlap) and one per stretch read twice (`eligibility_overlap`), one per registered
    outcome (its endpoint classes, time points and their roles) and per experimental drug (an RxClass
    assignment's check against the kept answer; for a drug with no RxClass class, whether RxClass established
    that or a lookup failed or never answered), so a piece no question touches is still seen. A piece whose
    envelope cannot be built within budget is a manifest row with that reason and no question.
    """
    protocol = study.get("protocolSection", {})
    nct = view["nct"]
    text = protocol.get("eligibilityModule", {}).get("eligibilityCriteria") or ""
    questions, manifest = _eligibility(nct, text if isinstance(text, str) else "", view)
    for part in (_outcomes(nct, view), _interventions(nct, study, view, answers)):
        questions.extend(part[0])
        manifest.extend(part[1])
    return [q | {"drawn_as": drawn_as} for q in questions], [row | {"drawn_as": drawn_as} for row in manifest]


def answer_questions(model: LocalModel, questions: list[dict]) -> list[dict]:
    """Ask `model` each question in turn, under its own kind's schema; each answer is validated, and a refusal
    or a failure is kept as its named code, never as a verdict. An untyped-criterion answer's verdict is what
    its instances say of the criterion (`untyped_reading`), its instances kept beside it. Each answer row
    carries its question's `drawn_as` ("" if it has none)."""
    rows = []
    for item in questions:
        options = tuple(item["options"])
        untyped = item["kind"] == "untyped_criterion"
        schema = instances_schema(options) if untyped else answer_schema(options)
        found: list[tuple[str, str]] = []
        try:
            raw, identity, cached = model.ask(item, schema)
            if untyped:
                code, found = validate_instances(raw, options, item["envelope"])
                verdict, quote = (untyped_reading(found) if code == "ok" else ""), ""
            else:
                code, verdict, quote = validate_answer(raw, options, item["envelope"])
        except TransportError as error:
            raw, identity, cached = "", "", False
            code, verdict, quote = error.code, "", ""
        rows.append(
            {"question": item["id"], "nct": item["target"].get("nct", ""), "kind": item["kind"], "code": code}
            | {"verdict": verdict, "quote": quote, "instances": [list(pair) for pair in found]}
            | {"identity": identity, "cached": cached, "raw": raw}
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
    """One trial through the loop: its record kept (or read back), the RxClass answers for its drug names kept
    in the audit folder, its manifest and questions written, its questions asked if there is a model. Returns
    the balance cells its record holds."""
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
    answers = classes_for([study])
    artifact = keep_rxclass(out / KEPT_RXCLASS, answers, drug_aliases([study]))
    view = read_population([study], answers)["views"][0]
    questions, manifest = trial_questions(study, view, artifact, drawn_as)
    _append(out / "manifest.jsonl", manifest)
    _append(out / "questions.jsonl", questions)
    counts["trials"] += 1
    counts["questions"] += len(questions)
    progress(f"{nct}: {len(questions)} questions, {len(manifest)} manifest rows")
    if model is not None:
        rows = answer_questions(model, questions)
        counts["answered"] += sum(1 for row in rows if row["code"] == "ok")
        counts["answer_errors"] += sum(1 for row in rows if row["code"] != "ok")
        counts["out_of_taxonomy"] += sum(
            1 for row in rows if any(option == "out_of_taxonomy" for option, _ in row["instances"])
        )
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
    released at the end. A trial already in out/records is read from there, never fetched again. Before a
    trial is read, the RxClass answers for its drug names are copied into out/rxclass.json with their
    retrieval times, each name once (a name already kept, by this run or an earlier one, is never rewritten);
    the reading's classes are checked against that kept copy as read back from disk, so an answer that has
    changed since it was kept is recorded as differing from the artifact. An answer naming a requirement
    outside the banks' taxonomy is counted apart (`out_of_taxonomy`), never as an error.

    Then the balance table goes to balance.json beside the manifest: the audited trials counted by phase,
    intervention type and primary purpose from their records. When the whole sample was audited, the sample
    declares its supplement and `query_ids` can read the registry, each declared cell no drawn trial holds is
    checked against the registry and, if the frame holds some, a labelled supplement is drawn for it and
    audited in the same loop; otherwise those cells are named "not_checked". A cell the registry returns
    none for is "empty_in_registry" only when its query's forms are in `VERIFIED_FORMS`."""
    (out / "records").mkdir(parents=True, exist_ok=True)
    counts = dict.fromkeys(
        ("trials", "questions", "answered", "answer_errors", "supplements", "out_of_taxonomy"), 0
    )
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
