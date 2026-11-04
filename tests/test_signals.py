"""Intent tests for source standing, structural substitution and public refusal boundaries."""

from __future__ import annotations

import copy
import json

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import signals, signals_guide
from TrialLedger.layer2.service import run


def measurement(unit="Years"):
    return a.Literal(
        a.Subject("participant"),
        a.Predicate("measurement", "age"),
        a.Value("quantity", "ge", number=18, unit=unit),
    )


def test_support_state_requires_each_resolved_accepted_premise():
    assert signals.support_state(["known", "interpolated"], ["resolved", "resolved"]) == "accepted"
    assert signals.support_state(["known", "proposed"], ["resolved", "resolved"]) == "proposed_refused"
    assert signals.support_state(["known"], ["conflicting"]) == "binding_unresolved"
    assert signals.support_state([], []) == "missing_support"
    assert signals.support_state(["known"], []) == "missing_support"


@pytest.mark.parametrize("kind", list(signals.MODULES))
def test_all_discovered_operator_examples_run_without_mutating_inputs(kind):
    guide = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]
    request = guide["signal_examples"][kind]
    before = copy.deepcopy(request)
    reply = run(request)
    assert reply["code"] == "complete", reply
    assert reply["result"]["signals"][0]["code"] == (
        "unresolved"
        if kind in ("dependencies", "estimand")
        else "bounded"
        if kind in ("overlap", "partition", "summary", "population")
        else "consistent"
    )
    assert request == before
    assert reply["result"]["premises"] == request["signals"]
    assert guide["operator_inputs"][kind] == signals.operator(kind).INPUTS[kind]


def test_summary_binding_replaces_only_the_numeric_value_and_requires_identical_units():
    original = measurement()
    expression = {"kind": "comparison", "ref": "age", "comparison": "le", "number": 60}
    result = signals.expression_body(expression, {"age": original}, "Years")
    assert result.subject == original.subject and result.predicate == original.predicate
    assert result.value.comparison == "le" and result.value.number == 60
    assert original.value.number == 18
    with pytest.raises(ValueError, match="unit_mismatch"):
        signals.expression_body(expression, {"age": original}, "Months")
    with pytest.raises(ValueError, match="positive_quantity"):
        signals.expression_body(expression, {"age": a.Not(original)}, "Years")


def test_complement_preserves_the_disjunction_and_difference_preserves_parent():
    p, q = measurement(), measurement("Months")
    assert signals.expression_body({"kind": "none_of", "refs": ["p", "q"]}, {"p": p, "q": q}) == a.Not(
        a.AnyOf((p, q))
    )
    assert signals.expression_body({"kind": "difference", "refs": ["p", "q"]}, {"p": p, "q": q}) == a.AllOf(
        (p, a.Not(q))
    )
    with pytest.raises(ValueError, match="missing_signal_predicate"):
        signals.expression_body({"kind": "all_of", "refs": ["p"]}, {})


@pytest.mark.parametrize(
    "status,resolution,code",
    [
        ("known", "resolved", "bounded"),
        ("interpolated", "resolved", "bounded"),
        ("proposed", "resolved", "unresolved"),
        ("known", "unresolved", "unresolved"),
        ("known", "conflicting", "unresolved"),
    ],
)
def test_calculation_never_promotes_its_support(status, resolution, code):
    request = signals_guide.example()
    support = request["signals"][0]["support"][0]
    support.update(status=status, resolution=resolution)
    row = run(request)["result"]["signals"][0]
    assert row["code"] == code and row["calculation_code"] == "bounded"
    assert row["status"] == status and row["basis"] == support["basis"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: r.update(signals=None),
        lambda r: r.update(signals={}),
        lambda r: r["signals"].append(copy.deepcopy(r["signals"][0])),
        lambda r: r["signals"][0].update(kind="clinical_guess"),
        lambda r: r["signals"][0].update(support=[]),
        lambda r: r["signals"][0]["support"][0].update(status="confirmed"),
        lambda r: r["signals"][0]["support"][0].update(basis=[]),
        lambda r: r["signals"][0]["support"][0].update(resolution=None),
        lambda r: r["signals"][0]["data"].update(total=True),
        lambda r: r["signals"][0].update(bindings={"a": None}),
    ],
)
def test_malformed_public_signal_wrappers_are_named_refusals(mutation):
    request = signals_guide.example()
    mutation(request)
    reply = run(request)
    assert reply["code"] == "refused" and reply["problems"] and reply["result"] is None


def test_empty_signal_list_is_a_complete_empty_analysis_not_a_false_observation():
    reply = run({"operation": "signals", "signals": []})
    assert reply["code"] == "complete" and reply["result"]["signals"] == []


def test_structural_bindings_accept_tagged_propositions_but_not_assertion_envelopes():
    request = signals_guide.example()
    request["signals"][0]["bindings"] = {"a": json.loads(a.canonical(measurement()))}
    assert run(request)["code"] == "complete"
    request["signals"][0]["bindings"]["a"] = {"class": "Always"}
    assert run(request)["code"] == "refused"


@pytest.mark.parametrize(
    "kind,witness,expected",
    [
        ("partition", "b", ["at_least_3", "at_most_3"]),
        ("summary", "summary", ["at_least_3"]),
        ("population", "outside", ["at_most_2", "at_most_3"]),
    ],
)
def test_numeric_expressions_bind_into_existing_participant_solver(kind, witness, expected):
    from TrialLedger.layer2 import bounds_guide

    request = bounds_guide.example()
    signal = signals_guide.example(kind)["signals"][0]
    data = signal["data"]
    body = request["observations"][0]["body"]
    high = copy.deepcopy(body)
    high["value"].update(comparison="ge", number=3)
    three = copy.deepcopy(body)
    three["value"].update(number=3)
    if kind == "partition":
        signal["bindings"] = {"a": body, "b": three}
    elif kind == "summary":
        data["unit"] = "example_scale"
        signal["bindings"] = {"age": body}
    else:
        signal["bindings"] = {"randomized": body, "analysed": high}
    request["signals"] = [signal]
    old = request["observations"][0]
    request["observations"] = [
        {
            "id": "derived",
            "denominator": data["total"],
            "population": data["universe"],
            "context": {},
            "bridge": old["bridge"],
            "derivation": {"signal": signal["id"], "witness": witness},
        }
    ]
    reply = run(request)
    assert reply["code"] == "complete", reply
    result = reply["result"]
    assert result["remaining"] == expected
    assert result["candidates"][0]["observations"][0]["derivation"]["expression"]
    assert result["premises"] == request


@pytest.mark.parametrize(
    "mutation,problem",
    [
        (lambda r: r["observations"][0].update(population="other:population"), "population_mismatch"),
        (lambda r: r["observations"][0].update(denominator=99), "population_mismatch"),
        (lambda r: r["observations"][0]["derivation"].update(witness="missing"), "unknown_derived_witness"),
        (lambda r: r["signals"][0].update(bindings={}), "missing_signal_predicate_binding"),
    ],
)
def test_derived_population_and_predicate_bindings_cannot_be_invented(mutation, problem):
    from TrialLedger.layer2 import bounds_guide

    request = bounds_guide.example()
    signal = signals_guide.example()["signals"][0]
    signal["bindings"] = {"a": request["query"], "b": request["query"]}
    request["signals"] = [signal]
    request["observations"] = [
        {
            "id": "derived",
            "denominator": 100,
            "population": "invented:baseline",
            "context": {},
            "bridge": request["observations"][0]["bridge"],
            "derivation": {"signal": signal["id"], "witness": "intersection"},
        }
    ]
    mutation(request)
    reply = run(request)
    assert reply["code"] == "refused" and problem in reply["problems"][0]
