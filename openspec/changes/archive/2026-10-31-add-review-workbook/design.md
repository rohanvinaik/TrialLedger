# Design — add-review-workbook

## Context

The ingestion layer is built (commit `ac9c8b6`): `trialledger pull` writes the complete registry records
(`studies.json`) and the registry's own spreadsheet (`studies.csv`), all or nothing. The design this change
begins is `docs/THEORY_OF_THE_CASE.md`. The founder's decisions for it, paraphrased (his messages are kept on
his machine, not in the repository): facts are to come from the unambiguous fields of the API layer just
built; raw publications are linked and brought to the surface, so a reader can quickly scan the source text,
and a thorough parser for them is not needed yet; what counts as significant should be fairly self-evident;
the spreadsheet is to carry eligibility and safety. The purpose this change serves, also paraphrased: at
bottom a clinical trial design project, in which clear, well-built symbolic systems automate the design of
clinical trials, as TriageGeist automated triage and harmonizing auto-populated a data record. The ledger and
edit checks here are the trusted substrate that design inference will run on; the review workbook is the first
projection of it.

## Goals / Non-Goals

**Goals:** a ledger of every record element with location and role; approved edit checks with named
outcomes; a review workbook answering the ten design questions, every value labelled stated, computed or
needs review, every source linked.

**Non-goals:** reading publications; computing anything across trials; interpreting free text; any model.

## Registry facts this design rests on (tasks 1.1–1.3, verified 2026-10-31)

Sources read whole: the vendored API contract `spec/ctg-oas-v2.yaml` (2.0.5); the API's field metadata
(`/api/v2/studies/metadata`, vendored as `TrialLedger/registry/ctg-metadata.json`) and enum table
(`/api/v2/studies/enums`, vendored as `TrialLedger/registry/ctg-enums.json`); the Protocol Registration Data
Element Definitions (<https://clinicaltrials.gov/policy/protocol-definitions>, last updated 2025-04-24) and
the Results Data Element Definitions (<https://clinicaltrials.gov/policy/results-definitions>, last updated
2024-12-31), read as rendered pages because the site serves every URL the same JavaScript shell. Live
measurements used a 2,529-study pull (`filter.advanced=AREA[StartDate]RANGE[2014-01-01,2014-01-10]`, data
timestamp 2026-10-30T09:00:04).

- **Results flag.** The metadata defines `hasResults` as `FUNC Present(ResultsFirstSubmitDate)`, «Flag that
  indicates if a study has posted results on public site». In the sample, the flag, the presence of a
  results section and the presence of `resultsFirstSubmitDate` agreed on every study (352 with, 2,177
  without).
- **References.** The protocol definitions give the responsible party one choice per reference: «Results
  Reference? Indicate if the reference provided reports on results from this clinical study. Select
  Yes/No» (RESULT, BACKGROUND). DERIVED is added by the registry and is not defined. Registry-wide on
  2026-10-30 (`/api/v2/stats/field/values?fields=ReferenceType`): 126,368 studies with DERIVED references,
  99,393 BACKGROUND, 43,671 RESULT, 379,555 none. In the sample's 2,177 studies without posted results:
  563 DERIVED, 360 BACKGROUND, 163 RESULT. The classic study page headed derived references «Publications
  automatically indexed to this study by ClinicalTrials.gov Identifier (NCT Number)»; that wording is known
  only from third-party copies (the current page returned 403 to the scraper) and is not used as a label.
- **Arm–intervention cross-reference.** Every one of the sample's 5,362 `armGroups[].interventionNames`
  entries equals `"<InterventionType label>: <interventions[].name>"`, the label being the enum table's
  `legacyValue` (for example `DRUG` → `Drug`); none equals a bare name. Every one of 5,376
  `interventions[].armGroupLabels` entries equals an arm's `label`.
- **Adverse events.** `numEvents` is absent, not zero, when unreported (9,441 of 13,715 serious-event
  entries; 17,144 of 22,932 other). Per-event `numAtRisk` was present on every entry (the metadata calls
  it «internally calculated»). Deaths totals were absent for 413 event groups (required only for primary
  completion on or after 2017-01-18).
- **Ages** are `<n> <unit>` with units Year(s), Month(s), Week(s), Day(s), Hour(s), Minute(s). An absent age
  cannot be told apart from «N/A (No limit)»: the metadata says «Required but data can be [Missing] if N/A
  (No limit) is selected».
- **Dates** are partial (`yyyy`, `yyyy-MM`, `yyyy-MM-dd`); the start-date type was absent in 1,767 older
  records («Required for INT/OBS that are FRED»).
- **Eligibility headings.** The definitions say «Use a bulleted list for each criterion below the headers
  "Inclusion Criteria" and "Exclusion Criteria"». The exact strings occur once each in 2,341 of 2,451 texts;
  variants in case and punctuation are rare (`Inclusion criteria:` 52 lines, `INCLUSION CRITERIA:` 4).
- **Link forms.** Study page: the registry's own CSV gives `https://clinicaltrials.gov/study/<NCT Number>`
  as the Study URL on all 2,529 rows. Posted documents: `https://cdn.clinicaltrials.gov/large-docs/<last two
  digits of the NCT number>/<NCT number>/<filename>` returned `application/pdf` for all 155 documents in the
  sample. PubMed: `https://pubmed.ncbi.nlm.nih.gov/<PMID>/` returned the article page for the three PMIDs
  tried.

## Decisions

1. **Sources.** Values come from the record's structured fields. Free text (eligibility, descriptions) is
   carried exactly as the record holds it (the API's markdown rendering, `markupFormat=markdown`) and never
   turned into structured values. Publications and documents are linked.
2. **The ledger is derived from the record being written**, the same content as `studies.json`, so the
   workbook is a pure function of the saved record and reproducible from it. An entry is one value of the
   record with its location (its path in the record). The ledger is lossless: rebuilding a record from its
   entries reproduces it exactly, and that is how it is tested. Roles come from the record's structure only:
   the section an outcome is listed in, the `type` the results give a measure, the group id a count carries,
   the type the registry gives a reference, the arm a description belongs to.
3. **Absence has four named states.** A field is `reported`, or absent for one of three reasons the
   registry itself states: `not_applicable` (the definitions limit the element to other study types, for
   example «Interventional Study Design (For interventional studies only)»; «EA does not have this data
   element»), `redacted` (a withheld study, where the metadata says «Redacted for Withheld studies» or
   «Marked as [Missing] for Withheld studies»), or `not_reported`. No view shows any of them as zero, none
   or no.
4. **Edit checks are an approved, versioned list** (below), each a pure decision over one record returning one
   of four outcomes with the fields and values involved: `consistent` (the rule applies and holds), `conflict`
   (the rule applies and is violated), `not_applicable` (the rule's condition does not arise in this record)
   or `not_checkable` (a value the rule needs is absent, or its precision cannot decide the rule). A missing
   input is never `consistent`; a conflict never changes a value. Only exact unit conversions are used
   (years↔months; weeks↔days↔hours↔minutes); partial dates are intervals and are in conflict only when the
   intervals cannot be in order. A value present but not of the registry's type is malformed, and its check is
   `not_checkable` with the value named. A cross-reference that matches nothing is a `conflict` only when
   every definition it could match is complete; while an intervention lacks a type or name, an arm a label or
   an event group an id, it is `not_checkable`. A number the record states (a group's number not completed) is
   never replaced by a derived one (Started minus Completed is used only when none is stated); a count stated
   for no group makes its milestone malformed, and a reason type that lists no count for a group leaves that
   group's sum not checkable. A check that is not approved is never gathered, so nothing only it reads can
   affect the checks that run.
5. **Eligibility is split only on the registry's stated headers.** A line consisting of `Inclusion Criteria`
   or `Exclusion Criteria`, optionally followed by a colon, is a heading; the text is split only when it has
   exactly one of each, inclusion first. The split has three parts, the text before the inclusion heading, the
   inclusion part and the exclusion part, and the three joined reproduce the original text exactly; an empty
   part is a blank cell, never a placeholder. Otherwise the whole text is shown and the decision says why:
   `not_split_missing`, `not_split_repeated` or `not_split_order`. Abstaining is the safe direction.
6. **Every cell has a kind**: stated (a structured field, shown with its record location), computed (a
   named rule, shown with its inputs) or needs review (shown with its sources, never filled). Each sheet's
   About entry gives the kind and source of every column; a column whose kind can vary per row carries a
   code column beside it.
7. **"No results posted" is stated with its context.** A study whose `hasResults` is false reads "no results
   posted" in its results and safety items, beside the structured fields that say why results may be
   absent: `derivedSection.miscInfoModule.submissionTracking.estimatedResultsFirstSubmitDate` («Results First
   Submitted Date but not yet Posted (e.g., still under QC review)»), `statusModule.dispFirstSubmitDate`
   (a certification or extension request to delay results) and `statusModule.resultsWaived`. Its linked
   publications are listed beside it.
8. **Publications are labelled in the registry's terms and no further.** RESULT: «reports on results from
   this clinical study», as the responsible party marked it. BACKGROUND: entered by the responsible party,
   not marked as reporting results. DERIVED: added by the registry, role not stated. A derived publication is
   never presented as a results publication or a secondary analysis.
9. **The spreadsheet never alters a value.** Every text value is written as text: a value beginning with `=`
   is never a formula. A value a cell cannot hold exactly is not truncated, cleaned or rounded: the cell
   names the reason and the record location where the value is (`cells.cell_text_state`:
   `forbidden_characters` for any character XML 1.0 forbids, control characters, U+FFFE, U+FFFF and lone
   surrogates alike; `carriage_return`; `too_long`, past 32,767 UTF-16 code units; `cells.cell_number_state`:
   `not_exact` for a number openpyxl's `"%.16g"` would not give back, an integer of 17 or more digits or one
   no double holds, a float needing 17 significant digits, negative zero, NaN or an infinity). A sheet that
   would exceed the format's 1,048,576 rows continues on a numbered sheet ("Record 2"), so no value is
   dropped. The workbook is checked by reading it back cell by cell against the ledger, comparing the kind of
   value as well as the value (a boolean is never taken for a count); it is reproducible byte for byte except
   for the write time in `docProps/core.xml`.
10. **Workbook format: two `.xlsx` files**, `review.xlsx` (the design sheets and the checks) and
    `record.xlsx` (the Record sheets: every value), because a reviewer outside a terminal opens a workbook,
    the data has several tables per study, and the format carries no encoding ambiguity. The Record sheets
    are most of the cells (1.35 of 2.18 million for 44 results-heavy Phase 3 trials) and Google Sheets opens
    at most 10 million cells in one spreadsheet, which about 200 such trials fill with them and about 500
    without; so the record has its own file (the founder's choice, 2026-10-31), and the writer counts each
    file's cells and names one over the cap (`cells.book_size_state`). The writer is `openpyxl`, one new
    runtime dependency, recorded in the manifest and lock. A folder of CSVs was considered and rejected for
    the reader this serves.
11. **Significance, in this change, is the ten questions.** Significance across trials, what distinguishes
    them versus what they all share, belongs to the cross-trial design change.
12. **Every value carries a warrant, and the workbook is certified** (the founder, 2026-10-31, paraphrased:
    each piece of information should be able to carry a strict warrant of the basis on which it entered the
    record). A study's digest is SHA-256 over its record in canonical JSON; the pull's root is the Merkle root
    of its studies' digests, in pull order; both are recorded in `studies.json`'s provenance, each study
    digest beside its NCT number, with the spreadsheet's digest. The code root is the Merkle root of the files
    the workbook's derivation reads (`warrants.derivation_files`: `workbook.py`, every package module it
    imports, followed through their own imports, `__init__.py` and the registry tables), recorded with the git
    commit of that code (`record.code_commit`, marked when it has uncommitted changes) and the writer
    (openpyxl's version). The command line, the network layer and the folder's writer and verifier are not in
    it, so changing them leaves every folder verifiable (the founder's choice, 2026-10-31). The record root
    commits to the whole provenance, the study digests with their labels, the studies' root and the
    spreadsheet's digest among it, so nothing in it can change unseen. A value's warrant is a hash committing
    to its basis: a stated value to its study digest, location and value; an absent value to its location and
    absence state under the absence rule; a computed value to its rule (id, tool version, the code root, the
    digest of the functions that apply it, the digests of the registry data it reads) and its inputs'
    warrants; a review item to its reason and sources. The code root makes a warrant commit to everything a
    rule can read, constants and tables included, not only the functions named. Each typed row carries the
    warrant of its cells; a Record row's warrant is determined by its study's digest, location and value.
    `write_record` certifies the workbook it wrote before renaming the folder into place. `trialledger verify
    <folder>` refuses a `studies.json` whose objects repeat a key, re-derives every digest, label and root,
    and, under the same code root, every cell and warrant; then it writes the workbook afresh and compares the
    file part for part, so a changed link, format or added part is named even when every cell holds its value.
    A folder written by other derivation code or another writer is not certified by this one; `verify` names
    the commit that wrote it, at which it can be verified. Correctness of the rules themselves rests on their
    two-sign tests and Detective certificates; warrants make each derivation reproducible and any alteration
    visible.
13. **Every value of the record is presented in the registry's own categories.** The Record sheets of
    `record.xlsx` list every ledger entry: the study, its category (the section and module names the API
    metadata gives, e.g. "Study Protocol › Study Design"), the field (the metadata's title), the location, the
    value exactly as the record holds it, and its structural role. The typed sheets are projections of it onto
    the design questions; nothing in the record is left unpresented.
14. **Construction follows Detective's own workflow.** Each decision is written unwired as a pure function
    returning named codes; given direct-call intent tests for both signs; converged with
    `detective converge --two-sign` in isolation, with every survivor killed by a test, proven equivalent
    with a note, or fenced; and only then wired in. The file-writing shell gets durability tests. The real
    entry point is verified end to end, then live. `tests/test_wiring.py` holds every function of the
    package to the production path, or to a declared reason (the proposed checks' code, dormant until
    approved), since a dead-code scan counts a function named in a table as used.

## Code shape (reconciled with the code; the process contract's §2)

| Module | Owns | Public interface | May import |
|---|---|---|---|
| `ingest.py` | the network shell and its decisions | `pull`, `Pull`, `PullError`, the pinned decisions | `httpx` |
| `registry.py` | the registry's own names: field titles, categories, enum labels, withheld-redaction fields | `category`, `title`, `enum_labels`, `redacted_when_withheld`, the data digests | the package data in `TrialLedger/registry/` |
| `ledger.py` | the record as entries: lossless leaves, structural roles, absence and results states | `get`, `as_list`, `location`, `field_path`, `entries`, `node_role`, `absence_state`, `field_state`, `results_state` | `registry` |
| `checks.py` | the edit checks: decisions, the versioned list with basis and approval, one gatherer per check, the shell over one record | the decisions, `CHECKS`, `APPROVED`, `BASIS`, `DECISIONS`, `GATHERERS`, `Malformed`, `run_checks` | `ledger`, `registry` |
| `eligibility.py` | the eligibility split | `split_eligibility` | nothing |
| `links.py` | link forms and reference roles | `study_link`, `pubmed_link`, `document_link`, `reference_role` | nothing |
| `cells.py` | what a spreadsheet cell, sheet or file can hold | `cell_text_state`, `cell_number_state`, `sheet_fits`, `book_size_state` | nothing |
| `warrants.py` | digests, the Merkle root, the code root, warrants | `canonical`, `digest`, `study_digest`, `merkle_root`, `code_root`, `stated`, `absent`, `computed`, `review`, `literal`, `row`, `rule`, `code_digest` | nothing |
| `workbook.py` | the projection into two books, the writer, the certifier and the file comparison | `write_workbook`, `certify`, `file_problems`, `SHEETS`, `REVIEW`, `RECORD`, `BOOKS`, `RULE`, `CODE_ROOT`, `WRITER`, `WorkbookError` | all of the above, `openpyxl` |
| `record.py` | the all-or-nothing write of the four files, the provenance digests and roots, verification | `write_record`, `digests`, `record_root`, `record_problems`, `verify_folder` | `ingest`, `workbook`, `warrants` |
| `cli.py` | the entry point: `pull` and `verify` | `main` | `ingest`, `record`, `workbook` |

Path: `trialledger pull` → `cli.parse_query_args` → `ingest.check_query` → `ingest.pull` (every page, both
formats, one snapshot) → `record.write_record` (digests and root into the provenance; `studies.json`,
`studies.csv`, then `workbook.write_workbook`: each sheet's rows from `ledger`, `checks`, `eligibility`,
`links`, `cells`, each cell a fact with its warrant; read back and `certify`; rename into place) → the
summary line. `trialledger verify <folder>` → `studies.json` read refusing repeated keys →
`record.record_problems` (digests, labels, both roots) → the code root and writer compared →
`workbook.certify` → `workbook.file_problems`.

## Approved edit checks (version 1)

Anchors are on <https://clinicaltrials.gov/policy/protocol-definitions> (P) and
<https://clinicaltrials.gov/policy/results-definitions> (R), as the API metadata's `dedLink` gives them.

| Id | Relation | The registry's words |
|---|---|---|
| `closed_primary_completion_actual` | Overall status COMPLETED or TERMINATED → primary completion date type ACTUAL | P#OverallStatus «Completed: The study has concluded normally; participants are no longer receiving an intervention or being examined (that is, last participant’s last visit has occurred)»; «Terminated: Study halted prematurely and will not resume; participants are no longer being examined or receiving intervention». P#LastFollowUpDate «The date that the final participant was examined or received an intervention for the purposes of final collection of data for the primary outcome, whether the clinical study concluded according to the pre-specified protocol or was terminated. [...] Once the clinical study has reached the primary completion date, the responsible party must update the Primary Completion Date to reflect the actual primary completion date.» |
| `closed_completion_actual` | Overall status COMPLETED or TERMINATED → study completion date type ACTUAL | The status definitions above; P#LastFollowUpDate «The date the final participant was examined or received an intervention for purposes of final collection of data for the primary and secondary outcome measures and adverse events (for example, last participant’s last visit), whether the clinical study concluded according to the pre-specified protocol or was terminated. Once the clinical study has reached the study completion date, the responsible party must update the Study Completion Date to reflect the actual study completion date.» |
| `withdrawn_actual_enrollment_zero` | Overall status WITHDRAWN and enrollment type ACTUAL → enrollment count 0 | P#OverallStatus «Withdrawn: Study halted prematurely, prior to enrollment of first participant»; P#IntEnrollment «the actual total number of participants that are enrolled in the clinical study» |
| `phase_interventional_only` | Study type other than INTERVENTIONAL → no phase other than NA | P#IntStudyDesign «Interventional Study Design (For interventional studies only)», containing P#StudyPhase «For a clinical trial of a drug product (including a biological product), the numerical phase of such clinical trial» |
| `results_flag_first_submit` | `hasResults` true exactly when `resultsFirstSubmitDate` is present | metadata `hasResults`: «FUNC Present(ResultsFirstSubmitDate)», «Flag that indicates if a study has posted results on public site» |
| `recruiting_site_recruiting_study` | Two or more locations, one RECRUITING → overall status RECRUITING; an overall UNKNOWN is the registry's assignment and not checkable | P#OverallStatus «If at least one facility in a multi-site clinical study has an Individual Site Status of "Recruiting," then the Overall Recruitment Status for the study must be "Recruiting."»; glossary «Last verified»: an unconfirmed study's «recruitment status is shown as unknown» |
| `arm_interventions_declared` | Every arm's intervention name is `<type label>: <name>` of a declared intervention | P#InterventionName «If multiple Arms or Groups have been specified, indicate which Interventions (or exposures) are in each Arm or Group of the study, using the Cross-Reference check boxes»; the label is the enum table's `legacyValue` |
| `intervention_arms_defined` | Every arm label an intervention names is the label of a defined arm | as above |
| `ae_counts_name_groups` | Every adverse-event count's group id is an event group's id | metadata `stats.groupId` «Internal Arm/Group ID», `eventGroups.id` «Internal group id»; R#AdverseEventAffected «Number of participants, in each arm/group» |
| `ae_affected_within_at_risk` | Per event and group: participants affected ≤ at risk; a blank at-risk count takes the group's table total | R#AdverseEventAffected «Number of participants, in each arm/group, experiencing at least one event being reported.»; R#AdverseEventAtRisk «Number of participants assessed, in each arm/group, for adverse events (that is, the denominator for calculating frequency of adverse events). Leave blank to indicate that the value specified as the total at risk in the arm/group for the table should be used.» |
| `ae_event_within_group_total` | Per event and group: participants affected ≤ the group's total affected in that table | R#SeriousTotalAffected «Overall number of participants affected by one or more Serious Adverse Events, for each arm/group.»; R#OtherAE_Affected «Overall number of participants affected, for each arm/group, by at least one Other (Not Including Serious) Adverse Event(s) reported in the table.» |
| `ae_events_at_least_affected` | Per event and group, where events are reported: events ≥ participants affected | R#OtherAEEvents «Number of occurrences, in each arm/group, of the adverse event being reported.»; R#AdverseEventAffected as above |
| `ae_group_totals_within_at_risk` | Per group: deaths, serious and other totals affected ≤ the matching total at risk | R#Mortality_Affected «Overall number of participants, in each arm/group, who died due to any cause»; R#Mortality_AtRisk «included in the assessment of deaths due to any cause (that is, the denominator [...])»; R#SeriousTotalAffected / R#SeriousAE_AtRisk; R#OtherAE_Affected / R#OtherAE_AtRisk, each «(that is, the denominator for calculating frequency [...])» |
| `flow_reasons_account` | Per period and group, where reasons are given: the reasons' participants sum to those not completed | R#DWReason «If reasons are provided, the total number of participants listed as Not Completed must be accounted for by all reasons for non-completion.»; R «Not Completed (calculated automatically) [...] calculated automatically by subtracting Completed from Started» |
| `age_limits_ordered` | Minimum age ≤ maximum age, where the units convert exactly | P#EligibilityMinAge «The numerical value, if any, for the minimum age a potential participant must meet to be eligible»; P#EligibilityMaxAge «The numerical value, if any, for the maximum age a potential participant can be to be eligible» |
| `start_before_primary_completion` | Start date ≤ primary completion date (as intervals) | P#StartDate «the actual date on which the first participant was enrolled»; P#LastFollowUpDate (primary completion) as above |
| `primary_completion_before_completion` | Primary completion date ≤ study completion date (as intervals) | P#LastFollowUpDate: the primary completion date is final collection «for the primary outcome»; the study completion date is final collection «for the primary and secondary outcome measures and adverse events» |

Not approved: any check over free text; any requirement check (a field the definitions require but the
record omits is shown as not reported, not as a conflict).

Version 1 as built: five checks are **approved** (basis "stated rule" or "registry function":
`closed_primary_completion_actual`, `closed_completion_actual`, `recruiting_site_recruiting_study`,
`flow_reasons_account`, `results_flag_first_submit`) and run in the workbook. The other twelve are
**proposed** (basis "stated scope" or "entailed by definitions") and wait for the founder to approve them by
name; they are built, pinned and listed with their basis on the Check Rules sheet, and do not run until
approved. On the 2,529-study sample all seventeen gave no conflict.

## Sequence after this change

1. The cross-trial design change, the purpose the founder restated: comparator bars on matched endpoints
   and time points, cohorts, niches as empty regions of the design space, mechanism-linked exclusions
   proposed as candidates for review, and recurring protocol language, each computed over comparable trials
   with the trials it rests on shown. The design space's indication and mechanism axes are the registry's
   own MeSH coding (`derivedSection.conditionBrowseModule`, `derivedSection.interventionBrowseModule`).
2. The end-stage parser (`add-publication-evidence`), from the founder's additions, paraphrased: results the
   registry lacks could be imputed from papers; and a raw paper can be processed by its sections, the sections
   deciding which differential parsing systems are assigned, each hunting the specific context that resolves a
   gap or inconsistency in how the trial's data is encoded, study data being so rigidly typed and formal that
   probably not even a small local model is needed. Designed from the Regenesis puller as read on 2026-10-31
   (`regenesis/puller/`, `lift.py`, `gse_emit_narrative.py`, `reason.py`), whose parts it recomposes;
   gap-driven hunting itself is new:
   - **Gaps drive the hunt.** The ledger's open items (needs-review cells, not-checkable and conflicting
     checks, results not posted) become typed queries: the fact sought, and the record's own vocabulary to
     hunt for (arm labels, intervention names and other names, registered outcome measures and time frames,
     units).
   - **Sections first, by their published types.** A paper is read in its own typed structure: PubMed's
     structured abstract (labelled sections with NLM categories) and, where open access, the full text's
     typed sections and tables. Section classes are kept or vetoed by heading alone, veto first, as the
     Regenesis puller does (Introduction, Discussion and the like are never evidence for a figure).
   - **Differential parsers.** Each fact type has a deterministic grammar bound to the section classes
     where that fact is stated (enrollment and randomization counts; per-arm outcome values with their
     units, intervals and p-values; adverse-event counts per arm; time points).
   - **A resolver deck**, after Regenesis's deterministic "cassettes": arm, intervention, outcome and
     time-point identity between the paper's words and the record's, each abstaining unless exactly one
     candidate fits.
   - **Censors**, after Regenesis's `cannot` rules: no figure from a vetoed section; none whose arm, outcome
     or time point is unresolved; none without its exact sentence or table cell.
   - **Evidence, not values.** A figure found enters the ledger as publication evidence with its warrant
     (PMID, section path, sentence or table cell, character span, parser and resolver versions), regime
     "from the paper"; approved coherence rules compare it with the registry, and a disagreement is shown,
     never resolved. Every fetch and parse ends in a named outcome (no publication, not open access, fetch
     failed, no matching section, not found, ambiguous, found): a failure never reads as an absence, a
     pathology the Regenesis reading found there.
   - Which publications to read waits on the founder: RESULT alone misses most results papers, and DERIVED
     states nothing about what a paper reports.
3. An interface that needs no terminal.

## Risks / Trade-offs

- A study whose eligibility text uses a variant heading is shown whole: correct, less convenient (about 4%
  of the sample).
- The document link form is observed, not documented; it is verified live by `tests/test_live.py`.
- A large pull makes large workbooks (the 2,529-study sample: 6.5 million cells, 72% on the Record sheets);
  a sheet over the row limit continues on numbered sheets rather than drop rows, and a file over Google
  Sheets' 10 million cells is named when it is written.
- `trialledger verify` writes the workbook afresh to compare the file, so it takes about as long as the
  write.
- A folder can be certified only by the derivation code and writer that wrote it: a code root or writer that
  differs is named, with the commit that wrote the folder, never compared approximately. Any edit to the
  derivation code, its docstrings included, therefore makes earlier folders verifiable only at their commit.

## Adversarial review (2026-10-31)

A Codex review, given the code and the specs and asked only for demonstrated defects, reported fourteen.
Each was reproduced before anything was changed, and each holds:

1. A drop-out reason list that is not a list was skipped and the check read consistent → malformed inputs
   are named and not checkable (decision 4).
2. A stated NOT COMPLETED count that is not a whole number was replaced by Started minus Completed →
   never replaced (decision 4).
3. An intervention without a type made a false conflict ("None: Testamab") → not checkable; the registry
   form says "type not reported".
4. Proposed checks were computed and only then filtered, so one malformed field could stop the approved
   checks → one gatherer per check, and only approved checks are gathered.
5. A changed hyperlink certified, 6. a boolean in place of a count certified (`1 == True`) → `verify`
   compares the file part for part, and the certifier compares kinds of value.
7. A check-count warrant did not commit to the decisions and constants that determine the count → every
   rule warrant commits to the code root.
8. A repeated key in `studies.json` certified, 9. a changed NCT label in the provenance certified → both
   refused and named; the record root now also commits to the rest of the provenance.
10. An unreadable workbook raised instead of being named → named, `not_certified`.
11. An empty "before the inclusion heading" part was shown as a placeholder, so the joined parts did not
    reproduce the text → a blank cell (decision 5).
12. A value a cell could not hold named its sheet row, not its record location → it names the location.
13. A number past 2**53 was rounded on write and the whole write failed → `cell_number_state`.
14. U+FFFF passed as writable and produced a file that cannot be read back → every character XML 1.0
    forbids is refused (decision 9).

A second Codex review, asked to break those fixes, reported ten more; each was reproduced, and each holds:
a non-text results submission date counted as present; a reason type listing no count for a group, and a
count stated for no group, let the flow check decide; a count longer than Python converts raised; two
reader errors (a missing shared string, an unknown compression) escaped the certifier; a check detail no
cell could hold pointed at "the whole record"; an added key inside the study digests changed no root; a
lone surrogate in `studies.json`, and a number longer than Python converts, crashed `verify`; and the wiring
inventory skipped lambdas. Each now reads not checkable, is named, or is reached: a malformed value is named;
the record root commits to the whole provenance; the certifier names any reader error; a check names the
fields it reads (`checks.READS`); and `tests/production_path.py` counts lambdas and reaches them.
