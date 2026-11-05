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

**R1. Per-claim support gating, confirmed by Rohan on 2026-11-04 ("per-claim on public path too").**
- Operators return per-claim rows naming what decided each row: `determined_by` roles for schedules, and
  `standing`/`determining_ids` for policies.
- The gate owner, `signals.evaluate`, adds a `claim_admission` row per claim, with fields `id`, `claim`,
  `outcome`, `support`, `admission` and `effective_outcome`.
- A claim-kind signal may carry `role_support`, `{role: [support ids]}`, in the public request.
  - A row is gated only by its deciding roles' support. An unbound role, or a row naming no roles, uses all of
    the signal's support.
  - A policy row's own rule standing also gates it, so a proposed prohibition doesn't hide known coverage.
  - An undecided row is `undetermined`.
- The whole-signal code remains the conservative summary.
- Managed sessions use exactly this path, because packet E emits `role_support` on each child signal. There
  is one gate, not two.
- A known `outside_window` is therefore admitted while a proposed collection plan stays unresolved (TIM-4,
  EPI-2).
- The pure decision `signals.claim_admission_state`: CrossHair `--report_all` reports "Not confirmed" for its
  contracts. It found no counterexample but proved nothing over all paths. It is not yet pinned.

**R3 and C6 readings confirmed by Rohan (2026-11-04).**
- R3: all three binomial assumptions are required for application; the arithmetic is always shown.
- C6: terminal states are exempt from coverage and exclusivity only; two or more enabled transitions are
  always competing; inputs are re-chosen freely at each step; `policy_state` may be used in guards and
  constraints.

**Adoption editions confirmed by Rohan (2026-11-04).**
- Adoption belongs to one definition edition (an exact object id and version). Changing governed content
  (everything except origin, standing, adoption support and the version label) needs a new version. Every
  revision path enforces it: `--edits`, `--session`, MCP `reason_revise` and a direct canonical revision all
  refuse `changed_protocol_object_version_required:<object id>`.
- An explicit instruction to change an adopted plan records the new version and its adoption together, with no
  second confirmation. The `--edits` shortcut does this mechanically when an adopted object gets a new version
  under a newly attributed `user_choice` origin and its support was not edited. It adds
  `adopt:<id>:<new version>` under that origin, with the earlier records' weakest standing, and rebinds only
  that object's support. Both edits are listed in the review as `adoption_of_instructed_version`.
- A what-if (`hypothesis` origin) never adopts, and a reused origin does not re-adopt. The earlier adoption then
  reads as stale. Unchanged objects keep their adoption. Wording or attribution changes outside the governed
  definition preserve adoption, and stay visible as changed warrants.
- A stale application is object-specific (`stale_adoption:<object>:<premise>`). One shared record can be
  current for one object and stale for another without either application overwriting the other. Only the
  stale object's deciding roles are withheld, and receipts keep the original premise id.

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

**R6. C10 ceilings fit together.**
- Each guard is evaluated only at valuations of its own from-state, so guard work is at most V·T, which is
  4096 × 128 = 524,288.
- The policy reservation is `S·V·(K+P+I) + V·T`. It doesn't charge S·V·T, because C10 forbids overcharging
  when a smaller safe bound is known.
- Policies that still exceed the 1,000,000 protocol-work ceiling return `limit`, with reserved and actual
  work, rather than refusing or partially succeeding.

**R6b. Internal support without relabelling (corrected after the side-agent review).**
- The first correction made packets C and D report `proposed` for missing, unresolved or conflicting internal
  support. That changed what `proposed` means, which C1.1 and P2 reserve for Rohan. It was not clerical.
- Corrected:
  - `signals.evaluate` accepts an optional `support_resolution` beside `support_status`.
  - Operators report the true weakest declared status and the worst declared resolution (a missing binomial
    role makes it unresolved).
  - The existing gate refuses through its existing channels, `proposed_refused` and `binding_unresolved`.
- No standing word changes meaning, and no new status word exists.

**R7. Staged freeze: a coordinator deviation from P2, reported to the user at release.**
- P2 requires all of 1.1–1.6 before any worker starts.
- The coordinator releases B, C and D, their independent oracles, and A once `operators.md` and `ledger.md` are
  frozen. Task 1.3 (the Serena producer/consumer trace for shared integration owners) and `projections.md` are
  finished during wave 1, before any shared-path integration and before E or F start.
- P2's purpose, that no worker codes against an unfrozen interface, still holds for every packet.
- The P4 "production consumers" for B, C and D are the coordinator's wave-2 work: `signals.MODULES`
  registration and the managed per-claim check.

**R8. Fixture disputes.**
- The fixtures are hand-derived by the coordinator, except the binomial tails, which the generator computes.
- If a fixture disagrees with the contract text, the builder stops that case and reports it. Never make the
  code match the fixture against the text, and never edit fixtures.
- Oracle authors first run their oracle against the fixture expectations without importing production code,
  and report any mismatch in their handback.

**R9. Commits in a shared checkout.**
- The gate reads the whole working tree. Commits and pushes happen only between waves, when no worker is
  writing, or the gate runs on a clean export of the commit.

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
