# Session revision and work accounting

The session owner now emits `result_digest = session_state.digest(response["result"])`.
The fingerprint covers the complete canonical current result, not the transport envelope,
summary, clinical projection, previous replay or comparison. The public pure
`design_session.prepare_revision(previous_request, previous_response, next_session)`
checks the old session identity, target and result fingerprint. It fills only the
parent digest and expected prior-result digest. It neither edits clinical inputs nor
promotes their origins/standing. A conflicting supplied parent is refused.

Both snapshots are freshly executed. The full existing `diff` is unchanged. The
additive `answer_diff` compares analyses and declared decisions independently across
answer, deciding support and actual deciding origin. Its rows retain every changed
axis, both projections and canonical before/after result paths. A priority label
never suppresses simultaneous changes. Refusals and unknown projections are explicitly
not comparable, rather than silently treated as equal answers. The shared
`clinical_answers.change_projection` owns the clinical projection for both analyses
and decisions; session-owned effective premises are supplied only as provenance context.

## Conservative work bound

No semantic solver bound is changed. `_satisfiable` already uses exact finite
partitions: a Boolean has 2 representatives, m numeric thresholds have 2m+1 exact
rational cells, and m enum members have m+1 representatives including an unlisted
member. Reservation uses the existing typed formula compiler and connected-component
owner. Removing premises for proof minimization cannot add variables, thresholds or
members. Taking the largest represented component (capped at the declared solver
bound) therefore bounds every enumeration in an ordinary decision, including global
consistency checks of components disconnected from the query.

For n supplied assertions, ordinary decision/proof checks use at most 2n+4 solver
calls. The shared explanation plan adds at most 2 decisions per planned condition
(maximum 8), plus one intrinsic-query feasibility check. Its candidate atoms and
thresholds already belong to the original query component. The same plan is consumed
by explanation and reservation. Interpretation fixed/local/combined consistency and
all query/frame uses are separately reserved. Accepted witnesses reserve their
intrinsic profile check; rejected witnesses reserve up to 3n+8 calls and the full
candidate-union partition, because disconnected criteria can explain rejection.
Derived witness bodies retain the full declared assignment ceiling until compiled.
Source assertion compilation is pure; its generated child requests are reserved
recursively. Nested decision-table checks retain their existing conservative
full-bound accounting. Unsupported estimates retain operation-specific full-bound
call ceilings rather than an invented smaller domain.

`SessionBudgetError(ValueError).diagnostics` retains the exact named refusal and
numeric cumulative analyses, expanded-item diagnostic, reserved work, effective
limits and reservation for the refused request. The refused child does not execute.
The same cumulative owner covers fresh old/current analyses and pairwise decision
checks. No old result is reused to save work.

## Verification packet locations

- `/Users/rohanvinaik/trialledger-runs/session-revision-hfref-20261104/`: complete
  copied HFrEF sources and workbook, public default-bound request/result pairs,
  instrumented replay, every solver call/formula and a computed receipt.
- `/Users/rohanvinaik/trialledger-runs/session-revision-observational-20261104/`:
  fresh NCT00106899 observational Alzheimer's cohort pull, verified workbook,
  simulated new-cohort age-choice/revision requests and real CLI/MCP responses.
- Authored tests: `tests/test_session_revision_delivery.py` and
  `tests/test_session_solver_work.py` plus existing session contract/work-scope suites.

All persona choices are simulated, not independently authenticated human confirmations.
The observational record reports general 55–90 eligibility separately from a current
healthy-control 70–90 recruitment note. The walkthrough does not adopt that note as
universal historical eligibility. `verify` establishes reproduction from retained
sources, not source truth. CrossHair confirmed the two named-code decisions over all
paths; the partition-product postcondition was Not confirmed, with no reported
counterexample. Detective two-sign evidence is handed off separately for adoption.
