# Spec Delta

## Purpose

Projects the ledger into a workbook a clinical reviewer can open without a terminal, organised around the
ten study-design questions, with every value labelled by how it was obtained and every source one click away.

## ADDED Requirements

### Requirement: The workbook answers the ten design questions from the ledger
The system SHALL write, for every pulled study, the population fields, the eligibility criteria, every
registered outcome with its type and time frame, other pre-specified outcomes, and adverse events per group,
all taken from the ledger.

#### Scenario: Eligibility and safety are present
- **WHEN** a pulled study has eligibility criteria and posted adverse events
- **THEN** the workbook shows the criteria in full and every serious and other adverse event with its term, organ system, group, number affected and number at risk

### Requirement: Every value is labelled stated, computed or needs review
The system SHALL label each value as stated (read from a structured field), computed (derived by a named
rule, shown with its inputs) or needs review (not determinable from structured fields, shown with its
sources). It SHALL NOT fill a needs-review value.

#### Scenario: Line of therapy is a review item
- **WHEN** a study's line of therapy is not a structured field of its record
- **THEN** the workbook marks it needs review and shows the eligibility text beside it

#### Scenario: Nothing unsourced is filled
- **WHEN** no structured field and no named rule determines a value
- **THEN** the cell is marked needs review and holds no value

### Requirement: Eligibility is split only when the record makes the split unambiguous
The system SHALL show inclusion and exclusion criteria separately only when the eligibility text contains
the registry's standard inclusion heading and exclusion heading exactly once each, in that order. Otherwise
it SHALL show the whole text and say that it was not split.

#### Scenario: Standard headings split the text
- **WHEN** the eligibility text has one "Inclusion Criteria" heading followed by one "Exclusion Criteria" heading
- **THEN** the workbook shows the two parts separately, and joined they reproduce the original text exactly

#### Scenario: Ambiguous text stays whole
- **WHEN** a heading is missing, repeated or out of order
- **THEN** the workbook shows the whole text unchanged and marks it not split

### Requirement: A study without posted results says so
The system SHALL state "no results posted" for the results and safety items of every study whose registry
results flag is false, and SHALL NOT leave those items blank or show them as zero events.

#### Scenario: An ongoing study
- **WHEN** a pulled study has no posted results
- **THEN** its safety and results items read "no results posted" and its linked publications are listed beside them

### Requirement: Every study links to its sources
The system SHALL give each study its registry page, every linked publication with the role the registry
assigns it and its citation, and every document the sponsor posted, each as a working link.

#### Scenario: Results publications are identified
- **WHEN** a record links a publication the registry types as a result
- **THEN** the workbook lists it as a results publication, with its PubMed link and citation

### Requirement: The workbook is written with the record or not at all
The system SHALL write the workbook inside the same all-or-nothing step as `studies.json` and `studies.csv`,
derived only from the record being written, and SHALL NOT leave a workbook behind when any file fails.

#### Scenario: A failed write leaves nothing
- **WHEN** writing any of the three files fails
- **THEN** no output directory and no partial workbook remain
