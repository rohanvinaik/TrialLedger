# TrialLedger

**Trial registry data, abstracted the way a clinical data manager would: every value from source, every
inconsistency queried, nothing invented.**

TrialLedger reads ClinicalTrials.gov through the registry's official API and produces files a person can
open, check and rely on: the complete record of every study a question matches, and a review workbook laid
out around what study design needs: population, eligibility, endpoints and time points, results, safety.
Every value it shows can be traced to the field of the registry record it came from or to a named rule
applied to such fields, and carries a warrant that lets anyone re-derive it. What cannot be traced is shown
as unresolved. Nothing is filled in by guesswork, and no AI system reads or summarizes the trials.

## Why this exists

A common shortcut in clinical development is to paste a ClinicalTrials.gov link into a chatbot and ask it
to summarize the design. The answer reads well and cannot be source-verified. A language model paraphrases;
it does not abstract. It can drop an exclusion criterion, merge two arms, attach a time point to the wrong
endpoint, report an estimated date as an actual one, or describe results that were never posted, and
nothing in the answer tells you which sentence is the wrong one. For a design decision, a fluent answer
with an unknown error rate is worse than no answer, because it looks finished.

Clinical research already has the discipline this calls for. Trial data is abstracted from source
documents, every value is source-verifiable, and edit checks raise queries on values that contradict each
other before anyone analyzes them. TrialLedger applies the same discipline to the registry itself.

## What it does today

Ask for one study, a list of studies, or every study matching a condition, an intervention, a sponsor, a
recruitment status or a date range. TrialLedger asks the registry's API and writes a new folder with four
files:

- **`studies.json`**: the complete registry record of every matching study, exactly as the registry sent
  it, under a header recording which query produced it, which release of the registry's data it came from,
  and when it was retrieved.
- **`studies.csv`**: the registry's own spreadsheet for the same studies. It opens in Excel, Numbers or
  Google Sheets. (Its columns are the registry's choice; eligibility and safety are not among them, which is
  why the review workbook exists.)
- **`review.xlsx`**: the review workbook (section 5 below). It answers the design questions study by study:
  eligibility split into inclusion and exclusion where the record allows it, every registered outcome with
  its time frame, posted results and statistical analyses per arm, every adverse event per arm with the
  numbers affected and at risk, participant flow, baseline measures, publications and posted documents, each
  linked to its source.
- **`record.xlsx`**: every value of every study, one per row, under the registry's own category and field
  names, so nothing in the record goes unpresented. It is its own file because it is the largest: Google
  Sheets opens at most 10 million cells in one spreadsheet, which this file reaches at about 300
  results-heavy trials and the review workbook at about 500. TrialLedger names any file over that cap when
  it writes it.

The folder is written only when the pull is complete and consistent:

- every page of results arrived, in both formats;
- the number of studies equals the number the registry reported, and no study arrived twice;
- the record file and the spreadsheet list exactly the same studies;
- the registry did not refresh its data while the pull was running;
- temporary server errors and dropped connections were retried and resolved;
- both workbooks, read back cell by cell, hold exactly what the record derives.

If any of these fails, nothing is written and the reason is printed. One kind of query is refused before it
is sent: when a search term consists only of NCT numbers, the registry silently ignores every filter in the
same query, so the answer would look filtered and not be.

A folder can be checked at any later time: `trialledger verify <folder>` re-derives everything in it from
`studies.json` and names anything that no longer follows (section 6).

## How it reasons

The parts below are designed and are being built in stages; the status table further down says which
stage is where.

### 1. The ledger: the source record, kept whole

Every element of every record is entered in a ledger, the way a monitor logs source data: the value as
written, where it sits in the record, and its role, such as an inclusion or an exclusion criterion, a
primary, secondary or other pre-specified outcome, or the arm a count belongs to. The ledger is deliberately
richer than any output, and nothing is ever removed from it. Every view TrialLedger produces is derived from
the ledger, and every derived value says what it came from.

### 2. Edit checks: each record checked against itself

The registry's structured fields constrain one another, as the fields of a case report form do. A study
marked completed should not carry an estimated completion date. Every intervention an arm names should be
declared by the study. No adverse event can affect more participants than were at risk. A minimum age
cannot exceed the maximum. Each check is reported as consistent, in conflict, not applicable to the record,
or not checkable: the last whenever a value the check needs is missing, malformed, or too imprecise to
decide it (two partial dates whose months overlap, say), so a check never passes for lack of evidence. A
conflict is shown to the reviewer as a query. It is never silently corrected, because a contradiction in a
record is exactly where an error in the data, or a fabricated value in someone's summary, reveals itself.

Seventeen checks are built, each quoting the registry's own definition it rests on. The five whose relation
the registry states as a rule, or defines one field as a function of another, run on every record: a
completed or terminated study's primary completion and study completion dates are typed actual; a
multi-site study with a recruiting site is itself recruiting; the reasons participants did not complete
account for all of them; and the results flag agrees with the results submission date. The other twelve,
including the arm, adverse-event and age checks above, follow from the definitions without being stated as
rules. They are built and tested, and listed in the workbook, but run only once the project's founder
approves each one by name.

The same discipline governs what is unknown. A field the registry left empty stays empty, and it is never
confused with a recorded "none". A study without posted results says so in so many words. That matters
more than it might seem: on 31 October 2026 only 80,808 of the 609,551 studies in the registry (13.3%) had
results posted to it.

### 3. Three kinds of answer

TriageGeist, an earlier project in this line of work, built emergency triage so that physicians could audit
every decision: protocol where there is protocol, a computed pattern where there is regularity, and judgment
only where two clinicians would also disagree. TrialLedger labels every value the same way:

- **Stated**: read directly from a structured field of the record.
- **Computed**: derived by a named rule, within one record or across comparable trials, with the rule and
  its inputs shown.
- **Needs review**: not determinable from the sources TrialLedger uses. It is shown with links to what a
  reviewer would read, and it is never filled in.

Each workbook's About sheet gives the kind and the source of every column it holds.

### 4. Publications: linked, surfaced, and the source for unposted results

The registry links each study to its publications, of three types. A study's responsible party enters some
of them and marks each one as reporting the study's results or not (the registry's types "result" and
"background"). The registry adds others itself (type "derived"), and for those it states no role at all: a
derived publication may report the results, describe the protocol, or analyse the data later, and the
record does not say which. Derived links are the most common kind: on 30 October 2026, 126,368 studies
carried derived publications, 99,393 background and 43,671 result. TrialLedger puts every linked
publication beside its study with its type in the registry's own terms, so a reader can go straight from a
value to the source text, and it never presents a derived publication as a results paper.

For studies whose results were never posted to the registry, publications are the next source (a later stage,
designed but not yet built): outcome and adverse-event figures a paper states explicitly can enter the ledger
as publication evidence, each one carrying the exact sentence it came from and marked as coming from the paper
rather than the registry. Where the paper and the registry disagree, both are shown. What a paper does not
state plainly stays a review item, with the paper linked. Which publications to read for a study is an open
design question, because the "result" type alone misses most results papers. A study that is still running has
no results anywhere yet, and the workbook says exactly that.

### 5. The review workbook

The first view built on the ledger answers the questions a clinical development team asks of each study:

| | What the reviewer needs | Where it comes from | Kind |
|---|---|---|---|
| 1 | Patient population | Age range, sex and healthy-volunteer status are structured fields; gender, when a study reports it, is recorded separately from sex. Further limits live in the eligibility text. | Stated |
| 2–3 | Key inclusion and exclusion criteria | The eligibility text in full, split into inclusion and exclusion when the record uses the registry's standard headings, and shown whole when it does not. | Stated |
| 4 | Line of therapy | Almost never a structured field; usually only in the eligibility text ("previously untreated", "after progression on"). | Needs review, with that text shown |
| 5 | Outcome measures and time points | Primary, secondary and other pre-specified outcomes with their time frames, as registered. | Stated |
| 6 | Biomarkers and time points | No structured biomarker field: they appear inside outcomes and eligibility, shown in full, and a biomarker keeps its role (eligibility, response or safety). | Stated where registered; needs review to single out |
| 7 | Anticipated efficacy threshold | Posted results of comparable trials, and results publications. | Computed across trials (later stage) |
| 8 | Safety signals | Serious and other adverse events per arm, with numbers affected and at risk, when results are posted; event grades usually appear only in publications. | Stated when posted; "no results posted" otherwise |
| 9 | Exploratory biomarkers, imaging, biopsies | "Other pre-specified" outcomes are a registry category; arm and intervention descriptions add detail. | Stated where registered |
| 10 | Standard protocol language | Criteria that recur across the trials of an indication. | Computed across trials (later stage) |

Each row carries the study's registry page, every linked publication with its type in the registry's own
terms (result or background as the responsible party marked it; derived, added by the registry with no
stated role), and any protocol, statistical analysis plan or consent form the sponsor posted.

The workbook has a sheet for each part of the record a reviewer reads: Studies (one row per study, the
design axes), Eligibility, Outcomes, Arms, Interventions, Sites, Outcome Results, Analyses, Adverse Events,
Event Groups, Participant Flow, Baseline, Publications, Documents, and the edit checks with the registry's
words for each. Beside it, `record.xlsx` lists every value of every study under the registry's own category
and field names, so nothing in the record goes unpresented. A value a spreadsheet cell cannot hold exactly
(text with characters the file format forbids, text longer than a cell holds, a number a cell would round)
is never cut, cleaned or rounded: its cell says why, and where the value is in `studies.json`.

### 6. Warrants: every value carries its basis

Every value in either workbook carries a warrant, a SHA-256 hash committing to what produced it. A value read
from the record commits to the study's record, the value's place in it and the value itself. A computed value
commits to its rule, to the exact code that derived it (a single root over the modules and registry tables
that derive the workbook), and to the warrants of its inputs. `studies.json` records each study's digest, a
root over all of them, and a record root over the provenance (the query, the data release, the retrieval time,
the code), the studies and the spreadsheet.

Before a folder is written, both workbooks are read back and every cell and warrant re-derived from the
record; if anything differs, nothing is written. Later, `trialledger verify` repeats the derivation and
compares both workbook files part for part, so any edit is named: a changed value, a count replaced by
TRUE, a changed link or format. A folder can be certified only by TrialLedger running the derivation code
that wrote it, and `studies.json` names that code's git commit, so an older folder is verified at its
commit. A change to the command line, the network layer, or the code that saves and verifies a folder
leaves every folder verifiable; a different version of the spreadsheet library is named, since it would
write the files differently. A warrant proves derivation, not authorship: anyone can re-run TrialLedger, so
to rely on a folder later, keep its record root. Whether a rule is right rests on its tests: every decision
is pinned by tests that a mutation tester (Detective) confirms are complete.

### 7. Questions across the registry (later stages)

The same ledger supports the questions a sponsor asks when planning a program. Each is a defined
computation over the registry's fields, and each must show the trials it rests on:

- **What we need to beat.** The efficacy and safety results of comparable trials, matched on endpoint and
  time point. Two trials that both report "change in HbA1c" are not comparable if one measures at 12 weeks
  and the other at 52.
- **Cohorts that do well.** Outcomes compared across trials grouped by how they define their populations,
  only where the comparison is like for like, and only against a stated objective (benefit, risk, comparator).
- **Underserved niches.** Combinations of indication, line of therapy, population and mechanism that no
  trial has studied, or that only failed or ongoing trials occupy. An empty combination is a lead, not
  proof of unmet need; unmet need also depends on disease burden and existing care.
- **Exclusions that point to a mechanism.** An exclusion that recurs across trials of one drug class or
  pathway, but not across the indication generally, points to a risk tied to that mechanism. One that
  every trial shares (pregnancy, for instance) points to nothing in particular. Such a pattern is proposed
  as a candidate for a person to evaluate; TrialLedger never treats a pattern as proven.

## The principles behind it

TrialLedger is built on information theory and data geometry. In practical terms:

- **Nothing is thrown away.** No summary can know more about a trial than its record contains, so the record
  is kept whole and every derived value points back to it.
- **Unknown stays unknown.** An unresolved value is the set of possibilities still open. Only evidence or an
  approved rule narrows it, never an assumption, and a silent field is never read as a "no".
- **Significant means informative.** What matters for a design question is what distinguishes the trials
  being compared. A criterion every trial shares is background; a criterion that varies with the mechanism
  being studied is signal.
- **Trials are points in a design space.** Its dimensions are the clinical ones: population, phase, line of
  therapy, mechanism, endpoint and time point, safety. Comparators are neighbors along matched dimensions;
  a cohort is a region; a niche is an empty region; the review workbook is that space seen along the
  dimensions one reviewer needs.
- **Every value carries its basis.** A warrant commits each value to the record and the exact rule code
  that rendered it; re-deriving it either reproduces it or names the value that no longer follows.

## What it will never do

- Have an AI read, summarize or interpret a trial.
- Fill in a value it cannot source.
- Round, truncate or clean a value to make it fit.
- Hide a gap, a conflict or a failed retrieval.
- Compare outcomes that are not comparable.
- Treat a recurring pattern as established fact.

## Status

| Part | State |
|---|---|
| Pulling studies; the record file and the registry's spreadsheet; the completeness guarantees | Built and verified, against the live registry |
| Ledger, the five approved edit checks, the review workbook, warrants and `trialledger verify` | Built and verified, against the live registry ([`add-review-workbook`](openspec/changes/archive/2026-10-31-add-review-workbook/)) |
| The twelve further edit checks | Built and tested; each waits for the founder's approval |
| Typed criteria, each trial's design coordinates, drug classes and the profile across a pull (`trialledger profile`) | First slice built, on the Phase 3 NSCLC trials of 2015–2024; every relation awaits the founder's approval ([`add-coherence-engine`](openspec/changes/add-coherence-engine/)) |
| Publication evidence for studies without posted results | Designed |
| An interface that needs no terminal | Planned |

## Running it

TrialLedger needs [uv](https://docs.astral.sh/uv/) (Python is installed through it):

```bash
uv sync
uv run trialledger resolve filter.ids=NCT03829332 --json -
uv run trialledger resolve query.cond="non-small cell lung cancer" filter.overallStatus=RECRUITING \
    --json reading.json --out design.xlsx
```

**The main path is `resolve`.** It queries ClinicalTrials.gov live (one snapshot, complete or nothing) and
resolves every matching study to its symbolic reading, without saving the registry's records: each eligibility
criterion split out and typed by fixed rules, each trial's design coordinates (setting, prior lines, biomarker
selection) as the values its own criteria still allow, each experimental drug's pharmacologic class from the
National Library of Medicine's RxClass, its registered outcomes, each declared expectation's observation and
deviation, and a **review queue**: what the rules could not cleanly resolve (an unclassified drug, a coordinate
the criteria contradict, an unresolved or deviating observation), each as a question with closed answer options
and its evidence, for a domain expert or a model to answer. TrialLedger never forces those answers. `--json`
writes the reading as JSON (a path, or `-` for standard output; the default); `--out` writes `design.xlsx`,
which adds the profile across the matched trials (how often each criterion appears, which criteria are
standard, which track a drug class, which settings and classes no trial occupies, and results grouped like for
like). Only the RxClass answers are cached, in `~/.cache/trialledger` (or `$TRIALLEDGER_CACHE`). It ends with
`0`, resolved; `1`, the query failed; `2`, the query was refused.

Each `NAME=VALUE` is one of the registry's own search parameters (`spec/ctg-oas-v2.yaml`), sent exactly as
written; the registry rejects names it does not know. `query.*` parameters search the way the registry's
website does, ranking by relevance and matching related terms, so they can return more than you meant;
`filter.*` parameters restrict the set exactly. Requests are spaced 1.25 seconds apart; the registry publishes
no rate limit, and if it asks TrialLedger to slow down, it does.

**The fallback, when a stored, verifiable record is wanted**, is to save a query and resolve the saved folder:

```bash
uv run trialledger pull query.cond=sarcoidosis filter.overallStatus=RECRUITING --out my_studies
uv run trialledger verify my_studies
uv run trialledger profile my_studies
```

`pull` writes the records as sent (`studies.json`), the registry's spreadsheet (`studies.csv`) and the two
certified workbooks; it ends with `0`, written; `1`, the pull or the write failed and nothing was written; `2`,
the query was refused. `verify` re-derives a saved folder and ends with `0`, certified; `1`, not certified,
each difference named; `2`, no TrialLedger record; it rewrites both workbooks to compare the files, so it takes
about as long as the original write. `profile` writes the same `design.xlsx` as `resolve --out` beside a saved
folder, changes none of its files, and refuses a folder whose record no longer matches its digests (`1`) or
that holds no record (`2`).

To check the build: `scripts/ci_local.sh` runs the fast gate (`--deep` adds the Detective audit of every
pinned decision and the vulture scans; it needs local checkouts of Detective and Wesker),
`.venv/bin/python scripts/push_checks.py install` installs the pre-push hook that runs the gate before every
push, and `uv run pytest -m live` runs pulls against the real registry.

## Where the ideas come from

- **harmonizing** turned proteomics papers and repository records into a structured, scored spreadsheet. It
  contributed the ledger (keep every piece of evidence, richer than the output), the projection boundary
  (decide what crosses into a given output), and cross-field coherence (let one confident fact constrain
  others; never invent).
- **GSE** contributed the treatment of uncertainty: absence and silence are different things, an unresolved
  value keeps its possibilities open, conflicts are reported rather than voted away, and a discovered
  pattern only ever proposes a rule.
- **TriageGeist** encoded emergency triage as a process that is symbolic almost throughout, legible to the
  clinicians who would have to trust it. It contributed the three kinds of answer and the principle that any
  non-auditable step must be small, bounded, and checked.

The design in full: [`docs/THEORY_OF_THE_CASE.md`](docs/THEORY_OF_THE_CASE.md). Rules for anyone changing
the code: [`AGENTS.md`](AGENTS.md).
