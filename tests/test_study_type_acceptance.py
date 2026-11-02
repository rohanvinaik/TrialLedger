"""Authored source-shape acceptance; passing metadata cases is not full clinical coverage."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import openpyxl
import pytest

from acceptance import preserve, reviewer
from tests.schema3_records import record_of
from TrialLedger import contract, readout

NCT = "NCT90000001"  # Arbitrary structural identity, never a clinical selection criterion.
TYPES = ("INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS")
# Independently authored source -> record -> displayed value, not a producer projection.
CASES = (
    ("designModule.designInfo.observationalModel", "observational_model", "COHORT", "Cohort"),
    ("designModule.designInfo.timePerspective", "time_perspective", "PROSPECTIVE", "Prospective"),
    ("designModule.patientRegistry", "patient_registry", False, "No"),
    ("designModule.targetDuration", "target_duration", "24 Months", "24 Months"),
    ("designModule.bioSpec.retention", "biospecimen_retention", "SAMPLES_WITH_DNA", "Samples with DNA"),
    (
        "designModule.bioSpec.description",
        "biospecimen_description",
        "Blood retained.\nNo tissue retained.",
        "Blood retained.\nNo tissue retained.",
    ),
    (
        "eligibilityModule.studyPopulation",
        "study_population",
        "Adults from two community clinics.\nNo hospital recruitment.",
        "Adults from two community clinics.\nNo hospital recruitment.",
    ),
    ("eligibilityModule.samplingMethod", "sampling_method", "PROBABILITY_SAMPLE", "Probability sample"),
    ("designModule.expandedAccessTypes.individual", "expanded_access_types.individual", True, "Yes"),
    ("designModule.expandedAccessTypes.intermediate", "expanded_access_types.intermediate", False, "No"),
    ("designModule.expandedAccessTypes.treatment", "expanded_access_types.treatment", False, "No"),
    (
        "statusModule.expandedAccessInfo.hasExpandedAccess",
        "expanded_access_info.hasExpandedAccess",
        True,
        "Yes",
    ),
    ("statusModule.expandedAccessInfo.nctId", "expanded_access_info.nctId", "NCT90000002", "NCT90000002"),
    (
        "statusModule.expandedAccessInfo.statusForNctId",
        "expanded_access_info.statusForNctId",
        "TEMPORARILY_NOT_AVAILABLE",
        "Temporarily not available",
    ),
    ("designModule.nPtrsToThisExpAccNctId", "expanded_access_referencing_studies", 0, 0),
)


def put(obj, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        obj = obj.setdefault(part, {})
    obj[parts[-1]] = copy.deepcopy(value)


def held(obj, path):
    for part in path.split("."):
        obj = obj[part]
    return obj


def source(study_type="OBSERVATIONAL", *, extras=True):
    body = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT, "briefTitle": "Source-shape acceptance"},
            "statusModule": {
                "overallStatus": "COMPLETED",
                "startDateStruct": {"date": "2020-01-01", "type": "ACTUAL"},
                "primaryCompletionDateStruct": {"date": "2022-01-01", "type": "ACTUAL"},
            },
            "designModule": {"studyType": study_type},
            "eligibilityModule": {
                "eligibilityCriteria": "Inclusion Criteria:\n- Adults aged 18 years or older."
            },
            "conditionsModule": {"conditions": ["Condition stated by source"]},
        },
        "hasResults": False,
    }
    if extras:
        for path, _target, value, _words in CASES:
            put(body["protocolSection"], path, value)
    return body


def produce(tmp_path, body):
    folder = tmp_path / "shape"
    folder.mkdir()
    record = record_of((NCT,), {NCT: body})
    (folder / "landscape.json").write_text(json.dumps(record), encoding="utf-8")
    readout.write_book(record, folder / "landscape.xlsx")
    return folder, record


def facts(book):
    """Independent worksheet traversal, with no renderer helper."""
    sheet = book["Trial review"]
    rows = list(sheet.values)
    headers = rows[0]
    return {
        row[headers.index("Fact")]: (row[headers.index("Value")], row[headers.index("Basis")])
        for row in rows[1:]
        if row[headers.index("Trial ID")] == NCT
    }


@pytest.mark.parametrize("study_type", TYPES)
def test_each_source_present_type_field_survives_record_workbook_and_mcp(tmp_path, study_type):
    body = source(study_type)
    folder, record = produce(tmp_path, body)
    assert not preserve.record_findings({NCT: body}, record)
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    rows = facts(book)
    ask = reviewer.mcp_ask(tmp_path, "shape")
    fields = {f.name: f for f in contract.FIELDS}
    for path, target, value, words in CASES:
        field = fields[f"studies[].{target}"]
        assert field.source == (f"protocolSection.{path}",)
        assert held(record["studies"][0], target) == value
        assert ask("/studies/0/" + target.replace(".", "/")) == ("ok", value)
        assert rows[field.label] == (words, "Registry")
    # Count scope is studies, never patients, referrals or enrollment.
    count_label = fields["studies[].expanded_access_referencing_studies"].label
    assert count_label == "Studies referencing this expanded-access record"
    assert rows[count_label] == (0, "Registry")
    # Metadata explicitly permits these dates on historical expanded-access records.
    assert record["studies"][0]["start_date"]["date"] == "2020-01-01"
    assert record["studies"][0]["primary_completion_date"]["date"] == "2022-01-01"
    book.close()


@pytest.mark.parametrize(
    "target",
    [
        "expanded_access_types.individual",
        "expanded_access_types.intermediate",
        "expanded_access_info.hasExpandedAccess",
        "patient_registry",
    ],
)
def test_missing_boolean_is_never_an_explicit_false(tmp_path, target):
    body = source(extras=False)
    folder, record = produce(tmp_path, body)
    value = held(record["studies"][0], target)
    assert value == {"status": "not_stated", "note": "not_reported"}
    assert reviewer.mcp_ask(tmp_path, "shape")("/studies/0/" + target.replace(".", "/")) == ("ok", value)
    field = next(f for f in contract.FIELDS if f.name == f"studies[].{target}")
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    assert facts(book).get(field.label, ("Not stated", "Not stated")) != ("No", "Registry")
    book.close()


@pytest.mark.parametrize(
    "left,right",
    [
        ("observational_model", "time_perspective"),
        ("expanded_access_types.individual", "expanded_access_types.intermediate"),
        ("expanded_access_info.statusForNctId", "overall_status"),
    ],
)
def test_record_branch_swap_cannot_pass_source_preservation(left, right):
    body = source()
    record = record_of((NCT,), {NCT: body})
    study = record["studies"][0]
    a, b = copy.deepcopy(held(study, left)), copy.deepcopy(held(study, right))
    put(study, left, b)
    put(study, right, a)
    findings = preserve.record_findings({NCT: body}, record)
    assert findings
    assert any(f.field in {f"studies[].{left}", f"studies[].{right}"} for f in findings)


def test_workbook_wrong_boolean_branch_and_linked_status_are_rejected(tmp_path):
    body = source()
    folder, _record = produce(tmp_path, body)
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    sheet = book["Trial review"]
    headers = [cell.value for cell in sheet[1]]
    fact_col, value_col = headers.index("Fact") + 1, headers.index("Value") + 1
    for row in sheet.iter_rows(min_row=2):
        if row[fact_col - 1].value == "Expanded access: individual patients":
            row[value_col - 1].value = "No"
        if row[fact_col - 1].value == "Linked expanded-access recruitment status":
            row[value_col - 1].value = "Completed"
    book.save(folder / "landscape.xlsx")
    book.close()
    findings = preserve.check_run({NCT: body}, folder / "landscape.json", folder / "landscape.xlsx")
    assert any("individual patients" in f.field for f in findings)
    assert any("Linked expanded-access recruitment status" in f.field for f in findings)


@pytest.mark.parametrize(
    "flag,section,status",
    [
        (True, {}, "known"),
        (False, None, "not_posted"),
        (True, None, "unresolved"),
        (False, {}, "unresolved"),
        (None, {}, "not_stated"),
        (None, None, "not_stated"),
    ],
)
def test_results_presence_matrix_never_relabels_inconsistency_as_posted(tmp_path, flag, section, status):
    body = source(extras=False)
    if flag is None:
        del body["hasResults"]
    else:
        body["hasResults"] = flag
    if section is not None:
        body["resultsSection"] = section
    folder, record = produce(tmp_path, body)
    reading = record["studies"][0]["results_posted"]
    assert reading["status"] == status
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    value, basis = facts(book)["Results posted"]
    if status == "unresolved":
        assert str(value).startswith("Unresolved") and basis == "Unresolved"
    elif status == "not_stated":
        assert value == "Not stated" and basis == "Not stated"
    book.close()


def test_posted_partial_modules_are_not_reported_zero_counts(tmp_path):
    body = source(extras=False)
    body["hasResults"] = True
    body["resultsSection"] = {}
    folder, record = produce(tmp_path, body)
    for name in ("participant_flow", "adverse_events", "posted_outcomes", "baseline"):
        assert record["studies"][0][name] == {"status": "not_stated", "note": "not_reported"}
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    rows = facts(book)
    for label in (
        "Participant flow",
        "Adverse events",
        "Posted outcome measures",
        "Baseline characteristics",
    ):
        assert rows[label] == ("Not stated", "Not stated")
    book.close()


def test_unknown_study_type_does_not_establish_clinical_capability(tmp_path):
    body = source("FUTURE_STUDY_TYPE")
    folder, record = produce(tmp_path, body)
    assert record["studies"][0]["study_type"] == "FUTURE_STUDY_TYPE"
    assert "coverage" not in record and "universe" not in record["studies"][0]
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    assert facts(book)["Study type"] == (
        "FUTURE_STUDY_TYPE (a registry code without clinical words)",
        "Registry",
    )
    assert not {"Readings", "Biomarkers", "Across-trial findings"} & set(book.sheetnames)
    book.close()


# All official enum alternatives for these new fields, frozen independently of DISPLAY.
ENUM_CASES = (
    (
        "ObservationalModel",
        "designModule.designInfo.observationalModel",
        "observational_model",
        {
            "COHORT": "Cohort",
            "CASE_CONTROL": "Case-control",
            "CASE_ONLY": "Case-only",
            "CASE_CROSSOVER": "Case-crossover",
            "ECOLOGIC_OR_COMMUNITY": "Ecologic or community",
            "FAMILY_BASED": "Family-based",
            "DEFINED_POPULATION": "Defined population",
            "NATURAL_HISTORY": "Natural history",
            "OTHER": "Other",
        },
    ),
    (
        "DesignTimePerspective",
        "designModule.designInfo.timePerspective",
        "time_perspective",
        {
            "RETROSPECTIVE": "Retrospective",
            "PROSPECTIVE": "Prospective",
            "CROSS_SECTIONAL": "Cross-sectional",
            "OTHER": "Other",
        },
    ),
    (
        "BioSpecRetention",
        "designModule.bioSpec.retention",
        "biospecimen_retention",
        {
            "NONE_RETAINED": "None retained",
            "SAMPLES_WITH_DNA": "Samples with DNA",
            "SAMPLES_WITHOUT_DNA": "Samples without DNA",
        },
    ),
    (
        "SamplingMethod",
        "eligibilityModule.samplingMethod",
        "sampling_method",
        {
            "PROBABILITY_SAMPLE": "Probability sample",
            "NON_PROBABILITY_SAMPLE": "Non-probability sample",
        },
    ),
    (
        "ExpandedAccessStatus",
        "statusModule.expandedAccessInfo.statusForNctId",
        "expanded_access_info.statusForNctId",
        {
            "AVAILABLE": "Available",
            "NO_LONGER_AVAILABLE": "No longer available",
            "TEMPORARILY_NOT_AVAILABLE": "Temporarily not available",
            "APPROVED_FOR_MARKETING": "Approved for marketing",
        },
    ),
)


def test_authored_branch_inventory_matches_official_saved_metadata():
    registry = Path(__file__).parents[1] / "TrialLedger" / "registry"
    metadata = json.loads((registry / "ctg-metadata.json").read_text())
    for path, _target, _value, _words in CASES:
        children = metadata
        for part in ("protocolSection." + path).split("."):
            node = next(n for n in children if n["name"] == part)
            children = node.get("children", [])
        assert not children, f"unreviewed metadata descendants at {path}"
    enums = {
        e["type"]: {v["value"] for v in e["values"]}
        for e in json.loads((registry / "ctg-enums.json").read_text())
    }
    assert enums["StudyType"] == set(TYPES)
    for name, _path, _target, alternatives in ENUM_CASES:
        assert set(alternatives) == enums[name], f"new official branch requires authored acceptance: {name}"


@pytest.mark.parametrize(
    "_enum,path,target,code,words",
    [
        (name, path, target, code, words)
        for name, path, target, alternatives in ENUM_CASES
        for code, words in alternatives.items()
    ],
)
def test_each_official_type_specific_enum_branch_is_preserved_and_displayed(
    tmp_path, _enum, path, target, code, words
):
    body = source("OBSERVATIONAL" if target != "expanded_access_info.statusForNctId" else "INTERVENTIONAL")
    put(body["protocolSection"], path, code)
    folder, record = produce(tmp_path, body)
    assert held(record["studies"][0], target) == code
    field = next(f for f in contract.FIELDS if f.name == f"studies[].{target}")
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    assert facts(book)[field.label] == (words, "Registry")
    book.close()


def test_genuinely_posted_empty_collections_are_zero_listings_not_missing(tmp_path):
    body = source(extras=False)
    body["hasResults"] = True
    body["resultsSection"] = {
        "participantFlowModule": {"periods": []},
        "baselineCharacteristicsModule": {"measures": []},
        "outcomeMeasuresModule": {"outcomeMeasures": []},
        "adverseEventsModule": {"seriousEvents": [], "otherEvents": []},
    }
    folder, _record = produce(tmp_path, body)
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    rows = facts(book)
    assert rows["Periods"] == ("0: Not stated (Participant flow)", "Registry")
    assert rows["Adverse-event terms"] == ("0 serious and 0 other terms (Safety)", "Registry")
    assert rows["Posted outcome measures"] == ("0 measures, 0 values (Posted results)", "Registry")
    assert rows["Baseline characteristics"] == ("0 characteristics (Baseline)", "Registry")
    book.close()


def test_changing_arbitrary_identity_does_not_change_source_shape_coverage():
    body = source()
    another = copy.deepcopy(body)
    another["protocolSection"]["identificationModule"]["nctId"] = "NCT90009999"
    original = record_of((NCT,), {NCT: body})["studies"][0]
    renamed = record_of(("NCT90009999",), {"NCT90009999": another})["studies"][0]
    for _path, target, value, _words in CASES:
        assert held(original, target) == held(renamed, target) == value


@pytest.mark.parametrize(
    "selected,label",
    [
        ("individual", "Expanded access: individual patients"),
        ("intermediate", "Expanded access: intermediate-size population"),
        ("treatment", "Expanded access: treatment IND/protocol"),
    ],
)
def test_each_expanded_access_population_category_has_its_own_boolean_scope(tmp_path, selected, label):
    body = source("EXPANDED_ACCESS")
    categories = {name: name == selected for name in ("individual", "intermediate", "treatment")}
    body["protocolSection"]["designModule"]["expandedAccessTypes"] = categories
    folder, record = produce(tmp_path, body)
    assert record["studies"][0]["expanded_access_types"] == categories
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    rows = facts(book)
    assert rows[label] == ("Yes", "Registry")
    assert (
        sum(
            rows[name][0] == "Yes"
            for name in (
                "Expanded access: individual patients",
                "Expanded access: intermediate-size population",
                "Expanded access: treatment IND/protocol",
            )
        )
        == 1
    )
    book.close()


# Source-shape oracles authored before the collection-presence producer was inspected.
COLLECTION_SHAPES = (
    ("outcomeMeasuresModule", ("outcomeMeasures",), "Posted outcome measures"),
    ("participantFlowModule", ("periods",), "Participant flow"),
    ("baselineCharacteristicsModule", ("measures",), "Baseline characteristics"),
    ("adverseEventsModule", ("seriousEvents", "otherEvents"), "Adverse events"),
)


@pytest.mark.parametrize("study_type", TYPES)
@pytest.mark.parametrize("module,members,label", COLLECTION_SHAPES)
def test_present_module_omitted_collection_is_not_an_empty_list(tmp_path, study_type, module, members, label):
    body = source(study_type, extras=False)
    body["hasResults"] = True
    body["resultsSection"] = {module: {}}
    folder, record = produce(tmp_path, body)
    presence = record["studies"][0]["collection_presence"]
    assert presence["status"] == "known"
    assert presence["rule"] == "landscape.collection_presence"
    for member in members:
        assert presence["result"][f"/resultsSection/{module}/{member}"] == "not_stated"
    ask = reviewer.mcp_ask(tmp_path, "shape")
    assert ask("/studies/0/collection_presence") == ("ok", presence)
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    assert facts(book)[label] == ("Not stated", "Not stated")
    book.close()


@pytest.mark.parametrize("module,members,label", COLLECTION_SHAPES)
def test_present_explicit_empty_collection_has_only_a_zero_listing_count(tmp_path, module, members, label):
    body = source(extras=False)
    body["hasResults"] = True
    body["resultsSection"] = {module: {member: [] for member in members}}
    folder, record = produce(tmp_path, body)
    presence = record["studies"][0]["collection_presence"]
    for member in members:
        assert presence["result"][f"/resultsSection/{module}/{member}"] == "stated_empty"
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    rows = facts(book)
    listing_labels = {
        "participantFlowModule": ("Periods", "0: Not stated (Participant flow)"),
        "outcomeMeasuresModule": (label, "0 measures, 0 values (Posted results)"),
        "baselineCharacteristicsModule": (label, "0 characteristics (Baseline)"),
        "adverseEventsModule": ("Adverse-event terms", "0 serious and 0 other terms (Safety)"),
    }
    actual_label, expected_words = listing_labels[module]
    assert rows[actual_label] == (expected_words, "Registry")
    assert "zero harms" not in str(rows).lower()
    book.close()


@pytest.mark.parametrize("malformed", [None, {}, "not a list", 0])
@pytest.mark.parametrize("module,members,label", COLLECTION_SHAPES)
def test_malformed_result_collection_is_unresolved_not_empty(tmp_path, module, members, label, malformed):
    body = source(extras=False)
    body["hasResults"] = True
    held_members = {member: [] for member in members}
    held_members[members[0]] = malformed
    body["resultsSection"] = {module: held_members}
    folder, record = produce(tmp_path, body)
    presence = record["studies"][0]["collection_presence"]
    assert presence["result"][f"/resultsSection/{module}/{members[0]}"] == "malformed"
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    rows = facts(book)
    # The summary's label may remain its listing label; the state/basis may not imply silence or zero.
    summary_labels = {
        "participantFlowModule": ("Participant flow", "Periods"),
        "outcomeMeasuresModule": (label,),
        "baselineCharacteristicsModule": (label,),
        "adverseEventsModule": ("Adverse events", "Adverse-event terms"),
    }
    displayed = [rows[key] for key in summary_labels[module] if key in rows]
    assert displayed, "malformed source shape requires an explicit summary"
    assert any(str(value).startswith("Unresolved") and basis == "Unresolved" for value, basis in displayed)
    assert not any(str(value).startswith("0 ") or value == "Not stated" for value, _basis in displayed)
    book.close()


@pytest.mark.parametrize("explicit_member", ["seriousEvents", "otherEvents"])
def test_one_empty_adverse_event_branch_does_not_fill_an_omitted_branch(tmp_path, explicit_member):
    body = source(extras=False)
    body["hasResults"] = True
    body["resultsSection"] = {"adverseEventsModule": {explicit_member: []}}
    folder, record = produce(tmp_path, body)
    presence = record["studies"][0]["collection_presence"]["result"]
    absent_member = "otherEvents" if explicit_member == "seriousEvents" else "seriousEvents"
    assert presence[f"/resultsSection/adverseEventsModule/{explicit_member}"] == "stated_empty"
    assert presence[f"/resultsSection/adverseEventsModule/{absent_member}"] == "not_stated"
    book = openpyxl.load_workbook(folder / "landscape.xlsx")
    assert facts(book)["Adverse events"] == ("Not stated", "Not stated")
    book.close()


def test_sparse_interventional_source_passes_whole_independent_preservation(tmp_path):
    body = source("INTERVENTIONAL", extras=False)
    folder, _record = produce(tmp_path, body)
    assert preserve.check_run({NCT: body}, folder / "landscape.json", folder / "landscape.xlsx") == []
