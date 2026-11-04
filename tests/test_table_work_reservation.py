"""Reserve represented table work without reducing any semantic or execution limit."""

import json
import random
from copy import deepcopy
from unittest.mock import patch

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import entail, run
from TrialLedger.layer2.decision_tables import EXAMPLES, evaluate, work_reservation


def literal(key, kind, value):
    operand = (
        a.Value("boolean")
        if kind == "boolean"
        else a.Value("enum", members=(value,))
        if kind == "enum"
        else a.Value("quantity", number=value, unit="declared-unit")
    )
    return json.loads(
        a.canonical(
            a.Literal(
                a.Subject("source_case"),
                a.Predicate("defined_term", key),
                operand,
                polarity="negative" if kind == "boolean" and not value else "positive",
            )
        )
    )


def random_table(seed):
    rng = random.Random(seed)
    data = deepcopy(EXAMPLES["decision_table"])
    data["domains"] = []
    for index in range(rng.randint(1, 4)):
        kind = rng.choice(["boolean", "enum", "quantity"])
        values = [False, True] if kind == "boolean" else ["a", "b"] if kind == "enum" else [0, 2]
        data["domains"].append(
            {"id": str(index), "values": [literal(str(index), kind, value) for value in values]}
        )
    choices = [value for domain in data["domains"] for value in domain["values"]]
    data["constraints"] = [deepcopy(rng.choice(choices)) for _ in range(rng.randint(0, 2))]
    data["rows"] = [
        {"id": str(index), "when": deepcopy(rng.choice(choices)), "action": rng.choice(data["actions"])}
        for index in range(rng.randint(1, 5))
    ]
    data["prohibitions"] = [
        {"id": str(index), "when": deepcopy(rng.choice(choices)), "action": rng.choice(data["actions"])}
        for index in range(rng.randint(0, 3))
    ]
    data["limits"] = {
        "solver_bound": rng.choice([1, 8, 128, 4096]),
        "solver_calls": rng.choice([1, 3, 32, 256]),
    }
    return data


def measured_work(data):
    """Count actual assignments yielded inside satisfiability, not the reservation's own estimate."""
    counter = {"assignments": 0, "satisfiability_calls": 0}
    original_product, original_satisfiable = entail.itertools.product, entail._satisfiable

    def counted_product(*args, **kwargs):
        for chosen in original_product(*args, **kwargs):
            counter["assignments"] += 1
            yield chosen

    def counted_satisfiable(*args, **kwargs):
        counter["satisfiability_calls"] += 1
        return original_satisfiable(*args, **kwargs)

    with (
        patch.object(entail.itertools, "product", counted_product),
        patch.object(entail, "_satisfiable", counted_satisfiable),
    ):
        result = evaluate("decision_table", data)
    counter["illustration_work"] = result["value"]["witness_summary"].get("work", 0)
    counter["total"] = counter["assignments"] + counter["illustration_work"]
    return counter


def test_public_dlt_example_reserves_numeric_partitions_not_its_unused_ceiling():
    data = deepcopy(EXAMPLES["decision_table"])
    before = deepcopy(data)
    assert work_reservation(data) == 16834  # 15 cells * 5 decisions * 6 checks + 16,384 illustrations.
    assert data == before
    assert data["limits"] == {"solver_bound": 4096, "solver_calls": 256}


def test_all_public_table_examples_cover_instrumented_actual_work():
    guide = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]
    examples = guide["signal_examples"]["decision_table"]["signals"]
    assert examples
    for example in examples:
        assert work_reservation(example["data"]) >= measured_work(example["data"])["total"]


@pytest.mark.parametrize("seed", range(32))
def test_random_small_table_reservation_covers_actual_enumerations_and_prohibitions(seed):
    data = random_table(seed)
    assert work_reservation(data) >= measured_work(data)["total"]


def test_guard_and_prohibition_thresholds_are_included_in_partition_union():
    data = deepcopy(EXAMPLES["decision_table"])
    condition = deepcopy(data["domains"][0]["values"][0])
    condition["value"].update(comparison="ge", number=2.5)
    data["rows"][0]["when"] = condition
    data["prohibitions"] = [{"id": "new-threshold", "when": deepcopy(condition), "action": "escalate"}]
    data["prohibitions"][0]["when"]["value"]["number"] = 3.5
    # Nine named thresholds have 19 rational cells, and six possible decisions each need at most six checks.
    assert work_reservation(data) == 19 * 6 * 6 + 16384
    assert work_reservation(data) >= measured_work(data)["total"]


def test_reservation_never_executes_the_solver():
    with patch.object(entail, "decide", side_effect=AssertionError("reservation executed solver")):
        assert work_reservation(deepcopy(EXAMPLES["decision_table"])) == 16834


@pytest.mark.parametrize("which", ["extra", "null-prohibitions", "undeclared-guard"])
def test_reservation_and_execution_share_exact_structural_refusals(which):
    data = deepcopy(EXAMPLES["decision_table"])
    if which == "extra":
        data["unsupported"] = []
    elif which == "null-prohibitions":
        data["prohibitions"] = None
    else:
        data["rows"][0]["when"] = literal("undeclared", "boolean", True)
    with pytest.raises(ValueError) as reserved:
        work_reservation(data)
    with pytest.raises(ValueError) as executed:
        evaluate("decision_table", data)
    assert str(reserved.value) == str(executed.value)
