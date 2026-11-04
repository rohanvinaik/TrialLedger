# Design

## Context

See proposal.md and the two spec deltas. The frozen audit at b8a635d retained complete source-backed
counterexamples: an RSV one-record local revision crosses a10000JSON-node ceiling; actual MCP schemas omit
two callable operations; a crossover ECOG row loses its local label; an admitted NSCLC setting word has no
consumer; aggregate interpretations omit the contrast between OUT_OF_SCOPE and REFUTED. All normal/live
tests passed, showing why these user-workflow boundaries need their own obligations.

## Goals / Non-Goals

**Goals:** restore useful source-to-decision handoffs; retain exact evidence and true epistemic standing;
make a new model's operating guidance match actual interfaces; distinguish clinical decisions, translation
tasks, evidence gaps and computational work. Verify coherent clinical output after every substantial increment.

**Non-Goals:** implement the entire unfinished protocol writer, invent clinical setting equivalences,
authenticate a human exchange from a caller-editable string, impose clinical standards from corpus counts,
or replace exact representation with clinical phrase matching. A simpler interface still exposes its expanded meaning.

## Decisions

### 1. Put acquisition protection at acquisition

Add one small acquisition-policy owner. Optional request `acquisition` contains positive integer
`max_studies` and `max_registry_requests`; unknown fields, booleans and invalid values refuse. Initial
documented search defaults are1000studies/100registry requests, operational safeguards rather than clinical
thresholds. A deliberate larger request supplies explicit expectations. Identifier-only pulls use their
actual requested scope and page plan. Budget adjustment is an operator task within the person's intended
scope, not permission to silently broaden a clinical question.

The pure decision consumes intended policy, observed total and current/planned registry-request counts;
it returns named within-budget, study-expansion or request-expansion codes. Check the first identifier
count before requesting more IDs/full bodies; preserve that count and saved evidence on stop. Count actual
direct/relay plan work as it becomes known, using existing page sizes and complete plan structure. Resume
must enforce the same recorded budget. Direct library/raw pull paths must use the same owner, accounting
for their JSON/CSV work. Retry/throttle/completeness/snapshot checks remain independent.

Alternatives rejected: merely reject an empty query (misses broad nonempty scopes); raise a local JSON
ceiling (measures retained evidence, not NIH work); forbid all large pulls (contradicts deliberate scope).

### 2. Keep local solver work distinct from copied evidence

`design_session` continues full old/new replay with aggregate solver reservations, analysis limits and
complete output-byte checks. Retain expanded JSON-node counts as diagnostics, but retire their use as an
acquisition refusal. Preserve the legacy version1 limit field for request compatibility, explicitly mark
its former node ceiling nonoperative, and document the remaining operative limits. Do not cache old answers,
strip source bodies, truncate results or weaken dependency/standing propagation to pass the audit inputs.
Unsupported JSON recursion/shape remains a validation problem owned by the existing strict input codecs.

### 3. One public capability inventory, shared bounded record access

An import-light capability inventory supplies public operation/view names to discovery/schema consumers;
dispatch remains explicit and verified for exact coverage. Emitted tool schemas, initialization guidance,
CLI help and docs must agree. Test actual `tools/list` using a standard schema validator as well as calls.

Expose CLI `record` using the existing record-view/access owner and page/text controls. Avoid a second
selector or importing a server process into the CLI; extract/reuse the pure shared access entry where
necessary. Preserve named errors, source addresses and exact continuation. Document `params.query.term`
name lookup with identity checking; the CodeBreaK example already works without a new acronym resolver.

### 4. Copy structural heading context without assigning clinical scope

`criterion_entries` adds optional literal context text, offsets and structural kind to each passage. A
Markdown heading is explicit formatting; an isolated non-bulleted colon label is copied as a preceding
source label, without claiming its clinical force. Ambiguous structure stays unstated. Keep the coarse
inclusion/exclusion band and exact source reconstruction. The row caption says local source heading/context,
not entry population or phase. Continuation carries the same context.

`readout` displays context beside each row, and record/address access exposes the same JSON. Update field
dictionary/type validation and reporting derivation version as needed. Old schema4 records must replay
through an explicit supported compatibility projection for their writing format, never silently compare an
old representation with new fields or certify missing context. Preserve layer-one isolation.

### 5. Attribute actual coordinate use and conditional differences

Coordinate admission remains a statement about standing. A separate per-input effect ledger records direct
consumers, applicable/inactive relations, removals and named no-effect reasons. It must distinguish no
consumer, unsatisfied applicability, redundancy, withheld support and an active negative guard. A guarded
input prevents an otherwise applicable relation by its exact forbids facts; preserving alternatives is a
real effect even without removals. If required facts are absent, report inactivity with the veto context.
Use the actual finite rule/fact
interfaces; do not infer causality from string similarity or fabricate a progression relation. Add a
distinct explicit `setting` coordinate restriction if needed to represent a person's chosen finite setting,
keeping `setting_word` as evidence that activates only warranted relations. Guides must explain the difference.

`interpretations` adds a pure named contrast decision and structured answer links for differing frame
outcomes/scopes and selected out-of-scope answers. Keep the fixed-floor short circuit and original verdicts.
Metadata and managed-session children consume the contrast, with guide wording that explains the material
question. Do not label compatible alternatives INCONSISTENT, make family survival source truth or weaken
known independent fixed answers.

### 6. Strict preparation, descriptive quantities and honest attribution

Provide small typed constructors over the existing assertion objects for quantities/enums and scoped
assertions; expose canonical expanded JSON and runnable use without interpreting prose. Prefer existing
model validation, no parallel ontology/force parser. MCP-only users retain valid explicit request shapes.

Frequency rows keep counts, bounds and numerical threshold behavior, with additive descriptive scope and
threshold meaning sufficient to avoid a bare standard claim. Five-trial/three-sponsor class support is a
separate calculation. Validate deviation status/audit/qualifiers with named invalid outcomes; replace the
wrong generated invalid-code characterization only through its owning Detective workflow. Keep task8b
public exposure unbuilt unless this increment explicitly integrates it (not required here).

Expose a clear caller-declaration attribution boundary in session/answer guidance and output where material.
Preserve origin references and revisions; do not claim user-choice labels independently authenticate consent.
Document a decision entry's literal accepted wording and actual exchange reference when available, without
adding mandatory confirmation for copied source facts or a fictitious authentication subsystem.

### 7. Ownership, sequence and proof

| Increment | Producer / consumers | Protected boundary |
|---|---|---|
| A: acquisition/local replay | acquisition policy -> request/ingest/steps/operate and session budgeting | no bulk accidental expansion; no source-truncation workaround |
| B: public access | capability inventory -> schema/discovery; shared record access -> CLI/MCP | advertised examples executable; exact paging |
| C: heading context | eligibility passages -> JSON/dictionary/workbook/record/replay | literal structure, not clinical interpretation |
| D: effects/contrasts | admission/facts/rules and frames -> metadata/session/guide/decision list | no unused-input success or unnamed material difference |
| E: preparation/attribution | typed model and quantity utilities -> public guidance/requests/answers | no promotion, false standard or invalid verified deviation |

The lead owns cross-cutting interfaces, specs, shared guidance, integration and final choices. Delegated
work has disjoint file contracts; contributors return facts and concrete changes, not interpretations of
the user's intent. The lead runs fresh symbolic references before edits and checks duplicate paths. Pure
decisions get direct positive and MUST-NOT tests and Detective two-sign observations, driven only by its
printed next actions. Preserve exact residuals; existing accepted historical limits do not excuse new gaps.

After each coherent substantial change, run a model-operated fresh clinical question in a different category
from the preceding walkthrough. Record query/seed/pool/sample before reading; retain awkward records, full
meaningful baseline/revision pairs and a clinical decision list. Treat coherence versus noise as an
observed diagnostic: does each statement name the relevant population/clock/premise and useful next action,
does local progress survive an unresolved headline, and does unchanged context avoid repeated questions?
Do not turn that reading into a universal numerical correctness score. Keep bulk captures outside Git.

## Risks / Trade-offs

- Operational defaults can stop an intended large search -> name count/budget and allow explicit scoped budgets.
- New context fields alter old report representation -> explicit replay compatibility and retained-source tests.
- A no-effect diagnostic can imply the input is false -> state admission separately and name missing consumption.
- Explanatory causes can become solver blockers -> preserve existing results and test every downstream consumer.
- Shared inventories can create a report-to-reasoner import -> keep them import-light and test layer isolation.
- Constructors can conceal a bad reading -> expose canonical expansion and refuse implicit scope/unit equivalence.
- Confirmation receipts can be overstated -> describe attribution, never authenticated truth.

## Migration Plan

Persist plan and obligations, implement one coherent increment at a time on main, verify real entry points
and clinical handoff, reconcile docs/specs and commit each verified change without AI attribution. Retain
old audit counterexamples and exact failure/pass receipts. Roll back a faulty increment by its commit.
Run the complete local gate and appropriate current pins before final delivery; do not mark a task complete
from a plan, test count, partial workaround or an unrelated green component.
