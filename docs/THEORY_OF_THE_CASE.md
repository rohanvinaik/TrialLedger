# Theory of the Case — TrialLedger

**Status:** filled 2026-10-31 from Rohan's words in the session that created the project. Read Part I
before anything else. His instruction for this document: «I don't literally type it out with my little
piggies, this discussion and overall context you've established is sufficient».

## Supremacy clause
This document is derived from Rohan's words in `docs/conversations/2026-10-31-the-case.md` (verbatim).
Quotes are his; anything else is marked as Claude's. Where this document is silent, ambiguous or wrong, his
words govern; where they are silent too, ask him rather than invent.

## Canonical references
| source | path |
|---|---|
| The founding conversation, verbatim | `docs/conversations/2026-10-31-the-case.md` |
| The API contract (ClinicalTrials.gov API v2, 2.0.5) | `spec/ctg-oas-v2.yaml` |
| harmonizing: shadow ledger, coherence, projector | `~/Projects/Kaggle_Killer/competitions/harmonizing/src/shadow_ledger.py`, `symbolic_healing.py`, `projector.py`, `dga_pipeline.py`; `pipeline_submission/README.md` |
| GSE: typed domains, explicit conflict, candidate rules | `~/Projects/gse/docs/program/LEXICON_IMPLEMENTATION_CONTRACT_2026-10-29.md` (read); the current `LEXICON_CONSTRUCTION_DESIGN.md` (not yet read by Claude) |
| TriageGeist: epistemic regimes, clinical banks, certified residual | `~/Projects/Kaggle_Killer/competitions/triagegeist/submission_packet/WRITEUP.md`, `src/banks.py`, `src/coherence.py` |
| The build process | `~/Projects/rohan-vinaik.github.io/papers/Core Documents/LLM_WORKFLOW/PROFESSIONAL_CODING_PERFORMANCE_ENGINEERING.md` |

## Part I — The Case

**The failure it answers:**

> LLMs are shit at "correctness". LLMs for data harvest and reasoning over medical rationale for study design is a TERRIBLE idea. I was having a conversation with someone whose coworker was getting necessary context on study design...by handing over hyperlinks to "clintrials.gov" webpages for fucking *Gemini* to parse in the chatbot.

**The claim:**

> I think this list is a trivial output, but the additional layers on TOP are ALSO entirely computable. Like, say you were in a pharma company and you wanted to think through how you might best shepheard your drug through approval. Find the participant cohorts that work best, or find an underserved niche that your drug can address that other competitors haven't, or, given the disease type and/or pathway you're treating, see the patient population and the exclusion criteria in common to impute a mechanism that's impacted and thus necessary to exclude when designing a study. Basic interpolation of the significant elements that are an inherent part of clinical study design.

**The machinery, named by him:**

> One of the key advances was the coherence system, which I've also used elsewhere (like in the most recent work in the GSE project repo--harmonizing context, doing logical coherence-driven symbolic logic to resolve illogical object and hallucination artifacts and make data resolution of imputed data fields automatable), and the implementation of the "shadow ledger" as an interface between the full data record and imputable data into a sub-set that is significant and useful. Then look into "TriageGeist", which did work to encode clinical decision-making into an almost entirely symbolic process. Extremely relevant, I think, when it comes to automating inference (in the literal/symbolic sense of the word) about the relevance of information for analysis

**The guiding light:**

> the system should built rigorously to these specs and the epistemology of my work--information theory and data geometry as the guiding light.

**Claude's restatement, which he accepted** («Good. I think this is pretty clear of a design, no?»): a symbolic
inference engine for clinical-study design, between the verbatim registry record and any answer, which
never lets a model read a trial. A ledger holds every element of every trial as typed evidence with its
scope, its source and its raw text. A coherence layer narrows what each field can be using approved
relations, fills only what is entailed, keeps the set of possible values where nothing is, and reports
contradictions instead of choosing; a contradiction is where an illogical object or a hallucinated value
shows itself. A projector emits the significant subset for one question: the colleague's ten-item sheet is
one projection, the pharma questions are others, computed across trials. TriageGeist's regimes label each
value as stated in the record, computed across comparable trials, or needing judgment. Relevance is
computed: an element matters to a question when it takes part in a relation with what the question is about.

## Part II — The data layer (built: the ingestion layer)

His specification:

> I'm talking about an API. You call it and you write and you're done. [...] I am asking you to build a basic ingestion layer. You make a query you call for a study or all studies from a range or a type or whatever the fuck, you pull and it makes a local JSON record plus a basic fucking spreadsheet so any idiot can read that.

What exists (commit `ac9c8b6`): `trialledger pull NAME=VALUE ...` sends ClinicalTrials.gov `/studies`
parameters as given and writes a new directory with `studies.json` (every matching record as the API sent
it, plus provenance: query, API version, the registry's data timestamp, retrieval time, count) and
`studies.csv` (the registry's own CSV for the same query). It writes only a complete pull: every page of
both formats, counts equal to the API's totals, the same NCT IDs in both files, one registry snapshot from
start to end. Transient server errors are retried and then fail; nothing is written on any failure. A
query the API would silently answer unfiltered (an NCT-ID-only `query.*` value beside a filter) is refused.

His decisions for the next layer (2026-10-31):

- «Fact sources should be the unambiguous fields from the API we just set up.»
- «Raw publications should be linked and surfaced, so a person reading the literal output can quickly go scan the source text, but we don't need to THOROUGHLY build a literal parser just yet.»
- «"Significant" should be pretty self-evident»
- «yes the spreadsheet should carry eligibility and safety»
- Of safety and efficacy for studies whose results were never posted to the registry: «We can impute this from papers/results, no? Might be worth adding that in then»

## Part III — The intelligence layer (designed; specified change by change in `openspec/changes/`)

Claude's sketch, from the accepted restatement and his decisions; each part names its origin.

1. **The ledger** (harmonizing, Pattern 5). Every element of a record becomes a ledger entry: its value as
   written, its place in the record, and its scope (inclusion or exclusion; primary, secondary or other
   outcome; which arm). The ledger is richer than any output and nothing is removed from it.
2. **Coherence** (harmonizing, Pattern 10; GSE's typed domains). Approved relations among the registry's
   unambiguous fields check each record against itself: a completed study with an estimated completion date,
   an arm naming an intervention the study never declares, more participants affected than at risk, a
   minimum age above the maximum. Each check returns consistent, conflict or cannot-check; conflicts are
   shown, never corrected; a field the registry left empty stays empty, distinct from a recorded "none".
3. **Projection** (harmonizing, Pattern 9). The first projection is the review workbook: the colleague's ten
   items for each study, eligibility and safety included, with links to the study page, its PubMed
   references and its posted documents beside every row.
4. **Publication evidence** (his addition: «We can impute this from papers/results, no?»). The registry
   types each linked publication as background, results or derived, so a study's results paper is found by
   an unambiguous field. For a study without posted results, figures its results paper states explicitly
   enter the ledger as publication evidence, each with its exact sentence and marked as from the paper;
   disagreement with the registry is shown; what the paper does not state plainly stays a review item.
   Measured 2026-10-31: 80,808 of 609,551 registered studies (13.3%) had results posted to the registry.
5. **Regimes** (TriageGeist). Every cell says how it was obtained: stated in the record, computed across
   comparable trials, or needs review. Needs-review cells are shown with their sources, not filled.
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
5. No model processes the trial data: «Why the hell would you think you could do data processing on medical data? YOU think you can do this? I LITERALLY started this out--my FIRST fucking prompt--by articulating the egregious failure mode of someone using an LLM to process clinical trail data.»
6. Complete or nothing: «we shouldn't have things like silent 503-error dropouts fucking with the correctness of the data parse».
7. Both signs, specified: «Tools like Detective should be THOROUGHLY used for two-sign specification of positive intent and negative specification.»
8. Facts come from the registry's unambiguous fields; publications are linked and surfaced, not parsed (his decisions, Part II).
9. The output is for a person: «just get clean, readable data that is obvious and correct».
10. Read the tools before building on them: «your design should, IDK, actually work and you should actually read the tools you're about to build».

## Part V — The Pathology Record
The first build was thrown away. In his words:
- «If you didn't literally read the --help/CLI, then you've completely hallucinated everything.»
- «Every FUCKING line of code you wrote is fucking useless because you won't take ten fucking seconds to fucking listen to me»
- «Why do you think you need to now do fucking forensics? [...] what do you think the point of "--help" even IS?????»
- «Why the hell would you think you could do data processing on medical data? [...] So your option...was to do exactly that???»

Claude's account of the failure modes, so they stay recognizable: designing around a tool from second-hand
prose instead of its own `--help`; an agent deciding the data processing itself, which is the failure this
project exists to reject; inventing scope where he was silent; over-correcting from too little reading into
reading everything when `--help` was the answer; and reading fragments of documents instead of whole units.
