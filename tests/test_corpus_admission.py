"""Corpus admission preserves known features while withholding pending interpretations per consumer."""

from __future__ import annotations

import copy

import pytest

from TrialLedger.layer2 import corpus_admission as c
from TrialLedger.layer2 import expectations, nearmiss, profile


def standing(status="known", resolution="resolved"):
    return {
        "status": status,
        "resolution": resolution,
        "basis": ["invented:explicit-standing-not-clinical-evidence"],
    }


def trial(identity="A", *, accepted=True, **values):
    item = {
        "id": identity,
        "sponsor": "invented-sponsor-" + identity,
        "stratum": "invented-set",
        "elements": ["inclusion:age=adult"],
        "basis": ["invented:trial-context"],
        "typed": True,
        "classes": ["invented-class"],
        "class_unresolved": False,
        "setting_domain": ["invented-setting"],
        "eligibility_content": "present",
        "coverage": {},
        "representation": {"setting": "invented-setting"},
        "predicates": {"PS": "0|1"},
        "start_year": "2020",
    }
    if accepted:
        item["standing"] = standing()
    item.update(values)
    return item


def feature_rows(result):
    return {row["element"]: row for row in result["frequency"]}


def test_pending_only_element_stays_visible_and_no_consumer_admits_it():
    request = [trial(accepted=False)]
    before = copy.deepcopy(request)
    result = c.prepare(request, [("invented-setting", "invented-class")])
    assert request == before
    row = feature_rows(result)["inclusion:age=adult"]
    assert row["stating"] == row["absence_established"] == 0
    assert (row["lower"], row["upper"], row["surprisal_bits"]) == (0.0, 1.0, None)
    assert row["pending_stating"] == row["unresolved_pending"] == row["unresolved"] == 1
    assert result["association_trials"] == result["pairs"] == []
    assert result["association_abstentions"][0]["code"] == "pending_support"
    assert result["near_miss_abstentions"][0]["trial"] == "A"
    assert result["occupancy"][0] == {
        "setting": "invented-setting",
        "class": "invented-class",
        "occupants": 0,
        "possible": 1,
        "state": "unknown",
    }
    assert result["pending"][0]["basis"] == request[0]["basis"]


def test_accepted_features_still_reach_all_existing_low_level_consumers():
    a, b = trial(), trial("B", predicates={"PS": "0|2"})
    result = c.prepare([a, b], [("invented-setting", "invented-class")])
    assert result["pending"] == result["association_abstentions"] == result["near_miss_abstentions"] == []
    assert feature_rows(result)["inclusion:age=adult"]["stating"] == 2
    assert nearmiss.near_misses(result["pairs"])[0][:5] == ("A", "B", "PS", "0|1", "0|2")
    assert result["occupancy"][0]["occupants"] == 2
    assert result["occupancy"][0]["state"] == "occupied"


def test_independent_known_age_survives_pending_performance_status():
    item = trial(
        elements=["inclusion:age=adult", "inclusion:PS=0|1"],
        feature_standings={"elements": {"inclusion:PS=0|1": standing("proposed")}},
    )
    result = c.prepare([item], [])
    rows = feature_rows(result)
    assert rows["inclusion:age=adult"]["stating"] == 1
    assert rows["inclusion:age=adult"]["lower"] == rows["inclusion:age=adult"]["upper"] == 1.0
    assert rows["inclusion:PS=0|1"]["stating"] == 0
    assert rows["inclusion:PS=0|1"]["pending_stating"] == 1
    assert result["trials"][0][4] == ["inclusion:age=adult"]
    assert result["association_trials"] == []
    pending = [row for row in result["pending"] if row["feature"] == ["elements", "inclusion:PS=0|1"]]
    assert pending[0]["value"] == "inclusion:PS=0|1"
    assert pending[0]["standing"]["status"] == "proposed"


def test_explicit_known_feature_overrides_omitted_trial_standing_without_promoting_siblings():
    item = trial(
        accepted=False,
        elements=["inclusion:age=adult", "inclusion:PS=0|1"],
        feature_standings={"elements": {"inclusion:age=adult": standing()}},
    )
    rows = {row["element"]: row for row in c.frequency([item])}
    assert rows["inclusion:age=adult"]["stating"] == 1
    assert rows["inclusion:PS=0|1"]["stating"] == 0
    assert rows["inclusion:PS=0|1"]["unresolved_pending"] == 1


@pytest.mark.parametrize(
    "status,resolution",
    [
        ("proposed", "resolved"),
        ("interpolated", "resolved"),
        ("known", "unresolved"),
        ("known", "partially_resolved"),
        ("known", "conflicting"),
    ],
)
def test_only_known_resolved_support_counts_as_corpus_fact(status, resolution):
    rows = c.frequency([trial(standing=standing(status, resolution))])
    assert rows[0]["stating"] == 0
    assert rows[0]["pending_stating"] == 1


def test_primary_endpoint_has_separate_pending_statement_bounds():
    accepted = trial(elements=["primary:invented-endpoint"])
    pending = trial("B", accepted=False, elements=["primary:invented-endpoint"])
    row = c.frequency([accepted, pending])[0]
    assert row["stating"] == 1 and row["statement_rate"] == 0.5
    assert row["lower"] is row["upper"] is row["unresolved"] is row["unresolved_pending"] is None
    assert row["pending_stating"] == 1
    assert (row["pending_statement_lower"], row["pending_statement_upper"]) == (0.5, 1.0)
    only_pending = c.frequency([pending])[0]
    assert only_pending["surprisal_bits"] is None and only_pending["stating"] == 0
    assert (only_pending["pending_statement_lower"], only_pending["pending_statement_upper"]) == (0.0, 1.0)


def test_pending_reading_and_source_abbreviation_are_separate_silence_reasons():
    accepted = trial()
    pending = trial(
        "B",
        elements=["inclusion:age=adult"],
        feature_standings={"elements": {"inclusion:age=adult": standing("proposed")}},
    )
    abbreviated = trial("C", elements=["inclusion:other=yes"], coverage={"inclusion": "abbreviation_stated"})
    row = feature_rows(c.prepare([accepted, pending, abbreviated], []))["inclusion:age=adult"]
    assert row["stating"] == 1 and row["unresolved"] == 2
    assert row["unresolved_pending"] == row["unresolved_abbreviated"] == 1
    assert row["unresolved_untyped"] == row["unresolved_unspecified"] == 0


@pytest.mark.parametrize("field", ["classes", "typed", "eligibility_content", "coverage"])
def test_pending_association_input_abstains_only_its_stratum(field):
    pending = trial(feature_standings={field: standing("proposed")})
    safe = trial("B", stratum="independent-stratum")
    result = c.prepare([pending, safe], [])
    assert [row[0] for row in result["association_trials"]] == ["B"]
    assert result["association_abstentions"][0]["stratum"] == "invented-set"
    assert result["association_abstentions"][0]["features"][0]["feature"] == [field]
    assert feature_rows(result)["inclusion:age=adult"]["stating"] == 1


@pytest.mark.parametrize("field", ["representation", "predicates"])
def test_pending_near_miss_field_withholds_pair_without_erasing_known_frequency(field):
    key = "setting" if field == "representation" else "PS"
    pending = trial(feature_standings={field: {key: standing("proposed")}})
    accepted = trial("B", predicates={"PS": "0|2"})
    result = c.prepare([pending, accepted], [])
    assert nearmiss.near_misses(result["pairs"]) == []
    assert [row[0] for row in result["pairs"]] == ["B"]
    assert result["near_miss_abstentions"][0]["trial"] == "A"
    assert feature_rows(result)["inclusion:age=adult"]["stating"] == 2


def test_pending_setting_widens_even_single_requested_setting_without_false_occupant():
    item = trial(feature_standings={"setting_domain": standing("proposed")})
    cells = [("invented-setting", "invented-class")]
    result = c.prepare([item], cells)
    assert result["occupancy_membership"] == [
        {
            "id": "A",
            "setting_domain": ("invented-setting",),
            "setting_known": False,
            "classes": ("invented-class",),
            "classes_known": True,
        }
    ]
    assert result["occupancy"][0]["occupants"] == 0
    assert result["occupancy"][0]["possible"] == 1
    assert result["occupancy"][0]["state"] == "unknown"
    more = [("invented-setting", "invented-class"), ("other-setting", "other-class")]
    rows = c.prepare([item], more)["occupancy"]
    assert [row["state"] for row in rows] == ["unknown", "empty"]


def test_pending_classes_are_possible_in_each_requested_class_without_widening_known_setting():
    item = trial(feature_standings={"classes": standing("proposed")})
    cells = [
        ("invented-setting", "invented-class"),
        ("invented-setting", "other-class"),
        ("elsewhere", "other-class"),
    ]
    rows = c.prepare([item], cells)["occupancy"]
    assert [row["state"] for row in rows] == ["unknown", "unknown", "empty"]


@pytest.mark.parametrize(
    "setting_known,classes_known,expected",
    [
        (True, True, ["occupied", "empty", "empty", "empty"]),
        (False, True, ["unknown", "empty", "unknown", "empty"]),
        (True, False, ["unknown", "unknown", "empty", "empty"]),
        (False, False, ["unknown", "unknown", "unknown", "unknown"]),
    ],
)
def test_occupancy_keeps_known_and_pending_dimensions_independent(setting_known, classes_known, expected):
    item = trial(
        feature_standings={
            "setting_domain": standing() if setting_known else standing("proposed"),
            "classes": standing() if classes_known else standing("proposed"),
        }
    )
    cells = [
        ("invented-setting", "invented-class"),
        ("invented-setting", "class-B"),
        ("setting-Y", "invented-class"),
        ("setting-Y", "class-B"),
    ]
    result = c.prepare([item], cells)
    assert [row["state"] for row in result["occupancy"]] == expected
    assert result["occupancy_membership"][0]["setting_known"] is setting_known
    assert result["occupancy_membership"][0]["classes_known"] is classes_known


def test_pending_setting_does_not_erase_known_class_for_single_requested_setting():
    item = trial(feature_standings={"setting_domain": standing("proposed")})
    cells = [("invented-setting", "invented-class"), ("invented-setting", "class-B")]
    result = c.prepare([item], cells)
    assert [row["state"] for row in result["occupancy"]] == ["unknown", "empty"]
    assert [row["possible"] for row in result["occupancy"]] == [1, 0]


def test_pending_element_blocks_association_instead_of_becoming_outside_absence():
    inside = [trial("in" + str(i), elements=["inclusion:X=yes"]) for i in range(5)]
    outside = [
        trial(
            "out" + str(i),
            classes=["other-class"],
            elements=["inclusion:X=yes"],
            feature_standings={"elements": {"inclusion:X=yes": standing("proposed")}},
        )
        for i in range(2)
    ]
    result = c.prepare(inside + outside, [])
    assert profile.mechanism_rows(result["association_trials"]) == []
    assert result["association_abstentions"][0]["trials"] == ["out0", "out1"]
    row = feature_rows(result)["inclusion:X=yes"]
    assert row["stating"] == 5 and row["pending_stating"] == row["unresolved_pending"] == 2


def test_known_support_with_unknown_class_membership_abstains_the_comparison_stratum():
    inside = [trial("inside" + str(i), elements=["inclusion:X=yes"]) for i in range(5)]
    outside = trial("outside", classes=["class-B"], elements=[])
    unknown = trial(
        "unknown", classes=["candidate-class"], class_unresolved=True, elements=["inclusion:X=yes"]
    )
    source = inside + [outside, unknown]
    original = copy.deepcopy(source)
    result = c.prepare(source, [])
    assert source == original
    assert result["association_trials"] == []
    assert profile.mechanism_rows(result["association_trials"]) == []
    abstention = result["association_abstentions"][0]
    assert abstention["stratum"] == "invented-set" and abstention["trials"] == ["unknown"]
    blocker = abstention["features"][0]
    assert blocker["code"] == "class_membership_unresolved"
    assert blocker["value"] is True and blocker["classes"] == ["candidate-class"]
    assert blocker["standing"] == unknown["standing"] and blocker["basis"] == unknown["basis"]
    assert feature_rows(result)["inclusion:X=yes"]["stating"] == 6


def test_known_empty_setting_domain_refuses_only_when_occupancy_is_requested():
    item = trial(setting_domain=[])
    assert c.prepare([item], [])["occupancy"] == []
    with pytest.raises(ValueError, match="^occupancy_requires_nonempty_setting_domains$"):
        c.prepare([item], [("invented-setting", "invented-class")])


@pytest.mark.parametrize("omitted", [False, True])
def test_pending_empty_or_omitted_setting_domain_widens_instead_of_refusing(omitted):
    item = trial(accepted=False, setting_domain=[])
    if omitted:
        del item["setting_domain"]
    result = c.prepare([item], [("invented-setting", "invented-class")])
    assert result["occupancy"][0]["state"] == "unknown"
    assert result["occupancy"][0]["occupants"] == 0 and result["occupancy"][0]["possible"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "standing-null",
        "overrides-null",
        "override-unknown",
        "element-missing",
        "predicate-missing",
        "representation-null",
        "scalar-null",
        "nested-null",
        "bad-status",
        "empty-basis",
        "missing-scalar",
    ],
)
def test_malformed_or_mistargeted_standings_refuse_instead_of_inheriting(mutation):
    item = trial()
    if mutation == "standing-null":
        item["standing"] = None
    elif mutation == "overrides-null":
        item["feature_standings"] = None
    elif mutation == "override-unknown":
        item["feature_standings"] = {"certified": standing()}
    elif mutation == "element-missing":
        item["feature_standings"] = {"elements": {"missing": standing()}}
    elif mutation == "predicate-missing":
        item["feature_standings"] = {"predicates": {"missing": standing()}}
    elif mutation == "representation-null":
        item["feature_standings"] = {"representation": None}
    elif mutation == "scalar-null":
        item["feature_standings"] = {"typed": None}
    elif mutation == "nested-null":
        item["feature_standings"] = {"elements": {"inclusion:age=adult": None}}
    elif mutation == "bad-status":
        item["standing"] = standing("confirmed")
    elif mutation == "empty-basis":
        item["standing"]["basis"] = []
    else:
        del item["typed"]
        item["feature_standings"] = {"typed": standing()}
    with pytest.raises(ValueError):
        c.prepare([item], [])


def test_empty_input_and_detached_ledgers_are_stable():
    assert c.prepare([], [])["frequency"] == []
    item = trial(accepted=False)
    result = c.prepare([item], [])
    result["pending"][0]["basis"].append("changed-output")
    result["admission"][0]["standing"]["basis"].append("changed-standing")
    assert item["basis"] == ["invented:trial-context"]
    assert "standing" not in item


def test_expectation_rows_inherit_or_override_without_changing_observation_states():
    rows = [("cell", "present"), ("cell", "not_documented"), ("cell", "unresolved")]
    item = {
        "basis": ["invented:expectation"],
        "standing": standing(),
        "observation_standings": [standing(), standing("proposed"), standing()],
    }
    original = copy.deepcopy((item, rows))
    result = c.expectations(item, rows)
    assert (item, rows) == original
    assert result["observations"] == [rows[0], rows[2]]
    assert result["admitted_count"] == 2
    assert result["pending"][0]["observation"] == rows[1]
    assert expectations.conditional_rarity(result["observations"], "cell", 1)[:3] == ("cell", 1.0, 1)
    omitted = c.expectations({"basis": ["invented:omitted-standing"]}, rows)
    assert omitted["observations"] == [] and len(omitted["pending"]) == 3
    assert expectations.conditional_rarity(omitted["observations"], "cell", 1)[0] == "abstain"


def test_known_observation_can_override_pending_expectation_without_promoting_others():
    rows = [("cell", "present"), ("cell", "explicitly_negated")]
    result = c.expectations(
        {"basis": ["invented:expectation"], "observation_standings": [standing(), standing("proposed")]}, rows
    )
    assert result["observations"] == [rows[0]]
    assert result["pending"][0]["observation"] == rows[1]


@pytest.mark.parametrize("overrides", [None, [], [None], [standing(), standing()]])
def test_explicit_invalid_observation_standing_arrays_never_default_to_known(overrides):
    with pytest.raises(ValueError):
        c.expectations(
            {"basis": ["invented:expectation"], "standing": standing(), "observation_standings": overrides},
            [("cell", "present")],
        )


def test_explicit_null_expectation_standing_is_not_omission():
    with pytest.raises(ValueError):
        c.expectations({"basis": ["invented"], "standing": None}, [])
