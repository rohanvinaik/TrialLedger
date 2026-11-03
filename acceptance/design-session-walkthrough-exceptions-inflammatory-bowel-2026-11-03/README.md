# Crohn maintenance: keeping a population question open

This is the **guide-only metadata acceptance** within the inflammatory-bowel packet. It uses the retained fresh acquisition made for this increment, not a new pull at acceptance time. The pending exception-target bridge and task 2.8 are not exercised or completed by this walkthrough.

The question recorded before reading selected records was: **For a proposed new ustekinumab maintenance study, which induction-response, eligibility and population assumptions are needed before baseline or participant-flow information can constrain entry restrictions?**

## The retained source and clinical question

The actual TrialLedger preview/gather used ustekinumab, Crohn Disease, PHASE3 and COMPLETED. All ten matched records were gathered. Seed **4203754419260876930**, recorded before selected-content reading, selected NCT03107793, NCT01369355 and NCT04245215 from the complete sorted pool. The heterogeneous sample was retained unchanged. `selection.json` contains the query, pool, sampling rule and locators.

The original clinical-response body was locally written at **2026-11-03 20:00:32.007450 UTC**, according to its preserved filesystem modification time. This is the recorded local capture time; an independent network response timestamp was not recorded. The registry's separate data timestamp is **2026-11-03T10:00:05**. The batch SHA256 is **ca9d12ac7a05f83256c7b4741cc502ec8a3f3547e8240e3e381706c09ae1cfd6**.

Complete eligibility, study descriptions, population/arm definitions, registered primary outcomes and selected baseline/flow modules were read. The exact reviewed units and study digests are in `source-inventory.json`; the source review is retained in `working-brief.md`.

The records describe different settings:

- **IM-UNITI, NCT01369355:** its randomized maintenance arms describe participants who responded to IV ustekinumab induction. Its complete study description also admits induction nonresponders into nonrandomized pathways. Baseline BG005 describes 476 ustekinumab induction nonresponders; this does not establish an exception to a universal responder-only entry rule. That universal rule was never supplied as a source fact.
- **STARDUST, NCT03107793:** the later maintenance randomization follows a week-16 CDAI-improvement ≥70 gate. Baseline describes 498 induction participants, including 13 aged ≥65; maintenance starts are 219 and 221. Those baseline witnesses have not been located in the later maintenance population. The preassignment explanation separately reports exclusion of a site for compliance, reducing analysis from 500 to 498.
- **REScUE, NCT04245215:** eligibility describes a documented primary response followed by secondary loss of response under prior Q8W maintenance. That is a different treatment-history condition from induction nonresponse. Its flow starts 54 per arm, with 37 and 35 completing. No withdrawal-reason collection is posted in that flow period.

These are documentary readings, not a computed claim that the studies are clinically comparable. Their primary outcomes also differ: CDAI remission at week 44, endoscopic response at week 48, and steroid-free PRO2 remission plus fecal calprotectin at week 48.

## Executed scope revision

The complete raw IM-UNITI study is embedded in `requests/scoped-randomized-maintenance.json`, with its exact study digest. The request anchors the complete arm definitions and complete study description. It supplies an **assistant-origin, proposed** reading: participants in the named randomized-maintenance population must have responded to IV ustekinumab at induction week 8. The local cohort label and clinical meaning remain a declared reading.

The source bridge generated an ordinary interpretation request. The revision retained its source-derived fixed assertions, proposed reading and query, but **removed the randomized-maintenance context**. That exact revised request is saved in `requests/population-context-retracted.json`; it does not silently widen the reading to every study entrant.

Both complete requests ran through the actual CLI and MCP. Their complete parsed results matched, excluding only the MCP tool wrapper field.

| Question | Randomized-maintenance context supplied | Context removed |
|---|---|---|
| Does the response requirement follow under this reading? | ENTAILED, proposed, conditional | UNDETERMINED, proposed, open |
| Does the fixed general age restriction require age ≥18 Years? | ENTAILED, known, settled | ENTAILED, known, settled |

The reopened response question retains **all** its effective blockers: `interpretation_unresolved`, `open_scope:cohort_ref:randomized-maintenance` and `no_constraint_mentions_query`. Here “open” means the population application is unresolved. It does not establish that nonresponse is allowed, or that there is no response rule.

The revised frame's own age query is also withheld while that frame is unresolved: effective UNDETERMINED with its scope blockers, alongside raw ENTAILED and its raw-result address. The separate fixed-age query and common consequence remain ENTAILED under `registry-age-minimumAge`. The metadata preserves both the gate and the independent result. The clinical handoff uses the fixed-age result, not the withheld branch answer.

The fixed floor does not compile the free-text response restriction: its response query is UNDETERMINED with `no_constraint_mentions_query` in both runs. Source anchoring locates the reading without admitting it as a known source-defined rule.

## What the person can tell from the handoff

| Kind | This case |
|---|---|
| Source fact | The raw structured `minimumAge` is `18 Years`; exact arm and description passages remain anchored to this snapshot. |
| Proposed meaning | The response restriction and its randomized-maintenance scope are the assistant's reading. |
| Accepted clinical premise | None has been supplied by a clinical user in this walkthrough. Confirmation would accept the person's premise while retaining its origin; it would not change the registry. |
| Derived consequence | Under the proposed scope reading, the response requirement follows conditionally. Removing its application context reopens that answer while preserving the independent age floor. |

Actual focused discovery for both `source_assertions` and `interpretations` exposes **`answer_guide.standing`** through CLI and MCP. Its wording distinguishes an overridable interpolated assumption from an unconfirmed proposed reading, and instructs the operator to inspect the question and every blocker before interpreting an open result. Both complete discovery request/result pairs are retained.

## Decision list

| Decision | Evidence and consequence | Next useful action |
|---|---|---|
| Which entry population is the new study intended to address? | Randomized maintenance, nonrandomized nonresponder pathways and re-induction after secondary loss are separately described. The scoped response conclusion reopens when context is withdrawn. | Specify the intended population; then confirm or revise the response reading and rerun. |
| What response definition and assessment event should apply? | The three studies use different response gates, treatment histories and endpoint definitions. | Define the intended response condition and event in clinical words. |
| Can these counts constrain eligibility exceptions? | IM-UNITI reports Protocol Violation during maintenance, with no identified entry criterion. STARDUST reports other compliance/treatment categories. Those categories do not supply an entry-eligibility exception count. | Obtain an applicable attribution and population correspondence if available; retain the source counts meanwhile. |
| Can induction-baseline older participants constrain a maintenance age policy? | STARDUST reports 13 aged ≥65 among 498 induction participants; their membership in the later 440-person maintenance population is unresolved. | Resolve the population relationship and exception assumptions before using those witnesses. |

The exception target-set handoff is still **unintegrated**. No new request fields were invented, Protocol Violation was not encoded as an entry failure, and no cap12→13 exception calculation was run for this guide check. That later path requires its own integrated acceptance; these source observations remain available for it. No absence of a posted failure was treated as compliance.

## Replay and retention

The four canonical complete result files in `results/` correspond to the two clinical requests and two focused discovery requests. `runtime-receipt.json` records all four actual CLI/MCP comparisons, commands, request/result hashes, source/rule versions, runtime file fingerprints and completion time. `finding-summary.json` retains the deciding warrants and effective metadata; full results remain authoritative. `receipt.json` records final file/byte accounting and links the inventories.

The raw batch, full reference workbook/report, lookup cache and duplicate MCP wire captures are retained locally at the path in `local-retention.json`. The full copied report was checked byte-for-byte against the original before redundant repository raw copies were removed. The full original report passed actual `trialledger verify`; that reproduction outcome is in `verification-receipt.json`. A separately copied retained full report is also verified below by the final receipt. No additional registry retrieval was performed during this guide acceptance.

The complete committed reasoning inputs/results support layer-two replay under the recorded writing version. For example, from the repository root:

```sh
uv run trialledger reason --request acceptance/design-session-walkthrough-exceptions-inflammatory-bowel-2026-11-03/requests/scoped-randomized-maintenance.json
uv run trialledger reason --request acceptance/design-session-walkthrough-exceptions-inflammatory-bowel-2026-11-03/requests/population-context-retracted.json
```

Layer-one workbook verification additionally requires the locally retained full report and source packet. A future registry re-fetch is a new observation and cannot recover these historical bytes by guarantee. The selected snapshot embedded in the first complete reasoning input is retained because that public operation requires it. Other raw batches, report/workbook copies and duplicate wire replies are kept outside Git. No authored Python helper is included in this reviewable packet.
