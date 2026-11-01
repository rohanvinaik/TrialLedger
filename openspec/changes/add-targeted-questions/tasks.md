# Tasks — add-targeted-questions

## 1. Questions and transport

- [x] 1.1 `questions.py`: the question object, the deterministic envelope (target, heading ancestry, parent stem,
      conjunction siblings, budget refusal), answer validation (one verdict per atom id, cited span inside the
      envelope, closed options)
- [x] 1.2 `transport.py`: the GSE-contract Ollama transport (explicit model, pin and verify, canonical JSON,
      schema format, temperature 0, budgets, named errors, identity) and the hash-keyed answer cache

## 2. Source manifest and audit questions

- [ ] 2.1 The source manifest of a resolved trial (eligibility pieces and gaps, outcomes, interventions)
- [ ] 2.2 Audit question builders: `atom_claim`, `untyped_criterion` (concept instances, out_of_taxonomy),
      outcome and intervention claims; RxClass assignments checked deterministically against the kept artifact

## 3. Live sample

- [ ] 3.1 `sample.py` and `trialledger sample`: strata by top-level condition ancestors, live id lists, seeded
      independent draws, deduplication with union inclusion probabilities, the hash-reserved confirmation pool,
      the balance table, everything kept; then `resolve --keep` on the drawn ids

  - 2026-10-31: built and converged (envelope, validate_answer, response_text, installed_digest, reserved,
    draw, inclusion: COMPLETE); `trialledger audit` writes the manifest and the atom-claim questions, then the
    validated answers; untyped-criterion, outcome and intervention questions are still manifest rows only (2.2).
    Id-only live paging: 80,929 IDs of the no-MeSH stratum in 103 s from one snapshot. 3.1 still lacks the
    balance table (phase, intervention type, primary purpose) and its supplement; 2.1 lacks the gap check.

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
