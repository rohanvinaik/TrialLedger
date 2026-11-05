# Frozen view interface: packet F, the clinical protocol view (interface v1)

This instantiates the C9 view, design decision 8 and OUT-1/OUT-2. A pure function turns one canonical v2
`design_session` result into clinical rows. Compact replies, the decision list and the workbook will all consume
those rows; that consumption is coordinator work in slice 6. The view **reasons about nothing**. It never runs a
solver or operator, never reads files, never interprets prose, and never supplies a premise. It only arranges
fields that are already present and renders exact values as text.

## Module and signature

The module is `TrialLedger/layer2/protocol_view.py`. Its tests are `tests/test_protocol_view.py`.

```python
view(result: dict) -> dict      # result = a v2 design_session `result` (the replay output), with a "protocol" key
```

- Without a `protocol` key, the view raises `ValueError("view_not_protocol_result")`.
- Allowed imports: `copy`, `json`, `fractions`, `typing`, and `TrialLedger.layer2.protocol_numbers` (`render`
  only).
- No other TrialLedger module. Add `protocol_view` to the static import contract; the coordinator owns that
  file.

**Inputs are the frozen fixtures** in `fixtures/results/*.json`, each `{"request", "result"}`. They are produced
by the real public operation (`build_result_fixtures.py`). Read the shapes from them:
- `result.protocol` holds `objects`, `sections`, `checks` and `limits_of_claim`.
- `result.protocol.checks[*]` holds `id`, `kind`, `required`, `scope`, `objects`, `projection`, `children`,
  `unresolved` and `not_computed`.
- `checks[*].children[*]` holds `id`, `receipt`, `request`, `result`, `request_digest`, `result_digest`,
  `signals`, `refusal` and `conditions`.
- `children[*].signals[*]` holds `id`, `kind`, `code`, `calculation_code`, `status`, `admission`, `blockers` and
  `claim_admission`.
- Each `claim_admission` row holds `id`, `claim`, `outcome`, `support`, `admission`, `effective_outcome` and
  `application`.

## Output: exactly these keys

```text
{"schema_version": 1,
 "sections": [...], "checks": [...], "schedule": [...], "open_items": [...], "limits_of_claim": [...]}
```

### `sections`

All eight, in the order population, eligibility, interventions, endpoints, assessments, efficacy, safety,
exploratory. Each row is `{id, declared, coverage, reasons, objects, checks}`:
- `declared` is the result's section state: requested, not_applicable or not_requested.
- `checks` lists the ids of checks consuming any of the section's objects, in check order.

**`coverage`.** The first matching rule wins:

| Rule | Coverage | Reasons |
|---|---|---|
| declared not_requested | `not_requested` | `[]` |
| declared not_applicable | `not_applicable` | the declared `basis` |
| requested with no objects | `open` | `["no_objects_declared"]` |
| any consuming check has `not_computed`, a `limit` signal code, or any claim outcome `not_executed` | `not_computed` | `"not_computed:<check id>"` |
| any consuming check has `unresolved` entries, or any claim row whose `effective_outcome` is `unresolved`, `unknown_target` or `undetermined` (a `conditional` application no longer opens the section; see integration correction 4) | `open` | one reason per cause, e.g. `"unresolved:<check id>:<code>"`, `"claim_unresolved:<check id>:<claim id>"` |
| requested with objects but no consuming check | `open` | `["no_check_declared"]` |
| otherwise | `specified` | `[]` |

`specified` means "represented and checked as declared". A requested section whose checks found a violation is
still `specified`; the violation appears in `checks` and `open_items`. No field, value or wording may ever say
complete, safe, valid, adequate or approved.

### `checks`

One row per check, in check order: `{id, kind, required, projection, summary, claims, findings, unresolved,
not_computed, conditions, refs}`.
- `summary` is `{code, calculation_code, admission}`, taken from the child signal. With no child signal it is
  null.
- `claims` holds one row per `claim_admission` row:
  `{id, claim, outcome, effective_outcome, admission, application, standing_support, wording}`.
  - `standing_support` is the row's `support` id list, unchanged.
  - `wording` is a fixed template from the **wording table** below, chosen by `(claim, effective_outcome)`.
    Refused rows use the refusal template, whatever the outcome. Conditional rows put
    `"If the declared condition applies: "` in front of the template.
- `refs` is `{"result": "/protocol/checks/<i>/children/<j>/result", "request_digest": ..., "result_digest": ...}`
  for each child.

**Wording table.** Exact strings. Use an f-string only where a placeholder is shown.

| claim | effective_outcome | wording |
|---|---|---|
| existence | satisfied | "At least one permitted assessment time falls within planned collection." |
| existence | no_feasible_time | "No permitted assessment time falls within planned collection." |
| existence / full_window | no_permitted_time | "The permitted window is empty, so no assessment is permitted." |
| nominal | satisfied | "The nominal target is inside the permitted window and within planned collection." |
| nominal | outside_window | "The nominal target is outside the permitted window." |
| nominal | not_collected | "The nominal target is inside the permitted window but outside planned collection." |
| nominal | unknown_target | "No nominal target is declared." |
| full_window | satisfied | "Planned collection covers every permitted assessment time." |
| full_window | uncovered | "Planned collection does not cover part of the permitted window: {uncovered}." |
| coverage | covered / gap | "Every reachable declared situation has a rule." / "{n} reachable declared situation(s) have no rule." |
| exclusivity | exclusive / competing | "No reachable declared situation enables more than one rule." / "{n} reachable declared situation(s) enable more than one rule." |
| prohibition | clear / violation / not_declared | "No declared prohibition is violated in reachable declared situations." / "{n} declared prohibition violation(s) in reachable declared situations." / "No prohibition is declared." |
| invariant | holds / violation / not_declared | "Every declared invariant holds in reachable declared situations." / "{n} declared invariant failure(s)." / "No invariant is declared." |
| termination | all_paths_terminate / not_established | "Every permitted path in the declared model reaches a terminal state." / "Termination is not established in the declared model: {reasons}." |
| null_rejection_probability / power | satisfied / not_satisfied | "The exact {quantity} {computed} meets the declared bound {comparison} {value}." / "...does not meet..." |
| any | unresolved, with admission `undetermined` | "Not determined: an input this claim needs is not declared." (added at integration; an undecided row is not a refusal) |
| any | unresolved, with any other admission (a refused row) | "Not applied: the deciding support is {admission}." |
| any | not_executed | "Not computed within the declared work limit." |

- `{n}` is the claim row's `violations_found`. Read it from the child `result` at the result address of the
  matching claim row in the signal value (`.../result/signals/0/value/claims/<k>`), with the same claim id.
- `{reasons}` joins the termination reasons with ", ".
- `{uncovered}` is the interval text (below).
- `{quantity}` is "null rejection probability" or "power".
- `{computed}` is the canonical rational, followed by its display decimal in brackets, for example
  `"1/4 (0.2500)"`.
- Any `(claim, outcome)` pair not in the table renders as `"Outcome: <outcome>."`. A test must show that the
  table covers every outcome in every fixture.

### `schedule`

One row per schedule check (the C9 schedule-of-assessments columns), in check order. Each row is exactly:

```text
{check, assessment, collection, cohort, arm, phase, conditionality, measurement, mode, anchor, unit,
 nominal, permitted, availability, feasible, full_coverage_gap, nominal_outcome, standing, origin, refs}
```

- `cohort`, `arm` and `phase` come from the check's `scope.context`. Null renders as `"all (open)"`.
- `conditionality` is `"conditional"` when the child has `conditions`, otherwise `"unconditional"`. A schedule
  check with no child is `"not projected: <codes>"`.
- `measurement` is the assessment's measurement id. `mode` is the collection's mode.
- `anchor` and `unit` come from the assessment.
- **Interval text.** `nominal`, `permitted`, `availability`, `feasible` and `full_coverage_gap` render exact
  values:
  - one interval is `[77, 91]` or `(80, 91]`; a singleton is `{91}`;
  - an infinite end is `-∞` or `+∞`;
  - a union is joined with `" ∪ "`;
  - an empty union is `"none"`;
  - null is `"unknown"`, or `"not computed"` when the claim wasn't requested.
- `feasible` and `full_coverage_gap` come from the operator value, at the child result's `/result/signals/0/value`
  existence and full_window rows. The original `permitted` window is always shown unchanged beside them.
- `standing` holds each object's own standing status, for example `{"assessment": "known", "collection":
  "proposed"}`.
- `origin` holds each object's `origin.kind` and `origin.ref`.

### `open_items`

One entry per item, in this order:
1. every `unresolved` projection entry;
2. every `not_computed` declaration (method, missing inputs);
3. every refused or undetermined claim;
4. every conditional claim;
5. every claim whose effective outcome is a failure (violated outcomes, open or conflict);
6. every `open`/`not_computed` section.

Each entry is `{kind, check, claim, text, ref}`, with `text` taken from the wording table or a fixed
`"<code>"` sentence. Nothing is merged, voted or ranked.

### `limits_of_claim`

The protocol result's `limits_of_claim`, plus exactly:
- `"Coverage and violations are over the declared variables, objects and claims only."`
- `"Rendered decimals are rounded displays; exact rationals are canonical."`

## Acceptance for packet F (direct-call tests in `tests/test_protocol_view.py`)

Every test body calls `protocol_view.view(...)` directly, by name.

**Positive.**
- For each fixture in `fixtures/results/`, assert the full section table, every check row's claim
  wording/application/admission, the schedule row for the schedule fixtures (TIM-1-like numbers:
  `permitted "[77, 91]"`, `availability "(-∞, 80]"`, `feasible "[77, 80]"`, `full_coverage_gap "(80, 91]"`), and
  open items:
  - work limit → section `not_computed`;
  - external method → `not_computed` with its missing inputs;
  - scope mismatch → `open`, with no schedule numbers and `conditionality "not projected: projection_scope_mismatch"`;
  - conditional assessment → `conditional` wording prefix and section `open`;
  - proposed prohibition → refused-row wording, while coverage stays covered;
  - an untouched section → `not_requested`.

**MUST-NOT.**
- No output string contains "complete", "safe", "valid", "adequate", "approved" or "medically". Write this as a
  recursive scan.
- A violated requested section is `specified`, not `open`, and its violation appears in `open_items`.
- The original permitted window is never replaced by the feasible interval.
- A refused claim's raw outcome is never shown as its effective outcome.
- A caller label (check or object id) never appears inside a computed wording template.
- The input result is not mutated (deepcopy compare).
- Calling `view` twice gives an identical value.
- Display decimals never decide anything; every comparison text uses the canonical rational.

## Integration corrections (coordinator, after the external review on 2026-11-04)

1. **Claim rows** also carry `standing` and `determining_ids`, taken from the gate's per-claim row. The view
   never reconstructs standing.
2. **Signals without claim rows** (estimand, dependencies, temporal, decision_table): `findings` holds
   `{signal, kind, code, calculation_code, admission, codes, ref}` per signal.
   - `codes` comes from `signal_finding_codes`: empty only when the signal is admitted, unchanged by the gate
     and blocker-free; otherwise every blocker, verbatim, or `code:<code>`.
   - Each code adds a `signal_finding` open item, and a section reason `signal:<check>:<code>`, so the
     section is `open`.
   - Previously an estimand collection-plan mismatch disappeared from the view.
3. **Section `findings`** (Rohan, 2026-11-04: "add a findings column"). Each section row adds `findings`,
   `findings_text` and `findings_detail` beside the unchanged C3 `coverage`. Only admitted rows count:

   | Label | When |
   |---|---|
   | `conflict_found` | Any admitted policy failure (gap, competing, violation, not_established, inconsistent_domain), or an admitted existing-operator code of conflict, inconsistent or violated |
   | `repair_choice_open` | Otherwise, any admitted schedule gap or unmet binomial target, or an admitted collection-plan mismatch |
   | `none_found_in_declared_checks` | Otherwise, when coverage is `specified` |
   | `not_checked` | Everything else |

   - A known prohibited-dose violation therefore reads "specified" **and** "conflict found", never "specified"
     alone.
   - Downstream outputs (the decision list and the workbook) must always show `findings` beside `coverage`.
4. **Conditional claims and applicability** (after the side-agent review).
   - A claim with `application: "conditional"` is a checked conditional obligation. It no longer makes its
     section `open`, and it stays visible through its wording prefix and a `claim_conditional` open item.
   - `application: "not_applicable"`, when the declared premises refute the condition, has the fixed wording
     "Not applicable: the declared condition does not hold in this scope." It is excluded from section findings.
   - Applicability is decided upstream by a check's explicit `condition_applicability` binding (task 2.9). It is
     never inferred.
5. **Applicability standing** (third external review).
   - Claim rows from the managed session carry `application_status` and `application_refs`: the weakest
     standing and deciding premise references of the applicability proof.
   - They also carry `finding_status`, the weakest of the arithmetic standing and the applicability proof.
   - The view's `standing` is `finding_status`. `arithmetic_standing` and `application_standing` stay separate,
     and `determining_ids` includes the applicability references.
   - When applicability rests on interpolated support, wording (including "Not applicable…") ends with
     "Applicability rests on interpolated support."
6. **Not-executed claims** (output test author, 2026-11-04). A claim whose effective outcome is `not_executed`
   (work limit) is an unsettled claim. It is listed as a `claim_unsettled` open item with the fixed wording "Not
   computed within the declared work limit." This is in addition to its section's `not_computed` coverage.
7. **Adoption** (explicit adoption records, decided by Rohan on 2026-11-04). The view adds `adoption`, one row per
   protocol object: `{object, kind, version, adopted_by, adoption_origins, adoption, object_standing}`.
   - `adoption` ∈ not_adopted, stale_version, adopted_known, adopted_interpolated or adopted_proposed, read only
     from declared adoption records and the `adoption_stale_version` entries.
   - The view now has seven keys.
   - Export adds a "Protocol adoption" sheet and an "Adoption" table in the decision list, so a reviewer sees who
     adopted each object version.
