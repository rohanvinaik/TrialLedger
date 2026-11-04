"""Intent: expose proved residual requirements without filling a partial profile.

Premises here are invented typed fixtures. No clinical reading or actual person is
established by these tests; conditions are implications under the supplied profile.
"""

import dataclasses
import json

from TrialLedger.layer2 import entail
from TrialLedger.layer2.assertions import (
    AllOf,
    AnyOf,
    Literal,
    Not,
    Predicate,
    Rule,
    ScopedAssertion,
    Subject,
    Value,
    canonical,
    from_canonical,
)
from TrialLedger.layer2.entail_explanations import explain


def fact(key):
    return Literal(Subject("participant"), Predicate("condition_status", key), Value("boolean"))


def number(key, value, comparison="eq", unit="unit"):
    return Literal(
        Subject("participant"),
        Predicate("measurement", key),
        Value("quantity", comparison, number=value, unit=unit, inclusivity="inclusive"),
    )


def rule(identity, body, *, application=None, status="known", modality="required"):
    fields = {"applicability": application} if application is not None else {}
    return ScopedAssertion(
        identity,
        "invented:" + identity,
        modality,
        body,
        rule=Rule("invented", "1"),
        status=status,
        resolution="resolved",
        **fields,
    )


def explained(given, query):
    decision = entail.decide(given, query)
    before = dataclasses.asdict(decision)
    result = explain(given, query, entail.EVERYONE, decision, 65536)
    assert dataclasses.asdict(decision) == before
    return result


def body(row):
    return canonical(from_canonical(json.dumps(row["body"])))


def test_bmi_profile_exposes_the_whole_four_way_condition_without_requiring_an_individual_disease():
    route = AnyOf(tuple(fact(str(index)) for index in range(4)))
    given = (
        rule("floor", number("BMI", 27, "ge")),
        rule("route", route, application=number("BMI", 30, "lt")),
    )
    result = explained(given, number("BMI", 28))
    matching = [row for row in result["conditions"] if row["body"].get("class") == "AnyOf"]
    assert len(matching) == 1
    assert body(matching[0]) == canonical(route)
    assert matching[0]["relation"] == "necessary_if_query"
    assert matching[0]["warrant"]["proof"] == ("route",)
    assert not any(row["body"].get("class") == "Literal" for row in result["conditions"])


def test_prior_treatment_exposes_washout_without_claiming_the_person_failed_it():
    prior = fact("prior")
    washout = number("since_dose_at_screening", 180, "ge", "days")
    result = explained((rule("washout", washout, application=prior),), prior)
    matching = [row for row in result["conditions"] if body(row) == canonical(washout)]
    assert len(matching) == 1
    assert matching[0]["relation"] == "necessary_if_query"
    assert matching[0]["warrant"]["proof"] == ("washout",)


def test_equivalent_disjunction_and_applicability_keep_the_same_backward_requirement():
    af = fact("AF")
    threshold = number("NT", 1200, "ge", "pg/mL")
    query = number("NT", 900, unit="pg/mL")
    conditional = explained((rule("threshold", threshold, application=af),), query)
    disjunction = explained((rule("threshold", AnyOf((Not(af), threshold))),), query)
    expected = canonical(Not(af))

    def compiled_bodies(result):
        return {
            entail.proposition_formula(from_canonical(json.dumps(row["body"])))[0]
            for row in result["conditions"]
        }

    assert entail.proposition_formula(Not(af))[0] in compiled_bodies(conditional)
    assert compiled_bodies(disjunction) == compiled_bodies(conditional), expected


def test_entailed_partial_profile_still_exposes_other_criteria_without_establishing_actual_absence():
    age = fact("adult")
    renal = fact("renal")
    given = (rule("adult", age), rule("renal", renal))
    result = explained(given, age)
    assert entail.decide(given, age).result == "ENTAILED"
    assert len(result["conditions"]) == 1
    assert body(result["conditions"][0]) == canonical(renal)
    assert result["conditions"][0]["relation"] == "required_by_criteria"
    assert result["conditions"][0]["warrant"]["proof"] == ("renal",)


def test_profile_established_compound_is_not_repeated_as_an_open_requirement():
    one, two = fact("one"), fact("two")
    given = (rule("both", AllOf((one, two))),)
    assert explained(given, AllOf((one, two)))["conditions"] == []


def test_refuted_profile_must_not_generate_vacuous_residuals():
    one, two = fact("one"), fact("two")
    given = (rule("one", one), rule("two", two))
    assert explained(given, Not(one))["conditions"] == []


def test_proposed_rule_must_not_supply_an_accepted_requirement():
    given = (rule("unconfirmed", fact("B"), application=fact("A"), status="proposed"),)
    assert explained(given, fact("A"))["conditions"] == []


def test_criteria_derived_truth_must_not_be_used_to_specialize_the_profile():
    from TrialLedger.layer2 import residual_requirements as residual
    from TrialLedger.layer2.entail_explanations import condition_plan

    one, two, other = fact("A"), fact("B"), fact("other")
    query = AnyOf((one, other))
    given = (rule("A", one), rule("conditional", two, application=one))
    plan = condition_plan(given, query, entail.EVERYONE)
    source = next(seed.body for seed in plan.seeds if isinstance(seed.body, AnyOf))
    assert residual.specialize(source, {}) == source
    result = explained(given, query)
    assert any(body(row) == canonical(source) for row in result["conditions"])
    assert not any(row["relation"] == "necessary_if_query" for row in result["conditions"])


def test_out_of_scope_and_unbound_rules_must_not_become_criteria_wide_requirements():
    from TrialLedger.layer2.assertions import Scope

    scoped = dataclasses.replace(rule("cohort", fact("A")), cohort=Scope("cohort_ref", "A"))
    for context in (entail.EVERYONE, entail.Context(cohort="B")):
        decision = entail.decide((scoped,), fact("other"), context)
        result = explain((scoped,), fact("other"), context, decision, 65536)
        assert result["conditions"] == []


def test_contradiction_anywhere_must_not_generate_vacuous_requirements():
    given = (rule("A", fact("A")), rule("not-A", Not(fact("A"))), rule("B", fact("B")))
    assert explained(given, fact("other"))["conditions"] == []


def test_profile_truth_classifier_requires_both_signed_checks():
    from TrialLedger.layer2.residual_requirements import profile_truth_code

    expected = {
        (True, False): "established",
        (False, True): "refuted",
        (True, True): "open",
        (False, False): "unresolved",
    }
    for pair, code in expected.items():
        assert profile_truth_code(*pair) == code
    for pair in ((None, True), (False, None), (None, None)):
        assert profile_truth_code(*pair) == "limited"
    for pair in ((True, 0), (1, False), ("true", False)):
        assert profile_truth_code(*pair) == "unresolved"


def test_junction_classifier_preserves_disjunction_and_conjunction():
    from TrialLedger.layer2.residual_requirements import junction_code

    cases = [
        ("and", [], "true"),
        ("or", [], "false"),
        ("and", ["true", "open"], "single"),
        ("or", ["false", "open"], "single"),
        ("and", ["false", "open"], "false"),
        ("or", ["true", "open"], "true"),
        ("and", ["open", "open"], "compound"),
        ("or", ["open", "open"], "compound"),
        ("future", [], "unresolved"),
        ("and", ["future"], "unresolved"),
        ("or", ["true", "future"], "unresolved"),
    ]
    for operator, states, expected in cases:
        assert junction_code(operator, states) == expected


def test_discovery_node_limit_preserves_the_whole_original_clause():
    from TrialLedger.layer2.residual_requirements import MAX_PLAN_NODES, candidate_plan

    whole = AllOf(tuple(fact(str(i)) for i in range(MAX_PLAN_NODES + 1)))
    plan = candidate_plan((rule("wide", whole),), fact("0"), entail.EVERYONE)
    assert plan.seeds[0].body == whole
    assert "resource_bound:explanation_plan_nodes" in plan.blockers


def test_discovery_does_not_descend_inside_a_qualified_literal():
    from TrialLedger.layer2.residual_requirements import candidate_plan

    qualified = dataclasses.replace(fact("A"), qualifiers=AnyOf((fact("B"), fact("C"))))
    plan = candidate_plan((rule("qualified", qualified),), fact("A"), entail.EVERYONE)
    assert tuple(seed.body for seed in plan.seeds) == (qualified,)


def test_reservation_covers_profile_proofs_and_newly_joined_components(monkeypatch):
    from TrialLedger.layer2 import solver_work

    route = AnyOf(tuple(fact(str(i)) for i in range(4)))
    given = (
        rule("floor", number("BMI", 27, "ge")),
        rule("route", route, application=number("BMI", 30, "lt")),
        rule("independent", fact("renal")),
        rule("washout", number("washout", 180, "ge", "days"), application=fact("prior")),
    )
    query = AllOf((number("BMI", 28), fact("prior")))
    calls = []
    original = entail._satisfiable

    def counted(formulas, bound):
        calls.append(solver_work._partition_space(formulas, bound))
        return original(formulas, bound)

    monkeypatch.setattr(entail, "_satisfiable", counted)
    reservation = solver_work._decision_work(given, query, entail.EVERYONE, 65536, True)
    result = explained(given, query)
    assert result["checks"]["profile_queries"] > 0
    assert any(row["relation"] == "required_by_criteria" for row in result["conditions"])
    assert any(row["relation"] == "necessary_if_query" for row in result["conditions"])
    assert reservation >= sum(calls)
    assert result["coverage"] == "bounded_candidate_discovery_not_complete_screening"
