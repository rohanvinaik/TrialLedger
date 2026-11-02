# The path to a complete MVP

Persisted 2026-11-02. This is the order of the remaining work from today's main to the three layer-one milestones
below and to layer two (a trial designed from that evidence). Each step names its change, its entry conditions,
its acceptance, what it may and may not claim, and the design decisions that bind it. A step is ticked only in the
commit that ticks its change's last task (add-design-conformance 4.2 tests this). Where this document and a
change's own design differ, the design governs and this document is corrected in the same commit.

## How every step is built (binding on every builder, human or agent)

- **The theory is the contract.** docs/THEORY_OF_THE_CASE.md Parts III and IV, read whole. Recognition (a word, a
  unit, a gene symbol) produces typed evidence with its span and decides nothing; meaning is assigned only by a
  named warrant (add-design-conformance design §2), for an ambiguous reading by eliminating alternatives across
  observations of distinct provenance; the same evidence is never counted twice; a default is interpolated, never
  known; a domain rule applies only within the
  indications it declares; what the sources do not decide is shown unresolved, never patched. brief-rules.md is
  carried verbatim in every build brief.
- **Gates, not memory.** The local gate (scripts/ci_local.sh, read whole) before every commit; the conformance test;
  a reviewed trace, bound to the code it reviewed, for every change to reading logic; the push gate; the same checks
  on GitHub on every push to main. Work is pushed directly to main (the founder's workflow).
- **Exposure is recorded.** The trials and runs looked at while writing or changing a rule are named in its trace.
  They may become regression tests; they cannot confirm the change. Confirmation uses data the change was not
  written on. The 2026-11-02 breadth runs are discovery evidence on this rule.
- **Remedies match the defect.** A presentation defect (a value the record holds that the workbook loses) is fixed
  in the workbook; a representation or interpretation defect (opposite thresholds grouped as one, a word read with
  the wrong referent) goes through the design; a warranted abstention (an unresolved setting the sources do not
  decide) is correct and is not "fixed".
- **Detective by its protocol** (~/Projects/SquishOS/ops/agents/reference/detective-protocol.md): one function at a
  time, the whole output read, exactly the next action it prints; only genuine pure decisions are pinned, never code
  about to be rewritten; an INCOMPLETE that names no next action is recorded as debt with its printout.
- **Independent readings.** A design change gets an independent reading (Codex model-only, SquishOS consultation
  protocol) before it is written into a change; a reading change gets one in its trace. Disagreement is resolved by
  the design documents, by lookup, or by the founder.
- **Documents describe what is built.** A promise of something not built lives only in a change's tasks or in
  add-agent-operation/documented-interface.md, never in README, AGENTS.md or SKILL.md.
- **The founder's words stay off git**; paraphrase.

## Layer one: three milestones

- **Milestone A, registry reporting:** the selected registry fields presented faithfully in the record and the
  workbook, across trial types; derived readings labelled and bounded, legacy readings marked. (Step 2.)
- **Milestone B, structural interpretation:** accepted readings derived through the designed mechanism
  (observations, candidates, bindings, eliminations, scoped assertions, checked projections), with coverage
  measured per bank and population: mentions found, complete representations, and eligibility evaluations,
  each with its recall as well as its precision (high precision on a small emitted subset does not establish
  useful coverage). (Steps 3, 6, 7, 8.)
- **Milestone C, the clinical development overview:** Milestone B plus the evidence beyond the registry record
  the reader needs: today's standard of care, adverse-event grades, assays and schedules, protocol success
  criteria, each from a named source with its status. (Step 9.)

### Step 1. add-design-conformance — the harness (entry: refine-landscape-record's conformance commits merged)
Tasks 0.1-4.2. Acceptance: the conformance test fails on each planted shortcut kind (an undeclared word list, a
decision moved into a data file, a legacy shortcut swapped at the same count, a decision without a warrant, a
stale entry); the push check refuses a reading change without a trace, or with one reviewed against other code;
the counterexamples of its design §7.4 and spec run at `trialledger landscape`; the checks run on GitHub on every
push to main. Claims: detection and accountability, bounded as its design §7 states. May not claim: that readings
are clinically right, or that the mechanism they protect exists (that is step 3).

### Step 2. refine-landscape-record — close it: Milestone A (entry: step 1's 0.1)
Open: the conformance commits (the three shortcuts and the treats-the-cancer gate removed; indication gating per
add-scoped-reasoning Decision 4; legacy readings labelled); the presentation defects of the 2026-11-02 breadth runs
(confidence level and sides written as silence, limits dropped beside a spread, the second level of denominators and
baseline populations, internal text in cells, enrollment's mixed form, a drug class missing without words, an empty
key-criteria band without words, "not stated" for a reading not produced); 5.1 the documents as built (no promise
of `design`, `edits` or an MCP `design` tool until they exist); 5.2 acceptance — the 3-, 49- and few-hundred-trial
runs and the breadth set (heart failure, type 2 diabetes, major depression, Alzheimer's, COVID-19 vaccines, a
TNF-blocker class, paediatric asthma, devices, ALS, the seeded registry-wide selection) re-run, each with the
independent preservation and reviewer checks, a findings ledger with every class disposed, the universe check, a
visual read by the lead, and performance on frozen inputs with memory traced by stage; 5.3 the release check
against the public repository; the deep gate on the exact candidate; the founder's fresh-sandbox test. Claims
(design §8): the selected registry fields preserved through record and workbook; derived readings labelled and
bounded; missing or unsupported readings visible; the assistant reaches by address what the clinician sees. May
not claim: a complete clinical interpretation; anything a legacy reading decides.

### Step 3. add-scoped-assertions — the first complete structural slice (entry: steps 1-2)
One path built end to end before the compiler is widened: source observations → candidates → bindings →
eliminations → scoped assertion → checked consumer projection → record and workbook, with observation identity,
source location, derivation ancestry, scope and supplied constraint carried in the computation
(add-design-conformance design §8), and a legacy reading typed so a consumer that requires a structural assertion
refuses it. Acceptance, demonstrated on the breadth findings as regression cases and confirmed on unseen trials: an
OR-list keeps its alternatives; a cohort-limited requirement stays cohort-limited; opposite measurement thresholds
stay distinct; a recognized word with the wrong referent establishes no clinical assertion; each perturbation
(reword, negate, change the target, remove a source, duplicate a sentence) handled without a new case-specific
rule. Claims: the mechanism works on that slice. May not claim: coverage.

### Step 4. add-agent-operation — finish (entry: step 2)
Open: 7.1 (the founder's rulings on the acceptance comparison), 3.1 (the founder's call on post-pull lookups in
relay mode), 0.1 vendor feasibility, 5.1/5.3 real agents per vendor, 6.1 `trialledger edits` (the reader's edits
read back as their own assertions). Acceptance: each vendor's agent completes a landscape from the README alone in
a fresh sandbox; edits round-trip.

### Step 5. add-coherence-engine — archive (entry: step 2)
Open: 6.2 a full gate run, 4.2 the `close` re-converge, 0.1 the live results spot check, the founder's approval of
each relation, the thresholds and the Audit sheet.

### Step 6. add-scoped-assertions — the compiler, widened (entry: step 3)
Open: 2.1-2.6 (D1 structure and D2 alternatives; D3 referents and D4 predicate identity; D5 qualifiers and D6 time;
D7 normative force and D8 applicability; D9 cohort scope and D10 definitions; D11 projection), 4.1 targeted
questions, 5.1-5.2 shadow mode and the transition report, 6.1-6.4 consumers switched one at a time and
`reading.effective_section` retired. Each compiling decision two-sign, confirmed on data it was not written on
(A3). Acceptance: the transition report on the frozen NSCLC records and the breadth set; every legacy decision
replaced; LEGACY_MAX reaches zero. Claims: readings derived by registered decision operations with their proofs.

### Step 7. add-scoped-reasoning — indication, the setting split, defaults (entry: step 6's group 2)
Open: 2.x scoped premises, 3.1-3.2 the indication coordinate (Decision 4; it absorbs `universes.py`'s assignment),
4.1-4.2 the setting split (Decision 5: disease extent, treatment history, treatment role; the role's antineoplastic
default interpolated with its defeaters), 5.x stratified defaults, 6.x evaluation through the live path by
populations (Decision 9), 7.4. Acceptance: Decision 9's discovery and confirmation waves. Claims: setting, history
and role each with its status.

### Step 8. add-bank-coverage — readings across trial types (entry: steps 6-7 for 6.1; 3.1b before 3.3)
Open: 3.1b, 3.2-3.5 general packages (labs and units, performance status across scales, prior therapy, conditions),
4.1 discovery, 5.1 and 5b.x domain packages, 6.1 contextual resolution, 7.1-7.2 confirmation and the release
manifest. Acceptance: its design's thresholds — precision (≥95% and ≥90% lower bound; abstaining over a wrong
reading) and its recall target — on confirmation batches, measured separately for mention extraction, complete
representation and eligibility evaluation. Claims: the coverage measured, per bank and population. (The breadth
runs' unread disease-defining criteria — HbA1c, MMSE, MADRS, ALSFRS, LVEF, and Karnofsky in NSCLC — are its
discovery evidence.)

### Milestone B is reached when steps 3 and 6-8 are done and their claims hold on a confirmation population.

### Step 9. add-evidence-sources — beyond the registry: Milestone C (entry: step 2; design and tasks written then)
Today's standard of care, adverse-event grades, assays and schedules, success criteria, each field first assessed
against the retained registry prose (a rule not yet reading it is step 6 or 8 work, not missing evidence).

## Layer two

### Step 10. add-design-surprise and add-targeted-questions — finish (entry: steps 6-7)
design-surprise 2.1, 3.1-3.2; targeted-questions 3.1, 4.2 (Codex's second read of the pilot), 5.x.

### Step 11. add-design-synthesis — the designer (entry: steps 6-8 and coherence's comparable results)
Founder rulings first (below); then 1.1-1.2, 2.1-2.5, 3.1-3.4 (3.3 needs step 4's edits). Acceptance per its
design. Claims: each design element marked deduced, recommended (with its trials and numbers) or chosen.

## Founder decisions on the critical path (each named in its change)

- add-agent-operation 7.1: the acceptance comparison's rulings (byte-order mark, NOT_POSTED measures, "none in the
  record" wording, the Role column's status, comparing against the registry page or its API).
- add-agent-operation 3.1: post-pull drug-class lookups in relay mode.
- add-coherence-engine: approval of each relation, the thresholds and the Audit sheet.
- add-scoped-reasoning: the ascertainment rule (when silence may be absence); gating EPC/MoA classes by identity.
- add-bank-coverage: whether "109/L" reads as 10⁹/L.
- add-design-synthesis: the output's name (design.xlsx is taken by `profile`), the command's form, and the status
  meanings of its Decision 2.
