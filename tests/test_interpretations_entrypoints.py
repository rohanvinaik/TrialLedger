"""Named clinical obligations reach both public boundaries without source promotion."""

from __future__ import annotations

import copy
import hashlib
import json
import socket
from pathlib import Path

import httpx
import pytest

from TrialLedger import cli
from TrialLedger.layer2.interpretations_guide import example, frame, premise, quantity

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "interpretations"


def snapshot(folder):
    return {
        path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.rglob("*")
        if path.is_file()
    }


@pytest.fixture(params=["cli", "mcp"])
def invoke(request, tmp_path, monkeypatch, capsys):
    """Exercise the command or complete stdio MCP request, preserving supplied report bytes."""
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "landscape.json").write_text('{"source":"unchanged"}')
    (reports / "landscape.xlsx").write_bytes(b"unchanged workbook")
    (reports / "raw.json").write_text('{"retained":"unchanged"}')
    original = snapshot(reports)

    def forbidden(*args, **kwargs):
        raise AssertionError("interpretation reasoning must never fetch clinical evidence")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)

    def call(payload):
        supplied = copy.deepcopy(payload)
        if request.param == "cli":
            path = tmp_path / "request.json"
            path.write_text(json.dumps(payload))
            code = cli.main(["reason", "--request", str(path)])
            captured = capsys.readouterr()
            assert captured.err == ""
            result = json.loads(captured.out)
            assert code == (2 if result["code"] == "refused" else 0)
        else:
            written = []
            lines = [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-11-25",
                            "capabilities": {},
                            "clientInfo": {"name": "interpretations-test", "version": "1"},
                        },
                    }
                ).encode(),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "reason", "arguments": {"request": payload}},
                    }
                ).encode(),
            ]
            assert cli.main(["mcp", "--root", str(reports)], mcp_streams=(lines, written.append)) == 0
            assert len(written) == 2
            reply = json.loads(written[1])["result"]
            result = json.loads(reply["content"][0]["text"])
            assert result.pop("tool") == "reason"
            if "code" not in result:
                assert payload is None and reply["isError"]
                assert result["refused"] == "wrong_type" and result["arguments"] == ["request"]
            else:
                assert reply["isError"] is (result["code"] == "refused")
        assert payload == supplied
        assert snapshot(reports) == original
        return result

    return call


def read_request(name):
    return json.loads((EXAMPLES / (name + "-request.json")).read_text())


def rows(result):
    return {row["id"]: row for row in result["interpretations"]}


def questions(result):
    return {row["id"]: row for row in result["consequences"]}


def test_focused_discovery_exposes_a_runnable_conditional_workflow(invoke):
    discovery = invoke({"operation": "describe", "view": "interpretations"})
    assert discovery["code"] == "complete"
    guide = discovery["result"]
    result = invoke(guide["example"])
    assert result["code"] == "complete"
    assert set(guide["result_guide"]["fields"]) == set(result["result"])
    assert guide["answer_guide"]["interpretations"]["conditional"]
    assert guide["input_shapes"]["interpretation"]["fields"]["assumptions"]
    assert result["result"]["remaining"] == ["PS0-2", "PS0-3"]
    assert result["result"]["refuted"] == ["under-18"]


def test_saved_continuing_session_is_reproducible_and_does_not_touch_evidence(invoke):
    before = snapshot(EXAMPLES)
    paths = sorted(EXAMPLES.glob("*-request.json"))
    assert len(paths) == 7
    for path in paths:
        result = invoke(json.loads(path.read_text()))
        expected = path.with_name(path.name.replace("-request.json", "-result.json"))
        assert result == json.loads(expected.read_text()), path.name
    assert snapshot(EXAMPLES) == before


def test_rival_ps_choices_remain_separate_and_selection_recomputes(invoke):
    original = invoke(read_request("draft-choices"))["result"]
    choices = rows(original)
    assert choices["PS0-2"]["state"] == choices["PS0-3"]["state"] == "compatible"
    assert choices["PS0-2"]["queries"][1]["decision"]["result"] == "REFUTED"
    assert choices["PS0-3"]["queries"][1]["decision"]["result"] == "UNDETERMINED"
    assert questions(original)["PS3"]["result"] == "UNDETERMINED"
    assert questions(original)["adult"]["warrant"]["guarantee"] == "fixed_floor"
    assert choices["PS0-2"]["premises"]["assumptions"][0]["status"] == "proposed"
    narrow = invoke(read_request("draft-selected-PS0-2"))["result"]
    wide = invoke(read_request("draft-revised-PS0-3"))["result"]
    assert narrow["selection"] == {"id": "PS0-2", "state": "selected", "origin": "user_choice"}
    assert questions(narrow)["PS3"]["result"] == "REFUTED"
    assert questions(wide)["PS3"]["result"] == "UNDETERMINED"
    assert len(wide["interpretations"]) == len(original["interpretations"])
    refused = read_request("draft-choices")
    refused["selected"] = "under-18"
    result = invoke(refused)["result"]
    assert result["selection"]["state"] == "refused"
    assert questions(result)["PS3"]["result"] == "UNDETERMINED"


def test_scheduled_and_actual_unscheduled_assessments_do_not_share_an_event(invoke):
    result = invoke(read_request("assessment-roles"))["result"]
    choices = rows(result)
    assert choices["scheduled-42"]["state"] == "compatible"
    assert choices["scheduled-49"]["state"] == "compatible"
    assert choices["scheduled-28"]["state"] == "refuted"
    assert choices["unscheduled-28"]["state"] == "compatible"
    assert choices["scheduled-28"]["signal_checks"][0]["calculation_code"] == "conflict"
    assert choices["unscheduled-28"]["signal_checks"][0]["calculation_code"] == "consistent"


def test_unknown_population_binding_retains_math_without_wrong_elimination(invoke):
    unknown = invoke(read_request("population-unresolved"))["result"]
    known = invoke(read_request("population-resolved"))["result"]
    assert unknown["remaining"] == ["aligned-EFQ", "everyone-in-EFQ"]
    assert unknown["unresolved"] == unknown["remaining"]
    assert unknown["fixed"]["signals"][0]["value"]["counts"][2] == {"id": "outside", "lower": 40, "upper": 40}
    check = rows(unknown)["everyone-in-EFQ"]["signal_checks"][0]
    assert check["code"] == "unresolved" and check["calculation_code"] == "conflict"
    assert questions(unknown)["adult"]["result"] == "ENTAILED"
    assert known["remaining"] == ["aligned-EFQ"]
    assert known["refuted"] == ["everyone-in-EFQ"]
    assert questions(known)["PS3"]["warrant"]["guarantee"] == "conditional_on_declared_family_not_exhaustive"
    assert questions(known)["PS3"]["warrant"]["status"] == "proposed"


def test_scope_mismatch_blocks_application_without_falsifying_a_design(invoke):
    request = read_request("population-resolved")
    for reading in request["interpretations"]:
        reading["binding_uses"][0]["scope"]["arm"] = "unbound-other-arm"
    result = invoke(request)["result"]
    assert result["refuted"] == []
    assert result["unresolved"] == ["aligned-EFQ", "everyone-in-EFQ"]
    assert questions(result)["adult"]["result"] == "ENTAILED"
    assert rows(result)["everyone-in-EFQ"]["signal_checks"][0]["calculation_code"] == "conflict"


def test_adopted_observed_definition_distinguishes_unknown_imputed_and_unavailable(invoke):
    result = invoke(read_request("endpoint-inputs"))["result"]
    choices = rows(result)
    assert choices["observed-week12"]["state"] == "compatible"
    assert choices["imputed-week12"]["state"] == "unresolved"
    assert choices["no-observed-week12"]["state"] == "refuted"
    assert questions(result)["adult"]["result"] == "ENTAILED"
    wrong_edition = read_request("endpoint-inputs")
    wrong_edition["bindings"][0]["scope"]["version"] = "invented:other-definition"
    for reading in wrong_edition["interpretations"]:
        reading["binding_uses"][0]["scope"]["version"] = "invented:other-definition"
    revised = invoke(wrong_edition)["result"]
    assert revised["refuted"] == []
    assert "no-observed-week12" in revised["unresolved"]


def test_proposed_hypothesis_is_never_admitted_to_ordinary_entailment(invoke):
    request = example()
    original = copy.deepcopy(request)
    hypothetical = invoke(request)["result"]
    assert hypothetical["remaining"] == ["PS0-2", "PS0-3"]
    assertion = request["interpretations"][0]["assumptions"][0]
    ordinary = invoke(
        {"operation": "entailment", "assertions": [assertion], "query": request["queries"][1]["body"]}
    )
    decision = ordinary["result"]["decision"]
    assert decision["result"] == "UNDETERMINED"
    assert "proposed_refused:PS-upper-2" in decision["blockers"]
    assert request == original


def test_conflicting_fixed_floor_prevents_explosion(invoke):
    request = example()
    contradiction = copy.deepcopy(request["interpretations"][2]["assumptions"][0])
    contradiction["status"] = "known"
    request["fixed"]["assertions"].append(contradiction)
    request["interpretations"] = request["interpretations"][:2]
    result = invoke(request)["result"]
    assert all(row["state"] == "floor_conflict" for row in result["interpretations"])
    assert all(query["result"] == "CONFLICT" for query in result["consequences"])


def test_hypothetical_or_is_not_flattened_into_and(invoke):
    request = example()
    parts = [quantity("age", "ge", 65, "Years"), quantity("ECOG", "le", 2, "ECOG")]
    request["interpretations"] = [
        frame(
            "either",
            "Age at least 65 or ECOG at most 2",
            [premise("either-rule", {"class": "AnyOf", "parts": parts})],
        ),
        frame(
            "both",
            "Age at least 65 and ECOG at most 2",
            [premise("both-rule", {"class": "AllOf", "parts": parts})],
        ),
    ]
    result = invoke(request)["result"]
    choices = rows(result)
    assert choices["either"]["state"] == choices["both"]["state"] == "compatible"
    assert choices["either"]["queries"][1]["decision"]["result"] == "UNDETERMINED"
    assert choices["both"]["queries"][1]["decision"]["result"] == "REFUTED"
    assert questions(result)["PS3"]["result"] == "UNDETERMINED"


@pytest.mark.parametrize("bound", [0, True, 65537])
def test_invalid_computation_bound_is_refused(invoke, bound):
    request = example()
    request["bound"] = bound
    result = invoke(request)
    assert result["code"] == "refused" and result["problems"]


def test_exhausted_computation_retains_rivals_without_false_refutation(invoke):
    request = example()
    request["bound"] = 1
    result = invoke(request)["result"]
    assert result["refuted"] == []
    assert result["unresolved"] == result["remaining"] == ["PS0-2", "PS0-3", "under-18"]
    assert "resource_bound" in result["fixed"]["blockers"]
    assert all(query["result"] == "UNDETERMINED" for query in result["consequences"])


@pytest.mark.parametrize(
    "mutation",
    [
        "fixed-null",
        "bindings-null",
        "frames-null",
        "queries-empty",
        "frame-unknown-field",
        "query-unknown-field",
        "duplicate-frame",
        "duplicate-query",
        "duplicate-assumption",
        "invalid-origin",
        "unknown-selection",
        "unknown-signal-claim",
        "top-null",
        "top-unknown-field",
        "floor-unknown-field",
        "frame-null",
        "query-null",
    ],
)
def test_malformed_or_ambiguous_requests_are_named_refusals(invoke, mutation):
    request = example()
    if mutation == "top-null":
        request = None
    elif mutation == "top-unknown-field":
        request["verdict"] = "compatible"
    elif mutation == "floor-unknown-field":
        request["fixed"]["certified"] = True
    elif mutation == "frame-null":
        request["interpretations"][0] = None
    elif mutation == "query-null":
        request["queries"][0] = None
    elif mutation == "fixed-null":
        request["fixed"] = None
    elif mutation == "bindings-null":
        request["bindings"] = None
    elif mutation == "frames-null":
        request["interpretations"] = None
    elif mutation == "queries-empty":
        request["queries"] = []
    elif mutation == "frame-unknown-field":
        request["interpretations"][0]["verdict"] = "compatible"
    elif mutation == "query-unknown-field":
        request["queries"][0]["answer"] = "ENTAILED"
    elif mutation == "duplicate-frame":
        request["interpretations"].append(copy.deepcopy(request["interpretations"][0]))
    elif mutation == "duplicate-query":
        request["queries"].append(copy.deepcopy(request["queries"][0]))
    elif mutation == "duplicate-assumption":
        request["interpretations"][0]["assumptions"] *= 2
    elif mutation == "invalid-origin":
        request["interpretations"][0]["origin"] = "model-certified"
    elif mutation == "unknown-selection":
        request["selected"] = "not-in-the-family"
    else:
        request["interpretations"][0]["signal_claims"] = [{"signal": "missing", "claim": {}}]
    result = invoke(request)
    if mutation == "top-null" and "refused" in result:
        assert result["refused"] == "wrong_type"
        return
    assert result["code"] == "refused" and result["result"] is None
    assert result["problems"]
