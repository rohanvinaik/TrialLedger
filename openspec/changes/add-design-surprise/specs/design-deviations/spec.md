# Spec Delta

## Purpose

Turns disagreement with expected trial design into information: each predicate's observation is typed, each
expectation is declared with its conditioning, and each deviation keeps a status that never folds a valid but
unexplained design choice into noise.

## ADDED Requirements

### Requirement: Every predicate has an observation status
The system SHALL give each declared predicate of each trial one status: present, explicitly negated, not
documented, unresolved or not applicable, with its scope and the spans it rests on. It SHALL NOT treat not
documented as permitted.

#### Scenario: An omitted exclusion is not permission
- **WHEN** a trial's criteria never mention autoimmune disease
- **THEN** the predicate "excludes active autoimmune disease" is not documented, and no view reports the trial as admitting autoimmune disease

#### Scenario: An abbreviated record's silence is unresolved
- **WHEN** a trial's criteria never mention autoimmune disease and the record says it lists only key criteria
- **THEN** the predicate is unresolved, with the reason that the record is abbreviated

#### Scenario: A qualified exception is its own observation
- **WHEN** a trial excludes active autoimmune disease but admits controlled hypothyroidism
- **THEN** the exclusion is present and the qualifier is recorded with its span, not read as a deviation

### Requirement: Expectations are declared with their conditioning
The system SHALL compute an expectation only for a declared predicate over a declared conditioning cell that
excludes the predicate and anything inferred from it, report the rarity of each trial's observation as
−log2 of its frequency in the cell with the cell's size, fall back only to a declared parent cell and say so, and
abstain where neither has the declared support.

#### Scenario: A sparse cell abstains
- **WHEN** a trial's cell holds fewer trials than the declared support and its parent cell does too
- **THEN** no rarity is reported for that trial, and the reason is named

### Requirement: Deviations keep separate statuses
The system SHALL classify each deviation as invalid extraction, scope unresolved, omission (not
documented), verified deviation (admitted) or explanation supported, and SHALL record replication across independent sponsors separately; a verified deviation
SHALL remain verified when no explanation is found.

#### Scenario: A first-of-its-kind exception survives
- **WHEN** a correctly typed trial deviates from an expectation with no compensating element, no recurrence and no explanatory coordinate
- **THEN** it is a verified deviation, unexplained, and is never classified as noise

### Requirement: Near-miss pairs are relative to a declared representation
The system SHALL pair two trials only when every predicate of a declared representation is known and equal for
both and exactly one verified predicate differs, and SHALL report the representation, sponsor lineage, era and
cohort structure with each pair.

#### Scenario: An unknown never matches
- **WHEN** one trial's setting is unresolved
- **THEN** it forms no near-miss pair on a representation that includes setting
