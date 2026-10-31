"""The `trialledger` command: API parameters in; the record, the registry's spreadsheet and a certified review
workbook out. And `trialledger verify`, which re-derives a written folder from its record."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from TrialLedger import classes as rx
from TrialLedger.design import (
    DESIGN_NAME,
    DesignError,
    drug_aliases,
    symbolic_output,
    write_book,
    write_design,
)
from TrialLedger.ingest import SPEC_API_VERSION, PullError, check_query, pull, query_studies
from TrialLedger.record import CSV_NAME, JSON_NAME, verify_folder, write_record
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
            "every "
            "typed element against the folder's population. Writes design.xlsx and classes.json; the pull's "
            "files are not changed. Ends with 0, written; 1, the record does not verify (nothing written); "
            "2, "
            "not a TrialLedger folder."
        ),
    )
    profile_parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    if args.command == "resolve":
        return _resolve(args, http=http, sleep=sleep, rxclass_get=rxclass_get)
    if args.command == "verify":
        return _verify(args.folder)
    if args.command == "profile":
        return _profile(args.folder, rxclass_get)

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
    answers = rx.load_or_lookup_at(cache, drug_aliases(studies), sleep=sleep, **lookup)
    if args.out:
        sizes = write_book(args.out, studies, answers)
        print(
            f"{args.out} written ({len(studies)} studies; "
            + ", ".join(f"{k} {v}" for k, v in sizes.items())
            + " rows)",
            file=sys.stderr,
        )
    if args.json or not args.out:
        document = {
            "query": params,
            "api_version": api_version,
            "data_timestamp": data_timestamp,
            "studies": symbolic_output(studies, answers),
        }
        text = json.dumps(document, indent=1, ensure_ascii=False)
        if not args.json or args.json == "-":
            print(text)
        else:
            Path(args.json).write_text(text, encoding="utf-8")
    return 0


def _profile(folder: Path, rxclass_get: Callable[[str, dict[str, str]], tuple[int, Any]] | None) -> int:
    try:
        target, sizes = write_design(folder, get=rxclass_get) if rxclass_get else write_design(folder)
    except DesignError as error:
        print(f"trialledger: nothing written — {error}", file=sys.stderr)
        return 2 if error.code == "not_a_record" else 1
    counts = ", ".join(f"{name} {count}" for name, count in sizes.items())
    print(f"{target} written ({DESIGN_NAME}: {counts} rows); the pull's own files are unchanged")
    return 0


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
