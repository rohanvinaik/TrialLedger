# ASTER-R: a simulated lupus cell-therapy platform

This is an invented clinical-development conversation, not a clinician confirmation or a proposed treatment recommendation. Registry passages are real retained evidence. Every ASTER-R restriction, relation, count and operational choice is explicitly simulated. The exercise checks represented choices, not a complete protocol.

## Start with the sources

A bounded NIH pull returned 45 Phase 1 lupus-nephritis registrations starting in 2020–2025, without a status restriction. Seed 2026110461 selected NCT06544330 and NCT06434363; neither sample was discarded. These multicohort cell-therapy studies provide documentary context, not a homogeneous efficacy comparison. The selected source workbook reproduced with `verify`.

The relevant complete registry modules were read. NCT06544330 describes non-lymphodepleted SYNCAR001 plus STK009; NCT06434363 describes AD-PluReceptor-CAR T cells with tafasitamab and lymphodepletion. Their populations, regimens and measurement periods remain separate. The registry's renal-response and background-treatment wording prompted questions; the program did not turn that wording into accepted clinical meaning automatically.

## The invented design and its decisions

ASTER-R combines induction, expansion and a later responder-only withdrawal stage. The draft requires adulthood, active biopsy-proven lupus nephritis and entry eGFR at least 30 mL/min/1.73m2, excludes uncontrolled infection, and requires eight stable weeks when an SGLT2 inhibitor is used. A separate permission records that background use can be allowed under that stability condition. Stage C requires a week-24 renal response.

| Decision | Computed consequence under these simulated choices | What remains open |
|---|---|---|
| Adult entry | Age 17 is ruled out; 45 is compatible with the represented restriction | All other eligibility requirements still apply |
| Infection | Uncontrolled infection is ruled out; its absence is required | How infection is clinically defined and assessed |
| Renal entry | eGFR 29 is ruled out under the initial 30 threshold | Clinical justification for the chosen threshold |
| Background SGLT2 treatment | Use alone leaves a stability requirement; use stable for only four weeks is ruled out | Whether the eight-week rule is the intended new-trial policy |
| Stage C | In explicit Stage C context, response is required and non-response is ruled out | The complete response definition and withdrawal regimen |

The later-stage cohort rule does not obscure the unrelated adult, infection or renal answers. The conditional permission remains visible without erasing any exclusion or requirement.

## Different thresholds can serve different roles

The draft separately represents an assessment trigger at a decline of at least 10% and an event definition at a decline greater than 15%, both relative to baseline at week 24. Claiming these definitions equivalent produces a conflict. Declaring that the later event must imply the earlier assessment trigger is consistent. The revision explicitly changes the intended relation to implication; it does not silently change either threshold to force agreement.

These are attributed typed readings bound to actual analysis addresses. The check establishes their declared logical relation, not that the chosen thresholds are clinically appropriate or faithfully interpret an external protocol.

## Operations and population assumptions

A separately invented planning scenario assumes 30 induction starters and 12 withdrawal entrants, with an attributed subset relation. The stage calculation preserves interpolated standing and a conditional count of 18 outside that subset. These are planning assumptions, not observed response rates from the two registries.

The declared treatment-policy estimand needs the represented week-24 renal measurements after treatment discontinuation. A supplied operations plan that stops collection produces `collection_plan_mismatch`. Actual measurements remain unknown; no treatment effect or missing-data estimator is computed. Choosing a suitable collection and analysis strategy remains a clinical/statistical task.

## Revision and delivery

The simulated second exchange widens entry eGFR from 30 to 20. Only the eGFR-29 profile changes its eligibility verdict, from ruled out to allowed but not required. The other verdicts stay fixed. Compatible profiles and their parent decisions report changed remaining requirements; they do not claim that widening eGFR changed the infection, age or Stage C rule. Changed support and origins remain separately visible.

Public CLI and initialized MCP produced identical complete baseline and revision results. Their Markdown and workbook exports were byte-identical. Read-only workbook inspection covered supporting-analysis summaries, warrants, changes and explicit permissions; no clipping was observed in those inspected ranges. The inspection did not cover every cell.

`receipt.json` records the exact sample, source fingerprints, outcomes, definition relations, revision axes and export locations. Complete requests/results and sources remain in this local run folder and its sibling report folders. Source preservation is verified; registry truth, clinical appropriateness, dosing, power, adaptive operating characteristics and complete protocol safety are not certified by this exercise.
