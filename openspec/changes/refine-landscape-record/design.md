# Design — faithful clinical reference reporting

## Context

The source writer and clinical workbook exist. This repair brings the whole project into one coherent
structure without importing the separate designer into reporting. The authoritative behavior is
`openspec/specs/registry-reporting/spec.md`; the full layer-two design is `add-design-synthesis/design.md`.

## Goals / Non-Goals

**Goals:** query or name studies; retain their source evidence; write matching selected clinical JSON and a
readable workbook; let the assistant retrieve and quote the same evidence. Preserve original structured
checks and warrants, canonical drug source identities, and appropriate fields for every declared study type.

**Non-goals:** interpreting eligibility, choosing key criteria, inferring treatment setting, selecting
biomarker roles, ranking comparability, proposing thresholds or constructing a protocol in this operation.

## Decisions

### 1. One reporting path

Preview resolves the request and fixes the query before retrieving studies. Direct/relay retrieval uses the
same request plan, pages, counts and identities and records its mode. Explicit identifiers are reconciled
individually. Failed or incomplete runs are named and resumable where safe; completion means the record and
workbook have been produced, not that every requested identifier was found.

Raw responses are retained. The clinical JSON is a selected projection, with a field dictionary identifying
sources and direct transformations. The archival pull remains available when every raw field and the
registry's own CSV/workbooks are required. It uses the same source-preservation principles, not another
clinical interpretation path.

### 2. Canonical drug evidence

Use the existing RxNorm identity and RxClass-by-concept machinery. Preserve own name, canonical concept,
related ingredients and alias roles. Attribute class assertions only to the entity their responses name;
never widen a salt, brand, biosimilar or combination by convenience. Missing identity, failed lookup,
negative lookup and conflict remain different. Retain responses and versions; ordering aliases must not
choose a clinical fact. Search expansion is explicit and separate from interpreting retrieved studies.

### 3. Source assembly and checks

The field table owns source paths and registry types. Assembly copies values and their nesting without a
clinical reader. A malformed scalar refuses the typed report at a named source location; its original raw
response remains retained and is never coerced. Collections distinguish stated, stated empty, absent and
malformed. Zero and false remain values.

Eligibility may be divided only by unambiguous source headings and physical passages with exact offsets;
joining the passages reproduces the original. These display divisions do not decide a criterion's referent,
force or clinical meaning. No candidate atom is a requirement.

The original approved structured checks run on source fields, not interpreted text. Their named results do
not overwrite sources. Results state remains separate from planned outcomes; supplied submission-under-
review, delay and waiver facts are presented beside it. Publication roles and documents are copied/linked,
not treated as findings read from those documents.

### 4. Clinical workbook and agent access

One Trial index row per study leads to the full Trial review dossier. Shared listings hold exact eligibility,
planned and posted outcomes, statistical analyses, baseline, participant flow, local groups and safety, with
sources and record addresses. Observational population/sampling/follow-up/specimen fields and expanded-access
availability/type fields are kept alongside applicable interventional design fields.

Population, group, denominator, unit, time frame and reporting period remain attached to each number. Do not
merge local group identifiers across modules. Source text is text even when it resembles a formula. Numbers
are numeric only when preserved exactly; long/unrepresentable values point to their retained record location.
Continuation sheets preserve all rows. Actual sparse, long and mixed-type workbooks are visually reviewed.

Long dossier values continue across visibly labelled, ordered rows without losing any character. The
independent checker reconstructs each complete value and detects omitted, reordered or duplicated parts.
Index title, sponsor and design cells wrap with row heights that expose all text. This is a bounded
readability/fidelity check, not permission to shorten source content or add an interpretation layer.

The assistant previews, gathers and answers from the same saved record, with bounded paging and exact workbook
addresses. It speaks in clinical terms and supplies the workbook. Layer-two requests are separate calls; the
LLM does not supply missing source facts, rewrite responses or perform a hidden interpretation during gathering.

### 5. Verification and separation

Replay uses retained inputs and the writing derivation version, checks evidence identities and reconstructs
JSON/workbook. Fingerprints include actual dependency code and resources, not unrelated layer-two modules or
help text. Import/call boundaries prevent reporting from invoking interpretation, including shadow output.
The separately callable reasoning layer accepts explicit typed premises and preserves their origin; it does
not confer registry standing on an agent's assertions.

## Acceptance

Independent checks compare source -> JSON -> workbook -> agent/address. Cover interventional, observational
and expanded-access source shapes, applicable metadata and enum branches, exact prose, local identities,
precision, zero/false and empty/missing/malformed boundaries. Change identities, ordering, cardinality and
optional values and plant paired losses; expectations do not call the producer's selector or formatter.
Clinical examples aid review but no trial id or phrase list may select extraction behavior.

Run current ordinary tests, type/lint checks, relevant Detective/two-sign behavior checks, retained-input
replay and installation/entry-point checks. Report incomplete or ungateable checks as such. Record the actual
proof basis and remaining limits; a test count does not establish clinical correctness. No new campaign of
clinical interpretation is needed to complete the generic source writer.

## Migration and risks

Keep original evidence and archival outputs verifiable under their writing versions. Remove wrong readers
and their public routes rather than leave compatibility fallbacks. Reconcile CLI, MCP, agent guide and
OpenSpec together. Preserve useful symbolic components in their separate layer; missing integration is not
a reason to delete correct logic. Any input the writer cannot represent is named, never silently dropped.
