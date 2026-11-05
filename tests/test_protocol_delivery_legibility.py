"""Legibility amendments (2026-11-04): plain words beside codes, no empty findings, no clipped cells."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
CLI = str(Path(sys.executable).with_name("trialledger"))
RESULTS = ROOT / "openspec/changes/connect-protocol-design-workflow/interface/fixtures/results"
FORBIDDEN = re.compile(r"\b(safe|valid|complete|adequate|approved)\b", re.IGNORECASE)


def _cli(*args: str) -> dict:
    done = subprocess.run([CLI, *args], capture_output=True, text=True, cwd=ROOT)
    return json.loads(done.stdout)


def _export(tmp_path: Path, name: str) -> Path:
    request = json.loads((RESULTS / f"{name}.json").read_text())["request"]
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    store = tmp_path / "store"
    reply = _cli("reason", "--request", str(path), "--store", str(store), "--compact")
    out = tmp_path / "export"
    exported = _cli(
        "reason-export", "--store", str(store), "--id", reply["artifact"]["id"], "--out", str(out)
    )
    assert exported["code"] == "complete", exported
    return out / "review"


def _rows(review: Path, sheet: str) -> list[dict]:
    book = load_workbook(review / "design-review.xlsx")
    rows = list(book[sheet].values)
    return [dict(zip(rows[0], row, strict=False)) for row in rows[1:]]


def test_not_computed_check_has_a_row_and_a_bullet_naming_the_reason(tmp_path):
    review = _export(tmp_path, "schedule-scope-mismatch-unresolved")
    rows = _rows(review, "Protocol findings")
    assert [r["Kind of finding"] for r in rows] == ["Not computed"]
    assert "different scopes" in rows[0]["Wording"] and "projection_scope_mismatch" in rows[0]["Wording"]
    text = (review / "decision-list.md").read_text()
    finding = text.split("Check week12-schedule (schedule, required)")[1].split("###")[0]
    assert "[Not computed]" in finding and "different scopes" in finding


def test_refused_wording_does_not_leak_the_admission_code(tmp_path):
    review = _export(tmp_path, "policy-violation-proposed")
    rows = [r for r in _rows(review, "Protocol findings") if r["Claim"] == "prohibition"]
    assert rows[0]["Wording"] == "Not applied: the deciding premise is still a proposal."
    assert rows[0]["Kind of finding"] == "Not applied" and rows[0]["Admission"] == "proposed_refused"
    assert rows[0]["Effective outcome"] != rows[0]["Outcome"]


def test_conflicts_sort_first_and_synopsis_counts_them(tmp_path):
    review = _export(tmp_path, "policy-violation-known")
    kinds = [r["Kind of finding"] for r in _rows(review, "Protocol findings")]
    assert kinds[0] == "Conflict"
    synopsis = {r["Section"]: r for r in _rows(review, "Protocol synopsis") if r["Section"] != "Legend"}
    assert synopsis["safety"]["Conflicts"] >= 1 and "Conflict" in synopsis["safety"]["Status"]
    assert all("claim_unresolved:" not in str(r["Reasons"]) for r in synopsis.values())


def test_plan_comparison_words_windows_selection_and_withheld_reason(tmp_path):
    review = _export(tmp_path, "decision-plan-comparison")
    rows = {r["Alternative"]: r for r in _rows(review, "Plan comparisons")}
    drafted, extend = rows["as-drafted"], rows["extend"]
    assert drafted["Permitted window"] == "[77, 91] days from randomization"
    assert drafted["Feasible window"] != drafted["Permitted window"]
    assert drafted["Full-coverage gap"] == "(80, 91] days from randomization"
    assert drafted["Selected by you (caller label)"].startswith("Selected (caller-attributed")
    assert "Not applied to the draft" in extend["Application in words"]
    assert "collection" in extend["Application in words"]
    retained = json.loads((RESULTS / "decision-plan-comparison.json").read_text())["result"]
    alt = retained["protocol"]["decisions"][0]["alternatives"][1]
    value = alt["checks"][0]["children"][0]["schedule"][0]
    assert value["available"][0]["upper"] == "91" and value["permitted"][0]["upper"] == "91"
    assert extend["Permitted window"] == "[77, 91] days from randomization"
    assert extend["Collection availability"] == "(-∞, 91] days from randomization"
    assert extend["Feasible window"] == "[77, 91] days from randomization"
    assert extend["Full-coverage gap"] == "none"
    assert not any("Not retained" in str(v) for v in extend.values())
    assert "repair choice" in drafted["Compatibility in words"].lower()


def test_no_plan_comparison_is_stated(tmp_path):
    review = _export(tmp_path, "schedule-refuted-and-conditional")
    assert _rows(review, "Plan comparisons")[0]["Decision"] == "No plan comparison declared"
    assert "No plan comparison declared." in (review / "decision-list.md").read_text()


def test_findings_cells_are_capped_and_open_items_are_worded(tmp_path):
    review = _export(tmp_path, "efficacy-binomial-and-external")
    for row in _rows(review, "Findings"):
        for key in ("Scope and question", "Reported values", "Necessary conditions", "What decides it"):
            assert len(str(row[key])) < 700, key
        assert "Unclassified open item (binding_unresolved" not in str(row["Open items"])


def test_adoption_is_labelled_as_a_caller_label(tmp_path):
    review = _export(tmp_path, "schedule-refuted-and-conditional")
    rows = _rows(review, "Protocol adoption")
    assert "Attributed to (caller label, not authenticated)" in rows[0]
    text = (review / "decision-list.md").read_text()
    assert "Attributed to (caller label, not authenticated)" in text


@pytest.mark.parametrize("name", ["schedule-refuted-and-conditional", "schedule-scope-mismatch-unresolved"])
def test_new_text_has_no_status_words(name, tmp_path):
    review = _export(tmp_path, name)
    book = load_workbook(review / "design-review.xlsx")
    for sheet in ("Protocol synopsis", "Protocol findings", "Plan comparisons", "Protocol adoption"):
        for row in book[sheet].values:
            for value in row:
                for match in FORBIDDEN.finditer(str(value or "")):
                    assert re.search(r"\b(not|no)\s*$", str(value)[: match.start()], re.I), value


def test_smallest_compact_budget_names_the_omitted_protocol_block_and_counts(tmp_path):
    request = json.loads((RESULTS / "policy-violation-known.json").read_text())["request"]
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request))
    reply = _cli(
        "reason",
        "--request",
        str(path),
        "--store",
        str(tmp_path / "store"),
        "--compact",
        "--max-bytes",
        "2048",
    )
    if "protocol" in reply:
        # It fit: the conflict must then be shown or counted as omitted, never silently missing.
        block = reply["protocol"]
        assert any(f["class"] == "conflict" for f in block["findings"]) or block["omitted"]["findings"] >= 1
        return
    assert "protocol" in reply["omitted_fields"]
    assert reply["protocol_omitted"]["conflicts"] >= 1
    assert reply["protocol_omitted"]["canonical_ref"] == "/response/protocol_view"
    assert len(json.dumps(reply, indent=2)) < 2048
