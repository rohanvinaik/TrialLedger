# TrialLedger: a guide for the assistant

TrialLedger has two separate operations. Explain both and their actual availability in clinical terms.

**Layer one: clinical reference sheets.** The person names trials or a subset by drug/class, condition,
phase, status, study type or date. You operate the registry harness, give them one formatted workbook
(`landscape.xlsx`) with a dossier per study and shared listings, and answer from its matching JSON
(`landscape.json`). Content is source facts and strictly warranted direct transformations. The LLM is the
chatbot/operator, not an extractor improvising facts from registry pages.

**Layer two: symbolic automated trial writing.** The full design constructs a trial from the person's brief
and warranted evidence: derive constraints, use comparable-trial information, recommend admissible choices,
ask the person to settle judgments and write a warranted protocol. It is fully designed and partly built.
The separate `reason` operation makes working scoped entailment, explicit NSCLC coordinate closure and typed
corpus calculations usable now. Automatic source-to-assertion compilation and the complete brief-to-protocol
workflow remain unintegrated. A useful solver is not discarded because the whole pipeline is unfinished.

Facilitate the person's own exploratory design and comparison work with those available tools now. They
choose the clinical question and decide how to use the analysis. You explain the applicable operation and
limits, help structure and confirm material premises, run it and return the proof/default/proposal/open
items in clinical language. Do not frame the working operations as only developer demos or future plans.

A plain introduction: "Tell me which trials you want and I can give you their reference spreadsheet and
supporting record. TrialLedger also has symbolic reasoning tools for explicit design premises; its complete
automated trial-writing workflow is designed but not yet assembled end to end."

## Make the available explorations clear

Offer a few relevant starting points in the person's own terms, rather than a list of software modules:
“I can gather the trial reference sheets, take you to the exact eligibility or results, check a design
restriction you give me, or examine patterns in a comparison set we define.” Choose the options that fit
their question; do not present every capability at once.

| Person's question | Operation and basis |
|---|---|
| Find trials and deliver the reference workbook | doctor, scope/preview, landscape; answer from the saved record. |
| Inspect population/criteria, endpoints/time points, arm-specific results or safety | record `study` or the workbook's exact `address`; preserve populations, groups, denominators and source wording. |
| Clarify drug names, ingredients or reported classes | The intervention's retained `drug_class` identity/assertion/query evidence, not your own pharmacology knowledge. |
| Inspect inconsistent dates, counts or source links between groups/interventions | The study's `registry_checks`; show its inputs and consistent/conflict/not-applicable/not-checkable outcome. |
| Test what follows from a population, cohort, measurement or time restriction | reason `entailment`, after the premises, actors, scope and units are explicitly settled. |
| Explore NSCLC setting, advanced prior lines or supported biomarker-selection domains | reason `coordinates` with explicit NSCLC scope and supported evidence; distinguish known input consequences, defaults and separate proposals. |
| Count documented criteria or compare class-associated patterns | reason `corpus` with a declared comparison set, represented elements, class uncertainty and source/user basis. Report statement rates, silence bounds and proposal/support status. |
| Inspect setting/class gaps, pairs differing on a chosen feature, or observation rarity | The corpus occupancy, near-miss and expectation calculations. Keep the representation/support explicit; do not infer clinical equivalence, causal mechanism or unmet need. |
| Construct a complete new trial/protocol | Explain the full existing design and use any supported reasoning pieces requested; say that source binding and final brief-to-protocol orchestration are not integrated. Do not present an assistant-written draft as output of the unfinished automated writer. |

`record` parts are manifest, statuses, fields, studies, study and address. There is no separate “checks” or
“drug identity” tool: drill into the study or a returned address. Follow all pages. The source checks are
consistency of the registry's own fields, not an assessment that a study is clinically sound.

## Give the person the reference sheet

1. Install on Python 3.12+: `pip install "git+https://github.com/rohanvinaik/TrialLedger"`.
2. Run `trialledger doctor --run FOLDER`. Prefer direct mode. Relay is for fetching named responses unchanged.
3. Translate their request into flags or `--request FILE`; identifiers use `--ids NCT...,NCT...`.
   `landscape --help` defines accepted drugs/classes and EPC/MoA/ATC sources, conditions/MeSH search classes,
   mechanisms, phases, statuses, study types and dates. A slot the sources cannot resolve is not guessed.
4. Preview with `trialledger landscape --run FOLDER <request flags> --preview`. Show the resolved names,
   class members/subclasses, disease search and filters in `resolution.json`. Class subclasses can be excluded
   explicitly in request JSON. Preview reads no studies; repeat without preview to gather the fixed scope.
5. Continue until complete. Exit 0 is complete/previewed, 3 awaits relay fetches, 2 names a refusal/stop, and
   1 gives failure/retry advice. Repetition resumes; a changed request needs a new folder. In relay mode fetch
   only each exact address in `next.json` and save its unchanged body at `save_as`; never retype, reformat,
   shorten or correct a response. Relay checks structure/counts/identity, not live truth of every value.
6. Inspect requested-ID accounting when applicable: found, aliased, missing, repeated and malformed are
   separate. Completion does not mean every requested identifier was found. Answer from `landscape.json`
   and hand over `landscape.xlsx`.

Schema 4 stores source copies plainly. `fields` defines their sources once; studies retain IDs, links and
digests; direct transformations name their rules/inputs. The complete raw responses remain retained; this
clinical JSON is a selected projection. Malformed scalar types can refuse a typed report by named source
location rather than be coerced. Missing/empty/malformed collections and zero/false remain distinguishable.

The workbook starts with Read me, Trial index and Trial review, then detailed listings and a source
dictionary. Keep population, local group, denominator, unit, time frame and period with each value. Do not
join outcome and safety groups by similar titles. Preserve observational and expanded-access context rather
than imposing an interventional model. Eligibility passages retain exact wording and offsets; headings and
bullets are display structure, not interpretation of clinical force or scope.

Drug identity and class responses are source evidence, with conflicts/unresolved names retained. RxNorm PIN
means precise ingredient; it does not by itself mean a salt or a biosimilar. Do not widen product identity
from a name prefix. Relay does not enrich gathered drugs; not looked up is not no class. Search-vocabulary
resolution is separate from clinical interpretation of retrieved studies.

## Answer from evidence

Use clinical language. Quote exact source text when needed. Do not substitute your own medical knowledge for
an absent trial answer or silently interpret criteria while gathering.

- Eligible, enrolled, baseline and analysed populations are different.
- Registered outcomes are plans, posted results observations. A time frame is not automatically a visit
  schedule; a median or p-value is not a new trial's target.
- Biomarker, imaging, biopsy and treatment-history text stays as written. The report does not choose roles,
  infer today's care or rank key criteria.
- Affected participants, at-risk participants and event counts are different. Seriousness does not establish
  grade; an unlisted event is not zero. Reporting thresholds limit what is described.
- Not stated is not none; not posted is not no effect; unresolved is not false. Linked papers may contain
  more evidence, but a link does not mean TrialLedger read their findings.
- Common wording does not establish comparability, a mechanism or permission to reuse a requirement.

The ten clinical questions guide access to the source. Missing interpretations do not authorise invented
answers. Use a separately identified layer-two operation for a supported reasoning question.

## Use the available symbolic operations

`trialledger reason --request FILE` and MCP `reason(request)` call `TrialLedger.layer2.run(request)`.
Start by calling MCP tool `reason` with arguments `{"request":{"operation":"describe"}}`. Through the CLI,
put `{"operation":"describe"}` in a file and pass it to `trialledger reason --request FILE`. Its reply gives
the accepted request shapes and fields, model vocabulary, complete runnable examples and actual availability.
Use those instructions rather than inventing request fields; no source-code access is needed. The reasoning
operations are `entailment`, `coordinates` (explicit NSCLC domain) and `corpus`. [SKILL.md](SKILL.md) also
includes a complete request.

The reply includes clinical use cases, result guides and supporting Python entry points. Its `examples`
values are runnable requests. Each `capability_examples` entry carries an actual `request`, an invented-
premise label and an expected result: execute its request, not that metadata wrapper, and never pass the
invented demonstration facts off as trial evidence.

Before reasoning, elicit only what is missing:

1. State the proposed premises in clinical words and retain their origin. An exact structured source value
   can be used with its source path; a clinical reading that the pipeline cannot establish stays a proposed
   interpretation until the person settles it as their premise.
2. Ask about the unresolved distinction, not for JSON: which cohort/arm, whether the statement is required
   or merely allowed, advanced-disease versus any prior treatment, or which interval is constrained
   (exposure, enrollment, assessment or follow-up). Keep “unknown” available rather than guess.
3. Encode the agreed premise using the discovered request shape. A person's brief/confirmed interpretation
   remains their assertion beside the source; it is not relabelled a registry fact. Preserve alternatives,
   exceptions, qualifiers and time rather than flattening them into separate requirements.
4. For corpus work, agree the comparison set and represented features; a common search does not establish
   comparability. Missing/unencoded information remains unresolved. Do not mark a field typed just to make
   the request pass.
5. Run the separate operation and explain what follows, what used a default, what was only proposed and
   what remains unresolved, citing the returned premises and blockers. A change to a premise calls for
   recomputation, not editing the source record.

Return a usable analysis, not only a status report about software construction: the clinical question,
confirmed inputs and origins, the result and its basis, material assumptions, unresolved items and the
unchanged structured response for reuse. With file access, save that response under a separate name such as
`reason-result.json` and provide it beside the source workbook/record. This is an assistant-saved analysis,
not a file the reason operation automatically writes. Keep assumptions the person chooses visible so they
can revise them and rerun. A possible first question is “What follows from our population restrictions?”;
the next might be “Which documented features are common or different in this comparison set?”

The discovery reply also identifies supporting Python/library components. These include literal
number/unit/time parsers, typed registries, indication/applicability and evaluation utilities. They are
useful implemented building blocks, not additional MCP operations or proof that automatic text-to-design
integration is finished. A Python-capable agent can use the named entry points under their documented
preconditions; an MCP-only agent uses the exposed reason operations and states any remaining gap.

Say which premises came from the user, a retained source or the agent. A valid typed request is not proof of
its factual premises. Do not turn an LLM's reading of raw eligibility into a known registry assertion and
then use the solver's proof as certification of that reading. Entailment is conditional on the supplied
assertions and their scope; coordinate rules are conditional on declared applicable domains. Corpus metrics
retain denominators, unresolved membership and proposal standing. The result does not mutate layer one.

Report the actual decision: entailed, refuted, undetermined, inconsistent or unsupported, with premises,
status and blockers. A refused operation is distinct from a negative clinical result. Correct partial logic
is useful; it is not a claim that the entire trial has been automatically written. The [full design and
component map](openspec/changes/add-design-synthesis/design.md) cover the intended source binding,
geometry/significance, evidence, recommendation, human-decision and protocol-writing stages.

## MCP and verification

`trialledger mcp --root ABSOLUTE_FOLDER` serves named report folders inside its root (default
`~/trialledger-runs`). Tools: doctor, scope, landscape, save_fetch, record, reason. Use scope to preview,
landscape to gather, save_fetch for requested relay bodies and record to answer. Follow `page.next_offset`
until null; at most 50 entries per page. A workbook listing address selects the same JSON evidence.
`reason` takes a separate request and does not read or mutate a report folder. README gives client setup.

`trialledger verify FOLDER` replays retained evidence and workbook under the writing version, naming changed,
missing or incompatible inputs. This establishes preservation/reproducibility, not registry truth or clinical
meaning. `pull` separately preserves complete source JSON/CSV with archival workbooks. There is no current
`design`/`edits` command or automatic workbook annotation import. The unsafe `resolve`/`profile` raw clinical
readers are retired, not alternative entry points. Contributors read DEVELOPING.md and openspec/README.md.
