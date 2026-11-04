# Two adopted restrictions, one impossible draft

This is a simulated new-trial draft informed by two real registry records. No clinician confirmation is
claimed. The source wording, snapshot identities and exact addresses are retained in
[source-evidence.json](source-evidence.json). This is an evidence excerpt, not a complete source archive;
the original reporting run also retains the full source responses and reproducible workbook.

- NCT03653546 (AZD3759): inclusion item 5 requires MRI-documented CNS metastases including brain metastases.
  Item 11 separately distinguishes measurable and non-measurable CNS lesions. We adopt only the
  requirement for brain metastases in this draft, not a universal measurable-lesion requirement.
- NCT01774721 (ARCHER 1050): the exclusion is any history of brain or leptomeningeal metastases. For the
  contradiction check, we adopt its exclusion of patients with brain metastases. We do not claim to have
  represented every historical or leptomeningeal case.
- A separate ECOG <=1 restriction is included to check that an unrelated premise stays out of the proof.

The two adopted brain-metastasis restrictions address the same participant and entry scope. They are
explicit premises of the simulated draft, not an automatic semantic extraction or a claim that the real
trials are individually inconsistent. `known` in the request means accepted within this stated simulation;
it does not certify a reading or a clinician exchange.

## Run it

The explicit draft premises are in [request.json](request.json). Its complete public response is saved
in [result.json](result.json).

```sh
trialledger reason --request examples/template-merge/request.json
```

The result is INCONSISTENT, with exactly `excludes-brain-metastases` and `requires-brain-metastases` in the
proof. `performance-status` is absent. Removing either of the two conflicting premises restores
satisfiability. Changing ECOG does not repair their contradiction. While inconsistent, another query still
returns INCONSISTENT rather than becoming a universal entailment.

CLI and initialized MCP use the same request. The README update verification exercised these controls and
the source reporting run's `verify` command. These are scoped executable checks, not a new Detective pin
or a clinical validation claim.
