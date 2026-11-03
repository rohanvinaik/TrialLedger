# Phase4 Parkinson: ask for the evidence that would separate explanations

The predeclared question was which entry-participant profiles, with an accepted or rejected sign, would distinguish competing eligibility explanations and where that evidence could be sought. The levodopa/ParkinsonDisease/PHASE4/COMPLETED query returned24 studies; seed6261498521908556500 selected NCT04821830, NCT00219284 and NCT01494532 before content reading. The complete pool was acquired and no study replaced. Whole selected clinical protocol units and full flow/baseline modules were read. Source and query receipts retain complete bodies locally; source-assertion requests retain complete required snapshots.

## What the records actually say

NCT00219284 has structured ages30–85, but its eligibility prose specifies30–80inclusive with81–85 allowed if the principal investigator considers the participant otherwise in goodhealth. It explicitly says other protocol-defined criteria apply. Its treatment-phase ProtocolViolation withdrawals9/5 do not identify an entry-eligibility failure or participant profile. Neither a mean baseline age nor a withdrawal label establishes the accepted/rejected cases needed below.

NCT04821830 concerns previously untreated or less-than4weeks-treated early Parkinson disease, structured ages45–90. Its description calls the work observational while the registry design field says interventional Phase4. NCT01494532 concerns advanced disease with stable L-dopa for at least4weeks before screening, age≥30, and a separate dopamine-agonist washout before randomization. Those settings and clocks are not interchangeable. The records also distinguish acute/chronic measurement states, maintenance week4 versus study week17, physician-discretion treatment and tolerability-driven changes. `source-reading.md` preserves the details. This walkthrough does not resolve those source channels, recommend therapy or validate a new statistical paradigm.

## The declared hypothetical family

These three represented rules are explicitly invented sensitivity inputs inspired by the age wording, not recovered complete protocols or clinician-confirmed readings:

1. `strict80`: age30–80.
2. `conditional85`: age30–85, and either age≤80 or the declared PI-goodhealth predicate holds.
3. `broad85`: age30–85 without that additional predicate.

Their assertions are interpolated assumptions; the question is what could distinguish them **if this declared family were the comparison**. The profile domain is explicitly chosen whole-year ages30–90 and a boolean PI-judgment predicate. It does not certify how any source measures fractional age or operationalizes the investigator's judgment.

No source observations eliminate a candidate. A candidate-only `design_bounds` attempt was correctly refused as empty_design_bounds_inputs; the workflow did not invent a zero-count or accepted witness to force it through. `survival_basis` instead honestly declares the hypothetical family. The evidence-request operation performs its actual consistency prechecks and profiles over that family.

## The useful investigation questions

The accepted/rejected search completes185 profiles and1113 decisions. It finds20 requests and returns4 under the explicit per-pair output cap, retaining16 omitted and output_limit:per_pair. Least-specified rows come first, not a score of clinical importance or availability.

- An **accepted, eligible-at-entry81-year-old** would eliminate the strict80 explanation under an accepted eligibility bridge and count above the exception allowance. This does not require the remaining candidate to be the full protocol.
- An **eligibility-rejected81-year-old** could eliminate broad85 only if broad85 were the complete eligibility rule, the rejection were correctly attributed to eligibility, and the bridge/count assumptions held. The actual registry explicitly omits other criteria, so that completeness premise is currently unavailable. A screen failure for an unrelated criterion would not establish age exclusion.
- An accepted-only search with both age and PI-goodhealth returns a two-attribute request: an accepted81-year-old for whom the declared goodhealth judgment does not hold. Under its named premises that would eliminate conditional85 while accommodating broad85. It is a question to investigate, not a fact about such a person.

Accepted requests point toward participation records bound to entry eligibility; rejected requests point toward screening/adjudication records. The operation does not claim these records exist. The actual ProtocolViolation9/5 labels never become rejected entry observations.

Every returned row has kind hypothetical_evidence_request and observed:false. None carries observation fields count, bridge, basis or status. Complete witness decisions, scope, required premises and where-to-seek text are retained. A future real observation must be separately sourced and submitted with its own standing, scope, bridge and exception accounting.

## Revision and limits

Restrict the investigation to accepted signs and age alone: the age-cap pairs remain separable, but conditional85 versus broad85 becomes not_separated_in_declared_variables. The result names the unsearched PI-goodhealth constraint and restricted signs. That is not proof that the explanations agree clinically; it identifies missing represented information. This revision completes61 profiles/186 decisions, finds5 rows and returns2 with3 explicitly omitted by the per-pair cap.

With a one-profile work budget, the search is incomplete and returns no row, with resource_bound:profiles and search_incomplete pairs. That is a computation task, not evidence that no separator exists. Output truncation and incomplete search remain separate.

## Managed-session wiring and independent source facts

The session embeds candidates through named candidate premises and identity projections, not an untracked parameters list. Their origins stay hypothesis and their effective standing remains proposed/unresolved. Computing hypothetical distinguishing questions over a named family does not promote its truth or generate an observed participant. The focused session domain is ages80–85, with explicit bound128,32profiles and256decisions; it completes20profiles/123decisions. The broader initial reservation was refused by the aggregate session budget, so the question was narrowed rather than the gate bypassed.

A separate historical source-rule premise in the same session entails NCT00219284's age≥30 restriction with known standing. All three standalone source-assertion checks independently entail age≥30 and leave universal age83 undetermined. They answer only the structured age restrictions, not full individual eligibility. Replaying them after the hypothetical search revisions returns identical complete results.

## Verification and handoff

Eight complete requests ran through separate actual CLI and MCP processes, with full parsed-document equality after removing only MCP's tool wrapper. Complete child requests/results, projection origins and dependency graph are retained inside the session pair. The runtime receipt freezes exact package hashes through execution; the local report passes verify. Every effective metadata pointer is checked against its actual result, and none is unclassified.

The final successful pairs were rerun after choosing the whole-year profile domain and narrowing the session reservation. Refused preparatory requests and duplicate wire output stay local outside the portable packet. No production source was edited. See `working-brief.md` for the clinical decision list and named evidence gaps.
