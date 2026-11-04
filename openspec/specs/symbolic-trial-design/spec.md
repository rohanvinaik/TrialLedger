# Symbolic trial design

## Purpose

Layer two constructs a trial from a brief and warranted evidence. This is the complete intended behavior,
not a claim that the whole pipeline is built. Correct partial operations remain independently available;
the consolidated change distinguishes working logic from missing integration.

## Requirements

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

### Requirement: Advertised reasoning matches executable reasoning
Every callable operation and focused discovery view SHALL appear in emitted MCP schemas and current
guidance. Runnable examples SHALL validate against the emitted schema and execute through CLI and MCP.
Unsupported operations SHALL remain unsupported.

#### Scenario: An assistant discovers managed sessions
- **WHEN** a client reads the tool schema and requests design_session or evidence_requests
- **THEN** both the operation and its focused view are advertised and execute with their documented contracts

### Requirement: Local replay budgets preserve ordinary source-backed work
Managed revision SHALL retain complete source snapshots, child requests/results, support and fresh replay
of both revisions. Repeated source JSON size SHALL NOT trigger an acquisition guard. Genuine solver work
and output limits SHALL remain distinct, named and inspectable.

#### Scenario: A detailed one-study source is revised
- **WHEN** a retained source-backed session changes only an endpoint collection plan
- **THEN** the original full-source baseline and revision execute within supported solver/output limits without source truncation, stale reuse or mandatory draft-only decomposition

### Requirement: Input admission is separate from semantic effect
Coordinate results SHALL distinguish admitted support from actual use and narrowing. Each input SHALL
identify its applicable consumer, effect or specific no-effect reason. An accepted but unused input SHALL
NOT be presented as a completed check of the person's intended restriction.

#### Scenario: An admitted setting word activates no relation
- **WHEN** an allowed setting-word value has no current narrowing consumer
- **THEN** the result retains the input, names the missing effect and preserves independently computed coordinates

#### Scenario: Evidence is redundant
- **WHEN** an applicable input changes no remaining value because another premise already excludes it
- **THEN** the result distinguishes redundancy from missing support or an unsupported mapping

#### Scenario: Evidence prevents a default
- **WHEN** an admitted input supplies an exact negative guard to an otherwise applicable relation
- **THEN** the result identifies the guarded relation and retained alternatives rather than claiming the input was unused

### Requirement: Aggregate interpretations explain their remaining difference
Common consequences SHALL retain structured reasons for differing frame answers or scopes, with the
relevant frame IDs and warrants. Correct unresolved results SHALL remain unresolved. Compatible rival
readings SHALL NOT become a contradiction or a selected source fact.

#### Scenario: Crossover and entry readings differ
- **WHEN** one compatible frame returns OUT_OF_SCOPE and another returns REFUTED
- **THEN** the common UNDETERMINED result names that scope/outcome contrast and downstream metadata and session handoffs retain it

#### Scenario: A single selected reading is out of scope
- **WHEN** the selected frame cannot answer an entry question because its rule applies only to crossover
- **THEN** the common result preserves that scoped explanation without inventing an entry answer

### Requirement: Frequency thresholds remain descriptive
Frequency threshold output SHALL name its comparison-set denominator and descriptive scope. Small exact
counts SHALL remain reportable. Frequency thresholds SHALL NOT imply clinical standards, recommendations
or class-association support.

#### Scenario: Two selected records both state an exclusion
- **WHEN** both admitted records state it and their lower frequency bound reaches the selected threshold
- **THEN** the count and met threshold remain available as a two-record description, separately from association support and clinical judgment

### Requirement: Invalid deviation input cannot assert a verified deviation
The deviation utility SHALL validate its status, audit and qualifier contract. Unknown or malformed
inputs SHALL have named refusals, while valid unexplained explicit negation remains a verified deviation
and silence remains omission.

#### Scenario: Status code is unknown
- **WHEN** an unknown status or invalid qualifier reaches the utility
- **THEN** it cannot return verified_deviation

### Requirement: Premise attribution does not authenticate confirmation
User-choice and accepted-reading declarations SHALL preserve inspectable origin and revision. Caller
labels SHALL NOT be described as independent verification of a human exchange or source truth. Direct
source facts SHALL remain usable without repeated confirmation.

#### Scenario: The caller writes confirmed in a basis string
- **WHEN** no independent interaction record establishes the human exchange
- **THEN** the supplied premise remains explicitly caller-declared, and its computations remain conditional on that representation

### Requirement: Typed preparation preserves the expanded meaning
Strict typed construction conveniences SHALL expand into the existing validated assertion representation
with source, scope, alternatives, boundaries and standing inspectable. Construction SHALL NOT interpret
clinical prose, choose a reading or promote confirmation.

#### Scenario: A compact typed criterion is prepared
- **WHEN** the assistant constructs a scoped quantity or enum restriction
- **THEN** the expanded request is visible and produces the same result as its explicit validated representation

### Requirement: Explanations preserve permissions and proved conditions
Reasoning replies SHALL retain accepted scoped permission mentions and bounded solver-proved necessary
conditions relevant to a query. They SHALL preserve the original decision and weakest support. Permissions
SHALL NOT establish presence or erase exclusions; unsupported or proposed information SHALL NOT become known.

#### Scenario: A draft explicitly permits a treatment
- **WHEN** a query concerns that treatment in the permission's accepted scope
- **THEN** the reply cites the permission while explaining that it imposes no eligibility requirement

#### Scenario: A threshold depends on a patient condition
- **WHEN** the query remains feasible and the accepted premises prove that it requires a condition
- **THEN** the reply exposes that condition and its deciding warrant beside the original answer

#### Scenario: An impossible profile implies anything vacuously
- **WHEN** the query is refuted, inconsistent or computation-limited
- **THEN** no vacuous implication is presented as a clinically useful necessary condition

### Requirement: Clinical projections conserve warrants
Every supported reasoning operation SHALL expose a compact clinical projection with outcome, standing,
scope, deciding values, support, origin and unresolved causes linked to canonical results. Rendering SHALL
NOT create clinical premises, authenticate confirmation, reinterpret source wording or discard unknown codes.

#### Scenario: A witness rules out a candidate
- **WHEN** a count exceeds an accepted exception allowance
- **THEN** the explanation retains count, denominator, allowance, source and bridge standing beside the elimination

#### Scenario: A result is compacted
- **WHEN** repeated premises or queries are omitted from the view
- **THEN** the complete canonical artifact remains retrievable and verifiable without truncation

### Requirement: Revisions are publicly constructible and explain changes
Public interfaces SHALL return result fingerprints and prepare valid revisions from retained prior
artifacts. Both snapshots SHALL be recomputed. An answer-level difference SHALL distinguish clinical
answers, support and origins from input-only changes while retaining the complete audit difference.

#### Scenario: One NYHA restriction is widened
- **WHEN** two of seven clinical answers change
- **THEN** the clinical change report identifies those two and retains the five unchanged answers despite changed input digests

#### Scenario: Standing changes while a verdict does not
- **WHEN** an unchanged verdict gains or loses admissible support
- **THEN** the support change remains visible and is not classified as clinically unchanged without qualification

#### Scenario: An MCP-only operator revises a session
- **WHEN** the operator supplies an immutable prior artifact and explicit updated premises
- **THEN** the public workflow constructs required integrity fields and recomputes without internal Python or copying a complete response into conversation

### Requirement: Solver budgets describe bounded reasoning work
Session reservations SHALL use a conservative bound on the actual represented solver problem and include
fresh previous and current work. Refusals SHALL report the reservation, limit and concerned work. Ordinary
bounded revisions SHALL run under documented defaults without removing genuine resource safeguards.

#### Scenario: A small represented problem has a large per-check ceiling
- **WHEN** finite domains establish a smaller safe ceiling
- **THEN** reservation uses that warranted bound rather than charging the maximum ceiling for every call

#### Scenario: A request exceeds a genuine bound
- **WHEN** its conservative reservation or actual supported limits are exceeded
- **THEN** the reply names the bound with numbers and never labels unexecuted checks as completed

### Requirement: Clinical decision delivery is reproducible
The system SHALL generate a readable decision list and separate design-review workbook from canonical
reasoning artifacts and declared source records. Each choice SHALL show evidence addresses, option
consequences, status, origin and open items. The original source workbook SHALL remain unchanged.

#### Scenario: A design review is shared
- **WHEN** the operator exports a completed session
- **THEN** the workbook and readable list agree with its canonical decisions and include traceable references and revision changes

#### Scenario: A caller claims the person confirmed a choice
- **WHEN** no independent confirmation mechanism exists
- **THEN** the output visibly attributes the supplied origin without presenting it as authenticated consent or registry truth

### Requirement: Discovery is task-sized and executable
Public discovery SHALL offer a minimal operation card with accepted shape, a runnable example and material
answer rules. Detailed models and full guides SHALL remain available on demand. CLI and MCP SHALL expose
consistent public result access, revision and export contracts with clinical descriptions.

#### Scenario: The operator asks what changed
- **WHEN** the assistant discovers the relevant operation
- **THEN** it receives a usable revision workflow without unrelated signal examples or a complete echoed prior result

#### Scenario: An unsupported operation is requested
- **WHEN** no implementation exists
- **THEN** discovery and execution retain the unsupported status rather than implying complete protocol generation
