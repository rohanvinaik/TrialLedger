# Historical freezes and current closure status (task 7.4)

The hashes below are historical writing bases, not certification of the current tree. The acquisition
and provenance closure after `db762ba` supersedes them for changed targets. See
[the current closure receipt](closure-20261105.md) for traced ownership, tests and target-specific proof
status. No whole-project proof completion is claimed by this pass.

- Commit: `a1c8d54b3cd9c25d5a4ae9e6c31c13d1dbdccf2e` (2026-11-04), tree `c89832836949a87bce5e512c3bc5d58e10b87755`.
- Rule: after this line there are no code edits except fixes forced by a proof finding (a CrossHair counterexample or Detective gap). Each such fix re-freezes and re-pins only the affected targets, recorded below.
- Production files changed by this change since its baseline 25c6bb5, with sha256 at the freeze:

```text
1124b2021fcd0fb4  TrialLedger/analysis_review.py
0c142b8a56cc53db  TrialLedger/capabilities.py
48d7a3d110051a4d  TrialLedger/clinical_delivery.py
7b16e21b0234ed9a  TrialLedger/clinical_export.py
f3ec0b4c7f0c30c0  TrialLedger/layer2/definition_checks.py
e222e3a9e17b704c  TrialLedger/layer2/design_session.py
f7a2e14130df7a66  TrialLedger/layer2/protocol_decisions.py
6cadefa997401ccc  TrialLedger/layer2/protocol_numbers.py
7d3fddc5104bc2bc  TrialLedger/layer2/protocol_objects.py
f7bf0100b81a6afc  TrialLedger/layer2/protocol_policies.py
cc3391b0893acb2a  TrialLedger/layer2/protocol_projections.py
cefec1971d36b073  TrialLedger/layer2/protocol_schedule.py
798bedc0b6b2a878  TrialLedger/layer2/protocol_statistics.py
1474103809174914  TrialLedger/layer2/protocol_view.py
618ae2b10ac20821  TrialLedger/layer2/request_preparation.py
961abb6ac9e0f784  TrialLedger/layer2/result_semantics.py
ac2592c175fa0c6d  TrialLedger/layer2/service.py
af3f01da2540c7e0  TrialLedger/layer2/session_projections.py
59c38727e9a24605  TrialLedger/layer2/session_state.py
355ad89ee9d44bef  TrialLedger/layer2/signals_guide.py
ca89d32d23c33548  TrialLedger/layer2/signals.py
d5c428095de594f2  TrialLedger/reasoning_artifacts.py
289a67c30fd36a2c  TrialLedger/reasoning_cards.py
fe228b89dbbb0cf3  TrialLedger/reasoning_cli.py
523e02ad25f695c3  TrialLedger/reasoning_delivery.py
c8c790ec7c322c52  TrialLedger/reasoning_mcp.py
```

## Re-freezes

- **Trace audit (2026-11-05).** Five post-freeze findings forced code changes, in `design_session`,
  `protocol_statistics`, `result_semantics`, `protocol_view`, `clinical_export` and `request_preparation`:
  - added and withdrawn rows carry `code`;
  - designs too wide to render return `limit`;
  - protocol causes are classified;
  - unresolved checks count in the headline;
  - open items are worded.
  They were committed after the gate passed (8,189 tests). The new freeze is that commit.

## Proof phase status (honest)

- The serialized proof run (CrossHair, Detective audit of every pinned decision, full `--deep` gate) was started
  at a1c8d54 and stopped at the user's request after about an hour. It is too slow to finish in-session: it
  audits 253 pinned decisions one at a time.
- Its partial converges could not be certified (the last was cut off mid-run), so they were discarded. The
  committed Detective evidence stands as it was: wave-1 pins, `results_reading` (complete, modulo 3
  unproven-equivalent and 1 crash-only), and `edition_change_state` (complete, 26/26).
- Not run in this change: the full `scripts/ci_local.sh --deep` gate, and CrossHair `--report_all` on the
  contracts added since wave 1. Tasks 2.7, 3.6, 4.5, 5.7 (pin part), 6.7 (pin part) and 7.4 stay open until they
  run, or until Rohan accepts this limitation explicitly.


## Composition and engineering pass (2026-11-05), before the next freeze

Done in this pass:
- **Steps 1–2.**
  - Conditions, standing, adoption and scope follow the linked-objects closure (Rohan).
  - Plain-signal applicability; simultaneous admission causes are named.
  - Every check carries a support axis on standing changes.
  - The headline never settles a conditionally applied result.
- **Step 3.**
  - One owner for outcome sets (`protocol_outcomes`).
  - Seven long functions split, with behaviour held byte-identical by golden outputs (`tests/golden/protocol/`).
  - F7 unused fields are consumed.
  - ty: 45 → 0 diagnostics in the protocol files.
- **Step 4.**
  - `tests/test_protocol_composition_matrix.py`, generated from the contract edge matrix.
  - `tests/test_protocol_metamorphic.py`: unrelated additions, renaming, reordering and duplicate adoption change
    nothing.
- **Acquisition coverage** (`coverage.py`, `coverage_run.py`).
  - Explicit MeSH-class vs condition-text comparison over complete ID sets, under the acquisition budget.
  - Plain coverage statements in the preview, report and workbook.
  - Union offered only as an explicit request; explicit drug additions marked as the person's.
  - Verified: EGFR/NSCLC 53 class vs 70 text (17 text-only, including FLAURA and AURA3; 14 lacking condition
    MeSH); T2D/SGLT2 8 vs 12.
- **Repairable refusals** (`layer2/refusal.py`).
  - `input_diagnostics` with pointer, rejected value, permitted vocabulary and discovery reference.
  - Identical on CLI and MCP, and kept in compact replies.
  - Protocol check-input refusals point at the check.

Open (listed, not fixed):
- Refusals raised in `design_session` / `session_state` (e.g. `alternative_requires_exact_entailment_query`), and
  errors raised before `run` in the CLI/MCP wrappers, still return only a code.
- Source-origin display was subsequently closed: actual check inputs and linked gating inputs, plus each
  alternative's own origins, reach compact replies, the decision list and workbook as caller attribution.
- Dependencies are not linked to a baseline's own collection plan (a contract decision for Rohan).

## Historical second freeze (2026-11-05)

- Commit `284ed95c82387848009add2fb7d41ec2b9b95973`. A targeted verification driver was started for pinned
  decisions and contracted functions; target list in `~/trialledger-runs/proof-targeted/targets.txt`.
  Its shell driver did not follow Detective's printed actions and is not accepted as final certification.
  The files are preserved as historical run material. Current code, imports and authored tests need their
  own evidence; the earlier proof tasks remain open.
