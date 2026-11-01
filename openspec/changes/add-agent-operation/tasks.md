# Tasks — add-agent-operation

The founder, 2026-11-01: the next priority, built to completion.

## 0. Feasibility probe (first)

- [ ] 0.1 In each vendor's app, the agent fetches four real URLs into its sandbox (the registry's version, an ID
      page of 1,000, one full study record, an RxClass classMembers answer) and reports, per URL, whether it
      arrived, its size, whether it parses whole as JSON; and whether its Python reaches them directly. The relay
      mode's page sizes and the entry point's instructions are set from what arrives; a vendor whose agent can
      neither fetch nor reach them is named unsupported in the entry point, never worked around. Also, per
      vendor, whether the agent can fetch the repository itself from GitHub (ChatGPT's code container is
      reported to reach package registries through a proxy but not other hosts); if it cannot, publishing the
      package to PyPI is the founder's decision.

## 1. The record contract

- [x] 1.1 `landscape.json` schema v1: request, scope, manifest, per-study ten-point extract and extras, cohort
      profile, review queue, coverage; each value with status, source and link; the `fields` self-description
- [x] 1.2 The per-study extract from the existing reading (no reading changes); planned outcomes apart from
      posted results

  2026-11-01: built in `TrialLedger/landscape.py` (`FIELDS`, `schema_problems`, the extract's assembly and
  `landscape_record(reading, studies, request, scope, manifest)`, `landscape_manifest`), every decision
  converged COMPLETE; tests in `tests/test_landscape.py`. Left: the command that calls it and writes the file
  (4.2), the scope it carries (2.3, here an opaque object), the workbook's Scope, Manifest and Study sheets
  (4.3), and comparable posted results in the cohort (waiting on `add-coherence-engine` 5.3). Nothing in
  production reaches the module until 4.2: its functions are declared in `tests/test_wiring.py` "until
  add-agent-operation 4.2".

  2026-11-01, after review: the record now carries `statuses` and `envelope` (what each status and each key of
  a value means) beside `fields`; `schema_problems` also checks every field's and value's type (scalars, an
  object's keys, a table's columns), a study's link against its own NCT number (a null link exempts nothing),
  efficacy and safety agreeing on the results and posting nothing without a results section, and coverage and
  the review queue naming the record's studies; it states what it cannot see (a value changed alike
  everywhere; only re-deriving from the studies finds it). `landscape_record` refuses a reading whose views'
  digests are not the studies', in order. A proposed relation that leaves a coordinate no value is unresolved,
  not proposed. Left as well: the Detective goldens of the landscape functions pin 64-hex study digests and
  warrants, which `scripts/push_checks.py` recognizes only as 16-hex `assert result == "<hex>"` lines, so the
  push scan refuses them until the founder decides how the scan treats them; and the cohort's occupancy copies
  `design.sheets`' code and imports `design._profile_trials` and `symbolic._axes`, which wants a shared public
  helper in `design.py` and `symbolic.py`.

## 2. Request resolution

- [x] 2.1 The request object and its refusals
- [x] 2.2 Drug class → members (RxClass `classMembers`, RxNorm names); mechanism → classes (crosswalk, entailed
      only); condition class → `AREA[ConditionAncestorTerm]`; drug → `AREA[InterventionName]` with other names
      (2026-11-01: settled as the rulings below record; where they and this line differ, the rulings hold.)

  2026-11-01, settled by Claude's reading and Codex's independent one, with the facts measured live that day
  (design.md As built here, "The rulings of 2026-11-01"): (1) the condition class keeps the term-or-ancestor
  form; (2) each drug name is searched in `AREA[InterventionName]` OR `AREA[InterventionOtherName]`, the names
  grouped inside each area (`request.name_clause`; both new forms in `NEW_FORMS` and
  `tests/request_query_forms.json`, dated, with an opt-in live test that they filter and that unheld names
  give 0); (3) a class means the class with its subclasses: `classes.rxclass_tree` (classTree) and each
  subclass's own members (`classes.direct_members_request`, trans=1) are asked, `rxclass_members` keeps every
  relation a member states, and `request.subclass_attribution` lists every subclass, attributes each member to
  the subclasses that list it as DIRECT and applies the new `drug_class.subclasses` ("include", "exclude" or
  ids to exclude, each with its subclasses; a DIRECT member never excluded); (4) a class member's base
  ingredient is searched only as a member the class lists, otherwise shown as a candidate
  (`request.member_names`). Every new request is named by `lookups_needed`; the RxNav answers they need were
  fetched into `tests/rxnav_request_answers.json` (release still 05-Oct-2026). Every changed or new decision
  converged `--two-sign` COMPLETE (`rxclass_tree`, `rxclass_members`, `slot_value_ok`,
  `subclass_attribution`, `member_names`, `resolve_scope`, `lookups_needed`; after review, the subclass
  orchestration `request._subclass_expansions`, now pinned with direct tests of each stop and wait, and
  `request.name_clause`). Left, for the founder: whether ruling 4 extends to a salt or biosimilar the person
  names in `drug` (today it is searched by its ingredient's name too); whether it should reach a brand or
  another-form member, as built, beyond the ruling's salt and biosimilar; and a biosimilar member's identity
  code, `salt` (`classes.name_identity`'s). Production reaches it through `trialledger landscape` (4.2).

  2026-11-01, ruling 4 corrected (a side reviewer's catch): as built it also kept a salt's ingredient out of the
  search, and a salt is the same molecule: the EPC Kinase Inhibitor lists dasatinib only as "dasatinib
  anhydrous", which 1 trial names, while 344 name "dasatinib", so the class's search lost them. A precise
  ingredient whose name is its ingredient's name followed by a word (a salt, hydrate or ester) is now searched
  by its ingredient too; a biosimilar ("bevacizumab-awwb", the ingredient's name joined by a hyphen to the FDA's
  suffix), a brand or another form still shows its ingredient as a candidate, not searched, as Codex advised.
  `request.member_names` re-converged `--two-sign` COMPLETE (85/90); the Kinase Inhibitor's search holds 82
  names, 68 with its subclasses excluded.
- [x] 2.3 The resolved scope written before any study is read; named codes for what cannot resolve
      (2026-11-01: the scope object, its named codes and the lookups it needs are built and converged,
      `request.resolve_scope` and `request.lookups_needed`; what is left is writing it into the run folder
      before any study is read, which needs the run folder (3.1, 3.2) and the command (4.2). A class whose
      query exceeds the registry's URL limit stops as `query_too_long`; splitting it into several queries is
      left to the step protocol, 3.1. Also left to 3.1: re-reading the RxNav release after the last round and
      refusing a change, since the scope's release is asked once, in the first round (`release_basis`), and
      retrying a failed lookup, which stops the scope until its answer is dropped and asked again.)

  2026-11-01, with 4.2 (`TrialLedger/operate.py`): the resolved scope is written into the run folder
  (`resolution.json`, `request.resolve_scope`'s with its release check; its query in `scope.json` through
  `steps.open_run`) before any study is read, and never resolved again once `scope.json` holds it. RxNav's
  release is asked again after the last round and a change refused by name (`operate.release_check`,
  `rxnav_release_changed`); a stop of failed lookups only (`operate.stop_status`) sets the failed answers
  aside in `lookups/dropped/`, so the same command asks them again; every other stop ends the run with its
  advice (`operate.stop_advice`, joined by `operate.scope_advice`, which tells a failed lookup beside such a
  stop as asked again in the new run folder the changed request needs, never in this one, whose failed
  answers are not set aside). `query_too_long` is not split: it ends the run (exit 2) advising a
  narrower request (an EPC class instead of a MoA class, a narrower subclass, the drugs themselves), as the
  4.2 task decided.

## 3. The step protocol

- [ ] 3.1 The pure decision naming what a run folder needs next (queries, pages, RxNav answers, complete)
- [x] 3.2 Direct mode through the existing transport; relay mode writing `next.json` and verifying fetched
      bodies with the existing classifiers; idempotent re-runs; nothing partial written as the record

  2026-11-01: built in `TrialLedger/steps.py` (`follow_ids`, `follow_batches`, `next_step`, converged
  `--two-sign` COMPLETE; the shell `open_run`, `advance`, `records`, `rxnav_answers`), with
  `ingest.json_query_params` extracted from `fetch_json_pages` unchanged (design.md Decision 6, "As built
  here"). 3.2 is done for the registry: every registry body is verified with the existing classifiers. RxNav
  bodies are not: each is only checked to be there, one that is not JSON (an error page, a recorded failure)
  is a failed lookup, and `rxnav_answers` hands them to their consumer in classes.py's `(status, body)` shape,
  so the classes.py decisions are applied by 4.2, not here. 3.1 holds the registry's whole plan (versions, ID
  pages, batches, every refusal) and relays the RxNav requests the scope fixes before any study is read. Left
  for 3.1: the RxNav answers the reading needs after the pull (`classes.load_or_lookup_at` over the pulled
  studies' drug names, chained: rxcui, then properties and related, then RxClass by name), each request fixed
  by the studies or by an earlier answer, are not yet named by the decision. A run is started by
  `trialledger landscape` (4.2), until which `steps.py` is declared in `tests/test_wiring.py`.

  2026-11-01, with 4.2: production now starts runs (`trialledger landscape`), so `steps.py` is on the
  production path but for `rxnav_answers` and `StepError` (declared in `tests/test_wiring.py`). The duties
  2.3 left to 3.1 are done in `operate.py` (above, 2.3), which resolves the request through its own
  `lookups/` before `open_run`, so the scope's RxNav requests are never relayed beside the registry's (it
  passes none). The post-pull RxNav answers are not planned by the step decision: direct mode asks them
  through `classes.load_or_lookup_at` exactly as `resolve` does; relay mode does not ask them (hundreds to
  thousands of URLs; decided 2026-11-01 by Claude and Codex independently), every drug's classes and axes
  reading not_looked_up. Left for 3.1: whether it closes so (the founder's call), and with it whether
  `open_run`'s `rxnav` and `rxnav_answers` are kept for another consumer or retired.

## 4. The operation and the workbook

- [x] 4.1 `trialledger doctor` (capability check as JSON, mode decided)

  2026-11-01: `TrialLedger/doctor.py`. `report` gathers the facts (Python version and support, each
  dependency's version, a short GET to clinicaltrials.gov, rxnav.nlm.nih.gov and github.com, a write-and-remove
  test of the run folder); the pure decision `run_mode` names the mode: `direct`, `relay`, or why no run can
  start (`unsupported_python`, `missing_dependency`, `folder_not_writable`, in that order), converged COMPLETE
  (67/67); each mode carries the agent's next step. `trialledger doctor [--run DIR]` prints the report as JSON
  and ends 0 when a run can start, 2 when it cannot; the probe is injectable (`cli.main(probe_get=...)`), and
  the production path runs it as a sandbox where RxNav is blocked (relay).
- [x] 4.2 `trialledger landscape` (request → run folder → record, workbook, manifest)
- [ ] 4.3 `landscape.xlsx`: the design workbook with Scope, Manifest and Study sheets

  2026-11-01: `TrialLedger/operate.py` (the run, end to end) and `trialledger landscape --run DIR
  (--request FILE | slot flags) [--mode direct|relay]` in `cli.py` (the flags read by
  `cli.request_from_flags`; the mode by default `doctor.report`'s). Exit codes: 0 complete, 3 awaiting fetch,
  2 refused or stopped by name, 1 failed (`operate.run_exit`), each printed with the agent's next step. The
  run writes `request.json`, `lookups/` and `lookups.json`, `resolution.json`, then the step protocol's
  folder, then `manifest.json` and `landscape.json` (refused unless `landscape.schema_problems` finds nothing
  in exactly the bytes written; never overwritten by a different record). Twelve pure decisions, each
  converged `--two-sign` COMPLETE (`lookup_request`, `saved_answer`, `answer_bytes`, `release_check`,
  `stop_status`, `stop_advice`, `scope_advice`, `run_exit`, `record_state`, `record_mode`,
  `retrieval_coverage`, `cli.request_from_flags`), and `reading.classes_as_looked_up`. `doctor.NEXT_STEP`
  names `trialledger landscape` for direct and relay. The production path runs it in both modes. A relay
  run's record equals a direct run's, apart from `manifest.retrieval`'s `mode` and `drug_classes`, only when
  no study read has an experimental arm's drug, biological or genetic intervention: with one, relay mode reads
  its classes and axes `not_looked_up` (no post-pull RxNav lookups, by design), and the review flags and
  cross-trial rows that follow from them differ too. Left: `landscape.xlsx` (4.3) has one call site,
  `operate.write_book` (staged, then renamed into place), which says "not built" until
  `TrialLedger/landscape_book.py` lands; the AGENTS.md, README.md and DEVELOPING.md updates (the task's
  report carries their text); and 5.1 (`SKILL.md`). For the founder: whether a class an experimental drug's
  own entry states is read `stated_by_record` in relay mode (as now) or `not_looked_up`, and whether a
  `not_looked_up` drug is a review question; and, when the first round's `version.json` failed, whether the
  whole resolution is set aside (today only the failed answers are, so the re-asked first release postdates
  the class and member answers it vouches for).

  2026-11-01, `pull`'s review.xlsx and record.xlsx laid out by workbook-design.md's "Formatting and print"
  (`TrialLedger/workbook.py`, formatting only): Arial 10, the header row bold and ruled below, the header row
  and identifying column frozen (B2), a filter over every listing, every cell top-aligned, widths and wrapping
  by column class from the existing `Column.kind` and `Column.source` (`width_class`: identifier 18 unwrapped,
  category 18, summary 40, long text 72), landscape with the header row repeated and a footer of the sheet's
  name and page; a sheet at most 170 characters wide fitted to one page wide, a wider one printed at full size
  over a defined print area with column A repeated (`print_fit`); no merged cells, no formulas, no number or
  date formats (dates stay the registry's text). Both decisions converged `--two-sign` COMPLETE. About stays
  first (it has no header row, so no frozen header and no filter); Checks, Check Rules and Record were already
  last. No cell value changes: with the code root pinned to the previous one, every cell of both books,
  warrants included, is identical; the code root itself changes (workbook.py is derivation code), so every
  computed warrant changes and a folder pulled before this commit verifies only at its own commit. Writing is
  about 1.3 times slower (300 studies: review 3.0 s to 4.0 s, record 4.5 s to 5.9 s, write and certify).
  Tests: `tests/test_width_class.py`, `tests/test_workbook_layout.py`. Left: the landscape.xlsx sheets
  themselves; a passage taller than Excel's 409-point row is still clipped on screen (continuation rows would
  change values).

  2026-11-01, after review: a warrant or record digest (64 characters) has its own class, 66 wide and unwrapped,
  so it is never cut off on screen or at the print area's edge (it had been an 18-wide identifier); an
  identifier column now wraps, so a value longer than 18 (a combined document's file name such as
  Prot_SAP_ICF_000.pdf, a stated absence) is never cut off, while an NCT number, PMID or group id fits; the Checks
  sheet is now wider than 170 and prints over a print area, so About is the one sheet fitted to a page. The
  Normal style and the default cell format are Arial 10, so empty cells and a reader's own entries match; a
  link is underlined, without colour; a brief summary is long text; About's topic and item columns swap widths
  (topic 40, item 18, the total still 170), so the book's title in A1 has a summary's width. No value changes.

  2026-11-01: the readout `workbook-design.md` settles is built in `TrialLedger/readout.py`
  (`write_readout(record, path)`, from a landscape.json record alone): Read me, Trial index, Trial review,
  Eligibility, Outcomes and efficacy, Biomarkers, Safety, Across-trial findings and Evidence register, every
  cell a pure row function's (each converged `--two-sign`), the register one row per displayed value, the file
  read back and refused unless every cell equals its derivation, its bytes the same for the same record. A
  criterion's role beside its heading is `criteria.criterion_role` (its own words "are excluded", "excluded
  if", "not eligible", "ineligible", "must not", "no history of", and, beyond the listed words, a permission
  "is permitted" or "are allowed", which under an exclusion heading is unresolved). Not carried by
  landscape.json schema 1, so shown "Not stated" with the register saying so: the brief title, the last
  update date, posted
  baseline characteristics, a criterion's cohort or arm, a biomarker's assay, specimen and timing, planning
  assumptions, a measurement's analysis population, denominators and analyses, an adverse event's grade, and
  an assessment schedule; the retrieval date shown is the manifest's data timestamp. Left: `trialledger
  landscape` (4.2) calls it (until then its functions are declared in `tests/test_wiring.py`), and the same
  formatting conventions for `pull`'s review.xlsx and record.xlsx.

## 5. The agent entry point

- [ ] 5.1 `SKILL.md` and the README's "For an agent" section, one procedure
- [x] 5.2 Packaging for a one-line install from the repository (package data, entry point, no compiler)

  2026-11-01, measured: installed into a fresh Python 3.12 environment from the repository (`uv pip install
  <path>`; httpx and openpyxl and their pure-Python dependencies, no compiler), the CLI runs, the registry
  tables and the seed fragment load from the installed package, and a live `resolve` of NCT04852770 run
  outside the repository writes its JSON and workbook. At runtime the package reads only its own files.
  Left: the same from the GitHub URL once the repository is public, and in each vendor's sandbox (0.1, 5.3).

  2026-11-01, the release check: `scripts/release_check.py` (tests in `tests/test_release_check.py`, how to
  run it in `scripts/README.md`) does what a first-time user does, in a new temporary directory outside the
  repository. It makes a fresh Python 3.12 environment with uv, then `pip install`s the repository's path or
  address (pip without its configuration or cache) and also `uv tool install`s it; a repository address is
  also cloned, so AGENTS.md and the package's file list are read from what the address serves. From that
  directory it runs every `--help`, `doctor`, a live `pull` of NCT04852770, NCT01827384 and NCT01086644,
  `verify` of the pulled folder and a one-trial `resolve` with --json and --out, then opens every workbook
  written. It reports each step's exit code, wall time, files written, warnings and tracebacks, and five
  checks, each with its problems or "not checked" and why (a check that did not run makes the verdict
  not_ready): the tracked package files the install left out, the outputs a user is handed, the requested-ID
  accounting, the commands AGENTS.md names that the CLI lacks, and pull's review.xlsx and record.xlsx against
  workbook-design.md's conventions (widths set, a filter and frozen panes on each listing); design.xlsx is
  inspected the same way, as leads. It also lists jargon in the help texts, printed words and workbooks. Its
  fourteen decisions converged `--two-sign` COMPLETE: five with nothing left; nine modulo unproven-equivalent
  or crash-only mutants (accounting_problems 51/55 killed, captured_text 36/40, jargon_found 21/23,
  missing_package_files 16/17, new_files 17/18, unknown_commands 17/20; clone_source 38/38, install_spec
  69/69 and subcommand_names 21/21 with such residuals besides).

  Run after the review's fixes, from this checkout and through `git+file://` (the address route, committed
  tree only), on this commit's code before this note was added: both not_ready, for one reason. Every step
  ended as expected; no package file was missing (48 tracked, all installed), so pyproject.toml is unchanged;
  the pull named NCT01086644 as aliased, answered by NCT01030536; `verify` certified the folder; the resolve
  of NCT01827384 from an empty cache took 169 s. pull's review.xlsx (17 sheets, Studies 50 columns) and
  record.xlsx set no column width and no filter on any sheet (their listings do freeze panes); design.xlsx
  sets none of the three and has blank cells (Classes 180, Results 186, Drug Axes 70) and an Audit sheet with
  "Founder: correct?" columns. Found and left for their owners: `TRIALLEDGER_CACHE` names the cache file, but
  `resolve --help` reads as if it named a folder, and a folder there fails the resolve with a traceback after
  all its RxNav lookups. `resolve` prints nothing during those lookups. `doctor` creates its run folder
  although its help says it changes nothing. `pull --help` cites `spec/ctg-oas-v2.yaml`, which an install does
  not have. An installed copy records `code_commit` "not a git checkout". main's AGENTS.md now names
  `landscape`, `design`, `edits` and `mcp`, which this CLI lacks: the guide check will name them until they
  land. The GitHub address itself waits on the public repository.

  2026-11-01, what that run found a first-time user trips on, fixed, and trials by number through `landscape`
  (no reading, record value or warrant changes; the code root is unchanged: 4370b5bf… under Python 3.14,
  f6092f35… under 3.12, the same as before this change under each): `trialledger landscape
  --ids NCT…,NCT…` (repeatable) is the request's `params` with `filter.ids`, joined by "," as given
  (`cli.request_from_flags`; `--ids` beside `--param filter.ids` is refused as `params_duplicate`), so the
  person gets landscape.json, its workbook and the requested-ID accounting
  (`manifest.retrieval.requested_ids`). Pull and landscape print each number not found under its own number in
  plain words (`ingest.requested_id_words`): "NCT01086644 is another number of NCT01030536: the registry gave
  that trial's record", never "aliased"; landscape also prints how many were asked and found.
  `TRIALLEDGER_CACHE` names a folder (classes.json inside it: one that exists, or a path ending in "/") or a
  file (`classes.cache_location`, `classes.cache_path`); the cache's contents are unchanged. `resolve` and
  `landscape` say how far their RxNav lookups have got: how many names they will ask about, then a line every
  five names and after the last (`classes.progress_due`; landscape's resolution rounds likewise, by request).
  `doctor` removes a run folder it created for its write test, with every folder above it it created; its help
  says what it changes, and its next step names `--ids`. `trialledger --help` says what TrialLedger does and
  lists the user commands first (doctor, landscape, pull, verify; `cli.USER_COMMANDS`), each in plain words
  with an example and its exit codes; the developer tools (resolve, profile, sample, audit, pilot; named by
  neither AGENTS.md nor README.md) have no help line, are named under "for developers" and still run; no user
  command's help says "symbolic", "digest", "warranted", "re-derive", "Merkle" or "code root" or cites
  spec/ctg-oas-v2.yaml (neither does pull's version note), and release_check's word list finds nothing in them
  but "relay", the mode the guides define (`tests/test_help_words.py`); "30%" reads as written; the default
  folders are `./trialledger_run` (doctor) and `./trialledger_<UTC time>` (pull). An installed copy records
  the commit it was built from: `hatch_build.py`, a hatchling build hook (no new dependency), writes
  `TrialLedger/build_commit.txt` into a wheel or sdist built from a checkout ("<commit> with uncommitted
  changes" when TrialLedger/ is not clean; an editable install is stamped nothing; the source tree is never
  written), and `record.code_commit` names it (`record.commit_named`) before asking git, which it asks only
  about a package git tracks, so a copy inside another repository is not named by that one's commit. The
  release check now runs `landscape --ids` of its three trials (no `--mode`: the doctor's), checks its
  accounting, sets `TRIALLEDGER_CACHE` to a folder, and reports the commit the install records; it adds
  "aliased" to its word list and expects landscape.json and landscape.xlsx. Converged `--two-sign` COMPLETE:
  `requested_id_words`, `cache_location`, `progress_due`, `commit_named`, `request_from_flags` and
  `release_check.accounting_problems` (now: an alias said as "<number> is another number of <study>", any
  other number not found as "<number>:"). Left: landscape.xlsx (4.3) and `design`, `edits` and `mcp`, which
  keep the release check not_ready until they land; whether `pull` gets the landscape's readable workbook (the
  founder's decision).

  2026-11-01, the review of that change, fixed (no reading, record value or warrant changes; both code roots
  as above). The code root is taken over the code's syntax as the running Python reads it, so the same commit
  has one root under 3.12 and another under 3.14, and a folder verifies only under the Python version that
  wrote it: `verify --help` and verify's words for another code now say so, in plain words (no "derivation
  code", no "warrant re-derives"), and name the Python this verify runs under. The record does not name the
  Python that wrote it, and making the root the same across Python versions changes the derivation code: both
  are the founder's call. `resolve --help` says when `TRIALLEDGER_CACHE` names a folder (one that already
  exists, or a path ending in "/") and that any other path is the cache file itself. Since landscape.xlsx is
  not built yet (4.3), `trialledger --help` and landscape's line no longer promise a spreadsheet, and a run's
  last words say so without the task's number. Landscape says "1 trial asked for by number"; its resolution
  progress reads "RxNav lookups asked"; doctor's next step and landscape's refusal say "the request's flags";
  verify's help says a repeated field ends 1 (not certified); landscape's exit 2 names a run folder holding
  another request and a sandbox where no run can start; doctor's `--run` is the folder to test, the one given
  to landscape. `hatch_build.built_from` asks git only about a checkout that tracks the package, so an
  unpacked sdist inside another repository keeps its own stamp (`tests/test_build_stamp.py`, with a stand-in
  for hatchling). The plain-words check of the help now runs over every `cli.USER_COMMANDS`, so `mcp` is held
  to it once it joins them. The `{doctor,...,pilot}` line of `trialledger --help` stays: the release check
  reads the commands from it (`release_check.subcommand_names`).
- [ ] 5.3 End to end with a real agent per vendor, in its app, relay mode where its sandbox needs it

## 6. Edits and the MCP adapter

- [ ] 6.1 `trialledger edits`: workbook edits as user assertions
- [x] 6.2 The stdio MCP adapter over `doctor`, `landscape`, `record`

  2026-11-01: `TrialLedger/mcp_server.py` and `trialledger mcp [--root DIR]` in `cli.py`. MCP revision
  2025-11-25 (the last revision opened by an `initialize` handshake; 2026-07-28 dropped it), stdio transport,
  JSON-RPC 2.0 written with the standard library only: `initialize` (the client's version when it is one of
  2025-11-25, 2025-06-18, 2025-03-26, 2024-11-05, else 2025-11-25), `notifications/initialized`, `ping`,
  `tools/list`, `tools/call`; parse error, invalid request (a batch among them), method not found
  (`server/discover` among them once initialized; before, "not initialized": either way an error of the
  handshake era, on which a dual-era client of 2026-07-28 falls back to `initialize`, as that revision's
  versioning page, "Backward Compatibility with Initialization-Based Versions", says for stdio, checked
  2026-11-01) and invalid params (an unknown tool) as JSON-RPC errors; a tool's refusal as a result with
  `isError: true` and plain words. Standard
  output carries protocol lines only (descriptor 1 is pointed at standard error once the protocol's copy is
  taken). Tools: `doctor`; `landscape` (the request object `--request` takes, its slots in the schema; the
  outcome's status, exit code and its meaning, detail and advice; for awaiting_fetch next.json's fetches, its
  instructions and the steps through `save_fetch`; isError exactly when the exit is 1 or 2); `save_fetch` (the
  body written exactly as given, as UTF-8, staged then renamed, only to a save_as the run's next.json names and
  only inside the run folder, a link carrying it out refused too); `scope` (resolution.json, resolved or
  stopped); `record` (manifest with the retrieval and requested-ID accounting, studies with their headline
  envelopes, one study's extract by NCT number, statuses with the envelope's meanings, fields; every value as
  the record holds it). Every run folder is a name (letters, digits, `.`, `_`, `-`) inside the root, by
  default `~/trialledger-runs`. Six pure decisions, each converged `--two-sign` COMPLETE: `route` (194/194),
  `negotiate` (40/40), `call_target` (72/72), `argument_problems` (134/136; the two survivors drop the `^` or
  the `$` of an anchored pattern before `re.fullmatch`, which anchors both ends already), `save_target`
  (75/75), `record_view` (199/200; the survivor makes a `zip` of two lists of one length non-strict). The
  production path drives an MCP session (a relay run through `save_fetch` and a direct run); only
  `stdio_streams` is declared in `tests/test_wiring.py`. Left: `design` is not served (it does not exist yet,
  `add-design-synthesis`), though AGENTS.md, README.md and documented-interface.md say `mcp` serves it; a body
  next.json no longer names (one refused as not_json or not_a_registry_page, whose advice is to delete it and
  fetch again) cannot be replaced through the tools, so through MCP such a run is started again in a new run
  folder; the relay through MCP passes every fetched body through the assistant's context (a batch of 100
  studies is megabytes), so an MCP client on a computer that reaches the registry should run direct.

  2026-11-01, after review: rebased on main's subclass work, so the request schema's `drug_class` takes
  `subclasses` (include, exclude or ids), held to `request.slot_value_ok` by a test. No line ends a session:
  JSON nested past the parser is a parse error, any other defect in answering a line an internal error with
  the next line read, and an answer echoing a lone surrogate the client sent is written with JSON's `\u`
  escapes (tested over the encoded stream). A run folder that is a link out of the root is refused
  (`run_outside_root`); `save_fetch` removes anything at its staging name and creates it afresh, never
  following a link. Statuses whose advice names the command line (`--run`, `--help`, "the same command")
  carry `with_these_tools`, saying what each means with the tools; a folder that cannot be written points to
  `--root` in the client's configuration. The descriptions and instructions say to run direct whenever doctor
  reports it and that a relayed body passes through the assistant, so it is saved exactly as received. Left
  for the founder: a relayed body passes through the assistant whether relayed by the shell (AGENTS.md: the
  assistant fetches "with your own fetch tool") or by `save_fetch`, and the step protocol checks its form,
  counts, page tokens and IDs, not its values; whether the record should mark that channel (it reads
  retrieval mode `relay` for both) is a change to the record's schema, not made here. `record` part studies
  is one result however many studies (about 2.4 KB each); not paged.

## 7. Layer-one acceptance

- [ ] 7.1 Twenty trials, chosen and written down before any comparison is made, diverse by phase, status,
      study type, results posted or not, sponsor class and record size (one with aliases among them); for
      each, an independent reader compares every field of `record.xlsx` and `review.xlsx` against the
      registry's own page, field by field, and every difference is recorded with its cause. `verify` proves a
      value derives from the record by the code; this establishes that the code maps each field faithfully.
      The result is reported as it falls, differences included. (2026-11-01: built and run, pending the
      founder's rulings below, as 2.2 is.)

  2026-11-01: built and run in `acceptance/` (report `acceptance/report-2026-11-01.md`), written without
  reading TrialLedger's code or tests: `select.py` froze a seeded selection of twenty trials over twenty
  strata in `selection.json` (its creation time and the script's SHA-256 in it) before the pull; `compare.py`
  ran `trialledger pull` on them as a black box, fetched the same records independently as JSON and CSV, and
  compared, per field: (a) every Record row of `record.xlsx` with the raw JSON at its Location, every leaf of
  the JSON with the rows, and each Role's facets with the record; (b) the API's CSV with the JSON by the
  registry's documented columns (`csv-columns.md`) and with `record.xlsx`; (c) every `review.xlsx` column
  declared stated from one registry field, the stated columns giving a row's place, the computed at-risk
  count against its declared rule, each sheet's rows against the records' elements, the links, and every
  pairing of a column with a field against the About sheet's declaration; (d) `studies.csv` byte for byte;
  (e) `verify`; (f) `studies.json` record by record; (g) the About sheets' provenance. Sixteen planted defects
  are all caught (the first version of (d), a whole-file comparison, missed the one in `studies.csv`; kept
  and reported). Tests: `tests/test_acceptance.py`, on small excerpts of the records; the reader's decisions
  are converged with Detective. Departure from this text: the reference is the registry's record as the API
  sends it (JSON and CSV, the sources `pull` reads), not the HTML study page. Independence, as it stands:
  which registry field each `review.xlsx` column holds was transcribed from `review.xlsx`'s own About sheet;
  the reader resolves each field in the registry's JSON independently. Found, for the founder: all 14,718
  record values agree and every one is held once; `studies.csv` is the API's CSV with a UTF-8 byte-order mark
  put before it, not byte for byte as AGENTS.md says; `review.xlsx`'s Outcome Results sheet has no row for a
  results-section outcome measure with nothing posted (three NOT_POSTED measures of NCT06145282), which only
  `record.xlsx` shows; Publications › Retractions says "none in the record", an absence wording the About
  sheet does not define; `record.xlsx`'s Role is declared stated though its source is a rule
  (`ledger.node_role`); the registry's CSV Age column omits the minimum and maximum ages its documentation
  lists. Every change made to the reader after its first comparison, including the revision after review, is
  listed in the report.

  2026-11-01, after review: left unticked, pending the founder's rulings: the byte-order mark (and AGENTS.md's
  "byte for byte"); the NOT_POSTED measures; the "none in the record" wording; Role's status; and whether the
  comparison with the HTML study page this text names is still wanted. Not covered by this test, by design:
  human transcribers, clinical meaning, and the columns computed by TrialLedger's rules other than the
  at-risk count.
