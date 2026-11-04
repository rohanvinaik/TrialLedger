"""Intent: permissions remain visible without constraining; conditions require nonvacuous scoped proof."""

import dataclasses

import pytest

from TrialLedger.layer2 import entail
from TrialLedger.layer2.assertions import (
    AllOf,
    Always,
    Literal,
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
from TrialLedger.layer2.entail_explanations import (
    MAX_CONDITIONS,
    condition_code,
    explain,
    explanation_gate,
    permission_code,
    planned_conditions,
)


def fact(key="AF", *, polarity="positive"):
    return Literal(
        Subject("participant"), Predicate("condition_status", key), Value("boolean"), polarity=polarity
    )


def number(value, comparison="eq", unit="pg/mL"):
    return Literal(
        Subject("participant"),
        Predicate("measurement", "ntp"),
        Value("quantity", comparison, number=value, unit=unit, inclusivity="inclusive"),
    )


def rule(identity, body, *, modality="required", status="known", cohort=None, applicability=None):
    return ScopedAssertion(
        identity,
        "caller:" + identity,
        modality,
        body,
        rule=Rule("caller", "1"),
        status=status,
        resolution="resolved",
        cohort=cohort or Scope("all_participants"),
        applicability=applicability or Always(),
    )


@pytest.mark.parametrize(
    "admission,scope,relation,conditional,expected",
    [
        ("accepted", "applicable", "none", False, "unrelated"),
        ("proposed", "applicable", "exact", False, "withheld_permission"),
        ("accepted", "outside", "exact", False, "out_of_scope"),
        ("accepted", "open", "exact", False, "withheld_permission"),
        ("accepted", "applicable", "related", False, "related_permission"),
        ("accepted", "applicable", "exact", True, "conditional_permission"),
        ("accepted", "applicable", "exact", False, "explicit_permission"),
        ("accepted", "applicable", "future", False, "withheld_permission"),
    ],
)
def test_permission_codes_never_promote_a_mention(admission, scope, relation, conditional, expected):
    assert permission_code(admission, scope, relation, conditional) == expected


@pytest.mark.parametrize(
    "result,blockers,intrinsic,expected",
    [
        ("REFUTED", [], True, "not_open"),
        ("INCONSISTENT", [], True, "not_open"),
        ("UNSUPPORTED_QUERY", [], True, "not_open"),
        ("UNDETERMINED", ["resource_bound"], True, "unresolved"),
        ("UNDETERMINED", ["opaque:x"], True, "unresolved"),
        ("UNDETERMINED", [], None, "limited"),
        ("UNDETERMINED", [], False, "impossible"),
        ("UNDETERMINED", ["undecided_by_constraints"], True, "eligible"),
    ],
)
def test_conditional_gate_refuses_vacuity_and_unresolved_profiles(result, blockers, intrinsic, expected):
    assert explanation_gate(result, blockers, intrinsic) == expected


@pytest.mark.parametrize(
    "global_result,implication,blockers,expected",
    [
        ("UNDETERMINED", "ENTAILED", [], "necessary"),
        ("ENTAILED", "ENTAILED", [], "already_required"),
        ("REFUTED", "ENTAILED", [], "not_proved"),
        ("UNDETERMINED", "UNDETERMINED", [], "not_proved"),
        ("UNDETERMINED", "ENTAILED", ["resource_bound"], "unresolved"),
    ],
)
def test_necessary_condition_code_requires_actual_implication(global_result, implication, blockers, expected):
    assert condition_code(global_result, implication, blockers) == expected


def test_exact_permission_is_visible_without_proving_presence():
    query = fact("treatment")
    given = (rule("permit", query, modality="permitted"),)
    decision = entail.decide(given, query)
    result = explain(given, query, entail.EVERYONE, decision, 65536)
    assert result["permissions"][0]["code"] == "explicit_permission"
    assert decision.result == "UNDETERMINED" and decision.proof == ()
    assert result["conditions"] == [] and result["checks"]["decisions"] == 0


def test_shared_quantity_variable_does_not_permit_an_excluded_value():
    given = (rule("permit", number(18, "ge", "years"), modality="permitted"),)
    query = number(15, "eq", "years")
    result = explain(given, query, entail.EVERYONE, entail.decide(given, query), 65536)
    assert result["permissions"][0]["code"] == "related_permission"
    assert result["permissions"][0]["body"]["value"]["number"] == 18


@pytest.mark.parametrize(
    "status,scope,context,code",
    [
        ("proposed", Scope("all_participants"), entail.EVERYONE, "withheld_permission"),
        ("known", Scope("cohort_ref", "A"), entail.Context(cohort="B"), "out_of_scope"),
        ("known", Scope("cohort_ref", "A"), entail.EVERYONE, "withheld_permission"),
    ],
)
def test_unaccepted_or_unbound_permission_is_not_explicit(status, scope, context, code):
    query = fact()
    given = (rule("permit", query, modality="permitted", status=status, cohort=scope),)
    result = explain(given, query, context, entail.decide(given, query, context), 65536)
    assert result["permissions"][0]["code"] == code


def test_permission_retains_applicability_without_asserting_it():
    query = fact("drug")
    given = (rule("permit", query, modality="permitted", applicability=fact()),)
    result = explain(given, query, entail.EVERYONE, entail.decide(given, query), 65536)
    assert result["permissions"][0]["code"] == "conditional_permission"
    assert result["permissions"][0]["applicability"]["predicate"]["key"] == "AF"


def test_permission_never_overrides_exclusion():
    query = fact()
    given = (rule("permit", query, modality="permitted"), rule("exclude", query, modality="excluded"))
    decision = entail.decide(given, query)
    result = explain(given, query, entail.EVERYONE, decision, 65536)
    assert decision.result == "REFUTED" and decision.proof == ("exclude",)
    assert result["conditions"] == []


def test_threshold_condition_is_proved_without_changing_original_answer():
    given = (
        rule("non_af", number(600, "ge"), applicability=fact(polarity="negative")),
        rule("af", number(1200, "ge"), applicability=fact()),
    )
    query = number(900)
    decision = entail.decide(given, query)
    before = dataclasses.asdict(decision)
    result = explain(given, query, entail.EVERYONE, decision, 65536)
    assert dataclasses.asdict(decision) == before and decision.result == "UNDETERMINED"
    assert len(result["conditions"]) == 1
    condition = result["conditions"][0]
    assert condition["body"]["polarity"] == "negative"
    assert condition["warrant"]["proof"] == ("af",) and condition["status"] == "known"
    assert result["checks"]["decisions"] == 4


def test_condition_plan_contains_no_atom_outside_original_query_component():
    given = (
        rule("non_af", number(600, "ge"), applicability=fact(polarity="negative")),
        rule("af", number(1200, "ge"), applicability=fact()),
        rule("other", fact("unrelated"), applicability=fact("unrelated_guard")),
    )
    query = number(900)
    plan = planned_conditions(given, query, entail.EVERYONE)
    formula, _ = entail.proposition_formula(query)
    all_atoms = set(entail._atoms(formula))
    for item in given[:2]:
        _, rule_formula, _ = entail.assertion_formula(item, entail.EVERYONE)
        all_atoms.update(entail._atoms(rule_formula))
    assert len(plan) == 2
    for condition in plan:
        compiled, _ = entail.proposition_formula(condition)
        assert set(entail._atoms(compiled)) <= all_atoms


def test_proposed_antecedents_never_create_a_condition_plan():
    query = number(900)
    given = (rule("proposed", number(1200, "ge"), applicability=fact(), status="proposed"),)
    assert planned_conditions(given, query, entail.EVERYONE) == ()
    assert explain(given, query, entail.EVERYONE, entail.decide(given, query), 65536)["conditions"] == []


def test_impossible_profile_never_generates_vacuous_conditions():
    query = AllOf((fact(), Not(fact())))
    decision = entail.decide((), query)
    result = explain((), query, entail.EVERYONE, decision, 65536)
    assert result["conditions"] == [] and result["checks"]["code"] == "impossible"


@pytest.mark.parametrize("query", [Opaque("unread"), "not a proposition"])
def test_unsupported_query_keeps_no_conditional_fact(query):
    decision = entail.decide((), query)
    result = explain((), query, entail.EVERYONE, decision, 65536)
    assert result["conditions"] == [] and result["checks"]["decisions"] == 0


def test_condition_plan_is_bounded_and_reports_incomplete_coverage():
    query = Not(fact("Q"))
    given = tuple(rule(str(i), fact("Q"), applicability=fact(str(i))) for i in range(9))
    result = explain(given, query, entail.EVERYONE, entail.decide(given, query), 65536)
    assert len(planned_conditions(given, query, entail.EVERYONE)) == MAX_CONDITIONS
    assert result["checks"]["decisions"] == 2 * MAX_CONDITIONS
    assert (
        result["checks"]["code"] == "limited"
        and "resource_bound:explanation_conditions" in result["blockers"]
    )


@pytest.mark.parametrize("bound", [None, False, 0, -1, 65537])
def test_invalid_explanation_bound_is_named(bound):
    query = fact()
    with pytest.raises(ValueError, match="invalid_resource_bound:explanations"):
        explain((), query, entail.EVERYONE, entail.decide((), query), bound)


def test_condition_warrant_cannot_promote_a_working_assumption():
    given = (rule("af", number(1200, "ge"), applicability=fact(), status="interpolated"),)
    query = number(900)
    result = explain(given, query, entail.EVERYONE, entail.decide(given, query), 65536)
    assert result["conditions"][0]["status"] == "interpolated"
    assert result["conditions"][0]["warrant"]["proof"] == ("af",)


@pytest.mark.parametrize("difference", ["unit", "time"])
def test_a_different_unit_or_time_window_does_not_supply_a_condition(difference):
    body = number(1200, "ge")
    query = (
        number(900, unit="ng/L")
        if difference == "unit"
        else dataclasses.replace(
            number(900),
            time=TemporalScope("at", "randomization", unit="days", certainty="explicit"),
        )
    )
    given = (rule("af", body, applicability=fact()),)
    result = explain(given, query, entail.EVERYONE, entail.decide(given, query), 65536)
    assert planned_conditions(given, query, entail.EVERYONE) == ()
    assert result["conditions"] == []


def test_permission_conjunction_is_not_flattened_into_a_permission_for_one_part():
    query = fact("drug")
    body = AllOf((query, fact("monitoring")))
    given = (rule("permit", body, modality="permitted"),)
    result = explain(given, query, entail.EVERYONE, entail.decide(given, query), 65536)
    assert result["permissions"][0]["code"] == "related_permission"
    assert result["permissions"][0]["body"]["class"] == "AllOf"


def test_non_boolean_applicability_flag_must_not_create_explicit_permission():
    assert permission_code("accepted", "applicable", "exact", 0) == "withheld_permission"


def test_unrecognized_feasibility_result_must_remain_a_computation_limit():
    assert explanation_gate("UNDETERMINED", [], {"nested": {"bounded": True}}) == "limited"
