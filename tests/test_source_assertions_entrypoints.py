"""Raw NIH source bindings reach the public CLI and stdio MCP without source promotion."""

from __future__ import annotations

import copy
import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from TrialLedger import cli, warrants
from TrialLedger.layer2.interpretations_guide import frame, premise, quantity
from TrialLedger.layer2.source_assertions_guide import example

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "source-bridge"
SOURCE = ROOT / "tests" / "fixtures" / "ipass-registry.json"


def snapshot(folder):
    return {
        path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.rglob("*")
        if path.is_file()
    }


@pytest.fixture(params=["cli", "mcp"])
def invoke(request, tmp_path, monkeypatch, capsys):
    """Use actual commands and protocol dispatch while forbidding clinical network fetches."""
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "landscape.json").write_text('{"source":"unchanged"}')
    (reports / "landscape.xlsx").write_bytes(b"unchanged workbook")
    (reports / "raw.json").write_bytes(SOURCE.read_bytes())
    original = snapshot(reports)
    fixture_bytes = SOURCE.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("source-bound reasoning must not fetch evidence")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(httpx.Client, "send", forbidden)

    def call(payload):
        supplied = copy.deepcopy(payload)
        if request.param == "cli":
            path = tmp_path / "request.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
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
                            "clientInfo": {"name": "source-bridge-test", "version": "1"},
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
                assert result["refused"] == "wrong_type"
            else:
                assert reply["isError"] is (result["code"] == "refused")
        assert payload == supplied
        assert snapshot(reports) == original
        assert SOURCE.read_bytes() == fixture_bytes
        return result

    return call


def read_request(name):
    return json.loads((EXAMPLES / (name + "-request.json")).read_text())


def analysis(result):
    return result["analyses"][0]["result"]


def rows(result):
    return {row["id"]: row for row in result["interpretations"]}


def rebind(request):
    """A deliberately changed test source needs an explicitly revised content identity."""
    digest = warrants.study_digest(request["study"])
    request["expected_digest"] = digest
    for anchor in request.get("anchors", []):
        anchor["digest"] = digest
    return digest


def test_discovery_example_runs_with_source_and_hypotheses_separate(invoke):
    description = invoke({"operation": "describe", "view": "source_assertions", "detail": "full"})
    assert description["code"] == "complete"
    guide = description["result"]
    envelope = invoke(guide["example"])
    assert envelope["code"] == "complete"
    result = envelope["result"]
    assert set(guide["result_guide"]["fields"]) == set(result)
    assert guide["input_shapes"]["source_anchor"]["required"] == ["id", "address", "digest", "expected"]
    assert guide["answer_guide"]["source_assertions"]["refused"][0] == "translation"
    computed = analysis(result)
    assert computed["remaining"] == ["adults"]
    assert computed["refuted"] == ["under-18"]
    assert computed["fixed"]["queries"][0]["result"] == "ENTAILED"
    assert result["interpretations"][0]["assumptions"][0]["status"] == "proposed"
    assert result["fixed"]["assertions"][0]["status"] == "known"


def test_complete_saved_packet_reproduces_without_changing_evidence(invoke):
    original = snapshot(EXAMPLES)
    paths = sorted(EXAMPLES.glob("*-request.json"))
    assert len(paths) == 3
    for path in paths:
        actual = invoke(json.loads(path.read_text()))
        expected = path.with_name(path.name.replace("-request.json", "-result.json"))
        assert actual == json.loads(expected.read_text()), path.name
    assert snapshot(EXAMPLES) == original


def test_structured_registry_age_bounds_queries_without_certifying_a_protocol(invoke):
    result = invoke(read_request("ipass-registered-age"))["result"]
    assert result["interpretations"] == []
    assert [row["operation"] for row in result["requests"]] == ["entailment", "entailment"]
    assert [row["result"]["decision"]["result"] for row in result["analyses"]] == ["ENTAILED", "REFUTED"]
    fixed = result["fixed"]["assertions"]
    assert len(fixed) == 1
    assert fixed[0]["rule"]["id"] == "ctg-structured-general-eligibility-age"
    assert fixed[0]["criterion_ref"].endswith("/protocolSection/eligibilityModule/minimumAge")
    assert result["source"]["version"] == warrants.study_digest(read_request("ipass-registered-age")["study"])
    assert any(row["code"] == "unresolved_retained" for row in result["coverage"])


def test_exact_baseline_counts_hydrate_a_conditional_overlap_not_an_exact_cutoff(invoke):
    request = read_request("ipass-baseline-overlap")
    result = invoke(request)["result"]
    assert result["submitted"]["interpretations"] == request["interpretations"]
    prepared = result["interpretations"][0]["signals"][0]
    assert prepared["data"]["total"] == 1217
    assert [row["lower"] for row in prepared["data"]["marginals"]] == [126, 1140]
    assert prepared["support"][0]["status"] == "proposed"
    assert result["bindings"][0]["status"] == "proposed"
    assert result["bindings"][0]["sources"][0]["address"] == request["anchors"][0]["address"]
    computed = analysis(result)
    reading = rows(computed)["aligned-baseline-counts"]
    signal = reading["signals"][0]
    assert signal["value"]["counts"][0] == {"id": "intersection", "lower": 49, "upper": 126}
    assert signal["status"] == "proposed"
    assert signal["guarantee"] == "conditional_on_interpretation"
    assert signal["assumed_bindings"] == ["same-baseline-universe"]
    assert computed["consequences"][0]["result"] == "ENTAILED"
    assert computed["consequences"][1]["result"] == "UNDETERMINED"


@pytest.mark.parametrize("field", ["population", "arm", "time", "version"])
def test_wrong_population_time_or_edition_preserves_math_and_blocks_application(invoke, field):
    request = read_request("ipass-baseline-overlap")
    request["interpretations"][0]["binding_uses"][0]["scope"][field] = "unbound-other-" + field
    result = analysis(invoke(request)["result"])
    assert result["refuted"] == []
    assert result["unresolved"] == ["aligned-baseline-counts"]
    row = rows(result)["aligned-baseline-counts"]
    signal = row["signals"][0]
    assert signal["code"] == "unresolved"
    assert signal["value"]["counts"][0] == {"id": "intersection", "lower": 49, "upper": 126}
    assert "scope_mismatch:same-baseline-universe" in signal["blockers"]
    assert result["consequences"][0]["result"] == "ENTAILED"


def test_whole_schedule_passage_preserves_rival_proposed_windows(invoke):
    request = read_request("ipass-schedule-readings")
    result = invoke(request)["result"]
    original = request["study"]["protocolSection"]["outcomesModule"]["primaryOutcomes"][0]["timeFrame"]
    assert result["anchors"][0]["span"] == {"start": 0, "end": len(original), "text": original}
    assert result["submitted"]["interpretations"][0]["basis"][1] == {
        "$source": "whole-schedule-passage",
        "as": "text",
    }
    computed = analysis(result)
    assert computed["remaining"] == ["randomization-anchored", "successive-gaps"]
    for reading, expected_second in zip(computed["interpretations"], [(77, 91), (70, 98)], strict=True):
        signal = reading["signals"][0]
        assert signal["status"] == "proposed"
        assert signal["guarantee"] == "conditional_on_interpretation"
        bounds = {
            (row["before"], row["after"]): (row["lower"], row["upper"]) for row in signal["value"]["bounds"]
        }
        assert bounds[("randomization", "first_nominal_target")] == (42, 42)
        assert bounds[("randomization", "second_nominal_target")] == (84, 84)
        assert bounds[("randomization", "first_permitted_assessment")] == (35, 49)
        assert bounds[("randomization", "second_permitted_assessment")] == expected_second


def test_day40_first_assessment_fits_without_changing_the_nominal_target(invoke):
    request = read_request("ipass-schedule-readings")
    for reading in request["interpretations"]:
        reading["signal_claims"] = [
            {
                "signal": "scheduled-assessments",
                "claim": {
                    "before": "randomization",
                    "after": "first_permitted_assessment",
                    "lower": 40,
                    "upper": 40,
                    "lower_inclusive": True,
                    "upper_inclusive": True,
                },
            }
        ]
    result = analysis(invoke(request)["result"])
    assert result["remaining"] == ["randomization-anchored", "successive-gaps"]
    for reading in result["interpretations"]:
        check = reading["signal_checks"][0]
        assert check["calculation_code"] == "consistent"
        bounds = {
            (row["before"], row["after"]): (row["lower"], row["upper"]) for row in check["value"]["bounds"]
        }
        assert bounds[("randomization", "first_permitted_assessment")] == (40, 40)
        assert bounds[("randomization", "first_nominal_target")] == (42, 42)
        assert bounds[("randomization", "second_nominal_target")] == (84, 84)


def test_second_visit_day72_depends_on_which_schedule_anchor_is_meant(invoke):
    request = read_request("ipass-schedule-readings")
    for reading in request["interpretations"]:
        reading["signal_claims"] = [
            {
                "signal": "scheduled-assessments",
                "claim": {
                    "before": "randomization",
                    "after": "second_permitted_assessment",
                    "lower": 72,
                    "upper": 72,
                    "lower_inclusive": True,
                    "upper_inclusive": True,
                },
            }
        ]
    result = analysis(invoke(request)["result"])
    readings = rows(result)
    anchored = readings["randomization-anchored"]
    rolling = readings["successive-gaps"]
    assert anchored["signal_checks"][0]["calculation_code"] == "conflict"
    assert anchored["state"] == "incoherent"
    assert rolling["signal_checks"][0]["calculation_code"] == "consistent"
    assert rolling["state"] == "compatible"
    assert result["consequences"][0]["result"] == "ENTAILED"


def test_source_origin_and_known_labels_do_not_promote_a_reading(invoke):
    request = example()
    request["interpretations"][0]["origin"] = "source"
    request["interpretations"][0]["assumptions"][0]["status"] = "known"
    prepared = invoke(request)["result"]["interpretations"][0]["assumptions"][0]
    assert prepared["status"] == "proposed"
    ordinary = invoke(
        {"operation": "entailment", "assertions": [prepared], "query": request["queries"][0]["body"]}
    )
    decision = ordinary["result"]["decision"]
    assert decision["result"] == "UNDETERMINED"
    assert "proposed_refused:adult-reading" in decision["blockers"]


def test_known_signal_and_binding_labels_remain_hypotheses(invoke):
    request = read_request("ipass-baseline-overlap")
    request["bindings"][0]["status"] = "known"
    request["interpretations"][0]["signals"][0]["support"][0]["status"] = "known"
    result = invoke(request)["result"]
    assert result["bindings"][0]["status"] == "proposed"
    assert result["interpretations"][0]["signals"][0]["support"][0]["status"] == "proposed"
    assert analysis(result)["interpretations"][0]["signals"][0]["status"] == "proposed"


@pytest.mark.parametrize("owner", ["frame", "binding"])
def test_templates_cannot_hide_undeclared_source_dependencies(invoke, owner):
    request = read_request("ipass-baseline-overlap")
    if owner == "frame":
        request["interpretations"][0]["anchors"].remove("PS2-count")
    else:
        request["bindings"][0]["anchors"].remove("PS2-count")
        request["bindings"][0]["basis"].append({"$source": "PS2-count", "as": "text"})
    result = invoke(request)
    assert result["code"] == "refused" and result["result"] is None
    assert result["problems"]


def test_hypothetical_or_and_are_preserved_and_produce_distinct_consequences(invoke):
    request = example()
    alternatives = [quantity("age", "ge", 65, "Years"), quantity("WHO_PS", "le", 2, "WHO_PS")]
    frames = []
    for identity, kind in (("either", "AnyOf"), ("both", "AllOf")):
        reading = frame(identity, identity, [premise(identity, {"class": kind, "parts": alternatives})])
        reading["anchors"] = ["eligibility-passage"]
        frames.append(reading)
    request["interpretations"] = frames
    request["queries"] = [{"id": "PS3", "body": quantity("WHO_PS", "eq", 3, "WHO_PS")}]
    result = invoke(request)["result"]
    assert [row["assumptions"][0]["body"]["class"] for row in result["interpretations"]] == ["AnyOf", "AllOf"]
    computed = rows(analysis(result))
    assert computed["either"]["queries"][0]["decision"]["result"] == "UNDETERMINED"
    assert computed["both"]["queries"][0]["decision"]["result"] == "REFUTED"


def test_inspection_only_does_not_pretend_to_run_a_design_check(invoke):
    request = example()
    request["queries"] = []
    result = invoke(request)["result"]
    assert result["requests"] == result["analyses"] == []
    assert result["fixed"]["assertions"][0]["status"] == "known"
    assert result["interpretations"][0]["assumptions"][0]["status"] == "proposed"


@pytest.mark.parametrize(
    "kind",
    ["overlap", "partition", "summary", "population", "temporal", "regimen", "relations", "dependencies"],
)
@pytest.mark.parametrize("resolution", ["resolved", "unresolved"])
def test_every_signal_channel_preserves_structure_and_proposed_admission(invoke, kind, resolution):
    discovered = invoke({"operation": "describe", "view": "signals", "detail": "full"})["result"]
    original = copy.deepcopy(discovered["signal_examples"][kind]["signals"][0])
    assert original["support"][0]["status"] == "known"
    original["support"][0]["resolution"] = resolution
    # This optional predicate tests representation conservation, not a clinical predicate binding.
    original["bindings"] = {
        "invented-measurement": quantity("invented-measurement", "ge", 5, "invented-unit")
    }
    context = (
        "INVENTED full teaching context, not a real NIH trial or a clinical source warrant. "
        "The following typed hypothesis, including its population, time, role, definition edition and "
        "predicate meanings, is explicitly invented for bridge admission testing:\n"
        + json.dumps(original, ensure_ascii=False, sort_keys=True)
    )
    study = {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT00000002",
                "briefTitle": "INVENTED bridge contract teaching record",
            },
            "eligibilityModule": {"minimumAge": "18 Years"},
            "descriptionModule": {"detailedDescription": context},
        }
    }
    digest = warrants.study_digest(study)
    reading = frame("invented-" + kind + "-reading", "Invented " + kind + " hypothesis", [])
    reading["anchors"] = ["invented-full-context"]
    reading["signals"] = [original]
    reading["basis"] = ["invented:typed-hypothesis-not-registry-evidence-or-confirmed-clinical-meaning"]
    request = {
        "operation": "source_assertions",
        "study": study,
        "expected_digest": digest,
        "anchors": [
            {
                "id": "invented-full-context",
                "address": "/protocolSection/descriptionModule/detailedDescription",
                "digest": digest,
                "expected": context,
                "span": {"start": 0, "end": len(context), "text": context},
            }
        ],
        "interpretations": [reading],
        "queries": [{"id": "invented-record-adult", "body": quantity("age", "ge", 18, "Years")}],
    }
    result = invoke(request)["result"]
    assert result["submitted"]["interpretations"] == request["interpretations"]
    assert result["anchors"][0]["span"]["text"] == context
    assert result["fixed"]["signals"] == []
    assert [row["id"] for row in result["fixed"]["assertions"]] == ["registry-age-minimumAge"]
    prepared = result["interpretations"][0]["signals"][0]
    assert prepared["data"] == original["data"]
    for key in ("subject", "predicate", "value", "polarity", "qualifiers", "time"):
        assert (
            prepared["bindings"]["invented-measurement"][key]
            == original["bindings"]["invented-measurement"][key]
        )
    assert prepared["support"][0]["status"] == "proposed"
    assert prepared["support"][0]["resolution"] == resolution
    assert result["anchors"][0]["ref"] in prepared["support"][0]["basis"]
    computed = analysis(result)
    emitted = computed["interpretations"][0]["signals"][0]
    # The existing public operator supplies the comparison; this test implements no operator rule.
    reference_signal = copy.deepcopy(original)
    reference_signal["support"][0]["resolution"] = "resolved"
    reference = invoke({"operation": "signals", "signals": [reference_signal]})["result"]["signals"][0]
    assert emitted["value"] == reference["value"]
    assert emitted["calculation_code"] == reference["calculation_code"]
    assert emitted["rule"] == reference["rule"]
    assert emitted["status"] == "proposed"
    assert emitted["guarantee"] == "conditional_on_interpretation"
    assert computed["interpretations"][0]["premises"]["signals"][0]["data"] == original["data"]
    assert computed["refuted"] == computed["incoherent"] == []
    assert computed["consequences"][0]["result"] == "ENTAILED"
    if resolution == "unresolved":
        assert emitted["code"] == "unresolved"
        assert computed["unresolved"] == [reading["id"]]
        assert emitted["blockers"]


@pytest.mark.parametrize("value", [None, True, 18.0, "18.0", "1,140", " 18", "18 Years"])
def test_numeric_hydration_refuses_coercion_and_unit_guessing(invoke, value):
    request = example()
    request["study"]["testValue"] = value
    digest = rebind(request)
    request["anchors"].append({"id": "number", "address": "/testValue", "digest": digest, "expected": value})
    request["queries"][0]["body"]["value"]["number"] = {"$source": "number", "as": "integer"}
    result = invoke(request)
    assert result["code"] == "refused" and result["result"] is None
    assert "invalid_integer:source_marker" in json.dumps(result["problems"])


@pytest.mark.parametrize("value", [None, "", "N/A", "18.0 Years", "18 years", "18 Years or older", False])
def test_unsupported_age_structure_does_not_become_a_clinical_restriction(invoke, value):
    request = example()
    request["study"]["protocolSection"]["eligibilityModule"]["minimumAge"] = value
    rebind(request)
    request["interpretations"] = []
    result = invoke(request)["result"]
    assert result["fixed"]["assertions"] == []
    assert result["analyses"][0]["result"]["decision"]["result"] == "UNDETERMINED"
    assert result["coverage"][0]["code"] != "compiled"


@pytest.mark.parametrize(
    "mutation",
    [
        "top-null",
        "study-null",
        "anchors-null",
        "frames-null",
        "bindings-null",
        "queries-null",
        "caller-fixed",
        "unknown-top-field",
        "stale-source",
        "stale-anchor",
        "missing-pointer",
        "wrong-expected-type",
        "wrong-span",
        "byte-offset-span",
        "anchor-unknown-field",
        "duplicate-anchor",
        "unknown-frame-anchor",
        "frame-anchors-empty",
        "template-unknown-field",
    ],
)
def test_translation_failures_are_named_refusals_never_clinical_refutations(invoke, mutation):
    request = example()
    if mutation == "top-null":
        request = None
    elif mutation.endswith("-null"):
        key = {"frames": "interpretations"}.get(mutation[:-5], mutation[:-5])
        request[key] = None
    elif mutation == "caller-fixed":
        request["fixed"] = {"assertions": []}
    elif mutation == "unknown-top-field":
        request["clinical_verdict"] = "eligible"
    elif mutation == "stale-source":
        request["study"]["protocolSection"]["eligibilityModule"]["minimumAge"] = "19 Years"
    elif mutation == "stale-anchor":
        request["anchors"][0]["digest"] = "stale"
    elif mutation == "missing-pointer":
        request["anchors"][0]["address"] = "/missing"
    elif mutation == "wrong-expected-type":
        request["anchors"][0]["expected"] = True
    elif mutation == "wrong-span":
        request["anchors"][0]["span"]["text"] += "changed"
    elif mutation == "byte-offset-span":
        text = "α🙂 adults"
        request["study"]["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = text
        rebind(request)
        request["anchors"][0]["expected"] = text
        request["anchors"][0]["span"] = {"start": 0, "end": len(text.encode()), "text": text}
    elif mutation == "anchor-unknown-field":
        request["anchors"][0]["clinical_meaning"] = "known"
    elif mutation == "duplicate-anchor":
        request["anchors"].append(copy.deepcopy(request["anchors"][0]))
    elif mutation == "unknown-frame-anchor":
        request["interpretations"][0]["anchors"] = ["missing"]
    elif mutation == "frame-anchors-empty":
        request["interpretations"][0]["anchors"] = []
    else:
        request["queries"][0]["body"]["value"]["number"] = {
            "$source": "eligibility-passage",
            "as": "integer",
            "normalize": True,
        }
    result = invoke(request)
    if mutation == "top-null" and "refused" in result:
        assert result["refused"] == "wrong_type"
    else:
        assert result["code"] == "refused" and result["result"] is None
        assert result["problems"]


def test_fresh_process_cli_and_stdio_mcp_return_complete_identical_json(tmp_path):
    request = example()
    path = tmp_path / "request.json"
    path.write_text(json.dumps(request), encoding="utf-8")
    before = path.read_bytes()
    command = subprocess.run(
        [sys.executable, "-m", "TrialLedger", "reason", "--request", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1"},
        },
    }
    call = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "reason", "arguments": {"request": request}},
    }
    protocol = subprocess.run(
        [sys.executable, "-m", "TrialLedger", "mcp", "--root", str(tmp_path / "reports")],
        input=json.dumps(initialize) + "\n" + json.dumps(call) + "\n",
        capture_output=True,
        text=True,
        check=True,
    )
    replies = [json.loads(line) for line in protocol.stdout.splitlines()]
    assert len(replies) == 2
    result = json.loads(replies[1]["result"]["content"][0]["text"])
    assert result.pop("tool") == "reason"
    assert result == json.loads(command.stdout)
    assert path.read_bytes() == before
    assert command.stderr == protocol.stderr == ""
