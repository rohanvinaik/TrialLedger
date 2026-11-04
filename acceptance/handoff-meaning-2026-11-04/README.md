# Preserve clinical handoff meaning

This packet checks the four defects found in the cold Phase 2 UC workflow: related source-reading export,
permissions absent from the primary review, option identity lost in open-item wording and stale adoption
references after revision. It records a scoped implementation, not complete protocol generation.

## Clinical outcomes

Two fresh seeded samples were retained, with their awkward comparators rather than replaced.

- **Phase 1 atopic dermatitis:** seed 2026110451 sampled NCT06193434 and NCT05729074 from 72 completed
  registrations starting in 2020–2025. These are multi-population studies, not one interchangeable cohort.
  NCT05729074's patient section explicitly discusses stable inhaled/nasal corticosteroids. A simulated
  AD-only draft adopts a conditional stability requirement and a separate permission. Two stable months
  are ruled out, three fit, and medication use is not mandatory. Tightening the chosen requirement to four
  months rules out the three-month profile without changing the no-medication answer. The new exchange
  reaches criterion and rule references; independent source references remain separate. The other source
  reports maximum age 70 in a structured field and 75 in its AD prose; that discrepancy is retained as a
  source/interpretation question, not silently corrected.
- **Phase 4 asthma:** seed 2026110452 sampled NCT06918418 and NCT06590740 from 13 completed registrations
  starting in 2023–2025. One concerns acute paediatric exacerbations, the other chronic adult cough; the
  sample is not declared a comparable class. A simulated acute-study draft adopts a symptom-onset interval
  and a qualified exclusion of altered mental status together with imminent respiratory failure. Both
  together are refuted; either feature alone is not excluded by that represented conjunction. Widening
  onset from 12 to 18 hours changes the 13-hour profile without changing the presentation checks. This is
  an examination of represented restrictions, not an assertion that either partial profile is clinically
  appropriate or wholly eligible.

Each case also explores an entry reading and a deliberately different-cohort control as proposed source
frames. Both remain compatible, and the common answer retains `interpretation_scope_contrast` with proposed
standing. Exporting their results does not adopt either reading or create a registry fact.

Complete baseline, source-reading and revision request/result pairs are in the case directories. Choice
confirmations are simulated. Clinical prose was read by the operator; there is no new automatic text encoder.
Raw registry bodies, reference workbooks and rendered reviews remain local under
`~/trialledger-runs/handoff-meaning-20261104/`; the receipts record locators, fingerprints and sizes. Embedded
source snapshots stay intact inside complete reasoning requests. The committed packet is about 2.7 MB,
without bulk raw pools or opaque archives.

## Public interface and conservation checks

The actual CLI and initialized stdio MCP server computed the same full baseline, source-reading and revised
responses in both fresh cases. Their final review workbooks are byte-identical for the same canonical inputs.
Identifying columns freeze at B2/C2. Permission summaries link to exact detailed rows instead of clipping
repeated full statements; Options and Markdown retain statements, gates, standing and references.

The original UC specimen was replayed through both public interfaces with its source-reading artifact
included. Export succeeds, the conditional rescreening permission is visible, source and new-choice origins
remain distinct and the revised adoption references agree. All 42 baseline values still match exact source
addresses. `uc-regression.json` records the artifacts and local retained input locators. The final exports
were independently read back; three clinical review regions were rendered and inspected.

Direct intent tests cover operation ownership, proposed/default standing, conditional permissions,
query/complement wording, malformed replacement inputs, exact reference matching, independent citations,
prior immutability and mechanical edit receipts. Existing source/entailment invariants remain in the full
suite. No solver verdict, source interpretation rule or acquisition limit changed.

## Formal verification scope

- `adoption_reference_code`: explicit Detective two-sign operator universe; see the retained exact report.
- `finding_owner_code`: explicit isolated two-sign operator universe; see the retained exact report and its
  unproven-equivalence/crash-only qualifications. Those qualifications are not proofs of equivalence.
- CrossHair `--report_all` on the independent contracts in `contracts.py` reports **Not confirmed** for the
  five properties within the five-second per-condition search. This is not a pass or an established
  violation. The exact output is retained separately from the mutation and public workflow evidence.
- The machine-wide extended deep-audit waiver is not replaced by these scoped checks. No whole-project
  mutation certificate, semantic encoder accuracy or independent real-clinician confirmation is claimed.

The consumer trace exercises 90 public CLI/MCP runs across 54 observed modules. It proves reachability and
complete-response parity for those cases; the clinical workflows and adversarial tests separately check
meaning and preservation. Final gate results and code fingerprints are recorded in `verification.json`.
