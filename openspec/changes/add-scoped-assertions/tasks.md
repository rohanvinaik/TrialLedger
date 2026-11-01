# Tasks — add-scoped-assertions

## 0. Founder decisions

- [x] 0.1 The eight decisions, recorded in design.md (2026-11-01)

## 1. Object model and registry

- [x] 1.1 `ScopedAssertion`, `Proposition` (Literal, AllOf, AnyOf, Not, Opaque), the closed vocabularies, and
      `TemporalScope`, as immutable typed data with validation (2026-11-01: `TrialLedger/assertions.py`,
      `model_problem` and `canonical`/`from_canonical`, tests/test_assertions.py; left: the registry of 1.2
      that fills predicate keys, units and values)
- [x] 1.2 The first predicate registry: each bank concept mapped to its predicate kind, versioned, with
      provenance (2026-11-01: `TrialLedger/predicates.py`, all 91 concepts of the `nsclc_legacy` seed, 12 of
      them "unresolved" with their reasons (`UNRESOLVED`); `VERSION` the mapping's digest; `predicate_registry`
      with each concept's authority and its fragment's exposure, checked against the concept registry's
      families and declared arguments; pure `mapping_problems` and `atom_literal`, both converged COMPLETE;
      tests/test_predicates.py on the real criteria of tests/test_banks.py, every row pinned; declared dormant
      in tests/test_wiring.py until 2.1. Revised after review the same day: the named measurements' value
      unresolved (their concepts declare no number), a written unit never replaced, vitamin premedication
      unresolved, tissue availability of the participant. Left: the compiler that calls `atom_literal` (group
      2), the params it names unread (window, grade, scope, expression, qualifier: D5 and D6), the vocabulary
      words the unresolved concepts lack, and a mapping fragment per package as add-bank-coverage 3.x adds
      concepts. The founder, 2026-11-01: the per-concept interpretations listed in design.md (predicate kinds
      not stated by Decision 2, value kinds and cardinality) stand as interpolated defaults, never known, and
      each is surfaced for human review where a reading or a design depends on it: in layer 2, among the
      closing questions of add-design-synthesis Decision 9, with the default as the suggestion)

## 2. Compiling decisions (each pure, two-sign, from the measured failures)

- [ ] 2.1 D1 structure and D2 alternatives
- [ ] 2.2 D3 referents and D4 predicate identity
- [ ] 2.3 D5 qualifiers and D6 temporal attachment
- [ ] 2.4 D7 normative force and D8 applicability
- [ ] 2.5 D9 cohort scope and D10 definitions
- [ ] 2.6 D11 projection

## 3. Entailment

- [x] 3.1 The finite-domain decision procedure with the six results, typed interval comparisons, a declared
      resource bound, deterministic order (2026-11-01: `TrialLedger/entail.py`, `decide`, `assertion_formula`,
      `proposition_formula`, tests/test_entail.py on hand-built assertions; left: assertions compiled from
      text (group 2), the run in shadow mode that wires it (5.1; declared dormant in tests/test_wiring.py
      until then))
- [x] 3.2 Epistemic propagation (weakest support; proposed never a premise; no promotion) (2026-11-01:
      `entail.weakest_status` and the proofs of `decide`; left: propagation through the consumers, group 6)

## Detective convergence: the accepted debt, reconciled serially (2026-11-01)

The founder accepted, on 2026-11-01, Detective convergence as debt incurred by parallel workflow work, to be
reconciled serially afterwards. Reconciled the same day, one decision at a time: each below ends COMPLETE
(operator universe, modulo unproven-equivalent and crash-only value gaps). `model_problem` needed direct
intent tests (every class asked directly, one field forced past its constructor, and three instances built
without the constructor's own check); `proposition_formula` and `weakest_status` an exception compared as a
value; `decide` a query that widens the search past its bound:

- `assertions.model_problem` (changed 2026-11-01: an assertion refused without its rule; an unresolved rule
  naming provenance refused; the branch node "unresolved")
- `assertions.canonical`
- `entail.proposition_formula` (changed 2026-11-01: a negative qualified literal negates the conjunction;
  member-set and reference values as membership variables; time identity without certainty)
- `entail.assertion_formula` (changed 2026-11-01: an assertion with an unresolved rule is never a premise)
- `entail.weakest_status`
- `entail.decide`

Converged at write time (2026-11-01, task 1.2), each COMPLETE modulo unproven-equivalent and crash-only gaps:
`predicates.mapping_problems` (re-measured with `--isolated`, as converge directed) and
`predicates.atom_literal` (four of Detective's witnesses pinned by a hand-written test, the exception compared
as a value).

## 4. Targeted questions

- [ ] 4.1 The nine kinds with mechanically generated candidates, envelopes and validation, through the
      add-targeted-questions transport

## 5. Shadow mode and the transition report

- [ ] 5.1 Assertions produced beside unchanged legacy outputs, on the frozen NSCLC records and the pilot records
- [ ] 5.2 The transition report with named change reasons, coverage per rule, denominators

## 6. Consumers, one at a time

- [ ] 6.1 Coherence (strict closure from known constraints; the default view)
- [ ] 6.2 Profile and occupancy (per the founder's decision on their meaning)
- [ ] 6.3 Expectations, near misses, the review queue, the audit's claims
- [ ] 6.4 `reading.effective_section` retired once nothing reads it; a new semantic version published
