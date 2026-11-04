"""Public v2 preparation and discovery for protocol designs (task 2.6, C9)."""

import copy
import json
import subprocess
import sys
from pathlib import Path

from TrialLedger.layer2 import run

ROOT = Path(__file__).resolve().parents[1]
CLI = str(Path(sys.executable).with_name("trialledger"))


def _example() -> dict:
    card = run({"operation": "describe", "view": "protocol"})
    assert card["code"] == "complete", card
    return copy.deepcopy(card["result"]["example"])


def test_the_discovered_protocol_example_prepares_and_runs_through_the_public_operation():
    prepared = run(_example())
    assert prepared["code"] == "complete", prepared["problems"]
    request = prepared["result"]["request"]
    session = request["session"]
    assert session["schema_version"] == 2
    objects = {o["id"]: o for o in session["protocol"]["objects"]}
    assert objects["week12"]["depends_on"] == ["score"]
    assert objects["collection"]["depends_on"] == ["week12"]
    reply = run(request)
    assert reply["code"] == "complete", reply["problems"]
    rows = reply["result"]["protocol"]["checks"][0]["children"][0]["signals"][0]["claim_admission"]
    assert [row["outcome"] for row in rows] == ["satisfied", "not_collected", "uncovered"]
    assert all(row["admission"] != "accepted" for row in rows)


def test_every_administrative_default_is_disclosed_and_no_clinical_value_is_defaulted():
    defaults = run(_example())["result"]["defaults"]
    paths = {entry["path"] for entry in defaults}
    for field in ("scope", "standing", "support", "depends_on"):
        assert f"/request/session/protocol/objects/1/{field}" in paths
    assert "/request/session/protocol/checks/0/scope" in paths
    assert not any(path.endswith(("/required", "/claims", "/origin", "/version", "/data")) for path in paths)
    standing = next(e for e in defaults if e["path"] == "/request/session/protocol/objects/1/standing")
    assert standing["value"]["status"] == "proposed" and standing["value"]["resolution"] == "unresolved"


def test_claims_required_flags_and_origins_are_never_defaulted():
    for edit, problem in (
        (lambda p: p["checks"][0].pop("claims"), "protocol_check_claims_required:week12-schedule"),
        (lambda p: p["checks"][0].pop("required"), "missing_field:protocol.check"),
        (lambda p: p["objects"][0].pop("origin"), "missing_field:protocol.object"),
    ):
        request = _example()
        edit(request["protocol"])
        reply = run(request)
        assert reply["code"] == "refused", problem
        assert any(problem in str(item) for item in reply["problems"]), (problem, reply["problems"])


def test_an_invalid_expansion_is_refused_before_any_computation():
    request = _example()
    request["protocol"]["objects"][1]["data"]["permitted"] = [
        {"lower": "91", "upper": "77", "lower_inclusive": True, "upper_inclusive": True}
    ]
    reply = run(request)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_empty_interval"]


def test_without_a_protocol_preparation_stays_version_one():
    request = _example()
    del request["protocol"]
    assert run(request)["result"]["request"]["session"]["schema_version"] == 1


def test_a_cold_cli_operator_prepares_retains_and_executes_by_id(tmp_path):
    request = tmp_path / "prepare.json"
    request.write_text(json.dumps(_example()))
    store = tmp_path / "store"
    first = subprocess.run(
        [CLI, "reason", "--request", str(request), "--store", str(store), "--compact"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    reply = json.loads(first.stdout)
    artifact = reply["artifact"]["id"]
    second = subprocess.run(
        [CLI, "reason", "--prepared", artifact, "--store", str(store), "--compact"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    executed = json.loads(second.stdout)
    assert executed["code"] == "complete", executed


def test_a_protocol_only_preparation_needs_no_questions_and_discloses_the_default():
    request = _example()
    del request["questions"]
    prepared = run(request)
    assert prepared["code"] == "complete", prepared["problems"]
    assert prepared["result"]["request"]["session"]["decisions"] == []
    assert {"path": "/request/session/decisions", "value": []} in prepared["result"]["defaults"]
    assert run(prepared["result"]["request"])["code"] == "complete"


def test_a_version_one_preparation_without_questions_keeps_its_refusal():
    request = _example()
    del request["questions"], request["protocol"]
    assert run(request)["problems"] == ["missing_field:prepare.design_session"]


def test_a_retained_study_handle_is_kept_and_validation_is_deferred_not_failed():
    request = _example()
    handle = {"$retained_study": {"run": "reference", "nct": "NCT00000000", "digest": "0" * 64}}
    request["sources"] = [{"id": "reference-study", "study": handle, "expected_digest": "0" * 64}]
    prepared = run(request)
    assert prepared["code"] == "complete", prepared["problems"]
    assert prepared["result"]["validation"] == "deferred_until_execution:retained_study"
    assert prepared["result"]["request"]["session"]["sources"][0]["study"] == handle


def test_inline_sources_are_still_validated_at_preparation():
    assert "validation" not in run(_example())["result"]
