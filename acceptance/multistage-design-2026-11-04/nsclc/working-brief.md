# Cold compact preparation: simulated NSCLC draft

This is a draft-only encoding and delivery exercise. There are no comparator records or source claims.
Every clinical choice is simulated, explicitly attributed as such, and is not an authenticated clinician confirmation.
No production request-preparation source or Python model builder was consulted. The hand-authored compact request
was expanded only by the public `prepare` operation; the transport script copied its returned request unchanged.
The operator was cold to this new preparation interface, but already knew TrialLedger's existing symbolic semantics.
This is not evidence about a model with no prior familiarity with the project.

## The intended choices

An invented advanced EGFR-mutant NSCLC platform starts with ECOG≤1, requires at least one of L858R or exon19 deletion,
excludes brain metastases only when neurologic instability is also present, permits prior adjuvant therapy while
separately excluding prior EGFR-TKI exposure, and admits only ≥50% induction improvers into a later Stage C.
The set-valued mutation representation permits compound mutations; the alternative exon20-only profile explicitly
lacks both qualifying mutations. Permission does not override the separate TKI exclusion.

“First-line” is the intended clinical framing, not a computed setting conclusion. Other prior advanced systemic
therapy, complete eligibility, treatment schedules, statistical design and safety monitoring are not represented.
The exercise checks these six restrictions, not a complete protocol or actual patient eligibility.

## What the computations returned

- ECOG2 was ruled out with ECOG≤1 and became allowed but not required after widening to ECOG≤2.
- Stable CNS disease and L858R+exon20 compounds remained possible under the represented restrictions.
- Neurologically unstable CNS disease, exon20 without either qualifying mutation, and prior EGFR TKI remained ruled out.
- Adjuvant permission remained visible beside the TKI exclusion; it never overrode that exclusion.
- A 40% improver was ruled out of Stage C; a 60% improver remained possible under its represented rule.
- The Stage C scope did not attach an open-cohort blocker to unrelated entry answers.
- CLI and initialized MCP produced identical baseline results, revisions and exported bytes.

## Revision receipt

| Decision | Primary change code | Verdict axis | Remaining requirements axis |
|---|---|---|---|
| adjuvant-and-tki | requirements_changed | unchanged | changed |
| cns-admission | requirements_changed | unchanged | changed |
| ecog-admission | answer_changed | changed | changed |
| genotype-admission | requirements_changed | unchanged | changed |
| withdrawal-admission | requirements_changed | unchanged | changed |

A stable, ruled-out alternative has no residual screening list, so those individual checks reported input_only;
its compatible paired alternative reported requirements_changed when the shared ECOG requirement changed.
That is a change of remaining work, not a change of its CNS, genotype or TKI verdict.

## Measured format burden

The compact input contains 6 criteria, 5 decisions and 10 option profiles.
It has 265 recursive JSON property occurrences and 6,235 canonical UTF-8 bytes;
the expanded request has 1728 property occurrences and 34,934 bytes.
Preparation accepted the first attempt. It disclosed 367 defaults. The full pretty-JSON
preparation reply was 113,004 bytes; each default receipt was independently checked against its
exact output pointer, with zero mismatches. Two public discovery calls preceded authoring. Full replies were
explicitly requested for baseline/revision parity; their large sizes are recorded, not described as compact replies.

The complete input, prepared request, public replies, initialized MCP tool discovery, read page and exports are beside
this brief. `measurements.json` records per-call request/response bytes, revision axes and returned export paths.

## Delivery

The CLI review is [decision-list.md](cli-export-final/review/decision-list.md) and
[design-review.xlsx](cli-export-final/review/design-review.xlsx). The matching MCP export is in `mcp-root/reasoning-exports/`.


## Retained preparation, without copying expanded JSON

The public no-copy path was then verified independently over CLI and initialized MCP. Preparation and computation
used the same compact input as above. The next computation named only the returned preparation artifact ID;
no expanded request was sent in that call. The canonical retained expanded request and computed baseline result
were exactly equal to the earlier copy-based path. Preparation IDs, computed IDs and complete canonical payloads
were equal across CLI/MCP.

- CLI preparation/computation replies: 981 and 9,546 bytes.
- MCP preparation/computation payloads: 999 and 9,564 bytes.
- MCP run-by-handle request: 191 canonical JSON-RPC bytes.
- All computation and revision reply payloads stayed within the 24,576-byte default.
- Decision reading used 6 calls: one directory and five exact-address reads. All five clinical views
  were recovered; the directory was never treated as evidence.
- The ECOG revision and final review workbook/Markdown again matched across CLI/MCP, including all remaining-requirement axes.

The negative omission probe left standing `proposed` and resolution `unresolved`.
Execution returned `UNDETERMINED` with `no_constraint_mentions_query, proposed_refused:ecog-floor`, no proof and no promoted standing.
`prepared-handle-receipt.json`, `prepared-delivery-receipt.json` and `omitted-standing-receipt.json` retain the exact checks.
The bounded-path final CLI export is in `cli-handle-export-final/review/`.

## Final integration replay

The unchanged compact clinical input was replayed after parent-level support/origin aggregation was completed. Full CLI/MCP revision results and exported bytes match. Non-ECOG verdicts remain unchanged; their parent decisions now retain the changed support and origins alongside the changed remaining requirements. Initial format-burden measurements above describe the original cold pass; the summary receipt separately records final bounded-delivery measurements and file hashes.
