"""The review and record workbooks — every value of the record, typed, warranted and certified.

Positive: each book's sheets and headers are those declared, its About sheet names the companion file, and
only the review book lists the ten questions; the Studies row links to the registry page and carries the
record's digest; eligibility splits only at the stated headings, into parts that join to the exact text;
absent fields read in the registry's terms; a study without results says so beside its publications; every
leaf of every study is on the record book's Record sheet under the registry's names; each book certifies
against its record, its file is the one this version writes, it is cell-identical when written twice, and
the writer counts the cells it wrote; a sheet past the row limit continues on a numbered sheet.
Negative: text is never a formula; text or a number a cell cannot hold is replaced by its reason and its
record location, never truncated, cleaned or rounded; a derived publication is never called a result;
proposed checks never run; an intervention without a type is never given one; a changed cell, a boolean in
place of a count, an unreadable file, a changed link and an added part are each named, and the writer
refuses what does not certify.
"""

import zipfile

import pytest
from openpyxl import load_workbook
from records import ELIGIBILITY, leaves, ongoing_study, results_study

from TrialLedger import warrants, workbook
from TrialLedger.checks import APPROVED, CHECKS
from TrialLedger.workbook import (
    BOOKS,
    RECORD,
    REVIEW,
    WARRANT_HEADER,
    WorkbookError,
    certify,
    file_problems,
    write_workbook,
)

LONG = "x" * 40000


def hazard_study():
    study = ongoing_study()
    study["protocolSection"]["identificationModule"]["nctId"] = "NCT00000009"
    study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"] = "bell\x07"
    study["protocolSection"]["eligibilityModule"]["studyPopulation"] = "a\r\nb"
    study["protocolSection"]["descriptionModule"] = {"briefSummary": LONG}
    return study


def record(*studies):
    return {
        "provenance": {"query": {"filter.ids": "x"}, "data_timestamp": "2026-10-30T09:00:04"},
        "studies": list(studies),
    }


@pytest.fixture
def written(tmp_path):
    data = record(results_study(), ongoing_study(), hazard_study())
    for book in BOOKS:
        write_workbook(data, tmp_path / book.name, book)
    return data, tmp_path / REVIEW.name


def record_book(path):
    return path.with_name(RECORD.name)


def rows(path, sheet):
    book = load_workbook(path, read_only=True)
    try:
        return [list(row) for row in book[sheet].iter_rows(values_only=True)]
    finally:
        book.close()


def by_header(path, sheet):
    header, *body = rows(path, sheet)
    return [dict(zip(header, row, strict=False)) for row in body]


def test_each_book_certifies_against_its_record(written):
    data, path = written
    assert certify(data, path) == []
    assert certify(data, record_book(path), book=RECORD) == []


def test_sheets_and_headers_are_the_declared_ones(written):
    _, path = written
    assert [sheet.name for sheet in RECORD.sheets] == ["Record"]
    assert "Record" not in [sheet.name for sheet in REVIEW.sheets]
    for book, file in ((REVIEW, path), (RECORD, record_book(path))):
        opened = load_workbook(file, read_only=True)
        assert opened.sheetnames == ["About", *(sheet.name for sheet in book.sheets)]
        opened.close()
        for sheet in book.sheets:
            expected = [c.header for c in sheet.columns] + ([WARRANT_HEADER] if sheet.warranted else [])
            assert rows(file, sheet.name)[0] == expected


def test_each_about_sheet_names_its_companion_and_only_review_lists_the_questions(written):
    _, path = written
    review, kept = rows(path, "About"), rows(record_book(path), "About")
    assert ["companion file", RECORD.name, RECORD.title, None] in review
    assert ["companion file", REVIEW.name, REVIEW.title, None] in kept
    assert any(row[0] == "the ten questions" for row in review)
    assert not any(row[0] == "the ten questions" for row in kept)
    assert review[0][0] == REVIEW.title and kept[0][0] == RECORD.title


def test_the_studies_row_links_and_carries_the_digest(written):
    data, path = written
    studies = by_header(path, "Studies")
    assert [s["NCT Number"] for s in studies] == ["NCT01234567", "NCT07654321", "NCT00000009"]
    assert studies[0]["Record Digest"] == warrants.study_digest(data["studies"][0])
    assert studies[0]["Results"] == "results posted"
    assert studies[1]["Results"] == "no results posted"
    assert studies[1]["Results Submitted, Not Yet Posted"] == "2026-09-01"
    assert studies[0]["Line of Therapy"].startswith("needs review")
    assert studies[0]["Interventions"] == "Drug: Testamab\nDrug: Placebo"
    assert studies[1]["Allocation"] == "not applicable to this study type"
    assert studies[1]["Maximum Age"] == "not reported"
    assert studies[0]["Approved Checks in Conflict"] == 0
    book = load_workbook(path)
    assert book["Studies"]["A2"].hyperlink.target == "https://clinicaltrials.gov/study/NCT01234567"
    book.close()


def test_eligibility_splits_only_at_the_stated_headings(written):
    _, path = written
    first, second, _ = by_header(path, "Eligibility")
    assert first["Split"] == "split"
    assert first["Before the Inclusion Heading"] is None  # nothing precedes the heading: a blank cell
    assert first["Inclusion Criteria"] + first["Exclusion Criteria"] == ELIGIBILITY
    assert second["Split"] == "not_split_missing"
    assert second["Whole Text"] == "Adults with example disease seen at the clinic."
    assert second["Line of Therapy"].startswith("needs review")


def test_text_is_never_a_formula(written):
    _, path = written
    book = load_workbook(record_book(path))
    sheet = book["Record"]
    cells = [
        row
        for row in sheet.iter_rows(min_col=5, max_col=5)
        if row[0].value == "=Testamab is compared with placebo."
    ]
    assert cells and cells[0][0].data_type == "s"
    book.close()


def test_text_a_cell_cannot_hold_is_replaced_by_its_reason(written):
    _, path = written
    record_values = {
        row["Location"]: row["Value"]
        for row in by_header(record_book(path), "Record")
        if row["NCT Number"] == "NCT00000009"
    }
    assert record_values["protocolSection.eligibilityModule.eligibilityCriteria"] == (
        "(not written: characters a spreadsheet file cannot hold; it is in studies.json: "
        "protocolSection.eligibilityModule.eligibilityCriteria of this row's study)"
    )
    assert record_values["protocolSection.eligibilityModule.studyPopulation"].startswith(
        "(not written: a carriage return"
    )
    assert record_values["protocolSection.descriptionModule.briefSummary"].startswith(
        "(not written: more characters"
    )
    assert all(not str(value).startswith("x" * 100) for value in record_values.values())


def test_every_leaf_is_on_the_record_sheet(written):
    data, path = written
    entries = by_header(record_book(path), "Record")
    for study in data["studies"]:
        nct = study["protocolSection"]["identificationModule"]["nctId"]
        mine = [e for e in entries if e["NCT Number"] == nct]
        assert len(mine) == len(leaves(study))
    stats = next(e for e in entries if e["Location"].endswith("seriousEvents[0].stats[0].numAffected"))
    assert stats["Category"] == "Study Results › Adverse Event Information"
    assert stats["Field"] == "Number of Participants Affected"
    assert stats["Value"] == 3
    assert stats["Role"] == "event_table=serious; group=EG000"


def test_a_study_without_results_says_so_beside_its_publications(written):
    _, path = written
    events = by_header(path, "Adverse Events")
    ongoing = [e for e in events if e["NCT Number"] == "NCT07654321"]
    assert len(ongoing) == 1
    assert ongoing[0]["Results"] == "no results posted"
    assert ongoing[0]["Publications"] == "DERIVED: PMID 35273311"
    posted = [e for e in events if e["NCT Number"] == "NCT01234567"]
    assert len(posted) == 4
    blank = next(e for e in posted if e["Term"] == "Fatigue" and e["Group ID"] == "EG001")
    assert blank["Participants at Risk"] == 60
    assert blank["At Risk Source"] == "group total (the event's is blank)"


def test_a_derived_publication_is_never_called_a_result(written):
    _, path = written
    publications = by_header(path, "Publications")
    derived = [p for p in publications if p["Type"] == "DERIVED"]
    assert derived and all("result" not in p["What the Type Says"].lower() for p in derived)
    result = next(p for p in publications if p["Type"] == "RESULT")
    assert (
        result["What the Type Says"] == "reports results from this study, as the responsible party marked it"
    )
    book = load_workbook(path)
    assert book["Publications"]["B2"].hyperlink.target == "https://pubmed.ncbi.nlm.nih.gov/31589554/"
    assert book["Documents"]["I2"].hyperlink.target == (
        "https://cdn.clinicaltrials.gov/large-docs/67/NCT01234567/Prot_SAP_000.pdf"
    )
    book.close()


def test_only_approved_checks_run(written):
    _, path = written
    checks = by_header(path, "Checks")
    assert {c["Check"] for c in checks} == set(APPROVED)
    rules = by_header(path, "Check Rules")
    assert [r["Check"] for r in rules] == [c.id for c in CHECKS]
    assert {r["Check"]: r["Approval"] for r in rules} == {
        c.id: ("approved" if c.id in APPROVED else "proposed") for c in CHECKS
    }


def test_a_changed_cell_is_named(written):
    data, path = written
    book = load_workbook(path)
    book["Studies"]["B2"].value = "A Different Title"
    book.save(path)
    problems = certify(data, path)
    assert problems and problems[0].startswith("Studies row 2:")


def test_the_writer_refuses_what_does_not_certify(tmp_path, monkeypatch):
    original = workbook._cell

    def tampering(sheet, fact):
        if fact.value == "A Study of Testamab in Example Disease":
            return workbook.WriteOnlyCell(sheet, value="tampered")
        return original(sheet, fact)

    monkeypatch.setattr(workbook, "_cell", tampering)
    with pytest.raises(WorkbookError) as raised:
        write_workbook(record(results_study()), tmp_path / "review.xlsx")
    assert raised.value.code == "workbook.readback_mismatch"


def studies_row(path):
    return by_header(path, "Studies")[0]


def test_a_number_a_cell_cannot_hold_is_replaced_by_its_reason(tmp_path):
    study = results_study()
    study["protocolSection"]["designModule"]["enrollmentInfo"]["count"] = 2**53 + 1
    path = tmp_path / "review.xlsx"
    write_workbook(record(study), path)
    assert studies_row(path)["Enrollment"] == (
        "(not written: a number a spreadsheet cell cannot hold exactly; it is in studies.json: "
        "protocolSection.designModule.enrollmentInfo.count of this row's study)"
    )


def test_a_character_the_file_forbids_is_replaced_by_its_reason(tmp_path):
    study = results_study()
    study["protocolSection"]["identificationModule"]["briefTitle"] = "a\uffffb"
    path = tmp_path / "review.xlsx"
    write_workbook(record(study), path)
    assert studies_row(path)["Brief Title"].startswith("(not written: characters a spreadsheet file cannot")


def test_an_intervention_without_a_type_is_never_given_one(tmp_path):
    study = results_study()
    del study["protocolSection"]["armsInterventionsModule"]["interventions"][0]["type"]
    path = tmp_path / "review.xlsx"
    write_workbook(record(study), path)
    assert by_header(path, "Interventions")[0]["Registry Form"] == "type not reported: Testamab"


def test_a_boolean_in_place_of_a_count_is_named(written):
    data, path = written
    book = load_workbook(path)
    assert book["Event Groups"]["E2"].value == 1
    book["Event Groups"]["E2"].value = True
    book.save(path)
    problems = certify(data, path)
    assert problems and problems[0].startswith("Event Groups row 2:")


def test_an_unreadable_workbook_is_named(written):
    data, path = written
    path.write_bytes(b"not a workbook")
    problems = certify(data, path)
    assert len(problems) == 1 and problems[0].startswith("workbook.unreadable: review.xlsx")
    assert file_problems(data, path)[0].startswith("workbook.unreadable: review.xlsx")


def rewrite_part(path, name, transform):
    with zipfile.ZipFile(path) as source:
        parts = [(info, source.read(info.filename)) for info in source.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as target:
        for info, data in parts:
            target.writestr(info, transform(data) if info.filename == name else data)


def test_the_file_is_the_one_this_version_writes(written):
    data, path = written
    assert file_problems(data, path) == []


def test_a_changed_link_is_named_though_every_cell_certifies(written):
    data, path = written
    rewrite_part(
        path,
        "xl/worksheets/_rels/sheet2.xml.rels",
        lambda part: part.replace(
            b"https://clinicaltrials.gov/study/NCT01234567", b"https://example.org/wrong-study"
        ),
    )
    assert certify(data, path) == []
    problems = file_problems(data, path)
    assert len(problems) == 1
    assert problems[0].startswith(
        "workbook.file_differs: review.xlsx: xl/worksheets/_rels/sheet2.xml.rels (the Studies sheet's links) "
        "differs"
    )
    assert file_problems(data, record_book(path), RECORD) == []


def test_an_added_part_is_named(written):
    data, path = written
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("xl/comments1.xml", "<comments/>")
    problems = file_problems(data, path)
    assert problems == [
        "workbook.file_differs: review.xlsx: the file's parts are not those this version writes "
        "(added ['xl/comments1.xml'], missing [], or in another order)"
    ]


def test_writing_twice_is_cell_identical(tmp_path):
    data = record(results_study(), ongoing_study())
    for book in BOOKS:
        first, second = tmp_path / f"a-{book.name}", tmp_path / f"b-{book.name}"
        write_workbook(data, first, book)
        write_workbook(data, second, book)
        for name in ["About", *(sheet.name for sheet in book.sheets)]:
            assert rows(first, name) == rows(second, name)


def test_the_writer_counts_the_cells_it_wrote(tmp_path):
    data = record(results_study(), ongoing_study(), hazard_study())
    for book in BOOKS:
        path = tmp_path / book.name
        cells = write_workbook(data, path, book)
        opened = load_workbook(path, read_only=True)
        names = opened.sheetnames
        opened.close()
        assert cells == sum(len(row) for name in names for row in rows(path, name)), book.name


def test_a_sheet_past_the_row_limit_continues(tmp_path, monkeypatch):
    monkeypatch.setattr(
        workbook, "sheet_fits", lambda data_rows: "fits" if data_rows + 1 <= 40 else "too_many_rows"
    )
    data = record(results_study(), ongoing_study())
    path = tmp_path / RECORD.name
    write_workbook(data, path, RECORD)
    book = load_workbook(path, read_only=True)
    parts = [name for name in book.sheetnames if name == "Record" or name.startswith("Record ")]
    book.close()
    assert len(parts) > 1
    total = sum(len(rows(path, part)) - 1 for part in parts)
    assert total == sum(len(leaves(study)) for study in data["studies"])
    assert certify(data, path, book=RECORD) == []


def test_a_file_any_reader_fails_on_is_named_never_raised(written):
    import re

    data, path = written
    rewrite_part(
        path,
        "xl/worksheets/sheet1.xml",
        lambda part: re.sub(rb'<c r="A1"[^>]*>.*?</c>', b'<c r="A1" t="s"><v>999999</v></c>', part, count=1),
    )
    problems = certify(data, path)
    assert len(problems) == 1 and problems[0].startswith("workbook.unreadable: review.xlsx")


def test_a_check_detail_no_cell_can_hold_names_the_fields_the_check_reads(tmp_path):
    study = results_study()
    study["protocolSection"]["statusModule"]["resultsFirstSubmitDate"] = "2020-05-01\x07"
    path = tmp_path / "review.xlsx"
    write_workbook(record(study), path)
    detail = next(r for r in by_header(path, "Checks") if r["Check"] == "results_flag_first_submit")["Detail"]
    assert detail == (
        "(not written: characters a spreadsheet file cannot hold; it is in studies.json: hasResults; "
        "protocolSection.statusModule.resultsFirstSubmitDate of this row's study)"
    )
