# V6 walkthroughs, wave 2 (2026-11-04): cold operators on the public CLI with real NIH pools

The simulated clinicians and assistants were Sonnet agents. They used only public discovery and the CLI; no source
reading. Every clinical choice was labelled simulated. The evidence folders are outside the repo:
`~/trialledger-runs/protocol-walk-neuro-20261104/` and `~/trialledger-runs/protocol-walk-haem-20261104/`. Each has
`brief.md` and `verdict.md` with exact request/response paths, pool accounting and seeded selection.

## Neurology (Phase 2, ALS functional outcome; V6 row "Objects/schedule/dependencies")

- **Pool.** 28 completed Phase 2 ALS studies started 2019–2021. The seeded sample of 4 was NCT04165850,
  NCT04414345, NCT04762589 and NCT04993755. NCT04762589 supplied "change from baseline in ALSFRS-R at 24 weeks"
  and the visit cadence. No instrument edition, window or post-discontinuation handling is stated in the record,
  and none was invented.
- **Wrong design and repair.**
  - The wrong design had collection ending on day 161 inside a 161–175 window, with nominal day 168. It returned
    `violated`: existence was satisfied only at day 161, the nominal day was `not_collected`, and the full window
    was `uncovered`.
  - The repair extended collection.
  - Detected: yes.

## Haematology (Phase 1 dose escalation; V6 row "Finite policy")

- **Wrong policy 1** escalated without a complete DLT window. It was covered and exclusive, but a prohibition
  violation was witnessed; once adopted it reads as a conflict.
- **Wrong policy 2**, a hold self-loop, returned termination `not_established` with `reachable_cycle`.
- **The repair** sends a window-incomplete cohort to a terminal deferred state, and every claim is satisfied.
- Detected: yes. This ran through public `signals`, because of defect 1 below.

## Defects found, and their status

| # | Defect | Status |
|---|---|---|
| 1 | The closed `data` fields for endpoint, estimand, policy and collection `event_handling` were not discoverable. This blocked the endpoint/estimand/dependencies objects (neuro) and the policy object (haem) | **Fixed**: `describe view protocol` now has `object_data`, `check_patterns` and `admission`. A policy object built from the published contract prepares and runs (coordinator check). Both walkers finished before seeing the fix, so a re-walk of endpoint/estimand/policy objects is owed (task 2.8 stays open) |
| 2 | `reason-revise` on a v2 session leaked "string indices must be integers" | **Fixed**: this was the nested `answer_diff.protocol` shape, now flattened. `reason-revise --session` works on v2 through the CLI and reports `verdict` |
| 3 | The bounded `--edits` shortcut refuses `/protocol/...` paths, and its schema is undocumented | **Fixed** (task 5.6): `/protocol` is an edit root; a changed object needs explicit origin, and changed content a new version. The schema is published as `revision_edits` in `describe view delivery` |
| 4 | Adoption support alone did not admit an object | **By design** (C3: own standing and support are conjunctive). It is now stated in the card's `admission` |
| 5 | Invariants are checked after every external variable is redrawn, and nothing said so | **By design** (C6, confirmed reading). Now documented in the operator inputs and the protocol card |
| 6 | The compact reply hides the protocol, and export has no protocol sheet or decision-list entry | **Open**: slice 6 (tasks 6.2–6.4) |
| 7 | A protocol-only session needed a placeholder question | **Fixed twice**. The first fix recorded its disclosed default at a path absent from the expansion, which surfaced as `missing_location:anchor.address`; the haematology re-run caught it. The default is now disclosed at `/request/session/decisions`, with regressions for both v2 and v1 |
| 8 | Predicate kinds are not discoverable from the refusal `predicate_kind_outside_vocabulary` | **Open**: a pre-existing entailment vocabulary issue, noted for the discovery owner |
| 9 | Schedule claim rows had an empty `determining_ids` | **Open** (minor): schedule rows name their deciding inputs through `support`. Whether `determining_ids` should mirror them is to be decided |

## Haematology re-run after the fix (same day)

- The policy is now expressed as a v2 protocol `policy` object, using the published `{model, bindings}` contract.
  It prepares and runs inside the protocol, with results identical to the earlier `signals` runs:
  - wrong 1 is a prohibition violation;
  - wrong 2 is termination `not_established`;
  - the fixed, adopted policy has all five claims accepted and satisfied.
- `reason-revise --session` from wrong 1 (adopted) to fixed (adopted) reports `protocol_checks: changed 1`, with
  axis `verdict`. Per-claim before/after detail is not in `answer_diff` (slice 6 delivery).
- Still open: export (defect 6), and `reason-result --part address` returning navigation for large nodes (a
  delivery readability item for slice 6).
