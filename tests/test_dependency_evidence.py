"""Explicit adopted prerequisites: unavailable, missing, observed and imputed never collapse.

Invented rules only. Public evaluate/check tests are paired with direct intent tests of each atomic
decision and a finite independent enumeration of one adopted OR-of-AND dependency's availability states.
"""

import json
from copy import deepcopy
from itertools import product

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import run
from TrialLedger.layer2.dependency_evidence import (
    EXAMPLES,
    alternative_state,
    check,
    condition_join,
    evaluate,
    guard_state,
    prerequisite_state,
)


def measurement(identity, mode="observed"):
    return {"id": identity, "mode": mode}


def rule(identity="change", alternatives=None, when=None, output=None):
    return {
        "id": identity,
        "version": "invented-1",
        "output": measurement(output or identity, "derived"),
        "alternatives": alternatives
        if alternatives is not None
        else [[measurement("baseline"), measurement("week12")]],
        "when": [] if when is None else when,
    }


def data(**fields):
    return {
        "scope": "invented:cohort-a:week12",
        "version": "1",
        "rules": [rule()],
        "adopted": ["change"],
        "available": [],
        "unavailable": [],
        "conditions": {},
        **fields,
    }


@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        ([], "ready"),
        (["available"], "ready"),
        (["unknown"], "unresolved"),
        (["unavailable"], "blocked"),
        (["unknown", "unavailable"], "blocked"),
    ],
)
def test_alternative_state_is_and_with_explicit_unavailability(inputs, expected):
    """Positive: complete inputs ready; negative: unknown never becomes explicit unavailability."""
    assert alternative_state(inputs) == expected


@pytest.mark.parametrize(
    ("matches", "expected"),
    [
        ([], "active"),
        (["true"], "active"),
        (["unknown"], "unresolved"),
        (["false"], "inactive"),
        (["unknown", "false"], "inactive"),
    ],
)
def test_guard_state_requires_support_and_a_false_conjunct_defeats_unknown(matches, expected):
    assert guard_state(matches) == expected


@pytest.mark.parametrize(
    ("guard", "alternatives", "expected"),
    [
        ("inactive", ["blocked"], "inactive"),
        ("unresolved", ["ready"], "unresolved"),
        ("active", ["blocked", "ready"], "ready"),
        ("active", ["blocked"], "blocked"),
        ("active", ["blocked", "unresolved"], "unresolved"),
        ("active", [], "unresolved"),
    ],
)
def test_prerequisite_state_is_conditional_or_not_an_implicit_conjunction(guard, alternatives, expected):
    assert prerequisite_state(guard, alternatives) == expected


@pytest.mark.parametrize(
    ("current", "incoming", "expected"),
    [
        ("unknown", "true", "true"),
        ("unknown", "false", "false"),
        ("true", "unknown", "true"),
        ("false", "unknown", "false"),
        ("true", "true", "true"),
        ("false", "false", "false"),
        ("true", "false", "conflict"),
        ("false", "true", "conflict"),
        ("unknown", "unknown", "unknown"),
    ],
)
def test_condition_join_refines_unknown_and_retains_dissent(current, incoming, expected):
    assert condition_join(current, incoming) == expected


def test_missing_is_unresolved_unavailable_is_conflict_and_complete_is_consistent():
    missing = evaluate("dependencies", data(available=[measurement("baseline")]))
    assert missing["code"] == "unresolved" and missing["blockers"] == ["dependency_unresolved:change"]
    assert missing["value"]["rules"][0]["missing"] == ["week12:observed"]
    unavailable = evaluate(
        "dependencies", data(available=[measurement("baseline")], unavailable=[measurement("week12")])
    )
    assert unavailable["code"] == "conflict" and unavailable["blockers"] == ["dependency_blocked:change"]
    ready = evaluate("dependencies", data(available=[measurement("baseline"), measurement("week12")]))
    assert ready["code"] == "consistent" and ready["blockers"] == []
    assert measurement("change", "derived") in ready["value"]["available"]
    assert ready["value"]["scope"] == "invented:cohort-a:week12" and ready["value"]["version"] == "1"
    assert ready["value"]["rules"][0]["version"] == "invented-1"


def test_unadopted_rules_impose_nothing_and_no_implicit_imputation_is_created():
    no_adoption = evaluate("dependencies", data(adopted=[], unavailable=[measurement("week12")]))
    assert no_adoption["code"] == "consistent" and no_adoption["value"]["rules"] == []
    assert no_adoption["value"]["available"] == []
    imputed = evaluate(
        "dependencies", data(available=[measurement("baseline"), measurement("week12", "imputed")])
    )
    assert imputed["code"] == "unresolved"
    assert measurement("change", "derived") not in imputed["value"]["available"]
    alternatives = [
        [measurement("baseline"), measurement("week12")],
        [measurement("baseline"), measurement("week12", "imputed")],
    ]
    explicit = evaluate(
        "dependencies",
        data(
            rules=[rule(alternatives=alternatives)],
            available=[measurement("baseline"), measurement("week12", "imputed")],
            unavailable=[measurement("week12")],
        ),
    )
    assert explicit["code"] == "consistent"
    assert explicit["value"]["rules"][0]["alternatives"][0][1]["state"] == "unavailable"
    assert explicit["value"]["rules"][0]["alternatives"][1][1] == {
        "id": "week12",
        "mode": "imputed",
        "state": "available",
    }


def test_conditional_prerequisite_is_neither_unconditional_nor_silently_inactive():
    guarded = rule(when=[{"id": "on-treatment", "is": "true"}])
    for conditions, expected in (
        ({}, "unresolved"),
        ({"on-treatment": "unknown"}, "unresolved"),
        ({"on-treatment": "false"}, "consistent"),
        ({"on-treatment": "true"}, "conflict"),
    ):
        result = evaluate(
            "dependencies", data(rules=[guarded], conditions=conditions, unavailable=[measurement("week12")])
        )
        assert result["code"] == expected
        assert measurement("change", "derived") not in result["value"]["available"]
    false_guard = rule(when=[{"id": "a", "is": "true"}, {"id": "b", "is": "false"}])
    result = evaluate("dependencies", data(rules=[false_guard], conditions={"a": "false"}))
    assert result["code"] == "consistent" and result["value"]["rules"][0]["state"] == "inactive"


def test_derived_closure_is_typed_and_cycles_do_not_create_missing_seeds():
    chained = data(
        rules=[
            rule("z-first", [[measurement("seed")]], output="intermediate"),
            rule("a-second", [[measurement("intermediate", "derived")]]),
        ],
        adopted=["z-first", "a-second"],
        available=[measurement("seed")],
    )
    result = evaluate("dependencies", chained)
    assert result["code"] == "consistent"
    assert measurement("a-second", "derived") in result["value"]["available"]
    assert measurement("intermediate", "observed") not in result["value"]["available"]
    circular = data(
        rules=[rule("a", [[measurement("b", "derived")]]), rule("b", [[measurement("a", "derived")]])],
        adopted=["a", "b"],
    )
    absent = evaluate("dependencies", circular)
    assert absent["code"] == "unresolved" and absent["value"]["available"] == []
    seeded = check("dependencies", circular, [{"available": [measurement("a", "derived")]}])
    assert seeded["code"] == "consistent" and len(seeded["value"]["available"]) == 2


def test_all_candidate_claims_are_joint_and_no_dissent_overwrites_a_source():
    base = data()
    claims = [{"available": [measurement("baseline")]}, {"available": [measurement("week12")]}]
    assert all(check("dependencies", base, [claim])["code"] == "unresolved" for claim in claims)
    assert check("dependencies", base, claims)["code"] == "consistent"
    conflict = check("dependencies", base, [*claims, {"unavailable": [measurement("week12")]}])
    assert conflict["code"] == "conflict" and "availability_conflict:week12:observed" in conflict["blockers"]
    conditional = data(rules=[rule(when=[{"id": "condition", "is": "true"}])])
    disagree = [{"conditions": {"condition": "true"}}, {"conditions": {"condition": "false"}}]
    conflicting_results = []
    for ordered in (disagree, list(reversed(disagree)), [*disagree, disagree[0]]):
        result = check("dependencies", conditional, ordered)
        assert result["code"] == "conflict" and "condition_conflict:condition" in result["blockers"]
        assert result["value"]["rules"][0]["state"] == "unresolved"
        conflicting_results.append(result)
    assert conflicting_results[0] == conflicting_results[1] == conflicting_results[2]
    no_adoption = data(adopted=[], available=[measurement("baseline"), measurement("week12")])
    assert check("dependencies", no_adoption, [{"adopted": ["change"]}])["code"] == "consistent"


def test_conflicting_derived_output_is_detected_even_after_a_later_closure_pass():
    ready = data(
        available=[measurement("baseline"), measurement("week12")],
        unavailable=[measurement("change", "derived")],
    )
    result = evaluate("dependencies", ready)
    assert result["code"] == "conflict" and "availability_conflict:change:derived" in result["blockers"]


def test_one_rule_matches_an_independent_finite_model_of_alternatives():
    # Independent classification: each AND is impossible iff an explicitly unavailable member occurs;
    # ready iff every member is available; any ready OR suffices; otherwise only all-impossible conflicts.
    groups = [("a", "b"), ("c",)]
    for states in product(("available", "unavailable", "unknown"), repeat=3):
        values = dict(zip(("a", "b", "c"), states, strict=True))
        is_ready = any(all(values[item] == "available" for item in group) for group in groups)
        impossible = all(any(values[item] == "unavailable" for item in group) for group in groups)
        expected = "consistent" if is_ready else "conflict" if impossible else "unresolved"
        request = data(
            rules=[rule(alternatives=[[measurement(item) for item in group] for group in groups])],
            available=[measurement(key) for key, state in values.items() if state == "available"],
            unavailable=[measurement(key) for key, state in values.items() if state == "unavailable"],
        )
        assert evaluate("dependencies", request)["code"] == expected, states


@pytest.mark.parametrize(
    ("field", "replacement", "problem"),
    [
        ("scope", "", "not_text:scope"),
        ("version", None, "not_text:version"),
        ("available", None, "not_a_list:measurements"),
        ("adopted", ["missing"], "unknown_adopted_rule"),
        ("conditions", {"x": True}, "condition_state_outside_vocabulary"),
        ("available", [measurement("x", "estimated")], "measurement_mode_outside_vocabulary"),
        ("available", [measurement("x"), measurement("x")], "duplicate_measurement"),
        ("adopted", ["change", "change"], "duplicate_adopted_rule"),
    ],
)
def test_malformed_inputs_are_refused_by_name(field, replacement, problem):
    with pytest.raises(ValueError, match=problem):
        evaluate("dependencies", data(**{field: replacement}))


def test_closed_schemas_and_rule_limits_are_enforced_without_coercion():
    for malformed in (None, {}, {**data(), "extra": "field"}):
        with pytest.raises(ValueError):
            evaluate("dependencies", malformed)
    for malformed_rule, problem in (
        (rule(alternatives=[]), "missing_dependency_alternative"),
        ({**rule(), "output": measurement("change")}, "rule_output_not_derived"),
        (rule(when=[{"id": "x", "is": "unknown"}]), "guard_state_outside_vocabulary"),
        (rule(when=[{"id": "x", "is": "true"}, {"id": "x", "is": "false"}]), "duplicate_dependency_guard"),
    ):
        with pytest.raises(ValueError, match=problem):
            evaluate("dependencies", data(rules=[malformed_rule]))
    with pytest.raises(ValueError, match="duplicate_dependency_rule"):
        evaluate("dependencies", data(rules=[rule(), rule()]))
    with pytest.raises(ValueError, match="resource_bound"):
        evaluate("dependencies", data(available=[measurement(str(index)) for index in range(1001)]))
    with pytest.raises(ValueError, match="resource_bound:dependency_facts"):
        check(
            "dependencies",
            data(rules=[], adopted=[]),
            [
                {"available": [measurement(str(index)) for index in range(1000)]},
                {"available": [measurement("last")]},
            ],
        )
    with pytest.raises(ValueError, match="empty_dependency_claim"):
        check("dependencies", data(), [{}])
    with pytest.raises(ValueError, match="unknown_field:dependency_claim"):
        check("dependencies", data(), [{"required": []}])
    for function, args in ((evaluate, (data(),)), (check, (data(), []))):
        with pytest.raises(ValueError, match="unsupported_dependency_kind"):
            function("unknown", *args)


def test_inputs_and_example_are_not_mutated_or_shared_between_results():
    request = deepcopy(EXAMPLES["dependencies"])
    before = deepcopy(request)
    result = evaluate("dependencies", request)
    assert request == before and result["code"] == "unresolved"
    result["value"]["available"].clear()
    assert evaluate("dependencies", request)["value"]["available"] == [measurement("baseline")]


def test_public_reason_entry_retains_scope_sources_standing_and_revision():
    request = {
        "operation": "signals",
        "signals": [
            {
                "id": "visit-inputs",
                "kind": "dependencies",
                "data": deepcopy(EXAMPLES["dependencies"]),
                "support": [
                    {
                        "id": "typed-inputs",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["invented:record/version/baseline"],
                    },
                    {
                        "id": "adopted-definition",
                        "status": "interpolated",
                        "resolution": "resolved",
                        "basis": ["user:adopted-invented-change-rule"],
                    },
                ],
            }
        ],
    }
    before = deepcopy(request)
    answer = run(request)
    assert answer["code"] == "complete"
    signal = answer["result"]["signals"][0]
    assert signal["code"] == "unresolved" and signal["status"] == "interpolated"
    assert signal["basis"] == ["invented:record/version/baseline", "user:adopted-invented-change-rule"]
    assert signal["value"]["scope"] == EXAMPLES["dependencies"]["scope"]
    revised = deepcopy(request)
    revised["signals"][0]["data"]["available"].append(measurement("week12"))
    settled = run(revised)["result"]["signals"][0]
    assert settled["code"] == "consistent" and settled["status"] == "interpolated"
    revised["signals"][0]["support"][1]["status"] = "proposed"
    refused = run(revised)["result"]["signals"][0]
    assert refused["code"] == "unresolved" and refused["calculation_code"] == "consistent"
    assert "proposed_refused:visit-inputs" in refused["blockers"]
    revised["signals"][0]["support"][1].update(status="interpolated", resolution="unresolved")
    unresolved = run(revised)["result"]["signals"][0]
    assert unresolved["code"] == "unresolved" and "binding_unresolved:visit-inputs" in unresolved["blockers"]
    assert request == before


def _dependency_design_request():
    target = a.Literal(
        a.Subject("participant"), a.Predicate("condition_status", "invented-target"), a.Value("boolean")
    )

    def assertion(identity, body):
        return json.loads(
            a.canonical(
                a.ScopedAssertion(
                    identity,
                    "user:invented-candidate",
                    "required",
                    body,
                    rule=a.Rule("invented", "1"),
                    status="known",
                    resolution="resolved",
                )
            )
        )

    def claim(body):
        return {"signal": "inputs", "claim": body}

    adoption = claim({"adopted": ["change"]})
    baseline = claim({"available": [measurement("baseline")]})
    week12 = claim({"available": [measurement("week12")]})
    no_week12 = claim({"unavailable": [measurement("week12")]})
    return {
        "operation": "design_bounds",
        "study_ref": "invented:study/version-1",
        "observations": [],
        "query": json.loads(a.canonical(target)),
        "signals": [
            {
                "id": "inputs",
                "kind": "dependencies",
                "data": data(adopted=[]),
                "support": [
                    {
                        "id": "typed-source",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["invented:source/version/inputs"],
                    },
                    {
                        "id": "adoption-map",
                        "status": "interpolated",
                        "resolution": "resolved",
                        "basis": ["user:invented-adoption-binding"],
                    },
                ],
            }
        ],
        "candidates": [
            {
                "id": "joint",
                "assertions": [assertion("target", target)],
                "signal_claims": [adoption, baseline, week12],
            },
            {
                "id": "missing",
                "assertions": [assertion("not-target", a.Not(target))],
                "signal_claims": [adoption, baseline],
            },
            {
                "id": "contradiction",
                "assertions": [assertion("not-target", a.Not(target))],
                "signal_claims": [adoption, baseline, week12, no_week12],
            },
        ],
    }


def test_public_candidate_dependency_claims_are_joint_with_unknown_and_conflict_distinct():
    request = _dependency_design_request()
    before = deepcopy(request)
    answer = run(request)
    assert answer["code"] == "complete", answer
    result = answer["result"]
    assert result["remaining"] == ["joint", "missing"]
    assert [row["state"] for row in result["candidates"]] == ["not_ruled_out", "unresolved", "ruled_out"]
    checks = [row["signal_checks"][0] for row in result["candidates"]]
    assert [check["code"] for check in checks] == ["consistent", "unresolved", "conflict"]
    assert checks[0]["status"] == "interpolated"
    assert measurement("change", "derived") in checks[0]["value"]["available"]
    assert "availability_conflict:week12:observed" in checks[2]["blockers"]
    assert result["consequence"]["result"] == "UNDETERMINED"
    request["candidates"] = [request["candidates"][0], request["candidates"][2]]
    revised = run(request)["result"]
    assert revised["remaining"] == ["joint"]
    assert (
        revised["consequence"]["result"] == "ENTAILED" and revised["consequence"]["status"] == "interpolated"
    )
    assert before["signals"] == request["signals"]


@pytest.mark.parametrize(
    ("field", "value", "blocker"),
    [
        ("status", "proposed", "proposed_refused:inputs"),
        ("resolution", "unresolved", "binding_unresolved:inputs"),
    ],
)
def test_public_candidate_dependency_claims_cannot_eliminate_from_unaccepted_support(field, value, blocker):
    request = _dependency_design_request()
    request["signals"][0]["support"][1][field] = value
    result = run(request)["result"]
    assert result["remaining"] == ["joint", "missing", "contradiction"]
    assert all(row["state"] == "unresolved" for row in result["candidates"])
    contradiction = result["candidates"][2]["signal_checks"][0]
    assert contradiction["code"] == "unresolved" and contradiction["calculation_code"] == "conflict"
    assert blocker in contradiction["blockers"]
    assert result["consequence"]["result"] == "UNDETERMINED"
