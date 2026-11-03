# Model-operated clinical walkthrough: diabetes design context

This is the development walkthrough following the documentation batch clarifying the IPASS count assumptions, computation limits, and model-operated workflow. It is outside CI and uses a fresh category, type-2 diabetes rather than the preceding NSCLC category. No runtime code was changed by this walkthrough.

## Question and selection

**Question:** For a proposed adult type-2 diabetes tirzepatide trial, do sampled completed phase-3 studies share background-therapy and comparator context, and what eligibility choices stay open?

The public landscape command was previewed, its complete identifier pool counted, and then the complete scope gathered:

```sh
uv run trialledger landscape --run /tmp/trialledger-docs-diabetes-20261103 \
  --drug tirzepatide --condition 'Type 2 Diabetes' --phase PHASE3 \
  --status COMPLETED --start-from 2020-01-01 --start-to 2022-12-31 --preview
# Same command without --preview gathered the scope.
```

The complete pool had seven studies. All seven were gathered; none were silently omitted. Before reading the selected studies, seed `3281138219941444813` was recorded. `random.Random(seed).sample(sorted(pool), 3)` selected **NCT04657016, NCT04255433, NCT05260021**, without replacement. The complete pool, exact ID-query address and sampling rule are in `selection.json`; `id-pool-001.json` retains the complete ID response.

For each selected study, the whole eligibility, population, arms, summary and registered-outcomes units were read. The exact full registry response containing all seven studies is retained once in `source/studies-001.json`. Addresses below are relative to each raw study's `protocolSection`; the study identifier is at `identificationModule.nctId`.

## What the records actually distinguish

| Selected study | Population and eligibility source | Arms and relevant endpoint context | Consequence for this question |
|---|---|---|---|
| NCT04657016 | `conditionsModule.conditions` lists obesity/overweight. `eligibilityModule` has minimum 18 years; its eligibility text explicitly excludes diabetes mellitus. Its BMI alternatives are at least 30, or at least 27 with a listed comorbidity. | `armsInterventionsModule.armGroups` describes tirzepatide versus placebo for 72 weeks after a lifestyle weight-loss program. `outcomesModule.primaryOutcomes` concerns weight change and weight reduction at week 72; HbA1c is secondary. | Membership in a diabetes search does not establish diabetes eligibility or a suitable diabetes comparator. The awkward sampled record was retained. Why the registry search matched this study was not established. |
| NCT04255433 | T2D, structured minimum 40 years; the eligibility text requires established CVD under its detailed definition and screening HbA1c from 7% through 10.5%. | The summary describes tirzepatide compared with dulaglutide. Both source arm-type fields say EXPERIMENTAL; those labels were preserved. The primary endpoint is a cardiovascular-event/time-to-first-event outcome, up to week 259; HbA1c at 36 months is secondary. | Adult age, a source-defined CVD population, comparator description and cardiovascular endpoint differ from a generic adult glycemic-control brief. A complete common background-medication policy was not established from the selected eligibility text. |
| NCT05260021 | Structured age fields are 10 to 18 years and age groups CHILD/ADULT. The eligibility text says 10 to below 18 **at screening**, and metformin and/or basal insulin with stable doses for at least 90 days. | Two tirzepatide doses versus placebo during the 30-week double-blind period; placebo then switches to tirzepatide. The primary HbA1c change is baseline to week 30. | Neither the ADULT tag nor the structured maximum alone settles adult eligibility at screening. Background alternatives and crossover time must remain explicit. The 30-week endpoint is not interchangeable with whole-study duration. |

These are source observations, not an assertion that all eligibility has been compiled. The complete contraception, BMI, exclusion, endpoint and other qualifiers remain in the retained record even where this walkthrough did not encode them. Their absence from a small reasoning request does not mean the trial lacks them.

## What the program computed

Five exact requests were each executed through the public CLI and actual MCP stdio `reason` tool. Full requests, CLI output and MCP transport records are under `reasoning/`. `calls.json` records ten completed executions; all five complete CLI/MCP result documents agreed after removing only MCP's transport `tool` wrapper. `summary.json` is a convenience summary, not a substitute for the complete results.

Each request used `source_assertions` with the complete raw study, its study digest, an exact eligibility anchor and context anchors for arms and primary outcomes. Only mechanically supported structured age information entered the fixed answers. The selected free-text readings entered interpretation frames as **proposed**, source-anchored premises. No person confirmed them in this development exercise. A frame being compatible means it is not ruled out by the supplied fixed constraints; it does not certify that it correctly translates every source clause.

| Case | Fixed result from supported structured input | Conditional result under the proposed reading |
|---|---|---|
| NCT04657016 | Minimum age 18 follows. Diabetes and BMI queries remain unresolved by this fixed input. | Diabetes and BMI below 27 are ruled out. BMI at least 30 is allowed but not required because the BMI 27-plus-comorbidity alternative remains. |
| NCT04255433 | Age at least 18 follows; age below 40 is ruled out. | T2D and qualifying CVD under this source's definition are required. Screening HbA1c of 11% is ruled out. This does not substitute a generic CVD definition or external medical knowledge. |
| NCT05260021 | Minimum age 10 follows. Untimed age exactly 18 remains unresolved. | Age 18 **at screening** is ruled out. Some background medication among metformin/basal insulin is required; neither individual medication is required. Dose stability is conditional on use of the corresponding drug, so a stability clause does not itself force that drug. |

The fixed age proposition and age at the named screening event were deliberately separate. The proposed screening reading did not overwrite the structured maximum 18 or answer an untimed age question by silently identifying the two times. This is not a demonstrated registry error and no source cleanup was performed.

## Meaningful revisions and their dependency trace

First, the `screening-upper-age` premise alone was withdrawn from the pediatric interpretation, leaving the source unchanged. The age-18-at-screening result changed from REFUTED to UNDETERMINED. The general structured minimum remained ENTAILED, and the separate background-medication disjunction remained ENTAILED. The deciding age proof names the withdrawn premise; the medication proof names `background-alternatives`.

Second, a deliberately hypothetical trial-design restriction replaced metformin **or** basal insulin with metformin **and** basal insulin. It is explicitly labeled a hypothetical narrowing, not a faithful reading of “and/or.” Both individual-medication queries changed from UNDETERMINED to ENTAILED. The screening-age conclusion remained unchanged. This is the concrete failure a careless translation could cause: an exact solver would correctly answer the narrower request while misleading the user if that request were presented as the source's rule.

The retained pairs are:

- `NCT05260021-source-reading-*`
- `NCT05260021-age-reading-withdrawn-*`
- `NCT05260021-hypothetical-both-drugs-*`

All are conditional computations over declared premises. None records a clinical choice by a real person.

## Decision-list handoff

| Decision | Evidence and computed consequence | Status |
|---|---|---|
| Which population belongs in this comparison? | One selected source excludes diabetes; one is pediatric; one requires age 40 or older and defined CVD. Search membership alone does not supply comparability. | Open; the comparison population needs an explicit choice. No sample replacement was made. |
| What adult-age rule, and at which event? | Structured age and screening-age wording are distinct channels. Withdrawing only the screening upper bound reopens that answer without erasing independent constraints. | Open; specify the new trial's age boundary and assessment event. |
| Is background therapy one alternative, either alternative, or both? | The pediatric proposed inclusive-OR reading requires some background therapy but neither drug individually. Requiring both changes the answer. A common policy across the three trials was not established. | Open; retain the alternatives until a design choice is made. |
| What function should the comparator serve? | Placebo after lifestyle modification, dulaglutide in a CV-outcomes setting, and placebo followed by crossover are different documentary contexts. Source arm labels and comparison roles were not collapsed. | Open; select a comparator and intended period rather than borrowing an arm title. |
| Which endpoint and time horizon answer the design question? | Weight at week 72, CV events up to week 259, and HbA1c at week 30 address different questions. No endpoint equivalence, time conversion or treatment effect was inferred. | Open; decide the target outcome and time horizon. |

The program settles consequences of an accepted encoding. The clinical choices above are not decided by this sample, a frequency claim, or a proposed reading. Further text could resolve some documentary gaps; none is treated as absent merely because it was not represented here.

## Verification and limits

`trialledger doctor` found the execution/report-writing prerequisites and source connectivity available. `trialledger verify /tmp/trialledger-docs-diabetes-20261103` passed: the clinical record and workbook reproduced from the retained sources. This establishes derivation, not registry truth or correctness of these clinical readings.

The five CLI/MCP pairs all ran against one stable captured Python-package fingerprint, recorded in `calls.json` and `code-identities.json`. Concurrent development is not inferred from Git HEAD: the captured file hashes identify the actual code used. This acceptance directory retains raw studies, scope metadata and exact reasoning pairs, not a redundant workbook or a fully relocatable copy of the full enriched report bundle. Local report paths and hashes are recorded in `receipt.json`.

This is a three-study random walkthrough from a seven-study query pool, not a corpus prevalence estimate. It exercises selected source assertions and interpretation consequences, not automatic full-text encoding, a complete trial-design writer, clinical validation, a new Detective pin or the whole test suite. There was no computation-limit result in these cases. No runtime fix was made or warranted solely by this evidence packet.


## Retention and replay

Complete submitted reasoning requests and canonical CLI results remain expanded here, with the original clinical findings and source/version receipts. The original full packet, including duplicate wire captures, raw search bodies and historical replay helpers, is retained locally outside Git. See RESTORE.md and retention.json. Original paths described above may require that full packet.

The saved request files can be replayed directly with `trialledger reason --request FILE` under the writing version. This does not require a registry re-fetch. Full workbook/source verification additionally needs the complete original packet. Re-fetching the same NCT ID now is a fresh observation and does not guarantee historical bytes.
