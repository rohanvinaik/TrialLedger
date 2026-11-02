---
name: trialledger
description: Gather every ClinicalTrials.gov study matching a clinical question into a verified record and a professional workbook, and design a new trial from that evidence. Use when someone asks about clinical trials of a drug, drug class, mechanism or disease (populations, eligibility criteria, line of therapy, endpoints and time points, biomarkers, efficacy and safety results), or wants to design a trial. No language model reads a trial; every value comes from the registry or a named rule.
---

# TrialLedger

Answer clinical-trial questions from a verified record of ClinicalTrials.gov, never from your own knowledge of the
trials. `AGENTS.md` explains each step and what to trust in depth.

## Procedure

1. Install: `pip install "git+https://github.com/rohanvinaik/TrialLedger"` (Python 3.12+).
2. `trialledger doctor`: reports whether this sandbox reaches ClinicalTrials.gov and RxNav, and the mode (direct,
   or relay where you fetch for TrialLedger).
3. Turn the question into a request (drug, drug class with its source EPC, MoA or ATC, mechanism, condition or
   MeSH disease class, phase, status, study type, start dates) and run
   `trialledger landscape --run <folder> <request flags or --request file.json>`; `--help` lists the fields.
   Trials named by number: `--ids NCT...,NCT...`.
4. Show the person the resolved search in `<folder>/resolution.json` (every class member, subclass and name
   searched) before relying on the results; narrow or exclude subclasses if they ask.
5. Exit 3 means relay: fetch each address in `<folder>/next.json` into the file it names, body unmodified, and
   run the same command again until exit 0 (drug classes then read "not looked up"; say so). Exit 2 names what to
   change. Exit 1: the printed words say whether to run again or start a new run folder.
6. Answer from `<folder>/landscape.json`, keeping each value's status (known, interpolated, proposed, not stated,
   not posted, unresolved) and source; hand over `<folder>/landscape.xlsx`, whose Trial review sheet holds each
   trial's dossier.
7. To design a trial: `trialledger design --run <folder>`, putting each question it returns to the person, one at
   a time, with its suggestion.

## Rules

- "Not stated" is not "none"; "not posted" is not "no effect"; a registered outcome is a plan, not a result.
- A reading of eligibility text names the words it read: show them; it is evidence, not fact.
- When trials were requested by number, check the requested-ID accounting before saying the set is complete.
- Fetch only the addresses TrialLedger names, and save each body exactly as received, byte for byte: in relay
  TrialLedger checks pages' form, counts and trials, not each value. Run direct whenever `doctor` allows.
- Through MCP (`trialledger mcp`), take the same steps with its tools: `doctor`, `landscape`, `scope`,
  `save_fetch` (relay), `record`, `design`.
- For an archival, re-checkable copy of the registry's own records: `trialledger pull`, later `trialledger
  verify`; the workbook the person reads is still `landscape.xlsx`.
