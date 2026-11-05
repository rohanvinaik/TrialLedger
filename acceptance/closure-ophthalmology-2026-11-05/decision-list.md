# Clinical design decision list

Session: simulated-retinal-loading-maintenance
Revision: scoped-repair

Questions and option labels are caller wording, not computed assertions. Only the represented restrictions are checked. Caller origin labels are not authenticated confirmation.

## Under the simulated age restriction, does age 49 fit initial entry? Maintenance response is a later question.

Question above is caller wording.
Current computed result: Settled within the declared alternatives (settled_within_declared_alternatives).
No option has been selected by the caller yet.

Comparator evidence and context:
No comparator context linked to this decision; source absence is not asserted.

### Caller-labelled option: Age 49 at entry

Represented profile: participant: "age" = 49.0 years
Actual analysis context: arm: all
cohort: initial-randomized
phase: loading
Computed answer: Ruled out by the represented criteria (REFUTED)
Feasibility: Ruled out under the represented restrictions (infeasible). Standing: known.
Deciding criteria:
entry-age: Requires participant: "age" ≥ 50.0 years [standing: known; Caller-declared clinical choice: simulated:sponsor-loading-maintenance-v1 (no clinician confirmation)]
Remaining requirements:
No additional proved requirement displayed; this is not complete screening.
Open items: No blocker reported
Exact result: `artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/decisions/0/alternatives/0`

### Caller-labelled option: Age 50 at entry

Represented profile: participant: "age" = 50.0 years
Actual analysis context: arm: all
cohort: initial-randomized
phase: loading
Computed answer: The represented proposition is allowed but not required under these restrictions (UNDETERMINED)
Feasibility: Compatible with the represented restrictions (feasible). Standing: known.
Deciding criteria:
entry-age: Requires participant: "age" ≥ 50.0 years [standing: known; Caller-declared clinical choice: simulated:sponsor-loading-maintenance-v1 (no clinician confirmation)]
Remaining requirements:
No additional proved requirement displayed; this is not complete screening.
Open items: This exact query is allowed but not required; its negation also fits (undecided_by_constraints)
Exact result: `artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/decisions/0/alternatives/1`

Origin: Computed from declared premises: simulated:sponsor-loading-maintenance-v1 (no clinician confirmation)
Coverage: Only caller-declared represented constructs; not complete clinical eligibility.
Exact result: `artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/decisions/0`

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

Check vision-schedule (schedule, required) — rests on standing proposed, unresolved (object:maintenance-vision, adoption:maintenance-vision)
Source readings among this check's inputs (caller-attributed): maintenance-vision: reading of scd411 at ctg:NCT04480463:73735d3fdb493af481e973d2c3676eb97e7592b2339b7b369b7083fb03218714#/protocolSection/outcomesModule/primaryOutcomes/0/timeFrame (caller-attributed)
Declared conditions (caller-declared): maintenance-vision: participant: "loading_response_confirmed" (exact conditions: artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/response/result/protocol/checks/2)
- [Not applied] existence: If the declared condition applies: Not applied: the deciding premise is still a proposal. — standing proposed; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/2/children/0/result
- [Not applied] nominal: If the declared condition applies: Not applied: the deciding premise is still a proposal. — standing proposed; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/2/children/0/result
- [Not applied] full_window: If the declared condition applies: Not applied: the deciding premise is still a proposal. — standing proposed; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/2/children/0/result

Check maintenance-schedule (schedule, required) — rests on standing known
Declared conditions (caller-declared): maintenance-oct: participant: "loading_response_confirmed" (exact conditions: artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/response/result/protocol/checks/1)
- [Conditional] existence: If the declared condition applies: At least one permitted assessment time falls within planned collection. — standing known; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/1/children/0/result
- [Conditional] nominal: If the declared condition applies: The nominal target is inside the permitted window and within planned collection. — standing known; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/1/children/0/result
- [Conditional] full_window: If the declared condition applies: Planned collection covers every permitted assessment time. — standing known; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/1/children/0/result

Check loading-schedule (schedule, required) — rests on standing known
- [No finding] existence: At least one permitted assessment time falls within planned collection. — standing known; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/0/children/0/result
- [No finding] nominal: The nominal target is inside the permitted window and within planned collection. — standing known; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/0/children/0/result
- [No finding] full_window: Planned collection covers every permitted assessment time. — standing known; result artifacts/536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d.json#/response/result/protocol/checks/0/children/0/result

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| loading-schedule | initial-randomized | all | loading | unconditional | oct | observed | randomization | day | 28 days from randomization | [25, 31] days from randomization | [25, 31] days from randomization | [25, 31] days from randomization | none | Target 28 days from randomization is inside the permitted window and within planned collection (satisfied) |
| maintenance-schedule | responders-rerandomized | all | maintenance | conditional — maintenance-oct: participant: "loading_response_confirmed" | oct | observed | maintenance_randomization | day | 56 days from maintenance_randomization | [49, 63] days from maintenance_randomization | [49, 63] days from maintenance_randomization | [49, 63] days from maintenance_randomization | none | Target 56 days from maintenance_randomization is inside the permitted window and within planned collection (satisfied) |
| vision-schedule | responders-rerandomized | all | maintenance | conditional — maintenance-vision: participant: "loading_response_confirmed" | vision-reading | observed | maintenance_randomization | week | 8 weeks from maintenance_randomization | [7, 9] weeks from maintenance_randomization | [7, 9] weeks from maintenance_randomization | [7, 9] weeks from maintenance_randomization | none | Target 8 weeks from maintenance_randomization has no applied finding (its deciding premise is a proposal or an input is missing) (unresolved) |

### Plan comparisons

No plan comparison declared.


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| oct | simulated-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:oct:simulated-v1 | user_choice: simulated:sponsor-loading-maintenance-v1 (no clinician confirmation) | known | known |
| loading-oct | simulated-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:loading-oct:simulated-v1 | user_choice: simulated:sponsor-loading-maintenance-v1 (no clinician confirmation) | known | n/a |
| loading-collection | simulated-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:loading-collection:simulated-v1 | user_choice: simulated:sponsor-loading-maintenance-v1 (no clinician confirmation) | known | n/a |
| maintenance-oct | simulated-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:maintenance-oct:simulated-v1 | user_choice: simulated:sponsor-loading-maintenance-v1 (no clinician confirmation) | known | n/a |
| maintenance-collection | simulated-v2 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:maintenance-collection:simulated-v2 | user_choice: simulated:sponsor repair expands maintenance OCT collection through day63 (no clinician confirmation) | known | n/a |
| vision-reading | simulated-v1 | not_adopted | No adoption record: nothing was declared as adopting this object; its definition reference is proposed | none | none | proposed | proposed |
| maintenance-vision | simulated-v1 | not_adopted | No adoption record: nothing was declared as adopting this object | none | none | proposed | n/a |
| vision-collection | simulated-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:vision-collection:simulated-v1 | user_choice: simulated:sponsor-loading-maintenance-v1 (no clinician confirmation) | known | n/a |

Superseded adoption records for maintenance-collection (listed, not used): adopt:maintenance-collection:simulated-v1 names a superseded version (maintenance-collection simulated-v1); not used.

### Open items

1. Check vision-schedule, claim visit: If the declared condition applies: Not applied: the deciding premise is still a proposal. (/protocol/checks/2/children/0/result)
2. Check vision-schedule, claim target: If the declared condition applies: Not applied: the deciding premise is still a proposal. (/protocol/checks/2/children/0/result)
3. Check vision-schedule, claim window: If the declared condition applies: Not applied: the deciding premise is still a proposal. (/protocol/checks/2/children/0/result)
4. Check maintenance-schedule: satisfied claims remain conditional on maintenance-oct: participant: "loading_response_confirmed". Applicability is not established by these calculations. (/protocol/checks/1/children/0/result)
5. Section assessments is open. (/protocol/sections/assessments)

### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.

## Changes from the previous revision (current revision: scoped-repair)

- protocol checks maintenance-schedule: Changed (verdict: the computed outcome changed; support: the deciding support changed; origin: the attributed origin changed; scope_model: the scope or an object version changed); Claim target, outcome: the nominal target is outside planned collection (not_collected) → holds under the declared inputs (satisfied); Claim window, outcome: planned collection leaves part of the permitted window uncovered (uncovered) → holds under the declared inputs (satisfied)
- entry: No change (unchanged). question: unchanged; answer: unchanged; requirements: unchanged; support: unchanged; origin: unchanged; wording: unchanged; context: unchanged
- question:entry:option:age49: No change (unchanged). question: unchanged; answer: unchanged; requirements: unchanged; support: unchanged; origin: unchanged; wording: unchanged; context: unchanged
- question:entry:option:age50: No change (unchanged). question: unchanged; answer: unchanged; requirements: unchanged; support: unchanged; origin: unchanged; wording: unchanged; context: unchanged
- protocol checks loading-schedule: No change (unchanged)
- protocol checks vision-schedule: No change (unchanged)
