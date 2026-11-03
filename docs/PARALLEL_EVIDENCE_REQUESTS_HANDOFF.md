# Parallel implementation contract: distinguishing evidence requests

Status: the external contribution is frozen and handed back. This document preserves its original exclusive
ownership contract; public integration now belongs to the lead. The integrated discovery views are
`evidence_requests` and `design_session`. Exact primitive receipts and their limitations are retained under
the integration change's evidence directory. The external handoff itself did not claim public integration.

## Purpose and clinical object

Build tasks 2a.1–2a.3 of `openspec/changes/integrate-warranted-design-session/tasks.md` as an isolated contribution. The lead session retains public integration and acceptance ownership.

Clinical question: two candidate eligibility explanations survive current evidence. What hypothetical participant profile, with an explicit accepted or eligibility-rejected sign, would distinguish them? The output is an investigation request, never an observation, a recommendation, or a recovered protocol.

Example: one candidate requires adulthood and ECOG ≤2; another additionally requires a marker. An adult ECOG-2, marker-negative participant rejected for eligibility can contradict the first explanation while fitting the second. A partial rejected adult ECOG-2 profile can also distinguish them when the first claims complete eligibility and the second admits an unrepresented marker completion. Do not invent the participant's actual marker status or infer that every ECOG-2 participant is excluded.

## Read first, in whole units

- `AGENTS.md`, `DEVELOPING.md`, `docs/THEORY_OF_THE_CASE.md`.
- The integration change's complete proposal, design, tasks and symbolic-trial-design spec delta. Section 2a is the governing bounded contract.
- Existing design-bounds and eligibility-witness definitions, their complete caller functions and relevant tests. Use a symbol map/AST and whole-unit reading. Do not use grep or extract text fragments.
- The engineering and Detective protocols referenced by AGENTS.md. The lead owns the shared Serena session; this agent uses maps/AST/whole reads.

## Exclusive ownership and delivery

Work from `/Users/rohanvinaik/tools/TrialLedger` on main. Do not create a branch or worktree. The following NEW files alone may be added to the shared checkout:

- `TrialLedger/layer2/evidence_requests.py`
- `TrialLedger/layer2/evidence_requests_guide.py`
- `tests/test_evidence_requests.py`

First send the lead the proposed closed request/result schema and the existing solver reuse points. Do not silently choose an incompatible schema. Keep proof work and bulky artifacts under a fresh `/tmp/trialledger-evidence-requests-<unique>/` directory. Return exact source/tests, full proof exports and commands to the lead.

Do not edit service.py, design_bounds.py, entail.py, signals.py, result_semantics.py, existing guides, certificates, examples, documentation or OpenSpec artifacts. Do not commit, stage, push or mutate retained source records. Do not add dependencies. Ask the lead before changing this ownership boundary.

## Required behavior

1. Reuse the existing scoped participant-witness decision engine. Do not implement a second eligibility solver. Preserve complete-eligibility claims versus partial restrictions for negative witnesses.
2. Use explicitly declared survivors, represented variables/domains, exact units, scope and comparison boundaries. Reject unsupported domains or bindings by name. Never assume the candidate family exhausts clinical protocols.
3. Search finite represented comparison cells, including supported partial profiles. Keep unspecified attributes unspecified. A negative witness means an ineligible completion exists, not universal exclusion of its partial profile.
4. Return profile, accepted/rejected sign, affected candidates, deciding checks/proofs, and required attribution/exception premises. Hypothetical rows cannot enter the evidence ledger automatically.
5. Order least-specified separating profiles first, with deterministic ties. Check weakening within the searched representation. This ordering is structural; it is not clinical utility or an evidence-availability probability.
6. Name an appropriate place to seek evidence: eligibility-attributed screening/adjudication records for rejected witnesses; appropriately bound participation records for accepted witnesses. Do not claim the evidence exists. Corpus silence never supplies a negative witness.
7. Bound aggregate enumeration, solver work, requests per pair, total returned requests and response bytes. Separate incomplete search from output truncation. Never invent an omitted count or report no separator after unfinished work.
8. Handle zero survivors as conflict, one survivor as no within-family separation needed, completed absence of separators, mixed signs, open boundaries and resource limits explicitly. A surviving candidate remains compatible, not historically identified.
9. Retain weakest support and scope through every returned check. Proposed readings may be explored conditionally under existing frame rules but cannot become ordinary factual premises.

## Verification and evidence

- Author positive and MUST-NOT tests directly against the decision functions, including scope mismatch, attribution ambiguity, exception thresholds, partial profiles, deterministic order, zero/one survivor, no separator, truncation and limits.
- Run project Ruff and advisory ty. Use actual Detective `--two-sign` and explicit CrossHair contracts on suitable pure primitive decisions, following the full printed next-action protocol in a fresh scratch directory. Preserve full reports, generated tests, configuration, hashes and residuals. Do not hand-edit generated suites or manufacture equivalence claims.
- Supply runnable public-operation examples for the lead to expose. Do not claim CLI/MCP integration before the lead wires and executes it.
- The lead will execute matching CLI/MCP requests and a fresh model-operated clinical walkthrough after integration. If the other agent can acquire a useful screening/run-in example, retain it separately and identify exactly what is documentary, interpreted and hypothetical; it does not replace that final integrated walkthrough.

## Return to the lead

Report files and exact commands, measured test results, solver reuse points, schema/refusal codes, proof scope and residuals, and concrete counterexamples discovered. Return facts. Clinical meaning, architecture decisions and final completion claims remain with the lead under the user's instructions.
