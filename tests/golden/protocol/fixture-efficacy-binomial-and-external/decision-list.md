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
Exact result: `artifacts/96a8e55419dde0ad5fdad120fec930d1859b10c18c5812529c6964804c252b77.json#/response/result/decisions/0/alternatives/0`

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
Exact result: `artifacts/96a8e55419dde0ad5fdad120fec930d1859b10c18c5812529c6964804c252b77.json#/response/result/decisions/0/alternatives/1`

Origin: Computed from declared premises: user:adult
Coverage: Only caller-declared represented constructs; not complete clinical eligibility.
Exact result: `artifacts/96a8e55419dde0ad5fdad120fec930d1859b10c18c5812529c6964804c252b77.json#/response/result/decisions/0`

## Protocol

### Sections

| Section | Declared | Coverage | Findings |
|---|---|---|---|
| population | not_requested | not_requested | No checks: section not requested. |
| eligibility | not_requested | not_requested | No checks: section not requested. |
| interventions | not_requested | not_requested | No checks: section not requested. |
| endpoints | requested | open | Not fully checked (see coverage). |
| assessments | not_requested | not_requested | No checks: section not requested. |
| efficacy | requested | not_computed | Not fully checked (see coverage). |
| safety | not_requested | not_requested | No checks: section not requested. |
| exploratory | not_requested | not_requested | No checks: section not requested. |

Coverage legend: specified = the section's declared checks ran and nothing is open (not a clinical completeness claim); open = something is unapplied, undetermined or missing; not_computed = a check could not be computed; not_requested or not_applicable = the section is not declared or declared not applicable.

### Findings

Counts: conflict 0; repair choice 0; not computed 1; not applied 2; not determined 0; definition relations refuted by a counterexample 0. Kinds: Conflict = an admitted policy failure; Repair choice = an admitted gap you choose how to repair; Not computed = no finding because an input, scope or method is missing; Not applied = the deciding premise is still a proposal or unsupported; Not determined = a declared input is missing.

Check survival-method (external_method, required)
- [Not computed] (whole check): No finding: computed outside this tool (external method); missing inputs: accrual_rate, dropout; result artifacts/96a8e55419dde0ad5fdad120fec930d1859b10c18c5812529c6964804c252b77.json#/response/result/protocol/checks/1

Check efficacy-exact (binomial_design, required) — rests on standing known
- [Not applied] null_rejection_probability: Not applied: a premise this claim needs is not fully resolved. Withheld because the model assumption 'alignment' is not declared (assumption_missing:alignment). The computed values (null rejection probability 0.0100, power 0.4044) stay visible; they are not applied. — standing known; result artifacts/96a8e55419dde0ad5fdad120fec930d1859b10c18c5812529c6964804c252b77.json#/response/result/protocol/checks/0/children/0/result
- [Not applied] power: Not applied: a premise this claim needs is not fully resolved. Withheld because the model assumption 'alignment' is not declared (assumption_missing:alignment). The computed values (null rejection probability 0.0100, power 0.4044) stay visible; they are not applied. — standing known; result artifacts/96a8e55419dde0ad5fdad120fec930d1859b10c18c5812529c6964804c252b77.json#/response/result/protocol/checks/0/children/0/result

### Model assumptions

These are your declared model assumptions; the exact values below are conditional on them and are not a clinical applicability finding.

- Check efficacy-exact: model fixed sample size with independent, identically distributed binary responses (fixed_n_iid_bernoulli). Roles: fixed_n (the sample size n is fixed in advance): declared, known, version fixture-v1; iid_binary (responses are independent binary outcomes sharing one probability): declared, known, version fixture-v1; alignment (the declared p0, p1 and response definition match the planned endpoint (your declaration)): missing. Application: withheld (withheld because the model assumption 'alignment' is not declared (assumption_missing:alignment)). Retained plan: sample size n 20; critical count (reject at or above) 9; p0 1/5 (0.2000); p1 2/5 (0.4000); null rejection probability 951937324593/95367431640625 (0.0100); power 38566710919168/95367431640625 (0.4044). Guarantee: exact, conditional on the declared model. Not computed: sample size search; sequential or adaptive operating characteristics; clinical applicability.

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### Plan comparisons

No plan comparison declared.


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| score | fixture-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:score:fixture-v1 | user_choice: user:simulated choice (fixture) | known | known |
| response | fixture-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:response:fixture-v1 | user_choice: user:simulated choice (fixture) | known | known |
| efficacy | fixture-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:efficacy:fixture-v1 | user_choice: user:simulated choice (fixture) | known | n/a |
| survival | fixture-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:survival:fixture-v1 | user_choice: user:simulated choice (fixture) | known | known |

Superseded adoption records for week12 (listed, not used): adopt:week12:fixture-v1 names a superseded version (week12 fixture-v1); not used.

### Open items

1. Not computed: external method; missing inputs: accrual_rate, dropout. (/protocol/checks/1)
2. Check efficacy-exact, claim alpha: Not applied: a premise this claim needs is not fully resolved. Withheld because the model assumption 'alignment' is not declared (assumption_missing:alignment). The computed values (null rejection probability 0.0100, power 0.4044) stay visible; they are not applied. (/protocol/checks/0/children/0/result)
3. Check efficacy-exact, claim power: Not applied: a premise this claim needs is not fully resolved. Withheld because the model assumption 'alignment' is not declared (assumption_missing:alignment). The computed values (null rejection probability 0.0100, power 0.4044) stay visible; they are not applied. (/protocol/checks/0/children/0/result)
4. Section endpoints is open. (/protocol/sections/endpoints)
5. Section efficacy is not_computed. (/protocol/sections/efficacy)

### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.
