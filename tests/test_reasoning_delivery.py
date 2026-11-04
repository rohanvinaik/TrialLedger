"""Intent tests for the shared clinical delivery shell; premises are invented fixtures."""

import json
from copy import deepcopy

import pytest
from test_session_revision_delivery import request

from TrialLedger import reasoning_artifacts as artifacts
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.cli import main
from TrialLedger.layer2 import run
from TrialLedger.mcp_server import Context, argument_problems, call_tool


def mcp(root, name, arguments):
    code, reply = call_tool(Context(root), {"name": name, "arguments": arguments})
    assert code == "ok"
    value = json.loads(reply["content"][0]["text"])
    assert value.pop("tool") == name
    return value, reply["isError"]


def test_cli_mcp_share_full_and_compact_canonical_answers(tmp_path, capsys):
    payload = request()
    path = tmp_path / "request.json"
    path.write_text(json.dumps(payload))
    root = tmp_path / "runs"
    store = root / ".reasoning"
    assert main(["reason", "--request", str(path), "--store", str(store), "--compact"]) == 0
    cli = json.loads(capsys.readouterr().out)
    remote, error = mcp(root, "reason", {"request": payload, "response_view": "compact"})
    assert not error
    assert remote == cli
    canonical = artifacts.load(store, cli["artifact"]["id"])
    assert canonical["request"] == payload
    assert canonical["response"]["result"] == run(payload)["result"]
    retrieved, error = mcp(root, "reason_result", {"id": cli["artifact"]["id"], "part": "result"})
    assert not error and retrieved["code"] == "complete"
    assert "run_folder" not in retrieved


def test_revision_retains_edit_evidence_without_echoing_large_values(tmp_path):
    held = delivery.execute(request(), store=tmp_path)
    identity = held["artifact"]["id"]
    patch = [
        {
            "op": "replace",
            "path": "/premises/0/payload/status",
            "value": "interpolated",
            "origin": {"kind": "user_choice", "ref": "invented-revision", "source": None, "analysis": None},
        }
    ]
    revised = delivery.revise(tmp_path, identity, revision="two", edits=patch)
    assert revised["code"] == "complete"
    assert revised["delivery"]["previous_artifact"] == identity
    assert "before" not in revised["delivery"]["edits"][0]
    canonical = artifacts.load(tmp_path, revised["artifact"]["id"])
    assert canonical["response"]["delivery"]["edits"][0]["before"] == "known"
    assert canonical["response"]["delivery"]["edits"][0]["after"] == "interpolated"
    assert revised["answer_diff"]["analyses"][0]["code"] == "support_changed"
    assert canonical["response"]["previous_fresh"] == held["result"]


def test_changed_payload_cannot_reuse_unreviewed_origin(tmp_path):
    held = delivery.execute(request(), store=tmp_path)
    with pytest.raises(ValueError, match="changed_premise_origin_required"):
        delivery.revise(
            tmp_path,
            held["artifact"]["id"],
            revision="two",
            edits=[{"op": "replace", "path": "/premises/0/payload/status", "value": "interpolated"}],
        )


def test_source_snapshot_cannot_be_rewritten_through_revision_shortcut():
    session = request()["session"]
    session["premises"][0]["kind"] = "source_assertion"
    with pytest.raises(ValueError, match="source_premise_requires_new_binding"):
        delivery.edited_session(
            session,
            "two",
            [
                {
                    "op": "replace",
                    "path": "/premises/0/payload/status",
                    "value": "interpolated",
                    "origin": deepcopy(session["premises"][0]["origin"]),
                }
            ],
        )


@pytest.mark.parametrize(
    "path,operation,code",
    [
        ("/sources/0", "replace", "immutable_session_field"),
        ("/id", "replace", "immutable_session_field"),
        ("/premises/0", "add", "unsupported_edit_operation"),
        (None, "replace", "invalid_edit_path"),
        ("xpremises", "replace", "invalid_edit_path"),
        ("/premises/a~1b", "replace", "invalid_edit_path"),
        ("/premises/0/payload/body", "replace", "replace_design_field"),
        ("/decisions", "replace", "replace_design_field"),
    ],
)
def test_shortcut_cannot_mutate_identity_or_source(path, operation, code):
    assert delivery.edit_path_code(path, operation) == code


def test_array_arguments_never_accept_objects_or_strings():
    schema = {"properties": {"edits": {"type": "array"}}, "required": ["edits"]}
    assert argument_problems(schema, {"edits": []}) == ("ok", [])
    assert argument_problems(schema, {"edits": {}}) == ("wrong_type", ["edits"])
    assert argument_problems(schema, {"edits": "[]"}) == ("wrong_type", ["edits"])


def test_compact_requires_actual_storage_and_keeps_question_outside_premises(tmp_path):
    with pytest.raises(ValueError, match="compact_requires_artifact_store"):
        delivery.execute(request(), response_view="compact")
    response = delivery.execute(
        request(), store=tmp_path, intent="necessity", question="Must everyone have A?"
    )
    assert response["presentation"]["question"] == "Must everyone have A?"
    assert artifacts.load(tmp_path, response["artifact"]["id"])["request"] == request()


def test_mcp_reasoning_namespaces_cannot_follow_links_outside_root(tmp_path):
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / ".reasoning").symlink_to(outside)
    reply, error = mcp(root, "reason", {"request": request(), "retain": True})
    assert error and reply["problems"] == ["reasoning_store_outside_root"]
    assert list(outside.iterdir()) == []
    (root / ".reasoning").unlink()
    held, error = mcp(root, "reason", {"request": request(), "retain": True})
    assert not error
    (root / "reasoning-exports").symlink_to(outside)
    reply, error = mcp(root, "reason_export", {"id": held["artifact"]["id"]})
    assert error and reply["problems"] == ["reasoning_export_outside_root"]
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("bad", [None, [], False, "unparsed"])
def test_retained_malformed_request_keeps_original_named_refusal(tmp_path, bad):
    response = delivery.execute(bad, store=tmp_path, response_view="compact")
    assert response["code"] == "refused"
    assert artifacts.load(tmp_path, response["artifact"]["id"])["request"] == bad
    assert response["problems"] == run(bad)["problems"]
    assert response["clinical"]["findings"][0]["disposition"] == "translation_question"
    assert response["clinical"]["findings"][0]["completion"] == "invalid"
    assert response["clinical"]["findings"][0]["blockers"] == response["problems"]
