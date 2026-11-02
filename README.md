# TrialLedger

**ClinicalTrials.gov records in a readable workbook, with every reported value traceable to its source.**

Give TrialLedger a search or a list of study numbers. It gathers the registry records and presents their design,
population, eligibility, interventions, planned outcomes, posted results and safety in one workbook. Your
assistant runs it, answers from the saved record and gives you the spreadsheet. No language model abstracts the
studies or supplies trial facts.

- **Layer one — trial reference sheets (available).** Ask for specific trial numbers or a subset by drug,
  drug class, condition, phase, status, study type or date. Receive one formatted spreadsheet and matching
  JSON, with a dossier per study and shared listings. The content is registry facts and strictly warranted
  direct derivations; your assistant answers from that evidence record.
- **Layer two — new-trial designer (partially built).** Intended to construct a new trial from scratch from
  your brief and layer-one evidence through symbolic reasoning, distinguishing deductions, proposals and
  choices that require your judgment. Some foundations exist; the complete design workflow is not available.

## What you receive

`landscape.xlsx` is the review workbook; `landscape.json` is the corresponding evidence record. Start with the
Trial index and study-by-study Trial review, then use the eligibility, outcome, results, statistical-analysis,
baseline, participant-flow, group and safety listings. A brief field dictionary identifies the source of the
reported fields. Listing addresses let your assistant retrieve the same evidence you see.

The report preserves the registry's wording and values. It keeps observational study populations, sampling,
follow-up and specimen information, and expanded-access types and availability, alongside interventional study
design. Enrollment count and actual/anticipated type remain separate. Results retain their group, analysis
population, denominator, unit and time frame. Safety retains affected participants, participants at risk and
event counts, with reporting period and threshold.

Eligibility text may be divided at unambiguous headings and bullets for readability; the original wording and
source locations remain available. That division does not interpret the criteria or decide whom they apply to.
Other direct operations include registry labels, source-presence and results states, counts and source links.
Drug lookup evidence, where available, names its source; a lookup failure is distinct from a negative response.

## How far the report goes

Layer one reports registry facts and strictly warranted direct derivations. It does not rank key criteria, infer
treatment setting, identify biomarker roles, decide which trials are comparable or make clinical recommendations.
There is no ordinary-report MeSH enrichment or disease classification. Exact eligibility, descriptions and
outcomes remain available for a professional to read; publications and documents are linked.

A registered outcome is a plan; a posted result is an observation. Eligible, enrolled and analysed populations
are different. An explicit empty event list is not proof of zero harms. **Not stated** is not none; **not
posted** is not no effect; **unresolved** or malformed input is not a negative finding. Seriousness does not
establish adverse-event grade. Current care, comparative benchmarks and new planning targets require more than
transcription of a registry record.

TrialLedger checks retrieval completeness and spreadsheet fidelity, and can replay a saved report offline.
Those checks establish preservation and reproducibility, not that the registry is correct or that a clinical
interpretation is correct. Coverage is checked across study types and source shapes; a passing collection of
examples does not establish every clinical situation.

## Use it through your assistant

Point your assistant at this repository and ask, for example:

> Using TrialLedger, find completed Phase 3 trials of EGFR tyrosine kinase inhibitors in non-small cell lung
> cancer. Show me the search before gathering the records, then give me the workbook.

The assistant previews the resolved drugs, class members/subclasses, disease search and filters before gathering
studies. A shared search does not establish that the resulting studies are clinically comparable.

For a local installation, Python 3.12 or later is required:

```bash
pip install "git+https://github.com/rohanvinaik/TrialLedger"
trialledger doctor --run egfr-nsclc
trialledger landscape --run egfr-nsclc --drug-class "EGFR tyrosine kinase inhibitors" --class-source ATC \
    --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED --preview
```

Read the preview and `resolution.json`, then repeat without `--preview` to gather that fixed search. For study
numbers, use `trialledger landscape --run my-trials --ids NCT04852770,NCT01827384`. `landscape --help` lists the
request fields. A request file can exclude class subclasses through `drug_class.subclasses`: `"exclude"` or a
list of subclass IDs, rather than the default `"include"`. A changed request uses a new run folder.

`doctor` checks ClinicalTrials.gov and RxNav reachability. In **direct** mode the program fetches for itself.
In **relay** mode the assistant fetches each exact address in `next.json`, saves its unchanged response to the
named file and repeats the command. Relay checks form, counts, order and study identities, not every value
against the live registry. Never retype, shorten or correct a body. Gathered-study drug enrichment is not
performed in relay mode; that means not looked up, not no class.

Exit **0** means complete, or previewed when requested; **3** means relay fetches awaited; **2** names a refusal
or stop; **1** names a failure and retry advice. Repeating the same request resumes safely. When studies were
requested by number, inspect the requested-ID accounting: a completed retrieval can still include missing IDs.

`trialledger verify FOLDER` replays a saved landscape offline from retained inputs under its writing code and
compares the record and workbook, including formatting and links. Missing or changed evidence is named, never
repaired. Older folders require their writing version. `trialledger pull` separately saves the registry's raw
records/CSV with certified archival `review.xlsx` and `record.xlsx`.

## MCP

`trialledger mcp --root /absolute/path/to/trialledger-runs` serves **doctor**, **scope**, **landscape**,
**save_fetch** and **record** over standard input/output. Preview with `scope`, gather with `landscape`, follow
relay requests exactly, and answer with `record`, including a workbook row's address. Lists and objects are
paged, at most 50 entries per call.

```json
{
  "mcpServers": {
    "TrialLedger": {
      "command": "/absolute/path/to/trialledger",
      "args": ["mcp", "--root", "/absolute/path/to/trialledger-runs"]
    }
  }
}
```

Use absolute paths; the client launches without a shell and does not expand `~`. Assistants follow
[AGENTS.md](AGENTS.md) or [SKILL.md](SKILL.md); contributors read [DEVELOPING.md](DEVELOPING.md).

## Layer two

Layer two's purpose is to construct a new trial from scratch using your design brief and the gathered evidence.
It is partially built: reasoning and existing-trial analysis foundations are present, but the integrated
brief-to-new-trial designer is unfinished. Its intended output distinguishes deductions with their premises,
proposals with their evidence, and decisions made by the person. This is symbolic reasoning, not LLM-generated
trial design. The design is documented in [add-design-synthesis](openspec/changes/add-design-synthesis/proposal.md)
and [THEORY_OF_THE_CASE.md](docs/THEORY_OF_THE_CASE.md).

These operations remain separate from layer-one reporting. The current CLI/MCP has no `design` or `edits`
operation or automatic workbook-edit import. A developer tool's `design.xlsx` analyses existing trials; it is
not a newly designed protocol.

MIT; see [LICENSE](LICENSE).
