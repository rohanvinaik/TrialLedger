"""Typed preparation is inspectable existing-model data, never clinical interpretation."""

from __future__ import annotations

import math

import pytest

from TrialLedger.layer2 import run
from TrialLedger.layer2.assertions import (
    ALWAYS,
    AllOf,
    AnyOf,
    Evidence,
    Literal,
    ModelError,
    Not,
    Predicate,
    Rule,
    Scope,
    ScopedAssertion,
    Subject,
    TemporalScope,
    Value,
    canonical,
    from_canonical,
)
from TrialLedger.layer2.construction import (
    enum_set_value,
    enum_value,
    expanded,
    literal,
    quantity,
    scoped_assertion,
)


def age(number=18, unit="years", comparison="ge"):
    return literal(
        subject=Subject("participant"),
        predicate=Predicate("demographic", "age"),
        value=quantity(number=number, comparison=comparison, unit=unit, inclusivity="inclusive"),
        polarity="positive",
        time=None,
        qualifiers=ALWAYS,
        evidence=(Evidence("record_field", "invented:brief/age"),),
    )


def statement(body, **changes):
    args = dict(
        id="adult",
        criterion_ref="invented:brief/age",
        modality="required",
        body=body,
        cohort=Scope("cohort_ref", "entry"),
        applicability=ALWAYS,
        rule=Rule("caller-reading", "1", warrants=("invented:brief",)),
    )
    args.update(changes)
    return scoped_assertion(**args)


def test_quantity_keeps_written_comparison_unit_boundary_subject_and_origin():
    proposition = age()
    explicit = Literal(
        Subject("participant"),
        Predicate("demographic", "age"),
        Value("quantity", comparison="ge", number=18, unit="years", inclusivity="inclusive"),
        evidence=(Evidence("record_field", "invented:brief/age"),),
    )
    assert proposition == explicit
    assert from_canonical(canonical(proposition)) == explicit
    output = expanded(proposition)
    assert output["value"]["comparison"] == "ge"
    assert output["value"]["unit"] == "years"
    assert output["value"]["inclusivity"] == "inclusive"
    assert output["subject"] == {"class": "Subject", "kind": "participant", "referent": ""}
    assert output["evidence"] == [{"class": "Evidence", "kind": "record_field", "ref": "invented:brief/age"}]


def test_explicit_scoped_assertion_defaults_to_unconfirmed_not_known():
    assertion = statement(age())
    assert assertion.status == "proposed" and assertion.resolution == "unresolved"
    assert assertion.cohort == Scope("cohort_ref", "entry")
    assert assertion.modality == "required" and assertion.criterion_ref == "invented:brief/age"
    output = expanded(assertion)
    assert output["rule"]["id"] == "caller-reading" and output["status"] == "proposed"
    result = run(
        {
            "operation": "entailment",
            "assertions": [output],
            "query": expanded(age()),
            "context": {"cohort": "entry"},
        }
    )
    assert result["code"] == "complete"
    assert result["result"]["decision"]["result"] == "UNDETERMINED"
    assert any(value.startswith("proposed_refused:") for value in result["result"]["decision"]["blockers"])


def test_enum_and_enum_set_do_not_collapse_one_of_into_all_of():
    one = enum_value(members=("exon19del", "L858R"), comparison="in")
    every = enum_set_value(members=("exon19del", "L858R"), comparison="in")
    assert one == Value("enum", comparison="in", members=("exon19del", "L858R"))
    assert every == Value("enum_set", comparison="in", members=("exon19del", "L858R"))
    assert expanded(one)["kind"] != expanded(every)["kind"]
    assert expanded(one)["members"] == expanded(every)["members"] == ["exon19del", "L858R"]


def test_boolean_structure_scope_time_force_and_standing_survive_expansion():
    window = TemporalScope(
        "before",
        "treatment_start",
        lower=0,
        upper=21,
        unit="days",
        inclusivity="inclusive",
        certainty="explicit",
    )
    timed = literal(
        subject=Subject("participant"),
        predicate=Predicate("procedure_event", "scan"),
        value=Value("boolean"),
        polarity="negative",
        time=window,
        qualifiers=age(),
        evidence=(),
    )
    body = AnyOf((timed, AllOf((age(), Not(age(65))))))
    assertion = statement(
        body,
        modality="excluded",
        cohort=Scope("arm_ref", "crossover"),
        status="interpolated",
        resolution="resolved",
    )
    output = expanded(assertion)
    assert from_canonical(canonical(assertion)) == assertion
    assert output["body"]["class"] == "AnyOf"
    assert output["body"]["parts"][1]["class"] == "AllOf"
    assert output["body"]["parts"][0]["time"]["anchor"] == "treatment_start"
    assert output["body"]["parts"][0]["polarity"] == "negative"
    assert output["cohort"]["ref"] == "crossover" and output["cohort"]["kind"] == "arm_ref"
    assert output["modality"] == "excluded" and output["status"] == "interpolated"


def test_constructed_and_explicit_requests_have_exactly_equal_answers():
    body = age()
    constructed = statement(body, status="known", resolution="resolved")
    explicit = ScopedAssertion(
        "adult",
        "invented:brief/age",
        "required",
        body,
        cohort=Scope("cohort_ref", "entry"),
        rule=Rule("caller-reading", "1", warrants=("invented:brief",)),
        status="known",
        resolution="resolved",
    )
    request = {
        "operation": "entailment",
        "assertions": [expanded(constructed)],
        "query": expanded(age(65)),
        "context": {"cohort": "entry"},
    }
    control = {**request, "assertions": [expanded(explicit)]}
    assert run(request) == run(control)
    assert run(request)["result"]["decision"]["result"] == "UNDETERMINED"
    assert run(request)["result"]["decision"]["blockers"] == ("undecided_by_constraints",)


def test_no_unit_conversion_or_scope_adoption_occurs():
    assert expanded(age(unit="months"))["value"]["unit"] == "months"
    assertion = statement(age(), status="known", resolution="resolved")
    result = run(
        {
            "operation": "entailment",
            "assertions": [expanded(assertion)],
            "query": expanded(age()),
            "context": {"cohort": "crossover"},
        }
    )
    assert result["result"]["decision"]["result"] == "OUT_OF_SCOPE"
    assert assertion.rule.id == "caller-reading"


@pytest.mark.parametrize("number", [True, False, math.nan, math.inf, "18", None])
def test_malformed_quantities_reuse_model_refusals(number):
    with pytest.raises(ModelError):
        quantity(number=number, comparison="ge", unit="years", inclusivity="inclusive")


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"comparison": []}, "comparison_not_text"),
        ({"comparison": "approximately"}, "comparison_not_for_value_kind"),
        ({"unit": None}, "unit_not_text"),
        ({"inclusivity": []}, "inclusivity_not_text"),
        ({"inclusivity": "probably"}, "inclusivity_outside_vocabulary"),
    ],
)
def test_quantity_shape_and_vocabulary_are_strict(changes, code):
    args = dict(number=18, comparison="ge", unit="years", inclusivity="inclusive")
    args.update(changes)
    with pytest.raises(ModelError, match=code):
        quantity(**args)


@pytest.mark.parametrize("members", [[], ["A"], (), ("",), (1,)])
def test_enum_members_remain_a_nonempty_immutable_tuple(members):
    with pytest.raises(ModelError):
        enum_value(members=members, comparison="in")


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"modality": []}, "modality_not_text"),
        ({"modality": "recommended"}, "modality_outside_vocabulary"),
        ({"status": []}, "status_not_text"),
        ({"status": "confirmed"}, "status_outside_vocabulary"),
        ({"resolution": []}, "resolution_not_text"),
        ({"cohort": None}, "assertion_field_not_its_class"),
        ({"rule": None}, "assertion_without_rule"),
    ],
)
def test_scope_force_and_admission_cannot_be_improvised(changes, code):
    with pytest.raises(ModelError, match=code):
        statement(age(), **changes)


def test_scope_and_origin_are_required_arguments():
    with pytest.raises(TypeError):
        scoped_assertion(id="x", criterion_ref="invented:x", modality="required", body=age())


@pytest.mark.parametrize("item", ["Adults may enroll", None, True, {}, [1]])
def test_expansion_refuses_nonmodel_input_instead_of_translating_prose(item):
    with pytest.raises(ModelError, match="not_a_model_object"):
        expanded(item)


def test_exact_large_integer_survives_existing_canonical_codec():
    number = 9007199254740993
    value = quantity(number=number, comparison="eq", unit="source units", inclusivity="inclusive")
    assert expanded(value)["number"] == number
    assert type(expanded(value)["number"]) is int
