# Proposal

## Why

TrialLedger keeps every registry record whole and lays it out for a reviewer, but it understands none of it:
eligibility is two text blobs, line of therapy and biomarkers read "needs review" for every study, and nothing
is computed across trials. The founder's design (docs/THEORY_OF_THE_CASE.md, Part III) is a coherence engine:
type every element of every trial, narrow each trial's design coordinates by approved relations, and measure
each element's information against comparable trials. This change builds it, starting with one indication
(advanced and early non-small-cell lung cancer, Phase 3, 2015 to 2024) and growing the typing by the residual.

## What Changes

- Itemize each study's eligibility text into individual criteria, each with its section (inclusion,
  exclusion, unsectioned) and its exact span, so the pieces reproduce the text.
- Type each criterion with deterministic banks (setting and stage, prior therapy, biomarker status,
  performance status, organ-function thresholds, CNS metastases, named conditions, protocol boilerplate).
  Every typed atom keeps its span; every criterion no bank types enters a residual with a named reason.
  No model reads any trial.
- Classify every drug and biological intervention by the U.S. National Library of Medicine's RxClass
  (FDA Established Pharmacologic Class and MED-RT mechanism of action), each class with its source id.
  Unresolved names stay unresolved.
- Resolve each trial's design coordinates (setting, prior lines for advanced disease, biomarker selection
  per gene, histology) as sets of still-possible values, narrowed by the evidence and by relations that are
  either approved or proposed; show contradictions as conflicts; never choose between conflicting values.
- Compute, over a pulled folder, a reference profile of every typed element (frequency against an explicit
  denominator, surprisal, sponsor support), a boilerplate tier, mechanism signals offered only as proposed
  rules, the occupancy of the design space, and posted results grouped for like-for-like comparison.
- Add `trialledger profile <folder>`, which writes `design.xlsx` beside the pull without changing the
  pull's other files.
- Supersede Decision 1 of the archived review-workbook design ("free text is never turned into structured
  values"): free text is now typed deterministically as a separate, span-carrying evidence tier, below the
  registry's structured fields. The ledger itself still carries free text verbatim.

## Capabilities

### New Capabilities

- `typed-evidence`: criteria itemized from eligibility text, typed atoms from deterministic banks with spans,
  sourced intervention classes, and the residual of what no bank could type.
- `trial-coherence`: each trial's design coordinates as domains of possible values, narrowed by evidence and
  by approved or proposed relations to a fixed point, with conflicts and derivation receipts.
- `design-profile`: the cross-trial layer over a pulled folder: reference profile, boilerplate tier,
  mechanism signals as proposals, design-space occupancy, comparable results, written to `design.xlsx`.

### Modified Capabilities

None. The review and record workbooks are unchanged in this change; projecting computed line of therapy and
biomarker selection into `review.xlsx` is a later change, once the founder has approved the relations.

## Impact

New modules beside the existing ones (criteria, banks, classes, coherence, profile, design workbook) and a
new `profile` subcommand. One new network dependency at analysis time: the public RxClass REST API
(`rxnav.nlm.nih.gov`), called through the existing HTTP client, cached in the folder as `classes.json`. The
derivation code of `review.xlsx` and `record.xlsx` is not touched, so their code root and every written
folder's verification are unaffected.
