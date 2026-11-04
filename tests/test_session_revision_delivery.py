"""Public revision preparation preserves declared clinical content and documentary identity.

All premises below are invented Boolean fixtures, not clinical records or actual confirmations.
"""

from copy import deepcopy

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import design_session as session
from TrialLedger.layer2 import session_state as state


def request():
    target = {
        "kind": "new_trial",
        "ref": "invented-draft",
        "scope": {
            "study": "invented-draft",
            "population": "general",
            "arm": "all",
            "time": "entry",
            "version": "one",
        },
    }
    literal = a.Literal(a.Subject("participant"), a.Predicate("measurement", "A"), a.Value("boolean"))
    premise = a.ScopedAssertion(
        "A",
        "invented:user:A",
        "required",
        literal,
        rule=a.Rule("invented-declared", "1"),
        status="known",
        resolution="resolved",
    )
    import json

    return {
        "operation": "design_session",
        "session": {
            "schema_version": 1,
            "id": "invented-session",
            "revision": "one",
            "parent_digest": None,
            "target": target,
            "sources": [],
            "premises": [
                {
                    "id": "A",
                    "kind": "assertion",
                    "payload": json.loads(a.canonical(premise)),
                    "origin": {
                        "kind": "user_choice",
                        "ref": "invented-not-a-real-exchange",
                        "source": None,
                        "analysis": None,
                    },
                    "depends_on": [],
                }
            ],
            "analyses": [
                {
                    "id": "A-check",
                    "operation": "entailment",
                    "target": deepcopy(target),
                    "parameters": {"query": json.loads(a.canonical(literal))},
                    "uses": [{"premise": "A", "slot": "assertions", "projection": "identity"}],
                }
            ],
            "decisions": [],
            "limits": dict(state.HARD_LIMITS),
        },
        "previous": None,
    }


def test_result_digest_covers_the_result_not_the_envelope():
    result = session.run(request())
    assert result["result_digest"] == state.digest(result["result"])
    assert result["result_digest"] != state.digest(result)


def test_public_revision_builder_fills_only_mechanical_parent_and_result_fields():
    previous_request = request()
    previous_response = session.run(previous_request)
    next_session = deepcopy(previous_request["session"])
    next_session["revision"] = "two"
    next_session["premises"][0]["origin"]["ref"] = "invented-explicit-revision-origin"
    before = deepcopy((previous_request, previous_response, next_session))
    revision = session.prepare_revision(previous_request, previous_response, next_session)
    expected = deepcopy(next_session)
    expected["parent_digest"] = previous_response["result"]["session_digest"]
    assert revision["session"] == expected
    assert revision["previous"]["expected_result_digest"] == previous_response["result_digest"]
    assert (previous_request, previous_response, next_session) == before
    replayed = session.run(revision)
    assert replayed["previous_fresh"] == previous_response["result"]
    assert replayed["result"]["premises"][0]["origin"]["ref"] == "invented-explicit-revision-origin"


def test_missing_parent_is_a_mechanical_omission_not_an_omitted_clinical_field():
    first = request()
    result = session.run(first)
    next_session = deepcopy(first["session"])
    next_session["revision"] = "two"
    del next_session["parent_digest"]
    revision = session.prepare_revision(first, result, next_session)
    assert revision["session"]["parent_digest"] == result["result"]["session_digest"]
    del next_session["target"]
    with pytest.raises(ValueError, match="invalid_fields:session"):
        session.prepare_revision(first, result, next_session)


@pytest.mark.parametrize("field", ["session_id", "revision", "target", "session_digest"])
def test_conflicting_prior_identity_never_becomes_a_valid_revision(field):
    first = request()
    response = session.run(first)
    response["result"][field] = "inconsistent-identity"
    response["result_digest"] = state.digest(response["result"])
    following = deepcopy(first["session"])
    following["revision"] = "two"
    with pytest.raises(ValueError, match="previous_result_session_mismatch"):
        session.prepare_revision(first, response, following)


@pytest.mark.parametrize("value", [None, False, 0, "wrong", [], {}])
def test_wrong_or_absent_public_result_digest_is_refused(value):
    first = request()
    response = session.run(first)
    response["result_digest"] = value
    following = deepcopy(first["session"])
    following["revision"] = "two"
    with pytest.raises(ValueError, match="result_mismatch"):
        session.prepare_revision(first, response, following)


def test_explicit_conflicting_parent_is_never_silently_repaired():
    first = request()
    response = session.run(first)
    following = deepcopy(first["session"])
    following.update(revision="two", parent_digest="different-parent")
    with pytest.raises(ValueError, match="parent_mismatch"):
        session.prepare_revision(first, response, following)


@pytest.mark.parametrize("field,value", [("id", "other"), ("revision", "one")])
def test_a_revision_requires_the_same_session_and_a_new_revision(field, value):
    first = request()
    response = session.run(first)
    following = deepcopy(first["session"])
    following.update(revision="two")
    following[field] = value
    with pytest.raises(ValueError, match="invalid_session_revision_identity"):
        session.prepare_revision(first, response, following)


@pytest.mark.parametrize("bad", [None, False, [], "unparsed"])
def test_malformed_revision_carriers_never_produce_a_prepared_request(bad):
    first = request()
    response = session.run(first)
    following = deepcopy(first["session"])
    following["revision"] = "two"
    with pytest.raises(ValueError):
        session.prepare_revision(bad, response, following)
    with pytest.raises(ValueError):
        session.prepare_revision(first, bad, following)
    with pytest.raises(ValueError):
        session.prepare_revision(first, response, bad)


@pytest.mark.parametrize(
    "flags,expected",
    [
        ((True, True, True, True, True, True), "ready"),
        ((False, False, False, False, False, False), "invalid_previous_response"),
        ((True, False, False, False, False, False), "previous_result_session_mismatch"),
        ((True, True, False, False, False, False), "result_mismatch"),
        ((True, True, True, False, True, True), "invalid_session_revision_identity"),
        ((True, True, True, True, False, True), "invalid_session_revision_identity"),
        ((True, True, True, True, True, False), "parent_mismatch"),
    ],
)
def test_revision_integrity_returns_the_specific_remedy(flags, expected):
    assert session.revision_input_code(*flags) == expected


def test_resource_refusal_preserves_numbers_without_executing_the_refused_child():
    current = request()
    current["session"]["limits"]["max_solver_work"] = 1
    called = []
    with pytest.raises(session.SessionBudgetError) as raised:
        session.run(current, execute=lambda payload: called.append(payload))
    assert str(raised.value) == "resource_bound:session_solver_work"
    details = raised.value.diagnostics
    assert details["budget"]["solver_work_reserved"] > details["limits"]["max_solver_work"]
    assert details["request_reservation"] == details["budget"]["solver_work_reserved"]
    assert details["budget"]["analyses"] == 1
    assert called == []


def test_revision_compares_origin_without_turning_it_into_an_answer_change():
    first = request()
    response = session.run(first)
    following = deepcopy(first["session"])
    following["revision"] = "two"
    following["premises"][0]["origin"]["ref"] = "another-invented-exchange"
    revised = session.run(session.prepare_revision(first, response, following))
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "origin_changed"
    assert row["changes"] == ["origin"]
    assert row["axes"]["answer"] == "unchanged"
    assert revised["diff"]["premises"][0]["code"] == "changed"


def test_same_verdict_with_weaker_proof_is_a_support_change():
    first = request()
    response = session.run(first)
    following = deepcopy(first["session"])
    following["revision"] = "two"
    following["premises"][0]["payload"]["status"] = "interpolated"
    revised = session.run(session.prepare_revision(first, response, following))
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "support_changed"
    assert row["changes"] == ["support"]
    assert row["axes"]["answer"] == "unchanged"


def test_refused_child_stays_explicitly_not_comparable():
    first = request()

    def refuse(payload):
        return {
            "code": "refused",
            "operation": payload["operation"],
            "result": None,
            "problems": ["invented-unknown-code"],
        }

    response = session.run(first, execute=refuse)
    following = deepcopy(first["session"])
    following["revision"] = "two"
    revised = session.run(session.prepare_revision(first, response, following), execute=refuse)
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "projection_unknown"
    assert set(row["axes"].values()) == {"not_comparable"}
    assert row["before"]["refusal"] == ["invented-unknown-code"]


@pytest.mark.parametrize("bound", [None, False, True, 0, -1, 65537, "4096", [], {}])
def test_malformed_bound_never_receives_a_smaller_reservation(bound):
    payload = {"operation": "entailment", "assertions": [], "query": {}, "bound": bound}
    with pytest.raises(ValueError, match="invalid_resource_bound:session_child"):
        session._reserve(payload)


def test_fresh_previous_and_current_work_accumulate_under_one_guard():
    first = request()
    response = session.run(first)
    following = deepcopy(first["session"])
    following["revision"] = "two"
    following["limits"]["max_solver_work"] = response["work"]["solver_work_reserved"]
    revision = session.prepare_revision(first, response, following)
    with pytest.raises(session.SessionBudgetError) as raised:
        session.run(revision)
    assert raised.value.diagnostics["budget"]["analyses"] == 2
    assert raised.value.diagnostics["budget"]["solver_work_reserved"] == (
        2 * response["work"]["solver_work_reserved"]
    )


@pytest.mark.parametrize(
    "flags,expected",
    [
        ((False, True, False, False, False, False, False), "new"),
        ((True, False, False, False, False, False, False), "withdrawn"),
        ((True, True, False, True, True, True, True), "projection_unknown"),
        ((True, True, True, False, False, False, False), "answer_changed"),
        ((True, True, True, True, False, False, False), "support_changed"),
        ((True, True, True, True, True, False, False), "origin_changed"),
        ((True, True, True, True, True, True, False), "input_only"),
        ((True, True, True, True, True, True, True), "unchanged"),
    ],
)
def test_answer_change_classification_keeps_specific_remedies(flags, expected):
    assert session.answer_change_code(*flags) == expected
