# TrialLedger: a guide for the assistant using it

You have been pointed at TrialLedger to help someone with clinical trials. This guide tells you what TrialLedger
is for, how to run it, what you can trust in what it gives you, and how to answer from it. Read it before you
answer them; come back to it when they ask what TrialLedger can do or how far to trust a result. `SKILL.md` holds
the same procedure in brief.

## What TrialLedger is for

Designing a clinical trial starts with what has already been done: which trials have tested this drug, this
class of drugs, this disease; whom they enrolled and excluded; what they measured and when; what they found.
That knowledge sits on ClinicalTrials.gov, run by the US National Library of Medicine, spread across hundreds of
separate records. TrialLedger gathers it, in two layers.

**Layer one gathers the evidence.** Given a search, it collects every study on ClinicalTrials.gov that matches it
and lays out what each record says: the population; the inclusion and exclusion criteria; the line of therapy;
the outcome measures and their time points; the biomarkers and the role each plays; the efficacy and safety
results where the trial posted them; exploratory measures; links to the registry page, publications and posted
documents. No language model reads a trial, and nothing is summarized, paraphrased or inferred: each value is a
field of the registry record, or the result of a named, fixed rule applied to such fields, and says which.

**Layer two designs a trial.** Given what the person wants to test, it constructs a trial the way an experienced
designer reasons: it builds what follows by logic from what they have stated, recommends what comparable trials
have done (with the trials and numbers behind each recommendation), and offers the choices that call for
judgment one at a time, with a suggestion, for the person to decide.

## The person you are helping

Usually a clinical development professional (a physician, a clinical scientist, a pharmacologist), not a
programmer. Speak to them in clinical terms, never in TrialLedger's internal ones. They want the key context of
comparable trials quickly, and a workbook they can read, filter, annotate and share with colleagues. Hand them
the workbook; answer their questions from the record.

## How to run it

1. **Install it** in your sandbox (Python 3.12 or later):
   `pip install "git+https://github.com/rohanvinaik/TrialLedger"` (or `uv tool install` the same address).
2. **Check what your sandbox can do:** `trialledger doctor` prints, as JSON, whether this sandbox reaches
   ClinicalTrials.gov and RxNav (the National Library of Medicine's drug vocabulary), the mode a run will use,
   and the next step. In **direct** mode TrialLedger fetches for itself. In **relay** mode (a chat sandbox that
   blocks programs from the internet), you fetch the web addresses TrialLedger names, with your own fetch tool,
   and TrialLedger verifies what you saved.
3. **Turn the question into a request, and show it to the person.** The request names what to search for: a
   drug, a drug class (from the FDA's Established Pharmacologic Classes, the MED-RT mechanism-of-action classes,
   or the WHO's ATC classes), a mechanism, a condition or a disease class (a MeSH term), and the phases, statuses,
   study types and start dates wanted. Pass it as flags or as a JSON file:

   ```bash
   trialledger landscape --run egfr-nsclc --drug-class "EGFR tyrosine kinase inhibitors" --class-source ATC \
       --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED
   ```

   `trialledger landscape --help` gives every field and its accepted values. When the person names trials by
   number, pass them as `--ids NCT01234567,NCT07654321`: the same run, the same record and workbook, and the
   record accounts for every number asked (found, found under another number, or missing).
4. **Read the resolved search before anything is gathered.** TrialLedger resolves the request through named
   sources and writes the result to `resolution.json` in the run folder (the record carries it as `scope`)
   before it reads a single study: each drug class expanded into its member drugs, with every subclass it
   includes named and each member attributed to its subclass; each member searched by its own name, its base
   ingredient searched only when the class itself lists it (otherwise shown as a candidate); each drug the
   person names searched by every name RxNorm gives it; every name in both the registry's intervention name and
   its other names; each disease class searched through the registry's MeSH terms and their descendants. Show the
   person what was included. A broad class may bring in subclasses they do not expect (the FDA's "Kinase
   Inhibitor" class includes HER2 and EGFR antibodies through its subclasses); the request can exclude a subclass,
   or all of them. If the request cannot be resolved (a class the source does not hold, a lookup that failed, a
   search too long for the registry), TrialLedger stops, names why, and says what to change; nothing is searched.
5. **Run it to completion.** The command ends with an exit code and plain words saying what happened:
   - **0**: complete. The run folder holds `landscape.json` and `landscape.xlsx`.
   - **3**: waiting for you (relay mode). `next.json` lists each web address to fetch and the file to save it
     as. Fetch each one exactly as named, save the body unmodified into the named file, and run the same command
     again. Repeat until it ends with 0. Fetch nothing else, and never edit a saved body. In relay mode
     TrialLedger does not look up the gathered trials' drug classes (that would be hundreds of addresses): each
     reads "not looked up", never "no class", and the record says so. Tell the person, and prefer a sandbox that
     reaches the internet when drug classes matter.
   - **2**: refused or stopped, with the reason and what to change; usually a changed request in a new run
     folder.
   - **1**: failed; nothing was written as the record. The printed words say which kind: if a service did not
     answer, run the same command again later and it resumes; if the registry or RxNav changed while being
     read, start a new run folder with the same request.
   Re-running the same command is always safe: it resumes where it stopped, and a finished run run again changes
   nothing.
6. **Answer from `landscape.json`, and hand over `landscape.xlsx`.** The workbook is the person's: a Read me, a
   Trial index (one row per trial), a Trial review (each trial's complete dossier, top to bottom), listings for
   eligibility, outcomes and efficacy, biomarkers and safety, the across-trial findings, and an evidence
   register.
7. **Design a trial when asked:** `trialledger design --run <folder>` takes what the person wants to test and the
   evidence the run gathered, and returns one question at a time, the decision that settles the most first, each
   with a suggested answer and what accepting it settles. Put each question to the person in plain words; record
   their answer, or accept every suggestion at once if they ask. The design is written as `design.json` and
   `design.xlsx`, every element marked as deduced (with the premises it rests on), recommended (with the trials
   and numbers behind it), or chosen by the person.

When the person edits the workbook (correcting a reading, answering an open question), `trialledger edits --run
<folder>` reads their edits back as their own assertions, never as registry facts, and re-checks what depends on
them.

## What you can trust, and why

Every value in `landscape.json` is an envelope: the value, its **status**, its **source** (the registry field or
the rule), the **rule** that read it if any, a **note**, and the study's registry **link**. The record's own
`statuses`, `envelope` and `fields` sections define each status and field; read them. Four questions, each with
its own answer:

1. **Did the records arrive intact?** Yes, and this is checked, not assumed. A retrieval follows every page to
   the end, its count must equal what the registry reported, no study may be repeated, the registry's JSON and
   its own spreadsheet export must name the same studies, and the registry must not have changed while it was
   read. If any of that fails, nothing is written. Every trial requested by number is accounted for: found, found
   under another number (the registry also matches a trial's alias numbers), missing, repeated, or not a valid
   number. A completed run is not proof that every requested trial was found: when the person asked for trials
   by number, read the requested-ID accounting before telling them the set is complete.
2. **Does the record faithfully reflect them?** Yes, for what the registry states (status **known**: a field of
   the record, or a direct rule over one). Every value carries a fingerprint tying it to the record and the code
   that derived it; the workbook is read back and checked cell by cell before it is released; a value a cell
   cannot hold exactly says why and where it is, rather than being cut or rounded.
3. **Does it read the clinical meaning correctly?** Only as far as each reading's evidence goes. Readings of
   eligibility text (an age limit, a laboratory threshold, a performance status, a prior therapy, a condition)
   and of a trial's setting are made by named rules, each naming the words it read, so you and the person can
   check them; some are known to be imperfect. A reading is evidence to show with its source words, never a fact
   to assert. Analysis across trials (common criteria, mechanism-linked exclusions, untried combinations, pairs of
   trials differing in one choice) is evidence to weigh: **proposed** when it holds even under the least
   favourable reading of silent records, **unresolved** when those records could reverse it.
4. **Is it more accurate than a professional's manual transcription?** That is not claimed. TrialLedger is built
   so that its completeness, reproducibility and traceability can be checked, which a manual spreadsheet's
   cannot; whether its field-level accuracy exceeds a trained professional's is an empirical question.

The statuses you will meet: **known**; **interpolated** (follows from a default rule, not from the record alone);
**proposed** (a pattern or rule suggested by evidence, not established); **not stated** (the record says nothing;
never "none"); **not posted** (the trial posted no results; many trials never do); **unresolved** (TrialLedger
could not settle it, and says why).

`trialledger pull` is the archival copy: it saves the registry's records exactly as sent, the registry's own
spreadsheet byte for byte, and two certified workbooks laid out field by field, and `trialledger verify` later
re-derives every value and names anything that no longer matches. Run it beside `landscape` when the person
needs the registry's records preserved and re-checkable, for instance values they will cite or copy into a
protocol; the workbook you hand them to read is still `landscape.xlsx`. `verify` proves that each value derives
from the saved record by the code that wrote it; it does not prove that a rule reads a criterion correctly.

## How to answer

- Answer from the record. Never answer about a trial from your own knowledge or from reading its registry page
  yourself, and say when the record does not contain the answer.
- Keep each value's status when you report it, and for anything read, interpolated or proposed, show what it
  rests on (the criterion's words, the rule, the trials and counts).
- "Not stated" is not "none"; "not posted" is not "no effect". A registered outcome is what a trial planned to
  measure, never evidence that it worked. A trial without posted results may still have a results publication
  the sponsor linked: say so.
- The line of therapy is the setting the trial registered, not today's standard of care.
- Point the person to the workbook for detail: the Trial review sheet holds each trial's dossier, the listings
  compare across trials.

## How to find out more

- `trialledger <command> --help`: what each command does, its options, and what each exit code means.
- `landscape.json`'s `statuses`, `envelope` and `fields` sections: what every status and field means.
- `README.md`: the project explained for clinical readers.
- `trialledger mcp` serves `doctor`, `landscape`, the record and `design` over the Model Context Protocol.
- `openspec/changes/`: the design of each part, in plain language.

If you are changing TrialLedger's own code rather than using it, read `DEVELOPING.md`.
