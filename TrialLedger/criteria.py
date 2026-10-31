"""Eligibility text as criteria: sections and items with exact spans, so nothing is lost or rewritten.

The registry asks for "a bulleted list for each criterion below the headers 'Inclusion Criteria' and
'Exclusion Criteria'" (Protocol Registration Data Element Definitions, Eligibility Criteria). Records follow
it with variants, measured on the 487 interventional Phase 3 NSCLC trials started 2015-2024: headings with
"Key", "Main" or a cohort or phase qualifier, any case, an ASCII or full-width colon, a section number; items
marked "*", "-", "•", "1.", "1)", "1.1", "a." or "i)"; deeper-indented markers as sub-items. Every piece is a
span of the original text; the gaps between pieces are whitespace only, so the pieces and gaps in order
reproduce the text exactly.
"""

from __future__ import annotations

import re

SECTIONS = ("inclusion", "exclusion", "unsectioned")

# A heading is a whole line: an optional section number, at most five words of qualifier, the word inclusion
# or exclusion, optionally "eligibility", then "criteria" or "criterion", at most six words of qualifier, and
# an optional colon. A line naming both kinds ("inclusion/exclusion criteria apply") is a note, not a heading,
# and so is a line ending in a full stop or carrying text after its colon.
_HEADING = re.compile(
    r"^\s*(?:\*\*)?\s*(?:\d+(?:\.\d+)*\s+)?"
    r"(?:[A-Za-z()]+\s+){0,5}?"
    r"(?P<kind>inclusion|exclusion)\s+(?:eligibility\s+)?criteri(?:a|on)"
    r"(?:\s+[A-Za-z0-9()]+){0,6}?"
    r"\s*[:：]?\s*(?:\*\*)?\s*$",
    re.IGNORECASE,
)
_BOTH = re.compile(r"inclusion\s*/\s*exclusion|exclusion\s*/\s*inclusion", re.IGNORECASE)
# A list marker at the start of a line, after any indentation.
_MARKER = re.compile(r"^(?P<indent>[ \t]*)(?:[*\-•]|\d+(?:\.\d+)*[.)]?|[a-z][.)]|[ivx]+[.)])[ \t]+\S")


def _lines(text: str) -> list[tuple[int, int]]:
    """Each line's (start, end) offsets, end excluding its newline."""
    spans, start = [], 0
    for line in text.split("\n"):
        spans.append((start, start + len(line)))
        start += len(line) + 1
    return spans


def _trimmed(text: str, start: int, end: int) -> tuple[int, int]:
    """The span with surrounding whitespace moved outside it."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def itemize(text: str) -> tuple[str, list[tuple[str, str, int, int]]]:
    """Divide eligibility text into headings, criteria and prose, each an exact span (pure — pinned).

    Returns (code, pieces), each piece (kind, section, start, end) with kind "heading", "criterion" or
    "prose" and section "inclusion", "exclusion" or "unsectioned" (the section of the latest heading above
    it). A criterion runs from its list marker to the next marker at its own indentation or shallower, the
    next heading, an unmarked line no deeper than its marker, or the end; deeper markers and deeper unmarked
    lines (continuations) stay inside it. Unmarked text outside a criterion is prose. Codes:
      itemized         — at least one criterion was found;
      no_list_markers  — there is text but no list marker: each section's text is one prose piece;
      empty            — the text is empty or whitespace only; no pieces.
    Pieces are in order and do not overlap; what lies between them is whitespace only.
    """
    if not text.strip():
        return "empty", []
    section = "unsectioned"
    spans: list[list] = []  # [kind, section, start, end] in order; the last one may still grow
    marker_depth = 0  # the indentation of the latest criterion's marker, a tab counting four columns
    for start, end in _lines(text):
        line = text[start:end]
        if not line.strip():
            continue
        depth = len(line[: len(line) - len(line.lstrip())].expandtabs(4))
        heading = _HEADING.match(line)
        if heading and not _BOTH.search(line):  # a section number ("1.0") is not a bullet
            section = heading.group("kind").lower()
            spans.append(["heading", section, start, end])
            continue
        last = spans[-1][0] if spans else None
        deeper = last == "criterion" and depth > marker_depth
        if _MARKER.match(line) and not deeper:
            spans.append(["criterion", section, start, end])
            marker_depth = depth
        elif deeper or last == "prose":
            spans[-1][3] = end
        else:
            spans.append(["prose", section, start, end])
    pieces = [(kind, sec, *_trimmed(text, start, end)) for kind, sec, start, end in spans]
    code = "itemized" if any(kind == "criterion" for kind, *_ in pieces) else "no_list_markers"
    return code, pieces
