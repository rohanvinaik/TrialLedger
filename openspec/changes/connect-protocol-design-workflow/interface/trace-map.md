# Task 1.3: Producer/consumer trace for the shared integration owners (Serena, main 00001d2)

The references come from Serena `find_referencing_symbols`, run fresh on 2026-11-04. Line numbers are at 00001d2.
This map tells the coordinator where each new output must enter and be consumed. Workers don't edit these
paths.

| Concern | Production owner (symbol) | Actual consumers found | v2 integration point |
|---|---|---|---|
| Session admission | `session_state.prepare` (269–383): strict field set, `schema_version == 1` | `design_session.run` (`current`/`old`), `request_preparation._session` (via `_decision_inputs`) | Dispatch on `schema_version`: 1 is unchanged (CMP-1); 2 also runs `protocol_objects.validate_protocol(protocol, target, premises, sources)` after the premises/sources are indexed, and adds protocol nodes to `graph`/`order` |
| Decision guard, path 1 | `session_state._decision_inputs` (215; raises `alternative_requires_exact_entailment_query` at 243) | `session_state.prepare` (364), `request_preparation._session` (479) | Tagged `kind: protocol_options` decisions go to a new coordinator validator. Legacy decisions keep this guard unchanged |
| Decision guard, path 2 | `design_session._decisions` (raises the same code at 574) | `design_session.replay` (712) only | The same tag dispatch. Both paths must change together; they are sibling parser/evaluator paths |
| Premise projection | `session_projections.project` and `effective` | `design_session._request` (444) and `replay` (669) | Unchanged. A protocol check's premise standing comes from `values[...]` (effective premises) and is passed to packet E as `premise_standing` |
| Child execution and budget | `design_session._child` (reservation at `_child/reserved`, line 236, through `_reserve` at 411) | `replay` (673), `_distinctions` (300), and `definition_checks.run` through the lambda at 690 | Protocol child `signals` requests run through `_child` so that `_reserve` charges them. `_reserve` must learn the three new kinds' `work_reservation(data)`: the operators expose it, and `solver_work` is the existing owner |
| Signal registration | `signals.MODULES` and `signals.operator` | `service._prepared_signals` (312, which refuses unknown kinds), `signals_guide.extend` (158–162: `INPUTS[kind]` and `EXAMPLES[kind]`), and the tests `test_signals.py:30` and `test_reason_entrypoints.py:243/264`, which run every discovered example through the CLI and MCP | Register `schedule_coverage`, `finite_policy` and `binomial_design`. Each module needs `INPUTS` and `EXAMPLES`; `EXAMPLES` was added to `operators.md` during wave 1. The existing parametrized tests then cover their discovery examples automatically. Check the `test_signals.py` expected-code list (it special-cases `dependencies`/`estimand` as `unresolved`) |
| Support gate | `signals.evaluate` and `support_state` | `service._signals` (356), `design_bounds.bound_designs` (175/249), `interpretations._local_calculation`/`_claim_checks`/`_frame_row`/`resolve` (144/258/294/532), `source_assertions._local_signals` (201) | The public `signals` request carries **no claims**: `service._signals` calls `signals.evaluate(signal)`. Coordinator change: an optional per-signal `claims` field, accepted only for the three new kinds (`unsupported_signal_claims` otherwise), passed to `signals.evaluate(signal, claims)`. `interpretations` and `design_bounds` consume generic kinds through candidate claims. Their admission boundary must be tested for the new kinds, or the new kinds explicitly refused there (V5) |
| Replay output | `design_session.replay` (660–727) | `run` (1057/1058), then `_diff` and `_answer_diff` | v2 adds a `protocol` section: the index, checks with per-claim gating (R1), receipts and child references. `_answer_diff` gains protocol axes in slice 5 |
| Definition relations | `definition_checks.prepare`/`run` | `session_state.prepare` (365), `replay` (686–691) | DEF-1/2 bind to actual protocol child request/result addresses (slice 5, task 5.4) |

**Open items for the coordinator's later slices.**
- The compact reader (`reasoning_delivery`), `result_semantics`, `clinical_answers`, revision (`prepare_revision`,
  `_answer_diff`) and export (`analysis_review`, the decision-list writer) are traced when slices 5 and 6 begin.
  Nothing in wave 1 or wave 2 touches them.
- Each slice's pass brief must refresh these references. Line numbers drift.
