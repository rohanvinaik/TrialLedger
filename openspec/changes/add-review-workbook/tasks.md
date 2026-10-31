# Tasks — add-review-workbook

## 1. Verify the registry facts the design relies on

- [x] 1.1 Check each proposed edit check against the registry's published data element definitions; approve only those with a stated rule, recording the rule beside the check
- [x] 1.2 Verify live the link forms of the registry study page, PubMed references and posted documents, and record the observations
- [x] 1.3 Measure on live pulls how often eligibility text carries the standard inclusion and exclusion headings exactly once each, in order

## 2. Ledger

- [x] 2.1 Write the ledger's pure decisions (entry location, role from structure, not reported versus recorded absence, results posted or not) unwired, with direct-call intent tests for both signs
- [x] 2.2 Converge each with `detective converge --two-sign`; kill, prove or fence every survivor; then wire them into the ledger build

## 3. Edit checks

- [x] 3.1 Write each approved check as a pure decision returning consistent, conflict, not_applicable or not_checkable, with both-sign intent tests (including: a missing input is never consistent; a conflict never changes a value)
- [x] 3.2 Converge each with `--two-sign`; then wire them into the ledger build

## 4. Review workbook

- [x] 4.1 Write the eligibility split decision and its intent tests (the parts reproduce the text exactly; ambiguous text is never split); converge
- [x] 4.2 Write the cell kinds (stated, computed, needs review) and the "no results posted" rule with their intent tests; converge
- [x] 4.3 Write the link builders for the registry page, publications with their registry roles, and posted documents, with intent tests; converge
- [x] 4.4 Add the spreadsheet writer dependency to the manifest and lock; write `review.xlsx` and `record.xlsx` inside the existing staging step, with durability tests (any failure leaves no directory and no workbook)

## 5. Verify end to end

- [x] 5.1 End-to-end tests through `trialledger pull` against the scripted API, both signs
- [x] 5.2 `scripts/ci_local.sh` green, including a two-sign audit of every pinned decision (39, 2026-10-31)
- [ ] 5.3 Live pulls of studies with and without posted results; open the workbook and check it cell by cell against the registry pages
  - Done 2026-10-31: `uv run pytest -m live` passes; a live pull of 44 Phase 3 psoriasis trials (with and without
    posted results) wrote both workbooks certified cell by cell against the API record, `trialledger verify`
    certified the folder, and 14 Studies columns agree with the registry's own CSV for all 44 studies.
  - Open: the registry's web pages themselves. Their results tables are collapsed sections that the page
    does not expose until clicked, so the page spot check (NCT03875482's serious events) was not made.
- [ ] 5.4 Update the README status table and the shape section of AGENTS.md; archive the change
  - The README and AGENTS.md are updated; the change is archived once 5.3 is complete.
