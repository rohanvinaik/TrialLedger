"""Shared exact-number syntax for protocol objects and operators (interface v1, contract C5)."""

import json
from fractions import Fraction
from pathlib import Path

import pytest

from TrialLedger.layer2 import protocol_numbers

FIXTURES = Path(__file__).resolve().parents[1] / (
    "openspec/changes/connect-protocol-design-workflow/interface/fixtures/rationals.json"
)
RATIONALS = json.loads(FIXTURES.read_text())


def test_valid_rationals_render_canonically():
    for raw, canonical in RATIONALS["valid"].items():
        assert protocol_numbers.render(protocol_numbers.rational(raw, "x")) == canonical


def test_invalid_rational_syntax_and_types_refuse_with_the_callers_prefix():
    for raw in RATIONALS["invalid_syntax"] + RATIONALS["invalid_type"]:
        with pytest.raises(ValueError, match=r"^schedule_invalid_rational$"):
            protocol_numbers.rational(raw, "schedule")


def test_components_over_256_bits_refuse_and_the_boundary_is_accepted():
    for raw in RATIONALS["over_bit_limit"]:
        with pytest.raises(ValueError, match=r"^binomial_rational_bit_limit$"):
            protocol_numbers.rational(raw, "binomial")
    assert protocol_numbers.rational(str((1 << 256) - 1), "x") == Fraction((1 << 256) - 1)


def test_a_float_or_bool_is_never_a_rational():
    assert protocol_numbers.rational_syntax(0.5, 256) == "invalid_rational"
    assert protocol_numbers.rational_syntax(True, 256) == "invalid_rational"
    assert protocol_numbers.rational_syntax(1, 256) == "invalid_rational"


def test_unknown_and_explicitly_empty_unions_stay_distinct():
    assert protocol_numbers.union(None, "x") is None
    assert protocol_numbers.union([], "x") == []


def test_interval_validation_names_each_malformation():
    closed = {"lower": "1", "upper": "2", "lower_inclusive": True, "upper_inclusive": True}
    cases = {
        "x_invalid_union": {"lower": "1"},
        "x_invalid_interval": [{**closed, "lower_inclusive": 1}],
        "x_infinite_inclusive": [{**closed, "lower": None}],
        "x_empty_interval": [{**closed, "lower": "2", "upper": "1"}],
        "x_union_limit": [closed] * 33,
    }
    for code, raw in cases.items():
        with pytest.raises(ValueError, match="^" + code + "$"):
            protocol_numbers.union(raw, "x")
    with pytest.raises(ValueError, match="^x_invalid_interval$"):
        protocol_numbers.union([{**closed, "note": "week 12"}], "x")


def test_singletons_need_both_ends_closed():
    point = {"lower": "91", "upper": "91", "lower_inclusive": True, "upper_inclusive": True}
    assert protocol_numbers.union([point], "x") == [(Fraction(91), Fraction(91), True, True)]
    with pytest.raises(ValueError, match="^x_empty_interval$"):
        protocol_numbers.union([{**point, "upper_inclusive": False}], "x")


def test_unions_are_validated_in_input_order_and_rendered_without_normalizing():
    raw = [
        {"lower": "2", "upper": "3", "lower_inclusive": True, "upper_inclusive": True},
        {"lower": "2/2", "upper": "4/2", "lower_inclusive": True, "upper_inclusive": False},
    ]
    rendered = protocol_numbers.render_union(protocol_numbers.union(raw, "x"))
    assert rendered == [
        {"lower": "2", "upper": "3", "lower_inclusive": True, "upper_inclusive": True},
        {"lower": "1", "upper": "2", "lower_inclusive": True, "upper_inclusive": False},
    ]
    assert protocol_numbers.render_union(None) is None


def test_pure_classifiers_name_their_outcomes():
    assert protocol_numbers.interval_shape(False, True, False, True) == "ok"
    assert protocol_numbers.interval_shape(False, True, True, True) == "infinite_inclusive"
    assert protocol_numbers.interval_shape(True, False, True, True) == "infinite_inclusive"
    assert protocol_numbers.interval_order(-1, False, False) == "ok"
    assert protocol_numbers.interval_order(0, True, True) == "ok"
    assert protocol_numbers.interval_order(0, True, False) == "empty_interval"
    assert protocol_numbers.interval_order(1, True, True) == "empty_interval"
