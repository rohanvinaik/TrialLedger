# Design

## Context

See `proposal.md` for motivation and the delta spec for externally visible requirements. This plan is a bounded integration of the protocol-writing thesis in `docs/THEORY_OF_THE_CASE.md` and `../add-design-synthesis/design.md`; it does not declare that larger design complete.

Planning baseline: main `25c6bb5c29513f2159751d29c309620522e32425`. Inspection at that baseline found:

| State | Evidence | Consequence for this change |
|---|---|---|
| Working operators | `signals.MODULES` dispatches temporal, dependencies, estimand, decision_table and other independent calculators | Reuse the existing mathematics and support gate; do not replace them with a protocol-specific solver |
| Working managed replay | `design_session.replay`, named `session_projections`, immutable reasoning artifacts | Add typed producers and consumers to this path rather than create a second design manager |
| Short preparation boundary | `request_preparation._questions` generates entailment analyses; `_session` constructs assertion criteria | Extend typed preparation, not clinical prose recognition |
| Decision boundary in two paths | `session_state._decision_inputs` and `design_session._decisions` both require exact entailment/query identity | Preserve v1; implement and test v2 administration and evaluation together |
| Working cross-definition checks | `definition_checks` binds operands to actual analysis requests/results | Use explicit definition relations across endpoint, schedule and policy consumers |
| Working supporting-analysis delivery | `analysis_review` renders independent analyses; temporal summaries lack a schedule grid | Preserve these results and add a clinical protocol view, not JSON-in-cells |
| Still designed, not integrated | Automatic clinical encoding, general statistical design, ranking/significance, autonomous complete writer | No completion claim for these components |

Grounding probes through the public CLI showed that an unlinked assessment/collection graph can be consistent; adding an adopted collection requirement exposes the conflict. With assessment days [77,91] and collection through day 80, temporal satisfiability returns a feasible [77,80]. It does not prove the protocol's whole permitted window is supported. A valid managed estimand analysis is accepted as supporting analysis but refused as a decision alternative (`alternative_requires_exact_entailment_query`). These are the starting counterexamples, not grounds to weaken the current operators.

One retained NIH example, NCT06544330, separately describes DLTs up to 28 days and safety observations up to 96 weeks. It does not supply a complete visit schedule or define every DLT predicate. The new representation must keep those information channels separate. Real records are documentary evidence; simulated design choices remain simulated choices.

## Goals / Non-Goals

**Goals:** connect explicit endpoint, schedule, efficacy and safety design objects to their proper independent checks; preserve useful partial answers; expose the consequential unresolved decisions; make the whole path discoverable and shareable by a clinical-development operator through an LLM. `contracts.md`, `verification.md` and `parallel-work.md` are normative parts of this design.

**Non-Goals:** reinterpret source prose, choose a clinical threshold or dose, certify a human confirmation, infer missing safety standards, estimate treatment effects, solve every statistical family, or make a complete-protocol claim from a passing collection of checks. No new dependencies are presumed necessary. Do not change layer-one reporting or theory to accommodate the implementation.

## Decisions

### 1. Explicit session v2; existing public lifecycle

Use `schema_version: 2` within the existing `design_session` operation and existing preparation, retained-artifact execution, reading, revision and export lifecycle. Keep v1 validation and canonical outputs unchanged. V2 adds the protocol ledger and a tagged protocol-option decision while retaining existing premise/source semantics. A v2 session can still carry legacy assertion decisions.

Why: extending v1's strict shape silently would change old meanings and fingerprints. A separate operation or designer would duplicate source admission, support, budgeting and transport. V2 is an adapter into the current replay, with explicit result additions; it is not another solver.

Versioned objects refer to the current immutable snapshot by stable IDs. Their source/clinical-definition edition is distinct from the draft revision and content digest. Clinical source editions are pinned; a local draft edit cannot refresh them. There is no implicit cross-version migration in this change.

### 2. Typed objects and named projections; source truth stays separate

Objects declare roles and references, not strings to interpret. A common envelope carries exact target/context, support and origin references. Type-specific payloads bind measurement/definition, endpoint, assessment, collection, estimand, efficacy and policy data. Dependencies form a validated acyclic projection graph; policy state cycles live inside the policy model, not in that graph.

Projectors accept only named kinds and validated fields and produce the existing operator requests with an inspectable projection record. They cannot select arbitrary JSON paths, evaluate code, infer a clinical synonym or turn a label into an assertion. Historic source values use the existing immutable source ledger and source-to-assertion rules. Accepting an interpretation establishes the person's premise, not source truth. A binding's weakness follows its actual consumers, not every object in the session.

Alternative considered: load all fields into one generic constraint store. Rejected because source plans, observations, permissions, defaults and new design choices would acquire indistinct force, and the individual operators would lose their own warrants.

### 3. Three schedule questions, exact interval semantics

Preserve permitted window W, nominal target n and planned collection availability C independently. Compute W intersect C, n membership and W subset C, with W minus C as the counterexample. Use exact rational finite interval unions with explicit endpoint inclusion and one exact written unit, anchor and scope. Missing availability is unknown, while an explicitly empty collection set means none is planned for that declared scope.

The existing temporal difference solver continues to check existential consistency and linked relative events. The new schedule calculator owns the set-coverage questions. A window depends on another event only through explicit constraints or a named projection with a warrant; no inference from words such as week, baseline or follow-up. Collection-plan coverage and actual observed data remain separate checks.

Why: forcing coverage into the existing existential solver would permit silent narrowing. Sampling a few times would miss open endpoints and narrow gaps. The bounded exact interval representation has inspectable small-world oracles and counterexamples.

### 4. Endpoint/estimand assembly reuses adopted dependencies

Typed endpoint objects point to explicit variable, definition, population and estimand declarations. Their adopted prerequisites project into `dependency_evidence`; explicit intercurrent-event requirements project into `estimand_evidence`. Existing OR-of-AND dependencies and observed/imputed/derived modes remain authoritative. An endpoint label or treatment-policy strategy alone adds no hidden rule.

Collection requirements link these checks to the schedule only with an explicit bridge: which input, window, population, event and mode. Declared cross-operation meaning relations use `definition_checks`. Equivalent MADRS thresholds, an earlier screening trigger and a two-visit relapse definition are different relations; a numeric mismatch alone is not a contradiction.

### 5. Bounded finite-state policies extend finite tables

Reuse the current finite predicates, domain enumeration, action/prohibition semantics and independent checks. Add states and explicit guarded transitions. Evaluate only reachable states under declared external-input domains; external inputs are nondeterministic over those domains at each step, and all memory must be represented in the state. There is no implicit clinical state update.

Report reachable action gaps, multiple enabled transitions, forbidden actions and invariant violations independently. Check prohibitions against the original feasible domain; never add the prohibition as a constraint that deletes its own counterexample. Return bounded counterexample traces. A terminal dosing state does not stop outcome collection. Termination is uncomputed unless an explicitly requested finite-graph claim is supported; there is no assumed fairness.

Alternative considered: add a large clinical safety vocabulary or a scripting language. Rejected: both hide assumptions and exceed the declared model. The person supplies the variables, scope, rules and source editions; coverage always names that declaration boundary.

### 6. One exact statistical family; others remain visible

Add a one-stage fixed-n independent-Bernoulli, one-sided greater-than calculation. For critical count k, compute exact binomial tails at supplied p0 and p1. This gives conditional type-I rejection probability and power, not clinical validity or an optimal design. No default alpha, power, effect, sample size or test is supplied. Exact rational arithmetic and an explicit work/bit-growth ceiling bound it.

Keep survival, continuous, clustered, multiple-testing, sequential/adaptive and other families as attributed external method declarations with `not_computed` outcomes. Do not coerce their parameters into binomial inputs. If the design contains interim adaptation, its relation to a fixed-n model must be explicit; operating characteristics of that adaptation are not supplied by a fixed-n calculation.

Why include a small real calculation: representation alone would leave the efficacy consumer untested. A tractable exact family exercises assumption binding and downstream propagation without pretending to solve general trial statistics.

### 7. Candidate options are explicit edits plus fresh independent checks

The v2 protocol decision selects declared object replacements and check IDs. Apply replacements to a detached snapshot, validate it and run its declared dependency closure freshly. Do not mutate the baseline, reuse stale results, recursively invoke design sessions or treat one analyst's label as a checked claim.

An unchosen design edit is a local candidate assumption, not a confirmed fact. Reuse the interpretations conditional-frame boundary: compute “if this plan is chosen” without promoting object standing or unresolved external bindings. Return the frame/assumptions and withhold unconditional application. All alternatives must include the same target's required checks; omission is a translation refusal, not a way to obtain compatibility. An explicit adopting revision is needed before a local hypothesis can affect the fixed design floor.

Aggregate only the required checks: accepted applicable conflict makes the option incompatible under those checks; missing required knowledge leaves it undetermined; all required checks discharged makes it compatible under those checks. Proposed checks retain conditional mathematics and cannot change the fixed floor. Optional context remains visible without silently becoming a gate. All options retain each check's own code and warrant, and coverage names the questions that were actually asked.

There is no voting across check families and no generic `consistent` -> `safe protocol` conversion. User selection is an attributed choice independent of compatibility. All accepted global constraints applicable to the target remain in the relevant consistency floor; scoping cannot conceal an applicable contradiction.

### 8. One clinical view feeds replies and files

Produce a pure protocol clinical view from canonical results, then use it for bounded replies, the decision list, protocol synopsis and Schedule of Assessments. Include the source quotation/location where available, profile/cohort, deciding values, standing and exact result reference. Unrequested content is distinguishable from requested-but-open and explicit not-applicable content. Pure rendering does not perform clinical reasoning.

Keep question wording and supplied labels attributed. Extend revision axes to verdict, requirements, support, origin, scope/model assumptions, wording and input-only changes; no label-only or residual-only change is called a clinical verdict change. Keep source workbooks immutable.

### 9. Evidence gates and parallelism are architectural constraints

SICP-style primitives have explicit domains, named outcomes and one mathematical/administrative responsibility. Before behavior edits, trace production references and sibling paths with Serena; workers use the supplied map and whole-unit reading, not separate heavy language-server instances. After edits, trace computed information through admission, replay, decisions, compact results, revision and export.

The coordinator owns shared integration; workers own disjoint modules and tests. Freeze schemas and acceptance examples before distributing work. Integrate vertical slices and run a different clinical category/phase/structure walkthrough after each substantial slice. Final Detective two-sign generation is serialized while the target and relevant test/import basis are frozen. An incomplete pin is a reported limitation, not an automatic waiver.

## Risks / Trade-offs

- [A v2 declaration looks medically complete] -> requested-section coverage and per-check quantifiers accompany every summary; no overall medical-completeness badge.
- [Cross-domain wiring erases uncertainty] -> named projection receipts, actual dependency standing, conditional/application split and paired downstream tests.
- [Combinatorial state/option growth] -> conservative admission and actual work accounting, finite exact limits, separate witness/display caps and retained partial findings.
- [A small statistical family is mistaken for a general designer] -> public method boundary, explicit assumptions, unsupported-family examples and an external-method handoff.
- [Parallel workers drift or overwrite shared state] -> frozen interfaces, disjoint writes, a single integration owner and serialized proof generation.
- [A broad proof claim hides input semantics] -> independent authored intent, mathematical oracles, source-bound clinical walkthroughs and honest target-specific proof receipts.
- [Versioning duplicates whole workflows] -> thin version dispatch around shared existing lifecycle; no copied source reader, budgeter, artifact store or solver.

## Migration Plan

1. Capture baseline v1 public behavior and freeze v2 interfaces, finite limits and schema fixtures before parallel implementation. All tasks in this plan start unchecked.
2. Build pure operators and named projections independently; integrate through existing support and replay boundaries one vertical slice at a time.
3. Add typed public preparation, protocol alternatives, clinical view, revision and export. Retain v1 byte-level canonical regression expectations where currently deterministic; do not rewrite old golds to make tests pass.
4. Complete the current proof and public-entry evidence packets in `verification.md`; reconcile discovery and documentation to the demonstrated boundary. Do not mark the full `add-design-synthesis` writer complete.
5. Commit coherent reviewed changes on main under the user's implementation authorization. No branches/worktrees, force-push or bundled unrelated edits. Roll back a bad coherent change by its commit; retain immutable previous artifacts and independently usable v1 behavior.

No runtime data migration is required. A version-conversion utility, if later wanted, is a separately specified change.
