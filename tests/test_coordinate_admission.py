"""Coordinate standing cannot promote pending readings or erase independent warranted components."""

from __future__ import annotations

from copy import deepcopy

import pytest

from TrialLedger.layer2 import coherence
from TrialLedger.layer2 import coordinate_admission as c


def row(concept, values, *, status="known", resolution="resolved", scope="", ref="source:premise"):
    return {
        "section": "inclusion",
        "concept": concept,
        "values": list(values),
        "scope": scope,
        "ref": ref,
        "standing": {"status": status, "resolution": resolution, "basis": [ref]},
    }


def tuples(given):
    return [(r["section"], r["concept"], tuple(r["values"]), r["scope"], r["ref"]) for r in given]


def test_all_known_evidence_matches_existing_typed_solver_at_every_level():
    given = [
        row("prior_lines", ["0"], scope="advanced"),
        row("extent", ["advanced"]),
        row("biomarker:EGFR", ["positive"]),
    ]
    result = c.resolve(given, tuples(given))
    assert result["coordinates"] == coherence.resolve(tuples(given))
    assert [entry["level"] for entry in result["admission"]] == ["known"] * 3
    assert [entry["code"] for entry in result["admission"]] == ["accepted"] * 3


def test_mixed_standing_preserves_known_components_and_interpolates_only_weaker_evidence():
    given = [
        row("biomarker:EGFR", ["positive"], ref="source:EGFR"),
        row("extent", ["advanced"]),
        row("prior_lines", ["0"], scope="advanced", status="interpolated", ref="default:lines"),
        row("biomarker:EGFR", ["negative"], status="proposed", ref="hypothesis:rival"),
    ]
    result = c.resolve(given, tuples(given))
    coordinates = result["coordinates"]
    assert coordinates["selection:EGFR"]["domain"] == ("positive",)
    assert coordinates["selection:EGFR"]["interpolated"]["domain"] == ("positive",)
    assert coordinates["prior_advanced_lines"]["domain"] == coherence.PRIOR_LINES
    assert coordinates["prior_advanced_lines"]["interpolated"] == {
        "domain": ("0",),
        "state": "resolved",
        "causes": [("prior_advanced_lines", ("1", "2", "3+"), "default:lines")],
    }
    assert coordinates["setting"]["domain"] == coherence.SETTINGS
    assert coordinates["setting"]["interpolated"]["domain"] == ("advanced_first_line",)
    assert result["admission"][-1]["code"] == "proposed_refused"
    assert result["admission"][-1]["level"] == "pending"


def test_missing_standing_remains_pending_and_does_not_activate_a_default():
    given = [row("prior_lines", ["0"], scope="advanced"), row("extent", ["advanced"])]
    del given[1]["standing"]
    result = c.resolve(given, tuples(given))
    assert result["coordinates"]["prior_advanced_lines"]["domain"] == ("0",)
    assert result["coordinates"]["setting"]["interpolated"]["domain"] == coherence.SETTINGS
    assert result["admission"][1]["level"] == "pending"
    assert result["admission"][1]["standing"]["basis"] == []


@pytest.mark.parametrize("resolution", ["unresolved", "partially_resolved", "conflicting"])
@pytest.mark.parametrize("status", ["known", "interpolated", "proposed"])
def test_unresolved_or_conflicting_standing_never_constrains_either_layer(status, resolution):
    given = [row("biomarker:EGFR", ["positive"], status=status, resolution=resolution)]
    result = c.resolve(given, tuples(given))
    assert result["coordinates"]["selection:EGFR"]["domain"] == coherence.STATES
    assert result["coordinates"]["selection:EGFR"]["interpolated"]["domain"] == coherence.STATES
    assert result["admission"][0]["level"] == "pending"
    expected = "proposed_refused" if status == "proposed" else "resolution_unresolved"
    assert result["admission"][0]["code"] == expected


def test_two_proposed_rivals_are_retained_separately_without_a_manufactured_conflict():
    given = [
        row("biomarker:EGFR", ["positive"], status="proposed", ref="rival:positive"),
        row("biomarker:EGFR", ["negative"], status="proposed", ref="rival:negative"),
    ]
    result = c.resolve(given, tuples(given))
    assert result["coordinates"]["selection:EGFR"]["state"] == "unnarrowed"
    assert result["coordinates"]["selection:EGFR"]["interpolated"]["state"] == "unnarrowed"
    assert [entry["ref"] for entry in result["admission"]] == ["rival:positive", "rival:negative"]


def test_interpolated_conflict_does_not_erase_known_domain_or_independent_coordinate():
    given = [
        row("biomarker:EGFR", ["positive"], ref="known:EGFR"),
        row("biomarker:EGFR", ["negative"], status="interpolated", ref="default:EGFR"),
        row("prior_lines", ["0"], scope="advanced", ref="known:lines"),
    ]
    result = c.resolve(given, tuples(given))["coordinates"]
    assert result["selection:EGFR"]["domain"] == ("positive",)
    assert result["selection:EGFR"]["interpolated"] == {
        "domain": (),
        "state": "conflict",
        "causes": [("selection:EGFR", ("positive",), "default:EGFR")],
    }
    assert result["prior_advanced_lines"]["domain"] == ("0",)
    assert result["prior_advanced_lines"]["interpolated"]["domain"] == ("0",)


def test_known_conflict_is_local_and_has_original_causes():
    given = [
        row("biomarker:EGFR", ["positive"], ref="known:positive"),
        row("biomarker:EGFR", ["negative"], ref="known:negative"),
        row("prior_lines", ["0"], scope="advanced"),
    ]
    result = c.resolve(given, tuples(given))["coordinates"]
    assert result["selection:EGFR"]["state"] == "conflict"
    assert [cause[2] for cause in result["selection:EGFR"]["causes"]] == ["known:positive", "known:negative"]
    assert result["prior_advanced_lines"]["state"] == "resolved"


def test_proposal_relations_remain_independent_after_interpolated_evidence():
    given = [
        row("resection", ["resected"], status="interpolated"),
        row("resection", ["resectable"], status="interpolated"),
    ]
    setting = c.resolve(given, tuples(given))["coordinates"]["setting"]
    assert setting["domain"] == setting["interpolated"]["domain"] == coherence.SETTINGS
    assert [proposal["domain"] for proposal in setting["proposals"]] == [
        ("adjuvant", "perioperative"),
        ("neoadjuvant", "perioperative"),
    ]


def test_inputs_and_original_pending_provenance_are_detached_and_retained():
    given = [row("biomarker:EGFR", ["positive"], status="proposed", ref="assistant:unconfirmed")]
    original = deepcopy(given)
    result = c.resolve(given, tuples(given))
    assert result["admission"][0]["evidence"] == original[0]
    assert given == original
    result["admission"][0]["evidence"]["standing"]["basis"].append("output-only")
    result["admission"][0]["standing"]["basis"].append("standing-output-only")
    assert given == original


@pytest.mark.parametrize(
    "standing",
    [
        None,
        [],
        {},
        {"status": "known", "resolution": "resolved", "basis": []},
        {"status": "invented", "resolution": "resolved", "basis": ["source"]},
        {"status": "known", "resolution": "resolved", "basis": ["source"], "approved": True},
    ],
)
def test_explicit_null_and_malformed_standing_refuse(standing):
    given = [row("biomarker:EGFR", ["positive"])]
    given[0]["standing"] = standing
    with pytest.raises(ValueError):
        c.resolve(given, tuples(given))


def test_empty_inputs_and_pairing_mismatch_do_not_silently_discard_evidence():
    assert c.resolve([], [])["coordinates"] == coherence.resolve([])
    with pytest.raises(ValueError, match="coordinate_evidence_length_mismatch"):
        c.resolve([row("prior_lines", ["0"])], [])
