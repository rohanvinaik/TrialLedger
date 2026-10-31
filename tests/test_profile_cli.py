"""`trialledger profile` and `trialledger resolve` end to end, through the CLI.

Positive: a written folder gets design.xlsx and classes.json, with every sheet the About sheet describes; the
pull's own four files are byte for byte unchanged and the folder still verifies.
Negative: a record that no longer matches its digests gets no design.xlsx (exit 1); a folder with no record
gets nothing (exit 2).
"""

import json

import httpx
import openpyxl
import pytest
from conftest import FakeAPI, csv_page
from records import ongoing_study, results_study

from TrialLedger import cli

PULL_FILES = ("studies.json", "studies.csv", "review.xlsx", "record.xlsx")


def rxclass(_url, params):
    if params["relaSource"] == "DAILYMED":
        item = {"classId": "N0000191260", "className": "Programmed Death Receptor-1 Blocking Antibody"}
        entry = {"rxclassMinConceptItem": item, "rela": "has_epc", "relaSource": "DAILYMED"}
        return 200, {"rxclassDrugInfoList": {"rxclassDrugInfo": [entry]}}
    return 200, {}


@pytest.fixture
def folder(tmp_path):
    first, second = results_study(), ongoing_study()
    ids = [study["protocolSection"]["identificationModule"]["nctId"] for study in (first, second)]
    api = FakeAPI(
        json_pages=[httpx.Response(200, json={"studies": [first, second], "totalCount": 2})],
        csv_pages=[csv_page(ids, total=2, header=True)],
    )
    out = tmp_path / "run"
    assert (
        cli.main(
            ["pull", f"filter.ids={','.join(ids)}", "--out", str(out)], http=api.client(), sleep=api.sleep
        )
        == 0
    )
    return out


def test_profile_writes_beside_the_pull_and_changes_none_of_it(folder):
    before = {name: (folder / name).read_bytes() for name in PULL_FILES}
    assert cli.main(["profile", str(folder)], rxclass_get=rxclass) == 0
    assert {name: (folder / name).read_bytes() for name in PULL_FILES} == before
    assert cli.main(["verify", str(folder)]) == 0
    book = openpyxl.load_workbook(folder / "design.xlsx", read_only=True)
    assert book.sheetnames == [
        "About",
        "Trials",
        "Criteria",
        "Residual",
        "Audit",
        "Coordinates",
        "Outcomes",
        "Results",
        "Expectations",
        "Relations",
        "Classes",
        "Profile",
        "Mechanism Signals",
        "Occupancy",
    ]
    cache = json.loads((folder / "classes.json").read_text())
    assert cache["endpoint"].startswith("https://rxnav.nlm.nih.gov/")


def test_a_tampered_record_gets_no_design(folder):
    record = json.loads((folder / "studies.json").read_text())
    record["studies"][0]["protocolSection"]["identificationModule"]["briefTitle"] = "changed"
    (folder / "studies.json").write_text(json.dumps(record))
    assert cli.main(["profile", str(folder)], rxclass_get=rxclass) == 1
    assert not (folder / "design.xlsx").exists()


def test_a_folder_without_a_record_gets_nothing(tmp_path):
    assert cli.main(["profile", str(tmp_path)], rxclass_get=rxclass) == 2
    assert list(tmp_path.iterdir()) == []


def test_resolve_reads_live_and_saves_no_record(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "cache" / "classes.json"))
    first, second = results_study(), ongoing_study()
    ids = [study["protocolSection"]["identificationModule"]["nctId"] for study in (first, second)]
    api = FakeAPI(json_pages=[httpx.Response(200, json={"studies": [first, second], "totalCount": 2})])
    out = tmp_path / "reading.json"
    book = tmp_path / "design.xlsx"
    code = cli.main(
        ["resolve", f"filter.ids={','.join(ids)}", "--json", str(out), "--out", str(book)],
        http=api.client(),
        sleep=api.sleep,
        rxclass_get=rxclass,
    )
    assert code == 0
    reading = json.loads(out.read_text())
    assert [s["nct"] for s in reading["studies"]] == ids
    assert {"criteria", "coordinates", "experimental_drugs", "outcomes", "expectations"} <= set(
        reading["studies"][0]
    )
    assert book.is_file() and (tmp_path / "cache" / "classes.json").is_file()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["cache", "design.xlsx", "reading.json"]


def test_resolve_refuses_an_empty_query(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "classes.json"))
    assert cli.main(["resolve"], rxclass_get=rxclass) == 2
