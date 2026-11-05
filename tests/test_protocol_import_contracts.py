"""Static import direction for the protocol modules (interface README, P2.4).

`TrialLedger/layer2/__init__.py` imports `service`, so every runtime import of a layer2 module already loads
the session engine. A runtime `sys.modules` check cannot show what a protocol module itself depends on. This
contract reads each module's own import statements and follows them through the package, statically.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "TrialLedger"
SESSION_AND_TRANSPORT = {
    "TrialLedger.layer2.session_state",
    "TrialLedger.layer2.design_session",
    "TrialLedger.layer2.session_projections",
    "TrialLedger.layer2.service",
    "TrialLedger.layer2.request_preparation",
    "TrialLedger.cli",
    "TrialLedger.mcp_server",
}
OPERATORS = {
    "TrialLedger.layer2.decision_tables",
    "TrialLedger.layer2.dependency_evidence",
    "TrialLedger.layer2.estimand_evidence",
    "TrialLedger.layer2.protocol_schedule",
    "TrialLedger.layer2.protocol_policies",
    "TrialLedger.layer2.protocol_statistics",
    "TrialLedger.layer2.signals",
}
# Pre-existing at 25c6bb5, not introduced by this change: decision_tables.work_reservation lazily imports
# solver_work, which imports session_state for its canonical() JSON helper only. Reusing the decision-table
# validators (operators.md, packet C) therefore reaches it statically. This one edge is named, not waived.
PREEXISTING_EDGES = {("TrialLedger.layer2.decision_tables", "TrialLedger.layer2.solver_work")}
RULES = {
    "TrialLedger.layer2.protocol_numbers": SESSION_AND_TRANSPORT | OPERATORS,
    "TrialLedger.layer2.protocol_schedule": SESSION_AND_TRANSPORT,
    "TrialLedger.layer2.protocol_policies": SESSION_AND_TRANSPORT,
    "TrialLedger.layer2.protocol_statistics": SESSION_AND_TRANSPORT,
    "TrialLedger.layer2.protocol_objects": SESSION_AND_TRANSPORT | OPERATORS,
    "TrialLedger.layer2.protocol_projections": SESSION_AND_TRANSPORT | OPERATORS,
}


def _path(module: str) -> Path | None:
    relative = Path(*module.split("."))
    for candidate in (PACKAGE.parent / (str(relative) + ".py"), PACKAGE.parent / relative / "__init__.py"):
        if candidate.exists():
            return candidate
    return None


def _direct_imports(module: str) -> set[str]:
    """Modules named by this file's own import statements (package `__init__` side effects excluded)."""
    path = _path(module)
    if path is None:
        return set()
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names if alias.name.startswith("TrialLedger"))
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("TrialLedger"):
            for alias in node.names:
                child = node.module + "." + alias.name
                found.add(child if _path(child) is not None else node.module)
    return found - {"TrialLedger", "TrialLedger.layer2"}


def _closure(module: str) -> set[str]:
    seen: set[str] = set()
    stack = [module]
    while stack:
        current = stack.pop()
        for name in _direct_imports(current):
            if (current, name) in PREEXISTING_EDGES:
                continue
            if name not in seen:
                seen.add(name)
                stack.append(name)
    return seen


@pytest.mark.parametrize("module", sorted(RULES))
def test_protocol_module_import_closure_respects_its_direction(module):
    if _path(module) is None:
        pytest.skip(module + " is not integrated yet")
    reached = _closure(module) & RULES[module]
    assert not reached, f"{module} reaches {sorted(reached)}"


def test_the_contract_detects_a_forbidden_edge():
    assert "TrialLedger.layer2.session_state" in _closure("TrialLedger.layer2.design_session")


def test_each_named_preexisting_edge_still_exists():
    for source, target in PREEXISTING_EDGES:
        assert target in _direct_imports(source), f"stale exception {source} -> {target}; remove it"


def test_the_clinical_view_reaches_only_pure_number_outcome_and_origin_projections():
    reached = {
        name for name in _closure("TrialLedger.layer2.protocol_view") if name.startswith("TrialLedger")
    }
    # protocol_outcomes is a dependency-free leaf: the one owner of the outcome classifications.
    assert reached == {
        "TrialLedger.layer2.protocol_numbers",
        "TrialLedger.layer2.protocol_outcomes",
        "TrialLedger.layer2.protocol_origins",
    }, sorted(reached)
