"""Version-2 sessions are admitted explicitly; version 1 is unchanged and never migrated (C2, CMP-1)."""

import copy

from TrialLedger.layer2 import run

EMPTY = {"schema_version": 1, "objects": [], "checks": [], "sections": []}


def _v1() -> dict:
    guide = run({"operation": "describe", "view": "design_session"})["result"]
    return copy.deepcopy(guide["example"])


def _v2(protocol: dict | None = None) -> dict:
    request = _v1()
    request["session"]["schema_version"] = 2
    request["session"]["protocol"] = copy.deepcopy(EMPTY if protocol is None else protocol)
    return request


def test_an_empty_v2_protocol_is_admitted_and_replays_the_v1_ledger():
    v1, v2 = run(_v1()), run(_v2())
    assert v2["code"] == "complete", v2
    assert [d["id"] for d in v2["result"]["decisions"]] == [d["id"] for d in v1["result"]["decisions"]]


def test_v2_requires_its_protocol_and_v1_refuses_one():
    missing = _v2()
    del missing["session"]["protocol"]
    assert run(missing)["problems"] == ["invalid_fields:session"]
    extra = _v1()
    extra["session"]["protocol"] = copy.deepcopy(EMPTY)
    assert run(extra)["problems"] == ["invalid_fields:session"]


def test_unknown_or_boolean_versions_refuse():
    for version in (3, 0, True, "2"):
        request = _v2()
        request["session"]["schema_version"] = version
        assert run(request)["problems"] == ["unsupported_session_version"], version


def test_protocol_translation_refusals_surface_with_their_named_code():
    protocol = copy.deepcopy(EMPTY)
    protocol["schema_version"] = True
    reply = run(_v2(protocol))
    assert reply["code"] == "refused"
    assert reply["problems"] == ["protocol_version"]


def test_a_mixed_version_revision_is_refused_not_migrated():
    first = run(_v1())
    revised = _v2()
    revised["session"]["revision"] = "two"
    from TrialLedger.layer2 import session_state

    revised["session"]["parent_digest"] = session_state.digest(_v1()["session"])
    revised["previous"] = {
        "session": _v1()["session"],
        "result": first["result"],
        "expected_result_digest": first["result_digest"],
    }
    reply = run(revised)
    assert reply["code"] == "refused"
    assert reply["problems"] == ["mixed_session_version_revision"]
