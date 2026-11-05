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
| safety | not_requested | not_requested | No checks: section not requested. |
| exploratory | not_requested | not_requested | No checks: section not requested. |

Coverage legend: specified = the section's declared checks ran and nothing is open (not a clinical completeness claim); open = something is unapplied, undetermined or missing; not_computed = a check could not be computed; not_requested or not_applicable = the section is not declared or declared not applicable.

### Findings

Counts: conflict 0; repair choice 0; not computed 0; not applied 0; not determined 0; definition relations refuted by a counterexample 0. Kinds: Conflict = an admitted policy failure; Repair choice = an admitted gap you choose how to repair; Not computed = no finding because an input, scope or method is missing; Not applied = the deciding premise is still a proposal or unsupported; Not determined = a declared input is missing.

Check trigger-check (finite_policy, required) — rests on standing known
- [No finding] coverage: Every reachable declared situation has a rule. — standing known; result artifacts/0de7f5a5e444d41ff9fbcdb4f5c2c867040210aa02cb4012b3d7174cf26d9011.json#/response/result/protocol/checks/0/children/0/result

Check relapse-check (finite_policy, required) — rests on standing known
- [No finding] coverage: Every reachable declared situation has a rule. — standing known; result artifacts/0de7f5a5e444d41ff9fbcdb4f5c2c867040210aa02cb4012b3d7174cf26d9011.json#/response/result/protocol/checks/1/children/0/result

### Definition relations

A relation is your declared relationship between two readings. A conflict means the relation is refuted by a counterexample, not that the protocol contradicts itself.

- Relation relapse-implies-trigger (the left reading implies the right reading): consistent, no counterexample to the declared relation was found. Standing known (your declaration). implies: ENTAILED.
  - Left reading (check relapse-check, address /request/signals/0/data/transitions/0/guard): this reading is an exact copy of the value at its address (exact_copy).
  - Right reading (check trigger-check, address /request/signals/0/data/transitions/0/guard): this reading is an exact copy of the value at its address (exact_copy).

### Schedule of assessments

| Check | Cohort | Arm | Phase | Conditionality | Measurement | Mode | Anchor | Unit | Nominal | Permitted | Collection | Feasible | Gap | Nominal outcome |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### Plan comparisons

No plan comparison declared.


### Adoption

| Object | Version | Adoption | Adoption in words | Adopted by (premise id) | Attributed to (caller label, not authenticated) | Object standing | Definition reference standing |
|---|---|---|---|---|---|---|---|
| trigger-rule | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:trigger-rule:invented-v1 | user_choice: user:invented adoption (teaching example) | known | n/a |
| relapse-rule | invented-v1 | adopted_known | Adopted as written (caller-attributed; known only if its premises hold) | adopt:relapse-rule:invented-v1 | user_choice: user:invented adoption (teaching example) | known | n/a |

### Open items


### Limits

- Each check covers only its declared objects, claims and variables; not medical completeness.
- Projection receipts record consumed objects and premises; they do not establish meaning.
- Each claim is admitted on its own deciding support; the signal code is a conservative summary.
- Coverage and violations are over the declared variables, objects and claims only.
- Rendered decimals are rounded displays; exact rationals are canonical.

## Supporting analyses

These are separate computations, not additional clinical choices. Inclusion alone does not bind populations or adopt a comparator's result. Applied results and conditional calculations remain distinct; open the exact result for all support and admission details.

### Main / definition relapse-implies-trigger (definition_check)

Applied: consistent; calculation: consistent. Standing: known.
Declared scope: kind: new_trial
ref: invented-draft
scope: arm: all
population: adults
study: invented-draft
time: entry
version: draft-1; version/snapshot: Open exact declarations and warrants
Declared relationship: implies; returned result: consistent. A conflict is relative to this explicit relationship, not proof that differently purposed thresholds must match.
Basis: user:invented definition-relation declaration (teaching example); rule: Declared definition relationship; open exact checks for rule versions
Open items: No blocker reported
Exact result: [definition_check result](artifacts/0de7f5a5e444d41ff9fbcdb4f5c2c867040210aa02cb4012b3d7174cf26d9011.json#/response/result/definition_checks/0)

- Left meaning: participant: "madrs" ≥ 22.0 score; bound protocol check: relapse-check, child 0; bound address: /request/signals/0/data/transitions/0/guard; resolution: resolved; basis: user:invented relapse-check reading (teaching example). Standing: known. [Exact detail](artifacts/0de7f5a5e444d41ff9fbcdb4f5c2c867040210aa02cb4012b3d7174cf26d9011.json#/response/result/definition_checks/0/declaration/left)

- Right meaning: participant: "madrs" ≥ 20.0 score; bound protocol check: trigger-check, child 0; bound address: /request/signals/0/data/transitions/0/guard; resolution: resolved; basis: user:invented trigger-check reading (teaching example). Standing: known. [Exact detail](artifacts/0de7f5a5e444d41ff9fbcdb4f5c2c867040210aa02cb4012b3d7174cf26d9011.json#/response/result/definition_checks/0/declaration/right)
