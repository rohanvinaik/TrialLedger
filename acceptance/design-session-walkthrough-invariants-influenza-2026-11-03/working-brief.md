# Working brief: Phase 2 early influenza treatment

Question: Which population/onset and assessment definitions matter for a proposed early-treatment study, and what follows when one operational premise changes?

No clinical person has confirmed the source readings or selected a policy. Source statements and hypothetical operational choices remain distinct. The reference workbook is local at `/Users/rohanvinaik/trialledger-runs/invariant-influenza-20261103/landscape.xlsx`; complete reasoning inputs/results accompany this brief.

| Decision | Documentary basis and computed consequence | Status / next action |
|---|---|---|
| Population and comparator set | NCT01179919: healthy obese PK; NCT00867139: immunocompromised randomized/open-label pathways; NCT00453999: hospitalized serious influenza. Common search membership does not establish clinical comparability. | Open: define the target setting before adopting restrictions. |
| Illness onset and reference event | NCT00867139 eligibility anchors ≤5days to diagnosis; NCT00453999 anchors ≤72hours to presentation and defines onset. Different events and units remain separate. | Open: define the intended onset and deadline. No automatic equivalence or unit conversion supplied. |
| Presentation-to-first-dose logistics | With the proposed72-hour presentation restriction, invented immediate dosing conflicts with hypothetical firstdose80hours. An invented0–24hour delay permits that course and yields firstdose≤96hours; an unknown delay ceiling yields no finite first-dose upper bound. | Open operational design choice, conditional checks in `presentation-and-*`. No recommendation to delay treatment. |
| Pathway-specific age | NCT00867139 randomized reading≥7 refutes age6 only in that named context; context retraction reopens the effective frame, retaining raw calculations and scope blockers. `1 Year` remains unsupported by the current direct-age compiler. | Resolve pathway and source boundary tension (“over7” in flow vs“≥7” in eligibility); extend direct grammar only with a warranted rule. |
| Assessments and follow-up | NCT00453999 clinical stability uses last nonmissing inpatient/outpatient assessment; NCT00867139 AE follow-up extends30days after finaldose. These horizons do not automatically mandate visits or end at discharge. | Specify endpoint-specific collection/censoring; full analysis definitions remain unencoded. |
| Renal metric and event | NCT01179919 Cockcroft–Gault reading refutes45mL/min conditionally; source clause supplies no explicit measurement event. Its structured maximum50years independently refutes age51. | Choose metric, unit and event explicitly. Different renal restrictions remain separate. |

The independent NCT00453999 structured adult-age answer stays known across the timing revisions. No historical source is rewritten. The scalar first-dose query remains unresolved; consult the actual temporal bounds/checks rather than presenting an unimplemented automatic projection as a solver result.

Evidence and translation tasks: determine intended source population; retain onset-definition alternatives, fever waivers, antiviral exceptions and pathway transitions; investigate unexplained group wording; supply the assessment/analysis definition required for the chosen endpoint. A protocol-violation count alone supplies no entry-failure attribution.

Replay complete requests under their recorded writing version. Layer-one workbook verification additionally needs the retained local full report/raw packet; a fresh registry pull is a new observation.
