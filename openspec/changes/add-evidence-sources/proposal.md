# Proposal: typed evidence from terminology, measurement, labelling and publication sources

## Why

The registry cannot answer several things the founder's report must hold for each study (refine-landscape-record
design §4a): a trial's place on today's standard-of-care ladder; biomarkers' and assessments' schedules, assays
and specimens; the protocol's own efficacy success criterion; adverse-event grades; exploratory imaging and
biopsies. They live in publications, product labels and maintained terminologies. A review on 2026-11-01 of the
NIH API catalog proposed a small set of such sources, each supplying typed evidence to the existing ledger, read
by fixed rules, never by a model; the person still receives one study-by-study report and its record.

## What changes (in order)

1. **Terminology and measurement.** MeSH (RDF: entry terms, definitions, pharmacological actions, descendants)
   and the NCI Thesaurus (clinical-research concepts and typed relationships) as versioned rule material: which
   disease concept a phrase names, whether it is a subtype of the indication, whether a term names a disease, a
   procedure, a substance or a measurement; each mapping kept as equivalent, broader, narrower or associated.
   UCUM for unit validation and conversion, a laboratory threshold kept as analyte, specimen, method, comparator,
   quantity, unit and reference basis (an absolute value apart from a multiple of the upper limit of normal).
   UMLS optional (it needs an account).
2. **Labels and publications.** DailyMed's structured labels bound to the resolved product (indication,
   population, dose, warnings, adverse-reaction tables with their own population and ascertainment), the
   version applicable to a historical comparison kept apart from the current one. PubMed and PubMed Central
   (full-text XML where permitted): an unresolved field becomes a typed evidence request, deterministic parsers
   seek its statements in the relevant sections and tables, and a publication citing an NCT number stays a
   candidate until its link to the study, cohort and analysis is established.
3. **Treatment context and benchmarks.** Dated treatment context from labels and NCI PDQ summaries, encoded as
   what each states (a treatment option discussed for a setting), never as a guideline. Three objects kept apart:
   the success criterion a protocol states; observed results from comparably defined studies; a planning target
   under a named decision rule. Adverse-event grades read under CTCAE by version, a grade only where a study
   reports one.

CDE and CDISC terminology and the NIH protocol templates (template language kept apart from language recurring
across trials) develop alongside.

Before any source is asked for a field, the field is assessed against the retained registry prose (descriptions,
outcome descriptions, criteria): content a rule does not yet read is bank coverage or scoped-assertion work
(add-bank-coverage, add-scoped-assertions), not missing evidence.

## How

Source adapters return the source, its release or document version, the retrieval time, the response and its
digest, and a named outcome (resolved, ambiguous, not found, unavailable, out of scope); lookups cached by concept
and version. Narrow resolvers (disease, drug, measurement, biomarker, document identity) produce typed
assertions (subject, relation, object, modality, cohort or arm, time, applicability, evidence): a biomarker
mentioned, required for enrollment and measured after treatment are different assertions. Assessment and
treatment-context objects give the join conditions; versioned, scoped relations (strict, default, proposal, as
add-scoped-reasoning keeps them) apply to them; contradictions stay visible. The evidence is projected into the
existing record and workbook beside the field it explains, with its source and date.

## Out of scope

NCI's Clinical Trials Search API as a required source (its documented coverage is restricted and excludes
biomarker data). Any language model reading a source.

Design and tasks follow when refine-landscape-record has landed.
