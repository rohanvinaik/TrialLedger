# Spec Delta

## MODIFIED Requirements

### Requirement: Designs follow explicit premises
The complete workflow SHALL accept intervention, indication, population, phase, question and constraints as
a typed brief, derive consequences and produce a protocol with open choices. It SHALL distinguish partial
reasoning from a completed design.

#### Scenario: A population is restricted
- **WHEN** the brief admits a subset of a declared demographic domain
- **THEN** other domain values are excluded by that premise, whose source remains recorded

### Requirement: Correct partial logic remains usable
The system SHALL expose typed symbolic operations independently of unfinished source compilation or
protocol orchestration, with their input contracts, domains and limitations.

#### Scenario: Source compilation is unavailable
- **WHEN** valid scoped assertions are supplied
- **THEN** entailment is usable without claiming automatic text interpretation or complete synthesis

#### Scenario: A clinician uses a supported analysis for their own work
- **WHEN** the person chooses an available reasoning or comparison question independently of a complete protocol
- **THEN** the assistant explains the operation and limits, helps confirm material premises, runs it and presents its basis, assumptions, unresolved items and reusable structured result beside the separate source record

#### Scenario: The assistant discovers an operation for one question
- **WHEN** discovery is requested
- **THEN** an overview and operation-specific formats, vocabulary, result guides and runnable examples are available, with the complete guide and worked session explicitly accessible

#### Scenario: The person revises an accepted premise
- **WHEN** a material premise changes
- **THEN** the operation recomputes from the revised input without changing the source record or treating confirmation as source truth

### Requirement: Assertions preserve logical structure
The system SHALL preserve subject, predicate, value, force, alternatives, qualifiers, condition, cohort,
branch, time and provenance. Recognized words SHALL be candidates only; unresolved binding SHALL block the
conclusion rather than be completed by a token list.

#### Scenario: A requirement is disjunctive
- **WHEN** an assertion requires A or B
- **THEN** neither A alone nor B alone is entailed

#### Scenario: An exclusion is qualified
- **WHEN** an assertion excludes A together with Q
- **THEN** it does not establish an unqualified exclusion of A

#### Scenario: An obligation is conditional
- **WHEN** stability is required if medication is used
- **THEN** medication use is not thereby required

### Requirement: Entailment uses satisfiable supported premises
The system SHALL entail only when accepted scoped premises are satisfiable and exclude every
counterexample. Inconsistency, unresolved scope, unsupported queries and resource exhaustion SHALL have
distinct named outcomes.

#### Scenario: Branches share a consequence
- **WHEN** premises are (A and B) or (A and C)
- **THEN** A is entailed while B and C individually remain undetermined

#### Scenario: Premises contradict
- **WHEN** accepted premises admit no feasible assignment
- **THEN** the result is inconsistent, not universal entailment

### Requirement: Execution cannot promote epistemic standing
The system SHALL distinguish facts and strict deductions, interpolated defaults, proposals, user choices
and unresolved values. Conclusions SHALL retain their support's weakest standing. Approval or determinism
SHALL NOT make defaults strict; proposals SHALL NOT become premises.

#### Scenario: An interpolated premise supports a conclusion
- **WHEN** a strict rule derives from it
- **THEN** the consequence remains interpolated

### Requirement: Evidence constrains rather than votes
The system SHALL retain source identities and dependencies, eliminate alternatives by warranted
constraints and surface dissent. Encodings of one source SHALL NOT count as independent support.

#### Scenario: Sources disagree
- **WHEN** supported sources imply incompatible interpretations
- **THEN** disagreement remains visible without choosing a winner by count

### Requirement: Clinical relations are scoped and sourced
Relations SHALL apply only within declared indications, populations, interventions and versions. Disease
extent, treatment history and tested-treatment role SHALL remain separate; a registered setting SHALL NOT
establish today's standard of care.

#### Scenario: Applicability is unresolved
- **WHEN** a specialised relation has no established applicable scope
- **THEN** it does not silently narrow the trial's domain

### Requirement: Corpus quantities remain distinct
Logical state, statement frequency, association, rarity and question-specific significance SHALL remain
separate, with declared populations, denominators and unresolved membership. Silence SHALL NOT establish
absence.

#### Scenario: Eligibility may be abbreviated
- **WHEN** S of N records state an element and U remain unresolved
- **THEN** statement rate S/N is separate from full-criteria interval [S/N, (S+U)/N]

### Requirement: Geometry cannot invent facts
The system SHALL represent feasible alternatives, occupied and unresolved regions, conditional expectations
and verified deviations. It SHALL preserve unexplained structured deviation and SHALL NOT equate rarity
with relevance or empty space with unmet patient need.

#### Scenario: A region has no known occupant
- **WHEN** unresolved trials could occupy it
- **THEN** it remains unknown rather than empty

#### Scenario: A valid deviation is unexplained
- **WHEN** its evidence and scope hold against a declared expectation
- **THEN** it remains information rather than discarded noise

### Requirement: Comparisons declare their representation
Results SHALL be compared only with explicit population, endpoint, unit, measure and time compatibility.
Near misses SHALL differ on one declared verified coordinate and name unknowns and interpolation. Neither
SHALL imply causality without another warrant.

#### Scenario: Endpoint scope differs
- **WHEN** measurements differ in population or outcome definition
- **THEN** they are not silently pooled into a benchmark

### Requirement: Additional evidence uses bounded adapters
The designed workflow SHALL obtain terminology, units, labels and publication evidence under named
versions, resolve study and entity bindings and retain exact source locations. Conflicts SHALL remain beside
the registry without overwriting it.

#### Scenario: Publication binding is unresolved
- **WHEN** its arm, cohort or analysis cannot be bound
- **THEN** the paper remains a candidate and supplies no attributed result

### Requirement: Ranking cannot change admissibility
The complete workflow SHALL filter by warranted constraints before ranking alternatives. Recommendations
SHALL carry sources, counts or rules. Scores SHALL NOT promote proposals to facts or admit infeasible
designs.

#### Scenario: Common practice is suggested
- **WHEN** comparable trials frequently use a criterion
- **THEN** it is a sourced observation or proposal, not a logical requirement

### Requirement: User choices close the remaining space
The complete workflow SHALL present consequential decisions in clinical terms with suggestions, warrants
and downstream effects. Accepted choices SHALL remain attributed to the person and trigger recomputation.

#### Scenario: A comparator is chosen
- **WHEN** the person settles a genuine remaining choice
- **THEN** the choice is recorded and dependants recomputed without making it a registry fact

### Requirement: Protocol outputs retain derivations
The complete workflow SHALL emit the brief, eligibility, interventions, endpoints, schedule, sample-size
inputs, safety plan and unresolved decisions in structured and readable form. Each element SHALL identify
whether it was deduced, interpolated, proposed or chosen, with its basis.

#### Scenario: An efficacy target is proposed
- **WHEN** observations inform a target under a named rule
- **THEN** observed results, a source protocol's criterion and the new planning target remain separate

### Requirement: Validation follows the claim made
Recognition, scoped representation, entailment and clinical projection SHALL be tested separately with
positive/negative cases and actual consumers. Development trials, test counts and mutation certificates
SHALL NOT replace a warrant of meaning.

#### Scenario: Scope is wrong despite old tests
- **WHEN** a counterexample shows an incorrect referent or logical structure
- **THEN** the conclusion is refused or repaired structurally rather than legitimised by old tests

## ADDED Requirements

### Requirement: Answers are reported by epistemic category
The discovery reply SHALL map every entailment decision and blocker, coordinate state and corpus status to
one of settled, something wrong, your call or not knowable from this evidence, or mark it as a translation
problem in the request. Undetermined results SHALL be explained by their named reasons, and the guide SHALL
remain tied to the outcomes the operations actually emit.

#### Scenario: The premises admit a value without requiring it
- **WHEN** a brief requires age 18 or older and the question is whether everyone is at least 65
- **THEN** the result is undetermined with the sole reason undecided_by_constraints, reported as allowed but not required

#### Scenario: A premise is an unconfirmed reading
- **WHEN** the only premise that speaks to a question is marked proposed
- **THEN** it is set aside with a named proposed_refused reason and the person is asked to confirm the reading

#### Scenario: The criteria contradict each other
- **WHEN** accepted premises admit no feasible assignment
- **THEN** every question returns inconsistent with the contradicting premises, reported as something wrong

### Requirement: Notable is computed and significance is reserved
User-facing "notable" SHALL denote declared-cell rarity with support and abstention and/or a verified
unexplained deviation from a declared, confirmed expectation, naming which part was computed. "Significance"
SHALL denote only derivational significance over a declared alternative space, which SHALL abstain when no
alternative space is declared.

#### Scenario: Only rarity is callable
- **WHEN** an assistant can reach the corpus operation but not the deviation-status building block
- **THEN** it reports the rarity as computed and does not present a hand-applied deviation status as computed

#### Scenario: No alternative space is declared
- **WHEN** significance is requested for a derivation whose admissible alternatives are not declared
- **THEN** no significance value is emitted and rarity is not substituted for it
