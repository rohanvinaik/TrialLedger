# Wave-1 Detective pins: receipt

Driver: the single proof driver, serial, one target at a time. Protocol: `detective-protocol.md` followed literally (run, read the whole output from a captured log, do what the printed block says).
Invocation: `PYTHONPATH=$HOME/tools/Detective:$HOME/tools/Wesker .venv/bin/detective ...` from the repo root.
Resolution proven: `Detective -> /Users/rohanvinaik/tools/Detective/Detective/__init__.py`, `Wesker -> /Users/rohanvinaik/tools/Wesker/Wesker/__init__.py`.
Entry chain: `detective --help` (first block: `detective regime`), `detective regime` -> "DONE: this regime resolves cleanly" (flat, testpaths tests, marker declared).
Logs (captured whole): `/tmp/pw1/*.log` (not committed). Reports: `.detective/reports/converge_<fn>.txt`.

## Hashes (sha256)

Start (frozen) and end, unchanged by anyone but me (checked after the numbers, schedule and objects groups, and at the end):

| file | start | end |
|---|---|---|
| protocol_numbers.py | 6cadefa997401ccc41d951549cf09337c9f436bc10cfb097712d2d8cb88979f8 | same (no edit) |
| protocol_schedule.py | e9f91e91be9e3b1e03aaf38cd63e5755299023a8d6ea33a23f4cf9d1e461e758 | 5e31fe6870e816bda03affe85650f22071d7113dabedc27915dfadfbaec3bcd3 (only tag text added on 2 docstring lines (full_window_outcome, schedule_code)) |
| protocol_objects.py | 8833d6d7b12e20248a8875421922cfc8fc3ae33eca354bf17c84a08632e1c582 | 596a1e10f6c108fb3d43e71c22608ad5f7ef6de921a556610174a619af4702b4 (only tag text on 5 docstring lines) |
| assertions.py, entail.py, source_evidence.py | 9fc3de90 / 48727bc4 / 0cd06238 | same |
| tests/test_protocol_numbers.py, _schedule.py, _schedule_oracle.py, _objects.py | 06fa74d5 / af3842bb / 5cfadd4b / 0c1760b6 | same |

No hash drift outside my own writes. Full hashes: start list recorded in `/tmp/pw1/hash0.txt`.

## Command chain per target

Plain chain per target: `converge T` (bare) -> read -> printed action -> `converge T --two-sign` (named by `audit T --two-sign --check`, the form `scripts/ci_local.sh --deep` runs) -> `audit T --two-sign --check`.
Exceptions to bare converge: rational_syntax (extra `--input`, `flag`), identity_state (extra `--input`), both as the printed block prescribed ("supply the distinguishing value(s) with --input").
`detective diagnose` was run only for rational_syntax, interval_shape, interval_order, existence_outcome (read-only; its block for the others was skipped as unnamed by the regime block).

## Status table (literal terminal lines)

Two-sign column is the terminal line of `converge T --two-sign`.

| target | plain converge | converge --two-sign | tag |
|---|---|---|---|
| numbers::rational_syntax | `COMPLETE (operator universe . modulo 5 unproven-equivalent . 1 crash-only value gap) . 26/27 killed` then after inputs+flag `COMPLETE (... modulo 1 crash-only value gap)`; | `COMPLETE (operator universe . modulo 2 crash-only value gaps) . 54/55 killed . policy 9+neg.f5a15364c11d` | already present; earned |
| numbers::interval_shape | `COMPLETE (operator universe) . 9/9 killed` | `COMPLETE (operator universe) . 28/28 killed` | already present; earned |
| numbers::interval_order | `COMPLETE (operator universe) . 19/19 killed` | `COMPLETE (operator universe) . 47/47 killed` | already present; earned |
| schedule::existence_outcome | `COMPLETE (operator universe) . 10/10 killed` | `COMPLETE ... 38/38 killed` | NOT added (see line-length) |
| schedule::nominal_outcome | `COMPLETE ... 15/15 killed` | `COMPLETE ... 61/61 killed` | NOT added (see line-length) |
| schedule::full_window_outcome | `COMPLETE ... 10/10 killed` | `COMPLETE ... 38/38 killed` | added |
| schedule::determined_by | `COMPLETE ... 35/35 killed` | `INCOMPLETE:  property_render_timeout: the remaining execution deadline is exhausted` | OFF |
| schedule::missing_inputs | `COMPLETE ... 19/19 killed` | `INCOMPLETE:  property_render_timeout: the remaining execution deadline is exhausted` | OFF |
| schedule::outcome_class | `COMPLETE ... 13/13 killed` | `INCOMPLETE:  property_render_timeout: the remaining execution deadline is exhausted` | OFF |
| schedule::schedule_code | `COMPLETE ... 14/14 killed` | `COMPLETE ... 42/42 killed` | added (replaced "(pure)") |
| objects::identity_state | `COMPLETE (... modulo 1 unproven-equivalent . 1 crash-only value gap)` then after inputs `COMPLETE (... modulo 1 crash-only value gap) . 22/22 killed` | `COMPLETE ... modulo 1 crash-only value gap . 41/41 killed` | added |
| objects::ceiling_state | `COMPLETE ... 8/8 killed` | `COMPLETE ... 18/18 killed` | added |
| objects::binding_state | `COMPLETE ... 6/6 killed` | `COMPLETE ... 16/16 killed` | added |
| objects::section_state | `COMPLETE ... 21/21 killed` | `COMPLETE ... 49/49 killed` | added |
| objects::check_pattern_state | `INCOMPLETE:  suite_render_timeout: the remaining execution deadline is exhausted` (141 mutants; pass 0 +4 tests, witness +5) | not run (plain INCOMPLETE, no printed next action) | OFF (was never present) |
| objects::origin_standing_state | `COMPLETE ... 13/13 killed` | `COMPLETE ... 32/32 killed` | added (replaced "(pure)") |

"Tag NOT added" for existence_outcome and nominal_outcome: appending `(pure — pinned)` to their first docstring line makes it 111+ columns and trips ruff E501 (limit 110). I reverted both rather than reflow docstring text I may not edit. Coordinator decision: shorten or wrap the first line, then add the tag (both are two-sign COMPLETE).

## Generated suites (tests/detective/)

- test_TrialLedger_layer2_protocol_numbers_rational_syntax_924fbf0517_synth.py
- test_TrialLedger_layer2_protocol_objects_identity_state_15cdefc842_synth.py
- test_TrialLedger_layer2_protocol_objects_origin_standing_state_1e7e31607c_synth.py
- test_TrialLedger_layer2_protocol_schedule_existence_outcome_665910cbf9_synth.py
- test_TrialLedger_layer2_protocol_schedule_full_window_outcome_ff05a67b66_synth.py
- test_TrialLedger_layer2_protocol_schedule_nominal_outcome_9647768281_synth.py
- test_TrialLedger_layer2_protocol_objects_check_pattern_state_c438979cae_synth.py  (written by the run that ended INCOMPLETE; treat as partial, not a certified suite)
- interval_shape, interval_order, ceiling_state, binding_state, section_state, determined_by, missing_inputs, outcome_class, schedule_code: no suite written (existing tests killed every mutant, or the run was INCOMPLETE).
- `tests/detective/certificates.json` modified by the tool (15 protocol entries `standing: complete`, no entry for check_pattern_state).
- `pytest tests/detective -k protocol`: 23 passed. `ruff check` on the three modules and tests/detective: clean after the reverts.

## Authored tests

None written. The tool never printed an action asking for a test. `tests/test_protocol_pins_authored.py` does not exist.

## Flags and inputs

- rational_syntax: `--input "('1', 8)" --input "('2', 1)" --input "('1', 1)"` killed the STATE x2, BOUNDARY (bit_length ==, ok at the edge) and SWAP survivors.
- rational_syntax: `detective flag ... VALUE_b2e95158` (`value.lstrip('-')` -> `lstrip('')`), recorded equivalent. Note: "RATIONAL.fullmatch admits '-' only as first char of the whole string, so lstrip('-') only affects the numerator; int('-n').bit_length() == int('n').bit_length() (bit_length ignores sign) and int() parses a leading '-', so parts' bit lengths are identical with or without the strip; return value identical for every str accepted by RATIONAL". The two-sign universe printed no unproven-equivalent afterwards.
- identity_state: `--input "('a',)" --input "('',)"` killed VALUE_330d5b92 (`0 < len` -> `1 < len`). Finding: no existing authored test pinned a one-character id as valid; the original authored suite missed it.
- Crash-only value gaps (tool: "detected, not equivalent", nothing to flag): rational_syntax BOUNDARY_df0ce996 (`type(value) is not str` -> `False`), identity_state BOUNDARY_52680a6c (`type(value) is str` -> `True`). No fence recorded.

## Audit read (a discrepancy to decide)

After every two-sign COMPLETE, `detective audit T --two-sign --check` printed a header `... complete[, modulo ...]` and then the same block: `DO THIS:  detective converge 'T' --two-sign`, with the Why "the setup is clean: ... converge writes and pins this function's suite". I ran that converge (twice for rational_syntax); the next audit printed the identical block. I did not read an exit status (protocol). Outcome: I cannot assert that `scripts/ci_local.sh --deep` passes for any pinned decision. Audit also proposes removing redundant authored tests (e.g. rational_syntax: 5; objects: 100+); I did not run `audit --remove` (it edits tests I may not touch).
Audit for determined_by/missing_inputs/outcome_class (run before the converge INCOMPLETE) read `complete, modulo 12 / 9 / 1 unproven-equivalent` under two-sign; no equivalence argument was made for them.

## CrossHair (`.venv/bin/crosshair check TrialLedger.layer2.<m> --report_all --per_path_timeout=5 --per_condition_timeout=60`)

protocol_numbers: lines 25,26 (rational_syntax posts), 54,55 (interval_shape), 66,67 (interval_order): all "Confirmed over all paths".
protocol_schedule:
- 83: error IndexError when calling cmp(_Work(), (0,), (0,)) (`_Work.cmp` contract, a counterexample)
- 91-93 existence_outcome, 107-110 nominal_outcome, 128-130 full_window_outcome: Confirmed over all paths
- 143, 164, 185, 189 (determined_by, missing_inputs, outcome_class): error `'(' was never closed (<string>, line 1)`: the wrapped multi-line `pre:` / `post:` lines do not parse, so those contracts were not checked
- 203, 204, 205 (schedule_code): Not confirmed
- 419, 421 (work_reservation): error invalid syntax / `'(' was never closed`; 437 (check): `ValueError: schedule_data_fields when calling check('schedule_coverage', {}, [])` (precondition not enforced by the contract; counterexample)
protocol_objects:
- 113,114 identity_state; 125,126 ceiling_state; 135,136 binding_state; 145,146,147 section_state; 300,301 origin_standing_state: Confirmed over all paths
- 163,164 check_pattern_state: Not confirmed

## Incomplete targets (exact reason)

- schedule::determined_by, missing_inputs, outcome_class: `converge --two-sign` -> `INCOMPLETE:  property_render_timeout: the remaining execution deadline is exhausted` (printed after "pass 0: N value-survivor(s) — synthesizing killing tests…", N = 11, 9, 1). No next action printed. Plain converge was COMPLETE for each.
- objects::check_pattern_state: plain `converge` -> `INCOMPLETE:  suite_render_timeout: the remaining execution deadline is exhausted` after pass 1 "26 survivor(s) — no progress, at floor" and "witness pass: +5 distinguishing kill test(s) auto-written". No next action printed.
Tags remain OFF for these four. Proof tasks stay unchecked.


## Coordinator notes (2026-11-04)

- **Audit not verified.** `scripts/ci_local.sh --deep` was started and then stopped at Rohan's request: the deep
  gate is deferred until the whole plan is implemented (final serialized proof phase, task 7.4).
  - The tags added here record `converge --two-sign` COMPLETE. Their `audit --two-sign --check` status is
    **unverified**: the driver saw the same "converge again" block after COMPLETE and did not read an exit
    status.
  - The fast pre-push gate does not audit, so the tags do not affect commits. They are re-audited, and kept or
    removed, in the final proof phase.
- **A pre-existing audit failure.** Before the run was stopped, the partial deep log already showed
  `AUDIT FAILED: TrialLedger/landscape.py::results_reading`, a decision that predates this change. The deep gate
  therefore fails at the current baseline regardless of this change, possibly through drift in the local
  Detective checkout. This is recorded for the final proof phase and for Rohan.
- **Partial suite moved out.** The partial generated suite from the INCOMPLETE `check_pattern_state` walk
  (`test_..._check_pattern_state_c438979cae_synth.py`) is uncertified. It was moved out of the repo to
  `~/trialledger-runs/proof-wave1-incomplete/` rather than committed as a pin.
- **CrossHair findings applied by the coordinator.** These are contract edits only: no behaviour change, and
  existing tests re-run.
  - `_Work.cmp` gained `len(x) == 2 and len(y) == 2` in its precondition. The IndexError counterexample used a
    1-tuple, which never occurs in production.
  - The wrapped multi-line `pre:`/`post:` contracts of `determined_by`, `missing_inputs` and `outcome_class` were
    rewritten as single lines so CrossHair can parse them.
