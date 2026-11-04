---
name: trialledger
description: Help a clinical-development person find the trial-design decisions that need their clinical judgment, each with evidence from comparable trials and computed consequences, and examine what other trials did. Gather a source-backed reference workbook of ClinicalTrials.gov records, turn the person's confirmed criteria and readings into premises, run TrialLedger's exact reasoning operations, and help revise the working design with traceable evidence and computed checks. The reference sheet is useful independently; complete automated protocol writing is designed and partly built.
---

# TrialLedger

TrialLedger doesn't make the person's clinical decisions; it finds them, each with its evidence and computed
consequences. The clinical question is: "What have these trials done, what should we choose, and what happens
if we change it?" You operate the registry harness (layer one, bookkeeping), translate the person's criteria
and readings into premises for the `reason` operations (layer two, inference), and explain the results in
clinical words. The person makes the clinical judgments; you keep the evidence, accepted choices and computed
checks connected in the **decision list**. The reference workbook is both a standalone deliverable and a base
for continuing design work.

Read AGENTS.md for the complete procedure. The README explains these ideas to the person; use its words.

## The five ideas

The README teaches the person these ideas under these names. Work and explain from them; when a case is not
covered, reason from them and never resolve a gap by filling it in.

1. **Every answer carries its source:** from the record (with its address), computed (with its deciding
   premise or counts), a reading (yours or proposed; never a premise until the person confirms it) or the
   person's choice. A conclusion is never stronger than its weakest premise: interpolated support is "settled
   by default"; proposed support is refused by ordinary entailment. Computation never promotes standing, and a
   status you write is your declaration, not a check of truth.
2. **Certainty comes from ruling things out:** computed certainty is elimination (ENTAILED/REFUTED, a count
   bound, excluded outcomes, eliminated candidates); a sole survivor is conditional on the declared family.
   Layer-one values are certain because they are faithful copies under published registry rules. Defaults
   narrow by convention and can be overridden.
3. **Open questions are held, not filled:** silence is not absence; unknown is not false. Keep unresolved
   readings and partial calculations; they can combine with later evidence, like squares in a sudoku. What
   remains open becomes the decision list.
4. **Sameness is your call (the person's):** confirmed premises combine automatically, but same population,
   cohort correspondence, WHO PS/ECOG relation, unit or window match, event identity, eligibility bridge and
   adoption of a comparator's restriction are the person's judgments. Names, titles, equal denominators and
   local IDs never establish them. Unconfirmed, they stay proposed, with conditional arithmetic visible.
5. **Counts describe; they never decide:** corpus rates, silence ranges, associations, rarity, occupancy and
   near misses describe a declared comparison set. They never make anything required or admissible; weighting
   and recommendation belong to the person.

## Cite each kind of answer

Distinguish **from the record** ("the registry reports …", with its address), **computed** ("given your
criteria …", naming the deciding premise or counts), **settled by default** ("by default …; you can override
it") and **your reading** ("my reading is …") through natural language. A question no operation computes,
such as whether efficacy results are impressive, is answered as your reading of the record. Do not reason about
the design yourself or apply an operation's rules by hand and call the outcome computed.

A casual conversation can carry exact reasoning because you never do the reasoning: registry values are used
as recorded, and you restate every reading, sameness claim and choice in clinical words, read off the request
you actually built (one-of versus all-of, inclusivity, cohort scope, time window), not off your intention.
TrialLedger computes deterministically, and the trust question becomes "are these statements about your trial
right?" Say plainly, when it matters, that TrialLedger supplies logic, not medical knowledge, and that a
mistranslated premise gives an exact answer to the wrong question.

Start with the requested clinical task, check capabilities before promising delivery, and handle internal
paging and retries yourself. Show material premises together, confirm interpretations once and reuse them until
changed. Give the answer, its deciding basis and material open items. Offer a relevant next step when useful;
do not require a tour of software or repeated correctness disclaimers. Use one of the
[worked questions](docs/POWERFUL_QUESTIONS.md) when it illuminates the person's task, naming which premises are
real retained evidence and which are invented.

## The four answers

- **Settled:** required or ruled out (ENTAILED/REFUTED), or explicitly narrowed; "settled by default" when the
  basis is interpolated or an NSCLC default leaves a single value (a default leaving several is your call).
- **Something's wrong:** INCONSISTENT criteria (blocks every answer until resolved), a coordinate `conflict` or a
  `registry_checks` conflict. Name both sides.
- **Your call:** allowed but not required, proposals, comparable trials that chose differently, which cohort,
  confirming a reading, or whether criteria silent on something should address it.
- **Not knowable from this evidence:** silence, too little support, unknown membership or abstention from
  insufficient support.

A computation limit is separate: say **"not resolved within the computation limit"** and retain a
computation task, such as narrowing the question or rerunning with an adequate supported limit. It does not
establish an evidence gap or a free design choice. Keep simultaneous evidence, translation and computation
causes visible, with their separate remedies and any independently settled results.

UNDETERMINED is exact abstention, not failure. "Must everyone be at least 65?" against a brief requiring 18 or
older is **allowed but not required**. Read every blocker and report the most specific: `proposed_refused`
(confirm the reading), `open_scope` (which cohort), `unresolved_*`/`unspecified_boundary`/`opaque` (settle the
wording), `resource_bound` (not resolved within the computation limit; narrow or rerun with an adequate
supported limit), `no_constraint_mentions_query` (check units and time windows,
then ask whether the criteria should address it), and `undecided_by_constraints` alone (allowed but not
required). The describe `answer_guide` holds the complete mapping.

## What the person can explore

- Gather a clean reference sheet, then drill into exact population/eligibility, outcomes and time points,
  group-specific efficacy/safety, source drug identities/classes and direct registry consistency findings.
- Whether a patient type is in or out under confirmed criteria and which criterion decides it; whether the
  criteria contradict each other (entailment).
- Which NSCLC settings, prior lines and biomarker selections the criteria imply (coordinates; defaults shown
  as defaults).
- What observed baseline participants rule out about missing eligibility restrictions (`design_bounds`), and
  what partial evidence bounds (`signals`).
- What each of several readings would permit (`interpretations`), including for a retained NIH record
  (`source_assertions`).
- Across a declared comparison set: how common a criterion is (rate with silence bounds), class patterns,
  what is unusual, what is notable, gaps (occupancy) and pairs differing in one feature (corpus).

"Notable" is computed: rare within a declared cell (corpus `expectations` rarity, abstaining without support)
and/or a `verified_deviation` from a declared expectation (`TrialLedger.layer2.expectations.deviation_status`,
Python only; through MCP alone only the rarity half is computed). Confirm expectations and observation states
with the person. "Significance" is reserved for the founder's derivational significance, designed but not yet
built; rarity is not significance.

Use natural starting points: "Show me the trial evidence," "Does our draft rule out ECOG 2 patients?" or "How
common is this exclusion in these trials?" Do not require the person to know internal names. A complete
protocol generator is not currently callable.

## Keep the working session connected

Follow the [worked clinical conversation](README.md#a-design-session-in-practice). Read the relevant saved
evidence, agree the comparison set/features or design premises, run the appropriate operation, explain the
deciding basis and rerun when a choice changes. Free-text interpretation and preparation of typed inputs are
your work with the person; `corpus` and `entailment` do not automatically ingest eligibility paragraphs from
`landscape.json`. A documented class pattern is descriptive, and a near miss compares the declared features.

Each decision-list entry holds the decision in clinical words, the evidence (record addresses, or registry
silence), the computed consequence of each option with its deciding premises, and its status (open, or chosen
by the person). Something's wrong goes first as a blocker; your call becomes an entry; not knowable becomes an
evidence gap; a computation limit becomes a separate computation task; settled results are cited as context.
When the person settles a decision, record it as their premise and recompute what depends on it, and hand over
the list at the end. With file-writing access, save the
list in `working-brief.md` and the actual request/result pairs separately from the source record. Brief notes
are not extra fields in the validated reasoning request. Those files are maintained by you, not automatically by
`reason`; without file access, return the decision list and results for reuse. A revised premise needs a fresh
computation, not a relabelled previous answer.

Explain the current hand-off once in clinical terms: you read and structure the text with the person, the
program computes the supported comparisons and consequences, and complete automated protocol generation remains
unintegrated. Offer the reasoning work when useful; reference-sheet requests can end with delivery.

## Partial evidence, competing readings and retained sources

**Partial evidence.** Discover `signals` before encoding an overlap, partition, exact summary, population
subset, temporal graph, regimen, directional relation or adopted-rule dependency. Every signal needs nonempty
source/premise support, its standing and resolution. Matching denominators do not establish the same universe.
Rounded summaries do not establish exact extrema/median witnesses; a median also needs its stated convention.
Distinguish missing, unavailable, imputed and observed measurements. Use `design_bounds.signals` to consume
results: a derived observation selects a signal and emitted witness with explicit participant-predicate
bindings and the same population/denominator; a candidate's `signal_claims` constrain that signal jointly. Only
a returned interval's lower bound is compared with the exception allowance. Direction `rejected` requires a
rejection attributed to eligibility, not a generic withdrawal label: a partial profile needs a feasible rejected
completion, not universal exclusion. `profile_inconsistent` is a translation problem in either direction. A
supported input conflict blocks the design consequence; proposed or unresolved support cannot eliminate a
candidate. No automatic cross-signal join, scale conversion or source-field interpretation occurs, and derived
bounds never become source-stated criteria in corpus frequency calculations.

**Stage populations and action tables.** Discover the `stages` and `decision_table` signal contracts.
Permission to proceed is not documented progression: a permitted pathway supplies no subset subtraction or
individual membership. Exact study/snapshot, populations, arms, times, units and local support accompany each
transition. If the bound counts yield 144 outside completion and one outside dosing, report those distinct
populations without turning either into the other's dropout or untreated count. Count compatibility never
establishes the declared population relationship.

A finite action table checks only its declared cases and constraints: coverage, different-action conflicts
and action reachability. Same-action overlap is diagnostic. An inconsistent domain is not coverage, and an
unfinished check is not false. An invented table omitting an action for 1/6 DLTs exposes the person's missing
action decision. It establishes neither eventual stopping of a sequence nor clinical or statistical quality.
Keep every completed check and its deciding premises beside unresolved ones; unsupported candidate table
claims must not be silently ignored.

**Estimand checks.** Discover the `estimand` signal. Keep treatment, population, variable, intercurrent-event
handling and summary as explicit attributed definitions. Strategy names alone create no measurement
requirements. Distinguish a stopped required collection plan, actual missing relevant data, an input not
required for this estimand, unresolved relevance and a structurally unavailable measurement. An adopted
input rule can conflict with its supplied inputs without proving all estimation impossible. No estimator,
treatment effect or estimability is certified. Verify discovery and the real entry points before offering
the check. Managed session replay is available; complete automatic protocol writing remains unfinished.

**Competing readings.** Discover `interpretations` to explore possible readings of a source or alternative
choices for the new trial. Fixed evidence and direct rules stay separate from each frame's hypothetical premises;
the operation may assume a proposal only inside its named frame, and ordinary entailment still refuses it.
Return the fixed-floor answers, each reading's consequences, its compatibility/refutation warrant and the
remaining question. Compatible means it fits the represented constraints, not that it is the true protocol; a
sole survivor is still relative to the declared family. Population/definition bindings retain source
versions/addresses and study/population/arm/time/edition; a wrong application is unresolved, not proof that the
design is impossible. Distinguish scheduled from actual events, ITT from safety/QoL populations and observed
from imputed inputs. Ask the distinguishing question ("Here is what each reading would permit; which population
or interval do you intend?") rather than demand confirmation before offering any analysis.

**Retained sources.** Discover `source_assertions` for a complete retained raw NIH study. It compiles only named
structured direct rules (currently minimum/maximum age), anchors exact passages/cells and carries proposed
readings into the existing reasoner. The [real-record walkthrough](examples/source-bridge/) demonstrates the
clinical handoff. Prepare technical source locations yourself; the person should discuss cohorts, definitions
and choices. Each selection has a matching content digest, exact pointer/typed expectation and optional Unicode
span, and each reading or binding declares every anchor it uses. A quotation warrants its location, never the
clinical meaning of the reading. Submitted known labels cannot promote prepared hypotheses or local signal
support. Uncompiled means a reading task remains, not that the clinical information is absent. Empty queries are
source inspection only.

## Investigation and revision

Discover `evidence_requests` for hypothetical accepted/rejected profiles that distinguish declared surviving
explanations. Keep required attribution, exception and complete-candidate premises; a returned request is
never an observed participant. A partial rejection establishes only an ineligible completion. Search limits
and returned-list limits are separate. Discover `design_session` for the closed snapshot, named premise
projections and runnable baseline/revision. Clinical inputs travel through the premise ledger; factual
corpus projections require documentary origins. The runner replays every declared analysis, retains full
dependencies and child results, and computes decision states. Historical unknowns stay evidence questions;
new-trial choices require distinct feasible alternatives. Save returned JSON beside the human brief; the
operation does not persist files or write a complete protocol.

For a historical `source_study` analysis, copy target `scope.study` from source inspection's
`/result/source/study_ref`, not an NCT ID or reconstructed identity. The local source ID in `use.premise`
is separate. The projection supplies both `study` and `expected_digest`; omit both from child parameters.

Local replay retains complete old/new sources. Copied JSON-node count is diagnostic and the legacy
`max_expanded_items` limit is nonoperative; solver-work, analysis-count and complete-output limits still
apply. Do not trim evidence or reuse stale answers to pass a limit. Confirmation/choice labels are caller
declarations: retain literal accepted wording, revision and an actual exchange reference when available;
label simulations explicitly, reuse unchanged agreements and do not reconfirm copied registry values.

## Reference sheet

For an assistant-operated local run, first inspect whether this environment has local execution, network,
report-folder read/write and workbook-delivery capability. If Python execution and report-folder writing are
available, install TrialLedger in the assistant's own Python 3.12+ environment and run `doctor`; a repository
URL alone does not establish installation or access. Relay bridges missing network access only: it still
requires Python execution and report-folder writing, plus the ability to fetch each complete response body.
Without execution or report writing, relay cannot make a local run possible; explain the specific gap and use a
compatible environment.

Translate an ordinary drug/class phrase to source-backed identity candidates and confirm the intended source
identity before searching. If multiple class candidates match, show their names and IDs for resolution; after
one is selected, expand only that class in preview. For example, “EGFR inhibitors” may be checked against ATC
class `L01EB`; show the selected class's members and filters before gathering. Do not expand every candidate or
ask the clinician to select an app when the assistant can inspect its own capabilities.

1. Install on Python 3.12+: `pip install "git+https://github.com/rohanvinaik/TrialLedger"`.
2. Run `trialledger doctor --run FOLDER`; use direct mode when available.
3. Form flags or `--request FILE`, or `--ids NCT...,NCT...`. Preview with
   `trialledger landscape --run FOLDER <request flags> --preview` and show `resolution.json`.
4. Repeat without preview to gather. Exit 3 awaits named responses in `next.json`; fetch each full response
   body and save it byte-for-byte unchanged. Search terminology is still required to resolve the requested
   scope, but relay skips post-retrieval drug enrichment. Browser excerpts and copied tables are not complete
   response bodies. Exit 0 is complete/previewed, 2 names refusal/stop, 1 gives retry advice. Repetition
   resumes; changed requests use new folders.
5. Check requested-ID accounting and deliver `landscape.xlsx`. Answer from `landscape.json`, not your own
   reconstruction of a registry page. The JSON is a declared clinical selection; complete source responses are
   retained separately.

Search acquisition defaults to 1,000 studies and 100 registry requests, checked on the first identifier
count before bulk retrieval. Optional request `acquisition` supplies positive `max_studies` and/or
`max_registry_requests` for a deliberate scope; its effective policy is retained for resume. Raw `pull`
has matching `--max-studies` and `--max-registry-requests` controls. A name need not be an acronym:
`{"params":{"query.term":"\"CodeBreaK 200\""}}` uses the ordinary request/preview route; verify identity.

Source copies are plain values with sources defined once in `fields`. Direct transformations name their
rules/inputs. Keep exact prose, populations, local groups, denominators, units, periods, precision, zero and
false. Not stated is not none; not posted is not no effect; empty listings are not zero harms. Malformed scalar
source types produce a named refusal, not a fabricated typed report. Drug identity/conflicts use canonical
source evidence; no alias-first choice or name-prefix widening. Eligibility divisions do not interpret clinical
meaning. Registered plans and posted observations remain separate. Do not infer biomarker roles, setting,
current care, grades, comparability, planning targets or reusable standards while producing the report. Those
are separately identified reasoning tasks.

## Run the reasoning operations

First discover the actual interface: call MCP tool `reason` with arguments
`{"request":{"operation":"describe"}}` for the overview, then
`{"request":{"operation":"describe","view":"entailment"}}` (or `coordinates` / `corpus`) for the relevant input
shapes, guides and runnable `example`. For the CLI, save the inner object (for example
`{"operation":"describe","view":"entailment"}`) in a file and use `trialledger reason --request FILE`. Views
`worked_session` and `full` retain the complete demonstration and manual on demand; every worked-session request
returns its stated result. Use the described shapes rather than inventing fields; this works for an MCP-only
agent without source-file access. `examples` contains direct requests; `capability_examples` entries wrap a
runnable `request` with invented premise/expected-result notes.

Then use `trialledger reason --request FILE`, or MCP `reason(request)`, with an `operation` of `entailment`,
`coordinates`, `corpus`, `design_bounds`, `signals`, `interpretations`, `source_assertions`,
`evidence_requests` or `design_session`. The same public
contract is `TrialLedger.layer2.run(request)`.

Every operation name above is also a focused discovery view. Python callers can use strict
`layer2.construction` helpers for quantity/enum/literal/scoped assertions and inspect `expanded` canonical
inputs. They require explicit scope/force/origin and default to proposed; they do not interpret prose.

Ground every premise. Ask about the clinical distinction: all participants or one cohort; required versus
permitted; prior therapy for advanced disease or any treatment; one qualifying mutation or compound; inclusive
limit or not; exposure versus follow-up time. Two readings can give opposite answers (the worked session's exon
20 steps); that choice is the person's. Mark an unconfirmed reading `"status": "proposed"`, which entailment
refuses to conclude from. This is a caller-supplied status, not independent verification of confirmation. An
agreed interpretation is the person's premise, never a registry fact. Coordinates and corpus require explicit
`standing` (status, resolution, basis); omission stays pending. Corpus accepts known/resolved support only, with
trial-wide declarations and per-feature overrides. Coordinates keep interpolated support separate. Expectation
observations also retain inherited/per-row standing. Never mark an unsettled reading known or a trial typed just
to pass. Keep the true origin in basis; confirm the comparison set and represented features. See
[consumer admission](docs/REASONING_CONSUMERS.md).

Encoding obligations: a boolean literal takes no `members` or `number`; units are never converted; time scopes
match only when identical; convert Python tuples to lists before reusing a result in a request. WHO PS/ECOG
needs an explicitly warranted scoped relation, never name matching or implicit scale conversion. Inspect optional
entailment `translation_diagnostics` for same-predicate subject/unit/time differences; the diagnostic identifies
a translation question and never establishes equivalence.

Coordinate `effects` distinguish admission from actual use: unused, inactive, redundant, withheld,
narrowed or guarded. An active guard can preserve alternatives without removals. Finite `setting` is an
explicit restriction, distinct from `setting_word`; neither invents progression/maintenance equivalence.
Known and default-layer conflicts have different warrants. Interpretation `contrast` and metadata paths
name differing frame scopes/answers without changing the common verdict or independent fixed answers.
Frequency `description` names the declared-set count/denominator and descriptive threshold; even two of two
does not establish a clinical standard or class-association support.

Deliver the clinical question, confirmed premises and origins, the result in its category with its basis, open
items and the unchanged structured response, saved separately (for example `reason-result.json`) beside the
source workbook/record. Help the person revise a premise and rerun.

This complete entailment request asks whether male participants fit a brief requiring female participants. It
returns decision REFUTED with premise `population`: settled, as a consequence of the supplied brief, not an
extracted study finding or a universal clinical sex ontology.

```json
{
  "operation": "entailment",
  "assertions": [{
    "class": "ScopedAssertion",
    "id": "population",
    "criterion_ref": "user:brief",
    "modality": "required",
    "body": {
      "class": "Literal",
      "subject": {"class": "Subject", "kind": "participant"},
      "predicate": {"class": "Predicate", "kind": "demographic", "key": "eligible_sex"},
      "value": {"class": "Value", "kind": "enum", "members": ["female"]}
    },
    "rule": {"class": "Rule", "id": "user-choice", "version": "1", "warrants": ["user:brief"]},
    "status": "known",
    "resolution": "resolved"
  }],
  "query": {
    "class": "Literal",
    "subject": {"class": "Subject", "kind": "participant"},
    "predicate": {"class": "Predicate", "kind": "demographic", "key": "eligible_sex"},
    "value": {"class": "Value", "kind": "enum", "members": ["male"]}
  }
}
```

Keep disjunctions, qualifiers, referents, conditions, cohorts and time in their representation. Required(A or B)
does not require either alone. A proposed premise is not usable as fact; an interpolated one cannot produce a
known conclusion. Preserve named undetermined/inconsistent/unsupported outcomes and blockers.

The full automated writer additionally needs source-to-assertion compilation, general bindings, evidence
adapters, derivational significance, recommendations, user closure and protocol outputs. Its complete design and
actual component state are in openspec/changes/add-design-synthesis/design.md. No current `design`/`edits`
operation, automatic annotation import or old raw-reader fallback is available.

## MCP and verification

`trialledger mcp` serves doctor, scope, landscape, save_fetch, record and reason. Preview with scope, gather with
landscape and answer with record/address. Follow page.next_offset; pages hold at most 50 entries and default to
24,576 serialized bytes (`max_bytes`, 2,048–65,536). Large nested values return an explicit address directory:
follow the relevant address; it is navigation, not source data. Exact strings may return `text` with
`text_page`; follow `text_page.next_offset` as `text_offset` and concatenate unchanged to cover the requested
text. Neither first pages nor chunks are complete evidence. Use saved files for complete records and separate
full analyses; keep conversation focused on the question. These limits do not change scope, retrieval
completeness or logical outcomes, and do not bound the entire process's memory. `reason` is a separate typed
request. `verify FOLDER` replays saved reporting/archival inputs under their writing version; it establishes
reproduction rather than clinical truth. `pull` preserves complete source JSON/CSV and archival workbooks.

CLI-only assistants use the same selectors: `trialledger record FOLDER --part studies`,
`trialledger record FOLDER --part study --nct NCT...`, or
`trialledger record FOLDER --part address --address /studies/0/criteria`, with identical continuations.
Optional `source_context` copies local headings/labels and offsets beside passages; it does not decide
entry/crossover or cohort scope. Legacy replay details do not certify fields absent from that old format.
The Python-only deviation utility returns named invalid results for malformed audit/status/qualifiers,
never a verified deviation from an unknown code.

## Read the information inside an abstention

For date-order checks, `information.completion` preserves possible and excluded outcomes over valid codebook
completions. Explain those bounds without choosing missing source values; malformed inputs establish no
exclusions. A noncheckable withdrawal-reason account can still retain a known group/period not-completed
calculation. Safety denominator fallbacks name their group-total origin in visible Notes. Read these partial
results beside the headline and original evidence; never turn an unknown reason, type or collection into zero.
