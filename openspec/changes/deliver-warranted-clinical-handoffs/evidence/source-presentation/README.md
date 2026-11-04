# Source presentation: a Phase 2 migraine walkthrough

The complete retained source packet is in `/Users/rohanvinaik/trialledger-runs/source-presentation-migraine-20261104/`. The receipt records its fingerprints. Raw bodies, workbooks and full source requests stay outside the repository.

The complete 131-study pool was retrieved in two pages. Seed 202611041431 was persisted before the two-study sample: NCT00781456 and NCT02959177. Both selected identifiers were gathered through `landscape`, the record was read through CLI pages, and `verify` reproduced the new reference workbook.

## Working brief

A simulated clinical-development lead is considering a Phase 2 migraine study. These random references concern different populations: episodic migraine in the Japanese galcanezumab study, and menstrually related migraine in the oral-contraceptive study. They are kept as separate references. Their presence in one pull does not establish clinical comparability or a class standard.

The operator asks whether age 60 fits. Exact NIH general-eligibility age fields for NCT02959177 compile through `source_assertions` as known source-bound lower and upper limits of 18 and 65 Years. The computed answer about age 60 is allowed but not required by those age fields. It is not an assertion that a particular person satisfies every enrollment requirement. Migraine onset before age 50 is separately retained in the narrative; it is not converted into an enrollment age cap.

The simulated new-trial draft uses an inclusive 18–50 Years restriction. It rules out age 60. Revising only the cap to 65 makes age 60 allowed but not required. Both choices are explicitly simulated; neither alleges an actual human confirmation or a source requirement for the new trial. The complete request/result pairs are beside this note. The real CLI and MCP paths produced identical results.

The primary endpoint records remain distinct: NCT02959177 describes an overall monthly migraine-headache-day change averaged over Months 1–6; NCT00781456 describes a 50% reduction in average weekly migraine episodes over a 91-day treatment period with a 25–35-day qualification baseline. No equivalence, visit schedule, unit conversion or required study length is inferred. The latter study also explicitly says its HIT-6 total could not be calculated after an administration error. That source statement stays visible; a missing valid score is not repaired by invented arithmetic.

## Decision list

- Choose the intended migraine population and whether either source is a suitable comparator. The random references alone do not settle this.
- Choose the new trial's age range. The simulated revision shows its exact effect; the comparator's 18–65 limit does not require adopting it.
- Choose the endpoint definition and observation period. The source descriptions differ and no equivalence has been accepted.
- Obtain protocol-level details behind “Others as directed/dictated by FDA-approved protocol” in NCT00781456. Registry silence is not absence.

## Presentation checks

The bounded study index preserves brief title, official title and the explicit not-stated acronym state. The baseline view retains all 88 source measurements across nine tables. Each measurement equals the value at its exact source pointer. Groups, denominator scopes, units and category/class metadata stay separate; no total or joint population is recomputed.

The historical HFrEF source-context-v2 report also verifies unchanged under its explicit writing contract, including display-1 provenance and old optional-note presentation. The new display uses blank absent optional Safety Notes while retaining actual source notes and computed denominator explanations.

These checks establish source preservation and the named computations, not clinical correctness of registry content, full protocol generation or automatic interpretation of free text.
