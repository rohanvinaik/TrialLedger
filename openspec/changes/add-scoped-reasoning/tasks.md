# Tasks — add-scoped-reasoning

## 1. Interim correctness

- [ ] 1.1 Relations gain `kind` (strict / default / proposal) apart from approval; the four relations approved
      earlier become defaults; `resolve` reports the known domain (stated evidence and strict relations), the
      interpolated domain (defaults added) and each proposal's narrowing on its own; consumers read the status they
      declare (strata, cells, occupancy, results: known; near misses: known and interpolated, labelled)
- [ ] 1.2 RxClass answers carry their warrant (request, release date, class ids) as known evidence

## 2. Scoped assertions

- [ ] 2.1 An assertion layer over the atoms: modality, time, branch, cohort; disjunctions kept as branches; the
      setting premises first (extent, stage, prior lines, resection, setting words)
- [ ] 2.2 Interventions as assertions: tested, comparator, background or supporting, from the arm and
      intervention fields

## 3. Indication

- [ ] 3.1 The indication coordinate, resolved from literal conditions and the record's disease assertions, the
      derived MeSH as lower-priority evidence, conflicts named
- [ ] 3.2 Every bank and relation declares its indications; outside them, inapplicable; unresolved, scope-unresolved

## 4. The setting split

- [ ] 4.1 `disease_extent`, `treatment_history`, `treatment_role` coordinates; the strict relations of Decision 5
- [ ] 4.2 The repaired defaults and the proposals of Decision 5, each with its counterexamples as tests

## 5. Closure

- [ ] 5.1 Default strata after strict closure; joint consistency; conflict quarantine; named unsupported cycles
- [ ] 5.2 Per-value justifications; full recomputation on a correction or a review answer

## 6. Evaluation through the live path

- [ ] 6.1 The evaluation plan recorded and frozen before any new population is opened (Decisions 9-10): the
      auditor model and its version, prompt and rubric; the adjudicator; the sample of agreed values sent to the
      human; sizes from the adjudicator's capacity and the auditor's budget
- [ ] 6.2 Discovery wave 1 (untouched later NSCLC Phase 3) through `resolve --keep`; outputs kept before any error
      is read
- [ ] 6.3 Confirmation on a population no rule was written against, scored per bank and slot

## 7. Drug-class axes (Decision 11)

- [ ] 7.1 Identity resolution of an intervention name (ingredient, combination, salt, brand), then RxClass ATC
      and `has_chemical_structure` with warrants; `DRUG_TYPES` gains GENETIC
- [ ] 7.2 Registry intervention MeSH kept at trial level unless linked; `shares_structure_class`
- [ ] 7.3 The sourced target-to-ATC crosswalk with named relations; near misses read alignment as alignment
- [ ] 7.4 Modality facets and cell properties from bound record wording and sourced mappings

## 8. Eligibility coverage (Decision 12)

- [x] 8.1 Content, sectioning and coverage-evidence attributes, one pure decision, with marker locations and
      scope; `_ABBREVIATED` moves there; Trials sheet, JSON, review flag (2026-10-31:
      `criteria.eligibility_coverage`; the pattern moved unchanged; Trials sheet columns, the
      `eligibility_coverage` JSON object, the `eligibility_abbreviated` review flag; `autoimmune_exclusion`
      reads the attribute, any section abbreviated. 2026-11-01: `provenance.py` entries for both marker
      patterns; end-to-end tests through `resolve` of the sheet, JSON and review flag. Left: the measured
      misses and example-list false positives of the pattern (transition report), for the founder.)
- [x] 8.2 The statement rate and the full-criteria interval in the profile; three-valued thresholds; signals,
      occupancy, expectations and near misses at their decision points
      (2026-10-31: `frequency_rows` over every trial, S, A, U by kind, the rate and the interval as separate
      columns; `full_criteria_tier`; `element_silence`; occupancy and near misses unchanged, each with its
      reason in its docstring. 2026-11-01: a trial no bank typed is its own kind of silence (no_rule_match); a
      primary endpoint has the statement rate only, no interval or tier; mechanism signals, a statement-rate
      comparison over typed trials, are proposed only when they hold with abbreviated silences read least
      favourably and unresolved when those could reverse them; the `design-profile` spec delta.
      Left: no ascertainment rule is declared, so A is 0 by construction and no tier is "not_met" yet, the
      founder's to declare; an itemized trial no bank typed stays in its mechanism group; the delta's MODIFIED
      requirements wait on `add-coherence-engine`'s archive.)
- [x] 8.3 The transition report on the frozen NSCLC records before the metrics are replaced
      (2026-10-31: `transition-eligibility-coverage.md`; expectations, occupancy and near misses identical;
      every changed review flag and profile tier listed with its reason. Regenerated 2026-11-01 on the same
      records: 40 primary-endpoint rows keep tier ""; 5,076 silences counted as no rule match; mechanism
      signals 598 → 261 proposed, 2,411 unresolved (666 of them added), every changed status listed.)
