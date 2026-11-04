# Start here: connected symbolic protocol design

## The assignment

Connect the existing symbolic reasoning into a coherent user-operated design workflow for endpoints, assessments, efficacy decisions and safety, with explicit evidence and unresolved choices. The person communicates through an LLM; the LLM translates and operates the tools. It must not improvise clinical premises and then present the program's conditional result as proof of that reading.

This is a persisted plan, not an implementation or a certificate. All implementation tasks are unchecked. Planning baseline is main `25c6bb5c29513f2159751d29c309620522e32425`; observe current code and other agents' work before applying. Start with the OpenSpec apply workflow for `connect-protocol-design-workflow` only after receiving implementation authorization.

## Mandatory reading order

1. Project AGENTS and `docs/THEORY_OF_THE_CASE.md`, then the relevant complete sections of `../add-design-synthesis/design.md` and its still-open tasks. Rohan's instructions govern over an agent's paraphrase.
2. [Proposal](proposal.md), [delta spec](specs/symbolic-trial-design/spec.md), [design](design.md).
3. [Normative contracts](contracts.md): epistemics, typed v2 schema, check/option semantics, exact mathematics, public delivery and limits.
4. [Verification contract](verification.md): paired intent cases, independent oracles, literal Detective discipline, source-backed clinical model runs and closure evidence.
5. [Parallel ownership](parallel-work.md), then [ordered tasks](tasks.md).
6. The machine's `code-verification.md`, `detective-protocol.md`, `project-composition.md` and applicable verification gates; the full engineering reference at `~/Projects/rohan-vinaik.github.io/papers/Core Documents/LLM_WORKFLOW/PROFESSIONAL_CODING_PERFORMANCE_ENGINEERING.md`. Read actual current instructions; this handoff does not waive them.

Do not give workers only the task list. They need the whole semantic contract plus a bounded P4 packet. Information flows down: the coordinator supplies user intent; workers supply checked facts. Shared files and final proof generation have one owner.

## Four small objects that explain the thesis

These are invented reasoning examples, not trial evidence:

| Clinician's question | Separate information channels | Warranted answer |
|---|---|---|
| “Can we call this a week-12 assessment plan?” | Nominal day 84; permitted [77,91]; collection ends day 80 | A feasible visit exists, but nominal support and full-window coverage fail. Do not silently narrow the protocol window. The person chooses the repair. |
| “Are we still estimating the chosen outcome after drug discontinuation?” | Explicit estimand requirement; measurement definition; collection plan; actual data state | A stop plan can conflict with the requirement while actual availability remains unknown. The strategy's name alone supplies no requirement. |
| “The dose rule covers every case; is it safe?” | Declared finite variables; reachability; action coverage; explicit forbidden actions | Complete coverage can coexist with a witnessed unsafe selection under an adopted prohibition. Coverage says nothing about unrepresented variables. |
| “Does this efficacy design meet our target?” | Chosen binary model; n/k/p0/p1; supplied probability thresholds; applicability assumptions | Exact probabilities can be computed and compared. Model applicability remains its own premise, and a survival/adaptive design is not silently substituted. |

The useful output is the decision list and shareable review: what the evidence says, what follows under stated premises, what conflicts, what remains possible and which choice or evidence would close it. The point is to conserve information with the appropriate warrant, not maximize settled labels or abstain away useful partial results.

## Execution order and stop lines

- First freeze exact interfaces and acceptance fixtures (tasks 1.1–1.6). This is mechanical specification work constrained by the plan; no builder invents missing clinical semantics.
- Release disjoint workers for objects/schedules/policies/statistics and later projections/view as slots permit. The coordinator alone changes shared replay, support, schemas, revision and delivery. Integrate vertical slices in task order; each owes its own docs, public checks and different clinical model-run walkthrough.
- Use named projections into existing solvers. No second designer, clinical keyword compiler, copied source reader, source mutation, automatic version migration or default clinical threshold.
- Final pins run serially under a frozen code/test/import basis. Read complete Detective output and obey its literal next actions. A stopped pin is a documented open limitation, not a reason to grind indefinitely or declare success. Only Rohan can accept that target's limitation.
- A genuine contradiction, unresolved binding, unsupported method, computation limit and open clinical choice are different outputs. Preserve their independent consequences through reply, revision and export.
- No autonomous complete-protocol or “medically certified” claim. This plan adds bounded protocol reasoning and a usable clinical handoff; general statistical methods, automatic clinical encoding and the full writer remain distinct work.

## Required finish packet

Current strict OpenSpec validation; current tests/oracles and real CLI/MCP evidence; producer-to-consumer trace with hashes; authored two-sign and exact proof-status index; varied clinical walkthrough receipts; source-linked decision list, protocol synopsis and Schedule of Assessments workbook; docs that match the demonstrated scope; coherent main commits/push only under implementation authorization. Report incomplete engineering gates separately from valid clinical unknowns.

No proof or test has been run for a future implementation merely because it is required here. OpenSpec reporting planning complete means the artifacts exist and validate, not that the build is complete.
