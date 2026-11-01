"""The audit question kinds beyond the atom claim: untyped criteria, outcome endpoints and time points,
intervention targets (add-targeted-questions, Decisions 1, 2, 6). Real texts are cited by NCT id; the rest are
marked synthetic.

Positive: a field's envelope is its own text verbatim with the field that names it as context; "up to N" is a
window and any other statement of a time point unmarked (no role); an untyped-criterion answer names one
or more closed concept instances, each with a span of the criterion, or none, or out_of_taxonomy with a span;
"EGFR or ALK" is two instances; out_of_taxonomy reads as its own outcome, never as a concept; every concept an
atom states is one of the options, one per value for a closed vocabulary and the concept alone otherwise; a
question of every kind fits the transport's context budget.
Negative: an empty field or one over budget is no envelope (refused, never cut); a time point the frame does
not state is not_stated; an open-valued concept is never split per value; an unknown option, a repeated
instance, none or insufficient_context beside another instance, a concept with no span or with a span outside
the criterion, or a malformed answer is a named error, never a reading.
"""

import json

from TrialLedger.banks import type_criterion
from TrialLedger.criteria import itemize
from TrialLedger.questions import (
    CONCEPT_OPTIONS,
    UNTYPED_OPTIONS,
    concept_instances,
    envelope,
    field_envelope,
    instances_schema,
    question,
    time_point_claim,
    time_point_role,
    untyped_claim,
    untyped_reading,
    validate_answer,
    validate_instances,
)
from TrialLedger.transport import RUBRICS, prompt_for

# NCT04382755, NCT05027230 and NCT05540704: criteria no bank types.
MENINGOCOCCAL = "* History of active or past meningococcal disease"
LIVER = "* Severe liver or kidney disease."
AGE = "* 16-50 years of age"


def untyped_envelope(criterion, heading="Exclusion Criteria:", untyped=True):
    text = f"{heading}\n\n{criterion}\n"
    code, pieces = itemize(text)
    assert code == "itemized"
    index = next(i for i, p in enumerate(pieces) if p[0] == "criterion")
    assert not untyped or type_criterion(text[pieces[index][2] : pieces[index][3]]) == []
    return envelope(text, pieces, index)[1]


def answer(*instances):
    return json.dumps({"instances": [{"option": o, "quote": q} for o, q in instances]})


def test_a_field_envelope_is_the_field_itself_with_its_naming_field():
    # NCT04693377: "Duration of response", time frame "Up to 24 weeks post-treatment"
    code, held = field_envelope(
        "outcomesModule.secondaryOutcomes[1].timeFrame",
        "Up to 24 weeks post-treatment",
        [("outcomesModule.secondaryOutcomes[1].measure", "Duration of response")],
    )
    assert code == "ok"
    assert held["target"] == {
        "text": "Up to 24 weeks post-treatment",
        "start": 0,
        "end": 29,
        "field": "outcomesModule.secondaryOutcomes[1].timeFrame",
    }
    assert held["context"] == [
        {"field": "outcomesModule.secondaryOutcomes[1].measure", "text": "Duration of response"}
    ]
    assert held["headings"] == held["scoping"] == held["siblings"] == [] and held["stem"] == ""
    quoted = json.dumps({"verdict": "supported", "quote": "Duration of response"})
    assert validate_answer(quoted, ("supported", "unsupported"), held) == (
        "ok",
        "supported",
        "Duration of response",
    )
    invented = json.dumps({"verdict": "supported", "quote": "at 24 weeks"})
    assert validate_answer(invented, ("supported",), held)[0] == "quote_not_in_envelope"


def test_an_empty_or_oversized_field_is_refused():
    assert field_envelope("f", "  ", []) == ("empty_field", {})
    assert field_envelope("f", "Duration of response", [("g", "x" * 10)], budget=25) == (
        "envelope_over_budget",
        {},
    )
    assert field_envelope("f", "Duration of response", [], budget=20)[0] == "ok"


def test_up_to_n_is_a_window_and_any_other_time_point_unmarked():
    """Positive: "up to N" is a window, claimed as one. Negative: any other statement is unmarked, never
    given a role ("scheduled" is not invented), and its claim says only that a time point is stated."""
    assert time_point_role("Up to 24 weeks post-treatment", "24 week") == "window"  # NCT04693377
    assert time_point_role("Baseline, assessed up to 24 weeks post-treatment", "24 week") == "window"
    assert time_point_role("during hospital admission (up to 28 days)", "28 day") == "window"  # NCT04382755
    assert time_point_role("Up to approximately 3 years", "3 year") == "window"
    assert time_point_role("baseline, 6 weeks, 12 weeks, 36 weeks", "12 week") == "unmarked"  # NCT05540704
    assert time_point_role("At 12 weeks post-treatment", "12 week") == "unmarked"  # NCT04693377
    # The founder's rule names "up to" only: "within" is not read as a window here (the model may say so).
    assert time_point_role("Within 6 months of randomization", "6 month") == "unmarked"  # NCT04679675
    assert time_point_claim("12 week", "unmarked") == "This time frame states a time point at 12 week(s)"
    assert time_point_claim("12 week", "not_stated") == time_point_claim("12 week", "unmarked")
    assert "observation window" in time_point_claim("24 week", "window")
    for role in ("window", "unmarked", "not_stated"):
        assert "scheduled" not in time_point_claim("24 week", role)


def test_a_time_point_the_frame_does_not_state_is_not_stated():
    assert time_point_role("baseline, 6 weeks, 12 weeks, 36 weeks", "2 week") == "not_stated"
    assert time_point_role("Up to 124 weeks", "24 week") == "not_stated"
    assert time_point_role("Week 24", "") == "not_stated"


def test_an_untyped_criterion_names_concept_instances_each_with_a_span():
    held = untyped_envelope(LIVER)
    found = validate_instances(
        answer(("condition:organ_impairment", "liver or kidney disease")), UNTYPED_OPTIONS, held
    )
    assert found == ("ok", [("condition:organ_impairment", "liver or kidney disease")])
    assert untyped_reading(found[1]) == "concept_stated"
    two = answer(("biomarker:EGFR", "EGFR"), ("biomarker:ALK", "ALK"))
    eligible = untyped_envelope("* Known EGFR or ALK status", "Inclusion Criteria:", untyped=False)
    assert validate_instances(two, UNTYPED_OPTIONS, eligible)[1] == [
        ("biomarker:EGFR", "EGFR"),
        ("biomarker:ALK", "ALK"),
    ]


def test_out_of_taxonomy_is_counted_apart_and_none_stands_alone():
    held = untyped_envelope(MENINGOCOCCAL)
    code, found = validate_instances(
        answer(("out_of_taxonomy", "meningococcal disease")), UNTYPED_OPTIONS, held
    )
    assert code == "ok" and untyped_reading(found) == "out_of_taxonomy"
    mixed = answer(("out_of_taxonomy", "meningococcal disease"), ("condition:active_infection", "active"))
    assert untyped_reading(validate_instances(mixed, UNTYPED_OPTIONS, held)[1]) == "concept_stated"
    assert untyped_reading([("none", "")]) == "no_requirement"
    assert untyped_reading([("insufficient_context", "")]) == "insufficient_context"
    assert validate_instances(answer(("none", "")), UNTYPED_OPTIONS, held) == ("ok", [("none", "")])


def test_a_bad_untyped_answer_is_a_named_error():
    held = untyped_envelope(AGE, "Inclusion Criteria:")
    good = ("age", "16-50 years of age")
    assert validate_instances(answer(good), UNTYPED_OPTIONS, held)[0] == "ok"
    assert validate_instances("not json", UNTYPED_OPTIONS, held) == ("malformed", [])
    assert validate_instances(json.dumps({"instances": []}), UNTYPED_OPTIONS, held) == ("malformed", [])
    assert (
        validate_instances(json.dumps({"instances": [good], "x": 1}), UNTYPED_OPTIONS, held)[0] == "malformed"
    )
    assert (
        validate_instances(json.dumps({"instances": [{"option": "age"}]}), UNTYPED_OPTIONS, held)[0]
        == "malformed"
    )
    assert validate_instances(json.dumps({"instances": [{"option": 1, "quote": ""}]}), UNTYPED_OPTIONS, held)[
        0
    ] == ("malformed")
    assert validate_instances(answer(("adult", "16-50")), UNTYPED_OPTIONS, held) == ("unknown_verdict", [])
    assert validate_instances(answer(good, good), UNTYPED_OPTIONS, held) == ("duplicate_instance", [])
    assert validate_instances(answer(good, ("none", "")), UNTYPED_OPTIONS, held) == (
        "exclusive_option_combined",
        [],
    )
    assert validate_instances(answer(("age", "")), UNTYPED_OPTIONS, held) == ("quote_not_in_target", [])
    assert validate_instances(answer(("age", "Inclusion Criteria")), UNTYPED_OPTIONS, held) == (
        "quote_not_in_target",
        [],
    )
    assert (
        validate_instances(answer(("out_of_taxonomy", "")), UNTYPED_OPTIONS, held)[0] == "quote_not_in_target"
    )
    assert validate_instances(answer(("none", "nowhere")), UNTYPED_OPTIONS, held) == (
        "quote_not_in_envelope",
        [],
    )


def test_every_concept_a_bank_types_is_an_option():
    # Synthetic criteria in the NSCLC wording the banks were measured on, uncited, one or more per bank.
    texts = [
        "* ECOG performance status 0-1",
        "* Documented EGFR mutation or ALK rearrangement",
        "* No prior systemic therapy for advanced or metastatic disease",
        "* Prior treatment with an anti-PD-1 antibody",
        "* Stage IV non-small cell lung cancer, completely resected",
        "* Adjuvant chemotherapy",
        "* Absolute neutrophil count >= 1.5 x 10^9/L",
        "* Adequate organ function",
        "* Active autoimmune disease or HIV infection",
        "* Age >= 18 years",
        "* Squamous histology",
    ]
    seen = set()
    for text in texts:
        for _bank, concept, values, _params, _s, _e in type_criterion(text):
            seen.update(concept_instances(concept, values))
    assert seen and seen <= set(CONCEPT_OPTIONS)
    assert len(CONCEPT_OPTIONS) == len(set(CONCEPT_OPTIONS))
    assert {"none", "out_of_taxonomy", "insufficient_context"} <= set(UNTYPED_OPTIONS)


def test_every_kind_has_a_rubric_and_fits_the_context_budget():
    assert {
        "atom_claim",
        "untyped_criterion",
        "outcome_endpoint",
        "outcome_time_point",
        "intervention_target",
    } == set(RUBRICS)
    long = "* " + "x" * 3970
    held = untyped_envelope(long)
    assert held and len(held["target"]["text"].encode()) <= 4000
    item = question(
        "untyped_criterion", {"nct": "N", "piece": 1, "claim": untyped_claim()}, held, UNTYPED_OPTIONS
    )
    assert len(prompt_for(item).encode("utf-8")) <= 16384 - 4096 - 1024
    schema = instances_schema(UNTYPED_OPTIONS)
    assert schema["properties"]["instances"]["items"]["properties"]["option"]["enum"] == list(UNTYPED_OPTIONS)


def test_a_closed_vocabulary_is_one_instance_per_value_and_any_other_concept_one_instance():
    assert concept_instances("condition", ("hiv",)) == ["condition:hiv"]
    assert concept_instances("lab", ("platelets", "neutrophils")) == ["lab:platelets", "lab:neutrophils"]
    assert concept_instances("age", ("stated",)) == ["age"]
    assert concept_instances("ecog_ps", ("0", "1")) == ["ecog_ps"]
    assert concept_instances("biomarker:EGFR", ("positive",)) == ["biomarker:EGFR"]
