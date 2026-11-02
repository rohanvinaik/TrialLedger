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

### Requirement: A disease-specific rule applies only within the indications it declares
Each study's record SHALL carry its disease as the registry states it, with no category assigned in its place,
and each disease-specific rule pack SHALL declare its indications and apply by add-scoped-reasoning Decision 4
(conditions first, the study's own disease statements next, the registry's MeSH last; a disagreement is a named
conflict; unresolved is never a negative).

#### Scenario: a psychotherapy trial carries no NSCLC setting
- **WHEN** a study's conditions are post-traumatic stress disorder and COVID-19
- **THEN** the NSCLC setting and line rules are inapplicable, and its record carries no setting or line reading

#### Scenario: a mis-derived MeSH term switches nothing on
- **WHEN** a study's conditions establish Alzheimer disease and its registry MeSH also carries "Lymphoma,
  Follicular"
- **THEN** its indication is Alzheimer disease, the MeSH term is shown as a named conflict, and no lymphoma rule
  applies

#### Scenario: undecidable scope is visible
- **WHEN** no source establishes the indication
- **THEN** each disease-specific pack reads scope unresolved with each source's finding, never a silent absence

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

### Requirement: The person sees the search before anything is gathered
The run SHALL offer a preview that resolves the request, writes the resolved search and returns it without
retrieving any study, and SHALL then execute against that fixed search.

#### Scenario: previewing a broad class retrieves nothing
- **WHEN** the person previews a request for a broad drug class
- **THEN** the resolved search with every member and subclass is returned and no study is requested from the
  registry

### Requirement: Every workbook row can be traced to the record
Every row of every listing SHALL carry its address in landscape.json, and the assistant's record tool SHALL
return the value at that address.

#### Scenario: asking about a workbook row
- **WHEN** the person names a row of the Posted results sheet to the assistant
- **THEN** the assistant reads that row's address and returns the same measurement, group, population and
  denominator the row shows

### Requirement: A condition that names no disease establishes nothing
A condition that is not a disease's declared name or an NLM MeSH entry term of a disease SHALL establish no
indication.

#### Scenario: conditions that are not diseases
- **WHEN** a study has no condition MeSH and its only condition is "Progression Free Survival"
- **THEN** its indication is unresolved with each source's finding, and no disease-specific reading is computed
  or denied silently

### Requirement: The workbook answers the reviewer's questions
The acceptance SHALL include, for each item of the reviewer's list (design §4a), a task a clinical reviewer
performs on the workbook with its expected sheet, evidence and unresolved cases, including telling a cohort's
restriction from the whole trial's and telling a follow-up horizon from an assessment time.

#### Scenario: a cohort restriction is not read as the trial's
- **WHEN** a criterion applies only to one cohort
- **THEN** the workbook does not show it as the whole trial's requirement
