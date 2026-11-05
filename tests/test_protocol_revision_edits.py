"""Bounded `--edits` revisions on /protocol paths (task 5.6; walkthrough wave 2, defect 3).

A changed protocol object needs explicit attribution, exactly like a changed premise. A change to its
content also needs a new version: adoption records name an exact id and version, so an edit under the old
version would carry an adoption to content nobody adopted. With a new version the earlier adoption reads
as stale (soft, unresolved; Rohan, 2026-11-04) until a new adoption record and support are supplied.
"""

import copy
import json

import pytest

from tests.test_protocol_options import _base
from tests.test_protocol_session_replay import adoption_premise
from TrialLedger import reasoning_artifacts as artifacts
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.cli import main
from TrialLedger.layer2.design_session_guide import EXAMPLE

ORIGIN = {
    "kind": "user_choice",
    "ref": "user:invented collection extension",
    "source": None,
    "analysis": None,
}
COLLECTION = "/protocol/objects/2"
THROUGH_95 = [{"lower": None, "upper": "95", "lower_inclusive": False, "upper_inclusive": True}]


def _held(tmp_path) -> str:
    request = _base()
    assert request["session"]["protocol"]["objects"][2]["id"] == "collection"
    held = delivery.execute(request, store=tmp_path)
    assert held["result"] is not None
    return held["artifact"]["id"]


def _check(reply: dict, identity: str = "week12-schedule") -> dict:
    return next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == identity)


def _unresolved_codes(reply: dict) -> list[str]:
    return [row["code"] for row in _check(reply)["unresolved"]]


def test_a_changed_protocol_object_without_attribution_is_refused(tmp_path):
    identity = _held(tmp_path)
    edits = [{"op": "replace", "path": COLLECTION + "/data/availability", "value": THROUGH_95}]
    with pytest.raises(ValueError, match="^changed_protocol_object_origin_required$"):
        delivery.revise(tmp_path, identity, revision="two", edits=edits)


def test_changed_object_content_under_the_same_version_is_refused(tmp_path):
    identity = _held(tmp_path)
    edits = [
        {"op": "replace", "path": COLLECTION + "/data/availability", "value": THROUGH_95, "origin": ORIGIN}
    ]
    with pytest.raises(ValueError, match="^changed_protocol_object_version_required:collection$"):
        delivery.revise(tmp_path, identity, revision="two", edits=edits)


def test_an_instructed_new_version_records_its_adoption_in_the_same_revision(tmp_path):
    """An explicit instruction to change an adopted plan adopts the new version (Rohan, 2026-11-04)."""
    identity = _held(tmp_path)
    edits = [
        {"op": "replace", "path": COLLECTION + "/data/availability", "value": THROUGH_95, "origin": ORIGIN},
        {"op": "replace", "path": COLLECTION + "/version", "value": "invented-v2"},
    ]
    revised = delivery.revise(tmp_path, identity, revision="two", edits=edits, response_view="full")
    assert revised["code"] == "complete", revised.get("problems")
    canonical = artifacts.load(tmp_path, revised["artifact"]["id"])
    session = canonical["request"]["session"]
    collection = session["protocol"]["objects"][2]
    assert (collection["version"], collection["origin"]) == ("invented-v2", ORIGIN)
    assert collection["support"] == ["adopt:collection:invented-v2"]
    record = next(p for p in session["premises"] if p["id"] == "adopt:collection:invented-v2")
    assert record["payload"] == {
        "objects": [{"id": "collection", "version": "invented-v2"}],
        "status": "known",
        "resolution": "resolved",
    }
    assert record["origin"] == ORIGIN
    # The earlier record stays as history; unchanged objects keep their own adoption.
    assert any(p["id"] == "adopt:collection:invented-v1" for p in session["premises"])
    week12 = session["protocol"]["objects"][1]
    assert week12["support"] == ["adopt:week12:invented-v1"]
    assert "adoption_stale_version" not in _unresolved_codes(revised)
    edits_review = canonical["response"]["delivery"]["edits"]
    mechanical = [row for row in edits_review if row.get("mechanical") == "adoption_of_instructed_version"]
    assert [row["path"] for row in mechanical] == [
        f"/premises/{len(session['premises']) - 1}",
        COLLECTION + "/support",
    ]
    rows = {row["id"]: row for row in revised["answer_diff"]["protocol_checks"]}
    assert rows["week12-schedule"]["code"] != "unchanged"


def test_a_what_if_new_version_is_never_adopted_and_its_old_adoption_reads_as_stale(tmp_path):
    """A hypothesis origin is a what-if: the new version gets no adoption, so the old one is stale."""
    identity = _held(tmp_path)
    what_if = {**ORIGIN, "kind": "hypothesis", "ref": "user:invented what-if through 95"}
    standing = {"status": "proposed", "resolution": "resolved", "basis": ["user:invented what-if"]}
    edits = [
        {"op": "replace", "path": COLLECTION + "/data/availability", "value": THROUGH_95, "origin": what_if},
        {"op": "replace", "path": COLLECTION + "/version", "value": "invented-v2"},
        {"op": "replace", "path": COLLECTION + "/standing", "value": standing},
    ]
    revised = delivery.revise(tmp_path, identity, revision="two", edits=edits, response_view="full")
    assert revised["code"] == "complete", revised.get("problems")
    session = artifacts.load(tmp_path, revised["artifact"]["id"])["request"]["session"]
    assert session["protocol"]["objects"][2]["support"] == ["adopt:collection:invented-v1"]
    assert not any(p["id"] == "adopt:collection:invented-v2" for p in session["premises"])
    assert "adoption_stale_version" in _unresolved_codes(revised)


def test_an_unchanged_origin_does_not_adopt_a_new_version(tmp_path):
    """Re-adoption needs a newly attributed instruction; a reused origin leaves the old one stale."""
    identity = _held(tmp_path)
    prior = artifacts.load(tmp_path, identity)["request"]["session"]["protocol"]["objects"][2]
    edits = [
        {
            "op": "replace",
            "path": COLLECTION + "/data/availability",
            "value": THROUGH_95,
            "origin": copy.deepcopy(prior["origin"]),
        },
        {"op": "replace", "path": COLLECTION + "/version", "value": "invented-v2"},
    ]
    revised = delivery.revise(tmp_path, identity, revision="two", edits=edits, response_view="full")
    assert revised["code"] == "complete", revised.get("problems")
    assert "adoption_stale_version" in _unresolved_codes(revised)


def test_a_new_adoption_record_and_support_clear_the_stale_version(tmp_path):
    identity = _held(tmp_path)
    prior = artifacts.load(tmp_path, identity)["request"]["session"]
    adoption = adoption_premise("collection", "invented-v2")
    adoption["origin"] = copy.deepcopy(ORIGIN)
    edits = [
        {"op": "replace", "path": COLLECTION + "/data/availability", "value": THROUGH_95, "origin": ORIGIN},
        {"op": "replace", "path": COLLECTION + "/version", "value": "invented-v2"},
        {"op": "replace", "path": COLLECTION + "/support", "value": ["adopt:collection:invented-v2"]},
        {"op": "replace", "path": "/premises", "value": [*copy.deepcopy(prior["premises"]), adoption]},
    ]
    revised = delivery.revise(tmp_path, identity, revision="two", edits=edits, response_view="full")
    assert revised["code"] == "complete", revised.get("problems")
    assert "adoption_stale_version" not in _unresolved_codes(revised)


def test_an_attributed_standing_edit_keeps_the_version(tmp_path):
    identity = _held(tmp_path)
    standing = {"status": "proposed", "resolution": "resolved", "basis": ["user:invented second look"]}
    edits = [{"op": "replace", "path": COLLECTION + "/standing", "value": standing, "origin": ORIGIN}]
    revised = delivery.revise(tmp_path, identity, revision="two", edits=edits, response_view="full")
    assert revised["code"] == "complete", revised.get("problems")
    held = artifacts.load(tmp_path, revised["artifact"]["id"])["request"]["session"]["protocol"]["objects"][2]
    assert (held["version"], held["standing"]) == ("invented-v1", standing)


def test_check_edits_need_no_origin_and_refuse_one(tmp_path):
    identity = _held(tmp_path)
    edits = [{"op": "replace", "path": "/protocol/checks/0/required", "value": False}]
    revised = delivery.revise(tmp_path, identity, revision="two", edits=edits, response_view="full")
    assert revised["code"] == "complete", revised.get("problems")
    assert _check(revised)["required"] is False
    with pytest.raises(ValueError, match="^edit_origin_requires_protocol_object$"):
        delivery.revise(tmp_path, identity, revision="three", edits=[{**edits[0], "origin": ORIGIN}])


def test_a_whole_object_replacement_still_needs_a_new_version_for_new_content(tmp_path):
    identity = _held(tmp_path)
    prior = artifacts.load(tmp_path, identity)["request"]["session"]["protocol"]["objects"][2]
    replacement = copy.deepcopy(prior)
    replacement["data"]["availability"] = THROUGH_95
    replacement["origin"] = copy.deepcopy(ORIGIN)
    with pytest.raises(ValueError, match="^changed_protocol_object_version_required:collection$"):
        delivery.revise(
            tmp_path,
            identity,
            revision="two",
            edits=[{"op": "replace", "path": COLLECTION, "value": replacement}],
        )


def test_protocol_paths_do_not_exist_in_a_v1_session():
    session = copy.deepcopy(EXAMPLE["session"])
    with pytest.raises(ValueError):
        delivery.edited_session(
            session, "two", [{"op": "replace", "path": "/protocol/objects/0/version", "value": "x"}]
        )


def test_the_cli_edits_flag_accepts_attributed_protocol_edits(tmp_path, capsys):
    identity = _held(tmp_path)
    path = tmp_path / "edits.json"
    path.write_text(
        json.dumps(
            [
                {
                    "op": "replace",
                    "path": COLLECTION + "/data/availability",
                    "value": THROUGH_95,
                    "origin": ORIGIN,
                },
                {"op": "replace", "path": COLLECTION + "/version", "value": "invented-v2"},
            ]
        )
    )
    command = ["reason-revise", "--store", str(tmp_path), "--id", identity, "--edits", str(path)]
    assert main([*command, "--revision", "two"]) == 0
    reply = json.loads(capsys.readouterr().out)
    assert reply["code"] == "complete", reply.get("problems")
    assert reply["delivery"]["previous_artifact"] == identity
