"""Operator inputs are refused at admission, by check id, before any work is reserved (PAH cold audit).

Malformed protocol operator parameters (p0 >= p1, a critical count above n + 1, no binomial assumption, a
terminal state with an outgoing transition) used to pass `prepare` and then refuse the whole session halfway
through a replay. They are now parsed at admission by each operator's own `validate`, with no
solver, and refused as protocol_check_input:<check id>:<operator code> by preparation and the run alike.
"""

import copy
import json

import pytest

from tests.test_protocol_options import _alt, _with_decision
from tests.test_protocol_session_replay import ORIGIN, _session, adopt, adoption_premise
from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import protocol_policies, protocol_schedule, protocol_statistics, run

ROLES = ("fixed_n", "iid_binary", "alignment")
CHECKS = ("week12-schedule", "efficacy-check")


def _assumption_premise(role: str) -> dict:
    """An invented accepted assumption record; its body is a boolean statement about the study procedure."""
    body = a.Literal(
        a.Subject("study_procedure"),
        a.Predicate("measurement", "invented_assumption_" + role),
        a.Value("boolean", "eq"),
    )
    payload = a.ScopedAssertion(
        "assume-" + role,
        "user:invented " + role + " assumption",
        "required",
        body,
        rule=a.Rule("user-explicit", "1"),
        status="known",
        resolution="resolved",
    )
    return {
        "id": "assume-" + role,
        "kind": "assertion",
        "payload": json.loads(a.canonical(payload)),
        "origin": copy.deepcopy(ORIGIN),
        "depends_on": [],
    }


def _binomial_session(**parameters) -> dict:
    """A v2 session with an adopted single-arm exact binomial efficacy check on an adopted endpoint."""
    request = _session("84", collection_status="known")
    adopt(request, "collection")
    session = request["session"]
    protocol = session["protocol"]
    template = protocol["objects"][0]
    reference = copy.deepcopy(template["data"]["definition"])
    values = {
        "model": "fixed_n_iid_bernoulli",
        "direction": "greater",
        "n": 20,
        "critical_count": 7,
        "p0": "1/5",
        "p1": "2/5",
    }
    values.update(parameters)
    assumptions = values.pop("assumptions", [{"role": role, "premise": "assume-" + role} for role in ROLES])
    for identity, kind, data, depends_on in (
        (
            "response",
            "endpoint",
            {"variable": "score", "definition": reference, "estimand": None, "dependencies": None},
            ["score"],
        ),
        (
            "efficacy",
            "efficacy",
            {
                "endpoint": "response",
                "method": "binomial_design",
                "parameters": values,
                "assumptions": assumptions,
            },
            ["response"],
        ),
    ):
        held = copy.deepcopy(template)
        held.update(id=identity, kind=kind, data=data, depends_on=depends_on)
        held["support"] = [f"adopt:{identity}:invented-v1"]
        protocol["objects"].append(held)
        session["premises"].append(adoption_premise(identity, "invented-v1"))
    session["premises"] += [_assumption_premise(role) for role in ROLES]
    protocol["checks"].append(
        {
            "id": "efficacy-check",
            "kind": "binomial_design",
            "scope": copy.deepcopy(template["scope"]),
            "objects": ["efficacy", "response"],
            "bindings": [],
            "claims": [],
            "required": True,
            "support": [],
        }
    )
    return request


@pytest.fixture
def no_operator_runs(monkeypatch):
    """Fail loudly if any protocol operator computes; admission must refuse before work."""

    def forbidden(*_args, **_kwargs):
        raise AssertionError("an operator computed before admission refused")

    for module in (protocol_statistics, protocol_schedule, protocol_policies):
        monkeypatch.setattr(module, "check", forbidden)
        monkeypatch.setattr(module, "work_reservation", forbidden)


def test_a_well_formed_binomial_design_is_admitted_and_computed():
    reply = run(_binomial_session())
    assert reply["code"] == "complete", reply.get("problems")
    check = next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == "efficacy-check")
    assert [child["result"]["code"] for child in check["children"]] == ["complete"]
    (signal,) = check["children"][0]["result"]["result"]["signals"]
    assert signal["code"] != "unsupported_method"
    assert (signal["value"]["n"], signal["value"]["critical_count"]) == (20, 7)
    assert "/" in signal["value"]["null_rejection_probability"] and "/" in signal["value"]["power"]


@pytest.mark.parametrize(
    ("parameters", "code"),
    [
        ({"p0": "1/2", "p1": "1/5"}, "binomial_invalid_probabilities"),
        ({"p0": "2/5", "p1": "2/5"}, "binomial_invalid_probabilities"),
        ({"critical_count": 22}, "binomial_invalid_critical_count"),
        ({"n": 0}, "binomial_invalid_n"),
        ({"assumptions": []}, "binomial_invalid_assumption"),
    ],
)
def test_malformed_binomial_parameters_are_refused_at_admission_by_check(no_operator_runs, parameters, code):
    reply = run(_binomial_session(**parameters))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_check_input:efficacy-check:" + code]


def test_an_inverted_permitted_window_is_still_refused_by_object_validation(no_operator_runs):
    """An empty interval was already refused by protocol object validation; it stays refused before work."""
    request = _session("84")
    week12 = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "week12")
    week12["data"]["permitted"] = [
        {"lower": "91", "upper": "77", "lower_inclusive": True, "upper_inclusive": True}
    ]
    reply = run(request)
    assert (reply["code"], reply["problems"]) == ("refused", ["protocol_empty_interval"])


def test_a_malformed_policy_model_is_refused_at_admission(no_operator_runs):
    from tests.test_protocol_definition_relations import _madrs_protocol

    request = _madrs_protocol()
    rule = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "retreatment-rule")
    # A terminal state may not have an outgoing transition (operator contract).
    rule["data"]["model"]["terminal"] = ["monitoring", "decided"]
    reply = run(request)
    assert reply["code"] == "refused"
    (problem,) = reply["problems"]
    assert problem.startswith("protocol_check_input:retreatment-check:"), problem


def test_a_plan_alternative_with_malformed_parameters_is_refused_at_admission(no_operator_runs):
    base = _binomial_session()
    replacement = copy.deepcopy(
        next(o for o in base["session"]["protocol"]["objects"] if o["id"] == "efficacy")
    )
    replacement["data"]["parameters"]["critical_count"] = 30
    request = _with_decision(base, [_alt("as-drafted", [], CHECKS), _alt("bad", [replacement], CHECKS)])
    request["session"]["decisions"][0]["question"] = "Which invented critical count should the draft use?"
    reply = run(request)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_check_input:efficacy-check:binomial_invalid_critical_count"]


def test_preparation_refuses_the_same_malformed_parameters_without_computing(no_operator_runs):
    """The compact preparation path refuses at preparation, not after a successful prepare."""
    card = run({"operation": "describe", "view": "protocol"})["result"]
    example = copy.deepcopy(card["example"])
    origin = example["protocol"]["objects"][0]["origin"]
    definition = copy.deepcopy(example["protocol"]["objects"][0]["data"]["definition"])
    example["protocol"]["objects"] += [
        {
            "id": "response",
            "kind": "endpoint",
            "version": "invented-v1",
            "origin": origin,
            "data": {"variable": "score", "definition": definition, "estimand": None, "dependencies": None},
        },
        {
            "id": "efficacy",
            "kind": "efficacy",
            "version": "invented-v1",
            "origin": origin,
            "data": {
                "endpoint": "response",
                "method": "binomial_design",
                "parameters": {
                    "model": "single_arm_exact_binomial",
                    "direction": "greater",
                    "n": 20,
                    "critical_count": 7,
                    "p0": "1/2",
                    "p1": "1/5",
                },
                "assumptions": [],
            },
        },
    ]
    example["protocol"]["checks"].append(
        {
            "id": "efficacy-check",
            "kind": "binomial_design",
            "objects": ["efficacy", "response"],
            "required": True,
            "claims": [],
        }
    )
    reply = run(example)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_check_input:efficacy-check:binomial_invalid_probabilities"]


def test_a_check_input_refusal_points_at_the_declared_check_and_names_the_contract():
    """Repairable refusal: the code is unchanged, and the diagnostic points at the failing check."""
    request = _binomial_session(p0="1/2", p1="1/5")
    reply = run(request)
    assert reply["problems"] == ["protocol_check_input:efficacy-check:binomial_invalid_probabilities"]
    (diagnostic,) = reply["input_diagnostics"]
    index = next(
        i for i, c in enumerate(request["session"]["protocol"]["checks"]) if c["id"] == "efficacy-check"
    )
    assert diagnostic["pointer"] == f"/session/protocol/checks/{index}"
    assert diagnostic["expected"]["operator_code"] == "binomial_invalid_probabilities"
    assert diagnostic["reference"] == {"operation": "describe", "view": "protocol", "detail": "schema"}
