# Spec Delta

## Purpose

Every declared clinical-trial type is typed by deterministic recognizers over one validated registry, measured
per bank at three levels with gold recall, and confirmed on frozen records no rule was written against.

## ADDED Requirements

### Requirement: A bank recognizes and never decides
The system SHALL have each bank return atoms and named findings for one criterion's text, with no network,
model or clock, and SHALL NOT read NO_TRIGGER as the absence of a concept.

#### Scenario: A measurement and an event in one criterion
- **WHEN** a criterion reads "HbA1c ≤8.0% and no myocardial infarction within six months before randomization"
- **THEN** the banks emit an HbA1c measurement expression and a myocardial-infarction event mention with its anchored window, and leave the negation and conjunction to the assertion layer

### Requirement: Indication never suppresses an explicit mention
The system SHALL use the trial's indication only to disambiguate or specialize a mention and SHALL recognize an
explicit eligibility mention whatever the indication.

#### Scenario: A healthy-volunteer trial excludes dialysis
- **WHEN** a healthy-volunteer trial's criterion excludes participants on dialysis
- **THEN** the renal exposure is recognized

### Requirement: Every concept has one owner
The system SHALL compile one registry from per-package fragments and SHALL refuse a build with a duplicate or
incompatible concept, an unknown argument, or a missing provenance entry.

#### Scenario: Two packages define HbA1c
- **WHEN** a domain package defines HbA1c beside the measurements package
- **THEN** the registry build fails naming both owners

### Requirement: Recall is measured against gold annotation
The system SHALL report each bank's recall only against independently annotated opportunities, and SHALL report
agreement between models as model-review agreement unless adjudication is grounded in the source.

#### Scenario: Only emitted claims were audited
- **WHEN** a bank's claims were audited but no gold sample was annotated
- **THEN** its precision is reported and its recall is reported as not measured
