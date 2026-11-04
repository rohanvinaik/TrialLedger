# Spec Delta

## ADDED Requirements

### Requirement: Managed protocol objects preserve their role
Version-2 sessions SHALL represent measurement definitions, endpoints, estimands, assessments, collection plans, efficacy rules and safety policies with explicit scope, origin, support and versioned references. Registered plans, observations and new design choices SHALL remain distinct. Missing bindings SHALL remain named gaps.

#### Scenario: An outcome horizon is available
- **WHEN** a source reports adverse events up to 96 weeks and says DLTs use protocol-defined criteria
- **THEN** neither a visit schedule nor the missing DLT definition is manufactured from those statements

#### Scenario: A stage has a different entry population
- **WHEN** randomized-withdrawal entry requires response but initial entry does not
- **THEN** its condition applies only to its declared stage and unrelated initial-entry checks retain their independently established answers

### Requirement: Protocol wiring preserves the warrant of every bridge
Every protocol-to-check projection SHALL expose its input identities, explicit adopted relation, applicability and output reference. Source location alone SHALL NOT establish clinical meaning. Proposed or unresolved bindings SHALL NOT narrow the accepted design floor, while their conditional calculations remain inspectable.

#### Scenario: The operator links an endpoint to a collection requirement
- **WHEN** the variable, population, time anchor and adopted dependency agree
- **THEN** the collection check consumes those bindings and retains their weakest support and exact references

#### Scenario: Only the source address matches
- **WHEN** two measurements share a source passage but their population or definition alignment is unsettled
- **THEN** no automatic equivalence or availability conclusion is admitted

### Requirement: Assessment feasibility differs from full window coverage
The system SHALL distinguish existence of a supported assessment time, support for the nominal target and support for every permitted time. It SHALL preserve the original permitted window and return exact unsupported intervals where decidable. Unknown availability SHALL differ from explicitly absent availability.

#### Scenario: Collection ends inside a permitted window
- **WHEN** assessment is permitted on days 77 through 91, targets day 84 and collection is available through day 80
- **THEN** feasibility is satisfied on days 77 through 80, nominal support fails and full coverage fails with unsupported interval (80,91], without rewriting the permitted window

#### Scenario: The boundary is open
- **WHEN** collection excludes day 91 but the permitted window includes it
- **THEN** full coverage fails even if every earlier permitted day is supported

#### Scenario: Availability is unknown
- **WHEN** no applicable collection availability has been declared
- **THEN** support remains unresolved rather than reported as impossible or complete

### Requirement: Endpoint checks preserve dependencies and collection modes
Endpoint checks SHALL use adopted definitions and prerequisites, preserving alternatives, baseline references, population, units, time and observed/imputed/derived modes. An estimand strategy name alone SHALL NOT create collection requirements. Planned collection SHALL NOT establish that data were observed.

#### Scenario: Change from baseline lacks a baseline
- **WHEN** an adopted change-score rule requires baseline and follow-up observations but baseline availability is unknown
- **THEN** the missing prerequisite is named without inventing a baseline or treating imputation as observation

#### Scenario: Collection stops after discontinuation
- **WHEN** an accepted requirement retains post-discontinuation assessments and the plan stops them
- **THEN** the mismatch appears in the decision, revision and export with that requirement's support

### Requirement: General protocol alternatives retain independent checks
Version-2 protocol alternatives SHALL apply explicit attributed design edits and freshly execute declared checks. Compatibility SHALL mean compatibility under those checks only. Per-check outcomes, conditional results, unknowns and limits SHALL remain visible; a successful calculation SHALL NOT certify a complete or clinically appropriate protocol.

#### Scenario: One option has an unresolved required check
- **WHEN** its schedule check passes but its required endpoint-definition check cannot resolve a binding
- **THEN** the option remains undetermined with both results preserved

#### Scenario: The selected option conflicts
- **WHEN** a caller selects an option that violates an accepted fixed requirement
- **THEN** selection remains attributed and the conflict remains a blocker

#### Scenario: An unchosen design is examined
- **WHEN** the person asks what would follow if a new assessment plan were chosen
- **THEN** its explicitly declared local assumptions support a conditional comparison without claiming confirmation or promoting proposed external evidence into the fixed floor

#### Scenario: An alternative omits a required check
- **WHEN** its declared check list excludes a required check for the decision target
- **THEN** it is refused as an invalid comparison rather than reported as compatible

### Requirement: Safety policies are checked over declared reachable states
Bounded finite-state safety checks SHALL preserve declared state, guard, action and action scope. They SHALL report reachable coverage gaps, competing transitions and forbidden actions with witnesses. Exhaustiveness SHALL refer only to represented variables and assumptions; absent safety variables SHALL NOT be treated as safe.

#### Scenario: A fully covered rule chooses an unsafe dose
- **WHEN** a reachable assignment triggers a selected dose and an explicitly adopted prohibition forbids that selection
- **THEN** the prohibition fails with a witness even though action coverage is complete

#### Scenario: Withholding treatment differs from withholding follow-up
- **WHEN** an action holds participant dosing without an adopted rule ending assessment collection
- **THEN** the system does not infer that follow-up stops

#### Scenario: A policy has a reachable cycle
- **WHEN** no termination obligation or fairness assumption is supplied
- **THEN** reachability and any cycle are reported without asserting observed nontermination or a termination guarantee

### Requirement: Efficacy calculations declare their statistical model
The supported one-stage, one-sided greater-than binomial design SHALL return exact null rejection probability and alternative power from explicit fixed sample size, critical count and probabilities. Results SHALL retain model assumptions and binding standing. Other statistical methods SHALL remain represented but uncomputed, without substituted methods or invented planning inputs.

#### Scenario: A binary design is fully declared
- **WHEN** n=2, rejection requires at least 2 successes, p0=1/2 and p1=3/4
- **THEN** the exact null rejection probability is 1/4 and power is 9/16, conditional on the supplied model

#### Scenario: A survival design is supplied
- **WHEN** the chosen method concerns time-to-event or multiplicity outside the implemented family
- **THEN** its declarations and missing calculation remain visible rather than receiving a binomial approximation

### Requirement: Cross-operation definitions are explicitly checked
Declared relations between definitions used by different protocol checks SHALL be evaluated with both operand bindings, scope and support. Distinct thresholds SHALL remain distinct unless an adopted relation connects them. Refutation SHALL identify the violated relation rather than asserting that every numerical difference is erroneous.

#### Scenario: Retreatment and relapse use different thresholds
- **WHEN** fully bound definitions trigger assessment at MADRS 20 and require MADRS 22 at two visits for relapse
- **THEN** the difference is retained; an explicitly declared equivalence fails, while a declared earlier-screening relationship is checked on its own terms

### Requirement: Protocol preparation is usable through public interfaces
CLI and MCP SHALL expose task-sized discovery and strict typed preparation for protocol objects, checks and alternatives. Public retained-artifact execution, reading, revision and export SHALL work without private builders or copying expanded requests into conversation. Defaults SHALL be enumerated and SHALL NOT supply missing clinical choices.

#### Scenario: A cold operator prepares a design
- **WHEN** the assistant uses only public discovery and typed input
- **THEN** preparation exposes the expansion, adopted projections and unresolved bindings and execution preserves the same meaning as the expanded request

### Requirement: Protocol delivery conserves clinical context
Readable output and a separate review workbook SHALL include a protocol synopsis and schedule of assessments. They SHALL preserve population, arm, event anchor, nominal target, permitted window, collection plan, conditionality, units and warrants. Requested but unresolved sections SHALL remain visible. Caller wording SHALL be distinguishable from computed conclusions.

#### Scenario: A colleague reviews the schedule
- **WHEN** full window coverage fails while a feasible assessment exists
- **THEN** both the original window and uncovered interval appear with the relevant requirement, source or choice and exact result reference

#### Scenario: A section is requested but uncomputed
- **WHEN** safety or sample-size content lacks an implemented method or required evidence
- **THEN** it remains an explicit open item and no complete-protocol label is emitted

### Requirement: Protocol revisions distinguish different consequences
Version-2 revisions SHALL recompute both snapshots and distinguish verdict, residual requirement, support, scope, model assumption and wording changes. They SHALL preserve prior canonical artifacts and source snapshots. A changed input digest or unrelated requirement SHALL NOT alone be called a changed clinical verdict.

#### Scenario: ECOG widens while genotype consequences stay constant
- **WHEN** only a residual performance-status requirement changes beside an unchanged genotype verdict
- **THEN** the revision reports the residual change without claiming genotype eligibility changed

### Requirement: Version one remains independently reproducible
Version-1 requests, results and stored artifacts SHALL remain usable under their documented contract. Version-2 functionality SHALL require an explicit version. Mixed-version revision SHALL be refused with a named explanation unless an explicit separately recorded conversion is implemented.

#### Scenario: An old eligibility session is replayed
- **WHEN** the unchanged version-1 request is run
- **THEN** its established canonical behavior remains unchanged and no protocol objects are silently added

### Requirement: Protocol limits preserve partial knowledge
Protocol execution SHALL account for represented intervals, reachable states, statistical arithmetic, alternatives and fresh revision work separately from registry acquisition and reply size. Limit outcomes SHALL name unexecuted claims and preserve completed independent results. Empty or bounded witness displays SHALL NOT imply that no counterexample exists.

#### Scenario: A witness display is capped
- **WHEN** exhaustive finite checking finds more violating cases than the display limit
- **THEN** the failure and complete search coverage remain visible with a capped witness count

#### Scenario: A required check is not executed
- **WHEN** a genuine work bound prevents its execution
- **THEN** the option cannot be reported as compatible under all declared checks

### Requirement: Protocol validation follows real consumers
Acceptance SHALL include independently authored positive and MUST-NOT cases, independent small-domain mathematical oracles, current behavioral pin records and real CLI/MCP revision/export paths. Model-operated clinical walkthroughs SHALL use varied phases, disease areas and design structures after substantial integration changes. Simulated choices and proof limitations SHALL be stated accurately.

#### Scenario: A component is correct but disconnected
- **WHEN** its unit tests pass but its finding does not reach a declared decision or exported schedule
- **THEN** workflow acceptance remains incomplete

#### Scenario: A proof tool stops without completing
- **WHEN** a current target has no admissible completed proof record
- **THEN** ordinary tests remain reportable but neither a proof success nor an inherited waiver is claimed
