"""Universes (refine-landscape-record 2.1-2.4): the assignment, the packs it permits, and the coordinates
coherence.resolve computes under them.

Positive: the three trials asked for by number are assigned exactly as the contract's worked example says
(general, haematologic, solid from the free-text condition); a trial whose only condition names no disease is
solid from its titles, and from its drug's ATC class when the titles name no cancer (an other name counts); a
supportive-care trial in cancer patients is solid oncology but gets no setting or line; a lymphoma trial's
antineoplastic drug counts as haematologic; solid and haematologic conditions give the union; every one of the
49 osimertinib trials is in an oncology universe; a fragment may declare universes.
Negative: a study with no usable condition and no oncology signal is scope unresolved, never general; in relay
mode the drug source reads "not looked up", never "no class"; a non-treatment trial's drugs are never read; a
rheumatoid arthritis trial of methotrexate (L01) is never oncology; membership alone permits no pack; a
coordinate no permitted pack owns is never computed; resolve without an assignment is unchanged; a fragment
naming an unknown universe is refused, and one naming none keeps the registry's version.
"""

import copy
import json
from pathlib import Path

import pytest

from TrialLedger import coherence, contract, universes
from TrialLedger.semantics import loader
from TrialLedger.universes import (
    Assignment,
    assign,
    atc_classes,
    counted_universe,
    drug_anchor,
    permitted_packs,
    reading,
    scope_case,
    term_hits,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "contract"
BODIES = {
    study["protocolSection"]["identificationModule"]["nctId"]: study
    for name in ("studies-ids-3.json", "studies-osimertinib-subset.json")
    for study in json.loads((FIXTURES / name).read_text(encoding="utf-8"))["studies"]
}
BASELINE = Path.home() / "tools" / "TrialLedger-runs" / "baseline-2026-11-01" / "osimertinib-phase3-49"
# RxNav's ATC answers for the fixtures' drug names, as the baseline runs' classes.json records them
# (2026-11-01); a name absent here was never asked.
CLASSES = {
    "Carboplatin": ("L01XA",),
    "Everolimus": ("L01EG", "L04AH"),
    "Temozolomide": ("L01AX",),
    "Trametinib": ("L01EE",),
    "Adavosertib": (),
    "Veliparib": (),
    **{f"CAT-8015 {dose} mcg/kg": () for dose in (20, 30, 40, 50, 60)},
    "Osimertinib": ("L01EB",),
    "Chemotherapy": (),
    "Cross-over to Osimertinib": (),
    "docetaxel, bevacizumab": (),
}
SETTING_PACK = "oncology.solid/setting_and_line"


def study(conditions=(), mesh=(), ancestors=(), purpose="TREATMENT", interventions=(), titles=("", "")):
    """A minimal registry study of API v2's shape."""
    design = {"designInfo": {"primaryPurpose": purpose}} if purpose else {}
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT00000000",
                **({"briefTitle": titles[0]} if titles[0] else {}),
                **({"officialTitle": titles[1]} if titles[1] else {}),
            },
            "conditionsModule": {"conditions": list(conditions)},
            "designModule": design,
            "armsInterventionsModule": {
                "interventions": [
                    {"type": "DRUG", "name": name, **({"otherNames": list(other)} if other else {})}
                    for name, *other in interventions
                ]
            },
        },
        "derivedSection": {
            "conditionBrowseModule": {
                "meshes": [{"term": term} for term in mesh],
                "ancestors": [{"term": term} for term in ancestors],
            }
        },
    }


def source(assignment, name):
    return next(entry for entry in assignment.sources if entry["source"] == name)


# ── the named fixtures (2.4) ───────────────────────────────────────────────────────────────────────────


def test_the_three_trials_by_number_are_the_contracts_worked_example():
    example = json.loads((FIXTURES / "examples" / "universes.json").read_text(encoding="utf-8"))
    for nct, expected in example.items():
        assert reading(assign(BODIES[nct], CLASSES)) == expected, nct


def test_the_ptsd_trial_is_general_and_says_why():
    """Positive: general, from its condition MeSH terms, the index words naming them. Negative: no pack, and
    its behavioural interventions are never read as having no class."""
    found = assign(BODIES["NCT04852770"], CLASSES)
    assert (found.case, found.universes, found.decided_by) == ("general", ("general",), "condition_mesh")
    assert found.packs == ()
    assert found.words == (
        "General: no domain readings apply (condition MeSH: Stress Disorders, Post-Traumatic; COVID-19)"
    )
    assert source(found, "drug_class")["status"] == "not_looked_up"


def test_the_lymphoma_and_cll_trial_is_haematologic_with_prior_lines_only():
    found = assign(BODIES["NCT01030536"], CLASSES)
    assert (found.universes, found.decided_by) == (("oncology.heme",), "condition_mesh")
    assert found.packs == ("oncology.heme/prior_lines",)
    anchors = [finding["anchor"] for finding in source(found, "condition_mesh")["found"]]
    assert anchors == ["Lymphoma", "Leukemia"]  # Neoplasms, an ancestor too, is not listed beside them
    assert found.words.startswith("Haematologic oncology (condition MeSH: Lymphoma, Non-Hodgkin")


def test_the_basket_without_condition_mesh_is_solid_from_its_free_text_condition():
    found = assign(BODIES["NCT01827384"], CLASSES)
    assert (found.universes, found.decided_by) == (("oncology.solid",), "free_text")
    assert source(found, "condition_mesh")["status"] == "no_terms"
    assert found.words == "Solid-tumour oncology (conditions: Advanced Malignant Solid Neoplasm)"
    assert SETTING_PACK in found.packs


@pytest.mark.parametrize("nct", ["NCT02959749", "NCT02151981"])
def test_a_trial_whose_condition_names_no_disease_is_solid_from_its_titles_and_its_drug(nct):
    """The baseline bodies name non-small cell lung cancer in their titles, so the titles decide; the drug
    source agrees (NCT02151981 reaches osimertinib only through an intervention's other name)."""
    found = assign(BODIES[nct], CLASSES)
    assert (found.case, found.universes, found.decided_by) == ("oncology", ("oncology.solid",), "free_text")
    assert source(found, "free_text")["status"] == "titles"
    assert source(found, "free_text")["non_oncology"] == []
    assert [f["term"] for f in source(found, "drug_class")["found"]] == ["Osimertinib"]
    assert found.words.startswith("Solid-tumour oncology (title: ")


def test_without_a_cancer_in_its_titles_the_drug_class_decides_and_in_relay_mode_nothing_does():
    """Positive: the Progression Free Survival trial with neutral titles is solid from osimertinib's ATC class
    (L01). Negative: in relay mode the drug source is not looked up, and the trial is scope unresolved, never
    general, each source's finding in its words."""
    body = copy.deepcopy(BODIES["NCT02959749"])
    body["protocolSection"]["identificationModule"].update(briefTitle="Study A", officialTitle="Study A")
    found = assign(body, CLASSES)
    assert (found.universes, found.decided_by) == (("oncology.solid",), "drug_class")
    assert found.words == "Solid-tumour oncology (drug class: Osimertinib, antineoplastic agents (ATC L01))"
    relayed = assign(body, None)
    assert (relayed.case, relayed.code, relayed.universes, relayed.packs) == (
        "unresolved",
        "unresolved_no_domain",
        (),
        (),
    )
    assert source(relayed, "drug_class")["status"] == "not_looked_up"
    assert relayed.words == (
        "Scope unresolved — no source identifies a domain: no condition MeSH term; the conditions name no "
        "disease (Progression Free Survival (an outcome)); no title names a cancer; drug class: the drugs' "
        "classes were not looked up (relay mode, or a name never asked of RxNav)"
    )
    assert reading(relayed)["status"] == "unresolved"
    assert reading(relayed)["words"] == ["Progression Free Survival"]


def test_no_usable_condition_is_unresolved_beside_an_identified_non_oncology_study_which_is_general():
    unusable = assign(study(conditions=["Overall Survival"]), {})
    assert (unusable.case, unusable.universes) == ("unresolved", ())
    identified = assign(study(conditions=["Asthma"]), {})
    assert (identified.case, identified.universes, identified.decided_by) == (
        "general",
        ("general",),
        "free_text",
    )
    assert identified.words == "General: no domain readings apply (conditions: Asthma)"


def test_a_condition_the_vocabulary_misses_is_no_evidence_of_another_domain():
    """Negative: a biomarker condition no table names, in a trial without condition MeSH, is never general and
    never a disagreement; the titles name the cancer. Without them it is scope unresolved, never general."""
    body = copy.deepcopy(BODIES["NCT02296125"])
    body["protocolSection"]["conditionsModule"]["conditions"] = ["EGFR T790M Mutation"]
    for mapping in (CLASSES, None):
        found = assign(body, mapping)
        assert (found.case, found.decided_by) == ("oncology", "free_text"), mapping
        assert source(found, "free_text")["status"] == "conditions_and_titles"
        assert source(found, "free_text")["non_oncology"] == []
        assert found.words.startswith("Solid-tumour oncology (title: AZD9291 Versus Gefitinib")
    body["protocolSection"]["identificationModule"].update(briefTitle="Study A", officialTitle="Study A")
    assert assign(body, None).code == "unresolved_no_domain"


def test_an_unmapped_condition_is_scope_unresolved_never_general():
    """The external review's case, exactly: no MeSH, no vocabulary term, nothing in the titles."""
    for mapping in ({}, None):
        found = assign(study(conditions=["Unmapped condition ZYX-123"], titles=("Study A", "")), mapping)
        assert (found.case, found.code, found.universes, found.packs) == (
            "unresolved",
            "unresolved_no_domain",
            (),
            (),
        )
        assert source(found, "free_text")["non_oncology"] == []
        assert "no condition names a term of the declared vocabularies (Unmapped condition ZYX-123)" in (
            found.words
        )
        assert reading(found)["status"] == "unresolved"


def test_a_declared_non_oncology_term_is_general_unless_a_title_names_a_cancer():
    assert assign(study(conditions=["Major Depressive Disorder"]), {}).case == "general"
    titled = study(conditions=["Major Depressive Disorder"], titles=("Sertraline in Breast Cancer", ""))
    assert assign(titled, {}).case == "oncology"


def test_a_condition_beside_one_that_names_a_cancer_is_never_listed_outside_oncology():
    """NCT05261399's conditions, as the 49-trial baseline holds them."""
    found = assign(study(["Carcinoma", "Non-Small-Cell Lung"]), {})
    text = source(found, "free_text")
    assert [f["term"] for f in text["found"]] == ["Carcinoma"]
    assert text["non_oncology"] == []


def test_a_supportive_care_trial_in_cancer_patients_gets_no_setting():
    """Positive: solid oncology from its condition MeSH, gene selection permitted. Negative: no setting or
    line (the pack needs a treatment purpose), and its antiemetic is never read for a class."""
    nausea = study(
        conditions=["Breast Cancer", "Chemotherapy-induced Nausea"],
        mesh=["Breast Neoplasms", "Nausea"],
        ancestors=["Neoplasms by Site", "Neoplasms", "Signs and Symptoms, Digestive"],
        purpose="SUPPORTIVE_CARE",
        interventions=[("Ondansetron",)],
    )
    found = assign(nausea, {"Ondansetron": ("A04AA",)})
    assert found.universes == ("oncology.solid",)
    assert found.packs == ("oncology.solid/gene_selection",)
    assert source(found, "drug_class")["status"] == "does_not_apply"
    coordinates = coherence.resolve([], found)
    assert "setting" not in coordinates and "prior_advanced_lines" not in coordinates
    assert set(coordinates) == {f"selection:{gene}" for gene in contract.SELECTED_GENES}


def test_methotrexate_in_rheumatoid_arthritis_is_unresolved_never_oncology():
    arthritis = study(
        conditions=["Rheumatoid Arthritis"],
        mesh=["Arthritis, Rheumatoid"],
        ancestors=["Arthritis", "Joint Diseases"],
        interventions=[("Methotrexate",)],
    )
    found = assign(arthritis, {"Methotrexate": ("L01BA", "L04AX")})
    assert (found.case, found.code, found.universes, found.packs) == (
        "unresolved",
        "unresolved_disagreement",
        (),
        (),
    )
    assert found.words == (
        "Scope unresolved — the sources disagree: the conditions are outside oncology (condition MeSH: "
        "Arthritis, Rheumatoid; conditions: Rheumatoid Arthritis), but drug class: Methotrexate, "
        "antineoplastic agents (ATC L01) signals cancer"
    )
    assert coherence.resolve([], found) == {}


def test_a_lymphomas_antineoplastic_drug_counts_as_haematologic():
    lymphoma = study(conditions=["Overall Survival"], titles=("Rituximab in Follicular Lymphoma", ""))
    lymphoma["protocolSection"]["armsInterventionsModule"]["interventions"] = [
        {"type": "DRUG", "name": "Rituximab"}
    ]
    found = assign(lymphoma, {"Rituximab": ("L01FA",)})
    assert found.universes == ("oncology.heme",)
    assert source(found, "drug_class")["found"] == [
        {"term": "Rituximab", "anchor": "L01", "universe": "oncology.heme"}
    ]


def test_solid_and_haematologic_conditions_give_the_union():
    basket = study(conditions=["Melanoma", "Hodgkin Lymphoma"])
    found = assign(basket, {})
    assert found.universes == ("oncology.solid", "oncology.heme")
    assert (
        found.words
        == "Solid-tumour oncology and haematologic oncology (conditions: Melanoma; Hodgkin Lymphoma)"
    )
    rows = coherence.resolve([], found)
    assert rows["prior_advanced_lines"]["packs"] == [
        "oncology.solid/setting_and_line",
        "oncology.heme/prior_lines",
    ]


def test_a_study_with_no_record_parts_is_unresolved():
    found = assign({}, None)
    assert (found.case, found.primary_purpose, found.universes) == ("unresolved", "", ())
    assert source(found, "drug_class")["status"] == "does_not_apply"
    assert source(found, "free_text")["status"] == "no_text"


# ── the decisions, both signs ──────────────────────────────────────────────────────────────────────────


def test_term_hits_in_the_texts_order_and_each_term_once():
    terms = list(contract.ONCOLOGY_TERMS)
    assert term_hits("Advanced Malignant Solid Neoplasm", terms) == ["malignan", "neoplasm"]
    assert term_hits("NSCLC", terms) == ["NSCLC"]
    assert term_hits("Non-Small-Cell Lung Carcinoma; carcinoma", terms) == ["carcinoma"]
    assert term_hits("Glioblastoma, leukemia and B-cell lymphoma", terms) == [
        "blastoma",
        "leukemia",
        "lymphoma",
    ]
    assert term_hits("lymphoma, then leukaemia", [("leukaemia", "within"), ("lymphoma", "within")]) == [
        "lymphoma",
        "leukaemia",
    ]


def test_term_hits_never_reads_part_of_a_word_or_a_disease_outside_the_vocabulary():
    terms = list(contract.ONCOLOGY_TERMS)
    assert term_hits("Anticancer Treatment", terms) == []  # "cancer" matches only a word's beginning
    assert term_hits("NSCLCs", [("NSCLC", "word")]) == []
    assert term_hits("Posttraumatic Stress Disorder", terms) == []
    assert term_hits("", terms) == []


def test_drug_anchor():
    assert drug_anchor(["L01EB"]) == "L01"
    assert drug_anchor(["A04AA", "L02BG"]) == "L02"
    assert drug_anchor(["L04AX", "L01BA"]) == "L01"
    assert drug_anchor(["L04AH"]) == ""
    assert drug_anchor([]) == ""


def test_counted_universe():
    assert counted_universe("Neoplasms", "oncology.solid", True) == "oncology.heme"
    assert counted_universe("L01", "oncology.solid", True) == "oncology.heme"
    assert counted_universe("Neoplasms", "oncology.solid", False) == "oncology.solid"
    assert counted_universe("carcinoma", "oncology.solid", True) == "oncology.solid"
    assert counted_universe("Lymphoma", "oncology.heme", False) == "oncology.heme"


@pytest.mark.parametrize(
    "condition, other, outside, code",
    [
        (True, False, False, "oncology"),
        (True, True, True, "oncology"),
        (False, True, False, "oncology"),
        (False, True, True, "unresolved_disagreement"),
        (False, False, True, "general"),
        (False, False, False, "unresolved_no_domain"),
    ],
)
def test_scope_case(condition, other, outside, code):
    assert scope_case(condition, other, outside) == code
    assert code in universes.CASE_CODES


def test_permitted_packs_need_every_requirement():
    assert permitted_packs(["oncology.solid"], "TREATMENT") == [
        "oncology.solid/setting_and_line",
        "oncology.solid/gene_selection",
        "oncology.solid/nsclc_relations",
    ]
    assert permitted_packs(["oncology.heme"], "TREATMENT") == ["oncology.heme/prior_lines"]
    assert permitted_packs(["oncology.heme"], "SUPPORTIVE_CARE") == []
    assert permitted_packs(["oncology.solid"], "") == ["oncology.solid/gene_selection"]
    assert permitted_packs(["general"], "TREATMENT") == []
    assert permitted_packs([], "TREATMENT") == []


def test_atc_classes_keeps_answered_names_and_marks_failed_ones():
    answers = {
        "Osimertinib": {"axes": {"ATC": {"code": "found", "assertions": [["L01EB", "EGFR TKIs"]]}}},
        "Placebo": {"axes": {"ATC": {"code": "not_found", "assertions": []}}},
        "Cisplatin injection": {"classes": [], "codes": {}},
        "Pemetrexed": {"axes": {"ATC": {"code": "lookup_failed", "assertions": []}}},
    }
    assert atc_classes(answers) == {"Osimertinib": ("L01EB",), "Placebo": (), "Pemetrexed": None}


def test_a_failed_drug_lookup_is_never_read_as_no_cancer_drug():
    from TrialLedger.universes import _drug_findings

    failed = {"Pemetrexed": None, "Placebo": ()}
    assert _drug_findings([["Pemetrexed"], ["Placebo"]], failed, "TREATMENT") == ("lookup_failed", [])
    answered = {"Pemetrexed": None, "Osimertinib": ("L01EB",)}
    status, found = _drug_findings([["Pemetrexed"], ["Osimertinib"]], answered, "TREATMENT")
    assert status == "read" and [f["term"] for f in found] == ["Osimertinib"]
    assert _drug_findings([["Placebo"]], {"Placebo": ()}, "TREATMENT") == ("read", [])


# ── resolve under a universe (2.2) ─────────────────────────────────────────────────────────────────────


FIRST_LINE = [
    ("inclusion", "stage", ("IV",), "", "criterion 0"),
    ("inclusion", "prior_lines", ("0",), "advanced", "criterion 1"),
]


def scoped(universes_, purpose="TREATMENT"):
    packs = tuple(permitted_packs(list(universes_), purpose))
    return Assignment("oncology", "oncology", tuple(universes_), "", purpose, (), packs, "")


def test_without_an_assignment_resolve_is_unchanged():
    rows = coherence.resolve(FIRST_LINE)
    assert set(rows) == set(coherence.COORDINATES)
    assert all("packs" not in row for row in rows.values())
    assert rows["setting"]["interpolated"]["domain"] == ("advanced_first_line",)


def test_a_solid_treatment_trial_gets_every_coordinate_tagged_with_its_pack():
    plain = coherence.resolve(FIRST_LINE)
    rows = coherence.resolve(FIRST_LINE, scoped(["oncology.solid"]))
    assert {name: {k: v for k, v in row.items() if k != "packs"} for name, row in rows.items()} == plain
    assert rows["setting"]["packs"] == [SETTING_PACK]
    assert rows["selection:EGFR"]["packs"] == ["oncology.solid/gene_selection"]


def test_a_haematologic_trial_gets_prior_lines_and_no_relation():
    """Negative: no setting, no gene selection, and the NSCLC relations never narrow anything."""
    rows = coherence.resolve(FIRST_LINE, scoped(["oncology.heme"]))
    assert list(rows) == ["prior_advanced_lines"]
    assert rows["prior_advanced_lines"]["domain"] == ("0",)
    assert rows["prior_advanced_lines"]["packs"] == ["oncology.heme/prior_lines"]


def test_membership_alone_permits_nothing():
    assert coherence.resolve(FIRST_LINE, scoped(["oncology.heme"], "PREVENTION")) == {}
    assert coherence.resolve(FIRST_LINE, scoped(["general"])) == {}


# ── the loader's universes key (2.3) ───────────────────────────────────────────────────────────────────


def fragment(**extra):
    return {
        "name": "pack",
        "version": "1",
        "exposure": loader.load_fragments()[0].exposure,
        "requires": [],
        "concepts": [],
        "references": [],
        **extra,
    }


def test_a_fragment_may_declare_its_universes():
    assert loader.fragment_from_data(fragment(universes=["oncology.solid"])).universes == ("oncology.solid",)
    assert loader.fragment_from_data(fragment()).universes == ()


def test_the_seed_registry_keeps_its_version():
    assert loader.compile_registry(loader.load_fragments()).version == (
        "762b1e54e93881263a21290231c44f28b6e37a018a1d32a5552e9240f7aad6d1"
    )


def test_declared_universes_enter_the_version_and_an_unknown_one_is_refused():
    seed = loader.load_fragments()
    declared = [loader.fragment_from_data(fragment(universes=["oncology.solid"])), *seed]
    plain = [loader.fragment_from_data(fragment()), *seed]
    assert loader.compile_registry(declared).version != loader.compile_registry(plain).version
    unknown = [loader.fragment_from_data(fragment(universes=["oncology.lung"])), *seed]
    with pytest.raises(loader.RegistryError) as refused:
        loader.compile_registry(unknown)
    assert refused.value.problems == (("unknown_universe", "pack", "oncology.lung"),)
    assert loader.universe_problems(declared, ["oncology.solid"]) == ()


def test_unknown_universes_are_named_in_fragment_and_declaration_order():
    first = loader.fragment_from_data(fragment(universes=["lung", "oncology.solid", "breast"]))
    second = loader.fragment_from_data({**fragment(universes=["skin"]), "name": "second"})
    assert loader.universe_problems([first, second], ["oncology.solid"]) == (
        ("unknown_universe", "pack", "lung"),
        ("unknown_universe", "pack", "breast"),
        ("unknown_universe", "second", "skin"),
    )


# ── acceptance: the 49 osimertinib trials (2.4; design §3) ─────────────────────────────────────────────


@pytest.mark.skipif(not BASELINE.is_dir(), reason="the baseline run folder is not on this machine")
def test_every_osimertinib_trial_is_in_an_oncology_universe(tmp_path):
    studies = json.loads((BASELINE / "bodies" / "studies-001.json").read_text(encoding="utf-8"))["studies"]
    classes = atc_classes(json.loads((BASELINE / "classes.json").read_text(encoding="utf-8"))["answers"])
    assert len(studies) == 49
    found = {s["protocolSection"]["identificationModule"]["nctId"]: assign(s, classes) for s in studies}
    (tmp_path / "assignments.json").write_text(
        json.dumps({nct: reading(a) for nct, a in found.items()}, indent=1), encoding="utf-8"
    )
    exceptions = {nct: a.words for nct, a in found.items() if a.case != "oncology"}
    assert exceptions == {}
    assert all(set(a.universes) <= {"oncology.solid", "oncology.heme"} for a in found.values())
