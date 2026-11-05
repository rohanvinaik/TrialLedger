"""Direct-call tests for the protocol projections (packet E, projections.md).

Unit behaviour only: these build request shapes and receipts. They never run a child through service,
the CLI or MCP, and say nothing clinical. Import isolation is asserted by the coordinator's static
contract test, not here.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from TrialLedger.layer2 import protocol_objects, protocol_projections

FIXTURES = (
    Path(__file__).resolve().parent.parent
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures"
)
CASES = {c["id"]: c for c in json.loads((FIXTURES / "objects.json").read_text())["cases"]}
SCHEDULE = {c["id"]: c for c in json.loads((FIXTURES / "schedule.json").read_text())["cases"]}
TARGET = {
    "kind": "new_trial",
    "ref": "draft",
    "scope": {"study": "draft", "population": "general", "arm": "all", "time": "entry", "version": "v1"},
}
PREMISES = {"p1": {"kind": "assertion"}, "p2": {"kind": "assertion"}}


def _adoptions(cases) -> dict:
    """One known, resolved adoption premise per object version in the fixtures (Rohan, 2026-11-04)."""
    out = {}
    for case in cases:
        objects = case["protocol"].get("objects")
        for item in objects if isinstance(objects, list) else []:
            if isinstance(item, dict) and isinstance(item.get("version"), str) and item["version"]:
                out[f"adopt:{item['id']}:{item['version']}"] = {
                    "kind": "adoption",
                    "payload": {
                        "objects": [{"id": item["id"], "version": item["version"]}],
                        "status": "known",
                        "resolution": "resolved",
                    },
                }
    return out


PREMISES.update(_adoptions(CASES.values()))
SOURCES = {
    "src": {"snapshot": {"study_ref": "ctg:NCT00000001:rev"}, "study": {"protocolSection": {"title": "x"}}}
}
STANDING = {
    "p1": {"status": "known", "resolution": "resolved", "basis": ["user:p1"]},
    "p2": {"status": "proposed", "resolution": "unresolved", "basis": ["user:p2"]},
}
for _id in _adoptions(CASES.values()):
    STANDING[_id] = {"status": "known", "resolution": "resolved", "basis": ["user:adoption"]}
WINDOW = [{"lower": "77", "upper": "91", "lower_inclusive": True, "upper_inclusive": True}]
THROUGH_80 = [{"lower": None, "upper": "80", "lower_inclusive": False, "upper_inclusive": True}]


def base() -> dict:
    return copy.deepcopy(CASES["valid_all_kinds"]["protocol"])


def build(protocol: dict) -> dict:
    return protocol_objects.validate_protocol(
        protocol, target=copy.deepcopy(TARGET), premises=dict(PREMISES), sources=copy.deepcopy(SOURCES)
    )


def edit(protocol: dict, identity: str, **fields) -> dict:
    obj = next(o for o in protocol["objects"] if o["id"] == identity)
    for key, value in fields.items():
        if key == "data":
            obj["data"].update(value)
        else:
            obj[key] = value
    return protocol


def run(protocol: dict, check: str, standing: dict | None = None) -> dict:
    return protocol_projections.project(
        build(protocol), check, premise_standing=copy.deepcopy(STANDING if standing is None else standing)
    )


def digest(request: dict) -> str:
    text = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def known(obj_id: str) -> dict:
    return {
        "id": "object:" + obj_id,
        "status": "proposed",
        "resolution": "unresolved",
        "basis": ["declared in draft"],
    }


def adoption(obj_id: str) -> dict:
    return {
        "id": "adoption:" + obj_id,
        "status": "proposed",
        "resolution": "unresolved",
        "basis": [f"no adoption support declared for {obj_id}"],
    }


def entry(premise: str) -> dict:
    return {"id": "premise:" + premise, **STANDING[premise]}


def adopt(protocol: dict, identity: str, status: str = "known", resolution: str = "resolved") -> dict:
    """Adopt one object by its own adoption premise; returns the premise standing to hand to `run`."""
    obj = next(o for o in protocol["objects"] if o["id"] == identity)
    premise = f"adopt:{identity}:{obj['version']}"
    obj["support"] = [premise]
    return {premise: {"status": status, "resolution": resolution, "basis": [f"user:adopts {identity}"]}}


def ids(entries: list[dict]) -> list[str]:
    return [e["id"] for e in entries]


def week12() -> dict:
    """a1 (assessment, condition removed) + c1 (collection) with the TIM-1 numbers."""
    protocol = base()
    edit(
        protocol,
        "a1",
        data={
            "anchor": "randomization",
            "unit": "day",
            "nominal": "84",
            "permitted": WINDOW,
            "condition": None,
        },
    )
    edit(protocol, "c1", data={"availability": THROUGH_80})
    return protocol


# --- schedule -------------------------------------------------------------------------------------------


def test_registry_names():
    assert protocol_projections.PROJECTIONS["schedule"] == "schedule_window_coverage:1"
    assert protocol_projections.PROJECTIONS["external_method"] == "external_method_declaration:1"
    assert "definition" not in protocol_projections.PROJECTIONS


def test_schedule_child_request_receipt_and_digest():
    protocol = week12()
    out = run(protocol, "k-sched")
    assert out["kind"] == "schedule" and out["projection"] == "schedule_window_coverage:1"
    assert out["unresolved"] == [] and out["not_computed"] is None
    (child,) = out["children"]
    scope = json.dumps(build(protocol)["checks"]["k-sched"]["scope"], sort_keys=True, separators=(",", ":"))
    signal = child["request"]["signals"][0]
    assert child["id"] == signal["id"] == "k-sched:schedule_window_coverage"
    assert set(child["request"]) == {"operation", "signals"} and child["request"]["operation"] == "signals"
    assert signal["kind"] == "schedule_coverage" and signal["claims"] == []
    assert signal["data"] == {
        "scope": scope,
        "anchor": "randomization",
        "unit": "day",
        "nominal": "84",
        "permitted": WINDOW,
        "available": THROUGH_80,
    }
    assert ids(signal["support"]) == ["object:a1", "adoption:a1", "object:c1", "adoption:c1"]
    receipt = child["receipt"]
    assert set(receipt) == {
        "projection", "version", "check", "objects", "premises", "target", "scope",
        "bindings", "role_support", "conditions", "request_digest", "closure",
    }  # fmt: skip
    assert (receipt["projection"], receipt["version"], receipt["check"]) == (
        "schedule_window_coverage",
        "1",
        "k-sched",
    )
    assert receipt["objects"] == ["a1", "c1"] and receipt["premises"] == []
    assert receipt["target"] == TARGET and receipt["bindings"] == [{"projection": "named"}]
    assert receipt["request_digest"] == digest(child["request"])
    assert receipt["conditions"] == []
    assert ids(receipt["role_support"]["permitted"]) == ["object:a1", "adoption:a1"]
    assert receipt["role_support"]["nominal"] == receipt["role_support"]["permitted"]
    assert ids(receipt["role_support"]["available"]) == ["object:c1", "adoption:c1"]


def test_tim1_numbers_give_schedule_fixture_data_except_scope():
    out = run(week12(), "k-sched")
    data = dict(out["children"][0]["request"]["signals"][0]["data"])
    fixture = dict(SCHEDULE["TIM-1"]["data"])
    assert isinstance(data.pop("scope"), str) and fixture.pop("scope")
    assert json.dumps(data, sort_keys=True) == json.dumps(fixture, sort_keys=True)


def test_schedule_claims_are_copied_from_the_check():
    protocol = week12()
    claims = [{"id": "nominal", "claim": "nominal"}]
    next(c for c in protocol["checks"] if c["id"] == "k-sched")["claims"] = claims
    signal = run(protocol, "k-sched")["children"][0]["request"]["signals"][0]
    assert signal["claims"] == claims and signal["claims"] is not claims


def test_empty_support_gives_adoption_entry_never_known_resolved():
    out = run(week12(), "k-sched")
    entries = out["children"][0]["request"]["signals"][0]["support"]
    adopt = next(e for e in entries if e["id"] == "adoption:a1")
    assert adopt["resolution"] == "unresolved" and adopt["basis"] == ["no adoption support declared for a1"]
    assert not any(e["status"] == "known" and e["resolution"] == "resolved" for e in entries)


def test_known_object_without_support_still_gets_unresolved_adoption_entry():
    protocol = week12()
    edit(protocol, "a1", standing={"status": "known", "resolution": "resolved", "basis": ["b"]})
    entries = run(protocol, "k-sched")["children"][0]["receipt"]["role_support"]["permitted"]
    assert entries[0] == {"id": "object:a1", "status": "known", "resolution": "resolved", "basis": ["b"]}
    assert entries[1]["id"] == "adoption:a1" and entries[1]["status"] == "known"
    assert entries[1]["resolution"] == "unresolved"


def test_proposed_support_premise_stays_in_support_and_role_support():
    protocol = week12()
    held = adopt(protocol, "a1", "proposed", "unresolved")
    out = run(protocol, "k-sched", standing={**STANDING, **held})
    child = out["children"][0]
    support = child["request"]["signals"][0]["support"]
    assert {"id": "premise:adopt:a1:e1", **held["adopt:a1:e1"]} in support
    assert ids(child["receipt"]["role_support"]["permitted"]) == ["object:a1", "premise:adopt:a1:e1"]
    assert not any(e["id"] == "adoption:a1" for e in support)
    assert child["receipt"]["premises"] == ["adopt:a1:e1"]


def test_proposed_collection_leaves_assessment_roles_untouched():
    plain = run(week12(), "k-sched")["children"][0]["receipt"]["role_support"]
    protocol = week12()
    edit(protocol, "c1", standing={"status": "proposed", "resolution": "unresolved", "basis": ["c"]})
    held = adopt(protocol, "c1", "proposed", "unresolved")
    roles = run(protocol, "k-sched", standing={**STANDING, **held})["children"][0]["receipt"]["role_support"]
    assert roles["permitted"] == plain["permitted"] and roles["nominal"] == plain["nominal"]
    for role in ("permitted", "nominal"):
        assert not any(e["id"].endswith("c1") or e["id"] == "premise:adopt:c1:e1" for e in roles[role])
    assert ids(roles["available"]) == ["object:c1", "premise:adopt:c1:e1"]


def test_known_assessment_beside_proposed_collection_keeps_known_roles():
    protocol = week12()
    edit(protocol, "a1", standing={"status": "known", "resolution": "resolved", "basis": ["a"]})
    held = {**adopt(protocol, "a1"), **adopt(protocol, "c1", "proposed", "unresolved")}
    roles = run(protocol, "k-sched", standing={**STANDING, **held})["children"][0]["receipt"]["role_support"]
    assert all(e["status"] == "known" and e["resolution"] == "resolved" for e in roles["permitted"])
    assert roles["available"][0]["status"] == "proposed"


def test_check_support_premises_follow_object_entries():
    protocol = week12()
    next(c for c in protocol["checks"] if c["id"] == "k-sched")["support"] = ["p2"]
    child = run(protocol, "k-sched")["children"][0]
    assert ids(child["request"]["signals"][0]["support"])[-1] == "premise:p2"
    assert child["receipt"]["premises"] == ["p2"]
    # Corrected after external review: check-wide support is explicit in every role, never inferred.
    roles = child["receipt"]["role_support"]
    assert roles and all(any(e["id"] == "premise:p2" for e in r) for r in roles.values())
    assert all("premise:p2" in ids for ids in child["request"]["signals"][0]["role_support"].values())


def test_assessment_condition_always_appears_in_conditions():
    protocol = week12()
    condition = base()["objects"][4]["data"]["condition"]
    assert condition is not None
    edit(protocol, "a1", data={"condition": condition})
    out = run(protocol, "k-sched")
    assert out["children"][0]["receipt"]["conditions"] == [{"object": "a1", "condition": condition}]


def test_scope_mismatch_yields_unresolved_and_no_child():
    protocol = week12()
    scope = copy.deepcopy(next(o for o in protocol["objects"] if o["id"] == "c1")["scope"])
    scope["context"] = {"cohort": "other", "phase": None, "arm": None}
    edit(protocol, "c1", scope=scope)
    out = run(protocol, "k-sched")
    assert out["children"] == []
    assert out["unresolved"] == [{"code": "projection_scope_mismatch", "objects": ["c1"], "premises": []}]


def test_open_context_is_never_aligned_to_a_concrete_one():
    protocol = week12()
    scope = copy.deepcopy(next(o for o in protocol["objects"] if o["id"] == "c1")["scope"])
    scope["context"]["cohort"] = None
    edit(protocol, "c1", scope=scope)
    out = run(protocol, "k-sched")
    assert out["children"] == [] and out["unresolved"][0]["objects"] == ["c1"]


def test_scope_too_long_is_unresolved():
    big = copy.deepcopy(TARGET)
    for key in ("study", "population", "arm", "time"):
        big["scope"][key] = "s" * 300
    index = _build_with_target(base(), big)
    out = protocol_projections.project(index, "k-sched", premise_standing=copy.deepcopy(STANDING))
    assert out["children"] == []
    assert out["unresolved"][0]["code"] == "projection_scope_too_long"


def _build_with_target(protocol: dict, target: dict) -> dict:
    for item in [*protocol["objects"], *protocol["checks"]]:
        item["scope"]["target"] = copy.deepcopy(target)
    return protocol_objects.validate_protocol(
        protocol, target=copy.deepcopy(target), premises=dict(PREMISES), sources=copy.deepcopy(SOURCES)
    )


def test_resembling_labels_never_create_a_binding():
    protocol = week12()
    twin = copy.deepcopy(next(o for o in protocol["objects"] if o["id"] == "a1"))
    twin["id"] = "a1-copy"
    twin["data"]["permitted"] = [
        {"lower": "0", "upper": "1", "lower_inclusive": True, "upper_inclusive": True}
    ]
    protocol["objects"].append(twin)
    out = run(protocol, "k-sched")
    data = out["children"][0]["request"]["signals"][0]["data"]
    assert data["permitted"] == WINDOW and out["children"][0]["receipt"]["objects"] == ["a1", "c1"]


def test_repeated_projection_has_the_same_digest_and_does_not_mutate():
    protocol = week12()
    index = build(protocol)
    index_before, standing = copy.deepcopy(index), copy.deepcopy(STANDING)
    first = protocol_projections.project(index, "k-sched", premise_standing=standing)
    second = protocol_projections.project(index, "k-sched", premise_standing=standing)
    assert (
        first["children"][0]["receipt"]["request_digest"]
        == second["children"][0]["receipt"]["request_digest"]
    )
    assert index == index_before and standing == STANDING
    first["children"][0]["request"]["signals"][0]["data"]["permitted"][0]["lower"] = "0"
    first["children"][0]["receipt"]["scope"]["context"]["cohort"] = "z"
    assert index == index_before


def test_missing_premise_standing_and_bad_check_id_raise_named_codes():
    protocol = week12()
    adopt(protocol, "a1")
    with pytest.raises(ValueError, match="^projection_missing_premise_standing$"):
        run(protocol, "k-sched", standing={})
    with pytest.raises(ValueError, match="^projection_invalid_standing$"):
        run(protocol, "k-sched", standing={"adopt:a1:e1": {"status": "known"}})
    with pytest.raises(ValueError, match="^projection_unknown_check$"):
        run(protocol, "nope")
    with pytest.raises(ValueError, match="^projection_unknown_check$"):
        protocol_projections.project(build(protocol), 3, premise_standing={})  # type: ignore[arg-type]


# --- other registry rows --------------------------------------------------------------------------------


def test_finite_policy_row():
    protocol = base()
    out = run(protocol, "k-pol")
    (child,) = out["children"]
    signal = child["request"]["signals"][0]
    pol = next(o for o in protocol["objects"] if o["id"] == "pol1")
    assert signal["kind"] == "finite_policy" and signal["data"] == pol["data"]["model"]
    assert signal["data"] is not pol["data"]["model"] and signal["claims"] == []
    assert child["id"] == "k-pol:finite_policy_model"
    assert ids(child["receipt"]["role_support"]["model"]) == [
        "object:pol1",
        "adoption:pol1",
        "object:m1",
        "premise:adopt:m1:e1",
        # Rohan (2026-11-05): a linked object (m1, reached through the policy binding) gates together with
        # what it references, here its baseline measurement m0, which is not adopted.
        "object:m0",
        "adoption:m0",
        "premise:p2",
    ]
    assert child["receipt"]["objects"] == ["pol1", "m1"]
    assert child["receipt"]["closure"] == ["pol1", "m1", "m0"]
    assert child["receipt"]["request_digest"] == digest(child["request"])


def test_binomial_row_builds_assumptions_from_premise_standing():
    protocol = base()
    out = run(protocol, "k-bin")
    (child,) = out["children"]
    signal = child["request"]["signals"][0]
    scope = json.dumps(build(protocol)["checks"]["k-bin"]["scope"], sort_keys=True, separators=(",", ":"))
    assert signal["kind"] == "binomial_design"
    assert signal["data"] == {
        "scope": scope,
        "model": "model-q",
        "direction": "greater",
        "n": 10,
        "critical_count": 6,
        "p0": "1/5",
        "p1": "3/5",
        "assumptions": [
            {"role": "fixed_n", "ref": "premise:p1", "version": "e1", **STANDING["p1"]},
            {"role": "fixed_n", "ref": "premise:p2", "version": "e1", **STANDING["p2"]},
            {"role": "iid_binary", "ref": "premise:p1", "version": "e1", **STANDING["p1"]},
        ],
    }
    roles = child["receipt"]["role_support"]
    assert ids(roles["parameters"]) == [
        "object:ef1",
        "adoption:ef1",
        "object:ep1",
        "premise:adopt:ep1:e1",
    ]
    assert ids(roles["assumptions"]) == ["premise:p1", "premise:p2"]
    assert entry("p2") in roles["assumptions"]


def test_binomial_assumption_uses_efficacy_version_not_premise_version():
    protocol = base()
    edit(protocol, "ef1", version="edition-9")
    data = run(protocol, "k-bin")["children"][0]["request"]["signals"][0]["data"]
    assert {a["version"] for a in data["assumptions"]} == {"edition-9"}


def test_estimand_child_has_no_claims_key_and_unlinked_data_is_unchanged():
    protocol = base()
    for obj in protocol["objects"]:
        if obj["kind"] == "collection":
            obj["data"]["event_handling"] = None
    child = run(protocol, "k-est")["children"][0]
    signal = child["request"]["signals"][0]
    est = next(o for o in protocol["objects"] if o["id"] == "est1")
    assert signal["kind"] == "estimand" and signal["data"] == est["data"] and "claims" not in signal
    assert ids(child["receipt"]["role_support"]["estimand"]) == ["object:est1", "adoption:est1"]


def test_a_linked_collection_supplies_the_estimand_collection_plan_with_its_standing():
    """Declared once on the collection (Rohan, 2026-11-04): event_handling.action drives the plan row."""
    protocol = base()
    collection = next(o for o in protocol["objects"] if o["kind"] == "collection")
    handling = collection["data"]["event_handling"]
    child = run(protocol, "k-est")["children"][0]
    plan = child["request"]["signals"][0]["data"]["collection_plan"]
    row = next(r for r in plan if r["requirement"] == handling["requirement"])
    assert row["action"] == handling["action"]
    assert (row["status"], row["resolution"]) == (
        collection["standing"]["status"],
        collection["standing"]["resolution"],
    )
    assert collection["id"] in child["receipt"]["objects"]


def test_a_differing_declaration_is_a_named_conflict_not_an_override():
    protocol = base()
    collection = next(o for o in protocol["objects"] if o["kind"] == "collection")
    handling = collection["data"]["event_handling"]
    est = next(o for o in protocol["objects"] if o["id"] == handling["estimand"])
    est["data"]["collection_plan"] = [
        {
            "requirement": handling["requirement"],
            "action": "stop" if handling["action"] == "collect" else "collect",
            "status": "known",
            "resolution": "resolved",
            "basis": ["user:invented"],
        }
    ]
    out = run(protocol, "k-est")
    assert out["children"] == []
    assert [u["code"] for u in out["unresolved"]] == ["projection_collection_plan_conflict"]


def test_dependencies_child_has_no_claims_key_and_includes_measurement_support():
    protocol = base()
    child = run(protocol, "k-dep")["children"][0]
    signal = child["request"]["signals"][0]
    ep = next(o for o in protocol["objects"] if o["id"] == "ep1")
    assert signal["kind"] == "dependencies" and signal["data"] == ep["data"]["dependencies"]
    assert "claims" not in signal
    assert ids(child["receipt"]["role_support"]["dependencies"]) == [
        "object:ep1", "premise:adopt:ep1:e1", "object:m1", "premise:adopt:m1:e1",
        "object:m0", "adoption:m0",
    ]  # fmt: skip
    # The change endpoint reaches m1 through its variable link; m1's baseline m0 gates it (Rohan, 2026-11-05).
    assert child["receipt"]["objects"] == ["ep1", "m1"]


@pytest.mark.parametrize("kind", ["temporal", "decision_table"])
def test_single_named_binding_becomes_the_request(kind):
    protocol = base()
    name = protocol_projections.PROJECTIONS[kind].split(":")[0]
    check = next(c for c in protocol["checks"] if c["kind"] == kind)
    check["objects"], check["support"] = ["m1"], ["p1"]
    check["bindings"] = [{"projection": name, "data": {"x": [1]}}]
    out = run(protocol, check["id"])
    (child,) = out["children"]
    signal = child["request"]["signals"][0]
    assert signal["kind"] == kind and signal["data"] == {"x": [1]} and signal["id"] == f"{check['id']}:{name}"
    assert ids(child["receipt"]["role_support"]["data"]) == ["object:m1", "premise:adopt:m1:e1", "premise:p1"]
    assert ids(signal["support"]) == ["object:m1", "premise:adopt:m1:e1", "premise:p1"]


@pytest.mark.parametrize(
    "bindings",
    [
        [],
        [{"projection": "named"}],
        [{"projection": "temporal_request"}],
        [{"projection": "temporal_request", "data": {}}, {"projection": "temporal_request", "data": {}}],
        [{"projection": "other", "data": {}}],
        [{"projection": "temporal_request", "data": {}, "extra": 1}],
        [{"projection": "temporal_request", "data": []}],
    ],
)
def test_other_binding_shapes_are_unresolved_without_child(bindings):
    protocol = base()
    check = next(c for c in protocol["checks"] if c["kind"] == "temporal")
    check["bindings"] = bindings
    out = run(protocol, check["id"])
    assert out["children"] == []
    assert [u["code"] for u in out["unresolved"]] == ["projection_binding_shape"]


def test_external_method_yields_no_child_and_declared_missing_inputs():
    protocol = base()
    for check in ("k-ext", "k-ext-alone"):
        out = run(protocol, check)
        xm = next(o for o in protocol["objects"] if o["id"] == "xm1")
        assert out["children"] == [] and out["unresolved"] == []
        assert out["not_computed"] == {
            "method": "xm1",
            "definition": xm["data"]["definition"],
            "missing": ["input_z"],
            "inputs": xm["data"]["inputs"],
        }


def test_definition_is_unresolved_slice_5():
    out = run(base(), "k-def")
    assert out["children"] == [] and out["not_computed"] is None
    assert out["unresolved"] == [{"code": "projection_slice_5", "objects": ["m1"], "premises": []}]


def test_scope_mismatch_on_bound_policy_object_blocks_policy_child():
    protocol = base()
    scope = copy.deepcopy(next(o for o in protocol["objects"] if o["id"] == "m1")["scope"])
    scope["context"]["cohort"] = "other"
    edit(protocol, "m1", scope=scope)
    out = run(protocol, "k-pol")
    assert out["children"] == [] and out["unresolved"][0]["objects"] == ["m1"]


def test_claim_kind_children_carry_role_support_ids_present_in_support():
    protocol = base()
    for check in ("k-pol", "k-bin"):
        signal = run(protocol, check)["children"][0]["request"]["signals"][0]
        listed = {e["id"] for e in signal["support"]}
        assert signal["role_support"] and all(set(v) <= listed for v in signal["role_support"].values())
    pol = run(protocol, "k-pol")["children"][0]["request"]["signals"][0]
    assert list(pol["role_support"]) == ["model"]
    binom = run(protocol, "k-bin")["children"][0]["request"]["signals"][0]
    assert binom["role_support"]["assumptions"] == ["premise:p1", "premise:p2"]
    assert list(binom["role_support"]) == ["parameters", "assumptions"]


def test_tim1_schedule_role_support_separates_assessment_and_collection():
    protocol = week12()
    held = {**adopt(protocol, "a1"), **adopt(protocol, "c1", "proposed", "unresolved")}
    child = run(protocol, "k-sched", standing={**STANDING, **held})["children"][0]
    signal = child["request"]["signals"][0]
    assert signal["role_support"] == {
        "permitted": ["object:a1", "premise:adopt:a1:e1"],
        "nominal": ["object:a1", "premise:adopt:a1:e1"],
        "available": ["object:c1", "premise:adopt:c1:e1"],
    }
    assert set(sum(signal["role_support"].values(), [])) <= {e["id"] for e in signal["support"]}
    assert child["receipt"]["request_digest"] == digest(child["request"])


def test_unclaimed_kinds_carry_no_role_support():
    protocol = base()
    for check in ("k-est", "k-dep"):
        assert "role_support" not in run(protocol, check)["children"][0]["request"]["signals"][0]
    check = next(c for c in protocol["checks"] if c["kind"] == "temporal")
    check["bindings"] = [{"projection": "temporal_request", "data": {"x": 1}}]
    assert "role_support" not in run(protocol, check["id"])["children"][0]["request"]["signals"][0]
