# Normative implementation contracts

This file is part of the design, not optional builder advice. The founder's instructions and `docs/THEORY_OF_THE_CASE.md` govern. If this contract appears to conflict with either, report the exact counterexample and stop the affected change; do not reinterpret theory, invent a binding or silently change the interface. Independent work can continue. Normative semantics below are frozen by this plan; mechanical schema fixtures must be published by the coordinator before parallel writes.

## C1. Epistemic invariants

1. Source fact, strictly warranted direct rule, accepted clinical interpretation, interpolated default, proposed reading and user choice remain distinct in origin and support. Existing `known/interpolated/proposed` and `resolved/unresolved/conflicting` fields retain their existing meanings. A caller's status declaration does not authenticate a conversation or certify factual truth.
2. A source address/digest establishes which evidence was retained, not what free text means. Only an existing direct rule or an explicit accepted binding can supply meaning. No keyword, heading, label, acronym or name similarity provides a clinical relation.
3. Every conclusion names its actual premises and rule version. Its effective support is no stronger than those dependencies. Graph reachability is not proof that every reachable premise decided the result; retain proof support separately from replay dependencies.
4. Raw conditional mathematics is retained separately from admitted application. Proposed or unresolved bindings cannot rule out accepted possibilities. A proposed counterexample can identify a question without becoming a fixed contradiction.
5. A contradiction among accepted applicable fixed constraints blocks closure of the affected target; it does not prove arbitrary answers. Retain useful independent findings with their own scope. Do not conceal an applicable global contradiction by artificially narrowing a check's declared inputs.
6. Repeated encodings, projections or quotations of one observation are not independent evidence. Counts, rarity and patterns remain descriptive. No clinical objective, preference, standard or new threshold is inferred from their frequency.
7. Units/anchors/measurement definitions compare by exact identity in this change. No implicit conversions, WHO/ECOG equivalence, baseline identity or source-edition refresh. An explicitly supplied conversion or equivalence can be represented as a separately supported binding; unsupported transformation methods remain uncomputed.
8. Eligible, randomized, baseline, analysed and withdrawal populations remain different. Entry, crossover and withdrawal scopes remain different. Seriousness is not grade, a horizon is not a schedule, a registered plan is not an observation, a planned observation is not available data, and a definition alone is not an obligation.

## C2. Compatibility, public shape and ownership

- Existing operation `design_session`, existing CLI/MCP lifecycle and existing artifact store remain the production route. Dispatch explicitly on `session.schema_version`. V1 validation, error codes, query decisions and canonical results must remain unchanged. Unknown versions refuse; no implicit migration. Revision requires matching session versions.
- V2 retains the v1 session fields and adds required `protocol`. Existing optional `definition_checks` remains supported. V2 protocol has exactly `schema_version` (integer 1), `objects`, `checks`, `sections`. Empty arrays are allowed for incremental designs; they do not imply completeness.
- Object IDs, check IDs and decision IDs use separate namespaces, are nonempty and unique, and are stable within a draft lineage. Object refs bind to the current immutable snapshot. Definition/source `version` is a separate field, never inferred from draft revision or changed digest.
- Strict JSON admission preserves null, missing and empty states. Unknown fields, bool-as-int, nonfinite numbers, duplicate IDs, cyclic object dependencies and dangling refs have named translation refusals. No coercion of malformed input into plausible clinical content.
- No new report-acquisition route, source parser, free-text compiler, generic rule engine, artifact store, budgeter or serializer. Extend the existing owners. Library, CLI, initialized MCP, compact reading and export must agree on meaning and exact canonical identities.

## C3. Typed protocol ledger

Every object has exactly `id`, `kind`, `scope`, `version`, `origin`, `standing`, `support`, `depends_on`, `data`.

| Field | Contract |
|---|---|
| scope | `{target, context}` using existing target and cohort/arm/phase context contracts; missing context never inferred from another object's heading |
| version | Nonempty declared definition edition/version; independent of the draft's revision |
| origin | Existing managed-premise origin shape and validation; linked source identity must exist; hypotheses cannot supply accepted facts |
| standing | Existing `{status,resolution,basis}` admission shape; basis must be nonempty and inspectable |
| support | Unique existing premise IDs supporting meaning/adoption; each is a real dependency, not a string claiming confirmation |
| depends_on | Unique protocol object IDs; refs in data must be listed here; forward refs allowed after whole-graph validation; no cycles |
| data | Closed payload for the declared kind, below; no arbitrary code, JSON-path substitution or clinical prose interpretation |

Object own standing and actual support are conjunctive. An own known status cannot erase a proposed supporting premise. An empty support list leaves adoption/application unresolved; it is allowed for a drafted object and must not become a known constraint. Origins remain visible even where two objects have equivalent mathematical content.

The closed kinds and payload contracts are:

| kind | data and role |
|---|---|
| measurement | `definition` (existing supported versioned reference), `unit` (exact string or null if unresolved), `mode` (observed/imputed/derived), `baseline` (measurement ID or null). Definition carries analyte/instrument/specimen/method as explicitly supplied reference content; the implementation does not interpret its name. A baseline ref creates no availability claim. |
| endpoint | `variable` (measurement ID), `definition` (supported reference), `estimand` (estimand ID or null), `dependencies` (existing dependencies signal data or null). Adopted rules and references must match the declared variable and scope. No default change-score rule is added. |
| estimand | Existing estimand signal data, unchanged in semantics. Typed refs bind its declarations/requirements to explicit protocol objects through check bindings, not label matching. A strategy alone creates no requirement. |
| assessment | `measurement` (ID), `anchor` (nonempty event identity), `unit`, `nominal` (exact rational or null), `permitted` (interval union or null), `condition` (existing typed proposition or null). Null condition means unconditional in this exact scope, not all populations. |
| collection | `assessment` (ID), `mode`, `availability` (interval union or null), `event_handling` (null, or `{estimand, requirement, action: collect|stop}` naming one estimand requirement and whether data are collected after the event; declared once here and consumed by the estimand projection, Rohan 2026-11-04). Inherits anchor/unit from the referenced assessment only through this named schema relation; not from similar wording. Availability describes the plan, not observed data. |
| efficacy | `endpoint` (ID), `method` (binomial_design or external_method), `parameters` (C7 data or an external_method object ID), `assumptions` (unique premise IDs). No planning number defaults. |
| policy | `model` (C6 finite policy data), `bindings` (unique explicit protocol/definition binding refs). Safety, dose/titration and efficacy-trigger roles are caller-declared, not inferred from action names. |
| external_method | `definition` (supported versioned reference), `inputs` (named values/units/refs without interpreted force), `missing` (explicit unresolved input names). Retained and exported; no method execution or script evaluation. |

All supported references reuse the existing reference shape with `ref`, `version`, `status`, `resolution`, `basis` where that operator requires it. Do not invent a weaker second support model. The coordinator publishes exact JSON Schema fixtures for each reused structure and one valid/malformed example per kind before releasing worker contracts.

Sections have exactly `id`, `state`, `objects`, `basis`. IDs are `population`, `eligibility`, `interventions`, `endpoints`, `assessments`, `efficacy`, `safety`, `exploratory`. State is `requested` or `not_applicable`; objects are declared relevant object IDs; not_applicable requires attributed nonempty basis. Omitted sections are `not_requested`, never silently complete. Computed section coverage is `specified`, `open`, `not_computed` or `not_applicable`, with reasons; `specified` means represented, not medically exhaustive. Eligibility/intervention sections can cite existing premise IDs through check bindings rather than duplicate those data as protocol objects.

## C4. Checks, projections and results

A check has exactly `id`, `kind`, `scope`, `objects`, `bindings`, `claims`, `required`, `support`. Scope uses C3's exact target/context contract; applicability to a decision is never guessed from an object label. `required` is a strict bool. `objects` and `support` are unique declared object/premise IDs. Bindings are closed named projection records, never caller-chosen JSON pointers. Claims are explicit typed obligations, not labels. Incompatible input scopes require an explicit supported relation or an unresolved binding; a projector cannot silently widen them.

| check kind | Allowed projection/claim and existing owner |
|---|---|
| temporal | Existing relative-event temporal data and explicit linkage, using graph_evidence; no universal-coverage claim |
| schedule | assessment plus collection -> C5, claims `existence`, `nominal`, `full_window`; nonempty subset explicitly chosen |
| dependencies | endpoint.dependencies -> dependency_evidence with explicit measurement/mode/window bindings |
| estimand | estimand -> estimand_evidence, preserving requirement, relevance, plan alignment and actual-input axes |
| definition | Existing definition_checks operands/relations bound to actual child requests/results; no arbitrary pointer operand |
| decision_table | Existing finite table/prohibition request, unchanged |
| finite_policy | policy.model -> C6; claims coverage, exclusivity, prohibition, invariant, or explicitly requested graph termination |
| binomial_design | efficacy -> C7; exact probabilities plus explicitly requested tail/power threshold comparisons |
| external_method | Retain the declaration; return not_computed with method and missing input refs |

For kinds reusing existing requests, `bindings` uses their existing typed shapes wrapped by a named projector, and `claims` contains only the kind's advertised claims. The coordinator's schema fixtures freeze these compositions before worker coding. There must be a bounded public way to supply relative temporal constraints and reused supporting analyses; do not require arbitrary analyses JSON for ordinary assessment windows.

Conditional objects are evaluated only in their declared applicable cases. Use existing typed entailment/finite domains to establish applicability or enumerate feasible conditional cases within the work bound. An unresolved condition yields an explicitly conditional result, not an unconditional success or an assumed false condition. Mutually exclusive cohorts keep separate windows; do not intersect them as if both applied to one patient. Definition relations and global requirements participate only with their adopted applicability and standing.

Each projection receipt records `projection`, `version`, `objects`, `premises`, `target`, `scope`, `bindings`, `request_digest`. Every constructed child request/result is retained canonically with its digest and result address. Dependencies participate in normal replay ordering and budget reservation.

New mathematical operators expose `evaluate(kind: str, data: dict) -> dict` and `check(kind: str, data: dict, claims: list[dict]) -> dict` in the existing signal operator contract: exactly `code`, `value`, `blockers`, `rule`, optionally the existing paired `support_status`, `determining_ids`. New kinds are registered through the fixed `signals` owner and use its support gate. They do not return an independently invented admission verdict.

The v2 protocol check view retains: check ID/kind, exact claim/quantifier, raw calculation code, effective application code, standing, scope, deciding IDs/rules, values/counterexamples, blockers, declared model coverage, projection and canonical child reference. Retain full existing envelopes; do not rewrite canonical child codes into one common truth value. All finite check classifications are named codes, not overloaded bools.

Independently decidable claims require independently gated support. Either project them into separate signal evaluations or retain equivalent per-claim admission/proof records using the existing gate. Do not let unknown C erase a proved n outside W, or let a proposed unrelated requirement weaken a known conflict. A family summary may remain unresolved while its known rows remain usable; consumers must read those rows rather than only the aggregate code.

Translation refusal, completed calculation, mathematical outcome, admissibility, proof completeness and clinical model coverage are distinct axes. A valid request may have an unresolved conclusion. A finished computation may refute a desired obligation. Unknown future codes remain safely unclassified; every code introduced by this build must have tested metadata, clinical wording, revision and export mappings.

## C5. Exact schedule operator

`schedule_coverage` data: exactly `scope`, `anchor`, `unit`, `nominal`, `permitted`, `available`. Scope is the validated exact scope reference; anchor/unit nonempty exact identities; nominal is a rational or null; permitted and available are interval unions or null. A union is a list of `{lower,upper,lower_inclusive,upper_inclusive}`. Endpoints are canonical rational strings or null for infinity; inclusion at infinity must be false. No floats. Reversed or empty single intervals are invalid; an empty union is valid explicit emptiness. Normalize unions without filling gaps.

Exact rational strings accept signed integers or integer fractions with positive denominator; canonical output is reduced with positive denominator, integers rendered without `/1`. Zero denominator, NaN, whitespace approximations and malformed numbers refuse. Input numeric-component bit cap is 256. Nominal has its own existence; null never defaults to midpoint. All comparisons use the same unit and anchor; incompatible bindings leave application unresolved, not silently converted.

Return independent named claims with the original W, n and C:

- `existence`: satisfied iff W intersect C is nonempty; return feasible union. Empty W means no permissible assessment, never an overall successful schedule.
- `nominal`: satisfied iff n belongs to both W and C; distinguish outside_window, not_collected and unknown_target.
- `full_window`: satisfied iff W is nonempty and W minus C is empty; return the exact uncovered union. If W is empty, code no_permitted_time rather than vacuous clinical success.
- Missing W/C yields unresolved only for dependent claims. Even when C is unknown, a known n outside W can be reported independently as outside_window. Preserve every independently proved fact.

Clinical obligation quantifiers are in the check. Do not automatically turn a permitted window into a full-coverage obligation; the operator can show the gap, while the person decides whether to narrow the window, extend collection or adopt another plan. Examples must include planned intervals versus individual actual observations, repeated visits, event-relative windows, conditions and separate post-discontinuation requirements.

## C6. Bounded finite-policy operator

`finite_policy` data: exactly `scope`, `version`, `variables`, `constraints`, `states`, `initial`, `terminal`, `actions`, `transitions`, `prohibitions`, `invariants`. Reuse the finite decision-table variable/domain and typed proposition representation; no new predicate parser. States are unique strings; initial/terminal are unique subsets with at least one initial state. The reserved enum variable `policy_state` is supplied by the state, never by caller external input. Every other variable has a finite declared domain; missing domains refuse. Constraints restrict the original feasible valuations and retain explicit support. Action definitions are `{id,scope,description}`; scope is exactly participant, cohort or study plus its declared target reference. Description is attributed wording, not interpreted effects. Unknown action refs refuse.

Transitions: `{id,from,to,guard,actions}`, with exact declared states, existing typed guard and unique nonempty action IDs. Action definitions retain their declared participant/cohort/study scope through explicit bindings; no cross-scope aggregation is invented. A terminal state has no outgoing transitions. Inputs may vary nondeterministically between steps; guard predicates read the current state and external valuation. Memory, counters and time progression must be explicit state/domain variables; no implicit numeric clock update.

Prohibitions and invariants: `{id,state,condition,actions,rule}`, where state is a declared state or null (all states), condition is typed, rule is a supported versioned reference. Prohibitions name forbidden action IDs. Invariants have an empty actions list and require their condition in each reached pre-transition valuation. Do not mutate the feasible domain to satisfy them. If a more expressive postcondition is needed, represent its state explicitly or report unsupported; do not invent assignment semantics.

Enumerate the finite feasible reachable model. At each reachable nonterminal state/valuation, zero enabled transitions is a gap; more than one is a competing transition even if actions are identical but next states differ. Any nondeterminism must be resolved as an explicit design choice, not row order. Terminal states are exempt from action coverage only, not from invariants. Keep independent `coverage`, `exclusivity`, `prohibitions`, `invariants`, `reachability` and optional `termination` results. No obligations of a kind -> `not_declared`, not safe.

Establish that at least one declared initial state/valuation is feasible before universal claims. An empty feasible initial model is `inconsistent_domain`, not vacuously covered/safe/terminating. Reachability nodes are feasible state/valuation pairs. An enabled transition to a state with no feasible valuation is a named transition-target conflict, not silently discarded to make coverage pass. Counterexample traces retain that attempted transition.

Return bounded shortest counterexample state/input/transition/action traces, deterministic tie ordering, exhaustive coverage counts, original variable domains and assumptions. A witness-display cap never stops the deciding exhaustive check. Finite reachable cycles are possible infinite paths in the declared transition model, not evidence that patients will fail to terminate. Termination, if requested, means all permitted paths reach a terminal state; no fairness assumption is supplied implicitly. Acyclicity alone is insufficient when a reachable dead end is not terminal.

## C7. Exact one-stage efficacy operator

`binomial_design` data: exactly `scope`, `model`, `direction`, `n`, `critical_count`, `p0`, `p1`, `assumptions`. Model must be `fixed_n_iid_bernoulli`, direction `greater`. n is a strict positive integer; k=critical_count is a strict integer in [0,n+1]. p0/p1 use C5 rational syntax and satisfy 0 <= p0 < p1 <= 1. Assumptions are 1 to 16 unique standing references `{role, ref, version, status, resolution, basis}` with `role` in `fixed_n`, `iid_binary`, `alignment` (roles may repeat; whole records may not). The ledger-level efficacy object declares them as `{role, premise}` pairs, which the projection turns into these references with each premise's actual standing (README R3). Unsupported direction/family has a named unsupported_method result; malformed numbers are translation refusals.

For k <= n, compute sum over i=k..n of choose(n,i)*p^i*(1-p)^(n-i). k=0 always rejects; k=n+1 never rejects. Define endpoint cases exactly, including 0^0 in the binomial mass as the combinatorial value 1. Return exact reduced rational `null_rejection_probability` and `power`, n, k, probabilities, model and actual assumption refs. Display decimals are explicitly rounded conveniences, never the canonical value or comparison basis.

Claims are `{id,quantity,comparison,value}` with quantity null_rejection_probability or power; comparison <= or >=; value exact rational in [0,1]. No alpha/power/effect defaults. A supplied upper alpha bound is compared with null rejection probability; do not call the supplied bound the computed type-I error. Any applicability gap retains conditional arithmetic but withholds a settled clinical application.

Hard n ceiling 512; rational component cap 256 bits; intermediate rational component ceiling 1,048,576 bits. Account exact arithmetic work and bit-growth before/while running; bound exhaustion cannot return a rounded answer as exact. Do not search n or k, optimize, simulate, extrapolate to sequential stopping or validate clinical model assumptions by arithmetic. External-method declarations remain usable, visible and uncomputed.

## C8. General protocol decisions

A new v2 decision has `kind: protocol_options` plus existing `id`, `question`, `target`, `coverage`, `selected`, optional `evidence`, and `alternatives`. Legacy query decisions retain the existing shape and semantics. A protocol alternative has exactly `id`, `label`, `replace_objects`, `checks`. Replacements are complete typed objects with existing IDs and unchanged kind/target; there is no generic JSON patch, arbitrary delete, source replacement or automatic permission override. All replacements carry attributed origin/support and can edit only the new-trial draft. Checks are unique declared check IDs; every alternative must include every session check marked required for that decision target. Scope-inapplicable checks are evaluated as such with a warrant, not silently omitted. Optional context check sets must be the same across compared alternatives. At least one required obligation is necessary for any compatibility claim.

Apply replacements simultaneously to a detached baseline. Resolve refs from that candidate only, validate and recompute all required dependent checks and applicable fixed constraints. Preserve baseline results separately. Reuse of immutable source bytes is allowed; reuse of an old computational verdict as fresh is not. Candidate edits cannot change which checks are required, hide evidence or promote proposal standing. Structural alternative designs use predeclared objects/conditional applicability; expanding the structure is an explicit revision, not an option-side schema trick.

Unchosen draft edits are explicit local hypotheses, not forged clinician confirmations. Reuse the existing interpretations distinction between local conditional calculation and admitted fixed application: `replace_objects` declares precisely which new-draft object values are assumed in that candidate frame. The frame may evaluate those values mathematically even when their own origin is hypothesis/proposed or they have no prior adoption support. It must not lift proposed external source readings, unresolved dependency bindings, clinical equivalences or model applicability premises. Those remain blockers unless separately and explicitly assumed in an existing interpretation frame, whose conditions must also be returned. Never mutate the original standing fields or the fixed floor.

Every candidate result carries `frame` (fixed or hypothetical), `assumption_refs` and `unconditional_application` (admitted or withheld). A hypothesis-dependent result is marked hypothetical, retains proposed origin and withholds unconditional application; say “if you choose this plan, these checks follow.” Local compatibility is not admission into another session's fixed floor and cannot be exported as an unconditional derived premise. Selection alone does not promote the edit: an explicit attributed revision adopting the new premise and a fresh replay is required. This permits useful what-if comparison without weakening the no-proposed-premise rule.

Aggregate named codes: `incompatible_under_declared_checks` for an admitted applicable required violation; `undetermined` for unresolved/unexecuted/unsupported required checks; `compatible_under_declared_checks` only when at least one required obligation is discharged and every required obligation is satisfied or explicitly supported not_applicable. For hypothetical candidates, admitted means within the explicitly returned local assumption frame; a conditional failure can refute that plan under those assumptions but is not a fixed-floor contradiction. Proposed external evidence cannot be admitted through this shorthand. Return all independent checks even when one blocks; translation-invalid candidates are invalid, not clinically excluded. No check voting and no promotion to safe/effective/optimal/complete.

Decision disposition is separate: user selection, evidence question, translation question, computation task, blocker, or design choice. Design choice requires explicit alternatives shown compatible under the same declared required checks and distinguishable in actual represented content; a conditional design choice names its candidate assumptions. Do not use labels to prove distinction. Unknown scope, unsettled source readings and incomplete rules are not design freedom. Selection cannot erase a blocker or independently authenticate a person.

## C9. Public preparation, delivery and revision

- Extend the existing short typed preparation contract with explicit schema_version 2 and the same `protocol`/protocol-option structures. Do not force ordinary users to manually construct projected signal supports, digests or child envelopes. Preparation produces those mechanically and lists every administrative default. Clinical values, support, scopes, methods and adoption are never defaulted.
- The public object-ID builder and focused runnable examples must cover endpoints, schedule, finite safety, efficacy and two non-entailment alternatives. Full schema and advanced request forms stay available on demand. A cold MCP-only operator must complete the lifecycle without source code or helper scripts.
- Build one pure clinical protocol view consumed by compact replies, markdown and workbook export. Keep canonical results retrievable with pages bounded by bytes and entries; all continuation must work. No result is made to fit by truncating source text, dropping options or deleting unknowns.
- Workbook adds Protocol synopsis and Schedule of assessments sheets to the existing review export, not to the layer-one workbook. Schedule rows include object/check ID, cohort/arm/stage, conditionality, measurement/mode, event anchor, unit, nominal target, permitted window, collection availability, feasible window, full-coverage gap, standing/origin and clickable evidence/result refs. Use clinical text, separate numeric/context columns and bounded summaries; JSON belongs in canonical artifacts, not clinical cells.
- The readable decision list must include consequential supporting analyses: policy violations, funnel bounds, estimand mismatches, schedule gaps and statistical claims where they inform this session. Keep existing stages/count analyses reusable even though this change adds no new population arithmetic.
- Revision replays both snapshots including alternatives; returns independent changed axes for verdict, residual requirements, support, origin, scope/model, wording and inputs. Clinical answer changed requires an actual verdict/decision consequence change, not only a changed digest or unrelated residual. Changing an equivalence premise may change support without changing the verdict; report both.

## C10. Work bounds and completion

Protocol hard ceilings: 256 objects, 128 checks, 16 alternatives per decision, 32 intervals per supplied union, 32 policy states, 128 transitions, 4096 external finite valuations, 64 displayed witnesses per check. In addition, the existing session limits still apply. Set a protocol-work hard ceiling of 1,000,000 charged primitive obligations; actual operator work/bit bounds remain enforced independently. Lower configurable limits are allowed; no silent increases.

Admission reserves a conservative bound on actual interval comparisons, reachable-state/valuation/transition checks, exact arithmetic and baseline/candidate/old-new replay. The coordinator must publish and test each reservation formula before integration; numbers must not be arbitrary maximum-per-call multiplication when a smaller safe represented bound is known. Bound validation includes cases just inside/on/outside each ceiling. No charging retained source bytes as clinical solver assignments, no treating reply size as NIH query scope, no increasing limits to hide an accidental whole-registry query.

If a bound stops a check, its claim is unexecuted/limited, not satisfied. Preserve independently completed results and a named limit with reserved/actual work and configured ceiling. Display caps are separate from deciding work. `verification.md` defines completion; a worker handoff, green unit suite, passing schema validation or a large kill count alone does not complete this change.
