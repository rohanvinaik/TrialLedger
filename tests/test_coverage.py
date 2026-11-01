"""Eligibility coverage — what a record's eligibility text says about itself, attributes kept apart.

The wording below is real (the 487 interventional Phase 3 NSCLC trials of 2015-2024, NCT numbers named),
except the completeness statements, which match nothing in that population and are synthetic.

Positive: empty text is empty; a heading sections the text; "Key Exclusion Criteria" scopes the exclusions
only and "Key Inclusion Criteria" the inclusions only; a note naming inclusion/exclusion scopes both; a note
naming neither takes its section, and in unsectioned text both; each marker keeps its piece and exact offsets;
a completeness statement is completeness_stated in its scope.
Negative: no marker never means complete (unspecified, never completeness_stated); "Key Exclusion Criteria"
never makes the inclusions abbreviated; a completeness statement never outweighs an abbreviation in the same
scope; whitespace-only text never has content.
"""

import pytest

from TrialLedger.criteria import eligibility_coverage, itemize


def coverage(text):
    return eligibility_coverage(text, itemize(text)[1])


def evidence(text):
    return dict(coverage(text)[2])


def test_empty_text_has_no_content_and_says_nothing():
    for text in ("", "  \n\t"):
        assert coverage(text) == (
            "empty",
            "unsectioned",
            (("inclusion", "unspecified"), ("exclusion", "unspecified")),
            [],
        )


def test_no_marker_never_means_complete():
    text = "Inclusion Criteria:\n\n* ECOG 0-1\n\nExclusion Criteria:\n\n* Pregnancy\n"
    content, sectioning, said, markers = coverage(text)
    assert (content, sectioning, markers) == ("present", "sectioned", [])
    assert dict(said) == {"inclusion": "unspecified", "exclusion": "unspecified"}


def test_unsectioned_text_is_unsectioned():
    assert coverage("* ECOG 0-1\n* No prior chemotherapy\n")[1] == "unsectioned"


def test_key_exclusion_criteria_scopes_the_exclusions_only():
    # NCT03456076: "Key Inclusion Criteria" without an exclusion marker is the same, the other way round
    text = "Inclusion Criteria:\n\n* ECOG 0-1\n\nKey Exclusion Criteria:\n\n* Pregnancy\n"
    content, _, said, markers = coverage(text)
    assert dict(said) == {"inclusion": "unspecified", "exclusion": "abbreviation_stated"}
    ((kind, scope, piece, start, end),) = markers
    assert (kind, scope, piece, text[start:end]) == ("abbreviation_stated", "exclusion", 2, "Key Exclusion")


def test_key_inclusion_criteria_scopes_the_inclusions_only():
    # NCT05607550's headings
    text = "Key Inclusion Criteria:\n\n* ECOG 0-1\n\nExclusion Criteria:\n\n* Pregnancy\n"
    assert evidence(text) == {"inclusion": "abbreviation_stated", "exclusion": "unspecified"}


def test_a_note_naming_both_scopes_both_wherever_it_sits():
    # NCT04746924, NCT05605613: the note sits under the exclusion heading
    text = (
        "Inclusion Criteria:\n\n* ECOG 0-1\n\nExclusion Criteria:\n\n* Pregnancy\n\n"
        "Note: Other protocol defined Inclusion/Exclusion criteria may apply\n"
    )
    _, _, said, markers = coverage(text)
    assert dict(said) == {"inclusion": "abbreviation_stated", "exclusion": "abbreviation_stated"}
    assert [(m[1], text[m[3] : m[4]]) for m in markers] == [
        ("both", "Other protocol defined Inclusion/Exclusion criteria may apply")
    ]


def test_a_note_naming_neither_takes_its_section():
    # NCT02576574: the same words under each heading
    inclusion_only = (
        "Inclusion Criteria:\n\n* ECOG 0-1\n* Other protocol defined criteria could apply\n\n"
        "Exclusion Criteria:\n\n* Pregnancy\n"
    )
    assert evidence(inclusion_only) == {"inclusion": "abbreviation_stated", "exclusion": "unspecified"}


def test_a_note_in_unsectioned_text_scopes_both():
    # NCT05722015, NCT06312137
    text = (
        "The key inclusion and exclusion criteria include but are not limited to the following:\n\n"
        "* ECOG 0-1\n"
    )
    _, sectioning, said, markers = coverage(text)
    assert sectioning == "unsectioned"
    assert dict(said) == {"inclusion": "abbreviation_stated", "exclusion": "abbreviation_stated"}
    assert {m[1] for m in markers} == {"both"}


def test_completeness_is_stated_only_by_a_statement_of_it():
    text = (
        "Inclusion Criteria:\n\n* ECOG 0-1\n\nExclusion Criteria:\n\n* Pregnancy\n\n"
        "No other exclusion criteria apply.\n"
    )
    assert evidence(text) == {"inclusion": "unspecified", "exclusion": "completeness_stated"}


def test_an_abbreviation_outweighs_completeness_in_its_scope():
    text = "Key Exclusion Criteria:\n\n* Pregnancy\n\nNo other exclusion criteria apply.\n"
    assert evidence(text)["exclusion"] == "abbreviation_stated"
    kinds = [m[0] for m in coverage(text)[3]]
    assert kinds == ["abbreviation_stated", "completeness_stated"]


@pytest.mark.parametrize(
    "line",
    [
        # measured on the development data and left for the founder's decision (see the transition report)
        "Note: Other protocol-defined inclusion/exclusion criteria apply",  # NCT04026412: no modal verb
        "Other protocol inclusion/exclusion criteria may apply",  # NCT03215706
    ],
)
def test_the_measured_misses_stay_unspecified_until_the_founder_decides(line):
    text = f"Inclusion Criteria:\n\n* ECOG 0-1\n\nExclusion Criteria:\n\n* Pregnancy\n\n{line}\n"
    assert evidence(text) == {"inclusion": "unspecified", "exclusion": "unspecified"}
