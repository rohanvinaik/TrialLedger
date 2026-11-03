"""Rejected observations constrain P AND NOT E; they never assert a universal exclusion of P.

All examples are invented typed premises. A separate four-row Boolean truth-table oracle checks every
pair of two-variable eligibility/profile functions, including inconsistent profiles and candidates.
"""

import json
from dataclasses import replace
from itertools import product

import pytest

from TrialLedger.layer2 import run
from TrialLedger.layer2.assertions import (
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
    Value,
    canonical,
)
from TrialLedger.layer2.entail import (
    ENTAILED,
    INCONSISTENT,
    OUT_OF_SCOPE,
    REFUTED,
    UNDETERMINED,
    UNSUPPORTED_QUERY,
    Context,
    decide,
    eligibility_witness,
    rejected_outcome,
)


def fact(key):
    return Literal(Subject("participant"), Predicate("condition_status", key), Value("boolean"))


def rule(identity, body, **fields):
    options = {"rule": Rule("invented", "1"), "status": "known", "resolution": "resolved", **fields}
    return ScopedAssertion(identity, f"invented:{identity}", "required", body, **options)


A, B = fact("A"), fact("B")


@pytest.mark.parametrize(
    ("eligible", "ineligible", "expected"),
    [
        (True, True, UNDETERMINED),
        (True, False, REFUTED),
        (False, True, ENTAILED),
        (False, False, UNSUPPORTED_QUERY),
        (None, True, UNDETERMINED),
        (True, None, UNDETERMINED),
        (None, False, UNDETERMINED),
        (False, None, UNDETERMINED),
        (None, None, UNDETERMINED),
    ],
)
def test_rejected_outcome_requires_the_correct_satisfiable_signs(eligible, ineligible, expected):
    """Positive: either feasible rejection survives; negative: no limit or impossible profile refutes E."""
    assert rejected_outcome(eligible, ineligible) == expected


def test_rejected_partial_profile_can_fail_an_unreported_requirement():
    """Positive: A may fail B; negative: rejection of A does not license NOT A or rule out A AND B."""
    candidate = (rule("a", A), rule("b", B))
    partial = eligibility_witness(candidate, A, direction="rejected")
    assert partial.result == UNDETERMINED
    assert partial.blockers == ("undecided_by_constraints",)
    assert partial.proof == ("a", "b")
    assert eligibility_witness(candidate, AllOf((A, Not(B))), direction="rejected").result == ENTAILED
    assert eligibility_witness(candidate, AllOf((A, B)), direction="rejected").result == REFUTED
    assert decide(candidate, Not(A)).result == REFUTED


def test_rejected_profile_need_not_share_a_variable_with_the_candidate():
    candidate = (rule("b", B),)
    result = eligibility_witness(candidate, A, direction="rejected")
    assert result.result == UNDETERMINED and result.proof == ("b",)
    assert eligibility_witness(candidate, Not(B), direction="rejected").result == ENTAILED
    assert eligibility_witness(candidate, B, direction="rejected").result == REFUTED


def test_empty_candidate_cannot_explain_any_rejection():
    result = eligibility_witness((), A, direction="rejected")
    assert (result.result, result.status, result.proof, result.blockers) == (REFUTED, "known", (), ())
    assert eligibility_witness((), AllOf((A, Not(A))), direction="rejected").result == UNSUPPORTED_QUERY


def test_numeric_rejected_witness_retains_the_exact_measurement_and_boundary():
    def ps(comparison, number, key="WHO_PS"):
        return Literal(
            Subject("participant"),
            Predicate("measurement", key),
            Value("quantity", comparison, number=number),
        )

    candidate = (rule("ps", ps("le", 1)),)
    assert eligibility_witness(candidate, ps("eq", 2), direction="rejected").result == ENTAILED
    assert eligibility_witness(candidate, ps("eq", 1), direction="rejected").result == REFUTED
    assert eligibility_witness(candidate, ps("ge", 1), direction="rejected").result == UNDETERMINED
    assert eligibility_witness(candidate, ps("eq", 2, "ECOG"), direction="rejected").result == UNDETERMINED


def test_candidate_inconsistency_is_independent_of_the_profile():
    candidate = (rule("a", A), rule("not-a", Not(A)), rule("b", B))
    result = eligibility_witness(candidate, B, direction="rejected")
    assert result.result == INCONSISTENT and result.proof == ("a", "not-a")
    impossible = eligibility_witness((rule("a", A),), AllOf((A, Not(A))), direction="rejected")
    assert impossible.result == UNSUPPORTED_QUERY and impossible.blockers == ("profile_inconsistent",)


def test_rejected_witness_preserves_scope_and_all_unsettled_premises():
    candidate = (rule("a", A, cohort=Scope("cohort_ref", "A")),)
    assert eligibility_witness(candidate, A, Context(cohort="B"), "rejected").result == OUT_OF_SCOPE
    assert eligibility_witness(candidate, A, direction="rejected").blockers == ("open_scope:cohort_ref:A",)
    base = rule("b", B)
    for open_rule, blocker in (
        (replace(base, status="proposed"), "proposed_refused:b"),
        (replace(base, resolution="unresolved"), "unresolved_assertion:b"),
        (replace(base, resolution="conflicting"), "conflicting:b"),
        (replace(base, rule=UNRESOLVED_RULE), "unresolved_rule:b"),
        (replace(base, body=Opaque("missing-piece")), "opaque:missing-piece"),
    ):
        result = eligibility_witness((rule("a", A), open_rule), Not(A), direction="rejected")
        assert result.result == UNDETERMINED and result.blockers == (blocker,)


def test_proof_standing_never_promotes_a_necessary_interpolated_constraint():
    candidate = (rule("a", A), rule("b", B, status="interpolated"))
    all_eligible = eligibility_witness(candidate, AllOf((A, B)), direction="rejected")
    assert (all_eligible.result, all_eligible.status, all_eligible.proof) == (
        REFUTED,
        "interpolated",
        ("a", "b"),
    )
    all_rejected = eligibility_witness(candidate, Not(A), direction="rejected")
    assert (all_rejected.result, all_rejected.status, all_rejected.proof) == (ENTAILED, "known", ("a",))
    necessary = eligibility_witness(candidate, Not(B), direction="rejected")
    assert necessary.result == ENTAILED and necessary.status == "interpolated" and necessary.proof == ("b",)


def test_conditional_candidate_does_not_imply_its_antecedent():
    candidate = (rule("conditional-b", B, applicability=A),)
    assert eligibility_witness(candidate, B, direction="rejected").result == REFUTED
    assert eligibility_witness(candidate, Not(B), direction="rejected").result == UNDETERMINED
    assert eligibility_witness(candidate, AllOf((A, Not(B))), direction="rejected").result == ENTAILED
    assert eligibility_witness(candidate, Not(A), direction="rejected").result == REFUTED


def test_full_negative_search_abstains_at_the_bound_without_discarding_a_candidate():
    # Each disconnected requirement fits bound 2; the whole candidate and profile require more cells.
    candidate = (rule("a", A), rule("b", B))
    result = eligibility_witness(candidate, A, direction="rejected", bound=2)
    assert (result.result, result.proof, result.blockers) == (UNDETERMINED, (), ("resource_bound",))
    assert eligibility_witness(candidate, A, direction="rejected", bound=4).result == UNDETERMINED


def test_accepted_direction_is_exactly_the_existing_decision():
    for candidate in ((), (rule("a", A),), (rule("a", A), rule("b", B, status="proposed"))):
        for profile in (A, Not(A), B, AllOf((A, B)), "not a proposition", Opaque("unknown")):
            assert eligibility_witness(candidate, profile) == decide(candidate, profile)
    with pytest.raises(ModelError, match="witness_direction_outside_vocabulary"):
        eligibility_witness((), A, direction="screened")
    for bound in (0, -1, True, 1.5, None):
        with pytest.raises(ModelError, match="invalid_resource_bound"):
            eligibility_witness((), A, direction="rejected", bound=bound)
    with pytest.raises(ModelError, match="duplicate_assertion_id"):
        eligibility_witness((rule("a", A), rule("a", B)), A, direction="rejected")


@pytest.mark.parametrize("direction", ["accepted", "rejected"])
def test_impossible_profile_is_not_evidence_against_a_candidate_in_either_direction(direction):
    profile = AllOf((A, Not(A)))
    for candidate in ((), (rule("a", A),), (rule("b", B),)):
        result = eligibility_witness(candidate, profile, direction=direction)
        assert result.result == UNSUPPORTED_QUERY and result.blockers == ("profile_inconsistent",)
    # Candidate inconsistency remains independently material, even beside a malformed observation.
    contradictory = (rule("a", A), rule("not-a", Not(A)))
    assert eligibility_witness(contradictory, profile, direction=direction).result == INCONSISTENT


def test_intrinsic_profile_resource_limit_never_becomes_an_accepted_witness():
    wide = AllOf((A, B))
    result = eligibility_witness((), wide, bound=2)
    assert result.result == UNDETERMINED and result.blockers == ("resource_bound",)
    assert eligibility_witness((), wide, bound=4) == decide((), wide, bound=4)


def _truth_function(mask):
    terms = [
        AllOf((A if a else Not(A), B if b else Not(B)))
        for index, (a, b) in enumerate(product((False, True), repeat=2))
        if mask & (1 << index)
    ]
    if not terms:
        return AllOf((A, Not(A)))
    return terms[0] if len(terms) == 1 else AnyOf(tuple(terms))


def test_all_two_variable_truth_functions_against_an_independent_small_model():
    universe = set(range(4))
    for eligibility_mask, profile_mask in product(range(16), repeat=2):
        eligible = {row for row in universe if eligibility_mask & (1 << row)}
        profile = {row for row in universe if profile_mask & (1 << row)}
        if not eligible:
            expected = INCONSISTENT
        elif not profile:
            expected = UNSUPPORTED_QUERY
        elif not profile - eligible:
            expected = REFUTED
        elif not profile & eligible:
            expected = ENTAILED
        else:
            expected = UNDETERMINED
        result = eligibility_witness(
            (rule("e", _truth_function(eligibility_mask)),),
            _truth_function(profile_mask),
            direction="rejected",
        )
        assert result.result == expected, (eligibility_mask, profile_mask, result)


def _model(value):
    return json.loads(canonical(value))


def _rejected_request(profile=A):
    return {
        "operation": "design_bounds",
        "study_ref": "invented:screening-log/version-1",
        "query": _model(B),
        "candidates": [
            {"id": "only-a", "assertions": [_model(rule("a", A))]},
            {"id": "a-and-b", "assertions": [_model(rule("a", A)), _model(rule("b", B))]},
            {"id": "unrestricted", "assertions": []},
        ],
        "observations": [
            {
                "id": "screened-out-a",
                "count": 2,
                "denominator": 10,
                "population": "invented:screened/version-1",
                "direction": "rejected",
                "body": _model(profile),
                "context": {},
                "status": "known",
                "basis": ["invented:screening-log/row-2"],
                "bridge": {
                    "status": "interpolated",
                    "resolution": "resolved",
                    "max_exceptions": 0,
                    "basis": ["user:invented-profile-and-rejection-assessment-aligned"],
                },
            }
        ],
    }


def test_public_design_bounds_uses_partial_rejected_profiles_without_universal_exclusion():
    request = _rejected_request()
    answer = run(request)
    assert answer["code"] == "complete", answer
    result = answer["result"]
    assert result["remaining"] == ["a-and-b"]
    assert [row["state"] for row in result["candidates"]] == ["ruled_out", "not_ruled_out", "ruled_out"]
    observation = result["candidates"][1]["observations"][0]
    assert observation["direction"] == "rejected"
    assert observation["decision"]["result"] == UNDETERMINED
    assert observation["decision"]["blockers"] == ("undecided_by_constraints",)
    assert result["consequence"]["result"] == ENTAILED and result["consequence"]["status"] == "interpolated"
    # The surviving design still requires A; observed rejection of partial A did not turn it into NOT A.
    request["query"] = _model(Not(A))
    assert run(request)["result"]["consequence"]["result"] == REFUTED
    request["observations"][0]["bridge"]["status"] = "proposed"
    proposed = run(request)["result"]
    assert len(proposed["remaining"]) == 3 and proposed["consequence"]["result"] == UNDETERMINED


@pytest.mark.parametrize("direction", ["accepted", "rejected"])
def test_public_design_bounds_impossible_profile_remains_unresolved_not_exclusion(direction):
    request = _rejected_request(AllOf((A, Not(A))))
    request["observations"][0]["direction"] = direction
    answer = run(request)
    assert answer["code"] == "complete", answer
    result = answer["result"]
    assert result["remaining"] == ["only-a", "a-and-b", "unrestricted"]
    assert result["consequence"]["result"] == UNDETERMINED
    for candidate in result["candidates"]:
        assert candidate["state"] == "unresolved"
        decision = candidate["observations"][0]["decision"]
        assert decision["result"] == UNSUPPORTED_QUERY and decision["blockers"] == ("profile_inconsistent",)


def test_public_rejected_count_interval_uses_only_the_guaranteed_lower_count():
    request = _rejected_request()
    observation = request["observations"][0]
    del observation["count"]
    observation.update(count_lower=0, count_upper=2)
    result = run(request)["result"]
    assert len(result["remaining"]) == 3
    assert result["candidates"][0]["observations"][0]["bounds"] == {"lower": 0, "upper": 2}
    observation["count_lower"] = 1
    assert run(request)["result"]["remaining"] == ["a-and-b"]
