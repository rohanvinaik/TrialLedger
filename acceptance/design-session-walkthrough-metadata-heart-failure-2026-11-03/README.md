# Heart-failure model walkthrough: result meaning survives the handoff

This is an executed model action checking the result-metadata increment in a different clinical category. It is not a clinician-confirmed brief, a complete eligibility analysis, or a recommendation. No clinical choice was made on the person's behalf.

The question declared before acquisition was: **For a proposed adult heart-failure trial considering LVEF 45%, how do sampled completed phase-3 empagliflozin records constrain EF range, background therapy and comparability?**

## Acquisition and source boundary

The actual public harness preview used `--drug empagliflozin --condition 'Heart Failure' --phase PHASE3 --status COMPLETED`. The resolved scope and exact ID preflight are retained. The complete pool had nine identifiers, below the predeclared 30-study gather limit. Seed **3968812432375741721** was recorded before reading selected study content; sampling without replacement from the sorted complete pool selected NCT03332212, NCT03057977 and NCT03448406. The full gather read all nine records.

`selection.json` retains the question, complete pool, seed, selection rule, exact preflight URL and source hashes. `raw-studies.json` is one byte-exact retained registry batch containing all nine studies. Each source-assertion request also carries its selected complete study because the public operation requires it. `gather-request.json`, `gather-resolution.json`, `gather-scope.json`, `gather-manifest.json` and `gather-fetches.json` retain acquisition accounting.

The complete eligibility/population, arms and registered primary outcomes of the three selected studies were read. Clinical wording below is a reading of that record. The typed EF restrictions, conditional medication rule and partial endpoint-input definition remain **proposed interpretations**. Anchoring a reading to an exact passage and digest locates it; it does not independently certify its meaning.

The full original reference report remains at `/tmp/trialledger-heart-failure-metadata-20261103`. Actual `trialledger verify` exited 0: the record and workbook reproduce from retained sources. This checks derivation, not clinical interpretation. The trimmed acceptance packet is not a complete report folder: the workbook and lookup cache were not copied here. See `verification-receipt.json`.

## What the source says, and what the executed reasoning settles

All source addresses below are within the selected study's `protocolSection`. The requests retain the complete study, expected digest, whole eligibility anchor and exact span. Full source details stay available in `raw-studies.json`.

| Record and scope | Documentary EF restriction at `eligibilityModule/eligibilityCriteria` | Actual conditional query result |
|---|---|---|
| NCT03332212, named cohort A | LVEF ≤40%, ECHO at screening | EF45 REFUTED; EF40 UNDETERMINED with `undecided_by_constraints` |
| NCT03332212, named cohort B | LVEF ≥50%, ECHO at screening; also no previous LVEF ≤40% | EF45 REFUTED; EF40 REFUTED |
| NCT03057977 | LVEF ≤40%; this passage does not specify an EF measurement method or event | EF45 REFUTED; EF40 UNDETERMINED with `undecided_by_constraints` |
| NCT03448406 | LVEF >40%, echocardiography at Visit 1; also no prior LVEF ≤40% under stable conditions | EF45 UNDETERMINED with `undecided_by_constraints`; EF40 REFUTED |

“Allowed but not required” here describes the encoded EF restriction only. It does not establish a patient's eligibility. Only the named present EF restriction is encoded in these cases; historical EF, biomarker thresholds, other criteria and any unposted criteria remain outside these requests. The two NCT03332212 requests check each named cohort separately; they do not assert that a declared candidate family exhausts every possible cohort explanation.

The fixed source-derived floor answers the structured general age question as ENTAILED, known and settled, using `registry-age-minimumAge` and `ctg-structured-general-eligibility-age:1`. Fixed EF queries remain UNDETERMINED with `no_constraint_mentions_query`: free-text clinical readings did not become fixed facts. The interpretation frames are compatible under the declared premises. Their decisive EF answers are **proposed/conditional**, while permitted alternatives remain **proposed/open**.

This general age result is not a full regional eligibility rule. NCT03057977's prose expressly requires age ≥20 for Japan, while its structured minimumAge is 18 Years. NCT03448406 also refers to local consent legislation. Both NCT03057977 and NCT03448406 say further criteria apply. These qualifiers remain relevant even when a structured age value is mechanically available.

## Background treatment: preserve the conditional

NCT03448406 says **if oral diuretics are prescribed** to control symptoms, the dose must be appropriate and stable for at least two weeks before Visit 1. The saved reading encodes medication use as the applicability condition of the stability restriction, using the same explicit Visit 1 event reference for the matching questions.

The executed frame returns UNDETERMINED with `undecided_by_constraints` for both “oral diuretics required?” and “two weeks of stability required unconditionally?” Metadata marks both open, proposed and computation-complete. The conditional does not entail its own antecedent. No diuretic-use premise was supplied, so this run does not compute a conclusion for an actual diuretic user.

The other records do not supply one interchangeable regimen. NCT03057977 requests appropriate HF therapy stable for at least one week before Visit 1. NCT03332212 cohort A specifies appropriate HF therapy stable before Visit 1 and through screening, with a separate diuretic timing exception; cohort B says oral diuretics, if prescribed, should be stable before Visit 1 and through screening. Those documentary differences were read and retained, not silently adopted into the new draft or collapsed into a common drug list.

## Endpoint definition: imputation is a separate permitted information channel

NCT03448406's complete `outcomesModule/primaryOutcomes/0` defines baseline-to-week-12 change in six-minute walking distance. It expressly says an imputed value is used if week-12 data are unavailable. It also specifies same-day longest measurements, the last pretreatment baseline measurement, zero for a participant present but not performing the test, and rankings for missing data, clinical events and death.

The saved proposed input definition is deliberately partial: baseline observed plus either week12 observed **or week12 imputed** can supply its declared change input. The available/unavailable inputs are invented investigation premises, not this study's actual patient data. The executed dependency signal reports `consistent`, with the rule `ready` through baseline-observed + week12-imputed even though week12-observed is unavailable. The unavailable observed input remains visible. Its metadata is **proposed, complete, conditional**. No observed-only rule was imported from another teaching example.

This does not compute the endpoint value, validate an imputation method, apply its zero/ranking rules, or establish the availability of real participant data. The source definition and that unresolved modeling work are retained together.

The studies also use different primary endpoints: PCr/ATP by cardiac MRS at week 12 (NCT03332212), CV death/HF hospitalization with patients-with-events per 100 patient-years through up to 1040 days (NCT03057977), and week-12 six-minute walking-distance change (NCT03448406). Same drug, condition and registry phase do not establish endpoint or population comparability.

## Revise a hypothetical new draft and recompute

Two separate actual `interpretations` calls examine a new draft with an upper EF boundary of 40 versus 45. Both are clearly invented proposed alternatives, with no fixed source restriction silently adopted.

| Hypothetical new-draft restriction | Actual EF45 result | Effective metadata |
|---|---|---|
| EF ≤40 | REFUTED, proof `draft-EF-upper` | proposed / complete / conditional |
| EF ≤45 | UNDETERMINED, `undecided_by_constraints` | proposed / complete / open |

The revision allows EF45 under that restriction without requiring every participant to have EF45. It does not amend any comparator's record or record a clinical user's choice. Earlier and revised request/result pairs are retained separately.

## Computation limits and pending corpus information

The same NCT03057977 source request was also executed with an intentionally tiny bound of 1. Its frame becomes unresolved; its queries retain `resource_bound` (and, for frame queries, `interpretation_unresolved`). Effective metadata reports **limited / not_computed**, even for the otherwise known general-age premise. This is not the clinical answer “allowed but not required.” No `raw_result` override was emitted in these eight cases; they do not independently exercise every gate-override branch.

A separate actual corpus call admits only the directly sourced structured-age element per feature, leaving EF meanings and clinical comparability proposed. It reports three of three selected records stating `minimumAge=18 Years`, with a [1,1] statement interval. This describes the declared source feature and three-record set, not comprehensive eligibility or a standard of care. The records have one lead sponsor in this calculation.

The generic candidate EF-reading element has **0 admitted statements, 3 pending statements, 3 unresolved trials and interval [0,1]**. The computed accounting row is descriptive; its eligibility-frequency tier is open/unresolved. The admitted general-age frequency and tier are also descriptive rather than closure of a clinical design decision. Zero admitted statements is not zero source restrictions. Association work abstains with `pending_support`. Clinical readings were not marked known merely to obtain a corpus statistic.

## Decision list left for the person

| Decision | Evidence and computed consequence | Status |
|---|---|---|
| Which EF phenotype and measurement event should the new trial address? | Named source ranges differ. The hypothetical ≤40→≤45 revision changes EF45 from ruled out to allowed under that restriction. Method/event identities are not merged across trials. | Open clinical choice |
| Should prior reduced EF exclude a person whose current EF is above the selected boundary? | NCT03332212 cohort B and NCT03448406 expressly constrain EF history. Present EF alone does not encode this history. | Open choice; history rule not yet encoded here |
| What background treatment and stability interval should apply, and to whom? | Conditional diuretic use does not require treatment for everyone. The source regimens/times differ. | Open clinical choice |
| Which endpoint and permitted input definition do we intend? | Different registered endpoint families; the exercise source permits imputation. The partial dependency result is conditional and does not model its full analysis. | Open choice and modeling gap |
| Which comparisons are meaningful? | Random sampling guards this model action against handpicked records; it does not establish clinical comparability. Candidate clinical corpus features remain pending. | Open clinical choice |
| Are all local and unposted eligibility requirements available? | General age is structured; Japan/local-age qualifiers and expressly abbreviated criteria remain outside that floor. | Evidence/translation gap |

## Replay and audit

`replay.py` constructs eight requests using existing public schemas, runs **actual CLI and fresh stdio MCP** calls, and requires complete parsed JSON equality (excluding only MCP's tool wrapper field). It does not invoke an unbuilt session operation. Full request files, CLI results and MCP wire replies are retained under `requests/` and `results/`.

Run from the repository root:

```sh
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label heart-failure-walkthrough -- uv run python acceptance/design-session-walkthrough-metadata-heart-failure-2026-11-03/replay.py
```

`reasoning-receipt.json` records revision `a3987b05db21f0cf3f871cc36f272ddc516c1ec2`, before/after SHA256 values for the uncommitted `result_semantics.py` and `service.py`, source digest and all eight transport comparisons. The measured runtime/source files were unchanged during the final calls. `findings.json` projects the actual effective metadata rows, including deciding query IDs/warrants and corpus counts; complete results remain authoritative. Ruff check and format check passed for the owned replay helper.

After metadata review, all eight CLI/MCP pairs were executed again against the final phase-one metadata implementation. The final results and receipt replace the earlier wording; `before-review/` retains only the historical receipt and digest inventory, explicitly not a separately replayable old packet. No equivalence claim against discarded earlier full result bodies is made. The current corpus rows were inspected with their actual `descriptive` disposition.

Two source-fidelity corrections were made before the final replay: Visit 1 stayed explicit for NCT03448406, and NCT03057977 gained no invented echo method or assessment event. All eight pairs were rerun after those input corrections. This packet records the bounded walkthrough, not a runtime Detective pin, broad clinical validation, or the project's full verification suite.


## Retention and replay

Complete submitted reasoning requests and canonical CLI results remain expanded here, with the original clinical findings and source/version receipts. The original full packet, including duplicate wire captures, raw search bodies and historical replay helpers, is retained locally outside Git. See RESTORE.md and retention.json. Original paths described above may require that full packet.

The saved request files can be replayed directly with `trialledger reason --request FILE` under the writing version. This does not require a registry re-fetch. Full workbook/source verification additionally needs the complete original packet. Re-fetching the same NCT ID now is a fresh observation and does not guarantee historical bytes.
