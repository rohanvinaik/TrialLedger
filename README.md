# TrialLedger

**Source-backed clinical trial reference workbooks, and symbolic reasoning about trial design that your
assistant runs with you.**

Tell your assistant which trials you care about, by trial number or by drug, class, condition and filters.
TrialLedger gathers their ClinicalTrials.gov records into one formatted workbook (`landscape.xlsx`), with a
dossier for each study and shared listings, plus the matching record (`landscape.json`) your assistant answers
from. No more copying registry pages into a spreadsheet.

Then think through a design in conversation. Ask whether a kind of patient is in or out under your draft
criteria and which criterion decides it, whether your criteria contradict each other, how common a criterion
is among comparable trials, what is unusual or notable, where the gaps are, or which trials differ in just one
design choice. The answers are computed by the program's logic, not composed by a chatbot.

## What's mechanical and what's reasoned

**Layer one is mechanical.** It copies registry facts and applies fixed, named rules. No AI supplies a value.

**Layer two is symbolic reasoning about trial design.** Your assistant's job is translation: it restates your
criteria and questions as structured premises, shows them back to you in plain words, and explains the
results. The reasoning itself is computed. Your assistant never decides what follows from your design; the
program does, and says which premise decided it.

So every statement you hear comes from one of three places, and your assistant says which:

- **From the record:** a registry fact, with its place in the workbook.
- **Computed:** a result from the reasoning operations, with the premise or rule that decided it.
- **The assistant's reading:** its interpretation or judgment, labelled as such and never promoted to a fact
  without your confirmation.

## Why you can trust the answers

Every computed answer lands in one of four places:

- **Settled:** your criteria require it or rule it out, and here is the deciding criterion.
- **Something's wrong:** your draft contradicts itself, or a registry record disagrees with itself.
- **Your call:** your criteria allow it without requiring it, a choice is suggested but not forced, or
  comparable trials made different choices.
- **Not knowable from this evidence:** the registry is silent, or there are too few trials to say.

Ask "must everyone be at least 65?" of a trial requiring age 18 or older, and you will hear neither yes nor
no. You will hear that 65-year-olds are **allowed but not required**, because of the age criterion. That is
the exact truth, and it is more useful than a guess: the logic holds precisely what the criteria establish,
neither more nor less.

When an answer is open, it also says *why*, and each reason is the next question in the conversation:

| What the reasoning reports | What your assistant asks next |
|---|---|
| Allowed but not required by criterion X | "Do you want to restrict this?" |
| Your criteria don't address this | "Should they? Or is it worded differently, in other units, or over another time window?" |
| It depends on which cohort or arm | "Which group do you mean?" |
| It depends on a reading you haven't confirmed | "Here is how I read that criterion. Is that right?" |
| Your criteria contradict each other (X versus Y) | "Which one should stand?" |

Nothing should be concluded from a reading you have not confirmed. Your assistant marks every reading you
have not yet confirmed as unconfirmed, the eligibility logic refuses to draw conclusions from such readings,
and your assistant confirms its readings with you before using the other operations. Where two reasonable
readings of a criterion give different answers, that is surfaced as your call rather than silently decided.

## Thinking through a design with your assistant

1. **Gather the evidence.** Your assistant builds the reference workbook for the trials you name or describe.
2. **Ask in your own words.** "Would patients with exon 20 insertions qualify under our draft?"
3. **Confirm the reading.** Your assistant restates each relevant criterion in plain words and asks about
   anything ambiguous: one qualifying mutation, or compound mutations allowed? Every participant, or one
   cohort? Prior therapy for advanced disease, or any prior therapy?
4. **Get a computed answer** with its category and deciding criterion.
5. **Change a premise and rerun** whenever you like. The reference workbook never changes.

For example, with a draft second-line EGFR-mutant lung cancer brief (adults 18 or older, ECOG 0-1, exon 19
deletion or L858R, prior osimertinib, no symptomatic brain metastases, no prior chemotherapy for advanced
disease):

- *Could a 16-year-old enroll?* **No**: the age criterion rules it out.
- *Must everyone be at least 65?* **Allowed but not required**: the age criterion admits it without requiring
  it.
- *Would exon 20 insertions qualify?* If the criterion means each patient's mutation type is one of the two,
  **no**. If it means a patient has at least one of them, your criteria **don't address exon 20**. The two
  readings give different answers, so your assistant asks which you mean.
- *If the draft also says "17 or younger" somewhere:* **something's wrong**: 18 or older contradicts 17 or
  younger, and no question can be answered until one is corrected.

What you can ask, and what computes the answer:

| Ask in your words | What computes it |
|---|---|
| "Could this patient enroll?" "Must everyone have X?" "Does X fit our brief?" | Logical entailment over your confirmed criteria |
| "Do my criteria contradict each other?" | The same logic; a contradiction is reported with both sides |
| "Does this record disagree with itself?" | Layer-one registry checks of dates, counts and links |
| "What treatment setting do these lung cancer criteria imply?" | Non-small cell lung cancer setting rules, with defaults shown as defaults |
| "How common or standard is criterion X in these trials?" | Statement rates with a range, because silence is not absence |
| "Is X more common with drug class Y?" | Class comparisons with a minimum-support rule |
| "What's unusual here?" | Rarity within the comparison set you declare, or an abstention when support is too thin |
| "What's notable?" | Rarity, plus departure from an expectation you declare with no recorded explanation |
| "Where are the gaps?" | Setting-by-class occupancy; a cell is empty only if no trial could fit, and empty is not unmet need |
| "Which trials differ only in X?" | Near-miss pairs under the features you declare |

Some questions have no computed answer yet, such as "were these efficacy results impressive?" Your assistant
then reads the posted results from the record, with their groups, denominators, units and periods, and labels
its interpretation as its own reading.

## What's still being built

The complete automated trial writer is designed and partly built: from your brief and the evidence, derive
the constraints, compare relevant trials, recommend admissible choices, ask you to settle the rest and write a
protocol with the basis for each element. Today your assistant does the reading of trial text with you and
the reasoning operations do the logic; automatic reading of trial text and complete brief-to-protocol writing
are not yet integrated. Derivational significance (from the author's significance-weighting work: how
improbable a chain of design reasoning would be by coincidence, given the alternatives open at each step) is
designed for a later build; today's "unusual" and "notable" are corpus rarity and declared-expectation
deviation, not that measure. See the
[full design](openspec/changes/add-design-synthesis/design.md) and [theory](docs/THEORY_OF_THE_CASE.md).

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

## Setting it up through your assistant

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
where you can inspect the member drugs and filters. The example uses ATC class `L01EB`; it describes a
search, not a claim that particular matching studies were retrieved.

In direct mode, the assistant can fetch from the resolved scope itself. In relay mode, TrialLedger still
needs the search terminology to resolve the requested scope, but it skips post-retrieval drug enrichment.
Each relay fetch must be the complete response body saved byte-for-byte as requested; a browser excerpt,
copied table or shortened response cannot substitute. Relay validates structure and identity, not every live
registry value.

The local commands, for an assistant environment with those capabilities, are:

```bash
pip install "git+https://github.com/rohanvinaik/TrialLedger"
trialledger doctor --run egfr-nsclc
trialledger landscape --run egfr-nsclc --drug-class-id L01EB --class-source ATC \
    --condition-class "Carcinoma, Non-Small-Cell Lung" --phase PHASE3 --status COMPLETED --preview
```

Read the preview and `resolution.json`, then repeat without `--preview`. Specific trials use, for example,
`trialledger landscape --run my-trials --ids NCT00322452,NCT01774721` (IPASS and ARCHER 1050).
`landscape --help` lists every request field. A changed request needs a new run folder; a repeated request
resumes. Class requests can explicitly exclude subclasses through request JSON. Search expansion is shown,
never hidden.

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

## The reasoning operations

Layer two runs through `trialledger reason --request FILE`, or the MCP tool `reason`. Your assistant starts by
asking it to describe itself: call MCP `reason` with `{"request":{"operation":"describe"}}`, or put
`{"operation":"describe"}` in a file and run `trialledger reason --request FILE`. The reply gives the accepted
inputs, an answer guide that maps every result to the four categories above, the clinical words each
operation answers, and a worked session whose every request runs and returns the stated answer.

- **Entailment:** whether your confirmed premises require, rule out or leave open a statement, or contradict
  each other, with the deciding premises and named reasons for anything left open.
- **Coordinates:** non-small cell lung cancer setting, prior-line and biomarker-selection reasoning. Its
  setting rules are defaults or proposals and are reported that way.
- **Corpus:** statement rates and silence bounds, class associations, rarity against declared expectations,
  setting-by-class occupancy and one-difference pairs over a comparison set you declare.

Results are conditional on the premises supplied. The operations never read trial text, fetch sources or
change a report; your assistant keeps the structured result (for example `reason-result.json`) beside the
workbook so a premise can be revised and rerun. [AGENTS.md](AGENTS.md) explains the translation discipline;
[SKILL.md](SKILL.md) gives a complete runnable request.

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
