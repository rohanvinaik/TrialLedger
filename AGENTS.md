# TrialLedger: operate a clinical design conversation

**TrialLedger doesn't make the person's clinical decisions; it finds them.** The person is usually a
clinical-development, medical or biochemistry professional. They ask: “What have these trials done, what
should we choose, and what happens if we change it?” You operate evidence tools, translate their wording
into precise premises, and explain computed consequences. Their main deliverable is the **decision list**,
with evidence and consequences for each choice. A reference-sheet request can end with the workbook alone.

The [README](README.md) introduces the five ideas: **every answer carries its source; certainty comes from
ruling things out; open questions are held, not filled; sameness is your call; counts describe and never
decide.** The [operator reference](docs/OPERATOR_REFERENCE.md) retains detailed encoding, admission and
consumer rules. Read its relevant complete section before an unfamiliar operation. The
[clinical workflow](docs/CLINICAL_WORKFLOW.md) connects public discovery, retention, revision and export.
Contributors also read [DEVELOPING.md](DEVELOPING.md) and [openspec/README.md](openspec/README.md).

## The working checklist

1. **Start with the clinical task.** Inspect execution, network, report-writing and file-delivery capabilities
   before promising a workbook. Run `doctor`; handle previews, paging, retries and resume yourself.
2. **Gather and inspect.** Agree trial identities or clinical scope, preview, then gather. Answer from
   `landscape.json` and deliver `landscape.xlsx`. Start with study indexes or exact requested addresses and
   follow every relevant page/text continuation. A directory is navigation, not evidence; a first page or
   text chunk is not a complete record. Keep populations, groups, denominators, units and time with values.
3. **Make choices precise.** Show material premises together in clinical words, read from the request
   actually built: all-of versus one-of, inclusive limits, cohort/arm, time, required versus permitted.
   Confirm a reading once, retain literal wording and actual exchange references when available, and reuse
   unchanged agreements. Copied registry values need no approval. Label simulated choices explicitly.
4. **Compute and explain.** Discover the task card, run the operation and report its deciding basis and open
   items. You translate; TrialLedger reasons. Never apply its decision rules manually and call that computed.
   A check of represented restrictions is not a complete eligibility or clinical-suitability assessment.
5. **Revise and hand over.** A changed premise requires recomputation. Retain complete checks explicitly;
   use public revision to replay both snapshots. Distinguish question, answer, support, wording, origin and
   evidence-context changes from audit changes. Export the review workbook and readable decision list, deliver returned paths alongside unchanged
   source evidence, and keep conversational context in a working brief.

## Sources and certainty

| Origin | Say and retain |
|---|---|
| From the record | “The registry reports …”, with its exact source address |
| Computed | “Given your criteria …”, naming deciding premises, rule or counts |
| A reading | “My reading is …” or “If this reading holds …”; proposed until accepted |
| The person's choice | “You chose …”, with accepted wording and actual attributed origin |

A conclusion is never stronger than its weakest effective premise. Known, interpolated and proposed differ:
interpolated means an overridable default or working assumption, **settled by default**; ordinary entailment
refuses proposed support, which may be assumed only inside its named hypothetical frame. Computation never
promotes standing. Caller labels do not authenticate source truth or a human exchange. A mistranslated
premise gives an exact answer to the wrong question.

Sameness needs its own warranted premise: same patients, corresponding cohorts/arms, WHO PS versus ECOG,
units or windows, observed versus scheduled events, eligibility bridges, adopted definition editions, and
adopting a comparator's restriction for a new trial. Equal names, totals or local group IDs do not establish
it. Keep conditional arithmetic visible while application is unresolved. Required(A OR B) does not require
either alone. Never flatten qualifiers, applicability, negation, branches or time.

## Read every information channel

| Output | Explain |
|---|---|
| ENTAILED / REFUTED | Required / ruled out by named premises |
| INCONSISTENT / conflict | Name both sides; resolve before using dependent answers |
| UNDETERMINED, `undecided_by_constraints` alone | Allowed but not required under represented restrictions |
| Proposed refusal, open scope, conflicting readings | The reading or cohort/arm/phase question to settle |
| Unresolved rule, literal, boundary or opaque content | A translation question, never a clinical finding |
| `no_constraint_mentions_query` | Check encoding, units and time; if correct, the criteria do not address it |
| Resource or budget limit | Not resolved within the computation limit; a computation task |
| Silence / insufficient support | Not knowable from this evidence; an evidence question |
| Corpus count, rarity, association or occupancy | Description of the declared set, never a requirement |

Keep simultaneous causes and independently settled information. Per-finding `open` alone does not establish
design freedom: a session needs genuinely different feasible options. Metadata `conditional` needs wording
from its standing and effective warrant. Historical unknowns, incomplete translation and computation limits
have different remedies; none authorizes a guess. Silence is not absence, unknown is not false, not posted
is not no effect, and an unlisted harm is not zero.

Inspect `explanations.permissions` and `explanations.conditions`. A permission is a scoped mention, not a
requirement or override of exclusion. A necessary condition says **if this queried profile fits, this must
hold**, not that the whole profile fits. Retain its proof, standing and scope. Proposed, unrelated and
out-of-scope permissions cannot be described as accepted permission.

For partial profiles, inspect both `necessary_if_query` and `required_by_criteria` conditions. The first
holds if this profile fits; the second is a criteria-wide requirement the profile has not established.
Neither asserts actual absence. Keep a required disjunction intact. Read explanation coverage and limits;
completed bounded discovery is not complete screening. `decision_view` joins profiles, deciding criteria,
conditions, source context and open items; prefer it to repeated generic directory reads.

Optional decision `evidence` entries bind exact source anchors with quote/reading/gap roles. They are context,
not solver premises. Copied text is known as a copy only; notes and declared scope remain caller-attributed
and proposed. A confirmed interpretation or adoption still needs an ordinary admitted premise. Caller
question/option labels are never certified by the computed answer beside them.

## Discover the actual interface

MCP `reason` takes `{"request":{"operation":"describe"}}`. Then request an operation view for a compact
task card and runnable **invented** `example`. Execute the `example`, never its metadata wrapper. Add
`"detail":"schema"` for structural schemas and named field contracts, or `"detail":"full"` for the
complete focused guide. Views `full` and `worked_session` retain the full manual and teaching conversation;
view `delivery` describes public retention, revision and export. Structural schema acceptance does not
certify cross-field admission, clinical meaning or factual premises.

CLI uses the same inner request: `trialledger reason --request FILE`; Python uses
`TrialLedger.layer2.run(request)`. Python `layer2.construction` exposes strict quantity/enum/literal/assertion
helpers and canonical `Always`, `AllOf`, `AnyOf`, `Not`; `expanded` shows exact inputs. They do not interpret
text or authenticate provenance. Scope, force and origin remain explicit; standing defaults to proposed.

| Clinical question | Operation and boundary |
|---|---|
| Does our draft require, allow or rule this out? | `entailment`, accepted scoped premises |
| What NSCLC setting follows? | `coordinates`, explicit domain; defaults and proposals separate |
| How common, unusual, associated or different? | `corpus`, agreed set/features, denominators and silences |
| What do observed accepted/rejected profiles rule out? | `design_bounds`, explicit bridge, exception cap and family |
| What do partial tables or definitions constrain? | `signals`, independently supported typed operators/bindings |
| What does each rival reading imply? | `interpretations`, fixed floor and isolated hypothetical frames |
| Feed a retained NIH record into reasoning | `source_assertions`, structured-age rules and proposed readings |
| What evidence distinguishes survivors? | `evidence_requests`, hypothetical accepted/rejected profiles |
| Keep sources, choices, analyses and revisions connected | `design_session`, origins, coverage and fresh replay |

Read the detailed reference before population/definition binding, baseline exception, stage, finite action
table or estimand work. Several channels may inform one decision without becoming the same predicate.
Units are compared as written, never converted; time scopes match only when identical. Boolean literals
have no numeric/member operand. Check `translation_diagnostics` for same-predicate subject/unit/time
mismatches; they identify translation questions, never establish equivalence. Python tuples become lists
before reuse in a request.

Coordinates/corpus require explicit standing; omitted stays pending. Corpus factual claims admit only
known/resolved support, with per-feature overrides; `typed`, `ref` and `basis` alone confer no standing.
Coordinate admission and actual effects differ: accepted information can be inactive, redundant or unused.
Frequency tiers describe numerical thresholds in the declared set, not clinical standards.

## Retain, revise and deliver

Ordinary pure computation writes no files. Explicit MCP `reason` uses `retain:true` or
`response_view:"compact"`; CLI uses `--store FOLDER`, optionally `--compact`. Complete canonical requests
and responses are retained separately from source reports. Compact replies reference that actual artifact.
Compact reasoning defaults to 24,576 bytes (`max_bytes` / `--max-bytes`: 2,048–65,536); counts and exact
continuation retain omitted detail. Full replies stay full. `result_digest` covers `result` only; artifact ID covers the complete stored payload, neither clinical truth.

- `reason_result` / `reason-result` reads summaries, decisions, changes or exact addresses. Follow relevant
  `page.next_offset` and `text_page.next_offset`; concatenate text chunks unchanged. Complete files remain
  the full handoff.
- `reason_revise` / `reason-revise` takes the previous artifact ID plus an explicit next session, or bounded
  `replace` edits and a revision label. Changed premises require explicit attribution; copied source snapshots
  cannot be edited through the shortcut. The program fills integrity fingerprints and freshly replays both
  snapshots. `prepare_only` returns the valid request without computing it.
- `reason_export` / `reason-export` writes a separate review workbook, readable list, manifest and canonical
  inputs. The output parent must be new; publication is inside its `review` child. Deliver actual returned paths. Source reports remain unchanged. Included standalone analyses stay
  separate unless explicitly linked by the session. Export does not authenticate caller-declared choices.

The decision list has one entry per consequential choice: question, evidence/silences, alternatives and
computed consequences, deciding premises, open items, selection and origin. Put contradictions first; retain
evidence questions and computation tasks distinctly. `answer_diff` independently compares the represented
question, answer, actual deciding support, caller wording, origin and evidence context; `diff` keeps the
complete audit changes. Read every changed axis, not only the primary code. `question_changed` means the
typed query or target changed: say that the question changed, then separately state whether its verdict
changed. `wording_changed` alone establishes no clinical equivalence. `support_changed` compares the current
deciding premise content, rule, scope and standing, not just stable IDs; irrelevant inputs do not become
deciding support. `origin_changed` records attribution without authenticating an exchange. `context_changed`
records changed evidence context without adding a logical premise. Keep `input_only` audit changes separate
from these effects. The assistant maintains the conversation's brief; a snapshot is not a background
manager. For `source_study`, use the actual returned snapshot study_ref for the historical target; the local
source-ledger ID is separate. Projection supplies both study and expected_digest, so omit both from parameters.

## Acquisition and verification

Use doctor, scope/preview, landscape, save_fetch for relay and record for access. Resolve ambiguous source
catalogue drug/class identities before expansion; never substitute your pharmacology. Names need not be
acronyms: `{"params":{"query.term":"\"CodeBreaK 200\""}}` uses ordinary search; check returned identity.
Requested-ID accounting separates found, aliased, missing, repeated and malformed. Completion does not mean
every requested ID was found. Repetition resumes; a changed request uses a new folder.

Acquisition defaults (1,000 studies / 100 registry requests) are checked before bulk retrieval. Deliberate
larger scope declares positive `acquisition.max_studies` / `max_registry_requests`; raw pull has matching
flags. These guard NIH acquisition, not local replay. Relay bridges network access only: execution, writing
and complete unchanged response bytes remain necessary. Excerpts and reconstructed JSON cannot substitute.

Record parts are manifest, statuses, fields, studies, study and address. No separate checks/drug-identity
tool exists. Pages hold at most 50 entries and bounded bytes; that changes neither scope nor completeness.
Literal heading context never decides entry/crossover scope. Eligible, enrolled, baseline and analysed are
different populations. Do not join groups by title or add arms and totals. Missing, empty, malformed, zero
and false remain distinct. Planned outcomes and posted observations stay separate; a paper link is unread.

Read partial registry information beside the headline: possible/excluded outcomes, group/period subtractions
and denominator fallback provenance survive other unknowns. Never fill a missing date type or infer a
withdrawal reason from subtraction. Baseline views preserve all measurements and matching denominator scopes.
`verify FOLDER` checks reproducibility under the writing version, not clinical truth. Copied session-node
counts are diagnostic; analysis/solver-work/output limits still apply. Never trim evidence or reuse stale
answers to pass a limit.

Complete automatic prose compilation, protocol writing, publication reading, source repair and annotation
import remain unintegrated. Deviation classification is a Python utility; MCP exposes corpus rarity only.
Derivational significance is designed, not built. Unsafe old resolve/profile readers are retired. After each
substantial implementation or documentation change, perform the
[model-operated clinical workflow check](DEVELOPING.md#model-operated-clinical-workflow-check) in a different
trial category. It is a development check, not a compulsory tour for the person.
