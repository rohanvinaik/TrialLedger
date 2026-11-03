# Numerical partial-evidence pin receipts

Recorded 2026-11-03 for the six pure numerical targets in
`TrialLedger/layer2/numeric_evidence.py`. This is a factual record of the serialized
Detective walk, not acceptance of clinical source premises or a whole-system proof.
The initial operator-only policy was `9.261d14e34119`. The completed explicit
two-sign rerun used `9+neg.f5a15364c11d`.

## Completed explicit two-sign rerun

After the scope correction recorded below, the coordinator froze source, tests,
and examples again and assigned an exclusive Detective slot. All six targets
were remeasured with explicit `--two-sign`; all printed decomposition follow-ups
retained `--two-sign`. Complete live stdout/stderr was read for each command.
The results here come from that rerun, not the earlier operator-only reports.

The actual initial convergence argv, under the standing `PYTHONPATH` and
owned-process wrapper documented below, were:

```sh
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::interval_state' --two-sign
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::overlap_bounds' --two-sign
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::partition_bounds' --two-sign
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::summary_bounds' --two-sign
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::summary_count_state' --two-sign
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::scope_state' --two-sign
```

Partition's initial full-scope convergence reached its aggregate deadline during
minimization and returned exit 3. Its literal final line was:

```text
FINAL TrialLedger/layer2/numeric_evidence.py::partition_bounds: ⚠ CUT — aggregate deadline exhausted during minimization; measurement partial, re-run with a larger --deadline · policy 9+neg.f5a15364c11d
```

Its diagnostic `30 behaviours · 26 pinned` was not treated as certified. The
printed repair named `--deadline 900`, or 0 to disable the limit. The same target
was rerun with the explicitly prescribed larger wall:

```sh
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::partition_bounds' --two-sign --deadline 900
```

That rerun reproduced successfully and printed the COMPLETE verdict below.
Its subsequent decomposition used the exact printed `--apply --two-sign`
command, with no invented deadline flag, and also completed successfully.
The CUT report path was overwritten by the successful run; the CUT line above
is retained from the complete original command output.

| Target | Full-policy universe | Killed | Value-pinned | Crash-only detected | Proof-backed equivalents | Unproven equivalents |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `interval_state` | 18 | 18 | 18 | 0 | 0 | 0 |
| `overlap_bounds` | 26 | 25 | 25 | 0 | 1 | 0 |
| `partition_bounds` | 30 | 26 | 26 | 0 | 4 | 0 |
| `summary_bounds` | 72 | 70 | 68 | 2 | 2 | 0 |
| `summary_count_state` | 65 | 65 | 64 | 1 | 0 | 0 |
| `scope_state` | 43 | 43 | 43 | 0 | 0 | 0 |

The literal final convergence verdicts were:

```text
FINAL TrialLedger/layer2/numeric_evidence.py::interval_state: ✓ COMPLETE (operator universe) · 18/18 killed · minimal cover 2 test(s) · policy 9+neg.f5a15364c11d

FINAL TrialLedger/layer2/numeric_evidence.py::overlap_bounds: ✓ COMPLETE (operator universe) · 25/26 killed · minimal cover 4 test(s) · policy 9+neg.f5a15364c11d

FINAL TrialLedger/layer2/numeric_evidence.py::partition_bounds: ✓ COMPLETE (operator universe) · 26/30 killed · 1 test(s) → tests/detective/test_TrialLedger_layer2_numeric_evidence_partition_bounds_0febd21c7e_synth.py · policy 9+neg.f5a15364c11d

FINAL TrialLedger/layer2/numeric_evidence.py::summary_bounds: ✓ COMPLETE (operator universe · modulo 2 crash-only value gaps) · 70/72 killed · 1 test(s) → tests/detective/test_TrialLedger_layer2_numeric_evidence_summary_bounds_5df2752181_synth.py · policy 9+neg.f5a15364c11d

FINAL TrialLedger/layer2/numeric_evidence.py::summary_count_state: ✓ COMPLETE (operator universe · modulo 1 crash-only value gap) · 65/65 killed · 1 test(s) → tests/detective/test_TrialLedger_layer2_numeric_evidence_summary_count_state_882556c136_synth.py · policy 9+neg.f5a15364c11d

FINAL TrialLedger/layer2/numeric_evidence.py::scope_state: ✓ COMPLETE (operator universe) · 43/43 killed · minimal cover 3 test(s) · policy 9+neg.f5a15364c11d
```

The tool's literal phrase `operator universe` is retained here. Full scope is
established by the explicit argv, the widened denominators, and the printed
`9+neg.f5a15364c11d` policy, rather than by silently changing that phrase.
The old and new counts are distinct measurements. In particular, the two
historical partition crash-only gaps were not reported as crash-only in the
completed full-policy run, which reported 26 pinned behaviours out of 30.

All six scoped decompositions reproduced their proof basis and terminated
`DONE: no separable block. There is no seam here to split.` No rewrite was
applied. The summary and summary-count decompositions stated that crash-only
survivors blocked automatic application before reporting no separable block;
those crash detections were not flagged equivalent. Module plans remained
advisory with zero funded regions, and module surveys reported zero traps.
No authored-test cleanup was performed. The Detective slot was returned idle
after all six terminal chains.

### Additional full-policy equivalence proofs

The five prior overlap/partition flags below were retained by the widened walk.
Full scope additionally exposed two OUTPUT candidates in `summary_bounds`.
They were proved and flagged using the exact printed `--two-sign` commands.
The exact notes supplied were:

- `OUTPUT_ec9181c1`:

  > The mutated return is the reversal of the two-element tuple (total,total). Both entries are the same integer, so reversal yields exactly (total,total), with identical type and value. No condition, arithmetic, iteration or source binding changes.

- `OUTPUT_b90df554`:

  > Let v=(total,total). Then v[1:2]=(total,), v[:1]=(total,), and v[2:]=(). Their concatenation is exactly (total,total). The lambda therefore returns the identical two-integer tuple; conditions, preceding arithmetic and exceptions are unchanged.

Both flags printed `recorded equivalent`, tied to the exact source, and
prescribed `audit <target> --two-sign`. Those audits prescribed another
`converge <target> --two-sign`, which was executed. The final scoped audit
reported `68/72 value-pinned`, `flagged equivalent 2 (your oracle — not gaps)`,
and `complete, modulo 2 crash-only value gaps`. The final scoped convergence
and decomposition followed; no unproven equivalent remained.

Reapply these two additional notes under the standing environment:

```sh
cd /Users/rohanvinaik/tools/TrialLedger
export PP=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-summary-two-sign-flag-reverse -- .venv/bin/detective flag 'TrialLedger/layer2/numeric_evidence.py::summary_bounds' OUTPUT_ec9181c1 --two-sign --note 'The mutated return is the reversal of the two-element tuple (total,total). Both entries are the same integer, so reversal yields exactly (total,total), with identical type and value. No condition, arithmetic, iteration or source binding changes.'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-summary-two-sign-audit -- .venv/bin/detective audit 'TrialLedger/layer2/numeric_evidence.py::summary_bounds' --two-sign

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-summary-two-sign-flag-rotate -- .venv/bin/detective flag 'TrialLedger/layer2/numeric_evidence.py::summary_bounds' OUTPUT_b90df554 --two-sign --note 'Let v=(total,total). Then v[1:2]=(total,), v[:1]=(total,), and v[2:]=(). Their concatenation is exactly (total,total). The lambda therefore returns the identical two-integer tuple; conditions, preceding arithmetic and exceptions are unchanged.'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-summary-two-sign-audit -- .venv/bin/detective audit 'TrialLedger/layer2/numeric_evidence.py::summary_bounds' --two-sign
```

Follow each complete current output, including a prescribed convergence before
the next action. For a fresh full-policy measurement use the six initial argv
above under `PYTHONPATH="$PP"` and `owned-run`; preserve `--two-sign` on every
measurement follow-up. The historical commands below intentionally preserve
their original operator-only argv and must not be used to claim full scope.

## Historical scope correction before the explicit rerun

The initial runs below measured the **operator universe only**. None of the six
`converge` commands explicitly included `--two-sign`. The subsequent numerical
`decompose --apply`, `audit`, and `flag` commands also omitted that option.
Consequently, those results did **not** establish the user's required full
two-sign coverage. At that checkpoint the scope was **unverified for all six
targets**. The completed explicit rerun above closes that outstanding scope
without relabeling the historical results.

The actual convergence argv, excluding the already documented environment and
owned-process wrapper, were:

```sh
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::interval_state'
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::overlap_bounds'
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::partition_bounds'
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::summary_bounds'
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::summary_count_state'
.venv/bin/detective converge 'TrialLedger/layer2/numeric_evidence.py::scope_state'
```

No earlier numerical two-sign measurement is claimed, and there is no numerical
two-sign report in this walk that a later operator-only decomposition could have
preserved. The counts, literal operator verdicts, and five equivalence notes below
are retained as actually measured; they must not be relabeled as two-sign
results. This correction changes the claimed verification scope, not those
historical measurements.

## Environment and walk

The target project's `.venv` ran Detective with the local Detective and Wesker
checkouts supplied through `PYTHONPATH`. The resolution check printed:

```text
Detective -> /Users/rohanvinaik/tools/Detective/Detective/__init__.py
Wesker -> /Users/rohanvinaik/tools/Wesker/Wesker/__init__.py
```

`detective --help` was followed by `detective regime`. Regime printed:

```text
DONE:  this regime resolves cleanly — nothing to migrate. Run `detective audit`,
       `converge`, or `decompose` on a target in it.
```

Each target's convergence was followed by the printed module plan, target
`decompose --apply`, and module survey. Each decomposition terminated with:

```text
DONE:  no separable block. There is no seam here to split.
```

The module surveys reported `0 trapped pure decisions`, with the qualification
that unresolved types and ambiguous uses are not proved input-reachable. The
style plans were advisory and funded zero regions. No source rewrite was applied.

## Changed-basis refusal and stable rerun

The initial `interval_state` run returned exit 3. Its literal final verdict was:

```text
FINAL TrialLedger/layer2/numeric_evidence.py::interval_state: ⚠ UNGATEABLE — the function or test basis changed between the two measurements; diagnostic counts; no certified bound or verdict established · policy 9.261d14e34119
```

Its printed repair was to keep the proof basis fixed and rerun only once that
cause was resolved. Work paused while integration edits were completed. The
coordinator then froze source and tests, and the same target was rerun. Detective
printed `reproducibility confirmed — the certificate rests on the isolated
observation`, followed by the successful literal verdict below. The refusal was
not treated as a successful measurement. Its static report path was reused by
the successful run; the refusal text above is retained from the original command
output, not presented as the current contents of that report.

The walk paused again after the completed interval target while the coordinator
repaired an unrelated contract docstring. Remaining targets started only after
the coordinator declared source and tests frozen again. Detective runs were
serialized; no other agent ran Detective concurrently.

## Historical operator-only counts and terminal standing

“Killed” includes both value assertions and crash detection. Crash-only mutants
are detected, not proved equivalent, and are not relabeled as value-pinned.
Equivalence flags are authored mathematical oracles tied to the exact source,
not mutation kills. The table records the final operator-only numerical walk,
including the later flags and audits of overlap and partition. Its terminal
standings closed only that historical measured scope. The completed explicit
two-sign results are reported separately above.

| Target | Killed / operator universe | Value-pinned | Crash-only detections | Proof-backed equivalents | Unproven equivalents after flags | Terminal standing |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `interval_state` | 8/8 | 8 | 0 | 0 | 0 | `✓ COMPLETE (operator universe)` |
| `overlap_bounds` | 14/15 | 14 | 0 | 1 | 0 | Final audit: `complete` |
| `partition_bounds` | 15/19 | 13 | 2 | 4 | 0 | Final audit: `complete, modulo 2 crash-only value gaps` |
| `summary_bounds` | 41/41 | 39 | 2 | 0 | 0 | `✓ COMPLETE (operator universe · modulo 2 crash-only value gaps)` |
| `summary_count_state` | 37/37 | 36 | 1 | 0 | 0 | `✓ COMPLETE (operator universe · modulo 1 crash-only value gap)` |
| `scope_state` | 15/15 | 15 | 0 | 0 | 0 | `✓ COMPLETE (operator universe)` |

The original complete convergence reports printed these literal final lines.
Their paths have since been reused by the explicit rerun. The historical overlap
and partition convergence results preceded their proof-backed flags; their
original modulo/unproven wording is preserved here rather than rewritten.

```text
FINAL TrialLedger/layer2/numeric_evidence.py::interval_state: ✓ COMPLETE (operator universe) · 8/8 killed · minimal cover 2 test(s) · policy 9.261d14e34119

FINAL TrialLedger/layer2/numeric_evidence.py::overlap_bounds: ✓ COMPLETE (operator universe · modulo 1 unproven-equivalent) · 14/15 killed · 1 test(s) → tests/detective/test_TrialLedger_layer2_numeric_evidence_overlap_bounds_ebf65ff194_synth.py · policy 9.261d14e34119

FINAL TrialLedger/layer2/numeric_evidence.py::partition_bounds: ✓ COMPLETE (operator universe · modulo 4 unproven-equivalent · 2 crash-only value gaps) · 15/19 killed · 2 test(s) → tests/detective/test_TrialLedger_layer2_numeric_evidence_partition_bounds_0febd21c7e_synth.py · policy 9.261d14e34119

FINAL TrialLedger/layer2/numeric_evidence.py::summary_bounds: ✓ COMPLETE (operator universe · modulo 2 crash-only value gaps) · 41/41 killed · 1 test(s) → tests/detective/test_TrialLedger_layer2_numeric_evidence_summary_bounds_5df2752181_synth.py · policy 9.261d14e34119

FINAL TrialLedger/layer2/numeric_evidence.py::summary_count_state: ✓ COMPLETE (operator universe · modulo 1 crash-only value gap) · 37/37 killed · 1 test(s) → tests/detective/test_TrialLedger_layer2_numeric_evidence_summary_count_state_882556c136_synth.py · policy 9.261d14e34119

FINAL TrialLedger/layer2/numeric_evidence.py::scope_state: ✓ COMPLETE (operator universe) · 15/15 killed · minimal cover 3 test(s) · policy 9.261d14e34119
```

After flags, overlap's audit printed `14/15 value-pinned`, `complete`, and
`flagged equivalent 1 (your oracle — not gaps)`. Partition's final audit printed
`13/19 value-pinned`, `complete, modulo 2 crash-only value gaps`, and
`flagged equivalent 4 (your oracle — not gaps)`. These audit results were read
from their complete command outputs; no `audit_overlap_bounds.txt` or
`audit_partition_bounds.txt` static file existed at the queried report paths.

The identified crash-only mutants were:

| Target | Mutant | Distinction reported by Detective |
| --- | --- | --- |
| `partition_bounds` | `SWAP_e2e1feff` | Replaces `sum(lowers)` with the list `lowers`; mutant raises where the original returns. |
| `partition_bounds` | `SWAP_957aa1a9` | Replaces the second pair iteration with iteration over `lowers`; mutant raises where the original returns. |
| `summary_bounds` | `VALUE_45a6805a` | Replaces remainder divisor 2 with 0. |
| `summary_bounds` | `VALUE_4ebece43` | Replaces floor-division divisor 2 with 0. |
| `summary_count_state` | `VALUE_b6ac0d06` | Replaces remainder divisor 2 with 0. |

Detective explicitly stated that these have distinguishing inputs, are already
detected by crash, and are not equivalence candidates: nothing to flag for them.

## Five exact equivalence notes

These are the exact notes supplied to the printed `detective flag` commands.
They rely on the primitives' declared integer/list contracts, not clinical text
or a matching denominator. Each flag printed `recorded equivalent`, then:

```text
keyed to this exact code — an edit un-flags it.

DONE:  future audit/converge runs treat it as equivalent — unless a witness
       is found, which outranks your flag. Proof beats judgement.
```

1. `overlap_bounds` — `SWAP_4dc6f66f`:

   > For the declared integer inputs E=sum(lowers)-(len(lowers)-1)*total is an integer. max(0,E)=max(E,0) by integer order, including the tie E=0. The unchanged min(uppers) result and exceptions are identical; all preceding operations are unchanged.

2. `partition_bounds` — `SWAP_aadfdac7`:

   > For integer inputs low and total-high_sum+high are integers. max(low,total-high_sum+high)=max(total-high_sum+high,low) by total integer order, including ties. All iteration, other operations, returned values and exceptions are unchanged.

3. `partition_bounds` — `SWAP_68f006a1`:

   > For integer inputs high and total-low_sum+low are integers. min(high,total-low_sum+low)=min(total-low_sum+low,high) by total integer order, including ties. All iteration, other operations, returned values and exceptions are unchanged.

4. `partition_bounds` — `VALUE_dd770196`:

   > The contract requires equal lengths of the two integer lists, so strict=True and strict=False yield identical pairs. Even outside that length precondition, the second comprehension keeps strict=True and raises the same zip length ValueError before any result returns. The first comprehension is pure integer arithmetic with no externally visible effects.

5. `partition_bounds` — `VALUE_029325d5`:

   > The contract requires equal lengths of the two integer lists, so strict=True and strict=False yield identical pairs. For unequal lengths the unchanged first comprehension raises the same strict zip ValueError before the mutated second comprehension is reached. Therefore the return values and exceptions are unchanged.

The flag outputs did not print a storage path. Local flags are held in ignored
`.detective/equivalents.json`; this receipt preserves the notes and reapplication
commands without changing that storage policy or committing unrelated flags.

## Reapplication commands

Run from the same checkout and project environment. First prove local resolution
again; an environment or source change requires a fresh tool verdict rather than
reuse of this receipt as a current measurement. These commands persist the exact
notes above; they do not replace the prescribed audit following each flag.
The commands reproduce the historical operator-only flag/audit walk and do not
provide the explicit two-sign verification reported separately above.

```sh
cd /Users/rohanvinaik/tools/TrialLedger
export PP=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker

PYTHONPATH="$PP" .venv/bin/python -c "import Detective, Wesker; print('Detective ->', Detective.__file__); print('Wesker ->', Wesker.__file__)"

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-overlap-flag -- .venv/bin/detective flag 'TrialLedger/layer2/numeric_evidence.py::overlap_bounds' SWAP_4dc6f66f --note 'For the declared integer inputs E=sum(lowers)-(len(lowers)-1)*total is an integer. max(0,E)=max(E,0) by integer order, including the tie E=0. The unchanged min(uppers) result and exceptions are identical; all preceding operations are unchanged.'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-overlap-audit -- .venv/bin/detective audit 'TrialLedger/layer2/numeric_evidence.py::overlap_bounds'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-partition-flag-max -- .venv/bin/detective flag 'TrialLedger/layer2/numeric_evidence.py::partition_bounds' SWAP_aadfdac7 --note 'For integer inputs low and total-high_sum+high are integers. max(low,total-high_sum+high)=max(total-high_sum+high,low) by total integer order, including ties. All iteration, other operations, returned values and exceptions are unchanged.'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-partition-audit -- .venv/bin/detective audit 'TrialLedger/layer2/numeric_evidence.py::partition_bounds'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-partition-flag-min -- .venv/bin/detective flag 'TrialLedger/layer2/numeric_evidence.py::partition_bounds' SWAP_68f006a1 --note 'For integer inputs high and total-low_sum+low are integers. min(high,total-low_sum+low)=min(total-low_sum+low,high) by total integer order, including ties. All iteration, other operations, returned values and exceptions are unchanged.'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-partition-audit -- .venv/bin/detective audit 'TrialLedger/layer2/numeric_evidence.py::partition_bounds'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-partition-flag-first-zip -- .venv/bin/detective flag 'TrialLedger/layer2/numeric_evidence.py::partition_bounds' VALUE_dd770196 --note 'The contract requires equal lengths of the two integer lists, so strict=True and strict=False yield identical pairs. Even outside that length precondition, the second comprehension keeps strict=True and raises the same zip length ValueError before any result returns. The first comprehension is pure integer arithmetic with no externally visible effects.'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-partition-audit -- .venv/bin/detective audit 'TrialLedger/layer2/numeric_evidence.py::partition_bounds'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-partition-flag-second-zip -- .venv/bin/detective flag 'TrialLedger/layer2/numeric_evidence.py::partition_bounds' VALUE_029325d5 --note 'The contract requires equal lengths of the two integer lists, so strict=True and strict=False yield identical pairs. For unequal lengths the unchanged first comprehension raises the same strict zip ValueError before the mutated second comprehension is reached. Therefore the return values and exceptions are unchanged.'

PYTHONPATH="$PP" /Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label trialledger-numeric-partition-audit -- .venv/bin/detective audit 'TrialLedger/layer2/numeric_evidence.py::partition_bounds'
```

Follow each command's complete current output. This historical recipe does not
authorize ignoring a future refusal, a discovered witness, or the scope decision
below concerning authored-test cleanup.

## Authored tests retained

The overlap and partition audits prescribed `audit <target> --remove` for tests
redundant relative to one target's minimal cover. An overlap removal run had
started when the coordinator explicitly declined authored-test cleanup. It was
interrupted immediately, returning exit 143 after baseline tracing; no removal
was printed. A complete read of `tests/test_numeric_evidence.py` confirmed all
three named overlap tests remained. No subsequent removal was run.

The coordinator retained the authored tests because finite-population oracles,
population alignment, joint consistency, and unresolved-boundary obligations
serve this feature beyond a single-function minimal mutation cover. This was an
explicit task-scope instruction overriding cleanup, not a claim that Detective
had failed. Generated suites were written/minimized by Detective itself; no
generated suite was hand-edited.

## Report and generated-test paths

Paths below are relative to `/Users/rohanvinaik/tools/TrialLedger`. Local reports
can be regenerated or overwritten; the literal results and proof notes above
are preserved here for review.

| Target | Convergence report | Decomposition report |
| --- | --- | --- |
| `interval_state` | `.detective/reports/converge_interval_state.txt` | `.detective/reports/decompose_interval_state.txt` |
| `overlap_bounds` | `.detective/reports/converge_overlap_bounds.txt` | `.detective/reports/decompose_overlap_bounds.txt` |
| `partition_bounds` | `.detective/reports/converge_partition_bounds.txt` | `.detective/reports/decompose_partition_bounds.txt` |
| `summary_bounds` | `.detective/reports/converge_summary_bounds.txt` | `.detective/reports/decompose_summary_bounds.txt` |
| `summary_count_state` | `.detective/reports/converge_summary_count_state.txt` | `.detective/reports/decompose_summary_count_state.txt` |
| `scope_state` | `.detective/reports/converge_scope_state.txt` | `.detective/reports/decompose_scope_state.txt` |

Shared style report:
`.detective/reports/plan_TrialLedger_layer2_numeric_evidence_py.txt`.

Generated tests:

- `tests/detective/test_TrialLedger_layer2_numeric_evidence_overlap_bounds_ebf65ff194_synth.py`
- `tests/detective/test_TrialLedger_layer2_numeric_evidence_partition_bounds_0febd21c7e_synth.py`
- `tests/detective/test_TrialLedger_layer2_numeric_evidence_summary_bounds_5df2752181_synth.py`
- `tests/detective/test_TrialLedger_layer2_numeric_evidence_summary_count_state_882556c136_synth.py`

Detective's candidate-equivalence search is bounded, not an equivalence proof.
The five original proof-backed flags close the historical operator candidates;
the two additional OUTPUT proofs close the new full-policy candidates. These
seven flags are distinguished from killed mutants in the full-policy table.
The numerical witness operators still require their declared typed inputs and
explicit scope/source bindings; these receipts do not establish those premises.
