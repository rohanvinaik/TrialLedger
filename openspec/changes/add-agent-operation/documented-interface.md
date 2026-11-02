# What README.md, AGENTS.md and SKILL.md promise (2026-11-01)

The founder's direction (paraphrased): the documents describe the system as built, never as provisional, so they
do not drift; the build delivers exactly what they describe. Each line below is a promise the documents make;
it is ticked when the code delivers it, and a promise the build cannot keep is changed in the documents and here
together, never left standing.

## Install and capability

- [ ] `pip install "git+https://github.com/rohanvinaik/TrialLedger"` installs a working `trialledger` on Python 3.12+
      (and `uv tool install` the same address); verified by scripts/release_check against the public repository.
- [ ] `trialledger doctor` reports reach of ClinicalTrials.gov and RxNav as JSON, the mode (direct or relay), and a
      next step naming `trialledger landscape`.

## trialledger landscape

- [ ] `--run DIR` with request flags (`--drug`, `--drug-class NAME --class-source EPC|MoA|ATC`, `--condition`,
      `--condition-class`, `--phase`, `--status`, `--study-type`, `--start-from`, `--start-to`, a way to exclude a
      drug class's subclasses) or `--request FILE.json`; `--help` lists every field and its accepted values.
- [ ] The README example runs: `--drug-class "EGFR tyrosine kinase inhibitors" --class-source ATC
      --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED`.
- [ ] `--ids NCT...,NCT...`: trials by number through the same run, the requested-ID accounting in the record.
- [ ] `resolution.json` (the record's `scope`) is written before any study is read: each class's members with every subclass named and each
      member attributed to its subclass; each drug by every RxNorm name, searched in intervention name and other
      names; each disease class by MeSH term and descendants; stops named with what to change.
- [x] Exit codes 0 complete, 3 waiting for relay fetches (`next.json`), 2 refused or stopped with advice, 1 failed
      with nothing written as the record (the words saying whether to run again or start a new run folder);
      each printed with plain words; re-running resumes and is safe. (2026-11-01, `operate.run_exit`.)
- [x] Relay: fetch each address in `next.json` into the file it names, body unmodified; nothing else fetched;
      drug classes read "not looked up" and the record says so. (2026-11-01, `operate.py`.)
- [ ] `landscape.json`: every value an envelope (value, status, source, rule, note, link); `statuses`,
      `envelope` and `fields` sections; requested-ID accounting when trials are requested by number.
- [ ] `landscape.xlsx` as workbook-design.md specifies: Read me, Trial index, Trial review, Eligibility,
      Outcomes and efficacy, Biomarkers, Safety, Across-trial findings, Evidence register; "Not stated", "Not
      posted", "Unresolved" in the cell; a sponsor-linked results publication beside "Not posted".

## Layer two and the rest

- [ ] `trialledger design --run <folder>`: one question at a time, the decision that settles the most first, each
      with a suggested answer and what it settles; accept-all; `design.json` and `design.xlsx`, every element
      deduced (with premises), recommended (with trials and numbers) or chosen (add-design-synthesis).
- [ ] `trialledger edits --run <folder>`: the person's workbook edits read back as their assertions, never as
      registry facts, and what depends on them re-checked (6.1).
- [ ] `trialledger mcp`: doctor, landscape, the record and design over the Model Context Protocol (6.2).
- [ ] `trialledger pull` and `trialledger verify` as described (built).
- [ ] The README's checks: a completed study with an estimated completion date, an adverse event affecting more
      people than were at risk, raised as queries (built: checks version 2).
