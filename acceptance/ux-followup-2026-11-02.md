# Clinical reference-sheet usability follow-up — 2026-11-02

This is a bounded update to search recovery, workbook presentation and assistant operation. The clinical
study records in both retained acceptance runs are unchanged. Layer-two reasoning and the unfinished full
trial writer retain their existing boundary.

## Delivered behavior

- A class-name miss can offer canonical choices from the requested source's RxClass catalogue. Every
  suggestion, including a sole candidate, remains unresolved until explicitly selected. An empty or failed
  catalogue is not evidence of no matching class. The existing explicit class-ID route remains available.
- CLI and MCP preview show the choices and recovery instructions before retrieval. Relay carries the search
  terminology requests and preserves complete response bodies; it still skips gathered-study enrichment.
- Safety uses separate source count/group rows, with the source group title beside affected participants,
  participants at risk and event count. Duplicate and orphan count records remain individually addressable;
  missing counts remain missing. Groups are never joined across studies or results modules by title.
- Record-address columns are hidden by default with reveal guidance. Posted outcomes have section borders
  based on exact study/outcome identity. Visible text determines row height; hidden pointers do not.
- Connection checks distinguish successful HTTP responses, blocked access, throttling, service failures and
  unexpected statuses, with per-host recovery advice. Gathering still validates response bodies.
- README and assistant instructions explain the clinical deliverable first, a capability-checked setup
  route, the exact relay requirements and useful present-day design reasoning with confirmed premises.

## Verification

The standard gate passed 3,503 tests, with ten opt-in live tests deselected; Ruff, formatting and package
typing passed. The final push gate checks the submitted tree again. All four OpenSpec items passed strict
validation. Live NLM previews independently demonstrated the abbreviated EGFR phrase offering ATC L01EB
without selection, then the explicit ID resolving seven listed member drugs.

Both retained report sets were regenerated through the public CLI without network requests:
`three-trials` and `mixed-study-types` (interventional, observational and expanded access). Independent
source-to-record-to-cell checking returned zero findings for each. The clinical `studies` objects match the
previous records exactly. Cache, JSON and workbook remain byte-identical on repetition; both reports replay
successfully. The changed Safety and Posted results views were rendered and visually inspected. Native
Excel was not exercised. These examples accompany generic structural and adversarial tests; trial IDs and
clinical phrase lists do not select reporting behavior.

Focused negative checks include sole-candidate non-selection, catalogue failures, exact relay preservation,
wrong local groups, absent versus zero counts, duplicate/orphan count records, fabricated extra rows and
missing count/group rows. The independent checker and reviewer tasks consume the new source row grain.

## Detective scope and explicit waiver

`doctor.http_probe_status` completed the two-sign operator-universe pin: 96/96 killed, reproducibility
confirmed. `request.class_candidate_selection` completed its two-sign pin modulo seven unproven-equivalent
survivors and nine crash-only value gaps: 143/146 killed. No equivalence flags were used to erase those limits.

The remaining workbook pins were waived at the user's explicit direction. The preliminary `safety_rows`
diagnosis was interrupted after its 31-test baseline (exit 130), without a verdict or generated tests;
`linked_groups` was not started. Their completion is not claimed;
the project-wide deep gate was also explicitly waived. Ordinary, independent preservation, replay and visual
checks are separate evidence and are not presented as mutation certification.

Local receipts: `/tmp/trialledger-ux-final-standard.log`, `/tmp/class-recovery-final2-converge.log`,
`/tmp/trialledger-ux-doctor-converge-two-sign.log` and `/tmp/trialledger-ux-frozen-qa.log`.
The retained QA outputs are under `/var/folders/y3/9hy3l65d7xvdl89kh19dnlf40000gp/T/trialledger-ux-final-szqzek2t/`.
These are pre-commit validation artifacts and keep their actual writing stamps.
