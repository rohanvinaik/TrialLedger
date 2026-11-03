# Phase 1 AML: where a dose table is missing

Question declared before acquisition: can sampled venetoclax combination studies supply a complete escalation, expansion and stopping decision table for a proposed AML study?

This is a fresh model-operated acceptance walkthrough of the integrated decision-table operator and its interpretation consumer. It is not validation of the sampled studies' dose algorithms: none of the three registry records supplies a complete algorithm. No clinical user confirmed a reading, and no source was replaced to obtain a tidier example.

## Acquisition and evidence

The complete query pool contained 31 completed Phase 1 AML studies mentioning venetoclax. The predeclared maximum whole-pool acquisition was 30. Seed 7075652826039879207 selected NCT02670044, NCT03625505 and NCT04666649 before their content was read; a new explicit-ID report acquired exactly these three. The complete pool, query, source identity resolution, timestamps and fingerprints are retained. The report and complete raw responses stay local outside Git. Complete study snapshots are also embedded in the source-assertion requests, as required by that operation.

All three studies' identification, status, description, design, eligibility, arms/interventions and outcomes modules were read in full. None has posted results, so participant-flow and baseline counts are unavailable here.

- **NCT02670044** documents venetoclax/cobimetinib and venetoclax/idasanutlin regimens in nine escalation/optimisation arms. Its first primary outcome counts DLTs from Cycle 1 Day 1 to Cycle 2 Day 1, for a minimum of 28 days. It does not state the DLT-count thresholds or action mapping needed for a complete table. Eligibility contains both a comorbidity branch mentioning ECOG 2 or 3 and a general ECOG 0–2 criterion; those are not silently flattened into an ECOG 3 permission.
- **NCT03625505** documents escalation followed by expansion at the dose determined in escalation. Its primary outcome states that RPTD uses available safety and pharmacokinetics data. FLT3 mutation is required for expansion only. None of this supplies a complete toxicity-to-action table or a threshold for adopting a dose.
- **NCT04666649** gives four dose cohorts. The RLT description specifies the first treatment day through 30 days after the first dose, while its `timeFrame` says one year after 12 cycles. Both source channels are preserved; neither is rewritten into the other. No case/action threshold is stated.

Precise source paths and complete anchor values are retained in the three `requests/*-source-age.json` files. A located passage establishes its wording, not a clinical interpretation or a complete table.

## What was actually computed

Eight requests were executed through separate real CLI and MCP processes. Their complete parsed documents matched, excluding only MCP's `tool` wrapper. The runtime receipt fingerprints 76 existing package files and checks them before and after calls. No package additions occurred during this run. The local report passed `trialledger verify`, establishing reproduction from retained sources, not clinical truth.

Three independent source-assertion requests compile each study's structured minimum age, 18 Years. Each query that the encoded age restriction requires age at least 18 is ENTAILED with known standing. Free-text eligibility remains retained and uncompiled. These checks do not establish overall individual enrollment eligibility.

The remaining inputs are **explicitly invented assistant proposals**, not extracted study rules or clinical recommendations. Their declared finite domain is the DLT count 0–6 in one hypothetical cohort of six evaluable people and one first-cycle context. The complete proposal maps 0 or 1 to `escalate`, and 2–6 to `stop`. These action identities have no independent clinical equivalence or authorization.

1. Remove count 1 from the first row: raw table coverage is `gap`, with `table_uncovered_case`.
2. Restore count 1: raw coverage becomes `covered`; the two distinct-action rows are disjoint and both actions reachable. This establishes completeness only over this declared finite family, not a complete protocol or a safe escalation design.
3. Also put count 1 into the stop row: coverage remains complete, but the rows overlap with different actions, yielding `table_conflicting_actions`.
4. Limit aggregate solver calls to one: the domain check is retained as feasible, while coverage, overlap and reachability remain unresolved with `resource_bound:table_checks`. A computation task is not missing clinical evidence.

All four ordinary signal results retain proposed support and `proposed_refused`; raw calculations are visible without becoming factual claims. The operator does not return a concrete witness profile here (`witnesses: []`). The count-1 explanation follows from the deliberately supplied row revision, not a claimed emitted witness.

A final interpretation request compares the gap, restored and overlapping proposals beside the independently compiled NCT03625505 age restriction. The complete proposal is compatible; gap and conflicting-action frames are incoherent. Their effective frame answers are withheld, while the raw age proof is retained. The fixed floor still entails the adult restriction independently. Replaying every source-age request after all revisions gives the same complete result.

## The clinical handoff

See `working-brief.md` for the decision list. Missing rules remain evidence gaps, proposed policy remains the person's choice, and a calculation limit remains a computation task. This walkthrough does not calculate operating characteristics, sequential termination, dose safety, efficacy, acceptable toxicity targets, RPTD, or a 3+3 algorithm.

The first helper attempt represented a single condition as unary `AnyOf`, correctly refused as `compound_needs_two_parts`. The helper was corrected to a literal, and all eight final CLI/MCP pairs rerun. One verification attempt used an unsupported `--run` flag; the documented positional-folder invocation then passed. Neither was a production failure.
