# Tasks: refine-landscape-record

## 0. Base and contract (sequential; nothing in 1-5 starts before 0.4)

- [ ] 0.1 The push gate's secret scan: the hex-digest detector removed (the project's lowercase hex digests are
      fingerprints, never credentials), the other detectors kept, the digest-recognition code it needed deleted.
- [ ] 0.2 The acceptance harness (add-agent-operation 7.1) on main.
- [ ] 0.3 relation-kinds (add-scoped-reasoning 1.1-1.2) rebased and on main (landscape.json schema 2).
- [x] 0.4 The contract commit: `TrialLedger/contract.py` (the schema-3 field table: field, API path or rule,
      plain or reading, consumers; the universe table; the display dictionaries for the API's enums), the
      baseline bodies and the API field metadata as test fixtures, and the two gates (every API path resolves
      in the saved bodies; every field names an existing consumer).

## 1. Unit A: the record (`landscape.py`, `operate.py`)

- [ ] 1.1 Plain registry values with the field dictionary; value objects only for readings and values not simply
      known; the per-value source and link copies removed.
- [ ] 1.2 The added fields of design §1, each from its contract path.
- [ ] 1.3 Results, analyses, baseline, participant flow and adverse events in the registry's nesting, groups keyed
      within their module.
- [ ] 1.4 The removals of design §1.
- [ ] 1.5 Universe assignment and per-universe readings wired in (consuming unit B), each study's assignment and
      sources recorded; the cohort section counts only trials a reading applies to and emits empty sections not
      at all.
- [ ] 1.6 schema 3: schema check, statuses, `fields`, RULE_VERSIONS (the universe table's version); study type kept.
- [ ] 1.8 The key-criteria reading (a named rule over each criterion's typed readings and a declared category set)
      and the standard-language section (criteria stated by most trials of the same universe, with counts,
      representative verbatim wording and their trials), per design §4a.
- [ ] 1.7 Preservation: an independent check of registry value → record value for every contract field on the
      fixture bodies (nested populations, category-level denominators, comments, precision), failing on planted
      defects (a measurement under the wrong group, a dropped nested field).

## 2. Unit B: universes (`universes.py`, `coherence.py`, `semantics/loader.py`) — the assignment of 2.1 and
the fixtures of 2.4 are superseded by 7.2 (design §9.1); build 7.2, not these

- [ ] 2.1 The universe table and `assign(study)`: the three sources of design §3, each finding recorded; one,
      several, none, undecidable.
- [ ] 2.2 Per-universe coordinates and relations; each pack's requirements; `resolve(evidence, universe)`.
- [ ] 2.3 The loader's optional `universes` key (absent from the canonical form when absent).
- [ ] 2.4 Named fixtures: the PTSD trial (general), the lymphoma/CLL immunotoxin (haematologic), the solid-tumour
      basket without condition MeSH (solid, from its free-text condition), an osimertinib trial whose condition is
      "Progression Free Survival" (solid, from its intervention), a supportive-care trial in cancer patients (no
      setting); a study with no usable condition at all (scope unresolved, never general) beside an identified
      non-oncology study (general).

## 3. Unit C: the workbook (`readout.py`)

- [ ] 3.1 The sheets of design §4, against fixture records of schema 3.
- [ ] 3.2 Display dictionaries for every code; labelled readings; the Readings sheet and the column dictionary in
      place of the per-cell evidence register.
- [ ] 3.3 Safety as term × groups; Posted results long by group; Groups, Baseline, Participant flow and
      Statistical analyses listings.
- [ ] 3.4 Read-back certification and deterministic bytes kept; continuation sheets past the row limit.
- [ ] 3.5 The compact Trial index (short fields, short unresolved labels, reasons in the dossier) and the
      dossier's section bands with links to the listings; the Read me's plain search first, provenance last; the
      treatment-context limit stated wherever setting or line appears.
- [ ] 3.7 The dossier's "Key criteria" band and the "Standard protocol language" sheet of design §4a.
- [ ] 3.6 Every row's address in the record in its key column; an independent record value → displayed cell
      check that fails on planted defects; a mixed-trial safety fixture (different group counts, a missing
      denominator, explicit zeros, a stat not reported for a group).

## 4. Unit D: lookups (`classes.py`, `request.py`, `reading.py`)

- [ ] 4.1 Distinct drugs from structured intervention names; dose and schedule stripped only by a named rule.
- [ ] 4.2 Identity once, classes by RxNorm identifier; negative answers cached.
- [ ] 4.3 A declared bound on requests in flight within NLM's limit; answers in a fixed order; the release checked
      before the first round and after the last.

## 5. Unit E: documents and acceptance

- [ ] 5.1 README, AGENTS.md, SKILL.md and the MCP tool descriptions rewritten as built (the record's form, the
      Readings sheet and column dictionary, universes); documented-interface.md updated with them.
- [ ] 5.2 Acceptance: the 3-trial and 49-trial baselines re-run and a run of a few hundred trials, measured as in
      design §7; the lung-cancer universe check; the reviewer's tasks of design §6, each with its expected
      destination, evidence and unresolved cases.
- [ ] 5.3 `scripts/release_check.py` against the public repository.

## 7. Corrections (design §9, 2026-11-02)

- [ ] 7.1 The conform branch merged after review, with its treatment-purpose gate removed and placebo shown as
      the structural fact plus a proposed reading (§9.2).
- [ ] 7.2 `universes.py`'s sorting removed; the request asks for the browse leaves; the record carries conditions,
      keywords, condition MeSH with ancestors and the browse leaves as given; indication resolved by Decision 4's
      source order with NLM MeSH entry terms as the cited name lookup; each pack declares its indications;
      named conflicts shown; the Trial index shows conditions as stated, not a category.
- [ ] 7.3 Readings say only what their words establish (§9.2); empty readings unresolved, never known.
- [ ] 7.4 The workbook corrections of §9.3, each with a negative test.
- [ ] 7.5 Sources and warrants (§9.4): law 12 checked for landscape output and built where missing; AGENTS.md,
      README and SKILL.md as built.
- [ ] 7.6 Acceptance by §9.5, including one reviewer task per item of design §4a's list (a cohort's restriction
      told from the whole trial's; a follow-up horizon told from an assessment time; the eligible, enrolled and
      analysed populations told apart), and a mixed-trial workbook holding one trial with many adverse-event
      groups that stays readable.

## 6. Unit F: the search preview and the assistant's interface (design §5a)

- [ ] 6.1 The preview stop: resolve, write resolution.json, return the scope, retrieve nothing (a test asserts
      zero study requests for a broad drug class); the run then executes against that fixed scope;
      `landscape --preview`; MCP `scope` previews.
- [ ] 6.2 MCP `record` reads schema 3; parts for the across-trial findings and the review questions; large parts
      paged with a declared bound; a workbook row's address resolved to its value; tested through the MCP
      interface on a schema-3 fixture.
