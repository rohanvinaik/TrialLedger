"""Near misses — one difference under a declared representation.

Positive: two trials with equal, known representations and exactly one differing known predicate pair, with
the predicate, both values, sponsors, years and the number of agreeing predicates.
Negative: an unknown representation value never matches; different representations never pair; two or more
differences, or none, never pair; a predicate unknown in either trial is never a difference.
"""

from TrialLedger.layer2.nearmiss import near_misses

REP = {"setting": "advanced_first_line", "classes": "PD-1"}


def trial(nct, predicates, rep=REP, sponsor="S", era="2019"):
    return (nct, dict(rep), predicates, sponsor, era)


def test_one_difference_pairs():
    pairs = near_misses(
        [
            trial("A", {"ecog": "0|1", "histology": "non_squamous"}, sponsor="S1", era="2018"),
            trial("B", {"ecog": "0|1|2", "histology": "non_squamous"}, sponsor="S2", era="2021"),
        ]
    )
    assert pairs == [("A", "B", "ecog", "0|1", "0|1|2", "S1", "S2", "2018", "2021", 1)]


def test_an_unknown_never_matches_and_never_differs():
    unknown_rep = {"setting": "", "classes": "PD-1"}
    assert (
        near_misses(
            [trial("A", {"ecog": "0|1"}, rep=unknown_rep), trial("B", {"ecog": "0|1|2"}, rep=unknown_rep)]
        )
        == []
    )
    assert near_misses([trial("A", {"ecog": "0|1", "x": ""}), trial("B", {"ecog": "0|1|2", "x": "1"})]) == [
        ("A", "B", "ecog", "0|1", "0|1|2", "S", "S", "2019", "2019", 0)
    ]


def test_different_representations_never_pair():
    other = {"setting": "advanced_previously_treated", "classes": "PD-1"}
    assert near_misses([trial("A", {"ecog": "0|1"}), trial("B", {"ecog": "0|1|2"}, rep=other)]) == []


def test_zero_or_two_differences_never_pair():
    assert near_misses([trial("A", {"ecog": "0|1", "h": "s"}), trial("B", {"ecog": "0|1", "h": "s"})]) == []
    assert near_misses([trial("A", {"ecog": "0|1", "h": "s"}), trial("B", {"ecog": "0|1|2", "h": "n"})]) == []


def test_an_empty_representation_never_pairs():
    assert near_misses([trial("A", {"ecog": "0|1"}, rep={}), trial("B", {"ecog": "0|1|2"}, rep={})]) == []
