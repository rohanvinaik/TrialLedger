"""The `trialledger` command. The user commands, which the guides name and `trialledger --help` lists first in
plain words for a clinical reader: `doctor` (what this sandbox can do), `landscape` (a request, or trials by
number, to the record and its workbook), `pull` (the registry's records saved with two certified workbooks)
and `verify` (a pulled folder re-derived from its record). The developer tools (`resolve`, `profile`,
`sample`, `audit`, `pilot`) run as before and are named under "for developers"."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from TrialLedger import classes as rx
from TrialLedger import warrants
from TrialLedger.design import DESIGN_NAME, DesignError, write_book, write_design
from TrialLedger.ingest import (
    SPEC_API_VERSION,
    PullError,
    check_query,
    pull,
    query_studies,
    requested_id_words,
)
from TrialLedger.reading import axes_aliases, drug_aliases, read_population
from TrialLedger.record import CSV_NAME, JSON_NAME, code_commit, verify_folder, write_record
from TrialLedger.request import PHASES, STATUSES, STUDY_TYPES
from TrialLedger.symbolic import symbolic_output
from TrialLedger.workbook import RECORD_NAME, WORKBOOK_NAME, WorkbookError

# The commands a person's assistant runs (the ones AGENTS.md and README.md name), listed first by
# `trialledger --help`; and TrialLedger's own testing and research tools, named under "for developers" and
# still runnable.
USER_COMMANDS = ("doctor", "landscape", "pull", "verify", "mcp")
DEVELOPER_COMMANDS = ("resolve", "profile", "sample", "audit", "pilot")

DESCRIPTION = """\
TrialLedger gathers every ClinicalTrials.gov study that matches a question about clinical trials (a drug, a
drug class, a disease, or trials by number) into a record an AI assistant answers from; a spreadsheet for
the person who asked is not built yet in this version (each run's last words say whether one was written).
Every value is a field of the registry's own record, or the result of a named, fixed rule over such fields,
and says which; no language model reads a trial. Start with `trialledger doctor`, then
`trialledger landscape`.
"""

DEVELOPER_EPILOG = """\
for developers (TrialLedger's own testing and research tools; not needed to gather or read trials):
  resolve   read a search's trials live into TrialLedger's internal reading and design.xlsx
  profile   read a folder `trialledger pull` saved into design.xlsx
  sample    draw a sample of trials for an audit of TrialLedger's readings
  audit     put targeted questions about a sample's readings to a local model
  pilot     the auditor pilot over an audit folder

Each command explains itself: trialledger <command> --help.
"""

DOCTOR_HELP = """\
Check, before the first run, what this computer or sandbox can do, and print a short report for the
assistant: the Python version and whether TrialLedger supports it, the packages TrialLedger needs, whether
clinicaltrials.gov, rxnav.nlm.nih.gov (the National Library of Medicine's drug vocabulary) and github.com
answer from here, and whether the run folder can be written. From those it names how a run will work here,
with the next step:
  direct  TrialLedger fetches from the registry and the drug vocabulary itself;
  relay   this sandbox cannot reach them, so the assistant fetches the web addresses TrialLedger names and
          saves each one where TrialLedger says;
or why no run can start here (an old Python, a missing package, a run folder that cannot be written).

What it changes: nothing that stays. Each website is asked one small question. To test the run folder it
writes one small file there and deletes it; a run folder that did not exist is created for the test and
removed again.

examples:
  trialledger doctor
  trialledger doctor --run egfr-nsclc

exit status: 0 a run can start here (direct or relay) · 2 no run can start here (the report says why and
what to do)
"""

PULL_HELP = """\
Save the registry's own records for a search, exactly as ClinicalTrials.gov sends them, into a new folder:
studies.json (every record as sent, with where and when it was fetched and a fingerprint of each record),
studies.csv (the registry's own spreadsheet for the same search, byte for byte), review.xlsx (each trial's
design, topic by topic, and the registry's edit checks) and record.xlsx (every value of every record, in the
registry's own categories). Every cell of both spreadsheets is checked against the records before the folder
is written, and `trialledger verify` checks the folder again later. If anything fails, nothing is written. A
spreadsheet larger than Google Sheets opens (10,000,000 cells) is named.

Use it when the person needs the registry's content itself, a value to cite or to copy into a protocol. To
answer a question about trials, run `trialledger landscape`.

Each search term is one of the registry's own search settings, written name=value, and sent as given (the
registry refuses a name it does not know): query.cond=asthma (a condition), filter.overallStatus=RECRUITING
(a status), filter.ids=NCT04852770,NCT01030536 (trials by number). Paging and format are set by TrialLedger.
Every trial asked for by number is accounted for in studies.json, and each one not found under its own
number is printed in plain words: another number of a trial the registry holds, not found, asked for twice,
or not a trial number.

examples:
  trialledger pull filter.ids=NCT04852770
  trialledger pull filter.ids=NCT04852770,NCT01030536 --out two-trials
  trialledger pull query.cond=sarcoidosis filter.overallStatus=RECRUITING
  trialledger pull "filter.advanced=AREA[StartDate]RANGE[2024-01-01,2024-01-31]" query.cond=asthma

exit status: 0 written · 1 the registry could not be read completely, or the folder could not be written;
nothing was written · 2 the search was refused (the words printed say why)
"""

VERIFY_HELP = """\
Check a folder that `trialledger pull` wrote: that every record in studies.json is exactly as it was saved
(each record's fingerprint, and one over them all), that studies.csv is unchanged, and that every cell of
review.xlsx and record.xlsx, and each file itself, is exactly what the same version of TrialLedger writes
from those records. Each difference is named. A folder written by another version of TrialLedger can be
checked only by that version, under any Python TrialLedger supports: the words printed name the commit to
install. A studies.json that holds one field twice in the same place is not certified (exit 1).

What it shows: that each value follows from the saved record by the code that wrote it. Not that the
registry is right, nor that a rule reads a criterion correctly.

example:
  trialledger verify trialledger_20261101T120000Z

exit status: 0 the folder checks out · 1 something no longer matches (each difference printed) · 2 not a
folder TrialLedger wrote (no readable studies.json)
"""

LANDSCAPE_HELP = """\
Gather every ClinicalTrials.gov study that matches a request, in one run, into a run folder (--run DIR):
landscape.json, the record an assistant answers from (every value with its status, its source and the
trial's registry link), with manifest.json beside it; and landscape.xlsx, the spreadsheet for the person
(the words printed at the end say whether it is there). Before any trial is read, the request's terms are
expanded through named sources and the expansion written to scope.json and resolution.json: a drug class into
its member drugs and every subclass it includes, each drug into every name RxNorm (the National Library of
Medicine's drug vocabulary) gives it, a disease class into the registry's own disease terms below it. A term
that cannot be expanded stops the run by name, with what to change; nothing is searched.

The request is the flags below, or a file (--request request.json) holding one object of the same fields:
  {"drug_class": {"name": "Kinase Inhibitor", "source": "EPC", "subclasses": "include"},
   "condition_class": "Lung Neoplasms", "phase": ["PHASE3"], "status": ["COMPLETED"]}
Each field is optional, but a request naming nothing is refused: drug (a list of names), drug_class (a name
or an id, its source EPC, MoA or ATC, and subclasses: "include", "exclude", or a list of the subclass ids to
leave out), mechanism, condition, condition_class, phase and status (lists of the registry's values),
study_type, start_from and start_to (YYYY-MM-DD), params (other registry search settings, name: value).

Trials by number: --ids NCT04852770,NCT01827384 (the same run and record as a search). Every number asked for
is accounted for in the record, and each one not found under its own number is printed in plain words:
another number of a trial the registry holds, not found, asked for twice, or not a trial number.

The run folder keeps everything fetched: running the same command again resumes, and a finished run run
again changes nothing. In direct mode TrialLedger fetches from the registry and the drug vocabulary itself,
and says how far its drug lookups have got. In relay mode, for a sandbox that cannot reach them, it writes
next.json, naming each web address to fetch and the file to save it as: fetch each one, save it unchanged,
then run the same command again, until it reports complete. In relay mode the drugs of the trials read are
not looked up for their classes, and the record says so. Unless --mode is given, the mode is what
`trialledger doctor` finds.

examples:
  trialledger landscape --run egfr-nsclc --drug-class "EGFR tyrosine kinase inhibitors" --class-source ATC \\
      --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED
  trialledger landscape --run my-trials --ids NCT04852770,NCT01827384,NCT01086644
  trialledger landscape --run asthma --request request.json --mode relay

exit status:
  0  complete: landscape.json is written
  3  waiting for the assistant (relay mode): fetch what next.json names, then run the same command again
  2  refused or stopped: the request, a term that cannot be expanded, a run folder that already holds
     another request, a fetched page that is not what it should be, or a computer or sandbox where no run
     can start (what `trialledger doctor` reports); the words printed say what to change
  1  failed: the registry or the drug vocabulary did not answer, or changed during the run; nothing was
     written as the record; the words printed say whether to run the same command again or to start a new
     run folder
"""

MCP_HELP = """\
Offer TrialLedger to an AI assistant app that runs local Model Context Protocol servers (Claude Desktop,
Claude Code, and the ChatGPT and Gemini apps that start one). The app starts this command itself and talks to
it; a person does not run it by hand. The assistant then has the same steps as tools: doctor (what this
computer can do), landscape (run or continue a search), save_fetch (save a page the assistant fetched for a
sandbox that cannot reach the registry, only where the run asks for it), scope (the search as resolved) and
record (the finished record, part by part, every value as the record holds it). Every run folder is a name
inside DIR, and nothing outside the run folders is read or written. The README shows how to add it to
Claude Desktop.

example:
  claude mcp add --scope user trialledger -- trialledger mcp --root ~/trialledger-runs

exit status: 0 the app closed the connection · 2 the command was given options it does not take
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


# The request slots `trialledger landscape` takes as flags of their own name, each as given.
FLAG_SLOTS = (
    "drug",
    "mechanism",
    "condition",
    "condition_class",
    "phase",
    "status",
    "study_type",
    "start_from",
    "start_to",
)


def request_from_flags(flags: dict[str, Any]) -> tuple[str, dict[str, Any], list[str]]:
    """The request that `trialledger landscape`'s slot flags state (pure — pinned).

    `flags` holds each flag's value as argparse gives it, None (or an empty list) when the flag is not
    given. Each slot of FLAG_SLOTS given is the request's slot, as given; --drug-class (a name),
    --drug-class-id (an id) and --class-source (EPC, MoA or ATC) make the drug_class object, holding only
    those given (request.request_problems refuses one without a source, or with both a name and an id);
    the --param NAME=VALUE words are the raw params, read as parse_query_args reads them; the --ids values
    (trials by number) are one more such word, filter.ids, their values joined by "," as given (the registry
    takes a comma-separated list; ingest.reconcile_ids accounts for each number, a malformed one included).
      "ok"                    — the request (empty when no flag is given, which request_problems refuses).
      "params_not_name_value" — a --param word with no "=" or nothing before it: no request.
      "params_duplicate"      — a --param name given more than once, filter.ids beside --ids among them: no
                                request.
    Returns (code, the request, the --param words concerned).
    """
    request: dict[str, Any] = {
        slot: flags[slot] for slot in FLAG_SLOTS if flags.get(slot) is not None and flags.get(slot) != []
    }
    named = (("name", "drug_class"), ("id", "drug_class_id"), ("source", "class_source"))
    drug_class = {key: flags[flag] for key, flag in named if flags.get(flag) is not None}
    if drug_class:
        request["drug_class"] = drug_class
    words = list(flags.get("param") or [])
    if flags.get("ids"):
        words.append("filter.ids=" + ",".join(flags["ids"]))
    if words:
        code, params, offending = parse_query_args(list(words))
        if code != "ok":
            return f"params_{code}", {}, offending
        request["params"] = params
    return "ok", request, []


def main(
    argv: list[str] | None = None,
    *,
    http: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rxclass_get: Callable[[str, dict[str, str]], tuple[int, Any]] | None = None,
    model_http: Callable[..., Any] | None = None,
    git: Callable[..., str] | None = None,
    ledger: Path | None = None,
    probe_get: Callable[..., Any] | None = None,
    mcp_streams: tuple[Iterable[bytes], Callable[[str], None]] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="trialledger",
        description=DESCRIPTION,
        epilog=DEVELOPER_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # The user commands are added first, each with its help line; a developer tool is added with no help
    # line, so it runs and appears in the usage line but is listed only under "for developers".
    commands = parser.add_subparsers(dest="command", required=True, title="commands")
    doctor_parser = commands.add_parser(
        "doctor",
        help="check what this computer or sandbox can do, before the first run",
        description=DOCTOR_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    doctor_parser.add_argument(
        "--run",
        type=Path,
        default=Path("trialledger_run"),
        metavar="DIR",
        help="the run folder to test: give the --run you will give `trialledger landscape` "
        "(default: ./trialledger_run)",
    )
    landscape_parser = commands.add_parser(
        "landscape",
        help="gather every trial matching a request, or trials by number, into a record to answer from",
        description=LANDSCAPE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    landscape_parser.add_argument(
        "--run",
        type=Path,
        required=True,
        metavar="DIR",
        help="the run folder, created if absent; the same command run again resumes it",
    )
    landscape_parser.add_argument(
        "--request", type=Path, metavar="FILE", help="the request as a file of the fields below, not flags"
    )
    landscape_parser.add_argument(
        "--ids",
        action="append",
        default=[],
        metavar="NCT,...",
        help="trials by number, separated by commas (repeat to add more)",
    )
    landscape_parser.add_argument(
        "--drug",
        action="append",
        default=[],
        help="a drug's name, searched by every name RxNorm gives it (repeat for each)",
    )
    landscape_parser.add_argument(
        "--drug-class", help="a drug class by name, with every subclass it includes (with --class-source)"
    )
    landscape_parser.add_argument("--drug-class-id", help="a drug class by its id (with --class-source)")
    landscape_parser.add_argument(
        "--class-source",
        help="the drug class's source: EPC (the FDA's Established Pharmacologic Classes), MoA (MED-RT's "
        "mechanisms of action) or ATC (the WHO's Anatomical Therapeutic Chemical classes)",
    )
    landscape_parser.add_argument(
        "--mechanism", help="a drug target, such as PD-1, through TrialLedger's sourced table of ATC classes"
    )
    landscape_parser.add_argument(
        "--condition", help="a condition, searched by the registry's own condition search"
    )
    landscape_parser.add_argument(
        "--condition-class", help="a disease class (a MeSH term), with every disease below it"
    )
    landscape_parser.add_argument(
        "--phase", action="append", default=[], help=f"a phase, one of {', '.join(PHASES)} (repeat)"
    )
    landscape_parser.add_argument(
        "--status", action="append", default=[], help=f"a status, one of {', '.join(STATUSES)} (repeat)"
    )
    landscape_parser.add_argument("--study-type", help=f"a study type, one of {', '.join(STUDY_TYPES)}")
    landscape_parser.add_argument("--start-from", help="the earliest start date, YYYY-MM-DD")
    landscape_parser.add_argument("--start-to", help="the latest start date, YYYY-MM-DD")
    landscape_parser.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="SETTING",
        help="another registry search setting, written name=value, such as query.term=biomarker (repeat)",
    )
    landscape_parser.add_argument(
        "--mode",
        choices=("direct", "relay"),
        help="direct, or relay for a sandbox that cannot reach the registry (default: what `trialledger "
        "doctor` finds)",
    )
    pull_parser = commands.add_parser(
        "pull",
        help="save the registry's own records for a search, with two checked spreadsheets",
        description=PULL_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pull_parser.add_argument(
        "parameters", nargs="*", metavar="SEARCH", help="a search setting, written name=value (see above)"
    )
    pull_parser.add_argument(
        "--out",
        type=Path,
        metavar="FOLDER",
        help="the folder to create, which must not exist yet (default: ./trialledger_<UTC time>)",
    )
    verify_parser = commands.add_parser(
        "verify",
        help="check that a folder pull saved is unchanged and still follows from its records",
        description=VERIFY_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    verify_parser.add_argument(
        "folder", type=Path, metavar="FOLDER", help="a folder `trialledger pull` wrote"
    )
    mcp_parser = commands.add_parser(
        "mcp",
        help="serve doctor, landscape, save_fetch, scope and record to an assistant over MCP (stdio)",
        description=MCP_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mcp_parser.add_argument(
        "--root",
        type=Path,
        default=None,
        metavar="DIR",
        help="the folder the run folders are made in (default ~/trialledger-runs)",
    )
    resolve_parser = commands.add_parser(
        "resolve",
        description=(
            "For developers. Query ClinicalTrials.gov live (the same parameters as pull, one snapshot, "
            "complete or nothing), and resolve every matching study to its symbolic reading: typed "
            "criteria, design coordinates, drug classes, outcomes and expectation observations. Nothing of "
            "the registry's record is saved. RxNav's answers are cached in "
            "~/.cache/trialledger/classes.json, or where TRIALLEDGER_CACHE says: a folder (classes.json is "
            "kept inside it) or a file. It names a folder when that folder already exists or the path ends "
            'in "/" (the folder is then created); any other path is the cache file itself. Its RxNav '
            "lookups say how far they have got every five names. "
            "Writes design.xlsx with --out, the reading as JSON with --json (a path, or - for standard "
            "output; the default). Ends with 0, resolved; 1, the query failed; 2, the query was refused."
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
    profile_parser = commands.add_parser(
        "profile",
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
        description=(
            "Fetch, live and from one registry snapshot, the NCT IDs of interventional trials started "
            "from 2010-01-01 to the present (today's UTC date, or --present; recorded in the file) in each "
            "top-level condition category (the registry's derived condition MeSH, a label "
            "for spread only) and among trials with no condition MeSH; draw a seeded random sample within "
            "each stratum from the discovery pool (a hash of the NCT ID reserves 30% for confirmation, "
            "never drawn here); write the strata, pool sizes, draws, memberships and inclusion probabilities"
            " as JSON, with the declared balance check (phase, intervention type, primary purpose) and its "
            "seeded supplement, which the audit applies. With --confirmation-batch N, draw instead from that "
            "one confirmation batch (sha256 mod 10 equal to N, of 0, 1, 2: one batch per release, never "
            "reused for a revised version), recorded in the file with the code's commit and source digest, "
            "and declare no supplement. A confirmation draw needs TrialLedger/ and tests/ clean at a commit, "
            "every inspected population declared with --inspected (a sample.json, an audit's balance.json, "
            "or a record folder or its studies.json: the NSCLC record, the pilot and discovery samples), "
            "whose trials it never draws. It consults the declared ledger of batches used, "
            "confirmation_ledger.json at the code's root (each batch with the source digest and commit of "
            "the code it confirmed), then records this batch there and commits the ledger alone. Ends with "
            "0, written; 1, the registry query failed, or the ledger was recorded but not committed; 2, "
            "refused (a batch not declared, code not clean at a commit, no or an empty inspected list, an "
            "unreadable ledger, or a batch already used for other code)."
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
    audit_parser = commands.add_parser(
        "audit",
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
    if args.command == "doctor":
        return _doctor(args.run, probe_get)
    if args.command == "landscape":
        return _landscape(args, http=http, sleep=sleep, rxclass_get=rxclass_get, probe_get=probe_get)
    if args.command == "mcp":
        return _mcp(
            args.root,
            http=http,
            sleep=sleep,
            rxclass_get=rxclass_get,
            probe_get=probe_get,
            streams=mcp_streams,
        )
    if args.command == "pilot":
        return _pilot(args, model_http=model_http)
    if args.command == "sample":
        return _sample(args, http=http, sleep=sleep, git=git, ledger=ledger)
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
            f"trialledger: note — the registry reports its interface version {result.api_version}; this "
            f"TrialLedger was written for version {SPEC_API_VERSION}",
            file=sys.stderr,
        )
    for entry in result.requested_ids:
        if entry["status"] != "found":
            print(f"trialledger: {requested_id_words(entry)}", file=sys.stderr)
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


def _doctor(folder: Path, probe_get: Callable[..., Any] | None) -> int:
    from TrialLedger.doctor import report

    found = report(folder, probe_get)
    print(json.dumps(found, indent=1))
    return 0 if found["mode"] in ("direct", "relay") else 2


def _landscape(args, *, http, sleep, rxclass_get, probe_get) -> int:
    """`trialledger landscape`: the request from --request or the slot flags, the mode from --mode or the
    doctor, the run (operate.run), and its end in plain words."""
    from TrialLedger.doctor import NEXT_STEP, report
    from TrialLedger.operate import Outcome, run, run_exit

    code, request, offending = request_from_flags(vars(args))
    outcome: Outcome | None = None
    if args.request is not None:
        flagged = code != "ok" or bool(request)
        request = _read_json(args.request)
        if flagged:
            words = "Give the request either as --request FILE or as flags (--drug, --ids, ...), not both."
            outcome = Outcome("request_refused", "request_and_flags", words)
        elif request is None:
            words = "The request file cannot be read as JSON: write the request as one JSON object of slots."
            outcome = Outcome("request_refused", f"request_unreadable: {args.request}", words)
    elif code != "ok":
        words = (
            "Each --param is one registry search setting, written name=value, each name once; --ids sets "
            "filter.ids, so trials by number are given there and not also as a --param."
        )
        outcome = Outcome("request_refused", f"{code}: {' '.join(offending)}", words)
    mode = args.mode
    if outcome is None and mode is None:
        mode = report(args.run, probe_get)["mode"]
        if mode not in ("direct", "relay"):
            outcome = Outcome("mode_unavailable", mode, NEXT_STEP[mode])
    if outcome is None:
        outcome = run(
            args.run,
            request,
            mode,
            get=rxclass_get or rx.http_get,
            http=http,
            sleep=sleep,
            progress=lambda message: print(message, file=sys.stderr),
        )
    code_ = run_exit(outcome.status)
    stream = sys.stdout if code_ in (0, 3) else sys.stderr
    print(f"trialledger landscape: {outcome.status} (exit {code_}) — run folder {args.run}", file=stream)
    if outcome.detail:
        print(outcome.detail, file=stream)
    print(outcome.advice, file=stream)
    return code_


def _mcp(root: Path | None, *, http, sleep, rxclass_get, probe_get, streams) -> int:
    """`trialledger mcp`: the MCP server over the process's standard input and output (or the streams
    given), every run folder inside `root`, until the client closes the connection."""
    from TrialLedger.mcp_server import DEFAULT_ROOT, Context, serve, stdio_streams

    lines, write = streams or stdio_streams()
    context = Context(
        root or DEFAULT_ROOT, get=rxclass_get or rx.http_get, http=http, sleep=sleep, probe_get=probe_get
    )
    serve(lines, write, context)
    return 0


def _sample(args, *, http, sleep, git, ledger) -> int:
    from TrialLedger.ingest import query_ids
    from TrialLedger.sample import (
        BASE_FROM,
        LEDGER_NAME,
        PACKAGE_ROOT,
        SnapshotChanged,
        batch_request,
        code_state,
        draw_sample,
        git_query,
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
    ledger_path: Path = ledger or PACKAGE_ROOT / LEDGER_NAME
    document: Any = None
    state: dict[str, Any] = {}
    if batch is not None:
        state = code_state(git=git)
        inspected = [_inspected_list(path) for path in args.inspected]
        document = _read_json(ledger_path)
        used = ledger_batches(document)
        commit = state["commit"]
        counts = [len(i["ncts"]) for i in inspected]
        verdict = batch_request(batch, commit, state["source_digest"], state["dirty"], counts, used)
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
            "batch_ledger": str(ledger_path),
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
        entry = {"source_digest": state["source_digest"], "commit": commit}
        retired = {**document, "batches": {**document["batches"], str(batch): entry}}
        ledger_path.write_text(json.dumps(retired, indent=1) + "\n", encoding="utf-8")
        message = (
            f"Confirmation batch {batch} used for code {commit[:12]} (source {entry['source_digest'][:12]})"
        )
        try:
            (git or git_query)(ledger_path.parent, "commit", "-m", message, "--", ledger_path.name)
        except (OSError, subprocess.CalledProcessError) as error:
            print(
                f"trialledger: {args.out} written and batch {batch} recorded in {ledger_path}, but the "
                f"ledger was not committed ({error}); commit it before any other draw",
                file=sys.stderr,
            )
            return 1
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
    cache = rx.cache_path()

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
    # Both outputs of resolve (the JSON and design.xlsx) read the axes, so they are asked for here, saying how
    # far they have got.
    answers = rx.load_or_lookup_at(
        rx.cache_path(),
        drug_aliases(studies),
        axes_aliases(studies),
        fill_axes=True,
        sleep=sleep,
        progress=lambda message: print(message, file=sys.stderr),
        **lookup,
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
        f"{folder}: certified — every record of {JSON_NAME} and {CSV_NAME} is as saved, and every cell of "
        "both spreadsheets, and each file itself, is what this version of TrialLedger writes from them"
    )
    return 0
