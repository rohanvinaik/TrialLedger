"""Clinical reference reports and separate symbolic reasoning over typed premises."""

from __future__ import annotations

import argparse
import functools
import json
import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import httpx

from TrialLedger import classes as rx
from TrialLedger.ingest import (
    SPEC_API_VERSION,
    PullError,
    check_query,
    pull,
    requested_id_words,
)
from TrialLedger.record import CSV_NAME, JSON_NAME, verify_folder, write_record
from TrialLedger.request import PHASES, STATUSES, STUDY_TYPES
from TrialLedger.workbook import RECORD_NAME, WORKBOOK_NAME, WorkbookError

# The public commands the assistant can run, in the same order as the guides and command help.
USER_COMMANDS = ("doctor", "landscape", "pull", "verify", "mcp", "reason")

DESCRIPTION = """\
TrialLedger gathers every ClinicalTrials.gov study that matches a question about clinical trials (a drug, a
drug class, a disease, or trials by number) into a record an AI assistant answers from and a spreadsheet
for the person who asked, every trial's dossier and the listings that compare them.
Every value is a field of the registry's own record, or the result of a named, fixed rule over such fields,
and says which; no language model supplies the trial facts. Your assistant answers from that saved record.
Start with `trialledger doctor`, then
`trialledger landscape`.

Layer one is mechanical: request specific trials or a subset, and receive a clinical reference spreadsheet
and matching evidence record for your assistant, containing registry facts and direct derivations only.
Layer two is symbolic reasoning about trial design. Your assistant restates your criteria and questions as
premises you confirm; the reason operation then computes whether something is required, ruled out,
contradictory, or allowed but not required, with the criterion that decides it. It also narrows NSCLC
settings and computes how common, unusual or patterned criteria are across trials you choose. Ask reason
for its describe operation to discover the supported inputs, answer guide and a worked session. The
complete automated trial writer is designed and partly built; its brief-to-protocol workflow is not yet
integrated.
"""

DEVELOPER_EPILOG = "Each command explains itself: trialledger <command> --help."

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
Check a folder that `trialledger landscape` wrote by replaying its retained registry records, drug answers
without contacting a service. The input fingerprints, code version, full
clinical record, and workbook (including formatting and links) must agree. Changed or missing evidence is
named; it is never fetched or repaired. Earlier landscape folders without retained lookup evidence cannot
pass this check: use their writing version or gather a new run.

Check a folder that `trialledger pull` wrote: that every record in studies.json is exactly as it was saved
(each record's fingerprint, and one over them all), that studies.csv is unchanged, and that every cell of
review.xlsx and record.xlsx, and each file itself, is exactly what the same version of TrialLedger writes
from those records. Each difference is named. A folder written by another version of TrialLedger can be
checked only by that version, under any Python TrialLedger supports: the words printed name the commit to
install. A studies.json that holds one field twice in the same place is not certified (exit 1).

What it shows: that each value follows from the saved record by the code that wrote it. Not that the
registry is right, nor that a rule reads a criterion correctly.

example:
  trialledger verify my-trials
  trialledger verify trialledger_20261101T120000Z

exit status: 0 the folder checks out · 1 something no longer matches (each difference printed) · 2 not a
folder TrialLedger wrote (no readable studies.json)
"""

LANDSCAPE_HELP = """\
Gather every ClinicalTrials.gov study that matches a request, in one run, into a run folder (--run DIR):
landscape.json, the record an assistant answers from, with manifest.json beside it; copied registry values
are stored as given, their sources defined once in the field dictionary, while rule readings and missing
values carry their status and explanation. Each trial has its registry link. landscape.xlsx is the
spreadsheet for the person (every
trial's dossier and the listings that compare them, checked cell by cell against the record). Before any trial
is read, the request's terms are expanded through named sources and the expansion written to scope.json and
resolution.json: a drug class into its member drugs and every subclass it includes, each drug into every name
RxNorm (the National Library of Medicine's drug vocabulary) gives it, a disease class into the registry's own
disease terms below it. A term that cannot be expanded stops the run by name, with what to change; nothing is
searched.

To see the search before anything is gathered, add --preview: the request is resolved and the search written
to the run folder exactly as above, then it is shown in plain words (each drug class with its subclasses and
the member drugs searched, each drug with the names it is searched by, each disease class, the other filters
and the exact search sent to the registry), and no trial is read. Show it to the person. Running the same
command again without --preview then gathers exactly that search; a changed request needs a new run folder.

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
not looked up for their classes, and the record says so. Registry conditions and MeSH are copied as given.
Unless --mode is given, the mode is what `trialledger doctor` finds.

examples:
  trialledger landscape --run egfr-nsclc --drug-class-id L01EB --class-source ATC \\
      --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED
  trialledger landscape --run my-trials --ids NCT04852770,NCT01827384,NCT01086644
  trialledger landscape --run asthma --request request.json --mode relay
  trialledger landscape --run kinase --drug-class "Kinase Inhibitor" --class-source EPC --preview

exit status:
  0  complete: landscape.json is written (with --preview: the search is resolved and shown; nothing gathered)
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
record (the finished record, part by part, every value as the record holds it). The separate reason tool
evaluates explicitly structured premises; first ask it for {"operation":"describe"} to receive formats and
runnable examples. It never alters a report. Every run folder is a name
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
    probe_get: Callable[..., Any] | None = None,
    mcp_streams: tuple[Iterable[bytes], Callable[[str], None]] | None = None,
) -> int:
    parser = argparse.ArgumentParser(
        prog="trialledger",
        description=DESCRIPTION,
        epilog=DEVELOPER_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Every public command has its own clinical purpose, usage and exit-code explanation.
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
        help="gather every trial matching a request, or trials by number, into a record and a spreadsheet",
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
        help="a drug name, with its canonical RxNorm name and sourced product names (repeat)",
    )
    landscape_parser.add_argument(
        "--drug-class",
        help="a drug class by name (use --drug-class-id for an ID); "
        "unresolved names offer source-catalogue choices",
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
    landscape_parser.add_argument(
        "--preview",
        action="store_true",
        help="resolve the request and show the search in plain words, reading no trial; run again without "
        "it to gather",
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
        help="check that a saved landscape or pull folder still follows from its retained sources",
        description=VERIFY_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    verify_parser.add_argument(
        "folder", type=Path, metavar="FOLDER", help="a folder `trialledger landscape` or `pull` wrote"
    )
    mcp_parser = commands.add_parser(
        "mcp",
        help="serve trial reference reports and separate reasoning to an assistant over MCP (stdio)",
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
    reason_parser = commands.add_parser(
        "reason",
        help="layer two: check design requirements and explore comparable-trial patterns",
        description=(
            "Check what your confirmed design premises require, rule out or leave as your call, and "
            "whether they contradict each other; narrow explicit NSCLC design choices; or compute how often "
            "represented criteria occur, how unusual they are, possible gaps and pairs of trials differing "
            "in one declared feature; or bound missing eligibility restrictions using baseline witnesses "
            "and explicit eligibility bridges. Undetermined is exact (allowed but not required, or a named "
            "reason), not a failure. Your assistant prepares the structured premises and explains their "
            "sources and limits. "
            "The operations evaluate supplied scoped assertions, explicit NSCLC design coordinates "
            "or a typed trial corpus. "
            "No trial text is interpreted. This is working symbolic logic; the complete trial writer is "
            'designed but its integration is unfinished. First put {"operation":"describe"} in the '
            "request file for an overview. Add view entailment, coordinates, corpus or design_bounds for "
            "that operation's "
            "exact formats, answer guide and runnable example; view worked_session or full gives the "
            "complete demonstration or manual.\n\n"
            "example: trialledger reason --request premises.json\n\n"
            "exit status: 0 evaluated (the logical result may be undetermined); 2 request refused"
        ),
    )
    reason_parser.add_argument("--request", type=Path, required=True, metavar="FILE")
    args = parser.parse_args(argv)
    if args.command == "reason":
        return _reason(args.request)
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
    if args.command == "verify":
        return _verify(args.folder)

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
    from TrialLedger.preview import preview

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
    say = functools.partial(print, file=sys.stderr)
    if outcome is None and args.preview:
        outcome = preview(args.run, request, mode, get=rxclass_get or rx.http_get, sleep=sleep, progress=say)
    elif outcome is None:
        outcome = run(
            args.run, request, mode, get=rxclass_get or rx.http_get, http=http, sleep=sleep, progress=say
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


def _verify(folder: Path) -> int:
    if (folder / "landscape.json").is_file():
        from TrialLedger.landscape_verify import verify_landscape

        code, problems = verify_landscape(folder)
        if code != "verified":
            for problem in problems:
                print(f"trialledger: {code} — {problem}", file=sys.stderr)
            return 1
        print(
            f"{folder}: verified — the clinical record and workbook reproduce from the retained sources. "
            "This checks derivation, not clinical interpretation."
        )
        return 0
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


def _reason(path: Path) -> int:
    from TrialLedger.landscape_verify import strict_json
    from TrialLedger.layer2 import run
    from TrialLedger.record import DuplicateKey

    try:
        request = strict_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, DuplicateKey) as error:
        print(f"trialledger reason: unreadable request — {error}", file=sys.stderr)
        return 2
    result = run(request)
    print(json.dumps(result, ensure_ascii=False, indent=1, allow_nan=False))
    return 0 if result["code"] == "complete" else 2
