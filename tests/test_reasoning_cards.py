"""Compact discovery must preserve the real contracts without eagerly replaying examples."""

import json
from copy import deepcopy

import pytest

from TrialLedger.layer2 import assertions, construction, service
from TrialLedger.reasoning_cards import TASKS, describe_card


def test_cards_do_not_build_full_manual_or_revision_examples(monkeypatch):
    def forbidden():
        raise AssertionError("minimal discovery must not build or replay the full manual")

    monkeypatch.setattr(service, "_full_description", forbidden)
    cards = [describe_card(view) for view in ("overview", *TASKS, "delivery")]
    assert all(isinstance(card, dict) for card in cards)
    assert all(len(json.dumps(card, ensure_ascii=False).encode()) < 10000 for card in cards)
    assert all("revision_example" not in card and "signal_examples" not in card for card in cards)


@pytest.mark.parametrize("view", TASKS)
def test_every_card_example_is_a_direct_complete_reasoning_request(view):
    card = describe_card(view)
    response = service.run(card["example"])
    assert response["code"] == "complete", response["problems"]
    assert response["operation"] == view
    assert "Invented" in card["example_basis"]


@pytest.mark.parametrize("view", TASKS)
def test_schema_tracks_closed_owner_fields_and_required_names(view):
    card = describe_card(view, schema=True)
    schema = card["request_schema"]
    owner = card["input_shapes"][view]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {"operation", *owner["fields"]}
    assert set(schema["required"]) == {"operation", *owner["required"]}
    assert schema["properties"]["operation"] == {"const": view}
    assert "Structural schema only" in schema["description"]


def test_tagged_schema_uses_actual_model_fields_defaults_and_vocabulary():
    schema = describe_card("entailment", schema=True)["request_schema"]
    definition = schema["$defs"]["ScopedAssertion"]
    assert definition["additionalProperties"] is False
    assert set(definition["properties"]) == {"class", *assertions.ScopedAssertion.__dataclass_fields__}
    assert definition["properties"]["status"]["enum"] == sorted(assertions.STATUSES)
    assert "status" not in definition["required"]
    assert set(definition["required"]) == {"class", "id", "criterion_ref", "modality", "body"}
    assert schema["properties"]["assertions"]["items"] == {"$ref": "#/$defs/ScopedAssertion"}
    assert len(schema["properties"]["query"]["anyOf"]) == len(assertions.PROPOSITIONS)


def test_delivery_schemas_are_the_actual_public_tool_declarations():
    from TrialLedger.reasoning_mcp import TOOL_SCHEMAS

    card = describe_card("delivery", schema=True)
    assert card["tools"] == TOOL_SCHEMAS
    card["tools"]["reason_result"]["inputSchema"]["required"].append("invented")
    assert "invented" not in TOOL_SCHEMAS["reason_result"]["inputSchema"]["required"]


def test_machine_shape_preserves_explicit_unselected_interpretation():
    card = describe_card("interpretations", schema=True)
    request = deepcopy(card["example"])
    request["selected"] = None
    assert service.run(request)["code"] == "complete"
    assert card["request_schema"]["properties"]["selected"]["type"] == ["string", "null"]


def test_discovery_returns_fresh_structures_and_keeps_unknown_views_unhandled():
    original = deepcopy(service.INPUTS["entailment"])
    card = describe_card("entailment")
    card["input"]["fields"]["invented"] = "must not mutate the owner"
    assert service.INPUTS["entailment"] == original
    assert describe_card("full") is None
    assert describe_card("future-operation") is None


def test_canonical_combinator_exports_are_identities_and_remain_runnable():
    assert construction.Always is assertions.Always
    assert construction.AllOf is assertions.AllOf
    assert construction.AnyOf is assertions.AnyOf
    assert construction.Not is assertions.Not
    a = assertions.Literal(
        assertions.Subject("participant"),
        assertions.Predicate("condition_status", "a"),
        assertions.Value("boolean"),
    )
    b = assertions.Literal(
        assertions.Subject("participant"),
        assertions.Predicate("condition_status", "b"),
        assertions.Value("boolean"),
    )
    compound = construction.AllOf((a, construction.AnyOf((b, construction.Not(b)))))
    response = service.run(
        {"operation": "entailment", "assertions": [], "query": construction.expanded(compound)}
    )
    assert response["code"] == "complete"
    assert response["result"]["decision"]["result"] == "UNDETERMINED"
