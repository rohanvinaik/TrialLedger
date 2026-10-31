"""Profile — elements measured against the population, kept apart as frequency, association and occupancy.

Positive: an element's frequency is over the stratum's typed trials, with surprisal in bits and its sponsors;
an element nearly every trial states is standard; an element more frequent within a class, from enough trials
and sponsors, is a proposed relation, with the 2×2 counts and the unresolved trials named; a cell with an
occupant is occupied, a failed or withdrawn one included.
Negative: an untyped trial is never in a denominator nor counted as lacking an element; one sponsor never
makes a proposal; an element no more frequent within a class is never listed; a cell that unresolved trials
could fall in is never empty; requiring and excluding the same thing are never one element.
"""

import math

import pytest

from TrialLedger.profile import element_key, frequency_rows, mechanism_rows, occupancy_rows


def trial(nct, sponsor="S", stratum="all", typed=True, elements=(), classes=(), unresolved=False):
    return (nct, sponsor, stratum, typed, list(elements), list(classes), unresolved)


@pytest.mark.parametrize(
    "atom, key",
    [
        (("inclusion", "lab", ("platelets",), (("value", "100"),)), "inclusion:lab:platelets"),
        (("exclusion", "prior_agent", ("PD-1",), ()), "exclusion:prior_agent:PD-1"),
        (("inclusion", "ecog_ps", ("0", "1"), ()), "inclusion:ecog_ps=0|1"),
        (("inclusion", "biomarker:PD-L1", (), (("expression", "≥50%"),)), "inclusion:biomarker:PD-L1=@≥50%"),
    ],
)
def test_element_keys(atom, key):
    assert element_key(*atom) == key


def test_requiring_and_excluding_are_different_elements():
    assert element_key("inclusion", "prior_agent", ("PD-1",), ()) != element_key(
        "exclusion", "prior_agent", ("PD-1",), ()
    )


def test_frequencies_count_typed_trials_only():
    trials = [
        trial("A", "S1", elements=["x", "y"]),
        trial("B", "S2", elements=["x"]),
        trial("C", "S2", typed=False, elements=["y", "y"]),
    ]
    rows = frequency_rows(trials)
    assert rows == [
        ("all", "x", 2, 2, 1.0, 0.0, 2, "standard"),
        ("all", "y", 1, 2, 0.5, 1.0, 1, ""),
    ]


def test_surprisal_is_minus_log2_of_the_share():
    trials = [trial(str(i), elements=["x"] if i == 0 else []) for i in range(8)]
    assert frequency_rows(trials)[0][5] == round(-math.log2(1 / 8), 3)


def test_a_stratum_with_no_typed_trial_has_no_rows():
    assert frequency_rows([trial("A", typed=False, elements=["x"])]) == []


def population(sponsors):
    inside = [trial(f"in{i}", sponsors[i], elements=["e"], classes=["VEGF"]) for i in range(6)]
    outside = [
        trial(f"out{i}", f"T{i}", elements=["e"] if i == 0 else [], classes=["PD-1"]) for i in range(6)
    ]
    return inside + outside + [trial("u", "U", elements=["e"], unresolved=True)]


def test_a_class_linked_element_is_proposed_with_its_counts():
    rows = [row for row in mechanism_rows(population([f"S{i}" for i in range(6)])) if row[1] == "VEGF"]
    assert rows == [("all", "VEGF", "e", 6, 6, 1, 6, 1.0, 0.1667, 0.8333, 6, 1, "proposed")]


def test_one_sponsor_never_makes_a_proposal():
    rows = [row for row in mechanism_rows(population(["S"] * 6)) if row[1] == "VEGF"]
    assert [row[-1] for row in rows] == ["below_support"]
    assert rows[0][10] == 1


def test_an_element_no_more_frequent_within_the_class_is_not_listed():
    assert [row for row in mechanism_rows(population([f"S{i}" for i in range(6)])) if row[1] == "PD-1"] == []


def test_occupancy_states():
    trials = [
        ("A", ("advanced_first_line",), ("PD-1",)),
        ("B", ("advanced_first_line", "advanced_previously_treated"), ("VEGF",)),
        ("C", ("adjuvant",), ()),
    ]
    rows = occupancy_rows(
        [
            ("advanced_first_line", "PD-1"),
            ("advanced_previously_treated", "VEGF"),
            ("adjuvant", "EGFR"),
            ("consolidation", "PD-1"),
        ],
        trials,
    )
    assert rows == [
        ("advanced_first_line", "PD-1", 1, 0, "occupied"),
        ("advanced_previously_treated", "VEGF", 0, 1, "unknown"),
        ("adjuvant", "EGFR", 0, 1, "unknown"),
        ("consolidation", "PD-1", 0, 0, "empty"),
    ]
