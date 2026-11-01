# landscape.xlsx: the workbook as the clinical readout (add-agent-operation 4.3)

Settled 2026-11-01 from a clinical reader's usability test of twenty lung-cancer trials, the founder's direction
(paraphrased: a serious, professional spreadsheet that professionals read, highlight, edit and share; no web
rendering, no dashboard design), Claude's reading and Codex's independent one, which agreed on the structure;
Codex's additions (the Trial review sheet, the evidence register, the treatments of each test failure) are
adopted.

## The reader and what the test found

The reader is a clinical development professional (MD, MD-PhD, clinical scientist) reviewing registered trials
for a drug program, alone and then with colleagues. They are not a data scientist. The test found: a main sheet
of 50 columns; one trial's information spread over many tabs; no widths, wrapping or filters; exclusions written
under an "Inclusion Criteria" heading; "assessed up to 10 years" not distinguished from a visit schedule;
anticipated efficacy not distinguished from observed; no grade in the safety listing; a sponsor-linked results
publication not shown beside "no results posted"; eligible population not distinguished from enrolled. The
reader wanted, for each trial: what the record says, what that establishes, what remains unresolved.

## Conventions drawn on

The landscape tables clinical development and competitive-intelligence teams circulate (one row per trial, a
fixed set of design columns); clinical data listings (stable identifiers at the left, units and denominators
explicit, every value as recorded, traceable); and ICH E3 reporting conventions (population, efficacy and
safety kept apart, analysis populations named, explanatory notes). The workbook is a registry readout, not a
study report.

## Sheets, in order

Every listing has a header row, a filter, frozen panes through its identifying columns, and a stable row key at
the right.

1. **Read me** — one row per topic: what the workbook is, the search as run, the retrieval date, scope surprises
   (combined phases, unexpected matches), what each status means, how to read a trial's dossier.
2. **Trial index** — one row per trial; the landscape table. Trial ID (linked to the registry); short title;
   phase; status; eligible population; treatment setting and line as registered; investigational treatment;
   comparator; enrollment (actual or anticipated, labelled); primary outcome; its time frame; registry results
   (posted, or not posted); results publication (a registry-tagged results publication, linked, or none);
   last registry update; link to the trial's dossier. Frozen through the short title.
3. **Trial review** — every trial's complete dossier, one block per trial, one row per labelled statement:
   Trial ID; section and item; statement type (**Record says**, **Establishes**, **Unresolved**); statement or
   value; evidence key. Read top to bottom, reached from the index's link or by filtering on Trial ID; never one
   tab per trial. Block order:
   1. identification, registry link, sponsor, phase, status, dates, enrollment and whether it is actual;
   2. eligible population and setting; separately, actual enrollment and posted baseline characteristics;
   3. arms and interventions, with drug classes where read;
   4. inclusion criteria, exclusion criteria, and criteria whose role is unresolved;
   5. primary, secondary and other outcomes, each with its registered time frame;
   6. biomarkers: stated role, population, assay, specimen, threshold and timing where stated;
   7. efficacy: planning assumptions and anticipated thresholds where stated, then, separately, posted observed
      results with their groups, denominators, uncertainty and analyses;
   8. safety: reporting period, denominators, categories, event terms, grades where explicitly reported;
   9. exploratory assessments, with their registry outcome category;
   10. protocol language, publications, protocol and statistical analysis plan links, open questions.
   "Establishes" holds only a bounded reading the record supports, never a clinical conclusion.
4. **Eligibility** — one row per criterion: Trial ID; cohort or arm it applies to; the registry's heading;
   the criterion's role; criterion number; the criterion as written; its typed reading; parameter; operator;
   value; unit; qualification or ambiguity; evidence key. The heading and the role are kept apart, so an
   exclusion written under an inclusion heading shows both, and an uncertain role reads Unresolved.
5. **Outcomes and efficacy** — one row per endpoint definition, planning statement, group result or analysis:
   Trial ID; outcome ID; category (primary, secondary, other); title; entry type (registered endpoint,
   anticipated, observed); group or comparison; analysis population; measure; value or estimate; unit;
   denominator; dispersion or confidence interval; statistical analysis; registry time frame; explicit
   assessment schedule ("Not stated" unless visits are specified); qualification; evidence key.
6. **Biomarkers** — one row per biomarker mention: Trial ID; biomarker; role (eligibility, stratification,
   response, safety, exploratory, or Unresolved); population; assay; specimen; threshold; timing; the words it
   was read from; evidence key.
7. **Safety** — one row per event, group and reported grade: Trial ID; group; event category (serious, other,
   deaths); organ system; event term as written; grade as explicitly reported (else "Not stated"); grade
   source; participants affected; participants at risk; events; collection method; reporting period;
   qualification; evidence key. Seriousness never stands in for grade.
8. **Across-trial findings** — one row per common criterion, mechanism-linked exclusion or trial pair: finding
   ID; type; criterion or design feature; finding; trial IDs; supporting / assessable / total; exceptions and
   unknowns; the rule or matching basis; evidence key. A pair's comparison scope is stated: registry similarity
   is not clinical comparability.
9. **Evidence register** — one row per displayed value: evidence ID; Trial ID; sheet; row key; field; value as
   displayed; status; source kind (registry field or rule); registry field or rule and version; source URL;
   inputs; retrieval date. Last, set apart.

## Status in the cell

A known value reads plainly; "Known" means stated by the record or read by a named rule, not clinically
certified. Every other state is written in words in the cell: "Not stated" (the record says nothing), "Not
posted" (no results or document posted), "Unresolved — <short reason>", "Interpolated — …", "Proposed — …".
Never a blank, zero, dash or "N/A" for these; "Not applicable" only where the registry's definitions establish
it. The evidence key carries provenance per field to the register; nothing depends on cell comments, hover text
or colour.

## Treatments of the test's findings

- A results publication tagged by the registry is shown beside "Registry results: Not posted", labelled as such;
  its existence supplies no efficacy values.
- "Assessed up to N" stays a time frame; an assessment schedule is reported only where visits are stated.
- Anticipated and observed efficacy are separate entry types, never one column.
- Grade only where explicitly reported.
- Eligible population and enrolled population are separate statements.
- Line of therapy is the trial's registered setting, never today's standard of care.

## Formatting and print

Arial 10-11 pt, bold header row, restrained borders, white background, text left and numbers right; no colour
meaning, no decoration, room for the reader's own highlighting. Widths: identifiers 15-18 characters, short
categories 14-22, summaries 35-50, verbatim criteria 65-85; prose wrapped and top-aligned, never truncated (an
oversized passage continues on numbered rows keeping its identity). Dates as 01-Nov-2026, source precision kept
as written; counts as integers with separators; units and comparators as the source writes them; affected,
assessed and event counts never merged. Hyperlinks with descriptive labels; full URLs in the register.
Printing: landscape, header rows repeated, a footer with the search, retrieval date, sheet and page; Trial
review starts each trial on a new page with column widths for a readable printed font; wide listings get a
defined print area, never microscopic scaling. No merged cells, no spacer rows inside tables, no hidden clinical
content, no macros, slicers or formulas: stored values and plain hyperlinks, checked in Excel, Google Sheets and
LibreOffice.

## Scale

At 20 trials and at 500 the index is one row per trial and Trial review one sheet of blocks; a reader filters the
index, then reads or prints the dossiers selected. A listing near a spreadsheet's row limit continues on
numbered sheets of the same schema; no row is dropped.

## Where it can still fail a reader

Registry ambiguity survives formatting (conflicting cohort language yields no dependable summary; the index must
point to the unresolved statement). Untyped criteria still matter (a criterion not read is listed, never
omitted from the dossier). A publication link supplies no findings. Long results make long dossiers. Wrapped
text and links behave differently across applications; a clipped row is a delivery failure. A pair differing in
one represented choice may differ in unrepresented ways.

## Built from, and certified

The workbook is derived from landscape.json alone, every cell from a field of the record; it is written, read
back and refused unless every cell equals its derivation, with deterministic bytes for the same record. The
formatting conventions (widths, wrapping, filters, frozen panes, print setup, dates) also apply to `pull`'s
review.xlsx and record.xlsx.
