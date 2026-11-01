"""The `trialledger` entry point, end to end against the scripted API.

Positive: a complete pull writes studies.json, studies.csv and a certified review.xlsx and record.xlsx, prints
one summary line and exits 0; `trialledger verify` certifies the folder it wrote (exit 0).
Negative: when the pull fails nothing is written and nothing reaches stdout (exit 1); a refused or
malformed query sends no request at all (exit 2); an existing output directory is never overwritten; a
changed record is not certified (exit 1); a folder that is not a record is refused (exit 2).
"""

import json
import subprocess
from pathlib import Path

import httpx
import pytest
from conftest import FakeAPI, csv_page, json_page, version

from TrialLedger.cli import main

A = "NCT00000001"


def one_study_api():
    return FakeAPI(json_pages=[json_page([A], total=1)], csv_pages=[csv_page([A], total=1, header=True)])


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


def test_an_audit_stops_on_a_snapshot_change_and_only_on_that(tmp_path, monkeypatch, capsys):
    """Positive: the registry changing between the balance check's queries ends the audit with 1, named.
    Negative: any other RuntimeError is not caught as one; it propagates."""
    from TrialLedger import audit
    from TrialLedger.sample import SnapshotChanged

    sample = tmp_path / "sample.json"
    sample.write_text(json.dumps({"seed": "s", "trials": []}), encoding="utf-8")

    def changed(*args, **kwargs):
        raise SnapshotChanged("the registry changed while supplementing: [T1, T2]")

    monkeypatch.setattr(audit, "run_audit", changed)
    assert main(["audit", str(sample), "--out", str(tmp_path / "a")]) == 1
    assert "audit stopped — the registry changed while supplementing" in capsys.readouterr().err

    def broken(*args, **kwargs):
        raise RuntimeError("a fault, not a snapshot change")

    monkeypatch.setattr(audit, "run_audit", broken)
    with pytest.raises(RuntimeError, match="a fault"):
        main(["audit", str(sample), "--out", str(tmp_path / "b")])


def _clean_git(commit="c" * 40, status="", tracked="", calls=None):
    """A fake of the git query: HEAD at `commit`, `status` as the changed paths, `tracked` as the tracked
    files (NUL-separated, read from the package root, so they set the source digest); every call is
    appended to `calls` when given, and a commit succeeds."""
    answers = {"rev-parse": commit + "\n", "status": status, "ls-files": tracked, "commit": ""}

    def git(root, *args):
        if calls is not None:
            calls.append((Path(root), *args))
        return answers[args[0]]

    return git


def _confirmation_inputs(tmp_path, inspected):
    """A kept sample listing `inspected` and an empty ledger of used batches."""
    kept = tmp_path / "discovery_sample.json"
    kept.write_text(json.dumps({"trials": [{"nct": nct} for nct in inspected]}), encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"batches": {}}), encoding="utf-8")
    return kept, ledger


def test_a_confirmation_sample_is_drawn_from_one_named_batch_with_its_code_version(
    tmp_path, monkeypatch, capsys
):
    """add-bank-coverage B8. Positive: `sample --confirmation-batch 1` draws only batch-1 trials and records
    the batch, the code's commit and source digest in sample.json; without it the sample is the discovery
    draw, as before. Negative: a batch outside 0, 1, 2, or a code version git cannot name, is refused (2)
    before any registry query, and nothing is written."""
    from TrialLedger import cli, ingest
    from TrialLedger.sample import pool

    ids = [f"NCT{n:08d}" for n in range(1, 201)]
    asked = []

    def query_ids(query, **kwargs):
        asked.append(query)
        return ids, "2.0.5", "T"

    monkeypatch.setattr(ingest, "query_ids", query_ids)
    monkeypatch.setattr(cli, "code_commit", lambda: "d" * 40)
    kept, ledger = _confirmation_inputs(tmp_path, ["NCT00000001"])
    batch = ["--inspected", str(kept), "--confirmation-batch"]
    out = tmp_path / "confirmation.json"
    argv = ["sample", "--seed", "s", "--per-stratum", "2", "--out", str(out), *batch, "1"]
    assert main(argv, git=_clean_git(), ledger=ledger) == 0
    sample = json.loads(out.read_text(encoding="utf-8"))
    assert sample["batch_ledger"] == str(ledger)
    assert sample["confirmation_batch"] == 1 and sample["drawn_from"] == "confirmation_1"
    assert sample["code_commit"] == "c" * 40 and sample["balance"]["supplement_per_cell"] == 0
    assert len(sample["code_source_digest"]) == 64 and sample["code_watched"] == ["TrialLedger", "tests"]
    assert sample["trials"] and all(pool(t["nct"]) == "confirmation_1" for t in sample["trials"])
    assert "from the confirmation_1 pool" in capsys.readouterr().out
    plain = tmp_path / "discovery.json"
    assert main(["sample", "--seed", "s", "--per-stratum", "2", "--out", str(plain)]) == 0
    discovery = json.loads(plain.read_text(encoding="utf-8"))
    assert discovery["confirmation_batch"] is None and discovery["drawn_from"] == "discovery"
    assert discovery["code_commit"] == "d" * 40 and "inspected" not in discovery
    assert all(pool(t["nct"]) == "discovery" for t in discovery["trials"])

    asked.clear()
    capsys.readouterr()
    refused = tmp_path / "refused.json"
    argv = ["sample", "--seed", "s", "--out", str(refused), *batch]
    assert main([*argv, "3"], git=_clean_git(), ledger=ledger) == 2
    assert "refused (confirmation.unknown_batch): batch 3" in capsys.readouterr().err
    assert main([*argv, "0"], git=_clean_git(commit=""), ledger=ledger) == 2
    assert "refused (confirmation.no_code_version)" in capsys.readouterr().err
    assert not asked and not refused.exists()


def test_a_confirmation_sample_excludes_every_inspected_trial_and_keeps_the_lists(tmp_path, monkeypatch):
    """Decision 9, B4. Positive: the trials of a kept sample and of a record folder are never drawn; each list
    is kept in sample.json with its file, its digest and its IDs, and the exclusions are counted. Negative: a
    draw with no inspected list, or with one that lists nothing, is refused and writes nothing."""
    from TrialLedger import ingest
    from TrialLedger.sample import pool

    ids = [f"NCT{n:08d}" for n in range(1, 201)]
    monkeypatch.setattr(ingest, "query_ids", lambda query, **kwargs: (ids, "2.0.5", "T"))
    batch1 = sorted(nct for nct in ids if pool(nct) == "confirmation_1")
    kept, ledger = _confirmation_inputs(tmp_path, batch1[:10])
    folder = tmp_path / "nsclc"
    folder.mkdir()
    studies = [{"protocolSection": {"identificationModule": {"nctId": nct}}} for nct in batch1[10:14]]
    (folder / "studies.json").write_text(json.dumps({"studies": studies}), encoding="utf-8")
    out = tmp_path / "confirmation.json"
    base = ["sample", "--seed", "s", "--per-stratum", "50", "--out", str(out)]
    inspected = ["--inspected", str(kept), "--inspected", str(folder)]
    assert main([*base, *inspected, "--confirmation-batch", "1"], git=_clean_git(), ledger=ledger) == 0
    sample = json.loads(out.read_text(encoding="utf-8"))
    assert {t["nct"] for t in sample["trials"]} == set(batch1[14:])
    assert sample["inspected_excluded"] == 14
    assert [item["ncts"] for item in sample["inspected"]] == [batch1[:10], batch1[10:14]]
    assert sample["inspected"][1]["path"] == str(folder / "studies.json")
    assert all(len(item["sha256"]) == 64 for item in sample["inspected"])

    out.unlink()
    assert main([*base, "--confirmation-batch", "1"], git=_clean_git(), ledger=ledger) == 2
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    assert (
        main([*base, "--inspected", str(empty), "--confirmation-batch", "1"], git=_clean_git(), ledger=ledger)
        == 2
    )
    missing = ["--inspected", str(tmp_path / "missing.json")]
    assert main([*base, *missing, "--confirmation-batch", "1"], git=_clean_git(), ledger=ledger) == 2
    assert not out.exists()


def test_a_confirmation_draw_needs_clean_code_and_retires_its_batch_in_the_ledger(
    tmp_path, monkeypatch, capsys
):
    """add-bank-coverage B8. Positive: a draw records its batch in the declared ledger with the code's
    source digest and commit, and commits the ledger alone; a re-draw of the same batch for the same code is
    allowed, even at a new commit (the ledger's own), and neither rewrites nor commits the ledger. Negative:
    uncommitted changes under TrialLedger/ or tests/, a batch the ledger gives other code, and a missing or
    malformed ledger are each refused, writing no sample and leaving the ledger byte for byte; a ledger that
    cannot be committed is named and ends with 1. No option names another ledger."""
    from TrialLedger import ingest
    from TrialLedger.sample import code_state

    ids = [f"NCT{n:08d}" for n in range(1, 201)]
    monkeypatch.setattr(ingest, "query_ids", lambda query, **kwargs: (ids, "2.0.5", "T"))
    kept, ledger = _confirmation_inputs(tmp_path, ["NCT00000001"])
    out = tmp_path / "confirmation.json"
    argv = ["sample", "--seed", "s", "--out", str(out), "--inspected", str(kept), "--confirmation-batch", "2"]
    calls = []
    assert main(argv, git=_clean_git(calls=calls), ledger=ledger) == 0
    digest = code_state(git=_clean_git())["source_digest"]
    entry = {"source_digest": digest, "commit": "c" * 40}
    assert json.loads(ledger.read_text(encoding="utf-8")) == {"batches": {"2": entry}}
    committed = [call for call in calls if call[1] == "commit"]
    assert len(committed) == 1 and committed[0][0] == tmp_path and committed[0][-2:] == ("--", ledger.name)
    assert "Confirmation batch 2 used for code cccccccccccc" in committed[0][3]
    written = ledger.read_bytes()
    calls.clear()
    assert main(argv, git=_clean_git(commit="f" * 40, calls=calls), ledger=ledger) == 0
    assert ledger.read_bytes() == written and not [call for call in calls if call[1] == "commit"]

    out.unlink()
    capsys.readouterr()
    assert main(argv, git=_clean_git(status=" M TrialLedger/banks.py\n"), ledger=ledger) == 2
    assert "confirmation.uncommitted_changes" in capsys.readouterr().err
    other_code = _clean_git(commit="e" * 40, tracked="pyproject.toml\0")
    assert main(argv, git=other_code, ledger=ledger) == 2
    assert "confirmation.batch_used" in capsys.readouterr().err
    assert ledger.read_bytes() == written
    assert main(argv, git=_clean_git(), ledger=tmp_path / "none.json") == 2
    ledger.write_text(json.dumps({"batches": {"5": entry}}), encoding="utf-8")
    assert main(argv, git=_clean_git(), ledger=ledger) == 2
    assert "confirmation.ledger_unreadable" in capsys.readouterr().err
    assert not out.exists()
    with pytest.raises(SystemExit):
        main([*argv, "--batch-ledger", str(ledger)], git=_clean_git(), ledger=ledger)

    ledger.write_text(json.dumps({"batches": {}}), encoding="utf-8")
    failing = _clean_git()

    def no_commit(root, *args):
        if args[0] == "commit":
            raise subprocess.CalledProcessError(1, ["git", "commit"])
        return failing(root, *args)

    capsys.readouterr()
    assert main(argv, git=no_commit, ledger=ledger) == 1
    assert "but the ledger was not committed" in capsys.readouterr().err
    assert out.exists() and json.loads(ledger.read_text(encoding="utf-8"))["batches"]["2"] == entry


def test_a_sample_frame_runs_to_the_present_and_records_it(tmp_path, monkeypatch, capsys):
    """add-bank-coverage B1 (2010 to the present). Positive: `sample` ends start dates at today's UTC date by
    default, or at --present, and sample.json records it with the base filter. Negative: a present that is not
    a calendar date, or lies before 2010-01-01, is refused (2) before any registry query, and nothing is
    written."""
    from datetime import UTC, datetime

    from TrialLedger import ingest

    asked = []

    def query_ids(query, **kwargs):
        asked.append(query["filter.advanced"])
        return [], "2.0.5", "T"

    monkeypatch.setattr(ingest, "query_ids", query_ids)
    out = tmp_path / "sample.json"
    assert main(["sample", "--seed", "s", "--out", str(out), "--present", "2026-10-15"]) == 0
    sample = json.loads(out.read_text(encoding="utf-8"))
    assert sample["present"] == "2026-10-15" and sample["base"].endswith("RANGE[2010-01-01,2026-10-15]")
    assert asked and all("RANGE[2010-01-01,2026-10-15]" in q for q in asked)
    today = tmp_path / "today.json"
    assert main(["sample", "--seed", "s", "--out", str(today)]) == 0
    assert json.loads(today.read_text(encoding="utf-8"))["present"] == datetime.now(UTC).date().isoformat()

    asked.clear()
    capsys.readouterr()
    refused = tmp_path / "refused.json"
    for bad in ("2026-13-01", "26-11-01", "2026-11-1", "2009-12-31", "now"):
        assert main(["sample", "--seed", "s", "--out", str(refused), "--present", bad]) == 2
        assert f"refused (sample.present): {bad}" in capsys.readouterr().err
    assert not asked and not refused.exists()
