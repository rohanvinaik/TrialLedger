# TrialLedger

**Gives an AI assistant real command of clinical trial data: every relevant study gathered and verified, and a
new trial designed from that evidence.**

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
runs. TrialLedger does the work by fixed, checkable rules, and the assistant answers you from what TrialLedger
built. No language model abstracts a trial or supplies a fact: every value comes from the registry record or from
a named rule. It works in two layers: the first gathers the evidence, the second designs a trial from it.

## Layer one: gathering the evidence

You ask about some kind of trial: trials of a drug, a drug class, a mechanism, a disease or a family of diseases.
TrialLedger finds every matching study on ClinicalTrials.gov and sets out what each one says:

- the population: age, sex, healthy volunteers
- the inclusion and exclusion criteria, in full
- the line of therapy, where the criteria state it
- the outcome measures, primary, secondary and exploratory, each with its time points
- the biomarkers, and the role each plays: who may enroll, how response is measured, how safety is watched
- efficacy and safety results, where the trial posted them
- links to the registry page, publications, and any protocol or statistical analysis plan the sponsor posted

You receive it twice over: as a structured record your assistant answers your questions from, and as a
spreadsheet you can open, edit and share.

This layer is purely mechanical. It makes no judgments and no recommendations; its only job is to be correct,
and it holds itself to the standards of clinical data management:

- **Every value has a source.** Each value traces to the registry field it came from, carries a fingerprint that
  lets anyone re-derive it, and says how it is known: read directly from a field, computed by a named rule, or
  needing review.
- **Unknown stays unknown.** An empty field is never read as "none", and a trial without posted results says so.
  This matters: only about 13% of registered studies have posted results.
- **Planned is never reported.** An outcome a trial registered is what it meant to measure, never evidence that it
  worked.
- **Records are checked against themselves.** A completed study should not carry an estimated completion date; no
  adverse event can affect more people than were at risk. Contradictions are raised as queries, never quietly
  corrected.
- **Complete or nothing.** If any part of a retrieval fails, nothing is presented as finished.

**Status: working.** This layer runs end to end on the live registry today. Packaging it as a single step your
assistant takes from a chat app is being finished now.

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

The result is a draft trial: the population and eligibility criteria, endpoints and schedule, and the inputs for
sample size, each element marked as deduced, recommended from precedent, or chosen by you.

**Status: about half built.** The reasoning works end to end on a demonstration case, Phase 3 trials in non-small
cell lung cancer: standard criteria, mechanism-linked exclusions, untried combinations, pairs of trials that differ
in a single design choice, and exact logical reasoning over eligibility. Extending it to every kind of trial, and
assembling the full draft with its suggestions, are under way.

## What TrialLedger will never do

- Let a language model abstract a trial or supply a value as fact.
- Fill in a value it cannot trace to its source.
- Hide a gap, a conflict or a failed retrieval.
- Compare results that are not comparable.
- Treat a recurring pattern as established fact.
- Make a design choice that is yours to make.

## Using it

**Through an assistant.** This is how TrialLedger is meant to be used: point your assistant at this repository and
ask your question. The instructions your assistant follows are being finished now.

**From a terminal.** TrialLedger needs [uv](https://docs.astral.sh/uv/), which installs everything else:

```bash
uv sync
uv run trialledger resolve query.cond="non-small cell lung cancer" filter.overallStatus=RECRUITING \
    --json reading.json --out design.xlsx
```

`resolve` queries the registry live and writes the reading of every matching trial, and the comparison across
them, as a record and a spreadsheet. To keep a stored, independently verifiable copy instead, `pull` saves the
registry's records with their spreadsheets, `verify` re-derives every value in a saved copy and names anything that
no longer matches, and `profile` writes the comparison for a saved copy. Each command explains its options with
`--help`.

**How the rules are tested.** TrialLedger's rules are checked on fresh trials they were not written against.
`sample` draws a random sample across every disease category; `audit` reads each trial and puts narrow, closed
questions about its reading to a small local model. The model sees only the excerpt each question is about and
grades TrialLedger's reading of it; it never abstracts the trial, its answer never becomes a fact, and every
challenge it raises goes to a person. A share of the registry is set aside, never looked at during development, for confirming the
rules once they are frozen.

## Background

TrialLedger draws on earlier projects. **harmonizing** contributed the ledger: keep every piece of
evidence, richer than any output, and never invent. **GSE** contributed its handling of uncertainty: silence is
not absence, conflicts are reported rather than voted away, and a pattern only ever proposes a rule.
**TriageGeist** showed that a clinical process can be symbolic almost throughout and legible to the clinicians who
must trust it. **ModelAtlas** contributed the recommendation engine and its manner of closing: surface what
remains open, and suggest the decision that settles the most.

The full design is in [`docs/THEORY_OF_THE_CASE.md`](docs/THEORY_OF_THE_CASE.md). An assistant using TrialLedger
reads [`AGENTS.md`](AGENTS.md); contributors start with [`DEVELOPING.md`](DEVELOPING.md).
