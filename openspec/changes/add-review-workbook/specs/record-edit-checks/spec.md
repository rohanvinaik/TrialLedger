# Spec Delta

## Purpose

Checks each record against itself using approved relations among the registry's structured fields, so that
internal contradictions surface as queries for a reviewer instead of passing silently into any view.

## ADDED Requirements

### Requirement: Checks use only approved relations over structured fields
The system SHALL run only checks from an approved, versioned list, each relating structured fields of one
record and each with a stated justification. It SHALL NOT check, or draw conclusions from, free text.

#### Scenario: Completion status against completion date type
- **WHEN** a record's overall status is completed and its completion date is typed estimated
- **THEN** the check reports a conflict naming both fields and their values

#### Scenario: Arms name only declared interventions
- **WHEN** an arm lists an intervention name that no declared intervention of the study carries
- **THEN** the check reports a conflict naming the arm and the undeclared intervention

#### Scenario: Affected never exceeds at risk
- **WHEN** an adverse-event count reports more participants affected than at risk in its group
- **THEN** the check reports a conflict naming the event, the group and both counts

#### Scenario: Age bounds are ordered
- **WHEN** a record's minimum age exceeds its maximum age
- **THEN** the check reports a conflict naming both ages

### Requirement: Every check has a named outcome
The system SHALL report each check on each record as consistent, conflict or not checkable, and SHALL
report not checkable whenever a field the check needs is absent.

#### Scenario: A missing input is not a pass
- **WHEN** a check needs a field the record does not report
- **THEN** the outcome is not checkable, never consistent

### Requirement: A conflict is shown, never resolved
The system SHALL present every conflict to the reviewer with the fields and values involved. It SHALL NOT
change, drop or choose between the conflicting values.

#### Scenario: Both values survive a conflict
- **WHEN** a check reports a conflict
- **THEN** both conflicting values remain in the ledger and in every view, exactly as the registry wrote them
