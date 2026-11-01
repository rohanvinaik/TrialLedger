# Tasks — add-bank-coverage

## 0. Founder decisions

- [x] 0.1 The nine decisions, recorded in design.md (2026-11-01)

## 1. Contracts and evaluation definitions (frozen before any package)

- [x] 1.1 The atom schema extension, predicate families, findings and their codes, offset convention
- [x] 1.2 The registry loader and validator, fragment format, ownership rules
- [x] 1.3 The provenance schema: concept authority apart from rule provenance; exposure records
- [x] 1.4 The supported-type matrix and its manifest format
- [x] 1.5 The evaluation module: three levels, matching rules, measures with denominators, gold-annotation
      format

  2026-11-01, built in `TrialLedger/semantics/` (`contracts.py`, `loader.py`, `fragments/nsclc_legacy.py`),
  `TrialLedger/typematrix.py`, `TrialLedger/evaluation.py` and `TrialLedger/provenance.py` (see design.md "As
  built here"). Left: nothing consumes them in production yet (declared in `tests/test_wiring.py` with the
  task that will: 2.1, 3.x, 4.1, 7.1, 7.2); the registry build does not yet refuse unsupported units, invalid
  spans or nondeterminism (Decision 2's last three, to land with the shared parsers of 3.1, which define
  units and spans); per-bank recall needs gold concepts mapped to their owners through `Registry.owners`,
  which no function does yet; `universe_status` takes the present as a full YYYY-MM-DD date; authority
  editions are unpinned (each pinned from its source by the package that first uses it, 3.x; AJCC's by 5.1,
  the founder's decision of 2026-11-01 to wait: `bank:setting` and two approved relations name the 8th edition in their
  notes, but none is pinned from its source), and the performance-status scale is marked `unversioned` and flagged on the
  registry until 2.1 or 3.3 pins its source edition.

  Revised 2026-11-01 after review: every measure reads one level and matching or judging a mixture is
  refused; `threshold_verdict` gives a verdict only on the measure its threshold names, only at or above a
  declared minimum sample, and reads a seeded cluster-bootstrap lower bound over trials; the gold record
  keeps each annotator's verdict and quote at its span and its agreement kind, and "agreed" needs two
  annotators; no version is invented (the local namespace has no edition, each local concept its own
  definition date; an unversioned scale is refused except, flagged, in the legacy fragment); every existing
  bank's exposure lists the pilot; the deep gate lists pinned decisions in subpackages
  (`TrialLedger/**`), and the tags of `contracts.atom_digest`, `contracts.slug`, `evaluation.agreement_kind`,
  `unit_rates` and `complete_representation` were written whole so it finds them.

  Claude's first settings, accepted by the founder to start (2026-11-01; open to review: "we can always
  review"):
  `evaluation.MINIMUM_DENOMINATOR` (30 judged items and 5 trials for either threshold) and
  `evaluation.BOOTSTRAP` (seed `evaluation-bootstrap-2026-11-01`, 2000 resamples, the 50th smallest: the
  2.5th percentile, nearest rank, of the pessimistic rate C/(C+W+U)); and the annotator verdicts `holds`,
  `does_not_hold`, `unsure`.

  Detective convergence, accepted by the founder on 2026-11-01 as debt incurred by parallel workflow work,
  was reconciled serially the same day: every decision below converges COMPLETE (operator universe, modulo
  unproven-equivalent and crash-only value gaps), `semantics.loader.fragment_from_data` excepted, which
  Detective cannot snapshot (`outcome_snapshot_failed`, a Detective defect, AGENTS.md Open items):
  `semantics.contracts`: `atom_digest`, `atom_problems`, `result_problems`, `slug`, `legacy_concept_id`,
  `from_legacy`, `to_legacy`, `legacy_result`;
  `semantics.loader`: `fragment_from_data`, `registry_problems` (changed: definition dates, unversioned
  scales), `registry_flags` (new), `atom_registry_problems`;
  `typematrix`: `study_coordinates`, `universe_status`, `manifest_problems`;
  `evaluation`: `agreement_kind` (changed: quotes at their spans, distinct annotators), `gold_problems`
  (changed), `at_level` (new), `match` and `judge` (changed: mixed levels refused), `bounds`, `rate` (changed:
  per-trial counts), `recall`, `precision`, `miss_rate`, `unit_rates`, `complete_representation`,
  `parameter_accuracy` (changed: level filtering), `clustered_lower_bound` (new), `precision_group` (new),
  `threshold_verdict` (changed). The tags of `banks.permitted`, `classes.rxnorm_concepts` and
  `classes.name_identity`, broken over two lines, are now written whole, and those three converge COMPLETE.

## 2. The existing banks against the contract

- [x] 2.1 Each bank audited, its rules kept or retired with reasons, its NSCLC and pilot exposure recorded

  2026-11-01, the report is `audit-existing-banks.md` (this folder). Every atom of every bank on the 10,187
  NSCLC criteria and the pilot's 228 passes the contract. Keep or retire follows B7, rule by rule (retired
  when no reading was found right; kept, wrong readings counted, when no narrow guard separates them before
  3.1 or 6.1). One branch is retired: performance status's single value, 8 of 8 NSCLC readings wrong, now
  abstaining (8 `ecog_ps` atoms, 8 `inclusion:ecog_ps` profile elements and near-miss predicates removed, 7
  Profile and 5 Mechanism rows of design.xlsx with them, the 8 criteria now untyped, each listed in the
  report). One rule is fixed: the disagreement kept from 1.2. In `banks.named_conditions`, a window in years
  whose words the age bank reads as the age is the age's, never a condition's window ("1. Male or female ≥ 18
  years.", NCT04416035). Registry problems on NSCLC fell from 62 to 25, and to 0 on the real criteria of
  tests/test_banks.py. 39 atoms changed: 37 `sex` and 1 `informed_consent` window on NSCLC, 1 `contraception`
  window on the pilot, each listed in the report. The frozen expectation is unchanged (110 present, 0 verified
  deviations), and so are the coordinates, trial for trial, and the near-miss pairs (none). `named_conditions`
  and `performance_status` converge COMPLETE. The pilot's one changed window (NCT04693377 #8) overlaps an age
  the age bank invents from a definition of menopause; the report says so. `provenance.PROVENANCE` now names
  the pilot in the origin of the two other banks its corrections revised (`bank:performance_status`,
  `bank:organ_function`; `DEV_AND_PILOT`). That changes three rows of design.xlsx's Rules sheet.

  Left, not fixed here, each routed in the report:
  - 25 criterion-wide grades on families that take none (3.4, 6.1).
  - 21 ages invented from a duration, a laboratory value or a definition on NSCLC; on the pilot 1 invented
    (NCT04693377 #8) and 2 incomplete (3.1, 3.2).
  - ECOG's comparator words ("≥2", "less than or equal to"), now abstaining rather than misread (3.1, 3.3).
  - 20 prior lines invented from "failure rate" or "intolerance to" (3.4, 5.1).
  - The lung gates of the resection and histology rules, which suppress explicit mentions against
    Decision 4: a breast trial's resection on the pilot (NCT02712437), 117 and 89 drops on NSCLC (5.1,
    6.1). A standing exception to B3 until then; accepted by the founder, 2026-11-01.
  - Two entailments authored inside banks, to register apart (Decision 2).
  - The performance-status scale, still `unversioned` and flagged (3.3).

## 3. Shared primitives and general packages (parallel, file-disjoint)

- [ ] 3.1b The quantity grammar (the founder, 2026-11-01: numbers and units parsed by a proper mathematical and
      unit-of-measure grammar, normalized and typed to be machine readable). Every quantity becomes a typed
      structure: its value an exact number (a mantissa and a power of a base, "10⁹/L" read as base 10, exponent
      9, unit L; "1.5 × 10^9/L" as mantissa 1.5), its unit in UCUM with its dimension, the text as written kept
      beside it. One value is one value however it is written ("10⁹", "1×10⁹", "1,000,000,000", "1e9", "one
      billion"), and the record gives its renderings from the structure, never from the text. Values compare
      by converting to the unit's canonical form (10⁹/L equals 10³/µL), exactly, never by string. Two readings
      the registry's text forces: a superscript lost in the text ("109/L", "1012/L", "103/uL") is read as the
      power of ten it lost, where the unit and the exponent's place admit no other reading, and recorded as a
      reading by that rule; a grouping mark before three digits ("100,000/mm3") is read as grouping where the
      unit and magnitude make the decimal reading impossible, and stays ambiguous otherwise. Built before
      3.3, which reads laboratory values through it.
- [x] 3.1 Shared parsers: numbers, units (UCUM), durations, intervals, reference expressions

  2026-11-01, built in `TrialLedger/semantics/parsers.py` (see design.md "As built here: the shared parsers"):
  `read_number`, `read_comparator`, `read_unit`, `read_reference`, `read_duration`, `read_window`,
  `read_interval`, each a pure decision over the original criterion text returning a `Parse` (parsed,
  ambiguous or abstained, every reading as named string fields, half-open spans); and the registry build's
  last three refusals of Decision 2 in `semantics/loader.py`: `unsupported_unit` (`unit_problems`, over a
  concept's new optional `units`), `invalid_span` (`example_problems`, over its new optional `examples`) and
  `nondeterministic_fragment` (`nondeterminism_problems`, every fragment file loaded twice by
  `load_fragments`). Two-sign tests in `tests/test_semantic_parsers.py` and `tests/test_registry_refusals.py`,
  from the real criteria of `tests/test_banks.py` and the pilot's; no bank's output changed, and the seed
  registry's version is unchanged (the new fields enter its canonical JSON only when used). Converged with
  `--two-sign`, each COMPLETE: the seven readers, `unit_problems`, `example_problems`,
  `nondeterminism_problems` and `registry_problems` (changed through its helper); `fragment_from_data`
  (changed: units and examples) ends INCOMPLETE with `outcome_snapshot_failed`, the Detective defect already
  named in AGENTS.md. Left: nothing consumes the parsers in production yet (declared in `tests/test_wiring.py`
  until 3.2-3.5); the contract's span roles hold no `reference` (a parse's reference span has that role, and an
  example cannot carry one: contracts.py is outside this task); UCUM's edition is unpinned in
  `provenance.CONCEPT_AUTHORITIES` (the table's codes are UCUM expressions, no edition cited); a list built
  from a set's iteration order inside one process loads alike twice and is not detected.

  2026-11-01, review of 662906a fixed (design.md "As built here"): a number before a multiplication or digits
  no unit or reference reads is no bound, and a factor after its reference is abstained; a two-sided window
  ("before or after") is abstained; a slash compound is read only from unit symbols; a power of ten only with
  its sign or a superscript ("109/L" is no unit); "> =" is no comparator (">or=" is ≥); "h" is lower case; a
  NaN is named once. Re-converged with `--two-sign`, each COMPLETE: `read_comparator`, `read_unit`,
  `read_reference`, `read_duration`, `read_window`, `read_interval`, `nondeterminism_problems`,
  `unit_problems`, `example_problems`, `registry_problems`. Left for the founder: whether "109/L" (a lost
  superscript) is read as 10^9/L; for 3.3: the reference forms not held ("ULRR", "upper limit of
  institutional normal", "-fold ULN"); for contracts.py's owner: the `reference` span role.
- [ ] 3.2 Demographics and developmental age; sex and reproductive status; reproductive requirements
- [ ] 3.3 Laboratory measurements; vitals and anthropometry; scales and functional status
- [ ] 3.4 Conditions and events; medication and substance exposure; procedures, anatomy and devices
- [ ] 3.5 Consent, capacity and participation; prior research participation; molecular markers; healthy volunteers

## 4. Discovery wave

- [ ] 4.1 ~6 trials per condition stratum plus balance supplements for the type matrix, through
      `trialledger audit`, frozen; Claude labels; residual read for missing capabilities; the priority table

  Resolved 2026-11-01 (the founder: extend the base). The sample's frame was fixed at start dates
  2010-01-01 to 2025-12-31, short of B1's 2010-to-the-present universe. It now runs to the present:
  `sample.base_query(present)`, with the present the UTC date of the draw (or `trialledger sample
  --present`), passed in and never read from a clock in `sample.py`. Each sample records its `present` and
  `base`, and its audit's supplements query the same frame. A sample drawn before the present was recorded
  (the pilot's) is read with `sample.LEGACY_PRESENT`, 2025-12-31, so its supplements are unchanged. Discovery
  and confirmation draws go through the same base.

## 5. Domain extensions (parallel, against frozen interfaces, order from 4.1)

- [ ] 5.1 Oncology (existing NSCLC rules migrated) and the other domain packages of design.md, one per worker

## 5b. Outcomes, arms, interventions and safety (Decision 11)

- [ ] 5b.1 Endpoint classes and outcome time frames for every domain
- [ ] 5b.2 Arm structure, comparators, dosing and regimen
- [ ] 5b.3 Safety grading and adverse-event terms
- [ ] 5b.4 Results comparability per domain (Decision 12)

## 6. Integration

- [ ] 6.1 Contextual resolution; the assertion layer (add-scoped-assertions) over the new atoms

## 7. Confirmation and release

- [ ] 7.1 A frozen confirmation draw from the reserved pool, gold annotation of its sample, evaluation through the
      real entry point, results per bank and type
  - [x] 7.1a Founder decision B8, the batches (2026-11-01): `sample.pool` names a trial's pool (discovery, or
        confirmation batch 0, 1, 2 by sha256 mod 10); `reserved` unchanged, so discovery is unchanged;
        `trialledger sample --confirmation-batch N` draws from that one batch (`sample.draw_batch`), refused (2)
        by `sample.batch_request` for a batch outside 0-2 or a code version git cannot name; sample.json records
        `drawn_from`, `confirmation_batch`, the batch rule and `code_commit`, and declares no supplement.
        Left (2026-11-01): freezing the confirmation records (Decision 9's downloaded records, not a live
        re-draw), gold annotation and evaluation; the ledger of used batches is task 7.1b. The new decisions
        converge COMPLETE (2026-11-01).
  - [x] 7.1b Inspected trials excluded, the code version named, used batches retired (2026-11-01; Decision 9,
        B4, B8). A confirmation draw takes `--inspected PATH` for each inspected population (the NSCLC record
        folder or its studies.json, the pilot and discovery sample.json files, an audit's balance.json), whose
        IDs `sample.inspected_ids` reads; sample.json keeps each list (`inspected`: path, sha256 of the file,
        the IDs), `sample.screen_inspected` removes them before each stratum's draw, and each stratum and the
        sample count the batch's trials so excluded (`inspected_excluded`). The draw is refused (2) unless
        TrialLedger/ and tests/ are clean at a commit (`sample.code_state`, through the git query
        `sample.git_query`, injectable as `cli.main(git=...)`), and records that commit (`code_commit`), a
        SHA-256 of the tracked source under both (`code_source_digest`) and the paths watched. The declared
        ledger `confirmation_ledger.json` (batch to the commit it confirmed, read by `sample.ledger_batches`)
        is passed as `--batch-ledger`, consulted before the draw and given the batch after the sample is
        written; a batch given to another commit is refused, the same commit may re-draw.
        `sample.batch_request` now names `uncommitted_changes`, `no_inspected`, `inspected_empty`,
        `ledger_unreadable` and `batch_used` beside `unknown_batch` and `no_code_version`. Two-sign tests in
        tests/test_sample.py and tests/test_cli.py; the production path draws a confirmation sample excluding
        its discovery sample. Not converged by Detective, under the founder's acceptance of 2026-11-01 of
        Detective convergence as debt incurred by parallel workflow work, reconciled serially the same day
        (each COMPLETE): the new `sample.inspected_ids`, `sample.ledger_batches`, `sample.screen_inspected` and
        the changed `sample.batch_request` (new signature and codes); `sample.draw_sample` (its new
        `inspected` input), `sample.code_state` and `sample.git_query` are shells, not pinned.
        Revised 2026-11-01 (the founder approved Claude's recommendation): the ledger names the code a batch
        confirmed by its source digest, with the commit beside it (`{"source_digest", "commit"}`), so
        committing the ledger, which moves HEAD and changes no watched file, never refuses a re-draw of the
        same code; `batch_request` takes the digest and names an undigested source `no_code_version`.
        `--batch-ledger` is gone: only the declared `confirmation_ledger.json` at the code's root
        (`sample.LEDGER_NAME`) is read, injectable for tests only as `cli.main(ledger=...)`. After recording
        the batch the draw commits the ledger alone (`git commit -- confirmation_ledger.json`); a failed
        commit is named and ends with 1. `ledger_batches` and `batch_request` changed again; both converge
        COMPLETE after the change.
- [ ] 7.2 Release with the supported/unsupported manifest
