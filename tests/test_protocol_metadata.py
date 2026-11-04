"""Every protocol operator outcome reaches clinical metadata classified, per claim (C4, R1)."""

import json
from pathlib import Path

import pytest

from TrialLedger.layer2 import run

FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures"
)
KINDS = {
    "schedule.json": "schedule_coverage",
    "policy.json": "finite_policy",
    "binomial.json": "binomial_design",
}
SUPPORT = [{"id": "invented", "status": "known", "resolution": "resolved", "basis": ["user:invented"]}]
CASES = [(name, case) for name in KINDS for case in json.loads((FIXTURES / name).read_text())["cases"]]


@pytest.mark.parametrize(("name", "case"), CASES, ids=[f"{n}:{c['id']}" for n, c in CASES])
def test_every_fixture_outcome_is_classified_per_claim(name, case):
    signal = {"id": "s", "kind": KINDS[name], "data": case["data"], "support": SUPPORT}
    if case["claims"] is not None:
        signal["claims"] = case["claims"]
    reply = run({"operation": "signals", "signals": [signal]})
    assert reply["code"] == "complete", reply["problems"]
    findings = reply["metadata"]["findings"]
    assert findings, "no findings"
    for finding in findings:
        assert finding["completion"] != "unclassified", finding
        assert finding["disposition"] != "unclassified", finding
        assert all(cause["kind"] != "unclassified" for cause in finding["causes"]), finding
    claims = [f for f in findings if f["kind"] == "protocol_claim"]
    assert len(claims) == len(reply["result"]["signals"][0]["claim_admission"])


def test_a_refused_claim_keeps_its_raw_outcome_beside_the_unresolved_reading():
    case = next(c for n, c in CASES if c["id"] == "POL-1-proposed-prohibition-keeps-raw-violation")
    signal = {
        "id": "s",
        "kind": "finite_policy",
        "data": case["data"],
        "support": SUPPORT,
        "claims": case["claims"],
    }
    findings = run({"operation": "signals", "signals": [signal]})["metadata"]["findings"]
    claim = next(f for f in findings if f["kind"] == "protocol_claim")
    assert claim["logical_result"] == "unresolved"
    assert claim["raw_result"] == "violation"
    assert [cause["kind"] for cause in claim["causes"]] == ["premise"]


def _findings(kind: str, data: dict, claims) -> list[dict]:
    signal = {"id": "s", "kind": kind, "data": data, "support": SUPPORT}
    if claims is not None:
        signal["claims"] = claims
    return run({"operation": "signals", "signals": [signal]})["metadata"]["findings"]


def test_schedule_gaps_are_the_persons_repair_choice_and_policy_failures_are_conflicts():
    tim1 = next(c for n, c in CASES if c["id"] == "TIM-1")
    schedule = _findings("schedule_coverage", tim1["data"], None)
    assert {f["disposition"] for f in schedule} == {"open", "settled"}
    assert schedule[0]["disposition"] == "open"
    unsafe = next(c for n, c in CASES if c["id"] == "POL-1-covered-but-unsafe")
    policy = {
        f.get("logical_result"): f["disposition"] for f in _findings("finite_policy", unsafe["data"], None)
    }
    assert policy["violation"] == "conflict"
    assert policy["violated"] == "conflict"


def test_an_unmet_binomial_target_is_open_not_a_conflict():
    case = next(c for n, c in CASES if c["id"] == "claims-alpha-bound-and-power")
    findings = _findings("binomial_design", case["data"], case["claims"])
    assert findings[0]["logical_result"] == "not_satisfied"
    assert findings[0]["disposition"] == "open"
