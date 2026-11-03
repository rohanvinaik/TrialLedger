# Design — symbolic automated trial writing

## Context

This consolidates the existing layer-two designs. The founder's intended system is fully designed; its
components and pipeline have different implementation states. The reporting record remains an independent
source-preserving product. A useful finite solver or corpus calculation is retained even before automatic
source compilation and complete brief-to-protocol orchestration are connected.

## Goals / Non-Goals

**Goals:** construct a clinical trial from explicit premises and warranted evidence; preserve the distinction
between deductions, interpolated defaults, proposals and human choices; keep correct partial symbolic tools
usable by an agent; provide the complete existing design and an honest component/integration map.

**Non-goals:** word matching as a substitute for meaning; a model extracting source facts or inventing a
protocol; clinical interpretation in the layer-one writer; new governance frameworks; using a narrow
historical demonstration as proof of broad clinical correctness.

## Decisions

### 1. One evidence substrate, two separate operations

Layer two consumes retained layer-one evidence, additional attributed evidence and explicit user premises.
It never changes a registry assertion in place. Its output is a separate reasoning or design result. Source
identity, record version, locations, raw text and rule versions accompany each use. User/agent-supplied typed
premises are labelled as such: syntactically valid JSON is not proof that they are facts about a trial.

The assistant operates the system in clinical language. It can call a partial symbolic operation without
claiming that the complete designer has run. Reporting and its verifier do not import or invoke this layer.

### 2. The brief and design space

The brief names intervention, indication, population, phase, clinical question and optional comparator,
duration, priority or other constraints. Empty or structurally invalid briefs are refused by name.
Variables have declared domains and semantics: participant population, condition and extent, prior treatment,
intervention roles, comparator, eligibility constraints, endpoints, schedules, safety, exploratory measures
and sample-size inputs. Missing values remain domains of possibilities rather than arbitrary defaults.

Conditional reasoning operates on that structure. Restricting a declared population domain eliminates its
other values. A bound on an exposure interval constrains that interval; it does not silently bind the trial's
follow-up or enrollment window instead. Clinical facts relating these variables require sourced or explicitly
chosen premises. No new medical rule is created merely because it sounds plausible to an agent.

### 3. Source identities and domain knowledge

RxNorm resolves the named entity and its ingredient/product relationships. RxClass supplies its separate
pharmacologic, mechanism, ATC or structure assertions. Aliases confirm or conflict with identity; an ingredient
is not a whole combination, a salt is not automatically every base-product record, and a biosimilar is not
silently the reference product. Trial-level MeSH remains trial-level unless a warranted link binds it.

MeSH, NCI Thesaurus and other declared vocabularies supply versioned concepts and relations. Equivalent,
broader, narrower and associated are distinct. A relation transfers membership only when its direction and
scope entail it. UCUM governs exact unit relations; measurement identity also retains analyte, specimen,
method and reference basis. Absolute values and multiples of a reference limit remain different objects.
Licensing and editions are explicit; no unsupported code or scale edition is invented.

Recognition is literal encoding: candidate entity, number, comparator, unit and original span. Its output is
not a clinical assertion. A concept hit alone cannot decide a condition versus exposure, current disease
versus history, participant versus partner, or a planned procedure versus prior treatment.

### 4. Scoped assertions and compilation

The representation keeps assertion id, source/criterion reference, subject, predicate, typed value, modality,
body, applicability, cohort/arm/phase, branch, temporal scope, evidence spans, rule and epistemic status.
Bodies preserve literal, conjunction, disjunction, negation and opaque unresolved parts. Modalities distinguish
required, excluded, permitted, definitional, descriptive and unresolved. Scope and time are semantic content,
not annotations to discard after recognition.

Compilation consists of bounded decisions over structure: item/list boundaries; coordination and alternatives;
referents; predicate identity; qualifier and measurement attachment; temporal attachment; local normative
force; conditional applicability; cohort scope and resets; definition/reference binding; consumer projection.
Each retains all supported alternatives, names ambiguity and emits no unconditional projection while its binding is
unresolved. Named hypothetical projections remain usable inside isolated interpretation frames. A grammar rule can support known only when its construction and bindings actually warrant that
conclusion; test accuracy alone does not supply the warrant.

Required(A or B) entails neither A nor B separately. Excluded(A and Q) does not exclude every A. Required
(stability if used) does not require use. A definition alone imposes nothing. A negative assay is not an absent
condition without a relation that establishes it. A caregiver's or partner's attribute does not transfer to
the participant. Cohort labels are not an exhaustive partition unless the source says so. Event-relative time
stays attached to its event; unspecified boundaries and anchors remain unspecified.

#### 4a. Retained-source bridge and admission

`source_assertions` accepts one complete retained NIH API v2 study. It binds identity using the existing
canonical study digest, distinct from an HTTP-body hash, and retains last-update metadata separately.
Content identity is not a clinical protocol edition. Exact JSON pointers, expected typed values, matching
content digests and optional half-open Unicode spans locate source evidence; invalid/stale anchors are
translation refusals, not clinical refutations. Missing, null, empty and malformed remain distinct.

Only a named source-defined direct rule can create a fixed assertion. The initial structured rules cover
minimum/maximum age with complete NIH integer/unit syntax, preserving units and registered eligibility role.
They establish what the registry encodes, not independent truth of the actual protocol. Unsupported syntax
and other source fields remain retained/uncompiled; age groups or nearby prose cannot fill a missing bound.

Clinical readings use exact anchors and the existing scoped logical objects. Their bodies, alternative
structure, subject, modality, conditions, qualifiers, cohort, branch and time remain intact. All prepared
readings, local signal support and population/definition bindings remain proposed regardless of submitted
labels. The submitted objects remain inspectable beside prepared objects. An unresolved derivation remains
unresolved. Exact value hydration copies a selected source cell into a hypothetical signal without guessing
its population, scale, role or denominator correspondence. Local IDs never join modules automatically.

The bridge returns reusable requests and runs them through existing entailment/interpretation consumers,
retaining complete responses. Empty queries are inspection only. It does not fetch sources, mutate reports,
repair registry values or insert derived statements into corpus counts. Coverage identifies compiled rules
and unresolved source content without claiming a complete clinical text compiler. The persisted ownership,
negative obligations and clinical workflow are in `docs/SOURCE_ASSERTION_BRIDGE_PLAN.md`.

### 5. Strict reasoning, defaults and proposals

For a context, a requirement constrains scope and applicability to imply its body; an exclusion implies the
negation of the whole body. Permissions do not impose presence. Definitions expand only through resolved
references. Known premises must be satisfiable before entailment: a query holds only if every admissible
assignment satisfies it. An inconsistent premise set returns INCONSISTENT rather than entailment by explosion.
Unsupported queries, out-of-scope queries, unresolved support and resource exhaustion remain distinct outcomes.
The existing exact finite-domain solver provides a bounded implementation of this operation.

Coordinate closure begins from declared finite domains and explicit typed evidence. Relations eliminate
values with a recorded cause until a fixed point; relation order does not decide the answer. NSCLC coordinates
are a domain-specific space, not a default space for every study. Disease extent, treatment history at
entry and the role of the tested treatment are separate variables. Applying staging or other specialised
relations requires their indication, site and edition.

Rule kind is strict, default or proposal, independently of approval. Strict conclusions retain their
premises. Defaults have explicit applicability/defeaters and declared strata; their joint consequences are
checked, implicated conflicts suspend them and trigger recomputation, and unsupported cycles are named.
Anything depending on a default remains interpolated. Proposals are shown independently and never used as
accepted premises. An explicitly hypothetical interpretation may assume a proposal locally, retaining that
assumption in every warrant; it never inserts it into the fixed floor, ordinary entailment or source corpus.
A user override retains provenance and recomputes dependants; it does not change source evidence.

Independent sources constrain the admissible space. Their identities and dependencies are retained, so the
same underlying evidence cannot be counted twice. Concurrence is not majority voting; disagreement is kept
rather than resolved by choosing a preferred token, source or first answer.

#### 5a. Competing interpretations and conditional warrants

Layer one explicitly supplies the rigid evidential/definitional floor and ceiling: retained source facts,
source-defined direct transformations and their scopes. Layer two operates within those bounds, preserving
separate possible interpretations, suggestions and exact consequences conditional on a declared reading.
Uncertainty of a reading and exactness of reasoning under that reading are separate axes. A useful reading
need not be uniquely established before its consequences can be explored. Compatibility is satisfiability,
not proof of intended meaning or a recommendation.

The `interpretations` operation receives a study reference, fixed scoped assertions/signals, source-bound
population/definition bindings, isolated interpretations and named proposition queries. An interpretation
retains id, clinical label, origin, basis, hypothetical scoped assertions, local signals, grouped signal
claims and binding uses. Each use names the target signal and exact study/population/arm/time/version scope.
Population bindings distinguish same-universe, subset and exhaustive-partition relations. Definition bindings
identify the adopted rule and its edition. Source references retain version, address and optional digest.
Matching titles/counts or retrieval success cannot manufacture any relation.

The operation first checks the fixed floor independently, then each interpretation in isolation using the
existing entailment and partial-evidence operators. Explicitly assumed proposals can be compiled in a private
hypothetical environment; original status and premise identities remain in the output. Nothing is admitted
to the source record. A fixed-floor contradiction blocks closure without explosion. Assumption-only
inconsistency is distinct from a reading refuted by fixed evidence. An interpolated floor can support only
an explicitly conditional refutation. Resource limits, unresolved scopes and binding mismatches retain the
reading as unresolved, rather than proving the clinical design impossible.

Every frame returns its conditional calculations and query answers beside compatibility, binding checks and
warrants naming rules, fixed premises, assumptions and blockers. Unresolved binding must not discard the raw
counts or conditional arithmetic. Fixed-floor answers remain separately available. Consequences shared by
all surviving readings are labelled relative to that declared family; an unresolved survivor prevents
overconfident closure, and a sole survivor never certifies an exhaustive reconstruction of the actual trial.
Selection records a user's choice, rejects admission of a refuted frame, preserves rival results and
recomputes from the full revised snapshot without changing standing.

Work the clinical question before wiring a new inference. For a proposed adult NSCLC trial, WHO PS source
observations do not choose an ECOG range. An interpretation of a first scheduled 42 ±7-day assessment yields
[35,49] exactly within its frame; an actual unscheduled scan is a different event and cannot refute that
schedule merely by occurring outside it. ITT, EFS and EFQ remain distinct populations; a cohort binding can
enable subset/overlap arithmetic without explaining missing assessments. An adopted observed-only endpoint
requires its declared inputs; imputation is not an observed measurement. The assistant uses these contrasts
to ask consequential questions and update the decision list rather than insist on an already recovered
protocol before offering useful analysis.

This implements the semantic-specification pattern of candidate readings constrained within explicit frames,
with retained plurality and a contradiction channel capable of breaking the working interpretation. It does
not claim a PAC error bound, an exact-learning identification certificate for the whole protocol, or a
complete enumeration of clinical meanings. The implementation plan and ownership contracts are persisted
in `docs/INTERPRETATION_IMPLEMENTATION_PLAN.md`.

### 6. Corpus descriptions and comparability

#### Partial-evidence constraints and representational capacity

The separate `signals` operation evaluates explicitly typed partial evidence. Independent operators own
count bounds (overlap, exhaustive/disjoint partitions, exact summaries and population lineage), temporal
order/interval constraints, bound regimen composition, directional source relations and adopted-rule
measurement prerequisites. Each returns a named bounded/consistent/conflict/unresolved result, rule version,
source/support references and blockers. These are mathematical/structural operators over caller-bound facts,
not clinical text readers. API/document adapters and clinical bindings retain their existing integration status.

Support is a nonempty list of independently identified premises with status, resolution and source/version
references. The weakest accepted standing propagates. Proposed or unresolved support cannot constrain a
candidate. Matching counts, titles, gene names, units or ontology indexing alone never establishes a binding.
Conflicts and computation limits are named rather than turned into empty domains or guessed values.

Count outputs retain lower and upper bounds. Same-universe marginals may establish a guaranteed overlap
without any independence assumption; no observed overlap point value is invented. For example, counts
126 and 1140 in the same 1217 participants bound their intersection to [49,126]. This requires explicit
study/version/population/assessment alignment. Summary operators distinguish full ranges and exact medians
from confidence intervals and rounded summaries. Partition complements need warranted exhaustiveness and
disjointness. Population differences require explicit subset identity and mean nonmembership in that
analysis, never automatically missingness, treatment nonreceipt or ineligibility.

`design_bounds` consumes these results in two ways. A derived observation references a named signal and
witness, whose expression is constructed from explicitly bound tagged predicates (including conjunction,
complement and measurement comparisons). Its guaranteed lower count is used against the exception allowance;
the complete interval remains visible. A candidate can also declare typed claims against a named signal.
All claims for the same signal are conjoined before checking compatibility. A warranted incompatibility
eliminates the candidate; unresolved checks retain it. No automatic cross-signal scope or identity join occurs.
The standing of signal-driven eliminations feeds the same surviving-design consequence calculation.

Observed acceptance and attributed rejection are distinct witness directions. Acceptance requires a feasible
completion P AND E; rejection requires P AND NOT E for profile P and candidate eligibility formula E.
An incompletely described rejected profile never supplies a universal exclusion. Both directions reuse the
existing scoped formula compiler and finite evaluator. Internally inconsistent candidates remain distinct
from an impossible profile or a resource-bound observation. Report/source records remain unchanged.

Temporal constraints retain event identity, anchors, units and strict/inclusive limits; actual and planned
events are not silently equated. Regimen evidence retains assigned/aggregate/observational roles, product
identity and explicit completeness. Directional relations transfer only what their declared relation kind
warrants. Dependency rules apply only when adopted in the applicable scope; missing input is unknown,
explicitly unavailable input can conflict, and imputed inputs do not satisfy observed-only requirements.

The public path is CLI/MCP reason -> service -> independent signal operators -> derived witnesses and/or
joint candidate claim checks -> design_bounds -> surviving-design consequences -> assistant decision list.
Every operator has runnable discovery and independent intent/countermodel tests. End-to-end tests perturb
source counts, alignment, bridge standing, temporal cycles, relation direction and prerequisites, proving
that these signals reach the returned design answer rather than remaining isolated helpers.

#### Baseline witnesses constrain candidate designs

The `design_bounds` operation tests declared candidate eligibility designs against typed baseline observations.
One observation retains its population, denominator, positive count, source references, proposition and entry
context. Its bridge explicitly binds observed participation to eligibility at the proposition's scope and
time, with provenance, resolution, epistemic standing and a maximum number of exceptions. This is caller-supplied
binding, never automatic interpretation of a table title. A bridge marked proposed or unresolved supplies no
eligibility constraint. Known source observations do not promote an interpolated bridge.

If a candidate's scoped constraints refute the observed proposition and count exceeds its bridge's exception
bound, that candidate is ruled out. Missing or zero categories never exclude a value. Counts from separate
observations are never added: marginal tables can overlap, as can aggregate and arm rows. Candidate restrictions
use the existing entailment engine, preserving alternatives, qualifiers, applicability, scope and time. A
resource bound or unresolved premise is not incompatibility. Internally inconsistent candidates are reported
separately. No survivors is a conflict within the declared candidate set, never universal entailment or proof
that the actual protocol is impossible.

Surviving candidate designs feed a common-consequence query through the same engine. A conclusion holds only
when every remaining candidate establishes it; its standing includes the support of candidate eliminations.
The candidate family is explicit and not assumed exhaustive of real protocols. For a family WHO PS <= U,
observed eligible PS 2 witnesses rule out U < 2; they do not establish U = 2. WHO PS is not silently ECOG.
Observed participation remains a source fact while protocol admissibility remains conditional on the bridge.
The operation neither rewrites eligibility text nor inserts derived bounds into corpus statement counts.

This implements a bounded part of tasks 5–7 and 10 without claiming general source compilation, default conflict
strata or complete protocol orchestration. Its public path is CLI/MCP reason -> service -> design_bounds ->
scoped entailment -> candidate survival -> common consequence -> assistant decision list. Reporting remains isolated.

A declared corpus and strata define every denominator. Known definite members and possible members remain
separate. Statement rate is S/N over all records in the declared stratum; for eligibility, full-criteria
frequency has identification interval [S/N, (S+U)/N], with unresolved silences counted and no rule match never
read as absence. A standard threshold is met only when its lower bound reaches it, fails only when the upper
bound falls below it, and is otherwise unresolved. Endpoint statement rates are not eligibility intervals.

Mechanism association is a statement-rate comparison, with class uncertainty, sponsor/program and era context.
A proposed signal must survive the declared adverse reading of unresolved records; otherwise it remains
unresolved. Association is not a causal clinical rule or a recommendation until its separate warrant holds.

Observed outcome comparisons require compatible population/cohort, endpoint, measure type, unit, time and
analysis context. The source protocol's success criterion, actual results and a new planning target are
three objects. A threshold for the new trial requires its explicit decision rule. Safety keeps affected,
at-risk and event counts, ascertainment, period and grades under their stated terminology version; seriousness
alone supplies no grade.

#### Consumer admission and translation diagnostics

Every public coordinate evidence item has explicit standing; missing standing remains pending. Known and
interpolated evidence have separate closures and provenance; proposed/unresolved rows constrain neither.
Corpus trials declare standing with per-feature overrides so mixed records retain independently usable
facts. Counts admit known/resolved support only. Zero-admitted candidate features stay visible, and pending
readings have their own counts/bounds rather than becoming source absence or abbreviation. Association
strata and near-miss trials with pending relevant inputs have named abstentions. Occupancy retains known
class information while separately widening pending settings. Expectation observations require inherited
or per-row support before entering rarity denominators. Standings are accepted premises, not independent
certification of source truth; no automatic source compiler is implied.

An exact same-predicate mismatch of subject, unit or temporal identity may explain an entailment abstention.
Such diagnostics never establish clinical equivalence or alter logical decisions. WHO PS/ECOG transfer
requires an explicit scoped relation with its own warrant, not a lexical alias. The public consumer map,
remaining integration work and migration are in `docs/REASONING_CONSUMERS.md`.

### 7. Information geometry, expectations and significance

Logical state, frequency, association, rarity and question-specific relevance remain separate. The geometry
records the declared design coordinates and feasible alternatives. Cells are occupied, unknown or empty;
failed and withdrawn trials still occupy cells, and a cell is empty only when no unresolved trial could fit.
Infeasibility requires a constraint. Calling an empty region underserved additionally requires evidence of need.

For a predicate Y and declared context C, corpus rarity is -log2 P(Y=1|C) for presence and
-log2 P(Y=0|C) for absence, with support counts. C excludes Y and consequences inferred from Y. A parent
hierarchy can provide broader support, explicitly labelled; it cannot invent subgroup evidence. If P denotes
presence probability, absence uses 1-P. This fixes the earlier plan's inverted absence-event expression; it
is a definition of this corpus statistic, not a replacement for the founder's significance framework.

The founder's derivational significance refers to what the admissible alternatives of a derivation afforded.
It must retain that alternative space and its relation to the question. It is not claimed merely by applying
corpus rarity, an arbitrary scalar or a frequency cut-off. A common protocol element can be essential while
rare information can be irrelevant. A genuine zero or orthogonality needs evidence; unknown is not zero.

Observations distinguish present, explicitly negated, not documented, unresolved and not applicable. A
mismatch is classified as invalid extraction, unresolved scope, verified deviation or explanation supported.
A valid unexplained deviation is retained; replication is a separate count, not an explanation. Predicate
granularity is checked before declaring deviation. Near misses require a declared representation whose
coordinates are known and equal except for one verified difference; any permitted interpolation, sponsor
lineage, era or cohort difference is shown. Outcome differences are associations to investigate, not causality.

#### 7a. "Notable" now; derivational significance as a planned build

Until derivational significance is built, user-facing "notable" names a computed object for design features:
an observation that is rare within a declared comparison cell (conditional rarity with cell/parent/abstain
standing) and/or a verified unexplained deviation from a declared expectation (`deviation_status`). Both
inputs, the expectation and each observation state, are declared and confirmed before use. Deviation status
is currently a Python building block; exposing it through `reason` (with its qualifier and audit inputs) is
separate work. "Significance" is not used for either quantity.

The planned build brings the founder's SIGNIFICANCE_WEIGHTING method to trial-design derivations. Its
quantity is the improbability, by coincidence, of a coherent derivation chain given the branching the
admissible design space afforded at each step: depth weighted by branching freedom, not depth alone.

- The alternative space is declared, never assumed: each hop's admissible alternatives come from finite
  design domains (the NSCLC coordinate domains are the natural first host, since their causes already record
  which premise or relation removed which values), and a derivation without a declared alternative space
  abstains rather than emitting a number.
- The per-conclusion weight is path-local: the sum of log out-degree over the branching the conclusion's own
  chain navigated, so a globally shallow rule graph does not flatten a real chain through a high-branching
  choice.
- The emitted value is a log-space bracket, not a point: floor from mean branching (b^N), ceiling from maximum
  per-hop branching with free ordering (C^N * N!), both read from the actual rule graph, with an error bar that
  grows with depth N and is reported with the value.
- Marginal coverage (kappa: a node's downstream reach) refines the raw bracket: a chain that resolves a whole
  cluster of downstream choices is significant; a chain of independent hops is not. Kappa re-flows when a rule
  or confirmed choice is added, so significance is recomputed after every user decision.
- Significance remains separate from logical state, frequency, rarity and relevance, and never promotes a
  default or proposal. It ranks and explains within the admissible space; it never changes admissibility.

Open definitions, settled with the founder before implementation: what counts as a hop in a trial-design
derivation (a relation firing, a confirmed choice or a domain narrowing); how b and C are measured over the
design rule graph; the coincidence baseline (the null) against which improbability is scored; and how
corpus-observed alternatives (what comparable trials chose) enter the branching alongside logical
alternatives. Regenesis's `significance.py` is the reference implementation of the per-read method on its own
rule frames; it is not wired to trial data and is not a TrialLedger dependency.

### 8. Gap-directed evidence

An unresolved design fact becomes a typed evidence request before external retrieval. Existing registry
prose is retained; a reader's inability to interpret it is not mislabelled as absent evidence.

The designed adapters are terminology/measurement sources (MeSH, NCI Thesaurus, UCUM and declared specialist
vocabularies), product labels (DailyMed bound to the resolved product/version), and PubMed/PMC publications
where accessible. Other data dictionaries or protocol templates enter with the same source contract. NCI PDQ
or labels can supply dated treatment context, but discussing an option is not being a clinical guideline.
Current care and historical care remain separate, and source availability/permissions are verified when an
adapter is implemented. Optional licensed resources are not silent prerequisites.

The publication pipeline is differential and symbolic: the gap fixes the fact type and study vocabulary;
typed sections/tables select admissible parsers; parsers locate explicit statements; identity resolvers bind
study, cohort, arm, intervention, outcome and time; censors reject wrong-section or unresolved evidence. Each
value retains document/version, section or table cell, exact text, spans, parser and resolver versions. A paper
citing an NCT number is only a candidate until the required bindings hold. Background, result and derived
registry references retain their source-defined roles. Missing, unavailable, ambiguous, not found and found
are distinct outcomes. Publication evidence never overwrites the registry.

### 9. Admissible recommendations

Hard constraints decide membership of the feasible set. A separate recommendation stage orders only what is
admissible; it cannot change truth or admit a forbidden design. The existing design uses hierarchical positions
and direction/depth, scoped spreading activation over trial and shared-anchor links, conditional rarity and
association, graph precedent, attenuated class inheritance and diversity among alternatives. Unknown positions
remain unknown rather than the zero coordinate.

Each suggestion carries the reason it was reached and its source, trials, counts or conditional rule. Corpus
standards are empirical practice, not a proof of clinical necessity. A mechanism-linked exclusion remains a
proposal. Inheritance by class remains interpolated with distance and assumptions. Combining recommendation
supports does not manufacture independent evidence or resolve a source conflict. Tie clusters retain their
discriminating axes and feed the closing step.

### 10. Closing the remainder and writing the protocol

After definitions, constraints, defaults and corpus observations narrow the space, the system chooses the
question whose answer leaves the smallest worst-case admissible remainder, including downstream consequences;
ties follow a declared deterministic order. It suggests the best-supported answer, shows its warrant and what
it would settle, and records the person's acceptance or alternative as their choice. Representation choices
are questions too when a default interpretation is material. One consequential question is presented at a time;
accept-all records every acceptance. Closed templates carry stable ids and amendments to the brief.

The complete outputs are design JSON and a readable design workbook/protocol synopsis: brief, population,
inclusion/exclusion, interventions/comparator, clinical endpoints and time points, biomarkers and assays,
assessment and procedure schedule, efficacy decision criterion and sample-size inputs, safety plan,
exploratory imaging/biopsies, reusable language and open decisions. Each element is deduced, interpolated,
proposed or chosen with its basis. Standard templates and recurring corpus language remain distinguishable.
An unresolved field stays visible or drives an evidence request; the requested output does not authorise a
fabricated answer. Corrections and user annotations remain assertions beside source facts and recompute the
design; automatic workbook-edit import is designed, not claimed available today.

The present partial operations must also be legible conversationally to a nontechnical person. Lead with a
clinical question and its computed answer, deciding evidence/premise, material uncertainty and next choice.
Use compact executed examples as explanatory objects: a missing cross-tabulation bounded by marginals,
positive and negative eligibility witnesses that can coexist, and scheduled versus actual event roles that
distinguish real from apparent contradictions. Keep real retained evidence and invented teaching premises
visibly distinct. `docs/POWERFUL_QUESTIONS.md` and the continuing interpretation session link the runnable
inputs/results; assistant context routes to them without making the person choose internal module names.

## Current component and integration state

The separate public operation is `TrialLedger.layer2.run(request)`, served by `trialledger reason --request
FILE` and MCP `reason`. Requests select `entailment`, `coordinates`, `corpus`, `design_bounds`, `signals` or
`interpretations`; responses distinguish complete
from refused and return results/problems. These operations answer from supplied typed premises; they do not
automatically interpret eligibility or claim a newly written protocol. Exact supported request shapes and
examples live with the public operation.

- Scoped assertion objects and exact finite entailment are implemented logic.
- Literal number/unit/comparator/window parsers, span contracts, versioned concept/predicate registries and
  typed applicability/evaluation utilities are retained under `layer2`; they encode candidates and do not
  constitute an automatic clinical text reader.
- Finite coordinate closure and NSCLC rule/domain machinery are retained for explicitly typed, applicable
  premises; their status is conditional on those inputs.
- Corpus statement rates, silence bounds, proposed association, occupancy and near-miss calculations are
  retained as separate operations over explicitly represented inputs.
- The canonical drug lookup machinery is shared source infrastructure; it is not a clinical reader.
- The bounded retained-source bridge compiles named structured rules and anchors hypothetical readings to
  exact source values/passages. General automatic clinical-prose compilation remains unintegrated. The faulty
  flat word-matching path is removed rather than kept as a fallback.
- General clinical ontology bindings, full default-stratum semantics, gap-directed publication/label
  adapters, derivational-significance integration (section 7a), recommendation/closing orchestration and
  complete brief-to-protocol outputs remain implementation work under this design.
- The `describe` reply carries an answer guide (four categories: settled, something wrong, your call, not
  knowable from this evidence; every entailment decision and blocker; coordinate and corpus states), the
  clinical words each operation answers and a runnable worked session. Tests tie each to the engine.

The earlier NSCLC development work is evidence of component behavior on its declared inputs, not broad
clinical validation. Incomplete integration does not negate correct logic. A component's tests also do not
certify the clinical truth of agent-supplied premises. The task list records verified build status separately
from this completed design.

## Acceptance

Test each claimed layer separately: recognition, complete scoped representation, reasoning and consumer
projection. Keep source-grounded expected claims and omissions; identified, abstained and wrong per class,
including over-narrowing, are distinct. Positive/negative cases cover alternatives, qualified exclusions,
nonparticipant referents, definitions, conditional obligations, event-relative time, cohort scope, explicit
absence, missing units, default conflict, status propagation and bounded-resource refusal. Changing AND to OR,
dropping a qualifier or antecedent, moving a negation, changing an actor/time anchor or promoting interpolation
must change or block the affected conclusion through the actual public operation.

Validation varies the logical/source structure and applicable study domains. Development populations remain
labelled; inspected examples do not confirm a rule written against them. A bounded reviewer may answer a
specific closed question only when explicitly authorised, with complete local context and all candidates plus
unresolved; review provenance remains distinct from facts, and model agreement is not a clinical warrant.
Detective behavior checks and ordinary tests complement these intent checks without substituting for meaning.

## Migration and risks

The reference writer stays independent throughout. Rescue correct components into the layer-two package,
remove unsafe raw readers and their public routes, wire the typed operation and validate its real entry point.
No compatibility adapter may quietly reintroduce flat atoms as clinical conclusions. Old retained outputs
remain reproducible at their writing code version, not relabelled as current truth.

Costly or unsupported reasoning returns a named partial/refused result. Thin evidence yields unresolved
choices rather than defaults hidden as facts. Domain coverage grows by warranted concepts and bindings, not
by fitting phrase lists to a set of trials. Existing designs constrain future implementation; finishing a
missing pipeline component is not permission to redesign the thesis.

## Reporting partial information remains independent

Mechanical reporting decodes source-defined conventions rather than estimating clinical meaning. A date
check retains exact possible/excluded outcomes over valid DateType and PartialDate completions, alongside
its headline and missing source fields. Malformed inputs yield no exclusions. Check aggregation preserves
independent contradictions beside malformed entries. Safety retains warranted group-denominator fallbacks
with visible origin and independent collection availability; flow accounting retains separately computable
not-completed quantities beside unknown reasons. These source-defined computations do not import layer two,
identify missing source values or complete the general clinical compiler. Their reach is bounded by the
published conventions available for the domain, not by calling all ambiguous text mechanical.
