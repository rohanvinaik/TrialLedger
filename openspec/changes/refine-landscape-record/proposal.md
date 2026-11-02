# Proposal: the landscape record and workbook hold what a reviewer uses, once

## Why

A real run (2026-11-01: three trials by number, then the 49 phase-3 trials of osimertinib) showed layer one's
output to be a data dump. For three trials the workbook's evidence register held 57,182 rows (one per displayed
cell), the dossier sheet 4,759 (every adverse event under every arm), the safety listing 3,750 (77% zeros);
registered outcomes carried eight columns of "Not applicable"; codes (PHASE1, COUNT_OF_PARTICIPANTS) and
internal slugs stood where clinical words belong; an oncology vocabulary was applied to every trial, so a PTSD
psychotherapy trial's setting read "Unresolved — 9 values remain: neoadjuvant | adjuvant ...". Worse, the
workbook said "Not stated" for values the registry holds (brief title, last update, baseline characteristics,
outcome denominators, analysis populations): the record dropped them in assembly. In the record itself each of
hundreds to thousands of values per study repeated its own source path and registry link. And 95% of a run's
wall time (1,005 s of a 49-trial run, 52 s of computing) was spent asking RxNav one name at a time, many of them
arm labels with doses in them.

The founder's direction (2026-11-01, paraphrased): the record holds the genuinely useful registry content,
encoded correctly, without degeneracy or repetition, built in the same principled way as the rest of the record;
what nobody would use is removed, not kept in case (the API can always be asked again); readings that do not
apply to a trial are solved by universe-scoped rules, after his Regenesis project's universe-specific rule
import; a non-programmer asks an assistant about some trials and gets a clean spreadsheet with all the context
they could need; build it fast and wide.

## What changes

- **landscape.json schema 3.** Registry copies are plain values; each field's API path is stated once, in the
  record's field dictionary. A value object (status, rule, the words read, note) is kept only for a rule's
  reading or a value that is not simply known. The fields a reviewer or designer uses are added (titles,
  design, why stopped, dates, sponsor class and collaborators, countries and sites, officials, DMC, summary
  and detailed description, condition and intervention MeSH, participant flow, baseline characteristics,
  results with their populations, denominators, comments and statistical analyses, adverse-event reporting
  details); copies and internal bookkeeping are removed (exploratory measures, per-criterion frequency tiers,
  per-alias lookup histories, the declared type matrix). Results, baseline, flow and adverse events
  keep the registry's own nesting, each module's groups keyed within the module.
- **Rules scoped to the diseases they are written for** (corrected 2026-11-02, design §9). The record carries
  each trial's disease as the registry states it: the sponsor's conditions and keywords, and the registry's
  condition MeSH terms with their ancestors and browse leaves, as the API gives them. No classifier sorts
  trials into categories. A rule written for one disease (the NSCLC setting and line rules) declares that
  disease and applies by add-scoped-reasoning Decision 4: the trial's indication comes from its conditions
  first, its own disease statements next, the registry's MeSH last; a disagreement is a named conflict, shown;
  what the sources do not resolve reads scope unresolved.
  Recognition of an explicit mention stays universal (founder decision B3).
- **The workbook, rebuilt for the reviewer.** Read me; Trial index (one row per trial in clinical words, with
  each trial's universe and why); Trial review (each trial's dossier, one row per fact, detail left to the
  listings); Eligibility; Registered outcomes; Posted results; Statistical analyses; Baseline; Participant flow;
  Groups; Safety (one row per term, groups as affected / at risk pairs); Biomarkers (mentions only);
  Across-trial findings (only what the evidence can support); Readings (one row per rule reading) and a column
  dictionary.
- **Lookups.** RxNav is asked for distinct drugs from the registry's structured intervention names, identity
  once and classes by RxNorm identifier, negative answers cached, a bounded number of requests at once within
  NLM's published limit (20 per second per address), the results in a fixed order.

## Out of scope

Layer two's use of the record (it recomputes from the raw studies today; citing a landscape digest instead is a
later change), per-cohort scoping inside a mixed basket, and `pull`'s archival workbooks, which keep their
field-by-field contract.
