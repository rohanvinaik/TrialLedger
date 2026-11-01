"""classes.rxclass_members, rxclass_tree and their requests — a drug class's members and its subclasses, by
RxClass classMembers and classTree.

The answers are RxNav's own, as fetched on 2026-11-01 under release 05-Oct-2026
(tests/rxnav_request_answers.json): ATC L01ED (five ALK inhibitors, each an ingredient, and no subclass), the
EPC Kinase Inhibitor (ingredients and precise ingredients, DIRECT and INDIRECT members, three of them both;
eight subclasses, Janus Kinase Inhibitor holding Tyrosine Kinase 2 Inhibitor) and the Janus Kinase Inhibitor's
own members asked with trans=1; RxClass answers {} for a class id it does not hold, to classMembers and to
classTree alike.

Positive: a 200 answer with members gives each member once, sorted, with its rxcui, name, term type and every
"Relation" node attribute it states, once, sorted (ruxolitinib: DIRECT and INDIRECT); a 200 tree gives each
class under its parent, each before its subclasses, at any depth; the requests name the class's own relation
source and relation (EPC: DAILYMED has_epc; MoA: MEDRT has_moa; ATC: ATC, no relation), trans=1 for a class's
own members, the class id alone for its tree.
Negative: an unknown class is not_found, never an empty member list or tree read as found; a failed request is
lookup_failed; a body without a member's concept, rxcui, name or term type, or a tree node without a string
id, name and type or with a subtree that is not a list, is malformed, never a member or a class; a relation
the answer does not state is (), never guessed.
"""

import json
from pathlib import Path

import pytest

from TrialLedger.classes import (
    class_members_request,
    class_tree_request,
    direct_members_request,
    rxclass_members,
    rxclass_tree,
)

ANSWERS = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
REST = "https://rxnav.nlm.nih.gov/REST"
MEMBERS = f"{REST}/rxclass/classMembers.json"
TREE = f"{REST}/rxclass/classTree.json"
ALK = ANSWERS["answers"][f"{MEMBERS}?classId=L01ED&relaSource=ATC"]
KINASE = ANSWERS["answers"][f"{MEMBERS}?classId=N0000175605&relaSource=DAILYMED&rela=has_epc"]
JAK_OWN = ANSWERS["answers"][f"{MEMBERS}?classId=N0000190858&relaSource=DAILYMED&rela=has_epc&trans=1"]
KINASE_TREE = ANSWERS["answers"][f"{TREE}?classId=N0000175605"]
ALK_TREE = ANSWERS["answers"][f"{TREE}?classId=L01ED"]


def test_an_atc_class_gives_its_members_once_sorted():
    assert rxclass_members(*ALK) == (
        "found",
        [
            ("1148495", "crizotinib", "IN", ("DIRECT",)),
            ("1535457", "ceritinib", "IN", ("DIRECT",)),
            ("1727455", "alectinib", "IN", ("DIRECT",)),
            ("1921217", "brigatinib", "IN", ("DIRECT",)),
            ("2103164", "lorlatinib", "IN", ("DIRECT",)),
        ],
    )


def test_an_epc_class_keeps_each_members_term_type_and_relations():
    code, members = rxclass_members(*KINASE)
    assert code == "found" and len(members) == 81
    assert ("1546019", "dasatinib anhydrous", "PIN", ("DIRECT",)) in members
    assert ("224905", "trastuzumab", "IN", ("INDIRECT",)) in members
    assert {member[2] for member in members} == {"IN", "PIN"}
    both = sorted(member[1] for member in members if member[3] == ("DIRECT", "INDIRECT"))
    assert both == ["everolimus", "ruxolitinib", "sirolimus"]
    assert len([member for member in members if member[3] == ("INDIRECT",)]) == 14
    assert members == sorted(members)


def test_a_class_asked_for_its_own_members_lists_them_direct():
    code, members = rxclass_members(*JAK_OWN)
    assert code == "found"
    assert [member[1] for member in members] == [
        "ruxolitinib",
        "tofacitinib",
        "baricitinib",
        "upadacitinib",
        "abrocitinib",
        "deuruxolitinib",
    ]
    assert {member[3] for member in members} == {("DIRECT",)}


def test_a_member_listed_twice_is_one_member():
    entry = ALK[1]["drugMemberGroup"]["drugMember"][0]
    body = {"drugMemberGroup": {"drugMember": [entry, entry]}}
    assert rxclass_members(200, body) == ("found", [("1148495", "crizotinib", "IN", ("DIRECT",))])


def test_every_relation_is_kept_as_text_once():
    entry = {"minConcept": {"rxcui": "1", "name": "a", "tty": "IN"}}
    entry["nodeAttr"] = [
        {"attrName": "Relation", "attrValue": "INDIRECT"},
        {"attrName": "Relation", "attrValue": 5},
        {"attrName": "Relation", "attrValue": "INDIRECT"},
        {"attrName": "Relation", "attrValue": "DIRECT"},
    ]
    assert rxclass_members(200, {"drugMemberGroup": {"drugMember": [entry]}}) == (
        "found",
        [("1", "a", "IN", ("5", "DIRECT", "INDIRECT"))],
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
        {
            "drugMemberGroup": {
                "drugMember": [{"minConcept": concept, "nodeAttr": [{"attrName": "Relation"}]}]
            }
        },
        {
            "drugMemberGroup": {
                "drugMember": [
                    {"minConcept": concept, "nodeAttr": [{"attrName": "SourceId", "attrValue": "DIRECT"}]}
                ]
            }
        },
    ]
    for body in bodies:
        assert rxclass_members(200, body) == ("found", [("1", "a", "IN", ())])


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


def test_a_class_own_members_and_its_tree_are_asked_by_its_id():
    assert direct_members_request("N0000190858", "EPC") == (
        MEMBERS,
        {"classId": "N0000190858", "relaSource": "DAILYMED", "rela": "has_epc", "trans": "1"},
    )
    assert direct_members_request("L01EJ", "ATC") == (
        MEMBERS,
        {"classId": "L01EJ", "relaSource": "ATC", "trans": "1"},
    )
    assert class_tree_request("N0000175605") == (TREE, {"classId": "N0000175605"})


# ── the class tree ───────────────────────────────────────────────────────────────────────────────────────


def test_a_class_tree_gives_each_subclass_under_its_parent_at_any_depth():
    root = "N0000175605"
    assert rxclass_tree(*KINASE_TREE) == (
        "found",
        [
            (root, "Kinase Inhibitor", "EPC", ""),
            ("N0000175625", "mTOR Inhibitor Immunosuppressant", "EPC", root),
            ("N0000175661", "HER2/neu Receptor Antagonist", "EPC", root),
            ("N0000175664", "Epidermal Growth Factor Receptor Antagonist", "EPC", root),
            ("N0000190858", "Janus Kinase Inhibitor", "EPC", root),
            ("N0000194043", "Tyrosine Kinase 2 Inhibitor", "EPC", "N0000190858"),
            ("N0000191009", "Vascular Endothelial Growth Factor Receptor 2 Antagonist", "EPC", root),
            ("N0000193788", "Rho Kinase Inhibitor", "EPC", root),
            ("N0000193976", "Cytomegalovirus pUL97 Kinase Inhibitor", "EPC", root),
        ],
    )


def test_a_class_without_subclasses_is_its_own_tree():
    assert rxclass_tree(*ALK_TREE) == (
        "found",
        [("L01ED", "Anaplastic lymphoma kinase (ALK) inhibitors", "ATC1-4", "")],
    )


def node(class_id, *children):
    item = {"rxclassMinConceptItem": {"classId": class_id, "className": class_id.lower(), "classType": "MOA"}}
    return item | ({"rxclassTree": list(children)} if children else {})


def test_a_class_under_two_parents_is_listed_under_each_and_a_repeat_once():
    body = {"rxclassTree": [node("A", node("B", node("D")), node("C", node("D")), node("B"))]}
    assert rxclass_tree(200, body) == (
        "found",
        [
            ("A", "a", "MOA", ""),
            ("B", "b", "MOA", "A"),
            ("D", "d", "MOA", "B"),
            ("C", "c", "MOA", "A"),
            ("D", "d", "MOA", "C"),
        ],
    )
    two_tops = {"rxclassTree": [node("A"), node("B")]}
    assert rxclass_tree(200, two_tops) == ("found", [("A", "a", "MOA", ""), ("B", "b", "MOA", "")])


@pytest.mark.parametrize(
    "status, body, code",
    [
        (200, {}, "not_found"),
        (200, {"rxclassTree": None}, "not_found"),
        (200, [], "malformed"),
        (200, None, "malformed"),
        (200, {"rxclassTree": []}, "malformed"),
        (200, {"rxclassTree": {}}, "malformed"),
        (200, {"rxclassTree": ["N0000175605"]}, "malformed"),
        (200, {"rxclassTree": [{}]}, "malformed"),
        (200, {"rxclassTree": [{"rxclassMinConceptItem": "N0000175605"}]}, "malformed"),
        (200, {"rxclassTree": [{"rxclassMinConceptItem": {"classId": "A", "className": "a"}}]}, "malformed"),
        (
            200,
            {
                "rxclassTree": [
                    {"rxclassMinConceptItem": {"classId": 5, "className": "a", "classType": "EPC"}}
                ]
            },
            "malformed",
        ),
        (200, {"rxclassTree": [node("A") | {"rxclassTree": {}}]}, "malformed"),
        (200, {"rxclassTree": [node("A") | {"rxclassTree": None}]}, "malformed"),
        (200, {"rxclassTree": [node("A", node("B"), "C")]}, "malformed"),
        (404, KINASE_TREE[1], "lookup_failed"),
        (0, None, "lookup_failed"),
    ],
)
def test_no_tree_has_a_named_reason(status, body, code):
    assert rxclass_tree(status, body) == (code, [])
