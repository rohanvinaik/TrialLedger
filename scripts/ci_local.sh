#!/usr/bin/env bash
# The declared gate, in two depths (process contract §6 and §9: a fast correctness gate for the common change
# cycle, the deeper mutation read on its own schedule, never hiding a deep failure behind a fast pass).
#
#   scripts/ci_local.sh          the fast gate, seconds: the locked environment, ruff, ruff format, pytest, ty.
#                                Run it before every commit; the pre-push hook (.githooks/pre-push →
#                                scripts/push_checks.py) runs it before every push of a tree it has not passed.
#   scripts/ci_local.sh --deep   the fast gate, then `detective audit --two-sign --check` on every decision
#                                tagged "(pure — pinned)" and the vulture island scans. Minutes. Run it after
#                                converging new decisions, before an archive, or when a pinned decision's
#                                tests change. A new decision is converged at write time, so the deep read
#                                re-certifies; it does not stand in for that converge.
#
# Detective and Wesker run from the founder's local checkouts, which lead their releases (his instruction,
# 2026-10-31, paraphrased: use the local checkouts, which he keeps improving); the deep gate refuses to audit
# with any other copy.
set -u
cd "$(dirname "$0")/.."
fail=0
deep=0
[ "${1:-}" = "--deep" ] && deep=1

# The tree this run checks, read before any step; stamped at the end if the gate passed and the tree did not
# change meanwhile, so a push of exactly this tree need not run the gate again.
gate_tree="$(.venv/bin/python scripts/push_checks.py tree 2>/dev/null || true)"

echo "== the locked environment"
uv sync --locked || fail=1

echo "== ruff check"
.venv/bin/ruff check . || fail=1

echo "== ruff format --check"
.venv/bin/ruff format --check . || fail=1

echo "== pytest (live calls deselected; uv run pytest -m live runs them)"
.venv/bin/pytest || fail=1

echo "== ty (advisory)"
uvx ty check --python .venv TrialLedger || echo "ty: the findings above are leads, not a gate"

if [ "$deep" -eq 1 ]; then
    DETECTIVE_ROOT="${DETECTIVE_ROOT:-$HOME/tools/Detective}"
    WESKER_ROOT="${WESKER_ROOT:-$HOME/tools/Wesker}"
    echo "== Detective and Wesker, as the deep gate imports them"
    for checkout in "$DETECTIVE_ROOT" "$WESKER_ROOT"; do
        if [ -d "$checkout" ]; then
            echo "$checkout at $(git -C "$checkout" log -1 --format='%h %cd' --date=short)"
        else
            echo "missing local checkout $checkout"
            fail=1
        fi
    done
    export PYTHONPATH="$DETECTIVE_ROOT:$WESKER_ROOT"
    if ! .venv/bin/python - "$DETECTIVE_ROOT" "$WESKER_ROOT" <<'EOF'
import sys
from pathlib import Path

import Detective
import Wesker

wanted = {"Detective": Path(sys.argv[1]).resolve(), "Wesker": Path(sys.argv[2]).resolve()}
ok = True
for name, module in (("Detective", Detective), ("Wesker", Wesker)):
    where = Path(module.__file__).resolve()
    inside = wanted[name] in where.parents
    print(f"{name} imported from {where}" + ("" if inside else f"  NOT the checkout {wanted[name]}"))
    ok = ok and inside
sys.exit(0 if ok else 1)
EOF
    then
        echo "the deep gate imports Detective or Wesker from somewhere other than the local checkouts"
        fail=1
    fi

    # Every decision tagged "(pure — pinned)" must still be complete under the two-sign contract. The list is
    # read from the code, not kept here.
    echo "== Detective: audit --two-sign --check on every pinned decision"
    targets=$(.venv/bin/python - <<'EOF'
import ast
import pathlib

for path in sorted(pathlib.Path("TrialLedger").glob("**/*.py")):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.FunctionDef) and "(pure — pinned)" in (ast.get_docstring(node) or ""):
            print(f"{path}::{node.name}")
EOF
)
    count=0
    for target in $targets; do
        count=$((count + 1))
        .venv/bin/detective audit "$target" --two-sign --check || { echo "AUDIT FAILED: $target"; fail=1; }
    done
    echo "audited $count pinned decisions"
    if [ "$count" -eq 0 ]; then
        echo "no pinned decisions found: an audit of nothing is not a pass"
        fail=1
    fi

    # Islands: code that computes but has no caller. Two scans, because they answer different questions.
    echo "== vulture (advisory) 1/2: nothing in production calls it (test-only code shows here)"
    .venv/bin/vulture TrialLedger scripts || echo "vulture: a name used only by a test is an island"
    echo "== vulture (advisory) 2/2: nothing anywhere calls it, tests included"
    .venv/bin/vulture TrialLedger scripts tests || echo "vulture: each line above is an island or dead code"
fi

if [ "$fail" -ne 0 ]; then
    echo "GATE: FAILED"
    exit 1
fi
.venv/bin/python scripts/push_checks.py stamp "$gate_tree" || echo "push gate: this run's tree was not stamped"
echo "GATE: PASSED$([ "$deep" -eq 1 ] && echo ' (deep)')"
