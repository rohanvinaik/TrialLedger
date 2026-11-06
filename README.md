# TrialLedger

**Clinical trial evidence you can trace. Design consequences you can check.**

[![CI](https://img.shields.io/github/actions/workflow/status/rohanvinaik/TrialLedger/tests.yml?branch=main&label=CI&style=flat&labelColor=334155)](https://github.com/rohanvinaik/TrialLedger/actions/workflows/tests.yml) [![Passing tests](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Ftests.json&style=flat&labelColor=334155)](https://rohanvinaik.github.io/TrialLedger/) [![Decision-logic mutation testing](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Fmutation.json&style=flat&labelColor=334155)](https://rohanvinaik.github.io/TrialLedger/)

[![Line coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Fcoverage.json&style=flat&labelColor=334155)](https://rohanvinaik.github.io/TrialLedger/) [![Branch coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Fbranches.json&style=flat&labelColor=334155)](https://rohanvinaik.github.io/TrialLedger/) [![License](https://img.shields.io/badge/License-MIT-blue?style=flat&labelColor=334155)](LICENSE)

<sub>[Verification & methodology](https://rohanvinaik.github.io/TrialLedger/)</sub>

Tell your AI assistant which trials interest you. TrialLedger gathers their ClinicalTrials.gov records into
a reference workbook, preserves the source wording and checks the records against the registry's own rules.
Then use the same conversation to work through your design: who could enroll, which criteria conflict,
what the evidence leaves open and what changes when you revise a choice.

You receive a decision list and a spreadsheet you can share with colleagues. Each choice has its evidence,
computed consequences and remaining questions. You make the clinical decisions; the program makes their
logical consequences inspectable.

## Two reasonable criteria. No possible patient.

Suppose you build a lung-cancer trial by borrowing entry restrictions from two real studies:

| Borrowed restriction | Source |
|---|---|
| Require brain metastases | The [AZD3759 study, NCT03653546](https://clinicaltrials.gov/study/NCT03653546), requires MRI-documented CNS metastases that include brain metastases |
| Exclude brain metastases | [ARCHER 1050](https://clinicaltrials.gov/study/NCT01774721) excludes any history of brain or leptomeningeal metastases |
| Require ECOG performance status at most 1 | A separate restriction in your draft |

For this simulated draft, we explicitly encode the first two choices as requiring and excluding brain
metastases in the same entry population. TrialLedger returns:

```text
INCONSISTENT
Deciding premises: excludes-brain-metastases, requires-brain-metastases
```

The ECOG premise is not implicated. Remove either conflicting restriction and the remaining criteria admit
a possible patient. The program identifies the pair that makes enrollment impossible and leaves the choice
of repair to you. It does not use the contradiction to claim that any arbitrary conclusion is true.

The source records are real; the merged draft is deliberately simulated. Translating their wording into
these draft premises is an explicit step, not an automatic reading certified by the solver. The AZD3759
record also distinguishes measurable and non-measurable CNS lesions; this example does not turn that into
a universal measurable-lesion requirement. [Run the check and inspect its sources](examples/template-merge/).

## Six trials. The same missing question.

An exploratory, single-reviewer review of registry histories reported six trials—ARCHER 1050, AURA3,
FLAURA, EXCLAIM-2, BR.26 and RADIANT—amending eligibility during recruitment to clarify how prior adjuvant
or neoadjuvant treatment counts. The recurring question: **does “no prior systemic therapy” include treatment before surgery,
after surgery, or only treatment for advanced disease?** In a TrialLedger conversation, the assistant makes
those readings explicit and the engine checks their consequences before you adopt one.

A smaller wording change shows what that buys. For the neuropathy clause examined in
[IFCT-GFPC 0502](https://clinicaltrials.gov/study/NCT00300586), ask whether a grade-3 patient is ruled out:

| Explicitly typed exclusion | Answer under this restriction |
|---|---|
| Grade 2 peripheral neuropathy | No: `UNDETERMINED` |
| Grade 2 or higher peripheral neuropathy | Yes: `REFUTED` |

Both answers reproduce through the public CLI. The reading and the consequence query are explicit steps;
the engine does not silently supply “or higher”. The six-trial pattern is a retrospective finding, while
broader estimates of what would have been caught remain hypotheses, not measured detection rates.

## Useful information can exist without a reported answer

IPASS reports 607 safety-evaluable participants and 590 quality-of-life-evaluable participants in a
609-person treatment cohort. It does not report their overlap. **If those two subsets refer to the same
609 people, at least 588 and at most 590 must be in both.** Only two people are outside the safety subset,
so at most two of the 590 can be outside it.

That is new information obtained from the relationship between the reported values. No patient-level data
or assumption about correlation is needed. The population correspondence remains an explicit premise; the
exact overlap remains unknown. [The source-bound calculation and its warrants](docs/POWERFUL_QUESTIONS.md#the-joint-table-is-missing-can-we-still-know-who-must-overlap)
are inspectable.

This is the project's information-theoretic thesis in practical form: **keep the information the evidence
actually supplies, including the possibilities it rules out.** Missing detail can leave a precise range.
Conflicting requirements can identify a precise repair. The remaining freedom becomes a clinical decision.
Your assistant handles the conversation; the symbolic engine checks the explicit relationships and names
what decided each answer.

## An assistant's reading stays a reading

Suppose one of two selected trials documents an exclusion and the other remains unresolved. TrialLedger
can report **1 of 2 documented, with a possible full-criteria range of 50–100%**. It cannot call the silent
trial a trial without that exclusion. A proposed reading of the second trial stays pending until accepted;
it does not quietly enter the accepted count. [Execute that distinction](examples/reasoning-admission/).

If your assistant misses a criterion **and leaves the trial unresolved**, the result loses precision rather
than inventing absence. That protection depends on retaining the unresolved status; a mistaken claim that
a record is completely encoded can still mislead. Likewise, an exact quotation proves where the words came
from, not that the reading has the right population, negation or meaning. Material readings are shown to
you as premises, and their consequences remain conditional on those premises being right.

You can therefore ask both “What follows if we adopt this reading?” and “What can we establish without
adopting it?” Defaults stay labelled and overridable. WHO PS and ECOG stay separate unless an explicit
equivalence premise connects them. A common practice remains a description, not a rule your trial must follow.

## The reference workbook is a deliverable on its own

Ask for named trials, or a subset by drug/class, condition, phase and status. A source-backed class search
expands to its documented members and names; the preview shows what will be searched. The workbook gives
you a dossier per trial and shared listings for eligibility, interventions, endpoints, baseline, results,
participant flow and safety.

A disease-class search can miss a trial that the registry never tagged with that class. TrialLedger
therefore compares its identifiers with a condition-text search by default. Additional hits stay candidates
for review; the assistant can inspect them and explicitly request the union. Neither route establishes a
complete clinical landscape, and a comparison that did not run never means there were no additional hits.

| What you can inspect | What TrialLedger preserves |
|---|---|
| The actual criterion | Verbatim wording, source headings and addresses, including awkward or contradictory source entries |
| The meaning of a number | Its population, local group, denominator, unit and reporting period |
| Missing information | “Not stated,” “not posted” and “not applicable” remain different; planned outcomes remain separate from results |
| The registry's internal consistency | 17 structured checks, with the fields, rule and outcome for each |
| The workbook's derivation | Retained source responses; `verify` checks that the record and workbook reproduce from them |

The consistency checks can expose a completed study with estimated completion dates, an arm naming an
undeclared intervention, affected participants exceeding those at risk, or non-completion reasons that
do not account for the reported total. Their rules cite registry definitions or direct consequences of
them. **“Not checkable” stays visible; it is never counted as a pass.** These checks establish consistency
within the record, not whether the registry matches events in the real world.

Your assistant answers from `landscape.json`; your colleagues receive `landscape.xlsx`. You can stop here,
or continue into a design review. TrialLedger is [MIT-licensed](LICENSE).

## From a question to a shareable design review

1. **Gather and inspect.** Choose the comparison set and get the reference workbook. Your assistant brings
   you the exact passages and values relevant to the design.
2. **Choose and check.** Make the intended restriction precise. Check its consequences, compare readings
   or leave an unresolved question open. “Allowed by this restriction” is different from “all eligibility
   requirements have been checked.”
3. **Revise and share.** Change a premise and rerun. Export `decision-list.md` and `design-review.xlsx`, with
   evidence, alternatives, consequences and origins. An ECOG edit can change a remaining requirement beside
   a brain-metastasis answer without changing that answer's verdict; the review distinguishes the two.

The working core also checks declared endpoint prerequisites, assessment timing, finite action rules and
collection requirements after treatment discontinuation. The broader protocol workflow is being connected
in the [current implementation plan](openspec/changes/connect-protocol-design-workflow/HANDOFF.md).
Complete automatic protocol writing remains unfinished.

The [ICH M11 / CDISC USDM roadmap](docs/M11_USDM_ROADMAP.md) proposes standards-based protocol import,
checked revisions and bidirectional exchange, followed by broader M11 document support. This is a future
direction, with explicit delivery stages and compatibility boundaries—not a current interoperability claim.

<details>
<summary>How the reasoning works, larger worked sessions and precise trust boundaries</summary>

## How it thinks

Published definitions, explicit premises and relationships between observations can settle questions that
no individual field answers. TrialLedger keeps the rest open and brings consequential choices to you.
Five ideas explain how.

### 1. Every answer carries its source

Each statement you receive comes from one of four places:

- **The record:** what ClinicalTrials.gov says, with a link to where it says it.
- **Computed:** what follows, by exact calculation, from statements you have confirmed. These confirmed
  statements are called *premises*.
- **A reading:** an interpretation of wording, by your assistant or proposed for discussion. It can be
  explored, but it is not relied on as a premise until you confirm it.
- **Your choice:** a design decision you have made, recorded as yours.

A computed answer is never stronger than its weakest premise. If it depends on a default convention or a
working assumption, it is labelled that way. If it depends on a reading you haven't confirmed, it is not
treated as settled at all.

### 2. Certainty comes from ruling things out

TrialLedger becomes certain of a computed answer only when the evidence leaves no alternative. A real
example: IPASS's baseline tables list a total of 1,217, a WHO PS 2 value of 126 and a never-smoker value of
1,140. Neither table gives the joint number. **If** those values are participant counts describing the same
1,217 patients, at least 49 must be both (126 + 1,140 is 49 more than 1,217) and at most 126 can be. Nothing is
assumed about whether the two traits are related. What becomes certain is what has been ruled out: fewer than
49 is impossible. The exact number stays open.

Some conclusions rest on a declared default rather than on evidence, such as a standard convention for
describing an NSCLC treatment setting, or on a working assumption you have accepted. These are labelled
**settled by default**, and you can override them.

### 3. Open questions are held, not filled

When the evidence leaves something open, TrialLedger neither guesses nor throws the question away. It keeps
it, because an open piece can combine with another piece later. Think of sudoku: a square that could be 3
or 7 isn't guessed. If two squares in the same row can each only be 3 or 7, then no other square in that row
can be 3 or 7, even though neither of the two is solved yet.

Trial records behave the same way. IPASS gives a month-level start date without saying whether it is actual or
estimated. TrialLedger can't supply the missing label. Under the registry's own rules, though, an actual start
makes the date-order check consistent and an estimated start makes it not applicable, so either way a conflict
is ruled out. In the invented teaching session below, patients at ECOG 2 were enrolled and one person at ECOG
2 was rejected as ineligible. Assuming enrolled patients met eligibility, the enrollments rule out any
performance-status cutoff below 2, and the rejection rules out "ECOG ≤2 and nothing else". Together they show
that no rule based on performance status alone explains both, without saying what else was involved.

Unlike sudoku, a trial design has no single correct solution. The squares still open at the end are your
decisions. TrialLedger collects them in a **decision list**.

### 4. Sameness is your call

The premises you confirm are combined automatically. A claim that two things are the same, though, is a
clinical judgment, and TrialLedger never makes one on its own: that two tables describe the same patients;
that WHO PS 2 corresponds to ECOG 2; that a scan was the scheduled assessment rather than an unscheduled one;
that a comparator's restriction should apply to your trial. Matching names or matching totals are not
enough. Until you confirm a sameness claim, its arithmetic stays visible as "if these are the same patients,
then …" and nothing settled depends on it.

### 5. Counts describe; they never decide

TrialLedger can tell you how often comparable trials state a criterion, how many are silent on it, whether
it is more common with a drug class and what is unusual among them. These counts come with their
denominators, and silence is counted separately from absence. But "most trials do this" never makes
anything required or forbidden in your design. Weighing what matters is expert judgment, and it stays with
you.

This is also why the reasoning can be exact. Once the source values are established as participant counts
for the same population, the overlap bounds follow by arithmetic. The count roles and population binding
remain premises; the numeric field type alone does not settle them.

The distinctions matter in everyday use. A performance-status statement beneath **“Crossover Inclusion
Criteria”** is shown with that exact source heading beside it. The heading helps you notice the question;
it does not decide whether the statement governs initial entry. If one reading applies at entry and another
only at crossover, TrialLedger shows their different consequences and names that scope difference while
keeping an independent registered age restriction usable. Choosing a reading still does not rewrite the record.

Likewise, a supplied phrase such as “previously treated” may be accepted without choosing between a
previously treated and a maintenance setting. The answer now shows when an input has no applicable rule,
is redundant, narrows the possibilities, or prevents a default. You can then state the intended restriction
as a separate design choice. More supplied information does useful work only when its meaning and consumer
are explicit; acceptance alone is no assurance that your intended question was checked.

The [five fresh design conversations](acceptance/clinical-handoffs-2026-11-03/) exercise these handoffs in
headache, pulmonary fibrosis, allergy, lung cancer and hypertension, with source readings and simulated
choices kept distinct. Their complete checks and revisions remain available beside the decision lists.

## How the work divides

| Stage | What happens | Who does it | Why it can be trusted |
|---|---|---|---|
| **Gathering** | Registry records are retrieved, preserved and laid out in a reference workbook. The registry's own published rules are applied, such as date-order checks. | TrialLedger, operated by your assistant | Values are faithful copies, and checks follow published registry rules. The workbook can be rebuilt from the saved records. No clinical reading is supplied. |
| **Translation** | Your criteria, your questions and readings of trial text become precise premises. | Your assistant, with you | Registry values are used as recorded. Every reading, sameness claim and choice is restated to you in clinical words before it is relied on. This is the only stage where an AI's reading enters the reasoning. |
| **Computation** (inference) | Confirmed premises and evidence are combined to rule possibilities out. The result says what follows, what conflicts and what stays open. | TrialLedger | The calculation is exact and gives the same answer every time. Each result names what decided it. |

The open decisions then come back to you. The reference workbook is useful on its own: you can stop after
gathering.

## What you can ask

| You might ask | What you get | Kind of answer |
|---|---|---|
| "Make reference sheets for IPASS and ARCHER 1050." "Find completed Phase 3 EGFR-inhibitor trials in NSCLC." | A workbook with a dossier per trial and shared listings, plus a matching evidence file | From the record |
| "Who could enroll? What was measured, and when? What were the results and safety by group?" | Exact registry wording, with groups, denominators, units and time frames | From the record |
| "Does this record contradict itself?" | The registry's own consistency checks, with the fields compared | From the record, by published rules |
| "Does our draft exclude ECOG 2 patients?" "Could this patient enroll?" | Excluded, allowed, or allowed but not required, naming the deciding criterion | Computed from your criteria |
| "Do our criteria contradict each other?" | The conflicting criteria, side by side | Computed |
| "This wording could mean two things. What would each allow?" | Each reading's consequences, and which readings the fixed evidence rules out | Computed under each reading, kept separate |
| "The comparator's eligibility text is thin. What does its baseline data tell us?" | Which candidate restrictions its enrolled patients rule out | Computed, under the sameness claims you confirm |
| "Neither table gives the joint numbers. Can we bound them?" | A range, such as 49–126 | Computed, under the sameness claims you confirm |
| "What treatment setting do these NSCLC criteria imply?" | Disease extent, prior treatment and line of therapy, with defaults labelled | Computed, with defaults labelled |
| "How common is this exclusion in these trials? Is it more common with this class? Which trials differ only in this? Where are the gaps?" | Counts and ranges over a comparison set you agree, with silent trials shown | Description of the comparison set |
| "Is this a good choice?" | The computable parts (does it fit, how common is it, what does it rule out), separated from judgment | Mixed, each part labelled |
| "Did the drug work?" | The posted results, read from the record; any interpretation is marked as your assistant's reading | From the record, plus a labelled reading |

The [worked questions](docs/POWERFUL_QUESTIONS.md) show several of these executed, with real and invented
examples labelled. Not available yet: writing a complete protocol, reading linked publications and checking
the registry against the real world.

## What you receive

- **`landscape.xlsx`**, the reference workbook. Start with Trial index and Trial review, then explore
  eligibility, interventions, planned outcomes, posted results, statistical analyses, baseline, participant
  flow, groups and safety. Numbers keep their study groups, denominators, units and reporting periods.
  Planned outcomes stay separate from posted results, and observational and expanded-access studies keep
  their own details. Missing information stays visible: "not stated" never becomes "none".
- **`landscape.json`**, the matching evidence record your assistant answers from, linked back to the
  registry. The complete registry responses are kept too.
- **`design-review.xlsx` and `decision-list.md`**, when you continue into design work. For each declared
  choice: the question in clinical words, alternatives, computed consequences, deciding evidence and
  premises, what remains open and any recorded selection. A revision distinguishes a changed question,
  changed answer, changed deciding support, remaining requirements, and changes to wording, attribution or evidence context.
  The accompanying manifest and complete saved checks let a colleague
  trace the handoff. Your assistant can keep conversational context in `working-brief.md` beside it.

A partial profile can also answer **“What else must hold?”** In an invented draft requiring BMI at least
30, or BMI at least 27 with one of four listed conditions, BMI 28 still needs **one of those conditions**.
It does not need all four, and the profile's silence does not mean the patient lacks them. Likewise,
confirmed prior-treatment and washout rules can expose a required interval without claiming it was met.
Each displayed requirement has its own proof and scope. Discovery is bounded; this is not complete screening.

Questions and option labels remain visibly yours beside the actual represented profile. Exact comparator
passages can be attached to a decision without becoming its criteria. A note interpreting a passage, or
calling something a gap, remains a proposed caller annotation; an adopted restriction needs its own premise.
The coherent decision view keeps those channels together for your assistant and the exported review.

Permission is another channel worth keeping. An invented draft can permit stable inhaled treatment without
requiring anyone to take it, while a separate rule requires three months of stability for those who do.
The review shows the permission, its condition and its origin beside the remaining eligibility checks.
Tightening stability to four months changes the three-month profile's answer without making treatment
mandatory. Proposed readings remain unconfirmed; including their results in a review does not adopt them.
Open items name the option they concern: allowing exactly two weeks and longer does not also allow one week.

The design review is a separate handoff. Your reference workbook and registry evidence remain unchanged.
Supporting analyses also have readable summaries: adaptive-rule gaps and forbidden selections, population
flow bounds, endpoint collection gaps and explicitly linked definitions. Their assumptions, populations and
exact checks travel with them; they do not disappear into a sheet of diagnostic codes.
With a source record supplied, the review also lays out baseline values by their local groups, preserving
population, unit and denominator context. An arm and a total are never silently added together.

## How far to trust each answer

| Kind of answer | Right when… | What could still be wrong | How to check it |
|---|---|---|---|
| From the record | It is a faithful copy, which is checked and can be replayed | The registry entry itself; anything the registry doesn't contain | Follow the source link |
| Published-rule check | The registry's own rules say so | Only what those rules cover | Ask which rule and fields were compared |
| Computed | Its premises are right; the calculation is exact and tested | A premise confirmed in error | Ask "which premises decided that?" |
| Settled by default | The default or working assumption fits your trial | The default may not fit | Override it and rerun |
| A reading | Never certified; used only inside a labelled "if this reading holds" check | The interpretation itself | Confirm it, reject it, or compare readings |
| Description of a comparison set | The counts are exact for the set you agreed | Whether those trials are truly comparable; silence isn't absence | Ask how many trials were silent |
| Your choice | It is yours, recorded as yours | Not applicable | Change it and rerun |

### Why a casual conversation can carry exact reasoning

Your assistant translates between clinical language and explicit premises; TrialLedger performs the declared checks.
Registry values are used as recorded; every reading, sameness claim and choice is restated to you in clinical
words, taken from the check actually being run, before anything relies on it. TrialLedger does the
calculation, the same way every time. The question of trust therefore shifts from "do I trust the AI?" to "are
these statements about my trial right?", which you are qualified to answer. When you change a premise, the
checks are rerun; an old answer is never relabelled as if it had checked the new one.

Two limits matter. First, TrialLedger reasons from the evidence, definitions and rules actually represented.
A registry record cannot supply a missing biological relationship or establish today's standard of care.
Second, translation can go wrong. A misread criterion yields an exact answer to the wrong question, which is why you
always see the premises restated. Each check is also saved as a file that a technical colleague can audit, and
at any point you can ask which premise decided an answer.

The saved labels are your assistant's account of the conversation: the program cannot independently tell
whether you confirmed a reading. Your accepted wording and its origin should therefore remain beside the
check. In demonstrations, a simulated choice is labelled as simulated. Copied registry values do not need
your approval, and an unchanged premise does not need repeated confirmation.

## A design session in practice

> “The comparator's eligibility entry is thin. Can we work out what it actually constrains before we
> choose our population, treatment sequence and assessments?”

This is an executable teaching case. Every study datum, drug identity and definition in it is **invented**.
Its [inputs and saved results](examples/partial-evidence/) run through the same operations your assistant
uses with real registry evidence.

**1. Gather the evidence and settle what it means.** The comparator reports 200 randomized participants: 40
at ECOG 2 and 180 never smokers. Its two cohorts together include everyone, with no overlap; cohort A has
140 and cohort B's count is omitted. The median age, an exact midpoint, is 65. An analysis population
contains 160 of the 200 randomized participants. A screening log records one person at ECOG 2 rejected as
ineligible, with no other details. Other records place the end of induction before randomization and the
first dose within seven days after it. One arm's product contains ingredients A and B. A dated definition
places marker A within family F, and family F within the qualifying-marker class. The adopted change-score
endpoint needs observed measurements at baseline and week 12; baseline is recorded and week 12 is unknown.

Your assistant keeps each source location, population, time point and definition. You settle what the
evidence means: which counts describe the same patients, whether the summaries are exact, and how many
enrolled patients might have been exceptions to eligibility. Here you accept, as a working assumption, that
there were no exceptions, so results depending on it are labelled settled by default.

**2. Test competing explanations together.** TrialLedger checks twelve candidate designs against that
evidence. Each piece of partial evidence does different work:

| Evidence | What it forces | Candidate it rules out |
|---|---|---|
| 40 ECOG 2 and 180 never smokers among the same 200 people | **20–40** have both | Excludes everyone with that combination |
| Cohort A has 140; cohorts A and B make up all 200 | Cohort B has **60** | Admits cohort A only |
| Exact midpoint median age 65 among 200 assessed | **At least 100** are 65 or older | Requires everyone to be under 65 |
| An analysis population is a stated 160-person subset of the 200 | **40** randomized people are outside that analysis | Assumes everyone randomized was analysed |
| Induction ends before randomization | Reversing that order contradicts the timeline | Randomizes before induction ends |
| The assigned product contains A and B | Its ingredients include both | Represents the arm as ingredient A alone |
| Marker A → family F → qualifying class | Marker A qualifies under that edition of the definition | Places marker A outside the class |
| The endpoint needs two observed measurements | An unavailable week-12 measurement conflicts with it | Uses the endpoint with no possible week-12 observation |
| One ECOG 2 patient was rejected as ineligible | ECOG alone can't explain that rejection | Defines eligibility solely as ECOG ≤2 |

Each result keeps its limits. Forty people outside an analysis are not thereby forty dropouts. The unknown
week-12 measurement stays unknown, and an imputed value does not count as observed under this definition.
One rejected ECOG 2 patient does not mean every ECOG 2 patient is excluded.

**3. See what remains open.** Nine candidates are ruled out. Three remain: adults requiring the qualifying
marker with ECOG 0–2; the same with ECOG 0–3; and adults with ECOG 0–2 and no marker requirement. Asked "Must
ECOG be ≤2?", TrialLedger answers **undetermined**: the surviving designs disagree, so the choice is yours.
The twelve candidates were declared for this exercise and don't cover every possible real protocol, so
surviving the checks is not proof of the comparator's actual criteria.

**4. Make a choice and check it.** You choose adults with ECOG 0–2. A separate
[check of your draft](examples/partial-evidence/draft-request.json) confirms that it rules out ECOG 3, naming
your performance-status criterion. Widen it to 0–3 and rerun: ECOG 3 is now allowed but not required. That
checks this one restriction, not every requirement for enrollment.

**5. Revise the evidence, too.** If the screening rejection can't be attributed to eligibility, the
"ECOG only" candidate is no longer ruled out; it is kept as unresolved. If up to 20 enrolled patients could
have been exceptions, an overlap of at least 20 no longer guarantees an eligible patient with both traits;
with up to 19 exceptions it still does. Your assistant reruns the checks and updates the decision list. The
original evidence never changes.

The handoff is the decision list:

| Decision | Evidence and computed consequence | Status |
|---|---|---|
| Performance-status range | The comparator enrolled ECOG 2 patients. Your 0–2 restriction excludes ECOG 3; widening it to 0–3 allows it. | **Chosen by you: 0–2**, with the check saved |
| Marker selection | The class relation is settled. Surviving designs differ on requiring the marker, and the single rejection doesn't decide it. | **Open:** should your population require it? |
| Endpoint assessments | The adopted definition needs observed baseline and week-12 measurements. Week 12 is unknown, and imputation alone doesn't satisfy the definition. | **Open:** settle the assessment plan or change the definition |

## The same method on a real record

The [IPASS walkthrough](examples/source-bridge/) applies these ideas to the retained registry record:

- **Directly from a structured field:** the registered minimum age of 18 years settles the registry's
  restriction to participants aged 18 or older. The eligibility prose stays as written. It is silent about
  performance status, so it supplies no cutoff.
- **Overlap of two baseline counts:** if the WHO PS 2 value, the never-smoker value and the total are
  participant counts describing the same patients, a reading for you to confirm, their overlap is
  **49–126**. This does not recover an eligibility cutoff, and WHO PS stays WHO PS.
- **Two analysis populations:** 607 safety-evaluable and 590 QoL-evaluable patients among 609 on gefitinib
  give **588–590** in both, if both tables describe the same cohort. The
  [workflow investigation](docs/SOURCE_INFORMATION_RESOLUTION.md) and its
  [saved checks](examples/source-workflows/) cover this and other analysis-population questions.
- **A schedule with two readings:** "every 42 ±7 days from randomization" gives a first window of days 35–49
  under either reading. The second window is days 77–91 if every tolerance is measured from randomization, or
  70–98 if each interval restarts at the previous visit. That choice is about how your schedule should work.

Each item keeps its source location and stays labelled as a reading until you confirm it. The registry
record itself is never changed.

The same reasoning can test the assumptions that make a count useful. Suppose a record reports a protocol
violation, and a separately supported reading identifies one enrolled person who failed entry eligibility.
That is incompatible with assuming **zero eligibility exceptions across that population**. It does not put
the person in the WHO PS 2 subgroup, and it does not tell us the maximum number of exceptions. The system
keeps the reported failure, its possible meanings, the scoped count and the unresolved ceiling together;
it blocks conclusions that depend on a contradicted assumption. A broad withdrawal label alone supplies no
entry-eligibility meaning.
Uncertainty stays local: one ambiguous failure cannot contradict a separately warranted allowance of five
under either reading. The system can retain that usable conclusion while leaving the failure's meaning open.

Population comparisons receive the same check before their numbers reach design reasoning. Under an explicit
same-arm interpretation, 609 people cannot be a subset of 590; 590 can fit within 609. Compatibility does not
prove that those are the corresponding populations. A wrong arm or record version leaves the interpretation
unresolved, with the arithmetic still visible. See [how these warrants reach their consumers](docs/REASONING_CONSUMERS.md).

## Three more decisions hidden in the paperwork

**“Who reached which stage?”** Being allowed to proceed to a treatment stage is different from actually
entering it. If explicitly bound counts place **144 people outside completion** and **one person outside
dosing**, TrialLedger keeps both answers, with their separate populations and time points. It does not call
all 144 untreated or identify which person received no dose. A documented population relationship permits
that subtraction; a pathway saying patients *may* proceed does not. A count that fits the relationship does
not prove that the relationship is true.

**“Does our dose table tell us what to do in every case?”** In an invented six-person cohort, suppose your
table assigns an action for zero dose-limiting toxicities and for two through six, but none for **one out of
six**. Once you declare those seven possible counts, TrialLedger can establish that the table leaves a case
uncovered. It also checks whether two applicable rows prescribe different actions and whether each listed
action is possible under your stated constraints. You decide the missing action. Covering this finite table
does not prove that a sequence of dose decisions eventually stops, or that the actions are clinically best.

**“What do we need to measure after treatment stops?”** TrialLedger keeps this question separate
from whether an analysis is possible. An explicitly adopted definition may require a week-12 outcome after
treatment discontinuation. A plan to stop collecting it is then a collection-plan mismatch; an actually
unavailable relevant outcome is a different finding. An outcome not required for that particular question,
an outcome whose relevance is unresolved, and a measurement that cannot exist after an event are kept
separate too. Merely naming a strategy such as “treatment policy” supplies no measurement requirement.
Stopping collection alone does not prove that estimation is impossible. These checks retain each channel's
own warrant; they do not certify a statistical estimator or treatment-effect estimate.

The executed [bipolar extension](acceptance/design-session-walkthrough-stages-bipolar-2026-11-03/README.md),
[early-phase AML](acceptance/design-session-walkthrough-decision-aml-2026-11-03/README.md) and
[dermatitis endpoint](acceptance/design-session-walkthrough-estimand-dermatitis-2026-11-03/README.md)
walkthroughs show the distinction between registry evidence, explicitly hypothetical designs and computed
consequences. They retain the sampled records' missing rules and unresolved meanings.

These checks support the continuing conversation and its decision list. A managed session now keeps the
declared sources, premises, analyses and decisions together and replays them when the design changes.
Complete automatic protocol writing remains unfinished.

## Keep the investigation and the design connected

**“What evidence would resolve the disagreement?”** Suppose two possible eligibility explanations remain:
adults with ECOG at most 2, and the same restriction plus a marker requirement. TrialLedger can ask for
an accepted marker-negative participant, which would contradict the marker requirement under a warranted
eligibility bridge. It can also ask for an adult ECOG-2 participant rejected for eligibility. That could
contradict the first explanation **if it claims to be the complete eligibility rule**, while the second
could explain rejection through the unspecified marker. No marker value is invented.

These are requests to investigate, not reports of actual patients. Each keeps its accepted or rejected
sign, the premises needed to make it decisive, and a place to look. Rejections may require a screening or
adjudication record beyond the registry. The least-specified separating profiles come first; that ordering
does not predict which evidence exists. A limited search and a shortened list of found requests are
reported separately. The [invented executable example](examples/design-session/) shows this handoff.
The [Parkinson's investigation](acceptance/design-session-walkthrough-evidence-parkinson-2026-11-03/README.md)
works through real age wording with a conditional older-age allowance and explicitly hypothetical profiles.

**“If we change our population, what else changes?”** The managed session reruns every declared analysis
from the revised premises and compares the consequences. Historical comparator restrictions stay attached
to their sources; adopting one for the new trial requires a separate premise. A historical unknown becomes
an evidence question. A new-trial question becomes a design choice only after genuinely different options
have been shown feasible under the represented constraints.

The [observational-diabetes walkthrough](acceptance/design-session-walkthrough-session-diabetes-2026-11-03/README.md)
uses three real registry records and an explicitly invented draft. Revising the draft from age 18+ to 65+
changes its age consequences while all historical source-age answers remain unchanged. An Ontario-specific
65+ reading stays proposed and local to Ontario. The source's conflicting design and follow-up descriptions
remain visible. The session retains both snapshots, complete checks, origins and the consequence comparison;
your assistant explains them in the working decision list. This checks the declared age restriction, not a
complete protocol's eligibility or clinical suitability.

**“Is the answer different, or did we ask something different?”** A revised question is kept separate
from a revised result. Adding “no other listed condition” to a patient profile changes what was asked,
even when both answers remain “allowed but not required.” Rewording its label alone does not establish
that two clinical questions mean the same thing.

The deciding basis can change while the answer stays fixed. Under a **simulated** requirement for at
least 90 days since prior treatment, a 60-day profile is ruled out. Changing that requirement to 180 days
still rules it out, but the saved check now names the revised rule and its actual content. An unchanged
answer must not hide that change. Wording, attribution and evidence attached for context are tracked
separately; adding background evidence does not quietly add a new restriction. The complete record of
input changes remains available beside this comparison of consequences.

Remaining requirements have their own comparison too. Widening ECOG from 0–1 to 0–2 can change what still
needs checking beside an allowed brain-metastasis profile while leaving that profile allowed. The review
says **remaining requirements changed; verdict unchanged**, rather than implying that its CNS answer moved.

### A rule can cover every case and still break a declared safety rule

In an invented adaptive protocol, a table can specify an action for every combination it lists and still
select a dose when the team has explicitly forbidden it. TrialLedger can now check those negative
specifications directly and show the offending situations. The guarantee concerns the declared variables
and rules: it does not supply a missing safety variable or establish clinical safety.

The same discipline applies when two parts of a protocol use different thresholds. A lower threshold for
starting a safety assessment can deliberately precede the threshold defining an endpoint. The designer can
declare that the endpoint must imply the trigger, or that two definitions really must be equivalent, and
check that relationship with attributed premises. Different numbers alone do not establish a contradiction.

The [asthma walkthrough](acceptance/design-session-walkthrough-docs-asthma-2026-11-03/README.md) revises the
representation itself: it adds a missing rival reading of background and relief therapy while retaining
the original. Their consequences differ, both remain proposed, neither establishes daily relief use, and
the independent registered age restriction stays settled. The remaining question is visible for the person
to resolve.

### Three useful answers inside one open question

Consider a heart-failure draft with different NT-proBNP requirements for participants with and without
atrial fibrillation. In the executed HFrEF workflow, the **draft premises are simulated choices**, separate
from the retained DAPA-HF and EMPEROR-Reduced registry records.

- Asked whether **900 pg/mL** fits, the draft does not give an unconditional yes or no. The computation
  nevertheless proves a useful condition: **if that profile fits these restrictions, the participant must
  not have atrial fibrillation**. A condition is retained with what proves it; the open headline does not
  erase it or become a claim that all eligibility has been checked.
- A draft statement that background SGLT2 treatment **is permitted** remains visible beside the answer.
  It imposes no requirement to use it and cannot defeat a separate exclusion. Being mentioned and being
  required are different information.
- DAPA-HF's posted NYHA table has **20, 23 and 43** class-IV participants in its two arms and total. Those
  are three source cells, not 86 people. Under an explicitly accepted working assumption aligning the
  baseline population with entry eligibility, the total
  rules out a candidate allowing only classes II–III when fewer than 43 exceptions are allowed. Allowing
  43 exceptions removes that particular elimination; it does not prove the candidate is the actual protocol.

Widening the simulated draft from NYHA II–III to II–IV changes two of its seven clinical answers. All seven
audit objects change because their inputs changed. The review shows both facts separately, so a colleague
can see the actual consequences without mistaking bookkeeping changes for seven new clinical findings.
The [implementation evidence](openspec/changes/deliver-warranted-clinical-handoffs/evidence/session-revisions/wiring-and-work.md)
records the executed checks and their scope.

</details>

## A protocol plan in practice

> “Our week-12 visit is allowed from day 77 to day 91, but the plan collects through day 80. Does that
> cover what we say, which way should we fix it, and what changes if we extend it?”

This is an executable teaching case. The plan, its adoption and every choice are **invented**; the checks
are real. Your assistant starts from discovery, not from memory:

```bash
echo '{"operation":"describe","view":"protocol","detail":"full"}' > describe.json
trialledger reason --request describe.json
```

The reply lists the built checks, the data each protocol object carries, the claims each check may make and
a runnable example per family. Your assistant saves `examples.decisions` as `plan.json`. It holds a
week-12 assessment (nominal day 84, permitted days 77–91), a collection plan through day 80, one schedule
check, and a comparison of two collection plans with the drafted plan selected.

**1. Prepare, then run.** Preparation expands the compact objects without computing anything and keeps
what it defaulted:

```bash
trialledger reason --request plan.json --store reasoning --compact          # artifact 864b5eed…
trialledger reason --prepared 864b5eedf6c642159b60aa3df55c51fdd38ba98d6a50cf39d3c32d6a18e8cd45 \
    --store reasoning --compact                                              # artifact c01d4aca…
```

**2. Read the schedule check by claim.** For the drafted plan, “given your declared intervals”:

| Claim | Outcome | Why |
|---|---|---|
| A visit exists | satisfied | days 77–80 are both permitted and collected |
| The nominal day 84 is collected | not collected | collection ends at day 80 |
| The full permitted window is covered | uncovered | days (80, 91] are permitted but not collected |

```bash
trialledger reason-result --store reasoning --part address \
    --id c01d4acaafafdc40f6d231e5bcbce0b04a07f8564c2ec655ca6f66116625f0b4 \
    --address /response/result/protocol/decisions
```

**3. Compare the two plans.** The decision `collection-plan` compares “Through day 80” with “Through day
91”. The drafted plan is a **repair choice** still open: its gaps are plan gaps for you to settle, not policy
conflicts. “Through day 91” is compatible under the declared checks, but it is a replacement held in its own
hypothetical frame, so its result is withheld from unconditional application. The drafted selection stays
yours; nothing here picks the plan for you.

**4. Revise on instruction.** The person says: collect through day 91. That is an explicit instruction to
change an adopted plan, so the new content is a new version of the collection, and its adoption is recorded
with it. Content changed under an unchanged version is refused (`changed_protocol_object_version_required:collection`).

```json
[
 {"op":"replace","path":"/protocol/objects/2/data/availability/0/upper","value":"91",
  "origin":{"kind":"user_choice","ref":"user:invented instruction to collect through day 91 (teaching example)","source":null,"analysis":null}},
 {"op":"replace","path":"/protocol/objects/2/version","value":"invented-v2"}
]
```

```bash
trialledger reason-revise --store reasoning --edits edits.json --revision collect-to-91 \
    --id c01d4acaafafdc40f6d231e5bcbce0b04a07f8564c2ec655ca6f66116625f0b4
```

The review lists the two adoption edits as `adoption_of_instructed_version`. In `answer_diff`, the
schedule check changed on its verdict, support, origin and scope axes: the nominal-day and full-window
claims moved from not collected / uncovered to satisfied. A what-if under a `hypothesis` origin would not
adopt, and its earlier adoption would read as stale instead.

**5. Hand it over.**

```bash
trialledger reason-export --store reasoning --out review-out \
    --id 0bcdcfc3befa70c00d2f081896f77fef971a945263b47383b28da5138f121406
```

The export returns the review workbook (with a schedule-of-assessments sheet), the readable decision list
and the manifest under `review-out/review`. The assessments section reports “no conflict or open repair
choice found in the declared checks”.

**What this does and does not establish.**

- **Working checks.** Exact schedule coverage over declared intervals; finite declared-variable policies
  (coverage, exclusivity, prohibition, invariant and termination claims, with bounded witnesses); exact
  fixed-n single-arm binomial probabilities; plan comparisons; definition relations; revision axes; delivery.
- **Encoded assumptions.** A binomial result applies only when its three roles (fixed n, independent
  binary outcomes, alignment of the endpoint with the design) are declared as premises; the arithmetic is
  always shown. Policy inputs from outside the model are re-chosen freely at each step. Coverage concerns
  the declared variables and states only, so a covered policy is not a safe policy. Standing, adoption and
  origin are the caller's attribution; TrialLedger authenticates none of it.
- **Deferred.** General statistical design (sample-size search, optimisation), adaptive, survival and
  cluster methods (a declared external method stays *not computed*, with its missing inputs named), the
  automatic protocol writer and prose compilation. Not computed is not a finding.

A clean schedule check says the declared intervals line up. It does not say the visit is clinically
appropriate, the protocol is valid or complete, or anyone has approved it.

## What isn't built yet

- **Automatic reading of eligibility prose.** Today you and your assistant settle readings together;
  TrialLedger compiles only the structured minimum and maximum age directly.
- **Complete protocol writing from a brief.** It is designed and partly built; the operations above, including
  the protocol checks, are its working core. Adaptive, cluster and survival calculations, sample-size search and
  optimisation are not built.
- **Scoring how significant a line of design reasoning is.** This is designed. Today's "unusual" measure
  is a simpler count within a comparison set.
- **Reading linked publications.** A link marks a place to look, not something TrialLedger has read.

The [full design](openspec/changes/add-design-synthesis/design.md) and [theory](docs/THEORY_OF_THE_CASE.md)
give the complete map.

## Getting started with your assistant

Give your assistant this repository and your clinical request. It checks whether its environment can run
Python, write report files, access the required sources and deliver the workbook. When those capabilities
are available, it handles installation, the search preview and retrieval. If something essential is missing,
it should explain the specific gap and the next practical step before promising a workbook.

A repository link alone does not install the program or give a chat app execution or network access.
If you have a technical colleague configuring a local assistant, the details are below. Assistants should
read [AGENTS.md](AGENTS.md) or [SKILL.md](SKILL.md); contributors should read [DEVELOPING.md](DEVELOPING.md).

<details>
<summary>Installation, local commands and assistant integration</summary>

Python 3.12+ and writable report storage are required. Install in the assistant's own environment:

```bash
pip install "git+https://github.com/rohanvinaik/TrialLedger"
trialledger doctor --run egfr-nsclc
trialledger landscape --run egfr-nsclc --drug-class-id L01EB --class-source ATC \
    --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED --preview
```

Inspect the resolved scope, then repeat without `--preview`. ATC `L01EB` is the source class used for this
example; the preview shows its current members. Ordinary class phrases can return source-catalogue choices;
select a class explicitly, even for a sole suggestion, then preview its ID in a new run. Specific trials use:

```bash
trialledger landscape --run my-trials --ids NCT00322452,NCT01774721
```

These are IPASS and ARCHER 1050. `landscape --help` lists request fields, including dates and study types;
request JSON can also exclude selected subclasses. A repeated request resumes, while a changed request needs
a new run folder. Exit 0 means complete/previewed; 3 awaits relay responses; 2 names a refusal/stop; 1 gives
failure/retry advice. Completion does not mean every requested identifier was found.

Prefer direct mode, in which TrialLedger fetches itself. Relay bridges missing network access only: it still
requires execution, report storage and access to complete response bodies. Fetch only the addresses in
`next.json`, saving each full response byte-for-byte unchanged. Excerpts, copied tables or reconstructed JSON
cannot substitute. Relay resolves search terminology but skips gathered-study drug enrichment. The harness
checks response structure and identity, not every value against a second live copy.

`trialledger verify FOLDER` replays retained reporting inputs and checks the record and workbook, including
formatting and links, under the writing version. It establishes reproducibility, not registry truth.
`trialledger pull` separately retains complete registry JSON/CSV with archival workbooks.

Saved evidence can also be read through the CLI with the same bounded access as MCP:

```bash
trialledger record my-trials --part studies
trialledger record my-trials --part study --nct NCT00322452
trialledger record my-trials --part address --address /studies/0/criteria --limit 10
trialledger record egfr-nsclc --part coverage --address /comparison/text_only
trialledger record egfr-nsclc --part coverage --coverage-file union_request
```

Coverage addresses are inside the selected saved coverage document, separate from workbook addresses.
The same MCP `record` calls use `part:"coverage"`, optional `coverage_file:"union_request"` and `address`.
The returned digest identifies the exact saved bytes; it establishes neither disease membership nor a
reading's truth. A union is offered only by a complete current comparison; reading it does not execute it.

Follow every returned page or text continuation needed for the question; an address directory is navigation,
not the underlying evidence. Local source-heading context is copied with exact offsets, without interpreting
entry, crossover or cohort scope. Verification names supported legacy formats rather than silently adding
new context to an old report.

Trial names need not occupy the registry's acronym field. A request file containing
`{"params":{"query.term":"\"CodeBreaK 200\""}}` uses the supported registry text search;
preview it with `trialledger landscape --run name-search --request REQUEST_FILE --preview`, then verify
the returned identity before using the record.

Search acquisition defaults to at most 1,000 studies and 100 registry requests. The first identifier count
is checked before bulk retrieval. An intended larger scope can declare, for example,
`"acquisition":{"max_studies":2000,"max_registry_requests":200}` in request JSON. The policy is retained
for resume; it does not change the clinical search. Raw `pull` exposes `--max-studies` and
`--max-registry-requests`. These guard NIH acquisition, not local reuse of complete retained evidence.

Retries and resumed comparison work share that request allowance, including failed direct attempts.
`landscape --run FOLDER --compare-condition-text --compare-plan` previews only the remaining work from
retained responses. Missing or malformed annotation data stays unresolved. Source-catalogue membership
and explicit `class_drug_additions` (CLI `--class-drug-addition`) remain distinct; additions are your scope
choices, not newly discovered catalogue facts.

For an assistant client that supports local MCP servers:

```json
{
  "mcpServers": {
    "TrialLedger": {
      "command": "/absolute/path/to/trialledger",
      "args": ["mcp", "--root", "/absolute/path/to/trialledger-runs"]
    }
  }
}
```

Use absolute paths. Tools are doctor, scope, landscape, save_fetch, record, reason, reason_result,
reason_revise and reason_export. The assistant handles
record paging: at most 50 entries and a default 24,576-byte record reply. Oversized nested values return exact
addresses to follow; long strings have lossless text continuation. Saved records are complete. These are
conversation-output limits, not a limit on the whole process's memory or a change to requested study scope.

Reasoning uses `trialledger reason --request FILE` or MCP `reason(request)`. Start with
`{"operation":"describe"}` for a short overview, then an operation view such as
`{"operation":"describe","view":"entailment"}` for its task card and invented runnable example.
Add `"detail":"schema"` for structural machine shapes and named field contracts, or `"detail":"full"`
for that operation's complete guide. Views `worked_session` and `full` retain the demonstration and full
manual. View `delivery` describes retained results, revisions and exports. The
[operator workflow](docs/CLINICAL_WORKFLOW.md) connects the calls without requiring internal Python imports.

For shorter typed requests, use `{"operation":"describe","view":"prepare"}`. Its public preparation
operation expands explicit criteria and question/options into a runnable request, disclosing defaults and
preserving origins. Run the returned request after inspecting its meaning. No Python builder is required;
unconfirmed readings remain proposed, and advanced canonical forms remain available.
Large preparations can stay in the reasoning store: MCP `reason` accepts `prepared:ARTIFACT_ID` in place
of `request`, and CLI uses `reason --prepared ID --store STORE`. The assistant inspects the defaults and
origins once and runs the retained expansion without copying its boilerplate back into conversation.

MCP can also read complete retained registry evidence through `record` part `source`, with `nct` and an
optional raw-study address. Digest-bound source handles attach the complete retained study without pasting
it into conversation; CLI uses the same mechanism with `--source-root ROOT`. The full study enters the
immutable reasoning artifact. Exact quotation establishes a copy's location, not its clinical meaning.

Use `{"operation":"describe","view":"design_bounds"}` for baseline witness bounds. It describes typed
observations, explicit eligibility bridges and candidate designs, with a runnable invented example. Candidate
eliminations feed a common-consequence query through the existing scoped solver. The operation does not read
tables automatically, reconstruct a complete protocol or change source-text frequency counts.

Use `{"operation":"describe","view":"signals"}` for the partial-evidence card and a
runnable invented request. Add `"detail":"full"` for the contracts and examples for every signal kind. `signals` evaluates those supplied inputs independently. To constrain a
design, include them in `design_bounds.signals`, select a derived observation with explicit predicate bindings,
or attach typed `signal_claims` to a candidate. Claims against one signal are checked together. Relations,
regimens and temporal graphs keep their own scopes; the operation does not invent joins between them.

Use `{"operation":"describe","view":"interpretations"}` for isolated hypothetical frames, population
and definition bindings, named queries and compatibility/refutation warrants. Fixed facts and rules are
checked separately from each frame's assumptions. Partial calculations remain inspectable when admission
is unresolved; selection never promotes a hypothesis to a source fact.

Use `{"operation":"describe","view":"source_assertions"}` for retained NIH study inputs, exact source
anchors and proposed readings. The bridge returns reusable reasoning requests and their complete results.
Empty queries inspect source admission without claiming a design check. Content digests identify snapshots;
they do not establish clinical protocol editions.

Use `{"operation":"describe","view":"evidence_requests"}` for bounded hypothetical profiles and
witness signs that distinguish declared surviving candidate rules. The guide separates enumeration limits,
returned-row limits and the complete response-byte limit. Unsupported numeric precision is refused rather
than changing comparison boundaries.

Use `{"operation":"describe","view":"design_session"}` for the closed version-1 session schema,
named premise projections, computed decisions and a runnable baseline example. Add `"detail":"full"`
for the complete schema and baseline/revision examples. Candidates and
other clinical inputs travel through its premise ledger, not arbitrary parameter substitution. Explicit
session budgets include child solver work; large evidence searches may need smaller declared bounds.
Copied-source JSON-node counts are diagnostic; the legacy `max_expanded_items` field no longer refuses
local replay. Aggregate solver work, analysis count and complete response-byte limits still apply.
The `source_study` projection supplies both `study` and `expected_digest`; omit both from child parameters.
Its historical target uses the exact `/result/source/study_ref` returned by source inspection; an NCT
number alone does not identify that snapshot. Its local source-ledger ID remains separate.
The pure operation returns reusable JSON. The CLI/MCP delivery layer can retain it explicitly, without
changing a source report or managing a background conversation:

```bash
trialledger reason --request SESSION_FILE --store REASONING_FOLDER --compact
trialledger reason-result --store REASONING_FOLDER --id ARTIFACT_ID --part decision_view
trialledger reason-revise --store REASONING_FOLDER --id ARTIFACT_ID --edits EDITS_FILE --revision revised
trialledger reason-export --store REASONING_FOLDER --id REVISED_ARTIFACT_ID --out REVIEW_FOLDER \
    --source-record REPORT_FOLDER/landscape.json
```

Compact reasoning replies default to 24,576 bytes; `--max-bytes` (MCP `max_bytes`) accepts 2,048–65,536.
Counts and continuation addresses identify details left in the complete retained artifact. Full replies stay
full. Export publishes into `REVIEW_FOLDER/review`; `REVIEW_FOLDER` must not already exist. Deliver the
returned paths rather than constructing a workbook path yourself.

The corresponding MCP calls use `reason` with `retain:true` or `response_view:"compact"`, followed by
`reason_result`, `reason_revise` and `reason_export`. The complete canonical request and response remain
retrievable by artifact ID and exact address. Follow all relevant page and text continuations. A revision
supplies explicit edits or a complete next session; the program fills integrity fingerprints and freshly
replays both snapshots. Changed clinical premises retain explicit attribution. Deliver the export's actual
returned file paths, including its workbook, readable list and manifest. Additional included analyses remain
separate unless the session explicitly relates them to a decision. The complete trial writer is a further
integration.

Entailment checks supplied scoped premises; coordinates uses the explicit NSCLC domain; corpus computes
statement rates with silence bounds, class associations, rarity, occupancy and one-feature comparisons.
Expectation-deviation classification remains a supporting Python utility. Derivational significance is
specified for future implementation; it is distinct from today's corpus rarity. The operations do not fetch
sources or alter reports. Full responses can be retained in the separate reasoning store or saved as explicit
request/result files for reuse.

</details>

MIT; see [LICENSE](LICENSE).
