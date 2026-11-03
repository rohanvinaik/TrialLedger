"""Authored positive and MUST-NOT intents: a hypothetical witness is a request for evidence, never evidence.

Every check reuses the existing participant-witness engine and design-bounds verdict, so each returned row is
round-tripped through the real `design_bounds` consumer. All study values, rules and markers are invented.
"""

import copy
import json

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import run
from TrialLedger.layer2.evidence_requests import (
    LIMITS,
    dominated,
    evaluate,
    family_state,
    output_state,
    pair_outcome,
    pair_relation,
    required_premises,
    seek,
)

PARTICIPANT = a.Subject("participant")


def literal(key, value, polarity="positive"):
    kind = "measurement" if value.kind in ("quantity", "interval") else "demographic"
    return a.Literal(PARTICIPANT, a.Predicate(kind, key), value, polarity)


def required(identity, body, status="known"):
    rule = a.Rule("invented", "1", warrants=("user:invented",))
    assertion = a.ScopedAssertion(
        identity, "user:invented", "required", body, rule=rule, status=status, resolution="resolved"
    )
    return json.loads(a.canonical(assertion))


def variable(identity, key, kind, domain):
    return {
        "id": identity,
        "subject": json.loads(a.canonical(PARTICIPANT)),
        "predicate": json.loads(a.canonical(a.Predicate(kind, key))),
        "time": None,
        "domain": domain,
    }


ADULT = literal("age", a.Value("quantity", "ge", number=18.0, unit="years"))
ECOG_2 = literal("ecog", a.Value("quantity", "le", number=2.0, unit="ECOG"))
ECOG_3 = literal("ecog", a.Value("quantity", "le", number=3.0, unit="ECOG"))
MARKER = literal("marker", a.Value("boolean", "eq"))
ECOG = variable(
    "ecog", "ecog", "measurement", {"kind": "integer", "unit": "ECOG", "minimum": 0, "maximum": 5}
)
MARKER_VAR = variable("marker", "marker", "demographic", {"kind": "boolean"})
AGE = variable(
    "age",
    "age",
    "measurement",
    {"kind": "continuous", "unit": "years", "minimum": 0, "maximum": None, "cut_points": []},
)


def request(candidates, survivors=None, variables=(ECOG, MARKER_VAR, AGE), **extra):
    body = {
        "operation": "evidence_requests",
        "study_ref": "invented:evidence-requests",
        "candidates": [{"id": identity, "assertions": rows} for identity, rows in candidates.items()],
        "survivors": list(candidates) if survivors is None else survivors,
        "survival_basis": ["invented:design_bounds-remaining"],
        "variables": list(variables),
    }
    body.update(extra)
    return body


@pytest.fixture
def handoff():
    """The handoff's clinical example: adult ECOG <=2, with or without a marker requirement."""
    return request(
        {
            "A": [required("A-age", ADULT), required("A-ecog", ECOG_2)],
            "B": [required("B-age", ADULT), required("B-ecog", ECOG_2), required("B-marker", MARKER)],
        }
    )


def consumer_states(source, row, survivors):
    """What the existing design_bounds consumer concludes from this hypothetical row, supplied as evidence."""
    observation = {
        "id": "hypothetical",
        "count": 1,
        "denominator": 1,
        "population": "hypothetical",
        "body": row["profile"],
        "context": {},
        "status": "known",
        "basis": ["roundtrip"],
        "direction": row["sign"],
        "bridge": {"status": "known", "resolution": "resolved", "max_exceptions": 0, "basis": ["roundtrip"]},
    }
    reply = run(
        {
            "operation": "design_bounds",
            "study_ref": source["study_ref"],
            "candidates": [c for c in source["candidates"] if c["id"] in survivors],
            "observations": [observation],
            "query": row["profile"],
            "bound": row["scope"]["bound"],
        }
    )
    assert reply["code"] == "complete", reply["problems"]
    return {c["id"]: c["observations"][0]["state"] for c in reply["result"]["candidates"]}


# --- pure decisions ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("count", "state"), [(0, "conflict"), (1, "single_survivor"), (2, "searched"), (9, "searched")]
)
def test_family_state_names_conflict_single_and_searched(count, state):
    assert family_state(count) == state


@pytest.mark.parametrize(
    ("first", "second", "relation"),
    [
        ("ruled_out", "not_ruled_out", "separates_first"),
        ("not_ruled_out", "ruled_out", "separates_second"),
        ("ruled_out", "ruled_out", "both_eliminated"),
        ("not_ruled_out", "not_ruled_out", "neither"),
        ("unresolved", "ruled_out", "undecided"),
        ("not_ruled_out", "unresolved", "undecided"),
        ("inconsistent", "not_ruled_out", "undecided"),
    ],
)
def test_pair_relation_separates_only_one_elimination_beside_one_accommodation(first, second, relation):
    assert pair_relation(first, second) == relation


def test_pair_outcome_never_claims_absence_after_unfinished_or_undecided_work():
    assert pair_outcome(1, False, True, False) == "separated"
    assert pair_outcome(0, False, False, True) == "search_incomplete"
    assert pair_outcome(0, True, True, True) == "search_incomplete"
    assert pair_outcome(0, True, False, False) == "not_separated_in_declared_variables"
    assert pair_outcome(0, True, False, True) == "no_separator"


def test_output_state_separates_truncation_from_search():
    assert output_state(0, 0) == "complete"
    assert output_state(4, 4) == "complete"
    assert output_state(4, 3) == "truncated"


def test_rejected_eliminations_need_complete_candidate_eligibility_but_accepted_ones_do_not():
    accepted = required_premises("accepted", ("A",))
    rejected = required_premises("rejected", ("A", "C"))
    assert accepted == (
        "eligibility_attribution:accepted",
        "accepted_resolved_bridge",
        "count_above_exception_allowance",
    )
    assert rejected[-2:] == ("complete_candidate_eligibility:A", "complete_candidate_eligibility:C")
    assert not any(p.startswith("complete_candidate_eligibility") for p in accepted)


def test_seek_names_screening_records_only_for_rejections_and_never_claims_they_exist():
    assert "screening" in seek("rejected") and "never" in seek("rejected")
    assert "screening" not in seek("accepted") and "eligibility bridge" in seek("accepted")


def test_dominated_uses_found_subsets_not_one_literal_weakenings():
    small, large = frozenset({"x"}), frozenset({"x", "y", "z"})
    assert dominated(large, (small,))
    assert not dominated(small, (small,))
    assert not dominated(large, (frozenset({"y", "w"}),))


# --- the clinical example and the real consumer -------------------------------------------------------------


def test_handoff_example_distinguishes_by_both_signs_without_inventing_marker_status(handoff):
    result = evaluate(handoff)
    assert result["family"] == "searched" and result["search"]["state"] == "complete"
    rows = result["requests"]
    accepted = [r for r in rows if r["sign"] == "accepted"]
    rejected = [r for r in rows if r["sign"] == "rejected"]
    assert accepted and accepted[0]["cells"] == {"marker": "does not hold"}
    assert accepted[0]["eliminates"] == ["B"] and accepted[0]["accommodates"] == ["A"]
    partial = [r for r in rejected if "marker" not in r["specified"]]
    assert partial, "a partial rejected profile with marker unspecified must still separate"
    assert all(r["eliminates"] == ["A"] and r["accommodates"] == ["B"] for r in partial)
    assert all("marker" not in json.dumps(r["profile"]) for r in partial)


@pytest.mark.parametrize(
    "candidates",
    [
        {
            "A": [required("A-age", ADULT), required("A-ecog", ECOG_2)],
            "B": [required("B-age", ADULT), required("B-ecog", ECOG_2), required("B-marker", MARKER)],
        },
        {"low": [required("low", ECOG_2)], "high": [required("high", ECOG_3)]},
        {
            "inclusive": [required("ge18", ADULT)],
            "strict": [
                required("gt18", literal("age", a.Value("quantity", "gt", number=18.0, unit="years")))
            ],
            "none": [required("any-ecog", ECOG_3)],
        },
    ],
)
def test_every_returned_request_matches_the_existing_design_bounds_consumer(candidates):
    source = request(candidates, limits={"max_requests_per_pair": 20, "max_requests": 200})
    result = evaluate(source)
    assert result["requests"]
    for row in result["requests"]:
        states = consumer_states(source, row, result["survivors"])
        assert all(states[c] == "ruled_out" for c in row["eliminates"])
        assert all(states[c] == "not_ruled_out" for c in row["accommodates"])


def test_accepted_witness_separates_cutoffs_and_open_boundaries_are_exact():
    cutoffs = evaluate(request({"low": [required("low", ECOG_2)], "high": [required("high", ECOG_3)]}))
    first = cutoffs["requests"][0]
    assert (
        first["sign"] == "accepted"
        and first["cells"] == {"ecog": "= 3 ECOG"}
        and first["eliminates"] == ["low"]
    )
    strict = literal("age", a.Value("quantity", "gt", number=18.0, unit="years"))
    boundary = evaluate(
        request({"ge": [required("ge", ADULT)], "gt": [required("gt", strict)]}, variables=(AGE,))
    )
    cells = [r["cells"]["age"] for r in boundary["requests"] if r["sign"] == "accepted"]
    assert cells == ["= 18 years"], "only the exact threshold separates inclusive from strict"


def test_mixed_signs_both_appear_with_sign_specific_premises(handoff):
    rows = evaluate(handoff)["requests"]
    assert {r["sign"] for r in rows} == {"accepted", "rejected"}
    for row in rows:
        complete = [p for p in row["required_premises"] if p.startswith("complete_candidate_eligibility:")]
        if row["sign"] == "rejected":
            assert complete == [f"complete_candidate_eligibility:{c}" for c in row["eliminates"]]
        else:
            assert not complete


# --- family states ---------------------------------------------------------------------------------------


def test_zero_one_and_equivalent_survivors(handoff):
    empty = evaluate(dict(handoff, survivors=[]))
    assert empty["family"] == "conflict" and empty["requests"] == [] and empty["pairs"] == []
    single = evaluate(dict(handoff, survivors=["A"]))
    assert single["family"] == "single_survivor" and single["requests"] == []
    twins = evaluate(
        request({"one": [required("x", ECOG_2)], "two": [required("y", ECOG_2)]}, variables=(ECOG,))
    )
    assert twins["pairs"][0]["outcome"] == "no_separator" and twins["requests"] == []


def test_inconsistent_survivor_is_reported_as_input_conflict_not_separated():
    clash = [
        required("hi", literal("ecog", a.Value("quantity", "ge", number=3.0, unit="ECOG"))),
        required("lo", ECOG_2),
    ]
    result = evaluate(request({"clash": clash, "ok": [required("ok", ECOG_2)]}, variables=(ECOG,)))
    assert result["inconsistent"] == ["clash"]
    assert result["input_conflicts"] == ["survivor_inconsistent:clash"]
    assert result["family"] == "single_survivor" and result["survivors"] == ["ok"]


# --- order, minimality and domains -----------------------------------------------------------------------


def test_order_is_least_specified_first_deterministic_and_minimal(handoff):
    source = dict(handoff, limits={"max_requests_per_pair": 20, "max_requests": 200})
    first, second = evaluate(copy.deepcopy(source)), evaluate(copy.deepcopy(source))
    assert first == second
    sizes = [r["profile_size"] for r in first["requests"]]
    assert sizes == sorted(sizes)
    rows = first["requests"]
    for row in rows:
        for other in rows:
            if other is row or other["sign"] != row["sign"] or other["eliminates"] != row["eliminates"]:
                continue
            assert not set(other["cells"].items()) < set(row["cells"].items()), (
                "superset of a found separator"
            )


def test_integer_domains_never_describe_fractional_participants():
    cutoffs = evaluate(
        request({"low": [required("low", ECOG_2)], "high": [required("high", ECOG_3)]}, variables=(ECOG,))
    )
    values = [r["profile"]["value"]["number"] for r in cutoffs["requests"]]
    assert values and all(float(v).is_integer() for v in values)
    half = literal("ecog", a.Value("quantity", "le", number=2.5, unit="ECOG"))
    result = evaluate(
        request({"half": [required("half", half)], "two": [required("two", ECOG_2)]}, variables=(ECOG,))
    )
    assert result["requests"] == []
    assert result["pairs"][0]["outcome"] == "no_separator", "no integer patient lies between 2 and 2.5"


def test_continuous_cells_respect_declared_limits_and_use_exclusive_intervals():
    bounded = dict(
        AGE, domain={"kind": "continuous", "unit": "years", "minimum": 18, "maximum": 80, "cut_points": [65]}
    )
    old = literal("age", a.Value("quantity", "le", number=65.0, unit="years"))
    result = evaluate(
        request({"any": [required("adult", ADULT)], "young": [required("le65", old)]}, variables=(bounded,)),
    )
    labels = [r["cells"]["age"] for r in result["requests"]]
    assert "between 65 and 80 years (exclusive)" in labels
    assert not any(label.startswith("<") or label.startswith(">") for label in labels)
    intervals = [
        r["profile"]["value"] for r in result["requests"] if r["profile"]["value"]["kind"] == "interval"
    ]
    assert all(v["inclusivity"] == "exclusive" for v in intervals)


def test_unrepresented_variable_is_a_translation_problem_not_absence():
    wrong_unit = dict(
        ECOG, id="ecog-score", domain={"kind": "integer", "unit": "score", "minimum": 0, "maximum": 5}
    )
    result = evaluate(
        request(
            {"low": [required("low", ECOG_2)], "high": [required("high", ECOG_3)]}, variables=(wrong_unit,)
        )
    )
    assert result["representation"]["unrepresented_variables"] == ["ecog-score"]
    assert result["pairs"][0]["outcome"] != "no_separator"
    assert "variable_unrepresented:ecog-score" in result["pairs"][0]["causes"]


def test_undeclared_constraints_limit_the_absence_claim():
    result = evaluate(
        request(
            {
                "A": [required("a", ECOG_2), required("m", MARKER)],
                "B": [
                    required("b", ECOG_2),
                    required("not-m", literal("marker", a.Value("boolean", "eq"), "negative")),
                ],
            },
            variables=(ECOG,),
        )
    )
    pair = result["pairs"][0]
    assert pair["outcome"] == "not_separated_in_declared_variables"
    assert "unsearched_constraints" in pair["causes"]


# --- limits ----------------------------------------------------------------------------------------------


def test_budget_exhaustion_is_incomplete_search_never_no_separator(handoff):
    result = evaluate(dict(handoff, limits={"max_decisions": 3}))
    assert result["search"]["state"] == "incomplete"
    assert "resource_bound:decisions" in result["search"]["causes"]
    assert all(p["outcome"] in ("separated", "search_incomplete") for p in result["pairs"])
    limited = evaluate(dict(handoff, limits={"max_profiles": 1}))
    assert "resource_bound:profiles" in limited["search"]["causes"]


def test_solver_limit_leaves_the_pair_undecided(handoff):
    result = evaluate(dict(handoff, bound=1))
    pair = result["pairs"][0]
    assert pair["outcome"] in ("separated", "search_incomplete")
    if pair["outcome"] == "search_incomplete":
        assert "resource_bound" in pair["causes"]


def test_output_truncation_counts_only_found_rows_and_leaves_search_complete(handoff):
    full = evaluate(dict(handoff, limits={"max_requests_per_pair": 20, "max_requests": 200}))
    cut = evaluate(dict(handoff, limits={"max_requests_per_pair": 20, "max_requests": 1}))
    assert cut["search"] == full["search"]
    assert cut["output"]["state"] == "truncated" and cut["output"]["returned"] == 1
    assert cut["output"]["omitted"] == full["output"]["found"] - 1
    tiny = evaluate(dict(handoff, limits={"max_bytes": 10}))
    assert tiny["output"]["returned"] == 0 and "output_limit:bytes" in tiny["output"]["causes"]


@pytest.mark.parametrize("name", sorted(LIMITS))
def test_hard_maxima_are_named_refusals(handoff, name):
    with pytest.raises(ValueError, match=f"resource_bound:evidence_requests:limits.{name}"):
        evaluate(dict(handoff, limits={name: LIMITS[name][1] + 1}))


# --- requests can never pass as evidence -------------------------------------------------------------------


def test_rows_are_structurally_unable_to_pass_as_observations(handoff):
    for row in evaluate(handoff)["requests"]:
        assert row["kind"] == "hypothetical_evidence_request" and row["observed"] is False
        assert not {"count", "bridge", "basis", "status", "denominator"} & set(row)


def test_proposed_candidate_premises_never_eliminate():
    proposed = {"low": [required("low", ECOG_2, status="proposed")], "high": [required("high", ECOG_3)]}
    result = evaluate(request(proposed, variables=(ECOG,)))
    assert not any("low" in r["eliminates"] for r in result["requests"])
    pair = result["pairs"][0]
    assert pair["outcome"] in ("separated", "search_incomplete")
    assert any(c.startswith("proposed_refused:") for c in pair["causes"]) or pair["outcome"] == "separated"


# --- named refusals ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda r: r.update(extra=1), "evidence_requests:request:unknown_field"),
        (lambda r: r.update(operation="design_bounds"), "evidence_requests:request:wrong_operation"),
        (
            lambda r: r["candidates"][0].update(signal_claims=[]),
            "evidence_requests:candidate:signal_claims_unsupported",
        ),
        (lambda r: r.update(survivors=["A", "Z"]), "evidence_requests:survivors:unknown_candidate"),
        (lambda r: r.update(survivors=["A", "A"]), "evidence_requests:survivors:duplicate_id"),
        (
            lambda r: r["candidates"].append(copy.deepcopy(r["candidates"][0])),
            "evidence_requests:candidates:duplicate_id",
        ),
        (lambda r: r.update(survival_basis=[]), "evidence_requests:survival_basis:nonempty_required"),
        (
            lambda r: r["variables"][0].update(domain={"kind": "enum_set"}),
            "evidence_requests:variable:unsupported_domain",
        ),
        (
            lambda r: r["variables"].append(dict(r["variables"][0], id="again")),
            "evidence_requests:variables:duplicate_key",
        ),
        (lambda r: r.update(signs=["refused"]), "evidence_requests:signs:unsupported_sign"),
        (lambda r: r.update(bound=0), "evidence_requests:bound:invalid_resource_bound"),
    ],
)
def test_named_refusals(handoff, mutate, code):
    broken = copy.deepcopy(handoff)
    mutate(broken)
    with pytest.raises(ValueError, match=code):
        evaluate(broken)


# --- discovery fragment ------------------------------------------------------------------------------------


def test_discovery_fragment_matches_the_validator_and_its_example_runs():
    from TrialLedger.layer2 import evidence_requests as module
    from TrialLedger.layer2 import evidence_requests_guide as guide

    shape = guide.INPUTS["evidence_requests"]
    assert set(shape["fields"]) | {"operation"} == module.FIELDS
    assert set(shape["required"]) | {"operation"} == module.REQUIRED
    assert set(guide.INPUTS["evidence_request_limits"]["fields"]) == set(module.LIMITS)
    result = evaluate(guide.example())
    rows = result["requests"]
    assert result["family"] == "searched" and result["search"]["state"] == "complete"
    accepted = [r for r in rows if r["sign"] == "accepted"]
    rejected = [r for r in rows if r["sign"] == "rejected" and "marker" not in r["specified"]]
    assert accepted[0]["eliminates"] == ["adult_scale_le_2_marker"]
    assert rejected and all(r["eliminates"] == ["adult_scale_le_2"] for r in rejected)
    outcomes = {p["outcome"] for p in result["pairs"]} | {result["family"], result["output"]["state"]}
    assert outcomes - {"searched", "complete"} <= set(guide.ANSWERS)


def test_discovery_extension_adds_one_answer_guide_entry_per_outcome():
    from TrialLedger.layer2 import evidence_requests_guide as guide

    description = {
        "availability": {"built": []},
        "question_vocabulary": [],
        "use_cases": [],
        "examples": {},
        "example_results": {},
        "answer_guide": {},
        "result_guides": {},
    }
    guide.extend(description)
    assert set(description["answer_guide"]["evidence_requests"]) == {
        "conflict",
        "single_survivor",
        "separated",
        "no_separator",
        "not_separated_in_declared_variables",
        "search_incomplete",
        "truncated",
    }
    assert description["examples"]["evidence_requests"]["operation"] == "evidence_requests"


def test_rows_record_the_solver_bound_so_a_replay_uses_the_same_limit(handoff):
    rows = evaluate(dict(handoff, bound=512))["requests"]
    assert rows and all(row["scope"]["bound"] == 512 for row in rows)
    assert all(row["scope"]["study_ref"] == handoff["study_ref"] for row in rows)


def test_evaluate_never_mutates_its_request(handoff):
    before = copy.deepcopy(handoff)
    evaluate(handoff)
    assert handoff == before
