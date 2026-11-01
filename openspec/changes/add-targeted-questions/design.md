# Design — add-targeted-questions

## Context

See proposal.md. Read in code before designing: GSE `gse/curation/lexicon_builder/residual.py` (`OllamaTransport`:
explicit model, `pin()` against `/api/tags` digest, `_verify_pin` before and after, canonical-JSON prompt from a
typed protocol, `format` = schema, `think` configurable, `temperature 0`, `num_ctx`/`num_predict`, refusal on
context overflow, `done_reason == "length"` an error, identity `model#digest@protocol`), `model_batch.py`
(slot-keyed batches, later); harmonizing `llm_residual.py` (minimal section-limited prompts, local Qwen, JSON
format, cache) and `symbolic_healing.py` (section-aware extraction); Regenesis `puller/sections.py`
(deterministic keep/veto by heading; a refine seam may only add). Local Ollama on an M1 Max (64 GB) holds
qwen3.8:27b (q4_K_M, q8_0), qwen3.5:35b (MoE), qwen3:8b and others; Qwen3.8-27B is the current Qwen release
(Apache-2.0). Codex's reading of the first design: `/tmp/trialledger-consult/auditor_answer.txt` at the time.

## Decisions

1. **A question is a typed object.** `(kind, target, envelope, options, schema)`: `kind` names what is asked
   (`atom_claim`, `untyped_criterion`, `assertion_modality`, `intervention_role`, …); `target` is the claim or gap
   with its ids; `envelope` is text only (below); `options` are closed and always include `insufficient_context`;
   `schema` constrains the answer to the options and requires the cited span's offsets. A question asks one
   thing. The symbolic system decides which questions exist; a model never chooses its context.
2. **The envelope is deterministic and bounded.** The target span with offsets; its heading ancestry (cohort
   headings included); the parent stem it continues; the siblings an explicit conjunction or alternative needs;
   nothing else. It never resolves the relationship itself. Over a byte budget, the question is not sent
   (`envelope_over_budget`), never truncated. Conditions or titles never license an answer the envelope does not
   support.
3. **Transport, GSE's contract.** Model named explicitly; digest pinned and verified before and after each call;
   canonical-JSON prompt `{operation, rubric, question}`; schema in `format`; temperature 0; think as configured;
   explicit context and output budgets; overflow refused; truncated output an error; a call budget required; named
   errors for timeout, connection, malformed envelope. Identity: model, digest, and a protocol digest over the
   schema, rubric, options, inference options and envelope version. Cache keyed by request hash and identity; a
   cache hit is a saved answer, not a new observation.
4. **Answers are validated deterministically.** Exactly one verdict per atom id; the cited span lies inside the
   envelope at its offsets (location, not entailment); options in the closed set; anything else is an audit
   error, never a verdict.
5. **The source manifest.** For each sampled trial: every eligibility piece (heading, criterion, prose) with its
   offsets, and every gap between pieces confirmed whitespace; every registered outcome; every intervention. A
   unit exists for each; the human can see any piece no question touched.
6. **Audit questions.** `atom_claim`: one atom of one criterion, options supported / wrong_value /
   wrong_polarity_or_modality / unsupported / insufficient_context. `untyped_criterion`: a criterion no bank typed,
   options the concept instances of the banks' domains (each with a span) plus none and out_of_taxonomy (with a
   span, counted apart, never an engine error in this wave). Matching is at the concept-instance level ("EGFR or
   ALK" is two instances); a wrong attribute of a captured concept is wrong_value, not also a miss. Untyped is
   split into: no in-scope concept, declined, silently missed. Interventions: a record-stated target claim is an
   `atom_claim` on the intervention's own text; an RxClass assignment is checked deterministically against its
   kept RxClass artifact, never by the model. Outcomes: an endpoint class is an `atom_claim`; a time point is
   graded against the rule that "up to N" is a window, not a scheduled measurement.
7. **Adjudication.** Rows at three levels (unit, atom verdict, omission). Blind first: for the pilot and for
   sampled accepted units, the human records what the envelope supports before seeing the model's verdict. Every
   challenged item and `insufficient_context` goes to the human; a seeded random sample of accepted items,
   including empty outputs, does too. Reported rates are named: errors found among accepted items; the share of
   human-confirmed errors the model accepted; challenges of correct readings; insufficient-context; malformed.
   Uncertainty respects clustering within trials; population estimates carry inclusion probabilities.
8. **Controlled mutations.** For the pilot, copies of real units with a known wrong threshold, reversed polarity,
   an unsupported added atom or a removed supported atom, each with a human-validated expected verdict, measure
   whether the model challenges a supplied answer (anchoring).
9. **The live sample.** Interventional studies; start date 2010-01-01 to 2025-12-31 by the record's start date,
   actual or anticipated as recorded (the type kept); strata = the registry's top-level condition ancestors
   (exact MeSH ids recorded), plus "no condition MeSH" (distinct from healthy volunteers); full id lists fetched
   live per stratum (`fields=NCTId`); independent seeded simple random draws within strata; selected trials
   deduplicated with π = 1 − Π(1 − n_h/N_h) over their strata; a balance table for phase (each registry value,
   combined phases kept as written), intervention type and primary purpose, with gaps filled by a labelled
   supplement. Confirmation pool: sha256(nct) mod 10 < 3, declared now, never drawn for discovery. Kept: id lists,
   retrieval times, seed, code version, membership labels and every resolved record (`resolve --keep`).
10. **The pilot.** 15–20 trials, 80–120 units across all unit types: a probability sample plus a separately
    labelled challenge set (empty atoms, exceptions, conjunctions, alternatives, cohort scopes, multiple instances,
    ambiguous time frames) plus the mutations. Configurations: qwen3.8:27b q4_K_M, qwen3.8:27b q8_0, qwen3.5:35b,
    each with thinking on. Compared per unit type and bank: known errors caught, known omissions caught, correct
    readings challenged, insufficient context, invalid responses, latency, human burden. Criteria are declared before
    the pilot runs; the least costly configuration meeting them is chosen, or the pilot reports insufficient
    evidence. A small pilot finds failures; it does not estimate reliability.
11. **Answers are not readings.** No model call inside `resolve` or `profile`. When an `assertion_modality` or
    similar question later feeds the symbolic system (add-scoped-reasoning), its answer is an overrulable value with
    its provenance, never known.

## Risks / Trade-offs

- [The adjudicator is the founder, not a trial-design expert] → blind references and named rates make his
  burden and his judgments visible; an expert can re-adjudicate the same rows later.
- [Model latency on a laptop] → measured in the pilot; batching a section's questions with slot-keyed output
  (GSE's batch transport) is a later optimisation once per-question agreement is known.
- [MeSH strata mislabel some trials] → strata are for spread, not for claims about a disease; membership kept.
