# Worked examples of the contract

Expected values a producer (unit A, the record; unit B, universes) and a consumer (unit C, the workbook;
the MCP record tool) are both held to, so that the two cannot agree on the same mistake. Each was cut from the
saved registry bodies in `../studies-*.json` and checked by hand against those bodies, as described below.
`tests/test_contract_examples.py` holds each to `contract.FIELDS` and `contract.SHEETS`, and re-reads every
plain value from the body it came from.

| File | What it shows |
|---|---|
| `record.json` | A schema-3 record of two studies: NCT04852770 (an ordinary study without results; values the registry does not hold; the general universe) and NCT01030536 (posted results nested as the registry nests them: a measure with its groups, its denominators per group, a class and a category, and the registry's "NA" values with their comments; a baseline measure; participant flow with a withdrawal reason; an adverse-event table; an unresolved drug class; a domain pack whose applicability is unresolved) |
| `universes.json` | The universe assignment of the three trials asked for by number: the PTSD trial (general), the CLL and lymphoma immunotoxin (haematologic), and the solid-tumour basket without condition MeSH (solid, from its free-text condition) |
| `safety.json` | The Safety sheet's columns and rows for two trials with 5 and 2 adverse-event groups (n = 5; the second trial's G3 to G5 cells are blank, as they cannot apply), and the Groups sheet's G1 ... Gn names |
| `mcp_paging.json` | The MCP record tool's `studies` part, paged: the first page of two of three studies |

## The shapes these examples fix

- A registry value is held plain, as the registry holds it (its precision, units and wording; a registry "NA"
  stays "NA", with its comment beside it).
- A value the registry does not hold is a value object `{"status": "not_stated", "note": <the ledger's
  absence state>}`.
- A rule's reading is a value object `{"status", "rule", "words", "result", "note"}`: the rule (the contract's
  rule for the field), the words it read, what it found, its status and why.
- A domain reading a trial's universe does not permit is absent (the PTSD trial has no coordinates; the
  universe reading's note says why); the haematologic trial's one pack, prior lines, requires an intervention
  that treats the cancer, and RxNav gives CAT-8015 no ATC class, so its applicability reads unresolved in the
  universe reading (`treated_target`, `applicability`) and the trial carries no coordinate.
- Each Safety row is addressed by a JSON pointer into the record the sheet was written from; in
  `safety.json` that record holds the two trials in the order listed under `trials`.

## How each value was checked

The values were cut by index from the saved bodies, then each was read against the body's own JSON, printed
for the purpose, on 2026-11-01:
- NCT04852770: titles, status and why stopped, start and last update dates, sponsor and class, study type,
  phase, purpose, allocation, masking, enrollment, conditions, condition MeSH terms, and the DMC flag
  (false), each against the protocol section; the acronym is absent from the identification module.
- NCT01030536: the first posted measure's type, title, population, parameter, unit, time frame and reporting
  status; its first two groups; its denominators (7 and 6 participants); its class and category, which hold
  no title; the first two measurements, both "NA" with the comment "Data was not reported as MTD was not
  reached in the specified arm group."; the baseline module's groups and denominators (7 and 6), and the
  "Age, Continuous" measure (mean, standard deviation, years; 63.4 ± 8.7 and 53.7 ± 16.9); the flow's
  "Overall Study" period, STARTED 7 and 6, and "Withdrawal by Subject" 0 and 0; the adverse events' time
  frame and threshold ("5"), the absent all-cause mortality comment, the first two groups' serious counts
  (0 of 7, 3 of 6), and "Lung infection" (0 of 7, 0 events; 0 of 6, 0 events); the first intervention
  (DRUG, "CAT-8015 20 mcg/kg"). The drug class and prior lines are the readings the baseline run's
  landscape.json (schema 1) records for this trial: drug class unresolved (the record names no cause; the
  cause's wording is unit A's to settle), prior lines unnarrowed (no typed atom narrows them).
- `universes.json`: each found term against the trial's condition MeSH terms and ancestors, its free-text
  conditions and titles; NCT01030536's ancestors hold Lymphoma, Leukemia and Neoplasms, NCT01827384 has no
  condition MeSH term. The third source is each treatment trial's drugs' ATC classes as the 3-trial baseline
  run's `classes.json` records RxNav's answers (re-read 2026-11-01, unit B): NCT01827384's Carboplatin
  (L01XA), Everolimus (L01EG, L04AH), Temozolomide (L01AX) and Trametinib (L01EE) fall under L01, Adavosertib
  and Veliparib have no ATC class; NCT01030536's CAT-8015 names have none; NCT04852770's behavioural
  interventions were never looked up. The notes are the Trial index words `universes.assign` writes.
- `safety.json`: every count against the serious-event statistics of both trials (Lung infection, Blood
  creatinine increased; Anaemia, Disseminated intravascular coagulation), each group's G column against the
  order of its event groups.
