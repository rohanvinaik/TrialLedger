"""Exact one-stage binomial design operator (interface v1, contract C7, packet D; acceptance STA-1..STA-4)."""

import copy
import json
from pathlib import Path

import pytest

from TrialLedger.layer2 import protocol_statistics

FIXTURES = Path(__file__).resolve().parents[1] / (
    "openspec/changes/connect-protocol-design-workflow/interface/fixtures/binomial.json"
)
FIXTURE = json.loads(FIXTURES.read_text())
CASES = FIXTURE["cases"]
MALFORMED = FIXTURE["malformed"]


def _assumption(role, ref="user:interface fixture", status="known", resolution="resolved"):
    return {
        "role": role,
        "ref": ref,
        "version": "1",
        "status": status,
        "resolution": resolution,
        "basis": ["user:simulated planning choice"],
    }


def _all_roles(**overrides):
    return [
        _assumption(role, ref=f"user:{role} fixture", **overrides.get(role, {}))
        for role in ("fixed_n", "iid_binary", "alignment")
    ]


def _data(n=2, k=2, p0="1/2", p1="3/4", assumptions=None):
    return {
        "scope": "draft:phase2-response",
        "model": "fixed_n_iid_bernoulli",
        "direction": "greater",
        "n": n,
        "critical_count": k,
        "p0": p0,
        "p1": p1,
        "assumptions": _all_roles() if assumptions is None else assumptions,
    }


# ----------------------------------------------------------------------------------------------------
# Acceptance fixtures (binomial.json). Each expected key is compared against the production result.
# ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_fixture_case_matches_expected_result(case):
    result = protocol_statistics.check("binomial_design", case["data"], case["claims"])
    expect = case["expect"]
    value = result["value"]
    assert result["code"] == expect["code"]
    if "computed" in expect:
        assert value["computed"] is expect["computed"]
    if "null_rejection_probability" in expect:
        assert value["null_rejection_probability"] == expect["null_rejection_probability"]
    if "power" in expect:
        assert value["power"] == expect["power"]
    if "display" in expect:
        assert value["display"] == expect["display"]
    if "support_status" in expect:
        assert result["support_status"] == expect["support_status"]
    if "support_resolution" in expect:
        assert result["support_resolution"] == expect["support_resolution"]
    if "application" in expect:
        assert value["application"] == expect["application"]
    if "assumption_coverage" in expect:
        assert value["assumption_coverage"] == expect["assumption_coverage"]
    if "claim_outcomes" in expect:
        assert {row["id"]: row["outcome"] for row in value["claims"]} == expect["claim_outcomes"]
    for blocker in expect.get("blockers_include", []):
        assert blocker in result["blockers"]


@pytest.mark.parametrize("case", MALFORMED, ids=[case["id"] for case in MALFORMED])
def test_fixture_malformed_case_refuses_with_named_code(case):
    with pytest.raises(ValueError) as refusal:
        protocol_statistics.check("binomial_design", case["data"], case["claims"])
    assert str(refusal.value) == case["refusal"]


CLAIMLESS_CASES = [case for case in CASES if not case["claims"]]


@pytest.mark.parametrize("case", CLAIMLESS_CASES, ids=[case["id"] for case in CLAIMLESS_CASES])
def test_evaluate_equals_check_with_no_claims(case):
    assert protocol_statistics.evaluate("binomial_design", case["data"]) == protocol_statistics.check(
        "binomial_design", case["data"], []
    )


# ----------------------------------------------------------------------------------------------------
# Authored MUST-NOT and boundary tests (direct calls).
# ----------------------------------------------------------------------------------------------------


def test_must_not_k_minus_one_for_sta1():
    at_k2 = protocol_statistics.check("binomial_design", _data(n=2, k=2), [])
    at_k1 = protocol_statistics.check("binomial_design", _data(n=2, k=1), [])
    assert at_k2["value"]["null_rejection_probability"] == "1/4"
    assert at_k2["value"]["power"] == "9/16"
    assert at_k1["value"]["null_rejection_probability"] == "3/4"
    assert at_k1["value"]["power"] == "15/16"


def test_must_not_lower_tail_for_upper_tail():
    # Pr(X >= 1) = 3/4 for n=2, p=1/2; the lower tail Pr(X <= 0) = 1/4 is the wrong event.
    result = protocol_statistics.check("binomial_design", _data(n=2, k=1), [])
    assert result["value"]["null_rejection_probability"] == "3/4"
    assert result["value"]["null_rejection_probability"] != "1/4"


def test_must_not_compare_display_string():
    # n=10, k=7, p0=1/2: exact tail 11/64 = 0.171875; display "0.1719" rounds up past the claim bound 0.17188.
    claims = [
        {
            "id": "exact-le",
            "quantity": "null_rejection_probability",
            "comparison": "<=",
            "value": "4297/25000",
        },
        {
            "id": "exact-ge",
            "quantity": "null_rejection_probability",
            "comparison": ">=",
            "value": "4297/25000",
        },
    ]
    result = protocol_statistics.check("binomial_design", _data(n=10, k=7, p0="1/2", p1="7/10"), claims)
    assert result["value"]["display"]["null_rejection_probability"] == "0.1719"
    assert {row["id"]: row["outcome"] for row in result["value"]["claims"]} == {
        "exact-le": "satisfied",
        "exact-ge": "not_satisfied",
    }


@pytest.mark.parametrize("field", ["n", "critical_count"])
def test_must_not_accept_bool_as_count(field):
    data = _data(n=2, k=2)
    data[field] = True
    expected = "binomial_invalid_n" if field == "n" else "binomial_invalid_critical_count"
    with pytest.raises(ValueError) as refusal:
        protocol_statistics.check("binomial_design", data, [])
    assert str(refusal.value) == expected


def test_must_not_accept_float_probability():
    data = _data()
    data["p0"] = 0.5
    with pytest.raises(ValueError) as refusal:
        protocol_statistics.check("binomial_design", data, [])
    assert str(refusal.value) == "binomial_invalid_rational"


def test_must_not_report_supplied_alpha_as_computed_type_one_error():
    alpha_claim = [
        {"id": "alpha", "quantity": "null_rejection_probability", "comparison": "<=", "value": "0"}
    ]
    with_claim = protocol_statistics.check("binomial_design", _data(n=2, k=2), alpha_claim)
    without_claim = protocol_statistics.check("binomial_design", _data(n=2, k=2), [])
    assert with_claim["value"]["null_rejection_probability"] == "1/4"
    assert without_claim["value"]["null_rejection_probability"] == "1/4"
    assert with_claim["value"]["claims"][0]["computed"] == "1/4"
    assert with_claim["value"]["claims"][0]["outcome"] == "not_satisfied"
    assert with_claim["value"]["display"] == without_claim["value"]["display"]


def test_missing_alignment_keeps_arithmetic_and_withholds_application():
    data = _data(assumptions=_all_roles()[:2])
    result = protocol_statistics.check("binomial_design", data, [])
    assert result["value"]["null_rejection_probability"] == "1/4"
    assert result["value"]["power"] == "9/16"
    assert result["support_status"] == "known"
    assert result["support_resolution"] == "unresolved"
    assert result["value"]["application"] == {"code": "withheld", "reasons": ["assumption_missing:alignment"]}
    assert "binomial_assumption_missing:alignment" in result["blockers"]


def test_must_not_report_missing_alignment_as_proposed():
    # A missing role is an unresolved binding, not a proposed declaration; the declared status stays known.
    result = protocol_statistics.check("binomial_design", _data(assumptions=_all_roles()[:2]), [])
    assert result["support_status"] != "proposed"
    assert result["support_status"] == "known"
    assert result["support_resolution"] == "unresolved"


def test_proposed_alignment_is_proposed_with_resolved_resolution():
    result = protocol_statistics.check(
        "binomial_design", _data(assumptions=_all_roles(alignment={"status": "proposed"})), []
    )
    assert result["support_status"] == "proposed"
    assert result["support_resolution"] == "resolved"


def test_unsupported_model_returns_no_probabilities_and_no_claims_evaluated():
    data = _data()
    data["model"] = "exponential_time_to_event"
    claims = [{"id": "power", "quantity": "power", "comparison": ">=", "value": "1/2"}]
    result = protocol_statistics.check("binomial_design", data, claims)
    assert result["code"] == "unsupported_method"
    assert result["support_status"] is None
    assert result["support_resolution"] is None
    assert result["determining_ids"] == []
    assert result["blockers"] == ["binomial_unsupported_method"]
    assert "null_rejection_probability" not in result["value"]
    assert "power" not in result["value"]
    assert "claims" not in result["value"]
    assert result["value"]["computed"] is False


def test_unsupported_model_still_validates_probabilities():
    data = _data(n=0)
    data["model"] = "exponential_time_to_event"
    with pytest.raises(ValueError) as refusal:
        protocol_statistics.check("binomial_design", data, [])
    assert str(refusal.value) == "binomial_invalid_n"


def test_input_is_not_mutated():
    data = _data(n=10, k=7, p0="1/2", p1="7/10")
    claims = [{"id": "a", "quantity": "power", "comparison": ">=", "value": "1/2"}]
    before_data, before_claims = copy.deepcopy(data), copy.deepcopy(claims)
    protocol_statistics.check("binomial_design", data, claims)
    protocol_statistics.evaluate("binomial_design", data)
    assert data == before_data
    assert claims == before_claims


@pytest.mark.parametrize("n", range(1, 31))
def test_work_used_is_within_reservation(n):
    for k in range(0, n + 2):
        for p0, p1 in (("1/2", "3/4"), ("0", "1")):
            data = _data(n=n, k=k, p0=p0, p1=p1)
            reserved = protocol_statistics.work_reservation(data)
            result = protocol_statistics.check("binomial_design", data, [])
            work = result["value"]["work"]
            assert reserved == 12 * (n + 2)
            assert work["reserved"] == reserved
            assert work["used"] <= reserved


def test_null_tail_is_upper_tail_and_k_zero_is_one():
    assert (
        protocol_statistics.evaluate("binomial_design", _data(n=3, k=0, p0="0", p1="1"))["value"][
            "null_rejection_probability"
        ]
        == "1"
    )
    assert (
        protocol_statistics.evaluate("binomial_design", _data(n=3, k=4, p0="0", p1="1"))["value"]["power"]
        == "0"
    )


def test_display_rounds_exact_ties_half_even():
    # n=5, p0=1/2: tail(5) = 1/32 = 0.03125 -> 312.5 scaled -> 312 (even); tail(1) = 31/32 -> 9687.5 -> 9688.
    low = protocol_statistics.check("binomial_design", _data(n=5, k=5, p0="1/2", p1="3/4"), [])
    high = protocol_statistics.check("binomial_design", _data(n=5, k=1, p0="1/2", p1="3/4"), [])
    assert low["value"]["display"]["null_rejection_probability"] == "0.0312"
    assert high["value"]["display"]["null_rejection_probability"] == "0.9688"


def test_precheck_bit_ceiling_returns_limit_without_probabilities(monkeypatch):
    monkeypatch.setattr(protocol_statistics, "MAX_INTERMEDIATE_BITS", 10)
    result = protocol_statistics.check(
        "binomial_design",
        _data(n=10, k=7, p0="1/2", p1="7/10"),
        [{"id": "a", "quantity": "power", "comparison": ">=", "value": "1/2"}],
    )
    assert result["code"] == "limit"
    assert result["support_status"] is None
    assert result["support_resolution"] is None
    assert result["value"]["null_rejection_probability"] is None
    assert result["value"]["power"] is None
    assert result["value"]["display"] is None
    assert result["value"]["claims"][0]["outcome"] == "limit"
    assert "binomial_bit_limit" in result["blockers"]
    assert result["value"]["work"] == {"reserved": 144, "used": 0, "max_bits": 10}


def test_running_bit_ceiling_returns_limit_with_work_already_charged(monkeypatch):
    # Force past the precheck so the per-operation ceiling is what stops the computation.
    monkeypatch.setattr(protocol_statistics, "_estimated_bits", lambda n, p0, p1: 0)
    monkeypatch.setattr(protocol_statistics, "MAX_INTERMEDIATE_BITS", 8)
    result = protocol_statistics.check("binomial_design", _data(n=10, k=7, p0="1/2", p1="7/10"), [])
    assert result["code"] == "limit"
    assert result["value"]["null_rejection_probability"] is None
    assert result["value"]["power"] is None
    assert 0 < result["value"]["work"]["used"] <= result["value"]["work"]["reserved"]
    assert result["value"]["work"]["max_bits"] == 8


def test_interpolated_status_gives_interpolated_support_when_all_roles_accepted():
    data = _data(assumptions=_all_roles(iid_binary={"status": "interpolated"}))
    result = protocol_statistics.check("binomial_design", data, [])
    assert result["support_status"] == "interpolated"
    assert result["value"]["application"] == {"code": "not_withheld_by_assumptions", "reasons": []}


def test_unresolved_assumption_keeps_arithmetic_and_withholds_application():
    data = _data(assumptions=_all_roles(fixed_n={"resolution": "unresolved"}))
    result = protocol_statistics.check("binomial_design", data, [])
    assert result["code"] == "computed"
    assert result["support_status"] == "known"
    assert result["support_resolution"] == "unresolved"
    assert result["value"]["application"]["code"] == "withheld"
    assert result["value"]["application"]["reasons"] == ["assumption_not_accepted:user:fixed_n fixture"]


def test_repeated_role_with_distinct_refs_is_allowed():
    extra = _assumption("fixed_n", ref="user:second fixed_n statement")
    result = protocol_statistics.check("binomial_design", _data(assumptions=_all_roles() + [extra]), [])
    assert result["value"]["assumption_coverage"] == {
        "fixed_n": "declared",
        "iid_binary": "declared",
        "alignment": "declared",
    }
    assert result["determining_ids"] == [
        "user:fixed_n fixture",
        "user:iid_binary fixture",
        "user:alignment fixture",
        "user:second fixed_n statement",
    ]


def test_examples_run_through_check_and_evaluate_without_mutation():
    example = protocol_statistics.EXAMPLES["binomial_design"]
    before = copy.deepcopy(example)
    checked = protocol_statistics.check("binomial_design", example, [])
    evaluated = protocol_statistics.evaluate("binomial_design", example)
    assert example == before
    assert checked["code"] == "computed"
    assert checked["value"]["null_rejection_probability"] == "1/4"
    assert checked["value"]["power"] == "9/16"
    assert checked == evaluated


def test_unknown_kind_refuses_for_check_and_evaluate():
    with pytest.raises(ValueError) as check_refusal:
        protocol_statistics.check("binomial_other", _data(), [])
    with pytest.raises(ValueError) as evaluate_refusal:
        protocol_statistics.evaluate("binomial_other", _data())
    assert str(check_refusal.value) == "unsupported_binomial_kind"
    assert str(evaluate_refusal.value) == "unsupported_binomial_kind"
