"""classes.progress_due — a long RxNav lookup says how far it has got, never silence for minutes.

The release check (2026-11-01): `resolve` of one trial from an empty cache printed nothing for 169 s.
Positive: a line after every fifth name and after the last; each round of a lookup says "<done> of <total>"
names or concepts, and its last line how many requests RxNav answered; load_or_lookup_at says first how many
names it will ask about.
Negative: no line before the first name, between the fifth names, or past the total; a lookup of nothing says
nothing and asks nothing.
"""

import pytest
from rxnav_fake import FakeRxNav

from TrialLedger.classes import PROGRESS_EVERY, _ask_rxnav, load_or_lookup_at, progress_due


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


def lookup(names, axes=(), progress=None):
    get = FakeRxNav(names={name: [f"9{n}"] for n, name in enumerate(names)}, concepts={})
    get.concepts = {f"9{n}": (name, "IN") for n, name in enumerate(names)}
    return _ask_rxnav(
        list(dict.fromkeys(names)),
        set(axes),
        get=get,
        sleep=lambda s: None,
        monotonic=lambda: 0.0,
        progress=progress or (lambda m: None),
    )


def test_a_lookup_says_how_far_it_has_got():
    said = []
    names = [f"drug {n}" for n in range(7)]
    lookup([*names, "drug 0"], progress=said.append)
    assert said == [
        "RxNorm identity asked of RxNav for 5 of 7 drug names",
        "RxNorm identity asked of RxNav for 7 of 7 drug names",
        "drug classes asked of RxNav for 5 of 7 RxNorm concepts",
        "drug classes asked of RxNav for 7 of 7 RxNorm concepts",
        "RxNav answered 16 requests about 7 drug names (7 names asked, 7 RxNorm concepts classed)",
    ]
    said.clear()
    lookup(names[:2], names[:2], progress=said.append)
    assert "RxNorm term types asked of RxNav for 2 of 2 concepts" in said


def test_a_cached_run_says_first_what_it_will_ask(tmp_path):
    said = []
    path = tmp_path / "classes.json"
    get = FakeRxNav(names={}, concepts={})
    load_or_lookup_at(
        path, ["a", "b"], ["a"], fill_axes=True, get=get, sleep=lambda s: None, progress=said.append
    )
    assert said[0].startswith("asking RxNav, the National Library of Medicine's drug vocabulary, about 2")
    assert said[1] == "RxNorm identity asked of RxNav for 2 of 2 drug names"
    assert said[-1].startswith("RxNav answered 4 requests about 2 drug names")
    said.clear()
    load_or_lookup_at(
        path, ["a", "b"], ["a"], fill_axes=True, get=get, sleep=lambda s: None, progress=said.append
    )
    assert said == []


def test_a_lookup_of_nothing_says_nothing(tmp_path):
    said = []
    get = FakeRxNav(names={}, concepts={})
    assert load_or_lookup_at(tmp_path / "c.json", [], get=get, progress=said.append) == {}
    assert said == [] and get.asked == []
