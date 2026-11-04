"""Intent tests: a complete finite policy table is not a safe policy, and no gap is hidden."""

import copy
import json
from pathlib import Path

import pytest

from TrialLedger.layer2 import construction as c
from TrialLedger.layer2 import protocol_policies as pp

FIXTURES = (
    Path(__file__).resolve().parent.parent
    / "openspec/changes/connect-protocol-design-workflow/interface/fixtures/policy.json"
)
FIXTURE = json.loads(FIXTURES.read_text())
CASES = {case["id"]: case for case in FIXTURE["cases"]}
KIND = "finite_policy"
X = c.expanded
SP = c.Subject(kind="study_procedure", referent="")


def lit(key, positive=True):
    return c.literal(
        subject=SP,
        predicate=c.Predicate(kind="measurement", key=key),
        value=c.Value(kind="boolean"),
        polarity="positive" if positive else "negative",
        time=None,
        qualifiers=c.Always(),
        evidence=(),
    )


def variable(identity):
    return {"id": identity, "values": [X(lit(identity)), X(lit(identity, False))]}


TAUT = c.AnyOf(parts=(lit("x"), c.Not(part=lit("x"))))


def rule(status="known", resolution="resolved"):
    return {"ref": "r", "version": "1", "status": status, "resolution": resolution, "basis": ["b"]}


def action(identity):
    return {"id": identity, "scope": {"level": "cohort", "ref": "draft"}, "description": identity}


def transition(identity, source, target, guard, actions):
    return {"id": identity, "from": source, "to": target, "guard": X(guard), "actions": actions}


def policy(states, initial, terminal, actions, transitions, **extra):
    data = {
        "scope": "draft:test",
        "version": "1",
        "variables": [variable("x")],
        "constraints": [],
        "states": states,
        "initial": initial,
        "terminal": terminal,
        "actions": [action(name) for name in actions],
        "transitions": transitions,
        "prohibitions": [],
        "invariants": [],
    }
    data.update(extra)
    return data


def claim(name, limit=64, identity=None):
    return {"id": identity or name, "claim": name, "witness_limit": limit}


def run(data, claims=None):
    if claims is None:
        return pp.evaluate(KIND, data)
    return pp.check(KIND, data, claims)


def by_claim(result):
    return {row["claim"]: row for row in result["value"]["claims"]}


@pytest.mark.parametrize("case_id", list(CASES))
def test_fixture_case(case_id):
    case = CASES[case_id]
    data = copy.deepcopy(case["data"])
    result = run(data, case["claims"])
    expect = case["expect"]
    assert set(result) == {
        "code",
        "value",
        "blockers",
        "rule",
        "support_status",
        "determining_ids",
        "support_resolution",
    }
    assert result["code"] == expect["code"]
    assert result["rule"] == "policy.finite_reachable_states:1"
    assert result["blockers"] == sorted(set(result["blockers"]))
    if "support_status" in expect:
        assert result["support_status"] == expect["support_status"]
    if "support_resolution" in expect:
        assert result["support_resolution"] == expect["support_resolution"]
    if "determining_ids" in expect:
        assert result["determining_ids"] == expect["determining_ids"]
    for key, wanted in expect.get("reachability", {}).items():
        assert result["value"]["reachability"][key] == wanted
    if "transition_target_conflicts" in expect:
        found = [row["transition"] for row in result["value"]["transition_target_conflicts"]]
        assert found == expect["transition_target_conflicts"]
    rows = by_claim(result)
    assert set(rows) == set(expect["claims"])
    for name, wanted in expect["claims"].items():
        row = rows[name]
        assert row["outcome"] == wanted["outcome"]
        assert row["violations_found"] == wanted["violations_found"]
        assert len(row["witnesses"]) == wanted["witnesses_returned"]
        assert row["reasons"] == wanted["reasons"]
        if "standing" in wanted:
            assert row["standing"] == wanted["standing"]
    work = result["value"]["work"]
    assert work["used"] <= work["reserved"] == pp.work_reservation(case["data"])
    assert case["data"] == data


@pytest.mark.parametrize("case", FIXTURE["malformed"], ids=lambda case: case["id"])
def test_fixture_malformed(case):
    data = copy.deepcopy(case["data"])
    with pytest.raises(ValueError) as error:
        run(data, case["claims"])
    assert str(error.value) == case["refusal"]
    if case["claims"] is None:
        with pytest.raises(ValueError) as error:
            pp.work_reservation(data)
        assert str(error.value) == case["refusal"]


def test_prohibition_never_removes_its_violating_valuations():
    declared = run(copy.deepcopy(CASES["POL-1-covered-but-unsafe"]["data"]))
    without = copy.deepcopy(CASES["POL-1-covered-but-unsafe"]["data"])
    without["prohibitions"] = []
    plain = run(without)
    assert [row["feasible_valuations"] for row in declared["value"]["feasibility"]] == [16, 16]
    assert declared["value"]["reachability"] == {
        **plain["value"]["reachability"],
        "guard_evaluations": declared["value"]["reachability"]["guard_evaluations"],
    }
    assert by_claim(declared)["coverage"]["outcome"] == "covered"
    assert by_claim(declared)["prohibition"]["violations_found"] == 3
    assert by_claim(plain)["prohibition"]["outcome"] == "not_declared"
    assert declared["code"] == "violated" and plain["code"] == "satisfied"


def test_violation_witness_trace_is_shortest_and_names_the_offending_transition():
    result = run(copy.deepcopy(CASES["POL-1-covered-but-unsafe"]["data"]))
    witnesses = by_claim(result)["prohibition"]["witnesses"]
    assert len(witnesses) == 3
    for item in witnesses:
        steps = item["trace"]
        assert [step["state"] for step in steps] == ["interim"]
        last = steps[-1]
        assert last["state"] == "interim"
        assert last["transition"] == "t-low"
        assert last["actions"] == ["select_low_dose"]
        assert last["valuation"]["low_safety"]["polarity"] == "positive"
        assert item["element"]["id"] == "no-low-dose-with-low-dose-signal"
    indexes = [json.dumps(item["trace"][-1]["valuation"], sort_keys=True) for item in witnesses]
    assert len(set(indexes)) == 3


def test_no_row_priority_and_no_action_only_dedup():
    same_actions = run(copy.deepcopy(CASES["POL-3-same-actions-different-targets"]["data"]))
    assert by_claim(same_actions)["exclusivity"]["outcome"] == "competing"
    assert by_claim(same_actions)["exclusivity"]["violations_found"] == 1
    duplicates = run(copy.deepcopy(CASES["POL-3-identical-duplicate-rows-not-deduplicated"]["data"]))
    assert by_claim(duplicates)["exclusivity"]["violations_found"] == 2
    reordered = copy.deepcopy(CASES["POL-3-same-actions-different-targets"]["data"])
    reordered["transitions"].reverse()
    after = run(reordered)
    assert by_claim(after)["exclusivity"]["outcome"] == "competing"
    assert by_claim(after)["coverage"]["outcome"] == "covered"


def test_terminal_state_is_exempt_from_coverage_but_not_invariants():
    result = run(copy.deepcopy(CASES["POL-4-terminal-exempt-from-coverage-not-invariants"]["data"]))
    rows = by_claim(result)
    assert rows["coverage"]["outcome"] == "covered"
    assert rows["invariant"]["outcome"] == "violation"
    assert rows["invariant"]["witnesses"][0]["trace"][-1]["state"] == "end"
    assert rows["invariant"]["witnesses"][0]["trace"][-1]["transition"] is None
    assert result["code"] == "violated"


def test_acyclic_dead_end_is_not_termination_and_no_fairness_is_assumed():
    result = run(
        copy.deepcopy(CASES["POL-5-acyclic-dead-end-is-not-termination"]["data"]), [claim("termination")]
    )
    row = by_claim(result)["termination"]
    assert row["outcome"] == "not_established"
    assert row["reasons"] == ["dead_end"]
    assert row["witnesses"][0]["trace"][-1]["transition"] is None
    assert result["value"]["fairness"] == "not_assumed"
    assert result["value"]["operating_characteristics"] == "not_computed"
    assert result["value"]["patient_outcomes"] == "not_modelled"
    assert result["value"]["guarantee"] == "exhaustive_over_declared_finite_model"


def test_reachable_cycle_blocks_termination_with_a_witness():
    data = policy(
        ["a", "b"],
        ["a"],
        ["b"],
        ["go", "stay"],
        [
            transition("loop", "a", "a", lit("x"), ["stay"]),
            transition("leave", "a", "b", c.Not(part=lit("x")), ["go"]),
        ],
    )
    result = run(data, [claim("coverage"), claim("termination")])
    rows = by_claim(result)
    assert rows["coverage"]["outcome"] == "covered"
    assert rows["termination"]["reasons"] == ["reachable_cycle"]
    assert rows["termination"]["witnesses"][0]["trace"][-1]["transition"] == "loop"
    assert "policy_not_established:termination" in result["blockers"]


def test_witness_limit_zero_leaves_outcome_and_count_unchanged():
    base = copy.deepcopy(CASES["POL-1-covered-but-unsafe"]["data"])
    full = by_claim(run(base, [claim("prohibition", 64)]))["prohibition"]
    for limit in (0, 1, 2):
        row = by_claim(run(base, [claim("prohibition", limit)]))["prohibition"]
        assert row["outcome"] == full["outcome"] == "violation"
        assert row["violations_found"] == 3
        assert len(row["witnesses"]) == limit
        assert row["witnesses_omitted"] == 3 - limit
        assert row["witnesses"] == full["witnesses"][:limit]


def test_empty_feasible_initial_model_is_inconsistent_never_vacuously_safe():
    result = run(
        copy.deepcopy(CASES["POL-7-empty-feasible-initial-model"]["data"]), [claim(n) for n in pp.CLAIMS]
    )
    assert result["code"] == "inconsistent_domain"
    assert result["blockers"] == ["policy_inconsistent_domain"]
    assert {row["outcome"] for row in result["value"]["claims"]} == {"inconsistent_domain"}
    assert result["value"]["reachability"]["initial_nodes"] == 0
    assert result["value"]["reachability"]["reachable_states"] == []


def test_infeasible_transition_target_is_reported_with_its_attempted_transition():
    result = run(copy.deepcopy(CASES["POL-7-transition-into-infeasible-target"]["data"]), [claim("coverage")])
    conflicts = result["value"]["transition_target_conflicts"]
    assert [row["transition"] for row in conflicts] == ["s-t"]
    assert (conflicts[0]["from"], conflicts[0]["to"]) == ("s", "t")
    assert conflicts[0]["trace"][-1]["transition"] == "s-t"
    assert result["code"] == "violated"
    assert "policy_transition_target_infeasible:s-t" in result["blockers"]
    assert by_claim(result)["coverage"]["outcome"] == "covered"
    assert [row["feasible_valuations"] for row in result["value"]["feasibility"]] == [2, 0, 2]


def test_external_inputs_vary_between_steps():
    data = copy.deepcopy(CASES["POL-2-inputs-vary-between-steps"]["data"])
    result = run(data, [claim("coverage")])
    reach = result["value"]["reachability"]
    assert "d" in reach["reachable_states"] and reach["unreachable_states"] == ["z"]
    # d is entered only from c on not-x, while c was entered on x: the input changed between steps.
    fixed_input = [t["id"] for t in data["transitions"] if t["id"] in ("a-c", "c-d")]
    assert fixed_input == ["a-c", "c-d"]
    assert reach["reachable_nodes"] == 8


def test_policy_state_cannot_be_declared_or_supplied():
    ok = copy.deepcopy(CASES["POL-5-terminating-policy"]["data"])
    reserved = copy.deepcopy(FIXTURE["malformed"][0]["data"])
    with pytest.raises(ValueError, match="^policy_reserved_variable$"):
        run(reserved)
    with pytest.raises(ValueError, match="^policy_data_fields$"):
        run({**ok, "policy_state": "s"})
    ok_result = run(ok)
    assert ok_result["code"] == "satisfied"


def test_termination_is_computed_only_when_requested():
    data = copy.deepcopy(CASES["POL-2-inputs-vary-between-steps"]["data"])
    implicit = run(data)
    assert set(by_claim(implicit)) == {"coverage", "exclusivity", "prohibition", "invariant"}
    assert implicit["code"] == "satisfied"
    requested = run(data, [claim("termination")])
    assert by_claim(requested)["termination"]["outcome"] == "not_established"
    assert requested["code"] == "violated"


def test_proposed_prohibition_keeps_raw_violation_but_withholds_support():
    result = run(
        copy.deepcopy(CASES["POL-1-proposed-prohibition-keeps-raw-violation"]["data"]), [claim("prohibition")]
    )
    row = by_claim(result)["prohibition"]
    assert row["outcome"] == "violation" and row["violations_found"] == 3
    assert row["standing"] == "proposed_refused"
    assert result["support_status"] == "proposed"
    assert result["determining_ids"] == ["no-low-dose-with-low-dose-signal"]


def test_unresolved_rule_is_not_accepted_support():
    data = copy.deepcopy(CASES["POL-4-terminal-exempt-from-coverage-not-invariants"]["data"])
    data["invariants"][0]["rule"] = rule("known", "unresolved")
    result = run(data, [claim("invariant")])
    assert by_claim(result)["invariant"]["standing"] == "binding_unresolved"
    assert result["support_status"] == "known"
    assert result["support_resolution"] == "unresolved"
    data["invariants"][0]["rule"] = rule("interpolated")
    assert run(data, [claim("invariant")])["support_status"] == "interpolated"


def test_no_rules_means_no_support_status():
    result = run(copy.deepcopy(CASES["POL-5-terminating-policy"]["data"]))
    assert result["support_status"] is None and result["determining_ids"] == []
    assert result["support_resolution"] is None
    assert {row["standing"] for row in result["value"]["claims"]} == {"no_rule_support"}


def test_work_limit_returns_limit_with_unexecuted_claims(monkeypatch):
    data = copy.deepcopy(CASES["POL-1-covered-but-unsafe"]["data"])
    reserved = pp.work_reservation(data)
    monkeypatch.setattr(pp, "MAX_POLICY_WORK", reserved - 1)
    result = run(data)
    assert result["code"] == "limit"
    assert result["blockers"] == ["policy_work_limit"]
    assert {row["outcome"] for row in result["value"]["claims"]} == {"not_executed"}
    assert result["value"]["work"] == {"reserved": reserved, "used": 0}
    monkeypatch.setattr(pp, "MAX_POLICY_WORK", reserved)
    assert run(data)["code"] == "violated"


def test_work_used_never_exceeds_reservation():
    for case in CASES.values():
        work = run(copy.deepcopy(case["data"]))["value"]["work"]
        assert 0 < work["used"] <= work["reserved"]


def test_reservation_formula():
    data = copy.deepcopy(CASES["POL-1-covered-but-unsafe"]["data"])
    assert pp.work_reservation(data) == 2 * 16 * (0 + 1 + 0) + 16 * 3


def test_input_is_not_mutated_and_repeat_is_identical():
    data = copy.deepcopy(CASES["POL-1-covered-but-unsafe"]["data"])
    before = copy.deepcopy(data)
    first = run(data)
    assert data == before
    assert run(data) == first
    json.dumps(first)


def test_wrong_kind_refuses():
    data = copy.deepcopy(CASES["POL-5-terminating-policy"]["data"])
    with pytest.raises(ValueError, match="^unsupported_policy_kind$"):
        pp.evaluate("decision_table", data)
    with pytest.raises(ValueError, match="^unsupported_policy_kind$"):
        pp.check("decision_table", data, [claim("coverage")])


def test_prohibition_scoped_to_another_state_does_not_fire():
    data = copy.deepcopy(CASES["POL-1-covered-but-unsafe"]["data"])
    data["prohibitions"][0]["state"] = "selected"
    row = by_claim(run(data))["prohibition"]
    assert row["outcome"] == "clear" and row["violations_found"] == 0


def test_classification_helpers():
    assert pp.claim_outcome("coverage", 0, 1) == "covered"
    assert pp.claim_outcome("coverage", 2, 1) == "gap"
    assert pp.claim_outcome("prohibition", 0, 0) == "not_declared"
    assert pp.claim_outcome("invariant", 0, 1) == "holds"
    assert pp.claim_outcome("termination", 1, 1) == "not_established"
    assert pp.policy_code(True, True, True) == "inconsistent_domain"
    assert pp.policy_code(False, True, False) == "limit"
    assert pp.policy_code(False, False, True) == "violated"
    assert pp.policy_code(False, False, False) == "satisfied"
    assert pp.rule_standing([], []) == "no_rule_support"
    assert pp.rule_standing(["known", "proposed"], ["resolved"] * 2) == "proposed_refused"
    assert pp.envelope_status(["known", "interpolated"]) == "interpolated"
    assert pp.envelope_status(["known", "proposed"]) == "proposed"
    assert pp.envelope_status([]) is None
    assert pp.envelope_resolution(["resolved", "unresolved", "partially_resolved"]) == "unresolved"
    assert pp.envelope_resolution(["unresolved", "conflicting"]) == "conflicting"
    assert pp.envelope_resolution([]) is None


def test_multi_step_trace_uses_first_enabling_valuation_and_offending_node():
    result = run(
        copy.deepcopy(CASES["POL-5-acyclic-dead-end-is-not-termination"]["data"]), [claim("coverage")]
    )
    trace = by_claim(result)["coverage"]["witnesses"][0]["trace"]
    assert [(step["state"], step["transition"]) for step in trace] == [("s", "s-m"), ("m", None)]
    assert trace[0]["actions"] == ["go"] and trace[1]["actions"] == []
    assert trace[0]["valuation"]["x"]["polarity"] == "positive"
    assert trace[1]["valuation"]["x"]["polarity"] == "negative"


def test_example_runs_without_mutation():
    example = pp.EXAMPLES["finite_policy"]
    before = copy.deepcopy(example)
    result = pp.evaluate(KIND, example)
    assert pp.check(KIND, example, [claim("prohibition", 1)])["code"] == result["code"] == "violated"
    assert by_claim(result)["prohibition"]["violations_found"] == 1
    assert example == before


def test_duplicate_claim_id_with_different_kinds_refuses():
    data = copy.deepcopy(CASES["POL-5-terminating-policy"]["data"])
    with pytest.raises(ValueError, match="^policy_duplicate_claim$"):
        pp.check(KIND, data, [claim("coverage", 1, "same"), claim("exclusivity", 1, "same")])


def test_conflicting_rule_never_yields_proposed_status():
    data = copy.deepcopy(CASES["POL-4-terminal-exempt-from-coverage-not-invariants"]["data"])
    data["invariants"][0]["rule"] = rule("known", "conflicting")
    result = run(data, [claim("invariant")])
    assert result["support_status"] == "known"
    assert result["support_resolution"] == "conflicting"
    assert by_claim(result)["invariant"]["standing"] == "binding_unresolved"
