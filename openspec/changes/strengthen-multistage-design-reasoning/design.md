# Design

## Context

See proposal.md. The existing solver compiles scopes as explicit Boolean guards but accumulates every open-scope blocker globally. Tables check coverage/overlap/reachability but no forbidden actions. Session analyses are independently computed; included analyses currently reach only the detailed Findings sheet. Raw NIH studies are retained but MCP reads only the clinical projection.

## Goals / Non-Goals

**Goals:** Preserve useful partial answers, enforce declared negative specifications, connect explicitly related definitions, and carry evidence and computed consequences through the actual operator workflow.

**Non-Goals:** Discover clinically necessary variables; equate safety triggers with outcome events; certify clinical safety, type-I-error control or a complete protocol; interpret source text automatically; authenticate caller confirmation.

## Decisions

1. Retain global satisfiability checks. Filter only open-scope blockers by the query's connected component, or by the actual deciding proof for definitive answers. Preserve all other admission/translation blockers. Negative eligibility witnesses still inspect every constraint and scope because any restriction may explain rejection.
2. Optional table `prohibitions` contain id, declared condition and action. Test intersection with action guards under the feasible domain; never add prohibitions to the domain constraints to erase counterexamples. Expose clear/violation/unresolved and the declared domain. Illustrative cases are independently bounded and explicitly incomplete when capped.
3. Optional session `definition_checks` bind two typed meanings to exact existing expanded analysis request/result addresses. Each reading and relation retains explicit status, resolution and basis; matching analysis targets are required. Accepted checks run existing entailment for implication, both directions for equivalence, or exclusion for disjointness. Different definitions alone are not conflict: conflict is relative to the declared relation. Proposed/unresolved meanings never become accepted premises. Fresh replay and budget accounting apply to these checks.
4. One analysis-summary row per returned signal, plus definition checks, names code, scope, standing, actual values, support, blockers and canonical address. It does not reimplement the inference engine or derive an uncited ratio. Full Findings remains available.
5. A retained-source handle is a transport object, not an assertion. It names a served report folder, NCT ID and content digest. Resolve only recognized source slots under the served root; verify identity/digest against the retained manifest. Store the full hydrated request so later replay does not depend on a mutable handle. Source access uses existing bounded paging without shortening exact text.
6. Public `prepare` expands typed atoms, logical combinations, criteria and questions/options into canonical requests. It returns every applied default and structured origin beside the expansion; absent standing remains proposed. This is construction/inspection, not reasoning or prose interpretation. Advanced canonical objects remain supported.
7. Revision compares residual conditions on an independent requirements axis. Parent decisions collect those from every actual option analysis, regardless of whether a display repeats them at decision level. A changed requirement with unchanged verdict is requirements_changed; real verdict changes retain answer_changed. Question changes retain priority.
8. Current session, previous session and supplied previous result are separately validated bounded JSON units. Their repeated source copies do not consume a single combined query-node cap. Per-unit strict JSON, depth/byte/node limits and aggregate actual solver/output budgets remain in force.
9. Retained preparation can execute by artifact identity through the shared delivery owner. Only a successful preparation artifact supplies an expansion. The canonical computed response retains the full construction ledger; compact delivery keeps counts and exact links. Revisions identify that ledger as historical, rather than overriding current attribution.
10. Table reservation computes a conservative finite partition over every declared domain/constraint/guard/prohibition threshold, then charges bounded checks/proof minimization plus illustration work. It does not reserve the per-call maximum for a smaller represented problem, and never changes execution budgets to make a request pass.
11. Empty-query source admission is inspection context, with no clinical answer to lose. New-trial silence is an unrepresented design question, without pretending feasibility was shown; historical silence remains an evidence question.

## Risks / Trade-offs

- Query-relevant uncertainty differs from whole eligibility → test both directions and all consumers, including negative witnesses and residual requirements.
- A clinically invalid declared relation can fail correctly → show the person's chosen relation and both typed readings; no numeric/name heuristic supplies it.
- Finite table case output can grow → bounded illustrations with counts and truncation; proof outcomes survive independently.
- New handles can escape a root or bind changed evidence → reject malformed paths, symlink escape, wrong identity and digest before computation.
- A concise summary can conceal uncertainty → retain standing/basis/scope and exact-result links; test proposed and limited cases.

## Migration Plan

All new request fields are optional; existing requests and canonical artifacts retain their meaning. Shared transport hydrates before existing reasoning validation. Commit the coherent change on main after full verification; revert the commit to roll back.
