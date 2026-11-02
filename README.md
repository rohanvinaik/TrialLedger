# TrialLedger

**Get a source-backed clinical trial workbook, or use symbolic reasoning to examine a design question.**

Tell your assistant which trials you want, or describe the drug/class, condition and filters. TrialLedger
gathers the ClinicalTrials.gov records and returns one formatted workbook (`landscape.xlsx`) with a dossier
for each study and shared listings, plus matching JSON (`landscape.json`). The workbook is the clinical
reference sheet; the JSON is its matching source-backed record. The assistant operates the registry search
and answers from that record rather than improvising facts from registry pages.

That is **layer one**, the available reference-sheet operation. **Layer two** is a designed automated
trial-writing workflow. It is intended to start from your brief and evidence, work out the resulting
constraints, compare relevant trials, propose choices for your review and write a protocol with its basis.
The full workflow is partly built. Separate reasoning operations already let you check what follows from
explicit requirements, explore supported NSCLC design options and compare stated features in a defined set.
These operations are useful on their own, even though automatic reading of trial text and complete
brief-to-protocol writing are not yet integrated.

You can use those working analyses for your own clinical-development work now, independently of asking for
a complete new trial. Choose the question; your assistant explains the applicable operation, helps you
structure and confirm material premises, runs it and returns the reasoning with assumptions and open items.
You decide how to use the result. Keep its reusable structured response beside the separate source record.

## Questions you can explore now

Your assistant can help you start with the study evidence, then use the separate reasoning tools when you
have design premises or a comparison set to examine.

| Ask in clinical terms | What is available |
|---|---|
| “Give me a reference sheet for these trials.” | Search or named-study retrieval, a dossier per study, shared listings and the matching source-backed record. |
| “Show me who could enroll, what was measured when, and the reported benefits and harms.” | Exact criteria and population details, planned versus posted outcomes, and group-specific results/safety with denominators, units and periods. |
| “Do these drug names resolve to the same thing, and which classes does NLM give them?” | Retained canonical identities, related ingredients, class assertions and alias conflicts; unresolved identity is shown. |
| “Does this record disagree with itself?” | Direct registry checks such as ordered dates, declared arm/intervention links and affected-versus-at-risk counts, with both values retained. |
| “Given our population restrictions, does this option still fit?” | Scoped logical entailment, refutation or an undetermined result, with the supplied premises that support it. |
| “Given this NSCLC treatment history, which settings remain possible?” | The existing coordinate rules, showing what follows from the inputs separately from defaults, proposals and conflicts. |
| “How often is this criterion documented, and what does missing detail leave open?” | Counts, statement rates and silence bounds in a supplied, explicitly represented comparison set. |
| “Is this documented pattern more frequent in one drug class, or unusual in this subgroup?” | Proposed class associations and conditional observation rarity with support counts; these do not establish a mechanism or clinical absence. |
| “Where are the gaps, or which studies differ on one chosen design feature?” | Setting-by-class occupancy and near-miss pairs under the declared comparison; unknown membership stays unknown and a pair is not proof that two trials are otherwise identical. |

The last five questions use confirmed, structured premises. The assistant first agrees with you what a
restriction means and which studies/features to compare. It does not silently turn free-text criteria into
facts. For example: is “no prior therapy” about advanced disease, and does the restriction apply to every
participant or one cohort? A result can then say “this follows from your brief,” “this uses an assumption,”
or “this remains open,” with its basis.

The complete automated trial writer is the designed next integration of these parts: population and
eligibility, interventions/comparator, endpoints and biomarkers, assessments/schedules, efficacy targets and
sample-size inputs, safety, exploratory procedures and warranted protocol language. The current tools can
explore supported parts of that design; they do not yet generate the complete protocol automatically.

## The reference sheet

`landscape.xlsx` and `landscape.json` present the same selected clinical evidence. Start with the Trial index
and each study's Trial review, then use eligibility, planned and posted outcomes, statistical analyses,
baseline, participant-flow, group and safety listings. Source links and record addresses connect the sheet
to the evidence used for an answer. Complete registry responses are retained separately; the clinical JSON
is a described selection, not a claim to contain every raw registry field.

The output preserves exact eligibility and description text, population, interventions, measures and time
frames, and posted efficacy and safety data with their own groups, denominators, units and periods.
Observational populations, sampling, follow-up and specimens and expanded-access details keep their own
structure. Supplied results-submission, delay and waiver information and direct consistency checks accompany
the relevant source facts. Drug lookups use canonical source identities and retain conflicts rather than
select the first successful alias.

A registered outcome is a plan, not a result. Not stated is not none; not posted is not no effect; an empty
event list does not establish zero harms. Seriousness does not establish grade. The sheet makes the evidence
available for clinical interpretation; it does not silently rank key criteria, assign biomarker roles,
infer current care or propose a new efficacy target. Those belong to a separately identified reasoning task.

## A clinical-development example

For example, ask: “I’m reviewing completed Phase 3 EGFR inhibitor studies in non-small cell lung cancer.
Gather the reference workbook, then show me the exact eligibility and the reported safety by study group.”
The assistant checks for Python execution, report-folder file access, network access and the ability to deliver
the workbook. If Python execution and report-folder writing are available, it installs TrialLedger into its
own Python 3.12+ environment, runs `doctor`, previews the resolved search and gathers that fixed scope. A
repository link alone does not establish that the assistant can install software or reach ClinicalTrials.gov.
Relay bridges missing network access only: it still requires Python execution and report-folder writing,
plus the ability to fetch each complete response. If execution or report writing is unavailable, relay cannot
make a local run possible.

For the class search, the assistant translates “EGFR inhibitors” to a source-backed candidate and checks its
ATC class name and ID. If the wording is unresolved, it shows source candidate names and IDs for you to
confirm, even when there is only one suggestion. It expands only the selected class in the next preview,
where you can inspect the member drugs and
filters. The example uses ATC class `L01EB`; it describes a search, not a claim that particular matching
studies were retrieved. No study IDs are assumed.

In direct mode, the assistant can fetch from the resolved scope itself. In relay mode, TrialLedger still
needs the search terminology to resolve the requested scope, but it skips post-retrieval drug enrichment.
Each relay fetch must be the complete response body saved byte-for-byte as requested; a browser excerpt,
copied table or shortened response cannot substitute. Relay validates structure and identity, not every live
registry value.

If the evidence raises a design question, the assistant can then use a separate symbolic operation for your
own work—for example, “Given these population restrictions, does this proposed cohort still fit?” It first
confirms which source passage or user premise applies to which participants, then reports what follows, what
depends on a chosen assumption and what remains unresolved. This does not change the reference workbook or
turn free text into an automatically extracted fact.

The local commands, for an assistant environment with those capabilities, are:

```bash
pip install "git+https://github.com/rohanvinaik/TrialLedger"
trialledger doctor --run egfr-nsclc
trialledger landscape --run egfr-nsclc --drug-class-id L01EB --class-source ATC \
    --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED --preview
```

Read the preview and `resolution.json`, then repeat without `--preview`. Specific trials use
`trialledger landscape --run my-trials --ids NCT04852770,NCT01827384`. `landscape --help` lists every request
field. A changed request needs a new run folder; a repeated request resumes. Class requests can explicitly
exclude subclasses through request JSON. Search expansion is shown, never hidden.

`doctor` chooses **direct** mode when the program can fetch, or **relay** when each exact response in
`next.json` must be fetched and saved unchanged. Relay checks form, counts, order and identities, not every
value against the live registry; never retype, shorten or correct a response. Gathered-study drug enrichment
is not performed in relay mode: not looked up is not no class.

Exit 0 means complete or previewed; 3 awaits relay responses; 2 names a refusal/stop; 1 gives failure/retry
advice. Requested-ID accounting still needs review: successful retrieval can include missing trial numbers.
Malformed source types produce a named refusal rather than a fabricated typed report; original evidence stays
retained.

`trialledger verify FOLDER` replays retained inputs and compares the report and workbook, including formatting
and links, under the writing version. It proves reproducibility, not registry truth or clinical interpretation.
`trialledger pull` separately preserves complete registry JSON/CSV and certified archival workbooks.

## The symbolic designer

The current separate operation is `trialledger reason --request FILE`, or MCP `reason`.

First ask it for its input instructions and worked examples: call MCP `reason` with
`{"request":{"operation":"describe"}}`, or put `{"operation":"describe"}` in a file and run
`trialledger reason --request FILE`. The reply gives accepted fields, model vocabulary, complete examples
and what is built versus not integrated. It also explains results and lists clinical use cases and the
separate supporting library components. The three reasoning operations are:

- **Entailment:** what follows, is refuted or remains undetermined from explicitly supplied scoped premises.
- **Coordinates:** the retained NSCLC finite-domain reasoning from explicit applicable evidence and rules.
- **Corpus:** statement rates and silence bounds, proposed associations, occupancy and near misses over a
  declared typed population.

For example, a brief that admits only female participants can make admitting male participants logically
incompatible with that brief. The tool cites the population premise. It does not claim that an agent's typed
premise was automatically extracted from a trial or certified as a registry fact. [SKILL.md](SKILL.md) gives
a complete runnable request; `reason --help` describes use.

A typical interaction is: “I want to check whether this proposed enrollment restriction conflicts with our
population.” The assistant identifies the relevant scope, confirms the premises with you, runs the logical
question and explains which premise supports the result. Or you can ask to examine documented patterns in
a comparison set you have chosen. These are usable analyses for your judgment, not merely demonstrations
of a future pipeline. The source workbook remains unchanged; the analysis can be kept and rerun when you
change a premise.

The complete design goes further: bind source evidence, preserve clinical scope and alternatives, derive
conditional constraints, compare compatible trials, use information geometry and significance, retrieve
specific missing evidence, recommend admissible choices and produce eligibility, endpoints, schedules,
safety and protocol outputs with their warrants. See the [full design](openspec/changes/add-design-synthesis/design.md)
and [theory](docs/THEORY_OF_THE_CASE.md) for what is built and what remains to integrate. There is no current
`design` or `edits` command, complete protocol generator or automatic workbook-edit import.

## MCP

`trialledger mcp --root /absolute/path/to/trialledger-runs` serves **doctor**, **scope**, **landscape**,
**save_fetch**, **record** and the separate **reason** operation over standard input/output.

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

Use absolute paths; a desktop client does not expand `~`. Preview with `scope`, gather with `landscape`,
follow relay requests exactly and answer with `record`, including workbook addresses. Follow returned page
offsets; lists and objects are paged at up to 50 entries. `reason(request)` is separate and does not mutate a
report. Assistants read [AGENTS.md](AGENTS.md) or [SKILL.md](SKILL.md); developers read
[DEVELOPING.md](DEVELOPING.md) and the [current contract](openspec/README.md).

MIT; see [LICENSE](LICENSE).
