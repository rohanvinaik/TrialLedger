# Clinical design decision list

Session: invented-session
Revision: one

Questions and option labels are caller wording, not computed assertions. Only the represented restrictions are checked. Caller origin labels are not authenticated confirmation.

No general design-choice entries were declared. Protocol plan comparisons and definition relations, if any, are under Protocol below; the workbook's Findings hold the rest.

## Protocol

### Sections

| Section | Declared | Coverage | Findings |
|---|---|---|---|
| population | not_requested | not_requested | No checks: section not requested. |
| eligibility | not_requested | not_requested | No checks: section not requested. |
| interventions | not_requested | not_requested | No checks: section not requested. |
| endpoints | not_requested | not_requested | No checks: section not requested. |
| assessments | not_requested | not_requested | No checks: section not requested. |
| efficacy | requested | specified | No conflict or open repair choice found in the declared checks. |
| safety | not_requested | not_requested | No checks: section not requested. |
| exploratory | not_requested | not_requested | No checks: section not requested. |

Coverage legend: specified = the section's declared checks ran and nothing is open (not a clinical completeness claim); open = something is unapplied, undetermined or missing; not_computed = a check could not be computed; not_requested or not_applicable = the section is not declared or declared not applicable.

### Findings

Counts: conflict 0; repair choice 0; not computed 0; not applied 0; not determined 0; definition relations refuted by a counterexample 0. Kinds: Conflict = an admitted policy failure; Repair choice = an admitted gap you choose how to repair; Not computed = no finding because an input, scope or method is missing; Not applied = the deciding premise is still a proposal or unsupported; Not determined = a declared input is missing.

Check binomial-check (binomial_design, required) — rests on standing known
- [No finding] null_rejection_probability: The exact null rejection probability 8267642361393/95367431640625 (0.0867) meets the declared bound <= 1/10. — standing known; result artifacts/cc338b2932346fee414362b11c1e09406e385631217370ad2f06d90165740b3d.json#/response/result/protocol/checks/0/children/0/result
- [No finding] power: The exact power 71524555975168/95367431640625 (0.7500) meets the declared bound >= 7/10. — standing known; result artifacts/cc338b2932346fee414362b11c1e09406e385631217370ad2f06d90165740b3d.json#/response/result/protocol/checks/0/children/0/result

### Model assumptions

These are your declared model assumptions; the exact values below are conditional on them and are not a clinical applicability finding.

- Check binomial-check: model fixed sample size with independent, identically distributed binary responses (fixed_n_iid_bernoulli). Roles: fixed_n (the sample size n is fixed in advance): declared, known, version invented-v1; iid_binary (responses are independent binary outcomes sharing one probability): declared, known, version invented-v1; alignment (the declared p0, p1 and response definition match the planned endpoint (your declaration)): declared, known, version invented-v1. Application: not_withheld_by_assumptions. Retained plan: sample size n 20; critical count (reject at or above) 7; p0 1/5 (0.2000); p1 2/5 (0.4000); null rejection probability 8267642361393/95367431640625 (0.0867); power 71524555975168/95367431640625 (0.7500). Guarantee: exact, conditional on the declared model. Not computed: sample size search; sequential or adaptive operating characteristics; clinical applicability.

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### Plan comparisons

No plan comparison declared.


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| response | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:response:invented-v1 | user_choice: user:invented adoption (teaching example) | known | known |
| response-endpoint | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:response-endpoint:invented-v1 | user_choice: user:invented adoption (teaching example) | known | known |
| efficacy-design | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:efficacy-design:invented-v1 | user_choice: user:invented adoption (teaching example) | known | n/a |

### Open items


### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.
