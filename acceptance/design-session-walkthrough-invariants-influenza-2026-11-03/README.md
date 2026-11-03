# Phase 2 influenza: early relative to which event?

The question was declared before acquisition: **For a proposed Phase 2 early influenza-treatment study, which compared population/onset and assessment definitions matter, and what follows when one temporal/eligibility premise changes?** A useful answer identifies the population and event being restricted, the consequences of a draft option, and the evidence still needed. No clinical user supplied confirmation or chose a policy in this investigation.

This is the fresh model-operated workflow following the invariant-test increment. It exercises existing threshold, scope and temporal constructs across phase and disease content. It does not validate a new dose-escalation, crossover, cluster or other trial-design paradigm.

## Acquisition and sample

The public TrialLedger preview and gather used **oseltamivir + Influenza + PHASE2 + COMPLETED**. The complete identifier preflight found 17 records, within the predeclared maximum of 30. All 17 were gathered. Seed **4136338864088426196**, recorded before selected-content reading, selected NCT01179919, NCT00867139 and NCT00453999 without replacement from the complete sorted pool. No awkward study was replaced. `selection.json` preserves the entire pool, exact query, identifier locator, response identity and sampling procedure.

Retention was declared before acquisition in `preflight.json`: the full report, raw bodies, workbook, lookup cache, helper and duplicate transport wires remain outside Git at `/Users/rohanvinaik/trialledger-runs/invariant-influenza-20261103`. Complete source snapshots needed by reasoning requests remain in those requests. `source-inventory.json` records the exact snapshots, raw batch fingerprint and full units reviewed. The batch capture time is a filesystem write time, not an independently recorded network-response timestamp. The registry data timestamp is separately retained in the gather manifest.

The complete selected identification/status, eligibility, design, descriptions, arms/interventions and registered outcomes were read, followed by the complete participant-flow and baseline modules. The full local record/workbook passed actual `trialledger verify`: preservation and reproduction are checked; clinical meaning is not certified.

## What the actual records make different

| Study | Documentary context | Consequential distinction |
|---|---|---|
| NCT01179919 | Healthy morbidly obese adults, single-group multiple-dose PK; structured phases PHASE1 and PHASE2; age18–50; Cockcroft–Gault estimated creatinine-clearance exclusion below50mL/min. Flow21 started/19 completed; baseline21 dosed. | A Phase2 influenza search does not establish infected-patient efficacy comparability. The PK endpoint is steady-state exposure over6days. One reported Protocol Violation does not identify an entry failure. |
| NCT00867139 | Immunocompromised influenza patients; randomized and open-label pathways; randomized eligibility says age≥7 while the younger1–6 pathway is open label. Illness onset is no more than5days before **diagnosis**. Flow2/1/4 starts; open-label completion3, with one withdrawal onday5. | The study-wide population is not the randomized population. Flowgroup descriptions say “over7” even for a group labelled open label, while baseline explicitly describes younger open-label children. Those source tensions remain; no boundary repair or forced group equivalence is performed. |
| NCT00453999 | Hospitalized adults with serious/potentially life-threatening influenza; randomized peramivir versus oseltamivir; illness onset≤72hours before **presentation**, with an explicit fever-or-respiratory-plus-constitutional onset definition. Flow137 starts; baseline ITT137. | Presentation, randomization and first dose are different events. Baseline duration categories concern randomization. A positive screening test differs from later confirmation: baseline reports15 not confirmed, which does not by itself establish15 eligibility violations. |

Assessment definitions also differ. NCT00867139's primary AE follow-up is30days after the final dose, with PCR days1,3,5,7,9,15,20,28 “if applicable.” NCT00453999's primary clinical-stability endpoint is followed for14days and censors at the last nonmissing assessment, inpatient **or outpatient**. Its symptom-change endpoint excludes missing data. Neither endpoint horizon automatically supplies a mandatory visit schedule, and hospital discharge does not automatically end endpoint follow-up. No efficacy comparison or new-trial target is inferred.

## Six actual request/result pairs

Each complete request ran through a separate CLI process and a fresh stdio MCP process. The complete parsed results matched after removing only MCP's `tool` wrapper field. `runtime-receipt.json` records commands, exits, code hashes and pair fingerprints. `finding-summary.json` is a convenience projection; complete canonical results remain authoritative.

1. **PK age and renal reading.** The direct structured source rules refute age51 with known standing. Renal45mL/min is unaddressed by that fixed floor, but refuted conditionally under the separately proposed reading of the named Cockcroft–Gault restriction. No screening event was attached to this renal rule: the selected clause does not specify one. A draft input initially attached screening; that assumption was removed and all six pairs rerun before finalization. This was an input-fidelity repair, not a runtime defect.
2. **Immunocompromised randomized context.** Under the proposed randomized-arm reading, age6 is refuted; six days of illness at diagnosis is also refuted under its separate onset reading. The full source remains unchanged.
3. **Remove the randomized application context.** Age6 reopens with `open_scope:cohort_ref:NCT00867139:randomized-arms`; it is not thereby allowed. The frame becomes unresolved. Its illness query retains raw REFUTED but effective UNDETERMINED because that frame is unresolved. This exposes the actual whole-frame gate instead of presenting its raw answer as admitted.
4. **Presentation plus invented immediate dosing.** The source-derived adult floor remains ENTAILED/known. A proposed source reading supplies onset-to-presentation [0,72]hours. A separately invented operational option requires first dose at presentation. Adding the hypothetical course “first dose at80hours” makes that proposed frame **incoherent**, with a temporal `conflict`. It does not refute the source record.
5. **Revise only the operational delay to0–24hours.** The same source presentation reading plus that invented delay gives first-dose bound [0,96]hours. The hypothetical80-hour first dose is consistent; under that claim the graph tightens presentation to56–72hours and delay to8–24hours. This is a computable operational consequence, not a recommended treatment delay.
6. **Leave the first-dose delay ceiling unknown.** First-dose upper bound remains null. The80-hour claim is compatible; no finite deadline is manufactured from the72-hour presentation restriction alone.

In all three timing versions the independent fixed adult answer remains ENTAILED/known. The incoherent version withholds its frame's age answer while preserving that separate fixed result and its deciding age rule.

The scalar query “illness duration80hours at first dose” remains `no_constraint_mentions_query`: no scalar first-dose assertion was supplied. The temporal graph's bound and explicit course-compatibility check are the computed answers. There is no automatic graph-to-measurement projection. The two representations are not silently equated.

## What remains unresolved or unencoded

- **Direct source-age coverage:** NCT00867139's exact structured minimum is `1 Year`. The public source compiler reports `unsupported` and produces no fixed age assertion. The record retains the field; it is not normalized to `Years` in the request. This is a concrete direct-rule coverage gap for later warranted extension, not absent age information.
- **Population and pathway:** the randomized/open-label age boundaries, asthma/severity alternatives, immunocompromise definition and monotherapy-failure route are not a fully compiled stage model. Their source wording remains intact.
- **Timing:** diagnosis, presentation, randomization, first dose and final dose require explicit relationships before transferring windows. No days-to-hours conversion or diagnosis-to-presentation identity was assumed.
- **Definitions and missingness:** primary endpoint censoring, symptom-score components, full analysis populations, “if applicable” PCR visits and all renal/history exceptions remain documentary context beyond these small checks. No claim of complete endpoint or eligibility encoding is made.
- **Protocol failure:** the healthy-volunteer PK flow reports one Protocol Violation. Its target and the maximum eligibility-exception allowance remain unknown; no negative eligibility specification was manufactured.
- **Comparability:** matching drug, condition and phase did not produce a common population or endpoint. The sample supplies design questions, not a prevalence estimate or evidence that one design is best.

## Clinical handoff

| Decision | Evidence and computed consequence | Next action |
|---|---|---|
| Which population are we designing for? | Healthy obese PK, immunocompromised pathways and hospitalized serious influenza are different source populations. | Specify infected status, severity, immune status and intended treatment pathway before selecting comparators. |
| Early relative to what? |≤5days beforediagnosis and≤72hours beforepresentation are separately sourced readings. First-dose timing needs another relation. | Define onset, reference event and a separate operational dosing deadline. |
| Which age rule applies to which pathway? | Randomized age6 is ruled out under the proposed≥7 reading; removing that cohort context reopens the question. | Resolve the intended pathway and boundary; retain the source's “over7”/“≥7” tension. |
| How do discharge and treatment completion affect assessments? | Clinical-stability follow-up can use outpatient assessments; AE follow-up is anchored to finaldose. | State the endpoint-specific follow-up and censoring plan rather than substitute hospital or treatment duration. |
| Which renal measure and event apply? | The PK reading names Cockcroft–Gault; its clause does not state a measurement event. Other selected records use different renal restrictions. | Choose the measure, unit and assessment event explicitly; do not equate renal metrics by a shared number. |

`working-brief.md` retains the concise decision list. All choices remain open; no clinical user's acceptance is claimed.

## Replay and limits

Replay any file under `requests/` with `trialledger reason --request FILE` under the recorded writing version. Those complete inputs support layer-two replay without a registry re-fetch. Full layer-one workbook verification additionally needs the local retained report and source packet. Re-fetching the same NCT ID is a new observation, not guaranteed historical-byte recovery.

This workflow supplies evidence about the exercised user-facing paths and their limits. It is separate from Detective pins and the full test gate, and does not establish automatic clinical encoding, clinical recommendation validity or complete protocol generation.
