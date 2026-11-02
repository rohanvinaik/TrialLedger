"""Reporting attributes class assertions to source identities, never to a selected name string.

The source-shaped fixtures deliberately use arbitrary names and identifiers. Exact RxCUI relations,
not the spelling of a drug, decide equality, related ingredients and combinations.
"""

import copy
from itertools import permutations

import pytest
from rxnav_fake import FakeRxNav

from TrialLedger.classes import (
    _ask_rxnav,
    alias_role,
    class_evidence,
    drug_axes,
    identity_evidence,
    name_identity,
)

DATA = {
    "names": {
        "A": ["100"],
        "A synonym": ["100"],
        "Brand": ["200"],
        "Precise form": ["300"],
        "Biologic variant": ["400"],
        "B": ["500"],
        "Combination": ["600"],
        "Ambiguous": ["100", "500"],
    },
    "concepts": {
        "100": ("canonical A", "IN"),
        "200": ("canonical brand", "BN"),
        "300": ("canonical precise form", "PIN"),
        "400": ("canonical biologic variant", "PIN"),
        "500": ("canonical B", "IN"),
        "600": ("canonical combination", "MIN"),
    },
    "ingredients": {"200": ["100"], "300": ["100"], "400": ["100"], "600": ["100", "500"]},
    "classes": {
        "100": [
            ("E", "Class E", "EPC", "has_epc", "DAILYMED", "100"),
            ("M", "Class M", "MOA", "has_moa", "MEDRT", "100"),
        ],
        "200": [("E", "Class E", "EPC", "has_epc", "DAILYMED", "100")],
        "300": [("E", "Class E", "EPC", "has_epc", "DAILYMED", "100")],
        "400": [("E", "Class E", "EPC", "has_epc", "DAILYMED", "100")],
        "500": [("B", "Class B", "EPC", "has_epc", "DAILYMED", "500")],
        "600": [
            ("E", "Class E", "EPC", "has_epc", "DAILYMED", "100"),
            ("C", "Class C", "EPC", "has_epc", "DAILYMED", "600"),
        ],
    },
}


@pytest.fixture(scope="module")
def answers():
    return _ask_rxnav(
        [*DATA["names"], "Unknown"],
        {*DATA["names"], "Unknown"},
        get=FakeRxNav(**DATA),
        sleep=lambda _: None,
        monotonic=lambda: 0.0,
        progress=lambda _: None,
    )


def test_exact_identity_establishes_only_subject_bearing_source_classes(answers):
    result = class_evidence(["A", "A synonym"], answers)
    assert (result["state"], result["reason"], result["resolved_by"]) == (
        "classified",
        "exact_source_subject",
        "A",
    )
    assert result["classes"] == [
        ["E", "Class E", "has_epc", "DAILYMED"],
        ["M", "Class M", "has_moa", "MEDRT"],
    ]
    own, alias = result["identities"]
    assert (own["rxcui"], own["canonical_name"], alias["role"]) == ("100", "canonical A", "confirms")
    assert all(row["subject_rxcui"] == "100" and row["standing"] == "known" for row in result["assertions"])
    assert all(row["request"]["params"] == {"rxcui": "100"} for row in result["assertions"])


def test_alias_order_cannot_choose_a_class_and_conflict_keeps_all_evidence(answers):
    results = [
        class_evidence(["A", *aliases], answers) for aliases in permutations(["A synonym", "B", "Brand"])
    ]
    assert all(result == results[0] for result in results)
    result = results[0]
    assert (result["state"], result["reason"], result["classes"]) == (
        "conflict",
        "alias_identity_conflict",
        [],
    )
    assert {identity["rxcui"] for identity in result["identities"]} == {"100", "200", "500"}
    assert {row["subject_rxcui"] for row in result["assertions"]} == {"100", "500"}
    assert not any(row["standing"] == "known" for row in result["assertions"])


def test_an_unknown_own_name_is_not_replaced_by_a_classified_alias(answers):
    result = class_evidence(["Unknown", "A", "B"], answers)
    assert (result["state"], result["reason"], result["classes"], result["resolved_by"]) == (
        "unresolved",
        "own_identity_not_in_rxnorm",
        [],
        "",
    )
    assert len(result["assertions"]) == 3
    assert {row["standing"] for row in result["assertions"]} == {"identity_unresolved"}


@pytest.mark.parametrize(
    "name, code, tty",
    [
        ("Brand", "brand", "BN"),
        ("Precise form", "precise_ingredient", "PIN"),
        ("Biologic variant", "precise_ingredient", "PIN"),
    ],
)
def test_related_ingredients_never_become_the_products_identity_or_class(answers, name, code, tty):
    result = class_evidence([name, "A"], answers)
    own, related = result["identities"]
    assert (own["code"], own["term_type"], own["ingredients"], related["role"]) == (
        code,
        tty,
        ["100"],
        "related_form",
    )
    assert own["rxcui"] != related["rxcui"]
    assert result["state"] == "unresolved" and result["classes"] == []
    assert {row["standing"] for row in result["assertions"]} == {"not_inherited"}


def test_two_precise_ingredients_with_a_shared_base_stay_distinct(answers):
    result = class_evidence(["Biologic variant", "Precise form"], answers)
    own, related = result["identities"]
    assert (own["rxcui"], related["rxcui"], related["role"]) == ("400", "300", "related_form")
    assert result["classes"] == []
    assert all(identity["code"] == "precise_ingredient" for identity in result["identities"])


def test_a_combination_keeps_its_own_assertion_and_does_not_inherit_components(answers):
    result = class_evidence(["Combination"], answers)
    assert result["state"] == "classified"
    assert result["classes"] == [["C", "Class C", "has_epc", "DAILYMED"]]
    assert {(row["subject_rxcui"], row["standing"]) for row in result["assertions"]} == {
        ("100", "not_inherited"),
        ("600", "known"),
    }
    conflict = class_evidence(["Combination", "A"], answers)
    assert conflict["state"] == "conflict" and conflict["classes"] == []
    assert conflict["identities"][1]["role"] == "alias_is_one_ingredient"


def test_punctuation_cannot_establish_a_missing_combination_identity(answers):
    result = class_evidence(["Unknown + B", "A"], answers)
    assert result["state"] == "not_looked_up" and result["classes"] == []
    assert result["identities"][1]["role"] == "alias_other_concept"
    assert alias_role(("not_in_rxnorm", "", []), ("ingredient", "100", ["100"])) == "alias_other_concept"


def test_ambiguous_and_failed_identity_are_distinct_from_negative_class_answers(answers):
    ambiguous = class_evidence(["Ambiguous", "A"], answers)
    assert ambiguous["state"] == "unresolved" and ambiguous["reason"] == "own_identity_ambiguous"
    failed = copy.deepcopy(answers)
    failed["A"]["axes"]["identity"]["ids"] = ["lookup_failed", []]
    result = class_evidence(["A"], failed)
    assert result["state"] == "lookup_failed" and result["classes"] == []
    negative = copy.deepcopy(answers)
    for axis in ("DAILYMED:has_epc", "MEDRT:has_moa"):
        negative["A"]["axes"][axis].update(code="not_found", assertions=[])
    result = class_evidence(["A"], negative)
    assert result["state"] == "unresolved" and result["reason"] == "no_direct_class_assertion"
    assert {query["code"] for query in result["queries"]} == {"not_found"}


def test_class_failure_and_malformed_subject_evidence_are_not_no_class(answers):
    failed = copy.deepcopy(answers)
    for axis in ("DAILYMED:has_epc", "MEDRT:has_moa"):
        failed["A"]["axes"][axis].update(code="lookup_failed", assertions=[])
    assert class_evidence(["A"], failed)["state"] == "lookup_failed"
    malformed = copy.deepcopy(answers)
    malformed["A"]["axes"]["DAILYMED:has_epc"].update(assertions=[["E", "Class E"]])
    malformed["A"]["axes"]["MEDRT:has_moa"].update(code="not_found", assertions=[])
    result = class_evidence(["A"], malformed)
    assert result["state"] == "unresolved" and result["reason"] == "class_response_malformed"
    assert result["classes"] == []


@pytest.mark.parametrize(
    "answer",
    [
        [],
        "bad",
        {"axes": {"identity": []}},
        {"axes": {"identity": {"ids": []}}},
        {"axes": {"identity": {"ids": ["found", [1]]}}},
    ],
)
def test_malformed_retained_identity_has_a_named_state(answer):
    assert identity_evidence("A", answer)["code"] == "malformed"
    assert class_evidence(["A"], {"A": answer})["classes"] == []


def test_missing_or_legacy_evidence_is_not_promoted_from_flat_classes():
    assert class_evidence(["A"], None)["state"] == "not_looked_up"
    assert class_evidence(["A"], {})["state"] == "not_looked_up"
    legacy = {
        "A": {"classes": [["E", "Class E", "has_epc", "DAILYMED"]], "codes": {"DAILYMED:has_epc": "found"}}
    }
    assert class_evidence(["A"], legacy)["classes"] == []
    assert class_evidence([], {})["reason"] == "no_recorded_name"


def test_malformed_requests_are_not_misreported_as_not_looked_up():
    assert class_evidence([None], {})["reason"] == "malformed_recorded_names"
    assert class_evidence(["A"], [])["reason"] == "malformed_answers"


def test_negative_query_code_with_assertions_is_malformed_not_a_known_class(answers):
    contradictory = copy.deepcopy(answers)
    contradictory["A"]["axes"]["DAILYMED:has_epc"]["code"] = "not_found"
    contradictory["A"]["axes"]["MEDRT:has_moa"].update(code="not_found", assertions=[])
    result = class_evidence(["A"], contradictory)
    assert result["state"] == "unresolved" and result["reason"] == "class_response_malformed"
    assert result["classes"] == []


def test_properties_must_describe_the_requested_concept():
    assert name_identity(
        ["found", ["100"]], ["found", [["500", "other concept", "IN"]]], ["not_asked", []]
    ) == ("unresolved", "", [])
    assert name_identity(["found", []], ["found", [["500", "other concept", "IN"]]], ["not_asked", []]) == (
        "unresolved",
        "",
        [],
    )


def test_source_requests_and_release_are_retained_on_identity_and_assertions(answers):
    result = class_evidence(["A"], answers)
    identity = result["identities"][0]
    assert identity["asked_as"] == "A" and identity["name_rule"] == "as_given"
    assert identity["release"][:2] == ["found", "05-Oct-2026"]
    assert identity["release_end"][:2] == identity["release"][:2]
    assert any(request["url"].endswith("properties.json") for request in identity["requests"])
    assert all(assertion["request"]["retrieved"] for assertion in result["assertions"])
    assert all(assertion["release"][:2] == identity["release"][:2] for assertion in result["assertions"])


def test_full_recorded_names_are_asked_without_dose_or_schedule_stripping():
    fake = FakeRxNav(**DATA)
    answers = _ask_rxnav(
        ["A 80 mg daily", "A"],
        {"A 80 mg daily", "A"},
        get=fake,
        sleep=lambda _: None,
        monotonic=lambda: 0.0,
        progress=lambda _: None,
    )
    assert answers["A 80 mg daily"]["asked_as"] == "A 80 mg daily"
    assert class_evidence(["A 80 mg daily", "A"], answers)["classes"] == []
    assert class_evidence(["A 80 mg daily", "A"], answers)["reason"] == "own_identity_not_in_rxnorm"


def test_old_normalized_lookup_is_only_a_candidate_in_both_source_consumers(answers):
    legacy = copy.deepcopy(answers["A"])
    legacy.update(asked_as="A", rule="dose_stripped")
    cached = {"A 80 mg daily": legacy}
    identity = identity_evidence("A 80 mg daily", legacy)
    assert identity["code"] == "lookup_candidate" and identity["canonical_name"] == "canonical A"
    result = class_evidence(["A 80 mg daily"], cached)
    assert result["state"] == "unresolved" and result["classes"] == []
    assert result["reason"] == "own_identity_lookup_candidate"
    code, reason, _identities, assertions = drug_axes(["A 80 mg daily"], cached)
    assert (code, reason) == ("unresolved", "own_name_lookup_candidate")
    assert not any(assertion[5] == "known" for assertion in assertions)


@pytest.mark.parametrize("code", ["lookup_failed", "not_found", "found"])
def test_legacy_query_codes_and_warrants_are_preserved_without_subject_promotion(code):
    request = {"url": "source-request", "params": {"drugName": "A"}, "retrieved": "recorded-time"}
    answer = {
        "codes": {"DAILYMED:has_epc": code},
        "classes": [["E", "Class E", "has_epc", "DAILYMED"]],
        "requests": [request],
        "release": ["found", "recorded-release"],
    }
    result = class_evidence(["A"], {"A": answer})
    assert result["identities"][0]["code"] == "not_recorded"
    assert result["queries"][0]["code"] == code
    assert result["queries"][0]["requests"] == [request]
    assert result["queries"][0]["release"] == ["found", "recorded-release"]
    assert result["classes"] == [] and result["resolved_by"] == ""
