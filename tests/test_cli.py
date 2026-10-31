"""The `trialledger pull` entry point, end to end against the scripted API.

Positive: a complete pull writes studies.json and studies.csv, prints one summary line and exits 0.
Negative: when the pull fails nothing is written and nothing reaches stdout (exit 1); a refused or
malformed query sends no request at all (exit 2); an existing output directory is never overwritten.
"""

import json

import httpx
from conftest import FakeAPI, csv_page, json_page, version

from TrialLedger.cli import main

A = "NCT00000001"


def one_study_api():
    return FakeAPI(json_pages=[json_page([A], total=1)], csv_pages=[csv_page([A], total=1, header=True)])


def test_pull_writes_both_files_and_reports(tmp_path, capsys):
    out = tmp_path / "run"
    code = main(
        ["pull", f"filter.ids={A}", "--out", str(out)], http=one_study_api().client(), sleep=lambda s: None
    )
    stdout = capsys.readouterr().out
    assert code == 0
    assert sorted(p.name for p in out.iterdir()) == ["studies.csv", "studies.json"]
    record = json.loads((out / "studies.json").read_text(encoding="utf-8"))
    assert [s["protocolSection"]["identificationModule"]["nctId"] for s in record["studies"]] == [A]
    assert stdout.startswith("1 studies written to ")
    assert "data as of 2026-10-30T09:00:04" in stdout


def test_default_directory_is_named_by_retrieval_time(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["pull", f"filter.ids={A}"], http=one_study_api().client(), sleep=lambda s: None) == 0
    (made,) = tmp_path.iterdir()
    assert made.name.startswith("trialledger_") and made.name.endswith("Z")


def test_failed_pull_writes_nothing_and_prints_nothing(tmp_path, capsys):
    fake = FakeAPI(json_pages=[httpx.Response(503)] * 4)
    out = tmp_path / "run"
    code = main(["pull", f"filter.ids={A}", "--out", str(out)], http=fake.client(), sleep=lambda s: None)
    captured = capsys.readouterr()
    assert code == 1
    assert not out.exists() and list(tmp_path.iterdir()) == []
    assert captured.out == ""
    assert "nothing written" in captured.err and "http.server_error" in captured.err


def test_refused_query_sends_nothing(capsys):
    fake = FakeAPI()
    code = main(["pull", f"query.term={A}", "filter.overallStatus=RECRUITING"], http=fake.client())
    assert code == 2
    assert fake.requests == []
    assert "filters_ignored" in capsys.readouterr().err


def test_malformed_word_is_refused(capsys):
    fake = FakeAPI()
    assert main(["pull", "asthma"], http=fake.client()) == 2
    assert fake.requests == []
    assert "not_name_value" in capsys.readouterr().err


def test_empty_query_is_refused(capsys):
    fake = FakeAPI()
    assert main(["pull"], http=fake.client()) == 2
    assert fake.requests == []
    assert "no_parameters" in capsys.readouterr().err


def test_existing_output_directory_is_kept(tmp_path, capsys):
    out = tmp_path / "run"
    out.mkdir()
    code = main(
        ["pull", f"filter.ids={A}", "--out", str(out)], http=one_study_api().client(), sleep=lambda s: None
    )
    captured = capsys.readouterr()
    assert code == 1
    assert list(out.iterdir()) == []
    assert captured.out == "" and "already exists" in captured.err


def test_api_version_drift_is_reported(tmp_path, capsys):
    fake = FakeAPI(
        versions=[version(api_version="2.1.0"), version(api_version="2.1.0")],
        json_pages=[json_page([A], total=1)],
        csv_pages=[csv_page([A], total=1, header=True)],
    )
    assert (
        main(
            ["pull", f"filter.ids={A}", "--out", str(tmp_path / "run")],
            http=fake.client(),
            sleep=lambda s: None,
        )
        == 0
    )
    assert "the API reports version 2.1.0" in capsys.readouterr().err
