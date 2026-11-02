# Developing TrialLedger

Read this when changing the project; AGENTS.md is the usage guide. The founding requirements are retained in
docs/conversations/2026-10-31-the-case.md; the first reporting plan is the archived add-review-workbook change.
Read docs/THEORY_OF_THE_CASE.md before proposing architecture. Do not change that theory to match an
implementation shortcut. TrialLedger is classical AI; no language model processes trial content or supplies facts.

## The layer boundary

Layer one is a small, auditable reporting operation: source → record → readable workbook/MCP. Its content is
registry facts and strictly warranted direct derivations. Exact structural segmentation, source-presence and
results states, labels, counts, links and direct source-backed RxNav responses are appropriate. Clinical inference,
defaults, proposals, rankings, comparability and trial design belong to layer two.

The schema-4 report has schema_version, request, scope, manifest, statuses, envelope, fields and studies.
`landscape_record(studies, request, scope, manifest, answers=None)` accepts raw source studies, not a clinical
analysis view. The ordinary reporting path must not call read_population, coherence, universes, indications or
the assertion compiler, including shadow output. Do not replace those calls with another interpretation path.
There is no compatibility scaffold, key-criterion ranking, biomarker recognition, inferred setting, cohort finding
or ordinary-report MeSH enrichment. Source text remains intact and available without recognition.

Search resolution and retained direct RxNav answers remain sourced operations. A service response is attributed
as returned; it does not authorize an inferred class/indication or default. Failed/not-looked-up/negative answers
remain distinct. Ordinary registry reports link publications and documents; they do not interpret them.

## Reporting code and contracts

- `operate.py`, `preview.py` and `steps.py`: fixed preview, resumable direct/relay retrieval, complete accounting
  and delivery. Incomplete or failed retrieval must not look complete.
- `contract.py`: selected field paths, types, labels, source-bound applicability and consumers; brief dictionaries
  and presentation policy. Include relevant observational/access fields rather than adopting interventional defaults.
- `landscape.py`: direct field assembly, lossless eligibility segmentation, named results/source collection states,
  links and sourced evidence. Every direct derivation has exact inputs and a rule/version.
- `readout.py`: workbook projection of that same record, exact value/type and scope preservation, readable source
  labels and row addresses. It must not decide clinical significance or hide an atypical source-present value.
- `mcp_server.py`: preview/gather/save/read interface, bounded paging and address access to the same evidence.
- `landscape_verify.py` and `landscape_warrants.py`: retained-input replay and derivation identity. Keep their
  source/code roots limited to what reporting actually consumes; do not pull clinical-analysis dependencies back in.
- `ingest.py`, `ledger.py`, `record.py`, `workbook.py`, `checks.py` and `warrants.py`: archival pull, source ledger,
  approved direct consistency checks and certified archival workbooks. Preserve their distinct contract.

Groups are local to each source module. Preserve population and denominator nesting, units, periods, precision,
zeros, false and NA/comments. Missing and malformed collections are not empty lists; an explicit empty event list
is not zero harms. Eligibility segmentation preserves literal text/order/bullets/offsets and reconstructs the
original; ambiguous headings leave source passages unsectioned. Headings are labels, not inferred polarity or cohort authority.

## Acceptance and engineering

`refine-landscape-record` contains the reporting tasks and checklist. Test source → record → workbook → MCP,
independently of producer selection/rendering code. Cover INTERVENTIONAL, OBSERVATIONAL and EXPANDED_ACCESS with
applicable design/population/results states and therapeutic/intervention breadth. Inventory the relevant metadata
complement, including fields missing from the original table. Source-present optional/historical fields remain
visible; unsupported/unexercised valid reporting combinations remain unmet.

Acceptance is schema-derived: test relevant field/enum/type branches, structural identity/order/cardinality
changes and intact/seeded defects, with independent source expectations. Visually review actual long/sparse and
mixed-type workbooks. The writer has no trial-ID or clinical-phrase decisions to fit. Keep source versions and
findings, and state unsupported fields; do not require a clinical-interpretation sampling campaign to deliver
this direct record writer. Reporting acceptance requires faithful access to evidence, not inferred answers to
the ten-question clinical wishlist.

Trace production consumers and duplicate paths before changing behavior. Keep decisions pure with named outcomes;
write positive and negative intent tests, verify the actual entry point and null/empty/malformed boundaries, and
converge changed pure decisions using Detective by its current protocol, one target at a time. Do not mark a
changed function pinned from an old measurement. Temporary helpers use SquishOS owned-run. Work on main with
no worktrees or feature branches. Do not commit without authorization.

Run scripts/ci_local.sh and read its complete output for the relevant local gate; the pre-push hook uses
scripts/push_checks.py. Read those files before altering their behavior. Detective/Wesker use the founder's local
checkouts, per SquishOS instructions. Run the final deep gate only when the candidate and proof basis are stable,
not concurrently with source/test edits. Live calls are opt-in. Report actual checks and unresolved failures;
never turn a past count into a current result.

A semantic-conformance inventory, clinical compiler, expanded vocabulary, external-source parser or new design
framework is not a layer-one completion gate. Simplicity and auditability are requirements. Verification shows
reproduction from saved sources, not that a clinical interpretation is correct.

## Layer two

Layer two is the partially built new-trial designer: its purpose is to construct a new trial from scratch
from a user brief and layer-one evidence through symbolic reasoning. Reasoning and existing-trial analysis
foundations exist; the integrated brief-to-new-trial workflow is unfinished. Keep that distinction explicit
in agent-facing descriptions rather than describing layer two only as a list of reporting exclusions.

The existing coherence, reasoning/assertion, bank, surprise, targeted-question, evidence-source and synthesis
changes retain their own designs. They are separate work and may consume the reporting evidence when their
interfaces are built. This reporting cleanup neither redesigns them nor claims completion. Developer resolve/
profile outputs, including design.xlsx, are analysis tools, not ordinary reports or synthesized new protocols.
There is no current public design/edits operation or automatic workbook-edit import. Keep documents as built;
future behavior belongs in the corresponding existing change.
