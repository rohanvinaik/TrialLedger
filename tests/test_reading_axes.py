"""reading — the drug-class axes in a study's view and across the population (Decision 11).

Positive: a study view carries each experimental drug's identity (decided by its own name), ATC and structure
classes with their standing and warrants, its own entry's targets and their crosswalk alignment, every
modality and cell extraction of every intervention entry with its warrant, and the trial's intervention MeSH,
linked only by a literal name; a genetic intervention of an experimental arm is read as a drug; two trials
whose drugs' ATC classes align and differ in one predicate are an aligned pair labelled with each basis; two
distinct drugs with a known shared structure class are related by shares_structure_class, keyed by rxcui; the
resolve JSON and design.xlsx's Drug Axes sheet render all of it with its requests; axes every name of which
was looked up are read as drug_axes gives them (axes_as_looked_up); a name whose answer holds axes is not
missing (axes_not_looked_up); changing a rule that decides the Drug Axes rows (axes_not_looked_up,
axes_as_looked_up) changes the sheet's warrant.
Negative: a drug whose axes were not looked up (own name or alias) is not_looked_up, with no identity, no
known class and no aligned ATC, never "no class"; a name with no answer, no axes entry or an empty one is
missing; a docstring-only change to those rules leaves the warrant, and the Trials sheet's warrant, as they
are; the drug tuples the outputs read are unchanged; an aligned
pair is never a pair as written (the
existing pairs are untouched); a brand's ingredient class, given by its other name, aligns nothing; a drug
whose target only overlaps an ATC class leaves the aligned representation unknown; another drug's name in the
entry ("XB-1 given after carboplatin and paclitaxel") gives no ATC membership; an arm's wording and the
eligibility text give no modality.
"""

import json
from typing import Any

from records import ongoing_study
from test_drug_axes import ANSWERS, NOT_ASKED, axes_answer

from TrialLedger.classes import drug_axes
from TrialLedger.design import sheets
from TrialLedger.reading import (
    aligned_near_miss_input,
    axes_aliases,
    axes_as_looked_up,
    axes_not_looked_up,
    drug_aliases,
    near_miss_input,
    read_population,
    structure_relations,
    study_view,
)
from TrialLedger.symbolic import symbolic_output

PLATINUM = [
    (
        "N0000175073",
        "Platinum-containing Compounds",
        "CHEM",
        "has_chemical_structure",
        "FDASPL",
        rxcui,
        name,
        "IN",
    )
    for rxcui, name in (("2555", "cisplatin"),)
]


def study(nct, interventions, arm, criteria="Inclusion Criteria:\n\n* No prior CAR-T therapy\n", meshes=()):
    record = ongoing_study()
    protocol = record["protocolSection"]
    protocol["identificationModule"]["nctId"] = nct
    protocol["eligibilityModule"]["eligibilityCriteria"] = criteria
    protocol["armsInterventionsModule"] = {
        "armGroups": [
            {
                "label": "A",
                "type": "EXPERIMENTAL",
                "description": "an autologous cell therapy arm",
                "interventionNames": arm,
            }
        ],
        "interventions": interventions,
    }
    record["derivedSection"] = {"interventionBrowseModule": {"meshes": list(meshes)}}
    return record


def answers():
    held = json.loads(json.dumps(ANSWERS))
    held["Cisplatin"] = axes_answer(
        ("found", ["2555"]), ("found", [("2555", "cisplatin", "IN")]), NOT_ASKED, structure=PLATINUM
    )
    carboplatin = [(*row[:5], "40048", "carboplatin", "IN") for row in PLATINUM]
    held["Carboplatin"] = axes_answer(
        ("found", ["40048"]), ("found", [("40048", "carboplatin", "IN")]), NOT_ASKED, structure=carboplatin
    )
    return held


def test_a_view_carries_each_drugs_axes_and_each_entrys_extractions():
    interventions = [
        {"type": "BIOLOGICAL", "name": "Keytruda", "otherNames": ["pembrolizumab"]},
        {"type": "GENETIC", "name": "XB-2", "description": "Autologous CAR-T cells"},
        {"type": "DRUG", "name": "Testamab"},
    ]
    record = study(
        "NCT1",
        interventions,
        ["Biological: Keytruda", "Genetic: XB-2"],
        meshes=[{"id": "D1", "term": "Testamab"}, {"id": "D2", "term": "Pembrolizumab"}],
    )
    view = study_view(record, answers())
    assert [d[0] for d in view["drugs"]] == ["Keytruda", "XB-2"]
    assert all(len(d) == 4 for d in view["drugs"])
    keytruda, xb2 = view["drug_axes"]
    assert (keytruda["identity"], keytruda["reason"]) == ("resolved", "own_name")
    # the brand is the own name: the class RxClass gave by its other name is pembrolizumab's, not inherited
    assert [(a[0], a[5]) for a in keytruda["assertions"]] == [
        ("Keytruda", "not_inherited"),
        ("pembrolizumab", "not_inherited"),
    ]
    assert keytruda["atc"] == ("", [])
    # XB-2's axes were never asked of RxNav: not looked up, never an identity or "no class"
    assert (xb2["identity"], xb2["reason"]) == ("not_looked_up", "own_name_not_looked_up")
    assert xb2["atc"] == ("", []) and xb2["assertions"] == []
    extracted = {(e[0], e[1], e[2], e[7]) for e in view["properties"]}
    assert extracted == {
        ("XB-2", "modality", "cell", "known"),
        ("XB-2", "lineage", "T cell", "known"),
        ("XB-2", "engineering", "chimeric antigen receptor", "known"),
        ("XB-2", "donor relationship", "autologous", "known"),
        ("Testamab", "modality", "antibody", "interpolated"),
        ("Keytruda", "modality", "antibody", "interpolated"),  # its other name, pembrolizumab, ends in -mab
    }
    assert all(
        e[5].startswith("protocolSection.armsInterventionsModule.interventions[") for e in view["properties"]
    )
    assert all(len(e[8]) == 64 for e in view["properties"])
    assert view["intervention_mesh"] == [
        ("D1", "Testamab", "intervention", "Testamab"),
        ("D2", "Pembrolizumab", "intervention", "Keytruda"),
    ]


def test_a_brand_alone_aligns_nothing_and_an_overlapping_target_stays_unknown():
    brand = study("NCT2", [{"type": "DRUG", "name": "Keytruda"}], ["Drug: Keytruda"])
    assert study_view(brand, answers())["drug_axes"][0]["atc"] == ("", [])
    stated = study(
        "NCT3", [{"type": "DRUG", "name": "XB-1", "description": "an anti-PD-1 antibody"}], ["Drug: XB-1"]
    )
    view = study_view(stated, answers())
    assert view["drugs"][0][1] == "stated_by_record"
    assert view["drug_axes"][0]["targets"] == ["PD-1"]
    assert view["drug_axes"][0]["alignment"][0][3:5] == ("overlaps", False)
    aligned = aligned_near_miss_input(view, near_miss_input(view))
    assert aligned[0][1]["atc"] == "" and aligned[1] == ""


def test_another_drugs_name_in_the_entry_gives_no_atc_membership():
    entry = {"type": "DRUG", "name": "XB-1", "description": "XB-1 given after carboplatin and paclitaxel"}
    view = study_view(study("NCT4", [entry], ["Drug: XB-1"]), answers())
    axes = view["drug_axes"][0]
    assert axes["targets"] == [] and axes["alignment"] == [] and axes["atc"] == ("", [])
    own = {"type": "DRUG", "name": "XB-1", "description": "XB-1 is an EGFR inhibitor"}
    assert study_view(study("NCT5", [own], ["Drug: XB-1"]), answers())["drug_axes"][0]["targets"] == [
        "EGFR inhibitor"
    ]


def first_line(nct, ecog, name, description=""):
    criteria = (
        "Inclusion Criteria:\n\n* Stage IV non-small cell lung cancer\n"
        "* No prior systemic therapy for advanced or metastatic disease\n"
        f"* ECOG performance status {ecog}\n\nExclusion Criteria:\n\n* Active autoimmune disease\n"
    )
    entry = {"type": "DRUG", "name": name, "description": description}
    return study(nct, [entry], [f"Drug: {name}"], criteria=criteria)


def platinum_answers():
    held = answers()
    # AB-1 is cisplatin and AB-2 carboplatin to RxNorm and RxClass, and neither entry names an agent word, so
    # neither record states a class: no pair as written can hold them
    for name, base, rxcui, subject in (
        ("AB-1", "Cisplatin", "2555", "cisplatin"),
        ("AB-2", "Carboplatin", "40048", "carboplatin"),
    ):
        held[name] = json.loads(json.dumps(held[base]))
        held[name]["axes"]["ATC"]["assertions"] = [
            ("L01XA", "Platinum compounds", "ATC1-4", "", "ATC", rxcui, subject, "IN")
        ]
    held["ZZ-9"] = axes_answer(("not_found", []), NOT_ASKED, NOT_ASKED)
    return held


def test_an_aligned_pair_is_labelled_with_its_basis_and_leaves_the_pairs_as_written():
    studies = [first_line("NCT11", "0-1", "AB-1"), first_line("NCT12", "0-2", "AB-2")]
    reading = read_population(studies, platinum_answers())
    assert reading["pairs"] == []
    assert reading["aligned_pairs"] == [
        ("NCT11", "NCT12", "ecog_ps", "0|1", "0|1|2", "", "", "2025", "2025", 0, "rxclass", "rxclass")
    ]
    inputs = zip(reading["views"], reading["near_miss_trials"], strict=True)
    assert [aligned_near_miss_input(v, t)[0][1]["atc"] for v, t in inputs] == ["L01XA", "L01XA"]


def test_a_platinum_word_in_an_entry_aligns_nothing():
    studies = [
        first_line("NCT13", "0-1", "AB-1"),
        first_line("NCT14", "0-2", "ZZ-9", "ZZ-9, a platinum agent"),
    ]
    reading = read_population(studies, platinum_answers())
    assert reading["aligned_pairs"] == []
    assert reading["views"][1]["drug_axes"][0]["atc"] == ("", [])


def test_distinct_drugs_sharing_a_structure_class_are_related_and_a_drug_is_not_its_own_relative():
    studies = [first_line("NCT21", "0-1", "Cisplatin"), first_line("NCT22", "0-1", "Carboplatin")]
    views = read_population(studies, answers())["views"]
    assert structure_relations(views) == [
        (
            "2555",
            "cisplatin",
            "40048",
            "carboplatin",
            "FDASPL:has_chemical_structure",
            "N0000175073 Platinum-containing Compounds",
            "05-Oct-2026",
        )
    ]
    same = read_population([studies[0], first_line("NCT23", "0-2", "Cisplatin")], answers())
    assert same["structure_relations"] == []


def test_the_json_and_the_workbook_render_the_axes_with_their_requests():
    studies = [first_line("NCT31", "0-1", "AB-1"), first_line("NCT32", "0-2", "AB-2")]
    studies[0]["protocolSection"]["armsInterventionsModule"]["interventions"][0]["description"] = (
        "AB-1, an autologous CAR-T cell therapy"
    )
    studies[0]["derivedSection"] = {"interventionBrowseModule": {"meshes": [{"id": "D1", "term": "AB-1"}]}}
    reading = read_population(studies, platinum_answers())
    first, second = symbolic_output(reading)
    [axes] = first["drug_axes"]
    assert (axes["identity"], axes["reason"], axes["atc"]) == (
        "resolved",
        "own_name",
        {"basis": "rxclass", "classes": ["L01XA"]},
    )
    atc = next(c for c in axes["classes"] if c["axis"] == "ATC")
    assert atc["standing"] == "known" and atc["release"] == "05-Oct-2026" and atc["retrieved"]
    assert atc["request"].endswith("byDrugName.json?drugName=X&relaSource=ATC")
    assert axes["names"][0]["requests"][0]["request"].endswith("rxcui.json?name=X&search=0")
    assert {(e["property"], e["value"], e["polarity"]) for e in first["extractions"]} >= {
        ("modality", "cell", "asserted")
    }
    assert all(len(e["warrant"]) == 64 for e in first["extractions"])
    assert first["intervention_mesh"] == [
        {"id": "D1", "term": "AB-1", "level": "intervention", "intervention": "AB-1"}
    ]
    assert (
        first["aligned_near_misses"][0]["other"] == "NCT32"
        and first["aligned_near_misses"][0]["basis"] == "rxclass"
    )
    assert first["near_misses"] == []
    assert [(r["a"]["rxcui"], r["b"]["rxcui"]) for r in first["structure_relations"]] == [("2555", "40048")]
    assert second["structure_relations"] == first["structure_relations"]
    header, rows = sheets(reading, {})["Drug Axes"]
    assert all(len(row) == len(header) for row in rows)
    kinds = {(row[0], row[4]) for row in rows}
    assert kinds == {(nct, kind) for nct in ("NCT31", "NCT32") for kind in ("name", "class", "aligned ATC")}
    request = next(row for row in rows if row[4] == "class" and "ATC" in row[6])
    assert request[9] == "05-Oct-2026" and "relaSource=ATC" in request[10] and request[11]


def test_a_study_with_no_known_structure_shows_no_relation():
    studies = [
        first_line("NCT33", "0-1", "ZZ-9"),
        first_line("NCT34", "0-1", "Cisplatin"),
        first_line("NCT35", "0-1", "Carboplatin"),
    ]
    first = symbolic_output(read_population(studies, platinum_answers()))[0]
    assert first["structure_relations"] == [] and first["drug_axes"][0]["classes"] == []


def test_only_an_experimental_drugs_names_are_asked_rxnav_for_axes():
    record = study(
        "NCT41",
        [
            {"type": "DRUG", "name": "XB-1", "otherNames": ["XB-1 + carboplatin"]},
            {"type": "DRUG", "name": "Placebo"},
        ],
        ["Drug: XB-1"],
    )
    record["protocolSection"]["armsInterventionsModule"]["armGroups"].append(
        {"label": "B", "type": "PLACEBO_COMPARATOR", "interventionNames": ["Drug: Placebo"]}
    )
    assert axes_aliases([record]) == ["XB-1", "XB-1 + carboplatin"]
    assert drug_aliases([record]) == ["XB-1", "XB-1 + carboplatin", "Placebo"]
    assert axes_aliases([study("NCT42", [{"type": "DRUG", "name": "Placebo"}], ["Drug: Placebo"])]) == [
        "Placebo"
    ]
    assert axes_aliases([study("NCT43", [{"type": "DRUG", "name": "Placebo"}], [])]) == []


def test_axes_looked_up_are_read_as_they_are():
    """Positive: every name looked up leaves drug_axes's answer as it is: pembrolizumab beside gefitinib is a
    conflict, pembrolizumab alone resolved with its class known."""
    for aliases in (["pembrolizumab", "gefitinib"], ["pembrolizumab"]):
        held = drug_axes(aliases, ANSWERS)
        assert axes_as_looked_up(aliases, [], held) == held
    assert drug_axes(["pembrolizumab", "gefitinib"], ANSWERS)[:2] == ("conflict", "alias_other_concept")
    assert {a[5] for a in drug_axes(["pembrolizumab"], ANSWERS)[3]} == {"known"}


def test_axes_not_looked_up_are_never_an_identity_or_a_known_class():
    """Negative: an own name not looked up attributes nothing, whatever an alias's cached answer says; an
    alias not looked up leaves no class known and no identity resolved, since the alias (gefitinib, another
    concept) would make it a conflict once asked."""
    assert axes_as_looked_up(
        ["never asked", "pembrolizumab"],
        ["never asked"],
        drug_axes(["never asked", "pembrolizumab"], ANSWERS),
    ) == ("not_looked_up", "own_name_not_looked_up", [], [])
    lazy = {name: answer for name, answer in ANSWERS.items() if name != "gefitinib"}
    lazy["gefitinib"] = {"codes": {}, "classes": []}
    code, reason, identities, assertions = axes_as_looked_up(
        ["pembrolizumab", "gefitinib"], ["gefitinib"], drug_axes(["pembrolizumab", "gefitinib"], lazy)
    )
    assert (code, reason) == ("not_looked_up", "alias_not_looked_up")
    assert [i[0] for i in identities] == ["pembrolizumab"]
    assert assertions and {a[5] for a in assertions} == {"alias_not_looked_up"}


def test_a_view_of_a_drug_not_looked_up_aligns_nothing():
    """Negative: a drug whose axes were not looked up has no aligned ATC classes, even where its own entry
    states a target, and no structure relation; positive: once looked up, the same drug reads its class."""
    entry = {"type": "DRUG", "name": "AB-1", "description": "AB-1 is an anti-PD-1 antibody"}
    record = study("NCT44", [entry], ["Drug: AB-1"])
    unasked = {name: answer for name, answer in platinum_answers().items() if name != "AB-1"}
    axes = study_view(record, unasked)["drug_axes"][0]
    assert (axes["identity"], axes["atc"], axes["targets"]) == ("not_looked_up", ("", []), ["PD-1"])
    assert study_view(record, platinum_answers())["drug_axes"][0]["atc"] == ("rxclass", ["L01XA"])


def test_a_name_whose_answer_holds_axes_is_looked_up():
    """Positive: names whose cached answers hold axes are not missing."""
    assert axes_not_looked_up(["pembrolizumab", "gefitinib"], ANSWERS) == []


def test_a_name_with_no_axes_is_not_looked_up():
    """Negative: a name with no answer, an answer with no axes entry or with empty axes is missing, in
    order."""
    held = {"a": {"codes": {}, "classes": []}, "b": {"axes": {}}, "pembrolizumab": ANSWERS["pembrolizumab"]}
    assert axes_not_looked_up(["never asked", "a", "pembrolizumab", "b"], held) == ["never asked", "a", "b"]


def _rules():
    """Stand-ins with the rules' own names and signatures: two whose bodies differ from the rules', and one
    that differs from axes_not_looked_up only in its docstring and a comment."""

    def axes_not_looked_up(aliases: list[str], answers: dict[str, Any]) -> list[str]:
        return [alias for alias in aliases if "axes" not in (answers.get(alias) or {})]

    changed_not = axes_not_looked_up

    def axes_as_looked_up(aliases: list[str], missing: list[str], axes: tuple) -> tuple[str, str, list, list]:
        return axes if not missing else ("not_looked_up", "own_name_not_looked_up", [], [])

    changed_as = axes_as_looked_up

    def axes_not_looked_up(aliases: list[str], answers: dict[str, Any]) -> list[str]:  # noqa: F811
        """Reworded: the names whose answers hold no axes."""
        return [alias for alias in aliases if not (answers.get(alias) or {}).get("axes")]  # a comment

    return changed_not, changed_as, axes_not_looked_up


def _warrants(reading, name):
    return [row[-1] for row in sheets(reading, {})[name][1]]


def test_changing_a_not_looked_up_rule_changes_the_drug_axes_warrant(monkeypatch):
    """Positive: replacing axes_not_looked_up or axes_as_looked_up by a different rule changes every Drug Axes
    warrant, so the warrant commits to the rules that decide its rows."""
    reading = read_population([first_line("NCT31", "0-1", "AB-1")], platinum_answers())
    before = _warrants(reading, "Drug Axes")
    assert before
    changed_not, changed_as, _reworded = _rules()
    for name, changed in (("axes_not_looked_up", changed_not), ("axes_as_looked_up", changed_as)):
        with monkeypatch.context() as patch:
            patch.setattr(f"TrialLedger.design.{name}", changed)
            after = _warrants(reading, "Drug Axes")
        assert len(after) == len(before) and not set(after) & set(before)
    assert _warrants(reading, "Drug Axes") == before


def test_a_reworded_rule_or_another_sheet_leaves_the_warrant(monkeypatch):
    """Negative: a docstring or comment change to axes_not_looked_up leaves the Drug Axes warrant; changing it
    leaves the Trials sheet's warrant."""
    reading = read_population([first_line("NCT31", "0-1", "AB-1")], platinum_answers())
    axes, trials = _warrants(reading, "Drug Axes"), _warrants(reading, "Trials")
    changed_not, _changed_as, reworded = _rules()
    monkeypatch.setattr("TrialLedger.design.axes_not_looked_up", reworded)
    assert _warrants(reading, "Drug Axes") == axes
    monkeypatch.setattr("TrialLedger.design.axes_not_looked_up", changed_not)
    assert _warrants(reading, "Trials") == trials
