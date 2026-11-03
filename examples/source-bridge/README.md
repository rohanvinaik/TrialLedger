# Retained source → exact anchors → proposed readings → computed consequences

This packet runs the public `source_assertions` operation on the unchanged retained
[IPASS study](../../tests/fixtures/ipass-registry.md). It demonstrates a source bridge, not automatic
clinical text interpretation or a recovered protocol. All population and schedule readings are
assistant-authored exploration premises, **not confirmed by a clinical user**.

The source object is included in each request. The response records its content digest and version metadata,
validated anchors, the fixed floor, proposed representations, generated ordinary requests and complete
solver responses. The original fixture and report files are not rewritten. A content digest identifies a
snapshot, not an independently established clinical protocol edition or the live registry's present state.

| Request/result pair | What is computed | What remains open |
|---|---|---|
| `ipass-registered-age` | The structured `minimumAge: "18 Years"` entails age ≥18 Years and refutes age <18 Years under the direct registry general-eligibility rule | Actual protocol completeness and every other restriction |
| `ipass-baseline-overlap` | Exact anchored strings hydrate total 1,217, WHO PS 2 count 126 and never-smoker count 1,140; under the proposed common-universe binding, the existing overlap operator returns [49,126] | Exact intersection, eligibility assessment-time alignment, eligibility exceptions, PS cutoff and any WHO-to-ECOG correspondence |
| `ipass-schedule-readings` | Both readings retain nominal targets day 42/day 84 and first permitted window [35,49]; the second permitted window is [77,91] under randomization anchoring or [70,98] under successive gaps | One schedule decision informed by nominal targets, tolerance and its subsequent anchor; actual attendance and endpoint confirmation remain separate |

The schedule anchor quotes the entire field, including `42 days ± 7 days`, `from randomization` and the
cutoff date. Each reading retains distinct nominal-target and permitted-window information channels for one
schedule decision. `first_nominal_target` is day 42, and a further 42-day nominal gap yields
`second_nominal_target` at day 84. These targets are separate from `first_permitted_assessment` and
`second_permitted_assessment`; they are not equations forcing attendance on nominal days. Both readings
retain the full ±7-day tolerance and the first permitted window [35,49]. Their distinction concerns
subsequent tolerances: are these attached to nominal days from randomization, or intervals after the
preceding assessment? Both frames remain proposed and internally compatible; the bridge has no prose rule
that certifies either clinical reading. A matching quotation establishes its location. Actual attendance and
response-confirmation intervals remain separate objects.

For the baseline example, the complete WHO performance-status, smoking and denominator objects are anchored
alongside their exact count cells. The recorded `NUMBER`/`Participants` metadata and module-local `BG002`
references stay visible. The clinical reading that these are exact participant counts in one common
population is proposed. No count is automatically made an eligibility criterion, and no cross-module group
identifier or equal denominator establishes correspondence. The query about WHO PS ≤2 remains
`UNDETERMINED`; the joint baseline bound does not recover an exact eligibility cutoff.

Every frame and binding declares its own anchor dependencies. Templates can copy an explicitly selected
integer, exact text or JSON value; they do not choose its clinical subject, population, units, role or time.
Prepared assumptions, signal support and bindings are forced to `proposed`, even if the submitted standing
was `known`. Their original submitted representations remain in the response for inspection.

Run a saved request directly:

```sh
trialledger reason --request examples/source-bridge/ipass-baseline-overlap-request.json
```

Rebuild all three request/result pairs through the CLI:

```sh
uv run python examples/source-bridge/build_examples.py
```

The builder reads the retained fixture, never refreshes the registry, and verifies that its bytes stay
unchanged. The [entry-point tests](../../tests/test_source_assertions_entrypoints.py) replay every full
response through CLI and MCP, forbid network calls, and verify report/source preservation. They also test
stale digests, missing addresses, typed values, Unicode spans, undeclared dependencies, OR/AND preservation,
wrong population/arm/time/version, unsupported numeric syntax and status promotion attempts. A candidate
first permitted assessment on day 40 fits both readings while nominal targets remain day 42/day 84. A candidate
second visit on day 72 conflicts with the randomization-anchored reading and fits the successive-gap reading
in an additional public CLI/MCP test; the source's intended reading is still not certified.

The [working brief](working-brief.md) is the clinical handoff. The generated requests and results remain
separate from that narrative and can be rerun after a reading or source revision.

## The same boundary across inference channels

The three IPASS pairs are a small real-source walkthrough. The parametrized public-boundary contract in
`test_every_signal_channel_preserves_structure_and_proposed_admission` covers **all eight existing signal
kinds** with the runnable examples obtained from `describe: signals`. Those additional cases are explicitly
invented typed hypotheses, anchored to an entire invented teaching context containing their supplied data.
They are not additional IPASS findings, and a generic registry passage is never offered as a warrant for
their invented numbers, definitions or clinical meanings.

These channels can inform the same decision or different decisions. Each retains its own object, scope,
premises and limits; combining them needs an explicit applicable relationship. A valid source anchor cannot
supply that relationship or promote a typed hypothesis into a source-known fact.

| Evidence channel | Clinical questions it can inform | What must remain explicit |
|---|---|---|
| Structured source age, compiled directly | Which registered age bound informs a proposed population? | The exact general-eligibility field and unit; no completeness or actual-protocol certification |
| `overlap` | What joint population can partial counts guarantee? | Common universe, assessment, count meaning and interval; no independence assumption or exact recovered cross-tabulation |
| `partition` | What belongs to a remaining category or complement? | Disjointness, coverage and population; an unknown category is not zero and partial coverage is not exhaustive |
| `summary` | What participant-count bounds follow from a reported minimum, maximum or median? | Exactness, assessed population, measurement/unit and median convention; rounded values do not become exact witnesses |
| `population` | Which analysis population is a subset, and who is outside it? | Parent/subset correspondence, version and count meaning; equal counts or titles do not establish membership |
| `temporal` | How do nominal targets, permitted windows, ordering and observed events constrain a design? | Separate event roles, timeline origin, units, inclusive boundaries and applicable course; one channel must not erase another |
| `regimen` | What assigned or observed arm composition follows from products and ingredients? | Planned/observed stage, arm role, product identities and completeness; no automatic alias expansion or transfer between roles |
| `relations` | What follows from declared concept membership or directional relations? | Edition, scope, direction and polarity; direct association is not causation and missing membership is not negative membership |
| `dependencies` | Can an adopted endpoint definition use the available measurements? | Adoption, definition edition, OR-of-AND inputs, conditions and observed/imputed/derived mode; unknown availability is not explicit unavailability |

For every signal kind, the test submits `known` support as an attempted promotion and verifies that prepared
support is `proposed` with the actual anchor reference. It preserves the complete typed data, including
population, time, role and definition edition where represented, plus a labelled invented predicate used
only to check representation conservation. The existing public operator supplies the comparison for the
calculation; the test does not implement its rules. With unresolved support, the conditional mathematical or
structural context remains visible, its usable code is unresolved, and the frame is not automatically
refuted. An unrelated source-defined adult-age answer remains settled. No automatic joins, new signal kind,
corpus admission or clinical meaning recognizer is implied by these tests.

Eligibility witnesses have a further distinction. Positive participation and an eligibility-attributed
rejection are different observations. A partial rejected profile does not establish universal exclusion;
the existing design-bounds route requires the rejection attribution and a feasible `P AND NOT E` completion.
This bridge does not automatically translate a flow-table rejection label into that representation or create
a new rejection route. Each clinical decision must retain the channels it actually uses and the particular
missing bindings or choices that still matter.
