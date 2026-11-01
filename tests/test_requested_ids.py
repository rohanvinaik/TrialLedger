"""Requested-ID reconciliation: what became of each NCT number a `filter.ids` pull asked for.

The registry matches a requested number against each study's own number and its aliases and answers with
the study under its own number, so a pull can return fewer studies than were asked for, or other numbers,
silently.
Positive: every requested token is accounted for, in order, as found, aliased (naming the study that
answered), missing, duplicate or malformed; lower case and short forms are read as the API reads them; the
accounting is carried into the pull, the record's provenance and its About sheet, and the record still
certifies.
Negative: no token is dropped, no alias is reported as found, no repeat is counted twice, and a token the API
would not accept is never canonicalized.
"""

import json

from conftest import csv_page, json_page
from openpyxl import load_workbook
from test_pull import A, B, run, two_page_api

from TrialLedger.ingest import reconcile_ids
from TrialLedger.record import JSON_NAME, verify_folder, write_record
from TrialLedger.workbook import RECORD_NAME


def study(nct_id, aliases=()):
    identification = {"nctId": nct_id}
    if aliases:
        identification["nctIdAliases"] = list(aliases)
    return {"protocolSection": {"identificationModule": identification}}


def test_each_requested_number_is_accounted_for_in_order():
    studies = [study("NCT01030536", ["NCT01086644"]), study("NCT04852770")]
    assert reconcile_ids("NCT04852770, nct1086644|NCT09999999 NCT4852770,NCT12x", studies) == [
        {"requested": "NCT04852770", "id": "NCT04852770", "status": "found", "study": "NCT04852770"},
        {"requested": "nct1086644", "id": "NCT01086644", "status": "aliased", "study": "NCT01030536"},
        {"requested": "NCT09999999", "id": "NCT09999999", "status": "missing", "study": ""},
        {"requested": "NCT4852770", "id": "NCT04852770", "status": "duplicate", "study": ""},
        {"requested": "NCT12x", "id": "", "status": "malformed", "study": ""},
    ]


def test_a_number_the_api_would_not_accept_is_malformed():
    for token in ("NCT0", "NCT123456789", "12345678", "NCT-1"):
        assert reconcile_ids(token, [])[0]["status"] == "malformed", token


def test_an_own_number_wins_over_another_study_alias():
    studies = [study("NCT00000002", ["NCT00000001"]), study("NCT00000001")]
    assert reconcile_ids("NCT00000001", studies)[0]["status"] == "found"


def test_an_empty_list_has_nothing_to_account_for():
    assert reconcile_ids(" , |", [study("NCT00000001")]) == []


def test_a_pull_by_ids_carries_the_accounting(no_clock):
    fake = two_page_api(
        json_pages=[json_page([A, B], total=2)], csv_pages=[csv_page([A, B], total=2, header=True)]
    )
    result = run(fake, no_clock, {"filter.ids": f"{A}|nct2,NCT00000009"})
    assert [(e["requested"], e["status"]) for e in result.requested_ids] == [
        (A, "found"),
        ("nct2", "found"),
        ("NCT00000009", "missing"),
    ]


def test_a_pull_by_search_carries_none(no_clock):
    assert run(two_page_api(), no_clock).requested_ids == []


def test_the_record_keeps_the_accounting_and_still_certifies(no_clock, tmp_path):
    fake = two_page_api(
        json_pages=[json_page([A, B], total=2)], csv_pages=[csv_page([A, B], total=2, header=True)]
    )
    result = run(fake, no_clock, {"filter.ids": f"{A},{B},NCT00000009"})
    out = tmp_path / "record"
    write_record(result, out)
    record = json.loads((out / JSON_NAME).read_text(encoding="utf-8"))
    assert record["provenance"]["requested_ids"][2]["status"] == "missing"
    assert verify_folder(out) == ("certified", [])
    about = load_workbook(out / RECORD_NAME, read_only=True).worksheets[0]
    rows = [tuple(row[:3]) for row in about.iter_rows(values_only=True)]
    assert ("requested id", "NCT00000009", "missing") in rows
