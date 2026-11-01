# Design — add-design-synthesis

## Context

Proposed 2026-11-01, after `add-agent-operation`, on which it builds. The landscape record supplies the corpus;
the scoped-assertion layer supplies the representation and entailment; this change adds the design variables,
the rule tables and the solver.

## Decisions

1. **The brief.** A JSON object: the investigational intervention (drug, class or modality), the indication, the
   phase, the question the trial is to answer (efficacy against a comparator, safety and dose, an outcome in a
   named population), and optional priorities and constraints (a comparator required, a population excluded, a
   duration limit). The agent writes it from the user's request; TrialLedger refuses an empty or unresolvable
   brief by name.

2. **Design variables are typed and closed.** Each variable has a domain from the existing vocabularies
   (setting coordinates, the assertion layer's predicates and value kinds, the endpoint classes, the time-point
   roles) and a value with a status: known when a definition or deduction fixes it, interpolated when a sourced
   design rule or a corpus standard sets it as a default the rules may build on, proposed when it is an
   admissible alternative the user's choice must settle.

3. **Definitions.** Identities and memberships: the drug's class and targets (RxClass, RxNorm, the crosswalk),
   the indication's place in the condition hierarchy, a phase's purpose. Warrant: the source and its release.

4. **Deductions.** The brief and every fixed variable are scoped assertions; definitional rules (reproductive
   capacity follows from sex and age as the population states them; a first-line setting entails no prior
   therapy for advanced disease; a pediatric population bounds age) are assertions too, and the entailment
   procedure derives each consequence with the premises it used. A contradiction among them is INCONSISTENT, named
   before any design is written.

5. **Sourced design rules.** Conditional rules with an applicability condition and a citation (a regulatory or
   methodological source, with its version), recorded in `provenance.py` as every rule is: e.g. a randomized
   comparison names its comparator; a time-to-event primary endpoint needs its assessment schedule. They set
   defaults (interpolated), never facts.

6. **Corpus observations.** From the landscape run: a criterion at the standard tier among comparable trials is
   inherited, citing the trials and the tier; a mechanism-linked exclusion of the drug's class is inherited,
   citing the signal; the primary endpoint class and time point most comparable trials use are proposed with
   their frequency; occupancy and near misses position the design; comparable posted results give effect-size
   and event-rate inputs, like for like only. Each carries the statistic it rests on and its silence bounds.

7. **Choice rules.** Where several designs are admissible, the user's priorities choose (stated in the brief or
   answered as closed questions); the result records that the choice was the user's.

8. **The solver.** Exact and deterministic over the typed variables (the entailment procedure's finite-domain
   enumeration, extended to design variables), with a declared resource bound returning UNDETERMINED rather than
   a guess. Output: the admissible designs, the one the priorities select, and the open questions.

9. **The output.** `design.json` (the brief, every variable with value, status and warrant, the eligibility as
   scoped assertions and as text, the endpoint and schedule tables, the sample-size inputs, the open questions)
   and `design.xlsx` (a synopsis sheet, eligibility, endpoints, schedule, warrants), in the same run folder as the
   landscape, delivered by the same entry point.

## Risks / Trade-offs

- [Thin comparable results for sample size] → inputs named with their basis and count; none invented; the
  publication parser (designed in the theory doc) raises coverage.
- [Indications outside the banks' coverage] → the type matrix's manifest marks them; corpus rules there return
  fewer defaults and more open questions, said so in the record.
