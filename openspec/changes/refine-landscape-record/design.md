# Design: refine-landscape-record

Settled 2026-11-01 from two analyses of a real run (an inventory of the record against the registry's API, and
a study of Regenesis's universe-specific rule import), Claude's reading and Codex's independent one (GPT-6.1 Sol,
model-only), which agreed on the structure; Codex's additions are adopted where marked. The founder's direction
is in the proposal.

## 0. Order and the frozen contract (settled before any unit starts)

The parallel build holds together only if every unit builds against the same contract, on the same base.

1. **Base.** The finished branches land first, in this order: the push gate's secret-scan fix; the acceptance
   harness (add-agent-operation 7.1); relation-kinds (add-scoped-reasoning 1.1-1.2), which already moves
   landscape.json to schema 2 and changes the coordinate output the readout shows. This change is **schema 3**.
2. **The contract commit**, on that base, before any unit: the schema-3 field table as code
   (`TrialLedger/contract.py`), one row per field: its name, its API path (or the rule that produces it), plain
   value or reading, and its consumers (a workbook sheet and column, the assistant through the MCP `record`
   tool, or a named layer-two reader). Two tests make the founder's two principles gates:
   - **no false silence:** every API path in the table resolves in real saved bodies (the 3-trial and 49-trial
     baseline runs, and the API's own field metadata, kept as fixtures); a value the registry holds that the
     record does not carry is a failing test, never a status a reader sees;
   - **nothing nobody uses:** every field names at least one consumer, and every consumer it names exists
     (checked like `tests/test_wiring.py`'s declared table).
   The universe table (section 3) and the display dictionaries (section 4) are part of the same commit.
3. **Units**, in parallel worktrees, against the contract commit (section 6).

## 1. The record (schema 3)

| Component | Contract |
|---|---|
| Registry values | Plain JSON values, the registry's precision, units and wording kept (a registry "NA" stays "NA", with its comment) |
| Field dictionary | Field → API path template, type, label, definition; once per record (`fields`, served by MCP) |
| Study source | NCT ID, registry link, the study's digest; once per study |
| Reading | Rule and version, the words read, the result, its status, its scope; one object per reading |
| Not simply known | A value object with its status (not stated, not posted, not applicable, unresolved, proposed, interpolated) and its note |

"Not stated" means the registry record holds no value, and only that. A field the registry's API does not have
(an adverse event's grade, a visit schedule, a criterion's cohort, a biomarker's assay, specimen or timing,
planning assumptions) has no column; where a reader would look for it, the sheet says once that the registry
does not report it (Safety: "The registry's adverse-event tables report no grade").

**Added** (all present in the saved bodies; API paths in the contract table): brief title, acronym, official
title, organization's study ID, secondary IDs, NCT aliases; design (allocation, intervention model, primary
purpose, masking and who is masked, the model and masking descriptions); why stopped; first posted, results first
posted, last update; lead sponsor's class, collaborators; location countries and site count; overall officials;
DMC; brief summary and detailed description (Codex: it carries treatment schedules, rescue rules and design
rationale no structured field holds); condition and intervention MeSH terms and ancestors; participant flow;
baseline characteristics; results' population description, denominators, comments, reporting status and
statistical analyses; adverse events' frequency threshold, description and all-cause mortality comment;
available IPD and protocol links; limitations and caveats.

**Removed:** per-value source and link copies; exploratory measures (an exact copy of other outcomes);
standard_language (per-criterion copies of the cohort tiers); interventions' per-alias RxNav request histories
(kept in classes.json); the declared type matrix (coverage.types, the same every run); study type (always
interventional in the supported universe; the scope enforces it); the eligibility's internal itemizing state;
duplicate results flags; empty bookkeeping in the scope. Not wanted: submit, QC and disposition dates, facility
names and contacts, responsible party, miscellaneous info, keywords, IPD-sharing process details, export and
violation flags, document file sizes.

**Shapes** (Codex): each results-type module keeps the registry's nesting and keys its groups within the module;
groups of different modules are never matched by title.

| Module | Shape |
|---|---|
| Posted outcomes | measure (title, type, population, unit, param and dispersion type, time frame, reporting status) → denominators (group, scope, count) → classes → categories → per-group measurement (value, spread or limits, comment) |
| Analyses | per measure: compared groups, method, parameter and value, CI, p-value, non-inferiority type, comments |
| Baseline | population description, denominators, measures → classes → categories → per-group measurement |
| Participant flow | groups, recruitment and pre-assignment details, periods → milestones and withdrawal reasons → per-group counts |
| Adverse events | reporting period, threshold, vocabulary, assessment type, description once; groups with totals; serious and other tables → term (organ system, term, vocabulary) → per-group affected, at risk, events |

Registered outcomes and posted measures stay separate; a link between them is made only by a named rule.

## 2. Readings

Readings keep their rules and words. A criterion's typed reading is shown with a label ("Reading: prior
treatment mentioned"), never a slug; an untyped criterion reads "No reading produced" (which does not mean the
criterion carries no clinical information). The drug class says why it is unresolved in words (the name is not
in RxNorm; the lookup failed; not looked up in relay mode); the registry's intervention MeSH is shown beside it,
labelled as the registry's term, never as a drug class.

## 3. Universes (the Regenesis port)

From Regenesis: a universe is a declared, versioned record naming the rule packs it owns; rules outside a
universe are never applied. Regenesis has no assignment step (its caller names the universe); TrialLedger's is new.

**Membership is not permission** (Codex): assignment gives a trial its candidate domains; each pack then states
what it requires before its coordinates are computed (the setting and line-of-therapy pack requires a treatment
purpose and an oncology domain; a trial in cancer patients treating depression or preventing nausea gets none).

**Assignment** is a pure function over three named sources, each recorded with what it found:
1. condition MeSH terms and their ancestors (the registry's derived browse module);
2. the free-text conditions and the titles, matched against a declared vocabulary (13 of the 49 osimertinib
   trials and the solid-tumour basket NCT01827384 carry no condition MeSH; some conditions are not diseases:
   "Progression Free Survival", "Anticancer Treatment");
3. for a treatment trial, its interventions' MeSH ancestors (an antineoplastic agent).

| Case | Record | Trial index and dossier |
|---|---|---|
| One domain | its packs' coordinates computed | universe and the source that decided it |
| Several | the union, each reading tagged with its pack | each universe named; a conflicting reading shown as such |
| None | general; domain coordinates absent | "General: no domain readings apply (…why)" |
| Sources disagree, or none decides | scope unresolved, with each source's finding | "Scope unresolved — <the disagreement>", never silently absent |

Universes in this change: `oncology.solid` (setting, prior advanced lines, gene selection, the NSCLC relations,
each pack declaring its own requirements), `oncology.heme` (prior lines only), `general` (none). Packs live in the
existing versioned fragment loader (`semantics/loader.py`), which already refuses a missing pack; a pack's
`universes` key is written into its canonical form only when present, so the NSCLC fragment's registry version
is unchanged until it declares one. Recognition stays universal (B3): an explicit "adjuvant" or mutation mention
outside an oncology universe is listed with its words and rule; it establishes no setting and no selection.

The acceptance run on a lung-cancer search asserts that every trial whose condition sources fall under
neoplasms is in an oncology universe, each exception named in the report.

## 4. The workbook

Conventions kept: header row, filter, frozen identifying columns, stable row keys, Arial, wrapped prose, print
setup, deterministic bytes, every cell read back against its derivation. Changed (Codex): a cell is blank only
where its column cannot apply to its row by construction; a value that could exist and does not is written in
words. Codes are shown through versioned display dictionaries (Phase 1/Phase 2, Participants, Systematic
assessment), sourced to the API's enum definitions.

| Sheet | Row | Holds |
|---|---|---|
| Read me | topic | the search as run, retrieval date and API version, the mode (direct or relayed, and what relaying checks), status meanings, what the registry does not report, how to read a dossier |
| Trial index | trial | linked ID, title and acronym, sponsor and class, phase, status and why stopped, conditions, universe and why, eligible population, design, arms, enrollment, start and primary completion, primary outcomes and time frames, results posted (date) or not, results publications, countries and sites, last update, dossier link; setting and line only where its pack applies |
| Trial review | trial × fact | identity, purpose and design, population and eligibility summary, arms and interventions with drug class, outcomes (one row each), results and safety availability with totals, flow and baseline availability, publications and documents, open questions; detail lives in the listings |
| Eligibility | criterion | heading, role, number, text, labelled readings |
| Registered outcomes | outcome | category, measure, description, time frame, endpoint and time-point readings |
| Posted results | measure × class × category × group | population, denominator, value, spread or CI, unit, comment; long by group (units, categories and denominators differ per measure) |
| Statistical analyses | analysis | measure, compared groups, method, parameter, CI, p-value, non-inferiority |
| Baseline | measure × class × category × group | denominator, value, spread, unit |
| Participant flow | period × milestone or reason × group | count, comment |
| Groups | trial × module × group | title, description, totals |
| Safety | trial × table × term | organ system, term, then each group's affected / at risk (events where reported); the reporting period, threshold and method once per trial; listed zeros kept, unlisted events never read as zeros |
| Biomarkers | mention | words, role, rule |
| Across-trial findings | supported finding | numerator, denominator, population, limits; below the signal minimum one line, "too few trials to assess" |
| Readings | rule reading | trial, field, the words read, the rule and version, the result |
| Column dictionary | sheet × column | the API path or the rule, once |

A listing too long for one sheet continues on numbered sheets of the same columns; no row is dropped.

## 5. Lookups

Ask RxNav for distinct drugs taken from the registry's structured intervention names, never arm labels; a dose
or schedule is stripped only by a named rule; identity once, then classes by RxNorm identifier; successful,
ambiguous and negative answers cached; at most a fixed number of requests in flight (a declared bound, at or
under NLM's 20 per second per address); the release asked before the first round and after the last, as now;
answers written in a fixed order, so a record's bytes never depend on the order replies arrive. A lookup that
fails stays distinct from "no class exists".

## 6. Code shape and units

The record unit owns every call site in `landscape.py`; the universe unit exposes pure functions only.

| Unit | Owns | Interface it provides or consumes |
|---|---|---|
| A. Record | `landscape.py` (study_extract, results/baseline/flow/AE shaping, cohort section, fields, schema), `operate.py` record assembly | consumes `contract.FIELDS`, `universes.assign`, `coherence.resolve(evidence, universe)` |
| B. Universes | `universes.py` (new: the universe table, `assign(study) -> Assignment`), `coherence.py` (per-universe coordinates and relations), `semantics/loader.py` (the `universes` key) | provides pure functions; edits no call site in landscape.py |
| C. Workbook | `readout.py` | consumes schema-3 records; built against fixture records made from the baseline bodies by the contract's shapes |
| D. Lookups | `classes.py`, the lookup lists in `request.py` / `reading.py` | provides the same answers, fewer requests |
| E. Documents and acceptance | README, AGENTS.md, SKILL.md, MCP tool descriptions, `acceptance/` | each promise the new contract changes rewritten as built (AGENTS's "every value is an envelope", the README's evidence register line); the acceptance runs |

Each unit: Detective converges every new pure decision; the gate before each commit; an independent review
before merge. Integration order: B and D, then A, then C, then E.

## 7. Receipts

Baseline (build 860b17d, Python 3.14, kept at ~/tools/TrialLedger-runs/baseline-2026-11-01): three trials by
number, the workbook written and checked in 14 s at 347 MB; the 49 osimertinib phase-3 trials, 1,005 s wall,
52 s CPU, 730 MB peak, almost all of it RxNav. After the change the same two runs and a run of a few hundred
trials are measured the same way; each change is reported with its behaviour (the new contract's tests) and its
resource result (wall time, CPU, peak memory, rows per sheet, record size).

## Risks

A misassigned trial loses a domain reading: the index shows each universe and its reason, and the acceptance
check names every exception. Compression can change meaning: denominators stay at their scope, groups are never
merged, zeros listed by the registry stay. Thresholded safety tables and posted results are not complete
accounts of harm or efficacy: the Read me and the Safety sheet say so. Folders written under schema 2 do not
verify under schema 3; a new run is needed.
