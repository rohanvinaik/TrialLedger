"""Repairs from the wave-3 cold walkthroughs (ALS/MS neurology, TB efficacy, CKD outcomes; 2026-11-04)."""

import copy
import json
from pathlib import Path

from tests.test_protocol_session_replay import new_edition
from TrialLedger.layer2 import run, session_state

FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures"
)


def _example() -> dict:
    return copy.deepcopy(run({"operation": "describe", "view": "protocol"})["result"]["example"])


def _adopted_example() -> dict:
    request = _example()
    request["criteria"][0]["status"] = "known"
    request["criteria"][0]["resolution"] = "resolved"
    for item in request["protocol"]["objects"]:
        item["standing"] = {"status": "known", "resolution": "resolved", "basis": ["user:invented adoption"]}
        item.pop("support", None)
        item["adopted_by"] = {"ref": "user:invented adoption", "status": "known", "resolution": "resolved"}
    return request


def _extended(request: dict) -> dict:
    collection = copy.deepcopy(request["protocol"]["objects"][2])
    # The replacement keeps the baseline object's edition, so it reuses that edition's adoption record.
    collection.pop("adopted_by", None)
    collection["support"] = [f"adopt:{collection['id']}:{collection['version']}"]
    collection["data"]["availability"] = [
        {"lower": None, "upper": "91", "lower_inclusive": False, "upper_inclusive": True}
    ]
    return collection


def test_a_plan_comparison_is_preparable_and_discoverable():
    card = run({"operation": "describe", "view": "protocol"})["result"]
    assert "protocol.decisions" in card["decisions"]["shape"]
    request = _adopted_example()
    request["protocol"]["decisions"] = [
        {
            "id": "collection-plan",
            "question": "How long should week-12 collection run?",
            "alternatives": [
                {"id": "as-drafted", "label": "Through day 80", "checks": ["week12-schedule"]},
                {
                    "id": "extend",
                    "label": "Through day 91",
                    "replace": [_extended(request)],
                    "checks": ["week12-schedule"],
                },
            ],
            "selected": {"alternative": "as-drafted", "origin": "user", "basis": ["user:invented selection"]},
        }
    ]
    prepared = run(request)
    assert prepared["code"] == "complete", prepared["problems"]
    session = prepared["result"]["request"]["session"]
    decision = next(d for d in session["decisions"] if d.get("kind") == "protocol_options")
    assert decision["coverage"] == "declared_design" and decision["alternatives"][0]["replace_objects"] == []
    reply = run(prepared["result"]["request"])
    assert reply["code"] == "complete", reply["problems"]
    rows = reply["result"]["protocol"]["decisions"][0]
    assert rows["disposition"] == "repair_choice"
    assert {a["id"]: a["compatibility"] for a in rows["alternatives"]} == {
        "as-drafted": "repair_choice_open_under_declared_checks",
        "extend": "compatible_under_declared_checks",
    }


def test_the_headline_metadata_counts_protocol_conflicts():
    request = json.loads((FIXTURES / "results/policy-violation-known.json").read_text())["request"]
    findings = run(request)["metadata"]["findings"]
    claims = [f for f in findings if f["kind"] == "protocol_claim"]
    assert any(f["logical_result"] == "violation" and f["disposition"] == "conflict" for f in claims)
    assert all(f["disposition"] != "unclassified" for f in findings)


def test_revision_rows_carry_per_claim_before_and_after():
    first = _adopted_example()
    prepared = run(first)["result"]["request"]
    initial = run(prepared)
    nxt = copy.deepcopy(prepared)
    nxt["session"]["revision"] = "two"
    nxt["session"]["parent_digest"] = session_state.digest(prepared["session"])
    nxt["session"]["protocol"]["objects"][2]["data"]["availability"][0]["upper"] = "91"
    # Changed content is a new edition, re-adopted with the instruction (Rohan, 2026-11-04).
    new_edition(nxt["session"], nxt["session"]["protocol"]["objects"][2]["id"])
    nxt["previous"] = {
        "session": prepared["session"],
        "result": initial["result"],
        "expected_result_digest": initial["result_digest"],
    }
    row = run(nxt)["answer_diff"]["protocol_checks"][0]
    changes = {(c["claim"], c["field"]): (c["before"], c["after"]) for c in row["changes"] if "claim" in c}
    assert changes[("target", "effective_outcome")] == ("not_collected", "satisfied")
    assert changes[("window", "effective_outcome")] == ("uncovered", "satisfied")
    assert ("visit", "effective_outcome") not in changes


def test_a_retained_handle_without_its_digest_is_refused_at_preparation():
    request = _example()
    request["sources"] = [
        {
            "id": "s",
            "study": {"$retained_study": {"run": "pool", "nct": "NCT00000000"}},
            "expected_digest": "0" * 64,
        }
    ]
    reply = run(request)
    assert (reply["code"], reply["problems"]) == ("refused", ["invalid_source_marker"])


def test_the_card_states_the_rules_walkers_had_to_guess():
    notes = run({"operation": "describe", "view": "protocol"})["result"]["notes"]
    for key in (
        "ids",
        "source_interpretation_origin",
        "external_method",
        "event_handling",
        "adoption",
        "raw_vs_effective",
        "retained_study",
    ):
        assert notes[key], key


def _estimand_with_linked_collection(action: str) -> dict:
    from tests.test_protocol_session_replay import _session, adopt

    example = run({"operation": "describe", "view": "signals", "detail": "full"})["result"]["signal_examples"]
    estimand = copy.deepcopy(example["estimand"]["signals"][0]["data"])
    requirement = estimand["requirements"][0]["id"]
    estimand["collection_plan"] = [
        row for row in estimand["collection_plan"] if row["requirement"] != requirement
    ]
    request = _session("84", collection_status="known")
    protocol = request["session"]["protocol"]
    template = copy.deepcopy(protocol["objects"][0])
    template.update(id="estimand", kind="estimand", depends_on=[], data=estimand, support=[])
    protocol["objects"].append(template)
    adopt(request, "estimand")
    collection = next(o for o in protocol["objects"] if o["id"] == "collection")
    collection["data"]["event_handling"] = {
        "estimand": "estimand",
        "requirement": requirement,
        "action": action,
    }
    collection["depends_on"] = sorted(set(collection["depends_on"]) | {"estimand"})
    check = copy.deepcopy(protocol["checks"][0])
    check.update(id="estimand-check", kind="estimand", objects=["estimand"], claims=[])
    protocol["checks"] = [check]
    return request


def test_the_collection_declares_the_estimand_plan_once():
    """MS walk: the collection's event_handling action now drives the estimand's alignment."""
    stop = run(_estimand_with_linked_collection("stop"))
    assert stop["code"] == "complete", stop["problems"]
    blockers = stop["result"]["protocol"]["checks"][0]["children"][0]["signals"][0]["blockers"]
    assert any(b.startswith("estimand_collection_plan_mismatch") for b in blockers)
    collect = run(_estimand_with_linked_collection("collect"))
    blockers = collect["result"]["protocol"]["checks"][0]["children"][0]["signals"][0]["blockers"]
    assert not any(b.startswith("estimand_collection_plan_mismatch") for b in blockers)
