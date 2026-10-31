"""date_interval — a registry partial date as the span of days it may denote.

Positive: yyyy covers its year, yyyy-MM its month (leap years honoured), yyyy-MM-dd one day.
Negative: any other form, or a day that does not exist, is unparseable, never repaired.
"""

from datetime import date

import pytest

from TrialLedger.checks import date_interval


def day(y, m, d):
    return date(y, m, d).toordinal()


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2020", ("year", (day(2020, 1, 1), day(2020, 12, 31)))),
        ("2020-02", ("month", (day(2020, 2, 1), day(2020, 2, 29)))),
        ("2021-02", ("month", (day(2021, 2, 1), day(2021, 2, 28)))),
        ("2020-12", ("month", (day(2020, 12, 1), day(2020, 12, 31)))),
        ("2020-05-17", ("day", (day(2020, 5, 17), day(2020, 5, 17)))),
        (None, ("absent", None)),
        ("2020-13", ("unparseable", None)),
        ("2020-00", ("unparseable", None)),
        ("2020-02-30", ("unparseable", None)),
        ("0000", ("unparseable", None)),
        ("2020-5", ("unparseable", None)),
        ("20-05-01", ("unparseable", None)),
        ("2020-05-17T00:00", ("unparseable", None)),
        ("May 2020", ("unparseable", None)),
        (2020, ("unparseable", None)),
    ],
)
def test_intervals(text, expected):
    assert date_interval(text) == expected
