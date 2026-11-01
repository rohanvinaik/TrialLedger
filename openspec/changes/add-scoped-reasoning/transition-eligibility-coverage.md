# Transition report — eligibility coverage (Decision 12, task 8.3)

Written 2026-10-31, before the metrics were replaced, on the frozen NSCLC development records: the 487
interventional Phase 3 NSCLC trials started 2015-2024 in `/tmp/nsclc3` (pulled 2026-10-31), read from a private
copy (that folder was not written to). The RxClass answers were the copy's cached `classes.json`; a cache miss
would have raised, and none occurred, so no live call was made. "Old" is the design sheets computed by the code
at commit `ec32704` (this change's parent) on that copy; "new" is the same computation by this change's code.
Regenerated 2026-11-01 after review, from the same copy and the same old values, when the profile gained the
no-rule-match silence and the statement-rate-only rows of primary endpoints and the mechanism status its bound
against abbreviated silences. Warrants are left out of the comparison (they commit to the code, so all of them
change). These numbers are measured on development data and establish nothing about other populations.

## What changed, in one place

| Consumer | Old | New | Changed decisions |
|---|---|---|---|
| Expectations (487 observations) | 110 present, 22 not documented, 9 unresolved as abbreviated, 346 not applicable | identical, row for row | none |
| Occupancy (198 cells) | as before | identical, row for row | none |
| Near misses | no pair | no pair | none |
| Review queue | 364 flags | the same 364, plus 64 `eligibility_abbreviated` | 64 added (appendix A) |
| Profile (1,108 rows) | frequency over itemized trials; tier standard or "" | statement rate over every trial; for the 1,068 eligibility elements the interval [S/N, (S+U)/N] and tier met, not met or unresolved; for the 40 primary endpoints the statement rate only, tier "" | 1,067 tiers "" → unresolved; 1 standard → met; 40 endpoint tiers "" kept (appendix D) |
| Mechanism signals | 3,269 rows: 598 proposed, 2,671 below support | 3,935 rows: 261 proposed, 1,263 below support, 2,411 unresolved; counts of every old row unchanged | 337 proposed → unresolved; 1,408 below support → unresolved; 666 added, unresolved; none removed (appendix C) |

## The attributes (task 8.1)

Each trial's eligibility now carries separate attributes, from one pure decision
(`criteria.eligibility_coverage`), shown on the Trials sheet (Eligibility Content, Sectioning, Inclusion
Coverage, Exclusion Coverage, Coverage Markers) and in the `resolve` JSON (`eligibility_coverage`):

- Content: present 487, empty 0.
- Sectioning: sectioned 478, unsectioned 9.
- Coverage evidence (inclusion, exclusion): (unspecified, unspecified) 423; (abbreviation stated, abbreviation
  stated) 55; (abbreviation stated, unspecified) 5; (unspecified, abbreviation stated) 4. Completeness stated: 0
  (the completeness pattern is prior and matched nothing here).
- Markers: 129 abbreviation markers, scoped inclusion 48, exclusion 48, both 33, each with its piece and its
  offsets in the text.

The abbreviation pattern moved from `expectations.py` to `criteria.py` byte for byte, so that the expectation it
gates would not change. It reads every piece (headings included), as before.

## Expectations: no change, and why

`autoimmune_exclusion` now reads the coverage attribute instead of searching the text itself. A predicate that
an inclusion criterion can also exclude ("No history of autoimmune disease") is silent only if both sections
are, so an abbreviation of either section makes its silence unresolved: the observation is
`abbreviated_criteria` when any section's evidence is `abbreviation_stated`. Every marker the old search found
is a marker of some scope, so the two readings agree by construction; measured, all 487 observations are
identical (the 9 `abbreviated_criteria` observations are NCT02576574, NCT02713867, NCT03195491, NCT03631199,
NCT03815643, NCT03833154, NCT06448312, NCT06623422, NCT06635824).

Had the expectation read the exclusion scope only, none of the 9 would change: each has an exclusion-scoped or
both-scoped marker. None of the 9 rests only on an "include, but are not limited to" marker either.

## Defects measured, left for the founder

The pattern was kept unchanged on purpose (the expectation's behaviour was not to change); what it gets wrong
on these records is reported here instead, and the review flag puts each abbreviation reading to a reviewer.

- Misses (11 records read "unspecified" in both scopes although they say other criteria apply):
  "Other protocol-defined inclusion/exclusion criteria apply" with no modal verb (NCT04026412, NCT06140836,
  NCT04025879, NCT02477826, NCT02998528, NCT02864251, NCT06159790, NCT06561386), "Other protocol
  inclusion/exclusion criteria may apply" (NCT03215706), "Other protocol inclusion criteria may apply" and
  "Other protocol exclusion criteria may apply" (NCT03348904), "Other inclusion and exclusion criteria will
  apply" (NCT06472245). In the profile they are unresolved either way (unspecified instead of abbreviated); in
  the expectation, any of them whose observation is `not_named` would become `abbreviated_criteria` if the
  pattern were widened.
- False positives (7 records read "abbreviation stated" only because a criterion lists examples with
  "include, but are not limited to"): NCT04929041, NCT03391869, NCT03743051, NCT03743064, NCT03912389,
  NCT05204628, NCT04267848. None of them is among the 9 `abbreviated_criteria` observations; in the profile their
  silence is counted as abbreviated instead of unspecified (both unresolved); each gets an
  `eligibility_abbreviated` flag whose options include "not abbreviated (the marker is misread)".

## Profile (task 8.2)

Old: an element's frequency was trials stating / trials whose eligibility was itemized, and it was standard at
0.9 or more. The silent trials, abbreviated ones included, were in the denominator as lacking the element.

New: two estimands, separate named columns. The registry statement rate S/N over every trial of the stratum (a
point). For an eligibility element (inclusion, exclusion, permitted, unsectioned), the full-criteria frequency,
identified only as the interval [S/N, (S+U)/N], where U is every silent trial, counted as empty eligibility (0
here), no rule match (eligibility text no bank typed any of), abbreviated in the element's section, or
unspecified. A, the trials whose absence a declared ascertainment rule establishes, is 0 by construction: no
ascertainment rule is declared (a completeness statement plus full typing was considered and rejected, because
a typed criterion can still mention an element no bank typed, which would read silence as absence again). So
every upper bound is 1.0 here, and the three-valued tier is met (the lower bound reaches 0.9) or unresolved,
never not met, until a rule is declared. A primary endpoint is not eligibility: its row gives the statement rate
only, no A, U, interval or tier, and its Estimand cell says so.

- Denominators: all trials 481 → 487; setting unresolved 399 → 405; advanced first line 82 → 82. The six trials
  that joined are those whose eligibility has no list markers (appendix B); each is silent about every
  eligibility element as no rule match, its own kind, never merged into unspecified.
- S changed in 4 rows, all primary endpoints stated by those six trials: objective response rate 46 → 48 and
  progression-free survival 244 → 247 (all trials); 37 → 39 and 186 → 189 (setting unresolved).
- Tiers: the one standard row, `inclusion:prior_lines=0` in advanced first line (79/82, rate 0.9634), is met.
  The other 1,067 eligibility rows change from "" (read as not standard) to unresolved, each for the same
  reason: its lower bound is below 0.9 and its upper bound is 1.0. The 40 primary-endpoint rows keep tier "".
  Unresolved silences over the eligibility rows: 5,076 no rule match (6 in each of the 846 rows outside
  advanced first line), 44,921 abbreviated, 317,541 unspecified.

## Mechanism signals (task 8.2)

A mechanism signal is a statement-rate comparison over the typed (itemized) trials whose experimental class is
known: a trial whose text was never typed is in neither group, never counted as lacking an element. A record
that says its list is abbreviated may hold an element it does not state, so the comparison is now bounded
against those silences. For a class C and element E, with m and n the silent trials in C and among the others
whose record says E's section is abbreviated: proposed when a/b > (c+n)/d (every abbreviated silence among the
others counted as stating E, every one in C as lacking it: the least favourable reading) with at least 5
trials and 3 sponsors; below support when it holds so with less support; unresolved when it fails so but
(a+m)/b > c/d (abbreviated silences could reverse it, or could make it), whatever its support; not listed when it
fails at both readings. The sheet adds the least favourable difference beside the stated one, and both
abbreviated-silence columns.

The 2×2 counts of all 3,269 old rows are unchanged; none was removed. Of the 598 proposed rows, 261 hold at the
least favourable reading and stay proposed; 337 do not and are unresolved. Of the 2,671 below-support rows,
1,263 hold at that reading and stay below support; 1,408 are unresolved. 666 rows are added, all unresolved:
the in-class rate does not exceed the others' as stated, but would if the class's abbreviated silences stated
the element. Every changed status is in appendix C.

A first version of this change compared statement rates over every known-class trial, typed or not. On these
records that admitted one untyped trial, NCT05104281 (no list markers; every experimental drug classed),
counted as stating nothing, and it alone removed 16 rows and added 8, 6 of them proposed: proposals that
existed only because an unread record was counted as lacking the element. It was rejected for that reason
before this report was final.

## Occupancy and near misses: no change, and why

Occupancy reads each trial's known setting domain, which only stated evidence narrows: a silent record keeps a
wide domain and stays among the trials that could fall in a cell, never out of it. Near misses compare stated
predicate values; a silent record's value is "", and "" never matches. Neither reads silence as a value, so
neither needed a change; both are identical on these records.

## Appendices: every changed decision

### A. Review flags added (eligibility_abbreviated), one per record

| NCT | Why | Evidence (scope, piece, offsets, marker) |
|---|---|---|
| NCT02272413 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 1, characters 945-977: Further inclusion criteria apply ⏐ [exclusion] piece 3, characters 1947-1979: Further exclusion criteria apply |
| NCT02395172 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 13, characters 2552-2605: Other protocol defined inclusion criteria could apply ⏐ [exclusion] piece 25, characters 4869-4922: Other protocol defined exclusion criteria could apply |
| NCT02576574 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 7, characters 771-814: Other protocol defined criteria could apply ⏐ [exclusion] piece 13, characters 1856-1899: Other protocol defined criteria could apply |
| NCT02713867 | the record says its criteria are abbreviated (both) | [both] piece 10, characters 814-877: Other protocol defined inclusion/exclusion criteria could apply |
| NCT02810457 | the record says its criteria are abbreviated (both) | [both] piece 17, characters 1342-1386: Other inclusion/exclusion criteria may apply |
| NCT02826161 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 8, characters 919-932: Key Exclusion |
| NCT03048136 | the record says its criteria are abbreviated (both) | [both] piece 10, characters 826-889: Other protocol defined inclusion/exclusion criteria could apply |
| NCT03088540 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 9, characters 874-887: Key Exclusion |
| NCT03195491 | the record says its criteria are abbreviated (both) | [both] piece 13, characters 1220-1283: Other protocol defined inclusion/exclusion criteria could apply |
| NCT03358875 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 9, characters 919-932: Key Exclusion ⏐ [both] piece 24, characters 2727-2788: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT03391869 | the record says its criteria are abbreviated (exclusion) | [exclusion] piece 32, characters 9661-9692: include, but are not limited to |
| NCT03409614 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 8, characters 1134-1147: Key Exclusion ⏐ [both] piece 16, characters 2242-2303: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT03417037 | the record says its criteria are abbreviated (both) | [both] piece 13, characters 1636-1699: Other protocol defined inclusion/exclusion criteria could apply |
| NCT03447769 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 6, characters 1060-1073: Key Exclusion |
| NCT03456076 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 11, characters 1470-1483: Key Exclusion |
| NCT03515629 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 7, characters 912-925: Key Exclusion ⏐ [both] piece 16, characters 2074-2135: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT03529084 | the record says its criteria are abbreviated (both) | [both] piece 26, characters 2688-2749: Other protocol-defined inclusion/exclusion criteria may apply |
| NCT03594747 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 9, characters 600-613: Key Exclusion ⏐ [both] piece 22, characters 1463-1524: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT03626545 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 5, characters 410-423: Key Exclusion |
| NCT03631199 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key inclusion ⏐ [exclusion] piece 5, characters 574-587: Key exclusion |
| NCT03631706 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 7, characters 953-1006: Other protocol defined inclusion criteria could apply ⏐ [exclusion] piece 13, characters 1813-1866: Other protocol defined exclusion criteria could apply |
| NCT03663205 | the record says its criteria are abbreviated (both) | [both] piece 22, characters 1569-1630: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT03743051 | the record says its criteria are abbreviated (exclusion) | [exclusion] piece 16, characters 2760-2790: include but are not limited to |
| NCT03743064 | the record says its criteria are abbreviated (exclusion) | [exclusion] piece 15, characters 2677-2707: include but are not limited to |
| NCT03802240 | the record says its criteria are abbreviated (inclusion) | [inclusion] piece 0, characters 0-14: Main Inclusion |
| NCT03815643 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 4, characters 629-682: Other protocol defined inclusion criteria could apply ⏐ [exclusion] piece 11, characters 1140-1193: Other protocol defined exclusion criteria could apply |
| NCT03833154 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 12-25: Key Inclusion ⏐ [exclusion] piece 11, characters 569-582: Key Exclusion ⏐ [inclusion] piece 18, characters 1063-1076: Key Inclusion ⏐ [exclusion] piece 30, characters 1929-1942: Key Exclusion |
| NCT03912389 | the record says its criteria are abbreviated (inclusion) | [inclusion] piece 11, characters 2231-2261: include but are not limited to |
| NCT04267848 | the record says its criteria are abbreviated (inclusion) | [inclusion] piece 18, characters 3315-3346: include, but are not limited to |
| NCT04379635 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 5, characters 265-278: Key Exclusion ⏐ [both] piece 11, characters 917-978: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT04427072 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 8, characters 2353-2366: Key Exclusion |
| NCT04466917 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 4, characters 353-387: Other inclusion criteria may apply ⏐ [exclusion] piece 18, characters 1300-1334: Other exclusion criteria may apply |
| NCT04619797 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 10, characters 749-762: Key Exclusion |
| NCT04633564 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 7, characters 905-918: Key Exclusion |
| NCT04746924 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 7, characters 667-680: Key Exclusion ⏐ [both] piece 12, characters 1270-1331: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT04816214 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 8, characters 880-893: Key Exclusion |
| NCT04866017 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 8, characters 1035-1048: Key Exclusion |
| NCT04921358 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 7, characters 1003-1016: Key Exclusion ⏐ [both] piece 13, characters 1601-1662: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT04929041 | the record says its criteria are abbreviated (inclusion) | [inclusion] piece 22, characters 4110-4141: include, but are not limited to |
| NCT05089734 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 10, characters 2321-2334: Key Exclusion ⏐ [both] piece 26, characters 4577-4638: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT05132075 | the record says its criteria are abbreviated (both) | [both] piece 10, characters 1195-1239: Other inclusion/exclusion criteria may apply |
| NCT05204628 | the record says its criteria are abbreviated (exclusion) | [exclusion] piece 16, characters 2712-2743: include, but are not limited to |
| NCT05226598 | the record says its criteria are abbreviated (both) | [both] piece 0, characters 4-18: main inclusion ⏐ [both] piece 0, characters 42-72: include but are not limited to |
| NCT05298423 | the record says its criteria are abbreviated (both) | [both] piece 0, characters 4-18: main inclusion ⏐ [both] piece 0, characters 42-72: include but are not limited to |
| NCT05502237 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 8, characters 901-914: Key Exclusion ⏐ [both] piece 23, characters 2383-2444: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT05522660 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-24: Most important inclusion ⏐ [exclusion] piece 20, characters 2656-2680: Most important exclusion |
| NCT05555732 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 7, characters 1911-1924: Key Exclusion ⏐ [exclusion] piece 10, characters 2806-2837: include, but are not limited to |
| NCT05605613 | the record says its criteria are abbreviated (both) | [both] piece 20, characters 1579-1640: Other protocol defined Inclusion/Exclusion criteria may apply |
| NCT05607550 | the record says its criteria are abbreviated (inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion |
| NCT05609968 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 1, characters 25-39: main inclusion ⏐ [inclusion] piece 1, characters 49-79: include but are not limited to ⏐ [exclusion] piece 7, characters 631-645: main exclusion ⏐ [exclusion] piece 7, characters 655-685: include but are not limited to |
| NCT05722015 | the record says its criteria are abbreviated (both) | [both] piece 0, characters 4-17: key inclusion ⏐ [both] piece 0, characters 41-71: include but are not limited to |
| NCT05785767 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 7, characters 1304-1317: Key Exclusion |
| NCT05791097 | the record says its criteria are abbreviated (both, exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 5, characters 515-528: Key Exclusion ⏐ [both] piece 11, characters 1604-1648: Other inclusion/exclusion criteria may apply |
| NCT05800015 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 7, characters 1464-1477: Key Exclusion |
| NCT05984277 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 5, characters 542-555: Key Exclusion |
| NCT06074588 | the record says its criteria are abbreviated (both) | [both] piece 0, characters 4-18: main inclusion ⏐ [both] piece 0, characters 42-72: include but are not limited to |
| NCT06077760 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 1, characters 25-39: main inclusion ⏐ [inclusion] piece 1, characters 49-79: include but are not limited to ⏐ [exclusion] piece 10, characters 1148-1162: main exclusion ⏐ [exclusion] piece 10, characters 1172-1202: include but are not limited to |
| NCT06151574 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 9, characters 1570-1602: Further inclusion criteria apply ⏐ [exclusion] piece 19, characters 3322-3354: Further exclusion criteria apply |
| NCT06212752 | the record says its criteria are abbreviated (both) | [both] piece 0, characters 4-17: key inclusion ⏐ [both] piece 0, characters 41-71: include but are not limited to |
| NCT06312137 | the record says its criteria are abbreviated (both) | [both] piece 0, characters 4-17: key inclusion ⏐ [both] piece 0, characters 41-71: include but are not limited to |
| NCT06345729 | the record says its criteria are abbreviated (both) | [both] piece 0, characters 4-18: main inclusion ⏐ [both] piece 0, characters 42-72: include but are not limited to |
| NCT06448312 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 19-32: Key Inclusion ⏐ [exclusion] piece 8, characters 695-708: Key Exclusion |
| NCT06623422 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 1, characters 25-39: main inclusion ⏐ [inclusion] piece 1, characters 49-79: include but are not limited to ⏐ [exclusion] piece 10, characters 1361-1375: main exclusion ⏐ [exclusion] piece 10, characters 1385-1415: include but are not limited to |
| NCT06635824 | the record says its criteria are abbreviated (exclusion, inclusion) | [inclusion] piece 0, characters 0-13: Key Inclusion ⏐ [exclusion] piece 8, characters 1299-1312: Key Exclusion |

### B. Trials that joined the profile's frequency cohorts (eligibility not itemized; not the mechanism groups)

Each is silent about every eligibility element as no_rule_match: it has text, and no bank typed any of it.

| NCT | Itemized | Content | Coverage (inclusion, exclusion) | Experimental classes all known | Primary endpoint elements |
|---|---|---|---|---|---|
| NCT05104281 | no_list_markers | present | unspecified, unspecified | True | primary:endpoint:progression_free_survival |
| NCT04797806 | no_list_markers | present | unspecified, unspecified | False | primary:endpoint:progression_free_survival |
| NCT06043973 | no_list_markers | present | unspecified, unspecified | False | primary:endpoint:progression_free_survival |
| NCT02859077 | no_list_markers | present | unspecified, unspecified | False | (none) |
| NCT04840290 | no_list_markers | present | unspecified, unspecified | False | primary:endpoint:objective_response_rate |
| NCT02272413 | no_list_markers | present | abbreviation_stated, abbreviation_stated | False | primary:endpoint:objective_response_rate |

### C. Mechanism signal rows whose status changed or that were added

a/b and c/d are the statement rates in the class and among the others (unchanged where the row existed); m and n are the silent trials in the class and among the others whose record says the element's section is abbreviated; the least favourable difference is a/b − (c+n)/d. A row is unresolved when that difference is not above 0 and (a+m)/b > c/d. No row was removed.

| Stratum | Class | Element | a/b | c/d | m | n | Difference | Least favourable | Old status | New status |
|---|---|---|---|---|---|---|---|---|---|---|
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:condition=active_infection | 2/3 | 5/9 | 0 | 2 | 0.1111 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:condition=bleeding_thrombosis | 1/3 | 1/9 | 0 | 3 | 0.2222 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:condition=diagnosis_confirmed | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:condition=hepatitis | 2/3 | 4/9 | 0 | 2 | 0.2222 | 0.0 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:condition=hiv | 2/3 | 4/9 | 0 | 2 | 0.2222 | 0.0 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:condition=live_vaccine | 1/3 | 2/9 | 0 | 3 | 0.1111 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:condition=organ_transplant | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:condition=tuberculosis | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:histology=small_cell | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:CTLA-4 | 1/3 | 2/9 | 0 | 4 | 0.1111 | -0.3333 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:chemotherapy | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:immune checkpoint | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:radiotherapy | 1/3 | 2/9 | 0 | 4 | 0.1111 | -0.3333 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | exclusion:prior_lines=0 | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ALK=positive | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:biomarker:EGFR=negative | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:biomarker:EGFR=positive | 1/3 | 1/9 | 0 | 3 | 0.2222 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:biomarker:PD-L1=@≥1% | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:condition=compliance | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:condition=diagnosis_confirmed | 3/3 | 8/9 | 0 | 1 | 0.1111 | 0.0 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:condition=informed_consent | 1/3 | 2/9 | 0 | 2 | 0.1111 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:condition=recent_radiotherapy | 1/3 | 1/9 | 0 | 3 | 0.2222 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:condition=weight_loss | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:ecog_ps=1 | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:extent:recurrent | 2/3 | 4/9 | 0 | 2 | 0.2222 | 0.0 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:lab:bilirubin | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:lab:creatinine clearance | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:lab:hemoglobin | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:lab:neutrophils | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:lab:platelets | 1/3 | 1/9 | 0 | 4 | 0.2222 | -0.2222 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | inclusion:prior_agent:ALK inhibitor | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | CTLA-4-directed Blocking Antibody | permitted:condition=immunosuppression_steroids | 1/3 | 0/9 | 0 | 4 | 0.3333 | -0.1111 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:biomarker:BRAF=unknown | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:biomarker:NTRK=unknown | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:biomarker:RET=unknown | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:condition=active_infection | 4/6 | 3/6 | 0 | 2 | 0.1667 | -0.1667 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:condition=diagnosis_confirmed | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:condition=effusion | 1/6 | 0/6 | 0 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:condition=hypertension | 1/6 | 1/6 | 1 | 2 | 0.0 | -0.3333 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:condition=neurologic_disorder | 3/6 | 3/6 | 1 | 1 | 0.0 | -0.1667 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:condition=organ_transplant | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:condition=pregnancy_or_breastfeeding | 2/6 | 2/6 | 1 | 2 | 0.0 | -0.3333 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:condition=weight_loss | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:histology=squamous | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:ALK inhibitor | 1/6 | 0/6 | 0 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:CTLA-4 | 2/6 | 1/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:EGFR inhibitor | 1/6 | 0/6 | 0 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:PD-L1 | 2/6 | 2/6 | 1 | 2 | 0.0 | -0.3333 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:immune checkpoint | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:prior_lines=1\|2\|3+ | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | exclusion:setting_word:consolidation | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ALK=positive | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ALK=unknown | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:biomarker:EGFR=positive | 1/6 | 1/6 | 1 | 2 | 0.0 | -0.3333 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:biomarker:EGFR=unknown | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:biomarker:NTRK=positive | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=@≥1% | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:biomarker:RET=positive | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ROS1=unknown | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=active_infection | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=autoimmune_disease | 2/6 | 0/6 | 1 | 3 | 0.3333 | -0.1667 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=cns_metastases | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=hepatitis | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=hiv | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=hypersensitivity | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=immunosuppression_steroids | 2/6 | 0/6 | 1 | 3 | 0.3333 | -0.1667 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=live_vaccine | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=other_malignancy | 3/6 | 0/6 | 1 | 3 | 0.5 | 0.0 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=pneumonitis_ild | 2/6 | 1/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 2/6 | 1/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=pulmonary_function | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=recent_surgery | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=serious_comorbidity | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=sex | 3/6 | 0/6 | 0 | 3 | 0.5 | 0.0 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:condition=unresolved_toxicity | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:extent:advanced | 3/6 | 2/6 | 0 | 2 | 0.1667 | -0.1667 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:ALT | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:AST | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:bilirubin | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:creatinine | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:creatinine clearance | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:hemoglobin | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:leukocytes | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:neutrophils | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:lab:platelets | 1/6 | 1/6 | 1 | 3 | 0.0 | -0.5 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:chemotherapy | 2/6 | 0/6 | 0 | 3 | 0.3333 | -0.1667 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:radiotherapy | 1/6 | 1/6 | 1 | 2 | 0.0 | -0.3333 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:setting_word:consolidation | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:stage:III | 1/6 | 1/6 | 1 | 2 | 0.0 | -0.3333 | (not listed) | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | inclusion:stage:IV | 4/6 | 3/6 | 1 | 2 | 0.1667 | -0.1667 | below_support | unresolved |
| advanced_first_line | Folate Analog Metabolic Inhibitor | permitted:condition=autoimmune_disease | 1/6 | 0/6 | 1 | 3 | 0.1667 | -0.3333 | below_support | unresolved |
| advanced_first_line | HER2/neu Receptor Antagonist | inclusion:condition=diagnosis_confirmed | 1/1 | 10/11 | 0 | 1 | 0.0909 | 0.0 | below_support | unresolved |
| advanced_first_line | Lymphocyte Activation Gene-3 Blocker | inclusion:condition=diagnosis_confirmed | 1/1 | 10/11 | 0 | 1 | 0.0909 | 0.0 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:condition=active_infection | 3/4 | 4/8 | 0 | 2 | 0.25 | 0.0 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:condition=hypertension | 1/4 | 1/8 | 0 | 3 | 0.125 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:condition=informed_consent | 2/4 | 1/8 | 0 | 3 | 0.375 | 0.0 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:condition=organ_transplant | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:condition=other_investigational | 2/4 | 1/8 | 0 | 3 | 0.375 | 0.0 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:condition=substance_or_psychiatric | 2/4 | 1/8 | 0 | 3 | 0.375 | 0.0 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:condition=unresolved_toxicity | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:condition=weight_loss | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:extent:metastatic | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:extent:recurrent | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:histology=non_squamous | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:prior_agent:PD-1 | 2/4 | 3/8 | 0 | 3 | 0.125 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:prior_agent:chemotherapy | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:prior_agent:immune checkpoint | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:prior_agent:radiotherapy | 2/4 | 1/8 | 0 | 4 | 0.375 | -0.125 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:prior_lines=1\|2\|3+ | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | exclusion:setting_word:consolidation | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:biomarker:ALK=positive | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:biomarker:EGFR=positive | 1/4 | 1/8 | 0 | 3 | 0.125 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=active_infection | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=autoimmune_disease | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=diagnosis_confirmed | 4/4 | 7/8 | 0 | 1 | 0.125 | 0.0 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=hepatitis | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=hiv | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=hypersensitivity | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=immunosuppression_steroids | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=live_vaccine | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 2/4 | 1/8 | 0 | 4 | 0.375 | -0.125 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=pulmonary_function | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=recent_surgery | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=serious_comorbidity | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:condition=unresolved_toxicity | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:ALT | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:AST | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:bilirubin | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:creatinine | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:creatinine clearance | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:hemoglobin | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:leukocytes | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:neutrophils | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:lab:platelets | 1/4 | 1/8 | 0 | 4 | 0.125 | -0.375 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:prior_agent:chemotherapy | 1/4 | 1/8 | 0 | 3 | 0.125 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:prior_agent:radiotherapy | 1/4 | 1/8 | 0 | 3 | 0.125 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:setting_word:consolidation | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:stage:III | 1/4 | 1/8 | 0 | 3 | 0.125 | -0.25 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | inclusion:stage:IV | 3/4 | 4/8 | 0 | 3 | 0.25 | -0.125 | below_support | unresolved |
| advanced_first_line | Microtubule Inhibitor | permitted:condition=autoimmune_disease | 1/4 | 0/8 | 0 | 4 | 0.25 | -0.25 | below_support | unresolved |
| advanced_first_line | Nucleoside Metabolic Inhibitor | inclusion:condition=diagnosis_confirmed | 1/1 | 10/11 | 0 | 1 | 0.0909 | 0.0 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:biomarker:BRAF=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:biomarker:NTRK=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:biomarker:RET=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=active_infection | 5/7 | 2/5 | 0 | 2 | 0.3143 | -0.0857 | proposed | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=cns_metastases | 6/7 | 4/5 | 0 | 1 | 0.0571 | -0.1429 | proposed | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=diagnosis_confirmed | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=effusion | 1/7 | 0/5 | 0 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=hepatitis | 4/7 | 2/5 | 0 | 2 | 0.1714 | -0.2286 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=hiv | 4/7 | 2/5 | 0 | 2 | 0.1714 | -0.2286 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=hypersensitivity | 3/7 | 1/5 | 0 | 2 | 0.2286 | -0.1714 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=hypertension | 1/7 | 1/5 | 1 | 2 | -0.0571 | -0.4571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=informed_consent | 2/7 | 1/5 | 1 | 2 | 0.0857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=neurologic_disorder | 4/7 | 2/5 | 1 | 1 | 0.1714 | -0.0286 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=organ_transplant | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=other_investigational | 2/7 | 1/5 | 1 | 2 | 0.0857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=other_malignancy | 2/7 | 2/5 | 1 | 1 | -0.1143 | -0.3143 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=pneumonitis_ild | 4/7 | 2/5 | 0 | 1 | 0.1714 | -0.0286 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=pregnancy_or_breastfeeding | 2/7 | 2/5 | 1 | 2 | -0.1143 | -0.5143 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=substance_or_psychiatric | 2/7 | 1/5 | 1 | 2 | 0.0857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=unresolved_toxicity | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:condition=weight_loss | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:extent:metastatic | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:extent:recurrent | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:histology=non_squamous | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:histology=squamous | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_agent:ALK inhibitor | 1/7 | 0/5 | 0 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_agent:CTLA-4 | 2/7 | 1/5 | 1 | 3 | 0.0857 | -0.5143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_agent:EGFR inhibitor | 1/7 | 0/5 | 0 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_agent:PD-1 | 3/7 | 2/5 | 1 | 2 | 0.0286 | -0.3714 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_agent:PD-L1 | 2/7 | 2/5 | 1 | 2 | -0.1143 | -0.5143 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_agent:chemotherapy | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_agent:immune checkpoint | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_agent:radiotherapy | 2/7 | 1/5 | 1 | 3 | 0.0857 | -0.5143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:prior_lines=1\|2\|3+ | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | exclusion:setting_word:consolidation | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:biomarker:ALK=positive | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:biomarker:ALK=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:biomarker:EGFR=positive | 1/7 | 1/5 | 1 | 2 | -0.0571 | -0.4571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:biomarker:EGFR=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:biomarker:NTRK=positive | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:biomarker:PD-L1=@≥1% | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:biomarker:RET=positive | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:biomarker:ROS1=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=active_infection | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=autoimmune_disease | 2/7 | 0/5 | 1 | 3 | 0.2857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=cns_metastases | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=contraception | 4/7 | 2/5 | 0 | 2 | 0.1714 | -0.2286 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=hepatitis | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=hiv | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=hypersensitivity | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=immunosuppression_steroids | 2/7 | 0/5 | 1 | 3 | 0.2857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=live_vaccine | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=other_malignancy | 3/7 | 0/5 | 1 | 3 | 0.4286 | -0.1714 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=pneumonitis_ild | 2/7 | 1/5 | 1 | 3 | 0.0857 | -0.5143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=pregnancy_or_breastfeeding | 3/7 | 0/5 | 1 | 3 | 0.4286 | -0.1714 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=pulmonary_function | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=recent_surgery | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=serious_comorbidity | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=sex | 3/7 | 0/5 | 0 | 3 | 0.4286 | -0.1714 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:condition=unresolved_toxicity | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:extent:advanced | 3/7 | 2/5 | 0 | 2 | 0.0286 | -0.3714 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:extent:recurrent | 4/7 | 2/5 | 1 | 1 | 0.1714 | -0.0286 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:ALT | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:AST | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:bilirubin | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:creatinine | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:creatinine clearance | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:hemoglobin | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:leukocytes | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:neutrophils | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:lab:platelets | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:organ_function_unspecified=adequate | 3/7 | 2/5 | 0 | 2 | 0.0286 | -0.3714 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:prior_agent:chemotherapy | 2/7 | 0/5 | 0 | 3 | 0.2857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:prior_agent:radiotherapy | 1/7 | 1/5 | 1 | 2 | -0.0571 | -0.4571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:setting_word:consolidation | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:stage:III | 1/7 | 1/5 | 1 | 2 | -0.0571 | -0.4571 | (not listed) | unresolved |
| advanced_first_line | Platinum-based Drug | inclusion:stage:IV | 5/7 | 2/5 | 1 | 2 | 0.3143 | -0.0857 | below_support | unresolved |
| advanced_first_line | Platinum-based Drug | permitted:condition=autoimmune_disease | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Poly(ADP-Ribose) Polymerase Inhibitor | inclusion:condition=diagnosis_confirmed | 1/1 | 10/11 | 0 | 1 | 0.0909 | 0.0 | below_support | unresolved |
| advanced_first_line | Programmed Death Ligand-1 Blocker | inclusion:condition=diagnosis_confirmed | 1/1 | 10/11 | 0 | 1 | 0.0909 | 0.0 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:BRAF=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:NTRK=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:RET=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:ROS1=positive | 2/7 | 2/5 | 1 | 1 | -0.1143 | -0.3143 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=active_infection | 5/7 | 2/5 | 0 | 2 | 0.3143 | -0.0857 | proposed | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=autoimmune_disease | 5/7 | 3/5 | 0 | 1 | 0.1143 | -0.0857 | proposed | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=bleeding_thrombosis | 1/7 | 1/5 | 1 | 2 | -0.0571 | -0.4571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=diagnosis_confirmed | 2/7 | 0/5 | 1 | 3 | 0.2857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=effusion | 1/7 | 0/5 | 0 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=hypersensitivity | 3/7 | 1/5 | 0 | 2 | 0.2286 | -0.1714 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=immunosuppression_steroids | 3/7 | 2/5 | 1 | 1 | 0.0286 | -0.1714 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=live_vaccine | 2/7 | 1/5 | 1 | 2 | 0.0857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=organ_transplant | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=other_malignancy | 2/7 | 2/5 | 1 | 1 | -0.1143 | -0.3143 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=pregnancy_or_breastfeeding | 2/7 | 2/5 | 1 | 2 | -0.1143 | -0.5143 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=recent_surgery | 3/7 | 2/5 | 0 | 1 | 0.0286 | -0.1714 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=tuberculosis | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=unresolved_toxicity | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:metastatic | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:recurrent | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=non_squamous | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=small_cell | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=squamous | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:ALK inhibitor | 1/7 | 0/5 | 0 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:CTLA-4 | 2/7 | 1/5 | 1 | 3 | 0.0857 | -0.5143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:EGFR inhibitor | 1/7 | 0/5 | 0 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:PD-1 | 3/7 | 2/5 | 1 | 2 | 0.0286 | -0.3714 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:PD-L1 | 2/7 | 2/5 | 1 | 2 | -0.1143 | -0.5143 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:chemotherapy | 2/7 | 0/5 | 1 | 3 | 0.2857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:immune checkpoint | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:radiotherapy | 2/7 | 1/5 | 1 | 3 | 0.0857 | -0.5143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_lines=0 | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ALK=positive | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ALK=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:EGFR=negative | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:EGFR=positive | 1/7 | 1/5 | 1 | 2 | -0.0571 | -0.4571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:EGFR=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:NTRK=positive | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@≥1% | 2/7 | 0/5 | 1 | 3 | 0.2857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:RET=positive | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ROS1=unknown | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=autoimmune_disease | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=cns_metastases | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=compliance | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=contraception | 4/7 | 2/5 | 0 | 2 | 0.1714 | -0.2286 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=immunosuppression_steroids | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=informed_consent | 2/7 | 1/5 | 0 | 2 | 0.0857 | -0.3143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=other_malignancy | 2/7 | 1/5 | 1 | 3 | 0.0857 | -0.5143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=pregnancy_or_breastfeeding | 2/7 | 1/5 | 1 | 3 | 0.0857 | -0.5143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=recent_radiotherapy | 1/7 | 1/5 | 1 | 2 | -0.0571 | -0.4571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=sex | 2/7 | 1/5 | 0 | 3 | 0.0857 | -0.5143 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=weight_loss | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:ecog_ps=0\|1 | 6/7 | 4/5 | 0 | 1 | 0.0571 | -0.1429 | proposed | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:ecog_ps=1 | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:extent:advanced | 4/7 | 1/5 | 0 | 2 | 0.3714 | -0.0286 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:histology=non_squamous | 5/7 | 4/5 | 1 | 0 | -0.0857 | -0.0857 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:histology=squamous | 4/7 | 2/5 | 1 | 1 | 0.1714 | -0.0286 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:bilirubin | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:creatinine clearance | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:hemoglobin | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:neutrophils | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:platelets | 1/7 | 1/5 | 1 | 3 | -0.0571 | -0.6571 | (not listed) | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:organ_function_unspecified=adequate | 3/7 | 2/5 | 0 | 2 | 0.0286 | -0.3714 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:ALK inhibitor | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=immunosuppression_steroids | 1/7 | 0/5 | 1 | 3 | 0.1429 | -0.4571 | below_support | unresolved |
| advanced_first_line | Topoisomerase Inhibitor | inclusion:condition=diagnosis_confirmed | 1/1 | 10/11 | 0 | 1 | 0.0909 | 0.0 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:biomarker:ALK=positive | 4/12 | 32/122 | 1 | 9 | 0.071 | -0.0027 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:biomarker:EGFR=positive | 4/12 | 37/122 | 1 | 10 | 0.0301 | -0.0519 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:biomarker:ROS1=positive | 2/12 | 9/122 | 2 | 13 | 0.0929 | -0.0137 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=bleeding_thrombosis | 1/12 | 29/122 | 2 | 15 | -0.1544 | -0.2773 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=cns_metastases | 6/12 | 62/122 | 1 | 5 | -0.0082 | -0.0492 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=diagnosis_confirmed | 1/12 | 27/122 | 2 | 14 | -0.138 | -0.2527 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=hiv | 6/12 | 57/122 | 0 | 12 | 0.0328 | -0.0656 | proposed | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=hypertension | 1/12 | 28/122 | 2 | 14 | -0.1462 | -0.2609 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=informed_consent | 1/12 | 11/122 | 2 | 15 | -0.0068 | -0.1298 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=investigator_judgment | 2/12 | 19/122 | 1 | 12 | 0.0109 | -0.0874 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=live_vaccine | 4/12 | 32/122 | 2 | 12 | 0.071 | -0.0273 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=neurologic_disorder | 2/12 | 29/122 | 2 | 9 | -0.071 | -0.1448 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=recent_radiotherapy | 5/12 | 56/122 | 2 | 12 | -0.0423 | -0.1407 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=serious_comorbidity | 3/12 | 17/122 | 2 | 14 | 0.1107 | -0.0041 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=tuberculosis | 4/12 | 28/122 | 2 | 15 | 0.1038 | -0.0191 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:condition=unresolved_toxicity | 1/12 | 20/122 | 2 | 15 | -0.0806 | -0.2036 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:extent:locally advanced | 1/12 | 8/122 | 2 | 15 | 0.0178 | -0.1052 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:extent:metastatic | 3/12 | 25/122 | 1 | 12 | 0.0451 | -0.0533 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:extent:unresectable | 1/12 | 8/122 | 2 | 15 | 0.0178 | -0.1052 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:CTLA-4 | 2/12 | 6/122 | 2 | 16 | 0.1175 | -0.0137 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:EGFR inhibitor | 1/12 | 10/122 | 2 | 15 | 0.0014 | -0.1216 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:PD-1 | 2/12 | 27/122 | 2 | 13 | -0.0546 | -0.1612 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:PD-L1 | 3/12 | 27/122 | 2 | 13 | 0.0287 | -0.0779 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:pemetrexed | 1/12 | 4/122 | 2 | 16 | 0.0505 | -0.0806 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:platinum | 1/12 | 10/122 | 2 | 14 | 0.0014 | -0.1134 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:radiotherapy | 4/12 | 42/122 | 2 | 14 | -0.0109 | -0.1257 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:taxane | 1/12 | 2/122 | 2 | 16 | 0.0669 | -0.0642 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_lines=0 | 1/12 | 1/122 | 2 | 16 | 0.0751 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:prior_lines=1\|2\|3+ | 1/12 | 5/122 | 2 | 15 | 0.0423 | -0.0806 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | exclusion:stage:IV | 1/12 | 3/122 | 2 | 16 | 0.0587 | -0.0724 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ALK=negative | 2/12 | 11/122 | 1 | 16 | 0.0765 | -0.0546 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ALK=negative\|positive | 1/12 | 0/122 | 2 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ALK=positive | 2/12 | 19/122 | 2 | 16 | 0.0109 | -0.1202 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:EGFR=negative | 2/12 | 18/122 | 1 | 14 | 0.0191 | -0.0956 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:EGFR=negative\|positive | 1/12 | 0/122 | 2 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:EGFR=positive | 2/12 | 37/122 | 2 | 13 | -0.1366 | -0.2432 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:PD-L1=@<1% | 1/12 | 1/122 | 1 | 17 | 0.0751 | -0.0642 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:PD-L1=@≥1% | 1/12 | 3/122 | 2 | 17 | 0.0587 | -0.0806 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:RET=positive | 1/12 | 5/122 | 2 | 17 | 0.0423 | -0.097 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ROS1=negative | 1/12 | 6/122 | 1 | 17 | 0.0342 | -0.1052 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ROS1=positive | 1/12 | 6/122 | 2 | 17 | 0.0342 | -0.1052 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=active_infection | 1/12 | 5/122 | 1 | 16 | 0.0423 | -0.0888 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=cardiac_disease | 1/12 | 9/122 | 1 | 16 | 0.0096 | -0.1216 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=cns_metastases | 2/12 | 11/122 | 2 | 17 | 0.0765 | -0.0628 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=compliance | 2/12 | 10/122 | 1 | 14 | 0.0847 | -0.0301 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=hiv | 1/12 | 10/122 | 1 | 16 | 0.0014 | -0.1298 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=immunosuppression_steroids | 3/12 | 26/122 | 2 | 14 | 0.0369 | -0.0779 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=informed_consent | 3/12 | 43/122 | 2 | 12 | -0.1025 | -0.2008 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=life_expectancy | 5/12 | 50/122 | 2 | 11 | 0.0068 | -0.0833 | proposed | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=measurable_disease | 7/12 | 71/122 | 1 | 6 | 0.0014 | -0.0478 | proposed | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=neurologic_disorder | 1/12 | 0/122 | 1 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=other_investigational | 1/12 | 4/122 | 2 | 16 | 0.0505 | -0.0806 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=other_malignancy | 1/12 | 9/122 | 1 | 16 | 0.0096 | -0.1216 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=pneumonitis_ild | 1/12 | 11/122 | 2 | 17 | -0.0068 | -0.1462 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=pregnancy_or_breastfeeding | 1/12 | 14/122 | 2 | 17 | -0.0314 | -0.1708 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=pulmonary_function | 1/12 | 9/122 | 2 | 17 | 0.0096 | -0.1298 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=tissue_available | 1/12 | 20/122 | 2 | 15 | -0.0806 | -0.2036 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:condition=weight_loss | 1/12 | 0/122 | 2 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:ecog_ps=1 | 1/12 | 1/122 | 2 | 16 | 0.0751 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:extent:advanced | 2/12 | 24/122 | 1 | 10 | -0.0301 | -0.112 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:extent:locally advanced | 2/12 | 23/122 | 2 | 13 | -0.0219 | -0.1284 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:extent:recurrent | 4/12 | 30/122 | 1 | 13 | 0.0874 | -0.0191 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:extent:unresectable | 1/12 | 15/122 | 2 | 15 | -0.0396 | -0.1626 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:lab:ALT | 3/12 | 27/122 | 1 | 15 | 0.0287 | -0.0943 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:lab:AST | 3/12 | 21/122 | 1 | 16 | 0.0779 | -0.0533 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:lab:bilirubin | 4/12 | 27/122 | 1 | 16 | 0.112 | -0.0191 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:lab:creatinine | 1/12 | 19/122 | 2 | 17 | -0.0724 | -0.2117 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:lab:hemoglobin | 3/12 | 26/122 | 2 | 15 | 0.0369 | -0.0861 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:lab:leukocytes | 1/12 | 4/122 | 2 | 16 | 0.0505 | -0.0806 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:lab:neutrophils | 4/12 | 29/122 | 1 | 15 | 0.0956 | -0.0273 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:lab:platelets | 4/12 | 30/122 | 1 | 15 | 0.0874 | -0.0355 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:prior_agent:ALK inhibitor | 1/12 | 4/122 | 2 | 17 | 0.0505 | -0.0888 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:prior_agent:EGFR inhibitor | 1/12 | 11/122 | 2 | 16 | -0.0068 | -0.138 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:prior_agent:chemotherapy | 4/12 | 38/122 | 1 | 11 | 0.0219 | -0.0683 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:prior_agent:immune checkpoint | 2/12 | 11/122 | 1 | 17 | 0.0765 | -0.0628 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:prior_agent:platinum | 3/12 | 24/122 | 2 | 12 | 0.0533 | -0.0451 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:prior_lines=1\|2\|3+ | 2/12 | 18/122 | 2 | 14 | 0.0191 | -0.0956 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:setting_word:consolidation | 1/12 | 5/122 | 2 | 17 | 0.0423 | -0.097 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:setting_word:maintenance | 1/12 | 2/122 | 2 | 17 | 0.0669 | -0.0724 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:stage:III | 3/12 | 29/122 | 1 | 13 | 0.0123 | -0.0943 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | inclusion:stage:I\|II\|III | 2/12 | 5/122 | 2 | 17 | 0.1257 | -0.0137 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:biomarker:EGFR=positive | 1/12 | 0/122 | 3 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:condition=autoimmune_disease | 1/12 | 4/122 | 2 | 17 | 0.0505 | -0.0888 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:condition=contraception | 1/12 | 1/122 | 2 | 17 | 0.0751 | -0.0642 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:extent:advanced | 1/12 | 2/122 | 2 | 17 | 0.0669 | -0.0724 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:extent:metastatic | 1/12 | 7/122 | 2 | 17 | 0.026 | -0.1134 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:prior_agent:EGFR inhibitor | 1/12 | 0/122 | 3 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:prior_agent:VEGF inhibitor | 1/12 | 1/122 | 2 | 17 | 0.0751 | -0.0642 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:prior_agent:chemotherapy | 2/12 | 15/122 | 1 | 17 | 0.0437 | -0.0956 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:prior_lines=1 | 1/12 | 2/122 | 2 | 17 | 0.0669 | -0.0724 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:prior_lines=1\|2 | 1/12 | 0/122 | 3 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:setting_word:adjuvant | 1/12 | 16/122 | 2 | 17 | -0.0478 | -0.1872 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:setting_word:neoadjuvant | 1/12 | 11/122 | 2 | 17 | -0.0068 | -0.1462 | (not listed) | unresolved |
| all trials | CTLA-4-directed Blocking Antibody | permitted:stage:IV | 1/12 | 0/122 | 3 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:biomarker:ALK=positive | 11/36 | 25/98 | 0 | 10 | 0.0505 | -0.0516 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:biomarker:BRAF=positive | 2/36 | 3/98 | 2 | 15 | 0.0249 | -0.1281 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:biomarker:BRAF=unknown | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:biomarker:EGFR=negative | 1/36 | 1/98 | 2 | 16 | 0.0176 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:biomarker:NTRK=unknown | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:biomarker:RET=unknown | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:biomarker:ROS1=positive | 3/36 | 8/98 | 2 | 13 | 0.0017 | -0.131 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=anticoagulant_use | 1/36 | 6/98 | 2 | 16 | -0.0334 | -0.1967 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=contraception | 2/36 | 3/98 | 2 | 16 | 0.0249 | -0.1383 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=diagnosis_confirmed | 11/36 | 17/98 | 2 | 14 | 0.1321 | -0.0108 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=effusion | 7/36 | 11/98 | 1 | 14 | 0.0822 | -0.0607 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=gi_perforation_fistula | 2/36 | 5/98 | 2 | 16 | 0.0045 | -0.1587 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=hepatitis | 16/36 | 43/98 | 1 | 11 | 0.0057 | -0.1066 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=informed_consent | 2/36 | 10/98 | 2 | 15 | -0.0465 | -0.1995 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=live_vaccine | 10/36 | 26/98 | 2 | 12 | 0.0125 | -0.11 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=measurable_disease | 2/36 | 5/98 | 2 | 16 | 0.0045 | -0.1587 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=neurologic_disorder | 8/36 | 23/98 | 2 | 9 | -0.0125 | -0.1043 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=organ_impairment | 1/36 | 8/98 | 2 | 15 | -0.0539 | -0.2069 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=organ_transplant | 11/36 | 24/98 | 2 | 15 | 0.0607 | -0.0924 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=other_investigational | 13/36 | 31/98 | 2 | 13 | 0.0448 | -0.0879 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=recent_radiotherapy | 18/36 | 43/98 | 1 | 13 | 0.0612 | -0.0714 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=sex | 1/36 | 2/98 | 2 | 16 | 0.0074 | -0.1559 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=tuberculosis | 9/36 | 23/98 | 2 | 15 | 0.0153 | -0.1378 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=unresolved_toxicity | 5/36 | 16/98 | 2 | 15 | -0.0244 | -0.1774 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=vitamin_premedication | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:condition=weight_loss | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:extent:advanced | 1/36 | 3/98 | 2 | 15 | -0.0028 | -0.1559 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:extent:locally advanced | 1/36 | 8/98 | 2 | 15 | -0.0539 | -0.2069 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:extent:unresectable | 2/36 | 7/98 | 2 | 15 | -0.0159 | -0.1689 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:histology=large_cell | 2/36 | 3/98 | 2 | 16 | 0.0249 | -0.1383 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:histology=non_squamous | 1/36 | 5/98 | 2 | 15 | -0.0232 | -0.1763 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:histology=small_cell | 4/36 | 11/98 | 2 | 16 | -0.0011 | -0.1644 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:histology=squamous | 7/36 | 7/98 | 2 | 15 | 0.123 | -0.03 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:lab:creatinine clearance | 1/36 | 2/98 | 2 | 16 | 0.0074 | -0.1559 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:ALK inhibitor | 2/36 | 4/98 | 1 | 16 | 0.0147 | -0.1485 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:CTLA-4 | 6/36 | 2/98 | 2 | 16 | 0.1463 | -0.017 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:PD-1 | 11/36 | 18/98 | 2 | 13 | 0.1219 | -0.0108 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:PD-L1 | 11/36 | 19/98 | 2 | 13 | 0.1117 | -0.021 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:VEGF inhibitor | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:chemotherapy | 9/36 | 24/98 | 1 | 13 | 0.0051 | -0.1276 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:immune checkpoint | 9/36 | 16/98 | 2 | 14 | 0.0867 | -0.0561 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:pemetrexed | 4/36 | 1/98 | 2 | 16 | 0.1009 | -0.0624 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:platinum | 5/36 | 6/98 | 2 | 14 | 0.0777 | -0.0652 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:radiotherapy | 14/36 | 32/98 | 1 | 15 | 0.0624 | -0.0907 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:taxane | 2/36 | 1/98 | 2 | 16 | 0.0454 | -0.1179 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_lines=1 | 1/36 | 5/98 | 2 | 15 | -0.0232 | -0.1763 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:prior_lines=1\|2\|3+ | 2/36 | 4/98 | 2 | 15 | 0.0147 | -0.1383 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:resection:resected | 1/36 | 1/98 | 2 | 16 | 0.0176 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:setting_word:adjuvant | 1/36 | 8/98 | 2 | 15 | -0.0539 | -0.2069 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:setting_word:consolidation | 2/36 | 0/98 | 2 | 16 | 0.0556 | -0.1077 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:setting_word:maintenance | 1/36 | 3/98 | 2 | 15 | -0.0028 | -0.1559 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:stage:I | 1/36 | 2/98 | 2 | 16 | 0.0074 | -0.1559 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:stage:III | 1/36 | 4/98 | 2 | 16 | -0.013 | -0.1763 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:stage:III\|IV | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:stage:II\|III | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | exclusion:stage:I\|III | 1/36 | 0/98 | 2 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:age=stated | 15/36 | 40/98 | 1 | 12 | 0.0085 | -0.1139 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ALK=negative | 5/36 | 8/98 | 2 | 15 | 0.0573 | -0.0958 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ALK=positive | 4/36 | 17/98 | 3 | 15 | -0.0624 | -0.2154 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ALK=unknown | 2/36 | 0/98 | 3 | 16 | 0.0556 | -0.1077 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:EGFR=positive | 12/36 | 27/98 | 3 | 12 | 0.0578 | -0.0646 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:EGFR=unknown | 2/36 | 1/98 | 3 | 15 | 0.0454 | -0.1077 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:KRAS=positive | 2/36 | 3/98 | 3 | 16 | 0.0249 | -0.1383 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:MET=positive | 1/36 | 2/98 | 3 | 16 | 0.0074 | -0.1559 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:NTRK=positive | 1/36 | 1/98 | 3 | 16 | 0.0176 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=@1-49% | 1/36 | 0/98 | 3 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=@>=1% | 1/36 | 0/98 | 3 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=@≥1% | 1/36 | 3/98 | 3 | 16 | -0.0028 | -0.1661 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 1/36 | 3/98 | 3 | 16 | -0.0028 | -0.1661 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=positive | 2/36 | 4/98 | 3 | 16 | 0.0147 | -0.1485 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:RET=positive | 1/36 | 5/98 | 3 | 16 | -0.0232 | -0.1865 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ROS1=negative | 3/36 | 4/98 | 3 | 15 | 0.0425 | -0.1105 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ROS1=unknown | 1/36 | 0/98 | 3 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=active_infection | 3/36 | 3/98 | 2 | 15 | 0.0527 | -0.1003 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=anticoagulant_use | 2/36 | 1/98 | 3 | 16 | 0.0454 | -0.1179 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=autoimmune_disease | 2/36 | 1/98 | 3 | 16 | 0.0454 | -0.1179 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=bleeding_thrombosis | 1/36 | 4/98 | 3 | 16 | -0.013 | -0.1763 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=cardiac_disease | 3/36 | 7/98 | 2 | 15 | 0.0119 | -0.1412 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=cns_metastases | 6/36 | 7/98 | 3 | 16 | 0.0952 | -0.068 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=gi_perforation_fistula | 2/36 | 2/98 | 3 | 16 | 0.0351 | -0.1281 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=hepatitis | 4/36 | 6/98 | 3 | 16 | 0.0499 | -0.1134 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=hiv | 6/36 | 5/98 | 2 | 15 | 0.1156 | -0.0374 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=hypersensitivity | 2/36 | 1/98 | 3 | 16 | 0.0454 | -0.1179 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=hypertension | 3/36 | 7/98 | 3 | 16 | 0.0119 | -0.1514 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=interacting_medication | 1/36 | 2/98 | 3 | 16 | 0.0074 | -0.1559 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=investigator_judgment | 2/36 | 8/98 | 3 | 16 | -0.0261 | -0.1893 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=life_expectancy | 14/36 | 41/98 | 2 | 11 | -0.0295 | -0.1417 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=live_vaccine | 1/36 | 0/98 | 3 | 16 | 0.0278 | -0.1355 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=malabsorption | 1/36 | 7/98 | 3 | 16 | -0.0437 | -0.2069 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=measurable_disease | 21/36 | 57/98 | 1 | 6 | 0.0017 | -0.0595 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=organ_transplant | 1/36 | 1/98 | 3 | 16 | 0.0176 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=pneumonitis_ild | 7/36 | 5/98 | 3 | 16 | 0.1434 | -0.0198 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 4/36 | 11/98 | 3 | 16 | -0.0011 | -0.1644 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=pulmonary_function | 2/36 | 8/98 | 3 | 16 | -0.0261 | -0.1893 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=qtc | 1/36 | 3/98 | 3 | 16 | -0.0028 | -0.1661 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=recent_radiotherapy | 8/36 | 26/98 | 3 | 13 | -0.0431 | -0.1757 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=recent_surgery | 12/36 | 32/98 | 2 | 14 | 0.0068 | -0.1361 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=serious_comorbidity | 1/36 | 1/98 | 3 | 16 | 0.0176 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=sex | 9/36 | 16/98 | 2 | 14 | 0.0867 | -0.0561 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=tissue_available | 5/36 | 16/98 | 3 | 14 | -0.0244 | -0.1672 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:condition=unresolved_toxicity | 3/36 | 11/98 | 3 | 14 | -0.0289 | -0.1718 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:extent:locally advanced | 7/36 | 18/98 | 3 | 12 | 0.0108 | -0.1117 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:extent:unresectable | 5/36 | 11/98 | 3 | 14 | 0.0266 | -0.1162 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:histology=adenocarcinoma | 1/36 | 3/98 | 3 | 15 | -0.0028 | -0.1559 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:histology=squamous | 5/36 | 14/98 | 2 | 10 | -0.004 | -0.106 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:lab:ALT | 7/36 | 23/98 | 2 | 14 | -0.0402 | -0.1831 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:lab:AST | 6/36 | 18/98 | 2 | 15 | -0.017 | -0.1701 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:lab:bilirubin | 7/36 | 24/98 | 2 | 15 | -0.0505 | -0.2035 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:lab:creatinine | 4/36 | 16/98 | 3 | 16 | -0.0522 | -0.2154 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:lab:creatinine clearance | 8/36 | 19/98 | 2 | 14 | 0.0283 | -0.1145 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:lab:leukocytes | 1/36 | 4/98 | 3 | 15 | -0.013 | -0.1661 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:organ_function_unspecified=adequate | 10/36 | 29/98 | 2 | 12 | -0.0181 | -0.1406 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:ALK inhibitor | 1/36 | 4/98 | 3 | 16 | -0.013 | -0.1763 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:CTLA-4 | 1/36 | 2/98 | 3 | 16 | 0.0074 | -0.1559 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:EGFR inhibitor | 7/36 | 5/98 | 3 | 15 | 0.1434 | -0.0096 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:PD-1 | 1/36 | 6/98 | 3 | 16 | -0.0334 | -0.1967 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:PD-L1 | 1/36 | 5/98 | 3 | 16 | -0.0232 | -0.1865 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:immune checkpoint | 3/36 | 10/98 | 3 | 15 | -0.0187 | -0.1718 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:pemetrexed | 3/36 | 2/98 | 3 | 15 | 0.0629 | -0.0901 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_lines=0 | 11/36 | 22/98 | 2 | 11 | 0.0811 | -0.0312 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_lines=1 | 1/36 | 4/98 | 3 | 14 | -0.013 | -0.1559 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:prior_lines=1\|2\|3+ | 5/36 | 15/98 | 3 | 13 | -0.0142 | -0.1468 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:resection:resectable | 6/36 | 3/98 | 3 | 15 | 0.1361 | -0.017 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:resection:resected | 5/36 | 10/98 | 2 | 15 | 0.0368 | -0.1162 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:setting_word:adjuvant | 5/36 | 19/98 | 2 | 13 | -0.055 | -0.1876 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:setting_word:consolidation | 3/36 | 3/98 | 3 | 16 | 0.0527 | -0.1105 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:setting_word:maintenance | 1/36 | 2/98 | 3 | 16 | 0.0074 | -0.1559 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:setting_word:neoadjuvant | 4/36 | 12/98 | 2 | 14 | -0.0113 | -0.1542 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:stage:I | 2/36 | 2/98 | 2 | 16 | 0.0351 | -0.1281 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:stage:II | 3/36 | 2/98 | 2 | 15 | 0.0629 | -0.0901 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:stage:III | 7/36 | 25/98 | 3 | 11 | -0.0607 | -0.1729 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:stage:II\|III | 6/36 | 8/98 | 2 | 15 | 0.085 | -0.068 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:stage:IV | 14/36 | 27/98 | 3 | 13 | 0.1134 | -0.0193 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | inclusion:stage:I\|II\|III | 1/36 | 6/98 | 3 | 16 | -0.0334 | -0.1967 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:biomarker:EGFR=negative | 1/36 | 0/98 | 3 | 17 | 0.0278 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:biomarker:EGFR=positive | 1/36 | 0/98 | 3 | 17 | 0.0278 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:condition=autoimmune_disease | 2/36 | 3/98 | 3 | 16 | 0.0249 | -0.1383 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:condition=measurable_disease | 1/36 | 0/98 | 3 | 17 | 0.0278 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:condition=pneumonitis_ild | 1/36 | 0/98 | 3 | 17 | 0.0278 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:condition=recent_radiotherapy | 3/36 | 9/98 | 3 | 16 | -0.0085 | -0.1718 | (not listed) | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:extent:locally advanced | 2/36 | 2/98 | 3 | 17 | 0.0351 | -0.1383 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:extent:metastatic | 4/36 | 4/98 | 3 | 16 | 0.0703 | -0.093 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:extent:recurrent | 4/36 | 0/98 | 3 | 17 | 0.1111 | -0.0624 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:prior_agent:EGFR inhibitor | 1/36 | 0/98 | 3 | 17 | 0.0278 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:prior_agent:chemotherapy | 7/36 | 10/98 | 3 | 15 | 0.0924 | -0.0607 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:prior_agent:immune checkpoint | 2/36 | 2/98 | 3 | 17 | 0.0351 | -0.1383 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:prior_agent:radiotherapy | 7/36 | 8/98 | 3 | 17 | 0.1128 | -0.0607 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:prior_lines=1\|2 | 1/36 | 0/98 | 3 | 17 | 0.0278 | -0.1457 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:setting_word:adjuvant | 6/36 | 11/98 | 3 | 16 | 0.0544 | -0.1088 | proposed | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:setting_word:neoadjuvant | 4/36 | 8/98 | 3 | 16 | 0.0295 | -0.1338 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:stage:III | 2/36 | 0/98 | 3 | 17 | 0.0556 | -0.1179 | below_support | unresolved |
| all trials | Folate Analog Metabolic Inhibitor | permitted:stage:IV | 1/36 | 0/98 | 3 | 17 | 0.0278 | -0.1457 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:biomarker:BRAF=positive | 4/40 | 1/94 | 1 | 16 | 0.0894 | -0.0809 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:biomarker:EGFR=negative | 2/40 | 0/94 | 2 | 16 | 0.05 | -0.1202 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:biomarker:KRAS=positive | 1/40 | 0/94 | 1 | 16 | 0.025 | -0.1452 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:biomarker:MET=positive | 1/40 | 0/94 | 2 | 16 | 0.025 | -0.1452 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:biomarker:NTRK=positive | 1/40 | 0/94 | 1 | 16 | 0.025 | -0.1452 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:biomarker:RET=positive | 2/40 | 0/94 | 1 | 16 | 0.05 | -0.1202 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:biomarker:ROS1=positive | 4/40 | 7/94 | 1 | 14 | 0.0255 | -0.1234 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=anticoagulant_use | 3/40 | 4/94 | 2 | 16 | 0.0324 | -0.1378 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=cns_metastases | 21/40 | 47/94 | 0 | 6 | 0.025 | -0.0388 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=compliance | 3/40 | 2/94 | 2 | 15 | 0.0537 | -0.1059 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=contraception | 1/40 | 4/94 | 2 | 16 | -0.0176 | -0.1878 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=diagnosis_confirmed | 7/40 | 21/94 | 2 | 14 | -0.0484 | -0.1973 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=effusion | 6/40 | 12/94 | 2 | 13 | 0.0223 | -0.116 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=gi_perforation_fistula | 4/40 | 3/94 | 2 | 16 | 0.0681 | -0.1021 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=hypertension | 12/40 | 17/94 | 2 | 14 | 0.1191 | -0.0298 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=interacting_medication | 6/40 | 4/94 | 2 | 15 | 0.1074 | -0.0521 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=measurable_disease | 2/40 | 5/94 | 2 | 16 | -0.0032 | -0.1734 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=organ_impairment | 4/40 | 5/94 | 2 | 15 | 0.0468 | -0.1128 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=other_malignancy | 22/40 | 42/94 | 2 | 11 | 0.1032 | -0.0138 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=prior_enrollment | 1/40 | 0/94 | 2 | 16 | 0.025 | -0.1452 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=pulmonary_function | 1/40 | 1/94 | 2 | 15 | 0.0144 | -0.1452 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=recent_radiotherapy | 21/40 | 40/94 | 2 | 12 | 0.0995 | -0.0282 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=recent_surgery | 20/40 | 37/94 | 1 | 10 | 0.1064 | 0.0 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=serious_comorbidity | 7/40 | 13/94 | 2 | 14 | 0.0367 | -0.1122 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=substance_or_psychiatric | 11/40 | 17/94 | 1 | 13 | 0.0941 | -0.0441 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:condition=unresolved_toxicity | 5/40 | 16/94 | 2 | 15 | -0.0452 | -0.2048 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:extent:metastatic | 7/40 | 21/94 | 2 | 11 | -0.0484 | -0.1654 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:extent:recurrent | 10/40 | 16/94 | 2 | 15 | 0.0798 | -0.0798 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:histology=adenocarcinoma | 1/40 | 2/94 | 2 | 16 | 0.0037 | -0.1665 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:histology=squamous | 4/40 | 10/94 | 2 | 15 | -0.0064 | -0.166 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:lab:ALT | 1/40 | 1/94 | 2 | 16 | 0.0144 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:lab:AST | 1/40 | 1/94 | 2 | 16 | 0.0144 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:lab:bilirubin | 1/40 | 0/94 | 2 | 16 | 0.025 | -0.1452 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:lab:creatinine | 1/40 | 1/94 | 2 | 16 | 0.0144 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_agent:ALK inhibitor | 3/40 | 3/94 | 2 | 15 | 0.0431 | -0.1165 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_agent:EGFR inhibitor | 3/40 | 8/94 | 2 | 15 | -0.0101 | -0.1697 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_agent:MET inhibitor | 2/40 | 1/94 | 0 | 16 | 0.0394 | -0.1309 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_agent:chemotherapy | 12/40 | 21/94 | 2 | 12 | 0.0766 | -0.0511 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_agent:docetaxel | 2/40 | 6/94 | 2 | 14 | -0.0138 | -0.1628 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_agent:pemetrexed | 2/40 | 3/94 | 2 | 16 | 0.0181 | -0.1521 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_agent:platinum | 3/40 | 8/94 | 2 | 14 | -0.0101 | -0.159 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_agent:radiotherapy | 17/40 | 29/94 | 2 | 14 | 0.1165 | -0.0324 | proposed | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_lines=1 | 1/40 | 5/94 | 2 | 15 | -0.0282 | -0.1878 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:prior_lines=1\|2\|3+ | 1/40 | 5/94 | 2 | 15 | -0.0282 | -0.1878 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:resection:resected | 1/40 | 1/94 | 2 | 16 | 0.0144 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:stage:I | 2/40 | 1/94 | 2 | 16 | 0.0394 | -0.1309 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:stage:III | 1/40 | 4/94 | 2 | 16 | -0.0176 | -0.1878 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:stage:II\|III | 1/40 | 0/94 | 2 | 16 | 0.025 | -0.1452 | below_support | unresolved |
| all trials | Kinase Inhibitor | exclusion:stage:IV | 1/40 | 3/94 | 2 | 16 | -0.0069 | -0.1771 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | exclusion:stage:I\|III | 1/40 | 0/94 | 2 | 16 | 0.025 | -0.1452 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:ALK=negative | 3/40 | 10/94 | 2 | 15 | -0.0314 | -0.191 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:ALK=positive | 11/40 | 10/94 | 1 | 17 | 0.1686 | -0.0122 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:KRAS=positive | 3/40 | 2/94 | 2 | 17 | 0.0537 | -0.1271 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:MET=negative | 1/40 | 1/94 | 1 | 17 | 0.0144 | -0.1665 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:MET=positive | 1/40 | 2/94 | 2 | 17 | 0.0037 | -0.1771 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:PD-L1=@<1% | 1/40 | 1/94 | 2 | 16 | 0.0144 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:PD-L1=@≥1% | 2/40 | 2/94 | 2 | 17 | 0.0287 | -0.1521 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 1/40 | 3/94 | 2 | 17 | -0.0069 | -0.1878 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:PD-L1=positive | 1/40 | 5/94 | 2 | 17 | -0.0282 | -0.209 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:PD-L1=unknown | 1/40 | 0/94 | 2 | 17 | 0.025 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:RET=positive | 3/40 | 3/94 | 2 | 17 | 0.0431 | -0.1378 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:ROS1=negative | 3/40 | 4/94 | 2 | 16 | 0.0324 | -0.1378 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:biomarker:ROS1=positive | 2/40 | 5/94 | 2 | 17 | -0.0032 | -0.184 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=active_infection | 2/40 | 4/94 | 2 | 15 | 0.0074 | -0.1521 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=anticoagulant_use | 1/40 | 2/94 | 2 | 17 | 0.0037 | -0.1771 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=bleeding_thrombosis | 3/40 | 2/94 | 2 | 17 | 0.0537 | -0.1271 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=cardiac_disease | 4/40 | 6/94 | 2 | 15 | 0.0362 | -0.1234 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=cns_metastases | 4/40 | 9/94 | 2 | 17 | 0.0043 | -0.1766 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=contraception | 23/40 | 43/94 | 2 | 13 | 0.1176 | -0.0207 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=diagnosis_confirmed | 32/40 | 73/94 | 0 | 7 | 0.0234 | -0.0511 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=effusion | 1/40 | 0/94 | 2 | 17 | 0.025 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=gi_perforation_fistula | 4/40 | 0/94 | 2 | 17 | 0.1 | -0.0809 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=hepatitis | 3/40 | 7/94 | 2 | 17 | 0.0005 | -0.1803 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=hiv | 4/40 | 7/94 | 2 | 15 | 0.0255 | -0.134 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=hypersensitivity | 1/40 | 2/94 | 2 | 17 | 0.0037 | -0.1771 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=interacting_medication | 3/40 | 0/94 | 2 | 17 | 0.075 | -0.1059 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=investigator_judgment | 4/40 | 6/94 | 2 | 17 | 0.0362 | -0.1447 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=life_expectancy | 16/40 | 39/94 | 1 | 12 | -0.0149 | -0.1426 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=malabsorption | 5/40 | 3/94 | 2 | 17 | 0.0931 | -0.0878 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=other_malignancy | 3/40 | 7/94 | 2 | 15 | 0.0005 | -0.159 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=pneumonitis_ild | 5/40 | 7/94 | 2 | 17 | 0.0505 | -0.1303 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 5/40 | 10/94 | 2 | 17 | 0.0186 | -0.1622 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=pulmonary_function | 2/40 | 8/94 | 2 | 17 | -0.0351 | -0.216 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=qtc | 4/40 | 0/94 | 2 | 17 | 0.1 | -0.0809 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=recent_radiotherapy | 11/40 | 23/94 | 2 | 14 | 0.0303 | -0.1186 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=recent_surgery | 13/40 | 31/94 | 2 | 14 | -0.0048 | -0.1537 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=sex | 7/40 | 18/94 | 2 | 14 | -0.0165 | -0.1654 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=substance_or_psychiatric | 1/40 | 1/94 | 2 | 17 | 0.0144 | -0.1665 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:condition=tissue_available | 8/40 | 13/94 | 2 | 15 | 0.0617 | -0.0979 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:extent:locally advanced | 8/40 | 17/94 | 2 | 13 | 0.0191 | -0.1191 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:extent:recurrent | 9/40 | 25/94 | 2 | 12 | -0.041 | -0.1686 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:extent:unresectable | 5/40 | 11/94 | 1 | 16 | 0.008 | -0.1622 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:histology=adenocarcinoma | 1/40 | 3/94 | 2 | 16 | -0.0069 | -0.1771 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:histology=large_cell | 1/40 | 0/94 | 2 | 17 | 0.025 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:histology=non_squamous | 18/40 | 39/94 | 2 | 7 | 0.0351 | -0.0394 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:histology=small_cell | 1/40 | 3/94 | 2 | 17 | -0.0069 | -0.1878 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:lab:ALT | 9/40 | 21/94 | 2 | 14 | 0.0016 | -0.1473 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:lab:AST | 7/40 | 17/94 | 2 | 15 | -0.0059 | -0.1654 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:lab:bilirubin | 9/40 | 22/94 | 2 | 15 | -0.009 | -0.1686 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:lab:creatinine | 8/40 | 12/94 | 2 | 17 | 0.0723 | -0.1085 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:lab:hemoglobin | 9/40 | 20/94 | 2 | 15 | 0.0122 | -0.1473 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:lab:leukocytes | 1/40 | 4/94 | 2 | 16 | -0.0176 | -0.1878 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:lab:neutrophils | 10/40 | 23/94 | 2 | 14 | 0.0053 | -0.1436 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:lab:platelets | 10/40 | 24/94 | 2 | 14 | -0.0053 | -0.1543 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:organ_function_unspecified=adequate | 13/40 | 26/94 | 0 | 14 | 0.0484 | -0.1005 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:ALK inhibitor | 2/40 | 3/94 | 2 | 17 | 0.0181 | -0.1628 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:EGFR inhibitor | 6/40 | 6/94 | 1 | 17 | 0.0862 | -0.0947 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:PD-1 | 2/40 | 5/94 | 2 | 17 | -0.0032 | -0.184 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:PD-L1 | 2/40 | 4/94 | 2 | 17 | 0.0074 | -0.1734 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:VEGF inhibitor | 2/40 | 0/94 | 2 | 17 | 0.05 | -0.1309 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:docetaxel | 2/40 | 2/94 | 1 | 17 | 0.0287 | -0.1521 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:immune checkpoint | 3/40 | 10/94 | 2 | 16 | -0.0314 | -0.2016 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:pemetrexed | 1/40 | 4/94 | 1 | 17 | -0.0176 | -0.1984 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_agent:radiotherapy | 8/40 | 22/94 | 2 | 13 | -0.034 | -0.1723 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_lines=0\|1\|2 | 1/40 | 0/94 | 2 | 17 | 0.025 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_lines=1 | 2/40 | 3/94 | 1 | 16 | 0.0181 | -0.1521 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_lines=1\|2 | 1/40 | 0/94 | 1 | 17 | 0.025 | -0.1559 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_lines=1\|2\|3+ | 5/40 | 15/94 | 2 | 14 | -0.0346 | -0.1835 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:prior_lines=2 | 2/40 | 2/94 | 2 | 16 | 0.0287 | -0.1415 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:resection:resected | 5/40 | 10/94 | 2 | 15 | 0.0186 | -0.141 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:setting_word:adjuvant | 8/40 | 16/94 | 2 | 13 | 0.0298 | -0.1085 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:setting_word:consolidation | 2/40 | 4/94 | 2 | 17 | 0.0074 | -0.1734 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:setting_word:maintenance | 1/40 | 2/94 | 2 | 17 | 0.0037 | -0.1771 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:setting_word:neoadjuvant | 5/40 | 11/94 | 2 | 14 | 0.008 | -0.141 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:stage:I | 1/40 | 3/94 | 2 | 16 | -0.0069 | -0.1771 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:stage:II | 1/40 | 4/94 | 2 | 15 | -0.0176 | -0.1771 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:stage:III\|IV | 6/40 | 13/94 | 1 | 12 | 0.0117 | -0.116 | proposed | unresolved |
| all trials | Kinase Inhibitor | inclusion:stage:II\|III | 4/40 | 10/94 | 2 | 15 | -0.0064 | -0.166 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:stage:IV | 11/40 | 30/94 | 2 | 14 | -0.0441 | -0.1931 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | inclusion:stage:I\|II | 2/40 | 2/94 | 2 | 17 | 0.0287 | -0.1521 | below_support | unresolved |
| all trials | Kinase Inhibitor | inclusion:stage:I\|II\|III | 2/40 | 5/94 | 2 | 17 | -0.0032 | -0.184 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | permitted:biomarker:EGFR=negative | 1/40 | 0/94 | 2 | 18 | 0.025 | -0.1665 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:condition=cns_metastases | 5/40 | 1/94 | 2 | 18 | 0.1144 | -0.0771 | proposed | unresolved |
| all trials | Kinase Inhibitor | permitted:condition=contraception | 1/40 | 1/94 | 2 | 17 | 0.0144 | -0.1665 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:condition=immunosuppression_steroids | 3/40 | 2/94 | 2 | 17 | 0.0537 | -0.1271 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:condition=other_malignancy | 2/40 | 0/94 | 2 | 18 | 0.05 | -0.1415 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:condition=pneumonitis_ild | 1/40 | 0/94 | 2 | 18 | 0.025 | -0.1665 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:condition=pregnancy_or_breastfeeding | 1/40 | 0/94 | 2 | 18 | 0.025 | -0.1665 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:condition=recent_radiotherapy | 4/40 | 8/94 | 2 | 17 | 0.0149 | -0.166 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:condition=recent_surgery | 2/40 | 0/94 | 2 | 18 | 0.05 | -0.1415 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:extent:advanced | 1/40 | 2/94 | 2 | 17 | 0.0037 | -0.1771 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:extent:metastatic | 3/40 | 5/94 | 2 | 17 | 0.0218 | -0.159 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:histology=adenocarcinoma | 1/40 | 0/94 | 2 | 18 | 0.025 | -0.1665 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:prior_agent:chemotherapy | 6/40 | 11/94 | 2 | 16 | 0.033 | -0.1372 | proposed | unresolved |
| all trials | Kinase Inhibitor | permitted:prior_agent:immune checkpoint | 1/40 | 3/94 | 2 | 18 | -0.0069 | -0.1984 | (not listed) | unresolved |
| all trials | Kinase Inhibitor | permitted:prior_agent:radiotherapy | 5/40 | 10/94 | 2 | 18 | 0.0186 | -0.1729 | proposed | unresolved |
| all trials | Kinase Inhibitor | permitted:prior_lines=1 | 1/40 | 2/94 | 2 | 17 | 0.0037 | -0.1771 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:setting_word:adjuvant | 6/40 | 11/94 | 2 | 17 | 0.033 | -0.1479 | proposed | unresolved |
| all trials | Kinase Inhibitor | permitted:setting_word:neoadjuvant | 4/40 | 8/94 | 2 | 17 | 0.0149 | -0.166 | below_support | unresolved |
| all trials | Kinase Inhibitor | permitted:stage:I\|II | 1/40 | 0/94 | 2 | 18 | 0.025 | -0.1665 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:biomarker:EGFR=negative | 1/27 | 1/107 | 2 | 16 | 0.0277 | -0.1218 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:biomarker:EGFR=positive | 10/27 | 31/107 | 1 | 10 | 0.0807 | -0.0128 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:biomarker:ROS1=positive | 1/27 | 10/107 | 2 | 13 | -0.0564 | -0.1779 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=active_infection | 13/27 | 53/107 | 2 | 10 | -0.0138 | -0.1073 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=anticoagulant_use | 1/27 | 6/107 | 2 | 16 | -0.019 | -0.1686 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=cardiac_disease | 10/27 | 47/107 | 2 | 12 | -0.0689 | -0.181 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=compliance | 1/27 | 4/107 | 2 | 15 | -0.0003 | -0.1405 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=diagnosis_confirmed | 6/27 | 22/107 | 2 | 14 | 0.0166 | -0.1142 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=gi_perforation_fistula | 1/27 | 6/107 | 2 | 16 | -0.019 | -0.1686 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=hiv | 14/27 | 49/107 | 2 | 10 | 0.0606 | -0.0329 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=informed_consent | 4/27 | 8/107 | 2 | 15 | 0.0734 | -0.0668 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=interacting_medication | 1/27 | 9/107 | 2 | 15 | -0.0471 | -0.1873 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=life_expectancy | 1/27 | 0/107 | 2 | 16 | 0.037 | -0.1125 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=live_vaccine | 9/27 | 27/107 | 2 | 12 | 0.081 | -0.0312 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=organ_impairment | 1/27 | 8/107 | 2 | 15 | -0.0377 | -0.1779 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=organ_transplant | 9/27 | 26/107 | 2 | 15 | 0.0903 | -0.0498 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=other_investigational | 10/27 | 34/107 | 2 | 13 | 0.0526 | -0.0689 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=other_malignancy | 12/27 | 52/107 | 2 | 11 | -0.0415 | -0.1443 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=pneumonitis_ild | 14/27 | 55/107 | 1 | 7 | 0.0045 | -0.0609 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=prior_enrollment | 1/27 | 0/107 | 2 | 16 | 0.037 | -0.1125 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=recent_surgery | 11/27 | 46/107 | 2 | 9 | -0.0225 | -0.1066 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=serious_comorbidity | 3/27 | 17/107 | 2 | 14 | -0.0478 | -0.1786 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=substance_or_psychiatric | 5/27 | 23/107 | 2 | 12 | -0.0298 | -0.1419 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=tuberculosis | 6/27 | 26/107 | 2 | 15 | -0.0208 | -0.161 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=unresolved_toxicity | 3/27 | 18/107 | 2 | 15 | -0.0571 | -0.1973 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:condition=weight_loss | 1/27 | 0/107 | 2 | 16 | 0.037 | -0.1125 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:extent:locally advanced | 3/27 | 6/107 | 1 | 16 | 0.055 | -0.0945 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:extent:metastatic | 5/27 | 23/107 | 1 | 12 | -0.0298 | -0.1419 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:extent:recurrent | 4/27 | 22/107 | 2 | 15 | -0.0575 | -0.1976 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:extent:unresectable | 3/27 | 6/107 | 2 | 15 | 0.055 | -0.0852 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:histology=adenocarcinoma | 1/27 | 2/107 | 2 | 16 | 0.0183 | -0.1312 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:histology=large_cell | 3/27 | 2/107 | 2 | 16 | 0.0924 | -0.0571 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:histology=non_squamous | 3/27 | 3/107 | 2 | 15 | 0.0831 | -0.0571 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:histology=small_cell | 4/27 | 11/107 | 2 | 16 | 0.0453 | -0.1042 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:histology=squamous | 2/27 | 12/107 | 2 | 15 | -0.0381 | -0.1783 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:ALK inhibitor | 1/27 | 5/107 | 2 | 15 | -0.0097 | -0.1499 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:CTLA-4 | 3/27 | 5/107 | 2 | 16 | 0.0644 | -0.0852 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:PD-1 | 7/27 | 22/107 | 2 | 13 | 0.0537 | -0.0678 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:PD-L1 | 6/27 | 24/107 | 2 | 13 | -0.0021 | -0.1236 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:VEGF inhibitor | 1/27 | 0/107 | 2 | 16 | 0.037 | -0.1125 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:chemotherapy | 7/27 | 26/107 | 0 | 14 | 0.0163 | -0.1146 | proposed | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:docetaxel | 2/27 | 6/107 | 1 | 15 | 0.018 | -0.1222 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:pemetrexed | 2/27 | 3/107 | 2 | 16 | 0.046 | -0.1035 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:platinum | 3/27 | 8/107 | 1 | 15 | 0.0363 | -0.1038 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_agent:taxane | 2/27 | 1/107 | 2 | 16 | 0.0647 | -0.0848 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_lines=0 | 1/27 | 1/107 | 2 | 16 | 0.0277 | -0.1218 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_lines=1 | 2/27 | 4/107 | 1 | 16 | 0.0367 | -0.1128 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:prior_lines=1\|2\|3+ | 1/27 | 5/107 | 2 | 15 | -0.0097 | -0.1499 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:setting_word:adjuvant | 1/27 | 8/107 | 2 | 15 | -0.0377 | -0.1779 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | exclusion:setting_word:consolidation | 2/27 | 0/107 | 2 | 16 | 0.0741 | -0.0755 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:setting_word:maintenance | 1/27 | 3/107 | 2 | 15 | 0.009 | -0.1312 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:stage:II | 1/27 | 0/107 | 2 | 16 | 0.037 | -0.1125 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:stage:III | 2/27 | 3/107 | 2 | 16 | 0.046 | -0.1035 | below_support | unresolved |
| all trials | Microtubule Inhibitor | exclusion:stage:III\|IV | 1/27 | 0/107 | 2 | 16 | 0.037 | -0.1125 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:age=stated | 13/27 | 42/107 | 2 | 11 | 0.089 | -0.0138 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:biomarker:ALK=negative | 2/27 | 11/107 | 2 | 15 | -0.0287 | -0.1689 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:biomarker:ALK=positive | 4/27 | 17/107 | 3 | 15 | -0.0107 | -0.1509 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:biomarker:EGFR=negative | 4/27 | 16/107 | 2 | 13 | -0.0014 | -0.1229 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:biomarker:PD-L1=@1-49% | 1/27 | 0/107 | 3 | 16 | 0.037 | -0.1125 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 2/27 | 2/107 | 3 | 16 | 0.0554 | -0.0942 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:biomarker:PD-L1=positive | 3/27 | 3/107 | 3 | 16 | 0.0831 | -0.0665 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=active_infection | 2/27 | 4/107 | 2 | 15 | 0.0367 | -0.1035 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=anticoagulant_use | 1/27 | 2/107 | 3 | 16 | 0.0183 | -0.1312 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=autoimmune_disease | 1/27 | 2/107 | 3 | 16 | 0.0183 | -0.1312 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=cardiac_disease | 1/27 | 9/107 | 2 | 15 | -0.0471 | -0.1873 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=cns_metastases | 2/27 | 11/107 | 3 | 16 | -0.0287 | -0.1783 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=compliance | 4/27 | 8/107 | 2 | 13 | 0.0734 | -0.0481 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=hepatitis | 2/27 | 8/107 | 3 | 16 | -0.0007 | -0.1502 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=hiv | 4/27 | 7/107 | 2 | 15 | 0.0827 | -0.0575 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=hypersensitivity | 1/27 | 2/107 | 3 | 16 | 0.0183 | -0.1312 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=hypertension | 1/27 | 9/107 | 3 | 16 | -0.0471 | -0.1966 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=immunosuppression_steroids | 5/27 | 24/107 | 2 | 14 | -0.0391 | -0.17 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=informed_consent | 8/27 | 38/107 | 3 | 11 | -0.0588 | -0.1616 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=live_vaccine | 1/27 | 0/107 | 3 | 16 | 0.037 | -0.1125 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=organ_transplant | 1/27 | 1/107 | 3 | 16 | 0.0277 | -0.1218 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=other_investigational | 1/27 | 4/107 | 3 | 15 | -0.0003 | -0.1405 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=other_malignancy | 4/27 | 6/107 | 2 | 15 | 0.0921 | -0.0481 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=pneumonitis_ild | 1/27 | 11/107 | 3 | 16 | -0.0658 | -0.2153 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 4/27 | 11/107 | 3 | 16 | 0.0453 | -0.1042 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=pulmonary_function | 5/27 | 5/107 | 3 | 16 | 0.1385 | -0.0111 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=recent_radiotherapy | 7/27 | 27/107 | 3 | 13 | 0.0069 | -0.1146 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=recent_surgery | 10/27 | 34/107 | 2 | 14 | 0.0526 | -0.0782 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=serious_comorbidity | 1/27 | 1/107 | 3 | 16 | 0.0277 | -0.1218 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=sex | 4/27 | 21/107 | 3 | 13 | -0.0481 | -0.1696 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=tissue_available | 3/27 | 18/107 | 3 | 14 | -0.0571 | -0.188 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:condition=unresolved_toxicity | 1/27 | 13/107 | 3 | 14 | -0.0845 | -0.2153 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:extent:advanced | 4/27 | 22/107 | 2 | 9 | -0.0575 | -0.1416 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:extent:recurrent | 8/27 | 26/107 | 3 | 11 | 0.0533 | -0.0495 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:extent:unresectable | 4/27 | 12/107 | 3 | 14 | 0.036 | -0.0948 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:histology=non_squamous | 10/27 | 47/107 | 2 | 7 | -0.0689 | -0.1343 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:histology=squamous | 5/27 | 14/107 | 2 | 10 | 0.0543 | -0.0391 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:lab:ALT | 7/27 | 23/107 | 2 | 14 | 0.0443 | -0.0865 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:lab:AST | 6/27 | 18/107 | 2 | 15 | 0.054 | -0.0862 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:lab:bilirubin | 9/27 | 22/107 | 2 | 15 | 0.1277 | -0.0125 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:lab:creatinine | 4/27 | 16/107 | 3 | 16 | -0.0014 | -0.1509 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:lab:leukocytes | 1/27 | 4/107 | 3 | 15 | -0.0003 | -0.1405 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:lab:neutrophils | 9/27 | 24/107 | 2 | 14 | 0.109 | -0.0218 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:lab:platelets | 9/27 | 25/107 | 2 | 14 | 0.0997 | -0.0312 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:ALK inhibitor | 2/27 | 3/107 | 3 | 16 | 0.046 | -0.1035 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:CTLA-4 | 1/27 | 2/107 | 3 | 16 | 0.0183 | -0.1312 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:EGFR inhibitor | 1/27 | 11/107 | 3 | 15 | -0.0658 | -0.206 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:PD-1 | 1/27 | 6/107 | 3 | 16 | -0.019 | -0.1686 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:PD-L1 | 1/27 | 5/107 | 3 | 16 | -0.0097 | -0.1592 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:chemotherapy | 7/27 | 35/107 | 2 | 10 | -0.0678 | -0.1613 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:docetaxel | 1/27 | 3/107 | 3 | 15 | 0.009 | -0.1312 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:immune checkpoint | 2/27 | 11/107 | 3 | 15 | -0.0287 | -0.1689 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:platinum | 5/27 | 22/107 | 2 | 12 | -0.0204 | -0.1326 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_agent:radiotherapy | 5/27 | 25/107 | 3 | 12 | -0.0485 | -0.1606 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_lines=1 | 1/27 | 4/107 | 2 | 15 | -0.0003 | -0.1405 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:prior_lines=1\|2\|3+ | 2/27 | 18/107 | 3 | 13 | -0.0942 | -0.2156 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:resection:resected | 5/27 | 10/107 | 2 | 15 | 0.0917 | -0.0485 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:setting_word:adjuvant | 4/27 | 20/107 | 2 | 13 | -0.0388 | -0.1603 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:setting_word:consolidation | 3/27 | 3/107 | 3 | 16 | 0.0831 | -0.0665 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:setting_word:neoadjuvant | 3/27 | 13/107 | 2 | 14 | -0.0104 | -0.1412 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:stage:I | 2/27 | 2/107 | 2 | 16 | 0.0554 | -0.0942 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:stage:II | 3/27 | 2/107 | 2 | 15 | 0.0924 | -0.0478 | below_support | unresolved |
| all trials | Microtubule Inhibitor | inclusion:stage:III | 7/27 | 25/107 | 2 | 12 | 0.0256 | -0.0865 | proposed | unresolved |
| all trials | Microtubule Inhibitor | inclusion:stage:III\|IV | 3/27 | 16/107 | 3 | 10 | -0.0384 | -0.1319 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | inclusion:stage:I\|II\|III | 2/27 | 5/107 | 3 | 16 | 0.0273 | -0.1222 | below_support | unresolved |
| all trials | Microtubule Inhibitor | permitted:condition=autoimmune_disease | 3/27 | 2/107 | 3 | 16 | 0.0924 | -0.0571 | below_support | unresolved |
| all trials | Microtubule Inhibitor | permitted:condition=contraception | 1/27 | 1/107 | 3 | 16 | 0.0277 | -0.1218 | below_support | unresolved |
| all trials | Microtubule Inhibitor | permitted:condition=pregnancy_or_breastfeeding | 1/27 | 0/107 | 3 | 17 | 0.037 | -0.1218 | below_support | unresolved |
| all trials | Microtubule Inhibitor | permitted:condition=recent_radiotherapy | 1/27 | 11/107 | 3 | 16 | -0.0658 | -0.2153 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | permitted:extent:locally advanced | 1/27 | 3/107 | 3 | 17 | 0.009 | -0.1499 | below_support | unresolved |
| all trials | Microtubule Inhibitor | permitted:extent:recurrent | 2/27 | 2/107 | 3 | 17 | 0.0554 | -0.1035 | below_support | unresolved |
| all trials | Microtubule Inhibitor | permitted:prior_agent:chemotherapy | 3/27 | 14/107 | 3 | 15 | -0.0197 | -0.1599 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | permitted:prior_agent:immune checkpoint | 1/27 | 3/107 | 3 | 17 | 0.009 | -0.1499 | below_support | unresolved |
| all trials | Microtubule Inhibitor | permitted:prior_agent:radiotherapy | 2/27 | 13/107 | 3 | 17 | -0.0474 | -0.2063 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | permitted:setting_word:adjuvant | 2/27 | 15/107 | 3 | 16 | -0.0661 | -0.2156 | (not listed) | unresolved |
| all trials | Microtubule Inhibitor | permitted:stage:III | 1/27 | 1/107 | 3 | 17 | 0.0277 | -0.1312 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:condition=diagnosis_confirmed | 2/8 | 26/126 | 0 | 16 | 0.0437 | -0.0833 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:condition=hypersensitivity | 4/8 | 55/126 | 0 | 9 | 0.0635 | -0.0079 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:extent:locally advanced | 1/8 | 8/126 | 0 | 17 | 0.0615 | -0.0734 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:histology=non_squamous | 1/8 | 5/126 | 0 | 17 | 0.0853 | -0.0496 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:histology=small_cell | 1/8 | 14/126 | 0 | 18 | 0.0139 | -0.129 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:prior_agent:PD-1 | 2/8 | 27/126 | 0 | 15 | 0.0357 | -0.0833 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:prior_agent:PD-L1 | 2/8 | 28/126 | 0 | 15 | 0.0278 | -0.0913 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:stage:III | 1/8 | 4/126 | 0 | 18 | 0.0933 | -0.0496 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | exclusion:stage:III\|IV | 1/8 | 0/126 | 0 | 18 | 0.125 | -0.0179 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:biomarker:ALK=negative | 1/8 | 12/126 | 0 | 17 | 0.0298 | -0.1052 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 1/8 | 3/126 | 1 | 18 | 0.1012 | -0.0417 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:condition=active_infection | 1/8 | 5/126 | 0 | 17 | 0.0853 | -0.0496 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:condition=cardiac_disease | 1/8 | 9/126 | 0 | 17 | 0.0536 | -0.0813 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:condition=compliance | 1/8 | 11/126 | 0 | 15 | 0.0377 | -0.0813 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:condition=diagnosis_confirmed | 6/8 | 99/126 | 1 | 6 | -0.0357 | -0.0833 | (not listed) | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:condition=organ_transplant | 1/8 | 1/126 | 1 | 18 | 0.1171 | -0.0258 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:condition=other_malignancy | 1/8 | 9/126 | 0 | 17 | 0.0536 | -0.0813 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:condition=pulmonary_function | 1/8 | 9/126 | 1 | 18 | 0.0536 | -0.0893 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:ecog_ps=0\|1\|2 | 1/8 | 26/126 | 1 | 16 | -0.0813 | -0.2083 | (not listed) | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:organ_function_unspecified=adequate | 3/8 | 36/126 | 1 | 13 | 0.0893 | -0.0139 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:prior_agent:CTLA-4 | 1/8 | 2/126 | 1 | 18 | 0.1091 | -0.0337 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:prior_agent:PD-1 | 1/8 | 6/126 | 1 | 18 | 0.0774 | -0.0655 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:prior_agent:PD-L1 | 1/8 | 5/126 | 1 | 18 | 0.0853 | -0.0575 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:prior_agent:platinum | 1/8 | 26/126 | 1 | 13 | -0.0813 | -0.1845 | (not listed) | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:setting_word:neoadjuvant | 1/8 | 15/126 | 0 | 16 | 0.006 | -0.121 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:stage:III | 1/8 | 31/126 | 1 | 13 | -0.121 | -0.2242 | (not listed) | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | inclusion:stage:I\|II\|III | 1/8 | 6/126 | 1 | 18 | 0.0774 | -0.0655 | below_support | unresolved |
| all trials | Nucleoside Metabolic Inhibitor | permitted:prior_agent:chemotherapy | 1/8 | 16/126 | 1 | 17 | -0.002 | -0.1369 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:biomarker:ALK=positive | 15/45 | 21/89 | 1 | 9 | 0.0974 | -0.0037 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:biomarker:BRAF=positive | 2/45 | 3/89 | 3 | 14 | 0.0107 | -0.1466 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:biomarker:BRAF=unknown | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:biomarker:EGFR=negative | 2/45 | 0/89 | 3 | 15 | 0.0444 | -0.1241 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:biomarker:NTRK=unknown | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:biomarker:RET=unknown | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:biomarker:ROS1=positive | 4/45 | 7/89 | 3 | 12 | 0.0102 | -0.1246 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=active_infection | 21/45 | 45/89 | 2 | 10 | -0.039 | -0.1513 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=anticoagulant_use | 1/45 | 6/89 | 3 | 15 | -0.0452 | -0.2137 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=compliance | 1/45 | 4/89 | 3 | 14 | -0.0227 | -0.18 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=contraception | 2/45 | 3/89 | 3 | 15 | 0.0107 | -0.1578 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=diagnosis_confirmed | 12/45 | 16/89 | 3 | 13 | 0.0869 | -0.0592 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=effusion | 6/45 | 12/89 | 1 | 14 | -0.0015 | -0.1588 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=gi_perforation_fistula | 1/45 | 6/89 | 3 | 15 | -0.0452 | -0.2137 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=hepatitis | 21/45 | 38/89 | 2 | 10 | 0.0397 | -0.0727 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=hiv | 20/45 | 43/89 | 2 | 10 | -0.0387 | -0.1511 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=informed_consent | 3/45 | 9/89 | 3 | 14 | -0.0345 | -0.1918 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=life_expectancy | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=live_vaccine | 13/45 | 23/89 | 2 | 12 | 0.0305 | -0.1044 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=measurable_disease | 1/45 | 6/89 | 3 | 15 | -0.0452 | -0.2137 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=neurologic_disorder | 10/45 | 21/89 | 2 | 9 | -0.0137 | -0.1149 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=organ_transplant | 12/45 | 23/89 | 3 | 14 | 0.0082 | -0.1491 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=other_investigational | 16/45 | 28/89 | 2 | 13 | 0.0409 | -0.1051 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=pneumonitis_ild | 24/45 | 45/89 | 1 | 7 | 0.0277 | -0.0509 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=prior_enrollment | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=tuberculosis | 10/45 | 22/89 | 3 | 14 | -0.025 | -0.1823 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=unresolved_toxicity | 6/45 | 15/89 | 3 | 14 | -0.0352 | -0.1925 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=vitamin_premedication | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:condition=weight_loss | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:extent:advanced | 1/45 | 3/89 | 2 | 15 | -0.0115 | -0.18 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:extent:recurrent | 7/45 | 19/89 | 3 | 14 | -0.0579 | -0.2152 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:extent:unresectable | 2/45 | 7/89 | 3 | 14 | -0.0342 | -0.1915 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:histology=adenocarcinoma | 1/45 | 2/89 | 3 | 15 | -0.0002 | -0.1688 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:histology=large_cell | 3/45 | 2/89 | 3 | 15 | 0.0442 | -0.1243 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:histology=non_squamous | 2/45 | 4/89 | 3 | 14 | -0.0005 | -0.1578 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:histology=small_cell | 6/45 | 9/89 | 3 | 15 | 0.0322 | -0.1363 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:histology=squamous | 7/45 | 7/89 | 3 | 14 | 0.0769 | -0.0804 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:lab:creatinine clearance | 1/45 | 2/89 | 3 | 15 | -0.0002 | -0.1688 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:ALK inhibitor | 2/45 | 4/89 | 2 | 15 | -0.0005 | -0.169 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:CTLA-4 | 5/45 | 3/89 | 3 | 15 | 0.0774 | -0.0911 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:EGFR inhibitor | 6/45 | 5/89 | 2 | 15 | 0.0772 | -0.0914 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:PD-1 | 13/45 | 16/89 | 2 | 13 | 0.1091 | -0.037 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:PD-L1 | 14/45 | 16/89 | 2 | 13 | 0.1313 | -0.0147 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:VEGF inhibitor | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:chemotherapy | 11/45 | 22/89 | 2 | 12 | -0.0027 | -0.1376 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:immune checkpoint | 12/45 | 13/89 | 3 | 13 | 0.1206 | -0.0255 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:pemetrexed | 4/45 | 1/89 | 3 | 15 | 0.0777 | -0.0909 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:platinum | 5/45 | 6/89 | 3 | 13 | 0.0437 | -0.1024 | proposed | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_agent:taxane | 2/45 | 1/89 | 3 | 15 | 0.0332 | -0.1353 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_lines=0 | 1/45 | 1/89 | 3 | 15 | 0.011 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_lines=1 | 1/45 | 5/89 | 3 | 14 | -0.034 | -0.1913 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:prior_lines=1\|2\|3+ | 2/45 | 4/89 | 3 | 14 | -0.0005 | -0.1578 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:resection:resected | 1/45 | 1/89 | 3 | 15 | 0.011 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:setting_word:adjuvant | 3/45 | 6/89 | 2 | 15 | -0.0007 | -0.1693 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:setting_word:consolidation | 2/45 | 0/89 | 3 | 15 | 0.0444 | -0.1241 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:setting_word:neoadjuvant | 1/45 | 4/89 | 2 | 14 | -0.0227 | -0.18 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:stage:I | 1/45 | 2/89 | 3 | 15 | -0.0002 | -0.1688 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:stage:II | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:stage:III | 1/45 | 4/89 | 3 | 15 | -0.0227 | -0.1913 | (not listed) | unresolved |
| all trials | Platinum-based Drug | exclusion:stage:III\|IV | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:stage:II\|III | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | exclusion:stage:I\|III | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:age=stated | 20/45 | 35/89 | 1 | 12 | 0.0512 | -0.0836 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:ALK=negative | 6/45 | 7/89 | 3 | 14 | 0.0547 | -0.1026 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:ALK=unknown | 2/45 | 0/89 | 4 | 15 | 0.0444 | -0.1241 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:EGFR=negative | 10/45 | 10/89 | 3 | 12 | 0.1099 | -0.025 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:EGFR=unknown | 2/45 | 1/89 | 4 | 14 | 0.0332 | -0.1241 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:KRAS=positive | 2/45 | 3/89 | 4 | 15 | 0.0107 | -0.1578 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:MET=positive | 1/45 | 2/89 | 4 | 15 | -0.0002 | -0.1688 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:NTRK=positive | 1/45 | 1/89 | 4 | 15 | 0.011 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:PD-L1=@1-49% | 1/45 | 0/89 | 4 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:PD-L1=@<50% | 1/45 | 0/89 | 3 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:PD-L1=@>=1% | 1/45 | 0/89 | 4 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:PD-L1=@≥1% | 1/45 | 3/89 | 4 | 15 | -0.0115 | -0.18 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:PD-L1=negative\|positive | 2/45 | 2/89 | 4 | 15 | 0.022 | -0.1466 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:PD-L1=positive | 2/45 | 4/89 | 4 | 15 | -0.0005 | -0.169 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:RET=positive | 1/45 | 5/89 | 4 | 15 | -0.034 | -0.2025 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:ROS1=negative | 4/45 | 3/89 | 4 | 14 | 0.0552 | -0.1021 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:biomarker:ROS1=unknown | 1/45 | 0/89 | 4 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=active_infection | 3/45 | 3/89 | 3 | 14 | 0.033 | -0.1243 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=anticoagulant_use | 3/45 | 0/89 | 4 | 15 | 0.0667 | -0.1019 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=autoimmune_disease | 2/45 | 1/89 | 4 | 15 | 0.0332 | -0.1353 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=bleeding_thrombosis | 1/45 | 4/89 | 4 | 15 | -0.0227 | -0.1913 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=cardiac_disease | 3/45 | 7/89 | 3 | 14 | -0.012 | -0.1693 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=cns_metastases | 7/45 | 6/89 | 4 | 15 | 0.0881 | -0.0804 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=compliance | 4/45 | 8/89 | 2 | 13 | -0.001 | -0.1471 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=diagnosis_confirmed | 36/45 | 69/89 | 3 | 4 | 0.0247 | -0.0202 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=gi_perforation_fistula | 2/45 | 2/89 | 4 | 15 | 0.022 | -0.1466 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=hepatitis | 4/45 | 6/89 | 4 | 15 | 0.0215 | -0.1471 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=hiv | 6/45 | 5/89 | 3 | 14 | 0.0772 | -0.0801 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=hypersensitivity | 2/45 | 1/89 | 4 | 15 | 0.0332 | -0.1353 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=hypertension | 4/45 | 6/89 | 4 | 15 | 0.0215 | -0.1471 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=interacting_medication | 1/45 | 2/89 | 4 | 15 | -0.0002 | -0.1688 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=investigator_judgment | 2/45 | 8/89 | 4 | 15 | -0.0454 | -0.214 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=live_vaccine | 1/45 | 0/89 | 4 | 15 | 0.0222 | -0.1463 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=malabsorption | 1/45 | 7/89 | 4 | 15 | -0.0564 | -0.225 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=organ_transplant | 1/45 | 1/89 | 4 | 15 | 0.011 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=other_investigational | 1/45 | 4/89 | 3 | 15 | -0.0227 | -0.1913 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=other_malignancy | 8/45 | 2/89 | 3 | 14 | 0.1553 | -0.002 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=pneumonitis_ild | 7/45 | 5/89 | 4 | 15 | 0.0994 | -0.0692 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=pregnancy_or_breastfeeding | 6/45 | 9/89 | 4 | 15 | 0.0322 | -0.1363 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=pulmonary_function | 6/45 | 4/89 | 4 | 15 | 0.0884 | -0.0801 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=qtc | 1/45 | 3/89 | 4 | 15 | -0.0115 | -0.18 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=recent_radiotherapy | 10/45 | 24/89 | 4 | 12 | -0.0474 | -0.1823 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=recent_surgery | 14/45 | 30/89 | 3 | 13 | -0.026 | -0.172 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=serious_comorbidity | 1/45 | 1/89 | 4 | 15 | 0.011 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=sex | 8/45 | 17/89 | 3 | 13 | -0.0132 | -0.1593 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=tissue_available | 6/45 | 15/89 | 4 | 13 | -0.0352 | -0.1813 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:condition=unresolved_toxicity | 3/45 | 11/89 | 4 | 13 | -0.0569 | -0.203 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:extent:advanced | 8/45 | 18/89 | 2 | 9 | -0.0245 | -0.1256 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:extent:recurrent | 9/45 | 25/89 | 4 | 10 | -0.0809 | -0.1933 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:extent:unresectable | 6/45 | 10/89 | 4 | 13 | 0.021 | -0.1251 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:histology=adenocarcinoma | 2/45 | 2/89 | 4 | 14 | 0.022 | -0.1353 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:histology=squamous | 6/45 | 13/89 | 3 | 9 | -0.0127 | -0.1139 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:ALT | 10/45 | 20/89 | 3 | 13 | -0.0025 | -0.1486 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:AST | 9/45 | 15/89 | 3 | 14 | 0.0315 | -0.1258 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:bilirubin | 12/45 | 19/89 | 3 | 14 | 0.0532 | -0.1041 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:creatinine | 7/45 | 13/89 | 4 | 15 | 0.0095 | -0.1591 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:creatinine clearance | 12/45 | 15/89 | 3 | 13 | 0.0981 | -0.0479 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:hemoglobin | 11/45 | 18/89 | 3 | 14 | 0.0422 | -0.1151 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:leukocytes | 1/45 | 4/89 | 4 | 14 | -0.0227 | -0.18 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:neutrophils | 12/45 | 21/89 | 3 | 13 | 0.0307 | -0.1154 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:lab:platelets | 12/45 | 22/89 | 3 | 13 | 0.0195 | -0.1266 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:prior_agent:ALK inhibitor | 2/45 | 3/89 | 4 | 15 | 0.0107 | -0.1578 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:prior_agent:CTLA-4 | 1/45 | 2/89 | 4 | 15 | -0.0002 | -0.1688 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:prior_agent:EGFR inhibitor | 5/45 | 7/89 | 4 | 14 | 0.0325 | -0.1248 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:prior_agent:PD-1 | 1/45 | 6/89 | 4 | 15 | -0.0452 | -0.2137 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:prior_agent:PD-L1 | 1/45 | 5/89 | 4 | 15 | -0.034 | -0.2025 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:prior_agent:immune checkpoint | 4/45 | 9/89 | 4 | 14 | -0.0122 | -0.1695 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:prior_agent:pemetrexed | 1/45 | 4/89 | 4 | 14 | -0.0227 | -0.18 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:prior_lines=1 | 1/45 | 4/89 | 4 | 13 | -0.0227 | -0.1688 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:resection:resectable | 6/45 | 3/89 | 4 | 14 | 0.0996 | -0.0577 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:resection:resected | 6/45 | 9/89 | 3 | 14 | 0.0322 | -0.1251 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:setting_word:adjuvant | 8/45 | 16/89 | 2 | 13 | -0.002 | -0.1481 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:setting_word:consolidation | 3/45 | 3/89 | 4 | 15 | 0.033 | -0.1356 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:setting_word:neoadjuvant | 6/45 | 10/89 | 2 | 14 | 0.021 | -0.1363 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:stage:I | 2/45 | 2/89 | 3 | 15 | 0.022 | -0.1466 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:stage:II | 3/45 | 2/89 | 3 | 14 | 0.0442 | -0.1131 | below_support | unresolved |
| all trials | Platinum-based Drug | inclusion:stage:III | 9/45 | 23/89 | 4 | 10 | -0.0584 | -0.1708 | (not listed) | unresolved |
| all trials | Platinum-based Drug | inclusion:stage:II\|III | 7/45 | 7/89 | 3 | 14 | 0.0769 | -0.0804 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:stage:IV | 14/45 | 27/89 | 4 | 12 | 0.0077 | -0.1271 | proposed | unresolved |
| all trials | Platinum-based Drug | inclusion:stage:I\|II\|III | 2/45 | 5/89 | 4 | 15 | -0.0117 | -0.1803 | (not listed) | unresolved |
| all trials | Platinum-based Drug | permitted:biomarker:EGFR=negative | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:biomarker:EGFR=positive | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:condition=autoimmune_disease | 3/45 | 2/89 | 4 | 15 | 0.0442 | -0.1243 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:condition=contraception | 1/45 | 1/89 | 4 | 15 | 0.011 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:condition=measurable_disease | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:condition=pneumonitis_ild | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:condition=pregnancy_or_breastfeeding | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:condition=recent_radiotherapy | 3/45 | 9/89 | 4 | 15 | -0.0345 | -0.203 | (not listed) | unresolved |
| all trials | Platinum-based Drug | permitted:extent:locally advanced | 2/45 | 2/89 | 4 | 16 | 0.022 | -0.1578 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:extent:metastatic | 4/45 | 4/89 | 4 | 15 | 0.0439 | -0.1246 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:extent:recurrent | 4/45 | 0/89 | 4 | 16 | 0.0889 | -0.0909 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:prior_agent:EGFR inhibitor | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:prior_agent:chemotherapy | 7/45 | 10/89 | 4 | 14 | 0.0432 | -0.1141 | proposed | unresolved |
| all trials | Platinum-based Drug | permitted:prior_agent:immune checkpoint | 2/45 | 2/89 | 4 | 16 | 0.022 | -0.1578 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:prior_agent:radiotherapy | 7/45 | 8/89 | 4 | 16 | 0.0657 | -0.1141 | proposed | unresolved |
| all trials | Platinum-based Drug | permitted:prior_lines=1\|2 | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:setting_word:adjuvant | 7/45 | 10/89 | 4 | 15 | 0.0432 | -0.1253 | proposed | unresolved |
| all trials | Platinum-based Drug | permitted:setting_word:neoadjuvant | 4/45 | 8/89 | 4 | 15 | -0.001 | -0.1695 | (not listed) | unresolved |
| all trials | Platinum-based Drug | permitted:stage:III | 2/45 | 0/89 | 4 | 16 | 0.0444 | -0.1353 | below_support | unresolved |
| all trials | Platinum-based Drug | permitted:stage:IV | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:age=stated | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:biomarker:ALK=positive | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:biomarker:BRAF=negative | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:biomarker:EGFR=positive | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:biomarker:MET=negative | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:biomarker:NTRK=negative | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:biomarker:RET=negative | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:biomarker:ROS1=positive | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:condition=active_infection | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:condition=cns_metastases | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:condition=diagnosis_confirmed | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:condition=hepatitis | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:condition=immunosuppression_steroids | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:condition=other_malignancy | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:condition=pneumonitis_ild | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:condition=tissue_available | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:ecog_ps=0\|1 | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:extent:metastatic | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:histology=small_cell | 1/45 | 1/89 | 4 | 16 | 0.011 | -0.1688 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:stage:III | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Platinum-based Drug | unsectioned:stage:IV | 1/45 | 0/89 | 4 | 16 | 0.0222 | -0.1576 | below_support | unresolved |
| all trials | Poly(ADP-Ribose) Polymerase Inhibitor | exclusion:condition=active_infection | 1/2 | 65/132 | 0 | 12 | 0.0076 | -0.0833 | below_support | unresolved |
| all trials | Poly(ADP-Ribose) Polymerase Inhibitor | exclusion:condition=hepatitis | 1/2 | 58/132 | 0 | 12 | 0.0606 | -0.0303 | below_support | unresolved |
| all trials | Poly(ADP-Ribose) Polymerase Inhibitor | exclusion:condition=hiv | 1/2 | 62/132 | 0 | 12 | 0.0303 | -0.0606 | below_support | unresolved |
| all trials | Poly(ADP-Ribose) Polymerase Inhibitor | exclusion:condition=hypersensitivity | 1/2 | 58/132 | 0 | 9 | 0.0606 | -0.0076 | below_support | unresolved |
| all trials | Poly(ADP-Ribose) Polymerase Inhibitor | inclusion:age=stated | 1/2 | 54/132 | 0 | 13 | 0.0909 | -0.0076 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:biomarker:ALK=positive | 3/12 | 33/122 | 1 | 9 | -0.0205 | -0.0943 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:biomarker:ALK=unknown | 1/12 | 0/122 | 1 | 16 | 0.0833 | -0.0478 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:biomarker:EGFR=unknown | 1/12 | 0/122 | 1 | 16 | 0.0833 | -0.0478 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:biomarker:PD-L1=unknown | 1/12 | 0/122 | 2 | 16 | 0.0833 | -0.0478 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=bleeding_thrombosis | 1/12 | 29/122 | 2 | 15 | -0.1544 | -0.2773 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=cardiac_disease | 4/12 | 53/122 | 2 | 12 | -0.1011 | -0.1995 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=effusion | 1/12 | 17/122 | 2 | 13 | -0.056 | -0.1626 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=hepatitis | 6/12 | 53/122 | 2 | 10 | 0.0656 | -0.0164 | proposed | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=hiv | 5/12 | 58/122 | 2 | 10 | -0.0587 | -0.1407 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=live_vaccine | 3/12 | 33/122 | 2 | 12 | -0.0205 | -0.1189 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=measurable_disease | 1/12 | 6/122 | 2 | 16 | 0.0342 | -0.097 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=neurologic_disorder | 1/12 | 30/122 | 2 | 9 | -0.1626 | -0.2363 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=other_investigational | 3/12 | 41/122 | 2 | 13 | -0.0861 | -0.1926 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=other_malignancy | 4/12 | 60/122 | 2 | 11 | -0.1585 | -0.2486 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=recent_surgery | 5/12 | 52/122 | 1 | 10 | -0.0096 | -0.0915 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=unresolved_toxicity | 3/12 | 18/122 | 2 | 15 | 0.1025 | -0.0205 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:condition=weight_loss | 1/12 | 0/122 | 2 | 16 | 0.0833 | -0.0478 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:extent:locally advanced | 1/12 | 8/122 | 2 | 15 | 0.0178 | -0.1052 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:extent:recurrent | 2/12 | 24/122 | 2 | 15 | -0.0301 | -0.153 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:extent:unresectable | 2/12 | 7/122 | 2 | 15 | 0.1093 | -0.0137 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:histology=non_squamous | 1/12 | 5/122 | 1 | 16 | 0.0423 | -0.0888 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:histology=small_cell | 1/12 | 14/122 | 2 | 16 | -0.0314 | -0.1626 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:histology=squamous | 1/12 | 13/122 | 1 | 16 | -0.0232 | -0.1544 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:CTLA-4 | 1/12 | 7/122 | 2 | 16 | 0.026 | -0.1052 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:PD-1 | 1/12 | 28/122 | 2 | 13 | -0.1462 | -0.2527 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:PD-L1 | 1/12 | 29/122 | 2 | 13 | -0.1544 | -0.2609 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:chemotherapy | 2/12 | 31/122 | 2 | 12 | -0.0874 | -0.1858 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:immune checkpoint | 3/12 | 22/122 | 1 | 15 | 0.0697 | -0.0533 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:pemetrexed | 1/12 | 4/122 | 2 | 16 | 0.0505 | -0.0806 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:taxane | 1/12 | 2/122 | 2 | 16 | 0.0669 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:setting_word:adjuvant | 1/12 | 8/122 | 2 | 15 | 0.0178 | -0.1052 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:setting_word:consolidation | 1/12 | 1/122 | 2 | 16 | 0.0751 | -0.056 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:setting_word:neoadjuvant | 1/12 | 4/122 | 2 | 14 | 0.0505 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:stage:III | 1/12 | 4/122 | 2 | 16 | 0.0505 | -0.0806 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | exclusion:stage:III\|IV | 1/12 | 0/122 | 2 | 16 | 0.0833 | -0.0478 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:biomarker:ALK=positive | 1/12 | 20/122 | 2 | 16 | -0.0806 | -0.2117 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:biomarker:EGFR=unknown | 1/12 | 2/122 | 1 | 17 | 0.0669 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:biomarker:PD-L1=negative\|positive | 1/12 | 3/122 | 2 | 17 | 0.0587 | -0.0806 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:biomarker:PD-L1=positive | 1/12 | 5/122 | 2 | 17 | 0.0423 | -0.097 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=active_infection | 1/12 | 5/122 | 2 | 15 | 0.0423 | -0.0806 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=autoimmune_disease | 1/12 | 2/122 | 2 | 17 | 0.0669 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=contraception | 6/12 | 60/122 | 1 | 14 | 0.0082 | -0.1066 | proposed | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=hepatitis | 1/12 | 9/122 | 2 | 17 | 0.0096 | -0.1298 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=hiv | 1/12 | 10/122 | 2 | 15 | 0.0014 | -0.1216 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=hypersensitivity | 1/12 | 2/122 | 2 | 17 | 0.0669 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=immunosuppression_steroids | 2/12 | 27/122 | 1 | 15 | -0.0546 | -0.1776 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=informed_consent | 5/12 | 41/122 | 1 | 13 | 0.0806 | -0.026 | proposed | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=investigator_judgment | 1/12 | 9/122 | 2 | 17 | 0.0096 | -0.1298 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=life_expectancy | 5/12 | 50/122 | 1 | 12 | 0.0068 | -0.0915 | proposed | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=live_vaccine | 1/12 | 0/122 | 2 | 17 | 0.0833 | -0.056 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=other_malignancy | 2/12 | 8/122 | 2 | 15 | 0.1011 | -0.0219 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=pneumonitis_ild | 1/12 | 11/122 | 2 | 17 | -0.0068 | -0.1462 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=pregnancy_or_breastfeeding | 1/12 | 14/122 | 2 | 17 | -0.0314 | -0.1708 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=pulmonary_function | 1/12 | 9/122 | 2 | 17 | 0.0096 | -0.1298 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=recent_surgery | 4/12 | 40/122 | 2 | 14 | 0.0055 | -0.1093 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=serious_comorbidity | 1/12 | 1/122 | 2 | 17 | 0.0751 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=sex | 3/12 | 22/122 | 0 | 16 | 0.0697 | -0.0615 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:condition=unresolved_toxicity | 1/12 | 13/122 | 2 | 15 | -0.0232 | -0.1462 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:ecog_ps=0\|1\|2 | 1/12 | 26/122 | 2 | 15 | -0.1298 | -0.2527 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:extent:recurrent | 4/12 | 30/122 | 1 | 13 | 0.0874 | -0.0191 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:histology=small_cell | 1/12 | 3/122 | 2 | 17 | 0.0587 | -0.0806 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:lab:ALT | 3/12 | 27/122 | 1 | 15 | 0.0287 | -0.0943 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:lab:AST | 2/12 | 22/122 | 2 | 15 | -0.0137 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:lab:bilirubin | 2/12 | 29/122 | 2 | 15 | -0.071 | -0.194 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:lab:creatinine | 1/12 | 19/122 | 2 | 17 | -0.0724 | -0.2117 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:lab:hemoglobin | 3/12 | 26/122 | 1 | 16 | 0.0369 | -0.0943 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:lab:neutrophils | 3/12 | 30/122 | 1 | 15 | 0.0041 | -0.1189 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:lab:platelets | 3/12 | 31/122 | 1 | 15 | -0.0041 | -0.127 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:organ_function_unspecified=adequate | 3/12 | 36/122 | 2 | 12 | -0.0451 | -0.1434 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:prior_agent:PD-1 | 2/12 | 5/122 | 2 | 17 | 0.1257 | -0.0137 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:prior_agent:PD-L1 | 2/12 | 4/122 | 2 | 17 | 0.1339 | -0.0055 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:prior_agent:immune checkpoint | 1/12 | 12/122 | 2 | 16 | -0.015 | -0.1462 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:prior_lines=0 | 3/12 | 30/122 | 2 | 11 | 0.0041 | -0.0861 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:resection:resectable | 2/12 | 7/122 | 2 | 16 | 0.1093 | -0.0219 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:resection:resected | 1/12 | 14/122 | 2 | 15 | -0.0314 | -0.1544 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:setting_word:adjuvant | 2/12 | 22/122 | 1 | 14 | -0.0137 | -0.1284 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:setting_word:neoadjuvant | 2/12 | 14/122 | 1 | 15 | 0.0519 | -0.071 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:stage:II | 1/12 | 4/122 | 2 | 15 | 0.0505 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:stage:III\|IV | 1/12 | 18/122 | 1 | 12 | -0.0642 | -0.1626 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:stage:II\|III | 1/12 | 13/122 | 2 | 15 | -0.0232 | -0.1462 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | inclusion:stage:I\|II\|III | 1/12 | 6/122 | 2 | 17 | 0.0342 | -0.1052 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | permitted:condition=autoimmune_disease | 1/12 | 4/122 | 2 | 17 | 0.0505 | -0.0888 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | permitted:condition=recent_radiotherapy | 1/12 | 11/122 | 2 | 17 | -0.0068 | -0.1462 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | permitted:extent:recurrent | 1/12 | 3/122 | 2 | 18 | 0.0587 | -0.0888 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | permitted:prior_agent:chemotherapy | 1/12 | 16/122 | 2 | 16 | -0.0478 | -0.179 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | permitted:prior_agent:radiotherapy | 1/12 | 14/122 | 2 | 18 | -0.0314 | -0.179 | (not listed) | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | permitted:setting_word:maintenance | 1/12 | 1/122 | 1 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:age=stated | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:ALK=positive | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:BRAF=negative | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:EGFR=positive | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:MET=negative | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:NTRK=negative | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:RET=negative | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:ROS1=positive | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:condition=active_infection | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:condition=cns_metastases | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:condition=diagnosis_confirmed | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:condition=hepatitis | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:condition=immunosuppression_steroids | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:condition=other_malignancy | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:condition=pneumonitis_ild | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:condition=tissue_available | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:ecog_ps=0\|1 | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:extent:metastatic | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:histology=small_cell | 1/12 | 1/122 | 2 | 18 | 0.0751 | -0.0724 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:stage:III | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Ligand-1 Blocker | unsectioned:stage:IV | 1/12 | 0/122 | 2 | 18 | 0.0833 | -0.0642 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:BRAF=positive | 2/62 | 3/72 | 9 | 8 | -0.0094 | -0.1205 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:BRAF=unknown | 1/62 | 0/72 | 9 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:EGFR=positive | 21/62 | 20/72 | 5 | 6 | 0.0609 | -0.0224 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:NTRK=unknown | 1/62 | 0/72 | 9 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:PD-L1=negative | 1/62 | 0/72 | 9 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:PD-L1=negative\|unknown | 1/62 | 0/72 | 9 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:RET=unknown | 1/62 | 0/72 | 9 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:ROS1=positive | 6/62 | 5/72 | 9 | 6 | 0.0273 | -0.056 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=anticoagulant_use | 1/62 | 6/72 | 9 | 9 | -0.0672 | -0.1922 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=bleeding_thrombosis | 11/62 | 19/72 | 9 | 8 | -0.0865 | -0.1976 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=cardiac_disease | 23/62 | 34/72 | 7 | 7 | -0.1013 | -0.1985 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=contraception | 3/62 | 2/72 | 9 | 9 | 0.0206 | -0.1044 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=diagnosis_confirmed | 10/62 | 18/72 | 8 | 8 | -0.0887 | -0.1998 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=effusion | 9/62 | 9/72 | 6 | 9 | 0.0202 | -0.1048 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=gi_perforation_fistula | 2/62 | 5/72 | 9 | 9 | -0.0372 | -0.1622 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=informed_consent | 3/62 | 9/72 | 9 | 8 | -0.0766 | -0.1877 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=interacting_medication | 2/62 | 8/72 | 8 | 9 | -0.0789 | -0.2039 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=investigator_judgment | 9/62 | 12/72 | 7 | 6 | -0.0215 | -0.1048 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=malabsorption | 2/62 | 11/72 | 9 | 9 | -0.1205 | -0.2455 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=measurable_disease | 2/62 | 5/72 | 9 | 9 | -0.0372 | -0.1622 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=organ_impairment | 3/62 | 6/72 | 9 | 8 | -0.0349 | -0.1461 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=other_investigational | 24/62 | 20/72 | 7 | 8 | 0.1093 | -0.0018 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=other_malignancy | 31/62 | 33/72 | 6 | 7 | 0.0417 | -0.0556 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=pregnancy_or_breastfeeding | 38/62 | 43/72 | 7 | 7 | 0.0157 | -0.0815 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=pulmonary_function | 1/62 | 1/72 | 8 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=qtc | 6/62 | 9/72 | 7 | 9 | -0.0282 | -0.1532 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=recent_radiotherapy | 28/62 | 33/72 | 7 | 7 | -0.0067 | -0.1039 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=serious_comorbidity | 6/62 | 14/72 | 8 | 8 | -0.0977 | -0.2088 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=unresolved_toxicity | 6/62 | 15/72 | 8 | 9 | -0.1116 | -0.2366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:advanced | 2/62 | 2/72 | 8 | 9 | 0.0045 | -0.1205 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:locally advanced | 2/62 | 7/72 | 9 | 8 | -0.065 | -0.1761 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:metastatic | 14/62 | 14/72 | 6 | 7 | 0.0314 | -0.0659 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:recurrent | 14/62 | 12/72 | 9 | 8 | 0.0591 | -0.052 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:unresectable | 3/62 | 6/72 | 9 | 8 | -0.0349 | -0.1461 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=adenocarcinoma | 2/62 | 1/72 | 9 | 9 | 0.0184 | -0.1066 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=large_cell | 4/62 | 1/72 | 9 | 9 | 0.0506 | -0.0744 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=non_squamous | 3/62 | 3/72 | 9 | 8 | 0.0067 | -0.1044 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=small_cell | 6/62 | 9/72 | 9 | 9 | -0.0282 | -0.1532 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=squamous | 4/62 | 10/72 | 9 | 8 | -0.0744 | -0.1855 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:lab:creatinine clearance | 1/62 | 2/72 | 9 | 9 | -0.0116 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:lab:hemoglobin | 1/62 | 3/72 | 9 | 9 | -0.0255 | -0.1505 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:ALK inhibitor | 3/62 | 3/72 | 8 | 9 | 0.0067 | -0.1183 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:CTLA-4 | 6/62 | 2/72 | 9 | 9 | 0.069 | -0.056 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:EGFR inhibitor | 4/62 | 7/72 | 8 | 9 | -0.0327 | -0.1577 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:VEGF inhibitor | 1/62 | 0/72 | 9 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:chemotherapy | 16/62 | 17/72 | 6 | 8 | 0.022 | -0.0892 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:docetaxel | 5/62 | 3/72 | 8 | 8 | 0.039 | -0.0721 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:immune checkpoint | 13/62 | 12/72 | 8 | 8 | 0.043 | -0.0681 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:pemetrexed | 3/62 | 2/72 | 9 | 9 | 0.0206 | -0.1044 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:platinum | 4/62 | 7/72 | 9 | 7 | -0.0327 | -0.1299 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:radiotherapy | 23/62 | 23/72 | 7 | 9 | 0.0515 | -0.0735 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:taxane | 2/62 | 1/72 | 9 | 9 | 0.0184 | -0.1066 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_lines=0 | 2/62 | 0/72 | 9 | 9 | 0.0323 | -0.0927 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_lines=1 | 2/62 | 4/72 | 9 | 8 | -0.0233 | -0.1344 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_lines=1\|2\|3+ | 1/62 | 5/72 | 9 | 8 | -0.0533 | -0.1644 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:resection:resected | 1/62 | 1/72 | 9 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:setting_word:adjuvant | 6/62 | 3/72 | 8 | 9 | 0.0551 | -0.0699 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:setting_word:consolidation | 1/62 | 1/72 | 9 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:setting_word:maintenance | 1/62 | 3/72 | 9 | 8 | -0.0255 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:setting_word:neoadjuvant | 2/62 | 3/72 | 8 | 8 | -0.0094 | -0.1205 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:stage:I | 1/62 | 2/72 | 9 | 9 | -0.0116 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:stage:III | 1/62 | 4/72 | 9 | 9 | -0.0394 | -0.1644 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | exclusion:stage:IV | 2/62 | 2/72 | 9 | 9 | 0.0045 | -0.1205 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:age=stated | 23/62 | 32/72 | 5 | 8 | -0.0735 | -0.1846 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ALK=negative\|positive | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ALK=positive | 8/62 | 13/72 | 10 | 8 | -0.0515 | -0.1626 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ALK=unknown | 2/62 | 0/72 | 10 | 9 | 0.0323 | -0.0927 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:BRAF=negative | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:BRAF=positive | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:EGFR=negative\|positive | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:EGFR=unknown | 2/62 | 1/72 | 10 | 8 | 0.0184 | -0.0927 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:HER2=positive | 1/62 | 4/72 | 10 | 8 | -0.0394 | -0.1505 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:KRAS=positive | 5/62 | 0/72 | 10 | 9 | 0.0806 | -0.0444 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:MET=negative | 1/62 | 1/72 | 10 | 8 | 0.0022 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:MET=positive | 1/62 | 2/72 | 10 | 9 | -0.0116 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:NTRK=negative | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:NTRK=positive | 2/62 | 0/72 | 10 | 9 | 0.0323 | -0.0927 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@1-49% | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@<1% | 1/62 | 1/72 | 9 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@<50% | 1/62 | 0/72 | 9 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@>=1% | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@≥1% | 4/62 | 0/72 | 10 | 9 | 0.0645 | -0.0605 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@≥50% | 1/62 | 1/72 | 9 | 8 | 0.0022 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=negative\|positive | 3/62 | 1/72 | 10 | 9 | 0.0345 | -0.0905 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=positive | 5/62 | 1/72 | 10 | 9 | 0.0668 | -0.0582 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=positive@≥50% | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:RET=negative | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:RET=positive | 3/62 | 3/72 | 10 | 9 | 0.0067 | -0.1183 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ROS1=negative | 7/62 | 0/72 | 9 | 9 | 0.1129 | -0.0121 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ROS1=positive | 3/62 | 4/72 | 10 | 9 | -0.0072 | -0.1322 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ROS1=unknown | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=active_infection | 3/62 | 3/72 | 8 | 9 | 0.0067 | -0.1183 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=anticoagulant_use | 1/62 | 2/72 | 10 | 9 | -0.0116 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=autoimmune_disease | 1/62 | 2/72 | 10 | 9 | -0.0116 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=bleeding_thrombosis | 1/62 | 4/72 | 10 | 9 | -0.0394 | -0.1644 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=cardiac_disease | 5/62 | 5/72 | 8 | 9 | 0.0112 | -0.1138 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=cns_metastases | 6/62 | 7/72 | 10 | 9 | -0.0004 | -0.1254 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=compliance | 8/62 | 4/72 | 6 | 9 | 0.0735 | -0.0515 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=contraception | 33/62 | 33/72 | 8 | 7 | 0.0739 | -0.0233 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=gi_perforation_fistula | 4/62 | 0/72 | 10 | 9 | 0.0645 | -0.0605 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=hepatitis | 5/62 | 5/72 | 10 | 9 | 0.0112 | -0.1138 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=hiv | 6/62 | 5/72 | 8 | 9 | 0.0273 | -0.0977 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=hypertension | 5/62 | 5/72 | 10 | 9 | 0.0112 | -0.1138 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=immunosuppression_steroids | 15/62 | 14/72 | 8 | 8 | 0.0475 | -0.0636 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=investigator_judgment | 5/62 | 5/72 | 10 | 9 | 0.0112 | -0.1138 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=life_expectancy | 24/62 | 31/72 | 8 | 5 | -0.0435 | -0.1129 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=malabsorption | 2/62 | 6/72 | 10 | 9 | -0.0511 | -0.1761 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=neurologic_disorder | 1/62 | 0/72 | 9 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=organ_transplant | 2/62 | 0/72 | 10 | 9 | 0.0323 | -0.0927 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=other_investigational | 4/62 | 1/72 | 9 | 9 | 0.0506 | -0.0744 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=other_malignancy | 6/62 | 4/72 | 8 | 9 | 0.0412 | -0.0838 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=pneumonitis_ild | 9/62 | 3/72 | 10 | 9 | 0.1035 | -0.0215 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=pregnancy_or_breastfeeding | 6/62 | 9/72 | 10 | 9 | -0.0282 | -0.1532 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=pulmonary_function | 6/62 | 4/72 | 10 | 9 | 0.0412 | -0.0838 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=recent_radiotherapy | 15/62 | 19/72 | 8 | 8 | -0.022 | -0.1331 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=recent_surgery | 17/62 | 27/72 | 8 | 8 | -0.1008 | -0.2119 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=serious_comorbidity | 1/62 | 1/72 | 10 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=substance_or_psychiatric | 1/62 | 1/72 | 10 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=tissue_available | 11/62 | 10/72 | 9 | 8 | 0.0385 | -0.0726 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=unresolved_toxicity | 2/62 | 12/72 | 10 | 7 | -0.1344 | -0.2316 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=weight_loss | 1/62 | 0/72 | 10 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:ecog_ps=0\|1\|2 | 10/62 | 17/72 | 8 | 9 | -0.0748 | -0.1998 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:ecog_ps=1 | 2/62 | 0/72 | 9 | 9 | 0.0323 | -0.0927 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:extent:advanced | 12/62 | 14/72 | 6 | 5 | -0.0009 | -0.0703 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:extent:unresectable | 4/62 | 12/72 | 10 | 7 | -0.1022 | -0.1994 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:histology=adenocarcinoma | 3/62 | 1/72 | 9 | 9 | 0.0345 | -0.0905 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:histology=non_squamous | 25/62 | 32/72 | 4 | 5 | -0.0412 | -0.1107 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:histology=small_cell | 1/62 | 3/72 | 10 | 9 | -0.0255 | -0.1505 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:ALT | 11/62 | 19/72 | 8 | 8 | -0.0865 | -0.1976 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:AST | 9/62 | 15/72 | 8 | 9 | -0.0632 | -0.1882 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:bilirubin | 12/62 | 19/72 | 8 | 9 | -0.0703 | -0.1953 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:creatinine | 6/62 | 14/72 | 10 | 9 | -0.0977 | -0.2227 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:creatinine clearance | 11/62 | 16/72 | 8 | 8 | -0.0448 | -0.1559 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:hemoglobin | 10/62 | 19/72 | 9 | 8 | -0.1026 | -0.2137 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:leukocytes | 2/62 | 3/72 | 10 | 8 | -0.0094 | -0.1205 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:neutrophils | 12/62 | 21/72 | 8 | 8 | -0.0981 | -0.2092 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:platelets | 12/62 | 22/72 | 8 | 8 | -0.112 | -0.2231 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:ALK inhibitor | 3/62 | 2/72 | 10 | 9 | 0.0206 | -0.1044 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:CTLA-4 | 1/62 | 2/72 | 10 | 9 | -0.0116 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:EGFR inhibitor | 3/62 | 9/72 | 10 | 8 | -0.0766 | -0.1877 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:PD-1 | 5/62 | 2/72 | 10 | 9 | 0.0529 | -0.0721 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:PD-L1 | 4/62 | 2/72 | 10 | 9 | 0.0367 | -0.0883 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:chemotherapy | 19/62 | 23/72 | 8 | 4 | -0.013 | -0.0685 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:docetaxel | 2/62 | 2/72 | 10 | 8 | 0.0045 | -0.1066 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:immune checkpoint | 9/62 | 4/72 | 9 | 9 | 0.0896 | -0.0354 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:pemetrexed | 1/62 | 4/72 | 10 | 8 | -0.0394 | -0.1505 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:platinum | 10/62 | 17/72 | 9 | 5 | -0.0748 | -0.1443 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:radiotherapy | 11/62 | 19/72 | 8 | 7 | -0.0865 | -0.1837 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_lines=1 | 2/62 | 3/72 | 10 | 7 | -0.0094 | -0.1066 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_lines=1\|2\|3+ | 7/62 | 13/72 | 8 | 8 | -0.0677 | -0.1788 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_lines=2 | 2/62 | 2/72 | 9 | 9 | 0.0045 | -0.1205 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:resection:resectable | 4/62 | 5/72 | 10 | 8 | -0.0049 | -0.116 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:resection:resected | 7/62 | 8/72 | 9 | 8 | 0.0018 | -0.1093 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:setting_word:adjuvant | 10/62 | 14/72 | 7 | 8 | -0.0332 | -0.1443 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:setting_word:consolidation | 1/62 | 5/72 | 10 | 9 | -0.0533 | -0.1783 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:setting_word:maintenance | 1/62 | 2/72 | 10 | 9 | -0.0116 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:setting_word:neoadjuvant | 7/62 | 9/72 | 8 | 8 | -0.0121 | -0.1232 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:I | 3/62 | 1/72 | 9 | 9 | 0.0345 | -0.0905 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:II | 1/62 | 4/72 | 9 | 8 | -0.0394 | -0.1505 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:III\|IV | 7/62 | 12/72 | 7 | 6 | -0.0538 | -0.1371 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:II\|III | 7/62 | 7/72 | 9 | 8 | 0.0157 | -0.0954 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:I\|II | 2/62 | 2/72 | 10 | 9 | 0.0045 | -0.1205 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:I\|II\|III | 3/62 | 4/72 | 10 | 9 | -0.0072 | -0.1322 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:biomarker:EGFR=positive | 1/62 | 0/72 | 11 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=autoimmune_disease | 4/62 | 1/72 | 10 | 9 | 0.0506 | -0.0744 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=contraception | 1/62 | 1/72 | 10 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=immunosuppression_steroids | 4/62 | 1/72 | 10 | 9 | 0.0506 | -0.0744 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=live_vaccine | 1/62 | 0/72 | 11 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=measurable_disease | 1/62 | 0/72 | 11 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=recent_radiotherapy | 4/62 | 8/72 | 11 | 8 | -0.0466 | -0.1577 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:extent:advanced | 2/62 | 1/72 | 10 | 9 | 0.0184 | -0.1066 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:extent:locally advanced | 3/62 | 1/72 | 11 | 9 | 0.0345 | -0.0905 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:extent:metastatic | 5/62 | 3/72 | 10 | 9 | 0.039 | -0.086 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:extent:recurrent | 3/62 | 1/72 | 11 | 9 | 0.0345 | -0.0905 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:EGFR inhibitor | 1/62 | 0/72 | 11 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:VEGF inhibitor | 1/62 | 1/72 | 10 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:chemotherapy | 10/62 | 7/72 | 9 | 9 | 0.0641 | -0.0609 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:immune checkpoint | 2/62 | 2/72 | 11 | 9 | 0.0045 | -0.1205 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:radiotherapy | 7/62 | 8/72 | 11 | 9 | 0.0018 | -0.1232 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_lines=0 | 1/62 | 1/72 | 11 | 9 | 0.0022 | -0.1228 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_lines=1 | 1/62 | 2/72 | 10 | 9 | -0.0116 | -0.1366 | (not listed) | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_lines=1\|2 | 1/62 | 0/72 | 11 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:setting_word:adjuvant | 9/62 | 8/72 | 10 | 9 | 0.0341 | -0.0909 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:setting_word:maintenance | 1/62 | 1/72 | 11 | 8 | 0.0022 | -0.1089 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:setting_word:neoadjuvant | 8/62 | 4/72 | 10 | 9 | 0.0735 | -0.0515 | proposed | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:stage:III | 2/62 | 0/72 | 11 | 9 | 0.0323 | -0.0927 | below_support | unresolved |
| all trials | Programmed Death Receptor-1 Blocking Antibody | permitted:stage:IV | 1/62 | 0/72 | 11 | 9 | 0.0161 | -0.1089 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:condition=active_infection | 2/4 | 64/130 | 0 | 12 | 0.0077 | -0.0846 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:condition=cardiac_disease | 2/4 | 55/130 | 0 | 14 | 0.0769 | -0.0308 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:condition=diagnosis_confirmed | 1/4 | 27/130 | 0 | 16 | 0.0423 | -0.0808 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:condition=hiv | 2/4 | 61/130 | 0 | 12 | 0.0308 | -0.0615 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:condition=hypersensitivity | 2/4 | 57/130 | 0 | 9 | 0.0615 | -0.0077 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:condition=hypertension | 1/4 | 28/130 | 0 | 16 | 0.0346 | -0.0885 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:condition=neurologic_disorder | 1/4 | 30/130 | 0 | 11 | 0.0192 | -0.0654 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:condition=substance_or_psychiatric | 1/4 | 27/130 | 0 | 14 | 0.0423 | -0.0654 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:extent:metastatic | 1/4 | 27/130 | 0 | 13 | 0.0423 | -0.0577 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:extent:recurrent | 1/4 | 25/130 | 0 | 17 | 0.0577 | -0.0731 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | exclusion:prior_agent:PD-1 | 1/4 | 28/130 | 0 | 15 | 0.0346 | -0.0808 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:biomarker:ALK=positive | 1/4 | 20/130 | 0 | 18 | 0.0962 | -0.0423 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:condition=immunosuppression_steroids | 1/4 | 28/130 | 0 | 16 | 0.0346 | -0.0885 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 1/4 | 14/130 | 0 | 19 | 0.1423 | -0.0038 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:condition=sex | 1/4 | 24/130 | 0 | 16 | 0.0654 | -0.0577 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:condition=tissue_available | 1/4 | 20/130 | 0 | 17 | 0.0962 | -0.0346 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:ecog_ps=0\|1\|2 | 1/4 | 26/130 | 0 | 17 | 0.05 | -0.0808 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:extent:locally advanced | 1/4 | 24/130 | 0 | 15 | 0.0654 | -0.05 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:lab:ALT | 1/4 | 29/130 | 0 | 16 | 0.0269 | -0.0962 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:lab:AST | 1/4 | 23/130 | 0 | 17 | 0.0731 | -0.0577 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:lab:bilirubin | 1/4 | 30/130 | 0 | 17 | 0.0192 | -0.1115 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:lab:creatinine | 1/4 | 19/130 | 0 | 19 | 0.1038 | -0.0423 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:lab:hemoglobin | 1/4 | 28/130 | 0 | 17 | 0.0346 | -0.0962 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:lab:neutrophils | 1/4 | 32/130 | 0 | 16 | 0.0038 | -0.1192 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:prior_agent:radiotherapy | 1/4 | 29/130 | 0 | 15 | 0.0269 | -0.0885 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | inclusion:prior_lines=0 | 1/4 | 32/130 | 0 | 13 | 0.0038 | -0.0962 | below_support | unresolved |
| all trials | Topoisomerase Inhibitor | permitted:prior_agent:chemotherapy | 1/4 | 16/130 | 0 | 18 | 0.1269 | -0.0115 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=active_infection | 4/8 | 62/126 | 0 | 12 | 0.0079 | -0.0873 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=diagnosis_confirmed | 2/8 | 26/126 | 0 | 16 | 0.0437 | -0.0833 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=hiv | 4/8 | 59/126 | 0 | 12 | 0.0317 | -0.0635 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=hypertension | 2/8 | 27/126 | 0 | 16 | 0.0357 | -0.0913 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=informed_consent | 1/8 | 11/126 | 0 | 17 | 0.0377 | -0.0972 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=interacting_medication | 1/8 | 9/126 | 0 | 17 | 0.0536 | -0.0813 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=life_expectancy | 1/8 | 0/126 | 0 | 18 | 0.125 | -0.0179 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=measurable_disease | 1/8 | 6/126 | 0 | 18 | 0.0774 | -0.0655 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=other_malignancy | 4/8 | 60/126 | 0 | 13 | 0.0238 | -0.0794 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=qtc | 1/8 | 14/126 | 0 | 16 | 0.0139 | -0.1131 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=substance_or_psychiatric | 2/8 | 26/126 | 0 | 14 | 0.0437 | -0.0675 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=tuberculosis | 2/8 | 30/126 | 0 | 17 | 0.0119 | -0.123 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:extent:metastatic | 2/8 | 26/126 | 0 | 13 | 0.0437 | -0.0595 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:extent:recurrent | 2/8 | 24/126 | 0 | 17 | 0.0595 | -0.0754 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:lab:ALT | 1/8 | 1/126 | 0 | 18 | 0.1171 | -0.0258 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:lab:AST | 1/8 | 1/126 | 0 | 18 | 0.1171 | -0.0258 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:lab:bilirubin | 1/8 | 0/126 | 0 | 18 | 0.125 | -0.0179 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:lab:creatinine | 1/8 | 1/126 | 0 | 18 | 0.1171 | -0.0258 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:CTLA-4 | 1/8 | 7/126 | 0 | 18 | 0.0694 | -0.0734 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:PD-1 | 2/8 | 27/126 | 0 | 15 | 0.0357 | -0.0833 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:VEGF inhibitor | 1/8 | 0/126 | 0 | 18 | 0.125 | -0.0179 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:pemetrexed | 1/8 | 4/126 | 0 | 18 | 0.0933 | -0.0496 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:platinum | 1/8 | 10/126 | 0 | 16 | 0.0456 | -0.0813 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:taxane | 1/8 | 2/126 | 0 | 18 | 0.1091 | -0.0337 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_lines=1\|2\|3+ | 1/8 | 5/126 | 0 | 17 | 0.0853 | -0.0496 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | exclusion:stage:II | 1/8 | 0/126 | 0 | 18 | 0.125 | -0.0179 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:biomarker:EGFR=positive | 3/8 | 36/126 | 0 | 15 | 0.0893 | -0.0298 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 1/8 | 3/126 | 0 | 19 | 0.1012 | -0.0496 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:biomarker:PD-L1=positive | 1/8 | 5/126 | 0 | 19 | 0.0853 | -0.0655 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=anticoagulant_use | 1/8 | 2/126 | 0 | 19 | 0.1091 | -0.0417 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=bleeding_thrombosis | 1/8 | 4/126 | 0 | 19 | 0.0933 | -0.0575 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=cardiac_disease | 1/8 | 9/126 | 0 | 17 | 0.0536 | -0.0813 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=cns_metastases | 1/8 | 12/126 | 0 | 19 | 0.0298 | -0.121 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=compliance | 1/8 | 11/126 | 0 | 15 | 0.0377 | -0.0813 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=hepatitis | 1/8 | 9/126 | 0 | 19 | 0.0536 | -0.0972 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=hiv | 1/8 | 10/126 | 0 | 17 | 0.0456 | -0.0893 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=interacting_medication | 1/8 | 2/126 | 0 | 19 | 0.1091 | -0.0417 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=investigator_judgment | 1/8 | 9/126 | 0 | 19 | 0.0536 | -0.0972 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=malabsorption | 1/8 | 7/126 | 0 | 19 | 0.0694 | -0.0813 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=other_malignancy | 1/8 | 9/126 | 0 | 17 | 0.0536 | -0.0813 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 2/8 | 13/126 | 0 | 19 | 0.1468 | -0.004 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=qtc | 1/8 | 3/126 | 0 | 19 | 0.1012 | -0.0496 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=recent_surgery | 3/8 | 41/126 | 0 | 16 | 0.0496 | -0.0774 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=unresolved_toxicity | 1/8 | 13/126 | 0 | 17 | 0.0218 | -0.1131 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:ecog_ps=0\|1\|2 | 2/8 | 25/126 | 0 | 17 | 0.0516 | -0.0833 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:extent:unresectable | 1/8 | 15/126 | 0 | 17 | 0.006 | -0.129 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:lab:AST | 2/8 | 22/126 | 0 | 17 | 0.0754 | -0.0595 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:lab:creatinine clearance | 2/8 | 25/126 | 0 | 16 | 0.0516 | -0.0754 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:lab:leukocytes | 1/8 | 4/126 | 0 | 18 | 0.0933 | -0.0496 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:prior_agent:ALK inhibitor | 1/8 | 4/126 | 0 | 19 | 0.0933 | -0.0575 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:prior_agent:VEGF inhibitor | 1/8 | 1/126 | 0 | 19 | 0.1171 | -0.0337 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:prior_lines=1\|2\|3+ | 2/8 | 18/126 | 0 | 16 | 0.1071 | -0.0198 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:prior_lines=2 | 1/8 | 3/126 | 0 | 18 | 0.1012 | -0.0417 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:setting_word:neoadjuvant | 1/8 | 15/126 | 0 | 16 | 0.006 | -0.121 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:stage:III | 2/8 | 30/126 | 0 | 14 | 0.0119 | -0.0992 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:stage:IV | 3/8 | 38/126 | 0 | 16 | 0.0734 | -0.0536 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | inclusion:stage:I\|II\|III | 1/8 | 6/126 | 0 | 19 | 0.0774 | -0.0734 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | permitted:condition=recent_radiotherapy | 1/8 | 11/126 | 0 | 19 | 0.0377 | -0.1131 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | permitted:extent:advanced | 1/8 | 2/126 | 0 | 19 | 0.1091 | -0.0417 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | permitted:prior_agent:radiotherapy | 2/8 | 13/126 | 0 | 20 | 0.1468 | -0.0119 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | permitted:setting_word:adjuvant | 2/8 | 15/126 | 0 | 19 | 0.131 | -0.0198 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Inhibitor | permitted:setting_word:neoadjuvant | 1/8 | 11/126 | 0 | 19 | 0.0377 | -0.1131 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Receptor 2 Antagonist | inclusion:age=stated | 1/2 | 54/132 | 0 | 13 | 0.0909 | -0.0076 | below_support | unresolved |
| all trials | Vascular Endothelial Growth Factor Receptor 2 Antagonist | inclusion:condition=life_expectancy | 1/2 | 54/132 | 0 | 13 | 0.0909 | -0.0076 | below_support | unresolved |
| all trials | Vinca Alkaloid | exclusion:condition=active_infection | 1/2 | 65/132 | 0 | 12 | 0.0076 | -0.0833 | below_support | unresolved |
| all trials | Vinca Alkaloid | exclusion:condition=cardiac_disease | 1/2 | 56/132 | 0 | 14 | 0.0758 | -0.0303 | below_support | unresolved |
| all trials | Vinca Alkaloid | exclusion:condition=hepatitis | 1/2 | 58/132 | 0 | 12 | 0.0606 | -0.0303 | below_support | unresolved |
| all trials | Vinca Alkaloid | exclusion:condition=hiv | 1/2 | 62/132 | 0 | 12 | 0.0303 | -0.0606 | below_support | unresolved |
| all trials | Vinca Alkaloid | exclusion:condition=hypersensitivity | 1/2 | 58/132 | 0 | 9 | 0.0606 | -0.0076 | below_support | unresolved |
| all trials | Vinca Alkaloid | exclusion:condition=recent_radiotherapy | 1/2 | 60/132 | 0 | 14 | 0.0455 | -0.0606 | below_support | unresolved |
| all trials | Vinca Alkaloid | exclusion:condition=recent_surgery | 1/2 | 56/132 | 0 | 11 | 0.0758 | -0.0076 | below_support | unresolved |
| all trials | Vinca Alkaloid | inclusion:age=stated | 1/2 | 54/132 | 0 | 13 | 0.0909 | -0.0076 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:biomarker:EGFR=positive | 3/9 | 32/113 | 1 | 9 | 0.0501 | -0.0295 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:biomarker:ROS1=positive | 1/9 | 6/113 | 2 | 11 | 0.058 | -0.0393 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=active_infection | 5/9 | 54/113 | 1 | 9 | 0.0777 | -0.002 | proposed | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=hypersensitivity | 4/9 | 51/113 | 1 | 6 | -0.0069 | -0.06 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=hypertension | 1/9 | 26/113 | 2 | 11 | -0.119 | -0.2163 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=immunosuppression_steroids | 3/9 | 48/113 | 1 | 5 | -0.0914 | -0.1357 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=informed_consent | 1/9 | 8/113 | 2 | 12 | 0.0403 | -0.0659 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=investigator_judgment | 2/9 | 18/113 | 1 | 9 | 0.0629 | -0.0167 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=live_vaccine | 3/9 | 30/113 | 2 | 9 | 0.0678 | -0.0118 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=neurologic_disorder | 2/9 | 23/113 | 2 | 7 | 0.0187 | -0.0433 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=pneumonitis_ild | 5/9 | 58/113 | 1 | 6 | 0.0423 | -0.0108 | proposed | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=recent_radiotherapy | 4/9 | 51/113 | 2 | 10 | -0.0069 | -0.0954 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=tuberculosis | 3/9 | 28/113 | 2 | 11 | 0.0855 | -0.0118 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:condition=unresolved_toxicity | 1/9 | 19/113 | 2 | 11 | -0.057 | -0.1544 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:extent:locally advanced | 1/9 | 8/113 | 2 | 11 | 0.0403 | -0.057 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:extent:unresectable | 1/9 | 8/113 | 2 | 11 | 0.0403 | -0.057 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:CTLA-4 | 1/9 | 4/113 | 2 | 12 | 0.0757 | -0.0305 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:EGFR inhibitor | 1/9 | 9/113 | 2 | 12 | 0.0315 | -0.0747 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:PD-1 | 1/9 | 23/113 | 2 | 10 | -0.0924 | -0.1809 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:PD-L1 | 2/9 | 24/113 | 2 | 10 | 0.0098 | -0.0787 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:pemetrexed | 1/9 | 4/113 | 2 | 12 | 0.0757 | -0.0305 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:platinum | 1/9 | 10/113 | 2 | 10 | 0.0226 | -0.0659 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:radiotherapy | 3/9 | 40/113 | 2 | 10 | -0.0206 | -0.1091 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_agent:taxane | 1/9 | 2/113 | 2 | 12 | 0.0934 | -0.0128 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:prior_lines=1\|2\|3+ | 1/9 | 4/113 | 2 | 11 | 0.0757 | -0.0216 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | exclusion:stage:IV | 1/9 | 3/113 | 2 | 12 | 0.0846 | -0.0216 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:age=stated | 3/9 | 47/113 | 1 | 10 | -0.0826 | -0.1711 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ALK=negative\|positive | 1/9 | 0/113 | 2 | 13 | 0.1111 | -0.0039 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ALK=positive | 1/9 | 19/113 | 2 | 12 | -0.057 | -0.1632 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:EGFR=negative | 1/9 | 18/113 | 1 | 10 | -0.0482 | -0.1367 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:EGFR=negative\|positive | 1/9 | 0/113 | 2 | 13 | 0.1111 | -0.0039 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:EGFR=positive | 1/9 | 36/113 | 2 | 10 | -0.2075 | -0.296 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:PD-L1=@<1% | 1/9 | 1/113 | 1 | 13 | 0.1023 | -0.0128 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:RET=positive | 1/9 | 4/113 | 2 | 13 | 0.0757 | -0.0393 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ROS1=negative | 1/9 | 6/113 | 1 | 13 | 0.058 | -0.057 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:biomarker:ROS1=positive | 1/9 | 6/113 | 2 | 13 | 0.058 | -0.057 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=active_infection | 1/9 | 4/113 | 1 | 12 | 0.0757 | -0.0305 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=cardiac_disease | 1/9 | 8/113 | 1 | 12 | 0.0403 | -0.0659 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=compliance | 1/9 | 10/113 | 1 | 10 | 0.0226 | -0.0659 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=contraception | 3/9 | 57/113 | 2 | 11 | -0.1711 | -0.2684 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=hiv | 1/9 | 9/113 | 1 | 12 | 0.0315 | -0.0747 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=informed_consent | 2/9 | 41/113 | 2 | 10 | -0.1406 | -0.2291 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=life_expectancy | 4/9 | 44/113 | 2 | 10 | 0.0551 | -0.0334 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=measurable_disease | 4/9 | 62/113 | 1 | 6 | -0.1042 | -0.1573 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=neurologic_disorder | 1/9 | 0/113 | 1 | 13 | 0.1111 | -0.0039 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=other_investigational | 1/9 | 4/113 | 2 | 12 | 0.0757 | -0.0305 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=other_malignancy | 1/9 | 6/113 | 1 | 12 | 0.058 | -0.0482 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=pneumonitis_ild | 1/9 | 8/113 | 2 | 13 | 0.0403 | -0.0747 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=pregnancy_or_breastfeeding | 1/9 | 11/113 | 2 | 13 | 0.0138 | -0.1013 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=pulmonary_function | 1/9 | 8/113 | 2 | 13 | 0.0403 | -0.0747 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:condition=tissue_available | 1/9 | 17/113 | 2 | 12 | -0.0393 | -0.1455 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:extent:advanced | 1/9 | 20/113 | 1 | 8 | -0.0659 | -0.1367 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:extent:locally advanced | 2/9 | 21/113 | 2 | 10 | 0.0364 | -0.0521 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:extent:recurrent | 2/9 | 26/113 | 1 | 11 | -0.0079 | -0.1052 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:extent:unresectable | 1/9 | 12/113 | 2 | 12 | 0.0049 | -0.1013 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:histology=squamous | 1/9 | 12/113 | 1 | 9 | 0.0049 | -0.0747 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:lab:bilirubin | 3/9 | 26/113 | 1 | 12 | 0.1032 | -0.0029 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:lab:creatinine | 1/9 | 18/113 | 2 | 13 | -0.0482 | -0.1632 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:lab:hemoglobin | 2/9 | 25/113 | 2 | 11 | 0.001 | -0.0964 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:lab:leukocytes | 1/9 | 3/113 | 2 | 12 | 0.0846 | -0.0216 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:lab:neutrophils | 3/9 | 28/113 | 1 | 11 | 0.0855 | -0.0118 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:lab:platelets | 3/9 | 29/113 | 1 | 11 | 0.0767 | -0.0206 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:prior_agent:EGFR inhibitor | 1/9 | 11/113 | 2 | 12 | 0.0138 | -0.0924 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:prior_lines=0 | 2/9 | 19/113 | 1 | 12 | 0.0541 | -0.0521 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:prior_lines=1\|2\|3+ | 2/9 | 18/113 | 2 | 10 | 0.0629 | -0.0256 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:setting_word:adjuvant | 1/9 | 23/113 | 1 | 10 | -0.0924 | -0.1809 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:setting_word:consolidation | 1/9 | 4/113 | 2 | 13 | 0.0757 | -0.0393 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | inclusion:setting_word:maintenance | 1/9 | 2/113 | 2 | 13 | 0.0934 | -0.0216 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:biomarker:EGFR=positive | 1/9 | 0/113 | 3 | 13 | 0.1111 | -0.0039 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:condition=autoimmune_disease | 1/9 | 3/113 | 2 | 13 | 0.0846 | -0.0305 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:condition=contraception | 1/9 | 1/113 | 2 | 13 | 0.1023 | -0.0128 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:condition=immunosuppression_steroids | 1/9 | 3/113 | 2 | 13 | 0.0846 | -0.0305 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:extent:advanced | 1/9 | 2/113 | 2 | 13 | 0.0934 | -0.0216 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:extent:metastatic | 1/9 | 7/113 | 2 | 13 | 0.0492 | -0.0659 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:prior_agent:EGFR inhibitor | 1/9 | 0/113 | 3 | 13 | 0.1111 | -0.0039 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:prior_agent:VEGF inhibitor | 1/9 | 1/113 | 2 | 13 | 0.1023 | -0.0128 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:prior_agent:chemotherapy | 2/9 | 15/113 | 1 | 13 | 0.0895 | -0.0256 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:prior_lines=1 | 1/9 | 2/113 | 2 | 13 | 0.0934 | -0.0216 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:prior_lines=1\|2 | 1/9 | 0/113 | 3 | 13 | 0.1111 | -0.0039 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:setting_word:adjuvant | 1/9 | 16/113 | 2 | 13 | -0.0305 | -0.1455 | (not listed) | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:setting_word:neoadjuvant | 1/9 | 11/113 | 2 | 13 | 0.0138 | -0.1013 | below_support | unresolved |
| setting unresolved | CTLA-4-directed Blocking Antibody | permitted:stage:IV | 1/9 | 0/113 | 3 | 13 | 0.1111 | -0.0039 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:biomarker:ALK=positive | 9/30 | 21/92 | 0 | 9 | 0.0717 | -0.0261 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:biomarker:BRAF=positive | 2/30 | 3/92 | 1 | 12 | 0.0341 | -0.0964 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:biomarker:EGFR=negative | 1/30 | 1/92 | 1 | 13 | 0.0225 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:biomarker:ROS1=positive | 2/30 | 5/92 | 1 | 12 | 0.0123 | -0.1181 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=anticoagulant_use | 1/30 | 6/92 | 1 | 13 | -0.0319 | -0.1732 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=contraception | 2/30 | 3/92 | 1 | 13 | 0.0341 | -0.1072 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=effusion | 6/30 | 11/92 | 1 | 11 | 0.0804 | -0.0391 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=gi_perforation_fistula | 2/30 | 5/92 | 1 | 13 | 0.0123 | -0.129 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=hepatitis | 13/30 | 40/92 | 1 | 9 | -0.0014 | -0.0993 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=live_vaccine | 10/30 | 23/92 | 1 | 10 | 0.0833 | -0.0254 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=measurable_disease | 2/30 | 5/92 | 1 | 13 | 0.0123 | -0.129 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=organ_transplant | 10/30 | 23/92 | 1 | 12 | 0.0833 | -0.0471 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=other_investigational | 12/30 | 29/92 | 1 | 11 | 0.0848 | -0.0348 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=recent_radiotherapy | 16/30 | 39/92 | 0 | 12 | 0.1094 | -0.021 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=sex | 1/30 | 2/92 | 1 | 13 | 0.0116 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=tuberculosis | 9/30 | 22/92 | 1 | 12 | 0.0609 | -0.0696 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=unresolved_toxicity | 5/30 | 15/92 | 1 | 12 | 0.0036 | -0.1268 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:condition=vitamin_premedication | 1/30 | 0/92 | 1 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:extent:advanced | 1/30 | 3/92 | 1 | 12 | 0.0007 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:extent:unresectable | 2/30 | 7/92 | 1 | 12 | -0.0094 | -0.1399 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:histology=large_cell | 2/30 | 3/92 | 1 | 13 | 0.0341 | -0.1072 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:histology=non_squamous | 1/30 | 4/92 | 1 | 12 | -0.0101 | -0.1406 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:histology=small_cell | 4/30 | 10/92 | 1 | 13 | 0.0246 | -0.1167 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:histology=squamous | 6/30 | 7/92 | 1 | 12 | 0.1239 | -0.0065 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:lab:creatinine clearance | 1/30 | 2/92 | 1 | 13 | 0.0116 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:ALK inhibitor | 1/30 | 4/92 | 1 | 13 | -0.0101 | -0.1514 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:CTLA-4 | 4/30 | 1/92 | 1 | 13 | 0.1225 | -0.0188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:PD-L1 | 9/30 | 17/92 | 1 | 11 | 0.1152 | -0.0043 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:VEGF inhibitor | 1/30 | 0/92 | 1 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:chemotherapy | 9/30 | 22/92 | 0 | 10 | 0.0609 | -0.0478 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:immune checkpoint | 8/30 | 15/92 | 1 | 11 | 0.1036 | -0.0159 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:pemetrexed | 4/30 | 1/92 | 1 | 13 | 0.1225 | -0.0188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:platinum | 5/30 | 6/92 | 1 | 11 | 0.1014 | -0.0181 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:radiotherapy | 13/30 | 30/92 | 0 | 12 | 0.1072 | -0.0232 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_agent:taxane | 2/30 | 1/92 | 1 | 13 | 0.0558 | -0.0855 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_lines=1 | 1/30 | 5/92 | 1 | 12 | -0.021 | -0.1514 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:prior_lines=1\|2\|3+ | 1/30 | 4/92 | 1 | 12 | -0.0101 | -0.1406 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:resection:resected | 1/30 | 1/92 | 1 | 13 | 0.0225 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:setting_word:consolidation | 1/30 | 0/92 | 1 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:setting_word:maintenance | 1/30 | 3/92 | 1 | 12 | 0.0007 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:stage:I | 1/30 | 2/92 | 1 | 13 | 0.0116 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:stage:III | 1/30 | 4/92 | 1 | 13 | -0.0101 | -0.1514 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:stage:III\|IV | 1/30 | 0/92 | 1 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:stage:II\|III | 1/30 | 0/92 | 1 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | exclusion:stage:I\|III | 1/30 | 0/92 | 1 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:age=stated | 13/30 | 37/92 | 1 | 10 | 0.0312 | -0.0775 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ALK=negative | 5/30 | 8/92 | 1 | 12 | 0.0797 | -0.0507 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ALK=unknown | 1/30 | 0/92 | 2 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:EGFR=positive | 11/30 | 26/92 | 2 | 10 | 0.0841 | -0.0246 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:EGFR=unknown | 1/30 | 1/92 | 2 | 12 | 0.0225 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:KRAS=positive | 2/30 | 3/92 | 2 | 13 | 0.0341 | -0.1072 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:MET=positive | 1/30 | 2/92 | 2 | 13 | 0.0116 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=@1-49% | 1/30 | 0/92 | 2 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=@>=1% | 1/30 | 0/92 | 2 | 13 | 0.0333 | -0.108 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 1/30 | 3/92 | 2 | 13 | 0.0007 | -0.1406 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:PD-L1=positive | 2/30 | 4/92 | 2 | 13 | 0.0232 | -0.1181 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:biomarker:ROS1=negative | 3/30 | 4/92 | 2 | 12 | 0.0565 | -0.0739 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=active_infection | 2/30 | 3/92 | 1 | 12 | 0.0341 | -0.0964 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=anticoagulant_use | 2/30 | 1/92 | 2 | 13 | 0.0558 | -0.0855 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=bleeding_thrombosis | 1/30 | 4/92 | 2 | 13 | -0.0101 | -0.1514 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=cardiac_disease | 3/30 | 6/92 | 1 | 12 | 0.0348 | -0.0957 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=cns_metastases | 5/30 | 7/92 | 2 | 13 | 0.0906 | -0.0507 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=gi_perforation_fistula | 2/30 | 2/92 | 2 | 13 | 0.0449 | -0.0964 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=hepatitis | 3/30 | 6/92 | 2 | 13 | 0.0348 | -0.1065 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=hiv | 5/30 | 5/92 | 1 | 12 | 0.1123 | -0.0181 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=hypersensitivity | 1/30 | 1/92 | 2 | 13 | 0.0225 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=hypertension | 3/30 | 7/92 | 2 | 13 | 0.0239 | -0.1174 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=interacting_medication | 1/30 | 2/92 | 2 | 13 | 0.0116 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=investigator_judgment | 2/30 | 8/92 | 2 | 13 | -0.0203 | -0.1616 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=life_expectancy | 11/30 | 37/92 | 2 | 10 | -0.0355 | -0.1442 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=malabsorption | 1/30 | 7/92 | 2 | 13 | -0.0428 | -0.1841 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=organ_transplant | 1/30 | 1/92 | 2 | 13 | 0.0225 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=pneumonitis_ild | 5/30 | 4/92 | 2 | 13 | 0.1232 | -0.0181 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 2/30 | 10/92 | 2 | 13 | -0.042 | -0.1833 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=pulmonary_function | 1/30 | 8/92 | 2 | 13 | -0.0536 | -0.1949 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=qtc | 1/30 | 3/92 | 2 | 13 | 0.0007 | -0.1406 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=recent_radiotherapy | 8/30 | 24/92 | 2 | 11 | 0.0058 | -0.1138 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=recent_surgery | 11/30 | 32/92 | 1 | 11 | 0.0188 | -0.1007 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=sex | 6/30 | 16/92 | 2 | 11 | 0.0261 | -0.0935 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=tissue_available | 4/30 | 14/92 | 2 | 12 | -0.0188 | -0.1493 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:condition=unresolved_toxicity | 2/30 | 11/92 | 2 | 11 | -0.0529 | -0.1725 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:extent:locally advanced | 7/30 | 16/92 | 2 | 10 | 0.0594 | -0.0493 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:extent:unresectable | 4/30 | 9/92 | 2 | 12 | 0.0355 | -0.0949 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:histology=adenocarcinoma | 1/30 | 3/92 | 2 | 12 | 0.0007 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:histology=squamous | 3/30 | 10/92 | 1 | 9 | -0.0087 | -0.1065 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:lab:AST | 5/30 | 18/92 | 1 | 12 | -0.029 | -0.1594 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:lab:creatinine clearance | 7/30 | 18/92 | 1 | 11 | 0.0377 | -0.0819 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:organ_function_unspecified=adequate | 8/30 | 26/92 | 2 | 10 | -0.0159 | -0.1246 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:ALK inhibitor | 1/30 | 3/92 | 2 | 13 | 0.0007 | -0.1406 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:CTLA-4 | 1/30 | 2/92 | 2 | 13 | 0.0116 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:PD-1 | 1/30 | 6/92 | 2 | 13 | -0.0319 | -0.1732 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:PD-L1 | 1/30 | 5/92 | 2 | 13 | -0.021 | -0.1623 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:immune checkpoint | 3/30 | 10/92 | 2 | 12 | -0.0087 | -0.1391 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_agent:pemetrexed | 3/30 | 2/92 | 2 | 12 | 0.0783 | -0.0522 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_lines=0 | 5/30 | 16/92 | 2 | 11 | -0.0072 | -0.1268 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_lines=1 | 1/30 | 4/92 | 2 | 11 | -0.0101 | -0.1297 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:prior_lines=1\|2\|3+ | 5/30 | 15/92 | 2 | 10 | 0.0036 | -0.1051 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:resection:resected | 5/30 | 10/92 | 1 | 12 | 0.058 | -0.0725 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:setting_word:consolidation | 2/30 | 3/92 | 2 | 13 | 0.0341 | -0.1072 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:setting_word:maintenance | 1/30 | 2/92 | 2 | 13 | 0.0116 | -0.1297 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:setting_word:neoadjuvant | 4/30 | 12/92 | 1 | 11 | 0.0029 | -0.1167 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:stage:I | 2/30 | 2/92 | 1 | 13 | 0.0449 | -0.0964 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:stage:II | 3/30 | 2/92 | 1 | 12 | 0.0783 | -0.0522 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:stage:III | 6/30 | 24/92 | 2 | 9 | -0.0609 | -0.1587 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:stage:II\|III | 6/30 | 8/92 | 1 | 12 | 0.113 | -0.0174 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:stage:IV | 10/30 | 24/92 | 2 | 11 | 0.0725 | -0.0471 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | inclusion:stage:I\|II\|III | 1/30 | 6/92 | 2 | 13 | -0.0319 | -0.1732 | (not listed) | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:biomarker:EGFR=negative | 1/30 | 0/92 | 2 | 14 | 0.0333 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:biomarker:EGFR=positive | 1/30 | 0/92 | 2 | 14 | 0.0333 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:condition=autoimmune_disease | 1/30 | 3/92 | 2 | 13 | 0.0007 | -0.1406 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:condition=measurable_disease | 1/30 | 0/92 | 2 | 14 | 0.0333 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:condition=pneumonitis_ild | 1/30 | 0/92 | 2 | 14 | 0.0333 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:condition=recent_radiotherapy | 3/30 | 9/92 | 2 | 13 | 0.0022 | -0.1391 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:extent:locally advanced | 2/30 | 2/92 | 2 | 14 | 0.0449 | -0.1072 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:extent:metastatic | 4/30 | 4/92 | 2 | 13 | 0.0899 | -0.0514 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:extent:recurrent | 4/30 | 0/92 | 2 | 14 | 0.1333 | -0.0188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:prior_agent:EGFR inhibitor | 1/30 | 0/92 | 2 | 14 | 0.0333 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:prior_agent:chemotherapy | 7/30 | 10/92 | 2 | 12 | 0.1246 | -0.0058 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:prior_agent:immune checkpoint | 2/30 | 2/92 | 2 | 14 | 0.0449 | -0.1072 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:prior_agent:radiotherapy | 7/30 | 8/92 | 2 | 14 | 0.1464 | -0.0058 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:prior_lines=1\|2 | 1/30 | 0/92 | 2 | 14 | 0.0333 | -0.1188 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:setting_word:adjuvant | 6/30 | 11/92 | 2 | 13 | 0.0804 | -0.0609 | proposed | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:setting_word:neoadjuvant | 4/30 | 8/92 | 2 | 13 | 0.0464 | -0.0949 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:stage:III | 2/30 | 0/92 | 2 | 14 | 0.0667 | -0.0855 | below_support | unresolved |
| setting unresolved | Folate Analog Metabolic Inhibitor | permitted:stage:IV | 1/30 | 0/92 | 2 | 14 | 0.0333 | -0.1188 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:biomarker:BRAF=positive | 4/40 | 1/82 | 1 | 12 | 0.0878 | -0.0585 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:biomarker:EGFR=negative | 2/40 | 0/82 | 2 | 12 | 0.05 | -0.0963 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:biomarker:KRAS=positive | 1/40 | 0/82 | 1 | 12 | 0.025 | -0.1213 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:biomarker:MET=positive | 1/40 | 0/82 | 2 | 12 | 0.025 | -0.1213 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:biomarker:NTRK=positive | 1/40 | 0/82 | 1 | 12 | 0.025 | -0.1213 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:biomarker:RET=positive | 2/40 | 0/82 | 1 | 12 | 0.05 | -0.0963 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:biomarker:ROS1=positive | 4/40 | 3/82 | 1 | 12 | 0.0634 | -0.0829 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=anticoagulant_use | 3/40 | 4/82 | 2 | 12 | 0.0262 | -0.1201 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=compliance | 3/40 | 1/82 | 2 | 12 | 0.0628 | -0.0835 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=contraception | 1/40 | 4/82 | 2 | 12 | -0.0238 | -0.1701 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=effusion | 6/40 | 11/82 | 2 | 10 | 0.0159 | -0.1061 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=gi_perforation_fistula | 4/40 | 3/82 | 2 | 12 | 0.0634 | -0.0829 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=hypertension | 12/40 | 15/82 | 2 | 11 | 0.1171 | -0.0171 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=interacting_medication | 6/40 | 4/82 | 2 | 11 | 0.1012 | -0.0329 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=measurable_disease | 2/40 | 5/82 | 2 | 12 | -0.011 | -0.1573 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=neurologic_disorder | 8/40 | 17/82 | 1 | 8 | -0.0073 | -0.1049 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=organ_impairment | 4/40 | 5/82 | 2 | 11 | 0.039 | -0.0951 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=other_malignancy | 22/40 | 38/82 | 2 | 9 | 0.0866 | -0.0232 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=prior_enrollment | 1/40 | 0/82 | 2 | 12 | 0.025 | -0.1213 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=pulmonary_function | 1/40 | 1/82 | 2 | 11 | 0.0128 | -0.1213 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=recent_radiotherapy | 21/40 | 34/82 | 2 | 10 | 0.1104 | -0.0116 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=recent_surgery | 20/40 | 32/82 | 1 | 9 | 0.1098 | 0.0 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=serious_comorbidity | 7/40 | 11/82 | 2 | 11 | 0.0409 | -0.0933 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:condition=substance_or_psychiatric | 11/40 | 14/82 | 1 | 10 | 0.1043 | -0.0177 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:extent:recurrent | 10/40 | 15/82 | 2 | 11 | 0.0671 | -0.0671 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:histology=adenocarcinoma | 1/40 | 2/82 | 2 | 12 | 0.0006 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:histology=squamous | 4/40 | 9/82 | 2 | 11 | -0.0098 | -0.1439 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:lab:ALT | 1/40 | 1/82 | 2 | 12 | 0.0128 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:lab:AST | 1/40 | 1/82 | 2 | 12 | 0.0128 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:lab:bilirubin | 1/40 | 0/82 | 2 | 12 | 0.025 | -0.1213 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:lab:creatinine | 1/40 | 1/82 | 2 | 12 | 0.0128 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_agent:ALK inhibitor | 3/40 | 2/82 | 2 | 12 | 0.0506 | -0.0957 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_agent:EGFR inhibitor | 3/40 | 7/82 | 2 | 12 | -0.0104 | -0.1567 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_agent:MET inhibitor | 2/40 | 1/82 | 0 | 12 | 0.0378 | -0.1085 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_agent:chemotherapy | 12/40 | 19/82 | 2 | 8 | 0.0683 | -0.0293 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_agent:docetaxel | 2/40 | 6/82 | 2 | 10 | -0.0232 | -0.1451 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_agent:pemetrexed | 2/40 | 3/82 | 2 | 12 | 0.0134 | -0.1329 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_agent:platinum | 3/40 | 8/82 | 2 | 10 | -0.0226 | -0.1445 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_agent:radiotherapy | 17/40 | 26/82 | 2 | 10 | 0.1079 | -0.014 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_lines=1 | 1/40 | 5/82 | 2 | 11 | -0.036 | -0.1701 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:prior_lines=1\|2\|3+ | 1/40 | 4/82 | 2 | 11 | -0.0238 | -0.1579 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:resection:resected | 1/40 | 1/82 | 2 | 12 | 0.0128 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:stage:I | 2/40 | 1/82 | 2 | 12 | 0.0378 | -0.1085 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:stage:III | 1/40 | 4/82 | 2 | 12 | -0.0238 | -0.1701 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:stage:II\|III | 1/40 | 0/82 | 2 | 12 | 0.025 | -0.1213 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:stage:IV | 1/40 | 3/82 | 2 | 12 | -0.0116 | -0.1579 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | exclusion:stage:I\|III | 1/40 | 0/82 | 2 | 12 | 0.025 | -0.1213 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:ALK=negative | 3/40 | 10/82 | 2 | 11 | -0.047 | -0.1811 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:KRAS=positive | 3/40 | 2/82 | 2 | 13 | 0.0506 | -0.1079 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:MET=negative | 1/40 | 1/82 | 1 | 13 | 0.0128 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:MET=positive | 1/40 | 2/82 | 2 | 13 | 0.0006 | -0.1579 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:PD-L1=@<1% | 1/40 | 1/82 | 2 | 12 | 0.0128 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:PD-L1=@≥1% | 2/40 | 0/82 | 2 | 13 | 0.05 | -0.1085 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 1/40 | 3/82 | 2 | 13 | -0.0116 | -0.1701 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:PD-L1=positive | 1/40 | 5/82 | 2 | 13 | -0.036 | -0.1945 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:PD-L1=unknown | 1/40 | 0/82 | 2 | 13 | 0.025 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:RET=positive | 3/40 | 2/82 | 2 | 13 | 0.0506 | -0.1079 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:ROS1=negative | 3/40 | 4/82 | 2 | 12 | 0.0262 | -0.1201 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:biomarker:ROS1=positive | 2/40 | 5/82 | 2 | 13 | -0.011 | -0.1695 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=active_infection | 2/40 | 3/82 | 2 | 11 | 0.0134 | -0.1207 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=anticoagulant_use | 1/40 | 2/82 | 2 | 13 | 0.0006 | -0.1579 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=bleeding_thrombosis | 3/40 | 2/82 | 2 | 13 | 0.0506 | -0.1079 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=cardiac_disease | 4/40 | 5/82 | 2 | 11 | 0.039 | -0.0951 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=cns_metastases | 4/40 | 8/82 | 2 | 13 | 0.0024 | -0.1561 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=contraception | 23/40 | 37/82 | 2 | 11 | 0.1238 | -0.0104 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=diagnosis_confirmed | 32/40 | 62/82 | 0 | 6 | 0.0439 | -0.0293 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=effusion | 1/40 | 0/82 | 2 | 13 | 0.025 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=gi_perforation_fistula | 4/40 | 0/82 | 2 | 13 | 0.1 | -0.0585 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=hepatitis | 3/40 | 6/82 | 2 | 13 | 0.0018 | -0.1567 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=hiv | 4/40 | 6/82 | 2 | 11 | 0.0268 | -0.1073 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=hypersensitivity | 1/40 | 1/82 | 2 | 13 | 0.0128 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=interacting_medication | 3/40 | 0/82 | 2 | 13 | 0.075 | -0.0835 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=investigator_judgment | 4/40 | 6/82 | 2 | 13 | 0.0268 | -0.1317 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=life_expectancy | 16/40 | 32/82 | 1 | 11 | 0.0098 | -0.1244 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=malabsorption | 5/40 | 3/82 | 2 | 13 | 0.0884 | -0.0701 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=measurable_disease | 22/40 | 44/82 | 0 | 7 | 0.0134 | -0.072 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=other_malignancy | 3/40 | 4/82 | 2 | 11 | 0.0262 | -0.1079 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=pneumonitis_ild | 5/40 | 4/82 | 2 | 13 | 0.0762 | -0.0823 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 5/40 | 7/82 | 2 | 13 | 0.0396 | -0.1189 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=pulmonary_function | 2/40 | 7/82 | 2 | 13 | -0.0354 | -0.1939 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=qtc | 4/40 | 0/82 | 2 | 13 | 0.1 | -0.0585 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=recent_radiotherapy | 11/40 | 21/82 | 2 | 11 | 0.0189 | -0.1152 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=recent_surgery | 13/40 | 30/82 | 2 | 10 | -0.0409 | -0.1628 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=sex | 7/40 | 15/82 | 2 | 11 | -0.0079 | -0.1421 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=substance_or_psychiatric | 1/40 | 1/82 | 2 | 13 | 0.0128 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:condition=tissue_available | 8/40 | 10/82 | 2 | 12 | 0.078 | -0.0683 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:extent:advanced | 7/40 | 14/82 | 0 | 9 | 0.0043 | -0.1055 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:extent:locally advanced | 8/40 | 15/82 | 2 | 10 | 0.0171 | -0.1049 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:extent:recurrent | 9/40 | 19/82 | 2 | 10 | -0.0067 | -0.1287 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:extent:unresectable | 5/40 | 8/82 | 1 | 13 | 0.0274 | -0.1311 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:histology=adenocarcinoma | 1/40 | 3/82 | 2 | 12 | -0.0116 | -0.1579 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:histology=large_cell | 1/40 | 0/82 | 2 | 13 | 0.025 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:histology=small_cell | 1/40 | 3/82 | 2 | 13 | -0.0116 | -0.1701 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:lab:ALT | 9/40 | 20/82 | 2 | 10 | -0.0189 | -0.1409 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:lab:AST | 7/40 | 16/82 | 2 | 11 | -0.0201 | -0.1543 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:lab:bilirubin | 9/40 | 20/82 | 2 | 11 | -0.0189 | -0.153 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:lab:creatinine | 8/40 | 11/82 | 2 | 13 | 0.0659 | -0.0927 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:lab:hemoglobin | 9/40 | 18/82 | 2 | 11 | 0.0055 | -0.1287 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:lab:leukocytes | 1/40 | 3/82 | 2 | 12 | -0.0116 | -0.1579 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:lab:neutrophils | 10/40 | 21/82 | 2 | 10 | -0.0061 | -0.128 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:lab:platelets | 10/40 | 22/82 | 2 | 10 | -0.0183 | -0.1402 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:organ_function_unspecified=adequate | 13/40 | 21/82 | 0 | 12 | 0.0689 | -0.0774 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:ALK inhibitor | 2/40 | 2/82 | 2 | 13 | 0.0256 | -0.1329 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:EGFR inhibitor | 6/40 | 6/82 | 1 | 13 | 0.0768 | -0.0817 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:PD-1 | 2/40 | 5/82 | 2 | 13 | -0.011 | -0.1695 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:PD-L1 | 2/40 | 4/82 | 2 | 13 | 0.0012 | -0.1573 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:VEGF inhibitor | 2/40 | 0/82 | 2 | 13 | 0.05 | -0.1085 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:docetaxel | 2/40 | 2/82 | 1 | 13 | 0.0256 | -0.1329 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:immune checkpoint | 3/40 | 10/82 | 2 | 12 | -0.047 | -0.1933 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:pemetrexed | 1/40 | 4/82 | 1 | 13 | -0.0238 | -0.1823 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_agent:radiotherapy | 8/40 | 20/82 | 2 | 10 | -0.0439 | -0.1659 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_lines=0\|1\|2 | 1/40 | 0/82 | 2 | 13 | 0.025 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_lines=1 | 2/40 | 3/82 | 1 | 12 | 0.0134 | -0.1329 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_lines=1\|2 | 1/40 | 0/82 | 1 | 13 | 0.025 | -0.1335 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:prior_lines=2 | 2/40 | 2/82 | 2 | 12 | 0.0256 | -0.1207 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:resection:resected | 5/40 | 10/82 | 2 | 11 | 0.003 | -0.1311 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:setting_word:adjuvant | 8/40 | 16/82 | 2 | 9 | 0.0049 | -0.1049 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:setting_word:consolidation | 2/40 | 3/82 | 2 | 13 | 0.0134 | -0.1451 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:setting_word:maintenance | 1/40 | 2/82 | 2 | 13 | 0.0006 | -0.1579 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:setting_word:neoadjuvant | 5/40 | 11/82 | 2 | 10 | -0.0091 | -0.1311 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:stage:I | 1/40 | 3/82 | 2 | 12 | -0.0116 | -0.1579 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:stage:II | 1/40 | 4/82 | 2 | 11 | -0.0238 | -0.1579 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:stage:III\|IV | 6/40 | 12/82 | 1 | 9 | 0.0037 | -0.1061 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:stage:II\|III | 4/40 | 10/82 | 2 | 11 | -0.022 | -0.1561 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:stage:IV | 11/40 | 23/82 | 2 | 11 | -0.0055 | -0.1396 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:stage:I\|II | 2/40 | 2/82 | 2 | 13 | 0.0256 | -0.1329 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | inclusion:stage:I\|II\|III | 2/40 | 5/82 | 2 | 13 | -0.011 | -0.1695 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:biomarker:EGFR=negative | 1/40 | 0/82 | 2 | 14 | 0.025 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:condition=cns_metastases | 5/40 | 1/82 | 2 | 14 | 0.1128 | -0.0579 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:condition=contraception | 1/40 | 1/82 | 2 | 13 | 0.0128 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:condition=immunosuppression_steroids | 3/40 | 1/82 | 2 | 13 | 0.0628 | -0.0957 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:condition=other_malignancy | 2/40 | 0/82 | 2 | 14 | 0.05 | -0.1207 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:condition=pneumonitis_ild | 1/40 | 0/82 | 2 | 14 | 0.025 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:condition=pregnancy_or_breastfeeding | 1/40 | 0/82 | 2 | 14 | 0.025 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:condition=recent_radiotherapy | 4/40 | 8/82 | 2 | 13 | 0.0024 | -0.1561 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:condition=recent_surgery | 2/40 | 0/82 | 2 | 14 | 0.05 | -0.1207 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:extent:advanced | 1/40 | 2/82 | 2 | 13 | 0.0006 | -0.1579 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:extent:metastatic | 3/40 | 5/82 | 2 | 13 | 0.014 | -0.1445 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:histology=adenocarcinoma | 1/40 | 0/82 | 2 | 14 | 0.025 | -0.1457 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:prior_agent:chemotherapy | 6/40 | 11/82 | 2 | 12 | 0.0159 | -0.1305 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:prior_agent:immune checkpoint | 1/40 | 3/82 | 2 | 14 | -0.0116 | -0.1823 | (not listed) | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:prior_agent:radiotherapy | 5/40 | 10/82 | 2 | 14 | 0.003 | -0.1677 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:prior_lines=1 | 1/40 | 2/82 | 2 | 13 | 0.0006 | -0.1579 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:setting_word:adjuvant | 6/40 | 11/82 | 2 | 13 | 0.0159 | -0.1427 | proposed | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:setting_word:neoadjuvant | 4/40 | 8/82 | 2 | 13 | 0.0024 | -0.1561 | below_support | unresolved |
| setting unresolved | Kinase Inhibitor | permitted:stage:I\|II | 1/40 | 0/82 | 2 | 14 | 0.025 | -0.1457 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:biomarker:EGFR=negative | 1/23 | 1/99 | 2 | 12 | 0.0334 | -0.0878 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:biomarker:ROS1=positive | 1/23 | 6/99 | 2 | 11 | -0.0171 | -0.1282 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=active_infection | 10/23 | 49/99 | 2 | 8 | -0.0602 | -0.141 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=anticoagulant_use | 1/23 | 6/99 | 2 | 12 | -0.0171 | -0.1383 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=bleeding_thrombosis | 4/23 | 24/99 | 2 | 12 | -0.0685 | -0.1897 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=cardiac_disease | 9/23 | 44/99 | 2 | 9 | -0.0531 | -0.144 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=compliance | 1/23 | 3/99 | 2 | 12 | 0.0132 | -0.108 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=diagnosis_confirmed | 6/23 | 20/99 | 2 | 10 | 0.0588 | -0.0422 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=effusion | 2/23 | 15/99 | 2 | 10 | -0.0646 | -0.1656 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=gi_perforation_fistula | 1/23 | 6/99 | 2 | 12 | -0.0171 | -0.1383 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=hiv | 12/23 | 45/99 | 2 | 8 | 0.0672 | -0.0136 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=hypersensitivity | 10/23 | 45/99 | 1 | 6 | -0.0198 | -0.0804 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=informed_consent | 2/23 | 7/99 | 2 | 12 | 0.0162 | -0.105 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=interacting_medication | 1/23 | 9/99 | 2 | 11 | -0.0474 | -0.1585 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=life_expectancy | 1/23 | 0/99 | 2 | 12 | 0.0435 | -0.0777 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=organ_impairment | 1/23 | 8/99 | 2 | 11 | -0.0373 | -0.1484 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=organ_transplant | 8/23 | 25/99 | 2 | 11 | 0.0953 | -0.0158 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=other_investigational | 8/23 | 33/99 | 2 | 10 | 0.0145 | -0.0865 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=other_malignancy | 11/23 | 49/99 | 2 | 9 | -0.0167 | -0.1076 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=pneumonitis_ild | 12/23 | 51/99 | 1 | 6 | 0.0066 | -0.054 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=prior_enrollment | 1/23 | 0/99 | 2 | 12 | 0.0435 | -0.0777 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=recent_surgery | 10/23 | 42/99 | 2 | 8 | 0.0105 | -0.0703 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=serious_comorbidity | 3/23 | 15/99 | 2 | 11 | -0.0211 | -0.1322 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:condition=tuberculosis | 6/23 | 25/99 | 2 | 11 | 0.0083 | -0.1028 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:extent:locally advanced | 3/23 | 6/99 | 1 | 12 | 0.0698 | -0.0514 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:extent:unresectable | 3/23 | 6/99 | 2 | 11 | 0.0698 | -0.0413 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:histology=adenocarcinoma | 1/23 | 2/99 | 2 | 12 | 0.0233 | -0.0979 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:histology=large_cell | 3/23 | 2/99 | 2 | 12 | 0.1102 | -0.011 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:histology=non_squamous | 2/23 | 3/99 | 2 | 11 | 0.0567 | -0.0545 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:histology=small_cell | 4/23 | 10/99 | 2 | 12 | 0.0729 | -0.0483 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:histology=squamous | 2/23 | 11/99 | 2 | 11 | -0.0242 | -0.1353 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:ALK inhibitor | 1/23 | 4/99 | 2 | 12 | 0.0031 | -0.1181 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:CTLA-4 | 2/23 | 3/99 | 2 | 12 | 0.0567 | -0.0646 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:PD-1 | 5/23 | 19/99 | 2 | 10 | 0.0255 | -0.0755 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:PD-L1 | 5/23 | 21/99 | 2 | 10 | 0.0053 | -0.0957 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:VEGF inhibitor | 1/23 | 0/99 | 2 | 12 | 0.0435 | -0.0777 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:chemotherapy | 6/23 | 25/99 | 0 | 10 | 0.0083 | -0.0927 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:docetaxel | 2/23 | 6/99 | 1 | 11 | 0.0264 | -0.0848 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:pemetrexed | 2/23 | 3/99 | 2 | 12 | 0.0567 | -0.0646 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:platinum | 3/23 | 8/99 | 1 | 11 | 0.0496 | -0.0615 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_agent:taxane | 2/23 | 1/99 | 2 | 12 | 0.0769 | -0.0444 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_lines=0 | 1/23 | 0/99 | 2 | 12 | 0.0435 | -0.0777 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:prior_lines=1 | 2/23 | 4/99 | 1 | 12 | 0.0466 | -0.0747 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:setting_word:adjuvant | 1/23 | 8/99 | 2 | 11 | -0.0373 | -0.1484 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:setting_word:consolidation | 1/23 | 0/99 | 2 | 12 | 0.0435 | -0.0777 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:setting_word:maintenance | 1/23 | 3/99 | 2 | 11 | 0.0132 | -0.0979 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:stage:II | 1/23 | 0/99 | 2 | 12 | 0.0435 | -0.0777 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:stage:III | 2/23 | 3/99 | 2 | 12 | 0.0567 | -0.0646 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | exclusion:stage:III\|IV | 1/23 | 0/99 | 2 | 12 | 0.0435 | -0.0777 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:biomarker:ALK=negative | 2/23 | 11/99 | 2 | 11 | -0.0242 | -0.1353 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:biomarker:ALK=positive | 3/23 | 17/99 | 3 | 11 | -0.0413 | -0.1524 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:biomarker:EGFR=negative | 4/23 | 15/99 | 2 | 9 | 0.0224 | -0.0685 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:biomarker:PD-L1=@1-49% | 1/23 | 0/99 | 3 | 12 | 0.0435 | -0.0777 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 2/23 | 2/99 | 3 | 12 | 0.0668 | -0.0545 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:biomarker:PD-L1=positive | 3/23 | 3/99 | 3 | 12 | 0.1001 | -0.0211 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=active_infection | 1/23 | 4/99 | 2 | 11 | 0.0031 | -0.108 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=anticoagulant_use | 1/23 | 2/99 | 3 | 12 | 0.0233 | -0.0979 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=cardiac_disease | 1/23 | 8/99 | 2 | 11 | -0.0373 | -0.1484 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=cns_metastases | 2/23 | 10/99 | 3 | 12 | -0.0141 | -0.1353 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=hepatitis | 1/23 | 8/99 | 3 | 12 | -0.0373 | -0.1585 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=hiv | 3/23 | 7/99 | 2 | 11 | 0.0597 | -0.0514 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=hypertension | 1/23 | 9/99 | 3 | 12 | -0.0474 | -0.1686 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=immunosuppression_steroids | 4/23 | 23/99 | 2 | 10 | -0.0584 | -0.1594 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=informed_consent | 8/23 | 35/99 | 3 | 9 | -0.0057 | -0.0966 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=organ_transplant | 1/23 | 1/99 | 3 | 12 | 0.0334 | -0.0878 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=other_investigational | 1/23 | 4/99 | 3 | 11 | 0.0031 | -0.108 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=other_malignancy | 3/23 | 4/99 | 2 | 11 | 0.09 | -0.0211 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=pregnancy_or_breastfeeding | 2/23 | 10/99 | 3 | 12 | -0.0141 | -0.1353 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=recent_radiotherapy | 7/23 | 25/99 | 3 | 10 | 0.0518 | -0.0492 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=recent_surgery | 9/23 | 34/99 | 2 | 10 | 0.0479 | -0.0531 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=sex | 3/23 | 19/99 | 3 | 10 | -0.0615 | -0.1625 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:condition=tissue_available | 3/23 | 15/99 | 3 | 11 | -0.0211 | -0.1322 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:ecog_ps=0\|1\|2 | 3/23 | 24/99 | 3 | 10 | -0.112 | -0.213 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:extent:advanced | 4/23 | 17/99 | 2 | 7 | 0.0022 | -0.0685 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:extent:locally advanced | 3/23 | 20/99 | 2 | 10 | -0.0716 | -0.1726 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:extent:recurrent | 5/23 | 23/99 | 3 | 9 | -0.0149 | -0.1058 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:extent:unresectable | 3/23 | 10/99 | 3 | 11 | 0.0294 | -0.0817 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:histology=non_squamous | 8/23 | 40/99 | 2 | 6 | -0.0562 | -0.1168 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:histology=squamous | 2/23 | 11/99 | 2 | 8 | -0.0242 | -0.105 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:lab:ALT | 6/23 | 23/99 | 2 | 10 | 0.0285 | -0.0725 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:lab:AST | 5/23 | 18/99 | 2 | 11 | 0.0356 | -0.0755 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:lab:creatinine | 3/23 | 16/99 | 3 | 12 | -0.0312 | -0.1524 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:ALK inhibitor | 2/23 | 2/99 | 3 | 12 | 0.0668 | -0.0545 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:CTLA-4 | 1/23 | 2/99 | 3 | 12 | 0.0233 | -0.0979 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:EGFR inhibitor | 1/23 | 11/99 | 3 | 11 | -0.0676 | -0.1787 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:PD-1 | 1/23 | 6/99 | 3 | 12 | -0.0171 | -0.1383 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:PD-L1 | 1/23 | 5/99 | 3 | 12 | -0.007 | -0.1282 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:chemotherapy | 6/23 | 34/99 | 2 | 7 | -0.0826 | -0.1533 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:docetaxel | 1/23 | 3/99 | 3 | 11 | 0.0132 | -0.0979 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:immune checkpoint | 2/23 | 11/99 | 3 | 11 | -0.0242 | -0.1353 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:platinum | 5/23 | 22/99 | 2 | 8 | -0.0048 | -0.0856 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_agent:radiotherapy | 4/23 | 24/99 | 3 | 9 | -0.0685 | -0.1594 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_lines=1 | 1/23 | 4/99 | 2 | 11 | 0.0031 | -0.108 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:prior_lines=1\|2\|3+ | 2/23 | 18/99 | 3 | 9 | -0.0949 | -0.1858 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:setting_word:adjuvant | 4/23 | 20/99 | 2 | 9 | -0.0281 | -0.119 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:setting_word:consolidation | 2/23 | 3/99 | 3 | 12 | 0.0567 | -0.0646 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:setting_word:neoadjuvant | 3/23 | 13/99 | 2 | 10 | -0.0009 | -0.1019 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:stage:I | 2/23 | 2/99 | 2 | 12 | 0.0668 | -0.0545 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:stage:II | 3/23 | 2/99 | 2 | 11 | 0.1102 | -0.0009 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:stage:III | 6/23 | 24/99 | 2 | 9 | 0.0184 | -0.0725 | proposed | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:stage:III\|IV | 3/23 | 15/99 | 3 | 7 | -0.0211 | -0.0918 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | inclusion:stage:I\|II\|III | 2/23 | 5/99 | 3 | 12 | 0.0365 | -0.0848 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:condition=autoimmune_disease | 2/23 | 2/99 | 3 | 12 | 0.0668 | -0.0545 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:condition=contraception | 1/23 | 1/99 | 3 | 12 | 0.0334 | -0.0878 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:condition=pregnancy_or_breastfeeding | 1/23 | 0/99 | 3 | 13 | 0.0435 | -0.0878 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:condition=recent_radiotherapy | 1/23 | 11/99 | 3 | 12 | -0.0676 | -0.1888 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:extent:locally advanced | 1/23 | 3/99 | 3 | 13 | 0.0132 | -0.1181 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:extent:recurrent | 2/23 | 2/99 | 3 | 13 | 0.0668 | -0.0646 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:prior_agent:chemotherapy | 3/23 | 14/99 | 3 | 11 | -0.011 | -0.1221 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:prior_agent:immune checkpoint | 1/23 | 3/99 | 3 | 13 | 0.0132 | -0.1181 | below_support | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:prior_agent:radiotherapy | 2/23 | 13/99 | 3 | 13 | -0.0444 | -0.1757 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:setting_word:adjuvant | 2/23 | 15/99 | 3 | 12 | -0.0646 | -0.1858 | (not listed) | unresolved |
| setting unresolved | Microtubule Inhibitor | permitted:stage:III | 1/23 | 1/99 | 3 | 13 | 0.0334 | -0.0979 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | exclusion:condition=diagnosis_confirmed | 2/7 | 24/115 | 0 | 12 | 0.077 | -0.0273 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | exclusion:extent:locally advanced | 1/7 | 8/115 | 0 | 13 | 0.0733 | -0.0398 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | exclusion:histology=non_squamous | 1/7 | 4/115 | 0 | 13 | 0.1081 | -0.005 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | exclusion:histology=small_cell | 1/7 | 13/115 | 0 | 14 | 0.0298 | -0.0919 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | exclusion:prior_agent:PD-1 | 2/7 | 22/115 | 0 | 12 | 0.0944 | -0.0099 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | exclusion:prior_agent:PD-L1 | 2/7 | 24/115 | 0 | 12 | 0.077 | -0.0273 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | exclusion:stage:III | 1/7 | 4/115 | 0 | 14 | 0.1081 | -0.0137 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:age=stated | 3/7 | 47/115 | 0 | 11 | 0.0199 | -0.0758 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:biomarker:ALK=negative | 1/7 | 12/115 | 0 | 13 | 0.0385 | -0.0745 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 1/7 | 3/115 | 1 | 14 | 0.1168 | -0.005 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:condition=active_infection | 1/7 | 4/115 | 0 | 13 | 0.1081 | -0.005 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:condition=cardiac_disease | 1/7 | 8/115 | 0 | 13 | 0.0733 | -0.0398 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:condition=compliance | 1/7 | 10/115 | 0 | 11 | 0.0559 | -0.0398 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:condition=diagnosis_confirmed | 5/7 | 89/115 | 1 | 5 | -0.0596 | -0.1031 | (not listed) | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:condition=other_malignancy | 1/7 | 6/115 | 0 | 13 | 0.0907 | -0.0224 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:condition=pulmonary_function | 1/7 | 8/115 | 1 | 14 | 0.0733 | -0.0484 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:ecog_ps=0\|1\|2 | 1/7 | 26/115 | 1 | 12 | -0.0832 | -0.1876 | (not listed) | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:prior_agent:PD-1 | 1/7 | 6/115 | 1 | 14 | 0.0907 | -0.0311 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:prior_agent:PD-L1 | 1/7 | 5/115 | 1 | 14 | 0.0994 | -0.0224 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:prior_agent:platinum | 1/7 | 26/115 | 1 | 9 | -0.0832 | -0.1615 | (not listed) | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:setting_word:neoadjuvant | 1/7 | 15/115 | 0 | 12 | 0.0124 | -0.0919 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:stage:III | 1/7 | 29/115 | 1 | 10 | -0.1093 | -0.1963 | (not listed) | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | inclusion:stage:I\|II\|III | 1/7 | 6/115 | 1 | 14 | 0.0907 | -0.0311 | below_support | unresolved |
| setting unresolved | Nucleoside Metabolic Inhibitor | permitted:prior_agent:chemotherapy | 1/7 | 16/115 | 1 | 13 | 0.0037 | -0.1093 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:biomarker:BRAF=positive | 2/38 | 3/84 | 2 | 11 | 0.0169 | -0.114 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:biomarker:EGFR=negative | 2/38 | 0/84 | 2 | 12 | 0.0526 | -0.0902 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:biomarker:EGFR=positive | 11/38 | 24/84 | 1 | 9 | 0.0038 | -0.1034 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:biomarker:ROS1=positive | 3/38 | 4/84 | 2 | 11 | 0.0313 | -0.0996 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=anticoagulant_use | 1/38 | 6/84 | 2 | 12 | -0.0451 | -0.188 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=bleeding_thrombosis | 8/38 | 20/84 | 2 | 12 | -0.0276 | -0.1704 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=cardiac_disease | 16/38 | 37/84 | 1 | 10 | -0.0194 | -0.1385 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=compliance | 1/38 | 3/84 | 2 | 12 | -0.0094 | -0.1523 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=contraception | 2/38 | 3/84 | 2 | 12 | 0.0169 | -0.1259 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=diagnosis_confirmed | 11/38 | 15/84 | 2 | 10 | 0.1109 | -0.0081 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=effusion | 5/38 | 12/84 | 1 | 11 | -0.0113 | -0.1422 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=gi_perforation_fistula | 1/38 | 6/84 | 2 | 12 | -0.0451 | -0.188 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=hepatitis | 17/38 | 36/84 | 2 | 8 | 0.0188 | -0.0764 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=life_expectancy | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=live_vaccine | 12/38 | 21/84 | 1 | 10 | 0.0658 | -0.0533 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=measurable_disease | 1/38 | 6/84 | 2 | 12 | -0.0451 | -0.188 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=organ_transplant | 11/38 | 22/84 | 2 | 11 | 0.0276 | -0.1034 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=other_investigational | 14/38 | 27/84 | 1 | 11 | 0.047 | -0.084 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=pneumonitis_ild | 20/38 | 43/84 | 1 | 6 | 0.0144 | -0.057 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=prior_enrollment | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=tuberculosis | 10/38 | 21/84 | 2 | 11 | 0.0132 | -0.1178 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=unresolved_toxicity | 5/38 | 15/84 | 2 | 11 | -0.047 | -0.1779 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:condition=vitamin_premedication | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:extent:advanced | 1/38 | 3/84 | 1 | 12 | -0.0094 | -0.1523 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:extent:unresectable | 2/38 | 7/84 | 2 | 11 | -0.0307 | -0.1617 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:histology=adenocarcinoma | 1/38 | 2/84 | 2 | 12 | 0.0025 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:histology=large_cell | 3/38 | 2/84 | 2 | 12 | 0.0551 | -0.0877 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:histology=non_squamous | 1/38 | 4/84 | 2 | 11 | -0.0213 | -0.1523 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:histology=small_cell | 6/38 | 8/84 | 2 | 12 | 0.0627 | -0.0802 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:histology=squamous | 6/38 | 7/84 | 2 | 11 | 0.0746 | -0.0564 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:lab:creatinine clearance | 1/38 | 2/84 | 2 | 12 | 0.0025 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:ALK inhibitor | 1/38 | 4/84 | 2 | 12 | -0.0213 | -0.1642 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:CTLA-4 | 3/38 | 2/84 | 2 | 12 | 0.0551 | -0.0877 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:EGFR inhibitor | 5/38 | 5/84 | 2 | 12 | 0.0721 | -0.0708 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:PD-1 | 10/38 | 14/84 | 1 | 11 | 0.0965 | -0.0345 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:VEGF inhibitor | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:chemotherapy | 10/38 | 21/84 | 1 | 9 | 0.0132 | -0.094 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:pemetrexed | 4/38 | 1/84 | 2 | 12 | 0.0934 | -0.0495 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:platinum | 5/38 | 6/84 | 2 | 10 | 0.0602 | -0.0589 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_agent:taxane | 2/38 | 1/84 | 2 | 12 | 0.0407 | -0.1021 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_lines=0 | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_lines=1 | 1/38 | 5/84 | 2 | 11 | -0.0332 | -0.1642 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:prior_lines=1\|2\|3+ | 1/38 | 4/84 | 2 | 11 | -0.0213 | -0.1523 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:resection:resected | 1/38 | 1/84 | 2 | 12 | 0.0144 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:setting_word:adjuvant | 3/38 | 6/84 | 1 | 12 | 0.0075 | -0.1353 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:setting_word:consolidation | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:setting_word:neoadjuvant | 1/38 | 4/84 | 1 | 11 | -0.0213 | -0.1523 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:stage:I | 1/38 | 2/84 | 2 | 12 | 0.0025 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:stage:II | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:stage:III | 1/38 | 4/84 | 2 | 12 | -0.0213 | -0.1642 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:stage:III\|IV | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:stage:II\|III | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | exclusion:stage:I\|III | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:age=stated | 18/38 | 32/84 | 1 | 10 | 0.0927 | -0.0263 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:ALK=negative | 6/38 | 7/84 | 2 | 11 | 0.0746 | -0.0564 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:ALK=unknown | 1/38 | 0/84 | 3 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:EGFR=unknown | 1/38 | 1/84 | 3 | 11 | 0.0144 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:KRAS=positive | 2/38 | 3/84 | 3 | 12 | 0.0169 | -0.1259 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:MET=positive | 1/38 | 2/84 | 3 | 12 | 0.0025 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:PD-L1=@1-49% | 1/38 | 0/84 | 3 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:PD-L1=@<50% | 1/38 | 0/84 | 2 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:PD-L1=@>=1% | 1/38 | 0/84 | 3 | 12 | 0.0263 | -0.1165 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:PD-L1=negative\|positive | 2/38 | 2/84 | 3 | 12 | 0.0288 | -0.114 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:PD-L1=positive | 2/38 | 4/84 | 3 | 12 | 0.005 | -0.1378 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:biomarker:ROS1=negative | 4/38 | 3/84 | 3 | 11 | 0.0695 | -0.0614 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=active_infection | 2/38 | 3/84 | 2 | 11 | 0.0169 | -0.114 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=anticoagulant_use | 3/38 | 0/84 | 3 | 12 | 0.0789 | -0.0639 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=bleeding_thrombosis | 1/38 | 4/84 | 3 | 12 | -0.0213 | -0.1642 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=cardiac_disease | 3/38 | 6/84 | 2 | 11 | 0.0075 | -0.1234 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=cns_metastases | 6/38 | 6/84 | 3 | 12 | 0.0865 | -0.0564 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=compliance | 4/38 | 7/84 | 1 | 10 | 0.0219 | -0.0971 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=diagnosis_confirmed | 30/38 | 64/84 | 2 | 4 | 0.0276 | -0.0201 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=gi_perforation_fistula | 2/38 | 2/84 | 3 | 12 | 0.0288 | -0.114 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=hepatitis | 3/38 | 6/84 | 3 | 12 | 0.0075 | -0.1353 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=hiv | 5/38 | 5/84 | 2 | 11 | 0.0721 | -0.0589 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=hypersensitivity | 1/38 | 1/84 | 3 | 12 | 0.0144 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=hypertension | 4/38 | 6/84 | 3 | 12 | 0.0338 | -0.109 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=interacting_medication | 1/38 | 2/84 | 3 | 12 | 0.0025 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=investigator_judgment | 2/38 | 8/84 | 3 | 12 | -0.0426 | -0.1855 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=malabsorption | 1/38 | 7/84 | 3 | 12 | -0.057 | -0.1999 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=measurable_disease | 22/38 | 44/84 | 1 | 6 | 0.0551 | -0.0163 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=organ_transplant | 1/38 | 1/84 | 3 | 12 | 0.0144 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=other_investigational | 1/38 | 4/84 | 2 | 12 | -0.0213 | -0.1642 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=other_malignancy | 5/38 | 2/84 | 2 | 11 | 0.1078 | -0.0232 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=pneumonitis_ild | 5/38 | 4/84 | 3 | 12 | 0.084 | -0.0589 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=pregnancy_or_breastfeeding | 3/38 | 9/84 | 3 | 12 | -0.0282 | -0.1711 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=pulmonary_function | 5/38 | 4/84 | 3 | 12 | 0.084 | -0.0589 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=qtc | 1/38 | 3/84 | 3 | 12 | -0.0094 | -0.1523 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=recent_radiotherapy | 10/38 | 22/84 | 3 | 10 | 0.0013 | -0.1178 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=recent_surgery | 13/38 | 30/84 | 2 | 10 | -0.015 | -0.1341 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=sex | 5/38 | 17/84 | 3 | 10 | -0.0708 | -0.1898 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=tissue_available | 5/38 | 13/84 | 3 | 11 | -0.0232 | -0.1541 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:condition=unresolved_toxicity | 2/38 | 11/84 | 3 | 10 | -0.0783 | -0.1974 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:extent:unresectable | 5/38 | 8/84 | 3 | 11 | 0.0363 | -0.0946 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:histology=adenocarcinoma | 2/38 | 2/84 | 3 | 11 | 0.0288 | -0.1021 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:histology=squamous | 3/38 | 10/84 | 2 | 8 | -0.0401 | -0.1353 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:lab:ALT | 9/38 | 20/84 | 2 | 10 | -0.0013 | -0.1203 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:lab:AST | 8/38 | 15/84 | 2 | 11 | 0.032 | -0.099 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:lab:bilirubin | 11/38 | 18/84 | 2 | 11 | 0.0752 | -0.0558 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:lab:creatinine | 6/38 | 13/84 | 3 | 12 | 0.0031 | -0.1397 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:lab:hemoglobin | 10/38 | 17/84 | 2 | 11 | 0.0608 | -0.0702 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:lab:neutrophils | 11/38 | 20/84 | 2 | 10 | 0.0514 | -0.0677 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:lab:platelets | 11/38 | 21/84 | 2 | 10 | 0.0395 | -0.0796 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_agent:ALK inhibitor | 2/38 | 2/84 | 3 | 12 | 0.0288 | -0.114 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_agent:CTLA-4 | 1/38 | 2/84 | 3 | 12 | 0.0025 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_agent:EGFR inhibitor | 5/38 | 7/84 | 3 | 11 | 0.0482 | -0.0827 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_agent:PD-1 | 1/38 | 6/84 | 3 | 12 | -0.0451 | -0.188 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_agent:PD-L1 | 1/38 | 5/84 | 3 | 12 | -0.0332 | -0.1761 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_agent:immune checkpoint | 4/38 | 9/84 | 3 | 11 | -0.0019 | -0.1328 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_agent:pemetrexed | 1/38 | 4/84 | 3 | 11 | -0.0213 | -0.1523 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_lines=0 | 8/38 | 13/84 | 2 | 11 | 0.0558 | -0.0752 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:prior_lines=1 | 1/38 | 4/84 | 3 | 10 | -0.0213 | -0.1404 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:resection:resectable | 6/38 | 3/84 | 3 | 11 | 0.1222 | -0.0088 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:resection:resected | 6/38 | 9/84 | 2 | 11 | 0.0508 | -0.0802 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:setting_word:adjuvant | 8/38 | 16/84 | 1 | 10 | 0.0201 | -0.099 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:setting_word:consolidation | 2/38 | 3/84 | 3 | 12 | 0.0169 | -0.1259 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:setting_word:neoadjuvant | 6/38 | 10/84 | 1 | 11 | 0.0388 | -0.0921 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:stage:I | 2/38 | 2/84 | 2 | 12 | 0.0288 | -0.114 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:stage:II | 3/38 | 2/84 | 2 | 11 | 0.0551 | -0.0758 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:stage:III | 8/38 | 22/84 | 3 | 8 | -0.0514 | -0.1466 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:stage:II\|III | 7/38 | 7/84 | 2 | 11 | 0.1009 | -0.0301 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:stage:IV | 9/38 | 25/84 | 3 | 10 | -0.0608 | -0.1798 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | inclusion:stage:I\|II\|III | 2/38 | 5/84 | 3 | 12 | -0.0069 | -0.1497 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | permitted:biomarker:EGFR=negative | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:biomarker:EGFR=positive | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:condition=autoimmune_disease | 2/38 | 2/84 | 3 | 12 | 0.0288 | -0.114 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:condition=contraception | 1/38 | 1/84 | 3 | 12 | 0.0144 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:condition=measurable_disease | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:condition=pneumonitis_ild | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:condition=pregnancy_or_breastfeeding | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:condition=recent_radiotherapy | 3/38 | 9/84 | 3 | 12 | -0.0282 | -0.1711 | (not listed) | unresolved |
| setting unresolved | Platinum-based Drug | permitted:extent:locally advanced | 2/38 | 2/84 | 3 | 13 | 0.0288 | -0.1259 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:extent:metastatic | 4/38 | 4/84 | 3 | 12 | 0.0576 | -0.0852 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:extent:recurrent | 4/38 | 0/84 | 3 | 13 | 0.1053 | -0.0495 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:prior_agent:EGFR inhibitor | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:prior_agent:chemotherapy | 7/38 | 10/84 | 3 | 11 | 0.0652 | -0.0658 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | permitted:prior_agent:immune checkpoint | 2/38 | 2/84 | 3 | 13 | 0.0288 | -0.1259 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:prior_agent:radiotherapy | 7/38 | 8/84 | 3 | 13 | 0.089 | -0.0658 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | permitted:prior_lines=1\|2 | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:setting_word:adjuvant | 7/38 | 10/84 | 3 | 12 | 0.0652 | -0.0777 | proposed | unresolved |
| setting unresolved | Platinum-based Drug | permitted:setting_word:neoadjuvant | 4/38 | 8/84 | 3 | 12 | 0.01 | -0.1328 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:stage:III | 2/38 | 0/84 | 3 | 13 | 0.0526 | -0.1021 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | permitted:stage:IV | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:age=stated | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:biomarker:ALK=positive | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:biomarker:BRAF=negative | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:biomarker:EGFR=positive | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:biomarker:MET=negative | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:biomarker:NTRK=negative | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:biomarker:RET=negative | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:biomarker:ROS1=positive | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:condition=active_infection | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:condition=cns_metastases | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:condition=diagnosis_confirmed | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:condition=hepatitis | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:condition=immunosuppression_steroids | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:condition=other_malignancy | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:condition=pneumonitis_ild | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:condition=tissue_available | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:ecog_ps=0\|1 | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:extent:metastatic | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:histology=small_cell | 1/38 | 1/84 | 3 | 13 | 0.0144 | -0.1404 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:stage:III | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Platinum-based Drug | unsectioned:stage:IV | 1/38 | 0/84 | 3 | 13 | 0.0263 | -0.1284 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:biomarker:ALK=positive | 3/11 | 27/111 | 1 | 8 | 0.0295 | -0.0426 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:biomarker:ALK=unknown | 1/11 | 0/111 | 1 | 12 | 0.0909 | -0.0172 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:biomarker:EGFR=unknown | 1/11 | 0/111 | 1 | 12 | 0.0909 | -0.0172 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:biomarker:PD-L1=unknown | 1/11 | 0/111 | 2 | 12 | 0.0909 | -0.0172 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=bleeding_thrombosis | 1/11 | 27/111 | 2 | 12 | -0.1523 | -0.2604 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=cardiac_disease | 3/11 | 50/111 | 2 | 9 | -0.1777 | -0.2588 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=effusion | 1/11 | 16/111 | 2 | 10 | -0.0532 | -0.1433 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=hiv | 5/11 | 52/111 | 2 | 8 | -0.0139 | -0.086 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=hypersensitivity | 5/11 | 50/111 | 0 | 7 | 0.0041 | -0.059 | proposed | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=hypertension | 3/11 | 24/111 | 2 | 11 | 0.0565 | -0.0426 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=live_vaccine | 3/11 | 30/111 | 2 | 9 | 0.0025 | -0.0786 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=measurable_disease | 1/11 | 6/111 | 2 | 12 | 0.0369 | -0.0713 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=other_investigational | 2/11 | 39/111 | 2 | 10 | -0.1695 | -0.2596 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=other_malignancy | 4/11 | 56/111 | 2 | 9 | -0.1409 | -0.2219 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:condition=recent_surgery | 5/11 | 47/111 | 1 | 9 | 0.0311 | -0.05 | proposed | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:extent:locally advanced | 1/11 | 8/111 | 2 | 11 | 0.0188 | -0.0803 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:extent:recurrent | 2/11 | 23/111 | 2 | 11 | -0.0254 | -0.1245 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:histology=non_squamous | 1/11 | 4/111 | 1 | 12 | 0.0549 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:histology=small_cell | 1/11 | 13/111 | 2 | 12 | -0.0262 | -0.1343 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:histology=squamous | 1/11 | 12/111 | 1 | 12 | -0.0172 | -0.1253 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:chemotherapy | 2/11 | 29/111 | 2 | 8 | -0.0794 | -0.1515 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:immune checkpoint | 2/11 | 21/111 | 1 | 11 | -0.0074 | -0.1065 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:pemetrexed | 1/11 | 4/111 | 2 | 12 | 0.0549 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:prior_agent:taxane | 1/11 | 2/111 | 2 | 12 | 0.0729 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:setting_word:adjuvant | 1/11 | 8/111 | 2 | 11 | 0.0188 | -0.0803 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:setting_word:neoadjuvant | 1/11 | 4/111 | 2 | 10 | 0.0549 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:stage:III | 1/11 | 4/111 | 2 | 12 | 0.0549 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | exclusion:stage:III\|IV | 1/11 | 0/111 | 2 | 12 | 0.0909 | -0.0172 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:age=stated | 5/11 | 45/111 | 2 | 9 | 0.0491 | -0.0319 | proposed | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:biomarker:ALK=positive | 1/11 | 19/111 | 2 | 12 | -0.0803 | -0.1884 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:biomarker:EGFR=unknown | 1/11 | 1/111 | 1 | 13 | 0.0819 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:biomarker:PD-L1=negative\|positive | 1/11 | 3/111 | 2 | 13 | 0.0639 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:biomarker:PD-L1=positive | 1/11 | 5/111 | 2 | 13 | 0.0459 | -0.0713 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:condition=contraception | 5/11 | 55/111 | 1 | 12 | -0.041 | -0.1491 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:condition=investigator_judgment | 1/11 | 9/111 | 2 | 13 | 0.0098 | -0.1073 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:condition=life_expectancy | 5/11 | 43/111 | 1 | 11 | 0.0672 | -0.0319 | proposed | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:condition=other_malignancy | 1/11 | 6/111 | 2 | 11 | 0.0369 | -0.0622 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:condition=recent_surgery | 3/11 | 40/111 | 2 | 10 | -0.0876 | -0.1777 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:condition=sex | 2/11 | 20/111 | 0 | 13 | 0.0016 | -0.1155 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:ecog_ps=0\|1\|2 | 1/11 | 26/111 | 2 | 11 | -0.1433 | -0.2424 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:extent:recurrent | 3/11 | 25/111 | 1 | 11 | 0.0475 | -0.0516 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:histology=small_cell | 1/11 | 3/111 | 2 | 13 | 0.0639 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:lab:ALT | 2/11 | 27/111 | 1 | 11 | -0.0614 | -0.1605 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:lab:AST | 1/11 | 22/111 | 2 | 11 | -0.1073 | -0.2064 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:lab:bilirubin | 1/11 | 28/111 | 2 | 11 | -0.1613 | -0.2604 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:lab:creatinine clearance | 3/11 | 22/111 | 1 | 11 | 0.0745 | -0.0246 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:lab:hemoglobin | 2/11 | 25/111 | 1 | 12 | -0.0434 | -0.1515 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:lab:leukocytes | 1/11 | 3/111 | 1 | 13 | 0.0639 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:lab:neutrophils | 2/11 | 29/111 | 1 | 11 | -0.0794 | -0.1785 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:lab:platelets | 2/11 | 30/111 | 1 | 11 | -0.0885 | -0.1876 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:organ_function_unspecified=adequate | 3/11 | 31/111 | 2 | 10 | -0.0066 | -0.0966 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:prior_agent:immune checkpoint | 1/11 | 12/111 | 2 | 12 | -0.0172 | -0.1253 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:prior_lines=0 | 2/11 | 19/111 | 2 | 11 | 0.0106 | -0.0885 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:resection:resected | 1/11 | 14/111 | 2 | 11 | -0.0352 | -0.1343 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:setting_word:adjuvant | 2/11 | 22/111 | 1 | 10 | -0.0164 | -0.1065 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:setting_word:neoadjuvant | 2/11 | 14/111 | 1 | 11 | 0.0557 | -0.0434 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:stage:II | 1/11 | 4/111 | 2 | 11 | 0.0549 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:stage:III\|IV | 1/11 | 17/111 | 1 | 9 | -0.0622 | -0.1433 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:stage:II\|III | 1/11 | 13/111 | 2 | 11 | -0.0262 | -0.1253 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | inclusion:stage:I\|II\|III | 1/11 | 6/111 | 2 | 13 | 0.0369 | -0.0803 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | permitted:condition=recent_radiotherapy | 1/11 | 11/111 | 2 | 13 | -0.0082 | -0.1253 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | permitted:extent:recurrent | 1/11 | 3/111 | 2 | 14 | 0.0639 | -0.0622 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | permitted:prior_agent:chemotherapy | 1/11 | 16/111 | 2 | 12 | -0.0532 | -0.1613 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | permitted:prior_agent:radiotherapy | 1/11 | 14/111 | 2 | 14 | -0.0352 | -0.1613 | (not listed) | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | permitted:setting_word:maintenance | 1/11 | 1/111 | 1 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:age=stated | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:ALK=positive | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:BRAF=negative | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:EGFR=positive | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:MET=negative | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:NTRK=negative | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:RET=negative | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:biomarker:ROS1=positive | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:condition=active_infection | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:condition=cns_metastases | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:condition=diagnosis_confirmed | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:condition=hepatitis | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:condition=immunosuppression_steroids | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:condition=other_malignancy | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:condition=pneumonitis_ild | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:condition=tissue_available | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:ecog_ps=0\|1 | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:extent:metastatic | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:histology=small_cell | 1/11 | 1/111 | 2 | 14 | 0.0819 | -0.0442 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:stage:III | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Ligand-1 Blocker | unsectioned:stage:IV | 1/11 | 0/111 | 2 | 14 | 0.0909 | -0.0352 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:BRAF=positive | 2/55 | 3/67 | 8 | 5 | -0.0084 | -0.083 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:EGFR=positive | 18/55 | 17/67 | 5 | 5 | 0.0735 | -0.0011 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:PD-L1=negative | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:PD-L1=negative\|unknown | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:biomarker:ROS1=positive | 4/55 | 3/67 | 8 | 5 | 0.028 | -0.0467 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=anticoagulant_use | 1/55 | 6/67 | 8 | 6 | -0.0714 | -0.1609 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=bleeding_thrombosis | 10/55 | 18/67 | 8 | 6 | -0.0868 | -0.1764 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=cardiac_disease | 22/55 | 31/67 | 6 | 5 | -0.0627 | -0.1373 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=contraception | 3/55 | 2/67 | 8 | 6 | 0.0247 | -0.0649 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=diagnosis_confirmed | 8/55 | 18/67 | 7 | 5 | -0.1232 | -0.1978 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=effusion | 8/55 | 9/67 | 6 | 6 | 0.0111 | -0.0784 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=gi_perforation_fistula | 2/55 | 5/67 | 8 | 6 | -0.0383 | -0.1278 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=informed_consent | 2/55 | 7/67 | 8 | 6 | -0.0681 | -0.1577 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=interacting_medication | 2/55 | 8/67 | 7 | 6 | -0.083 | -0.1726 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=investigator_judgment | 9/55 | 11/67 | 6 | 4 | -0.0005 | -0.0602 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=malabsorption | 2/55 | 11/67 | 8 | 6 | -0.1278 | -0.2174 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=measurable_disease | 2/55 | 5/67 | 8 | 6 | -0.0383 | -0.1278 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=organ_impairment | 3/55 | 6/67 | 8 | 5 | -0.035 | -0.1096 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=other_malignancy | 29/55 | 31/67 | 5 | 6 | 0.0646 | -0.025 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=pregnancy_or_breastfeeding | 36/55 | 41/67 | 6 | 5 | 0.0426 | -0.032 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=pulmonary_function | 1/55 | 1/67 | 7 | 6 | 0.0033 | -0.0863 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=qtc | 6/55 | 9/67 | 6 | 6 | -0.0252 | -0.1148 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=recent_radiotherapy | 25/55 | 30/67 | 6 | 6 | 0.0068 | -0.0828 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=serious_comorbidity | 6/55 | 12/67 | 7 | 6 | -0.07 | -0.1596 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:condition=substance_or_psychiatric | 8/55 | 17/67 | 6 | 5 | -0.1083 | -0.1829 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:advanced | 2/55 | 2/67 | 7 | 6 | 0.0065 | -0.083 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:locally advanced | 2/55 | 7/67 | 8 | 5 | -0.0681 | -0.1427 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:metastatic | 13/55 | 14/67 | 5 | 4 | 0.0274 | -0.0323 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:recurrent | 13/55 | 12/67 | 8 | 5 | 0.0573 | -0.0174 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:extent:unresectable | 3/55 | 6/67 | 8 | 5 | -0.035 | -0.1096 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=adenocarcinoma | 2/55 | 1/67 | 8 | 6 | 0.0214 | -0.0681 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=large_cell | 4/55 | 1/67 | 8 | 6 | 0.0578 | -0.0318 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=non_squamous | 2/55 | 3/67 | 8 | 5 | -0.0084 | -0.083 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=small_cell | 5/55 | 9/67 | 8 | 6 | -0.0434 | -0.133 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:histology=squamous | 3/55 | 10/67 | 8 | 5 | -0.0947 | -0.1693 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:lab:creatinine clearance | 1/55 | 2/67 | 8 | 6 | -0.0117 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:lab:hemoglobin | 1/55 | 3/67 | 8 | 6 | -0.0266 | -0.1161 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:ALK inhibitor | 2/55 | 3/67 | 8 | 6 | -0.0084 | -0.098 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:CTLA-4 | 4/55 | 1/67 | 8 | 6 | 0.0578 | -0.0318 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:EGFR inhibitor | 3/55 | 7/67 | 8 | 6 | -0.0499 | -0.1395 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:VEGF inhibitor | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:chemotherapy | 14/55 | 17/67 | 5 | 5 | 0.0008 | -0.0738 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:docetaxel | 5/55 | 3/67 | 7 | 5 | 0.0461 | -0.0285 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:immune checkpoint | 12/55 | 11/67 | 7 | 5 | 0.054 | -0.0206 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:pemetrexed | 3/55 | 2/67 | 8 | 6 | 0.0247 | -0.0649 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:platinum | 4/55 | 7/67 | 8 | 4 | -0.0318 | -0.0915 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:radiotherapy | 21/55 | 22/67 | 6 | 6 | 0.0535 | -0.0361 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_agent:taxane | 2/55 | 1/67 | 8 | 6 | 0.0214 | -0.0681 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_lines=0 | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_lines=1 | 2/55 | 4/67 | 8 | 5 | -0.0233 | -0.098 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:prior_lines=1\|2\|3+ | 1/55 | 4/67 | 8 | 5 | -0.0415 | -0.1161 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:resection:resected | 1/55 | 1/67 | 8 | 6 | 0.0033 | -0.0863 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:setting_word:adjuvant | 6/55 | 3/67 | 7 | 6 | 0.0643 | -0.0252 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:setting_word:consolidation | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:setting_word:maintenance | 1/55 | 3/67 | 8 | 5 | -0.0266 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:setting_word:neoadjuvant | 2/55 | 3/67 | 7 | 5 | -0.0084 | -0.083 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:stage:I | 1/55 | 2/67 | 8 | 6 | -0.0117 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:stage:III | 1/55 | 4/67 | 8 | 6 | -0.0415 | -0.1311 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | exclusion:stage:IV | 2/55 | 2/67 | 8 | 6 | 0.0065 | -0.083 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:age=stated | 21/55 | 29/67 | 5 | 6 | -0.051 | -0.1406 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ALK=negative\|positive | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ALK=positive | 7/55 | 13/67 | 9 | 5 | -0.0668 | -0.1414 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ALK=unknown | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:BRAF=negative | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:BRAF=positive | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:EGFR=negative\|positive | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:EGFR=unknown | 1/55 | 1/67 | 9 | 5 | 0.0033 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:HER2=positive | 1/55 | 2/67 | 9 | 6 | -0.0117 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:MET=negative | 1/55 | 1/67 | 9 | 5 | 0.0033 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:MET=positive | 1/55 | 2/67 | 9 | 6 | -0.0117 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:NTRK=negative | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:NTRK=positive | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@1-49% | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@<1% | 1/55 | 1/67 | 8 | 6 | 0.0033 | -0.0863 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@<50% | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@>=1% | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@≥1% | 2/55 | 0/67 | 9 | 6 | 0.0364 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=@≥50% | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=negative\|positive | 3/55 | 1/67 | 9 | 6 | 0.0396 | -0.0499 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=positive | 5/55 | 1/67 | 9 | 6 | 0.076 | -0.0136 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:PD-L1=positive@≥50% | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:RET=negative | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:RET=positive | 2/55 | 3/67 | 9 | 6 | -0.0084 | -0.098 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:biomarker:ROS1=positive | 3/55 | 4/67 | 9 | 6 | -0.0052 | -0.0947 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=active_infection | 3/55 | 2/67 | 7 | 6 | 0.0247 | -0.0649 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=anticoagulant_use | 1/55 | 2/67 | 9 | 6 | -0.0117 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=bleeding_thrombosis | 1/55 | 4/67 | 9 | 6 | -0.0415 | -0.1311 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=cardiac_disease | 5/55 | 4/67 | 7 | 6 | 0.0312 | -0.0583 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=cns_metastases | 5/55 | 7/67 | 9 | 6 | -0.0136 | -0.1031 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=compliance | 7/55 | 4/67 | 5 | 6 | 0.0676 | -0.022 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=contraception | 29/55 | 31/67 | 8 | 5 | 0.0646 | -0.01 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=gi_perforation_fistula | 4/55 | 0/67 | 9 | 6 | 0.0727 | -0.0168 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=hepatitis | 5/55 | 4/67 | 9 | 6 | 0.0312 | -0.0583 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=hiv | 6/55 | 4/67 | 7 | 6 | 0.0494 | -0.0402 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=hypertension | 5/55 | 5/67 | 9 | 6 | 0.0163 | -0.0733 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=immunosuppression_steroids | 14/55 | 13/67 | 7 | 5 | 0.0605 | -0.0141 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=investigator_judgment | 5/55 | 5/67 | 9 | 6 | 0.0163 | -0.0733 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=life_expectancy | 19/55 | 29/67 | 8 | 4 | -0.0874 | -0.1471 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=malabsorption | 2/55 | 6/67 | 9 | 6 | -0.0532 | -0.1427 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=neurologic_disorder | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=organ_transplant | 2/55 | 0/67 | 9 | 6 | 0.0364 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=other_investigational | 4/55 | 1/67 | 8 | 6 | 0.0578 | -0.0318 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=other_malignancy | 4/55 | 3/67 | 7 | 6 | 0.028 | -0.0616 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=pregnancy_or_breastfeeding | 4/55 | 8/67 | 9 | 6 | -0.0467 | -0.1362 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=pulmonary_function | 6/55 | 3/67 | 9 | 6 | 0.0643 | -0.0252 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=recent_radiotherapy | 14/55 | 18/67 | 7 | 6 | -0.0141 | -0.1037 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=recent_surgery | 17/55 | 26/67 | 7 | 5 | -0.079 | -0.1536 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=serious_comorbidity | 1/55 | 0/67 | 9 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=substance_or_psychiatric | 1/55 | 1/67 | 9 | 6 | 0.0033 | -0.0863 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=tissue_available | 10/55 | 8/67 | 8 | 6 | 0.0624 | -0.0271 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:condition=unresolved_toxicity | 2/55 | 11/67 | 9 | 4 | -0.1278 | -0.1875 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:ecog_ps=0\|1\|2 | 10/55 | 17/67 | 7 | 6 | -0.0719 | -0.1615 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:ecog_ps=1 | 1/55 | 0/67 | 8 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:extent:advanced | 8/55 | 13/67 | 6 | 3 | -0.0486 | -0.0934 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:extent:unresectable | 4/55 | 9/67 | 9 | 5 | -0.0616 | -0.1362 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:histology=adenocarcinoma | 3/55 | 1/67 | 8 | 6 | 0.0396 | -0.0499 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:histology=non_squamous | 20/55 | 28/67 | 3 | 5 | -0.0543 | -0.1289 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:histology=small_cell | 1/55 | 3/67 | 9 | 6 | -0.0266 | -0.1161 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:ALT | 11/55 | 18/67 | 7 | 5 | -0.0687 | -0.1433 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:AST | 9/55 | 14/67 | 7 | 6 | -0.0453 | -0.1349 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:bilirubin | 11/55 | 18/67 | 7 | 6 | -0.0687 | -0.1582 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:creatinine | 6/55 | 13/67 | 9 | 6 | -0.0849 | -0.1745 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:creatinine clearance | 10/55 | 15/67 | 7 | 5 | -0.0421 | -0.1167 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:hemoglobin | 9/55 | 18/67 | 8 | 5 | -0.105 | -0.1796 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:leukocytes | 2/55 | 2/67 | 9 | 5 | 0.0065 | -0.0681 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:neutrophils | 11/55 | 20/67 | 7 | 5 | -0.0985 | -0.1731 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:lab:platelets | 11/55 | 21/67 | 7 | 5 | -0.1134 | -0.1881 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:ALK inhibitor | 2/55 | 2/67 | 9 | 6 | 0.0065 | -0.083 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:CTLA-4 | 1/55 | 2/67 | 9 | 6 | -0.0117 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:EGFR inhibitor | 3/55 | 9/67 | 9 | 5 | -0.0798 | -0.1544 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:PD-1 | 5/55 | 2/67 | 9 | 6 | 0.0611 | -0.0285 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:PD-L1 | 4/55 | 2/67 | 9 | 6 | 0.0429 | -0.0467 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:chemotherapy | 18/55 | 22/67 | 8 | 1 | -0.0011 | -0.016 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:docetaxel | 2/55 | 2/67 | 9 | 5 | 0.0065 | -0.0681 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:pemetrexed | 1/55 | 4/67 | 9 | 5 | -0.0415 | -0.1161 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:platinum | 10/55 | 17/67 | 8 | 2 | -0.0719 | -0.1018 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_agent:radiotherapy | 11/55 | 17/67 | 7 | 5 | -0.0537 | -0.1284 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_lines=0 | 12/55 | 9/67 | 7 | 6 | 0.0839 | -0.0057 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_lines=1 | 2/55 | 3/67 | 9 | 4 | -0.0084 | -0.0681 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_lines=1\|2\|3+ | 7/55 | 13/67 | 7 | 5 | -0.0668 | -0.1414 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:prior_lines=2 | 2/55 | 2/67 | 8 | 6 | 0.0065 | -0.083 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:resection:resectable | 4/55 | 5/67 | 9 | 5 | -0.0019 | -0.0765 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:resection:resected | 7/55 | 8/67 | 8 | 5 | 0.0079 | -0.0668 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:setting_word:adjuvant | 10/55 | 14/67 | 6 | 5 | -0.0271 | -0.1018 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:setting_word:consolidation | 1/55 | 4/67 | 9 | 6 | -0.0415 | -0.1311 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:setting_word:maintenance | 1/55 | 2/67 | 9 | 6 | -0.0117 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:setting_word:neoadjuvant | 7/55 | 9/67 | 7 | 5 | -0.0071 | -0.0817 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:I | 3/55 | 1/67 | 8 | 6 | 0.0396 | -0.0499 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:II | 1/55 | 4/67 | 8 | 5 | -0.0415 | -0.1161 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:III\|IV | 7/55 | 11/67 | 6 | 4 | -0.0369 | -0.0966 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:II\|III | 7/55 | 7/67 | 8 | 5 | 0.0228 | -0.0518 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:I\|II | 2/55 | 2/67 | 9 | 6 | 0.0065 | -0.083 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | inclusion:stage:I\|II\|III | 3/55 | 4/67 | 9 | 6 | -0.0052 | -0.0947 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:biomarker:EGFR=positive | 1/55 | 0/67 | 10 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=autoimmune_disease | 4/55 | 0/67 | 9 | 6 | 0.0727 | -0.0168 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=contraception | 1/55 | 1/67 | 9 | 6 | 0.0033 | -0.0863 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=immunosuppression_steroids | 3/55 | 1/67 | 9 | 6 | 0.0396 | -0.0499 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=live_vaccine | 1/55 | 0/67 | 10 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=measurable_disease | 1/55 | 0/67 | 10 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:condition=recent_radiotherapy | 4/55 | 8/67 | 10 | 5 | -0.0467 | -0.1213 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:extent:advanced | 2/55 | 1/67 | 9 | 6 | 0.0214 | -0.0681 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:extent:locally advanced | 3/55 | 1/67 | 10 | 6 | 0.0396 | -0.0499 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:extent:metastatic | 5/55 | 3/67 | 9 | 6 | 0.0461 | -0.0434 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:extent:recurrent | 3/55 | 1/67 | 10 | 6 | 0.0396 | -0.0499 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:EGFR inhibitor | 1/55 | 0/67 | 10 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:VEGF inhibitor | 1/55 | 1/67 | 9 | 6 | 0.0033 | -0.0863 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:chemotherapy | 10/55 | 7/67 | 8 | 6 | 0.0773 | -0.0122 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:immune checkpoint | 2/55 | 2/67 | 10 | 6 | 0.0065 | -0.083 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_agent:radiotherapy | 7/55 | 8/67 | 10 | 6 | 0.0079 | -0.0817 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_lines=0 | 1/55 | 1/67 | 10 | 6 | 0.0033 | -0.0863 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_lines=1 | 1/55 | 2/67 | 9 | 6 | -0.0117 | -0.1012 | (not listed) | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:prior_lines=1\|2 | 1/55 | 0/67 | 10 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:setting_word:adjuvant | 9/55 | 8/67 | 9 | 6 | 0.0442 | -0.0453 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:setting_word:maintenance | 1/55 | 1/67 | 10 | 5 | 0.0033 | -0.0714 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:setting_word:neoadjuvant | 8/55 | 4/67 | 9 | 6 | 0.0858 | -0.0038 | proposed | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:stage:III | 2/55 | 0/67 | 10 | 6 | 0.0364 | -0.0532 | below_support | unresolved |
| setting unresolved | Programmed Death Receptor-1 Blocking Antibody | permitted:stage:IV | 1/55 | 0/67 | 10 | 6 | 0.0182 | -0.0714 | below_support | unresolved |
| setting unresolved | Topoisomerase Inhibitor | inclusion:biomarker:EGFR=positive | 1/3 | 36/119 | 0 | 12 | 0.0308 | -0.07 | below_support | unresolved |
| setting unresolved | Topoisomerase Inhibitor | inclusion:condition=recent_radiotherapy | 1/3 | 31/119 | 0 | 13 | 0.0728 | -0.0364 | below_support | unresolved |
| setting unresolved | Topoisomerase Inhibitor | inclusion:ecog_ps=0\|1 | 2/3 | 76/119 | 0 | 6 | 0.028 | -0.0224 | below_support | unresolved |
| setting unresolved | Topoisomerase Inhibitor | inclusion:stage:III | 1/3 | 29/119 | 0 | 11 | 0.0896 | -0.0028 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:biomarker:ALK=positive | 2/8 | 28/114 | 0 | 9 | 0.0044 | -0.0746 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=active_infection | 4/8 | 55/114 | 0 | 10 | 0.0175 | -0.0702 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=cns_metastases | 4/8 | 54/114 | 0 | 5 | 0.0263 | -0.0175 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=diagnosis_confirmed | 2/8 | 24/114 | 0 | 12 | 0.0395 | -0.0658 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=hiv | 4/8 | 53/114 | 0 | 10 | 0.0351 | -0.0526 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=hypertension | 2/8 | 25/114 | 0 | 13 | 0.0307 | -0.0833 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=informed_consent | 1/8 | 8/114 | 0 | 14 | 0.0548 | -0.068 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=interacting_medication | 1/8 | 9/114 | 0 | 13 | 0.0461 | -0.068 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=measurable_disease | 1/8 | 6/114 | 0 | 14 | 0.0724 | -0.0504 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=other_malignancy | 4/8 | 56/114 | 0 | 11 | 0.0088 | -0.0877 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=qtc | 1/8 | 14/114 | 0 | 12 | 0.0022 | -0.1031 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:condition=substance_or_psychiatric | 2/8 | 23/114 | 0 | 11 | 0.0482 | -0.0482 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:extent:metastatic | 2/8 | 25/114 | 0 | 9 | 0.0307 | -0.0482 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:extent:recurrent | 2/8 | 23/114 | 0 | 13 | 0.0482 | -0.0658 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:lab:ALT | 1/8 | 1/114 | 0 | 14 | 0.1162 | -0.0066 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:lab:AST | 1/8 | 1/114 | 0 | 14 | 0.1162 | -0.0066 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:lab:creatinine | 1/8 | 1/114 | 0 | 14 | 0.1162 | -0.0066 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:CTLA-4 | 1/8 | 4/114 | 0 | 14 | 0.0899 | -0.0329 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:PD-1 | 2/8 | 22/114 | 0 | 12 | 0.057 | -0.0482 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:pemetrexed | 1/8 | 4/114 | 0 | 14 | 0.0899 | -0.0329 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:platinum | 1/8 | 10/114 | 0 | 12 | 0.0373 | -0.068 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_agent:taxane | 1/8 | 2/114 | 0 | 14 | 0.1075 | -0.0154 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | exclusion:prior_lines=1\|2\|3+ | 1/8 | 4/114 | 0 | 13 | 0.0899 | -0.0241 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:biomarker:EGFR=positive | 3/8 | 34/114 | 0 | 12 | 0.0768 | -0.0285 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:biomarker:PD-L1=negative\|positive | 1/8 | 3/114 | 0 | 15 | 0.0987 | -0.0329 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:biomarker:PD-L1=positive | 1/8 | 5/114 | 0 | 15 | 0.0811 | -0.0504 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=anticoagulant_use | 1/8 | 2/114 | 0 | 15 | 0.1075 | -0.0241 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=bleeding_thrombosis | 1/8 | 4/114 | 0 | 15 | 0.0899 | -0.0417 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=cardiac_disease | 1/8 | 8/114 | 0 | 13 | 0.0548 | -0.0592 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=cns_metastases | 1/8 | 11/114 | 0 | 15 | 0.0285 | -0.1031 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=compliance | 1/8 | 10/114 | 0 | 11 | 0.0373 | -0.0592 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=hepatitis | 1/8 | 8/114 | 0 | 15 | 0.0548 | -0.0768 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=hiv | 1/8 | 9/114 | 0 | 13 | 0.0461 | -0.068 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=interacting_medication | 1/8 | 2/114 | 0 | 15 | 0.1075 | -0.0241 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=investigator_judgment | 1/8 | 9/114 | 0 | 15 | 0.0461 | -0.0855 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=malabsorption | 1/8 | 7/114 | 0 | 15 | 0.0636 | -0.068 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=other_malignancy | 1/8 | 6/114 | 0 | 13 | 0.0724 | -0.0417 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=qtc | 1/8 | 3/114 | 0 | 15 | 0.0987 | -0.0329 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=recent_surgery | 3/8 | 40/114 | 0 | 12 | 0.0241 | -0.0811 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:condition=unresolved_toxicity | 1/8 | 12/114 | 0 | 13 | 0.0197 | -0.0943 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:ecog_ps=0\|1\|2 | 2/8 | 25/114 | 0 | 13 | 0.0307 | -0.0833 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:extent:unresectable | 1/8 | 12/114 | 0 | 14 | 0.0197 | -0.1031 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:lab:AST | 2/8 | 21/114 | 0 | 13 | 0.0658 | -0.0482 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:lab:creatinine clearance | 2/8 | 23/114 | 0 | 12 | 0.0482 | -0.057 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:lab:leukocytes | 1/8 | 3/114 | 0 | 14 | 0.0987 | -0.0241 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:prior_agent:ALK inhibitor | 1/8 | 3/114 | 0 | 15 | 0.0987 | -0.0329 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:prior_agent:VEGF inhibitor | 1/8 | 1/114 | 0 | 15 | 0.1162 | -0.0154 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:prior_lines=1\|2\|3+ | 2/8 | 18/114 | 0 | 12 | 0.0921 | -0.0132 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:prior_lines=2 | 1/8 | 3/114 | 0 | 14 | 0.0987 | -0.0241 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:stage:III | 2/8 | 28/114 | 0 | 11 | 0.0044 | -0.0921 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:stage:IV | 3/8 | 31/114 | 0 | 13 | 0.1031 | -0.011 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | inclusion:stage:I\|II\|III | 1/8 | 6/114 | 0 | 15 | 0.0724 | -0.0592 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | permitted:condition=recent_radiotherapy | 1/8 | 11/114 | 0 | 15 | 0.0285 | -0.1031 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | permitted:extent:advanced | 1/8 | 2/114 | 0 | 15 | 0.1075 | -0.0241 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | permitted:prior_agent:radiotherapy | 2/8 | 13/114 | 0 | 16 | 0.136 | -0.0044 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | permitted:setting_word:adjuvant | 2/8 | 15/114 | 0 | 15 | 0.1184 | -0.0132 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Inhibitor | permitted:setting_word:neoadjuvant | 1/8 | 11/114 | 0 | 15 | 0.0285 | -0.1031 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Receptor 2 Antagonist | exclusion:condition=cns_metastases | 1/2 | 57/120 | 0 | 5 | 0.025 | -0.0167 | below_support | unresolved |
| setting unresolved | Vascular Endothelial Growth Factor Receptor 2 Antagonist | inclusion:age=stated | 1/2 | 49/120 | 0 | 11 | 0.0917 | 0.0 | below_support | unresolved |
| setting unresolved | Vinca Alkaloid | exclusion:condition=active_infection | 1/2 | 58/120 | 0 | 10 | 0.0167 | -0.0667 | below_support | unresolved |
| setting unresolved | Vinca Alkaloid | exclusion:condition=cardiac_disease | 1/2 | 52/120 | 0 | 11 | 0.0667 | -0.025 | below_support | unresolved |
| setting unresolved | Vinca Alkaloid | exclusion:condition=hepatitis | 1/2 | 52/120 | 0 | 10 | 0.0667 | -0.0167 | below_support | unresolved |
| setting unresolved | Vinca Alkaloid | exclusion:condition=hiv | 1/2 | 56/120 | 0 | 10 | 0.0333 | -0.05 | below_support | unresolved |
| setting unresolved | Vinca Alkaloid | exclusion:condition=hypersensitivity | 1/2 | 54/120 | 0 | 7 | 0.05 | -0.0083 | below_support | unresolved |
| setting unresolved | Vinca Alkaloid | exclusion:condition=recent_radiotherapy | 1/2 | 54/120 | 0 | 12 | 0.05 | -0.05 | below_support | unresolved |
| setting unresolved | Vinca Alkaloid | exclusion:condition=recent_surgery | 1/2 | 51/120 | 0 | 10 | 0.075 | -0.0083 | below_support | unresolved |
| setting unresolved | Vinca Alkaloid | inclusion:age=stated | 1/2 | 49/120 | 0 | 11 | 0.0917 | 0.0 | below_support | unresolved |

### D. Every profile row: old value, new rate, new bounds, and the tier decision

Old: trials stating / trials typed = frequency, tier. New: S / N = statement rate; for an eligibility element the full-criteria interval and U as no rule match + abbreviated + unspecified (no eligibility text was empty), and the tier; for a primary endpoint the statement rate only, no interval, tier "". Every eligibility row's tier changed from "" (not standard) to unresolved, for one reason: its lower bound is below 0.9 and its upper bound is 1.0, because its silent trials are unresolved (A = 0 by construction), except the one row marked met, which was standard and is met. Every primary-endpoint row keeps tier "".

| Stratum | Element | Old S/typed | Old freq | Old tier | New S/N | Rate | Bounds | U (no rule match + abbr + unsp) | New tier |
|---|---|---|---|---|---|---|---|---|---|
| advanced_first_line | inclusion:prior_lines=0 | 79/82 | 0.9634 | standard | 79/82 | 0.9634 | [0.9634, 1.0] | 3 (0 + 0 + 3) | met |
| advanced_first_line | inclusion:extent:metastatic | 72/82 | 0.878 | (not standard) | 72/82 | 0.878 | [0.878, 1.0] | 10 (0 + 0 + 10) | unresolved |
| advanced_first_line | inclusion:condition=diagnosis_confirmed | 71/82 | 0.8659 | (not standard) | 71/82 | 0.8659 | [0.8659, 1.0] | 11 (0 + 5 + 6) | unresolved |
| advanced_first_line | inclusion:condition=measurable_disease | 70/82 | 0.8537 | (not standard) | 70/82 | 0.8537 | [0.8537, 1.0] | 12 (0 + 0 + 12) | unresolved |
| advanced_first_line | inclusion:ecog_ps=0\|1 | 70/82 | 0.8537 | (not standard) | 70/82 | 0.8537 | [0.8537, 1.0] | 12 (0 + 3 + 9) | unresolved |
| advanced_first_line | exclusion:condition=cns_metastases | 61/82 | 0.7439 | (not standard) | 61/82 | 0.7439 | [0.7439, 1.0] | 21 (0 + 3 + 18) | unresolved |
| advanced_first_line | primary:endpoint:progression_free_survival | 58/82 | 0.7073 | (not standard) | 58/82 | 0.7073 | (statement rate only) |  | "" |
| advanced_first_line | inclusion:condition=life_expectancy | 52/82 | 0.6341 | (not standard) | 52/82 | 0.6341 | [0.6341, 1.0] | 30 (0 + 5 + 25) | unresolved |
| advanced_first_line | exclusion:condition=recent_surgery | 50/82 | 0.6098 | (not standard) | 50/82 | 0.6098 | [0.6098, 1.0] | 32 (0 + 8 + 24) | unresolved |
| advanced_first_line | exclusion:condition=immunosuppression_steroids | 47/82 | 0.5732 | (not standard) | 47/82 | 0.5732 | [0.5732, 1.0] | 35 (0 + 6 + 29) | unresolved |
| advanced_first_line | exclusion:condition=pneumonitis_ild | 46/82 | 0.561 | (not standard) | 46/82 | 0.561 | [0.561, 1.0] | 36 (0 + 5 + 31) | unresolved |
| advanced_first_line | exclusion:condition=recent_radiotherapy | 46/82 | 0.561 | (not standard) | 46/82 | 0.561 | [0.561, 1.0] | 36 (0 + 9 + 27) | unresolved |
| advanced_first_line | inclusion:stage:IV | 46/82 | 0.561 | (not standard) | 46/82 | 0.561 | [0.561, 1.0] | 36 (0 + 7 + 29) | unresolved |
| advanced_first_line | exclusion:condition=autoimmune_disease | 45/82 | 0.5488 | (not standard) | 45/82 | 0.5488 | [0.5488, 1.0] | 37 (0 + 4 + 33) | unresolved |
| advanced_first_line | exclusion:condition=hepatitis | 44/82 | 0.5366 | (not standard) | 44/82 | 0.5366 | [0.5366, 1.0] | 38 (0 + 8 + 30) | unresolved |
| advanced_first_line | exclusion:condition=hypersensitivity | 44/82 | 0.5366 | (not standard) | 44/82 | 0.5366 | [0.5366, 1.0] | 38 (0 + 7 + 31) | unresolved |
| advanced_first_line | exclusion:condition=other_malignancy | 44/82 | 0.5366 | (not standard) | 44/82 | 0.5366 | [0.5366, 1.0] | 38 (0 + 10 + 28) | unresolved |
| advanced_first_line | exclusion:condition=pregnancy_or_breastfeeding | 43/82 | 0.5244 | (not standard) | 43/82 | 0.5244 | [0.5244, 1.0] | 39 (0 + 11 + 28) | unresolved |
| advanced_first_line | exclusion:condition=active_infection | 42/82 | 0.5122 | (not standard) | 42/82 | 0.5122 | [0.5122, 1.0] | 40 (0 + 11 + 29) | unresolved |
| advanced_first_line | inclusion:age=stated | 42/82 | 0.5122 | (not standard) | 42/82 | 0.5122 | [0.5122, 1.0] | 40 (0 + 9 + 31) | unresolved |
| advanced_first_line | inclusion:condition=contraception | 42/82 | 0.5122 | (not standard) | 42/82 | 0.5122 | [0.5122, 1.0] | 40 (0 + 9 + 31) | unresolved |
| advanced_first_line | exclusion:condition=hiv | 39/82 | 0.4756 | (not standard) | 39/82 | 0.4756 | [0.4756, 1.0] | 43 (0 + 9 + 34) | unresolved |
| advanced_first_line | inclusion:histology=non_squamous | 38/82 | 0.4634 | (not standard) | 38/82 | 0.4634 | [0.4634, 1.0] | 44 (0 + 5 + 39) | unresolved |
| advanced_first_line | inclusion:condition=informed_consent | 36/82 | 0.439 | (not standard) | 36/82 | 0.439 | [0.439, 1.0] | 46 (0 + 12 + 34) | unresolved |
| advanced_first_line | inclusion:extent:locally advanced | 35/82 | 0.4268 | (not standard) | 35/82 | 0.4268 | [0.4268, 1.0] | 47 (0 + 10 + 37) | unresolved |
| advanced_first_line | primary:endpoint:overall_survival | 33/82 | 0.4024 | (not standard) | 33/82 | 0.4024 | (statement rate only) |  | "" |
| advanced_first_line | exclusion:condition=cardiac_disease | 30/82 | 0.3659 | (not standard) | 30/82 | 0.3659 | [0.3659, 1.0] | 52 (0 + 14 + 38) | unresolved |
| advanced_first_line | exclusion:condition=other_investigational | 29/82 | 0.3537 | (not standard) | 29/82 | 0.3537 | [0.3537, 1.0] | 53 (0 + 12 + 41) | unresolved |
| advanced_first_line | exclusion:prior_agent:radiotherapy | 29/82 | 0.3537 | (not standard) | 29/82 | 0.3537 | [0.3537, 1.0] | 53 (0 + 13 + 40) | unresolved |
| advanced_first_line | exclusion:condition=diagnosis_confirmed | 28/82 | 0.3415 | (not standard) | 28/82 | 0.3415 | [0.3415, 1.0] | 54 (0 + 12 + 42) | unresolved |
| advanced_first_line | inclusion:extent:recurrent | 28/82 | 0.3415 | (not standard) | 28/82 | 0.3415 | [0.3415, 1.0] | 54 (0 + 8 + 46) | unresolved |
| advanced_first_line | inclusion:extent:advanced | 27/82 | 0.3293 | (not standard) | 27/82 | 0.3293 | [0.3293, 1.0] | 55 (0 + 10 + 45) | unresolved |
| advanced_first_line | inclusion:organ_function_unspecified=adequate | 27/82 | 0.3293 | (not standard) | 27/82 | 0.3293 | [0.3293, 1.0] | 55 (0 + 8 + 47) | unresolved |
| advanced_first_line | exclusion:condition=bleeding_thrombosis | 26/82 | 0.3171 | (not standard) | 26/82 | 0.3171 | [0.3171, 1.0] | 56 (0 + 14 + 42) | unresolved |
| advanced_first_line | exclusion:condition=neurologic_disorder | 25/82 | 0.3049 | (not standard) | 25/82 | 0.3049 | [0.3049, 1.0] | 57 (0 + 7 + 50) | unresolved |
| advanced_first_line | inclusion:biomarker:EGFR=positive | 25/82 | 0.3049 | (not standard) | 25/82 | 0.3049 | [0.3049, 1.0] | 57 (0 + 13 + 44) | unresolved |
| advanced_first_line | exclusion:biomarker:ALK=positive | 23/82 | 0.2805 | (not standard) | 23/82 | 0.2805 | [0.2805, 1.0] | 59 (0 + 6 + 53) | unresolved |
| advanced_first_line | exclusion:prior_agent:chemotherapy | 23/82 | 0.2805 | (not standard) | 23/82 | 0.2805 | [0.2805, 1.0] | 59 (0 + 14 + 45) | unresolved |
| advanced_first_line | inclusion:histology=squamous | 23/82 | 0.2805 | (not standard) | 23/82 | 0.2805 | [0.2805, 1.0] | 59 (0 + 7 + 52) | unresolved |
| advanced_first_line | exclusion:biomarker:EGFR=positive | 22/82 | 0.2683 | (not standard) | 22/82 | 0.2683 | [0.2683, 1.0] | 60 (0 + 6 + 54) | unresolved |
| advanced_first_line | exclusion:condition=unresolved_toxicity | 22/82 | 0.2683 | (not standard) | 22/82 | 0.2683 | [0.2683, 1.0] | 60 (0 + 13 + 47) | unresolved |
| advanced_first_line | exclusion:extent:metastatic | 22/82 | 0.2683 | (not standard) | 22/82 | 0.2683 | [0.2683, 1.0] | 60 (0 + 13 + 47) | unresolved |
| advanced_first_line | exclusion:prior_agent:immune checkpoint | 22/82 | 0.2683 | (not standard) | 22/82 | 0.2683 | [0.2683, 1.0] | 60 (0 + 14 + 46) | unresolved |
| advanced_first_line | inclusion:condition=recent_radiotherapy | 22/82 | 0.2683 | (not standard) | 22/82 | 0.2683 | [0.2683, 1.0] | 60 (0 + 9 + 51) | unresolved |
| advanced_first_line | inclusion:condition=sex | 22/82 | 0.2683 | (not standard) | 22/82 | 0.2683 | [0.2683, 1.0] | 60 (0 + 13 + 47) | unresolved |
| advanced_first_line | inclusion:stage:III | 22/82 | 0.2683 | (not standard) | 22/82 | 0.2683 | [0.2683, 1.0] | 60 (0 + 10 + 50) | unresolved |
| advanced_first_line | exclusion:condition=live_vaccine | 21/82 | 0.2561 | (not standard) | 21/82 | 0.2561 | [0.2561, 1.0] | 61 (0 + 13 + 48) | unresolved |
| advanced_first_line | exclusion:condition=hypertension | 18/82 | 0.2195 | (not standard) | 18/82 | 0.2195 | [0.2195, 1.0] | 64 (0 + 15 + 49) | unresolved |
| advanced_first_line | exclusion:condition=qtc | 17/82 | 0.2073 | (not standard) | 17/82 | 0.2073 | [0.2073, 1.0] | 65 (0 + 15 + 50) | unresolved |
| advanced_first_line | exclusion:histology=squamous | 17/82 | 0.2073 | (not standard) | 17/82 | 0.2073 | [0.2073, 1.0] | 65 (0 + 15 + 50) | unresolved |
| advanced_first_line | exclusion:condition=effusion | 16/82 | 0.1951 | (not standard) | 16/82 | 0.1951 | [0.1951, 1.0] | 66 (0 + 14 + 52) | unresolved |
| advanced_first_line | exclusion:condition=interacting_medication | 16/82 | 0.1951 | (not standard) | 16/82 | 0.1951 | [0.1951, 1.0] | 66 (0 + 14 + 52) | unresolved |
| advanced_first_line | exclusion:condition=investigator_judgment | 16/82 | 0.1951 | (not standard) | 16/82 | 0.1951 | [0.1951, 1.0] | 66 (0 + 13 + 53) | unresolved |
| advanced_first_line | exclusion:condition=organ_transplant | 16/82 | 0.1951 | (not standard) | 16/82 | 0.1951 | [0.1951, 1.0] | 66 (0 + 13 + 53) | unresolved |
| advanced_first_line | exclusion:histology=small_cell | 16/82 | 0.1951 | (not standard) | 16/82 | 0.1951 | [0.1951, 1.0] | 66 (0 + 14 + 52) | unresolved |
| advanced_first_line | exclusion:prior_agent:PD-1 | 16/82 | 0.1951 | (not standard) | 16/82 | 0.1951 | [0.1951, 1.0] | 66 (0 + 13 + 53) | unresolved |
| advanced_first_line | exclusion:prior_agent:PD-L1 | 16/82 | 0.1951 | (not standard) | 16/82 | 0.1951 | [0.1951, 1.0] | 66 (0 + 13 + 53) | unresolved |
| advanced_first_line | inclusion:biomarker:EGFR=negative | 16/82 | 0.1951 | (not standard) | 16/82 | 0.1951 | [0.1951, 1.0] | 66 (0 + 14 + 52) | unresolved |
| advanced_first_line | exclusion:biomarker:ROS1=positive | 15/82 | 0.1829 | (not standard) | 15/82 | 0.1829 | [0.1829, 1.0] | 67 (0 + 9 + 58) | unresolved |
| advanced_first_line | exclusion:extent:recurrent | 15/82 | 0.1829 | (not standard) | 15/82 | 0.1829 | [0.1829, 1.0] | 67 (0 + 14 + 53) | unresolved |
| advanced_first_line | exclusion:prior_agent:EGFR inhibitor | 15/82 | 0.1829 | (not standard) | 15/82 | 0.1829 | [0.1829, 1.0] | 67 (0 + 14 + 53) | unresolved |
| advanced_first_line | inclusion:condition=immunosuppression_steroids | 15/82 | 0.1829 | (not standard) | 15/82 | 0.1829 | [0.1829, 1.0] | 67 (0 + 14 + 53) | unresolved |
| advanced_first_line | exclusion:condition=malabsorption | 14/82 | 0.1707 | (not standard) | 14/82 | 0.1707 | [0.1707, 1.0] | 68 (0 + 15 + 53) | unresolved |
| advanced_first_line | inclusion:biomarker:ALK=negative | 14/82 | 0.1707 | (not standard) | 14/82 | 0.1707 | [0.1707, 1.0] | 68 (0 + 14 + 54) | unresolved |
| advanced_first_line | inclusion:condition=recent_surgery | 14/82 | 0.1707 | (not standard) | 14/82 | 0.1707 | [0.1707, 1.0] | 68 (0 + 13 + 55) | unresolved |
| advanced_first_line | inclusion:prior_agent:radiotherapy | 14/82 | 0.1707 | (not standard) | 14/82 | 0.1707 | [0.1707, 1.0] | 68 (0 + 10 + 58) | unresolved |
| advanced_first_line | exclusion:condition=substance_or_psychiatric | 13/82 | 0.1585 | (not standard) | 13/82 | 0.1585 | [0.1585, 1.0] | 69 (0 + 15 + 54) | unresolved |
| advanced_first_line | inclusion:condition=tissue_available | 13/82 | 0.1585 | (not standard) | 13/82 | 0.1585 | [0.1585, 1.0] | 69 (0 + 13 + 56) | unresolved |
| advanced_first_line | inclusion:extent:unresectable | 13/82 | 0.1585 | (not standard) | 13/82 | 0.1585 | [0.1585, 1.0] | 69 (0 + 13 + 56) | unresolved |
| advanced_first_line | permitted:setting_word:adjuvant | 13/82 | 0.1585 | (not standard) | 13/82 | 0.1585 | [0.1585, 1.0] | 69 (0 + 15 + 54) | unresolved |
| advanced_first_line | inclusion:condition=pregnancy_or_breastfeeding | 11/82 | 0.1341 | (not standard) | 11/82 | 0.1341 | [0.1341, 1.0] | 71 (0 + 15 + 56) | unresolved |
| advanced_first_line | inclusion:lab:bilirubin | 11/82 | 0.1341 | (not standard) | 11/82 | 0.1341 | [0.1341, 1.0] | 71 (0 + 15 + 56) | unresolved |
| advanced_first_line | inclusion:lab:neutrophils | 11/82 | 0.1341 | (not standard) | 11/82 | 0.1341 | [0.1341, 1.0] | 71 (0 + 15 + 56) | unresolved |
| advanced_first_line | inclusion:lab:platelets | 11/82 | 0.1341 | (not standard) | 11/82 | 0.1341 | [0.1341, 1.0] | 71 (0 + 15 + 56) | unresolved |
| advanced_first_line | inclusion:stage:III\|IV | 11/82 | 0.1341 | (not standard) | 11/82 | 0.1341 | [0.1341, 1.0] | 71 (0 + 14 + 57) | unresolved |
| advanced_first_line | inclusion:lab:ALT | 10/82 | 0.122 | (not standard) | 10/82 | 0.122 | [0.122, 1.0] | 72 (0 + 15 + 57) | unresolved |
| advanced_first_line | inclusion:lab:AST | 10/82 | 0.122 | (not standard) | 10/82 | 0.122 | [0.122, 1.0] | 72 (0 + 15 + 57) | unresolved |
| advanced_first_line | inclusion:lab:hemoglobin | 10/82 | 0.122 | (not standard) | 10/82 | 0.122 | [0.122, 1.0] | 72 (0 + 15 + 57) | unresolved |
| advanced_first_line | permitted:prior_agent:radiotherapy | 10/82 | 0.122 | (not standard) | 10/82 | 0.122 | [0.122, 1.0] | 72 (0 + 16 + 56) | unresolved |
| advanced_first_line | permitted:setting_word:neoadjuvant | 10/82 | 0.122 | (not standard) | 10/82 | 0.122 | [0.122, 1.0] | 72 (0 + 16 + 56) | unresolved |
| advanced_first_line | exclusion:condition=tuberculosis | 9/82 | 0.1098 | (not standard) | 9/82 | 0.1098 | [0.1098, 1.0] | 73 (0 + 16 + 57) | unresolved |
| advanced_first_line | exclusion:prior_agent:CTLA-4 | 9/82 | 0.1098 | (not standard) | 9/82 | 0.1098 | [0.1098, 1.0] | 73 (0 + 14 + 59) | unresolved |
| advanced_first_line | exclusion:prior_agent:platinum | 9/82 | 0.1098 | (not standard) | 9/82 | 0.1098 | [0.1098, 1.0] | 73 (0 + 14 + 59) | unresolved |
| advanced_first_line | exclusion:setting_word:adjuvant | 9/82 | 0.1098 | (not standard) | 9/82 | 0.1098 | [0.1098, 1.0] | 73 (0 + 14 + 59) | unresolved |
| advanced_first_line | inclusion:lab:creatinine clearance | 9/82 | 0.1098 | (not standard) | 9/82 | 0.1098 | [0.1098, 1.0] | 73 (0 + 15 + 58) | unresolved |
| advanced_first_line | permitted:condition=recent_radiotherapy | 9/82 | 0.1098 | (not standard) | 9/82 | 0.1098 | [0.1098, 1.0] | 73 (0 + 16 + 57) | unresolved |
| advanced_first_line | primary:endpoint:objective_response_rate | 9/82 | 0.1098 | (not standard) | 9/82 | 0.1098 | (statement rate only) |  | "" |
| advanced_first_line | exclusion:extent:locally advanced | 8/82 | 0.0976 | (not standard) | 8/82 | 0.0976 | [0.0976, 1.0] | 74 (0 + 16 + 58) | unresolved |
| advanced_first_line | inclusion:prior_agent:chemotherapy | 8/82 | 0.0976 | (not standard) | 8/82 | 0.0976 | [0.0976, 1.0] | 74 (0 + 14 + 60) | unresolved |
| advanced_first_line | exclusion:condition=compliance | 7/82 | 0.0854 | (not standard) | 7/82 | 0.0854 | [0.0854, 1.0] | 75 (0 + 14 + 61) | unresolved |
| advanced_first_line | permitted:prior_agent:chemotherapy | 7/82 | 0.0854 | (not standard) | 7/82 | 0.0854 | [0.0854, 1.0] | 75 (0 + 16 + 59) | unresolved |
| advanced_first_line | exclusion:condition=gi_perforation_fistula | 6/82 | 0.0732 | (not standard) | 6/82 | 0.0732 | [0.0732, 1.0] | 76 (0 + 15 + 61) | unresolved |
| advanced_first_line | exclusion:condition=informed_consent | 6/82 | 0.0732 | (not standard) | 6/82 | 0.0732 | [0.0732, 1.0] | 76 (0 + 15 + 61) | unresolved |
| advanced_first_line | exclusion:histology=non_squamous | 6/82 | 0.0732 | (not standard) | 6/82 | 0.0732 | [0.0732, 1.0] | 76 (0 + 16 + 60) | unresolved |
| advanced_first_line | exclusion:setting_word:neoadjuvant | 6/82 | 0.0732 | (not standard) | 6/82 | 0.0732 | [0.0732, 1.0] | 76 (0 + 14 + 62) | unresolved |
| advanced_first_line | inclusion:biomarker:ALK=positive | 6/82 | 0.0732 | (not standard) | 6/82 | 0.0732 | [0.0732, 1.0] | 76 (0 + 14 + 62) | unresolved |
| advanced_first_line | inclusion:lab:creatinine | 6/82 | 0.0732 | (not standard) | 6/82 | 0.0732 | [0.0732, 1.0] | 76 (0 + 15 + 61) | unresolved |
| advanced_first_line | exclusion:condition=serious_comorbidity | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 15 + 62) | unresolved |
| advanced_first_line | exclusion:condition=smoking | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 12 + 65) | unresolved |
| advanced_first_line | exclusion:lab:AST | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 16 + 61) | unresolved |
| advanced_first_line | exclusion:lab:bilirubin | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 16 + 61) | unresolved |
| advanced_first_line | exclusion:lab:hemoglobin | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 16 + 61) | unresolved |
| advanced_first_line | exclusion:lab:platelets | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 16 + 61) | unresolved |
| advanced_first_line | exclusion:prior_lines=1\|2\|3+ | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 16 + 61) | unresolved |
| advanced_first_line | inclusion:biomarker:PD-L1=negative\|positive | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 13 + 64) | unresolved |
| advanced_first_line | inclusion:biomarker:ROS1=negative | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 14 + 63) | unresolved |
| advanced_first_line | inclusion:condition=compliance | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 15 + 62) | unresolved |
| advanced_first_line | inclusion:condition=unresolved_toxicity | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 15 + 62) | unresolved |
| advanced_first_line | inclusion:condition=vitamin_premedication | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 14 + 63) | unresolved |
| advanced_first_line | inclusion:ecog_ps=0\|1\|2 | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 15 + 62) | unresolved |
| advanced_first_line | inclusion:histology=adenocarcinoma | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 15 + 62) | unresolved |
| advanced_first_line | permitted:condition=immunosuppression_steroids | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 14 + 63) | unresolved |
| advanced_first_line | permitted:condition=other_investigational | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | [0.061, 1.0] | 77 (0 + 16 + 61) | unresolved |
| advanced_first_line | primary:endpoint:safety | 5/82 | 0.061 | (not standard) | 5/82 | 0.061 | (statement rate only) |  | "" |
| advanced_first_line | exclusion:biomarker:BRAF=positive | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 15 + 63) | unresolved |
| advanced_first_line | exclusion:condition=anticoagulant_use | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 16 + 62) | unresolved |
| advanced_first_line | exclusion:condition=organ_impairment | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 14 + 64) | unresolved |
| advanced_first_line | exclusion:extent:advanced | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 16 + 62) | unresolved |
| advanced_first_line | exclusion:lab:ALT | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 16 + 62) | unresolved |
| advanced_first_line | exclusion:lab:creatinine | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 16 + 62) | unresolved |
| advanced_first_line | exclusion:lab:creatinine clearance | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 16 + 62) | unresolved |
| advanced_first_line | exclusion:lab:neutrophils | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 16 + 62) | unresolved |
| advanced_first_line | inclusion:biomarker:PD-L1=@≥50% | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 12 + 66) | unresolved |
| advanced_first_line | inclusion:condition=cns_metastases | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 14 + 64) | unresolved |
| advanced_first_line | inclusion:condition=other_malignancy | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 15 + 63) | unresolved |
| advanced_first_line | inclusion:condition=pneumonitis_ild | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 15 + 63) | unresolved |
| advanced_first_line | permitted:condition=autoimmune_disease | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 14 + 64) | unresolved |
| advanced_first_line | permitted:extent:recurrent | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | [0.0488, 1.0] | 78 (0 + 16 + 62) | unresolved |
| advanced_first_line | primary:endpoint:pharmacokinetics | 4/82 | 0.0488 | (not standard) | 4/82 | 0.0488 | (statement rate only) |  | "" |
| advanced_first_line | exclusion:biomarker:MET=positive | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 16 + 63) | unresolved |
| advanced_first_line | exclusion:biomarker:NTRK=positive | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 16 + 63) | unresolved |
| advanced_first_line | exclusion:biomarker:RET=positive | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 16 + 63) | unresolved |
| advanced_first_line | exclusion:histology=adenocarcinoma | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 16 + 63) | unresolved |
| advanced_first_line | inclusion:biomarker:HER2=positive | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 14 + 65) | unresolved |
| advanced_first_line | inclusion:biomarker:PD-L1=@<1% | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 15 + 64) | unresolved |
| advanced_first_line | inclusion:biomarker:PD-L1=@≥1% | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 15 + 64) | unresolved |
| advanced_first_line | inclusion:condition=effusion | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 15 + 64) | unresolved |
| advanced_first_line | inclusion:condition=other_investigational | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 15 + 64) | unresolved |
| advanced_first_line | inclusion:prior_agent:EGFR inhibitor | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 15 + 64) | unresolved |
| advanced_first_line | inclusion:prior_lines=1\|2\|3+ | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 15 + 64) | unresolved |
| advanced_first_line | permitted:condition=cns_metastases | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | [0.0366, 1.0] | 79 (0 + 15 + 64) | unresolved |
| advanced_first_line | primary:endpoint:biomarker_endpoint | 3/82 | 0.0366 | (not standard) | 3/82 | 0.0366 | (statement rate only) |  | "" |
| advanced_first_line | exclusion:age=stated | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 16 + 64) | unresolved |
| advanced_first_line | exclusion:prior_agent:ALK inhibitor | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 14 + 66) | unresolved |
| advanced_first_line | exclusion:prior_agent:MET inhibitor | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 16 + 64) | unresolved |
| advanced_first_line | exclusion:prior_agent:VEGF inhibitor | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 16 + 64) | unresolved |
| advanced_first_line | exclusion:prior_agent:pemetrexed | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 16 + 64) | unresolved |
| advanced_first_line | exclusion:prior_lines=0 | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 16 + 64) | unresolved |
| advanced_first_line | inclusion:biomarker:ALK=unknown | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | inclusion:biomarker:BRAF=negative | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 14 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:EGFR=unknown | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | inclusion:biomarker:MET=positive | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 14 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:NTRK=negative | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 14 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:NTRK=positive | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 14 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:PD-L1=positive | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | inclusion:biomarker:RET=positive | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 14 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:ROS1=positive | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 14 + 66) | unresolved |
| advanced_first_line | inclusion:condition=active_infection | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | inclusion:condition=autoimmune_disease | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | inclusion:condition=cardiac_disease | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | inclusion:condition=pulmonary_function | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | inclusion:condition=weight_loss | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | inclusion:prior_agent:ALK inhibitor | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | permitted:extent:locally advanced | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 16 + 64) | unresolved |
| advanced_first_line | permitted:extent:metastatic | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 16 + 64) | unresolved |
| advanced_first_line | permitted:prior_agent:immune checkpoint | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | permitted:prior_agent:platinum | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 16 + 64) | unresolved |
| advanced_first_line | permitted:prior_lines=0 | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | [0.0244, 1.0] | 80 (0 + 15 + 65) | unresolved |
| advanced_first_line | primary:endpoint:quality_of_life | 2/82 | 0.0244 | (not standard) | 2/82 | 0.0244 | (statement rate only) |  | "" |
| advanced_first_line | exclusion:biomarker:BRAF=unknown | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:biomarker:HER2=positive | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:biomarker:KRAS=positive | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:biomarker:NTRK=unknown | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:biomarker:PD-L1=@≥50% | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:biomarker:RET=unknown | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:condition=contraception | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:condition=weight_loss | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:extent:unresectable | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:histology=large_cell | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | exclusion:setting_word:consolidation | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | inclusion:biomarker:BRAF=positive | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 14 + 67) | unresolved |
| advanced_first_line | inclusion:biomarker:KRAS=negative | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:KRAS=positive | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:PD-L1=@<50% | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 14 + 67) | unresolved |
| advanced_first_line | inclusion:biomarker:PD-L1=negative\|positive@0to49% | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:PD-L1=positive@≥50% | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:biomarker:RET=negative | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 14 + 67) | unresolved |
| advanced_first_line | inclusion:biomarker:ROS1=unknown | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=anticoagulant_use | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=bleeding_thrombosis | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=hepatitis | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=hiv | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=hypersensitivity | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=interacting_medication | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=investigator_judgment | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=live_vaccine | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=malabsorption | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=neurologic_disorder | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 14 + 67) | unresolved |
| advanced_first_line | inclusion:condition=qtc | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:condition=serious_comorbidity | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:ecog_ps=1 | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:lab:leukocytes | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:prior_agent:CTLA-4 | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:prior_agent:PD-1 | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:prior_agent:PD-L1 | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:prior_agent:docetaxel | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:prior_agent:platinum | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:prior_agent:taxane | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | inclusion:setting_word:consolidation | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | permitted:biomarker:BRAF=positive | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | permitted:condition=anticoagulant_use | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:condition=diagnosis_confirmed | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:condition=other_malignancy | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:condition=pneumonitis_ild | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:condition=recent_surgery | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 15 + 66) | unresolved |
| advanced_first_line | permitted:condition=unresolved_toxicity | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:extent:advanced | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:histology=adenocarcinoma | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:lab:AST | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:lab:bilirubin | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:lab:creatinine | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:lab:creatinine clearance | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:lab:hemoglobin | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:lab:neutrophils | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:lab:platelets | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:prior_agent:EGFR inhibitor | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:stage:III | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:stage:IV | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | permitted:stage:I\|II | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | [0.0122, 1.0] | 81 (0 + 16 + 65) | unresolved |
| advanced_first_line | primary:endpoint:duration_of_response | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | (statement rate only) |  | "" |
| advanced_first_line | primary:endpoint:intracranial_response | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | (statement rate only) |  | "" |
| advanced_first_line | primary:endpoint:time_to_progression | 1/82 | 0.0122 | (not standard) | 1/82 | 0.0122 | (statement rate only) |  | "" |
| all trials | inclusion:condition=diagnosis_confirmed | 380/481 | 0.79 | (not standard) | 380/487 | 0.7803 | [0.7803, 1.0] | 107 (6 + 16 + 85) | unresolved |
| all trials | inclusion:ecog_ps=0\|1 | 324/481 | 0.6736 | (not standard) | 324/487 | 0.6653 | [0.6653, 1.0] | 163 (6 + 21 + 136) | unresolved |
| all trials | inclusion:condition=measurable_disease | 289/481 | 0.6008 | (not standard) | 289/487 | 0.5934 | [0.5934, 1.0] | 198 (6 + 23 + 169) | unresolved |
| all trials | exclusion:condition=pregnancy_or_breastfeeding | 279/481 | 0.58 | (not standard) | 279/487 | 0.5729 | [0.5729, 1.0] | 208 (6 + 42 + 160) | unresolved |
| all trials | exclusion:condition=cns_metastases | 270/481 | 0.5613 | (not standard) | 270/487 | 0.5544 | [0.5544, 1.0] | 217 (6 + 22 + 189) | unresolved |
| all trials | exclusion:condition=recent_radiotherapy | 261/481 | 0.5426 | (not standard) | 261/487 | 0.5359 | [0.5359, 1.0] | 226 (6 + 33 + 187) | unresolved |
| all trials | exclusion:condition=other_malignancy | 259/481 | 0.5385 | (not standard) | 259/487 | 0.5318 | [0.5318, 1.0] | 228 (6 + 36 + 186) | unresolved |
| all trials | primary:endpoint:progression_free_survival | 244/481 | 0.5073 | (not standard) | 247/487 | 0.5072 | (statement rate only) |  | "" |
| all trials | exclusion:condition=active_infection | 239/481 | 0.4969 | (not standard) | 239/487 | 0.4908 | [0.4908, 1.0] | 248 (6 + 41 + 201) | unresolved |
| all trials | inclusion:extent:metastatic | 238/481 | 0.4948 | (not standard) | 238/487 | 0.4887 | [0.4887, 1.0] | 249 (6 + 22 + 221) | unresolved |
| all trials | inclusion:condition=life_expectancy | 237/481 | 0.4927 | (not standard) | 237/487 | 0.4867 | [0.4867, 1.0] | 250 (6 + 37 + 207) | unresolved |
| all trials | inclusion:age=stated | 232/481 | 0.4823 | (not standard) | 232/487 | 0.4764 | [0.4764, 1.0] | 255 (6 + 43 + 206) | unresolved |
| all trials | inclusion:condition=informed_consent | 232/481 | 0.4823 | (not standard) | 232/487 | 0.4764 | [0.4764, 1.0] | 255 (6 + 47 + 202) | unresolved |
| all trials | exclusion:condition=hypersensitivity | 226/481 | 0.4699 | (not standard) | 226/487 | 0.4641 | [0.4641, 1.0] | 261 (6 + 37 + 218) | unresolved |
| all trials | exclusion:condition=pneumonitis_ild | 222/481 | 0.4615 | (not standard) | 222/487 | 0.4559 | [0.4559, 1.0] | 265 (6 + 30 + 229) | unresolved |
| all trials | exclusion:condition=immunosuppression_steroids | 221/481 | 0.4595 | (not standard) | 221/487 | 0.4538 | [0.4538, 1.0] | 266 (6 + 25 + 235) | unresolved |
| all trials | inclusion:condition=contraception | 218/481 | 0.4532 | (not standard) | 218/487 | 0.4476 | [0.4476, 1.0] | 269 (6 + 46 + 217) | unresolved |
| all trials | exclusion:condition=recent_surgery | 215/481 | 0.447 | (not standard) | 215/487 | 0.4415 | [0.4415, 1.0] | 272 (6 + 37 + 229) | unresolved |
| all trials | exclusion:condition=hiv | 211/481 | 0.4387 | (not standard) | 211/487 | 0.4333 | [0.4333, 1.0] | 276 (6 + 33 + 237) | unresolved |
| all trials | exclusion:condition=hepatitis | 202/481 | 0.42 | (not standard) | 202/487 | 0.4148 | [0.4148, 1.0] | 285 (6 + 37 + 242) | unresolved |
| all trials | exclusion:condition=cardiac_disease | 200/481 | 0.4158 | (not standard) | 200/487 | 0.4107 | [0.4107, 1.0] | 287 (6 + 46 + 235) | unresolved |
| all trials | exclusion:condition=autoimmune_disease | 189/481 | 0.3929 | (not standard) | 189/487 | 0.3881 | [0.3881, 1.0] | 298 (6 + 28 + 264) | unresolved |
| all trials | exclusion:prior_agent:radiotherapy | 183/481 | 0.3805 | (not standard) | 183/487 | 0.3758 | [0.3758, 1.0] | 304 (6 + 38 + 260) | unresolved |
| all trials | inclusion:histology=non_squamous | 179/481 | 0.3721 | (not standard) | 179/487 | 0.3676 | [0.3676, 1.0] | 308 (6 + 29 + 273) | unresolved |
| all trials | exclusion:condition=other_investigational | 157/481 | 0.3264 | (not standard) | 157/487 | 0.3224 | [0.3224, 1.0] | 330 (6 + 42 + 282) | unresolved |
| all trials | inclusion:prior_lines=0 | 153/481 | 0.3181 | (not standard) | 153/487 | 0.3142 | [0.3142, 1.0] | 334 (6 + 35 + 293) | unresolved |
| all trials | primary:endpoint:overall_survival | 152/481 | 0.316 | (not standard) | 152/487 | 0.3121 | (statement rate only) |  | "" |
| all trials | exclusion:condition=bleeding_thrombosis | 150/481 | 0.3119 | (not standard) | 150/487 | 0.308 | [0.308, 1.0] | 337 (6 + 52 + 279) | unresolved |
| all trials | inclusion:prior_agent:chemotherapy | 149/481 | 0.3098 | (not standard) | 149/487 | 0.306 | [0.306, 1.0] | 338 (6 + 39 + 293) | unresolved |
| all trials | inclusion:stage:IV | 145/481 | 0.3015 | (not standard) | 145/487 | 0.2977 | [0.2977, 1.0] | 342 (6 + 41 + 295) | unresolved |
| all trials | inclusion:condition=recent_radiotherapy | 142/481 | 0.2952 | (not standard) | 142/487 | 0.2916 | [0.2916, 1.0] | 345 (6 + 45 + 294) | unresolved |
| all trials | exclusion:prior_agent:chemotherapy | 131/481 | 0.2723 | (not standard) | 131/487 | 0.269 | [0.269, 1.0] | 356 (6 + 49 + 301) | unresolved |
| all trials | inclusion:extent:locally advanced | 131/481 | 0.2723 | (not standard) | 131/487 | 0.269 | [0.269, 1.0] | 356 (6 + 43 + 307) | unresolved |
| all trials | inclusion:biomarker:EGFR=positive | 129/481 | 0.2682 | (not standard) | 129/487 | 0.2649 | [0.2649, 1.0] | 358 (6 + 48 + 304) | unresolved |
| all trials | exclusion:condition=hypertension | 124/481 | 0.2578 | (not standard) | 124/487 | 0.2546 | [0.2546, 1.0] | 363 (6 + 53 + 304) | unresolved |
| all trials | exclusion:biomarker:EGFR=positive | 119/481 | 0.2474 | (not standard) | 119/487 | 0.2444 | [0.2444, 1.0] | 368 (6 + 35 + 327) | unresolved |
| all trials | inclusion:prior_agent:radiotherapy | 119/481 | 0.2474 | (not standard) | 119/487 | 0.2444 | [0.2444, 1.0] | 368 (6 + 47 + 315) | unresolved |
| all trials | inclusion:stage:III | 119/481 | 0.2474 | (not standard) | 119/487 | 0.2444 | [0.2444, 1.0] | 368 (6 + 43 + 319) | unresolved |
| all trials | exclusion:biomarker:ALK=positive | 115/481 | 0.2391 | (not standard) | 115/487 | 0.2361 | [0.2361, 1.0] | 372 (6 + 35 + 331) | unresolved |
| all trials | exclusion:condition=diagnosis_confirmed | 115/481 | 0.2391 | (not standard) | 115/487 | 0.2361 | [0.2361, 1.0] | 372 (6 + 47 + 319) | unresolved |
| all trials | inclusion:condition=recent_surgery | 115/481 | 0.2391 | (not standard) | 115/487 | 0.2361 | [0.2361, 1.0] | 372 (6 + 47 + 319) | unresolved |
| all trials | exclusion:condition=live_vaccine | 112/481 | 0.2328 | (not standard) | 112/487 | 0.23 | [0.23, 1.0] | 375 (6 + 44 + 325) | unresolved |
| all trials | exclusion:condition=organ_transplant | 112/481 | 0.2328 | (not standard) | 112/487 | 0.23 | [0.23, 1.0] | 375 (6 + 46 + 323) | unresolved |
| all trials | inclusion:extent:recurrent | 112/481 | 0.2328 | (not standard) | 112/487 | 0.23 | [0.23, 1.0] | 375 (6 + 45 + 324) | unresolved |
| all trials | inclusion:lab:platelets | 112/481 | 0.2328 | (not standard) | 112/487 | 0.23 | [0.23, 1.0] | 375 (6 + 53 + 316) | unresolved |
| all trials | inclusion:organ_function_unspecified=adequate | 112/481 | 0.2328 | (not standard) | 112/487 | 0.23 | [0.23, 1.0] | 375 (6 + 43 + 326) | unresolved |
| all trials | inclusion:extent:advanced | 109/481 | 0.2266 | (not standard) | 109/487 | 0.2238 | [0.2238, 1.0] | 378 (6 + 42 + 330) | unresolved |
| all trials | exclusion:condition=substance_or_psychiatric | 108/481 | 0.2245 | (not standard) | 108/487 | 0.2218 | [0.2218, 1.0] | 379 (6 + 50 + 323) | unresolved |
| all trials | inclusion:condition=sex | 108/481 | 0.2245 | (not standard) | 108/487 | 0.2218 | [0.2218, 1.0] | 379 (6 + 52 + 321) | unresolved |
| all trials | inclusion:lab:neutrophils | 107/481 | 0.2225 | (not standard) | 107/487 | 0.2197 | [0.2197, 1.0] | 380 (6 + 53 + 321) | unresolved |
| all trials | exclusion:condition=effusion | 103/481 | 0.2141 | (not standard) | 103/487 | 0.2115 | [0.2115, 1.0] | 384 (6 + 49 + 329) | unresolved |
| all trials | exclusion:condition=unresolved_toxicity | 100/481 | 0.2079 | (not standard) | 100/487 | 0.2053 | [0.2053, 1.0] | 387 (6 + 49 + 332) | unresolved |
| all trials | exclusion:extent:metastatic | 97/481 | 0.2017 | (not standard) | 97/487 | 0.1992 | [0.1992, 1.0] | 390 (6 + 45 + 339) | unresolved |
| all trials | inclusion:lab:bilirubin | 97/481 | 0.2017 | (not standard) | 97/487 | 0.1992 | [0.1992, 1.0] | 390 (6 + 54 + 330) | unresolved |
| all trials | exclusion:condition=neurologic_disorder | 96/481 | 0.1996 | (not standard) | 96/487 | 0.1971 | [0.1971, 1.0] | 391 (6 + 39 + 346) | unresolved |
| all trials | inclusion:lab:ALT | 96/481 | 0.1996 | (not standard) | 96/487 | 0.1971 | [0.1971, 1.0] | 391 (6 + 53 + 332) | unresolved |
| all trials | inclusion:lab:hemoglobin | 96/481 | 0.1996 | (not standard) | 96/487 | 0.1971 | [0.1971, 1.0] | 391 (6 + 54 + 331) | unresolved |
| all trials | exclusion:prior_agent:immune checkpoint | 94/481 | 0.1954 | (not standard) | 94/487 | 0.193 | [0.193, 1.0] | 393 (6 + 52 + 335) | unresolved |
| all trials | inclusion:lab:AST | 91/481 | 0.1892 | (not standard) | 91/487 | 0.1869 | [0.1869, 1.0] | 396 (6 + 54 + 336) | unresolved |
| all trials | exclusion:histology=squamous | 88/481 | 0.183 | (not standard) | 88/487 | 0.1807 | [0.1807, 1.0] | 399 (6 + 51 + 342) | unresolved |
| all trials | exclusion:condition=investigator_judgment | 87/481 | 0.1809 | (not standard) | 87/487 | 0.1786 | [0.1786, 1.0] | 400 (6 + 47 + 347) | unresolved |
| all trials | inclusion:prior_lines=1\|2\|3+ | 87/481 | 0.1809 | (not standard) | 87/487 | 0.1786 | [0.1786, 1.0] | 400 (6 + 50 + 344) | unresolved |
| all trials | inclusion:prior_agent:platinum | 86/481 | 0.1788 | (not standard) | 86/487 | 0.1766 | [0.1766, 1.0] | 401 (6 + 45 + 350) | unresolved |
| all trials | exclusion:histology=small_cell | 85/481 | 0.1767 | (not standard) | 85/487 | 0.1745 | [0.1745, 1.0] | 402 (6 + 46 + 350) | unresolved |
| all trials | exclusion:condition=tuberculosis | 84/481 | 0.1746 | (not standard) | 84/487 | 0.1725 | [0.1725, 1.0] | 403 (6 + 56 + 341) | unresolved |
| all trials | inclusion:biomarker:EGFR=negative | 84/481 | 0.1746 | (not standard) | 84/487 | 0.1725 | [0.1725, 1.0] | 403 (6 + 49 + 348) | unresolved |
| all trials | inclusion:setting_word:adjuvant | 84/481 | 0.1746 | (not standard) | 84/487 | 0.1725 | [0.1725, 1.0] | 403 (6 + 49 + 348) | unresolved |
| all trials | inclusion:histology=squamous | 83/481 | 0.1726 | (not standard) | 83/487 | 0.1704 | [0.1704, 1.0] | 404 (6 + 39 + 359) | unresolved |
| all trials | inclusion:extent:unresectable | 81/481 | 0.1684 | (not standard) | 81/487 | 0.1663 | [0.1663, 1.0] | 406 (6 + 48 + 352) | unresolved |
| all trials | inclusion:lab:creatinine clearance | 78/481 | 0.1622 | (not standard) | 78/487 | 0.1602 | [0.1602, 1.0] | 409 (6 + 53 + 350) | unresolved |
| all trials | exclusion:condition=qtc | 77/481 | 0.1601 | (not standard) | 77/487 | 0.1581 | [0.1581, 1.0] | 410 (6 + 52 + 352) | unresolved |
| all trials | inclusion:condition=immunosuppression_steroids | 75/481 | 0.1559 | (not standard) | 75/487 | 0.154 | [0.154, 1.0] | 412 (6 + 52 + 354) | unresolved |
| all trials | exclusion:prior_agent:PD-1 | 74/481 | 0.1538 | (not standard) | 74/487 | 0.152 | [0.152, 1.0] | 413 (6 + 51 + 356) | unresolved |
| all trials | exclusion:prior_agent:PD-L1 | 74/481 | 0.1538 | (not standard) | 74/487 | 0.152 | [0.152, 1.0] | 413 (6 + 51 + 356) | unresolved |
| all trials | inclusion:biomarker:ALK=negative | 69/481 | 0.1435 | (not standard) | 69/487 | 0.1417 | [0.1417, 1.0] | 418 (6 + 53 + 359) | unresolved |
| all trials | exclusion:extent:recurrent | 68/481 | 0.1414 | (not standard) | 68/487 | 0.1396 | [0.1396, 1.0] | 419 (6 + 54 + 359) | unresolved |
| all trials | inclusion:ecog_ps=0\|1\|2 | 66/481 | 0.1372 | (not standard) | 66/487 | 0.1355 | [0.1355, 1.0] | 421 (6 + 56 + 359) | unresolved |
| all trials | inclusion:stage:III\|IV | 65/481 | 0.1351 | (not standard) | 65/487 | 0.1335 | [0.1335, 1.0] | 422 (6 + 50 + 366) | unresolved |
| all trials | inclusion:lab:creatinine | 64/481 | 0.1331 | (not standard) | 64/487 | 0.1314 | [0.1314, 1.0] | 423 (6 + 58 + 359) | unresolved |
| all trials | exclusion:condition=interacting_medication | 61/481 | 0.1268 | (not standard) | 61/487 | 0.1253 | [0.1253, 1.0] | 426 (6 + 52 + 368) | unresolved |
| all trials | inclusion:condition=tissue_available | 60/481 | 0.1247 | (not standard) | 60/487 | 0.1232 | [0.1232, 1.0] | 427 (6 + 47 + 374) | unresolved |
| all trials | exclusion:condition=malabsorption | 59/481 | 0.1227 | (not standard) | 59/487 | 0.1211 | [0.1211, 1.0] | 428 (6 + 53 + 369) | unresolved |
| all trials | exclusion:prior_agent:EGFR inhibitor | 58/481 | 0.1206 | (not standard) | 58/487 | 0.1191 | [0.1191, 1.0] | 429 (6 + 53 + 370) | unresolved |
| all trials | permitted:setting_word:adjuvant | 55/481 | 0.1143 | (not standard) | 55/487 | 0.1129 | [0.1129, 1.0] | 432 (6 + 60 + 366) | unresolved |
| all trials | inclusion:condition=unresolved_toxicity | 54/481 | 0.1123 | (not standard) | 54/487 | 0.1109 | [0.1109, 1.0] | 433 (6 + 52 + 375) | unresolved |
| all trials | inclusion:condition=compliance | 53/481 | 0.1102 | (not standard) | 53/487 | 0.1088 | [0.1088, 1.0] | 434 (6 + 54 + 374) | unresolved |
| all trials | inclusion:setting_word:neoadjuvant | 53/481 | 0.1102 | (not standard) | 53/487 | 0.1088 | [0.1088, 1.0] | 434 (6 + 51 + 377) | unresolved |
| all trials | exclusion:condition=gi_perforation_fistula | 49/481 | 0.1019 | (not standard) | 49/487 | 0.1006 | [0.1006, 1.0] | 438 (6 + 55 + 377) | unresolved |
| all trials | inclusion:biomarker:ALK=positive | 49/481 | 0.1019 | (not standard) | 49/487 | 0.1006 | [0.1006, 1.0] | 438 (6 + 54 + 378) | unresolved |
| all trials | exclusion:biomarker:ROS1=positive | 48/481 | 0.0998 | (not standard) | 48/487 | 0.0986 | [0.0986, 1.0] | 439 (6 + 46 + 387) | unresolved |
| all trials | inclusion:condition=pregnancy_or_breastfeeding | 48/481 | 0.0998 | (not standard) | 48/487 | 0.0986 | [0.0986, 1.0] | 439 (6 + 59 + 374) | unresolved |
| all trials | primary:endpoint:objective_response_rate | 46/481 | 0.0956 | (not standard) | 48/487 | 0.0986 | (statement rate only) |  | "" |
| all trials | exclusion:setting_word:adjuvant | 47/481 | 0.0977 | (not standard) | 47/487 | 0.0965 | [0.0965, 1.0] | 440 (6 + 52 + 382) | unresolved |
| all trials | inclusion:condition=cns_metastases | 47/481 | 0.0977 | (not standard) | 47/487 | 0.0965 | [0.0965, 1.0] | 440 (6 + 56 + 378) | unresolved |
| all trials | inclusion:prior_agent:EGFR inhibitor | 45/481 | 0.0936 | (not standard) | 45/487 | 0.0924 | [0.0924, 1.0] | 442 (6 + 55 + 381) | unresolved |
| all trials | exclusion:condition=anticoagulant_use | 43/481 | 0.0894 | (not standard) | 43/487 | 0.0883 | [0.0883, 1.0] | 444 (6 + 57 + 381) | unresolved |
| all trials | permitted:prior_agent:chemotherapy | 42/481 | 0.0873 | (not standard) | 42/487 | 0.0862 | [0.0862, 1.0] | 445 (6 + 60 + 379) | unresolved |
| all trials | permitted:setting_word:neoadjuvant | 42/481 | 0.0873 | (not standard) | 42/487 | 0.0862 | [0.0862, 1.0] | 445 (6 + 61 + 378) | unresolved |
| all trials | exclusion:condition=organ_impairment | 41/481 | 0.0852 | (not standard) | 41/487 | 0.0842 | [0.0842, 1.0] | 446 (6 + 54 + 386) | unresolved |
| all trials | permitted:prior_agent:radiotherapy | 41/481 | 0.0852 | (not standard) | 41/487 | 0.0842 | [0.0842, 1.0] | 446 (6 + 63 + 377) | unresolved |
| all trials | exclusion:condition=serious_comorbidity | 40/481 | 0.0832 | (not standard) | 40/487 | 0.0821 | [0.0821, 1.0] | 447 (6 + 56 + 385) | unresolved |
| all trials | exclusion:prior_agent:platinum | 40/481 | 0.0832 | (not standard) | 40/487 | 0.0821 | [0.0821, 1.0] | 447 (6 + 53 + 388) | unresolved |
| all trials | inclusion:prior_agent:immune checkpoint | 36/481 | 0.0748 | (not standard) | 36/487 | 0.0739 | [0.0739, 1.0] | 451 (6 + 56 + 389) | unresolved |
| all trials | exclusion:setting_word:neoadjuvant | 35/481 | 0.0728 | (not standard) | 35/487 | 0.0719 | [0.0719, 1.0] | 452 (6 + 49 + 397) | unresolved |
| all trials | permitted:condition=recent_radiotherapy | 35/481 | 0.0728 | (not standard) | 35/487 | 0.0719 | [0.0719, 1.0] | 452 (6 + 62 + 384) | unresolved |
| all trials | primary:endpoint:safety | 34/481 | 0.0707 | (not standard) | 34/487 | 0.0698 | (statement rate only) |  | "" |
| all trials | exclusion:condition=informed_consent | 33/481 | 0.0686 | (not standard) | 33/487 | 0.0678 | [0.0678, 1.0] | 454 (6 + 57 + 391) | unresolved |
| all trials | exclusion:prior_agent:docetaxel | 33/481 | 0.0686 | (not standard) | 33/487 | 0.0678 | [0.0678, 1.0] | 454 (6 + 52 + 396) | unresolved |
| all trials | exclusion:extent:locally advanced | 31/481 | 0.0644 | (not standard) | 31/487 | 0.0637 | [0.0637, 1.0] | 456 (6 + 56 + 394) | unresolved |
| all trials | primary:endpoint:disease_free_survival | 31/481 | 0.0644 | (not standard) | 31/487 | 0.0637 | (statement rate only) |  | "" |
| all trials | inclusion:resection:resected | 30/481 | 0.0624 | (not standard) | 30/487 | 0.0616 | [0.0616, 1.0] | 457 (6 + 56 + 395) | unresolved |
| all trials | exclusion:condition=contraception | 29/481 | 0.0603 | (not standard) | 29/487 | 0.0595 | [0.0595, 1.0] | 458 (6 + 56 + 396) | unresolved |
| all trials | exclusion:prior_agent:CTLA-4 | 29/481 | 0.0603 | (not standard) | 29/487 | 0.0595 | [0.0595, 1.0] | 458 (6 + 55 + 397) | unresolved |
| all trials | inclusion:condition=bleeding_thrombosis | 28/481 | 0.0582 | (not standard) | 28/487 | 0.0575 | [0.0575, 1.0] | 459 (6 + 59 + 394) | unresolved |
| all trials | exclusion:condition=compliance | 27/481 | 0.0561 | (not standard) | 27/487 | 0.0554 | [0.0554, 1.0] | 460 (6 + 55 + 399) | unresolved |
| all trials | exclusion:prior_lines=1\|2\|3+ | 27/481 | 0.0561 | (not standard) | 27/487 | 0.0554 | [0.0554, 1.0] | 460 (6 + 56 + 398) | unresolved |
| all trials | inclusion:biomarker:ROS1=negative | 27/481 | 0.0561 | (not standard) | 27/487 | 0.0554 | [0.0554, 1.0] | 460 (6 + 55 + 399) | unresolved |
| all trials | inclusion:condition=other_investigational | 27/481 | 0.0561 | (not standard) | 27/487 | 0.0554 | [0.0554, 1.0] | 460 (6 + 57 + 397) | unresolved |
| all trials | inclusion:stage:II\|III | 27/481 | 0.0561 | (not standard) | 27/487 | 0.0554 | [0.0554, 1.0] | 460 (6 + 54 + 400) | unresolved |
| all trials | exclusion:extent:advanced | 24/481 | 0.0499 | (not standard) | 24/487 | 0.0493 | [0.0493, 1.0] | 463 (6 + 56 + 401) | unresolved |
| all trials | inclusion:condition=cardiac_disease | 24/481 | 0.0499 | (not standard) | 24/487 | 0.0493 | [0.0493, 1.0] | 463 (6 + 57 + 400) | unresolved |
| all trials | exclusion:histology=non_squamous | 23/481 | 0.0478 | (not standard) | 23/487 | 0.0472 | [0.0472, 1.0] | 464 (6 + 55 + 403) | unresolved |
| all trials | inclusion:condition=pulmonary_function | 23/481 | 0.0478 | (not standard) | 23/487 | 0.0472 | [0.0472, 1.0] | 464 (6 + 59 + 399) | unresolved |
| all trials | inclusion:histology=adenocarcinoma | 23/481 | 0.0478 | (not standard) | 23/487 | 0.0472 | [0.0472, 1.0] | 464 (6 + 58 + 400) | unresolved |
| all trials | exclusion:condition=pulmonary_function | 22/481 | 0.0457 | (not standard) | 22/487 | 0.0452 | [0.0452, 1.0] | 465 (6 + 56 + 403) | unresolved |
| all trials | inclusion:condition=investigator_judgment | 22/481 | 0.0457 | (not standard) | 22/487 | 0.0452 | [0.0452, 1.0] | 465 (6 + 59 + 400) | unresolved |
| all trials | inclusion:condition=hiv | 21/481 | 0.0437 | (not standard) | 21/487 | 0.0431 | [0.0431, 1.0] | 466 (6 + 52 + 408) | unresolved |
| all trials | inclusion:condition=malabsorption | 21/481 | 0.0437 | (not standard) | 21/487 | 0.0431 | [0.0431, 1.0] | 466 (6 + 58 + 402) | unresolved |
| all trials | permitted:extent:metastatic | 21/481 | 0.0437 | (not standard) | 21/487 | 0.0431 | [0.0431, 1.0] | 466 (6 + 60 + 400) | unresolved |
| all trials | exclusion:biomarker:BRAF=positive | 20/481 | 0.0416 | (not standard) | 20/487 | 0.0411 | [0.0411, 1.0] | 467 (6 + 54 + 407) | unresolved |
| all trials | exclusion:extent:unresectable | 20/481 | 0.0416 | (not standard) | 20/487 | 0.0411 | [0.0411, 1.0] | 467 (6 + 57 + 404) | unresolved |
| all trials | inclusion:condition=pneumonitis_ild | 20/481 | 0.0416 | (not standard) | 20/487 | 0.0411 | [0.0411, 1.0] | 467 (6 + 58 + 403) | unresolved |
| all trials | inclusion:resection:resectable | 19/481 | 0.0395 | (not standard) | 19/487 | 0.039 | [0.039, 1.0] | 468 (6 + 56 + 406) | unresolved |
| all trials | exclusion:biomarker:RET=positive | 18/481 | 0.0374 | (not standard) | 18/487 | 0.037 | [0.037, 1.0] | 469 (6 + 55 + 408) | unresolved |
| all trials | exclusion:lab:hemoglobin | 18/481 | 0.0374 | (not standard) | 18/487 | 0.037 | [0.037, 1.0] | 469 (6 + 58 + 405) | unresolved |
| all trials | inclusion:condition=hepatitis | 18/481 | 0.0374 | (not standard) | 18/487 | 0.037 | [0.037, 1.0] | 469 (6 + 54 + 409) | unresolved |
| all trials | inclusion:prior_lines=1 | 17/481 | 0.0353 | (not standard) | 17/487 | 0.0349 | [0.0349, 1.0] | 470 (6 + 55 + 409) | unresolved |
| all trials | inclusion:stage:I\|II\|III | 17/481 | 0.0353 | (not standard) | 17/487 | 0.0349 | [0.0349, 1.0] | 470 (6 + 58 + 406) | unresolved |
| all trials | exclusion:histology=large_cell | 16/481 | 0.0333 | (not standard) | 16/487 | 0.0329 | [0.0329, 1.0] | 471 (6 + 54 + 411) | unresolved |
| all trials | exclusion:lab:ALT | 16/481 | 0.0333 | (not standard) | 16/487 | 0.0329 | [0.0329, 1.0] | 471 (6 + 58 + 407) | unresolved |
| all trials | exclusion:lab:AST | 16/481 | 0.0333 | (not standard) | 16/487 | 0.0329 | [0.0329, 1.0] | 471 (6 + 58 + 407) | unresolved |
| all trials | exclusion:prior_agent:VEGF inhibitor | 16/481 | 0.0333 | (not standard) | 16/487 | 0.0329 | [0.0329, 1.0] | 471 (6 + 57 + 408) | unresolved |
| all trials | inclusion:biomarker:KRAS=positive | 16/481 | 0.0333 | (not standard) | 16/487 | 0.0329 | [0.0329, 1.0] | 471 (6 + 57 + 408) | unresolved |
| all trials | inclusion:prior_agent:PD-L1 | 16/481 | 0.0333 | (not standard) | 16/487 | 0.0329 | [0.0329, 1.0] | 471 (6 + 56 + 409) | unresolved |
| all trials | permitted:condition=immunosuppression_steroids | 16/481 | 0.0333 | (not standard) | 16/487 | 0.0329 | [0.0329, 1.0] | 471 (6 + 58 + 407) | unresolved |
| all trials | primary:endpoint:event_free_survival | 16/481 | 0.0333 | (not standard) | 16/487 | 0.0329 | (statement rate only) |  | "" |
| all trials | exclusion:lab:neutrophils | 15/481 | 0.0312 | (not standard) | 15/487 | 0.0308 | [0.0308, 1.0] | 472 (6 + 58 + 408) | unresolved |
| all trials | exclusion:lab:platelets | 15/481 | 0.0312 | (not standard) | 15/487 | 0.0308 | [0.0308, 1.0] | 472 (6 + 58 + 408) | unresolved |
| all trials | exclusion:prior_agent:pemetrexed | 15/481 | 0.0312 | (not standard) | 15/487 | 0.0308 | [0.0308, 1.0] | 472 (6 + 57 + 409) | unresolved |
| all trials | inclusion:condition=vitamin_premedication | 15/481 | 0.0312 | (not standard) | 15/487 | 0.0308 | [0.0308, 1.0] | 472 (6 + 56 + 410) | unresolved |
| all trials | inclusion:lab:leukocytes | 15/481 | 0.0312 | (not standard) | 15/487 | 0.0308 | [0.0308, 1.0] | 472 (6 + 58 + 408) | unresolved |
| all trials | permitted:condition=autoimmune_disease | 15/481 | 0.0312 | (not standard) | 15/487 | 0.0308 | [0.0308, 1.0] | 472 (6 + 58 + 408) | unresolved |
| all trials | exclusion:condition=measurable_disease | 14/481 | 0.0291 | (not standard) | 14/487 | 0.0287 | [0.0287, 1.0] | 473 (6 + 58 + 409) | unresolved |
| all trials | exclusion:lab:bilirubin | 14/481 | 0.0291 | (not standard) | 14/487 | 0.0287 | [0.0287, 1.0] | 473 (6 + 58 + 409) | unresolved |
| all trials | exclusion:lab:creatinine | 14/481 | 0.0291 | (not standard) | 14/487 | 0.0287 | [0.0287, 1.0] | 473 (6 + 58 + 409) | unresolved |
| all trials | inclusion:biomarker:PD-L1=negative\|positive | 14/481 | 0.0291 | (not standard) | 14/487 | 0.0287 | [0.0287, 1.0] | 473 (6 + 56 + 411) | unresolved |
| all trials | inclusion:condition=hypertension | 14/481 | 0.0291 | (not standard) | 14/487 | 0.0287 | [0.0287, 1.0] | 473 (6 + 59 + 408) | unresolved |
| all trials | inclusion:condition=other_malignancy | 14/481 | 0.0291 | (not standard) | 14/487 | 0.0287 | [0.0287, 1.0] | 473 (6 + 57 + 410) | unresolved |
| all trials | inclusion:prior_agent:PD-1 | 14/481 | 0.0291 | (not standard) | 14/487 | 0.0287 | [0.0287, 1.0] | 473 (6 + 57 + 410) | unresolved |
| all trials | exclusion:biomarker:MET=positive | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 57 + 412) | unresolved |
| all trials | exclusion:histology=adenocarcinoma | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 58 + 411) | unresolved |
| all trials | exclusion:lab:creatinine clearance | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 58 + 411) | unresolved |
| all trials | exclusion:prior_agent:ALK inhibitor | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 55 + 414) | unresolved |
| all trials | exclusion:prior_lines=1 | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 57 + 412) | unresolved |
| all trials | inclusion:biomarker:MET=positive | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 58 + 411) | unresolved |
| all trials | inclusion:biomarker:PD-L1=positive | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 57 + 412) | unresolved |
| all trials | inclusion:biomarker:ROS1=positive | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 58 + 411) | unresolved |
| all trials | permitted:condition=cns_metastases | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | [0.0246, 1.0] | 475 (6 + 62 + 407) | unresolved |
| all trials | primary:endpoint:pharmacokinetics | 12/481 | 0.0249 | (not standard) | 12/487 | 0.0246 | (statement rate only) |  | "" |
| all trials | exclusion:setting_word:maintenance | 11/481 | 0.0229 | (not standard) | 11/487 | 0.0226 | [0.0226, 1.0] | 476 (6 + 57 + 413) | unresolved |
| all trials | exclusion:stage:III | 11/481 | 0.0229 | (not standard) | 11/487 | 0.0226 | [0.0226, 1.0] | 476 (6 + 57 + 413) | unresolved |
| all trials | inclusion:condition=active_infection | 11/481 | 0.0229 | (not standard) | 11/487 | 0.0226 | [0.0226, 1.0] | 476 (6 + 57 + 413) | unresolved |
| all trials | inclusion:condition=anticoagulant_use | 11/481 | 0.0229 | (not standard) | 11/487 | 0.0226 | [0.0226, 1.0] | 476 (6 + 59 + 411) | unresolved |
| all trials | inclusion:prior_agent:ALK inhibitor | 11/481 | 0.0229 | (not standard) | 11/487 | 0.0226 | [0.0226, 1.0] | 476 (6 + 59 + 411) | unresolved |
| all trials | exclusion:biomarker:KRAS=positive | 10/481 | 0.0208 | (not standard) | 10/487 | 0.0205 | [0.0205, 1.0] | 477 (6 + 56 + 415) | unresolved |
| all trials | exclusion:biomarker:NTRK=positive | 10/481 | 0.0208 | (not standard) | 10/487 | 0.0205 | [0.0205, 1.0] | 477 (6 + 57 + 414) | unresolved |
| all trials | inclusion:biomarker:RET=positive | 10/481 | 0.0208 | (not standard) | 10/487 | 0.0205 | [0.0205, 1.0] | 477 (6 + 58 + 413) | unresolved |
| all trials | inclusion:condition=qtc | 10/481 | 0.0208 | (not standard) | 10/487 | 0.0205 | [0.0205, 1.0] | 477 (6 + 59 + 412) | unresolved |
| all trials | inclusion:lab:albumin | 10/481 | 0.0208 | (not standard) | 10/487 | 0.0205 | [0.0205, 1.0] | 477 (6 + 58 + 413) | unresolved |
| all trials | inclusion:setting_word:consolidation | 10/481 | 0.0208 | (not standard) | 10/487 | 0.0205 | [0.0205, 1.0] | 477 (6 + 59 + 412) | unresolved |
| all trials | permitted:extent:recurrent | 10/481 | 0.0208 | (not standard) | 10/487 | 0.0205 | [0.0205, 1.0] | 477 (6 + 62 + 409) | unresolved |
| all trials | permitted:prior_agent:immune checkpoint | 10/481 | 0.0208 | (not standard) | 10/487 | 0.0205 | [0.0205, 1.0] | 477 (6 + 62 + 409) | unresolved |
| all trials | inclusion:setting_word:maintenance | 9/481 | 0.0187 | (not standard) | 9/487 | 0.0185 | [0.0185, 1.0] | 478 (6 + 59 + 413) | unresolved |
| all trials | inclusion:stage:I\|II | 9/481 | 0.0187 | (not standard) | 9/487 | 0.0185 | [0.0185, 1.0] | 478 (6 + 59 + 413) | unresolved |
| all trials | permitted:extent:locally advanced | 9/481 | 0.0187 | (not standard) | 9/487 | 0.0185 | [0.0185, 1.0] | 478 (6 + 63 + 409) | unresolved |
| all trials | primary:endpoint:biomarker_endpoint | 9/481 | 0.0187 | (not standard) | 9/487 | 0.0185 | (statement rate only) |  | "" |
| all trials | unsectioned:age=stated | 9/481 | 0.0187 | (not standard) | 9/487 | 0.0185 | [0.0185, 1.0] | 478 (6 + 63 + 409) | unresolved |
| all trials | exclusion:condition=sex | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 58 + 415) | unresolved |
| all trials | exclusion:condition=smoking | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 54 + 419) | unresolved |
| all trials | exclusion:prior_agent:taxane | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 56 + 417) | unresolved |
| all trials | inclusion:biomarker:HER2=positive | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 58 + 415) | unresolved |
| all trials | inclusion:biomarker:PD-L1=@≥1% | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 59 + 414) | unresolved |
| all trials | inclusion:prior_agent:docetaxel | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 58 + 415) | unresolved |
| all trials | inclusion:stage:I | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 58 + 415) | unresolved |
| all trials | permitted:condition=other_investigational | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 63 + 410) | unresolved |
| all trials | permitted:prior_agent:platinum | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 62 + 411) | unresolved |
| all trials | permitted:prior_lines=0 | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 62 + 411) | unresolved |
| all trials | unsectioned:condition=diagnosis_confirmed | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 62 + 411) | unresolved |
| all trials | unsectioned:ecog_ps=0\|1 | 8/481 | 0.0166 | (not standard) | 8/487 | 0.0164 | [0.0164, 1.0] | 479 (6 + 62 + 411) | unresolved |
| all trials | exclusion:biomarker:HER2=positive | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 58 + 416) | unresolved |
| all trials | exclusion:prior_agent:MET inhibitor | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 56 + 418) | unresolved |
| all trials | exclusion:prior_lines=0 | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 57 + 417) | unresolved |
| all trials | exclusion:stage:I | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 58 + 416) | unresolved |
| all trials | inclusion:biomarker:PD-L1=@≥50% | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 55 + 419) | unresolved |
| all trials | inclusion:prior_lines=2 | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 58 + 416) | unresolved |
| all trials | primary:endpoint:major_pathologic_response | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | (statement rate only) |  | "" |
| all trials | primary:endpoint:quality_of_life | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | (statement rate only) |  | "" |
| all trials | unsectioned:condition=immunosuppression_steroids | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 62 + 412) | unresolved |
| all trials | unsectioned:condition=other_malignancy | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 62 + 412) | unresolved |
| all trials | unsectioned:condition=recent_surgery | 7/481 | 0.0146 | (not standard) | 7/487 | 0.0144 | [0.0144, 1.0] | 480 (6 + 62 + 412) | unresolved |
| all trials | exclusion:condition=life_expectancy | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 57 + 418) | unresolved |
| all trials | exclusion:condition=weight_loss | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 57 + 418) | unresolved |
| all trials | exclusion:stage:IV | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 58 + 417) | unresolved |
| all trials | inclusion:condition=autoimmune_disease | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 59 + 416) | unresolved |
| all trials | inclusion:condition=effusion | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 59 + 416) | unresolved |
| all trials | inclusion:condition=hypersensitivity | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 59 + 416) | unresolved |
| all trials | inclusion:prior_agent:pemetrexed | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 58 + 417) | unresolved |
| all trials | inclusion:prior_agent:taxane | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 58 + 417) | unresolved |
| all trials | permitted:condition=anticoagulant_use | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 63 + 412) | unresolved |
| all trials | permitted:condition=recent_surgery | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 62 + 413) | unresolved |
| all trials | permitted:stage:III | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 63 + 412) | unresolved |
| all trials | primary:endpoint:intracranial_response | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | (statement rate only) |  | "" |
| all trials | primary:endpoint:pathologic_complete_response | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | (statement rate only) |  | "" |
| all trials | unsectioned:biomarker:EGFR=positive | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 63 + 412) | unresolved |
| all trials | unsectioned:condition=active_infection | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 62 + 413) | unresolved |
| all trials | unsectioned:condition=informed_consent | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 63 + 412) | unresolved |
| all trials | unsectioned:condition=pneumonitis_ild | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 62 + 413) | unresolved |
| all trials | unsectioned:condition=pregnancy_or_breastfeeding | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 62 + 413) | unresolved |
| all trials | unsectioned:condition=recent_radiotherapy | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 62 + 413) | unresolved |
| all trials | unsectioned:extent:metastatic | 6/481 | 0.0125 | (not standard) | 6/487 | 0.0123 | [0.0123, 1.0] | 481 (6 + 62 + 413) | unresolved |
| all trials | exclusion:resection:resected | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 58 + 418) | unresolved |
| all trials | inclusion:biomarker:BRAF=negative | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 57 + 419) | unresolved |
| all trials | inclusion:biomarker:BRAF=positive | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 58 + 418) | unresolved |
| all trials | inclusion:biomarker:EGFR=unknown | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 58 + 418) | unresolved |
| all trials | inclusion:biomarker:NTRK=positive | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 58 + 418) | unresolved |
| all trials | inclusion:biomarker:PD-L1=@<1% | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 58 + 418) | unresolved |
| all trials | inclusion:condition=gi_perforation_fistula | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 59 + 417) | unresolved |
| all trials | inclusion:condition=interacting_medication | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 59 + 417) | unresolved |
| all trials | inclusion:condition=weight_loss | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 59 + 417) | unresolved |
| all trials | inclusion:prior_agent:VEGF inhibitor | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 58 + 418) | unresolved |
| all trials | inclusion:prior_lines=1\|2 | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 57 + 419) | unresolved |
| all trials | inclusion:stage:II | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 57 + 419) | unresolved |
| all trials | permitted:extent:advanced | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 62 + 414) | unresolved |
| all trials | unsectioned:condition=cardiac_disease | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 62 + 414) | unresolved |
| all trials | unsectioned:condition=cns_metastases | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 63 + 413) | unresolved |
| all trials | unsectioned:condition=contraception | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 63 + 413) | unresolved |
| all trials | unsectioned:condition=hepatitis | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 62 + 414) | unresolved |
| all trials | unsectioned:condition=hiv | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 62 + 414) | unresolved |
| all trials | unsectioned:condition=hypersensitivity | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 62 + 414) | unresolved |
| all trials | unsectioned:condition=measurable_disease | 5/481 | 0.0104 | (not standard) | 5/487 | 0.0103 | [0.0103, 1.0] | 482 (6 + 62 + 414) | unresolved |
| all trials | exclusion:biomarker:EGFR=negative | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 58 + 419) | unresolved |
| all trials | inclusion:biomarker:NTRK=negative | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 58 + 419) | unresolved |
| all trials | inclusion:biomarker:RET=negative | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 58 + 419) | unresolved |
| all trials | inclusion:condition=neurologic_disorder | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 57 + 420) | unresolved |
| all trials | inclusion:histology=large_cell | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 59 + 418) | unresolved |
| all trials | inclusion:histology=small_cell | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 59 + 418) | unresolved |
| all trials | inclusion:prior_agent:CTLA-4 | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 59 + 418) | unresolved |
| all trials | permitted:condition=other_malignancy | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | permitted:condition=unresolved_toxicity | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | permitted:prior_agent:EGFR inhibitor | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | permitted:setting_word:maintenance | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 62 + 415) | unresolved |
| all trials | unsectioned:condition=bleeding_thrombosis | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | unsectioned:condition=investigator_judgment | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | unsectioned:condition=life_expectancy | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 62 + 415) | unresolved |
| all trials | unsectioned:condition=other_investigational | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | unsectioned:condition=unresolved_toxicity | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | unsectioned:extent:locally advanced | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 62 + 415) | unresolved |
| all trials | unsectioned:histology=small_cell | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | unsectioned:prior_agent:chemotherapy | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | unsectioned:prior_agent:radiotherapy | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 63 + 414) | unresolved |
| all trials | unsectioned:prior_lines=0 | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 62 + 415) | unresolved |
| all trials | unsectioned:stage:IV | 4/481 | 0.0083 | (not standard) | 4/487 | 0.0082 | [0.0082, 1.0] | 483 (6 + 62 + 415) | unresolved |
| all trials | exclusion:biomarker:ALK=unknown | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 57 + 421) | unresolved |
| all trials | exclusion:lab:albumin | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 58 + 420) | unresolved |
| all trials | exclusion:stage:III\|IV | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 58 + 420) | unresolved |
| all trials | inclusion:biomarker:ALK=unknown | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 59 + 419) | unresolved |
| all trials | inclusion:biomarker:MET=negative | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 58 + 420) | unresolved |
| all trials | inclusion:condition=organ_transplant | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 59 + 419) | unresolved |
| all trials | inclusion:condition=serious_comorbidity | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 59 + 419) | unresolved |
| all trials | inclusion:condition=substance_or_psychiatric | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 59 + 419) | unresolved |
| all trials | inclusion:ecog_ps=0 | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 59 + 419) | unresolved |
| all trials | inclusion:ecog_ps=2 | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 59 + 419) | unresolved |
| all trials | inclusion:prior_lines=0\|1\|2 | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 59 + 419) | unresolved |
| all trials | permitted:biomarker:EGFR=positive | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | permitted:condition=bleeding_thrombosis | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | permitted:condition=contraception | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 62 + 416) | unresolved |
| all trials | permitted:condition=effusion | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | permitted:condition=live_vaccine | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | permitted:condition=pneumonitis_ild | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | permitted:lab:hemoglobin | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | permitted:prior_agent:PD-L1 | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | permitted:prior_agent:VEGF inhibitor | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 62 + 416) | unresolved |
| all trials | permitted:prior_lines=1 | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 62 + 416) | unresolved |
| all trials | permitted:stage:IV | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | unsectioned:biomarker:ALK=positive | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | unsectioned:condition=compliance | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | unsectioned:condition=hypertension | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | unsectioned:condition=tissue_available | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | unsectioned:extent:advanced | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | unsectioned:extent:recurrent | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | unsectioned:organ_function_unspecified=adequate | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 62 + 416) | unresolved |
| all trials | unsectioned:prior_agent:platinum | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 63 + 415) | unresolved |
| all trials | unsectioned:stage:III | 3/481 | 0.0062 | (not standard) | 3/487 | 0.0062 | [0.0062, 1.0] | 484 (6 + 62 + 416) | unresolved |
| all trials | exclusion:age=stated | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | exclusion:biomarker:EGFR=unknown | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 57 + 422) | unresolved |
| all trials | exclusion:biomarker:PD-L1=negative | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | exclusion:biomarker:PD-L1=unknown | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | exclusion:setting_word:consolidation | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | exclusion:stage:II | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | exclusion:stage:I\|II | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | exclusion:stage:I\|II\|III | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=@<50% | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 57 + 422) | unresolved |
| all trials | inclusion:biomarker:PD-L1=negative | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 59 + 420) | unresolved |
| all trials | inclusion:biomarker:PD-L1=positive@≥1% | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=positive@≥50% | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 59 + 420) | unresolved |
| all trials | inclusion:condition=live_vaccine | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 59 + 420) | unresolved |
| all trials | inclusion:ecog_ps=1 | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 58 + 421) | unresolved |
| all trials | inclusion:prior_lines=0\|1 | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 59 + 420) | unresolved |
| all trials | inclusion:setting_word:perioperative | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 59 + 420) | unresolved |
| all trials | inclusion:stage:I\|III\|IV | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 59 + 420) | unresolved |
| all trials | permitted:biomarker:ALK=positive | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:condition=hypertension | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:condition=measurable_disease | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:condition=pregnancy_or_breastfeeding | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:histology=adenocarcinoma | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:lab:AST | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:lab:bilirubin | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:prior_agent:PD-1 | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:prior_lines=0\|1\|2 | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:resection:resected | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:stage:I\|II | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | permitted:stage:I\|II\|III | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | primary:endpoint:duration_of_response | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | (statement rate only) |  | "" |
| all trials | primary:endpoint:time_to_progression | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | (statement rate only) |  | "" |
| all trials | unsectioned:biomarker:BRAF=negative | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:biomarker:BRAF=positive | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:biomarker:EGFR=negative | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:biomarker:NTRK=negative | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:biomarker:ROS1=positive | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:condition=interacting_medication | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:condition=live_vaccine | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:condition=malabsorption | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:condition=organ_transplant | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:condition=qtc | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:condition=sex | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:condition=smoking | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:histology=non_squamous | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:lab:ALT | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:lab:creatinine | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:lab:creatinine clearance | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:lab:neutrophils | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:lab:platelets | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:prior_agent:EGFR inhibitor | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 63 + 416) | unresolved |
| all trials | unsectioned:prior_agent:PD-1 | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 62 + 417) | unresolved |
| all trials | unsectioned:prior_agent:immune checkpoint | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 62 + 417) | unresolved |
| all trials | unsectioned:setting_word:adjuvant | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 62 + 417) | unresolved |
| all trials | unsectioned:setting_word:neoadjuvant | 2/481 | 0.0042 | (not standard) | 2/487 | 0.0041 | [0.0041, 1.0] | 485 (6 + 62 + 417) | unresolved |
| all trials | exclusion:biomarker:ALK=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:biomarker:BRAF=unknown | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:biomarker:KRAS=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 57 + 423) | unresolved |
| all trials | exclusion:biomarker:NTRK=unknown | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:biomarker:PD-L1=@<50% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:biomarker:PD-L1=@≥50% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:biomarker:PD-L1=negative\|unknown | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:biomarker:PD-L1=positive | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:biomarker:RET=unknown | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:condition=prior_enrollment | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:condition=tissue_available | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:condition=vitamin_premedication | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:ecog_ps=0\|1 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:ecog_ps=2\|3\|4 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:prior_lines=2 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:setting_word:perioperative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:stage:II\|III | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | exclusion:stage:I\|III | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | inclusion:biomarker:ALK=negative\|positive | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:ALK=negative\|unknown | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | inclusion:biomarker:EGFR=negative\|positive | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:EGFR=negative\|unknown | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 58 + 422) | unresolved |
| all trials | inclusion:biomarker:HER2=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:KRAS=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=@1% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=@1-49% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=@>=1% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=negative\|positive@0to49% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=negative\|positive@≥1% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=negative\|positive@≥50% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=positive@>=50% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:PD-L1=unknown | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:biomarker:ROS1=unknown | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:condition=smoking | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:ecog_ps=2\|3 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | inclusion:stage:I\|II\|III\|IV | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 59 + 421) | unresolved |
| all trials | permitted:biomarker:BRAF=positive | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 62 + 418) | unresolved |
| all trials | permitted:biomarker:EGFR=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:condition=diagnosis_confirmed | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:condition=hepatitis | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:condition=hypersensitivity | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:condition=investigator_judgment | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:condition=malabsorption | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:condition=organ_transplant | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:condition=sex | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:condition=weight_loss | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 62 + 418) | unresolved |
| all trials | permitted:extent:unresectable | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:histology=non_squamous | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:histology=squamous | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:lab:ALT | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:lab:creatinine | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:lab:creatinine clearance | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:lab:neutrophils | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:lab:platelets | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:organ_function_unspecified=adequate | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:prior_agent:pemetrexed | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:prior_lines=1\|2 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:prior_lines=2 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | permitted:resection:resectable | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | primary:endpoint:disease_control_rate | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | (statement rate only) |  | "" |
| all trials | unsectioned:biomarker:ALK=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:biomarker:MET=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:biomarker:NTRK=positive | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:biomarker:PD-L1=@≥1% | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 62 + 418) | unresolved |
| all trials | unsectioned:biomarker:RET=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:biomarker:ROS1=negative | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:condition=anticoagulant_use | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:condition=autoimmune_disease | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:condition=gi_perforation_fistula | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:condition=neurologic_disorder | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:condition=substance_or_psychiatric | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:condition=vitamin_premedication | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:ecog_ps=0\|1\|2 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:extent:unresectable | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:histology=squamous | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:lab:AST | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:lab:bilirubin | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:lab:hemoglobin | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:prior_agent:CTLA-4 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 62 + 418) | unresolved |
| all trials | unsectioned:prior_agent:PD-L1 | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:prior_agent:VEGF inhibitor | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:prior_agent:taxane | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:prior_lines=1\|2\|3+ | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:setting_word:consolidation | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:setting_word:maintenance | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:stage:III\|IV | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:stage:I\|II\|III | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| all trials | unsectioned:stage:I\|II\|III\|IV | 1/481 | 0.0021 | (not standard) | 1/487 | 0.0021 | [0.0021, 1.0] | 486 (6 + 63 + 417) | unresolved |
| setting unresolved | inclusion:condition=diagnosis_confirmed | 309/399 | 0.7744 | (not standard) | 309/405 | 0.763 | [0.763, 1.0] | 96 (6 + 11 + 79) | unresolved |
| setting unresolved | inclusion:ecog_ps=0\|1 | 254/399 | 0.6366 | (not standard) | 254/405 | 0.6272 | [0.6272, 1.0] | 151 (6 + 18 + 127) | unresolved |
| setting unresolved | exclusion:condition=pregnancy_or_breastfeeding | 236/399 | 0.5915 | (not standard) | 236/405 | 0.5827 | [0.5827, 1.0] | 169 (6 + 31 + 132) | unresolved |
| setting unresolved | inclusion:condition=measurable_disease | 219/399 | 0.5489 | (not standard) | 219/405 | 0.5407 | [0.5407, 1.0] | 186 (6 + 23 + 157) | unresolved |
| setting unresolved | exclusion:condition=other_malignancy | 215/399 | 0.5388 | (not standard) | 215/405 | 0.5309 | [0.5309, 1.0] | 190 (6 + 26 + 158) | unresolved |
| setting unresolved | exclusion:condition=recent_radiotherapy | 215/399 | 0.5388 | (not standard) | 215/405 | 0.5309 | [0.5309, 1.0] | 190 (6 + 24 + 160) | unresolved |
| setting unresolved | exclusion:condition=cns_metastases | 209/399 | 0.5238 | (not standard) | 209/405 | 0.516 | [0.516, 1.0] | 196 (6 + 19 + 171) | unresolved |
| setting unresolved | exclusion:condition=active_infection | 197/399 | 0.4937 | (not standard) | 197/405 | 0.4864 | [0.4864, 1.0] | 208 (6 + 30 + 172) | unresolved |
| setting unresolved | inclusion:condition=informed_consent | 196/399 | 0.4912 | (not standard) | 196/405 | 0.484 | [0.484, 1.0] | 209 (6 + 35 + 168) | unresolved |
| setting unresolved | inclusion:age=stated | 190/399 | 0.4762 | (not standard) | 190/405 | 0.4691 | [0.4691, 1.0] | 215 (6 + 34 + 175) | unresolved |
| setting unresolved | primary:endpoint:progression_free_survival | 186/399 | 0.4662 | (not standard) | 189/405 | 0.4667 | (statement rate only) |  | "" |
| setting unresolved | inclusion:condition=life_expectancy | 185/399 | 0.4637 | (not standard) | 185/405 | 0.4568 | [0.4568, 1.0] | 220 (6 + 32 + 182) | unresolved |
| setting unresolved | exclusion:condition=hypersensitivity | 182/399 | 0.4561 | (not standard) | 182/405 | 0.4494 | [0.4494, 1.0] | 223 (6 + 30 + 187) | unresolved |
| setting unresolved | exclusion:condition=pneumonitis_ild | 176/399 | 0.4411 | (not standard) | 176/405 | 0.4346 | [0.4346, 1.0] | 229 (6 + 25 + 198) | unresolved |
| setting unresolved | inclusion:condition=contraception | 176/399 | 0.4411 | (not standard) | 176/405 | 0.4346 | [0.4346, 1.0] | 229 (6 + 37 + 186) | unresolved |
| setting unresolved | exclusion:condition=immunosuppression_steroids | 174/399 | 0.4361 | (not standard) | 174/405 | 0.4296 | [0.4296, 1.0] | 231 (6 + 19 + 206) | unresolved |
| setting unresolved | exclusion:condition=hiv | 172/399 | 0.4311 | (not standard) | 172/405 | 0.4247 | [0.4247, 1.0] | 233 (6 + 24 + 203) | unresolved |
| setting unresolved | exclusion:condition=cardiac_disease | 170/399 | 0.4261 | (not standard) | 170/405 | 0.4198 | [0.4198, 1.0] | 235 (6 + 32 + 197) | unresolved |
| setting unresolved | inclusion:extent:metastatic | 166/399 | 0.416 | (not standard) | 166/405 | 0.4099 | [0.4099, 1.0] | 239 (6 + 22 + 211) | unresolved |
| setting unresolved | exclusion:condition=recent_surgery | 165/399 | 0.4135 | (not standard) | 165/405 | 0.4074 | [0.4074, 1.0] | 240 (6 + 29 + 205) | unresolved |
| setting unresolved | exclusion:condition=hepatitis | 158/399 | 0.396 | (not standard) | 158/405 | 0.3901 | [0.3901, 1.0] | 247 (6 + 29 + 212) | unresolved |
| setting unresolved | exclusion:prior_agent:radiotherapy | 154/399 | 0.386 | (not standard) | 154/405 | 0.3802 | [0.3802, 1.0] | 251 (6 + 25 + 220) | unresolved |
| setting unresolved | exclusion:condition=autoimmune_disease | 144/399 | 0.3609 | (not standard) | 144/405 | 0.3556 | [0.3556, 1.0] | 261 (6 + 24 + 231) | unresolved |
| setting unresolved | inclusion:histology=non_squamous | 141/399 | 0.3534 | (not standard) | 141/405 | 0.3481 | [0.3481, 1.0] | 264 (6 + 24 + 234) | unresolved |
| setting unresolved | inclusion:prior_agent:chemotherapy | 141/399 | 0.3534 | (not standard) | 141/405 | 0.3481 | [0.3481, 1.0] | 264 (6 + 25 + 233) | unresolved |
| setting unresolved | exclusion:condition=other_investigational | 128/399 | 0.3208 | (not standard) | 128/405 | 0.316 | [0.316, 1.0] | 277 (6 + 30 + 241) | unresolved |
| setting unresolved | exclusion:condition=bleeding_thrombosis | 124/399 | 0.3108 | (not standard) | 124/405 | 0.3062 | [0.3062, 1.0] | 281 (6 + 38 + 237) | unresolved |
| setting unresolved | inclusion:condition=recent_radiotherapy | 120/399 | 0.3008 | (not standard) | 120/405 | 0.2963 | [0.2963, 1.0] | 285 (6 + 36 + 243) | unresolved |
| setting unresolved | primary:endpoint:overall_survival | 119/399 | 0.2982 | (not standard) | 119/405 | 0.2938 | (statement rate only) |  | "" |
| setting unresolved | exclusion:prior_agent:chemotherapy | 108/399 | 0.2707 | (not standard) | 108/405 | 0.2667 | [0.2667, 1.0] | 297 (6 + 35 + 256) | unresolved |
| setting unresolved | exclusion:condition=hypertension | 106/399 | 0.2657 | (not standard) | 106/405 | 0.2617 | [0.2617, 1.0] | 299 (6 + 38 + 255) | unresolved |
| setting unresolved | inclusion:prior_agent:radiotherapy | 105/399 | 0.2632 | (not standard) | 105/405 | 0.2593 | [0.2593, 1.0] | 300 (6 + 37 + 257) | unresolved |
| setting unresolved | inclusion:biomarker:EGFR=positive | 104/399 | 0.2607 | (not standard) | 104/405 | 0.2568 | [0.2568, 1.0] | 301 (6 + 35 + 260) | unresolved |
| setting unresolved | inclusion:condition=recent_surgery | 101/399 | 0.2531 | (not standard) | 101/405 | 0.2494 | [0.2494, 1.0] | 304 (6 + 34 + 264) | unresolved |
| setting unresolved | inclusion:lab:platelets | 101/399 | 0.2531 | (not standard) | 101/405 | 0.2494 | [0.2494, 1.0] | 304 (6 + 38 + 260) | unresolved |
| setting unresolved | inclusion:stage:IV | 99/399 | 0.2481 | (not standard) | 99/405 | 0.2444 | [0.2444, 1.0] | 306 (6 + 34 + 266) | unresolved |
| setting unresolved | exclusion:biomarker:EGFR=positive | 97/399 | 0.2431 | (not standard) | 97/405 | 0.2395 | [0.2395, 1.0] | 308 (6 + 29 + 273) | unresolved |
| setting unresolved | inclusion:stage:III | 97/399 | 0.2431 | (not standard) | 97/405 | 0.2395 | [0.2395, 1.0] | 308 (6 + 33 + 269) | unresolved |
| setting unresolved | exclusion:condition=organ_transplant | 96/399 | 0.2406 | (not standard) | 96/405 | 0.237 | [0.237, 1.0] | 309 (6 + 33 + 270) | unresolved |
| setting unresolved | inclusion:extent:locally advanced | 96/399 | 0.2406 | (not standard) | 96/405 | 0.237 | [0.237, 1.0] | 309 (6 + 33 + 270) | unresolved |
| setting unresolved | inclusion:lab:neutrophils | 96/399 | 0.2406 | (not standard) | 96/405 | 0.237 | [0.237, 1.0] | 309 (6 + 38 + 265) | unresolved |
| setting unresolved | exclusion:condition=substance_or_psychiatric | 95/399 | 0.2381 | (not standard) | 95/405 | 0.2346 | [0.2346, 1.0] | 310 (6 + 35 + 269) | unresolved |
| setting unresolved | exclusion:biomarker:ALK=positive | 92/399 | 0.2306 | (not standard) | 92/405 | 0.2272 | [0.2272, 1.0] | 313 (6 + 29 + 278) | unresolved |
| setting unresolved | exclusion:condition=live_vaccine | 91/399 | 0.2281 | (not standard) | 91/405 | 0.2247 | [0.2247, 1.0] | 314 (6 + 31 + 277) | unresolved |
| setting unresolved | exclusion:condition=diagnosis_confirmed | 87/399 | 0.218 | (not standard) | 87/405 | 0.2148 | [0.2148, 1.0] | 318 (6 + 35 + 277) | unresolved |
| setting unresolved | exclusion:condition=effusion | 87/399 | 0.218 | (not standard) | 87/405 | 0.2148 | [0.2148, 1.0] | 318 (6 + 35 + 277) | unresolved |
| setting unresolved | inclusion:condition=sex | 86/399 | 0.2155 | (not standard) | 86/405 | 0.2123 | [0.2123, 1.0] | 319 (6 + 39 + 274) | unresolved |
| setting unresolved | inclusion:lab:ALT | 86/399 | 0.2155 | (not standard) | 86/405 | 0.2123 | [0.2123, 1.0] | 319 (6 + 38 + 275) | unresolved |
| setting unresolved | inclusion:lab:bilirubin | 86/399 | 0.2155 | (not standard) | 86/405 | 0.2123 | [0.2123, 1.0] | 319 (6 + 39 + 274) | unresolved |
| setting unresolved | inclusion:lab:hemoglobin | 86/399 | 0.2155 | (not standard) | 86/405 | 0.2123 | [0.2123, 1.0] | 319 (6 + 39 + 274) | unresolved |
| setting unresolved | inclusion:organ_function_unspecified=adequate | 85/399 | 0.213 | (not standard) | 85/405 | 0.2099 | [0.2099, 1.0] | 320 (6 + 35 + 279) | unresolved |
| setting unresolved | inclusion:prior_agent:platinum | 85/399 | 0.213 | (not standard) | 85/405 | 0.2099 | [0.2099, 1.0] | 320 (6 + 30 + 284) | unresolved |
| setting unresolved | inclusion:extent:recurrent | 84/399 | 0.2105 | (not standard) | 84/405 | 0.2074 | [0.2074, 1.0] | 321 (6 + 37 + 278) | unresolved |
| setting unresolved | inclusion:prior_lines=1\|2\|3+ | 84/399 | 0.2105 | (not standard) | 84/405 | 0.2074 | [0.2074, 1.0] | 321 (6 + 35 + 280) | unresolved |
| setting unresolved | inclusion:setting_word:adjuvant | 84/399 | 0.2105 | (not standard) | 84/405 | 0.2074 | [0.2074, 1.0] | 321 (6 + 34 + 281) | unresolved |
| setting unresolved | inclusion:extent:advanced | 82/399 | 0.2055 | (not standard) | 82/405 | 0.2025 | [0.2025, 1.0] | 323 (6 + 32 + 285) | unresolved |
| setting unresolved | inclusion:lab:AST | 81/399 | 0.203 | (not standard) | 81/405 | 0.2 | [0.2, 1.0] | 324 (6 + 39 + 279) | unresolved |
| setting unresolved | exclusion:condition=unresolved_toxicity | 78/399 | 0.1955 | (not standard) | 78/405 | 0.1926 | [0.1926, 1.0] | 327 (6 + 36 + 285) | unresolved |
| setting unresolved | exclusion:condition=tuberculosis | 75/399 | 0.188 | (not standard) | 75/405 | 0.1852 | [0.1852, 1.0] | 330 (6 + 40 + 284) | unresolved |
| setting unresolved | exclusion:extent:metastatic | 75/399 | 0.188 | (not standard) | 75/405 | 0.1852 | [0.1852, 1.0] | 330 (6 + 32 + 292) | unresolved |
| setting unresolved | inclusion:prior_lines=0 | 74/399 | 0.1855 | (not standard) | 74/405 | 0.1827 | [0.1827, 1.0] | 331 (6 + 35 + 290) | unresolved |
| setting unresolved | exclusion:prior_agent:immune checkpoint | 72/399 | 0.1805 | (not standard) | 72/405 | 0.1778 | [0.1778, 1.0] | 333 (6 + 38 + 289) | unresolved |
| setting unresolved | exclusion:condition=investigator_judgment | 71/399 | 0.1779 | (not standard) | 71/405 | 0.1753 | [0.1753, 1.0] | 334 (6 + 34 + 294) | unresolved |
| setting unresolved | exclusion:condition=neurologic_disorder | 71/399 | 0.1779 | (not standard) | 71/405 | 0.1753 | [0.1753, 1.0] | 334 (6 + 32 + 296) | unresolved |
| setting unresolved | exclusion:histology=squamous | 71/399 | 0.1779 | (not standard) | 71/405 | 0.1753 | [0.1753, 1.0] | 334 (6 + 36 + 292) | unresolved |
| setting unresolved | exclusion:histology=small_cell | 69/399 | 0.1729 | (not standard) | 69/405 | 0.1704 | [0.1704, 1.0] | 336 (6 + 32 + 298) | unresolved |
| setting unresolved | inclusion:lab:creatinine clearance | 69/399 | 0.1729 | (not standard) | 69/405 | 0.1704 | [0.1704, 1.0] | 336 (6 + 38 + 292) | unresolved |
| setting unresolved | inclusion:biomarker:EGFR=negative | 68/399 | 0.1704 | (not standard) | 68/405 | 0.1679 | [0.1679, 1.0] | 337 (6 + 35 + 296) | unresolved |
| setting unresolved | inclusion:extent:unresectable | 68/399 | 0.1704 | (not standard) | 68/405 | 0.1679 | [0.1679, 1.0] | 337 (6 + 35 + 296) | unresolved |
| setting unresolved | inclusion:ecog_ps=0\|1\|2 | 61/399 | 0.1529 | (not standard) | 61/405 | 0.1506 | [0.1506, 1.0] | 344 (6 + 41 + 297) | unresolved |
| setting unresolved | exclusion:condition=qtc | 60/399 | 0.1504 | (not standard) | 60/405 | 0.1481 | [0.1481, 1.0] | 345 (6 + 37 + 302) | unresolved |
| setting unresolved | inclusion:condition=immunosuppression_steroids | 60/399 | 0.1504 | (not standard) | 60/405 | 0.1481 | [0.1481, 1.0] | 345 (6 + 38 + 301) | unresolved |
| setting unresolved | inclusion:histology=squamous | 60/399 | 0.1504 | (not standard) | 60/405 | 0.1481 | [0.1481, 1.0] | 345 (6 + 32 + 307) | unresolved |
| setting unresolved | exclusion:prior_agent:PD-1 | 58/399 | 0.1454 | (not standard) | 58/405 | 0.1432 | [0.1432, 1.0] | 347 (6 + 38 + 303) | unresolved |
| setting unresolved | exclusion:prior_agent:PD-L1 | 58/399 | 0.1454 | (not standard) | 58/405 | 0.1432 | [0.1432, 1.0] | 347 (6 + 38 + 303) | unresolved |
| setting unresolved | inclusion:lab:creatinine | 58/399 | 0.1454 | (not standard) | 58/405 | 0.1432 | [0.1432, 1.0] | 347 (6 + 43 + 298) | unresolved |
| setting unresolved | inclusion:biomarker:ALK=negative | 55/399 | 0.1378 | (not standard) | 55/405 | 0.1358 | [0.1358, 1.0] | 350 (6 + 39 + 305) | unresolved |
| setting unresolved | inclusion:stage:III\|IV | 54/399 | 0.1353 | (not standard) | 54/405 | 0.1333 | [0.1333, 1.0] | 351 (6 + 36 + 309) | unresolved |
| setting unresolved | exclusion:extent:recurrent | 53/399 | 0.1328 | (not standard) | 53/405 | 0.1309 | [0.1309, 1.0] | 352 (6 + 40 + 306) | unresolved |
| setting unresolved | inclusion:setting_word:neoadjuvant | 53/399 | 0.1328 | (not standard) | 53/405 | 0.1309 | [0.1309, 1.0] | 352 (6 + 36 + 310) | unresolved |
| setting unresolved | inclusion:condition=unresolved_toxicity | 49/399 | 0.1228 | (not standard) | 49/405 | 0.121 | [0.121, 1.0] | 356 (6 + 37 + 313) | unresolved |
| setting unresolved | inclusion:condition=compliance | 48/399 | 0.1203 | (not standard) | 48/405 | 0.1185 | [0.1185, 1.0] | 357 (6 + 39 + 312) | unresolved |
| setting unresolved | inclusion:condition=tissue_available | 47/399 | 0.1178 | (not standard) | 47/405 | 0.116 | [0.116, 1.0] | 358 (6 + 34 + 318) | unresolved |
| setting unresolved | exclusion:condition=interacting_medication | 45/399 | 0.1128 | (not standard) | 45/405 | 0.1111 | [0.1111, 1.0] | 360 (6 + 38 + 316) | unresolved |
| setting unresolved | exclusion:condition=malabsorption | 45/399 | 0.1128 | (not standard) | 45/405 | 0.1111 | [0.1111, 1.0] | 360 (6 + 38 + 316) | unresolved |
| setting unresolved | exclusion:condition=gi_perforation_fistula | 43/399 | 0.1078 | (not standard) | 43/405 | 0.1062 | [0.1062, 1.0] | 362 (6 + 40 + 316) | unresolved |
| setting unresolved | exclusion:prior_agent:EGFR inhibitor | 43/399 | 0.1078 | (not standard) | 43/405 | 0.1062 | [0.1062, 1.0] | 362 (6 + 39 + 317) | unresolved |
| setting unresolved | inclusion:biomarker:ALK=positive | 43/399 | 0.1078 | (not standard) | 43/405 | 0.1062 | [0.1062, 1.0] | 362 (6 + 40 + 316) | unresolved |
| setting unresolved | inclusion:condition=cns_metastases | 43/399 | 0.1078 | (not standard) | 43/405 | 0.1062 | [0.1062, 1.0] | 362 (6 + 42 + 314) | unresolved |
| setting unresolved | inclusion:prior_agent:EGFR inhibitor | 42/399 | 0.1053 | (not standard) | 42/405 | 0.1037 | [0.1037, 1.0] | 363 (6 + 40 + 317) | unresolved |
| setting unresolved | permitted:setting_word:adjuvant | 42/399 | 0.1053 | (not standard) | 42/405 | 0.1037 | [0.1037, 1.0] | 363 (6 + 45 + 312) | unresolved |
| setting unresolved | exclusion:condition=anticoagulant_use | 39/399 | 0.0977 | (not standard) | 39/405 | 0.0963 | [0.0963, 1.0] | 366 (6 + 41 + 319) | unresolved |
| setting unresolved | primary:endpoint:objective_response_rate | 37/399 | 0.0927 | (not standard) | 39/405 | 0.0963 | (statement rate only) |  | "" |
| setting unresolved | exclusion:setting_word:adjuvant | 38/399 | 0.0952 | (not standard) | 38/405 | 0.0938 | [0.0938, 1.0] | 367 (6 + 38 + 323) | unresolved |
| setting unresolved | exclusion:condition=organ_impairment | 37/399 | 0.0927 | (not standard) | 37/405 | 0.0914 | [0.0914, 1.0] | 368 (6 + 40 + 322) | unresolved |
| setting unresolved | inclusion:condition=pregnancy_or_breastfeeding | 37/399 | 0.0927 | (not standard) | 37/405 | 0.0914 | [0.0914, 1.0] | 368 (6 + 44 + 318) | unresolved |
| setting unresolved | inclusion:prior_agent:immune checkpoint | 36/399 | 0.0902 | (not standard) | 36/405 | 0.0889 | [0.0889, 1.0] | 369 (6 + 41 + 322) | unresolved |
| setting unresolved | exclusion:condition=serious_comorbidity | 35/399 | 0.0877 | (not standard) | 35/405 | 0.0864 | [0.0864, 1.0] | 370 (6 + 41 + 323) | unresolved |
| setting unresolved | permitted:prior_agent:chemotherapy | 35/399 | 0.0877 | (not standard) | 35/405 | 0.0864 | [0.0864, 1.0] | 370 (6 + 44 + 320) | unresolved |
| setting unresolved | exclusion:biomarker:ROS1=positive | 33/399 | 0.0827 | (not standard) | 33/405 | 0.0815 | [0.0815, 1.0] | 372 (6 + 37 + 329) | unresolved |
| setting unresolved | exclusion:prior_agent:docetaxel | 33/399 | 0.0827 | (not standard) | 33/405 | 0.0815 | [0.0815, 1.0] | 372 (6 + 36 + 330) | unresolved |
| setting unresolved | permitted:setting_word:neoadjuvant | 32/399 | 0.0802 | (not standard) | 32/405 | 0.079 | [0.079, 1.0] | 373 (6 + 45 + 322) | unresolved |
| setting unresolved | exclusion:prior_agent:platinum | 31/399 | 0.0777 | (not standard) | 31/405 | 0.0765 | [0.0765, 1.0] | 374 (6 + 39 + 329) | unresolved |
| setting unresolved | permitted:prior_agent:radiotherapy | 31/399 | 0.0777 | (not standard) | 31/405 | 0.0765 | [0.0765, 1.0] | 374 (6 + 47 + 321) | unresolved |
| setting unresolved | primary:endpoint:disease_free_survival | 31/399 | 0.0777 | (not standard) | 31/405 | 0.0765 | (statement rate only) |  | "" |
| setting unresolved | inclusion:resection:resected | 30/399 | 0.0752 | (not standard) | 30/405 | 0.0741 | [0.0741, 1.0] | 375 (6 + 41 + 328) | unresolved |
| setting unresolved | exclusion:setting_word:neoadjuvant | 29/399 | 0.0727 | (not standard) | 29/405 | 0.0716 | [0.0716, 1.0] | 376 (6 + 35 + 335) | unresolved |
| setting unresolved | primary:endpoint:safety | 29/399 | 0.0727 | (not standard) | 29/405 | 0.0716 | (statement rate only) |  | "" |
| setting unresolved | exclusion:condition=contraception | 28/399 | 0.0702 | (not standard) | 28/405 | 0.0691 | [0.0691, 1.0] | 377 (6 + 40 + 331) | unresolved |
| setting unresolved | exclusion:condition=informed_consent | 27/399 | 0.0677 | (not standard) | 27/405 | 0.0667 | [0.0667, 1.0] | 378 (6 + 42 + 330) | unresolved |
| setting unresolved | inclusion:condition=bleeding_thrombosis | 27/399 | 0.0677 | (not standard) | 27/405 | 0.0667 | [0.0667, 1.0] | 378 (6 + 44 + 328) | unresolved |
| setting unresolved | inclusion:stage:II\|III | 27/399 | 0.0677 | (not standard) | 27/405 | 0.0667 | [0.0667, 1.0] | 378 (6 + 39 + 333) | unresolved |
| setting unresolved | permitted:condition=recent_radiotherapy | 26/399 | 0.0652 | (not standard) | 26/405 | 0.0642 | [0.0642, 1.0] | 379 (6 + 46 + 327) | unresolved |
| setting unresolved | inclusion:condition=other_investigational | 24/399 | 0.0602 | (not standard) | 24/405 | 0.0593 | [0.0593, 1.0] | 381 (6 + 42 + 333) | unresolved |
| setting unresolved | exclusion:extent:locally advanced | 23/399 | 0.0576 | (not standard) | 23/405 | 0.0568 | [0.0568, 1.0] | 382 (6 + 40 + 336) | unresolved |
| setting unresolved | exclusion:condition=pulmonary_function | 22/399 | 0.0551 | (not standard) | 22/405 | 0.0543 | [0.0543, 1.0] | 383 (6 + 40 + 337) | unresolved |
| setting unresolved | exclusion:prior_lines=1\|2\|3+ | 22/399 | 0.0551 | (not standard) | 22/405 | 0.0543 | [0.0543, 1.0] | 383 (6 + 40 + 337) | unresolved |
| setting unresolved | inclusion:biomarker:ROS1=negative | 22/399 | 0.0551 | (not standard) | 22/405 | 0.0543 | [0.0543, 1.0] | 383 (6 + 41 + 336) | unresolved |
| setting unresolved | inclusion:condition=cardiac_disease | 22/399 | 0.0551 | (not standard) | 22/405 | 0.0543 | [0.0543, 1.0] | 383 (6 + 42 + 335) | unresolved |
| setting unresolved | inclusion:condition=investigator_judgment | 21/399 | 0.0526 | (not standard) | 21/405 | 0.0519 | [0.0519, 1.0] | 384 (6 + 44 + 334) | unresolved |
| setting unresolved | inclusion:condition=pulmonary_function | 21/399 | 0.0526 | (not standard) | 21/405 | 0.0519 | [0.0519, 1.0] | 384 (6 + 44 + 334) | unresolved |
| setting unresolved | exclusion:condition=compliance | 20/399 | 0.0501 | (not standard) | 20/405 | 0.0494 | [0.0494, 1.0] | 385 (6 + 41 + 338) | unresolved |
| setting unresolved | exclusion:extent:advanced | 20/399 | 0.0501 | (not standard) | 20/405 | 0.0494 | [0.0494, 1.0] | 385 (6 + 40 + 339) | unresolved |
| setting unresolved | exclusion:prior_agent:CTLA-4 | 20/399 | 0.0501 | (not standard) | 20/405 | 0.0494 | [0.0494, 1.0] | 385 (6 + 41 + 338) | unresolved |
| setting unresolved | inclusion:condition=hiv | 20/399 | 0.0501 | (not standard) | 20/405 | 0.0494 | [0.0494, 1.0] | 385 (6 + 37 + 342) | unresolved |
| setting unresolved | inclusion:condition=malabsorption | 20/399 | 0.0501 | (not standard) | 20/405 | 0.0494 | [0.0494, 1.0] | 385 (6 + 43 + 336) | unresolved |
| setting unresolved | exclusion:extent:unresectable | 19/399 | 0.0476 | (not standard) | 19/405 | 0.0469 | [0.0469, 1.0] | 386 (6 + 41 + 339) | unresolved |
| setting unresolved | inclusion:resection:resectable | 19/399 | 0.0476 | (not standard) | 19/405 | 0.0469 | [0.0469, 1.0] | 386 (6 + 41 + 339) | unresolved |
| setting unresolved | permitted:extent:metastatic | 19/399 | 0.0476 | (not standard) | 19/405 | 0.0469 | [0.0469, 1.0] | 386 (6 + 44 + 336) | unresolved |
| setting unresolved | inclusion:histology=adenocarcinoma | 18/399 | 0.0451 | (not standard) | 18/405 | 0.0444 | [0.0444, 1.0] | 387 (6 + 43 + 338) | unresolved |
| setting unresolved | exclusion:histology=non_squamous | 17/399 | 0.0426 | (not standard) | 17/405 | 0.042 | [0.042, 1.0] | 388 (6 + 39 + 343) | unresolved |
| setting unresolved | inclusion:condition=hepatitis | 17/399 | 0.0426 | (not standard) | 17/405 | 0.042 | [0.042, 1.0] | 388 (6 + 39 + 343) | unresolved |
| setting unresolved | inclusion:prior_lines=1 | 17/399 | 0.0426 | (not standard) | 17/405 | 0.042 | [0.042, 1.0] | 388 (6 + 40 + 342) | unresolved |
| setting unresolved | inclusion:stage:I\|II\|III | 17/399 | 0.0426 | (not standard) | 17/405 | 0.042 | [0.042, 1.0] | 388 (6 + 43 + 339) | unresolved |
| setting unresolved | exclusion:biomarker:BRAF=positive | 16/399 | 0.0401 | (not standard) | 16/405 | 0.0395 | [0.0395, 1.0] | 389 (6 + 39 + 344) | unresolved |
| setting unresolved | inclusion:condition=pneumonitis_ild | 16/399 | 0.0401 | (not standard) | 16/405 | 0.0395 | [0.0395, 1.0] | 389 (6 + 43 + 340) | unresolved |
| setting unresolved | primary:endpoint:event_free_survival | 16/399 | 0.0401 | (not standard) | 16/405 | 0.0395 | (statement rate only) |  | "" |
| setting unresolved | exclusion:biomarker:RET=positive | 15/399 | 0.0376 | (not standard) | 15/405 | 0.037 | [0.037, 1.0] | 390 (6 + 39 + 345) | unresolved |
| setting unresolved | exclusion:histology=large_cell | 15/399 | 0.0376 | (not standard) | 15/405 | 0.037 | [0.037, 1.0] | 390 (6 + 38 + 346) | unresolved |
| setting unresolved | inclusion:biomarker:KRAS=positive | 15/399 | 0.0376 | (not standard) | 15/405 | 0.037 | [0.037, 1.0] | 390 (6 + 42 + 342) | unresolved |
| setting unresolved | inclusion:prior_agent:PD-L1 | 15/399 | 0.0376 | (not standard) | 15/405 | 0.037 | [0.037, 1.0] | 390 (6 + 41 + 343) | unresolved |
| setting unresolved | exclusion:condition=measurable_disease | 14/399 | 0.0351 | (not standard) | 14/405 | 0.0346 | [0.0346, 1.0] | 391 (6 + 42 + 343) | unresolved |
| setting unresolved | exclusion:prior_agent:VEGF inhibitor | 14/399 | 0.0351 | (not standard) | 14/405 | 0.0346 | [0.0346, 1.0] | 391 (6 + 41 + 344) | unresolved |
| setting unresolved | inclusion:condition=hypertension | 14/399 | 0.0351 | (not standard) | 14/405 | 0.0346 | [0.0346, 1.0] | 391 (6 + 44 + 341) | unresolved |
| setting unresolved | inclusion:lab:leukocytes | 14/399 | 0.0351 | (not standard) | 14/405 | 0.0346 | [0.0346, 1.0] | 391 (6 + 43 + 342) | unresolved |
| setting unresolved | exclusion:lab:hemoglobin | 13/399 | 0.0326 | (not standard) | 13/405 | 0.0321 | [0.0321, 1.0] | 392 (6 + 42 + 344) | unresolved |
| setting unresolved | exclusion:prior_agent:pemetrexed | 13/399 | 0.0326 | (not standard) | 13/405 | 0.0321 | [0.0321, 1.0] | 392 (6 + 41 + 345) | unresolved |
| setting unresolved | inclusion:prior_agent:PD-1 | 13/399 | 0.0326 | (not standard) | 13/405 | 0.0321 | [0.0321, 1.0] | 392 (6 + 42 + 344) | unresolved |
| setting unresolved | exclusion:lab:ALT | 12/399 | 0.0301 | (not standard) | 12/405 | 0.0296 | [0.0296, 1.0] | 393 (6 + 42 + 345) | unresolved |
| setting unresolved | exclusion:prior_lines=1 | 12/399 | 0.0301 | (not standard) | 12/405 | 0.0296 | [0.0296, 1.0] | 393 (6 + 41 + 346) | unresolved |
| setting unresolved | exclusion:lab:AST | 11/399 | 0.0276 | (not standard) | 11/405 | 0.0272 | [0.0272, 1.0] | 394 (6 + 42 + 346) | unresolved |
| setting unresolved | exclusion:lab:neutrophils | 11/399 | 0.0276 | (not standard) | 11/405 | 0.0272 | [0.0272, 1.0] | 394 (6 + 42 + 346) | unresolved |
| setting unresolved | exclusion:setting_word:maintenance | 11/399 | 0.0276 | (not standard) | 11/405 | 0.0272 | [0.0272, 1.0] | 394 (6 + 41 + 347) | unresolved |
| setting unresolved | exclusion:stage:III | 11/399 | 0.0276 | (not standard) | 11/405 | 0.0272 | [0.0272, 1.0] | 394 (6 + 41 + 347) | unresolved |
| setting unresolved | permitted:condition=autoimmune_disease | 11/399 | 0.0276 | (not standard) | 11/405 | 0.0272 | [0.0272, 1.0] | 394 (6 + 44 + 344) | unresolved |
| setting unresolved | permitted:condition=immunosuppression_steroids | 11/399 | 0.0276 | (not standard) | 11/405 | 0.0272 | [0.0272, 1.0] | 394 (6 + 44 + 344) | unresolved |
| setting unresolved | exclusion:lab:creatinine | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 42 + 347) | unresolved |
| setting unresolved | exclusion:lab:platelets | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 42 + 347) | unresolved |
| setting unresolved | exclusion:prior_agent:ALK inhibitor | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 41 + 348) | unresolved |
| setting unresolved | inclusion:biomarker:MET=positive | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 44 + 345) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=positive | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 42 + 347) | unresolved |
| setting unresolved | inclusion:biomarker:ROS1=positive | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 44 + 345) | unresolved |
| setting unresolved | inclusion:condition=anticoagulant_use | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 44 + 345) | unresolved |
| setting unresolved | inclusion:condition=other_malignancy | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 42 + 347) | unresolved |
| setting unresolved | inclusion:condition=vitamin_premedication | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 42 + 347) | unresolved |
| setting unresolved | inclusion:lab:albumin | 10/399 | 0.0251 | (not standard) | 10/405 | 0.0247 | [0.0247, 1.0] | 395 (6 + 43 + 346) | unresolved |
| setting unresolved | exclusion:biomarker:KRAS=positive | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 40 + 350) | unresolved |
| setting unresolved | exclusion:biomarker:MET=positive | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 41 + 349) | unresolved |
| setting unresolved | exclusion:histology=adenocarcinoma | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 42 + 348) | unresolved |
| setting unresolved | exclusion:lab:bilirubin | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 42 + 348) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=negative\|positive | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 43 + 347) | unresolved |
| setting unresolved | inclusion:condition=active_infection | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 42 + 348) | unresolved |
| setting unresolved | inclusion:condition=qtc | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 44 + 346) | unresolved |
| setting unresolved | inclusion:prior_agent:ALK inhibitor | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 44 + 346) | unresolved |
| setting unresolved | inclusion:setting_word:consolidation | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 44 + 346) | unresolved |
| setting unresolved | inclusion:setting_word:maintenance | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 44 + 346) | unresolved |
| setting unresolved | inclusion:stage:I\|II | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 44 + 346) | unresolved |
| setting unresolved | permitted:condition=cns_metastases | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 47 + 343) | unresolved |
| setting unresolved | unsectioned:age=stated | 9/399 | 0.0226 | (not standard) | 9/405 | 0.0222 | [0.0222, 1.0] | 396 (6 + 47 + 343) | unresolved |
| setting unresolved | exclusion:condition=sex | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | [0.0198, 1.0] | 397 (6 + 42 + 349) | unresolved |
| setting unresolved | exclusion:lab:creatinine clearance | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | [0.0198, 1.0] | 397 (6 + 42 + 349) | unresolved |
| setting unresolved | exclusion:prior_agent:taxane | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | [0.0198, 1.0] | 397 (6 + 40 + 351) | unresolved |
| setting unresolved | inclusion:biomarker:RET=positive | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | [0.0198, 1.0] | 397 (6 + 44 + 347) | unresolved |
| setting unresolved | inclusion:stage:I | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | [0.0198, 1.0] | 397 (6 + 43 + 348) | unresolved |
| setting unresolved | permitted:prior_agent:immune checkpoint | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | [0.0198, 1.0] | 397 (6 + 47 + 344) | unresolved |
| setting unresolved | primary:endpoint:pharmacokinetics | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | (statement rate only) |  | "" |
| setting unresolved | unsectioned:condition=diagnosis_confirmed | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | [0.0198, 1.0] | 397 (6 + 46 + 345) | unresolved |
| setting unresolved | unsectioned:ecog_ps=0\|1 | 8/399 | 0.0201 | (not standard) | 8/405 | 0.0198 | [0.0198, 1.0] | 397 (6 + 46 + 345) | unresolved |
| setting unresolved | exclusion:biomarker:NTRK=positive | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | [0.0173, 1.0] | 398 (6 + 41 + 351) | unresolved |
| setting unresolved | exclusion:stage:I | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | [0.0173, 1.0] | 398 (6 + 42 + 350) | unresolved |
| setting unresolved | inclusion:prior_agent:docetaxel | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | [0.0173, 1.0] | 398 (6 + 43 + 349) | unresolved |
| setting unresolved | inclusion:prior_lines=2 | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | [0.0173, 1.0] | 398 (6 + 43 + 349) | unresolved |
| setting unresolved | permitted:extent:locally advanced | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | [0.0173, 1.0] | 398 (6 + 47 + 345) | unresolved |
| setting unresolved | primary:endpoint:major_pathologic_response | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | (statement rate only) |  | "" |
| setting unresolved | unsectioned:condition=immunosuppression_steroids | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | [0.0173, 1.0] | 398 (6 + 46 + 346) | unresolved |
| setting unresolved | unsectioned:condition=other_malignancy | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | [0.0173, 1.0] | 398 (6 + 46 + 346) | unresolved |
| setting unresolved | unsectioned:condition=recent_surgery | 7/399 | 0.0175 | (not standard) | 7/405 | 0.0173 | [0.0173, 1.0] | 398 (6 + 46 + 346) | unresolved |
| setting unresolved | exclusion:biomarker:HER2=positive | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 42 + 351) | unresolved |
| setting unresolved | exclusion:condition=life_expectancy | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 41 + 352) | unresolved |
| setting unresolved | exclusion:stage:IV | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 42 + 351) | unresolved |
| setting unresolved | inclusion:prior_agent:pemetrexed | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 43 + 350) | unresolved |
| setting unresolved | permitted:extent:recurrent | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 46 + 347) | unresolved |
| setting unresolved | permitted:prior_agent:platinum | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 46 + 347) | unresolved |
| setting unresolved | permitted:prior_lines=0 | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 47 + 346) | unresolved |
| setting unresolved | primary:endpoint:biomarker_endpoint | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | (statement rate only) |  | "" |
| setting unresolved | primary:endpoint:pathologic_complete_response | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | (statement rate only) |  | "" |
| setting unresolved | unsectioned:biomarker:EGFR=positive | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 47 + 346) | unresolved |
| setting unresolved | unsectioned:condition=active_infection | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 46 + 347) | unresolved |
| setting unresolved | unsectioned:condition=informed_consent | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 47 + 346) | unresolved |
| setting unresolved | unsectioned:condition=pneumonitis_ild | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 46 + 347) | unresolved |
| setting unresolved | unsectioned:condition=pregnancy_or_breastfeeding | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 46 + 347) | unresolved |
| setting unresolved | unsectioned:condition=recent_radiotherapy | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 46 + 347) | unresolved |
| setting unresolved | unsectioned:extent:metastatic | 6/399 | 0.015 | (not standard) | 6/405 | 0.0148 | [0.0148, 1.0] | 399 (6 + 46 + 347) | unresolved |
| setting unresolved | exclusion:condition=weight_loss | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 41 + 353) | unresolved |
| setting unresolved | exclusion:prior_agent:MET inhibitor | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 40 + 354) | unresolved |
| setting unresolved | exclusion:prior_lines=0 | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 41 + 353) | unresolved |
| setting unresolved | exclusion:resection:resected | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 42 + 352) | unresolved |
| setting unresolved | inclusion:biomarker:HER2=positive | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 44 + 350) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=@≥1% | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 44 + 350) | unresolved |
| setting unresolved | inclusion:condition=gi_perforation_fistula | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 44 + 350) | unresolved |
| setting unresolved | inclusion:condition=hypersensitivity | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 44 + 350) | unresolved |
| setting unresolved | inclusion:prior_agent:VEGF inhibitor | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 43 + 351) | unresolved |
| setting unresolved | inclusion:prior_agent:taxane | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 43 + 351) | unresolved |
| setting unresolved | inclusion:prior_lines=1\|2 | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 42 + 352) | unresolved |
| setting unresolved | inclusion:stage:II | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 42 + 352) | unresolved |
| setting unresolved | permitted:condition=anticoagulant_use | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 47 + 347) | unresolved |
| setting unresolved | permitted:condition=recent_surgery | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 47 + 347) | unresolved |
| setting unresolved | permitted:stage:III | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 47 + 347) | unresolved |
| setting unresolved | primary:endpoint:intracranial_response | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | (statement rate only) |  | "" |
| setting unresolved | primary:endpoint:quality_of_life | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | (statement rate only) |  | "" |
| setting unresolved | unsectioned:condition=cardiac_disease | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 46 + 348) | unresolved |
| setting unresolved | unsectioned:condition=cns_metastases | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 47 + 347) | unresolved |
| setting unresolved | unsectioned:condition=contraception | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 47 + 347) | unresolved |
| setting unresolved | unsectioned:condition=hepatitis | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 46 + 348) | unresolved |
| setting unresolved | unsectioned:condition=hiv | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 46 + 348) | unresolved |
| setting unresolved | unsectioned:condition=hypersensitivity | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 46 + 348) | unresolved |
| setting unresolved | unsectioned:condition=measurable_disease | 5/399 | 0.0125 | (not standard) | 5/405 | 0.0123 | [0.0123, 1.0] | 400 (6 + 46 + 348) | unresolved |
| setting unresolved | exclusion:biomarker:EGFR=negative | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 42 + 353) | unresolved |
| setting unresolved | inclusion:biomarker:BRAF=positive | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 44 + 351) | unresolved |
| setting unresolved | inclusion:condition=autoimmune_disease | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 44 + 351) | unresolved |
| setting unresolved | inclusion:condition=interacting_medication | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 44 + 351) | unresolved |
| setting unresolved | inclusion:histology=large_cell | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 44 + 351) | unresolved |
| setting unresolved | inclusion:histology=small_cell | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 44 + 351) | unresolved |
| setting unresolved | permitted:extent:advanced | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 46 + 349) | unresolved |
| setting unresolved | permitted:setting_word:maintenance | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 46 + 349) | unresolved |
| setting unresolved | unsectioned:condition=bleeding_thrombosis | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 47 + 348) | unresolved |
| setting unresolved | unsectioned:condition=investigator_judgment | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 47 + 348) | unresolved |
| setting unresolved | unsectioned:condition=life_expectancy | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 46 + 349) | unresolved |
| setting unresolved | unsectioned:condition=other_investigational | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 47 + 348) | unresolved |
| setting unresolved | unsectioned:condition=unresolved_toxicity | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 47 + 348) | unresolved |
| setting unresolved | unsectioned:extent:locally advanced | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 46 + 349) | unresolved |
| setting unresolved | unsectioned:histology=small_cell | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 47 + 348) | unresolved |
| setting unresolved | unsectioned:prior_agent:chemotherapy | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 47 + 348) | unresolved |
| setting unresolved | unsectioned:prior_agent:radiotherapy | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 47 + 348) | unresolved |
| setting unresolved | unsectioned:prior_lines=0 | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 46 + 349) | unresolved |
| setting unresolved | unsectioned:stage:IV | 4/399 | 0.01 | (not standard) | 4/405 | 0.0099 | [0.0099, 1.0] | 401 (6 + 46 + 349) | unresolved |
| setting unresolved | exclusion:biomarker:ALK=unknown | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 41 + 355) | unresolved |
| setting unresolved | exclusion:condition=smoking | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 42 + 354) | unresolved |
| setting unresolved | exclusion:lab:albumin | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 42 + 354) | unresolved |
| setting unresolved | exclusion:stage:III\|IV | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 42 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:BRAF=negative | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 43 + 353) | unresolved |
| setting unresolved | inclusion:biomarker:EGFR=unknown | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 43 + 353) | unresolved |
| setting unresolved | inclusion:biomarker:MET=negative | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 43 + 353) | unresolved |
| setting unresolved | inclusion:biomarker:NTRK=positive | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=@≥50% | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 43 + 353) | unresolved |
| setting unresolved | inclusion:biomarker:RET=negative | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:condition=effusion | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:condition=neurologic_disorder | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 43 + 353) | unresolved |
| setting unresolved | inclusion:condition=organ_transplant | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:condition=substance_or_psychiatric | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:condition=weight_loss | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:ecog_ps=0 | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:ecog_ps=2 | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:prior_agent:CTLA-4 | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | inclusion:prior_lines=0\|1\|2 | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 44 + 352) | unresolved |
| setting unresolved | permitted:biomarker:EGFR=positive | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:condition=bleeding_thrombosis | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:condition=contraception | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 46 + 350) | unresolved |
| setting unresolved | permitted:condition=effusion | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:condition=live_vaccine | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:condition=other_investigational | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:condition=other_malignancy | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:condition=unresolved_toxicity | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:prior_agent:EGFR inhibitor | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:prior_agent:PD-L1 | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | permitted:prior_agent:VEGF inhibitor | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 46 + 350) | unresolved |
| setting unresolved | permitted:prior_lines=1 | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 46 + 350) | unresolved |
| setting unresolved | unsectioned:biomarker:ALK=positive | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | unsectioned:condition=compliance | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | unsectioned:condition=hypertension | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | unsectioned:condition=tissue_available | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | unsectioned:extent:advanced | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | unsectioned:extent:recurrent | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | unsectioned:organ_function_unspecified=adequate | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 46 + 350) | unresolved |
| setting unresolved | unsectioned:prior_agent:platinum | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 47 + 349) | unresolved |
| setting unresolved | unsectioned:stage:III | 3/399 | 0.0075 | (not standard) | 3/405 | 0.0074 | [0.0074, 1.0] | 402 (6 + 46 + 350) | unresolved |
| setting unresolved | exclusion:biomarker:EGFR=unknown | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 41 + 356) | unresolved |
| setting unresolved | exclusion:biomarker:PD-L1=negative | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 42 + 355) | unresolved |
| setting unresolved | exclusion:biomarker:PD-L1=unknown | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 42 + 355) | unresolved |
| setting unresolved | exclusion:stage:II | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 42 + 355) | unresolved |
| setting unresolved | exclusion:stage:I\|II | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 42 + 355) | unresolved |
| setting unresolved | exclusion:stage:I\|II\|III | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 42 + 355) | unresolved |
| setting unresolved | inclusion:biomarker:NTRK=negative | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 44 + 353) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=@<1% | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 43 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=negative | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 44 + 353) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=positive@≥1% | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 43 + 354) | unresolved |
| setting unresolved | inclusion:condition=serious_comorbidity | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 44 + 353) | unresolved |
| setting unresolved | inclusion:prior_lines=0\|1 | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 44 + 353) | unresolved |
| setting unresolved | inclusion:setting_word:perioperative | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 44 + 353) | unresolved |
| setting unresolved | inclusion:stage:I\|III\|IV | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 44 + 353) | unresolved |
| setting unresolved | permitted:biomarker:ALK=positive | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:condition=hypertension | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:condition=measurable_disease | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:condition=pneumonitis_ild | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:condition=pregnancy_or_breastfeeding | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:lab:hemoglobin | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:prior_agent:PD-1 | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:prior_lines=0\|1\|2 | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:resection:resected | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:stage:IV | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | permitted:stage:I\|II\|III | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:biomarker:BRAF=negative | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:biomarker:BRAF=positive | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:biomarker:EGFR=negative | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:biomarker:NTRK=negative | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:biomarker:ROS1=positive | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:condition=interacting_medication | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:condition=live_vaccine | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:condition=malabsorption | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:condition=organ_transplant | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:condition=qtc | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:condition=sex | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:condition=smoking | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:histology=non_squamous | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:lab:ALT | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:lab:creatinine | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:lab:creatinine clearance | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:lab:neutrophils | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:lab:platelets | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:prior_agent:EGFR inhibitor | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 47 + 350) | unresolved |
| setting unresolved | unsectioned:prior_agent:PD-1 | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 46 + 351) | unresolved |
| setting unresolved | unsectioned:prior_agent:immune checkpoint | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 46 + 351) | unresolved |
| setting unresolved | unsectioned:setting_word:adjuvant | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 46 + 351) | unresolved |
| setting unresolved | unsectioned:setting_word:neoadjuvant | 2/399 | 0.005 | (not standard) | 2/405 | 0.0049 | [0.0049, 1.0] | 403 (6 + 46 + 351) | unresolved |
| setting unresolved | exclusion:biomarker:ALK=negative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:biomarker:KRAS=negative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 41 + 357) | unresolved |
| setting unresolved | exclusion:biomarker:PD-L1=@<50% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:biomarker:PD-L1=negative\|unknown | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:biomarker:PD-L1=positive | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:condition=prior_enrollment | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:condition=tissue_available | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:condition=vitamin_premedication | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:ecog_ps=0\|1 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:ecog_ps=2\|3\|4 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:prior_lines=2 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:setting_word:consolidation | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:setting_word:perioperative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:stage:II\|III | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | exclusion:stage:I\|III | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 42 + 356) | unresolved |
| setting unresolved | inclusion:biomarker:ALK=negative\|positive | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:ALK=negative\|unknown | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 43 + 355) | unresolved |
| setting unresolved | inclusion:biomarker:ALK=unknown | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:EGFR=negative\|positive | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:EGFR=negative\|unknown | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 43 + 355) | unresolved |
| setting unresolved | inclusion:biomarker:HER2=negative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=@1% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=@1-49% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=@<50% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 43 + 355) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=@>=1% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=negative\|positive@≥1% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=negative\|positive@≥50% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=positive@>=50% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=positive@≥50% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:biomarker:PD-L1=unknown | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:condition=live_vaccine | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:condition=smoking | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:ecog_ps=1 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 43 + 355) | unresolved |
| setting unresolved | inclusion:ecog_ps=2\|3 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | inclusion:stage:I\|II\|III\|IV | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 44 + 354) | unresolved |
| setting unresolved | permitted:biomarker:EGFR=negative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:condition=hepatitis | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:condition=hypersensitivity | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:condition=investigator_judgment | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:condition=malabsorption | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:condition=organ_transplant | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:condition=sex | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:condition=weight_loss | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 46 + 352) | unresolved |
| setting unresolved | permitted:extent:unresectable | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:histology=adenocarcinoma | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:histology=non_squamous | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:histology=squamous | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:lab:ALT | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:lab:AST | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:lab:bilirubin | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:organ_function_unspecified=adequate | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:prior_agent:pemetrexed | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:prior_lines=1\|2 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:prior_lines=2 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:resection:resectable | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | permitted:stage:I\|II | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | primary:endpoint:disease_control_rate | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | (statement rate only) |  | "" |
| setting unresolved | primary:endpoint:duration_of_response | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | (statement rate only) |  | "" |
| setting unresolved | primary:endpoint:time_to_progression | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | (statement rate only) |  | "" |
| setting unresolved | unsectioned:biomarker:ALK=negative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:biomarker:MET=negative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:biomarker:NTRK=positive | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:biomarker:PD-L1=@≥1% | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 46 + 352) | unresolved |
| setting unresolved | unsectioned:biomarker:RET=negative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:biomarker:ROS1=negative | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:condition=anticoagulant_use | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:condition=autoimmune_disease | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:condition=gi_perforation_fistula | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:condition=neurologic_disorder | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:condition=substance_or_psychiatric | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:condition=vitamin_premedication | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:ecog_ps=0\|1\|2 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:extent:unresectable | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:histology=squamous | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:lab:AST | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:lab:bilirubin | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:lab:hemoglobin | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:prior_agent:CTLA-4 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 46 + 352) | unresolved |
| setting unresolved | unsectioned:prior_agent:PD-L1 | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:prior_agent:VEGF inhibitor | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:prior_agent:taxane | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:prior_lines=1\|2\|3+ | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:setting_word:consolidation | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:setting_word:maintenance | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:stage:III\|IV | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:stage:I\|II\|III | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
| setting unresolved | unsectioned:stage:I\|II\|III\|IV | 1/399 | 0.0025 | (not standard) | 1/405 | 0.0025 | [0.0025, 1.0] | 404 (6 + 47 + 351) | unresolved |
