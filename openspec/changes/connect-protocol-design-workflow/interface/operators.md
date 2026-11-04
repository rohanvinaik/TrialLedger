# Frozen operator interfaces: packets B, C and D (interface v1)

This file mechanically instantiates contracts C4–C7 and C10 for the three pure mathematical operators. It
does not change their meaning. Where the contracts left a name or shape open, the choice made here is listed
under "Wave-0 resolutions" in `README.md` and is binding on every packet. Fixtures with expected outcomes are in
`fixtures/`. A builder who finds this file insufficient reports the exact case and stops that part of the work.

## Common rules for all three operators

- **Module contract (existing signal operator contract, `TrialLedger/layer2/signals.py`).** Each module exposes:
  - `INPUTS: dict`, describing its data fields, claims, outcomes and limits, in the same style as
    `decision_tables.INPUTS`;
  - `evaluate(kind: str, data: dict) -> dict`;
  - `check(kind: str, data: dict, claims: list[dict]) -> dict`;
  - `work_reservation(data: dict) -> int`, a pure function that may raise the same `ValueError` codes as
    `check`.
  - `EXAMPLES: dict`, exactly `{kind: <one invented, valid data dict>}`, mirroring `decision_tables.EXAMPLES`.
    `signals_guide.example(kind)` wraps it for discovery. Values and labels are plainly invented, with no
    clinical defaults. (Added during wave 1, after the registration trace; sent to B, C and D.)
- **Result envelope.** The result is a dict with exactly the keys `code`, `value`, `blockers` and `rule`. Packets C
  and D return the resolved extended form (see "Support envelope"). Packet B returns the plain form. `blockers` is a sorted list of
  unique strings. `rule` is a fixed string naming the rule and its version.
- **Translation refusals.** Malformed input raises `ValueError("<named_code>")`; nothing is ever coerced. The
  listed codes are exhaustive for each operator. A new refusal needs a coordinator decision.
- **Wrong kind.** `evaluate` and `check` raise `ValueError("unsupported_<module>_kind")` when `kind` is not the
  operator's kind.
- **Strict JSON input.** Unknown fields and missing fields refuse; `bool` is never accepted as an int; floats are
  never accepted where a rational is expected. Inputs are never mutated: build new structures, don't edit
  `data`.
- **Shared rational syntax (C5).**
  - A rational is a JSON string matching `^-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?$`, so a denominator is positive
    and has no leading zero.
  - The numerator and denominator, as written, each have `abs(int).bit_length() <= 256`.
  - Canonical output is the reduced fraction with a positive denominator. Integers are written without `/1`,
    and zero is `"0"` (input `"-0"` reads as 0).
  - Floats, ints, whitespace, `"+1"`, `"1.5"`, `"1e3"`, `"NaN"` and `"1/0"` all refuse.
  - **Use the frozen coordinator module `TrialLedger/layer2/protocol_numbers.py`; don't reimplement it.**
    `rational(value, prefix)` returns a Fraction or raises `<prefix>_invalid_rational` /
    `<prefix>_rational_bit_limit`. `render(Fraction)` gives canonical output. `union(raw, prefix)` returns
    validated intervals in input order, or None, raising `<prefix>_invalid_union`, `_union_limit`,
    `_invalid_interval`, `_infinite_inclusive` and `_empty_interval`. `render_union` renders without
    normalizing. The prefixes are `schedule` and `binomial`. Set arithmetic and normalization belong to
    packet B.
- **Display caps never change outcomes.** Exhaustive counts are reported beside capped witness lists.
- **Support envelope (C and D): standing words keep their existing meaning (C1.1).**
  - C and D return the *resolved* extended form: `code`, `value`, `blockers`, `rule`, `support_status`,
    `determining_ids` and `support_resolution`. `signals.evaluate` accepts this third form; the coordinator
    added it after the side-agent review on 2026-11-04.
  - `support_status` is the weakest status *actually declared* on the internal rules or assumptions: proposed
    if any is proposed, else interpolated if any is, else known. It is **never** set to `proposed` for anything
    that wasn't proposed.
  - `support_resolution` is the worst declared resolution, in the order conflicting > unresolved >
    partially_resolved > resolved. A missing required binding (packet D's missing role) makes it at least
    `unresolved`.
  - Both are `null` together, only when no internal rule or assumption is in play.
  - The gate conjoins both with the outer support. A proposed status is refused as `proposed_refused`; a
    non-resolved resolution is refused as `binding_unresolved`. The signal code becomes `unresolved` and
    `calculation_code` keeps the arithmetic. The exact per-row reason stays in `value`.
  - Per-claim gating (R1) remains the coordinator's managed path.
- **Prohibited imports and side effects.** No module imports `session_state`, `design_session`,
  `session_projections`, `service`, `request_preparation`, transport (`cli`, `mcp_server`, `reasoning_*`),
  acquisition or presentation modules. No file I/O, no network, no randomness, no clock reads.
- **Allowed imports.**
  - `fractions`, `itertools`, `json`, `math`, `dataclasses`, `typing` and `copy`.
  - `TrialLedger.layer2.assertions`, `TrialLedger.layer2.entail` and `TrialLedger.layer2.decision_tables`
    (packet C only).
  - `TrialLedger.layer2.signals.support_state` (packets C and D, for standing summaries only).
  - `TrialLedger.layer2.protocol_numbers` (packets B and D, and packet A in `ledger.md`).
- **Pure-decision helpers.** Small helpers that classify an outcome get docstrings with `pre:`/`post:`
  contracts, in the style of `decision_tables.prohibition_state`. They are total functions over
  str/bool/int/list/dict and return named string codes. Tag them `(pure — pinned)` only once the coordinator
  schedules their pin.

## Packet B: `schedule_coverage` (module `TrialLedger/layer2/protocol_schedule.py`)

### Data

`data` has exactly `scope`, `anchor`, `unit`, `nominal`, `permitted` and `available`.

| Field | Shape | Refusal codes |
|---|---|---|
| scope | Nonempty string of at most 1024 characters: an opaque, already validated scope identity | `schedule_invalid_scope` |
| anchor | Nonempty string of at most 256 characters: an exact event identity, never interpreted | `schedule_invalid_anchor` |
| unit | Nonempty string of at most 64 characters, compared only by exact equality | `schedule_invalid_unit` |
| nominal | A rational or `null`. `null` means "no nominal target declared" and never defaults | `schedule_invalid_rational` |
| permitted | `null` (unknown) or a union | see "Unions" |
| available | `null` (unknown, never "none") or a union. `[]` means explicitly no collection in this scope | see "Unions" |

**Unions.**
- A union is a list of 0 to 32 intervals (`schedule_union_limit` beyond that). Each interval has exactly
  `lower`, `upper`, `lower_inclusive` and `upper_inclusive`.
- `lower`/`upper` are rationals, or `null` for −∞/+∞. An inclusive flag at an infinite end must be `false`
  (`schedule_infinite_inclusive`). The flags must be strict bools (`schedule_invalid_interval`).
- An interval must be nonempty:
  - either `lower < upper`;
  - or `lower == upper` with both ends inclusive (a singleton).
  - A reversed interval, or an equal-endpoint interval that isn't closed on both sides, refuses with
    `schedule_empty_interval`.
- Normalization (applied to the output, never to the input object):
  - Sort intervals by lower endpoint.
  - Merge two intervals only when their union is one interval: they overlap, or they touch with the shared
    point included at least once. `[1,2)` and `[2,3]` merge to `[1,3]`; `[1,2)` and `(2,3]` stay separate.
  - Never fill a gap.
  - Canonical rationals in the output.

The full refusal list for packet B is `unsupported_schedule_kind`, `schedule_data_fields`,
`schedule_invalid_scope`, `schedule_invalid_anchor`, `schedule_invalid_unit`, `schedule_invalid_rational`,
`schedule_rational_bit_limit`, `schedule_invalid_union`, `schedule_union_limit`, `schedule_invalid_interval`,
`schedule_infinite_inclusive`, `schedule_empty_interval`, `schedule_invalid_claims` and
`schedule_duplicate_claim`.

### Claims

- `claims` is a nonempty list of 1 to 3 objects, each with exactly `id` and `claim`.
  - `id` is a nonempty string; ids are unique.
  - `claim` is one of `existence`, `nominal` or `full_window`, each used at most once
    (`schedule_duplicate_claim`). A repeated `id` also refuses with `schedule_duplicate_claim` (settled
    during wave 1 after the B′ oracle report).
  - An empty list or wrong shape refuses with `schedule_invalid_claims`.
- `evaluate(kind, data)` equals `check(kind, data, [{"id":"existence","claim":"existence"},
  {"id":"nominal","claim":"nominal"},{"id":"full_window","claim":"full_window"}])`.

### Outcomes

Let W = permitted, n = nominal and C = available. The table is checked top to bottom; the first matching row
applies.

| claim | Condition, in order | outcome | determined_by | missing |
|---|---|---|---|---|
| existence | W = [] | `no_permitted_time` | [permitted] | [] |
| existence | W null | `unresolved` | [] | [permitted] + ([available] if C null) |
| existence | C null | `unresolved` | [] | [available] |
| existence | W∩C ≠ ∅ | `satisfied` | [available, permitted] | [] |
| existence | otherwise | `no_feasible_time` | [available, permitted] | [] |
| nominal | n null | `unknown_target` | [nominal] | [nominal] |
| nominal | W null | `unresolved` | [] | [permitted] + ([available] if C null) |
| nominal | n ∉ W (including W = []) | `outside_window` | [nominal, permitted] | [] |
| nominal | C null | `unresolved` | [] | [available] |
| nominal | n ∉ C | `not_collected` | [available, nominal, permitted] | [] |
| nominal | otherwise | `satisfied` | [available, nominal, permitted] | [] |
| full_window | W = [] | `no_permitted_time` | [permitted] | [] |
| full_window | W null | `unresolved` | [] | [permitted] + ([available] if C null) |
| full_window | C null | `unresolved` | [] | [available] |
| full_window | W∖C = ∅ | `satisfied` | [available, permitted] | [] |
| full_window | otherwise | `uncovered` | [available, permitted] | [] |

`determined_by` and `missing` lists are sorted. `determined_by` names the minimal input roles the outcome
depends on. The coordinator gates each claim's support over exactly those roles (Resolution R1). This is how a
known `outside_window` survives an unknown or proposed collection plan.

### Value

The value has these fields, in order:
- `scope`, `anchor`, `unit`;
- `nominal` (canonical, or null);
- `permitted` and `available` (normalized, or null);
- `claims`, a list in the caller's order. Each row has exactly `id`, `claim`, `outcome`, `determined_by`,
  `missing`, `feasible` and `uncovered`:
  - `feasible` is the normalized W∩C on existence rows when W and C are both known; otherwise `null`.
  - `uncovered` is the normalized W∖C on full_window rows when W and C are both known; otherwise `null`.
- `work`, exactly `{"reserved": R, "used": U}`, with U ≤ R as an invariant;
- `guarantee`, the string `"exact_over_declared_intervals"`.

### Code, blockers and rule

- **Code.**
  - `violated` if any row's outcome is `no_permitted_time`, `no_feasible_time`, `outside_window`,
    `not_collected` or `uncovered`.
  - Otherwise `unresolved` if any row is `unresolved` or `unknown_target`.
  - Otherwise `satisfied`.
- **Blockers.**
  - `schedule_<outcome>:<claim id>` for every violated row;
  - `schedule_unresolved:<claim id>` for every unresolved or unknown_target row.
- **Rule.** `"schedule.exact_interval_coverage:1"`.

### Work

- The charged unit is one endpoint comparison: one call that compares two rationals, or a rational with an
  infinity.
- With w = len(W) (0 if null) and c = len(C) (0 if null), `R = 4*(w+c)**2 + 6*(w+c) + 8`.
- `used` counts actual comparisons. Tests must show U ≤ R on every fixture and on random small unions.

## Packet C: `finite_policy` (module `TrialLedger/layer2/protocol_policies.py`)

### Data

`data` has exactly `scope`, `version`, `variables`, `constraints`, `states`, `initial`, `terminal`, `actions`,
`transitions`, `prohibitions` and `invariants`.

| Field | Shape | Notes |
|---|---|---|
| scope, version | Nonempty strings of at most 1024 characters | |
| variables | The decision-table domain list `[{id, values:[equality Literal]}]`, validated by calling `decision_tables._domains` unchanged (at most 8 variables, at most 32 values each) | Product of value counts ≤ 4096, else `policy_valuation_limit`. No variable may use the reserved key (below) |
| constraints | List of at most 32 `{id, condition, rule}` | `condition` is a tagged proposition, parsed by `decision_tables._proposition` |
| states | 1 to 32 unique nonempty strings | Declared order is the tie order |
| initial | Nonempty unique subset of states | |
| terminal | Unique subset of states, possibly empty | A state may be both initial and terminal |
| actions | 1 to 64 `{id, scope:{level, ref}, description}` | `level` ∈ participant, cohort or study; `ref` and `description` are nonempty strings of at most 1024 characters. The description is attributed wording and is never interpreted |
| transitions | At most 128 `{id, from, to, guard, actions}` | `guard` is a tagged proposition; `actions` is a nonempty unique list of declared action IDs. `from` may not be terminal (`policy_terminal_outgoing`) |
| prohibitions | At most 32 `{id, state, condition, actions, rule}` | `state` is a declared state or null (all states); `actions` is a nonempty unique list of declared IDs |
| invariants | At most 32 `{id, state, condition, actions, rule}` | `actions` must be exactly `[]` (`policy_invariant_actions`) |

- **`rule`** (on constraints, prohibitions and invariants) is the existing standing reference
  `{ref, version, status, resolution, basis}`, validated like `estimand_evidence._ref`:
  - `status` ∈ known/interpolated/proposed;
  - `resolution` ∈ resolved/partially_resolved/unresolved/conflicting;
  - `basis` holds 1–32 unique nonempty strings.
- **IDs.** Constraint, transition, prohibition and invariant ids are each unique within their own list.
  Action ids are unique.
- **Variable keys.** Every condition, guard and constraint may use only declared variable keys plus the
  reserved key. Anything else refuses with `policy_undeclared_variable`.
- **Reserved variable `policy_state`.**
  - It is the equality literal with subject `{kind:"study_procedure", referent:""}`, predicate
    `{kind:"measurement", key:"policy_state"}`, an enum value with comparison `eq` and exactly one member, which
    is a declared state name. Polarity is positive, time null, qualifiers Always and evidence empty.
  - Build its key with `decision_tables._keys` on that literal.
  - Its value is always the node's current state; callers never supply it.
  - A literal using it with an undeclared state name refuses with `policy_unknown_state`.
  - Declaring it as a variable refuses with `policy_reserved_variable`.
- **Refusal list for packet C:**
  - `unsupported_policy_kind`, `policy_data_fields`, `policy_invalid_text`, `policy_invalid_list`,
    `policy_valuation_limit`, `policy_reserved_variable`, `policy_undeclared_variable`;
  - `policy_invalid_states`, `policy_unknown_state`, `policy_invalid_initial`, `policy_invalid_terminal`,
    `policy_invalid_action`, `policy_duplicate_id`, `policy_unknown_action`, `policy_terminal_outgoing`;
  - `policy_invariant_actions`, `policy_invalid_rule`, `policy_invalid_claims`, `policy_duplicate_claim`;
  - plus any `table_*` code raised unchanged by the reused decision-table validators.

### Semantics

- **Valuations.**
  - The external valuations are the product of the variable choices from `decision_tables._domain_options`,
    in declared order: the first variable varies slowest, and values follow declared order.
  - The valuation index is the position in that product.
  - The assignment for evaluation is `{variable key: scalar}` plus `{policy_state key: state}`.
  - Evaluate with `entail._holds(entail.proposition_formula(body)[0], assignment)`.
  - F(s) is the set of valuations that satisfy every constraint when the state is s.
- **Initial nodes** are (s, v) with s ∈ initial and v ∈ F(s). If there are none, the code is
  `inconsistent_domain` and every claim's outcome is `inconsistent_domain`. Nothing is vacuously covered, safe
  or terminating.
- **At a reachable node (s, v):**
  - Invariants with state ∈ {s, null} must hold. This applies at terminal nodes too.
  - If s is terminal, the node has no transitions and is exempt from coverage and exclusivity only.
  - Otherwise E = the transitions with `from == s` whose guard holds:
    - |E| = 0 is a coverage **gap**.
    - |E| > 1 is **competing**, whatever their actions or targets. There is no row priority and no dedup.
  - For each t ∈ E and each prohibition p with state ∈ {s, null}: if p's condition holds at (s, v) and
    `t.actions ∩ p.actions ≠ ∅`, that is a **prohibition violation**.
  - For each t ∈ E:
    - If F(t.to) is empty, record a **transition_target_infeasible** conflict, keeping the attempted
      transition.
    - Otherwise every (t.to, v') with v' ∈ F(t.to) is reachable, because inputs vary nondeterministically
      between steps (POL-2).
- **State-level computation is the reference.** Because successor valuations range over all of F(to),
  compute reachable states as a fixpoint over states, never by materializing node-to-node edges. The reachable
  nodes are all (s, v) with s reachable and v ∈ F(s).
- **Termination** is computed only when requested.
  - **State graph:** an edge s→t.to exists when some v ∈ F(s) enables t and F(t.to) is nonempty.
  - **`all_paths_terminate`** holds only when all three hold: no reachable cycle in that graph, no reachable
    gap node, and no reachable transition_target_infeasible.
  - **`not_established`** otherwise, with `reasons` ⊆ {`reachable_cycle`, `dead_end`,
    `transition_target_infeasible`} (sorted).
  - No fairness is assumed. Acyclic with a dead end is not terminating.
- **Witness traces.**
  - Each is the shortest by number of transitions, built with BFS over states.
  - Ties are broken by declared state order, then valuation index, then transition declared order.
  - A trace is a list of steps `{state, valuation, transition, actions}`. The last step is the offending node;
    its `transition` is the offending transition, or `null` for gaps and invariant failures.
  - `valuation` maps variable id → the canonical JSON of the chosen equality literal.
  - Earlier steps use the first valuation, in index order, that enables the step's transition.

### Claims

- `claims` is a nonempty list of objects, each with exactly `id`, `claim` and `witness_limit`:
  - `claim` ∈ coverage, exclusivity, prohibition, invariant or termination, each at most once;
  - `witness_limit` is a strict int from 0 to 64.
  - A repeated `claim` kind or a repeated `id` refuses with `policy_duplicate_claim`.
- `evaluate(kind, data)` equals `check` with coverage, exclusivity, prohibition and invariant, each with
  witness_limit 64 and id equal to its claim name. Termination is never implicit.

### Outcomes per claim

Each claim also returns its exhaustive `violations_found` count. The outcome is `inconsistent_domain` for
every claim when there is no feasible initial node, and `not_executed` for every claim when the work limit
applies.

What `violations_found` counts for each claim:
- **coverage:** reachable nonterminal nodes with |E| = 0.
- **exclusivity:** reachable nonterminal nodes with |E| > 1.
- **prohibition:** (node, enabled transition, prohibition) triples that violate.
- **invariant:** (node, invariant) pairs that fail.
- **termination:** `len(reasons)`. Each reason gets one witness:
  - for `reachable_cycle`, a trace reaching the first cycle state in tie order;
  - for `dead_end`, the shortest gap trace;
  - for a target conflict, its trace.

| claim | Outcomes |
|---|---|
| coverage | `covered` or `gap` |
| exclusivity | `exclusive` or `competing` |
| prohibition | `not_declared` (no prohibitions), `clear` or `violation` |
| invariant | `not_declared`, `holds` or `violation` |
| termination | `all_paths_terminate` or `not_established`, with `reasons` |

### Value

- `scope`, `version`, `declared_variables` (copied input), `states`, `initial`, `terminal`.
- `feasibility`: one `{state, feasible_valuations}` per declared state.
- `reachability`: `{initial_nodes, reachable_states, unreachable_states, reachable_nodes, guard_evaluations}`.
- `transition_target_conflicts`: a list of `{transition, from, to, trace}`, never dropped.
- `claims`, in caller order. Each row has exactly:
  - `id`, `claim`, `outcome`, `violations_found`;
  - `witnesses`: at most `witness_limit` items, each `{trace, element}`, where `element` names the gap,
    transition pair, prohibition id or invariant id;
  - `witness_limit`, `witnesses_omitted`;
  - `reasons` (termination only, otherwise `[]`);
  - `standing`;
  - `determining_ids`.
- `work`: `{reserved, used}`.
- `guarantee`: `"exhaustive_over_declared_finite_model"`.
- Also: `fairness: "not_assumed"`, `operating_characteristics: "not_computed"` and
  `patient_outcomes: "not_modelled"`.

**Standing.**
- A row's `determining_ids` are all constraint ids plus, for the prohibition and invariant claims, the ids of
  that kind.
- A row's `standing` is `signals.support_state` applied to those rules' statuses and resolutions, mapped to
  `known`/`interpolated` when accepted. Otherwise it is the support_state code itself (`proposed_refused`,
  `binding_unresolved` or `missing_support`). With no rules, the standing is `"no_rule_support"`.
- The coordinator gates application per claim from these rows. The operator never decides admission.
- **Envelope support.**
  - `determining_ids` lists every constraint, prohibition and invariant id, in declared order (constraints,
    then prohibitions, then invariants).
  - `support_status` and `support_resolution` follow the common rule over those rules, and are both `null`
    when there are none.

### Code, blockers and rule

- **Code.**
  - `inconsistent_domain` when there is no feasible initial node;
  - `limit` when the work limit applies;
  - `violated` when any requested claim's outcome is gap, competing, violation or not_established, or any
    transition_target conflict exists;
  - `satisfied` otherwise.
- **Blockers:**
  - `policy_<outcome>:<claim id>` for each failed claim;
  - `policy_transition_target_infeasible:<transition id>`;
  - `policy_inconsistent_domain`;
  - `policy_work_limit`.
- **Rule.** `"policy.finite_reachable_states:1"`.

### Work

The charged unit is one proposition evaluation (`entail._holds` on one compiled formula at one assignment).

- Let S = number of states, V = the product of domain sizes, K = constraints, T = transitions,
  P = prohibitions and I = invariants.
- Each transition's guard is evaluated only at valuations of its own from-state. So the reservation is
  `R = S*V*(K + P + I) + V*T`:
  - constraints are evaluated per (state, valuation) to build F(s);
  - prohibition and invariant conditions are evaluated once per reachable node;
  - guards cost at most V per transition.
- Witness traces must reuse the enabled-transition sets cached during exploration, which costs zero extra
  evaluations. Any evaluation that isn't cached is charged and must still fit in R.
- `used` counts actual evaluations, and U ≤ R is a tested invariant.
- `MAX_POLICY_WORK = 1_000_000` (the C10 protocol-work ceiling).
- If R > MAX_POLICY_WORK, return code `limit` with every claim `not_executed` and work `{reserved: R,
  used: 0}`. Do not raise.
- Witness caps never stop the exhaustive count.
- Tests patch the constant lower to exercise the limit.

## Packet D: `binomial_design` (module `TrialLedger/layer2/protocol_statistics.py`)

### Data

`data` has exactly `scope`, `model`, `direction`, `n`, `critical_count`, `p0`, `p1` and `assumptions`.

| Field | Shape | Refusal |
|---|---|---|
| scope | Nonempty string of at most 1024 characters | `binomial_invalid_scope` |
| model | Nonempty string of at most 128 characters. Only `fixed_n_iid_bernoulli` is computed; any other string returns code `unsupported_method` | `binomial_invalid_model` |
| direction | Nonempty string of at most 64 characters. Only `greater` is computed; any other string returns `unsupported_method` | `binomial_invalid_direction` |
| n | Strict int, 1 ≤ n ≤ 512 | `binomial_invalid_n`, `binomial_n_ceiling` |
| critical_count | Strict int, 0 ≤ k ≤ n+1 | `binomial_invalid_critical_count` |
| p0, p1 | Rationals with 0 ≤ p0 < p1 ≤ 1 | `binomial_invalid_rational`, `binomial_rational_bit_limit`, `binomial_invalid_probabilities` |
| assumptions | 1 to 16 unique `{role, ref, version, status, resolution, basis}`. `role` ∈ `fixed_n`, `iid_binary` or `alignment`; the other fields follow the standing-reference rules. Roles may repeat; whole objects may not | `binomial_invalid_assumption`, `binomial_duplicate_assumption` |

The other refusals are `unsupported_binomial_kind`, `binomial_data_fields`, `binomial_invalid_claims` and
`binomial_duplicate_claim`.

**Unsupported methods.** The value is `{scope, model, direction, computed: false, reason: "unsupported_method",
assumptions}`. The code is `unsupported_method`, the blockers are `["binomial_unsupported_method"]`, and
`support_status: null`, `determining_ids: []`. Validation of n, k, p0 and p1 still applies; claims are
validated but not evaluated.

### Mathematics (exact, `fractions.Fraction` only)

- For p ∈ {p0, p1}, `tail(p) = Σ_{i=k}^{n} C(n,i) p^i (1−p)^{n−i}`, with 0^0 = 1. Hence k = 0 gives 1 and
  k = n+1 gives 0.
- `null_rejection_probability = tail(p0)` and `power = tail(p1)`, both canonical rationals.
- **Display.** `display: {null_rejection_probability, power, rounding: "half_even_4dp"}`, with strings rounded
  half-even to 4 decimal places, such as `"0.2500"`. Display values are never a comparison basis.
- **Bit ceiling.**
  - Before computing, estimate `B = n*b + n + 2`, where b is the maximum bit length over the numerators and
    denominators of p and 1−p.
  - If B > `MAX_INTERMEDIATE_BITS = 1_048_576`, return code `limit` with both probabilities `null`.
  - While computing, if any intermediate numerator or denominator exceeds the ceiling, stop and return
    `limit` the same way. Never round.
- **Work.**
  - The charged unit is one Fraction operation: one `*`, one `+`, or one `**` call, where `p ** i` counts as
    one operation. `math.comb` is integer arithmetic and isn't charged.
  - Compute each term directly as `comb(n,i) * p**i * q**(n-i)`, with q = 1−p.
  - **Never** use an incremental ratio that divides by q or p. q is 0 when p = 1, as in the STA-2 fixture
    `p1 = "1"`, and p is 0 when p0 = "0".
  - Each tail has at most n+1 terms of at most 5 operations each, so the reservation is `R = 12*(n+2)`.
    `used` counts actual operations and must be ≤ R.
  - `value.work = {reserved, used, max_bits}`.

### Claims

- `claims` is a list of 0 to 16 objects, each exactly `{id, quantity, comparison, value}`:
  - `quantity` ∈ null_rejection_probability or power;
  - `comparison` ∈ `"<="` or `">="`;
  - `value` is a rational in [0, 1].
  - Ids are unique.
- `evaluate(kind, data)` equals `check(kind, data, [])`.
- Each claim row is `{id, quantity, comparison, value, computed, outcome}`, where `outcome` ∈ satisfied or
  not_satisfied, compared exactly. A supplied alpha bound is a claim value. It is never reported as the
  computed type-I error.

### Value, code and support

- **Value:**
  - `scope`, `model`, `direction`, `n`, `critical_count`, `p0`, `p1` (canonical);
  - `null_rejection_probability`, `power`, `display`;
  - `claims`;
  - `assumptions` (copied), `assumption_coverage: {fixed_n, iid_binary, alignment}`, each `declared` or
    `missing`, and `application`;
  - `work`;
  - `guarantee: "exact_conditional_on_declared_model"`;
  - `not_computed: ["sample_size_search", "sequential_or_adaptive_operating_characteristics",
    "clinical_applicability"]`.
- **Code:**
  - `unsupported_method` or `limit` as above;
  - otherwise `not_satisfied` if any claim row is not_satisfied;
  - `satisfied` if there are claims and all are satisfied;
  - `computed` when there are no claims.
- **Blockers:**
  - `binomial_assumption_missing:<role>` for each missing role (the calculation is retained);
  - `binomial_claim_not_satisfied:<id>`;
  - `binomial_bit_limit`.
- **Support (common rule).**
  - `support_status` is the weakest declared assumption status.
  - `support_resolution` is the worst declared resolution, raised to at least `unresolved` when any of the
    three roles is missing.
  - Both are `null` only for `unsupported_method` and `limit`.
  - `determining_ids` lists every assumption's `ref`, unique, in declared order.
  - `value.application` is exactly `{"code": "withheld" | "not_withheld_by_assumptions", "reasons": [...]}`.
    The reasons are sorted, from `assumption_missing:<role>` and `assumption_not_accepted:<ref>`.
    `not_withheld_by_assumptions` doesn't admit anything; admission still needs the outer gate.
- **Rule.** `"binomial.exact_one_stage_greater:1"`.

## Independent oracle obligations (V3), for the oracle packets B′, C′ and D′

Oracle authors never read the implementation module. Their oracle code lives in the test file named in
`README.md` and must not import the production module's private helpers.

- **B′.** An endpoint-cell oracle.
  - The cells are every endpoint as a point, plus every open cell between consecutive endpoints and the two
    unbounded outer cells.
  - Membership in W, C, W∩C and W∖C is decided per cell with `fractions.Fraction`.
  - Compare the production outcomes, feasible/uncovered unions and `determined_by` on every fixture and on
    small random unions.
  - Metamorphic properties: input permutation and duplication don't change outputs; widening C never removes
    feasibility or adds uncovered cells; `nominal` never changes existence or full_window.
- **C′.** A breadth-first explorer over an explicitly materialized node graph, (state, valuation) pairs with
  explicit edges.
  - Build it from a separately written evaluator over the same fixtures. Use `entail._holds` for literal
    evaluation only.
  - Compare reachability, gaps, competing pairs, prohibition and invariant violations, and termination on tiny
    models.
  - Reordering transitions and duplicating equivalent rules must not change truth values.
  - Terminal, dead-end, cycle and infeasible-target cases are mandatory.
- **D′.** Enumerate all 2^n outcome vectors for n ≤ 10 and sum exact product probabilities over vectors with
  at least k successes. Don't call any production helper.
  - Check normalization (k = 0 gives 1), k = n+1 gives 0, monotonic decrease in k, and monotonic increase in p.
  - STA-1: n=2, k=2, p0=1/2, p1=3/4 gives 1/4 and 9/16. With k=1 it gives 3/4 and 15/16.
