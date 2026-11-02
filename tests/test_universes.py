"""Indication-backed compatibility: no categories, no drug/purpose gate, no forced unknown scope.

Supersedes lexical/category expectations from the removed assignment design. Independent loader, ATC
answer-shape, and unscoped coherence obligations remain covered below.
"""

import json
from pathlib import Path

import pytest

from TrialLedger import coherence
from TrialLedger.indications import LookupResult, MeshIdentity
from TrialLedger.semantics import loader
from TrialLedger.universes import NSCLC_PACKS, assign, pack_scope, reading

NSCLC = MeshIdentity("D002289", "Carcinoma, Non-Small-Cell Lung", ("C04.100.200",), "2026")
LUNG = MeshIdentity("D008175", "Lung Neoplasms", ("C04.100",), "2026")
ALZHEIMER = MeshIdentity("D000544", "Alzheimer Disease", ("C10.228",), "2026")
LYMPHOMA = MeshIdentity("D008224", "Lymphoma", ("C04.588.100",), "2026")
LOOKUPS = {item.label: LookupResult("resolved", (item,)) for item in (NSCLC, LUNG, ALZHEIMER, LYMPHOMA)}
FIRST_LINE = [
    ("inclusion", "stage", ("IV",), "", "criterion 0"),
    ("inclusion", "prior_lines", ("0",), "advanced", "criterion 1"),
]


def study(conditions=(), mesh=(), purpose="TREATMENT", titles=(), interventions=()):
    return {
        "protocolSection": {
            "conditionsModule": {"conditions": list(conditions), "keywords": ["exact keyword"]},
            "designModule": {"designInfo": {"primaryPurpose": purpose}},
            "identificationModule": {"briefTitle": titles[0] if titles else ""},
            "armsInterventionsModule": {"interventions": list(interventions)},
        },
        "derivedSection": {
            "conditionBrowseModule": {
                "meshes": [{"term": name} for name in mesh],
                "ancestors": [{"term": "Neoplasms"}],
                "browseLeaves": [{"id": "leaf", "name": "name", "asFound": "words", "relevance": "high"}],
            }
        },
    }


def test_declared_indication_authorizes_existing_packs_without_assigning_category():
    result = assign(study([NSCLC.label]), lookups=LOOKUPS)
    assert result.code == "applicable"
    assert result.case == "resolved"
    assert result.universes == ()
    assert result.target is None
    assert result.packs == NSCLC_PACKS
    assert result.indications[0]["descriptor"] == NSCLC.descriptor
    assert all(row["status"] == "applicable" for row in result.applicability)
    assert all(
        row["scope"] == "indication; not a trial-wide cohort assertion" for row in result.applicability
    )


@pytest.mark.parametrize("purpose", ["", "PREVENTION", "SUPPORTIVE_CARE", "BASIC_SCIENCE"])
def test_primary_purpose_and_drug_class_cannot_gate_established_indication(purpose):
    for drug_classes in (None, {}, {"Placebo": ()}, {"Sertraline": ("N06AB",)}, {"Cisplatin": None}):
        result = assign(study([NSCLC.label], purpose=purpose), drug_classes, lookups=LOOKUPS)
        assert result.packs == NSCLC_PACKS
        assert result.primary_purpose == purpose
        assert result.target is None


def test_no_lookup_never_guesses_from_title_drug_class_or_derived_mesh():
    result = assign(
        study(["Unknown"], mesh=[NSCLC.label], titles=(NSCLC.label,)), {"Osimertinib": ("L01EB",)}
    )
    assert result.code == "scope_unresolved"
    assert result.packs == result.universes == ()
    assert reading(result)["status"] == "unresolved"


def test_unrelated_extra_mesh_remains_discrepancy_and_cannot_authorize_pack():
    result = assign(study([ALZHEIMER.label], mesh=[NSCLC.label]), lookups=LOOKUPS)
    assert result.code == "inapplicable"
    assert result.packs == ()
    assert result.indications[0]["descriptor"] == ALZHEIMER.descriptor
    assert result.relationships == (
        {
            "established": ALZHEIMER.descriptor,
            "registry": NSCLC.descriptor,
            "relation": "unexplained_discrepancy",
        },
    )


def test_compatible_broader_mesh_is_never_conflict_but_broader_condition_is_unresolved():
    exact = assign(study([NSCLC.label], mesh=[LUNG.label]), lookups=LOOKUPS)
    assert exact.code == "applicable"
    assert exact.relationships[0]["relation"] == "compatible_narrower"
    broad = assign(study([LUNG.label]), lookups=LOOKUPS)
    assert broad.code == "scope_unresolved"
    assert broad.packs == ()


def test_mixed_diseases_authorize_only_bounded_indication_scope():
    result = assign(study([NSCLC.label, LYMPHOMA.label]), lookups=LOOKUPS)
    assert result.packs == NSCLC_PACKS
    assert result.universes == ()
    assert len(result.indications) == 2
    assert "cohort and temporal scope remain separate" in result.words
    assert all("oncology.heme" not in pack for pack in result.packs)


def test_record_keeps_conditions_keywords_mesh_leaves_and_legacy_field_explicit():
    result = assign(study([NSCLC.label], mesh=[LUNG.label]), lookups=LOOKUPS)
    output = reading(result)
    assert output["rule"] == "universes.assign"
    assert output["words"] == [NSCLC.label]
    assert output["result"]["legacy"] is True
    assert output["result"]["universes"] == []
    assert output["result"]["indications"] == list(result.indications)
    assert output["result"]["relationships"] == list(result.relationships)
    sources = {row["source"]: row for row in result.sources if "source" in row}
    assert sources["registry_conditions"]["keywords"] == ["exact keyword"]
    assert sources["registry_mesh"]["browse_leaves"] == [
        {"id": "leaf", "name": "name", "asFound": "words", "relevance": "high"}
    ]
    assert sources["eligibility_disease_assertions"]["code"] == "not_yet_read"
    json.dumps(output)


def test_whole_resolved_title_is_read_but_title_fragment_is_not_guessed():
    lookups = {**LOOKUPS, "Progression Free Survival": LookupResult("not_found")}
    exact = assign(study(["Progression Free Survival"], titles=(NSCLC.label,)), lookups=lookups)
    assert exact.decided_by == "own_assertions"
    assert exact.packs == NSCLC_PACKS
    fragment = assign(
        study(["Progression Free Survival"], titles=("Study of " + NSCLC.label,)), lookups=lookups
    )
    assert fragment.code == "scope_unresolved"


def test_empty_and_malformed_module_shapes_are_unresolved():
    assert assign({}).code == "scope_unresolved"
    assert assign({"protocolSection": None, "derivedSection": []}).packs == ()


def test_coherence_consumes_permitted_packs_not_legacy_categories():
    scoped = assign(study([NSCLC.label]), lookups=LOOKUPS)
    plain = coherence.resolve(FIRST_LINE)
    rows = coherence.resolve(FIRST_LINE, scoped)
    assert {
        name: {key: value for key, value in row.items() if key != "packs"} for name, row in rows.items()
    } == plain
    assert rows["setting"]["packs"] == ["oncology.solid/setting_and_line"]
    assert rows["selection:EGFR"]["packs"] == ["oncology.solid/gene_selection"]
    assert coherence.resolve(FIRST_LINE, assign(study([ALZHEIMER.label]), lookups=LOOKUPS)) == {}
    assert coherence.resolve(FIRST_LINE, assign(study(["Unknown"]))) == {}
    assert pack_scope(())[0] == {}


def test_saved_baseline_without_mesh_lookups_never_invents_categories():
    fixture = Path(__file__).parent / "fixtures" / "contract" / "studies-osimertinib-subset.json"
    for record in json.loads(fixture.read_text())["studies"]:
        result = assign(record, {"Osimertinib": ("L01EB",)})
        assert result.universes == ()
        assert result.packs == ()
        assert result.code == "scope_unresolved"


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


def test_without_an_assignment_resolve_is_unchanged():
    rows = coherence.resolve(FIRST_LINE)
    assert set(rows) == set(coherence.COORDINATES)
    assert all("packs" not in row for row in rows.values())
    assert rows["setting"]["interpolated"]["domain"] == ("advanced_first_line",)


@pytest.mark.parametrize("bad", [None, "NSCLC", [None], [NSCLC.label, 12]])
def test_malformed_condition_collection_never_authorizes_from_derived_mesh(bad):
    record = study(mesh=[NSCLC.label])
    record["protocolSection"]["conditionsModule"]["conditions"] = bad
    result = assign(record, lookups=LOOKUPS)
    assert result.code == "scope_unresolved"
    assert result.packs == ()
    assert (
        next(row for row in result.sources if row.get("source") == "registry_conditions")["conditions"] == bad
    )


def test_title_source_never_claims_a_read_without_supplied_lookup():
    record = study([NSCLC.label], titles=("An unlooked-up study title",))
    result = assign(record, lookups=LOOKUPS)
    title_source = next(row for row in result.sources if row.get("source") == "titles")
    assert title_source["code"] == "not_looked_up"
    assert title_source["identities"] == []
