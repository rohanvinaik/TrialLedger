# Phase 2 migraine: a preventive platform with an attack-level rescue rule

This is a **simulated clinician conversation**. MX-64, its intended regimen, the choices below and the
conversation references are invented. The two registry records are real retained NIH evidence. A copied
registry sentence, a simulated choice and a computed consequence remain different things.

## The clinical question

[Simulated choice] Design an adult Phase 2 preventive migraine trial, with a separate attack-level rule
for investigational rescue. Ask which represented patients fit the adult entry restriction, whether the
rescue rule always specifies one action, and whether it can select an action explicitly forbidden by the
draft. Before considering efficacy claims, retain what the comparison trials actually studied.

The wider design would need a preventive endpoint, a diary, a separate acute/rescue observation period,
background-care rules, dosing, sample size and a statistical analysis plan. Those decisions were not
provided here and are not filled by the table checker.

## Reference evidence

The public CLI gathered all 18 returned completed interventional Phase 2 migraine studies with start dates
2020–2025. Acquisition limits were 100 studies and 30 registry requests. The pool and exact request are
retained in `sampling.json` and `registry-request.json`.

Sampling used `random.Random(2026110462).sample(sorted(all_returned_nct_ids), 2)`. No sample was discarded:

| Registry record | What its structured fields and wording report | Relevance and limit |
|---|---|---|
| NCT06728553, MTX101 | Acute treatment; randomized crossover; 78 actual participants; pain change from dosing to 2 hours is a planned secondary outcome; treatment-emergent safety assessments limited to 48 hours after a treated attack | Attack-level observation context. It is not a preventive-study template or proof of a rescue policy |
| NCT05679908, TNX-1900, PREVENTION | Chronic-migraine prevention; randomized parallel study; 88 actual participants; primary planned outcome uses the last 28 days of baseline and the last 28 days before week 12 | Preventive measurement context. Its primary outcome definition includes some attacks relieved by migraine-specific abortive treatment, so rescue and endpoint definition need separate attention |

These are heterogeneous reference studies, not a declared comparable class. I read the complete relevant
identification, status, design, eligibility, arms/interventions and planned-outcomes modules. I did not
assess posted efficacy magnitude, dose appropriateness, power or clinical suitability.

[Exact source wording] MTX101 lists “No more than a total of 15 headache days per month” under Key Exclusion
Criteria. This unusual wording is preserved. Its intended force was not corrected or silently adopted.
The decision list retains both eligibility passages with exact source addresses and snapshot digests.

The source workbook and clinical record reproduce under `trialledger verify reference`. That verifies
preservation and derivation, not the clinical truth of the registry.

## Simulated choices and the first rescue rule

Four independently declared Boolean inputs apply to one attack in the invented adult cohort:

1. An active safety warning is present.
2. Pain persists at 2 hours.
3. Investigational rescue has already been used for this attack.
4. The draft's declared lockout has elapsed.

These are supplied typed premises, not clinical interpretations extracted from either comparator. No
numeric lockout duration was inferred. The table's domain is exactly the 16 combinations of these flags.

[Simulated choice, exchange 1] If a warning is present, hold the investigational action and review. Otherwise,
if pain persists, select investigational rescue; if pain does not persist, continue observation.

Two explicit must-not rules accompany it:

- Never select investigational rescue when it has already been used for the attack or the lockout has not
  elapsed.
- Never select investigational rescue when an active warning is present.

[Computed, `table-initial-request.json` / `table-initial-result.json`] Coverage is **covered**, with no
different-action overlap. Nevertheless, the table is **conflict**: it can select an explicitly prohibited
action (`table_forbidden_action`). It returns three exact counterexample profiles:

| Warning | Pain persists | Rescue already used | Lockout elapsed | Returned forbidden action |
|---|---|---|---|---|
| No | Yes | Yes | Yes | Investigational rescue |
| No | Yes | Yes | No | Investigational rescue |
| No | Yes | No | No | Investigational rescue |

The prohibition was checked against the feasible cases. It was not added as a constraint that removes
those cases and then makes the rule appear safe.

## Revised rescue rule

[Simulated choice, exchange 2] Keep the warning hold. Select investigational rescue only when pain persists,
no rescue has been used for this attack, the lockout has elapsed and there is no active warning. Otherwise,
continue observation under the study table.

[Computed, `table-revised-request.json` / `table-revised-result.json`] The revised table is **consistent**,
coverage is **covered**, there are no different-action overlaps, and both declared prohibitions are
**clear** over the 16 declared combinations. This establishes compliance with these declared structural
rules. It does not establish clinical safety, sequential termination or operating characteristics.

[Open clinical choice] What non-study rescue or usual care is available when investigational rescue is
blocked? The action label “continue observation” does not answer that. The formal table's completeness
must not be presented as a complete care pathway.

## Partial illustration and translation boundaries

[Computed, `table-partial-witnesses-*`] I also declared nausea, aura, preventive arm and prior CGRP exposure as
four extra Boolean factors without assigning them new actions. This diagnostic table has 256 combinations.
With an explicit illustration bound of 128, the result still proves the same forbidden-action conflict,
while its witness summary reports:

- 128 of 256 combinations examined;
- zero counterexample illustrations returned from that prefix;
- 128 combinations unexamined;
- omitted witness count unknown, not zero;
- witness enumeration **truncated**.

Thus an empty bounded sample does not erase a proved conflict. These extra variables do not become
clinical decision rules merely because they were listed.

[Computed, `table-undeclared-*`] Adding a prohibition about an unrepresented allergic-reaction variable is
refused with `table_undeclared_prohibition_variable`. The operation does not silently introduce that
clinical factor or pretend that existing coverage included it.

[Computed, `table-unconfirmed-*`] Marking the input support proposed leaves applied state **unresolved**
and standing **proposed**, beside the raw conditional calculation **conflict**. The export preserves both.
It does not claim a real person confirmed the simulated policy.

## Adult entry decision and delivery

[Simulated choice] The represented new-trial age restriction requires age 18 years or older. The sampled
records both state 18–65, but the new restriction is a separate choice; no upper age cap was silently adopted.

[Computed, `managed-session-*`] Age 17 is REFUTED; age 45 is UNDETERMINED/allowed but not required under the
represented age restriction. This is not complete eligibility screening.

The initialized MCP transport and public CLI returned identical complete results for the initial rule,
revised rule, bounded illustrations, undeclared-variable refusal, proposed-support check and managed
session. Both exports included all four retained supporting analyses, exact source context and canonical
inputs. Their `design-review.xlsx` bytes match. `cli-export/review/decision-list.md` now displays the table
summary, declared variables, prohibitions and three initial counterexamples instead of leaving them only
on the detailed Findings sheet. The summaries remain separate from the age-policy decision.

One operator encoding error was deliberately retained in the record: my first evidence attachment gave
its context and anchor different IDs. The tool refused `identity_mismatch:decision.evidence.anchor`. I
corrected the scratch request, kept the refused pair as `managed-session-encoding-refusal-*`, and reran.
No source value or project code was changed to make the request pass.

## Requested, identified, abstained and wrong

| Class | What this exercise requested | Observed result |
|---|---|---|
| Declared rule conflict | Detect a covered table that can select forbidden rescue | Identified, with three exact profiles |
| Revised declared rule | Check coverage, conflicts and both prohibitions | Identified: covered, consistent, both clear within the declared domain |
| Bounded illustrations | Preserve limits beside an independently proved conflict | Identified: truncated, 128 unexamined, omitted count unknown |
| Translation | Do not silently add an undeclared clinical variable | Named refusal |
| Standing | Do not promote proposed support | Applied unresolved; raw conflict retained |
| Entry profile | Check age 17 and 45 under an explicit adult premise | REFUTED and allowed-but-not-required respectively |
| Delivery | Preserve these results through CLI, initialized MCP and included-analysis export | Matching full responses and byte-identical workbooks |
| Outside represented model | Clinical suitability, unrepresented harms, operating characteristics, sequential termination, comparator equivalence | Abstained/not computed |
| Wrong within these declared test oracles | A mismatched computed verdict or lost declared result | None observed; not a claim of universal correctness |

The machine-readable receipt retains source fingerprints, the fixed sample, full results, transport parity
and exact output paths. Open protocol choices remain open rather than being filled with invented content.
