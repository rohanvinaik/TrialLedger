"""The deep gate's pinned-decision list — read from the whole package, subpackages included.

Positive: the list `scripts/ci_local.sh --deep` audits, computed by the script's own embedded Python run from
the repository root, names the pinned decisions of the subpackage `TrialLedger/semantics/` (its loader and its
contracts) beside the top-level modules' ones, each as `path::name`.
Negative: a function whose docstring does not say "(pure — pinned)" is never listed, in a subpackage or at
the top level, and nothing outside `TrialLedger/` is.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPENING = "targets=$(.venv/bin/python - <<'EOF'\n"


def listed() -> list[str]:
    script = (ROOT / "scripts" / "ci_local.sh").read_text(encoding="utf-8")
    start = script.index(OPENING) + len(OPENING)
    code = script[start : script.index("\nEOF\n", start)]
    done = subprocess.run(
        [sys.executable, "-I", "-c", code], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return done.stdout.split()


def test_the_deep_gate_lists_subpackage_decisions():
    targets = listed()
    assert "TrialLedger/semantics/loader.py::registry_problems" in targets
    assert "TrialLedger/semantics/loader.py::registry_flags" in targets
    assert "TrialLedger/semantics/contracts.py::atom_problems" in targets
    assert "TrialLedger/evaluation.py::clustered_lower_bound" in targets
    # a tag after other words in its parentheses, or broken over two lines, is not found: these are whole
    assert "TrialLedger/evaluation.py::agreement_kind" in targets
    assert "TrialLedger/semantics/contracts.py::atom_digest" in targets


def test_the_deep_gate_lists_only_pinned_decisions_of_the_package():
    targets = listed()
    assert "TrialLedger/semantics/loader.py::compile_registry" not in targets  # untagged: a shell
    assert "TrialLedger/semantics/loader.py::load_fragments" not in targets
    assert "TrialLedger/evaluation.py::_single_level" not in targets
    assert all(target.startswith("TrialLedger/") for target in targets)
    assert len(targets) == len(set(targets))
