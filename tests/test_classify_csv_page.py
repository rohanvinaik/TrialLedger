"""classify_csv_page — each CSV page must fit when the pages are concatenated into one spreadsheet.

Positive: a first page that starts with the API's header row and carries an integer x-total-count, and later
pages without the header, are "next" with an x-next-page-token and "last" without; CRLF and LF line ends both
count as terminated; an empty later page is acceptable.
Negative: never accept a first page without the header, a later page that repeats it, a non-empty page that
does not end in a line break, a first page without a usable x-total-count, or an empty token.
"""

from TrialLedger.ingest import CSV_HEADER_START, classify_csv_page

HEADER = CSV_HEADER_START + "Study Title,Study URL\r\n"
ROW = "NCT04852770,A title,https://clinicaltrials.gov/study/NCT04852770\r\n"


def test_first_page_with_token_is_next():
    assert classify_csv_page(HEADER + ROW, True, "48", "tok") == "next"


def test_first_page_without_token_is_last():
    assert classify_csv_page(HEADER + ROW, True, "1", None) == "last"


def test_header_only_first_page_with_zero_total_is_last():
    assert classify_csv_page(HEADER, True, "0", None) == "last"


def test_later_page_with_token_is_next():
    assert classify_csv_page(ROW, False, None, "tok") == "next"


def test_later_page_without_token_is_last():
    assert classify_csv_page(ROW, False, None, None) == "last"


def test_lf_line_end_is_terminated():
    assert classify_csv_page("NCT04852770,A title,x\n", False, None, None) == "last"


def test_empty_later_page_is_acceptable():
    assert classify_csv_page("", False, None, None) == "last"


def test_first_page_without_header():
    assert classify_csv_page(ROW, True, "1", None) == "no_header"


def test_empty_first_page_has_no_header():
    assert classify_csv_page("", True, "0", None) == "no_header"


def test_later_page_repeating_the_header():
    assert classify_csv_page(HEADER + ROW, False, None, None) == "extra_header"


def test_unterminated_first_page():
    assert classify_csv_page(HEADER + ROW.rstrip("\r\n"), True, "1", None) == "unterminated"


def test_unterminated_later_page():
    assert classify_csv_page("NCT04852770,A title", False, None, "tok") == "unterminated"


def test_page_ending_in_carriage_return_only_is_unterminated():
    assert classify_csv_page("NCT04852770,A title\r", False, None, None) == "unterminated"


def test_first_page_without_total():
    assert classify_csv_page(HEADER + ROW, True, None, None) == "no_total"


def test_first_page_with_non_numeric_total():
    assert classify_csv_page(HEADER + ROW, True, "many", None) == "no_total"


def test_first_page_with_negative_total():
    assert classify_csv_page(HEADER + ROW, True, "-1", None) == "no_total"


def test_first_page_with_non_ascii_digit_total():
    assert classify_csv_page(HEADER + ROW, True, "٣", None) == "no_total"


def test_later_page_total_is_not_required():
    assert classify_csv_page(ROW, False, "junk", None) == "last"


def test_empty_token():
    assert classify_csv_page(ROW, False, None, "") == "bad_token"
