# Phase 1 malaria design conversation

This is a model-operated clinical workflow check. The clinician and every new-trial choice are simulated;
no human confirmation is asserted. Actual registry records and simulated draft premises remain separate.

Clinical question: should a new adult early-phase malaria study keep an age cap of 50 or allow older adults?
Before adopting either comparator's restriction, what does its registered age field actually cover?

## Evidence inspected

The public preview fixed Phase 1 malaria studies starting in 2024 or later. The complete 35-ID pool and seed
202611041738 were saved before selecting NCT06413108 and NCT07730177. The first is a Phase 1/2a monoclonal
antibody study in Mali with adult and child safety cohorts plus an efficacy cohort; the second is a planned
Phase 1 adult controlled-human-malaria-infection vaccine study in Burkina Faso. Their being found by one
search establishes no clinical comparability. Both have no posted results in these retained snapshots.

NCT06413108's structured minimum/maximum ages are 10/50 Years. The full eligibility text separately says
adult safety cohorts are 18–50 and school-age cohorts 10–15; its efficacy cohort says 10–50. The record keeps
all repeated headings unsectioned and preserves exact local source contexts rather than assigning one global
inclusion/exclusion interpretation. NCT07730177's structured bounds are 18/50 Years.

Source addresses are `/protocolSection/eligibilityModule/minimumAge`, `maximumAge` and `eligibilityCriteria`
in each complete raw study. The content-digest study identities are retained by each source_assertions result.

## What the computation resolved

- Age 12 is allowed but not required by NCT06413108's represented general age bounds. This says nothing about
  whether a 12-year-old could enter its adult safety cohort or satisfy all other criteria.
- NCT07730177's structured minimum age rules age 12 out, with registry-age-minimumAge as the deciding premise.
- A proposed adult-safety reading scoped to that cohort rules age 12 out only conditionally. It remains
  proposed; exact quotation and compatible scope do not promote it to a source fact.
- The simulated draft requires age 18–50. Its age restriction rules age 55 out. A public retained revision
  changes the cap to 65 and explicitly attributes that simulated choice. Age 55 then becomes allowed but not
  required. The separate question “not age 55” also becomes allowed but not required.

## Decision list

| Decision | Evidence and consequence | Status |
|---|---|---|
| New-trial upper age limit | Both comparators' general structured limits end at 50. The simulated 50 cap excludes 55; a 65 cap allows 55 without requiring that age. | The revision uses a simulated cap of 65; clinical selection remains open. This does not establish suitability or a standard. |
| Which historical cohort is meant | The mixed study's overall minimum is 10 while adult safety prose says 18–50. The adult-safety reading produces a different scoped consequence and stays proposed. | Reading/cohort question to settle before relying on it. |
| Missing results | Neither sampled record posts results in the retained source. | Evidence gap; no baseline learning or efficacy conclusion is claimed. |

## Public workflow and preservation

The workflow used CLI preview/gather/verify/record/reason/reason-revise/reason-export and a real stdio MCP
connection. Seven clinical/discovery/baseline/revision envelopes match after removing only MCP's transport
`tool` label. Four bounded artifact parts were retrieved through reason_result. No private digest or session
constructor was used by the operator. The complete old and revised snapshots remain in the .reasoning store.

CLI and MCP exports have byte-identical content. Their manifests bind exact canonical artifacts and unchanged
source copies. Independent readback checked manifest hashes/lengths, every workbook cell for formula type,
all artifact-link targets, decision labels, selected clinical outcomes and original-source fingerprints.
The source report verifies again after export. This readback does not certify complete clinical eligibility,
comparison-set suitability, or caller consent. Full sources, pairs and protocol exchanges remain beside this brief.
