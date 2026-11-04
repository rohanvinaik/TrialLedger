## ADDED Requirements

### Requirement: Partial profiles expose warranted remaining requirements
For a feasible partial profile, the system SHALL expose bounded solver-proved requirements not established
by that profile, preserving disjunctions, scope and weakest support. Candidate discovery SHALL distinguish
its own coverage from complete screening and SHALL NOT promote proposed premises.

#### Scenario: BMI selects a comorbidity route
- **WHEN** accepted criteria require a listed-condition disjunction below BMI 30 and the profile gives BMI 28
- **THEN** the disjunction is reported as required under that profile with its deciding warrant
- **AND** no individual condition is thereby required

#### Scenario: Prior treatment activates a washout
- **WHEN** accepted criteria require 180 days after prior treatment and timing is unspecified
- **THEN** the requirement is reported with its unit and anchor without claiming the person failed it

#### Scenario: Equivalent typed rules are used
- **WHEN** the tested implication is represented conditionally or by an equivalent disjunction
- **THEN** the same warranted residual requirement remains available

#### Scenario: The profile cannot fit
- **WHEN** the profile is refuted, inconsistent or not resolved within the supported bound
- **THEN** no vacuous implication is presented as useful screening information

### Requirement: Decision context is anchored and role separated
Decisions SHALL accept optional exact source-anchored context and retain its role and attribution.
Source wording, caller readings, caller-described gaps, adopted premises and clinical choices SHALL remain
distinct. Adding context alone SHALL NOT alter computed eligibility or establish semantic absence.

#### Scenario: A comparator informs a choice
- **WHEN** a decision cites an exact retained eligibility passage
- **THEN** its source, exact wording and context role appear beside the choice and deciding premises

#### Scenario: A caller describes registry silence
- **WHEN** a gap note is attached to a source anchor
- **THEN** it remains a caller-described evidence question rather than computed absence

#### Scenario: The anchor is stale
- **WHEN** expected value, digest or span differs from the retained source
- **THEN** the request is refused with a named translation error

### Requirement: Clinical views distinguish wording from computation
Clinical views SHALL show represented profiles, computed outcomes, deciding premise content, evidence,
origins and open items. Caller questions and labels SHALL be identified as caller wording. Typed logical
structure SHALL survive readable rendering; unsupported display shapes SHALL remain explicitly unresolved.

#### Scenario: A label claims an unencoded restriction
- **WHEN** a caller label mentions a restriction absent from its typed query
- **THEN** the label is not presented as a certified computed assertion
- **AND** the represented query remains inspectable beside the result

#### Scenario: A negated profile is feasible
- **WHEN** both a profile and its negation fit represented restrictions
- **THEN** the view does not claim that exclusion is already required

### Requirement: Revision distinguishes questions verdicts warrants and attribution
Revision SHALL retain independent question, answer, deciding-support and origin changes. A changed question
SHALL NOT be described as a verdict changing for an unchanged question. Deciding support SHALL include the
actual versioned premises rather than IDs alone; the complete audit difference SHALL remain available.

#### Scenario: A profile is sharpened
- **WHEN** a typed profile changes while its compatibility verdict stays the same
- **THEN** the view reports a changed question and unchanged verdict

#### Scenario: The deciding threshold changes
- **WHEN** a deciding rule changes from 90 to 180 days and a 60-day profile stays refuted
- **THEN** the changed support remains visible independently of the unchanged verdict

### Requirement: Conversational reasoning views obey explicit byte bounds
Compact replies SHALL obey a declared supported byte budget, retain canonical artifact identity, and
provide counts and exact continuation for omitted detail. A public decision view SHALL expose coherent
clinical content without requiring repeated generic directory traversal. Full canonical results SHALL remain
unchanged and retrievable.

#### Scenario: A many-check revision is compacted
- **WHEN** full before-and-after projections exceed the reply budget
- **THEN** concise changes and explicit continuation are returned rather than the full projections

#### Scenario: A clinical decision is requested
- **WHEN** its readable view fits the budget
- **THEN** profile, result, deciding premises, context and open items are available together

### Requirement: Discovery exposes actual specialized vocabulary
Discovery SHALL expose the accepted estimand strategy vocabulary from its validation owner. Structured
query displays SHALL preserve canonical warrants, and export help SHALL state the actual publication folder.

#### Scenario: The operator prepares an estimand
- **WHEN** the operator requests the signal contract
- **THEN** the accepted strategy values are discoverable without reading source code
