# Design — add-coherence-engine

## Context

See proposal.md for why. The pull, the verbatim ledger, the five approved edit checks, the review and record
workbooks, warrants and `verify` are built and archived (`openspec/specs/`). The design this change implements
is `docs/THEORY_OF_THE_CASE.md` Part III, revised 2026-10-31 after a second reading of harmonizing, GSE and
TriageGeist and a Codex consultation. First population: interventional Phase 3 trials of non-small-cell lung
cancer started 2015-01-01 to 2024-12-31 (487 studies, pulled 2026-10-31 at data timestamp
2026-10-30T09:00:04). What the records showed, read whole before designing:

- Eligibility is a bulleted or numbered list under headings that vary ("Inclusion Criteria:", "Key Inclusion
  Criteria", case and colon vary), carried in the API's markdown.
- The design coordinates are stated in the criteria: setting and stage ("complete resection of Stage IB to
  IIIA", "Stage IV unresectable, recurrent or metastatic"), prior lines ("has not received any prior systemic
  therapy for first-line treatment of advanced lung cancer", "previously treated with one platinum based
  regimen ... and progression"), biomarker selection with polarity ("negative or unknown sensitizing EGFR
  mutation", "documented ALK-positive disease"), performance status, organ function ("AST and ALT >= 3 × upper
  limit of normal"), CNS metastases, and condition exclusions that track the drug (an anti-VEGF trial excludes
  hemoptysis, cavitation, GI perforation, non-healing wounds and uncontrolled hypertension).
- The registry carries no mechanism axis: intervention MeSH ancestors are chemical-structure classes
  (Taxoids, Platinum Compounds, Antibodies). RxClass, queried live, gives a cited FDA pharmacologic class
  (pembrolizumab: "Programmed Death Receptor-1 Blocking Antibody", N0000191260; bevacizumab: "Vascular
  Endothelial Growth Factor Inhibitor", N0000193543), coarse for kinase inhibitors (osimertinib: "Kinase
  Inhibitor", N0000175605).

## Goals / Non-Goals

**Goals:** the typing, coherence and profile layers over one pulled folder, demonstrated end to end on the
NSCLC population, with the residual inventory deciding which bank to widen next.

**Non-Goals:** reading publications; a dated standard-of-care table (a trial's line as its own criteria define
it is computed here; its place on today's treatment ladder needs a dated table the founder approves, a later
change); projecting coordinates into `review.xlsx`; certifying `design.xlsx` by file re-derivation (each row is
warranted; `verify` of `design.xlsx` is an open item); any model at any step.

## Decisions

1. **A separate command over a written folder.** `trialledger profile <folder>` reads `studies.json`, checks
   it with the existing `record_problems`, and writes `design.xlsx` and `classes.json`. It imports nothing
   into `workbook.py`, so the review and record workbooks' code root, and every written folder's
   verification, are unchanged. Alternative rejected: deriving inside `pull`, which re-pulls (minutes) on
   every iteration and changes the code root on every commit.
2. **Free text is typed, as its own evidence tier.** This supersedes Decision 1 of the archived review-workbook
   design. The founder's words 2026-10-31 (paraphrased: every scrap of information extracted, processed and put
   in a clear semantic category; trials are highly typed and symbolic) govern. Tiers, strongest first: a
   registry structured field (hard: what this record version states); a typed atom from the record's text (with
   its span); a cited external class; nothing else. The ledger still carries every text verbatim.
3. **Itemization is a pure decision with exact spans.** Headings are lines matching `(key )?(inclusion|
   exclusion) criteria` with optional markdown emphasis and colon, case-insensitive. Items start at a line
   whose first non-space characters are a list marker (`*`, `-`, `•`, `1.`, `1)`); an indented marker under an
   item is a sub-item kept inside its parent. Pieces plus separators reproduce the text exactly (tested on
   every record of the population). The pinned `split_eligibility` is untouched.
4. **Banks are pure functions from one criterion's text to atoms or an abstention.** An atom is
   `(bank, concept, values, params, span)`: `values` are the states the text allows (ECOG {0,1}; EGFR {negative,
   unknown}); `params` hold thresholds as written (comparator, number, unit as written). Polarity is the
   criterion's section combined with in-text negation, recorded separately so neither is lost. Authored here:
   pattern syntax and the vocabulary of surface forms (gene symbols, analyte names, scale names). Not authored
   here: any clinical fact relating one thing to another (a drug's class, a condition's link to a mechanism);
   those come from a cited source or are computed from the population and proposed. First banks: setting and
   stage, prior therapy, biomarker, performance status, organ function, CNS metastases, named conditions,
   boilerplate (consent, contraception, pregnancy, life expectancy, measurable disease, compliance).
5. **Intervention classes in three tiers.** (a) RxClass `has_epc` (DAILYMED) and `has_moa` (MEDRT) for each
   drug or biological intervention's name, then each of its other names, through the existing throttled,
   retrying session, cached in `classes.json` with the request, the date and every class id; (b) a target
   stated in the intervention or arm description ("anti-PD-1", "EGFR tyrosine kinase inhibitor") typed by a
   bank, with its span, marked record-stated; (c) unresolved. Every count grouped by class reports the trials
   with an unresolved experimental intervention (the founder's side note, 2026-10-31: code-named agents are
   most of the competitor pipeline).
6. **Coordinates and domains (first set).** `setting` ⊆ {neoadjuvant, adjuvant, perioperative,
   consolidation, advanced_first_line, advanced_previously_treated, maintenance}; `prior_advanced_lines` ⊆ {0, 1,
   2, 3+}; `selection.<gene>` ⊆ {positive, negative, unknown} (the states a trial admits) for EGFR, ALK, ROS1,
   KRAS, BRAF, MET, RET, NTRK, HER2, PD-L1; `histology` ⊆ {squamous, non_squamous}. Each starts full. Evidence
   narrows a domain only where the text or a field states the value (a typed atom is itself a stated
   coordinate value, not a relation). Relations carry inference between coordinates.
7. **Relations: approved or proposed, by the founder's law 13.** A relation is `(id, statement, reads,
   narrows, guard, basis, approval)`. None is self-approved: every relation in this change ships proposed.
   Closure runs twice, approved-only (the reported domains) and approved-plus-proposed (the proposed narrowing,
   shown beside). Closure is a fixed point over finite domains; each removal records its cause; order of
   relations cannot change the result (tested by permutation). An emptied domain is a conflict naming every
   cause. First proposed relations: prior_advanced_lines = {0} with advanced stage → advanced_first_line;
   prior_advanced_lines ⊆ {1, 2, 3+} → advanced_previously_treated; complete resection required → adjuvant
   or perioperative; a disease-free or event-free survival primary endpoint → not an advanced setting;
   an arm labelled maintenance → maintenance; required positive driver status → biomarker-selected.
8. **Agreement is not assignment** (Codex, accepted 2026-10-31). Two atoms from the same criterion are one
   piece of evidence; a domain narrows only by elimination, never by counting agreeing sources.
9. **Profile quantities kept apart** (Codex, accepted): logical state (the domains), frequency (an element's
   share of a declared denominator), association (an element's frequency within a mechanism class against the
   rest of the stratum), relevance (question-specific, left to each view). The denominator is trials whose
   eligibility was itemized and typed; untyped trials are counted and excluded. Surprisal is −log2 of the
   frequency. Strata: the folder's population, and the population by resolved setting (unresolved kept as its
   own stratum). Standard tier: ≥ 90% of a stratum (a named constant, shown in the sheet). Mechanism signals:
   2×2 counts, the frequency difference, distinct lead sponsors among supporting trials, unresolved-class
   count; offered as a proposed relation only with at least 3 supporting sponsors and 5 supporting trials
   (named constants). No p-values are computed or implied.
10. **Occupancy** counts trials per (setting, biomarker selection, experimental class) among resolved trials,
    and per cell the unresolved trials that could fall in it; a cell is `occupied`, `unknown` or `empty`
    (empty only when no unresolved trial could fall there). Infeasible cells need approved infeasibility
    relations; none exist yet, so none is reported.
11. **Comparable results.** A bank over outcome measure titles types the endpoint class (overall survival,
    progression-free survival, objective response rate, disease-free survival, event-free survival, duration
    of response); posted measurements are grouped by (endpoint class, setting, unit, measure type) and shown as
    posted with the arm and time frame. Groups never merge across any of those.
12. **Output.** `design.xlsx` sheets, as built: About (every sheet, its kind and rule), Trials, Criteria (each
    criterion with its atoms), Residual, Audit (a sample of criteria with their spans and atoms for the
    founder's review; accuracy is scored only against his review, never against labels Claude wrote),
    Coordinates, Outcomes, Results, Relations, Classes, Profile, Mechanism Signals, Occupancy; and, from
    `add-design-surprise`, Expectations, Review Queue, Near Misses and Rules. Every row carries a warrant: `computed(rule, digests…)` from
    the existing `warrants` module. The existing cell writer's exactness rules (`cells.py`) apply.
13. **Construction.** Each pure decision is written unwired, given authored intent tests for both signs from
    real criteria of the population, formatted, converged once with `detective converge --two-sign`, then
    wired, with `tests/production_path.py` extended in the same commit. A survivor that cannot be killed
    truthfully is flagged or fenced and named under Open items; a decision is not re-converged unless its code
    changes. One commit per task group.

14. **Engineering feedback applied first (2026-10-31).** (a) `warrants.semantic_source` hashes a module or a
    rule function as its syntax tree without docstrings (comments never reach the tree); registry tables stay
    byte-hashed. A docstring or comment edit no longer changes the code root, so it no longer stops earlier
    folders from verifying at HEAD; anything the interpreter would execute differently still does. (b)
    `verify_folder` runs `file_problems` first when the writer matches; a file identical, part for part, to a
    fresh write holds exactly the derived cells, so `certify` runs only for a file that differs, and its cell
    diagnostics are reported when it finds any, the file's otherwise, as before. Clean folders verify in about
    half the time.

## Risks / Trade-offs

- [Typing errors propagate to every derived count] → spans on every atom, the residual inventory, and the
  Audit sheet for the founder's review; banks abstain rather than guess.
- [RxClass misses investigational agents] → other names, record-stated targets, and unresolved counts on every
  class-grouped figure.
- [Sponsor templates and eras make associations look mechanistic] → sponsor counts, setting strata and the
  proposal-only status of every signal.
- [A single population is small for rare cells] → counts are always shown; nothing is reported as a rate
  without its numerator and denominator.
- [Network dependency at analysis time] → `classes.json` cache with request and date; a failed lookup is a
  named state, never a missing class read as "no class".

## Open Questions

- The standard share (90%) and the signal support thresholds (3 sponsors, 5 trials) are first settings, to
  be set by the founder after he sees the profile.
