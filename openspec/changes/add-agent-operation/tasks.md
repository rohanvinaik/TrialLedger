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

- [ ] 1.1 `landscape.json` schema v1: request, scope, manifest, per-study ten-point extract and extras, cohort
      profile, review queue, coverage; each value with status, source and link; the `fields` self-description
- [ ] 1.2 The per-study extract from the existing reading (no reading changes); planned outcomes apart from
      posted results

## 2. Request resolution

- [x] 2.1 The request object and its refusals
- [ ] 2.2 Drug class → members (RxClass `classMembers`, RxNorm names); mechanism → classes (crosswalk, entailed
      only); condition class → `AREA[ConditionAncestorTerm]`; drug → `AREA[InterventionName]` with other names
      (2026-11-01: built and converged in `request.py`, pending the founder's ruling on two departures from
      this text, design.md As built here: the condition class is emitted as sample.py's verified
      term-or-ancestor form, not the ancestor alone, since the ancestor alone misses the trials tagged with
      the descriptor itself; and "other names" are RxNorm's names (its concept's, and a salt's, brand's or
      other form's ingredient's), not the registry's `AREA[InterventionOtherName]`, which is not emitted. Also
      for the founder: every RxClass member is expanded, INDIRECT ones included, and a PIN member is searched
      by its ingredient's name too.)
- [ ] 2.3 The resolved scope written before any study is read; named codes for what cannot resolve
      (2026-11-01: the scope object, its named codes and the lookups it needs are built and converged,
      `request.resolve_scope` and `request.lookups_needed`; what is left is writing it into the run folder
      before any study is read, which needs the run folder (3.1, 3.2) and the command (4.2). A class whose
      query exceeds the registry's URL limit stops as `query_too_long`; splitting it into several queries is
      left to the step protocol, 3.1. Also left to 3.1: re-reading the RxNav release after the last round and
      refusing a change, since the scope's release is asked once, in the first round (`release_basis`), and
      retrying a failed lookup, which stops the scope until its answer is dropped and asked again.)

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

## 4. The operation and the workbook

- [x] 4.1 `trialledger doctor` (capability check as JSON, mode decided)

  2026-11-01: `TrialLedger/doctor.py`. `report` gathers the facts (Python version and support, each
  dependency's version, a short GET to clinicaltrials.gov, rxnav.nlm.nih.gov and github.com, a write-and-remove
  test of the run folder); the pure decision `run_mode` names the mode: `direct`, `relay`, or why no run can
  start (`unsupported_python`, `missing_dependency`, `folder_not_writable`, in that order), converged COMPLETE
  (67/67); each mode carries the agent's next step. `trialledger doctor [--run DIR]` prints the report as JSON
  and ends 0 when a run can start, 2 when it cannot; the probe is injectable (`cli.main(probe_get=...)`), and
  the production path runs it as a sandbox where RxNav is blocked (relay).
- [ ] 4.2 `trialledger landscape` (request → run folder → record, workbook, manifest)
- [ ] 4.3 `landscape.xlsx`: the design workbook with Scope, Manifest and Study sheets

## 5. The agent entry point

- [ ] 5.1 `SKILL.md` and the README's "For an agent" section, one procedure
- [x] 5.2 Packaging for a one-line install from the repository (package data, entry point, no compiler)

  2026-11-01, measured: installed into a fresh Python 3.12 environment from the repository (`uv pip install
  <path>`; httpx and openpyxl and their pure-Python dependencies, no compiler), the CLI runs, the registry
  tables and the seed fragment load from the installed package, and a live `resolve` of NCT04852770 run
  outside the repository writes its JSON and workbook. At runtime the package reads only its own files.
  Left: the same from the GitHub URL once the repository is public, and in each vendor's sandbox (0.1, 5.3).
- [ ] 5.3 End to end with a real agent per vendor, in its app, relay mode where its sandbox needs it

## 6. Edits and the MCP adapter

- [ ] 6.1 `trialledger edits`: workbook edits as user assertions
- [ ] 6.2 The stdio MCP adapter over `doctor`, `landscape`, `record`

## 7. Layer-one acceptance

- [ ] 7.1 Twenty trials, chosen and written down before any comparison is made, diverse by phase, status,
      study type, results posted or not, sponsor class and record size (one with aliases among them); for
      each, an independent reader compares every field of `record.xlsx` and `review.xlsx` against the
      registry's own page, field by field, and every difference is recorded with its cause. `verify` proves a
      value derives from the record by the code; this establishes that the code maps each field faithfully.
      The result is reported as it falls, differences included.
