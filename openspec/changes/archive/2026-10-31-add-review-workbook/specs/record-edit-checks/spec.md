# Spec Delta

## Purpose

Checks each record against itself using approved relations among the registry's structured fields, so that
internal contradictions surface as queries for a reviewer instead of passing silently into any view.

## ADDED Requirements

### Requirement: Checks use only approved relations over structured fields
The system SHALL run only checks from an approved, versioned list, each relating structured fields of one
record and each carrying the registry's own words that state the relation. A check that is not approved
SHALL NOT be run or gathered. It SHALL NOT check, or draw conclusions from, free text.

#### Scenario: A proposed check never runs
- **WHEN** a check is proposed and not approved
- **THEN** it is not evaluated on any record, and nothing only it reads can affect the checks that run

#### Scenario: Completion status against completion date type
- **WHEN** a record's overall status is completed and its completion date is typed estimated
- **THEN** the check reports a conflict naming both fields and their values

#### Scenario: Arms name only declared interventions
- **WHEN** an arm lists an intervention name that no declared intervention of the study carries in the registry's `<type label>: <name>` form
- **THEN** the check reports a conflict naming the arm and the undeclared intervention

#### Scenario: Affected never exceeds at risk
- **WHEN** an adverse-event count reports more participants affected than at risk in its group
- **THEN** the check reports a conflict naming the event, the group and both counts

#### Scenario: A blank at-risk count is never zero
- **WHEN** an adverse-event count leaves the number at risk blank
- **THEN** the check uses the group's total at risk for that table, as the registry's definition directs, and says so

#### Scenario: Age bounds are ordered
- **WHEN** a record's minimum age exceeds its maximum age in units that convert exactly
- **THEN** the check reports a conflict naming both ages

### Requirement: Every check has a named outcome
The system SHALL report each check on each record as `consistent`, `conflict`, `not_applicable` or
`not_checkable`, and SHALL report `not_checkable` whenever a value the check needs is absent, malformed
(present but not of the type the registry gives it) or too imprecise to decide it.

#### Scenario: A missing input is not a pass
- **WHEN** a check needs a field the record does not report
- **THEN** the outcome is not checkable, never consistent

#### Scenario: A rule that does not arise is not a pass
- **WHEN** a check's condition does not arise in the record, such as a completion rule for a recruiting study
- **THEN** the outcome is not applicable, never consistent

#### Scenario: Imprecision is not a conflict
- **WHEN** two partial dates overlap, or two ages are in units with no exact conversion
- **THEN** the outcome is not checkable, never conflict and never consistent

#### Scenario: A malformed input is not a pass
- **WHEN** a value a check reads is present but not of the type the registry gives it
- **THEN** the outcome is not checkable, and its detail names the value

#### Scenario: An unknown definition is not a conflict
- **WHEN** a cross-reference matches nothing the record defines, while a definition it could match is incomplete (an intervention without a type or name, an arm without a label, an event group without an id)
- **THEN** the outcome is not checkable, never conflict

#### Scenario: A stated count is never replaced
- **WHEN** a record states a group's number not completed
- **THEN** the check uses that number, and reports not checkable when it is not a whole number; Started minus Completed is used only when no number not completed is stated

### Requirement: A conflict is shown, never resolved
The system SHALL present every conflict to the reviewer with the fields and values involved. It SHALL NOT
change, drop or choose between the conflicting values.

#### Scenario: Both values survive a conflict
- **WHEN** a check reports a conflict
- **THEN** both conflicting values remain in the ledger and in every view, exactly as the registry wrote them
