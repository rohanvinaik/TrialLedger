# Tasks — add-coherence-engine

## 0. Carried forward

- [ ] 0.1 Spot-check one study's results on its live registry page against `review.xlsx` (carried from add-review-workbook 5.3; the page's results tables are collapsed sections) and record the observation in this file

## 1. Itemize eligibility

- [ ] 1.1 Write the itemization decision (sections, criteria, spans, reasons) unwired with authored intent tests for both signs from real NSCLC criteria; verify the pieces reproduce the text for every record of the 487-study population; converge once with `--two-sign`
- [ ] 1.2 Wire it into a `profile` shell and extend `tests/production_path.py`; verify `tests/test_wiring.py` passes

## 2. Type criteria

- [ ] 2.1 Write the banks (setting and stage, prior therapy, biomarker, performance status, organ function, CNS metastases, named conditions, boilerplate), each a pure decision with authored two-sign intent tests from real criteria; converge each once; verify with the residual count on the population
- [ ] 2.2 Write the endpoint-class bank over outcome measure titles with intent tests; converge once

## 3. Classify interventions

- [ ] 3.1 Write the RxClass response decision (classes, or a named failure) with intent tests; converge once
- [ ] 3.2 Write the lookup shell over names and other names through the throttled session, caching `classes.json`; durability test (a failed lookup is named, never "no class"); verify a live lookup of the population
- [ ] 3.3 Write the record-stated target bank over intervention and arm descriptions; converge once

## 4. Coherence

- [ ] 4.1 Write coordinates, domains and evidence narrowing with intent tests (silence never narrows; agreement never assigns)
- [ ] 4.2 Write the relation table (all proposed) and the closure decision with intent tests (fixed point; order-independence by permutation; conflict names every cause); converge once

## 5. Profile

- [ ] 5.1 Write frequencies with explicit denominators, surprisal, sponsor support and the standard tier, with intent tests; converge once
- [ ] 5.2 Write mechanism signals (2×2 counts, difference, sponsors, unresolved count, proposal thresholds) with intent tests; converge once
- [ ] 5.3 Write occupancy (occupied / unknown / empty) and comparable-results grouping with intent tests; converge once

## 6. Output and command

- [ ] 6.1 Write `design.xlsx` (sheets per design Decision 12, every row warranted, `cells.py` exactness) and `trialledger profile <folder>` (refuses a record that does not verify; leaves the pull's files unchanged); end-to-end tests through the CLI, both signs
- [ ] 6.2 Run `scripts/ci_local.sh` whole and read its whole output; green

## 7. Live

- [ ] 7.1 Run `trialledger profile` on the NSCLC population; record residual size per bank, class coverage, resolved share per coordinate and the top standard and distinctive elements in this file
- [ ] 7.2 Update README (status, `profile`) and AGENTS.md (shape, open items)

## Workflow follow-up

- Founder approvals, collected: each proposed relation by id; the standard share and signal thresholds; a
  method for code-named agents beyond other names and record-stated targets; the Audit sheet's review.
- Archive once the founder has reviewed the Audit sheet and approved or rejected the relations.
