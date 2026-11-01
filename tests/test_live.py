"""Against the real ClinicalTrials.gov API. Opt-in: `uv run pytest -m live`."""

import csv
import io
import json

import httpx
import pytest

from TrialLedger import classes as rx
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


def test_every_verified_query_form_still_returns_trials():
    """Each form in sample.VERIFIED_FORMS, asked as recorded in tests/live_query_forms.json (countTotal, one
    ID per page), still returns trials; a recount is not expected to equal the recorded one."""
    import time
    from pathlib import Path

    from TrialLedger.ingest import API_BASE
    from TrialLedger.sample import VERIFIED_FORMS

    fixture = json.loads((Path(__file__).parent / "live_query_forms.json").read_text(encoding="utf-8"))
    for form in VERIFIED_FORMS:
        params = {"filter.advanced": fixture["forms"][form]["query"], "countTotal": "true", "pageSize": "1"}
        response = httpx.get(f"{API_BASE}/studies", params=params | {"fields": "NCTId"}, timeout=60)
        assert response.status_code == 200 and response.json()["totalCount"] > 0
        time.sleep(1.5)


def test_rxnav_resolves_identity_before_a_class_is_attributed():
    """Against RxNav (observed 2026-10-31 and 2026-11-01): gefitinib is its own ingredient and its ATC class
    L01EB is known; Keytruda is a brand that RxClass answers as pembrolizumab, so L01FF is not inherited."""
    answers = {
        name: {"axes": axes}
        for name, axes in rx.lookup_axes(["gefitinib", "Keytruda"], get=rx.http_get).items()
    }
    _, _, _, gefitinib = rx.drug_axes(["gefitinib"], answers)
    assert ("ATC", "L01EB", "known") in {(a[1], a[2], a[5]) for a in gefitinib}
    _, _, identities, keytruda = rx.drug_axes(["Keytruda"], answers)
    assert identities[0][1] == "brand"
    assert ("ATC", "L01FF", "not_inherited") in {(a[1], a[2], a[5]) for a in keytruda}
