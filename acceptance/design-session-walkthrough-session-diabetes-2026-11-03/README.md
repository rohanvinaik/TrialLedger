# An observational diabetes design session with a revision

The question and retention policy were declared before acquisition: what age restrictions and follow-up definitions do sampled metformin observational records actually supply, and which downstream answers change when a working brief revises a population or age premise?

This is a model-operated acceptance walkthrough of the managed session, using actual source snapshots and a separate **invented new-study design scenario**. No real clinical user made or confirmed a choice. The `user_choice` origins and `selected` entry below are explicitly labelled invented acceptance fixtures; they are not an attribution to the person running this project.

## The evidence stays awkward

The metformin / Type2Diabetes / OBSERVATIONAL / COMPLETED query returned23 IDs. No phase filter or therapeutic-phase label was imposed. Seed2556818910469820462 selected NCT00745433, NCT01318564 and NCT02475499 before content reading; the full23-study pool was acquired, with no replacements. All selected protocol identification, status, description, design, eligibility, arms/interventions and outcomes units were read. None has posted results, so selected participant flow and baseline counts are unavailable. Exact source identities, query, complete pool, seed, retention and capture receipts are retained.

`source-reading.md` keeps the substantive distinctions:

- NCT00745433 is a prospective add-on study with physician-discretion dosing and outcomes after12–20weeks. That does not automatically specify one exact visit or total study duration.
- NCT01318564's design field says OBSERVATIONAL, while its description says random assignment to packaging groups. Arm descriptions describe weekly crossover, while other wording describes Day1 toMonth3. These source channels remain unresolved; the session does not silently recode the study, change the schedule, or equate package opening with ingestion.
- NCT02475499 has a general structured minimum age18 but separately says Ontario patients are65+ because of prescription-data availability. Its base-entry, study-entry, exposure-lag and follow-up-start definitions are different clocks. Detailed follow-up starts entry+365days, while the outcome frame says from entry. Neither is erased or made equivalent by this age-focused acceptance case.

## Three known historical facts and one proposed reading

Three complete standalone source-assertion requests compile each record's structured minimum18Years. All entail the exact age≥18 restriction. All leave a universal age≥65 requirement undetermined. This concerns the encoded age restriction, not overall patient eligibility.

The managed session retains each complete source snapshot and compiles the same facts into historical analyses. Their historical target scopes identify the actual digest-bound registry study; they are never projected into the new-study draft as if comparator criteria automatically applied.

A separate source-interpretation premise reads NCT02475499's Ontario-specific age65 wording. It is bound to the actual description address, scoped to cohort_ref Ontario, and **proposed**. Ordinary Ontario and general-population queries retain `proposed_refused:Ontario-age-reading` and remain UNDETERMINED. General age18 remains known in a separate analysis. This demonstrates refusal and preservation, not a claim that the registry settled the assistant's encoding of the Ontario cohort.

## An explicitly invented draft choice

The invented initial draft requires age≥18. Two declared alternatives ask whether the represented age restriction permits65+ and below65. Both are feasible, and an actual completed pairwise distinguishing entailment is retained. The resulting decision is `design_choice`. This establishes distinct possibilities under this declared age restriction; no drug, disease or full eligibility recommendation follows.

In the invented second snapshot, the scenario user chooses a minimum age65 and selects the65+ alternative. The new snapshot carries the exact parent-session digest. The revision request includes the complete previous session and digest-checked previous result; the operation freshly replays both snapshots.

The older query becomes ENTAILED; the below65 query becomes REFUTED. The decision becomes `chosen_by_person` **inside the invented fixture only**, with its invented origin and selection basis intact. A chosen option passing one age restriction does not certify a protocol or determine what an actual person should choose.

The revision diff preserves three unchanged source objects and all five historical analyses, including the two proposed Ontario checks. It marks the draft age premise and four draft-dependent analyses changed. A derived ordinary adult assertion is also replayed through its producer analysis. Its logical answer stays ENTAILED under either age floor, but its effective support changes and the downstream derived recheck is marked changed. Full dependency edges remain visible; minimal proof membership is not used as a cache invalidation rule.

## What was verified

Five complete requests ran through separate actual CLI and MCP processes: three source-assertion checks, the baseline session and its revision. Complete parsed documents matched after removing only MCP's tool wrapper. The session results retain the full prepared child requests/results, their digests, actual distinction request/result, effective origins, projection ledger, dependency graph, diff and freshly replayed previous snapshot. No child request/result has been shortened for the packet.

Every final child envelope completed. The revision's `previous_fresh` matches the baseline snapshot exactly. The three standalone source-age requests replay identically after the draft revision. Runtime fingerprints cover all existing package files before and after calls; report verification separately establishes reproduction from retained source bodies and workbook, not registry truth.

Helper repairs were retained honestly: the first draft did not reuse identical alternative query serialization, used a mismatched assertion ledger ID, and initially guessed a cohort/context shape. The discovered exact forms were applied. A helper summary adapter also assumed source-assertion child layout for session child envelopes and was corrected. All five final CLI/MCP pairs were rerun. These are translation/helper corrections, not production failures.

`working-brief.md` is the clinical handoff. This walkthrough exercises the managed session on actual observational sources; it does not validate all observational study paradigms, reconstruct unposted results, resolve the conflicting schedule/design channels, or make a clinical choice.
