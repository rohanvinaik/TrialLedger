# Warranted design consequences and clinical handoff

This change exposes more information already warranted by the represented criteria and carries it through
revision, bounded replies and the colleague-facing review. It does not compile clinical prose automatically,
authenticate a person's confirmation or generate a complete protocol.

## What changed

- A partial profile can expose a proved remaining requirement. An invented BMI-28 profile needs one of a
  listed-condition disjunction; no individual condition is thereby required. Prior treatment can expose its
  washout requirement. Query-only specialization cannot borrow a fact from the criteria it is explaining.
  Criteria-wide requirements and profile-specific implications remain distinct, with proof, standing and scope.
- Optional exact-anchored decision evidence supplies context only. Copied passages are known as copies;
  caller notes and declared scope remain proposed annotations. Context never adds an eligibility constraint.
- The shared decision view shows caller wording beside the actual typed profile, computation context,
  independently computed feasibility support, logical warrant, deciding criteria, context and open items.
  The export consumes this owner. Long evidence flows through labelled complete display parts in Decision
  evidence; the main sheets link to it. No excerpt is presented as a complete source value.
- Revisions compare question, answer, versioned deciding support, origin, caller wording and evidence context
  separately, retaining the full audit difference. A sharpened query need not have a changed verdict.
- Compact replies obey a supported byte budget, default 24,576, with explicit counts and exact continuation.
  Full canonical artifacts remain intact. Presentation copies do not spend the logical replay input budget.
- Discovery exposes the actual estimand strategy vocabulary. The strategy name alone creates no requirement;
  adopted collection/measurement rules remain separate premises.

## Clinical checks

All choices below are simulated; fresh registry evidence and retained-evidence replay are distinguished.
They test exercised boundaries, not clinical generality or automatic translation accuracy.

| Check | Exercised structure and result | Retained local packet |
|---|---|---|
| Obesity replay | Original 15 decision objects unchanged; BMI/washout residuals; 15-analysis revisions; full bounded reconstruction | `~/trialledger-runs/bounded-obesity-20261104/` and `residual-obesity-replay-20261104/` |
| Phase 2 rheumatoid arthritis | Background-dose stability versus washout; proposed competing frames; candidate bounds; no window equivalence inferred | `~/trialledger-runs/residual-phase2-ra-20261104/` |
| Phase 4 hypertension | Unchanged verdict with revised support, genuinely changed verdict, refined question with same verdict; heterogeneous search retained | `~/trialledger-runs/phase4-hypertension-revision-20261104/` |
| Phase 2 tuberculosis search | TBM and MAC selections kept distinct; source age versus simulated new-trial age choice | `~/trialledger-runs/phase2-tuberculosis-revision-docs-20261104/` |
| Early-phase lupus | Renal/nonrenal scope, compound profiles, anchored comparator passages, changed scope and independent export review | [Complete replay pairs and clinical account](lupus-cohorts/README.md) |
| Cold Phase 3 migraine | Public discovery, period-specific medication rules, source context, revision and export; unaddressed predicates stay open | `~/trialledger-runs/cold-phase3-migraine-20261104/` |

The final obesity CLI revisions are 18,987 and 17,903 bytes, versus 302,368 and 328,322 in the audit packet.
MCP agrees apart from its transport label. At the 2,048-byte minimum the baseline/revision replies are
1,792/1,871 bytes. A total of 150 bounded reads reconstructed every checked finding, comparison, coherent
decision view and edit exactly. See [the receipt](bounded-obesity-receipt.json).

The cold migraine case retains a conservative session boundary: a new-draft predicate mentioned by no
constraint receives `no_constraint_mentions_query`; session feasibility and pairwise distinction are not
proved from that verdict. The operator should say the draft has not addressed the restriction and elicit a
choice. It must not present historical absence, or proved design freedom, as the computed answer. Extending
that orchestration would require explicit under-floor feasibility checks, not relabelling the result.

## Symbolic trace and conservation

The consumer trace executes actual CLI/MCP dispatch; it establishes reachability and transport parity,
not source meaning. `residual_requirements` feeds `entail_explanations` and the shared `solver_work` plan.
Entailment, interpretation frames and candidate queries consume those explanations. The clinical projection
retains conditions and origins; revision resolves versioned deciding IDs. `clinical_view` joins the actual
analysis context and exact decision evidence; both retained delivery and export consume it. Reporting remains
independent of the reasoning layer.

Saved-example refresh compares protected complete logical payloads, including numeric types, source values,
queries, scopes, decisions, proof and standing. Only additive explanations, their derived presentation and
result fingerprints are excluded from that comparison. Original request bytes remain unchanged; existing
permissions remain unchanged. This is not permission to replace an unexpected verdict with a new fixture.

## Explicit two-sign scope

Root inspected the complete static reports and CrossHair logs, checked target AST equality against the
measured copies, and adopted the three generated suites whole, without removing authored tests. See
[proof integration](proof-integration.json) and the complete reports in `proofs/`.

| Pure target | Detective reported | CrossHair `--report_all` |
|---|---|---|
| revision_change_code | COMPLETE 121/121 | Three contracts confirmed |
| compact_budget_code | COMPLETE 39/39 | Declared codomain contract confirmed |
| junction_code | COMPLETE 87/87 | Not confirmed |
| explanation_gate | COMPLETE modulo one unproven-equivalent, 75/76 | Two contracts not confirmed |
| profile_truth_code | COMPLETE modulo four unproven-equivalent, 88/92 | Three contracts confirmed |
| role_code | COMPLETE modulo one crash-only value gap, 35/35 killed, 34/35 value-pinned | Three contracts confirmed in annotated string domain |
| value_style | COMPLETE modulo four unproven-equivalent, 128/132 | Not confirmed |

Unproven equivalence remains unproven. A crash-only detection is not a return-value pin. “Not confirmed”
is not a proof or counterexample. These are per-function operator-universe measurements, never a whole-project
or clinical-truth certificate. The earlier extended whole-project deep-audit waiver remains separate.

Independent final workbook QA reconstructed all twelve evidence/note/scope groups, checked 107 links,
verified source copies and manifest hashes, and found no formula cells. The previously clipped criteria
8–10 are visible in the final rendered ranges. Native Excel was not tested. See
[the QA receipt](workbook-qa-receipt.json). The cold migraine receipt records its own writing version;
later layout-only verification and installed-source checks are separate receipts.

The final canonical replay exposed one additional mechanical defect: uncompiled source-region coverage
followed dictionary insertion order. Canonical artifact serialization could therefore manufacture a source
change. Coverage now sorts exact addresses, preserving every region and escaped pointer. A direct complete
source-bridge round-trip test covers the invariant; the final lupus replay keeps both sources unchanged.
No clinical assertion or eligibility decision changed in that repair.

## Closeout verification

The ordinary local gate passed 6,520 tests with Ruff/format and production Ty clean. Ten live API tests
passed separately. The final installed Python 3.12 package matches all 100 production modules. The current
consumer trace covers 90 runs / 45 CLI–MCP pairs and 54 observed modules, with equal request/result digests.
The writer additionally passed a separate installed CLI/MCP export comparison. See
[final verification](final-verification.json), [installed identity](installed-source-identity.json),
[installed export](installed-export.json), [coverage conservation](coverage-conservation.json) and
[live checks](live-checks.json). Full trace and console captures remain at their hash-bound local locations.

The normal secret scanner identified twelve public registry URIs or local retained-output paths. Complete
source/receipt units were reviewed and exact path/detector/whole-added-line fingerprints recorded through
the existing review mechanism. Detectors were not disabled. Normal publication checks run again over the
final committed tree. Implementation commit: `2331b5e`; the closeout commit records these receipts.
