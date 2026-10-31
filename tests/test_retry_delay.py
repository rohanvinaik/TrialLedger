"""retry_delay — how long to wait before the next attempt.

Positive: a delta-seconds Retry-After is honoured (surrounding whitespace allowed); otherwise the wait starts
at RETRY_BASE_SECONDS and doubles with each failed attempt; every wait is capped at RETRY_CAP_SECONDS.
Negative: never read an HTTP-date, a negative, fractional, non-ASCII or empty Retry-After as seconds; never
return more than the cap.
"""

from TrialLedger.ingest import RETRY_BASE_SECONDS, RETRY_CAP_SECONDS, retry_delay


def test_the_policy_constants():
    assert (RETRY_BASE_SECONDS, RETRY_CAP_SECONDS) == (2.0, 60.0)


def test_first_attempt_waits_the_base():
    assert retry_delay(1, None) == 2.0


def test_second_attempt_doubles():
    assert retry_delay(2, None) == 4.0


def test_third_attempt_doubles_again():
    assert retry_delay(3, None) == 8.0


def test_exponential_wait_is_capped():
    assert retry_delay(10, None) == 60.0


def test_retry_after_seconds_are_honoured():
    assert retry_delay(1, "7") == 7.0


def test_retry_after_with_whitespace_is_honoured():
    assert retry_delay(3, " 7 ") == 7.0


def test_retry_after_zero_is_honoured():
    assert retry_delay(2, "0") == 0.0


def test_retry_after_is_capped():
    assert retry_delay(1, "300") == 60.0


def test_retry_after_equal_to_cap_is_kept():
    assert retry_delay(1, "60") == 60.0


def test_http_date_retry_after_falls_back_to_backoff():
    assert retry_delay(2, "Wed, 21 Oct 2026 07:28:00 GMT") == 4.0


def test_negative_retry_after_falls_back_to_backoff():
    assert retry_delay(1, "-5") == 2.0


def test_fractional_retry_after_falls_back_to_backoff():
    assert retry_delay(1, "1.5") == 2.0


def test_non_ascii_digit_retry_after_falls_back_to_backoff():
    assert retry_delay(1, "٣") == 2.0


def test_empty_retry_after_falls_back_to_backoff():
    assert retry_delay(1, "") == 2.0
