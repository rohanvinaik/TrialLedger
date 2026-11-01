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

   *As built here (2026-11-01, tasks 3.1 and 3.2; `TrialLedger/steps.py`).* The run folder holds
   `request.json`, `scope.json` (the registry query and the RxNav requests, each `[url, params]`),
   `fetches.json` (every fetch named so far, in order, never rewritten: its full URL, parameters, the file its
   body is saved as and why: `version_start`, `id_page`, `studies_batch`, `version_end`, `rxnav_answer`),
   `bodies/` and, in relay mode, `next.json`. The plan is the direct path's own requests: /version; the ID
   pages exactly as `query_ids` sends them (fields=NCTId, 1,000 a page, each later page with the previous
   page's token), one at a time; then every batch of `PAGE_SIZE` (100) IDs at once, each exactly the request
   `query_studies({"filter.ids": ...})` sends; then /version again, named only once every batch is saved; the
   scope's RxNav requests are named alongside the first /version. The parameters come from
   `ingest.json_query_params`, extracted from `fetch_json_pages` unchanged, and each URL is httpx's own
   encoding of them, so the relayed URL is the URL the Session sends (tested against FakeAPI's recorded
   requests). Three pure decisions, each converged `--two-sign` to COMPLETE: `follow_ids` (the ID pages
   through `classify_json_page`, `classify_progress` and `assess_completeness`), `follow_batches` (each batch
   exactly its IDs, once, and exactly its totalCount; a whole batch is accepted even with a nextPageToken,
   since a further page could only exceed totalCount: the registry sent one with each full batch of 100 in a
   live run, 2026-11-01) and `next_step` (the whole folder: `classify_version` on both /version answers and
   `compare_snapshots` between them). One code, one remedy: `not_json` (a registry body that is a truncated
   download or an HTML page) and `not_a_registry_page` (a classifier's code in the detail): delete it and
   fetch again; `page_out_of_order` (a file saved for a fetch not yet named, or in no plan): delete it;
   `incomplete_total` (the ID pages cannot be followed to totalCount, `classify_progress`'s repeated_token,
   overrun or stalled in the detail, or do not hold exactly totalCount IDs; a batch is not exactly its IDs)
   and `snapshot_changed`: start a new run folder. A missing body is simply awaited by name; a hidden file in
   `bodies/` (`.DS_Store`) is no body.

   What is checked, exactly: every registry body as a direct pull checks its pages (form, totalCount, page
   tokens, every batch exactly its IDs, one snapshot from the first /version to the last). Nothing in a
   registry page says which request it answers, so a page saved under another page's name is caught only when
   its tokens or counts disagree; the relay instructions say so. An RxNav answer is answered once its file is
   saved, whatever it holds, and is checked no further (no snapshot covers it): one that is not JSON is a
   failed lookup, never refused and never asked again. Direct mode saves an RxNav request that fails
   (`PullError` from the Session: 404, 400, 5xx after retries) as a note `failed: <code>: <detail>`; the relay
   instructions ask the agent to save `failed: HTTP <status>` likewise; a registry request that fails still
   raises `PullError`, as in a direct pull. `rxnav_answers` reads them back in classes.py's `(status, body)`
   shape (`http_get`'s): 200 and the body for JSON, 0 and None otherwise, which `rxclass_classes`,
   `rxnorm_ids` and the others read as `lookup_failed`, never as no class. The classes.py decisions are
   applied by the consumer (4.2), not by the step decision. A recorded failure stays (a transient 5xx after
   the Session's retries included): to ask again, delete the file and run the same command. The Session's 1.25
   s spacing paces the RxNav requests too.

   The shell (`open_run`, `advance`, `records`, `rxnav_answers`) is the transport seam: direct mode fetches
   through `ingest.Session` and saves each body (staged, then renamed); relay mode writes `next.json` (status,
   detail, the run folder, plain instructions or the refusal's advice, and each fetch's URL and `save_as`) and
   returns `awaiting_fetch`. `records` assembles the studies in the ID pages' order only when `next_step` says
   complete; a relay round trip, a direct-mode run and `query_studies` give the same records on the same fake
   pages, and an opt-in live test (`test_a_live_run_holds_what_query_studies_returns`) found a direct-mode run
   equal to `query_studies`, order included, for a 269-study query on 2026-11-01. Left: the decision names
   only the RxNav requests the scope fixes before any study is read; the answers the reading needs after the
   pull (`classes.load_or_lookup_at` over the pulled studies' drug names, chained: rxcui, then properties and
   related, then RxClass by name, each request fixed by the studies or an earlier answer) are not yet planned,
   so task 3.1 stays open. Nothing in production starts a run until `trialledger landscape` (4.2), so
   `steps.py` is declared in `tests/test_wiring.py` until then.

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

## As built here

- **Decisions 4 and 5, 2026-11-01** (`TrialLedger/request.py`; `classes.class_members_request` and
  `classes.rxclass_members` beside the existing RxClass lookups). The request is validated by
  `request_problems` (`not_an_object`, `empty_request`, `unknown_slot`, `malformed_value` per
  `slot_value_ok`, a start_from after the start_to, `params_<check_query code>`, and `params_conflict` for a raw
  `filter.advanced` or `query.cond` the slots set themselves). `drug` is a list of names, `drug_class` an object
  of `source` (EPC, MoA, ATC) and exactly one of `name` or `id`, `phase` and `status` lists of the registry's
  enum values, `study_type` one value, dates YYYY-MM-DD; a name or condition class holding a double quote is
  refused, since it is quoted in the query.
- Resolution reads answers already fetched: `answers` maps each RxNav request, written as one URL line
  (`lookup_url`, the key task 3 can put in `next.json`), to its `[status, body]`. `lookups_needed(request,
  answers)` names the requests still needed, round by round (the release, `version.json`, first whenever any
  is needed): a class, the requested one or an ATC class an entailed crosswalk row names, is first confirmed
  by byName (with the source's class type: EPC, MOA, ATC1-4) or byId, and only then are its members asked
  (classMembers; EPC under DAILYMED has_epc, MoA under MEDRT has_moa, ATC under ATC), because RxClass answers
  `{}` both for an unknown class id and for a class with no member. A named
  drug's identity follows `lookup_axes`' chain (rxcui by exact name, properties, related ingredients); a member
  is already an RxNorm concept, and only a member that is not an ingredient (a PIN) asks its ingredients.
- Names (`drug_names`): the name asked; RxNorm's concept name when it resolves and differs; and, for a salt, a
  brand or another form of one ingredient, that ingredient's name, each with its source. A combination is
  never searched by one of its ingredients. A name RxNorm does not hold (or holds more than once) is searched
  as asked, with its code; a failed or malformed answer stops the scope (`name_lookup_failed`,
  `name_malformed`), never a name searched alone.
- The join: the names of one slot are joined by OR, the slots by AND (`request.JOIN`, in every scope). Forms:
  `AREA[InterventionName]"<name>"`, `AREA[Phase]X` and `AREA[OverallStatus]X` as OR groups,
  `AREA[StudyType]X`, `AREA[StartDate]RANGE[from|MIN,to|MAX]`, `condition` as the registry's `query.cond`,
  raw parameters beside them. The forms sample.py had not verified (`request.NEW_FORMS`) were tried live on
  2026-11-01 (`tests/request_query_forms.json`; `tests/test_request_live.py`, opt-in).
- Deviation, the condition class, pending the founder's ruling: emitted as sample.py's verified form,
  `(AREA[ConditionMeshTerm]"X" OR AREA[ConditionAncestorTerm]"X")`, not the ancestor alone. An ancestor is
  never the trial's own term, so the ancestor alone misses every trial tagged with the descriptor itself: for
  "Lung Neoplasms", 6,499 trials by ancestor, 11,763 by term or ancestor (2026-11-01).
- Pending the founder's ruling, "other names": a drug's other names are RxNorm's (its concept's name, and a
  salt's, brand's or other form's ingredient's); the registry's `AREA[InterventionOtherName]` is not emitted (a
  new form, untried live). Every RxClass member is expanded, DIRECT and INDIRECT (a member of a narrower class,
  as RxClass states it, kept with its relation): the EPC Kinase Inhibitor's 14 INDIRECT members include
  cetuximab, panitumumab, pertuzumab, ramucirumab, trastuzumab and margetuximab; the MoA Kinase Inhibitors'
  153 include bevacizumab and its biosimilars. A PIN member (a salt, or a biosimilar such as
  bevacizumab-awwb) is searched by its ingredient's name too, so a biosimilar widens to its reference
  product's name.
- The mechanism: `mechanism_rows` matches a crosswalk target apart from case; only a row whose relation
  `entails_membership` is expanded, into its ATC class's members; every other row is listed with its relation.
  No present row entails membership, so every mechanism stops today as `mechanism_not_entailed` (or
  `mechanism_not_in_crosswalk`) with no lookup made. Open for the founder: `narrower_than` (the target within
  the class) entails a target drug's membership of the class, but expanding the class then takes in members
  that are not of the target; `broader_than` would give only target drugs, though not all of them.
- The scope (`resolve_scope`): `code` (`refused`, `unresolved`, `awaiting_lookups`, `resolved`), the request's
  `check`, `join`, every slot with its clause, every expansion with its source, request, code and the RxNav
  `release`, `lookups`, `pending`, `stops` ([slot, code, detail]: `class_not_found`, `class_ambiguous` with the
  candidates, `class_source_mismatch`, `class_lookup_failed`, `class_malformed`, `mechanism_not_in_crosswalk`,
  `mechanism_not_entailed` with the rows, `no_members`, `members_lookup_failed`, `members_malformed`,
  `name_lookup_failed`, `name_malformed`, `name_not_quotable`, `query_<check_query code>`, `query_too_long`) and,
  only when resolved, `query`. Any stop stops the scope, whatever is still pending, so no registry query is
  sent for a scope that is short. A `*_lookup_failed` stop is final for those answers: to retry, the caller
  drops the failed answer and asks `lookups_needed` again (task 3.1); the other stops are RxNav's answer.
- The release, as built: `answers` is keyed by request, and version.json is one request, so the release is
  asked once, in the first round, and stamped on every expansion of later rounds without being re-read; the
  scope says so (`release_basis`, `request.RELEASE_BASIS`). Detecting a release change between rounds (asked
  again after the last round, refused on a change, as the registry's snapshot is) is task 3.1's, since only
  the run folder holds the rounds. Deviation: a release RxNav fails to state or states malformed stops
  nothing; it is kept as its code with the version "" on every expansion, as `classes.lookup_axes` keeps the
  axes asked without one.
- Measured 2026-11-01: the registry answers a URL of 8,185 characters and refuses one of 8,234 with HTTP 414. A
  query whose parameters, as `urlencode(query, quote_via=quote)` writes them (letters, digits, `_.-~` and `/`
  kept, every other byte as %XX), exceed `request.QUERY_LIMIT` (7,000) stops as `query_too_long`; the measure
  is no shorter than the URL sent (4,163 for the EPC Kinase Inhibitor query, whose whole URL as sent was
  3,919): the MoA class Kinase Inhibitors (194 members) does; the EPC Kinase Inhibitor (81 members)
  resolves and was answered (13,534 trials). Splitting a long query is for the step protocol (3.1).

## Risks / Trade-offs

- [App capabilities change] → `doctor` measures the session rather than assuming the vendor; the relay mode
  needs only the agent's ability to fetch a URL to a file and run Python.
- [Large scopes in relay mode mean many fetches] → pages of 1,000 IDs first, then records in batches by
  `filter.ids`; the scope is shown before the pull so the user can narrow it.
- [A class expansion missing a member] → the scope is in the record and the workbook; the class source and its
  release are named.
