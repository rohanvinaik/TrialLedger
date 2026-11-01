# Spec Delta

## Purpose

From a design brief and a landscape run, TrialLedger builds a draft trial design by symbolic operations, every
element warranted.

## ADDED Requirements

### Requirement: Every design element carries its warrant and status
The system SHALL write each design variable with its value, its status (known, interpolated, proposed) and the
rule, premises or corpus statistic it rests on.

#### Scenario: An inherited standard criterion
- **WHEN** a criterion meets the standard tier among the landscape's comparable trials
- **THEN** the design includes it as interpolated, citing the tier and the trials

### Requirement: Deductions are entailed, not judged
The system SHALL derive consequences of the brief and fixed variables through the entailment procedure, naming the
premises used.

#### Scenario: A study of outcomes in pregnancy
- **WHEN** the brief's question is an outcome in pregnancy
- **THEN** the population is restricted to people who can be pregnant, as a known deduction with its premises

#### Scenario: Contradictory requirements
- **WHEN** the brief and a fixed variable cannot both hold
- **THEN** the design reports INCONSISTENT with a minimal set of the conflicting premises and writes no design

### Requirement: Choices among admissible designs are the user's
The system SHALL settle a choice among admissible designs only by the user's stated priorities or answers, and
record it as the user's.

#### Scenario: Two admissible primary endpoints
- **WHEN** two endpoint classes are each admissible and no priority settles them
- **THEN** the design returns a closed question with both options and their corpus statistics
