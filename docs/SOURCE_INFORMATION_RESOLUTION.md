# Bringing more source information into symbolic reasoning

This investigation applies TrialLedger's [theory](THEORY_OF_THE_CASE.md) to a retained IPASS record,
the public reasoning operations and SymbolicSpellCheck. Its binding and competing-reading recommendations
now have an explicit layer-two representation in the [interpretation workflow](../examples/interpretations/).
The [retained-source bridge](../examples/source-bridge/) now compiles named structured rules and anchors
proposed readings to exact NIH values/passages. General clinical text compilation, clinical text repair
and external adapters remain proposed integrations.

The [executable packet](../examples/source-workflows/) separates source data, assistant-authored
interpretations and computed responses. All clinical bindings here are exploration premises, **not
interpretations confirmed by a clinical user**. Conditional demonstrations must not be presented as
confirmed clinical findings. The source is the unchanged [development fixture](../tests/fixtures/ipass-registry.md),
fetched on 2026-11-03; this investigation did not refresh it from the live registry.

## What a user can ask today

### “Did IPASS allow performance status 2? What cutoff should we choose?”

**From the record:** eligibility gives no performance-status cutoff. The baseline table reports 126
participants at WHO PS 2 and 1,140 never smokers, with a total denominator of 1,217. The scale is WHO PS.

**Computed:** the saved performance-status request rules out hypothetical upper cutoffs 0 and 1 under its
explicit participation-to-eligibility bridge. Cutoffs 2, 3, 4 and an unrestricted candidate remain.
“Must the cutoff be ≤2?” is `UNDETERMINED`. The joint-count request produces **[49,126]** for WHO PS 2
and never smoking under its explicit common-universe premise. A candidate excluding the whole joint
profile is ruled out with at most 48 eligibility exceptions; allowing 49 removes that guarantee.
The common consequence remains undetermined because an unrestricted candidate is included.

**Still unresolved:** the exact criterion, assessment-time alignment, eligibility exceptions and any
mapping to ECOG. The record's flow table even lists one randomized participant under “Eligibility criteria
not fulfilled”; that does not identify their PS or establish a complete upper bound on all deviations.
Blanket compliance is therefore an exploration premise, not a copied registry fact.

**Decision list:** the new trial's PS scale and range remain the person's choice. A future binding
adapter should preserve the baseline measure, category, group, denominator and source digest together,
and ask only about the eligibility bridge that the source cannot establish. The existing solver can
already consume that representation.

### “Why are the safety and quality-of-life denominators smaller?”

**From the record:** posted PFS uses ITT denominators 609 and 608. Posted outcome 3 describes EFS as a
subset of ITT receiving at least one dose and supplies denominators 607 and 589. Outcome 13 describes
EFQ as an ITT subset with evaluable baseline and at least one evaluable post-baseline QoL assessment;
its denominators are 590 and 561.

**Computed:** with explicit correspondence of the treatment cohorts across these outcome-local groups,
the population operator returns:

| Treatment cohort | Outside the stated EFS subset | Outside the stated EFQ subset |
|---|---:|---:|
| Gefitinib, ITT 609 | 2 | 19 |
| Carboplatin/paclitaxel, ITT 608 | 19 | 47 |

These saved results are interpolated because the exploration supplies the cross-outcome bindings. Repeated
`OG000`/`OG001` identifiers or matching titles alone do not certify those bindings.

The same bindings also let the existing overlap operator recover information that neither analysis table
states: **588–590** gefitinib participants and **542–561** comparator participants must belong to both
EFS and EFQ. No independence assumption or participant-level cross-tabulation is needed. The saved
`ipass-analysis-overlap` request computes these bounds separately within the two ITT cohorts.

**Still unresolved:** each person's reason for exclusion, whether absent assessments were never performed
or unevaluable, and the exact overlap between EFS and EFQ. Subset arithmetic alone cannot supply those causes.
The structured enrollment field also says 1,329, while the flow narrative reports 112 screening failures
out of 1,329 and the randomized groups total 1,217. Substituting 1,329 as the randomized denominator would
collapse different populations. Preserve each number's role and investigate the encoding instead of
changing the enrollment field to make the totals equal.

**Decision list:** define the new trial's analysis populations and required assessments explicitly.
The interpretation binding record now retains explicit study/population/arm/time/edition and source identity,
with effective subset, same-universe and partition applications to today's population, partition and overlap
operators. A future source adapter must still settle the membership definitions and clinical correspondences.
Neither cohort identity nor population equality should be inferred from
equal counts. Cross-signal composition needs an explicit shared binding, not an automatic join.

### “Can we reuse the comparator's assessment schedule and endpoint definition?”

**From the record:** the primary-outcome time frame explicitly describes baseline assessments and then
assessments every 42 ±7 days from randomization. This particular field contains a schedule. Other time-frame
fields may contain only a duration. The response definition separately requires confirmation at least
28 days after the initial response.

**Computed:** interpreting the first post-baseline scheduled assessment as an inclusive randomization-relative
window produces **[35,49] days** through the temporal operator. The companion request leaves the reading
unresolved: its `calculation_code` remains `consistent`, but its usable `code` becomes `unresolved`, with a
binding blocker. The engine does not certify the assistant's reading merely because it can solve it.

**Still unresolved:** actual attendance, the meaning of subsequent visit tolerances, the adopted RECIST
edition and whether a different assessment belongs to the confirmation rule. Combining the 42-day schedule
and 28-day confirmation interval requires named events and their actual relation, not subtraction of two
numbers found nearby.

The QoL description adds another useful case: improvement needs two qualifying visits at least 21 days
apart and no intervening visit with a specified decline. EFQ membership requires only baseline plus one
post-baseline assessment. Those are different predicates. The current dependency operator can represent
named required inputs and alternative input sets; it does not by itself evaluate an arbitrary longitudinal
“no intervening decline” predicate. That requires a scoped sequence definition, measured visits and a
completeness warrant for the intervening interval. An unreported intervening visit cannot become “none.”

**Decision list:** settle the endpoint edition, confirmation rule and assessment plan. A bounded schedule
compiler and versioned endpoint definitions could then feed the temporal and dependency operations, while
leaving unsupported longitudinal conditions open.

### “Can you fix the registry's encoding and spelling?”

There are several distinct operations with different warrants:

| Operation | Concrete example | What is warranted now / next |
|---|---|---|
| Source-defined interpretation of a blank | An event-level at-risk count is blank and its table group provides the default | Existing `checks.at_risk` returns the source-defined group denominator, retaining its origin. A blank does not become zero. |
| Detect an internal conflict | `hasResults` disagrees with presence of `resultsFirstSubmitDate` | Existing approved check reports `conflict`. The packet demonstrates this on a **synthetically corrupted copy**, not an observed IPASS error. |
| Recompute a defined redundant value | The same flag, with the defining date retained as the anchored input | A future effective-value view can recompute the flag under the pinned metadata rule. This warrants the defined projection; it does not independently validate the date. |
| Recover a misspelled surface | IPASS writes `thromboctyopenia` in the description of its thrombocytopenia outcome | The live SymbolicSpellCheck call applied `thrombocytopenia` and retained the exact edit. TrialLedger still needs a typed binding to that outcome before using the term's clinical meaning. |
| Reconcile materially different statements | Eligibility excludes prior chemotherapy; recruitment text separately exempts non-platinum adjuvant chemotherapy | Preserve both passages and their provenance. A source/version/scope investigation is needed before one interpretation can govern eligibility. |

The current `checks.run_checks` → `landscape.registry_check_reading` path detects inconsistencies and
retains inputs; it does **not** choose or apply a replacement. This is a foundation for correction.
The synthetic flag demonstration also verifies that checking leaves its input unchanged.

For a conflicting count equation, consistency alone cannot pick a repair: if two supposedly disjoint
counts 60 and 50 exceed total 100, changing either count, changing the total or correcting the population
binding could all remove the conflict. A minimal edit is not evidence of which value was intended.

## What transfers from SymbolicSpellCheck

The inspected MCP wrapper delegates to `gse.nlp.heal.suggest`. Its reusable mechanisms are exact decoded
source text, half-open Unicode spans, protected surfaces, named decisions, resource/policy identities,
and an edit ledger. `apply_edits` checks alignment, refuses overlapping edits and preserves unaffected
slices. These mechanisms fit TrialLedger's source-preservation requirement.

Three live MCP probes are retained in the packet:

- The real IPASS typo was corrected from `thromboctyopenia` to `thrombocytopenia`; grammatical context was
  available for this probe.
- An invented clinical string changed only `recieve` to `receive`, preserving the drug, negations,
  decimal, unit, scale and identifiers. Its context was `unread: GrammaticalDefinitionError` and the result
  was `partial`.
- An invented valid-word string containing `now`, `not`, `5 mg` and `0.5 mg` was unchanged. Its grammar
  context was also unread. Lexical validity cannot determine whether an author intended a different word
  or dose.

The clinical probes expose a concrete integration prerequisite: the sentence manifests split the decimal
`0.5` after its dot, although the corrected text preserves the decimal. The inspected `_manifest` function
uses punctuation as boundaries. TrialLedger should protect numeric spans before consuming sentence boundaries;
these manifests should not delimit clinical assertions as they stand. No GSE files were changed here.

Spelling recovery supplies candidate surfaces. Admitting a clinical proposition needs the additional
warrants for entity identity, relation, polarity, force, scope and time. The current drug-identity code
already provides a useful precedent: `identity_evidence` retains a lookup under another surface as
`lookup_candidate`, rather than certifying it as an exact identity of the recorded name.

## External sources that close specific gaps

These are proposed adapters, not newly installed integrations. The API capabilities below were checked
against primary documentation on 2026-11-03.

| Source | Information it can contribute | Admission rule |
|---|---|---|
| [RxNorm exact lookup](https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.findRxcuiByString.html) and [typed related concepts](https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getRelatedByType.html) | Canonical identities, term types and ingredient/product relations | Retain the lookup mode, relation path and release. Exact lookup can be ambiguous; normalized lookup can ignore salt forms. [Approximate results](https://lhncbc.nlm.nih.gov/RxNav/APIs/api-RxNorm.getApproximateMatch.html) generate candidates and do not prove identity. |
| [MeSH RDF](https://id.nlm.nih.gov/mesh/) and [concept structure](https://www.nlm.nih.gov/mesh/concept_structure.html) | Identifiers, terms and typed concept relations for condition binding | Preserve the relation's semantics and edition. Terms within one concept are synonymous; terms merely sharing a descriptor need not be. Search equivalence cannot become clinical identity. |
| [NCI EVS](https://www.cancer.gov/about-nci/organization/cbiit/data-standards/vocabulary) and its [official API clients](https://github.com/NCIEVS/evsrestapi-client-SDK) | Coded concepts, definitions, descendants, mappings and replacement-concept candidates | Keep terminology, concept status, edition and relation type. An inactive-code replacement must be checked for split/merge and scope before reuse. |
| [UCUM specification](https://ucum.org/ucum) and [NLM UCUM service](https://ucum.nlm.nih.gov/ucum-service.html) | Unit validation and defined conversions | Bind the measured quantity and unit dialect first. The service reports up to eight significant digits, so its numeric output alone cannot certify an exact threshold conversion. Analyte-dependent conversions need explicit additional premises. |
| [PMC OAI-PMH](https://pmc.ncbi.nlm.nih.gov/tools/oai/) | Reusable full-text JATS where rights permit; methods, definitions and cohort descriptions absent from the registry | Bind study, document version, section, population and time; retain disagreements. A registry citation is a locator, not a read finding. The older [PMC OA Web Service](https://pmc.ncbi.nlm.nih.gov/tools/oa-service/) was discontinued in August 2026. |

An adapter should request evidence for a named unresolved premise. For example, a missing endpoint edition
calls for the comparator's protocol or methods; a drug spelling candidate calls for identity and product
evidence. An ontology cannot supply an unreported eligibility criterion or establish that an assessment
actually occurred.

## Proposed implementation boundary

The interpretation increment connects explicitly supplied source-bound representations to the reasoning
already built. Further source adapters and correction functions should share this contract:

1. **Locate and type:** retain source digest/address/span and the quantity, population, entity or statement
   role. Preserve unknowns and alternatives.
2. **Generate candidates:** use source-defined transforms, protected spelling recovery, explicit reference
   relations or bounded grammars. Candidate generation does not assign truth.
3. **Check warrants:** evaluate type, scope, version, negation, units, temporal anchor and defining constraints.
   Enumerate admissible repairs only under a declared repair model and anchored premises. A unique survivor
   is unique within that model; its standing includes those premises and the model's coverage assumption.
4. **Resolve or abstain:** proposed codes are `unchanged`, `derived`, `corrected_overlay`, `ambiguous`,
   `conflict`, `insufficient_evidence` and `refused`. A proposal never becomes a known premise merely because
   it passed a schema or received a high spelling rank.
5. **Compose and present:** supply admitted typed facts and bindings to today's signals and design bounds.
   Preserve original and effective values side by side, the deciding rule and all dependent results.
   A revised source or withdrawn bridge invalidates the dependent view and requires recomputation.

My proposed order is **population/denominator bindings**, then **source-defined effective values and
correction ledgers**, then **protected lexical/quantity recovery and bounded schedule/definition compilation**.
The first turns the demonstrated coverage questions into reusable workflows. The second permits a narrowly
warranted correction without erasing evidence. The third expands the clinical text that can enter those
workflows, with each unsupported construction still visible.

Acceptance should follow each signal through the real record → binding → reasoning request → candidate
decision → decision-list path. Required negative cases include cross-module ID collisions, equal counts
with different populations, missing versus zero, estimated versus actual dates, valid-word errors, decimals,
unit case, polarity, exceptions, competing repairs, stale references and unavailable context. Measure
identified, abstained and wrong separately for each correction class. The existing teaching case checks
reasoning composition; it does not establish automatic encoding accuracy.
