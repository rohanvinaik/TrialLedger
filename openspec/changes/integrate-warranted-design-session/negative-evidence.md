# Negative evidence constrains candidate explanations

This applies the founder's Negative Specification framework to the current clinical workflow. The complete
reference was read at `/Users/rohanvinaik/tools/Detective/docs/theory/NEGATIVE_SPECIFICATION.md`, resolved from
the supplied Finder alias. Its sections 2, 5, 9 and 11.12 supply the two-sign, admissibility and propagation
obligations. This document does not import a code-specific complexity or completeness theorem into trial
design, or claim a measured learning rate.

## Two signs over a scoped clinical rule

Let E be a candidate eligibility rule at a particular study, population, arm, assessment time and version.
Let P describe the participant information actually available.

| Observation, under its warranted attribution | Constraint | What remains open |
|---|---|---|
| An eligible participant with P | There exists a participant satisfying P and E | E need not admit every P participant. Enrollment alone does not establish eligibility. |
| A participant with P rejected for ineligibility | There exists a participant satisfying P and not E | The responsible inclusion or exclusion criterion may be unknown. |
| Both observations for the same partial P and applicable rule | E cannot be explained by P alone | Other attributes, alternatives and qualifiers can distinguish the participants. |
| A documented eligibility exception with unknown profile | At least one participant failed the applicable entry rule | No particular clinical subgroup contains that person without further evidence. |
| A protocol-related withdrawal | Retain the reported failure, group, period and attribution | The failed requirement may concern entry, treatment or assessment; those targets are not interchangeable. |

An exact near-miss contrast localizes a distinguishing feature only when the represented comparison and
attribution warrant that localization. Broader negative observations still constrain explanations; they do
not need to be discarded until a one-feature contrast is available. A failed efficacy objective, analysis
exclusion and eligibility rejection also address different predicates.

For example, accepted and rejected ECOG 2 participants jointly rule out both complete explanations
“ECOG 2 always excludes” and “ECOG at most 2 is the only requirement.” An additional requirement Q could
explain their different outcomes. The observations establish neither Q's identity nor universal exclusion
of ECOG 2. These are logical examples, not claims about participants in the sampled registry records.

## Source attribution is an information channel

Keep the exact reason category and count as recorded. A separate binding states which requirement the
failure concerns, when it applied, its population correspondence and its evidential standing. The supplied
binding is a premise, not source verification performed by the solver. Proposed interpretations remain
available for conditional calculation without entering the accepted fixed floor.

The sampled IM-UNITI record lists “Protocol Violation” during maintenance without identifying a violated
entry criterion. That label must remain available as reported negative context. It cannot alone yield an
eligibility-exception floor. ICH E3 Q&A question 7 likewise describes protocol-related withdrawals more
broadly than entry ineligibility; application of a reference definition to this source must itself be
bound rather than assumed. [ICH E3 Q&A](https://www.hhs.gov/guidance/sites/default/files/hhs-guidance-documents/FDA/E3-Structure-and-Content-of-Clinical-Study-Reports---Questions-and-Answers-%28R1%29.pdf)

The planned public exception bridge will retain a set of possible failure targets, rather than force a
broad category into one label. The initial vocabulary will distinguish entry eligibility, treatment
adherence, assessment adherence and an explicit other-protocol-requirement residual. A broad failure can
leave every target possible. The residual prevents that vocabulary from silently claiming that the first
three exhaust protocol requirements. Source wording remains unchanged beside these supplied meanings.

An attribution may narrow the set only with its own evidence, scope, standing and dependencies. A
maintenance-period entry can describe an entry violation discovered late; recording period alone cannot
remove entry eligibility. Only an applicable, accepted attribution to entry eligibility alone can supply
an eligibility-exception floor for the bound count. A proposed singleton remains conditional. An empty
intersection of accepted target attributions is an attribution conflict, never a zero-exception result.
Unknown or broader targets retain their count and support without supplying an eligibility floor.

This target-set handoff is planned, not yet integrated into the public bridge. The existing participant
witness engine already computes both accepted and rejected directions; it is not a new solver.

The vendored API schema's `DropWithdraw.type` is a free string. Its participant-flow metadata defines
recording fields, not a label-to-entry-eligibility rule. Reading IPASS's eligibility-worded category as an
entry failure therefore remains a clinical interpretation. The floor-one/zero-cap conflict is conditional
on that reading and its scope; it is not a registry-only contradiction. A proposed reading supplies only
a hypothetical consequence; acceptance supplies a premise, not a registry-defined meaning.

## Ask which evidence would distinguish the remaining candidates

After the exception bridge, add a bounded evidence-request calculation over the declared surviving
candidate rules and represented participant variables. Reuse `eligibility_witness` for each hypothetical
profile and sign. Numeric enumeration uses exact comparison cells from the represented thresholds, not
an arbitrary clinical grid. Preserve explicit domains, units, scope, open cells and computation limits.
Unsupported domains and incomplete enumeration cannot produce a claim of complete separation.

For example, compare a candidate requiring adulthood and ECOG at most 2 with one additionally requiring
a marker. An eligibility rejection of an adult, marker-negative ECOG 2 participant can distinguish these
declared complete rules: the first has no way to explain that rejection, while the second does. An
accepted eligible example of that profile distinguishes them in the opposite direction. If the marker is
unknown, a positive example fits both candidates, but a negative example can still eliminate the first:
the second can explain rejection by an unspecified marker value. Evaluate each partial profile and sign
against each candidate rather than demanding a complete patient description. These are invented
investigations, not observed patients.

Report the hypothetical profile, sign, affected candidates, deciding proofs, scope and witness/exception
conditions as an evidence request. Do not add it to observations, count it as evidence, or claim that the
clinician should choose the resulting design. Empty candidate survival is a conflict; one survivor is
permitted and is not proof that the declared family contains the historical protocol. Do not require two
survivors as a runtime admissibility rule.

Prefer the least-specified profiles that still separate candidates within the declared representation,
with deterministic ordering and explicit search coverage. Sparsity is a structural criterion, not a claim
about the likelihood of finding a record. Mark every request's accepted/rejected sign and its suggested
evidence source; eligibility-attributed screening or adjudication logs are a possible place to look for
rejections. Do not assert that such records exist or that the registry can never contain them. Cap requests
per survivor pair and in aggregate, and enforce an output-byte bound. Distinguish output truncation from
incomplete search and from a completed search finding no separator.

Corpus `near_misses` compares trials differing in one represented feature. A participant-level positive /
negative comparison, if represented, is a contrast pair. These are different objects. A missing trial,
unposted rejection or absent corpus feature is neither kind of negative participant evidence.

## Propagate the observed distinction

The path to verify is source selection → scoped meaning/target binding → count bound or rejected witness
→ candidate compatibility → common consequence → user decision/evidence task. Every handoff retains the
observed sign, affected rule, support and unresolved alternatives. A computed difference with no consumer
is unfinished integration.

Use the existing `eligibility_witness` and `design_bounds` negative direction for conditional participant
reasoning; do not replace them with a manual inference. Keep raw protocol-related categories as attributed
evidence when no supported operation settles their narrower meaning. Accepted source-derived constraints
and invented investigation hypotheses remain distinguishable. A solver's own conclusion cannot be fed
back as independent source evidence validating its proposed interpretation. Preserve valid derived
information with its computation origin and complete dependencies; prohibit its promotion to an
independent observation or source-stated criterion. Origin-based admission in the new managed path must
refuse a prior design survivor offered as a known source witness. Legacy caller-declared premises cannot
authenticate arbitrary claims about their origin, and this work must not promise that they can.

The acceptance obligations include mixed accepted/rejected profiles, a broader protocol failure with a
known count but unknown eligibility attribution, wrong arm/time/version, incomplete candidate coverage,
universal-exclusion overreach and unchanged independent source facts after binding retraction. Every
negative-sign elimination must reach the candidate decision, elimination standing, common consequence
where relevant, classified metadata and decision/evidence-task handoff. No absence of a posted failure is
treated as proof of compliance.

Clinician-facing explanations use who was eligible and who was turned away for eligibility. Two-sign,
censor and teaching-set vocabulary belongs in theory and contributor material. Enrollment alone still
requires an explicit eligibility bridge and exception allowance before it serves as a positive witness.

## Separate follow-on: sponsor screening evidence

Typed screening-log observations could retain user-supplied rejection reasons, partial profiles,
population/time scope and provenance outside the registry. This needs its own input and admission
contract, including distinct-person counts and the same attribution and uncertainty rules. It is a
separate change, not an unimplemented capability advertised by this bridge.
