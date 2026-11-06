# Design

## Context

Planning baseline: main `c958063ffe5622c2b50e978232b6c74f9c27214b`, inspected 2026-11-05. This is a future capability, not a completion claim for the existing protocol-design build. See [proposal](proposal.md) for motivation and the [roadmap](../../../docs/M11_USDM_ROADMAP.md) for scope and effort.

The existing `protocol_objects.validate_protocol` admits closed scoped/versioned objects and is consumed by `session_state.prepare`. Existing schedule, policy, estimand, definition and statistical projections feed a common protocol view and review export. Session sources currently require `{id,study,expected_digest}` and compile through `source_assertions`; this NIH-specific shape is not a general protocol-source contract. Public `describe` view `protocol` confirms that writing, general statistics and optimisation are not built.

ICH M11 specifies content, hierarchy, cardinality, terminology and conformance. USDM 4.0.0 supplies study/document versions, populations, arms/epochs, objectives/endpoints, estimands, activities/timings and extension attributes. Eligibility and some conditions still contain text. The June 2025 USDM release and November 2025 final M11 artifacts must be mapped as separately versioned inputs; alignment is not assumed complete.

## Goals / Non-Goals

**Goals:** faithful interchange; mechanically warranted projections where definitions suffice; explicit interpretation where they do not; coherent clinical revision and handoff. Declare independently deliverable compatibility profiles rather than one blanket compatible flag.

**Non-Goals:** automatic clinical prose compilation, inventing missing protocol content, regulatory approval, electronic-signature authentication, new statistical solvers, FHIR/SDTM/CTIS implementation, or deploying an entire Study Definitions Repository. Such systems can later consume exported artifacts through separate adapters.

## Decisions

### 1. Pin a compatibility profile before coding

M1 starts with USDM 4.0.0 and the final M11 template/technical specification adopted 19 November 2025 as reference inputs. Retain artifact URLs, release/commit identities, hashes, terminology editions, applicable conformance-rule versions, licences and the actual validator/tool versions. Catalogue mapping differences rather than claiming all USDM 4 content matches final M11. Unknown codes stay preserved but unclassified; no fallback by matching display labels.

Published CDISC M11 and ClinicalTrials.gov crosswalks are reusable starting evidence. Direction matters: a USDM-to-registry crosswalk is not an invertible registry-to-protocol reconstruction. Verify each adopted relationship against its enclosing definitions. Existing NIH-only derivation identities must not acquire adapter dependencies.

Alternative rejected: generating a model from whichever current schema is online. It makes reuse and warrants depend on an unrecorded external change.

### 2. Retain a generic protocol source beside the NIH path

Use a discriminated source envelope with immutable payload identity, declared media/model version, origin, study/document/edition identity and exact object pointers. Reuse finite-JSON/anchor/digest, root isolation and bounded reads from the existing source infrastructure. Preserve original bytes independently from any normalized JSON representation. The implementation must add an explicit versioned contract; old sessions and historical artifacts must keep their current readers and digests.

Dependency trace to verify before editing:

`source retention → source admission/origin validation → session projections → protocol check → per-claim admission → protocol/decision view → compact reply/revision → Markdown/workbook/exchange package`.

Each edge owes an actual consumer and a test. Raw preserved content never enters a solver implicitly.

### 3. Separate import, interpretation and reasoning

The importer produces a retained source, a stable identity/reference index, validation results and a mapping ledger. Each source object records preservation state, mapping state, target IDs, rule/version, support and actual consumers. Suggested mapping states are `mapped_direct`, `interpretation_required`, `preserved_only` and `invalid`; these are adapter dispositions, not replacements for existing standing or solver outcomes.

Named pure projections translate only supported explicit relations. Admission remains with existing symbolic operations. A source fact is known as reported; an adopted restriction for a new trial is a separate choice. An ambiguous criterion remains proposed in isolated frames. An approved-document code cannot authenticate a clinical interpretation. Shared names, equal totals and matching labels do not establish identity.

Alternative rejected: replacing TrialLedger's reasoning representation with the entire USDM graph. The exchange model carries content beyond available operators and does not encode every warrant; wholesale replacement would couple preservation to solver support.

### 4. Preserve timing channels and graph boundaries

Map a nominal offset and permitted bounds using the definitions of their actual timing codes and source references, not their labels. Preserve original values, anchor direction, inclusive/exclusive boundaries, population/epoch and condition. Keep planned collection distinct from the permitted window and actual observations. A treatment-policy strategy name alone supplies no collection requirement.

M1 supports an explicitly enumerated fixed-visit profile. Repeated, nested and branching timelines remain intact as source objects; project them only after an explicit supported mapping exists. Calendar months are not fixed day counts. No infinite or event-ended repetition is silently unrolled to a finite count. M3 extends representational mappings where needed; it does not promise new statistical or unrestricted temporal reasoning.

### 5. Export from a preserved native graph, with explicit edit ownership

Keep the complete native source graph beside mapped reasoning objects. Use an identity map and explicit edit set to update supported fields and dependent references. Test semantic value/reference conservation; keep original bytes for exact recovery rather than claiming reformatted JSON is byte-identical. An unchanged export preserves unknown extensions/narrative content. An unsafe or ambiguous write-back is refused, not guessed.

Bundle ordinary USDM with a companion manifest of mappings, source/object pointers, rule versions, interpretations, adoption, standing, checks and coverage. Use native extension attributes only where their contract permits it; document which consumers support them. The companion is the full warrant carrier. Reimport without it is a fresh source observation, not restoration of prior human acceptance or proof. Export references cannot claim the eventual exported file's digest until that file is written; use a detached manifest to avoid a circular digest.

### 6. M11 adds a separate coverage and rendering layer

Map the imported or authored content to final M11 elements, required/conditional/optional rules, terminology and reuse requirements. Produce independently inspectable schema/reference, terminology, business-rule and content-coverage results. Missing data, unknown applicability, deliberate not-applicable declarations and contradictions need different remedies. Required placeholders do not pass coverage.

Assemble supplied content with source links into a reviewable M11-structured document and update its synopsis/schedule views. This is document assembly, not autonomous clinical authorship. Preserve source wording; a renamed heading or section number does not change an assertion. A complete-looking document cannot erase unchecked content or demonstrate clinical adequacy.

### 7. One public lifecycle, explicit compatibility claims

Expose the adapter through shared CLI/MCP discovery and bounded retention, then reuse preparation, reasoning, revision and export. Concrete command/operation names are frozen in IO-01 before implementation; no unimplemented command is advertised now. Do not require an operator to paste whole protocol JSON or write a Python builder.

A release reports its versioned profile and independent dimensions: preserved content, mapped content, conformance results, admitted analysis and open items. Counts describe coverage of that declared profile, never clinical correctness. Original registry workbooks remain untouched. Unsupported method/graph, translation question, missing evidence and computation limit remain separate in every consumer.

## Verification and delivery contracts

Each implementation slice requires small atomic functions with named decisions, a symbolic producer-to-consumer trace, authored positive and MUST-NOT cases, independent fixtures/oracles, property tests for reference/round-trip laws, and scoped Detective two-sign plus applicable CrossHair contracts. Never infer pin completion from ordinary tests or a mutation aggregate. Record survivors, equivalence warrants, fences and incomplete targets under the actual tool protocol; only the user can accept a pin limitation. Freeze the final proof basis and serialize final audits.

Mandatory negative cases include null/empty/malformed values; missing manifests; duplicate/dangling IDs; wrong editions; unknown codes/extensions; condition scope mismatch; proposed support; a stale adoption; a refusal hidden in a compact reply; a dropped unsupported narrative; recurrence truncation; an unrelated source update misreported as an answer change. Independent external examples must differ from fixtures constructed from the importer itself.

After each substantial implementation or documentation semantic change, perform the model-operated check in DEVELOPING.md. Rotate disease, phase and structure: Phase 1 vaccine dose cohorts; Phase 2 neurology discontinuation/estimand; Phase 3 cardiology event-relative assessments; oncology crossover; event-ended recurrence and observational preservation. Choose the question before sampling sources. Retain exact source evidence, explicit simulated choices, public CLI/MCP results, a consequential revision and the exported handoff. NIH records alone cannot prove USDM compatibility: an externally authored USDM file and its provenance are required for that claim.

## Risks / Trade-offs

- Structured appearance may overstate understanding → retain preservation/mapping/check coverage separately through all outputs.
- Exchange may strip epistemic extensions → detached warrant manifest; missing evidence never restores admission.
- Final M11 and the chosen USDM release differ → pinned field-level crosswalk and explicit gaps.
- Native graphs exceed solver expressiveness → preserve the graph and bound analysis; do not flatten it.
- Synthetic tests overfit the adapter → official/partner examples, independent oracle authors and cold operators.
- Source-contract changes disturb old artifacts → explicit versioning and replay compatibility; no automatic migration.

## Migration Plan

Three releases: M1 import/check; M2 bidirectional interchange; M3 broad USDM/M11 content support. Each declares and passes its own profile; no calendar due dates are promised. All eight implementation packages start uncompleted. Evolve sources/APIs additively with existing regression fixtures. Rollback disables the new adapter/profile and retains original source bytes and prior artifacts; it never rewrites historical evidence. Revalidate estimates after IO-01 using actual external examples and gap inventory.

GitHub holds the parent/child dependency graph and release milestones. Versioned specs hold behavioral authority; issue text links to them rather than redefining theory. Work on main in scoped commits under the project's current policy. A Project card or closed issue is not verification evidence, and final closure requires the release packet.
