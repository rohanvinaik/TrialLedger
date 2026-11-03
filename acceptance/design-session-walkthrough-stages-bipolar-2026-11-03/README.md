# Bipolar stages: which population reached the next stage?

The question was declared before retrieval: **For a proposed bipolar maintenance/randomized-withdrawal study, what can run-in and randomized counts tell us, and what population/transition premises are needed?** The retention plan and fresh random seed were recorded in `preflight.json` before acquisition, then acquisition waited for the public stage operation.

The sample did **not** supply a complete randomized-withdrawal run-in→randomized population. That coverage gap is retained. The executed new-stage acceptance concerns an actual open-label extension's enrollment→drug-receipt and enrollment→completion populations. It does not claim that randomized withdrawal has been validated by changing a label.

No clinical user accepted a reading or selected a design. Clinical set relations remain proposed or are explicitly hypothetical interpolated sensitivities. Exact counts and source locations are retained separately from those relations.

## Fresh query, bounded acquisition and source reading

The public TrialLedger preview resolved **quetiapine + Bipolar Disorder + PHASE3 + COMPLETED**. The complete identifier preflight found31 records. This exceeded the predeclared complete-pool gather limit30, so the full31-ID pool was retained and only the already selected IDs were gathered in a separate report folder. Seed **3948003275121507650**, recorded before selected-content reading, sampled NCT00090311, NCT00227305 and NCT00119652 without replacement from the complete sorted pool. No study was replaced to obtain a maintenance example.

`selection.json` retains the exact search, full pool, identifier locator, response fingerprint/timestamp, sample and bounded-gather decision. The original search preview is local at `/Users/rohanvinaik/trialledger-runs/stages-bipolar-20261103`. The actual complete3-ID report is `/Users/rohanvinaik/trialledger-runs/stages-bipolar-sample-20261103`; all3 requested identifiers were found under their own numbers. Its record and workbook passed actual `trialledger verify`.

Complete selected identification/status, descriptions, design, eligibility, interventions and registered outcomes were read. NCT00227305's complete participant-flow and baseline modules were also read. The other two records have no posted results section: missing flow/baseline is retained, not supplied as zero. `source-inventory.json` records the complete reviewed units and exact snapshots. The raw batch's capture timestamp is a filesystem write time; the registry's own version timestamp remains in the gather manifest.

| Selected study | What the source documents | Consequence for the original question |
|---|---|---|
| NCT00090311 / D1441C00149 | Acute3-week pediatric bipolar-I-mania trial; structured age10–17; actual enrollment220; randomized parallel placebo comparison; no posted flow/baseline results. | It is one predecessor of the extension below, but enrolled220 is not a documented count of feeder completers or all extension entrants. |
| NCT00227305 / D1441C00150 | Open-label26-week pediatric bipolar/schizophrenia extension. Eligibility says previously enrolled in D1441C00149 **or** D1441C00112; flow preassignment says completed one of those two feeder studies. In FG000,381 enrolled,380 received drug/safety population,237 completed26weeks,144 not completed. Baseline denominator380. | This supplies within-extension stage counts and explicit source context. It does not identify how many came from each feeder or constitute a randomized-withdrawal population. |
| NCT00119652 / EMBOLDEN II | Adult bipolar depression; acute8-week treatment and continuation described; structured age18–65; actual enrollment676; no posted flow/baseline results. | Mention of continuation does not supply its entrance count, gate, allocation or a run-in→randomized transition. |

The extension's baseline contains205 bipolar and175 schizophrenia participants. Thus its380 dosed/baseline total cannot silently become380 bipolar participants. Its structured maximum17, flow preassignment wording “between10 and18…at the time of consent,” and baseline13–18 category remain separate source channels. The category does not establish that an18-year-old was enrolled, and the untimed structured age is not automatically the consent-event age.

## What ran through the public interfaces

Nine complete request/result pairs ran through separate CLI and fresh stdio MCP processes. All complete parsed documents matched after removing only MCP's `tool` wrapper. `runtime-receipt.json` retains exact commands, exits, fingerprints and comparison times. Original package files were frozen; any separately added files are recorded outside that frozen-file claim. Full canonical results accompany the requests.

**Three source-age checks.** Each complete source snapshot enters `source_assertions`. The direct structured-age rules establish age≥10 and refute age≥18 for the two pediatric records; both propositions follow for the adult record. For the extension, the separate query “age18 at consent” remains UNDETERMINED with `no_constraint_mentions_query`. The preassignment passage is anchored, but no clinical reading or time equivalence is promoted into the fixed floor. The extension's complete age result was replayed after the stage revisions and remained unchanged.

**Four standalone stage checks.** The stage input retains study, snapshot, named population, FG000 arm, event/time, unit `person`, exact total and separate transition declarations. Enrollment is the parent separately for dosing and completion; no completion⊆dosed relation is supplied.

| Relation/application | Actual result |
|---|---|
| Permission to proceed, without an actual subset assertion | Both edges `permitted_only`; their `population_request` and `population_result` are null. No subtraction is admitted from permission. |
| Same proposed documented-subset readings | Each edge unresolved with `proposed_refused:<edge>`. Conditional raw population results remain visible:144 outside completion and1 outside drug receipt. These are not admitted conclusions. |
| Explicit hypothetical interpolated subset sensitivities | Each edge `bounded`/interpolated. Enrollment381 minus completion237 gives outside[144,144]; enrollment381 minus dosed380 gives outside[1,1]. |
| Change only completion application's target-time declaration | Completion edge unresolved with `stage_scope_mismatch:entry-to-completion`, with no population calculation. Dosing edge still bounded/interpolated with outside[1,1]. Read each edge's effective code/support rather than the aggregate unresolved label alone. |

The top-level `operator_support` and transition-local metadata retain determining edges and their weaker standing. The source count encoding remains distinguishable from the hypothetical lineage. A named `gate_ref` locates the source milestone reference; the operator does not evaluate a clinical response or tolerability gate from that reference.

**Two design-consumer revisions.** The same sensitivity input feeds `design_bounds` with two deliberately limited candidate count claims: everyone completed versus144 outside completers. Under the matched completion relation, the first is ruled out with **interpolated elimination standing**, while the144-outside claim is not ruled out. Change only the completion application time to the mismatched value: both candidates reopen as unresolved, retaining the scope blocker. The unaffected dosing calculation remains visible in both candidates' checks.

Those candidate claims test one aggregate count consequence, not a whole recovered protocol. The deliberately unrepresented individual-profile query remains UNDETERMINED. A surviving count explanation neither locates an individual nor decides a clinical eligibility criterion.

## Clinical meaning and limits

The144 participants outside the supplied completion subset are not automatically144 entry-ineligible people, treatment failures, or losses to follow-up. The record already supplies separate withdrawal categories. The one outside the dosed subset is not automatically located inside or outside completion. We supplied no relation joining those two subsets and performed no implicit cross-module or cross-study join.

The extension admitted completers from feeder149 **or** feeder112. Taking one selected predecessor's enrollment220 as the parent of all381 extension entrants would discard the other feeder and substitute enrollment for completion. No such subtraction or conflict claim was run. The OR reading, feeder-specific completion counts and cross-study correspondence remain documentary/translation tasks.

Missing continuation counts in EMBOLDEN II and missing acute-trial results in ANCHOR149 do not license invented stages. An actual run-in→randomized-withdrawal walkthrough still requires suitable source evidence. This sample was kept intact rather than replaced to conceal that gap.

## Decision list for the clinical designer

| Decision | Evidence and computed consequence | Next action |
|---|---|---|
| What stage is the target population? | The sample spans acute pediatric mania, a mixed-diagnosis open-label extension, and adult acute depression/continuation. None supplies the complete intended randomized-withdrawal pathway. | Specify acute, extension, stabilization, randomized maintenance or withdrawal before selecting comparators. |
| Which entrants can progress? | Feeder149 or112 completion is documentary context; permission and documented membership are different relations. | Identify the intended clinical gate and its assessment event, then obtain the population relationship it warrants. |
| What is the denominator for completion? | Under the explicit enrolled-parent sensitivity,237 of381 complete and144 are outside that subset.380 dosed is a separate subset. | Choose the population for the question; do not infer completion⊆dosed from arithmetic alone. |
| Can these figures plan bipolar maintenance recruitment? | Extension baseline380 includes175 schizophrenia participants; feeder-specific counts and randomized-maintenance counts are unavailable here. | Obtain indication- and stage-specific counts before treating the sample as recruitment evidence for that design. |
| What age and event define entry? | Structured10–17 is directly available; age18 at consent remains a separate unresolved query. | Clarify the consent/entry-age rule and source timing rather than silently repair the registry. |

`working-brief.md` preserves the concise handoff. No choice was made on behalf of a clinical user.

## Replay, retention and verification scope

Retention was decided before acquisition. The review packet contains complete reasoning requests/canonical results, query/pool/seed, source/runtime/version/time/hash receipts and this clinical handoff. Full report/workbook/raw bodies, lookup cache, helper and duplicate MCP wires remain local outside Git. Snapshots required by the source requests stay complete inside those requests.

Run any saved request with `trialledger reason --request FILE` under the recorded writing version. Complete inputs support layer-two replay. Layer-one workbook verification additionally needs the local retained full report and raw packet. Re-fetching an NCT ID is a new observation, not guaranteed historical-byte recovery.

The helper's final replay check initially compared Python tuples with JSON lists; it was normalized to the documented JSON form, then all9 pairs were rerun. No production defect is inferred from that helper-format correction. This workflow is separate from Detective pins and the full normal gate; it verifies the exercised public handoffs and preserves their clinical and paradigm-coverage limits.
