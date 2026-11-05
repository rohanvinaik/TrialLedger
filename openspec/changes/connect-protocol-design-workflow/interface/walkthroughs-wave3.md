# V6 walkthroughs, wave 3 (2026-11-04): isolated install of cceade7, cold CLI, real NIH pools

These were Sonnet clinician/assistant agents with no source reading; every choice was labelled simulated. The
evidence folders are `~/trialledger-runs/protocol-walk-{neuro2,id,renal}-20261104/`, each with `brief.md`,
`verdict.md`, pool accounting and seeded selection. They ran before the delivery commit 36762ac, so their
export findings predate it.

| Walk | Pool / selection | Computed | Wrong design → repair |
|---|---|---|---|
| Phase 2 relapsing MS (endpoint, estimand, dependencies) | 11 studies; seed 20261104 → NCT05116540, NCT03993171, NCT04002934 | estimand `collection_plan_mismatch`; dependencies consistent; schedule satisfied | stop at discontinuation → collect; `answer_diff` verdict (+ scope_model: the walker bumped the version) |
| Phase 2 pulmonary TB (exact efficacy) | 13 studies; seeded 3, none single-arm, so used as context only | A (30/20): α = 0.0494, power 0.7304 (power claim not met); B (40/26): α = 0.0403, power 0.8074 | A → B by revision gives verdict; a missing alignment role withholds application |
| Phase 3 CKD outcomes (external survival method, competing plans) | 28 studies; seeded 3 (2 with renal time-to-event outcomes) | plan A: week-24 window gap; plan B: satisfied; survival method `not_computed` with missing inputs | B → gap plan gives verdict and origin |

## Findings and status

| Finding | Status |
|---|---|
| `protocol_options` not discoverable or preparable (all three) | **Fixed**: `prepare` accepts `protocol.decisions` (compact alternatives with `replace`), and the card documents its shape, rules and results. Disclosed defaults point at the real expanded paths. Tested |
| Export, decision list and headline ignore the protocol | Export and decision list were **fixed in 36762ac**. The headline summary is **fixed now**: the metadata walks `result.protocol` checks and decisions (a violation counts as a conflict) |
| `answer_diff` has no before/after | **Fixed**: `protocol_checks` rows carry `changes`, the per-claim and per-signal before/after |
| `prepare` "drops" the handle digest | **Diagnosed**: the walker's handle had no digest, and preparation passed it through as given. Preparation now refuses a malformed handle early (`invalid_source_marker`) |
| Spurious `scope_model` | **Diagnosed**: not spurious. The walker changed the estimand object's version |
| Ids ambiguous, `source_interpretation` ref format, `external_method` inputs vs missing, raw vs effective outcomes, adoption attribution | **Documented** in the protocol card's `notes` |
| Collection `event_handling` is not consumed; availability is declared twice (estimand plan vs collection) | **Open**: a real design gap. It belongs with task 5.4 (cross-operation relations and bindings), and the card states it plainly meanwhile |
| Operator parameters (p0 > p1, k > n+1) are refused only at run time, after `prepare` succeeds | **Open**: admission-time operator validation is not yet run in preparation |
| `--revision` with `--session` rejected; `diff` omits protocol objects; `describe view protocol` ignores `detail` | **Open** (minor) |
| Adoption with an unrelated premise is accepted | **By design**: adoption is the caller's attribution; the tool does not judge relevance. Now documented |
