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

  Not converged with Detective. The founder accepted on 2026-11-01 Detective convergence as debt incurred by
  parallel workflow work, to be reconciled serially afterwards; under that acceptance, and not settled, these
  pinned decisions of group 1 have two-sign intent tests but no converge:
  `semantics.contracts`: `atom_digest`, `atom_problems`, `result_problems`, `slug`, `legacy_concept_id`,
  `from_legacy`, `to_legacy`, `legacy_result`;
  `semantics.loader`: `fragment_from_data`, `registry_problems` (changed: definition dates, unversioned
  scales), `registry_flags` (new), `atom_registry_problems`;
  `typematrix`: `study_coordinates`, `universe_status`, `manifest_problems`;
  `evaluation`: `agreement_kind` (changed: quotes at their spans, distinct annotators), `gold_problems`
  (changed), `at_level` (new), `match` and `judge` (changed: mixed levels refused), `bounds`, `rate` (changed:
  per-trial counts), `recall`, `precision`, `miss_rate`, `unit_rates`, `complete_representation`,
  `parameter_accuracy` (changed: level filtering), `clustered_lower_bound` (new), `precision_group` (new),
  `threshold_verdict` (changed). The deep gate (`scripts/ci_local.sh --deep`) flags each until it is
  converged. Outside this change, `banks.permitted`, `classes.rxnorm_concepts` and `classes.name_identity`
  break their tag over two lines, so the deep gate's list still misses them.

## 2. The existing banks against the contract

- [ ] 2.1 Each bank audited, its rules kept or retired with reasons, its NSCLC and pilot exposure recorded

## 3. Shared primitives and general packages (parallel, file-disjoint)

- [ ] 3.1 Shared parsers: numbers, units (UCUM), durations, intervals, reference expressions
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
        are not yet converged by Detective.
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
        Detective convergence as debt incurred by parallel workflow work, to be reconciled serially afterwards
        (not settled): the new `sample.inspected_ids`, `sample.ledger_batches`, `sample.screen_inspected` and
        the changed `sample.batch_request` (new signature and codes); `sample.draw_sample` (its new
        `inspected` input), `sample.code_state` and `sample.git_query` are shells, not pinned.
        Revised 2026-11-01 (the founder approved Claude's recommendation): the ledger names the code a batch
        confirmed by its source digest, with the commit beside it (`{"source_digest", "commit"}`), so
        committing the ledger, which moves HEAD and changes no watched file, never refuses a re-draw of the
        same code; `batch_request` takes the digest and names an undigested source `no_code_version`.
        `--batch-ledger` is gone: only the declared `confirmation_ledger.json` at the code's root
        (`sample.LEDGER_NAME`) is read, injectable for tests only as `cli.main(ledger=...)`. After recording
        the batch the draw commits the ledger alone (`git commit -- confirmation_ledger.json`); a failed
        commit is named and ends with 1. `ledger_batches` and `batch_request` changed again; both stay in the
        Detective debt.
- [ ] 7.2 Release with the supported/unsupported manifest
