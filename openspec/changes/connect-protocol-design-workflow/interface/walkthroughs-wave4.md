# V6 walkthroughs, wave 4 (2026-11-05): isolated install of d63dc08, cold CLI and MCP, real NIH pools

Five Sonnet clinician/assistant agents used only public discovery, the CLI and an initialized MCP client, against
an isolated install of d63dc08. They did no source reading. Every design value was labelled simulated. The shared
protocol is `~/trialledger-runs/wave4-walk-protocol.md`. The evidence folders are
`~/trialledger-runs/walk4-{neuro,haem,id,renal,psych}-20261105/`, each with `brief.md`, `verdict.md`, pool
accounting (`trialledger verify` passed for every pool), seeded selection (`random.Random(20261105)`) and
exports.

In every walk, MCP and the CLI produced the same artifact id and result digest.

| Walk (task) | Pool / sample | Wrong design → repair | Detected |
|---|---|---|---|
| Phase 2 ALS endpoint, estimand, dependencies (2.8) | 42 completed Phase 2 ALS studies, 2018–2022 | The estimand needs post-discontinuation data, but collection stops (`estimand_collection_plan_mismatch`). The repair is an instructed `--edits` new version, which re-adopted automatically. An imputed or unavailable baseline is never read as observed | yes |
| Phase 1 myeloma dose escalation (3.7) | 6 studies; NCT03848845, NCT04811898, NCT03828292 | (1) Escalation before the DLT window completes is a known prohibition violation, with a worded witness. (2) A hold loop gives termination not established (`reachable_cycle`). Both were repaired, by `--edits` and by `--session`. The DLT window sits in the policy, from the registry's "Up to 21 days" and arm-specific Day 21/28. The safety follow-up is a separate simulated schedule check | yes |
| Phase 2 HCV single-arm binary response (4.6) | 7 studies; NCT02175758, NCT02480387, NCT03036839 (context only) | p0 ≥ p1 is refused at `prepare`, naming the check. A missing alignment assumption withholds application while alpha 0.0442 and power 0.8122 stay retained. Plans compared, and n revised 30 → 36 (alpha 0.0522 then fails its bound) | yes |
| Phase 3 CKD outcomes (5.8) | 10 studies; CREDENCE NCT02065791, NCT03796156, NCT02021318 | A day-360 collection plan leaves day 364 uncollected and (360, 378] uncovered (repair choice). The event-driven log-rank method stays `not_computed`, with its five missing inputs named. A same-version change is refused on both `--session` and `--edits` | yes |
| Phase 3 MDD relapse prevention (6.7) | 3 studies (whole pool) | A collection gap (nominal day 56 not collected) is repaired. Relations: relapse ≥ 22 implies trigger ≥ 18 is consistent; `equivalent` and the converse are refuted relations, never protocol contradictions | yes |

The README, AGENTS, SKILL, DEVELOPING and docs maps were updated in the same wave (task 6.6), and every
published README request was run as written.

## Findings and status

| Finding (walk) | Status |
|---|---|
| A raw outcome shown as effective in Plan comparisons after a stale adoption (renal) | **Fixed**: alternative claims carry `effective_outcome`. Delivery shows the effective outcome and admission, and the raw value only "for reference" |
| Plan B's exact probabilities appear nowhere (id) | **Fixed**: each alternative retains `statistics` (n, k, p0, p1, exact tail probabilities). They are shown with decimals |
| The revision omits the n/k edit and before/after probabilities; decision rows say nothing about the selection (id, renal) | **Fixed**: `answer_diff` carries binomial value changes and decision `changes` (selection, disposition, per-alternative compatibility), all rendered |
| A withheld binomial claim does not name the missing role, and the model assumptions are never stated (id) | **Fixed**: the wording names `assumption_missing:<role>` and keeps the computed values. A Model assumptions section and sheet are added |
| A not-computed required external method hides repair vs compatible (renal) | **Decided by Rohan** (keep deciding). Delivery now names the deciding checks and the reason per alternative |
| Definition relations sit under "Supporting analyses", the direction is not shown, and a reading that differs from its guard is not flagged (psych) | **Fixed**: Protocol "Definition relations", per-direction results, `observed_match` (exact copy / differs) |
| A relation over an unadopted object reads "known" (psych) | **Decided by Rohan, fixed**: the status is capped by `bound_support`, and reads `proposed` until the bound objects are accepted |
| A superseded adoption reads as an effective premise (psych) | **Fixed**: labelled "names a superseded version; not used" |
| A refused child check is invisible; consistent dependency checks have no line (neuro) | **Fixed**: the check summary reads `refused`, with a Not computed item, and "No finding" rows |
| `answer_diff` misses origin and support changes for an object consumed through a link (neuro) | **Fixed**: the comparison includes receipt-consumed objects and non-claim signal support |
| "Settled" when the only compatible alternative is an unadopted what-if (haem) | **Decided by Rohan, fixed**: the disposition is `repair_choice` |
| An unmet selected binomial target reads as a repair choice (id) | **Decided by Rohan**: kept as a repair choice |
| A retained session copied with its own `parent_digest` is refused `parent_mismatch` (psych) | **Fixed**: a copied parent is treated as unset, and the program fills the real one |
| `reason-result --part decisions` is empty for a protocol plan comparison (haem) | **Fixed**: new parts `protocol` and `protocol_decisions` |
| The policy signal basis lists one adoption twice (haem) | **Fixed** for protocol kinds; v1 is unchanged (CMP-1) |
| The compact headline has no worded trace (haem) | **Fixed**: compact findings carry the witness, capped, with a truncation flag |
| The decision list says "No decision entries" above a plan comparison (id, psych) | **Fixed** wording |
| The protocol view is missing from the top-level discovery map; origin shape undocumented (docs, haem, psych) | **Fixed**: `discovery.protocol`, and `revision_edits.shape` documents `{kind, ref, source, analysis}` |
| The proposed endpoint definition reads as "adopted, known" (renal) | **Fixed**: the adoption output shows the definition reference standing |
| An `Always` guard is refused only at run (haem) | **By design, disclosed**: a session with retained-study handles defers validation to execution, and the run then refuses at admission, naming the check |
| Violations counted per reachable situation (one transition × an irrelevant flag) (haem) | **By design**: "in reachable declared situations" counts state × valuation |
| The object's standing basis still cites the old adoption after re-adoption (neuro) | **By design**: standing basis is caller text. The re-adoption edits are listed in the review |
| A plan mismatch labelled "repair choice" with no decision declared (neuro) | **By design**: consistent with "plan gaps open, policy conflict" |
| Dependencies are not linked to the baseline's own collection plan (neuro) | **Open contract gap**: a cross-operation link like the estimand's, for Rohan |
| `protocol_invalid_reference` and `invalid_fields:origin` don't name the field (renal, haem) | **Open** (minor): the origin shape is now documented; the reference code is unchanged |
| `record --text-limit` on a non-text address, and the page block on single objects (renal) | **Open** (minor, record reader) |
