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

- [ ] 2.1 The request object and its refusals
- [ ] 2.2 Drug class → members (RxClass `classMembers`, RxNorm names); mechanism → classes (crosswalk, entailed
      only); condition class → `AREA[ConditionAncestorTerm]`; drug → `AREA[InterventionName]` with other names
- [ ] 2.3 The resolved scope written before any study is read; named codes for what cannot resolve

## 3. The step protocol

- [ ] 3.1 The pure decision naming what a run folder needs next (queries, pages, RxNav answers, complete)
- [ ] 3.2 Direct mode through the existing transport; relay mode writing `next.json` and verifying fetched
      bodies with the existing classifiers; idempotent re-runs; nothing partial written as the record

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
