## ADDED Requirements

### Requirement: Layer one reports facts and direct derivations only
Ordinary reports SHALL contain selected registry facts and strictly warranted direct derivations. They SHALL
NOT invoke clinical analysis, indication assignment, assertion compilation, criterion ranking, biomarker
recognition, cross-trial inference or MeSH enrichment. Existing layer-two work SHALL remain separate.

#### Scenario: Registry prose mentions treatment history or a biomarker
- **WHEN** a retained criterion or outcome contains that text
- **THEN** the report preserves the exact text and location without assigning a therapy setting or biomarker role

### Requirement: Source fields are preserved once with their scope
The schema-4 record SHALL carry selected registry values plainly with source paths defined once in fields. Results SHALL
retain nesting, module-local groups, populations, denominators, units, times, precision, comments and explicit
zeros. Missing, malformed, false and empty SHALL remain distinct.

#### Scenario: Groups share titles across modules
- **WHEN** an outcome group and a safety group have the same title
- **THEN** each remains bound to its own module rather than being merged by title

### Requirement: Direct derivations state their basis
A derivation SHALL name its rule/version and exact source inputs. Eligibility segmentation SHALL preserve and
reconstruct the source, abstaining on ambiguous structure. Collection presence SHALL describe only source shape;
results state, links, labels, exact counts and directly returned RxNav evidence SHALL establish no clinical inference.

#### Scenario: An event list is empty or missing
- **WHEN** a list is explicitly empty, absent or malformed
- **THEN** the report distinguishes those states and never infers zero harms or an absent clinical condition

### Requirement: All three study types retain their relevant context
INTERVENTIONAL, OBSERVATIONAL and EXPANDED_ACCESS reporting SHALL preserve relevant source-present design and
population fields. Applicability SHALL cite metadata/source evidence. A present optional or historical value SHALL
NOT be hidden by a generic type policy.

#### Scenario: Observational and access context is stated
- **WHEN** the source gives sampling, study population, specimen retention or access type/availability/linkage
- **THEN** the record and workbook preserve those values with false and missing distinguished

### Requirement: The workbook and assistant expose the same readable evidence
The workbook SHALL use readable source labels and preserve cell type/value without truncation or rounding.
Every listing row SHALL have a record address that MCP resolves to the same scoped evidence. Unsupported Excel
values SHALL name the reason and record location. Oversized listings SHALL continue without dropping rows.

#### Scenario: A person asks about a result row
- **WHEN** the row is retrieved by its address
- **THEN** MCP returns its measurement, group, population and denominator as held in the record

### Requirement: Retrieval and replay are accountable
The operation SHALL preview/fix the search, account for pages and requested IDs, check counts/duplicates/snapshot
consistency, and retain unchanged relay bodies. Offline verify SHALL reconstruct the report under its writing
code and name changed/missing inputs or output differences without fetching repairs.

#### Scenario: A requested ID is missing
- **WHEN** retrieval completes but one requested ID was not found
- **THEN** the accounting names it and completion is not presented as proof that every requested ID was found

### Requirement: Reporting acceptance spans study types without a fitted fixture set
Acceptance SHALL cover the relevant source schema, enum and study-type applicability branches, independent
source expectations, perturbations, seeded defects and actual workbook visual checks under design §5. The writer
SHALL NOT depend on trial IDs, diagnosis vocabulary or clinical phrase recognition. Unsupported fields SHALL be
named. An interpretation-accuracy sampling campaign SHALL NOT be a reporting-delivery prerequisite.

#### Scenario: Fixed oncology examples pass but observational population is lost
- **WHEN** an observational source states its study population but the report omits it
- **THEN** that reporting combination fails regardless of other passing examples

#### Scenario: A source-preservation defect is repaired
- **WHEN** a source value is lost or misdisplayed
- **THEN** the repair addresses its generic field/shape rule and is checked with varied IDs and source values,
  rather than adding an exception for the affected trial

### Requirement: Reporting claims do not imply clinical interpretation
Acceptance SHALL check preservation, readability and access to available clinical-development source material,
not require a compiler, external-source synthesis or inferred answers. Tests SHALL NOT be presented as proof of
clinical correctness. Defaults, proposals and design decisions SHALL belong to layer two.

#### Scenario: The registry contains no current-care benchmark
- **WHEN** the person seeks current care, a comparative safety target or reusable protocol requirements
- **THEN** the report exposes its source evidence and limits without inventing the answer or failing a faithful
  reporting operation for lacking a layer-two inference
