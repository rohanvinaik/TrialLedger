# Proposal

## Why

The founder, 2026-11-01 (paraphrased): the second layer is classical-AI, symbolic inference, not LLM inference.
It reads the data, performs symbolic operations to judge what is significant and of value, and builds a clinical
trial for what the user is interested in by itself: most of the effort of designing a trial is mechanical
(gathering and reconciling what hundreds of comparable trials did) and deductive (a study of outcomes in
pregnancy enrolls only people who can be pregnant), and both are this layer's work.

## What Changes

- `trialledger design <brief> --landscape <run>`: from a design brief (the investigational drug or class, the
  indication, the phase, what the trial is to learn) and a landscape run, a draft design written as
  `design.json` and `design.xlsx`.
- Typed design variables: population (indication, disease extent, treatment history and role, biomarker
  selection, age, sex and reproductive status), eligibility (inclusion and exclusion as scoped assertions),
  intervention, comparator and background therapy, primary and secondary endpoints with time points, assessments
  and their schedule, stratification factors, sample-size inputs.
- Five kinds of rule, each with its warrant: definitions (identities and memberships); deductions through the
  scoped-assertion layer and entailment, each with the premises it used; sourced design rules, conditional, with
  their applicability; corpus observations from the landscape (standard criteria, mechanism-linked exclusions,
  endpoints and time points of comparable trials, occupancy and near misses, effect sizes of comparable posted
  results); choice rules applying the user's stated priorities where several designs are admissible.
- A deterministic constraint solver over the variables: every admissible design, contradictions named
  (INCONSISTENT), what the rules leave open returned as closed questions.
- Edits read back as the user's assertions and the design re-checked.

## Capabilities

### New Capabilities

- `design-synthesis`: the brief, the design variables, the rule kinds, the solver, the design record and
  workbook.

## Impact

Builds on `add-scoped-assertions` (the compiler of its group 2 and the entailment procedure), `add-bank-coverage`
(the general packages, for criteria outside oncology), `add-coherence-engine`'s profile and comparable results,
and `add-agent-operation` (the same run folder, entry point and delivery). New modules for the brief, the
variables, the rule tables and the solver; `cli.py` gains `design`.
