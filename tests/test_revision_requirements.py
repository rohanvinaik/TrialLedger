"""Changing another requirement must not claim a stable profile verdict changed."""

import json
from copy import deepcopy

from tests.test_scope_routing import fact, requirement
from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import run
from TrialLedger.layer2.design_session import prepare_revision, revision_change_code
from TrialLedger.layer2.design_session_guide import EXAMPLE


def test_residual_change_has_the_same_axis_for_options_and_parent_decisions():
    request = deepcopy(EXAMPLE)
    source = request["session"]["premises"][0]
    other = deepcopy(source)
    other["id"] = "renal"
    other["payload"] = json.loads(a.canonical(requirement("renal", fact("renal"))))
    request["session"]["premises"].append(other)
    for analysis in request["session"]["analyses"]:
        analysis["uses"].append({"premise": "renal", "slot": "assertions", "projection": "identity"})
    before = run(request)
    following = deepcopy(request["session"])
    following["revision"] = "two"
    following["premises"][1]["payload"]["body"] = json.loads(a.canonical(fact("changed-renal")))
    after = run(prepare_revision(request, before, following))
    assert after["code"] == "complete", after
    for field in ("analyses", "decisions"):
        for change in after["answer_diff"][field]:
            assert change["code"] == "requirements_changed"
            assert change["axes"]["answer"] == "unchanged"
            assert change["axes"]["requirements"] == "changed"
    assert request["session"]["premises"][1]["payload"]["body"] != following["premises"][1]["payload"]["body"]


def test_requirements_change_code_never_hides_a_real_verdict_or_question_change():
    assert (
        revision_change_code(True, True, True, True, True, True, True, True, True, False, False)
        == "requirements_changed"
    )
    assert (
        revision_change_code(True, True, True, True, True, False, True, True, True, False, False)
        == "answer_changed"
    )
    assert (
        revision_change_code(True, True, True, False, True, True, True, True, True, False, False)
        == "question_changed"
    )


def test_source_admission_inspection_does_not_invent_an_unknown_clinical_answer():
    from TrialLedger.layer2.design_session import _analysis_answer

    inspection = {
        "id": "source",
        "target": {"kind": "historical"},
        "request": {"operation": "source_assertions"},
        "result": {
            "code": "complete",
            "metadata": {"kind": "inspection", "findings": []},
            "result": {"source": {"nct": "NCT00000001"}, "analyses": []},
        },
    }
    projected = _analysis_answer(inspection, {"effective_premises": []})
    assert projected["state"] == "comparable"
    assert projected["answer"] == []
    assert projected["context"] == {"inspection": inspection["result"]["result"]}


def test_default_finite_table_reaches_the_managed_session_without_changing_limits():
    from TrialLedger.layer2.design_session_guide import EXAMPLE

    request = deepcopy(EXAMPLE)
    session = request["session"]
    table = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]["signal_examples"][
        "decision_table"
    ]["signals"][0]
    session["premises"] = [
        {
            "id": "table",
            "kind": "signal",
            "payload": table,
            "origin": {"kind": "user_choice", "ref": "simulated:table", "source": None, "analysis": None},
            "depends_on": [],
        }
    ]
    session["decisions"] = []
    session["analyses"] = [
        {
            "id": "table",
            "operation": "signals",
            "target": session["target"],
            "parameters": {},
            "uses": [{"premise": "table", "slot": "signals", "projection": "identity"}],
        }
    ]
    response = run(request)
    assert response["code"] == "complete", response
    assert response["result"]["analyses"][0]["result"]["result"]["signals"][0]["code"] == "consistent"
    assert response["result"]["limits"] == session["limits"]
    assert response["work"]["solver_work_reserved"] < session["limits"]["max_solver_work"]


def test_multi_member_enum_equality_is_refused_before_it_can_claim_exhaustion():
    table = deepcopy(
        run({"operation": "describe", "view": "signals", "detail": "full"})["result"]["signal_examples"][
            "decision_table"
        ]
    )
    data = table["signals"][0]["data"]
    literal = deepcopy(data["domains"][0]["values"][0])
    literal["value"] = {"class": "Value", "kind": "enum", "comparison": "eq", "members": ["clear", "concern"]}
    data["domains"] = [{"id": "safety", "values": [literal]}]
    data["rows"] = [{"id": "choose", "when": {"class": "Always"}, "action": "escalate"}]
    unsafe = deepcopy(literal)
    unsafe["value"]["members"] = ["concern"]
    data["prohibitions"] = [{"id": "no-concerning-dose", "when": unsafe, "action": "escalate"}]
    result = run(table)
    assert result["code"] == "refused"
    assert result["result"] is None
    assert result["problems"] == ["members_do_not_fit_comparison"]
