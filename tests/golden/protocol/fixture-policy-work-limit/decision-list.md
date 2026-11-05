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
Exact result: `artifacts/4074c5f4de05aae9383cdb6521f54f64266c102bd47fa6d882d9efdf065a2d94.json#/response/result/decisions/0/alternatives/0`

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
Exact result: `artifacts/4074c5f4de05aae9383cdb6521f54f64266c102bd47fa6d882d9efdf065a2d94.json#/response/result/decisions/0/alternatives/1`

Origin: Computed from declared premises: user:adult
Coverage: Only caller-declared represented constructs; not complete clinical eligibility.
Exact result: `artifacts/4074c5f4de05aae9383cdb6521f54f64266c102bd47fa6d882d9efdf065a2d94.json#/response/result/decisions/0`

## Protocol

### Sections

| Section | Declared | Coverage | Findings |
|---|---|---|---|
| population | not_requested | not_requested | No checks: section not requested. |
| eligibility | not_requested | not_requested | No checks: section not requested. |
| interventions | not_requested | not_requested | No checks: section not requested. |
| endpoints | not_requested | not_requested | No checks: section not requested. |
| assessments | not_requested | not_requested | No checks: section not requested. |
| efficacy | not_requested | not_requested | No checks: section not requested. |
| safety | requested | not_computed | Not fully checked (see coverage). |
| exploratory | not_requested | not_requested | No checks: section not requested. |

Coverage legend: specified = the section's declared checks ran and nothing is open (not a clinical completeness claim); open = something is unapplied, undetermined or missing; not_computed = a check could not be computed; not_requested or not_applicable = the section is not declared or declared not applicable.

### Findings

Counts: conflict 0; repair choice 0; not computed 1; not applied 0; not determined 0; definition relations refuted by a counterexample 0. Kinds: Conflict = an admitted policy failure; Repair choice = an admitted gap you choose how to repair; Not computed = no finding because an input, scope or method is missing; Not applied = the deciding premise is still a proposal or unsupported; Not determined = a declared input is missing.

Check big-safety (finite_policy, required) — rests on standing known
- [Not computed] coverage: Not computed within the declared work limit. — standing known; result artifacts/4074c5f4de05aae9383cdb6521f54f64266c102bd47fa6d882d9efdf065a2d94.json#/response/result/protocol/checks/0/children/0/result

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### Plan comparisons

No plan comparison declared.


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| big-rule | fixture-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:big-rule:fixture-v1 | user_choice: user:simulated choice (fixture) | known | n/a |

### Open items

1. Not computed within the declared work limit. (/protocol/checks/0/children/0/result)
2. Section safety is not_computed. (/protocol/sections/safety)

### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.
