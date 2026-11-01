# Tasks — add-targeted-questions

## 1. Questions and transport

- [ ] 1.1 `questions.py`: the question object, the deterministic envelope (target, heading ancestry, parent stem,
      conjunction siblings, budget refusal), answer validation (one verdict per atom id, cited span inside the
      envelope, closed options)
- [ ] 1.2 `transport.py`: the GSE-contract Ollama transport (explicit model, pin and verify, canonical JSON,
      schema format, temperature 0, budgets, named errors, identity) and the hash-keyed answer cache

## 2. Source manifest and audit questions

- [ ] 2.1 The source manifest of a resolved trial (eligibility pieces and gaps, outcomes, interventions)
- [ ] 2.2 Audit question builders: `atom_claim`, `untyped_criterion` (concept instances, out_of_taxonomy),
      outcome and intervention claims; RxClass assignments checked deterministically against the kept artifact

## 3. Live sample

- [ ] 3.1 `sample.py` and `trialledger sample`: strata by top-level condition ancestors, live id lists, seeded
      independent draws, deduplication with union inclusion probabilities, the hash-reserved confirmation pool,
      the balance table, everything kept; then `resolve --keep` on the drawn ids

## 4. Pilot

- [ ] 4.1 Pilot criteria declared; 15-20 trials, 80-120 units, a challenge set and the mutations; blind human
      references in the adjudication workbook
- [ ] 4.2 The three configurations run on the same units; compared per unit type and bank; one chosen, or
      insufficient evidence reported

## 5. Discovery wave

- [ ] 5.1 ~6 trials per stratum through `resolve --keep`; outputs kept before any audit
- [ ] 5.2 `trialledger audit`: questions asked, answers validated, the adjudication workbook written (challenged
      items, sampled accepted items, empty outputs), named rates with trial-clustered uncertainty
