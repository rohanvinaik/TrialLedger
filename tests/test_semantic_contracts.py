"""The bank contract — atoms with evidence spans, findings with five codes, and today's atoms through it.

The real criteria are the NSCLC criteria of tests/test_banks.py (2015-2024 Phase 3 records, as quoted there).

Positive: every atom the existing banks give on those criteria comes through the contract with no problem and
goes back unchanged (to_legacy ∘ from_legacy is the identity), so the banks report through the contract
without changing their outputs; a measurement and an event in one criterion ("HbA1c ≤8.0% and no myocardial
infarction within six months before randomization", the spec's scenario) are held with their concept, value,
unit, comparator and window spans apart; an atom's id is its content's digest, the same on every run;
concept ids name the legacy vocabulary entry (nsclc.condition.hiv, nsclc.biomarker.pd_l1).
Negative: a bank that recognizes nothing reports NO_TRIGGER, never ABSTAINED and never an absence; blank text
is INVALID_INPUT; a span outside the text, a span of unknown role, an atom with no span, unsorted or repeated
values, a repeated parameter or a tampered id each break the contract by name; a result that says both "atoms"
and NO_TRIGGER, says nothing, or emits an atom no IDENTIFIED finding names is refused; an atom with no legacy
concept is never turned into a legacy atom.
"""

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from TrialLedger.banks import BANKS
from TrialLedger.semantics.contracts import (
    Atom,
    BankResult,
    Finding,
    Span,
    atom_digest,
    atom_problems,
    from_legacy,
    legacy_concept_id,
    legacy_result,
    result_problems,
    slug,
    to_legacy,
)

HERE = Path(__file__).resolve().parent


def real_criteria() -> list[str]:
    """Every criterion text quoted in tests/test_banks.py (string constants over 25 characters)."""
    tree = ast.parse((HERE / "test_banks.py").read_text(encoding="utf-8"))
    found = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 25
    }
    return sorted(found)


def test_every_real_legacy_atom_comes_through_the_contract_unchanged():
    seen = 0
    for text in real_criteria():
        for bank, function in BANKS.items():
            atoms = function(text)
            result = legacy_result(bank, text, atoms)
            assert result_problems(result, text) == (), (bank, text)
            assert [to_legacy(atom) for atom in result.atoms] == atoms
            seen += len(atoms)
    assert seen > 100  # the fixture is the whole of test_banks.py's criteria, not a handful


def test_a_legacy_atom_keeps_its_span_whole_and_its_params_as_written():
    text = "ii. Alanine aminotransferase (ALT) and aspartate aminotransferase (AST)≤2.5×ULN."
    legacy = BANKS["organ_function"](text)[0]
    atom = from_legacy("organ_function", legacy)
    assert atom.spans == (Span("whole", legacy[3], legacy[4]),)  # one span, its parts not re-searched
    assert atom.params == legacy[2] and atom.values == legacy[1]
    assert atom.concept_id == "nsclc.lab.alt" and atom.mention_kind == "value_stated"
    assert atom.rule_id == "banks.organ_function" and atom.owner_bank == "organ_function"


@pytest.mark.parametrize(
    "concept, values, expected",
    [
        ("condition", ("hiv",), "nsclc.condition.hiv"),
        ("lab", ("creatinine clearance",), "nsclc.lab.creatinine_clearance"),
        ("prior_agent", ("PD-L1",), "nsclc.prior_agent.pd_l1"),
        ("biomarker:PD-L1", ("negative", "positive"), "nsclc.biomarker.pd_l1"),
        ("ecog_ps", ("0", "1"), "nsclc.ecog_ps"),
        ("stage", ("IV",), "nsclc.stage"),
        ("condition", (), ""),
        ("", ("x",), ""),
    ],
)
def test_legacy_concept_ids(concept, values, expected):
    assert legacy_concept_id(concept, values) == expected


def test_slug():
    assert slug("PD-L1") == "pd_l1"
    assert slug("creatinine clearance") == "creatinine_clearance"
    assert slug("  EGFR inhibitor ") == "egfr_inhibitor"
    assert slug("immune checkpoint") != slug("immune-checkpoint inhibitor")


def test_a_measurement_and_an_event_hold_their_spans_apart():
    text = "HbA1c ≤8.0% and no myocardial infarction within six months before randomization"
    spans = (
        Span("concept", 0, 5),
        Span("comparator", 6, 7),
        Span("value", 7, 10),
        Span("unit", 10, 11),
    )
    params = (("comparator", "≤"), ("unit", "%"), ("value", "8.0"))
    hba1c = Atom(
        atom_digest("measurements", "lab.hba1c", (), params, spans, "rule.hba1c"),
        "measurements",
        "lab.hba1c",
        "value_stated",
        (),
        params,
        spans,
        "rule.hba1c",
    )
    event_spans = (Span("concept", 19, 40), Span("window", 41, len(text)))
    mi_id = atom_digest("events", "event.mi", (), (), event_spans, "rule.mi")
    mi = Atom(mi_id, "events", "event.mi", "named", (), (), event_spans, "rule.mi")
    assert [text[s.start : s.end] for s in hba1c.spans] == ["HbA1c", "≤", "8.0", "%"]
    assert text[19:40] == "myocardial infarction"
    assert text[41:] == "within six months before randomization"
    findings = (
        Finding("IDENTIFIED", "measurements", "lab.hba1c", spans[0], hba1c.atom_id),
        Finding("IDENTIFIED", "events", "event.mi", event_spans[0], mi.atom_id),
    )
    # the negation ("no") and the conjunction are the assertion layer's: neither atom carries them
    assert result_problems(BankResult((hba1c, mi), findings), text) == ()


def test_an_atom_id_is_its_contents_digest():
    atom = from_legacy("age", ("age", ("stated",), (("minimum", "18"),), 2, 15))
    again = from_legacy("age", ("age", ("stated",), (("minimum", "18"),), 2, 15))
    assert atom.atom_id == again.atom_id and len(atom.atom_id) == 16
    moved = from_legacy("age", ("age", ("stated",), (("minimum", "18"),), 3, 15))
    assert moved.atom_id != atom.atom_id


def test_nothing_recognized_is_no_trigger_never_an_absence():
    text = "* Other inclusion criteria may apply."
    result = legacy_result("conditions", text, BANKS["conditions"](text))
    assert result.atoms == () and [f.code for f in result.findings] == ["NO_TRIGGER"]
    assert result_problems(result, text) == ()
    assert "ABSTAINED" not in {f.code for f in result.findings}


@pytest.mark.parametrize("text", ["", "   \n\t"])
def test_blank_text_is_invalid_input(text):
    result = legacy_result("age", text, [])
    assert [f.code for f in result.findings] == ["INVALID_INPUT"] and result.atoms == ()


TEXT = "* Age ≥ 18 years"


def good_atom() -> Atom:
    return from_legacy("age", ("age", ("stated",), (("minimum", "18"),), 2, 16))


def test_a_good_atom_has_no_problem():
    assert atom_problems(good_atom(), TEXT) == ()


@pytest.mark.parametrize(
    "change, problem",
    [
        ({"spans": (Span("whole", 2, 99),)}, "span_out_of_bounds"),
        ({"spans": (Span("whole", 5, 5),)}, "span_out_of_bounds"),
        ({"spans": (Span("gist", 2, 16),)}, "unknown_span_role"),
        ({"spans": ()}, "no_evidence"),
        ({"values": ("b", "a")}, "unsorted_values"),
        ({"values": ("a", "a")}, "duplicate_values"),
        ({"params": (("minimum", "18"), ("minimum", "21"))}, "duplicate_param"),
        ({"mention_kind": "guessed"}, "unknown_mention_kind"),
        ({"rule_id": ""}, "empty_rule"),
        ({"owner_bank": ""}, "empty_owner"),
        ({"concept_id": ""}, "empty_concept"),
    ],
)
def test_each_contract_breach_is_named(change, problem):
    assert problem in atom_problems(replace(good_atom(), **change), TEXT)


def test_a_tampered_atom_no_longer_matches_its_id():
    assert atom_problems(replace(good_atom(), values=("altered",)), TEXT) == ("wrong_atom_id",)


def test_inconsistent_results_are_refused():
    atom = good_atom()
    identified = Finding("IDENTIFIED", "age", atom.concept_id, atom.spans[0], atom.atom_id)
    no_trigger = Finding("NO_TRIGGER", "age", None, None, "")
    assert "atoms_with_no_trigger" in result_problems(BankResult((atom,), (identified, no_trigger)), TEXT)
    invalid = Finding("INVALID_INPUT", "age", None, None, "")
    assert "atoms_with_invalid_input" in result_problems(BankResult((atom,), (identified, invalid)), TEXT)
    assert result_problems(BankResult((), ()), TEXT) == ("no_finding",)
    assert result_problems(BankResult((atom,), (no_trigger,)), TEXT) == (
        "atom_without_identified",
        "atoms_with_no_trigger",
    )
    odd = Finding("PROBABLY", "age", None, Span("whole", 0, 99), "")
    assert result_problems(BankResult((), (odd,)), TEXT) == ("unknown_finding_code", "span_out_of_bounds")


def test_a_native_atom_has_no_legacy_form():
    with pytest.raises(ValueError):
        to_legacy(replace(good_atom(), legacy_concept=None))
