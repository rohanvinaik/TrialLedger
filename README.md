# TrialLedger

**Clinical trial design from the registry up: every fact from source, every inference shown, every choice
offered rather than made for you.**

Designing a clinical trial begins with a question that sounds simple: what has already been done? Which trials
have tested this drug, or this class of drugs, or anything in this disease? Whom did they enroll and whom did
they exclude? What did they measure, and when? What happened? The answers are public, on ClinicalTrials.gov, but
they are spread across hundreds of separate records, and gathering them properly means opening each record and
copying its fields by hand, for every question, every time.

TrialLedger does that work, and then goes further. It is a tool that an AI assistant (ChatGPT, Claude or Gemini)
picks up: you ask your assistant about trials, the assistant runs TrialLedger, and TrialLedger does the work by
fixed, checkable rules. No language model reads or summarizes a trial at any point. The assistant reads what
TrialLedger has built, and answers you from that.

It works in two layers.

## Layer one: the assistant

The first layer is a purely mechanical operator whose only job is to be correct.

You want to know about some kind of trial: trials of a drug, a drug class, a mechanism, a disease or a family of
diseases. TrialLedger finds every matching study on ClinicalTrials.gov and lays out, neatly and completely, what
each one says:

| | What you get | Where it comes from |
|---|---|---|
| 1 | The population | Age range, sex and healthy-volunteer status are structured fields; gender, where a study reports it, is kept apart from sex. Further limits are in the eligibility text. |
| 2–3 | Inclusion and exclusion criteria | The eligibility text in full, split into inclusion and exclusion wherever the record uses the registry's standard headings, and shown whole where it does not. |
| 4 | Line of therapy | Almost never a structured field; usually only in the eligibility text ("previously untreated", "after progression on"), which is shown. |
| 5 | Outcome measures and time points | Primary, secondary and other pre-specified outcomes, each with its time frame, as registered. |
| 6 | Biomarkers | There is no structured biomarker field: biomarkers appear inside outcomes and eligibility, and each keeps its role (who may enroll, how response is measured, how safety is watched). |
| 7 | Efficacy | Posted results and statistical analyses per arm, where results were posted. |
| 8 | Safety | Serious and other adverse events per arm, with the numbers affected and at risk, where results were posted. |
| 9 | Exploratory measures | "Other pre-specified" outcomes, and the detail in arm and intervention descriptions. |
| 10 | Links | Each study's registry page, every linked publication with its type in the registry's own terms, and any protocol, statistical analysis plan or consent form the sponsor posted. |

You get this two ways: as a structured record (a JSON file) that your assistant answers your questions from, and
as a spreadsheet you can open in Excel, Numbers or Google Sheets, read, edit and share.

That is all this layer does. It makes no judgments and no recommendations. What it adds is discipline, the same
discipline a clinical data manager applies to source documents:

- **Every value has a source.** Each value traces to the field of the registry record it came from, or to a
  named rule applied to such fields, and carries a warrant: a digital fingerprint that lets anyone re-derive it.
- **Every value says how it is known.** It is *stated* (read directly from a field), *computed* (derived by a
  named rule, with the rule and its inputs shown), or *needs review* (not determinable from the sources, shown
  with links to what a reviewer would read, and never filled in).
- **Unknown stays unknown.** A field the registry left empty stays empty, and is never confused with a recorded
  "none". A study without posted results says so in so many words. That matters more than it might seem: on 31
  October 2026, only 80,808 of the 609,551 studies in the registry (13.3%) had results posted to it.
- **Planned is never reported.** A registered outcome measure is what a trial intended to measure; it is never
  presented as evidence of efficacy.
- **Records are checked against themselves.** The registry's fields constrain one another, as the fields of a
  case report form do, and contradictions are raised as queries rather than corrected (more below).
- **Nothing partial is presented as complete.** If any part of a retrieval fails, nothing is written, and the
  reason is given.

**Status: functional.** This layer runs end to end on live registry data today. Packaging it as a single
operation your assistant runs from a chat app is being finished now.

## Layer two: the designer

The second layer designs the trial itself.

Think about how an experienced trial designer works. Most of a protocol is not a matter of taste. Some of it is
simply correct: it follows from the question being asked. Much of it is what comparable trials have done, for
reasons the field has settled. Only a small part calls for real judgment. TrialLedger divides the work the same
way, and treats each part differently.

### What is obviously correct is built as-is

Some design decisions follow by logic from what you want to show. A study of outcomes in pregnancy enrolls only
people who can become pregnant: excluding men is not a judgment call, it is a deduction. A first-line trial
enrolls people with no prior therapy for advanced disease. A pediatric study bounds the age of its population.

TrialLedger represents eligibility as precise logical statements (what is required, what is excluded, of whom,
and when), so it can derive these consequences exactly and show the steps each one rests on. If two
requirements contradict each other, it says so before any design is written, and names the pair that conflict.

### What has been done before is recommended, with the evidence

Much of the rest is precedent: what comparable trials have done. Here TrialLedger works as a recommendation
engine, using classical recommendation methods rather than a language model.

- **Finding the comparable trials.** Every trial has a position along clinical dimensions: its condition, more or
  less specific in the medical hierarchy; its drug, within its drug class; its line of therapy and stage of
  disease. "Comparable" is a precise requirement ("the same indication, or one level more specific"), and from
  there TrialLedger follows the connections between trials: trials of the same drug, trials sharing the same
  unusual criteria or the same class of endpoint. A rare shared criterion counts for more than a universal one.
  Each comparable trial comes with the reason it was found.
- **Standard practice.** A criterion that nearly every comparable trial includes is standard, and it is carried
  into the design with the share of trials behind it. A design that leaves a standard out carries a cost: the
  omission is named, so it has to be justified.
- **What the mechanism calls for.** An exclusion that recurs across trials of one drug class, but not across the
  disease as a whole, points to a risk tied to that mechanism: trials of PD-1 inhibitors exclude active
  autoimmune disease far more often than other lung-cancer trials do. Such exclusions are recommended for a drug of
  that class, with the comparison behind them. One that every trial shares (pregnancy, for instance) points to
  nothing in particular.
- **Endpoints and time points.** The primary endpoint and its time point are recommended from what comparable
  trials measured, matched like for like: two trials that both report "change in HbA1c" are not comparable if one
  measures at 12 weeks and the other at 52.
- **What it takes to succeed.** Event rates and effect sizes for planning come from the posted results of
  comparable trials, only where the comparison is like for like.
- **Where the gaps are.** Combinations of indication, line of therapy, population and mechanism that no trial has
  studied, or that only failed or ongoing trials occupy; and "near misses", pairs of trials alike in every known
  respect but one design choice, which show that choice in isolation. An empty combination is a lead, not proof
  of unmet need.
- **Precedent and inheritance.** Criteria and endpoint wording that many later trials reuse weigh more than one
  trial's choice. What is established for a drug class carries over to a new member of it, weakened by distance
  and labelled as inherited, never as fact.

One rule holds throughout: a recommendation never decides what is allowed. What the design may contain is
settled by the facts and the logic; the evidence only orders what remains, and every recommendation shows the
trials and the numbers behind it.

### What calls for judgment is offered to you, politely

After the logic and the evidence have done their work, a few real choices remain: places where more than one
design is sound and the choice is a matter of taste, strategy or ethics. TrialLedger does not make those choices,
and it does not leave you a list of open questions either. It behaves rather like a good butler.

It looks at what is still open and works out which single decision would settle the most. A choice of setting
that fixes the line of therapy, the prior-therapy criteria and the comparator all at once comes before a choice
that settles only itself. Then it asks that one question, and offers a suggestion: the option with the strongest
support, and, among equally supported options, the one that settles the most. With it, it says what accepting
would settle:

> *Would you care for biomarker selection in this trial? Most comparable trials of the class enrolled on it, and
> accepting it also sets the stratification and the screening assay.*

You accept, choose another option, or answer in your own words, and your choice is recorded as yours. Then it
offers the next. For most trials the right answers are obvious, and you can accept every suggestion in one step.

The result is a draft trial: a protocol synopsis, the eligibility list, the endpoint and schedule tables, and the
inputs for sample size, with every element showing its basis: deduced, recommended from precedent, or chosen by
you.

**Status: about half built.** The reasoning this layer rests on works end to end on a test case, Phase 3 trials
in non-small cell lung cancer, as a demonstration: standard criteria, mechanism-linked exclusions, untried
combinations, near-miss pairs, declared expectations and their deviations, and exact logical entailment over
eligibility. Extending the reasoning to every kind of trial, and assembling it into a full draft with the
recommendations and the polite questions, are being built.

## Why it is built this way

A common shortcut in clinical development is to paste a ClinicalTrials.gov link into a chatbot and ask it to
summarize the design. The answer reads well and cannot be checked against its source. A language model
paraphrases; it does not abstract. It can drop an exclusion criterion, merge two arms, attach a time point to the
wrong endpoint, report an estimated date as an actual one, or describe results that were never posted, and
nothing in the answer tells you which sentence is wrong. For a design decision, a fluent answer with an unknown
error rate is worse than no answer, because it looks finished. And done properly by hand, the same work takes
days for every question.

Clinical research already has the discipline this calls for. Trial data is abstracted from source documents,
every value is source-verifiable, and edit checks raise queries on values that contradict each other before
anyone analyzes them. TrialLedger applies that discipline to the registry itself, and lets an assistant do the
abstracting at the speed of a question. The designer layer extends the same principle to design: logic where
there is logic, evidence where there is precedent, and a person wherever there is genuine choice.

## How it stays correct

### The ledger: the source record, kept whole

Every element of every record is entered in a ledger, the way a monitor logs source data: the value as written,
where it sits in the record, and its role (an inclusion or an exclusion criterion; a primary, secondary or other
pre-specified outcome; the arm a count belongs to). The ledger is deliberately richer than any output, and nothing
is ever removed from it. Every view TrialLedger produces is derived from the ledger, and every derived value says
what it came from.

### Edit checks: each record checked against itself

A study marked completed should not carry an estimated completion date. Every intervention an arm names should be
declared by the study. No adverse event can affect more participants than were at risk. A minimum age cannot
exceed the maximum. Each check is reported as consistent, in conflict, not applicable, or not checkable, the last
whenever a value it needs is missing, malformed or too imprecise to decide (two partial dates whose months
overlap, say), so a check never passes for lack of evidence. A conflict is shown as a query and never silently
corrected, because a contradiction in a record is exactly where an error in the data, or a fabricated value in
someone's summary, reveals itself.

Seventeen checks are built, each quoting the registry's own definition it rests on. Five run on every record,
because the registry states their relation as a rule or defines one field from another: a completed or
terminated study's primary completion and study completion dates are typed actual; a multi-site study with a
recruiting site is itself recruiting; the reasons participants did not complete account for all of them; and the
results flag agrees with the results submission date. The other twelve, including the arm, adverse-event and age
checks above, follow from the definitions without being stated as rules; they are built, tested and listed, and
run once the project's founder approves each by name.

### Publications: linked, labelled, never overstated

The registry links each study to its publications, of three types. A study's sponsor enters some of them and marks
each as reporting the study's results or not (the registry's types "result" and "background"). The registry adds
others itself (type "derived") and states no role for them: a derived publication may report the results,
describe the protocol, or analyse the data later. Derived links are the most common kind: on 30 October 2026,
126,368 studies carried derived publications, 99,393 background and 43,671 result. TrialLedger shows every
publication beside its study with its type in the registry's own terms, and never presents a derived publication
as a results paper.

For studies whose results were never posted, publications are the next source (designed, not yet built): figures
a paper states explicitly can enter the ledger as publication evidence, each carrying the exact sentence it came
from and marked as coming from the paper. Where a paper and the registry disagree, both are shown; what a paper
does not state plainly stays a review item. A study still running has no results anywhere yet, and the
spreadsheet says exactly that.

### Warrants: every value carries its basis

Every value carries a warrant, a SHA-256 fingerprint committing to what produced it: for a value read from a
record, the study's record, the value's place in it and the value itself; for a computed value, its rule, the
exact code that derived it, and the warrants of its inputs. Before any folder is written, every cell and warrant
is re-derived from the record and compared; if anything differs, nothing is written. Later, `trialledger verify`
repeats the derivation and names any edit: a changed value, a count replaced by TRUE, a changed link. A folder is
verified against the version of the code that wrote it, which the folder names. A warrant proves derivation, not
authorship: anyone can re-run TrialLedger, so to rely on a folder later, keep its record fingerprint. Whether a
rule is right rests on its tests, and every decision is pinned by tests that a mutation tester (Detective)
confirms are complete.

## What it will never do

- Have an AI read, summarize or interpret a trial.
- Fill in a value it cannot source.
- Round, truncate or clean a value to make it fit.
- Hide a gap, a conflict or a failed retrieval.
- Compare outcomes that are not comparable.
- Treat a recurring pattern as established fact.
- Make a design choice that is yours to make.

## Status, part by part

| Part | State |
|---|---|
| Pulling studies; the record file and the registry's spreadsheet; the completeness guarantees | Built and verified, against the live registry |
| Ledger, the five approved edit checks, the review workbook, warrants and `trialledger verify` | Built and verified, against the live registry ([`add-review-workbook`](openspec/changes/archive/2026-10-31-add-review-workbook/)) |
| The twelve further edit checks | Built and tested; each waits for the founder's approval |
| Typed criteria, each trial's design coordinates, drug classes and the profile across a pull (`trialledger profile`) | First slice built, on the Phase 3 NSCLC trials of 2015–2024; every relation awaits the founder's approval ([`add-coherence-engine`](openspec/changes/add-coherence-engine/)) |
| Declared expectations and their deviations, the review queue, near misses, the provenance of every rule (`trialledger resolve`) | First slice built on the NSCLC development trials; confirmation on a population no rule was written against is next ([`add-design-surprise`](openspec/changes/add-design-surprise/)) |
| Eligibility as precise logical statements, with exact entailment (what a trial's criteria require, exclude or leave open) | Representation and entailment built and tested; compiling them from criteria text is being built ([`add-scoped-assertions`](openspec/changes/add-scoped-assertions/)) |
| Reading criteria for every kind of trial (all condition categories, interventions, purposes and phases; children, pregnancy, healthy volunteers) | Contracts, registry and evaluation built; the general packages are being built ([`add-bank-coverage`](openspec/changes/add-bank-coverage/)) |
| Publication evidence for studies without posted results | Designed |
| The assistant operation: a chat app's assistant runs TrialLedger from this repository, answers from the record and hands over the spreadsheet | Being built ([`add-agent-operation`](openspec/changes/add-agent-operation/)) |
| The designer: the full draft, the recommendation engine and the polite questions | Designed; its reasoning is the parts above ([`add-design-synthesis`](openspec/changes/add-design-synthesis/)) |

## Using it

### Through an assistant

This is how TrialLedger is meant to be used: point your assistant at this repository and ask it your question. The
instructions the assistant follows are being finished with the assistant operation above.

### From a terminal

TrialLedger needs [uv](https://docs.astral.sh/uv/), which installs Python for it:

```bash
uv sync
uv run trialledger resolve filter.ids=NCT03829332 --json -
uv run trialledger resolve query.cond="non-small cell lung cancer" filter.overallStatus=RECRUITING \
    --json reading.json --out design.xlsx
```

**`resolve` is the main command.** It queries ClinicalTrials.gov live, from one snapshot of the registry,
complete or not at all, and reads every matching study without saving the registry's records:

- **Eligibility**, each criterion split out and typed by fixed rules, with what the eligibility text says about
  itself: whether there is any, whether it is split into inclusion and exclusion, and whether the record says
  either list is abbreviated ("Key Exclusion Criteria", "other protocol-defined criteria may apply"), says it is
  complete, or says nothing. Saying nothing never counts as complete.
- **Each trial's design coordinates** (setting, prior lines of therapy, biomarker selection), as the values its
  own criteria still allow.
- **Each experimental drug's class** from the National Library of Medicine's RxClass, and beside it, never merged
  with it, its other drug-class axes: what RxNorm says the intervention's own name is (an ingredient, a salt, a
  brand, a combination; another name in the record may confirm that, never supply it); its ATC and
  chemical-structure classes, each counted only when asserted of that very concept (a brand does not inherit its
  ingredient's class); and the targets its own entry states (anti-PD-1, EGFR inhibitor; a word naming another
  drug, such as carboplatin, is no target), aligned to ATC by a cited crosswalk.
- **Each intervention's modality and cell properties**, from its own entry; a patient's history ("no prior
  CAR-T") is never the intervention's modality.
- **Outcomes**, and each declared expectation's observation and deviation.
- **Near misses**: another trial with the same setting and drug classes that differs in exactly one known design
  choice, such as the performance status it admits. An unknown never matches, and each pair names both sponsors
  and start years, because shared templates and eras explain many differences. The near misses are given again
  with drug classes compared by ATC, labelled as alignment, never as a match, along with the drugs that share a
  chemical-structure class.
- **A review queue**: what the rules could not cleanly resolve (an unclassified drug, a coordinate the criteria
  contradict, an unresolved or deviating observation, a record that says its criteria are abbreviated), each as a
  question with closed answer options and its evidence, for an expert to answer. TrialLedger never forces those
  answers.

`--json` writes this reading as JSON (to a path, or `-` for the screen; the default). `--out` writes
`design.xlsx`, which adds the profile across the matched trials: how often each criterion appears, which criteria
are standard, which track a drug class, which settings and classes no trial occupies, and results grouped like
for like, plus a Drug Axes sheet.

How often a criterion appears is given two ways, never merged: the share of records that state it, and the range
its share among the trials' full criteria could take. A record that is silent about a criterion (its eligibility
empty, untyped by any rule, abbreviated, or silent about its own coverage) has not said the trial lacks it. So a
criterion is standard only when the low end of that range reaches the threshold, not standard only when the high
end falls short, and unresolved otherwise; since no rule yet establishes that a silent trial lacks a criterion,
"not standard" does not yet occur. A primary endpoint is not a criterion, and only the share of records stating it
is given. A criterion tracks a drug class only when it is stated more often in that class even counting every
abbreviated record among the other trials as stating it; when such records could reverse the comparison, it is
shown as unresolved.

Only RxClass answers are cached, in `~/.cache/trialledger` (or `$TRIALLEDGER_CACHE`), each with its request,
retrieval time and RxNav release; after an update, `resolve` asks RxNav again about every name already cached,
four to six spaced requests a name. `resolve` ends with `0`, resolved; `1`, the query failed; `2`, the query was
refused.

**The registry changes daily.** Sponsors edit their studies, so the same query can read differently next month.
Every reading therefore records what it read: the registry's data timestamp and API version, each study's
fingerprint, a fingerprint over all of them, and the code version, so a later run can name exactly which studies
changed. When a reading will back a decision, a report or an audit, add `--keep snapshot.json` to save the exact
records read, or use the stored path below, which also certifies the files.

**The query.** Each `NAME=VALUE` is one of the registry's own search parameters (`spec/ctg-oas-v2.yaml`), sent
exactly as written; the registry rejects names it does not know. `query.*` parameters search the way the
registry's website does, ranking by relevance and matching related terms, so they can return more than you meant;
`filter.*` parameters restrict the set exactly. One kind of query is refused before it is sent: when a search term
consists only of NCT numbers, the registry silently ignores every filter in the same query, so the answer would
look filtered and not be. Requests are spaced 1.25 seconds apart; the registry publishes no rate limit, and if it
asks TrialLedger to slow down, it does.

### Keeping a certified copy

When a stored, verifiable record is wanted, save a query to a folder and work from the folder:

```bash
uv run trialledger pull query.cond=sarcoidosis filter.overallStatus=RECRUITING --out my_studies
uv run trialledger verify my_studies
uv run trialledger profile my_studies
```

`pull` writes four files, and only when the pull is complete and consistent: every page arrived in both formats;
the number of studies equals the number the registry reported, with none twice; the two formats list the same
studies; the registry did not refresh its data during the pull; temporary errors were retried and resolved; and
both workbooks, read back cell by cell, hold exactly what the record derives. If any of these fails, nothing is
written and the reason is printed. The four files:

- **`studies.json`**: the complete registry record of every study, exactly as sent, under a header recording the
  query, the release of the registry's data and the time of retrieval.
- **`studies.csv`**: the registry's own spreadsheet for the same studies. Its columns are the registry's choice,
  and eligibility and safety are not among them, which is why the review workbook exists.
- **`review.xlsx`**: the review workbook, the ten points above study by study, with a sheet for each part of the
  record a reviewer reads: Studies, Eligibility, Outcomes, Arms, Interventions, Sites, Outcome Results, Analyses,
  Adverse Events, Event Groups, Participant Flow, Baseline, Publications, Documents, and the edit checks with the
  registry's words for each. Each workbook's About sheet gives the kind and source of every column.
- **`record.xlsx`**: every value of every study, one per row, under the registry's own category and field names,
  so nothing goes unpresented. It is its own file because it is the largest: Google Sheets opens at most 10
  million cells in one spreadsheet, which this file reaches at about 300 results-heavy trials and the review
  workbook at about 500. TrialLedger names any file over that cap.

A value a spreadsheet cell cannot hold exactly (text with characters the format forbids, text longer than a cell
holds, a number a cell would round) is never cut, cleaned or rounded: its cell says why, and where the value is in
`studies.json`.

`pull` ends with `0`, written; `1`, the pull or the write failed and nothing was written; `2`, the query was
refused. `verify` re-derives a saved folder and ends with `0`, certified; `1`, not certified, each difference
named; `2`, no TrialLedger record. It rewrites both workbooks to compare them, so it takes about as long as the
original write. `profile` writes the same `design.xlsx` as `resolve --out` beside a saved folder, changes none of
its files, and refuses a folder whose record no longer matches its fingerprints (`1`) or that holds no record
(`2`). It reads each drug's RxNorm identity, ATC and chemical-structure classes as already cached, and marks a drug
never looked up as "not looked up", never as having no class; `profile --fill-axes` asks RxNav first (four to six
spaced requests a name, over an hour for a few hundred trials).

### Auditing a reading

TrialLedger's rules are checked against fresh trials they were not written on, with a small local model as a
grader, never as a reader.

- **Drawing a sample.** `trialledger sample --seed S --out sample.json` draws, live, a stratified random sample of
  interventional trials started from 2010 to the day of the draw (or to `--present YYYY-MM-DD`; the date is
  recorded, and the audit uses it too), across the registry's condition categories. A hashed 30% of trials is
  reserved for confirmation and never drawn here.
- **Asking targeted questions.** `trialledger audit sample.json --out DIR --model qwen3:8b --budget N` takes the
  trials one at a time: it reads each live (the record kept), resolves it, writes the questions its reading
  raises, and asks a local [Ollama](https://ollama.com) model each in turn. Each question asks one thing and shows
  only the text it is about: a typed claim with its criterion and headings; a criterion no rule typed, asked which
  known concepts it states (or that it states something outside them); an outcome's endpoint class against its
  title, and each time point against its time frame ("up to 24 months" is a window over which events are counted,
  not a measurement at 24 months; any other time is asked only as a time point, with no role read into it); a
  drug's target that its own entry states. The model only grades: its answers never change a reading, and every
  challenged answer goes to a reviewer.
- **Drug classes are checked, not asked.** Before reading a trial, the audit copies the RxClass answers for its
  drugs, with when each was retrieved, into its own folder (`rxclass.json`; an answer already there is never
  replaced), and checks the reading's classes against that kept copy, recording whether they match or differ. A
  drug with no class is recorded as one RxClass knows no class for, or as one whose lookup failed or was never
  answered.
- **Nothing in the text goes unread.** The audit's manifest lists every piece of each trial's eligibility text and
  confirms that only whitespace lies between the pieces; any text no piece covers is named, with its place and its
  words, even when pieces also overlap (each overlap is named too).
- **The sample's balance is checked.** `balance.json` counts the trials by phase (combined phases such as Phase
  1/Phase 2 kept as written, whatever order the record lists them in), intervention type and primary purpose.
  When the whole of a sample that declares its balance check has been audited, each registry value no drawn trial
  holds is checked live against the registry; where the registry holds such trials, one is drawn as a labelled
  supplement (seeded, with its own inclusion probability, and its union probability if drawn for more than one
  value, declared in sample.json) and audited too. A partial audit, or a sample drawn before the declaration,
  leaves its empty values "not checked". A value the registry returns no trial for is called empty only when its
  query form has been tried live (the dated list in `sample.VERIFIED_FORMS`); otherwise it is "query unverified".
  Every row of the manifest, the questions and the answers says whether its trial was drawn as the sample or as a
  supplement, and `trialledger pilot` draws only from the sample unless given `--include-supplement`.
- **Confirmation is done once, on unseen trials.** The reserved 30% is split into three confirmation batches, each
  used once. `trialledger sample --confirmation-batch N --inspected FILE ...` draws from one batch and leaves out
  every trial of each population named with `--inspected` (a record folder, a sample or an audit's balance check),
  since a rule cannot be confirmed on trials it was written against; each list is kept with its file's fingerprint,
  and the number left out is counted. The draw is refused unless the code is committed with no uncommitted
  changes, so the confirmation names exactly the code it tested. The repository's own ledger,
  `confirmation_ledger.json` (no other file is read), records the batch as used by that code, named by a
  fingerprint of its source and its commit, and the draw commits the ledger on its own. The batch is refused to
  any other code; the same code may draw it again.

### Checking the build

`scripts/ci_local.sh` runs the fast gate (`--deep` adds the Detective audit of every pinned decision and the
vulture scans; it needs local checkouts of Detective and Wesker). `.venv/bin/python scripts/push_checks.py install`
installs the pre-push hook that runs the gate before every push, and `uv run pytest -m live` runs pulls against the
real registry.

## Where the ideas come from

TrialLedger is built on information theory and data geometry. Nothing is thrown away, because no summary can know
more about a trial than its record contains. Unknown stays unknown: an unresolved value is the set of
possibilities still open, narrowed only by evidence or an approved rule. Significant means informative: a
criterion every trial shares is background; one that varies with the mechanism being studied is signal. And
trials are points in a design space whose dimensions are the clinical ones (population, phase, line of therapy,
mechanism, endpoint and time point, safety): comparators are neighbors, a cohort is a region, a niche is an empty
region.

It draws on the founder's earlier projects:

- **harmonizing** turned proteomics papers and repository records into a structured, scored spreadsheet. It
  contributed the ledger (keep every piece of evidence, richer than the output), the projection boundary (decide
  what crosses into a given output), and cross-field coherence (let one confident fact constrain others; never
  invent).
- **GSE** contributed the treatment of uncertainty: absence and silence are different things, an unresolved value
  keeps its possibilities open, conflicts are reported rather than voted away, and a discovered pattern only ever
  proposes a rule.
- **TriageGeist** encoded emergency triage as a process that is symbolic almost throughout, legible to the
  clinicians who would have to trust it. It contributed the three kinds of answer and the principle that any
  step that cannot be audited must be small, bounded and checked.
- **ModelAtlas** contributed the designer's recommendation engine (finding what is admissible first and ranking
  it separately; positions in hierarchies; connections followed through shared features; rarity weighting) and
  its closing manner: surface what remains open, and suggest the decision that settles the most.

The design in full: [`docs/THEORY_OF_THE_CASE.md`](docs/THEORY_OF_THE_CASE.md). Rules for anyone changing the
code: [`AGENTS.md`](AGENTS.md).
