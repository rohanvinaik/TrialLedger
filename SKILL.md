---
name: trialledger
description: Give a clinician a clean reference workbook and matching source-backed JSON for named or searched clinical trials. Operate the registry harness and answer from its record. A separate layer-two reason operation exposes typed symbolic logic; the complete automated trial-writing design is partly implemented.
---

# TrialLedger

Read AGENTS.md for the complete procedure. Explain both layers: the available source-faithful reference-sheet
operation, and the fully designed automated clinical trial writer whose useful partial symbolic operations
are available separately. Do not promise a finished new protocol.

Use the working layer-two tools for the clinician's own work now, independently of the full future writer.
Let them choose a question; explain the relevant operation/premises/limits, help confirm material assumptions,
run it and present proof, defaults, proposals and open items in clinical terms. The person exercises judgment
over the result. Do not reduce these capabilities to developer demonstrations or a roadmap.

## What the person can explore

- Gather a clean reference sheet, then drill into exact population/eligibility, outcomes and time points,
  group-specific efficacy/safety, source drug identities/classes and direct registry consistency findings.
- Ask what follows from confirmed population, cohort, numeric or temporal restrictions. Use entailment;
  show the premise and separate a deduction from an assumption or unresolved result.
- Explore supported NSCLC setting/prior-line/biomarker-selection domains from explicit premises, with
  defaults and proposals shown separately.
- In a declared, explicitly represented comparison set, inspect statement rates and silence bounds,
  proposed class associations, setting/class occupancy, near-miss pairs and conditional observation rarity.
  Neither missing detail nor rare/common wording establishes clinical absence, relevance or causation.
- Explore the complete automated trial-writing design and its remaining integration work: source binding,
  compatible evidence, geometry/significance, recommendations, choices and warranted protocol outputs.

Use natural starting points: “Show me the trial evidence,” “What follows from these enrollment restrictions?”
or “Which documented design features are shared or different in this comparison set?” Do not require the
person to know internal names. A complete protocol generator is not currently callable.

## Reference sheet

1. Install on Python 3.12+: `pip install "git+https://github.com/rohanvinaik/TrialLedger"`.
2. Run `trialledger doctor --run FOLDER`; prefer direct mode.
3. Form flags or `--request FILE`, or `--ids NCT...,NCT...`. Preview with
   `trialledger landscape --run FOLDER <request flags> --preview` and show `resolution.json`.
4. Repeat without preview to gather. Exit 3 awaits named responses in next.json; fetch each exactly and save
   unchanged. Exit 0 is complete/previewed, 2 names refusal/stop, 1 gives retry advice. Repetition resumes;
   changed requests use new folders. Never retype, reformat, shorten or correct a relay body.
5. Check requested-ID accounting and deliver landscape.xlsx. Answer from landscape.json, not your own
   reconstruction of a registry page. The JSON is a declared clinical selection; complete source responses
   are retained separately.

Source copies are plain values with sources defined once in `fields`. Direct transformations name their
rules/inputs. Keep exact prose, populations, local groups, denominators, units, periods, precision, zero and
false. Not stated is not none; not posted is not no effect; empty listings are not zero harms. Malformed
scalar source types produce a named refusal, not a fabricated typed report. Drug identity/conflicts use
canonical source evidence; no alias-first choice or name-prefix widening. Eligibility divisions do not
interpret clinical meaning. Registered plans and posted observations remain separate.

Do not infer biomarker roles, setting, current care, grades, comparability, planning targets or reusable
standards while producing the report. Those are separately identified reasoning tasks.

## Typed symbolic reasoning

First discover the actual interface: call MCP tool `reason` with arguments
`{"request":{"operation":"describe"}}`, or put `{"operation":"describe"}` in a file and run
`trialledger reason --request FILE`. The response gives accepted/required fields, nested model vocabulary,
complete runnable examples, limits and current availability. Use those shapes rather than inventing fields;
this works for an MCP-only agent without source-file access.

The reply also provides clinical use cases, result interpretation and supporting Python entry points.
`examples` contains direct requests; `capability_examples` entries wrap a runnable `request` with invented
premise/expected-result notes. Execute that request and retain its demonstration label when illustrating it.

Then use `trialledger reason --request FILE`, or MCP `reason(request)`, with an `operation` of `entailment`,
`coordinates` or `corpus`. The same public contract is `TrialLedger.layer2.run(request)`.
State the origin of supplied premises; an agent-authored assertion is not a registry fact merely because a
solver can reason from it. The operation does not mutate the report. NSCLC coordinate rules require that
explicit domain; corpus inputs require declared typed evidence and denominators.

If a premise is missing, ask about its clinical distinction: all participants or one cohort; required versus
permitted; prior therapy for advanced disease or any treatment; exposure versus follow-up time. Show your
proposed encoding in plain words, retain its user/source origin and keep unknowns. Do not invent an
interpretation of eligibility or label an agent-created premise as a known registry assertion. For corpus
work, confirm the set and represented features instead of assuming trials sharing a query are comparable.

Deliver the chosen clinical question, confirmed premises/origins, result, proof or assumption basis and open
items, plus the unchanged structured response for reuse. With file access, save it separately (for example
`reason-result.json`) beside the source workbook/record; reason itself does not write that file or alter the
report. Help the person revise a premise and rerun when they choose, without inventing missing source facts.

Supporting literal parsers, registries, applicability and evaluation utilities remain implemented Python
building blocks. The discovery reply names their entry points/preconditions. They are not extra MCP clinical
operations and do not supply the missing automatic source compiler.

This complete entailment request asks whether male participants fit a brief requiring female participants.
It returns a complete operation with decision REFUTED and premise `population`. That is a conditional
consequence of the supplied brief, not an extracted study finding or a universal clinical sex ontology.

```json
{
  "operation": "entailment",
  "assertions": [{
    "class": "ScopedAssertion",
    "id": "population",
    "criterion_ref": "user:brief",
    "modality": "required",
    "body": {
      "class": "Literal",
      "subject": {"class": "Subject", "kind": "participant"},
      "predicate": {"class": "Predicate", "kind": "demographic", "key": "eligible_sex"},
      "value": {"class": "Value", "kind": "enum", "members": ["female"]}
    },
    "rule": {"class": "Rule", "id": "user-choice", "version": "1", "warrants": ["user:brief"]},
    "status": "known",
    "resolution": "resolved"
  }],
  "query": {
    "class": "Literal",
    "subject": {"class": "Subject", "kind": "participant"},
    "predicate": {"class": "Predicate", "kind": "demographic", "key": "eligible_sex"},
    "value": {"class": "Value", "kind": "enum", "members": ["male"]}
  }
}
```

Keep disjunctions, qualifiers, referents, conditions, cohorts and time in their representation. Required(A or B)
does not require either alone. A proposed premise is not usable as fact; an interpolated one cannot produce a
known conclusion. Preserve named undetermined/inconsistent/unsupported outcomes and blockers.

The full automated writer additionally needs source-to-assertion compilation, general bindings, evidence
adapters, geometry/significance integration, recommendations, user closure and protocol outputs. Its complete
design and actual component state are in openspec/changes/add-design-synthesis/design.md. No current
`design`/`edits` operation, automatic annotation import or old raw-reader fallback is available.

## MCP and verification

`trialledger mcp` serves doctor, scope, landscape, save_fetch, record and reason. Preview with scope, gather
with landscape and answer with record/address. Follow page.next_offset; pages hold at most 50 entries.
`reason` is a separate typed request. `verify FOLDER` replays saved reporting/archival inputs under their
writing version; it establishes reproduction rather than clinical truth. `pull` preserves complete source
JSON/CSV and archival workbooks.
