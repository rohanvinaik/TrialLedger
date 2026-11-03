# Design

## Context

See `proposal.md` for the bounded integration objective and `evidence/workflow.md` for the fresh clinical investigation. This refines the consolidated `add-design-synthesis` design; it does not replace its epistemology or finish the automated writer.

Inspected current paths at revision `a3987b0`:

| Existing owner | What was established | Consequence for this pass |
|---|---|---|
| `service.run`, `_design_bounds`, `_bound_observation` | Public operations dispatch separately; a bridge supplies one caller-set maximum exception count | Add composition and evidence-aware preparation, preserving the standalone operation |
| `design_bounds.bound_designs` | Derived count intervals feed witness decisions; only the guaranteed lower count is compared with exceptions | Keep the interval and deciding inequality; do not invent a point estimate |
| `checks._gather_flow_reasons` | Reads flow reason counts and retains independently computed not-completed counts | Accounting consistency does not classify a reason as an eligibility deviation or establish its timing |
| `entail._satisfiable`, `decide` | Exact comparison-cell enumeration; named resource-bound abstention | The representation already has exact threshold cells; first repair the status handoff, not the entire solver |
| `entail._proof` | Returns one deterministically reduced proof set | Not an exhaustive ATMS label; never use it as the complete invalidation dependency set |
| `interpretations.resolve`, `_frame_row`, `_gate_calculation` | Immutable frames, fixed-floor checks, conditional local results and scope-gated binding uses | Reuse isolation and weakest-standing machinery; do not merge rivals into one premise set |
| `service._corpus`, `corpus_admission.prepare` | Caller-declared standing gates all public corpus consumers | Add a premise-backed projection path without pretending source meaning is independently verified |
| `graph_evidence.temporal_closure` | Exact rational difference closure, including strict bounds | Keep nominal targets, allowed windows and actual events distinct; do not discretize dense time silently |

The live run is not a passing implementation test for the proposed session. It establishes current operations and concrete missing handoffs. Twelve request/result pairs and the retained source/workbook are preserved under `evidence/registry-run/`.

## Goals / Non-Goals

**Goals:** make a small, replayable design session consume the reasoning already built; locate uncertainty precisely; make documentary constraints reach bridges and projected features; compute the decision-list state rather than ask an assistant to narrate it.

**Non-goals:** a database, autonomous background state, full ATMS support enumeration, replacement SAT/ILP engine, general cross-module pooling, generated complete protocol space, entropy/significance scoring, automatic arbitrary eligibility parsing, or complete protocol output. These are not smuggled in as prerequisites for this integration.

## Decisions

### 1. Classify results on independent axes

Keep existing operation-specific logical results. Group 1 provides additive version-1 metadata to individual
findings in existing public operations, without requiring a session. Discovery and empty source inspection
have no clinical findings. The implemented finding fields are:

- `path` and `kind`: JSON pointer to the actual finding and its operation-specific role;
- `logical_result`: the effective decision or compatibility state, not a replacement enum;
- `standing`: support strength as retained by that result;
- `completion`: `complete`, `limited`, `unsupported`, `invalid`, or fail-safe `unclassified`;
- `causes`: named codes and kinds, with multiple causes retained;
- `disposition`: `settled`, `conditional`, `conflict`, `open`, `descriptive`, `translation_question`, `not_computed`, `unsupported`, or fail-safe `unclassified`.

Optional `raw_result`, `raw_path` and `support_path` retain ungated calculations and deciding warrants.
Group 1 does not emit normalized `origin`, `coverage` or `uncertainty_causes` fields. Origin and represented
coverage remain in the actual premises and operation payloads until the planned session can expose them
from explicit dependencies and declared questions.

`conditional` must be explained from `standing`, not its disposition alone: interpolated support is an
overridable default or working assumption; proposed support is an unconfirmed reading, refused outside
the supported hypothetical frame. Current `open` is deliberately neutral about the kind of open question.
The session projection in task 5.2 will refine it into `design_choice`, `evidence_question` or
`translation_question` when the declared question, scope, dependencies and actual results warrant that
classification. Existing refusal metadata already uses `translation_question` for request repair.

Request-envelope `code: complete` continues to mean the request was handled. It must not imply the internal solver completed. A result can retain settled independent consequences beside a limited analysis.

`design_choice` is only for a named new-trial variable with both alternatives established feasible under the represented constraints. An absent historical cutoff is not a choice about historical reality. Nor is a question certified free when missing translation or unfinished computation could still constrain it. Inconsistency blocks closure; it is not a fifth way of choosing a protocol clause.

This tightens the review's four-way thesis: the substantive partition is conditional on a satisfiable, adequately represented question and completed computation. Its prerequisites and exceptions are first-class output. A blanket four-label classifier would recreate the very information loss being repaired.

### 2. Keep reported counts, exception meanings and upper-bound assumptions separate

Positive participation and negative failure/rejection observations are independent constraint channels.
The trial-specific application of Negative Specification is retained in `negative-evidence.md`. A failure
must keep its observed category and scope even when its target is unresolved. The planned bridge will
retain possible targets: entry eligibility, treatment adherence, assessment adherence and an explicit
other-protocol-requirement residual. Broader failures are not dead ends or silently narrowed to entry
ineligibility. Each narrowing retains its own warrant, standing and dependencies. Only an applicable,
accepted singleton entry-eligibility attribution supplies an eligibility-exception floor for its bound
count; proposed narrowing remains conditional. Empty accepted intersections are attribution conflicts.
Recording during maintenance alone cannot exclude an entry violation discovered late. This target-set
handoff is not yet integrated; the existing solver already handles both participant witness signs.

For a rejected profile P, the supported constraint is existence of a P participant outside candidate
eligibility E, not universal exclusion of P. Accepted and rejected examples of the same partial profile
can jointly refute an eligibility explanation based on that profile alone. They do not identify the
missing criterion. Unknown attribution retains alternatives and the broader reported failure; it is not
discarded and never becomes a guessed MUST-NOT. The existing rejected-witness solver remains the owner of
the conditional calculation. Source meaning, assessment time and whether a candidate claims complete
eligibility remain explicit premises.

A flow observation retains its complete source category, integer participant count, module-local group, period, study digest and source address. Selecting an arbitrary category by a word match cannot establish an exception predicate.

An `exception_binding` separately relates that observation to a particular eligibility predicate at a named assessment/entry context. Its rule, source evidence, status and resolution remain explicit. Initially the clinical relation is supplied as an accepted premise or explored inside a hypothetical frame. A source-defined rule may discharge it only when that rule warrants the relation; a consistent reason-accounting check does not do so.

The current vendored API schema defines `DropWithdraw.type` as a free string, and its participant-flow
metadata supplies no label-specific entry-eligibility definition. Therefore even IPASS's eligibility-worded
withdrawal label needs a supplied clinical attribution. Its floor-one/zero-cap conflict is conditional on
that reading and application scope, never settled from the registry codebook alone. Before acceptance it
is a hypothetical consequence, not an admitted conflict; acceptance makes it a consequence of the person's
premise, not a new registry fact.

The prepared envelope has a nonnegative lower bound, optional informative upper bound, structural population maximum, scope, support and blockers. `upper: null` means no supported informative ceiling, not zero and not infinity. The structural population maximum stays separately visible. Intersect applicable bounds; report an empty intersection as a bridge conflict. Do not silently clamp or discard the evidence. A declared upper bound below an admitted same-scope floor cannot reach candidate elimination.

Scope determines the valid transfer:

- A global exception upper bound may bound subgroup exceptions only under an explicit subgroup relation.
- A global exception lower bound does not establish an exception in an unspecified subgroup.
- A subgroup exception floor can constrain its declared parent only under the corresponding relation.
- Period/reason observations are not distinct people unless a partition/disjointness warrant establishes that.

Under the common-population reading, IPASS's PS-2/never-smoker lower count is 49. A maximum of 48 exceptions still leaves an eligible witness; 49 does not guarantee one. A reported floor of one supplies neither ceiling. An assumption of zero **global** exceptions conflicts with a warranted floor of one; zero exceptions **in that joint profile** need not, since the reported person's profile is unknown.

The non-light-ex-smoker count of two supplies a second, conditional channel. First bind the category to the source's smoking definition and the relevant time; then retain its possible overlap with the flow category. With no disjointness premise, one plus two is not three distinct exceptions. The current supplemental overlap probe permits intersection 0–1; the system has not identified which participants overlap.

Expose exception preparation before the session: add an optional typed exception-evidence reference on the existing `design_bounds` bridge, resolving only evidence supplied in that request. Public validation intersects applicable admitted evidence before the old witness consumer runs. Missing references, duplicate IDs and unresolved scope retain named outcomes. Legacy bridges retain their explicitly supplied-premise contract; omitted evidence is not claimed checked. CLI/MCP group-2 acceptance must trace the supplied source observation through the bound check to candidate survival.

A historical exception cap is an empirical uncertainty or explicit sensitivity assumption, not a clinical preference. Present the threshold needed for the desired inference rather than require the person to invent one number. No real-record example should silently lead with a zero-exception default.

Negative-sign eliminations must retain their deciding support through candidate state, elimination
standing, common consequence where relevant, classified metadata and the decision/evidence-task handoff.
An empty surviving candidate family is a conflict; a singleton is permitted without certifying the
historical protocol. Corpus silence is not a negative participant witness. Corpus `near_misses` remains
the trial-comparison object; a participant positive/negative comparison is a contrast pair.

### 2a. Produce bounded requests for distinguishing evidence

After exception integration and before session work, compute which hypothetical profiles and witness
signs would distinguish declared surviving candidates. Reuse `eligibility_witness` and exact finite
comparison cells over represented variables, preserving units, thresholds, open boundaries, scope and
explicit domains. Bound aggregate enumeration and solver work. Unsupported domains or incomplete
search retain named blockers; do not claim complete separation from a partial search.

Each request identifies a hypothetical profile/sign, affected candidates, deciding proofs and the
attribution and exception conditions required to make that observation decisive. A partial profile
can still separate candidates: one may forbid the observed sign while another accommodates it through
an unspecified attribute. Evaluate each candidate independently without filling that attribute. Results are investigation
requests, never observed evidence or automatically adopted premises. A candidate family with one
survivor needs no further within-family separation; no survivors instead requires conflict resolution.
This enumerates participant comparison cells for supplied candidates, not the generated protocol space
deferred in section 8. It neither scores clinical utility nor chooses a design for the person.

Return the least-specified separating profiles first within the declared profile representation. Check
whether a profile can be weakened while preserving the candidate separation; order by represented
attributes and deterministic canonical ties. State the searched coverage and do not claim a global
minimum after incomplete search. This is structural ordering, not an availability probability or utility
score. Every request explicitly marks `accepted` or `rejected` and suggests an evidence location without
claiming that evidence exists: eligibility-attributed screening/adjudication records for a negative
witness, or appropriately bound participation records for a positive witness. Registry flow may supply
an attributed rejection, but corpus absence never does.

Bound response size as well as enumeration: validate a maximum requests per survivor pair, an aggregate
request count and an output-byte limit. Retain pair identity, deterministic ordering and named output
truncation separately from unfinished enumeration. A suppressed request does not mean no separator exists;
do not report an exact omitted count unless it was actually computed.

### 3. Test proposed bindings before asking for a judgment

Each population candidate names study, snapshot, modules, population, arm, time and relation. Reuse existing scope/application checks and numeric operations for the declared relation. For example, IPASS's 609-person gefitinib ITT population cannot be a subset of its 590-person EFQ population under the declared same-arm correspondence. The reverse relation is numerically compatible. Counts from the other treatment arm cannot be substituted into that check.

A count conflict refutes the conditional relation under its binding premises. A wrong study/version/application is a translation or binding problem, not a clinical refutation. Passing these tests leaves a candidate compatible; it supplies neither identity nor exhaustive candidate coverage. Explanations identify what source evidence would distinguish the survivors. This moves warranted work before confirmation without replacing clinical judgment with equal-title/equal-count joins.

### 4. One immutable session snapshot, existing solvers underneath

Add `operation: design_session` to the shared reason API and focused discovery. The request contains a closed, versioned `session` object. Its conceptual fields are:

| Field | Contract |
|---|---|
| `schema_version`, `id`, `revision`, `parent_digest` | Immutable snapshot identity; first revision has no parent; supplied predecessor identity is checked |
| `target` | New-trial or historical-study question, study/draft identity and scope; comparator restrictions never become draft restrictions without an adoption premise |
| `sources` | Supplied retained snapshots with expected canonical digests, not arbitrary file paths or live fetching instructions |
| `premises` | Stable IDs, existing typed assertions/signals/bindings, exact origins, supports and acceptance state |
| `analyses` | Named existing reasoning requests plus explicit typed premise uses; no recursive session requests |
| `decisions` | Named clinical question, target, alternatives and referenced analysis/query IDs; narrative supplied by the assistant stays separate from computed state |
| `previous` | Optional prior snapshot/result for revision comparison, never an authority to reuse cached answers |

Freeze exact field schemas in discovery and strict schema tests before implementation; use current assertion/signal/binding types rather than a second clinical logic language. Accept declared narratives only as supplied labels. Unknown fields, duplicate or missing IDs, cycles in derivation dependencies, stale source references and unsupported projection targets have named refusals. Bound total expansion, recursive depth, analysis count and solver work, not only each child call.

Before schema freeze, build a concrete prototype from the retained IPASS/ARCHER child requests and a cap-48 to cap-49 revision. Check expanded child requests for exact equality and execute them. Compare independent semantic declarations, repeated decisions and contradiction opportunities separately from administrative fields or token counts. If the wrapper adds material translation burden, split session orchestration into its own follow-on change while shipping groups 1–2 independently.

The runner prepares validated typed child requests and calls the existing reasoning entry point. It preserves full submitted/prepared requests and returned results. No general string substitution, executable template, arbitrary pointer rewrite or status override is allowed. Projection rules own the allowed premise-to-request slots and their types.

The decision list is then a deterministic projection of those results: source context, deciding premises, conditional consequences for each option, open causes and chosen status. It is a computed view over **declared questions**, not a claim to discover every unstated protocol decision. The assistant remains responsible for identifying missing clinical questions and explaining the result.

### 5. Derive admission from both dependencies and origin

The session's corpus projection accepts premise references rather than an independent `known` override. Each feature projection identifies its rule and documentary basis; the weakest support propagates through the complete dependency path.

Standing alone is insufficient: a directly chosen draft restriction can be known as the person's choice without being a comparator's source statement. A baseline-derived eligibility bound is not a source-stated criterion. A confirmed source interpretation remains attributed to that interpretation and acceptance, not relabelled a literal registry value. Pending source interpretations remain pending; direct structured age may remain usable independently.

Keep reason-derived results as computed information with their full dependency paths. A prior survivor
or inferred interpretation cannot re-enter the managed path as an independent source witness merely
because its supplied standing is known. Test that explicit promotion attempt and dependency cycles.
Valid derived computations remain usable as derived inputs to supported consumers; their use does not
create a second independent observation. This admission guarantee does not authenticate arbitrary
origin claims in legacy manually constructed requests.

Use named projection rules for the represented corpus vocabulary and coordinate evidence. Refuse unsupported mappings instead of adding heuristic predicate matching. Retain current all-trial denominators, pending rows, association/near-miss abstentions and independently known occupancy dimensions. Do not broaden current corpus admission to accept interpolated facts. Existing manually constructed standalone requests retain their stated caller-declaration contract; the new path removes duplicate standing declarations in session-managed work, not all possible caller error.

The random holdout exposed a redundant structural declaration: `typed: false` alongside a directly typed age element is refused before feature admission. With `typed: true` explicitly meaning an eligibility element has been represented, while clinical readings and trial-wide standing remain proposed, the existing corpus path correctly counts only the known ages. Derive that structural flag from the prepared representation in the session adapter; do not treat it as complete source coverage, use it to promote pending facts or remove the standalone guard merely to accept inconsistent input. Retain both the refused and corrected probes as a documentation/input-contract case.

### 6. Replay first; optimize truth maintenance only against replay

For every revision, canonicalize the new snapshot and execute all its requested analyses. Return a comparison with the prior result identifying unchanged, changed, withdrawn and newly computed entries, with named causes. Source/user objects are immutable; prior snapshots and results remain inspectable.

Record full analysis dependencies, including input assertions, signals, bindings, source/rule versions, context, domains and limits. A returned minimal proof is an explanation, not a complete cache key. Adding a new constraint can change a previously open answer; removing one derivation can leave another. A cache indexed only by the old proof misses both cases.

This provides the observable truth-maintenance contract without falsely calling existing frames a complete ATMS. Later incremental execution must match full replay on revision sequences, including alternative support, added constraints, retracted choices, source updates, conflicting assumptions and independent results. Unsupported default cycles retain the existing limitations; this pass does not implement the full default-stratum semantics left in the consolidated design.

### 7. SICP decomposition and actual consumers

| Proposed owner | Coherent responsibility | Consumed by |
|---|---|---|
| `result_semantics.py` | Normalize actual returned states/causes into named clinical dispositions; retain mixed causes and original result | Session projections and operation answer guides |
| `exception_bounds.py` | Scoped bound intersection and witness/cap disposition over already validated primitive inputs | Session bridge preparation, then existing `design_bounds` |
| `session_state.py` | Validate immutable IDs, references, origins, revisions and full dependency structure | Session runner and replay/diff |
| `session_projections.py` | Prepare explicit typed consumer inputs and produce decision entries from real results | Session runner; existing corpus/coordinates consumers |
| `design_session.py` | Compose source admission, bindings, bridge preparation, child analyses, decision projection and revision comparison | `service.run` through CLI/MCP |

Pure primitive decisions use literal types and named codes suitable for direct authored tests, Detective and explicit contracts. Typed-object wrappers own validation; the runner owns composition. Avoid one-line abstraction proliferation or a generic rule framework. No module may be added as completed work without a traced public consumer.

Possible later sub-agent contracts are bounded by these owners: one owns result semantics/exception primitives; one owns state/projections; one owns clinical acceptance inputs and independent counterexamples. The lead owns service/discovery, integration, documentation and the full symbolic trace. Agents receive meaning and intent from the lead and return observed facts; they do not amend clinical premises or theory. No concurrent edits to shared service, guides or specifications.

### 8. Follow-ons follow demonstrated need

These are not implementation tasks of this bounded change:

1. **Joint population feasibility.** Start with an explicitly bound population graph, nonnegative integer atoms, marginal/subset/partition constraints and query expressions. Solve admitted constraints together and project tight min/max counts with witnesses or a named incomplete result. Keep independent scopes separate. The IPASS two-margin bound is already tight: do not claim an improvement there. Earn the extension with three-attribute/pairwise constraints, clipping under arm partitions and population lineage. Rational relaxation is not integer feasibility; an unfinished optimization cannot certify tight endpoints. Solver selection and any dependency change need their own proposal and verification.
2. **Finite generated design space.** Declare a coordinate language and its scope/coverage. Preserve correlations and nonconvex alternatives; products of marginal domains are not joint counts. Most-general/most-specific summaries alone need not describe all holes. Count distinct projected designs, not their proofs, aliases, participant completions or interpretation copies. A generated finite family does not enumerate all clinical protocols.
3. **Information accounting.** Given exact counts in the same declared finite space, report remaining `log2(cardinality)` and sequential reductions, separating source evidence from assumptions and human choices. This is a declared cardinality measure; it is not an empirical probability distribution, clinical utility or the founder's derivational significance. Order-dependent attribution is labelled. Unknown counts, changed coordinate partitions and empty spaces do not receive invented bit values. Preserve inclusive cut points and open cells; comparator landmarks define a representation, not truth outside it. Significance's existing open definitions remain open.
4. **Bounded semantic compilation.** The real ARCHER entry offers a simple ECOG clause alongside compound mutations, an adjuvant-treatment allowance and a broad prior-treatment exclusion. A whole-scope grammar may compile only what its construction, attachment and bindings warrant; recognition of `ECOG 0–1` does not establish arbitrary nearby clinical force. Keep unsupported clauses/attachments Opaque and source text intact. Measure source-unit/span coverage, supported semantic constructions and wrong projections separately. Compiled-to-Opaque ratio alone is not a fraction of all clinical meaning. Hold out fresh trials before writing grammar rules and revisit failures structurally.
5. **Sponsor screening-log input.** A separate change may accept user-supplied rejection reasons and partial participant profiles with explicit source origin, scope, distinct-person accounting and attribution. The current registry bridge does not provide that importer. Such records could supply negative eligibility evidence when the failed target is warranted; no scale or availability claim is assumed here.

The review's claim that two architectural steps would make every current thesis claim fully implemented is not adopted: source compilation, full design-space coverage and protocol closure remain unfinished in the existing authoritative plan.

### 9. Model-operated clinical walkthrough after substantial changes

After each substantial coherent code change or documentation-focused change, the assistant performs the model workflow in DEVELOPING.md (this change retains its planning copy in `workflow-check.md`). Use a different trial category for each substantial increment. Task groups can organize a coherent batch; they cannot suppress the trigger for a substantial change. AGENTS.md retains only a development-specific pointer, not the contributor procedure. This is an LLM action, explicitly outside CI: select a sane clinical query, retrieve a coherent pool, draw and record a fresh sample, read complete clinical units, run supported public reasoning, revise a meaningful premise and inspect the user handoff.

The model checks whether the documentation's promises can actually be carried out, whether uncompiled information is preserved and whether the question still makes clinical sense. Neither green tests nor a function pin replaces this action. Retain failures and unresolved findings; do not swap the sample to get a clean story. Rotate indications/settings, including domains outside NSCLC, without applying NSCLC rules outside scope. Random sampling is an overfitting guard, not a statistical validation claim.

Before task 2.8 and each later acquisition, apply DEVELOPING.md's walkthrough-retention contract: commit
the clinical handoff, complete reasoning inputs/results, query/sample and source/version/hash receipt;
retain bulky raw capture/report packets separately after checksum verification. Keep snapshots required
by reasoning inputs intact. Distinguish layer-two replay from workbook verification requiring the full
packet, and a fresh registry retrieval from exact historical recovery. Authored prototypes stay expanded
and inspectable. Record retained file/byte counts; do not multiply full captures across walkthroughs.

## Risks / Trade-offs

- **Premise acceptance mistaken for clinical truth** → preserve origin, source wording and hypothetical/accepted status separately; record the person/source that supplied it.
- **Flow categories mapped too broadly** → keep source reason counts distinct from the scoped entry-eligibility relation; no word-list classifier.
- **A session wrapper hides discarded information** → retain complete child requests/results and trace every deciding result into the list through CLI and MCP.
- **Full replay costs more than incremental execution** → bound work and report not-computed honestly; measure representative runs before optimizing. No speedup is claimed by this design.
- **A new status breaks clients or weakens established guarantees** → additive metadata and explicit discovery/versioning; keep old logical enums and standalone operations.
- **A broad review triggers a speculative rewrite** → fund only the handoffs demonstrated here; each larger follow-on earns a separate bounded change.

## Migration Plan

Implement and commit one coherent vertical increment at a time on main. Start with result causes, then exception/binding preparation, session replay/projections and the actual decision handoff. Preserve old direct requests. Update documentation only when the new behavior reaches both public entry points. Record ordinary gate, two-sign and contract outcomes separately, including typed tool limitations; do not reopen accepted historical pin limitations as a prerequisite.

Rollback is a normal commit revert. Saved source runs and old request/results retain their writing version and are never relabelled as outputs of the new session. Run the post-change model walkthrough after documentation is reconciled, and return any new failing case to its responsible increment before calling the pass complete.
