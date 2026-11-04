# Pediatric allergy-immunotherapy design exercise

The comparison records are real fresh registry pulls. All draft restrictions and the later selection below are explicitly simulated choices, not a clinical recommendation or an authenticated exchange with a clinician.

The question is whether a lung-function requirement should apply to everyone in a pediatric rhinitis study or only to participants who also have asthma. The source comparison is deliberately retained as sampled: BioCSI-2 (NCT01380327) is a pediatric Phase 1/2 cockroach-immunotherapy trial; NCT07345442 is a Phase 1 corticosteroid nasal-spray study in healthy adults. Sharing the allergic-rhinitis search does not make these populations or treatments interchangeable.

## Decision list

1. **Who should the lung-function requirement cover?** BioCSI-2's eligibility passage introduces asthma-specific conditions with “For those with asthma,” followed by the FEV1 and rescue-medication wording. See the complete eligibility text in the source record and its passage at `/studies/1/criteria/3`. My source reading is that these conditions apply to the asthma group; the tool does not establish that clinical reading merely by copying its heading. A deliberate universal counterreading was kept as a separate hypothetical frame. For a rhinitis-only question about FEV1 of 70% predicted, those frames return, respectively, outside the stated cohort and ruled out. The combined answer preserves that exact difference instead of silently choosing one reading. Neither frame is promoted to a registry fact. Selecting the asthma-only reading still leaves an explained outside-cohort answer.

   In the **simulated new draft**, we explicitly represented rhinitis without asthma, age 5–17 and a conditional FEV1 requirement for asthma. The completed checks allow FEV1 values on either side of 80 for that represented rhinitis-only group. The subsequent **simulated revision** deliberately applies the FEV1 requirement to everyone: FEV1 of 70 is then ruled out by that new policy. This change is the draft choice, not a correction of BioCSI-2. The age 18 profile remains ruled out by the unchanged age restriction.

   **Next useful action:** settle whether the new study's spirometry requirement is for the asthma subgroup or for everyone, and separately encode the rescue-medication condition. These checks concern the represented restrictions, not complete enrollment eligibility.

2. **What are the preliminary-dosing and maintenance populations?** BioCSI-2 documents low-dose and high-dose SLIT, with preliminary escalating doses before the three-month treatment course. The intervention descriptions distinguish up to three versus seven escalating doses and different daily schedules. The healthy-adult nasal-spray source describes single dosing followed by repeat dosing and reports36 participants; its six arm descriptions must not be treated as six disjoint twelve-person populations. Neither similar arm labels nor arithmetic establishes whether these are the same people across stages.

   **Status:** open. No individual membership, stage correspondence or complete escalation/stopping algorithm was inferred or validated in this exercise. **Next useful action:** obtain the protocol's stage-membership and safety-review rules before copying an escalation procedure. The workbook supplies the documented descriptions without manufacturing those rules.

3. **Which exclusions prevent reassessment?** A separate BioCSI-2 paragraph explicitly introduces a group of exclusions with wording about not being reassessed. The filtered viewing workbook preserves that full local label beside the English-language exclusion at `/studies/1/criteria/26`; the source label spans 2924–3071 and the passage 3073–3106. This is copied structure, not an automatically encoded screening policy.

   **Status:** documentary wording available; any reusable screening rule still needs an explicit reading/adoption. **Next useful action:** review that paragraph with the surrounding criteria rather than relying on an isolated filter row.

4. **What does the outcome establish?** BioCSI-2's planned primary measure is change in cockroach-specific serum IgE over three months, and its description explicitly leaves clinical significance unclear. This exercise did not analyze the posted results or establish clinical efficacy. The corticosteroid source's safety/PK endpoints and clocks are different and were not substituted for those biomarkers.

   **Next useful action:** choose the new study's clinical or biomarker objective, then specify its population, variable and assessment schedule. A registry time frame alone is not a complete schedule.

## What this workflow identified and left open

Actual CLI acquisition found both selected IDs, and the workbook verified from retained sources. Actual CLI/fresh MCP comparisons for this case are recorded in transport-receipt.json. Complete baseline/revision requests and results are retained, with full source snapshots, fresh prior replay and unchanged source children.

The local-label feature identified a useful non-reassessment label without inventing clinical scope. A concrete remaining presentation limit is visible too: the nested FEV1 passage carries the generic Inclusion label, while its asthma antecedent is in an earlier bullet. Literal heading context is not a list-ancestor/scope parser. The full preceding passage remains available, and the operator must retrieve and translate that dependency explicitly.

The demonstrated coherence is local: the scope choice changes its FEV1 consequences while the independent age answer stays fixed. Clinical comparability, complete escalation rules, complete eligibility, clinical significance and the full protocol remain open or untested. There is no overall correctness score.
