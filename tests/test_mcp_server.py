"""`trialledger mcp` (add-agent-operation 6.2): the Model Context Protocol server, revision 2025-11-25 over
stdio, driven message by message over a fake registry and RxNav's own recorded answers
(tests/rxnav_request_answers.json); nothing here touches the network.

Positive: initialize answers the version asked (or the latest here) with the tools capability, the server's
name and its instructions; ping is answered before and after; tools/list names every tool with a description
and an input schema; a relay run through the tools (landscape, save_fetch for every fetch it lists, landscape
again) writes the record a direct run writes; save_fetch writes the body exactly as given; scope returns the
resolved search; record returns each part as the record holds it; `trialledger mcp` serves a session and ends
0; each decision names every code it can return.
Negative: a line that is not JSON is a parse error; a batch, a request of another shape, an id that is null,
a boolean or a fraction are invalid requests; an unknown method (server/discover among them) is not found; a
request before initialize is refused, initialize twice too; notifications and responses are never answered;
an unknown tool and a call not of the protocol's shape are invalid params; no line ends the session over
the encoded stream (a lone surrogate echoed in an id, a save_as or an argument's name, JSON nested past the
parser, a defect in answering); a run folder that is a link out of the root is refused; arguments the
tool's schema refuses, a run that cannot start, a request refused, save_fetch to a path next.json does not
name, to a path outside the run folder (absolute, through "..", through a link) and before any next.json,
and a record or scope not there yet are tool results with isError true and plain words, nothing written.
"""

import json
from pathlib import Path

import httpx
import pytest
from conftest import version
from records import ongoing_study, results_study
from schema3_record import THIRD, schema3_record

from TrialLedger import cli, contract, mcp_server
from TrialLedger.contract import FIELDS
from TrialLedger.ingest import API_BASE
from TrialLedger.mcp_server import (
    ERRORS,
    INSTRUCTIONS,
    MANIFEST_KEYS,
    NOT_WRITABLE_WORDS,
    PREVIEW_MEANING,
    PROTOCOL_VERSIONS,
    RECORD_PAGE_LIMIT,
    RECORD_PARTS,
    RECORD_WORDS,
    REQUEST,
    SERVER_INFO,
    STATUS_KEYS,
    TOOL_NEXT,
    TOOL_TERMS,
    TOOLS,
    Context,
    answer,
    argument_problems,
    call_target,
    negotiate,
    page_window,
    pointer_value,
    record_view,
    route,
    save_target,
    serve,
    study_line,
)
from TrialLedger.preview import PREVIEWED, scope_words
from TrialLedger.request import lookup_url, slot_value_ok

DOC = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
ANSWERS = DOC["answers"]
PD1_IN_LUNG = DOC["requests"][0]
EXAMPLES = Path(__file__).parent / "fixtures" / "contract" / "examples"
INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "a client", "version": "1.0"},
    },
}
INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}


def ids_of(studies):
    return [s["protocolSection"]["identificationModule"]["nctId"] for s in studies]


def drug_free(study):
    for item in study["protocolSection"].get("armsInterventionsModule", {}).get("interventions", []):
        item["type"] = "DEVICE"
    return study


STUDIES = [drug_free(results_study()), drug_free(ongoing_study())]


def registry_client():
    """The registry: /version, the query's ID pages and its batches by filter.ids."""
    by_id = dict(zip(ids_of(STUDIES), STUDIES, strict=True))

    def serve_request(request):
        if request.url.path == "/api/v2/version":
            return version()
        params = request.url.params
        if params.get("fields") == "NCTId":
            page = [{"protocolSection": {"identificationModule": {"nctId": nct}}} for nct in by_id]
            return httpx.Response(200, json={"studies": page, "totalCount": len(page)})
        asked = params["filter.ids"].split(",")
        return httpx.Response(200, json={"studies": [by_id[n] for n in asked], "totalCount": len(asked)})

    return httpx.Client(base_url=API_BASE, transport=httpx.MockTransport(serve_request))


def rxnav_get(url, params):
    """RxNav as recorded; a name RxNorm does not hold, and no class for a name RxClass is asked about."""
    key = lookup_url(url, params)
    if key in ANSWERS:
        return tuple(ANSWERS[key])
    return (200, {"idGroup": {}}) if url.endswith("/rxcui.json") else (200, {})


def sandbox(url, **kwargs):
    """A chat app's sandbox: the registry and GitHub answer, RxNav is blocked, so the doctor says relay."""
    if "rxnav" in url:
        raise ConnectionRefusedError("egress blocked")
    return httpx.Response(200)


class Client:
    """An MCP client of this server, in process: each message answered as `serve` answers it."""

    def __init__(self, root, initialize=True, **transports):
        self.context = Context(root, **transports)
        root.mkdir(parents=True, exist_ok=True)
        self.initialized = False
        self.ids = 100
        if initialize:
            assert self.send(INIT)["result"]["protocolVersion"] == "2025-11-25"
            assert self.send(INITIALIZED) is None

    def send(self, message):
        line = message if isinstance(message, bytes) else json.dumps(message).encode("utf-8")
        reply, self.initialized = answer(self.context, line, self.initialized)
        return reply

    def call(self, name, **arguments):
        """A tool's result: its document and whether it is an error."""
        self.ids += 1
        params = {"name": name, "arguments": arguments}
        reply = self.send({"jsonrpc": "2.0", "id": self.ids, "method": "tools/call", "params": params})
        assert reply["id"] == self.ids and set(reply) == {"jsonrpc", "id", "result"}, reply
        result = reply["result"]
        assert set(result) == {"content", "isError"} and len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        return json.loads(result["content"][0]["text"]), result["isError"]


def relay_through_the_tools(client, run, request):
    """The assistant's part in relay mode: landscape, every listed URL fetched and saved, landscape again."""
    registry = registry_client()
    statuses = []
    for _round in range(20):
        document, is_error = client.call("landscape", run=run, request=request, mode="relay")
        statuses.append(document["status"])
        if document["status"] != "awaiting_fetch":
            return statuses, document, is_error
        assert is_error is False and document["exit"] == 3 and document["fetches"]
        for fetch in document["fetches"]:
            url = httpx.URL(fetch["url"])
            if url.host == "rxnav.nlm.nih.gov":
                status, body = rxnav_get(str(url.copy_with(query=None)), dict(url.params))
                text = json.dumps(body) if status == 200 else f"failed: HTTP {status}"
            else:
                text = registry.get(fetch["url"]).content.decode("utf-8")
            saved, refused = client.call("save_fetch", run=run, save_as=fetch["save_as"], body=text)
            assert refused is False and saved["saved"] == fetch["save_as"]
    raise AssertionError("the relay did not end within 20 rounds")


# ── the protocol, message by message ────────────────────────────────────────────────────────────────────


def test_initialize_answers_the_version_asked_with_the_tools_capability(tmp_path):
    client = Client(tmp_path, initialize=False)
    assert client.send(INIT) == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": INSTRUCTIONS,
        },
    }
    assert client.initialized is True


@pytest.mark.parametrize("asked", ["2025-06-18", "2025-03-26", "2024-11-05"])
def test_an_earlier_revision_is_answered_with_itself(tmp_path, asked):
    client = Client(tmp_path, initialize=False)
    message = {**INIT, "params": {**INIT["params"], "protocolVersion": asked}}
    assert client.send(message)["result"]["protocolVersion"] == asked


@pytest.mark.parametrize("asked", ["2026-07-28", "1900-01-01", "1.0"])
def test_an_unknown_version_is_answered_with_the_latest_here(tmp_path, asked):
    client = Client(tmp_path, initialize=False)
    message = {**INIT, "params": {**INIT["params"], "protocolVersion": asked}}
    assert client.send(message)["result"]["protocolVersion"] == PROTOCOL_VERSIONS[0] == "2025-11-25"


def test_initialize_without_a_version_is_invalid_params_and_initializes_nothing(tmp_path):
    client = Client(tmp_path, initialize=False)
    reply = client.send({"jsonrpc": "2.0", "id": "a", "method": "initialize", "params": {}})
    assert reply == {
        "jsonrpc": "2.0",
        "id": "a",
        "error": {
            "code": -32602,
            "message": ERRORS["invalid_params"][1],
            "data": {"supported": [*PROTOCOL_VERSIONS]},
        },
    }
    assert client.initialized is False


def test_notifications_and_responses_are_never_answered(tmp_path):
    client = Client(tmp_path)
    for message in (
        INITIALIZED,
        {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 3}},
        {"jsonrpc": "2.0", "method": "notifications/unknown", "params": [1]},
        {"jsonrpc": "2.0", "id": 7, "result": {}},
        {"jsonrpc": "2.0", "id": 8, "error": {"code": -1, "message": "no"}},
        b"",
        b"   \n",
    ):
        assert client.send(message) is None


def test_ping_is_answered_before_and_after_initialize(tmp_path):
    client = Client(tmp_path, initialize=False)
    assert client.send({"jsonrpc": "2.0", "id": 5, "method": "ping"}) == {
        "jsonrpc": "2.0",
        "id": 5,
        "result": {},
    }
    client.send(INIT)
    assert client.send({"jsonrpc": "2.0", "id": "p", "method": "ping"})["result"] == {}


def test_a_request_before_initialize_is_refused_and_initialize_twice_too(tmp_path):
    client = Client(tmp_path, initialize=False)
    reply = client.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert reply["id"] == 2 and reply["error"]["code"] == -32600
    assert reply["error"]["message"] == ERRORS["not_initialized"][1]
    client.send(INIT)
    again = client.send({**INIT, "id": 3})
    assert again["id"] == 3 and again["error"]["message"] == ERRORS["already_initialized"][1]


def test_tools_list_names_every_tool_with_its_description_and_schema(tmp_path):
    reply = Client(tmp_path).send({"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}})
    tools = reply["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "doctor",
        "landscape",
        "save_fetch",
        "scope",
        "record",
        "reason",
        "reason_result",
        "reason_revise",
        "reason_export",
    ]
    for tool in tools:
        assert set(tool) == {"name", "description", "inputSchema"}
        assert len(tool["description"]) > 200
        schema = tool["inputSchema"]
        assert schema["type"] == "object" and schema["additionalProperties"] is False
        assert set(schema["required"]) <= set(schema["properties"])
        if tool["name"] == "reason":
            assert schema["required"] == [] and "run" not in schema["properties"]
            assert schema["oneOf"] == [
                {"required": ["request"], "not": {"required": ["prepared"]}},
                {"required": ["prepared"], "not": {"required": ["request"]}},
            ]
        elif tool["name"] in {"reason_result", "reason_revise", "reason_export"}:
            assert schema["required"] == ["id"] and "run" not in schema["properties"]
        else:
            assert "run" in schema["required"]


@pytest.mark.parametrize("line", [b"{not json", b'{"jsonrpc": "2.0", "id": 1,', b"\xff\xfe{}", b"\x00"])
def test_a_line_that_is_not_json_is_a_parse_error(tmp_path, line):
    assert Client(tmp_path).send(line) == {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32700, "message": ERRORS["parse_error"][1]},
    }


@pytest.mark.parametrize(
    ("message", "ident"),
    [
        ([{"jsonrpc": "2.0", "id": 1, "method": "ping"}], None),
        ({"id": 1, "method": "ping"}, 1),
        ({"jsonrpc": "1.0", "id": 1, "method": "ping"}, 1),
        ({"jsonrpc": "2.0", "id": None, "method": "ping"}, None),
        ({"jsonrpc": "2.0", "id": True, "method": "ping"}, None),
        ({"jsonrpc": "2.0", "id": 1.5, "method": "ping"}, None),
        ({"jsonrpc": "2.0", "id": 4, "method": 4}, 4),
        ({"jsonrpc": "2.0", "id": 4}, 4),
        ("ping", None),
    ],
)
def test_a_message_not_of_the_protocols_shape_is_an_invalid_request(tmp_path, message, ident):
    reply = Client(tmp_path).send(message)
    assert reply["id"] == ident and reply["error"]["code"] == -32600


def test_an_unknown_method_is_not_found(tmp_path):
    client = Client(tmp_path)
    for method in ("server/discover", "resources/list", "prompts/list"):
        reply = client.send({"jsonrpc": "2.0", "id": method, "method": method})
        assert reply == {
            "jsonrpc": "2.0",
            "id": method,
            "error": {"code": -32601, "message": "Method not found"},
        }


def test_params_not_an_object_are_invalid_params(tmp_path):
    reply = Client(tmp_path).send({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": [1]})
    assert reply["error"]["code"] == -32602


def test_an_unknown_tool_and_a_call_not_of_its_shape_are_invalid_params(tmp_path):
    client = Client(tmp_path)
    reply = client.send(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "design", "arguments": {}}}
    )
    assert reply == {
        "jsonrpc": "2.0",
        "id": 4,
        "error": {"code": -32602, "message": "Unknown tool", "data": {"tool": "design"}},
    }
    for params in ({"arguments": {}}, {"name": "scope", "arguments": ["run"]}, {"name": 3}):
        reply = client.send({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": params})
        assert reply["error"]["code"] == -32602 and reply["id"] == 5


def test_serve_writes_one_line_per_answer_and_nothing_for_the_rest(tmp_path):
    written = []
    lines = [
        json.dumps(INIT).encode() + b"\n",
        json.dumps(INITIALIZED).encode() + b"\n",
        b"\n",
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).encode() + b"\n",
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ping"}).encode(),
    ]
    serve(lines, written.append, Context(tmp_path / "runs"))
    assert [json.loads(line)["id"] for line in written] == [1, 2, 3]
    assert not any("\n" in line for line in written)
    assert (tmp_path / "runs").is_dir()


def test_trialledger_mcp_serves_a_session_and_ends_0(tmp_path):
    written = []
    lines = [json.dumps(m).encode() for m in (INIT, INITIALIZED)]
    params = {"name": "scope", "arguments": {"run": "nothing-yet"}}
    lines.append(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": params}).encode())
    code = cli.main(["mcp", "--root", str(tmp_path / "runs")], mcp_streams=(iter(lines), written.append))
    assert code == 0
    replies = [json.loads(line) for line in written]
    assert replies[0]["result"]["serverInfo"] == SERVER_INFO
    assert replies[1]["result"]["isError"] is True


def encoded_session(tmp_path, messages, monkeypatch=None):
    """`serve` over the stream as stdio_streams writes it (each answer encoded as UTF-8): the replies."""
    out = []
    lines = [m if isinstance(m, bytes) else json.dumps(m).encode("utf-8") for m in messages]
    serve(lines, lambda text: out.append(text.encode("utf-8") + b"\n"), Context(tmp_path / "runs"))
    return [json.loads(line.decode("utf-8")) for line in out]


PING = {"jsonrpc": "2.0", "id": "after", "method": "ping"}


@pytest.mark.parametrize(
    "message",
    [
        {"jsonrpc": "2.0", "id": "\ud800", "method": "ping"},
        {"jsonrpc": "2.0", "id": "\udfff", "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "save_fetch", "arguments": {"run": "r", "save_as": "\ud800", "body": "{}"}},
        },
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "scope", "arguments": {"run": "r", "\ud800": 1}},
        },
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "\ud800"}},
    ],
)
def test_a_lone_surrogate_echoed_is_written_escaped_and_the_session_goes_on(tmp_path, message):
    replies = encoded_session(tmp_path, [INIT, INITIALIZED, message, PING])
    assert len(replies) == 3 and replies[2] == {"jsonrpc": "2.0", "id": "after", "result": {}}
    assert replies[1]["id"] == message["id"]


def test_json_nested_past_the_parser_is_a_parse_error_and_the_session_goes_on(tmp_path):
    deep = b"[" * 200000 + b"]" * 200000
    replies = encoded_session(tmp_path, [INIT, INITIALIZED, deep, PING])
    assert replies[1] == {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32700, "message": ERRORS["parse_error"][1]},
    }
    assert replies[2]["result"] == {}


def test_a_defect_in_answering_a_line_is_an_internal_error_and_the_session_goes_on(tmp_path, monkeypatch):
    real = mcp_server.answer

    def flawed(context, line, initialized):
        if b"boom" in line:
            raise KeyError("boom")
        return real(context, line, initialized)

    monkeypatch.setattr(mcp_server, "answer", flawed)
    boom = {"jsonrpc": "2.0", "id": 3, "method": "boom"}
    replies = encoded_session(tmp_path, [INIT, INITIALIZED, boom, PING])
    assert replies[1]["id"] is None and replies[1]["error"]["code"] == -32603
    assert replies[1]["error"]["data"] == {"detail": "KeyError: 'boom'"}
    assert replies[2]["result"] == {}


def test_wire_keeps_utf8_text_as_it_is_and_escapes_only_what_utf8_cannot_hold():
    assert mcp_server.wire({"a": "ß"}) == '{"a": "ß"}'
    assert mcp_server.wire({"a": "ß\ud800"}) == '{"a": "\\u00df\\ud800"}'


def test_a_run_folder_that_is_a_link_out_of_the_root_is_refused(tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "away").symlink_to(elsewhere, target_is_directory=True)
    client = Client(tmp_path / "runs", probe_get=sandbox)
    for tool, arguments in (("doctor", {}), ("landscape", {"request": PD1_IN_LUNG}), ("scope", {})):
        document, is_error = client.call(tool, run="away", **arguments)
        assert is_error is True and document["refused"] == "run_outside_root"
    assert list(elsewhere.iterdir()) == []


def test_the_request_schema_admits_every_drug_class_key_the_request_admits():
    drug_class = REQUEST["properties"]["drug_class"]
    examples = {
        "name": [{"source": "EPC", "name": "Kinase Inhibitor"}],
        "id": [{"source": "ATC", "id": "L01EB"}],
        "source": [
            {"source": source, "id": "L01EB"} for source in drug_class["properties"]["source"]["enum"]
        ],
        "subclasses": [
            {"source": "EPC", "name": "Kinase Inhibitor", "subclasses": rule}
            for rule in ("include", "exclude", ["N0000175605"])
        ],
    }
    assert set(drug_class["properties"]) == set(examples)
    for given in (value for key in drug_class["properties"] for value in examples[key]):
        assert slot_value_ok("drug_class", given), given
    assert drug_class["properties"]["subclasses"]["anyOf"][0]["enum"] == ["include", "exclude"]
    assert not slot_value_ok("drug_class", {"source": "EPC", "name": "Kinase Inhibitor", "other": 1})
    assert not slot_value_ok("drug_class", {"source": "EPC", "name": "Kinase Inhibitor", "subclasses": []})


# ── the tools ───────────────────────────────────────────────────────────────────────────────────────────


def test_doctor_reports_the_mode_and_the_next_step_with_these_tools(tmp_path):
    document, is_error = Client(tmp_path, probe_get=sandbox).call("doctor", run="first")
    assert is_error is False
    assert document["tool"] == "doctor" and document["run_folder"] == str((tmp_path / "first").resolve())
    assert document["mode"] == "relay" and document["with_these_tools"] == TOOL_NEXT["relay"]
    assert document["report"]["reachable"]["rxnav.nlm.nih.gov"] == "unreachable: ConnectionRefusedError"
    assert document["report"]["run_folder"] == {"path": str(tmp_path / "first"), "writable": True}


def test_doctor_says_why_no_run_can_start(tmp_path):
    (tmp_path / "taken").write_text("a file, not a folder", encoding="utf-8")
    document, is_error = Client(tmp_path, probe_get=sandbox).call("doctor", run="taken")
    assert is_error is True and document["mode"] == "folder_not_writable"
    assert document["with_these_tools"] == NOT_WRITABLE_WORDS and "--run" not in NOT_WRITABLE_WORDS


@pytest.mark.parametrize(
    ("arguments", "refused", "concerned"),
    [
        ({}, "missing_argument", ["run"]),
        ({"run": "a", "extra": 1}, "unknown_argument", ["extra"]),
        ({"run": 3}, "wrong_type", ["run"]),
        ({"run": "../outside"}, "not_allowed", ["run"]),
        ({"run": "/etc"}, "not_allowed", ["run"]),
        ({"run": ".hidden"}, "not_allowed", ["run"]),
        ({"run": "a\n"}, "not_allowed", ["run"]),
    ],
)
def test_arguments_the_schema_refuses_are_a_tool_error_in_plain_words(
    tmp_path, arguments, refused, concerned
):
    document, is_error = Client(tmp_path).call("scope", **arguments)
    assert is_error is True
    assert document["refused"] == refused and document["arguments"] == concerned and document["why"]
    assert sorted(p.name for p in tmp_path.iterdir()) == []


def test_relay_and_direct_preserve_same_registry_values(tmp_path):
    client = Client(tmp_path / "runs", probe_get=sandbox)
    statuses, document, is_error = relay_through_the_tools(client, "relayed", PD1_IN_LUNG)
    assert statuses[-1] == "complete" and set(statuses[:-1]) == {"awaiting_fetch"} and len(statuses) > 3
    assert is_error is False and document["exit"] == 0 and document["mode"] == "relay"
    folder = tmp_path / "runs" / "relayed"
    assert document["record"] == str((folder / "landscape.json").resolve())
    direct = Client(tmp_path / "runs", get=rxnav_get, http=registry_client(), sleep=lambda s: None)
    done, failed = direct.call("landscape", run="direct", request=PD1_IN_LUNG, mode="direct")
    assert failed is False and done["status"] == "complete" and "fetches" not in done
    relayed = json.loads((folder / "landscape.json").read_text(encoding="utf-8"))
    held = json.loads((tmp_path / "runs" / "direct" / "landscape.json").read_text(encoding="utf-8"))
    assert relayed["schema_version"] == held["schema_version"] == 4
    assert relayed["manifest"]["retrieval"]["mode"] == "relay"
    assert held["manifest"]["retrieval"]["mode"] == "direct"
    # These source studies are drug-free, so retrieval mode is the only reporting difference.
    relayed["manifest"]["retrieval"] = held["manifest"]["retrieval"]
    assert relayed == held


def test_landscape_without_a_mode_takes_the_doctors(tmp_path):
    document, is_error = Client(tmp_path, probe_get=sandbox).call("landscape", run="r", request=PD1_IN_LUNG)
    assert is_error is False and document["mode"] == "relay" and document["status"] == "awaiting_fetch"
    assert document["fetches"][0]["save_as"].startswith("lookups/")
    assert document["instructions"] and document["then"]


def test_landscape_refuses_a_request_by_name(tmp_path):
    client = Client(tmp_path, probe_get=sandbox)
    document, is_error = client.call("landscape", run="r", request={}, mode="relay")
    assert is_error is True and document["status"] == "request_refused" and document["exit"] == 2
    assert document["detail"].startswith("empty_request") and document["meaning"].startswith("refused")
    assert "--help" in document["advice"] and document["with_these_tools"] == TOOL_TERMS
    document, is_error = client.call("landscape", run="r", request=["drug"], mode="relay")
    assert is_error is True and document["refused"] == "wrong_type"


def test_landscape_that_cannot_start_says_why(tmp_path):
    (tmp_path / "taken").write_text("a file, not a folder", encoding="utf-8")
    document, is_error = Client(tmp_path, probe_get=sandbox).call(
        "landscape", run="taken", request=PD1_IN_LUNG
    )
    assert is_error is True and document["status"] == "mode_unavailable"
    assert document["detail"] == "folder_not_writable" and document["with_these_tools"] == NOT_WRITABLE_WORDS


def test_save_fetch_writes_the_body_exactly_as_given(tmp_path):
    client = Client(tmp_path, probe_get=sandbox)
    document, _ = client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
    first, *others = [fetch["save_as"] for fetch in document["fetches"]]
    body = '{"version": "05-Oct-2026", "note": "ß  kept\\n"}'
    saved, is_error = client.call("save_fetch", run="r", save_as=first, body=body)
    assert is_error is False and saved["bytes"] == len(body.encode("utf-8"))
    assert saved["still_to_save"] == others
    assert (tmp_path / "r" / first).read_bytes() == body.encode("utf-8")
    assert not [p for p in (tmp_path / "r" / first).parent.iterdir() if p.name.endswith(".partial")]


@pytest.mark.parametrize(
    "save_as",
    [
        "lookups/lookup-999.json",
        "bodies/ids-001.json",
        "request.json",
        "landscape.json",
    ],
)
def test_save_fetch_refuses_a_path_next_json_does_not_name(tmp_path, save_as):
    client = Client(tmp_path, probe_get=sandbox)
    client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
    before = (tmp_path / "r" / "request.json").read_bytes()
    document, is_error = client.call("save_fetch", run="r", save_as=save_as, body="{}")
    assert is_error is True and document["refused"] == "not_named"
    assert not (tmp_path / "r" / save_as).exists() or save_as == "request.json"
    assert (tmp_path / "r" / "request.json").read_bytes() == before


@pytest.mark.parametrize(
    "save_as",
    [
        "../outside.json",
        "/tmp/outside.json",
        "lookups/../../outside.json",
        "lookups\\x.json",
        "C:/x.json",
        "",
    ],
)
def test_save_fetch_refuses_a_path_outside_the_run_folder(tmp_path, save_as):
    client = Client(tmp_path / "runs", probe_get=sandbox)
    client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
    folder = tmp_path / "runs" / "r"
    # even a next.json edited to name the path
    waiting = json.loads((folder / "next.json").read_text(encoding="utf-8"))
    waiting["fetches"].append({"url": "https://x", "save_as": save_as, "why": "rxnav_answer"})
    (folder / "next.json").write_text(json.dumps(waiting), encoding="utf-8")
    document, is_error = client.call("save_fetch", run="r", save_as=save_as, body="{}")
    assert is_error is True and document["refused"] == "outside_run"
    assert not (tmp_path / "outside.json").exists() and not (tmp_path / "runs" / "outside.json").exists()


def test_save_fetch_refuses_a_path_a_link_carries_outside(tmp_path):
    client = Client(tmp_path / "runs", probe_get=sandbox)
    document, _ = client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
    save_as = document["fetches"][0]["save_as"]
    folder = tmp_path / "runs" / "r"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (folder / "lookups").rmdir()
    (folder / "lookups").symlink_to(elsewhere, target_is_directory=True)
    document, is_error = client.call("save_fetch", run="r", save_as=save_as, body="{}")
    assert is_error is True and document["refused"] == "outside_run"
    assert list(elsewhere.iterdir()) == []


def test_save_fetch_never_follows_a_link_at_its_staging_name(tmp_path):
    client = Client(tmp_path / "runs", probe_get=sandbox)
    document, _ = client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
    save_as = document["fetches"][0]["save_as"]
    target = tmp_path / "runs" / "r" / save_as
    outside = tmp_path / "outside.json"
    (target.parent / f".{target.name}.partial").symlink_to(outside)
    saved, is_error = client.call("save_fetch", run="r", save_as=save_as, body="{}")
    assert is_error is False and target.read_bytes() == b"{}" and not target.is_symlink()
    assert not outside.exists()


def test_save_fetch_lists_only_what_it_would_write_as_still_to_save(tmp_path):
    client = Client(tmp_path / "runs", probe_get=sandbox)
    document, _ = client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
    first, *others = [fetch["save_as"] for fetch in document["fetches"]]
    folder = tmp_path / "runs" / "r"
    waiting = json.loads((folder / "next.json").read_text(encoding="utf-8"))
    for outside in ("/etc/hosts", "../r/request.json"):
        waiting["fetches"].append({"url": "https://x", "save_as": outside, "why": "rxnav_answer"})
    (folder / "next.json").write_text(json.dumps(waiting), encoding="utf-8")
    saved, is_error = client.call("save_fetch", run="r", save_as=first, body="{}")
    assert is_error is False and saved["still_to_save"] == others


def test_a_registry_body_refused_is_answered_with_a_new_run_folder(tmp_path):
    client = Client(tmp_path / "runs", probe_get=sandbox)
    registry = registry_client()
    for _round in range(20):
        document, _ = client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
        registry_fetches = [f for f in document["fetches"] if f["save_as"].startswith("bodies/")]
        if registry_fetches:
            break
        for fetch in document["fetches"]:
            url = httpx.URL(fetch["url"])
            status, body = rxnav_get(str(url.copy_with(query=None)), dict(url.params))
            client.call("save_fetch", run="r", save_as=fetch["save_as"], body=json.dumps(body))
    assert registry.get(registry_fetches[0]["url"]).status_code == 200
    client.call("save_fetch", run="r", save_as=registry_fetches[0]["save_as"], body="failed: HTTP 503")
    document, is_error = client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
    assert is_error is True and document["status"] == "not_json" and document["exit"] == 2
    assert "new run name" in document["with_these_tools"]


def test_save_fetch_before_any_fetch_is_listed_is_refused(tmp_path):
    document, is_error = Client(tmp_path).call("save_fetch", run="r", save_as="bodies/x.json", body="{}")
    assert is_error is True and document["refused"] == "not_named"
    assert not (tmp_path / "r" / "bodies").exists()


def test_save_fetch_refuses_text_that_cannot_be_utf8(tmp_path):
    client = Client(tmp_path, probe_get=sandbox)
    document, _ = client.call("landscape", run="r", request=PD1_IN_LUNG, mode="relay")
    save_as = document["fetches"][0]["save_as"]
    document, is_error = client.call("save_fetch", run="r", save_as=save_as, body="\ud800")
    assert is_error is True and document["refused"] == "not_utf8"
    assert not (tmp_path / "r" / save_as).exists()


def test_scope_returns_the_resolved_search_once_there_is_one(tmp_path):
    client = Client(tmp_path / "runs", probe_get=sandbox)
    document, is_error = client.call("scope", run="r")
    assert is_error is True and document["error"] == "no_scope"
    relay_through_the_tools(client, "r", PD1_IN_LUNG)
    document, is_error = client.call("scope", run="r")
    held = json.loads((tmp_path / "runs" / "r" / "resolution.json").read_text(encoding="utf-8"))
    assert is_error is False and document["scope"] == held and held["code"] == "resolved"


# ── the decisions, directly ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("message", "initialized", "expected"),
    [
        ({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, False, ("initialize", 1)),
        ({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, True, ("already_initialized", 1)),
        ({"jsonrpc": "2.0", "id": "x", "method": "ping"}, False, ("ping", "x")),
        ({"jsonrpc": "2.0", "id": 0, "method": "ping", "params": {}}, True, ("ping", 0)),
        ({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, False, ("not_initialized", 2)),
        ({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, True, ("tools_list", 2)),
        ({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {}}, True, ("tools_call", 3)),
        ({"jsonrpc": "2.0", "id": 4, "method": "server/discover"}, True, ("method_not_found", 4)),
        ({"jsonrpc": "2.0", "id": 4, "method": "server/discover"}, False, ("not_initialized", 4)),
        ({"jsonrpc": "2.0", "method": "notifications/initialized"}, False, ("notification", None)),
        ({"jsonrpc": "2.0", "method": "notifications/x", "params": 3}, True, ("notification", None)),
        ({"jsonrpc": "2.0", "id": 5, "result": {}}, True, ("response", 5)),
        ({"jsonrpc": "2.0", "id": "5", "error": {}}, False, ("response", "5")),
        ({"jsonrpc": "2.0", "id": 6, "method": "ping", "params": []}, True, ("invalid_params", 6)),
        ({"jsonrpc": "2.0", "id": None, "result": {}}, True, ("invalid_request", None)),
        ({"jsonrpc": "2.0", "id": 7}, True, ("invalid_request", 7)),
        ({"jsonrpc": "2.0", "method": None, "id": 8}, True, ("invalid_request", 8)),
        ({"jsonrpc": "2.0", "method": 4, "id": 8}, True, ("invalid_request", 8)),
        ({"jsonrpc": "2.0", "method": "", "id": 8}, True, ("method_not_found", 8)),
        ({"jsonrpc": "1.0", "method": "ping", "id": True}, True, ("invalid_request", None)),
        ({"jsonrpc": "2.0", "id": 1.5, "result": {}}, True, ("invalid_request", None)),
        ({"jsonrpc": "2.0", "method": "ping", "id": False}, True, ("invalid_request", None)),
        ({"jsonrpc": "2.0", "method": "ping", "id": [1]}, True, ("invalid_request", None)),
        ({"jsonrpc": "2.1", "method": "ping", "id": 9}, True, ("invalid_request", 9)),
        ({"method": "ping", "id": 9}, True, ("invalid_request", 9)),
        ([{"jsonrpc": "2.0", "method": "ping", "id": 9}], True, ("invalid_request", None)),
        (None, True, ("invalid_request", None)),
        (3, False, ("invalid_request", None)),
    ],
)
def test_route_names_what_each_message_is(message, initialized, expected):
    assert route(message, initialized) == expected


def test_negotiate_echoes_a_supported_version_and_offers_the_latest_otherwise():
    for asked in PROTOCOL_VERSIONS:
        assert negotiate({"protocolVersion": asked}) == ("ok", asked)
    assert negotiate({"protocolVersion": "2099-01-01", "capabilities": {}}) == ("ok", "2025-11-25")
    assert negotiate({"protocolVersion": ""}) == ("ok", "2025-11-25")


@pytest.mark.parametrize("params", [None, [], "2025-11-25", {}, {"protocolVersion": 20251125}])
def test_negotiate_refuses_params_naming_no_version(params):
    assert negotiate(params) == ("invalid_params", "")


def test_call_target_names_the_tool_and_its_arguments():
    assert call_target({"name": "scope", "arguments": {"run": "r"}}) == ("ok", "scope", {"run": "r"})
    assert call_target({"name": "doctor"}) == ("ok", "doctor", {})
    assert call_target({"name": "design", "arguments": {}}) == ("unknown_tool", "design", {})
    assert call_target({"name": "Scope"}) == ("unknown_tool", "Scope", {})


@pytest.mark.parametrize(
    ("params", "name"),
    [
        (None, ""),
        ([], ""),
        ({}, ""),
        ({"name": 1}, ""),
        ({"name": "record", "arguments": []}, "record"),
        ({"name": "record", "arguments": None}, "record"),
    ],
)
def test_call_target_refuses_a_call_not_of_its_shape(params, name):
    assert call_target(params) == ("invalid_params", name, {})


SCHEMA = {
    "type": "object",
    "properties": {
        "run": {"type": "string", "pattern": "^[a-z]{1,3}$"},
        "part": {"type": "string", "enum": ["a", "b"]},
        "request": {"type": "object"},
        "count": {"type": "integer"},
        "flag": {"type": "boolean"},
    },
    "required": ["run", "request"],
    "additionalProperties": False,
}


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ({"run": "ab", "request": {}}, ("ok", [])),
        ({"run": "abc", "request": {"x": [1]}, "part": "b", "count": 0, "flag": False}, ("ok", [])),
        ([], ("not_an_object", [])),
        (None, ("not_an_object", [])),
        ({"run": "ab", "request": {}, "zz": 1, "aa": 2}, ("unknown_argument", ["aa", "zz"])),
        ({"zz": 1}, ("unknown_argument", ["zz"])),
        ({}, ("missing_argument", ["request", "run"])),
        ({"run": "ab"}, ("missing_argument", ["request"])),
        ({"run": 1, "request": []}, ("wrong_type", ["request", "run"])),
        ({"run": "ab", "request": {}, "count": True}, ("wrong_type", ["count"])),
        ({"run": "ab", "request": {}, "count": "1"}, ("wrong_type", ["count"])),
        ({"run": "ab", "request": {}, "flag": 1}, ("wrong_type", ["flag"])),
        ({"run": "abcd", "request": {}}, ("not_allowed", ["run"])),
        ({"run": "ab\n", "request": {}}, ("not_allowed", ["run"])),
        ({"run": "AB", "request": {}, "part": "c"}, ("not_allowed", ["part", "run"])),
    ],
)
def test_argument_problems_names_the_first_kind_and_every_argument_of_it(arguments, expected):
    assert argument_problems(SCHEMA, arguments) == expected


ENUM_ONLY = {"properties": {"part": {"type": "string", "enum": ["a", "b"]}}}
PATTERN_ONLY = {"properties": {"run": {"type": "string", "pattern": "^[a-z]+$"}}}


@pytest.mark.parametrize(
    ("schema", "arguments", "expected"),
    [
        (ENUM_ONLY, {"part": "a"}, ("ok", [])),
        (ENUM_ONLY, {"part": "c"}, ("not_allowed", ["part"])),
        (PATTERN_ONLY, {"run": "ab"}, ("ok", [])),
        (PATTERN_ONLY, {"run": "AB"}, ("not_allowed", ["run"])),
        (PATTERN_ONLY, {}, ("ok", [])),
        (SCHEMA, {3: "x"}, ("unknown_argument", ["3"])),
        (SCHEMA, {"run": "ab", "request": {}, "count": 5}, ("ok", [])),
    ],
)
def test_argument_problems_reads_an_enum_a_pattern_and_an_integer_alone(schema, arguments, expected):
    assert argument_problems(schema, arguments) == expected


def test_every_tools_schema_is_one_argument_problems_reads():
    kinds = {"string", "object", "integer", "boolean", "array"}
    for tool in TOOLS.values():
        for described in tool["inputSchema"]["properties"].values():
            assert described["type"] in kinds


@pytest.mark.parametrize(
    ("save_as", "named", "expected"),
    [
        ("bodies/ids-001.json", ["bodies/ids-001.json"], "ok"),
        ("lookups/lookup-001.json", ["bodies/x.json", "lookups/lookup-001.json"], "ok"),
        ("bodies/ids-002.json", ["bodies/ids-001.json"], "not_named"),
        ("bodies/ids-001.json", [], "not_named"),
        ("./bodies/ids-001.json", ["bodies/ids-001.json"], "not_named"),
        ("../x.json", ["../x.json"], "outside_run"),
        ("bodies/../../x.json", ["bodies/../../x.json"], "outside_run"),
        ("/etc/passwd", ["/etc/passwd"], "outside_run"),
        ("bodies\\..\\x.json", ["bodies\\..\\x.json"], "outside_run"),
        ("C:/x.json", ["C:/x.json"], "outside_run"),
        ("bodies/x\x00.json", ["bodies/x\x00.json"], "outside_run"),
        ("", [""], "outside_run"),
        (None, [None], "outside_run"),
        (["bodies/x.json"], ["bodies/x.json"], "outside_run"),
    ],
)
def test_save_target_admits_only_a_named_path_inside_the_run(save_as, named, expected):
    assert save_target(save_as, named) == expected


# ── the search preview through scope ────────────────────────────────────────────────────────────────────


def test_scope_with_the_request_previews_the_search_and_reads_no_trial(tmp_path):
    requests = []

    def registry(request):
        requests.append(request)
        return httpx.Response(500)

    http = httpx.Client(base_url=API_BASE, transport=httpx.MockTransport(registry))
    client = Client(tmp_path / "runs", get=rxnav_get, http=http, sleep=lambda s: None)
    document, is_error = client.call("scope", run="r", request=PD1_IN_LUNG, mode="direct")
    folder = tmp_path / "runs" / "r"
    held = json.loads((folder / "resolution.json").read_text(encoding="utf-8"))
    assert is_error is False and requests == []
    assert document["status"] == PREVIEWED and document["exit"] == 0
    assert document["meaning"] == PREVIEW_MEANING
    assert document["scope"] == held and document["in_words"] == scope_words(held)
    assert "Phase: Phase 3" in document["in_words"] and "with_these_tools" not in document
    assert not (folder / "landscape.json").exists() and not (folder / "fetches.json").exists()
    # read back without the request; then landscape gathers exactly that search
    again, is_error = client.call("scope", run="r")
    assert is_error is False and again == {
        "tool": "scope",
        "run_folder": str(folder.resolve()),
        "scope": held,
        "in_words": scope_words(held),
    }
    direct = Client(tmp_path / "runs", get=rxnav_get, http=registry_client(), sleep=lambda s: None)
    done, failed = direct.call("landscape", run="r", request=PD1_IN_LUNG, mode="direct")
    assert failed is False and done["status"] == "complete"
    record = json.loads((folder / "landscape.json").read_text(encoding="utf-8"))
    assert record["scope"] == held


def test_scope_previews_in_relay_mode_through_save_fetch(tmp_path):
    client = Client(tmp_path / "runs", probe_get=sandbox)
    for _round in range(20):
        document, is_error = client.call("scope", run="r", request=PD1_IN_LUNG)
        if document["status"] != "awaiting_fetch":
            break
        assert is_error is False and document["exit"] == 3 and document["mode"] == "relay"
        for fetch in document["fetches"]:
            url = httpx.URL(fetch["url"])
            assert url.host == "rxnav.nlm.nih.gov"
            status, body = rxnav_get(str(url.copy_with(query=None)), dict(url.params))
            client.call("save_fetch", run="r", save_as=fetch["save_as"], body=json.dumps(body))
    assert is_error is False and document["status"] == PREVIEWED and document["in_words"]
    assert not (tmp_path / "runs" / "r" / "bodies" / "version-start.json").exists()


def test_scope_refuses_a_changed_request_and_a_request_by_name(tmp_path):
    client = Client(tmp_path / "runs", get=rxnav_get, sleep=lambda s: None)
    client.call("scope", run="r", request=PD1_IN_LUNG, mode="direct")
    changed = {**PD1_IN_LUNG, "phase": ["PHASE2"]}
    document, is_error = client.call("scope", run="r", request=changed, mode="direct")
    assert is_error is True and document["status"] == "request_differs" and document["exit"] == 2
    assert document["with_these_tools"] == TOOL_TERMS
    document, is_error = client.call("scope", run="e", request={}, mode="direct")
    assert is_error is True and document["status"] == "request_refused"
    (tmp_path / "runs" / "taken").write_text("a file", encoding="utf-8")
    sandboxed = Client(tmp_path / "runs", probe_get=sandbox)
    document, is_error = sandboxed.call("scope", run="taken", request=PD1_IN_LUNG)
    assert is_error is True and document["status"] == "mode_unavailable"
    assert document["with_these_tools"] == NOT_WRITABLE_WORDS


# ── the record, schema 4, through the tool ──────────────────────────────────────────────────────────────


def placed(tmp_path, record=None):
    """A client whose run folder r holds the schema-4 fixture record (tests/schema3_record.py)."""
    folder = tmp_path / "runs" / "r"
    folder.mkdir(parents=True)
    held = schema3_record() if record is None else record
    (folder / "landscape.json").write_text(json.dumps(held), encoding="utf-8")
    return Client(tmp_path / "runs"), held


def test_record_serves_the_manifest_statuses_and_a_study_by_its_plain_nct(tmp_path):
    client, held = placed(tmp_path)
    manifest, is_error = client.call("record", run="r", part="manifest")
    assert is_error is False and manifest["manifest"] == {
        key: held[key] for key in ("schema_version", "request", "manifest")
    }
    statuses, _ = client.call("record", run="r", part="statuses")
    assert statuses["statuses"] == {"statuses": held["statuses"], "envelope": held["envelope"]}
    study, is_error = client.call("record", run="r", part="study", nct="NCT01030536")
    assert is_error is False and study == {
        "tool": "record",
        "run_folder": str((tmp_path / "runs" / "r").resolve()),
        "part": "study",
        "study": {key: held["studies"][1][key] for key in list(held["studies"][1])[:RECORD_PAGE_LIMIT]},
        "page": {
            "offset": 0,
            "limit": RECORD_PAGE_LIMIT,
            "returned": min(RECORD_PAGE_LIMIT, len(held["studies"][1])),
            "total": len(held["studies"][1]),
            "next_offset": RECORD_PAGE_LIMIT if len(held["studies"][1]) > RECORD_PAGE_LIMIT else None,
        },
    }
    complete = dict(study["study"])
    following = study["page"]["next_offset"]
    while following is not None:
        rest, failed = client.call("record", run="r", part="study", nct="NCT01030536", offset=following)
        assert failed is False
        if rest.get("navigation") == "addresses":
            for entry in rest["entries"]:
                code, exact = pointer_value(held, entry["address"])
                assert code == "ok" and entry["key"] not in complete
                complete[entry["key"]] = exact
        else:
            assert not complete.keys() & rest["study"].keys()
            complete.update(rest["study"])
        following = rest["page"]["next_offset"]
    assert complete == held["studies"][1]
    # a study is paged by its fields, each page a part of its keys
    first, _ = client.call("record", run="r", part="study", nct="NCT01030536", limit=3)
    keys = list(held["studies"][1])
    assert list(first["study"]) == keys[:3] and first["page"]["next_offset"] == 3


def test_record_pages_the_studies_as_the_contracts_example_shows(tmp_path):
    client, held = placed(tmp_path)
    first, is_error = client.call("record", run="r", part="studies", limit=2)
    assert is_error is False
    assert first["page"] == {"offset": 0, "limit": 2, "returned": 2, "total": 3, "next_offset": 2}
    assert [line["nct"] for line in first["studies"]] == ["NCT04852770", "NCT01030536"]
    rest, _ = client.call("record", run="r", part="studies", offset=2, limit=2)
    assert rest["page"] == {"offset": 2, "limit": 2, "returned": 1, "total": 3, "next_offset": None}
    assert rest["studies"][0]["nct"] == THIRD
    # the contract's own example page: its page, and every value it shows, are the ones served
    example = json.loads((EXAMPLES / "mcp_paging.json").read_text(encoding="utf-8"))
    assert example["page"] == first["page"]
    for shown, line in zip(example["studies"], first["studies"], strict=True):
        assert {key: line[key] for key in shown} == shown


def test_record_serves_only_the_studies_part_fields_on_a_line(tmp_path):
    client, held = placed(tmp_path)
    page, _ = client.call("record", run="r", part="studies")
    line = page["studies"][1]
    served = [f.name.removeprefix("studies[].") for f in FIELDS if ("mcp", "studies") in f.consumers]
    assert list(line) == list(dict.fromkeys(name.split(".")[0].removesuffix("[]") for name in served))
    assert line["lead_sponsor"] == {"name": "MedImmune LLC"}  # the name, never the class
    assert line["start_date"] == {"date": "2010-02-15", "type": "ACTUAL"}
    assert line["results_posted"] == held["studies"][1]["results_posted"]


@pytest.mark.parametrize("part", ["findings", "questions", "cohort"])
def test_record_rejects_removed_analysis_parts(tmp_path, part):
    client, _held = placed(tmp_path)
    result, failed = client.call("record", run="r", part=part)
    assert failed is True and result["refused"] == "not_allowed"
    assert record_view(schema3_record(), {"part": part}) == ("unknown_part", {})


def test_record_resolves_a_workbook_rows_address_to_its_value(tmp_path):
    client, held = placed(tmp_path)
    address = "/studies/1/adverse_events/events/0"
    document, is_error = client.call("record", run="r", part="address", address=address)
    assert is_error is False and document["address"] == address
    assert document["value"] == held["studies"][1]["adverse_events"]["events"][0]
    assert document["page"]["total"] == len(document["value"])  # an object is paged by its keys
    one, _ = client.call("record", run="r", part="address", address="/studies/1/enrollment/count")
    assert one["value"] == 23 and "page" not in one
    listed, _ = client.call("record", run="r", part="address", address="/studies", limit=1, offset=1)
    assert listed["navigation"] == "addresses" and "value" not in listed
    assert listed["entries"] == [{"address": "/studies/1", "index": 1, "kind": "object"}]
    assert listed["page"]["next_offset"] == 2
    assert pointer_value(held, listed["entries"][0]["address"]) == ("ok", held["studies"][1])


def test_record_pages_the_fields_by_field(tmp_path):
    client, held = placed(tmp_path)
    page, _ = client.call("record", run="r", part="fields")
    names = list(held["fields"])
    assert list(page["fields"]) == names[:RECORD_PAGE_LIMIT]
    assert page["page"]["total"] == len(names) > RECORD_PAGE_LIMIT


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        ({"part": "study"}, "nct_needed"),
        ({"part": "study", "nct": "NCT99999999"}, "no_such_study"),
        ({"part": "address"}, "address_needed"),
        ({"part": "address", "address": "studies/0"}, "not_a_pointer"),
        ({"part": "address", "address": "/studies/3"}, "outside_record"),
        ({"part": "address", "address": "/studies/01"}, "outside_record"),
        ({"part": "address", "address": "/nothing"}, "outside_record"),
        ({"part": "studies", "offset": 3}, "offset_out_of_range"),
        ({"part": "studies", "offset": -1}, "offset_out_of_range"),
        ({"part": "studies", "limit": 0}, "limit_out_of_range"),
        ({"part": "fields", "limit": RECORD_PAGE_LIMIT + 1}, "limit_out_of_range"),
    ],
)
def test_record_refuses_by_name_in_plain_words(tmp_path, arguments, error):
    client, held = placed(tmp_path)
    document, is_error = client.call("record", run="r", **arguments)
    assert is_error is True and document["error"] == error and document["why"] == RECORD_WORDS[error]
    if error == "no_such_study":
        assert document["held"] == [study["nct"] for study in held["studies"]]


def test_record_refuses_a_record_of_another_schema_and_one_not_there(tmp_path):
    client, _ = placed(tmp_path, {**schema3_record(), "schema_version": "2"})
    document, is_error = client.call("record", run="r", part="manifest")
    assert is_error is True and document["error"] == "schema_not_4" and "new run name" in document["why"]
    document, is_error = client.call("record", run="nothing", part="manifest")
    assert is_error is True and document["error"] == "no_record"
    document, is_error = client.call("record", run="r", part="cohort")
    assert is_error is True and document["refused"] == "not_allowed"
    document, is_error = client.call("record", run="r", part="study", nct="nct01234567")
    assert is_error is True and document["refused"] == "not_allowed"


def test_every_part_serves_what_the_contract_names_it_for():
    named = {rest[0] for f in FIELDS for kind, *rest in f.consumers if kind == "mcp"}
    assert named <= set(RECORD_PARTS)
    assert RECORD_PARTS == ("manifest", "studies", "study", "statuses", "fields", "address", "source")
    assert MANIFEST_KEYS == ("schema_version", "request", "manifest")
    assert STATUS_KEYS == ("statuses", "envelope")


def test_every_part_answers_on_a_real_record(tmp_path):
    client = Client(tmp_path / "runs", get=rxnav_get, http=registry_client(), sleep=lambda s: None)
    done, failed = client.call("landscape", run="r", request=PD1_IN_LUNG, mode="direct")
    assert failed is False and done["status"] == "complete"
    held = json.loads((tmp_path / "runs" / "r" / "landscape.json").read_text(encoding="utf-8"))
    assert held["schema_version"] == contract.SCHEMA_VERSION
    nct = held["studies"][1]["nct"]
    for arguments in (
        {"part": "manifest"},
        {"part": "statuses"},
        {"part": "fields"},
        {"part": "studies"},
        {"part": "study", "nct": nct},
        {"part": "address", "address": "/studies/1"},
    ):
        document, is_error = client.call("record", run="r", **arguments)
        assert is_error is False, (arguments, document)
    manifest, _ = client.call("record", run="r", part="manifest")
    assert manifest["manifest"] == {key: held.get(key) for key in MANIFEST_KEYS}
    studies, _ = client.call("record", run="r", part="studies")
    assert [line["nct"] for line in studies["studies"]] == [study["nct"] for study in held["studies"]]
    assert [line["overall_status"] for line in studies["studies"]] == [
        study["overall_status"] for study in held["studies"]
    ]
    study, _ = client.call("record", run="r", part="study", nct=nct)
    assert study["study"] == {
        key: held["studies"][1][key] for key in list(held["studies"][1])[:RECORD_PAGE_LIMIT]
    }
    fields, _ = client.call("record", run="r", part="fields", limit=RECORD_PAGE_LIMIT)
    assert fields["page"]["total"] == len(held["fields"])


# ── the record's decisions, directly ────────────────────────────────────────────────────────────────────


def window(offset, limit, returned, total, following):
    return {"offset": offset, "limit": limit, "returned": returned, "total": total, "next_offset": following}


@pytest.mark.parametrize(
    ("total", "offset", "limit", "expected"),
    [
        (3, 0, 2, ("ok", window(0, 2, 2, 3, 2))),
        (3, 2, 2, ("ok", window(2, 2, 1, 3, None))),
        (3, 0, 3, ("ok", window(0, 3, 3, 3, None))),
        (0, 0, 1, ("ok", window(0, 1, 0, 0, None))),
        (60, 0, RECORD_PAGE_LIMIT, ("ok", window(0, 50, 50, 60, 50))),
        (3, 3, 2, ("offset_out_of_range", {})),
        (0, 1, 2, ("offset_out_of_range", {})),
        (3, -1, 2, ("offset_out_of_range", {})),
        (3, 0, 0, ("limit_out_of_range", {})),
        (3, 0, RECORD_PAGE_LIMIT + 1, ("limit_out_of_range", {})),
    ],
)
def test_page_window(total, offset, limit, expected):
    assert page_window(total, offset, limit) == expected


DOCUMENT = {"a": [{"b/c": 1, "d~e": 2, "": 3}, [10, 20]], "n": None, "s": "text"}


@pytest.mark.parametrize(
    ("pointer", "expected"),
    [
        ("/a/0/b~1c", ("ok", 1)),
        ("/a/0/d~0e", ("ok", 2)),
        ("/a/0/", ("ok", 3)),
        ("/a/1/1", ("ok", 20)),
        ("/n", ("ok", None)),
        ("/a", ("ok", DOCUMENT["a"])),
        ("/a/2", ("outside_record", None)),
        ("/a/01", ("outside_record", None)),
        ("/a/-", ("outside_record", None)),
        ("/a/x", ("outside_record", None)),
        ("/s/0", ("outside_record", None)),
        ("/n/x", ("outside_record", None)),
        ("/b", ("outside_record", None)),
        ("/a/0/b~2c", ("not_a_pointer", None)),
        ("/a/0/b~", ("not_a_pointer", None)),
        ("a/0", ("not_a_pointer", None)),
        ("", ("not_a_pointer", None)),
        (["a"], ("not_a_pointer", None)),
        (None, ("not_a_pointer", None)),
    ],
)
def test_pointer_value(pointer, expected):
    assert pointer_value(DOCUMENT, pointer) == expected


def test_study_line_keeps_source_status_objects_and_missing_nested_fields():
    absent = {"status": "not_stated", "note": "not_reported"}
    unresolved = {"status": "unresolved", "note": "inconsistent source results state"}
    line = study_line(
        {"nct": "N", "lead_sponsor": absent, "results_posted": unresolved, "start_date": {"date": "x"}}
    )
    assert line["lead_sponsor"] == absent and line["results_posted"] == unresolved
    assert line["start_date"] == {"date": "x", "type": None}
    assert line["enrollment"] is None
    assert list(line) == list(
        dict.fromkeys(name.split(".")[0].removesuffix("[]") for name in mcp_server.STUDY_LINE)
    )


EMPTY = window(0, RECORD_PAGE_LIMIT, 0, 0, None)


@pytest.mark.parametrize(
    ("record", "arguments", "expected"),
    [
        (None, {"part": "manifest"}, ("not_a_record", {})),
        ({"studies": {}}, {"part": "manifest"}, ("not_a_record", {})),
        ({"studies": [1]}, {"part": "manifest"}, ("not_a_record", {})),
        ({"schema_version": 3, "studies": []}, {"part": "manifest"}, ("schema_not_4", {})),
        ({"schema_version": 4, "studies": []}, {"part": "cohort"}, ("unknown_part", {})),
        ({"schema_version": 4, "studies": []}, {"part": "fields"}, ("ok", {"fields": None})),
        (
            {"schema_version": 4, "studies": [], "fields": []},
            {"part": "fields"},
            ("ok", {"fields": [], "page": EMPTY}),
        ),
        (
            {"schema_version": 4, "studies": [{"nct": "N"}]},
            {"part": "address", "address": "/studies/0/nct"},
            ("ok", {"address": "/studies/0/nct", "value": "N"}),
        ),
    ],
)
def test_record_view_reads_what_a_record_holds_and_refuses_by_name(record, arguments, expected):
    assert record_view(record, arguments) == expected


def test_study_list_keeps_browse_leaves_as_an_actual_array_not_a_template_key():
    leaves = [{"id": "M123", "name": "Declared disease", "as_found": "Declared disease", "relevance": "HIGH"}]
    code, reply = record_view(
        {"schema_version": 4, "studies": [{"nct": "NCT1", "condition_browse_leaves": leaves}]},
        {"part": "studies"},
    )
    assert code == "ok"
    assert reply["studies"][0]["condition_browse_leaves"] == leaves
    assert "condition_browse_leaves[]" not in reply["studies"][0]


def test_record_studies_page_retains_reporting_status_through_tools(tmp_path):
    held = schema3_record()
    state = {"status": "unresolved", "note": "inconsistent source results state"}
    held["studies"][0]["results_posted"] = state
    client, _ = placed(tmp_path, held)
    page, failed = client.call("record", run="r", part="studies", limit=1)
    assert failed is False and page["studies"][0]["results_posted"] == state
    assert page["page"]["next_offset"] == 1
