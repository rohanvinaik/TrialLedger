"""split_eligibility — split at the registry's stated headers, or abstain.

Positive: one inclusion heading then one exclusion heading splits into three parts that join back to the
text exactly; a heading may carry a trailing colon and surrounding spaces or tabs.
Negative: a missing, repeated or misordered heading never splits; a header inside a sentence,
bullet or heading with other text on its line is not a heading. Case and CR/LF are literal format variants.
"""

import pytest

from TrialLedger.eligibility import heading_kind, legacy_split_eligibility, split_eligibility

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
        "inclusion criteria:\n* a\nexclusion criteria:\n* b",
        "INCLUSION CRITERIA:\n* a\nEXCLUSION CRITERIA:\n* b",
        "Intro\r\nInclusion criteria:\r\n* a\r\nExclusion criteria:\r\n* b\r\n",
        "Inclusion Criteria:\r* a\rExclusion Criteria:\r* b",
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
        ("**Inclusion Criteria:**\n* a\n**Exclusion Criteria:**\n* b", "not_split_missing"),
        ("Inclusion Criteria: adults\nExclusion Criteria: none", "not_split_missing"),
        ("See the Inclusion Criteria below.\nExclusion Criteria:\n* b", "not_split_missing"),
    ],
)
def test_ambiguous_text_is_not_split(text, expected):
    assert split_eligibility(text) == (expected, "", "", "")


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Inclusion criteria:\r\n", "inclusion"),
        ("  EXCLUSION CRITERIA \r", "exclusion"),
        ("\tInClUsIoN cRiTeRiA\t", "inclusion"),
        ("* Inclusion criteria:", "not_heading"),
        ("Crossover Inclusion Criteria:", "not_heading"),
        ("See Inclusion Criteria", "not_heading"),
        ("Inclusion Criteria:\nAdults", "not_heading"),
        ("", "not_heading"),
        (None, "not_text"),
        (False, "not_text"),
        ([], "not_text"),
    ],
)
def test_heading_kind_is_structural_and_total(line, expected):
    assert heading_kind(line) == expected


def test_case_variants_do_not_relax_repeated_or_reversed_sections():
    assert (
        split_eligibility("Inclusion criteria:\nA\nINCLUSION CRITERIA:\nB\nExclusion criteria:\nC")[0]
        == "not_split_repeated"
    )
    assert split_eligibility("Exclusion criteria:\nB\nInclusion criteria:\nA")[0] == "not_split_order"


def test_retained_splitter_keeps_old_case_and_crlf_abstentions():
    text = "Inclusion criteria:\r\nA\r\nExclusion criteria:\r\nB"
    assert legacy_split_eligibility(text) == ("not_split_missing", "", "", "")
    assert legacy_split_eligibility(STANDARD) == split_eligibility(STANDARD)
