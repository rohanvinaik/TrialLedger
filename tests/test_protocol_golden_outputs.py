"""Golden outputs for the protocol workflow (behaviour-preserving cleanup guard).

For every frozen protocol result fixture, and each `describe view protocol detail full` example (prepared,
then run), capture through the public CLI: the canonical `result.protocol`, the compact reply's `protocol`
block, `decision-list.md`, and a cell dump of every protocol workbook sheet from `reason-export`. The files
under `tests/golden/protocol/` were captured from the code before the cleanup refactor; a refactor must keep
them byte-identical. Regenerate deliberately with `TRIALLEDGER_UPDATE_GOLDENS=1` only when behaviour is meant
to change.
"""

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest
from openpyxl import load_workbook

from TrialLedger.layer2 import run

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / ".venv" / "bin" / "trialledger"
RESULTS = (
    REPO / "openspec" / "changes" / "connect-protocol-design-workflow" / "interface" / "fixtures" / "results"
)
GOLDEN = Path(__file__).resolve().parent / "golden" / "protocol"
PROTOCOL_SHEETS = (
    "Protocol synopsis",
    "Protocol findings",
    "Schedule of assessments",
    "Plan comparisons",
    "Protocol adoption",
)
FIXTURES = sorted(path.stem for path in RESULTS.glob("*.json"))
FAMILIES = sorted(run({"operation": "describe", "view": "protocol", "detail": "full"})["result"]["examples"])
CASES = [("fixture", name) for name in FIXTURES] + [("example", name) for name in FAMILIES]


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def request_for(kind: str, name: str) -> dict:
    if kind == "fixture":
        return json.loads((RESULTS / f"{name}.json").read_text())["request"]
    examples = run({"operation": "describe", "view": "protocol", "detail": "full"})["result"]["examples"]
    prepared = run(copy.deepcopy(examples[name]))
    assert prepared["code"] == "complete", prepared["problems"]
    return prepared["result"]["request"]


def cli(*args: str) -> str:
    proc = subprocess.run([str(CLI), *args], capture_output=True, text=True, cwd=REPO, check=False)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return proc.stdout


def sheet_dump(workbook_path: Path) -> str:
    book = load_workbook(workbook_path)
    lines: list[str] = []
    for name in PROTOCOL_SHEETS:
        if name not in book.sheetnames:
            lines.append(f"## {name}: absent")
            continue
        lines.append(f"## {name}")
        for row in book[name].iter_rows():
            for cell in row:
                if cell.value is not None:
                    lines.append(f"{cell.coordinate}\t{json.dumps(cell.value, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def generate(kind: str, name: str, work: Path) -> dict[str, str]:
    request_file = work / "request.json"
    request_file.write_text(json.dumps(request_for(kind, name)))
    store = work / "store"
    compact = json.loads(cli("reason", "--request", str(request_file), "--store", str(store), "--compact"))
    artifact_id = compact["artifact"]["id"]
    out = work / "export"
    cli("reason-export", "--store", str(store), "--id", artifact_id, "--out", str(out))
    review = out / "review"
    files = {
        "compact_protocol.json": canonical(compact.get("protocol")),
        "decision-list.md": (review / "decision-list.md").read_text(encoding="utf-8"),
        "workbook_protocol_sheets.txt": sheet_dump(review / "design-review.xlsx"),
    }
    exported = json.loads((review / "artifacts" / f"{artifact_id}.json").read_text(encoding="utf-8"))
    files["result_protocol.json"] = canonical(exported["response"]["result"].get("protocol"))
    return files


@pytest.mark.parametrize(("kind", "name"), CASES, ids=[f"{k}-{n}" for k, n in CASES])
def test_protocol_outputs_match_the_captured_goldens(kind, name, tmp_path):
    produced = generate(kind, name, tmp_path)
    folder = GOLDEN / f"{kind}-{name}"
    if os.environ.get("TRIALLEDGER_UPDATE_GOLDENS"):
        folder.mkdir(parents=True, exist_ok=True)
        for filename, text in produced.items():
            (folder / filename).write_text(text, encoding="utf-8")
    assert folder.is_dir(), f"no goldens for {kind}-{name}; capture them from the unchanged code"
    for filename, text in produced.items():
        assert (folder / filename).read_text(encoding="utf-8") == text, f"{kind}-{name}/{filename} changed"
