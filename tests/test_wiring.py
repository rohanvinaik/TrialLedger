"""Every table entry is wired: the production path reaches it, or it is declared dormant with its reason.

Vulture counts a function named in a table as used, so it cannot see a table entry nothing ever calls; these
tests can. The production path (tests/production_path.py, run in its own process with every call recorded
from before import) is a two-page pull with a retry and a value a cell cannot hold, `verify` of the folder
written, `verify` of an unreadable workbook, a pull the server keeps failing, `landscape` run in direct
and in relay mode, and `mcp` serving an MCP client's session (its module docstring lists every command it
runs).

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
# Every check is approved since version 2 (2026-11-01), so none is dormant; the tests below keep the rule for
# any check proposed later.
DORMANT_DECISIONS: set[str] = set()
DORMANT_HELPERS: set[str] = set()
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
    "operate.py: _ignore": "operate.run's default progress sink; the CLI passes its own",
    "mcp_server.py: stdio_streams": "the process's own standard input and output; production_path gives "
    "`trialledger mcp` its streams, as it gives the registry and RxNav",
    "mcp_server.py: stdio_streams.<locals>.write": "the writer of stdio_streams, likewise",
    "landscape.py: kept_strata": "the cohort's strata are read only from the signal minimum of trials up, "
    "which production_path's few trials do not reach; tests/test_landscape.py reaches it",
    "landscape.py: endpoint_profile": "the cohort's endpoints are read only from the signal minimum of "
    "trials up, which production_path's few trials do not reach; tests/test_landscape.py reaches it",
    "readout.py: ReadoutError.__init__": "raised only when landscape.xlsx read back differs from its "
    "derivation, which tests/test_readout_schema3.py simulates",
    "landscape.py: standard_language.<locals>.<lambda>": "orders the criteria a universe's trials share, and "
    "production_path's runs hold fewer trials of one universe than standard language needs; "
    "tests/test_landscape.py reaches it",
}
# The frozen contracts of add-bank-coverage group 1, which the parallel packages are written against: nothing
# in production consumes them yet. Each name is declared with the task that will put it on the path; that task
# removes its names from here.
FOUNDATIONS = {
    "until add-bank-coverage 2.1 (each existing bank audited through the contract and reporting by it)": (
        "semantics/contracts.py",
        (
            "_span_problems",
            "atom_digest",
            "atom_problems",
            "from_legacy",
            "legacy_concept_id",
            "legacy_result",
            "result_problems",
            "slug",
            "to_legacy",
        ),
    ),
    "until add-bank-coverage 2.1 and 3.x (the banks read under the compiled registry's version; each package "
    "compiles its fragment)": (
        "semantics/loader.py",
        (
            "RegistryError.__init__",
            "_alike",
            "_canonical",
            "_entry_problems",
            "_example",
            "_fragment_data",
            "_is_date",
            "_offset",
            "_pairs",
            "_unstable",
            "atom_registry_problems",
            "compile_registry",
            "example_problems",
            "fragment_from_data",
            "load_fragments",
            "nondeterminism_problems",
            "registry_flags",
            "registry_problems",
            "unit_problems",
            "universe_problems",
        ),
    ),
    "until add-bank-coverage 3.2-3.5 (each general package reads its numbers, comparators, units, durations, "
    "windows, intervals and references through the shared parsers; the registry build reads them already)": (
        "semantics/parsers.py",
        (
            "_abstained",
            "_bound",
            "_form_pattern",
            "_grouping",
            "_inside",
            "_interval",
            "_number_values",
            "_orientation",
            "_parse",
            "_range_unit",
            "_skip",
            "read_comparator",
            "read_duration",
            "read_interval",
            "read_number",
            "read_reference",
            "read_unit",
            "read_window",
        ),
    ),
    # landscape.json schema 3 (refine-landscape-record unit A) carries no per-study coverage, which reached
    # _module, declared_manifest, study_coordinates and universe_status; tests/test_typematrix.py reaches them
    "until add-bank-coverage 4.1 (the discovery wave's type balance) and 7.2 (the release manifest)": (
        "typematrix.py",
        ("_module", "declared_manifest", "manifest_problems", "study_coordinates", "universe_status"),
    ),
    "until refine-landscape-record unit E1's preservation checks read registry paths through the contract": (
        "contract.py",
        ("resolves",),
    ),
    "until add-bank-coverage 7.1 (the confirmation evaluated through the real entry point)": (
        "evaluation.py",
        (
            "_key",
            "_known_level",
            "_single_level",
            "agreement_kind",
            "at_level",
            "bounds",
            "clustered_lower_bound",
            "complete_representation",
            "gold_problems",
            "judge",
            "match",
            "miss_rate",
            "parameter_accuracy",
            "precision",
            "precision_group",
            "rate",
            "recall",
            "threshold_verdict",
            "unit_rates",
        ),
    ),
}
DECLARED |= {f"{file}: {name}": reason for reason, (file, names) in FOUNDATIONS.items() for name in names}
# The scoped-assertion object model and its decision procedure (add-scoped-assertions 1.1, 3.1, 3.2): a
# foundation nothing in production builds assertions for yet; the shadow-mode run reaches it, until
# add-scoped-assertions 5.1. tests/test_assertions.py and tests/test_entail.py reach every one.
UNTIL_SHADOW_MODE = "until add-scoped-assertions 5.1 (assertions produced in shadow mode)"
SCOPED_ASSERTIONS_DORMANT = {
    f"{module}: {name}": UNTIL_SHADOW_MODE
    for module, names in (
        (
            "assertions.py",
            (
                "_Validated.__post_init__",
                "_assertion_problem",
                "_build",
                "_evidence_problem",
                "_finite",
                "_plain",
                "_scope_problem",
                "_time_problem",
                "_value_problem",
                "_whole",
                "canonical",
                "from_canonical",
                "model_problem",
            ),
        ),
        (
            "entail.py",
            (
                "_atoms",
                "_components",
                "_fold",
                "_holds",
                "_literal_formula",
                "_negate",
                "_proof",
                "_satisfiable",
                "_scope_formula",
                "assertion_formula",
                "decide",
                "proposition_formula",
                "weakest_status",
            ),
        ),
    )
    for name in names
}
DECLARED |= SCOPED_ASSERTIONS_DORMANT
# The first predicate registry (add-scoped-assertions 1.2): the compiler of task group 2 reads it, starting
# with D1 structure and D2 alternatives (2.1), and nothing in production builds literals before then.
# tests/test_predicates.py reaches every one.
UNTIL_THE_COMPILER = (
    "until add-scoped-assertions 2.1 (the compiler reads atoms as literals through the registry)"
)
DECLARED |= {
    f"predicates.py: {name}": UNTIL_THE_COMPILER
    for name in ("_digest", "atom_literal", "mapping_problems", "predicate_registry")
}
# The run folder's shell beyond what `trialledger landscape` (add-agent-operation 4.2) reaches:
# tests/test_steps.py reaches every one.
DECLARED |= {
    "steps.py: StepError.__init__": "raised by records and rxnav_answers on a folder not complete, which "
    "operate.run never asks them of",
    "steps.py: _ignore": "advance's default progress sink; the CLI passes its own",
    "steps.py: rxnav_answers": "until add-agent-operation 3.1 (the RxNav requests the step decision relays "
    "beside the registry's; operate.run asks none of it)",
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
        "doctor": 0,
        "pull": 0,
        "verify": 0,
        "profile": 0,
        "profile_fill_axes": 0,
        "profile_not_a_record": 2,
        "resolve": 0,
        "landscape_lookup_failed": 1,
        "landscape": 0,
        "landscape_again": 0,
        "landscape_stopped": 2,
        "landscape_subclasses": 0,
        "landscape_ids": 0,
        "landscape_relay": 0,
        "mcp_relay": 0,
        "mcp_direct": 0,
        "mcp": 0,
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
