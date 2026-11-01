# TrialLedger: a guide for the assistant using it

You have been pointed at TrialLedger to help someone with clinical trials. This guide tells you what TrialLedger
is for, what you can trust in what it gives you, what the person should review before relying on it, and how to
run it. Read it before you answer them; come back to it when they ask what TrialLedger can do or how far to trust
a result.

## What TrialLedger is for

Designing a clinical trial starts with what has already been done: which trials have tested this drug, this
class of drugs, this disease; whom they enrolled and excluded; what they measured and when; what they found.
That knowledge sits on ClinicalTrials.gov, run by the US National Library of Medicine, spread across hundreds of
separate records. Gathering it by hand, record by record, is days of work for every question, and most of the
effort of trial design.

TrialLedger automates that work, in two layers.

**Layer one gathers the evidence. It is complete, and you can trust it.** Given a kind of trial (a drug, a drug
class, a mechanism, a disease or a family of diseases), it finds every matching study on ClinicalTrials.gov and
lays out what each record says: the population; the inclusion and exclusion criteria; the line of therapy; the
outcome measures and their time points; the biomarkers and the role each plays; the efficacy and safety results
where the trial posted them; exploratory measures; links to the registry page, publications and posted
documents. It is the same information the registry holds, organized, and nothing more: no language model reads
a trial, and nothing is summarized, paraphrased or inferred. Each value is a field of the registry record, or the
result of a named, fixed rule applied to such fields, and says which. Think of it as a meticulous clinical data
manager doing the lookup by hand, only exhaustively and instantly.

**Layer two designs a trial. It is being built.** Given what the person wants to test, it constructs a trial the
way an experienced designer reasons: it builds what follows by logic from what they have stated, recommends what
comparable trials have done (with the trials and numbers behind each recommendation), and offers the choices
that call for judgment one at a time, with a suggestion, for the person to decide. It is about half built. Its
reasoning works end to end on one demonstration case, Phase 3 trials in non-small cell lung cancer; extending it
to every kind of trial, and assembling a full draft design, are under way.

## What is fact and what needs review

The person will ask what they can rely on. Every value TrialLedger produces carries its status, so you can
always tell them exactly. The breakdown:

**Facts from the registry: rely on them as you would on the registry itself.**
- Everything a study's record states: its identifiers, phase, status, dates, sponsor, arms and interventions,
  enrollment, eligibility text, registered outcomes and time frames, posted results and adverse events,
  publications and documents. These are *stated* values, each with the record and field it came from.
- Absence is reported as absence. An empty field is "not stated", never "none"; a trial without posted results
  says "no results posted". A registered outcome is what a trial planned to measure, never evidence that it
  worked. Only about 13% of registered studies have posted results, so many questions about efficacy have no
  registry answer, and TrialLedger will say so rather than fill the gap.
- Drug classes come from the National Library of Medicine's RxClass and RxNorm, named as such, with the date
  they were retrieved.

**Readings by fixed rules: reliable, and traceable to the words they read.**
- Each eligibility criterion split out and classified (an age limit, a laboratory threshold, a performance
  status, a prior therapy, a named condition), each reading with the exact words it was read from. Where the
  rules cannot read a criterion confidently, they leave it unread and say so; they never guess.
- Each trial's setting (stage of disease, line of therapy, biomarker selection) as the values its own criteria
  allow.
- These are *computed* values. If the person needs certainty about one, show them the criterion text beside it.

**Analysis across trials: evidence for the person to weigh, not facts.**
- Which criteria are standard among the trials found, which exclusions follow a drug's mechanism, which settings
  no trial has tried, pairs of trials that differ in one design choice, expected criteria a trial lacks. Each
  comes with its numbers and a status: a pattern that holds even under the least favourable reading of silent
  records is *proposed*; one those records could reverse is *unresolved*. None is presented as established, and
  the person should review them before building on them.
- A **review queue** lists what the rules could not settle cleanly, each as a question with closed options and
  its evidence. These are for the person, or a domain expert, to answer.

**Layer two's design, when complete, will mark every element the same way:** *deduced* from the person's stated
premises (show them the premises), *recommended* from precedent (show them the trials and numbers), or *chosen*
by the person. Only their own choices are theirs to make; everything else they can check.

When the person asks whether something is true, find the value in the record TrialLedger wrote, give its status
and its source, and, for anything computed or proposed, show them what it rests on. Never answer about a trial
from your own knowledge or from reading its registry page yourself: answer from the record, and say when the
record does not contain the answer.

## How to run it

TrialLedger runs in your code sandbox. It needs Python 3.12 or later.

1. **Install it** from this repository: `pip install` the repository's address (or `uv tool install` it).
2. **Check what your sandbox can do:** `trialledger doctor` prints, as JSON, whether this sandbox can reach
   ClinicalTrials.gov and RxNav, and the next step. Some chat sandboxes block programs from reaching the
   internet. A relay through which you fetch the data for TrialLedger is being built; until it lands, a
   sandbox that cannot reach the registry cannot run TrialLedger, and the next step says so. Do not fetch
   registry records yourself in its place.
3. **Turn the person's question into a query.** Today, `trialledger resolve` takes the registry's own search
   parameters, for example:

   ```bash
   trialledger resolve query.cond="non-small cell lung cancer" query.intr="pembrolizumab" \
       filter.overallStatus=COMPLETED --json reading.json --out design.xlsx
   ```

   It writes the record as JSON (answer from this) and a spreadsheet (give this to the person). Check
   `trialledger resolve --help` for the parameters. A single command that takes the person's terms directly (a
   drug class, a mechanism, a disease family) and resolves them through the registry's and the National Library
   of Medicine's vocabularies, showing exactly what it included, is being finished, along with the fetching
   relay for blocked sandboxes; when it lands, this guide and `trialledger --help` describe it.
4. **Show the person what was searched**, so they can see what was included and narrow it if needed.
5. **Answer from the record, and hand over the spreadsheet.** Keep each value's status when you report it.

For a copy that can be re-verified later, `trialledger pull` saves the registry's records with certified
spreadsheets, and `trialledger verify` re-derives every value in a saved copy and names anything that no longer
matches.

## How to find out more

When the person asks something this guide does not settle, find the answer in the project rather than guessing:

- `README.md`: the project explained for clinical readers.
- `trialledger <command> --help`: what each command does and what each exit code means.
- Each value's warrant and source field in the record: how that value was obtained.
- `openspec/changes/`: the plans and status of each part, in plain language; `add-agent-operation` (running
  TrialLedger from an assistant) and `add-design-synthesis` (layer two's design) are the most relevant.
- `openspec/changes/add-bank-coverage/audit-existing-banks.md`: where the criterion-reading rules are known to
  fall short, rule by rule.

If you are changing TrialLedger's own code rather than using it, read `DEVELOPING.md`.
