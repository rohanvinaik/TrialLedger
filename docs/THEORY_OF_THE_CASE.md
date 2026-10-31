# Theory of the Case — TrialLedger

**Status:** filled 2026-10-31 from Rohan's words in the session that created the project. Read Part I before
anything else. His instruction for this document, paraphrased: he would not write it himself; what the session
discussed and established is enough to fill it.

## Supremacy clause
This document is derived from Rohan's words, kept verbatim in `docs/conversations/2026-10-31-the-case.md` on
his machine; at his instruction none of his messages, and no quotation of them, is kept in git. His words
appear here paraphrased, each marked as a paraphrase; anything else is marked as Claude's. A paraphrase is
Claude's rendering of his words, kept to their meaning and to his own terms, but it is not his words: before
building on one, read the passage it renders in the local record. Where this document is silent, ambiguous or
wrong, his words govern; where they are silent too, ask him rather than invent.

## Canonical references
| source | path |
|---|---|
| The founding conversation, verbatim | `docs/conversations/2026-10-31-the-case.md` (on his machine, not in the repository) |
| The API contract (ClinicalTrials.gov API v2, 2.0.5) | `spec/ctg-oas-v2.yaml` |
| harmonizing: shadow ledger, coherence, projector | `~/Projects/Kaggle_Killer/competitions/harmonizing/src/shadow_ledger.py`, `symbolic_healing.py`, `projector.py`, `dga_pipeline.py`; `pipeline_submission/README.md` |
| GSE: typed domains, explicit conflict, candidate rules | `~/Projects/gse/docs/program/LEXICON_IMPLEMENTATION_CONTRACT_2026-10-29.md` (read); the current `LEXICON_CONSTRUCTION_DESIGN.md` (not yet read by Claude) |
| TriageGeist: epistemic regimes, clinical banks, certified residual | `~/Projects/Kaggle_Killer/competitions/triagegeist/submission_packet/WRITEUP.md`, `src/banks.py`, `src/coherence.py` |
| The build process | `~/Projects/rohan-vinaik.github.io/papers/Core Documents/LLM_WORKFLOW/PROFESSIONAL_CODING_PERFORMANCE_ENGINEERING.md` |

## Part I — The Case

**The failure it answers** (his words, paraphrased): LLMs are bad at correctness, and using them to harvest
data and to reason about the medical rationale behind a study's design is a terrible idea. The case he began
from: a colleague's coworker was getting the context their study-design work needed by handing a chatbot
(Gemini) links to ClinicalTrials.gov pages to parse.

**The claim** (his words, paraphrased): the colleague's list is a trivial output, and the layers on top of it
are entirely computable as well. For a pharma company working out how best to shepherd its drug through
approval, that means finding the participant cohorts that work best; finding an underserved niche the drug can
address that competitors have not; or, given the disease type or pathway treated, looking at the patient
population and the exclusion criteria that trials have in common to impute a mechanism that is affected, and
is therefore necessary to exclude when a study is designed. To him, this is basic interpolation over
significant elements that every clinical study design inherently has.

**The machinery, named by him** (paraphrased): a key advance was the coherence system, which he has also used
elsewhere, as in his most recent GSE work, harmonizing context: symbolic logic, driven by coherence, by which
illogical objects and hallucination artifacts are resolved and resolving imputed data fields becomes
automatable. Beside it, the shadow ledger, which interfaces the full data record and its imputable data with
the subset that is significant and useful. And TriageGeist, which made clinical decision-making an almost
wholly symbolic process; he judges it highly relevant to automating inference, symbolic inference in the
literal sense, about how relevant information is to an analysis.

**What guides it** (his words, paraphrased): the system must be built with rigor, both to these specifications
and to the epistemology of his work, and information theory and data geometry are what guide it.

**Claude's restatement, which he accepted** (paraphrased: he judged it a clear design): a symbolic inference
engine for clinical-study design, between the verbatim registry record and any answer, which never lets a
model read a trial. A ledger holds every element of every trial as typed evidence with its scope, its source
and its raw text. A coherence layer narrows what each field can be using approved relations, fills only what
is entailed, keeps the set of possible values where nothing is, and reports contradictions instead of
choosing; a contradiction is where an illogical object or a hallucinated value shows itself. A projector emits
the significant subset for one question: the colleague's ten-item sheet is one projection, the pharma
questions are others, computed across trials. TriageGeist's regimes label each value as stated in the record,
computed across comparable trials, or needing judgment. Relevance is computed: an element matters to a
question when it takes part in a relation with what the question is about.

## Part II — The data layer (built: the ingestion layer)

His specification (paraphrased): a plain ingestion layer over the API, and no more: a query, for a single
study or for all studies in a range or of a kind; the pull; and, written locally, the JSON record and a simple
spreadsheet that anyone can read.

What exists (commit `ac9c8b6`): `trialledger pull NAME=VALUE ...` sends ClinicalTrials.gov `/studies`
parameters as given and writes a new directory with `studies.json` (every matching record as the API sent
it, plus provenance: query, API version, the registry's data timestamp, retrieval time, count) and
`studies.csv` (the registry's own CSV for the same query). It writes only a complete pull: every page of
both formats, counts equal to the API's totals, the same NCT IDs in both files, one registry snapshot from
start to end. Transient server errors are retried and then fail; nothing is written on any failure. A
query the API would silently answer unfiltered (an NCT-ID-only `query.*` value beside a filter) is refused.

His decisions for the next layer (2026-10-31, paraphrased):

- Facts are to come from the unambiguous fields of the API layer just built.
- Raw publications are linked and brought to the surface, so a reader of the output can go quickly to the
  source text and scan it; a thorough literal parser for them is not needed yet.
- What counts as significant should be fairly self-evident.
- The spreadsheet is to carry eligibility and safety.
- For studies whose results were never posted to the registry, safety and efficacy could be imputed from
  papers and their results, and that might be worth adding.

## Part III — The intelligence layer (steps 1–3 and 5 built in `add-review-workbook`; the rest designed)

Claude's sketch, from the accepted restatement and his decisions; each part names its origin.

1. **The ledger** (harmonizing, Pattern 5). Every element of a record becomes a ledger entry: its value as
   written, its place in the record, and its scope (inclusion or exclusion; primary, secondary or other
   outcome; which arm). The ledger is richer than any output and nothing is removed from it.
2. **Coherence** (harmonizing, Pattern 10; GSE's typed domains). Approved relations among the registry's
   unambiguous fields check each record against itself: a completed study with an estimated completion date,
   an arm naming an intervention the study never declares, more participants affected than at risk, a
   minimum age above the maximum. Each check returns consistent, conflict, not applicable or not checkable
   (a missing, malformed or too imprecise input is never a pass); conflicts are shown, never corrected; a
   field the registry left empty stays empty, distinct from a recorded "none". Seventeen checks are built;
   the five whose relation the registry states run, and the twelve it only entails wait for his approval
   (law 13).
3. **Projection** (harmonizing, Pattern 9). The first projection is the review workbook: the colleague's ten
   items for each study, eligibility and safety included, with links to the study page, its PubMed
   references and its posted documents beside every row.
4. **Publication evidence** (his addition, paraphrased: results the registry lacks could be imputed from
   papers). The registry types each linked publication BACKGROUND, RESULT or DERIVED. Only the first two are
   the responsible party's statement: the protocol data element definitions give it one choice per reference,
   «Results Reference? Indicate if the reference provided reports on results from this clinical study. Select
   Yes/No». DERIVED is added by the registry and the definitions never define it, so a derived publication has
   no stated role. A results paper is therefore found by an unambiguous field only when the responsible party
   marked it. Measured: on 2026-10-30, 126,368 studies carried DERIVED references, 99,393 BACKGROUND and
   43,671 RESULT (`/stats/field/values?fields=ReferenceType`); in a live sample of 2,177 studies without
   posted results (start dates 2014-01-01 to 2014-01-10), 563 had DERIVED references and 163 RESULT. Which
   publications to read for a study without posted results is open, for the founder to decide: RESULT alone
   misses most results papers, and DERIVED alone states nothing about what a paper reports. For a paper that
   is read, figures it states explicitly enter the ledger as publication evidence, each with its exact
   sentence and marked as from the paper; disagreement with the registry is shown; what the paper does not
   state plainly stays a review item. Measured 2026-10-31: 80,808 of 609,551 registered studies (13.3%) had
   results posted to the registry.
   **The end-stage parser** (his design, 2026-10-31, paraphrased: a raw paper is processed by its sections,
   and the sections decide which differential parsing systems are assigned, each hunting the specific context
   that resolves a gap or inconsistency in how the trial's data is encoded; because study data is rigidly
   typed and formal, probably not even a small local model is needed). The ledger's open items become typed
   queries carrying the record's own vocabulary; a paper is read in its published, typed sections, kept or
   vetoed by heading as the Regenesis puller does; a deterministic parser per fact type hunts the sections
   where that fact is stated; identity resolvers (after Regenesis's cassettes) bind the paper's arms, outcomes
   and time points to the record's or abstain; censors (after its `cannot` rules) forbid figures from vetoed
   sections or with unresolved bindings; what is found enters the ledger as warranted publication evidence,
   compared with the registry and never overriding it. Specified in
   `openspec/changes/add-review-workbook/design.md`, "Sequence after this change".
5. **Regimes** (TriageGeist). Every cell says how it was obtained: stated in the record, computed across
   comparable trials, or needs review. Needs-review cells are shown with their sources, not filled.
   **Warrants** (his principle, law 12): every value also carries a hash committing to that basis, its
   record bytes and the code that rendered it (a root over the modules and registry tables that derive the
   workbook, so a rule's constants and tables are committed too, with the commit of that code), so any reader
   can re-derive it from the record
   (`trialledger verify`, which also compares the workbook file part for part); what does not re-derive is
   refused.
6. **Across trials** (designed, later changes): comparators' posted results as the efficacy and safety bars;
   cohorts compared only within matching endpoints and time points; niches as combinations of design
   choices with no trials; exclusions that recur within a mechanism or class, not everywhere, proposed as
   mechanism-linked risks. A discovered pattern proposes a rule; a person approves it; it never confirms
   itself (GSE).

**Information theory and data geometry, Claude's restatement (not yet confirmed by him):**

- The record is the source and every view is derived from it. No derived view can know more about a trial
  than its record holds, so the record is kept whole and every derived value names what it came from.
- Unknown stays unknown. An unresolved value is the set of possibilities still open; only evidence or an
  approved rule narrows it, never an assumption.
- Significance is information: what distinguishes trials for the question asked. What every trial shares,
  such as excluding pregnancy, tells a designer nothing about how to differ and is background (the
  counterexample Codex raised, 2026-10-31).
- Each trial is a point in a design space whose axes are the clinical dimensions (population, phase, line of
  therapy, mechanism, endpoint and time point, safety). Comparisons run along matched axes; cohorts are
  regions; niches are empty regions; a mechanism-linked exclusion is structure aligned with the mechanism
  axis rather than the indication axis. The review workbook is the projection of that space onto the axes
  one reviewer needs.

## Part IV — The Laws
1. The architecture is classical AI, NOT ML (AI = genus, ML = one avoidable species).
2. A model is never the default; at most a bounded, founder-placed tail utility.
3. The substrate narrows/encodes; it never decides (decisions are the intelligence layer).
4. Iterate the encoder / data geometry, never model capacity.
5. No model processes the trial data (his words, paraphrased: an agent must not presume it can do the data
   processing on medical data itself; his very first prompt laid out exactly that egregious failure mode, a
   person having an LLM process clinical trial data).
6. Complete or nothing (paraphrased: nothing like a silent dropout on a 503 error may compromise how correctly
   the data is parsed).
7. Both signs, specified (paraphrased: Detective and tools like it are to be used thoroughly to specify both
   signs: the positive intent, and the negative specification).
8. Facts come from the registry's unambiguous fields; publications are linked and surfaced, not parsed (his
   decisions, Part II).
9. The output is for a person (paraphrased: what is wanted is data that is clean and readable, obvious and
   correct).
10. Read the tools before building on them (paraphrased: a design must actually work, and the tools it is
    about to be built with must actually be read).
11. All information, typed (paraphrased: all information, in the information-theoretic sense of signal above
    pure random entropy, down to the last scrap, is to be extracted, processed and presented in a clear
    semantic category; clinical trials are highly typed and symbolic, and by far most of the degrees of
    freedom in their design are computable objects).
12. Every value carries its warrant (paraphrased: each piece of information should be able to carry a strict
    warrant of the basis on which it entered the record; reading data out and understanding it within clinical
    trial design should come with a contract of its own, as it did at the core of TriageGeist, where each rule
    bears a strict warrant ensuring it is correct and together the rules form a formal contract of
    correctness).
13. Rules first, built exactly (paraphrased: he very much wants rules, which complete extraction of all
    available information inherently requires; and learned coherence or imputed information can be built in
    only once the rule-based parts are built very clearly and correctly). A rule TrialLedger's reading
    entails, rather than one the registry states, is proposed for his approval, never self-approved.
14. The purpose (paraphrased: at bottom this is a clinical trial design project: clear, well-built symbolic
    systems that automate the design of clinical trials, as TriageGeist automated triage and harmonizing
    auto-populated a data record for proteomics projects).

## Part V — The Pathology Record
The first build was thrown away. His words, paraphrased:
- not having literally read a tool's --help and CLI meant that everything built on it was completely
  hallucinated;
- every line of code written was useless, because he had not been listened to, when listening would have taken
  seconds;
- forensics were not needed: the point of --help is to be read;
- the option an agent chose was to do the data processing on medical data itself, the very failure the project
  began by naming.

Claude's account of the failure modes, so they stay recognizable: designing around a tool from second-hand
prose instead of its own `--help`; an agent deciding the data processing itself, which is the failure this
project exists to reject; inventing scope where he was silent; over-correcting from too little reading into
reading everything when `--help` was the answer; and reading fragments of documents instead of whole units.
