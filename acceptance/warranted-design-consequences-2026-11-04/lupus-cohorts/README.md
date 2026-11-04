# An early-phase lupus design: whose biopsy rule is it?

The question and random seed were recorded before reading the selected records. A complete Phase 1 lupus
CAR-T search returned 92 identifiers. Seed 2026110417 selected NCT05846347 and NCT06839976 without replacement.
The latter records Phase 1 and Phase 2. Both selections were retained; they are not declared comparable.
An initial malformed request was refused before retrieval; the corrected scope and separate sample run
remain in the local packet. No failed selection was replaced.

The initial idea concerned escalation and expansion cohorts. The selected records did not establish those
cohort identities. Reading their complete eligibility instead exposed a useful renal/nonrenal question:
NCT06839976 distinguishes lupus-nephritis requirements, including biopsy within the past 12 months, from
nonrenal SLE requirements. NCT05846347 has its own distinct requirements and exclusions. Neither source was
flattened into the other's population. Outcome time frames were read separately; none became a dose-evaluation
or visit-schedule rule.

## Simulated design conversation

**Person:** “For our draft, require age at least 18. Require a biopsy within 12 months in the renal cohort.
Do not silently make that a rule for the nonrenal cohort.”

These are explicit simulated new-trial choices. The registry passages are separately anchored context.
This two-predicate representation does not encode the full source eligibility or define clinical suitability.

**Computed:** A 20-year-old renal profile without that biopsy is refuted, with the biopsy premise deciding
it. The corresponding nonrenal profile is allowed but not required by the represented restrictions.
The biopsy-positive profiles also fit; nobody is required to be exactly 20. The actual cohort context is
shown beside each typed profile, independently of its caller-written label.

**Person revises:** “Apply that biopsy requirement to all cohorts.”

**Computed:** The nonrenal profile without biopsy is now refuted. The renal profile without biopsy remains
refuted, with changed scope/support. This is not a discovery that a comparator had a general biopsy rule;
it is the consequence of changing this simulated draft. The source passages remain unchanged.

## Handoff and limits

Actual CLI and subprocess stdio MCP agree on the baseline, revision and coherent decision view. The source
record/workbook verifies from its retained inputs. Export reads every workbook cell back and checks values,
types and links; formula-like strings remain literal text. Independent visual review found clipped context
and omitted computation context, which prompted the Decision evidence flow and actual-context column.
The final review is in the retained packet under `handoff-canonical/review/`.

Complete baseline/revision request and response pairs are committed here for layer-two replay under the
writing version, with sources embedded as required inputs. Layer-one verification additionally requires the
full report/raw packet at `~/trialledger-runs/phase1-lupus-cohort-handoff-20261104/`. Re-fetching an NCT number
is a new observation, not guaranteed recovery of those historical bytes. The storage receipt hashes the
retained files; duplicate workbooks, wire captures and raw search bodies remain local.

Final replay also canonicalizes JSON object keys. Its complete computational response equals the retained
public response; only the separately named delivery.previous_artifact/edits carrier is added by public
revision. Both source audit rows now remain unchanged. Uncompiled-source coverage is sorted by exact address,
so dictionary serialization cannot manufacture a source change. The earlier visual receipt refers to its
retained historical artifact; the final writer uses the same visible layout with corrected audit ordering.
