"""Independent census-scope orchestration regressions; no claim of mutation adequacy.

Real miniature Git archives supply identities and incremental history. Coverage and mutation outcomes are
explicit test doubles: these tests establish preservation/scheduling/reporting, not whether any real
mutant is caught. A partial sample must not turn complete merely because its missing records disappeared.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import quality_metrics as qm
from tests.test_quality_metrics import git, metrics, tiny_repository

COVERED = {
    "tests_passed": 3,
    "tests_deselected": 0,
    "statements": 7,
    "line_coverage": 100.0,
    "branches": 2,
    "branch_coverage": 100.0,
}


class SerialPool:
    """Run the orchestration's job partition deterministically without spawning mutation workers."""

    def __init__(self, max_workers):
        self.max_workers = max_workers

    def __enter__(self):
        return self

    def __exit__(self, *errors):
        return False

    def map(self, function, jobs):
        return map(function, jobs)


def repository(tmp_path):
    repo = tiny_repository(tmp_path)
    (repo / "TrialLedger/__init__.py").write_text(
        'def pinned_decision(x):\n    """Fixture decision (pure — pinned)."""\n'
        "    return x > 1\n"
        "def alpha():\n    return True\n"
        "def omega():\n    return False\n"
    )
    (repo / "tests/test_x.py").write_text(
        "from TrialLedger import pinned_decision, alpha, omega\n"
        "def test_declared_fixture():\n"
        "    assert pinned_decision(2) and alpha() and not omega()\n"
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Three explicit census fixture targets")
    return repo


def identity(row):
    return row["file"], row["name"], row["digest"]


def record(target):
    return {
        **target,
        "baseline": "passing",
        "selected_by": "name",
        "test_files": ["tests/test_x.py"],
        "outcomes": [{"line": 1, "kind": "bool", "outcome": "killed"}],
    }


def install_doubles(monkeypatch, repo, skipped=()):
    scheduled = []
    skip_names = set(skipped)

    def census(job):
        root, targets, _deadline = job
        scheduled.extend(targets)
        return [
            {**target, "skipped": True}
            if target["name"] in skip_names
            else {**record(target), "input_digest": qm.mutation_inputs_digest(Path(root))}
            for target in targets
        ]

    monkeypatch.chdir(repo)
    monkeypatch.setattr(qm, "coverage", lambda _root: dict(COVERED))
    monkeypatch.setattr(qm, "census", census)
    monkeypatch.setattr(qm, "ProcessPoolExecutor", SerialPool)
    return scheduled, skip_names


def execute(site: Path, *arguments):
    assert qm.main(["--workers", "1", "--unpinned-sample", "2", "--out", str(site), *arguments]) == 0
    return json.loads((site / "metrics.json").read_text())


def baseline(repo: Path, *, include_pending: bool = True):
    targets = qm.functions(repo)
    complete = [record(target) for target in targets if target["name"] != "omega"]
    commit = git(repo, "rev-parse", "HEAD")
    source = {
        **metrics(100.0),
        "commit": commit,
        "mutation_commit": commit,
        "mutation_measured": "2026-11-02",
        "functions_stale": 0,
        "functions_not_yet_measured": 1,
        "mutation_pinned": qm.tally([row for row in complete if row["pinned"]]),
        "mutation_unpinned_sample": {
            **qm.tally([row for row in complete if not row["pinned"]]),
            "seed": 20261102,
        },
        "records": complete,
    }
    if include_pending:
        source["pending_targets"] = [target for target in targets if target["name"] == "omega"]
    return source


@pytest.mark.parametrize("stop", ["limit", "deadline"])
def test_unfinished_unpinned_identities_survive_a_stop_and_are_actually_retried(stop, tmp_path, monkeypatch):
    repo = repository(tmp_path)
    scheduled, skipped = install_doubles(monkeypatch, repo, {"omega"} if stop == "deadline" else ())
    all_targets = {identity(row) for row in qm.functions(repo)}
    options = ["--limit", "1"] if stop == "limit" else ["--budget-minutes", "1"]
    first = execute(tmp_path / "first", *options)
    measured = {identity(row) for row in first["records"]}
    expected_pending = all_targets - measured
    assert expected_pending
    pending = first.get("pending_targets", [])
    assert {identity(row) for row in pending} == expected_pending
    assert any(not row["pinned"] for row in pending)
    assert first["functions_not_yet_measured"] == len(expected_pending)
    assert first["mutation_basis"]["status"] in {"partial", "unmeasured"}

    skipped.clear()
    scheduled.clear()
    second = execute(tmp_path / "second", "--incremental", str(tmp_path / "first/metrics.json"))
    assert expected_pending <= {identity(row) for row in scheduled}
    assert {identity(row) for row in second["records"]} == all_targets
    assert second["pending_targets"] == []
    assert second["functions_not_yet_measured"] == 0
    assert second["mutation_basis"]["status"] == "measured"


def test_legacy_anonymous_partial_scope_cannot_become_measured_with_zero_work(tmp_path, monkeypatch):
    repo = repository(tmp_path)
    scheduled, _ = install_doubles(monkeypatch, repo)
    source = baseline(repo, include_pending=False)
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(source))
    result = execute(tmp_path / "site", "--incremental", str(path))
    if result["mutation_basis"]["status"] == "measured":
        assert any(row["name"] == "omega" for row in scheduled), result
        assert any(row["name"] == "omega" for row in result["records"]), result
    else:
        assert result["functions_not_yet_measured"] >= 1, result
        badge = json.loads((tmp_path / "site/badges/mutation.json").read_text())
        assert badge["color"] == "lightgrey"


def test_coverage_only_keeps_pending_identities_and_original_census_date_for_replay(tmp_path, monkeypatch):
    repo = repository(tmp_path)
    scheduled, _ = install_doubles(monkeypatch, repo)
    source = baseline(repo)
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(source))
    with (repo / "tests/test_x.py").open("a") as stream:
        stream.write("\n# New coverage snapshot, no new clinical or mutation claim.\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Coverage publication fixture revision")

    early = execute(tmp_path / "early", "--coverage-only", "--incremental", str(path))
    assert not scheduled, "coverage publication must never run or refresh the census"
    assert early["pending_targets"] == source["pending_targets"]
    assert early["functions_not_yet_measured"] == 1
    assert early["mutation_commit"] == source["mutation_commit"]
    assert early["mutation_measured"] == "2026-11-02"
    assert early["mutation_basis"]["status"] == "historical"
    assert early["records"] == source["records"]

    replayed = execute(tmp_path / "replayed", "--incremental", str(tmp_path / "early/metrics.json"))
    assert any(row["name"] == "omega" for row in scheduled)
    assert replayed["pending_targets"] == []
    assert replayed["mutation_basis"]["status"] == "measured"


def test_a_completed_declared_sample_is_measured_and_reuses_without_inventing_pending_work(
    tmp_path, monkeypatch
):
    repo = repository(tmp_path)
    scheduled, _ = install_doubles(monkeypatch, repo)
    first = execute(tmp_path / "first")
    assert {row["name"] for row in scheduled} == {"pinned_decision", "alpha", "omega"}
    assert first.get("pending_targets", []) == []
    assert first["mutation_basis"]["status"] == "measured"
    assert first["functions_not_yet_measured"] == 0

    scheduled.clear()
    second = execute(tmp_path / "second", "--incremental", str(tmp_path / "first/metrics.json"))
    assert not scheduled
    assert second.get("pending_targets", []) == []
    assert second["records"] == first["records"]
    assert second["mutation_basis"]["status"] == "measured"
