# Design

## Context

Baseline is main at 913af9a. The HFrEF packet in
`~/trialledger-runs/hfref-persona-20261103` reproduced 19 identical CLI results and six equivalent MCP
clinical envelopes. Two of seven answers changed under the NYHA revision; all seven audit objects
changed. Default baseline reserved 9,437,184 assignments; revision stopped at 10,616,832 against
10,000,000. The successful declared-bound revision's 129 solver calls had domain spaces at most 140.
The engine already proves 900 pg/mL implies absence of AF under the draft. Reporting preserves nine NYHA
measurements but presents them as nine long rows; 2,428 optional Safety Notes cells repeat Not stated.

## Goals / Non-Goals

The integrated path is retained evidence and explicit premises -> existing computations and warrants ->
one clinical projection -> conversation, revision changes, readable list and a separate review workbook.
The canonical record and full reasoning results remain the audit sources. No renderer interprets prose,
chooses a cohort, authenticates a caller's origin or completes a protocol. Unknown remains available.

## Decisions

### 1. Separate owners and frozen builder contracts

The lead owns public service/CLI/MCP integration, artifact storage, export, discovery and documentation.
Builders work on main with disjoint source ownership; no branches, worktrees, commits or shared certificate
edits. The lead supplies intent and current reference traces; builders return checked facts and patches.
All code uses whole-unit reads, atomic functions, named decision codes and direct two-sign intent tests.

Reporting owner: eligibility, landscape/report version compatibility, readout optional notes, identity
index contract, and new `TrialLedger/baseline_view.py`. Export `baseline_tables(record) -> list[dict]`,
each with `id`, `trial`, `title`, `source`, `population`, `groups` and `rows`. Groups retain local IDs,
titles and denominator/source objects; rows retain class/category and an individually addressed value
object per source measurement, including parameter/unit/spread/comment. Never aggregate groups or infer
a shared denominator. Existing long-format evidence remains available.

Explanation owner: new `layer2/entail_explanations.py` and `layer2/clinical_answers.py`, plus interpretation
and design-bounds adapters. Export `explain(assertions, query, context, decision, bound) -> dict` with
`permissions`, `conditions`, `blockers`, and `checks`; and `project(operation, result) -> dict` returning
`version`, `operation`, `findings`. Each finding has `path`, `outcome`, `standing`, `scope`, `values`,
`support`, `origins`, `conditions`, `blockers`, and `canonical_ref`; add fields only with documented
consumers. Export `change_projection(operation, result) -> dict` with independent `answer`, `support`
and `origin` axes. These projections use existing result semantics and actual effective answers rather
than inventing a second admission policy. Unknown results retain their exact code and canonical path.

Session owner: design_session, session_state and a solver-work owner as needed. Return additive
`result_digest = state.digest(response['result'])`, retaining its exact scope. Add `answer_diff` beside
the unchanged audit `diff`, using the explanation owner's change projection. Export public pure
`prepare_revision(previous_request, previous_response, next_session) -> dict`, returning the canonical
design_session request; validate identity and integrity, fill mechanical parent/result fingerprints,
refuse contradictory supplied parents and preserve every declared clinical field and origin.

### 2. Explain without changing the eligibility floor

Permissions impose no requirement. Their explanation must independently check acceptance and applicable
scope; a proposed or unrelated permission cannot be described as accepted. An exclusion still rules out
the profile. Conditions are drawn from represented typed antecedents, not clinical names or token lists.
For an otherwise feasible query, prove query -> condition through the existing solver and retain that
decision's proof/standing. Do not report consequences of impossible queries or global inconsistency as
useful conditions. Bound additional checks explicitly; preserve unsupported and exhausted cases.
The lead wires the common owner into standalone entailment; the builder wires interpretation queries
and design-bounds consequences. Internal witness decisions need not expand all clinical explanations.

Count eliminations retain the deciding witness count/lower bound, denominator, exception cap, direction,
scope and weakest source/bridge standing even when the bridge has a directly supplied cap.

### 3. Charge represented work conservatively

Use the solver's finite partition construction, or a shared exact domain upper bound, to cap reservation
by represented work. Include all query/frame/candidate/proof-minimization uses and fresh old/current
replay. Any unsupported estimate falls back to the existing conservative ceiling. Never lower a semantic
bound silently or reuse stale results to pass a budget. Structured refusal diagnostics report the actual
reservation and limit; the named refusal remains. This is distinct from NIH acquisition policy.

### 4. Preserve canonical artifacts outside conversational output

The pure reasoning interface continues to accept/return JSON without source mutation. CLI/MCP delivery
shells may retain a request and full canonical response in a separate content-addressed reasoning store.
Artifact identity hashes the complete stored payload; supplied IDs never select arbitrary paths. Atomic
writes, size limits, collision verification and named missing/changed/malformed refusals are required.

Expose bounded artifact retrieval, revision preparation and export through public CLI/MCP. A compact
reply carries its clinical projection, scoped result digest and canonical artifact reference. A revision
uses the retained prior request/result and explicit next session or bounded explicit edits; mechanical
integrity filling is not a new clinical premise. Edits preserve origin unless explicitly changed and are
shown in the handoff. Store/export never alters a source report. CLI and MCP use the same owners.

### 5. One clinical projection, several views

Full replies add a clinical projection and concise summary while retaining original fields. Compact views
omit repeated carrier payload only when the full artifact remains accessible. Declared question intent
(compatibility, necessity, consistency or description) controls presentation, never the logical verdict.
If intent is unspecified, give the unambiguous logical outcome and relevant proved conditions.

An answer change compares effective result, scope and numeric content. Support and origin changes are
separate axes, so an unchanged verdict with weaker support is visible. Input-only changes do not become
clinical changes. Preserve audit hashes and unknown projection cases; never compare by fuzzy text.

The design-review workbook and Markdown list are deterministic projections of the same findings and
decisions. They include decision/options, evidence links, consequences, status, origin, open items and
before/after changes, plus reference-study context and compact baseline tables when a source record is
supplied. Export manifests bind exact session/source inputs; independent read-back checks cells and
links. Formula-like source text remains literal. The workbook does not certify the caller's premises.

### 6. Task-sized discovery and operator context

Add minimal focused discovery without automatically echoing revision results, every signal example or
unrelated model definitions. Preserve full guides and machine-readable payload schemas on demand.
Advertise new delivery operations in clinical terms and verify actual emitted schemas. Shorten the
project-owned operator guidance into a checklist and linked operation cards; preserve global generated
instructions at their source and leave theory intact. Export Always/AllOf/AnyOf/Not as direct canonical
construction aliases, without wrapper semantics. Count-only preview is optional metadata work, bounded
and explicit; it must not claim comparability or fetch full studies merely to display a count.

## Risks / Trade-offs

- Projection loss -> operation-aware conservation tests and links to complete canonical artifacts.
- Misleading conditions -> feasibility check first, exact scoped implication warrants, bounded checks.
- Budget under-reservation -> shared finite domains, conservative fallback and adversarial accounting.
- Legacy source replay -> explicit supported writing-version behavior or named incompatibility.
- Attractive but unauthenticated origins -> visible attribution, never a new consent guarantee.
- New artifact IO -> separate bounded store, strict identifiers and atomic immutable writes.
- Walkthrough overfitting -> HFrEF regression plus a fresh different phase/disease after each substantial
  increment, with full source snapshots, actual CLI/MCP and a readable decision handoff.

## Migration Plan

Keep legacy requests and full results accepted. New fields are additive. Reconcile active saved examples
only for declared additive fields and preserve protected clinical answers. Sync specs and operator cards
after real interface verification. Preserve exact proof packets and accepted historical limits. Commit
coherent verified changes on main and push through existing gates without attribution or bypasses.
