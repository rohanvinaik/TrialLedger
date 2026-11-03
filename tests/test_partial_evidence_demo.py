"""The README's invented session executes through both public boundaries and survives revisions."""

from __future__ import annotations

import copy
import json
import socket
from pathlib import Path

import httpx
import pytest

from TrialLedger import cli
from TrialLedger.mcp_server import Context, call_tool

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "partial-evidence"


@pytest.mark.parametrize("surface", ["cli", "mcp"])
def test_readme_partial_evidence_session_is_reproducible_and_revisable(
    tmp_path, capsys, monkeypatch, surface
):
    def forbidden(*args, **kwargs):
        raise AssertionError("the worked session must not fetch or invent source evidence")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    before = {p.name: p.read_bytes() for p in EXAMPLE.iterdir() if p.is_file()}

    def invoke(request):
        if surface == "cli":
            path = tmp_path / "request.json"
            path.write_text(json.dumps(request))
            assert cli.main(["reason", "--request", str(path)]) == 0
            return json.loads(capsys.readouterr().out)
        code, response = call_tool(Context(tmp_path), {"name": "reason", "arguments": {"request": request}})
        assert code == "ok" and not response["isError"]
        reply = json.loads(response["content"][0]["text"])
        assert reply.pop("tool") == "reason"
        return reply

    request = json.loads((EXAMPLE / "design-request.json").read_text())
    result = invoke(request)
    assert result == json.loads((EXAMPLE / "design-result.json").read_text())
    rows = {row["id"]: row for row in result["result"]["candidates"]}
    assert result["result"]["remaining"] == ["marker-PS0-2", "marker-PS0-3", "adult-PS0-2"]
    assert sum(row["state"] == "ruled_out" for row in rows.values()) == 9
    assert result["result"]["consequence"]["result"] == "UNDETERMINED"
    signals = {row["id"]: row for row in result["result"]["signals"]}
    assert signals["joint"]["value"]["counts"] == [{"id": "intersection", "lower": 20, "upper": 40}]
    assert signals["cohorts"]["value"]["counts"][1] == {"id": "cohort-B", "lower": 60, "upper": 60}
    assert signals["age-summary"]["value"]["counts"] == [{"id": "summary", "lower": 100, "upper": 200}]
    assert signals["analysis"]["value"]["counts"][2] == {"id": "outside", "lower": 40, "upper": 40}
    assert signals["change-score"]["code"] == "unresolved"
    assert rows["marker-PS0-2"]["signal_checks"][0]["code"] == "consistent"
    # All eight kinds reach an actual witness or joint-claim consumer, not just standalone helper output.
    for candidate, ref in [
        ("everyone-analysed", "analysis"),
        ("randomize-before-induction-ends", "sequence"),
        ("ingredient-A-only", "regimen"),
        ("marker-A-outside-family", "marker-family"),
        ("no-week12-observation", "change-score"),
    ]:
        assert any(
            check["id"] == ref and check["code"] == "conflict" for check in rows[candidate]["signal_checks"]
        )
    for candidate, observation in [
        ("excludes-joint", "joint-participants"),
        ("cohort-A-only", "cohort-B-participants"),
        ("under65-only", "age65-plus-participants"),
        ("PS-only", "eligibility-rejection"),
    ]:
        assert any(
            row["observation"] == observation and row["state"] == "ruled_out"
            for row in rows[candidate]["observations"]
        )
    revised = copy.deepcopy(request)
    revised["observations"][0]["bridge"]["max_exceptions"] = 20
    assert "excludes-joint" in invoke(revised)["result"]["remaining"]
    revised["observations"][0]["bridge"]["max_exceptions"] = 19
    assert "excludes-joint" not in invoke(revised)["result"]["remaining"]
    revised = copy.deepcopy(request)
    revised["observations"][3]["bridge"]["resolution"] = "unresolved"
    screen_rows = {row["id"]: row for row in invoke(revised)["result"]["candidates"]}
    assert screen_rows["PS-only"]["state"] == "unresolved"
    revised = copy.deepcopy(request)
    revised["candidates"][0]["signal_claims"][0]["claim"]["available"][0]["mode"] = "imputed"
    imputed_rows = {row["id"]: row for row in invoke(revised)["result"]["candidates"]}
    assert imputed_rows["marker-PS0-2"]["state"] == "unresolved"
    draft = json.loads((EXAMPLE / "draft-request.json").read_text())
    assert invoke(draft) == json.loads((EXAMPLE / "draft-result.json").read_text())
    assert invoke(draft)["result"]["decision"]["result"] == "REFUTED"
    draft["assertions"][1]["body"]["value"]["number"] = 3
    widened = invoke(draft)["result"]["decision"]
    assert widened["result"] == "UNDETERMINED" and widened["blockers"] == ["undecided_by_constraints"]
    draft["query"]["value"]["number"] = -1
    assert invoke(draft)["result"]["decision"]["result"] == "REFUTED"
    assert {p.name: p.read_bytes() for p in EXAMPLE.iterdir() if p.is_file()} == before
