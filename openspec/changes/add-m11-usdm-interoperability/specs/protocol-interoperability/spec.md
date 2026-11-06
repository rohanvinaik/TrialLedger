# Protocol interoperability

## Purpose

Let clinical teams exchange versioned study definitions and M11 protocol content while preserving original evidence, explicit interpretations and the limits of each computed check.

## ADDED Requirements

### Requirement: Compatibility claims identify their tested profile
The system SHALL identify the USDM, terminology, M11 template/technical-specification and adapter releases used. It SHALL report schema, reference, terminology and business-rule validation separately from reasoning coverage. A successful validation SHALL NOT certify clinical truth or a complete protocol.

#### Scenario: A structurally valid file contains unsupported analysis
- **WHEN** a supported USDM file describes a statistical method outside the available operators
- **THEN** exchange validation and preservation remain reportable while its analysis is explicitly not computed

#### Scenario: The version is unsupported
- **WHEN** a document declares an unsupported or conflicting model version
- **THEN** the original bytes remain available and a named refusal prevents silent migration or semantic projection

### Requirement: Protocol evidence has immutable identity
Imported protocols SHALL retain complete original bytes, source and document identities, versions, digests and exact object addresses. Document identity, study identity, amendment identity and local draft revision SHALL remain distinct. Reads and revisions SHALL preserve existing root isolation, continuation and immutable artifact guarantees.

#### Scenario: Two versions reuse an object identifier
- **WHEN** two protocol editions contain the same local endpoint ID with different definitions
- **THEN** each reference identifies its actual snapshot and edition and neither overwrites the other

### Requirement: Projection conserves source information
Every imported object SHALL have an explicit preservation and mapping disposition, linked to its source and any actual reasoning consumer. Unsupported content SHALL survive independently of the reasoning model. Missing, null, empty, malformed, zero and false SHALL remain distinguishable.

#### Scenario: A criterion is not interpretable
- **WHEN** an eligibility item is retained but has no supported logical mapping
- **THEN** its wording remains accessible and its analysis is unresolved rather than treated as absent or checked

### Requirement: Structured input does not promote standing
Direct transformations SHALL name their source definitions and rules. Interpretations SHALL remain proposed until explicitly admitted; adoption SHALL remain an attributed design choice. An imported document's approval/status code SHALL NOT authenticate a human exchange or adopt its restrictions for another trial. Findings SHALL retain their weakest actual support.

#### Scenario: Approved protocol contains an ambiguous exclusion
- **WHEN** its document status is approved but a reading remains proposed
- **THEN** that reading cannot supply an unconditional accepted constraint

#### Scenario: A direct structured value is available
- **WHEN** a versioned field and its codebook unambiguously establish a source value
- **THEN** the value is usable under that direct warrant without requiring a new human interpretation

### Requirement: Scope and timing survive interchange
Projections SHALL preserve study, cohort, arm, epoch, population role, event anchor, units, boundaries and conditions. Nominal time, permitted window, collection plan and observed availability SHALL remain separate. Unresolved temporal or population correspondence SHALL block only dependent application, with independently warranted information retained.

#### Scenario: Post-discontinuation collection is conditional
- **WHEN** a scheduled assessment applies after discontinuation but the event is not established
- **THEN** the declared obligation remains conditional and does not become an observed collection or unconditional visit

#### Scenario: A calendar duration cannot be exactly converted
- **WHEN** no applicable rule establishes its translation to the requested time representation
- **THEN** the duration is preserved and the dependent calculation names the unresolved mapping instead of assuming a fixed number of days

### Requirement: Competing sources and readings remain separate
The system SHALL retain protocol and registry disagreement with source editions and scope. Rival readings SHALL use existing isolated interpretation frames and warrants. Neither a newer timestamp nor a standards label SHALL silently replace conflicting evidence or select the intended clinical meaning.

#### Scenario: Registry and protocol disagree on performance status
- **WHEN** the two sources state different restrictions
- **THEN** both remain inspectable and adopting one for the draft is an explicit choice rather than source repair

### Requirement: Exchange preserves untouched content and explicit edits
Export SHALL preserve supported native content and unmodified unsupported content, maintain validated references, and distinguish unchanged round trips from deliberate edits. Revisions SHALL use new required object editions/adoptions and replay dependent checks. Unsupported edits SHALL be refused without changing the original artifact.

#### Scenario: One visit window is changed
- **WHEN** a user adopts a revised permitted window
- **THEN** the export changes that declared content and its legitimate dependants while unrelated arms, narratives and unknown extensions retain their recorded values

### Requirement: Warrants travel with explicit portability limits
An exchange package SHALL include an address-bound manifest of source identity, mappings, standing, adoption, assumptions, scope, rules and analysis coverage. It SHALL state which information uses native USDM, a documented extension or companion files. Missing companion evidence SHALL NOT recreate prior acceptance, adoption or proof status from ordinary USDM fields.

#### Scenario: A receiving system strips extensions
- **WHEN** the ordinary protocol returns without its warrant manifest
- **THEN** the source content remains importable but previous TrialLedger acceptance and warrants are not asserted as recovered

### Requirement: M11 coverage is conditional and content based
The system SHALL map supplied content to a pinned M11 edition, distinguish required, conditional and optional elements, and report unmet or undecided requirements. Assembled documents SHALL retain supplied wording and source links. Unknown applicability SHALL NOT become not applicable, and placeholders SHALL NOT satisfy required content.

#### Scenario: Amendment content is conditionally required
- **WHEN** amendment applicability is unresolved
- **THEN** the relevant content requirement remains open rather than silently omitted or declared complete

### Requirement: Public delivery exposes every material boundary
CLI and MCP SHALL share import, discovery, retention, revision and export semantics. Clinical outputs SHALL distinguish preservation, mapping, conformance, analysis coverage, conflicts and open tasks, with exact continuation links. Schema validity or a clean section SHALL NOT hide an unexecuted check.

#### Scenario: A cold operator shares a review
- **WHEN** the operator imports, checks, revises and exports through public interfaces
- **THEN** the decision list and workbook identify source clauses, profiles, scope, standing, deciding warrants and uncomputed content without private code access

### Requirement: Compatibility does not narrow existing capabilities
NIH acquisition/reporting and existing session/artifact formats SHALL retain their supported behavior without implicit migration. Unsupported USDM graphs, extensions or methods SHALL be preserved or explicitly refused at the affected boundary; they SHALL NOT be flattened, silently approximated or executed as caller code.

#### Scenario: A schedule repeats until a clinical event
- **WHEN** the analysis profile cannot represent its stopping rule
- **THEN** the source graph survives exchange and the analysis limitation is visible without truncating it to an arbitrary fixed visit count

### Requirement: Release evidence matches the claim
Each compatibility release SHALL publish its tested profile, external fixture basis, validator results, round-trip/edit checks, authored positive/MUST-NOT cases, scoped Detective two-sign and contract-check status, CLI/MCP parity and cold clinical walkthroughs. Unrun proofs and accepted pin limitations SHALL remain explicitly distinct from successful evidence.

#### Scenario: Internal round trips pass but no partner has tested the file
- **WHEN** only repository fixtures have been exercised
- **THEN** the release reports that tested boundary and does not claim demonstrated partner interoperability
