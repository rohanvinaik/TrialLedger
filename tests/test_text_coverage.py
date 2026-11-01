"""text_coverage — the source manifest's gap check: only whitespace lies between eligibility pieces.

Positive: a real numbered text (the same text tests/test_itemize.py reads), itemized, is covered: every
stretch before, between and after its pieces is whitespace only, so the pieces and the gaps reproduce the
text; empty text with no pieces is covered.
Negative: a piece dropped from that itemization leaves its text uncovered, named by its exact offsets; text
before the first or after the last piece is named; overlapping pieces are never called covered; whitespace
between pieces is never named as uncovered; an overlap never hides a hole, nor a hole an overlap: both are
reported together.
"""

from TrialLedger.audit import text_coverage
from TrialLedger.criteria import itemize

REAL = (
    "Key Inclusion Criteria:\n\n"
    "1. Written and signed informed consent\n"
    "2. Eastern Cooperative Oncology Group (ECOG) performance status 0 or 1\n\n"
    "Key Exclusion Criteria:\n\n"
    "1. Documented squamous NSCLC or small cell type or large cell neuroendocrine histology\n"
    "2. History of significant hemoptysis, central tumors with proximity to large vessels"
)


def test_a_real_itemized_text_is_covered():
    _code, pieces = itemize(REAL)
    assert text_coverage(REAL, pieces) == ("covered", [], [])
    assert text_coverage("", []) == ("covered", [], [])
    assert text_coverage("  \n\t", []) == ("covered", [], [])


def test_a_dropped_piece_is_named_by_its_offsets():
    _code, pieces = itemize(REAL)
    dropped = pieces[2]
    code, spans, overlaps = text_coverage(REAL, pieces[:2] + pieces[3:])
    assert code == "uncovered_text" and len(spans) == 1 and overlaps == []
    start, end = spans[0]
    assert REAL[start:end].strip() == REAL[dropped[2] : dropped[3]]


def test_text_outside_the_first_and_last_pieces_is_named():
    _code, pieces = itemize(REAL)
    code, spans, _overlaps = text_coverage(REAL, pieces[1:-1])
    assert code == "uncovered_text"
    assert REAL[spans[0][0] : spans[0][1]] == "Key Inclusion Criteria:\n\n"
    assert spans[-1][1] == len(REAL) and REAL[spans[-1][0] : spans[-1][1]].strip() == REAL[pieces[-1][2] :]
    assert text_coverage("a b", []) == ("uncovered_text", [(0, 3)], [])


def test_overlapping_pieces_are_never_covered():
    text = "* one\n* two"
    pieces = [("criterion", "unsectioned", 0, 7), ("criterion", "unsectioned", 6, 11)]
    assert text_coverage(text, pieces) == ("overlapping", [], [(6, 7)])
    whole = [("criterion", "unsectioned", 0, 11), ("criterion", "unsectioned", 6, 11)]
    assert text_coverage(text, whole) == ("overlapping", [], [(6, 11)])
    assert text_coverage(text, [("criterion", "unsectioned", 0, 5), ("criterion", "unsectioned", 6, 11)]) == (
        "covered",
        [],
        [],
    )


def test_overlaps_and_holes_are_reported_together():
    text = "* one\n* two\nstray words\n* three"
    first, second = (0, 7), (6, 11)
    third = (text.index("* three"), len(text))
    pieces = [("criterion", "unsectioned", *span) for span in (first, second, third)]
    code, holes, overlaps = text_coverage(text, pieces)
    assert code == "overlapping_and_uncovered"
    assert overlaps == [(6, 7)]
    assert [text[s:e].strip() for s, e in holes] == ["stray words"]
    later = "* one\nstray\n* two\n* three"
    two, three = later.index("* two"), later.index("* three")
    spans = [(0, 5), (two, three + 2), (three, len(later))]
    code, holes, overlaps = text_coverage(later, [("criterion", "unsectioned", *span) for span in spans])
    assert code == "overlapping_and_uncovered"
    assert [later[s:e].strip() for s, e in holes] == ["stray"] and overlaps == [(three, three + 2)]
    assert text_coverage(later, [("criterion", "unsectioned", 0, len(later))]) == ("covered", [], [])
