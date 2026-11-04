"""Clinical displays retain the typed logical boundaries and caller attribution."""

import json
from copy import deepcopy

import pytest

from TrialLedger import clinical_display, reasoning_artifacts
from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import source_evidence
from TrialLedger.layer2.service import run


def plain(value):
    return json.loads(a.canonical(value))


def fact(key="diabetes", **kwargs):
    return a.Literal(
        a.Subject("participant"), a.Predicate("condition_status", key), a.Value("boolean"), **kwargs
    )


def test_qualified_negative_never_becomes_negative_base_with_positive_qualifier():
    query = fact(polarity="negative", qualifiers=fact("at_screening"))
    text = clinical_display.proposition(plain(query))["text"]
    assert text.startswith("NOT ((")
    assert '"diabetes" AND participant: "at_screening"' in text
    assert not text.startswith('NOT (participant: "diabetes") AND')


def test_disjunction_and_set_membership_keep_different_meanings():
    query = a.AnyOf((fact("hypertension"), fact("sleep_apnoea")))
    text = clinical_display.proposition(plain(query))["text"]
    assert " OR " in text and " AND " not in text
    for kind, phrase in (("enum", "is one of"), ("enum_set", "includes every member of")):
        q = a.Literal(
            a.Subject("participant"),
            a.Predicate("disease_attribute", "marker"),
            a.Value(kind, "in", ("A", "B")),
        )
        assert phrase in clinical_display.proposition(plain(q))["text"]


def test_units_time_and_boundary_uncertainty_are_visible_without_conversion():
    q = a.Literal(
        a.Subject("participant"),
        a.Predicate("treatment_history", "washout"),
        a.Value("interval", "in", number=0, upper=21, unit="Days"),
        time=a.TemporalScope(
            "before",
            "treatment_start",
            lower=0,
            upper=21,
            unit="Days",
            inclusivity="exclusive",
            certainty="explicit",
        ),
    )
    text = clinical_display.proposition(plain(q))["text"]
    assert "Days" in text and "boundaries unspecified" in text
    assert "before treatment start" in text and "boundaries exclusive" in text


def test_combined_scope_is_not_reduced_to_an_empty_reference():
    scope = a.Scope("all_of", parts=(a.Scope("cohort_ref", "adult"), a.Scope("phase_ref", "entry")))
    rule = a.ScopedAssertion(
        "a",
        "user:simulated",
        "excluded",
        fact(),
        cohort=scope,
        rule=a.Rule("user_choice", "1"),
        status="known",
        resolution="resolved",
    )
    text = clinical_display.assertion(plain(rule))["text"]
    assert 'cohort ref "adult" AND phase ref "entry"' in text


@pytest.mark.parametrize("value", [None, {"class": "Future"}, plain(a.Opaque("unread"))])
def test_unknown_display_is_explicit_and_retains_its_reference(value):
    result = clinical_display.proposition(value, "/exact/query")
    assert result["code"] != "displayed"
    assert result["canonical_ref"] == "/exact/query"
    assert "unresolved" in result["text"]


def test_negated_option_label_cannot_turn_compatibility_into_required_exclusion(tmp_path):
    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    request["session"]["decisions"][0]["alternatives"][0]["label"] = "Excluded: unencoded previous diagnosis"
    response = run(request)
    view = response["decision_view"][0]
    assert view["caller_question"]["origin"].startswith("caller_wording")
    assert all(o["caller_label"]["origin"].startswith("caller_wording") for o in view["options"])
    assert all(o["profile"]["code"] == "displayed" for o in view["options"])
    assert all(o["deciding_premises"] for o in view["options"])
    saved = reasoning_artifacts.save(tmp_path, request, response)
    read = reasoning_artifacts.read(tmp_path, saved["id"], {"part": "decision_view", "limit": 1})
    assert "navigation" not in read
    assert read["value"][0] == view


def test_anchored_context_never_changes_the_analysis_constraints():
    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    before = run(request)
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {"eligibilityCriteria": "Crossover only: ECOG 0–2."},
        }
    }
    snapshot = source_evidence.snapshot(study)
    changed = deepcopy(request)
    changed["session"]["sources"].append(
        {"id": "comparator", "study": study, "expected_digest": snapshot["digest"]}
    )
    changed["session"]["decisions"][0]["evidence"] = [
        {
            "id": "passage",
            "source": "comparator",
            "role": "reading",
            "note": "An unconfirmed entry reading",
            "scope": "crossover",
            "anchor": {
                "id": "passage",
                "digest": snapshot["digest"],
                "address": "/protocolSection/eligibilityModule/eligibilityCriteria",
                "expected": "Crossover only: ECOG 0–2.",
            },
        }
    ]
    after = run(changed)
    assert after["code"] == "complete", after["problems"]
    assert [r["request"] for r in before["result"]["analyses"]] == [
        r["request"] for r in after["result"]["analyses"]
    ]
    assert after["decision_view"][0]["evidence"][0]["note_standing"] == "proposed"
    assert after["decision_view"][0]["evidence"][0]["anchor"]["value"] == "Crossover only: ECOG 0–2."


@pytest.mark.parametrize(
    ("kind", "comparison", "expected"),
    [
        ("boolean", "eq", "boolean"),
        ("quantity", "ge", "quantity"),
        ("quantity", "in", "unsupported"),
        ("interval", "in", "interval"),
        ("interval", "not_in", "interval"),
        ("enum", "eq", "enum"),
        ("enum", "ne", "enum"),
        ("enum", "in", "enum"),
        ("enum", "not_in", "enum"),
        ("enum_set", "in", "set"),
        ("enum_set", "not_in", "set"),
        ("enum_set", "eq", "unsupported"),
        ("entity_ref", "eq", "reference"),
        ("definition_ref", "eq", "reference"),
        ("entity_ref", "ne", "unsupported"),
        ("future", "eq", "unsupported"),
        ("", "", "unsupported"),
    ],
)
def test_value_style_direct_positive_and_must_not_types(kind, comparison, expected):
    assert clinical_display.value_style(kind, comparison) == expected


def test_export_uses_shared_view_with_attributed_labels_profiles_and_evidence(tmp_path):
    from openpyxl import load_workbook

    from TrialLedger.clinical_export import export_review

    request = run({"operation": "describe", "view": "design_session"})["result"]["example"]
    request["session"]["decisions"][0]["alternatives"][0]["label"] = "Unencoded previous diagnosis"
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001"},
            "eligibilityModule": {"eligibilityCriteria": "Crossover only: ECOG 0–2."},
        }
    }
    snapshot = source_evidence.snapshot(study)
    request["session"]["sources"].append(
        {"id": "comparator", "study": study, "expected_digest": snapshot["digest"]}
    )
    request["session"]["decisions"][0]["evidence"] = [
        {
            "id": "context",
            "source": "comparator",
            "role": "reading",
            "note": "Possible entry reading; unconfirmed",
            "scope": "crossover",
            "anchor": {
                "id": "context",
                "digest": snapshot["digest"],
                "address": "/protocolSection/eligibilityModule/eligibilityCriteria",
                "expected": "Crossover only: ECOG 0–2.",
            },
        }
    ]
    response = run(request)
    saved = reasoning_artifacts.save(tmp_path / "store", request, response)
    exported = export_review(tmp_path / "store", saved["id"], tmp_path / "handoff")
    book = load_workbook(exported["workbook"])
    try:
        assert "caller wording" in book["Options"]["B1"].value
        assert book["Options"]["B2"].value == "Unencoded previous diagnosis"
        assert "Unencoded previous diagnosis" not in book["Options"]["H2"].value
        assert "age" in book["Options"]["H2"].value
        assert "Requires" in book["Options"]["F2"].value
        context = book["Decision list"]["I2"]
        assert context.hyperlink.target.startswith("#'Decision evidence'!A")
        evidence = book["Decision evidence"]
        rows = list(evidence.iter_rows(min_row=2, values_only=True))
        assert any(row[3] == "Exact source copy" and row[5] == "Crossover only: ECOG 0–2." for row in rows)
        assert any(row[3] == "Caller note (reading)" and row[6] == "proposed" for row in rows)
        assert all(row[7] == "/protocolSection/eligibilityModule/eligibilityCriteria" for row in rows)
        assert all(c.data_type != "f" for sheet in book for row in sheet for c in row)
    finally:
        book.close()
    text = __import__("pathlib").Path(exported["decision_list"]).read_text()
    assert "Represented profile:" in text and "Deciding criteria:" in text
    assert "caller wording" in text and "Context only" in text


@pytest.mark.parametrize(
    "wrapped, expected",
    [
        ({"present": True, "value": "Years", "source": "/unit"}, "Years"),
        ({"present": True, "value": 0, "source": "/unit"}, 0),
        ({"present": True, "value": False, "source": "/unit"}, False),
        ({"present": True, "value": None, "source": "/unit"}, None),
        ({"present": False, "value": None, "source": "/unit"}, "Not stated"),
    ],
)
def test_source_scalar_display_preserves_zero_false_null_and_missing(wrapped, expected):
    from TrialLedger.clinical_export import _held_scalar

    assert _held_scalar(wrapped) == expected
    assert type(_held_scalar(wrapped)) is type(expected)
