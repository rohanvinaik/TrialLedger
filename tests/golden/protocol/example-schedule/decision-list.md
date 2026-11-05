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
Exact result: `artifacts/bba2e7bbf8af07e6bb99842b6b5f4d17609be16f26a2342ec69926c3d1a32448.json#/response/result/decisions/0/alternatives/0`

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
Exact result: `artifacts/bba2e7bbf8af07e6bb99842b6b5f4d17609be16f26a2342ec69926c3d1a32448.json#/response/result/decisions/0/alternatives/1`

Origin: Computed from declared premises: invented:brief
Coverage: Only caller-declared represented constructs; not complete clinical eligibility.
Exact result: `artifacts/bba2e7bbf8af07e6bb99842b6b5f4d17609be16f26a2342ec69926c3d1a32448.json#/response/result/decisions/0`

## Protocol

### Sections

| Section | Declared | Coverage | Findings |
|---|---|---|---|
| population | not_requested | not_requested | No checks: section not requested. |
| eligibility | not_requested | not_requested | No checks: section not requested. |
| interventions | not_requested | not_requested | No checks: section not requested. |
| endpoints | not_requested | not_requested | No checks: section not requested. |
| assessments | requested | open | Not fully checked (see coverage). |
| efficacy | not_requested | not_requested | No checks: section not requested. |
| safety | not_requested | not_requested | No checks: section not requested. |
| exploratory | not_requested | not_requested | No checks: section not requested. |

Coverage legend: specified = the section's declared checks ran and nothing is open (not a clinical completeness claim); open = something is unapplied, undetermined or missing; not_computed = a check could not be computed; not_requested or not_applicable = the section is not declared or declared not applicable.

### Findings

Counts: conflict 0; repair choice 0; not computed 0; not applied 3; not determined 0; definition relations refuted by a counterexample 0. Kinds: Conflict = an admitted policy failure; Repair choice = an admitted gap you choose how to repair; Not computed = no finding because an input, scope or method is missing; Not applied = the deciding premise is still a proposal or unsupported; Not determined = a declared input is missing.

Check week12-schedule (schedule, required) — rests on standing proposed, unresolved (object:week12, adoption:week12, object:collection, adoption:collection)
- [Not applied] existence: Not applied: the deciding premise is still a proposal. — standing proposed; result artifacts/bba2e7bbf8af07e6bb99842b6b5f4d17609be16f26a2342ec69926c3d1a32448.json#/response/result/protocol/checks/0/children/0/result
- [Not applied] nominal: Not applied: the deciding premise is still a proposal. — standing proposed; result artifacts/bba2e7bbf8af07e6bb99842b6b5f4d17609be16f26a2342ec69926c3d1a32448.json#/response/result/protocol/checks/0/children/0/result
- [Not applied] full_window: Not applied: the deciding premise is still a proposal. — standing proposed; result artifacts/bba2e7bbf8af07e6bb99842b6b5f4d17609be16f26a2342ec69926c3d1a32448.json#/response/result/protocol/checks/0/children/0/result

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| week12-schedule | not stated (open) | not stated (open) | not stated (open) | unconditional | score | observed | randomization | day | 84 days from randomization | [77, 91] days from randomization | (-∞, 80] days from randomization | [77, 80] days from randomization | (80, 91] days from randomization | Target 84 days from randomization has no applied finding (its deciding premise is a proposal or an input is missing) (unresolved) |

### Plan comparisons

No plan comparison declared.


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| score | invented-v1 | not_adopted | No adoption record: nothing was declared as adopting this object; its definition reference is proposed | none | none | proposed | proposed |
| week12 | invented-v1 | not_adopted | No adoption record: nothing was declared as adopting this object | none | none | proposed | n/a |
| collection | invented-v1 | not_adopted | No adoption record: nothing was declared as adopting this object | none | none | proposed | n/a |

### Open items

1. Check week12-schedule, claim visit: Not applied: the deciding premise is still a proposal. (/protocol/checks/0/children/0/result)
2. Check week12-schedule, claim target: Not applied: the deciding premise is still a proposal. (/protocol/checks/0/children/0/result)
3. Check week12-schedule, claim window: Not applied: the deciding premise is still a proposal. (/protocol/checks/0/children/0/result)
4. Section assessments is open. (/protocol/sections/assessments)

### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.
