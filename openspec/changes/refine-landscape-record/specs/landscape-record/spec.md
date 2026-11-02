## ADDED Requirements

### Requirement: The record carries every registry value a reviewer uses, once
landscape.json (schema 3) SHALL carry each field of the contract table (`TrialLedger/contract.py`) that the
registry record holds, as a plain value, with the field's API path stated once in the record's field dictionary,
and SHALL keep a value object (status, rule, words read, note) only for a rule's reading or a value that is not
simply known.

#### Scenario: a value the registry holds is never shown as not stated
- **WHEN** a study's registry record holds a field of the contract table (its brief title, its last update date,
  a posted measure's analysis population)
- **THEN** the record carries that value and the workbook shows it, and a contract field whose API path does not
  resolve in the saved bodies fails the contract test

#### Scenario: a registry copy is stored without repeated provenance
- **WHEN** a value is copied from the registry unchanged
- **THEN** it is stored as a plain value, and its API path appears once, in the field dictionary, never beside
  each value

### Requirement: Nothing is kept that nobody uses
Every field of the contract table SHALL name at least one consumer (a workbook sheet and column, the assistant
through the MCP record tool, or a named layer-two reader), and every consumer it names SHALL exist.

#### Scenario: a field without a consumer is refused
- **WHEN** a field is added to the contract table without a consumer, or names a sheet, column or reader that
  does not exist
- **THEN** the contract test fails

### Requirement: Results keep the registry's own structure
Posted outcomes, statistical analyses, baseline characteristics, participant flow and adverse events SHALL be
stored in the registry's nesting, with each module's groups keyed within the module, denominators at the scope
the registry gives them, and the registry's listed zeros kept.

#### Scenario: groups of different modules are not merged
- **WHEN** an outcome group and an adverse-event group have the same title
- **THEN** they remain distinct groups of their own modules unless a named rule links them

### Requirement: Domain readings apply only within their universe
Each study SHALL be assigned universes by a named rule over its condition MeSH terms and ancestors, its free-text
conditions and titles, and, for a treatment study, its interventions' MeSH; the assignment and each source's
finding SHALL be recorded and shown on the Trial index. A domain reading SHALL be computed only where its pack's
requirements hold; an explicit mention SHALL still be recognized in every universe.

#### Scenario: a psychotherapy trial carries no oncology setting
- **WHEN** a study's conditions are post-traumatic stress disorder and COVID-19 and its intervention is
  behavioural
- **THEN** it is in the general universe, its record carries no setting or line-of-therapy reading, and its index
  row says why

#### Scenario: a cancer trial without condition MeSH is still oncology
- **WHEN** a study's only condition is "Advanced Malignant Solid Neoplasm" and the registry gives no condition MeSH
- **THEN** it is assigned to solid-tumour oncology from its free-text condition, and the index names that source

#### Scenario: undecidable scope is visible
- **WHEN** the sources disagree or none decides
- **THEN** the study's scope reads unresolved with each source's finding, never a silent absence

### Requirement: The workbook is the reviewer's
landscape.xlsx SHALL show codes in clinical words through versioned display dictionaries, SHALL hold one row per
rule reading in its Readings sheet and each registry-copied column's source once in its column dictionary, and
SHALL lay out adverse events one row per term with each group's affected and at-risk counts.

#### Scenario: an adverse-event table does not explode
- **WHEN** a trial reports 243 terms across 14 groups
- **THEN** the Safety sheet holds 243 rows for its table of those terms, each with the 14 groups' counts

### Requirement: Lookups ask for each drug once
The run SHALL ask RxNav about distinct drugs taken from the registry's structured intervention names, with a
declared bound on requests in flight within NLM's published limit, and SHALL write the answers in an order that
does not depend on the order replies arrive.

#### Scenario: dose-labelled arms are one drug
- **WHEN** five arms name the same drug at five doses
- **THEN** RxNav is asked about that drug once
