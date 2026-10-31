# Design — add-design-surprise

## Context

See proposal.md. Sources: SIGNIFICANCE_WEIGHTING.md (read whole 2026-10-31); Claude's plan
(`/tmp/trialledger-consult/surprise_reading.md` at the time, summarised here) and Codex's reading of it, which
corrected it in five places, all accepted.

## Decisions

1. **Provenance boundary.** Every rule, vocabulary entry and threshold records its origin: `external` (a cited
   domain source), `prior` (authored before exposure to the population it is measured on) or `derived` (from a
   named population). The 487 Phase 3 NSCLC trials, read extensively while the banks were written, are
   development data for every existing bank. Confirmation runs on a population no rule was written against: a
   second indication, a later era, or the corpus pull; a split of one population must follow sponsor lineage
   (collaborators, shared templates, drug programs), not only the lead sponsor. Before a confirmation the schema,
   parsers, applicability rules, thresholds, audit rubric and sampling are frozen and versioned; a changed
   component needs fresh confirmation for the claims it touches; a held-out set looked at twice is development
   data.
2. **Observation status per predicate** (present / explicitly negated / not documented / unresolved / not
   applicable), with scope and spans. "Unresolved" covers untyped or unitemized text that could hold the
   predicate; it is an observability limit, not entropy.
3. **Conditional corpus rarity, honestly named.** For a declared binary predicate Y and declared cell C: presence
   scores −log2 P(Y=1|C), absence −log2 P(Y=0|C), with |C|; no "expected set" threshold. C excludes Y and anything
   inferred from Y. A declared parent hierarchy (for example class × setting → class → all) supplies support,
   reported as such; shrinkage never manufactures subgroup evidence; an unsupported cell abstains. The
   founder's derivational significance (improbability given the alternatives the derivation afforded) needs an
   explicit admissible-alternative space and is a later target, not claimed here.
4. **Deviation statuses**: invalid extraction (the span does not say what the atom says), scope unresolved
   (cohort, arm or section scope not determinable), verified deviation (valid, in scope, against the
   expectation; may stay unexplained), explanation supported (a recorded qualifier, a coordinate the cell did not
   condition on, or a cohort structure accounts for it). Replication across independent sponsors is a separate
   count, not an explanation. Predicate granularity is checked before a deviation is declared ("controlled
   hypothyroidism allowed" can be consistent with "excludes active autoimmune disease requiring systemic
   therapy").
5. **Near-miss pairs under representation R**: every predicate of R known and equal, one verified predicate
   different; sponsor lineage, era, geography and cohort structure reported; an outcome difference is an
   association to investigate, never a causal claim.
6. **Falsifier first.** One frozen expectation ("PD-1/PD-L1 blocker trials exclude active autoimmune disease"),
   traced end to end on real records and on constructed counterexamples (explicit exclusion, qualified
   exception, omission, unresolved text, conflicting cohort scopes): for each, the evidence span, predicate status,
   applicability, derivation, probability source and decision. It tests the observation contract, the rarity
   definition, the deviation statuses and the near-miss representation together, before the banks are
   refactored.

## Risks / Trade-offs

- [The schema was shaped by reading this population] → recorded as such under Decision 1; its claims are
  confirmed elsewhere.
- [Observation status multiplies predicate bookkeeping] → only declared predicates get a status; the banks keep
  their atoms.
