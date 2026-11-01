# Proposal

## Why

The founder's decisions of 2026-10-31, paraphrased:

- A model audits TrialLedger's readings and a human adjudicates (add-scoped-reasoning, Decision 10).
- A model is never handed a whole trial record. Context is scoped by section, each section in isolation, as he
  built it in harmonizing (publication sections, METHODS priority, minimal prompts to a local Qwen with JSON
  output) and in Regenesis (a deterministic heading classifier keeps or vetoes each section; a model seam may only
  add a non-vetoed section; windows assembled to a budget).
- A capable local small model (the Qwen family) through his GSE call setup.
- Models do not reason over every dimension: they resolve specific, targeted questions that the symbolic system
  needs answered to resolve the full study design.
- The live API path, on a genuinely well-scoped sample across the range of trial conditions and types.

A Codex reading of Claude's first auditor design the same day (by the SquishOS recipe, model only) found: an
isolated item can lose its parent stem, its alternatives or its cohort heading; a missing criterion cannot be
challenged unless every piece of source text is accounted for; a closed concept list measures completeness only
within the taxonomy; agreement with a model that sees the engine's answer is anchored unless controlled; a sample
needs declared overlap handling and inclusion probabilities, and its id lists and records kept.

## What Changes

- **Targeted questions.** The symbolic system poses a question as a typed object: its kind, the claim or gap it
  concerns, a deterministic source envelope (the target span with offsets, its heading ancestry, any parent stem,
  and the siblings an explicit "and"/"or" needs), closed answer options including `insufficient_context`, and a
  JSON schema. Nothing else of the trial is sent.
- **A local model answers** through a GSE-style transport (explicit model, pinned digest re-verified around every
  call, canonical-JSON prompt, schema-constrained output, temperature 0, context guard that refuses rather than
  truncates, a call budget), every request and answer cached by a hash that includes the model, schema, rubric,
  options and envelope version. An answer never becomes known: it is provenance-marked and overrulable.
- **Audit questions** are one kind: per atom, "does this envelope state this claim?" (supported / wrong value /
  wrong polarity or modality / unsupported / insufficient context); per criterion that no bank typed, "which of
  this bank domain's concept instances does it state?" plus `out_of_taxonomy` with a span. Interventions split
  record-stated target claims from RxClass assignments, which are checked deterministically against their kept
  artifact; outcomes define a time point against an observation window.
- **A source manifest** accounts for every piece of eligibility text (heading, item, ignored), every registered
  outcome and every intervention, so an omission has a unit to be found in.
- **Adjudication** by the human at the level of the atom, the omission and the unit, blind first (the human
  records what the source supports before seeing the model), on every challenged item and a declared random sample
  of accepted ones (empty outputs included); controlled mutations (a wrong threshold, a reversed polarity, an
  unsupported atom, a removed atom) test whether the model challenges a supplied answer.
- **A live stratified sample**: interventional studies, strata from the registry's top-level condition ancestors
  (a derived field, used as a label only), independent seeded draws per stratum, deduplicated with each trial's
  union inclusion probability; a hash-reserved confirmation pool no discovery wave may draw from; a balance table
  for intervention type and purpose; every id list, retrieval time, seed and resolved record kept.
- **A pilot before the wave**: 80–120 units from 15–20 trials, three auditor configurations on the same units
  against human references, a separate challenge set; the least costly configuration meeting declared criteria is
  chosen, or the pilot reports insufficient evidence.

## Capabilities

### New Capabilities

- `targeted-questions`: question objects, envelopes, the transport, caching, the source manifest, audit
  questions, adjudication, the live sample and the pilot.

### Modified Capabilities

- `epistemic-status` (add-scoped-reasoning): a model's answer is provenance on an overrulable value, never known.

## Impact

New modules (`questions.py`, `transport.py`, `sample.py`, `audit.py`), new CLI commands (`trialledger sample`,
`trialledger audit`) and `resolve --ask MODEL` (serial, one study at a time), an adjudication workbook. Without
`--ask`, `resolve` is unchanged; no change to the pull, the workbooks or their verification.
