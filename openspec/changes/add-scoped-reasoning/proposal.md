# Proposal

## Why

The founder's decisions of 2026-10-31, paraphrased:

- Any typed, structural information counts as **known**: a literal field of the registry's record, or a direct
  symbolic derivation from one (his hypothetical: an age written "2 years" encoded as "24 months"), a class the
  record itself states included.
- Apart from known stand inference-driven values, subject to counter or overrule, of two kinds that must not be
  conflated: an **interpolation**, coherent and assumed correct until overruled, on which symbolic rules may be
  built; and a **proposal**, genuinely uncertain, shown but never built on.
- RxClass classes count as known, with a warrant for their derivation.
- The setting relations are to be what an expert in clinical-trial design would hold valid; he defers that ruling
  to Claude and Codex.
- The live query is the assumed standard path, for building and for validation.
- The indication-scope problem is the one the harmonizing project addressed (its constraint graph lets one
  confident field, the organism, gate which values and rules are admissible; its evidence carries a scope).

What the founder's rule exposed, measured on the 487 development trials and read by Codex twice (its answers in
`/tmp/trialledger-consult/tiers_answer.txt` and `rulings_answer.txt` at the time; their substance is below):

- **Approved is not the same as strict.** Each of the four approved setting relations excludes a qualifying
  design (a locoregional recurrence treated with chemoradiation; local consolidation after prior systemic
  therapy; palliative radiotherapy in stage IV disease; a treatment-naive trial randomising at maintenance).
- **`setting` conflates three things**: the disease extent required at enrollment, the treatment history at
  enrollment, and the role of the treatment under test. Only the first two can be entailed by eligibility; the
  role is rarely more than an interpolation.
- **Relations read concept presence, not assertions.** 115 trials admit "locally advanced or metastatic" disease;
  the metastatic relation fired on 34 of them as if metastatic disease were required. "Previous stage IV disease is
  permitted" and "metastatic disease is excluded" carry the same concept.
- **A derived registry field is not ground truth.** The registry's MeSH coding misses Lung Neoplasms for 111 of the
  487 lung trials and codes 23 "Non-small Cell Lung Cancer" trials as "Parkinson Disease 4"; the literal
  `conditions` field names lung cancer in 478, and the other 9 name no disease.
- **The development population cannot confirm anything.** Every bank was written while reading it.

## What Changes

- Every derived value carries its epistemic status (known / interpolated / proposed), its justifications and its
  source; rule kind (strict / default / proposal) is separate from approval, source and validity.
- Rule premises consume **scoped assertions** (requirement, permission or exclusion; current or historical; the
  branch and cohort they belong to), never the presence of a concept; a strict conclusion needs every eligible
  branch to entail it.
- An **indication** coordinate, resolved by coherence from the literal conditions and the record's own disease
  assertions (derived MeSH as lower-priority evidence, its disagreement a named conflict), gates which banks and
  relations apply; a rule outside its indication is inapplicable, never negative.
- `setting` is split into **disease extent**, **treatment history** and **treatment role**: strict relations reach
  the first two; the role is reached by defaults with named defeaters, or by proposals.
- Defaults run in declared strata after strict closure, may consume earlier strata, and conflicting defaults are
  quarantined and reported; every removed value keeps its justifications; a correction or an override recomputes
  everything; each proposal is shown on its own and never enters closure.
- Every consumer (strata, cells, occupancy, near misses, the profile) declares which statuses it accepts.
- **Evaluation runs through `resolve`** on populations declared in advance, with every component frozen before a
  run, every fetched record kept, and whole-trial audits scored per bank and slot.

## Capabilities

### New Capabilities

- `epistemic-status`: statuses, rule kinds, scoped assertions, indication gating, the split setting, consumer
  contracts and the evaluation protocol.

### Modified Capabilities

- `trial-coherence` (add-coherence-engine): relations gain a kind and an indication scope; closure gains default
  strata, quarantine and per-value justifications (a delta once the mechanism is fixed).
- `design-deviations` (add-design-surprise): the near-miss representation and the expectation cells read declared
  statuses.

## Impact

`coherence.py` (relations, closure), `banks.py` and a new assertion layer over the atoms, `reading.py`,
`design.py`, `symbolic.py`, `review.py`; `design.xlsx` columns for each status; the JSON reading's coordinates.
No change to the pull, the review and record workbooks, or their verification.
