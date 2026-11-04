"""Intent: later-stage uncertainty must neither poison entry nor disappear from whole eligibility."""

import dataclasses
import json

from TrialLedger.layer2 import run
from TrialLedger.layer2.assertions import (
    AllOf,
    AnyOf,
    Literal,
    Not,
    Predicate,
    Rule,
    Scope,
    ScopedAssertion,
    Subject,
    Value,
    canonical,
)
from TrialLedger.layer2.entail import Context, decide, eligibility_witness, scope_blocker_code


def fact(name):
    return Literal(Subject("participant"), Predicate("condition_status", name), Value("boolean"))


def requirement(name, body, **kwargs):
    return ScopedAssertion(
        name,
        "invented:" + name,
        "required",
        body,
        rule=Rule("invented", "1"),
        status="known",
        resolution="resolved",
        **kwargs,
    )


def test_unrelated_stage_rule_cannot_obscure_universal_exclusion_or_residuals():
    given = (
        requirement("entry", Not(fact("sertraline"))),
        requirement("adult", fact("adult")),
        requirement("renal", fact("renal")),
        requirement("responder", fact("response"), cohort=Scope("cohort_ref", "C")),
    )
    assert decide(given, fact("sertraline")).result == "REFUTED"
    assert decide(given, fact("sertraline")).blockers == ()
    assert decide(given, fact("adult")).blockers == ()
    result = run(
        {
            "operation": "entailment",
            "assertions": [json.loads(canonical(item)) for item in given],
            "query": json.loads(canonical(fact("adult"))),
        }
    )
    assert result["code"] == "complete"
    assert result["result"]["decision"]["proof"] == ("adult",)
    assert any(
        row["body"] == json.loads(canonical(fact("renal")))
        for row in result["result"]["explanations"]["conditions"]
    )


def test_real_scope_dependency_and_indirect_dependency_stay_open():
    staged = requirement("stage", fact("response"), cohort=Scope("cohort_ref", "C"))
    assert decide((staged,), fact("response")).blockers == (
        "open_scope:cohort_ref:C",
        "undecided_by_constraints",
    )
    linked = requirement("link", AnyOf((Not(fact("response")), fact("ready"))))
    assert "open_scope:cohort_ref:C" in decide((staged, linked), fact("ready")).blockers
    assert decide((staged,), fact("response"), Context(cohort="C")).result == "ENTAILED"
    assert decide((staged,), fact("response"), Context(cohort="B")).result == "OUT_OF_SCOPE"


def test_proof_excludes_redundant_scope_even_for_same_predicate():
    global_rule = requirement("global", fact("response"))
    scoped_rule = requirement("scoped", fact("response"), cohort=Scope("cohort_ref", "C"))
    decision = decide((global_rule, scoped_rule), fact("response"))
    assert (decision.result, decision.proof, decision.blockers) == ("ENTAILED", ("global",), ())


def test_disconnected_contradiction_remains_global_and_proposals_remain_visible():
    given = (
        requirement("entry", fact("adult")),
        requirement("bad", AllOf((fact("other"), Not(fact("other"))))),
    )
    assert decide(given, fact("adult")).result == "INCONSISTENT"
    proposal = dataclasses.replace(requirement("proposal", fact("unrelated")), status="proposed")
    assert decide((given[0], proposal), fact("adult")).blockers == ("proposed_refused:proposal",)


def test_negative_witness_must_not_ignore_unrelated_open_scope():
    given = (
        requirement("adult", fact("adult")),
        requirement("stage", fact("response"), cohort=Scope("cohort_ref", "C")),
    )
    assert decide(given, fact("adult")).blockers == ()
    assert eligibility_witness(given, fact("adult"), direction="rejected").blockers == (
        "open_scope:cohort_ref:C",
    )


def test_scope_routing_classifier_keeps_other_blockers_and_proof_scope():
    assert scope_blocker_code("open_scope:cohort_ref:C", "REFUTED", True, False) == "unrelated_scope"
    assert scope_blocker_code("open_scope:cohort_ref:C", "ENTAILED", False, True) == "retain"
    assert scope_blocker_code("open_scope:cohort_ref:C", "UNDETERMINED", True, False) == "retain"
    assert scope_blocker_code("open_scope:cohort_ref:C", "UNDETERMINED", False, False) == "unrelated_scope"
    assert scope_blocker_code("proposed_refused:x", "ENTAILED", False, False) == "retain"
    assert scope_blocker_code("resource_bound", "INCONSISTENT", False, False) == "retain"
    assert scope_blocker_code("open_scope:cohort_ref:C", "INCONSISTENT", False, False) == "unrelated_scope"
    assert scope_blocker_code("open_scope:cohort_ref:C", "REFUTED", False, True) == "retain"
    assert scope_blocker_code("open_scope:cohort_ref:C", "UNDETERMINED", False, True) == "retain"


def test_silent_draft_is_a_missing_design_choice_not_missing_historical_evidence():
    from copy import deepcopy

    from TrialLedger.layer2.design_session_guide import EXAMPLE

    request = deepcopy(EXAMPLE)
    request["session"]["premises"] = []
    for analysis in request["session"]["analyses"]:
        analysis["uses"] = []
    result = run(request)
    decision = result["result"]["decisions"][0]
    assert decision["code"] == "unrepresented_design_question"
    assert all(option["code"] == "evidence_question" for option in decision["alternatives"])
    assert not decision["distinctions"]


def test_equivalent_profiles_are_not_a_fabricated_design_choice():
    from TrialLedger.layer2.design_session import _question

    alternatives = [{"id": "A", "code": "feasible"}, {"id": "B", "code": "feasible"}]
    assert _question("new_trial", alternatives, None, False) == "options_not_distinguished"
    assert _question("new_trial", alternatives, None, True) == "design_choice"
