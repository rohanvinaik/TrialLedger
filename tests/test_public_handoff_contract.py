"""Public discovery and descriptive counts must not misstate usable clinical information."""

from __future__ import annotations

import copy
import json

import pytest

from scripts.trace_reasoning_consumers import invoke
from TrialLedger import cli
from TrialLedger.capabilities import DISCOVERY_VIEWS, OPERATIONS, REASONING_OPERATIONS
from TrialLedger.layer2 import run


def test_emitted_schema_advertises_every_executable_focused_operation(tmp_path):
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "handoff-test", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    written = []
    assert (
        cli.main(
            ["mcp", "--root", str(tmp_path)],
            mcp_streams=([json.dumps(m).encode() for m in messages], written.append),
        )
        == 0
    )
    tools = json.loads(written[-1])["result"]["tools"]
    tool = next(t for t in tools if t["name"] == "reason")
    properties = tool["inputSchema"]["properties"]["request"]["properties"]
    assert properties["operation"]["enum"] == list(OPERATIONS)
    assert properties["view"]["enum"] == list(DISCOVERY_VIEWS)
    for operation in REASONING_OPERATIONS:
        assert operation in tool["description"]
        guide = run({"operation": "describe", "view": operation})
        assert guide["code"] == "complete"
        request = guide["result"]["example"]
        assert request["operation"] == operation
        assert run(request)["code"] == "complete"
    assert run({"operation": "design"})["code"] == "refused"


def two_trial_request():
    request = run({"operation": "describe", "view": "corpus"})["result"]["example"]
    first = request["trials"][0]
    second = copy.deepcopy(first)
    second["id"] = "invented-second-record"
    second["sponsor"] = "invented-second-sponsor"
    request["trials"] = [first, second]
    return request


@pytest.mark.parametrize("mode", ["cli", "mcp"])
def test_two_of_two_is_descriptive_and_retraction_reopens_silence(mode, tmp_path):
    request = two_trial_request()
    initial = invoke(request, mode, tmp_path)
    row = initial["result"]["frequency"][0]
    assert (row["stating"], row["trials"], row["tier"]) == (2, 2, "met")
    assert row["description"] == {
        "scope": "declared_comparison_set",
        "stating": 2,
        "trials": 2,
        "threshold": 0.9,
        "meaning": "descriptive frequency threshold; no clinical standard or recommendation",
    }
    assert initial["result"]["associations"] == []
    frequency_findings = [
        f for f in initial["metadata"]["findings"] if f["path"].startswith("/result/frequency/")
    ]
    assert frequency_findings
    assert all(f["disposition"] == "descriptive" for f in frequency_findings)
    request["trials"][1]["elements"] = []
    revised = invoke(request, mode, tmp_path)
    row = revised["result"]["frequency"][0]
    assert (row["stating"], row["trials"], row["lower"], row["upper"]) == (1, 2, 0.5, 1.0)
    assert row["tier"] == "unresolved"
    assert row["absence_established"] == 0
    assert row["description"]["stating"] == 1


def test_noneligibility_frequency_has_no_eligibility_threshold():
    request = two_trial_request()
    for trial in request["trials"]:
        trial["elements"] = ["primary:invented_endpoint"]
    row = run(request)["result"]["frequency"][0]
    assert row["tier"] == ""
    assert row["description"]["threshold"] is None
