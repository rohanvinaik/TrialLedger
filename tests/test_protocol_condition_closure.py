"""A declared assessment condition reaches every check that consumes it, directly or through a link.

Composition audit (2026-11-05): a responder-only (conditional) assessment kept its schedule check conditional,
but its linked collection's contribution to the estimand lost the condition; the estimand's alignment read
`aligned`, settled. Conditions now follow the reference closure of what a check consumes, plain signals carry
their applicability, and the headline never reads a conditionally applied result as settled.
"""

from tests.test_protocol_review_repairs import _revise
from tests.test_protocol_session_replay import _adult_body, _session, adopt
from tests.test_protocol_walkthrough_repairs import _estimand_with_linked_collection
from TrialLedger.layer2 import protocol_view, run


def _responder_only(entailed_by: list | None = None) -> dict:
    request = _estimand_with_linked_collection("collect")
    adopt(request, "collection")
    protocol = request["session"]["protocol"]
    next(o for o in protocol["objects"] if o["id"] == "week12")["data"]["condition"] = _adult_body(
        _session("84")
    )
    if entailed_by is not None:
        protocol["checks"][0]["bindings"] = [
            {"projection": "condition_applicability", "premises": entailed_by}
        ]
    return request


def _estimand(reply: dict) -> tuple[dict, dict]:
    assert reply["code"] == "complete", reply.get("problems")
    check = next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == "estimand-check")
    return check, check["children"][0]


def test_the_linked_assessment_condition_reaches_the_estimand_receipt_and_signal():
    check, child = _estimand(run(_responder_only()))
    assert [row["object"] for row in child["receipt"]["conditions"]] == ["week12"]
    (signal,) = child["signals"]
    assert signal["kind"] == "estimand"
    assert signal["application"] == "conditional"


def test_the_headline_never_reads_a_conditionally_applied_alignment_as_settled():
    reply = run(_responder_only())
    estimand = [f for f in reply["metadata"]["findings"] if f["kind"].startswith("estimand")]
    assert estimand
    assert not any(f["disposition"] == "settled" for f in estimand)
    alignment = next(f for f in estimand if f["kind"] == "estimand_collection_alignment")
    assert alignment["disposition"] == "conditional"


def test_the_view_and_open_items_say_the_result_holds_only_under_the_condition():
    view = protocol_view.view(run(_responder_only())["result"])
    check = next(c for c in view["checks"] if c["id"] == "estimand-check")
    assert [f["application"] for f in check["findings"]] == ["conditional"]
    assert [f["kind_of_finding"] for f in check["findings"]] == ["conditional"]
    texts = [i["text"] for i in view["open_items"] if i["check"] == "estimand-check"]
    assert any("only where the declared assessment condition applies" in t for t in texts)


def test_a_condition_proven_by_declared_premises_makes_the_estimand_unconditional():
    reply = run(_responder_only(entailed_by=["adult"]))
    _, child = _estimand(reply)
    assert child["signals"][0]["application"] == "unconditional"
    alignment = next(f for f in reply["metadata"]["findings"] if f["kind"] == "estimand_collection_alignment")
    assert alignment["disposition"] == "settled"


def test_without_a_condition_the_estimand_is_unchanged_and_unconditional():
    request = _estimand_with_linked_collection("collect")
    adopt(request, "collection")
    _, child = _estimand(run(request))
    assert child["receipt"]["conditions"] == []
    assert child["signals"][0]["application"] == "unconditional"


def test_adding_the_condition_is_a_revision_change_on_the_estimand_check():
    def responder_only(session):
        week12 = next(o for o in session["protocol"]["objects"] if o["id"] == "week12")
        week12["data"]["condition"] = _adult_body(_session("84"))
        week12["version"] = "invented-v1-responders"
        session["premises"].append(
            {
                **next(p for p in session["premises"] if p["id"] == "adopt:week12:invented-v1"),
                "id": "adopt:week12:invented-v1-responders",
                "payload": {
                    "objects": [{"id": "week12", "version": "invented-v1-responders"}],
                    "status": "known",
                    "resolution": "resolved",
                },
            }
        )
        week12["support"] = ["adopt:week12:invented-v1-responders"]

    first = _estimand_with_linked_collection("collect")
    adopt(first, "collection")
    reply = _revise(first, responder_only)
    row = next(r for r in reply["answer_diff"]["protocol_checks"] if r["id"] == "estimand-check")
    assert "verdict" in row["axes"]


# --- Linked objects' closure gates standing and adoption (Rohan, 2026-11-05) -------------------------------


def _schedule_beside(request: dict) -> dict:
    import copy

    protocol = request["session"]["protocol"]
    protocol["checks"].insert(0, copy.deepcopy(_session("84")["session"]["protocol"]["checks"][0]))
    return request


def test_an_unadopted_assessment_behind_a_linked_collection_withholds_the_estimand_finding():
    request = _estimand_with_linked_collection("collect")
    adopt(request, "collection")
    week12 = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "week12")
    week12["support"] = []
    _, child = _estimand(run(request))
    (signal,) = child["signals"]
    assert "week12" in child["receipt"]["closure"]
    assert signal["admission"]["code"] != "accepted"


def test_an_unadopted_estimand_named_by_a_collection_does_not_withhold_schedule_timing():
    request = _schedule_beside(_estimand_with_linked_collection("collect"))
    adopt(request, "collection")
    estimand = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "estimand")
    estimand["support"] = []
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    schedule = next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == "week12-schedule")
    child = schedule["children"][0]
    assert "estimand" not in child["receipt"]["closure"]
    rows = child["signals"][0]["claim_admission"]
    assert {row["admission"] for row in rows} == {"accepted"}


# --- Standing on every check row; check-local bindings named (Rohan, 2026-11-05) ----------------------------


def test_an_inherited_condition_without_its_own_binding_is_named_as_such():
    view = protocol_view.view(run(_responder_only())["result"])
    check = next(c for c in view["checks"] if c["id"] == "estimand-check")
    assert check["inherited_conditions"] == ["week12"] and check["applicability_binding"] is False
    texts = [i["text"] for i in view["open_items"] if i["check"] == "estimand-check"]
    assert any("declare a condition_applicability binding on this check" in t for t in texts)


def test_with_its_own_binding_the_inheriting_check_names_no_missing_binding():
    view = protocol_view.view(run(_responder_only(entailed_by=["adult"]))["result"])
    check = next(c for c in view["checks"] if c["id"] == "estimand-check")
    assert check["applicability_binding"] is True
    assert not any("declare a condition_applicability binding" in i["text"] for i in view["open_items"])


def test_every_check_row_carries_the_weakest_standing_it_rests_on_apart_from_conditional():
    from TrialLedger import clinical_delivery

    request = _estimand_with_linked_collection("collect")
    adopt(request, "collection")
    estimand = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "estimand")
    estimand["standing"] = {
        "status": "interpolated",
        "resolution": "resolved",
        "basis": ["user:invented default"],
    }
    view = clinical_delivery.protocol_delivery_view(run(request)["result"])
    summary = next(c for c in view["check_summaries"] if c["id"] == "estimand-check")
    assert summary["standing"] == "interpolated"
    assert summary["conditional"] is False
