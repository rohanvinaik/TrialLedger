"""Independent malformed entries cannot erase already witnessed registry contradictions."""

import copy

import pytest

from TrialLedger import checks, landscape


def safety(events):
    return {
        "resultsSection": {
            "adverseEventsModule": {
                "eventGroups": [{"id": "G1", "seriousNumAtRisk": 10, "seriousNumAffected": 10}],
                "seriousEvents": events,
            }
        }
    }


def event(affected=11):
    return {"term": "invented event", "stats": [{"groupId": "G1", "numAffected": affected, "numEvents": 5}]}


@pytest.mark.parametrize(
    "malformed", [{"term": "bad", "stats": "not an array"}, "bad event", {"term": "bad", "stats": [False]}]
)
@pytest.mark.parametrize("reverse", [False, True])
def test_independent_bad_entry_never_erases_known_conflicts(malformed, reverse):
    events = [event(), malformed]
    if reverse:
        events.reverse()
    source = safety(events)
    before = copy.deepcopy(source)
    results = {r.check_id: r for r in checks.run_checks(source)}
    for key in ("ae_affected_within_at_risk", "ae_event_within_group_total", "ae_events_at_least_affected"):
        assert results[key].outcome == "conflict"
        assert "not checkable" in results[key].detail and "malformed input" in results[key].detail
    assert source == before
    reported = landscape.registry_check_reading(source)["result"]["checks"]
    assert next(r for r in reported if r["id"] == "ae_affected_within_at_risk")["outcome"] == "conflict"


def test_bad_collection_does_not_erase_conflict_in_the_other_collection():
    source = safety("malformed serious collection")
    source["resultsSection"]["adverseEventsModule"]["otherEvents"] = [event()]
    result = {r.check_id: r for r in checks.run_checks(source)}["ae_events_at_least_affected"]
    assert result.outcome == "conflict"


def test_partial_flow_retains_derived_not_completed_beside_unknown_reason_count():
    source = {
        "resultsSection": {
            "participantFlowModule": {
                "periods": [
                    {
                        "title": "invented period",
                        "milestones": [
                            {"type": "STARTED", "achievements": [{"groupId": "G1", "numSubjects": "10"}]},
                            {"type": "COMPLETED", "achievements": [{"groupId": "G1", "numSubjects": "7"}]},
                        ],
                        "dropWithdraws": [{"type": "invented reason", "reasons": [{"groupId": "G1"}]}],
                    }
                ]
            }
        }
    }
    result = {r.check_id: r for r in checks.run_checks(source)}["flow_reasons_account"]
    assert result.outcome == "not_checkable"
    calculation = result.information["calculations"][0]
    assert calculation["value"] == 3 and calculation["rule"] == "STARTED minus COMPLETED"
    assert calculation["group"] == "G1" and calculation["period"] == 0
    assert "not completed 3" in result.detail
    row = next(
        r
        for r in landscape.registry_check_reading(source)["result"]["checks"]
        if r["id"] == "flow_reasons_account"
    )
    assert row["information"]["calculations"][0] == calculation


def test_reporting_dependency_fingerprint_includes_completion_rules():
    from pathlib import Path

    from TrialLedger import landscape_warrants

    package = Path(checks.__file__).parent
    assert package / "date_possibilities.py" in landscape_warrants.derivation_files(package)


def test_negative_not_completed_difference_is_a_conflict_not_a_participant_count():
    source = {
        "resultsSection": {
            "participantFlowModule": {
                "periods": [
                    {
                        "milestones": [
                            {"type": "STARTED", "achievements": [{"groupId": "G1", "numSubjects": "2"}]},
                            {"type": "COMPLETED", "achievements": [{"groupId": "G1", "numSubjects": "3"}]},
                        ],
                        "dropWithdraws": [{"reasons": [{"groupId": "G1"}]}],
                    }
                ]
            }
        }
    }
    result = {r.check_id: r for r in checks.run_checks(source)}["flow_reasons_account"]
    assert result.outcome == "conflict"
    assert result.information["calculations"][0]["code"] == "conflict"
    assert result.information["calculations"][0]["value"] == -1
