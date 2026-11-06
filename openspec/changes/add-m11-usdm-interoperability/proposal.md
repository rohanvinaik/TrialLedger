# Proposal

## Why

Clinical teams need to bring structured protocols into TrialLedger, check their represented consequences, and return changes to other study-definition systems without losing meaning or evidence. ICH M11 and CDISC USDM provide an exchange and content framework; they do not replace TrialLedger's warrants or certify interpretations of protocol text.

## What Changes

- Add version-pinned USDM import, first-class protocol-document snapshots, exact object addresses and explicit mapping/analysis coverage.
- Connect supported structured fields to existing scoped reasoning, preserving source facts, interpretations, defaults, hypotheses and adopted design choices separately.
- Add bidirectional exchange with stable identity/version mapping, preservation of unsupported content and a companion warrant manifest.
- Add M11 section mapping, conditional completeness checks and document assembly from supplied content. Missing clinical content remains a task, never generated evidence.
- Deliver through shared CLI/MCP discovery, preparation, revision and clinical export; retain existing NIH reporting and session compatibility.
- Track three independently accepted releases and eight dependent work packages in GitHub. Require symbolic consumer traces, positive/MUST-NOT tests, independent fixtures/oracles, Detective two-sign pins and cold clinical walkthroughs for each implemented slice.

These are future additions. There is no current USDM importer, M11 conformance claim, general protocol writer, automatic prose compiler or new statistical-method implementation in this proposal.

## Capabilities

### New Capabilities

- `protocol-interoperability`: faithful versioned protocol exchange, bounded projection into existing reasoning, M11 content coverage and inspectable clinical handoff.

### Modified Capabilities

None. Existing symbolic and registry-reporting invariants remain binding; the adapter supplies their inputs rather than introducing a second reasoner or altering the source workbook.

## Impact

Future work affects source retention, session source validation/origins, named projections, typed preparation, artifact revision and shared clinical delivery. A separate adapter owns USDM/M11 versions, terminology and exchange schemas. Existing `source_evidence`, `session_state`, `protocol_objects`, protocol projections/view, reasoning artifacts and CLI/MCP/export consumers are integration points, not authorization to rewrite them.

See [the roadmap](../../../docs/M11_USDM_ROADMAP.md) for delivery levels and estimates, and [design](design.md), [requirements](specs/protocol-interoperability/spec.md) and [tasks](tasks.md) for the proposed implementation contract. Planning is authorized; implementation has not started.
