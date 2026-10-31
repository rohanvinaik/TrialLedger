"""The vendored contracts are the authority; these facts in the code are held to them.

spec/ctg-oas-v2.yaml is the API contract; TrialLedger/registry/ holds the API's own field metadata and enum
table (/studies/metadata, /studies/enums). Every enum value, field path and table the code relies on must be
in them, and the derived tables must equal what was reviewed.
"""

from pathlib import Path

import yaml

from TrialLedger import registry
from TrialLedger.checks import CLOSED_STATUSES, INTERVENTION_TYPE_LABELS, REGISTRY_ASSIGNED_STATUSES
from TrialLedger.ingest import API_BASE, PAGE_SIZE, RESERVED_PARAMETERS, SPEC_API_VERSION
from TrialLedger.ledger import APPLIES_TO, FIXED_ROLES, IDENTIFIED_ROLES, REDACTED_WHEN_WITHHELD
from TrialLedger.links import REFERENCE_ROLES

SPEC = yaml.safe_load((Path(__file__).parents[1] / "spec" / "ctg-oas-v2.yaml").read_text("utf-8"))
LIST_STUDIES = {p["name"]: p for p in SPEC["paths"]["/studies"]["get"]["parameters"]}
SCHEMAS = SPEC["components"]["schemas"]


def enum(name):
    return set(SCHEMAS[name]["enum"])


def test_base_url_is_the_specs_server():
    assert SPEC["servers"][0]["url"] == API_BASE


def test_spec_version_is_the_documents_version():
    assert SPEC["info"]["version"] == SPEC_API_VERSION


def test_every_reserved_parameter_exists_in_the_spec():
    assert set(RESERVED_PARAMETERS) <= set(LIST_STUDIES)


def test_the_formats_the_tool_requests_are_allowed():
    assert {"json", "csv"} <= set(LIST_STUDIES["format"]["schema"]["enum"])
    assert "markdown" in LIST_STUDIES["markupFormat"]["schema"]["enum"]
    assert LIST_STUDIES["countTotal"]["schema"]["type"] == "boolean"


def test_page_size_is_within_what_the_api_honours():
    assert 1 <= PAGE_SIZE <= 1000
    assert "coerced down to  1,000" in LIST_STUDIES["pageSize"]["description"]


def test_the_enum_values_the_code_names_are_the_registrys():
    assert set(CLOSED_STATUSES) <= enum("Status") and set(REGISTRY_ASSIGNED_STATUSES) <= enum("Status")
    assert set(INTERVENTION_TYPE_LABELS) == enum("InterventionType")
    assert set(REFERENCE_ROLES) == enum("ReferenceType")
    assert {"PRIMARY", "SECONDARY", "OTHER_PRE_SPECIFIED"} <= enum("OutcomeMeasureType")
    assert {"ACTUAL", "ESTIMATED"} == enum("DateType") == enum("EnrollmentType")
    assert {"INTERVENTIONAL", "OBSERVATIONAL"} <= enum("StudyType")
    assert "NA" in enum("Phase")


def test_the_enum_labels_are_the_registry_tables():
    assert registry.enum_labels("InterventionType") == INTERVENTION_TYPE_LABELS
    assert INTERVENTION_TYPE_LABELS["DIETARY_SUPPLEMENT"] == "Dietary Supplement"


def test_every_field_the_tables_name_exists_in_the_metadata():
    for field in list(APPLIES_TO) + list(REDACTED_WHEN_WITHHELD):
        assert field in registry.FIELDS, field
    for place in list(FIXED_ROLES) + list(IDENTIFIED_ROLES):
        assert ".".join(place) in registry.FIELDS, place
    for place, (_, field) in IDENTIFIED_ROLES.items():
        assert ".".join(place) + "." + field in registry.FIELDS, (place, field)


def test_the_withheld_redactions_are_the_reviewed_list():
    assert len(REDACTED_WHEN_WITHHELD) == 42
    assert "protocolSection.eligibilityModule.stdAges" in REDACTED_WHEN_WITHHELD
    assert "protocolSection.statusModule.overallStatus" not in REDACTED_WHEN_WITHHELD


def test_the_registry_files_are_the_ones_shipped():
    assert len(registry.METADATA_DIGEST) == len(registry.ENUMS_DIGEST) == 64
    assert (
        registry.category("protocolSection.designModule.designInfo.allocation")
        == "Study Protocol › Study Design"
    )
    assert registry.title("hasResults") == "Has Results"
