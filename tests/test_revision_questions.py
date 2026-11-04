"""Revision axes over invented premises: no clinical claim or real confirmation."""

import json
from copy import deepcopy

import pytest

from tests.test_clinical_answers import session_decision
from tests.test_session_revision_delivery import request
from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import design_session as session
from TrialLedger.layer2.clinical_answers import change_projection


def quantity(days, comparison="ge"):
    return json.loads(
        a.canonical(
            a.Literal(
                a.Subject("participant"),
                a.Predicate("measurement", "washout_days"),
                a.Value("quantity", number=days, unit="days", comparison=comparison, inclusivity="inclusive"),
            )
        )
    )


def numeric_request():
    first = request()
    first["session"]["premises"][0]["payload"]["body"] = quantity(90)
    first["session"]["analyses"][0]["parameters"]["query"] = quantity(60, "eq")
    return first


def revise(first, change):
    response = session.run(first)
    following = deepcopy(first["session"])
    following["revision"] = "two"
    change(following)
    return session.run(session.prepare_revision(first, response, following))


def test_same_id_changed_rule_body_changes_support_even_when_both_refute_sixty_days():
    revised = revise(numeric_request(), lambda s: s["premises"][0]["payload"].update(body=quantity(180)))
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "support_changed"
    assert row["changes"] == ["support"]
    assert row["before"]["answer"][0]["outcome"] == row["after"]["answer"][0]["outcome"] == "REFUTED"
    versions = row["after"]["support"][0]["premise_versions"]
    assert versions[0]["value"]["payload"]["body"]["value"]["number"] == 180
    assert revised["diff"]["premises"][0]["code"] == "changed"


def test_sharpened_question_with_same_verdict_is_not_a_clinical_verdict_change():
    first = numeric_request()
    first["session"]["analyses"][0]["parameters"]["query"] = quantity(120, "eq")
    revised = revise(first, lambda s: s["analyses"][0]["parameters"].update(query=quantity(150, "eq")))
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "question_changed"
    assert row["axes"]["question"] == "changed"
    assert row["axes"]["answer"] == "unchanged"
    assert row["before"]["answer"][0]["outcome"] == row["after"]["answer"][0]["outcome"] == "UNDETERMINED"


def test_same_question_with_changed_verdict_retains_answer_change():
    revised = revise(numeric_request(), lambda s: s["premises"][0]["payload"].update(body=quantity(30)))
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "answer_changed"
    assert row["axes"]["question"] == "unchanged"
    assert row["axes"]["answer"] == "changed"
    assert "support" in row["changes"]


def test_unrelated_rule_body_change_does_not_contaminate_deciding_support():
    first = numeric_request()
    irrelevant = request()["session"]["premises"][0]
    irrelevant["id"] = irrelevant["payload"]["id"] = "other"
    first["session"]["premises"].append(irrelevant)
    first["session"]["analyses"][0]["uses"].append(
        {"premise": "other", "slot": "assertions", "projection": "identity"}
    )
    revised = revise(first, lambda s: s["premises"][1]["payload"]["body"]["predicate"].update(key="B"))
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "input_only"
    assert row["changes"] == []


def test_decision_wording_is_not_a_semantic_question_or_answer_change():
    before = {"decisions": [session_decision()]}
    after = deepcopy(before)
    after["decisions"][0]["question"] = "A differently worded clinical question"
    after["decisions"][0]["alternatives"][0]["label"] = "A renamed option"
    old, new = (change_projection("design_session", item) for item in (before, after))
    assert old["wording"] != new["wording"]
    for axis in ("question", "answer", "support", "origin", "context"):
        assert old[axis] == new[axis]


def test_copied_context_is_not_a_logical_answer_or_deciding_premise():
    before = {"decisions": [session_decision()]}
    after = deepcopy(before)
    after["decisions"][0]["evidence"] = [{"role": "gap", "note": "Registry silence"}]
    old, new = (change_projection("design_session", item) for item in (before, after))
    assert old["context"] != new["context"]
    for axis in ("question", "wording", "answer", "support", "origin"):
        assert old[axis] == new[axis]


def test_session_decision_context_change_has_its_own_remedy():
    before = {"analyses": [], "decisions": [session_decision()], "effective_premises": []}
    after = deepcopy(before)
    after["decisions"][0]["evidence"] = [{"role": "gap", "note": "Copied source silence"}]
    row = session._answer_diff(before, after)["decisions"][0]
    assert row["code"] == "context_changed"
    assert row["changes"] == ["context"]


def test_session_decision_wording_change_is_separate_from_declared_query():
    before = {"analyses": [], "decisions": [session_decision()], "effective_premises": []}
    after = deepcopy(before)
    after["decisions"][0]["question"] = "A caller's revised wording"
    row = session._answer_diff(before, after)["decisions"][0]
    assert row["code"] == "wording_changed"
    assert row["changes"] == ["wording"]


def test_target_scope_change_remains_a_changed_question_with_unchanged_verdict():
    first = numeric_request()

    def change_scope(s):
        s["target"]["scope"]["arm"] = "cohort-B"
        s["analyses"][0]["target"]["scope"]["arm"] = "cohort-B"

    revised = revise(first, change_scope)
    row = revised["answer_diff"]["analyses"][0]
    assert row["code"] == "question_changed"
    assert row["axes"]["answer"] == "unchanged"


@pytest.mark.parametrize(
    "flags,expected",
    [
        ((False, True, False, False, False, False, False, False, False, False), "new"),
        ((True, False, False, False, False, False, False, False, False, False), "withdrawn"),
        ((True, True, False, True, True, True, True, True, True, True), "projection_unknown"),
        ((True, True, True, False, False, False, False, False, False, False), "question_changed"),
        ((True, True, True, True, False, False, False, False, False, False), "answer_changed"),
        ((True, True, True, True, False, True, False, False, False, False), "support_changed"),
        ((True, True, True, True, False, True, True, False, False, False), "context_changed"),
        ((True, True, True, True, False, True, True, False, True, False), "wording_changed"),
        ((True, True, True, True, True, True, True, False, True, False), "origin_changed"),
        ((True, True, True, True, True, True, True, True, True, False), "input_only"),
        ((True, True, True, True, True, True, True, True, True, True), "unchanged"),
    ],
)
def test_revision_change_code_names_each_independent_remedy(flags, expected):
    assert session.revision_change_code(*flags) == expected


def test_changed_question_must_not_claim_same_question_answer_changed():
    assert (
        session.revision_change_code(True, True, True, False, True, False, True, True, True, True)
        == "question_changed"
    )


def test_context_must_not_be_buried_as_input_only_or_promoted_to_support():
    assert (
        session.revision_change_code(True, True, True, True, True, True, True, True, False, False)
        == "context_changed"
    )


def test_wording_must_not_certify_typed_question_equivalence_or_a_new_verdict():
    assert (
        session.revision_change_code(True, True, True, True, False, True, True, True, True, False)
        == "wording_changed"
    )


@pytest.mark.parametrize("basis", [None, [], {}, "unresolved"])
def test_unknown_support_shapes_remain_inspectable_without_inventing_premise_ids(basis):
    axes = change_projection("future_operation", {"basis": basis, "proof": None})
    assert axes["support"][0]["premise_versions"] == []
    assert axes["answer"][0]["values"]["unclassified"] == {"basis": basis, "proof": None}
