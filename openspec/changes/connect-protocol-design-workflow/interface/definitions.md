# Frozen interface: definition relations over protocol checks (task 5.4, DEF-1/DEF-2), interface v1

This extends the existing session `definition_checks` owner (`TrialLedger/layer2/definition_checks.py`). It
does not create a second meaning checker. A declared relation still binds two attributed typed readings to actual
computed addresses, and is still computed by fresh entailment in both directions where the relation needs it.

## Operand

An operand is the existing `{analysis, address, body, status, resolution, basis}`, **or** the same object with
`analysis` replaced by:

```text
protocol_check: <declared protocol check id>
child: <non-negative integer index into that check's children>  (optional, default 0)
```

- Exactly one of `analysis` or `protocol_check` is present (`definition_operand_reference`).
- `address` is an RFC 6901 pointer that begins `/request` or `/result`, evaluated on that protocol child's
  retained `{request, result}`.
- An unknown check gives `definition_unknown_protocol_check`. A missing child is a named translation refusal at
  run time (`definition_protocol_child_missing:<check id>`), never a guess.
- Both operands must have the same target. Protocol checks always have the session target.
- Protocol operands are allowed only in v2 sessions (`definition_protocol_requires_v2`).

## Evaluation

- Relations whose operands reference protocol checks are evaluated **after** the protocol checks have run, using
  the retained child `{request, result}`.
- The output row is the existing definition-check row: `id`, `relation`, `code`, `status`, `target`,
  `declaration`, `observed`, `checks`, `blockers`, `basis` and `guarantee`.
- Rows appear in `result.definition_checks` in declaration order, beside analysis-operand relations.
- A protocol child whose result is not `complete` blocks with `definition_protocol_child_refused:<check id>`.
- `observed` holds the actual retained value at each address, beside the declared reading. TrialLedger never
  certifies that a reading reproduces that value: a reading stays an attributed translation, and the reviewer
  compares the two. The acceptance fixture binds each reading to the threshold its own check carries (a
  finite-policy transition guard), and asserts that the reading equals the observed guard.

## Acceptance

- **DEF-1.** Two protocol checks carry different MADRS thresholds: a retreatment trigger at "MADRS ≥ 20" and a
  relapse definition at "MADRS ≥ 22 on two consecutive visits".
  - Their attributed readings stay two definitions.
  - A declared `equivalent` relation is refuted. A declared `implies` from the stricter relapse reading to the
    earlier trigger is checked on its own terms, and holds when the readings entail it.
  - A numeric difference alone is never reported as a contradiction.
- **DEF-2.** The same number under a different baseline, edition or population gives readings whose bodies differ
  in those typed fields. The relation is not established from the equal number alone.
- **MUST-NOT.**
  - A relation is never established from shared labels or check ids.
  - A proposed operand reading never becomes an admitted relation premise (`definition_proposed_refused`).
  - A missing address is never filled.
