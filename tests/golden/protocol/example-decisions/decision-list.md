# Clinical design decision list

Session: invented-session
Revision: one

Questions and option labels are caller wording, not computed assertions. Only the represented restrictions are checked. Caller origin labels are not authenticated confirmation.

## Which represented ages fit?

Question above is caller wording.
Current computed result: Settled within the declared alternatives (settled_within_declared_alternatives).
No option has been selected by the caller yet.

Comparator evidence and context:
No comparator context linked to this decision; source absence is not asserted.

### Caller-labelled option: Age 17

Represented profile: participant: "age" = 17.0 years
Actual analysis context: arm: Not stated
cohort: Not stated
phase: Not stated
Computed answer: Ruled out by the represented criteria (REFUTED)
Feasibility: Ruled out under the represented restrictions (infeasible). Standing: known.
Deciding criteria:
age: Requires participant: "age" ≥ 18.0 years [standing: known; Caller-declared clinical choice: invented:brief]
Remaining requirements:
No additional proved requirement displayed; this is not complete screening.
Open items: No blocker reported
Exact result: `artifacts/4b2b3872fe1e96326a5e5f363fd1da9fbccd616ee55c42be6b09d64bfb765ddb.json#/response/result/decisions/0/alternatives/0`

### Caller-labelled option: Age 18

Represented profile: participant: "age" = 18.0 years
Actual analysis context: arm: Not stated
cohort: Not stated
phase: Not stated
Computed answer: The represented proposition is allowed but not required under these restrictions (UNDETERMINED)
Feasibility: Compatible with the represented restrictions (feasible). Standing: known.
Deciding criteria:
age: Requires participant: "age" ≥ 18.0 years [standing: known; Caller-declared clinical choice: invented:brief]
Remaining requirements:
No additional proved requirement displayed; this is not complete screening.
Open items: This exact query is allowed but not required; its negation also fits (undecided_by_constraints)
Exact result: `artifacts/4b2b3872fe1e96326a5e5f363fd1da9fbccd616ee55c42be6b09d64bfb765ddb.json#/response/result/decisions/0/alternatives/1`

Origin: Computed from declared premises: invented:brief
Coverage: Only caller-declared represented constructs; not complete clinical eligibility.
Exact result: `artifacts/4b2b3872fe1e96326a5e5f363fd1da9fbccd616ee55c42be6b09d64bfb765ddb.json#/response/result/decisions/0`

## Protocol

### Sections

| Section | Declared | Coverage | Findings |
|---|---|---|---|
| population | not_requested | not_requested | No checks: section not requested. |
| eligibility | not_requested | not_requested | No checks: section not requested. |
| interventions | not_requested | not_requested | No checks: section not requested. |
| endpoints | not_requested | not_requested | No checks: section not requested. |
| assessments | requested | specified | A repair choice is open in the declared checks. |
| efficacy | not_requested | not_requested | No checks: section not requested. |
| safety | not_requested | not_requested | No checks: section not requested. |
| exploratory | not_requested | not_requested | No checks: section not requested. |

Coverage legend: specified = the section's declared checks ran and nothing is open (not a clinical completeness claim); open = something is unapplied, undetermined or missing; not_computed = a check could not be computed; not_requested or not_applicable = the section is not declared or declared not applicable.

### Findings

Counts: conflict 0; repair choice 2; not computed 0; not applied 0; not determined 0; definition relations refuted by a counterexample 0. Kinds: Conflict = an admitted policy failure; Repair choice = an admitted gap you choose how to repair; Not computed = no finding because an input, scope or method is missing; Not applied = the deciding premise is still a proposal or unsupported; Not determined = a declared input is missing.

Check week12-schedule (schedule, required) — rests on standing known
- [Repair choice] nominal: The nominal target is inside the permitted window but outside planned collection. — standing known; result artifacts/4b2b3872fe1e96326a5e5f363fd1da9fbccd616ee55c42be6b09d64bfb765ddb.json#/response/result/protocol/checks/0/children/0/result
- [Repair choice] full_window: Planned collection does not cover part of the permitted window: (80, 91]. — standing known; result artifacts/4b2b3872fe1e96326a5e5f363fd1da9fbccd616ee55c42be6b09d64bfb765ddb.json#/response/result/protocol/checks/0/children/0/result
- [No finding] existence: At least one permitted assessment time falls within planned collection. — standing known; result artifacts/4b2b3872fe1e96326a5e5f363fd1da9fbccd616ee55c42be6b09d64bfb765ddb.json#/response/result/protocol/checks/0/children/0/result

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| week12-schedule | not stated (open) | not stated (open) | not stated (open) | unconditional | score | observed | randomization | day | 84 days from randomization | [77, 91] days from randomization | (-∞, 80] days from randomization | [77, 80] days from randomization | (80, 91] days from randomization | Target 84 days from randomization is inside the permitted window but outside planned collection (not_collected) |

### Plan comparisons

How long should invented week-12 collection run? (caller wording)

Disposition: repair_choice (A repair choice is open: the option you selected, or every declared option, leaves a gap to repair)

| Alternative | Label | Frame | Compatibility | Conditional checks | Application |
|---|---|---|---|---|---|
| as-drafted | Through day 80 (caller wording) | fixed | repair_choice_open_under_declared_checks (A repair choice is open under the declared checks) | none | withheld |
| extend | Through day 91 (caller wording) | hypothetical | compatible_under_declared_checks (No conflict or repair choice found under the declared checks) | none | withheld |

- as-drafted: Not applied as a settled design: the draft as written has no clean result (a repair choice is open under the declared checks). Selected (caller-attributed, not authenticated) (origin user: user:invented selection (teaching example)). Permitted window: [77, 91] days from randomization; collection availability: (-∞, 80] days from randomization; feasible window: [77, 80] days from randomization; full-coverage gap: (80, 91] days from randomization. Claim outcomes: week12-schedule/visit holds under the declared inputs (satisfied) [known]; week12-schedule/target the nominal target is outside planned collection (not_collected) [known]; week12-schedule/window planned collection leaves part of the permitted window uncovered (uncovered) [known]. Checks deciding it: required check week12-schedule: repair_choice (claim visit: holds under the declared inputs (satisfied); claim target: the nominal target is outside planned collection (not_collected); claim window: planned collection leaves part of the permitted window uncovered (uncovered)).
- extend: Not applied to the draft: a hypothetical alternative that assumes these objects are replaced: collection. Not selected. Permitted window: [77, 91] days from randomization; collection availability: (-∞, 91] days from randomization; feasible window: [77, 91] days from randomization; full-coverage gap: none. Claim outcomes: week12-schedule/visit holds under the declared inputs (satisfied) [proposed]; week12-schedule/target holds under the declared inputs (satisfied) [proposed]; week12-schedule/window holds under the declared inputs (satisfied) [proposed]. Checks deciding it: required check week12-schedule: satisfied (claim visit: holds under the declared inputs (satisfied); claim target: holds under the declared inputs (satisfied); claim window: holds under the declared inputs (satisfied)).


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| score | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold); its definition reference is proposed | adopt:score:invented-v1 | user_choice: user:invented adoption (teaching example) | known | proposed |
| week12 | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:week12:invented-v1 | user_choice: user:invented adoption (teaching example) | known | n/a |
| collection | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:collection:invented-v1 | user_choice: user:invented adoption (teaching example) | known | n/a |

### Open items

1. The nominal target is inside the permitted window but outside planned collection. (/protocol/checks/0/children/0/result)
2. Planned collection does not cover part of the permitted window: (80, 91]. (/protocol/checks/0/children/0/result)

### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.
