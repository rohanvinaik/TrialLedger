"""Explicit typed readings and declared relations, not automatic clinical correspondence."""

import json
from copy import deepcopy

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import run
from TrialLedger.layer2.definition_checks import relation_result_code
from TrialLedger.layer2.design_session import prepare_revision
from TrialLedger.layer2.design_session_guide import EXAMPLE


def threshold(number, unit="score"):
    return json.loads(
        a.canonical(
            a.Literal(
                a.Subject("participant"),
                a.Predicate("measurement", "severity"),
                a.Value("quantity", "ge", number=number, unit=unit),
            )
        )
    )


def fixture(relation="implies", left=22, right=20):
    request = deepcopy(EXAMPLE)
    session = request["session"]
    session["decisions"] = []
    standing = {
        "status": "known",
        "resolution": "resolved",
        "basis": ["simulated:explicit-reading-not-registry-fact"],
    }
    for row, number in zip(session["analyses"], (left, right), strict=True):
        row["parameters"]["query"] = threshold(number)
    operands = [
        {
            "analysis": row["id"],
            "address": "/request/query",
            "body": deepcopy(row["parameters"]["query"]),
            **deepcopy(standing),
        }
        for row in session["analyses"]
    ]
    session["definition_checks"] = [
        {
            "id": "trigger-event-link",
            "relation": relation,
            "left": operands[0],
            "right": operands[1],
            **deepcopy(standing),
        }
    ]
    return request


def test_endpoint_implies_earlier_trigger_without_demanding_equal_thresholds():
    response = run(fixture())
    assert response["code"] == "complete", response
    row = response["result"]["definition_checks"][0]
    assert (row["code"], row["status"]) == ("consistent", "known")
    assert row["observed"]["left"] == threshold(22)
    assert row["declaration"]["right"]["body"] == threshold(20)
    assert row["checks"][0]["result"]["result"]["decision"]["result"] == "ENTAILED"
    finding = next(row for row in response["clinical"]["findings"] if row["kind"] == "definition_relation")
    assert finding["standing"] == "known"
    assert finding["canonical_ref"] == "/result/definition_checks/0"


def test_declared_equivalence_is_refuted_by_feasible_intermediate_values():
    response = run(fixture("equivalent"))
    assert response["code"] == "complete", response
    row = response["result"]["definition_checks"][0]
    assert row["code"] == "conflict"
    assert [check["result"]["result"]["decision"]["result"] for check in row["checks"]] == [
        "ENTAILED",
        "UNDETERMINED",
    ]
    assert (
        next(f for f in response["metadata"]["findings"] if f["kind"] == "definition_relation")["disposition"]
        == "conflict"
    )


def test_disjointness_fails_for_overlapping_thresholds():
    response = run(fixture("disjoint"))
    assert response["result"]["definition_checks"][0]["code"] == "conflict"


@pytest.mark.parametrize("part", [None, "left", "right"])
def test_proposed_meaning_or_relation_never_supplies_a_known_constraint(part):
    request = fixture()
    row = request["session"]["definition_checks"][0]
    target = row if part is None else row[part]
    target["status"] = "proposed"
    response = run(request)
    check = response["result"]["definition_checks"][0]
    assert (check["code"], check["status"], check["checks"]) == ("unresolved", None, [])
    assert check["blockers"] == ["definition_proposed_refused"]


def test_interpolated_meaning_stays_interpolated_and_unit_mismatch_is_not_false():
    request = fixture()
    request["session"]["definition_checks"][0]["right"]["status"] = "interpolated"
    assert run(request)["result"]["definition_checks"][0]["status"] == "interpolated"
    request["session"]["definition_checks"][0]["right"]["body"] = threshold(20, "other-score")
    check = run(request)["result"]["definition_checks"][0]
    assert check["code"] == "unresolved" and "no_constraint_mentions_query" in check["blockers"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["session"]["definition_checks"][0]["left"].update(address="/request/missing"),
        lambda r: r["session"]["definition_checks"][0]["left"].update(address="/id"),
        lambda r: r["session"]["definition_checks"][0]["left"].update(analysis="missing"),
        lambda r: r["session"]["definition_checks"][0].update(relation="similar"),
        lambda r: r["session"]["definition_checks"][0].update(basis=[]),
    ],
)
def test_malformed_links_are_named_refusals(mutate):
    request = fixture()
    mutate(request)
    response = run(request)
    assert response["code"] == "refused" and response["problems"]


def test_cross_target_readings_are_not_compared_without_a_binding():
    request = fixture()
    request["session"]["analyses"][1]["target"] = {
        "kind": "historical",
        "ref": "other",
        "scope": {"study": "other", "population": "other", "arm": "all", "time": "other", "version": "1"},
    }
    assert run(request)["problems"] == ["definition_target_mismatch"]


def test_revision_replays_the_relation_and_reports_its_changed_outcome():
    first = fixture("equivalent")
    baseline = run(first)
    following = deepcopy(first["session"])
    following["revision"] = "two"
    following["definition_checks"][0]["right"]["body"] = threshold(22)
    revised = run(prepare_revision(first, baseline, following))
    assert revised["previous_fresh"]["definition_checks"][0]["code"] == "conflict"
    assert revised["result"]["definition_checks"][0]["code"] == "consistent"
    assert revised["diff"]["definition_checks"][0]["code"] == "changed"
    assert revised["answer_diff"]["definition_checks"][0]["code"] == "question_changed"
    assert revised["work"]["analyses"] > baseline["work"]["analyses"]


def test_relation_classifier_does_not_confuse_counterexample_with_incomplete_search():
    assert relation_result_code(["ENTAILED"], False) == "consistent"
    assert relation_result_code(["ENTAILED", "UNDETERMINED"], False) == "conflict"
    assert relation_result_code(["REFUTED"], False) == "conflict"
    assert relation_result_code(["ENTAILED"], True) == "unresolved"
    assert relation_result_code([], False) == "unresolved"
    assert relation_result_code(["INCONSISTENT"], False) == "unresolved"
    assert relation_result_code(["unknown"], False) == "unresolved"
