---
name: trialledger
description: Produce a clean clinical-trial reference spreadsheet and matching JSON for specific trial numbers or a requested subset of ClinicalTrials.gov studies (layer one, available). Report registry facts and strictly warranted direct derivations. Layer two aims to construct a new trial from scratch through symbolic reasoning; it is partially built, without a complete design workflow.
---

# TrialLedger

**Layer one is available:** a user names specific trials or a subset by drug/class, condition, phase, status,
study type or date; return one formatted reference workbook (`landscape.xlsx`) and matching JSON
(`landscape.json`), with a dossier per study and shared listings. Use the saved record for answers and give
the person the workbook. Its content is registry facts and strictly warranted direct derivations only.

**Layer two is partially built:** its purpose is to construct a new trial from scratch from the user's brief
and layer-one evidence through symbolic reasoning, with deductions, proposals and human choices distinguished.
Reasoning and existing-trial analysis foundations exist; the complete design workflow and public design
command/tool do not. Explain this status when introducing TrialLedger; do not promise a completed new trial.

Read `AGENTS.md` for the full procedure.

1. Install on Python 3.12+: `pip install "git+https://github.com/rohanvinaik/TrialLedger"`.
2. Run `trialledger doctor --run FOLDER`; prefer direct mode. Relay means fetching named URLs unchanged.
3. Build request flags or `--request FILE`; study numbers use `--ids NCT...,NCT...`. Preview with
   `trialledger landscape --run FOLDER <request flags> --preview`. Show the resolved search and resolution.json.
4. Repeat without preview to gather the fixed search. A changed request uses a new folder. Exit 3 awaits
   next.json fetches; save each body unchanged at its named path and repeat. Exit 0 is complete/previewed;
   2 names refusal/stop; 1 gives failure/retry advice. Never shorten, retype or correct a relay response.
5. Read landscape.json, inspect requested-ID accounting when relevant, and deliver landscape.xlsx. Retrieval
   completion does not establish that every requested ID was found.

The schema-4 record stores copied fields plainly with source paths once in `fields`. Direct derivations name
their rule and inputs; missing/malformed values retain named states. Listing addresses retrieve the same scoped
record evidence through MCP. Preserve exact words, groups, populations, denominators, units, times, precision,
zeros and false. Not stated is not none; not posted is not no effect; empty listings are not zero harms.

Eligibility segmentation is structural, not interpretation. Keep registered plans apart from posted observations.
Show biomarker, imaging and treatment-history text as written; do not infer roles, setting, current care, grades,
comparability, planning targets or reusable standards. Ordinary reports do not perform MeSH enrichment or clinical
recognition/ranking. Direct drug lookup evidence remains attributed; relay does not enrich gathered drugs.

`trialledger mcp` exposes doctor, scope, landscape, save_fetch and record. Preview with scope; follow relay
requests exactly; use record/address for answers. Follow page.next_offset; paging is bounded at 50 entries.
`verify FOLDER` checks landscape or archival pull reproducibility offline from retained inputs under the writing
code. It does not certify clinical meaning. `pull` separately preserves raw registry records/CSV and archival
workbooks. Clinical inference/defaults/proposals and design belong to layer two. No current design/edits operation
or automatic import of workbook annotations is promised.
