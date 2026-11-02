"""Eligibility text as criteria: sections and items with exact spans, so nothing is lost or rewritten.

The registry asks for "a bulleted list for each criterion below the headers 'Inclusion Criteria' and
'Exclusion Criteria'" (Protocol Registration Data Element Definitions, Eligibility Criteria). Records follow
it with variants, measured on the 487 interventional Phase 3 NSCLC trials started 2015-2024: headings with
"Key", "Main" or a cohort or phase qualifier, any case, an ASCII or full-width colon, a section number; items
marked "*", "-", "•", "1.", "1)", "1.1", "a." or "i)"; deeper-indented markers as sub-items. Every piece is a
span of the original text; the gaps between pieces are whitespace only, so the pieces and gaps in order
reproduce the text exactly.

`eligibility_coverage` gives the text's own attributes, kept apart (openspec/changes/add-scoped-reasoning,
Decision 12): whether there is any content, whether headings section it, and what it says about its own
coverage in each section (abbreviated, complete, or nothing said), each marker with its location and scope.
"""

from __future__ import annotations

import re

# A heading is a whole line: an optional section number, at most five words of qualifier, the word inclusion
# or exclusion, optionally "eligibility", then "criteria" or "criterion", at most six words of qualifier, and
# an optional colon. A line naming both kinds ("inclusion/exclusion criteria apply") is a note, not a heading,
# and so is a line ending in a full stop or carrying text after its colon.
_HEADING = re.compile(
    r"^\s*(?:\*\*)?\s*(?:\d+(?:\.\d+)*\s+)?"
    r"(?:[A-Za-z()]+\s+){0,5}?"
    r"(?P<non>non[- ]?)?(?P<kind>inclusion|exclusion)\s+(?:eligibility\s+)?criteri(?:a|on)"
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
            # "Non-inclusion criteria" (a French protocol's exclusions) are exclusion criteria.
            section = "exclusion" if heading.group("non") else heading.group("kind").lower()
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


# A record that says it lists only some criteria ("Key Exclusion Criteria", "other protocol-defined criteria
# may apply"): its silence says less than a complete record's. Moved here unchanged from expectations.py
# (where it was used only by `autoimmune_exclusion`), so that the observations it gates do not change.
# Provenance (`pattern:eligibility_abbreviated`): derived, the 487 NSCLC development trials. Measured there
# (2026-10-31) and left for the founder's decision: it misses "Other protocol-defined inclusion/exclusion
# criteria apply" (no modal verb), "Other protocol inclusion/exclusion criteria may apply" and "Other
# inclusion and exclusion criteria will apply per protocol", and it also matches "include, but are not limited
# to" inside a criterion's list of examples.
_ABBREVIATED = re.compile(
    r"\b(?:key|main|major|most important|selected)\s+(?:inclusion|exclusion|eligibility)\b"
    r"|other\s+(?:protocol[- ]?defined\s+)?(?:inclusion\s*/\s*exclusion\s+|inclusion\s+|exclusion\s+)?"
    r"criteria\s+(?:may|could|will|might)\s+apply"
    r"|further\s+(?:inclusion|exclusion)\s+criteria\s+apply|include,? but (?:are|is) not limited to",
    re.IGNORECASE,
)
# A record that says its list is the whole of its criteria. Provenance (`pattern:eligibility_complete`):
# prior (authored before measuring);
# it matches nothing in the 487 NSCLC development trials, so its tests are synthetic. Kept narrow on purpose:
# "see the protocol for the complete list" is an abbreviation, not a statement of completeness.
_COMPLETE = re.compile(
    r"\bno (?:other|additional|further) (?:inclusion |exclusion |eligibility )?criteria (?:apply|are used)\b"
    r"|\b(?:these|the above) are (?:all|the complete|the full|all of the) "
    r"(?:inclusion |exclusion |eligibility )?criteria\b",
    re.IGNORECASE,
)
# The words a marker's phrase names its scope with, read up to the word "criteria" when it follows closely.
_PHRASE = re.compile(r".{0,40}?criteri", re.IGNORECASE | re.DOTALL)
SCOPES = ("inclusion", "exclusion")


def eligibility_coverage(
    text: str, pieces: list[tuple[str, str, int, int]]
) -> tuple[str, str, tuple[tuple[str, str], ...], list[tuple[str, str, int, int, int]]]:
    """What a trial's eligibility text says about itself, as separate attributes (pure — pinned).

    `pieces` are `itemize(text)`'s. Returns (content, sectioning, evidence, markers):
      content     — "empty" (no text, or whitespace only) or "present";
      sectioning  — "sectioned" (a heading divides the text) or "unsectioned";
      evidence    — for each scope, ("inclusion", e) and ("exclusion", e), e one of
                    abbreviation_stated (a marker scoping it says the list is partial: "Key Exclusion
                    Criteria", "other protocol-defined criteria may apply"), completeness_stated (a marker
                    says the list is whole, and none says it is partial) or unspecified. No marker never
                    means complete;
      markers     — each (kind, scope, piece index, start, end), kind abbreviation_stated or
                    completeness_stated, start and end the marker's offsets in `text`, scope "inclusion",
                    "exclusion" or "both".
    A marker's scope is the kind its own phrase names ("Key Exclusion Criteria" → exclusion; "Other
    protocol defined Inclusion/Exclusion criteria may apply" → both), else the section of the piece it sits
    in ("Other protocol defined criteria could apply" under the inclusion heading → inclusion), else, in
    unsectioned text, both. Markers are read piece by piece, every piece (headings included), and listed in
    piece order, a piece's abbreviation markers before its completeness markers.
    """
    if not text.strip():
        return "empty", "unsectioned", tuple((scope, "unspecified") for scope in SCOPES), []
    sectioning = "sectioned" if any(kind == "heading" for kind, *_ in pieces) else "unsectioned"
    markers = []
    for index, (_kind, section, start, end) in enumerate(pieces):
        piece = text[start:end]
        found = [("abbreviation_stated", m) for m in _ABBREVIATED.finditer(piece)]
        found += [("completeness_stated", m) for m in _COMPLETE.finditer(piece)]
        for kind, match in found:
            phrase = _PHRASE.match(piece, match.start())
            words = (phrase.group(0) if phrase else match.group(0)).lower()
            named = [scope for scope in SCOPES if scope in words]
            if len(named) == 1:
                scope = named[0]
            elif named or section not in SCOPES:
                scope = "both"
            else:
                scope = section
            markers.append((kind, scope, index, start + match.start(), start + match.end()))
    evidence = []
    for scope in SCOPES:
        kinds = {kind for kind, marked, *_ in markers if marked in (scope, "both")}
        if "abbreviation_stated" in kinds:
            evidence.append((scope, "abbreviation_stated"))
        elif "completeness_stated" in kinds:
            evidence.append((scope, "completeness_stated"))
        else:
            evidence.append((scope, "unspecified"))
    return "present", sectioning, tuple(evidence), markers


# What "not eligible" or "ineligible" must refer to before it states that the criterion excludes: this study,
# trial or protocol, or the person's participation ("not eligible for this study", "ineligible for
# enrollment", "ineligible to participate"). Standing alone ("are ineligible", "will be ineligible",
# "considered ineligible by the investigator") it refers to the study by default. "Ineligible for" anything
# else ("for any available standard line of therapy", "for transplant", "for or refused standard therapy")
# describes the patient, and is no exclusion.
_STUDY_REFERENT = (
    r"(?=\s+(?:for|from)\s+(?:(?:this|the|a|any)\s+)?(?:clinical\s+)?"
    r"(?:study|trial|protocol|enrol?ment|enrollment|participation|entry|inclusion|randomi[sz]ation)\b"
    r"|\s+to\s+(?:participate|enrol|enroll|enter|take\s+part|be\s+enrolled|be\s+included)\b"
    r"|(?!\s+(?:for|to)\b))"
)
# A criterion's own words that state it excludes ("patients with brain metastases are excluded", "excluded
# if", "not eligible" and "ineligible" referring to the study); that state a requirement in the negative
# ("must not", "no history of"); and that state a permission ("is permitted", "are allowed"). Read
# case-insensitively, whole words, in the text's order, the first alternative that matches at each place.
_ROLE_WORDS = re.compile(
    r"\b(?:(?P<excludes>(?:is|are|will\s+be|be)\s+excluded|excluded\s+if"
    rf"|(?:not\s+(?:be\s+)?eligible|ineligible){_STUDY_REFERENT})"
    r"|(?P<negates>must\s+not|no\s+history\s+of)"
    r"|(?P<permits>(?:is|are|will\s+be|be)\s+(?:permitted|allowed)))\b",
    re.IGNORECASE,
)


def criterion_role(text: str, heading_section: str) -> tuple[str, tuple[str, ...]]:
    """A criterion's role read from its own wording against the heading it sits under (pure — pinned).

    `heading_section` is the criterion's section as `itemize` gives it ("inclusion", "exclusion" or
    "unsectioned"). Returns (role, words): role "inclusion", "exclusion" or "unresolved"; words every
    role word below the criterion holds, as written, in the text's order (empty when the heading alone was
    read):
      excluding words ("are excluded", "excluded if", and "not eligible" or "ineligible" standing alone or
                       for this study, trial, protocol, enrollment or participation) — exclusion, under any
                       heading: the criterion says it excludes, so one under an inclusion heading is caught;
                       "ineligible for" a therapy, transplant or surgery describes the patient, and is none;
      negating words ("must not", "no history of") — exclusion under an exclusion heading; unresolved under
                       an inclusion heading (a requirement stated in the negative, or an exclusion under the
                       wrong heading: the words conflict with it) or under none;
      permitting words ("is permitted", "are allowed") under an exclusion heading — unresolved (a permission
                       is no exclusion); under an inclusion heading — inclusion;
      no such words  — the heading's own section; unresolved under no heading.
    """
    found = [(match.lastgroup, match.group(0)) for match in _ROLE_WORDS.finditer(text)]
    kinds = {kind for kind, _ in found}
    words = tuple(word for _, word in found)
    if "excludes" in kinds:
        return "exclusion", words
    if "negates" in kinds:
        return ("exclusion" if heading_section == "exclusion" else "unresolved"), words
    if "permits" in kinds:
        return ("inclusion" if heading_section == "inclusion" else "unresolved"), words
    if heading_section in SCOPES:
        return heading_section, ()
    return "unresolved", ()
