"""The `trialledger` command: API parameters in, a local JSON record and a spreadsheet out."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from TrialLedger.ingest import SPEC_API_VERSION, PullError, check_query, pull
from TrialLedger.record import CSV_NAME, JSON_NAME, write_record

PULL_HELP = """\
Pull every ClinicalTrials.gov study a query matches, through the official API (spec/ctg-oas-v2.yaml),
into a new directory holding studies.json (the records exactly as the API sent them, plus provenance) and
studies.csv (the API's own spreadsheet for the same query). If anything fails, nothing is written.

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
) -> int:
    parser = argparse.ArgumentParser(
        prog="trialledger",
        description="Pull ClinicalTrials.gov study records into a local JSON record and a spreadsheet.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
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
    args = parser.parse_args(argv)

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
        write_record(result, out_dir)
    except OSError as error:
        print(f"trialledger: nothing written — {error}", file=sys.stderr)
        return 1
    print(
        f"{result.total_count} studies written to {out_dir}/ ({JSON_NAME}, {CSV_NAME}) — "
        f"ClinicalTrials.gov data as of {result.data_timestamp}, API {result.api_version}"
    )
    return 0
