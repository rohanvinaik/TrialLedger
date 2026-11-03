# Working brief: what does this retained IPASS record establish?

**Clinical question:** distinguish registered eligibility facts, conditional information recoverable from
baseline counts, and the schedule choices that still need a clinical reading.

**Comparison set:** IPASS, NCT00322452, only. This is an executable development example using the unchanged
[retained registry response](../../tests/fixtures/ipass-registry.md), fetched on 2026-11-03. It is not a
clinical recommendation. No clinical user has confirmed the population or schedule interpretations.

The assistant prepares proposed representations around exact source anchors. TrialLedger copies selected
source values and computes through its existing solvers. Automatic compilation of arbitrary clinical prose
and complete protocol generation remain unintegrated. Input content and compiled coverage are inspectable;
uncompiled text does not become an absent restriction.

## Decision 1: what age restriction should the new trial use?

**Evidence:** `/protocolSection/eligibilityModule/minimumAge` is exactly `18 Years`. The named direct rule
`ctg-structured-general-eligibility-age` encodes that registered general eligibility field. No clinical
interpretation of nearby prose is needed for this limited fact.

**Consequence:** the [age request](ipass-registered-age-request.json) and complete
[result](ipass-registered-age-result.json) entail age ≥18 Years and refute age <18 Years from premise
`registry-age-minimumAge`. These results concern that source-defined restriction; they do not certify a
complete protocol or demonstrate that every actual participant met it.

**Status:** source context established under the direct rule. A new trial's age choice remains open.

## Decision 2: which performance-status scale and range should the new trial use?

**Evidence:** the retained eligibility text supplies no performance-status cutoff. The baseline module's
WHO performance-status table reports **126 participants at WHO PS 2**, its smoking table reports
**1,140 never smokers**, and its total denominator is **1,217 participants**, each under local group `BG002`.
The request anchors the complete tables as well as exact count cells; no WHO-to-ECOG mapping is supplied.

**Consequence:** the [baseline request](ipass-baseline-overlap-request.json) copies those count strings
through exact integer templates. Within frame `aligned-baseline-counts`, binding `same-baseline-universe`
proposes that the two categories describe one exact baseline participant universe. Under that reading,
`numeric.overlap:1` returns **WHO PS 2 ∩ never smoking = [49,126]**. The emitted support and binding remain
`proposed`, with guarantee `conditional_on_interpretation`; the [complete response](ipass-baseline-overlap-result.json)
retains the input and provenance. The question whether the represented restrictions require WHO PS ≤2 is
`UNDETERMINED`, because no encoded criterion addresses that bound. This is not an exact recovered cutoff.

**Status:** open. Settle the scale, baseline-to-eligibility assessment alignment and exception allowance
before using participation as an eligibility witness. The exact joint count and membership are not stated.
No observation in this packet is promoted into a source-stated eligibility criterion or corpus element.

## Decision 3: which nominal targets, tolerances and subsequent anchor define the assessment schedule?

**Evidence:** the whole retained primary-outcome time-frame field states:

> Tumour assessments as per RECIST were performed at baseline and then every 42 days ± 7 days from randomization until data cut off (14th April 2008).

The anchor preserves the exact full string and half-open Unicode span. The source text does not by itself
establish the identity or attendance of an individual scheduled or actual assessment.

**Consequence:** the [schedule request](ipass-schedule-readings-request.json) keeps two assistant-authored
frames separate. Each preserves **nominal targets at days 42 and 84** together with the full **±7-day
tolerance**. The second nominal target is derived from a further 42-day nominal gap. Distinct target events
and permitted-assessment events carry these information channels; a target is not equated with a permitted
or actual assessment. Both frames give the first permitted assessment an interval of **[35,49] days** from
randomization. These values jointly inform this one schedule decision.

Under `randomization-anchored`, each subsequent tolerance is attached to its nominal day from randomization;
the second permitted assessment is **[77,91] days**. Under `successive-gaps`, each permitted interval after
the preceding assessment is **[35,49] days**; the temporal operator derives a second permitted window of
**[70,98] days** from randomization. The [complete response](ipass-schedule-readings-result.json) retains the
nominal targets and both permitted interval sets. Both readings remain proposed and compatible with the
mechanically compiled floor; no clinical text parser independently identifies the source's intended reading.

**Status:** open as one schedule choice. Retain the nominal targets and tolerance together, then settle
whether each subsequent tolerance stays anchored to randomization or starts from the preceding assessment.
Confirm window inclusivity. Keep these target and permitted-window channels separate from actual attendance,
and obtain the adopted endpoint definition before combining the schedule with a response-confirmation
interval. The computed later windows are conditional schedule consequences, not observed attendance.

## Revisions and evidence preservation

Change the relevant reading or binding in a new request and rerun it. A changed source needs a fresh content
digest and matching anchors. A stale, missing, mistyped or misaligned selected anchor is a translation
refusal, never a clinical refutation. Retain earlier request/result pairs when preserving a revision; do not
rewrite the original registry fixture or describe an old result as checking revised premises.
