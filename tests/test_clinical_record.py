"""Clinical source content is preserved without speculative reading or selection."""

import copy

from records import ongoing_study

from TrialLedger import landscape


def test_unmapped_outcome_and_time_frame_stay_literal_without_a_clinical_recognizer():
    study = copy.deepcopy(ongoing_study())
    study["protocolSection"]["outcomesModule"] = {
        "primaryOutcomes": [{"measure": "Unmapped assessment XYZ", "timeFrame": "At investigator discretion"}]
    }
    [outcome] = landscape.study_extract(study)["registered_outcomes"]
    assert outcome["measure"] == "Unmapped assessment XYZ"
    assert outcome["time_frame"] == "At investigator discretion"
    assert "endpoint_classes" not in outcome
    assert "time_points" not in outcome


def test_comparator_and_experimental_interventions_keep_their_own_source_class_answers():
    study = copy.deepcopy(ongoing_study())
    study["protocolSection"]["armsInterventionsModule"] = {
        "interventions": [{"type": "DRUG", "name": "Alpha"}, {"type": "DRUG", "name": "Beta"}]
    }
    answers = {
        "Alpha": {"classes": [["A", "Alpha class", "has_epc", "FDA"]], "codes": {"EPC": "classified"}},
        "Beta": {"classes": [["B", "Beta class", "has_epc", "FDA"]], "codes": {"EPC": "classified"}},
    }
    interventions = landscape.study_extract(study, answers)["interventions"]
    for intervention, letter in zip(interventions, ("A", "B"), strict=True):
        reading = intervention["drug_class"]
        assert reading["status"] == "known"
        assert reading["result"]["classes"] == answers[intervention["name"]]["classes"]
        assert reading["result"]["classes"][0][0] == letter


def test_intervention_prose_cannot_supply_a_drug_class_when_no_source_lookup_does():
    study = copy.deepcopy(ongoing_study())
    study["protocolSection"]["armsInterventionsModule"] = {
        "interventions": [{"type": "DRUG", "name": "Alpha", "description": "EGFR inhibitor after platinum"}]
    }
    [intervention] = landscape.study_extract(study, {})["interventions"]
    assert intervention["drug_class"]["status"] == "unresolved"
    assert intervention["drug_class"]["result"]["classes"] == []


def test_collection_presence_distinguishes_source_silence_empty_and_malformed_at_each_scope():
    templates = ["results.measures[].classes[].values[].number"]
    assert landscape.collection_presence({}, templates) == {"/results/measures": "not_stated"}
    assert landscape.collection_presence({"results": {"measures": []}}, templates) == {
        "/results/measures": "stated_empty"
    }
    assert landscape.collection_presence({"results": {"measures": "not an array"}}, templates) == {
        "/results/measures": "malformed"
    }
    states = landscape.collection_presence(
        {"results": {"measures": [{"classes": []}, {}, {"classes": [{"values": [0]}]}]}}, templates
    )
    assert states == {
        "/results/measures": "stated",
        "/results/measures/0/classes": "stated_empty",
        "/results/measures/1/classes": "not_stated",
        "/results/measures/2/classes": "stated",
        "/results/measures/2/classes/0/values": "stated",
    }
    assert landscape.collection_presence({"results": None}, templates) == {"/results/measures": "malformed"}
    assert landscape.collection_presence({}, []) == {}
