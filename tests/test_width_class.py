"""How wide a workbook column is, and how a sheet prints: `workbook.width_class` and `workbook.print_fit`.

Positive: on the books' own column definitions, every NCT number, PMID, file and group id is an identifier
kept whole, and every warrant and record digest a warrant column wide enough for its 64 characters; every
description, brief summary, comment, criterion, citation, check detail and registry quotation is long text;
titles, measures, time frames, names, check ids, record locations and roles are summaries; each class's width
lies in the convention's range; a sheet at most READABLE_WIDTH wide is fitted to one page wide.
Negative: an enum, a date or a count is never given prose width; a link is never given prose width, whatever
its source mentions; a warrant is never cut to an identifier's width; a needs-review column is never a bare
category; a word inside a field's name, or in a parent field, never decides its class; a sheet one character
wider than readable is never scaled, it gets a print area.
"""

from TrialLedger import workbook
from TrialLedger.workbook import ABOUT_CLASSES, READABLE_WIDTH, SHEETS, WIDTHS, WRAPS, print_fit, width_class

CODES = {"I": "identifier", "C": "category", "S": "summary", "L": "long_text", "W": "warrant"}
# Each sheet's columns in order, one letter a column, as a clinical reader needs them laid out.
EXPECTED = {
    "Studies": "ISCCS" + "C" * 17 + "S" * 7 + "CS" + "C" * 11 + "SS" + "CCCC" + "W",
    "Eligibility": "ICCLCCCCSCLLLLLS",
    "Outcomes": "ICCSLSS",
    "Arms": "ISCLSS",
    "Interventions": "ICSSSLSS",
    "Sites": "ISCCCCCS",
    "Outcome Results": "ICCSLSLCCCSSSISSCCCCLSS",
    "Analyses": "ISSLCCCCCCCLSCCCLS",
    "Adverse Events": "ICCSSCCISCCCCLSS",
    "Event Groups": "IISLCCCCCCCSLLS",
    "Participant Flow": "ISCCISCLS",
    "Baseline": "ISCCSSSISCCCCS",
    "Publications": "IICSLSS",
    "Documents": "ICSCCCCCIS",
    "Checks": "ISCL",
    "Check Rules": "SSCCLW",
    "Record": "ISSSLS",
}


def classes(sheet):
    return [width_class(column.kind, column.source) for column in sheet.columns]


def test_every_column_of_every_sheet_has_its_class():
    assert set(EXPECTED) == {sheet.name for sheet in SHEETS}
    for sheet in SHEETS:
        assert len(EXPECTED[sheet.name]) == len(sheet.columns), sheet.name
        assert classes(sheet) == [CODES[letter] for letter in EXPECTED[sheet.name]], sheet.name


def test_identifiers_are_kept_whole():
    by_header = {(s.name, c.header): width_class(c.kind, c.source) for s in SHEETS for c in s.columns}
    for key in (
        ("Studies", "NCT Number"),
        ("Record", "NCT Number"),
        ("Publications", "PMID"),
        ("Documents", "File"),
        ("Event Groups", "Group ID"),
        ("Baseline", "Group ID"),
    ):
        assert by_header[key] == "identifier", key
    # An identifier fits its width, so wrapping never breaks one; a longer value in its column is not cut off.
    assert WRAPS["identifier"] and WIDTHS["identifier"] >= len("NCT01234567")


def test_a_warrant_is_shown_whole_on_one_line():
    by_header = {(s.name, c.header): width_class(c.kind, c.source) for s in SHEETS for c in s.columns}
    assert by_header[("Studies", "Record Digest")] == "warrant"
    assert by_header[("Check Rules", "Rule Warrant")] == "warrant"
    assert width_class("warrant", workbook.WARRANT_HEADER) == "warrant"
    assert width_class("warrant", "the record location of the outcome") == "warrant"
    assert not WRAPS["warrant"] and WIDTHS["warrant"] >= 64 + 2  # a SHA-256 digest, with the cell's margin


def test_prose_is_long_text_and_wrapped():
    by_header = {(s.name, c.header): width_class(c.kind, c.source) for s in SHEETS for c in s.columns}
    for key in (
        ("Eligibility", "Inclusion Criteria"),
        ("Eligibility", "Exclusion Criteria"),
        ("Eligibility", "Whole Text"),
        ("Eligibility", "Study Population"),
        ("Outcomes", "Description"),
        ("Analyses", "P-Value Comment"),
        ("Adverse Events", "Notes"),
        ("Publications", "Citation"),
        ("Checks", "Detail"),
        ("Check Rules", "The Registry's Words"),
        ("Record", "Value"),
    ):
        assert by_header[key] == "long_text", key
    assert WRAPS["long_text"] and WRAPS["summary"] and WRAPS["category"]


def test_summaries_by_their_names_and_words():
    assert width_class("stated", "protocolSection.identificationModule.briefTitle") == "summary"
    assert width_class("stated", "protocolSection.outcomesModule.<section>[].timeFrame") == "summary"
    assert (
        width_class("stated", "protocolSection.sponsorCollaboratorsModule.collaborators[]: name") == "summary"
    )
    assert width_class("computed", "group_title: outcomeMeasures[].groups[].title") == "summary"
    assert (
        width_class("computed", "registry_form over protocolSection.x.interventions[]: '<a>: <b>'")
        == "summary"
    )
    assert width_class("stated", "an approved edit check (Check Rules sheet)") == "summary"
    assert width_class("stated", "checks.CHECKS") == "summary"
    assert width_class("stated", "the record location of the outcome") == "summary"
    assert width_class("stated", "the role the record's structure gives the value") == "summary"
    assert width_class("needs review", "not a structured field of the record") == "summary"


def test_long_text_by_its_name_after_a_comma():
    source = "protocolSection.eligibilityModule.eligibilityCriteria, when not split"
    assert width_class("stated", source) == "long_text"
    assert (
        width_class("computed", "split_eligibility, part 2 of the exact text, from its heading")
        == "long_text"
    )


def test_each_width_lies_in_the_conventions_range():
    # The convention names no range for a warrant: it is a 64-character digest, kept whole on one line.
    ranges = {
        "identifier": (15, 18),
        "category": (14, 22),
        "summary": (35, 50),
        "long_text": (65, 85),
        "warrant": (66, 70),
    }
    assert set(WIDTHS) == set(WRAPS) == set(ranges)
    for code, (low, high) in ranges.items():
        assert low <= WIDTHS[code] <= high, code


def test_a_readable_sheet_fits_one_page_wide():
    assert print_fit(READABLE_WIDTH) == "fit_width"
    assert print_fit(0) == "fit_width"
    assert print_fit(sum(WIDTHS[code] for code in ABOUT_CLASSES)) == "fit_width"
    checks = next(sheet for sheet in SHEETS if sheet.name == "Checks")
    assert print_fit(sum(WIDTHS[code] for code in classes(checks))) == "fit_width"


def test_a_wider_sheet_is_never_scaled_but_given_a_print_area():
    assert print_fit(READABLE_WIDTH + 1) == "print_area"
    studies = next(sheet for sheet in SHEETS if sheet.name == "Studies")
    assert print_fit(sum(WIDTHS[code] for code in classes(studies))) == "print_area"
    checks = next(sheet for sheet in SHEETS if sheet.name == "Checks")
    assert print_fit(sum(WIDTHS[code] for code in classes(checks)) + WIDTHS["warrant"]) == "print_area"


def test_an_enum_a_date_or_a_count_is_never_prose():
    for source in (
        "protocolSection.statusModule.overallStatus",
        "protocolSection.statusModule.startDateStruct.date",
        "protocolSection.designModule.enrollmentInfo.count",
        "resultsSection.adverseEventsModule.eventGroups[].seriousNumAffected",
        "results_state; 'no results posted' when the registry's flag is false",
        "the section the outcome is registered in (primary, secondary, other outcomes)",
    ):
        assert width_class("stated", source) == "category", source


def test_a_link_is_never_given_prose_width_whatever_its_source_mentions():
    assert width_class("stated (link)", "references[].description; link: the exact text") == "identifier"


def test_a_warrant_is_never_cut_to_an_identifiers_width():
    assert width_class("warrant", "protocolSection.identificationModule.nctId") == "warrant"
    assert WIDTHS["warrant"] > WIDTHS["identifier"]


def test_a_needs_review_column_is_never_a_bare_category():
    assert width_class("needs review", "protocolSection.statusModule.overallStatus") == "summary"


def test_a_brief_summary_is_long_text():
    assert width_class("stated", "protocolSection.descriptionModule.briefSummary") == "long_text"


def test_a_word_inside_a_name_or_in_a_parent_never_decides():
    assert width_class("stated", "protocolSection.descriptionModule.summaryCount") == "category"
    assert width_class("stated", "outcomeMeasures[].titleCount") == "category"
    assert width_class("stated", "eventGroups[].description.idx") == "category"
    assert width_class("stated", "protocolSection.identificationModule.nctIdAlias") == "category"
