"""Engine repairs from the wave-4 real-data walkthroughs (`~/trialledger-runs/walk4-*-20261105/verdict.md`).

Each test names its walkthrough finding. Decisions by Rohan (2026-11-04): a definition relation is capped by
the standing of the protocol objects it is bound to; a sole compatible what-if is never "settled".
"""

import copy
import json

from tests.test_protocol_admission_inputs import _binomial_session
from tests.test_protocol_definition_relations import EDITION, _madrs_protocol, _with_relation
from tests.test_protocol_options import _alt, _base, _decision, _replacement, _with_decision
from tests.test_protocol_review_repairs import _revise
from tests.test_protocol_session_replay import ORIGIN, adopt, new_edition
from tests.test_protocol_walkthrough_repairs import _estimand_with_linked_collection
from TrialLedger import reasoning_artifacts as artifacts
from TrialLedger import reasoning_delivery as delivery
from TrialLedger.layer2 import protocol_decisions, run

NEW_ORIGIN = {**ORIGIN, "ref": "user:invented re-attribution"}


def _check_row(reply: dict, identity: str) -> dict:
    return next(row for row in reply["answer_diff"]["protocol_checks"] if row["id"] == identity)


# --- neuro: a linked collection consumed by the estimand projection --------------------------------------


def test_an_origin_change_on_a_linked_collection_reaches_the_estimand_check_origin_axis():
    def reattribute(session):
        next(o for o in session["protocol"]["objects"] if o["id"] == "collection")["origin"] = NEW_ORIGIN

    row = _check_row(_revise(_estimand_with_linked_collection("stop"), reattribute), "estimand-check")
    assert "origin" in row["axes"]
    assert "verdict" not in row["axes"]


def test_a_reattributed_linked_collection_changes_the_estimand_support_axis_on_re_adoption():
    def readopt(session):
        collection = next(o for o in session["protocol"]["objects"] if o["id"] == "collection")
        collection["data"]["event_handling"]["action"] = "collect"
        new_edition(session, "collection")

    first = _estimand_with_linked_collection("stop")
    adopt(first, "collection")
    row = _check_row(_revise(first, readopt), "estimand-check")
    assert {"verdict", "support", "scope_model"} <= set(row["axes"])


# --- id: exact statistics per alternative and in revisions -------------------------------------------------


def _binomial_decision() -> dict:
    base = _binomial_session()
    efficacy = next(o for o in base["session"]["protocol"]["objects"] if o["id"] == "efficacy")
    bigger = copy.deepcopy(efficacy)
    bigger["data"]["parameters"].update(n=30, critical_count=11)
    bigger["origin"] = {**ORIGIN, "kind": "hypothesis", "ref": "user:invented n=30"}
    bigger["standing"] = {"status": "proposed", "resolution": "resolved", "basis": ["user:invented n=30"]}
    checks = ("week12-schedule", "efficacy-check")
    return _with_decision(base, [_alt("as-drafted", [], checks), _alt("n30", [bigger], checks)])


def test_each_alternative_retains_its_own_exact_design_inputs_and_tail_probabilities():
    decision = _decision(run(_binomial_decision()))
    stats = {
        alternative["id"]: [
            value
            for check in alternative["checks"]
            for child in check["children"]
            for value in child["statistics"]
        ]
        for alternative in decision["alternatives"]
    }
    assert [(v["n"], v["critical_count"]) for v in stats["as-drafted"]] == [(20, 7)]
    assert [(v["n"], v["critical_count"]) for v in stats["n30"]] == [(30, 11)]
    assert stats["n30"][0]["power"] != stats["as-drafted"][0]["power"]
    assert all("/" in v["null_rejection_probability"] for v in stats["n30"])


def test_a_revision_reports_exact_binomial_inputs_and_probabilities_before_and_after():
    def bigger(session):
        efficacy = next(o for o in session["protocol"]["objects"] if o["id"] == "efficacy")
        efficacy["data"]["parameters"].update(n=24, critical_count=8)
        new_edition(session, "efficacy")

    row = _check_row(_revise(_binomial_session(), bigger), "efficacy-check")
    changes = {c["field"]: (c["before"], c["after"]) for c in row["changes"] if "signal" in c}
    assert changes["n"] == (20, 24) and changes["critical_count"] == (7, 8)
    assert {"null_rejection_probability", "power"} <= changes.keys()


def test_alternative_claims_carry_their_effective_outcome_beside_the_raw_one():
    decision = _decision(run(_binomial_decision()))
    claims = [c for a in decision["alternatives"] for ch in a["checks"] for c in ch["claims"]]
    assert claims and all("effective_outcome" in c for c in claims)
    for claim in claims:
        if claim["admission"] != "accepted":
            assert claim["effective_outcome"] == "unresolved"


# --- renal: decision rows say what changed -----------------------------------------------------------------


def test_a_selection_change_is_listed_before_and_after_on_the_decision_row():
    base = _base()
    alternatives = [
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
        _alt("as-drafted", [], ("week12-schedule",)),
    ]
    first = _with_decision(base, alternatives)
    chosen = {"alternative": "as-drafted", "origin": "user", "basis": ["user:invented choice"]}

    def select(session):
        next(d for d in session["decisions"] if d.get("kind") == "protocol_options")["selected"] = chosen

    row = next(r for r in _revise(first, select)["answer_diff"]["protocol_decisions"])
    assert "origin" in row["axes"]
    assert {"field": "selected", "before": None, "after": chosen} in row["changes"]


# --- psych: definition relations bound to protocol objects -------------------------------------------------


def _relation_row(request: dict) -> dict:
    reply = run(request)
    assert reply["code"] == "complete", reply.get("problems")
    return reply["result"]["definition_checks"][0]


def test_a_reading_that_differs_from_its_bound_value_is_marked_and_an_exact_copy_is_marked_too():
    exact = _relation_row(_with_relation("implies", "relapse-check", "retreatment-check"))
    assert exact["observed_match"] == {"left": "exact_copy", "right": "exact_copy"}
    request = _with_relation("implies", "relapse-check", "retreatment-check")
    request["session"]["definition_checks"][0]["right"]["body"] = copy.deepcopy(EDITION)
    assert _relation_row(request)["observed_match"] == {"left": "exact_copy", "right": "differs"}


def test_a_relation_bound_to_an_unadopted_object_reads_proposed_while_still_computed():
    """Rohan (2026-11-04): a relation is never stronger than the protocol objects it is bound to."""
    adopted = _relation_row(_with_relation("implies", "relapse-check", "retreatment-check"))
    assert (adopted["code"], adopted["status"]) == ("consistent", "known")

    request = _with_relation("implies", "relapse-check", "retreatment-check")
    session = request["session"]
    rule = next(o for o in session["protocol"]["objects"] if o["id"] == "relapse-rule")
    rule["support"] = []
    session["premises"] = [p for p in session["premises"] if p["id"] != "adopt:relapse-rule:invented-v1"]
    unadopted = _relation_row(request)
    assert unadopted["code"] == "consistent"
    assert unadopted["status"] == "proposed"
    left = {e["id"]: e for e in unadopted["bound_support"]["left"]}
    assert left["adoption:relapse-rule"]["resolution"] == "unresolved"


def test_v1_definition_rows_keep_their_exact_shape():
    """CMP-1: the new fields are added only for protocol operands."""
    from TrialLedger.layer2.design_session_guide import EXAMPLE

    request = copy.deepcopy(EXAMPLE)
    reply = run(request)
    for row in (reply.get("result") or {}).get("definition_checks", []):
        assert "observed_match" not in row and "bound_support" not in row


# --- haem: a sole compatible what-if is not settled ---------------------------------------------------------


def test_a_sole_compatible_what_if_is_a_repair_choice_and_a_fixed_compatible_plan_is_settled():
    """Rohan (2026-11-04): nothing adopted is settled when the only compatible alternative is hypothetical."""
    compatible, gap = "compatible_under_declared_checks", "repair_choice_open_under_declared_checks"
    assert (
        protocol_decisions.disposition([(gap, "a", False), (compatible, "b", True)], None) == "repair_choice"
    )
    assert (
        protocol_decisions.disposition([(compatible, "a", False), (gap, "b", True)], None)
        == "settled_within_declared_alternatives"
    )
    base = _base()
    alternatives = [
        _alt("as-drafted", [], ("week12-schedule",)),
        _alt("through-95", [_replacement(base, "95", ref="through 95")], ("week12-schedule",)),
    ]
    decision = _decision(run(_with_decision(base, alternatives)))
    assert decision["disposition"] == "repair_choice"


# --- psych/delivery: copied parent digests and readable parts ----------------------------------------------


def test_a_session_read_back_from_its_artifact_revises_without_hand_editing_its_parent(tmp_path):
    held = delivery.execute(_base(), store=tmp_path)
    first = delivery.revise(
        tmp_path,
        held["artifact"]["id"],
        session={
            **copy.deepcopy(artifacts.load(tmp_path, held["artifact"]["id"])["request"]["session"]),
            "revision": "two",
        },
        response_view="full",
    )
    assert first["code"] == "complete", first.get("problems")
    copied = copy.deepcopy(artifacts.load(tmp_path, first["artifact"]["id"])["request"]["session"])
    assert copied["parent_digest"] is not None
    copied["revision"] = "three"
    third = delivery.revise(tmp_path, first["artifact"]["id"], session=copied, response_view="full")
    assert third["code"] == "complete", third.get("problems")


def test_protocol_and_plan_comparisons_are_readable_parts(tmp_path):
    held = delivery.execute(_binomial_decision(), store=tmp_path)
    identity = held["artifact"]["id"]
    for part in ("protocol", "protocol_decisions"):
        reply = artifacts.read(tmp_path, identity, {"part": part})
        assert reply["code"] == "complete", (part, reply)
        assert "value" in reply or "entries" in reply


def test_a_protocol_signal_lists_each_basis_reference_once():
    reply = run(_madrs_protocol())
    for check in reply["result"]["protocol"]["checks"]:
        for child in check["children"]:
            for signal in ((child["result"].get("result") or {}).get("signals")) or []:
                assert len(signal["basis"]) == len(set(signal["basis"])), json.dumps(signal["basis"])
