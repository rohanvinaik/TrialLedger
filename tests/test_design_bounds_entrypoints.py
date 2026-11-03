"""Source -> report/address -> explicitly bound witness -> real CLI/MCP -> revised design answer.

IPASS is a retained development example. Its table bindings and eligibility bridge below are explicit
test premises, not an automatic compiler or independent confirmation of its actual protocol cutoff.
"""

from __future__ import annotations

import copy
import hashlib
import json
import socket
from pathlib import Path

import httpx
import pytest

from TrialLedger import cli, landscape, readout
from TrialLedger.layer2 import assertions as a
from TrialLedger.mcp_server import TOOLS, Context, call_tool, record_view

SOURCE = Path(__file__).parent / "fixtures" / "ipass-registry.json"


def model(item):
    return json.loads(a.canonical(item))


def who_ps(comparison, number):
    return a.Literal(
        a.Subject("participant"),
        a.Predicate("measurement", "WHO_PS"),
        a.Value("quantity", comparison, number=number, unit="WHO_PS"),
    )


def source_bound_request(record):
    # These exact addresses were read and manually bound for this development fixture. No title classifier.
    base = record["studies"][0]["baseline"]
    measure = base["measures"][5]
    category = measure["classes"][2]
    cell = category["categories"][0]["measurements"][2]
    denominator = base["denominators"][0]["counts"][2]
    assert measure["title"] == "WHO performance status" and measure["unit"] == "Participants"
    assert category["title"] == "2 (in bed =< 50% of the time)"
    assert cell["group"] == denominator["group"] == "BG002"
    assert base["groups"][2]["description"] == "Total of all reporting groups"
    address = "/studies/0/baseline/measures/5/classes/2/categories/0/measurements/2/value"
    code, view = record_view(record, {"part": "address", "address": address})
    assert code == "ok" and view["value"] == cell["value"] == "126"
    candidates = []
    for cutoff in range(5):
        identity = f"upper_{cutoff}"
        assertion = a.ScopedAssertion(
            identity,
            "test:declared-candidate-not-protocol-fact",
            "required",
            who_ps("le", cutoff),
            rule=a.Rule("test-candidate", "1", warrants=("test:finite-candidate-family",)),
            status="known",
            resolution="resolved",
        )
        candidates.append({"id": identity, "assertions": [model(assertion)]})
    candidates.append({"id": "no_ps_restriction", "assertions": []})
    return {
        "operation": "design_bounds",
        "study_ref": "NCT00322452:sha256:" + record["studies"][0]["digest"],
        "candidates": candidates,
        "observations": [
            {
                "id": "WHO_PS_2",
                "count": int(cell["value"]),
                "denominator": int(denominator["value"]),
                "population": "NCT00322452:baseline:BG002",
                "context": {},
                "status": "known",
                "body": model(who_ps("eq", 2)),
                "basis": [address, "/studies/0/baseline/denominators/0/counts/2", "/studies/0/digest"],
                "bridge": {
                    "status": "interpolated",
                    "resolution": "resolved",
                    "max_exceptions": 0,
                    "basis": [
                        "test:assume-PS-category-is-participant-count-and-aligned-to-eligibility-assessment",
                        "test:assume-at-least-one-PS2-participant-met-applicable-criteria-via-zero-exceptions",
                    ],
                },
            }
        ],
        "query": model(who_ps("le", 2)),
    }


@pytest.fixture
def retained_report(tmp_path):
    source = json.loads(SOURCE.read_bytes())
    manifest = landscape.landscape_manifest(
        [source], "fixture", "retained-development-example", "test", {}, landscape.RULE_VERSIONS
    )
    record = landscape.landscape_record([source], {}, {}, manifest)
    folder = tmp_path / "ipass"
    folder.mkdir()
    (folder / "landscape.json").write_text(json.dumps(record))
    readout.write_book(record, folder / "landscape.xlsx")
    assert readout.book_problems(record, folder / "landscape.xlsx") == []
    return folder, record


@pytest.fixture(autouse=True)
def network_forbidden(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("reason must not fetch or enrich sources")

    monkeypatch.setattr(socket.socket, "connect", fail)
    monkeypatch.setattr(httpx.Client, "send", fail)


def snapshot(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}


@pytest.mark.parametrize("surface", ["cli", "mcp"])
def test_ipass_bounds_reach_the_public_answers_and_recompute_on_revision(
    retained_report, tmp_path, capsys, surface
):
    folder, record = retained_report
    request = source_bound_request(record)
    before = snapshot(folder)

    def invoke(payload):
        if surface == "cli":
            path = tmp_path / "reason-request.json"
            path.write_text(json.dumps(payload))
            assert cli.main(["reason", "--request", str(path)]) == 0
            return json.loads(capsys.readouterr().out)["result"]
        code, reply = call_tool(Context(tmp_path), {"name": "reason", "arguments": {"request": payload}})
        assert code == "ok" and not reply["isError"]
        return json.loads(reply["content"][0]["text"])["result"]

    result = invoke(request)
    assert result["remaining"] == ["upper_2", "upper_3", "upper_4", "no_ps_restriction"]
    assert [row["state"] for row in result["candidates"][:2]] == ["ruled_out", "ruled_out"]
    assert result["candidates"][1]["observations"][0]["status"] == "interpolated"
    assert result["consequence"]["result"] == "UNDETERMINED"  # No recovery of exact cutoff 2.
    revised = copy.deepcopy(request)
    revised["observations"][0]["bridge"]["max_exceptions"] = 126
    assert len(invoke(revised)["remaining"]) == 6
    revised["observations"][0]["bridge"]["max_exceptions"] = 125
    assert invoke(revised)["remaining"] == result["remaining"]
    assert snapshot(folder) == before
    assert source_bound_request(record) == request


def test_mcp_advertises_the_new_operation_and_focused_discovery_to_clients():
    properties = TOOLS["reason"]["inputSchema"]["properties"]["request"]["properties"]
    assert "design_bounds" in properties["operation"]["enum"]
    assert "design_bounds" in properties["view"]["enum"]


def overlap_request(record):
    """Exact retained cells plus explicit same-universe/predicate/bridge premises; never a text classifier."""
    request = source_bound_request(record)
    base = record["studies"][0]["baseline"]
    smoking = base["measures"][4]
    assert smoking["title"] == "Smoking history" and smoking["unit"] == "Participants"
    assert smoking["classes"][0]["title"] == "Never Smoker"
    cell = smoking["classes"][0]["categories"][0]["measurements"][2]
    assert cell["group"] == "BG002" and cell["value"] == "1140"
    address = "/studies/0/baseline/measures/4/classes/0/categories/0/measurements/2/value"
    assert record_view(record, {"part": "address", "address": address})[1]["value"] == "1140"
    never = a.Literal(
        a.Subject("participant"), a.Predicate("demographic", "never_smoker"), a.Value("boolean")
    )
    joint = a.AllOf((who_ps("eq", 2), never))
    candidates = []
    for identity, modality, body in (("no_joint", "excluded", joint), ("requires_never", "required", never)):
        assertion = a.ScopedAssertion(
            identity,
            "test:declared-not-protocol",
            modality,
            body,
            rule=a.Rule("test-candidate", "1", warrants=("test:finite-candidates",)),
            status="known",
            resolution="resolved",
        )
        candidates.append({"id": identity, "assertions": [model(assertion)]})
    old = request["observations"][0]
    universe = old["population"]
    request.update(
        candidates=candidates,
        query=model(never),
        signals=[
            {
                "id": "joint-count",
                "kind": "overlap",
                "data": {
                    "universe": universe,
                    "alignment": "confirmed",
                    "total": 1217,
                    "marginals": [
                        {"ref": "ps2", "universe": universe, "lower": 126, "upper": 126},
                        {"ref": "never", "universe": universe, "lower": 1140, "upper": 1140},
                    ],
                },
                "bindings": {"ps2": model(who_ps("eq", 2)), "never": model(never)},
                "support": [
                    {
                        "id": "retained-counts",
                        "status": "known",
                        "resolution": "resolved",
                        "basis": [*old["basis"], address],
                    },
                    {
                        "id": "same-universe",
                        "status": "interpolated",
                        "resolution": "resolved",
                        "basis": ["test:assume-exact-participant-counts-in-one-baseline-universe"],
                    },
                ],
            }
        ],
        observations=[
            {
                "id": "joint-witness",
                "denominator": 1217,
                "population": universe,
                "context": {},
                "bridge": copy.deepcopy(old["bridge"]),
                "derivation": {"signal": "joint-count", "witness": "intersection"},
            }
        ],
    )
    return request


@pytest.mark.parametrize("surface", ["cli", "mcp"])
def test_partial_bounds_reach_real_entrypoints_elimination_and_revised_consequences(
    retained_report, tmp_path, capsys, surface
):
    folder, record = retained_report
    before = snapshot(folder)
    request = overlap_request(record)

    def invoke(payload):
        if surface == "cli":
            path = tmp_path / "partial-request.json"
            path.write_text(json.dumps(payload))
            assert cli.main(["reason", "--request", str(path)]) == 0
            return json.loads(capsys.readouterr().out)["result"]
        code, reply = call_tool(Context(tmp_path), {"name": "reason", "arguments": {"request": payload}})
        assert code == "ok" and not reply["isError"]
        return json.loads(reply["content"][0]["text"])["result"]

    result = invoke(request)
    assert result["signals"][0]["value"]["counts"] == [{"id": "intersection", "lower": 49, "upper": 126}]
    assert result["remaining"] == ["requires_never"]
    assert result["consequence"]["result"] == "ENTAILED"
    assert result["consequence"]["status"] == "interpolated"
    witness = result["candidates"][0]["observations"][0]
    assert witness["bounds"] == {"lower": 49, "upper": 126}
    assert witness["derivation"]["rule"] == "numeric.overlap:1"
    assert request["signals"][0]["support"][0]["basis"] == result["signals"][0]["support"][0]["basis"]
    revised = copy.deepcopy(request)
    revised["observations"][0]["bridge"]["max_exceptions"] = 49
    assert invoke(revised)["consequence"]["result"] == "UNDETERMINED"
    revised["observations"][0]["bridge"]["max_exceptions"] = 48
    assert invoke(revised)["remaining"] == ["requires_never"]
    revised = copy.deepcopy(request)
    revised["signals"][0]["data"]["alignment"] = "unresolved"
    unknown = invoke(revised)
    assert unknown["remaining"] == ["no_joint", "requires_never"]
    assert unknown["consequence"]["result"] == "UNDETERMINED"
    assert unknown["candidates"][0]["observations"][0]["bounds"] == {"lower": None, "upper": None}
    revised = copy.deepcopy(request)
    revised["signals"][0]["support"][1]["status"] = "proposed"
    assert invoke(revised)["consequence"]["result"] == "UNDETERMINED"
    assert snapshot(folder) == before
    assert overlap_request(record) == request


def test_partial_signal_operation_is_advertised_in_mcp():
    props = TOOLS["reason"]["inputSchema"]["properties"]["request"]["properties"]
    assert "signals" in props["operation"]["enum"] and "signals" in props["view"]["enum"]
