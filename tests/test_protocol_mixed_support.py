"""Weakest support governs when an object carries a known and a proposed adoption of the same version.

Restores mixed-support coverage that the explicit-adoption migration (67bae65) narrowed: an independent review
found the known-beside-proposed case gone from projections (L2), from two-premise references (L1) and from the
option tests, whose unsupported arm also changed version (L3). Each case here keeps the version fixed.
"""

import copy

from tests.test_protocol_options import (
    _alt,
    _base,
    _check,
    _complete,
    _decision,
    _replacement,
    _row,
    _with_decision,
)
from tests.test_protocol_projections import PREMISES, SOURCES, STANDING, TARGET, ids, week12
from tests.test_protocol_session_replay import adoption_premise
from TrialLedger.layer2 import protocol_objects, protocol_projections, run

SECOND = "adopt-review:a1:e1"


def _second_adoption(identity: str, version: str, status: str, resolution: str) -> dict:
    return {
        "kind": "adoption",
        "payload": {
            "objects": [{"id": identity, "version": version}],
            "status": status,
            "resolution": resolution,
        },
    }


def _mixed_index() -> tuple[dict, dict]:
    protocol = week12()
    a1 = next(o for o in protocol["objects"] if o["id"] == "a1")
    assert a1["version"] == "e1"
    a1["support"] = ["adopt:a1:e1", SECOND]
    premises = {**PREMISES, SECOND: _second_adoption("a1", "e1", "proposed", "unresolved")}
    index = protocol_objects.validate_protocol(
        protocol, target=copy.deepcopy(TARGET), premises=premises, sources=copy.deepcopy(SOURCES)
    )
    standing = {
        **STANDING,
        "adopt:a1:e1": {"status": "known", "resolution": "resolved", "basis": ["user:adopts a1"]},
        SECOND: {"status": "proposed", "resolution": "unresolved", "basis": ["user:second look at a1"]},
    }
    return index, standing


def test_l1_two_adoption_records_are_both_referenced_in_declared_order():
    index, _ = _mixed_index()
    assert index["references"]["a1"]["premises"] == ["adopt:a1:e1", SECOND]


def test_l2_a_known_and_a_proposed_adoption_both_stay_visible_in_support_and_roles():
    index, standing = _mixed_index()
    child = protocol_projections.project(index, "k-sched", premise_standing=standing)["children"][0]
    support = child["request"]["signals"][0]["support"]
    assert {"id": "premise:adopt:a1:e1", **standing["adopt:a1:e1"]} in support
    assert {"id": "premise:" + SECOND, **standing[SECOND]} in support
    assert ids(child["receipt"]["role_support"]["permitted"]) == [
        "object:a1",
        "premise:adopt:a1:e1",
        "premise:" + SECOND,
    ]
    assert child["receipt"]["premises"] == ["adopt:a1:e1", SECOND]
    statuses = {
        e["status"] for e in child["receipt"]["role_support"]["permitted"] if e["id"].startswith("premise:")
    }
    assert statuses == {"known", "proposed"}


def test_l3_a_proposed_adoption_beside_a_known_one_of_the_same_version_leaves_the_check_undetermined():
    """Same version as the baseline: only the proposed second adoption separates the two arms."""
    base = _base()
    review = adoption_premise("collection", "invented-v1", "proposed", "resolved")
    review["id"] = "adopt-review:collection:invented-v1"
    base["session"]["premises"].append(review)
    supported = _replacement(base, "95", ref="supported window")
    unsupported = _replacement(base, "95", ref="unsupported window")
    assert supported["version"] == unsupported["version"] == "invented-v1"
    unsupported["support"] = [*supported["support"], review["id"]]
    alternatives = [
        _alt("supported", [supported], ("week12-schedule",)),
        _alt("unsupported", [unsupported], ("week12-schedule",)),
    ]
    decision = _decision(_complete(_with_decision(base, alternatives)))
    assert _row(decision, "unsupported")["compatibility"] == "undetermined"
    assert _check(_row(decision, "unsupported"), "week12-schedule")["check_code"] == "undetermined"
    assert _row(decision, "supported")["compatibility"] != "undetermined"


def test_l3_the_mixed_adoption_refuses_admission_on_the_baseline_too():
    base = _base()
    review = adoption_premise("collection", "invented-v1", "proposed", "resolved")
    review["id"] = "adopt-review:collection:invented-v1"
    base["session"]["premises"].append(review)
    collection = next(o for o in base["session"]["protocol"]["objects"] if o["id"] == "collection")
    collection["support"] = [*collection["support"], review["id"]]
    reply = run(base)
    assert reply["code"] == "complete", reply.get("problems")
    check = next(c for c in reply["result"]["protocol"]["checks"] if c["id"] == "week12-schedule")
    rows = check["children"][0]["signals"][0]["claim_admission"]
    assert {row["admission"] for row in rows} == {"proposed_refused"}
