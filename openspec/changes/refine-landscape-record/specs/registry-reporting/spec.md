# Spec Delta

## MODIFIED Requirements

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

#### Scenario: A class phrase has multiple source candidates
- **WHEN** a requested class phrase resolves to more than one source-backed class candidate
- **THEN** candidate source names and IDs are shown for selection, and only the selected class is expanded in the subsequent preview

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

## ADDED Requirements

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

## ADDED Requirements

### Requirement: Safety listings preserve event-by-group identity
The system SHALL keep each safety event attached to its exact source title and local group, with the reported
affected and at-risk counts and their populations, units and periods where supplied. It SHALL NOT join rows
by similar event or group titles.

#### Scenario: One event is reported for multiple groups
- **WHEN** the same event title appears for more than one local group
- **THEN** each event-by-group row retains its source title, group identity and counts independently

### Requirement: Record addresses remain discoverable and exact
The workbook and record interface SHALL retain complete record addresses. When an address is collapsed for
display, a clear visible action SHALL reveal the full exact value so the person can identify which saved value
it selects.

#### Scenario: An address is collapsed
- **WHEN** a record address is collapsed for display
- **THEN** a clear visible action reveals the complete exact address

### Requirement: API probe outcomes distinguish reachability and HTTP access
The availability probe SHALL distinguish transport failure from HTTP status outcomes: 2xx `reachable`,
401/403 `access_blocked`, 429 `rate_limited`, 5xx `service_unavailable`, and other statuses
`unexpected_response`. The report SHALL give per-host `connection_advice` consistent with the observed
outcome. Probe outcomes SHALL NOT be presented as clinical search results; response decoding and shape
validation remain part of gathering.

#### Scenario: The probe receives an access-blocked response
- **WHEN** the probe receives HTTP 401 or 403
- **THEN** it reports `access_blocked` and does not recommend bypassing access controls

#### Scenario: The probe is rate limited or unavailable
- **WHEN** the probe receives HTTP 429 or a 5xx response
- **THEN** it reports `rate_limited` or `service_unavailable` respectively, with permitted wait/retry guidance

#### Scenario: The probe receives another HTTP status
- **WHEN** the probe receives a non-2xx status not covered above
- **THEN** it reports `unexpected_response`, distinct from a successful empty search

#### Scenario: The probe cannot connect
- **WHEN** the probe fails before receiving an HTTP response
- **THEN** it reports a transport failure separately from all HTTP status outcomes

#### Scenario: The probe reports per-host recovery guidance
- **WHEN** the probe records an HTTP or transport outcome for a host
- **THEN** its `connection_advice` reflects that outcome: wait before retrying rate limits, retry service outages later, do not bypass blocked access, and review an unexpected endpoint response
