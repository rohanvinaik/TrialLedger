"""The real archived console script must use the declared archived entry point, even outside its root."""

import json
import subprocess
import sys

from scripts import quality_metrics as qm
from tests.test_quality_metrics import git, tiny_repository


def test_archived_cli_runs_archived_code_after_the_live_source_changes(tmp_path):
    repo = tiny_repository(tmp_path)
    with (repo / "pyproject.toml").open("a") as stream:
        stream.write('\n[project.scripts]\ntrialledger="TrialLedger.console:main"\n')
    module = repo / "TrialLedger/console.py"
    module.write_text('def main():\n    print("archived entry point")\n')
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Declare the snapshot console entry point")
    snapshot = tmp_path / "snapshot"
    qm.archive(repo, "HEAD", snapshot)
    module.write_text('def main():\n    print("WRONG live entry point")\n')
    done = subprocess.run(
        [str(snapshot / ".venv/bin/trialledger")],
        cwd=tmp_path,
        env=qm.copy_env(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    assert done.stdout == "archived entry point\n"
    qm.check_isolated(snapshot)


def test_archive_does_not_invent_a_cli_when_the_snapshot_declares_none(tmp_path):
    repo = tiny_repository(tmp_path)
    snapshot = tmp_path / "snapshot"
    qm.archive(repo, "HEAD", snapshot)
    assert not (snapshot / ".venv/bin/trialledger").exists()


def test_coverage_counts_skips_and_deselections_independently_of_passing_tests(tmp_path, monkeypatch):
    def completed(argv, root, **kwargs):
        assert argv[:3] == [sys.executable, "-m", "pytest"]
        (root / "coverage.json").write_text(
            json.dumps(
                {
                    "totals": {
                        "num_statements": 2,
                        "covered_lines": 2,
                        "num_branches": 2,
                        "covered_branches": 1,
                    }
                }
            )
        )
        return subprocess.CompletedProcess(argv, 0, "=== 17 passed, 4 skipped, 10 deselected in 1s ===\n", "")

    monkeypatch.setattr(qm, "run", completed)
    report = qm.coverage(tmp_path)
    assert report["tests_passed"] == 17
    assert report["tests_skipped"] == 4
    assert report["tests_deselected"] == 10
    assert report["line_coverage"] == 100.0 and report["branch_coverage"] == 50.0
