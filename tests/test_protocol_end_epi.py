"""Acceptance cases END-1, END-2, END-3 and EPI-3 for the protocol workflow (all values invented).

Every test goes through the public path: `TrialLedger.layer2.run` on a v2 `design_session` request. No
clinical value here is a real trial claim; ids and basis strings say so.
"""

import copy

import pytest

from tests.test_protocol_session_replay import _session, adopt
from tests.test_protocol_walkthrough_repairs import _estimand_with_linked_collection
from TrialLedger.layer2 import run, source_evidence

OBSERVED, IMPUTED, DERIVED = "observed", "imputed", "derived"


def _m(identity: str, mode: str) -> dict:
    return {"id": identity, "mode": mode}


# ---------------------------------------------------------------------------------------------------------
# Dependency (change-score) sessions
# ---------------------------------------------------------------------------------------------------------
def _dependencies(**overrides) -> dict:
    """An invented change-score rule: change = baseline AND week12, both observed, adopted by id."""
    data = {
        "scope": "user:invented cohort and window",
        "version": "1",
        "rules": [
            {
                "id": "change",
                "version": "invented-definition-1",
                "output": _m("change", DERIVED),
                "alternatives": [[_m("baseline", OBSERVED), _m("week12", OBSERVED)]],
                "when": [],
            }
        ],
        "adopted": ["change"],
        "available": [_m("baseline", OBSERVED), _m("week12", OBSERVED)],
        "unavailable": [],
        "conditions": {},
    }
    data.update(overrides)
    return data


def _dependency_session(dependencies: dict, adopted: bool = True) -> dict:
    request = _session("84", collection_status="known")
    protocol = request["session"]["protocol"]
    template = protocol["objects"][0]
    endpoint = copy.deepcopy(template)
    endpoint.update(
        id="change-endpoint",
        kind="endpoint",
        depends_on=["score"],
        support=[],
        data={
            "variable": "score",
            "definition": copy.deepcopy(template["data"]["definition"]),
            "estimand": None,
            "dependencies": dependencies,
        },
    )
    protocol["objects"].append(endpoint)
    if adopted:
        adopt(request, "change-endpoint")
    check = copy.deepcopy(protocol["checks"][0])
    check.update(id="dep-check", kind="dependencies", objects=["change-endpoint"], claims=[])
    protocol["checks"] = [check]
    protocol["sections"] = []
    return request


def _check(reply: dict) -> dict:
    assert reply["code"] == "complete", reply["problems"]
    return reply["result"]["protocol"]["checks"][0]


def _signal(reply: dict) -> dict:
    child = _check(reply)["children"][0]
    return child["result"]["result"]["signals"][0]


def _states(signal: dict) -> dict:
    """The one rule row: state, missing inputs, and each alternative's per-input state."""
    (row,) = signal["value"]["rules"]
    return row


def _derived_available(signal: dict) -> bool:
    return _m("change", DERIVED) in signal["value"]["available"]


# ---------------------------------------------------------------------------------------------------------
# END-1: an adopted change score needs a declared baseline and follow-up in the right mode
# ---------------------------------------------------------------------------------------------------------
def test_end1_declared_observed_baseline_and_followup_make_the_adopted_change_score_ready():
    signal = _signal(run(_dependency_session(_dependencies())))
    row = _states(signal)
    assert (signal["code"], row["state"], row["missing"], signal["blockers"]) == (
        "consistent",
        "ready",
        [],
        [],
    )
    assert [(i["id"], i["mode"], i["state"]) for i in row["alternatives"][0]] == [
        ("baseline", OBSERVED, "available"),
        ("week12", OBSERVED, "available"),
    ]
    assert _derived_available(signal)
    assert (signal["admission"]["code"], signal["status"]) == ("accepted", "known")


def test_end1_an_undeclared_baseline_is_not_derived_and_the_score_stays_unresolved():
    signal = _signal(run(_dependency_session(_dependencies(available=[_m("week12", OBSERVED)]))))
    row = _states(signal)
    assert signal["code"] == "unresolved"
    assert signal["blockers"] == ["dependency_unresolved:change"]
    assert (row["state"], row["missing"]) == ("unresolved", ["baseline:observed"])
    assert [(i["id"], i["state"]) for i in row["alternatives"][0]] == [
        ("baseline", "unknown"),
        ("week12", "available"),
    ]
    assert not _derived_available(signal)
    assert signal["value"]["available"] == [_m("week12", OBSERVED)]


@pytest.mark.parametrize("mode", [IMPUTED, DERIVED])
def test_end1_a_baseline_in_the_wrong_mode_does_not_pass_as_an_observation(mode):
    dependencies = _dependencies(available=[_m("baseline", mode), _m("week12", OBSERVED)])
    signal = _signal(run(_dependency_session(dependencies)))
    row = _states(signal)
    assert (signal["code"], row["state"], row["missing"]) == (
        "unresolved",
        "unresolved",
        ["baseline:observed"],
    )
    assert [(i["id"], i["mode"], i["state"]) for i in row["alternatives"][0]][0] == (
        "baseline",
        OBSERVED,
        "unknown",
    )
    assert not _derived_available(signal)
    # The declared mode is retained as declared; nothing rewrites it to an observation.
    assert _m("baseline", mode) in signal["value"]["available"]
    assert _m("baseline", OBSERVED) not in signal["value"]["available"]


def test_end1_a_followup_in_the_wrong_mode_does_not_pass_as_an_observation():
    dependencies = _dependencies(available=[_m("baseline", OBSERVED), _m("week12", IMPUTED)])
    signal = _signal(run(_dependency_session(dependencies)))
    assert (signal["code"], _states(signal)["missing"]) == ("unresolved", ["week12:observed"])
    assert not _derived_available(signal)
    assert _m("week12", OBSERVED) not in signal["value"]["available"]


def test_end1_an_explicitly_unavailable_observed_baseline_blocks_even_with_an_imputed_one_declared():
    dependencies = _dependencies(
        available=[_m("baseline", IMPUTED), _m("week12", OBSERVED)],
        unavailable=[_m("baseline", OBSERVED)],
    )
    signal = _signal(run(_dependency_session(dependencies)))
    assert (signal["code"], _states(signal)["state"]) == ("conflict", "blocked")
    assert signal["blockers"] == ["dependency_blocked:change"]
    assert not _derived_available(signal)
    assert _m("baseline", IMPUTED) in signal["value"]["available"]


@pytest.mark.parametrize("mode", [OBSERVED, IMPUTED])
def test_end1_a_calculation_rule_cannot_output_an_observed_or_imputed_measurement(mode):
    dependencies = _dependencies()
    dependencies["rules"][0]["output"] = _m("change", mode)
    reply = run(_dependency_session(dependencies))
    child = _check(reply)["children"][0]
    assert child["result"]["code"] == "refused"
    assert child["result"]["problems"] == ["rule_output_not_derived"]
    assert child["result"]["result"] is None


def test_end1_measurement_objects_declaring_a_baseline_and_observed_mode_declare_no_availability():
    request = _dependency_session(_dependencies(available=[_m("week12", OBSERVED)]))
    protocol = request["session"]["protocol"]
    baseline = copy.deepcopy(protocol["objects"][0])
    baseline.update(id="baseline-measurement", support=[], depends_on=[])
    protocol["objects"].append(baseline)
    adopt(request, "baseline-measurement")
    score = next(o for o in protocol["objects"] if o["id"] == "score")
    score["data"]["baseline"] = "baseline-measurement"
    score["depends_on"] = ["baseline-measurement"]
    # Control: the ledger really carries an adopted, observed baseline measurement beside the endpoint.
    assert (baseline["data"]["mode"], score["data"]["baseline"]) == (OBSERVED, "baseline-measurement")
    signal = _signal(run(request))
    assert (signal["code"], _states(signal)["missing"]) == ("unresolved", ["baseline:observed"])
    assert not _derived_available(signal)


# ---------------------------------------------------------------------------------------------------------
# END-2: OR-of-AND alternatives and explicit adoption; no strategy-name collection rule
# ---------------------------------------------------------------------------------------------------------
def _or_of_and(available, unavailable=()) -> dict:
    dependencies = _dependencies(available=list(available), unavailable=list(unavailable))
    dependencies["rules"][0]["alternatives"] = [
        [_m("a", OBSERVED), _m("b", OBSERVED)],
        [_m("c", OBSERVED)],
    ]
    return dependencies


@pytest.mark.parametrize(
    ("name", "available", "unavailable", "code", "state"),
    [
        # Flattening to OR would make `a` alone sufficient; flattening to AND would demand `c` as well.
        ("a-alone-is-half-an-AND", [_m("a", OBSERVED)], [], "unresolved", "unresolved"),
        ("c-alone-satisfies-the-OR", [_m("c", OBSERVED)], [], "consistent", "ready"),
        ("a-and-b-satisfy-the-first-AND", [_m("a", OBSERVED), _m("b", OBSERVED)], [], "consistent", "ready"),
        (
            "one-blocked-one-unknown-stays-open",
            [_m("a", OBSERVED)],
            [_m("b", OBSERVED)],
            "unresolved",
            "unresolved",
        ),
        ("every-alternative-blocked", [], [_m("b", OBSERVED), _m("c", OBSERVED)], "conflict", "blocked"),
    ],
)
def test_end2_alternatives_keep_their_or_of_and_structure(name, available, unavailable, code, state):
    signal = _signal(run(_dependency_session(_or_of_and(available, unavailable))))
    assert (signal["code"], _states(signal)["state"]) == (code, state), name
    assert _derived_available(signal) is (state == "ready"), name


def test_end2_the_projected_request_carries_the_declared_alternatives_unchanged():
    dependencies = _or_of_and([_m("c", OBSERVED)])
    declared = copy.deepcopy(dependencies["rules"][0]["alternatives"])
    child = _check(run(_dependency_session(dependencies)))["children"][0]
    projected = child["request"]["signals"][0]["data"]["rules"][0]["alternatives"]
    assert projected == declared
    assert [len(group) for group in projected] == [2, 1]


def test_end2_an_unadopted_rule_imposes_nothing_and_derives_nothing():
    unadopted = _dependencies(adopted=[], available=[_m("baseline", OBSERVED), _m("week12", OBSERVED)])
    signal = _signal(run(_dependency_session(unadopted)))
    assert signal["value"]["rules"] == [] and signal["blockers"] == []
    # Every prerequisite is present, yet no rule is adopted automatically.
    assert not _derived_available(signal)
    # Control: the same rule named in `adopted` is evaluated and derives the output.
    adopted = _dependencies(available=[_m("baseline", OBSERVED), _m("week12", OBSERVED)])
    assert _derived_available(_signal(run(_dependency_session(adopted))))
    # Control: an unadopted rule with missing inputs raises no requirement either.
    missing = _dependencies(adopted=[], available=[])
    assert _signal(run(_dependency_session(missing)))["blockers"] == []
    assert _signal(run(_dependency_session(_dependencies(available=[]))))["blockers"] == [
        "dependency_unresolved:change"
    ]


def test_end2_an_unadopted_endpoint_object_is_not_applied_as_a_decided_dependency():
    unadopted = _signal(run(_dependency_session(_dependencies(), adopted=False)))
    assert (unadopted["code"], unadopted["admission"]["code"]) == ("unresolved", "binding_unresolved")
    entry = next(e for e in unadopted["support"] if e["id"] == "adoption:change-endpoint")
    assert entry["resolution"] == "unresolved"
    adopted = _signal(run(_dependency_session(_dependencies())))
    assert (adopted["code"], adopted["admission"]["code"]) == ("consistent", "accepted")


STRATEGIES = (
    "treatment_policy",
    "hypothetical",
    "composite",
    "while_on_treatment",
    "principal_stratum",
    "unresolved",
)


def _object(request: dict, identity: str) -> dict:
    return next(o for o in request["session"]["protocol"]["objects"] if o["id"] == identity)


def _estimand_signal(request: dict) -> dict:
    return _signal(run(request))


def _row(signal: dict) -> dict:
    (row,) = signal["value"]["requirements"]
    return row


def _estimand_session(action: str | None, strategy: str = "treatment_policy") -> dict:
    """An invented estimand with a required week-12 input; the collection declares `action`, or None."""
    request = _estimand_with_linked_collection("collect" if action is None else action)
    adopt(request, "collection")
    _object(request, "estimand")["data"]["events"][0]["strategy"] = strategy
    if action is None:
        _object(request, "collection")["data"]["event_handling"] = None
    return request


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_end2_a_strategy_name_never_becomes_a_collection_rule(strategy):
    request = _estimand_session(None, strategy)
    # Control: the strategy really is the declared one, and no plan is declared anywhere.
    assert _object(request, "estimand")["data"]["events"][0]["strategy"] == strategy
    assert _object(request, "estimand")["data"]["collection_plan"] == []
    reply = run(request)
    child = _check(reply)["children"][0]
    assert child["request"]["signals"][0]["data"]["collection_plan"] == []
    row = _row(_signal(reply))
    assert (row["collection_plan"], row["collection_alignment"]) == (None, "unresolved")
    assert not any(b.startswith("estimand_collection_plan_mismatch") for b in _signal(reply)["blockers"])


def test_end2_a_collection_plan_conflicting_with_the_estimand_is_named_and_not_overridden():
    request = _estimand_session("collect")
    _object(request, "estimand")["data"]["collection_plan"] = [
        {
            "requirement": "week12",
            "action": "stop",
            "status": "known",
            "resolution": "resolved",
            "basis": ["user:invented estimand-side plan"],
        }
    ]
    check = _check(run(request))
    assert check["children"] == []
    assert check["unresolved"] == [
        {"code": "projection_collection_plan_conflict", "objects": ["estimand", "collection"], "premises": []}
    ]


def test_end2_an_agreeing_estimand_side_plan_is_not_a_conflict():
    request = _estimand_session("stop")
    _object(request, "estimand")["data"]["collection_plan"] = [
        {
            "requirement": "week12",
            "action": "stop",
            "status": "known",
            "resolution": "resolved",
            "basis": ["user:invented estimand-side plan"],
        }
    ]
    check = _check(run(request))
    assert check["unresolved"] == [] and len(check["children"]) == 1


# ---------------------------------------------------------------------------------------------------------
# END-3: a required post-discontinuation input plus a stop plan is a named mismatch
# ---------------------------------------------------------------------------------------------------------
MISMATCH = "estimand_collection_plan_mismatch:week12"


def test_end3_a_required_input_with_a_stop_plan_is_a_named_mismatch_not_a_clinical_finding():
    signal = _estimand_signal(_estimand_session("stop"))
    row = _row(signal)
    assert _row(signal)["relevance"] == "required"
    assert (row["collection_plan"]["action"], row["collection_alignment"]) == (
        "stop",
        "collection_plan_mismatch",
    )
    assert row["collection_blockers"] == [MISMATCH] and MISMATCH in signal["blockers"]
    assert signal["code"] == "unresolved"  # a plan question, not a refutation of estimation
    assert (row["estimation"], signal["value"]["estimation"]) == ("not_computed", "not_computed")


def test_end3_a_collect_plan_for_the_same_requirement_is_aligned():
    signal = _estimand_signal(_estimand_session("collect"))
    row = _row(signal)
    assert (row["collection_plan"]["action"], row["collection_alignment"]) == ("collect", "aligned")
    assert MISMATCH not in signal["blockers"] and row["collection_blockers"] == []


def test_end3_the_mismatch_follows_the_declared_requirement_not_the_strategy_name():
    for strategy in STRATEGIES:
        stop = _estimand_signal(_estimand_session("stop", strategy))
        collect = _estimand_signal(_estimand_session("collect", strategy))
        assert MISMATCH in stop["blockers"], strategy
        assert MISMATCH not in collect["blockers"], strategy
    # Same strategy, same stop plan: only the declared relevance of the input removes the mismatch.
    request = _estimand_session("stop")
    _object(request, "estimand")["data"]["requirements"][0]["relevance"] = "not_required_for_this_estimand"
    signal = _estimand_signal(request)
    assert (_row(signal)["relevance"], _row(signal)["collection_alignment"]) == (
        "not_required_for_this_estimand",
        "aligned",
    )
    assert MISMATCH not in signal["blockers"]


@pytest.mark.parametrize("action", ["stop", "collect"])
def test_end3_a_plan_does_not_establish_whether_the_data_exist(action):
    signal = _estimand_signal(_estimand_session(action))
    row = _row(signal)
    assert row["collection_plan"]["action"] == action
    assert (row["data_state"], row["recorded_state"], row["actual_input"]) == ([], "unknown", "unresolved")
    assert signal["value"]["data_state"] == []


def _with_data_state(action: str, state: str) -> dict:
    request = _estimand_session(action)
    rule = {
        "ref": "user:invented data-state rule",
        "version": "1",
        "status": "known",
        "resolution": "resolved",
        "basis": ["user:invented data-state rule"],
    }
    _object(request, "estimand")["data"]["data_state"] = [
        {"requirement": "week12", "mode": OBSERVED, "state": state, "rule": rule}
    ]
    return request


def test_end3_declared_data_and_the_stop_plan_remain_separate_channels():
    stopped_but_present = _row(_estimand_signal(_with_data_state("stop", "available")))
    assert (stopped_but_present["actual_input"], stopped_but_present["collection_alignment"]) == (
        "available",
        "collection_plan_mismatch",
    )
    collected_but_absent = _estimand_signal(_with_data_state("collect", "unavailable"))
    row = _row(collected_but_absent)
    assert (row["actual_input"], row["collection_alignment"]) == ("missing_relevant", "aligned")
    assert "estimand_missing_relevant:week12" in collected_but_absent["blockers"]
    assert MISMATCH not in collected_but_absent["blockers"]


def test_end3_an_unadopted_collection_plan_is_not_applied_as_a_decided_plan():
    request = _estimand_session("stop")
    request["session"]["premises"] = [
        p for p in request["session"]["premises"] if p["id"] != "adopt:collection:invented-v1"
    ]
    _object(request, "collection")["support"] = []
    signal = _estimand_signal(request)
    assert signal["admission"]["code"] == "binding_unresolved"
    adopted = _estimand_signal(_estimand_session("stop"))
    assert adopted["admission"]["code"] == "accepted"


# ---------------------------------------------------------------------------------------------------------
# EPI-3: source rule, accepted interpretation and simulated choice keep distinct origins
# ---------------------------------------------------------------------------------------------------------
STUDY = {
    "protocolSection": {
        "identificationModule": {"nctId": "NCT00000001"},
        "eligibilityModule": {"minimumAge": "18 Years"},
    }
}
SNAPSHOT = source_evidence.snapshot(STUDY)
ADDRESS = "/protocolSection/eligibilityModule/minimumAge"
COPIED_ADDRESS = SNAPSHOT["study_ref"] + "#" + ADDRESS


def _origin_session(kind: str, standing: str, adoption: tuple[str, str] | None) -> dict:
    """The change-score endpoint under one origin kind, one declared standing and one adoption record."""
    request = _dependency_session(_dependencies(), adopted=False)
    session = request["session"]
    endpoint = _object(request, "change-endpoint")
    if kind == "source_interpretation":
        session["sources"].append(
            {"id": "registry", "study": copy.deepcopy(STUDY), "expected_digest": SNAPSHOT["digest"]}
        )
        endpoint["origin"] = {"kind": kind, "ref": COPIED_ADDRESS, "source": "registry", "analysis": None}
    elif kind == "hypothesis":
        endpoint["origin"] = {
            "kind": kind,
            "ref": "user:invented simulation",
            "source": None,
            "analysis": None,
        }
    endpoint["standing"] = {
        "status": standing,
        "resolution": "resolved" if standing == "known" else "unresolved",
        "basis": ["user:invented standing declaration"],
    }
    if adoption is not None:
        adopt(request, "change-endpoint", *adoption)
    return request


def _admission(reply: dict) -> tuple:
    signal = _signal(reply)
    return signal["code"], signal["status"], signal["admission"]["code"]


def test_epi3_a_copied_source_address_alone_is_a_reading_not_registry_truth():
    # The address resolves in the retained study, and the study is returned byte-for-byte unchanged.
    for standing in ("proposed", "known"):
        reply = run(_origin_session("source_interpretation", standing, None))
        assert reply["code"] == "complete", reply["problems"]
        returned = _object_in(reply, "change-endpoint")
        assert returned["origin"]["kind"] == "source_interpretation"
        assert returned["origin"]["ref"] == COPIED_ADDRESS
        assert reply["result"]["sources"][0]["study"] == STUDY
        signal = _signal(reply)
        # Neither the copied address nor even a caller-declared known standing applies the dependency.
        assert signal["code"] == "unresolved", standing
        assert signal["admission"]["code"] in ("proposed_refused", "binding_unresolved"), standing
        entry = next(e for e in signal["support"] if e["id"] == "adoption:change-endpoint")
        assert entry["resolution"] == "unresolved", standing
        # No compiled source rule and no source-rule origin is manufactured from the copied address.
        assert "source_assertion" not in {p["kind"] for p in reply["result"]["effective_premises"]}
        assert all(p["origin"]["kind"] == "user_choice" for p in reply["result"]["effective_premises"])


def _object_in(reply: dict, identity: str) -> dict:
    return next(o for o in reply["result"]["protocol"]["objects"] if o["id"] == identity)


def test_epi3_a_proposed_source_reading_is_withheld_while_its_accepted_twin_is_applied():
    proposed = _admission(run(_origin_session("source_interpretation", "proposed", None)))
    assert proposed == ("unresolved", "proposed", "proposed_refused")
    accepted_reply = run(_origin_session("source_interpretation", "known", ("known", "resolved")))
    assert _admission(accepted_reply) == ("consistent", "known", "accepted")


def test_epi3_acceptance_is_a_user_choice_beside_a_source_interpretation_object():
    reply = run(_origin_session("source_interpretation", "known", ("known", "resolved")))
    endpoint = _object_in(reply, "change-endpoint")
    # The object keeps its source-interpretation origin; approval does not recast it.
    assert endpoint["origin"] == {
        "kind": "source_interpretation",
        "ref": COPIED_ADDRESS,
        "source": "registry",
        "analysis": None,
    }
    premises = {p["id"]: p for p in reply["result"]["effective_premises"]}
    approval = premises["adopt:change-endpoint:invented-v1"]
    assert approval["origin"]["kind"] == "user_choice" and approval["origin"]["source"] is None
    assert (approval["standing"]["status"], approval["payload"]["objects"]) == (
        "known",
        [{"id": "change-endpoint", "version": "invented-v1"}],
    )
    assert reply["result"]["sources"][0]["study"] == STUDY
    assert not [
        p for p in premises.values() if p["origin"]["kind"] in ("source_rule", "source_interpretation")
    ]


def test_epi3_user_approval_does_not_promote_an_object_whose_own_standing_is_proposed():
    reply = run(_origin_session("source_interpretation", "proposed", ("known", "resolved")))
    assert _admission(reply) == ("unresolved", "proposed", "proposed_refused")
    standings = {e["id"]: e["status"] for e in _signal(reply)["support"]}
    assert standings["object:change-endpoint"] == "proposed"
    assert standings["premise:adopt:change-endpoint:invented-v1"] == "known"


def test_epi3_a_simulated_choice_stays_hypothetical_even_when_approved_as_known():
    for adoption in (("proposed", "unresolved"), ("known", "resolved")):
        reply = run(_origin_session("hypothesis", "proposed", adoption))
        assert _object_in(reply, "change-endpoint")["origin"]["kind"] == "hypothesis"
        assert _admission(reply) == ("unresolved", "proposed", "proposed_refused"), adoption
    # It is neither a source reading nor a user fact: no source is attached and none is invented.
    assert _object_in(reply, "change-endpoint")["origin"]["source"] is None
    assert reply["result"]["sources"] == []


def test_epi3_the_three_origins_remain_distinct_in_the_returned_ledger():
    kinds = {
        "source": _object_in(
            run(_origin_session("source_interpretation", "proposed", None)), "change-endpoint"
        ),
        "accepted": _object_in(
            run(_origin_session("source_interpretation", "known", ("known", "resolved"))), "change-endpoint"
        ),
        "simulated": _object_in(
            run(_origin_session("hypothesis", "proposed", ("proposed", "unresolved"))), "change-endpoint"
        ),
    }
    assert kinds["source"]["origin"]["kind"] == kinds["accepted"]["origin"]["kind"] == "source_interpretation"
    assert kinds["simulated"]["origin"]["kind"] == "hypothesis"
    assert kinds["source"]["support"] == [] and kinds["accepted"]["support"] == [
        "adopt:change-endpoint:invented-v1"
    ]
    assert kinds["source"]["standing"]["status"] == kinds["simulated"]["standing"]["status"] == "proposed"
    assert kinds["accepted"]["standing"]["status"] == "known"


@pytest.mark.parametrize(
    ("mutate", "problem"),
    [
        (lambda o: o["origin"].update(kind="source_rule"), "protocol_origin_kind"),
        (lambda o: o["origin"].update(kind="derived"), "protocol_origin_kind"),
        (
            lambda o: o["origin"].update(ref="ctg:NCT00000001:invented-digest#" + ADDRESS),
            "protocol_origin_digest",
        ),
        (
            lambda o: o["origin"].update(ref=SNAPSHOT["study_ref"] + "#/protocolSection/notThere"),
            "protocol_origin_pointer",
        ),
        (lambda o: o["origin"].update(kind="hypothesis"), "protocol_origin_source"),
    ],
)
def test_epi3_a_protocol_object_cannot_claim_a_registry_origin_or_a_dangling_address(mutate, problem):
    request = _origin_session("source_interpretation", "known", ("known", "resolved"))
    mutate(_object(request, "change-endpoint"))
    reply = run(request)
    assert (reply["code"], reply["problems"]) == ("refused", [problem])


@pytest.mark.parametrize("kind", ["hypothesis", "source_interpretation"])
def test_epi3_only_a_user_choice_can_adopt_a_protocol_object(kind):
    request = _origin_session("source_interpretation", "known", ("known", "resolved"))
    approval = next(
        p for p in request["session"]["premises"] if p["id"] == "adopt:change-endpoint:invented-v1"
    )
    approval["origin"] = {
        "kind": kind,
        "ref": COPIED_ADDRESS if kind == "source_interpretation" else "user:x",
        "source": "registry" if kind == "source_interpretation" else None,
        "analysis": None,
    }
    reply = run(request)
    assert (reply["code"], reply["problems"]) == ("refused", ["adoption_requires_user_choice"])
