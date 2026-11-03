"""Replay public examples through CLI/MCP and retain actual call edges, never correctness by coverage.

Run from the project root: .venv/bin/python -m scripts.trace_reasoning_consumers
The receipt contains digests and observed code paths, not private conversation or inferred clinical facts.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

from TrialLedger import cli
from TrialLedger.layer2 import run

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def cases():
    description = run({"operation": "describe", "view": "full"})["result"]
    rows = [("discovery:" + name, request) for name, request in description["examples"].items()]
    rows.extend(("signal:" + name, request) for name, request in description["signal_examples"].items())
    rows.extend(
        ("corpus:" + name, item["request"]) for name, item in description["capability_examples"].items()
    )
    for directory in ("source-bridge", "reasoning-admission", "partial-evidence", "interpretations"):
        for path in sorted((ROOT / "examples" / directory).glob("*-request.json")):
            rows.append((directory + ":" + path.stem, json.loads(path.read_text())))
    return rows


def identity(frame):
    filename = frame.f_code.co_filename
    path = Path(filename)
    if path.is_absolute() and ROOT / "TrialLedger" in path.parents:
        return path.relative_to(ROOT).as_posix() + "::" + frame.f_code.co_qualname
    return None


def invoke(request, mode, folder):
    if mode == "cli":
        path = folder / "request.json"
        path.write_text(json.dumps(request))
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = cli.main(["reason", "--request", str(path)])
        result = json.loads(stream.getvalue())
        assert status == (0 if result["code"] == "complete" else 2)
        return result
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "trace", "version": "1"},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "reason", "arguments": {"request": request}},
        },
    ]
    output = []
    assert (
        cli.main(
            ["mcp", "--root", str(folder / "reports")],
            mcp_streams=([json.dumps(m).encode() for m in messages], output.append),
        )
        == 0
    )
    result = json.loads(json.loads(output[-1])["result"]["content"][0]["text"])
    assert result.pop("tool") == "reason"
    return result


def build():
    receipts = []
    modules = set()
    for name, request in cases():
        reference = json.loads(json.dumps(run(request)))
        assert reference["code"] == "complete", (name, reference)
        original = digest(request)
        for mode in ("cli", "mcp"):
            entries = set()
            edges = set()

            def observe(frame, event, arg, entries=entries, edges=edges):
                if event == "call" and (callee := identity(frame)) is not None:
                    entries.add(callee)
                    modules.add(callee.split("::", 1)[0])
                    if frame.f_back is not None and (caller := identity(frame.f_back)) is not None:
                        edges.add((caller, callee))

            with tempfile.TemporaryDirectory(prefix="trialledger-consumer-trace-") as tmp:
                sys.setprofile(observe)
                try:
                    result = invoke(request, mode, Path(tmp))
                finally:
                    sys.setprofile(None)
            assert result == reference, (name, mode)
            assert digest(request) == original
            receipts.append(
                {
                    "case": name,
                    "mode": mode,
                    "operation": request["operation"],
                    "request_digest": original,
                    "result_digest": digest(result),
                    "entries": sorted(entries),
                    "edges": [list(e) for e in sorted(edges)],
                }
            )
    artifact = {
        "scope": (
            "Executed examples only. Call coverage does not certify clinical source meaning or all paths."
        ),
        "module_hashes": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(modules)},
        "runs": receipts,
    }
    destination = ROOT / "acceptance" / "reasoning-consumer-trace.json"
    destination.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({"runs": len(receipts), "modules": len(modules), "receipt": str(destination)}))


if __name__ == "__main__":
    build()
