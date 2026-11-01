# TrialLedger

**Gives an AI assistant real command of clinical trial data: every study matching a question gathered from
ClinicalTrials.gov into a verified record and a professional spreadsheet, and a new trial designed from that
evidence. No language model abstracts a trial or supplies a fact.**

Designing a clinical trial starts with what has already been done. Which trials have tested this drug, this class
of drugs, this disease? Whom did they enroll and exclude, what did they measure and when, and what happened? The
answers are public on ClinicalTrials.gov, but they are scattered across hundreds of records, and assembling them
properly means opening each record and copying its fields by hand, for every question. It is days of work, and it
is most of the work.

The common shortcut is to paste registry pages into a chatbot and ask for a summary. The summary reads well and
cannot be trusted: a language model paraphrases, and it can drop an exclusion criterion, merge two arms, attach a
time point to the wrong endpoint, or describe results that were never posted, with nothing to show which sentence
is wrong.

TrialLedger takes a different approach. It is a tool your AI assistant (ChatGPT, Claude or Gemini) picks up and
runs. TrialLedger does the work by fixed, checkable rules; the assistant answers you from what TrialLedger built,
and hands you the spreadsheet. Every value comes from the registry record or from a named rule, and says which.

## How you use it

You ask your assistant a question about trials, in your own words, and point it at this repository:

> *Using github.com/rohanvinaik/TrialLedger, find the completed Phase 3 trials of EGFR tyrosine kinase inhibitors
> in non-small cell lung cancer.*

The assistant installs TrialLedger in its own workspace, turns your question into a search, and shows you the
search before anything is gathered: each drug class expanded into its member drugs, with the subclasses it
includes named (so you can see, for instance, which antibodies a broad "kinase inhibitor" class brings in, and
exclude them); each disease class through the registry's own disease vocabulary; each drug by every name the
registry records it under. You confirm or narrow it. TrialLedger then gathers every study matching that search,
verifies the retrieval, and writes two things: a structured record your assistant answers your questions from,
and a workbook for you.

The workbook is a serious spreadsheet for professional reading, filtering, highlighting, editing and sharing:

- **Read me**: the search as run, the date the registry was read, and what each status means.
- **Trial index**: one row per trial, the landscape table you would circulate: phase, status, population and
  setting, investigational treatment and comparator, enrollment, primary outcome and time frame, whether results
  are posted, and any results publication the sponsor linked.
- **Trial review**: each trial's complete dossier, read top to bottom in the order of the questions a trial
  designer asks: population, inclusion and exclusion criteria, line of therapy, outcomes and time points,
  biomarkers, efficacy (anticipated and observed kept apart), safety, exploratory assessments, protocol
  language. Every statement is marked as what the record says, what that establishes, or what remains
  unresolved.
- **Eligibility, Outcomes and efficacy, Biomarkers, Safety**: listings for comparing across trials, one row per
  criterion, endpoint, result or event.
- **Across-trial findings**: criteria most trials share, exclusions that follow a drug's mechanism, and trials
  that differ in one design choice, each with how many trials support it out of how many could.
- **Evidence register**: where every value came from.

A value the record does not state says "Not stated"; results not posted say "Not posted"; anything TrialLedger
could not settle says "Unresolved" and why. Nothing is left blank, guessed or filled in.

## Layer one: gathering the evidence

For every trial matching the search, TrialLedger sets out what the record says: the population, the inclusion
and exclusion criteria in full, the line of therapy, the outcome measures with their time points, the biomarkers
and the role each plays, efficacy and safety results where the trial posted them, exploratory measures, and links
to the registry page, publications and any protocol or statistical analysis plan the sponsor posted.

It holds itself to the standards of clinical data management:

- **Every value has a source.** Each value traces to the registry field it came from or the named rule that read
  it, carries a fingerprint that lets anyone re-derive it, and says how it is known.
- **Unknown stays unknown.** An empty field is never read as "none". A trial without posted results says so, and
  shows any results publication the sponsor linked beside it.
- **Planned is never reported.** An outcome a trial registered is what it meant to measure, never evidence that it
  worked.
- **Records are checked against themselves.** A completed study should not carry an estimated completion date; no
  adverse event can affect more people than were at risk. Contradictions are raised as queries, never quietly
  corrected.
- **Complete or nothing.** A retrieval that cannot be completed and verified writes nothing, and every trial you
  asked for by number is accounted for: found, found under another number, or missing.

## Why the results can be trusted

TrialLedger is tested against the ways clinical data software produces plausible but wrong results: lost pages
of registry results, studies repeated or dropped, the registry changing mid-retrieval, a trial number that
silently matches another trial, spreadsheet cells that cut text or round numbers, values altered after the file
was written. Its rule is to preserve the source exactly or refuse to claim a complete result. The same scrutiny
applies to the code itself: every decision is a small, separately tested rule, the tests are checked by
deliberately altering the code to see that they catch it, and a test fails if any part of the program is never
actually used.

What this establishes is the faithfulness of the transcription: the record and the workbook say what the
registry says. Where TrialLedger reads clinical meaning from text (classifying an eligibility criterion, placing a
trial's line of therapy), the reading names the words it read, so it can be checked; such readings are marked as
readings, not as facts. TrialLedger makes no claim that the registry itself is correct, and none that its
accuracy exceeds a trained professional's: it is built so that its completeness, reproducibility and
traceability can be checked, which a manual spreadsheet's cannot.

## Layer two: designing the trial

Tell TrialLedger what you want to test, and it designs the trial.

It works the way an experienced trial designer thinks. Most of a protocol is not a matter of taste. Some of it is
simply correct, because it follows from the question. Much of it is what comparable trials have done, for reasons
the field has settled. Only a small part calls for judgment. TrialLedger treats each part accordingly.

**What is obviously correct, it builds.** Much of a design follows from what you have already stated. If the
outcomes are measured in the pregnant participant herself, the population is people who can become pregnant; a
study that enrolls partners states a different population, and gets different consequences. If "first-line" means
no prior systemic therapy for advanced disease, that follows for the eligibility criteria, while treatment given
earlier in the disease, such as after surgery, stays a separate question. These are deductions from explicit
premises, not decisions, and TrialLedger never treats a premise as given that you have not stated. It represents
eligibility as precise logical statements, keeping disease extent, treatment history and the role of the therapy
apart, derives what follows, shows each step with the premises it rests on, and flags any requirements that
contradict each other.

**What has been done before, it recommends, with the evidence.** Here TrialLedger works as a recommendation
engine, using classical methods rather than a language model. It finds the genuinely comparable trials, those
with the same indication, drug class, line of therapy and stage of disease, and reads what they did:

- the criteria nearly all of them share, which become standard parts of the design (leaving one out has to be
  justified)
- the exclusions that follow a drug's mechanism, such as the autoimmune exclusions typical of immunotherapy trials
- the endpoints and time points they used, compared like for like
- the event rates and effect sizes their posted results give, for planning the sample size
- the combinations of population, setting and mechanism no trial has yet tried

Every recommendation shows the trials and the numbers behind it, and evidence only ever ranks the options the
logic allows; it never overrides the logic.

**What calls for judgment, it offers to you.** After the logic and the evidence have done their work, a few real
choices remain, matters of strategy, taste or ethics. TrialLedger does not make them for you, and it does not hand
you a list of open questions either. Like a good butler, it works out which single decision would settle the most,
and offers it with a suggestion:

> *Would you care for biomarker selection in this trial? Comparable trials of this class have usually enrolled on
> it, and accepting would also settle the stratification and the screening test.*

You accept, choose otherwise, or answer in your own words, and the choice is recorded as yours. For most trials the
right answers are plain, and you can accept every suggestion at once.

The result is a draft trial in the same professional workbook form: the population and eligibility criteria,
endpoints and schedule, and the inputs for sample size, each element marked as deduced, recommended from
precedent, or chosen by you, with its reasons.

## What TrialLedger will never do

- Let a language model abstract a trial or supply a value as fact.
- Fill in a value it cannot trace to its source.
- Hide a gap, a conflict or a failed retrieval.
- Compare results that are not comparable.
- Treat a recurring pattern as established fact.
- Make a design choice that is yours to make.

## Running it yourself

TrialLedger needs Python 3.12 or later.

```bash
pip install "git+https://github.com/rohanvinaik/TrialLedger"
trialledger doctor
trialledger landscape --run egfr-nsclc --drug-class "EGFR tyrosine kinase inhibitors" --class-source ATC \
    --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED
```

The run folder then holds `landscape.json` (the record) and `landscape.xlsx` (the workbook), with the resolved
search in `scope.json`. `trialledger design --run <folder>` designs a trial from it. For a certified transcription
of the registry's own records, `trialledger pull` saves them with their spreadsheets, and `trialledger verify`
re-derives every value in a saved copy and names anything that no longer matches. Each command explains itself
with `--help`.

An assistant using TrialLedger reads [`AGENTS.md`](AGENTS.md) (or [`SKILL.md`](SKILL.md)); `trialledger mcp` serves
the same operations to any assistant that speaks the Model Context Protocol. Contributors start with
[`DEVELOPING.md`](DEVELOPING.md).

## Background

TrialLedger draws on earlier projects. **harmonizing** contributed the ledger: keep every piece of
evidence, richer than any output, and never invent. **GSE** contributed its handling of uncertainty: silence is
not absence, conflicts are reported rather than voted away, and a pattern only ever proposes a rule.
**TriageGeist** showed that a clinical process can be symbolic almost throughout and legible to the clinicians who
must trust it. **ModelAtlas** contributed the recommendation engine and its manner of closing: surface what
remains open, and suggest the decision that settles the most.

The full design is in [`docs/THEORY_OF_THE_CASE.md`](docs/THEORY_OF_THE_CASE.md).
