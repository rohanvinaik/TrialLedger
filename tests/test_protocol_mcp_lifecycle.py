"""The complete public protocol lifecycle through an initialized MCP client, and its parity with the CLI."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

from tests.test_protocol_session_replay import new_edition

ROOT = Path(__file__).resolve().parents[1]
CLI = str(Path(sys.executable).with_name("trialledger"))
FIXTURES = ROOT / "openspec/changes/connect-protocol-design-workflow/interface/fixtures"
SECTIONS = [
    "population",
    "eligibility",
    "interventions",
    "endpoints",
    "assessments",
    "efficacy",
    "safety",
    "exploratory",
]
SHEETS = [
    "Protocol synopsis",
    "Protocol findings",
    "Schedule of assessments",
    "Plan comparisons",
    "Protocol adoption",
]
ADOPTION = {"ref": "user:invented adoption", "status": "known", "resolution": "resolved"}


class McpClient:
    """A real `trialledger mcp` subprocess, initialized over JSON-RPC lines."""

    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.process = subprocess.Popen(
            [CLI, "mcp", "--root", str(root)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            cwd=ROOT,
        )
        self.ident = 0
        reply = self.send(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "lifecycle-test", "version": "1"},
            },
        )
        assert reply["result"]["serverInfo"]
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.process.stdin.flush()

    def send(self, method: str, params: dict) -> dict:
        self.ident += 1
        message = {"jsonrpc": "2.0", "id": self.ident, "method": method, "params": params}
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        reply = json.loads(self.process.stdout.readline())
        assert reply["id"] == self.ident and "error" not in reply, reply
        return reply

    def call(self, name: str, **arguments) -> dict:
        result = self.send("tools/call", {"name": name, "arguments": arguments})["result"]
        document = json.loads(result["content"][0]["text"])
        assert not result["isError"], document
        return document

    def close(self) -> None:
        self.process.stdin.close()
        assert self.process.wait(timeout=30) == 0


@pytest.fixture
def mcp(tmp_path):
    client = McpClient(tmp_path / "served")
    yield client
    client.close()


def cli(*args: str) -> dict:
    done = subprocess.run([CLI, *args], capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 0, done.stderr or done.stdout
    return json.loads(done.stdout)


def protocol_card(tmp_path: Path) -> dict:
    path = tmp_path / "describe.json"
    path.write_text(json.dumps({"operation": "describe", "view": "protocol"}))
    return cli("reason", "--request", str(path))["result"]["example"]


def lifecycle_preparation(tmp_path: Path) -> dict:
    """The documented protocol example with every object adopted and a two-plan comparison."""
    request = protocol_card(tmp_path)
    for item in request["protocol"]["objects"]:
        item["standing"] = {"status": "known", "resolution": "resolved", "basis": ["user:invented adoption"]}
        item["adopted_by"] = dict(ADOPTION)
    extended = copy.deepcopy(request["protocol"]["objects"][2])
    extended.pop("adopted_by")
    extended["support"] = ["adopt:collection:invented-v1"]
    extended["data"]["availability"] = [
        {"lower": None, "upper": "91", "lower_inclusive": False, "upper_inclusive": True}
    ]
    request["protocol"]["decisions"] = [
        {
            "id": "collection-plan",
            "question": "How long should week-12 collection run?",
            "alternatives": [
                {"id": "as-drafted", "label": "Through day 80", "checks": ["week12-schedule"]},
                {
                    "id": "extend",
                    "label": "Through day 91",
                    "replace": [extended],
                    "checks": ["week12-schedule"],
                },
            ],
            "selected": {"alternative": "as-drafted", "origin": "user", "basis": ["user:invented selection"]},
        }
    ]
    return request


def fetch(mcp: McpClient, artifact: str, address: str):
    """Reassemble the value at an address through reason_result, following navigation and continuations."""
    reply = mcp.call("reason_result", id=artifact, part="address", address=address)
    if "value" in reply:
        value = reply["value"]
        text_page = reply.get("text_page")
        while text_page and text_page.get("next_offset") is not None:
            more = mcp.call(
                "reason_result",
                id=artifact,
                part="address",
                address=address,
                text_offset=text_page["next_offset"],
            )
            value += more["value"]
            text_page = more.get("text_page")
        return value
    entries = list(reply["entries"])
    page = reply["page"]
    while page["next_offset"] is not None:
        reply = mcp.call(
            "reason_result", id=artifact, part="address", address=address, offset=page["next_offset"]
        )
        entries += reply["entries"]
        page = reply["page"]
    if all("index" in entry for entry in entries):
        return [fetch(mcp, artifact, entry["address"]) for entry in entries]
    return {entry["key"]: fetch(mcp, artifact, entry["address"]) for entry in entries}


def run_mcp_lifecycle(mcp: McpClient, preparation: dict) -> tuple[str, dict]:
    """Retain a preparation through MCP, then execute it by artifact id; return the executed id and reply."""
    prepared = mcp.call("reason", request=preparation, response_view="compact", retain=True)
    assert prepared["code"] == "complete", prepared
    executed = mcp.call("reason", prepared=prepared["artifact"]["id"], response_view="compact")
    assert executed["code"] == "complete", executed
    return executed["artifact"]["id"], executed


def revised_session(mcp: McpClient, artifact: str) -> dict:
    """The retained session with the collection availability widened to day 91 under a new revision label."""
    session = copy.deepcopy(mcp.call("reason_result", id=artifact, part="session")["value"])
    session["revision"] = "two"
    collection = next(o for o in session["protocol"]["objects"] if o["id"] == "collection")
    collection["data"]["availability"] = [
        {"lower": None, "upper": "91", "lower_inclusive": False, "upper_inclusive": True}
    ]
    # Changed content is a new edition, re-adopted with the instruction (Rohan, 2026-11-04).
    new_edition(session, "collection")
    return session


def sheets(path: str) -> dict:
    workbook = openpyxl.load_workbook(path)
    return {name: list(workbook[name].iter_rows(values_only=True)) for name in workbook.sheetnames}


def test_mcp_prepare_execute_compact_reply_carries_the_protocol_view(mcp, tmp_path):
    """A prepared protocol's compact reply shows eight sections, findings and the plan decision."""
    _, reply = run_mcp_lifecycle(mcp, lifecycle_preparation(tmp_path))
    protocol = reply["protocol"]
    assert [section["id"] for section in protocol["sections"]] == SECTIONS
    assert {s["id"]: s["declared"] for s in protocol["sections"]}["assessments"] == "requested"
    assert [f["class"] for f in protocol["findings"]] == ["repair_choice", "repair_choice"]
    assert {f["claim"] for f in protocol["findings"]} == {"target", "window"}
    decision = protocol["decisions"][0]
    assert decision["id"] == "collection-plan" and decision["disposition"] == "repair_choice"
    assert {a["id"]: a["compatibility"] for a in decision["alternatives"]} == {
        "as-drafted": "repair_choice_open_under_declared_checks",
        "extend": "compatible_under_declared_checks",
    }
    assert protocol["omitted"] == {"findings": 0, "checks": 0}


def test_mcp_reason_result_returns_the_full_canonical_protocol(mcp, tmp_path):
    """reason_result at /response/result/protocol reassembles the protocol the CLI computes in full."""
    preparation = lifecycle_preparation(tmp_path)
    artifact, _ = run_mcp_lifecycle(mcp, preparation)
    canonical = fetch(mcp, artifact, "/response/result/protocol")
    assert list(canonical["sections"]) == sorted(SECTIONS)
    assert [obj["id"] for obj in canonical["objects"]] == ["score", "week12", "collection"]
    claims = canonical["checks"][0]["children"][0]["signals"][0]["claim_admission"]
    assert [row["outcome"] for row in claims] == ["satisfied", "not_collected", "uncovered"]
    assert {row["admission"] for row in claims} == {"accepted"}
    request = tmp_path / "prepare.json"
    request.write_text(json.dumps(preparation))
    prepared = cli("reason", "--request", str(request))["result"]["request"]
    executed = tmp_path / "execute.json"
    executed.write_text(json.dumps(prepared))
    assert cli("reason", "--request", str(executed))["result"]["protocol"] == canonical


def test_mcp_revise_reports_the_protocol_verdict_change_per_claim(mcp, tmp_path):
    """reason_revise of a widened collection returns protocol_checks with a verdict axis."""
    artifact, _ = run_mcp_lifecycle(mcp, lifecycle_preparation(tmp_path))
    revised = mcp.call(
        "reason_revise", id=artifact, session=revised_session(mcp, artifact), response_view="compact"
    )
    assert revised["code"] == "complete", revised
    check = revised["answer_diff"]["protocol_checks"][0]
    assert check["id"] == "week12-schedule" and "verdict" in check["axes"]
    changes = {(c["claim"], c["field"]): (c["before"], c["after"]) for c in check["changes"]}
    assert changes == {
        ("target", "effective_outcome"): ("not_collected", "satisfied"),
        ("window", "effective_outcome"): ("uncovered", "satisfied"),
    }
    assert revised["protocol"]["findings"] == []


def test_mcp_export_publishes_the_protocol_decision_list_and_workbook_sheets(mcp, tmp_path):
    """reason_export of a revised session writes the protocol sections and five protocol sheets."""
    artifact, _ = run_mcp_lifecycle(mcp, lifecycle_preparation(tmp_path))
    revised = mcp.call(
        "reason_revise", id=artifact, session=revised_session(mcp, artifact), response_view="compact"
    )
    exported = mcp.call("reason_export", id=revised["artifact"]["id"])
    assert exported["code"] == "complete", exported
    listing = Path(exported["decision_list"])
    assert listing.parent.name == "review" and listing.name == "decision-list.md"
    text = listing.read_text()
    for heading in ("## Protocol", "### Plan comparisons", "### Adoption"):
        assert heading in text, heading
    assert "| score | invented-v1 | adopted_known |" in text
    workbook = sheets(exported["workbook"])
    for name in SHEETS:
        assert name in workbook, name
    adoption = {row[0]: row[3] for row in workbook["Protocol adoption"][1:]}
    assert adoption == {"score": "adopted_known", "week12": "adopted_known", "collection": "adopted_known"}


def test_cli_and_mcp_compute_the_same_canonical_result_and_decision_list(mcp, tmp_path):
    """CLI and MCP prepare, execute, revise and export agree on digests and the decision list."""
    preparation = lifecycle_preparation(tmp_path)
    mcp_artifact, mcp_reply = run_mcp_lifecycle(mcp, preparation)
    request = tmp_path / "prepare.json"
    request.write_text(json.dumps(preparation))
    store = tmp_path / "cli-store"
    prepared = cli("reason", "--request", str(request), "--store", str(store), "--compact")
    executed = cli("reason", "--prepared", prepared["artifact"]["id"], "--store", str(store), "--compact")
    assert executed["code"] == "complete"
    assert executed["result_digest"] == mcp_reply["result_digest"]
    assert executed["protocol"] == mcp_reply["protocol"]
    assert executed["artifact"]["id"] == mcp_artifact
    session = revised_session(mcp, mcp_artifact)
    session_file = tmp_path / "next-session.json"
    session_file.write_text(json.dumps(session))
    cli_revised = cli(
        "reason-revise",
        "--store",
        str(store),
        "--id",
        executed["artifact"]["id"],
        "--session",
        str(session_file),
    )
    mcp_revised = mcp.call("reason_revise", id=mcp_artifact, session=session, response_view="compact")
    assert cli_revised["result_digest"] == mcp_revised["result_digest"]
    assert cli_revised["answer_diff"]["protocol_checks"] == mcp_revised["answer_diff"]["protocol_checks"]
    out = tmp_path / "cli-export"
    cli("reason-export", "--store", str(store), "--id", cli_revised["artifact"]["id"], "--out", str(out))
    mcp_export = mcp.call("reason_export", id=mcp_revised["artifact"]["id"])
    cli_text = (out / "review" / "decision-list.md").read_bytes()
    mcp_text = Path(mcp_export["decision_list"]).read_bytes()
    assert cli_text == mcp_text


def conflict_request() -> dict:
    return json.loads((FIXTURES / "results/policy-violation-known.json").read_text())["request"]


@pytest.mark.parametrize("budget", [24576, 4096, 2048])
def test_an_admitted_conflict_is_never_silently_missing_from_the_compact_reply(mcp, budget):
    """Every canonical protocol conflict is shown in the compact reply or counted as not yet returned."""
    full = mcp.call("reason", request=conflict_request(), retain=True)
    canonical = fetch(mcp, full["artifact"]["id"], "/response/protocol_view/delivery_findings")
    conflicts = [row for row in canonical if row["class"] == "conflict"]
    assert conflicts, "the fixture must carry an admitted conflict"
    compact = mcp.call("reason", request=conflict_request(), response_view="compact", max_bytes=budget)
    shown = [f for f in compact.get("protocol", {}).get("findings", []) if f["class"] == "conflict"]
    page = compact.get("pages", {}).get("/response/protocol_view/delivery_findings")
    if page is None:
        assert len(shown) == len(conflicts) and compact["protocol"]["omitted"]["findings"] == 0
    else:
        assert page["total"] - page["returned"] >= len(conflicts) and page["next_offset"] is not None
    if shown:
        assert compact["protocol"]["findings"][0]["class"] == "conflict"
    if "protocol" not in compact:
        # The block was dropped for budget: it is named as omitted, with its conflicts still counted.
        assert "protocol" in compact["omitted_fields"]
        assert compact["protocol_omitted"]["conflicts"] >= len(conflicts)
        assert compact["protocol_omitted"]["canonical_ref"] == "/response/protocol_view"


def test_a_proposed_adoption_is_never_reported_as_adopted_known_in_the_export(mcp, tmp_path):
    """A proposed adoption stays adopted_proposed in the workbook and decision list, never adopted_known."""
    preparation = lifecycle_preparation(tmp_path)
    collection = preparation["protocol"]["objects"][2]
    collection["adopted_by"] = {"ref": "user:proposal", "status": "proposed", "resolution": "unresolved"}
    collection["standing"] = {"status": "proposed", "resolution": "unresolved", "basis": ["user:proposal"]}
    artifact, reply = run_mcp_lifecycle(mcp, preparation)
    assert {f["class"] for f in reply["protocol"]["findings"] if f["claim"]} == {"claim_unsettled"}
    exported = mcp.call("reason_export", id=artifact)
    adoption = {row[0]: row[3] for row in sheets(exported["workbook"])["Protocol adoption"][1:]}
    assert adoption["collection"] == "adopted_proposed"
    assert adoption["score"] == adoption["week12"] == "adopted_known"
    text = Path(exported["decision_list"]).read_text()
    assert "| collection | invented-v1 | adopted_proposed |" in text
    assert "| collection | invented-v1 | adopted_known |" not in text
