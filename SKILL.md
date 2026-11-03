---
name: trialledger
description: Help a clinical-development person find the trial-design decisions that need their clinical judgment, each with evidence from comparable trials and computed consequences, and examine what other trials did. Gather a source-backed reference workbook, prepare agreed comparison features and premises, run TrialLedger's symbolic tools, and help revise the working design with traceable evidence and computed checks. The reference sheet is useful independently; complete automated protocol writing is designed and partly built.
---

# TrialLedger

TrialLedger doesn't make the person's clinical decisions; it finds them, each with its evidence and computed
consequences. The clinical question is: "What have these trials done, what should we choose, and what happens
if we change it?" Gather the evidence, make the person's choice precise, check its consequences and help them
revise it. They make the clinical judgments; you keep the evidence, accepted choices and computed checks
connected in the decision list.
The reference workbook is both a standalone deliverable and a base for continuing design work.

Read AGENTS.md for the complete procedure. Layer one is mechanical: registry facts and fixed direct rules in
`landscape.xlsx` and `landscape.json`, answered from the saved record. Layer two is symbolic reasoning about
trial design: you translate, the `reason` operations reason. Restate the person's criteria and questions as
typed premises, show them back in plain words, ask about each ambiguity, encode only what they confirm, and
report the computed result in the person's terms with the premise that decided it. Do not reason about the
design yourself or apply an operation's rules by hand and call the outcome computed.

Start with the requested clinical task, check capabilities before promising delivery, and handle internal
paging and retries yourself. Show material reasoning premises together, confirm interpretations once and
reuse them until changed. Give the answer, its deciding basis and material open items. Offer a relevant next
step when useful; do not require a tour of software or repeated correctness disclaimers.

Distinguish **from the record** (with its address), **computed** (with its deciding premise or
counts) and **your reading** through natural language. A question no operation computes, such as whether efficacy results
are impressive, is answered as your reading of the record.

## Keep the working session connected

Follow the [worked clinical conversation](README.md#a-design-session-in-practice). Read the relevant saved
evidence, agree the comparison set/features or design premises, run the appropriate operation, explain the
deciding basis and rerun when a choice changes. Free-text interpretation and preparation of typed inputs are
your work with the person; `corpus` and `entailment` do not automatically ingest eligibility paragraphs from
`landscape.json`. A documented class pattern is descriptive, and a near miss compares the declared features.

Keep a **decision list** as the session's main deliverable. Each entry holds the decision in clinical words,
the evidence (record addresses, or registry silence), the computed consequence of each option with its
deciding premises, and its status (open, or chosen by the person). Something's wrong goes first as a blocker;
your call becomes an entry; not knowable becomes an evidence gap; settled results are cited as context. When
the person settles a decision, record it as their premise and recompute what depends on it, and hand over the
list at the end. Alongside it keep the question, comparison set and latest checks. With file-writing access,
save the list in `working-brief.md` and the actual request/result pairs separately from the source record.
Brief notes are not extra fields in the validated reasoning request. Those files are maintained by you, not
automatically by `reason`; without file access, return the decision list and results for reuse. A revised premise needs a fresh computation, not a relabelled previous answer.

Explain the current hand-off once in clinical terms: you read and structure the text with the person, the
program computes the supported comparisons and consequences, and complete automated protocol generation
remains unintegrated. Offer the reasoning work when useful; reference-sheet requests can end with delivery.

## The four answers

- **Settled:** required or ruled out (ENTAILED/REFUTED), or explicitly narrowed; "settled by default" when the
  basis is interpolated or an NSCLC default leaves a single value (a default leaving several is your call).
- **Something's wrong:** INCONSISTENT criteria (blocks every answer until resolved), a coordinate `conflict` or a
  `registry_checks` conflict. Name both sides.
- **Your call:** allowed but not required, proposals, comparable trials that chose differently, which cohort,
  confirming a reading, or whether criteria silent on something should address it.
- **Not knowable from this evidence:** silence, too little support, unknown membership, abstention, a
  computation limit.

UNDETERMINED is exact abstention, not failure. "Must everyone be at least 65?" against a brief requiring 18 or
older is **allowed but not required**. Read every blocker and report the most specific: `proposed_refused`
(confirm the reading), `open_scope` (which cohort), `unresolved_*`/`unspecified_boundary`/`opaque` (settle the
wording), `resource_bound` (narrow the question), `no_constraint_mentions_query` (check units and time windows,
then ask whether the criteria should address it), and `undecided_by_constraints` alone (allowed but not
required). The describe `answer_guide` holds the complete mapping.

## What the person can explore

- Gather a clean reference sheet, then drill into exact population/eligibility, outcomes and time points,
  group-specific efficacy/safety, source drug identities/classes and direct registry consistency findings.
- Whether a patient type is in or out under confirmed criteria and which criterion decides it; whether the
  criteria contradict each other (entailment).
- Which NSCLC settings, prior lines and biomarker selections the criteria imply (coordinates; defaults shown
  as defaults).
- What observed baseline participants rule out about missing eligibility restrictions (`design_bounds`).
  Discover its focused guide. Confirm population/group, participant counts, measurement identity, time and
  an exception allowance before accepting the eligibility bridge. Keep unconfirmed bridges proposed or
  unresolved, and accepted defaults interpolated. Candidate eliminations feed a common-consequence query;
  put the conditional bound and remaining choices on the decision list. Zero/missing categories do not
  exclude, overlapping marginals never sum, and an observed maximum does not recover an exact cutoff.
  WHO PS does not silently become ECOG. Derived bounds are separate from source-stated corpus elements.
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

## Partial evidence in the decision list

Discover `signals` before encoding an overlap, partition, exact summary, population subset, temporal graph,
regimen, directional relation or adopted-rule dependency. Every signal needs nonempty source/premise support,
its standing and resolution. Matching denominators do not establish the same universe. Rounded summaries do
not establish exact extrema/median witnesses; a median also needs its stated convention. Retain assessed
populations and distinguish missing, unavailable, imputed and observed measurements.

Use `design_bounds.signals` to consume these results: a derived observation selects a signal and emitted
witness, with explicit participant-predicate bindings and the same population/denominator; a candidate's
`signal_claims` constrain that signal jointly. Keep returned count intervals visible and compare only their
lower bound with the exception allowance. Direction `rejected` requires a rejection attributed to eligibility,
not a generic withdrawal label: a partial profile needs a feasible rejected completion, not universal
exclusion. `profile_inconsistent` is a translation problem in either direction.

A supported input conflict blocks the design consequence. Proposed or unresolved support cannot eliminate a
candidate. An unattached signal remains context; dependent claims/observations must explicitly reference it.
No automatic cross-signal join, scale conversion or source-field interpretation occurs. Put each result's
rule, sources and weakest standing on the relevant decision entry; revise premises and rerun. Derived bounds
never become source-stated criteria in corpus frequency calculations.

## Reference sheet

For an assistant-operated local run, first inspect whether this environment has local execution, network,
report-folder read/write and workbook-delivery capability. If Python execution and report-folder writing are
available, install TrialLedger in the assistant's own Python 3.12+ environment and run `doctor`; a repository
URL alone does not establish installation or access. Relay bridges missing network access only: it still
requires Python execution and report-folder writing, plus the ability to fetch each complete response body.
Without execution or report writing, relay cannot make a local run possible; explain the specific gap and use
a compatible environment.

Translate an ordinary drug/class phrase to source-backed identity candidates and confirm the intended source
identity before searching. If multiple class candidates match, show their names and IDs for resolution; after
one is selected, expand only that class in preview. For example, “EGFR inhibitors” may be checked against ATC
class `L01EB`; show the selected class's members and filters before gathering. Do not expand every candidate
or ask the clinician to select an app when the assistant can inspect its own capabilities.

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
   reconstruction of a registry page. The JSON is a declared clinical selection; complete source responses
   are retained separately.

Source copies are plain values with sources defined once in `fields`. Direct transformations name their
rules/inputs. Keep exact prose, populations, local groups, denominators, units, periods, precision, zero and
false. Not stated is not none; not posted is not no effect; empty listings are not zero harms. Malformed
scalar source types produce a named refusal, not a fabricated typed report. Drug identity/conflicts use
canonical source evidence; no alias-first choice or name-prefix widening. Eligibility divisions do not
interpret clinical meaning. Registered plans and posted observations remain separate.

Do not infer biomarker roles, setting, current care, grades, comparability, planning targets or reusable
standards while producing the report. Those are separately identified reasoning tasks.

## Typed symbolic reasoning

First discover the actual interface: call MCP tool `reason` with arguments
`{"request":{"operation":"describe"}}` for the overview, then
`{"request":{"operation":"describe","view":"entailment"}}` (or `coordinates` / `corpus`) for the relevant
input shapes, guides and runnable `example`. For the CLI, save the inner object (for example
`{"operation":"describe","view":"entailment"}`) in a file and use `trialledger reason --request FILE`.
Views `worked_session` and `full` retain the complete
demonstration and manual on demand; every worked-session request returns its stated result.
Use the described shapes rather than inventing
fields; this works for an MCP-only agent without source-file access. `examples` contains direct requests;
`capability_examples` entries wrap a runnable `request` with invented premise/expected-result notes.

Then use `trialledger reason --request FILE`, or MCP `reason(request)`, with an `operation` of `entailment`,
`coordinates`, `corpus`, `design_bounds` or `signals`. The same public contract is `TrialLedger.layer2.run(request)`.

Ground every premise. Ask about the clinical distinction: all participants or one cohort; required versus
permitted; prior therapy for advanced disease or any treatment; one qualifying mutation or compound; inclusive
limit or not; exposure versus follow-up time. Two readings can give opposite answers (the worked session's
exon 20 steps); that choice is the person's. Mark an unconfirmed reading `"status": "proposed"`, which
entailment refuses to conclude from. This is a caller-supplied status, not independent verification of
confirmation. An agreed interpretation is the person's premise, never a registry fact. Coordinates and
corpus do not enforce confirmation: confirm before
running and keep the true origin in `ref`/`basis`; never mark a trial `typed` just to pass. For corpus work,
confirm the comparison set and represented features.

Encoding obligations: a boolean literal takes no `members` or `number`; units are never converted; time scopes
match only when identical; convert Python tuples to lists before reusing a result in a request.

Deliver the clinical question, confirmed premises and origins, the result in its category with its basis,
open items and the unchanged structured response, saved separately (for example `reason-result.json`) beside
the source workbook/record. Help the person revise a premise and rerun.

This complete entailment request asks whether male participants fit a brief requiring female participants.
It returns decision REFUTED with premise `population`: settled, as a consequence of the supplied brief, not an
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
adapters, derivational significance, recommendations, user closure and protocol outputs. Its complete design
and actual component state are in openspec/changes/add-design-synthesis/design.md. No current
`design`/`edits` operation, automatic annotation import or old raw-reader fallback is available.

## MCP and verification

`trialledger mcp` serves doctor, scope, landscape, save_fetch, record and reason. Preview with scope, gather
with landscape and answer with record/address. Follow page.next_offset; pages hold at most 50 entries and
default to 24,576 serialized bytes (`max_bytes`, 2,048–65,536). Large nested values return an explicit address
directory: follow the relevant address; it is navigation, not source data. Exact strings may return `text`
with `text_page`; follow `text_page.next_offset` as `text_offset` and concatenate unchanged to cover the
requested text. Neither first pages nor chunks are complete evidence. Use saved files for complete records
and separate full analyses; keep conversation focused on the question. These limits do not change scope,
retrieval completeness or logical outcomes, and do not bound the entire process's memory.
`reason` is a separate typed request. `verify FOLDER` replays saved reporting/archival inputs under their
writing version; it establishes reproduction rather than clinical truth. `pull` preserves complete source
JSON/CSV and archival workbooks.
