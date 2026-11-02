# Unit E1 findings ledger, 2026-11-02

The independent checks (`acceptance/preserve.py`, `acceptance/reviewer.py`) run on the 3-trial folder twice:

- before: `e1-before-tl_int3.txt`, run on `/tmp/tl_int3` at the integration head before unit C's contract
  DISPLAY section (also kept at `~/tools/TrialLedger-runs/acceptance-2026-11-02/`);
- after: `e1-after-tl_int3b.txt`, run on `/tmp/tl_int3b`, the run written at 5b99c58 (unit A's record,
  recurring criteria, and unit C's workbook under the contract's display data), with the checks reading only
  the contract's declared policy (STATUS_WORDS, REASON_FORM, BASIS_WORDS, WHICH_LIST_WORDS,
  READING_CODE_WORDS, DATE_FORMS, NUMBER_FORMATS, EMPTY_LISTING_WORDS, INDEX_COMPACT, BLANK_BY_CONSTRUCTION,
  DENOMINATOR) and nothing of `readout.py`. `e1-after-tl_int3.txt` is the old folder's workbook (written before
  the display section) against today's contract: it is superseded by `/tmp/tl_int3b` and kept only as evidence.

Registry → record: 0 findings, before and after (complete mode, every plain field of the 3 bodies).

## Record → cell, by finding class

Each class has one disposition: a workbook or record defect, fixed (the fixing commit); a reviewed display-policy
change (the contract change, the example, the negative test); missing or contradictory source evidence, shown
unresolved; or a deferred software defect, excluded from the completion claim.

| Finding class (before) | Before | After | Disposition |
|---|---|---|---|
| Posted results Group shows the title without the group's ID | 319 | 0 | Workbook defect, fixed (b810200): each Group cell links to its Groups row, which shows the ID. Negative test: a link to another group is `wrong_link` |
| Groups has no posted-outcome group rows | 136 | 0 | Workbook defect, fixed (b810200) with a display-policy change (contract Groups row: a posted-outcome group once per trial per title and description, with an Outcome measures column). Checked by group identity (trial, title, description); negative test: a description that differs from the record |
| Posted results and Baseline Denominator show the count without "Participants" | 712 | 0 | Display-policy change (contract `DENOMINATOR`: participants unless otherwise specified; another unit written with its count). Negative test: a denominator changed to eyes, its cell still the bare count |
| Untitled class or category cells blank | 830 | 0 | Display-policy change (contract `BLANK_BY_CONSTRUCTION`: a measurement of an untitled class or category); the example record no longer writes a not-stated title. Negative test: such a cell holding "Not stated" is `not_blank` |
| Recurring criteria: a group not assessed leaves Role, counts, examples blank | 15 | 0 | Display-policy change (`BLANK_BY_CONSTRUCTION`, a group not assessed). Negative test: values in those cells are `not_blank` |
| Open questions written as the record's JSON, Basis "Registry" | 6 | 0 | Workbook defect, fixed (5b99c58: open questions in words, never the record's JSON) |
| Eligibility Role "Not settled: ..." for an unresolved role | 1 | 0 | Workbook defect, fixed (contract `STATUS_WORDS`: anything unresolved reads "Unresolved", with its reason in `REASON_FORM`) |
| Baseline and Participant flow Group show the title without the group's ID | 573 | 573 | **Open.** The contract's Group columns name the group ID; these cells give the title alone and no link. Either a workbook defect for unit C (link each to its Groups row, as Posted results does) or a display-policy change (the contract declaring the title sufficient where it is unique within its module); excluded from the completion claim until one is decided |

New classes the checks hold since this round, none found in `/tmp/tl_int3b`: `format_differs` (a count not
in General, a registry decimal not in the format of its own decimal places), `wrong_link`, `raw_record`,
`fact_missing`, the empty listing's words (`EMPTY_LISTING_WORDS`), the Trial review's Basis words
(`BASIS_WORDS`). The old folder's workbook fails several of them (`e1-after-tl_int3.txt`: counts in format 0,
the old Denominator header, no Recurring criteria sheet): superseded by `/tmp/tl_int3b`.

## The reviewer's tasks

| Task | After (`/tmp/tl_int3b`) | Disposition of what stays unresolved |
|---|---|---|
| Eligibility across trials | 86 criteria; 20 with no reading; every key criterion is its criterion's text and role | The 20: missing source evidence, shown unresolved ("No reading produced", checked in the Eligibility sheet) |
| Eligible vs enrolled | 38 items; NCT04852770 posted no baseline | Missing source evidence (not posted), shown unresolved |
| A result's population and denominator | 343 items; NCT04852770 posted no results | Missing source evidence (not posted), shown unresolved |
| Safety within its period | 23 items; NCT04852770 posted no adverse events | Missing source evidence (not posted), shown unresolved |
| Readings to their warrants | 357 warranted, 7 unresolved, 0 findings | See below |
| A row's address in the record tool | stand-in tool passes; the real tool expected to fail | Deferred until unit F 6.2 lands (the strict expected failure flips then) |

## The 89 unresolved reading cases, by warrant

Last round's 89 were readings citing no words, all lumped as "names no words". Each is now checked by the kind
of warrant its field rests on. "Traced" (quotation) means only that the cited words occur, exactly, in the
registry text the field reads; it never means the clinical interpretation of those words is right.

| Case (before) | Count | Warrant | Check | After |
|---|---|---|---|---|
| A criterion's role, no words cited | 68 | Structural (its heading) | The role equals the criterion's heading | 68 warranted (`heading`) |
| Results posted | 3 | Structural (the registry's hasResults flag) | Known where hasResults is true, not posted where it is false | 3 warranted (`flag_agrees`) |
| Open questions | 7 | Derivation (an unresolved reading it names) | The question's element is an intervention name of the trial | 7 warranted (`derived`) |
| A coordinate's interpolated level | 4 | Derivation (default relations over the known level) | Every value it leaves is one the known level leaves | 4 warranted (`narrows`) |
| A coordinate's known level | 4 | Derivation (typed readings) | Its cited words in the eligibility text; none cited, it is unnarrowed | 4 unresolved (`unnarrowed`): missing source evidence (no typed reading bears on it), shown Unresolved |
| No biomarker mention | 3 | None (no reading exists) | The Biomarkers sheet's empty line, in the contract's words | 3 unresolved: missing source evidence, shown in the contract's empty-line words |

Besides these, 18 roles cite their own words against the heading ("ineligible", "not eligible", "are
permitted"): each word is checked in the criterion's text (structural, `own_words`). The quotation readings
(criteria readings 100, endpoint and time-point readings 132, drug class and axes 22, universe 3) are traced.

## Conformance

`/tmp/tl_int3b`: registry → record 0; record → cell 573, all of the one open class above; every other class is
fixed or a declared policy with its negative test. Unexplained conformance failures: 0 (the open class is
named and excluded from the completion claim). To re-run after unit B's applicability and role fixes: the
same checks, `preserve.check_run(bodies, landscape.json, landscape.xlsx)` and `reviewer.review(load_run(folder,
bodies))`, over the final branch's run folder, its bodies read with `preserve.bodies_in`.
