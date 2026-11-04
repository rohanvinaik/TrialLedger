"""Persistent layer boundaries and real production behavior.

Partial symbolic foundations need not masquerade as a complete pipeline. These tests
instead enforce report isolation, absence of the retired raw readers, actual entry-point
outcomes, and the original approved-check and archival workbook invariants.
"""

import ast
import inspect
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from records import ongoing_study, results_study

from TrialLedger import cells, checks, cli, ledger, mcp_server, workbook
from TrialLedger.checks import APPROVED, BASIS, CHECKS, DECISIONS, GATHERERS

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent / "TrialLedger"
RETIRED = {
    "banks",
    "criteria",
    "reading",
    "design",
    "symbolic",
    "modality",
    "audit",
    "sample",
    "pilot",
    "questions",
    "transport",
    "gates",
}
REPORT_ROOTS = {
    "acquisition",
    "capabilities",
    "evidence_access",
    "record_access",
    "operate",
    "landscape",
    "readout",
    "landscape_verify",
    "landscape_warrants",
    "request",
    "preview",
    "steps",
    "classes",
    "doctor",
    "record",
    "workbook",
    "checks",
    "ledger",
    "registry",
    "eligibility",
    "links",
    "cells",
    "warrants",
}


def package_imports(path):
    """Python package dependencies from whole-module ASTs, including lazy imports."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names if alias.name.startswith("TrialLedger."))
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "TrialLedger":
                found.update(
                    "TrialLedger." + alias.name
                    for alias in node.names
                    if (PACKAGE / (alias.name + ".py")).is_file()
                    or (PACKAGE / alias.name / "__init__.py").is_file()
                )
            elif node.module.startswith("TrialLedger."):
                found.add(node.module)
    return found


def test_report_dependency_closure_cannot_reach_layer_two_or_retired_readers():
    waiting = {"TrialLedger." + name for name in REPORT_ROOTS}
    visited = set()
    while waiting:
        module = waiting.pop()
        if module in visited:
            continue
        visited.add(module)
        assert not module.startswith("TrialLedger.layer2"), module
        relative = module.removeprefix("TrialLedger.")
        assert relative.split(".")[0] not in RETIRED, module
        path = PACKAGE.joinpath(*relative.split(".")).with_suffix(".py")
        if not path.is_file():
            path = PACKAGE.joinpath(*relative.split("."), "__init__.py")
        assert path.is_file(), module
        waiting |= package_imports(path) - visited


def test_only_explicit_reason_handlers_may_import_layer_two_in_dispatchers():
    for filename in ("cli.py", "mcp_server.py"):
        tree = ast.parse((PACKAGE / filename).read_text())
        for unit in tree.body:
            for node in ast.walk(unit):
                names = (
                    [node.module]
                    if isinstance(node, ast.ImportFrom)
                    else [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else []
                )
                if any(name and name.startswith("TrialLedger.layer2") for name in names):
                    assert isinstance(unit, ast.FunctionDef) and unit.name == "_reason", filename


def test_retired_raw_reader_modules_and_commands_are_absent():
    assert not any((PACKAGE / (name + ".py")).exists() for name in RETIRED)
    tree = ast.parse(Path(cli.__file__).read_text())
    commands = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_parser"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    }
    assert not commands & {"resolve", "profile", "audit", "sample", "pilot"}
    assert "reason" in commands and "reason" in mcp_server.TOOLS
    assert not set(mcp_server.TOOLS) & {"resolve", "profile", "audit", "sample", "pilot"}


@pytest.fixture(scope="module")
def production():
    done = subprocess.run(
        [sys.executable, str(HERE / "production_path.py")],
        capture_output=True,
        text=True,
        check=True,
        cwd=HERE.parent,
    )
    reports = [
        line.removeprefix("WIRING ") for line in done.stdout.splitlines() if line.startswith("WIRING ")
    ]
    assert len(reports) == 1, done.stdout
    return json.loads(reports[0])


def test_real_reporting_archival_and_reasoning_scenarios_end_as_specified(production):
    assert production["codes"] == {
        "doctor": 0,
        "pull": 0,
        "verify": 0,
        "landscape_lookup_failed": 1,
        "landscape": 0,
        "landscape_again": 0,
        "verify_landscape": 0,
        "verify_landscape_nonfinite": 1,
        "landscape_stopped": 2,
        "landscape_subclasses": 0,
        "landscape_ids": 0,
        "landscape_preview": 0,
        "landscape_relay": 0,
        "mcp_relay": 0,
        "mcp_preview": 0,
        "mcp_direct": 0,
        "mcp": 0,
        "reason": 0,
        "verify_unreadable": 1,
        "failed_pull": 1,
    }


def test_production_gathers_exactly_the_approved_checks(production):
    called = set(production["called"])
    for check_id, gatherer in GATHERERS.items():
        assert (f"checks.py: {gatherer.__qualname__}" in called) == (check_id in APPROVED), check_id


def test_the_check_tables_agree():
    ids = [check.id for check in CHECKS]
    assert len(set(ids)) == len(ids) == 17
    assert list(GATHERERS) == ids
    assert set(DECISIONS) == set(BASIS) == set(checks.READS) == set(ids)
    assert set(APPROVED) <= set(ids)
    assert len({gatherer.__name__ for gatherer in GATHERERS.values()}) == len(ids)


def test_every_sheet_fills_every_column_of_every_row():
    contexts = workbook.contexts_for({"studies": [results_study(), ongoing_study()]})
    for sheet in workbook.SHEETS:
        rows = list(sheet.rows(contexts))
        assert rows, sheet.name
        assert all(len(row) == len(sheet.columns) for row in rows), sheet.name


def test_every_rule_is_looked_up(tmp_path, monkeypatch):
    looked_up = set()

    class Recording(dict):
        def __getitem__(self, key):
            looked_up.add(key)
            return super().__getitem__(key)

    monkeypatch.setattr(workbook, "RULE", Recording(workbook.RULE))
    record = {"provenance": {}, "studies": [results_study(), ongoing_study()]}
    for book in workbook.BOOKS:
        workbook.write_workbook(record, tmp_path / book.name, book)
    assert looked_up == set(workbook.RULE)


def returned_codes(function):
    """The string constants a function's return statements can give."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    return {
        value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Return) and node.value is not None
        for value in ast.walk(node.value)
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    }


def test_every_code_a_decision_returns_has_its_words():
    cell_codes = returned_codes(cells.cell_text_state) | returned_codes(cells.cell_number_state)
    assert set(workbook.CELL_REASONS) == cell_codes - {"ok"}
    assert set(workbook.RESULTS_TEXT) == returned_codes(ledger.results_state)
    assert set(ledger.ABSENCE_TEXT) == returned_codes(ledger.absence_state) - {"reported"}


def test_every_role_the_structure_states_is_reached():
    roles = {
        pair for study in (results_study(), ongoing_study()) for e in ledger.entries(study) for pair in e.role
    }
    names = {name for name, _ in roles}
    for pair in ledger.FIXED_ROLES.values():
        assert pair in roles, pair
    for role, _ in ledger.IDENTIFIED_ROLES.values():
        assert role in names, role
    assert "group" in names


def test_every_field_the_definitions_limit_is_shown():
    sources = [column.source for sheet in workbook.SHEETS for column in sheet.columns]
    for field in ledger.APPLIES_TO:
        assert any(source.startswith(field) for source in sources), field
