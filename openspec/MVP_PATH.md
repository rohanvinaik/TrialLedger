# The path to a complete MVP

Persisted 2026-11-02. This is the order of the remaining work from today's main to a complete layer one (a clinical
development reader gets a correct, legible record and workbook for clinical trials as a class) and a complete
layer two (a trial designed from that evidence). Each step names its change, its entry conditions, its acceptance,
what it may and may not claim, and the design decisions that bind it. A step is ticked only in the commit that
ticks its change's last task (add-design-conformance 4.2 tests this). Where this document and a change's own
design differ, the design governs and this document is corrected in the same commit.

## How every step is built (binding on every builder, human or agent)

- **The theory is the contract.** docs/THEORY_OF_THE_CASE.md Parts III and IV, read whole. Recognition (a word, a
  unit, a gene symbol) produces typed evidence with its span and decides nothing; meaning is assigned only by
  eliminating alternatives across independent evidence; one sentence counts once; a default is interpolated, never
  known; a domain rule applies only within the indications it declares; what the sources do not decide is shown
  unresolved, never patched (add-design-conformance; brief-rules.md is carried verbatim in every build brief).
- **Gates, not memory.** The local gate (scripts/ci_local.sh, read whole) before every commit; the conformance test
  (every lexical or data-driven decision declared and authorized); a reviewed trace for every change to reading
  logic; the push gate; once add-design-conformance 2.4 lands, the same checks required on GitHub for main.
- **Detective by its protocol** (~/Projects/SquishOS/ops/agents/reference/detective-protocol.md): one function at a
  time, the whole output read, exactly the next action it prints; only genuine pure decisions are pinned, never code
  about to be rewritten; an INCOMPLETE that names no next action is recorded as debt with its printout.
- **Independent readings.** A design change gets an independent reading (Codex model-only, SquishOS consultation
  protocol) before it is written into a change; a reading change gets one in its trace. Disagreement is resolved by
  the design documents, by lookup, or by the founder.
- **Documents describe what is built.** A promise of something not built lives only in a change's tasks or in
  add-agent-operation/documented-interface.md, never in README, AGENTS.md or SKILL.md.
- **The founder's words stay off git**; paraphrase.

## Layer one

### Step 1. add-design-conformance — the harness (entry: refine-landscape-record's conformance commits merged)
Tasks 0.1-4.2. Acceptance: the conformance test fails on each planted shortcut kind (an undeclared word list, a
data-file vocabulary, a code comparison deciding a domain, a mislabelled recognition, a stale entry); the push check
refuses a reading change without a reviewed trace; the four 2026-11-02 shortcut kinds are pinned by executable
counterexamples at `trialledger landscape`; GitHub requires the checks on main and the founder alone administers
branch protection and CODEOWNERS. Claims: detection and accountability under protected enforcement, bounded as its
design §7 states. May not claim: that readings are clinically right.

### Step 2. refine-landscape-record — close it (entry: step 1's 0.1)
Open: the conformance commits (the three shortcuts and the treats-the-cancer gate removed; indication gating per
add-scoped-reasoning Decision 4; legacy readings labelled); 5.1 the documents as built (no promise of `design`,
`edits` or an MCP `design` tool until they exist); 5.2 acceptance — the 3-, 49- and few-hundred-trial runs and the
breadth set across therapeutic areas (heart failure, type 2 diabetes, major depression, Alzheimer's, COVID-19
vaccines, a TNF-blocker class, paediatric asthma, devices, ALS, the seeded registry-wide selection), each with the
independent preservation and reviewer checks, a findings ledger with every class disposed (zero unexplained
conformance failures), the universe check, a visual read by the lead, and performance measured on frozen inputs
apart from live retrieval with memory traced by stage; 5.3 the release check against the public repository; the
deep gate on the exact candidate; the founder's fresh-sandbox test. Claims (design §8): the selected registry fields
preserved through record and workbook; derived readings labelled and bounded; missing or unsupported readings
visible; the assistant reaches by address what the clinician sees. May not claim: a complete clinical
interpretation; anything a legacy reading decides.

### Step 3. add-agent-operation — finish (entry: step 2)
Open: 7.1 (the founder's rulings on the acceptance comparison), 3.1 (the founder's call on post-pull lookups in
relay mode), 0.1 vendor feasibility, 5.1/5.3 real agents per vendor, 6.1 `trialledger edits` (the reader's edits
read back as their own assertions). Acceptance: each vendor's agent completes a landscape from the README alone in
a fresh sandbox; edits round-trip.

### Step 4. add-coherence-engine — archive (entry: step 2)
Open: 6.2 a full gate run, 4.2 the `close` re-converge, 0.1 the live results spot check, the founder's approval of
each relation, the thresholds and the Audit sheet. Archiving unblocks add-scoped-reasoning's delta specs.

### Step 5. add-scoped-assertions — the compiler (entry: steps 1-2; the real mediation boundary)
Open: 2.1-2.6 (D1 structure and D2 alternatives; D3 referents and D4 predicate identity; D5 qualifiers and D6 time;
D7 normative force and D8 applicability; D9 cohort scope and D10 definitions; D11 projection), 4.1 targeted
questions, 5.1-5.2 shadow mode and the transition report, 6.1-6.4 consumers switched one at a time and
`reading.effective_section` retired. Each compiling decision two-sign, from measured failures, confirmed on data it
was not written on (A3). Acceptance: the transition report on the frozen NSCLC records and the breadth set; every
legacy decision of add-design-conformance's LEGACY replaced; LEGACY_MAX reaches zero. Claims: readings derived by
registered decision operations with their proofs.

### Step 6. add-scoped-reasoning — indication, the setting split, defaults (entry: step 5's group 2)
Open: 2.x scoped premises, 3.1-3.2 the indication coordinate (Decision 4; it absorbs and replaces
refine-landscape-record's `universes.py` assignment), 4.1-4.2 the setting split (Decision 5: disease extent,
treatment history, treatment role; the role's antineoplastic default interpolated with its defeaters), 5.x
stratified defaults, 6.x evaluation through the live path by populations (Decision 9), 7.4. Acceptance: Decision 9's
discovery and confirmation waves. Claims: setting, history and role each with its status.

### Step 7. add-bank-coverage — readings across trial types (entry: steps 5-6 for 6.1; 3.1b before 3.3)
Open: 3.1b, 3.2-3.5 general packages (labs and units, performance status across scales, prior therapy, conditions),
4.1 discovery, 5.1 and 5b.x domain packages, 6.1 contextual resolution, 7.1-7.2 confirmation and the release
manifest. Acceptance: B7's thresholds (≥95% and ≥90% lower-bound precision; abstaining over a wrong reading) on
B8's confirmation batches. Claims: the coverage measured, per bank and population. (The Karnofsky miss of
2026-11-02 belongs here.)

### Step 8. add-evidence-sources — beyond the registry (entry: step 2; design and tasks written then)
Today's standard of care, adverse-event grades, assays and schedules, success criteria, each field first assessed
against the retained registry prose (a rule not yet reading it is step 5 or 7 work, not missing evidence).

### Layer one is complete when steps 1-7 are done and step 2's claims hold on a confirmation population.

## Layer two

### Step 9. add-design-surprise and add-targeted-questions — finish (entry: steps 5-6)
design-surprise 2.1, 3.1-3.2; targeted-questions 3.1, 4.2 (Codex's second read of the pilot), 5.x.

### Step 10. add-design-synthesis — the designer (entry: steps 5-7 and coherence's comparable results)
Founder rulings first (below); then 1.1-1.2, 2.1-2.5, 3.1-3.4 (3.3 needs step 3's edits). Acceptance per its
design. Claims: each design element marked deduced, recommended (with its trials and numbers) or chosen.

## Founder decisions on the critical path (each named in its change)

- add-agent-operation 7.1: the acceptance comparison's rulings (byte-order mark, NOT_POSTED measures, "none in the
  record" wording, the Role column's status, comparing against the registry page or its API).
- add-agent-operation 3.1: post-pull drug-class lookups in relay mode.
- add-coherence-engine: approval of each relation, the thresholds and the Audit sheet.
- add-scoped-reasoning: the ascertainment rule (when silence may be absence); gating EPC/MoA classes by identity.
- add-bank-coverage: whether "109/L" reads as 10⁹/L.
- add-design-conformance 2.4-2.5: branch protection and CODEOWNERS, which only the founder can administer.
- add-design-synthesis: the output's name (design.xlsx is taken by `profile`), the command's form, and the status
  meanings of its Decision 2.
