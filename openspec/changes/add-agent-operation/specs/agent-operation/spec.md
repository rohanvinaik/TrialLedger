# Spec Delta

## Purpose

An LLM agent pointed at the repository installs TrialLedger, runs one operation for a user's question about
clinical trials, answers from the record of truth it writes, and hands the user the workbook.

## ADDED Requirements

### Requirement: One operation from a request to a record and a workbook
The system SHALL turn a structured request into a run folder holding `landscape.json`, `landscape.xlsx` and
`manifest.json`, every value with its status, source field and link.

#### Scenario: A drug class in a disease
- **WHEN** the request names a drug class and a condition
- **THEN** the record holds every matching study's ten-point extract and the cohort profile, and its scope lists
  each member drug the class resolved to, with the class's source

### Requirement: Resolution is symbolic, shown and never guessed
The system SHALL resolve drug classes, mechanisms and condition classes through named sources, write every
expansion into the record before any study is read, and return a named code for what it cannot resolve.

#### Scenario: An unknown class
- **WHEN** the request names a class RxClass does not hold
- **THEN** the run stops with `class_not_found` and no query is sent

### Requirement: The operation needs no network of its own
The system SHALL run to completion whether or not its own process can reach the registry: fetching directly when
it can, and otherwise naming the exact URLs it needs and verifying each fetched body as the API's own.

#### Scenario: A sandbox without outbound HTTP
- **WHEN** `doctor` finds the registry unreachable and the run is started
- **THEN** the run writes `next.json` and stops with `awaiting_fetch`; after the agent saves each body, the next run
  verifies and continues until `complete`

#### Scenario: A body that is not the API's answer
- **WHEN** a fetched file is not a registry page (an error page, a truncated body, another snapshot)
- **THEN** the run refuses it by name and writes no record

### Requirement: Planned is never reported
The system SHALL keep registered outcomes apart from posted results; no field presents a registered outcome as
efficacy or safety evidence.

#### Scenario: A study without posted results
- **WHEN** a study has registered outcomes and no results
- **THEN** its record lists the outcomes as planned and states "no results posted"

### Requirement: Edits never overwrite a sourced value
The system SHALL read an edited workbook back as the user's assertions beside the sourced values.

#### Scenario: A user changes an exclusion cell
- **WHEN** the edited workbook is read back
- **THEN** the record shows the user's text as a user assertion and the registry's value unchanged
