# Design

## Context

Baseline is main d2f9f4f. The retained obesity session is outside Git at
`~/trialledger-runs/obesity-clinician-20261104`. Eight executable CLI audit checks established that
BMI28 implies a listed-condition disjunction and prior GLP-1 use implies 180 days, while the explanation
planner emits neither. An equivalent disjunction loses a reported backward condition. The r3 artifact
has no source ledger; decision labels are caller text, and two refined queries retain UNDETERMINED
verdicts but are called clinical-answer changes. A 90-to-180-day deciding rule change retains an unchanged
support signature. Compact r2/r3 files are 302368/328322 bytes; default decision reads require two
directories before alternatives. See proposal.md for scope.

## Goals / Non-Goals

Expose rigorously proved consequences and evidence in the clinician's decision, using shared owners.
The canonical request/result, existing audit diff, source reports and caller attribution survive.
No prose classifier, clinical recommendation, authenticated consent or automatic protocol writer is added.
Condition discovery remains finite and explicitly incomplete; a finished candidate plan is not complete
patient screening. Compound alternatives, scope, units and time remain logical objects.

## Decisions

### 1. Candidate discovery and proof are independent

Extend the shared explanation planner beyond applicability clauses. Generate bounded typed subformula
and profile-residual candidates from admitted constraints, including consequents and preserved disjunctions.
Specialization uses only what the profile establishes, not the criteria being explained. Every displayed
requirement is then verified by the existing scoped solver. Feasibility precedes implication; no vacuous
fact from a refuted/inconsistent profile is displayed. Distinguish necessary-if-profile requirements from
criteria-wide requirements not established by the supplied profile, and omit conditions already established
by that profile. None of these statements claims that the actual person lacks the required feature.

Equivalent conditional/disjunctive encodings must expose the same tested information, without requiring
identical sufficient proofs or claiming exhaustive prime-implicate enumeration. Proposed or unbound rules
cannot supply accepted candidates. Preserve strongest useful compound requirements rather than splitting
Required(A OR B) into individual obligations. Bound planning and solver calls; report enumeration/output
limits explicitly. The same plan feeds solver-work reservation, including any newly joined components.
Public entailment, interpretations and design-bounds consumers retain the explanations.

### 2. Decision evidence has a context role, not an implicit premise role

Add optional `evidence` to a decision; absent remains a valid legacy request and is not inserted into the
canonical caller session. Entries identify a local source, exact existing anchor contract
`{id,address,digest,expected,span?}`, a role `quote`, `reading` or `gap`, and an optional caller note.
Resolve through source_evidence.snapshot/anchors against complete retained sources, before reasoning.
Stale/missing/wrong-source anchors refuse as translation errors. Results preserve exact values/spans,
source identity, source scope and role. Copied wording is known as copied wording only; notes and semantic
readings/gaps are caller-attributed, not computed absence or accepted clinical premises. A confirmed reading
that constrains a design still travels through the ordinary premise ledger and admission path.

No evidence entry changes eligibility, establishes comparability, or joins populations. Context includes
the source location and an explicit source-scope description when supplied; that description remains caller
attribution. A registry passage cannot silently establish crossover/entry applicability.

### 3. One typed display and decision view feeds delivery and export

Provide a pure compositional display of the existing typed proposition: conjunction, disjunction,
negation, values, inclusivity, units and time stay explicit. Predicate names are declared names, not a new
clinical lexicon or certified English interpretation. Unsupported shapes retain exact canonical references
and a named display limitation. Keep caller question/option wording visibly separate from the represented
profile and computed outcome. A feasible negated profile is not rendered as an established exclusion.

Build a shared clinical decision view with question attribution, typed profiles, outcomes, conditions,
full deciding-premise wording/origins, anchored context, open items and canonical references. Attach this
additively to full delivery responses and expose `reason-result`/`reason_result` part `decision_view`.
Existing raw parts remain exact. The view is stored with the artifact so its navigation remains resolvable.
Export consumes this same view; it renders scalar unit/statistic wrappers as readable source values with
separate addresses, rather than raw JSON. Unknown/malformed values remain explicit. Full canonical files
remain the handoff. The atomic out/review publication contract remains and is stated in help.

### 4. Question and warrant changes are separately computable

Retain existing audit diff. Add a question axis and named question/wording changes; changing a typed query
or target must not be described as a changed verdict on the same question. Compare verdict/content after
separating question identity. Caller wording changes remain attributed. Do not claim semantic equivalence
from English or syntactic similarity. Scope changes remain visible even when a status string is unchanged.

Support signatures resolve actual deciding IDs to versioned premise payloads, including their rules,
scope and standing. A 90-to-180-day rule change changes support even if the profile stays refuted.
Unrelated premises do not contaminate the signature, and attribution-only changes remain independently
visible. A separate context axis records changed decision evidence without making it a changed logical
answer or deciding premise. Display consequential decision/question/support changes before input-only or unchanged rows.

### 5. Compact means bounded, not a shallow copy

Keep all canonical artifacts intact. Compact output defaults to the existing 24576-byte reply budget and
returns concise summaries, selected finding/change rows and explicit counts/continuation references.
Do not echo full before/after projections. Oversized fields remain retrievable at exact artifact addresses;
no shortened source text is presented as complete evidence. A self-contained decision view avoids routine
multi-directory retrieval. Preserve material blockers, standing, scope and unknown codes, with explicit
navigation when these cannot fit. CLI and MCP use the same owner and optional bounded byte control.

Expose estimand STRATEGIES from the validator's actual vocabulary through discovery/contracts. Preserve
canonical string warrants and add a structured display query rather than silently rewriting their identity.

## Risks / Trade-offs

- More candidate joins -> conservative reservation, finite planning caps and independent accounting tests.
- Apparent clinical interpretation in display -> compositional typed rendering, caller attribution and
  supported-shape fallbacks; never token matching.
- Source context mistaken for proof -> separate roles and two-sign tests that evidence never changes C.
- New comparisons hide real scope changes -> explicit question axis plus unchanged canonical audit.
- Compact omission -> total/returned counts and exact continuation; no unlabelled truncation.
- Legacy result fixtures -> preserve protected outcomes; document additive fields and deliberate diff changes.

## Migration Plan

Keep old requests valid and old raw artifact access unchanged. Add evidence, views and comparison metadata
without changing the source record. Reconcile examples with protected-payload checks. Verify real CLI/MCP,
old obesity counterexamples and fresh clinical questions in other phases/areas after substantial increments.
Use SICP-style atomic decisions, direct authored positive/MUST-NOT tests, explicit Detective two-sign walks
and CrossHair with report_all. Preserve incomplete outcomes honestly. Run the stable ordinary gate; the
previous extended whole-project audit waiver remains separate. Commit coherent changes on main.
