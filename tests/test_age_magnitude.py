"""age_magnitude — an age limit as a whole number within the unit family that converts exactly.

Positive: years and months become months (×12, ×1); weeks, days, hours and minutes become minutes.
Negative: anything but "<n> <unit>" in the registry's exact form is unparseable, never guessed.
"""

import pytest

from TrialLedger.checks import age_magnitude


@pytest.mark.parametrize(
    "age, expected",
    [
        ("18 Years", ("calendar", 216)),
        ("1 Year", ("calendar", 12)),
        ("6 Months", ("calendar", 6)),
        ("1 Month", ("calendar", 1)),
        ("2 Weeks", ("clock", 20160)),
        ("1 Week", ("clock", 10080)),
        ("3 Days", ("clock", 4320)),
        ("1 Day", ("clock", 1440)),
        ("2 Hours", ("clock", 120)),
        ("1 Hour", ("clock", 60)),
        ("30 Minutes", ("clock", 30)),
        ("1 Minute", ("clock", 1)),
        ("0 Years", ("calendar", 0)),
        (None, ("absent", None)),
        ("18 years", ("unparseable", None)),
        ("18Years", ("unparseable", None)),
        (" 18 Years", ("unparseable", None)),
        ("18 Years ", ("unparseable", None)),
        ("N/A", ("unparseable", None)),
        ("1.5 Years", ("unparseable", None)),
        (18, ("unparseable", None)),
    ],
)
def test_magnitudes(age, expected):
    assert age_magnitude(age) == expected


def test_an_age_of_more_than_nine_digits_is_unparseable():
    from TrialLedger.checks import age_magnitude

    assert age_magnitude("999999999 Years") == ("calendar", 999999999 * 12)
    assert age_magnitude("1000000000 Years") == ("unparseable", None)
    assert age_magnitude("9" * 5000 + " Days") == ("unparseable", None)
