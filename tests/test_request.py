"""request — a user's question as a structured request, resolved into one registry query (add-agent-operation
2.1-2.3).

The RxNav answers are RxNav's own, fetched on 2026-11-01 under release 05-Oct-2026 through the URLs
request.lookups_needed names (tests/rxnav_request_answers.json, which keeps the requests asked); nothing here
touches the network.

Positive: a well-formed request is ok and resolves, round by round, to the lookups it needs and then to one
registry query: a drug class to its members by RxClass (confirmed first by byName or byId), a brand or a salt
to its ingredient's name beside its own, an unknown name searched as asked, a condition class to the MeSH term
or ancestor, phase and status as OR groups, the start range with MIN or MAX, a condition to query.cond, raw
parameters beside them; every expansion keeps its request, code and the RxNav release, with what that
release rests on (asked once, in the first round); a class an entailed crosswalk row names is confirmed by
RxClass before its members.
Negative: an empty request, an unknown slot, a malformed value, a reversed start range and a raw parameter
check_query refuses or a slot sets are refused by name; a class RxClass does not hold, holds under another
source or holds twice, a mechanism outside the crosswalk or with no entailed row, a class with no member, a
failed or malformed answer, a crosswalk class RxClass no longer holds and a query the registry would refuse
each stop the scope by a named code, and no query is written; a failed lookup is never read as a name searched
alone; a release RxNav fails to state is kept as its code and stops nothing.
"""

import json
from pathlib import Path

import pytest

from TrialLedger import classes, request
from TrialLedger.request import (
    QUERY_LIMIT,
    class_matches,
    class_resolution,
    drug_names,
    identity_chain,
    lookups_needed,
    mechanism_rows,
    member_identity,
    request_problems,
    resolve_scope,
    slot_value_ok,
)

DOC = json.loads((Path(__file__).parent / "rxnav_request_answers.json").read_text(encoding="utf-8"))
ANSWERS = DOC["answers"]
PD1_IN_LUNG, BY_NAME, ALK_ATC, ALK_AS_EPC, NO_CLASS, KINASE_EPC, KINASE_MOA = DOC["requests"]
REST = "https://rxnav.nlm.nih.gov/REST"
VERSION = f"{REST}/version.json"
PD1_CLASS = (
    f"{REST}/rxclass/class/byName.json?className=Programmed+Death+Receptor-1+Blocking+Antibody&classTypes=EPC"
)
PD1_MEMBERS = f"{REST}/rxclass/classMembers.json?classId=N0000191260&relaSource=DAILYMED&rela=has_epc"
ALK_CLASS = f"{REST}/rxclass/class/byId.json?classId=L01ED"
ALK_MEMBERS = f"{REST}/rxclass/classMembers.json?classId=L01ED&relaSource=ATC"
KEYTRUDA = [
    f"{REST}/rxcui.json?name=Keytruda&search=0",
    f"{REST}/rxcui/1547550/properties.json",
    f"{REST}/rxcui/1547550/related.json?tty=IN",
]
PD1_NAMES = ["pembrolizumab", "nivolumab", "atezolizumab", "dostarlimab", "retifanlimab", "toripalimab"]
PD1_NAMES.append("tislelizumab")
PD1_CLAUSE = "(" + " OR ".join(f'AREA[InterventionName]"{name}"' for name in PD1_NAMES) + ")"
LUNG = '(AREA[ConditionMeshTerm]"Lung Neoplasms" OR AREA[ConditionAncestorTerm]"Lung Neoplasms")'


# ── 2.1 the request and its refusals ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "slot, value",
    [
        ("drug", ["Keytruda", "osimertinib"]),
        ("drug_class", {"name": "Kinase Inhibitor", "source": "EPC"}),
        ("drug_class", {"name": "Kinase Inhibitors", "source": "MoA"}),
        ("drug_class", {"id": "L01ED", "source": "ATC"}),
        ("mechanism", "PD-1"),
        ("mechanism", 'anti "PD-1"'),
        ("condition", "non-small cell lung cancer"),
        ("condition", '"lung cancer" OR NSCLC'),
        ("condition_class", "Lung Neoplasms"),
        ("phase", ["PHASE2", "PHASE3"]),
        ("status", ["RECRUITING", "NOT_YET_RECRUITING"]),
        ("study_type", "INTERVENTIONAL"),
        ("start_from", "2015-01-01"),
        ("start_to", "2024-12-31"),
        ("params", {"query.term": "biomarker", "filter.geo": "distance(39.0,-77.1,50mi)"}),
    ],
)
def test_a_slot_of_its_form_is_well_formed(slot, value):
    assert slot_value_ok(slot, value) is True


@pytest.mark.parametrize(
    "slot, value",
    [
        ("drug", []),
        ("drug", "Keytruda"),
        ("drug", [""]),
        ("drug", ["  "]),
        ("drug", ['XB-1 "fast"']),
        ("drug", ["Keytruda", 1]),
        ("drug_class", "Kinase Inhibitor"),
        ("drug_class", {"name": "Kinase Inhibitor"}),
        ("drug_class", {"name": "Kinase Inhibitor", "source": "SNOMED"}),
        ("drug_class", {"name": "Kinase Inhibitor", "source": ["EPC"]}),
        ("drug_class", {"name": "Kinase Inhibitor", "id": "N0000175605", "source": "EPC"}),
        ("drug_class", {"source": "EPC"}),
        ("drug_class", {"name": "", "source": "EPC"}),
        ("drug_class", {"name": "  ", "source": "EPC"}),
        ("drug_class", {"id": 5, "source": "ATC"}),
        ("drug_class", {"name": "Kinase Inhibitor", "source": "EPC", "relation": "has_epc"}),
        ("mechanism", ""),
        ("mechanism", "   "),
        ("mechanism", ["PD-1"]),
        ("condition", None),
        ("condition_class", ""),
        ("condition_class", 'Lung "Neoplasms"'),
        ("phase", []),
        ("phase", "PHASE2"),
        ("phase", ["PHASE9"]),
        ("phase", ["PHASE2", "PHASE9"]),
        ("phase", [["PHASE2"]]),
        ("status", ["RECRUTING"]),
        ("status", ["RECRUITING", "recruiting"]),
        ("study_type", "interventional"),
        ("study_type", ["INTERVENTIONAL"]),
        ("start_from", "2015-1-1"),
        ("start_from", "2015-02-30"),
        ("start_from", "20150101"),
        ("start_from", "2015"),
        ("start_to", 2015),
        ("params", {}),
        ("params", {"pageSize": 5}),
        ("params", {"query.term": "x", "pageSize": 5}),
        ("params", {"query.term": "x", 1: "x"}),
        ("params", [["query.term", "x"]]),
        ("params", {1: "x"}),
        ("sponsor", "Merck"),
        ("sponsor", {"query.term": "x"}),
        ("drug", ["Keytruda", ""]),
        ("drug", ["Keytruda", 'a"b']),
    ],
)
def test_a_slot_not_of_its_form_is_malformed(slot, value):
    assert slot_value_ok(slot, value) is False


def test_every_fetched_request_is_ok():
    for item in DOC["requests"]:
        assert request_problems(item) == ("ok", [])


@pytest.mark.parametrize(
    "item, refusal",
    [
        ([], ("not_an_object", [])),
        ("Keytruda", ("not_an_object", [])),
        (None, ("not_an_object", [])),
        ({}, ("empty_request", [])),
        ({"drug": ["a"], "sponsor": "x", "Phase": ["PHASE2"]}, ("unknown_slot", ["Phase", "sponsor"])),
        ({"phase": ["PHASE9"], "drug": [], "condition": "asthma"}, ("malformed_value", ["drug", "phase"])),
        (
            {"start_from": "2024-01-02", "start_to": "2024-01-01"},
            ("malformed_value", ["start_from", "start_to"]),
        ),
        ({"start_from": "2024-01-02", "start_to": "2024-1-1"}, ("malformed_value", ["start_to"])),
        ({"condition": "asthma", "params": {"pageSize": "5"}}, ("params_reserved", ["pageSize"])),
        ({"params": {"query.term": " ", "query.cond": "asthma"}}, ("params_empty_value", ["query.term"])),
        (
            {"params": {"query.term": "NCT01030536", "filter.overallStatus": "RECRUITING"}},
            ("params_filters_ignored", ["query.term"]),
        ),
        (
            {"phase": ["PHASE2"], "params": {"filter.advanced": "AREA[Phase]PHASE3"}},
            ("params_conflict", ["filter.advanced"]),
        ),
        ({"condition": "asthma", "params": {"query.cond": "copd"}}, ("params_conflict", ["query.cond"])),
        (
            {"condition": "asthma", "drug": ["x"], "params": {"query.cond": "c", "filter.advanced": "a"}},
            ("params_conflict", ["filter.advanced", "query.cond"]),
        ),
    ],
)
def test_a_request_is_refused_by_name(item, refusal):
    assert request_problems(item) == refusal


@pytest.mark.parametrize(
    "item",
    [
        {"start_from": "2024-01-01", "start_to": "2024-01-01"},
        {"start_from": "2024-01-01"},
        {"start_to": "1999-01-01"},
        {"params": {"filter.advanced": "AREA[Phase]PHASE3"}},
        {"condition": "asthma", "params": {"filter.advanced": "AREA[Phase]PHASE3"}},
        {"phase": ["PHASE2"], "params": {"query.cond": "asthma", "query.term": "NCT01030536 lymphoma"}},
    ],
)
def test_a_request_whose_slots_and_parameters_agree_is_ok(item):
    assert request_problems(item) == ("ok", [])


# ── 2.2 the class, the mechanism and the names ───────────────────────────────────────────────────────────


def test_a_class_by_name_and_by_id_is_rxclass_own():
    assert class_matches(*ANSWERS[PD1_CLASS]) == (
        "found",
        [["N0000191260", "Programmed Death Receptor-1 Blocking Antibody", "EPC"]],
    )
    assert class_matches(*ANSWERS[ALK_CLASS]) == (
        "found",
        [["L01ED", "Anaplastic lymphoma kinase (ALK) inhibitors", "ATC1-4"]],
    )


def test_classes_are_listed_once_sorted():
    a = {"classId": "N2", "className": "B", "classType": "EPC"}
    b = {"classId": "N1", "className": "A", "classType": "EPC"}
    body = {"rxclassMinConceptList": {"rxclassMinConcept": [a, b, a]}}
    assert class_matches(200, body) == ("found", [["N1", "A", "EPC"], ["N2", "B", "EPC"]])


@pytest.mark.parametrize(
    "status, body, code",
    [
        (200, {}, "not_found"),
        (200, [], "malformed"),
        (200, {"rxclassMinConceptList": []}, "malformed"),
        (200, {"rxclassMinConceptList": {}}, "malformed"),
        (200, {"rxclassMinConceptList": {"rxclassMinConcept": []}}, "malformed"),
        (200, {"rxclassMinConceptList": {"rxclassMinConcept": ["N1"]}}, "malformed"),
        (
            200,
            {"rxclassMinConceptList": {"rxclassMinConcept": [{"classId": "N1", "className": "A"}]}},
            "malformed",
        ),
        (
            200,
            {
                "rxclassMinConceptList": {
                    "rxclassMinConcept": [{"classId": 5, "className": "A", "classType": "EPC"}]
                }
            },
            "malformed",
        ),
        (404, {}, "lookup_failed"),
        (0, None, "lookup_failed"),
    ],
)
def test_no_class_answer_has_a_named_reason(status, body, code):
    assert class_matches(status, body) == (code, [])


@pytest.mark.parametrize(
    "source, found, resolution",
    [
        ("EPC", ("found", [["N1", "A", "EPC"]]), ("found", [["N1", "A", "EPC"]])),
        ("ATC", ("found", [["L01ED", "ALK", "ATC1-4"]]), ("found", [["L01ED", "ALK", "ATC1-4"]])),
        ("MoA", ("found", [["N9", "K", "MOA"], ["N1", "A", "EPC"]]), ("found", [["N9", "K", "MOA"]])),
        (
            "EPC",
            ("found", [["N2", "B", "EPC"], ["N1", "A", "EPC"], ["N3", "C", "MOA"]]),
            ("class_ambiguous", [["N1", "A", "EPC"], ["N2", "B", "EPC"]]),
        ),
        (
            "EPC",
            ("found", [["L01ED", "ALK", "ATC1-4"], ["L01", "X", "ATC1-4"]]),
            ("class_source_mismatch", [["L01", "X", "ATC1-4"], ["L01ED", "ALK", "ATC1-4"]]),
        ),
        ("EPC", ("not_found", []), ("class_not_found", [])),
        ("EPC", ("lookup_failed", []), ("class_lookup_failed", [])),
        ("ATC", ("malformed", []), ("class_malformed", [])),
    ],
)
def test_a_requested_class_is_one_class_of_its_source(source, found, resolution):
    assert class_resolution(source, *found) == resolution


def test_a_mechanism_without_an_entailed_row_is_listed_unexpanded():
    row = ("PD-1", "L01FF", classes._L01FF, "overlaps", False, classes.RXCLASS_BY_ID + "L01FF", "2026-11-01")
    assert mechanism_rows("PD-1") == ("mechanism_not_entailed", [row])
    assert mechanism_rows("  pd-1 ") == ("mechanism_not_entailed", [row])
    code, rows = mechanism_rows("EGFR inhibitor")
    assert code == "mechanism_not_entailed"
    assert [(r[1], r[3], r[4]) for r in rows] == [
        ("L01EB", "broader_than", False),
        ("L01FE", "broader_than", False),
    ]


def test_a_mechanism_outside_the_crosswalk_is_named():
    assert mechanism_rows("KRAS G12C") == ("mechanism_not_in_crosswalk", [])
    assert mechanism_rows("PD-1 inhibitor") == ("mechanism_not_in_crosswalk", [])


def test_only_an_entailed_row_is_expanded(monkeypatch):
    rows = (
        ("ALK", "L01ED", "ALK inhibitors", "equivalent_to", "cited", "request", "2026-11-01"),
        ("ALK", "L01EX", "Other kinase inhibitors", "overlaps", "cited", "request", "2026-11-01"),
    )
    monkeypatch.setattr(classes, "CROSSWALK", rows)
    monkeypatch.setattr(request, "CROSSWALK", rows)
    assert mechanism_rows("alk") == (
        "found",
        [
            ("ALK", "L01ED", "ALK inhibitors", "equivalent_to", True, "request", "2026-11-01"),
            ("ALK", "L01EX", "Other kinase inhibitors", "overlaps", False, "request", "2026-11-01"),
        ],
    )


def test_a_brand_is_resolved_through_its_whole_chain():
    urls, parts = identity_chain("Keytruda", ANSWERS)
    assert urls == KEYTRUDA
    assert parts == [
        ("found", ["1547550"]),
        ("found", [("1547550", "Keytruda", "BN")]),
        ("found", [("1547545", "pembrolizumab", "IN")]),
    ]


def test_an_ingredient_and_an_unknown_name_stop_early():
    assert identity_chain("osimertinib", ANSWERS) == (
        [f"{REST}/rxcui.json?name=osimertinib&search=0", f"{REST}/rxcui/1721560/properties.json"],
        [("found", ["1721560"]), ("found", [("1721560", "osimertinib", "IN")]), ("not_asked", [])],
    )
    assert identity_chain("XB-1 zzq", ANSWERS) == (
        [f"{REST}/rxcui.json?name=XB-1+zzq&search=0"],
        [("not_found", []), ("not_asked", []), ("not_asked", [])],
    )


def test_each_unanswered_step_is_pending():
    assert identity_chain("Keytruda", {}) == (
        [KEYTRUDA[0]],
        [("pending", []), ("not_asked", []), ("not_asked", [])],
    )
    first = {KEYTRUDA[0]: ANSWERS[KEYTRUDA[0]]}
    assert identity_chain("Keytruda", first) == (
        KEYTRUDA[:2],
        [("found", ["1547550"]), ("pending", []), ("not_asked", [])],
    )
    two = first | {KEYTRUDA[1]: ANSWERS[KEYTRUDA[1]]}
    assert identity_chain("Keytruda", two) == (
        KEYTRUDA,
        [("found", ["1547550"]), ("found", [("1547550", "Keytruda", "BN")]), ("pending", [])],
    )


def test_a_name_of_several_concepts_or_a_failed_step_asks_no_further():
    ids = f"{REST}/rxcui.json?name=X&search=0"
    assert identity_chain("X", {ids: [200, {"idGroup": {"rxnormId": ["2", "1"]}}]}) == (
        [ids],
        [("found", ["1", "2"]), ("not_asked", []), ("not_asked", [])],
    )
    assert identity_chain("X", {ids: [503, None]}) == (
        [ids],
        [("lookup_failed", []), ("not_asked", []), ("not_asked", [])],
    )
    properties = f"{REST}/rxcui/1/properties.json"
    answers = {ids: [200, {"idGroup": {"rxnormId": ["1"]}}], properties: [503, None]}
    assert identity_chain("X", answers) == (
        [ids, properties],
        [("found", ["1"]), ("lookup_failed", []), ("not_asked", [])],
    )


def test_a_member_is_its_own_concept():
    assert member_identity(["1148495", "crizotinib", "IN", "DIRECT"], {}) == (
        [],
        [("found", ["1148495"]), ("found", [("1148495", "crizotinib", "IN")]), ("not_asked", [])],
    )
    related = f"{REST}/rxcui/1546019/related.json?tty=IN"
    member = ["1546019", "dasatinib anhydrous", "PIN", "DIRECT"]
    assert member_identity(member, ANSWERS) == (
        [related],
        [
            ("found", ["1546019"]),
            ("found", [("1546019", "dasatinib anhydrous", "PIN")]),
            ("found", [("475342", "dasatinib", "IN")]),
        ],
    )
    assert member_identity(member, {})[1][2] == ("pending", [])


def test_a_brand_or_a_salt_is_searched_by_its_ingredient_too():
    _, parts = identity_chain("Keytruda", ANSWERS)
    assert drug_names("Keytruda", "request", parts) == (
        "brand",
        [["Keytruda", "request"], ["pembrolizumab", "rxnorm_ingredient"]],
    )
    _, parts = identity_chain("osimertinib mesylate", ANSWERS)
    assert drug_names("osimertinib mesylate", "request", parts) == (
        "salt",
        [["osimertinib mesylate", "request"], ["osimertinib", "rxnorm_ingredient"]],
    )


def test_the_rxnorm_name_is_added_only_when_it_differs():
    parts = [("found", ["1"]), ("found", [("1", "osimertinib", "IN")]), ("not_asked", [])]
    assert drug_names("Osimertinib", "request", parts) == ("ingredient", [["Osimertinib", "request"]])
    parts = [
        ("found", ["1"]),
        ("found", [("1", "pembrolizumab 25 MG/ML", "SCD")]),
        ("found", [("2", "pembrolizumab", "IN")]),
    ]
    assert drug_names("Keytruda injection", "request", parts) == (
        "other_form",
        [
            ["Keytruda injection", "request"],
            ["pembrolizumab 25 MG/ML", "rxnorm_concept"],
            ["pembrolizumab", "rxnorm_ingredient"],
        ],
    )


def test_a_combination_is_never_searched_by_one_ingredient():
    parts = [
        ("found", ["9"]),
        ("found", [("9", "carboplatin / pemetrexed", "MIN")]),
        ("found", [("1", "carboplatin", "IN"), ("2", "pemetrexed", "IN")]),
    ]
    assert drug_names("Carbo/Pem", "request", parts) == (
        "combination",
        [["Carbo/Pem", "request"], ["carboplatin / pemetrexed", "rxnorm_concept"]],
    )


@pytest.mark.parametrize(
    "parts, code, names",
    [
        ([("not_found", []), ("not_asked", []), ("not_asked", [])], "not_in_rxnorm", [["XB-1", "request"]]),
        ([("found", ["1", "2"]), ("not_asked", []), ("not_asked", [])], "ambiguous", [["XB-1", "request"]]),
        ([("found", ["1"]), ("not_found", []), ("not_asked", [])], "unresolved", [["XB-1", "request"]]),
        ([("pending", []), ("not_asked", []), ("not_asked", [])], "pending", []),
        ([("found", ["1"]), ("found", [("1", "x", "BN")]), ("pending", [])], "pending", []),
        ([("lookup_failed", []), ("not_asked", []), ("not_asked", [])], "lookup_failed", []),
        ([("found", ["1"]), ("malformed", []), ("not_asked", [])], "malformed", []),
        ([("found", ["1"]), ("found", [("1", "x", "BN")]), ("lookup_failed", [])], "lookup_failed", []),
    ],
)
def test_a_name_rxnorm_cannot_resolve_is_searched_as_asked_and_a_failure_never(parts, code, names):
    assert drug_names("XB-1", "request", parts) == (code, names)


# ── 2.3 the resolved scope ───────────────────────────────────────────────────────────────────────────────


def test_a_class_in_a_disease_resolves_to_one_query():
    scope = resolve_scope(PD1_IN_LUNG, ANSWERS)
    assert scope["code"] == "resolved"
    assert scope["check"] == ["ok", []]
    assert scope["stops"] == [] and scope["pending"] == []
    assert scope["lookups"] == [VERSION, PD1_CLASS, PD1_MEMBERS]
    assert scope["release"] == ["found", "05-Oct-2026", VERSION]
    assert scope["release_basis"] == request.RELEASE_BASIS
    assert scope["query"] == {
        "filter.advanced": f"{PD1_CLAUSE} AND {LUNG} AND AREA[Phase]PHASE3 AND AREA[OverallStatus]RECRUITING "
        "AND AREA[StudyType]INTERVENTIONAL AND AREA[StartDate]RANGE[2015-01-01,MAX]"
    }
    assert [(s["slot"], s["clause"]) for s in scope["slots"]] == [
        ("drug_class", PD1_CLAUSE),
        ("condition_class", LUNG),
        ("phase", "AREA[Phase]PHASE3"),
        ("status", "AREA[OverallStatus]RECRUITING"),
        ("study_type", "AREA[StudyType]INTERVENTIONAL"),
        ("start_from", "AREA[StartDate]RANGE[2015-01-01,MAX]"),
    ]
    first, second, *names = scope["expansions"]
    assert first == {
        "slot": "drug_class",
        "kind": "class",
        "source": "EPC",
        "request": PD1_CLASS,
        "code": "found",
        "classes": [["N0000191260", "Programmed Death Receptor-1 Blocking Antibody", "EPC"]],
        "release": "05-Oct-2026",
    }
    assert {k: second[k] for k in ("kind", "class", "source", "request", "code", "release")} == {
        "kind": "class_members",
        "class": "N0000191260",
        "source": "EPC",
        "request": PD1_MEMBERS,
        "code": "found",
        "release": "05-Oct-2026",
    }
    assert [member[1] for member in second["members"]] == PD1_NAMES
    assert names[0] == {
        "slot": "drug_class",
        "kind": "drug_names",
        "drug": "pembrolizumab",
        "source": "RxNorm",
        "requests": [],
        "code": "ingredient",
        "names": [["pembrolizumab", "rxclass_member"]],
        "release": "05-Oct-2026",
    }


def test_named_drugs_resolve_with_their_ingredients_and_a_start_bound():
    scope = resolve_scope(BY_NAME, ANSWERS)
    names = ["Keytruda", "pembrolizumab", "osimertinib", "osimertinib mesylate", "XB-1 zzq"]
    clause = "(" + " OR ".join(f'AREA[InterventionName]"{name}"' for name in names) + ")"
    assert scope["code"] == "resolved"
    assert scope["query"] == {"filter.advanced": f"{clause} AND AREA[StartDate]RANGE[MIN,2024-12-31]"}
    assert [(e["drug"], e["code"]) for e in scope["expansions"]] == [
        ("Keytruda", "brand"),
        ("osimertinib", "ingredient"),
        ("osimertinib mesylate", "salt"),
        ("XB-1 zzq", "not_in_rxnorm"),
    ]
    assert scope["expansions"][0]["requests"] == KEYTRUDA
    assert scope["expansions"][0]["names"] == [
        ["Keytruda", "request"],
        ["pembrolizumab", "rxnorm_ingredient"],
    ]
    assert scope["lookups"] == [
        VERSION,
        *KEYTRUDA,
        f"{REST}/rxcui.json?name=osimertinib&search=0",
        f"{REST}/rxcui/1721560/properties.json",
        f"{REST}/rxcui.json?name=osimertinib+mesylate&search=0",
        f"{REST}/rxcui/1721559/properties.json",
        f"{REST}/rxcui/1721559/related.json?tty=IN",
        f"{REST}/rxcui.json?name=XB-1+zzq&search=0",
    ]
    assert lookups_needed(BY_NAME, {}) == [
        VERSION,
        KEYTRUDA[0],
        f"{REST}/rxcui.json?name=osimertinib&search=0",
        f"{REST}/rxcui.json?name=osimertinib+mesylate&search=0",
        f"{REST}/rxcui.json?name=XB-1+zzq&search=0",
    ]


def test_a_request_asked_twice_is_one_lookup():
    scope = resolve_scope({"drug": ["Keytruda", "Keytruda"]}, {})
    assert scope["lookups"] == [VERSION, KEYTRUDA[0]] and scope["pending"] == [VERSION, KEYTRUDA[0]]
    resolved = resolve_scope({"drug": ["Keytruda", "Keytruda"]}, ANSWERS)
    assert resolved["lookups"] == [VERSION, *KEYTRUDA]
    assert resolved["query"] == {
        "filter.advanced": '(AREA[InterventionName]"Keytruda" OR AREA[InterventionName]"pembrolizumab")'
    }


def test_an_atc_class_by_id_resolves_and_a_salt_member_adds_its_ingredient():
    scope = resolve_scope(ALK_ATC, ANSWERS)
    alk = ["crizotinib", "ceritinib", "alectinib", "brigatinib", "lorlatinib"]
    assert scope["query"] == {
        "filter.advanced": "(" + " OR ".join(f'AREA[InterventionName]"{name}"' for name in alk) + ")"
    }
    assert scope["lookups"] == [VERSION, ALK_CLASS, ALK_MEMBERS]
    kinase = resolve_scope(KINASE_EPC, ANSWERS)
    assert kinase["code"] == "resolved"
    assert (
        'AREA[InterventionName]"dasatinib anhydrous" OR AREA[InterventionName]"dasatinib"'
        in (kinase["query"]["filter.advanced"])
    )


def test_what_rxclass_does_not_hold_as_asked_stops_the_scope():
    mismatch = resolve_scope(ALK_AS_EPC, ANSWERS)
    assert mismatch["code"] == "unresolved" and mismatch["query"] == {}
    assert mismatch["stops"] == [
        [
            "drug_class",
            "class_source_mismatch",
            [["L01ED", "Anaplastic lymphoma kinase (ALK) inhibitors", "ATC1-4"]],
        ]
    ]
    missing = resolve_scope(NO_CLASS, ANSWERS)
    assert missing["code"] == "unresolved" and missing["query"] == {}
    assert missing["stops"] == [["drug_class", "class_not_found", []]]


def test_a_query_the_registry_would_refuse_for_its_length_is_not_written():
    scope = resolve_scope(KINASE_MOA, ANSWERS)
    assert scope["code"] == "unresolved" and scope["query"] == {}
    [[slot, code, (length, limit)]] = scope["stops"]
    assert (slot, code, limit) == ("query", "query_too_long", QUERY_LIMIT) and length > QUERY_LIMIT


def test_a_mechanism_no_row_entails_stops_without_a_lookup():
    scope = resolve_scope({"mechanism": "PD-1", "condition": "melanoma"}, {})
    row = ["PD-1", "L01FF", classes._L01FF, "overlaps", False, classes.RXCLASS_BY_ID + "L01FF", "2026-11-01"]
    assert scope["code"] == "unresolved"
    assert scope["stops"] == [["mechanism", "mechanism_not_entailed", [row]]]
    assert scope["lookups"] == [] and scope["release"] == ["not_asked", "", ""]
    assert scope["release_basis"] == ""
    assert scope["expansions"] == [
        {
            "slot": "mechanism",
            "kind": "crosswalk",
            "source": "classes.CROSSWALK",
            "code": "mechanism_not_entailed",
        }
        | {"rows": [row]}
    ]
    assert resolve_scope({"mechanism": "KRAS"}, {})["stops"] == [
        ["mechanism", "mechanism_not_in_crosswalk", ["KRAS"]]
    ]


def test_an_entailed_mechanism_expands_into_its_class_members(monkeypatch):
    rows = (("ALK", "L01ED", "ALK inhibitors", "equivalent_to", "cited", "request", "2026-11-01"),)
    monkeypatch.setattr(classes, "CROSSWALK", rows)
    monkeypatch.setattr(request, "CROSSWALK", rows)
    assert lookups_needed({"mechanism": "ALK"}, {}) == [VERSION, ALK_CLASS]
    scope = resolve_scope({"mechanism": "ALK"}, ANSWERS)
    assert scope["code"] == "resolved"
    assert scope["lookups"] == [VERSION, ALK_CLASS, ALK_MEMBERS]
    assert [(e["kind"], e["code"]) for e in scope["expansions"][:3]] == [
        ("crosswalk", "found"),
        ("class", "found"),
        ("class_members", "found"),
    ]
    assert scope["query"]["filter.advanced"].startswith('(AREA[InterventionName]"crizotinib" OR ')


def test_a_crosswalk_class_rxclass_no_longer_holds_is_not_read_as_memberless(monkeypatch):
    rows = (("ALK", "L01ED", "ALK inhibitors", "equivalent_to", "cited", "request", "2026-11-01"),)
    monkeypatch.setattr(classes, "CROSSWALK", rows)
    monkeypatch.setattr(request, "CROSSWALK", rows)
    gone = ANSWERS | {ALK_CLASS: [200, {}]}
    scope = resolve_scope({"mechanism": "ALK"}, gone)
    assert scope["code"] == "unresolved" and scope["query"] == {}
    assert scope["stops"] == [["mechanism", "class_not_found", []]]
    assert scope["lookups"] == [VERSION, ALK_CLASS]


def test_a_class_with_no_member_and_a_failed_answer_stop_by_name():
    no_members = ANSWERS | {PD1_MEMBERS: [200, {}]}
    assert resolve_scope({"drug_class": PD1_IN_LUNG["drug_class"]}, no_members)["stops"] == [
        ["drug_class", "no_members", ["N0000191260"]]
    ]
    failed = ANSWERS | {PD1_MEMBERS: [503, None]}
    assert resolve_scope({"drug_class": PD1_IN_LUNG["drug_class"]}, failed)["stops"] == [
        ["drug_class", "members_lookup_failed", ["N0000191260"]]
    ]
    broken = ANSWERS | {PD1_MEMBERS: [200, {"drugMemberGroup": []}]}
    assert resolve_scope({"drug_class": PD1_IN_LUNG["drug_class"]}, broken)["stops"] == [
        ["drug_class", "members_malformed", ["N0000191260"]]
    ]
    unclassed = ANSWERS | {PD1_CLASS: [500, None]}
    scope = resolve_scope({"drug_class": PD1_IN_LUNG["drug_class"]}, unclassed)
    assert scope["stops"] == [["drug_class", "class_lookup_failed", []]] and scope["code"] == "unresolved"


def test_a_failed_name_lookup_is_never_searched_alone():
    failed = ANSWERS | {KEYTRUDA[2]: [503, None]}
    scope = resolve_scope({"drug": ["Keytruda", "osimertinib"]}, failed)
    assert scope["code"] == "unresolved" and scope["query"] == {}
    assert scope["stops"] == [["drug", "name_lookup_failed", ["Keytruda"]]]
    broken = ANSWERS | {KEYTRUDA[1]: [200, []]}
    assert resolve_scope({"drug": ["Keytruda"]}, broken)["stops"] == [
        ["drug", "name_malformed", ["Keytruda"]]
    ]


def test_a_name_that_cannot_be_quoted_stops():
    ids = f"{REST}/rxcui.json?name=XB&search=0"
    properties = f"{REST}/rxcui/7/properties.json"
    answers = {
        VERSION: ANSWERS[VERSION],
        ids: [200, {"idGroup": {"rxnormId": ["7"]}}],
        properties: [200, {"properties": {"rxcui": "7", "name": 'XB "seven"', "tty": "IN"}}],
    }
    scope = resolve_scope({"drug": ["XB"]}, answers)
    assert scope["stops"] == [["drug", "name_not_quotable", ['XB "seven"']]]


def test_a_scope_awaits_each_round_of_lookups():
    assert lookups_needed(PD1_IN_LUNG, {}) == [VERSION, PD1_CLASS]
    first = {VERSION: ANSWERS[VERSION], PD1_CLASS: ANSWERS[PD1_CLASS]}
    assert lookups_needed(PD1_IN_LUNG, first) == [PD1_MEMBERS]
    assert lookups_needed(PD1_IN_LUNG, ANSWERS) == []
    waiting = resolve_scope(PD1_IN_LUNG, first)
    assert waiting["code"] == "awaiting_lookups" and waiting["query"] == {}
    assert waiting["release"] == ["found", "05-Oct-2026", VERSION]
    assert resolve_scope(PD1_IN_LUNG, {})["release"] == ["pending", "", VERSION]


def test_no_lookup_is_named_for_a_refused_or_unresolvable_request():
    assert lookups_needed({}, {}) == []
    assert lookups_needed({"drug_class": {"name": "x", "source": "EPC"}, "mechanism": "KRAS"}, {}) == []
    refused = resolve_scope({"sponsor": "Merck"}, ANSWERS)
    assert refused == {
        "code": "refused",
        "check": ["unknown_slot", ["sponsor"]],
        "join": request.JOIN,
        "slots": [],
        "expansions": [],
        "lookups": [],
        "pending": [],
        "stops": [],
        "query": {},
        "release": ["not_asked", "", ""],
        "release_basis": "",
    }


def test_slots_without_lookups_resolve_alone_in_the_registry_own_forms():
    item = {
        "condition": "non-small cell lung cancer",
        "phase": ["PHASE2", "PHASE3", "PHASE2"],
        "status": ["RECRUITING", "NOT_YET_RECRUITING"],
        "start_from": "2015-01-01",
        "start_to": "2020-12-31",
        "params": {"query.term": "biomarker"},
    }
    scope = resolve_scope(item, {})
    assert scope["code"] == "resolved" and scope["lookups"] == []
    assert scope["query"] == {
        "filter.advanced": "(AREA[Phase]PHASE2 OR AREA[Phase]PHASE3) AND "
        "(AREA[OverallStatus]RECRUITING OR AREA[OverallStatus]NOT_YET_RECRUITING) AND "
        "AREA[StartDate]RANGE[2015-01-01,2020-12-31]",
        "query.cond": "non-small cell lung cancer",
        "query.term": "biomarker",
    }
    assert [s["clause"] for s in scope["slots"]][-3:] == [
        "AREA[StartDate]RANGE[2015-01-01,2020-12-31]",
        "AREA[StartDate]RANGE[2015-01-01,2020-12-31]",
        "",
    ]
    assert scope["slots"][0] == {
        "slot": "condition",
        "value": "non-small cell lung cancer",
        "clause": "non-small cell lung cancer",
    }
    assert resolve_scope({"params": {"filter.ids": "NCT04852770"}}, {})["query"] == {
        "filter.ids": "NCT04852770"
    }


def test_a_query_check_query_refuses_is_named():
    scope = resolve_scope({"condition": "NCT01030536", "phase": ["PHASE2"]}, {})
    assert scope["code"] == "unresolved" and scope["query"] == {}
    assert scope["stops"] == [["query", "query_filters_ignored", ["query.cond"]]]
    long = {"condition": "NCT01030536", "phase": ["PHASE2"], "params": {"query.term": "x" * QUERY_LIMIT}}
    assert resolve_scope(long, {})["stops"] == [["query", "query_filters_ignored", ["query.cond"]]]
    assert resolve_scope({"params": {"query.term": "x" * QUERY_LIMIT}}, {})["stops"] == [
        ["query", "query_too_long", [QUERY_LIMIT + len("query.term="), QUERY_LIMIT]]
    ]
    assert resolve_scope({"params": {"query.term": "x" * (QUERY_LIMIT - len("query.term="))}}, {})[
        "code"
    ] == ("resolved")


def test_a_release_rxnav_cannot_state_is_kept_as_its_code():
    answers = ANSWERS | {VERSION: [503, None]}
    scope = resolve_scope(ALK_ATC, answers)
    assert scope["code"] == "resolved" and scope["release"] == ["lookup_failed", "", VERSION]
    assert {e["release"] for e in scope["expansions"]} == {""}
    malformed = resolve_scope(ALK_ATC, ANSWERS | {VERSION: [200, {"version": ""}]})
    assert malformed["code"] == "resolved" and malformed["release"] == ["malformed", "", VERSION]
    assert malformed["release_basis"] == request.RELEASE_BASIS
