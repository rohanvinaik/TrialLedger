# Design

## Context

See proposal.md. The retained UC audit at ~/trialledger-runs/uc-phase2-cold-20261104 supplies exact public requests and failed exports. Existing consumers are CLI/MCP -> reasoning_delivery/clinical_delivery -> immutable artifacts -> clinical_view -> clinical_export. The detailed Findings path already preserves permissions; the primary decision renderer omits them. source_assertions and design_session both contain analyses but with different row schemas.

## Goals / Non-Goals

**Goals:** compose valid related results, preserve permission channels in primary review, retain query identity in open items, and make revised adoption references consistent with the new choice. Keep source reports and prior artifacts unchanged.

**Non-Goals:** infer new clinical meaning, change satisfiability/feasibility outcomes, authenticate human confirmation, reinterpret a copied citation, or integrate retained-source-reference acquisition or complete protocol writing.

## Decisions

1. Classify an analysis path by owning operation before reading managed analysis IDs. A small named-code function owns this discrimination; the existing exporter consumes it. Related source-reading findings remain separate and conditional, never assigned to a decision by position.
2. Extend the shared decision view's permission entries with the actual criterion/rule references and canonical parent address. Export permission statements, applicability, scope, standing and blockers into Options, the decision summary, a Permissions listing and Markdown. Use one renderer for these channels. A permission adds no constraint, authenticates nothing and cannot erase an exclusion. No returned permission is not a prohibition.
3. Qualify open items by option label, with labels explicitly caller wording. Query-level UNDETERMINED prose refers to the proposition and its complement, never implicitly to two declared options. Freeze decision identity in Decision list and question/option identity in Options.
4. After a content-changing assertion edit attributed as user_choice, rebind only criterion_ref/rule.warrants entries exactly equal to the previous adoption origin. Preserve all independent references. Keep the before/after edit receipt and immutable prior snapshot; do not change rule-definition versions or epistemic standing. Non-choice, source-bound and unrelated references are not retargeted. A named pure decision is shared by the edit consumer.
5. Direct intent tests cover successful source-reading inclusion, no conditional promotion, no inferred permission/necessity, mixed reference preservation, null/empty/boundary inputs and unchanged prior data. Pin changed pure decisions with Detective's prescribed two-sign workflow; report limitations honestly. Verify actual CLI/MCP, workbook cells and exact retained audit replay. Run a different disease/phase model walkthrough after each coherent nontrivial implementation wave.

## Risks / Trade-offs

- More output can obscure decisions -> concise permission summaries plus exact linked rows; no repeated full raw rule dump.
- A shared source reference resembles an adoption reference -> replace exact old origin only, never substrings or every warrant.
- Conditional permission is mistaken for checked entry eligibility -> display applicability and residual conditions separately; keep original verdict/feasibility unchanged.
- Different operation schemas share path names -> operation discrimination, real source_assertions regression artifact and independent plain interpretations coverage.

## Migration Plan

Additive output columns/permission listing and corrected display only; existing canonical inputs remain readable. New revisions use consistent adoption references; historical artifacts remain unchanged. Revert the scoped commit to roll back.
