"""The quality-metrics script plants only meaningful mutants and renders honest, scoped badges."""

import ast
import json

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
        "label": "mutation · pinned decisions",
        "message": "90.0%",
        "color": "green",
    }
    assert json.loads((tmp_path / "site" / "badges" / "dependencies.json").read_text())["message"] == "2"
    assert "`TrialLedger/x.py::f`" in (tmp_path / "site" / "survivors.md").read_text()
    text = report.read_text()
    assert "lower" in text and "bound" in text and "httpx, openpyxl" in text
    assert "not a clinical validation" in " ".join(text.split())


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
