"""Links to the sources a reviewer reads, in the forms verified live on 2026-10-31, and reference roles in
the registry's own terms."""

from __future__ import annotations

import re

# The registry's own CSV gives this as the "Study URL" of every study (2,529 of 2,529 rows, 2026-10-31).
STUDY_PAGE = "https://clinicaltrials.gov/study/{nct_id}"
PUBMED_PAGE = "https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
# Observed, not documented: every one of 155 posted documents in a 2,529-study sample returned
# application/pdf at this form (2026-10-31); tests/test_live.py keeps checking it.
DOCUMENT = "https://cdn.clinicaltrials.gov/large-docs/{suffix}/{nct_id}/{filename}"

_NCT_ID = re.compile(r"NCT[0-9]{8}")
_PMID = re.compile(r"[1-9][0-9]{0,8}")
_DOCUMENT_FILENAME = re.compile(r"[A-Za-z0-9_-]+\.pdf")

# What each reference type means, in the registry's terms (Protocol Registration Data Element Definitions,
# References: «Results Reference? Indicate if the reference provided reports on results from this clinical
# study. Select Yes/No»). DERIVED is not one of the responsible party's choices; its role is not stated.
REFERENCE_ROLES = {
    "RESULT": "reports results from this study, as the responsible party marked it",
    "BACKGROUND": "entered by the responsible party, not marked as reporting results",
    "DERIVED": "added by the registry, not by the responsible party; its role is not stated",
}


def study_link(nct_id: str | None) -> tuple[str, str]:
    """The registry page of a study (pure — pinned).

    ("ok", url) for a canonical NCT number; ("not_an_nct_id", "") otherwise.
    """
    if isinstance(nct_id, str) and _NCT_ID.fullmatch(nct_id):
        return "ok", STUDY_PAGE.format(nct_id=nct_id)
    return "not_an_nct_id", ""


def pubmed_link(pmid: str | None) -> tuple[str, str]:
    """The PubMed page of a reference (pure — pinned).

    ("ok", url) for a PMID that is a plain positive number; ("not_a_pmid", "") otherwise, including absent.
    """
    if isinstance(pmid, str) and _PMID.fullmatch(pmid):
        return "ok", PUBMED_PAGE.format(pmid=pmid)
    return "not_a_pmid", ""


def document_link(nct_id: str | None, filename: str | None) -> tuple[str, str]:
    """The registry's copy of a document the sponsor posted (pure — pinned).

    The folder is the last two digits of the NCT number.
      ("ok", url) for a canonical NCT number and a plain `.pdf` file name; ("not_linkable", "") otherwise.
    """
    if (
        isinstance(nct_id, str)
        and _NCT_ID.fullmatch(nct_id)
        and isinstance(filename, str)
        and _DOCUMENT_FILENAME.fullmatch(filename)
    ):
        return "ok", DOCUMENT.format(suffix=nct_id[-2:], nct_id=nct_id, filename=filename)
    return "not_linkable", ""


def reference_role(reference_type: str | None) -> str:
    """What a reference's type says of the publication, in the registry's terms only (pure — pinned).

    RESULT and BACKGROUND are the responsible party's statement; DERIVED is the registry's addition with no
    stated role, and is never described as a results publication.
    """
    if reference_type is None:
        return "type not reported"
    return REFERENCE_ROLES.get(reference_type, f"type {reference_type!r} is not one the registry defines")
