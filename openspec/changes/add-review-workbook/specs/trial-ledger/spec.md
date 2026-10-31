# Spec Delta

## Purpose

Holds every element of each pulled registry record as located, scoped evidence, so that every view
TrialLedger produces is derived from the complete record and can point back to its exact source field.

## ADDED Requirements

### Requirement: Every element of the record becomes a located entry
The system SHALL enter each value of a pulled study record in the ledger with the value exactly as the
registry wrote it and its location in the record, and SHALL NOT drop, merge or rewrite any value.

#### Scenario: A registered outcome keeps its text and place
- **WHEN** a record registers a primary outcome with a measure, a description and a time frame
- **THEN** the ledger holds three entries carrying those exact strings and their record locations

#### Scenario: Nothing is lost between the record and the ledger
- **WHEN** a ledger is built from a record
- **THEN** every value present in the record is present in the ledger, and no entry exists that the record does not contain

### Requirement: Each entry carries the role it plays in the study
The system SHALL record the role of each entry where the registry's structure states it: the outcome type
(primary, secondary or other pre-specified), the arm or event group a count belongs to, and whether a
reference is background, result or derived. It SHALL NOT infer a role the structure does not state.

#### Scenario: Outcome types come from the registry's own sections
- **WHEN** a record lists outcomes under primary, secondary and other outcomes
- **THEN** each entry carries the type of the section it was listed in

#### Scenario: A role the structure does not state stays unstated
- **WHEN** a value's role is expressed only in free text
- **THEN** its entry carries no role, rather than one inferred from the text

### Requirement: Silence is distinct from a recorded absence
The system SHALL distinguish a field the registry left empty from a field that records an absence, and
SHALL state whether results were posted from the registry's own results flag.

#### Scenario: A study without posted results says so
- **WHEN** a record's results flag is false
- **THEN** the ledger records "no results posted" as a stated fact about that study

#### Scenario: An empty field is never read as "none"
- **WHEN** a record omits an optional field
- **THEN** the ledger records the field as not reported, and no view presents it as zero, none or absent

### Requirement: Free text is carried, never interpreted
The system SHALL carry free-text fields, such as eligibility criteria and descriptions, verbatim, and SHALL
NOT derive structured values from them in this capability.

#### Scenario: Eligibility text stays whole
- **WHEN** a record's eligibility criteria are free text
- **THEN** the ledger holds that text unchanged, character for character
