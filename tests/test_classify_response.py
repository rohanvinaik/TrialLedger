"""classify_response — what one HTTP exchange means.

Positive: a 2xx carrying the expected media type is "ok" (charset parameters and letter case do not matter);
no response, 429 and 500/502/503/504 are retried while attempts remain.
Negative: an error status, a redirect or a body of the wrong media type is never "ok"; 400 and 404 are never
retried; once attempts run out a 503 is "server_error", a 429 "rate_limited" and a missing response
"no_response" — never a silent success, never another retry.
"""

from TrialLedger.ingest import classify_response

JSON = "application/json"
CSV = "text/csv"


def test_json_200_is_ok():
    assert classify_response(200, JSON, JSON, 1, 4) == "ok"


def test_csv_200_is_ok():
    assert classify_response(200, CSV, CSV, 1, 4) == "ok"


def test_media_type_parameters_and_case_are_ignored():
    assert classify_response(200, "Application/JSON; charset=utf-8", JSON, 1, 4) == "ok"


def test_last_2xx_code_is_ok():
    assert classify_response(299, JSON, JSON, 1, 4) == "ok"


def test_html_200_is_wrong_content_type():
    assert classify_response(200, "text/html; charset=utf-8", JSON, 1, 4) == "wrong_content_type"


def test_csv_body_when_json_expected_is_wrong_content_type():
    assert classify_response(200, CSV, JSON, 1, 4) == "wrong_content_type"


def test_missing_content_type_is_wrong_content_type():
    assert classify_response(200, None, JSON, 1, 4) == "wrong_content_type"


def test_301_is_a_redirect():
    assert classify_response(301, None, JSON, 1, 4) == "redirect"


def test_first_3xx_code_is_a_redirect():
    assert classify_response(300, JSON, JSON, 1, 4) == "redirect"


def test_last_3xx_code_is_a_redirect():
    assert classify_response(399, JSON, JSON, 1, 4) == "redirect"


def test_503_with_attempts_left_is_retried():
    assert classify_response(503, "text/html", JSON, 1, 4) == "retry"


def test_503_on_the_last_attempt_is_server_error():
    assert classify_response(503, "text/html", JSON, 4, 4) == "server_error"


def test_503_past_the_last_attempt_is_server_error():
    assert classify_response(503, "text/html", JSON, 5, 4) == "server_error"


def test_500_with_attempts_left_is_retried():
    assert classify_response(500, None, JSON, 3, 4) == "retry"


def test_502_with_attempts_left_is_retried():
    assert classify_response(502, None, CSV, 2, 4) == "retry"


def test_504_on_the_last_attempt_is_server_error():
    assert classify_response(504, None, CSV, 4, 4) == "server_error"


def test_501_is_not_retried():
    assert classify_response(501, None, JSON, 1, 4) == "unexpected_status"


def test_429_with_attempts_left_is_retried():
    assert classify_response(429, "text/plain", JSON, 1, 4) == "retry"


def test_429_on_the_last_attempt_is_rate_limited():
    assert classify_response(429, "text/plain", JSON, 4, 4) == "rate_limited"


def test_no_response_with_attempts_left_is_retried():
    assert classify_response(None, None, JSON, 1, 4) == "retry"


def test_no_response_on_the_last_attempt_is_no_response():
    assert classify_response(None, None, JSON, 4, 4) == "no_response"


def test_a_single_attempt_budget_never_retries():
    assert classify_response(503, None, JSON, 1, 1) == "server_error"


def test_400_is_never_retried():
    assert classify_response(400, "text/plain", JSON, 1, 4) == "bad_request"


def test_404_is_never_retried():
    assert classify_response(404, "text/plain", JSON, 1, 4) == "not_found"


def test_other_4xx_is_unexpected():
    assert classify_response(418, "text/plain", JSON, 1, 4) == "unexpected_status"


def test_1xx_is_unexpected():
    assert classify_response(199, JSON, JSON, 1, 4) == "unexpected_status"
