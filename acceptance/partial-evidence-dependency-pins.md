# Dependency and eligibility witness mutation receipt

The user directed mutation work to stop and authorized proceeding to push. No further convergence,
flagging, audit, planning, decomposition or survey was run after that instruction. This receipt records
the completed observations and the incomplete scope; it does not certify the unstarted targets.

## Environment and boundary

The project environment was `.venv/bin/python` / `.venv/bin/detective`. Import resolution was checked:
Detective resolved inside `/Users/rohanvinaik/tools/Detective/Detective/` and Wesker inside
`/Users/rohanvinaik/tools/Wesker/Wesker/`. Every Detective command used
`PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker` through the source-owned
`/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run` helper. `detective --help` was read first;
`detective regime` then reported a clean flat testing regime and nothing to migrate.

Every initial target convergence explicitly included `--two-sign`. The measured policy was
`9+neg.f5a15364c11d`. The two-sign counts below are the tool's scored universe, not just its smaller
operator-mutant census. Full command outputs and complete convergence reports were read.

Authored intent and integration tests were retained. Proposed single-function minimal-cover removals
were declined. Detective reported writing two sound generated tests for `prerequisite_state` and then
minimizing two of its own redundant tests. No source rewrite was applied. No normal gate, build, commit
or push was performed as part of this subtask.

## Literal standings

| Target | Last convergence standing | Killed / value-pinned | Operator census | Chain standing |
|---|---|---:|---:|---|
| `entail.rejected_outcome` | `✓ COMPLETE (operator universe)` | 75/75; 75/75 | 29 | Converge, plan, two-sign decompose and survey completed |
| `dependency_evidence.alternative_state` | `✓ COMPLETE (operator universe)` | 42/42; 42/42 | 14 | Converge, plan, two-sign decompose and survey completed |
| `dependency_evidence.guard_state` | `✓ COMPLETE (operator universe)` | 42/42; 42/42 | 14 | Converge, plan, two-sign decompose and survey completed |
| `dependency_evidence.prerequisite_state` | `✓ COMPLETE (operator universe · modulo 2 unproven-equivalent)` | 73/75; 73/75 | 29 | Converge completed; equivalence resolution and printed style chain stopped by user |
| `dependency_evidence.condition_join` | No run | Unmeasured | Unmeasured | Unstarted; no mutation certificate from this pass |
| `signals.support_state` | No run | Unmeasured | Unmeasured | Unstarted; no mutation certificate from this pass |

The first four convergence runs reported `every-killable-killed=True`, `line-complete=True`, and
reproducibility confirmed by a fresh isolated observation. The first three had no scored surviving or
value-unspecified mutants. For `prerequisite_state`, both remaining mutants were value-unspecified and
candidate-equivalent, not proven equivalent. Its 73 killed mutants were also 73 value-pinned mutants;
the reported basis gains no extra kills from crash-only differences. The other completed scored
universes were entirely value-pinned rather than only distinguished by crashes.

Dependency runs also reported nine isolation-hazardous tests deferred from the widening search.
Those tests were not represented as observed. The tool's static reachability exclusions were 3,096
tests for `rejected_outcome`, 2,965 for `alternative_state` and `guard_state`, and 2,964 for
`prerequisite_state`. Those counts describe these observations only.

## Unresolved equivalences

The complete `prerequisite_state` report retained these exact candidate-equivalent mutations:

- `OUTPUT_33ebbae3`: `return 'inactive'` becomes `return guard`.
- `OUTPUT_0914943b`: `return 'unresolved'` becomes `return guard`.

The engine reported no distinguishing input in 21 tried, including five additional boundary probes.
That is bounded search, not an equivalence proof. No `flag` command or proof note was applied before
the user stopped the work. Reapplication of an equivalence claim therefore still requires a reviewed
proof and the tool's prescribed commands; the following are pending commands, not completed actions:

```sh
env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective flag 'TrialLedger/layer2/dependency_evidence.py::prerequisite_state' OUTPUT_33ebbae3 --two-sign --note 'REPLACE WITH REVIEWED EQUIVALENCE PROOF'
env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective flag 'TrialLedger/layer2/dependency_evidence.py::prerequisite_state' OUTPUT_0914943b --two-sign --note 'REPLACE WITH REVIEWED EQUIVALENCE PROOF'
```

No other equivalence flags were needed in the measured targets. No pin command printed a refusal or
a no-repair residual in this scope. The user-directed stop, rather than a repair or waiver, ended the
remaining work.

## Executed target commands

These are the exact target command lines, in execution order. The initial reports for the first two
targets were produced before their style follow-ups; those follow-ups were then completed before
starting `guard_state`.

```sh
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-rejected-pin -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective converge 'TrialLedger/layer2/entail.py::rejected_outcome' --two-sign
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-alternative-pin -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective converge 'TrialLedger/layer2/dependency_evidence.py::alternative_state' --two-sign
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-rejected-plan -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective plan 'TrialLedger/layer2/entail.py'
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-rejected-decompose -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective decompose 'TrialLedger/layer2/entail.py::rejected_outcome' --apply --two-sign
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-rejected-survey -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective survey 'TrialLedger/layer2/entail.py'
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-alternative-plan -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective plan 'TrialLedger/layer2/dependency_evidence.py'
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-alternative-decompose -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective decompose 'TrialLedger/layer2/dependency_evidence.py::alternative_state' --apply --two-sign
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-alternative-survey -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective survey 'TrialLedger/layer2/dependency_evidence.py'
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-guard-pin -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective converge 'TrialLedger/layer2/dependency_evidence.py::guard_state' --two-sign
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-guard-plan -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective plan 'TrialLedger/layer2/dependency_evidence.py'
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-guard-decompose -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective decompose 'TrialLedger/layer2/dependency_evidence.py::guard_state' --apply --two-sign
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-guard-survey -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective survey 'TrialLedger/layer2/dependency_evidence.py'
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-prerequisite-pin -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective converge 'TrialLedger/layer2/dependency_evidence.py::prerequisite_state' --two-sign
```

All three completed decomposition commands printed: `DONE: no separable block. There is no seam here
to split.` Plans reported zero funded regions and labeled themselves advisory. The entailment survey
reported one trapped `_literal_formula` decision and explicitly labeled extraction advisory; that
function was outside these six targets. Dependency surveys reported zero trapped pure decisions.
These static readings are not broader behavioral or performance certificates.

## Reports and process cleanup

Complete convergence reports:

- `.detective/reports/converge_rejected_outcome.txt`
- `.detective/reports/converge_alternative_state.txt`
- `.detective/reports/converge_guard_state.txt`
- `.detective/reports/converge_prerequisite_state.txt`

Completed style-chain reports:

- `.detective/reports/plan_TrialLedger_layer2_entail_py.txt`
- `.detective/reports/decompose_rejected_outcome.txt`
- `.detective/reports/plan_TrialLedger_layer2_dependency_evidence_py.txt`
- `.detective/reports/decompose_alternative_state.txt`
- `.detective/reports/decompose_guard_state.txt`

The last Detective helper had already returned before the stop instruction; no active run needed
termination. An independent structured process inventory in the SquishOS environment then checked
every helper label used above and reported `owned_helpers_remaining: []`. The target environment
lacked the optional `psutil` package, so that read-only inventory used SquishOS's existing environment;
no dependency was installed. Source and authored tests remained unchanged during cleanup.
