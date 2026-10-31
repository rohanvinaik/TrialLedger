#!/usr/bin/env bash
# The local gate. Run it before every commit; any CI must run exactly this script.
set -euo pipefail
cd "$(dirname "$0")/.."

uv sync --locked
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest

# Every decision tagged "(pure — pinned)" must still be complete under the two-sign contract. The list is
# read from the code, not kept here. Detective resolves through the local checkouts while they lead PyPI.
export PYTHONPATH="${DETECTIVE_PYTHONPATH:-$HOME/tools/Detective:$HOME/tools/Wesker}"
targets=$(uv run --no-sync python - <<'EOF'
import ast
import pathlib

for path in sorted(pathlib.Path("TrialLedger").glob("*.py")):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef) and "(pure — pinned)" in (ast.get_docstring(node) or ""):
            print(f"{path}::{node.name}")
EOF
)
for target in $targets; do
    uv run --no-sync detective audit "$target" --two-sign --check
done
