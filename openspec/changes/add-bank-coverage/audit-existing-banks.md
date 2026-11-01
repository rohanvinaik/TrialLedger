# Audit of the existing banks against the contract (task 2.1)

Written 2026-11-01 by Claude. It covers the banks of `TrialLedger/banks.py` (the eight typing banks of
`BANKS`, `endpoint_classes`, `stated_targets` and the sentence-level `permitted`). It checks them against
Decisions 1 (the contract), 2 (the registry), 4 (indication disambiguates, never suppresses) and 5
(provenance). Every number below is measured on development data and establishes nothing about other
populations. The data:

- **NSCLC**: the 487 interventional Phase 3 NSCLC trials started 2015-2024 in `/tmp/nsclc3` (pulled
  2026-10-31). They were read from a private copy (`studies.json`, `classes.json`, `studies.csv`); the folder
  itself was not written to. 10,187 criteria, of which 8,565 were typed before this task and 8,557 after
  (the 8 criteria the ECOG retirement leaves untyped, below).
- **Pilot**: the 18-trial stratified pilot of 2026-10-31/11-01 (seed `pilot-2026-10-31`). Its records were
  read from `~/tools/TrialLedger-runs/pilot-2026-10-31/audit/records`. 228 criteria, of which 85 are typed.

Each criterion is itemized by `criteria.itemize`. Every bank is run on it and every atom is put through
`contracts.legacy_result`, `contracts.result_problems` and `loader.atom_registry_problems` against the
compiled seed registry. No model and no network were used.

## The result in one place

- **Contract problems** (`result_problems`): 0 on NSCLC, before and after; 0 on the pilot; 0 on the real
  criteria of tests/test_banks.py.
- **Registry problems** (`atom_registry_problems`): NSCLC 62 before, 25 after; pilot 0; the tests' real
  criteria 1 before, 0 after.
  - "≥ 18 years" read as a window: NSCLC 37 before, 0 after; the tests' real criteria 1 before, 0 after.
  - A criterion-wide grade on a family that takes none: NSCLC 25, unchanged; 0 elsewhere.
- **The frozen expectation** (`checkpoint_blockers_exclude_autoimmune_disease`) on NSCLC: 110 present, 22
  not documented, 9 unresolved, 346 not applicable; 0 verified deviations. Identical after, trial for trial.
- **Coordinates**, per NSCLC trial: identical after, trial for trial. **Profile elements**: identical after
  except 8 `inclusion:ecog_ps=…` elements, one in each of 8 trials, removed with the ECOG single-value
  branch (listed below); design.xlsx loses 7 Profile rows and 5 Mechanism rows with them, and no other row
  changes. Near-miss pairs: 0 before, 0 after.
- **The code root** (`warrants.derivation_files`) holds neither `banks.py` nor `provenance.py`. No stored
  folder's warrants change.

- **Keep or retire, by B7** ("abstention is always preferred to a wrong reading"). The test is applied rule
  by rule, branch by branch, on the measured populations:
  - A rule or branch with no reading found right is **retired**: it abstains. One: performance status's
    single-value branch, 8 of 8 NSCLC readings wrong, none on the pilot.
  - A rule whose wrong readings no narrow guard can separate from its other readings, without the shared
    parsers (3.1) or the assertion layer (6.1), is **kept**, its wrong readings counted. Retiring it whole
    would make every reading the audit did not find wrong abstain as well. B7 still binds it: no bank is
    released (Decision 10, step 7) until its owning package makes those readings abstain. Kept so: the age
    bank (21 of 258 NSCLC atoms found wrong, 1 of 7 on the pilot, 2 more incomplete), the prior-lines
    progression rule (20 of 117 found wrong), the conditions bank's criterion-wide grade (25 registry
    problems; the attachment of the other 452 grades unmeasured).
  - A rule that conforms and has no wrong reading found is kept as built.
  Each package that replaces a bank (3.1-3.5, 5.1) migrates or retires the rest against these findings.
- Two rules are **changed**: the conditions bank's window (the age is the age bank's) and the
  performance-status single-value branch (retired).
- The other defects found are recorded here with their counts and examples. Each is routed to the task
  that owns its fix.

## Fixed: the age is the age bank's (the disagreement kept for 2.1)

`named_conditions` attached the first time window within 60 characters after a mention. `_WINDOW` accepts a
bare `≥` or "at least" before a number of years, so "1. Male or female ≥ 18 years." gave `sex` the window
"18 years". `sex` is an Attribute, which takes no window, and the words are the criterion's age, which the
age bank already reads.

The rule now: a window in years whose words overlap the age bank's span for that criterion (`age_limits`) is
the age. It is the age bank's, not the condition's window. A window in any other unit is never taken for an
age, even where the age bank reads its number as an age (NCT04325763: "Life expectancy ≥ 3 months"
keeps its window, see the age bank's defects below). Tests:
- `tests/test_banks.py::test_an_age_beside_a_condition_is_the_age_banks`: NCT04416035, NCT03521154,
  NCT06254599.
- `test_a_window_in_months_is_never_taken_for_an_age`: NCT04325763, NCT02893332.
- `test_a_window_in_years_apart_from_the_age_is_kept`: authored. No real criterion of either population
  holds an age beside a window in years apart from it.

`tests/test_semantic_registry.py` now expects no registry problem on the real criteria. `named_conditions`
converges COMPLETE (operator universe, modulo 45 unproven-equivalent and 2 crash-only value gaps; 90/109
killed).

### Every changed output (39 atoms, one per criterion; the window removed, nothing else)

NSCLC, 38 criteria. In each, the window was the criterion's age: "Male or female ≥ 18 years", "... aged at
least 18 years", "... at least 18 years of age".

- `condition:sex`, `window 18 years` → no window, in 37 criteria: NCT02364999 #1, NCT02504489 #1,
  NCT02511106 #1, NCT02613507 #4, NCT03074864 #1, NCT03306992 #1, NCT03521154 #1, NCT03653546 #2,
  NCT03787992 #2, NCT03849768 #2, NCT04035486 #1, NCT04143607 #1, NCT04239833 #1, NCT04325698 #1,
  NCT04351555 #1, NCT04416035 #1, NCT04500704 #2, NCT04500717 #2, NCT04633564 #2, NCT04687241 #1,
  NCT04695925 #2, NCT04762459 #1, NCT04853342 #1, NCT04923906 #1, NCT04951635 #2, NCT05120349 #1,
  NCT05338970 #1, NCT05382728 #1, NCT05654454 #2, NCT05673590 #2, NCT06031558 #1, NCT06041776 #2,
  NCT06080776 #1, NCT06280196 #1, NCT06348199 #1, NCT06430866 #1, NCT06472245 #1.
- `condition:informed_consent`, `window 18 years` → no window: NCT06254599 #1, "At the time of signing the
  informed consent form (ICF), age is ≥ 18 years." The age at consent is not a window of the consent.

Pilot, 1 criterion:
- `condition:contraception`, `window 50 years` → no window: NCT04693377 #8, "... or underwent surgical
  sterilization. Women \>= 50 years of age would be considered post-menopausal ...". Here "the age is the
  age bank's" is **not** the mechanism: the criterion states no eligibility age, and the age bank's reading
  that the window overlaps (minimum 50) is itself invented from a definition of menopause (see the age
  bank's defects below). The window is dropped only because it overlaps that reading. The outcome is still
  right: "50 years" is no window of contraception or of the sterilization. When 3.2 stops reading 50 as an
  age, this window would come back unless the conditions bank no longer takes "≥ N years" without a
  temporal marker as a window (3.4, the conditions package).

(#n is the criterion's index among the trial's itemized pieces.)

These changes do not alter the frozen expectation, the profile elements or the coordinates: none of them
reads a condition's window.

### Every changed output of the performance-status retirement (8 atoms, NSCLC; none on the pilot)

Each is an inclusion criterion. Its `ecog_ps` atom is removed, so its profile element
`inclusion:ecog_ps=<value>` and its near-miss predicate `ecog_ps` (now unknown, "") go with it. Every reading
was wrong, so each trial's ECOG is now unread, never misread:

- NCT03372694 #3 and NCT03244605 #3, "* The score of ECOG ≥2 points": was 2 (should be 2-5).
- NCT03469960 #4, "4. ECOG PS \< 1": was 1 (should be 0).
- NCT05157776 #6, "6. ECOG 0～1;" (a full-width tilde): was 0 (should be 0, 1).
- NCT02273375 #9, "... ECOG performance status of 0, 1.": was 0 (should be 0, 1).
- NCT06564324 #6, "... performance status zero (0) to 1.": was 0 (should be 0, 1).
- NCT02448992 #4, "... better than Eastern Cooperative Group (ECOG) of 2 ...": was 2 (should be 0, 1).
- NCT03195491 #4, "... Performance Status of less than or equal to 1": was 1 (should be 0, 1).

Each of the 8 criteria held no other atom, so each is now **untyped** (typed criteria on NSCLC: 8,565 →
8,557; the pilot's 85 unchanged). An untyped criterion is unresolved silence in the profile, never an
absence, and an audit of these trials would now ask an `untyped_criterion` question of each.

design.xlsx (measured with `profile.frequency_rows` and `mechanism_rows` over the 487 trials, all and by
setting, before and after). Every removed row's element existed only through these misreadings:
- Profile, 7 rows removed: `inclusion:ecog_ps=0` (all trials, S 3; setting unresolved, S 3),
  `inclusion:ecog_ps=1` (all trials, S 2; setting unresolved, S 1; advanced_first_line, S 1),
  `inclusion:ecog_ps=2` (all trials, S 3; setting unresolved, S 3).
- Mechanism, 5 rows removed, every one `unresolved`: `inclusion:ecog_ps=1` against CTLA-4-directed
  Blocking Antibody (all trials; advanced_first_line) and against Programmed Death Receptor-1 Blocking
  Antibody (all trials; setting unresolved; advanced_first_line).
- No other row of either sheet changed.

Measured before and after on every NSCLC and pilot criterion: no other atom of any bank changed, the
coordinates and the frozen expectation are unchanged trial for trial, and `nearmiss.near_misses` finds no
pair either way. Tests: `tests/test_banks.py::test_a_lone_performance_status_value_read_first_abstains`
(the seven texts). `performance_status` converges COMPLETE (operator universe, modulo 47 unproven-equivalent
and 21 crash-only value gaps; 81/118 killed). Detective's golden for "* ECOG performance status 1 at
screening", which pinned the single value 1, now pins no atom.

The pilot's audit asked about the changed atom: `327b7caf86cb90de`, "This inclusion criterion requires
participants to have: condition = contraception (window 50 years)". Claude's blind label was
`unsupported`. qwen3:8b's answer was refused (`quote_not_in_envelope`), so it carries no verdict.
- Re-asked under this code, the claim reads "condition = contraception", with no window. It is still
  unsupported: a sterilization inside a definition of menopause is no contraception requirement. So the
  pilot's tally of 32 wrong claims, 20 corrected, is unchanged.
- `gates.mention_value_gate` acts only on a `wrong_value` verdict, so its pilot tally (25 right and 3
  wrong overruled) is unchanged too.
- The question's id, a digest of its content, would differ.

## Per bank

Exposure for every bank: NSCLC Phase 3 2015-2024, then the pilot of 2026-10-31/11-01, whose audit read
every bank's atoms (`provenance.RULE_EXPOSURE`, unchanged). No bank is frozen or confirmed. "Pilot-revised"
means the pilot's symbolic corrections (add-targeted-questions, "Symbolic corrections from the pilot")
changed its rules, so its rule provenance names the pilot too (`provenance.DEV_AND_PILOT`, new).
Atoms are counted on the two populations as `type_criterion` gives them.

### performance_status (`nsclc.ecog_ps`)

- **Exposure**: NSCLC 412 atoms before this task, 404 after; pilot 2. Pilot-revised (the API's escaped `=\<`).
  Its origin was NSCLC only and now names both populations.
- **Contract and registry**: no problem.
- **Decision 4**: no indication read.
- **Values**: invented or wrong in a measurable set. All 8 NSCLC atoms read from the single-value branch were
  wrong:
  - "ECOG ≥2 points" reads 2 alone (NCT03372694, NCT03244605).
  - "ECOG PS \< 1" reads 1 (NCT03469960).
  - "ECOG 0～1", with a full-width tilde, reads 0 (NCT05157776).
  - "of 0, 1." reads 0 (NCT02273375).
  - "zero (0) to 1" reads 0 (NCT06564324).
  - "better than ... ECOG of 2" reads 2 (NCT02448992).
  - "less than or equal to 1" reads 1 (NCT03195491).

  The cause: the comparator and range words the shared parser will own (3.1) are not read here.
- **Retired: the single-value branch** (B7: no reading of it found right). A lone value read first now
  abstains; the 8 changed outputs are listed above. A lone value that is right ("ECOG performance status 1")
  abstains too, until 3.1's comparators and 3.3 read it whole.
- **Kept**: the range, list and upper-bound branches read correctly on the tests' real criteria and on the
  pilot's 2 atoms. To replace: the scales package (3.3), over 3.1's comparators. The scale stays marked
  `unversioned` and flagged on the registry until 3.3 pins its source edition.

### biomarker (`nsclc.biomarker.<gene>`)

- **Exposure**: NSCLC 1,229 atoms, pilot 0.
- **Contract and registry**: no problem.
- **Decision 4**: no indication read. The gene list (EGFR, ALK, ROS1, KRAS, BRAF, MET, RET, NTRK, HER2,
  PD-L1) is oncology vocabulary. A gene outside it gives no atom, which is NO_TRIGGER, never "absent".
- **Entailment**: `_DOCUMENTED` reads "known/confirmed/documented ... status" as {negative, positive},
  never unknown. That is an entailment, known ⇒ not unknown, authored inside the bank. Decision 2 wants
  such entailments registered as separate, versioned rules. NSCLC: 28 atoms ("A known PD-L1 result",
  NCT04513925; "Confirmed tumor PD-L1 status", NCT03164616).
- **Kept**, the entailment named. To migrate: molecular markers (3.5) and oncology (5.1), with the
  entailment registered apart.

### prior_therapy (`nsclc.prior_lines`, `nsclc.prior_agent.<agent>`)

- **Exposure**: NSCLC 2,442 atoms, pilot 4.
- **Contract and registry**: no problem.
- **Decision 4**: no indication read.
- **Entailment**: progression, relapse, failure or intolerance on or after a therapy gives prior lines
  {1, 2, 3+}. That is an entailment (progressed on a therapy ⇒ at least one prior line) authored in the bank.
- **Invented values from the same rule**, 20 NSCLC atoms in all:
  - Contraception's "failure rate of \< 1% per year during the treatment" gives prior lines in 12
    criteria (NCT03456076, NCT03884192, NCT03351361, NCT02838420 twice, NCT06048315, NCT03194893 twice,
    NCT04603807, NCT03912389, NCT05648071, NCT03922997).
  - Hypersensitivity's "intolerance to study drugs" or "the investigational drug" gives prior lines in 7
    (NCT02284139, NCT06082635, NCT06281964, NCT06012435, NCT06319313, NCT05648071, NCT06048315).
  - "failure to get rid of those drugs" gives prior lines in 1 (NCT03083743).
- **Scope**: the param `scope` is "advanced" when those words appear anywhere in the criterion. That is
  attachment by co-occurrence, which Decision 1 gives to the assertion layer. NSCLC: advanced 227,
  unspecified 134.
- **Kept**, the entailment and the defects named (B7's second case: 20 of the progression rule's 117 NSCLC
  atoms found wrong; "failure" and "intolerance" also name a prior line's end, so no word list separates
  them without 3.1 and 3.4). To migrate: medication and substance exposure (3.4) and oncology lines and
  regimens (5.1). Attachment belongs to 6.1.

### setting (`nsclc.stage`, `nsclc.extent`, `nsclc.setting_word`, `nsclc.resection`)

- **Exposure**: NSCLC 2,355 atoms, pilot 1.
- **Contract and registry**: no problem.
- **Decision 4: nonconforming.** No indication is read, but the resection rule requires a lung word
  ("NSCLC", "non-small", "lung", "primary tumour") within 60 characters and no other site or malignancy
  near. That is a lung gate written into the text test. It drops explicit resections:
  - Pilot, 1: NCT02712437 #4, a breast-cancer trial, "must have completed primary surgical resection". This
    is Decision 4's own failure, an explicit mention suppressed outside the lung.
  - NSCLC, 117 dropped for want of a lung word near them. Many are the lung tumour's own resection with the
    word over 60 characters away (NCT03456076 #2, "Complete resection of ... Stage IB ... to Stage IIIA
    ... NSCLC"; NCT06632327 #1, "surgically resectable stage IIA to IIIB NSCLC"). Others are other
    malignancies, rightly not this tumour's (NCT05318443 #15, "local prostate cancer after radical
    resection").
  - NSCLC, 4 dropped near another site (NCT04656652 #37, "adequately resected non-melanoma skin cancer").
- **Kept**, nonconforming, with the reason: the concept is `nsclc.resection`, the lung tumour's
  resection. With no indication passed to banks, removing the gate would turn other malignancies'
  resections into this tumour's. To replace: a site-bearing resection (procedures, anatomy, 3.4; oncology,
  5.1), with the trial's indication used by the 6.1 resolver to say whose tumour it is, never to drop it.
- **Stage**: groups are AJCC words (`words_only`, no edition pinned; 5.1 pins it, the founder's decision
  to wait).
- **Negation window**: extent and stage negated within 30 characters are dropped. That is a text negation,
  which Decision 1 gives to the assertion layer. Kept until 6.1.

### organ_function (`nsclc.lab.<analyte>`, `nsclc.organ_function_unspecified`)

- **Exposure**: NSCLC 1,448 atoms, pilot 8. Pilot-revised (escaped comparators, paired thresholds with
  their qualifiers). Its origin was NSCLC only and now names both populations.
- **Contract and registry**: no problem.
- **Decision 4**: no indication read.
- **Values**: kept as written, never converted. "Adequate organ function" is `unspecified`, never a
  threshold.
- **Kept**. To migrate: laboratory measurements (3.3), units through UCUM (3.1).

### conditions (`nsclc.condition.<name>`)

- **Exposure**: NSCLC 8,867 atoms, pilot 86. Pilot-revised (negation, windows needing a temporal marker,
  vocabulary boundaries), and revised here (2.1, the age).
- **Contract**: no problem.
- **Registry**: 25 NSCLC atoms remain with `unknown_argument`, all `grade`, all after the fix (0 on the
  pilot). The bank attaches the first CTCAE grade anywhere in the criterion to every condition it names. The
  grade usually belongs to another mention. Each atom is listed, criterion by criterion:
  - `grade 2` on `malabsorption` and `pulmonary_function`: NCT04964479 #13 and #15, NCT05346952 #14 and #16,
    NCT05718167 #12 (both).
  - `grade` on `qtc`: NCT03856697 #19, NCT04009317 #3, NCT04762459 #3, NCT04923906 #3, NCT06564324 #23,
    NCT05204628 #16, NCT02201992 #12, NCT04687241 #3.
  - `grade` on `investigator_judgment`: NCT04471428 #6, NCT04762459 #3, NCT04923906 #3, NCT04687241 #3.
  - `grade` on `malabsorption`: NCT04762459 #3, NCT04923906 #3, NCT04687241 #3.
  - `grade` on `contraception`: NCT04009317 #3.
  - `grade` on `pulmonary_function`: NCT06505837 #20, NCT06300177 #17.
  - `grade ≥2` on `informed_consent`: NCT04547504 #26.

  Gating the grade on the concept's family would hide only the registry symptom: the State, Event and
  Exposure atoms (477 NSCLC condition atoms carry a grade) would keep a grade that belongs to another
  mention. The defect is attachment, which Decision 1 gives to the assertion layer. **Found, not fixed**
  (B7's second case: which of the 477 grades belong to their mention is not measured, and no rule here can
  tell without the assertion layer); routed to conditions and events (3.4) and the assertion layer (6.1).
- **Window values**: "Life expectancy ≥ 12 weeks" gives `life_expectancy` the window "12 weeks". That is
  the measurement's value read as a window (pinned by `tests/test_pilot_corrections.py`). Kept; to migrate
  to a Measurement value in 3.3.
- **Decision 4**: no indication read. "Other malignancy" and "transplant" are general vocabulary.
- **Kept**, the rest as built.

### age (`nsclc.age`)

- **Exposure**: NSCLC 258 atoms, pilot 7.
- **Contract and registry**: no problem.
- **Decision 4**: no indication read.
- **Values**: invented. `_AGE`'s unit is optional and its number is not bounded, so in a criterion that
  says "age" anywhere, the first comparator and number is read as the minimum age. 21 NSCLC atoms (of
  258) are a duration, a laboratory value or a definition's age:
  - Life expectancy, "at least 12 weeks" → minimum 12: NCT02714010 #4. "≥ 3 months" → minimum 3:
    NCT04325763 #1, NCT04073537 #3.
  - Contraception or amenorrhea, in months or days → minimum 3, 6, 12 or 180: NCT02893332 #8,
    NCT05668650 #13, NCT04500704 #8, NCT04500717 #9, NCT04772287 #12, NCT06505837 #9, NCT04841811 #7,
    NCT02972333 #9, NCT03849768 #7, NCT04316364 #7.
  - A window, "at least 4 weeks" → minimum 4: NCT04923906 #3.
  - A laboratory value, a number cut after three digits or before a decimal point: "≥75 × 10⁹/L" → 75
    (NCT05989542 #9); "≥ 1.5 × 109/L" → 1 (NCT03150875 #7); "≥ 1500 x 109/L" → 150 (NCT06598527 #1,
    NCT06564324 #8); "FEV1 ≥ 1.2 Liter" → 1 (NCT02790190 #4).
  - Definitions of menopause, "women over 45" → minimum 45 (NCT03391869 #16 and #26). That is an age,
    but of a definition, not of eligibility.

  On the pilot, its 7 atoms, each classified:
  - Invented, 1: NCT04693377 #8, "Women \>= 50 years of age would be considered post-menopausal" →
    minimum 50. A definition's age, the class of NCT03391869; the criterion states no eligibility age. The
    pilot's one changed conditions window rests on this reading (above).
  - Incomplete, 2: NCT03862950 #2, "age 6 through 35 years, inclusive" → minimum 6 alone ("through" is no
    range word here); NCT03862950 #14, "Age younger than 6 or older than 35 years" → minimum 35 alone, the
    bound "younger than 6" lost (the upper bound is sought only after the first match).
  - Not found wrong, 4: NCT01533272 #2 ("Older than 18 years old"), NCT04382755 #8 ("Age ≥ 18 years"),
    NCT04740710 #2 ("Age 18-65"), NCT06581653 #2 ("at least 18 years of age").

  Abstention is preferred to a wrong reading (B7). These are **found, not fixed** here, because the
  numbers, units and intervals are the shared parsers' (3.1) and the age is demographics' (3.2): no narrow
  guard separates "Age ≥ 18" (no unit) from "≥ 3 months" in a criterion that says "age" without them, so
  retiring the comparator branch would make the rule's 237 NSCLC atoms not found wrong abstain too. The fix
  is owned there. Meanwhile the conditions bank's new rule reads only windows in years as the age, so this
  defect never drops a weeks or months window; a window in years can be dropped by it, as on the pilot
  (NCT04693377 #8), and on no NSCLC criterion (measured: no criterion of either population has an age atom
  beside a kept window in years).
- **Kept** (B7's second case), the defects named. To migrate: demographics and developmental age (3.2).

### histology (`nsclc.histology.<name>`)

- **Exposure**: NSCLC 580 atoms, pilot 0.
- **Contract and registry**: no problem.
- **Decision 4: nonconforming.** A histology word with another site or malignancy within 40 characters
  gives no atom: 89 NSCLC drops, 0 on the pilot. On NSCLC these are the exceptions of an "other
  malignancy" criterion ("squamous cell carcinoma of the skin", NCT06254599 #16), rightly not this tumour.
  In a head-and-neck or cervical trial the same guard would drop the trial's own histology.
- **Kept**, nonconforming, with the reason: the concept is the lung tumour's histology (WHO lung tumour
  names, `words_only`, no edition cited). To replace: oncology histology by site (5.1), the 6.1 resolver
  disambiguating whose tumour.

### endpoints (`endpoint_classes`, `time_points`; not in `BANKS`)

- **Exposure**: NSCLC and pilot, per `RULE_EXPOSURE`.
- **Contract**: they return lists of class names and time points, not atoms. No contract or registry
  concept yet.
- **Decision 4**: no indication read. The classes are oncology-shaped (survival, response, pathologic
  response), which Decision 11 records.
- **Kept**. To replace: endpoint classes and time frames for every domain (5b.1).

### stated_targets (not in `BANKS`)

- **Exposure**: NSCLC and pilot.
- **Contract**: a list of agent words from an intervention's own description, not atoms.
- **Decision 4**: no indication read.
- **Values**: invented in a known case, already an open item in AGENTS.md: every agent word of the
  description counts, drug names among them ("XB-1 given after carboplatin" states "platinum"). Gating it
  is a change of output for the founder to approve.
- **Kept**. To migrate: medication and substance exposure (3.4) and the arm structure (5b.2).

### permitted (sentence-level modality in `type_criterion`)

- Pilot-revised. A sentence that grants a permission marks every atom in it `("modality", "permitted")`.
  That is a candidate annotation (Decision 1's `ANNOTATIONS`), never a requirement.
- **Kept**; the assertion layer (6.1) may override it.

## Silence and absence

No bank reads silence as absence. A bank that finds nothing returns no atom, which the adapter reports as
NO_TRIGGER. An untyped criterion is never read as lacking anything (the profile counts it as unresolved
silence). "No prior systemic therapy" gives zero lines because the text says so. `organ_function_unspecified`
is emitted only where no threshold was read, and says "adequate", never a value.

## Provenance changes (Decision 5)

The rule provenance of `bank:performance_status` and `bank:organ_function` now names the pilot beside the
NSCLC trials (`provenance.DEV_AND_PILOT`). The pilot's corrections revised both, but their origin named
NSCLC alone. `bank:performance_status`'s note now records the single-value branch's retirement.
`bank:conditions` already named both, and its note now records 2.1's age rule. No exposure
changed: `RULE_EXPOSURE` already listed both populations for every bank. These texts are rows of
design.xlsx's Rules sheet, so three rows read differently: `bank:performance_status` and
`bank:organ_function` (origin and note) and `bank:conditions` (note).

## Left for the founder or later tasks

- The 25 criterion-wide grades: 3.4 and 6.1.
- The age bank's 21 invented ages on NSCLC, and on the pilot 1 invented and 2 incomplete: 3.1 and 3.2.
- ECOG read from a lone value or from comparator words ("≥2", "\<", "less than or equal to"), now
  abstaining: 3.1 and 3.3.
- The 20 invented prior lines: 3.4 and 5.1.
- The lung gates of the resection and histology rules: 5.1 and 6.1. They are a standing exception to B3
  (Decision 4) until then, and need the founder's explicit acceptance: on the pilot they suppress a breast
  trial's resection (NCT02712437 #4).
- B7 applied rule by rule (above): the founder may prefer to retire the age bank's comparator branch, or
  the progression rule, now, at the cost of their readings not found wrong.
- The two entailments authored in banks (documented status, progression ⇒ prior line): to be registered as
  separate rules (Decision 2).
- The performance-status scale's source edition: 3.3.

Each will change outputs on NSCLC when fixed, to be listed then as here.
