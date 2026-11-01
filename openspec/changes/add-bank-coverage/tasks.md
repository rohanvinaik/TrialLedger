# Tasks — add-bank-coverage

## 0. Founder decisions

- [x] 0.1 The nine decisions, recorded in design.md (2026-11-01)

## 1. Contracts and evaluation definitions (frozen before any package)

- [ ] 1.1 The atom schema extension, predicate families, findings and their codes, offset convention
- [ ] 1.2 The registry loader and validator, fragment format, ownership rules
- [ ] 1.3 The provenance schema: concept authority apart from rule provenance; exposure records
- [ ] 1.4 The supported-type matrix and its manifest format
- [ ] 1.5 The evaluation module: three levels, matching rules, measures with denominators, gold-annotation format

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
- [ ] 7.2 Release with the supported/unsupported manifest
