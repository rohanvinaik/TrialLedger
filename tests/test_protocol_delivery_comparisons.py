"""Plan comparisons and protocol revision rows reach the readable outputs (delivery.md; tests-out gap 6)."""

import copy
import json
import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook

from tests.test_protocol_session_replay import new_edition

ROOT = Path(__file__).resolve().parents[1]
CLI = str(Path(sys.executable).with_name("trialledger"))
FIXTURE = ROOT / (
    "openspec/changes/connect-protocol-design-workflow/interface/fixtures/results/decision-plan-comparison.json"
)


def _cli(*args: str) -> dict:
    done = subprocess.run([CLI, *args], capture_output=True, text=True, cwd=ROOT)
    return json.loads(done.stdout)


def _store(tmp_path: Path, request: dict, name: str) -> str:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(request))
    return _cli("reason", "--request", str(path), "--store", str(tmp_path / "store"), "--compact")[
        "artifact"
    ]["id"]


def _export(tmp_path: Path, artifact: str, name: str) -> Path:
    reply = _cli(
        "reason-export", "--store", str(tmp_path / "store"), "--id", artifact, "--out", str(tmp_path / name)
    )
    assert reply["code"] == "complete", reply
    return tmp_path / name / "review"


def test_a_plan_comparison_reaches_the_compact_reply_decision_list_and_workbook(tmp_path):
    request = json.loads(FIXTURE.read_text())["request"]
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    compact = _cli("reason", "--request", str(path), "--store", str(tmp_path / "store"), "--compact")
    decision = compact["protocol"]["decisions"][0]
    assert decision["disposition"] == "repair_choice"
    assert {a["id"]: a["compatibility"] for a in decision["alternatives"]} == {
        "as-drafted": "repair_choice_open_under_declared_checks",
        "extend": "compatible_under_declared_checks",
    }
    review = _export(tmp_path, compact["artifact"]["id"], "export")
    markdown = (review / "decision-list.md").read_text()
    assert "### Plan comparisons" in markdown
    assert "Disposition: repair_choice" in markdown
    assert (
        "| extend | Collect through day 91 (caller wording) | hypothetical | compatible_under_declared_checks"
        in markdown
    )
    sheet = load_workbook(review / "design-review.xlsx")["Plan comparisons"]
    rows = [[cell.value for cell in row] for row in sheet.iter_rows(min_row=2)]
    assert {row[3]: row[6] for row in rows} == {
        "as-drafted": "repair_choice_open_under_declared_checks",
        "extend": "compatible_under_declared_checks",
    }
    assert all(row[2] == "repair_choice" for row in rows)


def test_a_protocol_revision_appears_in_the_changes_section_and_sheet(tmp_path):
    first = json.loads(FIXTURE.read_text())["request"]
    first_id = _store(tmp_path, first, "first")
    nxt = copy.deepcopy(first["session"])
    nxt["revision"] = "two"
    nxt["protocol"]["objects"][2]["data"]["availability"][0]["upper"] = "91"
    # Changed content is a new edition, re-adopted with the instruction (Rohan, 2026-11-04).
    new_edition(nxt, nxt["protocol"]["objects"][2]["id"])
    session_path = tmp_path / "next.json"
    session_path.write_text(json.dumps(nxt))
    revised = _cli(
        "reason-revise", "--store", str(tmp_path / "store"), "--id", first_id, "--session", str(session_path)
    )
    assert revised["code"] == "complete", revised
    review = _export(tmp_path, revised["artifact"]["id"], "export-two")
    markdown = (review / "decision-list.md").read_text()
    assert "protocol checks week12-schedule: " in markdown
    assert "(verdict" in markdown.split("protocol checks week12-schedule: ")[1].splitlines()[0]
    sheet = load_workbook(review / "design-review.xlsx")["Changes"]
    protocol_rows = [
        [c.value for c in row] for row in sheet.iter_rows(min_row=2) if row[0].value == "protocol checks"
    ]
    assert protocol_rows and protocol_rows[0][3] == "changed"
