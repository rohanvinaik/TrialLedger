# Proposal

## Why

`add-scoped-reasoning` Decision 3 calls for scoped assertions; its tasks 2.1-2.2 and 4-5 depend on them. The
auditor pilot of 2026-11-01 measured what is left after the general corrections: of the 32 wrong claims in
Claude's 100 blind labels, 12 remain, and every one is a scope failure the atoms cannot express — a disjunction
read as a requirement ("locally advanced or metastatic"; 34 NSCLC trials fire a relation premised on required
metastatic disease), another person's condition ("the source case ... with HIV"), a qualified subset ("HIV with
CD4 < 200"), definitional text (a post-menopause definition read as age, chemotherapy and contraception
requirements), a population or encounter scope, a conditional obligation ("concomitant medication must be
stable"), the study's own procedures, a window attached to the wrong event, an exposure read as a condition. The
four wrong claims the auditor model accepted are the same kinds. The founder asked that the design work go to
Codex; Codex drafted the contract from Claude's reading (2026-11-01, model only, by the SquishOS recipe), and this
change is that contract reconciled with the code as built.

## What Changes

- An assertion layer between atoms and every consumer: `ScopedAssertion {modality, body: Proposition,
  applicability, cohort, branch, spans, rule, status, resolution}` with `Proposition := Literal | AllOf | AnyOf |
  Not | Opaque`, each literal carrying subject, predicate, value, polarity, time and qualifiers. Atoms stay as they
  are, as evidence candidates; they are never eligibility assertions by themselves.
- Eleven pure decisions compile assertions from the text structure and the atoms (structure, alternatives,
  referents, predicate identity, qualifiers, time, normative force, applicability, cohort, definitions,
  projection), each abstaining on named evidence it lacks.
- Strict conclusions by entailment over the compiled eligibility formula (ENTAILED, REFUTED, UNDETERMINED,
  INCONSISTENT, OUT_OF_SCOPE, UNSUPPORTED_QUERY), deterministic, resource-bounded, abstaining on exhaustion.
- Targeted questions for the bounded gaps (subject binding, predicate identity, coordination, normative force,
  qualifier attachment, conditional scope, temporal attachment, cohort scope, definition binding), options
  generated mechanically, answers interpolated with provenance.
- Consumers read declared, proof-bearing projections; a consumer that cannot represent a distinction gets a
  blocked projection, never a silent simplification.
- Migration: shadow mode, a transition report with named change reasons, consumers switched one at a time, new
  measurements under a new semantic version.

## Capabilities

### New Capabilities

- `scoped-assertions`: the object model, the compiling decisions, entailment, the question kinds, consumer
  contracts and the migration.

### Modified Capabilities

- `epistemic-status` (add-scoped-reasoning): Decision 3 is specified here; `reading.effective_section` becomes
  the legacy path until its consumers are switched.

## Impact

A new module (or a small family: `assertions.py` for the model and compiler, `entail.py` for the decision
procedure); `reading.py` gains the assertions beside the atoms; `coherence.py`, `profile.py`, `expectations.py`,
`nearmiss.py`, `review.py`, `audit.py` switch to projections one at a time; `design.xlsx` and the resolve JSON
gain the assertions and their proofs. No change to the pull, the review and record workbooks, or their
verification.
