# Maintenance entry: source review checkpoint

Historical acquisition/source-review notes. The completed guide-only acceptance and current decision handoff are in [README.md](README.md). The later exception target-set acceptance remains pending.

Question recorded before acquisition: for a proposed new ustekinumab maintenance study, which induction-response, eligibility and population assumptions are needed before baseline or participant-flow information can constrain entry restrictions?

No clinical user has confirmed an interpretation or selected a new-trial policy. The source review below informs open decisions. The supported population-scope reasoning was subsequently executed for the guide-only acceptance; the integrated exception path is still unavailable.

## Fixed acquisition

The actual public preview/gather used ustekinumab, Crohn Disease, PHASE3 and COMPLETED. The complete ID preflight had ten IDs, below the declared 30-study limit. Seed 4203754419260876930 was recorded before selected-content reading; the fixed random sample is NCT03107793, NCT01369355 and NCT04245215. No trial was replaced based on its content. `selection.json` retains the full pool, query, seed and preflight URL; `local-retention.json` locates and fingerprints the original clinical response body and full report retained outside Git.

The full original report in `/tmp/trialledger-bowel-exceptions-20261103` passed actual `trialledger verify`: record and workbook reproduce from retained sources. This is derivation verification, not clinical confirmation. The trimmed packet is not a complete verify folder; its workbook and lookup cache remain in the original temporary run.

## Source distinctions that affect the question

**NCT01369355, IM-UNITI.** The brief purpose and randomized maintenance arms concern IV-ustekinumab induction responders. The complete description also permits induction nonresponders in nonrandomized pathways. Baseline group BG005 describes ustekinumab induction nonresponders, denominator 476; BG004 describes placebo induction nonresponders, denominator 285. These are not established exceptions to a universal responder-only entry rule. The rule would have to be scoped to the randomized maintenance population first. The complete baseline total is 1281 while structured actual enrollment is 1282; equality or an invented missing participant is not assumed. Posted maintenance withdrawal categories include Protocol Violation; that category does not identify an entry-eligibility breach.

**NCT03107793, STARDUST.** Entry eligibility is moderate/severe active disease, baseline CDAI 220–450 and specified endoscopic activity, with treatment-history and main/sub-study distinctions. The arm/flow descriptions introduce a later week-16 CDAI-improvement ≥70 gate before maintenance randomization. Baseline denominator 498 belongs to induction. The preassignment explanation says one site was excluded for compliance, reducing analysis from 500 to 498. Maintenance flow starts are 219 and 221, and extension starts 147 and 176. These are distinct periods and source populations, not interchangeable denominator labels.

The complete baseline age categories include 13 participants ≥65 years out of 498. That can be retained as a genuine observed age-channel witness, without claiming a minimum or exact individual age. It does not locate those 13 within the later 440 maintenance participants. The source does not provide a number of entry-ineligible older participants. Later withdrawal for disallowed concomitant treatment or noncompliance likewise does not supply that number.

**NCT04245215, REScUE.** Eligibility requires documented primary response followed by secondary loss of response, with prior Q8W ustekinumab maintenance. Primary response and later loss of response have explicit time/measurement alternatives. Induction nonresponse is not equivalent to secondary loss of response. The overall flow starts 54 per arm; completed counts are 37 and 35 and not-completed counts 17 and 19. No withdrawal-reason collection is posted in this flow period. The absence of that table does not establish zero exceptions. Baseline total108 matches the sum of those starts numerically, which alone does not supply a population binding.

## Decision list

| Decision | Retained evidence/consequence to check | Status |
|---|---|---|
| Are we designing entry into induction, a randomized maintenance cohort, a rescue pathway, or re-induction after secondary loss? | The fixed sample contains all these different settings. A universal responder-only rule across the whole IM-UNITI study would erase documented nonrandomized pathways. | Open clinical choice |
| What is the response definition, and at which event? | STARDUST's maintenance-entry CDAI70 at week16 differs from its primary endoscopic response at week48 and from REScUE's documented primary response plus subsequent loss. | Open definition/scope question |
| Which observed patients can witness a proposed entry restriction? | STARDUST's 13 participants ≥65 are in the 498-person induction baseline, not an identified subset of 440 maintenance participants. | Open population binding |
| What allowance for eligibility exceptions is justified? | No genuine count explicitly attributed to entry-eligibility exceptions was identified in the complete reviewed baseline/flow and clinical units. Protocol-violation withdrawal counts remain source categories, with their periods/groups. | Evidence gap; no cap inferred |
| Would a proposed max-age<65 rule survive a different hypothetical exception cap? | Candidate cap12 versus13 can be explored as explicitly hypothetical assumptions for the real count13, if the intended population binding is declared. Neither cap is a source fact or a clinical user choice. | Proposed computation case awaiting schema/runtime readiness |
| What can be used without a clinical free-text reading? | Each selected source records minimumAge18Years. A direct source-age rule may supply a general-age floor, independently of unsettled exception meanings. | To verify through public operations |

The primary outcomes are also heterogeneous: IM-UNITI CDAI remission at week44; STARDUST endoscopic response at week48 (with its missing-data/nonresponse rule); REScUE steroid-free PRO2 remission and fecal calprotectin at week48. This sample does not establish endpoint or population comparability. The reviewed source units and exact locations are recorded in `source-inventory.json`.
