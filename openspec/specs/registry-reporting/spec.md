# Registry reporting

## Purpose

Layer one gives a clinician a readable reference workbook and its supporting record for requested trials.
An assistant operates the API harness and answers from saved evidence. Source preservation, direct warrants
and clinical usability are the contract; clinical interpretation belongs to layer two.

## Requirements

### Requirement: One request produces one coherent reference set
The system SHALL accept study identifiers or a search, resolve the scope explicitly, and produce matching
JSON and a clinical workbook with each study's dossier and shared listings.

#### Scenario: Requested studies
- **WHEN** the person requests identifiers or a subset search
- **THEN** names and filters can be previewed and requested identifiers are accounted for as found, aliased, missing, repeated or malformed

### Requirement: Retrieval completion is checked
The system SHALL retain source responses and check pages, counts, identities and snapshot consistency. It
SHALL NOT present incomplete retrieval as complete.

#### Scenario: Retrieval fails
- **WHEN** a required page fails or the snapshot changes
- **THEN** the run names the retry or new-run action without presenting a partial set as complete

#### Scenario: Relay is required
- **WHEN** the program cannot fetch directly
- **THEN** it names exact responses to save unchanged, records relay mode and does not claim live value-level authentication

### Requirement: Complete source evidence remains available
The system SHALL retain complete gathered registry records. A selected projection SHALL declare its field
sources and exclusions and SHALL NOT be represented as the complete raw record.

#### Scenario: A field is outside the projection
- **WHEN** a gathered record contains an omitted field
- **THEN** its original remains in retained evidence and the omission does not imply source absence

### Requirement: Reporting preserves values and scope
The system SHALL copy values with population, local arm or group, denominator, unit, period and time frame.
It SHALL preserve eligibility wording and SHALL NOT derive clinical meaning from word matches.

#### Scenario: Populations differ
- **WHEN** results and enrollment use different populations or denominators
- **THEN** each retains its scope and groups are not joined by similar titles

#### Scenario: Eligibility has alternatives
- **WHEN** eligibility says A or B is acceptable
- **THEN** the report preserves it without emitting separate requirements for A and B

### Requirement: Direct transformations carry warrants
The system SHALL distinguish copies from transformations and identify sources and rules. Determinism alone
SHALL NOT confer known status on interpretation.

#### Scenario: Headings can be split
- **WHEN** standard inclusion and exclusion headings occur once each in order
- **THEN** text can be divided with exact offsets and lossless reconstruction; otherwise it remains intact and unsectioned

### Requirement: Unknown input is not a clinical negative
The system SHALL distinguish supplied values, zero, false, empty collections, missing values, malformed
input, not-applicable fields and unposted results. Malformed values SHALL be retained without fabricated
typed replacements.

#### Scenario: An event list is empty
- **WHEN** the source supplies an empty event list
- **THEN** the output means no items were listed, not that no harms occurred

#### Scenario: A scalar has the wrong type
- **WHEN** a source field lacks its declared registry type
- **THEN** the typed report is refused at a named source location while its original response remains retained, without coercion

### Requirement: Drug evidence is bound to source identity
The system SHALL use RxNorm and RxClass identity evidence for class attribution. It SHALL retain conflicts
and unresolved identities and SHALL NOT select by alias order or silently equate combinations, salts, brands
or biosimilars with other entities.

#### Scenario: Aliases conflict
- **WHEN** an intervention's names resolve incompatibly
- **THEN** responses remain visible and attribution is unresolved with the conflict named

#### Scenario: A precise ingredient has a base
- **WHEN** the source relates a precise ingredient to a base ingredient
- **THEN** that relationship does not silently widen product identity or search membership

### Requirement: Direct checks expose without correcting
The system SHALL expose approved structured-field checks as consistent, conflict, not applicable or not
checkable. Missing, malformed or imprecise input SHALL NOT pass; conflicting values SHALL remain.

#### Scenario: Affected exceeds at risk
- **WHEN** comparable counts report affected greater than at risk
- **THEN** the check names event, group and counts without rewriting them

### Requirement: Clinical questions guide presentation
The workbook SHALL expose population, eligibility, interventions, outcomes, time points, results, safety,
exploratory measures and documents. It SHALL distinguish plans from observations and include supplied
results-submission, delay or waiver context.

#### Scenario: Results are not posted
- **WHEN** a study has no posted results but supplies submission, delay, waiver or publication information
- **THEN** the output says no results posted and shows that context without inventing findings

#### Scenario: Interpretation is unstated
- **WHEN** treatment setting, biomarker role, a benchmark or protocol language is not directly established
- **THEN** the assistant points to the source and identifies the interpretation as separate layer-two work

### Requirement: Spreadsheet fidelity and readability are both required
The system SHALL preserve types, text, precision, links and record addresses. Unrepresentable values SHALL
name their reason and source location. Listings SHALL continue without truncation. The workbook SHALL be
read back and reviewed for actual readability.

#### Scenario: A value cannot be represented exactly
- **WHEN** the format would round or truncate it
- **THEN** the cell points to the exact record value instead

#### Scenario: Text resembles a formula
- **WHEN** a source string begins with an equals sign
- **THEN** the spreadsheet stores text, not a formula

#### Scenario: Long dossier and index text remains readable and exact
- **WHEN** a dossier value requires continuation or an index title, sponsor or design text needs more display space
- **THEN** the dossier uses visibly labelled ordered continuation rows and the index wraps with row heights that expose the complete text
- **AND** an independent check reconstructs the exact dossier value and reports omitted, reordered or duplicated continuation parts instead of passing them

### Requirement: Verification follows actual dependencies
The system SHALL replay retained evidence under the recorded derivation version and compare record and
workbook. Derivation identity SHALL include output dependencies and exclude unrelated layer-two code and
interface-only changes.

#### Scenario: Unrelated code changes
- **WHEN** only code outside reporting derivation changes
- **THEN** the reporting fingerprint stays unchanged

#### Scenario: Saved evidence or presentation changes
- **WHEN** an input, output value, link or format differs from replay
- **THEN** verification names the difference instead of succeeding

### Requirement: Acceptance follows structure across study types
The system SHALL check source-to-record-to-cell-to-agent fidelity across interventional, observational and
expanded-access structures. Trial IDs and disease phrase lists SHALL NOT decide extraction or establish
general coverage.

#### Scenario: Structure changes
- **WHEN** valid records change applicable fields, identities, order, cardinality or optional values
- **THEN** the generic projection preserves them and independent checks detect planted losses

### Requirement: Reporting cannot execute clinical interpretation
Reporting SHALL NOT invoke clinical recognizers, assertion compilation, defaults, comparability ranking,
cohort conclusions or synthesis. The assistant SHALL answer from the record.

#### Scenario: A report is produced
- **WHEN** the assistant gathers a reference sheet
- **THEN** clinical interpretation is not needed to write or verify it

### Requirement: Assistant access stays usable at larger record sizes
The assistant SHALL retrieve relevant saved evidence with bounded entry and serialized-size pages. Larger
nested values SHALL expose exact-address navigation, and long text SHALL have lossless continuation.
Navigation metadata and text chunks SHALL NOT be represented as complete source values. Limits SHALL NOT
change requested studies, saved evidence or retrieval completeness.

#### Scenario: One study contains a large results table
- **WHEN** a selected page exceeds the response-size budget
- **THEN** the reply provides exact addresses and continuation accounting rather than silently dropping results

#### Scenario: Eligibility exceeds a conversational response
- **WHEN** the exact string is returned in chunks
- **THEN** offsets and next-offset accounting permit exact reconstruction without normalization or omission

### Requirement: The assistant follows the clinical task
The assistant SHALL check execution, storage, connectivity and file delivery before promising a workbook,
show material search choices, handle internal paging/retries, and answer in clinical language with deciding
evidence and material open items. Complete records SHALL remain available as files.

#### Scenario: A capability is missing
- **WHEN** the environment cannot complete or deliver the requested reference sheet
- **THEN** the assistant states the specific gap and a practical next step rather than promising an unavailable output

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

### Requirement: Literal section formatting remains lossless
The system SHALL recognize standard inclusion/exclusion headings across letter-case and line-ending
variants without interpreting clinical text. It SHALL preserve original text and offsets, abstain on
ambiguous repeated or reversed sections, and retain supported historical report verification.

#### Scenario: Lowercase registry headings
- **WHEN** standard headings are written as Inclusion criteria and Exclusion criteria
- **THEN** their passages retain the correct structural section and exact literal local context
- **AND** the parts reconstruct the source without normalization

#### Scenario: A clinical phrase resembles a heading
- **WHEN** a heading occurs inside a sentence, bullet or nonstandard cohort label
- **THEN** it does not establish a top-level section or clinical entry scope

### Requirement: Study identity is available in bounded indexes
The saved-study index SHALL include source titles and acronym with identifier and current index fields.
Missing identity fields SHALL remain distinguishable from actual empty strings.

#### Scenario: A name search returns a study and its emulation
- **WHEN** the assistant retrieves the study index through CLI or MCP
- **THEN** source titles permit identity inspection without separate reads of each title

### Requirement: Compact tables conserve source scope
A compact baseline view SHALL retain every represented value, group identity, denominator, parameter,
unit, class/category and exact address. It SHALL NOT join populations, periods or similarly titled groups.
Empty optional annotation cells SHALL be blank while genuine source notes and derivation provenance remain.

#### Scenario: NYHA has three classes and three source groups
- **WHEN** a compact table presents those measurements
- **THEN** all nine source values remain individually addressable and the Total group is not added to its component groups

#### Scenario: Safety has no optional note
- **WHEN** neither a source note nor a derivation note applies
- **THEN** the Notes cell is blank without changing clinical missing-value semantics in other columns

#### Scenario: An at-risk denominator uses a group total
- **WHEN** that warranted transformation supplies a denominator
- **THEN** its rule and source provenance remain visible in Notes
