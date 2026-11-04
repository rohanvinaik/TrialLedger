# Wave-0 baseline capture (tasks 1.2, CLI part of 1.1)

Facts only. Repo HEAD 25c6bb5c29513f2159751d29c309620522e32425 (dirty: pyproject.toml, uv.lock modified; change dir untracked).
Environment: `environment.txt` (Python 3.14.7, uv 0.12.13, ruff 0.17.3, pytest 9.2.0, crosshair-tool 0.0.112
(`crosshair --version` is unrecognized; version read from package metadata), detective 1.2.2 (Wesker 1.2.2),
Detective repo ce2a500 2026-10-26, Wesker repo 2fbd029 2026-10-25, openspec 1.14.1).
Full responses live in /tmp/tl-baseline/ (not in repo); scratch store /tmp/tl-baseline/store, export /tmp/tl-baseline/export.

## Example fingerprints (`fingerprints.json`, `examples/`)
`reason --request` with `{"operation":"describe"}` lists 10 operations; `describe view=V` returns a runnable `example`
for: prepare, entailment, coordinates, corpus, design_bounds, signals, interpretations, source_assertions,
evidence_requests, design_session. The prepare view also has `session_example` (recorded as prepare_session_example).
Views full, worked_session, delivery have no `example`. 11 requests, each run twice: all exit 0, code `complete`,
stdout byte-identical across the two runs for all 11 (no nondeterminism observed). Response sizes 3.9 KB to 102 KB.

## v1 lifecycle (`lifecycle.json`, `lifecycle/`)
1. `trialledger reason --request lifecycle/01_design_session.request.json --store /tmp/tl-baseline/store --compact`
   -> complete, artifact 9b4a5bfa...054f1, result_digest 40233c6a...48b0baf65869054f1 (see json). 4 findings (3 open, 1 settled).
2. `reason-result --part summary` (7 rows) and `--part decisions` (1 decision, 24,429 bytes): both next_offset null, no text_page.
3. `reason-revise --edits lifecycle/02_edits.json --revision two --prepare-only` -> code prepared (keys code, request,
   previous_artifact, edits). The edits file must be a bare JSON list; wrapping it as {"edits":[...]} was refused with
   `invalid_revision_edits`. Edit: replace /premises/0/payload/body/value/number 18.0 -> 21.0 with origin
   user:adult-21-baseline-check. The program also recorded a mechanical rebind of /premises/0/payload/criterion_ref.
4. Real revise -> artifact f74fe87d...69cc0 (151,901 bytes), result_digest 62edc4aa...a0992aa0f.
   answer_diff: analysis `older`: support_changed (support, origin changed); analysis `younger` and decision
   `age-policy`: requirements_changed (support, origin, requirements changed). question, wording, answer, context unchanged everywhere.
5. `reason-export --id f74fe87d... --out /tmp/tl-baseline/export` -> complete, no problems. Files (sha256/size in lifecycle.json):
   design-review.xlsx (21,116 B), decision-list.md (3,561 B), export-manifest.json (648 B), artifacts/<id>.json (151,901 B).
Note: xlsx hash may not be reproducible across runs; not tested.

## Counterexamples (`counterexamples/`)
4a. TIM-1 temporal via `signals` kind `temporal`: events [origin, assessment], unit day, origin=origin; constraint 1
   lower 77 upper 91 both inclusive; constraint 2 (the collection limit) as a second record on the same pair, lower null, upper 80 inclusive.
   Returned code `complete`, signal code `consistent`, value.bounds:
   origin->assessment lower 77, upper 80, both inclusive; assessment->origin lower -80, upper -77, both inclusive.
   So the actual feasible range is [77,80], matching the design text. Request/response: tim1_temporal.*.json.
   Reproduction used two constraint records on one event pair (accepted). Operation computes bounds only; no separate existential-feasibility field.
4b. Design session = describe design_session example + premise `overlap-sig` (kind signal, payload = signals example overlap)
   + analysis `overlap-signal` (operation signals, uses overlap-sig slot signals identity) + decision `age-policy` alternative
   `younger` pointing at analysis `overlap-signal`. Result: exit 2, code `refused`, problems ["alternative_requires_exact_entailment_query"], result null.
   An earlier attempt putting the signals inside analysis parameters instead of via a premise use was refused with `projected_slot_collision:overlap-signal` (a different refusal; not the target one).
   Files: exact_query_refusal.request.json / .response.json.
