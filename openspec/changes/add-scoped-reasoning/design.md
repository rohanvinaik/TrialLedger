# Design — add-scoped-reasoning

## Context

See proposal.md. Sources: the founder's decisions of 2026-10-31 (paraphrased there and in
`docs/THEORY_OF_THE_CASE.md`); two Codex readings the same day (the epistemic model, then Claude's draft rulings
on the setting relations), both by the SquishOS consultation recipe, model only; the harmonizing project's
`symbolic_healing.py` (cross-field constraint graph; the organism gates admissible values) and `shadow_ledger.py`
(evidence scope: SAMPLE, BACKGROUND, METHOD_ONLY, HOST_SYSTEM). Measurements are on the 487 NSCLC development
trials and establish nothing about other populations.

## Decisions

1. **Three statuses, one per derived value.** *Known*: a literal record field; a typed assertion with its span; a
   class the record states; an RxClass class, with its warrant (the request, the RxClass release date, the class
   ids); or a strict rule's conclusion from known premises. *Interpolated*: a default's conclusion, or anything a
   strict rule derives from an interpolated premise. *Proposed*: a proposal's suggested narrowing, shown alone. A
   value with a known and an interpolated derivation is known; overruling one default leaves another's support
   standing. Who answered a review question (an expert or a model, as the founder specified) is provenance, not a
   status; an answer can overrule a default, and a contradiction with known evidence stays visible.
2. **Rule kind is not approval.** `kind ∈ {strict, default, proposal}`; approval and the basis are metadata. A
   strict rule is one whose positive premises and explicit definitions entail the conclusion; stating a defeater
   does not make a default strict, and failing to find one proves nothing.
3. **Scoped assertions.** Premises read assertions, each with: modality (required, permitted, excluded), time
   (current at enrollment, historical), the branch of a disjunction and the cohort it belongs to, and, for an
   intervention, its role (tested, comparator, background, supporting procedure). A strict conclusion holds for a
   trial only when every eligible branch in scope entails it. Absence has three states: a same-scope contradiction;
   a same-scope assertion of absence (the only known negative); nothing found (at most a named default
   assumption).
4. **Indication gates the rules** (harmonizing's organism gate; revised 2026-11-01 by add-bank-coverage Decision 4:
   indication disambiguates and specializes, never suppresses an explicit eligibility mention). A coordinate of its own, resolved from the
   literal `conditions`, the record's own disease assertions in eligibility and title, and the derived MeSH as a
   lower-priority source whose disagreement is a named conflict. Each bank and relation declares the indications
   it applies to (AJCC 8th lung staging: NSCLC; the NSCLC setting vocabulary: NSCLC); outside them it is
   inapplicable, and a trial whose indication is unresolved gets `scope_unresolved`, never a negative.
5. **The setting split.** `disease_extent` (required at enrollment: early resectable, locally advanced,
   metastatic, locoregional recurrence, with branches kept), `treatment_history` (prior advanced systemic lines at
   enrollment, with the line-count convention stated: induction, completion or progression, transition), and
   `treatment_role` of each tested intervention and phase (perioperative, definitive chemoradiation,
   consolidation after chemoradiation, first-line systemic, subsequent systemic, maintenance, local consolidative,
   palliative or supportive). Strict: required metastatic disease → metastatic extent; required stage IV under
   NSCLC staging → metastatic extent; required prior advanced systemic therapy → that history; required zero prior
   advanced systemic therapy at enrollment → that absence. Defaults (repaired per Codex): first-line systemic role
   when the tested intervention is antineoplastic and systemic and the phase is first-line, with local-treatment,
   supportive-care and maintenance-phase defeaters bound to the intervention's role and arm; subsequent systemic
   role when a new regimen after progression is the tested phase, with maintenance-phase and local-consolidation
   defeaters. Proposals: resection required → perioperative role; resectable required → perioperative role;
   consolidation named → consolidation role; unresectable locally advanced or metastatic → advanced treatment.
6. **Closure.** Strict closure as now (a fixed point, order-independent, every removal with its cause). Defaults
   in declared strata, consuming strict conclusions and earlier strata; candidate defaults are evaluated together,
   their joint consequences (strict ones included) checked; a conflict suspends the implicated defaults, is
   reported and closure recomputes; a default cycle is a named unsupported status. This is a deliberately
   restricted semantics and is named so. Each removed value keeps its justifications (rule and version, premises,
   default assumptions, evidence, review answers); a correction or override recomputes the whole trial.
7. **Consumer contracts.** Strata, expectation cells, occupancy and results grouping accept known only, and keep
   definite and possible membership apart; near misses accept known and interpolated, each pair labelled with the
   weakest status it rests on; the review queue shows proposals and conflicts.
8. **Interim, until 5–6 land.** The four relations approved earlier are not strict (Codex's counterexamples, which
   Claude holds valid). They become defaults now, so the known setting rests on stated evidence alone and the
   interpolated setting carries them; the 34 disjunction misfires remain a premise-reading defect, closed by 3.
9. **Evaluation through the live path** (Codex's plan, adopted): populations in this order, each a different
   structural boundary: untouched later NSCLC Phase 3; NSCLC earlier phases; other thoracic malignancies; breast,
   prostate and colorectal; lymphoma, leukaemia and myeloma; selected non-oncology areas. Each run is a
   `trialledger resolve` with `--keep`, so its records are kept. Before a discovery wave: the code version, banks,
   rules, query, sampling and audit rubric are recorded, and outputs kept before any error is read; a change makes a
   new development version. Before a confirmation, additionally frozen: vocabularies and releases, scope and
   applicability rules, defaults and consumer contracts, the population and its exclusions, sampling weights,
   denominators, the interval method, acceptance criteria and the stopping rule, and how reviewer disagreement is
   handled. A confirmation set inspected for development is retired. Sizes: about 100 trials per population for
   discovery; about 400 randomly sampled trials per broad population for a ±5-point estimate; zero errors in n
   independent audited items bounds the error near 3/n for that sample only; rare banks get their own probability
   samples. Audits sample whole trials (so misses and abstentions are seen), scoring per bank and slot: identified,
   abstained, wrong, inapplicable, audit-unresolved; over-narrowing reported apart.
10. **Who audits** (the founder's decision, 2026-10-31, after a side reviewer noted no reviewer was named): a model
    audits, a human adjudicates. The founder places the model here as a bounded tail role (AGENTS.md's escape
    hatch): it grades TrialLedger's output and never produces it, and nothing it says enters a reading. How
    (the founder, later the same day): never a whole record; the model answers only specific, targeted questions
    the symbolic system poses, each with closed options and a bounded section envelope, through his GSE setup on
    a local Qwen; specified in `openspec/changes/add-targeted-questions`. A value it challenges goes to the
    human, whose answer is the grade. Agreement between the auditor and TrialLedger is not confirmation (their errors can coincide): a
    random sample of the agreed values, declared in advance, also goes to the human, and the auditor's own miss
    rate, with its interval, is reported beside every estimate. The auditor is a model independent of the one
    that wrote the rules (not Claude), named and versioned in the frozen plan; its prompt and rubric are frozen
    with it. The adjudicator (later the same day, the founder's decision): Claude, blind, with Codex second-reading
    a sample and every disagreement (add-targeted-questions, Decision 12); who adjudicated is recorded per grade. Sizes follow the adjudicator's capacity: the plan states, before a run, how many trials and agreed
    values the human can read and the interval width that buys.

11. **Drug-class axes beyond EPC and MoA** (the founder, 2026-10-31: structural homologs and cell type are
    missing; Codex's reading the same day, adopted). Measured live: RxClass serves ATC (level 4 gives the
    precise class EPC lacks: gefitinib and osimertinib L01EB "EGFR tyrosine kinase inhibitors" where EPC says
    "Kinase Inhibitor"; pembrolizumab L01FF), and `has_chemical_structure` (DAILYMED, FDASPL), which returned
    nothing for those three; the record carries registry-derived intervention MeSH; `DRUG_TYPES` omits GENETIC.
    Contracts: separate coordinates never merged (pharmacologic class, mechanism, ATC, structure, modality
    facets, cell properties); a class is a source assertion about a resolved entity (identity resolution first:
    combinations, salts and brands never inherit ingredient classes by an API answer alone); trial-level MeSH
    stays at trial level unless a link or warranted mapping names its drug; record-stated targets align to ATC
    by a sourced crosswalk with named relations (equivalent_to, narrower_than, broader_than, overlaps,
    unresolved), membership only when the relation entails it; structure is reported as
    `shares_structure_class(a, b, taxonomy, class, release)`, never as homology without a separate rule;
    modality is multi-faceted (antibody, conjugate, radioactive, cell, gene, vaccine function), cell properties
    separate lineage, engineering, preparation and donor relationship; every extraction keeps subject,
    property, value, polarity, scope, evidence location, rule, status and warrant, so "prior CAR-T excluded" is
    an eligibility assertion, not the intervention's modality; name-suffix guesses are interpolated at most.
    As built here (2026-11-01, a performance repair): the axes are looked up explicitly and lazily. EPC and
    MoA lookups are unchanged; the axes are asked of RxNav only by a consumer that reads them (`resolve`, whose
    JSON and design.xlsx render them) or by the explicit fill (`trialledger profile --fill-axes`, after the
    record verifies). A plain profile renders the axes classes.json holds and names the rest `not_looked_up`
    (`reading.axes_not_looked_up` names the names not asked; `reading.axes_as_looked_up`: the own name's not
    asked, nothing attributed; an alias's not asked, no class known, since the alias could make a conflict), a
    named state never read as "no class" and never aligned. The Drug Axes sheet's warrant digests both rules
    and `reading.drug_axes_view` with the `classes.py` axes rules.
12. **Eligibility coverage, not "completeness"** (the founder: an abbreviated record's silence is read as
    absence; `_ABBREVIATED` is used only in expectations.py). Separate attributes: content (empty, present),
    sectioning (sectioned, unsectioned), coverage evidence (abbreviation stated, completeness stated,
    unspecified), each with its marker's location and scope ("Key Exclusion Criteria" scopes the exclusions).
    No marker never means complete. Two named estimands: the registry statement rate (records stating /
    cohort, a point), and the full-criteria frequency, an identification interval [S/N, (S+U)/N] where S
    states it, A establishes its absence by a declared ascertainment rule, U is unresolved (empty,
    abbreviated, unspecified silence, no rule match); a threshold is met only when the lower bound reaches it,
    not met when the upper bound falls short, unresolved otherwise; mechanism signals, occupancy, expectations
    and near misses handle it at their own decision points. Before any metric is replaced, a transition report
    on the same frozen records: old value, new rate, new bounds, changed decisions and their reasons. As built
    (2026-11-01; the `design-profile` delta): no ascertainment rule is declared, so A is 0 by construction; a
    primary endpoint is not eligibility and has the statement rate only, no interval or tier; a mechanism
    signal is a statement-rate comparison over typed trials, proposed only when it holds with every
    abbreviated silence among the others counted as stating and every one in the class as lacking (the least
    favourable reading), unresolved when those silences could reverse it, not listed when it fails at every
    reading.

## Risks / Trade-offs

- [Scoped assertions need disjunction and modality parsing, a larger reader] → built bank by bank, the setting
  premises first; until then the affected rules are defaults or proposals, never strict.
- [The known setting becomes rarer in the interim] → the near-miss representation and the strata say so in
  their headers; correctness before coverage.
- [A model auditor reads trial data] → placed by the founder as a grader only; its agreements are sampled for
  human review, so a shared error is measured rather than assumed away; its consultation budget (the Codex weekly
  window stood at 96% used on 2026-10-31) bounds how many trials a wave can audit.
- [The founder is not a trial-design expert and deferred the rulings] → every ruling cites its counterexamples and
  is listed for review by a domain expert when one is available.
