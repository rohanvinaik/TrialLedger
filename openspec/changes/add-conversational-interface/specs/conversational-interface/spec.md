# Spec Delta

## Purpose

A chatbot uses TrialLedger through tools and skills and never reads a trial itself.

## ADDED Requirements

### Requirement: The chatbot never reads a trial
The system SHALL give the chatbot only tool results, and its skills SHALL forbid answering from a trial's raw
text or filling a value no tool returned.

#### Scenario: A question the tools cannot answer
- **WHEN** a user asks something no tool resolves
- **THEN** the chatbot presents the review-queue question with its closed options, not an answer of its own

### Requirement: Every presented value keeps its status and source
The system SHALL return each value with its status (known, interpolated, proposed), its source and its link, and
the chatbot SHALL present them.

#### Scenario: An interpolated value
- **WHEN** a tool returns an interpolated value
- **THEN** the chatbot presents it as interpolated, with the default it rests on
