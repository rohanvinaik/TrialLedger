# Spec Delta

## Purpose

Measures every typed element of a set of comparable trials against that set, so that what is standard, what
is distinctive, what tracks a mechanism, which designs are unoccupied and which results can be compared are
computed from the registry and shown with the trials they rest on.

## ADDED Requirements

### Requirement: Profiling runs over a pulled folder and writes beside it
`trialledger profile <folder>` SHALL read the folder's `studies.json`, SHALL write `design.xlsx` and the
intervention-class cache `classes.json` into the folder, and SHALL NOT change the folder's other files. It
SHALL write nothing if the record does not verify against its recorded digests.

#### Scenario: The pull's files are untouched
- **WHEN** `trialledger profile` runs on a written folder
- **THEN** `studies.json`, `studies.csv`, `review.xlsx` and `record.xlsx` are byte-for-byte unchanged and the folder still verifies

#### Scenario: A tampered record is refused
- **WHEN** a study in the folder's `studies.json` no longer matches its recorded digest
- **THEN** the command names it and writes nothing

### Requirement: Frequencies have explicit denominators
The system SHALL report, for every typed element, the number of trials stating it, the number of trials whose
text could have stated it (trials whose eligibility was itemized and typed), the frequency over that
denominator, its surprisal in bits and the number of distinct lead sponsors among the trials stating it.

#### Scenario: An untyped trial is not counted as lacking an element
- **WHEN** a trial's eligibility could not be itemized
- **THEN** it is excluded from every element's denominator, and the number so excluded is shown

### Requirement: Standard language is a tier, not a verdict
The system SHALL mark as standard the elements stated by at least a named share of the trials in a stratum,
with the share shown, and SHALL NOT treat a standard element as clinically unimportant or a rare element as
clinically important.

#### Scenario: A near-universal criterion
- **WHEN** an element is stated by 95% of the trials in a stratum and the standard share is 90%
- **THEN** it is marked standard in that stratum, with its frequency and sponsor count

### Requirement: Mechanism signals are proposals
The system SHALL compare each element's frequency among trials whose experimental arm carries a mechanism
class with its frequency among the other trials of the same stratum, report the counts, the difference, the
number of distinct sponsors and the number of trials with an unresolved class, and SHALL present every such
association as a proposed relation, never as an established one.

#### Scenario: One sponsor cannot make a signal
- **WHEN** every trial stating an element in a mechanism class shares one lead sponsor
- **THEN** the association is reported with a sponsor count of one and is not offered as a proposal

#### Scenario: Unresolved classes are shown
- **WHEN** some trials in a stratum have an experimental intervention with no class
- **THEN** every mechanism signal in that stratum shows how many

### Requirement: Design-space occupancy distinguishes empty from unknown
The system SHALL count trials in each combination of resolved coordinates and mechanism class, report
separately the trials whose coordinates are unresolved, and SHALL NOT report a combination as unoccupied
when unresolved trials could fall in it.

#### Scenario: An empty cell with unresolved trials
- **WHEN** no resolved trial falls in a combination and some unresolved trials could
- **THEN** the combination is reported as unknown, with the number of trials that could fall in it

#### Scenario: A failed trial occupies its cell
- **WHEN** a terminated or withdrawn trial falls in a combination
- **THEN** it counts as occupying it, with its status shown

### Requirement: Results are grouped only when like for like
The system SHALL group posted outcome results by endpoint class and setting, show each result's arm, value,
unit, measure type and time frame exactly as posted, and SHALL NOT present results with different endpoint
classes, settings or units as comparable.

#### Scenario: Different endpoints are kept apart
- **WHEN** one trial posts overall survival and another posts progression-free survival
- **THEN** they appear in different groups

### Requirement: Every derived value carries a warrant
The system SHALL give every row of `design.xlsx` a warrant committing to the study digest or digests it
derives from and to the rule that derived it.

#### Scenario: A row names its basis
- **WHEN** a row of `design.xlsx` reports a frequency, a coordinate or a signal
- **THEN** it carries a warrant over its rule and the digests of the studies it counts
