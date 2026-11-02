"""Authored clinical display obligations: preserve scoped evidence, never imply absent clinical facts."""

from TrialLedger import readout
from TrialLedger.readout import analysis_rows, denominator_words, spread_words


def test_source_present_masking_roles_survive_missing_or_none_masking_in_every_study_type():
    from schema3_records import record_of
    from test_study_type_acceptance import NCT, source

    for kind in ("INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS"):
        for masking in (None, "NONE"):
            body = source(kind, extras=False)
            info = {"whoMasked": ["PARTICIPANT", "OUTCOMES_ASSESSOR"]}
            if masking is not None:
                info["masking"] = masking
            body["protocolSection"]["designModule"]["designInfo"] = {"maskingInfo": info}
            study = record_of((NCT,), {NCT: body})["studies"][0]
            assert study["who_masked"] == ["PARTICIPANT", "OUTCOMES_ASSESSOR"]
            index = readout.design_words(study)
            assert "Who is masked: Participant, Outcomes assessor" in index
            assert "interventional design fields not applicable" not in index
            facts = {fact: (value, basis) for _, _, fact, value, basis in readout.dossier_facts(study)}
            assert facts["Who is masked"] == ("Participant; Outcomes assessor", "Registry")
            info.pop("whoMasked")
            missing = record_of((NCT,), {NCT: body})["studies"][0]
            assert "Who is masked:" not in readout.design_words(missing)
            assert not any(fact == "Who is masked" for _, _, fact, _, _ in readout.dossier_facts(missing))


def test_source_dispersion_type_survives_without_numeric_spread_or_limits():
    assert spread_words("Standard Deviation", {}) == "Standard Deviation: Not stated"
    assert spread_words("STANDARD_DEVIATION", {}, "MeasureDispersionType") == "Standard deviation: Not stated"
    assert spread_words("STANDARD_ERROR", {}, "MeasureDispersionType") == "Standard error: Not stated"
    assert spread_words(None, {}) == "Not stated"
    assert spread_words({"status": "not_stated", "note": "not_reported"}, {}) == "Not stated"
    assert spread_words("NA", {}) == "Not applicable"
    assert (
        spread_words("STANDARD_DEVIATION", {"spread": "0"}, "MeasureDispersionType")
        == "Standard deviation: 0"
    )


def test_source_present_phase_and_every_design_field_survive_type_applicability():
    from schema3_records import record_of
    from test_study_type_acceptance import NCT, source

    for kind in ("INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS"):
        body = source(kind, extras=False)
        body["protocolSection"]["designModule"].update(
            {
                "phases": ["PHASE2"],
                "designInfo": {
                    "primaryPurpose": "TREATMENT",
                    "allocation": "RANDOMIZED",
                    "interventionModel": "PARALLEL",
                    "maskingInfo": {"masking": "DOUBLE", "whoMasked": ["PARTICIPANT"]},
                },
            }
        )
        study = record_of((NCT,), {NCT: body})["studies"][0]
        facts = {fact: value for _, _, fact, value, _ in readout.dossier_facts(study)}
        for label, value in (
            ("Phase", "Phase 2"),
            ("Primary purpose", "Treatment"),
            ("Allocation", "Randomized"),
            ("Intervention model", "Parallel assignment"),
            ("Masking", "Double"),
            ("Who is masked", "Participant"),
        ):
            assert facts[label] == value
        design = readout.design_words(study)
        assert all(
            value in design
            for value in ("Treatment", "Randomized", "Parallel assignment", "Double", "Participant")
        )


def test_unmeasured_source_placeholders_keep_the_measures_declared_dispersion_type():
    from schema3_records import record_of

    study = record_of(("NCT01030536",))["studies"][0]
    outcome = study["posted_outcomes"][0]
    outcome["classes"] = []
    outcome["dispersion_type"] = "Standard Deviation"
    headers = readout.sheet_headers(readout.contract.POSTED, 0)
    row = dict(zip(headers, (c[0] for c in readout.posted_rows(study, 0)[0]), strict=True))
    assert row["Spread or limits"] == "Standard Deviation: Not stated"
    assert row["Value"] == readout.contract.MEASUREMENT_PLACEHOLDER_WORDS["value"]
    baseline = study["baseline"]["measures"][0]
    baseline["classes"] = []
    baseline["dispersion_type"] = "STANDARD_DEVIATION"
    headers = readout.sheet_headers(readout.contract.BASELINE, 0)
    row = dict(zip(headers, (c[0] for c in readout.baseline_rows(study, 0)[0]), strict=True))
    assert row["Spread or limits"] == "Standard deviation: Not stated"
    assert row["Value"] == readout.contract.MEASUREMENT_PLACEHOLDER_WORDS["value"]


def test_dossier_source_links_are_clickable_and_invalid_or_absent_targets_stay_unlinked(tmp_path):
    from openpyxl import load_workbook
    from schema3_records import record_of

    record = record_of(("NCT01030536",))
    study = record["studies"][0]
    study["documents"] = [{"type": "Prot", "url": "https://example.org/source.pdf"}]
    study["references"] = [{"pmid": "12345", "citation": "Literal source citation", "type": "RESULT"}]
    study["links"] = [
        {"label": "Literal source link", "url": "https://example.org/source?x=1&y=2"},
        {"label": "Missing source link"},
        {"label": "Malformed source link", "url": "not a URL"},
    ]
    study["ipd_documents"] = [{"type": "Dataset", "url": "https://example.org/data"}]
    path = tmp_path / "source-links.xlsx"
    readout.write_book(record, path)
    book = load_workbook(path)
    facts = {row[2].value: row[3] for row in list(book[readout.contract.REVIEW])[1:]}
    for fact, url in (
        ("Posted document 1", "https://example.org/source.pdf"),
        ("Publication 1", "https://pubmed.ncbi.nlm.nih.gov/12345/"),
        ("Related link 1", "https://example.org/source?x=1&y=2"),
        ("Shared participant data or document 1", "https://example.org/data"),
    ):
        assert facts[fact].hyperlink.target == url
        assert facts[fact].font.underline == "single"
    assert "Literal source citation" in facts["Publication 1"].value
    assert "https://example.org/source?x=1&y=2" in facts["Related link 1"].value
    assert facts["Related link 2"].hyperlink is None and facts["Related link 3"].hyperlink is None
    assert readout.book_problems(record, path) == []
    book.close()


def test_empty_listing_words_describe_the_record_without_claiming_unposted_source_data():
    words = readout.contract.EMPTY_LISTING_WORDS
    assert words[readout.contract.ANALYSES] == "No statistical-analysis rows listed in these records"
    assert all(
        "listed in these records" in message for sheet, message in words.items() if sheet != "Registry checks"
    )
    assert words["Registry checks"] == "No registry checks in these records"
    assert all("None of these trials" not in message for message in words.values())


def test_declared_rxnav_class_members_stay_attached_without_alternative_language():
    reading = {
        "status": "known",
        "rule": "classes.class_evidence",
        "words": ["Source drug"],
        "result": {
            "state": "classified",
            "resolved_by": "RxNav",
            "classes": [
                ["class-1", "First source class", "has_epc", "FDASPL"],
                ["class-2", "Second source class", "has_moa", "MEDRT"],
            ],
        },
        "note": "",
    }
    words, label = readout.drug_class_words(reading)
    assert (words.splitlines(), label) == (
        [
            "Classes attributed to the exact RxNorm concept",
            "First source class [ID: class-1; relation: has_epc; source: FDASPL]",
            "Second source class [ID: class-2; relation: has_moa; source: MEDRT]",
        ],
        "Direct rule",
    )
    assert " or " not in words
    unresolved = {**reading, "status": "unresolved", "note": "lookup unavailable"}
    assert readout.drug_class_words(unresolved) == ("Unresolved — lookup unavailable", "Unresolved")
    malformed = {**reading, "result": {"classes": [["id", "name"]]}}
    assert readout.drug_class_words(malformed) == (
        "Unresolved — RxNav class result has an unsupported shape",
        "Unresolved",
    )


def test_registry_report_excludes_clinical_inference_but_preserves_exact_eligibility(tmp_path):
    from copy import deepcopy

    from schema3_records import BODIES, record_of

    body = deepcopy(BODIES["NCT01030536"])
    text = (
        "Inclusion Criteria:\nPatients must have EGFR disease or prior therapy.\n\n"
        "Exclusion Criteria:\nCohort A: no brain metastases.\n"
    )
    body["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = text
    record = record_of(("NCT01030536",), bodies={"NCT01030536": body})
    assert record["schema_version"] == 4
    assert not {"universes", "coverage", "cohort", "recurring_criteria"} & record.keys()
    study = record["studies"][0]
    forbidden = {
        "universe",
        "coordinates",
        "key_criteria",
        "biomarker_mentions",
        "scoped_assertions",
        "assertion_compilation",
        "open_questions",
    }
    assert not forbidden & study.keys()
    direct_rules = {
        "classes.class_evidence",
        "checks.run_checks",
        "landscape.criterion_entries",
        "ledger.results_state",
        "landscape.collection_presence",
    }
    assert {
        rule for field in readout.contract._STUDY_FIELDS if field.kind == "reading" for rule in field.source
    } <= direct_rules
    assert not {"interpolated", "proposed"} & record["statuses"].keys()
    assert study["eligibility"]["text"] == text
    for piece in study["criteria"]:
        assert set(piece) == {"heading", "number", "text", "source_start", "source_end"}
        assert text[piece["source_start"] : piece["source_end"]] == piece["text"]
    assert "".join(piece["text"] for piece in study["criteria"]) == text
    assert any(value == text + "\n[End of field]" for _, _, _, value, _ in readout.dossier_facts(study))
    names = {sheet.name for sheet in readout.contract.SHEETS}
    assert not {"Biomarkers", "Across-trial findings", "Recurring wording", "Readings"} & names
    headers = readout.sheet_headers(readout.contract.INDEX, 0)
    assert not {
        "Indication",
        "Treatment setting",
        "Prior lines for advanced disease",
        "Gene selection",
    } & set(headers)
    eligibility = readout.sheet_headers(readout.contract.ELIGIBILITY, 0)
    assert eligibility == (
        "Trial ID",
        "Address in the record",
        "Source section",
        "Passage",
        "Source passage",
    )
    path = tmp_path / "registry-report.xlsx"
    readout.write_book(record, path)
    assert readout.book_problems(record, path) == []


def test_nonstandard_eligibility_headings_remain_uninterpreted_source_passages():
    from copy import deepcopy

    from schema3_records import BODIES, record_of

    body = deepcopy(BODIES["NCT01030536"])
    text = "Cohort A\nMust have EGFR mutation.\nPossible exclusions\nNo prior therapy."
    body["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = text
    study = record_of(("NCT01030536",), bodies={"NCT01030536": body})["studies"][0]
    assert {piece["heading"] for piece in study["criteria"]} == {"unsectioned"}
    assert "".join(piece["text"] for piece in study["criteria"]) == text
    for piece in study["criteria"]:
        assert text[piece["source_start"] : piece["source_end"]] == piece["text"]


def test_long_source_passages_preserve_every_character_and_have_a_readable_prose_width(tmp_path):
    from copy import deepcopy

    from openpyxl import load_workbook
    from schema3_records import BODIES, record_of

    body = deepcopy(BODIES["NCT01030536"])
    text = "Unstandardized heading\n" + "word " * 700 + "\n\nFinal physical line.\n"
    body["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = text
    record = record_of(("NCT01030536",), bodies={"NCT01030536": body})
    pieces = record["studies"][0]["criteria"]
    assert "".join(piece["text"] for piece in pieces) == text
    assert {piece["heading"] for piece in pieces} == {"unsectioned"}
    assert all(len(piece["text"]) <= 1600 for piece in pieces)
    assert all(text[piece["source_start"] : piece["source_end"]] == piece["text"] for piece in pieces)
    path = tmp_path / "source-passages.xlsx"
    readout.write_book(record, path)
    book = load_workbook(path)
    sheet = book[readout.contract.ELIGIBILITY]
    assert sheet.column_dimensions["E"].width == 100
    assert [row[4].value for row in list(sheet)[1:]] == [piece["text"] for piece in pieces]
    book.close()


def test_all_study_types_keep_observational_and_expanded_access_source_fields(tmp_path):
    from copy import deepcopy

    from schema3_records import BODIES, record_of

    for kind in ("OBSERVATIONAL", "EXPANDED_ACCESS", "INTERVENTIONAL"):
        body = deepcopy(BODIES["NCT01030536"])
        protocol = body["protocolSection"]
        design = protocol["designModule"]
        design.update(
            {
                "studyType": kind,
                "patientRegistry": False,
                "targetDuration": "7 Years",
                "bioSpec": {
                    "retention": "SAMPLES_WITH_DNA",
                    "description": "Blood and tissue.\n\nStored separately.",
                },
                "expandedAccessTypes": {"individual": True, "intermediate": False, "treatment": True},
                "nPtrsToThisExpAccNctId": 17,
            }
        )
        design["designInfo"].update(
            {"observationalModel": "NATURAL_HISTORY", "timePerspective": "PROSPECTIVE"}
        )
        protocol["eligibilityModule"].update(
            {
                "studyPopulation": "Patients from two registry sites.\n\nSeparate source cohort.",
                "samplingMethod": "NON_PROBABILITY_SAMPLE",
            }
        )
        protocol["statusModule"]["expandedAccessInfo"] = {
            "hasExpandedAccess": False,
            "nctId": "NCT00000001",
            "statusForNctId": "TEMPORARILY_NOT_AVAILABLE",
        }
        record = record_of(("NCT01030536",), bodies={"NCT01030536": body})
        study = record["studies"][0]
        assert study["expanded_access_types"] == design["expandedAccessTypes"]
        assert study["expanded_access_info"] == protocol["statusModule"]["expandedAccessInfo"]
        facts = {fact: value for _, _, fact, value, _ in readout.dossier_facts(study)}
        expected = {
            "Observational study model": "Natural history",
            "Time perspective": "Prospective",
            "Patient registry": "No",
            "Target follow-up duration": "7 Years",
            "Biospecimen retention": "Samples with DNA",
            "Biospecimen description": "Blood and tissue.\n\nStored separately.\n[End of field]",
            "Study population description": (
                "Patients from two registry sites.\n\nSeparate source cohort.\n[End of field]"
            ),
            "Sampling method": "Non-probability sample",
            "Expanded access: individual patients": "Yes",
            "Expanded access: intermediate-size population": "No",
            "Expanded access: treatment IND/protocol": "Yes",
            "Has expanded access": "No",
            "Linked expanded-access record": "NCT00000001",
            "Linked expanded-access recruitment status": "Temporarily not available",
            "Studies referencing this expanded-access record": 17,
        }
        assert expected.items() <= facts.items()
        path = tmp_path / f"{kind}.xlsx"
        readout.write_book(record, path)
        assert readout.book_problems(record, path) == []


def test_missing_type_specific_fields_do_not_invent_negative_source_values():
    from copy import deepcopy

    from schema3_records import BODIES, record_of

    body = deepcopy(BODIES["NCT01030536"])
    body["protocolSection"]["designModule"]["studyType"] = "OBSERVATIONAL"
    body["protocolSection"]["statusModule"].pop("expandedAccessInfo", None)
    record = record_of(("NCT01030536",), bodies={"NCT01030536": body})
    study = record["studies"][0]
    assert study["observational_model"] == {"status": "not_stated", "note": "not_reported"}
    assert study["expanded_access_types"]["individual"] == {"status": "not_stated", "note": "not_reported"}
    assert readout.shown_field(study, "studies[].expanded_access_types.individual")[0] == "Not stated"
    assert readout.shown_field(study, "studies[].observational_model")[0] == "Not stated"
    assert (
        "No" not in readout.shown_field(study, "studies[].expanded_access_info.hasExpandedAccess")[0].split()
    )


def test_results_availability_keeps_module_absence_distinct_from_empty_listings():
    from copy import deepcopy

    from schema3_records import BODIES, record_of

    body = deepcopy(BODIES["NCT01030536"])
    body["hasResults"] = True
    body["resultsSection"] = {}
    study = record_of(("NCT01030536",), bodies={"NCT01030536": body})["studies"][0]
    for heading in ("Results", "Participant flow", "Safety"):
        rows = readout.availability_rows(study, heading)
        assert rows
        assert all(
            words == "Not stated" and label == readout.STATUS_LABELS["not_stated"] for _, words, label in rows
        )
    body["resultsSection"] = {
        "outcomeMeasuresModule": {"outcomeMeasures": []},
        "baselineCharacteristicsModule": {"measures": []},
        "participantFlowModule": {"periods": []},
        "adverseEventsModule": {"seriousEvents": [], "otherEvents": []},
    }
    study = record_of(("NCT01030536",), bodies={"NCT01030536": body})["studies"][0]
    assert readout.availability_rows(study, "Results")[0][1] == "0 measures, 0 values (Posted results)"
    assert readout.availability_rows(study, "Participant flow")[0][1].startswith("0:")
    assert readout.availability_rows(study, "Safety")[0][1] == "0 serious and 0 other terms (Safety)"
    study["participant_flow"] = {"status": "not_posted", "note": "not_posted"}
    assert readout.availability_rows(study, "Participant flow")[0][1] == "Not posted"


def test_collection_reporting_requires_every_counted_source_array():
    assert readout.collection_state({}, ("/first",)) == "untracked"
    for states, expected in (
        ({"/first": "stated", "/second": "stated_empty"}, "stated"),
        ({"/first": "stated_empty", "/second": "not_stated"}, "not_stated"),
        ({"/first": "not_stated", "/second": "malformed"}, "malformed"),
        ({"/first": "stated"}, "untracked"),
    ):
        reading = {
            "status": "known",
            "rule": "landscape.collection_presence",
            "words": [],
            "result": states,
            "note": "",
        }
        study = {"collection_presence": reading}
        assert readout.collection_state(study, ("/first", "/second")) == expected
        words, label = readout.collection_summary(study, ("/first", "/second"), "0 listed items")
        if expected == "stated":
            assert (words, label) == ("0 listed items", "Registry")
        elif expected == "not_stated":
            assert (words, label) == ("Not stated", "Not stated")
        else:
            assert words.startswith("Unresolved") and label == "Unresolved"


def test_sparse_interventional_design_and_enrollment_do_not_invent_applicability():
    from schema3_records import record_of
    from test_study_type_acceptance import NCT, source

    study = record_of((NCT,), {NCT: source("INTERVENTIONAL", extras=False)})["studies"][0]
    assert readout.design_words(study) == "Interventional — design not stated"
    assert readout.shown_field(study, "studies[].enrollment.count") == ("Not stated", "Not stated")


def test_confidence_metadata_survives_without_either_bound():
    study = {
        "nct": "NCT00000001",
        "posted_outcomes": [
            {"title": "Response", "analyses": [{"ci_percent": "95", "ci_sides": "TWO_SIDED"}]}
        ],
    }
    interval = analysis_rows(study, 0)[0][7][0]
    assert "95%" in interval and "2-sided" in interval
    assert interval != "Not stated" and "Not stated to Not stated" in interval


def test_absent_confidence_metadata_does_not_invent_a_level_or_sides():
    study = {"nct": "NCT00000001", "posted_outcomes": [{"analyses": [{}]}]}
    assert analysis_rows(study, 0)[0][7][0] == "Not stated"


def test_dispersion_retains_spread_and_limits_together():
    assert spread_words("Standard deviation", {"spread": "2.4", "lower_limit": "1", "upper_limit": "5"}) == (
        "Standard deviation: 2.4; Standard deviation limits: 1 to 5"
    )
    assert spread_words("NA", {}) == "Not applicable"
    assert spread_words(None, {}) == "Not stated"


def test_scope_denominators_are_not_replaced_by_one_another():
    scopes = [
        {"denominators": [{"units": "Eyes", "counts": [{"group": "g", "value": "14"}]}]},
        {"denominators": [{"units": "Participants", "counts": [{"group": "g", "value": "9"}]}]},
        {"denominators": [{"units": "Participants", "counts": [{"group": "g", "value": "11"}]}]},
    ]
    assert (
        denominator_words(scopes, "g") == "Class denominator: 14 Eyes; Measure denominator: 9 Participants; "
        "Module denominator: 11 Participants"
    )
    assert denominator_words(scopes, "other") == "Not stated"


def test_baseline_keeps_measure_and_module_populations():
    baseline = {
        "population": "All randomized",
        "groups": [{"id": "g", "title": "Drug"}],
        "measures": [
            {
                "title": "Age",
                "population": "Age recorded",
                "classes": [{"categories": [{"measurements": [{"group": "g", "value": "55"}]}]}],
            }
        ],
    }
    row = readout.baseline_rows({"nct": "NCT00000001", "baseline": baseline}, 0)[0]
    assert row[3][0] == "Measure population: Age recorded\nBaseline population: All randomized"


def test_enrollment_count_stays_numeric_and_missing_type_is_explicit():
    from schema3_records import record_of

    study = record_of(("NCT01030536",))["studies"][0]
    study["enrollment"] = {"count": 1234, "type": "ACTUAL"}
    headers = readout.sheet_headers(readout.contract.INDEX, 0)
    row = dict(zip(headers, (c[0] for c in readout.index_cells(study, "", "")), strict=True))
    assert row["Enrollment"] == 1234 and isinstance(row["Enrollment"], int)
    assert row["Enrollment type"] == "Actual"
    study["enrollment"] = {"count": 1234}
    row = dict(zip(headers, (c[0] for c in readout.index_cells(study, "", "")), strict=True))
    assert row["Enrollment"] == 1234 and row["Enrollment type"] == "Not stated"
    assert readout.shown_field(study, "studies[].enrollment.count")[0] == "1,234 (Not stated)"


def test_many_group_safety_keeps_every_count_and_fixed_identifiers(tmp_path):
    from openpyxl import load_workbook
    from schema3_records import record_of

    record = record_of(("NCT01030536",))
    study = record["studies"][0]
    study["adverse_events"] = {
        "groups": [
            {"id": f"g{i}", "title": f"Regimen {i}", "description": f"Registered group {i}"}
            for i in range(24)
        ],
        "events": [
            {
                "table": "serious",
                "term": "Listed event",
                "counts": [
                    {"group": f"g{i}", "affected": i, "at_risk": 100, "events": i * 2} for i in range(24)
                ],
            }
        ],
    }
    path = tmp_path / "many-groups.xlsx"
    readout.write_book(record, path)
    book = load_workbook(path)
    sheet = book[readout.contract.SAFETY]
    headers = [cell.value for cell in sheet[1]]
    cells = dict(zip(headers, [cell.value for cell in sheet[2]], strict=True))
    assert sheet.freeze_panes == "F2"
    assert sheet.column_dimensions["E"].width == 28
    assert cells["G1 affected"] == 0 and cells["G24 affected"] == 23
    assert cells["G24 at risk"] == 100 and cells["G24 events"] == 46
    assert len([name for name in headers if name.startswith("G")]) == 72
    assert len(book[readout.contract.GROUPS]["A"]) >= 25
    assert readout.book_problems(record, path) == []
    book.close()


def test_observational_and_expanded_access_designs_use_record_applicability():
    not_applicable = {"status": "not_stated", "note": "not_applicable"}
    for study_type, words in (("OBSERVATIONAL", "Observational"), ("EXPANDED_ACCESS", "Expanded access")):
        study = {
            "study_type": study_type,
            **{
                name: not_applicable
                for name in ("phases", "primary_purpose", "allocation", "intervention_model", "masking")
            },
        }
        assert readout.design_words(study) == f"{words} — interventional design fields not applicable"
        assert not readout.applies("studies[].allocation", study)
        # A conflicting supplied field remains visible; applicability cannot delete registry content.
        study["allocation"] = "RANDOMIZED"
        assert readout.applies("studies[].allocation", study)
        assert "Randomized" in readout.design_words(study)
    assert readout.applies(
        "studies[].allocation", {"allocation": {"status": "not_stated", "note": "not_reported"}}
    )


def test_empty_result_levels_keep_metadata_without_fabricating_measurements():
    measure = {
        "title": "Response",
        "description": "Registered response definition",
        "unit": "percent",
        "classes": [
            {"title": "Analyzed subset", "categories": [{"title": "Responders", "measurements": []}]}
        ],
    }
    study = {"nct": "NCT00000001", "posted_outcomes": [measure]}
    row = readout.posted_rows(study, 0)[0]
    assert row[1][0] == "/studies/0/posted_outcomes/0/classes/0/categories/0"
    assert row[3][0] == "Response" and row[4][0] == "Registered response definition"
    assert row[8][0] == "Analyzed subset" and row[9][0] == "Responders"
    assert row[10][0] == "Not applicable — no measurement"
    assert row[13][0] == "No measurements posted" and row[15][0] == "percent"
    assert "Not posted" not in [c[0] for c in row]
    baseline = {
        "nct": "NCT00000001",
        "baseline": {"population": "Randomized population", "measures": [{"title": "Age", "unit": "years"}]},
    }
    row = readout.baseline_rows(baseline, 0)[0]
    assert row[1][0] == "/studies/0/baseline/measures/0"
    assert row[2][0] == "Age" and "Randomized population" in row[3][0]
    assert row[9][0] == "No measurements posted" and row[11][0] == "years"


def test_denominator_qualifiers_survive_without_any_count():
    scopes = [{}, {"denominator_units": "Eyes"}, {"units_analyzed": "Lesions"}]
    words = denominator_words(scopes, "g")
    assert words == (
        "Not stated; Measure denominator units selected: Eyes; "
        "Module units analyzed (other than participants): Lesions"
    )
    assert denominator_words([{}, {}, {}], "g") == "Not stated"


def test_wrapped_clinical_prose_uses_more_than_six_lines_and_empty_summary_spans_table(tmp_path):
    from openpyxl import load_workbook
    from schema3_records import record_of

    record = record_of(("NCT01030536",))
    outcome = record["studies"][0]["posted_outcomes"][0]
    outcome["description"] = "Registered paragraph\n" * 14
    record["studies"][0]["registered_outcomes"] = []
    path = tmp_path / "long-clinical-text.xlsx"
    readout.write_book(record, path)
    book = load_workbook(path)
    assert book[readout.contract.POSTED].row_dimensions[2].height >= 14 * readout.LINE_POINTS
    assert book[readout.contract.POSTED].row_dimensions[2].height <= readout.contract.MAX_ROW_HEIGHT_POINTS
    registered = book[readout.contract.REGISTERED]
    assert "A2:F2" in {str(r) for r in registered.merged_cells.ranges}
    assert registered["A2"].value == readout.contract.EMPTY_LISTING_WORDS[readout.contract.REGISTERED]
    assert readout.book_problems(record, path) == []
    book.close()


def test_keywords_and_registry_browse_leaves_have_independent_plain_fields():
    from copy import deepcopy

    from schema3_records import BODIES, record_of

    bodies = {"NCT01030536": deepcopy(BODIES["NCT01030536"])}
    source = bodies["NCT01030536"]
    source["protocolSection"]["conditionsModule"]["keywords"] = ["Sponsor wording", "Second keyword"]
    source.setdefault("derivedSection", {}).setdefault("conditionBrowseModule", {})["browseLeaves"] = [
        {
            "id": "browse-1",
            "name": "Registry name",
            "asFound": "Original registry wording",
            "relevance": "HIGH",
        }
    ]
    record = record_of(("NCT01030536",), bodies=bodies)
    study = record["studies"][0]
    assert study["keywords"] == ["Sponsor wording", "Second keyword"]
    assert study["condition_browse_leaves"] == [
        {
            "id": "browse-1",
            "name": "Registry name",
            "as_found": "Original registry wording",
            "relevance": "HIGH",
        }
    ]
    facts = {fact: value for _, _, fact, value, _ in readout.dossier_facts(study)}
    assert facts["Sponsor keywords"] == "Sponsor wording; Second keyword"
    term = facts["Registry condition browse term 1"]
    assert "Registry name" in term and "Original registry wording" in term
    assert "High" in term and "HIGH" not in term


def test_guide_never_turns_missing_structured_extraction_into_narrative_absence():
    from schema3_records import record_of

    record = record_of(("NCT01030536",))
    source = "The tissue assay is specified at baseline; the protocol records event grades for Cohort A."
    record["studies"][0]["detailed_description"] = source
    guide = {row[0][0]: row[1][0] for row in readout.guide_rows(record)}
    limits = guide["What the registry does not report"]
    assert "records do not hold" not in limits
    assert (
        "Literal descriptions, eligibility criteria and attached protocols may state these details" in limits
    )
    assert "missing extraction is no evidence of source absence" in limits
    assert "legacy reading" not in guide["What each status means"].lower()
    assert "inferred eligibility requirements" in guide["How to read this workbook"]
    assert any(value == source for _, _, _, value, _ in readout.dossier_facts(record["studies"][0]))


def test_safety_counts_link_to_their_own_group_definition_without_changing_counts(tmp_path):
    from openpyxl import load_workbook
    from schema3_records import record_of

    record = record_of(("NCT01030536",))
    path = tmp_path / "group-links.xlsx"
    readout.write_book(record, path)
    book = load_workbook(path)
    safety = book[readout.contract.SAFETY]
    for column, group in ((6, "G1"), (9, "G2")):
        held = safety.cell(2, column)
        assert isinstance(held.value, int)
        assert held.hyperlink and held.hyperlink.tooltip.startswith("Groups:")
        sheet, address = held.hyperlink.location.split("!")
        groups = book[sheet.strip("'")]
        target = groups[address].row
        assert groups.cell(target, 1).value == safety.cell(2, 1).value
        assert groups.cell(target, 3).value == "Adverse events"
        assert groups.cell(target, 5).value == group
        assert held.font.underline == "single"
        assert safety.cell(2, column + 1).hyperlink.location == held.hyperlink.location
        assert safety.cell(2, column + 2).hyperlink.location == held.hyperlink.location
    assert readout.book_problems(record, path) == []
    book.close()
