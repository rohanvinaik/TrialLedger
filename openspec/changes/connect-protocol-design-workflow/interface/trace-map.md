# Producer/consumer trace map (tasks 1.3, 7.1 and the code-mapping part of 7.2)

Frozen code: a1c8d54 (`interface/freeze.md`). Fresh Serena `find_referencing_symbols` (one instance) plus `rg` and
executed traces, run on 2026-11-04. Line numbers are at a1c8d54. This was read-only: no repository file was edited
except this one. Scratch scripts and every output named below are under `~/trialledger-runs/traces-final/`
(`tracker.py`, `harness.py`, `revise.py`, `mcp_drive.py`, `codemap.py`, `consumed_report.txt`, `sha256.txt`).

## 0. Freeze check (7.1)

All 26 production files in `freeze.md` match their recorded sha256 prefix (full sha256 in `sha256.txt`). `HEAD` is
a1c8d54 and `git status` shows only the untracked `freeze.md`. `git diff --name-only 25c6bb5 HEAD -- TrialLedger` lists
exactly those 26 files. Files traced but not changed by this change, so absent from the freeze list:
`layer2/estimand_evidence.py` b8824a44574cb2f8, `layer2/dependency_evidence.py` 8dbc3986a0c3dd02,
`clinical_view.py` 37f93450e0185a17, `layer2/clinical_answers.py` 1ec5883bdec0bcf7. **Hash mismatches: none.**

## 1. Task 1.3: symbolic producer/consumer map

| Concern | Production owner | Production callers (Serena) | Duplicate or second path |
|---|---|---|---|
| Projection | `protocol_projections.project` (`layer2/protocol_projections.py`) | `design_session._run_protocol_checks:809`; `session_state._protocol_input_check:309` (placeholder standing) | **Runs twice per check**: once validate-only at admission (and again for every decision candidate, `session_state.prepare:457-461`), once for real in replay. Every alternative frame in `_run_protocol_checks` projects again. |
| Preparation | `request_preparation._protocol:738` (+ `_protocol_object:639`, `_protocol_scope:609`, `_protocol_decisions:690`) | only `_session:875`; `_session` then calls `session_state.prepare:906` to validate | prepare expands, then admission re-validates the same session (intended fresh validation). |
| Session admission | `session_state.prepare:323` | `design_session.run:1765/1772`, `prepare_revision:127/138`, `request_preparation._session:906` | The same session is prepared up to 4 times in one revision (old, next, current, previous). |
| Decision guard 1 (v1 exact-query) | `session_state._decision_inputs:240` (raises `alternative_requires_exact_entailment_query` at :268) | `session_state.prepare:432`, `request_preparation._session:835` | **Written twice**: sibling guard `design_session._decisions:583` (raises the same code at :609), called only from `replay:1151`. Both must change together. |
| Decision guard 2 (protocol_options) | `protocol_decisions.validate` | only `session_state.prepare:448`; candidates via `protocol_decisions.candidate` (:454) | v1 and protocol decisions are separate lists (`protocol_raw` vs `decisions`); no overlap. |
| Support gate | `signals.evaluate` (`layer2/signals.py`) | `service._signals:387` (**now passes claims** for `ClaimSignal`; the 00001d2 note "no claims" is obsolete), `service._design_bounds:572`, `design_bounds.bound_designs:175/249`, `interpretations._local_calculation:144/_claim_checks:258/_frame_row:294/resolve:532`, `source_assertions._local_signals:201` | none |
| Claim admission | `signals.claim_admission_state:100` | sole caller `signals._claim_admissions:170` | none |
| role_support | parsed `service._prepared_signals:345-370`; produced `protocol_projections:233/244`; echoed `signals:263-265` | read `signals._claim_admissions:134`; `design_session._semantic_record:1463` (warrant `roles`) | none |
| Budget | `design_session._child` (reservation at :255) | `_distinctions:319`, `_run_protocol_checks:828`, `replay:1107`, lambdas for `definition_checks.run` (replay:1126, `_run_protocol_checks:820`) | none |
| Budget reserve | `_reserve:385` (recurses :446) | `_child:255`; tests | `_nested_protocol_work:369` (caller `_reserve:453`) is the only protocol work formula in the session; operators own `work_reservation`. |
| Work-limit stop | `_limited_child` | `_run_protocol_checks:833` | rows are dropped later by `_protocol_answer_diff` (`not_computed`, `limited`) |
| Compact | `clinical_delivery.compact:320` | `reasoning_delivery.execute:341` | reads `response["protocol_view"]` written by `augment` |
| Delivery view | `clinical_delivery.protocol_delivery_view:86` over `protocol_view.view` (:1368) | `augment:49`; `clinical_export._protocol_rows:1190` (only for artifacts written before the current view shape) | `protocol_view.view` is the single reader of the full protocol result for compact, decision list and workbook. |
| Headline metadata | `result_semantics.metadata:979` | `service.run:1904/1924/1942`, `clinical_answers.project:328`, `result_semantics._source_assertions:819` | **Computed twice per response**: `service.run:1904` stores `response["metadata"]`, then `augment` → `clinical_answers.project:328` recomputes it. |
| Revision diff | `design_session._answer_diff` → `_protocol_answer_diff:1543` → `_check_changes:1500`, `protocol_axes:1394` | `_answer_diff` called from `run`; `protocol_axes` at :1600, :1650 | none |
| Edits path | `reasoning_delivery.edited_session:111` → `_check_protocol_objects:191` | `reasoning_delivery.revise:431`; `_check_protocol_objects` only `edited_session:184` | the `--session` path skips `edited_session` (both exercised, §2.5) |
| Export | `clinical_export._protocol_rows:1180`, `_protocol_change_row:920`, `_changes:843` | called from the export builder (`:2231`) | Export re-renders from the stored `response["protocol_view"]`; wording tables are shared with `protocol_view` (no copy). |
| Definition relations | `definition_checks.run` | `design_session.replay:1124`; `prepare` from `session_state.prepare:466` | relation rows rendered only by `protocol_view.relation_rows` (export), not by `protocol_view.view` (so absent from the compact `protocol` block) |

**Duplicated vocabularies (hand-synced, equal today).**
`protocol_decisions.CONFLICT_OUTCOMES/REPAIR_OUTCOMES/CONFLICT_CODES`, `protocol_view` lines 576-580 and
`clinical_delivery.CONFLICT_OUTCOMES` (equality checked in code: True). `result_semantics.CAUSE_KINDS` and
`protocol_view.FINDING_CODE_WORDS/UNRESOLVED_WORDS` are separate tables over overlapping codes; `dependency_*` and
`estimand_*` codes exist only in `CAUSE_KINDS`.

## 2. Task 7.1: executed producer-to-consumer traces

### 2.1 Method

For each family I ran the `describe view protocol detail full` example through (a) the CLI
(`prepare` → `reason --store --compact` → full run → `reason-result` → `reason-revise` → `reason-export`) and (b) an
initialised MCP client (`McpClient` imported read-only from `tests/test_protocol_mcp_lifecycle.py`; `mcp_drive.py`),
including `reason_revise` and `reason_export`. Field consumption was measured by wrapping the full `result` in
read-tracking dicts (`tracker.py`) and running each real consumer: `clinical_delivery.protocol_delivery_view`
(= compact `protocol`, decision list and workbook view), `clinical_answers.project` (= compact `clinical`),
`result_semantics.metadata`, `design_session._protocol_answer_diff` and the export writers
(`_decision_rows`, `_protocol_rows`, `_changes`, `_findings`, `_analysis_rows`). `consumed_report.txt` has the per-path
vector (D C M A X) for every family.

The `schedule` example is byte-identical to the main `example` (same preparation artifact). `dependencies` has no
example of its own: it is the second check of the `estimand` example, and I revised it separately.

### 2.2 Transport parity (all seven examples)

| Compared | Result |
|---|---|
| `describe view protocol detail full` result, CLI vs MCP | identical |
| canonical `/response/result/protocol`, reassembled over MCP `reason_result` vs CLI full | identical, all 7 |
| compact `protocol`, `decision_view`, `clinical` | identical, all 7 |
| `reason_revise` `answer_diff` and compact `protocol` | identical, all 7 |
| `reason_export` | complete, 4 files each |
| artifact id | **differs** (MCP runs `prepared=ID`, CLI runs the request): expected, id covers the whole payload |

### 2.3 Chains by family

Paths are relative to the full result (`R` = `/response/result`). Compact = the compact reply. Metadata kinds are
those in `response.metadata.findings[*].kind`.

| Family | Producer field | Compact reply | Decision list / workbook | `answer_diff` | Metadata headline |
|---|---|---|---|---|---|
| schedule (`main`, `decisions`) | `R/protocol/checks[*]/children[*]/signals[*]/claim_admission[*]/{outcome,effective_outcome,admission,application,finding_status}`; windows from `children[*]/request/signals[*]/data/{permitted,available,nominal}` and `result/result/signals[*]/value/{feasible,claims[*]/uncovered}` | `protocol.checks[*]`, `protocol.findings[*]` (class `repair_choice`/`claim_unsettled`), `protocol.canonical_ref=/response/protocol_view` | sheets Protocol findings, Schedule of assessments (columns Nominal target, Permitted window, Collection availability, Feasible window, Full-coverage gap, Nominal outcome), Protocol synopsis; decision list "Schedule of assessments" | `protocol_checks[*].changes[{claim,field}]` over the five `CHANGE_FIELDS` | `protocol_claim` (+ `signal`) |
| finite_policy | `…/claim_admission[*]` rows for coverage, prohibition, termination; witnesses at `result/result/signals[*]/value/claims[*]` | `protocol.findings[*]` class `conflict` with `witness` | Protocol findings (column Example trace), decision list Findings | `changes[{claim: prohibition, field: effective_outcome}]` | `protocol_claim` conflict, `signal` conflict |
| binomial_design | `result/result/signals[*]/value/{n,critical_count,p0,p1,null_rejection_probability,power}`, `…/value/assumptions`, roles | `protocol.checks[*]`; model assumptions in `protocol_view/checks[*]/models` | sheet Model assumptions, decision list "Model assumptions" | `changes[{signal,field in BINOMIAL_RETAINED}]` | `protocol_claim` satisfied, `signal` |
| external_method | `R/protocol/objects[*]/data/{definition,inputs,missing}`; no signal is produced (`claims: []`) | `protocol.findings[*]` class `not_computed`, `check.code: null` | Protocol findings "Not computed (whole check)"; Protocol adoption | **only** `axes: [scope_model]` (version), `changes: []`; edits to `inputs`/`missing` are not named in any row | **none**: `metadata.kind: inspection`, `findings: []` (see F4) |
| estimand | `result/result/signals[*]/value/requirements[*]/{relevance,collection_alignment,actual_input}` and blockers | `protocol.findings[*]` class `signal_finding`; `clinical.findings[*]` kinds `estimand_relevance`, `estimand_collection_alignment`, `estimand_actual_input` | Protocol findings; decision list "Open items" | `changes[{signal,field: blockers}]` (a plan mismatch surfaces through `blockers`); a linked-object edit without a blocker change shows `support`+`scope_model`, `changes: []` | `signal`, `estimand_relevance`, `estimand_collection_alignment`, `estimand_actual_input` |
| dependencies | `…/signals[*]/{code,calculation_code,blockers}` | `protocol.checks[*].code` | Protocol findings (claim column `dependencies`) | `changes[{signal,field in code,calculation_code,blockers}]` | `signal` |
| plan comparison | `R/protocol/decisions[*]/{disposition,alternatives[*]/{compatibility,frame,checks,replacements,candidate_digest}}` | `protocol.decisions[*]`, `protocol_view/decisions[*]/alternatives[*]/{windows,claim_outcomes,deciding_checks,statistics}` | sheet Plan comparisons (22 columns), decision list "Plan comparisons" | `protocol_decisions[*]` axes + `changes[{field: selected,disposition,compatibility}]` | `protocol_decision` (disposition mapped by `result_semantics._session_findings`) |
| definition relation | `R/definition_checks[*]/{code,blockers,observed_match,checks[*]/direction,bound_support}` | `clinical.findings[*]` kind `definition_relation` and `answer_diff.definition_checks[*]` (**not** in the compact `protocol` block) | sheet Definition relations (`protocol_view.relation_rows`), decision list | `answer_diff.definition_checks[*]` with the question/answer/support/context axes | `definition_relation` |

### 2.4 Defined-but-unconsumed outputs (no renderer reads them)

Strictly unread by the delivery view, `clinical_answers.project`, metadata, `_protocol_answer_diff` and the export
writers, in all seven families (`consumed_report.txt`):

1. `R/protocol/schema_version` (checked at admission only).
2. The retained raw child reply, `R/protocol/checks[*]/children[*]/result/{clinical,code,operation,problems,summary,
   result_digest,result_digest_scope,metadata/kind,metadata/version,result/basis,result/limits}`. It is addressable
   only through the `path` pointers in metadata findings and through `reason_result`; no renderer reads these fields.
3. `PROTOCOL_AXES[“wording”]` is never produced for a check (`changed` has no `wording` key for checks); it is produced
   only for decisions. Harmless, but the check-row `wording` axis is dead.
4. The `limited` list on `{code: not_computed}` revision rows (`design_session._protocol_answer_diff`, which snapshot
   was limited) is dropped by `_compact_change` (fields `id, code, changes, axes`) and not read by
   `_protocol_change_row`; the export wording says "in one snapshot" without naming which.
5. Read only by generic walkers (metadata, export `_analysis_rows`/`_findings`, never a protocol reader):
   `…/value/{guarantee,scope,unit,work}`, `data/{baseline,nominal,permitted,condition,assessment,availability,
   event_handling}` of non-schedule objects, and `definition_checks[*]/declaration/*/{body,resolution,basis}`.
6. `definition_checks[*]/observed_match` is not read by `design_session._definition_answer`, so an `exact_copy` →
   `differs` change with an unchanged relation code has no answer-diff axis of its own.

### 2.5 Consumers that read a field no producer sets

* **F1 (bug).** `clinical_delivery.augment:41` reads `row["code"]` for every `answer_diff` row; `_protocol_answer_diff`
  emits `{"id","change","axes"}` (no `code`) for a **new or withdrawn** check or decision. See §4.
* `_compact_change` reads `code` and so also drops `change` for those rows (the export reads `code or change`).
* Optional keys read with a default and absent in some families: `protocol_view` `/objects[*]/data/definition`
  (objects of kinds assessment, collection, policy), `answer_diff`'s `request/signals[*]/role_support` (estimand).
* Generic walkers probe `decision`, `query_decision`, `premises`, `effective_premises`, `fixed`, `warrant`, `body`,
  `proof`, `distinctions` on protocol nodes (`metadata`, `clinical_answers`, export `_findings`/`_analysis_rows`). None
  is set by a protocol producer. Benign, but those walkers treat protocol checks and decisions like analyses.

### 2.6 Revision paths exercised

Both `--session` and `--edits` (the latter for schedule and binomial; origin axis appears). Revised fields and
resulting axes: collection availability (verdict, support, scope_model; decisions disposition changes), policy
prohibition removed (verdict, support, scope_model), binomial `n`/`critical_count` (support, scope_model + four
retained fields), external-method inputs (scope_model only), estimand collection (support, scope_model),
dependency availability (verdict, support, scope_model), definition-relation threshold (question changed:
`answer_diff.definition_checks[0].axes = {question, answer, support, context: changed}`), stale adoption (checks
become `unresolved`, `binding_unresolved`), session work limit (rows `not_computed`).

## 3. Task 7.2: code mappings (`codemap.py`)

Mapped OK: all 7 `PROTOCOL_AXES` in `AXIS_WORDS`; all `change_code` rows but `absent` in export `CHANGE_WORDS`
(`absent` is unreachable: keys are drawn from the union); all 6 decision dispositions in `DISPOSITION_WORDS` and in
the `result_semantics` map; all 4 compatibilities; all 6 admission codes in `ADMISSION_WORDS` (accepted/undetermined
are not words); all 5 `RESULTS` for relation codes; all 4 `observed_match` values in `MATCH_WORDS`; all 3 relations, 2
directions; all 5 adoption codes; all schedule/policy/binomial blockers have `cause_kind` and `FINDING_CODE_WORDS`;
every claim outcome and operator signal code is in `RESULTS` with a disposition (none `unclassified`).

**Unmapped or falling to a fallback**

| Code | Where it falls | Reachable? |
|---|---|---|
| `definition_protocol_child_refused:*`, `definition_protocol_child_missing:*` | `cause_kind` → `unclassified`; finding disposition `unclassified`, `summary.dispositions {"unclassified": 1}` | **reproduced** (`max_solver_work: 150` on the definition example) |
| `projection_scope_mismatch`, `projection_scope_too_long`, `projection_collection_plan_conflict`, `projection_binding_shape`, `projection_slice_5`, `adoption_stale_version`, `session_work_limit` | no `CAUSE_KINDS` entry, **and** never routed to metadata (F4); `UNRESOLVED_WORDS` has all seven | scope_mismatch and stale reproduced; limit reproduced |
| Outcomes without `OUTCOME_WORDS`: `unknown_target`, `limit`, `covered`, `exclusive`, `clear`, `holds`, `all_paths_terminate`, `not_declared` | `outcome_words` returns the raw code; the positives have `STATIC_WORDING`, `unknown_target` has `nominal_phrase` | benign except `limit` |
| Signal codes without `OUTCOME_WORDS`: `limit`, `computed`, `consistent`, `unsupported_method` | raw code in change lines | by design |
| Open-item text (`protocol_view._open_items:1256/1265/1273`) uses the raw code: "Projection unresolved: session_work_limit.", "Finding from the estimand check: estimand_unresolved:week12." | ignores `UNRESOLVED_WORDS`/`code_words`, which the check rows and the decision-list findings do use (F5) | every protocol |
| Claim outcome `limit` (binomial) | not in `UNSETTLED` or `FAILURES`, so it would not be an open item | **latent**: the public path refuses earlier (`binomial_n_ceiling`, `binomial_rational_bit_limit` at ≥ 100-digit rationals); not reproduced |
| Raw Python text as a refusal code: `Exceeds the limit (4300 digits) for integer string conversion…` | shown as the check's refusal and `not_computed_items.code` (F2) | **reproduced** |

**Tests (read-only pytest, `-p no:cacheprovider`, no bytecode writes):**
`tests/test_discovery_examples_run.py` 94 passed; `tests/test_protocol_*.py` (39 files) 1211 passed;
`test_result_semantics.py` + `test_metadata_vocabulary.py` + `test_signals.py` 169 passed. Combined run: **1474 passed**
in 98.8 s, no failures. No test pins the F1-F5 behaviours below.

## 4. Findings to carry into the coordinator's list

* **F1 (blocks revision).** Withdrawing or adding a protocol check or decision refuses the whole revision with
  `problems: ["'code'"]` (CLI rc 2). Cause: `clinical_delivery.py:41` `Counter(row["code"] …)`. Reproduced by removing
  `dependencies-check` from the estimand session; confirmed by an in-memory patch that adds `code = change`, after
  which the revision completes with `{"code": "withdrawn"}`. Either `_protocol_answer_diff` should emit `code` for
  those rows (the established row shape) or the two readers should use `code or change`.
* **F2 (operator).** A valid binomial design (`n: 512`, `critical_count: 200`, `p0: 1/7…7` with 20 digits) hits Python's
  4300-digit integer-to-string limit. The child is refused with the raw Python message instead of the named
  `binomial_bit_limit`; the refusal text surfaces as a "code" in `not_computed_items`.
* **F3.** `definition_protocol_child_*` blockers are unclassified (§3).
* **F4.** Check-level `unresolved[*]` and external-method `not_computed` give no metadata or clinical finding. A
  session with every check not run (work limit) or an external method reports `summary.findings: 0`, `dispositions {}`
  and, for the external example, `metadata.kind: inspection`. Only the compact `protocol` block carries the state.
* **F5.** Open-item text and compact finding text use raw codes (§3).
* F6 (note). Hand-synced duplicate tables and duplicate computations (§1) are equal today; nothing enforces it.

## 5. Findings in full (repro and file:line)

R = `~/trialledger-runs/traces-final`. Paths under `TrialLedger/`. Line numbers at a1c8d54.

### F1. Withdrawing or adding a protocol check or decision refuses the whole revision
- Repro: take the estimand run artifact (`R/cli_compact_estimand.json`, `artifact.id`); remove `dependencies-check` from its session `protocol.checks` (`R/rev_session_withdraw.json`); `trialledger reason-revise --store R/cli_store --id <id> --session R/rev_session_withdraw.json` exits 2 with `problems: ["'code'"]`.
- Cause: `clinical_delivery.py:41` `Counter(row["code"] for row in changes.get(kind, []))` runs over every answer_diff kind. `layer2/design_session.py` `_protocol_answer_diff` emits `{"id","change","axes"}` (no `code`) for new/withdrawn rows (checks near :1558, decisions near :1613).
- Confirmed by an in-memory patch adding `code = change`: the revision completes with `{"code": "withdrawn"}`.
- Other readers: `clinical_export.py` `_protocol_change_row` (:922) and `code_of` (:872) use `code or change` (fine); `clinical_delivery._compact_change` (:282) copies only `id, code, changes, axes`, so it would drop `change`.
- Fix: emit `code` for those rows, or use `code or change` in every reader; pin with a test.

### F2. Binomial: a valid design hits Python's integer-to-string limit
- Repro: fetch the binomial session (`R/cli_compact_binomial_design.json`); set `efficacy-design` parameters `n: 512`, `critical_count: 200`, `p0: "1/77777777777777777777"`, `p1: "2/99999999999999999999"`; bump version with re-adoption; `reason-revise --session` (`R/big.json`, output `R/big_out_20.json`).
- Result: check `refused`; its refusal and `not_computed_items.code` are "Exceeds the limit (4300 digits) for integer string conversion; use sys.set_int_max_str_digits() to increase the limit". `binomial_bit_limit` and claim outcome `limit` are never reached.
- Site: not located (a `str(int)` on a large exact rational, past the `_estimated_bits` guard at `layer2/protocol_statistics.py:426`).
- Rationals of ~100 digits or more are refused earlier as `binomial_rational_bit_limit`, so the `limit` claim outcome was not reached; it is in neither `UNSETTLED` nor `FAILURES` (`layer2/protocol_view.py:33,35`), so by those tables it would not be an open item (unverified).

### F3. Unclassified definition-relation blockers; unmapped check-level codes
- 3a. `definition_protocol_child_refused:*` / `_missing:*` (`layer2/definition_checks.py:236`, refused near :247) are absent from `CAUSE_KINDS` (`layer2/result_semantics.py:14`); `cause_kind` (:261) returns `unclassified`, so `_session_findings` (:878) via `_row` (:359) gives `completion` and `disposition` `unclassified`. Repro: `R/run_definition_relation.json` with `session.limits.max_solver_work = 150` (`R/dr_limit_relapse.json`), `trialledger reason --request`; `summary.dispositions` is `{"unclassified": 1}`. The `_missing` variant is asserted from the code, not run. Fix: add both prefixes (refused as `computation`, missing as `translation`) and pin in `tests/test_result_semantics.py`.
- 3b. `projection_scope_mismatch`, `projection_scope_too_long`, `projection_collection_plan_conflict`, `projection_binding_shape`, `projection_slice_5`, `adoption_stale_version`, `session_work_limit` have no `CAUSE_KINDS` entry (producers `layer2/protocol_projections.py:157-158`, :467; `layer2/design_session.py:919`). `UNRESOLVED_WORDS` (`layer2/protocol_view.py:608`) has all seven. Latent only because nothing routes them to `cause_kind` (F4). Repro of the mismatch: set `scope.context.cohort = "cohort-B"` on `collection` in the `decisions` example, bump version with re-adoption (`R/mismatch.json`, `R/mismatch_out.json`).

### F4. Check-level `unresolved` and external-method `not_computed` produce no metadata or clinical finding
- Cause: `layer2/result_semantics.py` `_session_findings` (:878-935) walks only child results, protocol decisions and definition checks; it never reads `protocol.checks[*].unresolved` or `.not_computed`.
- Repro A: estimand session with `limits.max_solver_work = 200`, `reason-revise --session` (`R/lim_session.json`, `R/lim_out_200.json`): both checks `refused`, `summary.findings: 0`, `clinical.findings: []`, while `protocol.findings` has "Projection unresolved: session_work_limit." twice.
- Repro B: `trialledger reason --request R/run_external_method.json`: `metadata = {"kind": "inspection", "findings": []}`, `summary.findings: 0`, compact `protocol.findings` has a `not_computed` row.
- Fix: emit a finding per `unresolved` entry and per `not_computed` (`session_work_limit` as `computation`, `projection_*` as `translation`, `adoption_stale_version` as `premise`), or document that the headline excludes them (coordinator decision).

### F5. Raw codes in open-item text; OUTCOME_WORDS gaps
- `layer2/protocol_view.py:1256` ("Projection unresolved: {code}.") and :1273 ("Finding from the {kind} check: {code}.") use raw codes although `unresolved_words` (:656) and `code_words` (:641) exist. Visible in compact `protocol.findings[*].text` and the decision-list "Open items" (`R/cli_compact_estimand.json`, `R/lim_out_200.json`).
- `OUTCOME_WORDS` (:840-857) lacks `unknown_target`, `limit`, `covered`, `exclusive`, `clear`, `holds`, `all_paths_terminate`, `not_declared` and the signal codes `computed`, `consistent`, `unsupported_method`; `outcome_words` (:888) returns the bare code. The positives have `STATIC_WORDING` (:51) and `unknown_target` has `nominal_phrase` (:793). Mapping script: `R/codemap.py`.

### F6. Duplicate computations and hand-synced tables (equal today)
- Metadata twice per response: `layer2/service.py:1904` and `layer2/clinical_answers.py:328` (via `clinical_delivery.py:25`).
- v1 exact-query guard twice: `layer2/session_state.py:268` and `layer2/design_session.py:609`.
- Projection twice per check: `layer2/session_state.py:309` (and :457-461 per candidate) and `layer2/design_session.py:809`.
- Outcome sets copied in `layer2/protocol_decisions.py:34-39`, `layer2/protocol_view.py:576-580` and `clinical_delivery.py` (`CONFLICT_OUTCOMES`); equality checked at runtime.
- `CAUSE_KINDS` and `FINDING_CODE_WORDS/UNRESOLVED_WORDS` overlap as separate tables.

### F7. Weaker observations
- `PROTOCOL_AXES["wording"]` (`layer2/design_session.py:1391`) is never produced for checks.
- The `limited` list on `not_computed` revision rows is dropped by `_compact_change` (`clinical_delivery.py:282`) and unread by `_protocol_change_row` (`clinical_export.py:920`).
- External-method `inputs`/`missing` edits show only `scope_model` with `changes: []` (`R/rev_out_external_method.json`); an estimand linked-object edit shows `support` + `scope_model` with `changes: []` (`R/rev_out_estimand.json`).
- `definition_checks[*].observed_match` is unread by `design_session._definition_answer`.
- `result.protocol.schema_version` and the retained raw child reply fields are read by no renderer.
