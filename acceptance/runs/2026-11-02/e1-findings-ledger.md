# Unit E1 findings ledger, 2026-11-02

The independent checks (`acceptance/preserve.py`, `acceptance/reviewer.py`) on the 3-trial request at three
stages:

- **before**: `e1-before-tl_int3.txt`, `/tmp/tl_int3` at the integration head before unit C's contract
  display section (also kept at `~/tools/TrialLedger-runs/acceptance-2026-11-02/`);
- **C's head**: `e1-after-tl_int3b.txt`, `/tmp/tl_int3b`, written at 5b99c58 (unit A's record, recurring
  criteria, unit C's workbook under the contract's display data);
- **final**: `e1-final-tl_final3.txt`, `/tmp/tl_final3`, a fresh direct run at 2272e3f (units A, B, C, D and F
  together): `trialledger landscape --run /tmp/tl_final3 --ids NCT04852770,NCT01827384,NCT01086644 --mode
  direct`, exit 0, bodies kept (NCT01086644 is an alias of NCT01030536, accounted for).

The checks read only the contract's declared display policy (STATUS_WORDS, REASON_FORM, BASIS_WORDS,
WHICH_LIST_WORDS, READING_CODE_WORDS, DATE_FORMS, NUMBER_FORMATS, EMPTY_LISTING_WORDS, INDEX_COMPACT,
BLANK_BY_CONSTRUCTION, DENOMINATOR, and the universe table) and nothing of `readout.py`; locating source and
record values, joining groups and denominators at scope, row coverage, and the numeric comparison are their
own. (`e1-after-tl_int3.txt` is the old folder's workbook against today's contract, superseded by the two runs
above and kept only as evidence.)

Registry → record, complete mode, every plain field of the 3 bodies: 0 findings at every stage.

## Record → cell, by finding class

Dispositions: a workbook or record defect, fixed (the commit); a reviewed display-policy change (the contract
change, the example, the negative test); missing or contradictory source evidence, shown unresolved; a
deferred software defect, excluded from the completion claim.

| Finding class (before) | Before | C's head | Final | Disposition |
|---|---|---|---|---|
| Posted results Group shows the title without the group's ID | 319 | 0 | 0 | Workbook defect, fixed (b810200): each Group cell links to its Groups row, which shows the ID. Negative test: a link to another group is `wrong_link` |
| Groups has no posted-outcome group rows | 136 | 0 | 0 | Workbook defect, fixed (b810200) with a display-policy change (contract Groups row: a posted-outcome group once per trial per title and description, with an Outcome measures column). Checked by group identity; negative test: a description that differs from the record |
| Denominator shows the count without "Participants" | 712 | 0 | 0 | Display-policy change (contract `DENOMINATOR`). Negative test: a denominator changed to eyes, its cell still the bare count |
| Untitled class or category cells blank | 830 | 0 | 0 | Display-policy change (`BLANK_BY_CONSTRUCTION`, untitled class or category; the example record no longer writes a not-stated title). Negative test: such a cell holding "Not stated" is `not_blank` |
| Recurring criteria: a group not assessed leaves its cells blank | 15 | 0 | 0 | Display-policy change (`BLANK_BY_CONSTRUCTION`, a group not assessed). Negative test: values there are `not_blank` |
| Open questions written as the record's JSON, Basis "Registry" | 6 | 0 | 0 | Workbook defect, fixed (5b99c58) |
| Eligibility Role "Not settled: ..." for an unresolved role | 1 | 0 | 0 | Workbook defect, fixed (contract `STATUS_WORDS`: anything unresolved reads "Unresolved", its reason by `REASON_FORM`) |
| Baseline and Participant flow Group show the title without the group's ID | 573 | 573 | 573 | **Open.** The contract's Group columns name the group ID; these cells give the title alone and no link. A workbook defect for unit C (link each to its Groups row, as Posted results does) or a display-policy change (the contract declaring the title enough where it is unique within its module): excluded from the completion claim until one is decided |

Found and resolved in the checker during the final run: the Trial index's "Prior lines for advanced disease"
for NCT01030536 reads "Unresolved" where the record holds no coordinate. The checker had read every absent
coordinate as "Not applicable"; INDEX_COMPACT says "Not applicable outside the universe; else Unresolved", and
the haematologic universe owns the prior-lines pack (its applicability unresolved in the record, unit B). A
checker defect, fixed (the universe table decides; negative test both ways).

New classes held since this round, none found at C's head or in the final run: `format_differs`, `wrong_link`,
`raw_record`, `fact_missing`, the empty listing's words, the Trial review's Basis words, `wrong_words` for any
status.

## The reviewer's tasks

| Task | Final (`/tmp/tl_final3`) | Disposition of what stays unresolved |
|---|---|---|
| Eligibility across trials | 86 criteria; 20 with no reading; every key criterion its criterion's text and role | Missing source evidence, shown unresolved ("No reading produced", checked in the Eligibility sheet) |
| Eligible vs enrolled | 38 items; NCT04852770 posted no baseline | Missing source evidence (not posted), shown unresolved |
| A result's population and denominator | 343 items; NCT04852770 posted no results | Missing source evidence (not posted), shown unresolved |
| Safety within its period | 23 items; NCT04852770 posted no adverse events | Missing source evidence (not posted), shown unresolved |
| Readings to their warrants | 356 warranted, 6 unresolved, 0 findings | Below |
| A row's address in the record tool | 200 workbook rows asked of `trialledger mcp`'s record tool through the protocol; every answer the record's value | None (the bound is the task's declared 200 rows) |

## The 89 unresolved reading cases, by warrant

Last round's 89 were readings citing no words, lumped as "names no words". Each is now checked by the kind of
warrant its field rests on. "Traced" (quotation) means only that the cited words occur, exactly, in the
registry text the field reads; it never means the clinical interpretation of those words is right.

| Case (before) | Before | Warrant | Check | C's head | Final |
|---|---|---|---|---|---|
| A criterion's role, no words cited | 68 | Structural (its heading) | The role equals the heading | 68 warranted | 72 warranted |
| Results posted | 3 | Structural (the registry's hasResults flag) | Known where true, not posted where false | 3 warranted | 3 warranted |
| Open questions | 7 | Derivation (an unresolved reading it names) | Its element is an intervention name of the trial | 7 warranted | 7 warranted |
| A coordinate's interpolated level | 4 | Derivation (default relations over the known level) | Every value it leaves the known level leaves | 4 warranted | 3 warranted |
| A coordinate's known level | 4 | Derivation (typed readings) | Its cited words in the eligibility text; none, unnarrowed | 4 unresolved | 3 unresolved |
| No biomarker mention | 3 | None (no reading exists) | The Biomarkers sheet's empty line in the contract's words | 3 unresolved | 3 unresolved |

The unresolved coordinates are missing source evidence (no typed reading bears on them), shown "Unresolved" in
the index and dossier; the absent biomarker mentions are shown in the contract's empty-line words. At the final
head unit B's applicability rule removed the haematologic trial's prior-lines coordinate (one known and one
interpolated level fewer; its applicability reads unresolved in the universe reading), and its role fixes
moved four roles from their own words to their heading (14 roles now cite their own words against the
heading, each word checked in the criterion's text). Quotation readings traced in the final run: criteria
readings 100, endpoint and time-point readings 132, drug class and axes 22, universe 3.

## Conformance

Final (`/tmp/tl_final3`, 2272e3f with these checks): registry → record 0; record → cell 573, all of the one
open class above; reviewer findings 0; the record tool answers every address asked. Unexplained conformance
failures: 0 (the open class is named and excluded from the completion claim).
