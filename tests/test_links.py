"""Links and reference roles — the verified link forms, and the registry's terms for a reference.

Positive: a canonical NCT number links to its registry page; a plain PMID to PubMed; a posted document to
the registry's copy, filed under the NCT number's last two digits; each reference type is described in the
registry's terms.
Negative: anything that is not a canonical identifier or a plain .pdf name gets no link; a DERIVED reference
is never described as reporting results; an unknown type is never mapped onto a known one.
"""

import pytest

from TrialLedger.links import document_link, pubmed_link, reference_role, study_link


def test_study_link():
    assert study_link("NCT01827384") == ("ok", "https://clinicaltrials.gov/study/NCT01827384")


@pytest.mark.parametrize("nct", ["nct01827384", "NCT1827384", "NCT018273840", " NCT01827384", None, 1827384])
def test_no_study_link_for_a_non_canonical_id(nct):
    assert study_link(nct) == ("not_an_nct_id", "")


def test_pubmed_link():
    assert pubmed_link("31589554") == ("ok", "https://pubmed.ncbi.nlm.nih.gov/31589554/")


@pytest.mark.parametrize("pmid", ["", "0", "0123", "123a", "12 34", None, 31589554, "1234567890"])
def test_no_pubmed_link_for_a_non_pmid(pmid):
    assert pubmed_link(pmid) == ("not_a_pmid", "")


def test_document_link():
    assert document_link("NCT01827384", "Prot_SAP_000.pdf") == (
        "ok",
        "https://cdn.clinicaltrials.gov/large-docs/84/NCT01827384/Prot_SAP_000.pdf",
    )
    assert document_link("NCT04204200", "ICF_001.pdf")[1] == (
        "https://cdn.clinicaltrials.gov/large-docs/00/NCT04204200/ICF_001.pdf"
    )


@pytest.mark.parametrize(
    "nct, filename",
    [
        ("NCT01827384", "../Prot_000.pdf"),
        ("NCT01827384", "a/b.pdf"),
        ("NCT01827384", "Prot_000.docx"),
        ("NCT01827384", ""),
        ("NCT01827384", None),
        ("nct01827384", "Prot_000.pdf"),
        (None, "Prot_000.pdf"),
    ],
)
def test_no_document_link_for_an_unsafe_or_unknown_name(nct, filename):
    assert document_link(nct, filename) == ("not_linkable", "")


def test_reference_roles_in_the_registrys_terms():
    assert reference_role("RESULT") == "reports results from this study, as the responsible party marked it"
    assert reference_role("BACKGROUND") == "entered by the responsible party, not marked as reporting results"
    assert (
        reference_role("DERIVED")
        == "added by the registry, not by the responsible party; its role is not stated"
    )
    assert reference_role(None) == "type not reported"
    assert reference_role("SECONDARY") == "type 'SECONDARY' is not one the registry defines"


def test_a_derived_reference_is_never_called_a_result():
    role = reference_role("DERIVED")
    assert "result" not in role.lower()
    assert "secondary" not in role.lower()
