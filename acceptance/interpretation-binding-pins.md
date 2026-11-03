# Interpretation binding verification — 2026-11-03

Scope: `TrialLedger/layer2/interpretation_bindings.py` and authored
`tests/test_interpretation_bindings.py`. The interpretation engine is the production consumer;
the root integration receipt owns public CLI/MCP and complete-system verification.

## Behavior and boundary

The module parses explicit source-bound population/definition bindings and checks a declared use against
the exact study, population, arm, time and version. Population relations bind only their corresponding
subset/overlap/partition operator identities; an adopted definition binds the named rule edition.
Unresolved scope or operator disagreement is an unresolved application, not proof of an impossible trial.
Resolved proposed and interpolated bindings remain conditional within an interpretation; known resolved
bindings are supported. Checking never rewrites source or signal data.

Authored intent checks cover unknown/null/empty/malformed/oversize inputs, duplicate identities and uses,
all scope axes, reversed population subjects, missing partition exhaustiveness/disjointness, exact rule
edition/adoption, conditional standing, source preservation and observed versus imputed input preservation.
The initial scoped pytest run returned **45 passed**. The final scoped run, including the retained
Detective scope characterization, returned **46 passed**. Scoped Ruff check, Ruff format check and advisory
`ty` passed after the walks.
These checks establish the declared boundary; they do not independently certify a clinical source reading.

## Detective

Local resolution was observed under the project's `.venv`: Detective and Wesker imported from
`/Users/rohanvinaik/tools/Detective` and `/Users/rohanvinaik/tools/Wesker`. The regime resolved cleanly.
All pin invocations explicitly used `--two-sign`; the reported policy is `9+neg.f5a15364c11d`.

| Target | Current observation | Certificate boundary |
|---|---|---|
| `binding_standing` | `COMPLETE`, 39/39 killed; isolated observation reproduced | Full two-sign operator universe |
| `scope_compatibility` | Stable rerun: `COMPLETE (operator universe · modulo 6 unproven-equivalent)`; isolated observation reproduced | Full two-sign policy, with six survivors **not proved equivalent** |
| `population_compatibility` | `COMPLETE (operator universe · modulo 11 unproven-equivalent)`; isolated observation reproduced | 165/176 value-pinned; 170/176 killed; eleven survivors not proved equivalent |
| `definition_compatibility` | `COMPLETE (operator universe · modulo 19 unproven-equivalent · 1 crash-only value gap)`; isolated observation reproduced | 105/125 value-pinned; 116/125 killed; no equivalence proof for the nineteen |

Every target's printed style chain ran: `plan` was advisory with zero funded changes;
`decompose --apply --two-sign` returned **DONE: no separable block**; `survey` found zero trapped pure
decisions. No source rewrite occurred. The plan named unpinned parser/adapter regions and ambiguous
style regions; it did not certify them. No style cleanliness or behavior certificate is claimed for them.

The scope run wrote one generated characterization:
`tests/detective/test_TrialLedger_layer2_interpretation_bindings_scope_compatibility_2cbb1adadb_synth.py`.
It remains tool-owned and unedited. Its run stopped with:

> STOP: the function or test basis changed between the two measurements

Printed repair: keep the proof basis fixed and rerun only once that cause is resolved. Root confirmed
other agents were still writing test files and instructed all further binding pins to wait for a shared
source/test freeze. After root confirmed the global freeze, the prescribed rerun reproduced. No generic
budget retry or source edit was used to work around the stop.

The stable scope report distinguishes **60/66 value-pinned** from **65/66 killed**. Its final verdict is
`COMPLETE (operator universe · modulo 6 unproven-equivalent)`. Both counts and the unproven status are retained;
neither a universal equivalence proof nor a 66/66 value pin is claimed. Root directed the agent to retain
this residual and continue only the printed next actions, without grinding the six or altering source.

The stable population report similarly distinguishes **165/176 value-pinned** from **170/176 killed**,
with eleven candidate-equivalent survivors left **UNPROVEN**. Its isolated observation reproduced.
Detective wrote three generated tests during its search, then removed those same three as redundant during
its own minimization. No authored test was removed or changed. No equivalence flags were recorded.

The definition report distinguishes **105/125 value-pinned** from **116/125 killed**, with nineteen
candidate-equivalent survivors **UNPROVEN** and one **crash-only value gap**. The report explicitly says
the crash-only mutation is detected by the suite and is not an equivalence candidate. Its isolated
observation reproduced. Detective wrote two generated tests and removed those same two during its own
minimization. No authored test or source was edited after the shared freeze.

After the last prescribed survey completed, the serialized Detective slot was released to the core agent.
All four walks completed under the explicit full two-sign policy, with the exact residuals above; this
does not claim four residual-free value pins or universal equivalence. Parsing/dataclass adapters retain
ordinary authored boundary-test coverage and are not described as mutation-pinned.

Full logs: `/tmp/interpretation-binding-standing-pin.log`, `/tmp/interpretation-binding-plan.log`,
`/tmp/interpretation-binding-decompose.log`, `/tmp/interpretation-binding-survey.log`,
`/tmp/interpretation-binding-scope-pin.log`, `/tmp/interpretation-binding-scope-stable-pin.log`,
`/tmp/interpretation-binding-scope-plan.log`, `/tmp/interpretation-binding-scope-decompose.log`.
Population logs: `/tmp/interpretation-binding-population-pin.log`,
`/tmp/interpretation-binding-population-plan.log`, `/tmp/interpretation-binding-population-decompose.log`.
Definition logs: `/tmp/interpretation-binding-definition-pin.log`,
`/tmp/interpretation-binding-definition-plan.log`, `/tmp/interpretation-binding-definition-decompose.log`.
The corresponding static reports are under
`.detective/reports/`. This receipt must be updated with any subsequent stable-basis observations.

Resource disposition: **UNMEASURED**; no performance improvement is claimed. Literal-typed decision pins
are separate from authored tests of parsing and dataclass adapters and from the root's integration checks.
