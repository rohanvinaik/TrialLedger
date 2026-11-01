# Spec Delta

## Purpose

Every eligibility claim a consumer reads is a scoped constraint with a proof that keeps its subject, Boolean
structure, qualifiers, applicability, time, cohort and epistemic dependencies; where that proof cannot be built,
a named abstention and a bounded question.

## ADDED Requirements

### Requirement: Alternatives are never requirements of each branch
The system SHALL compile coordinated alternatives into a disjunction and SHALL conclude a requirement for the
trial only when every feasible branch entails it.

#### Scenario: Locally advanced or metastatic
- **WHEN** an inclusion criterion requires "locally advanced or metastatic NSCLC"
- **THEN** metastatic disease is not entailed, and no relation premised on required metastatic disease fires

#### Scenario: A shared conclusion
- **WHEN** the criteria compile to (A and B) or (A and C)
- **THEN** A is entailed and neither B nor C is

### Requirement: A qualified exclusion excludes only the qualified subset
The system SHALL keep a qualifier attached to its literal and SHALL never project an exclusion of the qualified
conjunction onto its components.

#### Scenario: HIV with CD4 below 200
- **WHEN** an exclusion criterion reads "HIV positive with current CD4+ count < 200"
- **THEN** no consumer reads an exclusion of HIV, and an HIV-positive participant with CD4 of 200 or more is not excluded by this criterion

### Requirement: Another person's attribute never transfers to the participant
The system SHALL bind each literal to its subject and SHALL NOT attribute a source case's, partner's or
caregiver's condition to the participant.

#### Scenario: The source case's HIV
- **WHEN** an exclusion criterion reads "The source case a person with HIV antiretroviral resistances"
- **THEN** no participant HIV exclusion is concluded

### Requirement: Definitions and conditional obligations impose nothing by themselves
The system SHALL store definitions apart from their use and compile a conditional obligation as an implication
from its antecedent.

#### Scenario: A post-menopause definition
- **WHEN** a criterion defines post-menopausal status by age, amenorrhea and prior chemotherapy
- **THEN** no age, chemotherapy or contraception requirement is concluded from the definition

#### Scenario: Stable medication if used
- **WHEN** a criterion requires concomitant medication to be stable for 4 weeks
- **THEN** medication use is not required

### Requirement: Strict conclusions are entailed, never assumed
The system SHALL return ENTAILED only when no feasible assignment satisfies the eligibility formula with the
query negated, SHALL return INCONSISTENT for a contradiction, and SHALL return UNDETERMINED on a resource bound.

#### Scenario: A contradiction
- **WHEN** a trial's constraints contradict each other
- **THEN** the result is INCONSISTENT and nothing is entailed from it

### Requirement: Consumers read proof-bearing projections
The system SHALL give consumers only declared projections with their proofs and SHALL block a projection a
consumer cannot represent.

#### Scenario: A key that cannot hold a qualifier
- **WHEN** the profile asks for an element key of a CD4-qualified HIV exclusion
- **THEN** it receives a blocked projection naming the qualifier, never the key exclusion:HIV:positive
