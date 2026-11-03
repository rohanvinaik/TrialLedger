"""Accepted contradictions survive withheld extra criteria; rejected profiles do not.

All clinical values are invented. The saved ECOG fixtures are the independent reader's complete requests.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from TrialLedger import cli
from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import design_bounds, evidence_requests, evidence_requests_guide, run
from TrialLedger.mcp_server import Context, call_tool

FIXTURES = Path(__file__).parent / "witness_direction_fixtures"
WITHHELD = ["proposed_refused:x", "unresolved_assertion:x", "unresolved_rule:x", "conflicting:x"]


def request(sign="accepted"):
    return json.loads(
        (
            FIXTURES
            / ("accepted-ecog4-request.json" if sign == "accepted" else "rejected-ecog2-request.json")
        ).read_text()
    )


@pytest.mark.parametrize("blocker", WITHHELD)
def test_accepted_refutation_uses_admitted_necessary_conjunct(blocker):
    assert design_bounds.witness_verdict("witness", "REFUTED", [blocker], "accepted") == "ruled_out"
    assert design_bounds.witness_verdict("witness", "REFUTED", [blocker]) == "ruled_out"
    assert design_bounds.witness_verdict("witness", "REFUTED", [blocker], "rejected") == "unresolved"


@pytest.mark.parametrize(
    "result", ["ENTAILED", "UNDETERMINED", "OUT_OF_SCOPE", "UNSUPPORTED_QUERY", "future"]
)
@pytest.mark.parametrize("direction", ["accepted", "rejected"])
def test_withheld_criterion_is_not_a_blanket_permission_to_ignore_uncertainty(result, direction):
    assert design_bounds.witness_verdict("witness", result, ["proposed_refused:x"], direction) == "unresolved"


@pytest.mark.parametrize(
    "blocker",
    [
        "resource_bound",
        "opaque:x",
        "open_scope:cohort_ref:A",
        "unresolved_scope:x",
        "unresolved_literal:x",
        "unspecified_boundary:x",
        "profile_inconsistent",
        "future_cause:x",
        "proposed_refused_future:x",
        "unresolved_rule",
    ],
)
@pytest.mark.parametrize("direction", ["accepted", "rejected"])
def test_limits_binding_profile_query_and_unknown_causes_must_not_eliminate(blocker, direction):
    assert (
        design_bounds.witness_verdict("witness", "REFUTED", ["proposed_refused:x", blocker], direction)
        == "unresolved"
    )


@pytest.mark.parametrize(
    "support,expected",
    [
        ("no_witness", "not_ruled_out"),
        ("proposed_refused", "unresolved"),
        ("binding_unresolved", "unresolved"),
        ("future", "unresolved"),
    ],
)
def test_witness_support_is_never_promoted(support, expected):
    assert design_bounds.witness_verdict(support, "REFUTED", ["proposed_refused:x"], "accepted") == expected


def test_accepted_ecog4_elimination_keeps_full_raw_blockers_proof_and_known_standing():
    answer = run(request())
    assert answer["code"] == "complete"
    candidate = answer["result"]["candidates"][1]
    witness = candidate["observations"][0]
    assert candidate["state"] == "ruled_out"
    assert candidate["elimination_status"] == "known"
    assert witness["status"] == "known"
    assert witness["decision"]["result"] == "REFUTED"
    assert witness["decision"]["proof"] == ("p-ecog",)
    assert witness["decision"]["blockers"] == ("proposed_refused:p-marker",)
    assert answer["result"]["consequence"]["result"] == "CONFLICT"
    assert answer["result"]["consequence"]["status"] == "known"
    findings = answer["metadata"]["findings"]
    assert any(v["logical_result"] == "ruled_out" and v["standing"] == "known" for v in findings)


def test_rejected_ecog2_remains_open_because_unknown_marker_could_explain_rejection():
    answer = run(request("rejected"))
    candidate = answer["result"]["candidates"][1]
    assert candidate["state"] == "unresolved"
    assert candidate["observations"][0]["decision"]["result"] == "UNDETERMINED"
    assert candidate["observations"][0]["decision"]["blockers"] == ("proposed_refused:p-marker",)
    assert "elimination_status" not in candidate


@pytest.mark.parametrize(
    "mutation",
    [
        "zero_count",
        "unknown_budget",
        "proposed_observation",
        "proposed_bridge",
        "wrong_scope",
        "resource_bound",
        "opaque",
        "impossible_profile",
    ],
)
def test_real_observation_gates_must_not_be_bypassed(mutation):
    payload = request()
    observation = payload["observations"][0]
    if mutation == "zero_count":
        observation["count"] = 0
    elif mutation == "unknown_budget":
        observation["bridge"]["resolution"] = "unresolved"
    elif mutation == "proposed_observation":
        observation["status"] = "proposed"
    elif mutation == "proposed_bridge":
        observation["bridge"]["status"] = "proposed"
    elif mutation == "wrong_scope":
        for candidate in payload["candidates"]:
            candidate["assertions"][0]["cohort"] = {"class": "Scope", "kind": "cohort_ref", "ref": "A"}
        observation["context"] = {"cohort": "B"}
    elif mutation == "resource_bound":
        payload["bound"] = 1
    elif mutation == "opaque":
        observation["body"] = json.loads(a.canonical(a.Opaque("unknown-profile")))
    else:
        body = deepcopy(observation["body"])
        observation["body"] = {"class": "AllOf", "parts": [body, {"class": "Not", "part": body}]}
    answer = run(payload)
    assert answer["code"] == "complete", answer
    assert all(v["state"] != "ruled_out" for v in answer["result"]["candidates"])


def test_elimination_standing_flows_to_common_consequence_without_pending_marker_poison():
    payload = request()
    floor = deepcopy(payload["candidates"][0]["assertions"][0])
    floor["id"] = "survivor-floor"
    floor["body"]["value"].update(comparison="ge", number=4)
    payload["candidates"].append({"id": "survivor", "assertions": [floor]})
    payload["query"] = deepcopy(floor["body"])
    result = run(payload)["result"]
    assert result["remaining"] == ["survivor"]
    assert result["consequence"]["result"] == "ENTAILED"
    assert result["consequence"]["status"] == "known"
    payload["observations"][0]["bridge"]["status"] = "interpolated"
    assert run(payload)["result"]["consequence"]["status"] == "interpolated"


def test_corpus_remains_descriptive_and_has_no_witness_policy_dependency():
    example = run({"operation": "describe", "view": "corpus"})["result"]["example"]
    answer = run(example)
    assert answer["code"] == "complete"
    assert answer["result"]["frequency"]
    counts = [v for v in answer["metadata"]["findings"] if v["kind"] == "corpus_statistic"]
    assert counts
    assert all(v["disposition"] == "descriptive" for v in counts)


@pytest.mark.parametrize("sign", ["accepted", "rejected"])
def test_real_cli_and_mcp_keep_direction_and_warrants(sign, tmp_path, capsys):
    payload = request(sign)
    path = tmp_path / "request.json"
    path.write_text(json.dumps(payload))
    assert cli.main(["reason", "--request", str(path)]) == 0
    cli_answer = json.loads(capsys.readouterr().out)
    code, reply = call_tool(Context(tmp_path), {"name": "reason", "arguments": {"request": payload}})
    assert code == "ok" and not reply["isError"]
    mcp_answer = json.loads(reply["content"][0]["text"])
    expected = "ruled_out" if sign == "accepted" else "unresolved"
    for answer in [cli_answer, mcp_answer]:
        row = answer["result"]["candidates"][1]
        assert row["state"] == expected
        assert row["observations"][0]["decision"]["blockers"] == ["proposed_refused:p-marker"]


def test_evidence_search_passes_each_sign_explicitly(monkeypatch):
    payload = evidence_requests_guide.example()
    seen = []
    owner = evidence_requests.witness_verdict

    def capture(support, result, blockers, direction=None):
        assert direction in ("accepted", "rejected")
        seen.append(direction)
        return owner(support, result, blockers, direction)

    monkeypatch.setattr(evidence_requests, "witness_verdict", capture)
    evidence_requests.evaluate(payload)
    assert set(seen) == {"accepted", "rejected"}


def test_unknown_exception_budget_is_not_coerced_to_zero_witness_exceptions():
    payload = request()
    payload["observations"][0]["bridge"]["max_exceptions"] = None
    answer = run(payload)
    assert answer["code"] == "refused" and answer["result"] is None
    assert answer["problems"]


def test_unknown_witness_direction_cannot_eliminate_a_candidate():
    assert design_bounds.witness_verdict("witness", "REFUTED", [], "unknown") == "unresolved"
