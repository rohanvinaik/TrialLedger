# A continuing clinical design workflow

The person supplies the clinical question and makes the choices. The assistant handles evidence access and
precise translation. TrialLedger computes consequences and produces the review handoff. These are public
interfaces; no internal digest function or private session constructor is needed.

## Find evidence and the decision

Inspect capabilities, run doctor, preview the agreed scope and gather the reference workbook. Check
requested-ID accounting. Use record study indexes and exact addresses to inspect relevant evidence, following
all page and text continuations. Keep populations, local groups, denominators, units and time. A publication
link remains a place to investigate, not read evidence.

Ask the consequential distinction: which cohort, required or permitted, one qualifying mutation or compound
mutations, inclusive boundary, nominal assessment or allowed window, same patients or distinct analysis
populations. Show material premises in clinical words from the actual request. Retain accepted wording and
origin; keep unsettled readings proposed and simulations labelled. Caller labels do not authenticate an exchange.

Discover a task with MCP reason:

```json
{"request":{"operation":"describe","view":"entailment"}}
```

The card has a runnable invented example and its boundary. Add `"detail":"schema"` inside request for
structural machine shapes and named field contracts, or `"detail":"full"` for the full focused guide.
Schema acceptance does not establish clinical meaning, admission or source truth. View full retains the
complete manual; delivery describes retained results, revision and export.

For routine design, discover `{"operation":"describe","view":"prepare"}` first. `prepare` lets an
LLM submit explicit typed criteria and a list of questions/options without writing model boilerplate or a
Python script. Its reply supplies `request` (run this next), `defaults` (inspect these), and `origins` (retain
these). Short `all`, `any` and `not` structures keep their logical force; quantities keep their comparison,
units and boundaries. Unspecified standing stays proposed. The expansion is inspectable structure, not
clinical translation or confirmation. Advanced canonical objects remain available.

Retain a large preparation with `response_view:"compact"`, then call MCP reason with
`{"prepared":"ARTIFACT_ID","response_view":"compact"}` instead of a request object. CLI uses
`trialledger reason --prepared ID --store STORE --compact`. This runs the exact retained expansion without
resending it. The computed artifact keeps the complete origin/default ledger; after a revision it is
labelled historical construction, with current premises and explicit edits taking precedence.

To attach comparator evidence through MCP, read `record` with `part:"source"`, the report `run`, `nct`,
and the raw-study address. Follow all continuation offsets. Keep the returned snapshot digest and exact
quote. In a study slot use `{"$retained_study":{"run":"REPORT","nct":"NCT_ID","digest":"DIGEST"}}`
with actual returned values. MCP resolves inside its served root; CLI uses `--source-root ROOT`. The
complete study is retained in the canonical request, so later revision does not reread a mutable source
folder. Attach quotes as decision context; adoption still requires a separate attributed premise.

## Keep the information inside an open answer

Ordinary entailment checks accepted scoped premises. Interpretations explores rivals separately while
preserving the fixed floor. Design bounds uses count witnesses and explicit eligibility bridges to eliminate
declared candidate designs. Signals keeps independently warranted bounds and typed relationships without
inventing joins. Design session declares shared sources, premises, analyses and decision alternatives.

Read results with their explanations. Allowed but not required is useful information. A scoped permission
to use background treatment is not a requirement or an exclusion override. An otherwise open profile can
have a proved necessary condition: “if this NT-proBNP value fits, absence of AF is required under this draft.”
That does not certify all eligibility. Proposed or out-of-scope support stays withheld. Numeric witnesses
keep count intervals, denominators, populations, exception caps and weakest support.

Conditions distinguish `necessary_if_query` from `required_by_criteria`. The latter is required across the
represented criteria but not established by this partial profile. For example, an invented BMI-28 profile
can still need one of a listed-condition disjunction. Do not flatten it into all conditions or tell the
person they lack them. Every row retains a warrant, standing and scope; coverage remains bounded discovery,
not complete screening. The same information survives entailment, rival readings and candidate-design queries.

A decision may carry optional `evidence` entries: id, local source ID, exact `{id,address,digest,expected,span?}`
anchor, role (`quote`, `reading`, `gap`), and optional note/scope. Stale anchors refuse. Exact copied wording
is known as copied wording; annotations remain caller-attributed and proposed, including descriptions of
silence. No context entry becomes a constraint or population binding. Put adopted restrictions in the
ordinary premise ledger separately.

Historical unknowns are evidence questions. Different feasible draft alternatives can be design choices.
Malformed translation needs correction; unfinished computation needs a narrower or adequately bounded run.
Keep remedies separate and retain independently settled conclusions.

For multistage designs, query-relevant scope is distinct from the whole eligibility definition. An open
withdrawal-stage responder criterion does not erase a universal entry exclusion or unrelated residuals.
When a question actually depends on that cohort, specify it. Global inconsistency remains a blocker; a
negative eligibility witness still considers every restriction that could explain rejection.
If a new draft does not represent a choice at all, `unrepresented_design_question` says so without
claiming evidence is missing or that both options were proved feasible. Historical silence remains an
evidence question. An unchanged admission-only source inspection is documentary context, not a failed
clinical comparison.

For an adaptive action table, declare every domain and any forbidden-action condition explicitly. A table
can cover all declared cases and still select a forbidden dose. `prohibitions` checks those cases without
removing them from the feasible domain. Read `prohibition_coverage`, `case_witnesses` and `witness_summary`;
the last distinguishes a complete illustration from a bounded sample. Coverage supplies neither missing
clinical variables nor a general safety, termination or statistical guarantee.
Managed-session reservations use the actual represented domain and all declared guard/prohibition
thresholds; the table's execution ceilings, solver limits and independent illustration bound still apply.

For cross-operation definitions, session `definition_checks` binds each typed reading to an existing
analysis ID and an address beginning `/request` or `/result`, with status, resolution and basis. The check
also declares relation, standing and basis. `implies` is directional; `equivalent` checks both directions;
`disjoint` checks exclusion. Matching targets are required. An assessment trigger at a lower threshold can
intentionally precede an endpoint: test the endpoint-implies-trigger relation rather than claiming that
different numbers contradict. Proposed or unresolved readings stay unresolved. Both the actual addressed
values and the supplied readings remain inspectable beside the fresh solver checks.

## Retain the complete check, retrieve only what is needed

MCP reason accepts explicit delivery controls beside request: `retain:true` or `response_view:"compact"`.
Replace the discovery request above with the actual clinical request. Compact delivery keeps the clinical
projection and artifact reference, backed by the complete canonical request and response. CLI uses:

```bash
trialledger reason --request SESSION_FILE --store STORE --compact
trialledger reason-result --store STORE --id ARTIFACT_ID --part decision_view
```

MCP reason_result part decision_view brings each caller question, typed profile, computed result, full
deciding criteria, context and open items together. Questions/labels are caller wording, not computed facts.
Raw parts summary, decisions, changes, request, result and address remain available. An address
is relative to the complete stored payload, such as `/response/result/decisions/0`. Follow page.next_offset
and text_page.next_offset to complete the requested evidence. An address directory is navigation, not data;
text chunks concatenate unchanged. Reasoning reply budgets accept 2,048–65,536 bytes; the default is
24,576 (`max_bytes` on reason/reason_revise, `--max-bytes` on reason/reason-revise). Compact rows have
total/returned/next_offset and canonical addresses rather than full before/after copies. Full retained files remain the complete handoff.

Artifact ID covers the complete stored canonical payload. Result_digest covers result only, excluding
presentation/artifact metadata. Fingerprints establish retained identity, not clinical truth. Source reports
remain unchanged. Without explicit retention, pure computation still writes no files.

## Revise a declared choice

MCP reason_revise takes the previous artifact id and either a complete next session or bounded edits plus
a revision label. Edits are explicit replace paths in design fields. Changed premises require attribution;
the shortcut refuses edits to copied source snapshots. For example, an age-limit edit may replace
`/premises/0/payload/body/value/number`, supplying the new number and the premise's true origin object.
Use an actual retained path and actual accepted choice; never invent an exchange reference.

Use prepare_only:true to inspect the valid request without running it. The program fills mechanical integrity
fingerprints and recomputes both complete snapshots. Read `answer_diff` for seven independent comparisons:

| Comparison | What the person needs to hear |
|---|---|
| Question | The typed profile, query or target changed; state its verdict separately |
| Answer | The computed verdict, values or consequences changed |
| Support | The deciding premise content, rule, scope or standing changed, even with the same ID |
| Wording | Caller-supplied question or option wording changed; clinical equivalence is not certified |
| Origin | Attribution changed; a saved label does not authenticate confirmation |
| Context | Attached evidence context changed; it did not become a logical constraint |
| Requirements | Remaining conditions changed while the query's verdict can stay unchanged |

Read every entry in `changes`: the primary code names only the first applicable kind. `diff` independently
retains the complete audit-object changes. A sharper query can have the same verdict; an unchanged refusal
can rest on a revised rule. For example, a simulated 60-day profile is ruled out under both a 90-day and a
180-day minimum washout, but the deciding rule changed. Actual deciding IDs resolve to versioned typed
content and standing for this comparison; unrelated replay inputs are not substituted for support.
Changed inputs alone are not changed clinical answers. The full focused design_session guide retains runnable
baseline/revision examples. CLI uses:

```bash
trialledger reason-revise --store STORE --id ARTIFACT_ID --edits EDITS_FILE --revision revised
```

For example, widening ECOG can leave an asymptomatic-CNS profile allowed while changing the ECOG condition
listed beside it. That is `requirements_changed`, not a new CNS verdict. The same comparison is made for
individual option analyses and their parent decision. A genuine changed verdict still uses the answer axis.

## Deliver the review

MCP reason_export takes id, optionally source_run and other retained include IDs. CLI uses:

```bash
trialledger reason-export --store STORE --id REVISED_ARTIFACT_ID --out REVIEW_FOLDER \
    --source-record REPORT_FOLDER/landscape.json
```

The output parent must not already exist. Publication is atomic into its `review` child. Deliver actual
returned workbook, readable-list and manifest paths. The review holds declared decisions and
alternatives, deciding evidence/premises, consequences, open items, selections, origins and changes. Included
standalone analyses remain separate unless the session binds them explicitly to a decision. The Decision
list and Options sheets are the clinical reading surface; Requirements gives each proved residual its own
row with profile, standing and scope; Findings retains detailed codes and typed values
for inspection alongside the complete canonical files. With source
evidence supplied, baseline presentation retains every measurement and matching denominator scope, including
unresolved groups. Never add arms and totals or interpret matching titles as identity.

Included population-stage, decision-table and estimand analyses also appear under Supporting analyses in
Markdown and in Analysis review. Analysis details retains the expanded basis and open items in readable
parts; full Findings remains available. A summary preserves the returned population/denominator, support
and exact result address. A table's many disjoint row pairs do not crowd out its actual gaps, conflicts or
forbidden selections. Session definition checks appear with their declared relation and conditional warrant.

Keep the original verified landscape.xlsx as the reference sheet. The manifest and exact canonical inputs
let a colleague trace the review. It reflects caller-declared premises and choices, not independent consent
or truth certification. Maintain a narrative working brief with the clinical question, literal accepted
wording and material gaps for the next conversation.

Complete protocol writing remains unintegrated. These operations are the working evidence and reasoning
core supporting the person's clinical design process now.

## Check a protocol plan

When the person drafts assessments, a dose or stopping policy, a single-arm binomial design or two competing
plan edits, discover `{"operation":"describe","view":"protocol","detail":"full"}`, take the relevant
family example's shape, prepare it with the person's declared objects, run the prepared request, then
revise and export as above. The [README's protocol conversation](../README.md#a-protocol-plan-in-practice)
shows each call. An instructed plan change is revised with `reason-revise --edits` giving a new object version
under the person's origin; the adoption of that version is recorded with it (`delivery` lists it as
`adoption_of_instructed_version`). Content changed under an unchanged version is refused. A what-if stays
hypothetical and adopts nothing. Read the plan comparison by alternative (compatible, repair choice open,
undetermined, incompatible), and `answer_diff.protocol_checks` / `protocol_decisions` by axis. The export
adds protocol synopsis, findings, schedule-of-assessments, plan-comparison and adoption sheets. This is a
check of declared intervals, variables and parameters: not a judgement of clinical appropriateness, safety,
validity or completeness. Adaptive, cluster and survival calculations, sample-size search and the protocol
writer are not built.

## Keep permission, requirement and choice separate in the review

The main decision and option sheets include permission mentions, with their applicability, scope, standing
and references; the Permissions sheet keeps each mention inspectable. A proposed mention stays unconfirmed,
and a missing mention is not a prohibition. A permission never overrides a separate exclusion or certifies
entry eligibility. For example, permitting stable inhaled treatment and requiring adequate stability are
two information channels, even when they inform one clinical choice.

Open items name the caller-labelled option they concern. “This exact query is allowed but not required”
means the represented proposition and its negation fit. It does not say that every option listed for the
decision fits: a two-week minimum permits exactly two weeks and longer intervals while ruling out one week.
The wide decision/option sheets keep identifying columns visible during horizontal scrolling.

Related source-bound competing readings can be included in the export as separate findings. Their original
scope and conditional warrants remain intact; inclusion does not adopt a reading or assign it to a decision.
When an assertion's content is revised as a user choice, the shortcut updates references to the old adoption
exchange and records those mechanical edits. Independent source citations and prior artifacts stay intact.
This is consistent attribution of a declared choice, not authentication of the person's confirmation.
