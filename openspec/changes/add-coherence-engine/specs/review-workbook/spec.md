# Spec Delta

## MODIFIED Requirements

### Requirement: Every value carries a warrant
The system SHALL give every presented value a warrant committing to its basis: the study's digest, the
value's location and the value; or the rule, the code root of the code that derives the workbook, the rule's
code and its inputs' warrants. It SHALL NOT present a value whose warrant does not re-derive.

#### Scenario: A warrant commits to all the code a rule can read
- **WHEN** the code of a module the workbook's derivation imports, directly or through another, changes in any way the interpreter would execute differently, or a registry table changes
- **THEN** the code root changes, and with it the warrant of every computed value

#### Scenario: Code that cannot change a derived value does not change a warrant
- **WHEN** only code the derivation does not import changes, such as the command line's help text
- **THEN** the code root is unchanged, and folders written before the change still verify

#### Scenario: Prose in the code does not change a warrant
- **WHEN** only a docstring, a comment or the layout of the derivation code changes
- **THEN** the code root and every warrant are unchanged, and folders written before the change still verify
