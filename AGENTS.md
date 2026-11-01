# For agents (and humans) arriving fresh — read before proposing anything

**TrialLedger is a classical-AI project. It is not ML.** It may look like it
is "missing the model." It is not — that is the thesis. Before proposing ANY architecture,
approach, or "improvement":

1. Read `docs/THEORY_OF_THE_CASE.md` (this folder) — the design and why classical AI wins
   here. If it is still a stub, ask the founder to fill it (or fill it WITH them) before
   proposing architecture.
2. **Restate the mechanism in your own words** and have the founder confirm it. A
   correct-sounding paraphrase is not the test; the data-flow is.
3. Never reframe the symbolic / deterministic / vector-symbolic / data-geometry /
   story-understanding design as ML. Never propose a model, CNN, transformer, ensemble, or
   classifier as the default. Iterate the *encoder / data geometry / signal*, never model
   capacity.

**Four different things, never collapsed:**
- **AI** — the genus (reasoning, representation, symbolic and vector-symbolic computation).
- **ML** — one narrow, **avoidable** species (gradient-fit models).
- **Classical AI** — symbolic / vector-symbolic / deterministic. Usually the architecture here.
- **Story-understanding intelligence** — Regenesis (the founder's Python port of Winston's
  Genesis; in the MCP list as `mcp__Regenesis__*`). A distinct thing again.

**Know your own bias (this is why the gate exists).** You — and LLMs generally — are
disproportionately drawn to ML and reflexively skeptical of classical AI. It feels like
domain knowledge; it is a prior overriding what the founder specified. The tells: "this
is really ML, just small/downstream"; "you'll need a model for the hard part"; "the
deterministic part is elegant but it caps out"; using "no algorithm beats its data" to
smuggle a model back in.

**The one escape hatch:** the founder may deliberately place a small, bounded model at some
tail of a pipeline (a registration/normalization utility; a <1% candidate-selection
residual). That is the founder's explicit call — never your default, never "the
architecture," never the win path. When they ask, comply; never volunteer it.

Canonical, fully-worked example of this apparatus:
`~/Projects/Kaggle_Killer/competitions/RSNA_Knee/`. Global law: `~/Projects/SquishOS/ops/agents/global.md`
("AI is not ML — the classical-AI default"; the scaffold's original pointer, `~/.claude/CLAUDE.md`, was
retired in the 2026-10-20 purge).

---

# TrialLedger — what an agent working here must keep true

TrialLedger pulls ClinicalTrials.gov records through the API in `spec/ctg-oas-v2.yaml` and writes a folder:
`studies.json` (the records as sent, plus provenance and content addresses), `studies.csv` (the API's own
CSV), `review.xlsx` (the review workbook: the design sheets and the checks) and `record.xlsx` (every value
of every study, in the registry's categories), every cell of both warranted and certified against the
record.
`trialledger verify <folder>` re-derives a written folder. The ingestion layer and the first projection
(`openspec/specs/`, archived change `openspec/changes/archive/2026-10-31-add-review-workbook`) are built; the
coherence engine (typing, each trial's design coordinates, the cross-trial profile) is under construction in
`openspec/changes/add-coherence-engine`, declared expectations, deviations and near misses in
`openspec/changes/add-design-surprise`, the epistemic statuses, scoped assertions and indication gating in
`openspec/changes/add-scoped-reasoning`, the targeted questions a local model answers (the audit among them)
in `openspec/changes/add-targeted-questions`, and the scoped-assertion layer (eligibility as scoped constraints
with entailment and proof-bearing projections; Codex's draft reconciled) in `openspec/changes/add-scoped-assertions`, and banks for every declared trial type (registry,
packages, contextual resolution, evaluation, confirmation) in `openspec/changes/add-bank-coverage`; the agent
operation (an LLM agent pointed at the repository installs it, runs one command for a user's question, answers
from the record it writes and hands over the workbook; no hosted service; the founder's next priority) in
`openspec/changes/add-agent-operation`, and the second layer, a draft trial design built symbolically from that
record, in `openspec/changes/add-design-synthesis`; the publication parser is designed in `docs/THEORY_OF_THE_CASE.md` and
the archived change's `design.md`. The README explains the system to
its clinical readers.

## The rule this project exists for

No code here interprets, summarises or rewrites study content, and no agent does either. The founder's
first prompt names the failure this project rejects: handing trial pages to a chatbot to parse. Every
value a person reads traces to a named field of the record, or to a named rule over such fields; what
cannot be traced is shown as unresolved, never filled.

## Shape

Every decision is a pure function tagged `(pure — pinned)`, returning a named code; the shells around them
gather facts and write files. `design.md`'s code-shape table gives each module's public interface.

- `ingest.py`: the network shell (`Session`, `fetch_version`, `fetch_json_pages`, `fetch_csv_pages`,
  `pull`) and its decisions.
- `registry.py`: the registry's own names (field titles, categories, enum labels, the fields redacted for
  withheld studies), read from the vendored `/studies/metadata` and `/studies/enums` in
  `TrialLedger/registry/`.
- `ledger.py`: the record as entries (every leaf with its location and the roles its place states, through
  `node_role`; the tests hold them to an independent walk that rebuilds every record), absence and results
  states.
- `checks.py`: seventeen edit checks, each with the registry's words, its basis and its approval; their
  decisions; one gatherer per check. Only `APPROVED` (five) run; a present but malformed input raises
  `Malformed` and its check is `not_checkable`.
- `eligibility.py`, `links.py`, `cells.py`: the eligibility split; link forms and reference roles; what a
  cell can hold exactly (`cell_text_state`, `cell_number_state`, `sheet_fits`).
- `warrants.py`: digests, the Merkle root, the code root (the derivation code and registry tables),
  warrants.
- `workbook.py`: the sheets of the two books (`REVIEW`: the design sheets and the checks; `RECORD`: the
  Record sheets), the writer, `certify` (every cell and its kind of value) and `file_problems` (a file part
  for part against a fresh write).
- `record.py`: `write_record` (four files or nothing, with the digests and roots, naming a workbook over
  Google Sheets' 10 million cells), `code_commit`, `record_problems`, `verify_folder`.
- `cli.py`: `trialledger resolve NAME=VALUE ...` (the main path: a live query resolved without saving the
  records; the founder's instruction 2026-10-31), and the stored-record fallback `trialledger pull`, `verify`
  and `profile <folder>`.
- `review.py`: the review queue, what the rules cannot cleanly resolve, as typed questions with closed answer
  options for an expert or a model; nothing in it is resolved by TrialLedger (the founder, 2026-10-31).
- `expectations.py`: declared expectations, observation statuses, conditional rarity, deviation statuses.
- `nearmiss.py`: near-miss pairs, one known difference under a declared representation.
- `gates.py`: symbolic gates on the auditor's answers (a model challenge resolved by a rule the symbols can
  re-derive; each gate's provenance in `provenance.py`); `gate:mention_value` from the auditor pilot.
- `questions.py`, `transport.py`, `sample.py`, `audit.py` (`openspec/changes/add-targeted-questions`): a
  targeted question with closed options and a bounded envelope of the record's own text; a local Ollama model
  behind GSE's contract (named explicitly, digest pinned and re-verified, schema-constrained, temperature 0,
  budgets, one model loaded at a time and released after the run); a live stratified sample with a
  hash-reserved confirmation pool and a declared balance check (`trial_cells`, `holds_cell`, `cell_status`,
  `balance_rows`: phase with combined phases as written and matched in any order, intervention type, primary
  purpose; an empty registry cell asked of the registry live and filled by a labelled, seeded supplement with
  its own and its union inclusion probability; a zero-hit cell is empty only by query forms tried live,
  `VERIFIED_FORMS`, else `query_unverified`; a snapshot change raises `SnapshotChanged`); the serial audit
  loop (`trialledger sample`, `trialledger audit`), one trial at a time, its manifest's gap check
  (`text_coverage`: only whitespace between eligibility pieces; every uncovered stretch and every overlap
  named, both together) and `balance.json` beside the manifest; every manifest, question and answer row
  labelled `drawn_as` (sample or supplement); `pilot.py` and `trialledger pilot` (the seeded blind-label list
  of atom claims and the planted mutations with their known verdicts, asked of one model at a time, drawn
  from the sample's own questions, `drawn_units`, unless `--include-supplement`). The audit's question kinds,
  each one thing asked of its own unit's text, each with its rubric in `transport.RUBRICS`, its schema and its
  validation: `atom_claim`; `untyped_criterion` (the banks' concept instances, `CONCEPT_OPTIONS`, each with a
  span, or none, or out_of_taxonomy with a span, counted apart); `outcome_endpoint` and `outcome_time_point`
  on the outcome's own measure or time frame (`time_point_role`: "up to N" is a window, claimed as one; any
  other time point is unmarked and claimed only as "a time point at N"; one the frame does not state as number
  then unit is not_stated); `intervention_target` on an experimental drug's own entry. An RxClass assignment
  is never asked: before a trial is read, `run_audit` copies the RxClass answers for its drug names into the
  audit folder's `rxclass.json`, each with its retrieval time (None for an answer cached before answers
  carried one), each name once and never rewritten; the reading's has_epc classes are then checked against
  that kept copy as read back from disk (`audit.rxclass_check`: matches_artifact, differs_from_artifact or
  not_in_artifact), and a drug with no RxClass class is recorded as `rxclass_unclassed` (every query of every
  name not_found), `rxclass_not_established` (a lookup failed, a body was malformed or a name was never
  answered) or `differs_from_artifact` (the kept copy classifies it; `audit.rxclass_absence`). The model's
  identity is per question kind (`LocalModel.identity(kind)` hashes only that kind's rubric). A model answer
  never becomes a reading.
- `reading.py`: the population read once (`read_population`: each study's view, with each experimental drug's
  axes, every entry's modality and cell extractions and the trial's intervention MeSH; the known classes,
  review flags, near-miss pairs, the aligned pairs (drug classes compared by ATC, labelled `rxclass` or
  `crosswalk`) and the structure relations), the one producer that `design.py` (design.xlsx) and `symbolic.py`
  (the
  `resolve` JSON) consume. A drug's axes are read as cached: a stored-folder `profile` asks RxNav for them
  only with `--fill-axes` (once the record verifies), `resolve` always; `reading.axes_not_looked_up` names
  the names never asked and `reading.axes_as_looked_up` reads such a drug `not_looked_up`, never no class
  and never aligned; the Drug Axes sheet's warrant digests both rules and `drug_axes_view`.
- The confirmation draw (`add-bank-coverage` B8, 7.1b): `sample.pool` splits the reserved pool into
  batches 0-2; `trialledger sample --confirmation-batch N` draws from one, excluding every trial of the
  inspected populations declared with `--inspected` (`inspected_ids`, `screen_inspected`; each list kept
  with its file's sha256, `inspected_excluded` counted), refused by `batch_request` unless TrialLedger/ and
  tests/ are clean at a commit (`code_state` through `git_query`, injectable as `cli.main(git=...)`;
  `code_commit` and `code_source_digest` recorded) and unless the declared ledger `confirmation_ledger.json`
  (`sample.LEDGER_NAME` at the code's root, the only one read; injectable only as `cli.main(ledger=...)`;
  `ledger_batches`) leaves the batch unused or gives it to the same code, named by its source digest, so a
  new commit of unchanged code may re-draw; the batch is recorded there with the digest and the commit after
  the sample is written, and the ledger alone is committed (a failed commit is named, exit 1).
- The bank foundations (`add-bank-coverage` group 1), consumed by no production path yet (declared in
  `tests/test_wiring.py` with the task that will): `semantics/` (`contracts.py`: the bank contract, `Atom`,
  `Span`, `Finding`, `BankResult` and the legacy adapter; `loader.py`: predicate families, `ConceptEntry`
  with `defined_on`, fragments, `registry_problems`, `registry_flags`, `compile_registry`, `UNVERSIONED`
  and `LEGACY_FRAGMENTS`; `fragments/nsclc_legacy.py`, the seed of the existing banks' concepts, audited by
  2.1), `semantics/parsers.py` (add-bank-coverage 3.1, dormant until 3.2-3.5: `read_number`,
  `read_comparator`, `read_unit`, `read_reference`, `read_duration`, `read_window`, `read_interval`, each
  over the original criterion text into a `Parse` that is parsed, ambiguous or abstained, every value a
  string, spans half-open; a unit keeps its writing with its UCUM form or is named unmapped, a slash compound
  only of unit symbols; a reference is never a unit, and a factor after it, a number before a factor or digits
  no unit or reference reads, and a window on both sides of its anchor are abstained), and in `loader.py` the
  three refusals the parsers make possible, `unsupported_unit` (`unit_problems`), `invalid_span`
  (`example_problems`) and `nondeterministic_fragment` (`nondeterminism_problems`; every fragment file
  loaded twice, a NaN alike to a NaN), over a concept's optional `units` and `examples`; the seed's registry
  version is unchanged,
  `typematrix.py` (the supported-type axes, `study_coordinates`, `universe_status`, the manifest),
  `evaluation.py` (three levels kept apart through `at_level`; `GoldRecord` with each annotator's `Read` and
  the agreement kind; `THRESHOLDS`, `THRESHOLD_MEASURE`, `MINIMUM_DENOMINATOR` and a seeded cluster
  `BOOTSTRAP` read by `threshold_verdict`), and `provenance.py`'s `CONCEPT_AUTHORITIES`,
  `DEVELOPMENT_POPULATIONS` and `RULE_EXPOSURE`, concept provenance apart from rule provenance.
- `assertions.py` and `entail.py` (`add-scoped-assertions` 1.1, 3.1, 3.2), dormant until its 5.1: the
  `ScopedAssertion` model (`Proposition`: `Literal`, `AllOf`, `AnyOf`, `Not`, `Opaque`; no default rule,
  `UNRESOLVED_RULE` explicit and never a premise; an unknown branch position is unresolved) and entailment
  with its six results, minimal proofs and blockers, the weakest premise status, proposed never a premise.
  A negative qualified literal is NOT (base AND qualifiers); an enum set's `in`/`not_in` are membership
  variables (`not_in` holds none); a literal's time identity excludes certainty. `predicates.py`
  (`add-scoped-assertions` 1.2), dormant until its 2.1: the first predicate registry, each of the 91 seed
  concepts mapped to its predicate kind, value kind, unit and subject (the participant for all of them), the
  key the concept id itself, versioned by the mapping's SHA-256 (`VERSION`), each entry with its concept's
  authority and its fragment's rule exposure; twelve concepts are `unresolved` with their reasons
  (`UNRESOLVED`); `mapping_problems` refuses a mapping that disagrees with the concept registry, including a
  value kind reading an operand the concept does not declare; `atom_literal` is the literal a mapped atom
  becomes, a unit kept as written and never replaced by the mapping's own, an age with its lower bound alone
  not kept (the bank keeps no comparator), every non-operand param named back unread.
- The coherence engine (`openspec/changes/add-coherence-engine`), outside the review and record workbooks'
  derivation and code root: `criteria.py` (eligibility itemized into headings, criteria and prose, exact
  spans; `eligibility_coverage`: content, sectioning and each section's coverage evidence, abbreviation
  stated, completeness stated or unspecified, each marker with its piece, offsets and scope;
  `add-scoped-reasoning` Decision 12), `banks.py` (deterministic typing banks: spanned atoms or abstention;
  polarity is the section's), `coherence.py` (coordinate domains, evidence narrowing, relations all proposed,
  closure), `classes.py` (NLM RxClass, every class with its id, failures named; the drug-class axes of
  `add-scoped-reasoning` Decision 11: RxNorm identity first (ingredient, salt, brand, combination), decided by
  the intervention's own name, an alias confirming it or naming its reason (`alias_role`) but never supplying
  a concept; ATC and `has_chemical_structure`, asked only for the experimental drugs' names, each with its
  warrant and the standing of every class (known only when asserted of the own name's concept);
  `shares_structure_class`; the sourced target-to-ATC `CROSSWALK` with named relations, keyed only by targets
  the drug's own entry states of it (`own_targets`), each row with its RxClass request and retrieval date;
  trial-level intervention MeSH), `modality.py` (modality facets and cell properties from the intervention's
  own entry, every extraction with its subject, property, value, polarity, scope, location, rule and status;
  one extraction per mention; patient-history or eligibility wording is `history`, never the modality; name
  stems interpolated), `profile.py` (element keys; over every trial of a stratum, the registry statement rate
  S/N and, for an eligibility element, the full-criteria interval [S/N, (S+U)/N], a silent trial's silence
  unresolved as empty, no rule match, abbreviated or unspecified, never absent; a primary endpoint the
  statement rate only; the standard tier three-valued; mechanism associations as a statement-rate comparison
  over typed trials, proposed only when it holds with abbreviated silences read least favourably, unresolved
  when they could reverse it; occupancy), `design.py` (a reading laid out as `design.xlsx`, its Drug Axes
  sheet among them; `profile` over a folder), `symbolic.py` (a reading as the `resolve` JSON, with each
  drug's axes, the extractions, the intervention MeSH, the aligned pairs and the structure relations).
- `spec/ctg-oas-v2.yaml` and `TrialLedger/registry/*.json`: the vendored contracts;
  `tests/test_spec_contract.py` holds the code to them.

A rule's warrant commits to the code root: the Merkle root of the derivation code (`workbook.py` and every
package module it imports, followed through their imports, `__init__.py` and the registry tables;
`warrants.derivation_files`), each module hashed as its syntax tree without docstrings or comments
(`warrants.semantic_source`) and each registry table as its bytes. A docstring or comment edit changes nothing;
any change the interpreter would execute differently changes every computed warrant, so a folder written
before it no longer certifies under the new code: `verify` names the code root and the
commit that wrote the folder (`code_commit` in its provenance), at which it can be verified. A change to
`cli.py`, `ingest.py`, `record.py` or anything else the derivation does not import leaves the root, and
every folder, unchanged.

## Gate

`scripts/ci_local.sh` is the fast gate, seconds: `uv sync --locked`, ruff check, ruff format check, pytest, ty
(advisory). Run it and read its whole output before every commit. `scripts/ci_local.sh --deep` adds, in
minutes, `detective audit --two-sign --check` on every function tagged `(pure — pinned)` (the list is read
from the code under `TrialLedger/**`, subpackages included, and an audit of none fails; a tag counts only
written whole on one line with nothing else inside its parentheses, and `banks.permitted`,
`classes.rxnorm_concepts` and `classes.name_identity` still break theirs over two lines), with Detective and Wesker from the founder's local checkouts
(`~/tools/Detective`, `~/tools/Wesker`, or `DETECTIVE_ROOT`/`WESKER_ROOT`), never the copy in `.venv`, and two
vulture scans, advisory. The deep gate is not part of the regular workflow: it re-audits every pinned decision of the
repository, a whole-repo redundant mutation pass, and is run once, at the very end, as a professionalism
cleanup (the founder, 2026-11-01). A new decision is converged at write time with `detective converge
--two-sign` on that one function; that is the workflow's Detective step (the founder's instruction, 2026-10-31,
paraphrased: the local gate is a quick scan for common-sense failures, not a long slog).
`.githooks/pre-push` runs `scripts/push_checks.py hook`, which runs the gate before a push of any tree it has
not passed on, scans the pushed commits' added lines for secrets (detect-secrets; Detective's function digests in
`tests/detective/certificates.json` and the 16-hex goldens on an exact `assert result == "…"` line of a
Detective-generated `test_*_synth.py` are recognized, nothing else) and audits the locked
dependencies for known flaws (pip-audit, advisory). Install it with
`.venv/bin/python scripts/push_checks.py install`. Live calls are opt-in: `uv run pytest -m live`.

Vulture counts a function named in a table as used, so it cannot see a table entry nothing calls.
`tests/test_wiring.py` holds the wiring instead: in its own process, recording every call from before import,
`tests/production_path.py` drives what production does (a two-page pull with a retry and a value a cell cannot
hold, `verify` of the folder, `profile` of it with RxClass answering for one name and failing for another,
`profile` of a folder with no record, a live `resolve` of four studies of which two are a near-miss pair
(whose records say their exclusions are abbreviated, so the coverage markers and their review flag are
reached; with RxNav resolving an ingredient, a brand and a combination and answering ATC and structure
classes, an own name RxNorm does not hold beside a combination alias, and a genetic intervention whose entry
states a CAR-T product), `sample` over every stratum, a confirmation `sample` of batch 1 that excludes that discovery
sample (a fake git names a clean commit) and one refused for an undeclared batch, which asks the real git,
`audit` of its draw (a trial with every kind of
question, answered in each kind's schema, the RxClass answers kept in the audit folder and an assignment
checked against that kept copy; its balance check asking the registry about every empty cell and auditing the
one supplement a cell's registry IDs yield) and `pilot` over that audit with a fake local model, an audit
refused for want of a budget and one refused because its model is not installed, `verify` of an unreadable
workbook, a pull the server keeps failing), and the test fails on any function of the package that path does
not reach, except the declared ones: the twelve proposed checks' gatherers, their four helpers and the eight
decisions only they use (dormant until the founder approves them; the gatherers are derived from
`APPROVED`), the two default progress sinks the CLI overrides, and `WorkbookError`'s constructor. It also
holds every sheet to its columns, every rule of `RULE` to a lookup, and every code a decision returns to its
words.

## Detective

Run from this repo's `.venv` with the local checkouts first:
`PYTHONPATH=$HOME/tools/Detective:$HOME/tools/Wesker .venv/bin/detective ...`. Every pinned decision here
was converged with `--two-sign`, which the printed DO THIS lines omit (keep adding it). The debt the founder
accepted for decisions written in parallel or in haste (2026-10-31 and 2026-11-01) was reconciled serially on
2026-11-01, one decision at a time: every one ends COMPLETE (operator universe, modulo unproven-equivalent and
crash-only value gaps, no flag set) except the three named under Open items that Detective cannot measure.
Where converge asked for it, an outcome it ran but would not write is pinned by a hand-written test (an
exception compared as a value, a seeded draw, an object built without its constructor's check).

A new decision is written unwired, given direct-call intent tests for both signs, converged with
`--two-sign` in isolation, and only then wired into the shell. Run `ruff format` before converging, never
after: the formatter re-indents a docstring whose continuation lines all share extra indentation, which
changes the function's source and un-keys its flags (it did to `cell_text_state` on 2026-10-31). A
converge whose routed tests write workbooks (`record_problems`) needs `--deadline` above the default 300 s.

The flags and supplied inputs live in the gitignored `.detective/` on the machine that made them
(`equivalents.json`, `inputs.json`); each flag is keyed to its function's exact code, so an edit un-flags
it. The proofs, so that they survive the machine:

- `retry_delay`, five: `abs` of a value already in [0.0, 60.0] is the identity (twice); `round(x, 0)` of
  an integral float is itself; `min` argument order matters only on equality or NaN, which cannot occur
  (twice).
- `date_interval`: catching `BaseException` catches exactly `ValueError` there (only `date()`,
  `toordinal()` and `calendar.monthrange()` run, on regex-validated digits); a SWAP whose diff is empty
  exchanges the identical operands of `(exact, exact)`.
- `split_eligibility`, three: an inclusion and an exclusion heading are never the same line, so `<` and
  `<=` agree on their positions; the two `[-1]`/`[0]` mutants read a list known to hold one entry.
- `age_limits_ordered`, two: a None magnitude comes only with the absent or unparseable family, so either
  dropped disjunct is implied by the others.
- `cell_text_state`: UTF-16-LE byte lengths are even, so `len / 2` equals `len // 2`.
- `whole_count`, two: dropping the handler's `return None` falls through to the final `return None`; the
  `try` holds only `int()` on ASCII digits, which raises only ValueError, so `except BaseException` is the
  same handler.
- `record_problems`: reversing, slicing or rotating the one-element `no_digests` list leaves it unchanged.

## Open items

- Decisions added or changed 2026-10-31 and 2026-11-01 for the balance table, the gap check and the
  supplement's labelling are converged (2026-11-01), `sample.balance_rows` excepted (below). The balance
  cell queries use the
  metadata's `piece` names (`Phase`, `InterventionType`, `DesignPrimaryPurpose`) as search areas and Essie
  `NOT` for an exact phase; each form was tried live once on 2026-11-01 and returned trials (counts in
  `tests/live_query_forms.json`; an unknown area or phase value is refused with HTTP 400), and
  `sample.VERIFIED_FORMS` declares them with that date. A supplement whose record does not hold its cell is
  named (`holds_cell: false`) and fills nothing.
- `detective converge TrialLedger/coherence.py::close --two-sign` printed UNGATEABLE (mutants exceeded a step
  budget); the target was not edited to clear it. The founder's decision.
- The setting relations are being re-ruled under `openspec/changes/add-scoped-reasoning` (the founder
  deferred the ruling to Claude and Codex, 2026-10-31): the four approved earlier are not strict (each
  excludes a qualifying design), `setting` is to be split into disease extent, treatment history and
  treatment role, premises are to read scoped assertions, and an indication coordinate is to gate every
  lung-specific rule. Until task 1.1 lands, the known setting still rests on the four relations.
- Near misses (`add-design-surprise` 2.2) find no pair on the development data: their representation is known
  for 22 of 487 trials (a record-stated class counts as known, the founder's decision 2026-10-31; the
  setting is read under approved relations only). The bottleneck is the setting (71 trials have one known
  value). A stated class and an RxClass class match only as written; aligning the two vocabularies needs a
  sourced mapping. Each pair reports the lead sponsor and start year; sponsor
  lineage, geography and cohort structure, which the spec asks for, are not yet read.
- The model identity is per question kind (a technical decision the founder delegated; design.md Decision 3):
  `LocalModel.identity(kind)` hashes the protocol version, that kind's rubric alone and the inference options,
  in the shape the digest had when `atom_claim` was the only kind, so atom-claim answers cached before the
  other kinds were added are still cache hits, and a rubric added or changed for one kind invalidates only
  that kind's cached answers (the `outcome_time_point` rubric, rewritten when time points stopped being called
  scheduled, invalidated only answers of that kind).
- A partly typed criterion is not asked about what its atoms miss: `untyped_criterion` is asked only of a
  criterion with no atom, so a requirement a bank left untyped beside an atom it did type is seen by no
  question until a kind for it is designed (`add-targeted-questions` 2.2).
- Eligibility coverage (`add-scoped-reasoning` 8.1-8.3, 2026-10-31; the transition report is
  `openspec/changes/add-scoped-reasoning/transition-eligibility-coverage.md`). The abbreviation pattern moved
  to `criteria.py` unchanged so that the expectation observations would not change (none did, on the 487 NSCLC
  records); measured there and left for the founder: it misses "Other protocol-defined inclusion/exclusion
  criteria apply" (no modal verb) and two other wordings (11 records read "unspecified"), and it matches
  "include, but are not limited to" inside a criterion's list of examples (7 records read "abbreviation
  stated" on that alone; the review flag asks about each). No ascertainment rule is declared, so A is 0 by
  construction and every full-criteria upper bound is 1 where any trial is silent: the standard tier is met or
  unresolved, never not met, until the founder declares one. The completeness pattern is prior and matched
  nothing. Both patterns have `provenance.py` entries (`pattern:eligibility_abbreviated`, derived;
  `pattern:eligibility_complete`, prior). Mechanism signals are bounded against abbreviated silences only; a
  typed (itemized) trial no bank typed any criterion of stays in its mechanism group as stating nothing (the
  founder's to rule on). The `design-profile` delta's MODIFIED requirements need `add-coherence-engine`
  archived first. Its decisions are converged (2026-11-01; `flags_for` re-measured with `--isolated`, as
  converge directed), `criteria.eligibility_coverage` excepted (below).
- The drug-class axes (`add-scoped-reasoning` group 7, 2026-11-01) are rendered in the `resolve` JSON (each
  drug's axes, the extractions with their warrants, the intervention MeSH at its level, the aligned pairs and
  the structure relations) and in design.xlsx's Drug Axes sheet. EPC and MoA classes are still attached by
  RxClass's answer without the identity step (a brand still reads its ingredient's EPC), and the EPC fallback
  `stated_by_record` still reads every agent word of an intervention's description, drug names among them
  ("XB-1 given after carboplatin" states "platinum"), so the existing outputs are unchanged; gating them is a
  change of output for the founder to approve. The crosswalk has nine rows, only the targets of
  `classes.TARGET_WORDS` (no drug name keys a row); none entails membership (each is overlaps, broader_than or
  unresolved), so the `crosswalk` basis of the aligned reading gives no class yet. The pure decisions of
  `classes.py` and `modality.py` are converged (2026-11-01).
- Three decisions Detective cannot measure: `sample.balance_rows`, `criteria.eligibility_coverage` and
  `semantics.loader.fragment_from_data` end converge (and audit) INCOMPLETE with `outcome_snapshot_failed`
  (`fragment_from_data` changed again in 3.1, the units and examples keys, and still ends so).
  In its witness search Detective deep-copies each observed return (`Detective/equivalence.py`, `_outcome`);
  a synthesized argument carried into the returned value can fail that copy with TypeError, and one such
  failure stops the whole run rather than the one witness. A defect of Detective, for its own repository;
  their two-sign intent tests stand meanwhile. Six `sample.py` decisions and three others whose tag read
  "(pure — pinned; ...)" or broke over two lines are now written whole, so the deep gate sees them.
- The sample's frame runs to the present (the founder, 2026-11-01): `sample.base_query(present)`, the
  present the UTC date of the draw or `sample --present`, recorded in sample.json with the base and used by
  its audit's supplements; a sample without one (the pilot's) is read with `LEGACY_PRESENT`, 2025-12-31.
- Decided 2026-11-01: the ledger names code by its source digest, only the declared ledger is read, and a
  draw commits it (Claude's recommendation, approved); the AJCC edition stays unpinned until the oncology package (5.1) pins it
  from its source (the founder: wait), although `bank:setting` names the 8th; Claude's first settings of
  `MINIMUM_DENOMINATOR` and `BOOTSTRAP` and the annotator verdicts are accepted to start, open to review.
- Mechanism signals (the founder, 2026-11-01): every comparison that holds at some reading is listed,
  below-support and unresolved rows included; weak but present signals are shown, to be pruned when the
  expansion is done, never hidden now.
- The existing banks audited (`add-bank-coverage` 2.1, 2026-11-01; report
  `openspec/changes/add-bank-coverage/audit-existing-banks.md`). Keep or retire follows B7 rule by rule: a rule or
  branch with no reading found right is retired (it abstains); a rule whose wrong readings no narrow guard can
  separate before the shared parsers or the assertion layer is kept, its wrong readings counted. Retired, with the
  founder's assent of 2026-11-01: the performance-status single-value branch (all 8 of its NSCLC readings wrong; 8
  criteria now untyped, 7 Profile and 5 Mechanism rows of design.xlsx removed). Kept with counted defects: the age
  bank (21 of 258 NSCLC atoms invented, 1 invented and 2 incomplete of 7 on the pilot), the prior-lines progression
  rule (20 of 117), the conditions bank's criterion-wide grade (25 registry problems). `named_conditions` reads a
  window in years overlapping the age bank's span as that age, never a condition's window. The lung gates of the
  resection and histology rules suppress explicit mentions against B3 (a breast trial's resection on the pilot)
  until 5.1 and 6.1: a standing exception for the founder to accept.
- The shared parsers (`add-bank-coverage` 3.1, 2026-11-01) leave questions. For the founder: whether "109/L",
  "1012/L" or "103/uL", where the registry's text lost a superscript, are read as 10^9/L, 10^12/L or 10^3/uL
  (today no unit, and a bound before them is abstained), and how "100,000/mm3" and every other single grouping mark
  before three digits are read (ambiguous until a declared domain rule). For `contracts.py`'s owner: the span role
  `reference`, which a parse gives and `contracts.SPAN_ROLES` does not hold, and an NCT id and record version on
  `Example`, which Decision 10's fixtures cite. For 3.3, each with its source: the reference forms not held
  ("ULRR", "upper limit of reference range", "-fold ULN") and the closed set of slash-compound unit symbols
  ("beats/min", "units/kg", "cells/HPF" abstain today). `read_window` abstains on "up to N" with no direction while
  `time_point_role` reads it as a window in an outcome's time frame: 5b.1 reconciles them. A caller reads a
  comparator from its phrase's head.
- The predicate registry (`add-scoped-assertions` 1.2) fixes interpretations for the founder's ruling: per-concept
  predicate kinds not stated by Decision 2 (exposure for smoking and live vaccines; medication_use for
  immunosuppressants, anticoagulants and interacting medication; procedure_event for recent surgery and organ
  transplant; disease_attribute for measurable disease and CNS metastases), value kinds and cardinality (ECOG,
  stage and prior lines single-valued enums; extent a member set), and `FAMILY_VALUE_KINDS`. Predicate kinds the
  vocabulary lacks (an undertaking, a capability, availability, study participation, a treatment role) leave their
  concepts unresolved.
- Comparable posted results (`add-coherence-engine` 5.3) wait on the endpoint-class bank (2.2); the residual
  (about 70% of criteria in the NSCLC population) decides the next banks (2.1b).

- Twelve proposed edit checks wait for the founder's approval by name: `withdrawn_actual_enrollment_zero`,
  `phase_interventional_only`, `arm_interventions_declared`, `intervention_arms_defined`,
  `ae_counts_name_groups`, `ae_affected_within_at_risk`, `ae_event_within_group_total`,
  `ae_events_at_least_affected`, `ae_group_totals_within_at_risk`, `age_limits_ordered`,
  `start_before_primary_completion`, `primary_completion_before_completion`.
- Which publications the end-stage parser reads for a study without posted results is the founder's
  decision: RESULT alone misses most results papers, and DERIVED states no role.
- `detective decompose TrialLedger/cli.py::parse_query_args --apply` stops on five crash-only survivors and
  asks for them to be flagged equivalent or killed by `--input`; converge says the same five are not
  equivalence candidates. Neither repair is truthful, so the split is not applied.
- `detective audit` reports as unproven-equivalent survivors that `converge`, using the supplied inputs,
  certifies as crash-only or kills (`classify_json_page`, `classify_csv_page`, `age_magnitude`,
  `date_interval` and others); and every audit names `converge` as its next action, including right after
  a COMPLETE converge.
- `detective survey` still lists `pull` and `write_record` as I/O-bound; `extract` reports an unresolved
  interface for both and proposes nothing. Their decisions are pinned or covered by durability tests.
- vulture's only remaining findings are not islands: openpyxl attribute writes (`freeze_panes`, `font`,
  `data_type`, `hyperlink`), which openpyxl reads when it saves, and pytest's `pytestmark`.
- `trialledger verify` writes the workbook afresh to compare the file, so it takes about as long as the
  original write.
