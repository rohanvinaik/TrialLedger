# Spec Delta

## Purpose

Projects the ledger into two workbooks a clinical reviewer can open without a terminal: the review workbook,
organised around the ten study-design questions, and the record workbook, which presents every value; every
value labelled by how it was obtained and every source one click away.

## ADDED Requirements

### Requirement: The workbook answers the ten design questions from the ledger
The system SHALL write, for every pulled study, the population fields, the eligibility criteria, every
registered outcome with its type and time frame, other pre-specified outcomes, the arms and interventions,
adverse events per group, and posted outcome results per group, all taken from the ledger.

#### Scenario: Eligibility and safety are present
- **WHEN** a pulled study has eligibility criteria and posted adverse events
- **THEN** the workbook shows the criteria in full and every serious and other adverse event with its term, organ system, group, number affected and number at risk

#### Scenario: Posted outcome results are shown per group
- **WHEN** a pulled study has posted outcome results
- **THEN** the workbook shows each measurement with its outcome, type, time frame, group, measure type, unit and value, exactly as posted

### Requirement: Every value is labelled stated, computed or needs review
The system SHALL label each value as stated (read from a structured field, with its record location),
computed (derived by a named rule, shown with its inputs) or needs review (not determinable from structured
fields, shown with its sources). It SHALL NOT fill a needs-review value.

#### Scenario: Line of therapy is a review item
- **WHEN** a study's line of therapy is not a structured field of its record
- **THEN** the workbook marks it needs review and shows the eligibility text beside it

#### Scenario: Nothing unsourced is filled
- **WHEN** no structured field and no named rule determines a value
- **THEN** the cell is marked needs review and holds no value

### Requirement: Eligibility is split only when the record makes the split unambiguous
The system SHALL show the eligibility text in three parts, the text before the inclusion heading, the
inclusion criteria and the exclusion criteria, only when the text contains the registry's stated inclusion
heading and exclusion heading exactly once each, in that order. Otherwise it SHALL show the whole text and
say why it was not split.

#### Scenario: Standard headings split the text
- **WHEN** the eligibility text has one "Inclusion Criteria" heading followed by one "Exclusion Criteria" heading
- **THEN** the workbook shows the parts separately, an empty part as a blank cell, and the parts joined reproduce the original text exactly

#### Scenario: Ambiguous text stays whole
- **WHEN** a heading is missing, repeated or out of order
- **THEN** the workbook shows the whole text unchanged and names the reason it was not split

### Requirement: A study without posted results says so
The system SHALL state "no results posted" for the results and safety items of every study whose registry
results flag is false, beside the registry's fields that record a results submission under review, a
certification or extension request, or a waiver, and SHALL NOT leave those items blank or show them as zero
events.

#### Scenario: An ongoing study
- **WHEN** a pulled study has no posted results
- **THEN** its safety and results items read "no results posted" and its linked publications are listed beside them

#### Scenario: Results submitted but not yet posted
- **WHEN** a study without posted results records a results submission date not yet posted
- **THEN** the workbook shows that date beside "no results posted", in the registry's words

### Requirement: Every study links to its sources
The system SHALL give each study its registry page, every linked publication with its type in the
registry's own terms and its citation, and every document the sponsor posted, each as a working link.

#### Scenario: Results publications are identified as the responsible party marked them
- **WHEN** a record links a publication typed RESULT
- **THEN** the workbook lists it as reporting results from the study, as the responsible party marked it, with its PubMed link and citation

#### Scenario: A derived publication is never presented as a result
- **WHEN** a record links a publication typed DERIVED
- **THEN** the workbook lists it as added by the registry with no stated role, never as a results publication or a secondary analysis

### Requirement: The spreadsheet never alters a value
The system SHALL write every text value as text and SHALL NOT truncate, clean, round or reinterpret a value.
A value the format cannot hold exactly, text or number, SHALL be replaced by its reason and its record
location.

#### Scenario: Text that looks like a formula stays text
- **WHEN** a value begins with "="
- **THEN** the cell holds that text, not a formula

#### Scenario: Text a cell cannot hold names its reason
- **WHEN** a value contains a character the file format forbids (a control character, U+FFFE, U+FFFF or a lone surrogate), a carriage return, or more characters than a cell holds
- **THEN** the cell names the reason and the record location of the value, and no truncated or cleaned text is written

#### Scenario: A number a cell cannot hold names its reason
- **WHEN** a number would not read back as the same number (an integer of 17 or more digits or one no double holds, a float needing 17 significant digits, negative zero, NaN or an infinity)
- **THEN** the cell names the reason and the record location of the value, and no rounded number is written

### Requirement: Every value of the record is presented in the registry's own categories
The system SHALL present every value of every pulled study in a record workbook beside the review workbook,
each with its category (the section and module names the registry's metadata gives), its field title, its
location and its structural role, and SHALL NOT leave any value of the record unpresented.

#### Scenario: The Record sheets hold every value
- **WHEN** a pull is written
- **THEN** the Record sheets of `record.xlsx` hold one row per value of every study's record, each under the registry's category and field names

### Requirement: A workbook too large for a common spreadsheet app is named
The system SHALL count the cells of each workbook it writes and SHALL name one that holds more than
10,000,000 cells, the most Google Sheets opens in one spreadsheet.

#### Scenario: A large workbook is named, not cut
- **WHEN** a workbook written for a pull holds more than 10,000,000 cells
- **THEN** the pull names the file, its number of cells and the cap, and writes every value all the same

#### Scenario: A large pull is not truncated
- **WHEN** a sheet's rows exceed a worksheet's row limit
- **THEN** the rows continue on a numbered sheet and none is dropped

### Requirement: Every value carries a warrant
The system SHALL give every presented value a warrant committing to its basis: the study's digest, the
value's location and the value; or the rule, the code root of the code that derives the workbook, the rule's
code and its inputs' warrants. It SHALL NOT present a value whose warrant does not re-derive.

#### Scenario: A warrant commits to all the code a rule can read
- **WHEN** a module the workbook's derivation imports, directly or through another, or a registry table changes
- **THEN** the code root changes, and with it the warrant of every computed value

#### Scenario: Code that cannot change a derived value does not change a warrant
- **WHEN** only code the derivation does not import changes, such as the command line's help text
- **THEN** the code root is unchanged, and folders written before the change still verify

### Requirement: The workbook is certified before the pull is written
The system SHALL certify the workbook by re-deriving every cell, its kind of value and every warrant from
the record before the pull is written, and SHALL NOT write a pull whose workbook does not certify.

#### Scenario: A workbook that does not re-derive is never written
- **WHEN** a cell read back differs from what the record derives
- **THEN** the pull is not written, and the difference is named

### Requirement: A written folder can be verified
`trialledger verify` SHALL re-derive every study digest, both roots, every cell and warrant of both
workbooks, and both workbook files part for part, under the code that wrote the folder, and SHALL NOT report
certified a folder it cannot fully re-derive.

#### Scenario: A written workbook certifies against its record
- **WHEN** `trialledger verify` is run on a folder TrialLedger wrote
- **THEN** every study digest, both roots, every cell and warrant, and every part of the workbook file re-derive from `studies.json`, and the command reports the folder certified

#### Scenario: An altered value is named
- **WHEN** a value in `studies.json` or a cell of the workbook is changed after writing, including a number replaced by a boolean
- **THEN** `trialledger verify` names the study digest, the root or the row that no longer follows, and does not report the folder certified

#### Scenario: An altered link, format or part is named
- **WHEN** a link, a format or any other part of the workbook file is changed or added while every cell's value stays the same
- **THEN** `trialledger verify` names the part of the file that differs from what this version writes, and does not report the folder certified

#### Scenario: A record a parser and a reader would read differently is refused
- **WHEN** an object in `studies.json` repeats a key
- **THEN** `trialledger verify` names the key and does not report the folder certified

#### Scenario: Only the code that wrote a folder can certify it
- **WHEN** `trialledger verify` runs under a code root, or a spreadsheet writer, other than the one recorded
- **THEN** it names the difference and the commit that wrote the folder, and does not report the folder certified

#### Scenario: An unreadable workbook is named
- **WHEN** the workbook in a folder cannot be read as a workbook
- **THEN** `trialledger verify` names it as unreadable and does not report the folder certified

### Requirement: The workbooks are written with the record or not at all
The system SHALL write both workbooks inside the same all-or-nothing step as `studies.json` and
`studies.csv`, derived only from the record being written, and SHALL NOT leave a workbook behind when any
file fails.

#### Scenario: A failed write leaves nothing
- **WHEN** writing any of the four files fails
- **THEN** no output directory and no partial workbook remain

#### Scenario: Read back, the workbook matches the ledger
- **WHEN** a workbook has been written
- **THEN** reading it back gives, cell for cell, the values the ledger holds, each of the same kind: text as text, a number as a number, a boolean as a boolean
