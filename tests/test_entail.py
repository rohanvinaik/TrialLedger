"""Entailment over hand-built scoped assertions (openspec/changes/add-scoped-assertions tasks 3.1 and 3.2; the
design's acceptance table, Decisions 6, 8 and 9). The compiler that builds assertions from text is a later
task (group 2); these assertions are built by hand. Their wording is the spec's, from the auditor pilot of
2026-11-01 ("locally advanced or metastatic NSCLC", "HIV positive with current CD4+ count < 200", "The source
case a person with HIV antiretroviral resistances", "The use of concomitant medication must be stable for 4
weeks"); the plan names no NCT ids for them.

Positive: (A∧B)∨(A∧C) entails A; required(HIV∧Q) entails required HIV; excluded(A∨B) entails NOT A and NOT B
and refutes A; required(stable) under applicability medication_use entails (use → stable), and stability once
use is required; a contradiction is INCONSISTENT with a minimal proof, whatever the query; an interpolated
premise yields an interpolated conclusion, a known one a known conclusion even beside an interpolated
duplicate; measurements compare as typed numbers, boundaries exactly; a cohort-scoped requirement is entailed
in its cohort; the bound abstains; the result is the same whatever the input order; a negative qualified
literal and the exclusion of its positive twin compile identically; a negative literal clashes with its twin
on every value kind; in {a} and not_in {a} on a member set clash; one time stated explicitly and entailed is
one variable.
Negative: neither B nor C from (A∧B)∨(A∧C); excluded(HIV∧CD4<200) does not entail NOT HIV, and a qualified
literal behaves as the conjunction; applicability never entails use; nothing is entailed from a contradiction;
a proposed premise is refused (never a premise, never a contradiction); nothing promotes interpolated to
known; another person's HIV, another unit, another time anchor or an Opaque never stands in; a requirement of
cohort B is out of scope in cohort A and undetermined trial-wide; an unresolved query is unsupported; a
negative qualified literal entails neither NOT base nor its qualifier (the mutant "move a negation" does); a
member subset never entails its superset; another orientation, anchor or bound is another variable; an
assertion whose rule is unresolved is never a premise."""

import dataclasses
import itertools

import pytest

from TrialLedger.assertions import (
    UNRESOLVED_RULE,
    AllOf,
    AnyOf,
    Literal,
    ModelError,
    Not,
    Opaque,
    Predicate,
    Rule,
    Scope,
    ScopedAssertion,
    Subject,
    TemporalScope,
    Value,
)
from TrialLedger.entail import (
    ENTAILED,
    EVERYONE,
    INCONSISTENT,
    OUT_OF_SCOPE,
    REFUTED,
    UNDETERMINED,
    UNSUPPORTED_QUERY,
    Context,
    assertion_formula,
    decide,
    proposition_formula,
    weakest_status,
)

PARTICIPANT = Subject("participant")
HOLDS = Value("boolean")
BY_HAND = Rule("hand_built", "1")


def fact(key: str, kind: str = "condition_status", subject: Subject = PARTICIPANT, **more) -> Literal:
    return Literal(subject, Predicate(kind, key), HOLDS, **more)


def cd4(comparison: str, number: float, unit: str = "cells/uL") -> Literal:
    return Literal(
        PARTICIPANT, Predicate("measurement", "CD4"), Value("quantity", comparison, number=number, unit=unit)
    )


def rule(ident, modality, body, status="known", **more) -> ScopedAssertion:
    fields = {"status": status, "resolution": "resolved", "rule": BY_HAND, **more}
    return ScopedAssertion(ident, f"crit:{ident}", modality, body, **fields)


A, B, C = fact("A"), fact("B"), fact("C")
HIV = fact("HIV")


def test_a_shared_branch_conclusion_is_entailed_and_no_branch_is():
    shared = (rule("r1", "required", AnyOf((AllOf((A, B)), AllOf((A, C))))),)
    entailed = decide(shared, A)
    assert entailed.result == ENTAILED and entailed.proof == ("r1",) and entailed.status == "known"
    assert decide(shared, B).result == UNDETERMINED
    assert decide(shared, C).result == UNDETERMINED
    assert decide(shared, AnyOf((B, C))).result == ENTAILED


def test_locally_advanced_or_metastatic_selects_neither():
    setting = Predicate("disease_attribute", "extent")
    advanced, metastatic = (Literal(PARTICIPANT, setting, Value("enum", "eq", (v,))) for v in ("la", "m"))
    either = (rule("r1", "required", AnyOf((advanced, metastatic))),)
    assert decide(either, metastatic).result == UNDETERMINED
    allowed = Literal(PARTICIPANT, setting, Value("enum", "in", ("la", "m")))
    assert decide(either, allowed).result == ENTAILED
    only = (rule("r1", "required", metastatic),)
    assert decide(only, metastatic).result == ENTAILED
    assert decide(only, advanced).result == REFUTED


def test_a_qualified_exclusion_excludes_only_the_qualified_subset():
    for body in (AllOf((HIV, cd4("lt", 200))), dataclasses.replace(HIV, qualifiers=cd4("lt", 200))):
        qualified = (rule("x1", "excluded", body),)
        assert decide(qualified, Not(HIV)).result == UNDETERMINED
        assert decide(qualified, AnyOf((Not(HIV), cd4("ge", 200)))).result == ENTAILED
        assert decide(qualified, AllOf((HIV, cd4("ge", 200)))).result == UNDETERMINED
        assert decide(qualified, AllOf((HIV, cd4("lt", 200)))).result == REFUTED
    required = (rule("r1", "required", AllOf((HIV, cd4("lt", 200)))),)
    assert decide(required, HIV).result == ENTAILED


def test_an_exclusion_of_alternatives_excludes_each():
    either = (rule("x1", "excluded", AnyOf((A, B))),)
    assert decide(either, Not(A)).result == ENTAILED
    assert decide(either, Not(B)).result == ENTAILED
    assert decide(either, A).result == REFUTED
    both = (rule("x1", "excluded", AllOf((A, B))),)
    assert decide(both, Not(A)).result == UNDETERMINED


def test_applicability_never_entails_its_antecedent():
    use = fact("concomitant", "medication_use")
    stable = fact("concomitant", "medication_stability")
    conditional = (rule("r1", "required", stable, applicability=use),)
    assert decide(conditional, use).result == UNDETERMINED
    assert decide(conditional, stable).result == UNDETERMINED
    assert decide(conditional, AnyOf((Not(use), stable))).result == ENTAILED
    used = (*conditional, rule("r2", "required", use))
    decided = decide(used, stable)
    assert decided.result == ENTAILED and decided.proof == ("r1", "r2")


def test_a_contradiction_is_inconsistent_and_entails_nothing():
    clash = (rule("r1", "required", A), rule("x1", "excluded", A), rule("r2", "required", B))
    for query in (A, Not(A), B, C):
        decided = decide(clash, query)
        assert decided.result == INCONSISTENT
        assert decided.proof == ("r1", "x1")
    assert decide((rule("r1", "required", A), rule("x1", "excluded", B)), A).result == ENTAILED
    measured = (rule("r1", "required", cd4("ge", 200)), rule("r2", "required", cd4("lt", 200)))
    assert decide(measured, HIV).result == INCONSISTENT


def test_an_interpolated_premise_yields_an_interpolated_conclusion():
    answered = (rule("r1", "required", AllOf((A, B)), status="interpolated"),)
    decided = decide(answered, A)
    assert decided.result == ENTAILED and decided.status == "interpolated"
    with_known = (*answered, rule("r2", "required", A))
    decided = decide(with_known, A)
    assert decided.status == "known" and decided.proof == ("r2",)
    chained = (rule("r1", "required", A), rule("r2", "required", AnyOf((Not(A), B)), status="interpolated"))
    decided = decide(chained, B)
    assert decided.status == "interpolated" and decided.proof == ("r1", "r2")
    clash = (rule("r1", "required", A, status="interpolated"), rule("x1", "excluded", A))
    assert decide(clash, A).status == "interpolated"


def test_a_proposed_premise_is_refused():
    proposed = (rule("p1", "required", A, status="proposed"),)
    decided = decide(proposed, A)
    assert decided.result == UNDETERMINED and decided.proof == ()
    assert "proposed_refused:p1" in decided.blockers
    beside = (rule("r1", "required", A), rule("p1", "excluded", A, status="proposed"))
    decided = decide(beside, A)
    assert decided.result == ENTAILED and decided.proof == ("r1",) and decided.status == "known"


def test_weakest_status():
    assert weakest_status(("known", "known")) == "known"
    assert weakest_status(("known", "interpolated")) == "interpolated"
    assert weakest_status(("interpolated", "proposed", "known")) == "proposed"
    assert weakest_status(()) == "known"
    with pytest.raises(ModelError):
        weakest_status(("known", "certain"))


def test_another_persons_attribute_never_transfers():
    source_case = Subject("source_case")
    theirs = (rule("x1", "excluded", fact("HIV", subject=source_case)),)
    assert decide(theirs, Not(HIV)).result == UNDETERMINED
    ours = (rule("x1", "excluded", HIV),)
    assert decide(ours, Not(HIV)).result == ENTAILED


def test_evidence_never_splits_a_variable_but_time_does():
    from TrialLedger.assertions import Evidence

    cited = dataclasses.replace(HIV, evidence=(Evidence("text_span", "4-7"),))
    assert decide((rule("x1", "excluded", cited),), Not(HIV)).result == ENTAILED
    after = TemporalScope("after", "named_event", "chronic pancreatitis diagnosis", 0, 2, "years")
    before = TemporalScope("before", "enrollment", "", 0, 2, "years")
    event_relative = (rule("x1", "excluded", fact("autoimmune pancreatitis", time=after)),)
    assert decide(event_relative, Not(fact("autoimmune pancreatitis", time=before))).result == UNDETERMINED
    assert decide(event_relative, Not(fact("autoimmune pancreatitis", time=after))).result == ENTAILED


def test_measurements_are_typed_and_boundaries_exact():
    floor = (rule("r1", "required", cd4("ge", 200)),)
    assert decide(floor, cd4("gt", 100)).result == ENTAILED
    assert decide(floor, cd4("ge", 200)).result == ENTAILED
    assert decide(floor, cd4("gt", 200)).result == UNDETERMINED
    assert decide(floor, cd4("lt", 200)).result == REFUTED
    assert decide(floor, cd4("gt", 100, unit="cells/mm3")).result == UNDETERMINED
    assert decide(floor, cd4("gt", 100, unit="")).result == UNDETERMINED


def test_an_unspecified_interval_boundary_stays_undecided():
    def age(value):
        return Literal(PARTICIPANT, Predicate("demographic", "age"), value)

    def span(inclusivity):
        return age(Value("interval", "in", number=18, upper=75, unit="years", inclusivity=inclusivity))

    over = age(Value("quantity", "gt", number=18, unit="years"))
    at_least = age(Value("quantity", "ge", number=18, unit="years"))
    assert decide((rule("r1", "required", span("exclusive")),), over).result == ENTAILED
    assert decide((rule("r1", "required", span("inclusive")),), over).result == UNDETERMINED
    unspecified = decide((rule("r1", "required", span("unspecified")),), over)
    assert unspecified.result == UNDETERMINED and "unspecified_boundary:age" in unspecified.blockers
    assert decide((rule("r1", "required", span("unspecified")),), at_least).result == ENTAILED


def test_opaque_content_is_never_false():
    open_branch = (rule("r1", "required", AnyOf((A, Opaque("piece 4 tail")))),)
    decided = decide(open_branch, A)
    assert decided.result == UNDETERMINED and "opaque:piece 4 tail" in decided.blockers
    assert decide((rule("x1", "excluded", AnyOf((A, Opaque("t")))),), A).result == REFUTED
    assert decide(open_branch, Opaque("piece 4 tail")).result == UNSUPPORTED_QUERY
    assert decide(open_branch, Literal(Subject("unresolved"), Predicate("unresolved"), HOLDS)).result == (
        UNSUPPORTED_QUERY
    )
    assert decide(open_branch, "A").result == UNSUPPORTED_QUERY


def test_cohort_scope_and_the_open_population():
    cohort_b = (rule("r1", "required", A, cohort=Scope("cohort_ref", "B")),)
    assert decide(cohort_b, A, Context(cohort="B")).result == ENTAILED
    out = decide(cohort_b, A, Context(cohort="A"))
    assert out.result == OUT_OF_SCOPE and out.proof == ("r1",)
    open_population = decide(cohort_b, A, EVERYONE)
    assert open_population.result == UNDETERMINED and "open_scope:cohort_ref:B" in open_population.blockers
    assert decide(cohort_b, C, Context(cohort="A")).result == UNDETERMINED


def test_what_contributes_nothing():
    for modality in ("permitted", "definitional", "descriptive"):
        assert assertion_formula(rule("m1", modality, A), EVERYONE)[0] == "no_constraint"
        assert decide((rule("m1", modality, A),), A).result == UNDETERMINED
    assert assertion_formula(rule("u1", "unresolved", A), EVERYONE)[0] == "unresolved"
    conflicting = rule("c1", "required", A, resolution="conflicting")
    assert assertion_formula(conflicting, EVERYONE)[0] == "conflicting"
    assert assertion_formula(rule("r1", "required", A), EVERYONE)[0] == "constraint"
    assert assertion_formula(rule("r1", "required", A, cohort=Scope("arm_ref", "2")), Context(arm="1"))[
        0
    ] == ("scoped_out")


def test_the_formula_keeps_structure():
    formula, blockers = proposition_formula(AnyOf((AllOf((A, B)), Not(C))))
    assert formula[0] == "or" and formula[1][0][0] == "and" and formula[1][1][0] == "not"
    assert blockers == ()
    with pytest.raises(ModelError):
        proposition_formula("A")


def test_the_resource_bound_abstains():
    wide = (rule("r1", "required", AnyOf(tuple(fact(f"F{i}") for i in range(6)))),)
    tight = decide(wide, fact("F0"), bound=8)
    assert tight.result == UNDETERMINED and "resource_bound" in tight.blockers
    assert decide(wide, AnyOf(tuple(fact(f"F{i}") for i in range(6)))).result == ENTAILED
    elsewhere = (rule("r0", "required", A), *wide)
    assert decide(elsewhere, A, bound=8).result == UNDETERMINED


def test_the_decision_is_the_same_in_any_order():
    premises = (
        rule("r1", "required", A),
        rule("r2", "required", AnyOf((Not(A), B))),
        rule("r3", "required", B, status="interpolated"),
        rule("x1", "excluded", AllOf((HIV, cd4("lt", 200)))),
        rule("p1", "required", C, status="proposed"),
    )
    results = {decide(order, B) for order in itertools.permutations(premises)}
    assert len(results) == 1
    (only,) = results
    assert only.result == ENTAILED and only.proof == ("r1", "r2") and only.status == "known"
    with pytest.raises(ModelError):
        decide((rule("r1", "required", A), rule("r1", "required", B)), A)


POSITIVE_HIV = dataclasses.replace(HIV, qualifiers=cd4("lt", 200))
NEGATIVE_HIV = dataclasses.replace(POSITIVE_HIV, polarity="negative")


def test_a_negative_qualified_literal_negates_the_conjunction():
    """Positive: "must not be HIV positive with CD4 < 200" as required(negative qualified literal) and as
    excluded(HIV qualified by CD4 < 200) compile to one formula and decide alike: the conjunction is refuted,
    HIV implies CD4 >= 200. Negative: neither encoding entails NOT HIV, nor CD4 < 200, nor CD4 >= 200."""
    as_negative = rule("r1", "required", NEGATIVE_HIV)
    as_exclusion = rule("r1", "excluded", POSITIVE_HIV)
    assert assertion_formula(as_negative, EVERYONE) == assertion_formula(as_exclusion, EVERYONE)
    assert proposition_formula(NEGATIVE_HIV) == proposition_formula(Not(POSITIVE_HIV))
    for encoding in ((as_negative,), (as_exclusion,)):
        assert decide(encoding, Not(HIV)).result == UNDETERMINED
        assert decide(encoding, HIV).result == UNDETERMINED
        assert decide(encoding, cd4("lt", 200)).result == UNDETERMINED
        assert decide(encoding, cd4("ge", 200)).result == UNDETERMINED
        assert decide(encoding, AllOf((HIV, cd4("lt", 200)))).result == REFUTED
        assert decide(encoding, POSITIVE_HIV).result == REFUTED
        assert decide(encoding, NEGATIVE_HIV).result == ENTAILED
        assert decide(encoding, AnyOf((Not(HIV), cd4("ge", 200)))).result == ENTAILED


def test_moving_a_negation_changes_the_meaning():
    """The semantic mutant "move a negation": NOT (HIV AND CD4 < 200) is not (NOT HIV) AND CD4 < 200, nor NOT
    HIV with the qualifier dropped. Positive: the moved form entails NOT HIV and CD4 < 200, the unqualified
    negative literal entails NOT HIV and refutes HIV. Negative: the negative qualified literal entails
    neither, and its formula differs from both mutants'."""
    moved = AllOf((Not(HIV), cd4("lt", 200)))
    dropped = dataclasses.replace(HIV, polarity="negative")
    assert proposition_formula(NEGATIVE_HIV) != proposition_formula(moved)
    assert proposition_formula(NEGATIVE_HIV) != proposition_formula(dropped)
    mutant = (rule("r1", "required", moved),)
    assert decide(mutant, Not(HIV)).result == ENTAILED
    assert decide(mutant, cd4("lt", 200)).result == ENTAILED
    unqualified = (rule("r1", "required", dropped),)
    assert decide(unqualified, Not(HIV)).result == ENTAILED and decide(unqualified, HIV).result == REFUTED
    kept = (rule("r1", "required", NEGATIVE_HIV),)
    assert decide(kept, Not(HIV)).result == UNDETERMINED
    assert decide(kept, cd4("lt", 200)).result == UNDETERMINED
    excluded_negative = (rule("x1", "excluded", NEGATIVE_HIV),)
    assert decide(excluded_negative, HIV).result == ENTAILED
    assert decide(excluded_negative, cd4("lt", 200)).result == ENTAILED


def test_a_negative_literal_on_each_value_kind():
    """Positive: a negative literal is the negation of its positive twin on every value kind (boolean,
    enumerated with ne, quantity, member set), so requiring both is INCONSISTENT. Negative: a negative
    literal's subject, predicate or time never leaks to another variable."""
    stage = Predicate("disease_attribute", "extent")
    twins = (
        HIV,
        Literal(PARTICIPANT, stage, Value("enum", "ne", ("m",))),
        cd4("lt", 200),
        Literal(PARTICIPANT, Predicate("disease_attribute", "mutations"), Value("enum_set", "in", ("EGFR",))),
    )
    for positive in twins:
        negative = dataclasses.replace(positive, polarity="negative")
        assert decide((rule("r1", "required", negative),), positive).result == REFUTED
        clash = (rule("r1", "required", negative), rule("r2", "required", positive))
        assert decide(clash, positive).result == INCONSISTENT
    others = (rule("r1", "required", dataclasses.replace(HIV, polarity="negative")),)
    assert decide(others, fact("HIV", subject=Subject("source_case"))).result == UNDETERMINED
    assert decide(others, fact("HBV")).result == UNDETERMINED


def test_membership_is_one_variable_and_respects_subsets():
    """Positive: on a member-set value, in {a} and not_in {a} are one variable, so requiring both is
    INCONSISTENT, as are in {a} and not_in {a, b}; in {a, b} entails in {a}; not_in {a, b} entails not_in {a}
    (it holds none of them); enumerated in {a} entails in {a, b}; a reference eq x and its negative twin
    clash. Negative: in {a} does not entail in {a, b}; not_in {a} does not entail not_in {a, b}, and not_in
    {EGFR, ALK} refutes EGFR alone; in {a} and not_in {b} are consistent; another predicate's member is
    another variable; a reference eq R1 does not refute eq R2 (single-valuedness is the registry's)."""

    def holds(comparison, *members, key="mutations", kind="enum_set"):
        return Literal(PARTICIPANT, Predicate("disease_attribute", key), Value(kind, comparison, members))

    clash = (rule("r1", "required", holds("in", "a")), rule("r2", "required", holds("not_in", "a")))
    assert decide(clash, HIV).result == INCONSISTENT
    apart = (rule("r1", "required", holds("in", "a")), rule("r2", "required", holds("not_in", "b")))
    assert decide(apart, holds("in", "a")).result == ENTAILED
    assert decide(apart, holds("in", "b")).result == REFUTED
    assert decide((rule("r1", "required", holds("in", "a", "b")),), holds("in", "a")).result == ENTAILED
    assert decide((rule("r1", "required", holds("in", "a")),), holds("in", "a", "b")).result == UNDETERMINED
    assert decide((rule("r1", "required", holds("not_in", "a")),), holds("not_in", "a", "b")).result == (
        UNDETERMINED
    )
    assert decide((rule("r1", "required", holds("not_in", "a", "b")),), holds("not_in", "a")).result == (
        ENTAILED
    )
    neither = (rule("r1", "required", holds("not_in", "EGFR", "ALK")),)
    assert decide(neither, holds("in", "EGFR")).result == REFUTED
    assert decide(neither, holds("in", "ALK")).result == REFUTED
    wider = (rule("r1", "required", holds("in", "a")), rule("r2", "required", holds("not_in", "a", "b")))
    assert decide(wider, HIV).result == INCONSISTENT
    assert decide((rule("r1", "required", holds("in", "a")),), holds("in", "a", key="fusions")).result == (
        UNDETERMINED
    )
    enum_one = (rule("r1", "required", holds("in", "a", key="extent", kind="enum")),)
    assert decide(enum_one, holds("in", "a", "b", key="extent", kind="enum")).result == ENTAILED
    assert decide(enum_one, holds("not_in", "a", key="extent", kind="enum")).result == REFUTED
    ref = Literal(PARTICIPANT, Predicate("defined_term", "regimen"), Value("entity_ref", "eq", ("R1",)))
    twin = (rule("r1", "required", ref), rule("x1", "excluded", ref))
    assert decide(twin, HIV).result == INCONSISTENT
    other = Literal(PARTICIPANT, Predicate("defined_term", "regimen"), Value("entity_ref", "eq", ("R2",)))
    assert decide((rule("r1", "required", ref),), other).result == UNDETERMINED


def test_time_certainty_is_not_identity_but_orientation_anchor_and_bounds_are():
    """Positive: one time scope stated explicitly and entailed is one variable (certainty is epistemic
    metadata). Negative: another orientation, anchor or bound is another variable."""
    explicit = TemporalScope("before", "enrollment", "", 0, 4, "weeks", certainty="explicit")
    entailed = dataclasses.replace(explicit, certainty="entailed")
    excluded = (rule("x1", "excluded", fact("surgery", "procedure_event", time=explicit)),)
    assert decide(excluded, Not(fact("surgery", "procedure_event", time=entailed))).result == ENTAILED
    assert decide(excluded, fact("surgery", "procedure_event", time=entailed)).result == REFUTED
    for changed in (
        dataclasses.replace(explicit, orientation="after"),
        dataclasses.replace(explicit, anchor="randomization"),
        dataclasses.replace(explicit, upper=8),
    ):
        assert decide(excluded, Not(fact("surgery", "procedure_event", time=changed))).result == UNDETERMINED


def test_an_unresolved_rule_is_never_a_premise():
    """Positive: an assertion stating its rule is a premise. Negative: one carrying the explicitly unresolved
    rule contributes nothing, is named as a blocker, and never forms a contradiction."""
    unknown = rule("u1", "required", A, rule=UNRESOLVED_RULE)
    assert assertion_formula(unknown, EVERYONE) == (
        "unresolved_rule",
        ("const", True),
        ("unresolved_rule:u1",),
    )
    decided = decide((unknown,), A)
    assert decided.result == UNDETERMINED and "unresolved_rule:u1" in decided.blockers
    beside = decide((unknown, rule("x1", "excluded", A)), A)
    assert beside.result == REFUTED and beside.proof == ("x1",)
    assert decide((rule("r1", "required", A),), A).result == ENTAILED


def test_a_status_outside_the_vocabulary_is_refused_by_name():
    """Positive: proposed, interpolated and known are the vocabulary. Negative: any other word raises exactly
    ModelError("status_outside_vocabulary"), never another error type nor a bare ModelError."""
    assert _outcome(weakest_status, ("known", "certain")) == ("ModelError", ("status_outside_vocabulary",))
    assert weakest_status(("known", "interpolated")) == "interpolated"


def test_anything_but_a_proposition_is_refused_by_name():
    """Positive: Always, Opaque, Not, AllOf, AnyOf and Literal compile. Negative: anything else, a bare string
    among them, raises exactly ModelError("not_a_proposition"), never another error type, a bare ModelError,
    or a formula."""
    assert _outcome(proposition_formula, "A") == ("ModelError", ("not_a_proposition",))


def _outcome(function, argument):
    """What a call does, as a value: its return, or the exact type name and arguments of what it raised, so
    an assertion (not a crash) tells a ModelError from any other error."""
    try:
        return ("returned", function(argument))
    except Exception as error:  # every error is compared by name and arguments, never passed through
        return (type(error).__name__, error.args)
