"""The acceptance test's comparison logic (acceptance/compare.py) and its selection (acceptance/select.py).

Positive: a workbook row, a CSV cell, a review cell, a provenance value or a file that holds exactly what the
registry's record holds agrees; a list held one item per line agrees; a field the record does not hold agrees
with a blank or an absence word; a row standing for no element agrees when the study has no element of that
kind; a Role whose every facet names a value of an enclosing element agrees; a computed at-risk count that
follows its declared rule agrees; a column declared stated from the field the reader pairs it with agrees; a
planted defect is found among the new results; the selection's draw is the same for the same seed whatever
order the registry listed the IDs in.
Negative: a changed text, a changed number, a value of another kind, a truncated text, a changed link and a
swapped pair are each a difference with both values named; a record value no row holds is omitted, one two
rows hold is duplicated; a row naming a location the record does not have differs; a CSV cell missing a
documented component differs; a byte-order mark, a changed line, a missing line and an extra line are each
named in the byte comparison; a cell stating it could not hold the value is not comparable; a Role facet the
record does not hold differs; an at-risk count or source off its rule differs; a column declared computed, or
from another field, or not declared, differs; a provenance value off the registry's differs; a defect no new
result names is not caught; a month is never drawn past the last month, and a record missing its modules
gives empty facts, not a crash.

The records are small excerpts, in the registry's own shape and with its own values, of NCT07780110,
NCT00069758 (whose identification lists an NCT ID alias) and NCT01410227's adverse events, as the API returned
them on 2026-11-01; no test touches the network or reads a run's files.
"""

import copy
import hashlib
import random

import pytest

from acceptance import compare
from acceptance import select as selection

NCT = "NCT07780110"
ALIAS = "NCT00069758"
TITLE = "protocolSection.identificationModule.briefTitle"
STUDY_URL = "https://clinicaltrials.gov/study/"
RICH_COLUMNS = [
    "NCT Number",
    "Study Title",
    "Study URL",
    "Acronym",
    "Study Status",
    "Brief Summary",
    "Study Results",
    "Conditions",
    "Interventions",
    "Primary Outcome Measures",
    "Secondary Outcome Measures",
    "Other Outcome Measures",
    "Sponsor",
    "Collaborators",
    "Sex",
    "Age",
    "Phases",
    "Enrollment",
    "Funder Type",
    "Study Type",
    "Study Design",
    "Other IDs",
    "Start Date",
    "Primary Completion Date",
    "Completion Date",
    "First Posted",
    "Results First Posted",
    "Last Update Posted",
    "Locations",
    "Study Documents",
]

# NCT07780110 as the API sent it, whole.
STUDY = {
    "protocolSection": {
        "identificationModule": {
            "nctId": NCT,
            "orgStudyIdInfo": {"id": "R5459-Vonsetamig"},
            "organization": {"fullName": "Regeneron Pharmaceuticals", "class": "INDUSTRY"},
            "briefTitle": "Compassionate Use of Vonsetamig",
        },
        "statusModule": {
            "statusVerifiedDate": "2026-08",
            "overallStatus": "AVAILABLE",
            "expandedAccessInfo": {"hasExpandedAccess": False},
            "studyFirstSubmitDate": "2026-08-18",
            "studyFirstPostDateStruct": {"date": "2026-08-21", "type": "ACTUAL"},
            "lastUpdatePostDateStruct": {"date": "2026-08-21", "type": "ACTUAL"},
        },
        "sponsorCollaboratorsModule": {
            "responsibleParty": {"type": "SPONSOR"},
            "leadSponsor": {"name": "Regeneron Pharmaceuticals", "class": "INDUSTRY"},
        },
        "descriptionModule": {"briefSummary": "Provide Compassionate Use of Vonsetamig"},
        "conditionsModule": {"conditions": ["Plasma Cell Mediated", "Antibody Mediated"]},
        "designModule": {"studyType": "EXPANDED_ACCESS", "expandedAccessTypes": {"individual": True}},
        "armsInterventionsModule": {
            "interventions": [{"type": "DRUG", "name": "Vonsetamig", "otherNames": ["REGN5459"]}]
        },
        "eligibilityModule": {
            "eligibilityCriteria": "Eligibility will be determined during the application review process.",
            "stdAges": ["CHILD", "ADULT", "OLDER_ADULT"],
        },
    },
    "derivedSection": {"miscInfoModule": {"versionHolder": "2026-10-30"}},
    "hasResults": False,
}

# An excerpt of NCT00069758: an NCT ID alias, a phase, an age limit, two sites.
ALIASED = {
    "protocolSection": {
        "identificationModule": {
            "nctId": ALIAS,
            "nctIdAliases": ["NCT00085033"],
            "orgStudyIdInfo": {"id": "SDX-105-01"},
            "briefTitle": "Safety and Activity of SDX-105 (Bendamustine) in Patients With Rituximab "
            "Refractory Non-Hodgkin's Lymphoma",
        },
        "statusModule": {"overallStatus": "COMPLETED", "startDateStruct": {"date": "2003-09"}},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Cephalon", "class": "INDUSTRY"}},
        "designModule": {
            "studyType": "INTERVENTIONAL",
            "phases": ["PHASE2"],
            "enrollmentInfo": {"count": 72},
        },
        "eligibilityModule": {"sex": "ALL", "minimumAge": "18 Years", "stdAges": ["ADULT", "OLDER_ADULT"]},
        "contactsLocationsModule": {
            "locations": [
                {
                    "facility": "University of Alabama at Birmingham",
                    "city": "Birmingham",
                    "state": "Alabama",
                    "zip": "35294-3300",
                    "country": "United States",
                },
                {
                    "facility": "San Diego Cancer Center",
                    "city": "Vista",
                    "state": "California",
                    "zip": "92083",
                    "country": "United States",
                },
            ]
        },
    },
    "hasResults": False,
}

# An excerpt of NCT01410227's adverse events, with a second group and an event that leaves numAtRisk blank.
EVENTS = {
    "resultsSection": {
        "adverseEventsModule": {
            "eventGroups": [
                {"id": "EG000", "title": "Safety Analysis Set", "seriousNumAtRisk": 37, "otherNumAtRisk": 37},
                {"id": "EG001", "title": "Arm B", "seriousNumAtRisk": 5, "otherNumAtRisk": 6},
            ],
            "seriousEvents": [
                {
                    "term": "Constipation",
                    "organSystem": "Gastrointestinal disorders",
                    "stats": [
                        {"groupId": "EG000", "numEvents": 1, "numAffected": 1, "numAtRisk": 37},
                        {"groupId": "EG001", "numAffected": 0},
                    ],
                }
            ],
            "otherEvents": [{"term": "Headache", "stats": [{"groupId": "EG001", "numAffected": 2}]}],
        }
    }
}
SERIOUS = ("resultsSection", "adverseEventsModule", "seriousEvents", 0, "stats", 0)
SERIOUS_BLANK = ("resultsSection", "adverseEventsModule", "seriousEvents", 0, "stats", 1)
OTHER_BLANK = ("resultsSection", "adverseEventsModule", "otherEvents", 0, "stats", 0)


def _rows(study: dict, nct: str = NCT) -> list[dict]:
    """A Record sheet holding every value of the study at its own location, as a faithful workbook would."""
    return [
        {"row": n, "nct": nct, "location": compare.format_location(tokens), "value": value, "title": None}
        for n, (tokens, value) in enumerate(compare.json_leaves(study), start=2)
    ]


def _results(findings: list[dict], comparison: str) -> list[str]:
    return [item["result"] for item in findings if item["comparison"] == comparison]


# --- locations and values ---------------------------------------------------------------------------------


def test_a_location_reads_back_as_the_path_it_names():
    tokens = compare.parse_location("protocolSection.identificationModule.nctIdAliases[0]")
    assert tokens == ("protocolSection", "identificationModule", "nctIdAliases", 0)
    assert compare.parse_location("a.b[2][3].c") == ("a", "b", 2, 3, "c")
    assert compare.format_location(tokens) == "protocolSection.identificationModule.nctIdAliases[0]"
    assert compare.format_location(("a", 0, 1, "b")) == "a[0][1].b"
    assert compare.format_location(()) == ""
    assert compare.field_pattern(tokens) == "protocolSection.identificationModule.nctIdAliases[]"
    assert compare.field_pattern(("a", 3, "b", 12, "c")) == "a[].b[].c"
    assert compare.resolve(STUDY, compare.parse_location(TITLE)) == (True, "Compassionate Use of Vonsetamig")
    assert compare.resolve([5, 6], (1,)) == (True, 6)
    assert compare.resolve(STUDY, ()) == (True, STUDY)


def test_a_text_that_is_not_a_location_or_a_path_the_record_lacks_is_named():
    assert compare.parse_location("not a location!") is None
    assert compare.parse_location("a..b") is None
    assert compare.parse_location("") is None
    assert compare.parse_location(None) is None
    assert compare.parse_location(-1) is None
    assert compare.resolve(STUDY, ("protocolSection", "nothingHere")) == (False, None)
    assert compare.resolve(STUDY, ("protocolSection", "conditionsModule", "conditions", 2)) == (False, None)
    assert compare.resolve(STUDY, ("hasResults", "x")) == (False, None)
    assert compare.resolve({"a": 1}, (0,)) == (False, None)


def test_every_leaf_is_listed_with_its_path_and_an_empty_container_is_a_leaf():
    assert compare.json_leaves({"a": {"b": 1, "c": [2, {"d": 3}]}, "e": [], "f": {}}) == [
        (("a", "b"), 1),
        (("a", "c", 0), 2),
        (("a", "c", 1, "d"), 3),
        (("e",), []),
        (("f",), {}),
    ]
    assert len(compare.json_leaves(STUDY)) == 30


def test_a_value_alone_is_one_leaf_at_the_empty_path():
    assert compare.json_leaves(7) == [((), 7)]
    assert compare.json_leaves("Phase 2") == [((), "Phase 2")]


def test_the_same_value_of_the_same_kind_agrees():
    assert compare.value_result("Phase 2", "Phase 2") == ("agree", "")
    assert compare.value_result(72, 72) == ("agree", "")
    assert compare.value_result(33.52066, 33.52066) == ("agree", "")
    assert compare.value_result(1.0, 1) == ("agree", "")
    assert compare.value_result(False, False) == ("agree", "")
    assert compare.value_result(None, None) == ("agree", "")


def test_a_changed_truncated_or_retyped_value_differs_and_says_how():
    assert compare.value_result("Safety Study", "Sefety Study") == ("differ", "different text")
    assert compare.value_result("Inclusion Criteria: adults", "Inclusion") == (
        "differ",
        "the cell holds the first 9 of 26 characters",
    )
    assert compare.value_result("abc", "abc ") == ("differ", "different text")
    assert compare.value_result(72, 73) == ("differ", "different value")
    assert compare.value_result(7, "7") == (
        "differ",
        "same text, different kind: number in the record, text in the cell",
    )
    assert compare.value_result(True, 1) == ("differ", "boolean in the record, number in the cell")
    assert compare.value_result(None, "x") == ("differ", "empty in the record, text in the cell")
    assert compare.value_result([1], [2]) == ("differ", "different value")


def test_a_cell_that_says_it_could_not_hold_the_value_is_not_comparable():
    said = "not written: over a cell's limit; see studies.json at x"
    assert compare.value_result("a" * 40000, said) == (
        "not_comparable",
        "the cell states it could not hold the value: " + said,
    )
    assert compare.value_result("see studies.json", "see studies.json") == ("agree", "")


def test_absence_agrees_only_with_a_blank_or_an_absence_word():
    assert compare.absence_result(None) == ("agree", "absent: blank")
    assert compare.absence_result("") == ("agree", "absent: blank")
    assert compare.absence_result("not reported") == ("agree", "absent: not reported")
    assert compare.absence_result("not applicable to this study type") == (
        "agree",
        "absent: not applicable to this study type",
    )
    assert compare.absence_result("none in the record") == (
        "differ",
        "the record holds no value here, the cell holds one",
    )
    assert compare.absence_result(0)[0] == "differ"


def test_a_field_title_is_the_registrys_or_not_comparable_where_it_gives_none():
    titles = compare.metadata_titles(
        [
            {
                "name": "protocolSection",
                "title": "Protocol Section",
                "children": [
                    {
                        "name": "identificationModule",
                        "children": [{"name": "briefTitle", "title": "Brief Title"}, {"name": "acronym"}],
                    }
                ],
            },
            {"name": "hasResults", "title": "Has Results"},
        ]
    )
    assert titles == {
        "protocolSection": "Protocol Section",
        "protocolSection.identificationModule.briefTitle": "Brief Title",
        "hasResults": "Has Results",
    }
    tokens = compare.parse_location(TITLE)
    assert compare.title_result(titles, tokens, "Brief Title") == ("agree", "")
    assert compare.title_result(titles, ("hasResults",), "Has Results") == ("agree", "")
    assert compare.title_result(titles, tokens, "Official Title") == ("differ", "different text")
    assert compare.title_result(titles, ("protocolSection", "identificationModule"), "x") == (
        "not_comparable",
        "the registry's metadata gives this field no title",
    )


# --- (a) record.xlsx --------------------------------------------------------------------------------------


def test_a_finding_keeps_every_part_of_a_result():
    assert compare.finding("a", NCT, "w", "f", "differ", "why", 1, 2) == {
        "comparison": "a",
        "nct": NCT,
        "where": "w",
        "field": "f",
        "result": "differ",
        "why": "why",
        "expected": 1,
        "found": 2,
    }
    assert compare.finding("e", "*", "w", "f", "agree", "")["expected"] is None


def test_a_faithful_record_sheet_agrees_value_by_value_and_leaf_by_leaf():
    findings = compare.compare_record_rows({NCT: STUDY}, _rows(STUDY), {})
    assert set(_results(findings, "a")) == {"agree"}
    assert set(_results(findings, "a-leaves")) == {"agree"}
    assert len(_results(findings, "a-leaves")) == len(compare.json_leaves(STUDY))
    assert set(_results(findings, "a-title")) == {"not_comparable"}
    assert _results(findings, "a-role") == []


def test_a_dropped_a_duplicated_and_a_misplaced_row_are_each_named():
    rows = _rows(STUDY)
    dropped = rows[3]
    rows = rows[:3] + rows[4:] + [dict(rows[5], row=999)]
    rows.append(
        {"row": 1000, "nct": NCT, "location": "protocolSection.nothingHere", "value": "x", "title": None}
    )
    rows.append({"row": 1001, "nct": NCT, "location": "protocolSection", "value": "x", "title": None})
    rows.append({"row": 1002, "nct": NCT, "location": "no location!", "value": "x", "title": None})
    rows.append({"row": 1003, "nct": ALIAS, "location": TITLE, "value": "x", "title": None})
    findings = compare.compare_record_rows({NCT: STUDY}, rows, {})
    issues = {
        (item["comparison"], item["where"], item["result"], item["why"])
        for item in findings
        if item["result"] != "agree"
    }
    assert ("a-leaves", dropped["location"], "omitted", "a value of the record no Record row holds") in issues
    assert ("a-leaves", rows[4]["location"], "duplicated", "2 Record rows hold this location") in issues
    assert (
        "a",
        "protocolSection.nothingHere",
        "differ",
        "the record holds nothing at this location",
    ) in issues
    assert ("a", "protocolSection", "differ", "the location holds a list or object, not a value") in issues
    assert ("a", "Record!row 1002", "differ", "the row's Location is not a location") in issues
    assert (
        "a",
        "Record!row 1003",
        "differ",
        "the row names a study the registry did not return for the selection",
    ) in issues


def test_each_row_and_each_leaf_has_its_exact_result():
    rows = [
        {"row": 2, "nct": "x", "location": "a", "value": 1, "title": "A", "role": None},
        {"row": 3, "nct": "x", "location": "b[0]", "value": 2, "title": "B", "role": "group=G"},
        {"row": 4, "nct": "x", "location": "b[0]", "value": 3, "title": None},
    ]
    no_title = "the registry's metadata gives this field no title"
    assert compare.compare_record_rows({"x": {"a": 1, "b": [2]}}, rows, {"a": "A"}) == [
        compare.finding("a", "x", "a", "a", "agree", "", 1, 1),
        compare.finding("a-title", "x", "a", "a", "agree", "", "A", "A"),
        compare.finding("a", "x", "b[0]", "b[]", "agree", "", 2, 2),
        compare.finding(
            "a-role",
            "x",
            "b[0]",
            "b[]",
            "differ",
            "no enclosing element of the record holds group=G",
            None,
            "group=G",
        ),
        compare.finding("a-title", "x", "b[0]", "b[]", "not_comparable", no_title, None, "B"),
        compare.finding("a", "x", "b[0]", "b[]", "differ", "different value", 2, 3),
        compare.finding("a-title", "x", "b[0]", "b[]", "not_comparable", no_title, None, None),
        compare.finding("a-leaves", "x", "a", "a", "agree", "", None, None),
        compare.finding(
            "a-leaves", "x", "b[0]", "b[]", "duplicated", "2 Record rows hold this location", 2, 2
        ),
    ]
    assert compare.compare_record_rows({}, [], {}) == []


def test_an_empty_record_with_no_rows_is_one_omitted_leaf():
    assert compare.compare_record_rows({"x": {}}, [], {"x": "x"}) == [
        compare.finding(
            "a-leaves", "x", "", "", "omitted", "a value of the record no Record row holds", {}, None
        )
    ]


def test_a_row_without_its_study_is_refused_by_the_missing_key():
    outcome = None
    try:
        compare.compare_record_rows({"x": {}}, [{}], {"x": "x"})
    except Exception as error:
        outcome = (type(error).__name__, error.args)
    assert outcome == ("KeyError", ("nct",))


def test_a_swapped_pair_between_studies_is_a_difference_in_each():
    studies = {NCT: STUDY, ALIAS: ALIASED}
    rows = _rows(STUDY) + _rows(ALIASED, ALIAS)
    first = next(r for r in rows if r["nct"] == NCT and r["location"] == TITLE)
    second = next(r for r in rows if r["nct"] == ALIAS and r["location"] == TITLE)
    first["value"], second["value"] = second["value"], first["value"]
    differ = [item for item in compare.compare_record_rows(studies, rows, {}) if item["result"] == "differ"]
    assert {(item["nct"], item["where"]) for item in differ} == {(NCT, TITLE), (ALIAS, TITLE)}
    assert all(item["expected"] != item["found"] for item in differ)


def test_a_role_whose_facets_hold_of_the_enclosing_elements_agrees():
    intervention = compare.parse_location("protocolSection.armsInterventionsModule.interventions[0].name")
    assert compare.role_result(STUDY, intervention, "intervention=Vonsetamig") == (
        "agree",
        "every facet holds of an element enclosing the row's location",
    )
    assert compare.role_result(EVENTS, (*SERIOUS, "numAffected"), "event_table=serious; group=EG000")[0] == (
        "agree"
    )
    group = ("resultsSection", "adverseEventsModule", "eventGroups", 1, "title")
    assert compare.role_result(EVENTS, group, "group=EG001")[0] == "agree"
    section = ("protocolSection", "outcomesModule", "secondaryOutcomes", 0, "measure")
    assert compare.role_result({}, section, "outcome_type=SECONDARY")[0] == "agree"
    posted = {"resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{"type": "PRIMARY"}]}}}
    measure = ("resultsSection", "outcomeMeasuresModule", "outcomeMeasures", 0, "title")
    assert compare.role_result(posted, measure, "outcome_type=PRIMARY")[0] == "agree"
    arms = {"armGroups": [{"label": "Arm A"}], "references": [{"type": "RESULT"}]}
    assert compare.role_result(arms, ("armGroups", 0, "label"), "arm=Arm A")[0] == "agree"
    assert compare.role_result(arms, ("references", 0, "pmid"), "reference_type=RESULT")[0] == "agree"


def test_a_role_naming_what_the_record_does_not_hold_differs_and_an_unknown_facet_is_named():
    intervention = compare.parse_location("protocolSection.armsInterventionsModule.interventions[0].name")
    assert compare.role_result(STUDY, intervention, "intervention=Placebo; arm=Vonsetamig") == (
        "differ",
        "no enclosing element of the record holds intervention=Placebo; arm=Vonsetamig",
    )
    assert compare.role_result(EVENTS, (*SERIOUS, "numAffected"), "event_table=other")[0] == "differ"
    assert compare.role_result(EVENTS, (*SERIOUS, "numAffected"), "group=EG001")[0] == "differ"
    section = ("protocolSection", "outcomesModule", "primaryOutcomes", 0, "measure")
    assert compare.role_result({}, section, "outcome_type=SECONDARY")[0] == "differ"
    assert compare.role_result(STUDY, intervention, "dose=10 mg") == (
        "not_comparable",
        "a facet this reader has no rule for: dose=10 mg",
    )
    assert compare.role_result(STUDY, intervention, None) == ("not_comparable", "the row states no role")
    assert compare.role_result(STUDY, intervention, "") == ("not_comparable", "the row states no role")
    rows = _rows(STUDY)
    for row in rows:
        row["role"] = "intervention=Placebo" if row["location"].endswith("interventions[0].name") else None
    roles = [i for i in compare.compare_record_rows({NCT: STUDY}, rows, {}) if i["comparison"] == "a-role"]
    assert [(i["result"], i["found"]) for i in roles] == [("differ", "intervention=Placebo")]


# --- (b) the API's CSV ------------------------------------------------------------------------------------


def test_a_csv_column_is_built_from_the_record_by_the_documented_fields():
    assert compare.csv_expected("NCT Number", STUDY) == ("exact", NCT)
    assert compare.csv_expected("Acronym", STUDY) == ("exact", "")
    assert compare.csv_expected("Study URL", STUDY) == ("exact", STUDY_URL + NCT)
    assert compare.csv_expected("Study Results", STUDY) == ("exact", "NO")
    assert compare.csv_expected("Study Results", {"hasResults": True}) == ("exact", "YES")
    assert compare.csv_expected("Conditions", STUDY) == ("exact", "Plasma Cell Mediated|Antibody Mediated")
    assert compare.csv_expected("Phases", ALIASED) == ("exact", "PHASE2")
    assert compare.csv_expected("Interventions", STUDY) == ("exact", "DRUG: Vonsetamig")
    assert compare.csv_expected("Enrollment", ALIASED) == ("exact", "72")
    assert compare.csv_expected("Age", ALIASED) == ("components", ["18 Years", "ADULT", "OLDER_ADULT"])
    assert compare.csv_expected("Other IDs", ALIASED) == ("components", ["SDX-105-01"])
    assert compare.csv_expected("Locations", ALIASED)[1][:5] == [
        "University of Alabama at Birmingham",
        "Birmingham",
        "Alabama",
        "35294-3300",
        "United States",
    ]
    assert compare.csv_cell_result(("exact", "COMPLETED"), "COMPLETED") == ("agree", "")
    assert compare.csv_cell_result(("components", ["18 Years", "ADULT"]), "18 Years, ADULT") == (
        "agree",
        "every documented component appears in the cell",
    )


RICH = {
    "protocolSection": {
        "identificationModule": {
            "nctId": "NCT00773474",
            "briefTitle": "T",
            "acronym": "AC",
            "orgStudyIdInfo": {"id": "O-1"},
            "secondaryIdInfos": [{"id": "S-1"}, {"type": "OTHER"}],
        },
        "statusModule": {
            "overallStatus": "TERMINATED",
            "startDateStruct": {"date": "2008-10"},
            "primaryCompletionDateStruct": {"date": "2011-01"},
            "completionDateStruct": {"date": "2011-02"},
            "studyFirstPostDateStruct": {"date": "2008-10-29"},
            "resultsFirstPostDateStruct": {"date": "2012-03-01"},
            "lastUpdatePostDateStruct": {"date": "2013-04-02"},
        },
        "sponsorCollaboratorsModule": {
            "leadSponsor": {"name": "L", "class": "OTHER"},
            "collaborators": [{"name": "Schering-Plough"}, {"name": "H"}],
        },
        "descriptionModule": {"briefSummary": "B"},
        "conditionsModule": {"conditions": ["C1", "C2"]},
        "designModule": {
            "studyType": "INTERVENTIONAL",
            "phases": ["PHASE2", "PHASE3"],
            "enrollmentInfo": {"count": 7},
            "designInfo": {
                "allocation": "RANDOMIZED",
                "interventionModel": "PARALLEL",
                "primaryPurpose": "TREATMENT",
                "maskingInfo": {"masking": "DOUBLE", "whoMasked": ["PARTICIPANT", "INVESTIGATOR"]},
            },
        },
        "armsInterventionsModule": {
            "interventions": [{"type": "DRUG", "name": "D"}, {"type": "OTHER", "name": "P"}]
        },
        "outcomesModule": {
            "primaryOutcomes": [{"measure": "M1", "timeFrame": "F1"}],
            "secondaryOutcomes": [{"measure": "M2", "description": "D2", "timeFrame": "F2"}],
            "otherOutcomes": [{"measure": "M3"}],
        },
        "eligibilityModule": {
            "sex": "ALL",
            "minimumAge": "18 Years",
            "maximumAge": "75 Years",
            "stdAges": ["ADULT", "OLDER_ADULT"],
        },
        "contactsLocationsModule": {
            "locations": [{"facility": "F", "city": "Vista", "zip": "92083", "country": "United States"}]
        },
    },
    "documentSection": {
        "largeDocumentModule": {"largeDocs": [{"label": "Protocol", "filename": "Prot_000.pdf"}]}
    },
    "hasResults": True,
}


def test_every_documented_csv_column_of_a_full_record_is_built_from_its_fields():
    assert {column: compare.csv_expected(column, RICH) for column in RICH_COLUMNS} == {
        "NCT Number": ("exact", "NCT00773474"),
        "Study Title": ("exact", "T"),
        "Study URL": ("exact", "https://clinicaltrials.gov/study/NCT00773474"),
        "Acronym": ("exact", "AC"),
        "Study Status": ("exact", "TERMINATED"),
        "Brief Summary": ("exact", "B"),
        "Study Results": ("exact", "YES"),
        "Conditions": ("exact", "C1|C2"),
        "Interventions": ("exact", "DRUG: D|OTHER: P"),
        "Primary Outcome Measures": ("components", ["M1", "F1"]),
        "Secondary Outcome Measures": ("components", ["M2", "D2", "F2"]),
        "Other Outcome Measures": ("components", ["M3"]),
        "Sponsor": ("exact", "L"),
        "Collaborators": ("exact", "Schering-Plough|H"),
        "Sex": ("exact", "ALL"),
        "Age": ("components", ["18 Years", "75 Years", "ADULT", "OLDER_ADULT"]),
        "Phases": ("exact", "PHASE2|PHASE3"),
        "Enrollment": ("exact", "7"),
        "Funder Type": ("exact", "OTHER"),
        "Study Type": ("exact", "INTERVENTIONAL"),
        "Study Design": (
            "components",
            ["RANDOMIZED", "PARALLEL", "TREATMENT", "DOUBLE", "PARTICIPANT", "INVESTIGATOR"],
        ),
        "Other IDs": ("components", ["O-1", "S-1"]),
        "Start Date": ("exact", "2008-10"),
        "Primary Completion Date": ("exact", "2011-01"),
        "Completion Date": ("exact", "2011-02"),
        "First Posted": ("exact", "2008-10-29"),
        "Results First Posted": ("exact", "2012-03-01"),
        "Last Update Posted": ("exact", "2013-04-02"),
        "Locations": ("components", ["F", "Vista", "92083", "United States"]),
        "Study Documents": ("components", ["Protocol", "Prot_000.pdf"]),
    }


def test_a_record_without_sites_gives_no_location_components():
    assert compare.csv_expected("Locations", {}) == ("components", [])


def test_an_observational_design_and_an_empty_record_give_their_own_components():
    observational = {
        "protocolSection": {
            "designModule": {"designInfo": {"observationalModel": "COHORT", "timePerspective": "PROSPECTIVE"}}
        }
    }
    assert compare.csv_expected("Study Design", observational) == ("components", ["COHORT", "PROSPECTIVE"])
    assert compare.csv_expected("Study Design", {}) == ("components", [])
    assert compare.csv_expected("Study URL", {}) == ("exact", "https://clinicaltrials.gov/study/None")
    assert compare.csv_expected("Locations", {}) == ("components", [])
    assert compare.csv_expected("Other IDs", {}) == ("components", [])
    assert compare.csv_expected("Conditions", {}) == ("exact", "")


def test_the_joined_columns_take_each_documented_piece():
    record = {
        "protocolSection": {
            "identificationModule": {"secondaryIdInfos": [{"id": "2003-1"}, {"type": "OTHER"}]},
            "sponsorCollaboratorsModule": {"collaborators": [{"name": "A"}, {"name": "B"}]},
            "outcomesModule": {"primaryOutcomes": [{"measure": "OS", "timeFrame": "2 years"}]},
            "designModule": {
                "designInfo": {
                    "allocation": "RANDOMIZED",
                    "maskingInfo": {"masking": "DOUBLE", "whoMasked": ["X"]},
                }
            },
        },
        "documentSection": {
            "largeDocumentModule": {"largeDocs": [{"label": "Protocol", "filename": "P.pdf"}]}
        },
    }
    assert compare.csv_expected("Collaborators", record) == ("exact", "A|B")
    assert compare.csv_expected("Other IDs", record) == ("components", ["2003-1"])
    assert compare.csv_expected("Primary Outcome Measures", record) == ("components", ["OS", "2 years"])
    assert compare.csv_expected("Secondary Outcome Measures", record) == ("components", [])
    assert compare.csv_expected("Study Design", record) == ("components", ["RANDOMIZED", "DOUBLE", "X"])
    assert compare.csv_expected("Study Documents", record) == ("components", ["Protocol", "P.pdf"])
    assert compare.csv_expected("Age", {}) == ("components", [])


def test_a_csv_cell_missing_a_documented_component_or_changed_differs():
    assert compare.csv_cell_result(("components", ["18 Years", "ADULT"]), "ADULT") == (
        "differ",
        "missing from the cell: 18 Years",
    )
    assert compare.csv_cell_result(("exact", "COMPLETED"), "COMPLETEX") == ("differ", "different text")
    assert compare.csv_expected("Not A Column", STUDY) == ("unknown", "Not A Column")
    assert compare.csv_cell_result(("unknown", "Not A Column"), "x") == (
        "not_comparable",
        "a column the registry's documentation does not list",
    )


def test_the_csv_against_the_record_and_the_workbook_agrees_or_names_the_column():
    header = ["NCT Number", "Study Title"]
    title = STUDY["protocolSection"]["identificationModule"]["briefTitle"]
    cells = {NCT: {TITLE: title, "protocolSection.identificationModule.nctId": NCT}}
    good = compare.compare_csv(
        {NCT: STUDY}, [{"NCT Number": NCT, "Study Title": title}], header, header, cells
    )
    assert [(i["comparison"], i["where"], i["result"]) for i in good] == [
        ("b-json", "header", "agree"),
        ("b-json", "NCT Number", "agree"),
        ("b-workbook", "NCT Number", "agree"),
        ("b-json", "Study Title", "agree"),
        ("b-workbook", "Study Title", "agree"),
    ]
    bad = compare.compare_csv(
        {NCT: STUDY},
        [{"NCT Number": NCT, "Study Title": title + "!"}, {"NCT Number": ALIAS, "Study Title": "x"}],
        header,
        ["NCT Number", "Brief Title"],
        cells,
    )
    assert {(i["comparison"], i["nct"], i["where"], i["result"]) for i in bad if i["result"] != "agree"} == {
        ("b-json", "*", "header", "differ"),
        ("b-json", NCT, "Study Title", "differ"),
        ("b-workbook", NCT, "Study Title", "differ"),
        ("b-json", ALIAS, "row", "differ"),
    }
    missing = compare.compare_csv({NCT: STUDY}, [], header, header, cells)
    assert [item["result"] for item in missing] == ["agree", "omitted"]
    twice = compare.compare_csv({NCT: STUDY}, [{"NCT Number": NCT}] * 2, header, header, cells)
    assert [(i["result"], i["found"]) for i in twice] == [("agree", None), ("duplicated", 2)]


def test_an_empty_workbook_cell_reads_as_the_csv_writes_nothing():
    assert compare.workbook_text({"x": None}, "x") == ""
    assert compare.workbook_text({"x[0]": None, "x[1]": 0}, "x[]") == "|0"


def test_each_csv_cell_and_row_has_its_exact_result():
    study = {
        "protocolSection": {
            "identificationModule": {"nctId": "N"},
            "eligibilityModule": {"minimumAge": "18 Years"},
        }
    }
    header = ["NCT Number", "Age"]
    cells = {"N": {"protocolSection.identificationModule.nctId": "N"}}
    nct_path = "protocolSection.identificationModule.nctId"
    assert compare.compare_csv(
        {"N": study}, [{"NCT Number": "N", "Age": "ADULT"}], header, header, cells
    ) == [
        compare.finding("b-json", "*", "header", "header", "agree", ""),
        compare.finding("b-json", "N", "NCT Number", "NCT Number", "agree", "", "N", "N"),
        compare.finding("b-workbook", "N", "NCT Number", nct_path, "agree", "", "N", "N"),
        compare.finding(
            "b-json", "N", "Age", "Age", "differ", "missing from the cell: 18 Years", ["18 Years"], "ADULT"
        ),
    ]
    unnamed = compare.compare_csv({"x": {}}, [{}], ["x"], ["x"], {"x": {"x": None}})
    assert unnamed == [
        compare.finding("b-json", "*", "header", "header", "agree", ""),
        compare.finding("b-json", "x", "row", "row", "omitted", "0 CSV rows for the study", 1, 0),
        compare.finding("b-json", "", "row", "row", "differ", "a CSV row for a study not returned", None, ""),
    ]
    assert compare.compare_csv({"x": {}}, [], [], ["x"], {"x": {"x": None}}) == [
        compare.finding(
            "b-json",
            "*",
            "header",
            "header",
            "differ",
            "the CSV's columns are not the documented columns, in order",
            ["x"],
            [],
        ),
        compare.finding("b-json", "x", "row", "row", "omitted", "0 CSV rows for the study", 1, 0),
    ]


def test_a_list_field_in_the_workbook_reads_as_the_csv_writes_it():
    cells = {"a.list[0]": "x", "a.list[1]": "y", "a.items[0].name": "n", "a.count": 3, "a.gap[1]": "z"}
    assert compare.workbook_text(cells, "a.list[]") == "x|y"
    assert compare.workbook_text(cells, "a.items[].name") == "n"
    assert compare.workbook_text(cells, "a.count") == "3"
    assert compare.workbook_text(cells, "a.missing") == ""
    assert compare.workbook_text(cells, "a.gap[]") == ""
    assert compare.workbook_text({"a[0].b[0]": 1}, "a[].b[0]") == "1"


# --- (c) review.xlsx --------------------------------------------------------------------------------------


def _review_row(row: int, cells: dict, link: str | None = None, nct: str = NCT) -> dict:
    return {
        "row": row,
        "cells": {"NCT Number": nct, **cells},
        "links": {"NCT Number": link or STUDY_URL + nct},
    }


def test_review_columns_paths_reach_the_rows_element_its_parent_or_an_enclosing_one():
    assert compare.column_path("@.numAffected", SERIOUS) == (
        "path",
        "resultsSection.adverseEventsModule.seriousEvents[0].stats[0].numAffected",
    )
    assert compare.column_path("@^.term", SERIOUS) == (
        "path",
        "resultsSection.adverseEventsModule.seriousEvents[0].term",
    )
    assert compare.column_path("@seriousEvents.term", SERIOUS) == (
        "path",
        "resultsSection.adverseEventsModule.seriousEvents[0].term",
    )
    assert compare.column_path("@seriousEvents", SERIOUS) == (
        "path",
        "resultsSection.adverseEventsModule.seriousEvents[0]",
    )
    assert compare.column_path("a.b", None) == ("path", "a.b")
    assert compare.column_path("@classes.title", SERIOUS) == ("outside", None)
    assert compare.column_path("@.x", None) == ("outside", None)
    assert compare.column_path("@^.x", ("a", 0)) == ("outside", None)


def test_a_pattern_expands_to_each_path_it_names_and_a_sheets_rows_to_their_elements():
    assert compare.expand({"a": [{"b": [1, 2]}, {"b": [3]}]}, "a[*].b[*]") == [
        ("a", 0, "b", 0),
        ("a", 0, "b", 1),
        ("a", 1, "b", 0),
    ]
    assert compare.expand({"a": [{"b": 1}]}, "a[0].b") == [("a", 0, "b")]
    assert compare.expand({"a": {"b": 1}}, "a[*]") == []
    assert compare.expand({"a": 1}, "a.c") == []
    assert compare.expand({"a": 1}, "a.b!") == []
    assert compare.row_elements({"m": [{"c": [5]}, {}]}, [("m[*]", ".c[*]")]) == [("m", 0, "c", 0), ("m", 1)]
    assert compare.row_elements({"m": [7], "n": [8]}, [("m[*]", ""), ("n[*]", "")]) == [("m", 0), ("n", 0)]
    assert compare.row_elements({}, [("m[*]", "")]) == []


def test_a_column_projects_one_value_or_the_list_a_wildcard_names():
    assert compare.project(STUDY, TITLE) == (True, "Compassionate Use of Vonsetamig")
    assert compare.project(STUDY, "protocolSection.conditionsModule.conditions[*]") == (
        True,
        ["Plasma Cell Mediated", "Antibody Mediated"],
    )
    assert compare.project(STUDY, "protocolSection.designModule.phases[*]") == (False, None)
    assert compare.project(STUDY, "not a path!") == (False, None)


def test_a_review_cell_agrees_with_its_field_a_list_one_item_per_line_and_absence_as_absence():
    assert compare.review_cell_result(True, ["ADULT", "OLDER_ADULT"], "ADULT\nOLDER_ADULT") == ("agree", "")
    assert compare.review_cell_result(True, "COMPLETED", "COMPLETED") == ("agree", "")
    assert compare.review_cell_result(False, None, "not reported") == ("agree", "absent: not reported")
    assert compare.review_cell_result(True, ["ADULT"], "ADULT, OLDER_ADULT") == ("differ", "different text")
    assert compare.review_cell_result(False, None, "COMPLETED")[0] == "differ"
    assert compare.review_cell_result(True, [{"a": 1}], "x") == (
        "not_comparable",
        "the field holds objects, not values",
    )
    assert compare.review_cell_result(True, {"a": 1}, "x") == (
        "not_comparable",
        "the field holds an object, not a value",
    )


def test_a_faithful_studies_row_agrees_lists_one_item_per_line_and_absence_as_absence():
    cells = {}
    for column, path in compare.STUDIES_COLUMNS.items():
        found, value = compare.project(STUDY, path) if isinstance(path, str) else (False, None)
        cells[column] = ("\n".join(value) if isinstance(value, list) else value) if found else "not reported"
    every = compare.compare_review({NCT: STUDY}, {"Studies": [_review_row(2, cells)]})
    findings = [item for item in every if item["field"].startswith("Studies")]
    assert {item["result"] for item in findings} == {"agree"}
    assert ("Eligibility", "omitted") in {(item["field"], item["result"]) for item in every}
    assert {item["comparison"] for item in findings} == {"c", "c-form", "c-links", "c-rows"}
    assert cells["Overall Status"] == "AVAILABLE"


def test_a_changed_review_cell_a_wrong_link_and_a_value_where_the_record_has_none_differ():
    cells = {"Overall Status": "COMPLETED", "Why Stopped": "it stopped"}
    findings = compare.compare_review(
        {NCT: STUDY}, {"Studies": [_review_row(2, cells, STUDY_URL + "NCT00000001")]}
    )
    issues = {(item["field"], item["result"]) for item in findings if item["result"] != "agree"}
    assert ("Studies › Overall Status", "differ") in issues
    assert ("Studies › Why Stopped", "differ") in issues
    assert ("Studies › NCT Number link", "differ") in issues
    assert ("Studies › Acronym", "not_comparable") in issues
    stray = compare.compare_review({NCT: STUDY}, {"Studies": [_review_row(2, {}, nct=ALIAS)]})
    assert ("c-rows", "a row for a study not returned") in {(i["comparison"], i["why"]) for i in stray}


def test_review_rows_omitted_duplicated_and_standing_for_nothing_are_each_judged():
    location = "protocolSection.contactsLocationsModule.locations[0]"
    site = {"Location": location}
    rows = [_review_row(2, site, nct=ALIAS), _review_row(3, site, nct=ALIAS)]
    findings = compare.compare_review({ALIAS: ALIASED}, {"Sites": rows})
    rows_results = {(item["where"], item["result"]) for item in findings if item["field"] == "Sites"}
    assert rows_results == {
        (location, "duplicated"),
        ("protocolSection.contactsLocationsModule.locations[1]", "omitted"),
    }
    wrong = compare.compare_review(
        {ALIAS: ALIASED}, {"Sites": [_review_row(2, {"Location": TITLE}, nct=ALIAS)]}
    )
    assert ("Sites!row 2", "differ") in {(i["where"], i["result"]) for i in wrong if i["field"] == "Sites"}
    placeholder = {"Results": "no results posted", "Location": None, "Value": None}
    empty = compare.compare_review({NCT: STUDY}, {"Outcome Results": [_review_row(2, placeholder)]})
    assert [(i["result"], i["found"]) for i in empty if i["field"] == "Outcome Results"] == [("agree", None)]
    holding = compare.compare_review(
        {NCT: STUDY}, {"Outcome Results": [_review_row(2, {**placeholder, "Value": "12"})]}
    )
    assert [item["result"] for item in holding if item["field"] == "Outcome Results"] == ["differ"]


def test_a_placeholder_row_agrees_only_when_its_declared_columns_say_absence():
    columns = {"Value": "@.value", "Group ID": "@.groupId"}
    cells = {"NCT Number": NCT, "Results": "no results posted", "Value": None, "Location": None}
    agree = compare.placeholder_result("Outcome Results", NCT, "w", cells, columns)
    assert agree["result"] == "agree"
    assert agree["why"] == (
        "absent: the record holds no element of this kind; the row says so (Results: no results posted)"
    )
    differ = compare.placeholder_result("Outcome Results", NCT, "w", {**cells, "Group ID": "OG000"}, columns)
    assert (differ["result"], differ["found"]) == ("differ", {"Group ID": "OG000"})


def test_the_eligibility_split_parts_must_join_back_into_the_registrys_text():
    text = "Inclusion Criteria:\n\n* adults\n\nExclusion Criteria:\n\n* none"
    study = {"protocolSection": {"eligibilityModule": {"eligibilityCriteria": text}}}
    row = {
        "row": 2,
        "cells": {
            "Split": "split",
            "Before the Inclusion Heading": None,
            "Inclusion Criteria": text[:30],
            "Exclusion Criteria": text[30:],
        },
        "links": {},
    }
    assert compare.special_checks("Eligibility", NCT, study, row, "w")[0]["result"] == "agree"
    row["cells"]["Exclusion Criteria"] = text[30:-2]
    assert compare.special_checks("Eligibility", NCT, study, row, "w")[0]["result"] == "differ"
    whole = {"row": 2, "cells": {"Split": "not_split_missing", "Whole Text": text}, "links": {}}
    assert compare.special_checks("Eligibility", NCT, study, whole, "w")[0]["result"] == "agree"
    whole["cells"]["Whole Text"] = text[:10]
    assert compare.special_checks("Eligibility", NCT, study, whole, "w")[0]["result"] == "differ"
    assert compare.special_checks("Arms", NCT, study, whole, "w") == []


def test_a_publication_and_a_document_link_must_name_their_pmid_and_the_studys_file():
    row = {
        "row": 2,
        "cells": {"PMID": "32021616"},
        "links": {"PMID": "https://pubmed.ncbi.nlm.nih.gov/32021616/"},
    }
    assert compare.special_checks("Publications", NCT, STUDY, row, "w")[0]["result"] == "agree"
    row["links"]["PMID"] = "https://pubmed.ncbi.nlm.nih.gov/24142084/"
    assert compare.special_checks("Publications", NCT, STUDY, row, "w")[0]["result"] == "differ"
    none = {"row": 2, "cells": {"PMID": "not reported"}, "links": {}}
    assert compare.special_checks("Publications", NCT, STUDY, none, "w") == []
    copy_url = f"https://cdn.clinicaltrials.gov/large-docs/10/{NCT}/Prot_SAP_000.pdf"
    document = {"row": 2, "cells": {"File": "Prot_SAP_000.pdf"}, "links": {"File": copy_url}}
    assert compare.special_checks("Documents", NCT, STUDY, document, "w")[0]["result"] == "agree"
    document["links"]["File"] = copy_url.replace(NCT, ALIAS)
    assert compare.special_checks("Documents", NCT, STUDY, document, "w")[0]["result"] == "differ"


def test_a_stated_column_of_the_rows_place_or_a_declared_form_holds_it():
    outcome = ("protocolSection", "outcomesModule", "secondaryOutcomes", 2)
    assert compare.structure_value("outcome section", {}, outcome) == (True, "SECONDARY")
    assert compare.structure_value("position", {}, outcome) == (True, 3)
    assert compare.structure_value("event table", EVENTS, OTHER_BLANK) == (True, "other")
    flow = ("resultsSection", "participantFlowModule", "periods", 0, "dropWithdraws", 1, "reasons", 0)
    assert compare.structure_value("flow kind", {}, flow) == (True, "reason not completed")
    milestone = ("resultsSection", "participantFlowModule", "periods", 0, "milestones", 1, "achievements", 0)
    assert compare.structure_value("flow kind", {}, milestone) == (True, "milestone")
    record = {
        "protocolSection": {
            "referencesModule": {"references": [{"retractions": [{"pmid": "1", "source": "PubMed"}]}]},
            "sponsorCollaboratorsModule": {
                "collaborators": [
                    {"name": "Schering-Plough", "class": "INDUSTRY"},
                    {"name": "H", "class": "OTHER"},
                ]
            },
        }
    }
    reference = ("protocolSection", "referencesModule", "references", 0)
    assert compare.structure_value("retractions", record, reference) == (True, "1 (PubMed)")
    assert compare.structure_value("collaborators", record, None) == (
        True,
        "Schering-Plough (INDUSTRY)\nH (OTHER)",
    )


def test_a_form_the_record_does_not_hold_is_absent_and_an_unknown_form_has_no_rule():
    assert compare.structure_value("collaborators", STUDY, None) == (False, None)
    assert compare.structure_value("retractions", STUDY, ("protocolSection",)) == (False, None)
    assert compare.structure_value("retractions", STUDY, None) == (False, None)
    assert compare.structure_value("outcome section", {}, ("protocolSection", "x", 0)) == (False, None)
    assert compare.structure_value("event table", {}, ("a", 0)) == (False, None)
    assert compare.structure_value("position", {}, ("protocolSection",)) == (False, None)
    assert compare.structure_value("position", {}, None) == (False, None)
    assert compare.structure_value("dose", {}, ("a", 0)) is None
    assert compare.column_value({"form": "dose"}, {}, ("a", 0)) == ("skip", "no rule for the form 'dose'")
    retracted = compare.compare_review(
        {ALIAS: ALIASED}, {"Studies": [_review_row(2, {"Collaborators": "none in the record"}, nct=ALIAS)]}
    )
    assert [(i["comparison"], i["result"]) for i in retracted if i["field"] == "Studies › Collaborators"] == [
        ("c-form", "differ")
    ]


REFERENCED = {
    "protocolSection": {
        "referencesModule": {"references": [{"retractions": [{"pmid": "1", "source": "PubMed"}]}]},
        "sponsorCollaboratorsModule": {
            "collaborators": [
                {"name": "Schering-Plough", "class": "INDUSTRY"},
                {"name": "H", "class": "OTHER"},
            ]
        },
    }
}
FLOW = ("resultsSection", "participantFlowModule", "periods", 0)


@pytest.mark.parametrize(
    ("form", "record", "row", "held"),
    [
        (
            "outcome section",
            {},
            ("protocolSection", "outcomesModule", "secondaryOutcomes", 2),
            (True, "SECONDARY"),
        ),
        ("outcome section", {}, ("protocolSection", "outcomesModule", "otherOutcomes", 0), (True, "OTHER")),
        ("outcome section", {}, ("protocolSection", "x", 0), (False, None)),
        ("position", {}, ("protocolSection", "outcomesModule", "secondaryOutcomes", 2), (True, 3)),
        ("position", {}, ("a", 0), (True, 1)),
        ("position", {}, ("protocolSection",), (False, None)),
        ("position", {}, None, (False, None)),
        ("event table", EVENTS, OTHER_BLANK, (True, "other")),
        ("event table", EVENTS, SERIOUS, (True, "serious")),
        ("event table", {}, ("a", 0), (False, None)),
        ("flow kind", {}, (*FLOW, "dropWithdraws", 1, "reasons", 0), (True, "reason not completed")),
        ("flow kind", {}, (*FLOW, "milestones", 1, "achievements", 0), (True, "milestone")),
        ("flow kind", {}, ("a", 0), (False, None)),
        (
            "retractions",
            REFERENCED,
            ("protocolSection", "referencesModule", "references", 0),
            (True, "1 (PubMed)"),
        ),
        ("retractions", STUDY, ("protocolSection",), (False, None)),
        ("retractions", STUDY, None, (False, None)),
        ("retractions", {"r": [{"retractions": ["x", {"pmid": "2"}]}]}, ("r", 0), (True, "2 (None)")),
        ("collaborators", REFERENCED, None, (True, "Schering-Plough (INDUSTRY)\nH (OTHER)")),
        ("collaborators", STUDY, None, (False, None)),
        ("dose", {}, ("a", 0), None),
    ],
)
def test_each_form_holds_the_rows_place_or_the_declared_text_of_its_field(form, record, row, held):
    assert compare.structure_value(form, record, row) == held


PLACEHOLDER = {"NCT Number": NCT, "Results": "no results posted", "Value": None, "Location": None}
PLACEHOLDER_COLUMNS = {"Value": "@.value", "Group ID": "@.groupId"}
ABSENT_ROW = "absent: the record holds no element of this kind; the row says so "


@pytest.mark.parametrize(
    ("name", "cells", "columns", "expected"),
    [
        (
            "Outcome Results",
            PLACEHOLDER,
            PLACEHOLDER_COLUMNS,
            compare.finding(
                "c-rows", NCT, "w", "Outcome Results", "agree", ABSENT_ROW + "(Results: no results posted)"
            ),
        ),
        (
            "Outcome Results",
            {**PLACEHOLDER, "Group ID": "OG000"},
            PLACEHOLDER_COLUMNS,
            compare.finding(
                "c-rows",
                NCT,
                "w",
                "Outcome Results",
                "differ",
                "a row standing for no element holds values in Group ID",
                None,
                {"Group ID": "OG000"},
            ),
        ),
        (
            "S",
            {"NCT Number": NCT, "Warrant": "x", "Location": "y", "Other": "z", "Gone": None},
            {},
            compare.finding("c-rows", NCT, "w", "S", "agree", ABSENT_ROW + "(Other: z)", None, "y"),
        ),
        ("S", {}, {}, compare.finding("c-rows", NCT, "w", "S", "agree", ABSENT_ROW + "()")),
    ],
)
def test_a_placeholder_row_has_its_exact_result(name, cells, columns, expected):
    assert compare.placeholder_result(name, NCT, "w", cells, columns) == expected


CRITERIA = "Inclusion Criteria:\n\n* adults\n\nExclusion Criteria:\n\n* none"
CRITERIA_STUDY = {"protocolSection": {"eligibilityModule": {"eligibilityCriteria": CRITERIA}}}
JOINED = "Eligibility › split parts, joined"
SPLIT = {"Split": "split", "Before the Inclusion Heading": None, "Inclusion Criteria": CRITERIA[:30]}
DOC_LINK = "https://cdn.clinicaltrials.gov/large-docs/10/N/P.pdf"


@pytest.mark.parametrize(
    ("name", "study", "cells", "links", "expected"),
    [
        (
            "Eligibility",
            CRITERIA_STUDY,
            {**SPLIT, "Exclusion Criteria": CRITERIA[30:]},
            {},
            [
                compare.finding(
                    "c",
                    "N",
                    "w",
                    JOINED,
                    "agree",
                    "the three parts joined are the registry's text",
                    CRITERIA,
                    CRITERIA,
                )
            ],
        ),
        (
            "Eligibility",
            CRITERIA_STUDY,
            {**SPLIT, "Exclusion Criteria": CRITERIA[30:-2]},
            {},
            [
                compare.finding(
                    "c",
                    "N",
                    "w",
                    JOINED,
                    "differ",
                    "the cell holds the first 56 of 58 characters",
                    CRITERIA,
                    CRITERIA[:-2],
                )
            ],
        ),
        (
            "Eligibility",
            {},
            {"Split": "split", "Inclusion Criteria": None},
            {},
            [compare.finding("c", "N", "w", JOINED, "agree", "absent: blank", None, "")],
        ),
        (
            "Eligibility",
            CRITERIA_STUDY,
            {"Split": "not_split_missing", "Whole Text": CRITERIA},
            {},
            [compare.finding("c", "N", "w", "Eligibility › Whole Text", "agree", "", CRITERIA, CRITERIA)],
        ),
        (
            "Eligibility",
            {},
            {"Split": "not_split_missing", "Whole Text": "not reported"},
            {},
            [
                compare.finding(
                    "c",
                    "N",
                    "w",
                    "Eligibility › Whole Text",
                    "agree",
                    "absent: not reported",
                    "<absent>",
                    "not reported",
                )
            ],
        ),
        (
            "Publications",
            {},
            {"PMID": "32021616"},
            {"PMID": "https://pubmed.ncbi.nlm.nih.gov/32021616/"},
            [
                compare.finding(
                    "c-links",
                    "N",
                    "w",
                    "Publications › PMID link",
                    "agree",
                    "",
                    "32021616",
                    "https://pubmed.ncbi.nlm.nih.gov/32021616/",
                )
            ],
        ),
        (
            "Publications",
            {},
            {"PMID": "32021616"},
            {"PMID": "https://pubmed.ncbi.nlm.nih.gov/24142084/"},
            [
                compare.finding(
                    "c-links",
                    "N",
                    "w",
                    "Publications › PMID link",
                    "differ",
                    "not the PMID's PubMed page",
                    "32021616",
                    "https://pubmed.ncbi.nlm.nih.gov/24142084/",
                )
            ],
        ),
        (
            "Publications",
            {},
            {"PMID": "not reported"},
            {"PMID": "https://example.org/32021616"},
            [
                compare.finding(
                    "c-links",
                    "N",
                    "w",
                    "Publications › PMID link",
                    "differ",
                    "not the PMID's PubMed page",
                    "not reported",
                    "https://example.org/32021616",
                )
            ],
        ),
        ("Publications", {}, {"PMID": "not reported"}, {}, []),
        (
            "Documents",
            {},
            {"File": "P.pdf"},
            {"File": DOC_LINK},
            [compare.finding("c-links", "N", "w", "Documents › File link", "agree", "", "P.pdf", DOC_LINK)],
        ),
        (
            "Documents",
            {},
            {"File": "P.pdf"},
            {},
            [
                compare.finding(
                    "c-links",
                    "N",
                    "w",
                    "Documents › File link",
                    "differ",
                    "not the study's copy of the file",
                    "P.pdf",
                )
            ],
        ),
        ("Arms", {}, {"File": "P.pdf"}, {}, []),
    ],
)
def test_each_sheets_further_check_has_its_exact_result(name, study, cells, links, expected):
    assert (
        compare.special_checks(name, "N", study, {"row": 2, "cells": cells, "links": links}, "w") == expected
    )


def test_an_adverse_event_rows_further_check_is_its_at_risk_rule():
    cells = {
        "Location": compare.format_location(SERIOUS),
        "At Risk Source": "stated",
        "Participants at Risk": 37,
    }
    held = {"At Risk Source": "stated", "Participants at Risk": 37}
    assert compare.special_checks(
        "Adverse Events", NCT, EVENTS, {"row": 2, "cells": cells, "links": {}}, "w"
    ) == [
        compare.finding(
            "c-rule",
            NCT,
            "w",
            "Adverse Events › Participants at Risk, At Risk Source",
            "agree",
            "stated: the count the rule names",
            held,
            held,
        )
    ]


def _raised(call, *args):
    """What a call raised, compared as a value: its type's name and its arguments."""
    try:
        call(*args)
    except Exception as error:
        return (type(error).__name__, error.args)
    return None


def test_a_column_spec_of_none_is_refused_by_name():
    assert _raised(compare.column_value, None, {}, (1,)) == (
        "AttributeError",
        ("'NoneType' object has no attribute 'startswith'",),
    )


def test_a_column_spec_of_a_number_is_refused_by_name():
    assert _raised(compare.column_value, -1, {}, (1,)) == (
        "AttributeError",
        ("'int' object has no attribute 'startswith'",),
    )


AE_COLUMNS = compare.REVIEW_SHEETS["Adverse Events"]["columns"]


def test_a_group_title_is_joined_by_the_rows_group_id():
    assert compare.column_value(AE_COLUMNS["Group Title"], EVENTS, SERIOUS) == (
        "value",
        (True, "Safety Analysis Set"),
    )
    assert compare.column_value(AE_COLUMNS["Group Title"], EVENTS, SERIOUS_BLANK) == (
        "value",
        (True, "Arm B"),
    )
    assert compare.column_value("@.numAffected", EVENTS, SERIOUS) == ("value", (True, 1))
    assert compare.column_value({"form": "event table"}, EVENTS, SERIOUS) == ("value", (True, "serious"))


def test_a_join_without_one_match_or_a_path_outside_the_row_is_not_compared():
    orphan = copy.deepcopy(EVENTS)
    orphan["resultsSection"]["adverseEventsModule"]["seriousEvents"][0]["stats"][0]["groupId"] = "EG009"
    assert compare.column_value(AE_COLUMNS["Group Title"], orphan, SERIOUS) == (
        "skip",
        "0 elements of resultsSection.adverseEventsModule.eventGroups have id 'EG009'",
    )
    assert compare.column_value(AE_COLUMNS["Group Title"], EVENTS, None) == (
        "skip",
        "the row's element does not reach the join key",
    )
    assert compare.column_value("@classes.title", EVENTS, SERIOUS) == (
        "skip",
        "the row's element does not reach this column's field",
    )


def test_an_at_risk_count_that_follows_its_declared_rule_agrees():
    stated = {"At Risk Source": "stated", "Participants at Risk": 37}
    assert compare.at_risk_result(EVENTS, SERIOUS, stated) == (
        "agree",
        "stated: the count the rule names",
        stated,
    )
    total = {"At Risk Source": "group total", "Participants at Risk": 5}
    assert compare.at_risk_result(EVENTS, SERIOUS_BLANK, total) == (
        "agree",
        "group total: the count the rule names",
        total,
    )
    other = {"At Risk Source": "group total", "Participants at Risk": 6}
    assert compare.at_risk_result(EVENTS, OTHER_BLANK, other)[0] == "agree"
    row = _review_row(2, {"Location": compare.format_location(SERIOUS), **stated})
    checks = compare.special_checks("Adverse Events", NCT, EVENTS, row, "w")
    assert [(i["comparison"], i["result"]) for i in checks] == [("c-rule", "agree")]


def test_an_at_risk_count_or_source_off_its_rule_differs_and_a_row_not_a_count_is_not_comparable():
    assert compare.at_risk_result(
        EVENTS, SERIOUS, {"At Risk Source": "stated", "Participants at Risk": 38}
    ) == (
        "differ",
        "different value",
        {"At Risk Source": "stated", "Participants at Risk": 37},
    )
    assert compare.at_risk_result(
        EVENTS, SERIOUS, {"At Risk Source": "group total", "Participants at Risk": 37}
    )[:2] == ("differ", "the rule gives At Risk Source 'stated'")
    assert compare.at_risk_result(EVENTS, SERIOUS_BLANK, {"At Risk Source": "stated"})[:2] == (
        "differ",
        "the rule gives At Risk Source 'group total'",
    )
    orphan = copy.deepcopy(EVENTS)
    orphan["resultsSection"]["adverseEventsModule"]["seriousEvents"][0]["stats"][1]["groupId"] = "EG009"
    assert compare.at_risk_result(orphan, SERIOUS_BLANK, {}) == (
        "not_comparable",
        "0 event groups have the count's group id",
        None,
    )
    assert compare.at_risk_result(EVENTS, None, {}) == (
        "not_comparable",
        "the row's Location is not an adverse event's count",
        None,
    )
    group = ("resultsSection", "adverseEventsModule", "eventGroups", 0)
    assert compare.at_risk_result(EVENTS, group, {})[0] == "not_comparable"


def test_a_column_declared_stated_from_its_paired_field_agrees():
    declared = ("stated", "protocolSection.designModule.phases")
    assert compare.declared_source_result("protocolSection.designModule.phases[*]", declared) == (
        "agree",
        "declared stated from the field the reader pairs it with",
    )
    assert compare.declared_source_result("@^.term", ("stated", "...Events[].term"))[0] == "agree"
    assert (
        compare.declared_source_result("@measurements.value", ("stated", "...measurements[].value, (text)"))[
            0
        ]
        == "agree"
    )
    join = AE_COLUMNS["Group Title"]
    assert (
        compare.declared_source_result(join, ("stated", "eventGroups[].title for the group id"))[0] == "agree"
    )
    link = ("stated (link)", "references[].pmid; link: its PubMed page")
    assert compare.declared_source_result("@.pmid", link)[0] == "agree"
    assert compare.declared_source_result({"form": "position"}, ("stated", "position, from 1")) == (
        "agree",
        "declared stated; the reader reads its form from this declaration",
    )


def test_a_column_declared_computed_from_another_field_or_not_at_all_differs():
    assert compare.declared_source_result("@.numAtRisk", ("computed", "at_risk: the event's numAtRisk")) == (
        "differ",
        "declared computed, not stated",
    )
    assert compare.declared_source_result("@.numAffected", ("stated", "...Events[].stats[].numEvents")) == (
        "differ",
        "the declared source does not name the field the reader pairs this column with",
    )
    wrong_module = ("stated", "protocolSection.statusModule.phases")
    assert compare.declared_source_result("protocolSection.designModule.phases", wrong_module)[0] == "differ"
    assert compare.declared_source_result("@.x", None) == (
        "differ",
        "review.xlsx's About sheet declares no such column",
    )
    sheets = {"Sites": {"columns": {"City": "@.city", "ZIP": "@.zip"}}}
    about = [
        ("provenance", "query", "filter.ids=x", None),
        ("column", "Sites › City", "stated", "protocolSection.contactsLocationsModule.locations[].city"),
        ("column", "Sites › ZIP", "computed", "a rule"),
    ]
    assert [(i["where"], i["result"], i["found"]) for i in compare.compare_declared(sheets, about)] == [
        ("Sites › City", "agree", ("stated", "protocolSection.contactsLocationsModule.locations[].city")),
        ("Sites › ZIP", "differ", ("computed", "a rule")),
    ]


# --- (g) provenance ---------------------------------------------------------------------------------------

VERSION = {"apiVersion": "2.0.5", "dataTimestamp": "2026-10-30T09:00:04"}
ABOUT = [
    ("TrialLedger record workbook", "TrialLedger 0.1.0", None, None),
    ("provenance", "source", "https://clinicaltrials.gov/api/v2/studies", None),
    ("provenance", "query", f"filter.ids={NCT},{ALIAS}", None),
    ("provenance", "api_version", "2.0.5", None),
    ("provenance", "data_timestamp", "2026-10-30T09:00:04", None),
    ("provenance", "study_count", 2, None),
    ("provenance", "tool", "TrialLedger 0.1.0", None),
    ("requested id", NCT, "found", None),
    ("requested id", ALIAS, "found", None),
]


def test_provenance_the_registry_and_the_selection_give_agrees():
    out = compare.provenance_results(
        ABOUT, "record.xlsx About", VERSION, [NCT, ALIAS], {NCT: STUDY, ALIAS: ALIASED}
    )
    assert [(i["nct"], i["field"], i["result"]) for i in out] == [
        ("*", "source", "agree"),
        ("*", "query", "agree"),
        ("*", "api_version", "agree"),
        ("*", "data_timestamp", "agree"),
        ("*", "study_count", "agree"),
        ("*", "tool", "not_comparable"),
        (NCT, "requested id", "agree"),
        (ALIAS, "requested id", "agree"),
    ]
    assert {i["where"] for i in out} == {"record.xlsx About"}


def test_provenance_off_the_registry_or_an_id_unaccounted_for_is_named():
    about = [row for row in ABOUT if row[1] not in ("study_count", ALIAS)]
    about = [
        ("provenance", "data_timestamp", "2026-10-29T09:00:04", None) if r[1] == "data_timestamp" else r
        for r in about
    ]
    about += [("requested id", NCT, "found", None), ("requested id", "NCT00085033", "found", None)]
    out = compare.provenance_results(
        about, "w", VERSION, [NCT, ALIAS, "NCT99999999"], {NCT: STUDY, ALIAS: ALIASED}
    )
    issues = [(i["nct"], i["field"], i["result"], i["why"]) for i in out if i["result"] != "agree"]
    assert issues == [
        ("*", "query", "differ", "the cell holds the first 34 of 46 characters"),
        ("*", "data_timestamp", "differ", "different text"),
        ("*", "study_count", "omitted", "the About sheet does not state it"),
        (
            "*",
            "tool",
            "not_comparable",
            "TrialLedger's record of its own run; the registry holds nothing to compare it with",
        ),
        (NCT, "requested id", "duplicated", "2 rows account for the requested ID"),
        (ALIAS, "requested id", "omitted", "0 rows account for the requested ID"),
        ("NCT99999999", "requested id", "omitted", "0 rows account for the requested ID"),
        ("NCT00085033", "requested id", "differ", "an ID the selection did not request"),
    ]
    unfetched = compare.provenance_results(ABOUT, "w", VERSION, [NCT, ALIAS], {NCT: STUDY})
    assert [(i["result"], i["found"]) for i in unfetched if i["nct"] == ALIAS] == [
        ("not_comparable", "found")
    ]
    lost = [("requested id", NCT, "not found", None)]
    assert compare.provenance_results(lost, "w", {}, [NCT], {NCT: STUDY})[-1]["result"] == "differ"


# --- (d), (f), the summary and the defects ----------------------------------------------------------------


def test_identical_csv_bytes_agree_and_a_byte_order_mark_or_a_changed_line_is_named():
    api = b"NCT Number,Study Status\r\nNCT07780110,AVAILABLE\r\n"
    same = compare.csv_bytes_results(api, api)
    assert [(i["where"], i["result"], i["why"]) for i in same] == [
        ("studies.csv", "agree", "byte for byte identical")
    ]
    assert same[0]["expected"] == same[0]["found"] and len(same[0]["found"]) == 64
    marked = compare.csv_bytes_results(b"\xef\xbb\xbf" + api, api)
    assert [(item["where"], item["result"]) for item in marked] == [
        ("studies.csv", "differ"),
        ("byte-order mark", "differ"),
        ("header", "agree"),
        ("line 2", "agree"),
    ]
    assert (marked[1]["why"], marked[1]["expected"], marked[1]["found"]) == (
        "a UTF-8 byte-order mark (EF BB BF) begins studies.csv only",
        "4e4354",
        "efbbbf",
    )
    assert compare.csv_bytes_results(api, b"\xef\xbb\xbf" + api)[1]["why"].endswith("the API's CSV only")
    changed = compare.csv_bytes_results(api.replace(b"AVAILABLE", b"AVAILABLX"), api)
    assert [(i["nct"], i["where"], i["result"], i["why"]) for i in changed][-1] == (
        NCT,
        "line 2",
        "differ",
        "the bytes differ from byte 20",
    )
    assert (changed[-1]["expected"], changed[-1]["found"]) == (
        "NCT07780110,AVAILABLE\r\n",
        "NCT07780110,AVAILABLX\r\n",
    )


def test_a_line_missing_from_or_added_to_studies_csv_is_named():
    api = b"NCT Number\r\nNCT07780110\r\nNCT00069758\r\n"
    short = compare.csv_bytes_results(api[:-13], api)
    assert [(i["nct"], i["where"], i["result"], i["why"]) for i in short][1:] == [
        ("*", "header", "agree", ""),
        (NCT, "line 2", "agree", ""),
        (ALIAS, "line 3", "omitted", "a line of the API's CSV missing"),
    ]
    longer = compare.csv_bytes_results(api + b"NCT01410227\r\n", api)
    assert [(i["nct"], i["where"], i["result"], i["why"]) for i in longer][-1] == (
        "NCT01410227",
        "line 4",
        "differ",
        "a line the API's CSV does not have",
    )
    cut = compare.csv_bytes_results(b"NCT Number\r\nNCT0778", b"NCT Number\r\nNCT07780110\r\n")
    assert cut[-1]["why"] == "the bytes differ from byte 7"


def test_records_kept_as_sent_agree_and_a_changed_or_unmatched_record_is_named():
    assert compare.compare_records({NCT: STUDY}, {NCT: STUDY}) == [
        compare.finding("f", NCT, "studies.json", "record", "agree", "")
    ]
    changed = copy.deepcopy(STUDY)
    changed["protocolSection"]["identificationModule"]["briefTitle"] = "x"
    changed["hasResults"] = True
    result = compare.compare_records({NCT: changed}, {NCT: STUDY})[0]
    assert (result["result"], result["why"]) == ("differ", "fields differ: hasResults, " + TITLE)
    extra = copy.deepcopy(STUDY)
    extra["protocolSection"]["identificationModule"]["acronym"] = "V"
    assert compare.compare_records({NCT: STUDY}, {NCT: extra})[0]["why"] == (
        "fields differ: protocolSection.identificationModule.acronym"
    )
    assert [
        (i["nct"], i["result"], i["why"]) for i in compare.compare_records({ALIAS: ALIASED}, {NCT: STUDY})
    ] == [
        (ALIAS, "differ", "in studies.json, not fetched"),
        (NCT, "omitted", "fetched, not in studies.json"),
    ]


def test_the_summary_counts_each_result_per_field_and_absence_apart():
    items = [
        compare.finding("c", NCT, "w", "f", "agree", "absent: blank"),
        compare.finding("c", ALIAS, "w", "f", "agree", ""),
        compare.finding("c", NCT, "w", "f", "differ", "different text"),
        compare.finding("a", NCT, "w", "g", "omitted", "x"),
    ]
    assert compare.summarize(items) == {
        "a": {"g": {"omitted": 1, "studies": 1}},
        "c": {"f": {"agree": 2, "of which absent": 1, "differ": 1, "studies": 2}},
    }
    assert compare.summarize([]) == {}


def test_a_planted_defect_is_caught_only_by_a_new_result_at_its_place():
    defect = {"comparisons": ["a", "b-workbook"], "nct": NCT, "marks": [TITLE]}
    hit = compare.finding("a", NCT, TITLE, "f", "differ", "different text")
    by_field = compare.finding("b-workbook", NCT, "Study Title", TITLE, "differ", "different text")
    elsewhere = compare.finding("a", NCT, "protocolSection.other", "g", "differ", "different text")
    other_study = compare.finding("a", ALIAS, TITLE, "f", "differ", "different text")
    other_comparison = compare.finding("c", NCT, TITLE, "f", "differ", "different text")
    assert compare.defect_caught(defect, [hit, by_field, elsewhere]) == [hit, by_field]
    assert compare.defect_caught(defect, [elsewhere, other_study, other_comparison]) == []
    any_study = {"comparisons": ["a"], "nct": "*", "marks": [TITLE]}
    assert compare.defect_caught(any_study, [hit, other_study]) == [hit, other_study]
    assert compare.issue_key(hit) == ("a", NCT, TITLE, "f", "differ")
    assert compare.issue_key(other_study) != compare.issue_key(hit)


# --- the selection ----------------------------------------------------------------------------------------


def test_the_draw_is_the_seeds_whatever_order_the_registry_lists_the_ids_in():
    ids = ["NCT00000003", "NCT00000001", "NCT00000002"]
    shuffled = ids[:]
    random.Random(7).shuffle(shuffled)
    assert selection.choose(ids, 1, "s", 0) == selection.choose(shuffled, 1, "s", 0)
    assert selection.choose(ids + ids, 1, "s", 0) == selection.choose(ids, 1, "s", 0)
    assert selection.choose(ids, 1, "s", 0) in ids
    assert selection.choose(["NCT00000009"], 1, "s", 0) == "NCT00000009"
    assert selection.choose([], 1, "s", 0) is None
    assert {selection.choose(ids, 1, "s", attempt) for attempt in range(12)} == set(ids)


def test_a_month_is_drawn_from_the_seed_and_never_past_the_last_month():
    draws = [selection.month_draw(selection.SEED, "s", attempt) for attempt in range(400)]
    assert draws[3] == selection.month_draw(selection.SEED, "s", 3)
    assert all((selection.FIRST_YEAR, 1) <= draw <= selection.LAST_MONTH for draw in draws)
    assert all(1 <= month <= 12 for _, month in draws)
    assert len(set(draws)) > 100
    assert min(draws)[0] == selection.FIRST_YEAR and max(draws)[0] == selection.LAST_MONTH[0]
    assert selection.month_draw(selection.SEED, "s", 3) != selection.month_draw(selection.SEED, "t", 3)


def test_a_window_narrows_the_stratum_to_a_month_or_a_year_of_first_posting():
    assert selection.window_expression("AREA[Phase]PHASE1", 2024, 2) == (
        "(AREA[Phase]PHASE1) AND AREA[StudyFirstPostDate]RANGE[2024-02-01,2024-02-29]"
    )
    assert selection.window_expression("X", 2023, 2).endswith("RANGE[2023-02-01,2023-02-28]")
    assert selection.window_expression("X", 2025, 12).endswith("RANGE[2025-12-01,2025-12-31]")
    assert (
        selection.window_expression("X", 2023, None)
        == "(X) AND AREA[StudyFirstPostDate]RANGE[2023-01-01,2023-12-31]"
    )
    either = "AREA[OverallStatus]A OR AREA[OverallStatus]B"
    assert selection.window_expression(either, 2020, 4).startswith(f"({either}) AND ")


def test_the_selection_records_each_trials_facts_and_their_coverage():
    alias = selection.record_facts(ALIASED, 7443)
    assert alias == {
        "nctId": ALIAS,
        "phases": ["PHASE2"],
        "overallStatus": "COMPLETED",
        "studyType": "INTERVENTIONAL",
        "hasResults": False,
        "leadSponsorClass": "INDUSTRY",
        "recordBytes": 7443,
        "nctIdAliases": ["NCT00085033"],
    }
    facts = [selection.record_facts(STUDY, 1738), alias, {**alias, "phases": ["PHASE1", "PHASE2"]}]
    covered = selection.coverage(facts)
    assert covered == {
        "phase": {"PHASE1": 1, "PHASE2": 2},
        "combined_phases": {"PHASE1+PHASE2": 1},
        "no_phase_field": 1,
        "overallStatus": {"AVAILABLE": 1, "COMPLETED": 2},
        "studyType": {"EXPANDED_ACCESS": 1, "INTERVENTIONAL": 2},
        "hasResults": {"False": 3},
        "leadSponsorClass": {"INDUSTRY": 3},
        "with_nct_id_aliases": 2,
        "recordBytes": {"min": 1738, "median": 7443, "max": 7443},
    }


def test_a_record_missing_its_modules_gives_empty_facts_and_no_selection_gives_no_sizes():
    assert selection.record_facts({}, 0) == {
        "nctId": None,
        "phases": [],
        "overallStatus": None,
        "studyType": None,
        "hasResults": None,
        "leadSponsorClass": None,
        "recordBytes": 0,
        "nctIdAliases": [],
    }
    empty = selection.coverage([selection.record_facts({}, 0)])
    assert (empty["phase"], empty["no_phase_field"], empty["overallStatus"]) == ({}, 1, {"None": 1})
    assert selection.coverage([])["recordBytes"] == {}


# --- one exact outcome per test, for the calls the decisions' convergence named -----------------------------


def test_the_declared_pairings_of_two_columns_are_each_judged():
    sheets = {"Sites": {"columns": {"City": "@.city", "ZIP": "@.zip"}}}
    city = ("stated", "protocolSection.contactsLocationsModule.locations[].city")
    about = [
        ("provenance", "query", "filter.ids=x", None),
        ("column", "Sites › City", *city),
        ("column", "Sites › ZIP", "computed", "a rule"),
    ]
    assert compare.compare_declared(sheets, about) == [
        compare.finding(
            "c-declared",
            "*",
            "Sites › City",
            "Sites › City",
            "agree",
            "declared stated from the field the reader pairs it with",
            "@.city",
            city,
        ),
        compare.finding(
            "c-declared",
            "*",
            "Sites › ZIP",
            "Sites › ZIP",
            "differ",
            "declared computed, not stated",
            "@.zip",
            ("computed", "a rule"),
        ),
    ]


def test_an_about_sheet_stating_nothing_omits_every_value_and_every_id():
    omitted = "the About sheet does not state it"
    assert compare.provenance_results([(1,)], "x", {}, ["x"], {"x": {}}) == [
        compare.finding(
            "g", "*", "x", "source", "omitted", omitted, "https://clinicaltrials.gov/api/v2/studies"
        ),
        compare.finding("g", "*", "x", "query", "omitted", omitted, "filter.ids=x"),
        compare.finding("g", "*", "x", "api_version", "omitted", omitted),
        compare.finding("g", "*", "x", "data_timestamp", "omitted", omitted),
        compare.finding("g", "*", "x", "study_count", "omitted", omitted, 1),
        compare.finding(
            "g", "x", "x", "requested id", "omitted", "0 rows account for the requested ID", 1, 0
        ),
    ]


def test_a_cut_line_is_named_at_its_first_differing_byte():
    pulled, fetched = b"NCT Number\r\nNCT0778", b"NCT Number\r\nNCT07780110\r\n"
    digests = (hashlib.sha256(fetched).hexdigest(), hashlib.sha256(pulled).hexdigest())
    assert compare.csv_bytes_results(pulled, fetched) == [
        compare.finding(
            "d", "*", "studies.csv", "studies.csv", "differ", "not byte for byte identical", *digests
        ),
        compare.finding("d", "*", "header", "studies.csv line", "agree", ""),
        compare.finding(
            "d",
            NCT,
            "line 2",
            "studies.csv line",
            "differ",
            "the bytes differ from byte 7",
            "NCT07780110\r\n",
            "NCT0778",
        ),
    ]


def test_a_record_fetched_but_not_kept_is_omitted():
    assert compare.compare_records({}, {"_unread": "x"}) == [
        compare.finding("f", "_unread", "studies.json", "record", "omitted", "fetched, not in studies.json")
    ]


def test_a_record_kept_but_not_fetched_differs():
    assert compare.compare_records({"_unread": "x"}, {}) == [
        compare.finding("f", "_unread", "studies.json", "record", "differ", "in studies.json, not fetched")
    ]


def test_a_result_without_its_comparison_is_refused_by_the_missing_key():
    outcome = None
    try:
        compare.summarize([{}])
    except Exception as error:
        outcome = (type(error).__name__, error.args)
    assert outcome == ("KeyError", ("comparison",))


def test_a_study_with_no_rows_in_any_sheet_has_its_study_rows_omitted():
    omitted = "an element of the record no row of the sheet stands for"
    assert compare.compare_review({"x": {}}, {"x": [{}]}) == [
        compare.finding("c-rows", "x", "Studies", "Studies", "omitted", omitted),
        compare.finding("c-rows", "x", "Eligibility", "Eligibility", "omitted", omitted),
    ]


def test_an_adverse_event_row_is_judged_column_by_column_its_join_skipped_and_its_rule_applied():
    study = {
        "resultsSection": {
            "adverseEventsModule": {
                "eventGroups": [{"id": "EG000", "title": "A"}],
                "seriousEvents": [
                    {"term": "Fever", "stats": [{"groupId": "EG009", "numAffected": 1, "numAtRisk": 5}]}
                ],
            }
        }
    }
    location = "resultsSection.adverseEventsModule.seriousEvents[0].stats[0]"
    cells = {"NCT Number": "N", "Location": location, "Group Title": "A", "Term": "Fever"}
    row = {"row": 2, "cells": cells, "links": {"NCT Number": STUDY_URL + "N"}}
    where, sheet = "Adverse Events!row 2", "Adverse Events › "
    missing = [
        "Organ System",
        "Source Vocabulary",
        "Assessment Type",
        "Notes",
        "Group ID",
        "Participants Affected",
        "Events",
    ]
    absent = "an element of the record no row of the sheet stands for"
    assert compare.compare_review({"N": study}, {"Adverse Events": [row]}) == [
        compare.finding("c-rows", "N", "Studies", "Studies", "omitted", absent),
        compare.finding("c-rows", "N", "Eligibility", "Eligibility", "omitted", absent),
        compare.finding(
            "c-links", "N", where, sheet + "NCT Number link", "agree", "", STUDY_URL + "N", STUDY_URL + "N"
        ),
        compare.finding("c", "N", where, sheet + "Term", "agree", "", "Fever", "Fever"),
        *[
            compare.finding("c", "N", where, sheet + c, "not_comparable", "the sheet has no such column")
            for c in missing
        ],
        compare.finding(
            "c",
            "N",
            where,
            sheet + "Group Title",
            "not_comparable",
            "0 elements of resultsSection.adverseEventsModule.eventGroups have id 'EG009'",
            None,
            "A",
        ),
        compare.finding("c", "N", where, sheet + "Table", "not_comparable", "the sheet has no such column"),
        compare.finding(
            "c-rule",
            "N",
            where,
            sheet + "Participants at Risk, At Risk Source",
            "differ",
            "the rule gives At Risk Source 'stated'",
            {"At Risk Source": "stated", "Participants at Risk": 5},
            {"At Risk Source": None, "Participants at Risk": None},
        ),
        compare.finding("c-rows", "N", location, "Adverse Events", "agree", ""),
        compare.finding(
            "c-rows",
            "N",
            "resultsSection.adverseEventsModule.eventGroups[0]",
            "Event Groups",
            "omitted",
            absent,
        ),
    ]


def test_a_planted_defect_without_its_comparisons_is_refused_by_the_missing_key():
    outcome = None
    try:
        compare.defect_caught({}, [{}])
    except Exception as error:
        outcome = (type(error).__name__, error.args)
    assert outcome == ("KeyError", ("comparison",))


def test_a_result_of_another_study_has_its_own_key():
    item = compare.finding("a", ALIAS, TITLE, "f", "differ", "different text")
    assert compare.issue_key(item) == ("a", ALIAS, TITLE, "f", "differ")


def test_an_unnamed_form_has_no_rule():
    assert compare.structure_value("", {}, None) is None


def test_a_placeholder_row_holding_its_declared_columns_differs_naming_them():
    cells = {"Location": "x", "NCT Number": "x", "Warrant": "x"}
    assert compare.placeholder_result("", "", "", cells, cells) == compare.finding(
        "c-rows",
        "",
        "",
        "",
        "differ",
        "a row standing for no element holds values in Location, NCT Number, Warrant",
        None,
        cells,
    )


def test_an_adverse_event_row_that_is_not_a_row_is_refused_by_name():
    row = {"cells": "x", "links": "x", "Split": "x", "PMID": "x", "File": "x", "Location": "x"}
    assert _raised(compare.special_checks, "Adverse Events", "", row, row, "") == (
        "AttributeError",
        ("'str' object has no attribute 'get'",),
    )


def test_an_eligibility_row_that_is_not_a_row_is_refused_by_name():
    row = {"cells": "x", "links": "x", "Split": "x", "PMID": "x", "File": "x", "Location": "x"}
    assert _raised(compare.special_checks, "Eligibility", " ", {"Location": ""}, row, " ") == (
        "AttributeError",
        ("'str' object has no attribute 'get'",),
    )


def test_a_row_without_cells_is_refused_by_the_missing_key():
    assert _raised(compare.special_checks, "x", "x", {}, {}, "x") == ("KeyError", ("cells",))


def test_a_row_without_links_is_refused_by_the_missing_key():
    assert _raised(compare.special_checks, "Adverse Events", " ", {"cells": "x"}, {"cells": "x"}, " ") == (
        "KeyError",
        ("links",),
    )


def test_numbers_in_place_of_bytes_are_refused_by_name():
    assert _raised(compare.csv_bytes_results, -1, -1) == (
        "TypeError",
        ("object supporting the buffer API required",),
    )


def test_a_result_without_its_comparison_has_no_key():
    assert _raised(compare.issue_key, {}) == ("KeyError", ("comparison",))


def test_a_result_without_its_study_has_no_key():
    assert _raised(compare.issue_key, {"comparison": "x"}) == ("KeyError", ("nct",))


def test_any_seed_draws_its_own_month():
    assert selection.month_draw(-1, "", -1) == (2026, 5)


def test_no_selected_trial_covers_nothing():
    assert selection.coverage([]) == {
        "phase": {},
        "combined_phases": {},
        "no_phase_field": 0,
        "overallStatus": {},
        "studyType": {},
        "hasResults": {},
        "leadSponsorClass": {},
        "with_nct_id_aliases": 0,
        "recordBytes": {},
    }


def test_facts_without_phases_are_refused_by_the_missing_key():
    assert _raised(selection.coverage, [{}]) == ("KeyError", ("phases",))


def test_a_record_with_no_modules_gives_empty_facts_of_its_size():
    assert selection.record_facts({}, 1) == {
        "nctId": None,
        "phases": [],
        "overallStatus": None,
        "studyType": None,
        "hasResults": None,
        "leadSponsorClass": None,
        "recordBytes": 1,
        "nctIdAliases": [],
    }


def test_a_protocol_section_that_is_not_an_object_is_refused_by_name():
    assert _raised(selection.record_facts, {"protocolSection": "x"}, 0) == (
        "AttributeError",
        ("'str' object has no attribute 'get'",),
    )


def test_a_whole_year_window_runs_from_january_to_december():
    assert (
        selection.window_expression("X", 2023, None)
        == "(X) AND AREA[StudyFirstPostDate]RANGE[2023-01-01,2023-12-31]"
    )


def test_a_month_window_in_an_early_year_keeps_the_year_as_written():
    assert (
        selection.window_expression("abc", 1, 2) == "(abc) AND AREA[StudyFirstPostDate]RANGE[1-02-01,1-02-28]"
    )


def test_a_month_that_is_not_one_is_refused_by_name():
    assert _raised(selection.window_expression, "", -1, -1) == ("IllegalMonthError", (-1,))


def test_a_form_with_no_rule_is_skipped_by_name():
    assert compare.column_value({"form": "dose"}, {}, ("a", 0)) == ("skip", "no rule for the form 'dose'")


def test_a_sheet_without_columns_is_refused_by_the_missing_key():
    assert _raised(compare.compare_declared, {"x": {}}, [(1,)]) == ("KeyError", ("columns",))


def test_a_cut_line_is_named_at_its_first_differing_byte_by_its_digests():
    assert compare.csv_bytes_results(b"NCT Number\r\nNCT0778", b"NCT Number\r\nNCT07780110\r\n")[0] == (
        compare.finding(
            "d",
            "*",
            "studies.csv",
            "studies.csv",
            "differ",
            "not byte for byte identical",
            hashlib.sha256(b"NCT Number\r\nNCT07780110\r\n").hexdigest(),
            hashlib.sha256(b"NCT Number\r\nNCT0778").hexdigest(),
        )
    )


def test_a_placeholder_row_with_no_cells_agrees_saying_nothing():
    assert compare.placeholder_result("abc", "abc", "abc", {}, {}) == compare.finding(
        "c-rows",
        "abc",
        "abc",
        "abc",
        "agree",
        "absent: the record holds no element of this kind; the row says so ()",
    )


def test_a_sheet_with_no_further_check_adds_nothing():
    row = {"cells": "x", "links": "x", "Split": "x", "PMID": "x", "File": "x", "Location": "x"}
    assert compare.special_checks("", "", {}, row, "") == []


def test_an_outcome_section_outside_the_outcome_lists_is_absent():
    assert compare.structure_value("outcome section", {}, ("protocolSection", "x", 0)) == (False, None)


def test_an_event_table_outside_the_event_lists_is_absent():
    assert compare.structure_value("event table", {}, ("a", 0)) == (False, None)


def test_a_position_of_no_list_element_is_absent():
    assert compare.structure_value("position", {}, ("protocolSection",)) == (False, None)


def test_a_position_of_no_row_is_absent():
    assert compare.structure_value("position", {}, None) == (False, None)


def test_an_outcome_section_of_a_bare_index_is_refused_by_name():
    assert _raised(compare.structure_value, "outcome section", {}, (1,)) == (
        "IndexError",
        ("tuple index out of range",),
    )
