# Spec Delta

## Purpose

Resolves each trial's design coordinates, such as its treatment setting, its prior lines of therapy and its
biomarker selection, as sets of still-possible values narrowed only by evidence and relations, so that what a
trial's design entails is computed and every contradiction is shown.

## ADDED Requirements

### Requirement: Each design coordinate is a domain of possible values
The system SHALL hold each design coordinate of each trial as the set of values still possible. A single
value SHALL be reported as resolved, several as unresolved with the values kept, and an empty set as a
conflict. An unresolved coordinate SHALL NOT be reported as any one value.

#### Scenario: No evidence leaves every value open
- **WHEN** nothing in a trial's typed evidence bears on its setting
- **THEN** its setting is unresolved with every setting value kept

#### Scenario: Evidence narrows the domain
- **WHEN** a trial's criteria state zero prior systemic lines for advanced disease
- **THEN** its prior-lines coordinate is resolved to zero, citing that criterion

### Requirement: Relations are approved or proposed, and only approved relations change a reported value
The system SHALL apply relations among coordinates and evidence to a fixed point, each relation carrying an
id, a statement, its basis and its approval. It SHALL report the domains under approved relations, and
separately the further narrowing proposed relations would make, without applying a proposed relation to a
reported value.

#### Scenario: A proposed relation is shown, not applied
- **WHEN** a proposed relation would narrow a trial's setting to adjuvant
- **THEN** the setting reported under approved relations is unchanged, and the proposed narrowing is shown beside it with the relation's id

#### Scenario: Closure reaches a fixed point
- **WHEN** one relation narrows a coordinate that another relation reads
- **THEN** the second relation is applied to the narrowed coordinate, and the result does not depend on the order relations are listed in

### Requirement: A contradiction is a named conflict, never a choice
The system SHALL report a coordinate whose domain becomes empty as a conflict naming every piece of evidence
and every relation that removed a value, and SHALL NOT choose, vote or drop evidence to resolve it.

#### Scenario: Contradictory criteria
- **WHEN** one criterion states zero prior lines for advanced disease and another requires progression after one platinum-based regimen for advanced disease
- **THEN** the prior-lines coordinate is a conflict naming both criteria

### Requirement: Every narrowing carries its derivation
The system SHALL record, for every value removed from a domain, the evidence spans or registry fields and
the relation that removed it, so that each reported domain can be re-derived from the record.

#### Scenario: A resolved value shows its basis
- **WHEN** a coordinate is resolved
- **THEN** its derivation lists the criteria, fields and relations that removed every other value

### Requirement: Silence never narrows a domain
The system SHALL NOT remove a value from a domain because a trial does not mention it. A default value SHALL
be applied only by an approved relation whose guard requires that no relevant evidence, typed or untyped, is
present.

#### Scenario: An unmentioned biomarker stays open
- **WHEN** a trial's criteria never mention ALK
- **THEN** its ALK-selection coordinate keeps every value, unless an approved guarded relation applies and the trial has no untyped criterion that could concern ALK
