"""run_checks — the shell that gathers each check's facts from one record.

Positive: a consistent record raises no conflict; by default only the approved checks run, all seventeen with
include_proposed, in the list's order; each check fires on a record that breaks its relation and names the
fields and values involved; a blank at-risk count takes the group's table total; a group's number not
completed is STARTED minus COMPLETED when no NOT COMPLETED milestone states it.
Negative: a check never changes the record; a check whose input is missing is never consistent; a check that
does not run is never gathered, so its malformed input cannot stop the others; a malformed input is named and
not checkable, never consistent; a stated count that is not a whole number is never replaced by a derived
one; a reference that matches nothing while some definition is unknown is not checkable, never a conflict.
"""

import copy

import pytest
from records import results_study

from TrialLedger.checks import APPROVED, CHECKS, run_checks


def outcomes(study, include_proposed=True):
    return {r.check_id: r for r in run_checks(study, include_proposed=include_proposed)}


def test_a_consistent_record_raises_no_conflict():
    assert all(r.outcome != "conflict" for r in run_checks(results_study(), include_proposed=True))


def test_only_approved_checks_run_by_default():
    assert [r.check_id for r in run_checks(results_study())] == [c.id for c in CHECKS if c.id in APPROVED]
    assert [r.check_id for r in run_checks(results_study(), include_proposed=True)] == [c.id for c in CHECKS]


def test_a_blank_at_risk_count_takes_the_group_total():
    study = results_study()
    stats = study["resultsSection"]["adverseEventsModule"]["otherEvents"][0]["stats"][1]
    assert "numAtRisk" not in stats
    stats["numAffected"] = 61
    result = outcomes(study)["ae_affected_within_at_risk"]
    assert result.outcome == "conflict"
    assert "61 affected > 60 at risk (group_total)" in result.detail


def set_path(study, keys, value):
    node = study
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value


P = "protocolSection"
R = "resultsSection"


@pytest.mark.parametrize(
    "check_id, edits, named",
    [
        (
            "closed_completion_actual",
            [((P, "statusModule", "completionDateStruct", "type"), "ESTIMATED")],
            "completionDateStruct.type=ESTIMATED",
        ),
        (
            "closed_primary_completion_actual",
            [
                ((P, "statusModule", "overallStatus"), "TERMINATED"),
                ((P, "statusModule", "primaryCompletionDateStruct", "type"), "ESTIMATED"),
            ],
            "overallStatus=TERMINATED",
        ),
        (
            "withdrawn_actual_enrollment_zero",
            [((P, "statusModule", "overallStatus"), "WITHDRAWN")],
            "enrollmentInfo.count=120",
        ),
        (
            "phase_interventional_only",
            [((P, "designModule", "studyType"), "OBSERVATIONAL")],
            "phases=['PHASE2']",
        ),
        (
            "results_flag_first_submit",
            [(("hasResults",), False)],
            "statusModule.resultsFirstSubmitDate=2020-05-01",
        ),
        (
            "recruiting_site_recruiting_study",
            [((P, "contactsLocationsModule", "locations", 1, "status"), "RECRUITING")],
            "1 RECRUITING",
        ),
        (
            "arm_interventions_declared",
            [((P, "armsInterventionsModule", "armGroups", 0, "interventionNames"), ["Drug: Unknownab"])],
            "arm 'Testamab' names 'Drug: Unknownab'",
        ),
        (
            "intervention_arms_defined",
            [((P, "armsInterventionsModule", "interventions", 1, "armGroupLabels"), ["Ghost arm"])],
            "intervention 'Placebo' names arm 'Ghost arm'",
        ),
        (
            "ae_counts_name_groups",
            [((R, "adverseEventsModule", "seriousEvents", 0, "stats", 1, "groupId"), "EG009")],
            "group EG009",
        ),
        (
            "ae_affected_within_at_risk",
            [((R, "adverseEventsModule", "seriousEvents", 0, "stats", 0, "numAffected"), 61)],
            "61 affected > 60 at risk (stated)",
        ),
        (
            "ae_event_within_group_total",
            [((R, "adverseEventsModule", "seriousEvents", 0, "stats", 0, "numAffected"), 7)],
            "7 affected > group total 6",
        ),
        (
            "ae_events_at_least_affected",
            [((R, "adverseEventsModule", "seriousEvents", 0, "stats", 0, "numEvents"), 2)],
            "2 events < 3 affected",
        ),
        (
            "ae_group_totals_within_at_risk",
            [((R, "adverseEventsModule", "eventGroups", 1, "deathsNumAffected"), 61)],
            "group EG001 deaths: 61 affected > 60 at risk",
        ),
        (
            "flow_reasons_account",
            [
                (
                    (
                        R,
                        "participantFlowModule",
                        "periods",
                        0,
                        "dropWithdraws",
                        0,
                        "reasons",
                        0,
                        "numSubjects",
                    ),
                    "4",
                )
            ],
            "reasons sum to 6, not completed 5",
        ),
        (
            "age_limits_ordered",
            [((P, "eligibilityModule", "minimumAge"), "70 Years")],
            "minimumAge=70 Years; maximumAge=65 Years",
        ),
        (
            "start_before_primary_completion",
            [((P, "statusModule", "startDateStruct", "date"), "2019-07")],
            "startDateStruct.date=2019-07",
        ),
        (
            "primary_completion_before_completion",
            [((P, "statusModule", "primaryCompletionDateStruct", "date"), "2020-01")],
            "primaryCompletionDateStruct.date=2020-01",
        ),
    ],
)
def test_each_check_fires_and_names_what_it_read(check_id, edits, named):
    study = results_study()
    for keys, value in edits:
        set_path(study, keys, value)
    result = outcomes(study)[check_id]
    assert result.outcome == "conflict", result
    assert named in result.detail


def test_a_check_never_changes_the_record():
    study = results_study()
    study["protocolSection"]["statusModule"]["completionDateStruct"]["type"] = "ESTIMATED"
    before = copy.deepcopy(study)
    run_checks(study, include_proposed=True)
    assert study == before


def test_a_missing_input_is_never_consistent():
    study = results_study()
    del study["protocolSection"]["statusModule"]["completionDateStruct"]["type"]
    del study["protocolSection"]["eligibilityModule"]["maximumAge"]
    results = outcomes(study)
    assert results["closed_completion_actual"].outcome == "not_checkable"
    assert results["age_limits_ordered"].outcome == "not_checkable"


FLOW = ("resultsSection", "participantFlowModule", "periods")


def milestones(study):
    return [m for period in study[FLOW[0]][FLOW[1]][FLOW[2]] for m in period["milestones"]]


def test_a_malformed_reasons_list_is_never_consistent():
    study = results_study()
    study[FLOW[0]][FLOW[1]][FLOW[2]][0]["dropWithdraws"].append({"type": "Other", "reasons": "malformed"})
    result = outcomes(study)["flow_reasons_account"]
    assert result.outcome == "not_checkable"
    assert result.detail.startswith("malformed input: resultsSection.participantFlowModule.periods[0]")
    assert result.detail.endswith("reasons is not a list")


def test_a_stated_not_completed_count_is_never_replaced():
    study = results_study()
    stated = [m for m in milestones(study) if m["type"] == "NOT COMPLETED"]
    assert stated
    for milestone in stated:
        for achievement in milestone["achievements"]:
            achievement["numSubjects"] = "malformed"
    assert outcomes(study)["flow_reasons_account"].outcome == "not_checkable"


def test_not_completed_is_started_minus_completed_when_no_milestone_states_it():
    study = results_study()
    for period in study[FLOW[0]][FLOW[1]][FLOW[2]]:
        period["milestones"] = [m for m in period["milestones"] if m["type"] != "NOT COMPLETED"]
    assert outcomes(study)["flow_reasons_account"].outcome == "consistent"


def interventions(study):
    return study["protocolSection"]["armsInterventionsModule"]["interventions"]


def test_an_intervention_without_a_type_never_makes_a_conflict():
    study = results_study()
    for intervention in interventions(study):
        if intervention["name"] == "Testamab":
            del intervention["type"]
    result = outcomes(study)["arm_interventions_declared"]
    assert result.outcome == "not_checkable"
    assert result.detail.endswith("; 1 intervention(s) without a registry type or name")


def test_an_arm_without_a_label_never_makes_a_conflict():
    study = results_study()
    del study["protocolSection"]["armsInterventionsModule"]["armGroups"][0]["label"]
    result = outcomes(study)["intervention_arms_defined"]
    assert result.outcome == "not_checkable"
    assert result.detail.endswith("; 1 arm(s) without a label")


def test_an_event_group_without_an_id_never_makes_a_conflict():
    study = results_study()
    del study["resultsSection"]["adverseEventsModule"]["eventGroups"][0]["id"]
    assert outcomes(study)["ae_counts_name_groups"].outcome == "not_checkable"


def test_a_repeated_event_group_id_is_not_checkable():
    study = results_study()
    groups = study["resultsSection"]["adverseEventsModule"]["eventGroups"]
    groups[1]["id"] = groups[0]["id"]
    results = outcomes(study)
    for check_id in ("ae_counts_name_groups", "ae_affected_within_at_risk", "ae_event_within_group_total"):
        assert results[check_id].outcome == "not_checkable", check_id
        assert results[check_id].detail.endswith("eventGroups repeats a group id")


def test_a_check_that_does_not_run_is_never_gathered():
    study = results_study()
    interventions(study)[0]["type"] = []
    approved = run_checks(study)
    assert [r.check_id for r in approved] == [c.id for c in CHECKS if c.id in APPROVED]
    assert all(r.outcome != "conflict" for r in approved)
    result = outcomes(study)["arm_interventions_declared"]
    assert result.outcome == "not_checkable"
    assert "interventions[0].type=[] is not text" in result.detail


def test_a_malformed_status_or_phase_is_not_checkable():
    study = results_study()
    study["protocolSection"]["statusModule"]["overallStatus"] = ["COMPLETED"]
    result = outcomes(study)["closed_completion_actual"]
    assert result.outcome == "not_checkable"
    assert "overallStatus=['COMPLETED'] is not text" in result.detail
    study = results_study()
    study["protocolSection"]["designModule"]["studyType"] = "OBSERVATIONAL"
    study["protocolSection"]["designModule"]["phases"] = [None]
    assert outcomes(study)["phase_interventional_only"].outcome == "not_checkable"


def test_a_results_submission_date_that_is_not_text_is_not_checkable():
    study = results_study()
    study["protocolSection"]["statusModule"]["resultsFirstSubmitDate"] = []
    result = outcomes(study)["results_flag_first_submit"]
    assert result.outcome == "not_checkable"
    assert "resultsFirstSubmitDate=[] is not text" in result.detail


def test_a_reason_without_counts_for_a_group_is_never_a_conflict():
    study = results_study()
    del study[FLOW[0]][FLOW[1]][FLOW[2]][0]["dropWithdraws"][0]["reasons"]
    assert outcomes(study)["flow_reasons_account"].outcome == "not_checkable"


def test_a_count_stated_for_no_group_is_not_checkable():
    study = results_study()
    for milestone in milestones(study):
        if milestone["type"] == "NOT COMPLETED":
            milestone["achievements"] = [{"numSubjects": "99"}]
    result = outcomes(study)["flow_reasons_account"]
    assert result.outcome == "not_checkable"
    assert result.detail.endswith("states a count for no group")


def test_a_count_too_long_to_read_is_not_checkable_never_raised():
    study = results_study()
    study[FLOW[0]][FLOW[1]][FLOW[2]][0]["dropWithdraws"][0]["reasons"][0]["numSubjects"] = "9" * 5000
    assert outcomes(study, include_proposed=False)["flow_reasons_account"].outcome == "not_checkable"
