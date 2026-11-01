# Proposal

## Why

The founder, 2026-11-01 (paraphrased): TrialLedger has two layers. The first is a correctness layer that an LLM
agent picks up like an exo-suit: asked about a mechanism, a drug, a drug or disease class, or any other way people
think about clinical trials, the agent uses it to query ClinicalTrials.gov and write a JSON record of truth for
that group (the ten-point extract and its extras: eligibility, outcomes and time points, biomarkers, efficacy,
safety, standard protocol language), answers the user from that record, and hands the user a spreadsheet to read,
edit and share. It must work from the OpenAI, Anthropic and Google apps, for a user who is not technical. The
delivery is the repository: an agent is pointed at it on GitHub, fetches it and runs it, from any device. The
repository is made public when it is built. This is the next priority, built to completion.

The work it replaces is mechanical: opening hundreds of registry records one at a time and copying their fields
by hand, for every question. The operation does that work whole, and the agent answers from what it wrote, never
from a trial page.

## What Changes

- An agent entry point at the repository's root: `SKILL.md` (the Agent Skills format) and a README section for
  agents, stating what TrialLedger is, how to install it, the capability check, the one operation, its outputs,
  and how to answer from the record and hand over the workbook.
- `trialledger doctor`: the capability check, as JSON (Python version, dependencies, which of GitHub,
  ClinicalTrials.gov and RxNav are reachable from this sandbox, a writable run folder).
- `trialledger landscape`: one operation from a structured request (drug, drug class, mechanism, disease or
  disease class, phase, status, dates, study type) to a run folder holding `landscape.json`, `landscape.xlsx` and
  `manifest.json`.
- Request resolution: the request compiled symbolically into registry queries (a drug class into its member
  drugs by RxClass and RxNorm; a mechanism into classes by the sourced crosswalk; a disease class into the
  registry's own condition-ancestor search), every expansion written into the record; what cannot be resolved is a
  named code, never a guess.
- The step protocol: TrialLedger needs no network of its own. Where the sandbox cannot reach the registry (the
  chat apps' code sandboxes, verified 2026-11-01), the operation writes the exact URLs it needs next into the run
  folder, the agent fetches them with its own fetch tool, and the next run verifies each response as the API's own
  and continues; where the sandbox can reach them, the same command fetches them itself. The run folder is the
  checkpoint: a sandbox's time limit loses nothing, and a record is never written as complete when the pull was
  not.
- The record contract: `landscape.json`, versioned and self-describing, each value with its status, source field
  and link; per trial and across the cohort; planned endpoints kept apart from posted results; coverage per trial
  type from the supported-type matrix.
- An MCP adapter over the same functions, for clients that launch a local server.
- Workbook edits read back as the user's own assertions, never overwriting a sourced value.

## Capabilities

### New Capabilities

- `agent-operation`: the entry point, the capability check, request resolution, the step protocol, the record
  contract, the workbook and its edits, the MCP adapter.

## Impact

New modules for request resolution, the step protocol and the record; `cli.py` gains `doctor` and `landscape`;
`ingest.py`'s transport becomes pluggable between direct HTTP and fetched files, with the same verification;
`SKILL.md` and the README's agent section at the root. The existing readings, workbooks and warrants are reused
unchanged. The earlier draft of this change (a conversational interface awaiting the founder's systems) is
superseded.
