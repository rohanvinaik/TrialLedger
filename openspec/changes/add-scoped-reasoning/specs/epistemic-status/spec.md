# Spec Delta

## Purpose

Every derived value says whether it is known, interpolated or proposed, rests on assertions read in their scope,
and is computed only by rules that apply to the trial's indication.

## ADDED Requirements

### Requirement: Every derived value has an epistemic status
The system SHALL give each derived value one status: known (a record field, a typed assertion, a record-stated or
RxClass class with its warrant, or a strict rule's conclusion from known premises), interpolated (a default's
conclusion or anything derived from one) or proposed; and SHALL keep the justifications of every removed value.

#### Scenario: A default's conclusion is never known
- **WHEN** a default narrows a trial's treatment role
- **THEN** the narrowed role is interpolated, and a strict rule applied to it yields an interpolated value

#### Scenario: A proposal is never built on
- **WHEN** a proposal suggests a narrowing
- **THEN** it is shown on its own, and no rule, stratum, cell or pair consumes it

### Requirement: Premises are scoped assertions
The system SHALL fire a rule only on assertions whose modality, time, branch and cohort satisfy its premises, and
SHALL draw a strict conclusion for a trial only when every eligible branch entails it.

#### Scenario: A disjunction is not a requirement
- **WHEN** inclusion admits "locally advanced or metastatic" disease
- **THEN** no rule premised on required metastatic disease fires

#### Scenario: A permission is not a requirement
- **WHEN** a criterion says previous stage IV disease is permitted
- **THEN** no rule premised on required stage IV disease fires

### Requirement: Rules apply only within their indication
The system SHALL resolve each trial's indication from its literal conditions and its own disease assertions, name
any disagreement with the registry's derived MeSH as a conflict, and treat a rule outside its declared
indications as inapplicable.

#### Scenario: A trial naming no disease
- **WHEN** a trial's conditions name no disease and its record asserts none
- **THEN** every indication-scoped rule is scope-unresolved for it, and nothing is inferred to be negative

### Requirement: Evaluation is declared before it is run
The system SHALL evaluate only through `trialledger resolve` with the fetched records kept, on populations whose
code, rules, sampling and audit rubric were recorded before the run, and SHALL report per bank and slot the
identified, abstained, wrong, inapplicable and audit-unresolved counts.

#### Scenario: An inspected confirmation set is retired
- **WHEN** a confirmation population's records are read to change a rule
- **THEN** that population is development data from then on, and confirmation needs a fresh one
