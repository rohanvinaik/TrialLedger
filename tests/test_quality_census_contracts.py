"""Direct two-sign intent: deferred work cannot disappear or supply a completed measurement."""

import pytest

from scripts.quality_metrics import census_scope, reconcile_census


def test_pending_sample_is_selected_with_current_code_but_unselected_functions_stay_out():
    pending = {
        "file": "TrialLedger/x.py",
        "name": "pending",
        "pinned": False,
        "mutants": 1,
        "digest": "current",
    }
    unrelated = {**pending, "name": "unselected"}
    baseline = {"commit": "old", "records": [], "pending_targets": [{**pending, "digest": "old"}]}
    assert census_scope([pending, unrelated], baseline, 60, 7) == [pending]


def test_first_scope_contains_pinned_decisions_even_outside_the_sample():
    pinned = {"file": "TrialLedger/x.py", "name": "pinned", "pinned": True, "mutants": 1}
    other = {**pinned, "pinned": False, "name": "other"}
    assert census_scope([pinned, other], None, 0, 7) == [pinned]


def test_a_never_measured_target_remains_pending_and_cannot_count_as_remeasured():
    pending = {"file": "TrialLedger/x.py", "name": "pending", "pinned": False, "digest": "d"}
    assert reconcile_census([{**pending, "skipped": True}], []) == {
        "records": [],
        "pending_targets": [pending],
        "remeasured": 0,
    }


def test_deferred_old_evidence_is_stale_and_never_merged_with_partial_new_outcomes():
    old = {"file": "TrialLedger/x.py", "name": "f", "outcomes": [{"outcome": "survived"}]}
    partial = {**old, "skipped": True, "outcomes": [{"outcome": "killed"}]}
    assert reconcile_census([partial], [old]) == {
        "records": [{**old, "stale": True}],
        "pending_targets": [],
        "remeasured": 0,
    }


def test_completed_measurements_survive_without_pending_or_stale_labels():
    record = {"file": "TrialLedger/x.py", "name": "f", "outcomes": [{"outcome": "killed"}]}
    assert reconcile_census([record], []) == {
        "records": [record],
        "pending_targets": [],
        "remeasured": 1,
    }


def test_a_missing_previous_target_identity_names_the_missing_file_key():
    with pytest.raises(KeyError) as error:
        reconcile_census([{}], [{}])
    assert error.value.args == ("file",)


def test_a_negative_sample_size_is_rejected_instead_of_silently_dropping_scope():
    with pytest.raises(ValueError) as error:
        census_scope([], {}, -1, -1)
    assert str(error.value) == "Sample larger than population or is negative"


def test_a_malformed_baseline_is_not_accepted_as_an_empty_sample():
    baseline = {
        key: "x" for key in ("pinned", "mutation_commit", "records", "pending_targets", "file", "name")
    }
    with pytest.raises(TypeError) as error:
        census_scope([], baseline, 0, 0)
    assert str(error.value) == "string indices must be integers, not 'str'"


def test_a_missing_pinned_field_names_the_invalid_target():
    with pytest.raises(KeyError) as error:
        census_scope([{}], {}, 1, 1)
    assert error.value.args == ("pinned",)


def test_sample_size_is_capped_to_the_available_inventory():
    assert census_scope([], {}, 1, 2) == []


def test_the_full_previous_sample_and_pending_members_keep_their_declared_order():
    rows = [
        {"file": "TrialLedger/x.py", "name": name, "pinned": pinned, "mutants": 1, "": "different"}
        for name, pinned in (("p", True), ("q", True), ("r", False), ("s", False))
    ]
    baseline = {"commit": "old", "records": [rows[3]], "pending_targets": [rows[2]]}
    assert census_scope(rows, baseline, 0, 7) == rows


def test_a_fresh_sample_never_repeats_pinned_or_includes_zero_mutant_unselected_functions():
    pinned = {"name": "p", "pinned": True, "mutants": 1}
    sample = {"name": "s", "pinned": False, "mutants": 1}
    excluded = {"name": "zero", "pinned": False, "mutants": 0}
    assert census_scope([pinned, sample, excluded], None, 2, 7) == [pinned, sample]
