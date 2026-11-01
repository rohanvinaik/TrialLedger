"""The registry's last three refusals (add-bank-coverage Decision 2, with the shared parsers of task 3.1):
unsupported units, invalid spans and nondeterministic fragments, each by its named code.

The examples are real criteria of tests/test_banks.py ("* Platelets ≥ 100 × 10^9/L; Hemoglobin ≥ 9 g/dL;
Creatinine ≤ 1.5 mg/dL"; "ii. ... (AST)≤2.5×ULN.") and the spec's HbA1c scenario.

Positive: a concept whose declared units the parsers read whole, each with its UCUM form where its unit
argument is ucum_unit, compiles, and so does one whose unmapped unit ("G/L") is declared as written
(unit_as_written); examples whose comparator, unit and numeric value spans are read there by the parsers
compile; a fragment loaded twice alike loads; the seed registry's version is unchanged by the new fields,
which enter its canonical form only when used; units and examples are parsed from a fragment's data exactly.
Negative: a unit with no UCUM form under ucum_unit, a reference expression declared as a unit ("× ULN"), a
unit the parsers do not read whole ("mg/dL and"), a pair of words ("AST/ALT") even as written, and units on a
concept that takes no unit are unsupported_unit; a span out of its example's text, empty, of no contract role,
a unit span over "×ULN" or over "Male/female", a comparator span that is no comparator and a numeric value
span that is no number are invalid_span; a fragment holding a set or a NaN (named once, by its place), or one
whose two loads differ (a random draw), is nondeterministic_fragment; a span offset that is not an integer is
a malformed fragment.
"""

import json
import math
from dataclasses import replace

import pytest

from TrialLedger import provenance
from TrialLedger.semantics.contracts import Span
from TrialLedger.semantics.loader import (
    PROBLEM_CODES,
    ConceptEntry,
    Example,
    Fragment,
    RegistryError,
    compile_registry,
    example_problems,
    fragment_from_data,
    load_fragments,
    nondeterminism_problems,
    registry_problems,
    unit_problems,
)

LABS = "* Platelets ≥ 100 × 10^9/L; Hemoglobin ≥ 9 g/dL; Creatinine ≤ 1.5 mg/dL"
ALT = "ii. Alanine aminotransferase (ALT) and aspartate aminotransferase (AST)≤2.5×ULN."
SEX = "Male/female aged 18 (constructed)"
HEMOGLOBIN = ConceptEntry(
    "lab.hemoglobin",
    "Measurement",
    (("comparator", "comparator"), ("value", "number"), ("unit", "ucum_unit")),
    "local",
    None,
    "haemoglobin concentration in blood, the unit as written",
    None,
    (),
    "2026-11-01",
    ("g/dL", "g/L", "mmol/L"),
    (
        Example(
            LABS,
            (
                Span("concept", 28, 38),
                Span("comparator", 39, 40),
                Span("value", 41, 42),
                Span("unit", 43, 47),
            ),
        ),
    ),
)


def problems(entry):
    fragment = Fragment("measurements", "1", "fragment:nsclc_legacy", (), (entry,), ())
    return registry_problems([fragment], provenance.CONCEPT_AUTHORITIES, provenance.RULE_EXPOSURE)


def test_the_three_codes_are_named():
    assert PROBLEM_CODES[-3:] == ("unsupported_unit", "invalid_span", "nondeterministic_fragment")


def test_a_concept_whose_units_and_spans_the_parsers_read_compiles():
    assert [LABS[s.start : s.end] for s in HEMOGLOBIN.examples[0].spans] == ["Hemoglobin", "≥", "9", "g/dL"]
    assert problems(HEMOGLOBIN) == ()
    assert unit_problems(HEMOGLOBIN) == () and example_problems(HEMOGLOBIN) == ()
    as_written = replace(HEMOGLOBIN, arguments=(("unit", "unit_as_written"),), units=("G/L", "× 10^9/L"))
    assert unit_problems(as_written) == ()  # an unmapped unit is kept as written, not refused
    registry = compile_registry(
        [Fragment("measurements", "1", "fragment:nsclc_legacy", (), (HEMOGLOBIN,), ())]
    )
    assert registry.concepts["lab.hemoglobin"].units == ("g/dL", "g/L", "mmol/L")


@pytest.mark.parametrize(
    "arguments, units, detail",
    [
        ((("unit", "ucum_unit"),), ("G/L",), "'G/L': no UCUM form, and the unit argument is ucum_unit"),
        ((("unit", "ucum_unit"),), ("× ULN",), "'× ULN': a reference expression, never a unit"),
        ((("unit", "unit_as_written"),), ("x ULN",), "'x ULN': a reference expression, never a unit"),
        ((("unit", "ucum_unit"),), ("mg/dL and",), "'mg/dL and': not one unit, whole"),
        ((("unit", "ucum_unit"),), (" mg/dL",), "' mg/dL': not one unit, whole"),
        ((("unit", "ucum_unit"),), ("grams",), "'grams': no unit"),
        ((("unit", "unit_as_written"),), ("AST/ALT",), "'AST/ALT': no unit"),
        ((("unit", "unit_as_written"),), ("inclusion/exclusion",), "'inclusion/exclusion': no unit"),
        ((("unit", "unit_as_written"),), ("109/L",), "'109/L': no unit"),
        ((("value", "number"),), ("mg/dL",), "'mg/dL': the concept takes no unit"),
    ],
)
def test_an_unsupported_unit_is_refused_by_name(arguments, units, detail):
    entry = replace(HEMOGLOBIN, arguments=arguments, units=units, examples=())
    assert problems(entry) == (("unsupported_unit", "lab.hemoglobin", detail),)


def test_every_unsupported_unit_is_named_in_order():
    entry = replace(HEMOGLOBIN, units=("g/dL", "G/L", "mg/dL", "× ULN"))
    assert [detail for _, _, detail in unit_problems(entry)] == [
        "'G/L': no UCUM form, and the unit argument is ucum_unit",
        "'× ULN': a reference expression, never a unit",
    ]


@pytest.mark.parametrize(
    "text, span, reason",
    [
        (LABS, Span("unit", 43, 99), "not a non-empty half-open span within the text"),
        (LABS, Span("value", 41, 41), "not a non-empty half-open span within the text"),
        (LABS, Span("value", -1, 2), "not a non-empty half-open span within the text"),
        (LABS, Span("gist", 28, 38), "a role no contract span has"),
        (LABS, Span("reference", 28, 38), "a role no contract span has"),
        (ALT, Span("unit", 75, 79), "not read there as its role (a reference expression, never a unit)"),
        (LABS, Span("comparator", 28, 38), "not read there as its role (no comparator)"),
        (LABS, Span("unit", 43, 45), "not read there as its role (other words)"),
        (LABS, Span("value", 28, 38), "not read there as its role (no number)"),
        (LABS, Span("value", 41, 47), "not read there as its role (other words)"),
        (SEX, Span("unit", 0, 11), "not read there as its role (no unit)"),
    ],
)
def test_an_invalid_span_is_refused_by_name(text, span, reason):
    entry = replace(HEMOGLOBIN, units=(), examples=(Example(text, (span,)),))
    where = f"example 0: {span.role} [{span.start}, {span.end})"
    assert problems(entry) == (("invalid_span", "lab.hemoglobin", f"{where} {reason}"),)


def test_a_span_held_to_its_bounds_only_where_no_parser_reads_its_role():
    """Positive: concept, qualifier, window and whole spans, and the value of a concept whose value is not a
    number, are held to their bounds only. Negative: those same spans out of bounds are still refused."""
    text = "* Documented ALK-positive disease according to an FDA-approved and CE-marked test"
    categorical = replace(
        HEMOGLOBIN,
        arguments=(("value", "text_as_written"),),
        units=(),
        examples=(Example(text, (Span("value", 17, 25), Span("concept", 13, 16), Span("whole", 2, 33))),),
    )
    assert example_problems(categorical) == ()
    beyond = replace(categorical, examples=(Example(text, (Span("window", 2, 999),)),))
    assert [code for code, _, _ in example_problems(beyond)] == ["invalid_span"]


def test_every_invalid_span_is_named_by_example_and_order():
    entry = replace(
        HEMOGLOBIN,
        examples=(
            Example(LABS, (Span("unit", 43, 47),)),
            Example(ALT, (Span("comparator", 71, 72), Span("unit", 75, 79), Span("whole", 0, 0))),
        ),
    )
    assert example_problems(entry) == (
        (
            "invalid_span",
            "lab.hemoglobin",
            "example 1: unit [75, 79) not read there as its role (a reference expression, never a unit)",
        ),
        (
            "invalid_span",
            "lab.hemoglobin",
            "example 1: whole [0, 0) not a non-empty half-open span within the text",
        ),
    )


def test_units_and_examples_are_parsed_from_data_exactly():
    data = {
        "name": "m",
        "version": "1",
        "exposure": "fragment:nsclc_legacy",
        "requires": [],
        "references": [],
    }
    concept = {"concept_id": "lab.hemoglobin", "family": "Measurement", "arguments": [["unit", "ucum_unit"]]}
    concept |= {"authority": "local", "definition": "Hb", "defined_on": "2026-11-01", "units": ["g/dL"]}
    concept["examples"] = [{"text": LABS, "spans": [["unit", 43, 47]]}]
    entry = fragment_from_data({**data, "concepts": [concept]}).concepts[0]
    assert entry.units == ("g/dL",) and entry.examples == (Example(LABS, (Span("unit", 43, 47),)),)
    for broken in ([["unit", 43.0, 47]], [["unit", True, 47]], [["unit", 43]]):
        with pytest.raises(RegistryError) as raised:
            fragment_from_data(
                {**data, "concepts": [{**concept, "examples": [{"text": LABS, "spans": broken}]}]}
            )
        assert raised.value.problems[0][0] == "malformed_fragment"
    with pytest.raises(RegistryError):
        fragment_from_data(
            {**data, "concepts": [{**concept, "examples": [{"text": LABS, "spans": [], "x": 1}]}]}
        )


# The seed registry's version measured on 2026-11-01 before units and examples existed: a digest, no secret.
SEED_VERSION = "762b1e54e93881263a21290231c44f28b6e37a018a1d32a5552e9240f7aad6d1"  # pragma: allowlist secret


def test_the_seed_registrys_version_is_unchanged_by_the_new_fields():
    """Positive: the seed compiles to the version it had before units and examples existed (SEED_VERSION,
    measured on 2026-11-01 before the change). Negative: a concept that uses them changes the version."""
    seed = load_fragments()
    assert compile_registry(seed).version == SEED_VERSION
    unit = replace(seed[0].concepts[0], units=("%",))
    changed = replace(seed[0], concepts=(unit, *seed[0].concepts[1:]))
    assert unit_problems(unit) == (("unsupported_unit", "nsclc.ecog_ps", "'%': the concept takes no unit"),)
    plain = Fragment(
        "measurements", "1", "fragment:nsclc_legacy", (), (replace(HEMOGLOBIN, examples=()),), ()
    )
    bare = Fragment(
        "measurements", "1", "fragment:nsclc_legacy", (), (replace(HEMOGLOBIN, units=(), examples=()),), ()
    )
    assert compile_registry([plain]).version != compile_registry([bare]).version
    assert changed != seed[0]


@pytest.mark.parametrize(
    "first, second, details",
    [
        (
            {"name": "a", "requires": {"b"}},
            {"name": "a", "requires": {"b"}},
            ["FRAGMENT.requires: an unordered set, whose order is the interpreter's hash seed's"],
        ),
        (
            {"concepts": [{"units": frozenset({"%"})}]},
            {"concepts": [{"units": frozenset({"%"})}]},
            ["FRAGMENT.concepts[0].units: an unordered set, whose order is the interpreter's hash seed's"],
        ),
        ({"version": math.nan}, {"version": math.nan}, ["FRAGMENT.version: a number that is not finite"]),
        (
            json.loads('{"version": NaN, "units": [NaN]}'),
            json.loads('{"version": NaN, "units": [NaN]}'),
            [
                "FRAGMENT.version: a number that is not finite",
                "FRAGMENT.units[0]: a number that is not finite",
            ],
        ),
        (
            json.loads('{"version": NaN}'),
            json.loads('{"version": 1.0}'),
            [
                "FRAGMENT.version: a number that is not finite",
                "two loads of the fragment gave different data",
            ],
        ),
        ({"units": ["%"]}, {"units": ("%",)}, ["two loads of the fragment gave different data"]),
        ({"units": ["%"]}, {"units": ["%", "g"]}, ["two loads of the fragment gave different data"]),
        ({"units": ["%"]}, {"unit": ["%"]}, ["two loads of the fragment gave different data"]),
        (
            {"version": (1.0, math.inf)},
            {"version": (1.0, math.inf)},
            ["FRAGMENT.version[1]: a number that is not finite"],
        ),
        ({"version": "0.31"}, {"version": "0.72"}, ["two loads of the fragment gave different data"]),
        ({"name": "a"}, {"name": "a"}, []),
        (None, None, []),
    ],
)
def test_a_nondeterministic_fragment_is_named_where_it_varies(first, second, details):
    found = nondeterminism_problems("x.py", first, second)
    assert found == tuple(("nondeterministic_fragment", "x.py", detail) for detail in details)


def test_a_json_fragment_holding_nan_is_named_once_by_its_place(tmp_path):
    """Positive: a NaN in a JSON fragment is named by its place. Negative: its two loads, each with its own
    NaN object, are not also called different data."""
    (tmp_path / "n.json").write_text(json.dumps(fragment_source()).replace('"1"', "NaN"), encoding="utf-8")
    with pytest.raises(RegistryError) as raised:
        load_fragments(tmp_path)
    assert raised.value.problems == (
        ("nondeterministic_fragment", "n.json", "FRAGMENT.version: a number that is not finite"),
    )


def fragment_source(**overrides):
    data = {
        "name": "m",
        "version": "1",
        "exposure": "fragment:nsclc_legacy",
        "requires": [],
        "references": [],
    }
    return {**data, "concepts": [], **overrides}


def test_a_fragment_that_loads_differently_twice_is_refused(tmp_path):
    (tmp_path / "a.py").write_text(
        "import random\nFRAGMENT = "
        + repr(fragment_source())
        + "\nFRAGMENT['version'] = str(random.random())\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistryError) as raised:
        load_fragments(tmp_path)
    assert raised.value.problems == (
        ("nondeterministic_fragment", "a.py", "two loads of the fragment gave different data"),
    )


def test_a_fragment_holding_a_set_is_refused_and_a_plain_one_loads(tmp_path):
    (tmp_path / "b.py").write_text(
        "FRAGMENT = " + repr(fragment_source()) + "\nFRAGMENT['requires'] = {'m'}\n", encoding="utf-8"
    )
    with pytest.raises(RegistryError) as raised:
        load_fragments(tmp_path)
    assert [code for code, _, _ in raised.value.problems] == ["nondeterministic_fragment"]
    (tmp_path / "b.py").unlink()
    (tmp_path / "c.json").write_text(json.dumps(fragment_source()), encoding="utf-8")
    assert [fragment.name for fragment in load_fragments(tmp_path)] == ["m"]


def test_example_problems_names_a_role_no_contract_span_has_before_its_bounds():
    """Positive: a well-placed unit span is no problem. Negative: a span of a role the contract does not hold
    is named for its role, even when it is also out of bounds; a reference span is such a role."""
    entry = replace(
        HEMOGLOBIN,
        examples=(Example(ALT, (Span("unit", 43, 47), Span("reference", 75, 79), Span("gist", 0, 999))),),
    )
    assert example_problems(entry) == (
        ("invalid_span", "lab.hemoglobin", "example 0: unit [43, 47) not read there as its role (no unit)"),
        ("invalid_span", "lab.hemoglobin", "example 0: reference [75, 79) a role no contract span has"),
        ("invalid_span", "lab.hemoglobin", "example 0: gist [0, 999) a role no contract span has"),
    )
    assert example_problems(replace(HEMOGLOBIN, examples=(Example(LABS, (Span("unit", 43, 47),)),))) == ()
