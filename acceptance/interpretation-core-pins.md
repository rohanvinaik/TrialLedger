# Competing interpretations: core verification

Scope: `TrialLedger/layer2/interpretations.py` and the authored intent suite
`tests/test_interpretations.py`. Public translation/discovery, installed entry points, full-project gates
and population/definition-binding decisions have separate owners and receipts.

## Observed behavior

The core reuses `entail.decide` for participant logic and `signals.evaluate` for mathematical checks.
`resolve` constructs private hypothetical environments, retains original proposed assertions/support,
checks each frame independently and computes declared-family consequences without claiming exhaustiveness.
Fixed-floor answers remain independently available. Proposed, partial or unresolved fixed premises cannot
produce an accepted fixed-rule refutation.

Binding standing and source references reach each dependent calculation/check. A bad application preserves
the calculation but blocks its admission. A joint signal claim supplies a hypothetical completion: its
check governs the frame while the uncompleted source calculation remains visible as `baseline_context`.
An observed-only prerequisite is not satisfied by imputation. Selection cannot admit a refuted frame.

On CPython 3.14.7 the scoped authored suite returned **21 passed**. The obligations include competing
proposed readings, ordinary entailment's unchanged proposal refusal, intrinsic versus fixed-floor
contradiction, interpolated exclusion support, partial/unresolved/conflicting scope, source preservation,
binding-gated arithmetic, conditional completion, joint claims, unsupported queries, computation limits,
selection, duplicates and an independent finite-Boolean-world compatibility oracle.

Commands observed:

```sh
.venv/bin/python -m pytest tests/test_interpretations.py
.venv/bin/ruff check TrialLedger/layer2/interpretations.py tests/test_interpretations.py
.venv/bin/ruff format --check TrialLedger/layer2/interpretations.py tests/test_interpretations.py
uvx ty check --python .venv TrialLedger/layer2/interpretations.py
```

The scoped Ruff, format and type checks passed after the final PEP 316 postconditions were added.
The postconditions describe the named output vocabularies, floor-conflict precedence, the compatible
boundary and admissible selection. The integration pass ran CrossHair in a fresh uv overlay with
`--report_all --per_condition_timeout=2`; its complete output was read from
`/tmp/trialledger-interpretations-crosshair.log`. All eight `compatibility_state` conditions reported
**Confirmed over all paths**. All seven `selection_state` conditions reported **Not confirmed**:
neither a violation nor a proof. The full-project gate is owned by the integration pass and is not
claimed by this scoped receipt.

## Detective two-sign observations

The current project environment imported Detective and Wesker from the founder's local checkouts:
`/Users/rohanvinaik/tools/Detective/Detective/__init__.py` and
`/Users/rohanvinaik/tools/Wesker/Wesker/__init__.py`. Full help was read, `detective regime` reported a clean
flat testing regime, and each new decision was converged with explicit `--two-sign`. The runs were
serialized after the binding agent released the shared slot. Their authored intent tests call the pure
decisions directly.

| Target | Scored / killed | Value-pinned | Residual | Policy |
|---|---:|---:|---|---|
| `compatibility_state` | 56 / 56 | 56 / 56 | None reported | `9+neg.f5a15364c11d` |
| `selection_state` | 70 / 70 | 69 / 70 | One crash-only value gap; no unproven-equivalence classification | `9+neg.f5a15364c11d` |

Both convergence walks reported fresh isolated reproducibility confirmation. Their final blocks:

```text
FINAL TrialLedger/layer2/interpretations.py::compatibility_state: ✓ COMPLETE (operator universe) · 56/56 killed · minimal cover 1 test(s) · policy 9+neg.f5a15364c11d

FINAL TrialLedger/layer2/interpretations.py::selection_state: ✓ COMPLETE (operator universe · modulo 1 crash-only value gap) · 70/70 killed · 2 test(s) → tests/detective/test_TrialLedger_layer2_interpretations_selection_state_acfea8a392_synth.py · policy 9+neg.f5a15364c11d
```

The selection report names `BOUNDARY_f075c95c`: replacing `if selected not in states:` with `if False:`.
The tool's distinction is retained verbatim:

```text
What remains differs from your function only by a CRASH: an input
distinguishes each (the mutant raises where your function returns), so
none is an equivalence candidate and nothing is offered to `flag` — no
value assertion can pin a raise. They are detected, not equivalent.
```

The tool generated and minimized its own suite to two tests in
`tests/detective/test_TrialLedger_layer2_interpretations_selection_state_acfea8a392_synth.py`.
It was not hand-edited. No authored test was deleted, no equivalence flag was invented, and no proposed
redundant-test removal was accepted.

The prescribed plan → decompose → survey chains were followed for both targets. Both decompositions ended
`DONE: no separable block. There is no seam here to split.` No source rewrite was applied. The selection
decomposition additionally reported that its crash-only residual blocks automatic application.

The module plan was advisory: zero funded regions, one constructive-but-unpinned `resolve` region, seven
ambiguous and seven silent. This is not module-wide style clearance. The survey named `_assume_assertions`
and `_assume_signal`; the prescribed extraction reads each returned **unresolved input interface**, named
the typed inputs and `dataclasses` dependency, and provided no complete extraction signature. Those
advisory residuals remain unimplemented; the source and authored tests stayed frozen throughout the pin walk.

Complete local logs were read without filtering:

- `/tmp/interpretation-compatibility-converge.log`
- `/tmp/interpretation-core-plan.log`
- `/tmp/interpretation-compatibility-decompose.log`
- `/tmp/interpretation-core-survey.log`
- `/tmp/interpretation-assumption-extract.log`
- `/tmp/interpretation-signal-extract.log`
- `/tmp/interpretation-selection-converge.log`
- `/tmp/interpretation-selection-plan.log`
- `/tmp/interpretation-selection-decompose.log`
- `/tmp/interpretation-selection-survey.log`
- `/tmp/interpretation-selection-assumptions-extract.log`
- `/tmp/interpretation-selection-signal-extract.log`

Static reports are at `.detective/reports/converge_compatibility_state.txt` and
`.detective/reports/converge_selection_state.txt`. Existing accepted limitations from earlier waves were
not reopened or relabelled. These observations concern the two named functions and their declared
operator universe; they do not certify clinical premise truth or every orchestration function.

## Resource boundary

This is an intentional representational/behavior addition. No paired performance improvement is claimed.
Runtime and memory payoff are **UNMEASURED**.
