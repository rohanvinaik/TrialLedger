# Competing interpretations: workflow verification

Date: 2026-11-03. Scope: focused discovery, the invented continuing design session and the public
CLI/stdio MCP boundaries. The root agent owns the engine, binding implementation, complete project gate,
fresh installation and mechanized pure-decision receipts separately.

## Implemented path

`reason` discovery → `interpretations_guide.extend` → runnable invented request → public service → isolated
frame engine / existing entailment and structural operators → exact response → assistant decision list.
The result guide's root field set is compared with the actual response. No solver logic is reimplemented
in the guide or example builder. The builder executes the public CLI in a separate process.

Owned files:

- `TrialLedger/layer2/interpretations_guide.py`
- `tests/test_interpretations_entrypoints.py`
- `examples/interpretations/` (seven complete request/result pairs, builder and human-readable session)
- This receipt.

## Observations

The final scoped test run collected and passed **62 tests** using Python 3.14.7 and pytest 9.2.0:

```sh
~/Projects/SquishOS/ops/agents/bin/owned-run --label interpretation-public-final-tests -- \
  .venv/bin/python -m pytest tests/test_interpretations_entrypoints.py
```

Ruff check and format validation passed for the owned Python files. `uvx ty check --python .venv
TrialLedger/layer2/interpretations_guide.py` reported all checks passed. These are scoped observations,
not a replacement for the root's final whole-project gate or Detective's pure-decision verdicts.

All seven saved requests completed through the public CLI. The tests replay them through the command
boundary and complete stdio MCP initialization/tool-call path and compare the full responses with the saved
JSON. Network calls are forbidden. Retained source/report/workbook fixture bytes and original request
objects are checked unchanged.

| Obligation | Observed behavior |
|---|---|
| Rival frames remain separate | ECOG 0–2 and 0–3 both compatible; their ECOG 3 query decisions differ |
| Fixed floor can refute | Under-18 reading refuted against the adult premise |
| Proposal isolation | Original assumptions remain proposed; ordinary entailment still refuses them |
| Selection and revision | Selecting 0–2 refutes ECOG 3; selecting 0–3 permits it without requiring it; all frames retained |
| Scheduled/actual distinction | Routine days 42 and 49 fit; routine day 28 conflicts; actual unscheduled day 28 fits its separate event |
| Unknown application retains values | Outside-EFQ count 40 survives; incompatible outside=0 claim cannot eliminate while binding unresolved |
| Resolved binding reaches a decision | Same outside=0 claim refutes once its application is usable; one survivor retains declared-family conditional standing |
| Unknown versus unavailable | Observed week 12 supplied hypothetically completes the definition; imputed-only remains unresolved; explicitly unavailable observed input conflicts |
| Edition and scope | Mismatched arm/application or definition edition remains unresolved without falsely refuting the clinical plan |
| OR versus AND | A hypothetical disjunction allows countermodels that a conjunction excludes |
| Fixed conflict | Contradictory floor blocks every common conclusion without explosion |
| Computation boundary | Bound 1 retains all rivals unresolved and names resource_bound; invalid bounds are refused |
| Strict public shape | Nulls, unknown fields, invalid origins, duplicate ids, unknown selection and missing signal references are named refusals |

MCP rejects a null top-level request at its transport schema with `refused: wrong_type`; the CLI returns
the reasoning refusal envelope. Tests preserve that boundary instead of pretending both reached the solver.

## Regression found during integration

Including binding-used fixed signals in each frame exposed an endpoint-completion regression: the source's
unknown week-12 baseline calculation was blocking a hypothesis even after its grouped claim supplied an
observed week-12 input. The core agent repaired the frame-state consumption. Saved examples were regenerated
after the repair. The authored endpoint test now requires the observed completion to be compatible while
retaining the source's unknown baseline context separately.

## Boundaries

Every datum and reference in this session is invented. These tests establish the named representation and
consumer obligations, not source truth, clinical appropriateness or general automatic encoding accuracy.
No source parser, external adapter, clinical spelling correction, statistical learning guarantee or complete
protocol writer was added in this scope. No performance improvement is claimed. No GSE files or terminology
stores were changed. No mechanized mutation certificate is claimed for this guide/example scope.
