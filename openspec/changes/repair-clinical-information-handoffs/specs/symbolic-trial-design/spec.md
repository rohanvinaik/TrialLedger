## ADDED Requirements

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
