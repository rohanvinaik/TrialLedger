# Clinical design decision list

Session: design
Revision: one

Questions and option labels are caller wording, not computed assertions. Only the represented restrictions are checked. Caller origin labels are not authenticated confirmation.

## Should the represented age restriction require age 65?

Question above is caller wording.
Current computed result: Open design choice (design_choice).
No option has been selected by the caller yet.

Comparator evidence and context:
No comparator context linked to this decision; source absence is not asserted.

### Caller-labelled option: 65 or older

Represented profile: participant: "age" ≥ 65.0 Years
Actual analysis context: None listed
Computed answer: The represented proposition is allowed but not required under these restrictions (UNDETERMINED)
Feasibility: Compatible with the represented restrictions (feasible). Standing: known.
Deciding criteria:
adult: Requires participant: "age" ≥ 18.0 Years [standing: known; Caller-declared clinical choice: user:adult]
Remaining requirements:
No additional proved requirement displayed; this is not complete screening.
Open items: This exact query is allowed but not required; its negation also fits (undecided_by_constraints)
Exact result: `artifacts/9d96486618cca3117ea893dbfdc7c09747698ed114aa9bd1fa91e8b119087aea.json#/response/result/decisions/0/alternatives/0`

### Caller-labelled option: Below 65

Represented profile: NOT (participant: "age" ≥ 65.0 Years)
Actual analysis context: None listed
Computed answer: The represented proposition is allowed but not required under these restrictions (UNDETERMINED)
Feasibility: Compatible with the represented restrictions (feasible). Standing: known.
Deciding criteria:
adult: Requires participant: "age" ≥ 18.0 Years [standing: known; Caller-declared clinical choice: user:adult]
Remaining requirements:
The supplied profile does not establish the following; actual absence is not asserted.
required_by_criteria: participant: "age" ≥ 18.0 Years [standing: known; proof: adult].
Open items: This exact query is allowed but not required; its negation also fits (undecided_by_constraints)
Exact result: `artifacts/9d96486618cca3117ea893dbfdc7c09747698ed114aa9bd1fa91e8b119087aea.json#/response/result/decisions/0/alternatives/1`

Origin: Computed from declared premises: user:adult
Coverage: Only caller-declared represented constructs; not complete clinical eligibility.
Exact result: `artifacts/9d96486618cca3117ea893dbfdc7c09747698ed114aa9bd1fa91e8b119087aea.json#/response/result/decisions/0`

## Protocol

### Sections

| Section | Declared | Coverage | Findings |
|---|---|---|---|
| population | not_requested | not_requested | No checks: section not requested. |
| eligibility | not_requested | not_requested | No checks: section not requested. |
| interventions | not_requested | not_requested | No checks: section not requested. |
| endpoints | not_requested | not_requested | No checks: section not requested. |
| assessments | requested | open | A repair choice is open in the declared checks. |
| efficacy | not_requested | not_requested | No checks: section not requested. |
| safety | requested | open | Not fully checked (see coverage). |
| exploratory | not_applicable | not_applicable | No checks: section not applicable. |

Coverage legend: specified = the section's declared checks ran and nothing is open (not a clinical completeness claim); open = something is unapplied, undetermined or missing; not_computed = a check could not be computed; not_requested or not_applicable = the section is not declared or declared not applicable.

### Findings

Counts: conflict 0; repair choice 1; not computed 0; not applied 2; not determined 0; definition relations refuted by a counterexample 0. Kinds: Conflict = an admitted policy failure; Repair choice = an admitted gap you choose how to repair; Not computed = no finding because an input, scope or method is missing; Not applied = the deciding premise is still a proposal or unsupported; Not determined = a declared input is missing.

Check week12-schedule (schedule, required) — rests on standing proposed, unresolved (adoption:collection)
- [Repair choice] nominal: The nominal target is outside the permitted window. — standing known; result artifacts/9d96486618cca3117ea893dbfdc7c09747698ed114aa9bd1fa91e8b119087aea.json#/response/result/protocol/checks/0/children/0/result
- [Not applied] existence: Not applied: the deciding premise is still a proposal. — standing proposed; result artifacts/9d96486618cca3117ea893dbfdc7c09747698ed114aa9bd1fa91e8b119087aea.json#/response/result/protocol/checks/0/children/0/result
- [Not applied] full_window: Not applied: the deciding premise is still a proposal. — standing proposed; result artifacts/9d96486618cca3117ea893dbfdc7c09747698ed114aa9bd1fa91e8b119087aea.json#/response/result/protocol/checks/0/children/0/result

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| week12-schedule | not stated (open) | not stated (open) | not stated (open) | unconditional | score | observed | randomization | day | 100 days from randomization | [77, 91] days from randomization | (-∞, 80] days from randomization | [77, 80] days from randomization | (80, 91] days from randomization | Target 100 days from randomization is outside the permitted window (outside_window) |

### Plan comparisons

No plan comparison declared.


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| score | fixture-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:score:fixture-v1 | user_choice: user:simulated choice (fixture) | known | known |
| week12 | fixture-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:week12:fixture-v1 | user_choice: user:simulated choice (fixture) | known | n/a |
| collection | fixture-v1 | not_adopted | No adoption record: nothing was declared as adopting this object | none | none | proposed | n/a |

### Open items

1. The nominal target is outside the permitted window. (/protocol/checks/0/children/0/result)
2. Check week12-schedule, claim visit: Not applied: the deciding premise is still a proposal. (/protocol/checks/0/children/0/result)
3. Check week12-schedule, claim window: Not applied: the deciding premise is still a proposal. (/protocol/checks/0/children/0/result)
4. Section assessments is open. (/protocol/sections/assessments)
5. Section safety is open. (/protocol/sections/safety)

### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.
