"""Repairs from the post-freeze producer/consumer trace audit (interface/trace-map.md, section 5)."""

import copy
import json

from tests.test_protocol_options import _base
from tests.test_protocol_replay_budgets import build, with_limits
from tests.test_protocol_review_repairs import _revise
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.layer2 import protocol_statistics, protocol_view, result_semantics, run


def test_f1_a_revision_that_withdraws_a_check_completes_and_reports_it(tmp_path):
    first = _base(optional=True)
    held = delivery.execute(first, store=tmp_path)
    following = copy.deepcopy(first["session"])
    following["revision"] = "two"
    following["protocol"]["checks"] = following["protocol"]["checks"][:1]
    following["protocol"]["sections"] = [
        {**section, "objects": section["objects"]} for section in following["protocol"]["sections"]
    ]
    revised = delivery.revise(tmp_path, held["artifact"]["id"], session=following)
    assert revised["code"] == "complete", revised.get("problems")
    rows = {row["id"]: row for row in revised["answer_diff"]["protocol_checks"]}
    withdrawn = [row for row in rows.values() if row["code"] == "withdrawn"]
    assert withdrawn and all(row["axes"] == [] and row["changes"] == [] for row in withdrawn)


def test_f2_a_design_too_wide_to_render_returns_limit_not_a_crash():
    data = {
        "scope": "invented",
        "model": "fixed_n_iid_bernoulli",
        "direction": "greater",
        "n": 512,
        "critical_count": 200,
        "p0": "12345678901234567890/98765432109876543210",
        "p1": "1/2",
        "assumptions": [
            {
                "role": role,
                "ref": "premise:a",
                "version": "1",
                "status": "known",
                "resolution": "resolved",
                "basis": ["x"],
            }
            for role in ("fixed_n", "iid_binary", "alignment")
        ],
    }
    result = protocol_statistics.check("binomial_design", data, [])
    assert result["code"] == "limit"
    assert "binomial_bit_limit" in result["blockers"]
    assert result["value"]["null_rejection_probability"] is None


def test_f3_protocol_codes_are_classified_never_unclassified():
    for code in (
        "definition_protocol_child_refused:check-a",
        "definition_protocol_child_missing:check-a",
        "projection_scope_mismatch",
        "projection_collection_plan_conflict",
        "adoption_stale_version",
        "session_work_limit",
        "external_method_not_computed",
    ):
        assert result_semantics.cause_kind(code) != "unclassified", code


def _limited_reply() -> dict:
    """Three schedule checks; at one unit under the total the last one is stopped by the session limit."""
    request = build(checks=3, collected=1)
    total = run(with_limits(request, max_solver_work=10_000))["work"]["solver_work_reserved"]
    reply = run(with_limits(build(checks=3, collected=1), max_solver_work=total - 1))
    assert reply["code"] == "complete", reply.get("problems")
    return reply


def test_f4_a_limited_check_is_an_open_item_in_the_headline_not_silence():
    reply = _limited_reply()
    findings = [f for f in reply["metadata"]["findings"] if f["kind"] == "protocol_check"]
    assert len(findings) == 1, reply["metadata"]["findings"]
    assert [c["code"] for c in findings[0]["causes"]] == ["session_work_limit"]
    assert (findings[0]["completion"], findings[0]["disposition"]) == ("limited", "not_computed")
    assert reply["summary"]["dispositions"].get("not_computed", 0) >= 1


def test_f4_an_external_method_check_counts_in_the_headline():
    card = run({"operation": "describe", "view": "protocol", "detail": "full"})["result"]
    prepared = run(copy.deepcopy(card["examples"]["external_method"]))
    reply = run(prepared["result"]["request"])
    findings = [f for f in reply["metadata"]["findings"] if f["kind"] == "protocol_check"]
    assert findings and findings[0]["completion"] == "unsupported"
    assert reply["summary"]["findings"] >= 1


def test_f5_open_items_word_projection_codes():
    view = protocol_view.view(_limited_reply()["result"])
    texts = [item["text"] for item in view["open_items"]]
    assert texts and not any(text.startswith("Projection unresolved:") for text in texts)
    assert any("work limit" in text for text in texts)


def test_the_card_defines_every_binomial_assumption_role():
    card = json.dumps(run({"operation": "describe", "view": "protocol"})["result"])
    assert "alignment (the population, endpoint and analysis set correspond" in card


def test_unrevised_session_still_revises_after_a_withdrawn_row():
    """F1 also reached the compact reply: a withdrawn row must render there."""
    first = _base(optional=True)

    def drop(session):
        session["protocol"]["checks"] = session["protocol"]["checks"][:1]

    reply = _revise(first, drop)
    assert reply["code"] == "complete"
