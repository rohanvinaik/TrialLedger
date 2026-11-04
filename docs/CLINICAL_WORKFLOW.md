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

Historical unknowns are evidence questions. Different feasible draft alternatives can be design choices.
Malformed translation needs correction; unfinished computation needs a narrower or adequately bounded run.
Keep remedies separate and retain independently settled conclusions.

## Retain the complete check, retrieve only what is needed

MCP reason accepts explicit delivery controls beside request: `retain:true` or `response_view:"compact"`.
Replace the discovery request above with the actual clinical request. Compact delivery keeps the clinical
projection and artifact reference, backed by the complete canonical request and response. CLI uses:

```bash
trialledger reason --request SESSION_FILE --store STORE --compact
trialledger reason-result --store STORE --id ARTIFACT_ID --part decisions
```

MCP reason_result takes id and a part: summary, decisions, changes, request, result or address. An address
is relative to the complete stored payload, such as `/response/result/decisions/0`. Follow page.next_offset
and text_page.next_offset to complete the requested evidence. An address directory is navigation, not data;
text chunks concatenate unchanged. Reasoning reply budgets accept 2,048–65,536 bytes; the default is
24,576. Full retained files remain the complete handoff.

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
fingerprints and recomputes both complete snapshots. Read answer_diff for independent answer/support/origin
changes and diff for audit-object changes. An unchanged answer with weaker support still matters; changed
inputs alone are not changed clinical answers. The full focused design_session guide retains runnable
baseline/revision examples. CLI uses:

```bash
trialledger reason-revise --store STORE --id ARTIFACT_ID --edits EDITS_FILE --revision revised
```

## Deliver the review

MCP reason_export takes id, optionally source_run and other retained include IDs. CLI uses:

```bash
trialledger reason-export --store STORE --id REVISED_ARTIFACT_ID --out REVIEW_FOLDER \
    --source-record REPORT_FOLDER/landscape.json
```

Deliver actual returned workbook, readable-list and manifest paths. The review holds declared decisions and
alternatives, deciding evidence/premises, consequences, open items, selections, origins and changes. Included
standalone analyses remain separate unless the session binds them explicitly to a decision. The Decision
list and Options sheets are the clinical reading surface; Findings retains detailed codes and typed values
for inspection alongside the complete canonical files. With source
evidence supplied, baseline presentation retains every measurement and matching denominator scope, including
unresolved groups. Never add arms and totals or interpret matching titles as identity.

Keep the original verified landscape.xlsx as the reference sheet. The manifest and exact canonical inputs
let a colleague trace the review. It reflects caller-declared premises and choices, not independent consent
or truth certification. Maintain a narrative working brief with the clinical question, literal accepted
wording and material gaps for the next conversation.

Complete protocol writing remains unintegrated. These operations are the working evidence and reasoning
core supporting the person's clinical design process now.
