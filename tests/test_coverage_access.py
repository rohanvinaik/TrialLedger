"""Exact, bounded coverage access through the shared public CLI and initialized MCP."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tests.test_protocol_mcp_lifecycle import CLI, ROOT
from tests.test_search_coverage_run import Registry, compare, make_run
from TrialLedger.evidence_access import read_record
from TrialLedger.record_access import response_bytes

OWNER = str(Path.home() / "Projects/SquishOS/ops/agents/bin/owned-run")


@pytest.fixture
def coverage_folder(tmp_path):
    folder = make_run(tmp_path)
    assert compare(folder, Registry())[0] == "complete"
    return folder


def read(folder, **arguments):
    return read_record(folder, {"part": "coverage", **arguments})


def test_coverage_reads_the_producers_exact_document_without_a_source_record(coverage_folder):
    raw = (coverage_folder / "coverage.json").read_bytes()
    reply, error = read(coverage_folder)
    assert not error, reply
    assert reply["value"] == json.loads(raw)
    assert reply["part"] == "coverage" and reply["coverage_file"] == "comparison"
    assert reply["snapshot"]["digest"] == hashlib.sha256(raw).hexdigest()
    assert reply["snapshot"]["file"] == "coverage.json"
    assert reply["snapshot"]["state"] == "complete"
    assert not (coverage_folder / "landscape.json").exists()


def test_an_address_reads_the_exact_id_set_and_every_page(coverage_folder):
    document = json.loads((coverage_folder / "coverage.json").read_bytes())
    found, offset = [], 0
    while offset is not None:
        reply, error = read(coverage_folder, address="/comparison/intersection", offset=offset, limit=1)
        assert not error, reply
        assert reply["address"] == "/comparison/intersection"
        found.extend(reply["value"])
        offset = reply["page"]["next_offset"]
    assert found == document["comparison"]["intersection"]


def test_text_continuation_preserves_the_selected_value_and_the_files(coverage_folder):
    path = coverage_folder / "coverage.json"
    document = json.loads(path.read_bytes())
    document["note"] = "literal café \u03b1\n" * 2000
    path.write_text(json.dumps(document, ensure_ascii=False))
    before = {p: p.read_bytes() for p in coverage_folder.iterdir() if p.is_file()}
    found, offset = "", 0
    while offset is not None:
        reply, error = read(coverage_folder, address="/note", text_offset=offset, text_limit=300)
        assert not error, reply
        found += reply["text"]
        offset = reply["text_page"]["next_offset"]
    assert found == document["note"]
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("state", ["not_run", "awaiting_fetch", "failed", "incomplete", "snapshot_differs"])
def test_unfinished_coverage_is_read_as_written_never_an_empty_completed_comparison(tmp_path, state):
    document = {"schema": "coverage-1", "state": state, "difference_words": "No statement is made."}
    (tmp_path / "coverage.json").write_text(json.dumps(document))
    reply, error = read(tmp_path)
    assert not error, reply
    assert reply["value"] == document and reply["snapshot"]["state"] == state
    assert "comparison" not in reply["value"]


def test_union_request_is_read_exactly_and_bound_to_the_current_offer(coverage_folder):
    raw = (coverage_folder / "coverage_union_request.json").read_bytes()
    reply, error = read(coverage_folder, coverage_file="union_request")
    assert not error, reply
    assert reply["value"] == json.loads(raw)
    assert reply["snapshot"]["digest"] == hashlib.sha256(raw).hexdigest()
    assert (
        reply["snapshot"]["comparison_digest"]
        == hashlib.sha256((coverage_folder / "coverage.json").read_bytes()).hexdigest()
    )


@pytest.mark.parametrize("state,offered", [("failed", True), ("complete", False)])
def test_a_leftover_union_file_never_becomes_a_current_offer(coverage_folder, state, offered):
    path = coverage_folder / "coverage.json"
    document = json.loads(path.read_bytes())
    document["state"], document["union"]["offered"] = state, offered
    path.write_text(json.dumps(document))
    reply, error = read(coverage_folder, coverage_file="union_request")
    assert error and reply["error"] == "coverage_union_not_offered"
    assert "value" not in reply


def test_a_union_file_with_different_ids_is_not_certified_by_its_presence(coverage_folder):
    (coverage_folder / "coverage_union_request.json").write_text(
        json.dumps({"params": {"filter.ids": "NCT99999999"}})
    )
    reply, error = read(coverage_folder, coverage_file="union_request")
    assert error and reply["error"] == "coverage_union_mismatch"


@pytest.mark.parametrize("selector", ["../request.json", "coverage.md", "", None, 1])
def test_coverage_file_selection_is_a_fixed_whitelist(coverage_folder, selector):
    reply, error = read(coverage_folder, coverage_file=selector)
    assert error and reply["error"] == "invalid_coverage_file"


def test_coverage_file_is_refused_on_another_part_instead_of_ignored(coverage_folder):
    reply, error = read_record(coverage_folder, {"part": "studies", "coverage_file": "comparison"})
    assert error and reply["error"] == "coverage_file_requires_coverage_part"


@pytest.mark.parametrize("filename", ["coverage.json", "coverage_union_request.json"])
def test_a_sidecar_symlink_cannot_escape_the_authorized_run(coverage_folder, tmp_path, filename):
    path = coverage_folder / filename
    outside = tmp_path / "outside.json"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    selector = "comparison" if filename == "coverage.json" else "union_request"
    reply, error = read(coverage_folder, coverage_file=selector)
    assert error and reply["error"] == "coverage_file_outside_run"


@pytest.mark.parametrize(
    "raw,code",
    [
        ('{"schema":"coverage-1","state":"failed","state":"complete"}', "coverage_duplicate_json_key"),
        ('{"schema":"coverage-1","state":"failed","number":NaN}', "coverage_json_invalid"),
        ('{"schema":"coverage-1","state":"failed","number":1e999}', "coverage_json_invalid"),
        ('{"schema":"coverage-2","state":"failed"}', "coverage_schema_unsupported"),
        ('{"schema":"coverage-1","state":"imaginary"}', "coverage_state_unsupported"),
        ("[]", "coverage_document_invalid"),
        ("null", "coverage_document_invalid"),
        ('{"schema":"coverage-1","state":"complete"}', "coverage_document_invalid"),
    ],
)
def test_malformed_evidence_is_refused_without_inventing_an_empty_comparison(tmp_path, raw, code):
    (tmp_path / "coverage.json").write_text(raw)
    reply, error = read(tmp_path)
    assert error and reply["error"] == code and "value" not in reply


@pytest.mark.parametrize(
    "arguments,code",
    [
        ({"address": "/not-held"}, "outside_record"),
        ({"address": "not-a-pointer"}, "not_a_pointer"),
        ({"offset": -1}, "offset_out_of_range"),
        ({"offset": True}, "offset_out_of_range"),
        ({"limit": 0}, "limit_out_of_range"),
        ({"limit": 51}, "limit_out_of_range"),
        ({"max_bytes": 2047}, "max_bytes_out_of_range"),
        ({"text_offset": 0}, "not_text"),
    ],
)
def test_invalid_selection_arguments_keep_the_shared_named_refusal(coverage_folder, arguments, code):
    reply, error = read(coverage_folder, **arguments)
    assert error and reply["error"] == code


def test_minimum_budget_never_loses_an_id_or_exceeds_the_data_reply_budget(coverage_folder):
    document = json.loads((coverage_folder / "coverage.json").read_bytes())
    document["long_list"] = [{"text": "x" * 500} for _ in range(70)]
    (coverage_folder / "coverage.json").write_text(json.dumps(document))
    reply, error = read(coverage_folder, address="/long_list", max_bytes=2048)
    assert not error, reply
    assert response_bytes(reply) <= 2048
    assert reply["page"]["next_offset"] is not None


def test_missing_coverage_does_not_claim_a_comparison_was_run(tmp_path):
    reply, error = read(tmp_path)
    assert error and reply["error"] == "coverage_not_available"


class CoverageMcp:
    """Initialize the actual public MCP command, with an owned temporary process group."""

    def __init__(self, root):
        self.process = subprocess.Popen(
            [OWNER, "--label", "coverage-interface-test", "--", CLI, "mcp", "--root", str(root)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            cwd=ROOT,
        )
        self.ident = 0
        self.send(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "coverage-test", "version": "1"},
            },
        )
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.process.stdin.flush()

    def send(self, method, params):
        self.ident += 1
        self.process.stdin.write(
            json.dumps({"jsonrpc": "2.0", "id": self.ident, "method": method, "params": params}) + "\n"
        )
        self.process.stdin.flush()
        reply = json.loads(self.process.stdout.readline())
        assert reply["id"] == self.ident and "error" not in reply
        return reply["result"]

    def call(self, arguments):
        result = self.send("tools/call", {"name": "record", "arguments": arguments})
        return json.loads(result["content"][0]["text"]), result["isError"]

    def close(self):
        self.process.stdin.close()
        assert self.process.wait(timeout=30) == 0


def test_cli_and_initialized_mcp_read_the_same_comparison_and_union(coverage_folder):
    client = CoverageMcp(coverage_folder.parent)
    try:
        for selector in ("comparison", "union_request"):
            result = subprocess.run(
                [CLI, "record", str(coverage_folder), "--part", "coverage", "--coverage-file", selector],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr or result.stdout
            cli_reply = json.loads(result.stdout)
            mcp_reply, error = client.call(
                {"run": coverage_folder.name, "part": "coverage", "coverage_file": selector}
            )
            assert not error and cli_reply == mcp_reply
    finally:
        client.close()


def test_discovery_exposes_the_selector_and_explicit_drug_additions(coverage_folder):
    client = CoverageMcp(coverage_folder.parent)
    try:
        tools = {tool["name"]: tool for tool in client.send("tools/list", {})["tools"]}
        properties = tools["record"]["inputSchema"]["properties"]
        assert "coverage" in properties["part"]["enum"]
        assert properties["coverage_file"]["enum"] == ["comparison", "union_request"]
        additions = tools["landscape"]["inputSchema"]["properties"]["request"]["properties"][
            "class_drug_additions"
        ]
        assert additions["type"] == "array" and additions["items"]["type"] == "string"
        assert additions["minItems"] == 1
    finally:
        client.close()


# Direct-call signs for the new pure decisions (routable by Detective's later serialized pass).


def test_selector_accepts_only_the_two_document_roles():
    from TrialLedger.coverage_access import coverage_selector_code

    assert coverage_selector_code("comparison") == "comparison"
    assert coverage_selector_code("union_request") == "union_request"


def test_selector_never_converts_a_path_or_nontext_value_into_a_document_role():
    from TrialLedger.coverage_access import coverage_selector_code

    assert coverage_selector_code("../coverage.json") == "invalid_coverage_file"
    assert coverage_selector_code(None) == "invalid_coverage_file"
    assert coverage_selector_code(["comparison"]) == "invalid_coverage_file"


def test_document_accepts_an_explicit_incomplete_state_without_inventing_a_comparison():
    from TrialLedger.coverage_access import coverage_document_code

    assert coverage_document_code({"schema": "coverage-1", "state": "failed"}) == "ok"


def test_document_never_promotes_an_unsupported_schema_state_or_absent_structure():
    from TrialLedger.coverage_access import coverage_document_code

    assert (
        coverage_document_code({"schema": "coverage-2", "state": "failed"}) == "coverage_schema_unsupported"
    )
    assert (
        coverage_document_code({"schema": "coverage-1", "state": "invented"}) == "coverage_state_unsupported"
    )
    assert (
        coverage_document_code({"schema": "coverage-1", "state": "complete"}) == "coverage_document_invalid"
    )
    assert coverage_document_code(None) == "coverage_document_invalid"
