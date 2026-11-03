# Symbolic trial design: integrated session delta

## ADDED Requirements

### Requirement: Existing operations distinguish logical and operational state
Every existing reasoning operation SHALL provide additive per-finding metadata preserving effective logical results and separate evidence, translation and computation causes. Mixed results SHALL remain separate. Completed request handling SHALL NOT imply completed reasoning; discovery and inspection SHALL NOT receive clinical verdicts.

#### Scenario: More computation settles unchanged premises
- **WHEN** an age requirement returns a resource limit and the same request settles with a larger limit
- **THEN** the first result is not-computed and the second retains its deciding premise without claiming that new evidence arrived

#### Scenario: Several causes remain open
- **WHEN** an unsettled binding and an unfinished computation both affect a query
- **THEN** both causes remain visible with their affected results and distinct remedies

#### Scenario: A finding is open before the session supplies question context
- **WHEN** existing version-1 metadata reports open with standing, completion and causes but no normalized origin or coverage
- **THEN** no design freedom is implied; the planned session refines that state from declared questions, dependencies, represented coverage and actual feasibility results

#### Scenario: Conditional findings have different standing
- **WHEN** two findings are conditional but one has interpolated support and the other proposed support
- **THEN** the answer guide distinguishes an overridable working assumption from an unconfirmed reading and preserves ordinary entailment's refusal of the proposed premise

### Requirement: Session decisions are relative to a declared target and representation
The system SHALL compute decision-list entries from named questions and returned results, preserving target, scope, standing and represented coverage. It SHALL distinguish clinical choices from evidence or translation tasks. A free design alternative SHALL require completed feasibility checks of both alternatives within the represented constraints.

#### Scenario: A historical cutoff is unknown
- **WHEN** the comparator's actual cutoff is not determined
- **THEN** the missing historical fact remains an evidence question rather than an arbitrary clinical choice, while the new trial's cutoff can be a separate design decision

#### Scenario: The representation is incomplete
- **WHEN** an encoded age restriction permits both older and younger adults but other eligibility content is unresolved
- **THEN** the answer names the age restriction and does not certify whole-patient eligibility or complete protocol admissibility

### Requirement: Exception bounds retain documentary meaning and application scope
The system SHALL represent reported reason counts separately from their eligibility-exception interpretation, with study, snapshot, population, arm, period and assessment alignment. An admitted lower bound SHALL NOT supply a nontrivial upper bound. Absent support SHALL NOT imply zero exceptions.

#### Scenario: A flow category reports one participant
- **WHEN** one withdrawal is reported under an eligibility reason and its application to enrollment eligibility is unresolved
- **THEN** the count remains a source fact and the exception interpretation remains conditional with the missing binding named

#### Scenario: Registry wording has no codebook-defined eligibility meaning
- **WHEN** IPASS's eligibility-worded withdrawal category is used to prepare an exception floor under the current vendored registry schema
- **THEN** its entry-eligibility interpretation remains a supplied reading; any zero-cap conflict depends on its accepted attribution and scope rather than the registry alone

#### Scenario: A cap conflicts with admitted evidence
- **WHEN** an existing design-bounds bridge references supplied applicable admitted exception evidence with floor one but caps that population at zero
- **THEN** CLI and MCP report the bridge conflict and withhold dependent elimination without requiring a session or altering the source

#### Scenario: The reported exception has an unknown profile
- **WHEN** a global exception is reported without WHO PS or smoking attributes
- **THEN** it does not establish an exception within the PS-2/never-smoker subgroup

#### Scenario: An entry-ineligibility floor is attached to a rejection budget
- **WHEN** a rejected witness references a floor for ineligible enrolled participants
- **THEN** the positive-budget calculation remains inspectable but its floor does not transfer; a named predicate mismatch blocks dependent elimination and common consequence

#### Scenario: Attribution uncertainty cannot affect an independently warranted cap
- **WHEN** a one-participant failure is treatment-only, has open entry/treatment targets, or has only a proposed entry reading, while the bridge independently supplies cap five
- **THEN** every represented selected floor fits the cap, so the check is consistent and independent eliminations survive; the possible-floor envelope does not become an upper bound on total exceptions

#### Scenario: A proposed bridge would conflict if adopted
- **WHEN** the bridge is proposed and its zero cap contradicts the conditional entry floor of one
- **THEN** the result retains the conditional interval conflict without admitting the bridge or a dependent elimination

#### Scenario: A failure has several possible targets
- **WHEN** a protocol-related failure remains attributable to entry eligibility, treatment, assessment or another protocol requirement
- **THEN** its count and possible targets remain available without an eligibility floor, and later narrowing retains its own evidence, scope and standing

#### Scenario: An entry violation is discovered during maintenance
- **WHEN** the recording period is maintenance but no accepted attribution excludes an entry requirement
- **THEN** entry eligibility remains possible; the recording period alone does not settle the failed target

#### Scenario: A target attribution becomes decisive or contradictory
- **WHEN** applicable accepted target evidence narrows the possible targets to entry eligibility alone, or instead yields an empty intersection
- **THEN** the first supplies the applicable eligibility floor and the second reports an attribution conflict; a proposed singleton supplies only a conditional floor

### Requirement: Negative evidence reaches each downstream decision
An attributed rejected participant profile SHALL constrain candidate eligibility by existence of an ineligible completion, never universal exclusion of the partial profile. Each supported elimination SHALL retain sign, scope, deciding support and standing through candidate decisions, common consequences where relevant, classified metadata and the decision/evidence-task handoff. Corpus silence SHALL NOT supply a negative participant witness.

#### Scenario: Both signs share a partial profile
- **WHEN** eligible and ineligible witnesses have the same represented partial profile under the applicable rule and warranted bridges
- **THEN** candidates unable to accommodate either sign are eliminated without identifying an unobserved distinguishing attribute or excluding everyone with that profile

#### Scenario: Negative constraints identify or empty a declared family
- **WHEN** supported eliminations leave one or no candidate designs
- **THEN** one remains a permissible within-family survivor without historical identification, while none reports conflict rather than a vacuous clinical consequence

### Requirement: Distinguishing observations remain evidence requests
The system SHALL compute bounded hypothetical participant-profile and sign requests against declared surviving candidates using the existing witness logic. It SHALL preserve represented domains, exact comparison boundaries, scope, attribution and exception conditions, affected candidates and deciding proofs. It SHALL distinguish incomplete enumeration from completed absence of a separator. Requests SHALL NOT become observed evidence or accepted premises automatically.

#### Scenario: An eligibility rejection distinguishes two candidate rules
- **WHEN** one candidate requires adulthood and ECOG at most 2, another additionally requires a marker, and the hypothetical profile is an adult marker-negative ECOG 2 participant rejected for eligibility
- **THEN** the evidence request states that this warranted negative witness would eliminate the first candidate but can fit the second, with its bridge and exception conditions explicit

#### Scenario: A partial profile still carries negative information
- **WHEN** a rejected adult ECOG 2 profile omits marker status, one candidate requires only adulthood and ECOG at most 2, and another additionally requires a marker
- **THEN** the first cannot explain rejection while the second can through an unspecified marker value; no actual marker value or universal exclusion is asserted

#### Scenario: A computation limit prevents complete separation analysis
- **WHEN** enumeration or a participant decision exceeds its declared work bound
- **THEN** the result retains candidate outcomes and named computation limits rather than claiming the candidates are indistinguishable under every possible observation

#### Scenario: Several profiles distinguish the same survivor pair
- **WHEN** profiles with different numbers of specified attributes separate a pair within the searched representation
- **THEN** the least-specified separating profiles are returned first with explicit witness signs, deterministic ties and evidence-location guidance, without a clinical-utility or evidence-availability probability claim

#### Scenario: More evidence requests exist than can be returned
- **WHEN** the per-pair, aggregate request count or output-byte cap is reached
- **THEN** the response marks output truncation separately from search completion and reports no uncomputed omitted count or false absence of separating evidence

### Requirement: Witness guarantees consume exception upper bounds
The system SHALL use an applicable justified or explicitly hypothetical exception upper bound to establish guaranteed eligible witnesses. Unknown upper bounds SHALL remain unresolved. Sensitivity assumptions SHALL retain their origin and SHALL NOT become claims about the historical trial.

#### Scenario: The guarantee changes at the exact boundary
- **WHEN** the joint-count lower bound is 49 and the exception upper bound changes from 48 to 49
- **THEN** the first setting guarantees at least one eligible witness under the bridge and the second does not, preserving the complete count interval and assumptions

#### Scenario: The total exception count has only a floor
- **WHEN** an aligned exception floor is known but no informative ceiling is supported
- **THEN** the system shows which hypothetical ceilings would establish the guarantee without selecting a ceiling as fact

### Requirement: Binding candidates are tested without being certified by compatibility
The system SHALL test declared population relations against applicable scope and count constraints before asking for judgment. Incompatible readings SHALL carry their conditional warrant; wrong or incomplete application scope SHALL remain an application problem. Compatible or sole-surviving candidates SHALL NOT be promoted to source identity.

#### Scenario: A subset exceeds its declared container
- **WHEN** a candidate identifies the 609-person gefitinib ITT group as a subset of its 590-person QoL group under the declared same-arm correspondence
- **THEN** the candidate is incompatible under that binding while both recorded counts remain unchanged

#### Scenario: Counts leave two correspondences possible
- **WHEN** two declared bindings satisfy all represented count constraints
- **THEN** both remain available and the result identifies the evidence or judgment needed to distinguish them

#### Scenario: An ordinary signal carries an unaccepted or mismatched population use
- **WHEN** a proposed binding or wrong arm/version applies to a signal used by a derived witness or candidate claim
- **THEN** the same precise application blockers reach every dependent consumer while the raw arithmetic remains visible; isolated hypothetical frames retain their separate assumption behavior

### Requirement: Overlapping evidence cannot manufacture additional people
The system SHALL retain the identity and dependence of count observations. Independent descriptions SHALL NOT be summed as disjoint populations without a partition warrant. Exception-floor combination SHALL respect possible overlap and incompatible scopes.

#### Scenario: Smoking categories and flow reasons may overlap
- **WHEN** two baseline non-light ex-smokers and one eligibility-related withdrawal are hypothetically bound to the same population
- **THEN** the system retains their possible overlap and does not infer three distinct exceptions or assign the withdrawal a smoking category

### Requirement: Session consumer admission follows referenced premises and origins
Automatic session projections SHALL derive feature standing from explicit premise dependencies and supported projection rules. They SHALL retain source-documentation origin separately from logical standing. Source-stated corpus counts SHALL exclude derived participation bounds, session choices and hypothetical readings, even if the caller labels them known.

#### Scenario: A known new-trial choice is offered as comparator evidence
- **WHEN** a new-trial ECOG choice is referenced as a comparator's documented restriction
- **THEN** the projection is refused with an origin mismatch rather than counted as a source statement

#### Scenario: A reasoning result is offered as its own independent support
- **WHEN** a prior design survivor is relabelled known and offered through the managed path as an independent source witness
- **THEN** origin-based admission refuses the promotion while the original computed result remains available with its dependencies; a dependency cycle is also refused

#### Scenario: One feature remains usable
- **WHEN** structured age is directly warranted but the PS reading is proposed
- **THEN** the age feature remains usable, the PS feature remains pending and the complete trial remains in the declared denominator

### Requirement: Session revisions replay the complete accepted snapshot
The system SHALL retain immutable revision identity, source identities, premise origins and full analysis dependencies. A revision SHALL recompute the complete requested analyses initially and return changed, withdrawn and independently retained answers. It SHALL NOT treat one returned proof as an exhaustive dependency label.

#### Scenario: A binding is withdrawn
- **WHEN** the common-population binding is withdrawn
- **THEN** its overlap-based eligibility consequence is withdrawn while independently warranted registered age remains settled

#### Scenario: A second support remains
- **WHEN** a conclusion has two independent derivations and a premise in only one is retracted
- **THEN** fresh recomputation retains the conclusion under the remaining support

#### Scenario: A previously absent constraint is added
- **WHEN** a new premise makes an open question constrained
- **THEN** the affected answer is recomputed even though the new premise was absent from the earlier proof

### Requirement: Sessions preserve complete existing reasoning results
The system SHALL expose the session through the shared public reasoning entry point, retain complete child request/result pairs and derive its decision list from those results. It SHALL keep separate operations usable, refuse recursive or excessive session work by name and leave reporting evidence unchanged.

#### Scenario: CLI and MCP receive the same snapshot
- **WHEN** the same valid session is run through either public entry point
- **THEN** the complete clinical dispositions, dependencies and child results agree

#### Scenario: A session is revised after a source update
- **WHEN** a retained source digest changes
- **THEN** stale source uses are named and dependent results are recomputed or withheld rather than reused as current

### Requirement: Substantial changes receive a model-operated clinical walkthrough
After a substantial coherent implementation or documentation-focused change, the assistant SHALL exercise a sensible clinical question on a recorded fresh sample from a different trial category, revise a material premise and retain findings. This model action SHALL remain outside CI; unavailable integrations and sampling limits SHALL remain explicit.

#### Scenario: A shared search contains different treatment settings
- **WHEN** a random sample includes first-line and post-EGFR-TKI studies from the same drug search
- **THEN** the walkthrough retains their distinct eligibility and treatment contexts rather than silently pooling them as comparable trials

#### Scenario: A difficult sample exposes a gap
- **WHEN** the walkthrough cannot carry a documented promise through an existing public consumer
- **THEN** it retains the sample and a concrete finding rather than selecting a replacement that makes the change appear complete
