# Tasks — add-design-surprise

## 1. Falsifier

- [x] 1.1 Freeze one expectation ("PD-1/PD-L1 blocker trials exclude active autoimmune disease"): predicate, applicability, conditioning cell, parent hierarchy, support; record its provenance
- [x] 1.2 Write the observation-status decision for that predicate with two-sign intent tests from real criteria and constructed counterexamples (explicit exclusion, qualified exception, omission, unresolved text, conflicting cohort scopes); converge once
- [x] 1.3 Trace the falsifier set end to end (span, status, applicability, derivation, probability source, decision) and record whether an unexplained valid exception survives and omission stays distinct from permission

  - 2026-10-31, frozen `checkpoint_blockers_exclude_autoimmune_disease` (expectations.FROZEN, provenance
    prior). Constructed set: explicit exclusion, qualified exception, omission, unresolved text, conflicting
    scopes, admission with a condition: all read as designed; an omission is never permission and a valid
    unexplained admission survives as a verified deviation. On the 487 development trials (141 applicable):
    the first pass gave 31 apparent deviations; every one was an extraction defect of the readers, not of the
    trials, and each is now a test: permissive sentences inside exclusion criteria ("replacement therapy is
    allowed") read as admission; a "NON-INCLUSION CRITERIA" heading (a French protocol's exclusions) missed,
    so exclusions read as inclusions; a negation farther than 60 characters, across "(e.g., Crohn's", missed.
    After the fixes: present 110, not documented 22 (deviation "omission", separate from admission, at a
    side reviewer's note), unresolved 9 (records saying they list only key criteria), verified deviations 0.
    So on development data the expectation holds wherever a trial names the condition; whether genuine
    deviations exist is a question for a population no rule was written against.
  - Production path (the founder's requirement, 2026-10-31): `trialledger resolve NAME=VALUE ...` resolves a
    live API query (one snapshot, complete or nothing) to the same reading without saving any record; JSON
    (`--json`) or design.xlsx (`--out`); RxClass answers cached in ~/.cache/trialledger or $TRIALLEDGER_CACHE.
    Live check: NCT03829332 (pembrolizumab) present/conforms with its exception kept; NCT04171284's SCT-I10
    stays unresolved (its intervention entry states no target; an arm's description names its whole
    combination, so it is never used to attribute a target to one drug).

## 2. Contracts

- [ ] 2.1 Provenance on every rule, vocabulary entry and threshold (external / prior / derived), shown on the Relations and a new Rules sheet
- [x] 2.2 Conditional rarity over declared cells with parent fallback and abstention; deviation statuses; near-miss pairs under a declared representation; each a pure decision, converged once

  - 2026-10-31, near misses (`nearmiss.near_misses`, `design.near_miss_input`, both converged COMPLETE; the
    Near Misses sheet and each study's `near_misses` in the `resolve` JSON). Representation R, declared
    before any pair was read: the setting when it is one value, and the experimental drugs' classes when
    every drug is classified by RxClass; predicates: inclusion ECOG values, inclusion histologies, the
    checkpoint expectation when present or explicitly negated. On the development data R is known for 12 of
    487 trials (77 have one setting, 290 drug names are unresolved), and no pair exists; the header of the
    sheet carries that count, so "0 rows" never reads as "none exist". Counting record-stated classes
    ("stated: PD-L1") as known gave 2 pairs, both reader defects (ECOG "0 or 1" before the scale's name read
    as "1"; fixed in `banks.performance_status`, re-converged, 7+ criteria corrected): that admission mixes
    two vocabularies and is the founder's decision, not made here.
    Residual against the requirement (design-deviations, "Near-miss pairs are relative to a declared
    representation"): each pair reports the lead sponsor and start year, not sponsor lineage (collaborators,
    shared templates), geography or cohort structure; and its differing predicate is a typed atom, verified
    only by the falsifier pass above, not by an audit of every pair. Both stay open until a pair exists to
    audit (a wider population).

## 3. Rules from the design schema

- [ ] 3.1 The eligibility design schema (slots typed by entity domain, value, temporal qualifier, polarity), authored from domain priors and cited sources, frozen and versioned before any confirmation
- [ ] 3.2 Confirmation on a population no rule was written against (the corpus pull, or a second indication), per-slot identified / abstained / wrong with denominators, audit sampling declared in advance

## Workflow follow-up

- Founder approvals: the frozen expectation and its cell; promotion of any specialised expectation.
