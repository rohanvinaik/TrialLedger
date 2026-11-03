# Where computed information goes

A source tells us what was recorded. A clinical reading supplies a possible meaning. A calculation tells us
what follows under those premises. Each handoff must retain all three, with the scope that makes it valid.
The complete automatic clinical-text compiler and trial writer are still unbuilt.

## Read each finding's answer and completion separately

Every public `reason` envelope now carries additive `metadata`, version 1. Its `findings` point to the
actual results with JSON pointers; the original operation payload remains available. Discovery is marked
`discovery`; a source inspection with no analysis is `inspection`, with no clinical findings.

Each finding retains its effective logical result, support standing, computation completion and all named
causes. A completed request can contain an unfinished calculation. `resource_bound` means not resolved
within the computation limit, not that more medical evidence is required. Premise, translation, coverage
and evidence causes remain distinct; unfamiliar codes are retained as `unclassified` rather than guessed.

An interpretation's raw solver result can differ from its effective answer after a binding or frame gate.
Read `logical_result` and its deciding warrant; `raw_result`/`raw_path` preserve a different ungated answer
without promoting it. A fixed adult-age answer can stay settled while another frame is computation-limited
and a third has an unconfirmed reading. Conversely, an established contradiction is not erased because a
different check ran out of resources: its conflict and the unfinished check both remain visible.

Metadata is computed from the existing operation results. It does not certify their source meanings,
recover missing premise origins, declare an open historical fact a clinical choice, or make corpus counts
clinical recommendations. The focused `describe` replies document the envelope and metadata fields.

Eliminated candidates retain `elimination_status` from the deciding witness or signal checks; their query's
support cannot replace that support. Known eliminations are settled, and weaker eliminations remain
conditional. Unresolved candidates receive no invented standing. Exact corpus counts and comparisons use
`descriptive`: their arithmetic describes the declared set without settling a clinical choice. Pending
features, unknown occupancy and proposed associations keep their open or conditional states.

Choose wording for `conditional` from `standing` and the effective warrant. Interpolated support means
an overridable default or working assumption; proposed support means an unconfirmed reading, refused by
ordinary entailment and explored only within its hypothetical frame. `open` alone establishes neither a
clinical choice nor an evidence gap. Current metadata has `causes`, not `uncertainty_causes`, and carries no
normalized `origin` or `coverage` fields; inspect the actual premises and operation-specific scope. Planned
session projections will add those distinctions from declared questions and dependencies.

A refused request has supplied no clinical finding. Its metadata identifies an invalid translation task,
unsupported operation or computation limit, retaining the complete refusal code. An unfamiliar detailed
refusal reason remains a request-repair task by that envelope's contract; unfamiliar reasoning codes outside
that context still remain `unclassified`.

## Existing public consumers

| Input channel | Actual consumer | Admission and preserved limit |
|---|---|---|
| Exact retained NIH field/quotation | source_assertions → existing entailment/interpretations | Snapshot and exact location; named structured age rules alone create fixed assertions. Other meanings remain proposed. |
| Scoped requirement/exclusion | entailment → finite countermodel check | Proposed premises refused; scope, alternatives and qualifiers retained. A decision is conditional on the supplied encoding. |
| Counts, partitions, summaries, subsets | signals → numeric_evidence; selected derived witness → design_bounds → eligibility_witness | Same universe and predicates explicitly bound; interval retained; lower bound alone compared to exceptions. |
| Reported protocol failures and separate target attributions | exception_bounds.prepare/apply → service._exception_application → design_bounds observations/consequence | Exact source anchors and scopes retained; entry-only accepted attribution supplies a floor, never an informative ceiling. Conflicting budgets block dependent elimination. |
| Explicit population/definition applications outside frames | signal_binding_gate.gate_signals → Signal.application_blockers → signals.evaluate → candidate claims and derived_witness | Same gate before every consumer; exact scope blockers and weakest support survive. Proposed bindings remain refused. Raw arithmetic stays visible. |
| Time, assigned regimen, directional relation, adopted definition | signals → graph_evidence/dependency_evidence → grouped candidate claims | Claims against one signal checked jointly; roles, versions and missing/observed/imputed distinctions retained. No automatic joins. |
| Rival meanings and population/definition bindings | interpretations → isolated frames → fixed answers, per-frame checks and common consequences | Proposed assumptions local only; binding applications gate admission; unresolved frames retained; family not exhaustive. |
| Typed NSCLC evidence | coordinate_admission → coherence closure | Known/resolved inputs narrow known; interpolated/resolved inputs only the weaker layer. Pending inputs retained, never conjoined. Defaults remain defaults. |
| Declared corpus elements | corpus_admission → profile frequency | Known/resolved only; all declared trials stay in N; pending-only features retained; no source silence becomes absence. |
| Corpus class comparison | corpus_admission → profile mechanism_rows | Pending relevant inputs withhold their stratum with explicit reasons. Other strata remain usable; a proposed association is an output pattern, not accepted clinical advice. |
| Declared representation and shared predicates | corpus_admission → nearmiss | Pending declared fields withhold that trial. One differing represented feature does not certify full trial equivalence. |
| Setting/class membership | corpus_admission → explicit occupancy projection | Known dimensions retained independently. Pending setting widens to requested settings; pending class remains possible. Empty means no possible member within this supplied set. |
| Declared expectation observations | corpus_admission → conditional_rarity | Known/resolved rows only; original states and pending rows retained. Denominator/support are explicit; no automatic join with trials. |

## Declare the warrant once, retain unsettled details

Discover `design_bounds` for the runnable `exception_example` and closed source/observation/binding
shapes. The example is invented. A recorded protocol violation retains its category and count; it needs
a separate warranted attribution before it constrains entry eligibility. Accepted target restrictions
intersect only for the same failure, scope and profile. Competing proposed readings remain separate.
An empty intersection is a conflict, not zero failures. Different counts combine conservatively by maximum,
never addition. A population-wide floor does not locate a violation in an arbitrary subgroup.

`exception_checks` preserves admitted and conditional floors, a separate supplied upper bound, structural
maximum, sources, rules and blockers. `upper: null` means unknown informative ceiling. Candidate witness
rows cite the check and expose the count threshold. A floor above the ceiling blocks that bridge and the
common consequence; the declared candidates are not refuted by an invalid bridge. These floors concern
exceptions to positive participation-to-eligibility bridges. Applying them to a rejected witness retains
the positive-budget calculation separately and reports `exception_budget_predicate_mismatch`.

Attribution uncertainty blocks a cap only when it can change compatibility. A single reported failure
with possible entry/treatment meanings cannot contradict an independently warranted cap of five under
either reading. `possible_floor_upper` describes the largest floor this selected evidence could supply;
it is **not** an upper bound on all exceptions. Cap zero remains attribution-dependent in that example.
`conditional_interval_state` exposes a conflict if a proposed bridge were adopted, without admitting it.
Irrelevant or inapplicable attributions retain their own support without weakening an independent known
conflict's standing.

Both `signals` and `design_bounds` accept explicit `bindings` and `binding_uses`; discovery provides
`binding_example`. Application checks precede all ordinary consumers, so a wrong arm or version cannot
reach an elimination through a derived witness or a candidate claim. Numerical compatibility does not
establish that two populations are the same. Existing hypothetical interpretation frames retain their
separate assumption rules. Unchanged standalone requests retain their caller-declared binding contract.

Discover `coordinates` or `corpus` for exact request shapes. A standing is:

```json
{"status":"known","resolution":"resolved","basis":["user:accepted-representation-v1"]}
```

It is a declaration of accepted premises, not a certificate of source truth. A named direct source rule can
warrant a known field without asking a person to approve a copied value. An assistant's unsettled clinical
reading cannot acquire that standing merely by being parsed, quoted or marked `typed`.

Coordinates put `standing` on each evidence object. Corpus trials can put it on the whole explicitly agreed
representation, then override an unsettled detail:

```json
{
  "standing":{"status":"known","resolution":"resolved","basis":["user:accepted-representation-v1"]},
  "feature_standings":{
    "elements":{
      "exclusion:brain_metastases=present":{
        "status":"proposed","resolution":"unresolved","basis":["assistant:two-possible-readings"]
      }
    }
  }
}
```

This is a fragment of a trial, not a complete request. The element must occur in its trial's `elements`.
Overrides for `representation` and `predicates` also name exact keys. Separate overrides are supported for
`classes`, `setting_domain`, `typed`, `eligibility_content` and `coverage`. Null or malformed declarations
refuse; omitted declarations stay pending. A precise known feature override can remain usable even when its
trial-wide standing is pending. Interpolated premises remain inspectable but do not enter factual corpus
counts. Use `interpretations` to explore their conditional clinical consequences.

Expectation inputs retain their existing numeric `support` threshold. Their separate `standing` applies to
observations, with `observation_standings` allowing a same-length array of per-row overrides. A known
`not_documented` observation means the declared documentary review found no statement; it never means the
patient type is admitted. An unconfirmed review does not enter the denominator.

## Explain the unresolved information

Frequency reports admitted statement counts and pending declarations separately. `pending_statement_lower`
and `pending_statement_upper` bound the effect of the **supplied candidate readings**; they do not assume
that all missing source text has been represented. Eligibility's separate `lower`/`upper` still bound the
full-criteria rate with unknown silences. `unresolved_pending` records admission uncertainty rather than
falsely calling it source abbreviation. At zero admitted count, `surprisal_bits` is null.

An association or near miss that could depend on pending information carries a named abstention alongside
the remaining results. This initial association guard is deliberately conservative at stratum level; it does
not yet compute tight association bounds over every joint completion of pending features. Pending records
are retained for that future refinement. They are not an empty-set or no-pattern finding.

For performance status, ask which proposition is being transferred between WHO PS and ECOG, for which
population, time and purpose. Neither a shared number nor the scale names prove equivalence. A declared
implication can connect exact propositions; equivalence can be represented as both implications using the
existing Boolean objects. Its scope, rule and standing remain deciding premises. An interpolated relation
cannot produce a known conclusion; a proposed relation is refused by ordinary entailment.

On `no_constraint_mentions_query`, optional `translation_diagnostics` identify exact same-predicate literals
whose subject, unit or temporal identity differs. Different predicate keys are never guessed equivalent.
The diagnostic keeps both identities, paths and premise standing. It explains a possible representation
mismatch without changing the logical decision or proving any medical mapping.

## Migration and unfinished work

Older coordinate/corpus requests without standings still run, but their readings now remain pending rather
than entering factual calculations. Add known/resolved declarations only where actual source rules or
accepted premises warrant them. Re-run the request; do not relabel old results. Historical outputs belong
to their writing version. Low-level Python profile/coherence functions retain documented typed-input
preconditions; the public admission boundary is `TrialLedger.layer2.run`, CLI reason and MCP reason.

General source-to-scoped-assertion compilation, ontology/measurement bindings, full default conflict strata,
tight association-completion bounds, automatic downstream orchestration, significance, recommendations and
complete protocol output remain work. The compiler must resolve every construction it can warrant and
preserve alternatives for everything else. A blanket confirmation step or a successful JSON parse is not a
substitute for those symbolic decisions.

## The same conservation obligation in reporting

The date check's `information.completion` records outcomes over the stored DateType/PartialDate codebook,
with possible outcomes, excluded outcomes, blockers and a named basis. The headline check stays separate.
IPASS's missing start type leaves consistent/inapplicable open while ruling out conflict over valid
completions. Malformed dates/types leave completion unresolved and provide no exclusions. This uses no
layer-two import and does not choose missing source values.

Independent malformed adverse-event entries remain explicit without erasing other established conflicts.
A Safety row can display its uniquely bound group-total risk fallback, naming the group source and rule in
Notes; explicit zero wins and an unbound group never supplies a denominator. Mixed serious/other collection
availability preserves each independently known count. Flow reason-accounting also retains its separately
computed not-completed quantity, group, period, source and rule under `information.calculations`; an unknown
reason count does not explain or erase that quantity. Reporting checks version 3 identifies the behavior.

The [verification receipt](../acceptance/information-handoffs-2026-11-03.md) records observed checks and the incomplete admission two-sign pin without promoting it to a pass.
