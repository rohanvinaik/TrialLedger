"""results_state — what a record states about posted results, from the registry's own flag.

Positive: a true flag with results is "posted"; a false flag without results is "not_posted".
Negative: a flag that disagrees with the record's contents is never "posted" or "not_posted"; an absent or
non-boolean flag is never read as either.
"""

import pytest

from TrialLedger.ledger import results_state


@pytest.mark.parametrize(
    "flag, section, expected",
    [
        (True, True, "posted"),
        (False, False, "not_posted"),
        (True, False, "flag_without_results"),
        (False, True, "results_without_flag"),
        (None, True, "flag_not_reported"),
        (None, False, "flag_not_reported"),
        ("false", False, "flag_not_reported"),
        (0, False, "flag_not_reported"),
    ],
)
def test_states(flag, section, expected):
    assert results_state(flag, section) == expected
