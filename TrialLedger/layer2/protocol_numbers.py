"""Exact rational and interval-union syntax shared by protocol objects and operators (C5 syntax only).

This module parses and renders. It performs no set arithmetic, unit or anchor comparison, or clinical
interpretation: those belong to their operators. Every malformed value refuses with a caller-prefixed code.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import cast

RATIONAL = re.compile(r"-?(0|[1-9][0-9]*)(/[1-9][0-9]*)?")
MAX_COMPONENT_BITS = 256
MAX_INTERVALS = 32
INTERVAL_FIELDS = {"lower", "upper", "lower_inclusive", "upper_inclusive"}

Interval = tuple[Fraction | None, Fraction | None, bool, bool]


def rational_syntax(value: object, max_bits: int) -> str:
    """Classify one rational string before arithmetic (pure — pinned).

    pre: max_bits > 0
    post: __return__ in ("ok", "invalid_rational", "rational_bit_limit")
    post: __return__ != "ok" or isinstance(value, str)
    """
    if type(value) is not str or RATIONAL.fullmatch(value) is None:
        return "invalid_rational"
    parts = value.lstrip("-").split("/")
    if any(int(part).bit_length() > max_bits for part in parts):
        return "rational_bit_limit"
    return "ok"


def rational(value: object, prefix: str) -> Fraction:
    """An exact rational from canonical-or-unreduced syntax; never a float, int or decimal."""
    code = rational_syntax(value, MAX_COMPONENT_BITS)
    if code != "ok":
        raise ValueError(prefix + "_" + code)
    return Fraction(str(value))


def render(value: Fraction) -> str:
    """Reduced canonical string; integers without '/1'."""
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def interval_shape(lower_known: bool, upper_known: bool, lower_inclusive: bool, upper_inclusive: bool) -> str:
    """Classify endpoint inclusion at infinity (pure — pinned).

    post: __return__ in ("ok", "infinite_inclusive")
    post: __return__ == "ok" or (lower_inclusive and not lower_known) or (upper_inclusive and not upper_known)
    """
    if (lower_inclusive and not lower_known) or (upper_inclusive and not upper_known):
        return "infinite_inclusive"
    return "ok"


def interval_order(order: int, lower_inclusive: bool, upper_inclusive: bool) -> str:
    """Classify a single interval from its endpoint comparison: -1 below, 0 equal, 1 reversed (pure — pinned).

    pre: order in (-1, 0, 1)
    post: __return__ in ("ok", "empty_interval")
    post: __return__ == "ok" or order == 1 or (order == 0 and not (lower_inclusive and upper_inclusive))
    """
    if order < 0:
        return "ok"
    if order == 0 and lower_inclusive and upper_inclusive:
        return "ok"
    return "empty_interval"


def _interval(raw: object, prefix: str) -> Interval:
    if type(raw) is not dict or set(raw) != INTERVAL_FIELDS:
        raise ValueError(prefix + "_invalid_interval")
    raw = cast(dict[str, object], raw)
    lower_inclusive, upper_inclusive = raw["lower_inclusive"], raw["upper_inclusive"]
    if type(lower_inclusive) is not bool or type(upper_inclusive) is not bool:
        raise ValueError(prefix + "_invalid_interval")
    lower = None if raw["lower"] is None else rational(raw["lower"], prefix)
    upper = None if raw["upper"] is None else rational(raw["upper"], prefix)
    if interval_shape(lower is not None, upper is not None, lower_inclusive, upper_inclusive) != "ok":
        raise ValueError(prefix + "_infinite_inclusive")
    if lower is not None and upper is not None:
        order = (lower > upper) - (lower < upper)
        if interval_order(order, lower_inclusive, upper_inclusive) != "ok":
            raise ValueError(prefix + "_empty_interval")
    return (lower, upper, lower_inclusive, upper_inclusive)


def union(raw: object, prefix: str) -> list[Interval] | None:
    """Validated intervals in input order, or None for an unknown union. Never normalized here."""
    if raw is None:
        return None
    if type(raw) is not list:
        raise ValueError(prefix + "_invalid_union")
    if len(raw) > MAX_INTERVALS:
        raise ValueError(prefix + "_union_limit")
    return [_interval(item, prefix) for item in raw]


def render_union(intervals: list[Interval] | None) -> list[dict] | None:
    """Canonical JSON intervals, in the order given; None stays unknown."""
    if intervals is None:
        return None
    return [
        {
            "lower": None if lower is None else render(lower),
            "upper": None if upper is None else render(upper),
            "lower_inclusive": lower_inclusive,
            "upper_inclusive": upper_inclusive,
        }
        for lower, upper, lower_inclusive, upper_inclusive in intervals
    ]
