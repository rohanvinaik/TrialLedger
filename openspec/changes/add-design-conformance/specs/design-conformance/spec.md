## ADDED Requirements

### Requirement: Every lexical or data-driven decision in a reading module is declared
The gate SHALL fail when a reading module holds a regular expression, word collection, inline word test or
runtime data load that the conformance inventory does not declare, and when a decision entry names no warrant from
the closed set of the design's §2.

#### Scenario: an undeclared word list
- **WHEN** a commit adds a list of condition words to a reading module without an inventory entry
- **THEN** the conformance test fails and names the module and the collection

#### Scenario: a decision without a warrant
- **WHEN** an inventory entry declares a collection as a decision with no warrant, or cites a decision id that no
  design document holds
- **THEN** the conformance test fails

#### Scenario: a decision moved into a resource file
- **WHEN** a commit moves a word list out of a reading module into a JSON, YAML or CSV file the module loads at run
  time, without declaring the resource and its hash
- **THEN** the conformance test fails and names the module and the file

#### Scenario: one legacy shortcut swapped for another
- **WHEN** a commit replaces a legacy decision's literals or behaviour with different ones while the number of
  legacy decisions stays the same
- **THEN** the conformance test fails, because each legacy decision is pinned by its identity, its literals' hash
  and its pinned inputs and outputs

### Requirement: Every change to reading logic carries a trace reviewed against that code
The push check SHALL refuse a commit that changes the code of a reading module or a conformance input unless its
message names a trace file present in that commit, holding the template's sections, a review verdict other than
"does not conform", and the content hashes of the modules and resources reviewed, each equal to the hash in the
commit's tree.

#### Scenario: a reading change without a trace
- **WHEN** a pushed commit changes a decision in a reading module and its message names no trace
- **THEN** the push is refused, naming the commit and the module

#### Scenario: a trace attached to code it did not review
- **WHEN** a commit's trace records a reviewed hash for a module that differs from the module in the commit
- **THEN** the push is refused, naming the module

#### Scenario: a docstring-only change
- **WHEN** a pushed commit changes only comments or docstrings of a reading module
- **THEN** no trace is required

#### Scenario: a trace whose review found non-conformance
- **WHEN** the named trace's review verdict is "does not conform"
- **THEN** the push is refused

### Requirement: The checks run on every push to main, off the builder's machine
A GitHub Actions workflow SHALL run the gate, the conformance test and the trace check on every push to main, and
the local push check SHALL refuse a push while the latest such run on main has failed, saying so when that state
cannot be read.

#### Scenario: a push with the local hook skipped
- **WHEN** a commit that fails the conformance test reaches main without the local hook
- **THEN** the GitHub run on that commit fails and reports it, and the next local push is refused until it is fixed

### Requirement: The known shortcut kinds are pinned by executable counterexamples
Fixture registry pages run through `trialledger landscape` SHALL produce the required unresolved, interpolated or
not-applicable outcome for each shortcut kind found on 2026-11-02 and each perturbation of design §7.4.

#### Scenario: duplicated evidence presented as separate support
- **WHEN** the same text, or a registry term derived from that text, is offered twice as support for one reading
- **THEN** it is counted once, and the reading's status is what that one piece of evidence warrants

#### Scenario: a non-oncology trial in oncology patients
- **WHEN** a nausea trial enrols patients receiving chemotherapy
- **THEN** the trial is not shown as outside oncology

#### Scenario: an unsupported projection
- **WHEN** a consumer that requires a structurally established assertion is given a legacy reading
- **THEN** the consumer refuses it with a named failure

### Requirement: The path to the MVP is persisted and kept current
The repository SHALL hold the path to a complete layer one and layer two as a document listing each remaining
change with its entry conditions, acceptance criteria and claims, and a test SHALL fail when the document names a
change that does not exist or marks a step done whose change has open tasks.

#### Scenario: a step marked done too early
- **WHEN** the path marks a change's step done while that change has an unticked task
- **THEN** the test fails
