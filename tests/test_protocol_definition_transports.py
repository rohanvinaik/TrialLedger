"""Task 5.4 transport evidence: a protocol-operand definition relation through the CLI and initialized MCP.

Both transports run the same canonical request; the computed result must be byte-identical (equal
`result_digest`) and the relation row must be the same `consistent` row the direct call gives.
"""

import json

import pytest

from tests.test_protocol_definition_relations import _with_relation
from tests.test_protocol_mcp_lifecycle import McpClient, cli
from TrialLedger.layer2 import run


@pytest.fixture
def mcp(tmp_path):
    client = McpClient(tmp_path / "served")
    yield client
    client.close()


def _cli_reply(tmp_path, request: dict) -> dict:
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    return cli("reason", "--request", str(path))


def test_implies_relation_over_protocol_operands_agrees_across_direct_cli_and_mcp(mcp, tmp_path):
    """DEF-1 across transports: equal result_digest and a consistent relation row on all three."""
    request = _with_relation("implies", "relapse-check", "retreatment-check")
    direct = run(request)
    via_cli = _cli_reply(tmp_path, request)
    via_mcp = mcp.call("reason", request=request)

    for reply in (direct, via_cli, via_mcp):
        assert reply["code"] == "complete"
        rows = reply["result"]["definition_checks"]
        assert len(rows) == 1
        assert rows[0]["code"] == "consistent"
        assert rows[0]["status"] == "known"
        assert rows[0]["blockers"] == []
    assert via_cli["result_digest"] == direct["result_digest"]
    assert via_mcp["result_digest"] == direct["result_digest"]
    assert via_cli["result"]["definition_checks"] == via_mcp["result"]["definition_checks"]
    assert via_cli["result"]["protocol"] == via_mcp["result"]["protocol"]


def test_refuted_equivalence_is_the_same_conflict_on_both_transports(mcp, tmp_path):
    """MUST-NOT: a transport cannot soften the relation; a refuted equivalence is a conflict on both."""
    request = _with_relation("equivalent", "relapse-check", "retreatment-check")
    via_cli = _cli_reply(tmp_path, request)
    via_mcp = mcp.call("reason", request=request)

    assert via_cli["result"]["definition_checks"][0]["code"] == "conflict"
    assert via_mcp["result"]["definition_checks"][0]["code"] == "conflict"
    assert via_cli["result_digest"] == via_mcp["result_digest"]
    # The two transports must not agree merely because both are consistent: this digest differs from implies.
    implied = _cli_reply(tmp_path, _with_relation("implies", "relapse-check", "retreatment-check"))
    assert implied["result_digest"] != via_cli["result_digest"]


def test_a_proposed_operand_is_blocked_identically_on_both_transports(mcp, tmp_path):
    """MUST-NOT: a proposed reading is never admitted by either transport."""
    request = _with_relation("implies", "relapse-check", "retreatment-check")
    request["session"]["definition_checks"][0]["left"]["status"] = "proposed"
    via_cli = _cli_reply(tmp_path, request)
    via_mcp = mcp.call("reason", request=request)
    for reply in (via_cli, via_mcp):
        row = reply["result"]["definition_checks"][0]
        assert row["code"] == "unresolved"
        assert row["blockers"] == ["definition_proposed_refused"]
        assert row["checks"] == []
    assert via_cli["result_digest"] == via_mcp["result_digest"]
