"""Source RxNorm identities and RxClass axes keep distinct entities and source subjects.

Exact concept equality can confirm identity; shared ingredients establish related forms only. No
combination, target or drug identity is inferred from clinical wording.
"""

import json

import pytest
from rxnav_fake import FakeRxNav

from TrialLedger import classes as rx
from TrialLedger.classes import (
    alias_role,
    class_standing,
    drug_atc,
    drug_axes,
    entails_membership,
    load_or_lookup_at,
    mesh_scope,
    name_identity,
    rxclass_assertions,
    rxnav_release,
    rxnorm_concepts,
    rxnorm_ids,
    shares_structure_class,
    target_alignment,
)

GEFITINIB_ATC = {
    "rxclassDrugInfoList": {
        "rxclassDrugInfo": [
            {
                "minConcept": {"rxcui": "328134", "name": "gefitinib", "tty": "IN"},
                "rxclassMinConceptItem": {
                    "classId": "L01EB",
                    "className": "Epidermal growth factor receptor (EGFR) tyrosine kinase inhibitors",
                    "classType": "ATC1-4",
                },
                "rela": "",
                "relaSource": "ATC",
            }
        ]
    }
}
KEYTRUDA_ATC = {
    "rxclassDrugInfoList": {
        "rxclassDrugInfo": [
            {
                "minConcept": {"rxcui": "1547545", "name": "pembrolizumab", "tty": "IN"},
                "rxclassMinConceptItem": {
                    "classId": "L01FF",
                    "className": "PD-1/PD-L1 (Programmed cell death protein 1/death ligand 1) inhibitors",
                    "classType": "ATC1-4",
                },
                "rela": "",
                "relaSource": "ATC",
            }
        ]
    }
}
CISPLATIN_FDASPL = {
    "rxclassDrugInfoList": {
        "rxclassDrugInfo": [
            {
                "minConcept": {"rxcui": "2555", "name": "cisplatin", "tty": "IN"},
                "rxclassMinConceptItem": {
                    "classId": "N0000175073",
                    "className": "Platinum-containing Compounds",
                    "classType": "CHEM",
                },
                "rela": "has_chemical_structure",
                "relaSource": "FDASPL",
            }
        ]
    }
}
KEYTRUDA_PROPERTIES = {
    "properties": {
        "rxcui": "1547550",
        "name": "Keytruda",
        "synonym": "",
        "tty": "BN",
        "language": "ENG",
        "suppress": "N",
        "umlscui": "",
    }
}
KEYTRUDA_RELATED = {
    "relatedGroup": {
        "rxcui": None,
        "conceptGroup": [
            {
                "tty": "IN",
                "conceptProperties": [
                    {
                        "rxcui": "1547545",
                        "name": "pembrolizumab",
                        "synonym": "",
                        "tty": "IN",
                        "language": "ENG",
                    }
                ],
            }
        ],
    }
}
TECENTRIQ_HYBREZA_RELATED = {
    "relatedGroup": {
        "conceptGroup": [
            {
                "tty": "IN",
                "conceptProperties": [
                    {"rxcui": "1792776", "name": "atezolizumab", "tty": "IN"},
                    {"rxcui": "5464", "name": "hyaluronidase", "tty": "IN"},
                ],
            }
        ]
    }
}


def test_an_rxclass_answer_keeps_the_concept_each_class_is_asserted_of():
    assert rxclass_assertions(200, KEYTRUDA_ATC) == (
        "found",
        [
            (
                "L01FF",
                "PD-1/PD-L1 (Programmed cell death protein 1/death ligand 1) inhibitors",
                "ATC1-4",
                "",
                "ATC",
                "1547545",
                "pembrolizumab",
                "IN",
            )
        ],
    )
    code, [assertion] = rxclass_assertions(200, CISPLATIN_FDASPL)
    assert code == "found" and assertion[3:6] == ("has_chemical_structure", "FDASPL", "2555")


@pytest.mark.parametrize(
    "status, body, code",
    [
        (200, {}, "not_found"),
        (200, [], "malformed"),
        (200, {"rxclassDrugInfoList": {"rxclassDrugInfo": []}}, "malformed"),
        (200, {"rxclassDrugInfoList": {"rxclassDrugInfo": ["x"]}}, "malformed"),
        # a class without the concept it is asserted of is never attributed to the name asked
        (
            200,
            {"rxclassDrugInfoList": {"rxclassDrugInfo": [{"rxclassMinConceptItem": {"classId": "L01FF"}}]}},
            "malformed",
        ),
        (503, GEFITINIB_ATC, "lookup_failed"),
        (0, None, "lookup_failed"),
    ],
)
def test_no_assertion_has_a_named_reason(status, body, code):
    assert rxclass_assertions(status, body) == (code, [])


def test_rxnorm_answers_are_read_or_named():
    assert rxnorm_ids(200, {"idGroup": {"rxnormId": ["1547550"]}}) == ("found", ["1547550"])
    assert rxnorm_ids(200, {"idGroup": {"name": "SHR-1316"}}) == ("not_found", [])
    assert rxnorm_ids(200, {"idGroup": {"rxnormId": []}}) == ("malformed", [])
    assert rxnorm_ids(200, {"idGroup": None}) == ("malformed", [])
    assert rxnorm_ids(500, None) == ("lookup_failed", [])
    assert rxnorm_concepts(200, KEYTRUDA_PROPERTIES) == ("found", [("1547550", "Keytruda", "BN")])
    assert rxnorm_concepts(200, KEYTRUDA_RELATED) == ("found", [("1547545", "pembrolizumab", "IN")])
    assert rxnorm_concepts(200, {"relatedGroup": {"conceptGroup": [{"tty": "IN"}]}}) == ("not_found", [])
    assert rxnorm_concepts(200, {}) == ("not_found", [])
    assert rxnorm_concepts(200, {"properties": {"rxcui": 1}}) == ("malformed", [])
    assert rxnorm_concepts(200, {"relatedGroup": {"conceptGroup": "IN"}}) == ("malformed", [])
    assert rxnorm_concepts(
        200, {"relatedGroup": {"conceptGroup": [{"conceptProperties": {"rxcui": "1"}}]}}
    ) == (
        "malformed",
        [],
    )
    assert rxnorm_concepts(404, None) == ("lookup_failed", [])
    assert rxnav_release(200, {"version": "05-Oct-2026", "apiVersion": "3.1.356"}) == ("found", "05-Oct-2026")
    assert rxnav_release(200, {"version": ""}) == ("malformed", "")
    assert rxnav_release(503, None) == ("lookup_failed", "")


NOT_ASKED = ("not_asked", [])


@pytest.mark.parametrize(
    "ids, concept, ingredients, expected",
    [
        (
            ("found", ["328134"]),
            ("found", [("328134", "gefitinib", "IN")]),
            NOT_ASKED,
            ("ingredient", "328134"),
        ),
        (
            ("found", ["1721559"]),
            ("found", [("1721559", "osimertinib mesylate", "PIN")]),
            ("found", [("1721560", "osimertinib", "IN")]),
            ("precise_ingredient", "1721559"),
        ),
        (
            ("found", ["1547550"]),
            ("found", [("1547550", "Keytruda", "BN")]),
            ("found", [("1547545", "pembrolizumab", "IN")]),
            ("brand", "1547550"),
        ),
        (
            ("found", ["2693894"]),
            ("found", [("2693894", "Tecentriq Hybreza", "BN")]),
            rxnorm_concepts(200, TECENTRIQ_HYBREZA_RELATED),
            ("combination", "2693894"),
        ),
        (
            ("found", ["9"]),
            ("found", [("9", "a / b", "MIN")]),
            ("not_found", []),
            ("combination", "9"),
        ),
        (
            ("found", ["9"]),
            ("found", [("9", "cisplatin 1 MG/ML Injectable Solution", "SCD")]),
            ("found", [("2555", "cisplatin", "IN")]),
            ("other_form", "9"),
        ),
    ],
)
def test_rxnorm_resolves_what_a_name_is(ids, concept, ingredients, expected):
    assert name_identity(ids, concept, ingredients)[:2] == expected


@pytest.mark.parametrize(
    "ids, concept, ingredients, code",
    [
        (("not_found", []), NOT_ASKED, NOT_ASKED, "not_in_rxnorm"),
        (("found", ["1", "2"]), NOT_ASKED, NOT_ASKED, "ambiguous"),
        (("malformed", []), NOT_ASKED, NOT_ASKED, "unresolved"),
        (("found", ["1"]), ("malformed", []), NOT_ASKED, "unresolved"),
        (("found", ["1"]), ("found", [("1", "X", "BN")]), ("not_found", []), "unresolved"),
        (("lookup_failed", []), NOT_ASKED, NOT_ASKED, "lookup_failed"),
        (("found", ["1"]), ("found", [("1", "X", "BN")]), ("lookup_failed", []), "lookup_failed"),
    ],
)
def test_an_unresolved_identity_has_a_named_reason(ids, concept, ingredients, code):
    assert name_identity(ids, concept, ingredients) == (code, "", [])


def test_a_class_is_the_names_own_only_when_asserted_of_its_own_concept():
    assert class_standing("ingredient", "328134", ["328134"], "328134") == "known"
    assert class_standing("precise_ingredient", "1721559", ["1721560"], "1721559") == "known"
    # RxClass answers Keytruda as pembrolizumab: the brand does not inherit the ingredient's class
    assert class_standing("brand", "1547550", ["1547545"], "1547545") == "not_inherited"
    assert class_standing("precise_ingredient", "1721559", ["1721560"], "1721560") == "not_inherited"
    assert class_standing("combination", "2693894", ["1792776", "5464"], "1792776") == "not_inherited"
    assert class_standing("ingredient", "328134", ["328134"], "1721560") == "other_entity"
    assert class_standing("not_in_rxnorm", "", [], "1547545") == "identity_unresolved"
    assert class_standing("ambiguous", "", [], "1547545") == "identity_unresolved"
    assert class_standing("lookup_failed", "", [], "1547545") == "identity_lookup_failed"


RETRIEVED = "2026-11-01T00:00:00+00:00"


def warrant(url, params):
    return {"url": url, "params": params, "retrieved": RETRIEVED}


def axes_answer(
    ids, concept, ingredients, atc=None, structure=None, release=("found", "05-Oct-2026"), name="X"
):
    def axis(source, rela, assertions):
        params = {"drugName": name, "relaSource": source} | ({"relas": rela} if rela else {})
        request = warrant(rx.RXCLASS, params)
        return {
            "code": "not_found",
            "assertions": assertions or [],
            "release": list(release),
            "request": request,
        }

    identity = {
        "ids": ids,
        "concept": concept,
        "ingredients": ingredients,
        "requests": [warrant(rx.RXNORM_IDS, {"name": name, "search": "0"})],
        "release": list(release),
    }
    return json.loads(
        json.dumps(
            {
                "codes": {},
                "classes": [],
                "axes": {
                    "identity": identity,
                    "ATC": axis("ATC", "", atc),
                    "DAILYMED:has_chemical_structure": axis("DAILYMED", "has_chemical_structure", []),
                    "FDASPL:has_chemical_structure": axis("FDASPL", "has_chemical_structure", structure),
                },
            }
        )
    )


PEMBRO_ATC = rxclass_assertions(200, KEYTRUDA_ATC)[1]
CARBOPLATIN_ATC = [("L01XA", "Platinum compounds", "ATC1-4", "", "ATC", "40048", "carboplatin", "IN")]
ANSWERS = {
    "Keytruda": axes_answer(
        ("found", ["1547550"]),
        ("found", [("1547550", "Keytruda", "BN")]),
        ("found", [("1547545", "pembrolizumab", "IN")]),
        atc=PEMBRO_ATC,
        name="Keytruda",
    ),
    "pembrolizumab": axes_answer(
        ("found", ["1547545"]),
        ("found", [("1547545", "pembrolizumab", "IN")]),
        NOT_ASKED,
        atc=PEMBRO_ATC,
        name="pembrolizumab",
    ),
    "gefitinib": axes_answer(
        ("found", ["328134"]),
        ("found", [("328134", "gefitinib", "IN")]),
        NOT_ASKED,
        atc=rxclass_assertions(200, GEFITINIB_ATC)[1],
        name="gefitinib",
    ),
    "SHR-1316": axes_answer(("not_found", []), NOT_ASKED, NOT_ASKED),
    # RxNorm holds neither the combination's name nor the code name; RxClass, asked by the alias, answers
    # carboplatin's class (the shape of its answer for a name it reads as carboplatin)
    "Carboplatin/Pemetrexed": axes_answer(("not_found", []), NOT_ASKED, NOT_ASKED, atc=CARBOPLATIN_ATC),
    "carboplatin": axes_answer(
        ("found", ["40048"]),
        ("found", [("40048", "carboplatin", "IN")]),
        NOT_ASKED,
        atc=CARBOPLATIN_ATC,
        name="carboplatin",
    ),
    "XB-1": axes_answer(("not_found", []), NOT_ASKED, NOT_ASKED),
    "XB-1 + carboplatin": axes_answer(
        ("found", ["9004"]),
        ("found", [("9004", "XB-1 / carboplatin", "MIN")]),
        ("found", [("9005", "xb-1", "IN"), ("40048", "carboplatin", "IN")]),
        atc=CARBOPLATIN_ATC,
    ),
    "Failing": axes_answer(("lookup_failed", []), NOT_ASKED, NOT_ASKED, atc=PEMBRO_ATC),
}

# Every hand-built identity response records the exact name whose answer it represents.
for recorded_name, answer in ANSWERS.items():
    answer["axes"]["identity"]["requests"][0]["params"]["name"] = recorded_name


def test_the_own_name_decides_and_an_alias_of_its_concept_confirms_it():
    code, reason, identities, assertions = drug_axes(["pembrolizumab", "Keytruda", "never asked"], ANSWERS)
    assert (code, reason) == ("resolved", "own_name")
    assert [(i[0], i[1], i[4]) for i in identities] == [
        ("pembrolizumab", "ingredient", "own"),
        ("Keytruda", "brand", "related_form"),
    ]
    # RxClass answers Keytruda as pembrolizumab: asked by either name, the class is the own concept's
    assert [(a[0], a[2], a[5]) for a in assertions] == [
        ("Keytruda", "L01FF", "known"),
        ("pembrolizumab", "L01FF", "known"),
    ]
    release, request, retrieved = assertions[1][8:]
    assert release == "05-Oct-2026" and retrieved == RETRIEVED
    assert request == rx.RXCLASS + "?drugName=pembrolizumab&relaSource=ATC"
    assert identities[0][5] == ((rx.RXNORM_IDS + "?name=pembrolizumab&search=0", RETRIEVED),)
    assert identities[0][6] == "05-Oct-2026"


def test_a_brand_own_name_never_takes_its_ingredients_class_from_an_alias():
    code, reason, identities, assertions = drug_axes(["Keytruda", "pembrolizumab"], ANSWERS)
    assert (code, reason) == ("resolved", "own_name")
    assert identities[1][4] == "related_form"
    assert {a[5] for a in assertions} == {"not_inherited"}


def test_an_unheld_own_name_is_unresolved_whatever_its_alias_resolves_to():
    code, reason, identities, assertions = drug_axes(["Carboplatin/Pemetrexed", "carboplatin"], ANSWERS)
    assert (code, reason) == ("unresolved", "alias_other_concept")
    assert [(i[0], i[1], i[4]) for i in identities] == [
        ("Carboplatin/Pemetrexed", "not_in_rxnorm", "own"),
        ("carboplatin", "ingredient", "alias_other_concept"),
    ]
    assert {a[5] for a in assertions} == {"identity_unresolved"}
    code, reason, identities, assertions = drug_axes(["XB-1", "XB-1 + carboplatin"], ANSWERS)
    assert (code, reason) == ("unresolved", "alias_is_combination")
    assert {a[5] for a in assertions} == {"identity_unresolved"}
    assert drug_axes(["SHR-1316"], ANSWERS)[:2] == ("unresolved", "own_name_not_in_rxnorm")
    assert drug_axes(["never asked", "pembrolizumab"], ANSWERS) == (
        "unresolved",
        "own_name_not_asked",
        [],
        [],
    )
    code, reason, _, assertions = drug_axes(["Failing", "pembrolizumab"], ANSWERS)
    assert (code, reason) == ("lookup_failed", "own_name_lookup_failed")
    assert {a[5] for a in assertions} == {"identity_lookup_failed"}


def test_an_alias_naming_another_concept_is_a_conflict_and_nothing_is_known():
    code, reason, _, assertions = drug_axes(["pembrolizumab", "gefitinib"], ANSWERS)
    assert (code, reason) == ("conflict", "alias_other_concept")
    assert {a[5] for a in assertions} == {"identity_conflict", "other_entity"}
    assert not any(a[5] == "known" for a in assertions)
    code, reason, _, _ = drug_axes(["carboplatin", "XB-1 + carboplatin"], ANSWERS)
    assert (code, reason) == ("conflict", "alias_is_combination")


def test_an_alias_role_never_supplies_a_concept():
    single = ("ingredient", "40048", ["40048"])
    combination = ("combination", "9004", ["40048", "9005"])
    unheld = ("not_in_rxnorm", "", [])
    assert alias_role(single, ("brand", "1", ["40048"])) == "related_form"
    assert alias_role(combination, single) == "alias_is_one_ingredient"
    assert alias_role(unheld, single) == "alias_other_concept"
    assert alias_role(single, combination) == "alias_is_combination"
    assert alias_role(unheld, combination) == "alias_is_combination"
    assert alias_role(unheld, single) == "alias_other_concept"
    assert alias_role(("ingredient", "328134", ["328134"]), single) == "alias_other_concept"
    assert alias_role(combination, ("ingredient", "7", ["7"])) == "alias_other_concept"
    assert alias_role(single, unheld) == "alias_not_resolved"


PLATINUM = ("FDASPL:has_chemical_structure", "N0000175073", "Platinum-containing Compounds", "05-Oct-2026")


def test_two_drugs_sharing_a_structure_class_are_related_by_it():
    assert shares_structure_class(("carboplatin", [PLATINUM]), ("cisplatin", [PLATINUM])) == [
        (
            "carboplatin",
            "cisplatin",
            "FDASPL:has_chemical_structure",
            "N0000175073 Platinum-containing Compounds",
            "05-Oct-2026",
        )
    ]


def test_structure_is_never_merged_across_sources_releases_or_a_drug_and_itself():
    dailymed = ("DAILYMED:has_chemical_structure", *PLATINUM[1:])
    later = (*PLATINUM[:3], "02-Nov-2026")
    unknown = (*PLATINUM[:3], "")
    assert shares_structure_class(("carboplatin", [PLATINUM]), ("cisplatin", [dailymed])) == []
    assert shares_structure_class(("carboplatin", [PLATINUM]), ("cisplatin", [later])) == []
    assert shares_structure_class(("carboplatin", [unknown]), ("cisplatin", [unknown])) == []
    assert shares_structure_class(("cisplatin", [PLATINUM]), ("cisplatin", [PLATINUM])) == []


def test_only_a_relation_that_entails_membership_makes_a_member():
    assert entails_membership("equivalent_to") and entails_membership("narrower_than")
    for relation in ("broader_than", "overlaps", "unresolved", "homolog"):
        assert not entails_membership(relation)


def test_own_targets_align_to_atc_by_the_crosswalk():
    assert target_alignment(["PD-1", "radiotherapy"]) == [
        (
            "PD-1",
            "L01FF",
            "PD-1/PD-L1 (Programmed cell death protein 1/death ligand 1) inhibitors",
            "overlaps",
            False,
            rx.RXCLASS_BY_ID + "L01FF",
            "2026-11-01",
        ),
        ("radiotherapy", "", "", "unresolved", False, "", ""),
    ]
    egfr = target_alignment(["EGFR inhibitor"])
    assert [(row[1], row[3], row[4]) for row in egfr] == [
        ("L01EB", "broader_than", False),
        ("L01FE", "broader_than", False),
    ]


def test_every_crosswalk_row_names_a_relation_cites_its_source_and_its_request():
    relations = {"equivalent_to", "narrower_than", "broader_than", "overlaps", "unresolved"}
    for target, atc, name, relation, citation, request, read in rx.CROSSWALK:
        assert target and atc and name and citation and relation in relations
        assert request == rx.RXCLASS_BY_ID + atc and read == "2026-11-01"


def test_no_crosswalk_row_is_keyed_by_a_drug_name():
    named = {"platinum", "cisplatin", "carboplatin", "taxane", "paclitaxel", "docetaxel", "pemetrexed"}
    assert not named & {row[0] for row in rx.CROSSWALK}


def test_a_drug_has_atc_classes_by_rxclass_first_then_by_entailed_membership_only():
    assert drug_atc(["L01FF", "L01FF"], ["PD-1"], []) == ("rxclass", ["L01FF"])
    # a row entailing membership (none of the present crosswalk does) gives its class
    entailed = [
        ("T", "L01XX", "Other", "equivalent_to", True, "", ""),
        ("U", "L01YY", "Y", "narrower_than", True, "", ""),
    ]
    assert drug_atc([], ["U", "T"], entailed) == ("crosswalk", ["L01XX", "L01YY"])
    # PD-1 overlaps L01FF: no membership, so no classes; a partly entailed drug is not known either
    assert drug_atc([], ["PD-1"], target_alignment(["PD-1"])) == ("", [])
    assert drug_atc([], ["T", "PD-1"], entailed + target_alignment(["PD-1"])) == ("", [])
    assert drug_atc([], [], []) == ("", [])


def test_intervention_mesh_stays_at_trial_level_unless_literally_one_interventions_name():
    names = {"Testamab": ["Testamab", "TM-1"], "Carboplatin": ["Carboplatin"], "Paraplatin": ["carboplatin"]}
    meshes = [
        {"id": "D000003", "term": "testamab"},
        {"id": "D016190", "term": "Carboplatin"},
        {"id": "D000970", "term": "Antineoplastic Agents"},
        {"id": 7, "term": "skipped"},
    ]
    assert mesh_scope(meshes, names) == [
        ("D000003", "testamab", "intervention", "Testamab"),
        ("D016190", "Carboplatin", "trial", ""),
        ("D000970", "Antineoplastic Agents", "trial", ""),
    ]
    assert mesh_scope(None, names) == []


GEFITINIB = {
    "names": {"gefitinib": ["328134"], "Placebo": ["8375"]},
    "concepts": {"328134": ("gefitinib", "IN"), "8375": ("placebo", "IN")},
    "classes": {
        "328134": [
            (
                "L01EB",
                "Epidermal growth factor receptor (EGFR) tyrosine kinase inhibitors",
                "ATC1-4",
                "",
                "ATC",
                "328134",
            )
        ]
    },
}


def test_a_name_cached_before_the_axes_is_asked_for_them_alone(tmp_path):
    path = tmp_path / "classes.json"
    old = {"codes": {"DAILYMED:has_epc": "found"}, "classes": [["N1", "X", "has_epc", "DAILYMED"]]}
    path.write_text(json.dumps({"answers": {"gefitinib": old}}))
    get = FakeRxNav(**GEFITINIB)
    answers = load_or_lookup_at(
        path, ["gefitinib"], ["gefitinib"], fill_axes=True, get=get, sleep=lambda _: None
    )
    assert [url.rsplit("/", 1)[-1] for url, _ in get.asked] == [
        "version.json",
        "rxcui.json",
        "properties.json",
        "byRxcui.json",
        "version.json",
    ]
    assert answers["gefitinib"]["classes"] == old["classes"]
    atc = answers["gefitinib"]["axes"]["ATC"]
    assert atc["code"] == "found" and atc["release"][:2] == ["found", "05-Oct-2026"]
    assert atc["request"]["params"] == {"rxcui": "328134"} and atc["request"]["retrieved"]
    assert [a[0] for a in atc["assertions"]] == ["L01EB"]
    # the structure axes are read from the same answer: RxClass states none of gefitinib
    assert answers["gefitinib"]["axes"]["FDASPL:has_chemical_structure"]["code"] == "not_found"
    assert json.loads(path.read_text())["answers"]["gefitinib"]["axes"]["identity"]["ids"] == [
        "found",
        ["328134"],
    ]
    get.asked.clear()
    load_or_lookup_at(path, ["gefitinib"], ["gefitinib"], fill_axes=True, get=get, sleep=lambda _: None)
    assert get.asked == []


def test_a_name_no_experimental_drug_carries_is_never_given_axes(tmp_path):
    get = FakeRxNav(**GEFITINIB)
    answers = load_or_lookup_at(
        tmp_path / "c.json", ["Placebo", "XB-1"], ["XB-1"], fill_axes=True, get=get, sleep=lambda _: None
    )
    assert "axes" not in answers["Placebo"] and "axes" in answers["XB-1"]
    # one batch: the release before and after it, each name's identity once; Placebo's concept is classed
    # but never described, XB-1 (not in RxNorm) neither
    assert get.count(rx.RXNAV_VERSION) == 2 and get.count(rx.RXNORM_IDS) == 2
    assert [p for url, p in get.asked if url == rx.RXCLASS_BY_RXCUI] == [{"rxcui": "8375"}]
    assert not any(url.endswith("properties.json") for url, _ in get.asked)
    assert answers["XB-1"]["axes"]["identity"]["ids"] == ["not_found", []]
    assert answers["XB-1"]["axes"]["ATC"]["code"] == "not_in_rxnorm"


def test_the_axes_are_kept_only_when_filled_and_epc_moa_as_before(tmp_path):
    """Positive: with fill_axes the axes are kept, and EPC and MoA asked exactly as without it, request for
    request. Negative: without it no RxNav request about the axes alone is made (no concept's properties or
    ingredients), on a cold cache or on one whose names were cached before the axes, which is left as it
    was."""

    def run(path, fill):
        get = FakeRxNav(**GEFITINIB)
        answers = load_or_lookup_at(
            path, ["Placebo", "gefitinib"], ["gefitinib"], fill_axes=fill, get=get, sleep=lambda _: None
        )
        return [(url, tuple(sorted(params.items()))) for url, params in get.asked], answers

    def classes_only(asked):
        return [a for a in asked if not a[0].endswith(("properties.json", "related.json"))]

    (lazy, lazy_answers), (filled, filled_answers) = (
        run(tmp_path / "lazy.json", False),
        run(tmp_path / "f.json", True),
    )
    assert classes_only(lazy) == lazy and len(lazy) == 6
    assert classes_only(filled) == lazy and len(filled) > len(lazy)
    assert not any("axes" in answer for answer in lazy_answers.values())
    assert {k: v["classes"] for k, v in lazy_answers.items()} == {
        k: v["classes"] for k, v in filled_answers.items()
    }
    before = tmp_path / "before.json"
    old = {"codes": {"DAILYMED:has_epc": "not_found"}, "classes": []}
    before.write_text(json.dumps({"answers": {"Placebo": old, "gefitinib": old}}))
    text = before.read_text()
    assert run(before, False)[0] == [] and before.read_text() == text
