# Documented interface: registry reporting

README.md, AGENTS.md and SKILL.md describe the reporting interface. This checklist records outstanding
verification; editing the documentation does not complete a task. Source/runtime checks control completion.

- [ ] Public installation works on Python 3.12+ and passes the release/fresh-sandbox procedure.
- [ ] doctor reports ClinicalTrials.gov/RxNav reachability and direct/relay mode; scope or landscape --preview
  resolves and fixes the search without reading studies, showing members/subclasses, names and filters.
- [ ] landscape gathers the fixed request or requested IDs completely, with pagination/count/identity/snapshot
  checks and requested-ID accounting. Exit 0 complete/previewed, 3 awaiting relay, 2 refusal/stop, 1 failure advice.
- [ ] Relay saves only named URLs/bodies unchanged and resumes safely. It checks form/counts/identities, not each
  value against the live registry; gathered-study drug enrichment is not performed in relay mode.
- [ ] Schema 4 contains only schema_version, request, scope, manifest, statuses, envelope, fields and studies.
  Registry fields are copied plainly, with paths/definitions once in fields; direct derivations name rule/inputs.
- [ ] The report uses direct assembly with exact eligibility segmentation, collection/results states, links,
  counts and source-backed RxNav evidence. It has no clinical analysis/indication/compiler path, MeSH enrichment,
  key-criterion ranking, biomarker recognition, inferred setting or cross-trial findings.
- [ ] The readable workbook presents identity/design/population/eligibility, interventions, registered outcomes,
  posted results/analyses, baseline, flow, groups, safety and source links/dictionary. Relevant observational and
  expanded-access fields survive; groups, denominators, precision, false/zero and missing/malformed states remain
  scoped. Values cells cannot hold exactly name their record location/reason; listings continue without loss.
- [ ] Every listing address reaches the same value through MCP, with bounded paging. The tools are doctor, scope,
  landscape, save_fetch and record. No public design/edits tool or automatic workbook-annotation import is promised.
- [ ] verify replays a landscape or archival pull offline under its writing code, checking sources/record/workbook
  and formatting/links. Missing/changed evidence is named without repair. Old folders need their writing version.
- [ ] The reporting acceptance in refine-landscape-record covers all three study types and applicable design,
  population/results/source states and clinical breadth using independent source expectations, frozen held-out
  selection, regressions, structural perturbations, seeded defects and visual review. Gaps stay named/unmet.

Layer one contains source facts and strictly warranted direct derivations only. Clinical inference, defaults,
proposals, comparison, external-source interpretation and trial design remain separate layer-two work. The ten
clinical-development questions guide evidence access, not an invented obligation to infer answers in the report.
Retrieval, preservation, tests and reproducibility do not certify registry truth or clinical correctness.
