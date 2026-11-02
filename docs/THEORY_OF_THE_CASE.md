# Theory of the Case — TrialLedger

## Authority

This document records Rohan's design in paraphrase. His instructions govern; an agent's paraphrase, an
implementation and a passing test do not amend them. The founding conversation is retained locally at
`docs/conversations/2026-10-31-the-case.md`, outside Git. No verbatim private conversation is published here.
The current layer boundary incorporates his subsequent corrections. Superseded agent-written descriptions
are not competing interpretations of his thesis.

The original systems named as design references are harmonizing's shadow ledger, coherence and projector;
TriageGeist's epistemic regimes and orthogonal clinical representations; GSE's typed constraints and explicit
conflicts; and his DATA_GEOMETRY and SIGNIFICANCE_WEIGHTING work. They are instruments for constructing this
system, not claims that an arbitrary recognizer implements their theory.

Canonical local references are retained so an implementer can read the actual instrument before extending it:

| Reference | Location |
|---|---|
| Founding requirements, verbatim and private | `docs/conversations/2026-10-31-the-case.md` |
| ClinicalTrials.gov API contract | `spec/ctg-oas-v2.yaml` and the vendored registry metadata/enums |
| harmonizing's ledger, coherence and projector | `~/Projects/Kaggle_Killer/competitions/harmonizing/src/`: `shadow_ledger.py`, `symbolic_healing.py`, `projector.py`, `dga_pipeline.py` |
| TriageGeist | `~/Projects/Kaggle_Killer/competitions/triagegeist/submission_packet/WRITEUP.md`, `src/banks.py`, `src/coherence.py` |
| GSE typed-domain construction | `~/Projects/gse/docs/program/LEXICON_IMPLEMENTATION_CONTRACT_2026-10-29.md` and `LEXICON_CONSTRUCTION_DESIGN.md` |
| Information geometry and significance | The founder's canonical DATA_GEOMETRY and SIGNIFICANCE_WEIGHTING documents; their definitions must be read before extending those methods |
| Engineering workflow | `~/Projects/rohan-vinaik.github.io/papers/Core Documents/LLM_WORKFLOW/PROFESSIONAL_CODING_PERFORMANCE_ENGINEERING.md` |

## The case

A clinical development professional needs a reliable account of comparable trials before designing their
own. Asking a language model to extract and improvise facts from registry pages defeats that purpose.
Clinical trial records already contain highly structured information. The first operation is therefore
simple: request trials from the government registry, preserve their records and present relevant fields
clearly. The chatbot translates the person's request into API inputs, operates the harness, answers from its
saved evidence and hands over the workbook.

The second operation uses that warranted substrate to do non-trivial symbolic trial design. Much of a
trial's design space is constrained by its own definitions, population, intervention, question and temporal
structure. Explicit premises can eliminate incompatible alternatives; comparable trials contribute sourced
observations and proposals; the remaining judgments go to the person. This is the automated clinical
trial-writing thesis. It is fully designed and only partly implemented. A working symbolic component remains
valuable when an upstream encoder or the final orchestration is unfinished.

## Layer one: source-faithful clinical reference sheets

Input is one or more study identifiers or a search by drug, class, condition and registry filters. Output is
one clinical workbook with each study's dossier and shared listings, plus the matching JSON evidence record.
The complete source responses are retained. The clinical projection is selected and described; it is not
mislabelled as the entire raw registry record.

Every value is either source data or a strictly warranted direct transformation. Examples are a source-defined
label, an exact unit conversion whose premises hold, a count, a link, a results/source-presence state, a
structured consistency check, or lossless division at unambiguous eligibility headings. These operations do
not decide clinical meaning. The source paths and rule definitions can be recorded once in the field
dictionary; copying every plain value into a separate envelope is not a requirement.

Eligibility, descriptions and outcomes remain exact source text. Dividing text for readability does not
interpret negation, exceptions, alternative cohorts, treatment lines or biomarker roles. The assistant can
quote and point to the evidence; a clinical interpretation is identified as such and kept separate.

Drug terminology uses existing canonical identity evidence from RxNorm/RxClass. Identity, ingredients,
product forms, class membership and alias relationships are different objects. A response about an ingredient
is not automatically a response about a combination, salt, biosimilar or product. Disagreement and missing
identity remain visible; the first successful alias is not a resolution policy.

Population, eligibility, interventions, planned measures and time points, posted results, safety and source
documents are presented in clinical terms. Eligible, enrolled and analysed populations stay distinct. Local
result-group identifiers retain their module scope; denominators, units and periods accompany numbers.
Registered outcomes are plans, not efficacy observations. Seriousness is not an adverse-event grade. Missing,
malformed, explicitly empty, not applicable and not posted remain different states.

A complete run checks retrieval coverage and identity. A workbook is checked against its record and can be
replayed from retained sources. Warrants bind actual derivation dependencies, not unrelated design code.
These checks establish preservation and reproducibility. They do not establish registry truth or confer
clinical meaning on a recognizer. The reporting path never invokes the layer-two compiler or solver.

## Layer two: symbolic automated trial writing

### Evidence and representation

The ledger retains source values, exact locations, versions, scope and warrants. Additional terminology,
labels and publications contribute their own attributed evidence rather than overwrite the registry.
Recognition identifies literal candidate entities, quantities, units and spans. It does not establish the
subject, predicate, polarity, force, time, condition or clinical significance of a statement by itself.

The assertion representation preserves conjunctions and alternatives, exclusions and permissions,
qualifiers, conditionality, definitions, referents, cohorts, arms and time anchors. Required(A or B) does not
require A or B separately; excluded(A and Q) does not exclude every A; an obligation conditional on medication
use does not require medication use; a definition imposes nothing until properly referenced. A number near
an age word cannot become an age restriction without binding the measurement and its role.

Meaning is settled by constraints and the constructive or destructive combination of independent evidence.
Each source measures its own thing. Encodings of the same evidence are not independent corroboration.
Agreement alone does not assign a value; supported constraints eliminate alternatives. Unresolved binding or
disagreement stays unresolved rather than being filled by a phrase list or a majority vote.

### Reasoning and epistemic standing

Known is a source fact or a strict conclusion from known premises. Interpolated is a declared default or a
conclusion resting on interpolation. Proposed is a candidate to weigh, not a premise. A user's choice remains
a user's choice. Approval is not logical strictness, and a deterministic program does not promote status.
Every conclusion retains premises, source and rule versions and its weakest support.

Scoped entailment checks satisfiability before conclusions; inconsistent premises do not entail everything.
Finite coordinate closure removes values with recorded causes and reaches an order-independent fixed point.
Defaults have declared applicability and defeaters; conflicting defaults are suspended and reported, not
selected by order. A bounded solver returns a named undetermined result when it cannot decide.

Clinical relations are scoped to the indication, population, intervention and relevant edition. Disease
extent, prior treatment at enrollment and the role of the tested treatment remain separate. A trial's setting
is not today's standard of care. Ontology relations and unit conversions need source-backed definitions;
recognizing a vocabulary term does not supply those relations.

### Information geometry and significance

The reference population and feasible alternative space are explicit. Logical state, frequency, association,
rarity and relevance are different quantities. A common item is not thereby unimportant; an unusual item is
not thereby relevant. A genuine zero or orthogonality needs a warrant; not documented is not absence.

Corpus statement frequency describes what the records state. If S of N records state an eligibility element
and U remain unresolved, S/N is a statement rate and [S/N, (S+U)/N] is its full-criteria identification interval.
Unresolved membership and support counts accompany associations and standards. A mechanism-linked exclusion
is a proposal with its evidence, not a causal conclusion from co-occurrence.

Conditional rarity is computed against a declared cell that does not condition on the very predicate being
scored. Presence and absence have different event probabilities. Rarity is a corpus statistic; derivational
significance concerns what the admissible alternatives of a derivation afforded and must identify that space.
Structured disagreement or a verified unexplained deviation is retained as information rather than collapsed
into noise. Near misses use a declared representation and verified differences, not hidden similarity.

Design space can be occupied, unresolved or empty; failed trials still occupy their regions. An empty feasible
region is an exploration lead, while unmet clinical need requires additional evidence. Results are compared
only under declared population, endpoint, measure, unit and time compatibility. Protocol success criteria,
observed comparator results and new planning targets remain separate.

### From a brief to a protocol

The full design is documented in `openspec/changes/add-design-synthesis/design.md`: typed brief and variables;
source/identity binding; scoped assertions; strict and default reasoning; compatible corpus observations;
information geometry and significance; gap-directed source evidence; ranking of admissible alternatives;
questions that close the remaining space; and warranted protocol outputs.

The clinical output covers the requested population, inclusion and exclusion criteria, treatment context,
endpoints and time points, biomarkers and their roles and schedules, efficacy decision criteria and inputs,
safety, exploratory procedures and reusable protocol language. No requested cell authorizes invention.
Evidence gaps remain visible or drive bounded source requests; human decisions are requested where warranted.

A deterministic publication workflow is designed: typed gaps select sections and tables; differential parsers
read the relevant fact type; resolvers bind study, cohort, arm, outcome and time; censors refuse unresolved or
wrong-section evidence. It remains a separate component, not a reporting-MVP prerequisite. A model is never
the default extractor or designer. Any explicitly authorised bounded review utility is a reviewer whose
answers retain their provenance, not a source of registry facts.

## Implementation and acceptance

The current operation map and unfinished integrations are maintained in the two active OpenSpec changes and
agent guide. An incomplete pipeline is not incomplete logic. Conversely, a tested standalone component does
not prove that its intended production workflow is connected. Both facts must be reported accurately.

Layer-one acceptance follows source schema and structure across interventional, observational and
expanded-access records, including atypical supplied fields and empty/missing/malformed boundaries. Clinical
recognition is not needed to make that generic writer correct.

Layer-two recognition, scoped representation, entailment and projection are checked separately. Positive and
negative intent cases test scope, alternatives, qualifiers, referents, time and epistemic propagation through
real consumers. Development examples do not establish generality. Mutation checks pin the behavior specified;
they do not create a warrant for a wrong premise. Identified, abstained and wrong are reported separately.

Simplicity, inspectability and a readable clinical output are requirements. A framework, word list or gate
that obscures the warrant rather than implements it is not justified by an agent's convenience.
