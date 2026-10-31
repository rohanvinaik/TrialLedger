"""Against the real ClinicalTrials.gov API. Opt-in: `uv run pytest -m live`."""

import pytest

from TrialLedger.ingest import SPEC_API_VERSION, pull

pytestmark = pytest.mark.live


def test_lookup_by_id_and_by_alias_through_the_real_api():
    # NCT01086644 is an alias of NCT01030536 (observed 2026-10-31); the API answers with the canonical study.
    result = pull({"filter.ids": "NCT04852770,NCT01086644"})
    ids = sorted(s["protocolSection"]["identificationModule"]["nctId"] for s in result.studies)
    assert ids == ["NCT01030536", "NCT04852770"]
    assert result.csv_text.startswith("NCT Number,")
    assert result.api_version == SPEC_API_VERSION
