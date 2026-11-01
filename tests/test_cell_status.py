"""cell_status — what one declared cell of the balance table says.

Positive: a cell a drawn trial holds is present, whatever the registry says; a cell no drawn trial holds that
the registry holds is a gap, and a filled gap is named as filled by a supplement; a cell the registry returns
none for by a verified query is empty in the registry.
Negative: a cell no trial of the frame holds is never a gap; a cell the registry was not asked about is never
called a gap or empty, only not checked; a supplement never makes a cell present; a zero-hit answer to a query
whose form was never tried live is never read as absence, only as query_unverified.
"""

from TrialLedger.sample import cell_status


def test_present_and_gaps():
    assert cell_status(3, 0, None, True) == "present"
    assert cell_status(1, 2, 0, False) == "present"
    assert cell_status(0, 0, 40, True) == "gap"
    assert cell_status(0, 0, 40, False) == "gap"
    assert cell_status(0, 1, 40, True) == "gap_supplemented"
    assert cell_status(0, 1, 1, False) == "gap_supplemented"


def test_never_a_gap_without_the_registrys_word():
    assert cell_status(0, 0, 0, True) == "empty_in_registry"
    assert cell_status(0, 0, None, True) == "not_checked"
    assert cell_status(0, 2, None, False) == "not_checked"
    assert cell_status(0, 3, 0, True) == "empty_in_registry"


def test_silence_from_an_unverified_query_is_never_absence():
    assert cell_status(0, 0, 0, False) == "query_unverified"
    assert cell_status(0, 3, 0, False) == "query_unverified"
    assert cell_status(0, 0, 0, True) != "query_unverified"
