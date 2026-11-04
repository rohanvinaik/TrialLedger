"""One selector, two transports: exact saved evidence, named refusals and lossless continuation."""

import json

import pytest
from conftest import FakeAPI, csv_page, json_page

from TrialLedger import cli, evidence_access, mcp_server
from TrialLedger.cli import main
from TrialLedger.evidence_access import page_window, pointer_value, read_record
from TrialLedger.mcp_server import Context, call_tool

A = "NCT00000001"


def saved(folder, text="Exact source text"):
    folder.mkdir()
    record = {
        "schema_version": 4,
        "studies": [{"nct": A, "brief_title": "Invented transport fixture", "eligibility": {"text": text}}],
        "fields": [{"name": "text", "source": "retained fixture"}],
        "request": {"condition": "invented fixture"},
        "scope": {},
        "manifest": {},
        "statuses": {},
        "escaped/key~": {"zero": 0, "false": False, "null": None},
    }
    (folder / "landscape.json").write_text(json.dumps(record))
    return record


def invoke(folder, arguments, capsys):
    argv = ["record", str(folder)]
    for key, value in arguments.items():
        argv += ["--" + key.replace("_", "-"), str(value)]
    code = main(argv)
    cli_result = json.loads(capsys.readouterr().out)
    status, payload = call_tool(
        Context(folder.parent), {"name": "record", "arguments": {"run": folder.name, **arguments}}
    )
    assert status == "ok"
    mcp_result = json.loads(payload["content"][0]["text"])
    assert cli_result == mcp_result
    assert code == (2 if payload["isError"] else 0)
    return cli_result


@pytest.mark.parametrize(
    "arguments",
    [
        {"part": "studies", "limit": 1},
        {"part": "study", "nct": A},
        {"part": "fields"},
        {"part": "manifest"},
        {"part": "statuses"},
        {"part": "address", "address": "/escaped~1key~0/zero"},
        {"part": "address", "address": "/escaped~1key~0/false"},
        {"part": "address", "address": "/escaped~1key~0/null"},
        {"part": "address", "address": "not-a-pointer"},
        {"part": "address", "address": "/studies/01"},
        {"part": "studies", "offset": -1},
        {"part": "studies", "limit": 0},
        {"part": "studies", "max_bytes": 2047},
        {"part": "address", "address": "/studies", "text_offset": 1},
    ],
)
def test_cli_and_mcp_record_share_complete_parsed_reply(tmp_path, capsys, arguments):
    folder = tmp_path / "run"
    saved(folder)
    invoke(folder, arguments, capsys)


def test_default_cli_record_is_the_study_index_without_network(tmp_path, capsys):
    folder = tmp_path / "run"
    saved(folder)
    fake = FakeAPI()
    assert main(["record", str(folder)], http=fake.client()) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["part"] == "studies"
    assert result["studies"][0]["nct"] == A
    assert fake.requests == []


def test_text_chunks_reconstruct_all_characters_and_do_not_rewrite_source(tmp_path, capsys):
    text = "αβ\nExact\tWHO ≠ ECOG\r\n" * 800
    folder = tmp_path / "run"
    saved(folder, text)
    before = (folder / "landscape.json").read_bytes()
    offset = 0
    chunks = []
    while True:
        result = invoke(
            folder,
            {
                "part": "address",
                "address": "/studies/0/eligibility/text",
                "text_offset": offset,
                "text_limit": 1000,
                "max_bytes": 4096,
            },
            capsys,
        )
        assert result["text_page"]["offset"] == offset
        chunks.append(result["text"])
        offset = result["text_page"]["next_offset"]
        if offset is None:
            break
    assert "".join(chunks) == text
    assert len(chunks) > 1
    assert (folder / "landscape.json").read_bytes() == before


def test_large_nested_value_returns_navigation_and_exact_child_address(tmp_path, capsys):
    folder = tmp_path / "run"
    saved(folder, "long-source-" * 2000)
    result = invoke(folder, {"part": "study", "nct": A, "max_bytes": 2048}, capsys)
    assert result["navigation"] == "addresses"
    entry = next(x for x in result["entries"] if x["key"] == "eligibility")
    assert entry["address"] == "/studies/0/eligibility"
    child = invoke(folder, {"part": "address", "address": entry["address"], "max_bytes": 2048}, capsys)
    assert child["navigation"] == "addresses"
    assert child["entries"][0]["address"] == "/studies/0/eligibility/text"


def test_missing_and_malformed_records_are_named_not_empty_success(tmp_path, capsys):
    folder = tmp_path / "run"
    folder.mkdir()
    assert invoke(folder, {"part": "studies"}, capsys)["error"] == "no_record"
    (folder / "landscape.json").write_text('{"broken":')
    assert invoke(folder, {"part": "studies"}, capsys)["error"] == "not_a_record"


def test_mcp_helpers_are_reexports_of_shared_selector_not_parallel_implementations():
    assert mcp_server.record_view is evidence_access.record_view
    assert mcp_server.pointer_value is evidence_access.pointer_value
    assert mcp_server.page_window is evidence_access.page_window
    assert mcp_server.study_line is evidence_access.study_line


def test_direct_selector_keeps_exact_empty_false_and_zero_values():
    assert pointer_value({"x": 0}, "/x") == ("ok", 0)
    assert pointer_value({"x": False}, "/x") == ("ok", False)
    assert pointer_value({"x": []}, "/x") == ("ok", [])
    assert pointer_value({"x": None}, "/x") == ("ok", None)
    assert pointer_value({"x": 0}, "/x/y") == ("outside_record", None)
    assert page_window(0, 0, 1) == (
        "ok",
        {"offset": 0, "limit": 1, "returned": 0, "total": 0, "next_offset": None},
    )
    assert page_window(1, 1, 1) == ("offset_out_of_range", {})


def test_shared_read_owner_does_not_certify_missing_record(tmp_path):
    result, is_error = read_record(tmp_path, {"part": "studies"})
    assert is_error is True
    assert result["error"] == "no_record"


@pytest.mark.parametrize("flag,value", [("--max-studies", "0"), ("--max-registry-requests", "-1")])
def test_raw_cli_budget_flags_refuse_before_http(capsys, flag, value):
    fake = FakeAPI()
    assert main(["pull", "query.cond=asthma", flag, value], http=fake.client()) == 2
    assert fake.requests == []
    captured = capsys.readouterr()
    assert "acquisition.invalid_" in captured.err and captured.out == ""


def test_raw_cli_explicit_budget_is_passed_to_shared_raw_owner(tmp_path, monkeypatch, capsys):
    actual = cli.pull
    received = []

    def watched(query, **kwargs):
        received.append(kwargs["acquisition"])
        return actual(query, **kwargs)

    monkeypatch.setattr(cli, "pull", watched)
    fake = FakeAPI(
        json_pages=[json_page([A], total=1), json_page([A], total=1)],
        csv_pages=[csv_page([A], total=1, header=True)],
    )
    assert (
        main(
            [
                "pull",
                "query.cond=asthma",
                "--max-studies",
                "1",
                "--max-registry-requests",
                "5",
                "--out",
                str(tmp_path / "out"),
            ],
            http=fake.client(),
            sleep=lambda _: None,
        )
        == 0
    )
    assert received == [{"max_studies": 1, "max_registry_requests": 5}]
    assert len(fake.requests) == 5
    assert "1 studies written" in capsys.readouterr().out


def test_verified_legacy_format_details_remain_visible_on_success(tmp_path, monkeypatch, capsys):
    from TrialLedger import landscape_verify

    (tmp_path / "landscape.json").write_text("{}")
    monkeypatch.setattr(
        landscape_verify,
        "verify_landscape",
        lambda _: ("verified", ["legacy_format: source context absent in writing version"]),
    )
    assert main(["verify", str(tmp_path)]) == 0
    stdout = capsys.readouterr().out
    assert "verified" in stdout
    assert "legacy_format: source context absent in writing version" in stdout
