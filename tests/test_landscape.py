"""Registry-only landscape reporting: exact source values, direct states and no clinical inference.

The saved registry specimens exercise group scope, precision, absence, schema refusals and source
correspondence. Interpretation engine tests remain in their separate layer-two test modules.
"""

import copy
import json
from pathlib import Path

import pytest

from TrialLedger import contract, landscape
from TrialLedger.contract import FIELDS, holds_value, template_values

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"


BODIES = [
    study
    for name in ("studies-ids-3.json", "studies-osimertinib-subset.json")
    for study in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["studies"]
]


NCT = "protocolSection.identificationModule.nctId"


def build(studies, answers=None):
    manifest = landscape.landscape_manifest(
        studies, "2.0.5", "2026-11-01T00:00:00", "abc", {}, landscape.RULE_VERSIONS
    )
    record = landscape.landscape_record(studies, {"ids": []}, {"query": {}}, manifest, answers)
    return json.loads(json.dumps(record, ensure_ascii=False))


@pytest.fixture(scope="module")
def record():
    return build(BODIES)


def by_nct(record, nct):
    return next(study for study in record["studies"] if study["nct"] == nct)


def body(nct):
    return next(study for study in BODIES if template_values(study, NCT) == [nct])


def test_a_record_of_the_saved_bodies_validates(record):
    assert landscape.schema_problems(record) == ()
    assert list(record) == list(landscape.RECORD_KEYS)
    assert record["schema_version"] == contract.SCHEMA_VERSION == 4


def test_the_record_describes_every_contract_field_once(record):
    assert set(record["fields"]) == {field.name for field in FIELDS}
    brief = record["fields"]["studies[].brief_title"]
    assert brief == {
        "label": "Brief title",
        "kind": "plain",
        "source": ["protocolSection.identificationModule.briefTitle"],
        "form": "as held",
        "display": "",
        "reads": [],
    }
    assert not {"universes", "coverage", "cohort", "recurring_criteria"} & record.keys()


def test_the_rule_versions_name_the_source_contract_and_display_dictionaries():
    versions = landscape.RULE_VERSIONS
    assert versions["landscape_schema"] == 4
    assert versions["display"] == contract.DISPLAY_VERSION
    assert versions["contract"] == contract.CONTRACT_VERSION


def test_no_value_carries_its_own_source_or_link(record):
    text = json.dumps(record["studies"])
    assert '"source": "protocolSection' not in text and '"source": "resultsSection' not in text
    for study in record["studies"]:
        assert text.count(f'"link": "{study["link"]}"') == 1


def test_the_removed_sections_are_gone(record):
    assert not {"review_queue", "universes", "coverage", "cohort", "recurring_criteria"} & record.keys()
    for study in record["studies"]:
        for removed in ("standard_language", "exploratory_measures", "efficacy", "safety", "publications"):
            assert removed not in study
        assert "itemized" not in study["eligibility"]
        for document in study["documents"]:
            assert not {"filename", "upload_date", "has_protocol", "has_sap", "has_icf"} & set(document)


def record_places(study, name):
    """Every value the record holds at a contract field's name, by its list positions (absences left out)."""
    nodes = [((), study)]
    for part in name.split(".")[1:]:
        following = []
        for positions, node in nodes:
            key = part.removesuffix("[]")
            if not isinstance(node, dict) or key not in node:
                continue
            held = node[key]
            if part.endswith("[]"):
                following += [
                    ((*positions, i), item) for i, item in enumerate(held if isinstance(held, list) else [])
                ]
            else:
                following.append((positions, held))
        nodes = following
    return [
        held for _, held in nodes if not (isinstance(held, dict) and tuple(held) == landscape.ABSENT_KEYS)
    ]


def test_every_contract_field_a_body_holds_is_in_its_record(record):
    checked = 0
    for study in BODIES:
        extract = by_nct(record, template_values(study, NCT)[0])
        for field in FIELDS:
            if field.kind != "plain" or not field.name.startswith("studies[]."):
                continue
            held = any(
                holds_value(value) for source in field.source for value in template_values(study, source)
            )
            if held:
                assert record_places(extract, field.name), (extract["nct"], field.name)
                checked += 1
    assert checked > 400


def test_a_value_the_registry_does_not_hold_is_not_stated_with_its_absence_state(record):
    psd = by_nct(record, "NCT04852770")
    assert psd["acronym"] == {"status": "not_stated", "note": "not_reported"}
    assert "acronym" not in body("NCT04852770")["protocolSection"]["identificationModule"]
    for study in record["studies"]:
        for key, value in study.items():
            if isinstance(value, dict) and tuple(value) == landscape.ABSENT_KEYS and key != "results_posted":
                source = contract.FIELD_NAMES.get(f"studies[].{key}")
                if source is not None and source.kind == "plain":
                    assert not any(
                        holds_value(v) for t in source.source for v in template_values(body(study["nct"]), t)
                    )


def test_study_level_values_are_the_registrys_exactly(record):
    psd = by_nct(record, "NCT04852770")
    assert psd["brief_title"] == "Efficacy of TBCT, MBHP and PPT for PTSD During the Covid-19 Pandemics"
    assert psd["start_date"] == {"date": "2020-04-06", "type": "ACTUAL"}
    assert psd["last_update_posted"] == "2025-04-04"
    assert psd["lead_sponsor"] == {"name": "Fundação Bahiana de Infectologia", "class": "OTHER"}
    assert psd["phases"] == ["NA"] and psd["dmc"] is False
    assert psd["enrollment"] == {"count": 135, "type": "ACTUAL"}
    assert psd["condition_mesh"] == ["Stress Disorders, Post-Traumatic", "COVID-19"]


def test_countries_are_distinct_and_sites_counted(record):
    cll = by_nct(record, "NCT01030536")
    locations = template_values(body("NCT01030536"), "protocolSection.contactsLocationsModule.locations[]")
    assert cll["site_count"] == len(locations)
    assert cll["countries"] == list(dict.fromkeys(location["country"] for location in locations))


def test_a_posted_measure_keeps_its_groups_denominators_and_na_with_its_comment(record):
    measure = by_nct(record, "NCT01030536")["posted_outcomes"][0]
    assert measure["type"] == "PRIMARY" and measure["title"] == "Maximum Tolerated Dose (MTD)"
    assert measure["groups"][:2] == [
        {"id": "OG000", "title": "CAT-8015 20 Microgram Per Kilogram (mcg/kg)", **measure["groups"][0]},
        {"id": "OG001", "title": "CAT-8015 30 Microgram Per Kilogram (mcg/kg)", **measure["groups"][1]},
    ]
    assert measure["denominators"][0]["units"] == "Participants"
    assert measure["denominators"][0]["counts"][:2] == [
        {"group": "OG000", "value": "7"},
        {"group": "OG001", "value": "6"},
    ]
    first = measure["classes"][0]["categories"][0]["measurements"][0]
    assert first == {
        "group": "OG000",
        "value": "NA",
        "comment": "Data was not reported as MTD was not reached in the specified arm group.",
    }


def test_an_untitled_class_is_left_untitled_never_not_stated(record):
    klass = by_nct(record, "NCT01030536")["posted_outcomes"][0]["classes"][0]
    assert "title" not in klass and "title" not in klass["categories"][0]


def test_baseline_flow_and_adverse_events_keep_their_own_groups_and_listed_zeros(record):
    cll = by_nct(record, "NCT01030536")
    age = next(m for m in cll["baseline"]["measures"] if m["title"] == "Age, Continuous")
    assert age["param_type"] == "MEAN" and age["dispersion_type"] == "STANDARD_DEVIATION"
    measured = age["classes"][0]["categories"][0]["measurements"]
    assert measured[:2] == [
        {"group": "BG000", "value": "63.4", "spread": "8.7"},
        {"group": "BG001", "value": "53.7", "spread": "16.9"},
    ]
    assert cll["baseline"]["groups"][0]["id"] == "BG000"
    period = cll["participant_flow"]["periods"][0]
    assert period["title"] == "Overall Study" and period["milestones"][0]["type"] == "STARTED"
    assert period["milestones"][0]["counts"][:2] == [
        {"group": "FG000", "participants": "7"},
        {"group": "FG001", "participants": "6"},
    ]
    events = cll["adverse_events"]
    assert events["frequency_threshold"] == "5"
    assert events["all_cause_mortality_comment"] == {"status": "not_stated", "note": "not_reported"}
    assert events["groups"][0]["id"] == "EG000" and events["groups"][0]["serious_affected"] == 0
    lung = next(e for e in events["events"] if e["term"] == "Lung infection")
    assert lung["table"] == "serious"
    assert lung["counts"][:2] == [
        {"group": "EG000", "affected": 0, "at_risk": 7, "events": 0},
        {"group": "EG001", "affected": 0, "at_risk": 6, "events": 0},
    ]


def test_groups_of_different_modules_are_never_merged(record):
    cll = by_nct(record, "NCT01030536")
    titles = {group["title"] for group in cll["adverse_events"]["groups"]}
    assert titles & {group["title"] for group in cll["baseline"]["groups"]}
    assert {g["id"][:2] for g in cll["adverse_events"]["groups"]} == {"EG"}
    assert {g["id"][:2] for g in cll["baseline"]["groups"]} == {"BG"}


def test_a_study_without_results_has_no_results_modules_but_why(record):
    psd = by_nct(record, "NCT04852770")
    for module in ("posted_outcomes", "baseline", "participant_flow", "adverse_events"):
        assert psd[module] == {"status": "not_posted", "note": "no results are posted for the study"}
    assert psd["results_posted"]["status"] == "not_posted"
    assert psd["registered_outcomes"], "a registered outcome stays, planned"


def test_every_registered_outcome_preserves_its_source_list_and_literal_words(record):
    for study in record["studies"]:
        original = body(study["nct"])["protocolSection"].get("outcomesModule", {})
        expected = [
            (kind, entry)
            for kind, key in (
                ("primary", "primaryOutcomes"),
                ("secondary", "secondaryOutcomes"),
                ("other", "otherOutcomes"),
            )
            for entry in original.get(key, [])
        ]
        assert len(study["registered_outcomes"]) == len(expected)
        for outcome, (kind, entry) in zip(study["registered_outcomes"], expected, strict=True):
            assert outcome["category"] == kind
            assert outcome["measure"] == entry["measure"]
            if "timeFrame" in entry:
                assert outcome["time_frame"] == entry["timeFrame"]
            assert "endpoint_classes" not in outcome and "time_points" not in outcome


def test_every_element_is_addressable_by_a_json_pointer(record):
    def pointer(node, path):
        for part in path.strip("/").split("/"):
            node = node[int(part)] if isinstance(node, list) else node[part]
        return node

    held = pointer(record, "/studies/0/posted_outcomes/0/classes/0/categories/0/measurements/1")
    assert (
        held
        == by_nct(record, "NCT01030536")["posted_outcomes"][0]["classes"][0]["categories"][0]["measurements"][
            1
        ]
    )


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (lambda r: r.update(schema_version="3"), ("unknown_schema_version", "schema_version")),
        (lambda r: r.update(extra=1), ("undescribed_field", "extra")),
        (lambda r: r.pop("studies"), ("missing_field", "studies")),
        (lambda r: r["fields"].pop("studies[].nct"), ("fields_differ", "fields")),
        (lambda r: r["studies"][0].update(sponsor="X"), ("undescribed_field", "studies[0].sponsor")),
        (lambda r: r["studies"][0].pop("brief_title"), ("missing_field", "studies[0].brief_title")),
        (lambda r: r["studies"][0].update(link="x"), ("wrong_link", "studies[0].link")),
        (
            lambda r: r["studies"][0].update(acronym={"status": "known", "note": ""}),
            ("unknown_status", "studies[0].acronym"),
        ),
        (lambda r: r["studies"][0].update(acronym={"value": 1}), ("malformed_value", "studies[0].acronym")),
        (
            lambda r: r["studies"][0]["results_posted"].update(rule="other.rule"),
            ("wrong_rule", "studies[0].results_posted"),
        ),
        (lambda r: r["studies"][0].update(arms={}), ("wrong_type", "studies[0].arms")),
        (lambda r: r["studies"][0].update(digest="0"), ("digest_mismatch", "manifest.study_digests")),
        (lambda r: r["manifest"].update(merkle_root="0"), ("root_mismatch", "manifest.merkle_root")),
    ],
)
def test_the_validator_names_each_departure(record, change, expected):
    broken = copy.deepcopy(record)
    change(broken)
    assert expected in landscape.schema_problems(broken)


def test_a_record_that_is_not_an_object_is_refused():
    assert landscape.schema_problems([]) == (("not_an_object", ""),)


def test_list_prefix_and_below():
    assert landscape.list_prefix("a.b[].c[].d") == "a.b[]"
    assert landscape.list_prefix("a.b") == ""
    assert landscape.below("a.b[].c", "a.b[]") == "c"
    assert landscape.below("a.b[]", "a.b[]") == ""
    assert landscape.below("a.b", "") == "a.b"


@pytest.mark.parametrize(
    ("node", "template", "form", "word", "expected"),
    [
        ({"a": "x"}, "a", "as held", "", ("held", "x")),
        ({"a": 0}, "a", "as held", "", ("held", 0)),
        ({"a": False}, "a", "as held", "", ("held", False)),
        ({"a": ""}, "a", "as held", "", ("absent", None)),
        ({}, "a", "as held", "", ("absent", None)),
        ({"a": ["x", "y"]}, "a[]", "as held", "", ("held", ["x", "y"])),
        ({"a": []}, "a[]", "as held", "", ("absent", None)),
        ({"a": [{"c": "x"}, {"c": "x"}, {"c": "y"}]}, "a[].c", "distinct", "", ("held", ["x", "y"])),
        ({"a": [{}, {}]}, "a[]", "count", "", ("held", 2)),
        ({"a": []}, "a[]", "count", "", ("absent", None)),
        ({}, "", "which list", "serious", ("held", "serious")),
        ({}, "", "which list", "", ("absent", None)),
        ({"a": "NA"}, "a", "as held", "", ("held", "NA")),
    ],
)
def test_leaf_value_by_form(node, template, form, word, expected):
    assert landscape.leaf_value(node, template, form, word) == expected


def test_results_reading_and_module_absence():
    assert landscape.results_reading("posted")["status"] == "known"
    assert landscape.results_reading("not_posted")["status"] == "not_posted"
    assert landscape.results_reading("flag_not_reported")["status"] == "not_stated"
    unresolved = landscape.results_reading("flag_without_results")
    assert unresolved["status"] == "unresolved" and unresolved["note"] == "flag_without_results"
    assert landscape.module_absence("not_posted")["status"] == "not_posted"
    assert landscape.module_absence("posted") == {"status": "not_stated", "note": "not_reported"}


@pytest.mark.parametrize(
    ("node", "kind", "rule", "expected"),
    [
        ("x", "plain", "", "ok"),
        ({"status": "not_stated", "note": "not_reported"}, "plain", "", "ok"),
        ({"status": "not_posted", "note": ""}, "plain", "", "ok"),
        ({"status": "known", "note": ""}, "plain", "", "unknown_status"),
        ({"value": 1}, "plain", "", "malformed_value"),
        ({"status": "not_stated", "note": None}, "plain", "", "malformed_value"),
        ({"status": "known", "rule": "r", "words": [], "result": 1, "note": ""}, "reading", "r", "ok"),
        ([{"status": "known", "rule": "r", "words": [], "result": 1, "note": ""}], "reading", "r", "ok"),
        (
            {"status": "odd", "rule": "r", "words": [], "result": 1, "note": ""},
            "reading",
            "r",
            "unknown_status",
        ),
        (
            {"status": "known", "rule": "q", "words": [], "result": 1, "note": ""},
            "reading",
            "r",
            "wrong_rule",
        ),
        ("x", "reading", "r", "malformed_value"),
        (3, "itemized", "", "ok"),
        ({"category": "x"}, "itemized", "", "ok"),
    ],
)
def test_value_problem(node, kind, rule, expected):
    assert landscape.value_problem(node, kind, rule) == expected


def test_reporting_contains_only_source_fields_and_direct_state_readings(record):
    assert set(record) == {
        "schema_version",
        "request",
        "scope",
        "manifest",
        "statuses",
        "envelope",
        "fields",
        "studies",
    }
    forbidden = {
        "universe",
        "coordinates",
        "key_criteria",
        "biomarker_mentions",
        "open_questions",
        "scoped_assertions",
        "assertion_compilation",
        "axes",
        "modality",
        "endpoint_classes",
        "time_points",
    }

    def inspect(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            if "status" in value and "rule" in value:
                assert value["status"] not in {"interpolated", "proposed"}
                assert value["rule"] in {
                    "ledger.results_state",
                    "landscape.collection_presence",
                    "classes.class_evidence",
                    "checks.run_checks",
                }
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    for study in record["studies"]:
        inspect(study)


@pytest.mark.parametrize("study_type", ["INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS"])
def test_full_eligibility_and_literal_fields_survive_without_a_clinical_reading(study_type):
    source = copy.deepcopy(BODIES[0])
    text = (
        "Inclusion Criteria:\n- Participants with EGFR mutation OR ECOG > 2.\n"
        "- Cohort A: platelets >= 100000/mm3.\n\nExclusion Criteria:\n"
        "- Previous treatment unless the investigator permits it."
    )
    source["protocolSection"]["designModule"]["studyType"] = study_type
    source["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = text
    source["protocolSection"]["eligibilityModule"]["studyPopulation"] = (
        "Source-defined population; not a reconstructed enrolled group."
    )
    [study] = build([source])["studies"]
    assert study["study_type"] == study_type
    assert study["eligibility"]["text"] == text
    assert study["study_population"] == source["protocolSection"]["eligibilityModule"]["studyPopulation"]
    for criterion in study["criteria"]:
        assert (
            {"heading", "number", "text", "source_start", "source_end"}
            <= set(criterion)
            <= {"heading", "number", "text", "source_start", "source_end", "source_context"}
        )
        assert criterion["text"] == text[criterion["source_start"] : criterion["source_end"]]
        assert "readings" not in criterion and "role" not in criterion


def test_changed_raw_eligibility_changes_only_the_corresponding_literal_evidence():
    source = copy.deepcopy(BODIES[0])
    before = build([source])["studies"][0]
    changed = copy.deepcopy(source)
    wording = "Eligibility details are not itemized: a clinician must review this entire sentence."
    changed["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = wording
    after = build([changed])["studies"][0]
    assert before["digest"] != after["digest"]
    assert after["eligibility"]["text"] == wording
    assert before["brief_title"] == after["brief_title"]
    assert before["posted_outcomes"] == after["posted_outcomes"]
    assert after["criteria"]
    assert "".join(passage["text"] for passage in after["criteria"]) == wording
    assert all(passage["heading"] == "unsectioned" for passage in after["criteria"])
    offset = 0
    for passage in after["criteria"]:
        assert passage["source_start"] == offset
        offset += len(passage["text"])
        assert passage["source_end"] == offset


@pytest.mark.parametrize(
    "text,sections",
    [
        (
            "Inclusion Criteria:\nAdults.\nExclusion Criteria:\nNo prior treatment.",
            [
                ("inclusion", "Inclusion Criteria:\nAdults.\n"),
                ("exclusion", "Exclusion Criteria:\nNo prior treatment."),
            ],
        ),
        (
            "No exclusion is implied by this unsectioned source sentence.",
            [
                ("unsectioned", "No exclusion is implied by this unsectioned source sentence."),
            ],
        ),
        (
            "Eligibility:\nParticipants may have ECOG 0 or 1.",
            [
                ("unsectioned", "Eligibility:\nParticipants may have ECOG 0 or 1."),
            ],
        ),
        (
            "Inclusion Criteria:\nFirst.\nInclusion Criteria:\nRepeated.\nExclusion Criteria:\nLast.",
            [
                (
                    "unsectioned",
                    "Inclusion Criteria:\nFirst.\nInclusion Criteria:\nRepeated.\nExclusion Criteria:\nLast.",
                ),
            ],
        ),
    ],
)
def test_only_exact_unambiguous_source_headings_classify_source_passages(text, sections):
    source = copy.deepcopy(BODIES[0])
    source["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = text
    [study] = build([source])["studies"]
    assert study["eligibility"]["text"] == text
    grouped = []
    for passage in study["criteria"]:
        if grouped and grouped[-1][0] == passage["heading"]:
            grouped[-1] = (passage["heading"], grouped[-1][1] + passage["text"])
        else:
            grouped.append((passage["heading"], passage["text"]))
    assert grouped == sections
    assert "".join(c["text"] for c in study["criteria"]) == text
    offset = 0
    for criterion in study["criteria"]:
        assert criterion["source_start"] == offset
        offset += len(criterion["text"])
        assert criterion["source_end"] == offset
        assert (
            {"heading", "number", "text", "source_start", "source_end"}
            <= set(criterion)
            <= {"heading", "number", "text", "source_start", "source_end", "source_context"}
        )


@pytest.mark.parametrize(
    "text",
    [
        "Literal source text without a heading. " * 500,
        "\n".join(f"Literal source evidence line {number}." for number in range(800)),
    ],
)
def test_long_eligibility_is_visible_as_bounded_exact_source_passages(text):
    original = copy.deepcopy(BODIES[0])
    original["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = text
    [study] = build([original])["studies"]
    passages = study["criteria"]
    assert len(passages) > 1
    assert study["eligibility"]["text"] == "".join(p["text"] for p in passages) == text
    offset = 0
    for passage in passages:
        assert passage["heading"] == "unsectioned"
        assert passage["source_start"] == offset
        assert 0 < len(passage["text"]) <= 1600
        offset += len(passage["text"])
        assert passage["source_end"] == offset
        assert set(passage) == {"heading", "number", "text", "source_start", "source_end"}
    assert offset == len(text)
