"""The vendored spec (spec/ctg-oas-v2.yaml) is the contract; these facts in the code are held to it."""

from pathlib import Path

import yaml

from TrialLedger.ingest import API_BASE, PAGE_SIZE, RESERVED_PARAMETERS, SPEC_API_VERSION

SPEC = yaml.safe_load((Path(__file__).parents[1] / "spec" / "ctg-oas-v2.yaml").read_text("utf-8"))
LIST_STUDIES = {p["name"]: p for p in SPEC["paths"]["/studies"]["get"]["parameters"]}


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
