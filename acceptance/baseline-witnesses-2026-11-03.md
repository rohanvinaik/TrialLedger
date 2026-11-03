# Baseline witnesses — implementation and verification

## Pass brief and setup

Objective: use observed participant distributions as conditional symbolic bounds on missing eligibility
restrictions, and carry those bounds into the continuing design conversation. This is an authorized new
reasoning capability, not a same-answer optimization. Reporting values, evidence, workbooks and existing
operations remain protected. No source compiler, clinical token matcher or new dependency was introduced.

The starting revision was `99e54bb9cd982bdd5e34c51c0cb462cc66828103`, on main with a clean tree.
The declared environment is uv/pyproject/uv.lock; `uv sync --locked` succeeded. The selected interpreter was
Python 3.14.7. Production dependencies remain httpx and openpyxl. Source acquisition was available for the
retained development fixture; reasoning tests explicitly forbid network access. No credential is required.
The declared ordinary gate is `bash scripts/ci_local.sh`, and CI uses the same locked dependencies, Ruff,
formatting and whole pytest suite. Native clinical usability and independent protocol confirmation were not
measured by this pass.

## Code shape and proof obligation

`design_bounds` owns one inverse operation: test explicitly declared eligibility designs against typed
population witnesses. `service` owns request validation and object construction. `bounds_guide` owns the
focused schema, answer categories and runnable invented example. The existing `entail` engine remains the
single owner of participant logic. Side effects stay in the existing CLI/MCP boundaries.

For observation proposition P, participant count n and an accepted, resolved eligibility bridge allowing at
most k exceptions, n > k guarantees at least one eligible P witness. A candidate E for which E AND P is
unsatisfiable is therefore eliminated. The entailment engine establishes that incompatibility. This is
conditional on the supplied population/scale/time/count bindings, never a source-truth certification.

Every observation is checked independently: overlapping marginals, arm rows and totals never sum or vote.
Zero and unobserved categories provide no exclusion. A missing/unconfirmed bridge cannot eliminate a design.
Candidate alternatives, qualifiers, scope and time remain in their structured propositions. WHO PS is not ECOG.
Internally inconsistent candidates are separately identified. Empty survival is a conflict in this declared
family; a family is not assumed exhaustive of real protocols. Dependent conclusions include the weakest
support used in eliminations. Candidate survival does not certify complete patient eligibility.

## Observed producer-to-consumer path

CLI `main -> _reason` and MCP `reason -> _reason` both consume `layer2.run`. Its operation dispatch calls
`service._design_bounds -> design_bounds.bound_designs`. Each candidate/observation calls scoped `entail.decide`,
then `witness_support -> witness_verdict -> candidate_state`. Candidate survival feeds `common_result`, which
consumes the query decisions for all surviving designs. Serialized results expose candidate proofs, blockers,
source/bridge references, remaining alternatives and common consequence. Focused discovery, MCP's advertised
enum, CLI help, README, AGENTS and SKILL route this result into the assistant's decision list and revision loop.
No automatic design-session manager is claimed.

Serena references established both public callers of `layer2.run`, the dispatch to the new adapter and its
call to the core. A real CLI runtime trace on the retained IPASS example observed one core composition,
six witness-support/verdict/candidate reductions, twelve scoped entailment calls and one common-consequence
reduction. The exact request/result and full trace were retained locally under
`/var/folders/y3/9hy3l65d7xvdl89kh19dnlf40000gp/T/trialledger-witness-trace-fvlhi5w2/`.
This is execution evidence for that workload, not a performance improvement claim.

## Intent, boundaries and actual evidence

The authored integration test removes a candidate using a positive witness and observes the common query
change to ENTAILED/interpolated. Raising the exception allowance restores that candidate and changes the query
back to UNDETERMINED. This checks consumption of the signal, not merely helper output. A common negative
consequence also retains interpolated standing. Known bridges/observations permit known deductions;
proposed inputs and unresolved bindings do not.

The retained IPASS response is documented in `tests/fixtures/ipass-registry.md`. Its WHO PS 2 total is
126/1,217. Tests use exact report addresses and explicit test bindings, without a title classifier or
cross-module group join. The declared cutoff family retains upper 2, 3, 4 and no restriction, ruling out upper
0 and 1 only under its test bridge. An allowance of 126 restores all six candidates; 125 still leaves a
witness. The exact cutoff remains unresolved. Both CLI and MCP tests preserve the saved record and workbook
byte-for-byte; reporting's fresh-interpreter import guard now explicitly forbids all of `TrialLedger.layer2`.
IPASS informed this rule and is development evidence, not independent validation.

Authored tests cover null/malformed fields, bool/string/negative/out-of-range counts, empty denominators,
unknown fields, duplicate ids, unsupported queries, per-call and aggregate computation limits, proposed and
conflicting bindings, scale/unit/time/cohort differences, conditional applicability, disjunctions, overlapping
observations, inconsistent candidates, no survivors and revision. Existing real CLI/stdio MCP discovery tests
now execute the new example with network forbidden and reporting files unchanged.

## Detective receipts

Detective and Wesker resolved from the founder's local checkouts under the project's own environment.
`detective --help -> regime` found a clean regime. Each primitive was converged with `--two-sign` and its
complete printed protocol followed through plan/decompose/survey. Each decomposition reported no separable
block. The composition's five-argument interface received an attributed style LEAVE judgment; it is not a
behavior certificate. Object-bound composition and request adapters are covered by authored integration
tests, not claimed as mutation-complete.

| Pure decision | Two-sign converge |
|---|---|
| witness_support | COMPLETE, 58/58 killed |
| witness_verdict | COMPLETE, 106/106 killed |
| candidate_state | COMPLETE, 57/57 killed |
| common_result | COMPLETE, 89/89 killed |

Every converge confirmed reproducibility. No equivalence flag or fence was used. All distinguishing tests
were already authored, so these converges wrote no new characterization suites. Durable function digests and
standing are in `tests/detective/certificates.json`; full local reports are `.detective/reports/`.

The ordinary gate passed 3,650 tests with ten opt-in live tests deselected, Ruff, formatting and package typing
(`/tmp/trialledger-witness-standard.log`). OpenSpec strict validation passed. The initial gate correctly
declined to stamp the tree because proof/docs changed during its run; the stable-tree rerun is recorded below.

## Residual and resource disposition

The existing project-wide deep-audit waiver and older pin limitations remain as recorded in the 2026-11-02
acceptance documents; they are not promoted to passes. The four new pure decisions have their own fresh pins.
This capability does not complete general table interpretation, source compilation, default-stratum conflict
suspension, protocol writing or the broader open synthesis tasks. Bridge correctness remains an explicit
source/user-premise obligation. Derived bounds do not enter corpus statement counts automatically.

Runtime work is bounded by candidates * (observations + 1) solver calls (at most 1,000), each with the declared
assignment cap (at most 65,536). No distributions are expanded into individual participants. The IPASS trace
observed twelve calls for six designs and one observation. Paired speed/memory improvement is UNMEASURED:
this adds a new answer rather than optimizing an incumbent. No efficiency gain is claimed.

## Final validation

A fresh `audit --two-sign --check` of witness_support reported complete, 58/58 value-pinned, and prescribed
converge. That reconverge confirmed COMPLETE, 58/58 killed, reproducibly, followed by plan/decompose/survey
as printed. Authored tests were retained: the function-local minimal cover does not supersede their named
binding and boundary obligations. The other three decisions retain their fresh complete converges above.

A wheel was built from the changed tree and installed in an isolated Python 3.12.12 environment at
`/tmp/trialledger-witness-install.KNderR/`. All 51 Python package files matched the checkout byte-for-byte.
The installed CLI's complete IPASS response matched the checkout's response exactly. This is a changed-tree
installation check, not a published release or a claim that the old build-commit stamp identifies these edits.

After adding the explicit different-unit counterexample and refining blocker-specific answer guidance,
the focused suite passed all 76 tests. Final review then identified duplicate typed-assertion, entry-context
and resource-limit validation in the old/new service paths. Both now consume shared `_scoped_assertions`,
`_reason_context` and `_assignment_bound` helpers. After that consolidation, all 165 focused operation,
entry-point, guide and navigation tests passed, as did Ruff and package typing. The isolated installation was
rebuilt and again matched all 51 source files and the complete CLI response.

The final stable-code ordinary gate passed **3,651 tests**, with ten opt-in live tests deselected, Ruff,
formatting and package typing clean. Its full output is `/tmp/trialledger-witness-stable-gate.log`; it stamped
tree `ad183b1bf6e860db5318e6504a8a2ec614b2921d`. Only this receipt and the task completion marker were updated
afterward. Task 4b is complete; the broader synthesis change remains 6/16 tasks complete, with the other ten
integration tasks open. No archive or release was performed.
