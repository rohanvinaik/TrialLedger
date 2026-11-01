"""classes.rxclass_members and class_members_request — a drug class's members, by RxClass classMembers.

The answers are RxNav's own, as fetched on 2026-11-01 under release 05-Oct-2026
(tests/rxnav_request_answers.json): ATC L01ED (five ALK inhibitors, each an ingredient) and the EPC Kinase
Inhibitor (ingredients and precise ingredients, DIRECT and INDIRECT members); RxClass answers {} for a class
id it does not hold.

Positive: a 200 answer with members gives each member once, sorted, with its rxcui, name, term type and its
"Relation" node attribute; the request names the class's own relation source and relation (EPC: DAILYMED
has_epc; MoA: MEDRT has_moa; ATC: ATC, no relation).
Negative: an unknown class is not_found, never an empty member list read as found; a failed request is
lookup_failed; a body without a member's concept, rxcui, name or term type is malformed, never a member; a
relation the answer does not state is "", never guessed.
"""

import json
from pathlib import Path

import pytest

from TrialLedger.classes import class_members_request, rxclass_members

ANSWERS = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
MEMBERS = "https://rxnav.nlm.nih.gov/REST/rxclass/classMembers.json"
ALK = ANSWERS["answers"][f"{MEMBERS}?classId=L01ED&relaSource=ATC"]
KINASE = ANSWERS["answers"][f"{MEMBERS}?classId=N0000175605&relaSource=DAILYMED&rela=has_epc"]


def test_an_atc_class_gives_its_members_once_sorted():
    assert rxclass_members(*ALK) == (
        "found",
        [
            ("1148495", "crizotinib", "IN", "DIRECT"),
            ("1535457", "ceritinib", "IN", "DIRECT"),
            ("1727455", "alectinib", "IN", "DIRECT"),
            ("1921217", "brigatinib", "IN", "DIRECT"),
            ("2103164", "lorlatinib", "IN", "DIRECT"),
        ],
    )


def test_an_epc_class_keeps_each_members_term_type_and_relation():
    code, members = rxclass_members(*KINASE)
    assert code == "found" and len(members) == 81
    assert ("1546019", "dasatinib anhydrous", "PIN", "DIRECT") in members
    assert {member[2] for member in members} == {"IN", "PIN"}
    assert {member[3] for member in members} == {"DIRECT", "INDIRECT"}
    assert members == sorted(members)


def test_a_member_listed_twice_is_one_member():
    entry = ALK[1]["drugMemberGroup"]["drugMember"][0]
    body = {"drugMemberGroup": {"drugMember": [entry, entry]}}
    assert rxclass_members(200, body) == ("found", [("1148495", "crizotinib", "IN", "DIRECT")])


def test_a_relation_is_kept_as_text():
    entry = {"minConcept": {"rxcui": "1", "name": "a", "tty": "IN"}}
    entry["nodeAttr"] = [{"attrName": "Relation", "attrValue": 5}]
    assert rxclass_members(200, {"drugMemberGroup": {"drugMember": [entry]}}) == (
        "found",
        [("1", "a", "IN", "5")],
    )


def test_a_relation_the_answer_does_not_state_is_empty():
    concept = {"rxcui": "1", "name": "a", "tty": "IN"}
    bodies = [
        {"drugMemberGroup": {"drugMember": [{"minConcept": concept}]}},
        {"drugMemberGroup": {"drugMember": [{"minConcept": concept, "nodeAttr": "DIRECT"}]}},
        {
            "drugMemberGroup": {
                "drugMember": [{"minConcept": concept, "nodeAttr": ["x", {"attrName": "Other"}]}]
            }
        },
    ]
    for body in bodies:
        assert rxclass_members(200, body) == ("found", [("1", "a", "IN", "")])
    stated = {"minConcept": concept, "nodeAttr": [{"attrName": "Relation"}]}
    assert rxclass_members(200, {"drugMemberGroup": {"drugMember": [stated]}}) == (
        "found",
        [("1", "a", "IN", "")],
    )


@pytest.mark.parametrize(
    "status, body, code",
    [
        (200, {}, "not_found"),
        (200, {"drugMemberGroup": {}}, "not_found"),
        (200, {"drugMemberGroup": {"drugMember": None}}, "not_found"),
        (200, [], "malformed"),
        (200, None, "malformed"),
        (200, {"drugMemberGroup": []}, "malformed"),
        (200, {"drugMemberGroup": {"drugMember": []}}, "malformed"),
        (200, {"drugMemberGroup": {"drugMember": "pembrolizumab"}}, "malformed"),
        (200, {"drugMemberGroup": {"drugMember": ["pembrolizumab"]}}, "malformed"),
        (200, {"drugMemberGroup": {"drugMember": [{"nodeAttr": []}]}}, "malformed"),
        (200, {"drugMemberGroup": {"drugMember": [{"minConcept": "x"}]}}, "malformed"),
        (
            200,
            {"drugMemberGroup": {"drugMember": [{"minConcept": {"rxcui": 1, "name": "a", "tty": "IN"}}]}},
            "malformed",
        ),
        (
            200,
            {"drugMemberGroup": {"drugMember": [{"minConcept": {"rxcui": "1", "name": "a"}}]}},
            "malformed",
        ),
        (503, ALK[1], "lookup_failed"),
        (0, None, "lookup_failed"),
    ],
)
def test_no_member_has_a_named_reason(status, body, code):
    assert rxclass_members(status, body) == (code, [])


def test_one_malformed_member_spoils_the_answer():
    good = ALK[1]["drugMemberGroup"]["drugMember"][0]
    body = {
        "drugMemberGroup": {"drugMember": [good, {"minConcept": {"rxcui": "2", "name": None, "tty": "IN"}}]}
    }
    assert rxclass_members(200, body) == ("malformed", [])


def test_the_request_names_the_class_sources_relation():
    assert class_members_request("N0000191260", "EPC") == (
        MEMBERS,
        {"classId": "N0000191260", "relaSource": "DAILYMED", "rela": "has_epc"},
    )
    assert class_members_request("N0000175082", "MoA") == (
        MEMBERS,
        {"classId": "N0000175082", "relaSource": "MEDRT", "rela": "has_moa"},
    )
    assert class_members_request("L01ED", "ATC") == (MEMBERS, {"classId": "L01ED", "relaSource": "ATC"})
