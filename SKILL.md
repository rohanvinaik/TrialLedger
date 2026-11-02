---
name: trialledger
description: Give a clinical-development person a source-backed reference workbook for named or searched ClinicalTrials.gov trials, then help them think through trial design with TrialLedger's symbolic reasoning. You translate their criteria and questions into confirmed premises and report computed answers (settled, something wrong, your call, not knowable from this evidence) with the deciding premise. The complete automated trial writer is designed and partly built.
---

# TrialLedger

Read AGENTS.md for the complete procedure. Layer one is mechanical: registry facts and fixed direct rules in
`landscape.xlsx` and `landscape.json`, answered from the saved record. Layer two is symbolic reasoning about
trial design: you translate, the `reason` operations reason. Restate the person's criteria and questions as
typed premises, show them back in plain words, ask about each ambiguity, encode only what they confirm, and
report the computed result in the person's terms with the premise that decided it. Do not reason about the
design yourself or apply an operation's rules by hand and call the outcome computed.

Label every statement: **from the record** (with its address), **computed** (with its deciding premise or
counts) or **your reading** (said plainly). A question no operation computes, such as whether efficacy results
are impressive, is answered as your reading of the record.

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
`{"request":{"operation":"describe"}}`, or put `{"operation":"describe"}` in a file and run
`trialledger reason --request FILE`. Read `answer_guide`, `question_vocabulary` and `worked_session`; every
worked-session request runs and returns its stated result. Use the described shapes rather than inventing
fields; this works for an MCP-only agent without source-file access. `examples` contains direct requests;
`capability_examples` entries wrap a runnable `request` with invented premise/expected-result notes.

Then use `trialledger reason --request FILE`, or MCP `reason(request)`, with an `operation` of `entailment`,
`coordinates` or `corpus`. The same public contract is `TrialLedger.layer2.run(request)`.

Ground every premise. Ask about the clinical distinction: all participants or one cohort; required versus
permitted; prior therapy for advanced disease or any treatment; one qualifying mutation or compound; inclusive
limit or not; exposure versus follow-up time. Two readings can give opposite answers (the worked session's
exon 20 steps); that choice is the person's. Mark an unconfirmed reading `"status": "proposed"`, which
entailment refuses to conclude from. Coordinates and corpus do not enforce confirmation: confirm before
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
with landscape and answer with record/address. Follow page.next_offset; pages hold at most 50 entries.
`reason` is a separate typed request. `verify FOLDER` replays saved reporting/archival inputs under their
writing version; it establishes reproduction rather than clinical truth. `pull` preserves complete source
JSON/CSV and archival workbooks.
