# Questions that reveal what the system can do

TrialLedger helps a person move from scattered trial evidence to a smaller, explicit set of design choices.
The examples below show why exact reasoning and useful interpretation belong together. Each names the
available evidence, the extra premise it needs, what the program computes and the decision left to the person.

## “The joint table is missing. Can we still know who must overlap?”

A development scientist wants to compare safety and quality-of-life coverage in IPASS. One table describes
607 of 609 gefitinib participants as safety-evaluable; another describes 590 as QoL-evaluable. Neither gives
the cross-tabulation. After explicitly binding both subsets to the same treatment cohort, the existing
reasoning operation bounds the number in **both** populations at **588–590**. For the comparator, the
corresponding counts 589 and 561 among 608 give **542–561** in both.

The first bound has a plain explanation: only two of the 609 people are outside the stated safety subset,
so at most two of the 590 QoL participants can be outside it. The program exposes that constraint while
retaining the population correspondence it depends on.

The program can therefore expose a narrow joint bound even without participant-level data. The binding is
an explicit interpretation in this exploration and keeps interpolated standing. The exact overlap,
individual identities and reasons for nonmembership remain open. Matching arm names alone does not supply
the binding.

**What this communicates:** information can reside in the relationships among reported values. A missing
table leaves a bounded question, rather than an invitation to invent the missing cells.

Executed source-bound example: [request](../examples/source-workflows/ipass-analysis-overlap-request.json)
and [complete result](../examples/source-workflows/ipass-analysis-overlap-result.json), using the retained
[IPASS development record](../tests/fixtures/ipass-registry.md).

**The next clinical question:** “Do these tables really refer to the same cohort and assessment population,
and what coverage should our new endpoint require?” The arithmetic does not choose that requirement.

## “PS 2 appears among both accepted and rejected people. Is the record impossible?”

Consider the **invented** teaching study in the README: 40 randomized participants have ECOG 2, and a
screening log records an eligibility-attributed rejection of a person at ECOG 2 without their other attributes.
These observations can coexist. A candidate explanation that eligibility consists solely of ECOG ≤2 cannot
explain that rejection under the stated attribution. Other criteria could distinguish accepted and rejected
people, but the partial rejected profile does not tell us which criterion did so.

The same study reports 180 never smokers among 200 randomized participants. Their overlap with ECOG 2 must
be **20–40**, under the stated population binding. An eligibility interpretation excluding every person in
that joint profile conflicts with a zero-exception eligibility bridge. Allow 20 exceptions and that guarantee
disappears; allow only 19 and at least one eligible joint-profile witness remains.

The executable session checks all of this alongside cohort counts, age summaries, analysis coverage,
treatment sequence, combination ingredients, class relations and endpoint inputs. **Nine of twelve declared
designs are ruled out.** Three remain, differing on PS cutoff or marker selection. Neither surviving a check
nor explaining one rejection makes a marker requirement a source fact.

**What this communicates:** symbolic reasoning can combine positive and negative evidence without flattening
either. The absent rejection reason remains a precise open question, while the supplied observations still
eliminate incompatible explanations.

Executed invented example: [session](../examples/partial-evidence/README.md),
[request](../examples/partial-evidence/design-request.json) and
[complete result](../examples/partial-evidence/design-result.json).

**The next clinical question:** “Which additional restriction do we actually intend?” The answer is a human
choice supported by further evidence, not a requirement manufactured from a survivor count.

## “Does the early scan break the schedule?”

The **invented** continuing session gives a first scheduled routine assessment window of days 35–49 from
randomization, plus a separately identified actual unscheduled scan on day 28. Proposed routine visits at
day 42 and at the inclusive day-49 boundary fit. A proposal that day 28 is the routine first visit conflicts
with the fixed routine window. Keeping day 28 as the separate unscheduled event is compatible.

A nontechnical conversation can carry a more subtle distinction too: interpreting real wording “every
42 ±7 days from randomization” as that first window remains a reading. Under that reading, 35–49 is exact.
The program can retain another reading without giving up exact checks within either frame. A planned
schedule never establishes that a visit actually happened.

**What this communicates:** disagreement between numbers becomes informative only after the events and
roles are bound. The system can identify a false contradiction as well as a real one.

Executed invented example: [request](../examples/interpretations/assessment-roles-request.json) and
[complete result](../examples/interpretations/assessment-roles-result.json).

**The next clinical question:** “Are we choosing the routine schedule, describing an exception, or changing
the meaning of the source wording?” Those are different decisions.

## “Can one unresolved detail coexist with a useful answer?”

The **invented** population example reports 200 in an ITT parent and 160 in an EFQ subset. The conditional
calculation retains **40 outside EFQ**. If the cohort correspondence is unresolved, the program keeps that
number and the proposed interpretations visible, while withholding an exclusion that depends on the binding.
Resolve the binding and the candidate “everyone was in EFQ” is refuted under it. An independently fixed adult
requirement remains settled in both requests.

The endpoint example makes the same distinction operational. An adopted definition requires observed
baseline and week-12 measurements. The source leaves week 12 unknown. A hypothetical plan supplying an
observed week-12 input completes the definition conditionally. Supplying only an imputed value leaves the
observed-input question open. Explicitly making the required observed input unavailable conflicts with the
adopted definition. The hypothetical completion never becomes posted data.

**What this communicates:** uncertainty has a location and dependencies. The system can keep what is
resolved, explore what depends on an assumption, and ask about the remaining distinction without discarding
the whole analysis or silently filling the gap.

Executed invented examples: [unresolved population](../examples/interpretations/population-unresolved-result.json),
[resolved population](../examples/interpretations/population-resolved-result.json) and
[endpoint inputs](../examples/interpretations/endpoint-inputs-result.json). Matching requests are beside them.

**The next clinical question:** “Should we obtain the observation, change the adopted endpoint definition,
or leave this plan open?” The program shows the consequences of those options; it does not choose for us.

## Use the examples in a real conversation

The [retained-source walkthrough](../examples/source-bridge/) connects these questions to actual NIH input:
direct structured age bounds, exact baseline cells feeding a hypothetical overlap calculation, and rival
readings of the schedule passage. Source anchors establish the text/cell and snapshot; clinical meaning
remains the reading's premise. Revisions rerun the existing reasoner, preserving the original evidence.

Start with the person's task: reference evidence, a draft restriction, a comparison, or a choice that needs
clarification. Gather the relevant record and keep its exact passages. Show material premises together in
ordinary clinical words. Run the appropriate operation and answer the question with its deciding source,
premise or rule. Use a named hypothetical frame when the person would benefit from examining a reading
before accepting it. Keep rivals and contradictions available.

The remaining capacities fit that same conversation. A selected comparison set can show how often a
restriction is documented, how much registry silence leaves unresolved, which declared design regions are
occupied and which pairs differ on one represented feature. These are computed descriptions, not permission
to copy a criterion or proof of clinical unmet need. Drug terminology supplies source-backed identity and
class evidence; an approximate match remains a candidate. Source consistency checks identify disagreements
without choosing which source value to replace. A linked paper supplies a place to seek evidence, not a
finding until its relevant content and bindings are read.

End with the decision list: the choice, its evidence, computed consequences and whether it is open or chosen.
The source record, hypothetical interpretations and human decisions remain distinguishable throughout.
