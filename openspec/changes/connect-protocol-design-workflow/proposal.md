# Proposal

## Why

TrialLedger already computes temporal bounds, endpoint prerequisites, estimand collection conflicts and finite decision rules, but its short preparation and decision alternatives principally serve assertion/eligibility questions. A clinical-development operator needs those computations connected across endpoints, assessments, efficacy and safety, with the exact question, scope, warrant and remaining choice preserved into the conversation and spreadsheet.

## What Changes

- Add an explicit version-2 managed protocol representation for measurement definitions, endpoints/estimands, assessment targets and permitted windows, collection availability, efficacy rules and safety policies. Preserve version-1 requests, results and artifacts without implicit migration.
- Compile named, inspectable projections into existing independent reasoning operators. Distinguish possible schedules, nominal-target support and coverage of every permitted assessment; never silently replace a protocol window with its feasible intersection.
- Add protocol alternatives that apply explicit design edits and freshly evaluate declared checks. Preserve each check and its warrant rather than translating every result into entailment or a blanket feasible/settled label.
- Extend short preparation and public CLI/MCP discovery to construct these objects and alternatives without private Python builders or copied expanded JSON.
- Add bounded finite-state safety-policy checks and an explicitly conditional, exact one-stage binomial efficacy calculation. Other statistical families remain explicitly represented but uncomputed, rather than being approximated by this method.
- Export a source-linked protocol synopsis and schedule of assessments alongside the decision list, with requested-but-unresolved sections and changed consequences visible.
- Require producer-to-consumer symbolic traces, authored positive/MUST-NOT tests, independent small-world oracles, current Detective two-sign records, contract checks, real CLI/MCP/revision/export checks and rotating model-operated clinical walkthroughs. Freeze shared interfaces before parallel work; serialize shared-file integration and final proof generation.

There is no automatic clinical prose interpretation, clinical choice of endpoint/dose/threshold, invented safety standard, general statistical-design optimizer, or claim of a complete autonomous protocol writer. These remain distinct from checking a person's explicit design and exposing its unresolved decisions. In particular, a field being present is not proof of medical completeness.

## Capabilities

### New Capabilities

None. This extends the existing symbolic design capability rather than introducing a competing designer.

### Modified Capabilities

- `symbolic-trial-design`: connected protocol objects and independent checks; quantified schedule coverage; general managed alternatives; finite safety policies; conditional efficacy calculations; short preparation, revision and clinical delivery with explicit coverage and warrants.

## Impact

Layer two and its shared public delivery paths only. Reuse `signals`, `graph_evidence`, `dependency_evidence`, `estimand_evidence`, `decision_tables`, `definition_checks`, immutable artifacts and source binding. Extend managed-session validation/projection, budgets, clinical metadata, revisions, preparation, discovery and export. Reporting acquisition, raw records, source workbooks and their derivation identities remain independent.

The implementation is governed jointly by `design.md`, `contracts.md`, `verification.md`, `parallel-work.md` and the delta spec. `HANDOFF.md` is the entry point. Supporting contracts are normative, not optional suggestions. The planning baseline is main commit `25c6bb5c29513f2159751d29c309620522e32425`; implementers must observe later changes rather than overwrite them.
