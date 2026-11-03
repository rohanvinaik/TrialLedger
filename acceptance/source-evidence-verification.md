# Source-evidence verification

## Scope and contract

Owned files are `TrialLedger/layer2/source_evidence.py`, `tests/test_source_evidence.py`, and this receipt.
The implementation was checked against `docs/SOURCE_ASSERTION_BRIDGE_PLAN.md`. It neither fetches data nor
reads or writes report folders, edits retained evidence, chooses clinical bindings, or interprets text.

The production consumer being integrated is the compiler in `TrialLedger/layer2/source_assertions.py`.
The compiler owns clinical rule application and provenance attachment to symbolic requests. This module
supplies only bounded location and explicit value substitution.

`BridgeError(ValueError)` carries a named translation-refusal string. Snapshot identity is the existing
tagged canonical-document `warrants.study_digest`, not raw-response SHA-256. The exact snapshot shape is:

```text
{nct, digest, study_ref: "ctg:<NCT>:<digest>", version: digest,
 last_update: exact lastUpdatePostDateStruct object or null}
```

Content version is not a clinical protocol edition. The NCT identifier must match `NCT` and eight ASCII
digits in full. The raw study must be a strict finite JSON object with object-valued protocol and identity
modules. An explicitly malformed status module or scalar last-update object is refused, rather than silently
treated as absent.

Anchors require the closed shape `{id,address,digest,expected}` with optional `{start,end,text}` span.
Identifiers are nonempty and distinct, at most 256. RFC 6901 escapes decode once; array indexes are canonical
unsigned decimal. Expected values compare recursively with exact JSON types, so boolean is not integer and
null is not a missing location. Unicode spans use half-open Python character offsets and must equal the
exact selected string slice. Repeated words retain the submitted offsets; no text search is performed.

A located result has `{id,address,digest,value,ref,source,code:"located"}`, plus its exact span when supplied.
`source` is `{ref:study_ref,version:digest,address,digest}`. `ref` is `study_ref#address`, extended by
`:chars:start:end` for a span. The full addressed value and the exact quoted slice remain distinguishable.

Hydration copies the template and resolves only exact `{"$source":id,"as":mode}` markers. A span selects
its `text`; otherwise the full value is selected. Modes are `integer`, `text`, and `json`. Integer mode
accepts actual integers excluding booleans, or complete ASCII decimal strings with optional sign. Leading
zeroes in source strings are allowed; whitespace, commas, floats, decimals, exponents and Unicode digits are
refused. Text requires a string. JSON preserves types and nesting. Source JSON that itself contains a
`$source` property remains literal. No source value, template, input anchor, snapshot or located result is
mutated, and returned collections are independent copies.

Strict JSON is bounded to 4 MiB of compact UTF-8 serialization, depth 64 from root depth zero, and 100,000
JSON values per copied object. String keys are required. Nonfinite floats, non-JSON Python values and invalid
Unicode are refused. Snapshot, anchor declarations, located output and template are checked; hydrated output
is bounded during construction, including repeated expansions and depth at the insertion location.

## Executed scoped checks

Final scoped run on 2026-11-03, Python 3.14.7 / pytest 9.2.0:

| Check | Result |
|---|---|
| `uv run pytest tests/test_source_evidence.py` | 115 passed |
| `ruff check TrialLedger/layer2/source_evidence.py tests/test_source_evidence.py` | All checks passed |
| `ruff format TrialLedger/layer2/source_evidence.py tests/test_source_evidence.py` | Both files unchanged on final formatting check |
| `ty check TrialLedger/layer2/source_evidence.py tests/test_source_evidence.py` | All checks passed |

Authored cases cover malformed identity, stale snapshots/digests/expected values, missing versus null,
recursive bool/integer/float differences, malicious pointer escapes/indexes, exact Unicode/repeated spans,
closed marker/anchor schemas, decimal protection, literal source JSON, nonfinite/invalid JSON, cycles,
byte/depth/node/anchor limits and their boundaries, expansion limits, and independent copies. A retained
IPASS source cell is located and explicitly converted from `"126"` to `126` without adding a clinical label
or eligibility assertion. This fixture is development evidence, not independent clinical validation.

## Pending shared checks

The pure named-code decisions offered for the serialized Detective pass are `integer_state` and
`pointer_state`; `exact_json_equal` is also a pure comparator. These carry PEP 316 postconditions. No
Detective or CrossHair run was started by this worker before the shared freeze. No mutation kill-rate,
symbolic proof, full-project gate, public CLI/MCP end-to-end clearance or clinical-meaning accuracy is
claimed by the scoped checks above. Those belong to the coordinated integration verification.

## Serialized Detective verification after shared freeze

The lead explicitly confirmed the functional source/authored-test freeze before these walks. The worker
held the exclusive Detective slot throughout and released it after the final prescribed plan. No source or
authored test was changed, no proposed test removal was accepted, and no equivalence flag was authored.
Detective generated its own tests. The complete protocol, follow-next-actions skill, local Detective
`AGENTS.md`, help and regime output were read before convergence.

Every Detective and prescribed pytest command used TrialLedger's own environment with:

```text
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label <purpose> --
env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker
.venv/bin/detective <arguments>
```

The pytest form substituted `.venv/bin/python -m pytest <arguments>`. Working directory was
`/Users/rohanvinaik/tools/TrialLedger`. Resolution was proved in the same environment:

```text
Python -> /Users/rohanvinaik/tools/TrialLedger/.venv/bin/python
Detective -> /Users/rohanvinaik/tools/Detective/Detective/__init__.py
Wesker -> /Users/rohanvinaik/tools/Wesker/Wesker/__init__.py
pytest -> /Users/rohanvinaik/tools/TrialLedger/.venv/lib/python3.14/site-packages/pytest/__init__.py
```

`detective --help` prescribed `regime`; `regime` printed `DONE`, clean with nothing to migrate.
`converge --help` and `plan --help` were also read in full. Each target then used:

```text
converge TrialLedger/layer2/source_evidence.py::integer_state --two-sign --full
converge TrialLedger/layer2/source_evidence.py::pointer_state --two-sign --full
converge TrialLedger/layer2/source_evidence.py::exact_json_equal --two-sign --full
```

All three reported comprehensive, exhaustive full operator-universe policy `9+neg.f5a15364c11d` and
line-complete status, with reproducibility confirmed by a fresh isolated observation. Exact reported results:

| Target | Final behavior status | Killed | Value-pinned | Explicit residual |
|---|---|---|---|---|
| `integer_state` | COMPLETE modulo 1 unproven-equivalent | 47/47 | 46/47 | 1 candidate-equivalent remains UNPROVEN |
| `pointer_state` | COMPLETE modulo 1 crash-only value gap | 32/32 | 31/32 | Detected by crash; not an equivalence candidate |
| `exact_json_equal` | COMPLETE modulo 20 unproven-equivalent and 5 crash-only value gaps | 56/76 | 51/76 | 20 candidates remain UNPROVEN; 5 detected by crash |

These distinctions are the tool's reported categories. Candidate-equivalence was not promoted to proof, and
crash-only detection was not reported as a return-value pin. Per the governing protocol, the printed COMPLETE
modulo unproven-equivalent statuses ended the behavior walks without grinding or speculative flags.

Tool-owned generated files:

- `tests/detective/test_TrialLedger_layer2_source_evidence_integer_state_4424136a84_synth.py`: one test.
- `tests/detective/test_TrialLedger_layer2_source_evidence_pointer_state_d1111cb815_synth.py`: one test.
- `tests/detective/test_TrialLedger_layer2_source_evidence_exact_json_equal_5d5923dba0_synth.py`: four tests.

The printed pytest instruction was followed. After the integer walk, full pytest reported **4387 passed,
10 deselected in 96.55s**. After pointer, the printed generated-test alternative `pytest -m detective`
reported **395 passed, 4003 deselected in 1.34s**. After equality, the same alternative reported **399 passed,
4003 deselected in 1.32s**. The full-suite count precedes the five later generated tests; it is not presented
as a post-final-generation full-suite measurement.

The complete style path was followed for each target:

```text
plan TrialLedger/layer2/source_evidence.py::integer_state --full
plan TrialLedger/layer2/source_evidence.py::pointer_state --full
plan TrialLedger/layer2/source_evidence.py::exact_json_equal --full
```

Integer and pointer plans reported SILENT, pinned, clean, zero funded, and no next action. Equality reported
AMBIGUOUS, escalated, pinned, not_clean, with `overload (48 DOF / 16 lines (static proxy))` and the
`memoizable_pure_recursion` template. It prescribed a style leave/proceed choice. The worker stopped and
reported that choice to the lead under the no-hand-flags instruction. The lead authorized this exact
**style disposition**, distinct from any behavioral equivalence claim:

```text
flag TrialLedger/layer2/source_evidence.py::exact_json_equal --style --leave
--note "Keep bounded structural JSON equality for source admission. Repeated-comparison benefit is unmeasured; preserve current value/type semantics without adding cache behavior."
```

Detective printed `DONE`, recorded the style judgment against the exact definition/current reading, and
prescribed one further plan:

```text
plan TrialLedger/layer2/source_evidence.py::exact_json_equal
```

That final plan reported residual `judged_leave 1`, zero funded and no further action. The tool states the
judgment reopens if the code or reading changes and never touches the behavior layer. No decompose, survey,
extract, receipt or rewrite action was prescribed by these completed chains. No source rewrite occurred.
Static style silence and the deliberate leave are not module-wide style approval or performance evidence.

All command outputs were redirected intact, then read in full. Logs remain in
`/tmp/trialledger-source-evidence-20261103/`:

- `resolution.log`, `help.log`, `regime.log`, `converge-help.log`, `plan-help.log`.
- `integer-state-converge.log`, `integer-state-pytest.log`, `integer-state-plan.log`.
- `pointer-state-converge.log`, `pointer-state-pytest.log`, `pointer-state-plan.log`.
- `exact-json-equal-converge.log`, `exact-json-equal-pytest.log`, `exact-json-equal-plan.log`,
  `exact-json-equal-style-leave.log`, `exact-json-equal-plan-after-leave.log`.

Detective also writes full static reports under `.detective/reports/`; the temporary logs preserve the
earlier equality plan before its final judged-leave report. CrossHair, independent whole-project gates,
installed CLI/stdio MCP checks and clinical-meaning review were not performed by this serialized worker.
