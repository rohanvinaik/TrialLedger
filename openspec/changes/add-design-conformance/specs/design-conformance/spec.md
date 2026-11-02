## ADDED Requirements

### Requirement: Every lexical collection in a reading module is declared
The gate SHALL fail when a reading module holds a regular expression or a literal word or phrase collection that
the conformance inventory does not declare as recognition or decision, and when a decision entry cites no design
decision or names no independent source it is combined with.

#### Scenario: an undeclared word list
- **WHEN** a commit adds a list of condition words to a reading module without an inventory entry
- **THEN** the conformance test fails and names the module and the collection

#### Scenario: a decision without authority
- **WHEN** an inventory entry declares a collection as a decision but cites no design decision, or a decision id
  that no design document holds
- **THEN** the conformance test fails

#### Scenario: legacy decisions only shrink
- **WHEN** a change adds an entry to the legacy decisions beyond the declared maximum
- **THEN** the conformance test fails

### Requirement: Every change to reading logic carries a reviewed trace
The push gate SHALL refuse a commit that changes the code of a reading module unless its message names a trace
file present in that commit, holding the template's sections and an independent review verdict other than "does
not conform".

#### Scenario: a reading change without a trace
- **WHEN** a pushed commit changes a decision in a reading module and its message names no trace
- **THEN** the push is refused, naming the commit and the module

#### Scenario: a docstring-only change
- **WHEN** a pushed commit changes only comments or docstrings of a reading module
- **THEN** no trace is required

#### Scenario: a trace whose review found non-conformance
- **WHEN** the named trace's review verdict is "does not conform"
- **THEN** the push is refused

### Requirement: The path to the MVP is persisted and kept current
The repository SHALL hold the path to a complete layer one and layer two as a document listing each remaining
change with its entry conditions, acceptance criteria and claims, and a test SHALL fail when the document names a
change that does not exist or marks a step done whose change has open tasks.

#### Scenario: a step marked done too early
- **WHEN** the path marks a change's step done while that change has an unticked task
- **THEN** the test fails
