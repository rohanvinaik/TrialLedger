# Spec Delta

## Purpose

Turns the free text of each registry record into typed, span-carrying evidence by deterministic rules, so that
the design of every trial becomes a set of computable objects, and names everything that could not be typed.

## ADDED Requirements

### Requirement: Eligibility text is itemized into criteria with exact spans
The system SHALL divide each study's eligibility text into sections (inclusion, exclusion, unsectioned) and
criteria, each with its exact character span, such that the text of the pieces and the separators between
them reproduces the original text exactly. A text it cannot divide SHALL become one criterion with a named
reason.

#### Scenario: A numbered list becomes criteria
- **WHEN** an inclusion section lists "1. ECOG performance status 0 or 1" and "2. Measurable disease per RECIST 1.1"
- **THEN** two inclusion criteria result, each holding its exact text and span

#### Scenario: Heading variants are recognised
- **WHEN** the text heads its sections "Key Inclusion Criteria" and "Key Exclusion Criteria", with or without a colon, in any case
- **THEN** the criteria under each heading carry that heading's section

#### Scenario: Nothing is lost
- **WHEN** a study's eligibility text is itemized
- **THEN** joining every piece and separator in order reproduces the text character for character

#### Scenario: A text without list markers is not forced
- **WHEN** a section contains prose with no list markers
- **THEN** the section is one criterion and the reason `no_list_markers` is recorded

### Requirement: Criteria are typed by deterministic banks
The system SHALL type each criterion with banks of deterministic patterns, each emitting atoms (a concept from
a versioned vocabulary, its polarity as the text states it, its parameters, and its span) or abstaining. No
model SHALL read, summarize or interpret any trial text.

#### Scenario: A performance-status range
- **WHEN** an inclusion criterion reads "Eastern Cooperative Oncology Group (ECOG) performance status 0 or 1"
- **THEN** an atom for ECOG performance status with the allowed values 0 and 1 results, with its span

#### Scenario: A biomarker with polarity
- **WHEN** an inclusion criterion requires "negative or unknown sensitizing EGFR mutation"
- **THEN** an atom for EGFR status with the allowed states negative and unknown results

#### Scenario: A threshold keeps its unit
- **WHEN** an exclusion criterion reads "AST and ALT >= 3 × upper limit of normal"
- **THEN** an atom for each analyte results with the comparator, the value 3 and the unit "× ULN", never a converted value

#### Scenario: Prior therapy fixes what the text states
- **WHEN** an inclusion criterion reads "has not received any prior systemic therapy for advanced lung cancer"
- **THEN** a prior-therapy atom states zero prior systemic lines for advanced disease, with its span

### Requirement: Everything untyped is named
The system SHALL record every criterion that no bank types, and every bank abstention, with a named reason,
and SHALL NOT treat an untyped criterion as the absence of any concept.

#### Scenario: An untyped criterion enters the residual
- **WHEN** no bank types a criterion
- **THEN** it is listed in the residual with its text, span and the reason `no_bank_matched`

#### Scenario: Untyped is not absent
- **WHEN** a study has untyped criteria
- **THEN** no view reports that study as lacking any concept those criteria might contain

### Requirement: Interventions are classified from a cited source or from the record's own words
The system SHALL classify each drug or biological intervention by the RxClass service of the U.S. National
Library of Medicine (FDA Established Pharmacologic Class, MED-RT mechanism of action), trying its name and
every other name the record gives it, each class with its source id; or by a mechanism the record itself
states in the intervention's or arm's description, with its span; and otherwise SHALL leave it unresolved.

#### Scenario: A named drug is classified with its source
- **WHEN** an intervention is named "Pembrolizumab"
- **THEN** it carries the class "Programmed Death Receptor-1 Blocking Antibody" with its RxClass class id and relation source

#### Scenario: A code-named agent is resolved through its other names
- **WHEN** an intervention named by a sponsor code lists a nonproprietary name among its other names that RxClass classifies
- **THEN** it carries that class, and the name that resolved it

#### Scenario: A mechanism stated by the record
- **WHEN** an intervention's description states it is an anti-PD-1 monoclonal antibody and RxClass does not classify it
- **THEN** it carries the stated target with its span, marked as stated by the record rather than by a source

#### Scenario: An unclassifiable agent stays unresolved
- **WHEN** neither RxClass nor the record classifies an intervention
- **THEN** it is unresolved, and every count that groups trials by class reports how many trials have an unresolved experimental intervention
