"""Reservation must cover observed solver work without changing semantic solver bounds."""

import json
import math

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import design_session, entail, solver_work
from TrialLedger.layer2.service import run


@pytest.mark.parametrize(
    "sizes,ceiling,expected", [([], 100, 1), ([2, 3, 5], 100, 30), ([2, 3, 5], 29, 29), ([3], 1, 1)]
)
def test_exact_partition_product_is_capped_without_enumeration(sizes, ceiling, expected):
    assert solver_work.partition_product(sizes, ceiling) == expected


@pytest.mark.parametrize("bad", [None, True, False, 0, -1, "3", [], {}])
def test_partition_ceiling_rejects_malformed_scalars(bad):
    with pytest.raises(ValueError, match="invalid_partition_ceiling"):
        solver_work.partition_product([2], bad)


@pytest.mark.parametrize("bad", [None, True, {}, (), [None], [False], [0], [-1], ["2"]])
def test_partition_sizes_reject_malformed_collections(bad):
    with pytest.raises(ValueError, match="invalid_partition_sizes"):
        solver_work.partition_product(bad, 100)


def _assignment_space(formulas):
    """Independent counted domains at actual solver calls, before enumeration."""
    dimensions = {}
    families = {}
    for formula in formulas:
        for family, key, payload in entail._atoms(formula):
            families[key] = family
            values = dimensions.setdefault(key, set())
            if family == "measure":
                values.add(payload)
            elif family == "enum":
                values.update(payload)
    return math.prod(
        2
        if families[key] == "bool"
        else 2 * len(values) + 1
        if families[key] == "measure"
        else len(values) + 1
        for key, values in dimensions.items()
    )


@pytest.mark.parametrize("operation", ["entailment", "interpretations", "design_bounds", "source_assertions"])
def test_reservation_covers_real_entrypoint_calls_for_discovered_examples(operation, monkeypatch):
    guide = run({"operation": "describe", "view": operation})["result"]
    payload = guide["example"]
    original = entail._satisfiable
    work = []

    def observed(formulas, bound):
        work.append(min(bound, _assignment_space(formulas)))
        return original(formulas, bound)

    monkeypatch.setattr(entail, "_satisfiable", observed)
    reservation = design_session._reserve(payload)
    result = run(payload)
    assert result["code"] == "complete"
    assert reservation >= sum(work)
    assert payload.get("bound", entail.MAX_ASSIGNMENTS) == guide["example"].get(
        "bound", entail.MAX_ASSIGNMENTS
    )


def test_disconnected_constraints_and_numeric_cells_are_all_reserved(monkeypatch):
    q = a.Literal(
        a.Subject("participant"),
        a.Predicate("measurement", "age"),
        a.Value("quantity", "ge", number=18, unit="years"),
    )
    unrelated = a.Literal(
        a.Subject("participant"),
        a.Predicate("measurement", "lab"),
        a.Value("quantity", "le", number=20, unit="mg"),
    )
    models = tuple(
        a.ScopedAssertion(
            str(i),
            "invented",
            "required",
            body,
            rule=a.Rule("invented", "1"),
            status="known",
            resolution="resolved",
        )
        for i, body in enumerate((q, unrelated))
    )
    request = {
        "operation": "entailment",
        "query": json.loads(a.canonical(q)),
        "assertions": [json.loads(a.canonical(item)) for item in models],
    }
    original = entail._satisfiable
    work = []

    def observed(formulas, bound):
        work.append(_assignment_space(formulas))
        return original(formulas, bound)

    monkeypatch.setattr(entail, "_satisfiable", observed)
    result = run(request)
    assert result["result"]["decision"]["result"] == "ENTAILED"
    assert sum(work) <= design_session._reserve(request) < 65536


def test_unsupported_estimate_retains_a_full_conservative_ceiling(monkeypatch):
    monkeypatch.setattr(solver_work, "logical_reservation", lambda request, bound: None)
    assert design_session._reserve({"operation": "entailment", "assertions": [], "query": {}}) >= (
        65536 * (4 * 17 + 1)
    )


def test_rejected_profile_reserves_the_whole_candidate_not_only_its_component(monkeypatch):
    payload = run({"operation": "describe", "view": "design_bounds"})["result"]["example"]
    payload["observations"][0]["direction"] = "rejected"
    for candidate in payload["candidates"]:
        for index in range(5):
            body = a.Literal(
                a.Subject("participant"),
                a.Predicate("measurement", "other-" + str(index)),
                a.Value("boolean"),
            )
            assertion = a.ScopedAssertion(
                "other-" + str(index),
                "invented",
                "required",
                body,
                rule=a.Rule("invented", "1"),
                status="known",
                resolution="resolved",
            )
            candidate["assertions"].append(json.loads(a.canonical(assertion)))
    original = entail._satisfiable
    work = []

    def observed(formulas, bound):
        work.append(_assignment_space(formulas))
        return original(formulas, bound)

    monkeypatch.setattr(entail, "_satisfiable", observed)
    reserved = design_session._reserve(payload)
    result = run(payload)
    assert result["code"] == "complete"
    assert max(work) >= 3 * 2**5
    assert reserved >= sum(work)
