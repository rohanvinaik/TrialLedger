"""Authored intents for compatibility of selected possible floors with a supplied cap.

Attribution uncertainty may remain even when every attribution fits the cap. The
largest selected possible floor is never the total number of exceptions.
"""

from TrialLedger.layer2.exception_bounds import floor_cap_state


def test_possible_floor_one_must_not_block_cap_five():
    assert floor_cap_state(0, 1, 5, 100) == "consistent"


def test_selected_non_entry_failure_must_not_create_an_eligibility_floor():
    assert floor_cap_state(0, 0, 5, 100) == "consistent"


def test_known_floor_one_fits_cap_five():
    assert floor_cap_state(1, 1, 5, 100) == "consistent"


def test_uncertain_floor_one_with_cap_zero_is_attribution_dependent():
    assert floor_cap_state(0, 1, 0, 100) == "attribution_dependent"


def test_certain_floor_one_with_cap_zero_is_a_conflict():
    assert floor_cap_state(1, 1, 0, 100) == "ceiling_conflict"


def test_unknown_ceiling_must_not_be_zero_or_certified_from_selected_count():
    assert floor_cap_state(0, 1, None, 100) == "unknown_ceiling"
    assert floor_cap_state(1, 1, None, 100) == "unknown_ceiling"


def test_unknown_ceiling_keeps_attribution_uncertainty_even_above_population_size():
    assert floor_cap_state(0, 101, None, 100) == "unknown_ceiling"


def test_certain_structural_conflict_precedes_unknown_ceiling():
    assert floor_cap_state(101, 101, None, 100) == "structural_maximum_conflict"


def test_possible_structural_conflict_must_not_become_certain_conflict():
    assert floor_cap_state(0, 101, 200, 100) == "attribution_dependent"


def test_certain_structural_conflict_precedes_informative_ceiling_conflict():
    assert floor_cap_state(2, 2, 0, 1) == "structural_maximum_conflict"


def test_floor_equal_to_cap_must_not_conflict():
    assert floor_cap_state(5, 5, 5, 100) == "consistent"


def test_possible_floor_just_above_cap_must_remain_material():
    assert floor_cap_state(5, 6, 5, 100) == "attribution_dependent"


def test_structural_maximum_bounds_compatibility_even_when_cap_is_larger():
    assert floor_cap_state(5, 5, 100, 5) == "consistent"
    assert floor_cap_state(5, 6, 100, 5) == "attribution_dependent"
    assert floor_cap_state(6, 6, 100, 5) == "structural_maximum_conflict"


def test_zero_boundary_preserves_unknown_ceiling_distinction():
    assert floor_cap_state(0, 0, 0, 0) == "consistent"
    assert floor_cap_state(0, 0, None, 0) == "unknown_ceiling"


def test_widening_cap_can_remove_material_attribution_without_certifying_total_count():
    assert floor_cap_state(0, 1, 0, 100) == "attribution_dependent"
    assert floor_cap_state(0, 1, 1, 100) == "consistent"
    assert floor_cap_state(0, 1, 5, 100) == "consistent"
