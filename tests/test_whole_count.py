"""whole_count — a participant count the registry stores as text.

Positive: plain ASCII digits are the number they spell, zero included.
Negative: decimals, signs, blanks, non-ASCII digits and non-text are never read as a number.
"""

import pytest

from TrialLedger.checks import whole_count


@pytest.mark.parametrize(
    "text, expected",
    [
        ("12", 12),
        ("0", 0),
        ("007", 7),
        ("1.5", None),
        ("-1", None),
        ("", None),
        (" 3", None),
        ("٣", None),
        (None, None),
        (12, None),
    ],
)
def test_counts(text, expected):
    assert whole_count(text) == expected


def test_a_number_too_long_for_python_to_read_is_no_count():
    from TrialLedger.checks import whole_count

    assert whole_count("9" * 5000) is None
    assert whole_count("9" * 4000) == int("9" * 4000)
