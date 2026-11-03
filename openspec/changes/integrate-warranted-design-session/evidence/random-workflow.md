# Random clinical workflow check

This check followed the first documentation/design draft, using the founder's requested model action. It is not CI and does not validate unbuilt session behavior. Complete source runs and requests/results are retained under `holdout-run/`; `holdout-receipt.json` records exact identities.

## Question and selection

For a proposed first-line advanced EGFR-selected NSCLC trial, which completed Phase 3 osimertinib studies actually address the same treatment setting, and what mutation/prior-therapy choices remain?

The harness resolved/previewed `--drug osimertinib --condition 'Non-Small Cell Lung Cancer' --phase PHASE3 --status COMPLETED`, then gathered all six matching studies. Before reading selected records, a random seed was written: `4492926297228073722`. Sampling three IDs from the sorted complete pool selected, without replacement:

- `NCT05015608`
- `NCT02474355`
- `NCT02296125`

The full pool and selection procedure are retained in the receipt. This is a small within-query sample, not a representative validation set. No trial was replaced because it complicated the question.

## Reading the actual clinical units

Complete eligibility passages, structured population fields, summaries and arms establish the documentary differences below. The clinical encodings remain proposed readings, not confirmed interpretations or a recovered whole protocol.

| Study | Source content relevant to comparison | What must not be flattened |
|---|---|---|
| NCT05015608 | Advanced disease after first-line EGFR-TKI progression, MET amplification after progression, T790M excluded, ECOG 0 or 1, combination versus chemotherapy | Not the same setting as a treatment-naïve trial; a combination is not osimertinib alone |
| NCT02474355 | Prior EGFR-TKI, T790M required, additional lines may have occurred, WHO PS 0–2, single-arm treatment | Prior TKI does not establish exactly one prior line; a Phase 3 label does not establish a randomized comparison |
| NCT02296125 | Treatment-naïve for advanced disease, prior adjuvant/neoadjuvant therapy permitted, prior EGFR-TKI excluded, WHO PS 0–1 | Advanced-treatment naïvety is not never-treated; WHO remains WHO; qualifiers on stability and CNS metastases remain part of the complete source |

The search returned six genuine matches, but drug/phase/status membership did not establish a common first-line comparison cell. T790M has opposite forces in two sampled records. The summaries and arms expose intervention-role differences before any frequency claim is useful.

## Run through the current reasoner

Three `source_assertions` requests supply each complete raw study, exact digest, the whole eligibility passage anchor and an explicitly proposed setting/marker/PS reading. No submitted reading is admitted to the fixed floor.

- All three direct structured minimum-age queries are `ENTAILED` from registered age.
- In the proposed NCT05015608 frame, prior EGFR-TKI is required, T790M is refuted and ECOG 2 is refuted.
- In the proposed NCT02474355 frame, prior EGFR-TKI and T790M are required. “Must everyone be WHO PS 2?” is undetermined, as expected for a 0–2 restriction: it is not an assertion that everyone has score 2.
- In the proposed NCT02296125 frame, prior EGFR-TKI, prior systemic therapy for advanced disease and WHO PS 2 are refuted by the supplied readings.
- The fixed floor leaves each of those prose-derived questions undetermined. The prepared source bridge preserved the distinction between exact clinical consequences inside a frame and unconfirmed meaning.

The typed subset deliberately does not encode every relation. For example, a generic prior-EGFR-TKI predicate does not automatically imply the separately named prior-advanced-systemic predicate. That residual is a representation/binding task, not proof that the source omitted treatment history. The complete source remains beside the selected assertions.

## Revision

Withdrawing only the PS assumptions from the NCT02296125 proposed reading changes its PS-2 result from `REFUTED` to `UNDETERMINED`. Its prior-TKI and prior-advanced-systemic results remain refuted within the frame; the independently fixed adult-age answer stays entailed. The source record is unchanged. Today this revision is a separately prepared full request; the proposed session will own that replay and the consequence diff.

## Corpus handoff and the retained refusal

The first corpus request supplies known structured age features, proposed treatment-history features and `typed: false`. It is refused with `elements_without_typed_premises:0`. Reading the complete validator and frequency/admission consumers shows why: the structural flag contradicts the presence of an already typed age element. It is not a completeness certificate, and accepted feature standing is a separate question.

The second request records `typed: true` precisely because an eligibility element has been typed. It leaves trial-wide standing, treatment-history features and comparability unconfirmed. The direct age features retain their separate known support. This is a corrected declaration with an explicit reason, not a clinical premise promoted to make the request pass.

The actual result counts **3 of 3** records encoding minimum age 18 Years, with no treatment-history statements admitted. The pending prior-TKI-required feature has two candidate statements and the pending exclusion one; neither becomes a factual count. All three trials remain in N. The association stratum abstains with pending-support/class-membership reasons.

This identifies a small integration task: the session adapter should derive the structural flag from prepared features and derive admission from their support/origin. It does not justify removing the public guard or declaring whole eligibility typed. The initial refusal and corrected result are both retained.

## Clinical handoff

For the new first-line design, the sampled records do not form a homogeneous set of precedents. The next useful choices are the prior-treatment context, marker-selection role and whether PS 2 should be permitted under the chosen scale. The MET-amplified and T790M-positive post-TKI populations are context, not automatic eligibility templates for first-line disease. Prior adjuvant therapy needs its own policy; a ban on prior advanced treatment does not settle it.

No operation has selected the best clinical option. The system has supplied exact conditional checks and preserved the distinctions needed to ask the consequential questions.

## Findings carried into the plan

1. Keep retrieval membership distinct from clinical comparison membership.
2. Preserve prior-treatment event/context rather than an undifferentiated treated/untreated flag.
3. Preserve marker required/excluded roles and combination versus single-agent intervention identity.
4. Derive redundant structural metadata; keep source coverage and premise admission separate.
5. Make revision replay and its independent/dependent consequence report a computed handoff.
6. A selective encoding leaves representation tasks visible; it must never be described as all clinical information being absent or automatically resolved.

Six distinct public CLI request/result pairs are retained for this check: four complete source/interpretation requests, one refused corpus request and one complete corrected corpus request. Source/workbook replay verified. Coordinates were not used to turn unconfirmed treatment-history readings into known settings; a clinician-confirmed or formally warranted setting binding remains an explicit next step. No new runtime code, mutation pin or complete-thesis validation is claimed.
