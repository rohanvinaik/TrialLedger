"""The supported-type matrix — a trial's type on every axis, v1's universe, and the manifest's accounts.

Positive: an interventional trial started 2010 or later is in v1's universe (B1), whatever its phase,
purpose or population; a record's coordinates are read from its own fields on every axis (phase as written,
not applicable among the values; each condition category among its MeSH terms and ancestors; children from
the standard age groups; healthy volunteers from the boolean); the declared manifest accounts for every value
of every axis, with observational studies and expanded access unsupported and named why.
Negative: an observational or expanded-access study, a start before 2010, a start after the present a run
is read at, a start date not stated or unreadable, a study type not stated or unknown are each outside the
universe by name; a field the record does not fill is NONE, never guessed; pregnancy is never read (no
registry field states it); a manifest that calls a type supported without measured results, leaves a value
out, repeats one, names an unknown axis or value, or calls one unsupported without a reason is refused.
"""

import copy

import pytest

from TrialLedger.layer2.typematrix import (
    AXIS_VALUES,
    NO_MESH,
    NONE,
    NOT_IN_REGISTRY,
    declared_manifest,
    manifest_problems,
    study_coordinates,
    universe_status,
)
from TrialLedger.registry import enum_labels


def study(study_type="INTERVENTIONAL", start="2015-03-01", **extra):
    protocol = {
        "designModule": {
            "studyType": study_type,
            "phases": ["NA"],
            "designInfo": {
                "primaryPurpose": "PREVENTION",
                "allocation": "NA",
                "interventionModel": "SINGLE_GROUP",
            },
        },
        "statusModule": {"startDateStruct": {"date": start}},
        "eligibilityModule": {"stdAges": ["CHILD", "ADULT"], "healthyVolunteers": True},
        "armsInterventionsModule": {"interventions": [{"type": "BIOLOGICAL"}, {"type": "BIOLOGICAL"}]},
    }
    found = {"protocolSection": protocol}
    found.update(extra)
    return found


def test_the_axes_come_from_the_registry_and_the_sample():
    assert "NA" in AXIS_VALUES["phase"] and "PHASE1|PHASE2" in AXIS_VALUES["phase"]
    assert AXIS_VALUES["primary_purpose"] == tuple(enum_labels("PrimaryPurpose"))
    assert len(AXIS_VALUES["primary_purpose"]) == 10
    assert NO_MESH in AXIS_VALUES["condition_category"]
    assert set(AXIS_VALUES["study_type"]) == {"INTERVENTIONAL", "OBSERVATIONAL", "EXPANDED_ACCESS"}


def test_a_vaccine_trial_in_healthy_children_has_every_coordinate():
    record = study(
        derivedSection={
            "conditionBrowseModule": {
                "meshes": [{"id": "D007239", "term": "Infections"}],
                "ancestors": [{"id": "D000001", "term": "Respiratory Tract Diseases"}],
            }
        }
    )
    assert study_coordinates(record) == {
        "phase": ["NA"],
        "intervention_type": ["BIOLOGICAL"],
        "primary_purpose": ["PREVENTION"],
        "condition_category": ["Infections", "Respiratory Tract Diseases"],
        "allocation": ["NA"],
        "intervention_model": ["SINGLE_GROUP"],
        "children": ["yes"],
        "healthy_volunteers": ["yes"],
        "pregnancy": [NOT_IN_REGISTRY],
    }


def test_what_a_record_does_not_fill_is_none_never_guessed():
    bare = {"protocolSection": {}}
    coordinates = study_coordinates(bare)
    assert coordinates["condition_category"] == [NO_MESH]
    assert coordinates["children"] == coordinates["healthy_volunteers"] == [NONE]
    assert coordinates["allocation"] == coordinates["intervention_model"] == [NONE]
    assert coordinates["pregnancy"] == [NOT_IN_REGISTRY]
    adults = study()
    adults["protocolSection"]["eligibilityModule"] = {"stdAges": ["ADULT"], "healthyVolunteers": False}
    adults["derivedSection"] = {"conditionBrowseModule": {"meshes": [{"term": "Pregnancy"}]}}
    coordinates = study_coordinates(adults)
    assert coordinates["children"] == ["no"] and coordinates["healthy_volunteers"] == ["no"]
    # MeSH terms but none of the declared categories: NONE, not NO_MESH, and pregnancy is still not read
    assert coordinates["condition_category"] == [NONE] and coordinates["pregnancy"] == [NOT_IN_REGISTRY]


@pytest.mark.parametrize(
    "record, present, code",
    [
        (study(), None, "in_universe"),
        (study(start="2010-01"), None, "in_universe"),
        (study(start="2026-11"), "2026-11-01", "in_universe"),
        (study(start="2009-12-31"), None, "before_universe"),
        (study(start="2027-02"), "2026-11-01", "after_present"),
        (study(start="2027-02"), None, "in_universe"),
        (study(start=""), None, "start_date_not_stated"),
        (study(start="March 2015"), None, "start_date_unreadable"),
        (study(start="15-03"), None, "start_date_unreadable"),
        (study("OBSERVATIONAL"), None, "observational_unsupported"),
        (study("EXPANDED_ACCESS"), None, "expanded_access_unsupported"),
        (study("REGISTRY"), None, "unknown_study_type"),
        ({"protocolSection": {}}, None, "study_type_not_stated"),
    ],
)
def test_the_universe(record, present, code):
    assert universe_status(record, present) == code


def test_the_declared_manifest_accounts_for_every_type():
    manifest = declared_manifest()
    assert manifest_problems(manifest) == ()
    statuses = {(row["axis"], row["value"]): row for row in manifest["rows"]}
    assert statuses[("study_type", "OBSERVATIONAL")]["status"] == "unsupported"
    assert "v1" in statuses[("study_type", "EXPANDED_ACCESS")]["reason"]
    assert statuses[("study_type", "INTERVENTIONAL")]["status"] == "unmeasured"
    assert statuses[("phase", "NA")]["status"] == "unmeasured"
    assert len(manifest["rows"]) == sum(len(values) for values in AXIS_VALUES.values())


def test_an_unaccountable_manifest_is_refused():
    manifest = declared_manifest()
    rows = manifest["rows"]
    broken = copy.deepcopy(manifest)
    broken["rows"][0]["status"] = "supported"  # no measured results cited
    broken["rows"][1]["status"] = "unsupported"  # no reason
    broken["rows"][1]["reason"] = ""
    broken["rows"].append(dict(rows[2]))
    broken["rows"].append({**rows[2], "value": "PHASE5"})
    broken["rows"].append({**rows[2], "axis": "sponsor"})
    broken["rows"].append({**rows[2], "status": "probably"})
    broken["rows"].append({"axis": "phase"})
    dropped = (rows[-1]["axis"], rows[-1]["value"])
    del broken["rows"][len(rows) - 1]
    found = manifest_problems(broken)
    assert ("supported_without_evidence", rows[0]["axis"], rows[0]["value"]) in found
    assert ("unsupported_without_reason", rows[1]["axis"], rows[1]["value"]) in found
    assert ("duplicate_row", rows[2]["axis"], rows[2]["value"]) in found
    assert ("unknown_value", rows[2]["axis"], "PHASE5") in found
    assert ("unknown_axis", "sponsor", rows[2]["value"]) in found
    assert ("unknown_status", rows[2]["axis"], rows[2]["value"]) in found
    assert ("wrong_fields", "phase", "") in found
    assert ("missing_row", *dropped) in found
    supported = copy.deepcopy(manifest)
    phase_na = next(row for row in supported["rows"] if (row["axis"], row["value"]) == ("phase", "NA"))
    phase_na.update(status="supported", evidence="evaluation:2027-01-confirmation")
    assert manifest_problems(supported) == ()
    assert manifest_problems({}) == (("no_rows", "", ""),)
