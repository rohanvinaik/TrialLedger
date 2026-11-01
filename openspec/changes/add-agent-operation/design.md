# Design — add-agent-operation

## Context

Proposed 2026-11-01 (supersedes the earlier conversational-interface draft). The user is not technical and uses
a chat app (ChatGPT, Claude or Gemini); the app's agent is TrialLedger's operator. The founder's terms: no hosted
service, the repository is the product, public once built; the agent fetches it and runs it.

Measured 2026-11-01 (secondary sources, to re-check at build time): ChatGPT's code container installs packages
through a proxy but blocks outbound HTTP from user code, and can fetch public URLs into the container; Claude's
in-app code execution reaches package registries and GitHub by default, not other domains; Gemini's agent
sandboxes reach an allowlist. So the agent can install TrialLedger and fetch URLs, while TrialLedger's own code
may not reach ClinicalTrials.gov or RxNav. Desktop and CLI agents (Claude Code, Codex, a laptop) can.

## Decisions

1. **The repository is the product; the agent is the operator.** Nothing is hosted. Installation is one line
   from the repository (`pip install git+https://github.com/<owner>/TrialLedger`, or `uv tool install` from the
   same URL, or an archive download where git is absent), with Python 3.12 or later and two dependencies (httpx,
   openpyxl), no compiler. Every file a run needs (registry tables, rule banks, schemas) ships in the package.

2. **The agent entry point.** `SKILL.md` at the root (Agent Skills format: name, description, then the
   procedure) and a README section "For an agent" carry the same procedure: run `trialledger doctor`; install if
   needed; turn the user's question into a request (the agent's job: it is the user's sentence, not a trial's);
   run `trialledger landscape`; follow the step protocol until the run is complete; answer from `landscape.json`
   keeping each value's status; attach `landscape.xlsx` through the app's file mechanism. Vendor-specific notes
   (where a capability differs) sit in the same document, never in another format.

3. **The capability check.** `trialledger doctor` prints JSON: Python version and whether it is supported, each
   dependency's presence and version, whether clinicaltrials.gov, rxnav.nlm.nih.gov and github.com answer from
   this process (a small GET each, a timeout of seconds), and whether the run folder is writable. It decides the
   mode: `direct` (TrialLedger fetches) or `relay` (the agent fetches). It changes nothing.

4. **The request.** A JSON object (or the equivalent command-line flags) of slots: `drug` (names), `drug_class`
   (an RxClass class name or id with its source: EPC, MoA, ATC), `mechanism` (a target word of the crosswalk),
   `condition` (a term), `condition_class` (a MeSH descriptor to read as an ancestor), `phase`, `status`,
   `study_type`, `start_from`, `start_to`, and raw registry parameters for anything else. Every slot is
   optional; an empty request is refused.

5. **Request resolution is symbolic and shown.** A drug class resolves to its member drugs by RxClass
   (`classMembers`, with the class's source and relation), each member's names by RxNorm; a mechanism to the
   classes the sourced crosswalk aligns to it (only entailed relations; an overlapping one is listed as such and
   not expanded); a condition class to the registry's own `AREA[ConditionAncestorTerm]` search, so the registry's
   MeSH tree does the descent; a drug or member name to `AREA[InterventionName]` with its other names. The
   resolved scope (every expansion, its source and the query sent) is written into the record before any trial is
   read, so the agent can show the user what was included. Unresolvable slots return named codes
   (`class_not_found`, `class_ambiguous` with the candidates, `mechanism_not_in_crosswalk`, ...), never a guess.

6. **The step protocol.** One pure decision reads the run folder and names what is needed next: the queries to
   send, the pages awaited (each page's URL fixed by the previous page's `nextPageToken`), the RxNav answers
   awaited, or `complete`. In `direct` mode the command performs those requests itself through the existing
   transport (throttle, retries, snapshot checks). In `relay` mode it writes `next.json` (each URL and the file
   name to save its body as) and exits with a named status (`awaiting_fetch`); the agent fetches each URL to that
   file, and the next run verifies each body with the same classifiers as a direct pull (`classify_json_page`,
   `classify_version`, the snapshot timestamp) and continues. A body that is not the API's own answer, or a
   snapshot that changed mid-run, is refused by name; nothing partial is ever written as the record. The folder is
   the checkpoint; re-running is idempotent.

7. **The record contract.** `landscape.json`, versioned (`schema_version`), self-describing (a `fields` section
   gives each field's meaning, status vocabulary and source): the request; the resolved scope; the manifest (data
   timestamp, API version, each study's digest, the Merkle root, code commit, rule versions, retrieval coverage);
   per study, the ten-point extract and its extras, each value with status, source field path and the registry
   link; across the cohort, the profile (statement rates with their silence bounds, standard tier, mechanism
   signals, occupancy, near misses, endpoints and time points by class, comparable posted results); the review
   queue's closed questions; coverage per trial type from the supported-type matrix. Planned endpoints and posted
   results are different fields: a registered outcome is never efficacy evidence.

8. **The workbook.** `landscape.xlsx` is the existing design workbook (its sheets and warrants unchanged) with a
   Scope sheet (the resolved scope), a Manifest sheet and a Study sheet per the ten points. Readable in Excel,
   Numbers and Google Sheets.

9. **Edits are the user's assertions.** `trialledger edits <run> <edited.xlsx>` reads the edited workbook back:
   a changed or added cell becomes a user assertion with its author, never overwriting the sourced value; the
   record shows both. A cell the workbook marks as derived is re-derived, never edited in place.

10. **The MCP adapter.** A thin stdio MCP server exposing `doctor`, `landscape` (start or continue a run) and
    `record` (read a finished run's JSON), over the same functions, for clients that launch a local server. It
    adds no logic.

## Risks / Trade-offs

- [App capabilities change] → `doctor` measures the session rather than assuming the vendor; the relay mode
  needs only the agent's ability to fetch a URL to a file and run Python.
- [Large scopes in relay mode mean many fetches] → pages of 1,000 IDs first, then records in batches by
  `filter.ids`; the scope is shown before the pull so the user can narrow it.
- [A class expansion missing a member] → the scope is in the record and the workbook; the class source and its
  release are named.
