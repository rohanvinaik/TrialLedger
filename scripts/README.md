# scripts/

- `ci_local.sh`: the gate, run before every commit (see `DEVELOPING.md`, "Gate").
- `push_checks.py`: the pre-push hook the gate stamps for.
- `release_check.py`: TrialLedger as a first-time user meets it. Run it before publishing.

## Before publishing: the release check

Run it from a machine that reaches ClinicalTrials.gov and RxNav, with `uv` on the PATH. It needs no
environment of its own (the standard library only):

```bash
python3 scripts/release_check.py                     # this checkout, as its working tree stands
python3 scripts/release_check.py git+https://github.com/<owner>/TrialLedger   # once the repository is public
```

It creates a new temporary directory outside the repository, makes a fresh Python 3.12 environment there with
`uv venv --seed`, and installs TrialLedger the way `AGENTS.md` tells an assistant to: `pip install` the
repository's path or address, then `uv tool install` it, with uv's tool folder kept inside the temporary
directory. pip runs without a configuration file or cache, and uv without its configuration or cache, so
nothing installed or set on this machine before is reused. A repository address is also cloned there, so
that `AGENTS.md` and the package's file list are read from what the address serves. It then works from that
directory with an empty TrialLedger cache. It runs `trialledger --help` and every subcommand's `--help`, then
`doctor`. It pulls three trials by number, live; one of them, NCT01086644, is another trial's alias number,
and the pull must name it. It runs `verify` on the pulled folder and a one-trial `resolve` with `--json` and
`--out`, then opens every workbook written with the environment's own openpyxl.

The report is `WORK/REPORT.md`, and each step's output is kept beside it under `WORK/captures/`. For each step
the report gives the exit code against the expected one, the wall time, the files and folders the step wrote
with their sizes, and every warning or traceback. Then five checks, each with its problems, or "not checked"
and why:

- package files: the files git tracks under `TrialLedger/` that the installed distribution lacks;
- outputs handed to the user: `studies.json`, `studies.csv`, `review.xlsx` and `record.xlsx` from the pull,
  `reading.json` and `design.xlsx` from the resolve;
- requested-ID accounting: every number asked for is accounted for, and the alias is named;
- guide commands: the commands `AGENTS.md` names that the installed CLI lacks;
- workbook conventions: each sheet of pull's `review.xlsx` and `record.xlsx` sets its column widths, and each
  listing has a filter and frozen panes, as `openspec/changes/add-agent-operation/workbook-design.md` requires
  of them. The resolve's `design.xlsx` is inspected the same way; its departures are reported as leads.

The report also lists each workbook's sheets (rows, columns, widths, filter, frozen panes, blank cells), what
the script does not check (cell values against the registry, wrapping, fonts, print setup, date formats,
clinical wording beyond its fixed list, the commands it does not run), and, for each help text, printed
message and workbook, the words from a fixed list that a clinical reader would not know. These are leads for
rewording, not faults.

It ends 0 ("ready") only when every step ended as expected without a traceback and every check ran and found
nothing. A check that could not run (an archive address, a failed install or clone) makes the verdict
"not_ready", never "ready"; the script ends 1. It refuses, ending 2, a source that is neither a folder nor an
https or git+ address (`not_a_source`), and a `--work` folder that already exists (`work_exists`) or lies
inside the repository (`work_inside_repository`). The whole run takes about four to six minutes, most of it
the resolve's RxNav lookups from an empty cache. A local checkout is installed from its working tree,
untracked files included. The report states the commit and how many paths are uncommitted, so commit first
if the report is meant to stand for what GitHub will serve. `git+file:///path/to/checkout` takes the address
route on a local repository: it installs and reads the committed tree only, as GitHub would serve it.
