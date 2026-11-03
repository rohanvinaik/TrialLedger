# Reasoning admission and translation audit

## Clinical object and boundary

A comparison of forty trials must not treat an unsettled reading as forty source facts. Nor should one
unsettled performance-status reading erase a separately warranted age restriction. This change audits the
existing typed entrypoints, not the still-unbuilt general eligibility compiler or complete trial writer.
The old review is a set of failure hypotheses, not authority for clinical WHO/ECOG equivalence.

Instrument: TrialLedger's exact/conditional distinction and existing reasoning operators. Specimen: current
public entailment, coordinates and corpus requests. Reproductions before the fix are retained in
`acceptance/reasoning-admission-audit.json` using explicitly invented premises.

## Contract

- A standing is a closed object `{status, resolution, basis}` using the assertion vocabularies. Explicit
  standings require nonempty provenance. Missing standing means pending, never known. A caller declaring
  known still supplies a premise; the flag does not independently certify confirmation or source truth.
- Coordinates accept `standing` per evidence item. Known/resolved items constrain known coordinates;
  interpolated/resolved items enter only the interpolated layer. Pending/proposed/conflicting/unresolved
  items remain visible and constrain neither layer. Competing proposals are never silently conjoined.
- Corpus trials accept an explicit trial-wide `standing` and `feature_standings` overrides. Overrides cover
  individual elements, representation fields and predicates; scalar collection fields classes,
  setting_domain, typed, eligibility_content and coverage have separate standing. Missing trial-wide
  declaration defaults pending. Inheritance permits an explicitly accepted representation without repeating
  a thousand confirmations, while an unsettled feature can override it.
- Corpus factual counts consume only known/resolved support. Interpolated information is retained pending
  for this consumer, not promoted to a source statement. Frequency retains the declared element universe,
  zero-admitted rows and pending counts. Eligibility silence remains unresolved. Unsettled source readings
  and source abbreviation are different reasons. Primary endpoint pending bounds are reported separately
  from known statement counts. No pending item becomes a negative fact.
- Association comparisons with pending membership/typing/element/coverage support in a stratum abstain
  explicitly rather than pretending that unknown readings are known absences. Other strata remain usable.
  Near-miss candidates with pending declared representation/predicate fields are withheld explicitly.
  Pending setting membership widens to all requested settings; pending class membership remains possible.
- Expectations accept `standing` and per-row `observation_standings`; unadmitted observations do not enter
  rarity denominators and remain inspectable. This population is declared independently of corpus trials;
  do not imply an automatic join.
- Entailment diagnostics name structurally demonstrable subject, unit or temporal mismatches only when
  predicate identity matches. They cannot bind different predicate names or establish WHO/ECOG equivalence.
  An explicit scoped implication/equivalence premise may connect representations; proposed bridges remain
  refused. Diagnostics explain abstention and never change the solver's decision.

## Consumer and verification plan

Trace service.run through CLI/MCP to all five corpus consumers and coordinate closure. Keep layer-one
reporting isolated. Use null/empty/malformed inputs, mixed accepted/pending evidence, pending-only features,
unknown memberships and per-row overrides. Run real CLI/MCP cases and discovery examples. Pin new pure
admission classifiers with authored positive/negative cases, and scoped Detective two-sign checks where
applicable, retaining exact residual limits. Run the repository's complete normal gate before committing
on main. Update conversational documentation and OpenSpec without marking the full compiler/writer built.

## Reporting handoff extension from the subsequent review

Audit the layer-one channel with the same conservation obligation, while using only its source-defined
rules. Retain exact possible/excluded date-order outcomes over valid DateType/PartialDate completions;
never fill missing source fields. Keep a known adverse-event contradiction despite independent malformed
entries, show warranted group-denominator fallbacks with visible origin, retain known collection counts
beside unknown collections, and serialize independently computed not-completed counts beside unresolved
reason accounting. Check both report JSON and workbook consumers; bind new dependencies/versioning.
