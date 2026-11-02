"""cli.request_from_flags — `trialledger landscape`'s slot flags as the request they state
(add-agent-operation 4.2).

The requests are those whose RxNav answers tests/rxnav_request_answers.json keeps.

Positive: the flags of a drug class in a condition class, with phase, status, study type and start date, state
exactly the recorded request; drugs, a class by id, a mechanism, a condition, a start range and raw
parameters are each their slot, as given; an empty value (an empty string, False, 0) is given and kept.
Negative: a flag not given is no slot, and no flag is the empty request (which request_problems refuses); a
class without a source or with a name and an id is passed on as given for request_problems to refuse, never
completed or chosen; a --param word that is not NAME=VALUE, or a name given twice, states no request.
"""

import json
from pathlib import Path

import pytest

from TrialLedger.cli import FLAG_SLOTS, request_from_flags
from TrialLedger.request import request_problems

DOC = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
PD1_IN_LUNG, BY_NAME, ALK_ATC = DOC["requests"][:3]
NOTHING = {slot: None for slot in FLAG_SLOTS} | {
    "phase": [],
    "status": [],
    "drug": [],
    "param": [],
    "ids": [],
}
NOTHING |= {"drug_class": None, "drug_class_id": None, "class_source": None}


def flags(**given):
    return NOTHING | given


def test_the_flags_of_a_drug_class_in_a_disease_state_the_recorded_request():
    stated = flags(
        drug_class="Programmed Death Receptor-1 Blocking Antibody",
        class_source="EPC",
        condition_class="Lung Neoplasms",
        phase=["PHASE3"],
        status=["RECRUITING"],
        study_type="INTERVENTIONAL",
        start_from="2015-01-01",
    )
    assert request_from_flags(stated) == ("ok", PD1_IN_LUNG, [])
    assert request_problems(PD1_IN_LUNG) == ("ok", [])


def test_each_flag_is_its_slot_as_given():
    stated = flags(
        drug=["Keytruda", "osimertinib", "osimertinib mesylate", "XB-1 zzq"], start_to="2024-12-31"
    )
    assert request_from_flags(stated) == ("ok", BY_NAME, [])
    assert request_from_flags(flags(drug_class_id="L01ED", class_source="ATC")) == ("ok", ALK_ATC, [])
    code, request, _ = request_from_flags(
        flags(mechanism="PD-1", condition="asthma", param=["query.term=biomarker", "filter.geo=a=b"])
    )
    assert (code, request) == (
        "ok",
        {
            "mechanism": "PD-1",
            "condition": "asthma",
            "params": {"query.term": "biomarker", "filter.geo": "a=b"},
        },
    )


def test_an_empty_value_given_is_kept():
    assert request_from_flags(flags(condition="", drug_class="")) == (
        "ok",
        {"condition": "", "drug_class": {"name": ""}},
        [],
    )
    assert request_from_flags(flags(study_type=0, mechanism=False)) == (
        "ok",
        {"mechanism": False, "study_type": 0},
        [],
    )


def test_no_flag_is_the_empty_request():
    assert request_from_flags(NOTHING) == ("ok", {}, [])
    assert request_from_flags({}) == ("ok", {}, [])
    assert request_problems({}) == ("empty_request", [])


def test_a_class_is_passed_on_as_given_never_completed():
    assert request_from_flags(flags(drug_class="Kinase Inhibitor")) == (
        "ok",
        {"drug_class": {"name": "Kinase Inhibitor"}},
        [],
    )
    both = flags(drug_class="Kinase Inhibitor", drug_class_id="N0000175605", class_source="EPC")
    code, request, _ = request_from_flags(both)
    assert request == {"drug_class": {"name": "Kinase Inhibitor", "id": "N0000175605", "source": "EPC"}}
    assert request_problems(request) == ("malformed_value", ["drug_class"])


@pytest.mark.parametrize(
    ("words", "refused"),
    [
        (["query.term"], ("params_not_name_value", {}, ["query.term"])),
        (["=x", "query.term=y"], ("params_not_name_value", {}, ["=x"])),
        (["query.term=a", "query.term=b"], ("params_duplicate", {}, ["query.term"])),
    ],
)
def test_a_param_that_is_not_name_value_states_no_request(words, refused):
    assert request_from_flags(flags(drug=["Keytruda"], param=words)) == refused


def test_trials_by_number_are_the_registrys_filter_ids():
    """--ids (the release check, 2026-11-01: trials by number through landscape). Positive: the values are
    filter.ids, joined by "," as given, beside any other --param and any slot; a request of numbers alone is
    one request_problems accepts. Negative: no --ids, or an empty list, adds nothing; filter.ids given both as
    --ids and as --param is refused, neither chosen; a malformed number is passed on, never dropped."""
    numbers = flags(ids=["NCT04852770,NCT01827384", "NCT01086644"])
    request = {"params": {"filter.ids": "NCT04852770,NCT01827384,NCT01086644"}}
    assert request_from_flags(numbers) == ("ok", request, [])
    assert request_problems(request) == ("ok", [])
    code, both, _ = request_from_flags(flags(ids=["NCT1"], param=["query.term=x"], phase=["PHASE3"]))
    assert (code, both) == ("ok", {"phase": ["PHASE3"], "params": {"query.term": "x", "filter.ids": "NCT1"}})
    assert request_from_flags(flags(ids=[])) == ("ok", {}, [])
    assert request_from_flags(flags(ids=None, drug=["a"])) == ("ok", {"drug": ["a"]}, [])
    twice = flags(ids=["NCT04852770"], param=["filter.ids=NCT01827384"])
    assert request_from_flags(twice) == ("params_duplicate", {}, ["filter.ids"])
    assert request_from_flags(flags(ids=["NCT12x"]))[1] == {"params": {"filter.ids": "NCT12x"}}
