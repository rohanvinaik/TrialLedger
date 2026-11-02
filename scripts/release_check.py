"""Install and exercise the current TrialLedger candidate in a fresh user environment.

The default source is this checkout as it stands, including uncommitted package changes; a repository or
archive address can also be supplied. A fresh Python 3.12 environment installs the source with pip and uv.
The script reads public help, checks doctor, gathers and verifies the archival and ordinary reference
outputs for requested identifiers, and runs a separately supplied typed symbolic premise through reason.
It never calls the retired raw clinical readers or claims a complete new protocol was produced.

Each step retains its complete output, exit, timing, warnings and written files. Checks compare installed
package files against the current source candidate, expected report artifacts, requested-ID accounting,
guide commands, basic workbook conventions and the conditional reasoning result. Missing checks are not
passes. Full clinical readability and independent source-to-cell fidelity remain separate acceptance work.

It writes only inside the chosen work directory, outside the repository. Registry and vocabulary calls are
live; run it on a machine that reaches those services. No push or publication is requested.

    python3 scripts/release_check.py
    python3 scripts/release_check.py git+https://github.com/<owner>/TrialLedger
    python3 scripts/release_check.py --work /tmp/tl-release

Exit 0 means ready for the checks actually performed, 1 not ready, 2 a refused source/work directory.
Read WORK/REPORT.md and the complete captures beside it; readiness is not clinical certification.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

REPOSITORY = Path(__file__).resolve().parents[1]
PYTHON = "3.12"
# The pull asks for three trials by number. NCT01086644 is not a trial's own number: the registry answers it
# with the trial that lists it among its aliases (NCT01030536 when last checked), so the accounting must name
# it.
PULL_IDS = ("NCT04852770", "NCT01827384", "NCT01086644")
STEP_TIMEOUT_S = 1800
FOLDER = -1  # the size a folder is listed with among the files a step wrote
ARCHIVE_SUFFIXES = (".zip", ".tar.gz", ".tgz", ".whl")
TRACEBACK = "Traceback (most recent call last)"
WARNING = re.compile(r"\w*warning\b", re.IGNORECASE)
# Words in the CLI's printed text that a clinical reader (not a programmer) would not know. A fixed list, read
# from the help texts and messages as they stood on 2026-11-01; each hit is a lead for the wording, not a
# fault.
JARGON = (
    "JSON",
    "API",
    "NAME=VALUE",
    "query.*",
    "filter.*",
    "Merkle root",
    "digest",
    "digests",
    "warrant",
    "warranted",
    "code root",
    "re-derive",
    "derivation",
    "symbolic",
    "standard output",
    "TRIALLEDGER_CACHE",
    "relay",
    "Ollama",
    "RxClass",
    "RxNav",
    "SHA-256",
    "sha256",
    "seeded",
    "stratum",
    "strata",
    "envelope",
    "jsonl",
    "axes",
    "not_looked_up",
    "coordinates",
    "typed",
    "spec/ctg-oas-v2.yaml",
    # A status code, which the printed words say plainly ("<number> is another number of <trial>").
    "aliased",
    # Column headings of the workbooks a first-time user is handed.
    "Warrant",
    "Atoms",
    "Founder",
)
# A step's verdicts that let the release go out: a warning is reported, never hidden, but blocks nothing.
PASSING = ("as_expected", "warned")
# The landscape's run folder, relative to the folder the commands run in.
LANDSCAPE_RUN = "landscape-run"
# What the archival pull and ordinary reference report hand the user.
EXPECTED_OUTPUTS = (
    "pulled/studies.json",
    "pulled/studies.csv",
    "pulled/review.xlsx",
    "pulled/record.xlsx",
    f"{LANDSCAPE_RUN}/landscape.json",
    f"{LANDSCAPE_RUN}/landscape.xlsx",
)
# Original archival listing conventions; ordinary report formatting is checked by its own verifier and
# inspected below as presentation evidence, without treating a dossier as a filtered listing.
HELD_WORKBOOKS = ("pulled/review.xlsx", "pulled/record.xlsx")
# Run by the fresh environment's own Python (openpyxl is a TrialLedger dependency): for each workbook named,
# each sheet's size, whether any column width is set, its filter and frozen panes, the blank cells below its
# header row, and its text (every sheet's header row; the first sheet, the read-me, whole).
INSPECTOR = """
import json, sys
import openpyxl

def words(row):
    return " ".join(str(value) for value in row if isinstance(value, str))

found = {}
for path in sys.argv[1:]:
    book = openpyxl.load_workbook(path)
    sheets = []
    for position, sheet in enumerate(book.worksheets):
        rows = list(sheet.iter_rows(values_only=True))
        sheets.append({
            "sheet": sheet.title,
            "rows": sheet.max_row,
            "columns": sheet.max_column,
            "widths": any(d.customWidth for d in sheet.column_dimensions.values()),
            "filtered": bool(sheet.auto_filter.ref),
            "frozen": sheet.freeze_panes is not None,
            "blanks": sum(1 for row in rows[1:] for value in row if value is None or value == ""),
            "text": "\\n".join(words(row) for row in (rows if position == 0 else rows[:1])),
        })
    found[path] = sheets
print(json.dumps(found))
"""


def install_spec(source: str, is_dir: bool) -> tuple[str, str]:
    """How pip is given the source to install, as a named code and pip's argument (pure — pinned).

    path           — a local directory, installed from its working tree as it stands (untracked files too);
    vcs_url        — an address already written for pip ("git+https://..."), as given;
    repository_url — an https address of a repository: pip installs it only as "git+<address>", so that is
                     what it is given (a repository's page address alone is not something pip can install);
    archive_url    — an https address of a .zip, .tar.gz, .tgz or .whl, as given;
    not_a_source   — anything else, refused, with no argument: pip would read it as a package name on PyPI.
    """
    if is_dir:
        return "path", source
    if source.startswith("git+"):
        return "vcs_url", source
    if source.startswith("https://"):
        if source.endswith(ARCHIVE_SUFFIXES):
            return "archive_url", source
        return "repository_url", "git+" + source
    return "not_a_source", ""


def clone_source(spec: str) -> tuple[str, str]:
    """The address git clones and the revision it checks out, from pip's repository argument (pure — pinned).

    pip's "git+" prefix is dropped and so is a "#" fragment (egg=, subdirectory=); the revision is what
    follows the last "@" of the address's path, as pip reads it ("https://host/o/TrialLedger@v0.1" names
    v0.1), never an "@" of its host part ("ssh://git@host/o/TrialLedger" names none). No revision: "".
    """
    address = spec.removeprefix("git+").partition("#")[0]
    parts = urlsplit(address)
    if "@" not in parts.path:
        return address, ""
    path, _, revision = parts.path.rpartition("@")
    return urlunsplit(parts._replace(path=path)), revision


def captured_text(value: bytes | str | None) -> str:
    """A step's captured output as text, in whichever form subprocess hands it over (pure — pinned).

    A str as given; bytes (what TimeoutExpired holds, even for a run that asked for text) decoded as UTF-8,
    each byte that is not UTF-8 replaced by U+FFFD; None, nothing captured, "".
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def subcommand_names(help_text: str) -> tuple[str, ...]:
    """The subcommands a --help text lists, in its own order (pure — pinned).

    argparse writes them as the first "{a,b,...}" group of the usage line; a text without one lists none, ().
    """
    match = re.search(r"\{([a-z][a-z0-9,-]*)\}", help_text)
    return tuple(match.group(1).split(",")) if match else ()


def output_findings(text: str) -> tuple[tuple[str, str], ...]:
    """Each line of a step's printed output that a release must not hide, with its kind (pure — pinned).

    "traceback" — the line Python starts an uncaught exception's report with;
    "warning"   — a line naming a warning (a word ending in "warning", any case: UserWarning, WARNING:).
    Every other line is nothing; the lines keep their order and their words, stripped of surrounding space.
    """
    found: list[tuple[str, str]] = []
    for line in text.splitlines():
        if TRACEBACK in line:
            found.append(("traceback", line.strip()))
        elif WARNING.search(line):
            found.append(("warning", line.strip()))
    return tuple(found)


def step_verdict(expected: int, actual: int | None, kinds: tuple[str, ...]) -> str:
    """One step's verdict from its expected exit code, its actual one and its findings' kinds (pure — pinned).

    timed_out       — the step did not end within its time limit (no exit code);
    unexpected_exit — it ended with another code than the one a first-time user should see;
    traceback       — it ended as expected but printed a traceback;
    warned          — it ended as expected and printed a warning, and no traceback;
    as_expected     — it ended as expected and printed neither.
    """
    if actual is None:
        return "timed_out"
    if actual != expected:
        return "unexpected_exit"
    if "traceback" in kinds:
        return "traceback"
    if "warning" in kinds:
        return "warned"
    return "as_expected"


def missing_package_files(tracked: tuple[str, ...], installed: tuple[str, ...]) -> tuple[str, ...]:
    """The package's tracked files the install did not put in place, sorted (pure — pinned).

    Both are paths relative to the package's parent, "/"-separated ("TrialLedger/registry/ctg-enums.json"), as
    `git ls-files` and `importlib.metadata.files` write them; an installed file nothing tracks (a compiled
    module, the distribution's metadata) is no gap. None missing: ().
    """
    return tuple(sorted(set(tracked) - set(installed)))


def outputs_missing(expected: tuple[str, ...], present: tuple[str, ...]) -> tuple[str, ...]:
    """The outputs a first-time user should be handed that are not there, in expected's order (pure — pinned).

    Both are paths relative to the folder the commands ran in, "/"-separated ("pulled/review.xlsx"); a present
    file nobody expected is no gap. All there: ().
    """
    return tuple(path for path in expected if path not in present)


def reason_problems(answer: Any) -> tuple[str, ...]:
    """Check the supplied population example through the installed public reasoning operation.

    A completed entailment must refute male membership under the explicit female-only premise and name
    that premise. This checks conditional logic, never a registry finding. Malformed, refused or unsupported
    responses, a different decision, or a lost proof each have a distinct named problem.
    """
    if not isinstance(answer, dict):
        return ("reason_response_not_an_object",)
    if answer.get("code") != "complete" or answer.get("operation") != "entailment":
        return ("reason_operation_incomplete",)
    result = answer.get("result")
    decision = result.get("decision") if isinstance(result, dict) else None
    if not isinstance(decision, dict):
        return ("reason_decision_missing",)
    if decision.get("result") != "REFUTED":
        return ("reason_wrong_decision",)
    proof = decision.get("proof")
    if not isinstance(proof, list) or "population" not in proof:
        return ("reason_premise_missing",)
    return ()


def sheet_departures(place: str, first: bool, widths: bool, filtered: bool, frozen: bool) -> tuple[str, ...]:
    """Where one sheet departs from the original listing conventions, by code (pure — pinned).

    `place` is "<workbook>/<sheet>". Every sheet sets its column widths (no_widths); every sheet but the
    first, the read-me, is a listing and also filters its header row (no_filter) and freezes its panes
    (not_frozen). Each departure is written "<code>:<place>", in that order. None: ().
    """
    codes = [] if widths else ["no_widths"]
    if not first:
        if not filtered:
            codes.append("no_filter")
        if not frozen:
            codes.append("not_frozen")
    return tuple(f"{code}:{place}" for code in codes)


def new_files(before: dict[str, int], after: dict[str, int]) -> tuple[tuple[str, int], ...]:
    """The files a step wrote, with their sizes in bytes, sorted by path (pure — pinned).

    A file is written when it is in `after` and either absent from `before` or of another size there; a file
    rewritten at the same size is not seen, and a file removed is not listed. A folder is listed with the
    size FOLDER, so a folder is written only when it is new.
    """
    return tuple(sorted((path, size) for path, size in after.items() if before.get(path) != size))


def accounting_problems(
    asked: tuple[str, ...], entries: Any, printed: str, expect_alias: bool
) -> tuple[str, ...]:
    """What a run's requested-ID accounting leaves unsaid, by code and number (pure — pinned).

    `entries` is the record's accounting (studies.json's `provenance.requested_ids`, landscape.json's
    `manifest.retrieval.requested_ids`: one object per requested number: requested, id, status, study);
    `printed` is what the command printed. For each number asked, in order:
      not_accounted:<number> — the record has no entry for it;
      not_printed:<number>   — its status is not "found" and the command did not say so in plain words:
                               "<number> is another number of <study>" for an alias, "<number>:" otherwise.
    Then, when `expect_alias`, no_alias_named — no entry's status is "aliased". Accounted: ().
    """
    rows = entries if isinstance(entries, list) else []
    by_number = {row.get("requested"): row for row in rows if isinstance(row, dict)}
    problems: list[str] = []
    for number in asked:
        row = by_number.get(number)
        if row is None:
            problems.append(f"not_accounted:{number}")
            continue
        status = row.get("status")
        said = f"{number} is another number of {row.get('study')}" if status == "aliased" else f"{number}:"
        if status != "found" and said not in printed:
            problems.append(f"not_printed:{number}")
    if expect_alias and not any(row.get("status") == "aliased" for row in by_number.values()):
        problems.append("no_alias_named")
    return tuple(problems)


def unknown_commands(guide: str, available: tuple[str, ...]) -> tuple[str, ...]:
    """The commands a guide names as `trialledger <name>` that the installed CLI lacks (pure — pinned).

    A name is a run of lower-case letters after "`trialledger " (a placeholder such as "<command>" names
    nothing); each once, in the guide's order. Every one available: ().
    """
    named = dict.fromkeys(re.findall(r"`trialledger ([a-z]+)", guide))
    return tuple(name for name in named if name not in available)


def jargon_found(text: str) -> tuple[str, ...]:
    """The words of JARGON a text uses, each once, in JARGON's order (pure — pinned).

    A word counts only whole and as written, case kept: neither neighbour may be a letter, a digit, "_" or
    "-", so "API" is found in "the API" but not in "APIs" or "rapid", and "digest" not in "digests". None: ().
    """
    return tuple(
        word for word in JARGON if re.search(r"(?<![\w-])" + re.escape(word) + r"(?![\w-])", text) is not None
    )


def overall_verdict(verdicts: tuple[str, ...], checks: tuple[tuple[str, ...] | None, ...]) -> str:
    """Whether the release can go out, from every step's verdict and every check's problems (pure — pinned).

    `checks` holds each check's problems, or None for a check that could not run. "ready" only when there was
    a step, every step's verdict is in PASSING and every check ran and found no problem; else "not_ready": a
    check that did not run is never read as passed.
    """
    if not verdicts or any(verdict not in PASSING for verdict in verdicts):
        return "not_ready"
    return "ready" if all(problems == () for problems in checks) else "not_ready"


# The shell: everything below gathers facts and writes files.


def _sizes(roots: tuple[Path, ...]) -> dict[str, int]:
    """Every file under the roots, by path, with its size; every folder with FOLDER, so that a folder a step
    creates and leaves empty is seen too."""
    found: dict[str, int] = {}
    for root in roots:
        for path in sorted(root.rglob("*")):
            found[str(path)] = path.stat().st_size if path.is_file() else FOLDER
    return found


def _size_words(size: int) -> str:
    return "a folder" if size == FOLDER else f"{size:,} bytes"


class Steps:
    """Runs each step in the user's folder, keeps its output under captures/ and its facts for the report."""

    def __init__(self, work: Path, env: dict[str, str]) -> None:
        self.work = work
        self.home = work / "home"
        self.cache = work / "cache"
        self.captures = work / "captures"
        for folder in (self.home, self.cache, self.captures):
            folder.mkdir(parents=True)
        self.env = env
        self.done: list[dict[str, Any]] = []

    def run(self, name: str, argv: list[str], expected: int = 0) -> dict[str, Any]:
        number = len(self.done) + 1
        stem = self.captures / f"{number:02d}-{name}"
        before = _sizes((self.home, self.cache))
        started = time.monotonic()
        try:
            done = subprocess.run(
                argv,
                cwd=self.home,
                env=self.env,
                capture_output=True,
                text=True,
                timeout=STEP_TIMEOUT_S,
                check=False,
            )
            code: int | None = done.returncode
            out, err = captured_text(done.stdout), captured_text(done.stderr)
        except subprocess.TimeoutExpired as expired:
            code = None
            out, err = captured_text(expired.stdout), captured_text(expired.stderr)
        except OSError as error:
            code, out, err = 127, "", f"could not start: {error}"
        seconds = time.monotonic() - started
        Path(f"{stem}.stdout").write_text(out, encoding="utf-8")
        Path(f"{stem}.stderr").write_text(err, encoding="utf-8")
        findings = output_findings(out + "\n" + err)
        step = {
            "number": number,
            "name": name,
            "argv": argv,
            "expected": expected,
            "exit": code,
            "seconds": round(seconds, 1),
            "verdict": step_verdict(expected, code, tuple(kind for kind, _ in findings)),
            "findings": findings,
            "written": new_files(before, _sizes((self.home, self.cache))),
            "stdout": out,
            "stderr": err,
            "capture": str(stem),
        }
        self.done.append(step)
        print(f"  {number:02d} {name}: exit {code} ({step['verdict']}, {seconds:.1f} s)", file=sys.stderr)
        return step

    def skip(self, name: str, why: str) -> None:
        self.done.append({"number": len(self.done) + 1, "name": name, "skipped": why, "verdict": "skipped"})


def _git(source: Path, *arguments: str) -> str:
    """What `git -C source <arguments>` prints, or "" when git cannot say."""
    try:
        done = subprocess.run(
            ["git", "-C", str(source), *arguments], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return done.stdout


# Variables of this machine's shell that would make the run differ from a first-time user's: a Python or
# conda environment of the repository's, pip's and uv's own settings, and TrialLedger's.
INHERITED_PREFIXES = ("PYTHON", "VIRTUAL_ENV", "CONDA_", "PIP_", "UV_", "TRIALLEDGER_")


def _clean_env(work: Path, venv: Path) -> dict[str, str]:
    """The environment a first-time user's shell would have: this machine's (HOME included, so that uv finds
    the Pythons installed here), without any Python, pip, uv or TrialLedger setting of its own, with no pip
    configuration file, the fresh environment first on PATH and an empty TrialLedger cache."""
    env = {key: value for key, value in os.environ.items() if not key.startswith(INHERITED_PREFIXES)}
    env["PIP_CONFIG_FILE"] = os.devnull
    # The tool folder is on PATH as a user's ~/.local/bin is, after the environment, which the steps use.
    env["PATH"] = os.pathsep.join([str(venv / "bin"), str(work / "uv-tools" / "bin"), env.get("PATH", "")])
    # The variable names a folder (classes.json is kept inside it) or a file (classes.cache_location); a
    # first-time user names a folder, as here.
    env["TRIALLEDGER_CACHE"] = str(work / "cache")
    env["UV_TOOL_DIR"] = str(work / "uv-tools")
    env["UV_TOOL_BIN_DIR"] = str(work / "uv-tools" / "bin")
    return env


def _check_words(problems: tuple[str, ...] | None, why: str) -> str:
    if problems is None:
        return f"not checked: {why}"
    return ", ".join(f"`{problem}`" for problem in problems) or "none"


NOT_CHECKED = (
    "whether each cell's value is right: `verify` certifies that each value derives from the saved record by "
    "the code that wrote it, and nothing here reads a value against the registry",
    "wrapping, fonts, alignment, column widths' sizes, date and number formats, print setup and hyperlink "
    "labels: only whether widths, filters and frozen panes "
    "are set",
    "the clinical wording of the workbooks beyond the fixed list of words below",
    "a live MCP client session: MCP help is read, but its application integration is tested separately; "
    "'guide commands' names those the installed CLI lacks",
    "a landscape run by drug class or disease class (the run here asks for trials by number), and relay mode",
    "anything a step wrote outside home/ and cache/ of the work directory (HOME is this machine's)",
)


def _report(facts: dict[str, Any], steps: list[dict[str, Any]], verdict: str) -> str:
    out = [
        "# TrialLedger release check",
        "",
        f"- Verdict: **{verdict}**",
        f"- Source: `{facts['source']}` ({facts['spec_code']}; pip was given `{facts['spec']}`)",
        f"- Commit: {facts['commit'] or 'not known'}"
        + (f"; working tree has {facts['dirty']} changed or untracked paths" if facts["dirty"] else ""),
        f"- Work directory (the user's folder is home/): `{facts['work']}`",
        f"- Started {facts['started']} UTC; Python {PYTHON} made by uv; pip without configuration file or "
        "cache; TRIALLEDGER_CACHE an empty folder at the start",
        "- The commit the installed copy names in what it writes: "
        + (", ".join(f"{where}: `{named}`" for where, named in facts["named_commits"]) or "nothing written"),
        "",
        "## Checks",
        "",
        "A check that could not run is not checked, never passed.",
        "",
    ]
    for name, (problems, why) in facts["checks"].items():
        out.append(f"- {name}: {_check_words(problems, why)}")
    out += ["", "## Steps", "", "| # | step | exit (expected) | seconds | verdict |"]
    out.append("|---|------|-----------------|---------|---------|")
    for step in steps:
        if "skipped" in step:
            out.append(f"| {step['number']} | {step['name']} | skipped: {step['skipped']} | | skipped |")
        else:
            out.append(
                f"| {step['number']} | {step['name']} | {step['exit']} ({step['expected']}) | "
                f"{step['seconds']} | {step['verdict']} |"
            )
    out += ["", "## Each step", ""]
    for step in steps:
        if "skipped" in step:
            continue
        out.append(f"### {step['number']:02d} {step['name']}")
        out.append("")
        if step["name"] == "inspect-workbooks":
            out.append(
                "`python -c INSPECTOR " + " ".join(step["argv"][3:]) + "` (INSPECTOR is in the script)"
            )
        else:
            out.append("`" + " ".join(step["argv"]).replace(facts["work"], "$WORK") + "`")
        out.append("")
        out.append(
            f"Exit {step['exit']} (expected {step['expected']}), {step['seconds']} s, {step['verdict']}."
        )
        out.append(
            f"Output kept in `{step['capture'].replace(facts['work'], '$WORK')}.stdout` and `.stderr`."
        )
        if step["findings"]:
            out += ["", "Warnings and tracebacks:", ""]
            out += [f"- {kind}: `{line}`" for kind, line in step["findings"]]
        if step["written"]:
            out += ["", "Files and folders written:", ""]
            out += [
                f"- `{path.replace(facts['work'], '$WORK')}`: {_size_words(size)}"
                for path, size in step["written"]
            ]
        if step["name"] in facts["show_output"]:
            for stream in ("stdout", "stderr"):
                if step[stream].strip():
                    out += ["", f"{stream}:", "", "```", *step[stream].splitlines(), "```"]
        out.append("")
    out += ["## Package files", ""]
    if facts["tracked"] is None:
        out.append("Not checked: " + facts["checks"]["package files"][1] + ".")
    else:
        out.append(
            f"{len(facts['tracked'])} current package source files under TrialLedger/; "
            f"{len(facts['installed'])} files "
            "installed (the distribution's own list); missing from the install: "
            + (", ".join(f"`{path}`" for path in facts["checks"]["package files"][0] or ()) or "none")
            + "."
        )
        out.append(
            "Non-Python package files installed: "
            + (", ".join(f"`{p}`" for p in sorted(facts["data_files"])) or "none")
            + "."
        )
    for command, check in (
        ("pull", "requested-ID accounting"),
        ("landscape", "requested-ID accounting (landscape)"),
    ):
        out += ["", f"## Requested-ID accounting (the {command})", ""]
        for row in facts["requested_ids"][command]:
            answered = f", answered by {row.get('study')}" if row.get("study") != row.get("requested") else ""
            out.append(f"- {row.get('requested')}: {row.get('status')}{answered}")
        out += ["", "Problems: " + _check_words(*facts["checks"][check]) + "."]
    out += ["", "## Commands the guide names", ""]
    out.append(
        f"Available: {', '.join(facts['subcommands']) or 'none read'}. Named by AGENTS.md but not available: "
        + _check_words(*facts["checks"]["guide commands"])
        + "."
    )
    out += ["", "## Workbooks", ""]
    if not facts["sheets"]:
        out.append("None inspected.")
    else:
        out += [
            "Blank cells are counted below each sheet's header row. pull's review.xlsx and record.xlsx are "
            "held to their listing conventions; ordinary-report presentation is checked by its verifier.",
            "",
            "| workbook | sheet | rows | columns | widths set | filter | frozen panes | blank cells |",
            "|----------|-------|------|---------|------------|--------|--------------|-------------|",
        ]
        for path, sheet in facts["sheets"]:
            out.append(
                f"| {path} | {sheet['sheet']} | {sheet['rows']:,} | {sheet['columns']} | "
                f"{'yes' if sheet['widths'] else 'no'} | {'yes' if sheet['filtered'] else 'no'} | "
                f"{'yes' if sheet['frozen'] else 'no'} | {sheet['blanks']:,} |"
            )
        out += ["", "Departures that are leads (not held): " + (", ".join(facts["leads"]) or "none") + "."]
    out += ["", "## Not checked by this script", ""]
    out += [f"- {item}" for item in NOT_CHECKED]
    out += ["", "## Words a clinical reader would not know (a fixed list; leads, not faults)", ""]
    for name, words in facts["jargon"].items():
        out.append(f"- {name}: " + (", ".join(f"`{word}`" for word in words) or "none"))
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    started = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
    parser = argparse.ArgumentParser(
        prog="release_check",
        description="Install TrialLedger as a first-time user does, in a fresh directory; report each step.",
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=str(REPOSITORY),
        help="a local checkout (default: this one) or the repository's address (git+https://... or https://...)",
    )
    parser.add_argument(
        "--work", type=Path, help="the work directory to create (default: a new temporary one)"
    )
    args = parser.parse_args(argv)

    source_dir = Path(args.source).expanduser()
    is_dir = source_dir.is_dir()
    code, spec = install_spec(str(source_dir.resolve()) if is_dir else args.source, is_dir)
    if code == "not_a_source":
        print(f"release_check: refused (not_a_source): {args.source}", file=sys.stderr)
        return 2
    if args.work is not None:
        work = args.work.expanduser().resolve()
        if work.exists():
            print(f"release_check: refused (work_exists): {work}", file=sys.stderr)
            return 2
        if work.is_relative_to(REPOSITORY) or (is_dir and work.is_relative_to(source_dir.resolve())):
            print(f"release_check: refused (work_inside_repository): {work}", file=sys.stderr)
            return 2
        work.mkdir(parents=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="trialledger-release-")).resolve()
    venv = work / "venv"
    env = _clean_env(work, venv)
    steps = Steps(work, env)
    print(f"release_check: working in {work}", file=sys.stderr)

    uv = shutil.which("uv") or "uv"
    tl = str(venv / "bin" / "trialledger")
    made = steps.run(
        "make-environment", [uv, "venv", "--python", PYTHON, "--seed", "--no-config", "--no-cache", str(venv)]
    )
    installed_ok = False
    if made["exit"] == 0:
        install = steps.run(
            "pip-install", [str(venv / "bin" / "python"), "-m", "pip", "install", "--no-cache-dir", spec]
        )
        installed_ok = install["exit"] == 0
    else:
        steps.skip("pip-install", "the environment was not made")

    # Where AGENTS.md and the tracked package files are read: the checkout itself, or a clone of the address.
    root: Path | None = source_dir.resolve() if is_dir else None
    no_root = "the source is an archive, which has no AGENTS.md or git file list to read"
    if code in ("vcs_url", "repository_url"):
        address, revision = clone_source(spec)
        clone = work / "source"
        cloned = steps.run("clone-repository", ["git", "clone", address, str(clone)])
        if cloned["exit"] == 0 and revision:
            cloned = steps.run("checkout-revision", ["git", "-C", str(clone), "checkout", revision])
        root = clone if cloned["exit"] == 0 else None
        no_root = "the repository could not be cloned"

    listed: list[str] = []
    if installed_ok:
        lister = (
            "import importlib.metadata as m, json; "
            "print(json.dumps([f.as_posix() for f in (m.files('TrialLedger') or [])]))"
        )
        listing = steps.run("list-installed-files", [str(venv / "bin" / "python"), "-c", lister])
        try:
            listed = json.loads(listing["stdout"])
        except ValueError:
            listed = []
    installed = tuple(path for path in listed if path.startswith("TrialLedger/"))
    tracked: tuple[str, ...] | None = None
    package: tuple[tuple[str, ...] | None, str] = (None, no_root)
    if root is not None:
        # A local candidate includes added files and excludes deleted tracked paths. Comparing Git's old
        # index alone would miss the rescued package and falsely require retired modules in the install.
        tracked = (
            tuple(
                path.relative_to(root).as_posix()
                for path in sorted((root / "TrialLedger").rglob("*"))
                if path.is_file()
                and not any(
                    part.startswith(".") or part == "__pycache__" for part in path.relative_to(root).parts
                )
                and path.suffix not in (".pyc", ".pyo")
            )
            or None
        )
        if tracked is None:
            package = (None, "the source has no package file under TrialLedger/")
        elif not installed:
            package = (None, "the install failed or lists no installed file")
        else:
            package = (missing_package_files(tracked, installed), "")

    help_texts: dict[str, str] = {}
    subcommands: tuple[str, ...] = ()
    accounting: tuple[tuple[str, ...] | None, str] = (None, "the install failed")
    landscape_accounting: tuple[tuple[str, ...] | None, str] = (None, "the install failed")
    outputs: tuple[tuple[str, ...] | None, str] = (None, "the install failed")
    workbooks: tuple[tuple[str, ...] | None, str] = (None, "the install failed")
    reasoning: tuple[tuple[str, ...] | None, str] = (None, "the install failed")
    entries: dict[str, Any] = {"pull": [], "landscape": []}
    named_commits: list[tuple[str, str]] = []
    sheets: list[tuple[str, dict[str, Any]]] = []
    leads: list[str] = []
    if installed_ok:
        top = steps.run("help", [tl, "--help"])
        help_texts["trialledger --help"] = top["stdout"]
        subcommands = subcommand_names(top["stdout"])
        for name in subcommands:
            sub = steps.run(f"help-{name}", [tl, name, "--help"])
            help_texts[f"trialledger {name} --help"] = sub["stdout"]
        steps.run("doctor", [tl, "doctor", "--run", "doctor-run"])
        premise = {
            "class": "Literal",
            "subject": {"class": "Subject", "kind": "participant"},
            "predicate": {"class": "Predicate", "kind": "demographic", "key": "eligible_sex"},
            "value": {"class": "Value", "kind": "enum", "members": ["female"]},
        }
        reason_request = {
            "operation": "entailment",
            "assertions": [
                {
                    "class": "ScopedAssertion",
                    "id": "population",
                    "criterion_ref": "user:brief",
                    "modality": "required",
                    "body": premise,
                    "rule": {
                        "class": "Rule",
                        "id": "user-choice",
                        "version": "1",
                        "warrants": ["user:brief"],
                    },
                    "status": "known",
                    "resolution": "resolved",
                }
            ],
            "query": {**premise, "value": {"class": "Value", "kind": "enum", "members": ["male"]}},
        }
        (steps.home / "premises.json").write_text(json.dumps(reason_request), encoding="utf-8")
        reasoned = steps.run("reason", [tl, "reason", "--request", "premises.json"])
        try:
            reasoning = (reason_problems(json.loads(reasoned["stdout"])), "")
        except ValueError:
            reasoning = (("reason_response_unreadable",), "")
        pulled = steps.run("pull", [tl, "pull", "filter.ids=" + ",".join(PULL_IDS), "--out", "pulled"])
        record = steps.home / "pulled" / "studies.json"
        if pulled["exit"] == 0 and record.is_file():
            provenance = json.loads(record.read_text(encoding="utf-8")).get("provenance", {})
            entries["pull"] = provenance.get("requested_ids")
            named_commits.append(("pulled/studies.json", str(provenance.get("code_commit"))))
            printed_words = pulled["stdout"] + pulled["stderr"]
            accounting = (
                accounting_problems(PULL_IDS, entries["pull"], printed_words, expect_alias=True),
                "",
            )
            steps.run("verify", [tl, "verify", "pulled"])
        else:
            accounting = (None, "the pull wrote no record")
            steps.skip("verify", "the pull wrote no folder")
        # The same trials through the run an assistant makes for a person who names trials by number.
        ran = steps.run("landscape", [tl, "landscape", "--run", LANDSCAPE_RUN, "--ids", ",".join(PULL_IDS)])
        landscape = steps.home / LANDSCAPE_RUN / "landscape.json"
        if ran["exit"] == 0 and landscape.is_file():
            manifest = json.loads(landscape.read_text(encoding="utf-8")).get("manifest", {})
            entries["landscape"] = manifest.get("retrieval", {}).get("requested_ids")
            named_commits.append((f"{LANDSCAPE_RUN}/landscape.json", str(manifest.get("code_commit"))))
            printed_words = ran["stdout"] + ran["stderr"]
            landscape_accounting = (
                accounting_problems(PULL_IDS, entries["landscape"], printed_words, expect_alias=True),
                "",
            )
            steps.run("verify-landscape", [tl, "verify", LANDSCAPE_RUN])
        else:
            landscape_accounting = (None, "the landscape wrote no record")
            steps.skip("verify-landscape", "the landscape wrote no record")
        present = tuple(path for path in EXPECTED_OUTPUTS if (steps.home / path).is_file())
        outputs = (outputs_missing(EXPECTED_OUTPUTS, present), "")
        books = [path for path in present if path.endswith(".xlsx")]
        if books:
            inspected = steps.run(
                "inspect-workbooks", [str(venv / "bin" / "python"), "-c", INSPECTOR, *books]
            )
            try:
                found: dict[str, list[dict[str, Any]]] = json.loads(inspected["stdout"])
            except ValueError:
                found = {}
            held: list[str] = []
            for path, book_sheets in found.items():
                for position, sheet in enumerate(book_sheets):
                    sheets.append((path, sheet))
                    departures = sheet_departures(
                        f"{path}/{sheet['sheet']}",
                        position == 0,
                        sheet["widths"],
                        sheet["filtered"],
                        sheet["frozen"],
                    )
                    (held if path in HELD_WORKBOOKS else leads).extend(departures)
                help_texts[f"{path} (headings; first sheet whole)"] = "\n".join(
                    s["text"] for s in book_sheets
                )
            unread = [path for path in HELD_WORKBOOKS if path not in found]
            workbooks = (tuple(held), "") if not unread else (None, "not read: " + ", ".join(unread))
        else:
            workbooks = (None, "no workbook was written")
        tool = steps.run(
            "uv-tool-install", [uv, "tool", "install", "--no-config", "--no-cache", "--python", PYTHON, spec]
        )
        if tool["exit"] == 0:
            steps.run("uv-tool-help", [str(work / "uv-tools" / "bin" / "trialledger"), "--help"])
        else:
            steps.skip("uv-tool-help", "uv tool install failed")
    else:
        steps.skip("trialledger", "the install failed")

    printed = {f"{s['name']} (printed)": s["stdout"] + s["stderr"] for s in steps.done if "argv" in s}
    texts = {
        **help_texts,
        **{
            k: v
            for k, v in printed.items()
            if k.split(" ")[0] in ("doctor", "pull", "verify", "landscape", "reason")
        },
    }
    guide: tuple[tuple[str, ...] | None, str]
    if root is None:
        guide = (None, no_root)
    elif not (root / "AGENTS.md").is_file():
        guide = (None, "the source has no AGENTS.md")
    elif not subcommands:
        guide = (None, "the installed CLI's --help listed no command")
    else:
        guide = (unknown_commands((root / "AGENTS.md").read_text(encoding="utf-8"), subcommands), "")
    checks = {
        "package files": package,
        "outputs handed to the user": outputs,
        "requested-ID accounting": accounting,
        "requested-ID accounting (landscape)": landscape_accounting,
        "guide commands": guide,
        "workbook conventions (pull's workbooks)": workbooks,
        "typed reasoning": reasoning,
    }
    verdicts = tuple(step["verdict"] for step in steps.done)
    verdict = overall_verdict(verdicts, tuple(problems for problems, _ in checks.values()))
    facts = {
        "source": args.source,
        "spec_code": code,
        "spec": spec,
        "commit": _git(root, "rev-parse", "HEAD").strip() if root is not None else "",
        "dirty": len(_git(root, "status", "--porcelain").splitlines()) if root is not None else 0,
        "work": str(work),
        "started": started,
        "tracked": tracked if package[0] is not None else None,
        "installed": installed,
        "data_files": [path for path in installed if not path.endswith((".py", ".pyc"))],
        "requested_ids": {key: rows if isinstance(rows, list) else [] for key, rows in entries.items()},
        "named_commits": named_commits,
        "checks": checks,
        "subcommands": subcommands,
        "sheets": sheets,
        "leads": leads,
        "jargon": {name: jargon_found(text) for name, text in texts.items()},
        "show_output": (
            "pip-install",
            "doctor",
            "pull",
            "verify",
            "landscape",
            "verify-landscape",
            "reason",
            "uv-tool-install",
        ),
    }
    report = work / "REPORT.md"
    report.write_text(_report(facts, steps.done, verdict), encoding="utf-8")
    print(f"release_check: {verdict}; the report is {report}")
    return 0 if verdict == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
