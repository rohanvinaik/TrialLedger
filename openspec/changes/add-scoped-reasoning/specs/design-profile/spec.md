# Spec Delta

## Purpose

The profile's frequencies keep what a record states apart from what a trial's full criteria hold: the registry
statement rate is a point, the full-criteria frequency of an eligibility element an interval whose unresolved
silences are counted by kind, and every threshold and comparison is decided against that interval (Decision 12).

## MODIFIED Requirements

### Requirement: Frequencies have explicit denominators
The system SHALL report, for every typed element in a stratum, the number of trials stating it (S), the number
of the stratum's trials (N, every trial, whether or not its eligibility was itemized or typed), the registry
statement rate S/N, its surprisal in bits and the number of distinct lead sponsors among the trials stating it.
For an eligibility element (an inclusion, exclusion, permitted or unsectioned element) it SHALL also report the
full-criteria frequency as the identification interval [S/N, (S+U)/N], where A counts the silent trials whose
absence a declared ascertainment rule establishes and U the silent trials whose silence does not establish
absence, U counted separately as empty eligibility, eligibility no rule typed (no rule match), a record that says
the element's section is abbreviated, and a record that says nothing of its coverage. While no ascertainment rule
is declared, A SHALL be 0 and SHALL be labelled as 0 by construction. The system SHALL NOT count a silent trial
as lacking an element, and SHALL NOT merge a trial no rule typed into any other kind of silence. A primary
endpoint is not an eligibility element: the system SHALL report its statement rate only, with no interval, and
its row SHALL say so.

#### Scenario: An untyped trial is not counted as lacking an element
- **WHEN** a trial's eligibility text is present but no rule typed any of it
- **THEN** it is in every element's N, and for each eligibility element it does not state it is counted in U as no rule match, never in A and never as unspecified

#### Scenario: An abbreviated record's silence is unresolved
- **WHEN** a typed trial whose record says "Key Exclusion Criteria" does not state an exclusion element
- **THEN** it is counted in that element's U as abbreviated, and the upper bound of the interval includes it

#### Scenario: A primary endpoint has the statement rate only
- **WHEN** every trial of a stratum states the same primary endpoint
- **THEN** its row gives S, N and the statement rate, no A, U or interval, and says it is the statement rate only

### Requirement: Standard language is a tier, not a verdict
The system SHALL decide the standard tier of an eligibility element from its full-criteria interval against a
named share, with the share shown: met when the lower bound reaches the share, not met when the upper bound
falls short of it, unresolved otherwise, comparing unrounded values. A primary endpoint SHALL have no tier. The
system SHALL NOT treat a standard element as clinically unimportant or a rare element as clinically important.

#### Scenario: A near-universal criterion
- **WHEN** an eligibility element is stated by 95% of the trials in a stratum and the standard share is 90%
- **THEN** its tier is met in that stratum, with its statement rate, its interval and its sponsor count

#### Scenario: Silence keeps the tier unresolved
- **WHEN** an eligibility element is stated by 80% of a stratum's trials and the other 20% are silent with no ascertainment rule declared
- **THEN** its tier is unresolved, never not met

### Requirement: Mechanism signals are proposals
The system SHALL compare each element's statement rate among the typed trials whose experimental arm carries a
mechanism class with its statement rate among the other typed trials of the same stratum, report the counts,
the difference, the silent trials of each group whose record says the element's section is abbreviated, the
difference at the least favourable reading of those silences, the number of distinct sponsors and the number of
trials with an unresolved class, and SHALL present every such association as a proposed relation, never as an
established one. It SHALL offer an association as proposed only when the comparison still holds with every
abbreviated silence among the other trials counted as stating the element and every one in the class counted as
lacking it, and with enough supporting trials and sponsors; it SHALL mark the association unresolved when
abbreviated silences could reverse the comparison, and SHALL NOT list an element whose comparison fails at
every reading. A trial whose eligibility was never typed SHALL be in neither group.

#### Scenario: One sponsor cannot make a signal
- **WHEN** every trial stating an element in a mechanism class shares one lead sponsor
- **THEN** the association is reported with a sponsor count of one and is not offered as a proposal

#### Scenario: Unresolved classes are shown
- **WHEN** some trials in a stratum have an experimental intervention with no class
- **THEN** every mechanism signal in that stratum shows how many

#### Scenario: Abbreviated silences could reverse a signal
- **WHEN** an exclusion element is stated by 5 of 6 trials in a class and 1 of 4 others, and the 3 silent others say their exclusions are abbreviated
- **THEN** the association is unresolved, not proposed, whatever its sponsor count
