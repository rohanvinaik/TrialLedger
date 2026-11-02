"""classes.progress_due — a long RxNav lookup says how far it has got, never silence for minutes.

The release check (2026-11-01): `resolve` of one trial from an empty cache printed nothing for 169 s.
Positive: a line after every fifth name and after the last; the lookups say "<done> of <total> drug names",
and load_or_lookup_at says first how many names it will ask about.
Negative: no line before the first name, between the fifth names, or past the total; a lookup of nothing says
nothing.
"""

import pytest

from TrialLedger.classes import PROGRESS_EVERY, load_or_lookup_at, lookup, lookup_axes, progress_due


@pytest.mark.parametrize(
    ("done", "total", "due"),
    [
        (5, 12, True),
        (10, 12, True),
        (12, 12, True),
        (1, 1, True),
        (3, 3, True),
        (1, 12, False),
        (4, 12, False),
        (6, 12, False),
        (0, 12, False),
        (0, 0, False),
        (13, 12, False),
        (15, 12, False),
        (-5, 12, False),
    ],
)
def test_progress_is_due_every_fifth_name_and_at_the_end(done, total, due):
    assert progress_due(done, total) is due


def test_the_cadence_is_every_five():
    assert PROGRESS_EVERY == 5
    assert [n for n in range(1, 13) if progress_due(n, 12)] == [5, 10, 12]


def answering(url, params):
    return 200, {}


def test_a_lookup_says_how_far_it_has_got():
    said = []
    names = [f"drug {n}" for n in range(7)]
    lookup([*names, "drug 0"], get=answering, sleep=lambda s: None, progress=said.append)
    assert said == [
        "drug classes asked of RxNav for 5 of 7 drug names",
        "drug classes asked of RxNav for 7 of 7 drug names",
    ]
    said.clear()
    lookup_axes(names[:2], get=answering, sleep=lambda s: None, progress=said.append)
    assert said == ["identity and ATC and structure classes asked of RxNav for 2 of 2 names"]


def test_a_cached_run_says_first_what_it_will_ask(tmp_path):
    said = []
    path = tmp_path / "classes.json"
    load_or_lookup_at(
        path, ["a", "b"], ["a"], fill_axes=True, get=answering, sleep=lambda s: None, progress=said.append
    )
    assert said[0].startswith(
        "asking RxNav, the National Library of Medicine's drug vocabulary, for the drug"
    )
    assert "2 drug names not yet cached" in said[0] and said[1].endswith("for 2 of 2 drug names")
    assert said[2].startswith("asking RxNav for the identity") and "1 experimental drug names" in said[2]
    said.clear()
    load_or_lookup_at(
        path, ["a", "b"], ["a"], fill_axes=True, get=answering, sleep=lambda s: None, progress=said.append
    )
    assert said == []


def test_a_lookup_of_nothing_says_nothing():
    said = []
    assert lookup([], get=answering, sleep=lambda s: None, progress=said.append) == {}
    assert said == []
