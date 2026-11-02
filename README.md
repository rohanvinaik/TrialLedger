# TrialLedger

**A clinical-trial reference workbook backed by its source record, and a separate symbolic trial designer.**

Give your assistant trial numbers or a description of the trials you want. TrialLedger gathers their
ClinicalTrials.gov records and returns one readable workbook with a dossier for each study and shared
listings, plus matching JSON. The assistant answers from that evidence rather than inventing trial facts.

That is **layer one**, the available reference-sheet operation. **Layer two** is the separately designed
automated clinical trial writer: use a brief, warranted evidence and symbolic constraints to construct a new
trial, suggest supported choices and ask the person to settle the remaining judgments. Its scoped reasoning,
NSCLC coordinate and corpus-analysis operations are available; automatic source interpretation and the
complete brief-to-protocol workflow are not yet integrated. Incomplete integration does not make those
working symbolic components unusable.

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

## Use it through your assistant

Ask, for example:

> Using TrialLedger, find completed Phase 3 trials of EGFR tyrosine kinase inhibitors in non-small cell lung
> cancer. Show me the search, then give me the reference workbook.

For local use, install on Python 3.12 or later:

```bash
pip install "git+https://github.com/rohanvinaik/TrialLedger"
trialledger doctor --run egfr-nsclc
trialledger landscape --run egfr-nsclc --drug-class "EGFR tyrosine kinase inhibitors" --class-source ATC \
    --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED --preview
```

Read the preview and `resolution.json`, then repeat without `--preview`. Specific trials use
`trialledger landscape --run my-trials --ids NCT04852770,NCT01827384`. `landscape --help` lists every request
field. A changed request needs a new run folder; a repeated request resumes. Class requests can explicitly
exclude subclasses through request JSON. Search expansion is shown, never hidden.

`doctor` chooses **direct** mode when the program can fetch, or **relay** when the assistant must fetch each
exact response in `next.json` unchanged. Relay checks form, counts, order and identities, not every value
against the live registry; never retype, shorten or correct a response. Gathered-study drug enrichment is not
performed in relay mode: not looked up is not no class.

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
