"""The quality-metrics script plants only meaningful mutants and renders honest, scoped badges."""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import quality_metrics as qm


def mutants_of(source):
    return qm.mutants(ast.parse(source).body[0])


def test_the_docstring_and_f_string_parts_are_never_mutated():
    found = mutants_of('def f(x):\n    """Doc 1 == 2."""\n    return f"{x} items" if x == 1 else "none"\n')
    assert {kind for *_, kind in found} == {"compare", "int", "str"}
    assert all("Doc" not in replacement and "items" not in replacement for *_, replacement, _ in found)


def test_each_operator_family_has_its_mutant():
    found = mutants_of("def f(a, b):\n    return (a < 2 and b) or True\n")
    assert sorted(kind for *_, kind in found) == ["bool", "boolop", "boolop", "compare", "int"]
    compare = next(replacement for *_, replacement, kind in found if kind == "compare")
    assert compare == "a <= 2"


def test_a_multiline_expression_is_skipped_rather_than_spliced():
    found = mutants_of("def f(a):\n    return (\n        a\n        == 1\n    )\n")
    assert [kind for *_, kind in found] == ["int"]


def test_colour_thresholds():
    assert [qm.color(p) for p in (99, 95, 92, 85, 75, 10)] == [
        "brightgreen",
        "brightgreen",
        "green",
        "yellowgreen",
        "yellow",
        "orange",
    ]


def metrics(kill_rate):
    tallied = {
        "functions": 2,
        "mutants": 10,
        "killed": 9,
        "timeouts": 0,
        "survived": 1,
        "kill_rate": kill_rate,
        "functions_selected_by_module_import": 1,
    }
    return {
        "commit": "0123456789abcdef",
        "measured": "2026-11-02",
        "python": "3.14.0",
        "tests_passed": 3566,
        "tests_deselected": 10,
        "line_coverage": 97.7,
        "statements": 8660,
        "branch_coverage": 95.5,
        "branches": 3558,
        "mutation_pinned": tallied,
        "mutation_unpinned_sample": tallied,
        "detective_certificates": {"pinned_decisions": 2, "complete": 1},
        "runtime_dependencies": ["httpx>=0.28", "openpyxl>=3.1"],
        "package_functions": 3,
        "package_nonblank_lines": 100,
        "records": [
            {
                "file": "TrialLedger/x.py",
                "name": "f",
                "outcomes": [{"outcome": "survived", "kind": "int", "before": "a", "after": "b"}],
            }
        ],
    }


def test_render_writes_scoped_badges_report_and_every_survivor(tmp_path):
    report = tmp_path / "QUALITY.md"
    qm.render(metrics(90.0), tmp_path / "site", report)
    mutation = json.loads((tmp_path / "site" / "badges" / "mutation.json").read_text())
    assert mutation == {
        "schemaVersion": 1,
        "label": "Mutation Census (Decision Logic)",
        "message": "90.0% · 0123456 · Measured",
        "color": "green",
    }
    assert json.loads((tmp_path / "site" / "badges" / "dependencies.json").read_text())["message"] == "2"
    assert "`TrialLedger/x.py::f`" in (tmp_path / "site" / "survivors.md").read_text()
    text = report.read_text()
    assert "lower" in text and "bound" in text and "httpx, openpyxl" in text
    assert "not a clinical validation" in " ".join(text.split())
    assert "latest successful publication" in text
    assert "audit not rerun or freshness-validated" in text


def test_an_unmeasured_mutation_score_says_so():
    qm_out = qm.rate({"kill_rate": None})
    assert qm_out == "not measured"


def test_only_survivors_keep_their_planted_bug_text():
    kept = qm.slim(
        [
            {
                "file": "f.py",
                "name": "g",
                "outcomes": [
                    {"line": 1, "kind": "int", "outcome": "killed", "before": "a", "after": "b"},
                    {"line": 2, "kind": "str", "outcome": "survived", "before": "c", "after": "d"},
                ],
            }
        ]
    )
    assert kept[0]["outcomes"] == [
        {"line": 1, "kind": "int", "outcome": "killed"},
        {"line": 2, "kind": "str", "outcome": "survived", "before": "c", "after": "d"},
    ]


def test_a_function_not_started_before_the_deadline_is_returned_skipped(tmp_path):
    target = {"file": "TrialLedger/x.py", "name": "f", "pinned": True, "mutants": 3, "digest": "d"}
    assert qm.census((str(tmp_path), [target], 1.0)) == [{**target, "skipped": True}]


@pytest.mark.parametrize(
    ("updates", "status"),
    [
        ({}, "measured"),
        ({"mutation_commit": "older"}, "historical"),
        ({"functions_stale": 1}, "partial"),
        ({"functions_not_yet_measured": 1}, "partial"),
        ({"mutation_commit": None}, "unmeasured"),
        ({"mutation_commit": "older", "functions_stale": 1}, "historical"),
    ],
)
def test_mutation_basis_never_promotes_old_or_incomplete_results(updates, status):
    source = {**metrics(95.4), **updates}
    assert qm.mutation_basis(source)["status"] == status


def test_pinned_functions_without_a_passing_baseline_make_the_census_partial():
    source = metrics(99.0)
    source["mutation_pinned"] = {**source["mutation_pinned"], "functions_with_failing_baseline": 1}
    assert qm.mutation_basis(source)["status"] == "partial"
    assert "1 without passing baseline" in qm.mutation_message(source)


def test_no_mutants_does_not_become_a_measured_zero_percent_score():
    assert qm.mutation_basis(metrics(None))["status"] == "unmeasured"
    assert qm.mutation_message(metrics(None)) == "Not measured"


def test_render_keeps_old_census_date_and_incomplete_scope_visible(tmp_path):
    source = {
        **metrics(99.0),
        "commit": "newer123456",
        "measured": "2026-11-04",
        "mutation_commit": "older123456",
        "mutation_measured": "2026-11-02",
        "functions_stale": 7,
        "functions_not_yet_measured": 3,
    }
    qm.render(source, tmp_path)
    mutation = json.loads((tmp_path / "badges/mutation.json").read_text())
    assert mutation["message"] == "99.0% · older12 · Historical · 7 stale · 3 unmeasured"
    assert mutation["color"] == "lightgrey"
    tests = json.loads((tmp_path / "badges/tests.json").read_text())
    assert tests["message"] == "3,566 passed · newer12"
    assert tests["label"] == "Test Suite"
    for filename in ("index.html", "quality.md"):
        report = (tmp_path / filename).read_text()
        assert "2026-11-04" in report and "2026-11-02" in report
        assert "Historical" in report and "7 stale" in report and "3 unmeasured" in report
    survivors = (tmp_path / "survivors.md").read_text()
    assert "older12" in survivors and "newer12" not in survivors
    assert source["mutation_commit"] == "older123456"


def test_partial_census_cannot_render_as_unqualified_green(tmp_path):
    source = {**metrics(99.0), "functions_stale": 1}
    qm.render(source, tmp_path)
    mutation = json.loads((tmp_path / "badges/mutation.json").read_text())
    assert "Partial" in mutation["message"] and "1 stale" in mutation["message"]
    assert mutation["color"] == "lightgrey"


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def tiny_repository(tmp_path):
    repo = tmp_path / "repo"
    (repo / "TrialLedger").mkdir(parents=True)
    (repo / "TrialLedger/__init__.py").write_text(
        'def f(x):\n    """An isolated census fixture (pure — pinned)."""\n'
        "    if x > 1:\n        return True\n    return False\n"
    )
    (repo / "tests/detective").mkdir(parents=True)
    (repo / "tests/detective/certificates.json").write_text("{}")
    (repo / "tests/test_x.py").write_text("from TrialLedger import f\ndef test_f():\n    assert f(2)\n")
    (repo / "pyproject.toml").write_text('[project]\nname="fixture"\nversion="0.0.0"\ndependencies=[]\n')
    git(repo, "init", "--initial-branch=main")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Initial fixture")
    return repo


def quality_cli(repo, *args):
    pytest.importorskip("coverage", reason="CLI measurement checks use the quality workflow's overlay")
    pytest.importorskip("pytest_cov", reason="CLI measurement checks use the quality workflow's overlay")
    script = Path(qm.__file__).resolve()
    result = subprocess.run(
        [sys.executable, str(script), *args], cwd=repo, capture_output=True, text=True, timeout=90
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_public_coverage_publication_keeps_census_basis_for_the_next_incremental_run(tmp_path):
    repo = tiny_repository(tmp_path)
    old_commit = git(repo, "rev-parse", "HEAD")
    source = metrics(90.0)
    source.update(
        commit=old_commit,
        records=[
            {
                **qm.functions(repo)[0],
                "baseline": "passing",
                "selected_by": "name",
                "test_files": ["tests/test_x.py"],
                "outcomes": [{"outcome": "survived", "kind": "compare", "before": "a", "after": "b"}],
            }
        ],
    )
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(source))
    with (repo / "tests/test_x.py").open("a") as stream:
        stream.write("def test_boundary():\n    assert not f(1)\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Change selected tests without changing the function")
    new_commit = git(repo, "rev-parse", "HEAD")
    site = tmp_path / "site"
    quality_cli(repo, "--coverage-only", "--incremental", str(baseline), "--out", str(site))
    early = json.loads((site / "metrics.json").read_text())
    assert early["commit"] == new_commit and early["mutation_commit"] == old_commit
    assert early["mutation_measured"] == "2026-11-02"
    assert early["tests_passed"] == 2 and early["functions_remeasured"] == 0
    assert early["mutation_pinned"] == source["mutation_pinned"]
    assert early["records"] == source["records"]
    assert early["mutation_basis"]["status"] == "historical"
    output = quality_cli(repo, "--count-only", "--incremental", str(site / "metrics.json"))
    assert "measuring 1 functions" in output and "reusing 0" in output
    quality_cli(repo, "--incremental", str(site / "metrics.json"), "--out", str(site), "--workers", "1")
    measured = json.loads((site / "metrics.json").read_text())
    assert measured["mutation_commit"] == new_commit
    assert measured["functions_remeasured"] == 1
    assert measured["mutation_basis"]["status"] == "measured"


def test_first_public_coverage_publication_does_not_invent_a_census(tmp_path):
    repo = tiny_repository(tmp_path)
    site = tmp_path / "site"
    quality_cli(repo, "--coverage-only", "--out", str(site))
    result = json.loads((site / "metrics.json").read_text())
    assert result["tests_passed"] == 1
    assert result["mutation_commit"] is None and result["mutation_measured"] is None
    assert result["records"] == [] and result["mutation_basis"]["status"] == "unmeasured"
    mutation = json.loads((site / "badges/mutation.json").read_text())
    assert mutation["message"] == "Not measured" and mutation["color"] == "lightgrey"
    output = quality_cli(repo, "--count-only", "--incremental", str(site / "metrics.json"))
    assert "measuring 1 functions" in output


def test_public_limited_census_reports_omitted_targets_instead_of_a_complete_scope(tmp_path):
    repo = tiny_repository(tmp_path)
    with (repo / "TrialLedger/__init__.py").open("a") as stream:
        stream.write('def g():\n    """Second fixture (pure — pinned)."""\n    return True\n')
    with (repo / "tests/test_x.py").open("a") as stream:
        stream.write("from TrialLedger import g\ndef test_g():\n    assert g()\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "Add a second census target")
    site = tmp_path / "site"
    quality_cli(repo, "--limit", "1", "--workers", "1", "--out", str(site))
    result = json.loads((site / "metrics.json").read_text())
    assert result["functions_remeasured"] == 1 and result["functions_not_yet_measured"] == 1
    assert result["mutation_pinned"]["kill_rate"] == 100.0
    mutation = json.loads((site / "badges/mutation.json").read_text())
    assert "Partial" in mutation["message"] and "1 unmeasured" in mutation["message"]
    assert mutation["color"] == "lightgrey"
