# Project scripts

- `ci_local.sh`: relevant local code/test gate; see DEVELOPING.md, Verification.
- `push_checks.py`: pre-push checks and the local gate stamp.
- `release_check.py`: installation and first-use walk in a fresh directory, using the current candidate.

## Installation and first-use check

Run from a machine that reaches ClinicalTrials.gov and RxNav, with `uv` on PATH. The script uses the standard
library to create a fresh Python 3.12 environment and install TrialLedger and its runtime dependencies:

```bash
python3 scripts/release_check.py
python3 scripts/release_check.py /absolute/path/to/TrialLedger
python3 scripts/release_check.py git+https://github.com/rohanvinaik/TrialLedger
```

The default is this checkout's current working tree, including added package files and excluding deleted
ones. A Git address tests its committed source, not local edits. A repository address is cloned so the
script can compare the source package and guide with what was installed. An archive can be installed, but
checks requiring its absent source/guide remain not checked.

The work directory is outside the repository. The script creates its environment and uv-tool folder there,
clears inherited Python/pip/uv/TrialLedger settings, disables installer configuration/caches and gives the
run an empty TrialLedger cache. It retains this machine's HOME and installed Python/tool infrastructure;
this is not a claim to reproduce every other machine or chat sandbox. It does not publish or push anything.

The installed program is exercised through its actual command line:

1. Read top-level and every public command's help, then run doctor.
2. Run a separately supplied typed population premise through `reason`, checking the expected conditional
   refutation and its premise id. This checks useful symbolic logic, not extraction from a trial or a
   complete generated protocol.
3. `pull` three identifiers, including an alias, and `verify` the archival folder.
4. `landscape --ids` for the same identifiers and `verify` the ordinary reference-report folder.
5. Open written workbooks using the installed environment, then install with `uv tool install` and read
   that command's help too.

It never invokes the retired raw clinical readers. Expected user artifacts are the pull's `studies.json`,
`studies.csv`, `review.xlsx` and `record.xlsx`, and the reference run's `landscape.json` and `landscape.xlsx`.
It does not require a new-trial design workbook.

## Read the evidence

`WORK/REPORT.md` records the source/commit and uncommitted state, each step's exit against its expected exit,
wall time, warnings/tracebacks and written paths/sizes. Complete stdout and stderr are retained under
`WORK/captures/`; the report does not replace those captures.

The checks cover missing installed package files, expected artifacts, requested-ID accounting for both
retrieval paths, commands named by AGENTS.md, the original archival listing conventions and the typed
reasoning consequence. Workbook inspection records widths, filters, frozen panes, sheet sizes and blank
cells. Presentation departures in the ordinary report are leads alongside its own replay verifier, not a
claim that every dossier should behave as a filtered listing. The fixed jargon list is a wording-review
lead, not a rule deciding clinical meaning.

Exit 0 means ready for the checks actually performed: steps ended as expected without traceback and every
required check ran without a problem. Exit 1 means not ready; missing checks never become passes. Exit 2
names a refused source or unsafe/existing work-directory choice. Warnings remain visible. Runtime is
measured for each execution rather than promised from a past run.

## Limits

This walk does not independently adjudicate source truth, clinical interpretation or every source-to-cell
value. Replay establishes derivation from retained inputs. Full readability review, exact formatting and
source-preservation acceptance remain separate checks. This walk uses identifiers; it does not establish
class-search or relay coverage, every study type, or a live MCP client's application integration. It does not
exercise the complete automated trial writer. Current requirements are in
[the two-layer contract](../openspec/README.md), not a superseded workbook-design change.
