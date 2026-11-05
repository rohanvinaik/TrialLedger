"""Refusals keep their exact code and gain a located, bounded diagnostic; unknown locations say so."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from tests.test_protocol_mcp_lifecycle import McpClient
from TrialLedger import reasoning_artifacts
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.layer2 import refusal, run
from TrialLedger.layer2 import request_preparation as prepare

ROOT = Path(__file__).resolve().parents[1]
CLI = str(Path(sys.executable).with_name("trialledger"))


def literal(kind="measurement", key="ecog"):
    return {
        "class": "Literal",
        "subject": {"class": "Subject", "kind": "participant"},
        "predicate": {"class": "Predicate", "kind": kind, "key": key},
        "value": {"class": "Value", "kind": "quantity", "comparison": "le", "number": 1, "unit": "score"},
    }


def nested_request():
    return {
        "operation": "entailment",
        "assertions": [],
        "query": {"class": "AllOf", "parts": [literal(), literal("bogus")]},
    }


def diagnostic(response):
    assert response["code"] == "refused"
    (found,) = response["input_diagnostics"]
    return found


def test_nested_invalid_predicate_has_exact_pointer_vocabulary_and_reference():
    response = run(nested_request())
    assert response["problems"] == ["predicate_kind_outside_vocabulary"]
    found = diagnostic(response)
    assert found["pointer"] == "/query/parts/1/predicate/kind"
    assert found["rejected"] == {"type": "str", "value": "bogus"}
    assert "measurement" in found["expected"]["vocabulary"] and "bogus" not in found["expected"]["vocabulary"]
    assert found["reference"] == {"operation": "describe", "view": "entailment", "detail": "schema"}
    assert found["input"] == "request"


def test_invalid_predicate_in_a_decision_option_query_is_located_through_prepare():
    request = prepare.session_example()
    request["questions"][0]["options"][0]["query"]["predicate"]["kind"] = "bogus"
    response = run(request)
    assert response["problems"] == ["predicate_kind_outside_vocabulary"]
    found = diagnostic(response)
    assert found["pointer"] == "/questions/0/options/0/query/predicate/kind"
    assert found["expanded_pointer"] == "/request/session/decisions/0/alternatives/0/query/predicate/kind"


def test_canonical_session_option_refusal_has_no_invented_location():
    """The session validator names its own code and does not yet carry the located cause."""
    expanded = run(prepare.session_example())["result"]["request"]
    expanded["session"]["decisions"][0]["alternatives"][0]["query"]["predicate"]["kind"] = "bogus"
    response = run(expanded)
    assert response["problems"] == ["alternative_requires_exact_entailment_query"]
    assert "input_diagnostics" not in response


def test_identical_invalid_nodes_do_not_guess_one_location():
    bad = literal("bogus")
    request = {
        "operation": "entailment",
        "assertions": [],
        "query": {"class": "AllOf", "parts": [bad, deepcopy(bad)]},
    }
    found = diagnostic(run(request))
    assert found["pointer"] is None
    assert found["candidates"] == ["/query/parts/0/predicate/kind", "/query/parts/1/predicate/kind"]


def test_other_vocabulary_families_and_structure():
    value = literal()
    value["value"]["kind"] = "nonsense"
    request = {"operation": "entailment", "assertions": [], "query": value}
    found = diagnostic(run(request))
    assert (found["pointer"], found["rejected"]["value"]) == ("/query/value/kind", "nonsense")
    value["value"]["kind"] = "quantity"
    value["value"]["comparison"] = "in"
    found = diagnostic(run(request))
    assert found["pointer"] == "/query/value/comparison"
    assert "le" in found["expected"]["vocabulary"] and "in" not in found["expected"]["vocabulary"]
    value["value"]["comparison"] = "le"
    value["subject"]["kind"] = "robot"
    assert diagnostic(run(request))["pointer"] == "/query/subject/kind"
    value["subject"]["kind"] = "participant"
    value["predicate"]["colour"] = "red"
    found = diagnostic(run(request))
    assert (found["pointer"], found["rejected"]["value"]) == ("/query/predicate/colour", "colour")
    del value["predicate"]["colour"]
    del value["value"]
    found = diagnostic(run(request))
    assert found["expected"]["missing_fields"] == ["value"]
    assert found["pointer"] == "/query"


def test_operation_view_and_unknown_field_names():
    found = diagnostic(run({"operation": "nope"}))
    assert (found["pointer"], found["rejected"]["value"]) == ("/operation", "nope")
    assert "entailment" in found["expected"]["vocabulary"]
    found = diagnostic(run({"operation": "describe", "view": "nope"}))
    assert found["pointer"] == "/view" and "prepare" in found["expected"]["vocabulary"]
    found = diagnostic(run({"operation": "describe", "detail": "tiny"}))
    assert found["pointer"] == "/detail" and found["expected"]["vocabulary"] == ["card", "full", "schema"]
    found = diagnostic(run({"operation": "describe", "bogus": 1}))
    assert found["pointer"] == "/bogus"
    assert diagnostic(run([]))["pointer"] == ""


def test_unknown_location_is_explicit_and_codes_are_unchanged():
    response = run({"operation": "entailment", "assertions": "x", "query": literal()})
    assert response["problems"] == ["not_a_list:assertions"]
    found = diagnostic(response)
    assert found["pointer"] is None and found["note"] == refusal.UNKNOWN_NOTE
    # a refusal raised where no record exists carries no diagnostics at all
    bare = run({"operation": "entailment", "assertions": [], "query": literal(), "bound": -1})
    assert (
        bare["code"] == "refused" and "input_diagnostics" not in bare or diagnostic(bare)["pointer"] is None
    )


def test_rejected_value_is_bounded():
    request = nested_request()
    request["query"]["parts"][1]["predicate"]["kind"] = "x" * 5000
    found = diagnostic(run(request))
    assert len(found["rejected"]["value"]) == refusal.MAX_REJECTED and found["rejected"]["truncated"] is True
    assert len(json.dumps(found)) < 2000


def criterion(body):
    return {
        "id": "c",
        "modality": "required",
        "body": body,
        "origin": {"kind": "user_choice", "ref": "invented:brief"},
        "status": "known",
        "resolution": "resolved",
    }


def compact_literal(kind="condition_status"):
    return {"kind": "boolean", "predicate": {"kind": kind, "key": "flag"}}


def prepare_request(body, query):
    return {"operation": "prepare", "for": "entailment", "criteria": [criterion(body)], "query": query}


def test_prepare_names_the_submitted_compact_pointer_and_the_expanded_path():
    request = prepare_request({"all": [compact_literal(), compact_literal("bogus")]}, compact_literal())
    response = run(request)
    assert response["problems"] == ["predicate_kind_outside_vocabulary"]
    found = diagnostic(response)
    assert found["pointer"] == "/criteria/0/body/all/1/predicate/kind"
    assert found["input"] == "submitted_prepare_request"
    assert found["expanded_pointer"] == "/request/assertions/0/body/parts/1/predicate/kind"
    assert found["reference"]["view"] == "prepare"
    query_bad = run(
        prepare_request({"all": [compact_literal(), compact_literal()]}, compact_literal("bogus"))
    )
    assert diagnostic(query_bad)["pointer"] == "/query/predicate/kind"
    assert diagnostic(query_bad)["expanded_pointer"] == "/request/query/predicate/kind"


def test_prepare_compact_structure_and_value_family():
    request = prepare_request(compact_literal(), compact_literal())
    request["criteria"][0]["colour"] = 1
    found = diagnostic(run(request))
    assert found["pointer"] == "/criteria/0/colour"
    request = prepare_request(compact_literal(), compact_literal())
    request["query"]["kind"] = "weird"
    found = diagnostic(run(request))
    assert found["pointer"] == "/query/kind" and "boolean" in found["expected"]["vocabulary"]
    request = prepare_request(
        compact_literal(),
        {
            "kind": "quantity",
            "predicate": {"kind": "measurement", "key": "x"},
            "comparison": "in",
            "number": 1,
            "unit": "u",
            "inclusivity": "inclusive",
        },
    )
    found = diagnostic(run(request))
    assert found["pointer"] == "/query/comparison"


def test_invalid_predicate_in_a_protocol_assessment_condition_through_prepare():
    request = prepare.protocol_example()
    assessment = next(item for item in request["protocol"]["objects"] if item["kind"] == "assessment")
    assessment["data"]["condition"] = compact_literal("bogus")
    index = request["protocol"]["objects"].index(assessment)
    response = run(request)
    assert response["problems"] == ["predicate_kind_outside_vocabulary"]
    found = diagnostic(response)
    assert found["pointer"] == f"/protocol/objects/{index}/data/condition/predicate/kind"
    assert (
        found["expanded_pointer"]
        == f"/request/session/protocol/objects/{index}/data/condition/predicate/kind"
    )
    assert found["input"] == "submitted_prepare_request"
    assert found["rejected"]["value"] == "bogus"


def write(tmp_path, request, name="request.json"):
    path = tmp_path / name
    path.write_text(json.dumps(request))
    return path


def run_cli(path):
    done = subprocess.run([CLI, "reason", "--request", str(path)], capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 2, done.stderr or done.stdout
    return json.loads(done.stdout)


@pytest.mark.parametrize(
    "request_factory",
    [
        nested_request,
        lambda: prepare_request({"all": [compact_literal(), compact_literal("bogus")]}, compact_literal()),
        lambda: {"operation": "describe", "view": "nope"},
    ],
)
def test_run_cli_and_mcp_return_identical_diagnostics(tmp_path, request_factory):
    request = request_factory()
    direct = run(request)
    via_cli = run_cli(write(tmp_path, request))
    client = McpClient(tmp_path / "served")
    try:
        reply = client.send("tools/call", {"name": "reason", "arguments": {"request": request}})["result"]
        assert reply["isError"] is True
        via_mcp = json.loads(reply["content"][0]["text"])
    finally:
        client.close()
    assert direct["input_diagnostics"] == via_cli["input_diagnostics"] == via_mcp["input_diagnostics"]
    assert direct["problems"] == via_cli["problems"] == via_mcp["problems"]
    assert direct["input_diagnostics"][0]["pointer"] is not None


def test_a_prepared_request_run_by_id_names_its_pointer_in_the_request_as_run(tmp_path):
    good = run(prepare_request(compact_literal(), compact_literal()))
    assert good["code"] == "complete"
    expanded = deepcopy(good["result"]["request"])
    expanded["query"]["predicate"]["kind"] = "bogus"
    forged = deepcopy(good)
    forged["result"]["request"] = expanded
    store = tmp_path / "store"
    artifact = reasoning_artifacts.save(store, prepare_request(compact_literal(), compact_literal()), forged)
    reply = delivery.execute(None, store=store, prepared=artifact["id"])
    assert reply["problems"] == ["predicate_kind_outside_vocabulary"]
    found = diagnostic(reply)
    assert found["pointer"] == "/query/predicate/kind" and found["input"] == "request"


def test_no_diagnostics_on_success_or_unlocated_refusal_without_record():
    assert "input_diagnostics" not in run(prepare_request(compact_literal(), compact_literal()))
    refused = run({"operation": "entailment", "assertions": [], "query": literal(), "bound": 0})
    assert refused["code"] == "refused"
    assert "input_diagnostics" not in refused


def test_a_refused_compact_reply_still_fits_its_budget(tmp_path):
    from TrialLedger import clinical_delivery

    reply = delivery.execute(
        nested_request(), store=tmp_path / "store", response_view="compact", max_bytes=2048
    )
    assert reply["code"] == "refused" and reply["problems"] == ["predicate_kind_outside_vocabulary"]
    assert clinical_delivery.response_bytes(reply) <= 2048 - 128
    # the exact diagnostic stays retained at the artifact; compact names it as omitted
    stored = reasoning_artifacts.load(tmp_path / "store", reply["artifact"]["id"])
    assert stored["response"]["input_diagnostics"][0]["pointer"] == "/query/parts/1/predicate/kind"


def test_a_compact_refusal_carries_its_input_diagnostics_when_they_fit(tmp_path):
    """The repair pointer reaches the compact reply itself, not only the stored artifact."""
    reply = delivery.execute(nested_request(), store=tmp_path / "store", response_view="compact")
    assert reply["code"] == "refused"
    assert reply["input_diagnostics"][0]["pointer"] == "/query/parts/1/predicate/kind"
    assert "input_diagnostics" not in reply.get("omitted_fields", [])
