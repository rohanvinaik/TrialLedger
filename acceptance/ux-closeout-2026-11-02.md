# Clinical MVP UX closeout — 2026-11-02

This pass improves the existing assistant-operated reference-sheet and symbolic-analysis workflows. It
changes no reporting projection, workbook writer, clinical solver or source-binding rule. The complete
automated trial writer remains designed and partly built; its working operations remain available.

## Delivered behavior

- README leads with the clinical request, workbook/record and concrete explorations. Local installation and
  MCP configuration are in an expandable technical section. The assistant checks execution, report storage,
  connectivity and file delivery before promising the artifact.
- Assistant instructions put the clinical answer, deciding basis and material open items first. They use
  natural provenance wording, group material premises for confirmation, reuse unchanged agreements and
  handle internal paging/retries. Confirmation accepts a premise without making it a registry fact.
- `reason` discovery defaults to an overview. Views entailment, coordinates and corpus provide the relevant
  formats, vocabulary, result meanings and runnable example. Views worked_session and full preserve the
  demonstration and complete manual. Serialized JSON measured 3,808 bytes for the overview versus
  75,876 for the full guide during this pass; these are measured response sizes, not token estimates.
- Worked ECOG 0–1 premises now encode both inclusive bounds. Tests check -1, 0, 1 and 2, alternatives,
  contradictions, unconfirmed readings, scope and revision. A one-restriction answer does not certify
  complete patient eligibility.
- `record` retains its 50-entry limit and adds an evidence JSON budget (default 24,576; configurable
  2,048–65,536 bytes, with small tool/run metadata overhead). Large containers return an explicit exact-address
  directory; long text returns character offsets and lossless continuation. Navigation and chunks are
  separate from complete source values. A missing ID cannot dump a large study index into its error.
- The independent reviewer client follows directories and text continuations. Saved records, requested scope,
  retrieval completion and computed conclusions are unchanged by display limits. These controls bound
  conversational output, not whole-process memory or the size of every reasoning/scope response. Complete
  analyses can be retained separately through the existing file-based workflow.

## Checks performed

The ordinary local gate passed: **3,566 tests, ten opt-in live tests deselected**, Ruff, formatting and
package typing. The gate log names its exact tree; pre-push checks cover the final submitted tree again.
All four OpenSpec items passed strict validation. A wider advisory typing check of acceptance/reviewer.py
reported ten diagnostics in unchanged functions; none was in the new continuation client. They are not a
package-type-check pass or a new clinical-validation finding.

A fresh live CLI run previewed and gathered NCT00322452 and NCT01774721, finding both requested IDs and
writing the workbook and matching JSON. Replay succeeded. Repeating the completed run with network
transports forbidden left all twelve retained files byte-identical.

Independent source → record → workbook checking returned zero findings for that fresh run and both retained
report sets (three-trials and mixed-study-types). All five current reviewer tasks, including asking MCP
about listing addresses, returned zero findings for each set. The retained mixed set includes interventional,
observational and expanded-access structures. Generic and adversarial tests cover identity/order/cardinality,
missing/empty/zero/false, malformed requests, long escaped/multi-byte text and byte-limited continuation;
trial IDs and clinical word lists do not select extraction behavior.

The fresh Python 3.12 installation/first-use check passed all nineteen steps: package installation, public
help, doctor, typed reasoning, archival pull/replay, reference-report retrieval/replay, workbook inspection
and isolated tool installation. The installed CLI and a fresh MCP process also discovered and ran examples
for all three reasoning operations; MCP read the fresh report's study index. After the final interface edits,
the package was reinstalled and all 49 Python source files matched the checkout byte-for-byte; installed
overview and large missing-ID recovery checks passed.

This pass did not change workbook rendering. The preceding visual review is recorded in
[the usability follow-up](ux-followup-2026-11-02.md). Native Excel and a hosted chat application's UI were not
exercised here. The installed protocol walk is not a claim of independent clinician usability testing or a
complete automated protocol generator. Class recovery, relay and interrupted retrieval retain their ordinary
entry-point tests; the live runs here used identifiers and direct mode, not a new broad landscape campaign.

## Detective receipts and limits

The local Detective/Wesker checkouts were verified before invocation.

- `record_access.bounded_view`: two-sign converge reported **COMPLETE**, 274/289 killed, modulo fifteen
  unproven-equivalent survivors and forty-one crash-only value gaps. Reproducibility was confirmed. No
  equivalence flags were used to erase those limits.
- `record_access.text_window`: every executable line was covered, but converge reported **UNGATEABLE**:
  nine mutations reached no verdict under the execution budgets. Its diagnostic counts are not a completed
  certificate. Ordinary intent tests check boundaries, progress and exact reconstruction, including escaped
  Unicode. The generated tests and ungateable certificate standing are retained.

The project-wide deep gate remains waived under the existing instruction. No additional refactoring or
clinical interpretation campaign was added as a reporting prerequisite.

## Local receipts

- `/tmp/trialledger-ux-closeout-standard.log` and the final commit/push gate logs.
- `/tmp/trialledger-ux-closeout-review.json` and `/tmp/trialledger-ux-closeout-repeat.json`.
- `/tmp/trialledger-ux-closeout-installed-current.json`.
- Fresh live outputs: `/tmp/trialledger-ux-closeout-20261102/`.
- Fresh installation report: `/private/var/folders/y3/9hy3l65d7xvdl89kh19dnlf40000gp/T/trialledger-release-hkz5f2nq/REPORT.md`.
- Installed front-door examples and responses: `/var/folders/y3/9hy3l65d7xvdl89kh19dnlf40000gp/T/trialledger-ux-front-door-t5_qcpmd/`.
- Detective full reports: `.detective/reports/converge_bounded_view.txt` and `converge_text_window.txt`.

These temporary paths describe the actual local receipts; they are not repository artifacts or permanent
remote downloads. Retained reports keep their real pre-commit writing stamps.
