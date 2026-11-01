"""trial_cells — the balance cells a resolved record holds.

Positive: a record's phase list is one cell joined by "|" in its own order, so a combined phase stays as
written; each distinct intervention type is a cell, in order of first appearance; the primary purpose is read
from the design.
Negative: a combined phase is never split into its phases; a repeated intervention type is never counted
twice; a record that fills none of the three (an observational record, or one of the wrong shapes) is NONE on
each axis, never a guessed value.
"""

from records import ongoing_study, results_study

from TrialLedger.sample import NONE, trial_cells


def test_a_records_values_are_its_cells():
    assert trial_cells(results_study()) == {
        "phase": ["PHASE2"],
        "intervention_type": ["DRUG"],
        "primary_purpose": ["TREATMENT"],
    }


def test_a_combined_phase_stays_as_written_and_types_keep_their_order():
    study = results_study()
    study["protocolSection"]["designModule"]["phases"] = ["PHASE1", "PHASE2"]
    study["protocolSection"]["armsInterventionsModule"]["interventions"] = [
        {"type": "RADIATION", "name": "SBRT"},
        {"type": "DRUG", "name": "Testamab"},
        {"type": "RADIATION", "name": "Boost"},
        {"name": "untyped"},
    ]
    cells = trial_cells(study)
    assert cells["phase"] == ["PHASE1|PHASE2"]
    assert cells["intervention_type"] == ["RADIATION", "DRUG"]


def test_what_a_record_does_not_fill_is_none():
    assert trial_cells(ongoing_study()) == {
        "phase": [NONE],
        "intervention_type": [NONE],
        "primary_purpose": [NONE],
    }
    assert trial_cells({}) == trial_cells(ongoing_study())
    odd = {
        "protocolSection": {
            "designModule": {"phases": "PHASE2", "designInfo": "TREATMENT"},
            "armsInterventionsModule": {"interventions": {"type": "DRUG"}},
        }
    }
    assert trial_cells(odd) == trial_cells({})
    assert trial_cells({"protocolSection": []}) == trial_cells({})
