"""classify_progress — pagination follows a token only while it is still making honest progress.

Positive: a fresh token, with no more studies than the total and at most MAX_EMPTY_PAGES empty pages in a
row, is followed ("continue").
Negative: never follow a token already followed (a loop); never continue once more studies have arrived than
the API's total; never keep following tokens through more than MAX_EMPTY_PAGES consecutive empty pages.
"""

from TrialLedger.ingest import MAX_EMPTY_PAGES, classify_progress


def test_fresh_token_continues():
    assert classify_progress("b", ["a"], 100, 250, 0) == "continue"


def test_first_token_continues():
    assert classify_progress("a", [], 0, 0, 1) == "continue"


def test_received_equal_to_total_continues():
    assert classify_progress("b", ["a"], 250, 250, 1) == "continue"


def test_empty_streak_at_the_limit_continues():
    assert classify_progress("c", ["a", "b"], 10, 10, MAX_EMPTY_PAGES) == "continue"


def test_repeated_token_stops():
    assert classify_progress("a", ["x", "a"], 100, 250, 0) == "repeated_token"


def test_more_than_total_stops():
    assert classify_progress("b", ["a"], 251, 250, 0) == "overrun"


def test_one_empty_page_too_many_stops():
    assert classify_progress("d", ["a", "b", "c"], 10, 10, MAX_EMPTY_PAGES + 1) == "stalled"


def test_repeated_token_is_reported_before_overrun():
    assert classify_progress("a", ["a"], 300, 250, 0) == "repeated_token"


def test_overrun_is_reported_before_stall():
    assert classify_progress("z", ["a"], 300, 250, MAX_EMPTY_PAGES + 1) == "overrun"
