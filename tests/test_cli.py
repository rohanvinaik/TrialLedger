"""The `trialledger` entry point, end to end against the scripted API.

Positive: a complete pull writes studies.json, studies.csv and a certified review.xlsx and record.xlsx, prints
one summary line and exits 0; `trialledger verify` certifies the folder it wrote (exit 0).
Negative: when the pull fails nothing is written and nothing reaches stdout (exit 1); a refused or
malformed query sends no request at all (exit 2); an existing output directory is never overwritten; a
changed record is not certified (exit 1); a folder that is not a record is refused (exit 2).
"""

import json

import httpx
from conftest import FakeAPI, csv_page, json_page, version

from TrialLedger.cli import main

A = "NCT00000001"


def one_study_api():
    return FakeAPI(
        json_pages=[json_page([A], total=1), json_page([A], total=1)],
        csv_pages=[csv_page([A], total=1, header=True)],
    )


def test_pull_writes_the_folder_and_reports(tmp_path, capsys):
    out = tmp_path / "run"
    code = main(
        ["pull", f"filter.ids={A}", "--out", str(out)], http=one_study_api().client(), sleep=lambda s: None
    )
    stdout = capsys.readouterr().out
    assert code == 0
    assert sorted(p.name for p in out.iterdir()) == [
        "record.xlsx",
        "review.xlsx",
        "studies.csv",
        "studies.json",
    ]
    record = json.loads((out / "studies.json").read_text(encoding="utf-8"))
    assert [s["protocolSection"]["identificationModule"]["nctId"] for s in record["studies"]] == [A]
    assert stdout.startswith("1 studies written to ")
    assert "(studies.json, studies.csv, review.xlsx, record.xlsx, certified)" in stdout
    assert "data as of 2026-10-30T09:00:04" in stdout


def test_verify_certifies_what_pull_wrote(tmp_path, capsys):
    out = tmp_path / "run"
    main(["pull", f"filter.ids={A}", "--out", str(out)], http=one_study_api().client(), sleep=lambda s: None)
    capsys.readouterr()
    assert main(["verify", str(out)]) == 0
    assert "certified" in capsys.readouterr().out


def test_verify_refuses_a_changed_record(tmp_path, capsys):
    out = tmp_path / "run"
    main(["pull", f"filter.ids={A}", "--out", str(out)], http=one_study_api().client(), sleep=lambda s: None)
    saved = json.loads((out / "studies.json").read_text(encoding="utf-8"))
    saved["studies"][0]["protocolSection"]["identificationModule"]["briefTitle"] = "Changed"
    (out / "studies.json").write_text(json.dumps(saved), encoding="utf-8")
    capsys.readouterr()
    assert main(["verify", str(out)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "NOT certified" in captured.err and "record.study_digest" in captured.err


def test_verify_refuses_a_folder_that_is_not_a_record(tmp_path, capsys):
    assert main(["verify", str(tmp_path)]) == 2
    assert "not a TrialLedger record" in capsys.readouterr().err


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
        json_pages=[json_page([A], total=1), json_page([A], total=1)],
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
    err = capsys.readouterr().err
    assert "the registry reports its interface version 2.1.0" in err
    assert "spec/ctg-oas-v2.yaml" not in err


def test_a_pull_says_what_became_of_each_number_in_plain_words(tmp_path, capsys):
    """The release check (2026-11-01). Positive: an alias reads "<number> is another number of <trial>", a
    number no trial holds says so. Negative: a status is never printed as its code ("aliased"), and a number
    found under its own number is not printed."""
    aliased = {
        "protocolSection": {"identificationModule": {"nctId": A, "nctIdAliases": ["NCT01086644"]}},
    }
    fake = FakeAPI(
        json_pages=[
            json_page([A], total=1),
            httpx.Response(200, json={"studies": [aliased], "totalCount": 1}),
        ],
        csv_pages=[csv_page([A], total=1, header=True)],
    )
    argv = ["pull", f"filter.ids=NCT01086644,{A},NCT09999999", "--out", str(tmp_path / "run")]
    assert main(argv, http=fake.client(), sleep=lambda s: None) == 0
    err = capsys.readouterr().err
    assert f"trialledger: NCT01086644 is another number of {A}: the registry gave that trial's record" in err
    assert "trialledger: NCT09999999: no trial in the registry has this number" in err
    assert "aliased" not in err and f"trialledger: {A}:" not in err
