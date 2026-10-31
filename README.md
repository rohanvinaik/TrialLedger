# TrialLedger

**Trial registry data, abstracted the way a clinical data manager would: every value from source, every
inconsistency queried, nothing invented.**

TrialLedger reads ClinicalTrials.gov through the registry's official API and produces files a person can
open, check and rely on: the complete record of every study a question matches, and, as it is built out, a
review workbook laid out around what study design needs: population, eligibility, endpoints and time points,
biomarkers, safety. Every value it shows can be traced to the field of the registry record it came from, to
a named rule applied to such fields, or to a quoted sentence of a linked publication. What cannot be traced
is shown as unresolved. Nothing is filled in by guesswork, and no AI system reads or summarizes the trials.

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
recruitment status or a date range. TrialLedger asks the registry's API and writes a new folder with two
files:

- **`studies.json`**: the complete registry record of every matching study, exactly as the registry sent
  it, under a header recording which query produced it, which release of the registry's data it came from,
  and when it was retrieved.
- **`studies.csv`**: the registry's own spreadsheet for the same studies. It opens in Excel, Numbers or
  Google Sheets. (Its columns are the registry's choice; eligibility and safety are not among them, which is
  why the review workbook below exists.)

The folder is written only when the pull is complete and consistent:

- every page of results arrived, in both formats;
- the number of studies equals the number the registry reported, and no study arrived twice;
- the record file and the spreadsheet list exactly the same studies;
- the registry did not refresh its data while the pull was running;
- temporary server errors and dropped connections were retried and resolved.

If any of these fails, nothing is written and the reason is printed. One kind of query is refused before it
is sent: when a search term consists only of NCT numbers, the registry silently ignores every filter in the
same query, so the answer would look filtered and not be.

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
cannot exceed the maximum. TrialLedger runs checks like these on every record and reports each one as
consistent, in conflict, or not checkable. A conflict is shown to the reviewer as a query. It is never
silently corrected, because a contradiction in a record is exactly where an error in the data, or a
fabricated value in someone's summary, reveals itself.

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

### 4. Publications: linked, surfaced, and the source for unposted results

The registry links each study to its publications and says which of them report the study's results.
TrialLedger puts every linked publication beside its study, so a reader can go straight from a value to the
source text. For studies whose results were never posted to the registry, the results publication is the
next source: outcome and adverse-event figures the paper states explicitly can enter the ledger as
publication evidence, each one carrying the exact sentence it came from and marked as coming from the paper
rather than the registry. Where the paper and the registry disagree, both are shown. What a paper does not
state plainly stays a review item, with the paper linked. A study that is still running has no results
anywhere yet, and the workbook says exactly that.

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

Each row carries the study's registry page, every linked publication with the role the registry gives it
(background, results, or derived), and any protocol, statistical analysis plan or consent form the sponsor
posted.

### 6. Questions across the registry (later stages)

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

## What it will never do

- Have an AI read, summarize or interpret a trial.
- Fill in a value it cannot source.
- Hide a gap, a conflict or a failed retrieval.
- Compare outcomes that are not comparable.
- Treat a recurring pattern as established fact.

## Status

| Part | State |
|---|---|
| Pulling studies; the record file and the registry's spreadsheet; the completeness guarantees | Built and verified, against the live registry |
| Ledger, edit checks, the review workbook with eligibility, safety and publication links | Specified: [`openspec/changes/add-review-workbook`](openspec/changes/add-review-workbook/) |
| Publication evidence for studies without posted results | Designed |
| Questions across the registry | Designed |
| An interface that needs no terminal | Planned |

## Running it

TrialLedger needs [uv](https://docs.astral.sh/uv/) (Python is installed through it):

```bash
uv sync
uv run trialledger pull filter.ids=NCT04852770
uv run trialledger pull filter.ids=NCT04852770,NCT01030536 --out my_studies
uv run trialledger pull query.cond=sarcoidosis filter.overallStatus=RECRUITING
uv run trialledger pull "filter.advanced=AREA[StartDate]RANGE[2024-01-01,2024-01-31]" query.cond=asthma
```

Each `NAME=VALUE` is one of the registry's own search parameters (`spec/ctg-oas-v2.yaml`), sent exactly as
written; the registry rejects names it does not know. `query.*` parameters search the way the registry's
website does, ranking by relevance and matching related terms, so they can return more than you meant;
`filter.*` parameters restrict the set exactly. `uv run trialledger pull --help` lists examples.

The command ends with one of three outcomes: `0`, written; `1`, the pull or the write failed and nothing
was written; `2`, the query was refused before anything was sent. Requests are spaced 1.25 seconds apart.
The registry publishes no rate limit; if it asks TrialLedger to slow down, it does.

To check the build: `scripts/ci_local.sh` runs the full gate, and `uv run pytest -m live` runs one pull
against the real registry.

## Where the ideas come from

- **harmonizing** turned proteomics papers and repository records into a structured, scored spreadsheet. It
  contributed the ledger (keep every piece of evidence, richer than the output), the projection boundary
  (decide what crosses into a given output), and cross-field coherence (let one confident fact constrain
  others; never invent).
- **GSE** contributed the treatment of uncertainty: absence and silence are different things, an unresolved
  value keeps its possibilities open, conflicts are reported rather than voted away, and a discovered
  pattern only ever proposes a rule.
- **TriageGeist** encoded emergency triage as an almost entirely symbolic process, legible to the
  clinicians who would have to trust it. It contributed the three kinds of answer and the principle that
  any non-auditable step must be small, bounded, and checked.

The design in full: [`docs/THEORY_OF_THE_CASE.md`](docs/THEORY_OF_THE_CASE.md). Rules for anyone changing
the code: [`AGENTS.md`](AGENTS.md).
