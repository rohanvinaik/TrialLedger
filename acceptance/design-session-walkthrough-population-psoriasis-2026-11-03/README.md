# Psoriasis: one count, several possible meanings

Question declared before acquisition: **For a proposed adult plaque-psoriasis trial considering an upper age limit below 65, how can posted baseline/flow counts constrain that choice, and what must be established before treating protocol-related withdrawals as eligibility exceptions or joining analysis populations?**

No clinical user has accepted the readings or chosen a new-trial policy. This walkthrough compares declared explanations of observed studies and exposes the premises needed to reuse their evidence. A historical age distribution does not obligate a new trial to recruit that age range.

## Fresh acquisition and fixed sample

The actual TrialLedger preview/gather used guselkumab, Psoriasis, PHASE3 and COMPLETED. The complete query pool had 17 IDs, within the predeclared 30-study limit. Seed **6115270599430829862** was recorded before selected-content reading; sampling without replacement from the sorted pool selected **NCT02905331, NCT04936308 and NCT02203032**. No study was replaced after reading it. `selection.json` retains the complete pool, request, exact preflight locator, seed and timestamps.

Retention was declared before acquisition: the full report, workbook and raw bodies stay outside Git at `/Users/rohanvinaik/trialledger-runs/psoriasis-population-exceptions-20261103`. The raw clinical batch SHA256 is **68321af7033bb6c329737e177fbcfd864fbf96803ec7925d19a4fd500cc706ba**. Its local write time is **2026-11-03T21:05:34.282796+00:00**; this is a filesystem capture timestamp, not an independently recorded network response time. The registry's separate data timestamp is retained in the gather manifest. The actual full report passed `trialledger verify`: record and workbook reproduce from retained sources; interpretation is not certified by that check.

Complete selected eligibility, descriptions, arm definitions, primary outcomes, baseline and flow modules were read. Exact study fingerprints and reviewed unit addresses are in `source-inventory.json`. The raw batch contains NAVIGATE at `/studies/3`, the SelfDose study at `/studies/15`, and SOLSTICE at `/studies/16`.

## The source distinctions a designer needs

**NAVIGATE, NCT02203032:** entry is into an open-label ustekinumab run-in. At week 16, inadequate responders are randomized, while responders continue in a nonrandomized pathway. Run-in flow reports 872 started, 871 treated and four withdrawals categorized **Protocol Violation**. Baseline explicitly concerns enrolled participants receiving at least one dose and has denominator 871, including **53 aged ≥65**. The 872-person flow population and 871-person baseline population remain separate. The four reported violations are not located within the older subgroup, nor established as entry-eligibility failures.

**SelfDose, NCT02905331:** this is a moderate/severe plaque-psoriasis study with placebo crossover at week 16, baseline total 78 and six participants in its ≥65 category. Its primary IGA/PASI assessments count specified treatment failures and missing data as nonresponders. Treatment failure concerns that efficacy analysis; it does not establish entry ineligibility. The age-category boundary wording is preserved rather than silently repaired into a different partition.

**SOLSTICE, NCT04936308:** the broad query also retrieved active psoriatic arthritis after inadequate response/intolerance to one prior anti-TNF agent. It remains in the sample as a distinct clinical setting. In its Q8W arm, flow starts are **152** and the full analysis set is **151**. The Q4W rows are 151 and 150. The source comments describe **one participant randomized and treated at two sites**, appearing in both arm rows and excluded from analysis sets. Two row differences are not evidence of two distinct people. No cross-arm subtraction or sum is performed.

## Actual exception-attribution revisions

The public `design_bounds.exception_evidence` requests embed the complete NAVIGATE snapshot and anchor the exact typed count `"4"`, category `"Protocol Violation"`, denominator `"872"`, full flow group and full recording period. Those documentary quantities remain unchanged across five requests. The separate meaning binding and exception ceiling are declared hypotheses.

| Supplied meaning and ceiling | Actual result |
|---|---|
| Proposed broad protocol failure; unknown ceiling | Attribution open; no admitted eligibility floor; conditional floor 0. Ceiling stays null with `exception_upper_unknown`. Both candidate explanations unresolved. |
| Same proposed broad failure; independently assumed ceiling 5 | The represented floor can range up to 4, which fits 5 under every represented attribution. The bridge is consistent/interpolated; the still-proposed meaning remains visible without blocking the independent age conclusion. |
| Proposed entry-only attribution; ceiling 0 | Admitted floor remains 0; **conditional floor 4** retained. `binding_proposed` and `missing_entry_attribution` block closure. |
| Explicitly hypothetical, interpolated entry-only attribution; ceiling 0 | Floor 4 conflicts with ceiling 0. Common result CONFLICT/interpolated with `exception_bridge_conflict:enrolled-run-in`. This is a conflict between supplied premises. |
| Same hypothetical attribution; separately assumed ceiling 4 | Exception interval [4,4] is consistent/interpolated; the bridge conflict is removed. Both age-design candidates remain possible in this count-only case. |

The finite ceilings are **invented for the investigation**. Four attributed failures supply a lower bound, never evidence that there were at most four exceptions. The broad-cap5 result's `possible_floor_upper=4` describes the largest lower-bound constraint from these observations across represented meanings; it is not an upper bound on total exceptions. Its pending proposed attribution remains in the result while material blockers are empty. The recording period does not by itself identify the failed requirement. No real entry-only attribution or clinical-user confirmation is claimed.

The general adult-age query remains independently ENTAILED/known through the exact structured minimumAge rule in `source-general-age`. In the broad/proposed exception cases, each candidate's own age query also retains its direct proof, even though the common candidate-family answer is withheld. In the consistent-cap case that common age answer is known because its deciding proof is the independent minimum-age assertion, not the hypothetical exception attribution. Read the per-finding proof and status, not one label for the entire request.

## The sharp age boundary, without making a new design decision

Two separate requests use the real NAVIGATE baseline count **53 aged ≥65 among 871 treated participants**. The category reading and eligibility bridge are explicitly interpolated investigation premises. No protocol-withdrawal count or 872-person population is inserted into this calculation.

- Under the invented allowance of at most **52** exceptions, at least one older participant must serve as an eligible witness. The historical candidate requiring everyone to be under 65 is ruled out, with interpolated elimination standing.
- Change only that invented allowance to **53**: all 53 older participants could be excepted, so the candidate is restored and the observation reports `no_witness`.

The exact threshold is a computable consequence of the declared bridge. It neither establishes the actual exception allowance nor recommends an age cutoff. Both candidates carry the complete direct source-age floor, **18–99 Years**, copied from the actual source-assertion result with its original rule and provenance. The other candidate adds no further upper age restriction; neither survivor result establishes the complete historical protocol.

## Population direction and arm scope reach the consumer

The SOLSTICE count calculation is restricted to the **Q8W arm**. Its proposed subset binding names 152 started participants as the parent and the 151-person full analysis set as the subset. The source values and comments are cited; the clinical set correspondence remains a supplied premise.

| Revision through actual public operations | Observed consequence |
|---|---|
| Ordinary `signals` with proposed subset binding | Effective unresolved with `proposed_refused`; raw mathematical outside count [1,1] retained. |
| Same relation as an explicitly hypothetical interpolated assumption | Bounded/interpolated: one Q8W participant outside the analysis set. No eligibility-failure meaning follows. |
| Reverse only binding subjects while keeping the operator unchanged | Translation probe: unresolved `subjects_mismatch`, not a numerical refutation. |
| Coherently reverse both relation and operator: put 152 started participants inside a 151-person analysis parent | Conditional numerical conflict/interpolated with `inconsistent_population_total`. This refutes that supplied relation. |
| `design_bounds` with the matching interpolated subset and candidate claim “zero outside” | The claim is ruled out; the one-outside candidate survives. Elimination standing remains interpolated. |
| Change only the application arm to Q4W while the binding remains Q8W | Both candidates reopen as unresolved. Exact `scope_mismatch` survives; the zero-outside raw arithmetic conflict cannot eliminate a candidate for the wrong application. |

These are related questions, not interchangeable failures. A mismatched request needs repair; an impossible relation under accepted assumptions is a conditional contradiction. The complete effective/raw codes, blockers, declaration provenance and deciding checks remain in the canonical results.

## Decision handoff

| Decision | What this evidence/computation supplies | What would help next |
|---|---|---|
| What age coverage should the new trial seek? | Observed older participants, and the exact exception threshold needed to eliminate a historical under-65-only explanation. | Choose the intended population and explain any proposed age restriction; do not treat historical frequency as an obligation. |
| Which requirements did the four run-in violations concern? | Exact count, category, group and recording period; broad possibilities and an unconfirmed entry-only reading remain distinct. | Obtain applicable attribution if available. Keep an unknown ceiling unknown until separately warranted. |
| Which enrolled patients are represented in baseline, randomization and analysis? | NAVIGATE 872/871 and later randomization pathways; SOLSTICE per-arm analysis exclusions with explicit duplicate-person context. | Establish the relevant set correspondence at the intended arm/time/version. |
| Can the studied populations be compared for this design choice? | Plaque psoriasis, device administration, run-in nonresponse and active PsA are separately documented. | Decide which settings answer the new trial's question; the common registry search does not establish comparability. |

## Replay and bounded claims

Fourteen complete request/result pairs were executed through separate CLI and MCP processes after the corrected runtime freeze, with complete parsed JSON equality excluding only MCP's tool wrapper field. `runtime-receipt.json` records the commands, identities and runtime fingerprints. `receipt.json` and the file inventory record actual retention counts and hashes. Full raw/report copies and duplicate MCP wire captures remain local; the required complete source snapshots stay embedded in the exception/source-assertion requests. No source text or result has been shortened.

The complete reasoning inputs/results support layer-two replay under the writing version. Layer-one workbook verification additionally requires the locally retained report and raw sources. A future registry pull would be a new observation, not guaranteed historical-byte recovery. The capture helper remains local and is not production code.

One draft input repair is recorded: a shared scope object initially changed both sides of the intended wrong-arm comparison. It was corrected to change only the application scope, read back as Q8W binding versus Q4W use, and all pairs were rerun. The final coherent reverse-subset case is distinct from the retained subjects-mismatch translation probe. No runtime defect is inferred from those draft mistakes.

This walkthrough records the exercised public handoffs and their clinical limits. It does not certify automatic clinical encoding, authenticate a caller's claimed confirmation, or establish complete protocol identity from surviving candidates.
