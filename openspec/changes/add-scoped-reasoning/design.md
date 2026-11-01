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
4. **Indication gates the rules** (harmonizing's organism gate). A coordinate of its own, resolved from the
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
    with it. The human adjudicator is the founder, or a domain expert when one is available; which, is recorded
    per grade. Sizes follow the adjudicator's capacity: the plan states, before a run, how many trials and agreed
    values the human can read and the interval width that buys.

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
