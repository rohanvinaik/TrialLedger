# TrialLedger

**TrialLedger doesn't make your clinical decisions. It finds them.**

Much of designing a trial is documentary and logical work: finding what comparable trials did, copying it out
accurately, and working out what a draft restriction does and doesn't allow. TrialLedger, run by your
assistant, does that work and hands you the choices that genuinely need your clinical judgment, each with its
evidence and its consequences worked out.

For a draft lung cancer trial compared with IPASS and ARCHER 1050, one decision looks like this:

- **Evidence:** ARCHER 1050 requires ECOG performance status 0–1. IPASS's registry entry doesn't say; its
  linked publications are the place to check.
- **Your decision:** What performance-status range do you intend?
- **Consequence:** Widening your draft from ECOG 0–1 to 0–2 moves ECOG 2 patients from excluded to allowed.
- **Still open:** Your draft says nothing about brain metastases. ARCHER 1050 excludes any history of them.

Your attention goes to the decisions, with the evidence assembled and the consequences computed rather than
guessed. The evidence comes from the studies you care about: TrialLedger gathers their ClinicalTrials.gov
records into a readable reference workbook and a matching evidence record, so you can examine who could
enroll, what was measured, when it was assessed, and what results and safety information were reported.

Then ask: “What have these studies done here—and what would happen if we chose something different?”

Your assistant brings the relevant evidence into the conversation, helps make your intended choices
explicit, and runs TrialLedger's comparison and reasoning tools. You can examine documented patterns, check
whether your draft restrictions conflict, explore alternatives, and revise a choice with its consequences
in view.

You make the clinical judgments. TrialLedger's job is to make them visible: what is already settled by your
choices, what contradicts itself, what is genuinely yours to decide, and what the evidence cannot tell you. The reference workbook is useful on its own,
and it provides the evidence base for a continuing design conversation.

## A design session in practice

Suppose you're sketching an NSCLC trial and ask:

> “We need an age cutoff—and what about CNS metastases or prior treatment? What have other trials like
> these used?”

Here is how the conversation can develop. The draft choices below illustrate the workflow; they are not
findings from a particular trial or a recommended protocol.

**1. Look at the evidence.** Your assistant gathers the trials you choose, shows the search scope, and reads
the relevant population fields and exact eligibility passages. You agree which features and trials to
compare. TrialLedger can then count documented restrictions while keeping missing information visible.
“Eight studies document this restriction; two don't say” is different from “this is standard practice.”
It can also show restrictions documented more often within a selected drug class, unusual observations,
and trial pairs that differ on one feature under the comparison you defined.

**2. Make a choice precise.** You say, “Let's use adults 18 or older, ECOG 0–1, and EGFR exon 19 deletion or
L858R.” Your assistant might ask: “If L858R occurs alongside another mutation, should that person qualify?”
That question makes your intended eligibility decision explicit. The assistant records your agreed reading
for the analysis.

**3. Check the consequences.** Ask, “Does that rule out ECOG 2?” or “Do these restrictions contradict each
other?” Your assistant runs the reasoning tool and explains the answer with the premise that decides it.
For supported NSCLC questions, it can also examine which treatment settings remain possible, showing where
a result uses a default or leaves you a choice.

**4. Revise the design.** Add a cohort, change a restriction or reconsider a comparison. Your assistant
updates the working choices and reruns the relevant checks. You can see what follows from the revised
choices, what remains open and which evidence informed them. The original registry record stays intact.

The session leaves you with a **decision list**: each choice you made or still face, the evidence behind it
and what it changes, alongside the source workbook and record. Your assistant can save the list and the
structured checks behind it, so you can revisit a decision, change it and see its consequences again.

Today, your assistant reads trial text with you, makes the agreed choices explicit and runs the checks;
TrialLedger computes the supported comparisons and logical consequences. The complete automated trial
writer is designed and partly built. Automatic conversion of trial text into reasoning inputs and complete
protocol writing are not yet integrated. Its working tools are available now for your own design
and comparison work. See the [full design](openspec/changes/add-design-synthesis/design.md) and
[theory](docs/THEORY_OF_THE_CASE.md) for the component map.

## What you receive

**`landscape.xlsx`** is the clinical reference workbook. Start with Trial index and Trial review, then explore
eligibility, interventions, planned outcomes, posted results, statistical analyses, baseline, participant
flow, groups and safety. Numbers keep their study groups, denominators, units and reporting periods.
Observational and expanded-access studies retain their own applicable details.

**`landscape.json`** contains the matching selected clinical evidence your assistant uses for questions.
Complete registry responses are also retained. The workbook and record preserve source wording, with links
back to the evidence behind an answer. Planned outcomes remain separate from posted results, and missing
information stays visible. A source link gives you a place to investigate further when an answer needs
information beyond the registry.

You can also stop at the reference sheet. For example:

- “Give me the reference sheets for IPASS and ARCHER 1050.”
- “Find completed Phase 3 EGFR inhibitor studies in non-small cell lung cancer.”
- “Show me who could enroll, the outcome time points and the reported safety by treatment group.”

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
