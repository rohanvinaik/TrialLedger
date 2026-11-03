# Developing TrialLedger

Read docs/THEORY_OF_THE_CASE.md and openspec/README.md before changing behavior. The founding conversation
remains local in docs/conversations/2026-10-31-the-case.md. The founder's instructions govern the design;
passing tests or an implementation shortcut do not amend it. AGENTS.md and SKILL.md guide the assistant
using the product.

## One project, two isolated operations

Layer one: request -> fixed scope -> retained government source -> direct clinical JSON -> readable
workbook/MCP. The assistant is its chatbot/operator. It does not improvise source facts or run interpretation
while gathering. Layer two: explicit typed premises/evidence -> scoped symbolic reasoning and corpus geometry
-> the separately designed automated trial writer. Correct partial logic is preserved independently of
missing source compilation or final orchestration.

The current public commands are doctor, landscape, pull, verify, mcp and reason. MCP serves doctor, scope,
landscape, save_fetch, record and reason. `reason --request FILE`/`reason(request)` is separate and does not
mutate a report. There is no complete design/edits command or automatic annotation import. Retired raw-reader,
model-audit, sample and pilot routes are not compatibility fallbacks.

## Reporting ownership and invariants

- `request`, `preview`, `steps`, `operate`: resolve/preview scope, retrieve/resume, account for every requested
  identity and release matching record/workbook. Failure cannot appear complete.
- `classes`: shared canonical source lookup infrastructure. Retain exact identities, related ingredients,
  class subjects, releases and conflicts. PIN is precise ingredient, not universally salt. Never widen a
  biosimilar/product from a name prefix or choose a fact by alias order.
- `contract`, `landscape`: declared selected source paths/types, direct assembly, exact eligibility passages,
  collection/results states, links, approved direct checks and supplied results-submission/delay/waiver
  context. Malformed scalar types refuse the typed report at a named location; raw evidence remains retained.
- `readout`: projection of the same record, types/precision/scope, exact-text fallback, continuation, source
  links and row addresses. It does not rank clinical significance.
- `mcp_server`: bounded access to preview, gather, save and read, plus the separate symbolic operation.
- `landscape_verify`, `landscape_warrants`: retained-input replay and actual derivation dependencies.
- `ingest`, `registry`, `ledger`, `checks`, `eligibility`, `links`, `cells`, `warrants`, `record`, `workbook`:
  source preservation, original direct consistency checks and archival certified outputs.

Schema 4 keeps copied fields plain, sources once in the field dictionary and direct transformation inputs
explicit. The clinical record is selected; complete raw responses are retained. Keep population and denominator
nesting, local group identity, units, time, precision, zero/false and source comments. Do not join groups by
similar titles. Missing, empty and malformed differ; an empty event list does not mean zero harms. Structural
eligibility segmentation must reconstruct the exact source and never decide polarity, referent or force.

The report path cannot import or invoke clinical recognizers, the layer-two compiler/solver, defaults,
comparability or synthesis, including shadow output. Bound fingerprints to actual derivation dependencies;
unrelated symbolic changes and help text do not alter a report's derivation identity.

## Layer two ownership and standing

`layer2.design_bounds` owns baseline witness bounds over explicit candidate eligibility designs. Service
validates observations, count/denominator, provenance and bridge contracts; `bounds_guide` exposes their
focused discovery and runnable example. The module reuses scoped entailment for candidate compatibility
and queries across surviving designs. Positive witnesses beyond a declared exception budget eliminate a
candidate; observation populations never sum. Conclusions retain the weakest elimination support. Neither
source text, scale identity, time alignment nor compliance is guessed. Reporting does not import this module.
`tests/test_design_bounds_entrypoints.py` connects retained IPASS source -> report/address -> explicitly bound
test premises -> CLI/MCP -> revised consequences. This is a development example, not independent protocol
confirmation. Discovery and assistant guidance route these results into the continuing session's decision list.

`layer2.signals` owns support standing and structural substitution for explicit mathematical witnesses;
`numeric_evidence`, `graph_evidence` and `dependency_evidence` own finite count equations, graph constraints
and adopted-rule prerequisites respectively. They expose `evaluate`/`check` with fixed result contracts;
`signals_guide` exposes their input shapes and runnable examples. `service` validates the public wrappers;
`design_bounds` consumes grouped candidate claims and derived observations. Dynamic dispatch is a fixed
module map, never caller code. A derived interval keeps its lower/upper bounds and original mathematical
expression; only its lower bound reaches witness support. `entail.eligibility_witness` reuses the existing
formula machinery for both acceptance and rejection, refusing impossible profiles before using a witness.
An accepted source-signal conflict blocks common consequences; an unresolved unattached signal remains
context until explicitly consumed. No automatic cross-signal join is implemented.

The source-to-CLI/MCP IPASS test also binds two retained marginals, verifies [49,126], tests elimination and
common consequences, then revises exceptions/alignment/support. Independent small-world oracles check count
bounds, temporal cycles, membership, subtype closure, rejected completions and prerequisite availability.
See [partial evidence verification](acceptance/partial-evidence-2026-11-03.md) for the scoped receipt.

This is a current nontechnical user workflow as well as a set of components: the clinician chooses a
question for their own work, the assistant elicits/encodes confirmed premises and explains the resulting
proof, default, proposal or unresolved item. The structured analysis is reusable beside the unchanged source
record. Discovery and result descriptions must enable that interaction without source-code access or a
complete future trial-writing pipeline.

`interpretations` owns isolated hypothetical frames over a separately checked fixed floor. It reuses scoped
entailment and signal operators; proposed hypotheses are assumed only in private branch copies and remain
proposed in retained inputs. Compatibility, fixed-floor refutation, internal incoherence, unresolved checking
and floor conflict are separate outcomes with formal warrants. Fixed query answers remain independent;
conditional results survive unresolved admission, and a sole surviving frame never establishes protocol
identity. Selection remains a user's choice and recomputes the whole snapshot.

`interpretation_bindings` owns source-bound population/definition objects and effective use checks. Study,
population, arm, time and edition scope and source addresses remain explicit; mismatched applications are
unresolved rather than clinical refutations. `interpretations_guide` owns focused discovery. The public path
is CLI/MCP reason -> service -> binding checks and isolated frames -> existing exact operators -> per-frame
warrants and declared-family consequences -> assistant decision list. See
`docs/INTERPRETATION_IMPLEMENTATION_PLAN.md` for ownership and negative obligations. Reporting never imports
these components. No text compiler, source repair engine or external adapter is implied by this operation.

`TrialLedger.layer2.run(request)` owns the public typed operation.

`source_evidence` owns finite strict-JSON snapshots, exact pointer/value/span anchors and explicit value
hydration. `source_assertions` owns named structured-field rules and source-anchored proposed frames, with
submitted inputs and uncompiled coverage retained. The service validates and runs generated ordinary requests;
the compiler never calls the service. Exact source location cannot certify meaning. Content version and
clinical definition/protocol edition stay separate. See `docs/SOURCE_ASSERTION_BRIDGE_PLAN.md` for ownership
and admission obligations. General clinical text compilation remains unfinished.

Scoped assertion objects/finite entailment, explicit NSCLC coordinate closure and corpus calculations are
reusable components. Full design, source binding,
default semantics, information geometry/significance, differential evidence parsing, recommendation, user
closure and protocol output are specified in openspec/changes/add-design-synthesis/design.md. Its task file
separates current implemented components from missing integration; do not infer missing logic from missing
pipeline wiring or claim an integrated writer from unit tests.

The public discovery request is `{"operation":"describe"}` through reason; it returns an overview. Add
`"view":"entailment"`, `coordinates`, `corpus`, `design_bounds`, `signals`, `interpretations` or
`source_assertions` for focused formats, vocabulary,
result meanings and an example; `worked_session` and `full` retain the complete demonstration and manual. Its input descriptions and
examples must stay tied to actual validators, and its capability/result descriptions must reflect what an
agent can invoke. User-facing surfaces should explain clinical explorations as well as operation names:
population/temporal consequences, possible NSCLC settings, documented patterns and uncertainty, gaps and
one-feature comparisons. Do not expose only a research-pipeline status summary when useful logic is callable.

The value proposition is that TrialLedger does not make the person's clinical decisions; it finds them,
each with its evidence and computed consequences, in a decision list the assistant keeps and hands over. The
assistant translates and the operations reason. The result guide maps outcomes to four categories (settled,
something wrong, your call, not knowable from this evidence), which route into that list. User-facing wording answers the
clinical question naturally with the deciding basis and material open items; it does not require repeated
category labels or qualifications. Keep record facts, computed results and the assistant's reading
distinguishable. Confirmation accepts a person's premise without certifying source truth; entailment's
proposed-premise guard consumes caller-supplied status, not independently verified consent. The describe
`answer_guide`, `question_vocabulary` and `worked_session` live in `layer2/guide.py`; tests/test_layer2_guide.py
ties them to the engine's decisions, blockers and states, so a new outcome needs a guide entry. "Notable" means
corpus rarity and/or a verified unexplained deviation from a declared expectation; "significance" is reserved
for the founder's derivational significance (design.md section 7, task 8).

`record_access` owns response-size controls, consumed by MCP `record_view`: entry paging plus a conservative
serialized-JSON budget, address directories for oversized containers and exact character continuation for
long strings. Navigation/chunks are explicitly different from complete source values. Response limits never
alter saved evidence, requested scope, retrieval completion or solver outcomes. They bound conversation
output, not whole-process memory: record loading and some corpus calculations still materialize their
inputs. Reuse retained files and retrieval checkpoints; do not add a resource scheduler to solve a display
budget. Reasoning replies remain complete; large analyses are best run through the file-based CLI and saved
separately rather than repeatedly echoed into a conversation.

| Existing component | Current access and boundary |
|---|---|
| `service.run`, scoped `assertions` and `entail.decide` | CLI/MCP entailment over supplied, validated assertions with proof/status/blockers; no automatic source interpretation. |
| `coherence.resolve` and its finite NSCLC domains/relations | CLI/MCP coordinates with explicit applicable typed premises; direct narrowing, defaults and proposals remain separate. |
| `profile.frequency_rows`, `mechanism_rows`, `occupancy_rows`, `nearmiss.near_misses`, `expectations.conditional_rarity` | CLI/MCP corpus over a declared typed set; statement/silence bounds, proposed associations, occupancy, pairs and observation rarity. |
| `expectations.deviation_status`, `review.flags_for` | Python utilities over supplied observations/review states, not automatic clinical extraction or explanation. |
| `indications.MeshLookup.lookup`, `resolve_indication`, `universes.assign`, `pack_scope` | Python source/indication/applicability components; not an ordinary-report interpretation stage or a complete automatic assertion compiler. |
| `predicates.predicate_registry`, `atom_literal` and semantic contracts/loader | Python typed vocabulary, mapping and validation components; a candidate literal does not settle clinical force, referent or scope. |
| `semantics.parsers.read_number`, `read_comparator`, `read_unit`, `read_reference`, `read_duration`, `read_window`, `read_interval` | Python literal-expression readers with spans and parsed/ambiguous/abstained outcomes; they do not decide what a number measures. |
| `evaluation` and `typematrix` | Python claim/evaluation and declared-domain coverage utilities; no automatic adjudication of clinical truth. |

Keep these building blocks available even when a composed path is unfinished. Their library entry points
and preconditions can be discovered/described without pretending each is a public clinical operation.
Corpus observation rarity is not derivational significance or clinical absence frequency. A near miss is
one known difference under its declared representation, not proof that complete trials match in every other
respect. The full source compiler, general clinical bindings, significance/recommendation integration and
protocol orchestration remain distinct implementation work under the existing design.

A recognised word is a candidate, not meaning. No flat token/pattern path may establish clinical requirements.
Preserve scope, alternatives, qualifiers, actors, local force, conditionality, definitions and time. Ontology
relations need sources; grammar needs resolved bindings. Unknown is not false or orthogonal. Proposed
material is not a premise; defaults remain interpolated through strict consequences. Sources constrain
alternatives, not a vote; duplicate encodings are not independent evidence. Every result remains conditional
on its supplied premises and retains their source/user/agent origin.

## Admission and information handoffs

`layer2.admission` validates explicit standing; `coordinate_admission` keeps known/interpolated evidence
separate; `corpus_admission` projects per-feature support for every public corpus consumer. Missing support
is pending. Original values, provenance and reasons remain alongside accepted computations. Unknown class
membership and pending readings can withhold associations; independent known dimensions still constrain
occupancy. Translation diagnostics describe exact typed-identity differences, never clinical aliases.
See `docs/REASONING_CONSUMERS.md` and the executable `examples/reasoning-admission/` session.

`scripts/trace_reasoning_consumers.py` runs actual CLI/MCP dispatch for all discovery examples and retained
source/admission sessions, comparing complete JSON and recording call edges plus source hashes. It is a
reachability receipt, not semantic proof. Adversarial tests provide separate behavior evidence. Reporting
partial outcomes use only source-defined conventions and never import the clinical reasoning layer.

## Model-operated clinical workflow check

After each substantial implementation change or documentation-focused semantic change, the assistant works
through a sensible clinical question on a fresh registry sample. Coherent edits can be checked as one change;
an arbitrary task-group boundary does not replace this trigger. This is a model-operated development action
outside CI, not a new software gate or an automatic clinical encoder. Use a different trial category from
the preceding walkthrough, such as another indication or study type, and record the category. Rotate beyond
NSCLC without applying its coordinate rules outside their declared domain.

The purpose is to test the available path from the person's question to evidence, typed reasoning, a
meaningful revision and a usable decision handoff. Look for a documented promise the person cannot carry out,
a missing consumer, a silently narrowed interpretation or information lost between stages. Fixed teaching
examples and green tests do not perform this check.

1. **Choose the question before inspecting favorable records.** State an ordinary clinical-development task:
   population selection, treatment setting, comparator eligibility, assessment plan, analysis coverage or
   endpoint prerequisites. State what a useful answer would look like.
2. **Retrieve through TrialLedger.** Check capabilities when the environment changed, preview a coherent
   registry search and gather its complete declared scope or a separately declared ID sample. Preserve exact
   requests, scope, raw bodies and source identities. A partial page is not a complete search. If retrieval is
   unavailable, retain the specific gap and identify any retained-evidence fallback as such, not a fresh pull.
3. **Draw and record a fresh sample.** Write a random seed before reading the selected studies and sample from
   the retrieved identifier pool. Retain the pool and selection rule. Two or three trials usually suffice for
   the walkthrough. Keep clinically heterogeneous or awkward selections; if a clinical filter changes the
   sample, retain the exclusions and reasons. Randomness guards against fitting to familiar examples; it does
   not establish representative clinical validation.
4. **Read complete clinical units.** Read the selected studies' eligibility and relevant population/group
   definitions, measures, denominators, time and flow context. Work out what a trial designer would ask next.
   Matching names or totals do not establish population, scale, event or endpoint identity. Preserve material
   alternatives and unexplained conflicts.
5. **Use the relevant available system.** Compile named direct source rules, inspect source checks and anchor
   passages/readings. Run the applicable assertion, signal, interpretation, coordinate and corpus operations;
   unrelated calls do not improve the check. Read the actual prepared premises and complete deciding result
   units, and retain full request/result files. Record unavailable integrations as findings rather than supply
   their missing conclusions yourself.
6. **Revise one consequential premise.** Change a design choice, retract a binding, move a boundary or leave a
   disputed reading proposed, then rerun the actual operations. Check that dependent answers change or reopen
   while independent information remains. Never rewrite the source to fit the revision.
7. **Hand off the decision.** Present the clinical question, source evidence, exact conditional consequences,
   remaining choices and evidence/translation/computation tasks. Check that the person can tell which next
   action helps. One restriction is not whole-patient eligibility; compatibility is not protocol identity;
   historical frequency is not a design obligation.
8. **Retain findings and their remedies.** Save the question, scope, category, seed, pool, sample, source
   identities, operations, changed premise, observed consequence and open issues. Distinguish a wiring defect,
   unsupported capability, unresolved interpretation, evidence gap and unfinished computation. Link each
   actionable finding to its counterexample and owner. Do not replace a failed sample or silently amend its
   evidence. Resolve in-scope findings or retain them for the next bounded change.

Report one short clinical walkthrough and the concrete findings. Keep formal test and mutation receipts
separate from the model's reading. A walkthrough tests the thesis at the user-facing boundaries exercised;
it does not certify the whole system or automatic encoding accuracy. `verify` checks reproduction of an
existing saved record and workbook; missing artifacts require a separately established regeneration path.

### Walkthrough retention

Decide retention before acquisition. Capture complete raw responses locally, but commit the reviewable
clinical README/decision list, query and sampling record, complete reasoning request/result pairs (including
the consequential revision), and a receipt. The receipt records source IDs, retrieval time and locators,
raw-body and snapshot fingerprints, writing code/rule versions, commands, parity/verification outcomes,
file hashes and retained byte counts. A needed source snapshot embedded in a request remains part of that
complete input; do not remove it to reduce size. Do not truncate results or silently shorten source text.

Keep one canonical returned result where CLI/MCP results were compared for equality, recording both
entry-point checks and their identities in the receipt. Duplicate wire captures, intermediate exports,
full workbook/report copies and unrelated raw search bodies stay in the local retained packet, with a
checksum and retrieval location. Preserve that packet and verify its bytes before removing redundant
repository copies. Use expanded files for authored prototypes and other artifacts reviewers must inspect;
do not hide implementation or schema choices in an archive.

State the distinction in each README: the committed complete inputs support layer-two replay under the
writing version; layer-one workbook verification additionally needs the retained full report and source
packet. A registry re-fetch by NCT ID and time is a new observation, not guaranteed recovery of historical
bytes. If exact evidence is unavailable, report that limitation rather than relabel the new pull as replay.
Record actual file/byte counts and avoid committing the same raw capture beside every derived artifact.

## Verification

Trace production consumers and duplicate paths before behavior edits. Use symbolic/AST inspection, read
whole units and keep decisions pure with named outcomes. Write positive and negative intent tests, exercise
null/empty/malformed/boundary inputs through the actual entry point and trace signals to consumers. Converge
changed pure decisions with Detective by its current SquishOS protocol, one target at a time. A generated
characterization is not a clinical warrant. Never turn an incomplete/ungateable result or stale measurement
into a pass.

Run scripts/ci_local.sh, read its full output and keep relevant local/type/lint checks current. Detective and
Wesker use the founder's local checkouts. Run the final deep gate only after code and proof inputs are stable.
Follow current machine instructions for temporary processes, Git and verification tools; do not restate or
weaken them in this repository.

The dated [rescue verification record](acceptance/rescue-2026-11-02.md) retains the completed checks,
individual mutation-check limitation and founder-approved boundary for the extended deep audit. Read the
actual receipts before reusing a validation claim; a skipped or incomplete check is not a pass.

The subsequent [clinical usability follow-up](acceptance/ux-followup-2026-11-02.md) records class-search
recovery, named safety-group rows and presentation checks, including the explicit waiver of remaining pins.

Reporting acceptance independently checks source -> record -> workbook -> MCP/address across interventional,
observational and expanded-access structures and metadata branches, atypical supplied values, exact prose and
empty/missing/malformed states. Perturb identities, ordering, cardinality and valid optional fields; plant
paired defects. Review actual sparse/long/mixed workbooks visually. A fixed trial list is not generality.

Layer-two recognition, scoped representation, entailment and consumer conclusions are evaluated separately,
with logical and source perturbations and explicit applicability. Preserve identified/abstained/wrong counts
and source-grounded counterexamples. A broad clinical campaign is not a prerequisite for the generic record
writer. No semantic inventory, conformance bureaucracy or new framework is a substitute for implementing the
stated contracts simply and correctly.
