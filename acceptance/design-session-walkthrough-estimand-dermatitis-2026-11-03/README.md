# Phase 2 dermatitis: a response definition is more than an analysis label

The question declared before acquisition was: for a proposed Phase2 atopic-dermatitis study, how do sampled tralokinumab records define response after rescue treatment, treatment discontinuation or an unavailable assessment? Which information concerns the clinical target, and which concerns an analysis technique?

This is a fresh model-operated walkthrough of the integrated estimand relevance, collection and actual-input representation and its interpretation consumer. It does not reconstruct a complete registry estimand or validate any clinical target. No clinical user confirmed a reading or chose a new policy.

## Fixed acquisition and source reading

The complete tralokinumab / Atopic Dermatitis / PHASE2 / COMPLETED query returned four studies. Seed3061570227477035330 selected NCT05388760, NCT02347176 and NCT04556461 before their content was read. All four pool records were acquired; no selected study was replaced. The selected set is deliberately retained even though it contains pediatric PK, adult randomized efficacy and adult single-group skin-barrier studies.

`selection.json` preserves the full query, complete ID pool, seed, retrieval time and body fingerprint. `source-inventory.json` identifies exact selected snapshots and read units. All selected protocol identification, status, description, design, eligibility, arms/interventions and outcomes modules were read in full. NCT02347176's complete participant-flow and baseline modules and complete relevant efficacy result objects0,1,6,7,8,9 were read. Results for the other two studies are not posted in these snapshots. `source-reading.md` records the clinical distinctions and source gaps.

Important source distinctions:

- NCT05388760 permits medically necessary rescue at the trial doctor's discretion. Its primary objective is pediatric PK; its efficacy outcomes extend to week68. Permission to rescue supplies neither a post-rescue target nor a missing-data rule.
- NCT02347176 reports exclusion of prohibited-medication data from named efficacy analyses and explicitly reports LOCF for EASI50 and SCORAD50. Neither wording supplies a complete clinical estimand. Prohibited medication is not assumed to be the same as rescue medication. Its ITT definition says randomized **and treated**, and outcome denominator labels do not reveal individual exclusions or missing observations.
- NCT04556461 measures TEWL in selected lesional and non-lesional skin areas at day112 versus day0. Local marker-area restrictions do not become whole-person treatment restrictions. A single-group skin-barrier endpoint does not become a randomized treatment contrast.

Complete selected snapshots and exact source anchors are embedded in `requests/*-source-age.json`; the full raw report and workbook remain local outside Git. A located passage establishes its wording, not the clinical meaning of an unencoded target.

## Exact source restrictions stay independent

Three source-assertion requests ask whether the structured age restriction requires at least18Years. The adult trials NCT02347176 and NCT04556461 entail this; pediatric NCT05388760 refutes it. Standing is known, from the structured source rule. This answers only the age restriction, not overall enrollment eligibility. Replaying all three requests after the hypothetical revisions returns identical complete results. No comparator age restriction was silently adopted into the new-study draft.

## Explicit hypothetical target and revisions

Every new-study definition ref, discontinuation event, relevance rule, collection plan and data state below is an **invented assistant sensitivity**, declared interpolated and overridable. These are not source facts or clinician-confirmed choices. The five refs identify supplied treatment, population, variable, intercurrent events and summary definitions; `definition_state: complete` means admitted supplied refs, not medically complete or validated definitions.

The declared scenario concerns an observed EASI score at one exact nominal week12 window after discontinuation. Its observation is declared required; the collection plan says stop; the scenario says the observed value is unavailable while an imputed value is available.

| Change in supplied premise | Computed result | What stays unresolved |
|---|---|---|
| Initial required observation + stop collection + unavailable observed value | Relevance required; collection_plan_mismatch; missing_relevant | Clinical target, appropriateness and estimation |
| Change only the plan to collect | Collection aligned; actual input remains missing_relevant | A planned collection does not recover a datum |
| Then make the observed input available in the hypothetical scenario | Aligned and available; aggregate consistent, interpolated | No estimation, estimator validation or clinical recommendation follows |
| Instead supply an alternative relevance rule saying this observation is not required | Aligned; not_required_for_this_estimand, while recorded state remains unavailable | The alternative target still needs clinical judgment; absence has not become availability |
| Change only outer support to proposed | Admission proposed_refused, even though raw and effective aggregate codes are both unresolved | Ordinary outputs cannot treat the proposal as accepted |
| Change only strategy label from treatment_policy to hypothetical, keeping all explicit rules | Same relevance, plan mismatch and missing-input conclusions | Strategy vocabulary supplies no hidden data rule or estimator |

Observed and imputed modes are retained separately. The available imputed value does not satisfy the declared observed-measurement requirement. No adopted estimator dependency was supplied, so this walkthrough does not claim an estimator conflict or infer validity of LOCF. The operator retains `estimation: not_computed` throughout. These scenarios say nothing about actual missingness or medication use in the source trials.

The channel-local metadata preserves required relevance separately from the plan mismatch and unavailable-input causes. In the proposed-support case it explicitly gates effective channel claims and retains their raw states. No result is classified as settled clinical truth merely because its arithmetic or representation is internally consistent.

The final `interpretations` request compares the required/stopped scenario with the aligned/available scenario. The former frame is unresolved; the latter is compatible. A deliberately unencoded clinical-appropriateness question remains UNDETERMINED in both. Compatibility is not recommendation, and complete supplied refs do not constitute clinical validation.

## Verification and handoff

Ten requests ran through separate real CLI and MCP processes, with complete parsed-document equality after removing only MCP's tool wrapper. The runtime receipt fingerprints76 existing package files and checks them before and after calls; all remained unchanged and no files were added during the run. The local report passes `trialledger verify`, which establishes reproduction from retained evidence, not registry truth or clinical interpretation. The complete requests and canonical results are retained without shortened snapshots or outputs.

The first helper run's available-observation revision retained an obsolete ref label saying unavailable; that label was corrected to available, and all ten final pairs were rerun. This was an input-quality repair, not a production failure.

`working-brief.md` is the clinical decision list. Remaining evidence gaps include the full rescue/discontinuation policies, endpoint observation and imputation conventions, intended new-study population and comparator, and target-specific required inputs. The system does not fill those gaps from phase, strategy name, equal denominator, study completion, or the assistant's domain expectations.
