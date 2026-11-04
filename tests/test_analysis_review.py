"""Included computations must reach the readable handoff without gaining a warrant.

These invented inputs test delivery semantics, not clinical suitability. Coverage
must never certify safety, proposed support must remain unconfirmed, and population
denominators must never transfer merely because results share an export.
"""

from copy import deepcopy
from pathlib import Path

import pytest
from openpyxl import load_workbook

from TrialLedger import reasoning_artifacts
from TrialLedger.analysis_review import review_priority_code, summaries
from TrialLedger.clinical_export import _blocker_text, export_review
from TrialLedger.layer2 import run


def _signal(kind, value, *, code="consistent", status="known", identity="invented"):
    return {
        "id": identity,
        "kind": kind,
        "code": code,
        "calculation_code": code,
        "value": value,
        "status": status,
        "basis": ["simulated choice: not an authenticated human exchange"],
        "rule": "invented:1",
        "blockers": [],
        "admission": {"code": "accepted", "application_blockers": []},
    }


def _payload(signals):
    return {
        "request": {"operation": "signals"},
        "response": {
            "operation": "signals",
            "code": "complete",
            "result": {"signals": signals},
            "problems": [],
        },
    }


def _table():
    return {
        "scope": "invented escalation cohort, one interim decision",
        "version": "draft1",
        "coverage": {"state": "covered"},
        "overlaps": [
            {
                "rows": ["A", "B"],
                "actions": ["continue", "continue"],
                "state": "disjoint",
                "same_action": True,
            }
        ],
        "prohibitions": [],
        "case_witnesses": [],
        "termination": "not_computed_static_table",
        "operating_characteristics": "not_computed",
    }


def test_priority_must_expose_returned_issues_before_open_and_completed_checks():
    assert review_priority_code("conflict", []) == "reported_issue"
    assert review_priority_code("consistent", ["gap"]) == "reported_issue"
    assert review_priority_code("unresolved", ["conflicting_actions"]) == "reported_issue"
    assert review_priority_code("consistent", ["violation"]) == "reported_issue"
    assert review_priority_code("unresolved", ["collection_plan_mismatch"]) == "reported_issue"
    assert review_priority_code("unresolved", []) == "open_check"
    assert review_priority_code("refused", []) == "open_check"
    assert review_priority_code("consistent", ["unresolved"]) == "open_check"
    assert review_priority_code("bounded", []) == "reported_result"
    assert review_priority_code("complete", []) == "reported_result"
    assert review_priority_code("permitted_only", []) == "reported_result"
    assert review_priority_code("INCONSISTENT", []) == "reported_issue"
    assert review_priority_code("UNDETERMINED", []) == "open_check"
    assert review_priority_code("OUT_OF_SCOPE", []) == "open_check"
    assert review_priority_code("UNSUPPORTED_QUERY", []) == "open_check"
    assert review_priority_code("ENTAILED", []) == "reported_result"
    assert review_priority_code("REFUTED", []) == "reported_result"


def test_priority_must_not_reinterpret_disjoint_overlap_unknown_or_future_codes():
    assert review_priority_code("consistent", ["disjoint", "overlap", "clear"]) == "reported_result"
    assert review_priority_code("future", []) == "unclassified"
    assert review_priority_code("", []) == "unclassified"
    assert review_priority_code("unknown", ["not_computed"]) == "unclassified"
    assert review_priority_code("consistent", []) == "reported_result"


def test_table_summary_is_one_row_without_disjoint_noise_and_never_certifies_safety():
    result = summaries([("a" * 64, _payload([_signal("decision_table", _table())]))])
    assert len(result) == 1
    row = result[0]
    assert row["canonical_ref"] == "/response/result/signals/0"
    assert row["scope"] == "invented escalation cohort, one interim decision"
    assert row["version"] == "draft1"
    assert "only the declared variables" in row["summary"]
    assert "0 different-action overlaps" in row["summary"]
    assert "no safety property checked" in row["summary"]
    assert "0 violations" not in row["summary"]
    text = " ".join(detail["text"] for detail in row["details"])
    assert "coverage does not establish clinical safety" in text
    assert "disjoint" not in text
    assert "operating characteristics: not_computed" in text


def test_table_violations_preserve_conditions_and_returned_case_profile():
    table = _table()
    profile = {"class": "Always"}
    table["prohibitions"] = [
        {"id": "no-escalation", "action": "escalate", "when": profile, "state": "violation"}
    ]
    table["case_witnesses"] = [
        {
            "kind": "prohibition_violation",
            "profile": profile,
            "rows": ["escalate-rule"],
            "actions": ["escalate"],
        }
    ]
    table["witness_summary"] = {
        "state": "truncated",
        "combinations_examined": 4,
        "combinations_total": 16,
        "witnesses_returned": 1,
        "unexamined_combinations": 12,
    }
    row = summaries([("a" * 64, _payload([_signal("decision_table", table, code="conflict")]))])[0]
    assert row["priority"] == "reported_issue"
    text = " ".join(detail["text"] for detail in row["details"])
    assert "no-escalation" in text and "violation" in text and "escalate-rule" in text
    assert "truncated" in text and "unexamined combinations 12" in text
    assert row["details"][2]["canonical_ref"].endswith("/case_witnesses/0")


def test_uncomputed_prohibition_results_are_neither_absent_declarations_nor_clearance():
    value = _table()
    value["coverage"] = None
    value["domain"] = {"state": "unresolved"}
    value["prohibition_coverage"] = {"state": "unresolved", "declared": 2}
    value["witness_summary"] = {"state": "not_computed", "reason": "domain_not_established_feasible"}
    row = summaries([("a" * 64, _payload([_signal("decision_table", value, code="unresolved")]))])[0]
    assert "2 action prohibitions declared; checks unresolved" in row["summary"]
    assert "not declared" not in row["summary"]
    text = " ".join(detail["text"] for detail in row["details"])
    assert "empty result list is not clearance" in text
    assert "Cases not computed: domain_not_established_feasible" in text
    assert "examined None" not in text


def test_proposed_calculation_must_not_be_rendered_as_admitted_or_known():
    signal = _signal("decision_table", _table(), code="unresolved", status="proposed")
    signal["calculation_code"] = "consistent"
    signal["admission"]["code"] = "proposed_refused"
    signal["blockers"] = ["proposed_refused:invented"]
    row = summaries([("a" * 64, _payload([signal]))])[0]
    assert row["code"] == "unresolved" and row["calculation_code"] == "consistent"
    assert row["standing"] == "proposed"
    assert row["blockers"] == ["proposed_refused:invented"]
    assert row["admission"]["code"] == "proposed_refused"


def test_numeric_summary_retains_returned_denominator_and_interval_without_source_transfer():
    value = {
        "universe": "optimization population",
        "total": 541,
        "counts": [{"id": "intersection", "lower": 29, "upper": 273}],
    }
    row = summaries(
        [("a" * 64, _payload([_signal("overlap", value, code="bounded", status="interpolated")]))]
    )[0]
    assert "29–273" in row["summary"] and "total: 541" in row["summary"]
    assert "437" not in str(row)
    assert row["standing"] == "interpolated"
    assert row["details"][0]["canonical_ref"] == "/response/result/signals/0/value/counts/0"


def test_estimand_summary_keeps_collection_mismatch_beside_unknown_actual_inputs():
    signal = _signal(
        "estimand",
        {
            "scope": "invented withdrawal cohort",
            "version": "draft1",
            "definition_state": "complete",
            "requirements": [
                {
                    "id": "after-stop",
                    "relevance": "required",
                    "relevance_status": "known",
                    "collection_alignment": "collection_plan_mismatch",
                    "collection_status": "interpolated",
                    "actual_input": "unresolved",
                    "actual_status": None,
                    "declaration": {"variable": "relapse", "window": "after discontinuation"},
                }
            ],
        },
        code="unresolved",
    )
    row = summaries([("a" * 64, _payload([signal]))])[0]
    assert row["priority"] == "reported_issue"
    assert "1 collection-plan mismatches" in row["summary"]
    assert "actual input unresolved" in row["details"][0]["text"]
    assert "standing interpolated" in row["details"][0]["text"]
    assert "estimation is not computed" in row["summary"]


def test_stage_review_keeps_unevaluated_gate_and_each_transition_standing():
    value = {
        "study": "NCT-invented",
        "snapshot": "source-v1",
        "transitions": [
            {
                "id": "response-selection",
                "source": "induction",
                "target": "withdrawal",
                "code": "bounded",
                "status": "interpolated",
                "basis": ["simulated response-selection assumption"],
                "source_stage": {
                    "population": "induction starters",
                    "total": 100,
                    "unit": "person",
                    "time": "baseline",
                },
                "target_stage": {"population": "responders", "total": 40, "unit": "person", "time": "week24"},
                "declaration": {"gate_ref": "response criterion not evaluated"},
                "population_result": {
                    "value": {
                        "universe": "induction",
                        "total": 100,
                        "counts": [{"id": "outside", "lower": 60, "upper": 60}],
                    }
                },
            }
        ],
    }
    row = summaries(
        [("a" * 64, _payload([_signal("stages", value, code="bounded", status="interpolated")]))]
    )[0]
    assert row["version"] == "source-v1"
    assert row["details"][0]["standing"] == "interpolated"
    assert "response criterion not evaluated" in row["details"][0]["text"]
    assert "simulated response-selection assumption" in row["details"][0]["text"]
    assert "60" in row["details"][1]["text"] and "total: 100" in row["details"][1]["text"]


def test_dependency_review_preserves_modes_and_does_not_turn_missing_alternative_into_failure():
    value = {
        "scope": "invented assay",
        "version": "v1",
        "rules": [
            {
                "id": "derive",
                "version": "v1",
                "state": "ready",
                "missing": ["alternative:observed"],
                "output": {"id": "endpoint", "mode": "modelled"},
            }
        ],
    }
    row = summaries([("a" * 64, _payload([_signal("dependencies", value)]))])[0]
    assert "0 blocked" in row["summary"]
    assert "modelled" in row["details"][0]["text"]
    assert "need not block an available alternative" in row["details"][0]["text"]


def test_managed_nested_result_owns_exact_child_address_not_an_invented_top_level_path():
    payload = {
        "response": {
            "operation": "design_session",
            "code": "complete",
            "result": {
                "analyses": [
                    {"id": "interim", "result": _payload([_signal("decision_table", _table())])["response"]}
                ],
            },
        }
    }
    row = summaries([("a" * 64, payload)])[0]
    assert row["canonical_ref"] == "/response/result/analyses/0/result/result/signals/0"
    assert row["analysis"].endswith(" / interim / invented")


def test_inclusion_does_not_merge_same_named_signals_or_mutate_results():
    payload = _payload([_signal("decision_table", _table())])
    before = deepcopy(payload)
    rows = summaries([("a" * 64, payload), ("b" * 64, payload)])
    assert len(rows) == 2
    assert rows[0]["analysis"] != rows[1]["analysis"]
    assert rows[0]["artifact"] != rows[1]["artifact"]
    assert payload == before


def test_definition_relationship_is_explicit_and_never_claims_purposeless_threshold_equality():
    binding = {
        "analysis": "adaptive",
        "address": "/meaning",
        "body": {"class": "Always"},
        "status": "interpolated",
        "resolution": "resolved",
        "basis": ["simulated binding"],
    }
    payload = {
        "response": {
            "operation": "design_session",
            "code": "complete",
            "result": {
                "analyses": [],
                "definition_checks": [
                    {
                        "id": "same-relapse",
                        "relation": "equivalent",
                        "code": "conflict",
                        "status": "interpolated",
                        "target": {"kind": "new_trial", "ref": "invented"},
                        "declaration": {"left": binding, "right": {**binding, "analysis": "estimand"}},
                        "basis": ["simulated sameness premise"],
                        "blockers": ["declared_relationship_conflict"],
                    }
                ],
            },
        }
    }
    row = summaries([("a" * 64, payload)])[0]
    assert row["canonical_ref"] == "/response/result/definition_checks/0"
    assert row["priority"] == "reported_issue"
    assert row["standing"] == "interpolated"
    assert "Declared relationship: equivalent" in row["summary"]
    assert "not proof that differently purposed thresholds must match" in row["summary"]
    assert row["details"][0]["canonical_ref"].endswith("/declaration/left")
    assert row["details"][0]["standing"] == "interpolated"


def test_unknown_related_operation_keeps_explicit_summary_and_refusal():
    payload = {
        "response": {
            "operation": "future",
            "code": "refused",
            "result": None,
            "problems": ["unknown_field:x"],
        }
    }
    row = summaries([("a" * 64, payload)])[0]
    assert row["standing"] is None and row["calculation_code"] == "Not summarized"
    assert row["blockers"] == ["unknown_field:x"] and row["code"] == "refused"
    assert "does not bind" in row["scope"]


@pytest.mark.parametrize("view", ["signals", "design_bounds", "source_assertions", "interpretations"])
def test_public_export_keeps_included_operation_in_markdown_and_workbook(tmp_path, view):
    session = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    main = reasoning_artifacts.save(tmp_path / "store", session, run(session))
    request = run({"operation": "describe", "view": view})["result"]["example"]
    related = reasoning_artifacts.save(tmp_path / "store", request, run(request))
    exported = export_review(tmp_path / "store", main["id"], tmp_path / "out", include=[related["id"]])
    text = Path(exported["decision_list"]).read_text()
    assert "Supporting analyses" in text
    assert "Included 1" in text
    assert f"artifacts/{related['id']}.json#/response" in text
    book = load_workbook(exported["workbook"])
    try:
        rows = list(book["Analysis review"].values)
        assert any(str(row[0]).startswith("Included 1") for row in rows[1:])
        assert "Findings" in book.sheetnames and "Analysis details" in book.sheetnames
    finally:
        book.close()


def test_issue_summary_precedes_consistent_table_even_when_included_later():
    clean = _signal("decision_table", _table())
    broken = _signal("decision_table", _table(), code="conflict", identity="broken")
    rows = summaries([("a" * 64, _payload([clean, broken]))])
    assert rows[0]["analysis"].endswith(" / broken")


def test_managed_decision_answers_are_not_duplicated_but_independent_checks_remain():
    logical = {
        "operation": "entailment",
        "code": "complete",
        "result": {
            "decision": {
                "result": "REFUTED",
                "query": '{"class":"Always"}',
                "proof": ["exclusion"],
                "status": "known",
                "blockers": [],
            },
        },
    }
    payload = {
        "response": {
            "operation": "design_session",
            "code": "complete",
            "result": {
                "decisions": [{"alternatives": [{"analysis": "chosen-option"}]}],
                "analyses": [
                    {"id": "chosen-option", "result": logical},
                    {
                        "id": "independent",
                        "result": logical,
                        "request": {"context": {"cohort": "withdrawal"}},
                    },
                ],
            },
        }
    }
    rows = summaries([("a" * 64, payload)])
    assert len(rows) == 1
    assert rows[0]["analysis"] == "Main / independent"
    assert rows[0]["code"] == "REFUTED"
    assert rows[0]["basis"] == ["exclusion"]
    assert rows[0]["scope"] == {"cohort": "withdrawal"}
    assert rows[0]["canonical_ref"] == "/response/result/analyses/1/result/result/decision"


def test_actual_public_table_violation_reaches_the_export_with_exact_witness(tmp_path):
    from TrialLedger.layer2.decision_tables import EXAMPLES

    data = deepcopy(EXAMPLES["decision_table"])
    data["prohibitions"] = [
        {
            "id": "never-escalate-one",
            "action": "escalate",
            "when": data["domains"][0]["values"][1],
        }
    ]
    request = {
        "operation": "signals",
        "signals": [
            {
                "id": "invented-safety",
                "kind": "decision_table",
                "data": data,
                "support": [
                    {
                        "id": "explicit",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": ["simulated design choice"],
                    }
                ],
            }
        ],
    }
    response = run(request)
    assert response["code"] == "complete", response
    assert response["result"]["signals"][0]["code"] == "conflict"
    stored = reasoning_artifacts.save(tmp_path / "store", request, response)
    exported = export_review(tmp_path / "store", stored["id"], tmp_path / "out")
    text = Path(exported["decision_list"]).read_text()
    assert "1 violations among 1 declared action prohibitions" in text
    assert "Returned prohibition_violation case" in text
    assert "never-escalate-one" in text
    assert "/value/case_witnesses/" in text


def test_known_signal_blockers_are_readable_but_unknown_codes_remain_unclassified():
    known = [
        "table_uncovered_case",
        "table_conflicting_actions",
        "table_forbidden_action",
        "estimand_collection_plan_mismatch:after-stop",
        "estimand_unresolved:after-stop",
        "dependency_blocked:derive",
        "dependency_unresolved:derive",
        "definition_proposed_refused",
        "definition_computation_refused",
        "definition_analysis_refused:child",
        "definition_empty_antecedent:left",
    ]
    text = _blocker_text(known)
    assert "Unclassified" not in text
    assert all(code in text for code in known)
    assert "Unclassified open item" in _blocker_text(["definition_future_code"])


def test_remaining_requirements_change_is_separate_from_the_verdict_in_export(tmp_path):
    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    response = run(request)
    response["answer_diff"] = {
        "decisions": [
            {
                "id": "fixture-requirements",
                "code": "requirements_changed",
                "axes": {
                    "question": "unchanged",
                    "answer": "unchanged",
                    "requirements": "changed",
                    "support": "unchanged",
                    "origin": "unchanged",
                    "wording": "unchanged",
                    "context": "unchanged",
                },
            }
        ],
        "analyses": [],
    }
    stored = reasoning_artifacts.save(tmp_path / "store", request, response)
    exported = export_review(tmp_path / "store", stored["id"], tmp_path / "out")
    text = Path(exported["decision_list"]).read_text()
    assert "Remaining requirements changed; verdict unchanged (requirements_changed)" in text
    assert "answer: unchanged; requirements: changed" in text
    book = load_workbook(exported["workbook"])
    try:
        rows = list(book["Changes"].values)
        assert rows[0][-1] == "Remaining requirements"
        assert rows[1][-1] == "changed"
    finally:
        book.close()


def test_long_analysis_details_are_losslessly_split_into_readable_sheet_parts(tmp_path):
    basis = "Long declared reference: " + "\n".join(str(number) + " α" * 40 for number in range(20))
    signal = _signal(
        "overlap",
        {"universe": "invented", "total": 10, "counts": [{"id": "intersection", "lower": 2, "upper": 4}]},
        code="bounded",
    )
    signal["basis"] = [basis]
    payload = _payload([signal])
    stored = reasoning_artifacts.save(tmp_path / "store", payload["request"], payload["response"])
    exported = export_review(tmp_path / "store", stored["id"], tmp_path / "out")
    book = load_workbook(exported["workbook"])
    try:
        rows = list(book["Analysis details"].iter_rows(min_row=2, values_only=True))
        basis_rows = rows[1:]
        reconstructed = "".join(row[1] for row in basis_rows)
        assert reconstructed == "Declared basis references: " + basis + "; rule: invented:1"
        assert all(len(row[1]) <= 320 and row[1].count("\n") <= 5 for row in basis_rows)
        assert len(basis_rows) > 1 and basis_rows[0][-1] == f"1/{len(basis_rows)}"
        assert "1 declared basis references" in book["Analysis review"]["H2"].value
    finally:
        book.close()


def test_declared_definition_changes_reach_the_readable_revision_handoff(tmp_path):
    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    response = run(request)
    response["answer_diff"] = {
        "decisions": [],
        "analyses": [],
        "definition_checks": [
            {
                "id": "shared-response",
                "code": "answer_changed",
                "axes": {"answer": "changed", "requirements": "unchanged"},
            }
        ],
    }
    stored = reasoning_artifacts.save(tmp_path / "store", request, response)
    exported = export_review(tmp_path / "store", stored["id"], tmp_path / "out")
    assert "shared-response: Clinical answer changed" in Path(exported["decision_list"]).read_text()
    book = load_workbook(exported["workbook"])
    try:
        assert book["Changes"]["A2"].value == "definition_checks"
        assert "/answer_diff/definition_checks/0" in book["Changes"]["I2"].hyperlink.target
    finally:
        book.close()
