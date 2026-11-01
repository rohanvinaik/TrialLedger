# Design — add-bank-coverage

## Context

Codex's design of 2026-11-01 (kept at `/tmp/trialledger-consult/banks_answer.txt` at the time), reconciled with
the code by Claude; **As built here** marks the reconciliation.

## Decisions

1. **The bank contract.** A bank recognizes; it never decides eligibility. `recognize(text, version) ->
   BankResult {atoms, findings}`; an atom `{atom_id, owner_bank, concept_id, mention_kind, values, params,
   evidence_spans (concept, value, unit, comparator apart; half-open, on the original text), rule_id}`; findings
   with codes IDENTIFIED, AMBIGUOUS, ABSTAINED, NO_TRIGGER, INVALID_INPUT. NO_TRIGGER is never evidence that a
   criterion holds no relevant concept. A numeric expression stays local ("HbA1c ≤ 8.0%"); negation, attachment
   and applicability belong to the assertion layer (add-scoped-assertions). Reference expressions ("1.5 × ULN")
   stay symbolic; eGFR equations and HbA1c assay conventions stay distinct. **As built here**: today's atom
   `(bank, concept, values, params, start, end)` is extended, not replaced; `text_polarity` and `modality` stay
   candidate annotations the assertion layer may override.
2. **One registry from fragments.** Predicate signatures, not patient facts; families Attribute, Measurement,
   State, Event, Exposure, Count, Relation, Capability, Commitment. Each concept has one owner; domain packages
   reference shared concepts (NYHA lives in scales, HbA1c in measurements, diabetes type in condition attributes).
   The build rejects duplicates, incompatible definitions, unknown arguments, invalid parameter types, missing
   provenance, unsupported units, unversioned scales, unresolved dependencies, invalid spans, nondeterminism.
   Clinical entailments are separately registered, versioned rules, never consequences of recognizing a word.
3. **Packages.** General (each with its predicate families and authority, editions and licensing pinned at
   implementation): demographics and developmental age (CT.gov definitions, CDISC); sex and reproductive status;
   reproductive requirements (tests, methods, actors, duration); consent, capacity and participation (ICH E6);
   scales and functional status (each instrument its own identity — ADL is not one instrument; ECOG, Karnofsky,
   Lansky, NYHA, mRS from their sources); laboratory measurements (LOINC, UCUM — LOINC identifies observations, a
   bare analyte name may not justify a code); vitals and anthropometry; conditions and events (SNOMED CT, ICD, NCI
   Thesaurus); medication and substance exposure (RxNorm, RxClass with its named source); procedures, anatomy and
   devices; prior research participation; molecular markers (HGNC, HGVS); healthy-volunteer eligibility (not an
   entailment that a participant has no disease). Domain extensions: oncology (stage tuples by system, edition and
   site; histology; lines and regimens), cardiovascular, metabolic and endocrine, neurology, psychiatry
   (diagnostic system and edition; instrument forms), infectious disease, respiratory (ATS/ERS, GOLD), renal and
   hepatic (KDIGO; Child-Pugh and MELD variants), pediatrics and pregnancy (Tanner, WHO growth standards),
   vaccination (CVX), devices, surgery and rehabilitation, behavioral and operational. Where no adequate
   vocabulary exists: a local namespace with a written definition, argument types, examples, exclusions and
   provenance. CTCAE grades adverse events only; MeSH indexes and samples, never decides semantics; DSM and AJCC
   need edition and licensing decisions. Outcomes and stated drug targets stay separate surfaces.
4. **Contextual resolution, not an exclusive gate** (revises add-scoped-reasoning Decision 4). Banks stay pure;
   a resolver uses trial context to disambiguate (an abbreviation with several meanings) and to activate
   specialized interpretations, never to suppress an explicit mention: a vaccine trial still excludes
   immunosuppressants, a depression trial recent MI, a healthy-volunteer trial dialysis. Results SCOPE_SUPPORTED,
   SCOPE_UNRESOLVED, SCOPE_CONFLICT; any recognizer-skipping optimization must be shown to drop no explicit
   mention.
5. **Provenance in two records.** Concept provenance (authority, edition, licence) and rule provenance (external,
   prior or derived; the source passages or declared prior; the development populations and examples inspected;
   the freeze version and date; later confirmation populations). A source-backed concept does not make a
   phrase pattern prior if inspected criteria shaped it. **As built here**: `provenance.PROVENANCE` gains a
   concept-authority table beside its rule entries; every existing bank is labelled with its NSCLC and pilot
   exposure.
6. **Discovery drives priority, not rules.** Freeze the discovery population and registry snapshot; read its
   residual for missing capabilities (gestational age, device anatomy), not for patterns; specify each bank from
   independent sources and declared domain rules; record any influence from inspected wording; freeze; assess on
   untouched data. Priority in separate columns: residual prevalence by slice, trials affected, consequence of a
   wrong interpretation, dependencies unlocked, source readiness and licensing, effort; general capabilities
   first where they unlock several domains.
7. **The supported-type matrix.** Condition category is one axis; also intervention type, primary purpose
   (treatment, prevention, diagnostic, screening, supportive care, basic science), phase including not
   applicable, allocation and model, population (children, pregnancy, healthy volunteers). Every declared type has
   a supported/unsupported manifest and measured results. The release scope (interventional 2010-2025 today) is
   the founder's to declare; observational studies and expanded access are out until declared.
8. **Evaluation.** Three objects: mention extraction, scoped assertion, eligibility evaluation, audited apart and
   traced. Gold annotation of a sample for recall (auditing emitted claims alone cannot measure misses). Measures:
   any-mention coverage, complete-representation coverage, bank recall, precision, parameter accuracy by field,
   abstention rate, miss rate, scoped-assertion precision and recall, each with its numerator and denominator;
   one-to-one matching declared before evaluation; unresolved labels kept with bounds C/(C+W+U) and
   (C+U)/(C+W+U); clustering by trial. Model agreement is reported as model-review agreement unless adjudication
   is grounded in the source. Audit prompts hold the complete criterion and its structure and hide the bank's
   rationale; nonemitted opportunities and hard negatives included.
9. **Confirmation.** Frozen downloaded records (not a live re-draw) with their versions; related records grouped
   so shared protocols cannot leak across splits; the reserved pool assessed once per version; a batch that
   changes a rule becomes development data for the revised version; previously inspected trials (NSCLC, the
   pilot, the discovery wave) never confirm.
10. **Build order.** (1) Freeze contracts and evaluation definitions (atom schema, families, registry loader,
    ownership, offsets, provenance schema, type matrix). (2) Audit the existing banks against them, keeping
    justified rules with their exposure labelled. (3) Shared primitives and the general packages, in parallel,
    shared parsers with one owner. (4) Domain extensions against frozen interfaces, one file-disjoint package per
    worker, order from the capability table. (5) Contextual resolution and the assertion layer integrated. (6) A
    frozen confirmation through the real entry point. (7) Release with explicit unsupported cases. Each bank
    delivers recognizer, registry fragment, source manifest, exposure record, fixtures (real criteria cited by NCT
    id and record version; inclusion and exclusion formulations; hard negatives) and known abstentions; verified
    through `trialledger audit`. **As built here**: parallel packages run as a workflow in temporary worktrees
    (the founder's exception of 2026-11-01), merged serially to main, one commit each.

## Founder decisions (Codex's recommended choice in each; none taken here)

- The supported universe and type matrix of this release (interventional only, or more).
- What "typed" means: mention, complete scoped representation and evaluated eligibility reported apart.
- Indication as contextual disambiguation, never an exclusive filter.
- Derived-rule admission: exposure kept; no confirmation on a population that informed the rule.
- Terminology policy: pinned editions, licensed subsets, local definitions; abstain on unsupported mappings.
- Audit authority: source-grounded adjudication; model agreement named as such.
- Release thresholds per bank and predicate, including consequential error classes, declared in advance.
- Confirmation reuse: inspected batches retired for revised rules; future batch allocation declared now.
- The local model stays a reviewer; bank recognition and assertion compilation stay deterministic.

## Risks / Trade-offs

- [Vocabulary explosion] → one owner per concept; the registry build rejects duplicates.
- [Overlap between banks] → evidence of the same instance merged; different interpretations kept as alternatives,
  never "longest match wins".
- [Licensed terminologies (SNOMED CT, DSM, AJCC)] → source and licensing work starts early; abstain where a
  mapping is unsupported.
