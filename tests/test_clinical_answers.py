"""Clinical projection conserves effective outcomes and separates answer/support/origin changes."""

import dataclasses
import json
from copy import deepcopy

import pytest

from TrialLedger.layer2 import entail, result_semantics, source_evidence
from TrialLedger.layer2.assertions import Literal, Predicate, Rule, ScopedAssertion, Subject, Value, canonical
from TrialLedger.layer2.clinical_answers import change_projection, project
from TrialLedger.layer2.entail_explanations import explain


def fact(name="A"):
    return Literal(Subject("participant"), Predicate("condition_status", name), Value("boolean"))


def rule(identity, body, status="known"):
    return ScopedAssertion(
        identity,
        "caller:" + identity,
        "required",
        body,
        rule=Rule("caller", "1"),
        status=status,
        resolution="resolved",
    )


def result(assertions, query):
    decision = entail.decide(assertions, query)
    return {
        "decision": dataclasses.asdict(decision),
        "premises": [json.loads(canonical(a)) for a in assertions],
        "explanations": explain(assertions, query, entail.EVERYONE, decision, 65536),
    }


def test_projection_reads_metadata_without_promoting_or_mutating():
    payload = result((rule("first", fact()),), fact())
    before = deepcopy(payload)
    view = project("entailment", payload)
    row = view["findings"][0]
    assert payload == before
    assert row["outcome"] == "ENTAILED" and row["standing"] == "known"
    assert row["canonical_ref"] == "/result/decision"
    assert row["support"]["proof"] == ["first"]
    assert row["origins"] == [{"premise": "first", "criterion_ref": "caller:first"}]
    assert row["scope"]["query"]["class"] == "Literal"


def test_unrelated_input_echo_does_not_change_any_clinical_axis():
    before = result(
        (rule("first", fact()), dataclasses.replace(rule("irrelevant", fact("B")), modality="descriptive")),
        fact(),
    )
    after = deepcopy(before)
    after["premises"][1]["criterion_ref"] = "caller:new-irrelevant-origin"
    assert change_projection("entailment", before) == change_projection("entailment", after)


def test_execution_check_counts_are_not_a_support_change():
    before = result((rule("first", fact()),), fact())
    after = deepcopy(before)
    after["explanations"]["checks"]["decisions"] += 2
    assert change_projection("entailment", before) == change_projection("entailment", after)


def test_same_verdict_with_weaker_support_remains_visible():
    before = result((rule("first", fact()),), fact())
    after = result((rule("first", fact(), "interpolated"),), fact())
    old = change_projection("entailment", before)
    new = change_projection("entailment", after)
    assert old["answer"] == new["answer"] and old["origin"] == new["origin"]
    assert old["support"] != new["support"]


def test_deciding_origin_changes_without_inventing_a_new_answer():
    before = result((rule("first", fact()),), fact())
    after = deepcopy(before)
    after["premises"][0]["criterion_ref"] = "caller:new-origin"
    old = change_projection("entailment", before)
    new = change_projection("entailment", after)
    assert old["answer"] == new["answer"] and old["support"] == new["support"]
    assert old["origin"] != new["origin"]


def test_session_can_supply_deciding_origin_context_without_input_churn():
    payload = result(
        (rule("first", fact()), dataclasses.replace(rule("other", fact("B")), modality="descriptive")),
        fact(),
    )
    payload["effective_premises"] = [
        {"id": "first", "origin": {"kind": "user_choice", "ref": "exchange-1"}},
        {"id": "other", "origin": {"kind": "user_choice", "ref": "other-exchange"}},
    ]
    before = change_projection("entailment", payload)
    changed = deepcopy(payload)
    changed["effective_premises"][1]["origin"]["ref"] = "new-irrelevant-exchange"
    assert change_projection("entailment", changed) == before
    changed["effective_premises"][0]["origin"]["ref"] = "exchange-2"
    assert change_projection("entailment", changed)["origin"] != before["origin"]


def test_displayed_independent_requirement_retains_its_deciding_origin():
    before = result((rule("first", fact()), rule("other", fact("B"))), fact())
    after = deepcopy(before)
    after["premises"][1]["criterion_ref"] = "caller:revised-independent-requirement-origin"
    old = change_projection("entailment", before)
    new = change_projection("entailment", after)
    assert before["decision"]["result"] == after["decision"]["result"] == "ENTAILED"
    assert old["answer"] == new["answer"] and old["support"] == new["support"]
    assert old["origin"] != new["origin"]
    assert any(
        condition["relation"] == "required_by_criteria"
        and condition["body"] == json.loads(canonical(fact("B")))
        for condition in before["explanations"]["conditions"]
    )


def test_numeric_bounds_change_answer_even_with_unchanged_bounded_code():
    before = {
        "signals": [
            {
                "id": "overlap",
                "kind": "overlap",
                "code": "bounded",
                "calculation_code": "bounded",
                "value": {"counts": [{"id": "intersection", "lower": 710, "upper": 2251}], "total": 4744},
                "status": "known",
                "basis": ["source:table"],
                "blockers": [],
            }
        ]
    }
    after = deepcopy(before)
    after["signals"][0]["value"]["counts"][0]["lower"] = 711
    old = change_projection("signals", before)
    new = change_projection("signals", after)
    assert old["answer"] != new["answer"] and old["support"] == new["support"]


def session_decision():
    return {
        "id": "choose",
        "question": "Choose A or B?",
        "code": "design_choice",
        "standing": "known",
        "origin": {"kind": "computed", "refs": []},
        "origin_refs": [],
        "input_origins": [{"premise": "unrelated", "origin": {"ref": "old"}}],
        "target": {"kind": "new_trial", "ref": "draft"},
        "coverage": "represented_restriction",
        "coverage_limit": "This restriction only.",
        "selected": None,
        "alternatives": [
            {
                "id": "A",
                "label": "A",
                "code": "feasible",
                "query": {"class": "Literal", "value": "A"},
                "warrant": {
                    "result": "UNDETERMINED",
                    "proof": ["first"],
                    "status": None,
                    "blockers": ["undecided_by_constraints"],
                },
                "feasibility_status": "known",
                "analysis_result_digest": "old-A",
            },
            {
                "id": "B",
                "label": "B",
                "code": "feasible",
                "query": {"class": "Literal", "value": "B"},
                "warrant": {
                    "result": "UNDETERMINED",
                    "proof": ["first"],
                    "status": None,
                    "blockers": ["undecided_by_constraints"],
                },
                "feasibility_status": "known",
                "analysis_result_digest": "old-B",
            },
        ],
        "distinctions": [],
    }


def test_session_decision_omits_audit_carrier_changes_but_preserves_choices():
    before = {"decisions": [session_decision()]}
    after = deepcopy(before)
    after["decisions"][0]["input_origins"][0]["origin"]["ref"] = "irrelevant-new"
    after["decisions"][0]["alternatives"][0]["analysis_result_digest"] = "new-A"
    assert change_projection("design_session", before) == change_projection("design_session", after)
    after["decisions"][0]["selected"] = {"alternative": "A", "origin": "user", "basis": ["exchange-2"]}
    assert (
        change_projection("design_session", before)["answer"]
        != change_projection("design_session", after)["answer"]
    )


def test_unknown_result_stays_unknown_and_retains_complete_value():
    payload = {"future": {"zero": 0, "missing": None, "explicit_false": False}}
    row = project("future_operation", payload)["findings"][0]
    assert row["disposition"] == "unclassified" and row["completion"] == "unclassified"
    assert row["values"]["unclassified"] == payload


def test_conditional_proof_keeps_its_deciding_origin_even_when_original_verdict_has_none():
    from tests.test_entail_explanations import fact, number, rule

    payload = result((rule("af", number(1200, "ge"), applicability=fact()),), number(900))
    payload["decision"]["proof"] = ()
    row = project("entailment", payload)["findings"][0]
    assert row["outcome"] == "UNDETERMINED" and row["support"]["proof"] == []
    assert row["conditions"][0]["warrant"]["proof"] == ["af"]
    assert row["origins"] == [{"premise": "af", "criterion_ref": "caller:af"}]


def test_witness_projection_retains_exact_count_allowance_population_and_bridge():
    from TrialLedger.layer2 import run

    example = run({"operation": "describe", "view": "design_bounds"})["result"]["example"]
    payload = run(example)["result"]
    view = project("design_bounds", payload)
    rows = [row for row in view["findings"] if row["kind"] == "witness"]
    assert rows
    for row in rows:
        raw = source_evidence._selected({"result": payload}, row["canonical_ref"])
        for name in (
            "count_lower",
            "count_upper",
            "count_kind",
            "denominator",
            "max_exceptions",
            "direction",
        ):
            assert row["values"][name] == raw[name]
        assert row["scope"]["population"] == raw["population"]
        assert row["support"]["basis"] == list(raw["basis"])
        assert row["standing"] == raw["status"]


def test_null_result_is_not_a_settled_negative():
    row = project("entailment", None)["findings"][0]
    assert row["disposition"] == "unclassified" and row["values"]["unclassified"] is None


@pytest.mark.parametrize(
    "operation",
    [
        "entailment",
        "coordinates",
        "corpus",
        "design_bounds",
        "signals",
        "interpretations",
        "source_assertions",
        "evidence_requests",
        "design_session",
    ],
)
def test_current_operation_projection_retains_every_effective_metadata_finding(operation):
    from TrialLedger.layer2 import run

    guide = run({"operation": "describe", "view": operation})["result"]
    response = run(guide["example"])
    assert response["code"] == "complete"
    payload = response["result"]
    metadata = result_semantics.metadata(operation, payload)
    view = project(operation, payload)
    assert [r["path"] for r in view["findings"]] == [r["path"] for r in metadata["findings"]]
    for finding, original in zip(view["findings"], metadata["findings"], strict=True):
        assert finding["outcome"] == original["logical_result"]
        assert finding["standing"] == original["standing"]
        source_evidence._selected({"result": payload}, finding["canonical_ref"])
