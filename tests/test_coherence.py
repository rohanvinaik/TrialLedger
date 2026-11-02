"""Coherence — design coordinates as domains narrowed by evidence and relations, to a fixed point, at each
epistemic status (add-scoped-reasoning, Decisions 1, 2, 7 and 8).

Positive: an inclusion atom keeps the values it states and an exclusion atom removes them, each removal named
with its criterion; relations narrow when their facts hold and their prior-lines condition is met; closure
reaches the same fixed point in any order; every relation has a kind apart from its approval, the four
approved earlier defaults and the three proposed proposals; a trial requiring no prior advanced therapy for
stage IV disease is first line at the interpolated level, by the default; a strict relation narrows the known
domain, and a strict relation applied to a default's conclusion narrows the interpolated one; each proposal
narrows the interpolated domain on its own (a resected and resectable trial gets each proposal's pair, never
their intersection); a consumer accepting interpolated values builds on an interpolated single value,
labelled so, and a pair rests on its weakest status; contradictory evidence empties a domain and names every
cause.
Negative: silence never narrows (no evidence leaves every domain full); an unsectioned atom, an atom of
unspecified scope and an atom without values never narrow; no relation is strict, so a default's conclusion
never enters the known domain and a proposal's never enters the known or interpolated one; a default never
fires on its counterexamples; a relation whose facts are absent never applies; an unknown relation id, a
relation of no kind and a consumer accepting proposals are refused, never silently skipped; an empty domain is
never resolved, and a conflict or several values is never a value to build on.
"""

import pytest

from TrialLedger.layer2.coherence import (
    COORDINATES,
    KINDS,
    RELATIONS,
    SETTINGS,
    Relation,
    accepted_value,
    close,
    domain_state,
    level_status,
    narrow_by_evidence,
    resolve,
    weakest,
)

RELATION_IDS = tuple(relation.id for relation in RELATIONS)
DEFAULTS = (
    "first_line_when_no_prior_advanced_therapy",
    "previously_treated_when_prior_advanced_therapy_required",
    "advanced_when_metastatic_disease_required",
    "advanced_when_stage_iv_required",
)
PROPOSALS = (
    "adjuvant_or_perioperative_when_resection_required",
    "neoadjuvant_or_perioperative_when_resectable_required",
    "consolidation_when_named",
)


def raised(function, *args):
    """An exception compared as a value: (its type's name, its args)."""
    try:
        function(*args)
    except Exception as error:  # noqa: BLE001 — the exception is the value under test
        return type(error).__name__, error.args
    return None


FIRST_LINE = [
    ("inclusion", "prior_lines", ("0",), "advanced", "c3"),
    ("inclusion", "stage", ("IV",), "", "c2"),
    ("inclusion", "extent", ("metastatic",), "", "c2"),
]


def test_silence_never_narrows():
    domains, causes = narrow_by_evidence([])
    assert domains == dict(COORDINATES)
    assert causes == []


def test_inclusion_keeps_and_exclusion_removes_with_causes():
    domains, causes = narrow_by_evidence(
        [
            ("inclusion", "biomarker:EGFR", ("negative", "unknown"), "", "c1"),
            ("exclusion", "biomarker:ALK", ("positive",), "", "c9"),
        ]
    )
    assert domains["selection:EGFR"] == ("negative", "unknown")
    assert domains["selection:ALK"] == ("negative", "unknown")
    assert causes == [("selection:EGFR", ("positive",), "c1"), ("selection:ALK", ("positive",), "c9")]


@pytest.mark.parametrize(
    "atom",
    [
        ("unsectioned", "prior_lines", ("0",), "advanced", "c1"),
        ("inclusion", "prior_lines", ("0",), "unspecified", "c1"),
        ("inclusion", "biomarker:PD-L1", ("positive",), "", "c1"),
        ("inclusion", "biomarker:EGFR", (), "", "c1"),
        ("inclusion", "stage", ("IV",), "", "c1"),
    ],
)
def test_atoms_that_state_no_coordinate_never_narrow(atom):
    assert narrow_by_evidence([atom]) == (dict(COORDINATES), [])


def test_contradictory_evidence_is_a_named_conflict():
    domains, causes = narrow_by_evidence(
        [
            ("inclusion", "prior_lines", ("0",), "advanced", "c3"),
            ("inclusion", "prior_lines", ("1",), "advanced", "c4"),
        ]
    )
    assert domains["prior_advanced_lines"] == ()
    assert domain_state(domains["prior_advanced_lines"], COORDINATES["prior_advanced_lines"]) == "conflict"
    assert [ref for _, _, ref in causes] == ["c3", "c4"]


def test_every_relation_has_a_kind_apart_from_its_approval():
    kinds = {relation.id: (relation.kind, relation.approval) for relation in RELATIONS}
    assert kinds == {
        **{relation: ("default", "approved") for relation in DEFAULTS},
        **{relation: ("proposal", "proposed") for relation in PROPOSALS},
    }
    assert KINDS == ("strict", "default", "proposal")
    assert not [relation for relation in RELATIONS if relation.kind == "strict"]


def test_first_line_is_interpolated_by_the_default_and_never_known():
    result = resolve(FIRST_LINE)
    assert result["prior_advanced_lines"]["domain"] == ("0",)
    assert result["prior_advanced_lines"]["causes"] == [("prior_advanced_lines", ("1", "2", "3+"), "c3")]
    # the known setting rests on stated evidence and strict relations alone: no relation is strict
    assert (result["setting"]["domain"], result["setting"]["state"], result["setting"]["causes"]) == (
        SETTINGS,
        "unnarrowed",
        [],
    )
    interpolated = result["setting"]["interpolated"]
    assert (interpolated["domain"], interpolated["state"]) == (("advanced_first_line",), "resolved")
    # the first default listed leaves one value, so the others (advanced, a superset) remove nothing more
    assert interpolated["causes"] == [
        (
            "setting",
            tuple(s for s in SETTINGS if s != "advanced_first_line"),
            "first_line_when_no_prior_advanced_therapy",
        )
    ]
    assert result["setting"]["proposals"] == []
    # a coordinate no default narrows is the same at both levels, with no cause added
    assert result["prior_advanced_lines"]["interpolated"] == {
        "domain": ("0",),
        "state": "resolved",
        "causes": [],
    }


def test_the_whole_reading_of_one_stated_coordinate_is_pinned():
    """Positive: a trial stating only no prior advanced line gets, for every coordinate in order, exactly its
    three levels: prior lines known as none, with its one cause, and every other coordinate unnarrowed at both
    levels. Negative: no relation fires (no advanced-disease fact), no proposal is listed, and nothing else is
    returned (Detective's converge of resolve, 2026-11-01: an exact outcome pinned by hand)."""
    unnarrowed = {
        name: {
            "domain": full,
            "state": "unnarrowed",
            "causes": [],
            "interpolated": {"domain": full, "state": "unnarrowed", "causes": []},
            "proposals": [],
        }
        for name, full in COORDINATES.items()
    }
    expected = {
        **unnarrowed,
        "prior_advanced_lines": {
            "domain": ("0",),
            "state": "resolved",
            "causes": [("prior_advanced_lines", ("1", "2", "3+"), "criterion 1")],
            "interpolated": {"domain": ("0",), "state": "resolved", "causes": []},
            "proposals": [],
        },
    }
    result = resolve([("inclusion", "prior_lines", ("0",), "advanced", "criterion 1")])
    assert result == expected
    assert list(result) == list(COORDINATES)


RESECTED_AND_RESECTABLE = [
    ("inclusion", "resection", ("resected",), "", "c0"),
    ("inclusion", "resection", ("resectable",), "", "c1"),
]


def test_each_proposal_narrows_on_its_own_never_cumulatively():
    """Positive: a trial requiring a resection and resectable disease gets each proposal's narrowing apart.
    Negative: never their intersection (perioperative alone), and neither enters a level built on."""
    row = resolve(RESECTED_AND_RESECTABLE)["setting"]
    assert row["domain"] == row["interpolated"]["domain"] == SETTINGS
    assert row["proposals"] == [
        {
            "relation": "adjuvant_or_perioperative_when_resection_required",
            "domain": ("adjuvant", "perioperative"),
            "state": "unresolved",
            "causes": [
                (
                    "setting",
                    tuple(s for s in SETTINGS if s not in ("adjuvant", "perioperative")),
                    "adjuvant_or_perioperative_when_resection_required",
                )
            ],
        },
        {
            "relation": "neoadjuvant_or_perioperative_when_resectable_required",
            "domain": ("neoadjuvant", "perioperative"),
            "state": "unresolved",
            "causes": [
                (
                    "setting",
                    tuple(s for s in SETTINGS if s not in ("neoadjuvant", "perioperative")),
                    "neoadjuvant_or_perioperative_when_resectable_required",
                )
            ],
        },
    ]
    assert not [p for p in row["proposals"] if p["domain"] == ("perioperative",)]


def test_a_proposal_narrows_from_the_interpolated_domain():
    """A resection required beside a prior advanced line required: the default leaves previously treated or
    maintenance, and the proposal, applied to that, leaves nothing (a conflict), only at its own level."""
    row = resolve(
        [
            ("inclusion", "resection", ("resected",), "", "c0"),
            ("inclusion", "prior_lines", ("1", "2", "3+"), "advanced", "c1"),
        ]
    )["setting"]
    assert row["domain"] == SETTINGS
    assert row["interpolated"]["domain"] == ("advanced_previously_treated", "maintenance")
    assert row["proposals"] == [
        {
            "relation": "adjuvant_or_perioperative_when_resection_required",
            "domain": (),
            "state": "conflict",
            "causes": [
                (
                    "setting",
                    ("advanced_previously_treated", "maintenance"),
                    "adjuvant_or_perioperative_when_resection_required",
                )
            ],
        }
    ]


def table():
    """A declared table: a default narrowing prior lines to none on a named word, and a strict relation from
    no prior lines to first line."""
    lines = Relation(
        "no_prior_lines_when_named",
        "a test default",
        "a test basis",
        "proposed",
        "default",
        ("inclusion:setting_word:x",),
        (),
        "prior_advanced_lines",
        ("0",),
    )
    strict = Relation(
        "first_line_when_no_prior_lines",
        "a test strict relation",
        "a test basis",
        "proposed",
        "strict",
        (),
        ("0",),
        "setting",
        ("advanced_first_line",),
    )
    return lines, strict


def test_a_strict_relation_narrows_the_known_domain():
    row = resolve([("inclusion", "prior_lines", ("0",), "advanced", "c3")], relations=table())["setting"]
    assert (row["domain"], row["state"]) == (("advanced_first_line",), "resolved")
    assert row["causes"] == [
        (
            "setting",
            tuple(s for s in SETTINGS if s != "advanced_first_line"),
            "first_line_when_no_prior_lines",
        )
    ]
    assert row["interpolated"] == {"domain": ("advanced_first_line",), "state": "resolved", "causes": []}


def test_a_strict_relation_on_a_defaults_conclusion_is_interpolated():
    """Positive: a default narrows prior lines to none, then the strict relation gives first line, both at the
    interpolated level. Negative: neither reaches the known level."""
    result = resolve([("inclusion", "setting_word", ("x",), "", "c0")], relations=table())
    assert result["prior_advanced_lines"]["domain"] == ("0", "1", "2", "3+")
    assert result["setting"]["domain"] == SETTINGS
    assert result["prior_advanced_lines"]["interpolated"]["domain"] == ("0",)
    assert result["setting"]["interpolated"]["domain"] == ("advanced_first_line",)
    assert {c[2] for c in result["setting"]["interpolated"]["causes"]} == {"first_line_when_no_prior_lines"}


def test_a_relation_of_no_kind_is_refused():
    odd = Relation("odd", "s", "b", "approved", "approved", (), (), "setting", ("adjuvant",))
    refused = raised(lambda: resolve([], relations=(*RELATIONS, odd)))
    assert refused == ("ValueError", ("relations of no kind: ['odd']",))


@pytest.mark.parametrize(
    "level, domain, known, status",
    [
        ("known", ("0",), ("0",), "known"),
        ("known", ("0", "1"), ("0", "1"), "unresolved"),
        ("known", (), (), "unresolved"),
        ("interpolated", ("0",), ("0",), "known"),
        ("interpolated", ("0", "1"), ("0", "1"), "unresolved"),
        ("interpolated", ("0",), ("0", "1"), "interpolated"),
        ("interpolated", ("0", "1"), ("0", "1", "2"), "interpolated"),
        ("interpolated", (), ("0", "1"), "unresolved"),
        ("proposed", ("0",), ("0", "1"), "proposed"),
        ("proposed", ("0", "1"), ("0", "1", "2"), "proposed"),
        ("proposed", (), ("0", "1"), "unresolved"),
    ],
)
def test_each_level_says_its_status(level, domain, known, status):
    assert level_status(level, domain, known) == status


def test_a_level_that_is_none_of_the_three_has_no_status():
    assert raised(level_status, "approved", ("0",), ("0",)) == (
        "ValueError",
        ("no status for the level 'approved'",),
    )


def row(known, interpolated):
    return {"domain": known, "interpolated": {"domain": interpolated}}


@pytest.mark.parametrize(
    "known, interpolated, accepts, value",
    [
        (("adjuvant",), ("adjuvant",), ("known",), ("adjuvant", "known")),
        (("adjuvant",), ("adjuvant",), ("known", "interpolated"), ("adjuvant", "known")),
        (SETTINGS, ("maintenance",), ("known", "interpolated"), ("maintenance", "interpolated")),
        (SETTINGS, ("maintenance",), ("known",), ("", "")),
        (SETTINGS, ("maintenance", "adjuvant"), ("known", "interpolated"), ("", "")),
        ((), (), ("known", "interpolated"), ("", "")),
        (("adjuvant", "perioperative"), (), ("known", "interpolated"), ("", "")),
    ],
)
def test_a_consumer_builds_only_on_the_statuses_it_declares(known, interpolated, accepts, value):
    assert accepted_value(row(known, interpolated), accepts) == value


def test_a_known_only_consumer_never_reads_the_interpolated_level():
    assert accepted_value({"domain": ("adjuvant", "maintenance")}, ("known",)) == ("", "")


@pytest.mark.parametrize(
    "accepts",
    [
        ("known", "proposed"),
        ("interpolated",),
        (),
        ("known", "interpolated", "proposed"),
        ("known", "approved"),
    ],
)
def test_a_consumer_accepting_proposals_or_not_known_is_refused(accepts):
    assert raised(accepted_value, row(("adjuvant",), ("adjuvant",)), accepts) == (
        "ValueError",
        (f"a consumer accepts known, and interpolated at most, never {list(accepts)}",),
    )


@pytest.mark.parametrize(
    "statuses, status",
    [
        (["known", "known"], "known"),
        (["known", "interpolated"], "interpolated"),
        (["interpolated", "known"], "interpolated"),
        (["interpolated", "proposed", "known"], "proposed"),
        (["known"], "known"),
    ],
)
def test_a_value_rests_on_its_weakest_status(statuses, status):
    assert weakest(statuses) == status


@pytest.mark.parametrize("statuses", [[], ["known", ""], ["unresolved"]])
def test_nothing_named_has_no_status(statuses):
    assert raised(weakest, statuses) == ("ValueError", (f"no status to weigh among {statuses}",))


def setting_after(facts, lines=None):
    evidence = [("inclusion", "prior_lines", lines, "advanced", "c1")] if lines else []
    domains, _ = narrow_by_evidence(evidence)
    defaults = [r.id for r in RELATIONS if r.kind == "default"]
    return close(domains, facts, defaults)[0]["setting"]


@pytest.mark.parametrize(
    "facts, lines",
    [
        # neoadjuvant stage III requiring no prior therapy for "locally advanced" disease (Codex, 2026-10-31)
        (["inclusion:extent:locally advanced", "inclusion:resection:resectable"], ("0",)),
        # resected oligometastatic disease, adjuvant
        (["inclusion:extent:metastatic", "inclusion:stage:IV", "inclusion:resection:resected"], None),
        # consolidation after definitive chemoradiation, one prior platinum regimen given with radiation
        (["inclusion:prior_agent:radiotherapy", "inclusion:setting_word:consolidation"], ("1",)),
        # "stage III or IV" admits stage III chemoradiation
        (["inclusion:stage:III", "inclusion:stage:IV"], None),
    ],
)
def test_approved_relations_never_fire_on_the_counterexamples(facts, lines):
    assert setting_after(facts, lines) == SETTINGS


def test_maintenance_survives_a_prior_line_requirement():
    assert "maintenance" in setting_after(["inclusion:extent:metastatic"], ("1",))


def orders(ids):
    """Every rotation of `ids` and of its reverse: each relation in every position, in both directions (a
    declared set of 2n orders in place of all n! permutations, which made each mutant of `close` run 5,040
    closures and left Detective's measurement of it without a verdict)."""
    forward, backward = list(ids), list(reversed(ids))
    return [seq[i:] + seq[:i] for seq in (forward, backward) for i in range(len(seq))]


def test_the_declared_orders_put_every_relation_everywhere():
    found = orders(RELATION_IDS)
    assert len(found) == 2 * len(RELATION_IDS)
    for relation in RELATION_IDS:
        assert {order.index(relation) for order in found} == set(range(len(RELATION_IDS)))


def test_closure_is_order_independent():
    domains, _ = narrow_by_evidence(FIRST_LINE)
    facts = ["inclusion:stage:IV", "inclusion:extent:metastatic", "inclusion:resection:resected"]
    results = {tuple(close(domains, facts, order)[0].items()) for order in orders(RELATION_IDS)}
    assert len(results) == 1


def test_a_relation_without_its_facts_never_applies():
    domains, _ = narrow_by_evidence([])
    closed, causes = close(domains, [], list(RELATION_IDS))
    assert closed == dict(COORDINATES)
    assert causes == []


def test_relations_that_disagree_empty_the_domain_with_both_named():
    domains, _ = narrow_by_evidence([("inclusion", "prior_lines", ("0",), "advanced", "c1")])
    facts = ["inclusion:extent:metastatic", "inclusion:setting_word:consolidation"]
    closed, causes = close(domains, facts, list(RELATION_IDS))
    assert closed["setting"] == ()
    assert {relation for _, _, relation in causes} >= {
        "first_line_when_no_prior_advanced_therapy",
        "consolidation_when_named",
    }


def hand_built(forbids=("x",), lines_within=("x",)):
    """A relation of a declared table, as Detective's converge of close asked for (2026-11-01)."""
    return Relation("x", "x", "x", "x", "x", ("x",), lines_within, "x", ("x",), ("x",), forbids)


def test_close_on_a_hand_built_table():
    """Positive: a relation whose facts hold, whose forbidding facts are absent and whose prior lines lie
    within its own (strictly fewer) narrows its coordinate, naming the values it removed. Negative: a
    forbidding fact stops it; a domain without the prior-lines coordinate is refused (KeyError), never closed
    as if its prior lines held anything."""
    assert raised(close, {"x": ("x",)}, ["x"], ["x"], (hand_built(),)) == (
        "KeyError",
        ("prior_advanced_lines",),
    )
    wide = {"x": ("x", "y"), "prior_advanced_lines": ("x",)}
    assert close(wide, ["x"], ["x"], (hand_built(),)) == (wide, [])
    narrowed = {"x": ("x",), "prior_advanced_lines": ("x",)}
    assert close(wide, ["x"], ["x"], (hand_built(forbids=()),)) == (narrowed, [("x", ("y",), "x")])
    within = hand_built(forbids=(), lines_within=("x", "z"))
    assert close(wide, ["x"], ["x"], (within,)) == (narrowed, [("x", ("y",), "x")])
    beyond = {"x": ("x", "y"), "prior_advanced_lines": ("x", "q")}
    assert close(beyond, ["x"], ["x"], (within,)) == (beyond, [])


def test_an_unknown_relation_is_never_skipped():
    with pytest.raises(KeyError):
        close(dict(COORDINATES), [], ["no_such_relation"])


@pytest.mark.parametrize(
    "domain, state",
    [
        ((), "conflict"),
        (("0",), "resolved"),
        (("0", "1"), "unresolved"),
        (("0", "1", "2", "3+"), "unnarrowed"),
    ],
)
def test_domain_states(domain, state):
    assert domain_state(domain, COORDINATES["prior_advanced_lines"]) == state
