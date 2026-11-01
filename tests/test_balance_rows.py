"""balance_rows — the sample's balance table by phase, intervention type and primary purpose.

Positive: every registry value of every axis is a row, in the registry's order (the two phase combinations
the metadata names among them), counted over the drawn and the supplement trials apart; a combined phase is
its own row; a value no enum declares (NONE) follows the declared rows; the registry's count is carried and
the status is cell_status's; a combined phase listed in another order counts for its declared cell and is
kept as written in the record's cells.
Negative: a trial is never counted under a phase it holds only as part of a combination; a supplement trial is
never counted as drawn; a value no enum declares is never a gap; a zero-hit cell whose query form is not on
the verified list is never called empty.
"""

from records import ongoing_study, results_study

from TrialLedger.sample import NONE, VERIFIED_FORMS, balance_rows, declared_cells, trial_cells


def rows_by_cell(rows):
    return {(row["axis"], row["value"]): row for row in rows}


def test_every_registry_value_is_a_row_in_order():
    declared = declared_cells()
    assert declared["phase"] == [
        "NA",
        "EARLY_PHASE1",
        "PHASE1",
        "PHASE2",
        "PHASE3",
        "PHASE4",
        "PHASE1|PHASE2",
        "PHASE2|PHASE3",
    ]
    assert "TREATMENT" in declared["primary_purpose"] and "DEVICE" in declared["intervention_type"]
    rows = balance_rows([], [], declared, {}, VERIFIED_FORMS)
    assert [(r["axis"], r["value"]) for r in rows] == [(a, v) for a, vs in declared.items() for v in vs]
    assert {r["status"] for r in rows} == {"not_checked"}


def test_counts_drawn_and_supplement_apart():
    combined = results_study()
    combined["protocolSection"]["designModule"]["phases"] = ["PHASE1", "PHASE2"]
    drawn = [trial_cells(results_study()), trial_cells(combined), trial_cells(ongoing_study())]
    supplement = [trial_cells(results_study())]
    registry = {"phase=PHASE3": 50, "phase=PHASE4": 0, "primary_purpose=PREVENTION": 7}
    rows = rows_by_cell(balance_rows(drawn, supplement, declared_cells(), registry, VERIFIED_FORMS))
    assert rows["phase", "PHASE2"] == {
        "axis": "phase",
        "value": "PHASE2",
        "registry_value": True,
        "drawn": 1,
        "supplement": 1,
        "registry_count": None,
        "status": "present",
    }
    assert rows["phase", "PHASE1|PHASE2"]["drawn"] == 1 and rows["phase", "PHASE1"]["drawn"] == 0
    assert rows["phase", "PHASE3"]["status"] == "gap" and rows["phase", "PHASE3"]["registry_count"] == 50
    assert rows["phase", "PHASE4"]["status"] == "empty_in_registry"
    assert rows["primary_purpose", "PREVENTION"]["status"] == "gap"
    assert rows["intervention_type", "DRUG"]["drawn"] == 2


def test_an_undeclared_value_is_named_never_a_gap():
    drawn = [trial_cells(ongoing_study())]
    rows = balance_rows(drawn, [], declared_cells(), {f"phase={NONE}": 0}, VERIFIED_FORMS)
    tail = [r for r in rows if not r["registry_value"]]
    assert [(r["axis"], r["value"]) for r in tail] == [
        ("phase", NONE),
        ("intervention_type", NONE),
        ("primary_purpose", NONE),
    ]
    assert {r["status"] for r in tail} == {"undeclared"}
    assert all(r["drawn"] == 1 for r in tail)
    assert [r["value"] for r in rows if r["axis"] == "phase"][-1] == NONE


def test_a_combined_phase_in_another_order_counts_and_stays_as_written():
    reversed_order = results_study()
    reversed_order["protocolSection"]["designModule"]["phases"] = ["PHASE2", "PHASE1"]
    cells = trial_cells(reversed_order)
    assert cells["phase"] == ["PHASE2|PHASE1"]
    rows = balance_rows([cells], [], declared_cells(), {}, VERIFIED_FORMS)
    by = rows_by_cell(rows)
    assert by["phase", "PHASE1|PHASE2"]["drawn"] == 1 and by["phase", "PHASE1|PHASE2"]["status"] == "present"
    assert by["phase", "PHASE1"]["drawn"] == 0 and by["phase", "PHASE2"]["drawn"] == 0
    assert ("phase", "PHASE2|PHASE1") not in by
    undeclared = results_study()
    undeclared["protocolSection"]["designModule"]["phases"] = ["PHASE4", "PHASE3"]
    other = results_study()
    other["protocolSection"]["designModule"]["phases"] = ["PHASE3", "PHASE4"]
    tail = balance_rows(
        [trial_cells(undeclared), trial_cells(other)], [], declared_cells(), {}, VERIFIED_FORMS
    )
    named = [r for r in tail if r["axis"] == "phase" and not r["registry_value"]]
    assert [(r["value"], r["drawn"], r["status"]) for r in named] == [("PHASE4|PHASE3", 2, "undeclared")]


def test_a_zero_hit_cell_is_empty_only_by_a_verified_query():
    registry = {"phase=PHASE4": 0, "primary_purpose=SCREENING": 0, "intervention_type=GENETIC": 0}
    verified = rows_by_cell(balance_rows([], [], declared_cells(), registry, VERIFIED_FORMS))
    assert {verified[c]["status"] for c in [("phase", "PHASE4"), ("primary_purpose", "SCREENING")]} == {
        "empty_in_registry"
    }
    only_phase = {"AREA[Phase]": "2026-11-01"}
    rows = rows_by_cell(balance_rows([], [], declared_cells(), registry, only_phase))
    assert rows["phase", "PHASE4"]["status"] == "query_unverified"  # the exact-phase NOT form is not listed
    assert rows["primary_purpose", "SCREENING"]["status"] == "query_unverified"
    assert rows["intervention_type", "GENETIC"]["status"] == "query_unverified"
    assert rows["phase", "PHASE3"]["status"] == "not_checked"
    none = rows_by_cell(balance_rows([], [], declared_cells(), {"phase=PHASE4": 3}, {}))
    assert none["phase", "PHASE4"]["status"] == "gap"
