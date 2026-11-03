# Source workflows: evidence, conditional computation and unresolved meaning

The [investigation](../../docs/SOURCE_INFORMATION_RESOLUTION.md) explains these simple user questions,
what today's operations compute and the proposed integrations. This packet uses the retained
[IPASS development source](../../tests/fixtures/ipass-registry.md). It is an exploration, not a
clinical recommendation or a recovered protocol.

`binding-notes.json` names the source's byte digest and the origin of the interpretations. The
performance-status and joint-count requests reuse the explicit development bindings from
`tests/test_design_bounds_entrypoints.py` (`source_bound_request` and `overlap_request`). Their
`test:` references denote development assumptions, never source-authored statements. The joint request
adds an unrestricted candidate to keep the smoking requirement genuinely open. Candidate families
are declared hypotheses, not exhaustive protocol spaces. Population and schedule readings were authored
for this investigation; they have not been confirmed by a clinical user. They are marked interpolated.

Every `*-request.json` below is accepted directly by `trialledger reason --request FILE` or MCP `reason`.
The matching `*-result.json` is the complete response executed through the CLI on 2026-11-03.

| Request | Computed result |
|---|---|
| `ipass-performance-status` | Upper-cutoff candidates 0 and 1 ruled out under the bridge; exact cutoff remains undetermined |
| `ipass-joint` | WHO PS 2 ∩ never smoking is [49,126]; whole-profile exclusion ruled out under zero exceptions |
| `ipass-joint-exceptions-48` | At least one eligible joint-profile witness still guaranteed |
| `ipass-joint-exceptions-49` | Whole-profile exclusion no longer ruled out |
| `ipass-analysis-populations` | Outside EFS: 2 and 19; outside EFQ: 19 and 47, under declared cohort correspondences |
| `ipass-analysis-overlap` | EFS ∩ EFQ is [588,590] for gefitinib and [542,561] for the comparator, under the same cohort bindings |
| `ipass-assessment-window` | Interpreted first scheduled post-baseline window [35,49] days |
| `ipass-assessment-window-unresolved` | Same arithmetic, usable result unresolved because its reading is unresolved |

For example:

```sh
trialledger reason --request examples/source-workflows/ipass-analysis-populations-request.json
trialledger reason --request examples/source-workflows/ipass-assessment-window-unresolved-request.json
```

The layer-one record used to prepare the existing development requests was rebuilt with
`landscape.landscape_manifest` and `landscape.landscape_record`, with no network or terminology lookups.
Its projected study digest differs from the raw response byte digest; the raw source remains unchanged.
The investigation's `ipass-registry-checks.json` is explicitly a projection of check rows, not a complete
clinical record. `synthetic-results-flag-conflict.json` changes only a copy's `hasResults`, records the
relevant check and verifies input preservation. It is not an observed registry error and does not
demonstrate an implemented repair.

The three `spell-*-result.json` files are complete live SymbolicSpellCheck MCP responses. Inputs are
inside the responses: one real-source typo sentence, an invented clinical protection probe and an
invented valid-word probe. These are correction observations, not `reason` request files. Context
availability, partial states, sentence manifests, policy/dictionary identities and exact edit spans
remain visible. No learning operation or GSE edit was performed.
