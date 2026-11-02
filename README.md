# TrialLedger

**Tell your assistant which clinical trials you're interested in. Get a reference spreadsheet you can work
from, with a matching evidence record for follow-up questions.**

Name specific trials, or describe a group by drug, drug class, condition, phase, status or study type.
TrialLedger gathers their ClinicalTrials.gov records into one formatted workbook, with a dossier per study
and shared listings. Your assistant can then take you to the exact eligibility, endpoints, results or safety
information behind an answer.

For example:

- “Give me the reference sheets for IPASS and ARCHER 1050.”
- “Find completed Phase 3 EGFR inhibitor studies in non-small cell lung cancer.”
- “Show me who could enroll, the outcome time points and the reported safety by treatment group.”

## What you receive

**`landscape.xlsx`** is the clinical reference workbook. Start with Trial index and Trial review, then explore
eligibility, interventions, planned outcomes, posted results, statistical analyses, baseline, participant
flow, groups and safety. Numbers keep their study groups, denominators, units and reporting periods.
Observational and expanded-access studies retain their own applicable details.

**`landscape.json`** contains the matching selected clinical evidence your assistant uses for questions.
Complete registry responses are also retained. The workbook and record preserve source wording; the assistant
can show the evidence behind an answer without reconstructing a registry page from memory.

The search is shown before gathering: which drugs a class includes, the condition and the filters. If a
name is ambiguous, your assistant helps you select the intended source-backed meaning. Requested trial
numbers are accounted for, including any that were not found. An interrupted run can resume.

The report copies registry facts and applies fixed, named transformations. It keeps planned outcomes
separate from posted results and makes missing information visible. It does not invent a treatment setting,
adverse-event grade, current standard of care or a new study's efficacy target when the source does not
establish one. Source links remain available for further investigation.

## Work through a design question

TrialLedger also has working symbolic reasoning tools that your assistant operates with you. You can ask:

- “Does our draft rule out ECOG 2 patients? Which restriction decides that?”
- “Do these criteria contradict each other?”
- “What treatment settings could these lung cancer premises support?”
- “How often is this exclusion documented in the comparison set we chose?”
- “Which trials differ on this design feature? What's unusual in this set?”

Your assistant restates the material premises together in clinical words, checks ambiguities with you and
runs the appropriate operation. You get the answer, its deciding premise or counts, and any open issue that
changes its meaning. Change a premise and rerun whenever you like; the source record stays intact.

For example, if your draft requires adults aged 18 or older, a 16-year-old fails that age restriction.
A minimum age of 65 is not required: the restriction allows adults on both sides of 65. That answers the
age question without claiming that every requirement for a particular patient's enrollment has been checked.

These operations compute consequences from the premises supplied. Your assistant distinguishes what the
registry reports, what the program computes and its own clinical reading. Your confirmation establishes a
premise for the analysis; it does not turn an interpretation into a registry fact. Supported defaults and
suggestions remain visible as such.

The complete automated trial writer—from a brief and evidence to a warranted protocol—is designed and
partly built. Its working reasoning tools are available now; automatic source-to-premise compilation and
complete brief-to-protocol writing are not yet integrated. See the [full design](openspec/changes/add-design-synthesis/design.md)
and [theory](docs/THEORY_OF_THE_CASE.md) for the component map and remaining work.

## Getting started with your assistant

Give your assistant this repository and your clinical request. It checks whether its environment can run
Python, write report files, access the required sources and deliver the workbook. When those capabilities
are available, it handles installation, the search preview and retrieval. If something essential is missing,
it should explain the specific gap and the next practical step before promising a workbook.

A repository link alone does not install the program or give a chat app execution or network access.
If you have a technical colleague configuring a local assistant, the details are below. Assistants should
read [AGENTS.md](AGENTS.md) or [SKILL.md](SKILL.md); contributors should read [DEVELOPING.md](DEVELOPING.md).

<details>
<summary>Installation, local commands and assistant integration</summary>

Python 3.12+ and writable report storage are required. Install in the assistant's own environment:

```bash
pip install "git+https://github.com/rohanvinaik/TrialLedger"
trialledger doctor --run egfr-nsclc
trialledger landscape --run egfr-nsclc --drug-class-id L01EB --class-source ATC \
    --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED --preview
```

Inspect the resolved scope, then repeat without `--preview`. ATC `L01EB` is the source class used for this
example; the preview shows its current members. Ordinary class phrases can return source-catalogue choices;
select a class explicitly, even for a sole suggestion, then preview its ID in a new run. Specific trials use:

```bash
trialledger landscape --run my-trials --ids NCT00322452,NCT01774721
```

These are IPASS and ARCHER 1050. `landscape --help` lists request fields, including dates and study types;
request JSON can also exclude selected subclasses. A repeated request resumes, while a changed request needs
a new run folder. Exit 0 means complete/previewed; 3 awaits relay responses; 2 names a refusal/stop; 1 gives
failure/retry advice. Completion does not mean every requested identifier was found.

Prefer direct mode, in which TrialLedger fetches itself. Relay bridges missing network access only: it still
requires execution, report storage and access to complete response bodies. Fetch only the addresses in
`next.json`, saving each full response byte-for-byte unchanged. Excerpts, copied tables or reconstructed JSON
cannot substitute. Relay resolves search terminology but skips gathered-study drug enrichment. The harness
checks response structure and identity, not every value against a second live copy.

`trialledger verify FOLDER` replays retained reporting inputs and checks the record and workbook, including
formatting and links, under the writing version. It establishes reproducibility, not registry truth.
`trialledger pull` separately retains complete registry JSON/CSV with archival workbooks.

For an assistant client that supports local MCP servers:

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

Use absolute paths. Tools are doctor, scope, landscape, save_fetch, record and reason. The assistant handles
record paging: at most 50 entries and a default 24,576-byte record reply. Oversized nested values return exact
addresses to follow; long strings have lossless text continuation. Saved records are complete. These are
conversation-output limits, not a limit on the whole process's memory or a change to requested study scope.

Reasoning uses `trialledger reason --request FILE` or MCP `reason(request)`. Start with
`{"operation":"describe"}` for an overview. Ask for `{"operation":"describe","view":"entailment"}`,
`coordinates` or `corpus` for the relevant formats, guide and runnable example. Views `worked_session` and
`full` retain the demonstration and complete manual on demand.

Entailment checks supplied scoped premises; coordinates uses the explicit NSCLC domain; corpus computes
statement rates with silence bounds, class associations, rarity, occupancy and one-feature comparisons.
Expectation-deviation classification remains a supporting Python utility. Derivational significance is
specified for future implementation; it is distinct from today's corpus rarity. The operations do not fetch
sources or alter reports. The assistant can save a full response separately as `reason-result.json` for reuse.

</details>

MIT; see [LICENSE](LICENSE).
