"""Review flags — what the system cannot cleanly resolve, as typed questions, never resolved here.

Positive: an unresolved or failed drug class, an emptied coordinate, an unresolved expectation, an
admitting observation and a record that says its criteria are abbreviated each give one flag, with its
evidence, a question and a closed set of options.
Negative: a classified or record-stated drug, a resolved or unresolved-but-non-empty coordinate, a present,
not documented or not applicable observation and a record with no abbreviation marker never give a flag; no
flag carries an answer.
"""

import pytest

from TrialLedger.layer2.review import flags_for

FULL = {"setting": ["adjuvant", "advanced_first_line"], "prior_advanced_lines": ["0", "1"]}


def kinds(flags):
    return [flag[0] for flag in flags]


def test_a_clean_trial_has_nothing_to_flag():
    assert (
        flags_for(
            [("Pembrolizumab", "classified"), ("XB-1", "stated_by_record")],
            {
                "setting": (["advanced_first_line"], "resolved", []),
                "prior_advanced_lines": (["0", "1"], "unnarrowed", []),
            },
            FULL,
            {
                "e": ("present", "excluded", ["* Active autoimmune disease"]),
                "f": ("not_documented", "not_named", []),
            },
            ["PD-1 Blocking Antibody"],
            [],
        )
        == []
    )


@pytest.mark.parametrize("state", ["unresolved", "lookup_failed"])
def test_an_unresolved_drug_class_is_a_closed_question(state):
    (flag,) = flags_for([("SCT-I10", state)], {}, FULL, {}, ["PD-1 Blocking Antibody"], [])
    assert flag[0] == "drug_class_unresolved" and flag[1] == "SCT-I10" and state in flag[2]
    assert flag[6] == ["PD-1 Blocking Antibody", "none of these"]


def test_a_conflict_offers_every_value_and_cohorts():
    (flag,) = flags_for([], {"setting": ([], "conflict", ["criterion 3", "criterion 9"])}, FULL, {}, [], [])
    assert flag[0] == "coordinate_conflict" and flag[4] == ["criterion 3", "criterion 9"]
    assert flag[6] == ["adjuvant", "advanced_first_line", "the trial has cohorts that differ"]


def test_unresolved_and_admitting_observations_are_flagged_with_their_evidence():
    flags = flags_for(
        [],
        {},
        FULL,
        {
            "a": ("unresolved", "conflicting_scopes", ["* Cohort A ...", "* Cohort B ..."]),
            "b": ("explicitly_negated", "admitted", ["* Patients with lupus are eligible"]),
            "c": ("not_applicable", "no class", []),
        },
        [],
        [],
    )
    assert kinds(flags) == ["expectation_unresolved", "verified_deviation"]
    assert flags[0][2] == "conflicting_scopes" and flags[1][4] == ["* Patients with lupus are eligible"]


def test_an_abbreviated_record_is_one_closed_question_with_every_marker():
    markers = [
        ("inclusion", "piece 0, characters 0-13: Key Inclusion"),
        ("exclusion", "piece 7, characters 905-918: Key Exclusion"),
    ]
    (flag,) = flags_for([], {}, FULL, {}, [], markers)
    assert flag[0] == "eligibility_abbreviated" and "(exclusion, inclusion)" in flag[2]
    assert flag[4] == [
        "[inclusion] piece 0, characters 0-13: Key Inclusion",
        "[exclusion] piece 7, characters 905-918: Key Exclusion",
    ]
    assert flag[6] == ["abbreviated (confirmed)", "not abbreviated (the marker is misread)"]


def test_no_flag_carries_an_answer():
    flags = flags_for(
        [("X", "unresolved")],
        {"setting": ([], "conflict", [])},
        FULL,
        {"a": ("unresolved", "r", [])},
        [],
        [("exclusion", "Key Exclusion")],
    )
    assert all(len(flag) == 7 for flag in flags)
