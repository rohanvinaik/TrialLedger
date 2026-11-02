"""landscape.xlsx — the clinical readout workbook, and the criterion role it shows beside each heading.

Built on records landscape.landscape_record makes from tests/test_landscape.py's studies (a study with posted
results in every module, an observational one, the near-miss pair, the audited trial), a trial whose headings
hold the wrong roles and the results study with its results removed.
Positive: a criterion's role is read from its own wording against its heading, an exclusion under an
inclusion heading caught with its words; every sheet comes in the design's order with its columns and grain
(one index row per trial, one dossier block per trial read top to bottom in the design's order, one
eligibility row per criterion with its heading and role apart, registered, anticipated and observed outcomes
apart, one biomarker row per mention, one safety row per event and group, one finding per profile row and
pair, one register row per displayed value); a results publication tagged RESULT is shown beside "Registry
results: Not posted"; the index links each trial to its registry page and its first dossier row; frozen
panes, filters, widths, wrapped top-aligned Arial, numbers right-aligned with separators, landscape printing
with repeated headers, a footer and each trial's dossier on a new page; the same record writes the same bytes;
500 trials stay one index row each and one Trial review sheet, and a sheet past its capacity continues on
numbered sheets with the links following it.
Negative: an exclusion under an inclusion heading is never read as inclusion and an uncertain role is
unresolved, never guessed; no status is ever a blank, a dash, "N/A" or "None"; what landscape.json does not
carry (a short title, an assay, a specimen, a planning assumption, a denominator, a grade, a schedule) is "Not
stated" and the register says so; a grade is never filled and seriousness never stands in for it; an at-risk
count is never filled from a group total; a DERIVED reference is never a results publication; a proposal or an
interpolation is never established; no merged cell and no formula; a tampered cell, a file that is not the
workbook, and a write whose read-back differs are refused (the last leaving no file); readout.py and
criteria.py stay outside the derivation code root, so no warrant changes.
"""

import copy
import re
import zipfile
from pathlib import Path

import pytest
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from production_path import near_miss_study
from records import results_study
from test_landscape import record_for

from TrialLedger import readout, warrants
from TrialLedger.criteria import criterion_role, itemize
from TrialLedger.landscape import standard_values
from TrialLedger.readout import (
    arm_entries,
    arm_treatments,
    atom_cells,
    biomarker_entries,
    biomarker_facts,
    class_cell,
    coordinate_cell,
    coverage_cell,
    criteria_entries,
    date_text,
    dated,
    dispersion_text,
    document_cell,
    efficacy_entries,
    eligibility_rows,
    enrolled,
    exploratory_entries,
    finding_rows,
    fitted,
    footer_parts,
    frequency_finding,
    held_cell,
    identification_entries,
    index_row,
    joined,
    language_entries,
    listing_rows,
    mechanism_finding,
    modality_cell,
    numbered_criteria,
    observed_facts,
    outcome_entries,
    outcome_rows,
    pair_finding,
    place,
    plain,
    population_entries,
    publication_cell,
    publication_note,
    quoted,
    read_list_cell,
    read_me_rows,
    readout_plan,
    readout_problems,
    register_rows,
    result_publications,
    review_rows,
    role_cell,
    safety_entries,
    safety_facts,
    scalar_text,
    search_words,
    shown,
    statement_type,
    tier_cell,
    trials_stating,
    write_readout,
)

P = "protocolSection"


def criteria_of(study):
    """A study's criteria as itemize gives them: (section, text)."""
    text = study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    return [(section, text[s:e]) for kind, section, s, e in itemize(text)[1] if kind == "criterion"]


# ── the criterion's role ──────────────────────────────────────────────────────────────────────────────


def test_the_records_own_criteria_take_their_headings_role():
    assert [criterion_role(text, section) for section, text in criteria_of(results_study())] == [
        ("inclusion", ()),
        ("inclusion", ()),
        ("exclusion", ()),
        ("exclusion", ()),
    ]
    # a negative in words that are not role words stays under its heading
    first = criteria_of(near_miss_study("NCT09000001", "0-1"))
    assert first[1] == ("inclusion", "* No prior systemic therapy for advanced or metastatic disease")
    assert [criterion_role(text, section)[0] for section, text in first] == [
        "inclusion",
        "inclusion",
        "inclusion",
        "exclusion",
    ]


@pytest.mark.parametrize(
    "text, words",
    [
        ("* Patients with brain metastases are excluded", ("are excluded",)),
        ("* Patients are EXCLUDED IF pregnant", ("are EXCLUDED",)),
        ("* Excluded if pregnant", ("Excluded if",)),
        ("* Patients with HIV will be excluded", ("will be excluded",)),
        ("* A smoker is excluded", ("is excluded",)),
        ("* Prior transplant: not eligible", ("not eligible",)),
        ("* Prior transplant: will not be eligible", ("not be eligible",)),
        ("* Pregnant women are ineligible", ("ineligible",)),
        ("* Patients who must not stop steroids are ineligible", ("must not", "ineligible")),
        ("* Prior therapy is permitted; active HBV is excluded", ("is permitted", "is excluded")),
    ],
)
def test_an_exclusion_under_an_inclusion_heading_is_caught_with_its_words(text, words):
    assert criterion_role(text, "inclusion") == ("exclusion", words)
    assert criterion_role(text, "exclusion") == ("exclusion", words)
    assert criterion_role(text, "unsectioned") == ("exclusion", words)


@pytest.mark.parametrize(
    "text, words",
    [
        ("* Must not be pregnant", ("Must not",)),
        ("* No history of interstitial lung disease", ("No history of",)),
        ("* no  history  of HIV; must not smoke", ("no  history  of", "must not")),
    ],
)
def test_a_negative_requirement_is_exclusion_only_under_the_exclusion_heading(text, words):
    assert criterion_role(text, "exclusion") == ("exclusion", words)
    assert criterion_role(text, "inclusion") == ("unresolved", words)
    assert criterion_role(text, "unsectioned") == ("unresolved", words)


@pytest.mark.parametrize(
    "text, words",
    [
        ("* Prior anti-PD-1 therapy is permitted", ("is permitted",)),
        ("* Treated brain metastases are allowed", ("are allowed",)),
        ("* Bisphosphonates will be permitted", ("will be permitted",)),
        ("* Steroids may be allowed", ("be allowed",)),
    ],
)
def test_a_permission_is_never_an_exclusion(text, words):
    assert criterion_role(text, "inclusion") == ("inclusion", words)
    assert criterion_role(text, "exclusion") == ("unresolved", words)
    assert criterion_role(text, "unsectioned") == ("unresolved", words)


@pytest.mark.parametrize(
    "text",
    [
        "* Adults with example disease",
        "* Mustnot be pregnant",  # no word boundary: not the words "must not"
        "* Patients are excludedd",
        "* eligibility confirmed",
        "* nonexcluded sites",
        "",
    ],
)
def test_without_role_words_the_heading_decides_and_no_heading_is_unresolved(text):
    assert criterion_role(text, "inclusion") == ("inclusion", ())
    assert criterion_role(text, "exclusion") == ("exclusion", ())
    assert criterion_role(text, "unsectioned") == ("unresolved", ())


# ── fixtures: records built by landscape.landscape_record from test_landscape's studies ──────────────


@pytest.fixture(scope="module")
def record():
    """The test population's record: a study with results in every module, an observational study, the
    near-miss pair and the audited trial."""
    return record_for()


def mixed_study():
    """A near-miss trial whose inclusion heading holds an exclusion and a negative requirement, whose
    exclusion heading holds a permission, and whose criteria name a biomarker."""
    study = near_miss_study("NCT09000007", "0-1")
    study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = (
        "Inclusion Criteria:\n\n* Stage IV non-small cell lung cancer\n"
        "* Patients with brain metastases are excluded\n* Must not be pregnant\n"
        "* EGFR mutation positive\n\n"
        "Exclusion Criteria:\n\n* Prior anti-PD-1 therapy is permitted\n* Active autoimmune disease\n"
    )
    study["protocolSection"]["designModule"]["phases"] = ["PHASE2", "PHASE3"]
    return study


def unposted_study():
    """The results study with its results section removed and its flag false: no results posted, its
    RESULT-typed publication still in the record."""
    study = results_study()
    del study["resultsSection"]
    study["hasResults"] = False
    return study


@pytest.fixture(scope="module")
def small():
    """A record of the mixed trial and the unposted results trial."""
    return record_for([mixed_study(), unposted_study()])


def env(value, status, source="src", rule="", note=""):
    return {"value": value, "status": status, "source": source, "rule": rule, "note": note, "link": ""}


ELIGIBILITY = "protocolSection.eligibilityModule.eligibilityCriteria"
CARRIED = "landscape.json (schema 1) carries no such field"


def absent(field):
    return ("Not stated", "", "absent_from_record", field, "", CARRIED)


def words(rows, column):
    return [row[column][0] for row in rows]


# ── one value as a cell ───────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value, text",
    [
        (None, "Not stated"),
        (True, "Yes"),
        (False, "No"),
        (["a", 1], '["a", 1]'),
        ({"k": 1}, '{"k": 1}'),
        (7, "7"),
    ],
)
def test_one_item_is_its_text_and_none_is_not_stated(value, text):
    assert scalar_text(value) == text


@pytest.mark.parametrize(
    "value, shown_value",
    [
        ("Example Pharma", "Example Pharma"),
        (120, 120),
        (10**16, "10000000000000000"),
        (True, "Yes"),
        (["PHASE2", "PHASE3"], "PHASE2\nPHASE3"),
        ([True, None], "Yes\nNot stated"),
        ({"date": "2018-01", "type": "ACTUAL"}, "date: 2018-01\ntype: ACTUAL"),
        ("", "Not stated"),
        ("  \n", "Not stated"),
        ([], "Not stated"),
        ({}, "Not stated"),
        (None, "Not stated"),
    ],
)
def test_a_known_value_reads_plainly_and_nothing_in_it_is_never_a_blank(value, shown_value):
    assert plain(value) == shown_value


@pytest.mark.parametrize(
    "status, value, note, text, shown_status",
    [
        ("known", "ALL", "", "ALL", "known"),
        ("known", [], "", "Not stated", "known"),
        ("not_stated", None, "not_reported", "Not stated", "not_stated"),
        ("not_stated", None, "not_applicable", "Not applicable", "not_stated"),
        ("not_stated", None, "redacted", readout.REDACTED, "not_stated"),
        ("not_posted", "no results posted", "", "Not posted", "not_posted"),
        ("proposed", ["adjuvant"], "why", "Proposed — adjuvant", "proposed"),
        ("interpolated", "antibody", "", "Interpolated — antibody", "interpolated"),
        ("unresolved", None, "lookup_failed", "Unresolved — lookup failed", "unresolved"),
        ("unresolved", None, "", "Unresolved — the rules cannot settle it from the record", "unresolved"),
        ("likely", "x", "n", "Unresolved — status 'likely' is not one landscape.json defines", "unresolved"),
    ],
)
def test_every_status_is_written_in_words_in_the_cell(status, value, note, text, shown_status):
    assert shown(env(value, status, "a.b", "r", note)) == (text, "", shown_status, "a.b", "r", note)


@pytest.mark.parametrize(
    "kind, status, statement",
    [
        ("record", "known", "Record says"),
        ("record", "not_stated", "Record says"),
        ("record", "not_posted", "Record says"),
        ("reading", "known", "Establishes"),
        ("reading", "not_stated", "Record says"),
        ("reading", "unresolved", "Unresolved"),
        ("record", "unresolved", "Unresolved"),
        ("reading", "proposed", "Unresolved"),
        ("reading", "interpolated", "Unresolved"),
    ],
)
def test_establishes_is_only_a_known_reading_and_a_proposal_is_never_established(kind, status, statement):
    assert statement_type(kind, status) == statement


@pytest.mark.parametrize(
    "text, written",
    [
        ("2026-11-01", "01-Nov-2026"),
        ("2019-12", "Dec-2019"),
        ("2019-01-07", "07-Jan-2019"),
        ("2025", "2025"),
        ("2020-05-01T09:08", "01-May-2020 09:08"),
        ("2026-10-30 09:00:03", "30-Oct-2026 09:00:03"),
        ("2019-13", "2019-13"),
        ("2019-00-01", "2019-00-01"),
        ("Spring 2019", "Spring 2019"),
        (None, "Not stated"),
        (20190101, "Not stated"),
    ],
)
def test_dates_keep_their_precision_and_anything_else_is_as_written(text, written):
    assert date_text(text) == written


def test_a_date_and_an_enrollment_name_their_type():
    assert dated(env({"date": "2019-06-30", "type": "ACTUAL"}, "known"))[0] == "30-Jun-2019 (actual)"
    assert dated(env({"date": "2027-12", "type": "ESTIMATED"}, "known"))[0] == "Dec-2027 (anticipated)"
    assert dated(env({"date": "2027", "type": "OTHER"}, "known"))[0] == "2027 (type OTHER)"
    assert dated(env({"date": "2027"}, "known"))[0] == "2027"
    assert dated(env(None, "not_stated", note="not_reported"))[0] == "Not stated"
    assert dated(env("2027", "known"))[0] == "2027"
    assert enrolled(env({"count": 1200, "type": "ACTUAL"}, "known"))[0] == "1,200 (actual)"
    assert enrolled(env({"count": 500, "type": "ESTIMATED"}, "known"))[0] == "500 (anticipated)"
    assert enrolled(env({"count": 5, "type": "X"}, "known"))[0] == "5 (type X)"
    assert enrolled(env({"type": "ACTUAL"}, "known"))[0] == "Not stated (actual)"
    assert enrolled(env({"count": True}, "known"))[0] == "Not stated"
    assert enrolled(env({"count": 7}, "known")) == ("7", "", "known", "src", "", "")
    assert enrolled(env(None, "not_stated", note="redacted"))[0] == readout.REDACTED


# ── a criterion's role and a coordinate ───────────────────────────────────────────────────────────────


def test_quoted_words_are_each_in_quotation_marks():
    assert quoted(("must not", "ineligible")) == "“must not”, “ineligible”"
    assert quoted(()) == ""


@pytest.mark.parametrize(
    "text, heading, shown_role, status",
    [
        ("* Adults", "inclusion", "Inclusion", "known"),
        ("* Pregnancy", "exclusion", "Exclusion", "known"),
        (
            "* Patients with brain metastases are excluded",
            "inclusion",
            "Exclusion — its own words: “are excluded”; written under the Inclusion heading",
            "known",
        ),
        ("* Pregnant women are ineligible", "exclusion", "Exclusion — its own words: “ineligible”", "known"),
        ("* Prior therapy is permitted", "inclusion", "Inclusion — its own words: “is permitted”", "known"),
        (
            "* Must not be pregnant",
            "inclusion",
            "Unresolved — its own words “Must not” conflict with the Inclusion heading",
            "unresolved",
        ),
        ("* Adults", "unsectioned", "Unresolved — under no inclusion or exclusion heading", "unresolved"),
        (
            "* Must not be pregnant",
            "unsectioned",
            "Unresolved — under no inclusion or exclusion heading; its own words: “Must not”",
            "unresolved",
        ),
        (
            "* Pregnant women are ineligible",
            "unsectioned",
            "Exclusion — its own words: “ineligible”; under no inclusion or exclusion heading",
            "known",
        ),
    ],
)
def test_the_role_is_shown_beside_the_heading_with_the_words_it_was_read_from(
    text, heading, shown_role, status
):
    held = role_cell(text, heading)
    assert (held[0], held[2], held[3], held[4]) == (
        shown_role,
        status,
        ELIGIBILITY,
        "criteria.criterion_role",
    )


def test_a_coordinate_reads_its_one_value_or_says_what_remains():
    known = env(["advanced_first_line"], "known", "s", "r", "resolved")
    assert coordinate_cell(known) == ("advanced_first_line", "", "known", "s", "r", "resolved")
    assert coordinate_cell(env([], "known"))[0] == "Not stated"
    proposed = env(["adjuvant", "perioperative"], "proposed", "s", "r", "unresolved; x removed by y")
    assert coordinate_cell(proposed)[0] == "Proposed — adjuvant | perioperative; unresolved; x removed by y"
    several = env(["0", "1"], "unresolved", "s", "r", "unnarrowed")
    assert coordinate_cell(several)[:3] == (
        "Unresolved — 2 values remain: 0 | 1; unnarrowed",
        "",
        "unresolved",
    )
    conflict = env([], "unresolved", "s", "r", "conflict")
    assert coordinate_cell(conflict)[0] == "Unresolved — no value remains (a conflict); conflict"
    assert coordinate_cell(env(None, "not_stated", note="not_reported"))[0] == "Not stated"
    assert coordinate_cell(env("x", "known"))[0] == "x"


def test_criteria_are_numbered_in_the_texts_order_whatever_their_heading(small):
    numbered = numbered_criteria(small["studies"][0])
    assert [(n, piece, heading, text["value"]) for n, piece, heading, text, _ in numbered] == [
        (1, 1, "inclusion", "* Stage IV non-small cell lung cancer"),
        (2, 2, "inclusion", "* Patients with brain metastases are excluded"),
        (3, 3, "inclusion", "* Must not be pregnant"),
        (4, 4, "inclusion", "* EGFR mutation positive"),
        (5, 6, "exclusion", "* Prior anti-PD-1 therapy is permitted"),
        (6, 7, "exclusion", "* Active autoimmune disease"),
    ]
    assert numbered_criteria(small["studies"][1])[2][2] == "exclusion"


# ── the cells several sheets share ────────────────────────────────────────────────────────────────────


def test_joined_cells_keep_the_least_settled_status():
    known = ("a", "", "known", "", "", "")
    absent_one = absent("x")
    assert joined(("A", "B"), (known, absent_one), "s", "r") == (
        "A: a\nB: Not stated",
        "",
        "known",
        "s",
        "r",
        "",
    )
    assert joined(("A",), (absent_one,), "s", "r")[2] == "not_stated"
    assert (
        joined(("A", "B"), (known, ("Not posted", "", "not_posted", "", "", "")), "s", "r")[2] == "not_posted"
    )
    for status in ("unresolved", "proposed", "interpolated"):
        held = ("x", "", status, "", "", "")
        assert joined(("A", "B", "C"), (known, ("Not posted", "", "not_posted", "", "", ""), held), "", "")[
            2
        ] == ("unresolved")
    with pytest.raises(ValueError):
        joined(("A",), (known, known), "", "")


def test_an_object_the_record_holds_is_shown_field_by_field(record):
    arm = record["studies"][0]["arms"][1]
    assert held_cell(arm, readout.ARM_FIELDS) == (
        "Label: Placebo\nType: PLACEBO_COMPARATOR\nDescription: Not stated\nInterventions: Drug: Placebo",
        "",
        "known",
        "protocolSection.armsInterventionsModule.armGroups[1]",
        "",
        "",
    )
    entry = record["studies"][0]["interventions"][0]["entry"]
    assert held_cell(entry, readout.INTERVENTION_FIELDS)[0] == (
        "Type: DRUG\nName: Testamab\nOther names: TM-1\nDescription: Intravenous infusion\nArms: Testamab"
    )
    blank = env({"label": " ", "interventionNames": []}, "known")
    assert held_cell(blank, readout.ARM_FIELDS)[0] == (
        "Label: Not stated\nType: Not stated\nDescription: Not stated\nInterventions: Not stated"
    )
    assert held_cell(env(None, "not_stated", note="not_reported"), readout.ARM_FIELDS)[0] == "Not stated"


def test_a_drug_class_names_its_source_and_an_unclassed_drug_is_unresolved(record):
    audited = record["studies"][4]["interventions"]
    assert class_cell(audited[0]["drug_class"])[:3] == (
        "Class its own entry states: stated: PD-1",
        "",
        "known",
    )
    assert class_cell(audited[1]["drug_class"])[0] == (
        "FDA established pharmacologic class (NLM RxClass): Programmed Death Receptor-1 Blocking Antibody"
    )
    assert class_cell(record["studies"][0]["interventions"][0]["drug_class"])[:3] == (
        "Unresolved — lookup failed",
        "",
        "unresolved",
    )
    assert class_cell(env({"state": "classified", "classes": []}, "known"))[0] == (
        "FDA established pharmacologic class (NLM RxClass): Not stated"
    )


def test_a_modality_read_from_a_name_stem_is_interpolated_never_established(record):
    stem = record["studies"][0]["interventions"][0]["modality"][0]
    assert modality_cell(stem)[:3] == (
        "Interpolated — modality: antibody (asserted; intervention entry)",
        "",
        "interpolated",
    )
    stated = record["studies"][4]["interventions"][0]["modality"][0]
    assert modality_cell(stated)[:3] == ("modality: antibody (asserted; intervention entry)", "", "known")
    assert modality_cell(env(None, "unresolved", note="x"))[0] == "Unresolved — x"


def test_the_eligibility_text_says_how_it_was_read_and_names_its_markers(record):
    assert coverage_cell(record["studies"][2]["eligibility"]) == (
        "Criteria: itemized; headings: sectioned; inclusion list: unspecified; exclusion list: abbreviation "
        "stated\n“Key Exclusion” says the exclusion list is abbreviated",
        "",
        "known",
        ELIGIBILITY,
        "criteria.eligibility_coverage",
        "",
    )
    assert coverage_cell({"itemized": env("x", "known"), "coverage": env(None, "unresolved", note="y")})[
        0
    ] == ("Unresolved — y")


def test_a_rule_that_reads_nothing_is_unresolved_never_an_empty_answer():
    assert read_list_cell(env(["2 year"], "known", "s", "r"), "none") == ("2 year", "", "known", "s", "r", "")
    assert read_list_cell(env([], "known", "s", "r"), "none read") == (
        "Unresolved — none read",
        "",
        "unresolved",
        "s",
        "r",
        "",
    )
    assert read_list_cell(env(None, "not_stated", note="not_reported"), "x")[0] == "Not stated"


def test_a_standard_tier_is_known_only_when_the_profile_settles_it():
    met = {"element": "e", "tier": "met", "statement_rate": 0.95, "lower_bound": 0.9, "upper_bound": 1.0}
    assert tier_cell(env(met, "known", "s", "r")) == (
        "e: standard tier met (statement rate 0.95; full-criteria interval 0.9 to 1.0)",
        "",
        "known",
        "s",
        "r",
        "",
    )
    straddles = {**met, "tier": "unresolved"}
    assert tier_cell(env(straddles, "unresolved", note="unresolved"))[:3] == (
        "Unresolved — e: unresolved (statement rate 0.95; full-criteria interval 0.9 to 1.0)",
        "",
        "unresolved",
    )
    untyped = env(None, "unresolved", note="no bank typed this criterion: no element to measure")
    assert tier_cell(untyped)[0] == "Unresolved — no bank typed this criterion: no element to measure"
    assert tier_cell(env(met, "proposed"))[0] == "Proposed — " + plain(met)


def test_publications_and_documents_carry_their_links(record):
    first = record["studies"][0]
    assert publication_cell(first["publications"][0]) == (
        "Author A. Results paper. J Ex. 2020.\nPMID: 31589554\nRole: reports results from this study, as the "
        "responsible party marked it",
        "https://pubmed.ncbi.nlm.nih.gov/31589554/",
        "known",
        "protocolSection.referencesModule.references[0]",
        "links.reference_role",
        "",
    )
    assert publication_cell(first["publications"][2])[0].splitlines()[1] == "PMID: Not stated"
    assert publication_cell(first["publications"][2])[1] == ""
    assert document_cell(first["documents"][0]) == (
        "Type: Prot_SAP\nLabel: Study Protocol and Statistical Analysis Plan\nProtocol: Yes\nStatistical "
        "analysis plan: Yes\nConsent form: No\nFile: Prot_SAP_000.pdf\nDate: 07-Jan-2019\nUploaded: "
        "01-May-2020 09:08",
        "https://cdn.clinicaltrials.gov/large-docs/67/NCT01234567/Prot_SAP_000.pdf",
        "known",
        "documentSection.largeDocumentModule.largeDocs[0]",
        "links.document_link",
        "",
    )
    assert document_cell(env({"url": ""}, "known"))[1] == ""
    assert publication_cell(env(None, "not_stated", note="not_reported"))[0] == "Not stated"
    assert document_cell(env(None, "not_stated", note="not_reported"))[0] == "Not stated"


def test_only_a_result_typed_reference_is_a_results_publication(record, small):
    found = result_publications(record["studies"][0])
    assert found == [
        (
            "PMID 31589554: Author A. Results paper. J Ex. 2020. — " + readout.RESULT_WORDS,
            "https://pubmed.ncbi.nlm.nih.gov/31589554/",
            "known",
            "protocolSection.referencesModule.references[0]",
            "links.reference_role",
            "",
        )
    ]
    # a DERIVED reference (the observational study's only one) is never a results publication
    assert result_publications(record["studies"][1]) == []
    assert publication_note(record["studies"][1]) == (
        "Not stated",
        "",
        "not_stated",
        "protocolSection.referencesModule.references",
        "links.reference_role",
        "no reference of type RESULT",
    )
    note = publication_note(small["studies"][1])
    assert note[0] == "Results publication (registry type RESULT): " + found[0][0]
    assert note[1:3] == ("https://pubmed.ncbi.nlm.nih.gov/31589554/", "known")
    unlinked = {"publications": [env({"type": "RESULT", "citation": "C.", "pmid": None}, "known")]}
    assert result_publications(unlinked)[0][:2] == ("C. — " + readout.RESULT_WORDS, "")


# ── one trial's dossier, top to bottom ────────────────────────────────────────────────────────────────


def test_one_trials_dossier_reads_top_to_bottom_in_the_designs_order(record):
    rows = review_rows(record["studies"][0], record["review_queue"])
    sections = words(rows, 1)
    assert list(dict.fromkeys(sections)) == list(readout.SECTIONS)
    assert sections == sorted(sections, key=readout.SECTIONS.index), "each block whole, in order"
    assert words(rows, 0) == ["NCT01234567"] * len(rows)
    assert words(rows, 5) == [f"NCT01234567-R{n:03d}" for n in range(1, len(rows) + 1)]
    assert [(row[2][0], row[3][0], row[4][0]) for row in rows[:10]] == [
        ("Trial ID", "Record says", "NCT01234567"),
        ("Registry page", "Record says", "ClinicalTrials.gov record NCT01234567"),
        ("Lead sponsor", "Record says", "Example Pharma"),
        ("Phase", "Record says", "PHASE2"),
        ("Overall status", "Record says", "COMPLETED"),
        ("Study type", "Record says", "INTERVENTIONAL"),
        ("Start date", "Record says", "15-Jan-2018 (actual)"),
        ("Primary completion date", "Record says", "30-Jun-2019 (actual)"),
        ("Completion date", "Record says", "Dec-2019 (actual)"),
        ("Enrollment (actual or anticipated)", "Record says", "120 (actual)"),
    ]
    assert rows[1][4][1] == "https://clinicaltrials.gov/study/NCT01234567"
    items = words(rows, 2)
    # the eligible population, then separately the enrolled population
    assert items.index("Conditions") < items.index("Enrolled population: actual enrollment")
    assert items[items.index("Enrolled population: actual enrollment") + 1] == (
        "Enrolled population: posted baseline characteristics"
    )
    # planning (not carried), then the results and their publication, then the observed results
    efficacy = [(row[2][0], row[4][0]) for row in rows if row[1][0] == "7 Efficacy"]
    assert [item for item, _ in efficacy] == [
        "Planning assumptions and anticipated thresholds",
        "Registry results",
        "Results publication (registry type RESULT)",
        "Observed result 1: Objective response rate — Testamab",
        "Observed result 2: Objective response rate — Placebo",
    ]
    assert efficacy[0][1] == "Not stated" and efficacy[1][1] == "results posted"
    assert efficacy[3][1].splitlines()[3] == "Value: 21"
    # no grade is ever shown but as not stated, and seriousness never stands in for it
    safety = [row[4][0] for row in rows if row[1][0] == "8 Safety"]
    assert all("Grade as reported: Not stated" in text for text in safety[2:])
    assert safety[8].splitlines()[1:5:3] == ["Event category: Serious", "Grade as reported: Not stated"]
    question = [row for row in rows if row[2][0].startswith("Open question")]
    assert [(row[2][0], row[3][0]) for row in question] == [
        ("Open question 1: drug_class_unresolved", "Unresolved")
    ]
    assert question[0][4][0].startswith(
        "Unresolved — What is the pharmacologic class (mechanism) of Testamab?"
    )


def test_identification_and_population_are_the_records_own_values(record):
    audited = record["studies"][4]
    assert identification_entries(audited)[2:4] == [
        (
            "Lead sponsor",
            "record",
            (
                "Not stated",
                "",
                "not_stated",
                f"{P}.sponsorCollaboratorsModule.leadSponsor.name",
                "",
                "not_reported",
            ),
        ),
        (
            "Phase",
            "record",
            ("Not applicable", "", "not_stated", f"{P}.designModule.phases", "", "not_applicable"),
        ),
    ]
    unlinked = {**audited, "link": ""}
    assert identification_entries(unlinked)[1][2] == (
        "Not stated",
        "",
        "not_stated",
        "studies[].link",
        "links.study_link",
        "not an NCT number",
    )
    first = population_entries(record["studies"][0])
    assert [(item, kind, held[0]) for item, kind, held in first][-6:] == [
        ("Treatment setting (approved relations)", "reading", first[-6][2][0]),
        ("Treatment setting with proposed relations", "reading", first[-5][2][0]),
        (
            "Prior lines for advanced disease (approved relations)",
            "reading",
            "Unresolved — 4 values remain: 0 | 1 | 2 | 3+; unnarrowed",
        ),
        (
            "Prior lines for advanced disease with proposed relations",
            "reading",
            "Unresolved — 4 values remain: 0 | 1 | 2 | 3+; no proposed relation narrows it",
        ),
        ("Enrolled population: actual enrollment", "record", "120 (actual)"),
        ("Enrolled population: posted baseline characteristics", "record", "Not stated"),
    ]
    assert first[-1][2] == absent("Posted baseline characteristics")
    pair = population_entries(record["studies"][2])
    assert [held[0] for _, _, held in pair[8:11]] == ["advanced_first_line", "advanced_first_line", "0"]
    assert pair[-2:] == [
        (
            "Enrolled population: actual enrollment",
            "record",
            (
                "Not stated — the registered enrollment is not actual",
                "",
                "not_stated",
                f"{P}.designModule.enrollmentInfo",
                "",
                "",
            ),
        ),
        (
            "Enrolled population: posted baseline characteristics",
            "record",
            ("Not posted", "", "not_posted", "hasResults", "ledger.results_state", ""),
        ),
    ]


def test_arms_and_interventions_with_classes_where_read(record):
    audited = arm_entries(record["studies"][4])
    assert [(item, kind, held[0].splitlines()[0]) for item, kind, held in audited] == [
        ("Arm 1", "record", "Label: A"),
        ("Intervention 1", "record", "Type: DRUG"),
        ("Intervention 1 drug class", "reading", "Class its own entry states: stated: PD-1"),
        ("Intervention 1 modality 1", "reading", "modality: antibody (asserted; intervention entry)"),
        ("Intervention 2", "record", "Type: DRUG"),
        (
            "Intervention 2 drug class",
            "reading",
            (
                "FDA established pharmacologic class (NLM RxClass): Programmed Death Receptor-1 Blocking "
                "Antibody"
            ),
        ),
    ]
    # an intervention that is not an experimental drug has no class row
    assert [item for item, _, _ in arm_entries(record["studies"][0])] == [
        "Arm 1",
        "Arm 2",
        "Intervention 1",
        "Intervention 1 drug class",
        "Intervention 1 modality 1",
        "Intervention 2",
    ]
    assert arm_entries(record["studies"][1]) == [
        (
            "Arms",
            "record",
            ("Not stated", "", "not_stated", f"{P}.armsInterventionsModule.armGroups", "", ""),
        ),
        (
            "Interventions",
            "record",
            ("Not stated", "", "not_stated", f"{P}.armsInterventionsModule.interventions", "", ""),
        ),
    ]


def test_criteria_come_inclusion_then_exclusion_then_unresolved_with_heading_and_role_apart(small, record):
    entries = criteria_entries(small["studies"][0])
    assert [(item, kind, held[0]) for item, kind, held in entries[1:]] == [
        ("Criterion 1 (heading: Inclusion)", "record", "* Stage IV non-small cell lung cancer"),
        ("Criterion 4 (heading: Inclusion)", "record", "* EGFR mutation positive"),
        ("Criterion 2 (heading: Inclusion)", "record", "* Patients with brain metastases are excluded"),
        (
            "Criterion 2 role",
            "reading",
            "Exclusion — its own words: “are excluded”; written under the Inclusion heading",
        ),
        ("Criterion 6 (heading: Exclusion)", "record", "* Active autoimmune disease"),
        ("Criterion 3 (heading: Inclusion)", "record", "* Must not be pregnant"),
        (
            "Criterion 3 role",
            "reading",
            "Unresolved — its own words “Must not” conflict with the Inclusion heading",
        ),
        ("Criterion 5 (heading: Exclusion)", "record", "* Prior anti-PD-1 therapy is permitted"),
        (
            "Criterion 5 role",
            "reading",
            "Unresolved — its own words “is permitted” conflict with the Exclusion heading",
        ),
    ]
    assert entries[0][:2] == ("Eligibility text, as read", "reading")
    prose = criteria_entries(record["studies"][1])
    assert [(item, held[0]) for item, _, held in prose] == [
        (
            "Eligibility text, as read",
            (
                "Criteria: no list markers; headings: unsectioned; inclusion list: unspecified; exclusion "
                "list: unspecified"
            ),
        ),
        ("Eligibility text (no criterion itemized)", "Adults with example disease seen at the clinic."),
    ]


def test_outcomes_keep_their_registered_time_frames_and_a_time_frame_is_never_a_schedule(record):
    audited = outcome_entries(record["studies"][4])
    assert [(item, kind, held[0]) for item, kind, held in audited] == [
        ("Primary outcome 1: measure", "record", "Duration of response"),
        ("Primary outcome 1: registered time frame", "record", "Up to 24 weeks post-treatment"),
        ("Primary outcome 1: description", "record", "Not stated"),
        ("Primary outcome 1: endpoint class read", "reading", "duration_of_response"),
        ("Primary outcome 1: time points read", "reading", "24 week"),
        ("Secondary outcome 1: measure", "record", "Pain response"),
        ("Secondary outcome 1: registered time frame", "record", "At 12 weeks post-treatment"),
        ("Secondary outcome 1: description", "record", "Not stated"),
        ("Secondary outcome 1: endpoint class read", "reading", "Unresolved — " + readout.NO_CLASS),
        ("Secondary outcome 1: time points read", "reading", "12 week"),
        ("Explicit assessment schedule", "record", "Not stated"),
    ]
    assert audited[-1][2] == absent("Explicit assessment schedule")
    assert [item for item, _, _ in outcome_entries(record["studies"][1])] == [
        "Registered outcomes",
        "Explicit assessment schedule",
    ]


def test_biomarkers_efficacy_safety_and_exploratory_blocks(record, small):
    assert biomarker_entries(record["studies"][1]) == [
        (
            "Biomarkers",
            "record",
            ("Not stated", "", "not_stated", ELIGIBILITY, readout.BIOMARKER_RULES, readout.NO_BIOMARKER),
        )
    ]
    [(item, kind, held)] = biomarker_entries(small["studies"][0])
    assert (item, kind, held[2]) == ("Biomarker 1: EGFR", "reading", "known")
    assert held[0].splitlines() == [
        "Biomarker: EGFR",
        "Role: Eligibility",
        "Population: inclusion: positive",
        "Assay: Not stated",
        "Specimen: Not stated",
        "Threshold: Not stated",
        "Timing: Not stated",
        "Words read from: “EGFR” (criterion piece 4)",
    ]
    unposted = efficacy_entries(small["studies"][1])
    assert [(item, held[0]) for item, _, held in unposted] == [
        ("Planning assumptions and anticipated thresholds", "Not stated"),
        ("Registry results", "Not posted"),
        (
            "Results publication (registry type RESULT)",
            "PMID 31589554: Author A. Results paper. J Ex. 2020. — " + readout.RESULT_WORDS,
        ),
    ]
    assert efficacy_entries(record["studies"][1])[2] == (
        "Results publication (registry type RESULT)",
        "record",
        publication_note(record["studies"][1]),
    )
    assert [(item, held[0]) for item, _, held in safety_entries(small["studies"][1])] == [
        ("Reporting period", "Not stated"),
        ("Registry results", "Not posted"),
    ]
    posted = safety_entries(record["studies"][0])
    assert [item for item, _, _ in posted][2:4] == [
        "Safety row 1: Deaths (all causes), All-cause mortality, group total — Testamab",
        "Safety row 2: Serious, Any serious adverse event, group total — Testamab",
    ]
    assert exploratory_entries(record["studies"][0]) == [
        (
            "Exploratory 1 (registry category: other pre-specified)",
            "record",
            (
                "Measure: Biomarker X level\nRegistered time frame: Baseline, Week 12",
                "",
                "known",
                f"{P}.outcomesModule.otherOutcomes[0].measure",
                "",
                "",
            ),
        )
    ]
    assert exploratory_entries(record["studies"][1])[0][2][0] == "Not stated"


def test_protocol_language_publications_documents_and_open_questions(record):
    audited = language_entries(record["studies"][4], record["review_queue"])
    assert [(item, held[0]) for item, _, held in audited] == [
        (
            "Criterion 1: standard language",
            (
                "Unresolved — inclusion:ecog_ps=0|1: unresolved (statement rate 0.4; full-criteria interval "
                "0.4 to 1.0)"
            ),
        ),
        (
            "Criterion 2: standard language",
            "Unresolved — no bank typed this criterion: no element to measure",
        ),
        (
            "Publication 1 (registry type DERIVED)",
            (
                "Author D. Protocol. 2025.\nPMID: 35273311\nRole: added by the registry, not by the "
                "responsible party; its role is not stated"
            ),
        ),
        ("Protocol and statistical analysis plan", "Not posted"),
    ]
    none = language_entries({**record["studies"][4], "publications": []}, [])
    assert none[2] == (
        "Publications",
        "record",
        ("Not stated", "", "not_stated", f"{P}.referencesModule.references", "", ""),
    )
    asked = language_entries(record["studies"][2], record["review_queue"])
    assert asked[-1][0] == "Open question 1: eligibility_abbreviated"
    assert asked[-1][2][2:5] == ("unresolved", "review_queue", "review.flags_for")


# ── the listings ──────────────────────────────────────────────────────────────────────────────────────


def test_the_index_is_one_row_per_trial_with_the_landscape_columns(record):
    first = index_row(record["studies"][0], ("Trial review", 2))
    assert len(first) == len(readout.INDEX_COLUMNS)
    assert [held[0] for held in first] == [
        "NCT01234567",
        "Not stated",
        "PHASE2",
        "COMPLETED",
        "Conditions: Example Disease\nAges: 18 Years to 65 Years\nSex: ALL\nHealthy volunteers: No",
        first[5][0],
        "Testamab (EXPERIMENTAL): Drug: Testamab",
        "Placebo (PLACEBO_COMPARATOR): Drug: Placebo",
        "120 (actual)",
        "1. Objective response rate",
        "1. Week 24",
        "results posted",
        "Results publication (registry type RESULT): PMID 31589554: Author A. Results paper. J Ex. 2020. — "
        + readout.RESULT_WORDS,
        "Not stated",
        "Trial review, row 2",
        "NCT01234567-I",
    ]
    assert first[0][1] == "https://clinicaltrials.gov/study/NCT01234567"
    assert first[14][1] == "#'Trial review'!A2"
    assert first[1] == absent("Short title") and first[13] == absent("Last registry update")
    assert (
        first[5][0].splitlines()[1]
        == "Prior lines for advanced disease: Unresolved — 4 values remain: 0 | 1 | 2 | 3+; unnarrowed"
    )
    pair = index_row(record["studies"][2], ("Trial review 2", 9))
    assert [held[0] for held in pair[5:8]] == [
        "Setting: advanced_first_line\nPrior lines for advanced disease: 0",
        "A (EXPERIMENTAL): Drug: Placebo",
        "No comparator arm registered",
    ]
    assert pair[14][:2] == ("Trial review 2, row 9", "#'Trial review 2'!A9")
    observational = index_row(record["studies"][1], ("Trial review", 3))
    assert [held[0] for held in observational[6:12]] == [
        "Not stated",
        "Not stated",
        "500 (anticipated)",
        "Not stated",
        "Not stated",
        "Not posted",
    ]


def test_a_results_publication_is_shown_beside_registry_results_not_posted(small):
    row = index_row(small["studies"][1], ("Trial review", 2))
    assert row[11][0] == "Not posted"
    assert row[12][0].startswith("Results publication (registry type RESULT): PMID 31589554")
    assert row[12][1] == "https://pubmed.ncbi.nlm.nih.gov/31589554/"
    observed = [held for held in outcome_rows(small["studies"][1]) if held[4][0] == "Observed"]
    assert [(held[2][0], held[8][0], held[15][0]) for held in observed] == [
        ("Not posted", "Not posted", row[12][0])
    ]


def test_arm_treatments_read_the_arms_types():
    arms = [
        env({"label": "A", "type": "EXPERIMENTAL", "interventionNames": ["Drug: X"]}, "known"),
        env({"label": "B", "type": "ACTIVE_COMPARATOR"}, "known"),
        env(
            {"label": "C", "type": "SHAM_COMPARATOR", "interventionNames": ["Device: S", "Drug: T"]}, "known"
        ),
        env(None, "not_stated", note="not_reported"),
    ]
    assert arm_treatments(arms, readout.COMPARATORS, "none")[0] == (
        "B (ACTIVE_COMPARATOR): Not stated\nC (SHAM_COMPARATOR): Device: S; Drug: T"
    )
    assert arm_treatments(arms, ("PLACEBO_COMPARATOR",), "No such arm")[0] == "No such arm"
    assert arm_treatments([], readout.COMPARATORS, "none")[:3] == ("Not stated", "", "not_stated")


def test_eligibility_is_one_row_per_criterion_its_heading_and_role_apart(small, record):
    rows = eligibility_rows(small["studies"][0])
    assert len(rows) == 6 and all(len(row) == len(readout.ELIGIBILITY_COLUMNS) for row in rows)
    assert [(row[2][0], row[3][0], row[4][0]) for row in rows] == [
        ("Inclusion", "Inclusion", 1),
        ("Inclusion", "Exclusion — its own words: “are excluded”; written under the Inclusion heading", 2),
        ("Inclusion", "Unresolved — its own words “Must not” conflict with the Inclusion heading", 3),
        ("Inclusion", "Inclusion", 4),
        ("Exclusion", "Unresolved — its own words “is permitted” conflict with the Exclusion heading", 5),
        ("Exclusion", "Exclusion", 6),
    ]
    assert rows[0][1] == absent("Cohort or arm a criterion applies to")
    assert words(rows, 12) == [f"NCT09000007-E{n:03d}" for n in range(1, 7)]
    assert [row[4][5] for row in rows] == ["piece 1", "piece 2", "piece 3", "piece 4", "piece 6", "piece 7"]
    prose = eligibility_rows(record["studies"][1])
    assert [held[0] for held in prose[0]] == [
        "NCT07654321",
        "Not stated",
        "No heading",
        "Unresolved — the eligibility text holds no list of criteria",
        "Not stated",
        "Adults with example disease seen at the clinic.",
        "Unresolved — no rule typed this criterion",
        "Not stated",
        "Not stated",
        "Not stated",
        "Not stated",
        "Not stated",
        "NCT07654321-E001",
    ]


def test_a_typed_reading_names_its_parameter_operator_value_and_unit():
    atoms = [
        env(
            {
                "concept": "lab",
                "values": ["hemoglobin"],
                "params": {"comparator": "≥", "value": "9", "unit": "g/dL"},
                "section": "inclusion",
            },
            "known",
            "s",
            "banks.organ_function",
        ),
        env(
            {
                "concept": "age",
                "values": ["stated"],
                "params": {"minimum": "18", "maximum": "65"},
                "section": "inclusion",
            },
            "known",
            "s",
            "banks.age",
        ),
        env(
            {"concept": "age", "values": [], "params": {"minimum": "18"}, "section": "inclusion"},
            "known",
            "s",
            "banks.age",
        ),
        env(
            {
                "concept": "prior_agent",
                "values": ["PD-1"],
                "params": {"modality": "permitted", "maximum": "2"},
                "section": "permitted",
            },
            "known",
            "s",
            "banks.prior_therapy",
        ),
    ]
    cells = atom_cells(atoms)
    assert [held[0].splitlines() for held in cells] == [
        [
            "lab = hemoglobin (inclusion)",
            "age = stated (inclusion)",
            "age =  (inclusion)",
            "prior_agent = PD-1 (permitted)",
        ],
        ["lab: hemoglobin", "age: stated", "age: ", "prior_agent: PD-1"],
        ["≥", "Not stated", "Not stated", "Not stated"],
        ["9", "18 to 65", "18", "2"],
        ["g/dL", "Not stated", "Not stated", "Not stated"],
        ["Not stated", "Not stated", "Not stated", "modality permitted"],
    ]
    assert {held[4] for held in cells} == {"banks.organ_function; banks.age; banks.prior_therapy"}
    assert {held[2] for held in cells} == {"known"}
    untyped = atom_cells([])
    assert [held[:3] for held in untyped] == [
        ("Unresolved — no rule typed this criterion", "", "unresolved")
    ] + [("Not stated", "", "not_stated")] * 5


def test_outcomes_keep_registered_anticipated_and_observed_apart(record):
    rows = outcome_rows(record["studies"][0])
    assert [(row[1][0], row[2][0], row[4][0]) for row in rows] == [
        ("P1", "Primary", "Registered endpoint"),
        ("S1", "Secondary", "Registered endpoint"),
        ("O1", "Other", "Registered endpoint"),
        ("A1", "Not stated", "Anticipated"),
        ("R1", "Primary", "Observed"),
        ("R2", "Primary", "Observed"),
    ]
    assert all(len(row) == len(readout.OUTCOME_COLUMNS) for row in rows)
    assert [held[0] for held in rows[0][5:13]] == ["Not applicable — registered endpoint"] * 8
    assert [held[0] for held in rows[0][13:16]] == [
        "Week 24",
        "Not stated",
        "Description: Per RECIST 1.1\nEndpoint class read: objective_response_rate",
    ]
    assert [held[0] for held in rows[4][3:16]] == [
        "Objective response rate",
        "Observed",
        "Testamab",
        "Not stated",
        "COUNT_OF_PARTICIPANTS",
        "21",
        "Participants",
        "Not stated",
        "Not stated",
        "Not stated",
        "Week 24",
        "Not stated",
        "Not stated",
    ]
    assert rows[4][6] == absent("Analysis population") and rows[4][10] == absent("Denominator")
    assert rows[4][12] == absent("Statistical analysis") and rows[4][14] == absent(
        "Explicit assessment schedule"
    )
    assert words(rows, 16) == [f"NCT01234567-O{n:03d}" for n in range(1, 7)]


def test_observed_facts_name_their_group_dispersion_class_and_category():
    held = {
        "outcome_type": "POST_HOC",
        "measure": "m",
        "time_frame": None,
        "unit": "months",
        "param_type": "MEDIAN",
        "dispersion_type": "95% Confidence Interval",
        "arm": None,
        "group_id": "OG9",
        "class": "All",
        "category": None,
        "value": "12.1",
        "spread": None,
        "lower_limit": "10.0",
        "upper_limit": None,
    }
    facts = observed_facts(env(held, "known", "s", "r"))
    assert [fact[0] for fact in facts] == [
        "Post hoc",
        "Group OG9",
        "MEDIAN",
        "12.1",
        "months",
        "95% Confidence Interval: 10.0 to Not stated",
        "Not stated",
        "Not stated",
        "Not stated",
        "All",
    ]
    assert (
        dispersion_text({"dispersion_type": "STANDARD_DEVIATION", "spread": "9.2"})
        == "STANDARD_DEVIATION: 9.2"
    )
    assert dispersion_text({"dispersion_type": None, "upper_limit": "3"}) == "Not stated: Not stated to 3"
    assert dispersion_text({}) == "Not stated"
    other = observed_facts(env({**held, "outcome_type": "SURPRISE", "class": None, "arm": "Arm A"}, "known"))
    assert (other[0][0], other[1][0], other[9][0]) == ("SURPRISE", "Arm A", "Not stated")


def test_biomarkers_are_one_row_per_mention_and_assay_and_specimen_are_not_carried(small, record):
    [mention] = biomarker_facts(small["studies"][0])
    assert [held[0] for held in mention] == [
        "EGFR",
        "Eligibility",
        "inclusion: positive",
        "Not stated",
        "Not stated",
        "Not stated",
        "Not stated",
        "“EGFR” (criterion piece 4)",
    ]
    assert mention[3] == absent("Biomarker assay") and mention[6] == absent("Biomarker timing")
    rows = listing_rows(small["studies"][0], [mention], "B")
    assert words(rows, 0) == ["NCT09000007"] and words(rows, 9) == ["NCT09000007-B001"]
    [exploratory] = biomarker_facts(record["studies"][0])
    assert [held[0] for held in exploratory[:2]] + [exploratory[6][0]] == [
        "Biomarker X level",
        "Exploratory (an other pre-specified outcome)",
        "Baseline, Week 12",
    ]
    outcome = {
        "outcome_type": "primary",
        "measure": "ctDNA clearance",
        "time_frame": "8 weeks",
        "time_points": [],
    }
    roles = {"eligibility": [], "outcome": [env(outcome, "known", "s", "r")], "exploratory": []}
    [measured] = biomarker_facts({"biomarkers": roles})
    assert measured[1][:3] == (
        "Unresolved — measured by a primary outcome; the record does not say whether for response or safety",
        "",
        "unresolved",
    )
    threshold = env(
        {
            "biomarker": "PD-L1",
            "states": [],
            "params": {"expression": ">=50%"},
            "span": "PD-L1",
            "piece": 2,
            "section": "inclusion",
        },
        "known",
        "s",
        "r",
    )
    [read] = biomarker_facts({"biomarkers": {"eligibility": [threshold], "outcome": [], "exploratory": []}})
    assert (read[2][0], read[5][0]) == ("inclusion: states not stated", "expression >=50%")
    assert [held[0] for held in biomarker_facts(record["studies"][1])[0]] == ["Not stated"] * 8


def test_safety_is_one_row_per_event_and_group_and_a_grade_is_never_filled(record, small):
    facts = safety_facts(record["studies"][0])
    rows = listing_rows(record["studies"][0], facts, "S")
    assert all(len(row) == len(readout.SAFETY_COLUMNS) for row in rows)
    assert [(row[1][0], row[2][0], row[4][0], row[7][0], row[8][0], row[9][0]) for row in rows] == [
        ("Testamab", "Deaths (all causes)", "All-cause mortality, group total", 1, 60, "Not stated"),
        ("Testamab", "Serious", "Any serious adverse event, group total", 6, 60, "Not stated"),
        ("Testamab", "Other", "Any other adverse event, group total", 30, 60, "Not stated"),
        ("Placebo", "Deaths (all causes)", "All-cause mortality, group total", 0, 60, "Not stated"),
        ("Placebo", "Serious", "Any serious adverse event, group total", 2, 60, "Not stated"),
        ("Placebo", "Other", "Any other adverse event, group total", 20, 60, "Not stated"),
        ("Testamab", "Serious", "Pneumonitis", 3, 60, 4),
        ("Placebo", "Serious", "Pneumonitis", 0, 60, "Not stated"),
        ("Testamab", "Other", "Fatigue", 18, 60, 25),
        # an at-risk count the record does not state is never filled from its group's total
        ("Placebo", "Other", "Fatigue", 10, "Not stated", 12),
    ]
    assert {row[5] for row in rows} == {absent("Grade")} and {row[6] for row in rows} == {
        absent("Grade source")
    }
    assert [row[10][0] for row in rows[6:]] == [
        "SYSTEMATIC_ASSESSMENT",
        "SYSTEMATIC_ASSESSMENT",
        "Not stated",
        "Not stated",
    ]
    assert {row[11][0] for row in rows} == {"Up to 30 days after last dose"}
    assert rows[6][12][0] == "Vocabulary: MedDRA 21.0"
    [unposted] = safety_facts(small["studies"][1])
    assert [held[0] for held in unposted[:11]] == ["Not posted"] * 11
    assert unposted[11] == publication_note(small["studies"][1])
    empty = {**record["studies"][0], "safety": {**record["studies"][0]["safety"], "groups": [], "events": []}}
    [none] = safety_facts(empty)
    assert [held[0] for held in none] == ["Not stated"] * 10 + ["Up to 30 days after last dose", "Not stated"]
    unnamed = env({"arm": None, "group_id": "EG9", "table": "other"}, "known")
    assert (
        safety_facts({"safety": {**record["studies"][0]["safety"], "groups": [], "events": [unnamed]}})[0][0][
            0
        ]
        == "Group EG9"
    )


# ── across trials ─────────────────────────────────────────────────────────────────────────────────────


def test_each_cohort_element_names_its_trials_from_their_own_readings(record):
    stating = trials_stating(record)
    assert stating["inclusion:ecog_ps=0|1"] == ["NCT09000001", "NCT09000004"]
    assert stating["primary:endpoint:objective_response_rate"] == ["NCT01234567"]
    for row in record["cohort"]["frequency"]:
        if row["stratum"] == "all trials":
            assert len(stating[row["element"]]) == row["stating"], row["element"]


def test_findings_carry_their_numbers_and_a_pair_says_similarity_is_not_comparability(record):
    rows = finding_rows(record)
    assert all(len(row) == len(readout.FINDING_COLUMNS) for row in rows)
    assert words(rows, 0) == [f"F{n:03d}" for n in range(1, len(rows) + 1)] == words(rows, 8)
    first = [held[0] for held in rows[0][1:8]]
    assert first == [
        "Common criterion (all trials)",
        "exclusion:condition=autoimmune_disease",
        (
            "Unresolved — Stated by 2 of 5 trials (statement rate 0.4; full-criteria interval 0.4 to 1.0); "
            "standard tier unresolved"
        ),
        "NCT09000001\nNCT09000002",
        "2 / 2 / 5",
        "Absent in 0; unresolved in 3 (empty 0, no rule match 1, abbreviated 0, unspecified 2)",
        "profile.frequency_rows; estimand statement rate and full-criteria interval; sponsors 1",
    ]
    assert rows[0][3][2] == "unresolved"
    pair = rows[-1]
    assert [held[0] for held in pair[1:8]] == [
        "Trial pair (as written)",
        "ecog_ps",
        (
            "NCT09000001: 0|1; NCT09000002: 0|1|2; 1 other predicates agree. Registry similarity, not "
            "clinical comparability: they may differ in what is not represented"
        ),
        "NCT09000001\nNCT09000002",
        "2 trials compared",
        "Sponsors: Not stated / Not stated; start years 2025 / 2025",
        "nearmiss.near_misses",
    ]
    empty = {
        **record,
        "cohort": {"frequency": [], "mechanism_signals": [], "near_misses": [], "aligned_near_misses": []},
    }
    assert [held[0] for held in finding_rows(empty)[0]] == ["F001"] + ["Not stated"] * 7 + ["F001"]


def test_a_statement_rate_alone_and_a_setting_stratum_name_no_trials():
    row = {
        "stratum": "advanced_first_line",
        "element": "primary:endpoint:x",
        "stating": 1,
        "absent": None,
        "unresolved_empty": None,
        "unresolved_no_rule_match": None,
        "unresolved_abbreviated": None,
        "unresolved_unspecified": None,
        "unresolved": None,
        "trials": 3,
        "statement_rate": 0.3333,
        "lower_bound": None,
        "upper_bound": None,
        "sponsors": 1,
        "standard_tier": "",
        "estimand": "statement rate only",
    }
    assert frequency_finding(row, {"primary:endpoint:x": ["NCT1"]}) == (
        "Common criterion (advanced_first_line)",
        "primary:endpoint:x",
        "Stated by 1 of 3 trials (statement rate 0.3333); no standard tier (a statement rate only)",
        "known",
        "",
        "1 / Not stated / 3",
        "Not stated: a statement rate only, no silence is counted",
        "profile.frequency_rows; estimand statement rate only; sponsors 1",
    )
    met = {
        **row,
        "stratum": "all trials",
        "standard_tier": "met",
        "absent": 1,
        "lower_bound": 0.9,
        "upper_bound": 1.0,
    }
    found = frequency_finding(met, {"primary:endpoint:x": ["NCT1", "NCT2"]})
    assert found[2:6] == (
        (
            "Stated by 1 of 3 trials (statement rate 0.3333; full-criteria interval 0.9 to 1.0); standard "
            "tier met"
        ),
        "known",
        "NCT1\nNCT2",
        "1 / 2 / 3",
    )


def test_a_mechanism_comparison_is_proposed_or_unresolved_never_established():
    row = {
        "stratum": "all trials",
        "class": "PD-1 Blocker",
        "element": "exclusion:condition=autoimmune_disease",
        "in_class_stating": 5,
        "in_class": 6,
        "others_stating": 1,
        "others": 10,
        "rate_in_class": 0.83,
        "rate_in_others": 0.1,
        "difference": 0.73,
        "least_favourable_difference": 0.5,
        "sponsors": 3,
        "unresolved_class_trials": 0,
        "abbreviated_in_class": 1,
        "abbreviated_in_others": 2,
        "status": "proposed",
    }
    found = mechanism_finding(row)
    assert found == (
        "Mechanism-linked exclusion",
        "PD-1 Blocker: exclusion:condition=autoimmune_disease (all trials)",
        (
            "Proposed — Stated by 5 of 6 trials in the class and 1 of 10 others; difference 0.73 (least "
            "favourable 0.5)"
        ),
        "proposed",
        "",
        "5 / 6 / 16",
        "Unresolved class trials 0; abbreviated in the class 1, in others 2",
        "profile.mechanism_rows; sponsors 3",
    )
    below = mechanism_finding({**row, "status": "below_support", "others": None})
    assert below[2].startswith("Unresolved — below_support: Stated by 5 of 6") and below[3] == "unresolved"
    assert below[5] == "5 / 6 / Not stated"


def test_an_aligned_pair_names_its_bases():
    row = {
        "a": "NCT11",
        "b": "NCT12",
        "difference": "ecog_ps",
        "value_a": "0|1",
        "value_b": "0|1|2",
        "sponsor_a": "S",
        "sponsor_b": "",
        "start_year_a": "2025",
        "start_year_b": "",
        "predicates_agreeing": 0,
        "basis_a": "rxclass",
        "basis_b": "crosswalk",
    }
    found = pair_finding(row, "aligned by ATC class")
    assert found[0] == "Trial pair (aligned by ATC class)"
    assert found[6:] == (
        "Sponsors: S / Not stated; start years 2025 / Not stated",
        "nearmiss.near_misses; bases rxclass, crosswalk",
    )


# ── the Read me, the register and the plan ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "request_, scope, search",
    [
        ({"drug": ["Placebo"]}, {"queries": []}, '{"drug": ["Placebo"]}'),
        (
            {"drug": ["X"]},
            {"query": {"query.cond": "lung", "filter.advanced": "AREA[Phase]PHASE3"}},
            "query.cond=lung; filter.advanced=AREA[Phase]PHASE3",
        ),
        ({}, {"query": "cond=lung"}, "cond=lung"),
        ({}, {"query": "  "}, "Not stated"),
        ({}, {"query": {}}, "Not stated"),
        (None, None, "Not stated"),
        ([], "x", "Not stated"),
        ("", {}, "Not stated"),
        ({"b": 1, "a": "é"}, [], '{"a": "é", "b": 1}'),
    ],
)
def test_the_search_as_run_is_the_scopes_query_or_the_request(request_, scope, search):
    assert search_words(request_, scope) == search


def test_the_read_me_names_the_search_the_surprises_and_what_each_status_means(record, small):
    rows = read_me_rows(record)
    topics = {row[0][0]: row[1][0] for row in rows}
    assert words(rows, 2) == [f"M{n:02d}" for n in range(1, len(rows) + 1)]
    assert topics["Search as run"] == '{"drug": ["Placebo"]}'
    assert (
        topics["Retrieval date"]
        == "30-Oct-2026 09:00:03 (the registry's data timestamp); ClinicalTrials.gov API 2.0.3"
    )
    assert topics["Trials"] == "5 trials, one row each in the Trial index"
    assert topics["Retrieval coverage"] == "matched: 5\nread: 5"
    assert topics["Scope surprise: combined phases"] == "No trial here registers more than one phase"
    assert topics["Scope surprise: outside the supported universe"].splitlines() == [
        f"{nct}: observational unsupported"
        for nct in ("NCT07654321", "NCT09000001", "NCT09000002", "NCT09000004")
    ]
    assert topics["Status: Not posted"] == "no results or document posted"
    assert topics["Status: Not carried"] == f"{CARRIED}; the cell says Not stated"
    assert "Status: TrialLedger's own label" not in topics
    assert (
        topics["Sheet: Trial review"]
        == "6 columns: Trial ID; Section; Item; Statement type; Statement or value; Evidence key"
    )
    assert (
        topics["Not carried by the record: Grade and grade source"]
        == f"an adverse event's grade — {CARRIED}; the cell says Not stated"
    )
    surprises = {row[0][0]: row[1][0] for row in read_me_rows(small)}
    assert surprises["Scope surprise: combined phases"] == "NCT09000007: PHASE2, PHASE3"
    assert surprises["Retrieval coverage"] == "matched: 5\nread: 5"
    bare = {**record, "manifest": {**record["manifest"], "retrieval": {}}, "coverage": {"studies": []}}
    bare_topics = {row[0][0]: row[1][0] for row in read_me_rows(bare)}
    assert bare_topics["Retrieval coverage"] == "Not stated"
    assert (
        bare_topics["Scope surprise: outside the supported universe"]
        == "Every trial here is inside the supported universe"
    )


def test_the_register_holds_one_row_per_displayed_value_with_its_source(record):
    rows = [index_row(record["studies"][0], ("Trial review", 2))]
    versions = ("2.0.3", "9.9", "30-Oct-2026")
    register = register_rows("Trial index", readout.INDEX_COLUMNS, rows, True, versions)
    entered = [header for header, _, entered in readout.INDEX_COLUMNS if entered]
    assert [row[4][0] for row in register] == entered
    assert all(len(row) == len(readout.REGISTER_COLUMNS) for row in register)
    assert [held[0] for held in register[0]] == [
        "NCT01234567-I/Trial ID",
        "NCT01234567",
        "Trial index",
        "NCT01234567-I",
        "Trial ID",
        "NCT01234567",
        readout.STATUS_WORDS["known"],
        "Rule",
        f"links.study_link (TrialLedger 9.9; {readout.VERSION})",
        "https://clinicaltrials.gov/study/NCT01234567",
        "Not stated",
        "30-Oct-2026",
    ]
    assert [held[0] for held in register[1][5:10]] == [
        "Not stated",
        readout.STATUS_WORDS["absent_from_record"],
        "Not carried by the record",
        "Short title (landscape.json schema 1)",
        "https://clinicaltrials.gov/study/NCT01234567",
    ]
    assert [held[0] for held in register[2][7:9]] == [
        "Registry field",
        f"{P}.designModule.phases (ClinicalTrials.gov API 2.0.3)",
    ]
    own = register_rows("Read me", readout.READ_ME_COLUMNS, [], False, versions)
    assert own == []
    findings = register_rows(
        "Across-trial findings", readout.FINDING_COLUMNS, finding_rows(record)[:1], False, versions
    )
    assert {row[1][0] for row in findings} == {"Cohort"} and {row[9][0] for row in findings} == {
        readout.ACROSS
    }
    label_only = [
        (("NCT1", "", "label", "", "", ""), ("x", "", "label", "", "", ""), ("K", "", "label", "", "", ""))
    ]
    columns = (("Trial ID", 1, False), ("Topic", 1, True), ("Key", 1, False))
    [mine] = register_rows("S", columns, label_only, True, versions)
    assert [held[0] for held in mine[6:10]] == [
        readout.STATUS_WORDS["label"],
        "TrialLedger's own words",
        f"TrialLedger 9.9; {readout.VERSION}",
        "Not stated",
    ]
    counted = [((7, "", "known", "a.b", "", "n"), ("K", "", "label", "", "", ""))]
    [count] = register_rows("S", (("N", 1, True), ("Key", 1, False)), counted, False, versions)
    assert count[5][0] == 7 and count[10][0] == "n"


def test_a_value_a_cell_cannot_hold_is_named_and_an_oversized_one_continues_on_numbered_rows():
    bell = ("a bell\x07", "", "known", "x.y", "", "")
    cr = ("one\rtwo", "", "known", "", "rule", "")
    key = ("K-1", "", "label", "", "", "")
    [row] = fitted([(bell, cr, key)])
    assert row == (
        (
            "Unresolved — not written: forbidden characters; it is in landscape.json at x.y",
            "",
            "unresolved",
            "x.y",
            "",
            "",
        ),
        (
            "Unresolved — not written: carriage return; it is in landscape.json at rule",
            "",
            "unresolved",
            "",
            "rule",
            "",
        ),
        key,
    )
    long = "a" * (readout.CHUNK * 3 + 5)
    shorter = "b" * 33000
    trial = ("NCT1", "", "label", "", "", "")
    out = fitted([(trial, (long, "", "known", "s", "", ""), (shorter, "", "known", "s", "", ""), key)])
    assert [len(row[1][0]) for row in out] == [readout.CHUNK] * 3 + [5]
    assert "".join(row[1][0] for row in out) == long
    assert [row[2][0] for row in out[3:]] == ["(continued in the rows above)"]
    assert "".join(row[2][0] for row in out[:3]) == shorter
    assert [row[3][0] for row in out] == ["K-1"] + [f"K-1 (continued {n})" for n in (2, 3, 4)]
    assert {row[0] for row in out} == {trial}
    assert fitted([(trial, (5, "", "known", "", "", ""), key)]) == [
        (trial, (5, "", "known", "", "", ""), key)
    ]
    assert fitted([]) == []


def test_a_row_is_placed_on_its_numbered_sheet():
    assert place(0, 10, "Trial review") == ("Trial review", 2)
    assert place(9, 10, "Trial review") == ("Trial review", 11)
    assert place(10, 10, "Trial review") == ("Trial review 2", 2)
    assert place(25, 10, "Trial review") == ("Trial review 3", 7)


def test_the_footer_names_the_search_the_sheet_the_page_and_the_retrieval_date():
    assert footer_parts("drug=X & Y", "30-Oct-2026") == (
        "Search: drug=X && Y",
        "&A, page &P of &N",
        "Retrieved 30-Oct-2026",
    )
    left, centre, right = footer_parts("x" * 300, "30-Oct-2026")
    assert left == "Search: see the Read me sheet"
    fits = "y" * (255 - len("&LSearch: &C&A, page &P of &N&RRetrieved 30-Oct-2026"))
    assert footer_parts(fits, "30-Oct-2026")[0] == "Search: " + fits
    assert footer_parts(fits + "y", "30-Oct-2026")[0] == "Search: see the Read me sheet"
    assert footer_parts("&", "a&b")[2] == "Retrieved a&&b"


def test_every_sheet_in_order_with_its_columns_and_grain(record):
    plan = readout_plan(record)
    assert (
        [name for name, *_ in plan]
        == list(readout.SHEET_NAMES)
        == [
            "Read me",
            "Trial index",
            "Trial review",
            "Eligibility",
            "Outcomes and efficacy",
            "Biomarkers",
            "Safety",
            "Across-trial findings",
            "Evidence register",
        ]
    )
    by_name = {name: (columns, rows, starts) for name, columns, rows, starts in plan}
    for name, (columns, rows, _) in by_name.items():
        assert rows and all(len(row) == len(columns) for row in rows), name
    ncts = [study["nct"]["value"] for study in record["studies"]]
    assert words(by_name["Trial index"][1], 0) == ncts
    review = by_name["Trial review"][1]
    assert list(dict.fromkeys(words(review, 0))) == ncts
    starts = [words(review, 0).index(nct) for nct in ncts]
    assert by_name["Trial review"][2] == starts[1:]
    assert [row[14][1] for row in by_name["Trial index"][1]] == [
        f"#'Trial review'!A{start + 2}" for start in starts
    ]
    assert len(by_name["Eligibility"][1]) == sum(max(1, len(numbered_criteria(s))) for s in record["studies"])
    entered = sum(
        sum(1 for _, _, flag in by_name[name][0] if flag) * len(by_name[name][1])
        for name, _ in readout.LISTINGS
    )
    assert len(by_name["Evidence register"][1]) == entered
    keys = [row[-1][0] for name, _ in readout.LISTINGS for row in by_name[name][1]]
    assert len(keys) == len(set(keys)), "every row key is stable and unique"


def sparse_record():
    """A record with what landscape.json can leave empty: an element not profiled, a reference with no type
    and a measurement with no title, group or class."""
    held = record_for([results_study()])
    study = held["studies"][0]
    study["standard_language"][0]["elements"] = standard_values(["inclusion:x"], {}, study["link"])
    study["publications"][2]["value"]["type"] = None
    measured = study["efficacy"]["measurements"][0]["value"]
    measured.update(measure=None, arm=None, group_id=None, outcome_type=None, unit=None)
    return held


NOTHING = re.compile(r"\bNone\b|\[\]|\{\}|\bnull\b")


def test_status_words_are_never_blank_a_dash_or_n_a(record, small):
    for held in (record, small, sparse_record()):
        for name, _, rows, _ in readout_plan(held):
            for row in rows:
                for value in row:
                    text = value[0]
                    if not isinstance(text, int):
                        assert text.strip() not in ("", "-", "—", "N/A", "none"), name
                        assert not NOTHING.search(text), (name, text)
                    assert value[2] in readout.STATUS_WORDS, (name, value)


def test_an_element_not_profiled_names_no_numbers():
    [value] = standard_values(["inclusion:x"], {}, "link")
    assert tier_cell(value)[0] == "Unresolved — inclusion:x: not profiled"
    rate_only = env({"element": "e", "tier": "met", "statement_rate": 0.5, "lower_bound": None}, "known")
    assert tier_cell(rate_only)[0] == "e: standard tier met (statement rate 0.5)"
    assert (
        tier_cell(env({"element": "e", "statement_rate": None}, "unresolved"))[0]
        == "Unresolved — e: unresolved"
    )


def test_text_beginning_with_an_equals_sign_is_written_as_text_never_a_formula(tmp_path):
    study = results_study()
    study["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"] = "=1+1"
    path = tmp_path / readout.NAME
    write_readout(record_for([study]), path)
    review = load_workbook(path)["Trial review"]
    [sponsor] = [row[4] for row in review.iter_rows(min_row=2) if row[2].value == "Lead sponsor"]
    assert (sponsor.value, sponsor.data_type) == ("=1+1", "s")


def five_hundred(record):
    """500 synthetic trials: the observational study's extract under 500 NCT numbers."""
    studies = []
    for n in range(500):
        study = copy.deepcopy(record["studies"][1])
        nct = f"NCT{20000000 + n:08d}"
        study["nct"]["value"], study["link"] = nct, f"https://clinicaltrials.gov/study/{nct}"
        studies.append(study)
    return {**record, "studies": studies, "review_queue": []}


def test_five_hundred_trials_stay_one_index_row_each_and_one_trial_review_sheet(record):
    plan = {name: rows for name, _, rows, _ in readout_plan(five_hundred(record))}
    assert len(plan["Trial index"]) == 500
    review = plan["Trial review"]
    assert place(len(review) - 1, readout.CAPACITY, "Trial review")[0] == "Trial review"
    assert {row[14][1].partition("!")[0] for row in plan["Trial index"]} == {"#'Trial review'"}
    assert len({row[0][0] for row in review}) == 500


# ── the file ──────────────────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def written(small, tmp_path_factory):
    path = tmp_path_factory.mktemp("readout") / readout.NAME
    return path, write_readout(small, path)


def test_the_file_holds_every_sheet_with_its_header_and_formatting(written, small):
    path, cells = written
    book = load_workbook(path)
    assert book.sheetnames == list(readout.SHEET_NAMES)
    plan = {name: (columns, rows) for name, columns, rows, _ in readout_plan(small)}
    assert cells == sum(len(columns) * (len(rows) + 1) for columns, rows in plan.values())
    freezes = {name: freeze for name, _, freeze, _ in readout.SHEETS}
    for sheet in book.worksheets:
        columns, rows = plan[sheet.title]
        last = get_column_letter(len(columns))
        assert [cell.value for cell in sheet[1]] == [header for header, *_ in columns]
        assert all(cell.font.bold and cell.font.name == "Arial" for cell in sheet[1])
        assert sheet.freeze_panes == freezes[sheet.title]
        assert sheet.auto_filter.ref == f"A1:{last}{len(rows) + 1}"
        assert sheet.print_title_rows == "$1:$1"
        assert sheet.print_area == f"'{sheet.title}'!$A$1:${last}${len(rows) + 1}"
        assert sheet.page_setup.orientation == "landscape"
        assert sheet.page_setup.fitToWidth is None and not sheet.sheet_properties.pageSetUpPr.fitToPage
        assert sheet.oddFooter.center.text == "&A, page &P of &N"
        assert sheet.oddFooter.left.text.startswith("Search: ")
        assert sheet.oddFooter.right.text == "Retrieved 30-Oct-2026 09:00:03"
        assert not sheet.merged_cells.ranges
        widths = [sheet.column_dimensions[get_column_letter(n)].width for n in range(1, len(columns) + 1)]
        assert widths == [width for _, width, _ in columns]
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                assert cell.data_type in ("s", "n"), (sheet.title, cell.coordinate)
                assert cell.font.name == "Arial" and cell.font.size == 10 and not cell.font.bold
                assert cell.alignment.vertical == "top"
                if cell.data_type == "s":
                    assert cell.alignment.wrap_text and cell.alignment.horizontal == "left"
                else:
                    assert cell.alignment.horizontal == "right" and cell.number_format == "#,##0"
    review = book["Trial review"]
    assert [brk.id for brk in review.row_breaks.brk] == [
        row - 1
        for row in range(2, review.max_row + 1)
        if review.cell(row, 1).value != review.cell(row - 1, 1).value and row > 2
    ]


def test_the_index_links_each_trial_to_its_registry_page_and_its_first_dossier_row(written):
    path, _ = written
    book = load_workbook(path)
    index, review = book["Trial index"], book["Trial review"]
    for row in range(2, index.max_row + 1):
        trial, dossier = index.cell(row, 1), index.cell(row, 15)
        assert trial.hyperlink.target == f"https://clinicaltrials.gov/study/{trial.value}"
        assert trial.hyperlink.ref == trial.coordinate and dossier.hyperlink.ref == dossier.coordinate
        assert dossier.hyperlink.target is None
        sheet, _, cell = dossier.hyperlink.location.partition("!")
        assert sheet == "'Trial review'"
        target = review[cell]
        assert target.value == trial.value and review.cell(target.row, 3).value == "Trial ID"
        assert review.cell(target.row - 1, 1).value != trial.value


def test_the_same_record_writes_the_same_bytes(written, small, tmp_path):
    path, _ = written
    again = tmp_path / "again.xlsx"
    write_readout(small, again)
    assert again.read_bytes() == path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        assert {info.date_time for info in archive.infolist()} == {readout.ZIP_TIME}
        assert b"dcterms:created" not in archive.read("docProps/core.xml")
        assert b"dcterms:modified" not in archive.read("docProps/core.xml")


def test_a_tampered_cell_is_refused(written, small, tmp_path):
    path, _ = written
    assert readout_problems(small, path) == []
    book = load_workbook(path)
    book["Safety"]["B2"] = "Testamab, edited"
    tampered = tmp_path / "tampered.xlsx"
    book.save(tampered)
    [problem] = readout_problems(small, tampered)
    assert problem.startswith("Safety row 2: expected ")
    retyped = load_workbook(path)
    retyped["Eligibility"]["E2"] = "1"
    retyped.save(tampered)
    assert readout_problems(small, tampered)[0].startswith("Eligibility row 2: expected ")
    (tmp_path / "broken.xlsx").write_bytes(b"not a workbook")
    assert readout_problems(small, tmp_path / "broken.xlsx")[0].startswith("readout.unreadable: broken.xlsx")


def test_a_write_whose_read_back_differs_is_refused_and_leaves_no_file(small, tmp_path, monkeypatch):
    original = readout._cell

    def altered(sheet, held, header, styles):
        if held[0] == "Testamab":
            held = ("Testamab, altered", *held[1:])
        return original(sheet, held, header, styles)

    monkeypatch.setattr(readout, "_cell", altered)
    path = tmp_path / readout.NAME
    with pytest.raises(readout.ReadoutError) as refused:
        write_readout(record_for([results_study()]), path)
    assert refused.value.code == "readout.readback_mismatch"
    assert not path.exists()


def test_a_sheet_past_its_capacity_continues_on_numbered_sheets(small, tmp_path, monkeypatch):
    monkeypatch.setattr(readout, "CAPACITY", 40)
    path = tmp_path / readout.NAME
    write_readout(small, path)
    book = load_workbook(path)
    assert "Trial review 2" in book.sheetnames and "Evidence register 2" in book.sheetnames
    assert book.sheetnames.index("Trial review 2") == book.sheetnames.index("Trial review") + 1
    index = book["Trial index"]
    second = index.cell(3, 15).hyperlink.location
    sheet, _, cell = second.partition("!")
    target = book[sheet.strip("'")][cell]
    assert target.value == index.cell(3, 1).value
    assert readout_problems(small, path) == []


def test_readout_and_criteria_are_outside_the_derivation_code_root():
    package = Path(readout.__file__).parent
    names = {path.name for path in warrants.derivation_files(package)}
    assert "readout.py" not in names and "criteria.py" not in names
