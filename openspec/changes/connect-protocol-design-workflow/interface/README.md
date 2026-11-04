# Interface packet for `connect-protocol-design-workflow`, wave 0 (interface v1)

The coordinator owns this folder. It is the frozen basis that worker packets build against. Builders may read
it but never edit it. Report a gap as a factual case instead.

| File | Contents | Tasks |
|---|---|---|
| `README.md` | Pass brief, wave-0 resolutions, ownership and import rules, wave plan | 1.1, 1.6 |
| `baseline/` | Baseline at main 25c6bb5: environment, v1 example fingerprints, v1 lifecycle, the two starting counterexamples reproduced through the public CLI | 1.1, 1.2 |
| `operators.md` | Frozen contracts for `schedule_coverage`, `finite_policy` and `binomial_design`, with work-reservation formulas and oracle obligations | 1.4, 1.5 |
| `ledger.md` | Frozen protocol-object/check/section validator contract (packet A) | 1.4 |
| `projections.md` | Packet E projection registry, C8 option shapes and clinical-view fixtures | 1.3, 1.4 (frozen before E and F start) |
| `fixtures/` | Generator plus acceptance fixtures (`schedule.json`, `policy.json`, `binomial.json`, `rationals.json`) | 1.4 |
| `../../../../TrialLedger/layer2/protocol_numbers.py` | Coordinator-owned shared rational/union syntax, with tests in `tests/test_protocol_numbers.py`. All 9 tests pass; CrossHair `--report_all` confirms all 6 contracts over all paths | 1.4 |

## 1.1 Pass brief

**Clinical question.**
- Can a clinical-development person, working through their assistant, check explicit endpoint, assessment,
  efficacy and safety design choices?
- Can they see which requirement, source or choice decides each consequence?
- Can they compare two concrete plan edits, and hand a colleague a decision list plus a schedule of
  assessments without any invented premise?

**Starting counterexamples, reproduced at 25c6bb5 through the public CLI (`baseline/counterexamples/`).**
- `signals`/`temporal` with an assessment in [77,91] and collection through day 80 returns `consistent`, with
  bounds [77,80]. It never says that the protocol's full permitted window is unsupported.
- A valid `signals` analysis used as a decision alternative is refused with
  `alternative_requires_exact_entailment_query`. Supporting analyses cannot be options.

**Existing logic, reused unchanged.**
- The `signals` operator contract and support gate (`signals.evaluate`, `support_state`).
- `graph_evidence` temporal, `dependency_evidence`, `estimand_evidence`, and `decision_tables` (including
  prohibitions and case witnesses).
- `definition_checks` bound to actual analysis request/result addresses.
- Managed replay (`session_state.prepare`, `design_session`), immutable artifacts, compact reading, revision
  `answer_diff`, and export.
- Multistage scope: rerunning the previous TRD eligibility session at HEAD without an explicit entry context
  now classifies its decisions as design_choice, settled_within_declared_alternatives (twice) and
  unrepresented_design_question. At 33cb080 all four were evidence_question. SCP-1 is therefore regression
  protection for the v2 path.

**Missing wiring, which this change builds.**
- Typed v2 protocol objects.
- Exact set coverage for schedules.
- Finite-state policies (finite tables only check a single decision today).
- An exact binomial calculation.
- Named projections from objects into the existing operators.
- Per-claim support gating.
- Protocol-option decisions that aren't exact entailment queries.
- v2 preparation and discovery.
- A clinical protocol view, a protocol synopsis and a schedule-of-assessments sheet.
- Revision axes for these.

**Deferred and not claimed.**
- Automatic clinical prose encoding.
- General statistical design (survival, adaptive, multiplicity, sample-size search).
- Ranking and significance.
- The autonomous complete protocol writer (`add-design-synthesis` tasks 5–12).

## Wave-0 resolutions (clerical; no clinical meaning changed)

**R1. Per-claim support gating (C4's "retain equivalent per-claim admission records").**
- Operators return per-claim rows naming the inputs or rules that decided each row: `determined_by` for
  schedules, and `determining_ids`/`standing` for policies.
- The coordinator applies the existing `signals.support_state` gate per claim, over only those inputs'
  supports.
- The public `signals` operation still uses its single conservative whole-signal gate.
- This is how a known `outside_window` survives an unknown or proposed collection plan (TIM-4, EPI-2).

**R2. C6 field naming and the reserved state.**
- C6's `variables` keeps its name, and each entry uses the decision-table domain shape.
- `policy_state` is a reserved equality literal whose value is the current state. It may appear in guards,
  constraints and conditions. Callers can never declare or supply it.
- This makes C6's transition-target conflict expressible.

**R3. Efficacy assumptions.**
- C3's efficacy `assumptions` become `{role, premise}` pairs, so that roles (fixed_n, iid_binary, alignment)
  are declared rather than inferred.
- Packet E projects them into C7's role-tagged standing references, carrying each premise's actual standing.
- A missing role is a named blocker with the arithmetic retained (STA-4).

**R4. Claim and outcome names C5–C7 left open.**
- Schedule: `no_feasible_time`, `uncovered`, `unknown_target`, plus per-claim `determined_by`/`missing`.
- Policy: `not_executed`, `not_established` with `reasons`.
- Binomial: `computed`/`satisfied`/`not_satisfied`/`unsupported_method`/`limit`.
- Witness caps travel in policy claims (`witness_limit`), because C6 has no limits field.

**R5. One shared syntax owner.**
- Rational and union parsing lives once, in `protocol_numbers.py`, which the coordinator owns. Packets A, B
  and D import it.
- This avoids three copies of C5 syntax built by three parallel agents.

**R6. C10 ceilings fit together.** Guard evaluations are at most 4096 × 128 = 524,288. Policies that exceed
the 1,000,000 protocol-work ceiling once constraints and rules are counted return `limit`, keeping their
reserved and actual work, rather than refusing or partially succeeding.

**R7. Staged freeze (process; the user approved the waves on 2026-11-04).**
- P2's rule that no worker codes against an unfrozen interface is kept per packet.
- B, C and D, their independent oracles, and A start once `operators.md` and `ledger.md` are frozen.
- E and F start only after `projections.md` and representative result fixtures are frozen.
- Coordinator task 1.3 (the Serena producer/consumer trace for shared integration owners) is completed during
  wave 1, before any shared-path integration.

## Ownership (P3) and import direction (P2.4)

| Packet | Model | Sole writable paths | Builds against |
|---|---|---|---|
| A | Sonnet | `TrialLedger/layer2/protocol_objects.py`, `tests/test_protocol_objects.py`, `interface/fixtures/objects.json` | `ledger.md` |
| B | Haiku | `TrialLedger/layer2/protocol_schedule.py`, `tests/test_protocol_schedule.py` | `operators.md` §B, `fixtures/schedule.json` |
| B′ (oracle) | Haiku | `tests/test_protocol_schedule_oracle.py` | `operators.md` §B and oracle section; must not read `protocol_schedule.py` |
| C | Sonnet | `TrialLedger/layer2/protocol_policies.py`, `tests/test_protocol_policies.py` | `operators.md` §C, `fixtures/policy.json` |
| C′ (oracle) | Haiku | `tests/test_protocol_policies_oracle.py` | `operators.md` §C and oracle section; must not read `protocol_policies.py` |
| D | Haiku | `TrialLedger/layer2/protocol_statistics.py`, `tests/test_protocol_statistics.py` | `operators.md` §D, `fixtures/binomial.json` |
| D′ (oracle) | Haiku | `tests/test_protocol_statistics_oracle.py` | `operators.md` §D and oracle section; must not read `protocol_statistics.py` |
| E | Sonnet (wave 2) | `TrialLedger/layer2/protocol_projections.py`, `tests/test_protocol_projections.py` | `projections.md` |
| F | Sonnet (wave 2) | `TrialLedger/layer2/protocol_view.py`, `tests/test_protocol_view.py` | `projections.md`, canonical result fixtures |

**Import direction:**
- The operator modules (B, C, D) import only what `operators.md` allows. They never import session,
  transport, acquisition or presentation modules.
- `protocol_objects` (A) never imports `session_state`/`design_session` or any operator.
- `protocol_projections` (E) may call A and the operators. It never copies their mathematics.
- `protocol_view` (F) reads canonical results only. It never runs a solver or supplies a premise.
- Shared paths, including discovery, `signals.MODULES` registration and every existing test, belong to the
  coordinator.

**Test discipline:**
- A worker runs only its own test file, plus `tests/test_protocol_numbers.py`, with `.venv/bin/pytest -q <file>`,
  and ruff check/format on its own files. The full suite (6,793 tests, about 2 minutes) is coordinator-only.
- Workers never run Detective, never commit, never touch git state and never install dependencies.

## Acceptance-ID map for wave 1

| Acceptance ID | Owning test files |
|---|---|
| TIM-1, TIM-2, TIM-3, TIM-4, TIM-6 (operator part) | `test_protocol_schedule.py`, `test_protocol_schedule_oracle.py` |
| POL-1 through POL-7 (operator part) | `test_protocol_policies.py`, `test_protocol_policies_oracle.py` |
| STA-1 through STA-4 (operator part) | `test_protocol_statistics.py`, `test_protocol_statistics_oracle.py` |
| EPI-1 (raw calculation kept beside proposed standing) | the policy and binomial fixtures above |
| C3 admission (duplicate, dangling, cyclic, malformed, scope, origin) | `test_protocol_objects.py` |
| TIM-5, END-*, EPI-2/3, SCP-*, DEF-*, OPT-*, REV-1, OUT-*, LIM-1, CMP-1 | Coordinator and packets E/F in waves 2+ |

## Wave plan

1. **Wave 1** (this release): A, B, B′, C, C′, D and D′ in parallel. Meanwhile the coordinator does task 1.3
   and freezes `projections.md`.
2. **Coordinator integration of slice 2.** v2 admission and replay, schedule registration, per-claim gating
   (R1), preparation/discovery for the slice, the full suite, and the V6 neurological walkthrough.
3. **Wave 2:** E and F, plus independent test authors for OPT/REV/OUT cases. The coordinator integrates slices
   3 and 4 (policy and efficacy), with their walkthroughs.
4. **Slices 5–6** (coordinator: alternatives, revision, delivery). Cheap agents do review and author test files.
   Proof runs happen one at a time on frozen code.
