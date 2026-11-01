# Tasks — add-bank-coverage

## 0. Founder decisions

- [ ] 0.1 The nine decisions listed in design.md

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

## 6. Integration

- [ ] 6.1 Contextual resolution; the assertion layer (add-scoped-assertions) over the new atoms

## 7. Confirmation and release

- [ ] 7.1 A frozen confirmation draw from the reserved pool, gold annotation of its sample, evaluation through the
      real entry point, results per bank and type
- [ ] 7.2 Release with the supported/unsupported manifest
