# Tasks: faithful registry reporting

## 1. Direct reporting path

- [x] 1.1 Establish the schema-4 reporting field table, source paths, consumers and display dictionary. The earlier
      schema-3 contract was implemented; its completion does not complete this replacement contract.
- [x] 1.2 Assemble selected registry fields directly; remove clinical-analysis/compiler/indication dependencies
      from ordinary reports, including MeSH enrichment, inferred setting, key-criterion ranking, biomarker
      recognition and across-trial findings.
- [x] 1.3 Retain exact eligibility segmentation, results state, collection presence, links and direct RxNav
      evidence only with their source/rule basis; no default, proposal or inferred clinical membership.
- [x] 1.4 Preserve observational/access design and population fields, exact prose, result structure, local group
      identities, populations, denominators, units, precision, zeros/false and named missing/malformed states.

## 2. Readable workbook and MCP

- [x] 2.1 Render the reporting sheets in design §3, with a compact index, full dossier/listings, clinical registry
      labels, conditional columns and informative absence; remove inference sheets and clinical rankings.
- [x] 2.2 Preserve cell values/types and links, exact long-text fallback, continuation sheets and read-back checks.
- [x] 2.3 Every listing address resolves through paginated MCP to the same scoped source evidence.

## 3. Retrieval and verification

- [x] 3.1 Keep preview, fixed search, direct/relay resume, complete page/count/identity checks and requested-ID accounting.
- [x] 3.2 Replay the retained reporting inputs offline and compare the record/workbook; name missing/changed inputs
      or writing-code mismatch without repair. Verify direct sourced lookups without interpreting their meaning.

## 4. Acceptance and delivery

- [x] 4.1 Check the relevant metadata-to-field complement and schema/enum/study-type applicability branches;
      keep independent source expectations and cases demonstrating the generic writer has no trial-specific rules.
- [x] 4.2 Execute independent source → record → workbook → MCP checks across applicable type/design/population/
      results/clinical-breadth combinations, including explicit empty/absent/malformed and source-present atypical fields.
- [x] 4.3 Execute structural perturbations and paired intact/seeded-defect checks; visually inspect homogeneous and
      mixed-type workbooks, long prose and many groups; publish per-combination findings and remaining reporting gaps.
- [ ] 4.4 Verify changed pure decisions with two-sign intent tests and Detective, run relevant local/release checks,
      offline replay and fresh-sandbox procedure, and measure performance on frozen inputs. No test result is a
      claim of clinical correctness or complete clinical interpretation.
- [x] 4.5 README, AGENTS project guide, SKILL, DEVELOPING, CLI/MCP descriptions and documented-interface reflect
      the source-preserving reporting operation. Existing layer-two plans remain separate and unchanged.

Current verification evidence and explicit Detective limitations: `acceptance/reporting-recovery.md`.
Task4.4 remains open because incomplete/ungateable mutation runs are not passes; the direct-report
implementation, independent preservation checks, offline replay and fresh local installation have run.
