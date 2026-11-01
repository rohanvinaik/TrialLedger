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

### Requirement: Ranking never decides admissibility
The system SHALL decide which designs, comparable trials and elements are admissible by hard constraints alone,
and order the admissible ones by a separate score; a score SHALL never admit or exclude.

#### Scenario: A highly ranked trial outside the constraints
- **WHEN** a trial scores high on shared criteria but its indication lies outside the comparability constraint
- **THEN** it is not a comparable trial, whatever its score

#### Scenario: A standard the design lacks
- **WHEN** a criterion is standard among comparable trials with probability P and the design lacks it
- **THEN** the design carries the cost -log P for that absence and names it among what must be justified

### Requirement: The remainder is closed by suggested decisions
The system SHALL surface what the rules leave open one question at a time, the question whose answer closes the
most of the remaining admissible designs first, with a suggested answer chosen by warrant and then by closure,
shown with what accepting it would fix.

#### Scenario: A setting choice that settles several variables
- **WHEN** two settings remain admissible and one of them, through entailment, also fixes the line of therapy,
  the comparator and the prior-therapy criteria
- **THEN** the setting is asked before variables it would settle, and its suggestion names everything accepting it
  would fix

#### Scenario: Accept every suggestion
- **WHEN** the user accepts every suggestion
- **THEN** the design closes, each accepted choice recorded as the user's with its warrant
