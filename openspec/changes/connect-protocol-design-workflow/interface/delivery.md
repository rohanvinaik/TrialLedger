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

## Legibility amendments (2026-11-04)

Wording and rows only; no computed value, operator output, admission or revision logic changed. Every code stays
reachable (its own column, a parenthesis, or the "Open exact result" link).

- **Protocol findings** gains a first column `Kind of finding` (Conflict, Repair choice, Not computed, Not applied,
  Not determined, Conditional, Not applicable, Finding, No finding), from the view's existing conflict/repair split.
  Rows sort conflicts first. A check whose projection is unresolved or not computed emits one `Not computed` row
  (claim `(whole check)`, because the result does not retain declared claims of an unresolved check) and a
  matching `[Not computed]` bullet. Standing `null` renders `n/a`. Result reference is the artifact address plus
  pointer (hyperlinked "Open exact result"). Refused wording reads "the deciding premise is still a proposal".
  The md bullets gain a `[Kind]` prefix and count line plus a kinds legend.
- **Protocol synopsis** gains `Conflicts`, `Repair choices`, `Status`, `Reason codes`; `Reasons` is now words. A
  legend row follows the table.
- **Schedule of assessments**: unset cohort/arm/phase read `not stated (open)`. Interval, nominal and unit cells
  carry unit and anchor (`[77, 91] days from randomization`); nominal outcome is a sentence with its code.
- **Plan comparisons** gains `Disposition in words`, `Compatibility in words`, `Application in words`,
  `Selected by you (caller label)`, `Selection origin and basis (caller label)`, `Permitted window`,
  `Collection availability`, `Feasible window`, `Full-coverage gap`, `Claim outcomes under this alternative`.
  Windows come from each alternative's own retained `schedule` values
  (`decisions[].alternatives[].checks[].children[].schedule`), read by the view's shared builder
  (`window_texts`); "Not retained" appears only when `schedule` is absent or empty. No comparison reads
  "No plan comparison declared". The view's decision rows gain `selected`, per-alternative `windows` and
  `claim_outcomes`.
- **Protocol adoption** headings: `Adopted by (premise id)`, `Attributed to (caller label, not authenticated)`;
  new `Adoption in words`. The md table adds origin, words and object standing.
- **Changes**: protocol rows read `Changed (<axis words>)`, list per-claim before/after text from
  `answer_diff` `changes`, and sort with the other changed rows ahead of unchanged ones.
- **Findings (developer sheet)**: clinical text capped at 300 characters with the omitted count and the exact
  address; widths follow the longest line, row heights are no longer capped below the spreadsheet maximum;
  protocol codes use the Protocol findings wording.
- Header-only sheets carry one `None in this session` row. The md decision "Current computed result" line and
  "No option has been selected by the caller yet." replace the ambiguous "Selected ... option: Open".
- **Protocol findings** gains a last column `Example trace (first witness)`: the view's `witness_wording` (the first
  bounded witness of a policy gap, competing transitions, violation or unestablished termination, in words), or
  `n/a`. The decision list adds it as an indented `Example trace:` line under that claim's bullet.

### Wave-4 additions (2026-11-05)

Wording and rows only; each reads retained fields, none is computed in delivery.

- **Plan comparisons.** `Claim outcomes under this alternative` shows each claim's effective outcome and
  admission; a claim whose support is refused reads "not applied" with the reason, and its calculated outcome is
  labelled "for reference only". When claims are not applied the retained windows carry "(calculated; its claims
  are not applied)". New columns `Checks deciding this alternative` (required or optional, check code and the
  reason: not-computed method with its missing inputs, or the unapplied claims) and `Retained binomial plan`
  (n, critical count, p0, p1, exact null-rejection probability and power, each rational with a rounded 4-place
  decimal), from `children[].statistics`. The view's alternatives gain `deciding_checks` and `statistics`.
- **Changes.** `changes` rows render binomial value changes (n, critical count, p0, p1, null-rejection
  probability, power; rationals with decimals) and decision changes (selected alternative, disposition,
  per-alternative compatibility) as before → after text.
- **Model assumptions** (md `### Model assumptions` after Findings; sheet `Model assumptions` only when a
  binomial check exists): the model in words, each role (fixed_n, iid_binary, alignment) declared or missing with
  standing and version, the application and why it is withheld, the retained plan, the guarantee and what is not
  computed. A withheld binomial claim's wording names the missing or unaccepted role and states that the computed
  values stay visible and are not applied. The view's check rows gain `models`.
- **Definition relations** (md `### Definition relations`; sheet `Definition relations` only when a relation has
  a protocol operand): relation, code, each direction's result, caller-declared standing and `observed_match`;
  a `differs` side warns "this reading differs from the value at its address". A `conflict` reads "refuted by a
  counterexample ... not a contradiction inside the protocol", is counted on the Findings counts line and listed
  under Open items. `protocol_view.relation_rows(result)` is a separate pure function over `result`.
- **Header.** The decision list no longer says "No decision entries were declared"; it says no general
  design-choice entries were declared and points to Protocol and Findings.
- **Refused child.** A refused check child is a `Not computed` finding with its words and code; the check
  summary code reads `refused`; the section reads `not_computed`, never "none found". The check row gains
  `refusals`.
- **Consistent plain signals** (`clean_signals`) get a `No finding` row and bullet ("... check returned
  consistent").
- **Adoption.** New `Definition reference standing` column (the object's own `data.definition` status) with
  words such as "its definition reference is proposed"; new `Superseded adoption records (listed, not used)`
  column and md lines ("names a superseded version (...); not used"), also marked in Sources and origins.
- **Compact findings** carry the bounded witness sentence (`witness`, `witness_truncated`; 240 characters). If it
  does not fit the byte budget it is dropped before the finding is, and the row says `witness_omitted`.
- **Optional not-computed check.** A section whose required checks computed adds "Required checks computed;
  optional check X not computed: <reason>." to `findings_text`; coverage codes are unchanged.
