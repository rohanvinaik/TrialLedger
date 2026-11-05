"""Definition relations over protocol checks (DEF-1/DEF-2): two MADRS readings stay two definitions.

Each reading is bound to a typed threshold that the protocol itself carries: the transition guard of an
adopted finite-policy object, retained in that check's child request. The tests assert that every reading body
is the exact retained guard it is bound to, so the relation is computed over the protocol's own
thresholds, not over an unrelated address. TrialLedger itself never certifies that a caller's reading
matches its address; it shows the observed value beside the reading.
"""

import copy
import json
from typing import cast

from tests.test_protocol_session_replay import _session, adoption_premise
from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import run
from TrialLedger.layer2.design_session_guide import EXAMPLE

BASIS = {
    "retreatment-check": ["user:invented MADRS retreatment trigger reading"],
    "relapse-check": ["user:invented MADRS relapse definition reading"],
    "baseline-change-check": ["user:invented MADRS change-from-baseline response reading"],
    "edition-check": ["user:invented MADRS second-edition trigger reading"],
}
GUARD = "/request/signals/0/data/transitions/0/guard"
SCORES = (18, 21, 23)


def threshold(key: str, number: int) -> dict:
    """A typed reading: participant measurement `key` at or above `number` score points."""
    value = a.Value("quantity", "ge", number=number, unit="score")
    return json.loads(
        a.canonical(a.Literal(a.Subject("participant"), a.Predicate("measurement", key), value))
    )


def _canonical(proposition: a.Proposition) -> dict:
    return json.loads(a.canonical(proposition))


def _parsed(raw: dict) -> a.Proposition:
    return cast(a.Proposition, a.from_canonical(json.dumps(raw)))


def _domain(key: str) -> dict:
    """Representative MADRS scores; the guard threshold is decided per valuation by the policy operator."""
    values = [
        _canonical(
            a.Literal(
                a.Subject("participant"),
                a.Predicate("measurement", key),
                a.Value("quantity", "eq", number=n, unit="score"),
            )
        )
        for n in SCORES
    ]
    return {"id": key, "values": values}


def _policy(identity: str, keys: tuple[str, ...], guard: dict, action: str) -> dict:
    """A two-transition finite policy whose first transition guard is the protocol's typed threshold."""

    def act(name: str) -> dict:
        return {
            "id": name,
            "scope": {"level": "participant", "ref": "invented:participant"},
            "description": name,
        }

    return {
        "scope": "invented:" + identity,
        "version": "invented:" + identity + "-v1",
        "variables": [_domain(key) for key in keys],
        "constraints": [],
        "states": ["monitoring", "decided"],
        "initial": ["monitoring"],
        "terminal": ["decided"],
        "actions": [act(action), act("continue_monitoring")],
        "transitions": [
            {"id": action, "from": "monitoring", "to": "decided", "guard": guard, "actions": [action]},
            {
                "id": "no-" + action,
                "from": "monitoring",
                "to": "decided",
                "guard": _canonical(a.Not(_parsed(guard))),
                "actions": ["continue_monitoring"],
            },
        ],
        "prohibitions": [],
        "invariants": [],
    }


TRIGGER = threshold("madrs", 20)
RELAPSE = _canonical(
    a.AllOf((_parsed(threshold("madrs", 22)), _parsed(threshold("madrs_previous_visit", 22))))
)
BASELINE_CHANGE = threshold("madrs_change_from_baseline", 20)
EDITION = threshold("madrs_edition_2", 20)
RULES = {
    # check id: (object id, variable keys, guard, action)
    "retreatment-check": ("retreatment-rule", ("madrs",), TRIGGER, "retreat"),
    "relapse-check": ("relapse-rule", ("madrs", "madrs_previous_visit"), RELAPSE, "record_relapse"),
    "baseline-change-check": (
        "baseline-change-rule",
        ("madrs_change_from_baseline",),
        BASELINE_CHANGE,
        "record_response",
    ),
    "edition-check": ("edition-rule", ("madrs_edition_2",), EDITION, "retreat_edition_2"),
}


def _madrs_protocol() -> dict:
    """A v2 session whose adopted policy objects carry the MADRS thresholds as typed transition guards."""
    request = _session("84")
    session = request["session"]
    protocol = session["protocol"]
    template = protocol["objects"][0]
    for check_id, (object_id, keys, guard, action) in RULES.items():
        held = copy.deepcopy(template)
        held.update(
            id=object_id,
            kind="policy",
            depends_on=[],
            support=[f"adopt:{object_id}:invented-v1"],
            data={"model": _policy(object_id, keys, guard, action), "bindings": []},
        )
        protocol["objects"].append(held)
        session["premises"].append(adoption_premise(object_id, "invented-v1"))
        protocol["checks"].append(
            {
                "id": check_id,
                "kind": "finite_policy",
                "scope": copy.deepcopy(template["scope"]),
                "objects": [object_id],
                "bindings": [],
                "claims": [{"id": "coverage", "claim": "coverage", "witness_limit": 1}],
                "required": True,
                "support": [],
            }
        )
    session["definition_checks"] = []
    return request


def _operand(check: str, child: int = 0, status: str = "known") -> dict:
    """A reading of a check's retained guard: its body is exactly the guard the protocol carries."""
    return {
        "protocol_check": check,
        "child": child,
        "address": GUARD,
        "body": copy.deepcopy(RULES[check][2]),
        "status": status,
        "resolution": "resolved",
        "basis": list(BASIS[check]),
    }


def _relation(identity: str, relation: str, left: dict, right: dict) -> dict:
    return {
        "id": identity,
        "relation": relation,
        "left": left,
        "right": right,
        "status": "known",
        "resolution": "resolved",
        "basis": ["user:invented definition-relation declaration"],
    }


def _with_relation(relation: str, left: str, right: str) -> dict:
    request = _madrs_protocol()
    request["session"]["definition_checks"] = [
        _relation("trigger-link", relation, _operand(left), _operand(right))
    ]
    return request


def _row(reply: dict) -> dict:
    return reply["result"]["definition_checks"][0]


def _directions(row: dict) -> dict:
    return {check["direction"]: check["result"]["result"]["decision"]["result"] for check in row["checks"]}


def test_each_reading_is_the_threshold_the_protocol_check_itself_carries():
    """The fixture binds each reading to its check's retained guard, not to an unrelated protocol value."""
    reply = run(_with_relation("implies", "relapse-check", "retreatment-check"))
    assert reply["code"] == "complete", reply
    row = _row(reply)
    for side in ("left", "right"):
        assert row["observed"][side] == row["declaration"][side]["body"], side
    assert row["observed"] == {"left": RELAPSE, "right": TRIGGER}
    checks = {check["id"]: check for check in reply["result"]["protocol"]["checks"]}
    for check_id in ("relapse-check", "retreatment-check"):
        child = checks[check_id]["children"][0]
        assert child["result"]["code"] == "complete"
        assert child["request"]["signals"][0]["data"]["transitions"][0]["guard"] == RULES[check_id][2]


def test_stricter_relapse_reading_implies_the_earlier_trigger_reading():
    """DEF-1: the declared implies from 'MADRS >= 22 on two consecutive visits' to 'MADRS >= 20' holds."""
    reply = run(_with_relation("implies", "relapse-check", "retreatment-check"))
    assert reply["code"] == "complete", reply
    row = _row(reply)
    assert (row["code"], row["status"], row["blockers"]) == ("consistent", "known", [])
    assert _directions(row) == {"implies": "ENTAILED"}


def test_declared_equivalence_between_the_twenty_and_twenty_two_readings_is_refuted():
    """DEF-1: 'equivalent' fails from trigger to relapse; the relation, not a source, is refuted."""
    reply = run(_with_relation("equivalent", "relapse-check", "retreatment-check"))
    assert reply["code"] == "complete", reply
    row = _row(reply)
    assert row["code"] == "conflict"
    directions = _directions(row)
    assert directions["left_implies_right"] == "ENTAILED"
    assert directions["right_implies_left"] != "ENTAILED"


def test_the_two_readings_stay_two_definitions_and_the_protocol_is_unchanged():
    """DEF-1: relation rows keep both readings separate; the protocol checks are not merged or re-decided."""
    reply = run(_with_relation("equivalent", "relapse-check", "retreatment-check"))
    assert reply["code"] == "complete", reply
    row = _row(reply)
    assert row["declaration"]["left"]["body"] != row["declaration"]["right"]["body"]
    assert [check["id"] for check in reply["result"]["protocol"]["checks"]] == [
        "week12-schedule",
        *RULES,
    ]
    baseline = run(_madrs_protocol())
    assert reply["result"]["protocol"] == baseline["result"]["protocol"]


def test_a_numeric_difference_alone_is_not_reported_as_a_protocol_contradiction():
    """DEF-1: the converse implication (>=20 to >=22) is not established, and no protocol check changes."""
    reply = run(_with_relation("implies", "retreatment-check", "relapse-check"))
    assert reply["code"] == "complete", reply
    row = _row(reply)
    assert row["code"] != "consistent"
    assert _directions(row)["implies"] != "ENTAILED"
    baseline = run(_madrs_protocol())
    assert reply["result"]["protocol"] == baseline["result"]["protocol"]
    for check in reply["result"]["protocol"]["checks"][1:]:
        assert [signal["code"] for signal in check["children"][0]["signals"]] == ["satisfied"], check["id"]


def test_same_number_with_a_different_baseline_field_does_not_establish_equivalence():
    """DEF-2: >=20 on the absolute score and >=20 change from baseline differ in a typed field."""
    reply = run(_with_relation("equivalent", "retreatment-check", "baseline-change-check"))
    assert reply["code"] == "complete", reply
    row = _row(reply)
    assert row["code"] != "consistent"
    assert row["observed"]["right"] == BASELINE_CHANGE
    assert row["declaration"]["left"]["body"]["value"] == row["declaration"]["right"]["body"]["value"]
    assert row["declaration"]["left"]["body"]["predicate"] != row["declaration"]["right"]["body"]["predicate"]


def test_same_number_with_a_different_edition_field_does_not_establish_equivalence():
    """DEF-2: the same >=20 number under a different scale edition is not an established relation."""
    reply = run(_with_relation("equivalent", "retreatment-check", "edition-check"))
    assert reply["code"] == "complete", reply
    row = _row(reply)
    assert row["code"] != "consistent"
    assert row["observed"]["right"] == EDITION


def test_a_proposed_protocol_operand_reading_is_blocked_and_never_admitted():
    """MUST-NOT: a proposed operand is refused as definition_proposed_refused; no check runs on it."""
    for part in ("left", "right"):
        request = _with_relation("implies", "relapse-check", "retreatment-check")
        request["session"]["definition_checks"][0][part]["status"] = "proposed"
        reply = run(request)
        row = _row(reply)
        assert (row["code"], row["status"], row["checks"]) == ("unresolved", None, []), part
        assert row["blockers"] == ["definition_proposed_refused"], part


def test_shared_check_ids_never_establish_a_relation():
    """MUST-NOT: both operands naming one check id is not a relation; the declared readings decide."""
    request = _madrs_protocol()
    left = _operand("retreatment-check")
    right = _operand("retreatment-check")
    right["body"] = copy.deepcopy(EDITION)
    request["session"]["definition_checks"] = [_relation("same-check", "equivalent", left, right)]
    reply = run(request)
    assert reply["code"] == "complete", reply
    row = _row(reply)
    # Same check id on both sides; the right reading is not what that check carries, and it is not merged.
    assert row["observed"] == {"left": TRIGGER, "right": TRIGGER}
    assert row["declaration"]["right"]["body"] == EDITION
    assert row["code"] != "consistent"


def test_an_unknown_protocol_check_is_refused_by_name():
    """MUST-NOT: a protocol_check id not declared by the session is refused by name, never guessed."""
    request = _with_relation("implies", "relapse-check", "retreatment-check")
    request["session"]["definition_checks"][0]["left"]["protocol_check"] = "no-such-check"
    reply = run(request)
    assert reply["code"] == "refused", reply
    assert reply["problems"] == ["definition_unknown_protocol_check"]


def test_an_operand_naming_both_analysis_and_protocol_check_is_refused():
    """MUST-NOT: an operand carries exactly one of analysis or protocol_check."""
    request = _with_relation("implies", "relapse-check", "retreatment-check")
    request["session"]["definition_checks"][0]["left"]["analysis"] = request["session"]["analyses"][0]["id"]
    reply = run(request)
    assert reply["code"] == "refused", reply
    assert reply["problems"] == ["definition_operand_reference"]


def test_protocol_operands_in_a_v1_session_are_refused():
    """MUST-NOT: protocol operands are allowed only in v2 sessions."""
    request = copy.deepcopy(EXAMPLE)
    session = request["session"]
    session["decisions"] = []
    operand = _operand("retreatment-check")
    session["definition_checks"] = [_relation("trigger-link", "implies", operand, operand)]
    reply = run(request)
    assert reply["code"] == "refused", reply
    assert reply["problems"] == ["definition_protocol_requires_v2"]


def test_a_child_index_out_of_range_blocks_only_that_row():
    """MUST-NOT: a missing protocol child is a named row blocker, not a crash and not a guessed child."""
    request = _with_relation("implies", "relapse-check", "retreatment-check")
    request["session"]["definition_checks"][0]["right"]["child"] = 5
    reply = run(request)
    assert reply["code"] == "complete", reply
    row = _row(reply)
    assert row["blockers"] == ["definition_protocol_child_missing:retreatment-check"]
    assert row["checks"] == []
    assert row["code"] == "unresolved"


def test_a_missing_protocol_address_is_never_filled():
    """MUST-NOT: an address absent from the child's retained request is refused by name, not filled."""
    request = _with_relation("implies", "relapse-check", "retreatment-check")
    request["session"]["definition_checks"][0]["right"]["address"] = (
        "/request/signals/0/data/transitions/9/guard"
    )
    reply = run(request)
    assert reply["code"] == "refused", reply
    assert reply["problems"] == ["missing_location:anchor.address"]
