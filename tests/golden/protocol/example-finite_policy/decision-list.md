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
| efficacy | not_requested | not_requested | No checks: section not requested. |
| safety | requested | specified | Conflict found in the declared checks. |
| exploratory | not_requested | not_requested | No checks: section not requested. |

Coverage legend: specified = the section's declared checks ran and nothing is open (not a clinical completeness claim); open = something is unapplied, undetermined or missing; not_computed = a check could not be computed; not_requested or not_applicable = the section is not declared or declared not applicable.

### Findings

Counts: conflict 1; repair choice 0; not computed 0; not applied 0; not determined 0; definition relations refuted by a counterexample 0. Kinds: Conflict = an admitted policy failure; Repair choice = an admitted gap you choose how to repair; Not computed = no finding because an input, scope or method is missing; Not applied = the deciding premise is still a proposal or unsupported; Not determined = a declared input is missing.

Check dose-policy-check (finite_policy, required) — rests on standing known
- [Conflict] prohibition: 1 declared prohibition violation(s) in reachable declared situations. — standing known; result artifacts/3f39f4f5970d23028e65acfe131cb8a2d2cef0d8a20b78bc94513933c08de148.json#/response/result/protocol/checks/0/children/0/result
  - Example trace: Example from the retained bounded trace: in state interim with efficacy_signal, safety_concern, transition continue selects continue_dosing.
- [No finding] coverage: Every reachable declared situation has a rule. — standing known; result artifacts/3f39f4f5970d23028e65acfe131cb8a2d2cef0d8a20b78bc94513933c08de148.json#/response/result/protocol/checks/0/children/0/result
- [No finding] termination: Every permitted path in the declared model reaches a terminal state. — standing known; result artifacts/3f39f4f5970d23028e65acfe131cb8a2d2cef0d8a20b78bc94513933c08de148.json#/response/result/protocol/checks/0/children/0/result

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### Plan comparisons

No plan comparison declared.


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| dose-policy | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:dose-policy:invented-v1 | user_choice: user:invented adoption (teaching example) | known | n/a |

### Open items

1. 1 declared prohibition violation(s) in reachable declared situations. (/protocol/checks/0/children/0/result)

### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.
