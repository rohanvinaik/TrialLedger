"""Typed mismatch candidates never certify clinical equivalence or promote proposed source readings.

All clinical labels and equivalence premises below are invented representation examples, not NIH facts
or medical claims that WHO and ECOG scales are interchangeable.
"""

import dataclasses
import json

import pytest

from TrialLedger.layer2 import run
from TrialLedger.layer2.assertions import (
    AllOf,
    AnyOf,
    Evidence,
    Literal,
    Not,
    Opaque,
    Predicate,
    Rule,
    Scope,
    ScopedAssertion,
    Subject,
    TemporalScope,
    Value,
    canonical,
)
from TrialLedger.layer2.entail import decide
from TrialLedger.layer2.translation_diagnostics import diagnose, mismatch_dimensions

INVENTED = Rule("invented-declared-premise", "1", warrants=("invented:translation-test",))


def measured(unit="WHO", subject=None, key="performance_status", time=None, value=None):
    return Literal(
        subject or Subject("participant"),
        Predicate("measurement", key),
        value or Value("quantity", "eq", number=2, unit=unit),
        time=time,
    )


def assertion(body, identity="invented-source", status="known", resolution="resolved", **fields):
    return ScopedAssertion(
        identity,
        f"invented:translation-test#{identity}",
        "required",
        body,
        rule=INVENTED,
        status=status,
        resolution=resolution,
        **fields,
    )


def plain(item):
    return json.loads(canonical(item))


def test_shared_predicate_different_scale_unit_is_only_a_candidate_with_exact_values():
    source = measured()
    query = measured(value=Value("interval", "in", number=0, upper=1, unit="ECOG", inclusivity="inclusive"))
    given = assertion(source, status="proposed")
    before = canonical(given), canonical(query)
    [row] = diagnose([given], query)
    assert row["code"] == "candidate_translation_mismatch"
    assert row["premise"] == "invented-source" and row["dimensions"] == ["unit"]
    assert row["premise_identity"]["unit"] == "WHO" and row["query_identity"]["unit"] == "ECOG"
    assert row["premise_literal"]["value"]["number"] == 2
    assert row["query_literal"]["value"]["number"] == 0 and row["query_literal"]["value"]["upper"] == 1
    assert row["status"] == "proposed" and row["resolution"] == "resolved"
    assert row["premise_path"] == ["body"] and row["query_path"] == []
    assert row["rule"] == plain(INVENTED)
    assert (canonical(given), canonical(query)) == before
    assert decide((given,), query).result == "UNDETERMINED"


@pytest.mark.parametrize(
    "key", ["ECOG_PS", "PERFORMANCE_STATUS", "performance status", "performance_status "]
)
def test_different_predicate_names_never_imply_a_candidate_correspondence(key):
    assert diagnose((assertion(measured(key="WHO_PS")),), measured("ECOG", key=key)) == []


def test_same_key_in_different_predicate_kind_is_not_the_same_identity():
    query = dataclasses.replace(measured("ECOG"), predicate=Predicate("demographic", "performance_status"))
    assert diagnose((assertion(measured()),), query) == []


def test_unresolved_predicate_is_not_an_established_identity():
    source = dataclasses.replace(measured(), predicate=Predicate("unresolved", ""))
    query = dataclasses.replace(source, subject=Subject("source_case"))
    assert mismatch_dimensions(source, query) == ()
    assert diagnose((assertion(source),), query) == []


def test_subject_kind_and_referent_are_exact_identity_dimensions():
    source = measured(subject=Subject("source_case"))
    assert mismatch_dimensions(source, measured()) == ("subject",)
    other = measured(subject=Subject("other_person", "person-a"))
    query = measured(subject=Subject("other_person", "person-b"))
    [row] = diagnose((assertion(other),), query)
    assert row["dimensions"] == ["subject"]
    assert row["premise_identity"]["subject"]["referent"] == "person-a"
    assert row["query_identity"]["subject"]["referent"] == "person-b"


def test_units_are_exact_strings_and_missing_is_not_converted():
    for unit in ("who", "WHO ", "", "ECOG"):
        assert mismatch_dimensions(measured(), measured(unit)) == ("unit",)
    assert mismatch_dimensions(measured(), measured()) == ()


@pytest.mark.parametrize("kind", ["boolean", "enum", "enum_set", "entity_ref", "definition_ref"])
def test_nonmeasurement_unit_words_do_not_split_the_solver_variable(kind):
    comparison = "in" if kind == "enum_set" else "eq"
    members = () if kind == "boolean" else ("x",)
    source = measured(value=Value(kind, comparison, members, unit="WHO"))
    query = dataclasses.replace(source, value=Value(kind, comparison, members, unit="ECOG"))
    assert mismatch_dimensions(source, query) == ()
    assert diagnose((assertion(source),), query) == []


def test_measurement_and_boolean_families_do_not_acquire_a_unit_conversion_diagnostic():
    query = dataclasses.replace(measured(), value=Value("boolean", unit="ECOG"))
    assert mismatch_dimensions(measured(), query) == ()


def test_temporal_certainty_and_all_evidence_are_epistemic_not_identity():
    before = TemporalScope("before", "enrollment", lower=0, upper=21, unit="days", certainty="explicit")
    cited_time = dataclasses.replace(
        before, certainty="entailed", evidence=(Evidence("record_field", "time"),)
    )
    source = dataclasses.replace(measured(time=before), evidence=(Evidence("text_span", "source:0:5"),))
    query = dataclasses.replace(measured(time=cited_time), evidence=(Evidence("text_span", "query:8:13"),))
    assert mismatch_dimensions(source, query) == ()
    assert diagnose((assertion(source),), query) == []


@pytest.mark.parametrize(
    "change",
    [
        {"upper": 10},
        {"lower": 1},
        {"anchor": "randomization"},
        {"orientation": "after"},
        {"unit": "weeks"},
        {"inclusivity": "inclusive"},
        {"anchor": "named_event", "anchor_ref": "different-event"},
    ],
)
def test_temporal_window_role_bounds_and_units_remain_exact(change):
    time = TemporalScope("before", "enrollment", lower=0, upper=21, unit="days")
    source, query = measured(time=time), measured(time=dataclasses.replace(time, **change))
    [row] = diagnose((assertion(source),), query)
    assert row["dimensions"] == ["time"]
    assert row["premise_identity"]["time"] != row["query_identity"]["time"]


def test_absent_time_and_explicit_time_are_not_the_same():
    query = measured(time=TemporalScope("at", "enrollment"))
    [row] = diagnose((assertion(measured()),), query)
    assert row["dimensions"] == ["time"] and row["premise_identity"]["time"] is None


def test_all_three_dimensions_are_named_in_stable_order_without_changing_a_decision():
    source = measured(subject=Subject("source_case"), time=TemporalScope("at", "enrollment"))
    query = measured("ECOG")
    given = (assertion(source),)
    before = decide(given, query)
    [row] = diagnose(given, query)
    assert row["dimensions"] == ["subject", "unit", "time"]
    assert decide(given, query) == before
    assert before.result == "UNDETERMINED" and before.blockers == ("no_constraint_mentions_query",)


def test_nested_alternatives_negation_applicability_and_qualifiers_keep_occurrence_paths():
    unrelated = measured(key="unrelated")
    source = measured()
    qualified = dataclasses.replace(unrelated, qualifiers=Not(source))
    body = AllOf((AnyOf((Not(source), unrelated)), qualified))
    applicability = Not(AllOf((unrelated, source)))
    given = assertion(body, applicability=applicability)
    query = AnyOf((unrelated, Not(dataclasses.replace(unrelated, qualifiers=measured("ECOG")))))
    rows = diagnose((given,), query)
    assert [row["premise_path"] for row in rows] == [
        ["body", "parts", 0, "parts", 0, "part"],
        ["body", "parts", 1, "qualifiers", "part"],
        ["applicability", "part", "parts", 1],
    ]
    assert all(row["query_path"] == ["parts", 1, "part", "qualifiers"] for row in rows)
    assert all(row["dimensions"] == ["unit"] for row in rows)


@pytest.mark.parametrize(
    "status,resolution",
    [
        ("known", "resolved"),
        ("interpolated", "resolved"),
        ("proposed", "resolved"),
        ("known", "unresolved"),
        ("known", "conflicting"),
        ("known", "partially_resolved"),
    ],
)
def test_all_supplied_standings_are_reported_without_admitting_or_promoting_them(status, resolution):
    given = assertion(measured(), status=status, resolution=resolution)
    [row] = diagnose((given,), measured("ECOG"))
    assert (row["status"], row["resolution"]) == (status, resolution)
    assert row["modality"] == "required" and row["criterion_ref"] == given.criterion_ref


def test_nonconstraining_modality_and_cohort_stay_visible_without_becoming_constraints():
    given = dataclasses.replace(
        assertion(measured()), modality="descriptive", cohort=Scope("cohort_ref", "A")
    )
    [row] = diagnose((given,), measured("ECOG"))
    assert row["modality"] == "descriptive"
    assert row["cohort"] == plain(Scope("cohort_ref", "A"))
    assert decide((given,), measured("ECOG")).result == "UNDETERMINED"


def test_rows_are_deterministic_by_premise_id_and_do_not_share_mutable_payloads():
    a, b = assertion(measured(), "a"), assertion(measured(), "b")
    query = measured("ECOG")
    rows = diagnose([b, a], query)
    assert rows == diagnose((a, b), query)
    assert [row["premise"] for row in rows] == ["a", "b"]
    rows[0]["query_literal"]["predicate"]["key"] = "changed"
    assert rows[1]["query_literal"]["predicate"]["key"] == "performance_status"
    assert query.predicate.key == "performance_status"


def test_empty_inputs_opaque_content_and_same_identity_are_not_silence_certificates():
    assert diagnose([], measured()) == []
    assert diagnose((assertion(Opaque("invented:unknown-source")),), measured()) == []
    assert diagnose((assertion(measured()),), Opaque("invented:unknown-query")) == []
    assert diagnose((assertion(measured()),), measured()) == []
    changed_threshold = measured(value=Value("quantity", "le", number=1, unit="WHO"))
    assert diagnose((assertion(measured()),), changed_threshold) == []


def test_public_entailment_accepts_only_the_explicit_scoped_boolean_equivalence_premise():
    """Invented IFF connects declared propositions, never an automatically inferred scale conversion."""
    a = Literal(Subject("participant"), Predicate("measurement", "invented_ECOG_allowed"), Value("boolean"))
    b = Literal(Subject("participant"), Predicate("measurement", "invented_WHO_allowed"), Value("boolean"))
    source = assertion(a, "invented-source")
    iff = AllOf((AnyOf((Not(a), b)), AnyOf((Not(b), a))))
    bridge = assertion(iff, "invented-equivalence", status="interpolated", cohort=Scope("cohort_ref", "A"))

    def ask(items, context):
        response = run(
            {
                "operation": "entailment",
                "assertions": [plain(item) for item in items],
                "query": plain(b),
                "context": {"cohort": context},
            }
        )
        assert response["code"] == "complete", response
        return response["result"]["decision"]

    implicit = ask((source,), "A")
    assert implicit["result"] == "UNDETERMINED"
    assert implicit["blockers"] == ("no_constraint_mentions_query",)
    explicit = ask((source, bridge), "A")
    assert (explicit["result"], explicit["status"]) == ("ENTAILED", "interpolated")
    assert explicit["proof"] == ("invented-equivalence", "invented-source")
    assert ask((source, bridge), "B")["result"] == "OUT_OF_SCOPE"
    proposed = ask((source, dataclasses.replace(bridge, status="proposed")), "A")
    assert proposed["result"] == "UNDETERMINED"
    assert "proposed_refused:invented-equivalence" in proposed["blockers"]
    assert diagnose((source,), b) == []
