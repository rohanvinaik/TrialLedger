# An invented continuing design session

These are executable teaching premises for the main README, **not trial evidence or recommendations**.
All study values, class definitions, product identities, population bindings, bridges and candidate designs
are invented. No API lookup or clinical text recognizer produced them.

Run from the repository root:

```sh
trialledger reason --request examples/partial-evidence/design-request.json
trialledger reason --request examples/partial-evidence/draft-request.json
```

MCP `reason` accepts the same request objects. `design-result.json` and `draft-result.json` retain the complete
public responses. `tests/test_partial_evidence_demo.py` compares fresh CLI/MCP outputs with those files,
checks every signal's actual consumer and exercises the revisions below without network access or file changes.

The design request contains all eight signal kinds and an attributed rejected profile. Twelve hypothetical
candidate explanations are supplied. Nine are ruled out; `marker-PS0-2`, `marker-PS0-3` and `adult-PS0-2`
remain. The question whether every remaining model requires ECOG ≤2 stays UNDETERMINED. This finite family
is explicitly declared, not claimed exhaustive of actual protocols. Surviving models do not establish the
real criterion or the reason for a screening rejection.

The endpoint's source signal remains unresolved because week 12 is unknown. Each otherwise compatible
candidate adds an explicit availability hypothesis, which makes its rule check consistent. That hypothesis
is not a posted observation. A candidate saying observed week 12 was unavailable conflicts with the adopted
observed-only definition. An imputed measurement alone leaves the requirement unresolved.

Revisions tested through both public surfaces:

- Change the joint observation's `bridge.max_exceptions` from 0 to 20: `excludes-joint` returns. At 19 it
  remains ruled out. The intersection stays [20,40], never an exact count.
- Set the rejected observation's bridge resolution to `unresolved`: `PS-only` is retained as unresolved.
- Change `marker-PS0-2`'s week-12 availability claim from observed to imputed: that candidate becomes
  unresolved under the same endpoint definition.
- In the draft request, widen `draft-PS` from ≤2 to ≤3: the ECOG 3 question changes from REFUTED to
  UNDETERMINED with `undecided_by_constraints` (allowed but not required by this restriction).

The draft is a separate invented user choice. Comparator compatibility does not prescribe the new trial's
clinical choices. No source is overwritten, no participant counts are summed across observations and no
cross-signal identity join is inferred. Source and bridge standing remain visible in every dependent check.
