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
