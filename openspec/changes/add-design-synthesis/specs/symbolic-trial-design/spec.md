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
branch, time and provenance. Recognized words SHALL be candidates only; unresolved binding SHALL block an
unconditional conclusion rather than be completed by a token list. Isolated hypothetical consequences SHALL
remain available with the interpretation and unresolved binding explicitly named.

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
SHALL NOT make defaults strict; proposals SHALL NOT become accepted premises. Explicit hypothetical frames
MAY assume proposals locally without admitting them to the fixed floor or ordinary entailment.

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

### Requirement: Baseline witnesses bound declared eligibility designs
The system SHALL expose typed `design_bounds` reasoning over declared candidate designs, using scoped
entailment. Observations SHALL retain population, denominator, count, proposition, context and sources.
Explicit eligibility bridges SHALL retain standing, resolution, provenance and an exception bound.

#### Scenario: Observed PS 2 constrains a cutoff family
- **WHEN** an aligned participant count at WHO PS 2 exceeds a confirmed bridge's exception allowance
- **THEN** candidate WHO PS upper cutoffs below 2 are ruled out with their proofs, while cutoffs 2 and above and no cutoff can remain
- **AND** the exact cutoff remains unresolved and WHO PS is not silently mapped to ECOG

### Requirement: Witness bounds preserve uncertainty and independence
Witness-based elimination SHALL require accepted, resolved evidence with a guaranteed positive count
beyond the exception allowance, using the appropriate accepted/rejected feasibility check. Zero, silence,
proposed or unresolved bindings SHALL NOT establish exclusion. Counts
SHALL NOT sum across observations. Unknown computation SHALL retain a candidate as unresolved. Derived bounds
SHALL remain separate from source text and source-statement frequencies.

#### Scenario: Overlapping baseline observations
- **WHEN** two observations might describe the same participants or an arm and its aggregate
- **THEN** each is checked independently without adding their counts or inventing joint participant profiles

#### Scenario: The bridge or candidate changes
- **WHEN** the exception allowance reaches the positive count or binding becomes proposed/unresolved
- **THEN** the witness no longer eliminates the candidate and downstream consequences are recomputed

### Requirement: Surviving designs feed conditional consequences
The system SHALL compute a common query consequence across all remaining declared candidates, retaining
the weakest support used in eliminations. The candidate family SHALL NOT be claimed exhaustive of actual
protocols. Empty survival SHALL be a named conflict rather than entailment by explosion.

#### Scenario: No declared design survives
- **WHEN** every candidate is ruled out or internally inconsistent
- **THEN** the result is a conflict within that family, not entailment by explosion

#### Scenario: The assistant operates the continuing design session
- **WHEN** baseline witnesses inform a design choice through CLI or MCP reason
- **THEN** focused discovery supplies runnable inputs, the answer names observation and bridge origins, and the decision list retains the conditional bound and remaining choices beside unchanged evidence

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

### Requirement: Typed partial evidence constrains declared designs
The separate `signals` operation SHALL expose overlap, disjoint partitions, exact ordered summaries,
population subsets, temporal intervals, regimen composition, directional relations and adopted measurement
dependencies. Inputs SHALL retain explicit scope, source/version references, support standing and binding
resolution. Operators SHALL NOT recognize clinical meaning from words or fetch additional evidence.

#### Scenario: Aligned marginals guarantee a joint witness
- **WHEN** two participant sets in one confirmed universe have counts 126 and 1140 out of 1217
- **THEN** their intersection is bounded by [49,126], without independence or an exact joint count
- **AND** missing alignment refuses witness use even when the denominators agree

#### Scenario: Complement or population difference is represented
- **WHEN** disjoint parts or an explicit subset relation bind a finite universe
- **THEN** counts obey the total equation and typed complement/difference expressions preserve their predicates
- **AND** missing counts are unknown bounds rather than observed zeros

#### Scenario: An exact median is used
- **WHEN** exactness and the midpoint median convention are explicitly supplied for the assessed population
- **THEN** inclusive side-count bounds are computed, with the even-median equality hole retained in joint claim checking
- **AND** rounded values, missing conventions or a zero assessed population provide no summary witness

### Requirement: Structural signals retain their declared semantics
Temporal constraints SHALL use exact dense-time intervals and strictness without invented time steps.
Regimen composition SHALL preserve planned/observed stage, assigned arms, products and ingredient identities.
Relation closure SHALL be directional, scoped and versioned; only declared subtype/instance inheritance
SHALL compose. Associated and ingredient relations SHALL remain direct. Missing membership SHALL NOT
become a negative fact.

#### Scenario: Joint temporal claims conflict
- **WHEN** individually feasible candidate claims form a strict zero-length cycle together
- **THEN** their joint check conflicts and can eliminate that supported candidate

#### Scenario: A product is a combination
- **WHEN** a resolved assigned arm includes a bound product with explicit ingredients
- **THEN** ingredient membership follows that composition without treating ingredient and product as identical
- **AND** aggregate or observational groups do not silently become assigned arms

### Requirement: Negative witnesses and prerequisites retain alternatives
An attributed rejected profile P SHALL require a feasible P AND NOT E completion under candidate E,
without establishing universal exclusion of P. Both witness directions SHALL refuse intrinsically impossible
profiles. Measurement dependencies SHALL apply only to explicitly adopted rules, retain OR-of-AND
prerequisites and guards, and distinguish observed, imputed and derived inputs.

#### Scenario: Rejection has an unspecified explanation
- **WHEN** P is rejected and E requires P together with another attribute
- **THEN** E can remain feasible because the other attribute may explain rejection
- **AND** a candidate that requires only P cannot accommodate that rejected witness

#### Scenario: An adopted calculation lacks an input
- **WHEN** its required observed input is missing, explicitly unavailable or supplied only as imputed
- **THEN** those states remain distinct, and a calculation never manufactures an observed measurement

### Requirement: Partial evidence reaches public design consequences
CLI and MCP SHALL expose focused discovery and runnable examples for every signal kind. Derived observations
SHALL select an emitted witness using explicit predicate bindings and the same population/denominator.
Only its guaranteed lower count SHALL be compared with the exception allowance. Candidate claims per signal
SHALL be conjoined jointly, and every elimination-dependent consequence SHALL retain weakest support.

#### Scenario: A derived bound changes
- **WHEN** a source binding becomes unresolved or the exception allowance reaches its lower bound
- **THEN** dependent candidate elimination and the common consequence are recomputed
- **AND** intervals remain intervals, proposals do not constrain, and source records and statement counts stay unchanged

#### Scenario: Source constraints conflict
- **WHEN** accepted input evidence is internally inconsistent
- **THEN** a named source conflict blocks the common consequence without entailment by explosion

### Requirement: Competing interpretations preserve conditional usefulness
The separate `interpretations` operation SHALL retain each reading's identity, origin, clinical label,
premises and alternatives. Fixed layer-one evidence and direct rules SHALL bound the represented admissible
space. Exact consequences conditional on a reading SHALL remain distinct from confirmation of that reading.

#### Scenario: Two plausible readings disagree
- **WHEN** separate frames imply different parameter values without violating the fixed floor
- **THEN** both readings and their conditional consequences remain available
- **AND** neither becomes a source fact or a requirement of the new trial by surviving

#### Scenario: A proposed reading is explored
- **WHEN** an unconfirmed scoped assertion is explicitly assumed inside an interpretation
- **THEN** its exact hypothetical consequences are computed with that assumption in the warrant
- **AND** ordinary entailment still refuses that proposed assertion as an accepted premise

### Requirement: Compatibility and refutation carry separate warrants
The operation SHALL distinguish compatible, fixed-floor-refuted, internally incoherent, unresolved and
fixed-floor-conflict states. Warrants SHALL identify rules, fixed premises, hypothetical premises, standing
and blockers. Compatibility SHALL NOT certify intended meaning or clinical appropriateness.

#### Scenario: A frame contradicts fixed evidence
- **WHEN** the represented constraints admit no completion together but the fixed floor is satisfiable
- **THEN** the frame is refuted with its deciding fixed and hypothetical premises
- **AND** refutation depending on an interpolated floor remains conditional on that floor

#### Scenario: The floor contradicts itself
- **WHEN** the fixed premise set is inconsistent
- **THEN** closure is blocked for every frame, without universal entailment

#### Scenario: A planned window and an actual scan differ
- **WHEN** a scheduled visit interpretation has a fixed interval and a separately represented actual unscheduled scan occurs outside it
- **THEN** the different events do not conflict without a premise equating them

### Requirement: Source bindings have typed and effective consumers
Population and definition bindings SHALL retain source versions/locations and explicit study, population,
arm, time and edition scope. Each application SHALL identify its target signal and check the declared
relation and scope. Unknown bindings SHALL preserve conditional calculations while preventing unsupported
admission, pooling or refutation.

#### Scenario: An analysis subset is bound
- **WHEN** a subset binding matches the target population operator's universe, parent and subset
- **THEN** the binding check feeds the interpretation's admissibility and the computed difference retains that support
- **AND** equal denominators or group titles alone never establish the binding

#### Scenario: An endpoint definition has another edition
- **WHEN** the binding's adopted rule edition differs from its application
- **THEN** that application is unresolved and its conditional calculations remain inspectable
- **AND** imputed and observed prerequisites remain distinct

### Requirement: Surviving interpretations do not manufacture certainty
The operation SHALL expose fixed-floor answers independently and common consequences across declared
surviving frames, without assuming family exhaustiveness. Unresolved frames SHALL remain possible and block
unsupported common closure. Selecting a frame SHALL remain a user choice and recompute the full snapshot.

#### Scenario: Only one declared frame survives
- **WHEN** a single candidate remains
- **THEN** its consequences remain conditional on the declared family and assumptions
- **AND** the actual protocol is not claimed uniquely identified

#### Scenario: A selected frame is refuted
- **WHEN** the requested selection conflicts with fixed evidence
- **THEN** it is not admitted and the contradictory warrant is retained

#### Scenario: A binding is revised
- **WHEN** population alignment, definition edition or hypothesis support changes
- **THEN** all dependent frame decisions and common consequences are recomputed from the revised request
- **AND** retained source records and the original request remain unchanged
