"""assess_completeness — a finished pagination is accepted only if it holds every match exactly once.

Positive: as many distinct studies as the API's total is "complete", including zero of zero.
Negative: a repeated study, fewer studies than the total, or more than the total is never "complete".
"""

from TrialLedger.ingest import assess_completeness


def test_every_match_once_is_complete():
    assert assess_completeness(3, ["NCT00000001", "NCT00000002", "NCT00000003"]) == "complete"


def test_zero_of_zero_is_complete():
    assert assess_completeness(0, []) == "complete"


def test_repeated_study():
    assert assess_completeness(3, ["NCT00000001", "NCT00000001", "NCT00000002"]) == "duplicates"


def test_fewer_than_total():
    assert assess_completeness(3, ["NCT00000001", "NCT00000002"]) == "short"


def test_nothing_received_of_a_positive_total():
    assert assess_completeness(5, []) == "short"


def test_more_than_total():
    assert assess_completeness(1, ["NCT00000001", "NCT00000002"]) == "excess"


def test_duplicates_are_reported_before_a_count_mismatch():
    assert assess_completeness(5, ["NCT00000001", "NCT00000001"]) == "duplicates"
