"""The ledger is the record, entry by entry.

Positive: rebuilding a record from its leaves reproduces it exactly, in content and key order; every leaf
carries its location; a registered outcome's three strings are three located entries; free text is held
character for character.
Negative: no entry exists that the record does not contain; nothing is dropped, merged or rewritten.
"""

import json
from typing import Any

from records import ELIGIBILITY, leaves, ongoing_study, results_study

from TrialLedger.ledger import entries, field_path, get, location


def rebuild(entries: list[tuple[tuple[str | int, ...], Any]]) -> Any:
    """The JSON value whose leaves are `entries`: the inverse of `leaves`, the witness of the ledger's
    losslessness (production never rebuilds a record: the record is kept whole)."""
    if len(entries) == 1 and entries[0][0] == ():
        return _fresh(entries[0][1])
    root: Any = None
    for path, value in entries:
        if root is None:
            root = [] if isinstance(path[0], int) else {}
        node = root
        for depth, key in enumerate(path):
            if depth == len(path) - 1:
                _put(node, key, _fresh(value))
                break
            child = _fetch(node, key)
            if child is None:
                child = [] if isinstance(path[depth + 1], int) else {}
                _put(node, key, child)
            node = child
    return root


def _fresh(value: Any) -> Any:
    if isinstance(value, dict):
        return {}
    if isinstance(value, list):
        return []
    return value


def _fetch(node: Any, key: str | int) -> Any:
    if isinstance(node, list):
        return node[key] if isinstance(key, int) and key < len(node) else None
    return node.get(key)


def _put(node: Any, key: str | int, value: Any) -> None:
    if isinstance(node, list) and isinstance(key, int):
        if key == len(node):
            node.append(value)
        else:
            node[key] = value
    elif isinstance(node, dict) and isinstance(key, str):
        node[key] = value
    else:
        raise ValueError(f"entry key {key!r} does not fit a {type(node).__name__}: not a ledger of one value")


def test_round_trip_reproduces_the_record_exactly():
    for study in (results_study(), ongoing_study()):
        rebuilt = rebuild(leaves(study))
        assert rebuilt == study
        assert json.dumps(rebuilt) == json.dumps(study)


def test_empty_containers_survive_the_round_trip():
    study = {"a": [], "b": {}, "c": [{"d": []}], "e": None, "f": 0, "g": False, "h": ""}
    assert json.dumps(rebuild(leaves(study))) == json.dumps(study)


def test_a_bare_value_round_trips():
    assert rebuild(leaves("text")) == "text"
    assert rebuild(leaves({})) == {}


def test_entries_are_the_leaves_with_their_locations():
    study = results_study()
    ledger = list(entries(study))
    assert [(e.location, e.value) for e in ledger] == [(location(p), v) for p, v in leaves(study)]


def test_a_registered_outcome_is_three_located_entries():
    ledger = {e.location: e for e in entries(results_study())}
    base = "protocolSection.outcomesModule.primaryOutcomes[0]"
    assert ledger[f"{base}.measure"].value == "Objective response rate"
    assert ledger[f"{base}.description"].value == "Per RECIST 1.1"
    assert ledger[f"{base}.timeFrame"].value == "Week 24"


def test_free_text_is_held_character_for_character():
    ledger = {e.location: e for e in entries(results_study())}
    assert ledger["protocolSection.eligibilityModule.eligibilityCriteria"].value == ELIGIBILITY


def test_no_entry_the_record_does_not_contain():
    study = results_study()
    for entry in entries(study):
        assert entry.location
    assert len(list(entries(study))) == len(leaves(study))


def test_roles_travel_from_structure_to_every_leaf():
    ledger = {e.location: dict(e.role) for e in entries(results_study())}
    assert ledger["protocolSection.outcomesModule.secondaryOutcomes[0].timeFrame"] == {
        "outcome_type": "SECONDARY"
    }
    assert ledger["protocolSection.outcomesModule.otherOutcomes[0].measure"] == {
        "outcome_type": "OTHER_PRE_SPECIFIED"
    }
    stats = "resultsSection.adverseEventsModule.seriousEvents[0].stats[0].numAffected"
    assert ledger[stats] == {"event_table": "serious", "group": "EG000"}
    other = "resultsSection.adverseEventsModule.otherEvents[0].stats[1].numAffected"
    assert ledger[other] == {"event_table": "other", "group": "EG001"}
    measurement = (
        "resultsSection.outcomeMeasuresModule.outcomeMeasures[0].classes[0].categories[0]"
        ".measurements[1].value"
    )
    assert ledger[measurement] == {"outcome_type": "PRIMARY", "group": "OG001"}
    assert ledger["protocolSection.referencesModule.references[1].citation"] == {"reference_type": "DERIVED"}
    assert ledger["protocolSection.armsInterventionsModule.armGroups[0].description"] == {"arm": "Testamab"}
    assert ledger["protocolSection.armsInterventionsModule.interventions[0].otherNames[0]"] == {
        "intervention": "Testamab"
    }


def test_free_text_carries_no_role():
    ledger = {e.location: e for e in entries(results_study())}
    assert ledger["protocolSection.eligibilityModule.eligibilityCriteria"].role == ()
    assert ledger["protocolSection.descriptionModule.briefSummary"].role == ()


def test_field_path_drops_list_indices():
    assert field_path(("protocolSection", "armsInterventionsModule", "armGroups", 0, "label")) == (
        "protocolSection.armsInterventionsModule.armGroups.label"
    )


def test_get_never_invents():
    study = results_study()
    assert get(study, "protocolSection", "outcomesModule", "primaryOutcomes", 0, "timeFrame") == "Week 24"
    assert get(study, "protocolSection", "outcomesModule", "primaryOutcomes", 5) is None
    assert get(study, "protocolSection", "outcomesModule", "primaryOutcomes", -1) is None
    assert get(study, "protocolSection", "nope", "deeper") is None
    assert get(study, "protocolSection", 0) is None
