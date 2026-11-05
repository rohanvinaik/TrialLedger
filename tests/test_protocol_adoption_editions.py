"""REV-1 adoption editions: one guard on every revision path, and stale applications kept per object.

Closes two gaps from the adoption-version audit at aec72e8
(`~/trialledger-runs/adoption-version-audit-20261104/`):
1. Content changed under an unchanged version was refused by `--edits` but accepted by `--session`, MCP and
   direct canonical revisions, retaining the old adoption.
2. One adoption record covering several objects could be current for one object and stale for another; support
   de-duplication kept the current application, so the stale object's findings were admitted as known.

Rohan (2026-11-04): adoption belongs to a particular definition edition; an instructed change records the new
version and its adoption together; a what-if stays hypothetical; unchanged objects keep their adoption.
"""

import copy
import json
import subprocess

import pytest

from tests.test_protocol_mcp_lifecycle import CLI, ROOT, McpClient
from tests.test_protocol_session_replay import ORIGIN, _session, adoption_premise
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.layer2 import protocol_view, run

OBJECTS = ("score", "week12", "collection")
AVAILABLE_CLAIMS = ("visit", "window")  # decided with the collection's availability in every outcome here


def _shared(nominal: str = "84", record: str = "adopt-plan", order: tuple = OBJECTS) -> dict:
    """Every object adopted at invented-v1 by one shared, attributed adoption record."""
    request = _session(nominal, collection_status="known")
    session = request["session"]
    session["premises"] = [p for p in session["premises"] if p.get("kind") != "adoption"]
    session["premises"].append(
        {
            "id": record,
            "kind": "adoption",
            "payload": {
                "objects": [{"id": o, "version": "invented-v1"} for o in order],
                "status": "known",
                "resolution": "resolved",
            },
            "origin": copy.deepcopy(ORIGIN),
            "depends_on": [],
        }
    )
    for item in session["protocol"]["objects"]:
        item["support"] = [record]
    return request


def _new_collection_edition(request: dict, version: str = "invented-v2") -> dict:
    collection = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "collection")
    collection["version"] = version
    collection["data"]["availability"][0]["upper"] = "95"
    return request


def _claims(reply: dict) -> dict:
    assert reply["code"] == "complete", reply.get("problems")
    check = next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == "week12-schedule")
    return {
        row["id"]: row
        for child in check["children"]
        for signal in child["signals"]
        for row in signal["claim_admission"]
    }


def _adoption(reply: dict) -> dict:
    return {row["object"]: row["adoption"] for row in protocol_view.view(reply["result"])["adoption"]}


# --- 1. A shared record current for one object never admits a stale version of another ---------------------


def test_a_shared_record_current_for_the_assessment_does_not_admit_the_stale_collection():
    claims = _claims(run(_new_collection_edition(_shared())))
    for identity in AVAILABLE_CLAIMS:
        assert claims[identity]["admission"] == "binding_unresolved", identity
        assert claims[identity]["effective_outcome"] == "unresolved", identity


def test_control_the_same_shared_record_admits_when_every_object_is_current():
    claims = _claims(run(_shared()))
    assert {row["admission"] for row in claims.values()} == {"accepted"}


def test_separate_records_and_a_shared_record_withhold_the_same_stale_findings():
    shared = _claims(run(_new_collection_edition(_shared())))
    separate = _session("84", collection_status="known")
    adoption_ids = {o: f"adopt:{o}:invented-v1" for o in OBJECTS}
    separate["session"]["premises"] = [
        p for p in separate["session"]["premises"] if p.get("kind") != "adoption"
    ]
    separate["session"]["premises"] += [adoption_premise(o, "invented-v1") for o in OBJECTS]
    for item in separate["session"]["protocol"]["objects"]:
        item["support"] = [adoption_ids[item["id"]]]
    separate_claims = _claims(run(_new_collection_edition(separate)))
    assert {k: v["admission"] for k, v in shared.items()} == {
        k: v["admission"] for k, v in separate_claims.items()
    }


def test_the_stale_application_keeps_its_own_identity_and_its_premise_provenance():
    reply = run(_new_collection_edition(_shared()))
    child = next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == "week12-schedule")[
        "children"
    ][0]
    support = {e["id"]: e for e in child["request"]["signals"][0]["support"]}
    assert support["premise:adopt-plan"]["resolution"] == "resolved"
    assert support["stale_adoption:collection:adopt-plan"]["resolution"] == "unresolved"
    assert child["receipt"]["premises"] == ["adopt-plan"]
    available = [e["id"] for e in child["receipt"]["role_support"]["available"]]
    assert "stale_adoption:collection:adopt-plan" in available and "premise:adopt-plan" not in available


# --- 2. Renaming or ordering support records never changes admission ---


@pytest.mark.parametrize(
    ("record", "order"),
    [("adopt-plan", OBJECTS), ("aa-plan", OBJECTS), ("zz-plan", tuple(reversed(OBJECTS)))],
)
def test_renaming_or_reordering_the_shared_record_does_not_change_admission(record, order):
    baseline = _claims(run(_new_collection_edition(_shared())))
    renamed = _claims(run(_new_collection_edition(_shared(record=record, order=order))))
    assert {k: v["admission"] for k, v in renamed.items()} == {k: v["admission"] for k, v in baseline.items()}


def test_reordering_the_protocol_objects_does_not_change_admission():
    baseline = _claims(run(_new_collection_edition(_shared())))
    request = _new_collection_edition(_shared())
    request["session"]["protocol"]["objects"].reverse()
    reordered = _claims(run(request))
    assert {k: v["admission"] for k, v in reordered.items()} == {
        k: v["admission"] for k, v in baseline.items()
    }


# --- 3. A stale collection never withholds an assessment-only finding --------------------------------------


def test_a_stale_collection_does_not_withhold_a_nominal_target_outside_its_permitted_window():
    claims = _claims(run(_new_collection_edition(_shared(nominal="100"))))
    target = claims["target"]
    assert (target["outcome"], target["admission"], target["effective_outcome"]) == (
        "outside_window",
        "accepted",
        "outside_window",
    )
    assert target["status"] == "known"
    for identity in AVAILABLE_CLAIMS:
        assert claims[identity]["admission"] == "binding_unresolved", identity


# --- 4. Adopting the new version restores the findings; unchanged objects keep their adoption -----------


def test_adopting_the_new_collection_version_restores_its_findings_and_keeps_the_others():
    request = _new_collection_edition(_shared())
    request["session"]["premises"].append(adoption_premise("collection", "invented-v2"))
    collection = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "collection")
    collection["support"] = ["adopt:collection:invented-v2"]
    reply = run(request)
    assert {row["admission"] for row in _claims(reply).values()} == {"accepted"}
    adoption = _adoption(reply)
    assert adoption["collection"] == "adopted_known"
    assert adoption["week12"] == adoption["score"] == "adopted_known"


# --- 5. Raw arithmetic stays visible but is never presented as an adopted fact ------------------------------


def test_raw_arithmetic_stays_visible_while_the_stale_object_is_not_reported_as_adopted():
    reply = run(_new_collection_edition(_shared()))
    claims = _claims(reply)
    for identity in AVAILABLE_CLAIMS:
        assert claims[identity]["outcome"] == "satisfied", identity
        assert claims[identity]["effective_outcome"] == "unresolved", identity
    adoption = _adoption(reply)
    assert adoption["collection"] == "stale_version"
    assert adoption["week12"] == "adopted_known"


# --- The version guard holds on every revision path ---------------------------------------------------------


def _same_version_next(session: dict) -> dict:
    following = copy.deepcopy(session)
    following["revision"] = "two"
    following.pop("parent_digest", None)
    collection = next(o for o in following["protocol"]["objects"] if o["id"] == "collection")
    collection["data"]["availability"][0]["upper"] = "95"
    return following


def test_session_revision_refuses_content_changed_under_the_same_version(tmp_path):
    request = _shared()
    held = delivery.execute(request, store=tmp_path)
    with pytest.raises(ValueError, match="^changed_protocol_object_version_required:collection$"):
        delivery.revise(tmp_path, held["artifact"]["id"], session=_same_version_next(request["session"]))
    with pytest.raises(ValueError, match="^changed_protocol_object_version_required:collection$"):
        delivery.revise(
            tmp_path,
            held["artifact"]["id"],
            session=_same_version_next(request["session"]),
            prepare_only=True,
        )


def test_cli_session_revision_refuses_content_changed_under_the_same_version(tmp_path):
    request = _shared()
    (tmp_path / "request.json").write_text(json.dumps(request))
    (tmp_path / "next.json").write_text(json.dumps(_same_version_next(request["session"])))
    store = str(tmp_path / "store")
    done = subprocess.run(
        [CLI, "reason", "--request", str(tmp_path / "request.json"), "--store", store, "--compact"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert done.returncode == 0, done.stderr
    identity = json.loads(done.stdout)["artifact"]["id"]
    command = ["reason-revise", "--store", store, "--id", identity, "--session", str(tmp_path / "next.json")]
    refused = subprocess.run([CLI, *command], capture_output=True, text=True, cwd=ROOT)
    assert refused.returncode != 0
    assert "changed_protocol_object_version_required:collection" in refused.stdout + refused.stderr


def test_mcp_session_revision_refuses_content_changed_under_the_same_version(tmp_path):
    client = McpClient(tmp_path / "served")
    try:
        request = _shared()
        held = client.call("reason", request=request, retain=True)
        reply = client.send(
            "tools/call",
            {
                "name": "reason_revise",
                "arguments": {
                    "id": held["artifact"]["id"],
                    "session": _same_version_next(request["session"]),
                },
            },
        )["result"]
        assert reply["isError"]
        assert "changed_protocol_object_version_required:collection" in reply["content"][0]["text"]
    finally:
        client.close()


def test_a_new_edition_through_a_session_revision_keeps_the_old_adoption_stale_until_re_adopted(tmp_path):
    request = _shared()
    held = delivery.execute(request, store=tmp_path)
    following = _same_version_next(request["session"])
    _new_collection_edition({"session": following})
    revised = delivery.revise(tmp_path, held["artifact"]["id"], session=following, response_view="full")
    assert revised["code"] == "complete", revised.get("problems")
    assert _adoption(revised)["collection"] == "stale_version"
    claims = _claims(revised)
    for identity in AVAILABLE_CLAIMS:
        assert claims[identity]["admission"] == "binding_unresolved", identity


# --- A third path: plan alternatives (protocol_options replace_objects) ---


def test_a_same_version_replacement_in_a_plan_alternative_never_yields_an_admitted_known_finding():
    """A replacement keeping the baseline version, even user_choice and known, stays a hypothetical frame.

    The baseline's adoption names that version, but the replaced object's own entries are only assumed inside
    the frame, so every finding resting on it is proposed and the alternative's application is withheld.
    """
    from tests.test_protocol_options import _alt, _base, _complete, _decision, _with_decision

    base = _base()
    template = next(o for o in base["session"]["protocol"]["objects"] if o["id"] == "collection")
    replacement = copy.deepcopy(template)
    replacement["data"]["availability"] = [
        {"lower": None, "upper": "95", "lower_inclusive": False, "upper_inclusive": True}
    ]
    replacement["origin"] = {**ORIGIN, "ref": "user:invented same-version replacement"}
    replacement["standing"] = {"status": "known", "resolution": "resolved", "basis": ["user:invented"]}
    assert replacement["version"] == template["version"]
    alternatives = [
        _alt("same-version", [replacement], ("week12-schedule",)),
        _alt("draft", [], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))
    alternative = next(a for a in decision["alternatives"] if a["id"] == "same-version")
    assert (alternative["frame"], alternative["unconditional_application"]) == ("hypothetical", "withheld")
    claims = [claim for check in alternative["checks"] for claim in check["claims"]]
    assert claims and all(claim["finding_status"] == "proposed" for claim in claims)
    assert all(claim["assumed"] == ["object:collection"] for claim in claims)
