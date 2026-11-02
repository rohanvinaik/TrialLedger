# The contract's fixtures

What `tests/test_contract.py` holds `TrialLedger/contract.py` to (refine-landscape-record 0.4).

| File | What it is |
|---|---|
| `metadata.json` | The API's field metadata, `GET /api/v2/studies/metadata`, as saved by the baseline run of 2026-11-01 (`~/tools/TrialLedger-runs/baseline-2026-11-01/api-metadata/metadata.json`); the same content as `TrialLedger/registry/ctg-metadata.json`, which a test checks |
| `enums.json` | The API's enum table, `GET /api/v2/studies/enums`, fetched 2026-11-01 and saved byte for byte; the same content as `TrialLedger/registry/ctg-enums.json`, which a test checks |
| `studies-ids-3.json` | The three trials asked for by number in the baseline run (NCT01030536, NCT01827384, NCT04852770), the registry's page exactly as saved |
| `studies-osimertinib-subset.json` | Seven of the 49 osimertinib phase-3 trials of the baseline run, each study object exactly as the registry sent it, chosen by `select_bodies.py` |

The whole baseline (3.5 MB of bodies) is more than a fixture should hold, so the osimertinib trials are a
subset: the fewest that, with the three trials by number, hold every API path the contract reads, plus the two
trials whose only condition names no disease (NCT02959749, "Progression Free Survival"; NCT02151981,
"Anticancer Treatment"). The choice is deterministic. To make it again, from the repository root:

```bash
.venv/bin/python tests/fixtures/contract/select_bodies.py ~/tools/TrialLedger-runs/baseline-2026-11-01
```

It prints the trials kept and the paths no baseline trial holds; those paths are exactly
`contract.UNEXERCISED`, each with why it is carried all the same. Re-run it whenever the contract gains a path.
