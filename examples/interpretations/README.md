# A continuing design session with competing interpretations

Every clinical value, study identifier, source address and definition in this packet is **invented**.
These are executable teaching premises, not an IPASS reconstruction or clinical recommendations. The
operation reads no registry text and retrieves no external evidence. The assistant supplies the typed
readings; TrialLedger computes their compatibility and consequences.

## Begin with the person's design question

> “We are designing an adult NSCLC trial. Should we allow ECOG 3? Can we use the comparator's schedule
> and analysis populations? Show me which things are fixed and which depend on a reading.”

The working brief accepts adulthood and ECOG at least 0. “Fixed” means accepted for this session:
these invented user premises remain separate from registry facts. The person has not selected an upper
PS limit. The assistant proposes ECOG 0–2 and 0–3 in isolated frames, retaining their proposed standing.
An intentionally incompatible under-18 reading tests the fixed adult requirement.

Run [draft-choices-request.json](draft-choices-request.json):

- ECOG 0–2 and 0–3 are both compatible with the fixed floor.
- ECOG 3 is refuted under 0–2 and allowed but not required under 0–3. The common answer remains open.
- The under-18 reading is refuted by the fixed adult premise, with both premise ids in its warrant.
- The adult query is entailed directly from the fixed floor independently of the proposed readings.

The assistant can discuss either reading now. No confirmation is needed to show a labelled hypothetical
consequence. Ordinary `entailment` still refuses proposed premises: isolated assumption does not admit them
to source truth or to another interpretation.

## Settle a choice, then revise it

The person chooses 0–2. [The selected request](draft-selected-PS0-2-request.json) records that choice;
its ECOG 3 consequence is refuted under the selected frame. [The revised request](draft-revised-PS0-3-request.json)
selects 0–3 instead: ECOG 3 becomes allowed but not required. Every frame and the original evidence remain
inspectable. Selection changes the working choice without certifying that a comparator used it.

This checks the represented age and PS restrictions, not every condition of patient enrollment.

## Keep the schedule's event roles distinct

[assessment-roles-request.json](assessment-roles-request.json) accepts an explicit invented rule that the
first **scheduled routine** assessment lies in days 35–49 from randomization. A separate observed log names
an **actual unscheduled** scan on day 28. Four proposed plans are checked against those facts:

| Proposed interpretation | Computed compatibility |
|---|---|
| Routine first assessment on day 42 | Compatible |
| Routine first assessment at the inclusive day-49 boundary | Compatible |
| Treat day 28 as the routine first assessment | Refuted by the fixed routine window |
| Retain day 28 as the separate actual unscheduled scan | Compatible |

The fixed routine window is an explicit teaching premise here. A real source's wording “every 42 ±7 days”
still needs its own interpretation and event binding; this operation does not derive the reading from text.
The deciding event identity, temporal claim and rule stay visible. The actual scan cannot silently become a
scheduled visit, nor can the schedule establish actual attendance.

## Use partial population information without overclaiming

An invented comparator reports an ITT parent of 200 and an EFQ subset of 160. The arithmetic gives 40 outside
EFQ. Whether that population correspondence applies to the interpretation is separately represented.

With [the application unresolved](population-unresolved-request.json), both the aligned reading and the
claim that everyone was analysed remain unresolved. The 40-person calculation is retained. Even though
“outside EFQ = 0” conflicts mathematically with that count, the unsupported application cannot eliminate
the reading. Fixed adulthood is still settled independently, and the exact conditional PS result remains
visible inside each frame's query decision.

With [the binding resolved](population-resolved-request.json), the aligned reading is compatible and the
“everyone in EFQ” reading is refuted. The binding remains proposed: it is an explicit hypothetical
correspondence, not a verified source fact. A consequence from the one remaining declared frame therefore
keeps its conditional, proposed standing. The supplied family is not assumed exhaustive of actual protocols.
The 40-person difference establishes coverage under the supplied relation, not the reason for nonmembership.

## Check the adopted endpoint definition

[endpoint-inputs-request.json](endpoint-inputs-request.json) supplies a versioned adopted change-score
definition requiring **observed** baseline and week-12 measurements. Baseline is available; the fixed source
does not state week-12 availability. Three hypothetical plans show the distinction:

| Plan | Computed result |
|---|---|
| Supply an observed week-12 assessment | Compatible under that availability hypothesis |
| Supply an imputed value, leaving observed availability unknown | Unresolved; imputation does not fill the observed-input requirement |
| State that observed week 12 is unavailable | Refuted under the adopted observed-only definition |

The source's unknown week-12 input remains visible as baseline context. The first plan supplies a conditional
completion; it does not turn the hypothetical observation into a posted result. An unknown input is not
unavailable. A wrong definition edition or application scope blocks attribution rather than proving that
the clinical design is impossible.

## Hand over the decision list

| Decision | Evidence and computed consequences | Status |
|---|---|---|
| PS upper limit | Both 0–2 and 0–3 fit the fixed brief; their consequences for ECOG 3 differ | Chosen 0–2 in one request; revised to 0–3 in a separate request |
| Routine assessment date | Explicit routine window permits days 35–49; day 28 belongs to a separate actual event | Choose the routine plan; preserve event roles |
| Analysis-population correspondence | 40 outside EFQ under the declared subset; application initially unresolved | Resolve the binding before using it to reject a plan |
| Endpoint inputs | Adopted edition requires observed baseline and week 12 | Choose an observed assessment plan or explicitly adopt a different definition |

The assistant keeps source facts, hypothetical premises, exact conditional consequences and human choices
side by side. No clinical choice is made by a survivor count, and no source record is edited.

## Execute and verify

Every `*-request.json` runs unchanged through `trialledger reason --request FILE` or MCP `reason`.
Each matching `*-result.json` is the complete public CLI response. For example:

```sh
trialledger reason --request examples/interpretations/draft-choices-request.json
trialledger reason --request examples/interpretations/population-unresolved-request.json
```

`build_examples.py` constructs these invented premises and executes the public CLI to rebuild the saved
responses. Use `--requests-only` to prepare the requests without running them. The authored tests in
`tests/test_interpretations_entrypoints.py` compare CLI and complete stdio MCP responses, enforce the named
clinical distinctions, perturb scope/edition/logic/selection, verify proposal isolation and preserve report
bytes. These examples demonstrate composition; they are not independent clinical validation of the rules.
