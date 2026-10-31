# Proposal

## Why

The founder's instructions of 2026-10-31, paraphrased: finish the symbolic rules as if designing a clinical-trial
pipeline from domain knowledge and priors, without p-hacking against this population's residual; and, once the
rules approach a coherent set, treat disagreement that is not pure entropy as information: the surprise of a
structured rule violation is the successor of near-miss learning and surprise (SIGNIFICANCE_WEIGHTING.md:
surprise = −log P turned inward; signal-to-noise intrinsic to the spine; confirmation only from an independent
source; specialise, never ban). A Codex reading of Claude's plan the same day corrected it in five places, all
accepted: a provenance boundary, not only a split; conditional corpus rarity is not yet derivational significance;
every predicate needs an observation status; a valid unexplained deviation must survive as such; near-miss pairs
are relative to a declared representation.

## What Changes

- Every typed predicate carries an observation status: present, explicitly negated, not documented, unresolved
  or not applicable, with scope (section, cohort or arm) and provenance (span). "Not documented" never means
  "allowed".
- Every rule and threshold carries its provenance: an external domain source, authored before exposure to a
  population, or derived from one; the 487 Phase 3 NSCLC trials are development data.
- Expectations are declared predicates with a declared conditioning cell (excluding the predicate and anything
  inferred from it) and a declared parent hierarchy; the output is labelled conditional corpus rarity, abstaining
  where the cell is unsupported; derivational significance is a named later target.
- Deviations from an expectation are classified by separate statuses: invalid extraction, scope unresolved,
  verified deviation (may stay unexplained) and explanation supported; replication is recorded, never taken as
  explanation.
- Near-miss pairs: trials equal on a declared representation (unknowns never match) and differing in one verified
  predicate, with sponsor lineage, era and cohort structure named.
- The first step is a falsifier: one frozen expectation traced end to end on real records and constructed
  counterexamples, before the banks are refactored.

## Capabilities

### New Capabilities

- `design-deviations`: observation statuses, declared expectations with conditional rarity, deviation statuses and
  near-miss pairs.

### Modified Capabilities

None yet: `typed-evidence` gains observation status when the falsifier has fixed the contract (a delta then).

## Impact

New module(s) beside `profile.py`; `design.xlsx` gains Expectations, Deviations and Near Misses sheets later. No
change to the pull, the review and record workbooks, or their verification.
