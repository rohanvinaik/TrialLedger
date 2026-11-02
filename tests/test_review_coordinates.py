"""The coordinates the review queue asks about: the conflicts of the known and the interpolated levels
(add-scoped-reasoning, Decision 7), read from coherence.resolve's own rows.

Positive: a trial whose stated evidence contradicts itself is a conflict, every criterion named; a default
that contradicts stated evidence is a conflict at the interpolated level, the criterion and the default both
named, the known level's cause first; a trial the first-line default narrows reads that narrowing and its
cause; every coordinate is read, in resolve's order, at its interpolated level.
Negative: a proposal's conflict is never the trial's (its narrowing is shown with the proposal alone); a
coordinate the levels leave several values is never a conflict; a review flag is raised only for a conflict at
a level built on.
"""

from TrialLedger.coherence import COORDINATES, SETTINGS, Relation, resolve
from TrialLedger.reading import review_coordinates, review_flags

FIRST_LINE = [
    ("inclusion", "stage", ("IV",), "", "c1"),
    ("inclusion", "prior_lines", ("0",), "advanced", "c3"),
]
CONTRADICTORY = [
    ("inclusion", "prior_lines", ("0",), "advanced", "c3"),
    ("inclusion", "prior_lines", ("1",), "advanced", "c4"),
]
# a resection required beside a prior advanced line: the proposal alone leaves no setting
PROPOSAL_CONFLICT = [
    ("inclusion", "resection", ("resected",), "", "c0"),
    ("inclusion", "prior_lines", ("1", "2", "3+"), "advanced", "c1"),
]


def no_prior_lines_default():
    """A declared default: a named word means no prior advanced line."""
    return (
        Relation(
            "no_prior_lines_when_named",
            "a test default",
            "a test basis",
            "proposed",
            "default",
            ("inclusion:setting_word:x",),
            (),
            "prior_advanced_lines",
            ("0",),
        ),
    )


def test_a_trial_the_first_line_default_narrows():
    """Every coordinate, in resolve's order: the setting at its interpolated level with the default that
    narrowed it, prior lines with its criterion, the rest unnarrowed with nothing removed."""
    result = review_coordinates(resolve(FIRST_LINE))
    assert list(result) == list(COORDINATES)
    assert result["setting"] == (
        ["advanced_first_line"],
        "resolved",
        ["first_line_when_no_prior_advanced_therapy"],
    )
    assert result["prior_advanced_lines"] == (["0"], "resolved", ["c3"])
    assert {name: held for name, held in result.items() if name.startswith("selection:")} == {
        name: (list(full), "unnarrowed", [])
        for name, full in COORDINATES.items()
        if name.startswith("selection:")
    }


def test_contradictory_evidence_is_a_conflict_with_every_criterion():
    result = review_coordinates(resolve(CONTRADICTORY))
    assert result["prior_advanced_lines"] == ([], "conflict", ["c3", "c4"])
    # the setting is not narrowed by an empty prior-lines domain: no relation fires on it
    assert result["setting"] == (list(SETTINGS), "unnarrowed", [])


def test_a_default_that_contradicts_the_evidence_is_a_conflict():
    """Positive: stated one prior line, and a default saying none: the known level keeps the stated line, the
    interpolated level is empty, and both causes are named, the known level's first. Negative: without the
    default's word, nothing is a conflict."""
    evidence = [
        ("inclusion", "prior_lines", ("1",), "advanced", "c1"),
        ("inclusion", "setting_word", ("x",), "", "c2"),
    ]
    rows = resolve(evidence, relations=no_prior_lines_default())
    assert rows["prior_advanced_lines"]["domain"] == ("1",)
    assert review_coordinates(rows)["prior_advanced_lines"] == (
        [],
        "conflict",
        ["c1", "no_prior_lines_when_named"],
    )
    quiet = review_coordinates(resolve(evidence[:1], relations=no_prior_lines_default()))
    assert quiet["prior_advanced_lines"] == (["1"], "resolved", ["c1"])
    assert not [name for name, (_, state, _) in quiet.items() if state == "conflict"]


def test_a_proposals_conflict_is_never_the_trials():
    rows = resolve(PROPOSAL_CONFLICT)
    assert [p["state"] for p in rows["setting"]["proposals"]] == ["conflict"]
    assert review_coordinates(rows)["setting"] == (
        ["advanced_previously_treated", "maintenance"],
        "unresolved",
        ["previously_treated_when_prior_advanced_therapy_required"],
    )


def flags(rows):
    view = {"drugs": [], "coordinates": rows, "observations": {}, "coverage": {"markers": []}}
    return [(kind, element, evidence) for kind, element, _why, _p, evidence, _q, _o in review_flags(view, [])]


def test_the_review_queue_raises_the_conflicts_of_the_levels_built_on():
    """Positive: a default contradicting the stated evidence, and evidence contradicting itself, each raise
    one coordinate_conflict naming what removed values. Negative: a proposal's conflict, and a trial the first
    line default narrows, raise none."""
    evidence = [
        ("inclusion", "prior_lines", ("1",), "advanced", "c1"),
        ("inclusion", "setting_word", ("x",), "", "c2"),
    ]
    assert flags(resolve(evidence, relations=no_prior_lines_default())) == [
        ("coordinate_conflict", "prior_advanced_lines", ["c1", "no_prior_lines_when_named"])
    ]
    assert flags(resolve(CONTRADICTORY)) == [("coordinate_conflict", "prior_advanced_lines", ["c3", "c4"])]
    assert flags(resolve(PROPOSAL_CONFLICT)) == []
    assert flags(resolve(FIRST_LINE)) == []
