"""The `trialledger` command: API parameters in; the record, the registry's spreadsheet and a certified review
workbook out. And `trialledger verify`, which re-derives a written folder from its record."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from TrialLedger import classes as rx
from TrialLedger import warrants
from TrialLedger.design import DESIGN_NAME, DesignError, write_book, write_design
from TrialLedger.ingest import SPEC_API_VERSION, PullError, check_query, pull, query_studies
from TrialLedger.reading import axes_aliases, drug_aliases, read_population
from TrialLedger.record import CSV_NAME, JSON_NAME, code_commit, verify_folder, write_record
from TrialLedger.symbolic import symbolic_output
from TrialLedger.workbook import RECORD_NAME, WORKBOOK_NAME, WorkbookError

PULL_HELP = """\
Pull every ClinicalTrials.gov study a query matches, through the official API (spec/ctg-oas-v2.yaml),
into a new directory holding studies.json (the records exactly as the API sent them, plus provenance and
content digests), studies.csv (the API's own spreadsheet for the same query), review.xlsx (the review
workbook: the design sheets and the approved edit checks) and record.xlsx (every value of every study, in the
registry's own categories), every cell of both warranted and certified against the record. If anything
fails, nothing is written; a workbook over Google Sheets' cap of 10,000,000 cells is named.

NAME is any /studies query parameter from the spec, sent exactly as given; the API rejects unknown names.
query.* parameters search the API's search areas and rank by relevance; filter.* parameters restrict the
set. Paging, format and fields are set by TrialLedger and cannot be overridden.

examples:
  trialledger pull filter.ids=NCT04852770
  trialledger pull filter.ids=NCT04852770,NCT01030536
  trialledger pull query.cond=sarcoidosis filter.overallStatus=RECRUITING
  trialledger pull "filter.advanced=AREA[StartDate]RANGE[2024-01-01,2024-01-31]" query.cond=asthma

exit status: 0 written · 1 the pull or the write failed, nothing written · 2 the query was refused
"""

VERIFY_HELP = """\
Re-derive a folder TrialLedger wrote, from studies.json: every study's digest and NCT number, the Merkle
root, the spreadsheet's digest and the record root over the provenance; then, under the code that wrote the
folder (its code root) and the same spreadsheet writer, every cell, kind of value and warrant of
review.xlsx and record.xlsx, and both files themselves, part for part, against a fresh write. Each value
that no longer follows is named; a studies.json whose objects repeat a key is refused.

exit status: 0 certified · 1 not certified (the differences are printed) · 2 not a TrialLedger record
"""


def parse_query_args(args: list[str]) -> tuple[str, dict[str, str], list[str]]:
    """Turn `name=value` command-line words into ClinicalTrials.gov API parameters (pure — pinned).

    Only the first "=" separates name from value, so a value may itself contain "=".
      "ok"             — the parameters, in the order given.
      "not_name_value" — words with no "=" or with nothing before it; nothing is guessed.
      "duplicate"      — a name given more than once; neither value is chosen silently.
    """
    malformed = [word for word in args if "=" not in word or word.startswith("=")]
    if malformed:
        return "not_name_value", {}, malformed
    params: dict[str, str] = {}
    duplicates: list[str] = []
    for word in args:
        name, value = word.split("=", 1)
        if name in params and name not in duplicates:
            duplicates.append(name)
        params[name] = value
    if duplicates:
        return "duplicate", {}, duplicates
    return "ok", params, []


def main(
    argv: list[str] | None = None,
    *,
    http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rxclass_get: Callable[[str, dict[str, str]], tuple[int, Any]] | None = None,
    model_http: Callable[..., Any] | None = None,
    git: Callable[..., str] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="trialledger",
        description=(
            "Resolve ClinicalTrials.gov studies to their symbolic design reading. The main path is "
            "`resolve`: a live query of the registry's API, read and resolved without saving the records. "
            "The fallback, when a stored and verifiable record is wanted, is `pull` (save a query's records, "
            "spreadsheet and certified workbooks), `profile` (resolve a saved folder) and `verify`."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    resolve_parser = commands.add_parser(
        "resolve",
        help="resolve a live query's studies to their symbolic reading, without saving the records",
        description=(
            "Query ClinicalTrials.gov live (the same parameters as pull, one snapshot, complete or nothing), "
            "and resolve every matching study to its symbolic reading: typed criteria, design coordinates, "
            "drug classes, outcomes and expectation observations. Nothing of the registry's record is saved; "
            "RxClass answers are cached in ~/.cache/trialledger (or $TRIALLEDGER_CACHE). Writes design.xlsx "
            "with --out, the reading as JSON with --json (a path, or - for standard output; the default). "
            "Ends with 0, resolved; 1, the query failed; 2, the query was refused."
        ),
    )
    resolve_parser.add_argument("parameters", nargs="*", metavar="NAME=VALUE")
    resolve_parser.add_argument("--out", type=Path, help="write design.xlsx for the matched studies here")
    resolve_parser.add_argument(
        "--json", help="write the symbolic reading as JSON here (- for standard output)"
    )
    resolve_parser.add_argument(
        "--keep",
        type=Path,
        help="also save the exact snapshot read (records, digests, root) here, so the reading can be "
        "re-checked after the registry changes; for a certified stored record use pull",
    )
    pull_parser = commands.add_parser(
        "pull",
        help="pull every study a query matches",
        description=PULL_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pull_parser.add_argument("parameters", nargs="*", metavar="NAME=VALUE")
    pull_parser.add_argument(
        "--out", type=Path, help="directory to create (default: ./trialledger_<UTC time>)"
    )
    verify_parser = commands.add_parser(
        "verify",
        help="re-derive a written folder from its record",
        description=VERIFY_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    verify_parser.add_argument("folder", type=Path)
    profile_parser = commands.add_parser(
        "profile",
        help="type, resolve and profile a written folder's studies into design.xlsx",
        description=(
            "Itemize and type every study's eligibility by deterministic rules, resolve each trial's design "
            "coordinates, classify experimental drugs by NLM RxClass (cached in classes.json), and measure "
            "every typed element against the folder's population. The drug-class axes (RxNorm identity, ATC, "
            "structure) are read from classes.json as cached: a drug whose axes were never asked of RxNav is "
            "marked not_looked_up on the Drug Axes sheet (never read as no class), unless --fill-axes asks "
            "for them first. Writes design.xlsx and classes.json; the pull's files are not changed. Ends "
            "with 0, written; 1, the record does not verify (nothing written, nothing asked); 2, not a "
            "TrialLedger folder."
        ),
    )
    profile_parser.add_argument("folder", type=Path)
    profile_parser.add_argument(
        "--fill-axes",
        action="store_true",
        help="first ask RxNav, spaced, for the axes of every experimental drug name classes.json does not "
        "yet hold (four to six requests a name: about an hour for a 487-trial folder never filled), and "
        "cache them",
    )
    sample_parser = commands.add_parser(
        "sample",
        help="draw a live, stratified sample of interventional trials for an audit",
        description=(
            "Fetch, live and from one registry snapshot, the NCT IDs of interventional trials started "
            "from 2010-01-01 to the present (today's UTC date, or --present; recorded in the file) in each "
            "top-level condition category (the registry's derived condition MeSH, a label "
            "for spread only) and among trials with no condition MeSH; draw a seeded random sample within "
            "each stratum from the discovery pool (a hash of the NCT ID reserves 30%% for confirmation, "
            "never drawn here); write the strata, pool sizes, draws, memberships and inclusion probabilities"
            " as JSON, with the declared balance check (phase, intervention type, primary purpose) and its "
            "seeded supplement, which the audit applies. With --confirmation-batch N, draw instead from that "
            "one confirmation batch (sha256 mod 10 equal to N, of 0, 1, 2: one batch per release, never "
            "reused for a revised version), recorded in the file with the code's commit and source digest, "
            "and declare no supplement. A confirmation draw needs TrialLedger/ and tests/ clean at a commit, "
            "every inspected population declared with --inspected (a sample.json, an audit's balance.json, "
            "or a record folder or its studies.json: the NSCLC record, the pilot and discovery samples), "
            "whose trials it never draws, and --batch-ledger, the declared file of batches used (batch to "
            "the commit it confirmed), which it consults and then records this batch in. Ends with 0, "
            "written; 1, the registry query failed; 2, refused (a batch not declared, code not clean at a "
            "commit, no or an empty inspected list, an unreadable ledger, or a batch already used for "
            "another commit)."
        ),
    )
    sample_parser.add_argument("--per-stratum", type=int, default=6)
    sample_parser.add_argument("--seed", required=True)
    sample_parser.add_argument("--out", type=Path, required=True)
    sample_parser.add_argument(
        "--present",
        help="the last start date of the frame, YYYY-MM-DD (default: today's UTC date)",
    )
    sample_parser.add_argument(
        "--confirmation-batch",
        type=int,
        help="draw a confirmation sample from this one batch (0, 1 or 2) instead of the discovery pool",
    )
    sample_parser.add_argument(
        "--inspected",
        type=Path,
        action="append",
        default=[],
        help="a kept list of trials already inspected, never drawn for confirmation (repeat for each)",
    )
    sample_parser.add_argument(
        "--batch-ledger",
        type=Path,
        help="the declared ledger of confirmation batches used (confirmation_ledger.json)",
    )
    audit_parser = commands.add_parser(
        "audit",
        help="ask a local model targeted questions about a sample's readings, one trial at a time",
        description=(
            "For each trial of a sample, in turn: read it live (the record kept under OUT/records), resolve "
            "it, write its source manifest and its questions (one per typed claim, each with a bounded "
            "envelope of its own eligibility text), then, with --model, ask a local Ollama model each "
            "question and write the validated answers. Questions are written before any answer, for blind "
            "references. Then balance.json: the trials by phase, intervention type and primary purpose, each "
            "registry value no drawn trial holds checked live against the registry and, as the sample "
            "declares, filled by a labelled, seeded supplement (audited in turn). Nothing changes a reading. "
            "Ends with 0, done; 1, the registry or the model failed; 2, refused."
        ),
    )
    audit_parser.add_argument("sample", type=Path)
    audit_parser.add_argument("--out", type=Path, required=True)
    audit_parser.add_argument(
        "--model", help="an installed Ollama model, named explicitly (none: questions only)"
    )
    audit_parser.add_argument("--budget", type=int, default=0, help="the most model calls this run may make")
    audit_parser.add_argument("--no-think", action="store_true")
    audit_parser.add_argument("--limit", type=int, default=0, help="audit only the first N trials")
    pilot_parser = commands.add_parser(
        "pilot",
        help="the auditor pilot over an audit folder: blind-label list, mutations, one model's answers",
        description=(
            "Over an audit folder's questions: write the seeded list of questions to label blind "
            "(to_label.json) and the planted mutations with the verdicts they must receive "
            "(mutations.jsonl), both drawn from the sample's own trials (drawn_as sample) unless "
            "--include-supplement; with --model, ask that one model the labelled questions and the "
            "mutations, one at a time, into DIR/pilot-<model>/answers.jsonl, and release it. Ends with 0, "
            "done; 2, refused."
        ),
    )
    pilot_parser.add_argument("folder", type=Path)
    pilot_parser.add_argument("--label", type=int, default=100)
    pilot_parser.add_argument("--mutate", type=int, default=60)
    pilot_parser.add_argument("--model")
    pilot_parser.add_argument("--budget", type=int, default=0)
    pilot_parser.add_argument("--no-think", action="store_true")
    pilot_parser.add_argument(
        "--include-supplement",
        action="store_true",
        help="also draw from the questions of trials drawn as a balance supplement (default: sample only)",
    )
    args = parser.parse_args(argv)
    if args.command == "pilot":
        return _pilot(args, model_http=model_http)
    if args.command == "sample":
        return _sample(args, http=http, sleep=sleep, git=git)
    if args.command == "audit":
        return _audit(args, http=http, sleep=sleep, rxclass_get=rxclass_get, model_http=model_http)
    if args.command == "resolve":
        return _resolve(args, http=http, sleep=sleep, rxclass_get=rxclass_get)
    if args.command == "verify":
        return _verify(args.folder)
    if args.command == "profile":
        return _profile(args.folder, rxclass_get, fill_axes=args.fill_axes)

    code, params, offending = parse_query_args(args.parameters)
    if code != "ok":
        print(f"trialledger: refused ({code}): {' '.join(offending)}", file=sys.stderr)
        return 2
    verdict, names = check_query(params)
    if verdict != "ok":
        detail = ", ".join(names) or "give at least one NAME=VALUE"
        print(f"trialledger: refused (query.{verdict}): {detail}", file=sys.stderr)
        return 2
    try:
        result = pull(
            params, http=http, sleep=sleep, progress=lambda message: print(message, file=sys.stderr)
        )
    except PullError as error:
        print(f"trialledger: nothing written — {error}", file=sys.stderr)
        return 1
    if result.api_version != SPEC_API_VERSION:
        print(
            f"trialledger: note — the API reports version {result.api_version}; "
            f"spec/ctg-oas-v2.yaml describes {SPEC_API_VERSION}",
            file=sys.stderr,
        )
    stamp = result.retrieved_at.replace("-", "").replace(":", "")
    out_dir: Path = args.out or Path(f"trialledger_{stamp}")
    try:
        write_record(result, out_dir, progress=lambda message: print(message, file=sys.stderr))
    except (OSError, WorkbookError) as error:
        print(f"trialledger: nothing written — {error}", file=sys.stderr)
        return 1
    print(
        f"{result.total_count} studies written to {out_dir}/ ({JSON_NAME}, {CSV_NAME}, {WORKBOOK_NAME}, "
        f"{RECORD_NAME}, "
        f"certified) — ClinicalTrials.gov data as of {result.data_timestamp}, API {result.api_version}"
    )
    return 0


def _read_json(path: Path) -> Any:
    """A JSON file's content, or None when it cannot be read as JSON."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _inspected_list(path: Path) -> dict[str, Any]:
    """One declared list of inspected trials as kept in a confirmation sample: the file (a record folder's
    studies.json), the SHA-256 of its bytes and the NCT IDs it lists."""
    from TrialLedger.sample import inspected_ids

    path = path / JSON_NAME if path.is_dir() else path
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        digest = ""
    return {"path": str(path), "sha256": digest, "ncts": inspected_ids(_read_json(path))}


def _sample(args, *, http, sleep, git) -> int:
    from TrialLedger.ingest import query_ids
    from TrialLedger.sample import (
        BASE_FROM,
        SnapshotChanged,
        batch_request,
        code_state,
        draw_sample,
        ledger_batches,
    )

    present = args.present or datetime.now(UTC).date().isoformat()
    try:
        valid = date.fromisoformat(present).isoformat() == present and present >= BASE_FROM
    except ValueError:
        valid = False
    if not valid:
        print(
            f"trialledger: refused (sample.present): {present} is not a date from {BASE_FROM}",
            file=sys.stderr,
        )
        return 2
    batch = args.confirmation_batch
    commit = code_commit()
    inspected: list[dict[str, Any]] = []
    extra: dict[str, Any] = {}
    used: dict[str, str] | None = None
    if batch is not None:
        state = code_state(git=git)
        inspected = [_inspected_list(path) for path in args.inspected]
        ledger = _read_json(args.batch_ledger) if args.batch_ledger else None
        used = ledger_batches(ledger)
        commit = state["commit"]
        verdict = batch_request(batch, commit, state["dirty"], [len(i["ncts"]) for i in inspected], used)
        if verdict != "ok":
            dirty = ", ".join(state["dirty"][:5])
            print(
                f"trialledger: refused (confirmation.{verdict}): batch {batch}, code {commit or 'unnamed'}"
                + (f", uncommitted: {dirty}" if dirty else ""),
                file=sys.stderr,
            )
            return 2
        extra = {
            "code_source_digest": state["source_digest"],
            "code_watched": state["watched"],
            "inspected": inspected,
            "batch_ledger": str(args.batch_ledger),
        }

    def ids(query, progress):
        return query_ids(query, http=http, sleep=sleep, progress=progress)

    try:
        sample = draw_sample(
            args.per_stratum,
            args.seed,
            ids,
            progress=lambda m: print(m, file=sys.stderr),
            batch=batch,
            inspected=frozenset(nct for item in inspected for nct in item["ncts"]),
            present=present,
        )
    except (PullError, SnapshotChanged) as error:
        print(f"trialledger: nothing written — {error}", file=sys.stderr)
        return 1
    sample["code_commit"] = commit
    sample.update(extra)
    args.out.write_text(json.dumps(sample, indent=1), encoding="utf-8")
    if batch is not None and used is not None and str(batch) not in used:
        retired = {**(ledger or {}), "batches": used | {str(batch): commit}}
        args.batch_ledger.write_text(json.dumps(retired, indent=1) + "\n", encoding="utf-8")
    cells = sum(len(values) for values in sample["balance"]["cells"].values())
    excluded = sample["inspected_excluded"]
    print(
        f"{args.out} written ({len(sample['trials'])} trials from the {sample['drawn_from']} pool, "
        f"data as of {sample['data_timestamp']}; "
        f"balance declared over {cells} registry values, {sample['balance']['supplement_per_cell']} "
        "supplement trial per empty cell"
        + (f"; {excluded} inspected trials of the batch excluded" if excluded is not None else "")
        + ")"
    )
    return 0


def _pilot(args, *, model_http) -> int:
    from TrialLedger.audit import answer_questions
    from TrialLedger.pilot import drawn_units, mutations, to_label
    from TrialLedger.transport import LocalModel, TransportError, urllib_http

    lines = (args.folder / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    questions = drawn_units([json.loads(line) for line in lines], args.include_supplement)
    labelled = to_label(questions, args.label, "pilot-labels")
    planted = mutations(questions, args.mutate, "pilot-mutations")
    (args.folder / "to_label.json").write_text(json.dumps(labelled, indent=1), encoding="utf-8")
    with (args.folder / "mutations.jsonl").open("w", encoding="utf-8") as out:
        for item, expected in planted:
            out.write(json.dumps({"question": item, "expected": expected}, ensure_ascii=False) + "\n")
    print(f"{args.folder}: {len(labelled)} to label blind, {len(planted)} mutations")
    if not args.model:
        return 0
    if args.budget <= 0:
        print("trialledger: refused (a model needs --budget, the most calls it may make)", file=sys.stderr)
        return 2
    where = args.folder / f"pilot-{args.model.replace(':', '_').replace('/', '_')}"
    where.mkdir(exist_ok=True)
    try:
        model = LocalModel(
            args.model,
            model_http or urllib_http,
            where / "answer_cache.jsonl",
            budget=args.budget,
            think=not args.no_think,
        )
        model.pin()
    except TransportError as error:
        print(f"trialledger: refused (model.{error.code})", file=sys.stderr)
        return 2
    chosen = set(labelled)
    asked = [q for q in questions if q["id"] in chosen] + [item for item, _ in planted]
    try:
        rows = answer_questions(model, asked)
    finally:
        model.release()
    with (where / "answers.jsonl").open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    answered = sum(row["code"] == "ok" for row in rows)
    print(f"{where}: {answered} answered, {len(rows) - answered} errors")
    return 0


def _audit(args, *, http, sleep, rxclass_get, model_http) -> int:
    from TrialLedger.audit import run_audit
    from TrialLedger.ingest import query_ids
    from TrialLedger.sample import SnapshotChanged
    from TrialLedger.transport import LocalModel, TransportError, urllib_http

    sample = json.loads(args.sample.read_text(encoding="utf-8"))
    model = None
    if args.model:
        if args.budget <= 0:
            print(
                "trialledger: refused (a model needs --budget, the most calls it may make)", file=sys.stderr
            )
            return 2
        try:
            model = LocalModel(
                args.model,
                model_http or urllib_http,
                args.out / "answer_cache.jsonl",
                budget=args.budget,
                think=not args.no_think,
            )
            model.pin()
        except TransportError as error:
            print(f"trialledger: refused (model.{error.code})", file=sys.stderr)
            return 2
    lookup = {"get": rxclass_get} if rxclass_get else {}
    cache = Path(os.environ.get("TRIALLEDGER_CACHE", str(rx.USER_CACHE)))

    def fetch(nct):
        return query_studies({"filter.ids": nct}, http=http, sleep=sleep)

    def classes_for(studies):
        return rx.load_or_lookup_at(cache, drug_aliases(studies), sleep=sleep, **lookup)

    def ids(query, progress):
        return query_ids(query, http=http, sleep=sleep, progress=progress)

    try:
        counts = run_audit(
            sample,
            args.out,
            fetch=fetch,
            classes_for=classes_for,
            model=model,
            limit=args.limit,
            query_ids=ids,
            progress=lambda m: print(m, file=sys.stderr),
        )
    except (PullError, SnapshotChanged) as error:
        print(f"trialledger: audit stopped — {error}", file=sys.stderr)
        return 1
    print(f"{args.out}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    return 0


def _resolve(args, *, http, sleep, rxclass_get) -> int:
    code, params, offending = parse_query_args(args.parameters)
    if code != "ok":
        print(f"trialledger: refused ({code}): {' '.join(offending)}", file=sys.stderr)
        return 2
    verdict, names = check_query(params)
    if verdict != "ok":
        print(
            f"trialledger: refused (query.{verdict}): {', '.join(names) or 'give at least one NAME=VALUE'}",
            file=sys.stderr,
        )
        return 2
    try:
        studies, api_version, data_timestamp = query_studies(
            params, http=http, sleep=sleep, progress=lambda message: print(message, file=sys.stderr)
        )
    except PullError as error:
        print(f"trialledger: nothing resolved — {error}", file=sys.stderr)
        return 1
    lookup = {"get": rxclass_get} if rxclass_get else {}
    cache = Path(os.environ.get("TRIALLEDGER_CACHE", str(rx.USER_CACHE)))
    # Both outputs of resolve (the JSON and design.xlsx) read the axes, so they are asked for here.
    answers = rx.load_or_lookup_at(
        cache, drug_aliases(studies), axes_aliases(studies), fill_axes=True, sleep=sleep, **lookup
    )
    reading = read_population(studies, answers)
    if args.out:
        sizes = write_book(args.out, reading, answers)
        print(
            f"{args.out} written ({len(studies)} studies; "
            + ", ".join(f"{k} {v}" for k, v in sizes.items())
            + " rows)",
            file=sys.stderr,
        )
    digests = [warrants.study_digest(study) for study in studies]
    basis = {
        "query": params,
        "api_version": api_version,
        "data_timestamp": data_timestamp,
        "study_digests": digests,
        "merkle_root": warrants.merkle_root(digests),
        "code_commit": code_commit(),
    }
    if args.keep:
        args.keep.write_text(json.dumps({**basis, "studies": studies}, ensure_ascii=False), encoding="utf-8")
    if args.json or not args.out:
        document = {**basis, "studies": symbolic_output(reading)}
        text = json.dumps(document, indent=1, ensure_ascii=False)
        if not args.json or args.json == "-":
            print(text)
        else:
            Path(args.json).write_text(text, encoding="utf-8")
    return 0


def _profile(
    folder: Path, rxclass_get: Callable[[str, dict[str, str]], tuple[int, Any]] | None, *, fill_axes: bool
) -> int:
    get = {"get": rxclass_get} if rxclass_get else {}
    if fill_axes:
        _fill_axes(folder, **get)
    try:
        target, sizes = write_design(folder, **get)
    except DesignError as error:
        print(f"trialledger: nothing written — {error}", file=sys.stderr)
        return 2 if error.code == "not_a_record" else 1
    counts = ", ".join(f"{name} {count}" for name, count in sizes.items())
    print(f"{target} written ({DESIGN_NAME}: {counts} rows); the pull's own files are unchanged")
    if not fill_axes:
        print(
            "drug axes read as cached in classes.json; any not yet asked are marked not_looked_up "
            "(trialledger profile --fill-axes asks RxNav for them)",
            file=sys.stderr,
        )
    return 0


def _fill_axes(folder: Path, get: Callable[[str, dict[str, str]], tuple[int, Any]] = rx.http_get) -> None:
    """`profile --fill-axes`: ask RxNav for the axes of the folder's experimental drug names not yet cached in
    its classes.json, only once its record verifies; a folder that is no record or does not verify is left
    as it is, for write_design to name."""
    from TrialLedger.record import record_problems

    try:
        record = json.loads((folder / JSON_NAME).read_text(encoding="utf-8"))
        studies = record["studies"]
    except (OSError, ValueError, KeyError, TypeError):
        return
    csv_path = folder / CSV_NAME
    if record_problems(record, csv_path.read_bytes() if csv_path.is_file() else None):
        return
    names = axes_aliases(studies)
    print(f"asking RxNav for the axes of up to {len(set(names))} names, spaced", file=sys.stderr)
    rx.load_or_lookup(folder, drug_aliases(studies), names, fill_axes=True, get=get)


def _verify(folder: Path) -> int:
    code, problems = verify_folder(folder)
    if code == "not_a_record":
        print(f"trialledger: not a TrialLedger record — {problems[0]}", file=sys.stderr)
        return 2
    if code == "not_certified":
        for problem in problems:
            print(f"trialledger: does not follow — {problem}", file=sys.stderr)
        print(
            f"trialledger: {folder} is NOT certified ({len(problems)} difference(s) shown)", file=sys.stderr
        )
        return 1
    print(
        f"{folder}: certified — every digest and root, every cell and warrant of both workbooks, and both "
        f"workbook files re-derive from {JSON_NAME}"
    )
    return 0
