# Negative-evidence review: current CLI behavior

These five requests use invented score values, counts and rules from the public design-bounds example. They are not trial evidence. Each was executed through the real CLI; the complete submitted request and returned result are retained. The supplied eligibility bridge is interpolated, including its zero-exception assumption.

- An accepted score-2 witness leaves two declared upper-cutoff candidates.
- Adding a rejected score-3 witness leaves one candidate. Its elimination and common consequence retain interpolated standing.
- Accepted and rejected score-2 witnesses empty this declared family and return CONFLICT, without claiming that every real protocol is impossible.
- Making the negative bridge proposed prevents its elimination; the independent positive elimination remains.

- A score-2 profile with an unspecified second measurement can have both eligible and ineligible examples under a two-requirement candidate. The score-only candidate is eliminated; the missing measurement is not filled or universally excluded.

Candidate metadata is classified for all five requests. This verifies existing witness and metadata behavior. It does not verify the planned target-set bridge, evidence-request enumerator, managed-origin admission, MCP parity for these new cases, or a fresh clinical walkthrough. Those remain open tasks in the plan.

`identities.json` records the writing module identities and hashes of complete requests/results. Replay from the repository root with `.venv/bin/trialledger reason --request <this-folder>/<case>-request.json`; compare using the recorded writing version.
