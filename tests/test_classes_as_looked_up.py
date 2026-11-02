"""reading.classes_as_looked_up — a drug RxClass was never asked about is not_looked_up, never "no class" and
never "lookup failed" (add-agent-operation 4.2: a relay run asks RxNav nothing after the pull).

The answers are classes.lookup's, over RxClass byDrugName bodies of the live service's shape (an EPC for
pembrolizumab, nothing for an unknown name, a 503).

Positive: a drug none of whose names was asked is not_looked_up with no class and no resolving name, whatever
classes.drug_class said of it (lookup_failed over an empty cache); the reading of a population with no answers
names every experimental drug not_looked_up and reads no class from its own entry in RxClass's place.
Negative: a drug with any name answered keeps classes.drug_class's answer unchanged (classified, unresolved,
lookup_failed), so a run that looked its names up reads as it always did; an answer recorded for another
name says nothing of this drug.
"""

import pytest
from records import results_study

from TrialLedger import classes
from TrialLedger.reading import classes_as_looked_up, read_population

EPC = {
    "rxclassDrugInfoList": {
        "rxclassDrugInfo": [
            {
                "minConcept": {"rxcui": "1547545", "name": "pembrolizumab", "tty": "IN"},
                "rxclassMinConceptItem": {
                    "classId": "N0000191260",
                    "className": "Programmed Death Receptor-1 Blocking Antibody",
                    "classType": "EPC",
                },
                "rela": "has_epc",
                "relaSource": "DAILYMED",
            }
        ]
    }
}


def rxclass(url, params):
    if url == classes.RXNAV_VERSION:  # the release, asked once a lookup batch (classes.lookup's warrant)
        return 200, {"version": "05-Oct-2026", "apiVersion": "3.1.356"}
    if params["drugName"] == "pembrolizumab" and params["relaSource"] == "DAILYMED":
        return 200, EPC
    if params["drugName"] == "flaky":
        return 503, None
    return 200, {}


def answered(*names):
    return classes.lookup(list(names), get=rxclass, sleep=lambda seconds: None)


def test_a_drug_no_name_of_which_was_asked_is_not_looked_up():
    found = classes.drug_class({}, ["Keytruda", "pembrolizumab"])
    assert found == ("lookup_failed", [], "")
    assert classes_as_looked_up(["Keytruda", "pembrolizumab"], {}, found) == ("not_looked_up", [], "")


def test_an_answer_for_another_name_says_nothing_of_this_drug():
    answers = answered("pembrolizumab")
    found = classes.drug_class(answers, ["XB-1"])
    assert classes_as_looked_up(["XB-1"], answers, found) == ("not_looked_up", [], "")


def test_a_drug_with_no_name_is_not_looked_up():
    assert classes_as_looked_up([], {}, ("unresolved", [], "")) == ("not_looked_up", [], "")


@pytest.mark.parametrize(
    ("names", "state"),
    [
        (["Keytruda", "pembrolizumab"], "classified"),
        (["XB-1"], "unresolved"),
        (["flaky"], "lookup_failed"),
    ],
)
def test_a_drug_with_a_name_answered_keeps_its_answer(names, state):
    answers = answered("Keytruda", "pembrolizumab", "XB-1", "flaky")
    found = classes.drug_class(answers, names)
    assert found[0] == state
    assert classes_as_looked_up(names, answers, found) == found


def test_one_name_answered_is_enough_to_keep_the_answer():
    answers = answered("pembrolizumab")
    found = classes.drug_class(answers, ["Keytruda", "pembrolizumab"])
    assert found[0] == "classified"
    assert classes_as_looked_up(["Keytruda", "pembrolizumab"], answers, found) == found


def test_a_reading_with_no_answers_names_an_experimental_drug_not_looked_up():
    study = results_study()
    view = read_population([study], {})["views"][0]
    assert view["drugs"] == [("Testamab", "not_looked_up", [], "")]
    assert view["drug_axes"][0]["identity"] == "not_looked_up"
    answered_view = read_population([study], answered("Testamab", "TM-1"))["views"][0]
    assert answered_view["drugs"] == [("Testamab", "unresolved", [], "")]


def test_a_class_the_drugs_own_entry_states_is_read_whether_or_not_rxclass_was_asked():
    study = results_study()
    entry = study["protocolSection"]["armsInterventionsModule"]["interventions"][0]
    entry["description"] = "Testamab is an anti-PD-1 antibody"
    stated = [("Testamab", "stated_by_record", ["stated: PD-1"], "description")]
    assert read_population([study], {})["views"][0]["drugs"] == stated
    assert read_population([study], answered("Testamab", "TM-1"))["views"][0]["drugs"] == stated
