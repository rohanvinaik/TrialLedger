# Post-documentation walkthrough: what does the asthma therapy clause require?

Question declared after DOCSREADY and before acquisition: for a proposed Phase3 asthma study, how do sampled records distinguish background controller treatment, rescue/as-needed treatment and eligible populations, and what should change when the representation of those roles is revised?

The fresh budesonide/Asthma/PHASE3/COMPLETED query returned78 IDs, above the predeclared whole-pool maximum30. Seed692001714306634475 selected NCT00419952, NCT01360021 and NCT01001364 before their content was read. A separate explicit-ID report acquired exactly these three, without replacement. The complete pool, query, source-vocabulary resolution, body fingerprints and acquisition timestamps are retained. All selected protocol clinical units were read, plus complete flow/baseline units where posted. NCT01001364 has no posted results. Full raw bodies/workbook remain local; required source snapshots are complete inside requests.

## The real clinical question

NCT01001364's eligibility wording describes current inhaled corticosteroids “associated or not to” long-acting beta2-adrenergics and relief medication. Does the optional phrase apply only to one associated therapy, or does it leave relief use unrequired too? That affects whether a person without current relief use is ruled out by this particular criterion. It does not decide their full eligibility, what treatment is appropriate, or whether they should have access to rescue treatment.

The other sampled studies supply context without settling this reading:

- NCT01360021 requires documented daily inhaled corticosteroid use for at least3months, and measures rescue-medication use separately over a12-week treatment period/14-week recording period. Its eligibility and daily outcome diary are different channels. Baseline contains21 participants aged12–under18; no cross-study population correspondence is assumed.
- NCT00419952 studies self-reported African American participants with moderate/severe asthma requiring inhaled corticosteroids. Flow describes a2-week run-in with as-needed rescue. Entry excludes those requiring systemic corticosteroids, while later exacerbations are defined using systemic treatment and/or emergency/urgent care/hospitalization. Entry restriction and post-entry event definition are not silently conflated. Its title and arm text also use different printed dose-unit wording; it is preserved, not normalized by medical expectation.
- NCT01001364 separately describes clinical stability for1month, current inhaled corticosteroid use, asthma symptoms for6months, twice-daily treatment for12weeks and outcome frames of4months. Clinical stability does not itself establish an unchanged controller dose, and those time channels are not collapsed into one study length.

Full source facts and unresolved channels are recorded in `source-reading.md`. Shared search membership is not a declaration of clinical comparability.

## What is fixed, what is a reading

Three actual source-assertion requests compile the structured minimum age12Years. Each entails age≥12 and refutes age11 for that represented age restriction. Free-text medication meaning is not mechanically compiled.

For the focal NCT01001364 source, two exact source-anchored readings are retained as **proposed**:

| Reading | Current inhaled corticosteroid use | Current relief use | No current relief use | Daily relief use |
|---|---|---|---|---|
| Relief is required current co-treatment | Required conditionally | Required conditionally | Ruled out conditionally | Unresolved |
| Current ICS required; relief requirement left unaddressed | Required conditionally | Unresolved | Unresolved | Unresolved |

Both frames are compatible with the represented fixed floor. The second frame does not assert that rescue is forbidden or unnecessary; it leaves that requirement unaddressed. Neither frame claims to encode all treatment alternatives, LABA combinations, routes, doses, prior use or exceptions in the source. Current use is not daily use. No reading has been confirmed by a clinical user.

The fixed source floor still entails age≥12 with known standing outside either frame. Frame-local answers retain proposed standing and a conditional-on-interpretation guarantee. Ordinary entailment refuses the unconfirmed relief-required premise with `proposed_refused`, rather than treating one reading as established.

## The managed revision adds the missing question

The initial immutable historical session contains the first source reading. The revision **adds the rival reading**, preserving the original; it makes no new-trial adoption and no user-choice attribution. The source-study projection supplies the exact retained study and digest. Both source-reading arrays, exact anchor values, proposed assumptions, queries and complete child results remain in the replay record.

Fresh replay changes only the conditional-reading analysis. The original source snapshot, direct age premise/analysis and ordinary proposed-premise refusal remain unchanged. `previous_fresh` equals the baseline snapshot exactly. The revised analysis retains both compatible readings and their different effects on current relief use. This is a representation improvement with clinical consequences, not a numeric threshold rename or a fabricated source update.

The session has no declared computed design-choice entry because the unresolved object is a translation question. The human-facing decision list makes that question explicit and preserves the consequences; the system does not choose its reading for the person.

## Verification and scope

Reasoning execution began after OVERVIEWREADY. Seven complete requests ran through separate actual CLI and MCP processes: default discovery, three source-age checks, the two-reading source bridge, and baseline/revised sessions. Complete parsed results match after removing only MCP's tool wrapper. Source-age requests replay identically after the reading revision. All existing runtime files were fingerprinted before and after calls, without changes; no new runtime file appeared during execution. The local report passed verify, establishing reproduction from retained evidence, not registry truth.

A preparatory managed request redundantly supplied expected_digest beside source_study projection and was correctly refused as source_study_collision. Reading the complete request-preparation function established that this projection owns both study and expected_digest. The duplicate was removed and all seven final pairs rerun. No production behavior was changed. This input-contract finding is now clarified explicitly in README/AGENTS: source_study owns both study and expected_digest; omit both from analysis parameters. Runtime behavior was unchanged. A separate refused-contract replay reconstructs the preparatory condition from the successful request by restoring only the redundant digest; its complete CLI/MCP refusal results match. The original overwritten wire bytes are not claimed to be retained. Seven successful pairs remain the clinical acceptance measurement; this additional refusal is an input-contract check.

The portable packet keeps full required snapshots, prior session/result, child requests/results, provenance and revision diff. Raw report/workbook and duplicate wires stay outside Git. No clinical confirmation, efficacy interpretation, complete-protocol claim or treatment recommendation is made. `working-brief.md` is the clinical handoff.
