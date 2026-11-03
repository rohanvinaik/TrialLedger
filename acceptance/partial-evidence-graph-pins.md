# Partial-evidence graph mutation receipt — 2026-11-03

Scope: four small decisions in `TrialLedger/layer2/graph_evidence.py`. This is a factual record of Detective's commands and printed dispositions, not a certificate for the entire module or its clinical bindings. The supplied source meanings remain caller premises.

## Final scope and standing

| Target | Explicit final policy | Literal behaviour standing | Return-value pins | Crash-only detections | Equivalence standing |
|---|---|---|---|---|---|
| `bound_tightness` | `--two-sign`, `9+neg.f5a15364c11d` | `✓ COMPLETE (operator universe) · 54/54 killed · minimal cover 8 test(s)` | 54/54 | 0 | No remaining candidate |
| `graph_disposition` | `--two-sign`, `9+neg.f5a15364c11d` | `✓ COMPLETE (operator universe) · 34/34 killed · minimal cover 3 test(s)` | 34/34 | 0 | No remaining candidate |
| `relation_conflict` | `--two-sign`, `9+neg.f5a15364c11d` | `✓ COMPLETE (operator universe · modulo 1 crash-only value gap) · 53/53 killed · minimal cover 7 test(s)` | 52/53 | 1 | No remaining candidate; nothing flagged |
| `membership_problem` | Latest attempted convergence explicitly used `--two-sign` | `INCOMPLETE: harvest_cut: codomain observation did not complete admissibly` | No final full-policy convergence count established | No final full-policy convergence count established | See earlier audit and the one recorded proof below; do not infer a later certificate |

The tool's literal COMPLETE text says “operator universe” even in the explicit two-sign runs; the policy identifier and argv above retain which scope was actually requested. Killed-by-crash is not return-value-pinned, and neither is a proof-backed equivalent.

The user explicitly chose **“Accept a documented pin limitation”** for `membership_problem`'s `harvest_cut` only. Its complete full two-sign convergence remains unachieved. This acceptance does not waive any other target or turn the failed measurement into a pass. No further membership convergence, audit or flag was run after that choice.

## Runtime and invocation

Working directory: `/Users/rohanvinaik/tools/TrialLedger`. The project's own `.venv/bin/detective` ran with:

```text
PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker
```

The import probe printed:

```text
Detective -> /Users/rohanvinaik/tools/Detective/Detective/__init__.py
Wesker -> /Users/rohanvinaik/tools/Wesker/Wesker/__init__.py
```

Every measured CLI invocation used the owned-process launcher:

```text
/Users/rohanvinaik/Projects/SquishOS/ops/agents/bin/owned-run --label LABEL -- env PYTHONPATH=/Users/rohanvinaik/tools/Detective:/Users/rohanvinaik/tools/Wesker .venv/bin/detective ARGUMENTS
```

`--help` and `regime` were read. Regime printed `DONE: this regime resolves cleanly — nothing to migrate.` The first help-only call used bare `detective`; it made no measurement. Help was then repeated through the project environment and standing local imports before regime and convergence.

## Initial narrower measurements and repairs

The initial `converge` commands mistakenly omitted `--two-sign`. These earlier operator-only results do not satisfy the requested final scope.

1. `converge TrialLedger/layer2/graph_evidence.py::bound_tightness` printed `⚠ UNGATEABLE` because the in-process universe did not reproduce in isolation. Its exact prescribed repair, `converge TrialLedger/layer2/graph_evidence.py::bound_tightness --isolated`, completed at 26/26. Its initial decomposition found no separable block. This was subsequently superseded for task scope by the explicit full-policy 54/54 run and full-policy chain below.
2. `converge TrialLedger/layer2/graph_evidence.py::membership_problem` printed `⚠ CUT — aggregate deadline exhausted during minimization`. Its prescribed `--deadline 900` rerun completed the narrower 28-mutant universe at 25/28 killed, 23/28 value-pinned, three unproven equivalence candidates and two crash-only value gaps. Full stdout/stderr of that repaired narrower run is `/tmp/trialledger-graph-membership-deadline.log`.
3. The proof flag below printed a next action of `audit ... --two-sign`. That audit completed with 65 mutants, 60/65 value-pinned, two crash-only gaps, one flagged equivalent and two unproven equivalence candidates. It prescribed `converge ... --two-sign`.
4. `converge TrialLedger/layer2/graph_evidence.py::membership_problem --two-sign` ended with the exact `INCOMPLETE: harvest_cut: codomain observation did not complete admissibly` residual and no printed repair command. No repair was invented.

The failed explicit two-sign membership run produced streamed tool output only; no filesystem log retained. Its exact final residual is quoted above; there is no claimed full-output file for this failed run. Reading `.detective/reports/converge_membership_problem.txt` afterward showed that it still held the earlier **28-operator** report. That stale static report is not evidence of the failed run's full-policy completion. The completed two-sign audit likewise preceded the failed convergence and must not be promoted into a later convergence certificate.

A subsequent inspection of the exact `membership_problem` entry in `tests/detective/certificates.json` found `standing: "complete"`, `cut_reasons: []`, `refusal: ""` and `function_digest: "8e255dd644b4f3f2"`. That stored entry encodes no policy or scope. Its scope-less standing must **not** be treated as the requested full two-sign convergence certificate: the latest explicit convergence remains `harvest_cut`, and full two-sign convergence remains unachieved. The entry's fields alone do not determine which earlier narrower run or audit wrote it; no origin is inferred. The tool-owned certificate metadata was not modified.

## Recorded equivalence proof

Only one membership equivalence flag was recorded. This exact argument vector followed the standing launcher above under label `graph-membership-flag-union`:

```text
flag TrialLedger/layer2/graph_evidence.py::membership_problem SWAP_66aa091e --two-sign --note 'For the declared list[str]/list[list[str]] domain, set.union accepts each members list as an iterable. Replacing each set(members) iterable with members changes neither elements inserted nor the resulting positive set; duplicate strings are discarded by union in both forms. All later decisions receive the identical positive set.'
```

The mutant replaces:

```python
positive = set(required).union(*(set(members) for members in complete))
```

with:

```python
positive = set(required).union(*(members for members in complete))
```

Detective printed `✓ recorded equivalent`, keyed to the exact code. The proof applies to the declared lists of strings; the union receives the same elements in both forms. Its next prescribed `audit ... --two-sign` produced the earlier 65-mutant audit described above. No flag was recorded for the two other membership candidates, and no later status for them is inferred from the failed convergence.

The narrower membership report identified `SWAP_61bc1f63` and `VALUE_66e0af55` as crash-only detections, expressly not equivalence candidates. Neither was flagged.

## Completed full-policy paths

The final behaviour invocations were:

```text
converge TrialLedger/layer2/graph_evidence.py::graph_disposition --two-sign
converge TrialLedger/layer2/graph_evidence.py::relation_conflict --two-sign
converge TrialLedger/layer2/graph_evidence.py::relation_conflict --two-sign --input '([["person", "instance_of", "A"], ["person", "instance_of", "B"]], [], [["A", "B"]])'
converge TrialLedger/layer2/graph_evidence.py::bound_tightness --two-sign
```

The first relation run reported `SWAP_0506ef59` as a candidate equivalent with a structural warning. Its mutation changes `memberships.setdefault(subject, set()).add(target)` into `subject.add(target)`. The explicit nested input above followed the report's instruction. Detective then reported the mutant as **crash-only-distinguishable**, with no equivalence candidate and nothing offered to flag. The resulting behaviour standing is the final 53/53 killed, 52/53 value-pinned row above.

Each completed target followed its printed `plan` → `decompose --apply --two-sign` → `survey` chain. Decomposition retained the two-sign policy and recalled the supplied relation input.

| Target | Decomposition result | Source disposition |
|---|---|---|
| `bound_tightness` | `DONE: no separable block. There is no seam here to split.` | Unchanged |
| `graph_disposition` | `DONE: no separable block. There is no seam here to split.` | Unchanged |
| `relation_conflict` | `STOP` — `_compute_memberships` proposed, not proven/applied; one crash-only survivor blocked automatic extraction | Tool explicitly reported source not touched |

The relation style proposal is an unproven optional extraction, separate from its completed behaviour standing. The crash-only mutant was not mislabelled equivalent to enable a rewrite. Final module plan was advisory: zero funded, five constructive, eleven escalated, zero fenced and seven silent. Survey reported zero trapped pure decisions, with its explicit static-scan limits. No style proposal was implemented.

## Report and output paths

Complete final convergence logs:

- `/tmp/trialledger-graph-bound-two-sign.log`
- `/tmp/trialledger-graph-disposition.log`
- `/tmp/trialledger-graph-relation.log` — initial full-policy relation run
- `/tmp/trialledger-graph-relation-nested.log` — final explicit-input relation run

Complete final decomposition logs:

- `/tmp/trialledger-graph-bound-decompose.log`
- `/tmp/trialledger-graph-disposition-decompose.log`
- `/tmp/trialledger-graph-relation-decompose.log`

Static reports, relative to the repository root:

- `.detective/reports/converge_bound_tightness.txt`
- `.detective/reports/converge_graph_disposition.txt`
- `.detective/reports/converge_relation_conflict.txt`
- `.detective/reports/decompose_bound_tightness.txt`
- `.detective/reports/decompose_graph_disposition.txt`
- `.detective/reports/decompose_relation_conflict.txt`
- `.detective/reports/plan_TrialLedger_layer2_graph_evidence_py.txt`
- `.detective/reports/converge_membership_problem.txt` — earlier narrower report, stale with respect to the latest failed full-policy run
- The earlier full-policy membership audit produced streamed tool output only; no filesystem log retained. No `audit_membership_problem.txt` report file exists in the report directory.

Temporary logs and `.detective` reports are local, regeneratable evidence. This repository receipt records the reported boundary even when those local files are absent from a fresh checkout.

## Test ownership and remaining boundary

No production source or authored test was edited during the mutation walks. Detective generated and minimized only its own characterization tests. Its proposed removal lists for authored tests were declined: a minimal cover for one function does not retire the tests' graph, integration, oracle or public-entry obligations. The earlier graph suite run had 91 passing tests, with Ruff and module typing clean; this receipt does not restate that earlier run as a new post-pin measurement.

The four decisions consume already typed values. Their mutation results do not certify registry truth, source binding, clinical eligibility, arbitrary temporal/regimen closure code, or the complete public system. Public-path tests and the project's final gate supply separate evidence. The accepted membership limitation remains visible and unclosed.
