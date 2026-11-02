"""reading.classes_as_looked_up — a drug RxClass was never asked about is not_looked_up, never "no class" and
never "lookup failed" (add-agent-operation 4.2: a relay run asks RxNav nothing after the pull).

The answers are classes._ask_rxnav's, over RxNorm and RxClass bodies of the live service's shape (an EPC for
pembrolizumab and its brand, a name RxNorm does not hold, a 503).

Positive: a drug none of whose names was asked is not_looked_up with no class and no resolving name, whatever
classes.drug_class said of it (lookup_failed over an empty cache); the reading of a population with no answers
names every experimental drug not_looked_up and reads no class from its own entry in RxClass's place.
Negative: a drug with any name answered keeps classes.drug_class's answer unchanged (classified, unresolved,
lookup_failed), so a run that looked its names up reads as it always did; an answer recorded for another
name says nothing of this drug.
"""

import pytest
from records import results_study
from rxnav_fake import FakeRxNav

from TrialLedger import classes
from TrialLedger.reading import classes_as_looked_up, read_population

# RxNorm holds pembrolizumab and its brand Keytruda (RxClass answers either about pembrolizumab); "flaky"
# fails; anything else RxNorm does not hold.
RXNAV = {
    "names": {"pembrolizumab": ["1547545"], "Keytruda": ["1547550"], "flaky": ["9999"]},
    "concepts": {"1547545": ("pembrolizumab", "IN"), "1547550": ("Keytruda", "BN"), "9999": ("flaky", "IN")},
    "classes": {
        rxcui: [
            (
                "N0000191260",
                "Programmed Death Receptor-1 Blocking Antibody",
                "EPC",
                "has_epc",
                "DAILYMED",
                "1547545",
            )
        ]
        for rxcui in ("1547545", "1547550")
    },
    "failing": {"9999"},
}


def answered(*names):
    return classes._ask_rxnav(
        list(names),
        set(),
        get=FakeRxNav(**RXNAV),
        sleep=lambda seconds: None,
        monotonic=lambda: 0.0,
        progress=lambda message: None,
    )


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
