# Replay and retention for the integrated design session

Each dated clinical packet keeps its question, complete reasoning request/result pairs, sampling record,
source identities, clinical decision handoff and verification receipt. Examples labelled invented remain
invented. Full raw search responses, reporting workbooks, helper programs and duplicate wire captures are
retained at the locations in each packet's local-retention record, outside Git.

With the recorded writing version installed, run any complete request using:

```bash
trialledger reason --request /absolute/path/to/requests/REQUEST.json
```

Save new output separately. A changed program produces a new observation; the committed result is not
silently relabelled. The managed revision request includes the complete previous session/result and their
content identities. The runner freshly replays both snapshots. Exact file contents and canonical content
digests have different jobs; retain both as recorded.

Complete retained inputs support layer-two replay after moving the packet: reasoning requests contain
their required snapshots and do not read the original local report path. Layer-one workbook verification
additionally requires the entire reporting folder and source bodies listed by local-retention.json. Restore
that folder intact and run `trialledger verify /absolute/path/to/restored-report`. Fetching the registry
again by NCT ID is a fresh retrieval, not guaranteed recovery of the historical bytes.

Proof packets live under `openspec/changes/integrate-warranted-design-session/evidence/`. Their manifests
name exact stored files, sizes and hashes. Storage-transform records map compressed full logs and historical
Python sources stored as `.py.txt` back to their original identities; portable `detective-state` names map
to the original hidden state where applicable. Restore into a separate scratch directory, check the recorded
hashes and use the recorded configuration/tool versions. Never copy a historical wrapper module over the
current implementation. Current-function correspondence receipts distinguish unchanged pure functions and
their actual globals from subsequently changed orchestration wrappers.

The consumer trace is a separate reachability receipt with complete-result comparisons and source hashes.
It is not a proof of clinical meaning. Executable-process checks, authored negative cases, mutation outcomes,
symbolic-contract outcomes and clinical walkthroughs retain their own scopes. Historical accepted proof
limitations remain limitations; they are not converted to passes by a newer integration.
