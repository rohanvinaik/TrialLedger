"""Task 4.3: binomial_design and external_method through shared session replay, budgets and metadata.

Every request is an invented fixture. A study-derived number may enter a plan only as a declared, attributed
object value; no source result is read by the projection, and no unsupported survival, cluster or adaptive
calculation is computed or implied.
"""

import copy
import json

from tests.test_protocol_admission_inputs import _binomial_session
from tests.test_protocol_session_replay import adoption_premise
from TrialLedger.layer2 import run, source_evidence

MODEL = "fixed_n_iid_bernoulli"
CHECK = "efficacy-check"
SURVIVAL = "survival-check"


def _computed(**parameters) -> dict:
    values = {"model": MODEL, "n": 2, "critical_count": 2, "p0": "1/2", "p1": "3/4"}
    values.update(parameters)
    return _binomial_session(**values)


def _check(reply: dict, identity: str = CHECK) -> dict:
    return next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == identity)


def _signal(reply: dict) -> dict:
    (child,) = _check(reply)["children"]
    return child["result"]["result"]["signals"][0]


def _survival(request: dict, missing=("accrual_rate", "dropout")) -> dict:
    """Add an adopted external survival-method declaration and its check to a binomial session."""
    session = request["session"]
    protocol = session["protocol"]
    template = protocol["objects"][0]
    reference = copy.deepcopy(template["data"]["definition"])
    for identity, kind, data, depends_on in (
        (
            "survival-method",
            "external_method",
            {
                "definition": {**reference, "ref": "invented:logrank-sample-size"},
                "inputs": [{"name": "hazard_ratio", "value": "0.7", "unit": "ratio", "ref": None}],
                "missing": list(missing),
            },
            ["response"],
        ),
        (
            "efficacy-ext",
            "efficacy",
            {
                "endpoint": "response",
                "method": "external_method",
                "parameters": "survival-method",
                "assumptions": [],
            },
            ["response", "survival-method"],
        ),
    ):
        held = copy.deepcopy(template)
        held.update(id=identity, kind=kind, data=data, depends_on=depends_on)
        held["support"] = [f"adopt:{identity}:invented-v1"]
        protocol["objects"].append(held)
        session["premises"].append(adoption_premise(identity, "invented-v1"))
    protocol["checks"].append(
        {
            "id": SURVIVAL,
            "kind": "external_method",
            "scope": copy.deepcopy(template["scope"]),
            "objects": ["efficacy-ext", "survival-method"],
            "bindings": [{"projection": "named"}],
            "claims": [],
            "required": True,
            "support": [],
        }
    )
    return request


def _digests(reply: dict) -> tuple[str, str]:
    (child,) = _check(reply)["children"]
    return child["request_digest"], child["result_digest"]


def test_exact_tails_reach_the_session_child_from_the_declared_object_values():
    """STA-1 through replay: n=2, k=2 gives 1/4 and 9/16; k=1 gives 3/4 and 15/16 (k versus k-1)."""
    two = run(_computed())
    assert two["code"] == "complete", two.get("problems")
    value = _signal(two)["value"]
    assert (value["null_rejection_probability"], value["power"]) == ("1/4", "9/16")
    assert value["guarantee"] == "exact_conditional_on_declared_model"
    assert "clinical_applicability" in value["not_computed"]

    one = run(_computed(critical_count=1))
    value = _signal(one)["value"]
    assert (value["null_rejection_probability"], value["power"]) == ("3/4", "15/16")


def test_a_supported_but_unmet_power_target_is_open_and_never_a_conflict_in_the_headline():
    """Missing a declared power target is a design question; the headline must not count it as a conflict."""
    request = _computed()
    request["session"]["protocol"]["checks"][-1]["claims"] = [
        {"id": "power", "quantity": "power", "comparison": ">=", "value": "9/10"}
    ]
    reply = run(request)
    row = next(c for c in _signal(reply)["claim_admission"] if c["claim"] == "power")
    assert row["outcome"] == "not_satisfied"
    assert _signal(reply)["value"]["power"] == "9/16"
    index = reply["result"]["protocol"]["checks"].index(_check(reply))
    prefix = f"/result/protocol/checks/{index}/"
    findings = [
        f for f in reply["metadata"]["findings"] if f["kind"] == "protocol_claim" and prefix in f["path"]
    ]
    assert [(f["logical_result"], f["disposition"]) for f in findings] == [("not_satisfied", "open")]
    # The schedule check's own gaps are repair choices, so no finding anywhere is a conflict.
    assert "conflict" not in reply["summary"]["dispositions"]


# --- source results are never planning targets ---------------------------------------------------------

REGISTRY_POINTER = (
    "/resultsSection/outcomeMeasuresModule/outcomeMeasures/0/classes/0/categories/0/measurements/0"
)


def _study(responders: str) -> dict:
    return {
        "protocolSection": {"identificationModule": {"nctId": "NCT00000002"}},
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [
                    {
                        "title": "Responders",
                        "classes": [{"categories": [{"measurements": [{"value": responders}]}]}],
                    }
                ]
            }
        },
    }


def _with_source(request: dict, responders: str) -> dict:
    """Attach a retained registry result; no plan value is taken from it."""
    study = _study(responders)
    snapshot = source_evidence.snapshot(study)
    request["session"]["sources"].append(
        {"id": "registry", "study": study, "expected_digest": snapshot["digest"]}
    )
    return request


def _source_origin(request: dict, responders: str) -> dict:
    """Mark the efficacy object as a reading of the registry result, with a copied address."""
    snapshot = source_evidence.snapshot(_study(responders))
    efficacy = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "efficacy")
    efficacy["origin"] = {
        "kind": "source_interpretation",
        "ref": snapshot["study_ref"] + "#" + REGISTRY_POINTER + "/value",
        "source": "registry",
        "analysis": None,
    }
    return request


def test_a_retained_registry_result_changes_no_planning_value_or_child_digest():
    """MUST-NOT: the projection never reads source results; attaching one moves no child digest."""
    plain = run(_computed())
    with_registry = run(_with_source(_computed(), "12"))
    other_registry = run(_with_source(_computed(), "17"))

    for reply in (plain, with_registry, other_registry):
        assert reply["code"] == "complete", reply.get("problems")
    assert _digests(plain) == _digests(with_registry) == _digests(other_registry)
    assert with_registry["result"]["sources"][0]["study"] == _study("12")
    assert other_registry["result"]["sources"][0]["study"] == _study("17")


def test_planning_parameters_are_the_declared_object_values_not_the_registry_numbers():
    """The child request carries n, k, p0 and p1 exactly as the object declares them."""
    reply = run(_with_source(_computed(n=2, critical_count=2), "7777"))
    (child,) = _check(reply)["children"]
    data = child["request"]["signals"][0]["data"]
    assert (data["n"], data["critical_count"], data["p0"], data["p1"]) == (2, 2, "1/2", "3/4")
    assert "7777" not in json.dumps(data)


def test_a_registry_rate_enters_only_as_an_attributed_proposed_reading_that_is_withheld_until_adopted():
    """A source-derived plan value keeps its origin and is not applied while only proposed."""
    request = _source_origin(_with_source(_computed(), "12"), "12")
    efficacy = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == "efficacy")
    efficacy["standing"] = {
        "status": "proposed",
        "resolution": "unresolved",
        "basis": ["user:invented reading"],
    }
    efficacy["support"] = []
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")

    held = next(o for o in reply["result"]["protocol"]["objects"] if o["id"] == "efficacy")
    assert held["origin"]["kind"] == "source_interpretation"
    assert held["origin"]["source"] == "registry"
    signal = _signal(reply)
    # The exact arithmetic is retained beside the refusal; neither is promoted to a registry fact.
    assert signal["value"]["power"] == "9/16"
    assert (signal["code"], signal["status"]) == ("unresolved", "proposed")
    assert signal["admission"]["code"] == "proposed_refused"
    assert all(p["kind"] != "source_assertion" for p in reply["result"]["effective_premises"])


def test_an_adopted_source_reading_keeps_its_origin_and_does_not_recast_it_as_registry_truth():
    """Adoption is a separate user choice; the object stays a source interpretation."""
    request = _source_origin(_with_source(_computed(), "12"), "12")
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    held = next(o for o in reply["result"]["protocol"]["objects"] if o["id"] == "efficacy")
    assert held["origin"]["kind"] == "source_interpretation"
    assert _signal(reply)["admission"]["code"] == "accepted"
    adoption = next(
        p for p in reply["result"]["effective_premises"] if p["id"] == "adopt:efficacy:invented-v1"
    )
    assert adoption["origin"]["kind"] == "user_choice"


# --- external methods stay uncomputed ------------------------------------------------------------------


def test_an_external_survival_method_is_not_computed_and_names_its_missing_inputs():
    """STA-3 through replay: no child, no number, and the declared missing inputs are named."""
    reply = run(_survival(_computed()))
    assert reply["code"] == "complete", reply.get("problems")
    check = _check(reply, SURVIVAL)
    assert check["children"] == []
    assert check["unresolved"] == []
    assert check["not_computed"]["method"] == "survival-method"
    assert check["not_computed"]["missing"] == ["accrual_rate", "dropout"]
    assert check["not_computed"]["inputs"] == [
        {"name": "hazard_ratio", "value": "0.7", "unit": "ratio", "ref": None}
    ]
    assert reply["result"]["protocol"]["checks"].index(check) == 2


def test_an_external_method_with_no_declared_missing_input_is_still_not_computed():
    """MUST-NOT: a complete-looking declaration is not a calculation; the operator never runs."""
    reply = run(_survival(_computed(), missing=()))
    check = _check(reply, SURVIVAL)
    assert check["children"] == []
    assert check["not_computed"]["missing"] == []
    assert check["not_computed"]["method"] == "survival-method"


def test_an_external_method_does_not_borrow_the_binomial_design_or_alter_it():
    """MUST-NOT: the survival declaration neither reuses the binary design nor changes its result."""
    without = run(_computed())
    with_method = run(_survival(_computed()))
    assert _digests(without) == _digests(with_method)
    survival_text = json.dumps(_check(with_method, SURVIVAL))
    for forbidden in ("power", "null_rejection_probability", "binomial", "critical_count"):
        assert forbidden not in survival_text, forbidden


def test_the_external_method_reaches_the_readable_view_as_not_computed_with_its_missing_inputs():
    """The clinical view lists the uncomputed method with the inputs that are missing."""
    reply = run(_survival(_computed()))
    items = [i for i in reply["protocol_view"]["open_items"] if i["kind"] == "not_computed"]
    assert [i["check"] for i in items] == [SURVIVAL]
    assert "accrual_rate" in items[0]["text"] and "dropout" in items[0]["text"]
    summary = next(s for s in reply["protocol_view"]["check_summaries"] if s["id"] == SURVIVAL)
    assert summary["code"] is None
    assert (summary["conflicts"], summary["repairs"]) == (0, 0)


# --- unsupported models and directions ------------------------------------------------------------------


def test_an_unsupported_model_gives_unsupported_method_and_no_arithmetic():
    """STA-3: a time-to-event model is explicit, uncomputed, and still carries named blockers."""
    request = _binomial_session(model="exponential_time_to_event")
    request["session"]["protocol"]["checks"][-1]["claims"] = [
        {"id": "power", "quantity": "power", "comparison": ">=", "value": "1/2"}
    ]
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    signal = _signal(reply)
    assert signal["code"] == "unsupported_method"
    assert signal["blockers"] == ["binomial_unsupported_method"]
    assert signal["value"]["computed"] is False
    for absent in ("power", "null_rejection_probability", "claims", "display"):
        assert absent not in signal["value"], absent
    assert signal["claim_admission"] == []


def test_an_unsupported_direction_is_unsupported_not_reinterpreted():
    """MUST-NOT: a lower-tail request is not silently answered with the upper tail."""
    reply = run(_computed(direction="less"))
    signal = _signal(reply)
    assert signal["code"] == "unsupported_method"
    assert "power" not in signal["value"]
    assert signal["value"]["computed"] is False


def test_an_unsupported_model_reaches_the_clinical_view_as_a_finding_not_a_pass():
    """The unsupported method is a visible finding with no satisfied claim."""
    reply = run(_binomial_session(model="exponential_time_to_event"))
    summary = next(s for s in reply["protocol_view"]["check_summaries"] if s["id"] == CHECK)
    assert summary["code"] == "unsupported_method"
    items = [i for i in reply["protocol_view"]["open_items"] if i["check"] == CHECK]
    assert any("binomial_unsupported_method" in i["text"] for i in items)


# --- budget ---------------------------------------------------------------------------------------------


def _reserved(request: dict) -> int:
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    return reply["work"]["solver_work_reserved"]


def test_binomial_work_is_reserved_in_the_session_budget_and_gated_exactly():
    """LIM-1: the session reservation includes the binomial child; one unit less is refused by name."""
    reserved = _reserved(_computed())
    bare = _computed()
    bare["session"]["protocol"]["checks"] = [
        c for c in bare["session"]["protocol"]["checks"] if c["id"] != CHECK
    ]
    assert reserved > _reserved(bare)

    at_limit = _computed()
    at_limit["session"]["limits"]["max_solver_work"] = reserved
    assert run(at_limit)["code"] == "complete"

    below = _computed()
    below["session"]["limits"]["max_solver_work"] = reserved - 1
    refused = run(below)
    assert refused["code"] == "refused"
    assert refused["problems"] == ["resource_bound:session_solver_work"]


def test_a_larger_declared_n_reserves_more_session_work_and_the_child_reserves_by_its_formula():
    """The reservation grows with n; the child's own reservation is 12 * (n + 2)."""
    small, large = run(_computed(n=2)), run(_computed(n=40, critical_count=20))
    assert large["work"]["solver_work_reserved"] > small["work"]["solver_work_reserved"]
    for reply, n in ((small, 2), (large, 40)):
        work = _signal(reply)["value"]["work"]
        assert work["reserved"] == 12 * (n + 2)
        assert 0 < work["used"] <= work["reserved"]
