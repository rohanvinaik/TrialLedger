# ICH M11 / CDISC USDM interoperability roadmap

**Status: proposed future direction. No integration is implemented by this plan.**

The intended workflow: **bring in a structured protocol, inspect what it says, check the represented design, revise a choice and return a protocol package other systems can use—alongside the evidence and decision workbook.**

ICH M11 standardizes protocol content and organization. CDISC USDM represents study definitions for exchange. TrialLedger contributes the explicit reasoning: what follows, what conflicts, what is merely a reading, and what remains the person's decision. These are complementary jobs. A valid interchange file is not a verified clinical design.

## Delivery roadmap

| Release | Useful capacity | Acceptance boundary | Cumulative effort estimate |
|---|---|---|---|
| **M1: Import and check** | Retain a USDM protocol, inspect exact objects and project a declared subset into existing reasoning and clinical delivery. | Supported fixed visits, scoped populations and explicitly mapped definitions; ambiguous prose stays unresolved; everything else stays preserved. | **2–4 engineer-weeks** |
| **M2: Bidirectional exchange** | Adopt a supported change, replay consequences and export USDM with a companion warrant manifest. | Unchanged content survives round trips; deliberate edits update the right objects/versions; CLI/MCP and workbook tell the same story. | **6–10 engineer-weeks** |
| **M3: Broad USDM and M11 support** | Cover broader study graphs and M11 content, conditional completeness and document assembly. | Tested version/profile and external validation are published; unsupported reasoning remains explicit. | **3–6 engineer-months** |

These are planning estimates including our verification discipline, not calendar promises. Re-estimate after IO-01 against externally authored files and the actual gap inventory. Broader exchange does not require every statistical method or narrative clause to have a solver. Automated clinical authorship, partner-specific integrations and FHIR/SDTM/CTIS delivery are separate projects.

## What needs building

| Package | Deliverable | Depends on | Release |
|---|---|---|---|
| [**IO-01**](https://github.com/rohanvinaik/TrialLedger/issues/2) | Pin standard/terminology versions, external fixtures, compatibility profile and public contracts. | — | M1 |
| [**IO-02**](https://github.com/rohanvinaik/TrialLedger/issues/3) | Protocol-document snapshots, object addresses and source origins without disturbing NIH evidence. | IO-01 | M1 |
| [**IO-03**](https://github.com/rohanvinaik/TrialLedger/issues/4) | Explicit import mappings into scoped objects; separate preservation, conformance, interpretation and actual reasoning coverage. | IO-01, IO-02 | M1 |
| [**IO-04**](https://github.com/rohanvinaik/TrialLedger/issues/5) | Public CLI/MCP lifecycle and clinical handoff, including a meaningful revision and evidence-linked workbook. | IO-03 | M1 |
| [**IO-05**](https://github.com/rohanvinaik/TrialLedger/issues/6) | Native-graph write-back, supported edits, stable versions, round-trip conservation and portable warrants. | IO-03, IO-04 | M2 |
| [**IO-06**](https://github.com/rohanvinaik/TrialLedger/issues/7) | Final M11 content crosswalk, conditional completeness and document assembly from supplied content. | IO-01, IO-05 | M3 |
| [**IO-07**](https://github.com/rohanvinaik/TrialLedger/issues/8) | Broader timeline/epoch/arm mappings, preservation of complex or unsupported graphs and scope-aware compatibility profiles. | IO-03, IO-05 | M3 |
| [**IO-08**](https://github.com/rohanvinaik/TrialLedger/issues/9) | Independent cross-release acceptance, external interoperability checks and honest final proof/coverage reporting. | IO-04, IO-05, IO-06, IO-07 | M3 |

Tests, documentation, Detective pins and clinical walkthroughs belong to **each package**. IO-08 audits the integrated result; it does not postpone those obligations. Independent fixture/oracle work can run alongside implementation after contracts freeze. Shared source/session/revision/export files have one integration owner; parallel workers get explicit file and semantic contracts.

## One example of the value—and the boundary

Suppose an imported protocol specifies a nominal day-84 assessment, permits days 77–91, and separately plans collection only through day 80. Under explicit matching scope and accepted bindings, the current schedule operator can show three different things: a feasible visit exists; the nominal day is not collected; and days after 80 through 91 are uncovered. The export must retain the original permitted window until the person changes it. It must never quietly replace the window with days 77–80.

Now add “only after treatment discontinuation.” The timing calculation can remain useful while its applicability stays conditional. The importer cannot turn a planned obligation into an observed event, or a document's approval code into the person's adoption. This is why the bridge must carry scope and warrants, not just matching field names. This example is invented; it describes the intended adapter workflow, not a current USDM demonstration.

USDM also retains eligibility text. “No prior systemic therapy” still needs its setting and time scope resolved. An imported label cannot do that reasoning for us. Conversely, an unambiguous structured value with a versioned codebook should enter by a direct warrant without needless human reconfirmation.

## What “compatible” will mean

- **Preserved:** exact source bytes and addressed content remain available, including unsupported objects.
- **Conformant within a named profile:** schema, references, terminology and applicable business/content rules were checked, with their versions and outcomes.
- **Mapped:** a documented rule or explicit reading connects a source object to a TrialLedger representation.
- **Checked:** an actual supported operation ran, with its scope, admission, determining premises and limits visible.
- **Portable:** native USDM, documented extensions and companion warrants have distinct guarantees. A recipient that drops the warrants does not thereby retain our acceptance or proof history.

Those dimensions stay separate in conversation, stored artifacts, revisions, spreadsheets and release reporting. There is no blanket “fully understood” or regulatory-approval badge. Standardized data can expand the mechanically knowable floor; it cannot supply missing clinical judgment.

## Tracking and authority

The public [GitHub Project](https://github.com/users/rohanvinaik/projects/6) and [parent issue](https://github.com/rohanvinaik/TrialLedger/issues/1) track execution, with native child/dependency links. Release milestones are [M1](https://github.com/rohanvinaik/TrialLedger/milestone/1), [M2](https://github.com/rohanvinaik/TrialLedger/milestone/2) and [M3](https://github.com/rohanvinaik/TrialLedger/milestone/3); no due dates or owners are promised.

The versioned [OpenSpec proposal](../openspec/changes/add-m11-usdm-interoperability/proposal.md), [design](../openspec/changes/add-m11-usdm-interoperability/design.md), [requirements](../openspec/changes/add-m11-usdm-interoperability/specs/protocol-interoperability/spec.md) and [tasks](../openspec/changes/add-m11-usdm-interoperability/tasks.md) hold the proposed contract. The [project theory](THEORY_OF_THE_CASE.md) and the person's instructions govern it. Existing incomplete protocol-design work remains separately tracked.

Close a package only with evidence at its real consumers: authored positive/MUST-NOT cases, independent fixtures/oracles, symbolic traces, scoped Detective two-sign/contract checks, public CLI/MCP parity, an actual revision/export and a cold clinical walkthrough in a different trial category. Record unrun proofs, unresolved meanings and accepted pin limitations distinctly. Internal fixtures do not prove interoperability with an untested partner.

Implementation proceeds on main under the existing project policy. Issues and milestones organize releases; they do not introduce feature branches or a new approval process.

## Reference baseline

- [ICH M11 overview](https://database.ich.org/sites/default/files/ICH%20M11%20Explainer_May2026.pdf): guideline, template and technical specification are distinct artifacts.
- [Final M11 technical specification](https://database.ich.org/sites/default/files/ICH_Step4_M11_Final_TechnicalSpecification_2025_1119.pdf) and [template](https://database.ich.org/sites/default/files/ICH_Step4_M11_Final_Template_2025_1119.pdf), adopted 19 November 2025.
- [CDISC USDM 4.0.0](https://github.com/cdisc-org/DDF-RA/releases/tag/v4.0.0), with its [exchange schema](https://github.com/cdisc-org/DDF-RA/blob/v4.0.0/Deliverables/API/USDM_API.json) and [data dictionary](https://github.com/cdisc-org/DDF-RA/blob/v4.0.0/Deliverables/UML/dataDictionary.MD).
- [Published M11 crosswalk](https://github.com/cdisc-org/DDF-RA/blob/main/Documents/Mappings/m11_mapping.xlsx) and [ClinicalTrials.gov crosswalk](https://github.com/cdisc-org/DDF-RA/blob/main/Documents/Mappings/ct-gov_mapping.xlsx). These moving links are discovery references; IO-01 must pin the exact artifacts before using their mappings.
