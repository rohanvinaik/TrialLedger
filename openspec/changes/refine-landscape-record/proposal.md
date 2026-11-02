# Proposal: a faithful registry record and a readable workbook

## Why

A clinical development professional needs the registry's information in one readable place, including
eligibility and posted safety, without manually transcribing hundreds of pages. The report must preserve what
the source says and make missing information visible. It must not mix reporting with clinical interpretation.

## What changes

- Build schema-4 `landscape.json` directly from retained registry records, with source paths defined once in `fields`.
- Present the same evidence in `landscape.xlsx` and through MCP row addresses: identity, design, population,
  exact eligibility, interventions, registered outcomes, posted results, analyses, baseline, flow, safety and links.
- Keep only strictly warranted direct derivations, such as exact eligibility segmentation, source collection
  states, results availability, source-defined labels, document links and directly returned RxNav evidence.
- Preserve observational and expanded-access context as well as interventional fields. Keep groups, populations,
  units, denominators, time frames, precision, explicit zeros and missing values at their source scope.
- Remove inferred setting, indication assignment, criterion ranking, biomarker recognition, compiler output and
  across-trial findings from the ordinary reporting path. Ordinary reports perform no MeSH enrichment.
- Verify retrieval and offline reproducibility; independently check source → record → workbook/MCP across
  study types, including sparse, malformed and mixed-type cases.

## Scope

Layer one contains registry facts and strictly warranted direct derivations only. Clinical inference, defaults,
proposals, comparative judgments and trial design belong to layer two. Existing layer-two designs remain separate;
this change neither redesigns them nor makes their completion a reporting prerequisite. Publications and posted
documents are linked, not interpreted. No language model processes trial content.

## Capabilities

### Modified Capabilities

- `landscape-record`: source-preserving reporting with a compact field dictionary and readable workbook/MCP.

## Impact

The report assembles fields directly rather than passing through clinical analysis machinery. The workbook and
MCP consume the same record. Existing archival pull/verify behavior remains a separate preservation operation.
