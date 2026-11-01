"""The first predicate registry (openspec/changes/add-scoped-assertions task 1.2; design Decision 2).

The real criteria are the NSCLC criteria of tests/test_banks.py (2015-2024 Phase 3 records, as quoted there;
that file names no NCT ids), typed by the existing banks and carried through the bank contract.

Positive: every concept of the seed registry is mapped, and nothing else, with no problem against the registry
and the closed vocabularies; labs are measurements, age demographic, prior therapy treatment history, a named
condition its status, some an exposure, a medication or a procedure by a per-concept reading open to the
founder's ruling; the unsettled
concepts are listed and mapped "unresolved"; the mapping's version is its digest, the same in any order, and
the predicate registry carries each concept's authority and its fragment's exposure with its populations;
every atom the banks give on the real criteria becomes a well-formed literal of its own concept, its atom the
evidence, positive, a lab threshold a typed quantity with its unit as written, an ECOG range one score of
several, a stated age range an interval with unspecified boundaries.
Negative: a concept of no registry, a registry concept left unmapped, a kind outside a vocabulary, another
person as a concept's subject, a value kind its family does not take, a value kind reading an operand the
concept does not declare (life expectancy, QTc and pulmonary function as quantities), a unit on a value with
none and a concept mapped twice are each named; a Commitment no predicate kind names (vitamin premedication)
is unresolved, never a medication use; a registry that disagrees is refused naming every problem. An atom of
no mapping is unresolved, never guessed; an age with only its lower bound (the bank keeps no comparator) is
never "at least"; a decimal comma, an unknown comparator, reversed bounds, a unit other than the concept's
own, a stray value and a value kind with no reading are never read; text_polarity and modality are never
read, and a window, a grade, a scope or an expression is named back unread, never dropped silently; a mapping
outside the vocabularies and an atom without an id are refused.
"""

from dataclasses import replace

import pytest
from test_semantic_contracts import real_criteria

from TrialLedger.assertions import Evidence, Literal, Predicate, Subject, Value
from TrialLedger.banks import BANKS
from TrialLedger.predicates import (
    FAMILY_VALUE_KINDS,
    MAPPING_BY_CONCEPT,
    MAPPINGS,
    UNIT_AS_WRITTEN,
    UNRESOLVED,
    VERSION,
    PredicateError,
    PredicateMapping,
    _digest,
    atom_literal,
    mapping_problems,
    predicate_registry,
)
from TrialLedger.semantics.contracts import Atom, Span, from_legacy, legacy_result
from TrialLedger.semantics.loader import FAMILIES, compile_registry, load_fragments

REGISTRY = compile_registry(load_fragments())
SEED_FAMILIES = {concept: entry.family for concept, entry in REGISTRY.concepts.items()}
SEED_ARGUMENTS = {c: tuple(name for name, _ in entry.arguments) for c, entry in REGISTRY.concepts.items()}


def mapping(concept="nsclc.condition.hiv", kind="condition_status", value_kind="boolean", unit="", **more):
    return PredicateMapping(concept, kind, value_kind, unit, **more)


# ── mapping_problems ────────────────────────────────────────────────────────────────────────────────


def test_every_seed_concept_is_mapped_and_nothing_else():
    assert mapping_problems(MAPPINGS, SEED_FAMILIES, SEED_ARGUMENTS) == ()
    assert set(MAPPING_BY_CONCEPT) == set(REGISTRY.concepts)
    assert len(MAPPINGS) == len(MAPPING_BY_CONCEPT) == 91
    assert set(FAMILY_VALUE_KINDS) == set(FAMILIES)


def test_each_concept_has_the_kind_its_mapping_states():
    kinds = {concept: (m.kind, m.value_kind, m.unit, m.subject) for concept, m in MAPPING_BY_CONCEPT.items()}
    lab = ("measurement", "quantity", UNIT_AS_WRITTEN, "participant")
    assert kinds["nsclc.lab.creatinine_clearance"] == lab
    assert kinds["nsclc.age"] == ("demographic", "interval", "years", "participant")
    assert kinds["nsclc.prior_lines"] == ("treatment_history", "enum", "", "participant")
    assert kinds["nsclc.prior_agent.platinum"] == ("treatment_history", "boolean", "", "participant")
    assert kinds["nsclc.condition.hiv"] == ("condition_status", "boolean", "", "participant")
    assert kinds["nsclc.condition.smoking"][0] == "exposure"
    assert kinds["nsclc.condition.anticoagulant_use"][0] == "medication_use"
    assert kinds["nsclc.condition.recent_surgery"][0] == "procedure_event"
    assert kinds["nsclc.condition.informed_consent"][0] == "consent"
    assert kinds["nsclc.condition.pregnancy_or_breastfeeding"][0] == "reproductive_status"
    assert kinds["nsclc.biomarker.pd_l1"] == ("disease_attribute", "enum", "", "participant")
    assert kinds["nsclc.extent"][1] == "enum_set"  # recurrent and metastatic hold at once
    assert kinds["nsclc.ecog_ps"] == ("measurement", "enum", "", "participant")  # an ordinal scale's score
    # no seed concept names a subject other than the participant (tissue_available names no specimen)
    assert {c for c, k in kinds.items() if k[3] != "participant"} == set()


# Every row pinned: (kind, value kind, unit) of each concept, the vocabulary-table rows by their prefix, the
# named conditions by name; every subject is the participant (above).
PINNED_PREFIXES = {
    "nsclc.biomarker.": ("disease_attribute", "enum", ""),
    "nsclc.prior_agent.": ("treatment_history", "boolean", ""),
    "nsclc.lab.": ("measurement", "quantity", UNIT_AS_WRITTEN),
    "nsclc.histology.": ("disease_attribute", "boolean", ""),
}
PINNED_KINDS = {
    "nsclc.ecog_ps": ("measurement", "enum"),
    "nsclc.prior_lines": ("treatment_history", "enum"),
    "nsclc.stage": ("disease_attribute", "enum"),
    "nsclc.extent": ("disease_attribute", "enum_set"),
    "nsclc.setting_word": ("unresolved", "enum_set"),
    "nsclc.resection": ("unresolved", "enum_set"),
    "nsclc.organ_function_unspecified": ("unresolved", "enum"),
    "nsclc.age": ("demographic", "interval"),
    "nsclc.condition.informed_consent": ("consent", "boolean"),
    "nsclc.condition.compliance": ("unresolved", "boolean"),
    "nsclc.condition.contraception": ("unresolved", "boolean"),
    "nsclc.condition.pregnancy_or_breastfeeding": ("reproductive_status", "boolean"),
    "nsclc.condition.life_expectancy": ("measurement", "unresolved"),
    "nsclc.condition.measurable_disease": ("disease_attribute", "boolean"),
    "nsclc.condition.cns_metastases": ("disease_attribute", "boolean"),
    "nsclc.condition.other_malignancy": ("condition_status", "boolean"),
    "nsclc.condition.hiv": ("condition_status", "boolean"),
    "nsclc.condition.hepatitis": ("condition_status", "boolean"),
    "nsclc.condition.tuberculosis": ("condition_status", "boolean"),
    "nsclc.condition.active_infection": ("condition_status", "boolean"),
    "nsclc.condition.autoimmune_disease": ("condition_status", "boolean"),
    "nsclc.condition.pneumonitis_ild": ("condition_status", "boolean"),
    "nsclc.condition.organ_transplant": ("procedure_event", "boolean"),
    "nsclc.condition.immunosuppression_steroids": ("medication_use", "boolean"),
    "nsclc.condition.qtc": ("measurement", "unresolved"),
    "nsclc.condition.cardiac_disease": ("condition_status", "boolean"),
    "nsclc.condition.hypertension": ("condition_status", "boolean"),
    "nsclc.condition.bleeding_thrombosis": ("condition_status", "boolean"),
    "nsclc.condition.anticoagulant_use": ("medication_use", "boolean"),
    "nsclc.condition.gi_perforation_fistula": ("condition_status", "boolean"),
    "nsclc.condition.malabsorption": ("unresolved", "boolean"),
    "nsclc.condition.hypersensitivity": ("condition_status", "boolean"),
    "nsclc.condition.live_vaccine": ("exposure", "boolean"),
    "nsclc.condition.recent_surgery": ("procedure_event", "boolean"),
    "nsclc.condition.recent_radiotherapy": ("treatment_history", "boolean"),
    "nsclc.condition.unresolved_toxicity": ("condition_status", "boolean"),
    "nsclc.condition.tissue_available": ("unresolved", "boolean"),
    "nsclc.condition.other_investigational": ("unresolved", "boolean"),
    "nsclc.condition.interacting_medication": ("medication_use", "boolean"),
    "nsclc.condition.substance_or_psychiatric": ("condition_status", "boolean"),
    "nsclc.condition.smoking": ("exposure", "boolean"),
    "nsclc.condition.effusion": ("condition_status", "boolean"),
    "nsclc.condition.neurologic_disorder": ("condition_status", "boolean"),
    "nsclc.condition.pulmonary_function": ("measurement", "unresolved"),
    "nsclc.condition.weight_loss": ("condition_status", "boolean"),
    "nsclc.condition.investigator_judgment": ("unresolved", "boolean"),
    "nsclc.condition.serious_comorbidity": ("condition_status", "boolean"),
    "nsclc.condition.sex": ("demographic", "enum"),
    "nsclc.condition.diagnosis_confirmed": ("unresolved", "boolean"),
    "nsclc.condition.prior_enrollment": ("unresolved", "boolean"),
    "nsclc.condition.vitamin_premedication": ("unresolved", "boolean"),
    "nsclc.condition.organ_impairment": ("condition_status", "boolean"),
}


def pinned(concept):
    prefixed = [row for prefix, row in PINNED_PREFIXES.items() if concept.startswith(prefix)]
    if prefixed:
        return prefixed[0]
    return (*PINNED_KINDS[concept], "years" if concept == "nsclc.age" else "")


def test_every_row_is_pinned():
    assert {c: (m.kind, m.value_kind, m.unit) for c, m in MAPPING_BY_CONCEPT.items()} == {
        c: pinned(c) for c in REGISTRY.concepts
    }
    assert sum(not c.startswith(tuple(PINNED_PREFIXES)) for c in REGISTRY.concepts) == len(PINNED_KINDS)


def test_the_unsettled_concepts_are_unresolved_never_guessed():
    assert UNRESOLVED == (
        "nsclc.setting_word",
        "nsclc.resection",
        "nsclc.organ_function_unspecified",
        "nsclc.condition.compliance",
        "nsclc.condition.contraception",
        "nsclc.condition.malabsorption",
        "nsclc.condition.tissue_available",
        "nsclc.condition.other_investigational",
        "nsclc.condition.investigator_judgment",
        "nsclc.condition.diagnosis_confirmed",
        "nsclc.condition.prior_enrollment",
        "nsclc.condition.vitamin_premedication",  # an undertaking (Commitment), as compliance is
    )
    for concept in UNRESOLVED:
        assert MAPPING_BY_CONCEPT[concept].note.startswith("unresolved: "), concept
    assert not any(m.note.startswith("unresolved") for m in MAPPINGS if m.concept_id not in UNRESOLVED)


def test_each_disagreement_is_named():
    families = {"nsclc.condition.hiv": "State", "nsclc.lab.alt": "Measurement", "x.odd": "Unknown"}
    mappings = (
        mapping(),
        mapping("nsclc.lab.alt", "lab_value", "number", "U/L"),
        mapping("x.none"),
        mapping("nsclc.condition.hiv", "measurement"),
        mapping("x.odd", value_kind="enum", subject="investigator"),
    )
    assert mapping_problems(mappings, families, {}) == (
        ("predicate_kind_outside_vocabulary", "nsclc.lab.alt"),
        ("value_kind_outside_vocabulary", "nsclc.lab.alt"),
        ("unit_not_for_value_kind", "nsclc.lab.alt"),  # a unit only on a quantity or an interval
        ("concept_of_no_registry", "x.none"),
        ("duplicate_mapping", "nsclc.condition.hiv"),
        ("subject_kind_outside_vocabulary", "x.odd"),
        ("value_kind_not_for_family", "x.odd"),  # an unknown family takes no value kind
    )


def test_a_value_kind_must_fit_the_family_and_a_unit_its_value():
    families = {"a.state": "State", "a.measure": "Measurement", "a.event": "Event"}
    declared = {"a.state": ("comparator", "value", "unit"), "a.measure": ("comparator", "value", "unit")}
    assert mapping_problems(
        (
            mapping("a.state", value_kind="quantity", unit="mg/dL"),
            mapping("a.measure", "measurement", "boolean", "mg/dL"),
            mapping("a.event", "procedure_event", "unresolved", "days"),
        ),
        families,
        declared,
    ) == (
        ("value_kind_not_for_family", "a.state"),
        ("value_kind_not_for_family", "a.measure"),
        ("unit_not_for_value_kind", "a.measure"),
        ("unit_not_for_value_kind", "a.event"),
    )
    # an unresolved value kind fits every family; a quantity's or interval's unit is its own
    fitting = (
        mapping("a.state", value_kind="unresolved"),
        mapping("a.measure", "measurement", "quantity", "mg/dL"),
        mapping("a.event", "procedure_event", "boolean"),
    )
    assert mapping_problems(fitting, families, declared) == ()


def test_a_value_kind_must_read_only_operands_the_concept_declares():
    # the named measurements declare a window alone: as quantities, no atom of them could carry a number
    named = ("nsclc.condition.life_expectancy", "nsclc.condition.qtc", "nsclc.condition.pulmonary_function")
    assert all(SEED_ARGUMENTS[c] == ("window",) for c in named)
    as_quantities = tuple(
        replace(m, value_kind="quantity", unit=UNIT_AS_WRITTEN) if m.concept_id in named else m
        for m in MAPPINGS
    )
    assert mapping_problems(as_quantities, SEED_FAMILIES, SEED_ARGUMENTS) == tuple(
        ("operand_not_declared", c) for c in named
    )
    families = {"a.m": "Measurement", "a.n": "Measurement"}
    declared = {"a.m": ("minimum", "maximum"), "a.n": ("comparator", "value")}
    assert mapping_problems(
        (mapping("a.m", "measurement", "quantity"), mapping("a.n", "measurement", "quantity")),
        families,
        declared,
    ) == (("operand_not_declared", "a.m"), ("operand_not_declared", "a.n"))  # "unit" undeclared for a.n
    assert (
        mapping_problems(
            (mapping("a.m", "measurement", "interval"), mapping("a.n", "measurement", "enum")),
            families,
            declared,
        )
        == ()
    )
    # a concept of no registry is named as such, never also for its operands
    assert mapping_problems((mapping("x.none", "measurement", "quantity"),), {}, {}) == (
        ("concept_of_no_registry", "x.none"),
    )


def test_another_person_is_never_a_concepts_subject_and_an_unmapped_concept_is_named():
    families = {"a.b": "State", "a.c": "State", "a.a": "Event"}
    assert mapping_problems((mapping("a.b", subject="other_person"),), families, {}) == (
        ("subject_without_referent", "a.b"),
        ("registry_concept_unmapped", "a.a"),
        ("registry_concept_unmapped", "a.c"),
    )
    assert mapping_problems((), {}, {}) == ()
    assert mapping_problems((mapping("a.b", "unresolved", subject="unresolved"),), {"a.b": "State"}, {}) == ()


def test_the_version_is_the_mappings_digest_in_any_order():
    assert VERSION == _digest(MAPPINGS) == _digest(tuple(reversed(MAPPINGS)))
    assert len(VERSION) == 64
    changed = tuple(replace(m, kind="unresolved") if m.concept_id == "nsclc.age" else m for m in MAPPINGS)
    assert _digest(changed) != VERSION
    assert _digest(MAPPINGS[1:]) != VERSION


def test_the_registry_carries_each_concepts_provenance():
    registry = predicate_registry()
    assert registry.version == VERSION and registry.concept_registry == REGISTRY.version
    assert set(registry.entries) == set(REGISTRY.concepts)
    stage, hiv, squamous = (
        registry.entries[c] for c in ("nsclc.stage", "nsclc.condition.hiv", "nsclc.histology.squamous")
    )
    assert (stage.authority, hiv.authority, squamous.authority) == ("ajcc", "local", "who_thoracic")
    assert {(e.exposure, e.populations) for e in registry.entries.values()} == {
        ("fragment:nsclc_legacy", ("nsclc_phase3_2015_2024", "pilot_2026_10_31"))
    }
    assert registry.entries["nsclc.age"].mapping == MAPPING_BY_CONCEPT["nsclc.age"]


def test_a_registry_that_disagrees_is_refused_naming_every_problem():
    with pytest.raises(PredicateError) as refused:
        predicate_registry(mappings=(*MAPPINGS[1:], mapping("x.none")))
    assert refused.value.args == (
        (("concept_of_no_registry", "x.none"), ("registry_concept_unmapped", "nsclc.ecog_ps")),
    )


# ── atom_literal ────────────────────────────────────────────────────────────────────────────────────
#
# Each test calls atom_literal itself and compares its whole outcome, so every reading is pinned directly.


def atoms_of(text):
    return [
        atom for bank, function in BANKS.items() for atom in legacy_result(bank, text, function(text)).atoms
    ]


def atom_of(text, concept):
    return next(atom for atom in atoms_of(text) if atom.concept_id == concept)


def fact(atom, kind, value, subject="participant"):
    """The literal atom_literal should give: positive, timeless, unqualified, the atom its evidence."""
    evidence = (Evidence("atom_ref", atom.atom_id),)
    return Literal(Subject(subject), Predicate(kind, atom.concept_id), value, evidence=evidence)


def test_every_real_atom_becomes_a_literal_of_its_own_concept():
    codes = set()
    for text in real_criteria():
        for atom in atoms_of(text):
            code, literal, unread = atom_literal(MAPPING_BY_CONCEPT.get(atom.concept_id), atom)
            codes.add(code)
            assert literal.predicate == Predicate(MAPPING_BY_CONCEPT[atom.concept_id].kind, atom.concept_id)
            assert literal.polarity == "positive" and literal.evidence == (
                Evidence("atom_ref", atom.atom_id),
            )
            assert not {"text_polarity", "modality"} & set(unread)
    # operand_not_read: life expectancy, a named measurement whose value is unresolved
    assert codes == {"mapped", "predicate_unresolved", "operand_not_kept", "operand_not_read"}


def test_a_lab_threshold_is_a_typed_quantity_with_its_unit_as_written():
    text = "* Platelets ≥ 100 × 10^9/L; Hemoglobin ≥ 9 g/dL; Creatinine ≤ 1.5 mg/dL"
    creatinine = atom_of(text, "nsclc.lab.creatinine")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.lab.creatinine"], creatinine) == (
        "mapped",
        fact(creatinine, "measurement", Value("quantity", "le", number=1.5, unit="mg/dL")),
        (),
    )
    text = "* Documented ALK-positive disease, stage IV, after progression on platinum; AST ≤ 2.5 × ULN"
    ast = atom_of(text, "nsclc.lab.ast")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.lab.ast"], ast) == (
        "mapped",
        fact(ast, "measurement", Value("quantity", "le", number=2.5, unit="× ULN")),
        (),
    )


def test_scores_states_and_counts_are_members():
    ecog = atom_of("5. World Health Organization (WHO) performance status 0-2", "nsclc.ecog_ps")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.ecog_ps"], ecog) == (
        "mapped",
        fact(ecog, "measurement", Value("enum", "in", ("0", "1", "2"))),
        (),
    )
    egfr = atom_of("* Positive EGFR gene mutation (19/21)", "nsclc.biomarker.egfr")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.biomarker.egfr"], egfr) == (
        "mapped",
        fact(egfr, "disease_attribute", Value("enum", "eq", ("positive",))),
        (),
    )
    lines = atom_of("* Untreated advanced NSCLC", "nsclc.prior_lines")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.prior_lines"], lines) == (
        "mapped",
        fact(lines, "treatment_history", Value("enum", "eq", ("0",))),
        ("scope",),
    )
    extent = atom_of("* Untreated advanced NSCLC", "nsclc.extent")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.extent"], extent) == (
        "mapped",
        fact(extent, "disease_attribute", Value("enum_set", "in", ("advanced",))),  # "in" even of one
        (),
    )
    stage = atom_of("* Stage IB-IIIA NSCLC, excluding stage IV", "nsclc.stage")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.stage"], stage) == (
        "mapped",
        fact(stage, "disease_attribute", Value("enum", "in", ("I", "II", "III"))),
        ("expression",),  # "IB-IIIA" is narrower than its groups: D5's to attach, never dropped
    )


def test_a_stated_age_range_is_an_interval_and_a_lower_bound_alone_is_unresolved():
    ranged = atom_of("8. Aged 18 to 75 years, ECOG PS: 0-1", "nsclc.age")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.age"], ranged) == (
        "mapped",
        fact(ranged, "demographic", Value("interval", "in", number=18.0, upper=75.0, unit="years")),
        (),
    )
    # "≥ 18 years": the bank keeps no comparator ("older than 18" is another), so never "at least 18"
    alone = atom_of("1. Male or female ≥ 18 years.", "nsclc.age")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.age"], alone) == (
        "operand_not_kept",
        fact(alone, "demographic", Value("unresolved")),
        (),
    )


def test_a_named_condition_is_its_status_and_its_window_is_left_unread():
    text = "7. Receipt of live attenuated vaccine within 30 days prior to the first dose of IP."
    vaccine = atom_of(text, "nsclc.condition.live_vaccine")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.condition.live_vaccine"], vaccine) == (
        "mapped",
        fact(vaccine, "exposure", Value("boolean")),
        ("window",),
    )
    # a named measurement's value is unresolved: the concept declares no number, so none is read
    life = atom_of("Life expectancy ≥ 12 weeks", "nsclc.condition.life_expectancy")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.condition.life_expectancy"], life) == (
        "operand_not_read",
        fact(life, "measurement", Value("unresolved")),
        ("window",),
    )
    sex = atom_of("2. Age ≥ 18 years and \\<75 years male or females;", "nsclc.condition.sex")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.condition.sex"], sex) == (
        "operand_not_kept",  # either sex: no member named
        fact(sex, "demographic", Value("unresolved")),
        (),
    )


def test_an_annotation_is_never_read():
    # an inclusion criterion of test_banks.py whose sentence says the EGFR-mutated "are excluded"
    text = next(t for t in real_criteria() if t.startswith("* No prior treatment for Stage IV NSCLC."))
    egfr = atom_of(text, "nsclc.biomarker.egfr")
    assert ("text_polarity", "excluded") in egfr.params
    egfr_mapping = MAPPING_BY_CONCEPT["nsclc.biomarker.egfr"]
    stated = fact(egfr, "disease_attribute", Value("enum", "eq", ("positive",)))
    assert atom_literal(egfr_mapping, egfr) == ("mapped", stated, ())
    params = (("modality", "permitted"), ("expression", "≥50%"), ("expression", "≥1%"))
    permitted = replace(egfr, params=params)
    assert atom_literal(egfr_mapping, permitted) == ("mapped", stated, ("expression",))  # each name once


def test_an_unsettled_concept_keeps_its_value():
    text = "* Complete resection of histologically confirmed Stage IB to IIIA NSCLC, eligible for adjuvant "
    setting = atom_of(text + "therapy", "nsclc.setting_word")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.setting_word"], setting) == (
        "predicate_unresolved",
        fact(setting, "unresolved", Value("enum_set", "in", ("adjuvant",))),
        (),
    )
    organ = atom_of("* Adequate hematologic and renal function", "nsclc.organ_function_unspecified")
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.organ_function_unspecified"], organ) == (
        "predicate_unresolved",
        fact(organ, "unresolved", Value("enum", "eq", ("adequate",))),
        (),
    )
    tissue = from_legacy("conditions", ("condition", ("tissue_available",), (), 0, 3))
    assert atom_literal(MAPPING_BY_CONCEPT["nsclc.condition.tissue_available"], tissue) == (
        "predicate_unresolved",
        fact(tissue, "unresolved", Value("boolean")),
        (),
    )


def test_an_atom_of_no_mapping_is_unresolved_never_guessed():
    params = (("window", "1 year"), ("modality", "permitted"), ("window", "2 years"))
    atom = from_legacy("histology", ("histology", ("adenosquamous",), params, 0, 4))
    unresolved = fact(atom, "unresolved", Value("unresolved"), subject="unresolved")
    assert atom_literal(None, atom) == ("concept_not_mapped", unresolved, ("window",))
    # another concept's mapping is no mapping of this atom
    squamous = MAPPING_BY_CONCEPT["nsclc.histology.squamous"]
    assert atom_literal(squamous, atom) == ("concept_not_mapped", unresolved, ("window",))


def lab_atom(*params):
    return from_legacy("organ_function", ("lab", ("ALT",), params, 0, 3))


def test_a_quantity_is_read_only_from_a_known_comparator_and_a_plain_number():
    alt = MAPPING_BY_CONCEPT["nsclc.lab.alt"]
    for params, code in (
        ((("comparator", "≥"), ("value", "1,5"), ("unit", "× ULN")), "operand_not_read"),  # 1.5 or 1,500?
        ((("comparator", "="), ("value", "2"), ("unit", "× ULN")), "operand_not_read"),
        ((("comparator", "≥"),), "operand_not_kept"),
        ((("value", "40"),), "operand_not_kept"),
    ):
        atom = lab_atom(*params)
        assert atom_literal(alt, atom) == (code, fact(atom, "measurement", Value("unresolved")), ()), params
    atom = lab_atom(("comparator", ">"), ("value", "40"), ("qualifier", "with liver metastases"))
    assert atom_literal(alt, atom) == (
        "mapped",
        fact(atom, "measurement", Value("quantity", "gt", number=40.0)),  # no unit written: ""
        ("qualifier",),
    )
    atom = lab_atom(("comparator", "<"), ("value", "3"), ("unit", "x ULN"))
    below = Value("quantity", "lt", number=3.0, unit="x ULN")
    assert atom_literal(alt, atom) == ("mapped", fact(atom, "measurement", below), ())
    # a concept's own unit is never put in place of another the atom writes ("3 x ULN" is not "3 U/L")
    own = replace(alt, unit="U/L")
    assert atom_literal(own, atom) == ("operand_not_read", fact(atom, "measurement", Value("unresolved")), ())
    fixed = Value("quantity", "lt", number=3.0, unit="U/L")
    same = lab_atom(("comparator", "<"), ("value", "3"), ("unit", "U/L"))
    assert atom_literal(own, same) == ("mapped", fact(same, "measurement", fixed), ())
    unwritten = lab_atom(("comparator", "<"), ("value", "3"))
    assert atom_literal(own, unwritten) == ("mapped", fact(unwritten, "measurement", fixed), ())
    unitless = Value(
        "quantity", "lt", number=3.0
    )  # a concept with no unit: one written is another measurement
    assert atom_literal(replace(alt, unit=""), atom) == (
        "operand_not_read",
        fact(atom, "measurement", Value("unresolved")),
        (),
    )
    assert atom_literal(replace(alt, unit=""), unwritten) == (
        "mapped",
        fact(unwritten, "measurement", unitless),
        (),
    )


def age_atom(*params):
    return from_legacy("age", ("age", ("stated",), params, 0, 3))


def test_an_interval_is_read_only_from_two_plain_ordered_bounds():
    age = MAPPING_BY_CONCEPT["nsclc.age"]
    for params, code in (
        ((("minimum", "75"), ("maximum", "18")), "operand_not_read"),  # reversed
        ((("minimum", "18"), ("maximum", "seventy")), "operand_not_read"),
        ((("minimum", "eighteen"), ("maximum", "75")), "operand_not_read"),
        ((("maximum", "75"),), "operand_not_kept"),
        ((("minimum", "18"),), "operand_not_kept"),
        ((), "operand_not_kept"),
    ):
        atom = age_atom(*params)
        assert atom_literal(age, atom) == (code, fact(atom, "demographic", Value("unresolved")), ()), params
    atom = age_atom(("minimum", "18"), ("maximum", "18"))
    point = Value("interval", "in", number=18.0, upper=18.0, unit="years")
    assert atom_literal(age, atom) == ("mapped", fact(atom, "demographic", point), ())
    # a unit the atom writes is not an interval's operand: named back unread, and never replaced by "years"
    months = age_atom(("minimum", "6"), ("maximum", "18"), ("unit", "months"))
    assert atom_literal(age, months) == (
        "operand_not_read",
        fact(months, "demographic", Value("unresolved")),
        ("unit",),
    )
    years = age_atom(("minimum", "18"), ("maximum", "75"), ("unit", "years"))
    ranged = Value("interval", "in", number=18.0, upper=75.0, unit="years")
    assert atom_literal(age, years) == ("mapped", fact(years, "demographic", ranged), ("unit",))


def test_a_stray_value_or_a_kind_with_no_reading_is_never_read():
    hiv = MAPPING_BY_CONCEPT["nsclc.condition.hiv"]
    stray = from_legacy("conditions", ("condition", ("hiv", "positive"), (), 0, 3))
    unread = fact(stray, "condition_status", Value("unresolved"))
    assert atom_literal(hiv, stray) == ("operand_not_read", unread, ())
    named = from_legacy("conditions", ("condition", ("hiv",), (("window", "6 months"),), 0, 3))
    assert atom_literal(hiv, named) == (
        "mapped",
        fact(named, "condition_status", Value("boolean")),
        ("window",),
    )
    for kind in ("entity_ref", "definition_ref", "unresolved"):
        assert atom_literal(replace(hiv, value_kind=kind), named) == (
            "operand_not_read",
            fact(named, "condition_status", Value("unresolved")),
            ("window",),
        ), kind
    ecog = MAPPING_BY_CONCEPT["nsclc.ecog_ps"]
    none = from_legacy("performance_status", ("ecog_ps", (), (), 0, 3))
    assert atom_literal(ecog, none) == (
        "operand_not_kept",
        fact(none, "measurement", Value("unresolved")),
        (),
    )
    one = from_legacy("performance_status", ("ecog_ps", ("1",), (), 0, 3))
    assert atom_literal(ecog, one) == ("mapped", fact(one, "measurement", Value("enum", "eq", ("1",))), ())
    assert atom_literal(replace(ecog, value_kind="enum_set"), one) == (
        "mapped",
        fact(one, "measurement", Value("enum_set", "in", ("1",))),
        (),
    )


def test_a_mapping_outside_the_vocabularies_or_an_atom_without_an_id_is_refused():
    named = from_legacy("conditions", ("condition", ("hiv",), (), 0, 3))
    hiv = MAPPING_BY_CONCEPT["nsclc.condition.hiv"]
    for refused_mapping, atom, problem in (
        (replace(hiv, kind="xcondition_status"), named, "predicate_kind_outside_vocabulary"),
        (replace(hiv, kind="xunresolved"), named, "predicate_kind_outside_vocabulary"),
        (replace(hiv, subject="investigator"), named, "subject_kind_outside_vocabulary"),
        (replace(hiv, subject="other_person"), named, "other_person_without_referent"),
        (hiv, replace(named, atom_id=""), "evidence_without_ref"),
        (None, replace(named, atom_id=""), "evidence_without_ref"),
    ):
        try:
            outcome = atom_literal(refused_mapping, atom)
        except Exception as error:  # every exception, so a wrong one is a wrong value, never a crash
            outcome = (type(error).__name__, error.args)
        assert outcome == ("ModelError", (problem,))


def test_a_refused_mapping_is_refused_by_its_own_first_problem():
    """Positive: the problem named is the mapping's own (its kind, its subject), whatever its value kind and
    however its concept id is written (one segment, no dot). Negative: never a problem of a value built
    otherwise (an "eq" member set, an "in" of one enum member) nor an index past the concept id's one segment.
    The witnesses are Detective's (converge, 2026-11-01)."""
    bare = Atom("x", "x", "x", "x", ("x",), (("x", "x"),), (Span("whole", 0, 1),), "x", "x")
    extent = from_legacy("setting", ("extent", ("recurrent",), (), 10, 20))
    organ = from_legacy("organ_function", ("organ_function_unspecified", ("adequate",), (), 2, 41))
    surgery = from_legacy("conditions", ("condition", ("recent_surgery",), (), 27, 34))
    for refused_mapping, atom, problem in (
        (PredicateMapping("x", "x", "x", "x", "x", "x"), bare, "subject_kind_outside_vocabulary"),
        (
            replace(MAPPING_BY_CONCEPT["nsclc.extent"], kind="xdisease_attribute"),
            extent,
            "predicate_kind_outside_vocabulary",
        ),
        (
            replace(MAPPING_BY_CONCEPT["nsclc.organ_function_unspecified"], kind="xunresolved"),
            organ,
            "predicate_kind_outside_vocabulary",
        ),
        (
            replace(MAPPING_BY_CONCEPT["nsclc.condition.recent_surgery"], kind="xprocedure_event"),
            surgery,
            "predicate_kind_outside_vocabulary",
        ),
    ):
        try:
            outcome = atom_literal(refused_mapping, atom)
        except Exception as error:  # every exception, so a wrong one is a wrong value, never a crash
            outcome = (type(error).__name__, error.args)
        assert outcome == ("ModelError", (problem,))
