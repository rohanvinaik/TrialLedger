# Tasks — add-review-workbook

## 1. Verify the registry facts the design relies on

- [ ] 1.1 Check each proposed edit check against the registry's published data element definitions; approve only those with a stated rule, recording the rule beside the check
- [ ] 1.2 Verify live the link forms of the registry study page, PubMed references and posted documents, and record the observations
- [ ] 1.3 Measure on live pulls how often eligibility text carries the standard inclusion and exclusion headings exactly once each, in order

## 2. Ledger

- [ ] 2.1 Write the ledger's pure decisions (entry location, role from structure, not reported versus recorded absence, results posted or not) unwired, with direct-call intent tests for both signs
- [ ] 2.2 Converge each with `detective converge --two-sign`; kill, prove or fence every survivor; then wire them into the ledger build

## 3. Edit checks

- [ ] 3.1 Write each approved check as a pure decision returning consistent, conflict or not_checkable, with both-sign intent tests (including: a missing input is never consistent; a conflict never changes a value)
- [ ] 3.2 Converge each with `--two-sign`; then wire them into the ledger build

## 4. Review workbook

- [ ] 4.1 Write the eligibility split decision and its intent tests (the parts reproduce the text exactly; ambiguous text is never split); converge
- [ ] 4.2 Write the cell kinds (stated, computed, needs review) and the "no results posted" rule with their intent tests; converge
- [ ] 4.3 Write the link builders for the registry page, publications with their registry roles, and posted documents, with intent tests; converge
- [ ] 4.4 Add the spreadsheet writer dependency to the manifest and lock; write `review.xlsx` inside the existing staging step, with durability tests (any failure leaves no directory and no workbook)

## 5. Verify end to end

- [ ] 5.1 End-to-end tests through `trialledger pull` against the scripted API, both signs
- [ ] 5.2 `scripts/ci_local.sh` green, including a two-sign audit of every pinned decision
- [ ] 5.3 Live pulls of studies with and without posted results; open the workbook and check it cell by cell against the registry pages
- [ ] 5.4 Update the README status table and the shape section of AGENTS.md; archive the change
