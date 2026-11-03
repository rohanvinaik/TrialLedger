"""Intent tests: finite coverage never certifies clinical action or sequential termination."""

import json
from copy import deepcopy

import pytest

from TrialLedger.layer2 import assertions as a
from TrialLedger.layer2 import decision_tables as tables
from TrialLedger.layer2.decision_tables import table_check_state, table_state


@pytest.mark.parametrize("kind", ["domain", "coverage", "overlap", "action"])
@pytest.mark.parametrize("result", ["ENTAILED", "REFUTED", "UNDETERMINED", "INCONSISTENT"])
def test_blocked_check_never_closes(kind, result):
    assert table_check_state(kind, result, True) == "unresolved"


@pytest.mark.parametrize("kind", ["domain", "coverage", "overlap", "action"])
def test_inconsistent_domain_never_vacuously_completes(kind):
    assert table_check_state(kind, "INCONSISTENT", False) == "domain_conflict"


@pytest.mark.parametrize("result", ["ENTAILED", "REFUTED", "UNDETERMINED"])
def test_completed_nonconflicting_domain_is_feasible(result):
    assert table_check_state("domain", result, False) == "feasible"


def test_coverage_requires_universal_truth():
    assert table_check_state("coverage", "ENTAILED", False) == "covered"
    assert table_check_state("coverage", "REFUTED", False) == "gap"
    assert table_check_state("coverage", "UNDETERMINED", False) == "gap"


def test_overlap_requires_only_one_feasible_state():
    assert table_check_state("overlap", "ENTAILED", False) == "overlap"
    assert table_check_state("overlap", "UNDETERMINED", False) == "overlap"
    assert table_check_state("overlap", "REFUTED", False) == "disjoint"


def test_action_reachability_is_not_universal_requirement():
    assert table_check_state("action", "ENTAILED", False) == "reachable"
    assert table_check_state("action", "UNDETERMINED", False) == "reachable"
    assert table_check_state("action", "REFUTED", False) == "unreachable"


@pytest.mark.parametrize("gap", [False, True])
@pytest.mark.parametrize("overlap", [False, True])
@pytest.mark.parametrize("incomplete", [False, True])
def test_domain_conflict_precedes_vacuous_table_claims(gap, overlap, incomplete):
    assert table_state("domain_conflict", gap, overlap, incomplete) == "conflict"


@pytest.mark.parametrize("gap", [False, True])
@pytest.mark.parametrize("overlap", [False, True])
@pytest.mark.parametrize("incomplete", [False, True])
def test_unknown_domain_never_refutes_table(gap, overlap, incomplete):
    assert table_state("unresolved", gap, overlap, incomplete) == "unresolved"


def test_known_table_conflict_survives_incomplete_other_checks():
    assert table_state("feasible", True, False, True) == "conflict"
    assert table_state("feasible", False, True, True) == "conflict"
    assert table_state("feasible", False, False, True) == "unresolved"
    assert table_state("feasible", False, False, False) == "consistent"


def example():
    return deepcopy(tables.EXAMPLES["decision_table"])


def literal(number, key="DLT", unit="participant"):
    return json.loads(
        a.canonical(
            a.Literal(
                a.Subject("source_case"),
                a.Predicate("measurement", key),
                a.Value("quantity", number=number, unit=unit),
            )
        )
    )


def test_expanded_cohort_table_covers_all_declared_outcomes():
    result = tables.evaluate("decision_table", example())
    assert result["code"] == "consistent"
    assert result["value"]["coverage"]["state"] == "covered"
    assert {r["state"] for r in result["value"]["actions"]} == {"reachable"}
    assert result["blockers"] == []
    assert all(row["blockers"] == [] for row in result["value"]["actions"])
    assert any(
        row["decision"]["blockers"] == ("undecided_by_constraints",) for row in result["value"]["actions"]
    )
    assert result["value"]["termination"] == "not_computed_static_table"
    assert result["value"]["operating_characteristics"] == "not_computed"


def test_missing_one_of_six_case_is_a_coverage_gap():
    data = example()
    data["rows"][0]["when"] = literal(0)
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "conflict"
    assert "table_uncovered_case" in result["blockers"]
    assert result["value"]["coverage"]["state"] == "gap"
    assert result["value"]["coverage"]["uncovered_condition"]["class"] == "Not"


def test_conflicting_action_for_one_case_is_not_first_match_wins():
    data = example()
    data["rows"].append({"id": "contradictory-one", "when": literal(1), "action": "stop"})
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "conflict"
    assert "table_conflicting_actions" in result["blockers"]
    assert any(r["state"] == "overlap" and not r["same_action"] for r in result["value"]["overlaps"])


def test_same_action_overlap_is_diagnostic_not_ambiguity():
    data = example()
    data["rows"].append({"id": "redundant-one", "when": literal(1), "action": "escalate"})
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "consistent"
    assert any(r["state"] == "overlap" and r["same_action"] for r in result["value"]["overlaps"])


def test_empty_feasible_domain_is_not_vacuous_coverage():
    data = example()
    data["constraints"] = [literal(8)]
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "conflict"
    assert result["value"]["domain"]["state"] == "domain_conflict"
    assert result["value"]["coverage"] is None


def test_action_without_rows_is_unreachable():
    data = example()
    data["actions"].append("expand")
    result = tables.evaluate("decision_table", data)
    row = next(row for row in result["value"]["actions"] if row["action"] == "expand")
    assert row["state"] == "unreachable"
    assert result["code"] == "consistent"


def test_impossible_row_action_is_unreachable():
    data = example()
    data["actions"].append("expand")
    data["rows"].append({"id": "outside-domain", "when": literal(8), "action": "expand"})
    result = tables.evaluate("decision_table", data)
    row = next(row for row in result["value"]["actions"] if row["action"] == "expand")
    assert row["state"] == "unreachable"


@pytest.mark.parametrize("which", ["rows", "constraints"])
def test_undeclared_variable_is_refused(which):
    data = example()
    if which == "rows":
        data["rows"][0]["when"] = literal(0, key="different")
    else:
        data["constraints"] = [literal(0, key="different")]
    with pytest.raises(ValueError, match="table_undeclared"):
        tables.evaluate("decision_table", data)


def test_different_count_unit_is_not_same_variable():
    data = example()
    data["rows"][0]["when"] = literal(0, unit="person-period")
    with pytest.raises(ValueError, match="table_undeclared_guard_variable"):
        tables.evaluate("decision_table", data)


@pytest.mark.parametrize("mutation", ["empty", "inequality", "negative", "duplicate", "mixed", "opaque"])
def test_domain_must_be_explicit_finite_resolved_equalities(mutation):
    data = example()
    values = data["domains"][0]["values"]
    if mutation == "empty":
        values.clear()
    elif mutation == "inequality":
        values[0]["value"]["comparison"] = "ge"
    elif mutation == "negative":
        values[0]["polarity"] = "negative"
    elif mutation == "duplicate":
        values.append(deepcopy(values[0]))
    elif mutation == "mixed":
        values[0] = literal(0, key="other")
    else:
        values[0] = {"class": "Opaque", "ref": "unread"}
    with pytest.raises(ValueError):
        tables.evaluate("decision_table", data)


def test_solver_limit_never_becomes_a_gap():
    data = example()
    data["limits"]["solver_bound"] = 1
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "unresolved"
    assert result["value"]["domain"]["state"] == "unresolved"
    assert result["value"]["coverage"] is None
    assert "resource_bound" in result["blockers"]


def test_call_limit_keeps_unperformed_checks_explicit():
    data = example()
    data["limits"]["solver_calls"] = 2
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "unresolved"
    assert result["value"]["coverage"]["state"] == "covered"
    assert all(r["state"] == "unresolved" for r in result["value"]["overlaps"])
    assert "resource_bound:table_checks" in result["blockers"]


def test_known_gap_remains_conflict_beside_unfinished_overlap_checks():
    data = example()
    data["rows"][0]["when"] = literal(0)
    data["limits"]["solver_calls"] = 2
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "conflict"
    assert {"table_uncovered_case", "resource_bound:table_checks"} <= set(result["blockers"])


def test_constraints_restrict_allowed_combinations():
    data = example()
    data["constraints"] = [literal(0)]
    data["rows"][0]["when"] = literal(0)
    data["rows"].pop()
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "consistent"
    assert result["value"]["coverage"]["state"] == "covered"


def test_input_is_not_mutated():
    data = example()
    before = deepcopy(data)
    tables.evaluate("decision_table", data)
    assert data == before


def test_candidate_claims_are_refused():
    with pytest.raises(ValueError, match="unsupported_table_candidate_claim"):
        tables.check("decision_table", example(), [{"anything": "unsupported"}])


@pytest.mark.parametrize("field", ["domains", "rows", "actions", "constraints"])
def test_null_lists_are_not_empty(field):
    data = example()
    data[field] = None
    with pytest.raises(ValueError, match="table_list_required"):
        tables.evaluate("decision_table", data)


def test_row_order_does_not_pick_a_winner():
    data = example()
    data["rows"].append({"id": "contradictory-one", "when": literal(1), "action": "stop"})
    before = tables.evaluate("decision_table", data)
    data["rows"].reverse()
    after = tables.evaluate("decision_table", data)
    assert before["code"] == after["code"] == "conflict"
    assert before["blockers"] == after["blockers"]


@pytest.mark.parametrize("kind", ["boolean", "enum"])
def test_finite_non_numeric_domains_keep_every_declared_value(kind):
    data = example()
    if kind == "boolean":
        value = a.Value("boolean")
        positive = a.Literal(a.Subject("source_case"), a.Predicate("defined_term", "event"), value)
        negative = a.Literal(
            a.Subject("source_case"), a.Predicate("defined_term", "event"), value, polarity="negative"
        )
        values = [json.loads(a.canonical(positive)), json.loads(a.canonical(negative))]
    else:
        values = [
            json.loads(
                a.canonical(
                    a.Literal(
                        a.Subject("source_case"),
                        a.Predicate("defined_term", "event"),
                        a.Value("enum", members=(member,)),
                    )
                )
            )
            for member in ["present", "absent"]
        ]
    data["domains"] = [{"id": "event-domain", "values": values}]
    data["rows"] = [
        {"id": "present", "when": values[0], "action": "escalate"},
        {"id": "absent", "when": values[1], "action": "stop"},
    ]
    result = tables.evaluate("decision_table", data)
    assert result["code"] == "consistent"
    assert result["value"]["coverage"]["state"] == "covered"
    data["rows"].pop()
    assert tables.evaluate("decision_table", data)["value"]["coverage"]["state"] == "gap"


def test_equal_numbers_at_different_events_do_not_join():
    data = example()
    body = data["rows"][0]["when"]["parts"][0]
    body["time"] = json.loads(a.canonical(a.TemporalScope("at", "named_event", "other-event")))
    with pytest.raises(ValueError, match="table_undeclared_guard_variable"):
        tables.evaluate("decision_table", data)


@pytest.mark.parametrize("claims", [None, {}, "", 0])
def test_malformed_claim_collection_is_not_a_noop(claims):
    with pytest.raises(ValueError, match="table_claims_list_required"):
        tables.check("decision_table", example(), claims)


@pytest.mark.parametrize("key", ["solver_bound", "solver_calls"])
@pytest.mark.parametrize("value", [0, None, True])
def test_limits_are_positive_integers_not_bool_or_unknown(key, value):
    data = example()
    data["limits"][key] = value
    with pytest.raises(ValueError, match="table_invalid_solver"):
        tables.evaluate("decision_table", data)


def test_nested_input_is_bounded_before_recursive_hydration():
    data = example()
    condition = literal(0)
    for _ in range(40):
        condition = {"class": "Not", "part": condition}
    data["rows"][0]["when"] = condition
    with pytest.raises(ValueError, match="resource_bound:table_input"):
        tables.evaluate("decision_table", data)


def test_aggregate_input_nodes_are_bounded_before_hydration():
    data = example()
    data["rows"][0]["when"] = {"class": "AllOf", "parts": [literal(0) for _ in range(1000)]}
    with pytest.raises(ValueError, match="resource_bound:table_input"):
        tables.evaluate("decision_table", data)


def test_cyclic_python_input_is_bounded_instead_of_recursing_forever():
    data = example()
    data["constraints"].append(data)
    with pytest.raises(ValueError, match="resource_bound:table_input"):
        tables.evaluate("decision_table", data)
