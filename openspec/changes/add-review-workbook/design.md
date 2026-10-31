# Design — add-review-workbook

## Context

The ingestion layer is built (commit `ac9c8b6`): `trialledger pull` writes the complete registry records
(`studies.json`) and the registry's own spreadsheet (`studies.csv`), all or nothing. The design this change
begins is `docs/THEORY_OF_THE_CASE.md`. The founder's decisions for it, verbatim in
`docs/conversations/2026-10-31-the-case.md`: «Fact sources should be the unambiguous fields from the API we
just set up»; «Raw publications should be linked and surfaced [...] but we don't need to THOROUGHLY build a
literal parser just yet»; «"Significant" should be pretty self-evident»; «yes the spreadsheet should carry
eligibility and safety».

## Goals / Non-Goals

**Goals:** a ledger of every record element with location and role; approved edit checks with named
outcomes; a review workbook answering the ten design questions, every value labelled stated, computed or
needs review, every source linked.

**Non-goals:** reading publications; computing anything across trials; interpreting free text; any model.

## Decisions

1. **Sources.** Values come from the record's structured fields. Free text (eligibility, descriptions) is
   carried verbatim and never turned into structured values. Publications and documents are linked.
2. **The ledger is derived from the record being written**, the same content as `studies.json`, so the
   workbook is a pure function of the saved record and reproducible from it. Roles come from the record's
   structure only (which section an outcome is listed in, which group a count belongs to, the type the
   registry gives a reference).
3. **Edit checks are an approved, versioned list**, each a pure decision returning `consistent`,
   `conflict` or `not_checkable`, each with its justification. Proposed first list, every entry subject to
   task 1.1: completed status with an estimated completion date; withdrawn status with a nonzero actual
   enrollment; an observational study carrying an interventional phase; the results flag against the
   presence of a results section; an arm naming an intervention the study does not declare; an
   intervention naming an arm the study does not define; an adverse event affecting more participants than
   at risk; an event count naming a group the results do not define; minimum age above maximum age; start,
   primary completion and completion dates out of order. A relation without a stated registry rule is not
   approved.
4. **Eligibility is split only on the registry's standard headings**, each present exactly once and in
   order; otherwise the whole text is shown and marked not split. Splitting is a pure decision with named
   codes (`split`, `not_split_missing`, `not_split_repeated`, `not_split_order`); the two parts must
   reproduce the original text exactly. Abstaining is the safe direction.
5. **Every cell carries its kind**: stated, computed (with rule and inputs) or needs review (with sources).
   A study whose results flag is false reads "no results posted" in its results and safety items.
6. **Workbook format: one `.xlsx` file, `review.xlsx`**, with tabs for studies, eligibility, outcomes,
   adverse events, sources and checks, because a reviewer outside a terminal opens one file, the data has
   several tables per study, and the format carries no encoding ambiguity. It needs one new runtime
   dependency, a pure-Python spreadsheet writer (`openpyxl`), recorded in the manifest and lock. A folder
   of CSVs was considered and rejected for the reader this serves.
7. **Significance, in this change, is the ten questions.** Significance across trials, what distinguishes
   them versus what they all share, belongs to `add-cross-trial-views`.
8. **Construction follows Detective's own workflow.** Each decision is written unwired as a pure function
   returning named codes; given direct-call intent tests for both signs (what must happen, what must never
   happen); converged with `detective converge --two-sign` in isolation, with every survivor killed by a
   test, proven equivalent with a note, or fenced; and only then wired in. The file-writing shell gets
   durability tests. The real entry point is verified end to end, then live.

## Sequence after this change

1. `add-publication-evidence`, from the founder's addition «We can impute this from papers/results, no?
   Might be worth adding that in then»: for studies without posted results, follow the publications the
   registry types as results; enter figures the paper states explicitly as publication evidence, each with
   its exact sentence, labelled as from the paper; show any disagreement with the registry; leave the rest
   as review items. Deterministic first; no model unless the founder places one. 13.3% of registered
   studies had posted results on 2026-10-31 (80,808 of 609,551).
2. `add-cross-trial-views`: comparator bars on matched endpoints and time points, cohorts, niches, and
   mechanism-linked exclusions proposed as candidates for review.
3. An interface that needs no terminal.

## Risks / Trade-offs

- Some proposed checks may not correspond to a registry rule; task 1.1 keeps only those that do.
- The URL form of posted documents is unverified; task 1.2 verifies it live before any link is built.
- Eligibility text that does not use the standard headings is shown whole: correct, less convenient.
- A large pull makes a large workbook; the format's row limit (1,048,576 per tab) is far above the
  registry's total study count.
