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

- [x] 7.1 Identity resolution of an intervention name (ingredient, combination, salt, brand), then RxClass ATC
      and `has_chemical_structure` with warrants; `DRUG_TYPES` gains GENETIC
- [x] 7.2 Registry intervention MeSH kept at trial level unless linked; `shares_structure_class`
- [x] 7.3 The sourced target-to-ATC crosswalk with named relations; near misses read alignment as alignment
- [ ] 7.4 Modality facets and cell properties from bound record wording and sourced mappings

  2026-11-01, done: `classes.py` resolves each name by RxNorm (exact-name rxcui, its term type, a
  non-ingredient's ingredients: `name_identity`), asks RxClass ATC and `has_chemical_structure` (DAILYMED and
  FDASPL, kept apart) and keeps each class with the concept RxClass asserts it of (`rxclass_assertions`). The
  intervention's own name decides its identity (`drug_axes`): another name may confirm that concept but never
  supplies one (`alias_role`), so an own name RxNorm does not hold is `unresolved` with a named reason
  whatever its aliases resolve to ("Carboplatin/Pemetrexed" beside "carboplatin": `alias_is_one_ingredient`;
  "XB-1" beside "XB-1 + carboplatin": `alias_is_combination`), and an alias naming another concept is a
  `conflict`. A class is `known` only when asserted of the own name's concept (`class_standing`; Keytruda and
  osimertinib mesylate, answered by RxClass as their ingredients, are `not_inherited`). Every answer is cached
  under the name's `axes` with its request, retrieval time and RxNav release, asked only for the experimental
  drugs' names (the only ones read); a name cached earlier is asked for the axes alone.
  `shares_structure_class` relates two distinct concepts, keyed by rxcui, per taxonomy and release, never
  homology. Intervention MeSH stays at trial level unless the term is literally one intervention's name or
  other name (`mesh_scope`; the "link" read as that literal identity). `CROSSWALK` aligns to ATC only targets
  a drug's own entry states of it (`own_targets`: anti-PD-1, EGFR inhibitor ...; a word naming another drug,
  or a target in the patient's history, is none), each row citing the ATC name RxClass returns with its byId
  request (read 2026-11-01); `entails_membership` admits equivalent_to and narrower_than only, and no present
  row does; the aligned near-miss reading (`aligned_near_miss_input`, `drug_atc`) pairs by ATC classes and
  labels each pair `rxclass` or `crosswalk`, beside the pairs as written, which are unchanged. `modality.py`
  reads the facets and cell properties from each intervention's own name, other names and description, one
  extraction per mention, patient-history and eligibility wording as `history` (never the modality, never
  unlocking cell properties). All of it is rendered: the `resolve` JSON gives each drug's axes, the
  extractions with warrants, the intervention MeSH at its level, the aligned pairs and the structure
  relations, and design.xlsx a Drug Axes sheet. 7.4 stays open: its "sourced mappings" are only the USAN name
  stems, interpolated. Left: gating EPC/MoA (and the EPC `stated_by_record` fallback, which still reads drug
  names as stated classes) by identity, an output change for the founder; a sourced modality mapping. The
  new decisions were converged on 2026-11-01 (the accepted debt, reconciled serially).

  2026-11-01, the axes made lazy (a performance regression: asked on every profile, the axes took
  `trialledger profile` of the stored 487-trial NSCLC folder from about 17 s to over an hour on first run).
  `classes.load_or_lookup(_at)` asks EPC and MoA exactly as before, request for request; the axes only with
  `fill_axes`, which `resolve` passes (its JSON and design.xlsx read them) and `trialledger profile
  --fill-axes` passes after the record verifies (a record that does not verify is asked nothing). A plain
  profile reads the axes cached in classes.json, and `reading.axes_as_looked_up` marks a drug whose own name's
  axes were never asked `not_looked_up` / `own_name_not_looked_up` (no identity, no class, aligned ATC
  unknown), and one whose alias's were not `not_looked_up` / `alias_not_looked_up` (no class known: the
  unasked alias could make it a conflict); never "no class". Measured on a private copy of the folder, RxNav
  faked as unavailable (every request a transport failure, answered at once), the spacing sleep real: before,
  812.5 s and 3,897 axis requests (a floor: live, each request also waits on the network); after, 16.4 s and
  0 requests; EPC and MoA 0 requests in both (all cached). Which names were not looked up is its own pure
  decision, `reading.axes_not_looked_up` (a name with no answer, no `axes` entry or an empty one), and the
  Drug Axes sheet's warrant commits to every rule that decides its rows: `design.sheets`'s `drug_axes` rule
  digests `reading.drug_axes_view` (whose aligned ATC is unknown for a drug not looked up),
  `reading.axes_not_looked_up` and `reading.axes_as_looked_up` beside the `classes.py` rules, so changing any
  of them changes the warrant. Left: the stored folder's axes, asked only when someone runs `--fill-axes`
  (974 names there).

  Detective debt, reconciled serially on 2026-11-01: `reading.axes_not_looked_up` and
  `reading.axes_as_looked_up` converge COMPLETE; `reading.drug_axes_view` is not a pinned decision and keeps
  its two-sign intent tests. Group 8's decisions likewise converge COMPLETE, `criteria.eligibility_coverage`
  excepted: Detective cannot snapshot one of its witnesses (`outcome_snapshot_failed`, a Detective defect,
  AGENTS.md Open items).

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
