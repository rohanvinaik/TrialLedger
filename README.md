# TrialLedger

[![tests](https://img.shields.io/github/actions/workflow/status/rohanvinaik/TrialLedger/tests.yml?branch=main&label=tests&logo=github)](https://github.com/rohanvinaik/TrialLedger/actions/workflows/tests.yml)
[![test suite](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Ftests.json)](QUALITY.md)
[![coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Fcoverage.json)](QUALITY.md)
[![branch coverage](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Fbranches.json)](QUALITY.md)
[![mutation score](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Fmutation.json)](QUALITY.md)
[![runtime dependencies](https://img.shields.io/endpoint?url=https%3A%2F%2Frohanvinaik.github.io%2FTrialLedger%2Fbadges%2Fdependencies.json)](pyproject.toml)
[![python](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**TrialLedger doesn't make your clinical decisions. It finds them.**

Much of designing a trial is documentary and logical work: finding what comparable trials did, copying it out
accurately, and working out what a draft restriction does and doesn't allow. TrialLedger, run by your AI
assistant, does that work. It hands you the choices that genuinely need clinical judgment, each with its
evidence and its consequences worked out.

For a draft lung cancer trial compared with IPASS and ARCHER 1050, one decision looks like this:

- **Evidence:** ARCHER 1050 requires ECOG performance status 0–1. IPASS's registered eligibility gives no
  cutoff; its baseline nevertheless reports 126 of 1,217 participants at WHO PS 2. WHO PS and ECOG are kept
  as separate scales.
- **Your decision:** What performance-status range do you intend?
- **Consequence:** Widening your draft from ECOG 0–1 to 0–2 moves ECOG 2 patients from excluded to allowed.
- **Still open:** Your draft says nothing about brain metastases. ARCHER 1050 excludes any history of them.

You talk to your assistant in ordinary clinical language. Behind the conversation, every answer is either
copied from the registry, calculated by TrialLedger from statements you have confirmed, or plainly marked as
a reading or as your choice. This page explains how that works, what you can ask, and how far to trust each
kind of answer.

## How it thinks

Many AI tools fill the gaps in a clinical record with what is probably true. TrialLedger does the opposite.
It works out exactly what the evidence settles, keeps everything else open, and brings the open parts to you
as questions. Five ideas explain nearly everything it does.

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
example: IPASS reports 1,217 baseline participants, 126 at WHO PS 2 and 1,140 who never smoked. Neither
count says how many patients are both. **If** both counts describe the same 1,217 patients, at least 49 must
be both (126 + 1,140 is 49 more than 1,217) and at most 126 can be. Nothing is assumed about whether the two
traits are related. What becomes certain is what has been ruled out: fewer than 49 is impossible. The exact
number stays open.

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

This is also why the reasoning can be exact. It works with reported counts and stated criteria, not with
estimates about biology: 126 of 1,217 is what IPASS reported, so a bound on that count is arithmetic.

## How the work divides

| Stage | What happens | Who does it | Why it can be trusted |
|---|---|---|---|
| **Gathering** (bookkeeping) | Registry records are retrieved, preserved and laid out in a reference workbook. The registry's own published rules are applied, such as date-order checks. | TrialLedger, operated by your assistant | Values are faithful copies, and checks follow published registry rules. The workbook can be rebuilt from the saved records. Nothing is interpreted. |
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
- **The decision list.** For each consequential choice: the decision in clinical words, the evidence from the
  compared trials (including where the registry is silent), the computed consequence of each option, and its
  status, open or chosen by you. Your assistant can keep it in a `working-brief.md` file beside the saved
  checks, so the design can be revised and rechecked later.

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

Your assistant does not do the reasoning. It translates between your words and TrialLedger's premises.
Registry values are used as recorded; every reading, sameness claim and choice is restated to you in clinical
words, taken from the check actually being run, before anything relies on it. TrialLedger does the
calculation, the same way every time. The question of trust therefore shifts from "do I trust the AI?" to "are
these statements about my trial right?", which you are qualified to answer. When you change a premise, the
checks are rerun; an old answer is never relabelled as if it had checked the new one.

Two limits matter. First, TrialLedger supplies logic, not medical knowledge. It knows only what the registry
records and what you have confirmed: nothing about pharmacology, biology or today's standard of care. Second,
translation can go wrong. A misread criterion yields an exact answer to the wrong question, which is why you
always see the premises restated. Each check is also saved as a file that a technical colleague can audit, and
at any point you can ask which premise decided an answer.

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
- **Overlap of two baseline counts:** if the WHO PS 2 count, the never-smoker count and the total describe
  the same patients, a reading for you to confirm, their overlap is **49–126**. This does not recover an
  eligibility cutoff, and WHO PS stays WHO PS.
- **Two analysis populations:** 607 safety-evaluable and 590 QoL-evaluable patients among 609 on gefitinib
  give **588–590** in both, if both tables describe the same cohort. The
  [workflow investigation](docs/SOURCE_INFORMATION_RESOLUTION.md) and its
  [saved checks](examples/source-workflows/) cover this and other analysis-population questions.
- **A schedule with two readings:** "every 42 ±7 days from randomization" gives a first window of days 35–49
  under either reading. The second window is days 77–91 if every tolerance is measured from randomization, or
  70–98 if each interval restarts at the previous visit. That choice is about how your schedule should work.

Each item keeps its source location and stays labelled as a reading until you confirm it. The registry
record itself is never changed.

## What isn't built yet

- **Automatic reading of eligibility prose.** Today you and your assistant settle readings together;
  TrialLedger compiles only the structured minimum and maximum age directly.
- **Complete protocol writing from a brief.** It is designed and partly built; the operations above are its
  working core.
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

Use absolute paths. Tools are doctor, scope, landscape, save_fetch, record and reason. The assistant handles
record paging: at most 50 entries and a default 24,576-byte record reply. Oversized nested values return exact
addresses to follow; long strings have lossless text continuation. Saved records are complete. These are
conversation-output limits, not a limit on the whole process's memory or a change to requested study scope.

Reasoning uses `trialledger reason --request FILE` or MCP `reason(request)`. Start with
`{"operation":"describe"}` for an overview. Ask for `{"operation":"describe","view":"entailment"}`,
`coordinates` or `corpus` for the relevant formats, guide and runnable example. Views `worked_session` and
`full` retain the demonstration and complete manual on demand.

Use `{"operation":"describe","view":"design_bounds"}` for baseline witness bounds. It describes typed
observations, explicit eligibility bridges and candidate designs, with a runnable invented example. Candidate
eliminations feed a common-consequence query through the existing scoped solver. The operation does not read
tables automatically, reconstruct a complete protocol or change source-text frequency counts.

Use `{"operation":"describe","view":"signals"}` for the eight partial-evidence contracts and a
runnable invented request per kind. `signals` evaluates those supplied inputs independently. To constrain a
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

Entailment checks supplied scoped premises; coordinates uses the explicit NSCLC domain; corpus computes
statement rates with silence bounds, class associations, rarity, occupancy and one-feature comparisons.
Expectation-deviation classification remains a supporting Python utility. Derivational significance is
specified for future implementation; it is distinct from today's corpus rarity. The operations do not fetch
sources or alter reports. The assistant can save a full response separately as `reason-result.json` for reuse.

</details>

MIT; see [LICENSE](LICENSE).
