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

9. **Closing the remainder ("Jeeves mode", the founder's term, from his ModelAtlas project).** After the
   definitions, deductions, design rules and corpus observations have narrowed the space, what remains is a set
   of admissible designs differing on some variables. TrialLedger does not leave the user a list of open
   questions to work through: it surfaces the remainder and suggests the decision that closes it most
   effectively, by symbolic logic, as ModelAtlas's refinement guidance does (`build_refinement_guidance`):
   - **Which question.** Each open variable is scored by how much its answer would close: how evenly its values
     split the remaining admissible designs (the balance `k * (n - k)`, zero for a value every design shares,
     which closes nothing), plus what each answer would fix downstream through entailment (a choice of setting
     that settles the line, the prior-therapy criteria and the comparator closes more than one that settles
     only itself). The question asked first is the one whose answer leaves the fewest admissible designs in the
     worst case; ties break on a declared order, deterministically.
   - **Which answer to suggest.** Among that question's options, the suggestion is the one with the strongest
     warrant (a deduction over a design rule over a corpus standard over a corpus majority), and, among equally
     warranted options, the one that closes the most of the remaining space. The suggestion is shown with its
     warrant and with what accepting it would close ("this also fixes the comparator and three criteria"); the
     user accepts it, picks another option, or answers freely, and whichever they choose is recorded as theirs.
   - **The form.** Questions are declarative templates with typed slots and a stable `question_id`, never
     phrased ad hoc, so the agent can switch on the id; every option carries the brief amendment it applies, so
     the agent merges it and re-runs `design` mechanically until nothing is open. One question at a time, the
     highest-value first; "accept every suggestion" closes the design in one step, every acceptance recorded.

10. **The output.** `design.json` (the brief, every variable with value, status and warrant, the eligibility as
   scoped assertions and as text, the endpoint and schedule tables, the sample-size inputs, the open questions)
   and `design.xlsx` (a synopsis sheet, eligibility, endpoints, schedule, warrants), in the same run folder as the
   landscape, delivered by the same entry point.

## Risks / Trade-offs

- [Thin comparable results for sample size] → inputs named with their basis and count; none invented; the
  publication parser (designed in the theory doc) raises coverage.
- [Indications outside the banks' coverage] → the type matrix's manifest marks them; corpus rules there return
  fewer defaults and more open questions, said so in the record.
