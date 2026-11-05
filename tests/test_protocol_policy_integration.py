"""Task 3.4: finite_policy through the shared support gate, managed projections and clinical metadata.

Every request is an invented fixture built on the public v2 session. Raw operator outcomes, admitted
(effective) outcomes, termination, work ceilings and witness caps are all read from the replayed protocol.
"""

import copy
import json
from pathlib import Path

import pytest

from tests.test_protocol_options import _policy_session
from TrialLedger.layer2 import protocol_policies as pp
from TrialLedger.layer2 import run

FIXTURES = (
    Path(__file__).resolve().parents[1]
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures/policy.json"
)
UNSAFE = next(c for c in json.loads(FIXTURES.read_text())["cases"] if c["id"] == "POL-1-covered-but-unsafe")
RULE = "interim-rule"
CHECK = "interim-safety"


def _claims(request: dict, *claims: tuple[str, int]) -> dict:
    request["session"]["protocol"]["checks"][0]["claims"] = [
        {"id": name, "claim": name, "witness_limit": limit} for name, limit in claims
    ]
    return request


def _model(request: dict) -> dict:
    item = next(o for o in request["session"]["protocol"]["objects"] if o["id"] == RULE)
    return item["data"]["model"]


def _cyclic(request: dict) -> dict:
    """The stop transition returns to the interim state, so a cycle is reachable."""
    _model(request)["transitions"][1]["to"] = "interim"
    return request


def _signal(reply: dict) -> dict:
    (child,) = reply["result"]["protocol"]["checks"][0]["children"]
    return child["result"]["result"]["signals"][0]


def _rows(reply: dict) -> dict:
    """Claim admission rows of the managed child signal, which carry application and finding status."""
    (child,) = reply["result"]["protocol"]["checks"][0]["children"]
    return {row["claim"]: row for row in child["signals"][0]["claim_admission"]}


def _raw(reply: dict) -> dict:
    return {row["claim"]: row for row in _signal(reply)["value"]["claims"]}


def _complete(request: dict) -> dict:
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    return reply


def _protocol_findings(reply: dict) -> list[dict]:
    return [f for f in reply["metadata"]["findings"] if "/protocol/" in f["path"]]


# --- EPI/SCP: raw conditional result versus the admitted result ---------------------------------------


def test_a_proposed_prohibition_stays_unadmitted_while_known_coverage_is_admitted():
    """EPI/SCP: the prohibition rule's standing gates the prohibition claim only; coverage keeps its own."""
    reply = _complete(_claims(_policy_session("proposed"), ("coverage", 1), ("prohibition", 1)))
    rows = _rows(reply)

    assert rows["coverage"]["admission"] == "accepted"
    assert rows["coverage"]["finding_status"] == "known"
    assert rows["coverage"]["effective_outcome"] == "covered"
    assert rows["prohibition"]["admission"] == "proposed_refused"
    assert rows["prohibition"]["finding_status"] == "proposed"
    assert rows["prohibition"]["determining_ids"] == ["invented-no-continue-with-safety-signal"]


def test_the_raw_outcome_is_visible_and_the_effective_outcome_is_withheld_for_a_proposed_rule():
    """A proposed prohibition keeps the raw violation beside an unresolved effective outcome."""
    reply = _complete(_claims(_policy_session("proposed"), ("prohibition", 1)))
    row = _rows(reply)["prohibition"]

    assert row["outcome"] == "violation"
    assert row["effective_outcome"] == "unresolved"
    assert _raw(reply)["prohibition"]["outcome"] == "violation"
    assert _raw(reply)["prohibition"]["violations_found"] == 1
    signal = _signal(reply)
    assert (signal["code"], signal["calculation_code"]) == ("unresolved", "violated")
    assert "proposed_refused:interim-safety:finite_policy_model" in signal["blockers"]


def test_a_known_prohibition_is_admitted_with_the_same_raw_outcome():
    """The positive twin: with known standing the raw violation is the effective one."""
    reply = _complete(_claims(_policy_session("known"), ("prohibition", 1)))
    row = _rows(reply)["prohibition"]

    assert (row["outcome"], row["effective_outcome"], row["admission"]) == (
        "violation",
        "violation",
        "accepted",
    )
    assert _signal(reply)["code"] == "violated"


def test_the_withheld_claim_reaches_metadata_as_open_with_its_raw_result():
    """MUST-NOT: a raw violation under a proposed rule is not a conflict in the clinical metadata."""
    reply = _complete(_claims(_policy_session("proposed"), ("prohibition", 1)))
    claim = next(f for f in _protocol_findings(reply) if f["kind"] == "protocol_claim")

    assert claim["logical_result"] == "unresolved"
    assert claim["raw_result"] == "violation"
    assert claim["disposition"] == "open"
    assert [cause["kind"] for cause in claim["causes"]] == ["premise"]
    assert "conflict" not in {f["disposition"] for f in _protocol_findings(reply)}
    assert "conflict" not in reply["summary"]["dispositions"]


def test_a_known_violation_is_counted_as_a_conflict_in_the_headline():
    """The clinical headline counts the known violation, in the signal and in its claim, as conflicts."""
    reply = _complete(_claims(_policy_session("known"), ("prohibition", 1)))
    conflicts = [f for f in _protocol_findings(reply) if f["disposition"] == "conflict"]

    assert {f["kind"] for f in conflicts} == {"signal", "protocol_claim"}
    assert {f["logical_result"] for f in conflicts} == {"violated", "violation"}
    assert reply["summary"]["dispositions"]["conflict"] == len(conflicts) == 2
    assert all(f["standing"] == "known" for f in conflicts)


def test_the_headline_conflict_count_equals_the_conflict_findings_for_every_standing():
    """The headline never disagrees with the findings it summarizes."""
    for standing in ("known", "proposed"):
        reply = _complete(_claims(_policy_session(standing), ("prohibition", 1)))
        listed = sum(1 for f in reply["metadata"]["findings"] if f["disposition"] == "conflict")
        assert reply["summary"]["dispositions"].get("conflict", 0) == listed, standing


# --- no implicit follow-up termination ------------------------------------------------------------------


def test_termination_is_reported_only_when_a_termination_claim_is_declared():
    """The default claims never carry a termination row, in either the admission rows or the raw claims."""
    for request in (_policy_session("known"), _cyclic(_policy_session("known"))):
        reply = _complete(_claims(request, ("coverage", 1), ("prohibition", 1)))
        assert "termination" not in _rows(reply)
        assert "termination" not in _raw(reply)
        assert "all_paths_terminate" not in json.dumps(_signal(reply)["value"])
        assert "not_established" not in json.dumps(_signal(reply)["value"])


def test_a_declared_termination_claim_is_reported_for_an_acyclic_policy():
    """A declared claim on an acyclic, fully covered policy is established for all paths."""
    reply = _complete(_claims(_policy_session("known"), ("termination", 1)))
    row = _rows(reply)["termination"]
    assert (row["outcome"], row["effective_outcome"], row["admission"]) == (
        "all_paths_terminate",
        "all_paths_terminate",
        "accepted",
    )
    assert _raw(reply)["termination"]["reasons"] == []


def test_a_reachable_cycle_gives_not_established_never_termination():
    """POL-5: a cycle yields not_established with its named reason and witness, and assumes no fairness."""
    reply = _complete(_claims(_cyclic(_policy_session("known")), ("termination", 1)))
    row = _rows(reply)["termination"]

    assert (row["outcome"], row["effective_outcome"]) == ("not_established", "not_established")
    raw = _raw(reply)["termination"]
    assert raw["reasons"] == ["reachable_cycle"]
    assert len(raw["witnesses"]) == 1
    assert _signal(reply)["blockers"] == ["policy_not_established:termination"]
    assert _signal(reply)["value"]["fairness"] == "not_assumed"


def test_an_undeclared_cycle_is_not_reported_as_a_termination_finding():
    """MUST-NOT: the same cyclic model without the claim raises no termination blocker or conflict."""
    reply = _complete(_claims(_cyclic(_policy_session("known")), ("coverage", 1)))
    assert _signal(reply)["code"] == "satisfied"
    assert _signal(reply)["blockers"] == []
    assert "conflict" not in reply["summary"]["dispositions"]


# --- exact work and display limits ----------------------------------------------------------------------


def test_a_model_over_the_work_ceiling_returns_limit_with_reserved_and_used_work(monkeypatch):
    """LIM-1: over the ceiling nothing is executed; the limit names the reservation and zero work used."""
    request = _claims(_policy_session("known"), ("coverage", 1), ("prohibition", 1))
    reserved = pp.work_reservation(_model(request))
    monkeypatch.setattr(pp, "MAX_POLICY_WORK", reserved - 1)
    reply = _complete(request)
    signal = _signal(reply)

    assert (signal["code"], signal["calculation_code"]) == ("limit", "limit")
    assert signal["blockers"] == ["policy_work_limit"]
    assert signal["value"]["work"] == {"reserved": reserved, "used": 0}
    assert {row["outcome"] for row in signal["claim_admission"]} == {"not_executed"}
    assert {row["effective_outcome"] for row in signal["claim_admission"]} == {"not_executed"}


def test_a_limit_is_never_a_partial_success_or_a_conflict(monkeypatch):
    """MUST-NOT: no witness, violation, coverage or pass survives a limit; metadata says not computed."""
    request = _claims(_policy_session("known"), ("coverage", 1), ("prohibition", 1))
    monkeypatch.setattr(pp, "MAX_POLICY_WORK", pp.work_reservation(_model(request)) - 1)
    reply = _complete(request)

    for row in _raw(reply).values():
        assert row["outcome"] == "not_executed"
        assert row["violations_found"] == 0
        assert row["witnesses"] == []
    findings = _protocol_findings(reply)
    assert {f["disposition"] for f in findings if f["kind"] == "signal"} == {"not_computed"}
    signal_finding = next(f for f in findings if f["kind"] == "signal")
    assert signal_finding["completion"] == "limited"
    assert [cause["code"] for cause in signal_finding["causes"]] == ["policy_work_limit"]
    assert "conflict" not in reply["summary"]["dispositions"]


def test_the_work_ceiling_is_exact_at_the_reservation(monkeypatch):
    """A ceiling equal to the reservation computes; one below does not."""
    request = _claims(_policy_session("known"), ("prohibition", 1))
    reserved = pp.work_reservation(_model(request))
    monkeypatch.setattr(pp, "MAX_POLICY_WORK", reserved)
    reply = _complete(request)
    work = _signal(reply)["value"]["work"]
    assert _signal(reply)["code"] == "violated"
    assert work["reserved"] == reserved and 0 < work["used"] <= reserved


def test_policy_work_is_reserved_in_the_session_budget_and_gated_exactly():
    """LIM-1 / C10: the session reservation includes the policy child; one unit less stops that check by name.

    A bound that stops a check leaves it unexecuted and never satisfied, names the limit with reserved work
    and the configured ceiling, and keeps independently completed results (C10; interface budgets.md F1).
    """
    request = _claims(_policy_session("known"), ("prohibition", 1))
    reserved = _complete(request)["work"]["solver_work_reserved"]

    at_limit = copy.deepcopy(request)
    at_limit["session"]["limits"]["max_solver_work"] = reserved
    assert run(at_limit)["code"] == "complete"
    assert _signal(run(at_limit))["code"] == "violated"

    below = copy.deepcopy(request)
    below["session"]["limits"]["max_solver_work"] = reserved - 1
    stopped = run(below)
    assert stopped["code"] == "complete", stopped.get("problems")
    (check,) = [c for c in stopped["result"]["protocol"]["checks"] if c["kind"] == "finite_policy"]
    (limit,) = [u for u in check["unresolved"] if u["code"] == "session_work_limit"]
    assert limit["limit"] == "resource_bound:session_solver_work"
    assert limit["configured"]["max_solver_work"] == reserved - 1
    assert limit["reserved"] > 0
    assert [child["result"]["code"] for child in check["children"]] == ["refused"]
    assert not any(signal for child in check["children"] for signal in child["signals"])


@pytest.mark.parametrize("limit", [0, 1, 2, 3, 64])
def test_witness_caps_bound_the_displayed_traces_exactly_without_changing_the_outcome(limit):
    """POL-6: the cap bounds the witnesses shown; the violation count and the effective outcome are fixed."""
    request = _claims(_policy_session("known"), ("prohibition", limit))
    request["session"]["protocol"]["objects"][-1]["data"]["model"] = copy.deepcopy(UNSAFE["data"])
    reply = _complete(request)
    raw = _raw(reply)["prohibition"]
    shown = min(limit, 3)

    assert raw["violations_found"] == 3
    assert len(raw["witnesses"]) == shown
    assert raw["witnesses_omitted"] == 3 - shown
    assert _rows(reply)["prohibition"]["effective_outcome"] == "violation"
    assert _signal(reply)["code"] == "violated"


def test_a_capped_witness_list_is_a_prefix_of_the_uncapped_one_and_an_empty_display_is_not_clearance():
    """MUST-NOT: a cap of zero is not read as no violation, and a cap never reorders or alters traces."""

    def witnesses(limit: int) -> list:
        request = _claims(_policy_session("known"), ("prohibition", limit))
        request["session"]["protocol"]["objects"][-1]["data"]["model"] = copy.deepcopy(UNSAFE["data"])
        reply = _complete(request)
        assert _rows(reply)["prohibition"]["outcome"] == "violation"
        return _raw(reply)["prohibition"]["witnesses"]

    full = witnesses(64)
    assert len(full) == 3
    assert witnesses(0) == []
    assert witnesses(2) == full[:2]
