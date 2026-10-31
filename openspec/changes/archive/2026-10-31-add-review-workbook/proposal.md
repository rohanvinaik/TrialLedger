# Add the review workbook

## Why

The registry's own spreadsheet omits what study design needs most: eligibility criteria and safety
results. The colleague's ten questions need a view built from the complete record, in which every value
is traceable to its field, every internal inconsistency is queried, and nothing is filled in. This is the
first projection of the design in `docs/THEORY_OF_THE_CASE.md` (Part III, steps 1–3 and 5): the ledger,
the edit checks and the review workbook, over the registry's structured fields only.

## What Changes

- Enter every element of each pulled record in a ledger: its value as written, its location in the record
  and its role (inclusion or exclusion, outcome type, arm). Nothing is removed; an empty field stays
  distinct from a recorded "none".
- Run approved edit checks among the registry's unambiguous fields on every record, each reported as
  consistent, conflict, not applicable or not checkable. Conflicts are shown as queries and never corrected.
- Write a review workbook beside `studies.json` and `studies.csv`, organised around the ten questions:
  population, eligibility (split by the registry's standard headings only when they are unambiguous),
  outcomes and time frames, other pre-specified outcomes, adverse events per arm, and an explicit
  "no results posted" where the registry has none. Every value is labelled stated, computed or needs review.
  Beside it, a record workbook presents every value of every study in the registry's own categories.
- Link every study to its registry page, every linked publication with the role the registry assigns it,
  and every document the sponsor posted.
- Give every value a warrant committing to its basis, record the pull's roots in its provenance, certify the
  workbook against the record before the pull is written, and add `trialledger verify`, which re-derives a
  written folder (the founder's addition, 2026-10-31, paraphrased: each piece of information should be able to
  carry a strict warrant of the basis on which it entered the record).
- Keep the all-or-nothing guarantee: the workbook is written with the other two files or not at all.
- Out of scope: reading publications (the next change, `add-publication-evidence`), computations across
  trials (`add-cross-trial-views`), and an interface that needs no terminal.

## Capabilities

### New Capabilities

- `trial-ledger`: every element of a pulled record as located, scoped evidence, from which all views derive.
- `record-edit-checks`: approved consistency relations among a record's structured fields, with named outcomes.
- `review-workbook`: the per-study projection of the ledger answering the ten design questions, with links
  to every source a reviewer would read.

### Modified Capabilities

None. No OpenSpec specifications existed before this change; the ingestion layer is described by the
README and its tests.

## Impact

New modules beside `TrialLedger/ingest.py` for the registry's names, the ledger, the checks, the cells, the
links, the warrants and the workbook; `record.py` writes the workbook inside the existing staging directory
and verifies a written folder; `cli.py` reports the workbook and adds `verify`. One new runtime dependency,
openpyxl, decided in `design.md`. Every decision is built as a pure function with two-sign intent tests and
converged with Detective.
