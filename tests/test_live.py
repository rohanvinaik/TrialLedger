"""Against the real ClinicalTrials.gov API. Opt-in: `uv run pytest -m live`."""

import csv
import io
import json

import httpx
import pytest

from TrialLedger.ingest import SPEC_API_VERSION, pull
from TrialLedger.links import document_link, study_link
from TrialLedger.record import verify_folder, write_record

pytestmark = pytest.mark.live


def test_lookup_by_id_and_by_alias_through_the_real_api():
    # NCT01086644 is an alias of NCT01030536 (observed 2026-10-31); the API answers with the canonical study.
    result = pull({"filter.ids": "NCT04852770,NCT01086644"})
    ids = sorted(s["protocolSection"]["identificationModule"]["nctId"] for s in result.studies)
    assert ids == ["NCT01030536", "NCT04852770"]
    assert result.csv_text.startswith("NCT Number,")
    assert result.api_version == SPEC_API_VERSION


def test_a_live_pull_writes_a_certified_folder_whose_links_resolve(tmp_path):
    # NCT01827384 has posted results and two posted documents (observed 2026-10-31).
    result = pull({"filter.ids": "NCT01827384,NCT02472444"})
    out = tmp_path / "live"
    write_record(result, out)
    assert verify_folder(out) == ("certified", [])
    rows = list(csv.reader(io.StringIO(result.csv_text, newline="")))
    url_column = rows[0].index("Study URL")
    for row in rows[1:]:
        assert study_link(row[0]) == ("ok", row[url_column])
    saved = json.loads((out / "studies.json").read_text(encoding="utf-8"))
    study = next(
        s for s in saved["studies"] if s["protocolSection"]["identificationModule"]["nctId"] == "NCT01827384"
    )
    doc = study["documentSection"]["largeDocumentModule"]["largeDocs"][0]
    code, url = document_link("NCT01827384", doc["filename"])
    assert code == "ok"
    head = httpx.head(url, follow_redirects=True, timeout=60)
    assert head.status_code == 200 and head.headers["content-type"] == "application/pdf"
