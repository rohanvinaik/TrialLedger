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
accurately, and working out what a draft restriction does and doesn't allow. TrialLedger, run by your
assistant, does that work and hands you the choices that genuinely need your clinical judgment, each with its
evidence and its consequences worked out.

For a draft lung cancer trial compared with IPASS and ARCHER 1050, one decision looks like this:

- **Evidence:** ARCHER 1050 requires ECOG performance status 0–1. IPASS's eligibility text gives no cutoff; its
  baseline nevertheless reports 126/1,217 participants at WHO PS 2. These scales retain their own identities.
- **Your decision:** What performance-status range do you intend?
- **Consequence:** Widening your draft from ECOG 0–1 to 0–2 moves ECOG 2 patients from excluded to allowed.
- **Still open:** Your draft says nothing about brain metastases. ARCHER 1050 excludes any history of them.

Your attention goes to the decisions, with the evidence assembled and the consequences computed rather than
guessed. The evidence comes from the studies you care about: TrialLedger gathers their ClinicalTrials.gov
records into a readable reference workbook and a matching evidence record, so you can examine who could
enroll, what was measured, when it was assessed, and what results and safety information were reported.

Then ask: “What have these studies done here—and what would happen if we chose something different?”

Your assistant brings the relevant evidence into the conversation, helps make your intended choices
explicit, and runs TrialLedger's comparison and reasoning tools. You can examine documented patterns, check
whether your draft restrictions conflict, explore alternatives, and revise a choice with its consequences
in view.

You make the clinical judgments. TrialLedger's job is to make them visible: what is already settled by your
choices, what contradicts itself, what is genuinely yours to decide, and what the evidence cannot tell you. The reference workbook is useful on its own,
and it provides the evidence base for a continuing design conversation.

## Information is also in the constraints

A trial record carries information beyond its explicit sentences. Eligibility, baseline distributions,
participant flow, assigned treatments and endpoint definitions describe related parts of the same study.
Once their populations, scopes and meanings are bound, their constraints can be combined. Designs compatible
with one field can become impossible when another field is considered. The remaining alternatives show both
what follows and which choices still need judgment.

That is TrialLedger's information-theoretic thesis: **make the information already carried by the evidence
available as constraints on an explicit space of possibilities.** A missing statement can leave a question
partly identified. For example, among the same 1,217 IPASS participants, 126 at WHO PS 2 and 1,140 never smokers
require at least `126 + 1,140 − 1,217 = 49` participants with both attributes, and at most 126. This bound needs
no assumption that the attributes are independent. It exposes a consequence of the reported counts without
inventing a cross-tabulation or an exact count.

Each inference needs a **formal warrant**: typed premises, the rule connecting them, its applicability
conditions and an inspectable conclusion. The overlap bound requires a shared participant universe. Using
that overlap to constrain eligibility additionally requires a bridge from observed participants to eligible
participants, with an explicit allowance for exceptions. If fewer than 49 could be exceptions, at least one
eligible joint-profile witness remains; a design excluding that entire profile is incompatible with those
premises. The exact performance-status cutoff still does not follow.

The conclusion keeps the standing of its weakest premise. Strict deductions from known premises are known;
an eligibility bridge adopted as an interpolation makes its consequences interpolated, even when the
arithmetic and logic are exact. An unconfirmed proposal can be assumed within its explicitly hypothetical
frame; it cannot constrain an accepted design outside that frame. Every result keeps its
source or accepted premise, population, scale, units, time, rule and blockers. Conflicts and unresolved
bindings remain visible, and changed premises require recomputation. This is what makes the reasoning
reviewable for clinical work: the person can inspect what supports an answer and precisely what would change it.

**An uncertain interpretation can still be useful.** Layer one supplies the fixed source facts and direct
rules that bound the represented possibilities. Layer two can keep competing readings, explore what follows
if each holds, and show a formal warrant wherever a reading violates those fixed constraints. The uncertainty
of a reading and the exactness of its conditional consequences are separate. Your assistant can discuss
those possibilities with you without turning a plausible reading into a registry fact or forcing a choice
before its consequences can be examined.

For example, reading “every 42 ±7 days from randomization” as the first scheduled assessment window yields
35–49 days exactly within that interpretation. Whether that is the intended reading remains a separate
question. An actual unscheduled scan outside the window is a different event. The system keeps these roles
and alternative readings separate, so evidence can break a working interpretation and leave useful partial
information available for the next question.

The worked session below demonstrates this composition across counts, sets, time, ingredients, class
relations and adopted definitions. Each contributes its own constraint; together they eliminate incompatible
designs and expose the decisions left open. Corpus frequency and rarity are separate measurements, and
derivational significance remains a planned component; this example does not assign a probability to the
surviving designs.

## Questions that reveal the method

The system can answer questions that initially seem to require missing data or clinical guesswork:

| A person's question | What the reasoning can recover | What stays open |
|---|---|---|
| “Neither table gives the joint population. Can we still bound it?” | IPASS counts of 607 safety-evaluable and 590 QoL-evaluable among the same 609 gefitinib participants bound their overlap at **588–590**, under explicit cohort correspondence | Exact identities and the reason for missing coverage |
| “PS 2 people were both randomized and rejected. Is that a contradiction?” | In the invented session, positive and attributed negative witnesses eliminate different eligibility explanations without turning rejection into a universal exclusion | Which additional criterion explains the rejection |
| “Does an early scan invalidate the schedule?” | A scheduled day-28 visit conflicts with a stipulated days-35–49 routine window; a separate actual unscheduled scan can coexist with it | Which event and reading the person intends |

Each is a small demonstration of the same thesis: related evidence can constrain more than any one field
states, while the remaining uncertainty still belongs in the conversation. The
[worked questions](docs/POWERFUL_QUESTIONS.md) link the complete executed inputs and results, distinguish
real retained evidence from invented teaching cases, and show the consequential question to ask next.

## A design session in practice

> “The comparator's eligibility entry is thin. Can we work out what it actually constrains before we
> choose our population, treatment sequence and assessments?”

Here is an executable teaching case. Every study datum, drug identity and definition in this session is
**invented**. Its [inputs and saved results](examples/partial-evidence/) run through the same reasoning
operations your assistant uses with retained registry evidence.

**1. Assemble the evidence and settle its meaning.** The comparator reports 200 randomized participants:
40 at ECOG 2 and 180 never smokers. Its two mutually exclusive, exhaustive cohorts include 140 in cohort A,
with cohort B's count omitted. The exact midpoint median age is 65. An explicitly bound analysis population
contains 160 of the 200 randomized participants. A screening log records an eligibility-attributed rejection
of one person at ECOG 2, without their other attributes.

Other structured evidence places induction's end before randomization and the first dose within seven days
afterward; an assigned arm contains a combination product with ingredients A and B. A versioned definition
places marker A within family F, and F within the qualifying-marker class. An adopted change-score definition
requires observed baseline and week-12 measurements; the evidence supplies baseline and leaves week 12 unknown.

Your assistant retains each source address, population, assessment time and definition. You settle which
baseline counts describe the same participants, whether the summaries are exact, and how many participants
might be exceptions to an eligibility interpretation. In this example, the eligibility bridges allow zero
exceptions and remain interpolated premises.

**2. Test competing explanations together.** TrialLedger checks twelve declared candidate designs against
those premises. Different pieces of partial evidence do different work:

| Evidence | Computed constraint | Candidate it rules out |
|---|---|---|
| 40 ECOG 2 and 180 never smokers among the same 200 people | **20–40** have both attributes | Excludes every person with that joint profile |
| Cohort A has 140; A and B partition 200 | Cohort B has **60** | Admits cohort A only |
| Exact midpoint median age 65 among 200 assessed people | **At least 100** are 65 or older | Requires everyone to be under 65 |
| Analysis population is an explicit 160-person subset of 200 | **40** randomized people are outside that analysis | Assumes everyone randomized was analysed |
| Induction ends before randomization | Reversing that order contradicts the bound timeline | Randomizes before induction ends |
| Assigned product contains A and B | Its ingredient set includes both | Represents the arm as ingredient A alone |
| Marker A → family F → qualifying-marker class | Marker A is in the qualifying class under that edition | Places marker A outside that class |
| Adopted change score requires two observed measurements | Explicitly unavailable week-12 observation conflicts with that definition | Uses that definition with no possible week-12 observation |
| An ECOG 2 profile was rejected for eligibility | Performance status alone cannot explain that rejection | Defines eligibility solely as ECOG ≤2 |

These results preserve their limits. Forty people outside an analysis are not thereby forty dropouts or
ineligible participants. An unknown week-12 measurement stays unknown; the compatible candidates explicitly
hypothesize its availability, which does not turn it into posted data. An imputed value does not satisfy this
observed-only definition. The rejected partial profile does not establish that every ECOG 2 person is excluded.

**3. See what remains genuinely open.** Nine candidates are ruled out. Three remain: an adult population
requiring a qualifying marker with ECOG 0–2; the same with ECOG 0–3; and an adult ECOG 0–2 population without
that marker requirement. Each assumes the observed measurements needed by the adopted endpoint definition.
The common-consequence question “Must ECOG be ≤2?” returns **undetermined**. The exact cutoff and marker
requirement remain open; these declared candidates do not exhaust every possible real protocol.

The assistant carries those open choices into the decision list, keeping them separate from what the
source constraints have settled.

**4. Make a choice and check its consequence.** You choose adults with ECOG 0–2 for your draft. A separate
[brief check](examples/partial-evidence/draft-request.json) returns **refuted** for ECOG 3, naming your
performance-status premise. Widen that premise to 0–3 and rerun: the range allows ECOG 3 without requiring it.
That checks the encoded restriction; other eligibility requirements remain separate.

**5. Revise the evidence, too.** If the screening rejection cannot be attributed to eligibility, its bridge
becomes unresolved and the performance-status-only candidate is retained as unresolved. If the joint
baseline bridge permits 20 exceptions, its lower bound no longer guarantees an eligible joint-profile witness;
19 exceptions still leave one. The assistant reruns the checks and updates the decision list, keeping the
original evidence intact.

At handoff, the updated **decision list** makes the human choices and computed consequences visible:

| Decision | Evidence and computed consequence | Status |
|---|---|---|
| Performance-status range | Comparator witnesses include ECOG 2; your selected 0–2 restriction excludes ECOG 3. Widening it to 0–3 allows 3. | **Chosen by you: 0–2**, with the checked brief retained |
| Marker selection | The class relation is resolved; surviving designs differ on requiring the marker, and the partial rejection does not settle it. | **Open:** should the new population require it? |
| Endpoint assessments | The adopted definition needs observed baseline and week-12 inputs. Week 12 remains unknown; imputation alone does not satisfy that definition. | **Open:** settle the assessment plan or explicitly change the definition |

The assistant retains the workbook, decision list and request/result pairs separately. Revising a choice
updates the checks and list, while the source record remains intact.

The real IPASS example follows the same discipline: its 126 WHO PS 2 participants and 1,140 never smokers among
1,217 baseline participants bound their overlap to **49–126** only under a confirmed common-universe binding.
The eligibility interpretation needs its own bridge; WHO PS retains its own scale, and an observed category
does not recover an exact eligibility cutoff.

For source-based questions about analysis populations, assessment windows and conservative data cleanup,
see the [workflow investigation](docs/SOURCE_INFORMATION_RESOLUTION.md) and its
[executed request/result pairs](examples/source-workflows/). They distinguish today's conditional
computations from the source-binding and correction integrations proposed next.

Today, your assistant reads and structures evidence with you; TrialLedger computes these bounds,
compatibility checks and consequences. Automatic conversion of clinical text into reasoning inputs and
complete protocol writing remain unintegrated. See the [full design](openspec/changes/add-design-synthesis/design.md)
and [theory](docs/THEORY_OF_THE_CASE.md) for the component map.

## Explore competing readings without losing the evidence

“Could this wording mean either option, and what would each option permit?” is a supported question.
The separate `interpretations` operation checks an explicit fixed floor and keeps each proposed reading
in its own frame. It returns fixed-evidence answers, consequences under each reading, compatibility or
refutation warrants, unresolved applications and the choices left open. Proposed assumptions remain visible;
ordinary entailment still refuses to use them as accepted premises.

The [executable continuing session](examples/interpretations/) starts with an invented adult NSCLC draft.
ECOG 0–2 and 0–3 both fit its fixed choices but answer the ECOG 3 question differently. A scheduled assessment
outside a stipulated window is refuted, while a separately represented unscheduled scan can coexist with
that schedule. Population bindings and adopted endpoint editions affect their actual checks; unresolved
bindings retain conditional counts, and an imputed input does not become an observed measurement.

Your assistant can discuss these alternatives before asking you to settle a reading. Selecting one remains
your choice, with its assumptions intact. Even a single compatible survivor leaves conclusions conditional
on the declared family; the system does not claim it has recovered the whole protocol. Changed evidence or choices call for
a fresh check, and fixed contradictions remain visible even when you prefer a particular option.

## What you receive

**`landscape.xlsx`** is the clinical reference workbook. Start with Trial index and Trial review, then explore
eligibility, interventions, planned outcomes, posted results, statistical analyses, baseline, participant
flow, groups and safety. Numbers keep their study groups, denominators, units and reporting periods.
Observational and expanded-access studies retain their own applicable details.

**`landscape.json`** contains the matching selected clinical evidence your assistant uses for questions.
Complete registry responses are also retained. The workbook and record preserve source wording, with links
back to the evidence behind an answer. Planned outcomes remain separate from posted results, and missing
information stays visible. A source link gives you a place to investigate further when an answer needs
information beyond the registry.

You can also stop at the reference sheet. For example:

- “Give me the reference sheets for IPASS and ARCHER 1050.”
- “Find completed Phase 3 EGFR inhibitor studies in non-small cell lung cancer.”
- “Show me who could enroll, the outcome time points and the reported safety by treatment group.”

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

Entailment checks supplied scoped premises; coordinates uses the explicit NSCLC domain; corpus computes
statement rates with silence bounds, class associations, rarity, occupancy and one-feature comparisons.
Expectation-deviation classification remains a supporting Python utility. Derivational significance is
specified for future implementation; it is distinct from today's corpus rarity. The operations do not fetch
sources or alter reports. The assistant can save a full response separately as `reason-result.json` for reuse.

</details>

MIT; see [LICENSE](LICENSE).
