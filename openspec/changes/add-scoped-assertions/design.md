# Design — add-scoped-assertions

## Context

The contract below is Codex's draft (2026-11-01; the full text is kept beside the consult as
`/tmp/trialledger-consult/assertions_answer.txt` at the time, quoted where it is load-bearing), reconciled by
Claude with the code as built. Reconciliation notes are marked **As built here**.

## Decisions

1. **Scoped constraints over propositions, not flat tuples.** `required(A OR B)` is not two requirements;
   `excluded(A AND Q)` excludes neither component; `required(stable IF used)` does not require use; a definition
   imposes nothing by itself. Atoms remain immutable evidence candidates; `text_polarity` and `modality` stay as
   candidate annotations and never authorize sentence-wide negation or permission by themselves.
   **As built here**: atoms are `(bank, concept, values, params, start, end)`; the compiler reads them with the
   criterion's text and `criteria.itemize`'s pieces; nothing in the banks changes.
2. **The object model.** `ScopedAssertion {id, criterion_ref, modality, body, applicability, cohort, branch, span,
   rule, status, resolution}`; `Proposition := Literal{subject, predicate, value, polarity, time, qualifiers,
   evidence} | AllOf[≥2] | AnyOf[≥2] | Not | Opaque(unresolved_ref)`; Opaque is unresolved, never false.
   Closed vocabularies: modality {required, excluded, permitted, definitional, descriptive, unresolved};
   polarity {positive, negative, unresolved} on the literal; subject kind {participant, source_case, partner,
   caregiver, other_person (with an explicit referent), study_intervention, study_procedure, encounter, specimen,
   unresolved}; predicate kind {condition_status, exposure, treatment_history, procedure_event, measurement,
   demographic, disease_attribute, medication_use, medication_stability, consent, reproductive_status,
   encounter_purpose, defined_term, unresolved}; value kind, comparison, temporal orientation, anchor kind,
   certainty, branch node, scope expression, evidence kind as in the draft. A population qualifier is cohort or
   applicability, never a subject. Unknown vocabulary is unresolved, never a new string. Predicate keys, values,
   units and relation ids live in versioned registries. **As built here**: the first registry is the banks'
   concepts, each mapped to its predicate kind (named conditions to condition_status unless a construction says
   exposure, history or procedure; prior therapy to treatment_history; labs to measurement; age to demographic).
3. **Conditionality is applicability, not modality.** `required(medication_stability(4 weeks))` with
   applicability `medication_use` compiles to `medication_use → stability`.
4. **Time.** `TemporalScope {orientation, anchor, bounds, inclusivity, certainty, evidence}`; units kept as
   written; an event-relative window ("within 2 years after diagnosis of chronic pancreatitis") never becomes
   enrollment-relative; an unresolved anchor supports no enrollment window.
5. **Provenance.** Every assignment names its record version, half-open spans, atom ids, rule id and version,
   premises, warrants and targeted answers; normalized text keeps a map to the original spans.
6. **Semantics.** Modality acts on the whole body (required F means F; excluded F means NOT F; permitted F
   imposes nothing; definitional F only through a valid reference; descriptive and unresolved contribute
   nothing). A negative test result is not the absence of the condition without a warranted relation. Qualified
   literals keep their qualifiers: `excluded(HIV ∧ CD4<200)` does not entail `excluded(HIV)`, while
   `required(HIV ∧ Q)` does entail `required(HIV)`. Definitions are stored apart from their use and expand only
   through a resolved reference, keeping alternatives. A permission never establishes presence, never widens to a
   broader predicate, never erases an exclusion. **As built here**: `reading.effective_section` is the legacy
   path, identified as such until its consumers are switched.
7. **The compiling decisions** (pure, each with named decision codes and evidence, none mutating atoms):
   D1 structure (item spans, headings, list boundaries, explicit conjunctions; punctuation alone is not grouping);
   D2 alternatives ("or", "and/or" inclusive, "either … or" not exclusive unless stated, "one of the following" at
   least one; slashes and damaged lists unresolved); D3 referents (an attribute of a source case, partner or
   caregiver never transfers by default); D4 predicate identity (status vs exposure, history vs planned
   procedure, test vs condition; a concept hit alone decides nothing); D5 qualifiers (restrictive attachment,
   measurement binding; ambiguous attachment blocks the bare projection); D6 temporal attachment (to the governed
   event and anchor; nearest mention is not enough); D7 normative force (explicit constructions, else section
   context; a mention inside an explanation or a definition does not inherit it); D8 applicability ("if",
   "when", "unless"; a conditional never implies its antecedent); D9 cohort scope (a small heading grammar —
   "Cohort X only:", "For phase N:", "For arm X:" — with explicit reset; named cohorts are never assumed
   exhaustive); D10 definitions (no free-standing conclusions from a definition's contents); D11 projection
   (only through resolved bindings and kept qualifiers). Mixed clauses get separate local force. **As built
   here**: `criteria.itemize` already gives D1 its pieces and keeps sub-items inside their parent;
   `questions.envelope` already finds stems, scoping lines and "or"/"and" siblings, the seed of D2 and D9.
8. **Entailment.** For a context c, required gives `scope ∧ applicability → body`, excluded `… → NOT body`,
   conjoined; a query Q is ENTAILED only if the formula is shown satisfiable, no feasible assignment satisfies
   E ∧ ¬Q, the proof uses accepted premises and warrants only, and every applicable context is covered.
   `(A∧B)∨(A∧C)` entails A, neither B nor C; "locally advanced or metastatic" restricts the setting to both,
   selects neither. Branches are pruned only by a proof of unsatisfiability; all branches impossible is
   INCONSISTENT, never universal entailment; missing support is never evidence of absence. **As built here**: the
   formulas are small (one trial's criteria); an exact finite-domain procedure (enumerating the assignments of
   the literals a query depends on, with intervals as typed comparisons) is enough to start, with a declared
   resource bound returning UNDETERMINED.
9. **Epistemic propagation.** Resolution and status are separate; a derived conclusion has the weakest status of
   its support; proposed material is never a premise; nothing deterministic promotes interpolated to known.
   Approved relations are not automatically strict (add-scoped-reasoning Decision 2 holds).
10. **Targeted questions** for bounded gaps: subject_binding, predicate_identity, coordination_structure,
    normative_force, qualifier_attachment, conditional_scope, temporal_attachment, cohort_scope,
    definition_binding; options are every mechanically generated candidate plus unresolved (a question whose
    candidates are incomplete is not ready); the envelope holds the whole criterion and its governing headings,
    and adjacent criteria when a boundary depends on them. An accepted answer instantiates a declared
    interpretation, is interpolated, triggers recomputation and stays as provenance; it never supplies a warrant
    or a threshold. **As built here**: the transport, the closed-option schemas, the envelopes and the audit loop
    of add-targeted-questions carry these kinds; the local auditor is qwen3:8b with thinking.
11. **Consumer contracts.** Consumers query declared projections (`ConsumerContract {accepted statuses,
    subjects, modalities, predicates, temporal and scope requirements, projection}`), each result with its
    decision code, conclusion, scope, status, proof and blockers; a consumer that cannot represent a distinction
    (the key `exclusion:HIV:positive` for a CD4-qualified exclusion) gets a blocked projection. "Current" is not a
    universal profile filter. Initial declarations: strata and profile known participant constraints; coherence
    known for strict closure, interpolated only in its default view; near misses known and interpolated, naming
    which rest on interpolation; the review queue the unresolved and conflicting; the audit the emitted claim
    and its proof.
12. **Migration.** Freeze the comparison inputs; produce assertions in shadow mode beside unchanged legacy
    outputs; add projections beside them; emit the transition report (identity, input invariance, every changed
    claim with its new decision, expression, scope and proof, a change reason from ALTERNATIVE_NOT_UNIVERSAL,
    NONPARTICIPANT_SUBJECT, QUALIFIED_EXCLUSION, DEFINITION_ONLY, CONDITIONAL_OBLIGATION,
    ENCOUNTER_OR_POPULATION_SCOPE, STUDY_EVENT_ROLE, TEMPORAL_REATTACHMENT, EXPOSURE_NOT_CONDITION,
    PERMISSION_NOT_REQUIREMENT, COHORT_RESTRICTION, OTHER_RESOLVED_SCOPE_CHANGE, UNRESOLVED_READING, propagation,
    coverage, denominators); switch consumers one at a time with no hidden atom fallback; publish under a new
    semantic version. For the 34 NSCLC trials the report separates "the faulty premise removed", "another
    criterion still requires metastasis" and "now unresolved".
13. **Tests.** Every rule two-sign, from the measured failures (the table in the draft: alternatives,
    treatment alternatives, shared branch conclusions, exclusion structure, other-person subjects, qualified
    subsets, definitions and their expansion, encounter scope, conditional obligations, planned procedures,
    event-relative time, exposure identity, permission, clause-local permission, cohort scope, test versus
    condition, epistemic status, inconsistency, open populations), plus empty and malformed inputs, nesting,
    negation scope, threshold boundaries, missing units, cohort resets, stale answers, deterministic replay,
    proof retention through every consumer, no use of proposed assertions, no promotion of interpolated ones,
    resource exhaustion as abstention; semantic mutants (swap AND/OR, drop a qualifier, move a negation, rebind
    another person to the participant, erase an antecedent, re-anchor to enrollment, promote interpolated) must
    be killed; verification through the real consumer entry points.

## As built here: the object model and the decision procedure (tasks 1.1, 3.1, 3.2; 2026-11-01)

- `TrialLedger/assertions.py` holds the model as frozen dataclasses (`Evidence`, `Subject`, `Predicate`,
  `Value`, `TemporalScope`, `Always`, `Literal`, `AllOf`, `AnyOf`, `Not`, `Opaque`, `Scope`, `Branch`, `Span`,
  `Rule`, `ScopedAssertion`) and the vocabularies of Decision 2 as frozensets; every class refuses on
  construction what `model_problem` names (a code, `ModelError`), so an unknown word cannot enter. `canonical`
  is tagged, key-sorted JSON that writes every number as a float and keeps order and nesting; `from_canonical`
  reads it back to an equal object. A predicate is its kind and its registry key (the registry is 1.2). A
  value is `boolean`, `enum` (eq, ne, in, not_in over members), `enum_set`, `quantity` (one number, the unit
  as written, "" when missing), `interval` ([number, upper] with its inclusivity), a reference, or
  `unresolved`. An assertion's defaults are the weakest: status proposed, resolution unresolved.
- `TrialLedger/entail.py` decides by exact enumeration: a literal is a variable keyed by subject, predicate
  and time with every evidence field stripped; a quantity or interval is a typed comparison on a measurement
  keyed also by its unit, enumerated at every named threshold, every midpoint and one beyond each end; an
  enumerated value ranges over its named members and one unlisted member (open domain). The formula is split
  into components by shared variables; every component is checked for satisfiability (INCONSISTENT anywhere
  stops everything), then the query's component decides it. The bound is `MAX_ASSIGNMENTS` (65,536
  assignments per enumeration). A proof is a minimal premise set, from known premises alone when they
  suffice, premises dropped weakest first, then by id.
- Interpretations fixed here, each open to the founder's ruling:
  - OUT_OF_SCOPE means no constraint in the query's context speaks of the query's variables, but an
    assertion scoped to another context does; nothing speaking of it at all is UNDETERMINED
    ("no_constraint_mentions_query").
  - A context names the participant's one entry cohort, phase or arm: naming cohort A makes a cohort-B scope
    false (entry cohorts disjoint). A context that names none leaves each named scope a free variable (A5:
    named cohorts are never exhaustive), so a cohort-B requirement is UNDETERMINED trial-wide.
  - A qualified literal is the conjunction of its base and its qualifiers, and its polarity negates that
    conjunction: a negative qualified literal is NOT (base AND qualifiers), never (NOT base) AND qualifiers.
    So required(negative "HIV with CD4 < 200") and excluded(HIV qualified by CD4 < 200) compile to one formula
    and entail neither NOT HIV nor CD4 < 200 (corrected 2026-11-01; the first build negated the base alone).
  - A member-set (`enum_set`) value is one membership Boolean per member: `in` S holds every member of S,
    `not_in` S holds none of them (as `not_in` excludes every member for `enum`), so `in` {a} and `not_in` {a}
    are one variable and requiring both is INCONSISTENT; `in` {a, b} implies `in` {a} and `not_in` {a, b}
    implies `not_in` {a}, never the reverse. A boolean is one variable on its subject, predicate and time; a
    reference (`entity_ref`, `definition_ref`) one Boolean per member. The comparison, unit and inclusivity of
    these kinds never split a variable.
  - A reference compared with `eq` is not taken as single-valued: `eq` R1 required leaves `eq` R2
    UNDETERMINED, never refuted (as in the first build). Whether a reference predicate is single-valued is
    the registry's to say (task 1.2) and open to the founder's ruling.
  - A literal's time identity is its orientation, anchor, bounds, unit and inclusivity; its certainty, like
    its evidence, is epistemic metadata and never splits a variable.
  - No invented provenance: a `ScopedAssertion` has no default rule and is refused without one
    ("assertion_without_rule"); `UNRESOLVED_RULE` (id and version "unresolved", nothing else) says explicitly
    that the derivation is not known, and such an assertion is never a premise ("unresolved_rule"). The branch
    node vocabulary has "unresolved", the default position; an unknown position is never "leaf".
  - An interval whose inclusivity is unspecified leaves each boundary point undecided (a free variable per
    boundary; A7: the boundary is preserved, never assumed).
  - Another unit, or a missing unit, is another measurement: no conversion, so no entailment across units;
    another time scope (orientation, anchor, bounds) is likewise another variable.
  - An assertion whose resolution is unresolved, or whose modality is, contributes nothing and is named as a
    blocker; one whose resolution is conflicting contributes nothing (A6); a partially resolved one
    contributes its body with its `Opaque` parts free.
  - A literal with an unresolved subject, predicate, polarity or value kind is a free variable, never false; a
    query holding one, or an `Opaque`, is UNSUPPORTED_QUERY; so is a query holding an interval whose
    inclusivity is unspecified (its boundary points are undecided).
  - A decision's blockers pool every blocker the trial's assertions raise in the context (an `Opaque` in an
    unrelated criterion is named on every query), with the result's own code added.

## Founder decisions (decided 2026-11-01: the founder approved Claude's recommendations, "Good. Let's encode this")

- A1. Separate requirement, exclusion, permission and allowed-set projections; occupancy means the trial's
  required constraints admit the cell, with "mentions it" reported apart.
- A2. No question kind's model answers are adopted automatically until that kind passes its own pilot (planted
  errors accepted at most as rarely as the auditor's 1 of 164); a kind that passes is adopted as interpolated;
  the rest are queued.
- A3. A grammar rule confers known only when its construction is unambiguous, two-sign tested and confirmed on
  data it was not written on; ontology relations only with a cited source.
- A4. Unresolved results are shown as blocked claims with their cause, never as absent.
- A5. Named cohorts are exhaustive only on explicit evidence.
- A6. Conflicting defaults: neither fires, the conflict reported.
- A7. Unspecified temporal boundaries preserved; any assumed convention interpolated.
- A8. Definitions: explicit local references first; wider binding only by separately specified rules.

## The draft's proposed settings (kept for the record)

- What the profile and occupancy mean: separate requirement, exclusion, permission and allowed-set projections,
  and an explicit definition of occupancy.
- Which question kinds' validated model answers are adopted as interpolated automatically; the rest are queued.
- The versioned grammar rules, ontology relations and external warrants that admit known status.
- Unresolved results shown as blocked claims with their cause, never as absent.
- Named cohorts treated as exhaustive only on explicit evidence.
- A declared cautious policy for conflicting defaults, never execution order.
- Temporal conventions: unspecified boundaries preserved; any supplied convention interpolated unless warranted.
- Definition scope: explicit local references first, wider binding only by separately specified rules.

## Risks / Trade-offs

- [The compiler abstains often at first] → abstention is named and counted; the transition report measures
  coverage per rule; targeted questions take the bounded remainder.
- [A second representation beside the atoms] → shadow mode until each consumer switches; no consumer keeps both.
- [The entailment procedure's cost] → formulas are per trial and small; a declared bound returns UNDETERMINED.
