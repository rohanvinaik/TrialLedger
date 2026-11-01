"""Every table entry is wired: the production path reaches it, or it is declared dormant with its reason.

Vulture counts a function named in a table as used, so it cannot see a table entry nothing ever calls; these
tests can. The production path (tests/production_path.py, run in its own process with every call recorded
from before import) is a two-page pull with a retry and a value a cell cannot hold, `verify` of the folder
written, `verify` of an unreadable workbook, and a pull the server keeps failing.

Positive: the check tables agree with each other; production gathers exactly the approved checks; every
function of the package runs on the production path except the declared ones; every sheet fills every column
of every row; every rule of the RULE table is looked up; every code a decision returns has its words; every
role the structure states and every field the definitions limit to a study type is reached.
Negative: no function goes unreached without a declared reason; a dormant decision belongs to proposed checks
only, and a dormant helper is called only from their code.
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

from TrialLedger import cells, checks, ledger, workbook
from TrialLedger.checks import APPROVED, BASIS, CHECKS, DECISIONS, GATHERERS

HERE = Path(__file__).resolve().parent
PROPOSED = [check.id for check in CHECKS if check.id not in APPROVED]
# Code that runs only once the founder approves a proposed check (law 13: a rule TrialLedger's reading entails
# is proposed for his approval, never self-approved). Approving a check moves its code onto the path.
DORMANT_DECISIONS = {
    "withdrawn_enrollment_zero",
    "phase_interventional_only",
    "member",
    "bounded",
    "age_magnitude",
    "age_limits_ordered",
    "date_interval",
    "dates_ordered",
}
DORMANT_HELPERS = {"_dates", "_event_counts", "_event_groups", "_unknown"}
# Reached by no production path, each for its reason.
DECLARED = {
    "record.py: _ignore": "write_record's default progress sink, likewise",
    "workbook.py: WorkbookError.__init__": "raised only when the read-back differs from the derivation, "
    "which tests/test_workbook.py simulates",
    "classes.py: http_get": "RxClass's network transport; production_path injects a fake, as it does the API",
    "profile.py: mechanism_rows.<locals>.<lambda>": "sorts mechanism rows, and two studies make none; "
    "tests/test_profile.py reaches it",
    "audit.py: run_audit.<locals>.<lambda>": "run_audit's default progress sink; the CLI passes its own",
    "sample.py: draw_sample.<locals>.<lambda>": "draw_sample's default progress sink; the CLI passes its own",
    "transport.py: urllib_http": "the local model's network call; production_path injects a fake, as it does "
    "the registry and RxClass",
}


@pytest.fixture(scope="module")
def production():
    done = subprocess.run(
        [sys.executable, str(HERE / "production_path.py")],
        capture_output=True,
        text=True,
        check=True,
        cwd=HERE.parent,
    )
    report = next(line for line in done.stdout.splitlines() if line.startswith("WIRING "))
    return json.loads(report.removeprefix("WIRING "))


def test_the_production_path_ends_as_production_does(production):
    assert production["codes"] == {
        "pull": 0,
        "verify": 0,
        "profile": 0,
        "profile_fill_axes": 0,
        "profile_not_a_record": 2,
        "resolve": 0,
        "sample": 0,
        "sample_confirmation": 0,
        "sample_confirmation_refused": 2,
        "audit": 0,
        "pilot": 0,
        "audit_no_budget": 2,
        "audit_refused": 2,
        "verify_unreadable": 1,
        "failed_pull": 1,
    }


def test_the_check_tables_agree():
    ids = [check.id for check in CHECKS]
    assert len(set(ids)) == len(ids) == 17
    assert list(GATHERERS) == ids
    assert set(DECISIONS) == set(BASIS) == set(checks.READS) == set(ids)
    assert set(APPROVED) <= set(ids)
    assert len({gatherer.__name__ for gatherer in GATHERERS.values()}) == len(ids)


def test_production_gathers_exactly_the_approved_checks(production):
    unreached = set(production["unreached"])
    for check_id, gatherer in GATHERERS.items():
        assert (f"checks.py: {gatherer.__name__}" not in unreached) == (check_id in APPROVED), check_id


def test_only_declared_code_goes_unreached(production):
    dormant = {f"checks.py: {GATHERERS[check_id].__name__}" for check_id in PROPOSED}
    dormant |= {f"checks.py: {name}" for name in DORMANT_DECISIONS | DORMANT_HELPERS}
    assert set(production["unreached"]) == dormant | set(DECLARED)


def test_a_dormant_decision_belongs_to_proposed_checks_only():
    approved = {decision.__name__ for check_id in APPROVED for decision in DECISIONS[check_id]}
    proposed = {decision.__name__ for check_id in PROPOSED for decision in DECISIONS[check_id]}
    assert proposed >= DORMANT_DECISIONS
    assert not DORMANT_DECISIONS & approved


def test_a_dormant_helper_is_called_only_from_proposed_checks():
    tree = ast.parse(Path(checks.__file__).read_text(encoding="utf-8"))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    dormant = {GATHERERS[check_id].__name__ for check_id in PROPOSED} | DORMANT_HELPERS
    for helper in DORMANT_HELPERS:
        callers = {
            name
            for name, node in functions.items()
            if name != helper and any(isinstance(n, ast.Name) and n.id == helper for n in ast.walk(node))
        }
        assert callers and callers <= dormant, (helper, callers)


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
