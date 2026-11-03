# Competing interpretations: implementation contract

## Authorized objective and clinical object

The founder's request, 2026-11-03:

> Excellent. Work this framing into the README and OpenSpec design, then build the layer-two representation for competing interpretations, their premises, and formal warrants for compatibility or refutation. Make sure that if you start to question the exact way something should be wired, how a source can speak to correctness vs useful inference, how this feeds into reasoning about clinical trials, that you ground this with common-sense reasoning in the domain space. Literally work it out like a user would, try to actually design the clinical trial, ask the questions that a sane user would, see what the information-theoretic principles are able to usefully guide one towards, while minimizing (1) information that is lost by being unresolved and (2) unhelpfully over-narrow/incorrect inference-driven suggestions that are misleading/incorrect. This folds into the work I had you do with the response before this, the "source-bound population and definition bindings" point you made, as well as the gaps you noted with the admission rules. Let's plan it out and persist it, then blast through with sub-agents to make this complete and correct. Use the same overall discipline of the prior commits you've made today

The theory and semantic-specification framework are the instrument. The clinical workflow and software
are the specimen. This is an intentional new capability, not a same-answer optimization.

| Claim | Kind / scope | Falsifier and check |
|---|---|---|
| Fixed evidence can refute a reading without identifying the intended protocol | Derivation within represented domains | Countermodels and fixed-floor contradiction tests |
| Unconfirmed readings remain useful | Architectural requirement | An isolated hypothesis must produce conditional consequences without entering ordinary entailment |
| Source bindings must affect decisions | Implementation obligation | Population/definition scope revisions must change the public result, not only metadata |
| Surviving readings do not exhaust the actual protocol | Representation boundary | A single survivor must never become a globally known fact merely by survival |

## Work it as a trial designer

The user is designing an adult NSCLC trial and considering ECOG 0–2 or 0–3, a comparator-like assessment
schedule and safety/QoL analysis populations. The decision list remains the clinical output.

1. **Population:** keep IPASS WHO PS observations separate from the new ECOG choice. Fixed source counts
   constrain a participation profile only through the declared bridge. Ask which scale, population and time
   are meant, not for confirmation of arithmetic. A source observation is not a recovered cutoff.
2. **Assessments:** explore the reading that the first scheduled assessment is 42 ±7 days from randomization.
   Its [35,49] consequence is exact within the reading. Distinguish a proposed scheduled visit at day 28 from
   an actual unscheduled scan at day 28. Their different roles must prevent a false conflict. Rival anchor
   readings stay separate and inspectable.
3. **Analysis populations:** retain ITT, EFS and EFQ as distinct sets. Conditional cohort correspondence
   permits today's subset/overlap arithmetic. An unresolved correspondence must retain source counts and
   conditional calculations while preventing unsupported pooling or unconditional conclusions.
4. **Endpoint definitions:** an adopted observed-only definition licenses its prerequisites within its scope
   and edition. An imputed measurement is a different input. Unknown availability is an open question;
   explicitly unavailable required input can refute a hypothesized plan under that definition.
5. **Source cleanup:** retain original text and proposed/effective interpretations separately. A typo candidate
   or approximate terminology match cannot establish identity. This increment provides binding and warrant
   representation; automatic text repair, external retrieval and complete protocol generation remain separate.

## Public request and module boundary

Add `reason` operation and focused discovery view `interpretations`. Existing operations retain their
contracts, including ordinary entailment's refusal to use proposed premises. The new operation receives:

- `study_ref`; `fixed` with `assertions` and `signals`; typed `bindings`; `interpretations`; named `queries`;
  optional existing `context`, `bound`, and `selected` interpretation id.
- An interpretation has `id`, `label`, `origin` (assistant/user/source), `basis`, `assumptions` (existing
  scoped assertion objects), local `signals`, grouped `signal_claims`, and `binding_uses`.
- A query has `id` and tagged proposition `body`. No caller-supplied result or verdict is accepted.
- A binding has `id`, `kind` (population/definition), `relation`, `subjects`, `scope`, `sources`, `status`,
  `resolution`, `basis`. Scope names `study`, `population`, `arm`, `time`, `version`. Sources retain
  `ref`, `version`, `address` and optional `digest`. Explicit scope uses never join on titles/counts alone.
- A binding use has `binding`, target `signal` id and the declared `scope` for that application. It is checked
  against the binding and target operator before the target may supply an admitted branch result.

`interpretations` owns isolated frames, named compatibility decisions and warrants. `interpretation_bindings`
owns binding models, strict parsing and use checks. `service` owns public request translation using existing
assertion/signal/context validators; `interpretations_guide` owns discovery. Existing `entail`, `signals`,
numeric/graph/dependency operators remain the single reasoning implementations. Layer one never imports the
new modules. No runtime dependency is added.

## Standing and result contract

Fixed evidence is checked independently first. An inconsistent fixed floor blocks closure for every frame,
without entailment by explosion. Proposed or unresolved material cannot masquerade as the fixed floor.

A frame is an explicit hypothetical environment. Proposed assertions/support can be assumed **only inside
that frame**, with original inputs and hypothetical premise ids retained. Exact solver consequences remain
labelled conditional; this is never an admission to source truth, ordinary entailment or corpus counts.
Scoped applicability, qualifiers, alternatives, units and time survive the local assumption adapter.

Return the fixed-floor query answers; every frame's original premises; its conditional calculations and
query answers; binding checks; compatibility state; warrants naming rules, fixed references, assumptions and
blockers; surviving/refuted/unresolved frame ids; and a consequence per query across the declared survivors.
Keep source conflict, internally incoherent frame, fixed-floor refutation, compatibility and unresolved
checking distinct. Compatibility means satisfiable, not true or clinically recommended.

Only supported fixed evidence can supply a fixed-floor refutation. A conflict relying on an interpolated
floor is explicitly conditional on that floor. Binding scope mismatch is an unresolved application, not
proof that the clinical design is impossible. Unresolved frames remain possible and block overconfident
common consequences; their computed partial values remain visible. A sole survivor is still conditional on
the declared family; family exhaustiveness is never inferred. Selection is a user choice, cannot admit a
refuted frame, and triggers a full recomputation without promoting standing.

## Ownership contracts and sequence

1. Root: persist and reconcile OpenSpec/README; inspect consumers; own service translation and integration.
2. Core agent: only `interpretations.py`, `tests/test_interpretations.py` and its scoped verification receipt.
   Public engine interface and frame/query dataclasses are fixed by the root before coding. No service/docs,
   existing solver edits, branches, worktrees, commits or external messages.
3. Binding agent: only `interpretation_bindings.py`, `tests/test_interpretation_bindings.py` and its receipt.
   No source fetching, identity guessing or source mutation. Report facts and concrete counterexamples.
4. Workflow agent: only `interpretations_guide.py`, `tests/test_interpretations_entrypoints.py`,
   `examples/interpretations/` and its receipt, after the request shape is fixed. Exercise real CLI/MCP,
   clinical decisions, counterexamples, revisions and source isolation. No overlapping edits.

All agents use whole-unit reads and a read-only Aider map for orientation; no text search or agent-owned
Serena servers. Root supplies meaning and intent; agents supply implementation facts and test evidence.
Before editing existing symbols root checks references. Changes stay on main and are reviewed together.

## Acceptance obligations

- Positive and negative authored tests: distinct rival frames, fixed contradiction, wrong scope, unsupported
  query, malformed/null/empty/duplicate inputs, OR versus AND, unknown versus false, proposed standing,
  missing versus unavailable input, planned versus actual time, observed versus imputed, resource bounds,
  competing bindings, non-exhaustive single survivor, selection/refutation and revision recomputation.
- A finite small-world oracle checks frame compatibility against direct enumeration independently of solver
  verdict dispatch. No source fact becomes false merely because an interpretation is refused.
- Real CLI and MCP discover and execute the same requests; saved example results agree; fixed evidence and
  all original request objects remain unchanged. Trace binding → signal check → frame decision → query answer.
- Converge new literal-typed pure decisions with Detective's explicit full two-sign policy, follow printed
  next actions, retain complete receipts and distinguish tool limitations from passes. Do not restart the
  prior wave's accepted/unstarted pins. New limits need explicit reporting and the appropriate owner decision.
- Run the complete normal project gate and advisory types, source/report isolation tests and fresh installed
  CLI/MCP paths. Report actual scope, performance unmeasured (no optimization claim), residuals and OpenSpec
  task state. The rest of the complete protocol writer remains outside this increment.
