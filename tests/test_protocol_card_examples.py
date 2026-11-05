"""Protocol discovery card: detail levels, built/unbuilt boundary, examples and policy trace wording."""

import copy
import json
import re

import pytest

from TrialLedger.layer2 import protocol_view, run

FAMILIES = {
    "schedule",
    "finite_policy",
    "binomial_design",
    "external_method",
    "estimand",
    "decisions",
    "definition_relation",
}
FORBIDDEN = re.compile(r"\b(safe|valid|complete|adequate|approved)\b")


def describe(detail: str | None = None) -> dict:
    request = {"operation": "describe", "view": "protocol"}
    if detail:
        request["detail"] = detail
    reply = run(request)
    assert reply["code"] == "complete", reply["problems"]
    return reply["result"]


def examples() -> dict:
    return copy.deepcopy(describe("full")["examples"])


def computed(family: str, request: dict | None = None) -> dict:
    prepared = run(request or examples()[family])
    assert prepared["code"] == "complete", prepared["problems"]
    reply = run(prepared["result"]["request"])
    assert reply["code"] == "complete", reply["problems"]
    return reply["result"]


def checks(result: dict) -> dict:
    return {check["id"]: check for check in result["protocol"]["checks"]}


def rows(check: dict) -> dict:
    return {
        row["id"]: row
        for child in check["children"]
        for signal in child["signals"]
        for row in signal["claim_admission"]
    }


def test_detail_levels_are_honoured_and_the_compact_card_stays_small():
    card, schema, full = describe(), describe("schema"), describe("full")
    assert (card["detail"], schema["detail"], full["detail"]) == ("card", "schema", "full")
    assert "examples" not in card and "examples" not in schema and "examples" in full
    assert "example" in card and "example" not in schema
    assert len(json.dumps(schema)) < len(json.dumps(card)) < len(json.dumps(full))
    assert len(json.dumps(card)) < 20_000
    assert card["discover"]["full"] == {"operation": "describe", "view": "protocol", "detail": "full"}
    assert set(card["example_families"]) == FAMILIES
    assert "full" in card["next"]


def test_every_implemented_family_has_one_focused_example():
    assert set(examples()) == FAMILIES
    assert examples()["schedule"] == describe()["example"]


def test_the_built_and_unbuilt_boundary_is_one_short_field_in_every_level():
    for detail in (None, "schema", "full"):
        boundary = describe(detail)["built_boundary"]
        assert set(boundary) == {"built", "not_built", "policy_coverage"}
        text = " ".join(boundary["not_built"])
        for word in ("adaptive", "cluster", "survival", "optimisation", "sample-size", "protocol writing"):
            assert word in text, word
        assert "declared variables" in boundary["policy_coverage"]
        assert "not a safe policy" in boundary["policy_coverage"]
        assert len(json.dumps(boundary)) < 2_000


@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_each_example_is_invented_prepares_and_runs_to_complete(family):
    request = examples()[family]
    assert request["operation"] == "prepare" and request["for"] == "design_session"
    text = json.dumps(request)
    assert "invented" in text
    for item in request["protocol"]["objects"]:
        assert item["origin"]["ref"].startswith("user:invented") or "invented" in item["origin"]["ref"]
    assert computed(family)["protocol"]["checks"]


def test_schedule_example_is_left_unadopted_so_its_findings_stay_unadmitted():
    result = computed("schedule")
    assert {row["admission"] for row in rows(checks(result)["week12-schedule"]).values()} == {
        "proposed_refused"
    }


def test_policy_example_reports_a_prohibition_violation_with_a_witness_and_no_safety_claim():
    result = computed("finite_policy")
    outcomes = {key: row["outcome"] for key, row in rows(checks(result)["dose-policy-check"]).items()}
    assert outcomes == {
        "coverage": "covered",
        "prohibition": "violation",
        "termination": "all_paths_terminate",
    }
    view = protocol_view.view(result)
    texts = json.dumps(view)
    assert "Example from the retained bounded trace" in texts
    assert "safety_concern" in texts
    assert "transition continue selects continue_dosing" in texts
    wording = [row["wording"] for check in view["checks"] for row in check["claims"]]
    assert "1 declared prohibition violation(s) in reachable declared situations." in wording


def test_binomial_example_declares_all_three_assumption_roles_as_premises():
    request = examples()["binomial_design"]
    efficacy = next(o for o in request["protocol"]["objects"] if o["kind"] == "efficacy")
    assert [a["role"] for a in efficacy["data"]["assumptions"]] == ["fixed_n", "iid_binary", "alignment"]
    ids = {criterion["id"] for criterion in request["criteria"]}
    assert {a["premise"] for a in efficacy["data"]["assumptions"]} <= ids
    result = computed("binomial_design")
    claims = rows(checks(result)["binomial-check"])
    assert {key: row["outcome"] for key, row in claims.items()} == {
        "type-one": "satisfied",
        "power": "satisfied",
    }
    value = checks(result)["binomial-check"]["children"][0]["result"]["result"]["signals"][0]["value"]
    assert value["application"]["code"] != "withheld"
    assert value["null_rejection_probability"] and value["power"]


def test_external_method_example_reads_not_computed_with_named_missing_inputs():
    result = computed("external_method")
    check = checks(result)["outside-method-check"]
    assert check["not_computed"]["missing"] == ["accrual_rate"]
    assert check["children"] == [] or all(not child["signals"] for child in check["children"])
    assert "not_computed" in json.dumps(protocol_view.view(result)).replace(" ", "_").lower()


def test_estimand_example_links_collection_once_and_adds_a_dependencies_check():
    request = examples()["estimand"]
    collection = next(o for o in request["protocol"]["objects"] if o["kind"] == "collection")
    assert collection["data"]["event_handling"] == {
        "estimand": "week-policy",
        "requirement": "week12",
        "action": "collect",
    }
    estimand = next(o for o in request["protocol"]["objects"] if o["kind"] == "estimand")
    assert estimand["data"]["collection_plan"] == []
    result = computed("estimand")
    found = checks(result)
    assert found["estimand-check"]["children"][0]["refusal"] is None
    blockers = found["estimand-check"]["children"][0]["signals"][0]["blockers"]
    assert not any(b.startswith("estimand_collection_plan_mismatch") for b in blockers)
    assert found["dependencies-check"]["children"][0]["signals"][0]["code"] == "consistent"


def test_decisions_example_compares_two_plans_under_one_check():
    result = computed("decisions")
    (decision,) = result["protocol"]["decisions"]
    assert [alt["id"] for alt in decision["alternatives"]] == ["as-drafted", "extend"]
    assert decision["selection"]["alternative"] == "as-drafted"


def test_definition_relation_example_relates_two_protocol_checks():
    result = computed("definition_relation")
    (row,) = result["definition_checks"]
    assert (row["relation"], row["code"]) == ("implies", "consistent")
    assert {side["protocol_check"] for side in (row["declaration"]["left"], row["declaration"]["right"])} == {
        "trigger-check",
        "relapse-check",
    }


def policy_texts(mutate) -> list[str]:
    request = examples()["finite_policy"]
    mutate(request["protocol"]["objects"][0]["data"]["model"])
    result = computed("finite_policy", request)
    found: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "witness_wording" and isinstance(value, str):
                    found.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(protocol_view.view(result))
    return found


def test_a_coverage_gap_witness_is_worded_without_a_selected_transition():
    texts = policy_texts(lambda model: model["transitions"].pop(1))
    gap = next(t for t in texts if "no declared rule applies" in t and "not efficacy_signal" in t)
    assert gap.startswith("Example from the retained bounded trace")


def test_a_reachable_cycle_witness_is_worded_with_its_transition_and_the_code_stays_in_the_row():
    def loop(model):
        model["transitions"][1]["to"] = "interim"

    texts = policy_texts(loop)
    cycle = next(t for t in texts if "transition hold selects hold_dosing" in t)
    assert cycle.startswith("Example from the retained bounded trace")


def test_trace_wording_never_certifies_and_is_read_only():
    texts = policy_texts(lambda model: model["transitions"].pop(1))
    for text in texts:
        assert not FORBIDDEN.search(text.lower()), text
    assert protocol_view.witness_text({}) == ""
    assert protocol_view.witness_text({"witnesses": [{"trace": []}]}) == ""
    detail = {"witnesses": [{"trace": [{"state": "s", "valuation": {}, "transition": None, "actions": []}]}]}
    before = copy.deepcopy(detail)
    assert "in state s, no declared rule applies" in protocol_view.witness_text(detail)
    assert detail == before


def test_literal_text_renders_booleans_and_quantities_in_words():
    boolean = {"predicate": {"key": "x"}, "polarity": "negative", "value": {"kind": "boolean"}}
    quantity = {
        "predicate": {"key": "madrs"},
        "polarity": "positive",
        "value": {"kind": "quantity", "comparison": "eq", "number": 21.0, "unit": "score"},
    }
    assert protocol_view.literal_text(boolean) == "not x"
    assert protocol_view.literal_text(quantity) == "madrs eq 21 score"
    assert protocol_view.literal_text(None) == "an undeclared value"
