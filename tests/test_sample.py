"""The live stratified sample.

Positive: a draw is seeded, depends only on the set of IDs, the seed and the label, and takes n from the
discovery pool; a trial in two strata is kept once with both memberships and its union inclusion probability;
the whole sample records queries, pool sizes, the seed and the snapshot, and declares its balance check; a
declared cell no drawn trial holds is asked of the registry within the frame, exactly, and a seeded supplement
is drawn from its discovery pool with its own inclusion probability, and a trial drawn for two cells carries
its union probability; every form a cell query is built from was tried live and is declared with its date.
Negative: no confirmation-pool ID is ever drawn; a smaller pool gives fewer, never repeats; a sample whose
strata come from different snapshots fails; a present or undeclared cell is never asked or supplemented; a
supplement never repeats a sampled trial; supplements read across snapshots fail with SnapshotChanged, never
a bare RuntimeError; no form is declared verified without a live count above zero on that date."""

import json
from pathlib import Path

import pytest

from TrialLedger.sample import (
    CATEGORIES,
    NO_MESH,
    NONE,
    VERIFIED_FORMS,
    SnapshotChanged,
    cell_query,
    declared_cells,
    draw,
    draw_sample,
    draw_supplements,
    holds_cell,
    inclusion,
    query_forms,
    reserved,
    stratum_query,
)

IDS = [f"NCT{n:08d}" for n in range(1, 201)]


def test_the_confirmation_pool_is_fixed_and_never_drawn():
    held = [nct for nct in IDS if reserved(nct)]
    assert 30 < len(held) < 90
    drawn, pool = draw(IDS, 500, "s", "Neoplasms")
    assert pool == len(IDS) - len(held) and len(drawn) == pool
    assert not set(drawn) & set(held)


def test_a_draw_is_seeded_and_order_free():
    first, _ = draw(IDS, 6, "s", "Neoplasms")
    assert first == draw(list(reversed(IDS)) + IDS[:10], 6, "s", "Neoplasms")[0]
    assert len(first) == 6 == len(set(first))
    assert first != draw(IDS, 6, "t", "Neoplasms")[0]
    assert first != draw(IDS, 6, "s", "Eye Diseases")[0]
    assert draw(IDS, 0, "s", "x") == ([], draw(IDS, 0, "s", "x")[1])
    assert draw(IDS, -1, "s", "x")[0] == []
    assert draw([], 6, "s", "x") == ([], 0)


def test_union_inclusion_probability():
    sizes = {"a": (6, 60), "b": (6, 12), "c": (0, 0)}
    assert inclusion(["a"], sizes) == pytest.approx(0.1)
    assert inclusion(["a", "b"], sizes) == pytest.approx(1 - 0.9 * 0.5)
    assert inclusion(["c"], sizes) == 0
    assert inclusion([], sizes) == 0
    assert inclusion(["b"], {"b": (20, 12)}) == pytest.approx(1)


def test_stratum_queries():
    assert stratum_query(NO_MESH).endswith("AREA[ConditionMeshTerm]MISSING")
    query = stratum_query("Eye Diseases")
    assert 'AREA[ConditionMeshTerm]"Eye Diseases" OR AREA[ConditionAncestorTerm]"Eye Diseases"' in query
    assert query.startswith("AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2010-01-01,2025-12-31]")


def test_the_whole_sample_keeps_memberships_and_its_snapshot():
    shared = [nct for nct in IDS if not reserved(nct)][:3]

    def fake(query, progress):
        if "Neoplasms" in query["filter.advanced"] or "MISSING" in query["filter.advanced"]:
            return shared, "2.0.5", "T"
        return [], "2.0.5", "T"

    sample = draw_sample(2, "s", fake)
    assert sample["data_timestamp"] == "T" and len(sample["strata"]) == len(CATEGORIES) + 1
    trials = {t["nct"]: t for t in sample["trials"]}
    assert set(trials) <= set(shared) and 2 <= len(trials) <= 3
    for trial in trials.values():
        assert trial["strata"] == ["Neoplasms", NO_MESH]
        assert trial["inclusion_probability"] == pytest.approx(1 - (1 - 2 / 3) ** 2)


def test_a_sample_across_snapshots_fails():
    stamps = iter(["T1"] + ["T2"] * 40)

    def fake(query, progress):
        return [], "2.0.5", next(stamps)

    with pytest.raises(SnapshotChanged, match="changed while sampling"):
        draw_sample(2, "s", fake)


def test_the_sample_declares_its_balance_check_before_any_draw():
    sample = draw_sample(2, "s", lambda query, progress: ([], "2.0.5", "T"))
    declared = sample["balance"]
    assert declared["cells"] == declared_cells() and declared["supplement_per_cell"] == 1
    assert declared["axes"] == {
        "phase": "Phase",
        "intervention_type": "InterventionType",
        "primary_purpose": "DesignPrimaryPurpose",
    }


def test_a_cell_query_is_exact_and_within_the_frame():
    query = cell_query("phase", "PHASE2")
    assert query.startswith(
        "AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2010-01-01,2025-12-31] AND ("
    )
    assert "AREA[ConditionMeshTerm]MISSING" in query and 'AREA[ConditionAncestorTerm]"Eye Diseases"' in query
    assert "AREA[Phase]PHASE2" in query and "NOT AREA[Phase]PHASE1" in query
    assert "NOT AREA[Phase]PHASE2" not in query
    both = cell_query("phase", "PHASE1|PHASE2")
    assert "AREA[Phase]PHASE1 AND AREA[Phase]PHASE2 AND NOT AREA[Phase]NA" in both
    assert "NOT AREA[Phase]PHASE1" not in both and "NOT AREA[Phase]PHASE3" in both
    assert cell_query("primary_purpose", "SCREENING").endswith("AREA[DesignPrimaryPurpose]SCREENING")
    assert cell_query("intervention_type", "GENETIC").endswith("AREA[InterventionType]GENETIC")


def test_supplements_fill_only_empty_registry_cells_from_one_snapshot():
    rows = [
        {"axis": "phase", "value": "PHASE2", "status": "present"},
        {"axis": "phase", "value": "PHASE4", "status": "not_checked"},
        {"axis": "primary_purpose", "value": "SCREENING", "status": "not_checked"},
        {"axis": "phase", "value": NONE, "status": "undeclared"},
    ]
    drawable = [nct for nct in IDS if not reserved(nct)]
    asked = []

    def fake(query, progress):
        asked.append(query["filter.advanced"])
        if "PHASE4" in query["filter.advanced"]:
            return [*drawable[:3], *[n for n in IDS if reserved(n)][:2]], "2.0.5", "T"
        return [], "2.0.5", "T"

    registry, supplements, snapshot = draw_supplements(rows, "s", 1, {drawable[0]}, fake, lambda m: None)
    assert len(asked) == 2 and registry == {"phase=PHASE4": 5, "primary_purpose=SCREENING": 0}
    assert snapshot == {"api_version": "2.0.5", "data_timestamp": "T"}
    [item] = supplements
    assert item["nct"] in drawable[1:3] and item["label"] == "supplement phase=PHASE4"
    assert item["pool"] == 2 and item["inclusion_probability"] == pytest.approx(0.5)
    again = draw_supplements(rows, "s", 1, {drawable[0]}, fake, lambda m: None)[1]
    assert again == supplements
    nothing = draw_supplements(rows[:1], "s", 1, set(), fake, lambda m: None)
    assert nothing == ({}, [], {"api_version": "", "data_timestamp": ""})


def test_supplements_across_snapshots_fail():
    rows = [{"axis": "phase", "value": v, "status": "not_checked"} for v in ("NA", "PHASE4")]
    stamps = iter(["T1", "T2"])

    def fake(query, progress):
        return [], "2.0.5", next(stamps)

    with pytest.raises(SnapshotChanged, match="changed while supplementing"):
        draw_supplements(rows, "s", 1, set(), fake, lambda m: None)


def test_an_empty_stratum_draws_nothing_and_says_its_pool_is_empty():
    """Positive: an empty stratum returns an empty draw and a pool of zero, as a pair. Negative: never None, a
    bare list or a bare count."""
    result = draw([], 6, "s", "x")
    assert result == ([], 0)
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], list) and result[1] == 0


def test_a_trial_supplementing_two_cells_carries_its_union_probability():
    drawable = [nct for nct in IDS if not reserved(nct)]
    rows = [
        {"axis": "phase", "value": "PHASE4", "status": "not_checked"},
        {"axis": "primary_purpose", "value": "SCREENING", "status": "not_checked"},
        {"axis": "intervention_type", "value": "GENETIC", "status": "not_checked"},
    ]

    def fake(query, progress):
        where = query["filter.advanced"]
        if "PHASE4" in where or "SCREENING" in where:
            return drawable[:2], "2.0.5", "T"
        return drawable[5:9], "2.0.5", "T"

    _registry, supplements, _snapshot = draw_supplements(rows, "s", 1, set(), fake, lambda m: None)
    assert len(supplements) == 3
    for item in supplements[:2]:
        assert item["inclusion_probability"] == pytest.approx(0.5)
        assert item["memberships"] == ["supplement phase=PHASE4", "supplement primary_purpose=SCREENING"]
        assert item["union_inclusion_probability"] == pytest.approx(1 - 0.5 * 0.5)
    genetic = supplements[2]
    assert genetic["memberships"] == ["supplement intervention_type=GENETIC"]
    assert genetic["union_inclusion_probability"] == genetic["inclusion_probability"] == pytest.approx(0.25)


def test_holds_cell_matches_a_combination_in_any_order_and_nothing_else():
    assert holds_cell(["PHASE2|PHASE1"], "PHASE1|PHASE2")
    assert holds_cell(["PHASE1|PHASE2"], "PHASE1|PHASE2")
    assert holds_cell(["DRUG", "DEVICE"], "DEVICE")
    assert not holds_cell(["PHASE1|PHASE2"], "PHASE2")
    assert not holds_cell(["PHASE2"], "PHASE1|PHASE2")
    assert not holds_cell([], "PHASE2") and not holds_cell(["PHASE2|PHASE3"], "PHASE1|PHASE2")


def test_the_query_forms_of_a_cell():
    assert query_forms("phase", "PHASE2") == ["AREA[Phase]", "NOT AREA[Phase]"]
    assert query_forms("phase", "PHASE1|PHASE2") == ["AREA[Phase]", "NOT AREA[Phase]"]
    assert query_forms("primary_purpose", "SCREENING") == ["AREA[DesignPrimaryPurpose]"]
    assert query_forms("intervention_type", "DRUG") == ["AREA[InterventionType]"]
    for axis in ("phase", "primary_purpose", "intervention_type"):
        assert all(form in cell_query(axis, "PHASE2") for form in query_forms(axis, "PHASE2"))


def test_every_verified_form_was_tried_live_on_its_date():
    """The declared list holds the forms the live check of tests/live_query_forms.json returned trials for,
    each with that check's date; a form it did not try, or that returned none, is never declared."""
    fixture = json.loads((Path(__file__).parent / "live_query_forms.json").read_text(encoding="utf-8"))
    assert set(VERIFIED_FORMS) == set(fixture["forms"])
    for form, asked in fixture["forms"].items():
        assert VERIFIED_FORMS[form] == fixture["asked"]
        assert asked["status"] == 200 and 0 < asked["totalCount"] < fixture["base"]["totalCount"]
        assert asked["query"].startswith(fixture["base"]["query"]) and form in asked["query"]
    exact = fixture["forms"]["NOT AREA[Phase]"]["totalCount"]
    assert exact < fixture["forms"]["AREA[Phase]"]["totalCount"]  # the NOT form excludes combinations
    forms_used = {
        form for axis, values in declared_cells().items() for v in values for form in query_forms(axis, v)
    }
    assert forms_used == set(VERIFIED_FORMS)
