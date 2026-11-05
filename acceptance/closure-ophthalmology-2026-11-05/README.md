# Loading and responder maintenance: a cold clinical handoff

A simulated sponsor asks whether a retinal trial can keep initial entry and loading independent from
responder-only maintenance, preserve a source-inspired proposal as a proposal, and repair collection
without changing unrelated answers. All new-trial choices are explicitly simulated; no clinician
confirmation or medical suitability is asserted.

## Sources and selection

A fresh public pull searched Macular Degeneration, Phase 3, Completed, starting from 2020-01-01. Its
complete class pool contained 22 studies. Seed 20261105 was recorded before reading clinical records;
sampling the sorted pool selected NCT04480463 and NCT07214740 without exclusions. The default comparison
found another 15 condition-text-only candidates; the explicit 37-ID union was not executed. Public CLI
and initialized MCP coverage reads agreed. The candidates were never asserted to be class members.

The first trial is a randomized wet-AMD biosimilar study: its registry reports minimum age 50 years and
BCVA change from baseline to Week 8, described using ETDRS letters or 2702 charts. The second is a
single-arm geographic-atrophy prefilled-syringe safety study, with safety through Day 30 and successful
injection at Day 1. The awkward pairing stays visible; no shared population, endpoint or chart equivalence
is inferred. Complete eligibility, design and outcome units were read beside identity and description.

## What the declared design resolves

| Question | Computed answer and warrant |
|---|---|
| Does age 49 fit initial entry under the simulated minimum of 50? | REFUTED by the entry-age premise. Age 50 is allowed, not required. This is not complete eligibility. |
| Does loading OCT line up? | Nominal day 28 and permitted/collected days [25,31] agree under known adopted objects. |
| Does maintenance OCT line up? | Only if `loading_response_confirmed`. Collection ending at day 53 misses nominal day 56 and leaves gap (53,63] in permitted days [49,63]. |
| Can the Week-8 registry outcome supply a maintenance plan? | It supplies an attributed proposed reading. The maintenance anchor and weeks [7,9] are invented proposals; raw satisfied arithmetic remains unapplied. |
| What changes when collection extends through day 63? | Only the maintenance nominal/full-window outcomes change. A new version and simulated adoption are recorded. Entry, loading and the proposed vision plan stay unchanged. |

Initial-randomized/loading and responders-rerandomized/maintenance are explicit separate contexts. Days
and weeks, initial and maintenance randomization, source wording and new-trial choices remain separate.
No entry premise establishes a later response event.

The first export exposed two delivery gaps: its generic conditional wording hid the actual responder
condition, and repeated tasks obscured the remedies. The re-walk verified their repair. Check summaries,
readable paragraphs and the assessment sheet name the typed condition. Passing conditional claims share
one delivery task; the original ten canonical per-claim rows remain retained beside five delivered tasks.
Where distinct claims have identical task wording, the final list names their check and claim.

## Public lifecycle and retained evidence

The walker used public discovery, short preparation, retained-ID execution, bounded reads, revision and
export through both CLI and initialized MCP. Its 21 artifact assertions passed; these are not formal
proofs or universal clinical validation. The coordinator then freshly replayed the same initial artifact
and explicit revision through the final CLI and exported again, adding exact condition references and
disambiguated task labels. No source was edited to fit the draft.

- `artifact.json` is the complete final canonical request/response, including both replay snapshots.
  Its SHA-256 is `536554bd7b0743ad311d22699199599cb063cbe0ad7acc2f5056cdbc52f9294d`.
  The `request` object is the complete public reasoning input, not a shortened transcript.
- `decision-list.md` is the coordinator's final readable export.
- `sampling.json`, `scoped-receipt.json` and `scoped-verification.json` retain the walker's pool, earlier
  public-transport identities, exact file fingerprints and measured checks. Those receipts name the earlier
  scoped artifact; `final-receipt.json` identifies the coordinator's final replay and export separately.
- Full raw acquisition and source workbooks remain at
  `/Users/rohanvinaik/trialledger-runs/closure-ophthalmology-20261105/`.
  Final exported workbook and manifest remain at
  `/Users/rohanvinaik/trialledger-runs/closure-audit-20261105/final-clinical-export/review/`.

These complete reasoning inputs support layer-two replay under their writing rules. Layer-one workbook
verification additionally needs the retained full report/source packet. Initial verification passed; a
later verify refused `wrong_code` after concurrent source edits. That is a writing-version limitation,
not proof that registry values changed. A new pull would be a new observation, not recovery of old bytes.
No full raw response or workbook is duplicated in this acceptance folder.

## What this did not test

No numerical responder definition, loading regimen, rescue/hold policy, observed patient data, estimand
completeness, efficacy calculation or whole protocol was supplied. No safety or clinical-validity claim
follows. Corpus, source assertions, design bounds and negative witnesses were not exercised. Workbook
values and links were inspected; native Excel/visual rendering was not tested. The separate test and
proof receipt records engineering evidence without promoting the simulated clinical choices.
