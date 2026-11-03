"""The managed session reaches real public transports and preserves local child warrants."""

import json
from copy import deepcopy

import pytest

from scripts.trace_reasoning_consumers import invoke
from TrialLedger.layer2 import design_session_guide as guide
from TrialLedger.layer2 import run


def pointer(value, path):
    for part in path.removeprefix("/").split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


@pytest.mark.parametrize("snapshot_request", [guide.EXAMPLE, guide.REVISION_EXAMPLE])
def test_complete_session_findings_point_to_actual_local_results_and_warrants(snapshot_request):
    request = snapshot_request
    before = deepcopy(request)
    response = run(request)
    assert response["code"] == "complete", response
    assert request == before
    assert response["metadata"]["kind"] == "reasoning"
    assert any(row["kind"] == "session_decision" for row in response["metadata"]["findings"])
    for finding in response["metadata"]["findings"]:
        assert finding["completion"] != "unclassified" and finding["disposition"] != "unclassified"
        for field in ("path", "raw_path", "support_path"):
            if field in finding:
                pointer(response, finding[field])
    decision = response["result"]["decisions"][0]
    assert decision["standing"] == "known"
    assert decision["origin_refs"] and decision["input_origins"]


def test_focused_discovery_exposes_exact_shapes_and_actual_revision():
    response = run({"operation": "describe", "view": "design_session"})
    assert response["code"] == "complete", response
    description = response["result"]
    assert description["example"]["operation"] == "design_session"
    assert run(description["example"])["result"]["decisions"][0]["code"] == "design_choice"
    revision = run(description["revision_example"])
    assert revision["result"]["decisions"][0]["code"] == "settled_within_declared_alternatives"
    assert revision["previous_fresh"] and revision["diff"] and revision["work"]["analyses"] == 5


def test_empty_session_is_inspection_and_not_clinical_validation():
    request = deepcopy(guide.EXAMPLE)
    request["session"].update(premises=[], analyses=[], decisions=[])
    response = run(request)
    assert response["code"] == "complete", response
    assert response["metadata"] == {"version": 1, "kind": "inspection", "findings": []}
    assert response["work"]["analyses"] == 0


def test_historical_source_origin_cannot_be_claimed_for_a_user_choice():
    request = deepcopy(guide.EXAMPLE)
    request["session"]["premises"][0]["origin"].update(kind="source_rule")
    response = run(request)
    assert response["code"] == "refused"
    assert response["problems"] == ["source_rule_requires_compiled_assertion"]
    assert response["metadata"]["findings"][0]["disposition"] == "translation_question"


@pytest.mark.parametrize("mode", ["cli", "mcp"])
@pytest.mark.parametrize("snapshot_request", [guide.EXAMPLE, guide.REVISION_EXAMPLE])
def test_real_transports_keep_complete_session_and_revision(mode, snapshot_request, tmp_path):
    request = snapshot_request
    response = run(request)
    assert response["code"] == "complete", response
    assert invoke(request, mode, tmp_path) == json.loads(json.dumps(response))
