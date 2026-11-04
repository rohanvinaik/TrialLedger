"""Declared safety invariants must expose forbidden selections rather than exclude their witnesses.

All clinical identities and rules here are invented. Coverage cannot certify variables or prohibitions
that were never supplied, and bounded case illustrations cannot certify exhaustive screening.
"""

import json
from copy import deepcopy

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import run
from TrialLedger.layer2.decision_tables import EXAMPLES, evaluate, prohibition_state


@pytest.mark.parametrize("result", ["ENTAILED", "REFUTED", "UNDETERMINED", "INCONSISTENT"])
def test_an_unfinished_safety_check_never_becomes_clear(result):
    assert prohibition_state(result, True) == "unresolved"


def test_one_feasible_forbidden_selection_is_a_violation():
    assert prohibition_state("ENTAILED", False) == "violation"
    assert prohibition_state("UNDETERMINED", False) == "violation"


def test_only_refuted_forbidden_selection_is_clear():
    assert prohibition_state("REFUTED", False) == "clear"
    assert prohibition_state("INCONSISTENT", False) == "domain_conflict"


def table():
    return deepcopy(EXAMPLES["decision_table"])


def prohibition(data, value=1, action="escalate"):
    return {
        "id": "invented:no-escalation",
        "action": action,
        "when": deepcopy(data["domains"][0]["values"][value]),
    }


def test_covered_table_exposes_forbidden_action_without_hiding_its_case():
    data = table()
    data["prohibitions"] = [prohibition(data)]
    before = deepcopy(data)
    result = evaluate("decision_table", data)
    assert data == before
    assert result["code"] == "conflict"
    assert result["blockers"] == ["table_forbidden_action"]
    value = result["value"]
    assert value["coverage"]["state"] == "covered"
    assert value["prohibitions"][0]["state"] == "violation"
    assert value["prohibitions"][0]["basis"] == ["invented:no-escalation", "zero-or-one"]
    assert value["prohibition_coverage"]["state"] == "checked"
    assert value["witnesses"] == []  # Numeric population witnesses remain a distinct channel.
    case = value["case_witnesses"][0]
    assert case["kind"] == "prohibition_violation"
    assert case["profile"] == data["domains"][0]["values"][1]
    assert case["scope"] == data["scope"] and case["version"] == data["version"]
    assert case["result_address"] == "/value/prohibitions/0"
    assert case["values"] == [{"domain": "DLT-count", "value": case["profile"]}]


def test_clear_prohibition_is_not_a_general_safety_certification():
    data = table()
    data["prohibitions"] = [prohibition(data, 2)]
    value = evaluate("decision_table", data)["value"]
    assert value["prohibitions"][0]["state"] == "clear"
    assert value["prohibition_coverage"]["declared"] == 1
    assert value["prohibition_coverage"]["guarantee"] == "conditional_on_declared_table"
    assert value["declared_domains"] == data["domains"]


def test_unmentioned_safety_is_not_reported_checked():
    absent = evaluate("decision_table", table())["value"]["prohibition_coverage"]
    data = table()
    data["prohibitions"] = []
    assert evaluate("decision_table", data)["value"]["prohibition_coverage"] == absent
    assert absent["state"] == "not_declared" and absent["declared"] == 0


def test_an_action_without_rows_cannot_violate_a_prohibition():
    data = table()
    data["actions"].append("invented:never-selected")
    data["prohibitions"] = [prohibition(data, action="invented:never-selected")]
    result = evaluate("decision_table", data)
    assert result["code"] == "consistent"
    assert result["value"]["prohibitions"][0]["state"] == "clear"
    assert result["value"]["prohibitions"][0]["rule"] == "table.action_without_rows:1"


def test_a_prohibition_does_not_replace_declared_feasibility_constraints():
    data = table()
    data["prohibitions"] = [prohibition(data)]
    data["constraints"] = [data["domains"][0]["values"][0]]
    result = evaluate("decision_table", data)
    assert result["code"] == "consistent"
    assert result["value"]["prohibitions"][0]["state"] == "clear"
    assert result["value"]["witness_summary"]["feasible_profiles_examined"] == 1


def test_inconsistent_domain_is_not_a_vacuously_clear_prohibition():
    data = table()
    data["prohibitions"] = [prohibition(data)]
    data["constraints"] = data["domains"][0]["values"][:2]
    result = evaluate("decision_table", data)
    assert result["code"] == "conflict"
    assert result["value"]["prohibition_coverage"]["state"] == "unresolved"
    assert result["value"]["witness_summary"]["state"] == "not_computed"


def test_unfinished_prohibition_is_not_clear_but_proved_violation_survives_other_limits():
    data = table()
    data["prohibitions"] = [prohibition(data)]
    data["limits"]["solver_calls"] = 2
    result = evaluate("decision_table", data)
    assert result["code"] == "unresolved"
    assert result["value"]["prohibitions"][0]["state"] == "unresolved"
    assert result["value"]["prohibition_coverage"]["state"] == "unresolved"
    data["limits"]["solver_calls"] = 3
    result = evaluate("decision_table", data)
    assert result["code"] == "conflict"
    assert {"table_forbidden_action", "resource_bound:table_checks"} <= set(result["blockers"])


@pytest.mark.parametrize("value", [None, {}, "", 0])
def test_null_or_malformed_prohibitions_are_not_an_empty_safety_list(value):
    data = table()
    data["prohibitions"] = value
    with pytest.raises(ValueError, match="table_list_required:prohibitions"):
        evaluate("decision_table", data)


@pytest.mark.parametrize(
    "change,code",
    [
        ("duplicate", "table_duplicate_prohibition"),
        ("action", "table_unknown_prohibition_action"),
        ("variable", "table_undeclared_prohibition_variable"),
        ("fields", "table_fields:prohibition"),
    ],
)
def test_prohibitions_cannot_invent_variables_or_actions(change, code):
    data = table()
    data["prohibitions"] = [prohibition(data)]
    if change == "duplicate":
        data["prohibitions"].append(deepcopy(data["prohibitions"][0]))
    elif change == "action":
        data["prohibitions"][0]["action"] = "invented:unknown"
    elif change == "variable":
        data["prohibitions"][0]["when"]["predicate"]["key"] = "invented:unmeasured-safety"
    else:
        data["prohibitions"][0]["rationale"] = "invented"
    with pytest.raises(ValueError, match=code):
        evaluate("decision_table", data)


def test_gap_and_conflict_profiles_are_returned_without_manual_solver_calls():
    data = table()
    data["rows"][0]["when"] = data["domains"][0]["values"][0]
    data["rows"].append(
        {"id": "invented:contradiction", "when": data["domains"][0]["values"][0], "action": "stop"}
    )
    result = evaluate("decision_table", data)
    cases = result["value"]["case_witnesses"]
    assert {case["kind"] for case in cases} == {"coverage_gap", "conflicting_actions"}
    assert (
        next(case for case in cases if case["kind"] == "coverage_gap")["profile"]
        == data["domains"][0]["values"][1]
    )
    assert next(case for case in cases if case["kind"] == "conflicting_actions")["actions"] == [
        "escalate",
        "stop",
    ]


def test_witness_output_cap_is_explicit_without_weakening_exact_coverage():
    data = table()
    prototype = data["domains"][0]["values"][0]
    values = []
    for number in range(32):
        item = deepcopy(prototype)
        item["value"]["number"] = number
        values.append(item)
    data["domains"][0]["values"] = values
    data["rows"] = [{"id": "only-zero", "when": values[0], "action": "stop"}]
    result = evaluate("decision_table", data)
    assert result["code"] == "conflict"
    assert result["value"]["coverage"]["state"] == "gap"
    summary = result["value"]["witness_summary"]
    assert summary["state"] == "truncated"
    assert summary["combinations_total"] == summary["combinations_examined"] == 32
    assert summary["witnesses_found"] == 31 and summary["witnesses_returned"] == 16
    assert summary["omitted_witnesses"] == 15


def boolean(key, positive=True):
    return json.loads(
        a.canonical(
            a.Literal(
                a.Subject("source_case"),
                a.Predicate("defined_term", key),
                a.Value("boolean"),
                polarity="positive" if positive else "negative",
            )
        )
    )


def test_multivariable_witnesses_preserve_conjunction_and_negative_boolean_values():
    data = table()
    safety, efficacy = boolean("invented:safe"), boolean("invented:effective")
    data["domains"] = [
        {"id": "safety", "values": [safety, boolean("invented:safe", False)]},
        {"id": "efficacy", "values": [efficacy, boolean("invented:effective", False)]},
    ]
    data["rows"] = [
        {
            "id": "all-select",
            "when": {"class": "AnyOf", "parts": [safety, boolean("invented:safe", False)]},
            "action": "escalate",
        }
    ]
    data["prohibitions"] = [
        {"id": "no-unsafe", "when": boolean("invented:safe", False), "action": "escalate"}
    ]
    result = evaluate("decision_table", data)
    assert result["code"] == "conflict"
    cases = result["value"]["case_witnesses"]
    assert len(cases) == 2
    assert all(case["profile"]["class"] == "AllOf" for case in cases)
    assert all(case["values"][0]["value"]["polarity"] == "negative" for case in cases)
    assert result["value"]["witness_summary"]["combinations_examined"] == 4


def test_partial_case_enumeration_never_reports_complete_discovery():
    data = table()
    data["domains"] = [{"id": str(i), "values": [boolean(str(i)), boolean(str(i), False)]} for i in range(8)]
    data["rows"] = [
        {"id": "positive", "when": boolean("0"), "action": "escalate"},
        {"id": "negative", "when": boolean("0", False), "action": "stop"},
    ]
    data["limits"]["solver_bound"] = 128
    result = evaluate("decision_table", data)
    assert result["code"] == "consistent"
    summary = result["value"]["witness_summary"]
    assert summary["state"] == "truncated"
    assert summary["combinations_total"] == 256
    assert summary["combinations_examined"] == summary["unexamined_combinations"] == 128
    assert summary["omitted_witnesses"] is None
    assert summary["work"] <= 16384
    assert summary["witnesses_found"] == 0


def test_enum_witnesses_keep_exact_declared_scalar_members():
    data = table()
    body = a.Literal(
        a.Subject("source_case"),
        a.Predicate("defined_term", "invented:band"),
        a.Value("enum", members=("a",)),
    )
    first = json.loads(a.canonical(body))
    second = deepcopy(first)
    second["value"]["members"] = ["b"]
    last = deepcopy(first)
    last["value"]["members"] = ["c"]
    data["domains"] = [{"id": "band", "values": [first, second, last]}]
    data["rows"] = [{"id": "c-only", "when": last, "action": "stop"}]
    result = evaluate("decision_table", data)
    assert result["code"] == "conflict"
    assert result["value"]["witness_summary"]["combinations_total"] == 3
    assert {case["profile"]["value"]["members"][0] for case in result["value"]["case_witnesses"]} == {
        "a",
        "b",
    }
    assert all(len(case["profile"]["value"]["members"]) == 1 for case in result["value"]["case_witnesses"])


@pytest.mark.parametrize("status", ["proposed", "interpolated", "known"])
def test_public_signal_wrapper_retains_weakest_support_for_forbidden_actions(status):
    data = table()
    data["prohibitions"] = [prohibition(data)]
    response = run(
        {
            "operation": "signals",
            "signals": [
                {
                    "id": "invented:table",
                    "kind": "decision_table",
                    "data": data,
                    "support": [
                        {
                            "id": "invented:adoption",
                            "status": status,
                            "resolution": "resolved",
                            "basis": ["invented:simulated-choice"],
                        }
                    ],
                }
            ],
        }
    )
    assert response["code"] == "complete", response
    signal = response["result"]["signals"][0]
    assert signal["status"] == status
    assert signal["code"] == ("unresolved" if status == "proposed" else "conflict")
    assert signal["value"]["prohibitions"][0]["state"] == "violation"
    assert signal["calculation_code"] == "conflict"
