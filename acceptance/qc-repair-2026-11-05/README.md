# QC reporting repair, 2026-11-05

Rohan's request: “Yes, continue. Fix all three issues with the same rigor, preserve the other agent’s
Detective files, then commit and push on main. Follow GitHub CI through successful publication and verify
that the QC reporting is honest.” He also identified README badge drift as part of the defect.

The specimen is the QC pipeline and its published claims. The instruments are the project's information
preservation rules, independent regression contracts, actual archived CLI execution, and remote run and
publication receipts. A passing local gate is evidence about that tree, not a successful GitHub deployment.

| Claim | Kind and scope | Falsifier | Check |
|---|---|---|---|
| Public MCP tests are portable | Execution invariant, Ubuntu and local test environments | A test requires a personal launcher | Reuse the initialized CLI/MCP client; no absent-launcher skips |
| Coverage runs archived code | Measurement invariant, one archived commit | The CLI is missing or imports changed live code | Console entry point from the snapshot's project declaration; adversarial external working directory and live-source change; full archived coverage run |
| Deferred targets remain unresolved | Conservation invariant, incremental census | An omitted unpinned target disappears and produces Measured | Independent limit/deadline/replay/coverage-only contracts and positive complete control |
| Deadline exhaustion is not a kill | Measurement invariant, selected subprocesses | Partial outcomes count as a completed function or budget timeout as a caught mutant | Independent fake-clock boundaries, discarded partial results and restored-source assertions |
| Badges disclose their actual basis | Reporting invariant, generated site and README | Missing measurement provenance, silent historical census or unobserved deployment | Compact measured signals, linked dated report, exact input applicability and post-push read-back |

## Wiring

`archive` provisions the snapshot's declared console entry point using the measuring interpreter's
dependencies. Its imports explicitly select the archived source. `publish_coverage` and every mutation
worker share this owner; neither borrows the live checkout's CLI implementation.

`census_scope` retains the current pinned set and the remembered sampled identities, including
`pending_targets`. Limits and worker deadlines both produce deferred targets. `reconcile_census` keeps an
old result only as stale, or retains the exact never-measured identity. The next incremental run consumes
those identities. A legacy anonymous missing-count remains explicitly unresolved until a fresh
non-incremental census declares a new sample. No missing identity becomes a measurement.

`census_test_run` caps each subprocess by the remaining budget. A budget timeout, including equality with
the ordinary test timeout, defers the whole function. Earlier partial outcomes are discarded; source
restoration still runs. Ordinary test timeouts before budget exhaustion remain separately counted.

`render` consumes these results without strengthening them. Historical and incomplete mutation badges
remain neutral, coverage-only publication preserves the census's own date, and a reuse-only run records a
separate check date. Passing, skipped and deselected test counts are parsed independently. Every numeric
badge originally included its measurement commit/date. The current-build follow-up below moves that
provenance into the linked report and verifies applicability separately from presentation.

## Evidence and boundaries

The original push at `2202323` failed both remote workflows. Tests failed on three machine-specific MCP
launches; Quality failed in archived public-CLI tests. The earlier local gate did not establish remote
success. The original remote runs remain inspectable:

- [Tests failure](https://github.com/rohanvinaik/TrialLedger/actions/runs/42114875208)
- [Quality failure](https://github.com/rohanvinaik/TrialLedger/actions/runs/42114875281)

The independent pending-scope and deadline packets use explicit measurement doubles for orchestration;
they do not prove mutation adequacy. `test_quality_metrics.py` separately executes real coverage and
mutation subprocesses on miniature repositories under the workflow's coverage overlay. Actual CLI/MCP
regressions exercise coverage access and conditional clinical exports without changing clinical semantics.

`contracts.py` contains three CrossHair contracts over fixed declared target shapes. All three reported
Confirmed over all paths. They cover skip/history and pending-sample alternatives, not every possible
record or subprocess behavior. Target-specific Detective receipts retain their exact qualifications.
No whole-codebase deep proof is acquired by association with these checks.

Detective's retained [reconciliation receipt](proofs/reconcile_census.txt) reports COMPLETE modulo four
unproven equivalences, 34/34 killed. Its [sample-scope receipt](proofs/census_scope.txt) remains INCOMPLETE:
three killable residuals, 66/67 killed, including a refused seeded-Random golden capture. The requested
exception assertions are authored and pass; this is not treated as a completed pin or an accepted waiver.
The exact target AST fingerprints are retained in [targets.json](proofs/targets.json). These outcomes do
not change the independent public execution and information-preservation checks.

Full local gate, archived measurement, proof work and post-push publication receipts are retained under
`~/trialledger-runs/ci-repair-20261105/`. Remote completion requires both workflows for the actual pushed
commit and a live metrics/badge read-back after final Pages deployment. The dated local measurements in
that packet are not a substitute for those remote receipts.

The other agent's modified certificate and preview-scope suite are excluded from this change and preserved
byte-for-byte. No clinical source record, admission rule, standing or symbolic clinical outcome is changed.

## Current-build badge follow-up

The compact README keeps the existing measured test, coverage and decision-mutation signals. Commit/date,
method and detailed scope stay in the linked report; repository and published-report links resolve in their
own locations. Badge presentation does not supply measurement evidence.

Mutation records now carry a fingerprint of the actual archived inputs and measurement environment.
Archived manifests exclude generated coverage files and console wrappers from that identity. Code, test
fixtures, lockfiles and executable README examples remain inputs; README prose and layout do not.
A complete matching census can therefore apply to a presentation-only revision while retaining its real
measurement commit/date. Missing, legacy, stale or mismatched evidence requires remeasurement. The
coordinator refuses a missing or different worker fingerprint instead of replacing it with its own.
`applicability_contracts.py` checks all combinations of matching input, complete scope and pending work;
CrossHair reported Confirmed over all paths for that bounded contract. Independent regressions cover the
producer, archive, scheduling, carry-forward and public reporting boundaries. A manual 120-minute refresh
is available for the one-time migration from records without this evidence; an old score labelled
Historical is not treated as completion of that refresh.

Function targets use their full lexical identity, including class and enclosing function, with a source
location distinguishing repeated declarations at the same lexical path. The worker verifies that exact
target's body fingerprint before changing it. Test selection still uses the leaf name conservatively.
Legacy leaf-only sample identities retain all matching current declarations until remeasurement rather
than silently dropping ambiguous members. Independent two-sign regressions inspect the actual mutated
source and refuse wrong or stale targets; applicability cannot collapse two distinct target identities.
