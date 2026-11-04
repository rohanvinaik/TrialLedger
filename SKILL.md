---
name: trialledger
description: Gather clinical-trial reference workbooks and help a clinical-development person find design decisions needing judgment, with source evidence, exact computed consequences, competing readings, revisions and a shareable decision workbook. Complete automatic protocol writing remains unintegrated.
---

# TrialLedger

**TrialLedger doesn't make the person's clinical decisions; it finds them.** Operate the evidence tools,
translate clinical wording into precise premises, and explain computed consequences. Read
[AGENTS.md](AGENTS.md) for the checklist, [the public workflow](docs/CLINICAL_WORKFLOW.md) for connected calls,
and the relevant complete section of [the operator reference](docs/OPERATOR_REFERENCE.md) before unfamiliar
encoding work. Use the [README's](README.md) clinical language.

1. Inspect execution, network, writing and delivery capabilities. Run doctor, preview agreed scope, gather
   and deliver landscape.xlsx. Answer from matching landscape.json; read relevant exact addresses and follow
   every required page/text continuation. Keep populations, groups, units, denominators and time.
2. Restate material premises from the actual request: AND/OR, qualifiers, negation, applicability, scope,
   inclusivity, time, required versus permitted. Confirm interpretations once, retain wording/origin and
   reuse unchanged agreements. Copied values need no approval. Label simulated choices explicitly.
3. Discover and run the relevant operation. You translate; TrialLedger reasons. Report deciding support and
   material open items; never apply its rules yourself and call that computed. Recompute changed premises.
4. Retain complete checks explicitly, revise through public retained state, export the decision workbook
   and readable list, and deliver returned paths beside unchanged source evidence. Keep the narrative brief.

## Keep the epistemic boundary

Say “the registry reports”, “given your criteria”, “under this working assumption”, “my reading is” and
“you chose” where each matters. Conclusions never exceed their weakest effective premise. Interpolated
means overridable, settled by default. Ordinary entailment refuses proposed support; named hypothetical
frames may explore it without making it a fact. Caller status/origin labels do not authenticate truth or
human confirmation. A mistranslation gives an exact answer to the wrong question.

Same patients, corresponding cohorts/arms, WHO PS/ECOG relations, units/windows, assessment identity,
eligibility bridges, adopted definitions and adoption of comparator restrictions need warranted premises.
Equal names or totals never supply them. Units are not converted and time scopes match only when identical.
Boolean literals have no operand. Silence is not absence; unknown is not false. Counts describe the agreed
set and never establish a clinical standard, requirement or recommendation.

An open answer can contain useful proved information: permission is not requirement or an exclusion override;
a necessary condition says **if the profile fits, this must hold**, not that complete eligibility fits.
Criteria-wide requirements can also be shown when the partial profile has not established them. Neither
means actual absence; preserve disjunctions and bounded coverage. Read
explanations, proof, standing, scope and every blocker together. Distinguish translation questions, evidence
gaps, genuine feasible choices and unfinished computation. Limits are computation tasks, never evidence of
absence or design freedom.

## Discover one task at a time

MCP reason takes `{"request":{"operation":"describe"}}`, then an operation view such as entailment for a
compact card and invented runnable example. Execute its example, not metadata. Add `"detail":"schema"`
inside request for structural schemas/named field contracts, or `"detail":"full"` for the complete focused
guide. Full and worked_session views retain the manual and teaching session; delivery describes retention,
revision and export. CLI takes the inner object in a file: `trialledger reason --request FILE`.

| Need | Operation |
|---|---|
| What do criteria require, allow or rule out? | entailment |
| What NSCLC setting follows, with defaults labelled? | coordinates |
| How common, unusual, associated or different in the agreed set? | corpus |
| What do observed accepted/rejected profiles rule out? | design_bounds |
| What do partial tables, stages or definitions constrain? | signals |
| What does each rival reading imply? | interpretations |
| Bind a complete retained NIH record and exact anchors | source_assertions |
| What hypothetical evidence distinguishes survivors? | evidence_requests |
| Keep sources, choices, analyses and revisions connected | design_session |

Python construction helpers expose canonical Always/AllOf/AnyOf/Not and strict literal/quantity/assertion
constructors; expanded shows exact inputs. They do not interpret prose. Structural schemas do not certify
clinical meaning, cross-field admission or source truth.

## Retain and hand over

Pure computation writes no files. MCP reason uses retain:true or response_view:"compact"; CLI uses --store
and optionally --compact. Compact replies default to 24,576 bytes; max_bytes/--max-bytes accepts
2,048–65,536 with counts and exact continuation. Full mode stays full. The complete canonical request/response stay separate from source reports.
Result_digest identifies result only; artifact ID identifies the complete payload, neither clinical truth.

- reason_result / reason-result part decision_view reads profiles, deciding criteria, linked context and
  open items together; raw decisions, changes and exact addresses remain available. Follow relevant page/text
  continuations; compact output references the complete retrievable artifact.
- reason_revise / reason-revise takes the artifact ID plus an explicit next session or bounded replacement
  edits and revision label. Changed premises need origins. The program fills integrity fingerprints and
  freshly replays both snapshots; prepare_only returns the valid request without executing.
- reason_export / reason-export writes a separate workbook, readable list, manifest and canonical inputs.
  The output parent must not exist; publication is its review child. Deliver actual returned paths. Source evidence stays unchanged. Included standalone analyses remain
  separate unless explicitly linked by the session; caller-declared choices remain unauthenticated.

Each decision holds the question, evidence/silence, alternatives and computed consequences, deciding
premises, open items, selection and origin. Put contradictions first; retain independent settled results.
Caller questions and labels remain attributed beside represented profiles. Optional exact-anchored decision
evidence supplies context only; quote, reading and gap notes never add an implicit restriction or establish
source absence. Accepted readings/adoptions need admitted premises. Answer_diff separates
question/answer/support/origin/wording/context changes; audit diff records input/carrier changes. They answer
different questions. Retained snapshots are not a background manager.

Doctor/scope/landscape/save_fetch/record operate source reports. Relay still needs execution, writing and
complete unchanged bodies. Acquisition defaults (1,000 studies/100 requests) guard NIH access, separate from
local solver/analysis/output limits. Never trim evidence or use stale answers to pass a limit. Verify checks
reproducibility, not clinical truth. Heading context does not decide entry/crossover scope. Complete prose
compilation, protocol writing, publication reading and derivational significance remain unintegrated.
