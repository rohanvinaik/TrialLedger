"""classify_json_page — what one decoded JSON page of /studies means for pagination.

Positive: a well-formed page with a nextPageToken is "next" even when its studies list is empty (the API may
send empty pages); without a token it is "last"; only the first page must carry totalCount.
Negative: a page that is not an object, has no studies list, holds a study without a canonical nctId, lacks a
usable totalCount on the first page, or offers an empty or non-string token is never "next" or "last".
"""

from TrialLedger.ingest import classify_json_page


def study(nct_id):
    return {"protocolSection": {"identificationModule": {"nctId": nct_id}}}


def test_first_page_with_token_is_next():
    page = {"totalCount": 3, "studies": [study("NCT04852770")], "nextPageToken": "abc"}
    assert classify_json_page(page, True) == "next"


def test_empty_page_with_token_is_next():
    assert classify_json_page({"studies": [], "nextPageToken": "abc"}, False) == "next"


def test_first_page_without_token_is_last():
    page = {"totalCount": 1, "studies": [study("NCT04852770")]}
    assert classify_json_page(page, True) == "last"


def test_later_page_needs_no_total():
    assert classify_json_page({"studies": [study("NCT01030536")]}, False) == "last"


def test_zero_results_first_page_is_last():
    assert classify_json_page({"totalCount": 0, "studies": []}, True) == "last"


def test_list_body_is_not_an_object():
    assert classify_json_page([study("NCT04852770")], True) == "not_an_object"


def test_missing_studies():
    assert classify_json_page({"totalCount": 1}, True) == "no_studies"


def test_studies_not_a_list():
    assert classify_json_page({"totalCount": 1, "studies": {"a": 1}}, True) == "no_studies"


def test_study_that_is_not_an_object():
    assert classify_json_page({"totalCount": 1, "studies": ["NCT04852770"]}, True) == "bad_study"


def test_study_without_protocol_section():
    assert classify_json_page({"totalCount": 1, "studies": [{"hasResults": False}]}, True) == ("bad_study")


def test_protocol_section_that_is_not_an_object():
    page = {"totalCount": 1, "studies": [{"protocolSection": "NCT04852770"}]}
    assert classify_json_page(page, True) == "bad_study"


def test_identification_module_that_is_not_an_object():
    page = {"totalCount": 1, "studies": [{"protocolSection": {"identificationModule": ["x"]}}]}
    assert classify_json_page(page, True) == "bad_study"


def test_study_without_identification_module():
    page = {"totalCount": 1, "studies": [{"protocolSection": {"statusModule": {}}}]}
    assert classify_json_page(page, True) == "bad_study"


def test_study_without_nct_id():
    page = {"totalCount": 1, "studies": [{"protocolSection": {"identificationModule": {}}}]}
    assert classify_json_page(page, True) == "bad_study"


def test_study_with_short_nct_id():
    assert classify_json_page({"totalCount": 1, "studies": [study("NCT1030536")]}, True) == ("bad_study")


def test_study_with_lowercase_nct_id():
    assert classify_json_page({"totalCount": 1, "studies": [study("nct01030536")]}, True) == ("bad_study")


def test_study_with_numeric_nct_id():
    assert classify_json_page({"totalCount": 1, "studies": [study(1030536)]}, True) == "bad_study"


def test_one_bad_study_among_good_ones():
    page = {"totalCount": 2, "studies": [study("NCT04852770"), study("")]}
    assert classify_json_page(page, True) == "bad_study"


def test_first_page_without_total():
    assert classify_json_page({"studies": [study("NCT04852770")]}, True) == "no_total"


def test_first_page_with_negative_total():
    assert classify_json_page({"totalCount": -1, "studies": []}, True) == "no_total"


def test_first_page_with_boolean_total():
    assert classify_json_page({"totalCount": True, "studies": [study("NCT04852770")]}, True) == ("no_total")


def test_first_page_with_float_total():
    assert classify_json_page({"totalCount": 5.0, "studies": [study("NCT04852770")]}, True) == ("no_total")


def test_first_page_with_null_total():
    assert classify_json_page({"totalCount": None, "studies": []}, True) == "no_total"


def test_first_page_with_string_total():
    assert classify_json_page({"totalCount": "1", "studies": [study("NCT04852770")]}, True) == ("no_total")


def test_empty_token():
    assert classify_json_page({"studies": [], "nextPageToken": ""}, False) == "bad_token"


def test_null_token():
    assert classify_json_page({"studies": [], "nextPageToken": None}, False) == "bad_token"


def test_numeric_token():
    assert classify_json_page({"studies": [], "nextPageToken": 7}, False) == "bad_token"
