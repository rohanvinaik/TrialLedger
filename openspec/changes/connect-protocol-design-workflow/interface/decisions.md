# Frozen slice-5 interface: protocol alternatives (C8) and revision axes (C9, REV-1), interface v1

This instantiates C8 and the C9 revision clause for the coordinator's implementation in `design_session` and
`session_state`, and for the independent test authors who write the acceptance tests first. Contracts C1, C4 and C8
govern. Everything here goes through the public `design_session` request on a v2 session.

## Decision shape (v2)

A v2 session's `decisions` may mix legacy query decisions (unchanged) and protocol decisions. A protocol decision is
exactly:

```text
{kind: "protocol_options", id, question, target, coverage, selected, alternatives, evidence?}
```

- `target`, `coverage`, `selected` and `evidence` use the existing decision field contracts. `coverage` must be
  `declared_design`.
- `alternatives` holds 2 to 16 entries, each exactly `{id, label, replace_objects, checks}`:
  - `replace_objects` is a list of 0 to 16 **complete** v2 protocol objects (the C3 envelope). Each `id` must
    already exist in the session protocol, with the **same `kind`** and the **same `scope.target`**. An empty
    list means "the baseline as declared".
  - `checks` is a unique list of declared check ids.
- **Every alternative must list every session check that has `required: true`** and whose `scope.target` equals
  the decision's target. Optional context checks (`required: false`) listed by any alternative must be listed
  by all of them. At least one required check must exist.

**Refusal codes** (translation refusals; the whole request is refused):
- `protocol_option_fields`
- `protocol_option_count` (fewer than 2 or more than 16 alternatives)
- `protocol_option_unknown_object`
- `protocol_option_kind_changed`
- `protocol_option_target_changed`
- `protocol_option_unknown_check`
- `protocol_option_missing_required_check`
- `protocol_option_context_mismatch`
- `protocol_option_no_required_check`
- `protocol_option_coverage`
- any `protocol_*` code from re-validating a candidate protocol, such as a malformed replacement object

A replacement may never be a source object, add or delete an object, or change which checks are required.

## Candidate frames

Each alternative is evaluated **freshly** on a detached candidate:
1. Start from the baseline protocol.
2. Replace the listed objects simultaneously.
3. Re-validate with `protocol_objects`.
4. Project and run exactly the alternative's checks through the ordinary budgeted child path.

The baseline's own `result.protocol` is unchanged and retained separately. No baseline child result is reused.

**`frame`.**
- `fixed` when `replace_objects` is empty.
- Otherwise `hypothetical`. Every replaced object is a local assumption of that frame. Only its own object
  entry counts as assumed-accepted inside the frame.
- Its support premises, unchanged objects, applicability proofs and model assumptions keep their real
  standing. Proposed external evidence is never lifted.

The rest of the alternative row:
- `assumption_refs`: the replaced object ids, sorted.
- `unconditional_application`:
  - `admitted` only for a fixed frame whose required checks are all compatible;
  - otherwise `withheld`.
- A hypothetical result is worded "if you choose this plan, these checks follow".

## Per-check outcome inside a frame

For each listed check, `check_code` is one of the following, first match:

| check_code | When |
|---|---|
| `not_applicable` | Every claim row's application is `not_applicable` |
| `violated` | Any claim row is admitted (in-frame) and its outcome is a failure: a policy failure, schedule gap, unmet binomial target, or a non-claim signal whose admitted code is conflict/inconsistent/violated |
| `undetermined` | Any applicable claim row is unadmitted or undetermined; or the projection is unresolved; or the method is not computed; or the code is `limit`; or the child was refused |
| `satisfied` | Otherwise |

In-frame admission means the gate's ordinary admission, except that an assumed object's own entry counts as
accepted.

**Conditional claims** (settled after the side-agent review, consistent with Rohan's earlier acceptance):
- An admitted claim whose application is `conditional` is a checked conditional obligation, **not**
  undetermined. Its success satisfies the check and its failure violates it.
- Check rows list `conditional_claims`, and alternatives list `conditional_checks`, so the condition stays
  visible.
- A post-discontinuation visit therefore cannot stall a comparison.

## Alternative aggregate

`compatibility` is one of:
- `incompatible_under_declared_checks`: any **required** check is `violated`;
- `undetermined`: otherwise, any required check is `undetermined`;
- `compatible_under_declared_checks`: every required check is `satisfied` or `not_applicable`, and at least one
  is `satisfied`.

Optional context checks never change `compatibility`; they are reported beside it. There is no voting, and never
`safe`, `effective`, `optimal` or `complete`.

Each alternative row is exactly:

```text
{id, label, frame, assumption_refs, unconditional_application, compatibility, conditional_checks,
 checks: [{id, required, check_code, conditional_claims, claims, children}], candidate_digest}
```

- `claims` holds each claim's id, claim, outcome, admission, application and finding_status.
- `children` holds each child's request_digest and result_digest.
- `candidate_digest` is the digest of the candidate protocol.

## Decision disposition (separate from compatibility)

The protocol decision row is `{id, kind, question, target, coverage, selected, alternatives, disposition,
selection}`. `disposition` is, first match:

| disposition | When |
|---|---|
| `blocker` | A **selected** alternative is `incompatible_under_declared_checks`. Selection never erases a blocker (OPT-3) |
| `design_choice` | At least two alternatives are `compatible_under_declared_checks` and their `candidate_digest`s differ. Labels never prove distinction |
| `evidence_question` | Otherwise, any alternative is `undetermined` |
| `settled_within_declared_alternatives` | Exactly one alternative is compatible |
| `no_compatible_alternative` | Otherwise |

`selection` is the existing attributed `selected` block, retained verbatim. It never changes compatibility or
admission.

## Revision axes for protocol results (C9, REV-1)

`answer_diff` gains two fields, `protocol_checks` and `protocol_decisions`. Each compares the before and after
protocol results, both freshly replayed, and holds rows `{id, code, axes}`, the established answer_diff row shape.
Every consumer (summary counts, compact paging) reads `code`. This was corrected at integration from a nested
`protocol: {checks, decisions}` shape that existing consumers could not read.

- `code` uses the existing `change_code`: new, withdrawn, unchanged, changed or absent.
- `axes` is a sorted subset of `verdict`, `requirements`, `support`, `origin`, `scope_model`, `wording` and
  `input`:

| Axis | Changes when |
|---|---|
| `verdict` | Any claim's `effective_outcome` or `application` changed, or a decision's alternative `compatibility` or `disposition` changed |
| `requirements` | A claim's `admission` changed while its `effective_outcome` did not |
| `support` | A claim's `support` or `determining_ids` changed, or a child's role_support changed |
| `origin` | An involved object's `origin` changed |
| `scope_model` | An involved object's `scope` or `version` changed, or a check's `scope` changed |
| `wording` | Only labels or question text changed |
| `input` | The request_digest changed with none of the above |

- A digest change alone is only `input`.
- `wording` alone never implies a changed verdict.
- A residual-only change, `requirements` without `verdict`, is never reported as a verdict change.
- Both snapshots are replayed freshly. Mixed v1/v2 revisions stay refused.

## Integration clarifications (coordinator, after the test authors' handoffs)

1. **Location.** Protocol decision rows are in `result.protocol.decisions`. Legacy query decisions stay in
   `result.decisions`, and their revision rows stay in `answer_diff.decisions`. `answer_diff.protocol_decisions`
   lists only `protocol_options` decisions.
2. **Assumption standing.** An alternative's claim rows carry `assumed`, the sorted assumed support-entry ids
   the claim rests on. When `assumed` is non-empty, `finding_status` is `proposed`. In-frame admission still
   counts for `check_code`, but a local assumption is never reported as known (OPT-4).
3. **Identical compatible candidates.** Two compatible alternatives with identical `candidate_digest`s are not a
   design choice. The table's order then gives `evidence_question` if any alternative is undetermined, otherwise
   `settled_within_declared_alternatives`.
4. **Schedule gaps.** `uncovered`, `not_collected`, `outside_window`, `no_feasible_time` and `no_permitted_time`
   are the schedule failure outcomes that make a check `violated`.

## Repair choices in comparisons (Rohan, 2026-11-04: "new 'repair choice' result")

Schedule gaps (`no_feasible_time`, `no_permitted_time`, `outside_window`, `not_collected`, `uncovered`) and an
unmet binomial target (`not_satisfied`) are the person's repair choice in comparisons too, as in the clinical
labels.

**Precedence.** These supersede the earlier tables where they differ.

- **`check_code`**, first match:
  1. `not_applicable`
  2. `violated`: an admitted policy failure (gap, competing, violation, not_established, inconsistent_domain), or
     an admitted conflict/inconsistent/violated code from an existing operator
  3. `undetermined`
  4. `repair_choice`: an admitted schedule gap or unmet binomial target
  5. `satisfied`
- **`compatibility`** over the required checks, first match:
  1. `incompatible_under_declared_checks` (any violated)
  2. `undetermined` (any undetermined). Missing knowledge outranks a known repair
  3. `repair_choice_open_under_declared_checks` (any repair_choice)
  4. `compatible_under_declared_checks` (at least one satisfied)
- **`disposition`**, first match:
  1. `blocker`: the selected alternative is incompatible
  2. `repair_choice`: the selected alternative is repair_choice_open
  3. `design_choice`
  4. `evidence_question`
  5. `settled_within_declared_alternatives`
  6. `repair_choice`: no compatible alternative, but at least one repair_choice_open
  7. `no_compatible_alternative`

A selected plan with a visit-window gap therefore reads "repair choice", never "blocker". A selected plan whose
admitted dosing policy violates its own prohibition is still a blocker.
