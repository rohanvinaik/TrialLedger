"""Class navigation stays unresolved until an explicit choice, through CLI and MCP alike."""

import json

from TrialLedger.cli import main
from TrialLedger.mcp_server import Context, call_tool

NAME = "EGFR tyrosine kinase inhibitors"
CANONICAL = "Epidermal growth factor receptor (EGFR) tyrosine kinase inhibitors"


def catalogue(url, params):
    if url.endswith("/version.json"):
        return 200, {"version": "test-release"}
    if url.endswith("/class/byName.json"):
        return 200, {}
    if url.endswith("/allClasses.json"):
        return 200, {
            "rxclassMinConceptList": {
                "rxclassMinConcept": [
                    {"classId": "L01EB", "className": CANONICAL, "classType": "ATC1-4"},
                ]
            }
        }
    raise AssertionError(f"No member expansion or registry retrieval before selection: {url}")


def test_cli_offers_id_choice_without_gathering_or_fixing_a_search(tmp_path, capsys):
    folder = tmp_path / "choice"
    code = main(
        [
            "landscape",
            "--run",
            str(folder),
            "--mode",
            "direct",
            "--preview",
            "--drug-class",
            NAME,
            "--class-source",
            "ATC",
        ],
        rxclass_get=catalogue,
        sleep=lambda _: None,
    )
    assert code == 2
    words = capsys.readouterr().err
    assert "L01EB" in words and CANONICAL in words
    assert "--drug-class-id" in words and "--class-source" in words
    assert not (folder / "scope.json").exists()
    assert not (folder / "landscape.json").exists()
    assert json.loads((folder / "request.json").read_text())["drug_class"]["name"] == NAME


def test_mcp_first_scope_reply_contains_choices_and_plain_words(tmp_path):
    context = Context(tmp_path, get=catalogue, sleep=lambda _: None)
    code, result = call_tool(
        context,
        {
            "name": "scope",
            "arguments": {
                "run": "choice",
                "mode": "direct",
                "request": {"drug_class": {"name": NAME, "source": "ATC"}},
            },
        },
    )
    assert code == "ok" and result["isError"] is True
    reply = json.loads(result["content"][0]["text"])
    assert reply["scope"]["code"] == "unresolved"
    assert reply["scope"]["query"] == {}
    assert "L01EB" in "\n".join(reply["in_words"])
    assert CANONICAL in "\n".join(reply["in_words"])
    assert not (tmp_path / "choice" / "scope.json").exists()


def test_mcp_rejected_changed_request_does_not_describe_the_previous_scope(tmp_path):
    context = Context(tmp_path, get=catalogue, sleep=lambda _: None)
    folder = tmp_path / "choice"
    folder.mkdir()
    (folder / "request.json").write_text(json.dumps({"condition": "asthma"}))
    (folder / "resolution.json").write_text(
        json.dumps({"code": "resolved", "query": {"query.cond": "asthma"}})
    )
    code, result = call_tool(
        context,
        {
            "name": "scope",
            "arguments": {
                "run": "choice",
                "mode": "direct",
                "request": {"condition": "diabetes"},
            },
        },
    )
    reply = json.loads(result["content"][0]["text"])
    assert code == "ok" and result["isError"] is True
    assert "scope" not in reply and "in_words" not in reply


def test_relay_carries_search_catalogue_without_rewriting_bodies(tmp_path):
    context = Context(tmp_path, sleep=lambda _: None)
    args = {"run": "relay", "mode": "relay", "request": {"drug_class": {"name": NAME, "source": "ATC"}}}
    urls = []
    for _ in range(6):
        code, result = call_tool(context, {"name": "scope", "arguments": args})
        assert code == "ok"
        reply = json.loads(result["content"][0]["text"])
        if reply["status"] != "awaiting_fetch":
            assert reply["scope"]["code"] == "unresolved"
            assert "L01EB" in "\n".join(reply["in_words"])
            assert any("/allClasses.json" in url for url in urls)
            assert not (tmp_path / "relay" / "scope.json").exists()
            return
        for fetch in reply["fetches"]:
            from urllib.parse import parse_qsl, urlsplit

            url = urlsplit(fetch["url"])
            urls.append(fetch["url"])
            status, body = catalogue(url.scheme + "://" + url.netloc + url.path, dict(parse_qsl(url.query)))
            assert status == 200
            raw = json.dumps(body, indent=3, ensure_ascii=True) + "\n\n"
            code, saved = call_tool(
                context,
                {
                    "name": "save_fetch",
                    "arguments": {
                        "run": "relay",
                        "save_as": fetch["save_as"],
                        "body": raw,
                    },
                },
            )
            assert code == "ok" and not saved.get("isError", False)
            assert (tmp_path / "relay" / fetch["save_as"]).read_bytes() == raw.encode("utf-8")
    raise AssertionError("Relay did not reach explicit class choices")
