"""Independent exact-target identity regressions, not evidence of mutation adequacy.

The selected-pytest double reads each complete fixture module to identify the body actually changed.
Real AST discovery, source mutation/restoration and applicability run without Git or worker processes.
"""

from __future__ import annotations

import ast
import copy
import subprocess

import pytest

from scripts import quality_metrics as qm

METHODS = '''class A:
    def choose(self):
        """A decision (pure — pinned)."""
        return True

class B:
    def choose(self):
        """B decision (pure — pinned)."""
        return False
'''
NESTED = """def outer():
    def inner():
        return True
    return inner()

def other():
    def inner():
        return False
    return inner()
"""


def fixture(tmp_path, source=METHODS):
    (tmp_path / "TrialLedger").mkdir()
    (tmp_path / "tests").mkdir()
    path = tmp_path / "TrialLedger/decisions.py"
    path.write_text(source)
    (tmp_path / "tests/test_decisions.py").write_text(
        "def test_declared():\n    choose = True\n    inner = True\n    assert choose and inner\n"
    )
    return path


def returned_constants(source):
    """Full-AST observation of returned constants, indexed by their lexical scope."""
    result = {}

    def visit(nodes, prefix=()):
        for node in nodes:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                qualified = (*prefix, node.name)
                if isinstance(node, ast.FunctionDef):
                    for statement in node.body:
                        if isinstance(statement, ast.Return) and isinstance(statement.value, ast.Constant):
                            result[".".join(qualified)] = statement.value.value
                visit(node.body, qualified)

    visit(ast.parse(source).body)
    return result


def completed():
    return subprocess.CompletedProcess(["selected pytest double"], 0, stdout="", stderr="")


def test_discovery_keeps_same_named_methods_and_nested_functions_as_distinct_identities(tmp_path):
    fixture(tmp_path, METHODS + "\n" + NESTED)
    rows = qm.functions(tmp_path)
    names = {row["name"] for row in rows}
    assert {"A.choose", "B.choose", "outer", "outer.inner", "other", "other.inner"} <= names
    indexed = {row["name"]: row for row in rows}
    assert indexed["A.choose"]["digest"] != indexed["B.choose"]["digest"]
    assert indexed["outer.inner"]["digest"] != indexed["other.inner"]["digest"]


@pytest.mark.parametrize("name", ["A.choose", "B.choose"])
def test_census_mutates_exactly_the_named_method_and_restores_the_complete_source(
    name, tmp_path, monkeypatch
):
    path = fixture(tmp_path)
    target = next(row for row in qm.functions(tmp_path) if row["name"] == name)
    observations = []

    def selected(*_args, **_kwargs):
        observations.append(returned_constants(path.read_text()))
        return completed()

    monkeypatch.setattr(qm, "pytest", selected)
    result = qm.census((str(tmp_path), [target], 0.0))
    expected = {"A.choose": True, "B.choose": False}
    assert observations[0] == expected
    expected[name] = not expected[name]
    assert observations[1:] == [expected]
    assert result[0]["name"] == name and result[0]["digest"] == target["digest"]
    assert result[0]["baseline"] == "passing"
    assert len(result[0]["outcomes"]) == 1
    assert path.read_text() == METHODS


@pytest.mark.parametrize("name", ["outer.inner", "other.inner"])
def test_census_selects_the_exact_nested_function_without_touching_its_same_named_sibling(
    name, tmp_path, monkeypatch
):
    path = fixture(tmp_path, NESTED)
    target = next(row for row in qm.functions(tmp_path) if row["name"] == name)
    observations = []

    def selected(*_args, **_kwargs):
        observations.append(returned_constants(path.read_text()))
        return completed()

    monkeypatch.setattr(qm, "pytest", selected)
    result = qm.census((str(tmp_path), [target], 0.0))
    expected = {"outer.inner": True, "other.inner": False}
    assert observations[0] == expected
    expected[name] = not expected[name]
    assert observations[1:] == [expected]
    assert result[0]["name"] == name
    assert len(result[0]["outcomes"]) == 1
    assert path.read_text() == NESTED


@pytest.mark.parametrize("name", ["A.choose", "outer.inner", "A.choose@2"])
def test_test_discovery_uses_the_leaf_name_of_a_qualified_target(name, tmp_path):
    fixture(tmp_path)
    leaf = "inner" if name == "outer.inner" else "choose"
    (tmp_path / "tests/test_decisions.py").write_text(
        f"def test_declared():\n    {leaf} = True\n    assert {leaf}\n"
    )
    files, selected_by = qm.select_tests(tmp_path, "TrialLedger/decisions.py", name)
    assert files == ["tests/test_decisions.py"] and selected_by == "name"


@pytest.mark.parametrize(
    "source,expected",
    [
        ("def choose():\n    return True\ndef choose():\n    return False\n", {"choose@1", "choose@3"}),
        (
            "class A:\n    def choose(self):\n        return True\n"
            "    def choose(self):\n        return False\n",
            {"A.choose@2", "A.choose@4"},
        ),
        (
            "def outer():\n    def inner():\n        return True\n"
            "    def inner():\n        return False\n    return inner()\n",
            {"outer.inner@2", "outer.inner@4"},
        ),
    ],
)
def test_repeated_identical_qualified_names_receive_unambiguous_line_identities(source, expected, tmp_path):
    fixture(tmp_path, source)
    names = [row["name"] for row in qm.functions(tmp_path)]
    assert expected <= set(names)
    assert len(names) == len(set(names))


def test_census_resolves_a_repeated_qualified_definition_by_its_line_identity(tmp_path, monkeypatch):
    source = (
        "class A:\n    def choose(self):\n        return True\n    def choose(self):\n        return False\n"
    )
    path = fixture(tmp_path, source)
    target = next(row for row in qm.functions(tmp_path) if row["name"] == "A.choose@4")
    observations = []

    def selected(*_args, **_kwargs):
        tree = ast.parse(path.read_text())
        methods = tree.body[0].body
        observations.append([method.body[0].value.value for method in methods])
        return completed()

    monkeypatch.setattr(qm, "pytest", selected)
    result = qm.census((str(tmp_path), [target], 0.0))
    assert observations == [[True, False], [True, True]]
    assert result[0]["name"] == "A.choose@4"
    assert path.read_text() == source


def test_stale_target_body_digest_is_rejected_before_any_selected_suite_or_source_mutation(
    tmp_path, monkeypatch
):
    path = fixture(tmp_path)
    target = next(row for row in qm.functions(tmp_path) if row["name"] == "A.choose")
    current = METHODS.replace("return True", "return False", 1)
    path.write_text(current)
    calls = []

    def forbidden(*_args, **_kwargs):
        calls.append(True)
        pytest.fail("a stale body identity must never be measured under its old digest")

    monkeypatch.setattr(qm, "pytest", forbidden)
    try:
        result = qm.census((str(tmp_path), [target], 0.0))
    except (SystemExit, ValueError) as error:
        assert "target" in str(error).lower()
        assert "mismatch" in str(error).lower() or "digest" in str(error).lower()
    else:
        assert result and all(row.get("skipped") and not row.get("outcomes") for row in result)
    assert not calls
    assert path.read_text() == current


@pytest.mark.parametrize("bad_name", ["choose", "Missing.choose"])
def test_an_ambiguous_or_absent_target_never_falls_back_to_the_first_matching_leaf(
    bad_name, tmp_path, monkeypatch
):
    path = fixture(tmp_path)
    target = next(row for row in qm.functions(tmp_path) if row["name"] == "A.choose")
    target = {**target, "name": bad_name}

    def forbidden(*_args, **_kwargs):
        pytest.fail("no test may run for an absent exact qualified target")

    monkeypatch.setattr(qm, "pytest", forbidden)
    try:
        result = qm.census((str(tmp_path), [target], 0.0))
    except (SystemExit, ValueError) as error:
        assert "target" in str(error).lower()
    else:
        assert result and all(row.get("skipped") and not row.get("outcomes") for row in result)
    assert path.read_text() == METHODS


def test_applicability_preserves_both_same_leaf_pinned_targets_and_refuses_a_collapsed_record_set(tmp_path):
    fixture(tmp_path)
    everything = qm.functions(tmp_path)
    assert {row["name"] for row in everything} == {"A.choose", "B.choose"}
    input_digest = qm.mutation_inputs_digest(tmp_path)
    records = [{**row, "input_digest": input_digest, "baseline": "passing"} for row in everything]
    prior = {
        "scope_complete": True,
        "records": records,
        "pending_targets": [],
        "functions_stale": 0,
        "functions_not_yet_measured": 0,
        "unidentified_pending_targets": 0,
    }
    assert qm.mutation_applicability(prior, input_digest, everything) == "applicable"
    missing = {**prior, "records": records[:1]}
    assert qm.mutation_applicability(missing, input_digest, everything) != "applicable"
    collapsed = {**prior, "records": [copy.deepcopy(records[0]), copy.deepcopy(records[0])]}
    assert qm.mutation_applicability(collapsed, input_digest, everything) != "applicable"


def test_legacy_leaf_only_unpinned_scope_retains_both_current_qualified_targets_for_refresh(tmp_path):
    fixture(tmp_path, METHODS.replace("(pure — pinned)", "unmarked fixture"))
    everything = qm.functions(tmp_path)
    assert all(not row["pinned"] for row in everything)
    legacy = {**everything[0], "name": "choose"}
    assert "input_digest" not in legacy
    baseline = {"mutation_commit": "old-fixture-commit", "records": [legacy], "pending_targets": []}
    scope = qm.census_scope(everything, baseline, 0, 0)
    assert {row["name"] for row in scope} == {"A.choose", "B.choose"}
