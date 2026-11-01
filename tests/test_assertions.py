"""The scoped-assertion object model (openspec/changes/add-scoped-assertions task 1.1; design Decision 2).

The wording the literals stand for is the spec's, quoted from the auditor pilot of 2026-11-01 ("HIV positive
with current CD4+ count < 200", "The source case a person with HIV antiretroviral resistances", "The use of
concomitant medication must be stable for 4 weeks"); the plan names no NCT ids for them.

Positive: every closed vocabulary admits its own words, "unresolved" among them; a well-formed literal,
qualified literal, compound, negation, opaque content, scope, time and assertion are built; `canonical` reads
back to an equal object, writes 200 and 200.0 alike, and keeps a qualified literal, a conjunction and their
order distinct; an assertion carries its rule, stated or explicitly unresolved, and an unknown branch position
is "unresolved".
Negative: a word outside its vocabulary, a compound of one part, a list where a tuple belongs, another person
without a referent, a predicate without a key, a comparison its value kind does not admit, a NaN or bool
number, reversed bounds, a span that is not half-open, an event anchor without its event and an assertion
without an id or without its rule, and an unresolved rule naming provenance, are each refused with their code;
nothing outside the model serializes."""

import dataclasses
import math

import pytest

from TrialLedger.assertions import (
    ALWAYS,
    BRANCH_NODES,
    MODALITIES,
    UNRESOLVED_RULE,
    AllOf,
    AnyOf,
    Branch,
    Evidence,
    Literal,
    ModelError,
    Not,
    Opaque,
    Predicate,
    Rule,
    Scope,
    ScopedAssertion,
    Span,
    Subject,
    TemporalScope,
    Value,
    canonical,
    from_canonical,
    model_problem,
)

PARTICIPANT = Subject("participant")
TRUE = Value("boolean")
HIV = Literal(
    PARTICIPANT, Predicate("condition_status", "HIV"), TRUE, evidence=(Evidence("text_span", "0-12"),)
)
CD4_LOW = Literal(
    PARTICIPANT, Predicate("measurement", "CD4"), Value("quantity", "lt", number=200, unit="/uL")
)
D5 = Rule("D5", "1", premises=("atom:3",))


def refused(build) -> str:
    with pytest.raises(ModelError) as caught:
        build()
    return caught.value.args[0]


def test_every_vocabulary_admits_its_own_words():
    for modality in MODALITIES:
        assert ScopedAssertion("a1", "c1", modality, HIV, rule=D5).modality == modality
    assert Subject("other_person", "the source case").referent == "the source case"
    assert Predicate("unresolved").key == ""
    assert Literal(Subject("unresolved"), Predicate("unresolved"), Value("unresolved"), "unresolved")
    window = TemporalScope("after", "named_event", "chronic pancreatitis diagnosis", 0, 2, "years")
    assert window.anchor_ref == "chronic pancreatitis diagnosis"
    assert Scope("any_of", parts=(Scope("cohort_ref", "A"), Scope("arm_ref", "2"))).parts[1].ref == "2"
    assert Branch("any_of", (0, 1)).path == (0, 1)
    assert Span(3, 3).end == 3


def test_a_word_outside_its_vocabulary_is_refused_never_kept():
    assert refused(lambda: ScopedAssertion("a1", "c1", "conditional", HIV)) == "modality_outside_vocabulary"
    assert refused(lambda: ScopedAssertion("a1", "c1", "required", HIV, status="likely")) == (
        "status_outside_vocabulary"
    )
    assert refused(lambda: Subject("population")) == "subject_kind_outside_vocabulary"
    assert refused(lambda: Predicate("diagnosis", "HIV")) == "predicate_kind_outside_vocabulary"
    assert (
        refused(lambda: Literal(PARTICIPANT, HIV.predicate, TRUE, "maybe")) == "polarity_outside_vocabulary"
    )
    assert refused(lambda: Evidence("guess", "x")) == "evidence_kind_outside_vocabulary"
    assert refused(lambda: TemporalScope("within", "enrollment")) == "orientation_outside_vocabulary"
    assert refused(lambda: Scope("population", "x")) == "scope_kind_outside_vocabulary"
    assert refused(lambda: Branch("xor")) == "branch_node_outside_vocabulary"


def test_malformed_structure_is_refused_with_its_code():
    assert refused(lambda: AllOf((HIV,))) == "compound_needs_two_parts"
    assert refused(lambda: AnyOf([HIV, CD4_LOW])) == "compound_needs_two_parts"
    assert refused(lambda: AllOf((HIV, "CD4"))) == "compound_part_not_proposition"
    assert refused(lambda: Not("HIV")) == "negated_part_not_proposition"
    assert refused(lambda: Opaque("")) == "opaque_without_ref"
    assert refused(lambda: Subject("other_person")) == "other_person_without_referent"
    assert refused(lambda: Predicate("condition_status")) == "predicate_without_key"
    assert refused(lambda: Literal(PARTICIPANT, HIV.predicate, TRUE, qualifiers="CD4")) == (
        "qualifiers_not_condition"
    )
    assert refused(lambda: Literal(PARTICIPANT, HIV.predicate, TRUE, evidence=["x"])) == (
        "evidence_not_tuple_of_evidence"
    )
    assert refused(lambda: ScopedAssertion("", "c1", "required", HIV)) == "assertion_without_id"
    assert refused(lambda: ScopedAssertion("a1", "c1", "required", "HIV")) == "body_not_proposition"
    assert refused(lambda: ScopedAssertion("a1", "c1", "required", HIV, span=[Span(0, 1)], rule=D5)) == (
        "span_not_tuple_of_spans"
    )
    assert refused(lambda: Scope("cohort_ref")) == "scope_without_ref"
    assert (
        refused(lambda: Scope("all_of", parts=(Scope("cohort_ref", "A"),))) == "scope_combination_malformed"
    )
    assert refused(lambda: Rule("", "1")) == "rule_without_id_or_version"


def test_values_suit_their_kind():
    assert Value("quantity", "ge", number=18, unit="years").number == 18
    assert Value("quantity", "lt", number=200).unit == ""  # a missing unit stays missing
    assert Value("interval", "in", number=18, upper=75, unit="years", inclusivity="inclusive").upper == 75
    assert Value("enum", "in", ("locally_advanced", "metastatic")).members[1] == "metastatic"
    assert refused(lambda: Value("quantity", "in", number=1)) == "comparison_not_for_value_kind"
    assert refused(lambda: Value("boolean", "ne")) == "comparison_not_for_value_kind"
    assert refused(lambda: Value("quantity", "lt", number=math.nan)) == "number_not_finite"
    assert refused(lambda: Value("quantity", "lt", number=True)) == "number_not_finite"
    assert refused(lambda: Value("quantity", "lt")) == "quantity_needs_one_number"
    assert refused(lambda: Value("interval", "in", number=75, upper=18)) == "interval_bounds_reversed"
    assert refused(lambda: Value("enum", "eq", ("a", "b"))) == "members_do_not_fit_comparison"
    assert refused(lambda: Value("enum", "in")) == "members_do_not_fit_comparison"
    assert refused(lambda: Value("boolean", members=("yes",))) == "boolean_with_operand"
    assert refused(lambda: Value("quantity", "lt", number=1, inclusivity="closed")) == (
        "inclusivity_outside_vocabulary"
    )


def test_time_and_spans_are_checked():
    assert refused(lambda: TemporalScope("after", "named_event")) == "named_event_without_ref"
    assert refused(lambda: TemporalScope("before", "enrollment", lower=4, upper=2)) == "time_bounds_reversed"
    assert refused(lambda: TemporalScope("before", "enrollment", certainty="likely")) == (
        "certainty_outside_vocabulary"
    )
    assert refused(lambda: Span(5, 4)) == "span_not_half_open"
    assert refused(lambda: Span(-1, 4)) == "span_not_offsets"
    assert refused(lambda: Span(0.0, 4)) == "span_not_offsets"
    assert refused(lambda: Branch("leaf", (-1,))) == "branch_path_not_indexes"


def test_the_model_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        HIV.polarity = "negative"
    assert model_problem("HIV") == "not_a_model_object"
    assert model_problem(ALWAYS) == "ok"


def test_canonical_keeps_compound_identity_and_reads_back():
    qualified = dataclasses.replace(HIV, qualifiers=CD4_LOW)
    conjoined = AllOf((HIV, CD4_LOW))
    texts = {canonical(qualified), canonical(conjoined), canonical(AllOf((CD4_LOW, HIV))), canonical(HIV)}
    assert len(texts) == 4
    assertion = ScopedAssertion(
        "a1",
        "NCT1:exclusion:3",
        "excluded",
        AnyOf((qualified, Not(Opaque("piece 3 tail")))),
        applicability=Literal(PARTICIPANT, Predicate("medication_use", "concomitant"), TRUE),
        cohort=Scope("any_of", parts=(Scope("cohort_ref", "B"), Scope("phase_ref", "2"))),
        branch=Branch("any_of", (1, 0)),
        span=(Span(10, 52),),
        rule=D5,
        status="known",
        resolution="resolved",
    )
    text = canonical(assertion)
    assert from_canonical(text) == assertion
    assert canonical(from_canonical(text)) == text
    whole = Value("quantity", "lt", number=200, unit="/uL")
    assert canonical(whole) == canonical(Value("quantity", "lt", number=200.0, unit="/uL"))


def test_nothing_outside_the_model_serializes_or_reads_back():
    with pytest.raises(ModelError):
        canonical({"class": "Literal"})
    with pytest.raises(ModelError):
        from_canonical('{"class": "Atom", "bank": "x"}')
    with pytest.raises(ModelError):
        from_canonical('{"class": "Span", "start": 0.5, "end": 2.0}')
    with pytest.raises(ModelError):
        from_canonical('{"class": "Opaque", "ref": "x", "extra": 1}')
    with pytest.raises(ModelError):
        from_canonical('{"class": "AllOf", "parts": [{"class": "Opaque", "ref": "x"}]}')


def test_provenance_is_never_invented():
    """Positive: a stated rule, or the rule explicitly unresolved, builds; an unknown branch position is
    "unresolved" (a vocabulary word), never "leaf". Negative: an assertion without its rule is refused, from
    code and from its serialization; an unresolved rule naming a version or premises is refused."""
    stated = ScopedAssertion("a1", "c1", "required", HIV, rule=D5)
    assert stated.rule == D5 and stated.branch == Branch("unresolved")
    assert "unresolved" in BRANCH_NODES and stated.branch.node != "leaf"
    unknown = ScopedAssertion("a1", "c1", "required", HIV, rule=UNRESOLVED_RULE)
    assert unknown.rule.id == "unresolved" and from_canonical(canonical(unknown)) == unknown
    assert refused(lambda: ScopedAssertion("a1", "c1", "required", HIV)) == "assertion_without_rule"
    ruleless = canonical(stated).replace(canonical(D5), "null")
    assert refused(lambda: from_canonical(ruleless)) == "assertion_without_rule"
    assert refused(lambda: Rule("unresolved", "1")) == "unresolved_rule_with_provenance"
    assert refused(lambda: Rule("unresolved", "unresolved", premises=("atom:3",))) == (
        "unresolved_rule_with_provenance"
    )
    assert Rule("D5", "unresolved").version == "unresolved"


def _forced(item, **fields):
    """A copy of a well-formed object with fields set past its own check, as data read from elsewhere could
    arrive; `model_problem` must still name what is wrong with it."""
    copy = dataclasses.replace(item)
    for name, value in fields.items():
        object.__setattr__(copy, name, value)
    return copy


EVIDENCE = Evidence("text_span", "0-12")
WELL_FORMED = (
    ALWAYS,
    EVIDENCE,
    PARTICIPANT,
    Subject("other_person", "the source case"),
    HIV.predicate,
    Predicate("unresolved"),
    TRUE,
    TemporalScope("before", "enrollment"),
    HIV,
    AllOf((HIV, CD4_LOW)),
    AnyOf((HIV, CD4_LOW)),
    Not(HIV),
    Opaque("piece 3 tail"),
    Scope("cohort_ref", "A"),
    Branch("any_of", (0, 1)),
    Span(3, 3),
    D5,
    UNRESOLVED_RULE,
    ScopedAssertion("a1", "c1", "required", HIV, rule=D5),
)


def test_every_well_formed_object_is_ok_when_asked_directly():
    """Positive: each class of the model, built well, is "ok" when model_problem is called on it directly.
    Negative: anything outside the model is "not_a_model_object"."""
    assert [model_problem(item) for item in WELL_FORMED] == ["ok"] * len(WELL_FORMED)
    assert model_problem(("participant",)) == "not_a_model_object"


@pytest.mark.parametrize(
    ("item", "fields", "code"),
    [
        (EVIDENCE, {"kind": "guess"}, "evidence_kind_outside_vocabulary"),
        (EVIDENCE, {"ref": ""}, "evidence_without_ref"),
        (EVIDENCE, {"ref": 7}, "evidence_without_ref"),
        (PARTICIPANT, {"kind": "population"}, "subject_kind_outside_vocabulary"),
        (Subject("other_person", "x"), {"referent": ""}, "other_person_without_referent"),
        (PARTICIPANT, {"referent": 7}, "referent_not_text"),
        (HIV.predicate, {"kind": "diagnosis"}, "predicate_kind_outside_vocabulary"),
        (HIV.predicate, {"key": ""}, "predicate_without_key"),
        (Predicate("unresolved"), {"key": 7}, "predicate_without_key"),
        (HIV, {"subject": "participant"}, "literal_subject_not_subject"),
        (HIV, {"predicate": "HIV"}, "literal_predicate_not_predicate"),
        (HIV, {"value": True}, "literal_value_not_value"),
        (HIV, {"polarity": "maybe"}, "polarity_outside_vocabulary"),
        (HIV, {"time": "4 weeks"}, "literal_time_not_temporal_scope"),
        (HIV, {"qualifiers": "CD4"}, "qualifiers_not_condition"),
        (HIV, {"evidence": [EVIDENCE]}, "evidence_not_tuple_of_evidence"),
        (AllOf((HIV, CD4_LOW)), {"parts": (HIV,)}, "compound_needs_two_parts"),
        (AnyOf((HIV, CD4_LOW)), {"parts": [HIV, CD4_LOW]}, "compound_needs_two_parts"),
        (AllOf((HIV, CD4_LOW)), {"parts": (HIV, "CD4")}, "compound_part_not_proposition"),
        (Not(HIV), {"part": "HIV"}, "negated_part_not_proposition"),
        (Opaque("x"), {"ref": ""}, "opaque_without_ref"),
        (Opaque("x"), {"ref": 7}, "opaque_without_ref"),
        (Branch("any_of", (0, 1)), {"node": "xor"}, "branch_node_outside_vocabulary"),
        (Branch("any_of", (0, 1)), {"path": (0, -1)}, "branch_path_not_indexes"),
        (Branch("any_of", (0, 1)), {"path": [0, 1]}, "branch_path_not_indexes"),
        (Branch("any_of", (0, 1)), {"path": (0, 1.0)}, "branch_path_not_indexes"),
        (Span(3, 3), {"start": -1}, "span_not_offsets"),
        (Span(3, 3), {"end": 3.0}, "span_not_offsets"),
        (Span(3, 3), {"start": 4}, "span_not_half_open"),
        (D5, {"id": ""}, "rule_without_id_or_version"),
        (D5, {"version": ""}, "rule_without_id_or_version"),
        (UNRESOLVED_RULE, {"version": "1"}, "unresolved_rule_with_provenance"),
        (UNRESOLVED_RULE, {"answers": ("q1",)}, "unresolved_rule_with_provenance"),
        (D5, {"premises": ["atom:3"]}, "rule_refs_not_text"),
        (D5, {"warrants": ("",)}, "rule_refs_not_text"),
        (D5, {"answers": (7,)}, "rule_refs_not_text"),
    ],
)
def test_a_malformed_field_is_named_when_asked_directly(item, fields, code):
    """Negative: one field set past the constructor's check (a word outside its vocabulary, a missing ref
    or key, a field of the wrong class, a list where a tuple belongs, a compound of one part, a negative or
    fractional index or offset, a reversed span, a rule without its id or version, an unresolved rule naming
    provenance, a reference that is not text) is named by its code, never "ok"."""
    assert model_problem(_forced(item, **fields)) == code


def _unchecked(cls, **fields):
    """An instance built without its constructor's check, which itself calls model_problem: so the answer
    model_problem gives is observed as a value, never pre-empted by a refusal at construction."""
    item = object.__new__(cls)
    for field in dataclasses.fields(cls):
        default = field.default if field.default is not dataclasses.MISSING else None
        object.__setattr__(item, field.name, fields.get(field.name, default))
    return item


def test_a_subject_a_predicate_and_a_value_are_ok_each_on_its_own_branch():
    """Positive: a participant subject with no referent, a keyed condition predicate and a boolean value are
    each "ok" by their own class's check, asked of instances whose construction did not already ask. Negative:
    none is read as another class's object (an evidence, subject or predicate check would refuse its kind)."""
    assert model_problem(_unchecked(Subject, kind="participant", referent="")) == "ok"
    assert model_problem(_unchecked(Predicate, kind="condition_status", key="HIV")) == "ok"
    boolean = _unchecked(
        Value, kind="boolean", comparison="eq", members=(), unit="", inclusivity="unspecified"
    )
    assert model_problem(boolean) == "ok"
