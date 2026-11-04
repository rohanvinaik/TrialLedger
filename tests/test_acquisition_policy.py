"""Intent tests: NIH work protection must not become a clinical or local replay ceiling."""

import pytest

from TrialLedger.acquisition import (
    effective_policy,
    expansion_code,
    expected_id_count,
    policy_problem,
    registry_plan_requests,
)


def test_tiny_acquisition_and_exact_boundary_are_permitted():
    assert expansion_code(1000, 100, 1, 2, 4) == "within_budget"
    assert expansion_code(1000, 100, 1000, 100, 100) == "within_budget"


def test_broad_first_count_must_not_authorize_bulk_work():
    assert expansion_code(1000, 100, 1001, 2, 15) == "study_expansion"
    assert expansion_code(1000, 100, 10, 2, 101) == "request_expansion"
    assert expansion_code(1000, 100, None, 101, 0) == "request_expansion"


def test_an_explicit_larger_budget_must_not_be_replaced_by_defaults():
    assert effective_policy({"max_studies": 5000, "max_registry_requests": 300}) == {
        "max_studies": 5000,
        "max_registry_requests": 300,
    }
    assert expansion_code(5000, 300, 5000, 2, 57) == "within_budget"


def test_defaults_are_operational_and_partial_overrides_are_literal():
    assert effective_policy() == {"max_studies": 1000, "max_registry_requests": 100}
    assert effective_policy({"max_studies": 2}) == {"max_studies": 2, "max_registry_requests": 100}
    assert effective_policy({}) == {"max_studies": 1000, "max_registry_requests": 100}


def test_malformed_policies_must_not_be_coerced_or_silently_accepted():
    assert policy_problem(None) == "not_an_object"
    assert policy_problem([]) == "not_an_object"
    assert policy_problem({"extra": 5}) == "unknown_field"
    assert policy_problem({"max_studies": True}) == "invalid_max_studies"
    assert policy_problem({"max_studies": 0}) == "invalid_max_studies"
    assert policy_problem({"max_studies": 1.5}) == "invalid_max_studies"
    assert policy_problem({"max_registry_requests": False}) == "invalid_max_registry_requests"
    assert policy_problem({"max_registry_requests": -1}) == "invalid_max_registry_requests"
    assert policy_problem({"max_registry_requests": "100"}) == "invalid_max_registry_requests"
    assert policy_problem({"max_studies": 1, "max_registry_requests": 1}) == "ok"
    with pytest.raises(ValueError, match="acquisition.invalid_max_studies"):
        effective_policy({"max_studies": False})


def test_bad_costs_must_not_be_treated_as_zero_or_missing():
    assert expansion_code(1, 1, False, 0, 0) == "invalid_cost"
    assert expansion_code(True, 1, 0, 0, 0) == "invalid_cost"
    assert expansion_code(1, 0, 0, 0, 0) == "invalid_cost"
    assert expansion_code(1, 1, -1, 0, 0) == "invalid_cost"
    assert expansion_code(1, 1, 0, -1, 0) == "invalid_cost"
    assert expansion_code(1, 1, 0, 0, 1.0) == "invalid_cost"
    assert expansion_code(1, 1, 0, 1, 1) == "within_budget"


def test_complete_page_plan_counts_json_csv_ids_and_both_snapshot_requests():
    assert registry_plan_requests(0, "run") == 3
    assert registry_plan_requests(0, "json_csv") == 5
    assert registry_plan_requests(100, "run") == 4
    assert registry_plan_requests(101, "run") == 5
    assert registry_plan_requests(1001, "run") == 15
    assert registry_plan_requests(1001, "ids") == 4
    assert registry_plan_requests(1001, "studies") == 14
    assert registry_plan_requests(1001, "json_csv") == 25
    with pytest.raises(ValueError, match="invalid_acquisition_plan"):
        registry_plan_requests(1, "other")
    with pytest.raises(ValueError, match="invalid_acquisition_plan"):
        registry_plan_requests(True, "run")
    with pytest.raises(ValueError, match="invalid_acquisition_plan"):
        registry_plan_requests(1, "run", page_size=0)


def test_explicit_id_scope_must_not_expand_from_duplicate_tokens():
    assert expected_id_count({"filter.ids": "NCT00000001,nct00000001|NCT00000002"}) == 2
    assert expected_id_count({"query.cond": "lung cancer"}) is None
    assert effective_policy(expected_studies=2000, expected_requests=204) == {
        "max_studies": 2000,
        "max_registry_requests": 204,
    }


def test_empty_and_partial_policy_are_valid_without_fabricating_a_budget_value():
    assert policy_problem({}) == "ok"
    assert policy_problem({"max_studies": 2}) == "ok"
    assert policy_problem({"max_registry_requests": 2}) == "ok"
