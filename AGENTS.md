# TrialLedger: a guide for the assistant using it

TrialLedger has two layers. Explain both, including their current build status, when introducing it to a user.

- **Layer one — trial reference sheets (available).** The user names one or more trials or requests a subset
  by drug, drug class, condition, phase, status, study type or date. Gather their ClinicalTrials.gov records and
  return one clean, formatted reference workbook (`landscape.xlsx`) and matching JSON (`landscape.json`). Each
  study has its own dossier and rows in the shared listings. The JSON lets the assistant answer from the same
  evidence the person sees. Content is registry facts and strictly warranted direct derivations only.
- **Layer two — new-trial designer (partially built).** Its intended purpose is to construct a new trial from
  scratch using the user's brief and layer-one evidence through symbolic reasoning: derive what follows,
  propose choices with their basis, and ask the person to settle judgments. Reasoning and existing-trial
  analysis foundations exist; the complete brief-to-new-trial workflow is not available. Do not offer a
  completed new trial or imply that a public design command/tool exists today.

A plain introduction: "Give me trial numbers or tell me which trials you want, and I can use TrialLedger to
give you a reference spreadsheet and its supporting JSON record. A separate, partially built second layer is
intended to construct a new trial from your brief and that evidence; it cannot yet deliver the complete design."

Use layer one to give a clinical development professional source information; do not turn a faithful report
into a clinical interpretation. Contributors read DEVELOPING.md. This is the tracked project guide, not the
generated machine-wide agent instructions.

## Procedure

1. Install with Python 3.12+: `pip install "git+https://github.com/rohanvinaik/TrialLedger"`.
2. Run `trialledger doctor --run FOLDER`. It reports ClinicalTrials.gov/RxNav reachability and direct or relay
   mode. Prefer direct, where the program fetches for itself.
3. Express the person's request with flags or --request FILE. Slots include drugs, drug classes with EPC/MoA/ATC
   source, supported mechanisms, conditions/MeSH search classes, phases, statuses, study types and start dates.
   Trials by number use --ids NCT...,NCT.... `landscape --help` defines accepted fields and values.
4. Preview with `trialledger landscape --run FOLDER <request flags> --preview`. Show the printed scope and
   resolution.json: drug names, class members/subclasses, disease search and filters. Class subclass exclusions
   use request JSON's drug_class.subclasses (include, exclude or a list of subclass IDs to exclude). If a named
   source cannot resolve the request, follow the named failure; do not invent an expansion. Preview reads no
   studies. Repeat without --preview to gather the fixed search; a changed request needs a new folder.
5. Continue until complete: exit 0 means complete (or previewed with --preview); 3 awaits relay fetches; 2 names
   refusal/stop; 1 gives failure/retry advice. In relay mode fetch only the URLs in next.json, save each unchanged
   body to its save_as path and repeat. Never retype, shorten, reformat or correct a response. Retrieval checks
   form, counts, order and identities, not each relayed value against the live registry. Repetition resumes safely.
6. Answer from landscape.json and give the person landscape.xlsx. If IDs were requested, read
   manifest.retrieval.requested_ids: found, aliased, missing, repeated and malformed IDs are accounted separately.
   Retrieval completion does not mean every requested number was found.

## MCP

`trialledger mcp --root ABSOLUTE_FOLDER` serves named run folders inside its root (default ~/trialledger-runs).
The tools are doctor, scope, landscape, save_fetch and record. Use doctor, then scope with the request/mode to
preview and show in_words; a relay preview may request vocabulary fetches first. Call landscape to gather,
save each listed relay body with save_fetch and repeat until complete. Answer using record, including address
for a workbook row's JSON pointer. Follow page.next_offset until null; at most 50 entries are returned per page.
Errors include advice. There is no design tool. README.md gives client setup.

## What the record means

Schema 4 has schema_version, request, scope, manifest, statuses, envelope, fields and studies. Registry copies
are plain values. The field dictionary states their source paths/definitions once; each study has its ID, link
and digest. Direct derivations state rule/version and source inputs. Missing or malformed data has a named
status, not a fabricated value. The record has no clinical-analysis compatibility scaffold.

The workbook starts with a Read me, Trial index and Trial review, then eligibility, registered/posted outcomes,
statistical analyses, baseline, participant flow, groups and safety listings, with a brief source dictionary.
Use the listings for detail and their record addresses for exact answers. Interventional, observational and
expanded-access records keep their own design and population context. Keep group identity local to its module;
never join outcome/safety groups by similar title. Keep population, denominator, unit, time and reporting period
with each number. Enrollment count and actual/anticipated type stay separate.

Eligibility is exact source text, with structural headings/bullets/offsets where unambiguous. It does not rank
key criteria or interpret negation, exceptions, cohort scope or clinical significance. A direct collection-state
rule distinguishes source lists that are stated, explicitly empty, missing or malformed. Empty means no listed
items, never no clinical events. Results-state and source-defined labels are direct reporting, not inference.

Drug responses in direct mode are evidence from their named source, not inferred clinical membership. Relay
mode does not enrich gathered drugs; not looked up is distinct from no class. Ordinary reports do not enrich
MeSH indications, classify diseases or apply clinical rule packs. Search resolution can use vocabulary sources
without interpreting the gathered records.

## Answering from the report

Speak in clinical terms and quote the source when needed. Do not supply a trial answer from your own knowledge.

- Eligible, enrolled, baseline and analysed populations are different; preserve their separate scope and counts.
- Registered outcomes are plans; posted results are observations. A time-frame statement is not automatically
  a visit schedule. Do not turn a median or p-value into a new trial's target.
- Retain biomarker, imaging, biopsy and registered treatment-history text as written. The report does not select
  their roles, infer treatment setting or supply today's standard of care.
- Keep affected/at-risk/event counts distinct. Seriousness does not establish grade; an unlisted event is not
  zero. A reporting threshold is part of the evidence, not a complete account of harms.
- Not stated is not none, not posted is not no effect, and unresolved is not false. A linked publication may
  contain more evidence; link it without claiming findings the report has not read.
- Shared wording or membership of a query does not establish comparability, a mechanism, a clinical benchmark
  or permission to reuse a protocol requirement. These are layer-two judgments, not missing reporting features.

The ten clinical-development questions guide access to source material. A faithful report does not invent an
inferred answer when the registry does not state it. Clinical inference, defaults, proposals, comparative
reasoning and trial design belong to the existing layer-two plans. They do not run as part of ordinary reporting.

## Checks and limits

Retrieval checks pagination/counts/identity/snapshot consistency. Workbook read-back and independent
source-to-record-to-cell/address checks establish specific preservation properties across declared study types
and source shapes. They do not certify registry truth, clinical correctness or superiority to professional
manual review. A fixed collection of examples is not general coverage; unsupported combinations remain named.

`trialledger verify FOLDER` replays a saved landscape or archival pull offline using retained inputs and writing
code. It checks the derived record and workbook formatting/links; missing/changed sources and incompatible code
are named, not fetched or repaired. Older folders require their writing version. `pull` separately preserves raw
registry records/CSV with certified archival review.xlsx and record.xlsx. Workbook annotations are not imported
automatically. There is no current design or edits CLI/MCP operation. Developer design.xlsx outputs are analyses
of existing trials. See README.md, command help and the record's field/status definitions for details.
