"""Real CLI/MCP reasoning is separate, conditional, network-free and read-only on reports."""

from __future__ import annotations

import hashlib
import json
import socket
import urllib.request
from pathlib import Path

import httpx
import pytest

from TrialLedger import cli
from TrialLedger.layer2 import service, signals


def fact(key, value):
    return {
        "class": "Literal",
        "subject": {"class": "Subject", "kind": "participant"},
        "predicate": {"class": "Predicate", "kind": "disease_attribute", "key": key},
        "value": {"class": "Value", "kind": "enum", "members": [value]},
    }


def alternatives_request():
    a, b = fact("EGFR", "positive"), fact("ALK", "positive")
    return {
        "operation": "entailment",
        "assertions": [
            {
                "class": "ScopedAssertion",
                "id": "alternative",
                "criterion_ref": "user:typed-premise",
                "modality": "required",
                "body": {"class": "AnyOf", "parts": [a, b]},
                "rule": {
                    "class": "Rule",
                    "id": "user-premise",
                    "version": "1",
                    "warrants": ["user:typed-premise"],
                },
                "status": "known",
                "resolution": "resolved",
            }
        ],
        "query": a,
    }


COORDINATES = {
    "operation": "coordinates",
    "domain": "nsclc",
    "evidence": [
        {
            "section": "inclusion",
            "concept": "prior_lines",
            "values": ["0"],
            "scope": "advanced",
            "ref": "user:lines",
            "standing": {"status": "known", "resolution": "resolved", "basis": ["user:lines"]},
        },
        {
            "section": "inclusion",
            "concept": "extent",
            "values": ["advanced"],
            "scope": "",
            "ref": "user:extent",
            "standing": {"status": "known", "resolution": "resolved", "basis": ["user:extent"]},
        },
    ],
}
REFUSED = [
    {"operation": "coordinates", "domain": "diabetes", "evidence": []},
    {"operation": "coordinates", "domain": "nsclc", "evidence": "EGFR-positive or ALK-positive"},
    {"operation": "entailment", "assertions": ["Age >= 18"], "query": fact("age", "18")},
    {"operation": "corpus", "studies": [{"protocolSection": {}}]},
    {"operation": "design"},
]


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("reason must never use the network")

    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(urllib.request, "urlopen", fail)
    monkeypatch.setattr(httpx.Client, "send", fail)
    return fail


def snapshot(folder: Path):
    return {
        path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.rglob("*")
        if path.is_file()
    }


@pytest.fixture
def reports(tmp_path):
    saved = tmp_path / "reports"
    saved.mkdir()
    (saved / "landscape.json").write_text('{"retained":"source-record"}')
    (saved / "landscape.xlsx").write_bytes(b"retained workbook bytes")
    (saved / "bodies").mkdir()
    (saved / "bodies" / "studies-001.json").write_text('{"studies":[]}')
    return saved


def invoke_cli(payload, reports, tmp_path, capsys):
    request = tmp_path / "premises.json"
    request.write_text(json.dumps(payload))
    before = snapshot(reports)
    code = cli.main(["reason", "--request", str(request)])
    captured = capsys.readouterr()
    assert snapshot(reports) == before
    assert captured.err == ""
    return code, json.loads(captured.out)


def invoke_mcp(payload, reports, forbid_network):
    def line(ident, method, params):
        return json.dumps({"jsonrpc": "2.0", "id": ident, "method": method, "params": params}).encode()

    lines = [
        line(
            1,
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "reason-test", "version": "1"},
            },
        ),
        line(2, "tools/call", {"name": "reason", "arguments": {"request": payload}}),
    ]
    written = []
    before = snapshot(reports)
    code = cli.main(
        ["mcp", "--root", str(reports)],
        rxclass_get=forbid_network,
        probe_get=forbid_network,
        mcp_streams=(lines, written.append),
    )
    assert code == 0
    assert snapshot(reports) == before
    assert len(written) == 2
    reply = json.loads(written[-1])
    assert "error" not in reply
    result = reply["result"]
    document = json.loads(result["content"][0]["text"])
    assert document["tool"] == "reason" and "run_folder" not in document
    return result["isError"], document


def test_cli_preserves_alternatives_and_reports_conditional_proof(reports, tmp_path, capsys):
    code, result = invoke_cli(alternatives_request(), reports, tmp_path, capsys)
    assert code == 0 and result["code"] == "complete"
    assert result["result"]["decision"]["result"] == "UNDETERMINED"
    assert result["result"]["premises"][0]["body"]["class"] == "AnyOf"
    assert "Conditional" in result["result"]["basis"]


def test_mcp_preserves_alternatives_and_reports_conditional_proof(reports, forbid_network):
    error, result = invoke_mcp(alternatives_request(), reports, forbid_network)
    assert not error and result["code"] == "complete"
    assert result["result"]["decision"]["result"] == "UNDETERMINED"
    assert result["result"]["premises"][0]["body"]["class"] == "AnyOf"


def test_cli_exposes_a_deduction_with_its_supplied_premise(reports, tmp_path, capsys):
    payload = alternatives_request()
    payload["query"] = payload["assertions"][0]["body"]
    code, result = invoke_cli(payload, reports, tmp_path, capsys)
    assert code == 0
    assert result["result"]["decision"]["result"] == "ENTAILED"
    assert result["result"]["decision"]["proof"] == ["alternative"]


def test_mcp_exposes_a_deduction_with_its_supplied_premise(reports, forbid_network):
    payload = alternatives_request()
    payload["query"] = payload["assertions"][0]["body"]
    error, result = invoke_mcp(payload, reports, forbid_network)
    assert not error
    assert result["result"]["decision"]["result"] == "ENTAILED"
    assert result["result"]["decision"]["proof"] == ["alternative"]


def test_cli_keeps_nsclc_defaults_out_of_known_level(reports, tmp_path, capsys):
    code, result = invoke_cli(COORDINATES, reports, tmp_path, capsys)
    assert code == 0
    setting = result["result"]["coordinates"]["setting"]
    assert setting["state"] == "unnarrowed" and len(setting["domain"]) > 1
    assert setting["interpolated"]["domain"] == ["advanced_first_line"]


def test_mcp_keeps_nsclc_defaults_out_of_known_level(reports, forbid_network):
    error, result = invoke_mcp(COORDINATES, reports, forbid_network)
    assert not error
    setting = result["result"]["coordinates"]["setting"]
    assert setting["state"] == "unnarrowed" and len(setting["domain"]) > 1
    assert setting["interpolated"]["domain"] == ["advanced_first_line"]


@pytest.mark.parametrize("payload", REFUSED)
def test_cli_refuses_unsupported_or_raw_requests(reports, tmp_path, capsys, payload):
    code, result = invoke_cli(payload, reports, tmp_path, capsys)
    assert code == 2 and result["code"] == "refused" and result["problems"]
    assert result["result"] is None


@pytest.mark.parametrize("payload", REFUSED)
def test_mcp_refuses_unsupported_or_raw_requests(reports, forbid_network, payload):
    error, result = invoke_mcp(payload, reports, forbid_network)
    assert error and result["code"] == "refused" and result["problems"]
    assert result["result"] is None


def test_cli_refuses_ambiguous_json_without_touching_reports(reports, tmp_path, capsys):
    request = tmp_path / "ambiguous.json"
    request.write_text('{"operation":"coordinates","operation":"corpus"}')
    before = snapshot(reports)
    assert cli.main(["reason", "--request", str(request)]) == 2
    captured = capsys.readouterr()
    assert "unreadable request" in captured.err
    assert snapshot(reports) == before


def test_cli_discovery_delivers_every_worked_request_ready_to_run(reports, tmp_path, capsys):
    code, reply = invoke_cli({"operation": "describe", "view": "full"}, reports, tmp_path, capsys)
    assert code == 0 and reply["code"] == "complete"
    description = reply["result"]
    assert description["clinical_use"] and description["use_cases"] and description["result_guides"]
    requests = [
        *description["examples"].values(),
        *description["signal_examples"].values(),
        *(example["request"] for example in description["capability_examples"].values()),
    ]
    assert {request["operation"] for request in requests} == set(service.OPERATIONS) - {"describe"}
    assert set(description["signal_examples"]) == set(signals.MODULES)
    assert {
        signal["kind"] for request in description["signal_examples"].values() for signal in request["signals"]
    } == set(signals.MODULES)
    for request in requests:
        code, result = invoke_cli(request, reports, tmp_path, capsys)
        assert code == 0 and result["code"] == "complete"
        assert set(description["result_guides"][request["operation"]]["fields"]) == set(result["result"])


def test_mcp_discovery_delivers_every_worked_request_ready_to_run(reports, forbid_network):
    error, reply = invoke_mcp({"operation": "describe", "view": "full"}, reports, forbid_network)
    assert not error and reply["code"] == "complete"
    description = reply["result"]
    assert description["clinical_use"] and description["use_cases"] and description["result_guides"]
    requests = [
        *description["examples"].values(),
        *description["signal_examples"].values(),
        *(example["request"] for example in description["capability_examples"].values()),
    ]
    assert {request["operation"] for request in requests} == set(service.OPERATIONS) - {"describe"}
    assert set(description["signal_examples"]) == set(signals.MODULES)
    assert {
        signal["kind"] for request in description["signal_examples"].values() for signal in request["signals"]
    } == set(signals.MODULES)
    for request in requests:
        error, result = invoke_mcp(request, reports, forbid_network)
        assert not error and result["code"] == "complete"
        assert set(description["result_guides"][request["operation"]]["fields"]) == set(result["result"])
