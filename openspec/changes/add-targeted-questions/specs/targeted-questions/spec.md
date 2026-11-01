# Spec Delta

## Purpose

A local model answers only specific questions the symbolic system poses, each with closed options and a bounded
source envelope; its answers are validated, cached, adjudicated by a human, and never become readings.

## ADDED Requirements

### Requirement: A question carries only its envelope
The system SHALL send a model one question at a time with closed options that include insufficient context, and
only the target span, its heading ancestry, its parent stem and the siblings an explicit conjunction or
alternative needs; it SHALL refuse, not truncate, an envelope over its budget.

#### Scenario: A list item that continues a stem
- **WHEN** a criterion is item "a." of "Patients must satisfy either: a. … or b. …"
- **THEN** its envelope carries the stem and item "b.", and nothing else of the trial

### Requirement: The transport is pinned and constrained
The system SHALL call an explicitly named local model whose installed digest is verified before and after every
call, with a schema-constrained answer at temperature 0, and SHALL treat a truncated or malformed answer as an
error, never as a verdict.

#### Scenario: The model changes under the tag
- **WHEN** the installed digest differs from the pinned one
- **THEN** the answer is refused with a named error

### Requirement: Every source piece has a unit
The system SHALL account for every eligibility piece, every gap between pieces, every registered outcome and
every intervention of a sampled trial, so an omission has a unit to be found in.

#### Scenario: A criterion no bank typed
- **WHEN** a criterion carries no atom
- **THEN** it becomes an untyped-criterion question, never silently absent from the audit

### Requirement: Accepted answers are sampled for the human
The system SHALL send every challenged item, and a declared random sample of accepted items including empty
outputs, to a human who records what the source supports before seeing the model's verdict.

#### Scenario: The model accepts a wrong atom
- **WHEN** a sampled accepted atom is wrong by the human's reference
- **THEN** it is counted among errors found in accepted items, and the model's acceptance rate of known errors is reported

### Requirement: The live sample is declared and kept
The system SHALL draw interventional trials live by seeded random draws within declared strata, record each
trial's inclusion probability, never draw from the hash-reserved confirmation pool for discovery, and keep the
id lists, retrieval times, seed and every resolved record.

#### Scenario: A trial in two strata
- **WHEN** a trial is drawn in two strata
- **THEN** it is audited once, with its union inclusion probability and both memberships kept
