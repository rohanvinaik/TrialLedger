## ADDED Requirements

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
