# Tasks: refine-landscape-record

## 0. Base and contract (sequential; nothing in 1-5 starts before 0.4)

- [ ] 0.1 The push gate's secret scan: the hex-digest detector removed (the project's lowercase hex digests are
      fingerprints, never credentials), the other detectors kept, the digest-recognition code it needed deleted.
- [ ] 0.2 The acceptance harness (add-agent-operation 7.1) on main.
- [ ] 0.3 relation-kinds (add-scoped-reasoning 1.1-1.2) rebased and on main (landscape.json schema 2).
- [ ] 0.4 The contract commit: `TrialLedger/contract.py` (the schema-3 field table: field, API path or rule,
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
- [ ] 1.6 schema 3: schema check, statuses, `fields`, RULE_VERSIONS (the universe table's version).

## 2. Unit B: universes (`universes.py`, `coherence.py`, `semantics/loader.py`)

- [ ] 2.1 The universe table and `assign(study)`: the three sources of design §3, each finding recorded; one,
      several, none, undecidable.
- [ ] 2.2 Per-universe coordinates and relations; each pack's requirements; `resolve(evidence, universe)`.
- [ ] 2.3 The loader's optional `universes` key (absent from the canonical form when absent).
- [ ] 2.4 Named fixtures: the PTSD trial (general), the lymphoma/CLL immunotoxin (haematologic), the solid-tumour
      basket without condition MeSH (solid, from its free-text condition), an osimertinib trial whose condition is
      "Progression Free Survival" (solid, from its intervention), a supportive-care trial in cancer patients (no
      setting).

## 3. Unit C: the workbook (`readout.py`)

- [ ] 3.1 The sheets of design §4, against fixture records of schema 3.
- [ ] 3.2 Display dictionaries for every code; labelled readings; the Readings sheet and the column dictionary in
      place of the per-cell evidence register.
- [ ] 3.3 Safety as term × groups; Posted results long by group; Groups, Baseline, Participant flow and
      Statistical analyses listings.
- [ ] 3.4 Read-back certification and deterministic bytes kept; continuation sheets past the row limit.

## 4. Unit D: lookups (`classes.py`, `request.py`, `reading.py`)

- [ ] 4.1 Distinct drugs from structured intervention names; dose and schedule stripped only by a named rule.
- [ ] 4.2 Identity once, classes by RxNorm identifier; negative answers cached.
- [ ] 4.3 A declared bound on requests in flight within NLM's limit; answers in a fixed order; the release checked
      before the first round and after the last.

## 5. Unit E: documents and acceptance

- [ ] 5.1 README, AGENTS.md, SKILL.md and the MCP tool descriptions rewritten as built (the record's form, the
      Readings sheet and column dictionary, universes); documented-interface.md updated with them.
- [ ] 5.2 Acceptance: the 3-trial and 49-trial baselines re-run and a run of a few hundred trials, measured as in
      design §7; the lung-cancer universe check; the workbook opened and read as a reviewer would.
- [ ] 5.3 `scripts/release_check.py` against the public repository.
