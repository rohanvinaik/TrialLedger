"""Reporting must load without the clinical interpretation engines, in a fresh interpreter."""

import subprocess
import sys
from pathlib import Path


def test_public_reporting_entry_modules_do_not_import_interpretation_engines():
    program = """
import importlib.abc
import sys

forbidden = (
    "TrialLedger.layer2",
    "TrialLedger.reading", "TrialLedger.coherence", "TrialLedger.universes",
    "TrialLedger.indications", "TrialLedger.assertion_compiler", "TrialLedger.banks",
)
class RefuseInterpretation(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
            raise AssertionError("Reporting imported interpretation engine: " + fullname)
sys.meta_path.insert(0, RefuseInterpretation())
from TrialLedger import landscape, operate, readout, cli, mcp_server
assert not any(name in sys.modules for name in forbidden)
print("reporting_import_boundary_preserved")
"""
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=Path(__file__).parents[1],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "reporting_import_boundary_preserved"
