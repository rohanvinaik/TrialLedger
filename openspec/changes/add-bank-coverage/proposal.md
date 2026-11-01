# Proposal

## Why

The founder, 2026-11-01: after the proof of concept, "no more excuses: build it properly, across ALL clinical
trial types". Every bank today was written on 487 Phase 3 NSCLC trials; on the 18-trial stratified pilot across
all condition categories, 38% of criteria were typed (84% on NSCLC), and about a third of typed claims were
wrong before general corrections. The founder asked that the design go to Codex; Codex drafted it from Claude's
reading (model only, SquishOS recipe), and this change is that design reconciled with the code.

## What Changes

- A bank recognizes text and decides nothing about eligibility: `recognize(criterion_text, frozen_version) ->
  {atoms, findings}`, pure, no network, model or clock; named results IDENTIFIED, AMBIGUOUS, ABSTAINED,
  NO_TRIGGER (never evidence of absence), INVALID_INPUT; separate spans for concept, value, unit, comparator.
- One shared semantic registry compiled from versioned per-package fragments, one owner per concept, predicate
  families (Attribute, Measurement, State, Event, Exposure, Count, Relation, Capability, Commitment); the build
  rejects duplicate or incompatible concepts, unknown arguments, missing provenance, unversioned scales.
- General packages (demographics and developmental age; sex and reproductive status; reproductive requirements;
  consent, capacity and participation; scales and functional status; laboratory measurements; vitals and
  anthropometry; conditions and events; medication and substance exposure; procedures, anatomy and devices;
  prior research participation; molecular markers; healthy-volunteer eligibility), then domain extensions
  (oncology, cardiovascular, metabolic, neurology, psychiatry, infectious disease, respiratory, renal and hepatic,
  pediatrics and pregnancy, vaccination, devices and surgery, behavioral and operational), each against frozen
  interfaces, file-disjoint.
- Mention-level contextual resolution replaces an exclusive indication gate: indication disambiguates, never
  suppresses an explicit eligibility mention (SCOPE_SUPPORTED, SCOPE_UNRESOLVED, SCOPE_CONFLICT).
- Concept provenance (authority and edition) and rule provenance (external, prior or derived, with the
  development populations inspected) recorded separately.
- A supported-type matrix (condition, intervention type, primary purpose, phase including not applicable,
  allocation and model, population: children, pregnancy, healthy volunteers) with an accountable
  supported/unsupported manifest per declared type.
- Three evaluation levels (mention, scoped assertion, eligibility) with gold annotation on a sample for recall,
  model-review agreement named as such, per bank and slice identified / abstained / wrong / silent miss /
  unresolved, clustered by trial; a frozen confirmation run through the real entry point.

## Capabilities

### New Capabilities

- `bank-coverage`: the bank contract, the registry, the packages, contextual resolution, provenance, the type
  matrix and the evaluation.

### Modified Capabilities

- `epistemic-status` (add-scoped-reasoning): Decision 4's indication gate becomes contextual disambiguation that
  never suppresses an explicit mention.

## Impact

`banks.py` is split into packages with registry fragments under the package; shared parsers for numbers, units,
durations and intervals; a registry loader and validator; an evaluation module; the existing banks kept, audited
against the contract and labelled with their development exposure.
