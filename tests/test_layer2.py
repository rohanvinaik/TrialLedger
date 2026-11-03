"""The agent boundary exposes correct existing logic without reading clinical prose."""

import dataclasses
import json

import pytest

from TrialLedger.layer2 import run
from TrialLedger.layer2.assertions import (
    AllOf,
    AnyOf,
    Literal,
    Predicate,
    Rule,
    ScopedAssertion,
    Subject,
    Value,
    canonical,
    from_canonical,
)
from TrialLedger.layer2.entail import decide


def literal(key, comparison="eq", members=("yes",), number=None):
    kind = "quantity" if number is not None else "enum"
    return Literal(
        Subject("participant"),
        Predicate("measurement", key),
        Value(kind, comparison, members if kind == "enum" else (), number=number),
    )


def premise(body, identity="given", status="known"):
    return ScopedAssertion(
        identity,
        "user:" + identity,
        "required",
        body,
        rule=Rule("user-premise", "1", warrants=("user:" + identity,)),
        status=status,
        resolution="resolved",
    )


def model(item):
    return json.loads(canonical(item))


def test_an_alternative_remains_an_alternative_through_the_public_entry():
    a, b = literal("EGFR", members=("positive",)), literal("ALK", members=("positive",))
    source = premise(AnyOf((a, b)))
    result = run({"operation": "entailment", "assertions": [model(source)], "query": model(a)})
    assert result["code"] == "complete"
    assert result["result"]["decision"]["result"] == "UNDETERMINED"
    both = run({"operation": "entailment", "assertions": [model(source)], "query": model(AllOf((a, b)))})
    assert both["result"]["decision"]["result"] == "UNDETERMINED"
    alternative = run({"operation": "entailment", "assertions": [model(source)], "query": model(source.body)})
    assert alternative["result"]["decision"]["result"] == "ENTAILED"
    assert alternative["result"]["premises"] == [model(source)]


def test_a_population_constraint_has_a_conditional_exclusion_consequence():
    female, male = literal("eligible_sex", members=("female",)), literal("eligible_sex", members=("male",))
    source = premise(female)
    result = run({"operation": "entailment", "assertions": [model(source)], "query": model(male)})
    assert result["result"]["decision"]["result"] == "REFUTED"
    assert result["result"]["decision"]["proof"] == ("given",)
    assert "Conditional" in result["result"]["basis"]


def test_a_default_premise_never_becomes_a_known_deduction():
    source = premise(literal("eligible_sex", members=("female",)), status="interpolated")
    result = run({"operation": "entailment", "assertions": [model(source)], "query": model(source.body)})
    assert result["result"]["decision"]["status"] == "interpolated"


def test_large_threshold_cells_are_not_collapsed_by_float_rounding():
    source = premise(literal("x", "ge", number=1e308))
    query = literal("x", "gt", number=1e308)
    assert decide((source,), query).result == "UNDETERMINED"
    assert decide((source,), source.body).result == "ENTAILED"
    assert decide((premise(query),), source.body).result == "ENTAILED"
    assert decide((source,), literal("x", "lt", number=1e308)).result == "REFUTED"


def test_adjacent_huge_integer_bounds_and_canonical_round_trip_are_exact():
    high = 10**100 + 1
    exact = literal("x", "eq", number=high)
    assert from_canonical(canonical(exact)) == exact
    assert decide((premise(exact),), literal("x", "eq", number=high - 1)).result == "REFUTED"
    assert (
        decide((premise(literal("x", "gt", number=high)),), literal("x", "le", number=high)).result
        == "REFUTED"
    )


def test_coordinates_require_explicit_domain_and_keep_default_separate():
    evidence = [
        {
            "section": "inclusion",
            "concept": "prior_lines",
            "values": ["0"],
            "scope": "advanced",
            "ref": "user:no-prior",
        },
        {
            "section": "inclusion",
            "concept": "extent",
            "values": ["advanced"],
            "scope": "",
            "ref": "user:advanced",
        },
    ]
    result = run({"operation": "coordinates", "domain": "nsclc", "evidence": evidence})
    assert result["code"] == "complete"
    setting = result["result"]["coordinates"]["setting"]
    assert setting["state"] == "unnarrowed"
    assert setting["interpolated"]["domain"] == ("advanced_first_line",)
    assert result["result"]["premises"] == evidence
    unsupported = run({"operation": "coordinates", "domain": "diabetes", "evidence": evidence})
    assert unsupported["code"] == "refused" and unsupported["problems"] == ["unsupported_domain"]


def test_raw_registry_records_and_text_cannot_become_symbolic_facts():
    for request in (
        {"operation": "coordinates", "domain": "nsclc", "evidence": "EGFR-positive or ALK-positive"},
        {"operation": "coordinates", "domain": "nsclc", "evidence": [], "studies": [{"protocolSection": {}}]},
        {"operation": "entailment", "assertions": ["ECOG <= 1"], "query": "ECOG"},
    ):
        assert run(request)["code"] == "refused"


def trial(identity, elements, klass="Class A"):
    return {
        "id": identity,
        "sponsor": identity,
        "stratum": "declared-comparable-set",
        "elements": elements,
        "basis": ["user:typed-trials"],
        "typed": bool(elements),
        "classes": [klass],
        "class_unresolved": False,
        "representation": {"setting": "first_line"},
        "predicates": {"ECOG": "0-1"},
        "start_year": "2020",
    }


def test_corpus_silence_retains_bounds_and_does_not_establish_absence():
    result = run({"operation": "corpus", "trials": [trial("A", ["inclusion:ecog_ps=0|1"]), trial("B", [])]})
    assert result["code"] == "complete"
    (row,) = result["result"]["frequency"]
    assert row["statement_rate"] == 0.5 and row["lower"] == 0.5 and row["upper"] == 1.0
    assert row["absence_established"] == 0 and row["unresolved"] == 1 and row["tier"] == "unresolved"


def test_corpus_near_miss_retains_the_declared_representation():
    a, b = trial("A", []), trial("B", [])
    b["predicates"] = {"ECOG": "0-2"}
    result = run({"operation": "corpus", "trials": [a, b]})
    (pair,) = result["result"]["near_misses"]
    assert (pair["a"], pair["b"], pair["difference"]) == ("A", "B", "ECOG")
    b["representation"] = {"setting": ""}
    assert run({"operation": "corpus", "trials": [a, b]})["result"]["near_misses"] == []


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"operation": []},
        {"operation": "design"},
        {"operation": "entailment", "assertions": [], "query": {}, "bound": True},
        {"operation": "corpus", "trials": [{"id": "A"}]},
    ],
)
def test_malformed_requests_are_named_refusals(payload):
    result = run(payload)
    assert result["code"] == "refused" and result["result"] is None and result["problems"]


def test_scoped_contexts_and_resource_bound_pass_through_the_entry():
    source = premise(literal("x"))
    source = dataclasses.replace(
        source, cohort=from_canonical('{"class":"Scope","kind":"cohort_ref","ref":"A","parts":[]}')
    )
    result = run(
        {
            "operation": "entailment",
            "assertions": [model(source)],
            "query": model(source.body),
            "context": {"cohort": "B"},
        }
    )
    assert result["result"]["decision"]["result"] == "OUT_OF_SCOPE"
    limited = run(
        {"operation": "entailment", "assertions": [model(source)], "query": model(source.body), "bound": 1}
    )
    assert limited["result"]["decision"]["result"] == "UNDETERMINED"


def test_describe_returns_runnable_examples_for_every_working_operation():
    described = run({"operation": "describe", "view": "full"})
    assert described["code"] == "complete"
    description = described["result"]
    assert set(description["examples"]) == {
        "entailment",
        "coordinates",
        "corpus",
        "design_bounds",
        "signals",
        "interpretations",
        "source_assertions",
    }
    results = {name: run(payload) for name, payload in description["examples"].items()}
    assert all(reply["code"] == "complete" for reply in results.values())
    assert results["entailment"]["result"]["decision"]["result"] == "REFUTED"
    assert results["entailment"]["result"]["decision"]["proof"] == ("population",)
    setting = results["coordinates"]["result"]["coordinates"]["setting"]
    assert setting["state"] == "unnarrowed"
    assert setting["interpolated"]["domain"] == ("advanced_first_line",)
    (row,) = results["corpus"]["result"]["frequency"]
    assert (row["statement_rate"], row["lower"], row["upper"]) == (0.5, 0.5, 1.0)
    assert "does not certify" in description["premise_status"]["known"]
    assert (
        "automatic source-to-assertion compilation" in description["availability"]["designed_not_integrated"]
    )


def test_description_field_sets_match_actual_unknown_and_missing_field_refusals():
    description = run({"operation": "describe", "view": "full"})["result"]
    for operation, payload in description["examples"].items():
        assert set(payload) <= {"operation", *description["input_shapes"][operation]["fields"]}
        assert run({**payload, "raw_registry_text": "not a typed premise"})["code"] == "refused"
        for field in description["input_shapes"][operation]["required"]:
            missing = {key: value for key, value in payload.items() if key != field}
            assert run(missing)["code"] == "refused"
    assert run({"operation": "describe", "trials": []})["code"] == "refused"


def test_described_array_types_are_enforced():
    examples = run({"operation": "describe", "view": "full"})["result"]["examples"]
    for operation, key in (("entailment", "assertions"), ("coordinates", "evidence"), ("corpus", "trials")):
        assert run({**examples[operation], key: "raw prose"})["code"] == "refused"


def test_describe_has_no_network_or_filesystem_mutation(monkeypatch):
    import socket
    from pathlib import Path

    import httpx

    def forbidden(*args, **kwargs):
        raise AssertionError("describe is a pure description")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    assert run({"operation": "describe", "view": "full"})["code"] == "complete"


def test_modifying_a_description_cannot_rewrite_the_validator():
    description = run({"operation": "describe", "view": "full"})["result"]
    description["input_shapes"]["coordinates"]["fields"]["raw_text"] = "string"
    description["vocabularies"]["coordinate_values"]["prior_lines"] = ("anything",)
    assert (
        run({"operation": "coordinates", "domain": "nsclc", "evidence": [], "raw_text": "x"})["code"]
        == "refused"
    )
    fresh = run({"operation": "describe", "view": "full"})["result"]
    assert "raw_text" not in fresh["input_shapes"]["coordinates"]["fields"]


def test_described_corpus_capabilities_have_runnable_examples_with_the_stated_results():
    description = run({"operation": "describe", "view": "full"})["result"]
    examples = description["capability_examples"]
    assert set(examples) == {"associations", "near_misses", "occupancy", "expectations"}
    replies = {name: run(example["request"]) for name, example in examples.items()}
    assert all(reply["code"] == "complete" for reply in replies.values())
    for example in examples.values():
        assert example["premise_origin"].startswith("Invented")
        for item in [*example["request"]["trials"], *example["request"].get("expectations", [])]:
            assert item["basis"] == ["user:invented-demonstration-premises-not-registry-facts"]
    association = next(
        row for row in replies["associations"]["result"]["associations"] if row["class"] == "invented-class-a"
    )
    assert association["element"] == "inclusion:example_requirement=yes"
    assert association["status"] == "proposed"
    assert (association["inside_rate"], association["outside_rate"]) == (1, 0)
    assert (
        association["inside_stating"]
        == description["result_guides"]["corpus"]["associations"]["support"]["stating_trials"]
    )
    (pair,) = replies["near_misses"]["result"]["near_misses"]
    assert (pair["difference"], pair["value_a"], pair["value_b"]) == ("example_score_limit", "0|1", "0|2")
    assert pair["other_predicates_agreeing"] == 1
    assert (pair["sponsor_a"], pair["sponsor_b"], pair["year_a"], pair["year_b"]) == (
        "invented-sponsor-0",
        "invented-sponsor-1",
        "2020",
        "2021",
    )
    cells = replies["occupancy"]["result"]["occupancy"]
    assert [(row["setting"], row["occupants"], row["possible"], row["state"]) for row in cells] == [
        ("example-setting-a", 1, 1, "occupied"),
        ("example-setting-b", 0, 1, "unknown"),
        ("example-setting-c", 0, 0, "empty"),
    ]
    (expectation,) = replies["expectations"]["result"]["expectations"]
    assert expectation["rarity"] == ("cell", 0.5, 2, 1.0, 1.0)


def test_described_result_fields_match_the_actual_operation_responses():
    described = run({"operation": "describe", "view": "full"})
    description = described["result"]
    guides = description["result_guides"]
    assert set(guides["envelope"]) == set(described)
    for operation in ("entailment", "coordinates", "corpus"):
        reply = run(description["examples"][operation])["result"]
        assert set(guides[operation]["fields"]) == set(reply)
        if operation == "entailment":
            assert set(guides[operation]["fields"]["decision"]) == set(reply["decision"])
        if operation == "coordinates":
            for coordinate in reply["coordinates"].values():
                assert set(guides[operation]["coordinate_row"]) == set(coordinate)
    for kind, example in description["capability_examples"].items():
        reply = run(example["request"])["result"]
        for row in reply[kind]:
            assert set(guides["corpus"][kind]["row_fields"]) == set(row)
        for row in reply["frequency"]:
            assert set(guides["corpus"]["frequency"]["row_fields"]) == set(row)
    assert len(guides["corpus"]["expectations"]["rarity_positions"]) == 5


def test_described_developer_blocks_exist_without_becoming_public_operations():
    import importlib

    description = run({"operation": "describe", "view": "full"})["result"]
    assert set(description["operation_field"]["values"]) == {
        "describe",
        "entailment",
        "coordinates",
        "corpus",
        "design_bounds",
        "signals",
        "interpretations",
        "source_assertions",
    }
    for block in description["developer_building_blocks"]["entries"]:
        assert block["purpose"] and block["precondition"]
        for entrypoint in block["entrypoints"]:
            module_name, name = entrypoint.rsplit(".", 1)
            assert callable(getattr(importlib.import_module(module_name), name))
    assert run({"operation": "deviation_status", "status": "explicitly_negated"})["code"] == "refused"
    assert all(
        case["operation"]
        in {
            "entailment",
            "coordinates",
            "corpus",
            "design_bounds",
            "signals",
            "interpretations",
            "source_assertions",
        }
        for case in description["use_cases"]
    )
