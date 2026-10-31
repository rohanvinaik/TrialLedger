"""itemize — eligibility text as headings, criteria and prose, each an exact span.

Positive: the registry's headings and their measured variants ("Key", any case, a full-width colon, a section
number, a cohort or phase qualifier) open a section; "*", "-", "•", "1.", "1)", "1.1", "a." and "i)" open a
criterion; a deeper marker or a deeper unmarked line stays inside its criterion; pieces are in order, never
overlap, and only whitespace lies between them, so pieces and gaps reproduce the text.
Negative: a note naming both kinds ("inclusion/exclusion criteria apply"), a sentence ending in a full stop,
a heading with text after its colon, and a bulleted line mentioning inclusion are never headings; an unmarked
note after the last criterion is never glued to it; text with no list marker is never forced into criteria;
empty text has no pieces; a criterion's section is never guessed when no heading precedes it.
"""

import pytest

from TrialLedger.criteria import itemize

REAL = (
    "Key Inclusion Criteria:\n\n"
    "1. Written and signed informed consent\n"
    "2. Eastern Cooperative Oncology Group (ECOG) performance status 0 or 1\n\n"
    "Key Exclusion Criteria:\n\n"
    "1. Documented squamous NSCLC or small cell type or large cell neuroendocrine histology\n"
    "2. History of significant hemoptysis, central tumors with proximity to large vessels"
)


def texts(text, pieces):
    return [(kind, section, text[start:end]) for kind, section, start, end in pieces]


def test_a_real_numbered_text_becomes_criteria():
    code, pieces = itemize(REAL)
    assert code == "itemized"
    assert texts(REAL, pieces) == [
        ("heading", "inclusion", "Key Inclusion Criteria:"),
        ("criterion", "inclusion", "1. Written and signed informed consent"),
        ("criterion", "inclusion", "2. Eastern Cooperative Oncology Group (ECOG) performance status 0 or 1"),
        ("heading", "exclusion", "Key Exclusion Criteria:"),
        (
            "criterion",
            "exclusion",
            "1. Documented squamous NSCLC or small cell type or large cell neuroendocrine histology",
        ),
        (
            "criterion",
            "exclusion",
            "2. History of significant hemoptysis, central tumors with proximity to large vessels",
        ),
    ]


@pytest.mark.parametrize(
    "heading, section",
    [
        ("Inclusion Criteria:", "inclusion"),
        ("Exclusion criteria", "exclusion"),
        ("INCLUSION CRITERIA:", "inclusion"),
        ("Inclusion criteria：", "inclusion"),
        ("1.0 Inclusion Criteria", "inclusion"),
        ("2.0 Exclusion Criteria", "exclusion"),
        ("Main Cohort Key Exclusion Criteria:", "exclusion"),
        ("Inclusion Criteria (All Cohorts):", "inclusion"),
        ("Exclusion criteria specific to Cohort A1:", "exclusion"),
        ("Exclusion Criteria Related to Medications and Chemotherapy:", "exclusion"),
        ("Exclusion criterion:", "exclusion"),
        ("**Inclusion Criteria:**", "inclusion"),
    ],
)
def test_heading_variants_open_their_section(heading, section):
    text = f"{heading}\n* a criterion"
    code, pieces = itemize(text)
    assert code == "itemized"
    assert texts(text, pieces) == [("heading", section, heading), ("criterion", section, "* a criterion")]


@pytest.mark.parametrize(
    "line",
    [
        "Other protocol defined inclusion/exclusion criteria apply",
        "Note: Other protocol-defined Inclusion/ Exclusion Criteria apply",
        "Further inclusion criteria apply.",
        "Inclusion Criteria:1. Age: 18-75 years old, male or female;",
    ],
)
def test_notes_and_run_on_lines_are_never_headings(line):
    code, pieces = itemize(line)
    assert code == "no_list_markers"
    assert pieces == [("prose", "unsectioned", 0, len(line))]


def test_a_bulleted_line_mentioning_inclusion_is_a_criterion():
    text = "Exclusion Criteria:\n* Major surgery 28 days before inclusion into the study"
    _, pieces = itemize(text)
    assert texts(text, pieces)[1] == (
        "criterion",
        "exclusion",
        "* Major surgery 28 days before inclusion into the study",
    )


@pytest.mark.parametrize("marker", ["*", "-", "•", "1.", "1)", "1.1", "a.", "i)"])
def test_every_measured_marker_opens_a_criterion(marker):
    text = f"Inclusion Criteria:\n{marker} first\n{marker} second"
    code, pieces = itemize(text)
    assert code == "itemized"
    assert [kind for kind, *_ in pieces] == ["heading", "criterion", "criterion"]


def test_sub_items_and_continuations_stay_inside_their_criterion():
    text = (
        "Inclusion Criteria:\n"
        "* Adequate organ function:\n"
        "  * ANC ≥ 1.5 × 10^9/L\n"
        "  * Platelets ≥ 100 × 10^9/L\n"
        "    measured within 14 days\n"
        "* ECOG 0-1"
    )
    _, pieces = itemize(text)
    assert texts(text, pieces)[1:] == [
        (
            "criterion",
            "inclusion",
            "* Adequate organ function:\n  * ANC ≥ 1.5 × 10^9/L\n  * Platelets ≥ 100 × 10^9/L\n"
            "    measured within 14 days",
        ),
        ("criterion", "inclusion", "* ECOG 0-1"),
    ]


def test_an_unmarked_note_after_the_last_criterion_is_its_own_prose():
    text = "Exclusion Criteria:\n* Pregnancy\nNote: Other protocol defined criteria may apply"
    _, pieces = itemize(text)
    assert texts(text, pieces)[1:] == [
        ("criterion", "exclusion", "* Pregnancy"),
        ("prose", "exclusion", "Note: Other protocol defined criteria may apply"),
    ]


def test_an_indented_list_under_a_heading_keeps_exact_spans():
    text = "Inclusion Criteria:\n  1. Age ≥ 18\n  2. ECOG 0-1"
    _, pieces = itemize(text)
    assert pieces == [
        ("heading", "inclusion", 0, 19),
        ("criterion", "inclusion", 22, 33),
        ("criterion", "inclusion", 36, 47),
    ]
    assert [text[s:e] for _, _, s, e in pieces[1:]] == ["1. Age ≥ 18", "2. ECOG 0-1"]


def test_an_indented_marker_after_prose_opens_a_criterion():
    text = "Inclusion Criteria:\nPatients must meet all of the following:\n  * Age ≥ 18"
    _, pieces = itemize(text)
    assert [kind for kind, *_ in pieces] == ["heading", "prose", "criterion"]


def test_consecutive_unmarked_lines_are_one_prose_piece():
    text = "Notes:\nOther protocol defined criteria may apply"
    assert itemize(text) == ("no_list_markers", [("prose", "unsectioned", 0, len(text))])


def test_a_tab_counts_four_columns():
    # a sub-item indented five spaces under a tab-indented item is deeper (5 > 4); one indented four is not
    deeper = "\t* parent\n     * child"
    level = "\t* parent\n    * sibling"
    assert [kind for kind, *_ in itemize(deeper)[1]] == ["criterion"]
    assert [kind for kind, *_ in itemize(level)[1]] == ["criterion", "criterion"]


def test_text_before_any_heading_is_unsectioned():
    text = "For inclusion in the study, patients should fulfill the following:\n* Age 18 or older"
    _, pieces = itemize(text)
    assert [(kind, section) for kind, section, *_ in pieces] == [
        ("prose", "unsectioned"),
        ("criterion", "unsectioned"),
    ]


@pytest.mark.parametrize("text", ["", "   \n\t\n"])
def test_empty_text_has_no_pieces(text):
    assert itemize(text) == ("empty", [])


@pytest.mark.parametrize(
    "text",
    [
        REAL,
        "Inclusion Criteria:\n\n* a\n\n  * b\n\nExclusion Criteria:\n\n1) c\n   continued\n\nNotes:\nsee\n",
        "Adults with stage IV disease who consent.",
        "  * leading indent\r\n* windows line ending\r\n",
    ],
)
def test_pieces_and_gaps_reproduce_the_text(text):
    _, pieces = itemize(text)
    cursor = 0
    for _, _, start, end in pieces:
        assert start >= cursor and end > start
        assert text[cursor:start].strip() == ""
        assert text[start:end] == text[start:end].strip()
        cursor = end
    assert text[cursor:].strip() == ""


def test_a_non_inclusion_heading_opens_the_exclusion_section():
    text = "INCLUSION CRITERIA:\n1. Adults\nNON-INCLUSION CRITERIA:\n9. Active autoimmune disease"
    assert [(kind, section) for kind, section, *_ in itemize(text)[1]] == [
        ("heading", "inclusion"),
        ("criterion", "inclusion"),
        ("heading", "exclusion"),
        ("criterion", "exclusion"),
    ]
