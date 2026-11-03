# Return to the lead: distinguishing evidence requests (tasks 2a.1–2a.3)

Frozen 2026-11-03. Three new files in the shared checkout, untracked, not staged or committed. Copies and hashes
are here (`SHA256SUMS`):

| File | sha256 |
|---|---|
| `TrialLedger/layer2/evidence_requests.py` | `abd04aef31d3b9f424b8abc034c43b9d7b37a88496b854008f91f7b6409038e9` |
| `TrialLedger/layer2/evidence_requests_guide.py` | `83b13f6b2dabd95f96ffb881ca832ddfe942c9c7231322a92d504b8f803387ab` |
| `tests/test_evidence_requests.py` | `4403df12f7268e7c483fafab80a3ced97e7462fe4598f9225c9ffe73861ea20a` |

No other file was edited. Not wired: `service`, `result_semantics`, `guide.py` and the metadata vocabulary test are
yours (see `../SCHEMA.md`, "Lead-owned integration needed"). CLI/MCP integration is not claimed.

## Contract

`../SCHEMA.md` is the proposed closed request/result contract, including the post-review contract decisions at
its end. Public entry point for dispatch: `evidence_requests.evaluate(request) -> dict`, raising `ValueError`
with named codes (`evidence_requests:<where>:<problem>`, `resource_bound:evidence_requests:<what>`).
Discovery fragment: `evidence_requests_guide.INPUTS`, `example()`, `ANSWERS`, `RESULT_GUIDE`, `extend()`.

## Solver reuse

- Every participant check is `entail.eligibility_witness(...)`; every verdict is `design_bounds.witness_verdict`
  under hypothetically satisfied support. No second eligibility solver.
- Survivor consistency uses `entail.decide`. Models are parsed with `assertions.from_canonical`; `service` is not
  imported (it will import this module).

## Measured results (frozen source)

| Check | Result | Receipt |
|---|---|---|
| Authored suite | 55 passed | `receipts/authored-suite.txt` |
| Independent suite (written from the contract only, by a separate agent) | 138 passed | `receipts/independent-suite.txt`; suite in `../independent-tests/` |
| Real-consumer round trip, 60 random families | 737 requests, 0 mismatches against `design_bounds` witness states | `receipts/randomized-roundtrip.txt` |
| Ruff / ty (advisory) | clean / clean | `receipts/ruff.txt`, `receipts/ty.txt` |

The independent suite passes after two recorded contract decisions (`../independent-tests/contract-decisions.diff`):
dotted `where` in refusal codes (house style) and the top-level `input_conflicts` field. Its as-written copy is
retained. It is ready to add as `tests/test_evidence_requests_independent.py` if you want it; adding that file is
outside this contribution's ownership.

## Pins (Detective 1.2.2, policy `9+neg.f5a15364c11d`, two-sign) on the frozen module

| Function | FINAL |
|---|---|
| `family_state` | ✓ COMPLETE (operator universe) · 44/44 killed · minimal cover 3 |
| `pair_relation` | ✓ COMPLETE · 56/56 · minimal cover 6 |
| `pair_outcome` | ✓ COMPLETE · 55/55 · minimal cover 1 |
| `output_state` | ✓ COMPLETE · 18/18 · minimal cover 1 |
| `required_premises` | ✓ COMPLETE (modulo 4 crash-only value gaps) · 34/34 · 2 generated tests |
| `seek` | ✓ COMPLETE · 27/27 · 2 generated tests |
| `dominated` | ✓ COMPLETE · 16/16 · 1 generated test |

Logs: `receipts/converge-*.log`; full command record with exit codes: `receipts/commands.json`; full scratch
run: `../proof-v2/`. The `required_premises` receipt is from the post-fix rerun
(`converge-required_premises.contract-fix.log`); the other six functions' source is unchanged since their
runs. Generated suites are in `../proof-v2/tests/detective/` and were not edited or copied into the checkout.
The first proof run on an earlier snapshot is retained in `../proof/`.

Protocol deviations, all scratch-only: the shared venv's editable install shadows the scratch copy, so
converge was refused until the scratch `pyproject.toml` got the same `pythonpath = ["."]` line that
`detective regime --migrate` wrote in the first run. `pip install -e .` was refused because it would repoint the
shared venv. Refused logs are kept (`*.refused-shadowed.log`). `plan`/`survey` were not rerun on the final
source; the first run's are in `../proof/` (all targets clean; one survey flag on `_head` reads
`dataclasses.replace` as a filesystem write, which my reading says is a false positive).

## CrossHair 0.0.110 (PEP316, `--per_condition_timeout 30`) on the frozen module

17 postconditions confirmed over all paths; no counterexample. Not confirmed (search budget exhausted, status
UNKNOWN, unbounded inputs): `required_premises` lines 144–146 (tuple/str inputs) and `dominated` line 179
(frozenset inputs). Log: `receipts/crosshair-final.log`.

## Counterexamples found and fixed during the pass

1. CrossHair: `required_premises('rejected', ())` refuted the postcondition "accepted iff three premises". The
   function was right; the contract was wrong. Corrected to
   `len(__return__) == 3 + (len(eliminated) if sign == 'rejected' else 0)`, then repinned and rechecked.
2. CrossHair could not construct `typing.Literal` arguments, so two primitives' contracts were never exercised.
   Parameters are now `str` with explicit `pre:` conditions (house style), and `pair_relation` inputs are bounded
   to the four verdicts.
3. Independent suite: a declared variable matching no survivor dropped its `variable_unrepresented` cause on the
   no-usable-variable path (fixed); row shapes simplified (`undecided`/`inconsistent` as id lists, bare coverage
   codes); rows now record the solver `bound` so a replay uses the same limit.

## Finding outside ownership (for your decision)

`../lead-findings/proposed-blocks-accepted-elimination/`: `design_bounds.witness_verdict` refuses an accepted
witness's elimination when the candidate has an unconfirmed reading, even though the refutation rests on known
premises alone and no resolution of a withheld conjunct could undo it. The rejected direction correctly stays open.
Reproduced through `run`; proposed direction-aware fix and tests included. This module inherits whatever
`witness_verdict` does; if the fix adds a direction argument, the one call in `_search` must pass the sign.

## Not done

- No CLI/MCP execution, service wiring, metadata adapter, guide entries or model-operated walkthrough (yours
  after integration).
- No real screening/run-in example was acquired.
