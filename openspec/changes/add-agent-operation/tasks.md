# Tasks — add-agent-operation

The founder, 2026-11-01: the next priority, built to completion.

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

- [ ] 4.1 `trialledger doctor` (capability check as JSON, mode decided)
- [ ] 4.2 `trialledger landscape` (request → run folder → record, workbook, manifest)
- [ ] 4.3 `landscape.xlsx`: the design workbook with Scope, Manifest and Study sheets

## 5. The agent entry point

- [ ] 5.1 `SKILL.md` and the README's "For an agent" section, one procedure
- [ ] 5.2 Packaging for a one-line install from the repository (package data, entry point, no compiler)
- [ ] 5.3 End to end with a real agent per vendor, in its app, relay mode where its sandbox needs it

## 6. Edits and the MCP adapter

- [ ] 6.1 `trialledger edits`: workbook edits as user assertions
- [ ] 6.2 The stdio MCP adapter over `doctor`, `landscape`, `record`
