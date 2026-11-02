# Design: refine-landscape-record

Settled 2026-11-01 from two analyses of a real run (an inventory of the record against the registry's API, and
a study of Regenesis's universe-specific rule import), Claude's reading and Codex's independent one (GPT-6.1 Sol,
model-only), which agreed on the structure; Codex's additions are adopted where marked. A further review the
same evening (an agent that traced the reporting path, ran the MCP and operation tests and opened the saved
workbook) added the search preview, the MCP migration, the compact index, the treatment-context limit, the
safety table's columns, preservation tests and two scope boundaries; each is marked "(review)". The founder's
direction is in the proposal.

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
   Presence is not preservation (review): units A and C add an independent check of registry value → record
   value → displayed cell, including nested populations, category-level denominators, comments and precision,
   and it must fail on planted defects (a measurement assigned to the wrong group, a dropped nested field).
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

Study type is kept (review): the request accepts observational studies, so the record says which each study is.

**Removed:** per-value source and link copies; exploratory measures (an exact copy of other outcomes);
standard_language (per-criterion copies of the cohort tiers); interventions' per-alias RxNav request histories
(kept in classes.json); the declared type matrix (coverage.types, the same every run); the eligibility's internal itemizing state;
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

**Addresses** (review): every workbook row carries its address in the record (a JSON pointer into
landscape.json, in the row's key column), so a person can ask the assistant about that row and the assistant
reads exactly that value.

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
| None (a non-oncology domain positively identified) | general; domain coordinates absent | "General: no domain readings apply (…why)" |
| Sources disagree, or none identifies any domain | scope unresolved, with each source's finding | "Scope unresolved — <the disagreement>", never silently absent |

The boundary (review): "general" needs positive evidence of a non-oncology domain (a condition MeSH term outside
Neoplasms, or a recognized non-oncology condition) and no oncology signal; a study whose sources yield no usable
condition at all (no MeSH, and conditions that are not diseases, such as "Progression Free Survival") is scope
unresolved, never general. Fixtures distinguish the two.

**Treatment context** (review): the setting and line read here are the trial's setting *as registered*, never
its place on today's standard of care, which needs dated, sourced context the registry does not hold; the
workbook says so wherever setting or line appears. The split of setting into disease extent, treatment history
and treatment role (add-scoped-reasoning, open) is consumed when it lands; until then the Read me names the
limitation.

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
| Read me | topic | first the search in plain words and what it found; then how to read the workbook, status meanings, what the registry does not report, the treatment-context limit; last the technical provenance (retrieval date, API version, mode and what relaying checks, code version); no raw JSON |
| Trial index | trial | compact (review): linked ID, acronym or short title, sponsor, phase, status, conditions, universe, design in short words, enrollment, start, primary endpoint (short), results posted (date) or not, publications (count, linked), countries, last update, dossier link; setting and line only where its pack applies; an unresolved value as a short label ("Unresolved"), its reason in the dossier; no cell sized by prose |
| Trial review | trial × fact | in section bands: identity, purpose and design, the brief summary, population and eligibility summary, arms and interventions with drug class, outcomes (one row each), results and safety availability with totals, flow and baseline availability, publications and documents, open questions with their reasons; each band links to its listing; detail lives in the listings |
| Eligibility | criterion | heading, role, number, text, labelled readings |
| Registered outcomes | outcome | category, measure, description, time frame, endpoint and time-point readings |
| Posted results | measure × class × category × group | population, denominator, value, spread or CI, unit, comment; long by group (units, categories and denominators differ per measure) |
| Statistical analyses | analysis | measure, compared groups, method, parameter, CI, p-value, non-inferiority |
| Baseline | measure × class × category × group | denominator, value, spread, unit |
| Participant flow | period × milestone or reason × group | count, comment |
| Groups | trial × module × group | title, description, totals |
| Safety | trial × table × term | organ system, term, then for each group G1…Gn of that trial's adverse-event module three numeric cells (affected, at risk, events), n being the most groups any trial in the run has; a trial with fewer groups leaves the extra columns blank by construction; a stat the registry does not give for a group reads "Not reported"; listed zeros kept as 0; the Groups sheet names G1…Gn per trial; the reporting period, threshold and method once per trial; unlisted events never read as zeros |
| Biomarkers | mention | words, role, rule |
| Across-trial findings | supported finding | numerator, denominator, population, limits; below the signal minimum one line, "too few trials to assess" |
| Readings | rule reading | trial, field, the words read, the rule and version, the result |
| Column dictionary | sheet × column | the API path or the rule, once |

A listing too long for one sheet continues on numbered sheets of the same columns; no row is dropped.

## 4a. What the reviewer asked for, item by item (2026-11-01)

The founder's list of what each study's report must hold (paraphrased): the patient population; the key
inclusion and exclusion criteria; the trial's line of therapy on the current standard-of-care ladder; the
clinical outcome measures with the time points assessed; the biomarkers with their time points; the anticipated
efficacy threshold; the safety signals, with adverse-event grades (what a new trial must do better than); the
exploratory biomarkers, imaging and biopsies; and standard protocol language reusable across studies in an
indication. This change answers each from the registry, or names the source a later change adds:

| Item | This change | Later (add-evidence-sources) |
|---|---|---|
| Population | eligibility, population fields; the enrolled baseline apart | |
| Key inclusion and exclusion | a "Key criteria" band in each dossier: the criteria whose readings fall in a declared set of decisive categories (performance status, biomarker selection, prior therapy and line, measurable disease, organ-function thresholds, CNS metastases, autoimmune disease and immunosuppression, HIV and hepatitis B and C, cardiac history), each verbatim with its reading; every criterion stays in Eligibility | |
| Line on today's ladder | the registered setting and line, labelled as registered | dated treatment context (labels, PDQ) under named rules |
| Outcomes and time points | registered outcomes with time-point readings | assessment schedules from publications |
| Biomarkers and time points | biomarker mentions with their words and role | assays, specimens and schedules from publications |
| Efficacy threshold | posted results and statistical analyses (including non-inferiority margins) | the protocol's stated success criterion; a planning target under a named decision rule, kept apart from observed results |
| Safety, with grade | counts per group within their reporting period and threshold | grades from publications under CTCAE, by version |
| Exploratory measures | the registry's other outcomes and biomarker mentions | assays, imaging and biopsies from publications |
| Standard protocol language | a "Standard protocol language" sheet: each criterion most comparable trials state (comparable = the same universe), with how many of how many, representative verbatim wording and its trials | template language (NIH protocol templates) kept apart from language recurring across trials |

## 5. Lookups

Ask RxNav for distinct drugs taken from the registry's structured intervention names, never arm labels; a dose
or schedule is stripped only by a named rule; identity once, then classes by RxNorm identifier; successful,
ambiguous and negative answers cached; a request-rate budget (at most 15 per second, under NLM's 20 per second
per address) enforced by spacing, plus a declared bound on requests in flight (review: a concurrency bound alone
does not bound the rate); the release asked before the first round and after the last, as now;
answers written in a fixed order, so a record's bytes never depend on the order replies arrive. A lookup that
fails stays distinct from "no class exists".

## 5a. The search preview and the assistant's interface (review)

AGENTS.md promises the person sees the resolved search before anything is gathered, but `landscape` resolves and
then retrieves in one call, and the MCP `scope` tool asks for `landscape` first. A preview step resolves the
request, writes `resolution.json`, and returns the scope with no study retrieved (a test asserts zero registry
study requests for a broad drug class); the run then executes against that fixed scope. The CLI gains
`landscape --preview`; MCP's `scope` tool previews.

MCP's `record` tool reads schema 3 (today it expects `{"value": ...}` around trial IDs and returns
`no_such_study` for a plain one), gains parts for the across-trial findings and the review questions, pages
large parts with a declared bound, and resolves a workbook row's address to its value. Tested through the MCP
interface on a schema-3 fixture.

## 6. Code shape and units

The record unit owns every call site in `landscape.py`; the universe unit exposes pure functions only.
`operate.py` (the run's control, record assembly and lookup scheduling) has one owner, the integrator: units A,
D and F expose functions and the integrator wires them (a second review, 2026-11-01). The contract commit
carries executable examples, not only names: schema-3 fixture records with hand-checked expected values
(ordinary, missing, conflicting and nested results), the exact shapes of a universe assignment, an MCP paging
response and the safety columns for trials with different group counts, so a producer and a consumer cannot
agree on the same mistake.

| Unit | Owns | Interface it provides or consumes |
|---|---|---|
| A. Record | `landscape.py` (study_extract, results/baseline/flow/AE shaping, cohort section, fields, schema) | consumes `contract.FIELDS`, `universes.assign`, `coherence.resolve(evidence, universe)` |
| B. Universes | `universes.py` (new: the universe table, `assign(study) -> Assignment`), `coherence.py` (per-universe coordinates and relations), `semantics/loader.py` (the `universes` key) | provides pure functions; edits no call site in landscape.py |
| C. Workbook | `readout.py` | consumes schema-3 records; built against fixture records made from the baseline bodies by the contract's shapes |
| D. Lookups | `classes.py`, the lookup lists in `request.py` / `reading.py` | provides the same answers, fewer requests |
| F. Preview and MCP (review) | a preview function the integrator wires into `operate.py`, `cli.py`'s landscape flags, `mcp_server.py` | consumes schema-3 records (fixture records until A lands) |
| E1. Independent checks (built from the start) | `acceptance/` and its tests: the registry → record → cell preservation checks and the reviewer's tasks, written from the contract's examples, never from the producers' code | the target units A, C and F must meet |
| E2. Documents (last) | README, AGENTS.md, SKILL.md, MCP tool descriptions, CLI help | each promise the new contract changes rewritten as built (AGENTS's "every value is an envelope", the README's evidence register line) |

Each unit: Detective converges every new pure decision; the gate before each commit; an independent review
before merge. Integration order: B and D, then A, then C and F (each switched from fixture records to A's real
output before it merges), then E2; E1's checks run at every integration. The workbook unit first renders a
sample (Read me, compact index, one full dossier, Posted results, mixed-group safety) for the integrator's
inspection before it builds the remaining sheets.

Acceptance (review), each with its expected destination, evidence and unresolved cases: compare eligibility
across selected trials (Eligibility); tell the eligible from the enrolled population (Trial review, Baseline);
find a result's analysis population and denominator (Posted results); read safety within its reporting period
(Safety, Groups); trace a biomarker to its source words (Biomarkers, Readings); ask the assistant about a
workbook row by its address and get that value (MCP).

## 7. Receipts

Baseline (build 860b17d, Python 3.14, kept at ~/tools/TrialLedger-runs/baseline-2026-11-01): three trials by
number, the workbook written and checked in 14 s at 347 MB; the 49 osimertinib phase-3 trials, 1,005 s wall,
52 s CPU, 730 MB peak, almost all of it RxNav. After the change the same two runs and a run of a few hundred
trials are measured the same way; each change is reported with its behaviour (the new contract's tests) and its
resource result (wall time, CPU, peak memory, rows per sheet, record size).

## 8. What completion claims (a third review, 2026-11-02)

This change is complete when, and claims only that: the selected registry fields are preserved through the
record and the workbook (checked independently, registry value to record value to displayed cell, on real run
folders); derived readings are labelled and bounded, each applied only where its requirements hold (membership
in a universe is not permission: the setting and line pack also needs an anticancer intervention, else its
applicability reads unresolved; unknown condition text is no evidence of any domain); missing or unsupported
readings stay visible ("No reading produced", "applicability unresolved", "not looked up", "lookup failed"); and
the assistant retrieves, by a row's address, the same evidence the clinician sees. It does not claim a
comprehensive clinical interpretation: the recurring-criteria sheet is example wording around shared elements
within a stated grouping, the starting material for standard protocol language, never established reusable
text; and three further changes carry the rest of the reviewer's list:

- add-evidence-sources: the content the registry does not hold (today's standard of care, grades, assays and
  schedules, success criteria), each field first assessed as "not yet read by a rule" or "not in the retrieved
  registry content" before a publication or label is asked;
- add-bank-coverage: the readings the rules miss (a Karnofsky performance status read as no reading);
- add-scoped-assertions: referents, normative force, temporal attachment and cohort scope (what a person is
  "ineligible for", which cohort a criterion binds); adding recognized terms does not settle these.

Acceptance, in order: the fixes of the third review; units A, C, F and E1 integrated; the MCP address task
passing through the integrated interface; preservation and the reviewer's tasks on real run folders; the
workbook read visually (long criteria, mixed groups, unresolved cases); the deep gate on the exact release
candidate; the committed package installed locally, then from the public repository; the fresh-sandbox test.
Every finding of the independent checks gets one disposition, recorded in a findings ledger kept beside the
first report so a falling count can be read (a fourth review, 2026-11-02): a workbook or record defect is fixed
and the check re-run; a reviewed display-policy change updates the contract, its examples and a negative test,
then the check re-runs; missing or contradictory source evidence is kept and shown unresolved; a deferred software
defect names the capability it affects, which the completion claim then excludes. Naming a defect does not
discharge it: the target is zero unexplained conformance failures, with source uncertainty reported apart. The
checks share only the contract's declarative display policy with the workbook, never its rendering or selection
code, and keep their own hand-checked examples and planted defects. A reading "traced" means its cited words
occur in the registry text, not that its clinical interpretation is right; readings resting on a heading or a
derivation are checked by that warrant, not by quotation. Posted-outcome group descriptions stay reachable: once
per trial and distinct group in the Groups sheet, linked from each result row.

Performance is measured twice, on frozen inputs (the saved bodies and caches) apart from live retrieval, with
the cache state, runtime and versions recorded, and memory traced to the stage that uses it, not only its peak.

## Risks

A misassigned trial loses a domain reading: the index shows each universe and its reason, and the acceptance
check names every exception. Compression can change meaning: denominators stay at their scope, groups are never
merged, zeros listed by the registry stay. Thresholded safety tables and posted results are not complete
accounts of harm or efficacy: the Read me and the Safety sheet say so. Folders written under schema 2 do not
verify under schema 3; a new run is needed.
