"""Independent current-build mutation-basis contract, not a claim of mutation adequacy.

Real tiny Git archives supply inputs, identities and history. Test doubles provide declared coverage and
mutation results only to inspect scheduling, applicability and publication; no real kill-rate is certified.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import quality_metrics as qm
from tests.test_quality_metrics import git, metrics, tiny_repository
from tests.test_quality_pending_scope import COVERED, SerialPool

README = "# Fixture\n\nExplanatory prose.\n\n```bash\ntrialledger doctor\n```\n"


def repository(tmp_path):
    repo = tiny_repository(tmp_path)
    files = {
        "README.md": README,
        "TrialLedger/helper.py": "THRESHOLD = 1\n",
        "tests/fixtures/profile.json": '{"age":18}\n',
        "tests/golden/answer.txt": "Required by declared criteria.\n",
        "uv.lock": "version = 1\nrevision = 1\n",
        ".python-version": "3.12\n",
        "scripts/quality_metrics.py": '"""Invented measurement engine input."""\nVERSION = 1\n',
        ".github/workflows/quality.yml": "name: Invented fixture quality\njobs: {}\n",
    }
    for relative, text in files.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Explicit measurement inputs fixture")
    return repo


def record(target, input_digest=None):
    row = {
        **target,
        "baseline": "passing",
        "selected_by": "name",
        "test_files": ["tests/test_x.py"],
        "outcomes": [{"line": 3, "kind": "compare", "outcome": "killed"}],
    }
    if input_digest is not None:
        row["input_digest"] = input_digest
    return row


def inputs(repo):
    return qm.mutation_inputs_digest(repo)


def complete_baseline(repo):
    commit = git(repo, "rev-parse", "HEAD")
    digest = inputs(repo)
    records = [record(target, digest) for target in qm.functions(repo)]
    return {
        **metrics(100.0),
        "commit": commit,
        "mutation_commit": commit,
        "mutation_measured": "2026-11-02",
        "mutation_applies_to": commit,
        "scope_complete": True,
        "functions_stale": 0,
        "functions_not_yet_measured": 0,
        "unidentified_pending_targets": 0,
        "pending_targets": [],
        "records": records,
        "mutation_pinned": qm.tally(records),
        "mutation_unpinned_sample": {**qm.tally([]), "seed": 20261102},
    }


def doubles(monkeypatch, repo):
    scheduled, covered = [], []

    def census(job):
        root, targets, _deadline = job
        scheduled.extend(targets)
        return [record(target, inputs(Path(root))) for target in targets]

    def coverage(root):
        covered.append(root)
        return dict(COVERED)

    monkeypatch.chdir(repo)
    monkeypatch.setattr(qm, "coverage", coverage)
    monkeypatch.setattr(qm, "census", census)
    monkeypatch.setattr(qm, "ProcessPoolExecutor", SerialPool)
    return scheduled, covered


def execute(site, baseline, *arguments):
    path = site.parent / (site.name + "-baseline.json")
    path.write_text(json.dumps(baseline))
    assert qm.main(["--workers", "1", "--incremental", str(path), "--out", str(site), *arguments]) == 0
    return json.loads((site / "metrics.json").read_text())


def commit(repo, message="Measurement fixture revision"):
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def test_input_digest_is_deterministic_across_checkout_locations_and_file_mtimes(tmp_path):
    repo = repository(tmp_path)
    before = inputs(repo)
    clone = tmp_path / "elsewhere"
    shutil.copytree(repo, clone)
    (clone / "TrialLedger/helper.py").touch()
    assert inputs(repo) == before == inputs(clone)


@pytest.mark.parametrize(
    "relative",
    [
        "TrialLedger/helper.py",
        "TrialLedger/__init__.py",
        "tests/test_x.py",
        "tests/fixtures/profile.json",
        "tests/golden/answer.txt",
        "uv.lock",
        "pyproject.toml",
        ".python-version",
        "scripts/quality_metrics.py",
        ".github/workflows/quality.yml",
    ],
)
def test_every_declared_behavior_test_and_environment_input_changes_the_digest(relative, tmp_path):
    repo = repository(tmp_path)
    before = inputs(repo)
    path = repo / relative
    changes = {
        "TrialLedger/helper.py": ("THRESHOLD = 1", "THRESHOLD = 2"),
        "TrialLedger/__init__.py": ("x > 1", "x > 2"),
        "tests/test_x.py": ("f(2)", "f(3)"),
        "tests/fixtures/profile.json": ('"age":18', '"age":19'),
        "tests/golden/answer.txt": ("Required", "Allowed"),
        "uv.lock": ("revision = 1", "revision = 2"),
        "pyproject.toml": ("dependencies=[]", 'dependencies=["invented-helper>=1"]'),
        ".python-version": ("3.12", "3.13"),
        "scripts/quality_metrics.py": ("VERSION = 1", "VERSION = 2"),
        ".github/workflows/quality.yml": ("Invented fixture quality", "Changed fixture quality"),
    }
    previous, changed = changes[relative]
    original = path.read_text()
    assert previous in original
    path.write_text(original.replace(previous, changed))
    assert inputs(repo) != before


def test_readme_prose_and_heading_edits_do_not_invalidate_executable_evidence(tmp_path):
    repo = repository(tmp_path)
    before = inputs(repo)
    (repo / "README.md").write_text(
        README.replace("# Fixture", "# Better heading").replace(
            "Explanatory prose.", "Clearer explanatory prose."
        )
    )
    assert inputs(repo) == before


@pytest.mark.parametrize(
    "language,first,second",
    [
        ("bash", "trialledger doctor", "trialledger record report"),
        ("python", "print(1)", "print(2)"),
        ("json", '{"operation":"describe"}', '{"operation":"prepare"}'),
    ],
)
def test_changed_readme_executable_fences_invalidate_the_measurement_basis(language, first, second, tmp_path):
    repo = repository(tmp_path)
    path = repo / "README.md"
    path.write_text(f"# Fixture\n\n```{language}\n{first}\n```\n")
    before = inputs(repo)
    path.write_text(f"# Fixture\n\n```{language}\n{second}\n```\n")
    assert inputs(repo) != before


def test_actual_census_records_keep_the_pristine_full_input_digest(tmp_path, monkeypatch):
    repo = repository(tmp_path)
    before = inputs(repo)
    target = next(row for row in qm.functions(repo) if row["pinned"])
    monkeypatch.setattr(qm, "pytest", lambda *_args, **_kw: subprocess.CompletedProcess(["pytest"], 0))
    records = qm.census((str(repo), [target], 0.0))
    assert records[0]["input_digest"] == before
    assert inputs(repo) == before, "mutant source must be restored before measuring its applicability"


@pytest.mark.parametrize("record_digest", [None, "different-input-digest"])
def test_legacy_or_mismatched_records_are_remeasured_even_with_unchanged_function_and_named_tests(
    record_digest, tmp_path, monkeypatch
):
    repo = repository(tmp_path)
    baseline = complete_baseline(repo)
    for row in baseline["records"]:
        if record_digest is None:
            row.pop("input_digest")
        else:
            row["input_digest"] = record_digest
    scheduled, _ = doubles(monkeypatch, repo)
    result = execute(tmp_path / "site", baseline)
    assert {row["name"] for row in scheduled} == {row["name"] for row in baseline["records"]}
    assert all(row["input_digest"] == inputs(repo) for row in result["records"])


def test_unselected_helper_change_forces_remeasurement_of_an_unchanged_decision(tmp_path, monkeypatch):
    repo = repository(tmp_path)
    baseline = complete_baseline(repo)
    old_target = next(row for row in qm.functions(repo) if row["pinned"])
    (repo / "TrialLedger/helper.py").write_text("THRESHOLD = 2\n")
    commit(repo)
    assert next(row for row in qm.functions(repo) if row["pinned"])["digest"] == old_target["digest"]
    scheduled, _ = doubles(monkeypatch, repo)
    result = execute(tmp_path / "site", baseline)
    assert any(row["name"] == old_target["name"] for row in scheduled)
    assert result["records"][0]["input_digest"] == inputs(repo)


def test_coverage_only_verifies_presentation_carry_without_redating_or_recommitting_the_measurement(
    tmp_path, monkeypatch
):
    repo = repository(tmp_path)
    baseline = complete_baseline(repo)
    (repo / "README.md").write_text(README.replace("Explanatory prose.", "More useful explanatory prose."))
    current = commit(repo, "Presentation-only fixture change")
    scheduled, covered = doubles(monkeypatch, repo)
    result = execute(tmp_path / "site", baseline, "--coverage-only")
    assert covered and not scheduled
    assert result["mutation_applies_to"] == current
    assert result["scope_complete"] is True
    assert result["mutation_commit"] == baseline["mutation_commit"]
    assert result["mutation_measured"] == "2026-11-02"
    assert result["records"] == baseline["records"]


@pytest.mark.parametrize(
    "defect",
    [
        "legacy_input",
        "wrong_input",
        "wrong_function_digest",
        "missing_record",
        "extra_record",
        "stale_record",
        "stale_count",
        "pending",
        "anonymous",
        "scope_incomplete",
    ],
)
def test_coverage_only_never_promotes_unverified_or_incomplete_prior_scope(defect, tmp_path, monkeypatch):
    repo = repository(tmp_path)
    baseline = complete_baseline(repo)
    if defect == "legacy_input":
        baseline["records"][0].pop("input_digest")
    elif defect == "wrong_input":
        baseline["records"][0]["input_digest"] = "wrong"
    elif defect == "wrong_function_digest":
        baseline["records"][0]["digest"] = "wrong"
    elif defect == "missing_record":
        baseline["records"] = []
    elif defect == "extra_record":
        baseline["records"].append({**baseline["records"][0], "name": "not_a_current_function"})
    elif defect == "stale_record":
        baseline["records"][0]["stale"] = True
    elif defect == "stale_count":
        baseline["functions_stale"] = 1
    elif defect == "pending":
        baseline["pending_targets"] = [qm.functions(repo)[0]]
        baseline["functions_not_yet_measured"] = 1
    elif defect == "anonymous":
        baseline["unidentified_pending_targets"] = 1
        baseline["functions_not_yet_measured"] = 1
    elif defect == "scope_incomplete":
        baseline["scope_complete"] = False
    (repo / "README.md").write_text(README + "\nAnother prose sentence.\n")
    current = commit(repo)
    scheduled, _ = doubles(monkeypatch, repo)
    result = execute(tmp_path / "site", baseline, "--coverage-only")
    assert not scheduled
    assert result.get("mutation_applies_to") != current


@pytest.mark.parametrize("changed", ["helper", "dependency", "readme_example"])
def test_coverage_only_cannot_promote_code_dependency_or_executable_example_changes(
    changed, tmp_path, monkeypatch
):
    repo = repository(tmp_path)
    baseline = complete_baseline(repo)
    if changed == "helper":
        (repo / "TrialLedger/helper.py").write_text("THRESHOLD = 2\n")
    elif changed == "dependency":
        path = repo / "pyproject.toml"
        path.write_text(path.read_text().replace("dependencies=[]", 'dependencies=["invented-helper>=1"]'))
    else:
        (repo / "README.md").write_text(README.replace("trialledger doctor", "trialledger record report"))
    current = commit(repo)
    scheduled, _ = doubles(monkeypatch, repo)
    result = execute(tmp_path / "site", baseline, "--coverage-only")
    assert not scheduled
    assert result.get("mutation_applies_to") != current
    assert result["mutation_commit"] == baseline["mutation_commit"]
    assert result["mutation_measured"] == baseline["mutation_measured"]


def test_count_only_produces_no_applicability_receipt_and_never_runs_measurement(tmp_path, monkeypatch):
    repo = repository(tmp_path)
    baseline = complete_baseline(repo)
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(baseline))
    original = path.read_bytes()
    scheduled, covered = doubles(monkeypatch, repo)
    out = tmp_path / "count-only-output"
    assert qm.main(["--count-only", "--incremental", str(path), "--out", str(out)]) == 0
    assert not scheduled and not covered
    assert not out.exists()
    assert path.read_bytes() == original


@pytest.mark.parametrize("component", ["python", "platform", "installed_tool"])
def test_actual_runtime_and_installed_measurement_tool_versions_change_the_digest(
    component, tmp_path, monkeypatch
):
    repo = repository(tmp_path)
    if component == "installed_tool":
        monkeypatch.setattr(qm.metadata, "version", lambda _name: "fixture-installed-1")
    before = inputs(repo)
    if component == "python":
        monkeypatch.setattr(qm.sys, "version", qm.sys.version + " changed fixture interpreter")
    elif component == "platform":
        monkeypatch.setattr(qm.sys, "platform", qm.sys.platform + " changed fixture platform")
    else:
        monkeypatch.setattr(qm.metadata, "version", lambda _name: "fixture-installed-2")
    assert inputs(repo) != before


def test_readme_indented_executable_examples_are_measurement_inputs(tmp_path):
    repo = repository(tmp_path)
    path = repo / "README.md"
    path.write_text("# Fixture\n\nRun the public command:\n\n    trialledger doctor\n")
    before = inputs(repo)
    path.write_text("# Fixture\n\nRun the public command:\n\n    trialledger record report\n")
    assert inputs(repo) != before


@pytest.mark.parametrize("source_kind", ["git_checkout", "archive"])
def test_generated_coverage_and_console_outputs_do_not_change_inputs_but_tracked_fixture_edits_do(
    source_kind, tmp_path
):
    repo = repository(tmp_path)
    project = repo / "pyproject.toml"
    project.write_text(project.read_text() + '\n[project.scripts]\ntrialledger="TrialLedger:f"\n')
    commit(repo, "Declare the archived console entry point")
    if source_kind == "archive":
        root = tmp_path / "archive"
        qm.archive(repo, "HEAD", root)
        assert (root / ".qc-inputs.json").is_file()
    else:
        root = repo
        qm.snapshot_cli(root)
    wrapper = root / ".venv/bin/trialledger"
    assert wrapper.is_file(), "exercise the real generated console wrapper"
    before = inputs(root)
    (root / ".coverage").write_bytes(b"invented generated coverage database")
    (root / "coverage.json").write_text('{"totals":{"covered_lines":1}}\n')
    wrapper.write_text(wrapper.read_text() + "\n# Generated wrapper variation\n")
    (root / "tests/fixtures/transient-untracked.json").write_text('{"temporary":true}\n')
    assert inputs(root) == before
    fixture = root / "tests/fixtures/profile.json"
    fixture.write_text(fixture.read_text().replace('"age":18', '"age":19'))
    assert inputs(root) != before, "a retained input remains an input after coverage generates outputs"


@pytest.mark.parametrize("worker_digest", [None, "worker-reported-different-inputs"])
def test_coordinator_never_relabels_a_missing_or_mismatched_worker_digest_as_its_own(
    worker_digest, tmp_path, monkeypatch, capsys
):
    repo = repository(tmp_path)
    baseline = complete_baseline(repo)
    (repo / "TrialLedger/helper.py").write_text("THRESHOLD = 2\n")
    current = commit(repo, "Require fresh worker evidence after helper change")
    _scheduled, _covered = doubles(monkeypatch, repo)
    seen = []

    def wrong_worker(job):
        _root, targets, _deadline = job
        seen.extend(targets)
        return [record(target, worker_digest) for target in targets]

    monkeypatch.setattr(qm, "census", wrong_worker)
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))
    site = tmp_path / "site"
    try:
        result_code = qm.main(
            [
                "--workers",
                "1",
                "--incremental",
                str(baseline_path),
                "--out",
                str(site),
            ]
        )
    except SystemExit as error:
        assert "mutation_input_mismatch" in str(error)
        assert seen, "the worker must actually have been called"
        return
    assert seen, "the changed helper must force a new worker measurement"
    if result_code:
        output = capsys.readouterr()
        assert "mutation_input_mismatch" in output.out + output.err
        return
    published = json.loads((site / "metrics.json").read_text())
    assert published.get("mutation_applies_to") != current
    assert published["functions_remeasured"] == 0
    assert published["scope_complete"] is False
    assert not any(row.get("input_digest") == inputs(repo) for row in published["records"])
