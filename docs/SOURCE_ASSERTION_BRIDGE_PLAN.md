# Source-to-assertion bridge: implementation contract

## Grounding and scope

The main-session natural-language requests and final explanations were reread before this plan. The read
covered the information-theoretic thesis, the source-workflow exploration, the founder's layer-one versus
layer-two correction, the competing-interpretation request and the conversational examples. Tool traffic,
sub-agent thinking and implementation summaries were excluded from the discussion read. The private
conversation is not republished here. This plan applies its requirements; it does not revise the theory.

The instrument is the founder's epistemology in THEORY_OF_THE_CASE and the main-session discussion.
The specimen is the retained NIH record -> assertion/binding -> existing reasoning -> decision-list path.

| Obligation | Kind | Scope | Counterexample / check |
|---|---|---|---|
| Fixed source facts/direct rules bound possibilities | Design requirement | Registered evidence, not independent registry truth | Prose interpretation enters fixed floor without a direct warrant |
| Exact checking can operate under uncertain readings | Conditional derivation | Explicit isolated frames | Proposal discarded as unusable, or admitted as a source fact |
| Location proves quotation, not clinical meaning | Derivation boundary | Content-bound source anchors | Matching text or a valid schema promotes a hypothesis |
| Relationships need their own premises | Design requirement | Population, arm, time, edition, definition | Equal counts/local IDs silently join distinct populations |
| Unresolved information retains partial utility | Design requirement | Independent fixed facts and conditional results | Unresolved binding removes unrelated evidence or implies false |

## Concrete clinical workflow

1. Inspect a retained complete NIH API v2 study, preserving its content identity. Its structured minimum age
   can support a registered general-eligibility age bound under a named schema rule. This does not certify
   the actual protocol or actual participant ages. Missing/unsupported fields produce no restriction.
2. Locate exact passages/cells by JSON pointer, expected typed value, content digest and optional half-open
   Unicode span. Never normalize a passage or search for the first matching label. The same displayed group
   identifier in two modules remains two locations.
3. Describe possible readings with full logical structure, applicability, actor, cohort and time. Each frame
   names the anchors it reads; every clinical interpretation remains proposed. A source-origin label, user
   confirmation, or an arbitrary submitted rule cannot manufacture a source warrant.
4. Copy exact selected counts into hypothetical signals without manual retyping. IPASS's PS 2, never-smoker
   and total counts can feed the existing overlap operator. Its [49,126] result remains conditional on the
   explicit common-universe interpretation, and never becomes an exact observed intersection or PS cutoff.
5. Run the existing operations through the public service. Keep fixed answers, per-reading consequences,
   incompatibilities, unresolved applications and the remaining clinical choice together. Revisions require
   a fresh source binding and recomputation; no record/report is rewritten.

## Frozen public contract

### Cross-channel domain audit

The schedule is one worked decision, not the scope of the admission discipline. Every channel must keep its
own measured object and the clinical binding by which it can inform one or several decisions. Multiple
channels can inform one choice without becoming the same variable, and one channel can inform several
choices without acquiring additional meaning.

| Information channel | Decision it can inform | Binding required / forbidden collapse |
|---|---|---|
| Registered structured eligibility | Which entry restrictions to adopt | Registry general rule differs from actual compliance and the new trial's choice |
| Accepted baseline witnesses | Which eligibility interpretations remain possible | Explicit eligibility/time/scale bridge and exceptions; observation is not the cutoff |
| Attributed rejected profiles | Whether a candidate could explain rejection | A feasible ineligible completion, not universal exclusion or an invented rejection reason |
| Marginals and joint bounds | Which compound populations must be represented | Same universe and assessment scope, no independence or exact joint-count assumption |
| Partitions and complements | Coverage or residual category to plan | Explicit exhaustiveness/disjointness; unreported is not zero |
| Summary statistics | Which boundary/side witnesses constrain candidates | Exactness, statistic convention, units and assessed population; median is not a target |
| Population lineage | Which endpoint population and assessment coverage to use | Explicit parent/subset and cross-table identities; nonmembership is not its cause |
| Time and schedule | Exposure, follow-up, visits or study duration choices | Different intervals/events; preserve nominal targets, tolerance and actual attendance separately |
| Regimen and product structure | Which treatment composition to define | Product/ingredient identity, assigned versus observed role and completeness; list is not simultaneous dosing |
| Directional reference relations | Which entities or classes a constraint can cover | Relation semantics, direction, edition and scope; index/association is not participant membership |
| Adopted endpoint dependencies | Which measurements the design must obtain | Adopted definition, edition, input mode and alternatives; imputed is not observed, unknown is not unavailable |

The bridge carries all eight structural signal kinds through unchanged typed data with proposed support;
cross-channel public tests check their conservation and admission. Existing accepted/rejected witness
operations retain their explicit eligibility bridges and separate consumer contracts; the source bridge
does not invent an automatic witness compiler. A source location never resolves these clinical bindings.
The clinician-facing decision list assembles the channels needed for a choice, retains independent useful
answers, and asks the missing consequential question instead of discarding information or narrowing by guess.

### Domain check: a draft NSCLC trial

Work through an actual design conversation before choosing a projection. A person considering an adult
NSCLC comparison needs separate decisions about the enrollment PS range, endpoint evaluability and visit
tolerances. IPASS's registered minimum age is source context; it does not choose the new trial's age range.
Its baseline WHO PS 2 observations and joint smoking bound do not choose an ECOG range or identify an exact
eligibility ceiling. The population correspondence and eligibility bridge remain separate questions.

For scheduling, nominal day 42 and allowed days 35–49 describe different roles, so treating them as rival
source interpretations would create an unhelpful narrowing. A consequential unresolved distinction is
whether each tolerance remains anchored to randomization or restarts from the preceding scheduled visit.
Both readings retain first window [35,49]. Under an anchored second window the bounds are [77,91]; under
successive gaps they propagate to [70,98]. The existing temporal operation computes these consequences
inside proposed frames. The clinical question is which scheduling rule to adopt or confirm, not which
arbitrarily narrowed point value happens to survive. Actual attendance remains a different event.

Keep nominal target day 42 and allowable window [35,49] as distinct information channels informing that same
decision. Both must remain explicit in each frame, with nominal target events separate from permitted visit
events; nominal second target 84 similarly differs from its allowable second window. A target cannot become
an equality constraint on every permissible visit, and a tolerance interval cannot erase its nominal target.
The public regression must retain both and show that a permitted day-40 first visit can coexist with nominal
day 42. The conversation is an executable domain test of representational adequacy, alongside formal checks.

These are contextual derivations under declared interpretations, not source-certified schedules. They
preserve useful first-window information while exposing the later distinction and its practical effects.

### Request and response

Operation `source_assertions` requires `study`, one raw NIH API v2 study object. Optional fields are
`expected_digest`, `anchors`, `interpretations`, `bindings`, `queries`, `context`, `bound`, `selected`.
Caller-supplied `fixed` material is forbidden. Empty queries support source inspection without pretending a
design check ran. With queries and frames, one generated `interpretations` request is run; without frames,
each query runs ordinary entailment over the mechanically generated fixed assertions.

Snapshot identity uses existing `warrants.study_digest`, a tagged canonical-document hash, distinct from a
raw HTTP-body SHA-256. `study_ref` is `ctg:<NCT>:<digest>` and `version` is that content digest. The source's
last-update object is retained separately; neither timestamp nor content digest invents a protocol edition.
Strict JSON type/finite-value, size, depth and node bounds apply before source processing.

An anchor has `id`, `address`, `digest`, `expected`, and optional `span` with `start`, `end`, `text`.
Pointers have strict RFC6901 escapes and canonical array indexes. Expected values compare exact JSON types;
missing differs from null and bool differs from integer. Spans must reproduce the exact source slice.
An invalid/stale selected address is a named translation refusal, not a clinical refutation.

Templates may use exactly `{"$source":"anchor-id","as":"integer|text|json"}`. Integer conversion accepts
only a whole integer or a complete signed integer string, never bool, rounded decimal, commas or omitted
values. Text stays exact. JSON copy is lossless. Hydration supplies values, never their clinical identity.

Frames use the existing interpretation shape plus nonempty `anchors`. Submitted frames remain unchanged in
the ledger; prepared assumptions and signal support are proposed and carry verified anchor provenance.
Body, alternatives, exclusions, qualifiers, applicability, subject, branch, cohort, temporal role and
resolution remain intact. Existing bindings add nonempty `anchors`; prepared bindings remain proposed with
actual source references, preserving relation, scope and resolution. Wrong applications remain unresolved
through existing binding checks. No automatic joins or corpus insertion are permitted.

The result retains `source`, `anchors`, `fixed`, `interpretations`, `bindings`, `coverage`, `submitted`,
`requests`, `limits`, and `analyses` (complete downstream response envelopes). Generated requests are directly
reusable. Coverage names mechanically compiled versus retained/uncompiled source content and distinct absent,
null, empty, malformed and unsupported states. Inspection and successful compilation never claim complete
clinical semantic coverage.

Initial direct rules cover only structured eligibility `minimumAge`/`maximumAge` with complete nonnegative
integer/NIH age-unit syntax. Units remain as written; no implicit conversion. N/A and unsupported text supply
no bound. No age-group, sex, healthy-volunteer, participant-flow or clinical-prose meaning is guessed.
Further clinical grammars/adapters remain explicit work, rather than an unsafe fallback.

## Ownership and integration

| Owner | Exclusive writes | Contract |
|---|---|---|
| Source evidence agent | source_evidence.py, its tests and scoped receipt | Snapshot, pointers, spans, strict hydration; no clinical meaning |
| Compiler agent | source_assertions.py, its tests and scoped receipt | Structured direct rules, proposed frames/bindings, runnable requests |
| Workflow agent | source_assertions_guide.py, entry-point tests, source-bridge examples, scoped receipt | Discovery and real CLI/MCP examples; no duplicate solver |
| Root | Public service/MCP, global documentation/OpenSpec, integration receipt | Recheck facts against discussion, trace consumers, acceptance and commit |

All work stays on main. No worker commits, branches, worktrees, cross-owner edits, network evidence edits or
terminology-store changes. Root supplies meaning and intent; workers report implementation facts. Root uses
fresh Serena references for existing edits; workers use structural maps and whole-unit reads. Shared source
and target tests freeze before serialized Detective walks. Generated tests remain tool-owned. No old accepted
mutation limitation is reopened. Performance payoff is unmeasured; this is a representational addition.

## Verification obligations

Test actual NIH -> exact anchor/value -> structured premise/proposed frame -> existing solver -> public
returned consequence. Negative cases cover stale/changed records, null/missing/empty/malformed fields,
duplicate identities, wrong pointer escapes/indexes, repeated text, Unicode spans, decimals, numeric bools,
OR/AND, qualified negation, conditional obligation, nonparticipant actor, wrong cohort/time/edition,
cross-module local IDs, unknown versus unavailable, unsupported syntax, proposal promotion and source mutation.
An unresolved object is never a negative fact. Mutation and type checks do not certify clinical semantics.

Use authored two-sign intents and scoped Detective decisions plus meaningful CrossHair contracts where
applicable; follow printed actions and report exact residuals. Run complete project gate, strict OpenSpec
validation and fresh installed CLI/stdio MCP examples with all source bytes unchanged. Report identified,
abstained and wrong separately per supported class against declared expected cases. Teaching cases do not
establish general clinical encoding accuracy. Persist receipts, update assistant context, commit and push
only after the required checks pass.
