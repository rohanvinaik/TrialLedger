"""Profile — elements measured against the population, kept apart as frequency, association and occupancy.

Positive: an element's registry statement rate is over every trial of the stratum, with the surprisal of that
rate in bits and its sponsors; an eligibility element's full-criteria frequency is the interval [S/N,
(S+U)/N], its unresolved silences counted as empty, no rule match, abbreviated and unspecified; the standard
tier is met when the lower bound reaches the threshold, not met when the upper bound falls short, unresolved
otherwise; a primary endpoint has the statement rate only; an element stated more often within a class's typed
trials, from enough trials and sponsors, and still so with abbreviated silences read least favourably, is a
proposed relation, with the 2×2 counts, the unresolved trials and the abbreviated silences named; a comparison
that abbreviated silences could reverse, or could make, is listed as unresolved; a cell with an occupant is
occupied, a failed or withdrawn one included.
Negative: a silent trial is never counted as lacking an element (A stays 0: no ascertainment rule is
declared), so the tier is never "not_met" while any silence is unresolved; a trial no bank typed is never
"unspecified"; a primary endpoint is never given an interval or a tier, even when every trial states it; a
share just under the threshold never rounds up to "met"; an abbreviated exclusion section never makes an
inclusion element's silence abbreviated; a trial whose text was never typed is never in a mechanism group; a
comparison abbreviated silences could reverse is never proposed, whatever its support; one sponsor never makes
a proposal; an element no more frequent within a class at any reading is never listed; a cell that unresolved
trials could fall in is never empty; requiring and excluding the same thing are never one element.
"""

import math

import pytest

from TrialLedger.profile import (
    element_key,
    element_silence,
    frequency_rows,
    full_criteria_tier,
    mechanism_rows,
    occupancy_rows,
)

SAID_NOTHING = (("inclusion", "unspecified"), ("exclusion", "unspecified"))
KEY_EXCLUSIONS = (("inclusion", "unspecified"), ("exclusion", "abbreviation_stated"))


def trial(
    nct,
    sponsor="S",
    stratum="all",
    typed=True,
    elements=(),
    classes=(),
    unresolved=False,
    content="present",
    coverage=SAID_NOTHING,
):
    return (nct, sponsor, stratum, typed, list(elements), list(classes), unresolved, content, coverage)


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


@pytest.mark.parametrize(
    "element, content, typed, coverage, silence",
    [
        ("exclusion:condition=hiv", "empty", False, SAID_NOTHING, "empty"),
        # no bank typed the trial's text: its own kind, ahead of what the record says of its coverage
        ("exclusion:condition=hiv", "present", False, KEY_EXCLUSIONS, "no_rule_match"),
        ("exclusion:condition=hiv", "present", False, SAID_NOTHING, "no_rule_match"),
        ("exclusion:condition=hiv", "present", True, KEY_EXCLUSIONS, "abbreviated"),
        (
            "inclusion:ecog_ps=0|1",
            "present",
            True,
            KEY_EXCLUSIONS,
            "unspecified",
        ),  # the inclusions said nothing
        (
            "permitted:prior_agent:PD-1",
            "present",
            True,
            KEY_EXCLUSIONS,
            "abbreviated",
        ),  # either section could
        ("unsectioned:lab:platelets", "present", True, KEY_EXCLUSIONS, "abbreviated"),
        ("exclusion:condition=hiv", "present", True, SAID_NOTHING, "unspecified"),
        # a completeness statement alone establishes nothing: no ascertainment rule is declared
        ("exclusion:condition=hiv", "present", True, (("exclusion", "completeness_stated"),), "unspecified"),
        # a primary endpoint is not an eligibility element, whatever the trial's eligibility
        ("primary:endpoint:overall_survival", "empty", False, KEY_EXCLUSIONS, "not_eligibility"),
        ("primary:endpoint:overall_survival", "present", True, KEY_EXCLUSIONS, "not_eligibility"),
    ],
)
def test_why_a_trial_is_silent(element, content, typed, coverage, silence):
    assert element_silence(element, content, typed, coverage) == silence


@pytest.mark.parametrize(
    "s, a, u, n, tier",
    [
        (9, 0, 1, 10, "met"),  # the lower bound reaches the threshold
        (8, 2, 0, 10, "not_met"),  # the upper bound falls short
        (8, 0, 2, 10, "unresolved"),
        (8, 1, 1, 10, "unresolved"),  # the upper bound reaches it exactly
        (89996, 0, 10004, 100000, "unresolved"),  # 0.89996, never rounded up to met
        (0, 0, 0, 0, "unresolved"),
    ],
)
def test_the_standard_tier_is_three_valued(s, a, u, n, tier):
    assert full_criteria_tier(s, a, u, n, 0.9) == tier


INTERVAL = "statement rate and full-criteria interval"
RATE_ONLY = "statement rate only (not an eligibility element)"


def test_every_trial_is_in_the_cohort_and_silence_is_unresolved_by_kind():
    trials = [
        trial("A", "S1", elements=["exclusion:x", "inclusion:y"]),
        trial("B", "S2", elements=["exclusion:x"], coverage=KEY_EXCLUSIONS),
        trial("C", "S3", elements=["inclusion:z"], coverage=KEY_EXCLUSIONS),
        trial("D", "S4", content="empty"),
        trial("E", "S5", typed=False),  # text, no list markers: no bank typed it
        trial("F", "S6", elements=["primary:endpoint:pfs"]),  # an endpoint typed, its eligibility not
    ]
    assert frequency_rows(trials) == [
        ("all", "exclusion:x", 2, 0, 1, 2, 1, 0, 4, 6, 0.3333, 0.3333, 1.0, 1.585, 2, "unresolved", INTERVAL),
        ("all", "inclusion:y", 1, 0, 1, 2, 0, 2, 5, 6, 0.1667, 0.1667, 1.0, 2.585, 1, "unresolved", INTERVAL),
        ("all", "inclusion:z", 1, 0, 1, 2, 0, 2, 5, 6, 0.1667, 0.1667, 1.0, 2.585, 1, "unresolved", INTERVAL),
        ("all", "primary:endpoint:pfs", 1, *[None] * 6, 6, 0.1667, None, None, 2.585, 1, "", RATE_ONLY),
    ]


def test_an_untyped_trial_is_never_unspecified_nor_absent():
    (row,) = frequency_rows([trial("A", elements=["exclusion:e"]), trial("x", typed=False)])
    assert row[3] == 0 and row[4:9] == (0, 1, 0, 0, 1)  # one no_rule_match, never unspecified or absent


def test_an_element_nearly_every_trial_states_is_standard():
    trials = [trial(str(i), elements=["inclusion:x"]) for i in range(9)] + [
        trial("9", elements=["inclusion:y"])
    ]
    assert frequency_rows(trials)[0][15] == "met"


def test_a_primary_endpoint_has_the_statement_rate_only():
    # every trial states it, yet it is never given an interval or a tier: it is not eligibility
    (row,) = frequency_rows([trial(str(i), elements=["primary:endpoint:os"]) for i in range(10)])
    assert row[2] == 10 and row[9:11] == (10, 1.0)
    assert row[3:9] == (None,) * 6 and row[11:13] == (None, None)
    assert row[15:] == ("", RATE_ONLY)


def test_surprisal_is_minus_log2_of_the_statement_rate():
    trials = [trial(str(i), elements=["x"] if i == 0 else []) for i in range(8)]
    assert frequency_rows(trials)[0][13] == round(-math.log2(1 / 8), 3)


def test_a_stratum_where_nothing_is_stated_has_no_rows():
    assert frequency_rows([trial("A"), trial("B", content="empty")]) == []


def population(sponsors):
    inside = [trial(f"in{i}", sponsors[i], elements=["e"], classes=["VEGF"]) for i in range(6)]
    outside = [
        trial(f"out{i}", f"T{i}", elements=["e"] if i == 0 else [], classes=["PD-1"]) for i in range(6)
    ]
    return inside + outside + [trial("u", "U", elements=["e"], unresolved=True)]


def test_a_class_linked_element_is_proposed_with_its_counts():
    rows = [row for row in mechanism_rows(population([f"S{i}" for i in range(6)])) if row[1] == "VEGF"]
    assert rows == [("all", "VEGF", "e", 6, 6, 1, 6, 1.0, 0.1667, 0.8333, 0.8333, 6, 1, 0, 0, "proposed")]


def test_abbreviated_silences_are_named_and_a_robust_comparison_is_proposed():
    trials = population([f"S{i}" for i in range(6)])
    trials[7] = trial("out1", "T1", classes=["PD-1"], coverage=KEY_EXCLUSIONS)  # silent, abbreviated
    rows = [row for row in mechanism_rows(trials) if row[1] == "VEGF"]
    assert rows[0][13:15] == (0, 0)  # "e" is no eligibility element: its silence is never abbreviated
    trials = [trial(f"in{i}", f"S{i}", elements=["exclusion:hiv"], classes=["VEGF"]) for i in range(5)] + [
        trial("in5", "S5", classes=["VEGF"], coverage=KEY_EXCLUSIONS),
        trial("out0", "T0", classes=["PD-1"], coverage=KEY_EXCLUSIONS),
        trial("out1", "T1", classes=["PD-1"]),
    ]
    (row,) = [row for row in mechanism_rows(trials) if row[1] == "VEGF"]
    # 5/6 against 0/2, and against (0+1)/2 at the least favourable reading: it still holds
    assert row[3:7] == (5, 6, 0, 2) and row[10] == 0.3333 and row[13:] == (1, 1, "proposed")


def test_a_comparison_abbreviated_silences_could_reverse_is_unresolved_never_proposed():
    trials = [trial(f"in{i}", f"S{i}", elements=["exclusion:hiv"], classes=["VEGF"]) for i in range(5)] + [
        trial("in5", "S5", classes=["VEGF"]),
        trial("out0", "T0", elements=["exclusion:hiv"], classes=["PD-1"]),
        *[trial(f"out{i}", f"T{i}", classes=["PD-1"], coverage=KEY_EXCLUSIONS) for i in (1, 2, 3)],
    ]
    (row,) = [row for row in mechanism_rows(trials) if row[1] == "VEGF"]
    # 5/6 > 1/4 as stated, but not 5/6 > (1+3)/4: enough trials and sponsors, still not proposed
    assert row[3:7] == (5, 6, 1, 4) and row[9:11] == (0.5833, -0.1667) and row[-1] == "unresolved"


def test_a_comparison_only_abbreviated_silences_could_make_is_listed_unresolved():
    trials = [trial(f"in{i}", f"S{i}", elements=["exclusion:hiv"], classes=["VEGF"]) for i in range(3)] + [
        *[trial(f"in{i}", f"S{i}", classes=["VEGF"], coverage=KEY_EXCLUSIONS) for i in (3, 4, 5)],
        trial("out0", "T0", elements=["exclusion:hiv"], classes=["PD-1"]),
        trial("out1", "T1", classes=["PD-1"]),
    ]
    (row,) = [row for row in mechanism_rows(trials) if row[1] == "VEGF"]
    # 3/6 is not above 1/2 as stated; (3+3)/6 would be: listed, unresolved, its difference shown as 0
    assert row[9] == 0.0 and row[13:] == (3, 0, "unresolved")


def test_a_comparison_that_fails_at_every_reading_is_not_listed():
    trials = [
        trial("in0", "S0", elements=["exclusion:hiv"], classes=["VEGF"]),
        trial("in1", "S1", classes=["VEGF"]),
        trial("out0", "T0", elements=["exclusion:hiv"], classes=["PD-1"]),
        trial("out1", "T1", classes=["PD-1"], coverage=KEY_EXCLUSIONS),
    ]
    assert [row for row in mechanism_rows(trials) if row[1] == "VEGF"] == []


def test_an_untyped_trial_is_in_the_frequency_cohort_and_in_neither_mechanism_group():
    trials = population([f"S{i}" for i in range(6)]) + [trial("x", "X", typed=False, classes=["PD-1"])]
    (vegf,) = [row for row in mechanism_rows(trials) if row[1] == "VEGF"]
    assert vegf[3:7] == (6, 6, 1, 6)  # "x" is not counted among the others lacking "e"
    (row,) = frequency_rows(trials)
    assert row[2] == 8 and row[9] == 14  # in the cohort of the statement rate


def test_one_sponsor_never_makes_a_proposal():
    rows = [row for row in mechanism_rows(population(["S"] * 6)) if row[1] == "VEGF"]
    assert [row[-1] for row in rows] == ["below_support"]
    assert rows[0][11] == 1


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
