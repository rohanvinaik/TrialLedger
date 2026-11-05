# Replay-budget formulas: candidate, check and old/new replay work (task 1.5, C10), interface v1

This publishes how `design_session` charges work for protocol checks, plan alternatives and revisions, derived
from the code and verified by `tests/test_protocol_replay_budgets.py`. The operator reservations themselves
(`operators.md`) are inputs here. Where this file and the code disagree, the code is the ground truth and the
disagreement is listed under **Findings**.

## What is charged, and where

Everything is charged through one owner, `design_session._child(request, execute, budget, limits)`:

| Counter | Added per child | Enforced |
|---|---|---|
| `budget["analyses"]` | 1 | `limits.max_analyses` |
| `budget["solver_work_reserved"]` | `_reserve(request)` | `limits.max_solver_work` |
| `budget["expanded_items"]` | `_nodes(request)` | not enforced (diagnostic only) |

The counters are added **before** the child executes. The refusal check runs immediately after adding, so the
refused child's own reservation is already inside the budget that the refusal reports.
`design_session.run` returns the final counters as `work`; a refusal carries them in `diagnostics`.

Nothing is reserved for the whole session up front. Reservation is incremental and pre-execution per child:
children that fit run, and a child that crosses a limit raises `SessionBudgetError` only when the crossing child is not a protocol check child (see below); a protocol check child
that crosses a limit is released and recorded as limited, and the run continues (F1, fixed).

## Symbols

- `nodes(x)`: JSON node count. Every dict, list and scalar is one node; dictionary keys are not nodes
  (`design_session._nodes`).
- `N(q)`: `nodes(q)` of one constructed child request `q`.
- `R_op`: the operator's own reservation:
  - `schedule_coverage`: `4*s**2 + 6*s + 8`, with `s = w + c` the interval counts of `permitted` and `available`
    (null counts as 0). `protocol_schedule._reservation`.
  - `finite_policy`: `S*V*(K+P+I) + V*T`, with `S` states, `V` the product of the domain sizes, `K`, `P`, `I` the
    constraint, prohibition and invariant counts, `T` transitions. `protocol_policies._reservation`.
  - `binomial_design`: `12*(n+2)`. `protocol_statistics.work_reservation`.
- No repeat factor: `design_session._nested_protocol_work` sums `work_reservation` over operator nodes once,
  because `signals.evaluate` calls a claim-kind operator once per signal. (`_nested_table_work`, with the
  `3*(queries+1)*(frames+1)*(candidates+1)` repeat factor, now covers decision tables only.)

## Per child

A `signals` child (every protocol operator child):

```text
analyses            += 1
expanded_items      += N(q)
solver_work_reserved += N(q) + sum(R_op(signal) for signal in q.signals if signal.kind is an operator kind)
```

`design_session._reserve`: for operation `signals`, `base = _nodes(request)` (it is not one of the solver
operations and `solver_work.logical_reservation` returns `None`), and `_nested_protocol_work` adds `R_op` once for
every dict node whose `kind` is `schedule_coverage`, `finite_policy` or `binomial_design`.

Reference values for the test session (one permitted window, `c` collected intervals, four support entries,
three claims; `N = 58 + 5*(1+c)` there):

| c | s | R | N | charge = N + R |
|---|---|---|---|---|
| 0 (null counts 0; `[]` also 0) | 1 | 18 | 63 | 81 |
| 1 | 2 | 36 | 68 | 104 |
| 2 | 3 | 62 | 73 | 135 |
| 4 | 5 | 138 | 83 | 221 |
| 5 | 6 | 188 | 88 | 276 |

`N` is measured on the retained request. It grows by 5 nodes per interval and with every support entry, basis
string and claim; the test session's constants are not a general closed form. Binomial `n = 20`:
`N = 81`, `R = 264`, charge `345`. Policy (S=2, V=2, P=1, T=1): `R = 6`, `N = 208`, charge `214`.

An entailment child (applicability, legacy analyses, decision distinctions) is charged
`solver_work.logical_reservation(request, bound)` (the partition-space bound) plus `0` nested operators. It has no
closed form here; the tests read it from `design_session._reserve` and check only that it is charged once.

### Conservative planning bound, before building anything

At the hard operator ceilings the largest single child (excluding N) is its `R`:

| Operator | Largest R |
|---|---|
| `schedule_coverage` (32 + 32 intervals) | 16,776 |
| `binomial_design` (n = 512) | 6,168 |
| `finite_policy` (S=32, V=4096, K+P+I=96, T=128) | 13,107,200 |

Only a policy with `N + R` above `max_solver_work` (hard ceiling 10,000,000), that is K+P+I of roughly 77 or more at
S=32, V=4096, is limited by the session before the operator can report its own `limit`. Policies with R between
1,000,000 and the session limit run and return the operator's `limit` code, as README R6 says.

## Per protocol check child

`design_session._run_protocol_checks` runs, for each check id in the list it is given:

1. `protocol_projections.project(index, check_id, ...)` (uncharged) returns zero or more children. A `schedule`,
   `finite_policy`, `binomial_design`, `estimand` or `dependencies` check yields one child; `external_method`,
   `definition` and any unresolved projection yield none, so they cost nothing.
2. For each child, `_applicability(child.receipt.conditions, deciding, ...)`:
   - no conditions: no child;
   - conditions but no `condition_applicability` binding on the check: no child, the claims stay conditional;
   - with the binding: **one entailment child per declared condition**, in order, before the check child.
3. One `signals` (or `temporal` / `decision_table`) child for the check child itself. If this child crosses a
   session limit, `_limited_child` releases its charge (`analyses`, `expanded_items`, `solver_work_reserved`),
   records the child as a refused result (`problems: [code]`) and appends to the check's `unresolved` an entry
   `{code: "session_work_limit", objects: [], premises: [], limit, reserved, already_reserved,
   configured: {max_analyses, max_solver_work}}`. Later checks that fit still run, and the check classifies as
   `undetermined`, never satisfied.

```text
cost(check, index) = sum over children j of [ m_j * E_j  +  charge(q_j) ]
```

with `m_j` the number of conditions bound for child `j`, `E_j` the entailment charge and `charge(q_j)` as above.
A check costs `0` when its projection is unresolved or not computed.

## Per plan alternative

`design_session._protocol_decision_rows`: for every protocol decision, for every alternative, it builds the
candidate (`protocol_decisions.candidate`) and calls `_run_protocol_checks` on **the candidate index** with
exactly the alternative's `checks` list. Nothing from the baseline run is reused:

```text
cost(decision d) = sum over alternatives a of d, sum over checks c in a.checks, of cost(c, candidate(a))
```

- An alternative with `replace_objects: []` is still a full fresh replay (the test asserts three identical
  requests are charged three times).
- Required checks must be listed by every alternative (`protocol_option_missing_required_check`); optional
  context checks must be the same set for all of them. So with `M` listed checks and `N_d` alternatives a
  decision adds `N_d * M` check costs.
- Each decision adds its own set; two decisions over the same checks double the alternative work.

## Whole replay of one snapshot

`design_session.replay` charges, in this order:

1. one child per declared analysis in dependency order (`prepared["order"]`; sources and premises are free);
2. `_protocol_checks`: the baseline checks in `check_order`, then every protocol decision's alternatives in
   declaration order;
3. `definition_checks.run`: one entailment child per accepted relation direction (`equivalent` = 2, `implies` and
   `disjoint` = 1; a relation that is blocked costs 0);
4. `_decisions`: one entailment child per unordered pair of `feasible` legacy alternatives with equal floors.

```text
W(snapshot) = analyses + protocol_baseline + sum_d cost(d) + definitions + legacy_distinctions
children(protocol) = M + sum_d N_d * M_d          (+ m per bound condition)
```

For `M` checks and `N` alternatives of one decision with a one-child schedule check: `analyses = M * (1 + N)`.

## Old and new snapshots in a revision

`design_session.run` with `previous` creates a single `budget` and calls `replay(old)` then `replay(new)` into it.
The old snapshot is replayed **freshly**, not read from the supplied previous result:

```text
W(revision) = W(old) + W(new)
```

The limits apply to the running total, so a revision can refuse inside the new snapshot even though the new
snapshot alone fits. The earlier standalone `run` of the old session is a separate budget and is not counted.

## Limits: which one refuses, at what boundary

| Field in `session.limits` | Code that refuses | Comparison | Where | Hard ceiling |
|---|---|---|---|---|
| `max_solver_work` | `resource_bound:session_solver_work` | `solver_work_reserved > limit` (equal passes) | `_child` via `session_work_code`, checked **first**. Protocol check child: limited (`limit` in the unresolved entry). Any other child: whole run refused | 10,000,000 |
| `max_analyses` | `resource_bound:session_analyses` | `analyses > limit` (equal passes) | `_child`, checked second | 128 |
| `max_output_bytes` | `resource_bound:session_output_bytes` | `len(canonical(output).encode()) > limit` (equal passes) | end of `run`, after all children | 16,000,000 |
| `max_expanded_items` | none | not compared | `limit_semantics`: `legacy_nonoperative` | 10,000 |
| `max_analyses` (admission) | `resource_bound:analyses` | declared analyses `>` limit | `session_state.prepare` | 128 |
| `max_premises`, `max_sources`, `max_decisions` | `resource_bound:premises` / `sources` / `decisions` | declared count `>` limit | `session_state.prepare` | 1000 / 64 / 128 |
| any limit field | `invalid_limit:<field>` | not an integer in `[1, hard ceiling]` | `session_state.prepare` | as listed |

When both work and analyses are exceeded by the same child, the solver-work code is reported. A whole-run refusal
(applicability entailments, declared analyses, definition and decision children) carries in its
`diagnostics` `{code, operation, budget, limits: {max_analyses, max_solver_work}, request_reservation}`;
`budget` includes the refused child. `max_analyses` counts every child (applicability entailments, protocol
checks of every alternative, both snapshots), so at the default 128 it is the binding ceiling long before the
protocol ceilings: `M * (1 + N) <= 128`, for example 8 checks admit 15 alternatives; a 16th is limited (its
last 8 checks `undetermined`) rather than refused.

Protocol ceilings that are not budget limits (256 objects `protocol_object_limit`, 128 checks
`protocol_check_limit`, 16 alternatives `protocol_option_count`, 16 replacements `protocol_option_fields`,
32 intervals `*_union_limit`) are admission refusals counted in lengths, not in work. The operator's own work
ceiling, `MAX_POLICY_WORK = 1,000,000`, is independent: it makes the operator return code `limit` for an
executed child, and applies only to `finite_policy`.

## Not charged

Projection, candidate construction and admission validation; premises and sources; retained source bytes; display
caps (`witness_limit`); reply size; the `previous` result supplied by the caller.

## Findings

- **F1. Fixed: a session bound limits one protocol check; it no longer refuses the run.** A protocol check
  child that crosses a limit is released and recorded as limited with the named limit, reserved and already
  reserved work, and the configured ceilings; independently completed checks keep their results and the run is
  `complete`. Non-protocol children still refuse the whole run. In a revision, a check limited in either
  snapshot is reported in `answer_diff.protocol_checks` as `{code: not_computed, axes: [], limited: [before|after],
  changes: []}`, never as a verdict change (fixed after review; the export words it "Not compared").
- **F2. Limitation to accept: reservation is incremental, not at admission.** C10 says admission reserves a
  conservative bound on baseline, candidate and old/new replay. The code reserves child by child while replaying,
  so a late child can be limited after earlier ones have run. Per-check limiting (F1) now makes this graceful but
  the reservation is still not known up front, and which checks are limited depends on declaration order.
- **F3. Fixed: operators are charged once.** `N + sum(R)` replaces `N + 6*sum(R)`, so README R6 holds literally up
  to the session limit.
- **F4. The default `max_analyses` (128) is the effective alternatives-times-checks ceiling.** The 16-alternative
  and 128-check protocol ceilings cannot both be used: 16 alternatives of 8 checks need 136 children (the surplus
  is limited).
- **F5. There are no protocol-specific configurable ceilings.** C10 allows "lower configurable limits"; the only
  configurable bounds are the seven `session.limits` fields. `max_expanded_items` is accepted and ignored.

## Test map

`tests/test_protocol_replay_budgets.py` observes the code two ways: it wraps `design_session._child`
(monkeypatch `Spy`) to record each child and its delta, and it reads the retained counters `reply["work"]` and the
refusal `diagnostics`. Expected numbers come from a local node counter and the operator formulas above, never from
`_reserve` (the single exception is the entailment child, stated in the test).

| Claim | Test |
|---|---|
| per child, schedule | `test_one_schedule_child_costs_nodes_plus_the_operator_reservation` |
| per child, policy and binomial | `test_policy_and_binomial_children_are_charged_by_their_own_operator_formulas` |
| unresolved / not computed checks are free | `test_a_check_whose_projection_is_unresolved_or_not_computed_is_charged_nothing` |
| per check | `test_the_baseline_charges_one_child_per_declared_check` |
| per alternative, N x M, optional checks | `test_every_alternative_replays_all_its_checks_freshly_and_the_total_is_the_sum` |
| fresh replay, no reuse | `test_an_alternative_identical_to_the_baseline_is_still_charged_not_reused` |
| applicability | `test_applicability_entailments_are_charged_before_the_check_child_and_only_when_bound` |
| old + new | `test_a_revision_replays_both_snapshots_into_one_budget`, `..._costs_more_than_the_new_snapshot_alone_by_exactly_the_old_replay` |
| ceilings | `test_the_solver_work_limit_is_inclusive...`, `test_the_analyses_limit_is_inclusive...`, `test_solver_work_is_named_before_analyses...`, `test_a_non_protocol_child_over_the_limit_still_refuses_the_whole_run`, `test_c10_a_session_bound_limits_one_check_and_keeps_the_completed_ones`, `test_a_later_smaller_check_still_runs_after_a_larger_one_is_released`, `test_a_limited_checks_claims_never_read_satisfied...`, `test_a_revision_with_one_snapshots_check_limited...`, `test_a_policy_over_its_operator_ceiling_runs_while_the_session_has_room..., `test_the_output_size_limit_is_inclusive...`, `test_session_limits_are_inclusive_at_the_hard_ceiling...`, `test_the_legacy_expanded_items_limit_is_diagnostic_only`, `test_the_default_analyses_limit_is_the_binding_protocol_ceiling...` |
