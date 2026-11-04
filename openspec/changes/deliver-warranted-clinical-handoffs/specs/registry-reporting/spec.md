## ADDED Requirements

### Requirement: Literal section formatting remains lossless
The system SHALL recognize standard inclusion/exclusion headings across letter-case and line-ending
variants without interpreting clinical text. It SHALL preserve original text and offsets, abstain on
ambiguous repeated or reversed sections, and retain supported historical report verification.

#### Scenario: Lowercase registry headings
- **WHEN** standard headings are written as Inclusion criteria and Exclusion criteria
- **THEN** their passages retain the correct structural section and exact literal local context
- **AND** the parts reconstruct the source without normalization

#### Scenario: A clinical phrase resembles a heading
- **WHEN** a heading occurs inside a sentence, bullet or nonstandard cohort label
- **THEN** it does not establish a top-level section or clinical entry scope

### Requirement: Study identity is available in bounded indexes
The saved-study index SHALL include source titles and acronym with identifier and current index fields.
Missing identity fields SHALL remain distinguishable from actual empty strings.

#### Scenario: A name search returns a study and its emulation
- **WHEN** the assistant retrieves the study index through CLI or MCP
- **THEN** source titles permit identity inspection without separate reads of each title

### Requirement: Compact tables conserve source scope
A compact baseline view SHALL retain every represented value, group identity, denominator, parameter,
unit, class/category and exact address. It SHALL NOT join populations, periods or similarly titled groups.
Empty optional annotation cells SHALL be blank while genuine source notes and derivation provenance remain.

#### Scenario: NYHA has three classes and three source groups
- **WHEN** a compact table presents those measurements
- **THEN** all nine source values remain individually addressable and the Total group is not added to its component groups

#### Scenario: Safety has no optional note
- **WHEN** neither a source note nor a derivation note applies
- **THEN** the Notes cell is blank without changing clinical missing-value semantics in other columns

#### Scenario: An at-risk denominator uses a group total
- **WHEN** that warranted transformation supplies a denominator
- **THEN** its rule and source provenance remain visible in Notes
