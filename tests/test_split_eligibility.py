"""split_eligibility — split at the registry's stated headers, or abstain.

Positive: one inclusion heading then one exclusion heading splits into three parts that join back to the
text exactly; a heading may carry a trailing colon and surrounding spaces or tabs.
Negative: a missing, repeated or misordered heading never splits; a header inside a sentence, a variant in
case, or a heading with other text on its line is not a heading.
"""

import pytest

from TrialLedger.eligibility import split_eligibility

STANDARD = "Inclusion Criteria:\n\n* adults\n\nExclusion Criteria:\n\n* pregnancy"


def test_standard_headings_split_into_three_parts():
    code, before, inclusion, exclusion = split_eligibility(STANDARD)
    assert code == "split"
    assert before == ""
    assert inclusion == "Inclusion Criteria:\n\n* adults\n\n"
    assert exclusion == "Exclusion Criteria:\n\n* pregnancy"


@pytest.mark.parametrize(
    "text",
    [
        STANDARD,
        "Key criteria for this trial.\n\nInclusion Criteria\n* a\nExclusion Criteria\n* b",
        "  Inclusion Criteria:  \n* a\n\tExclusion Criteria:\t\n* b\n",
        "Inclusion Criteria:\nExclusion Criteria:",
    ],
)
def test_the_parts_join_back_exactly(text):
    code, before, inclusion, exclusion = split_eligibility(text)
    assert code == "split"
    assert before + inclusion + exclusion == text


def test_text_before_the_inclusion_heading_is_kept():
    code, before, inclusion, _ = split_eligibility(
        "Summary line\nInclusion Criteria:\n* a\nExclusion Criteria:\n* b"
    )
    assert code == "split"
    assert before == "Summary line\n"
    assert inclusion.startswith("Inclusion Criteria:")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Adults seen at the clinic.", "not_split_missing"),
        ("Inclusion Criteria:\n* a", "not_split_missing"),
        ("Exclusion Criteria:\n* b", "not_split_missing"),
        ("", "not_split_missing"),
        (
            "Inclusion Criteria:\n* a\nInclusion Criteria:\n* c\nExclusion Criteria:\n* b",
            "not_split_repeated",
        ),
        (
            "Inclusion Criteria:\n* a\nExclusion Criteria:\n* b\nExclusion Criteria:\n* c",
            "not_split_repeated",
        ),
        ("Exclusion Criteria:\n* b\nInclusion Criteria:\n* a", "not_split_order"),
        ("inclusion criteria:\n* a\nexclusion criteria:\n* b", "not_split_missing"),
        ("INCLUSION CRITERIA:\n* a\nEXCLUSION CRITERIA:\n* b", "not_split_missing"),
        ("**Inclusion Criteria:**\n* a\n**Exclusion Criteria:**\n* b", "not_split_missing"),
        ("Inclusion Criteria: adults\nExclusion Criteria: none", "not_split_missing"),
        ("See the Inclusion Criteria below.\nExclusion Criteria:\n* b", "not_split_missing"),
    ],
)
def test_ambiguous_text_is_not_split(text, expected):
    assert split_eligibility(text) == (expected, "", "", "")
