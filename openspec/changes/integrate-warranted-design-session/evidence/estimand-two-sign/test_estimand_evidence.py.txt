"""Intent: estimand relevance, collection plans and observations cannot promote or replace one another."""

from copy import deepcopy

import pytest

from TrialLedger.layer2.estimand_evidence import (
    EXAMPLES,
    actual_input,
    check,
    collection_alignment,
    evaluate,
)
from TrialLedger.layer2.signals import support_state


def example():
    return deepcopy(EXAMPLES["estimand"])


def fact(data, state="available", mode="observed", status="known", requirement="week12"):
    rule = deepcopy(data["requirements"][0]["rule"])
    rule.update(ref="invented:data:" + requirement + ":" + mode + ":" + state, status=status)
    return {"requirement": requirement, "mode": mode, "state": state, "rule": rule}


def adopted(data, identity="week12"):
    return {
        "scope": data["scope"],
        "version": data["version"],
        "rules": [
            {
                "id": "change",
                "version": "invented:1",
                "output": {"id": "change", "mode": "derived"},
                "alternatives": [[{"id": identity, "mode": "observed"}]],
                "when": [],
            }
        ],
        "adopted": ["change"],
        "available": [],
        "unavailable": [],
        "conditions": {},
    }


def row(result, identity="week12"):
    return next(item for item in result["value"]["requirements"] if item["id"] == identity)


def test_stop_collection_is_plan_mismatch_not_impossible_estimation():
    result = evaluate("estimand", example())
    assert result["code"] == "unresolved"
    assert row(result)["collection_alignment"] == "collection_plan_mismatch"
    assert row(result)["actual_input"] == "unresolved"
    assert result["value"]["dependency_code"] == "consistent"
    assert result["value"]["estimation"] == "not_computed"


@pytest.mark.parametrize(
    "strategy", ["treatment_policy", "hypothetical", "composite", "while_on_treatment", "principal_stratum"]
)
def test_strategy_label_does_not_invent_or_override_supplied_relevance(strategy):
    data = example()
    data["events"][0]["strategy"] = strategy
    result = evaluate("estimand", data)
    assert row(result)["relevance"] == "required"
    assert row(result)["collection_alignment"] == "collection_plan_mismatch"
    data["requirements"] = []
    data["collection_plan"] = []
    result = evaluate("estimand", data)
    assert result["value"]["requirements"] == []
    assert result["support_status"] is None
    assert result["determining_ids"] == []


def test_collect_plan_does_not_manufacture_actual_observation():
    data = example()
    data["collection_plan"][0]["action"] = "collect"
    result = evaluate("estimand", data)
    assert row(result)["collection_alignment"] == "aligned"
    assert row(result)["actual_input"] == "unresolved"
    assert result["value"]["dependency_result"]["value"]["available"] == []


def test_missing_relevant_does_not_itself_prove_dependency_conflict():
    data = example()
    data["data_state"] = [fact(data, "unavailable")]
    result = evaluate("estimand", data)
    assert row(result)["actual_input"] == "missing_relevant"
    assert result["code"] == "unresolved"
    assert result["value"]["dependency_code"] == "consistent"


def test_adopted_rule_can_conflict_under_its_explicit_input_premises():
    data = example()
    data["data_state"] = [fact(data, "unavailable")]
    data["dependencies"] = adopted(data)
    result = evaluate("estimand", data)
    assert result["code"] == "conflict"
    assert result["support_status"] == "known"
    assert "adopted:change" in result["determining_ids"]
    assert "dependency_blocked:change" in result["blockers"]
    assert result["value"]["estimation"] == "not_computed"


def test_imputation_does_not_replace_required_observed_input():
    data = example()
    data["data_state"] = [fact(data, "available", mode="imputed")]
    data["dependencies"] = adopted(data)
    result = evaluate("estimand", data)
    assert row(result)["actual_input"] == "unresolved"
    assert row(result)["data_state"] == []
    assert result["value"]["dependency_result"]["code"] == "unresolved"
    assert {"id": "week12", "mode": "imputed"} in result["value"]["dependency_result"]["value"]["available"]


def test_not_required_absence_is_not_missing_relevant():
    data = example()
    data["events"][0]["strategy"] = "while_on_treatment"
    data["requirements"][0]["relevance"] = "not_required_for_this_estimand"
    data["data_state"] = [fact(data, "unavailable")]
    result = evaluate("estimand", data)
    assert row(result)["collection_alignment"] == "aligned"
    assert row(result)["actual_input"] == "not_required_for_this_estimand"
    assert row(result)["recorded_state"] == "unavailable"
    assert result["code"] == "consistent"


def test_unknown_plan_irrelevant_when_input_explicitly_not_required():
    data = example()
    data["requirements"][0]["relevance"] = "not_required_for_this_estimand"
    data["collection_plan"] = []
    result = evaluate("estimand", data)
    assert row(result)["collection_alignment"] == "aligned"
    assert row(result)["actual_input"] == "not_required_for_this_estimand"
    assert row(result)["recorded_state"] == "unknown"


def test_event_word_death_does_not_establish_nonexistence():
    data = example()
    data["events"][0]["event_ref"]["ref"] = "death"
    result = evaluate("estimand", data)
    assert row(result)["actual_input"] == "unresolved"
    assert row(result)["recorded_state"] == "unknown"


def test_explicit_structural_nonexistence_stays_separate_from_missing():
    data = example()
    data["data_state"] = [fact(data, "structurally_unavailable")]
    result = evaluate("estimand", data)
    assert row(result)["actual_input"] == "structurally_unavailable"
    assert result["code"] == "unresolved"
    data["requirements"][0]["relevance"] = "not_required_for_this_estimand"
    result = evaluate("estimand", data)
    assert row(result)["actual_input"] == "structurally_unavailable"
    assert result["code"] == "consistent"


def test_pending_unrelated_definition_keeps_local_known_checks():
    data = example()
    data["definitions"]["summary"]["status"] = "proposed"
    data["collection_plan"][0]["action"] = "collect"
    data["data_state"] = [fact(data)]
    result = evaluate("estimand", data)
    assert result["value"]["definition_state"] == "unresolved"
    assert row(result)["relevance"] == "required"
    assert row(result)["relevance_status"] == "known"
    assert row(result)["collection_alignment"] == "aligned"
    assert row(result)["actual_input"] == "available"
    assert row(result)["actual_status"] == "known"


def test_proposed_relevance_rule_never_yields_known_dependency_conflict():
    data = example()
    data["requirements"][0]["rule"]["status"] = "proposed"
    data["data_state"] = [fact(data, "unavailable")]
    data["dependencies"] = adopted(data)
    result = evaluate("estimand", data)
    assert row(result)["relevance"] == "unresolved"
    assert result["value"]["dependency_result"]["code"] == "conflict"
    assert result["value"]["dependency_code"] == "unresolved"
    assert result["code"] == "unresolved"


def test_pending_fact_remains_unknown_not_unavailable():
    data = example()
    data["data_state"] = [fact(data, "unavailable", status="proposed")]
    data["dependencies"] = adopted(data)
    result = evaluate("estimand", data)
    assert row(result)["recorded_state"] == "unknown"
    assert result["code"] == "unresolved"
    checks = result["value"]["dependency_checks"]
    assert next(item for item in checks if item["id"] == "adopted:change")["result"]["code"] == "unresolved"


def test_known_conflict_survives_unrelated_proposed_fact():
    data = example()
    other = deepcopy(data["requirements"][0])
    other.update(id="unrelated-day28", window="day28")
    data["requirements"].append(other)
    data["data_state"] = [
        fact(data, "unavailable"),
        fact(data, "available", status="proposed", requirement=other["id"]),
    ]
    data["dependencies"] = adopted(data)
    result = evaluate("estimand", data)
    assert result["code"] == "conflict"
    assert result["support_status"] == "known"
    assert result["determining_ids"] == ["adopted:change"]
    assert row(result, "unrelated-day28")["actual_input"] == "unresolved"


def test_two_hop_adopted_closure_preserves_derived_availability():
    data = example()
    data["collection_plan"][0]["action"] = "collect"
    data["data_state"] = [fact(data)]
    dep = adopted(data)
    dep["rules"].append(
        {
            "id": "summary",
            "version": "invented:1",
            "output": {"id": "summary", "mode": "derived"},
            "alternatives": [[{"id": "change", "mode": "derived"}]],
            "when": [],
        }
    )
    dep["adopted"].append("summary")
    data["dependencies"] = dep
    result = evaluate("estimand", data)
    check = next(item for item in result["value"]["dependency_checks"] if item["id"] == "adopted:summary")
    assert check["code"] == "consistent"
    assert check["request"]["adopted"] == ["change", "summary"]
    assert {"id": "summary", "mode": "derived"} in check["result"]["value"]["available"]
    dep["adopted"] = ["summary"]
    result = evaluate("estimand", data)
    check = next(item for item in result["value"]["dependency_checks"] if item["id"] == "adopted:summary")
    assert check["code"] == "unresolved"
    assert len(check["request"]["rules"]) == 2
    assert {"id": "summary", "mode": "derived"} not in check["result"]["value"]["available"]


def test_redundant_interpolated_fact_does_not_weaken_known_conflict():
    data = example()
    available = fact(data)
    unavailable = fact(data, "unavailable")
    duplicate = fact(data, "structurally_unavailable", status="interpolated")
    data["data_state"] = [available, unavailable, duplicate]
    result = evaluate("estimand", data)
    assert result["code"] == "conflict"
    assert result["support_status"] == "known"


@pytest.mark.parametrize(
    "field,value",
    [("mode", "imputed"), ("variable", "other-variable"), ("event", "unknown-event"), ("window", "")],
)
def test_invalid_requirement_binding_refused(field, value):
    data = example()
    data["requirements"][0][field] = value
    with pytest.raises(ValueError):
        evaluate("estimand", data)


def test_wrong_dependency_scope_refused():
    data = example()
    data["dependencies"] = adopted(data)
    data["dependencies"]["scope"] = "other-arm"
    with pytest.raises(ValueError, match="estimand_dependency_scope_mismatch"):
        evaluate("estimand", data)


@pytest.mark.parametrize("value", [None, {}, 0, "", [None]])
def test_malformed_event_collection_refused(value):
    data = example()
    data["events"] = value
    with pytest.raises(ValueError):
        evaluate("estimand", data)


def test_nonempty_candidate_claim_refused():
    with pytest.raises(ValueError, match="estimand_candidate_claims_unsupported"):
        check("estimand", example(), [{"available": ["week12"]}])


def test_order_independence_and_input_immutability():
    data = example()
    data["data_state"] = [fact(data), fact(data, "available", mode="imputed")]
    before = deepcopy(data)
    result = evaluate("estimand", data)
    data["data_state"].reverse()
    changed = evaluate("estimand", data)
    assert changed["code"] == result["code"]
    assert changed["value"]["dependency_result"] == result["value"]["dependency_result"]
    data["data_state"].reverse()
    assert data == before


@pytest.mark.parametrize(
    "statuses,resolutions,expected",
    [
        ([], [], "missing_support"),
        (["known"], [], "missing_support"),
        (["proposed"], ["resolved"], "proposed_refused"),
        (["known"], ["unresolved"], "binding_unresolved"),
        (["known"], ["resolved"], "accepted"),
        (["interpolated"], ["resolved"], "accepted"),
    ],
)
def test_support_state_direct(statuses, resolutions, expected):
    assert support_state(statuses, resolutions) == expected


@pytest.mark.parametrize(
    "relevance,action,expected",
    [
        ("required", "stop", "collection_plan_mismatch"),
        ("required", "collect", "aligned"),
        ("required", "unknown", "unresolved"),
        ("unresolved", "collect", "unresolved"),
        ("not_required_for_this_estimand", "unknown", "aligned"),
        ("not_required_for_this_estimand", "stop", "aligned"),
    ],
)
def test_collection_alignment_direct(relevance, action, expected):
    assert collection_alignment(relevance, action) == expected


@pytest.mark.parametrize(
    "relevance,state,expected",
    [
        ("required", "structurally_unavailable", "structurally_unavailable"),
        ("required", "available", "available"),
        ("required", "unavailable", "missing_relevant"),
        ("required", "unknown", "unresolved"),
        ("unresolved", "unavailable", "unresolved"),
        ("not_required_for_this_estimand", "unavailable", "not_required_for_this_estimand"),
        ("not_required_for_this_estimand", "available", "available"),
        ("not_required_for_this_estimand", "structurally_unavailable", "structurally_unavailable"),
    ],
)
def test_actual_input_direct(relevance, state, expected):
    assert actual_input(relevance, state) == expected


def test_pending_variable_binding_does_not_promote_raw_available_source_input():
    data = example()
    data["data_state"] = [fact(data)]
    data["definitions"]["variable"]["status"] = "proposed"
    result = evaluate("estimand", data)
    assert row(result)["recorded_state"] == "available"
    assert row(result)["actual_input"] == "unresolved"
    assert row(result)["actual_status"] is None


def test_pending_relevance_does_not_erase_independent_bound_input_availability():
    data = example()
    data["data_state"] = [fact(data)]
    data["requirements"][0]["rule"]["status"] = "proposed"
    result = evaluate("estimand", data)
    assert row(result)["relevance"] == "unresolved"
    assert row(result)["actual_input"] == "available"
    assert row(result)["actual_status"] == "known"


@pytest.mark.parametrize("where", ["requirements", "collection_plan", "data_state"])
def test_unhashable_reference_is_named_refusal(where):
    data = example()
    if where == "data_state":
        data[where] = [fact(data)]
    field = "event" if where == "requirements" else "requirement"
    data[where][0][field] = []
    with pytest.raises(ValueError, match="estimand_identity_required"):
        evaluate("estimand", data)


def test_one_unresolved_support_must_never_be_hidden_by_one_resolved_support():
    assert support_state(["known", "known"], ["resolved", "unresolved"]) == "binding_unresolved"
