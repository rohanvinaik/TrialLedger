# Design: source → record → readable workbook and MCP

## 1. Reporting boundary

Layer one gathers registry facts and strictly warranted direct derivations. It does not infer clinical meaning,
rank criteria, select biomarkers, assign indication or setting, propose mechanisms, compare trials or design a
protocol. Those operations belong to the existing layer-two work. A clinical interpretation compiler, external
source parser or semantic-conformance framework is not a prerequisite for this report.

The reporting path assembles retained API fields directly. `landscape_record(studies, request, scope,
manifest, answers=None)` takes source studies, not an analysis view. Schema 4 has only `schema_version`,
`request`, `scope`, `manifest`, `statuses`, `envelope`, `fields` and `studies`; there is no legacy compatibility
scaffold. It does not invoke `read_population`, coherence,
universe/indication assignment or the assertion compiler. Ordinary reports do not fetch MeSH enrichment.
Search resolution may use named vocabulary sources to construct the requested query; this does not authorize
clinical interpretation of the studies it retrieves. Direct RxNav response evidence may be retained as sourced
lookup evidence, without inferred memberships or automatic clinical conclusions.

## 2. Record and source contract

Registry copies are plain values in schema 4. `fields` defines each selected field's source path, label, type and
consumer once. Each study has its ID, registry link and digest. A direct derivation names its rule, version and
source inputs. Missing or malformed inputs have named states; neither becomes false, zero, none or a successful
reading. Proposed and interpolated clinical readings are absent from ordinary reporting output.

Preserve clinically useful structured fields and exact prose: identity/status/dates, design, population,
eligibility, arms/cohorts and interventions, registered outcomes, posted results/statistical analyses, baseline,
participant flow, adverse events, limitations, publications and documents. Results keep the registry's nesting;
group identities are local to their module. Keep actual/anticipated enrollment separate, and keep every population,
denominator, unit, time frame, reporting threshold, NA reason, precision and explicit zero with its value.
Registered outcomes remain plans, not observations. Linked publications are not asserted to contain findings the
report has not read.

Cross-type context includes observational model, time perspective, patient-registry flag, target follow-up,
specimen retention/description, study population and sampling method; and expanded-access type flags, availability,
linked record/status and the source-defined count of studies referencing an access record. Multiple boolean flags,
false and missing remain distinct. Preserve a present historical field even if it is optional or unusual for the
study type. Inapplicability is source/metadata-bound, never inferred merely from a missing key.

Eligible direct derivations are limited to source-defined labels, exact links and counts, results/source-presence
states, and lossless eligibility segmentation under unambiguous source headings/bullets. Segmentation retains
literal wording, ordering, bullets and source locations and reconstructs the original text; ambiguous headings leave passages unsectioned. Physical source lines and bounded continuations remain
exact substrings with offsets; joining them reconstructs every character. A heading is a source label, not a clinical polarity or cohort inference.
An empty source list establishes only an empty listing, not zero harms or an absent clinical condition. A missing
or malformed collection is distinguished from an explicit empty list at its exact source pointer.

## 3. Workbook and assistant

The workbook starts with Read me, Trial index and Trial review, then Eligibility, Registered outcomes, Posted
results, Statistical analyses, Baseline, Participant flow, Groups, Safety and Column dictionary. Any direct-rule
listing states its source and purpose. Do not expose inference sheets, key-criterion rankings, inferred setting,
biomarker recognition or cross-trial findings as reporting. Clinical text remains available in the source fields
and exact eligibility/outcome listings rather than being selectively recognized.

Use readable registry labels, filters, stable row identities, wrapped prose and links. Keep the index compact;
long text belongs in the dossier/listings. Present observational cohorts and access programs in their own terms,
without forcing experimental-arm or interventional design labels. Avoid irrelevant columns where a field cannot
apply; informative absence is stated in words. Mixed-type workbooks must remain readable.

Every listing row has a JSON-pointer address into the record. MCP returns the same source-scoped value, with
bounded paging. Workbook cells must preserve type and value; text beginning with `=` remains text. Values Excel
cannot hold exactly name the reason and their record location rather than being truncated or rounded. Continue
oversized listings on numbered sheets; never drop rows. Read back the workbook before release.

## 4. Retrieval and reproducibility

Preview resolves and fixes the search before studies are fetched. Retrieval accounts for every page and requested
ID, checks counts, duplicates and snapshot consistency, and resumes direct or exact-body relay fetches. A failed
or incomplete retrieval does not become a completed evidence record. Relay verifies shape/counts/identities, not
values against the live service; retain response bodies unchanged.

`verify` replays retained inputs offline under the writing derivation code and checks the record and workbook,
including formatting and links. Missing/changed evidence and incompatible code are named, never repaired by the
verifier. Reproducibility proves derivation from retained sources, not registry truth or clinical correctness.

## 5. Acceptance across study types

Acceptance verifies literal encoding, readable presentation and access to the clinical-development source fields.
It does not require a clinical interpretation, external-source synthesis, or an answer beyond what the registry
states. Existing fixed baselines and inspected failures are regressions, not coverage claims.

Acceptance follows the registry schema and the declared field/display contract, not an arbitrary set of trial
numbers. Exercise each selected field shape, relevant enum and study-type applicability branch, with independent
source expectations and source-preserving perturbations. The record writer must not depend on trial ID,
diagnosis vocabulary or recognized clinical phrases. A source-present value wins over a generic type policy.

Use actual interventional, observational and expanded-access records to check readable population/design context,
including a mixed workbook; retain their source versions and the findings. Synthetic boundary cases establish
specified encoding/display behavior, not clinical interpretation accuracy. An interpretation-accuracy study,
population sampling campaign or comprehensive combination ledger is not a reporting-delivery prerequisite.
State the tested source shapes and any unsupported fields honestly; finite examples do not establish every
clinical situation. Source inspection is for direct value comparison, not fitting clinical readings.

Required checklist:

- [ ] Map complete relevant metadata modules to record fields/consumers or reviewed exclusions, including paths
  outside the original contract. Check observational and access fields, not only oncology/interventional examples.
- [ ] Independently compare exact source → record → displayed workbook → MCP/address values and source scopes,
  including homogeneous-type and mixed-type workbooks. A present selected value lost anywhere fails.
- [ ] Exercise actual/anticipated and child/adult populations, cohort descriptions, one/many groups, posted/partly
  posted/no results, explicit empty/absent/malformed collections, zeros/false/NA, precision and nested denominators.
- [ ] Check identity-preserving reordering/renaming with local references updated, unrelated-study insertion,
  varying cardinality and one-field perturbations. Only affected evidence/presentation changes.
- [ ] Pair intact cases with planted omissions, wrong group/population, false-as-missing, precision/text loss,
  misleading zero/absence, bad labels and broken addresses; accept intact and reject each defect.
- [ ] Visually review sparse/long/mixed-type/many-group workbooks. Publish per-type/combination encoding,
  presentation and access findings, source limits, unexercised cases and unsupported fields separately.
- [ ] Run the relevant local tests, two-sign verification for changed pure decisions, offline verify, release
  installation and fresh-sandbox assistant procedure on the exact candidate. Record performance on frozen inputs.

The colleague's questions guide which evidence is easy to find: population/eligibility, registered treatment
history as prose, outcomes/timing, biomarker/imaging/biopsy text as written, protocol/statistical statements if
registered, observed results, safety and verbatim wording. The report does not determine current care, select
key criteria, interpret biomarker roles, infer grades, set planning targets or authorize language reuse. Those
are layer-two questions. Reporting acceptance asks whether their available source material was preserved and is
readable/retrievable, not whether an interpretation engine can answer them.

## 6. Completion claim

Completion means the declared registry fields and direct derivations are preserved and readable across the
declared source-field contract, with source addresses and reproducibility. It does not establish superior manual
abstraction accuracy, clinical correctness, comparative validity or readiness of the layer-two designer.
