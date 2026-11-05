"""Executable guard (task 7.2): every published runnable discovery example runs to complete as published.

Views are read from the code's DISCOVERY_VIEWS, never hard-coded. A published example is any request dict
(an `operation` from OPERATIONS) a view returns, found by walking the described result at every detail level;
shape descriptions (input_shapes, operations, fields) are not examples. A prepare request is prepared and the
expanded request is then run. Protocol examples also run through the CLI and an initialized MCP client, and
the three result digests must agree.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.test_protocol_mcp_lifecycle import McpClient
from TrialLedger.capabilities import DISCOVERY_VIEWS, OPERATIONS
from TrialLedger.layer2 import run

ROOT = Path(__file__).resolve().parents[1]
CLI = str(Path(sys.executable).with_name("trialledger"))
DETAILS = ("card", "schema", "full")
# Containers that describe request shapes or list operations, not runnable examples.
NOT_EXAMPLES = (
    "/input_shapes",
    "/operations/",
    "/result_guides",
    "/compact_shapes",
    "/input/",
    "/use_cases/",
)
# Intentionally unrunnable published requests: path-independent request digest -> reason.
SKIPPED: dict[str, str] = {}


def _digest(request: dict) -> str:
    return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:16]


def _walk(node: object, path: str, found: list[tuple[str, dict]]) -> None:
    if isinstance(node, dict):
        # The root dict is the described card itself: its `operation` names what is described.
        if path and isinstance(node.get("operation"), str) and node["operation"] in OPERATIONS:
            if not any(part in path + "/" for part in NOT_EXAMPLES):
                found.append((path, node))
            return
        for key, value in node.items():
            _walk(value, f"{path}/{key}", found)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk(value, f"{path}/{index}", found)


PUBLISHING_VIEWS: set[str] = set()


def published_examples() -> dict[str, tuple[str, dict]]:
    """Unique published requests keyed by digest, each with its first `view/detail/path` location."""
    unique: dict[str, tuple[str, dict]] = {}
    for view in DISCOVERY_VIEWS:
        for detail in DETAILS:
            reply = run({"operation": "describe", "view": view, "detail": detail})
            assert reply["code"] == "complete", (view, detail, reply["problems"])
            found: list[tuple[str, dict]] = []
            _walk(reply["result"], "", found)
            if found:
                PUBLISHING_VIEWS.add(view)
            for path, request in found:
                unique.setdefault(_digest(request), (f"{view}/{detail}{path}", copy.deepcopy(request)))
    return unique


EXAMPLES = published_examples()


def executed(request: dict) -> dict:
    """Run a request as published; a prepare request is prepared and its expanded request is run."""
    reply = run(copy.deepcopy(request))
    assert reply["code"] == "complete", reply["problems"]
    if request["operation"] == "prepare":
        reply = run(copy.deepcopy(reply["result"]["request"]))
        assert reply["code"] == "complete", reply["problems"]
    return reply


def test_every_discovery_view_is_described_and_publishes_something():
    assert set(DISCOVERY_VIEWS) >= {"overview", "prepare", "protocol", "delivery", "worked_session", "full"}
    # Only the delivery view describes retention and export; it publishes no request of its own.
    assert set(DISCOVERY_VIEWS) - {"delivery"} == PUBLISHING_VIEWS
    assert len(EXAMPLES) >= len(DISCOVERY_VIEWS)


@pytest.mark.parametrize("key", sorted(EXAMPLES), ids=[EXAMPLES[k][0] for k in sorted(EXAMPLES)])
def test_every_published_example_runs_to_complete_as_published(key):
    where, request = EXAMPLES[key]
    if key in SKIPPED:
        pytest.skip(SKIPPED[key])
    reply = executed(request)
    assert reply["result"], where


def test_every_view_card_is_stable_across_repeated_discovery():
    for view in DISCOVERY_VIEWS:
        first = run({"operation": "describe", "view": view})
        assert first == run({"operation": "describe", "view": view}), view


# ---------------------------------------------------------------------------------------------------------
# Protocol examples: CLI / MCP parity
# ---------------------------------------------------------------------------------------------------------


def protocol_examples() -> dict:
    reply = run({"operation": "describe", "view": "protocol", "detail": "full"})
    assert reply["code"] == "complete"
    return reply["result"]["examples"]


PROTOCOL = protocol_examples()


def cli_reason(path: Path) -> dict:
    done = subprocess.run([CLI, "reason", "--request", str(path)], capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 0, done.stderr or done.stdout
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def mcp(tmp_path_factory):
    client = McpClient(tmp_path_factory.mktemp("served") / "root")
    yield client
    client.close()


@pytest.mark.parametrize("family", sorted(PROTOCOL))
def test_protocol_example_matches_across_in_process_cli_and_mcp(family, mcp, tmp_path):
    preparation = tmp_path / "prepare.json"
    preparation.write_text(json.dumps(PROTOCOL[family]))
    prepared = cli_reason(preparation)
    assert prepared["code"] == "complete", prepared["problems"]
    expanded = prepared["result"]["request"]
    assert expanded == run(copy.deepcopy(PROTOCOL[family]))["result"]["request"]
    request = tmp_path / "request.json"
    request.write_text(json.dumps(expanded))
    cli_reply = cli_reason(request)
    mcp_reply = mcp.call("reason", request=expanded)
    local = run(copy.deepcopy(expanded))
    assert cli_reply["code"] == mcp_reply["code"] == local["code"] == "complete", family
    assert cli_reply["result_digest"] == mcp_reply["result_digest"] == local["result_digest"], family
    mcp_prepared = mcp.call("reason", request=PROTOCOL[family])
    assert mcp_prepared["result_digest"] == prepared["result_digest"], family
