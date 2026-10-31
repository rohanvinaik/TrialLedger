# trial-ledger Specification

## Purpose
Holds every element of each pulled registry record as located, scoped evidence, so that every view
TrialLedger produces is derived from the complete record and can point back to its exact source field.

## Requirements

### Requirement: Every element of the record becomes a located entry
The system SHALL enter each value of a pulled study record in the ledger with the value exactly as the
registry wrote it and its location in the record, and SHALL NOT drop, merge or rewrite any value.

#### Scenario: A registered outcome keeps its text and place
- **WHEN** a record registers a primary outcome with a measure, a description and a time frame
- **THEN** the ledger holds three entries carrying those exact strings and their record locations

#### Scenario: Nothing is lost between the record and the ledger
- **WHEN** a ledger is built from a record
- **THEN** rebuilding a record from the ledger's entries reproduces the original exactly, and no entry exists that the record does not contain

### Requirement: Each entry carries the role it plays in the study
The system SHALL record the role of each entry where the registry's structure states it: the outcome type
(primary, secondary or other pre-specified, from the section it is listed in, or the type a posted result
gives it), the arm or event group a count belongs to, and the type the registry gives a reference. It SHALL
NOT infer a role the structure does not state.

#### Scenario: Outcome types come from the registry's own sections
- **WHEN** a record lists outcomes under primary, secondary and other outcomes
- **THEN** each entry carries the type of the section it was listed in

#### Scenario: A count carries its group
- **WHEN** an adverse-event count names a group id
- **THEN** its entry carries that group id and the table (serious or other) it belongs to

#### Scenario: A role the structure does not state stays unstated
- **WHEN** a value's role is expressed only in free text
- **THEN** its entry carries no role, rather than one inferred from the text

### Requirement: Silence is distinct from a recorded absence
The system SHALL report an absent field as `not_applicable` when the registry's definitions limit it to
other study types, as `redacted` when the study is withheld and the registry states the field is redacted
or marked missing for withheld studies, and as `not_reported` otherwise. It SHALL state whether results
were posted from the registry's own results flag.

#### Scenario: A study without posted results says so
- **WHEN** a record's results flag is false
- **THEN** the ledger reports "no results posted" as a stated fact about that study

#### Scenario: An empty field is never read as "none"
- **WHEN** a record omits an optional field
- **THEN** the ledger reports the field as not reported, and no view presents it as zero, none or absent

#### Scenario: A field outside the study type is not applicable
- **WHEN** an observational study has no allocation
- **THEN** the ledger reports allocation as not applicable, not as not reported

#### Scenario: A withheld study's fields are redacted
- **WHEN** a withheld study omits a field the registry redacts for withheld studies
- **THEN** the ledger reports it as redacted, not as not reported

### Requirement: The record is content-addressed
The system SHALL record, in the provenance of every pull, each study's digest (SHA-256 over its record in
canonical JSON) beside its NCT number, the Merkle root of those digests in pull order, and the digest of the
registry's spreadsheet as written, so that any change to a study's record changes its digest and the root.

#### Scenario: Digests identify the record exactly
- **WHEN** a pull is written
- **THEN** its provenance holds each study's digest and the root, and recomputing them from the written studies reproduces them

#### Scenario: A changed record no longer matches
- **WHEN** any value of a written study is changed
- **THEN** its recomputed digest and the recomputed root differ from those recorded

#### Scenario: A mislabelled study is named
- **WHEN** a recorded NCT number differs from the NCT number of the study its digest belongs to
- **THEN** the difference is named

### Requirement: The provenance is committed by a record root
The system SHALL record the code root of the derivation code that wrote the pull, that code's git commit,
and a record root committing to the whole provenance, the study digests with their labels, the studies' root
and the spreadsheet's digest among it, so that any change to the provenance changes the record root.

#### Scenario: A changed provenance no longer matches
- **WHEN** any provenance entry of a written pull is changed, such as its query or its data timestamp
- **THEN** the recomputed record root differs from the one recorded

### Requirement: Free text is carried, never interpreted
The system SHALL carry free-text fields, such as eligibility criteria and descriptions, verbatim, and SHALL
NOT derive structured values from them in this capability.

#### Scenario: Eligibility text stays whole
- **WHEN** a record's eligibility criteria are free text
- **THEN** the ledger holds that text unchanged, character for character
