"""Direct-call tests for the protocol-object validator (packet A, ledger.md).

Unit behaviour only: these do not exercise session admission, the CLI or MCP, and say nothing clinical.
"""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from TrialLedger.layer2 import protocol_objects

FIXTURES = (
    Path(__file__).resolve().parent.parent
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures/objects.json"
)
CASES = json.loads(FIXTURES.read_text())["cases"]
BY_ID = {case["id"]: case for case in CASES}
TARGET = {
    "kind": "new_trial",
    "ref": "draft",
    "scope": {"study": "draft", "population": "general", "arm": "all", "time": "entry", "version": "v1"},
}
PREMISES = {"p1": {"kind": "assertion"}, "p2": {"kind": "assertion"}}
SOURCES = {
    "src": {
        "snapshot": {"study_ref": "ctg:NCT00000001:rev"},
        "study": {"protocolSection": {"title": "invented"}},
    }
}
ALL_SECTIONS = [
    "population",
    "eligibility",
    "interventions",
    "endpoints",
    "assessments",
    "efficacy",
    "safety",
    "exploratory",
]


def context() -> dict:
    return {"target": copy.deepcopy(TARGET), "premises": dict(PREMISES), "sources": copy.deepcopy(SOURCES)}


def valid() -> dict:
    return copy.deepcopy(BY_ID["valid_all_kinds"]["protocol"])


def obj(protocol: dict, identity: str) -> dict:
    return next(item for item in protocol["objects"] if item["id"] == identity)


def test_fixture_cases_are_all_exercised():
    assert len(CASES) >= 100
    assert {"expect", "refusal"} >= set().union(*({k for k in c} - {"id", "protocol"} for c in CASES))


@pytest.mark.parametrize("case", [c for c in CASES if "refusal" in c], ids=lambda c: c["id"])
def test_malformed_fixture_refuses_with_its_named_code(case):
    with pytest.raises(ValueError) as error:
        protocol_objects.validate_protocol(case["protocol"], **context())
    assert str(error.value) == case["refusal"]


@pytest.mark.parametrize("case", [c for c in CASES if "expect" in c], ids=lambda c: c["id"])
def test_valid_fixture_is_admitted(case):
    index = protocol_objects.validate_protocol(case["protocol"], **context())
    assert index["schema_version"] == 1
    assert len(index["objects"]) == len(case["protocol"]["objects"])
    assert list(index["sections"]) == ALL_SECTIONS


def test_every_kind_and_every_check_pattern_is_admitted():
    index = protocol_objects.validate_protocol(valid(), **context())
    assert set(index["kinds"].values()) == set(protocol_objects.KINDS)
    kinds = [check["kind"] for check in index["checks"].values()]
    assert set(kinds) == set(protocol_objects.CHECK_KINDS)
    assert index["check_order"] == [check["id"] for check in valid()["checks"]]


def test_empty_lists_are_valid_and_every_section_is_not_requested():
    index = protocol_objects.validate_protocol(
        {"schema_version": 1, "objects": [], "checks": [], "sections": []}, **context()
    )
    assert index["objects"] == {} and index["order"] == [] and index["checks"] == {}
    assert list(index["sections"]) == ALL_SECTIONS
    for section in index["sections"].values():
        assert section == {"state": "not_requested", "objects": [], "basis": []}


def test_requested_and_not_applicable_sections_are_kept_and_the_rest_omitted():
    index = protocol_objects.validate_protocol(valid(), **context())
    assert index["sections"]["endpoints"] == {"state": "requested", "objects": ["ep1"], "basis": ["listed"]}
    assert index["sections"]["eligibility"]["state"] == "not_applicable"
    assert index["sections"]["eligibility"]["basis"] == ["single-cohort draft"]
    assert index["sections"]["interventions"]["state"] == "not_requested"
    assert index["sections"]["exploratory"]["state"] == "not_requested"
    assert index["sections"]["population"] == {"state": "requested", "objects": [], "basis": []}


def test_forward_references_resolve_after_whole_graph_validation():
    protocol = valid()
    # m1 names m0 as baseline and lists it; m0 is declared after m1 in the fixture
    ids = [item["id"] for item in protocol["objects"]]
    assert ids.index("m1") < ids.index("m0")
    index = protocol_objects.validate_protocol(protocol, **context())
    assert index["references"]["m1"]["objects"] == ["m0"]


def test_order_puts_dependencies_first_with_ties_in_input_order():
    index = protocol_objects.validate_protocol(valid(), **context())
    position = {identity: place for place, identity in enumerate(index["order"])}
    for identity, item in index["objects"].items():
        for parent in item["depends_on"]:
            assert position[parent] < position[identity]
    assert sorted(index["order"]) == sorted(index["objects"])
    # m1 (declared first) waits for m0; est1 is ready and earlier than m1's other dependents
    assert index["order"][:3] == ["m0", "m1", "est1"]


def test_dependents_and_references_are_derived_from_the_declared_lists():
    index = protocol_objects.validate_protocol(valid(), **context())
    assert index["dependents"]["m1"] == ["ep1", "a1", "pol1", "xm1"]
    assert index["dependents"]["pol1"] == []
    assert index["references"]["ef1"] == {"objects": ["ep1"], "premises": [], "sources": []}
    assert index["references"]["ef2"]["objects"] == ["ep1", "xm1"]
    assert index["references"]["m0"]["sources"] == ["src"]
    assert index["references"]["ep1"]["premises"] == ["p1", "p2"]
    # an extra explicit dependency is allowed and is not a data reference
    protocol = valid()
    obj(protocol, "a1")["depends_on"].append("est1")
    extra = protocol_objects.validate_protocol(protocol, **context())
    assert extra["references"]["a1"]["objects"] == ["m1"]
    assert "a1" in extra["dependents"]["est1"]


def test_empty_support_is_allowed_and_no_effective_standing_is_returned():
    protocol = valid()
    item = obj(protocol, "a1")
    item["support"] = []
    item["standing"] = {"status": "known", "resolution": "resolved", "basis": ["declared"]}
    index = protocol_objects.validate_protocol(protocol, **context())
    assert index["objects"]["a1"]["support"] == []
    assert index["objects"]["a1"]["standing"]["status"] == "known"
    assert set(index) == {
        "schema_version",
        "objects",
        "kinds",
        "order",
        "dependents",
        "references",
        "checks",
        "check_order",
        "sections",
    }
    for key in ("references", "sections"):
        assert not any("standing" in str(row) for row in index[key].values())


def test_index_is_detached_from_the_input_in_both_directions():
    protocol = valid()
    pristine = copy.deepcopy(protocol)
    index = protocol_objects.validate_protocol(protocol, **context())
    assert protocol == pristine
    snapshot = copy.deepcopy(index)
    obj(protocol, "a1")["data"]["permitted"][0]["lower"] = "0"
    protocol["checks"][0]["claims"].append({"changed": True})
    protocol["sections"][1]["objects"].append("m0")
    assert index == snapshot
    index["objects"]["a1"]["data"]["anchor"] = "mutated"
    index["checks"]["k-sched"]["objects"].append("m0")
    index["sections"]["endpoints"]["objects"].append("m0")
    assert obj(protocol, "a1")["data"]["anchor"] == "event-z"
    again = protocol_objects.validate_protocol(protocol, **context())
    assert again["objects"]["a1"]["data"]["anchor"] == "event-z"


def test_null_context_is_open_and_never_inferred():
    index = protocol_objects.validate_protocol(valid(), **context())
    assert index["objects"]["a1"]["scope"]["context"] == {"cohort": "cohort-x", "phase": None, "arm": None}


def test_the_validator_returns_json_that_round_trips():
    index = protocol_objects.validate_protocol(valid(), **context())
    assert json.loads(json.dumps(index)) == index


def test_literal_key_lists_have_their_pinned_contents():
    assert protocol_objects.R_DEP == (
        "scope",
        "version",
        "rules",
        "adopted",
        "available",
        "unavailable",
        "conditions",
    )
    assert protocol_objects.R_EST[0] == "scope" and len(protocol_objects.R_EST) == 9
    assert protocol_objects.R_POL[2] == "variables" and len(protocol_objects.R_POL) == 11


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda p: p.__setitem__("schema_version", True), "protocol_version"),
        (lambda p: p["checks"][0].__setitem__("required", 1), "protocol_invalid_required"),
        (lambda p: obj(p, "a1")["data"].__setitem__("nominal", 84.0), "protocol_invalid_rational"),
        (lambda p: obj(p, "a1")["data"].__setitem__("nominal", True), "protocol_invalid_rational"),
        (
            lambda p: obj(p, "ef1")["data"]["parameters"].__setitem__("critical_count", 6.0),
            "protocol_data_fields:efficacy",
        ),
        (lambda p: obj(p, "a1")["scope"]["context"].pop("arm"), "protocol_scope_context"),
        (lambda p: obj(p, "a1")["scope"].pop("context"), "protocol_scope_fields"),
        (lambda p: p.__setitem__("objects", None), "protocol_not_list"),
        (lambda p: obj(p, "a1").__setitem__("depends_on", None), "protocol_not_list"),
        (lambda p: obj(p, "a1").__setitem__("support", ["p1", ["p2"]]), "protocol_unknown_premise"),
    ],
)
def test_strict_types_never_coerce(mutate, code):
    protocol = valid()
    mutate(protocol)
    with pytest.raises(ValueError, match=f"^{code}$"):
        protocol_objects.validate_protocol(protocol, **context())


def test_protocol_that_is_not_an_object_is_refused():
    for bad in (None, [], "protocol", 1):
        with pytest.raises(ValueError, match="^protocol_fields$"):
            protocol_objects.validate_protocol(bad, **context())


def test_a_257th_object_is_refused_and_the_256th_is_not():
    over = BY_ID["object_limit_257"]["protocol"]
    with pytest.raises(ValueError, match="^protocol_object_limit$"):
        protocol_objects.validate_protocol(over, **context())
    exact = protocol_objects.validate_protocol(BY_ID["object_limit_256_is_valid"]["protocol"], **context())
    assert len(exact["order"]) == 256


def test_a_long_dependency_chain_orders_without_recursion():
    protocol = valid()
    protocol["checks"] = []
    protocol["sections"] = []
    items = []
    for number in range(256):
        item = copy.deepcopy(obj(valid(), "m0"))
        item["id"] = f"chain-{number}"
        item["origin"] = {"kind": "user_choice", "ref": "user:x", "source": None, "analysis": None}
        item["data"]["baseline"] = f"chain-{number - 1}" if number else None
        item["depends_on"] = [f"chain-{number - 1}"] if number else []
        items.append(item)
    protocol["objects"] = list(reversed(items))
    index = protocol_objects.validate_protocol(protocol, **context())
    assert index["order"] == [f"chain-{number}" for number in range(256)]


def test_a_context_key_omitted_differs_from_null():
    protocol = valid()
    obj(protocol, "a1")["scope"]["context"]["phase"] = None
    protocol_objects.validate_protocol(protocol, **context())
    del obj(protocol, "a1")["scope"]["context"]["phase"]
    with pytest.raises(ValueError, match="^protocol_scope_context$"):
        protocol_objects.validate_protocol(protocol, **context())


def test_pure_helpers_return_their_named_codes():
    assert protocol_objects.identity_state("a" * 256) == "ok"
    assert protocol_objects.identity_state("a" * 257) == "invalid_id"
    assert protocol_objects.identity_state("") == "invalid_id"
    assert protocol_objects.identity_state(1) == "invalid_id"
    assert protocol_objects.ceiling_state(256, 256) == "ok"
    assert protocol_objects.ceiling_state(257, 256) == "over_limit"
    assert protocol_objects.binding_state(True, False) == "ok"
    assert protocol_objects.binding_state(True, True) == "invalid_binding"
    assert protocol_objects.binding_state(False, False) == "invalid_binding"
    assert protocol_objects.section_state("not_applicable", 0) == "not_applicable_basis"
    assert protocol_objects.section_state("not_applicable", 1) == "ok"
    assert protocol_objects.section_state("requested", 0) == "ok"
    assert protocol_objects.section_state("done", 1) == "invalid_state"
    assert protocol_objects.check_pattern_state("temporal", {}, 5, False) == "ok"
    assert protocol_objects.check_pattern_state("estimand", {"estimand": 1}, 1, False) == "ok"
    assert protocol_objects.check_pattern_state("estimand", {"estimand": 2}, 2, False) == "check_objects"


FORBIDDEN = (
    "decision_tables",
    "dependency_evidence",
    "estimand_evidence",
    "protocol_schedule",
    "protocol_policies",
    "protocol_statistics",
    "session_state",
    "design_session",
)


def test_validating_adds_no_solver_operator_or_session_module_to_a_fresh_process():
    # Interface gap (reported): importing any TrialLedger.layer2 module first runs layer2/__init__, which
    # imports `service` and so session_state/design_session. The ledger's literal "none in sys.modules"
    # cannot hold in a fresh process. This test fixes the baseline (the package alone) and asserts that
    # importing and validating with protocol_objects adds none of the forbidden modules beyond it.
    script = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "import TrialLedger.layer2\n"
        "before = set(sys.modules)\n"
        "from TrialLedger.layer2 import protocol_objects\n"
        "case = json.loads(Path(sys.argv[1]).read_text())['cases'][0]\n"
        "target, premises, sources = (json.loads(arg) for arg in sys.argv[2:5])\n"
        "index = protocol_objects.validate_protocol(\n"
        "    case['protocol'], target=target, premises=premises, sources=sources)\n"
        "assert case['id'] == 'valid_all_kinds' and index['order']\n"
        "added = sorted(set(sys.modules) - before)\n"
        "names = json.loads(sys.argv[5])\n"
        "print(json.dumps([n for n in added if n.rsplit('.', 1)[-1] in names]))\n"
    )
    done = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(FIXTURES),
            json.dumps(TARGET),
            json.dumps(PREMISES),
            json.dumps(SOURCES),
            json.dumps(list(FORBIDDEN)),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).resolve().parent.parent,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout.strip().splitlines()[-1]) == []


def test_module_source_imports_none_of_the_forbidden_modules():
    tree = ast.parse(Path(protocol_objects.__file__).read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    leaves = {name.rsplit(".", 1)[-1] for name in names}
    assert not leaves & set(FORBIDDEN)
    assert {"assertions", "entail", "protocol_numbers", "source_evidence"} <= leaves
