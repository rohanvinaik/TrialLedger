# Source assertion compiler: scoped verification

This receipt covers `TrialLedger/layer2/source_assertions.py` and its authored
`tests/test_source_assertions.py` tests. Public service, installed CLI/MCP, discovery,
complete project gates and serialized mutation verification belong to the root integration pass.

## Implemented boundary

- Complete canonical nonnegative integer `minimumAge`/`maximumAge` values with NIH plural age units
  produce known registered-general-eligibility constraints under a content-bound named direct rule.
- Missing, null, empty, malformed, N/A and unsupported age values produce named coverage and no bound.
  Other eligibility fields, including free text, sex and healthy-volunteer flags, remain retained and unresolved.
- Verified source locations provide provenance only. Caller assertions, local signal support and
  population/definition bindings become proposed; submitted originals remain separately inspectable.
- Frame and binding templates can hydrate only from their own declared anchor set. Undeclared dependencies
  are refused even when the corresponding anchor is otherwise verified in the same request.
- Rule version is the explicit implementation version `1`; source content identity remains in snapshot
  metadata and exact provenance references. Uncompiled study sections/modules have retained root references.
- Boolean alternatives, conditional applicability, actor, qualifiers, cohort, branch and temporal
  meaning survive. An unresolved derivation remains unresolved after anchoring.
- Empty queries support inspection. Nonempty queries produce directly reusable existing-operation
  requests. The compiler does not call the service or mutate the study.

## Executed checks

On 2026-11-03, after the scoped code/test changes:

```text
uv run pytest tests/test_source_assertions.py
47 passed

uv run ruff check TrialLedger/layer2/source_assertions.py tests/test_source_assertions.py
All checks passed!

ty check TrialLedger/layer2/source_assertions.py tests/test_source_assertions.py
All checks passed!

ty check TrialLedger
All checks passed!
```

The authored tests exercise the retained real IPASS record, structured ages and units, absent and
malformed parents, zero, unsupported numeric/unit syntax, retained sibling fields, exact number-span
hydration, source/output independence, unknown fields, duplicates, fixed-floor injection, bad digests,
inspection-time frame validation, ordinary-entailment refusal of prepared proposals, conditional frame
calculation, unresolved rules/resolution, OR/AND, conditional applicability, nonparticipant actors,
qualified negative literals, cohort/time preservation, proposed signal support and unresolved
population-binding applications.

The review regressions additionally cover undeclared source dependencies in both frames and bindings,
implementation-version/source-digest separation, uncompiled NIH section roots, and aggregate frame,
assumption, binding and repeated-query work budgets. The aggregate checks also apply with no queries.

No network, branch, worktree or commit was used for this scoped implementation. These checks
establish the named representational and admission cases; they do not certify clinical meaning or establish
general clinical extraction accuracy. The pure `age_state` decision carries PEP 316 postconditions for the
serialized verification pass.

## Serialized Detective walk

After the root's functional/authored-test freeze, `age_state` was walked with the project `.venv`
interpreter and local Detective/Wesker checkouts. Import resolution was printed and verified. The complete
help and regime output were read; the regime printed `DONE`, clean, nothing to migrate. The target purpose
was the seven named admission states, not clinical interpretation.

The first `converge ... --full --two-sign` run printed:

> UNGATEABLE — the in-process mutant universe did not reproduce under isolated evaluation — COMPLETE is
> withheld; re-measure with --isolated, preserving the same inputs and tests.

Its prescribed repair was followed exactly with `--isolated`, preserving inputs/tests. The second run printed:

```text
✓ every killable mutant killed + line-complete — 1 crash-only value gap(s)
mutants: 85/85 killed
value: 84/85 pinned
every-killable-killed=True  line-complete=True
FINAL TrialLedger/layer2/source_assertions.py::age_state:
✓ COMPLETE (operator universe · modulo 1 crash-only value gap)
```

The remaining TYPE perturbation raises where the original returns. Detective printed that it is detected
by crash, no input is owed for detection, and it is not an equivalence candidate: nothing to flag. This is
the exact residual, not a proof that every return value is pinned. The report named no further verification
or style action after its final COMPLETE block. Proposed redundant-test removals were not applied.

Tool-owned generated test:
`tests/detective/test_TrialLedger_layer2_source_assertions_age_state_f3d6476ddb_synth.py`
(one test; verified passing by Detective). Canonical full report:
`.detective/reports/converge_age_state.txt`. Full command-capture logs:
`/tmp/trialledger-age-state-help.log`, `/tmp/trialledger-age-state-regime.log`,
`/tmp/trialledger-age-state-converge-help.log`, `/tmp/trialledger-age-state-converge-1.log`,
`/tmp/trialledger-age-state-converge-2.log`. The commands ran through `owned-run`. No source or authored
test was edited during the walk.
