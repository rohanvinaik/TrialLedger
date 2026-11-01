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

from TrialLedger import cli, warrants

PULL_FILES = ("studies.json", "studies.csv", "review.xlsx", "record.xlsx")


def rxclass(url, params):
    # RxNorm and the RxNav release know nothing here, and only DailyMed's EPC answers.
    if not url.endswith("/byDrugName.json") or params.get("relas") != "has_epc":
        return 200, {}
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
        "Review Queue",
        "Near Misses",
        "Drug Axes",
        "Rules",
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
    kept = tmp_path / "snapshot.json"
    code = cli.main(
        [
            "resolve",
            f"filter.ids={','.join(ids)}",
            "--json",
            str(out),
            "--out",
            str(book),
            "--keep",
            str(kept),
        ],
        http=api.client(),
        sleep=api.sleep,
        rxclass_get=rxclass,
    )
    assert code == 0
    reading = json.loads(out.read_text())
    assert [s["nct"] for s in reading["studies"]] == ids
    assert {
        "eligibility_coverage",
        "criteria",
        "coordinates",
        "experimental_drugs",
        "outcomes",
        "expectations",
    } <= set(reading["studies"][0])
    coverage = reading["studies"][0]["eligibility_coverage"]
    assert set(coverage) == {"content", "sectioning", "evidence", "markers"}
    assert set(coverage["evidence"]) == {"inclusion", "exclusion"}
    assert book.is_file() and (tmp_path / "cache" / "classes.json").is_file()
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["cache", "design.xlsx", "reading.json", "snapshot.json"]
    snapshot = json.loads(kept.read_text())
    assert snapshot["study_digests"] == reading["study_digests"] and len(snapshot["studies"]) == 2
    assert reading["merkle_root"] == warrants.merkle_root(reading["study_digests"])
    assert reading["data_timestamp"] and "code_commit" in reading


def test_resolve_refuses_an_empty_query(tmp_path, monkeypatch):
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "classes.json"))
    assert cli.main(["resolve"], rxclass_get=rxclass) == 2


def near_miss_study(nct, ecog):
    study = ongoing_study()
    protocol = study["protocolSection"]
    protocol["identificationModule"]["nctId"] = nct
    protocol["eligibilityModule"]["eligibilityCriteria"] = (
        "Inclusion Criteria:\n\n* Stage IV non-small cell lung cancer\n"
        "* No prior systemic therapy for advanced or metastatic disease\n"
        f"* ECOG performance status {ecog}\n\nExclusion Criteria:\n\n* Active autoimmune disease\n"
    )
    protocol["armsInterventionsModule"] = {
        "armGroups": [{"label": "A", "type": "EXPERIMENTAL", "interventionNames": ["Drug: Pembrolizumab"]}],
        "interventions": [{"type": "DRUG", "name": "Pembrolizumab"}],
    }
    return study


def test_resolve_reports_a_near_miss_in_the_sheet_and_the_json(tmp_path, monkeypatch):
    """Positive: two first-line PD-1 trials differing only in the ECOG they admit are one near-miss row, and
    each study's JSON names the other. Negative: the studies of the other tests, with nothing comparable,
    carry no near miss."""
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "cache" / "classes.json"))
    studies = [near_miss_study("NCT09000001", "0-1"), near_miss_study("NCT09000002", "0-2"), results_study()]
    api = FakeAPI(json_pages=[httpx.Response(200, json={"studies": studies, "totalCount": 3})])
    out, book = tmp_path / "reading.json", tmp_path / "design.xlsx"
    query = "filter.ids=NCT09000001,NCT09000002"
    argv = ["resolve", query, "--json", str(out), "--out", str(book)]
    assert cli.main(argv, http=api.client(), sleep=api.sleep, rxclass_get=rxclass) == 0
    header, *rows = openpyxl.load_workbook(book, read_only=True)["Near Misses"].iter_rows(values_only=True)
    assert header[10].startswith("Representation (known for 2 of 3 trials")
    assert [row[:5] for row in rows] == [("NCT09000001", "NCT09000002", "ecog_ps", "0|1", "0|1|2")]
    header, *trials = openpyxl.load_workbook(book, read_only=True)["Trials"].iter_rows(values_only=True)
    columns = [
        header.index(name) for name in ("Eligibility Content", "Inclusion Coverage", "Exclusion Coverage")
    ]
    assert {tuple(row[i] for i in columns) for row in trials[:2]} == {
        ("present", "unspecified", "unspecified")
    }
    reading = {s["nct"]: s["near_misses"] for s in json.loads(out.read_text())["studies"]}
    assert [(m["other"], m["value"], m["other_value"]) for m in reading["NCT09000002"]] == [
        ("NCT09000001", "0|1|2", "0|1")
    ]
    assert reading[results_study()["protocolSection"]["identificationModule"]["nctId"]] == []


ABBREVIATED = (
    "Inclusion Criteria:\n\n* Stage IV non-small cell lung cancer\n* ECOG performance status 0-1\n\n"
    "Key Exclusion Criteria:\n\n* Active autoimmune disease\n"
)


def test_resolve_carries_an_abbreviated_record_to_the_sheets_and_the_json(tmp_path, monkeypatch):
    """Positive: a record whose exclusions are "Key Exclusion Criteria" shows its sectioning, its coverage per
    section and its marker with the marker's exact offsets on the Trials sheet and in the JSON, and its
    eligibility_abbreviated question on the Review Queue sheet and in the JSON. Negative: a record with no
    marker has no marker, reads unspecified in both sections (never complete) and gets no such question."""
    monkeypatch.setenv("TRIALLEDGER_CACHE", str(tmp_path / "cache" / "classes.json"))
    abbreviated = near_miss_study("NCT09000003", "0-1")
    abbreviated["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = ABBREVIATED
    plain = near_miss_study("NCT09000004", "0-1")
    api = FakeAPI(json_pages=[httpx.Response(200, json={"studies": [abbreviated, plain], "totalCount": 2})])
    out, book = tmp_path / "reading.json", tmp_path / "design.xlsx"
    argv = ["resolve", "filter.ids=NCT09000003,NCT09000004", "--json", str(out), "--out", str(book)]
    assert cli.main(argv, http=api.client(), sleep=api.sleep, rxclass_get=rxclass) == 0
    start = ABBREVIATED.index("Key Exclusion")
    end = start + len("Key Exclusion")

    studies = {s["nct"]: s for s in json.loads(out.read_text())["studies"]}
    coverage = studies["NCT09000003"]["eligibility_coverage"]
    assert (coverage["content"], coverage["sectioning"]) == ("present", "sectioned")
    assert coverage["evidence"] == {"inclusion": "unspecified", "exclusion": "abbreviation_stated"}
    ((marker,),) = [coverage["markers"]]
    assert (marker["kind"], marker["scope"], marker["start"], marker["end"]) == (
        "abbreviation_stated",
        "exclusion",
        start,
        end,
    )
    assert ABBREVIATED[marker["start"] : marker["end"]] == marker["text"] == "Key Exclusion"
    (flag,) = [f for f in studies["NCT09000003"]["review"] if f["kind"] == "eligibility_abbreviated"]
    assert flag["evidence"] == [
        f"[exclusion] piece {marker['piece']}, characters {start}-{end}: Key Exclusion"
    ]
    assert flag["answer"] is None
    assert studies["NCT09000004"]["eligibility_coverage"]["markers"] == []
    assert studies["NCT09000004"]["eligibility_coverage"]["evidence"] == {
        "inclusion": "unspecified",
        "exclusion": "unspecified",
    }
    assert not [f for f in studies["NCT09000004"]["review"] if f["kind"] == "eligibility_abbreviated"]

    workbook = openpyxl.load_workbook(book, read_only=True)
    header, *rows = workbook["Trials"].iter_rows(values_only=True)
    trials = {row[0]: dict(zip(header, row, strict=True)) for row in rows}
    row = trials["NCT09000003"]
    assert (row["Eligibility Content"], row["Sectioning"]) == ("present", "sectioned")
    assert (row["Inclusion Coverage"], row["Exclusion Coverage"]) == ("unspecified", "abbreviation_stated")
    assert row["Coverage Markers"] == (
        f"abbreviation_stated [exclusion] piece {marker['piece']}, characters {start}-{end}: Key Exclusion"
    )
    assert (trials["NCT09000004"]["Exclusion Coverage"], trials["NCT09000004"]["Coverage Markers"]) in {
        ("unspecified", None),
        ("unspecified", ""),
    }
    header, *rows = workbook["Review Queue"].iter_rows(values_only=True)
    queue = [dict(zip(header, row, strict=True)) for row in rows]
    flagged = [(q["NCT Number"], q["Evidence"]) for q in queue if q["Kind"] == "eligibility_abbreviated"]
    assert flagged == [("NCT09000003", flag["evidence"][0])]
