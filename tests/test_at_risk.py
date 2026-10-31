"""at_risk — the number at risk for one event, by the registry's rule for a blank.

Positive: a stated number is used as stated, zero included; a blank takes the group's table total.
Negative: a blank is never zero; with both blank there is no number at all.
"""

from TrialLedger.checks import at_risk


def test_a_stated_number_is_used():
    assert at_risk(10, 20) == ("stated", 10)


def test_zero_is_stated_not_blank():
    assert at_risk(0, 20) == ("stated", 0)


def test_a_blank_takes_the_group_total():
    assert at_risk(None, 20) == ("group_total", 20)


def test_both_blank_is_absent_never_zero():
    assert at_risk(None, None) == ("absent", None)
