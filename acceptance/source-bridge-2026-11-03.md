# Retained-source bridge: integration verification — 2026-11-03

## Scope and clinical contract

The main-session natural-language discussion was reread before the implementation plan. The implemented
path is raw retained NIH study -> content identity and exact anchors -> named structured direct rules or
separately proposed clinical readings -> existing entailment/interpretation/signal operations -> complete
public response and decision list. Reporting remains independent. No source, report or terminology store
was rewritten and no clinical text recognizer, repair engine or complete protocol writer is claimed.

The direct rules cover complete supported NIH integer/unit minimum/maximum age fields. They establish
registered-general-eligibility content of the supplied record, not independent registry truth, actual
compliance or a new trial's required choice. Unsupported and uncompiled content remains visible. Exact
source location proves quotation and value preservation, not clinical interpretation. Prepared assumptions,
local signal support and bindings remain proposed; unresolved derivations remain unresolved. Only declared
anchor dependencies may hydrate a frame or binding. Content digests and rule/clinical editions stay distinct.

## Domain grounding across the channels

The clinical walkthrough exposed a representation test: nominal day 42 and allowable days 35–49 are
different channels informing one schedule decision. Both are retained, rather than made rival meanings.
The two proposed later-tolerance readings preserve nominal targets 42/84 and the first permitted window,
while the existing temporal operator computes second windows [77,91] versus [70,98]. Day 40 can be permitted
without changing the nominal target. A proposed second visit on day 72 fits only the successive-gap model;
the other joint hypothetical constraint set is incoherent, not a proof that source meaning was refuted.

This discipline is tested across all eight structural signal kinds, not limited to time. Public CLI/MCP
checks preserve each payload's population, units, roles, time, definition modes and predicate structure,
retain independent fixed answers and withhold unsupported admission. Accepted/rejected eligibility witnesses
retain their separate existing bridges and consumers; no automatic witness-text compiler was added.
`docs/SOURCE_ASSERTION_BRIDGE_PLAN.md` records the full clinical channel/decision/binding audit.

Three complete retained-IPASS examples demonstrate registered age, conditional baseline overlap [49,126]
and competing schedule readings. Each includes the raw source, exact locations, reusable generated requests
and complete results. The working brief holds the clinical choices and their remaining questions. The raw
fixture's SHA-256 remains `dc5b4cb1f416420d38c93c444f5a7b5f93d35d1676dc9c1cfa0379a58fe53354`.

## Observed consumer checks

- The root focused run passed **380 tests**, including the three new suites, discovery/entry-point
  inventories and reporting/source preservation. The scoped suites comprise 115 source-evidence, 47 compiler
  and 133 public workflow tests; the remaining focused cases exercise existing consumers and boundaries.
- The source-workflow receipt separately records bounded identified/abstained/wrong counts per clinical
  case and per signal kind. Dependencies can correctly remain unresolved even with resolved support because
  a required observed input is unknown. No aggregate accuracy or broad clinical validation is inferred.
- A fresh CPython 3.12.12 installation, with runtime dependencies only, imported from its own site-packages
  outside the repository with PYTHONPATH removed. All **62 package Python files** matched current source
  byte for byte. All **three full example responses** matched through installed CLI and actual installed
  stdio MCP initialization/tool-call subprocesses. `source-bridge-installed-entrypoints.json` retains the
  metadata. The build predates this commit; byte identity establishes which functional source was checked.
- `source-bridge-consumer-trace.json` records actual CLI execution of the three examples through 157 traced
  code entries in ten modules, with source hashes. It observes source anchoring, hydration, direct rules,
  source-bound application checks, existing solvers and returned consequences. This is a runtime wiring
  observation, not a performance claim.
- A read-only worker review exercised eight additional public requests covering status promotion,
  undeclared dependencies, unresolved rules, OR/AND, actor/condition/cohort/time, unsupported maximum age and
  invalid inspection frames. No counterexample was found in those cases; this is not general source truth.

Root review found and repaired an actual provenance gap before the shared freeze: a frame/binding could
hydrate from an otherwise verified anchor it had not declared. The compiler now selects its declared
anchors first and refuses any other dependency. The review also separated rule version `1` from snapshot
identity, added uncompiled study-root coverage and bounded aggregate/repeated-query work during inspection.

## Symbolic contracts and mutation scope

CrossHair ran all four pure target contracts with `--report_all --per_condition_timeout=2`. The three
integer-state, two pointer-state and one exact-JSON-equality postconditions reported **Confirmed over all
paths**. The three age-state conditions reported **Not confirmed**: neither a violation nor a proof.
Complete output was read from `/tmp/trialledger-source-bridge-crosshair.log`. No code was changed to obtain
those results. All four serialized Detective walks used full two-sign policy `9+neg.f5a15364c11d`:

| Decision | Value-pinned | Killed | Retained limit |
|---|---:|---:|---|
| integer_state | 46/47 | 47/47 | One unproven-equivalent |
| pointer_state | 31/32 | 32/32 | One crash-only value gap |
| exact_json_equal | 51/76 | 56/76 | Twenty unproven-equivalent; five crash-only value gaps |
| age_state | 84/85 | 85/85 | One crash-only value gap |

These are the tool's COMPLETE operator-universe verdicts modulo the stated limits, not universal equivalence
proofs or residual-free return-value pins. The first age observation was UNGATEABLE; its exact prescribed
isolated rerun established the final verdict without changing source or authored tests. Seven generated
tests across four files remain tool-owned and unedited. No authored test was removed or equivalence flag
invented. Source/compiler receipts retain full commands and logs; the root read the complete converge reports.

Integer, pointer and age style plans were SILENT/clean with zero funded changes and no further action.
Equality's plan offered memoization and an explicit leave/proceed choice. The root selected the printed
style-leave command to retain bounded structural equality with unmeasured repeated-comparison benefit.
The prescribed follow-up plan recorded judged_leave, zero funded and no further action. This is a style
disposition only, not a behavioral equivalence claim or performance evidence. The root age plan ran after
the completed behavior walk; no source rewrite was made.

## Final gate

The normal project gate passed on the frozen functional/test basis: **4,393 passed, 10 opt-in live tests
deselected**, CPython 3.14.7 / pytest 9.2.0. Locked environment sync, Ruff check, format check (460 Python
files), and advisory whole-package ty passed. Full output was read from
`/tmp/trialledger-source-bridge-gate.log`. That run did not stamp its tree because the documentation/receipt
changed during verification; the commit's exact tree receives the normal pre-push gate. Strict OpenSpec
validation and `git diff --check` also passed. The ten traced module hashes and all 62 installed package
files were rechecked unchanged after the mutation walks.

Task 4n is complete for this bounded bridge. General clinical prose compilation and the remaining full
writer integrations stay unchecked. Prior accepted mutation limitations are retained in their original
receipts and are not reopened. Performance and memory payoff are unmeasured.
