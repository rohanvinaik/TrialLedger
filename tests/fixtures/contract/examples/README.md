# Worked examples of the source-report contract

These schema-4 examples use the fixed registry bodies in `../studies-*.json`. They contain copied source
values, exact eligibility passages with character offsets, direct results/reporting states and run provenance.
They contain no clinical interpretation, default assumptions, biomarker role recognition, trial-setting
assignment, clinical criterion selection or across-trial recommendations.

| File | What it shows |
|---|---|
| `record.json` | The complete report shape for the same two exemplars: NCT04852770 without posted results and NCT01030536 with nested posted outcomes, baseline, flow and adverse events. Drug classes not looked up remain explicitly unresolved. |
| `safety.json` | The unchanged handcrafted safety example: counts and sheet columns for trials with five and two event groups, including listed zeros and extra group columns blank by construction. |
| `mcp_paging.json` | The actual source-only MCP `studies` projection: the two exemplar studies on the first page of a three-study record. |

`record.json` and `mcp_paging.json` were regenerated through the current producer from those saved bodies.
That generation is not an accuracy oracle. `tests/test_contract_examples.py` separately traverses each source
path and array position to check copied values and absences. It also checks literal eligibility text against
its source slices and checks fixed manual anchors: the PTSD/COVID-19 condition wording, absence of posted
modules, baseline values 63.4 with spread 8.7 and 53.7 with spread 16.9, and the source `NA` spread/comment.
The independent safety check continues to compare every handcrafted example count with its raw event table.

Registry precision, units, source wording and comments are retained. `Not stated` is never zero or none;
`Not posted` is never no effect. An explicitly empty collection supports a zero listing count, not a claim
that no events or effects occurred. Collection-reporting metadata distinguishes omitted, empty and malformed
source arrays. Registry `NA` values and their source comments remain literal.

Eligibility section labels use only the original, unambiguous standard heading split. Physical source lines
are displayed as passages, with long lines divided at a space where possible to keep each passage within
1,600 characters. Blank lines stay with their preceding passage. Every character is retained: concatenating
the passages reproduces the complete source, and `source_start` and `source_end` locate each exact slice.
Nonstandard or ambiguous headings remain unsectioned. No token recognition assigns a clinical role or converts
those words into an eligibility assertion.

Addresses are JSON pointers into the report. Group definitions are local to their source module and study;
groups from different modules are never joined merely because their titles match. These examples exercise
source preservation and the report contract, not the clinical accuracy of an interpretation system.
