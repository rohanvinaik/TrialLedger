"""A compact reply is bounded navigation, never shortened clinical evidence.

The many-row payloads are invented fixtures; no real human confirmation is asserted.
"""

import json
from copy import deepcopy

import pytest
from test_session_revision_delivery import request

from TrialLedger import clinical_delivery as clinical
from TrialLedger import reasoning_artifacts as artifacts
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.cli import main
from TrialLedger.mcp_server import TOOLS, Context, argument_problems, call_tool


def many_rows(count=80):
    axes = {name: "changed" for name in ("question", "answer", "support", "origin", "context", "input")}
    finding = {
        "path": "/result/decision",
        "kind": "logical",
        "outcome": "UNDETERMINED",
        "standing": "proposed",
        "disposition": "conditional",
        "completion": "complete",
        "blockers": ["invented-unknown-blocker"],
        "scope": {"source_text": "完整\r\n" * 400},
        "values": {"source_value": "unshortened source " * 400},
    }
    change = {
        "id": "invented-check",
        "code": "invented-unknown-change-code",
        "axes": axes,
        "changes": list(axes),
        "before": {"projections": [deepcopy(finding)] * 3},
        "after": {"projections": [deepcopy(finding)] * 3},
    }
    return {
        "code": "complete",
        "operation": "design_session",
        "summary": {"code": "complete", "findings": count},
        "problems": [],
        "result": {"decisions": []},
        "clinical": {
            "version": 1,
            "operation": "design_session",
            "findings": [deepcopy(finding) for _ in range(count)],
        },
        "answer_diff": {
            "analyses": [deepcopy(change) for _ in range(count)],
            "decisions": [deepcopy(change)],
        },
        "decision_view": [
            {
                "id": "age-policy",
                "caller_question": {"text": "Invented choice?", "origin": "caller"},
                "decision_code": "design_choice",
                "selected": None,
                "coverage": "represented",
                "evidence": [deepcopy(finding)],
                "options": [],
            }
        ],
        "delivery": {
            "previous_artifact": "a" * 64,
            "edits": [{"path": "/premises", "before": deepcopy(finding), "after": deepcopy(finding)}],
        },
    }


@pytest.mark.parametrize("value", [None, False, True, 0, -1, 2047, 65537, "4096", 4096.0, [], {}])
def test_compact_budget_must_not_admit_malformed_or_unsupported_values(value):
    assert clinical.compact_budget_code(value) == "max_bytes_out_of_range"


@pytest.mark.parametrize("value", [2048, 2049, 24576, 65535, 65536])
def test_compact_budget_includes_both_exact_supported_boundaries(value):
    assert clinical.compact_budget_code(value) == "valid_compact_budget"


@pytest.mark.parametrize("budget", [2048, 4096, 24576, 65536])
def test_many_check_revision_obeys_pretty_utf8_budget_without_before_after(tmp_path, budget):
    response = many_rows()
    original = deepcopy(response)
    held = artifacts.save(tmp_path, {"operation": "invented-test"}, response)
    compact = clinical.compact(response, held, max_bytes=budget)
    assert len((json.dumps(compact, ensure_ascii=False, indent=1) + "\n").encode()) <= budget
    assert (
        len(json.dumps({"tool": "reason_revise", **compact}, ensure_ascii=False, indent=1).encode()) <= budget
    )
    assert response == original
    assert artifacts.load(tmp_path, held["id"])["response"] == original
    assert compact["artifact"]["id"] == held["id"]
    changes = compact.get("answer_diff")
    if changes is not None:
        for kind in ("analyses", "decisions"):
            for row in changes[kind]:
                assert set(row) == {"id", "code", "axes", "changes", "canonical_ref"}
                assert row["axes"] == original["answer_diff"][kind][0]["axes"]
                assert row["code"] == "invented-unknown-change-code"
            page = changes["pages"][kind]
            assert page["returned"] == len(changes[kind])
            assert page["total"] == len(original["answer_diff"][kind])
            assert page["next_offset"] == (len(changes[kind]) if len(changes[kind]) < page["total"] else None)
    else:
        assert compact["navigation"] == "exact_artifact"
        assert compact["pages"]["/response/answer_diff/analyses"]["total"] == 80


def test_finding_summaries_keep_standing_blockers_and_exact_scope_not_shortened_values(tmp_path):
    response = many_rows(3)
    held = artifacts.save(tmp_path, {}, response)
    compact = clinical.compact(response, held)
    row = compact["clinical"]["findings"][0]
    assert row["standing"] == "proposed"
    assert row["disposition"] == "conditional"
    assert row["blockers"] == ["invented-unknown-blocker"]
    assert "values" not in row and "scope" not in row
    scope = artifacts.read(tmp_path, held["id"], {"part": "address", "address": row["scope_ref"]})
    assert scope["value"] == response["clinical"]["findings"][0]["scope"]
    decision = compact["decision_view"]["decisions"][0]
    assert decision["caller_question"]["origin"] == "caller"
    full = artifacts.read(
        tmp_path, held["id"], {"part": "address", "address": decision["canonical_ref"], "max_bytes": 65536}
    )
    assert full["value"] == response["decision_view"][0]


def test_oversized_first_summary_has_explicit_zero_return_and_exact_continuation(tmp_path):
    response = many_rows(2)
    response["clinical"]["findings"][0]["blockers"] = ["unknown:" + "末" * 10000]
    held = artifacts.save(tmp_path, {}, response)
    compact = clinical.compact(response, held, max_bytes=4096)
    section = compact["clinical"]
    assert section["findings"] == []
    assert section["page"] == {"offset": 0, "returned": 0, "total": 2, "next_offset": 0}
    assert section["canonical_ref"] == "/response/clinical/findings"
    assert (
        artifacts.load(tmp_path, held["id"])["response"]["clinical"]["findings"][0]
        == response["clinical"]["findings"][0]
    )


def test_empty_lists_terminate_without_a_false_continuation(tmp_path):
    response = many_rows(0)
    held = artifacts.save(tmp_path, {}, response)
    compact = clinical.compact(response, held)
    assert compact["clinical"]["page"] == {"offset": 0, "returned": 0, "total": 0, "next_offset": None}


@pytest.mark.parametrize("budget", [2048, 4096, 24576, 65536])
def test_actual_cli_mcp_text_envelopes_share_the_declared_budget(tmp_path, capsys, budget):
    payload = request()
    path = tmp_path / "request.json"
    path.write_text(json.dumps(payload))
    root = tmp_path / "runs"
    assert (
        main(
            [
                "reason",
                "--request",
                str(path),
                "--store",
                str(root / ".reasoning"),
                "--compact",
                "--max-bytes",
                str(budget),
            ]
        )
        == 0
    )
    text = capsys.readouterr().out
    assert len(text.encode()) <= budget
    cli = json.loads(text)
    code, reply = call_tool(
        Context(root),
        {
            "name": "reason",
            "arguments": {"request": payload, "response_view": "compact", "max_bytes": budget},
        },
    )
    assert code == "ok" and not reply["isError"]
    remote_text = reply["content"][0]["text"]
    assert len(remote_text.encode()) <= budget
    remote = json.loads(remote_text)
    assert remote.pop("tool") == "reason"
    assert remote == cli


def test_revision_budget_keeps_complete_change_projections_in_the_artifact(tmp_path):
    held = delivery.execute(request(), store=tmp_path)
    edits = [
        {
            "op": "replace",
            "path": "/premises/0/payload/status",
            "value": "interpolated",
            "origin": {"kind": "user_choice", "ref": "invented-revision", "source": None, "analysis": None},
        }
    ]
    revised = delivery.revise(tmp_path, held["artifact"]["id"], revision="two", edits=edits, max_bytes=4096)
    assert len((json.dumps(revised, ensure_ascii=False, indent=1) + "\n").encode()) <= 4096
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "support_changed" and row["axes"]["support"] == "changed"
    retained = artifacts.load(tmp_path, revised["artifact"]["id"])
    assert "before" in retained["response"]["answer_diff"]["analyses"][0]
    assert "after" in retained["response"]["answer_diff"]["analyses"][0]


@pytest.mark.parametrize("value", [None, False, True, "2048", 2048.0])
def test_mcp_byte_type_validation_follows_the_declared_schema_owner(value):
    for name in ("reason", "reason_revise"):
        args = {"request": {}} if name == "reason" else {"id": "a" * 64}
        args["max_bytes"] = value
        assert argument_problems(TOOLS[name]["inputSchema"], args) == ("wrong_type", ["max_bytes"])


@pytest.mark.parametrize("budget", [2047, 65537])
def test_malformed_budget_refuses_before_computation_or_store_creation(tmp_path, budget):
    with pytest.raises(ValueError, match="^max_bytes_out_of_range$"):
        delivery.execute(request(), store=tmp_path / "never", response_view="compact", max_bytes=budget)
    with pytest.raises(ValueError, match="^max_bytes_out_of_range$"):
        delivery.revise(tmp_path / "never", "a" * 64, session={}, max_bytes=budget)
    assert not (tmp_path / "never").exists()


def test_full_mode_stays_full_and_compact_without_storage_is_still_refused(tmp_path):
    full = delivery.execute(request(), store=tmp_path, max_bytes=2048)
    assert "result" in full and "view" not in full
    assert len(json.dumps(full, indent=1).encode()) > 2048
    with pytest.raises(ValueError, match="compact_requires_artifact_store"):
        delivery.execute(request(), response_view="compact", max_bytes=2048)
