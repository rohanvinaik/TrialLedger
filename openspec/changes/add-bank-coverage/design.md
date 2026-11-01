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

## As built here: the frozen contracts (tasks 1.1-1.5, 2026-11-01)

- **1.1 (Decision 1)** `TrialLedger/semantics/contracts.py`: frozen `Span(role, start, end)` (half-open on the
  original criterion text; roles concept, value, unit, comparator, qualifier, window, and `whole` for a legacy
  atom's one span), `Atom(atom_id, owner_bank, concept_id, mention_kind, values, params, spans, rule_id,
  legacy_concept)`, `Finding(code, owner_bank, concept_id, span, note)` with the five codes, `BankResult`. The
  id is the first 16 hex digits of the SHA-256 of the atom's canonical content (`atom_digest`). Validation is
  by named problems (`atom_problems`, `result_problems`), never by raising. The adapter (`from_legacy`,
  `to_legacy`, `legacy_result`) is lossless: on every criterion of `tests/test_banks.py` (139 atoms) every
  atom comes back unchanged; its one span is `whole` (the parts are not re-searched); a bank's empty answer
  is NO_TRIGGER, blank text INVALID_INPUT. Concept ids: `nsclc.<concept>`, keyed concepts by their first
  value (`nsclc.condition.hiv`, `nsclc.lab.alt`, `nsclc.biomarker.pd_l1`).
- **1.2 (Decision 2)** `TrialLedger/semantics/loader.py`: the nine families with the argument names each
  takes, ten argument types, `ConceptEntry`, `Reference` (a shared concept another package owns, with the
  signature expected of it: how "incompatible" is detected across packages without a second definition),
  `Fragment`, `registry_problems` (twenty named codes, twenty-three since 3.1; a duplicate or incompatible concept names both
  owners), `compile_registry` (version: SHA-256 of the fragments' canonical JSON in name order),
  `load_fragments` (`*.json`, or `*.py` with a `FRAGMENT` dict, in `semantics/fragments/`, never under the
  vendored `TrialLedger/registry/`), `atom_registry_problems`. The seed fragment `nsclc_legacy` (91 concepts)
  is built from the banks' own tables, exposure `fragment:nsclc_legacy`. One legacy disagreement is kept for
  2.1: the conditions bank reads "≥ 18 years" as a window of `sex` (an Attribute takes no window). 2.1
  resolved it: the age is the age bank's.
  Not yet refused: unsupported units, invalid spans, nondeterminism (with 3.1's shared parsers; refused since
  3.1, below). No version is
  invented: each local concept carries its own definition date (`defined_on`, YYYY-MM-DD; refused without
  one); a scale names its pinned source edition, or, in a fragment of `LEGACY_FRAGMENTS` only, the explicit
  mark `unversioned`, which the build accepts and lists in `Registry.flags` (`registry_flags`); a new
  package's unversioned scale is refused. The seed's performance-status scale is so marked and flagged.
- **1.3 (Decision 5)** `provenance.py` gains `CONCEPT_AUTHORITIES` (B5's open authorities first; SNOMED CT
  licence_required; DSM, AJCC and the WHO lung histology names words_only; every edition unpinned, AJCC's
  too (`bank:setting` and two approved relations name the 8th edition in their notes, but no edition is
  pinned from its source; 5.1 pins it, the founder's decision of 2026-11-01 to wait), and the local namespace has none, borrowing none from a fragment; a code from an
  unpinned authority is refused), `LICENCE_STATUSES`, `DEVELOPMENT_POPULATIONS` and `RULE_EXPOSURE`
  (populations inspected, freeze, confirmation batches) beside the unchanged `PROVENANCE`. Every existing
  bank lists the pilot (2026-10-31/11-01) among its populations: the pilot's audit read every bank's atoms.
- **1.4 (Decision 7, B1)** `TrialLedger/typematrix.py`: axes from the vendored enums and `sample`'s
  declarations (primary purpose has the registry's ten values, not six); `study_coordinates` (pregnancy is
  `not_in_registry`: no field states it, and it is never read from text); `universe_status` (interventional,
  start from 2010-01, "the present" passed in, never read from a clock); the manifest format
  (`MANIFEST_FIELDS`, statuses supported, unsupported, unmeasured; supported only with an evaluation cited)
  and `manifest_problems`.
- **1.5 (Decision 8, B2, B6, B7)** `TrialLedger/evaluation.py`: the three levels, kept apart (every measure
  takes its level and reads only that level's gold and emitted claims, `at_level`; `match` and `judge` refuse
  a mixture); `Claim` and the gold record (`GoldRecord`: the quote must be the text at its span; each
  annotator's `Read`, its verdict holds, does_not_hold or unsure and its quote at its own span; the recorded
  agreement kind, which must be `agreement_kind`'s: source_grounded only when two distinct annotators each
  quote the text at their span, else model_review_agreement; "agreed" refused with fewer than two annotators
  or a read that does not say holds); `MATCHING_RULE` and `match` (one to one, longest overlap, then nearer
  start, then position); `judge`; `bounds` (None when nothing is labelled); `rate` (numerator, denominator,
  trials, per-trial counts, bounds); `recall` (not_measured without gold), `precision`, `miss_rate`,
  `unit_rates` (any-mention coverage and abstention), `complete_representation`, `parameter_accuracy`;
  `THRESHOLDS` with `THRESHOLD_MEASURE`, `MINIMUM_DENOMINATOR` and `BOOTSTRAP` beside them, and
  `threshold_verdict`: the measure its threshold names only (else wrong_measure), at or above the minimum
  sample only (else insufficient_denominator), judged on `clustered_lower_bound`, the 50th smallest of 2000
  seeded resamples of the trials of the pessimistic rate C/(C+W+U), never on the unresolved bound alone.

## As built here: the shared parsers (task 3.1, 2026-11-01)

- `TrialLedger/semantics/parsers.py`, one owner for every package. Each reader takes the criterion's text and
  a position, skips whitespace and reads one expression there into a `Parse(kind, status, readings, spans,
  end, note)`: status `parsed` (one reading), `ambiguous` (every reading the words allow, none chosen) or
  `abstained` (none, with its note); each reading a tuple of named string fields (never a float, a bool or
  NaN); spans `contracts.Span`, half-open on the original text. Nothing is unescaped first: the API's
  "=\<", "\>=", "\^", "\~" are read where they stand.
  - `read_number`: digits, signed only where no digit stands before the sign ("0-1" is a range), or a written
    form (zero to ninety-nine). One mark before three digits ("50,000", "1.500") is ambiguous, grouping or
    decimal; a comma that cannot group ("0,1": a decimal comma or a list) is abstained; digits inside a name
    ("PD-L1", "CTLA-4", "B12", "HbA1c") are not read; number words are ASCII letters only, and a fraction
    ("one-third") or a tens word before a hyphenated word ("twenty-something") is abstained, never a wrong
    value.
  - `read_comparator`: symbols, escaped forms and word forms (`COMPARATORS`), the longest first, normalised to
    <, ≤, >, ≥, =; the sign is the matched form's (each form its own group), never the matched text looked up
    again, so a form case-insensitive matching folds ("leſs than") is still a named result. A strict sign or
    "=" never reads the start of a two-symbol form the table does not hold ("> =", "< /=", "= <": abstained);
    ">or=" and "<or=" are held. A form is read where the caller starts: a caller starts at the phrase's head
    ("more than" read inside "not more than" is the shorter form).
  - `read_unit`: `UNITS`, each written form with its UCUM expression (10*9/L, /mm3, mg/dL, mL/min, a, mo, wk,
    d, h, min, ...) or none; a slash compound of unit symbols the table does not hold ("G/L", "IU/dL",
    "copies/mL"; each part an SI prefix and a base, a counted thing, a unit of time or "G", from a closed set,
    so a pair of words such as "AST/ALT", "Male/female" or "inclusion/exclusion" is no unit) and a unit with
    no UCUM form here ("half-lives", "pack-years", "mL/min/1.73 m2": its normalisation is left unmapped rather
    than guessed) are kept as written and named `unmapped`. A power of ten is read only with its sign or a
    superscript ("10^9/L", "10e9/L", "10⁹/L"); "109/L", where the registry's text lost a superscript, is no
    unit (reading it as 10^9/L is a convention left to the founder). "h" is hours in lower case only ("H.
    pylori"). A reference expression is never a unit.
  - `read_reference`: an optional factor, ×/x/*/"times", ULN or LLN in any written form; the factor is "" when
    none is written, never 1; a factor written after the reference ("ULN x 2.5") is abstained (`FACTOR_AFTER`),
    never read as no factor; its span's role is `reference`, which `contracts.SPAN_ROLES` does not yet hold.
    Forms not held ("ULRR", "upper limit of reference range", "upper limit of institutional normal", "the
    normal upper limit", "2.5-fold ULN") are no reference: vocabulary for 3.3 to add with its source.
  - `read_duration`: a number then a unit of time ("a 4-week washout" too).
  - `read_window` (add-scoped-assertions Decision 4 and A7): a marker ("within", "in the last", "within prior")
    or a comparator, a duration, an orientation (before, after, or unspecified: "of" or "from" after a marker)
    and its anchor as written, else "unresolved" (never the enrollment). A marker bounds by N with
    inclusivity unspecified; a comparator gives its own. An unmarked duration with a direction ("4 weeks prior
    to randomization") is ambiguous: within N, or at least N. "within ≥ 5 years" is abstained; a duration
    with no marker and no direction ("≥ 12 weeks", "2 years of smoking") is no window. A window on both sides
    of its anchor ("within 14 days before or after randomization", "before/after") is abstained: no
    orientation value names both, and inventing one is a design decision. A clause word ends the anchor
    wherever it stands, its first word included ("before and during the study": anchor unresolved).
  - `read_interval`: one comparator and a bound (its inclusivity), two comparators on two sides (explicit), a
    range ("18 to 75 years", "0\~1", "6 through 35 years", "between ... and ...") unspecified unless
    "inclusive"/"exclusive" is written, or "or more"/"or older"/"or less". A bound is a reference (its factor)
    or a number with its unit; a unit written once is the range's, two different ones are abstained. A number
    followed, on its line, by a multiplication (×, *, x, "times", "-fold") or digits that no unit or reference
    reads ("≤ 1.5 × ULRR", "≥ 1.5 x 10 9/L", "≥ 100 109/L", "100 000/mm3") is no bound (`UNREAD_AFTER`): the
    interval is abstained, never a bare number with its unit or reference lost.
- The registry build refuses, through these parsers, the last three of Decision 2. `ConceptEntry` gains two
  optional fields, `units` (as written) and `examples` (`Example(text, spans)`), parsed by
  `fragment_from_data`; `compile_registry` writes them into its canonical JSON only when a concept has them,
  so the seed's version is unchanged. `unsupported_unit` (`unit_problems`): a declared unit on a concept with
  no unit argument, one `read_unit` does not read whole (a reference such as "× ULN" among them), or an
  unmapped unit where the unit argument is `ucum_unit`. `invalid_span` (`example_problems`): a span of no
  contract role, outside or empty on its example's text, or a comparator, unit or (for a numeric value
  argument) value span the parsers do not read there as its role. `nondeterministic_fragment`
  (`nondeterminism_problems`): `load_fragments` loads every file twice; an unordered set, a non-finite
  number, or two loads that differ are refused, each place named. The loads are compared with a NaN alike to
  a NaN in the same place (each JSON load makes its own float object), so a NaN is named once, by its place.
- Review of 2026-11-01 (commit 662906a), fixed: a lost reference or factor after a multiplication, the
  two-sided window, the slash compound read from any pair of words, the power of ten read from run-on digits,
  the strict comparator read from "> =", "H" as hours, a NaN reported twice, and two test criteria quoted
  as edited excerpts (now verbatim). Left as disclosed: the `reference` span role (contracts.py's owner) and
  a comparator read from inside a longer phrase (callers start at the head).

## As built here: the existing banks audited (task 2.1, 2026-11-01)

- **Decisions 1, 2, 4, 5**, report `audit-existing-banks.md`. The audit ran every bank over the 10,187
  criteria of the NSCLC development records, from a private copy of `/tmp/nsclc3`, and over the pilot's 228.
  Every atom passes `contracts.result_problems`. Keep or retire is decided by B7, rule by rule: a rule or
  branch with no reading found right is retired (it abstains); a rule whose wrong readings no narrow guard
  can separate from its others without 3.1's parsers or 6.1's assertion layer is kept, its wrong readings
  counted, and B7 binds it at release, when its owning package must make them abstain.
- **Retired: performance status's single-value branch.** All 8 of its NSCLC readings were wrong ("ECOG ≥2
  points" read 2, "less than or equal to 1" read 1, "0～1" read 0) and it read nothing on the pilot. A lone
  value read first now abstains. That removes 8 `ecog_ps` atoms, their 8 `inclusion:ecog_ps` profile
  elements (7 Profile and 5 unresolved Mechanism rows of design.xlsx) and their near-miss predicates; the 8
  criteria are now untyped (8,565 → 8,557 typed). The frozen expectation, the coordinates and the near-miss
  pairs (none) are unchanged.
- **The age is the age bank's.** `banks.named_conditions` no longer takes a window in years whose words
  overlap the age bank's span (`age_limits`) for a condition's window. A window in any other unit is never
  taken for an age. This resolves 1.2's kept disagreement: "≥ 18 years" read as the window of `sex`, an
  Attribute. The registry problems left on NSCLC (25, none on the pilot or the tests' real criteria) are
  criterion-wide grades. They are attachment, the assertion layer's (6.1), and are not hidden by gating
  the grade on a family. On the pilot the one window removed (NCT04693377 #8, "50 years") overlaps an age
  the age bank invents from a definition of menopause: the outcome is right, but not because the age is
  eligibility's.
- **Nonconforming with Decision 4, kept.** No bank reads the indication. But the resection and histology
  rules drop a mention near a non-lung site, or, for resection, far from a lung word. On the pilot that
  suppresses a breast trial's resection. They stay until 5.1 gives resection and histology a site and 6.1's
  resolver says whose tumour it is.
- **Decision 5.** `provenance.DEV_AND_PILOT` names the pilot in the rule origin of every bank its
  corrections revised: performance status, organ function and conditions. Exposure (`RULE_EXPOSURE`) is
  unchanged. Every bank already listed both populations.

## Founder decisions (decided 2026-11-01: the founder approved Claude's recommendations)

- B1. Supported universe of v1: every interventional study, all phases including not applicable, all primary
  purposes and populations, start 2010 to the present; observational studies and expanded access explicitly
  unsupported, each a declared later type.
- B2. "Typed" is reported at three levels apart: mention, complete scoped representation, evaluated eligibility.
- B3. Indication disambiguates and specializes; it never suppresses an explicit mention.
- B4. Exposure is always recorded; a population that informed a rule never confirms it.
- B5. Open authorities first: LOINC, UCUM, RxNorm and RxClass, MeSH, NCI Thesaurus, HGNC and HGVS, ICD-10-CM and
  ICD-11. SNOMED CT needs a UMLS licence and is not required for v1. DSM and the AJCC tables are proprietary:
  psychiatric diagnoses are coded through ICD with DSM names kept only as words; cancer stage groups are
  recognized as words citing the AJCC edition, its tables never reproduced.
- B6. Audit authority: Claude labels blind and Codex second-reads, both required to quote the source text, so
  adjudication is source-grounded; a human expert's spot-check when one is available; model agreement without a
  quote is reported as model-review agreement.
- B7. Release thresholds, declared before measuring: lower-bound precision at least 95% on consequential classes
  (polarity, modality, subject, qualifier) and at least 90% on the rest; recall reported, v1 target at least 70%
  for the general packages; abstention is always preferred to a wrong reading.
- B8. The reserved 30% confirmation pool is split now into three sequential 10% batches (sha256(NCT ID) mod 10
  equal to 0, 1, 2), one per release; a batch is never reused for a revised version. **As built here**
  (2026-11-01, task 7.1a): `sample.pool(nct)` returns `discovery` or `confirmation_0`/`_1`/`_2`;
  `sample.reserved` is unchanged in code and holds exactly when `pool` is a batch, so every discovery draw is as
  before. `sample.draw_batch` draws one stratum from one batch, seeded by seed, batch and label;
  `trialledger sample --confirmation-batch N` uses it for every stratum, after `sample.batch_request` allows it
  (`unknown_batch` outside 0-2, `no_code_version` when `record.code_commit` cannot name the code), and writes
  `drawn_from`, `confirmation_batch`, `confirmation_batches` and `code_commit` into sample.json. A confirmation
  sample declares `supplement_per_cell` 0, since the balance supplement is drawn from the discovery pool; its
  balance table still asks the registry and names each gap. The code version recorded is `code_commit`'s
  (it watches only the review workbook's derivation files, not the banks). Since task 7.1b (2026-11-01) a
  confirmation draw records instead the commit at which TrialLedger/ and tests/ are clean (refused otherwise)
  and a digest of their tracked source; it excludes every trial of the inspected populations declared with
  `--inspected` (Decision 9, B4), keeping each list and counting the exclusions; and it consults the declared
  ledger `confirmation_ledger.json` (batch to the commit it confirmed), refusing a batch already given to
  another commit and recording the batch once the sample is written.
- B9. The local model stays a reviewer; recognition and compilation stay deterministic.

## Codex's recommended settings (kept for the record)

- The supported universe and type matrix of this release (interventional only, or more).
- What "typed" means: mention, complete scoped representation and evaluated eligibility reported apart.
- Indication as contextual disambiguation, never an exclusive filter.
- Derived-rule admission: exposure kept; no confirmation on a population that informed the rule.
- Terminology policy: pinned editions, licensed subsets, local definitions; abstain on unsupported mappings.
- Audit authority: source-grounded adjudication; model agreement named as such.
- Release thresholds per bank and predicate, including consequential error classes, declared in advance.
- Confirmation reuse: inspected batches retired for revised rules; future batch allocation declared now.
- The local model stays a reviewer; bank recognition and assertion compilation stay deterministic.

11. **Beyond eligibility: outcomes, arms, interventions and safety for every trial type** (Claude's gap,
    approved 2026-11-01). The founder's original ten-point list covers endpoints and time points, safety signals,
    comparators and exploratory measures; today's endpoint, intervention and safety typing is oncology-shaped.
    The same package treatment applies: endpoint classes for every domain (measurement instruments, events,
    composite endpoints, patient-reported outcomes), outcome time frames (window, scheduled point, landmark,
    event-driven), arm structure (experimental, active comparator, placebo, sham, standard of care, add-on),
    dosing and regimen, and safety grading (CTCAE for adverse events only, MedDRA terms where posted), each with
    its registry fragment, sources and evaluation.
12. **Results comparability across domains.** "What we need to beat" compares posted results only within the same
    endpoint class, measure type, unit and population; per-domain measure types (change from baseline, responder
    rate, time to event, rate ratio) and unit handling (UCUM) declared; nothing pooled or converted silently.

## Risks / Trade-offs

- [Vocabulary explosion] → one owner per concept; the registry build rejects duplicates.
- [Overlap between banks] → evidence of the same instance merged; different interpretations kept as alternatives,
  never "longest match wins".
- [Licensed terminologies (SNOMED CT, DSM, AJCC)] → source and licensing work starts early; abstain where a
  mapping is unsupported.
