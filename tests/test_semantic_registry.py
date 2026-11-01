"""The registry — one owner per concept, compiled from fragments, refusing what it cannot vouch for.

Positive: the seed fragment (the existing banks' concepts, development-exposed) compiles; every concept an
existing bank gives on the real criteria of tests/test_banks.py is a registry concept; its version is the
fragments' digest, the same whatever order they are given in; a JSON fragment and a Python fragment load
alike; a domain package that references a shared concept with its owner's signature compiles; a local concept
with its own definition date compiles; the seed's performance-status scale, whose source edition is not
pinned, is marked unversioned and flagged on the registry, never given a version.
Negative: two packages defining HbA1c (the spec's scenario) fail naming both owners, alike as a duplicate and
differently as an incompatible definition; a reference that disagrees with the owner, or names nothing, is
refused; an unknown family or argument, an invalid argument type, a concept or fragment without provenance, an
unknown authority or exposure, a code from a licence-required, words-only or unpinned authority, a local
concept without a definition or without a valid definition date of its own, an unversioned scale (a scale
marked unversioned in any package but the legacy fragment among them), an unresolved dependency or
requirement, a duplicate or unversioned fragment and a malformed fragment are each refused by name; a param a
concept does not declare is named (the conditions bank's "≥ 18 years" read as the window of `sex` is one, left
for task 2.1).
"""

import json
from dataclasses import replace

import pytest
from test_semantic_contracts import real_criteria

from TrialLedger import provenance
from TrialLedger.banks import BANKS
from TrialLedger.semantics.contracts import from_legacy, legacy_result
from TrialLedger.semantics.loader import (
    LEGACY_FRAGMENTS,
    UNVERSIONED,
    ConceptEntry,
    Fragment,
    Reference,
    RegistryError,
    atom_registry_problems,
    compile_registry,
    fragment_from_data,
    load_fragments,
    registry_flags,
    registry_problems,
)

AUTHORITIES = provenance.CONCEPT_AUTHORITIES
EXPOSURES = provenance.RULE_EXPOSURE
HBA1C = ConceptEntry(
    "lab.hba1c",
    "Measurement",
    (("comparator", "comparator"), ("value", "number"), ("unit", "ucum_unit")),
    "local",
    None,
    "glycated haemoglobin A1c, as a proportion or a molar ratio, the assay convention kept",
    None,
    (),
    "2026-11-01",
)


def fragment(name, concepts=(), references=(), requires=(), exposure="fragment:nsclc_legacy", version="1"):
    return Fragment(name, version, exposure, tuple(requires), tuple(concepts), tuple(references))


def codes(fragments):
    return [code for code, _subject, _detail in registry_problems(fragments, AUTHORITIES, EXPOSURES)]


def test_the_seed_compiles_and_owns_every_legacy_concept():
    registry = compile_registry(load_fragments())
    assert registry.fragments == (("nsclc_legacy", "nsclc-legacy 2026-10-31"),)
    assert set(registry.owners.values()) == {"nsclc_legacy"}
    problems = []
    for text in real_criteria():
        for bank, function in BANKS.items():
            for atom in legacy_result(bank, text, function(text)).atoms:
                problems += [(atom.concept_id, p, text) for p in atom_registry_problems(atom, registry)]
    # one known disagreement, kept for 2.1: the conditions bank reads "≥ 18 years" as a window of `sex`
    assert problems == [("nsclc.condition.sex", "unknown_argument", "1. Male or female ≥ 18 years.")]


def test_the_version_is_the_fragments_digest_in_any_order():
    other = fragment("measurements", [HBA1C])
    seed = load_fragments()
    first = compile_registry([*seed, other])
    second = compile_registry([other, *seed])
    assert first.version == second.version and len(first.version) == 64
    assert compile_registry(seed).version != first.version


def test_two_packages_defining_hba1c_fail_naming_both_owners():
    alike = registry_problems(
        [fragment("measurements", [HBA1C]), fragment("metabolic", [HBA1C])], AUTHORITIES, EXPOSURES
    )
    assert alike == (("duplicate_concept", "lab.hba1c", "owners: measurements, metabolic"),)
    differently = replace(HBA1C, family="State", arguments=())
    found = registry_problems(
        [fragment("measurements", [HBA1C]), fragment("metabolic", [differently])], AUTHORITIES, EXPOSURES
    )
    assert found == (("incompatible_definition", "lab.hba1c", "owners: measurements, metabolic"),)


def test_a_reference_must_agree_with_its_owner():
    agreeing = Reference("lab.hba1c", "Measurement", HBA1C.arguments)
    assert codes([fragment("measurements", [HBA1C]), fragment("metabolic", references=[agreeing])]) == []
    disagreeing = Reference("lab.hba1c", "Measurement", (("value", "number"),))
    found = registry_problems(
        [fragment("measurements", [HBA1C]), fragment("metabolic", references=[disagreeing])],
        AUTHORITIES,
        EXPOSURES,
    )
    assert found == (
        ("incompatible_definition", "lab.hba1c", "owner measurements, referenced differently by metabolic"),
    )
    assert codes([fragment("metabolic", references=[agreeing])]) == ["unresolved_dependency"]


@pytest.mark.parametrize(
    "change, code",
    [
        ({"family": "Feeling"}, "unknown_family"),
        ({"arguments": (("dose", "number"),)}, "unknown_argument"),
        ({"arguments": (("value", "float"),)}, "invalid_argument_type"),
        ({"authority": ""}, "missing_provenance"),
        ({"authority": "wikipedia"}, "unknown_authority"),
        ({"authority": "snomedct"}, "licence_not_held"),
        ({"authority": "ajcc", "code": "IIIA"}, "proprietary_code"),
        ({"authority": "loinc", "code": "4548-4"}, "unpinned_edition"),
        ({"definition": " "}, "missing_definition"),
        ({"defined_on": None}, "missing_definition_date"),
        ({"defined_on": "2026-11"}, "missing_definition_date"),
        ({"defined_on": "2026-02-30"}, "missing_definition_date"),
        ({"scale": ("NYHA functional class", UNVERSIONED)}, "unversioned_scale"),
        ({"arguments": (("scale_score", "scale_score"),)}, "unversioned_scale"),
        ({"scale": ("NYHA functional class", "")}, "unversioned_scale"),
        ({"depends_on": ("lab.glucose",)}, "unresolved_dependency"),
        ({"concept_id": "HbA1c"}, "invalid_concept_id"),
    ],
)
def test_each_refusal_is_named(change, code):
    assert codes([fragment("measurements", [replace(HBA1C, **change)])]) == [code]


def test_a_versioned_scale_and_a_resolved_dependency_compile():
    nyha = ConceptEntry(
        "scales.nyha",
        "Measurement",
        (("scale_score", "scale_score"),),
        "local",
        None,
        "NYHA functional class",
        ("NYHA functional classification", "Criteria Committee of the NYHA, 9th ed."),
        ("lab.hba1c",),
        "2026-11-01",
    )
    assert codes([fragment("measurements", [HBA1C, nyha])]) == []


def test_fragment_refusals():
    assert codes([fragment("a"), fragment("a")]) == ["duplicate_fragment"]
    assert codes([fragment("a", version=" ")]) == ["unversioned_fragment"]
    assert codes([fragment("a", exposure="")]) == ["missing_provenance"]
    assert codes([fragment("a", exposure="fragment:nowhere")]) == ["unknown_exposure"]
    assert codes([fragment("a", requires=["b"])]) == ["unresolved_requirement"]
    assert codes([fragment("a", requires=["b"]), fragment("b")]) == []


def test_compile_raises_every_problem():
    with pytest.raises(RegistryError) as raised:
        compile_registry([fragment("a", [HBA1C]), fragment("b", [HBA1C])])
    assert raised.value.problems == (("duplicate_concept", "lab.hba1c", "owners: a, b"),)


def data(**overrides):
    entry = {"concept_id": "lab.hba1c", "family": "Measurement", "arguments": [["value", "number"]]}
    entry["authority"] = "local"
    entry["definition"] = "HbA1c"
    entry["defined_on"] = "2026-11-01"
    base = {"name": "m", "version": "1", "exposure": "fragment:nsclc_legacy", "requires": []}
    return {**base, "concepts": [entry], "references": [], **overrides}


def test_fragment_data_is_parsed_exactly():
    parsed = fragment_from_data(data())
    assert parsed.concepts[0].arguments == (("value", "number"),)
    assert parsed.concepts[0].code is None and parsed.concepts[0].scale is None
    assert parsed.concepts[0].defined_on == "2026-11-01"
    undated = data(concepts=[{k: v for k, v in data()["concepts"][0].items() if k != "defined_on"}])
    assert fragment_from_data(undated).concepts[0].defined_on is None


@pytest.mark.parametrize(
    "broken",
    [
        {k: v for k, v in data().items() if k != "version"},
        data(owner="someone"),
        data(
            concepts=[{"concept_id": "x.y", "family": "State", "arguments": [], "authority": "local", "z": 1}]
        ),
        data(concepts=[{"concept_id": "x.y", "family": "State", "arguments": [["only-a-name"]]}]),
    ],
)
def test_a_malformed_fragment_is_refused(broken):
    with pytest.raises(RegistryError) as raised:
        fragment_from_data(broken)
    assert raised.value.problems[0][0] == "malformed_fragment"


def test_json_and_python_fragments_load_alike(tmp_path):
    (tmp_path / "a_measurements.json").write_text(json.dumps(data()), encoding="utf-8")
    (tmp_path / "b_metabolic.py").write_text(
        "FRAGMENT = " + repr(data(name="metabolic", concepts=[])), encoding="utf-8"
    )
    (tmp_path / "notes.txt").write_text("not a fragment", encoding="utf-8")
    loaded = load_fragments(tmp_path)
    assert [f.name for f in loaded] == ["m", "metabolic"]
    assert compile_registry(loaded).owners == {"lab.hba1c": "m"}
    (tmp_path / "c_empty.py").write_text("X = 1", encoding="utf-8")
    with pytest.raises(RegistryError):
        load_fragments(tmp_path)


def test_an_atom_of_no_concept_or_with_an_undeclared_param_is_named():
    registry = compile_registry(load_fragments())
    stranger = from_legacy("x", ("mystery", ("a",), (), 0, 1))
    assert atom_registry_problems(stranger, registry) == ("unknown_concept",)
    age = from_legacy("age", ("age", ("stated",), (("minimum", "18"), ("text_polarity", "excluded")), 0, 3))
    assert atom_registry_problems(age, registry) == ()  # an annotation is allowed on every concept
    odd = from_legacy("age", ("age", ("stated",), (("dose", "18"),), 0, 3))
    assert atom_registry_problems(odd, registry) == ("unknown_argument",)


def test_no_version_is_invented():
    assert provenance.CONCEPT_AUTHORITIES["local"][1] is None  # nothing borrowed from the NSCLC fragment
    assert provenance.CONCEPT_AUTHORITIES["ajcc"][1] is None  # named in notes, never pinned from its source
    seed = load_fragments()
    for entry in seed[0].concepts:
        assert entry.defined_on == "2026-11-01", entry.concept_id
        assert entry.scale is None or entry.scale[1] != seed[0].version, entry.concept_id
    ecog = compile_registry(seed).concepts["nsclc.ecog_ps"]
    assert ecog.scale == ("ECOG/Zubrod/WHO performance status, as criteria write it", UNVERSIONED)


def test_an_unversioned_scale_is_flagged_in_the_legacy_fragment_and_refused_in_a_new_package():
    assert LEGACY_FRAGMENTS == ("nsclc_legacy",)
    registry = compile_registry(load_fragments())
    assert registry.flags == (("unversioned_scale", "nsclc.ecog_ps", "nsclc_legacy"),)
    scaled = replace(HBA1C, concept_id="scales.ps", scale=("performance status", UNVERSIONED))
    assert codes([fragment("nsclc_legacy", [scaled])]) == []
    assert registry_flags([fragment("nsclc_legacy", [scaled])]) == (
        ("unversioned_scale", "scales.ps", "nsclc_legacy"),
    )
    assert codes([fragment("scales", [scaled])]) == ["unversioned_scale"]
    assert registry_flags([fragment("scales", [scaled])]) == ()  # refused there, never merely flagged
    pinned = replace(scaled, scale=("performance status", "Oken et al. 1982"))
    assert registry_flags([fragment("nsclc_legacy", [pinned])]) == ()
    assert compile_registry([fragment("measurements", [HBA1C])]).flags == ()
