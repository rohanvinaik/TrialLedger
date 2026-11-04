# Frozen slice-6 interface: protocol delivery (C9, OUT-1, OUT-2), interface v1

One pure view, `protocol_view.view(result)`, plus the protocol decision rows, feeds every output: the compact reply,
`decision-list.md`, and the review workbook (`design-review.xlsx`). Nothing is recomputed in delivery.

**Acceptance blockers** (OUT-1, and the PAH cold audit):
- A known conflict or repair choice must survive into every readable output, beside coverage, with its deciding
  support and result reference.
- Truncation must name what it omitted and where it is retained.
- No raw JSON in clinical cells; source workbooks stay untouched.

## Compact reply (`reason ... --compact`, MCP `response_view: compact`) for a v2 design_session

A new key `protocol`:

```text
{canonical_ref: "/response/result/protocol",
 sections: [{id, declared, coverage, findings, findings_text}]     # all eight, never paged
 findings: [{kind, check, claim, text, ref}]                         # paged; ordered as below
 checks:   [{id, kind, required, code, conflicts, repairs, conditional}]   # paged
 decisions: [{id, disposition, alternatives: [{id, label, compatibility}]}]
 pages: {findings: {...}, checks: {...}}                             # the existing compact page shape
 omitted: {findings: n, checks: n}}
```

- `findings` are the view's `open_items`, re-ordered: admitted conflicts first, then repair choices, then
  unresolved projections, not-computed, refused or undetermined, conditional, and finally sections.
- Paging uses the existing compact budget. Omitted rows are counted and reachable through `reason-result` at
  their `ref`.
- `conflicts` and `repairs` count each check's admitted conflict and repair-choice claims.

## Decision list (`decision-list.md`)

The `## Protocol` section comes after the existing decisions and contains, in this order:
1. `### Sections`: a table `Section | Declared | Coverage | Findings`, with all eight sections.
2. `### Findings`: one sub-list per check, headed `Check <id> (<kind>, required|optional)`.
   - One bullet per claim: `<claim>: <wording> — standing <standing>; result <ref>`.
   - One bullet per existing-operator finding code.
3. `### Schedule of assessments`: a table
   `Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted |
   Collection | Feasible | Gap | Nominal outcome`.
4. `### Plan comparisons`, per protocol decision:
   - its question;
   - `Disposition: <disposition>`;
   - a table `Alternative | Label | Frame | Compatibility | Conditional checks | Application`.
5. `### Open items`: a numbered list, in the compact `findings` order.
6. `### Limits`: the view's `limits_of_claim`.

The existing `## Changes` section also lists `protocol_checks` and `protocol_decisions` rows, as
`<id>: <code> (<axes>)`.

## Workbook sheets (added to the existing review workbook only)

- `Protocol synopsis`: `Section, Declared, Coverage, Findings, Findings text, Reasons, Objects, Checks`.
- `Protocol findings`, one row per claim or operator finding: `Check, Kind, Required, Claim, Outcome, Effective
  outcome, Admission, Application, Standing, Arithmetic standing, Applicability standing, Wording, Determining
  references, Result reference`.
- `Schedule of assessments`: `Check, Assessment, Collection, Cohort, Arm, Phase, Conditionality, Measurement, Mode,
  Anchor, Unit, Nominal target, Permitted window, Collection availability, Feasible window, Full-coverage gap,
  Nominal outcome, Standing, Origin, Result reference`.
- `Plan comparisons`: `Decision, Question, Disposition, Alternative, Label, Frame, Compatibility, Conditional
  checks, Assumptions, Application`.
- **Cell content.** Every cell is clinical text or a number. Lists are joined with "; ". A standing map renders as
  `assessment: known; collection: proposed`, and an origin as `user_choice: <ref>`. A reference cell holds the
  canonical address.
- The `Changes` sheet gains protocol rows.

## MUST-NOT (for the output tests)

- An admitted conflict or repair choice present in `result.protocol` must not be missing from the compact reply
  (directly or as counted omitted), the decision list, or the workbook.
- No cell or line says safe, valid, complete, adequate or approved.
- The permitted window is never replaced by the feasible window.
- A refused claim's raw outcome is never shown as its effective outcome.
- No JSON object text appears in a clinical cell.
- `landscape.xlsx` and other source workbooks are byte-identical after export.
