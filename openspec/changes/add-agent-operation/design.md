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

   *As built here (2026-11-01, tasks 1.1 and 1.2; `TrialLedger/landscape.py`).* Schema version "1". Every
   value a person reads is an envelope of six keys: `value`, `status`, `source` (its location in the study
   record, as `ledger.location` writes it), `rule` ("" when the value is the record's own, exactly as held;
   otherwise the named rule that read it), `note` (the ledger's absence state for a field not stated, or why a
   value is unresolved) and `link` (`links.study_link`). The record describes itself in three sections:
   `statuses` (what each status means), `envelope` (what each of those six keys means) and `fields` (each
   field's meaning, type, admitted statuses and source; its own meaning explains the type notation). The
   statuses are closed (`STATUSES`): known, interpolated (a modality read from a name stem), proposed (a
   coordinate narrowed by a proposed relation), not_stated (no value; the note is `not_reported`,
   `not_applicable` or `redacted`, never zero or no), not_posted (no results posted) and unresolved; each
   field admits only its own (`fields[...]["statuses"]`), so a posted measurement can never be not_posted and
   a planned outcome never sits under efficacy; an object value's type names its keys in order (`value(object:
   ...)`), or says the object is shown as the record holds it. Per study, the ten points are `population`;
   `inclusion`, `exclusion` (and `unsectioned`) as itemized, each atom with its effective section and element
   key; `line_of_therapy_and_setting` (setting and prior advanced lines under approved relations, and beside
   each the domain proposed relations would leave: the approved status when they do not narrow it, proposed
   when they do, unresolved when they leave no value); `outcomes` (planned: primary, secondary, other, each
   with its bank-read endpoint classes and time points); `biomarkers` (eligibility atoms; outcome and
   exploratory by the `biomarker_endpoint` class of primary/secondary and of other outcomes); `efficacy` and
   `safety` (the results state, then each posted measurement per arm and each adverse event per arm, read from
   the results section only, at-risk counts as stated and never filled from a group total);
   `exploratory_measures` (the other pre-specified outcomes); `standard_language` (each criterion's elements
   with their tier from the frequency rows over all trials; an untyped criterion has no tier, never not_met).
   The extras: sponsor, phases, overall status, study type, conditions, the three dates, enrollment, arms,
   interventions (the entry; its drug class and axes when it is an experimental drug, else unresolved; its
   modality extractions with their own status), publications (with `links.reference_role`) and documents (with
   `links.document_link`). The cohort is the profile as design.xlsx's sheets compute it, rows named by column
   (frequency and mechanism over all trials then by known setting, occupancy, near misses as written and
   aligned, structure relations, the thresholds) plus `endpoints` (each outcome type and endpoint class with
   its trials and time points); comparable posted results wait on `add-coherence-engine` 5.3. Coverage is v1's
   universe, every declared type's status (`typematrix.declared_manifest`) and each study's coordinates and
   universe status at the manifest's data timestamp. The manifest is `landscape_manifest`'s: `resolve`'s names
   (api_version, data_timestamp, study_digests, merkle_root, code_commit) with `rule_versions` (the command
   passes `RULE_VERSIONS`: schema, tool, design, derivation code root, every relation's approval) and
   `retrieval` as given. `landscape_record` refuses (ValueError) a reading whose views' digests are not the
   studies' digests, in order, so it never pairs one study with another's reading. `schema_problems` names by
   code every departure the record itself shows: a changed description; an undescribed or missing field; a
   field or value not of its type (`type_holds`: strings, integers, booleans, an object's exact keys, a
   table's exact columns; null only for not_stated or unresolved); a malformed envelope; an unknown or
   inadmissible status; no source; no link, or one not the study's own (`links.study_link` of the study's NCT
   number, which the study's own `link` must also be: a null link exempts nothing); efficacy and safety that
   disagree on the results state, a results value that is not `results_value`'s for its status, or anything
   posted while there is no results section; a posted value not from the results section; coverage rows or
   review questions of studies the record does not hold; digests or a root that disagree with the studies. It
   walks the record level by level to a declared depth, so it ends whatever it is given. It checks the record
   against the schema and against itself, never against the study records: a value changed alike everywhere it
   appears (both results states, or a study's NCT number with its link and every value's) passes it, and only
   re-deriving the record from the studies its manifest names finds that. The module reads no study
   differently from `reading.read_population`, changes no existing output, and is outside the derivation code
   root, so no warrant changes.

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

- **Decisions 4 and 5, 2026-11-01** (`TrialLedger/request.py`; `classes.class_members_request`,
  `classes.direct_members_request`, `classes.class_tree_request`, `classes.rxclass_members` and
  `classes.rxclass_tree` beside the existing RxClass lookups). The request is validated by
  `request_problems` (`not_an_object`, `empty_request`, `unknown_slot`, `malformed_value` per
  `slot_value_ok`, a start_from after the start_to, `params_<check_query code>`, and `params_conflict` for a raw
  `filter.advanced` or `query.cond` the slots set themselves). `drug` is a list of names, `drug_class` an object
  of `source` (EPC, MoA, ATC), exactly one of `name` or `id` and optionally `subclasses` ("include", the
  default; "exclude"; or a non-empty list of subclass ids to exclude), `phase` and `status` lists of the
  registry's enum values, `study_type` one value, dates YYYY-MM-DD; a name or condition class holding a double
  quote is refused, since it is quoted in the query.
- Resolution reads answers already fetched: `answers` maps each RxNav request, written as one URL line
  (`lookup_url`, the key task 3 can put in `next.json`), to its `[status, body]`. `lookups_needed(request,
  answers)` names the requests still needed, round by round (the release, `version.json`, first whenever any
  is needed): a class, the requested one or an ATC class an entailed crosswalk row names, is first confirmed
  by byName (with the source's class type: EPC, MOA, ATC1-4) or byId, and only then are its members
  (classMembers; EPC under DAILYMED has_epc, MoA under MEDRT has_moa, ATC under ATC) and its tree (classTree)
  asked, because RxClass answers `{}` both for an unknown class id and for a class with no member; then each
  subclass's own members (classMembers with trans=1); then, once `subclass_attribution` has read which members
  are searched, those members' ingredients. A named drug's identity follows `lookup_axes`' chain (rxcui by
  exact name, properties, related ingredients); a member is already an RxNorm concept, and only a member that
  is not an ingredient (a PIN) asks its ingredients.
- Names (`drug_names`, for a drug the person names): the name asked; RxNorm's concept name when it resolves
  and differs; and, for a salt, a brand or another form of one ingredient, that ingredient's name, each with
  its source. A combination is never searched by one of its ingredients. A name RxNorm does not hold (or holds
  more than once) is searched as asked, with its code; a failed or malformed answer stops the scope
  (`name_lookup_failed`, `name_malformed`), never a name searched alone. A class member's names
  (`member_names`) follow ruling 4 below.
- The join: the names of one slot are joined by OR, the slots by AND (`request.JOIN`, in every scope). Forms:
  each slot's names as `(AREA[InterventionName]X OR AREA[InterventionOtherName]X)`, X one quoted name or the
  quoted names joined by OR in parentheses (`request.name_clause`, ruling 2 below), `AREA[Phase]X` and
  `AREA[OverallStatus]X` as OR groups, `AREA[StudyType]X`, `AREA[StartDate]RANGE[from|MIN,to|MAX]`,
  `condition` as the registry's `query.cond`, raw parameters beside them. The forms sample.py had not verified
  (`request.NEW_FORMS`) were tried live on 2026-11-01 (`tests/request_query_forms.json`;
  `tests/test_request_live.py`, opt-in).
- **The rulings of 2026-11-01 on task 2.2's open points** (Claude's reading and Codex's independent one,
  with the facts measured live that day; until then the first two were built as departures pending a ruling,
  and every member, DIRECT and INDIRECT, was searched with a PIN member's ingredient):
  1. *The condition class keeps the term-or-ancestor form* (agreed): `(AREA[ConditionMeshTerm]"X" OR
     AREA[ConditionAncestorTerm]"X")`, sample.py's verified form, not the ancestor alone. An ancestor is never
     the trial's own term, so the ancestor alone misses every trial tagged with the descriptor itself: for
     "Lung Neoplasms", 6,499 trials by ancestor, 11,763 by term or ancestor.
  2. *Each drug name is searched in `AREA[InterventionName]` OR `AREA[InterventionOtherName]`* (agreed:
     sponsors put the identifying name in either field). Measured: `AREA[InterventionOtherName]"pembrolizumab"`
     1,610 of 609,551 registered studies; an unheld name 0. Pairing the areas name by name would take the
     EPC Kinase Inhibitor's query to 8,619 escaped characters, over `QUERY_LIMIT`, so the names are grouped
     inside each area, `AREA[InterventionName]("a" OR "b")`, a second new form: the registry answered the
     Kinase Inhibitor's 81 names grouped exactly as one by one (13,284 each), two names alike (184; with
     other names, 190), and the grouped name-or-other-name query in 3,505 characters (4,071 escaped; 13,723
     trials). Both forms are in `NEW_FORMS` with their date and checked by the opt-in live test (above 0 and
     below the registry total; unheld names 0, singly, as an other name and grouped; grouped equal to one by
     one); the counts are in `tests/request_query_forms.json`.
  3. *A class means the class with its subclasses, and nothing is hidden.* Measured: RxClass's INDIRECT
     members of a class are the members of its subclasses in the source's own hierarchy; classMembers without
     trans returned DIRECT and INDIRECT entries (ruxolitinib, everolimus and sirolimus carry both in one
     member's attributes, which `rxclass_members` now keeps as every relation stated, sorted), with trans=1
     the DIRECT ones only. The EPC Kinase Inhibitor's classTree lists eight subclasses (mTOR Inhibitor
     Immunosuppressant, HER2/neu Receptor Antagonist, Epidermal Growth Factor Receptor Antagonist, Janus Kinase
     Inhibitor and under it Tyrosine Kinase 2 Inhibitor, Vascular Endothelial Growth Factor Receptor 2
     Antagonist, Rho Kinase Inhibitor, Cytomegalovirus pUL97 Kinase Inhibitor); the MoA Kinase Inhibitors'
     tree holds 49 classes under it, to six levels. `rxclass_tree` reads a tree (each class under its parent,
     a class under two parents under each); `subclass_attribution` lists every subclass and gives each member
     its `via`, the subclasses whose own members (trans=1) list it as DIRECT ("trastuzumab, via HER2/neu
     Receptor Antagonist"; deucravacitinib via Tyrosine Kinase 2 Inhibitor, not Janus Kinase Inhibitor).
     `drug_class.subclasses` excludes all subclasses or the ids listed, each with every subclass under it; a
     member the class lists as DIRECT is never excluded, and one reached through several subclasses only when
     all are excluded. Excluded members stay in the scope, marked, and are not searched. Named stops:
     `subclasses_not_found`, `subclasses_lookup_failed`, `subclasses_malformed` (the tree),
     `subclass_members_lookup_failed`, `subclass_members_malformed`, `tree_not_of_class` (the tree's top is
     not the class), `subclass_not_in_class` (an id to exclude is no subclass of it) and
     `member_unattributed` (a subclass is excluded and a member that is not DIRECT has no subclass listing it,
     so whether it is excluded cannot be read; under "include" such a member is searched, its via empty). A
     subclass with no own member is no stop. With every subclass excluded the EPC Kinase Inhibitor keeps 67 of
     its 81 members (the 14 INDIRECT-only ones out; ruxolitinib, everolimus and sirolimus kept).
  4. *A precise ingredient's base name is searched only when the class itself lists that ingredient* (Codex:
     widening bevacizumab-awwb to bevacizumab would admit Avastin trials). `member_names`: a member that is not
     an ingredient (a PIN, a brand, another form) is searched by its own name; its ingredient is searched only
     as a member the class lists (the MoA Kinase Inhibitors list bevacizumab, so bevacizumab-awwb adds
     nothing), and otherwise shown as a candidate, `[name, "rxnorm_ingredient", "the ingredient of <member>
     (<tty>)"]`, in its expansion's `candidates`, not searched: the EPC Kinase Inhibitor lists dasatinib
     anhydrous and not dasatinib, so dasatinib is a candidate (measured: 1 trial names dasatinib anhydrous,
     344 dasatinib). Applied to class members only: a drug the person names is still searched by its
     ingredient's name beside its own (Keytruda with pembrolizumab, osimertinib mesylate with osimertinib), as
     before; whether the ruling extends to a named salt or biosimilar is open for the founder. Beyond the
     ruling's words, for the founder: it is applied to every member that is not an ingredient, so a brand (BN)
     or another-form member is not widened to its ingredient either; and a biosimilar member shows the identity
     code `salt` (`classes.name_identity`'s, unchanged: bevacizumab-awwb is a PIN). Measured beside
     it, for the founder, and relied on nowhere: the registry reads some names alike itself
     (`AREA[InterventionName]"Keytruda"` and `"pembrolizumab"` both 2,584), but not a biosimilar's
     ("bevacizumab-awwb" 4, "bevacizumab" 2,667).
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
  `mechanism_not_entailed` with the rows, `no_members`, `members_lookup_failed`, `members_malformed`, the
  subclass stops of ruling 3, `name_lookup_failed`, `name_malformed`, `name_not_quotable`,
  `query_<check_query code>`, `query_too_long`) and, only when resolved, `query`. A class's expansions, in
  order: `class` (the confirmation), `class_members` (each member with its relations), `class_tree`, one
  `subclass_members` per subclass, `subclass_attribution` (the rule, every subclass with whether it is
  excluded, every member with its via and whether it is searched), then one `drug_names` per searched member
  (its names and its `candidates`; a named drug's `candidates` are always empty). The subclass expansions and
  their stops are `_subclass_expansions`' (pinned with direct tests after review, 2026-11-01): the tree, each
  subclass once (one under two parents too), and the attribution only once nothing has stopped, no answer is
  pending and the class's members were found. Any stop stops the scope, whatever is still pending, so no
  registry query is sent for a scope that is short. A `*_lookup_failed` stop is final for those answers: to
  retry, the caller drops the failed answer and asks `lookups_needed` again (task 3.1); the other stops are
  RxNav's answer.
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
  is no shorter than the URL sent (4,071 for the EPC Kinase Inhibitor query under the grouped
  name-or-other-name form, whose whole URL as sent was 3,505; 4,163 and 3,919 under the first round's
  InterventionName-only form):
  the MoA class Kinase Inhibitors (194 members, 11,437 escaped) does; the EPC Kinase Inhibitor (81 members)
  resolves and was answered (13,723 trials; 13,534 in the first round). Splitting a long query is for the step
  protocol (3.1).
- **The operation, 2026-11-01 (task 4.2; `TrialLedger/operate.py`, `trialledger landscape` in `cli.py`).**
  `trialledger landscape --run DIR (--request FILE | the slot flags) [--mode direct|relay]`, the mode by
  default `doctor.report`'s. The run folder, in the order written: `request.json` (only once
  `request_problems` says ok; a folder holding another request is refused, `request_differs`); the
  resolution's RxNav answers in `lookups/` (`lookup-NNN.json`, one a request, named in `lookups.json`, never
  renamed), each request the `request.lookup_url` line split back (`lookup_request`) and fetched directly
  through `classes.http_get`, 0.2 s apart, or relayed in `next.json` in the step protocol's own shape and
  instructions (`why` rxnav_answer, `save_as` under `lookups/`); a direct answer is saved as JSON or as the
  note of its failure (`answer_bytes`) and every saved answer read back as `(200, body)` or `(0, None)`
  (`saved_answer`), as `steps.rxnav_answers` reads one, so a relayed run and a direct run read the same
  answers. After the last round RxNav's `version.json` is asked again (`lookups/release-end.json`) and
  compared (`release_check`): a change is refused (`rxnav_release_changed`, exit 1), a failed request asked
  again, a release not stated on either side recorded and refusing nothing; the scope's `release_basis`
  then says so and `release_check` holds the code and both releases. A scope whose stops are all failed
  lookups (`stop_status`) sets every failed answer aside in `lookups/dropped/` and ends 1, so the same
  command asks them again; any other stop ends 2 with its advice (`stop_advice`; `query_too_long`: narrow
  the request), joined by `scope_advice`, which tells a failed lookup beside another stop once, as asked
  again in the new run folder the changed request needs (this folder sets nothing aside, so a re-run here
  stops alike). `resolution.json` (the scope as resolved, the record's `scope`) and `scope.json` (its query,
  through `steps.open_run`, no RxNav requests) are written before any study is read; once `scope.json`
  exists the resolution is read back, never asked again. Then `steps.advance`; on complete, the reading:
  direct mode `classes.load_or_lookup_at` with the run folder's own `classes.json` and `fill_axes=True`,
  exactly as `resolve`; relay mode no answers at all, so every experimental drug's EPC and MoA classes are
  `not_looked_up` (`reading.classes_as_looked_up`, new; a drug none of whose names was ever asked, never no
  class and never lookup_failed; a class its own entry states is still read, `stated_by_record`, as for any
  drug RxClass does not classify) and its axes too (`reading.axes_as_looked_up`, as before). The manifest's
  `retrieval` (`retrieval_coverage`) states the mode, the registry's count and the studies read, whether the
  classes were looked up (direct: RxClass asked for the EPC and MoA classes of every drug, biological and
  genetic intervention, RxNav for the identity, ATC classes and structure of experimental arms' only, as
  `reading.axes_aliases` names them; relay: not, with why), and, for a filter.ids query,
  `ingest.reconcile_ids`'s accounting. A relay run's record therefore equals a direct run's (but for
  `retrieval`'s `mode` and `drug_classes`) only when no study read has an experimental arm's drug. The
  record is refused unless `landscape.schema_problems` finds nothing in the decoded bytes to be written
  (`schema_problem`); `manifest.json` then `landscape.json` are written staged and renamed, and
  a re-run that derives the same bytes writes nothing, one that derives others is refused
  (`record_differs`), the record never overwritten (`record_state`); a finished run is re-read in the mode
  its record names (`record_mode`), and the record always carries the request as `request.json` keeps it,
  so the same request given again otherwise (a file's key order, the flags) writes the same bytes. Exit
  codes (`run_exit`): 0 complete; 3 awaiting fetch; 1 failed (`lookup_failed`, `rxnav_release_changed`,
  `pull_failed`, `snapshot_changed`, `incomplete_total`; nothing written as the record; `lookup_failed` and
  `pull_failed` are resumed by the same command, the other three need a new run folder, as their words
  say); 2 every other end (the request, a scope stop, a refused body, `schema_problem`,
  `record_differs`). `landscape.xlsx` has one call site, `operate.write_book`, importing
  `TrialLedger.landscape_book.write_landscape_book` (4.3) with `.landscape.partial.xlsx` as the path and
  renaming that into place, so a run cut short leaves no partial workbook a re-run would keep; until that
  module exists it writes nothing and the run says the workbook is not built. Deviations, for the founder:
  the relay statement that classes were not looked up sits in `manifest.retrieval` (the record's retrieval
  coverage, as `landscape.py` names it), not in `coverage`, which is per-trial-type coverage from the
  supported-type matrix and whose keys `landscape.FIELDS` fixes (another unit's file); and `manifest.json`
  (the spec's) is written beside `landscape.json`, the same manifest. Changed outputs: `doctor`'s `next` for
  direct and relay now names `trialledger landscape`; a reading in which no name of an experimental drug has
  an answer now reads that drug `not_looked_up` where it read `lookup_failed` (no existing command reads one
  so: `resolve`, `profile` and `audit` ask every name), so such a drug is no longer a
  `drug_class_unresolved` review question.

## Risks / Trade-offs

- [App capabilities change] → `doctor` measures the session rather than assuming the vendor; the relay mode
  needs only the agent's ability to fetch a URL to a file and run Python.
- [Large scopes in relay mode mean many fetches] → pages of 1,000 IDs first, then records in batches by
  `filter.ids`; the scope is shown before the pull so the user can narrow it.
- [A class expansion missing a member] → the scope is in the record and the workbook; the class source and its
  release are named.
