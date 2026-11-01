"""The date-order checks read only dates that record events that happened (checks version 2, 2026-11-01).

Positive: two ACTUAL dates in order are consistent, and certainly inverted are a conflict; the gathered check
names each date with its type.
Negative: an ESTIMATED date never makes a conflict, however far it lies from the other (a stale forecast is
not a contradiction); a missing type is never consistent; overlapping partial dates decide nothing.
"""

import pytest
from records import results_study

from TrialLedger.checks import actual_dates_ordered, run_checks

P = "protocolSection"


def test_two_actual_dates_are_ordered_or_inverted():
    assert actual_dates_ordered("2019-01-05", "ACTUAL", "2020-06-30", "ACTUAL") == "consistent"
    assert actual_dates_ordered("2021-01", "ACTUAL", "2020-06-30", "ACTUAL") == "conflict"


@pytest.mark.parametrize(
    ("earlier_type", "later_type"),
    [("ESTIMATED", "ACTUAL"), ("ACTUAL", "ESTIMATED"), ("ESTIMATED", "ESTIMATED")],
)
def test_a_forecast_is_never_a_contradiction(earlier_type, later_type):
    assert actual_dates_ordered("2021-06", earlier_type, "2020-05", later_type) == "not_applicable"


def test_a_missing_type_or_an_open_order_decides_nothing():
    assert actual_dates_ordered("2021-06", None, "2020-05", "ACTUAL") == "not_checkable"
    assert actual_dates_ordered("2020-06", "ACTUAL", "2020", "ACTUAL") == "not_checkable"


def test_an_estimated_start_after_the_actual_primary_completion_raises_no_query():
    study = results_study()
    status = study[P]["statusModule"]
    status["startDateStruct"] = {"date": "2021-06", "type": "ESTIMATED"}
    result = {r.check_id: r for r in run_checks(study)}["start_before_primary_completion"]
    assert result.outcome == "not_applicable"
    assert "startDateStruct.type=ESTIMATED" in result.detail
