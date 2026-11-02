"""landscape.json schema 3 (refine-landscape-record 1.1-1.6 and 1.8), built from the registry's saved bodies.

Positive: plain registry values are held exactly as the registry holds them, every contract field a body holds
is in the record (the contract's no-false-silence gate, against real records), absences are value objects
only where the registry holds nothing, results keep the registry's nesting with each module's groups keyed
within it, readings are value objects of their contract rule, domain readings appear only where the study's
universe admits their pack, the cohort keeps only what the evidence supports, and the record describes itself.
Negative: no per-value source or link copies, none of the removed sections, no value object for a value the
registry holds, no setting for a general trial, no endpoint among the criterion frequencies, and the validator
names every planted departure.

Unit B's interface (universes.assign, coherence.resolve under an assignment) is stood in for by
tests/universe_shim.py until unit B lands.
"""

import copy
import json
from pathlib import Path

import pytest
from universe_shim import shim_domains

from TrialLedger import contract, landscape
from TrialLedger.contract import FIELDS, holds_value, template_values
from TrialLedger.reading import read_population

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"
BODIES = [
    study
    for name in ("studies-ids-3.json", "studies-osimertinib-subset.json")
    for study in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["studies"]
]
NCT = "protocolSection.identificationModule.nctId"


def build(studies):
    reading = read_population(studies, {})
    manifest = landscape.landscape_manifest(
        studies, "2.0.5", "2026-11-01T00:00:00", "abc", {}, landscape.RULE_VERSIONS
    )
    record = landscape.landscape_record(
        reading, studies, {"ids": []}, {"query": {}}, manifest, None, shim_domains
    )
    return json.loads(json.dumps(record, ensure_ascii=False))


@pytest.fixture(scope="module")
def record():
    return build(BODIES)


def by_nct(record, nct):
    return next(study for study in record["studies"] if study["nct"] == nct)


def body(nct):
    return next(study for study in BODIES if template_values(study, NCT) == [nct])


# ── the record as a whole ─────────────────────────────────────────────────────────────────────────────


def test_a_record_of_the_saved_bodies_validates(record):
    assert landscape.schema_problems(record) == ()
    assert list(record) == list(landscape.RECORD_KEYS)
    assert record["schema_version"] == contract.SCHEMA_VERSION == "3"


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
    assert record["universes"] == landscape.universes_table()
    assert [u["name"] for u in record["universes"]] == ["oncology.solid", "oncology.heme", "general"]


def test_the_rule_versions_name_the_universe_table_and_the_display_dictionaries():
    versions = landscape.RULE_VERSIONS
    assert versions["landscape_schema"] == "3"
    assert versions["universes"]["table"] == contract.UNIVERSE_TABLE_VERSION
    assert versions["display"] == contract.DISPLAY_VERSION
    assert versions["contract"] == contract.CONTRACT_VERSION


def test_no_value_carries_its_own_source_or_link(record):
    text = json.dumps(record["studies"])
    assert '"source": "protocolSection' not in text and '"source": "resultsSection' not in text
    for study in record["studies"]:
        assert text.count(f'"link": "{study["link"]}"') == 1


def test_the_removed_sections_are_gone(record):
    assert "review_queue" not in record and "types" not in record["coverage"]
    assert "studies" not in record["coverage"]
    for study in record["studies"]:
        for removed in ("standard_language", "exploratory_measures", "efficacy", "safety", "publications"):
            assert removed not in study
        assert "itemized" not in study["eligibility"]
        for document in study["documents"]:
            assert not {"filename", "upload_date", "has_protocol", "has_sap", "has_icf"} & set(document)


# ── no false silence: every contract field a body holds is in the record ─────────────────────────────


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


# ── results in the registry's nesting ─────────────────────────────────────────────────────────────────


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


def test_every_registered_outcome_names_its_list_and_its_readings(record):
    for study in record["studies"]:
        kinds = [o["category"] for o in study["registered_outcomes"]]
        assert kinds == sorted(kinds, key=["primary", "secondary", "other"].index)
        for outcome in study["registered_outcomes"]:
            assert outcome["endpoint_classes"]["rule"] == "banks.endpoint_classes"
            assert outcome["time_points"]["rule"] == "banks.time_points"


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


# ── readings and universes ────────────────────────────────────────────────────────────────────────────


def test_every_reading_is_a_value_object_of_its_contract_rule(record):
    rules = {field.name: field.source[0] for field in FIELDS if field.kind == "reading"}
    for study in record["studies"]:
        assert study["universe"]["rule"] == rules["studies[].universe"]
        assert study["results_posted"]["rule"] == rules["studies[].results_posted"]
        for criterion in study["criteria"]:
            assert criterion["role"]["rule"] == rules["studies[].criteria[].role"]
            assert all(r["rule"] == rules["studies[].criteria[].readings"] for r in criterion["readings"])
        for name, value in study.get("coordinates", {}).items():
            assert tuple(value) == landscape.READING_KEYS and value["rule"] == "coherence.resolve", name


def test_a_general_trial_carries_no_domain_reading(record):
    psd = by_nct(record, "NCT04852770")
    assert psd["universe"]["result"]["universes"] == ["general"]
    assert "coordinates" not in psd
    assert not any(q["result"]["kind"] == "coordinate_conflict" for q in psd["open_questions"])


def test_a_haematologic_trial_carries_prior_lines_only(record):
    cll = by_nct(record, "NCT01030536")
    assert set(cll["coordinates"]) <= {
        "prior_advanced_lines",
        "prior_advanced_lines_interpolated",
        "prior_advanced_lines_proposed",
    }
    assert "prior_advanced_lines" in cll["coordinates"]
    assert "oncology.heme/prior_lines" in cll["coordinates"]["prior_advanced_lines"]["note"]


def test_a_solid_treatment_trial_carries_setting_lines_and_selection(record):
    solid = [
        study
        for study in record["studies"]
        if study["universe"]["result"]["universes"] == ["oncology.solid"]
        and study["primary_purpose"] == "TREATMENT"
    ]
    assert solid
    for study in solid:
        assert {"setting", "prior_advanced_lines", "selection"} <= set(study["coordinates"])


def test_an_experimental_drug_has_its_class_and_says_why_it_is_unresolved(record):
    cll = by_nct(record, "NCT01030536")
    drug = cll["interventions"][0]
    assert drug["type"] == "DRUG" and drug["name"] == "CAT-8015 20 mcg/kg"
    assert drug["drug_class"]["status"] == "unresolved"
    assert drug["drug_class"]["note"] == landscape.CLASS_NOTES["not_looked_up"]


def test_only_a_study_whose_criteria_could_not_be_itemized_carries_coverage(record):
    for study, held in zip(record["studies"], BODIES, strict=True):
        if "coverage" in study["eligibility"]:
            assert study["eligibility"]["coverage"]["status"] == "unresolved"
        assert (
            study["eligibility"]["text"]
            == template_values(held, "protocolSection.eligibilityModule.eligibilityCriteria")[0]
        )


# ── the cohort ────────────────────────────────────────────────────────────────────────────────────────


def test_the_cohort_holds_no_endpoint_among_criterion_frequencies_and_no_empty_table(record):
    cohort = record["cohort"]
    assert "thresholds" in cohort
    for name, rows in cohort.items():
        if name != "thresholds":
            assert rows, name
    assert not any(
        row["element"].startswith(landscape.ENDPOINT_ELEMENT) for row in cohort.get("frequency", [])
    )
    assert cohort["endpoints"]


def test_a_stratum_holding_every_trial_is_dropped():
    assert landscape.kept_strata({"advanced_first_line": ["B", "A"]}, ["A", "B"]) == []
    assert landscape.kept_strata({"advanced_first_line": ["A"], "setting unresolved": ["B"]}, ["A", "B"]) == [
        "advanced_first_line",
        "setting unresolved",
    ]
    assert landscape.kept_strata({}, ["A"]) == []


def test_by_setting_strata_count_only_trials_a_setting_applies_to(record):
    solid = {s["nct"] for s in record["studies"] if "setting" in s.get("coordinates", {})}
    for row in record["cohort"].get("frequency", []):
        if row["stratum"] != landscape.ALL_TRIALS:
            assert row["trials"] <= len(solid)


# ── the record's refusals ─────────────────────────────────────────────────────────────────────────────


def test_a_reading_of_other_studies_is_refused():
    reading = read_population(BODIES[:2], {})
    manifest = landscape.landscape_manifest(BODIES[:2], "2", "t", "c", {}, landscape.RULE_VERSIONS)
    with pytest.raises(ValueError, match="not of these studies"):
        landscape.landscape_record(reading, BODIES[1::-1], {}, {}, manifest, None, shim_domains)


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (lambda r: r.update(schema_version="2"), ("unknown_schema_version", "schema_version")),
        (lambda r: r.update(extra=1), ("undescribed_field", "extra")),
        (lambda r: r.pop("cohort"), ("missing_field", "cohort")),
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
            lambda r: r["studies"][0]["universe"].update(rule="other.rule"),
            ("wrong_rule", "studies[0].universe"),
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


# ── the pure decisions, both signs ────────────────────────────────────────────────────────────────────


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


def row(domain, interpolated=None, proposals=(), causes=(), packs=("oncology.solid/setting_and_line",)):
    return {
        "domain": list(domain),
        "state": "narrowed",
        "causes": list(causes),
        "interpolated": {"domain": list(interpolated or domain), "state": "narrowed", "causes": []},
        "proposals": [{"relation": r, "domain": list(d), "state": "s", "causes": []} for r, d in proposals],
        "packs": list(packs),
    }


def test_a_coordinate_known_by_one_value_is_known_and_a_default_never_known():
    found = dict(landscape.coordinate_readings(row(["adjuvant"], causes=[("setting", ["x"], "criterion 2")])))
    assert found[""]["status"] == "known" and found[""]["result"] == ["adjuvant"]
    assert (
        "x removed by criterion 2" in found[""]["note"]
        and "pack oncology.solid/setting_and_line" in found[""]["note"]
    )
    assert found["_interpolated"]["note"] == "no default relation narrows it"
    assert "_proposed" not in found
    widened = dict(landscape.coordinate_readings(row(["a", "b"], interpolated=["a"])))
    assert widened[""]["status"] == "unresolved" and widened["_interpolated"]["status"] == "interpolated"


def test_a_proposal_is_proposed_and_one_leaving_nothing_unresolved():
    found = dict(landscape.coordinate_readings(row(["a", "b"], proposals=[("p1", ["a"])])))
    assert found["_proposed"]["status"] == "proposed"
    assert found["_proposed"]["result"] == [{"relation": "p1", "domain": ["a"]}]
    empty = dict(landscape.coordinate_readings(row(["a", "b"], proposals=[("p1", [])])))
    assert empty["_proposed"]["status"] == "unresolved"


def test_gene_selection_names_only_narrowed_genes():
    full = ["negative", "positive", "unknown"]
    found = dict(landscape.selection_readings({"EGFR": row(["positive"]), "ALK": row(full)}))
    assert found[""]["status"] == "known" and found[""]["result"] == {"EGFR": ["positive"]}
    none = dict(landscape.selection_readings({"EGFR": row(full)}))
    assert none[""]["status"] == "unresolved" and none[""]["note"] == "no gene's state is stated"


def test_a_drug_class_is_known_only_when_classified_or_stated():
    assert landscape.drug_class_reading(["d", "classified", ["EPC"], "d"])["status"] == "known"
    assert landscape.drug_class_reading(["d", "stated_by_record", ["s"], "description"])["status"] == "known"
    for state in ("unresolved", "lookup_failed", "not_looked_up"):
        held = landscape.drug_class_reading(["d", state, [], ""])
        assert held["status"] == "unresolved" and held["note"] == landscape.CLASS_NOTES[state]
    assert landscape.drug_class_reading(["d", "odd", [], ""])["note"] == "odd"


def test_criteria_are_numbered_within_their_heading_with_a_role_and_readings():
    atom = ("biomarker_status", "biomarker:EGFR", ("positive",), (), 0, 4)
    criteria = [
        (1, "inclusion", "EGFR mutation", [atom]),
        (2, "inclusion", "Age 18", []),
        (4, "exclusion", "Pregnancy", []),
    ]
    found = landscape.criterion_entries(criteria)
    assert [(c["heading"], c["number"]) for c in found] == [
        ("inclusion", 1),
        ("inclusion", 2),
        ("exclusion", 1),
    ]
    assert found[0]["readings"][0]["words"] == ["EGFR"]
    assert found[1]["readings"] == []
    assert found[2]["role"]["result"] == "exclusion"
    mentions = landscape.biomarker_mentions(found, [])
    assert [m["result"]["biomarker"] for m in mentions] == ["EGFR"]
    assert mentions[0]["result"]["at"] == "criteria/0"


def test_an_outcome_naming_a_biomarker_endpoint_is_a_mention_and_another_is_not():
    outcome = {
        "category": "secondary",
        "measure": "ctDNA",
        "endpoint_classes": {"result": ["biomarker_endpoint"]},
    }
    other = {"category": "primary", "measure": "OS", "endpoint_classes": {"result": ["overall_survival"]}}
    found = landscape.biomarker_mentions([], [other, outcome])
    assert [m["result"]["at"] for m in found] == ["registered_outcomes/1"]
    assert found[0]["result"]["role"] == "secondary outcome"


def test_open_questions_leave_out_a_coordinate_the_universe_does_not_admit():
    flags = [
        ("coordinate_conflict", "setting", "why", "1", ["e"], "q", ["a"]),
        ("drug_class_unresolved", "X", "why2", "3", [], "q2", ["b"]),
    ]
    assert [q["result"]["kind"] for q in landscape.open_questions(flags, set())] == ["drug_class_unresolved"]
    assert len(landscape.open_questions(flags, {"setting"})) == 2


def test_criteria_evidence_is_what_the_view_narrows_by():
    atom = ("b", "setting_word:adjuvant", ("adjuvant",), (("scope", "disease"),), 0, 3)
    assert landscape.criteria_evidence([(3, "inclusion", "adj", [atom])]) == [
        ("inclusion", "setting_word:adjuvant", ("adjuvant",), "disease", "criterion 3")
    ]


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
    ],
)
def test_value_problem(node, kind, rule, expected):
    assert landscape.value_problem(node, kind, rule) == expected


# ── key criteria and standard protocol language (task 1.8) ──────────────────────────────────────────


@pytest.mark.parametrize(
    ("concept", "values", "expected"),
    [
        ("ecog_ps", ["0", "1"], "performance_status"),
        ("biomarker:EGFR", ["positive"], "biomarker_selection"),
        ("prior_lines", ["1"], "prior_therapy_and_line"),
        ("prior_agent", ["platinum"], "prior_therapy_and_line"),
        ("lab", ["ANC"], "organ_function"),
        ("condition", ["cns_metastases"], "cns_metastases"),
        ("condition", ["hepatitis"], "hiv_and_hepatitis"),
        ("condition", ["qtc"], "cardiac_history"),
        ("condition", ["pregnancy_or_breastfeeding"], ""),
        ("age", ["18"], ""),
        ("biomarker", [], ""),
    ],
)
def test_key_category(concept, values, expected):
    assert landscape.key_category(concept, values) == expected


def test_a_criterion_with_a_key_reading_is_a_key_criterion_once_a_category():
    atoms = [
        ("biomarker_status", "biomarker:EGFR", ("positive",), (), 0, 4),
        ("biomarker_status", "biomarker:MET", ("negative",), (), 5, 8),
        ("age", "age", ("18",), (), 0, 2),
    ]
    criteria = landscape.criterion_entries([(1, "inclusion", "EGFR mutation, MET negative", atoms)])
    found = landscape.key_criteria(criteria)
    assert len(found) == 1
    assert found[0]["words"] == ["EGFR mutation, MET negative"]
    assert found[0]["result"]["category"] == "biomarker_selection"
    assert found[0]["result"]["role"] == "inclusion" and found[0]["result"]["at"] == "criteria/0"
    assert [r["concept"] for r in found[0]["result"]["readings"]] == ["biomarker:EGFR", "biomarker:MET"]
    assert landscape.key_criteria(landscape.criterion_entries([(1, "inclusion", "Age 18", [atoms[2]])])) == []


def trial(nct, universes, texts):
    atom = ("performance_status", "ecog_ps", ("0", "1"), (), 0, 4)
    criteria = landscape.criterion_entries([(i, "inclusion", text, [atom]) for i, text in enumerate(texts)])
    return {"nct": nct, "universe": {"result": {"universes": universes}}, "criteria": criteria}


def test_a_reading_most_trials_of_a_universe_state_is_standard_with_its_wording():
    studies = [
        trial("NCT3", ["oncology.solid"], ["ECOG 0-1"]),
        trial("NCT1", ["oncology.solid"], ["ECOG performance status of 0 or 1 at screening"]),
        trial("NCT2", ["oncology.solid"], ["ECOG 0 or 1"]),
        trial("NCT4", ["oncology.solid"], []),
    ]
    found = landscape.standard_language(studies)
    assert found["not_assessed"] == []
    [row] = found["rows"]
    assert (row["stating"], row["of"], row["trials"]) == (3, 4, ["NCT1", "NCT2", "NCT3"])
    assert [w["text"] for w in row["wording"]] == [
        "ECOG 0-1",
        "ECOG performance status of 0 or 1 at screening",
    ]
    assert row["wording"][0]["nct"] == "NCT3" and row["wording"][0]["at"] == "/studies/0/criteria/0"
    assert row["role"] == "inclusion" and row["universe"] == "oncology.solid"


def test_a_reading_too_few_trials_state_is_not_standard_and_a_small_universe_is_not_assessed():
    studies = [trial(f"NCT{i}", ["oncology.solid"], ["ECOG 0-1"] if i < 2 else []) for i in range(5)]
    studies.append(trial("NCT9", ["general"], ["ECOG 0-1"]))
    found = landscape.standard_language(studies)
    assert found["rows"] == []
    assert found["not_assessed"] == [
        {"universe": "general", "trials": 1, "reason": "too few trials to assess (1; at least 3 needed)"}
    ]


def test_the_record_holds_key_criteria_and_standard_language(record):
    assert set(record["standard_language"]) == {"share", "minimum_trials", "rows", "not_assessed"}
    for study in record["studies"]:
        for key in study["key_criteria"]:
            criterion = study["criteria"][int(key["result"]["at"].rpartition("/")[2])]
            assert key["words"] == [criterion["text"]]
    assert any(study["key_criteria"] for study in record["studies"])
