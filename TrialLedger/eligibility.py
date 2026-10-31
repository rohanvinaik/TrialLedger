"""Eligibility criteria, split only where the registry's stated headers make the split unambiguous."""

from __future__ import annotations

# P#EligibilityCriteria: «Use a bulleted list for each criterion below the headers "Inclusion Criteria" and
# "Exclusion Criteria".» A heading line is one of these, optionally followed by a colon.
INCLUSION_HEADINGS = ("Inclusion Criteria", "Inclusion Criteria:")
EXCLUSION_HEADINGS = ("Exclusion Criteria", "Exclusion Criteria:")


def split_eligibility(text: str) -> tuple[str, str, str, str]:
    """Split eligibility text at the registry's stated headers, or abstain (pure — pinned).

    A heading is a line (text between line feeds) holding only a stated header, apart from spaces and tabs.
    The text is split only when it has exactly one inclusion heading and one exclusion heading, inclusion
    first, into: the text before the inclusion heading; the inclusion part, from its heading; the exclusion
    part, from its heading. The three joined are the text, character for character.
      ("split", before, inclusion, exclusion)
      ("not_split_missing", "", "", "")  — a heading of either kind is absent.
      ("not_split_repeated", "", "", "") — a heading of either kind occurs more than once.
      ("not_split_order", "", "", "")    — the exclusion heading comes before the inclusion heading.
    """
    inclusion: list[int] = []
    exclusion: list[int] = []
    position = 0
    for line in text.split("\n"):
        content = line.strip(" \t")
        if content in INCLUSION_HEADINGS:
            inclusion.append(position)
        elif content in EXCLUSION_HEADINGS:
            exclusion.append(position)
        position += len(line) + 1
    if not inclusion or not exclusion:
        return "not_split_missing", "", "", ""
    if len(inclusion) > 1 or len(exclusion) > 1:
        return "not_split_repeated", "", "", ""
    start, end = inclusion[0], exclusion[0]
    if end < start:
        return "not_split_order", "", "", ""
    return "split", text[:start], text[start:end], text[end:]
