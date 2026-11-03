"""Intent: stage pathways cannot manufacture person membership, count units, or scope warrants."""

from copy import deepcopy

import pytest

from TrialLedger.layer2.stage_evidence import check, evaluate, stage_result_code, transition_gate


def example():
    source = {
        "id": "induction",
        "population": "induction-started",
        "arm": "all",
        "time": "entry",
        "unit": "person",
        "total": 498,
    }
    target = {
        "id": "maintenance",
        "population": "randomized-maintenance",
        "arm": "all",
        "time": "week16",
        "unit": "person",
        "total": 440,
    }
    scope = {
        "study": "invented:crohn-design",
        "snapshot": "invented:snapshot-v1",
        "source_population": source["population"],
        "target_population": target["population"],
        "source_arm": source["arm"],
        "target_arm": target["arm"],
        "source_time": source["time"],
        "target_time": target["time"],
        "unit": "person",
    }
    edge = {
        "id": "randomized-after-runin",
        "source": source["id"],
        "target": target["id"],
        "relation": "documented_subset",
        "scope": scope,
        "status": "interpolated",
        "resolution": "resolved",
        "basis": ["invented:declared-person-lineage"],
        "gate_ref": "invented:week16-response-gate",
    }
    return {
        "study": scope["study"],
        "snapshot": scope["snapshot"],
        "resolution": "resolved",
        "stages": [source, target],
        "transitions": [edge],
    }


def test_documented_subset_reuses_population_engine_without_membership():
    result = evaluate("stages", example())
    assert result["code"] == "consistent"
    edge = result["value"]["transitions"][0]
    assert edge["code"] == "bounded"
    assert edge["status"] == "interpolated"
    assert edge["population_request"]["total"] == 498
    assert edge["population_result"]["value"]["counts"][-1] == {"id": "outside", "lower": 58, "upper": 58}
    assert result["value"]["witnesses"] == []
    assert "individual_membership" in edge["guarantee"]


def test_permitted_progression_does_not_supply_subset_arithmetic():
    data = example()
    data["transitions"][0]["relation"] = "permitted"
    data["stages"][1]["total"] = 1000
    result = evaluate("stages", data)
    edge = result["value"]["transitions"][0]
    assert edge["code"] == "permitted_only"
    assert edge["population_request"] is None
    assert edge["population_result"] is None
    assert result["code"] == "consistent"


def test_permitted_edge_cannot_consume_subset_claim():
    data = example()
    data["transitions"][0]["relation"] = "permitted"
    result = check(
        "stages", data, [{"transition": "randomized-after-runin", "count": "outside", "lower": 0, "upper": 0}]
    )
    assert result["code"] == "unresolved"
    assert result["blockers"] == ["stage_subset_not_warranted:randomized-after-runin"]


def test_impossible_subset_is_conditional_conflict_not_wrong_relation_identity():
    data = example()
    data["stages"][1]["total"] = 499
    result = evaluate("stages", data)
    edge = result["value"]["transitions"][0]
    assert edge["code"] == "conflict"
    assert edge["status"] == "interpolated"
    assert edge["population_result"]["code"] == "conflict"
    assert "inconsistent_population_total" in edge["population_result"]["blockers"]


def test_proposed_relation_retains_raw_conflict_but_no_admitted_refutation():
    data = example()
    data["stages"][1]["total"] = 499
    data["transitions"][0]["status"] = "proposed"
    result = evaluate("stages", data)
    edge = result["value"]["transitions"][0]
    assert edge["code"] == "unresolved"
    assert edge["population_result"]["code"] == "conflict"
    assert result["blockers"] == ["proposed_refused:randomized-after-runin"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("snapshot", "other-snapshot"),
        ("study", "other-study"),
        ("source_arm", "another-arm"),
        ("target_time", "later"),
    ],
)
def test_scope_mismatch_never_reaches_population_arithmetic(field, value):
    data = example()
    data["transitions"][0]["scope"][field] = value
    result = evaluate("stages", data)
    edge = result["value"]["transitions"][0]
    assert edge["code"] == "unresolved"
    assert edge["population_result"] is None
    assert result["blockers"] == ["stage_scope_mismatch:randomized-after-runin"]


@pytest.mark.parametrize("unit", ["person-period", "cluster", "event"])
def test_count_units_never_convert_implicitly(unit):
    data = example()
    data["stages"][1]["unit"] = unit
    result = evaluate("stages", data)
    edge = result["value"]["transitions"][0]
    assert edge["code"] == "unresolved"
    assert edge["population_result"] is None
    assert result["blockers"] == ["stage_unit_mismatch:randomized-after-runin"]


@pytest.mark.parametrize("index", [0, 1])
def test_unknown_total_is_not_zero(index):
    data = example()
    data["stages"][index]["total"] = None
    result = evaluate("stages", data)
    edge = result["value"]["transitions"][0]
    assert edge["code"] == "unresolved"
    assert edge["population_result"] is None
    assert result["blockers"] == ["stage_total_unknown:randomized-after-runin"]


def test_explicit_zero_is_usable():
    data = example()
    data["stages"][1]["total"] = 0
    edge = evaluate("stages", data)["value"]["transitions"][0]
    assert edge["code"] == "bounded"
    assert edge["population_result"]["value"]["counts"][-1]["lower"] == 498


def test_claims_against_one_edge_are_checked_together():
    claims = [{"transition": "randomized-after-runin", "count": "outside", "lower": 0, "upper": 0}]
    result = check("stages", example(), claims)
    edge = result["value"]["transitions"][0]
    assert edge["code"] == "conflict"
    assert edge["claims"] == [{"count": "outside", "lower": 0, "upper": 0}]


def test_unresolved_edge_does_not_erase_independent_conflict():
    data = example()
    data["stages"][1]["total"] = 499
    edge = deepcopy(data["transitions"][0])
    edge.update(id="unconfirmed-other-application", status="proposed")
    data["transitions"].append(edge)
    result = evaluate("stages", data)
    assert result["code"] == "conflict"
    rows = {row["id"]: row for row in result["value"]["transitions"]}
    assert rows["randomized-after-runin"]["code"] == "conflict"
    assert rows[edge["id"]]["code"] == "unresolved"
    assert rows["randomized-after-runin"]["status"] == "interpolated"


def test_order_independence_and_input_immutability():
    data = example()
    before = deepcopy(data)
    result = evaluate("stages", data)
    data["stages"].reverse()
    assert evaluate("stages", data) == result
    data["stages"].reverse()
    assert data == before


@pytest.mark.parametrize("value", [False, -1, 1.2, "498", [], {}])
def test_malformed_total_refused(value):
    data = example()
    data["stages"][0]["total"] = value
    with pytest.raises(ValueError, match="stage_count_required"):
        evaluate("stages", data)


@pytest.mark.parametrize(
    "field,value", [("source", "unknown"), ("target", "unknown"), ("relation", "same-title"), ("basis", [])]
)
def test_invalid_transition_refused(field, value):
    data = example()
    data["transitions"][0][field] = value
    with pytest.raises(ValueError):
        evaluate("stages", data)


def test_empty_graph_has_no_fabricated_witness():
    data = example()
    data["stages"] = []
    data["transitions"] = []
    result = evaluate("stages", data)
    assert result["code"] == "consistent"
    assert result["value"]["transitions"] == result["value"]["witnesses"] == []


@pytest.mark.parametrize(
    "args,expected",
    [
        (("documented_subset", "known", "resolved", False, True), "stage_scope_mismatch"),
        (("documented_subset", "known", "resolved", True, False), "stage_unit_mismatch"),
        (("documented_subset", "proposed", "resolved", True, True), "proposed_refused"),
        (("documented_subset", "known", "unresolved", True, True), "stage_binding_unresolved"),
        (("permitted", "known", "resolved", True, True), "permitted_only"),
        (("documented_subset", "interpolated", "resolved", True, True), "checkable"),
    ],
)
def test_transition_gate_direct_intent(args, expected):
    assert transition_gate(*args) == expected


@pytest.mark.parametrize(
    "codes,expected",
    [
        ([], "consistent"),
        (["bounded"], "consistent"),
        (["permitted_only"], "consistent"),
        (["unresolved"], "unresolved"),
        (["conflict"], "conflict"),
        (["unresolved", "conflict"], "conflict"),
    ],
)
def test_result_code_direct_intent(codes, expected):
    assert stage_result_code(codes) == expected


def test_admitted_numeric_conflict_keeps_deciding_cause():
    data = example()
    data["stages"][1]["total"] = 499
    result = evaluate("stages", data)
    assert result["code"] == "conflict"
    assert "inconsistent_population_total" in result["blockers"]
    assert result["support_status"] == "interpolated"
    assert result["determining_ids"] == ["randomized-after-runin"]


def test_known_conflict_not_weakened_by_unrelated_interpolated_conflict():
    data = example()
    data["stages"][1]["total"] = 499
    known = deepcopy(data["transitions"][0])
    known.update(id="known-lineage", status="known")
    data["transitions"].append(known)
    result = evaluate("stages", data)
    assert result["code"] == "conflict"
    assert result["support_status"] == "known"
    assert result["determining_ids"] == ["known-lineage"]


def test_candidate_claim_does_not_inherit_unrelated_pending_edge():
    data = example()
    known = data["transitions"][0]
    known["status"] = "known"
    other = deepcopy(known)
    other.update(id="unrelated-pending", status="proposed")
    data["transitions"].append(other)
    assert evaluate("stages", data)["code"] == "unresolved"
    result = check(
        "stages", data, [{"transition": known["id"], "count": "outside", "lower": 58, "upper": 58}]
    )
    assert result["code"] == "consistent"
    assert result["support_status"] == "known"
    assert result["blockers"] == []
    assert result["determining_ids"] == [known["id"]]
    rows = {row["id"]: row for row in result["value"]["transitions"]}
    assert rows["unrelated-pending"]["code"] == "unresolved"


def test_graph_binding_uncertainty_gates_every_edge():
    data = example()
    data["resolution"] = "unresolved"
    data["stages"][1]["total"] = 499
    result = evaluate("stages", data)
    assert result["code"] == "unresolved"
    assert result["support_status"] is None
    assert result["value"]["transitions"][0]["population_result"]["code"] == "conflict"


def test_consistent_all_edges_retains_weakest_admitted_support():
    data = example()
    known = deepcopy(data["transitions"][0])
    known.update(id="known-lineage", status="known")
    data["transitions"].append(known)
    assert evaluate("stages", data)["support_status"] == "interpolated"


@pytest.mark.parametrize(
    "code,statuses,expected",
    [
        ("unresolved", ["known"], "no_support"),
        ("consistent", [], "no_support"),
        ("conflict", ["interpolated", "known"], "known"),
        ("conflict", ["interpolated"], "interpolated"),
        ("consistent", ["known"], "known"),
        ("consistent", ["known", "interpolated"], "interpolated"),
    ],
)
def test_support_status_direct_intent(code, statuses, expected):
    from TrialLedger.layer2.stage_evidence import stage_support_status

    assert stage_support_status(code, statuses) == expected
