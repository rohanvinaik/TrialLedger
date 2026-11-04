# Wave 1 receipt (coordinator, 2026-11-04)

Integrated basis for packets A, B, C and D and the oracles B′, C′ and D′. Hashes are `shasum -a 256` at commit time. Every file was re-verified by the coordinator, not accepted on its handoff.

| File | sha256 |
|---|---|
| `TrialLedger/layer2/protocol_numbers.py` | `6cadefa997401ccc…` |
| `TrialLedger/layer2/protocol_objects.py` | `01c887fc33b37d5b…` |
| `TrialLedger/layer2/protocol_schedule.py` | `e9f91e91be9e3b1e…` |
| `TrialLedger/layer2/protocol_policies.py` | `74c693faf4443e3a…` |
| `TrialLedger/layer2/protocol_statistics.py` | `a86c89f50ed81869…` |
| `TrialLedger/layer2/signals.py` | `4cfbbd0d48487b9b…` |
| `tests/test_protocol_numbers.py` | `06fa74d551b02d0e…` |
| `tests/test_protocol_objects.py` | `0c1760b69820110c…` |
| `tests/test_protocol_schedule.py` | `af3842bb4258848e…` |
| `tests/test_protocol_schedule_oracle.py` | `5cfadd4bbb24f9fa…` |
| `tests/test_protocol_policies.py` | `ed9dee7192214e22…` |
| `tests/test_protocol_policies_oracle.py` | `33baa0d674aeef9d…` |
| `tests/test_protocol_statistics.py` | `7028b5a710dbf620…` |
| `tests/test_protocol_statistics_oracle.py` | `aa064715de401e77…` |
| `tests/test_protocol_import_contracts.py` | `0c232fb7b493c334…` |
| `tests/test_signal_support_resolution.py` | `16de423e30e14871…` |
| `openspec/changes/connect-protocol-design-workflow/interface/fixtures/schedule.json` | `181f834d4b9ad969…` |
| `openspec/changes/connect-protocol-design-workflow/interface/fixtures/policy.json` | `8ef9294eb64ee380…` |
| `openspec/changes/connect-protocol-design-workflow/interface/fixtures/binomial.json` | `ef52f2c93af512fc…` |
| `openspec/changes/connect-protocol-design-workflow/interface/fixtures/rationals.json` | `44f1941ac99b74a1…` |
| `openspec/changes/connect-protocol-design-workflow/interface/fixtures/objects.json` | `508003acd51e5356…` |

## Verified results

**Tests.** The protocol test files, `test_signal_support_resolution.py` and `test_signals.py` give
`482 passed`. Each operator agrees with its independently written oracle:
- B′: endpoint cells over every fixture plus 400 seeded random unions and metamorphic properties;
- C′: an explicit node graph over every fixture plus 60 random models covering every status and resolution
  pair;
- D′: all 2^n outcome vectors for n ≤ 10, every k and a grid of p values.

**Fixture checks.** Each oracle first checked every fixture expectation with no production import. All
agreed, including the hand-derived policy fixtures.

**Support gate**, traced through `signals.evaluate` with known outer support:

| Case | Admission | Status |
|---|---|---|
| Missing alignment role | `binding_unresolved` | stays `known` |
| Proposed alignment | `proposed_refused` | `proposed` |
| Fully declared STA-1 | accepted | `known` |
| Proposed prohibition | `proposed_refused`, with `calculation_code` `violated` | `proposed` |
| Known prohibition | accepted | `violated` |

**Lint, types and imports.**
- `ruff check .` and `ruff format --check .` are clean.
- `ty` is clean on every new module except one advisory finding in `protocol_statistics.py`: a mixed-type row
  dict, where the outcome is always a string.
- The static import-direction contract passes, with one named pre-existing edge
  (`decision_tables → solver_work → session_state`, a lazy import for `canonical()`).

**Not yet run:**
- Detective two-sign pins and CrossHair on the new pure helpers. The pins are scheduled serially by the
  coordinator after the slice-2 freeze.
- The full suite runs in the commit gate.
- No CLI, MCP or clinical claim: the operators aren't registered yet.

## Corrections made during wave 1 (coordinator)

1. **Standing words (R6b).** The first correction relabelled missing, unresolved or conflicting internal
   support as `proposed`, which a side agent flagged. `signals.evaluate` now accepts `support_resolution`, and
   no standing word changes meaning.
2. **Import isolation.**
   - `ledger.md`'s runtime `sys.modules` test was impossible, because `TrialLedger/layer2/__init__.py`
     imports `service`.
   - It is replaced by the static closure contract in `tests/test_protocol_import_contracts.py`.
   - Packet A's runtime test is kept as a weaker supplementary check.
3. **Interface additions.**
   - `EXAMPLES` in each operator, because discovery wraps it.
   - A duplicate claim id refuses as `<operator>_duplicate_claim`.
4. **Accepted interpretation (packet C).** Any variable whose `predicate.key` is `policy_state` is refused as
   reserved, not only the exact reserved formula key. This is stricter, and it is consistent with R2: callers
   can never declare the reserved state.
5. **Typing casts.** The coordinator added typing casts after the dict guards in packets B and D. Behavior is
   unchanged; the tests were re-run.
