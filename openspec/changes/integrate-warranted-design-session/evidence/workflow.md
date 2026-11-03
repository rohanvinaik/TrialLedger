# Clinical workflow investigation, 2026-11-03

## Question and observing boundary

“We are considering a new advanced NSCLC trial. Comparing IPASS and ARCHER 1050, what performance-status, population and assessment choices can the evidence actually constrain, and which questions remain ours?”

This is an engineering investigation through the live product, not a clinical user's confirmed design session. Source facts, analyst-authored hypotheses and exact results under those hypotheses remain separate. The current operations do not claim to have run the proposed `design_session`.

## Actual pull

At revision `a3987b05db21f0cf3f871cc36f272ddc516c1ec2`, the declared project environment ran doctor, scope preview and direct landscape retrieval for `NCT00322452,NCT01774721`. Both identifiers were found under their own numbers. Registry API 2.0.5 reported data timestamp `2026-11-03T10:00:05`. RxNav enrichment completed. `trialledger verify` reproduced the JSON and workbook from the retained evidence.

The complete run is in `registry-run/`; `receipt.json` records commands and SHA-256 identities. Original runtime paths inside saved requests intentionally remain unchanged. `registry-run/` is a byte-preserved relocation of `/tmp/trialledger-thesis-live-20261103`; source/result values were not rewritten to make their references look local. Full raw study bodies remain in `registry-run/bodies/studies-001.json`. Standalone study JSON files are parsed-study copies, not claimed original HTTP bytes.

## What we read and what follows

### Performance status, smoking and exceptions

From complete eligibility, baseline and participant-flow units:

- IPASS has structured minimum age 18 Years and no structured maximum. Its eligibility text names never smokers or light ex-smokers and gives no PS cutoff.
- Its baseline reports 1,217 participants, 126 at WHO PS 2 and 1,140 never smokers. The baseline population-description field is not stated. Both PS and smoking tables have `param_type: NUMBER`, not `COUNT_OF_PARTICIPANTS`; reading their participant units and categories as exact participant counts is a retained premise, not a silently compiled registry rule.
- The smoking table separately records two “Ex-smoker (non-light)” participants, one in each arm.
- The flow table reports one carboplatin/paclitaxel participant under “Eligibility criteria not fulfilled,” and zero in the other arm. It does not give that person's PS or smoking category. The count does not establish a complete upper bound on deviations.
- ARCHER 1050's eligibility explicitly includes ECOG PS 0–1. Its flow table reports three gefitinib participants under “Did not meet eligibility criteria.” WHO PS remains separate from ECOG.

Conditional on common baseline population/count semantics, the public source bridge returns a PS-2/never-smoker overlap of 49–126 inside a proposed interpretation. It does not add a fixed PS restriction. The registered adult-age answer remains known independently.

Separate sensitivity probes, explicitly labelled hypothetical and not clinically confirmed, supply exception caps 0, 1, 48 and 49 to the public `design_bounds` operation. At 0/1/48 the candidate excluding the whole joint profile is ruled out; at 49 it remains. The common query remains undetermined because an unrestricted candidate is included. A proposed bridge retains all candidates as unresolved. These results validate the existing inequality and admission behavior, not the empirical truth of the caps.

**Observed handoff:** the old maximum-exception field cannot reference a source-derived exception envelope, and the request does not automatically include the flow evidence. The kernel consequently answers the supplied hypothetical cap without checking it against those unsupplied facts. Fix the composition rather than declare the arithmetic wrong.

**Needed meaning check:** turning the flow category into an entry-eligibility exception needs its population/time/criterion relation. Once admitted, it can contradict a zero **global** exception cap. It does not contradict zero exceptions in a subgroup whose membership is unspecified. The baseline non-light category can supply another conditional floor only after its definition and timing are bound. These counts may overlap; they must not be added blindly.

The supplemental `ipass-two-count-channels` probe binds the two baseline participants and the one flow participant to a common population hypothetically. The existing overlap operation returns 0–1 in both groups. It does not classify either category as an eligibility violation or identify their members.

### Schedules and endpoint definitions

IPASS's complete primary schedule passage describes assessments every 42 ±7 days from randomization. The current source bridge preserves two proposed readings: nominal targets 42/84 under both, first allowed window 35–49 under both, and later windows 77–91 versus 70–98. Both frames remain compatible. Source anchoring does not select a reading.

The complete RECIST response definition additionally requires confirmation at least 28 days after the initial response. The QoL definition requires two qualifying visits at least 21 days apart and no intervening visit with the specified decline; EFQ membership requires baseline and at least one post-baseline assessment. These are different events and predicates. This pass did not compile the longitudinal absence condition, infer an endpoint edition or certify actual attendance. The session must preserve these as specific open tasks, not one generic duration choice.

### Treatment history and mutation eligibility

ARCHER's complete eligibility allows T790M together with exon 19 deletion or L858R; reading the mutation alternatives as a single exhaustive value loses this exception. The same eligibility has an inclusion allowing a sufficiently remote neoadjuvant/adjuvant treatment interval and a broad exclusion referring to previous systemic treatment of early as well as advanced NSCLC. Those passages require scope/exception reconciliation before a flattened prior-therapy restriction is used.

IPASS likewise has a broad prior-chemotherapy exclusion and a recruitment passage exempting non-platinum adjuvant chemotherapy. These are documentary tensions to preserve and investigate, not permission to choose a favored sentence. A selective phrase compiler that ignores the surrounding scope would hide information here.

### Computation versus evidence

The two `draft-age-bound` probes use the same **invented draft premise** requiring age ≥18 and the same age query. At bound 1, public entailment returns `UNDETERMINED` with `resource_bound`; at bound 100, it returns `ENTAILED` with proof `draft-adults`. No source evidence changed. Current user guidance groups resource limits with “not knowable from this evidence”; the planned normalization separates unfinished computation.

## Review dispositions

| Review object | Finding and action |
|---|---|
| Exception floor | Real documentary channel; source count and eligibility interpretation must remain separate; integrate a scoped envelope and cap consistency check |
| Corpus standing | Current public guards already exist; missing piece is a premise-backed projection that checks origin as well as status |
| Shared constraints | Existing claims are joint within one signal; do not claim general cross-signal feasibility; fund larger exact count work with a case that actually improves the bound |
| Truth maintenance | Frames and a minimal proof are useful primitives, not all-support labels; initial full replay is the correctness reference |
| Every clause in four classes | Conditional on representation, satisfiability and completed computation; include conflict, translation and computational prerequisites explicitly |
| Entropy accounting | Follow-on over an exactly counted declared design space; no claim that current candidates enumerate protocols or that cardinality equals derivational significance |
| Grammar coverage | Follow-on; measure defined source units/constructions and errors, not an unsupported fraction of all clinical meaning |

## Current decision handoff

| Clinical entry | What the run supplies | Remaining task |
|---|---|---|
| New-trial PS scale/range | ARCHER's ECOG wording; IPASS WHO participation and conditional witness bounds | Choose the draft restriction; obtain or declare any scale relation explicitly |
| Historical eligibility compliance | Named flow counts and a second smoking-category channel | Settle their meanings/alignment; retain unknown total deviations and hypothetical cap sensitivity |
| Assessment plan | Separate nominal targets, windows, confirmation and QoL requirements | Choose anchors/definitions for the new trial and investigate the comparator's unresolved meanings |
| Prior treatment and mutations | Full passages with alternatives and apparent conflicts retained | Clarify scope before using them as criteria or a comparison feature |
| Unfinished calculation | A reproducible tiny-bound abstention | Complete/narrow computation; do not request new medical evidence as its remedy |

## What was and was not verified

Twelve complete public CLI request/result pairs were executed in the project environment and retained. Layer-one replay verified preservation/reproduction. Whole relevant clinical units were reread after an oversized first display was truncated. One supplemental probe failed under the wrong system interpreter before producing a reasoning result; the saved result is the successful project-environment run. No runtime code changed, no new mutation pin was attempted, and the full project suite was not rerun for this planning-only pass.

The post-documentation random workflow check is recorded separately. Neither this targeted run nor that sample establishes broad clinical validation or automatic encoding accuracy.
