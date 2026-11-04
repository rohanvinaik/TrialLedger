## ADDED Requirements

### Requirement: Acquisition limits describe the requested NIH work
The system SHALL guard expected study count and registry-request complexity before bulk retrieval. It
SHALL retain the intended budget and observed expansion, name refusals and preserve completed evidence.
An explicitly budgeted large pull SHALL remain possible. Local reasoning replay SHALL NOT be treated as
new NIH acquisition.

#### Scenario: A nonempty query is accidentally broad
- **WHEN** the first identifier response exceeds the declared or documented default acquisition budget
- **THEN** direct and relay paths stop before remaining identifier pages or full-study batches, name the count and budget, and explain how to revise scope or explicitly budget the intended pull

#### Scenario: A legitimate larger scope is requested
- **WHEN** a valid explicit acquisition budget covers the observed count and planned registry requests
- **THEN** complete retrieval proceeds with the same paging, identity and snapshot checks

#### Scenario: An acquisition budget is malformed
- **WHEN** a budget contains unknown fields, booleans in integer slots or invalid limits
- **THEN** the request is refused by a named validation result before retrieval

### Requirement: Individual passages retain literal local source context
Eligibility passage rows SHALL retain the nearest source heading text and source offsets when structurally
available, alongside the coarse top-level section and exact passage. Sorting, filtering and continuation
SHALL NOT silently remove this context. A copied heading SHALL NOT establish clinical scope or force.

#### Scenario: Crossover criteria follow a top-level inclusion heading
- **WHEN** an ECOG passage follows the literal heading Crossover Inclusion Criteria
- **THEN** its JSON, workbook row and address access preserve that heading beside the passage without asserting entry eligibility

#### Scenario: Structure is ambiguous or absent
- **WHEN** a nearest heading cannot be established from source structure
- **THEN** the context remains unstated, with exact text and offsets intact rather than an invented heading

#### Scenario: An old report is verified
- **WHEN** a retained report predates the context fields
- **THEN** replay uses its supported writing contract or names incompatibility, never silently claims equality to the new representation

### Requirement: CLI and MCP share bounded saved-record access
The CLI SHALL expose the same saved-record parts, address selection, page limits and exact text
continuations as MCP. Both SHALL preserve scope and distinguish navigation, partial text and complete
values. Invalid addresses and limits SHALL have named refusals.

#### Scenario: A CLI-only assistant needs one eligibility passage
- **WHEN** it requests a study or exact saved address through the CLI
- **THEN** it receives bounded evidence and explicit continuation without loading the whole record into conversation

#### Scenario: Trial name is not an acronym field
- **WHEN** a registry text search resolves a name through another source field
- **THEN** the assistant can use the supported query route and verify returned identity without inventing an acronym or recalling an identifier
