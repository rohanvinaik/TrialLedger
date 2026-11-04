"""Positive and MUST-NOT handoff contracts; all clinical premises are invented."""

import json
from copy import deepcopy
from pathlib import Path

import openpyxl
import pytest
from test_clinical_export import retained
from test_session_revision_delivery import request

from TrialLedger import clinical_export as export
from TrialLedger import reasoning_artifacts as artifacts
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.layer2 import run


@pytest.mark.parametrize("operation", ["source_assertions", "interpretations"])
def test_related_readings_export_without_assuming_managed_analysis_ids(tmp_path, operation):
    payload = run({"operation": "describe", "view": operation, "detail": "full"})["result"]["example"]
    result = run(payload)
    assert result["code"] == "complete"
    held = artifacts.save(tmp_path / "store", payload, result)["id"]
    main = retained(tmp_path / "store")["id"]
    answer = export.export_review(tmp_path / "store", main, tmp_path / "out", include=[held])
    canonical = json.loads((Path(answer["folder"]) / "artifacts" / f"{held}.json").read_text())
    assert canonical["response"]["result"] == json.loads(json.dumps(result["result"]))
    book = openpyxl.load_workbook(answer["workbook"])
    rows = list(book["Findings"].values)[1:]
    assert any(r[0] == "Related analysis" and r[1] == operation for r in rows)
    assert any(r[3] == "proposed" for r in rows)
    assert all(r[0] != "A-check" for r in rows if r[1] == operation)


@pytest.mark.parametrize(
    "operation,path,count,expected",
    [
        ("design_session", "/result/analyses/0/result", 1, "managed_analysis"),
        ("design_session", "/result/analyses/1", 2, "managed_analysis"),
        ("design_session", "/result/analyses/1", 1, "operation_result"),
        ("design_session", "/result/analyses/0", 0, "operation_result"),
        ("source_assertions", "/result/analyses/0/result", 1, "operation_result"),
        ("interpretations", "/result/analyses/0/result", 1, "operation_result"),
        ("design_session", "/result/analyses", 2, "operation_result"),
        ("design_session", "/result/other/0", 2, "operation_result"),
        ("design_session", "x/result/analyses/0", 2, "operation_result"),
        ("design_session", "/result/analyses/-1", 2, "operation_result"),
        ("design_session", "/result/analyses/a", 2, "operation_result"),
        ("design_session", "", 2, "operation_result"),
    ],
)
def test_finding_owner_must_not_assign_cross_operation_or_unowned_ids(operation, path, count, expected):
    assert export.finding_owner_code(operation, path, count) == expected


def permission_session(status="known"):
    payload = request()
    session = payload["session"]
    premise = session["premises"][0]["payload"]
    premise["modality"] = "permitted"
    premise["status"] = status
    condition = deepcopy(premise["body"])
    condition["predicate"]["key"] = "B-treated"
    premise["applicability"] = condition
    target = session["target"]
    options = []
    session["analyses"] = []
    for id, q in [("attempt", premise["body"]), ("no-attempt", {"class": "Not", "part": premise["body"]})]:
        query = {"class": "AllOf", "parts": [deepcopy(condition), deepcopy(q)]}
        session["analyses"].append(
            {
                "id": id,
                "operation": "entailment",
                "target": deepcopy(target),
                "parameters": {"query": query},
                "uses": [{"premise": "A", "slot": "assertions", "projection": "identity"}],
            }
        )
        options.append({"id": id, "label": id, "analysis": id, "query": deepcopy(query)})
    session["decisions"] = [
        {
            "id": "permission",
            "question": "May we rescreen after treatment?",
            "target": deepcopy(target),
            "coverage": "represented_restriction",
            "alternatives": options,
            "selected": None,
        }
    ]
    return payload


@pytest.mark.parametrize("status", ["known", "interpolated"])
def test_primary_handoff_preserves_permission_condition_support_and_nonrequirement(tmp_path, status):
    result = delivery.execute(permission_session(status), store=tmp_path / "store")
    option = result["decision_view"][0]["options"][0]
    mention = option["permissions"][0]
    assert mention["standing"] == status
    assert mention["criterion_ref"] == "invented:user:A"
    assert mention["rule"]["id"] == "invented-declared"
    assert "B-treated" in mention["applicability"]["text"]
    assert option["logical_result"] == "UNDETERMINED"
    answer = export.export_review(tmp_path / "store", result["artifact"]["id"], tmp_path / "out")
    book = openpyxl.load_workbook(answer["workbook"])
    rows = list(book["Permissions"].values)
    assert len(rows) == 3
    assert rows[1][6] == status and "B-treated" in rows[1][4]
    assert book["Decision list"].cell(2, 10).value
    assert book["Options"].cell(2, 14).value
    text = Path(answer["decision_list"]).read_text()
    assert "Permission mentions:" in text
    assert "neither a requirement nor complete entry eligibility" in text
    assert "B-treated" in text
    assert book["Decision list"].freeze_panes == "B2"
    assert book["Options"].freeze_panes == "C2"
    assert "attempt:" in book["Decision list"].cell(2, 5).value
    assert "no-attempt:" in book["Decision list"].cell(2, 5).value


def test_proposed_permission_must_not_be_rendered_as_accepted(tmp_path):
    result = delivery.execute(permission_session("proposed"), store=tmp_path / "store")
    for option in result["decision_view"][0]["options"]:
        assert option["permissions"][0]["standing"] == "proposed"
        assert option["permissions"][0]["blockers"]
        assert option["feasibility"] != "feasible"
    answer = export.export_review(tmp_path / "store", result["artifact"]["id"], tmp_path / "out")
    book = openpyxl.load_workbook(answer["workbook"])
    assert book["Permissions"].cell(2, 7).value == "proposed"
    assert "not been confirmed" in book["Options"].cell(2, 14).value


def test_optional_exact_query_must_not_claim_both_declared_options_survive():
    text = export._blocker_text(["undecided_by_constraints"])
    assert "exact query" in text
    assert "negation" in text
    assert "Both sides remain possible" not in text


@pytest.mark.parametrize(
    "kind,old_kind,new_kind,old,new,reference,expected",
    [
        ("assertion", "user_choice", "user_choice", "old", "new", "old", "rebind_adoption"),
        ("source_assertion", "user_choice", "user_choice", "old", "new", "old", "preserve_reference"),
        ("assertion", "source_rule", "user_choice", "old", "new", "old", "preserve_reference"),
        ("assertion", "user_choice", "source_interpretation", "old", "new", "old", "preserve_reference"),
        ("assertion", "user_choice", "user_choice", "", "new", "", "preserve_reference"),
        ("assertion", "user_choice", "user_choice", "old", "", "old", "preserve_reference"),
        ("assertion", "user_choice", "user_choice", "old", "new", "source:edition", "preserve_reference"),
        ("assertion", "user_choice", "user_choice", "old", "new", "old#source", "preserve_reference"),
    ],
)
def test_adoption_reference_must_not_rewrite_independent_or_nonchoice_basis(
    kind,
    old_kind,
    new_kind,
    old,
    new,
    reference,
    expected,
):
    assert delivery.adoption_reference_code(kind, old_kind, new_kind, old, new, reference) == expected


def test_changed_choice_rebinds_own_exchange_but_not_source_warrants_or_standing(tmp_path):
    payload = request()
    item = payload["session"]["premises"][0]
    old = item["origin"]["ref"]
    item["payload"]["criterion_ref"] = old
    item["payload"]["rule"]["warrants"] = [old, "ctg:independent-source#address"]
    before = deepcopy(payload)
    held = delivery.execute(payload, store=tmp_path)
    edits = [
        {
            "op": "replace",
            "path": "/premises/0/payload/status",
            "value": "interpolated",
            "origin": dict(item["origin"], ref="invented:new-choice"),
        }
    ]
    revised = delivery.revise(tmp_path, held["artifact"]["id"], revision="two", edits=edits)
    current = artifacts.load(tmp_path, revised["artifact"]["id"])
    changed = current["request"]["session"]["premises"][0]["payload"]
    assert changed["criterion_ref"] == "invented:new-choice"
    assert changed["rule"]["warrants"] == ["invented:new-choice", "ctg:independent-source#address"]
    assert changed["status"] == "interpolated"
    assert changed["rule"]["version"] == "1"
    assert payload == before
    assert artifacts.load(tmp_path, held["artifact"]["id"])["request"] == before
    reviewed = current["response"]["delivery"]["edits"]
    assert len(reviewed) == 3
    assert reviewed[1]["before"] == old and reviewed[1]["after"] == "invented:new-choice"


def test_malformed_replacement_reaches_named_validation_not_a_reference_keyerror(tmp_path):
    payload = request()
    held = delivery.execute(payload, store=tmp_path)
    bad = deepcopy(payload["session"]["premises"])
    del bad[0]["kind"]
    bad[0]["payload"]["status"] = "interpolated"
    with pytest.raises(ValueError):
        delivery.revise(
            tmp_path,
            held["artifact"]["id"],
            revision="two",
            edits=[{"op": "replace", "path": "/premises", "value": bad}],
        )
