# Tasks — add-targeted-questions

## 1. Questions and transport

- [x] 1.1 `questions.py`: the question object, the deterministic envelope (target, heading ancestry, parent stem,
      conjunction siblings, budget refusal), answer validation (one verdict per atom id, cited span inside the
      envelope, closed options)
- [x] 1.2 `transport.py`: the GSE-contract Ollama transport (explicit model, pin and verify, canonical JSON,
      schema format, temperature 0, budgets, named errors, identity) and the hash-keyed answer cache

## 2. Source manifest and audit questions

- [ ] 2.1 The source manifest of a resolved trial (eligibility pieces and gaps, outcomes, interventions)

  - 2026-10-31: the gap check is built: `audit.text_coverage` (pure — pinned) confirms that only whitespace lies
    before, between and after the pieces; each trial's manifest has an `eligibility_text` row with the result
    and one `eligibility_gap` row (offsets and text) per stretch no piece covers, and overlapping pieces are
    named.
  - 2026-11-01: overlaps and holes are reported together (`overlapping_and_uncovered`), so an overlap never
    hides uncovered text: one `eligibility_gap` row per uncovered stretch and one `eligibility_overlap` row
    per stretch read twice; every manifest row carries `drawn_as`. Left: Detective convergence of
    `text_coverage` (accepted debt), so not ticked.
- [x] 2.2 Audit question builders: `atom_claim`, `untyped_criterion` (concept instances, out_of_taxonomy),
      outcome and intervention claims; RxClass assignments checked deterministically against the kept artifact

  - 2026-10-31: built. `untyped_criterion`: one question per criterion no bank typed, options the banks'
    concept instances (`questions.CONCEPT_OPTIONS`, named as atoms name them: `biomarker:EGFR`,
    `condition:hiv`, `lab:platelets`, `ecog_ps`) plus `out_of_taxonomy`, `none`, `insufficient_context`; the
    answer is a list of instances, each with a span of the criterion itself (`validate_instances`);
    `untyped_reading` names what it says (`concept_stated`, `out_of_taxonomy`, `no_requirement`,
    `insufficient_context`); out_of_taxonomy answers are counted apart, never as errors. Outcomes:
    `outcome_endpoint` (an endpoint class on the outcome's own measure) and `outcome_time_point` (each time
    point on its own time frame, with the measure as context, in the role `time_point_role` gives it: "up to
    N" a window, claimed as one; any other statement unmarked, claimed only as "a time point at N"; not_stated
    when the frame does not state it as number then unit; wrong_role is only a window claimed as a time point
    or the reverse). Interventions: `intervention_target` (a record-stated target on the experimental drug's
    own entry: description, name as context). RxClass: before a trial is read, `run_audit` copies the RxClass
    answers for its drug names into the audit folder (`rxclass.json`), each with its retrieval time (None for
    an answer cached before answers carried one; `classes.lookup` now stamps each), each name once and never
    rewritten; the reading's has_epc classes are checked against that kept copy as read back from disk
    (`audit.rxclass_check`: matches_artifact, differs_from_artifact, not_in_artifact) and recorded in the
    manifest, never asked; a drug with no RxClass class is recorded as `rxclass_unclassed` (every query of
    every name not_found), `rxclass_not_established` (a lookup failed, a body was malformed, or a name was
    never answered) or `differs_from_artifact` (`audit.rxclass_absence`), and is never asked unless its own
    entry states a target. Each kind has its rubric, schema and validation; an outcome's or intervention's
    envelope is its own field verbatim (`field_envelope`), refused over budget. The model identity is per kind
    (`LocalModel.identity(kind)`, design.md Decision 3). Left: Detective convergence of the new decisions
    (accepted debt); the split of a `concept_stated` answer into declined and silently missed is the
    adjudicator's (5.2); an outcome with no endpoint class or time point is a manifest row (`no_claim`), never
    asked; "within N" and similar are unmarked (the rule names only "up to"); a partly typed criterion gets no
    untyped question (only a criterion with no atom does), so a requirement a bank missed beside an atom it
    typed is seen by no question yet (open).

## 3. Live sample

- [ ] 3.1 `sample.py` and `trialledger sample`: strata by top-level condition ancestors, live id lists, seeded
      independent draws, deduplication with union inclusion probabilities, the hash-reserved confirmation pool,
      the balance table, everything kept; then `resolve --keep` on the drawn ids

  - 2026-10-31: built and converged (envelope, validate_answer, response_text, installed_digest, reserved,
    draw, inclusion: COMPLETE); `trialledger audit` writes the manifest and the atom-claim questions, then the
    validated answers; untyped-criterion, outcome and intervention questions were then manifest rows only
    (2.2, since built). Id-only live paging: 80,929 IDs of the no-MeSH stratum in 103 s from one snapshot. 3.1
    still lacks the balance table (phase, intervention type, primary purpose) and its supplement; 2.1 lacks
    the gap check.
  - 2026-10-31 (later): the balance table and its supplement are built. `sample.json` declares them before any
    draw (the axes with their search areas, the registry's values from the vendored enums plus the two phase
    combinations the metadata's rule names, one supplement trial per empty cell, the seed label). The audit
    reads each trial's cells from its record when it is resolved (`trial_cells`: a combined phase is one cell,
    as written; a field the record leaves empty is "(none recorded)", never a gap) and writes `balance.json`
    beside its manifest (`balance_rows`, `cell_status`): drawn and supplement counts apart, the registry's count
    for each cell it asked. Audited whole, a declared sample has each empty registry cell fetched live within the
    frame (one snapshot), and a cell the registry holds gets a seeded supplement from its discovery pool outside
    the sample, with its own inclusion probability n/N, audited in the same loop and labelled in the manifest
    (`drawn_as`); a supplement whose record lacks its cell is named and fills nothing. A partial audit, or a
    sample from before the declaration (the pilot's), asks the registry nothing: its empty cells are
    "not_checked".
  - 2026-11-01: the three search areas and the exact-phase `NOT` were tried live once (countTotal, pageSize 1;
    `tests/live_query_forms.json`, data of 2026-10-30) and each returned trials; `sample.VERIFIED_FORMS`
    declares them with that date, and a zero-hit cell whose query uses a form not on that list is
    "query_unverified", never "empty_in_registry". A declared phase combination matches a record listing its
    phases in another order (`holds_cell`), the written value kept. A trial drawn as a supplement for two
    cells carries its union probability. Question and answer rows carry `drawn_as`, and `trialledger pilot`
    draws only the sample's questions unless `--include-supplement`. A snapshot change raises
    `SnapshotChanged`, the only error besides `PullError` that `sample` and `audit` catch. Left, so not
    ticked: Detective convergence of `trial_cells`, `holds_cell`, `cell_status`, `balance_rows` (accepted
    debt); under-representation (sample share against the registry's share for a non-empty cell) is not
    measured, since the registry's count is fetched only for empty cells; the drawn trials are kept as the
    audit's records, not through `resolve --keep`.

## 4. Pilot

  Declared 2026-10-31, before any pilot answer exists. Sample: `trialledger sample --seed pilot-2026-10-31
  --per-stratum 1` (18 strata, one trial each), kept under ~/tools/TrialLedger-runs/pilot-2026-10-31. Units:
  every `atom_claim` question of those trials; Claude labels a seeded random 100 blind (seed "pilot-labels",
  before running any model); mutations: up to 60 seeded atoms (seed "pilot-mutations"), each turned into three
  questions with known answers (values changed: wrong_value; inclusion and exclusion swapped:
  wrong_polarity_or_modality; another criterion's atom claimed of this one: unsupported). Configurations:
  qwen3.5:4b and qwen3:8b, thinking on, run one after the other, each released after its run. Deciding measure,
  in order: (1) mutations accepted as supported, at most 5%; (2) correct readings (by Claude's label) challenged,
  at most 25%; (3) time per question. The 4B is chosen if it meets (1) and (2); else the 8B; else the pilot
  reports insufficient evidence. A mutation whose model verdict differs from its expected one is checked by
  Claude before it counts: a concept mutation claims another criterion's concept, which a bank may have missed
  in this criterion's text. Codex second-reads a seeded 20 of Claude's labels and every question where
  Claude and the chosen model disagree, capped at 40; the Claude-Codex disagreement rate is reported.

- [ ] 4.1 Pilot criteria declared; 15-20 trials, 80-120 units, a challenge set and the mutations; blind human
      references in the adjudication workbook
- [ ] 4.2 The three configurations run on the same units; compared per unit type and bank; one chosen, or
      insufficient evidence reported

## 5. Discovery wave

- [ ] 5.1 ~6 trials per stratum through `resolve --keep`; outputs kept before any audit
- [ ] 5.2 `trialledger audit`: questions asked, answers validated, the adjudication workbook written (challenged
      items, sampled accepted items, empty outputs), named rates with trial-clustered uncertainty

## The loop (the founder, 2026-10-31)

The small model answers targeted questions; Claude and Codex audit its answers for correctness; what the audit
finds becomes symbolic rules, bank fixes and sharper questions that pre-empt the model's drift and uncertainty,
so what is left for the model keeps shrinking.

## Symbolic corrections from the pilot (2026-10-31)

Claude's 100 blind labels of the pilot's questions found 32 wrong claims (5 wrong value, 15 wrong polarity or
modality, 12 unsupported). Corrected by general rules, each with tests, every changed decision re-converged:
the API's escaped `=\<`; paired thresholds with their qualifiers; in-text negation of a condition's mention
(`text_polarity`), with "not limited to" and "not only" excepted; permission as a sentence-level modality
(`permitted`), never a requirement; a window needs a temporal marker; `reading.effective_section` shared by the
reading and the audit claims; vocabulary boundaries (AIDS in capitals only; vitamin premedication needs its
context; anticoagulant use and serious comorbidity split from bleeding and investigator judgment; "childbearing
potential" is not contraception; the study's own investigational product is not another study's; an
immunosuppressive disease is not therapy; "capable of becoming pregnant" is not pregnancy). Result: 20 of the 32
corrected, 68 of 68 right claims unchanged; on the NSCLC set the frozen expectation is unchanged (110 present, 0
verified deviations). The 12 left need the scoped-assertion layer (add-scoped-reasoning task 2): alternatives,
another person's condition, definitional text, qualified subsets, a study's own procedures.

## The auditor pilot's result (2026-11-01)

qwen3.5:4b with thinking took about five minutes a question (8 of 277 answered, 7 matching Claude's reference)
and was stopped; it fails on time. qwen3:8b with thinking answered 257 of 277 (18 quotes not found verbatim, 2
truncated): planted mutations accepted as supported 1 of 164 (0.6%, criterion 1 met); of Claude's 100 labelled
claims, wrong ones caught 24 of 28, right ones challenged 30 of 65 (46%, criterion 2 as declared not met). The
founder's ruling: an over-challenge is a warrant for a symbolic gate, not a failure. 26 of the 30 were
"wrong_value" on named-condition claims (the model grading `condition = pregnancy_or_breastfeeding` as a
value): named-condition claims now read in words, and `gates.mention_value_gate` (derived from this pilot,
recorded as such) overrules that challenge where the rules re-derive the condition in the same effective section
and window; on the pilot it overrules 25 right and 3 wrong claims, the 3 being scoped-assertion cases. The quote
normalizer (`questions.quote_in`: markdown escapes, whitespace, quotation marks, a trailing ellipsis as a prefix)
answers the quote errors. The 4 wrong claims the model accepted are all scoped-assertion cases (alternatives,
another person, a qualified subset, a paired threshold). qwen3:8b with thinking is the auditor. Codex's
second read of Claude's labels and the disagreements is the remaining step of 4.2.
